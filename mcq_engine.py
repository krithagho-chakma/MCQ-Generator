import streamlit as st
import google.generativeai as genai
import json
import PyPDF2
from docx import Document

# --- 1. PAGE CONFIG & CUSTOM CSS (NEW UI IMPROVEMENTS) ---
st.set_page_config(page_title="MCQ Engine", page_icon="📚", layout="wide")

# Injecting custom CSS to make the UI minimal and clean
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 4px;
            font-size: 16px;
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. PERSISTENT SESSION STATE ---
# Initialize session state for API Key and Table Data
if "user_api_key" not in st.session_state:
    st.session_state["user_api_key"] = ""
if "mcq_data_t1" not in st.session_state:
    st.session_state["mcq_data_t1"] = None
if "mcq_data_t2" not in st.session_state:
    st.session_state["mcq_data_t2"] = None

st.sidebar.title("⚙️ Configuration")
st.sidebar.markdown("---")

api_key_input = st.sidebar.text_input(
    "🔑 Gemini API Key:", 
    value=st.session_state["user_api_key"], 
    type="password",
    help="Enter your Google AI Studio API key to power the engine."
)

if api_key_input:
    st.session_state["user_api_key"] = api_key_input
    genai.configure(api_key=st.session_state["user_api_key"])
    st.sidebar.success("API Key Active")
else:
    st.sidebar.warning("API key required to proceed.")

# --- 3. HELPER FUNCTIONS ---
def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

def extract_text_from_docx(docx_file):
    doc = Document(docx_file)
    text = ""
    for para in doc.paragraphs:
        if para.text:
            text += para.text + "\n"
    return text

def generate_mcqs(context_text, user_topics, custom_instructions, num_easy, num_medium, num_hard, selected_model):
    model = genai.GenerativeModel(selected_model)
    total_questions = num_easy + num_medium + num_hard
    
    if context_text.strip():
        source_instruction = "Based on the provided Context Text and user instructions, generate"
        context_block = f"Context Text:\n{context_text}"
    else:
        source_instruction = "Based on your expert general knowledge and user instructions, generate"
        context_block = "No context text provided. Generate purely based on the requested topics and instructions."
    
    prompt = f"""
    Act as an expert educator. {source_instruction} exactly {total_questions} board-standard multiple-choice questions.
    
    SPECIAL USER GENERATION INSTRUCTIONS (CRITICAL):
    {custom_instructions if custom_instructions else "None provided. Follow standard board-level question generation."}

    CRITICAL INSTRUCTIONS FOR DIFFICULTY LEVEL:
    You must generate EXACTLY:
    - {num_easy} questions where "difficulty_level" is "Easy"
    - {num_medium} questions where "difficulty_level" is "Medium"
    - {num_hard} questions where "difficulty_level" is "Hard"
    Do not use any other words for difficulty level.

    CRITICAL INSTRUCTION FOR THE 'topics' COLUMN FIELD:
    Here is the list of allowed topic names: {user_topics}
    For the "topics" field in each question object, you MUST select EXACTLY ONE topic from the list above that best fits the generated question. Do not invent any new topics.
    DO NOT include sequence identifiers like '1.0', '2.1', etc. in the topic field.

    CRITICAL INSTRUCTION FOR 'solution_body':
    The "solution_body" field MUST follow this exact 2-line format:
    Line 1: The exact text of the correct option (DO NOT include sequence identifiers like 'A.', 'B.', 'Option A', '১.', etc.). Place an Enter at the end of the line.
    Line 2: A clear, detailed explanation of why this answer is correct. Always start with the line 'ব্যাখ্যা:'

    Example format for solution_body:
    "ইনপুট, প্রসেসিং, আউটপুট, মেমোরি ও কন্ট্রোল ইউনিট
    ব্যাখ্যা: কম্পিউটারের কাজ করার মূল পদ্ধতি হলো তথ্য গ্রহণ, প্রসেসিং, প্রদর্শন ও সংরক্ষণ করা।"

    Output the result STRICTLY as a JSON array of objects. Do not include markdown formatting like ```json.
    Each object must have the following exact keys:
    "sl_no", "question_title", "A", "B", "C", "D", 
    "solution_body", "correct_option", "subject", "chapter", "topics", 
    "question_category", "difficulty_level".
    
    {context_block}
    """
    
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        )
    )
    
    return json.loads(response.text)

