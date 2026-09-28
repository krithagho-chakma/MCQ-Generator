import streamlit as st
import google.generativeai as genai
import json
import PyPDF2
from docx import Document

# --- 1. PERSISTENT SESSION STATE API KEY ---
st.sidebar.title("⚙️ Configuration")

# Initialize session state for the key if it doesn't exist yet
if "user_api_key" not in st.session_state:
    st.session_state["user_api_key"] = ""

# Sidebar input linked to session state
api_key_input = st.sidebar.text_input(
    "Enter your Gemini API Key:", 
    value=st.session_state["user_api_key"], 
    type="password"
)

# Save to session state whenever user enters or changes it
if api_key_input:
    st.session_state["user_api_key"] = api_key_input
    genai.configure(api_key=st.session_state["user_api_key"])
else:
    st.sidebar.warning("Please enter your API key to proceed.")

# --- 2. HELPER FUNCTIONS ---
def extract_text_from_pdf(pdf_file):
    """Reads the uploaded PDF and pulls all the text out."""
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

def generate_mcqs(context_text, user_topics, num_easy, num_medium, num_hard, selected_model):
    """Sends the text, topics, and difficulty distribution using the chosen SDK."""
    model = genai.GenerativeModel(selected_model)
    total_questions = num_easy + num_medium + num_hard
    
    prompt = f"""
    Act as an expert educator. Based on the following Context Text, generate exactly {total_questions} board-standard multiple-choice questions.
    
    CRITICAL INSTRUCTIONS FOR DIFFICULTY LEVEL:
    You must generate EXACTLY:
    - {num_easy} questions where "difficulty_level" is "Easy"
    - {num_medium} questions where "difficulty_level" is "Medium"
    - {num_hard} questions where "difficulty_level" is "Hard"
    Do not use any other words for difficulty level.

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

    Output the result STRICTLY as a JSON array of objects. Do not include markdown formatting like ```json.
    Each object must have the following exact keys:
    "sl_no", "question_title", "A", "B", "C", "D", 
    "solution_body", "correct_option", "subject", "chapter", "topics", 
    "question_category", "difficulty_level".
    
    Context Text:
    {context_text}
    """
    
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        )
    )
    
    return json.loads(response.text)

def parse_existing_mcqs(raw_mcq_text, user_topics, special_instructions, selected_model):
    """Parses PRE-EXISTING raw MCQs and maps them to the required 13-column schema."""
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
    """Creates the formatted Word Document with the 13-column table."""
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

# --- 3. WEB INTERFACE (STREAMLIT) ---
st.title("📚 MCQ Automation & Formatting Engine")
# Create two tabs
tab1, tab2 = st.tabs(["✨ Generate New MCQs", "📋 Format Existing Raw MCQs"])

