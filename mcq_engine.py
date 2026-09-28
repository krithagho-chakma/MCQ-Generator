import streamlit as st
import google.generativeai as genai
import json
import PyPDF2
from docx import Document

# Initialize session state variables specific to MCQs
if "mcq_data_t1" not in st.session_state:
    st.session_state["mcq_data_t1"] = None
if "mcq_data_t2" not in st.session_state:
    st.session_state["mcq_data_t2"] = None

def extract_text_from_pdf(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted: text += extracted + "\n"
    return text

def extract_text_from_docx(docx_file):
    doc = Document(docx_file)
    text = ""
    for para in doc.paragraphs:
        if para.text: text += para.text + "\n"
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

    CRITICAL INSTRUCTION FOR THE 'topics' COLUMN FIELD:
    Here is the list of allowed topic names: {user_topics}
    For the "topics" field, MUST select EXACTLY ONE topic from the list above. DO NOT include sequence identifiers like '1.0', '2.1'.

    CRITICAL INSTRUCTION FOR 'solution_body':
    Line 1: The exact text of the correct option (DO NOT include sequence identifiers like 'A.', 'B.'). Place an Enter at the end of the line.
    Line 2: A clear, detailed explanation of why this answer is correct. Always start with the line 'ব্যাখ্যা:'

    Output STRICTLY as a JSON array of objects with keys:
    "sl_no", "question_title", "A", "B", "C", "D", "solution_body", "correct_option", "subject", "chapter", "topics", "question_category", "difficulty_level".
    
    {context_block}
    """
    response = model.generate_content(prompt, generation_config=genai.GenerationConfig(response_mime_type="application/json"))
    return json.loads(response.text)

def parse_existing_mcqs(raw_mcq_text, user_topics, special_instructions, selected_model):
    model = genai.GenerativeModel(selected_model)
    prompt = f"""
    You are an expert educational content parser. Map the provided raw MCQs strictly into a standard JSON structure.
    Parse ALL MCQs. Extract Question Title, Options A-D, Correct Option, and Solution Body (generate one if missing).
    Topics allowed: {user_topics}
    
    CRITICAL INSTRUCTION FOR 'solution_body':
    Line 1: Exact text of correct option.
    Line 2: Explanation starting with 'ব্যাখ্যা:'.
    
    SPECIAL USER INSTRUCTIONS (CRITICAL): {special_instructions if special_instructions else "None"}

    Output STRICTLY as a JSON array of objects with keys:
    "sl_no", "question_title", "A", "B", "C", "D", "solution_body", "correct_option", "subject", "chapter", "topics", "question_category", "difficulty_level".

    Raw MCQs:
    {raw_mcq_text}
    """
    response = model.generate_content(prompt, generation_config=genai.GenerationConfig(response_mime_type="application/json"))
    return json.loads(response.text)

def create_mcq_docx(mcq_data, output_filename="MCQs.docx"):
    doc = Document()
    doc.add_heading('Generated MCQs', 0)
    table = doc.add_table(rows=1, cols=13)
    table.style = 'Table Grid'
    headers = ["Sl no.", "Question Title", "Option A", "Option B", "Option C", "Option D", "Solution Body", "Correct Option", "Subject", "Chapter", "Topics", "Question Category", "Difficulty Level"]
    hdr_cells = table.rows[0].cells
    for i, header in enumerate(headers): hdr_cells[i].text = header
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

def run_mcq_interface(model_choice, api_key_input):
    tab1, tab2 = st.tabs(["✨ Generate New MCQs", "📋 Format Existing MCQs"])
    
    with tab1:
        with st.container(border=True):
            st.markdown("#### 📄 1. Source Material (Optional)")
            st.caption("Leave blank to generate purely on topics provided.")
            col_file, col_text = st.columns(2)
            with col_file: uploaded_file = st.file_uploader("Upload Document (PDF/DOCX)", type=["pdf", "docx"], key="mcq_f1")
            with col_text: raw_text = st.text_area("Or paste raw text here", height=100, key="mcq_t1")

        with st.container(border=True):
            st.markdown("#### 🎯 2. Question Parameters")
            topics_input = st.text_input("Allowed Topics for Table Mapping (comma-separated)", placeholder="e.g., Hardware", key="mcq_top1")
            custom_instructions = st.text_area("Custom Generation Instructions (Optional)", height=100, key="mcq_cust1")

        with st.container(border=True):
            st.markdown("#### 📊 3. Difficulty Breakdown")
            col1, col2, col3 = st.columns(3)
            with col1: num_easy = st.number_input("🟢 Easy", min_value=0, value=10, key="mcq_e1")
            with col2: num_medium = st.number_input("🟡 Medium", min_value=0, value=15, key="mcq_m1")
            with col3: num_hard = st.number_input("🔴 Hard", min_value=0, value=5, key="mcq_h1")

        total_q = num_easy + num_medium + num_hard
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_btn, col_msg = st.columns([1, 2])
        with col_btn: generate_btn = st.button("🚀 Generate MCQs", use_container_width=True, type="primary")
        with col_msg: st.info(f"Target Generation: **{total_q}** Questions")

        if generate_btn:
            if not api_key_input: st.error("Please enter your API Key in the sidebar first!")
            elif total_q == 0: st.error("Please specify at least one question to generate.")
            elif not topics_input: st.error("Please provide at least one topic.")
            else:
                with st.spinner(f"Engine running... Generating {total_q} questions using {model_choice}"):
                    text_to_process = ""
                    if uploaded_file:
                        if uploaded_file.name.endswith('.pdf'): text_to_process = extract_text_from_pdf(uploaded_file)
                        elif uploaded_file.name.endswith('.docx'): text_to_process = extract_text_from_docx(uploaded_file)
                    elif raw_text: text_to_process = raw_text
                    try:
                        st.session_state["mcq_data_t1"] = generate_mcqs(text_to_process, topics_input, custom_instructions, num_easy, num_medium, num_hard, model_choice)
                        st.success("✨ Generation Complete!")
                    except Exception as e: st.error(f"An error occurred: {e}")

        if st.session_state["mcq_data_t1"]:
            with st.container(border=True):
                st.markdown("#### 👀 Preview & Edit Generated Table")
                edited_data_t1 = st.data_editor(st.session_state["mcq_data_t1"], use_container_width=True, num_rows="dynamic", key="mcq_edit1")
            create_mcq_docx(edited_data_t1, "Generated_MCQs.docx")
            with open("Generated_MCQs.docx", "rb") as file:
                st.download_button("📥 Download Edited Word Document (.docx)", data=file, file_name="Generated_MCQs.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)

    with tab2:
        with st.container(border=True):
            st.markdown("#### 📝 1. Raw Input")
            col_file_t2, col_text_t2 = st.columns(2)
            with col_file_t2: uploaded_file_t2 = st.file_uploader("Upload Raw MCQs (PDF/DOCX)", type=["pdf", "docx"], key="mcq_f2")
            with col_text_t2: raw_text_t2 = st.text_area("Or paste raw pre-written MCQs here", height=150, key="mcq_t2")
        
        with st.container(border=True):
            st.markdown("#### 🎯 2. Formatting Parameters")
            topics_input_t2 = st.text_input("Target Topics (Optional)", key="mcq_top2")
            special_instructions = st.text_area("Special AI Instructions (Optional)", height=100, key="mcq_cust2")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🛠️ Format Existing MCQs", use_container_width=True, type="primary"):
            if not api_key_input: st.error("Please configure your API Key in the sidebar.")
            elif not uploaded_file_t2 and not raw_text_t2: st.error("Please provide raw MCQs.")
            else:
                with st.spinner("Parsing and reformatting questions..."):
                    text_to_process = ""
                    if uploaded_file_t2:
                        if uploaded_file_t2.name.endswith('.pdf'): text_to_process = extract_text_from_pdf(uploaded_file_t2)
                        elif uploaded_file_t2.name.endswith('.docx'): text_to_process = extract_text_from_docx(uploaded_file_t2)
                    elif raw_text_t2: text_to_process = raw_text_t2
                    try:
                        st.session_state["mcq_data_t2"] = parse_existing_mcqs(text_to_process, topics_input_t2, special_instructions, model_choice)
                        st.success("✨ Successfully reformatted!")
                    except Exception as e: st.error(f"Error parsing MCQs: {e}")

        if st.session_state["mcq_data_t2"]:
            with st.container(border=True):
                st.markdown("#### 👀 Preview & Edit Formatted Table")
                edited_data_t2 = st.data_editor(st.session_state["mcq_data_t2"], use_container_width=True, num_rows="dynamic", key="mcq_edit2")
            create_mcq_docx(edited_data_t2, "Formatted_Ready_MCQs.docx")
            with open("Formatted_Ready_MCQs.docx", "rb") as f:
                st.download_button("📥 Download Edited Word Document (.docx)", data=f, file_name="Formatted_Ready_MCQs.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