def parse_existing_mcqs(raw_mcq_text, user_topics, special_instructions, selected_model):
    model = genai.GenerativeModel(selected_model)
    
    prompt = f"""
    You are an expert educational content parser and converter.
    Your task is to take the provided raw, unformatted, or existing MCQs and map them strictly into a standard JSON structure.
    
    CRITICAL PARSING RULES:
    1. Parse ALL MCQs found in the input text into a JSON array of objects.
    2. Number the sl_no sequentially starting from 1.
    3. Extract the Question Title, Option A, Option B, Option C, Option D, Correct Option, and Solution Body (if solution body isn't provided, create a brief accurate explanation).
    4. Infer appropriate "subject", "chapter", "question_category" (e.g., Board, Model Test), and "difficulty_level" (Easy, Medium, Hard) for each question.

    CRITICAL INSTRUCTION FOR THE 'topics' FIELD:
    Here is a list of allowed topics: {user_topics}
    For the "topics" field in each question, you MUST select EXACTLY ONE topic from the list above that best fits the question. Do not invent any new topics.
    DO NOT include sequence identifiers like '1.0', '2.1', etc.

    CRITICAL INSTRUCTION FOR 'solution_body':
    The "solution_body" field MUST follow this exact 2-line format:
    Line 1: The exact text of the correct option (DO NOT include sequence identifiers like 'A.', 'B.', 'Option A', '১.', etc.). Place an Enter at the end of the line.
    Line 2: A clear, detailed explanation of why this answer is correct. Always start with the line 'ব্যাখ্যা:'

    Example format for solution_body:
    "ইনপুট, প্রসেসিং, আউটপুট, মেমোরি ও কন্ট্রোল ইউনিট
    ব্যাখ্যা: কম্পিউটারের কাজ করার মূল পদ্ধতি হলো তথ্য গ্রহণ, প্রসেসিং, প্রদর্শন ও সংরক্ষণ করা।"
    
    SPECIAL USER INSTRUCTIONS (CRITICAL):
    {special_instructions if special_instructions else "None provided. Follow standard parsing."}

    Output the result STRICTLY as a JSON array of objects. Do not include markdown formatting like ```json.
    Each object must have the following exact keys:
    "sl_no", "question_title", "A", "B", "C", "D", 
    "solution_body", "correct_option", "subject", "chapter", "topics", 
    "question_category", "difficulty_level".

    Raw MCQs to parse:
    {raw_mcq_text}
    """
    
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(response_mime_type="application/json")
    )
    return json.loads(response.text)

def create_mcq_docx(mcq_data, output_filename="MCQs.docx"):
    doc = Document()
    doc.add_heading('Generated MCQs', 0)
    
    table = doc.add_table(rows=1, cols=13)
    table.style = 'Table Grid'
    
    headers = [
        "Sl no.", "Question Title", "Option A", "Option B", "Option C", 
        "Option D", "Solution Body", "Correct Option", "Subject", 
        "Chapter", "Topics", "Question Category", "Difficulty Level"
    ]
    
    hdr_cells = table.rows[0].cells
    for i, header in enumerate(headers):
        hdr_cells[i].text = header
        
    for mcq in mcq_data:
        row_cells = table.add_row().cells
        # Use .get() defensively with a string fallback just in case rows were added manually
        row_cells[0].text = str(mcq.get("sl_no", ""))
        row_cells[1].text = str(mcq.get("question_title", ""))
        row_cells[2].text = str(mcq.get("A", ""))
        row_cells[3].text = str(mcq.get("B", ""))
        row_cells[4].text = str(mcq.get("C", ""))
        row_cells[5].text = str(mcq.get("D", ""))
        row_cells[6].text = str(mcq.get("solution_body", ""))
        row_cells[7].text = str(mcq.get("correct_option", ""))
        row_cells[8].text = str(mcq.get("subject", ""))
        row_cells[9].text = str(mcq.get("chapter", ""))
        row_cells[10].text = str(mcq.get("topics", ""))
        row_cells[11].text = str(mcq.get("question_category", ""))
        row_cells[12].text = str(mcq.get("difficulty_level", ""))
        
    doc.save(output_filename)