# ================= TAB 1: GENERATE NEW MCQS =================
with tab1:
    st.write("Upload a source document, define your topics, and configure difficulty levels.")
    # --- NEW: EXPANDED MODEL SELECTION UI ---
    st.subheader("1. AI Model Selection")
    model_choice = st.selectbox(
        "Choose which Gemini model to use:",
        options=[
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite"
        ],
        index=1 # Sets gemini-3.7-flash as the default choice
    )

    # Provide the official free-tier quota details dynamically
    if model_choice == "gemini-3.8-flash":
        st.warning("⚠️ **Free Tier Limit:** Only 20 requests per day. You will hit limits very quickly.")
    elif model_choice == "gemini-3.7-flash":
        st.info("💡 **Free Tier Limit:** 1,500 requests per day. Recommended for bulk generation.")
    elif model_choice == "gemini-3.6-flash":
        st.error("🚫 **Free Tier Limit:** Not available on the Free Tier. Requires a Pay-As-You-Go billing account.")
    elif model_choice == "gemini-3.5-flash":
        st.info("💡 **Free Tier Limit:** 1,500 requests per day. Fast and highly stable.")
    elif model_choice == "gemini-3.5-flash-lite":
        st.success("✅ **Free Tier Limit:** 1,500 requests per day. Ultra-fast for simpler, high-volume tasks.")
    elif model_choice == "gemini-3.1-flash-lite":
        st.success("✅ **Free Tier Limit:** 1,500 requests per day. High efficiency and speed for basic processing.")

    # --- PREVIOUS INPUTS ---

    uploaded_file = st.file_uploader("2. Upload Source PDF", type="pdf")
    raw_text = st.text_area("Or paste raw source text here")
    topics_input = st.text_input("3. Enter specific topics (comma-separated)", placeholder="e.g., Hardware, Memory, Super Computers")

    st.write("4. Difficulty Breakdown (Number of Questions)")
    col1, col2, col3 = st.columns(3)
    with col1:
        num_easy = st.number_input("Easy", min_value=0, max_value=50, value=10)
    with col2:
        num_medium = st.number_input("Medium", min_value=0, max_value=50, value=15)
    with col3:
        num_hard = st.number_input("Hard", min_value=0, max_value=50, value=5)

    total_q = num_easy + num_medium + num_hard
    st.info(f"Total questions to generate: {total_q}")

    if st.button("Generate MCQs"):
        if not api_key_input:
            st.error("Please enter your API Key in the sidebar first!")
        elif total_q == 0:
            st.error("Please specify at least one question to generate.")
        elif not topics_input:
            st.error("Please provide at least one topic.")
        elif not uploaded_file and not raw_text:
            st.error("Please provide some source text or upload a PDF.")
        else:
            with st.spinner(f"Analyzing text and generating {total_q} questions (this takes a minute)..."):
                text_to_process = ""
                if uploaded_file:
                    text_to_process = extract_text_from_pdf(uploaded_file)
                elif raw_text:
                    text_to_process = raw_text
                    
                try:
                    # Added model_choice here so the dropdown works correctly
                    mcq_json = generate_mcqs(text_to_process, topics_input, num_easy, num_medium, num_hard, model_choice)
                    create_mcq_docx(mcq_json, "Generated_MCQs.docx")
                    
                    st.success("Successfully generated!")
                    
                    with open("Generated_MCQs.docx", "rb") as file:
                        st.download_button(
                            label="Download Formatted Word Document",
                            data=file,
                            file_name="Generated_MCQs.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# ================= TAB 2: FORMAT EXISTING MCQS =================
with tab2:
    st.subheader("Convert & Reformat Pre-written MCQs")
    st.write("Paste your raw, unformatted questions or upload a document containing ready MCQs.")
    
    uploaded_file_t2 = st.file_uploader("1. Upload Raw MCQs Document (PDF)", type="pdf", key="t2_pdf")
    raw_text_t2 = st.text_area("Or paste raw pre-written MCQs here", height=200, placeholder="1. What is CPU?\nA. Brain\nB. Memory\nC. Output\nD. Storage\nAnswer: A", key="t2_text")
    
    topics_input_t2 = st.text_input("2. Target Topics (Optional)", placeholder="e.g., Computer Basics, Hardware", key="t2_topics")
    
    special_instructions = st.text_area(
        "3. Special Instructions for AI (Optional)", 
        placeholder="e.g., 'Set Subject to ICT', 'Fix any Bengali spelling mistakes', 'Automatically fill in missing solution explanations', 'Mark difficulty as Medium for all'",
        key="t2_instructions"
    )

    if st.button("Format Existing MCQs", key="btn_t2"):
        if not api_key_input:
            st.error("Please configure your API Key in the sidebar.")
        elif not uploaded_file_t2 and not raw_text_t2:
            st.error("Please provide your raw MCQs in the text box or upload a file.")
        else:
            with st.spinner(f"Parsing and reformatting questions using {model_choice}..."):
                text_to_process = extract_text_from_pdf(uploaded_file_t2) if uploaded_file_t2 else raw_text_t2
                try:
                    mcq_json = parse_existing_mcqs(text_to_process, topics_input_t2, special_instructions, model_choice)
                    create_mcq_docx(mcq_json, "Formatted_Ready_MCQs.docx")
                    st.success("Successfully reformatted into table format!")
                    
                    with open("Formatted_Ready_MCQs.docx", "rb") as f:
                        st.download_button(
                            label="Download Formatted Word Document (.docx)",
                            data=f,
                            file_name="Formatted_Ready_MCQs.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key="dl_t2"
                        )
                except Exception as e:
                    st.error(f"Error parsing MCQs: {e}")
