import streamlit as st
import google.generativeai as genai
from mcq_engine import run_mcq_interface
from cq_engine import run_cq_interface

# --- PAGE CONFIG & CUSTOM CSS ---
st.set_page_config(page_title="Edu Automation Engine", page_icon="📚", layout="wide")

st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        #header {visibility: hidden;}
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

# --- SIDEBAR & SESSION STATE ---
if "user_api_key" not in st.session_state:
    st.session_state["user_api_key"] = ""

st.sidebar.title("⚙️ Configuration")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio("🔀 Select Engine Mode:", ["📚 MCQ Engine", "✍️ CQ Engine"])
st.sidebar.markdown("---")

# --- NEW: Interactive API Key Guide ---
api_key_input = st.sidebar.text_input(
    "🔑 Gemini API Key:", 
    value=st.session_state["user_api_key"], 
    type="password",
    help="Enter your Google AI Studio API key to power the engine."
)

with st.sidebar.expander("ℹ️ How to get a free API key?"):
    st.markdown("""
    **Step-by-step Guide:**
    1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
    2. Sign in with your standard Google account.
    3. Click the blue **Create API key** button.
    4. Select a project (or create a new one) and generate the key.
    5. **Copy** the generated key and **paste** it in the box above.
    
    *Note: The Gemini 3.7 Flash model provides up to 1,500 free requests per day!*
    """)

if api_key_input:
    st.session_state["user_api_key"] = api_key_input
    genai.configure(api_key=st.session_state["user_api_key"])
    st.sidebar.success("API Key Active")
else:
    st.sidebar.warning("API key required to proceed.")

# --- MAIN INTERFACE HEADER ---
st.title(app_mode.replace("🔀 Select Engine Mode:", ""))
st.markdown("Automate the generation and formatting of board-standard questions.")

with st.container(border=True):
    st.markdown("#### 🤖 Global AI Model Selection")
    model_choice = st.selectbox(
        "Select the Gemini engine for this task:",
        options=["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"],
        index=1,
        label_visibility="collapsed"
    )
    if model_choice == "gemini-3.8-flash": st.caption("⚠️ **Free Tier Limit:** 20 requests per day.")
    elif model_choice == "gemini-3.7-flash": st.caption("💡 **Free Tier Limit:** 1,500 requests per day. (Recommended)")
    elif model_choice == "gemini-3.6-flash": st.caption("🚫 **Free Tier Limit:** Requires Pay-As-You-Go account.")
    else: st.caption("✅ **Free Tier Limit:** 1,500 requests per day.")

st.markdown("<br>", unsafe_allow_html=True)

# --- MODULE ROUTING ---
if app_mode == "📚 MCQ Engine":
    run_mcq_interface(model_choice, api_key_input)
elif app_mode == "✍️ CQ Engine":
    run_cq_interface(model_choice, api_key_input)