# --- 4. WEB INTERFACE (MODERNIZED UI) ---
st.title("📚 MCQ Automation Engine")
st.markdown("Automate the generation and formatting of board-standard multiple-choice questions.")

# --- GLOBAL MODEL SELECTION ---
with st.container(border=True):
    st.markdown("#### 🤖 Global AI Model Selection")
    model_choice = st.selectbox(
        "Select the Gemini engine for this task:",
        options=[
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite"
        ],
        index=1,
        label_visibility="collapsed"
    )

    if model_choice == "gemini-3.8-flash":
        st.caption("⚠️ **Free Tier Limit:** 20 requests per day.")
    elif model_choice == "gemini-3.7-flash":
        st.caption("💡 **Free Tier Limit:** 1,500 requests per day. (Recommended)")
    elif model_choice == "gemini-3.6-flash":
        st.caption("🚫 **Free Tier Limit:** Requires Pay-As-You-Go account.")
    else:
        st.caption("✅ **Free Tier Limit:** 1,500 requests per day.")

st.markdown("<br>", unsafe_allow_html=True) # Spacer

# Create two clean tabs
tab1, tab2 = st.tabs(["✨ Generate New MCQs", "📋 Format Existing MCQs"])

# ================= TAB 1: GENERATE NEW MCQS =================
with tab1:
    with st.container(border=True):
        st.markdown("#### 📄 1. Source Material (Optional)")
        st.caption("Leave blank to generate questions based purely on the topics provided below.")
        
        col_file, col_text = st.columns(2)
        with col_file:
            uploaded_file = st.file_uploader("Upload Document (PDF/DOCX)", type=["pdf", "docx"])
        with col_text:
            raw_text = st.text_area("Or paste raw text here", height=100)

    with st.container(border=True):
        st.markdown("#### 🎯 2. Question Parameters")
        topics_input = st.text_input(
            "Allowed Topics for Table Mapping (comma-separated)", 
            placeholder="e.g., Hardware, Memory, Super Computers"
        )
        custom_instructions = st.text_area(
            "Custom Generation Instructions (Optional)", 
            placeholder="e.g., 'Focus heavily on numerical problems', 'Generate questions in Bengali'",
            height=100,
            key="t1_custom_instructions"
        )

    with st.container(border=True):
        st.markdown("#### 📊 3. Difficulty Breakdown")
        col1, col2, col3 = st.columns(3)
        with col1:
            num_easy = st.number_input("🟢 Easy", min_value=0, max_value=50, value=10)
        with col2:
            num_medium = st.number_input("🟡 Medium", min_value=0, max_value=50, value=15)
        with col3:
            num_hard = st.number_input("🔴 Hard", min_value=0, max_value=50, value=5)

    total_q = num_easy + num_medium + num_hard

    st.markdown("<br>", unsafe_allow_html=True) # Spacer
    
    col_btn, col_msg = st.columns([1, 2])
    with col_btn:
        generate_btn = st.button("🚀 Generate MCQs", use_container_width=True, type="primary")
    with col_msg:
        st.info(f"Target Generation: **{total_q}** Questions")

    if generate_btn:
        if not api_key_input:
            st.error("Please enter your API Key in the sidebar first!")
        elif total_q == 0:
            st.error("Please specify at least one question to generate.")
        elif not topics_input:
            st.error("Please provide at least one topic for table mapping.")
        else:
            with st.spinner(f"Engine running... Generating {total_q} questions using {model_choice}"):
                text_to_process = ""
                if uploaded_file:
                    if uploaded_file.name.endswith('.pdf'):
                        text_to_process = extract_text_from_pdf(uploaded_file)
                    elif uploaded_file.name.endswith('.docx'):
                        text_to_process = extract_text_from_docx(uploaded_file)
                elif raw_text:
                    text_to_process = raw_text
                    
                try:
                    # Fetch and save data into Session State so it doesn't vanish when edited
                    st.session_state["mcq_data_t1"] = generate_mcqs(
                        text_to_process, topics_input, custom_instructions, 
                        num_easy, num_medium, num_hard, model_choice
                    )
                    st.success("✨ Generation Complete!")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

    # Display the editable table and download button IF data exists in session state
    if st.session_state["mcq_data_t1"]:
        with st.container(border=True):
            st.markdown("#### 👀 Preview & Edit Generated Table")
            st.caption("Double-click any cell to edit its text. You can also add or delete rows using the tools on the right. Changes instantly apply to your download.")
            
            # Interactive Data Editor
            edited_data_t1 = st.data_editor(
                st.session_state["mcq_data_t1"], 
                use_container_width=True, 
                num_rows="dynamic", 
                key="editor_t1"
            )
        
        # Build the Word Document using the EDITED data
        create_mcq_docx(edited_data_t1, "Generated_MCQs.docx")
        
        with open("Generated_MCQs.docx", "rb") as file:
            st.download_button(
                label="📥 Download Edited Word Document (.docx)",
                data=file,
                file_name="Generated_MCQs.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True
            )

