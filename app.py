import streamlit as st
import google.generativeai as genai
from datetime import datetime
import hashlib

# ────────────────────────────────────────────────
#  Page config & DARK aesthetic styling with background
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="Curriculum Designer",
    page_icon="📚✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark theme + background image
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: linear-gradient(rgba(15, 17, 23, 0.75), rgba(15, 17, 23, 0.85)),
                    url('https://images.unsplash.com/photo-1506905925346-21bda4d32df4?ixlib=rb-4.0.3&auto=format&fit=crop&w=2400&q=80') center center / cover no-repeat fixed !important;
        color: #e2e8f0 !important;
    }

    .main .block-container {
        padding-top: 2.5rem;
        padding-bottom: 4rem;
        max-width: 1200px;
        background: rgba(15, 17, 23, 0.65);
        border-radius: 16px;
        backdrop-filter: blur(6px);
    }

    h1, h2, h3 {
        color: #c7d2fe !important;
    }

    .stChatMessage {
        border-radius: 16px !important;
        padding: 1rem 1.2rem !important;
        margin: 1rem 0 !important;
        backdrop-filter: blur(4px);
    }

    .stChatMessage.user {
        background: rgba(30, 41, 59, 0.85) !important;
        border: 1px solid #334155;
    }

    .stChatMessage.assistant {
        background: rgba(30, 41, 59, 0.92) !important;
        border: 1px solid #475569;
        box-shadow: 0 4px 16px rgba(0,0,0,0.5);
    }

    .stChatInput > div > div {
        background: rgba(30, 41, 59, 0.9) !important;
        border: 1px solid #475569 !important;
        color: #e2e8f0 !important;
        border-radius: 9999px !important;
    }

    .sidebar .sidebar-content {
        background: rgba(17, 24, 39, 0.92) !important;
        border-right: 1px solid #1e293b !important;
        backdrop-filter: blur(8px);
    }

    hr {
        border-top: 1px solid #334155 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
#  Simple login system
# ────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Hardcoded credentials (CHANGE THESE in production!)
VALID_USERNAME = "teacher"
VALID_PASSWORD_HASH = hashlib.sha256("curriculum2025".encode()).hexdigest()

if not st.session_state.logged_in:
    st.title("Welcome to Curriculum Designer")
    st.markdown("Please sign in to continue")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True, type="primary")

            if submit:
                if username == VALID_USERNAME:
                    input_hash = hashlib.sha256(password.encode()).hexdigest()
                    if input_hash == VALID_PASSWORD_HASH:
                        st.session_state.logged_in = True
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Incorrect password")
                else:
                    st.error("User not found")

    st.caption("Demo: username = teacher | password = curriculum2025")
    st.stop()

# ────────────────────────────────────────────────
#  Logout function
# ────────────────────────────────────────────────
def logout():
    st.session_state.logged_in = False
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ────────────────────────────────────────────────
#  API Key
# ────────────────────────────────────────────────
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = st.text_input("🔑 Gemini API Key", type="password", placeholder="Enter your key...")

if not GEMINI_API_KEY:
    st.warning("Please provide your Gemini API key → https://aistudio.google.com/app/apikey")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

# ────────────────────────────────────────────────
#  Full System Prompt
# ────────────────────────────────────────────────
SYSTEM_PROMPT = """You are Curriculum Designer — a friendly, professional, and structured education expert.

Your goal: Help teachers, tutors & educators create high-quality, customized curricula.

Follow this strict workflow:
1. Greet and ask for these details (one by one or together):
   - Subject / Topic
   - Grade / Age level
   - Duration (weeks / months / total hours)
   - Main learning objectives or goals
   - Any special requirements (project-based, inclusive, exam-oriented, language, etc.)

2. Once you have enough info, create a complete curriculum plan using clear markdown:
   - Title & Overview
   - SMART learning objectives
   - Unit / Week-by-week breakdown (topics + subtopics + estimated time)
   - Teaching & learning activities
   - Assessment methods
   - Resources & materials
   - Differentiation / adaptations for diverse learners

3. Always format output beautifully with headings, bullets, tables when useful.
4. After presenting the plan → ask: "Would you like to modify anything? Add/remove units? Change focus? Make it more detailed?"

Be encouraging, patient, and precise. Use simple language unless the user asks for academic tone."""

# ────────────────────────────────────────────────
#  Sidebar
# ────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/000000/open-book.png", width=72)
    st.title("Curriculum Designer")
    st.caption("Logged in")

    model_options = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash", "gemini-2.5-pro"]
    selected_model = st.selectbox("Model", model_options, index=2)

    if st.button("🧹 New Conversation", use_container_width=True):
        st.session_state.messages = []
        if "notebook_content" in st.session_state:
            del st.session_state.notebook_content
        st.rerun()

    if st.button("🚪 Logout", use_container_width=True):
        logout()

    st.markdown("---")

    # Notebook
    st.subheader("📝 Notebook")

    if "notebook_content" not in st.session_state:
        st.session_state.notebook_content = "# My Curriculum Notes\n\nStart writing or let the AI help..."

    edited_notes = st.text_area(
        "Notes (edit freely)",
        value=st.session_state.notebook_content,
        height=300,
        key="notebook_editor"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✨ Summarize Chat", use_container_width=True):
            with st.spinner("Summarizing..."):
                chat_summary = "\n".join([f"**{m['role']}**: {m['content'][:300]}..." for m in st.session_state.messages[-8:]])
                prompt = f"Summarize the following curriculum discussion concisely in markdown notes format:\n\n{chat_summary}"
                response = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
                st.session_state.notebook_content += f"\n\n## Summary from Chat\n{response.text}"
                st.rerun()

    with col2:
        if st.button("➕ Expand Notes", use_container_width=True):
            topic = st.text_input("Topic to expand", key="expand_topic")
            if topic and st.button("Generate", key="generate_expand"):
                with st.spinner("Generating..."):
                    last_msg = st.session_state.messages[-1]["content"] if st.session_state.messages else ""
                    prompt = f"Create well-structured markdown notes on: '{topic}'\nSuitable for curriculum revision.\nContext: {last_msg[:500]}..."
                    response = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
                    st.session_state.notebook_content += f"\n\n## {topic}\n{response.text}"
                    st.rerun()

    st.download_button(
        "Download Notes (.md)",
        data=st.session_state.notebook_content,
        file_name="curriculum_notes.md",
        mime="text/markdown",
        use_container_width=True
    )

# ────────────────────────────────────────────────
#  Main content
# ────────────────────────────────────────────────
@st.cache_resource
def get_model(model_name: str):
    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_PROMPT
    )

model = get_model(selected_model)

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "model",
        "content": "Hello! 👋 I'm **Curriculum Designer**.\n\nTell me about the curriculum you'd like to create:\n• Subject / Topic?\n• Grade / Age level?\n• Duration?\n• Goals?\n• Special requirements?\n\nReady when you are! 🚀"
    })

for msg in st.session_state.messages:
    display_role = "assistant" if msg["role"] == "model" else "user"
    with st.chat_message(display_role):
        st.markdown(msg["content"])

# User input
if prompt := st.chat_input("Describe the curriculum you need..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Designing..."):
            gemini_history = []
            for m in st.session_state.messages[:-1]:
                role = "model" if m["role"] in ("assistant", "model") else "user"
                gemini_history.append({"role": role, "parts": [m["content"]]})

            chat = model.start_chat(history=gemini_history)
            response = chat.send_message(prompt)
            full_response = response.text

            st.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})