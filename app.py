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
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        
        /* 1. Space between the tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 15px;
        }
        
        /* 2. Base styling for all tabs (Bigger, bolder, structural) */
        .stTabs [data-baseweb="tab"] {
            height: 55px;
            white-space: pre-wrap;
            background-color: rgba(128, 128, 128, 0.05); /* Subtle grey background for inactive tabs */
            border-radius: 8px 8px 0px 0px; /* Rounded top corners like a folder */
            font-size: 18px; /* Larger font */
            font-weight: 700;
            padding: 10px 24px;
            border: 1px solid rgba(128, 128, 128, 0.2);
            border-bottom: none;
            transition: all 0.2s ease-in-out;
        }
        
        /* 3. Hover effect for inactive tabs */
        .stTabs [data-baseweb="tab"]:hover {
            background-color: rgba(128, 128, 128, 0.15);
        }

        /* 4. Custom Styling for Tab 1 (✨ Generate New MCQs) - Green Theme */
        .stTabs [data-baseweb="tab"]:nth-child(1)[aria-selected="true"] {
            background-color: rgba(76, 175, 80, 0.1) !important;
            border-top: 4px solid #4CAF50 !important;
            border-left: 1px solid #4CAF50 !important;
            border-right: 1px solid #4CAF50 !important;
            color: #4CAF50 !important;
        }

        /* 5. Custom Styling for Tab 2 (📋 Format Existing) - Blue Theme */
        .stTabs [data-baseweb="tab"]:nth-child(2)[aria-selected="true"] {
            background-color: rgba(33, 150, 243, 0.1) !important;
            border-top: 4px solid #2196F3 !important;
            border-left: 1px solid #2196F3 !important;
            border-right: 1px solid #2196F3 !important;
            color: #2196F3 !important;
        }
        
        /* Remove Streamlit's default red bottom border on active tabs */
        .stTabs [data-baseweb="tab-border"] {
            display: none;
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
    
    *Note: The Gemini 3.1 Flash model is recommended to use for its higher token count! You may use other models as well. But, they have very lower free tier limit.*
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