# ================= TAB 2: FORMAT EXISTING MCQS =================
with tab2:
    with st.container(border=True):
        st.markdown("#### 📝 1. Raw Input")
        st.caption("Upload or paste your unformatted questions.")
        col_file_t2, col_text_t2 = st.columns(2)
        with col_file_t2:
            uploaded_file_t2 = st.file_uploader("Upload Raw MCQs (PDF/DOCX)", type=["pdf", "docx"], key="t2_pdf")
        with col_text_t2:
            raw_text_t2 = st.text_area("Or paste raw pre-written MCQs here", height=150, placeholder="1. What is CPU?\nA. Brain\nB. Memory\nC. Output\nD. Storage\nAnswer: A", key="t2_text")
    
    with st.container(border=True):
        st.markdown("#### 🎯 2. Formatting Parameters")
        topics_input_t2 = st.text_input("Target Topics (Optional)", placeholder="e.g., Computer Basics, Hardware", key="t2_topics")
        special_instructions = st.text_area(
            "Special AI Instructions (Optional)", 
            placeholder="e.g., 'Set Subject to ICT', 'Fix any Bengali spelling mistakes', 'Automatically fill in missing solution explanations'",
            height=100,
            key="t2_instructions"
        )

    st.markdown("<br>", unsafe_allow_html=True) # Spacer

    if st.button("🛠️ Format Existing MCQs", use_container_width=True, type="primary", key="btn_t2"):
        if not api_key_input:
            st.error("Please configure your API Key in the sidebar.")
        elif not uploaded_file_t2 and not raw_text_t2:
            st.error("Please provide your raw MCQs in the text box or upload a document.")
        else:
            with st.spinner(f"Parsing and reformatting questions using {model_choice}..."):
                text_to_process = ""
                if uploaded_file_t2:
                    if uploaded_file_t2.name.endswith('.pdf'):
                        text_to_process = extract_text_from_pdf(uploaded_file_t2)
                    elif uploaded_file_t2.name.endswith('.docx'):
                        text_to_process = extract_text_from_docx(uploaded_file_t2)
                elif raw_text_t2:
                    text_to_process = raw_text_t2
                    
                try:
                    # Save parsed data to Session State
                    st.session_state["mcq_data_t2"] = parse_existing_mcqs(
                        text_to_process, topics_input_t2, special_instructions, model_choice
                    )
                    st.success("✨ Successfully reformatted into table format!")
                except Exception as e:
                    st.error(f"Error parsing MCQs: {e}")

    # Display the editable table and download button IF data exists in session state
    if st.session_state["mcq_data_t2"]:
        with st.container(border=True):
            st.markdown("#### 👀 Preview & Edit Formatted Table")
            st.caption("Double-click any cell to edit its text. You can also add or delete rows. Changes instantly apply to your download.")
            
            # Interactive Data Editor
            edited_data_t2 = st.data_editor(
                st.session_state["mcq_data_t2"], 
                use_container_width=True, 
                num_rows="dynamic", 
                key="editor_t2"
            )
        
        # Build the Word Document using the EDITED data
        create_mcq_docx(edited_data_t2, "Formatted_Ready_MCQs.docx")
        
        with open("Formatted_Ready_MCQs.docx", "rb") as f:
            st.download_button(
                label="📥 Download Edited Word Document (.docx)",
                data=f,
                file_name="Formatted_Ready_MCQs.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                key="dl_t2"
            )
