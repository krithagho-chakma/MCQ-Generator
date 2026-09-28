import streamlit as st
import google.generativeai as genai
import json
import pymupdf4llm
import pypandoc
import os
import PyPDF2
from docx import Document

# --- 3. HELPER FUNCTIONS ---
def extract_text_from_pdf(pdf_file):
    with open("temp.pdf", "wb") as f:
        f.write(pdf_file.read())
    text = pymupdf4llm.to_markdown("temp.pdf")
    os.remove("temp.pdf")
    return text

def extract_text_from_docx(docx_file):
    with open("temp.docx", "wb") as f:
        f.write(docx_file.read())
    # pypandoc reads the docx and converts native Word equations to $LaTeX$
    text = pypandoc.convert_file("temp.docx", "markdown")
    os.remove("temp.docx")
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

    CRITICAL INSTRUCTION FOR MATH AND EQUATIONS:
    If the source text contains mathematical equations, chemical formulas, or physics expressions, you MUST preserve them using standard LaTeX format. Use $ for inline math (e.g., $E=mc^2$) and $$ for display math. Do NOT use plain text approximations.
    
    CRITICAL INSTRUCTIONS FOR DIFFICULTY LEVEL:
    You must generate EXACTLY:
    - {num_easy} questions where "difficulty_level" is "Easy"
    - {num_medium} questions where "difficulty_level" is "Medium"
    - {num_hard} questions where "difficulty_level" is "Hard"
    Do not use any other words for difficulty level.

    CRITICAL INSTRUCTION FOR THE 'topics' COLUMN FIELD:
    Here is the list of allowed topic names: {user_topics}
    For the "topics" field in each question object, you MUST select EXACTLY ONE topic from the list above that best fits the generated question. Do not invent any new topics.
    DO NOT include sequence identifiers like '1.1', '2.1', etc. in the topic field.

    CRITICAL INSTRUCTION FOR 'solution_body':
    The "solution_body" field MUST follow this exact 2-line format:
    Line 1: The exact text of the correct option (DO NOT include sequence identifiers like 'A.', 'B.', 'Option A', '১.', etc.). Place an Enter at the end of the line.
    Line 2: A clear, detailed explanation of why this answer is correct. Always start with the line 'ব্যাখ্যা:'

    Example format for solution_body:
    "ইনপুট, প্রসেসিং, আউটপুট, মেমোরি ও কন্ট্রোল ইউনিট
    ব্যাখ্যা: কম্পিউটারের কাজ করার মূল পদ্ধতি হলো তথ্য গ্রহণ, প্রসেসিং, প্রদর্শন ও সংরক্ষণ করা।"

    Output the result STRICTLY as a JSON array of objects.
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

    CRITICAL INSTRUCTION FOR MATH AND EQUATIONS:
    If the source text contains mathematical equations, chemical formulas, or physics expressions, you MUST preserve them using standard LaTeX format. Use $ for inline math (e.g., $E=mc^2$) and $$ for display math. Do NOT use plain text approximations.

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
    # Build an HTML table. Pandoc handles HTML-to-Word conversions flawlessly.
    html = "<h1>Generated MCQs</h1>\n<table border='1'>\n"
    html += "<tr><th>Sl no.</th><th>Question Title</th><th>Option A</th><th>Option B</th><th>Option C</th><th>Option D</th><th>Solution Body</th><th>Correct Option</th><th>Subject</th><th>Chapter</th><th>Topics</th><th>Question Category</th><th>Difficulty Level</th></tr>\n"
    
    for mcq in mcq_data:
        html += "<tr>"
        html += f"<td>{mcq.get('sl_no', '')}</td>"
        html += f"<td>{mcq.get('question_title', '')}</td>"
        html += f"<td>{mcq.get('A', '')}</td>"
        html += f"<td>{mcq.get('B', '')}</td>"
        html += f"<td>{mcq.get('C', '')}</td>"
        html += f"<td>{mcq.get('D', '')}</td>"
        
        # Replace python newline characters with HTML breaks for the 2-line solution body
        sol_body = str(mcq.get('solution_body', '')).replace('\n', '<br>')
        html += f"<td>{sol_body}</td>"
        
        html += f"<td>{mcq.get('correct_option', '')}</td>"
        html += f"<td>{mcq.get('subject', '')}</td>"
        html += f"<td>{mcq.get('chapter', '')}</td>"
        html += f"<td>{mcq.get('topics', '')}</td>"
        html += f"<td>{mcq.get('question_category', '')}</td>"
        html += f"<td>{mcq.get('difficulty_level', '')}</td>"
        html += "</tr>\n"
    
    html += "</table>"
    
    # format='html+tex_math_dollars' tells Pandoc to render the HTML table but also parse $x^2$ as equations
    pypandoc.convert_text(html, 'docx', format='html+tex_math_dollars', outputfile=output_filename)
def run_mcq_interface(model_choice, api_key_input):
    # Initialize session state for API Key and Table Data
    if "user_api_key" not in st.session_state:
        st.session_state["user_api_key"] = ""
    if "mcq_data_t1" not in st.session_state:
        st.session_state["mcq_data_t1"] = None
    if "mcq_data_t2" not in st.session_state:
        st.session_state["mcq_data_t2"] = None
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
