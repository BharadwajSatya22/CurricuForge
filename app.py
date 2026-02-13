import streamlit as st
import google.generativeai as genai
import hashlib
import requests
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from io import BytesIO
import json
import os
from google.api_core.exceptions import ResourceExhausted

# ────────────────────────────────────────────────
#  Page config & DARK aesthetic styling
# ────────────────────────────────────────────────
st.set_page_config(
    page_title="CurricuForge: Curriculum Designer",
    page_icon="📚✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif; }

    .stApp {
        background: linear-gradient(rgba(15,17,23,0.78), rgba(15,17,23,0.88)),
                    url('https://images.unsplash.com/photo-1506905925346-21bda4d32df4?ixlib=rb-4.0.3&auto=format&fit=crop&w=2400&q=80') center/cover fixed !important;
        color: #e2e8f0 !important;
    }

    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3.5rem;
        max-width: 1200px;
        background: rgba(15,17,23,0.68);
        border-radius: 16px;
        backdrop-filter: blur(6px);
    }

    h1, h2, h3 { color: #c7d2fe !important; }

    .stChatMessage {
        border-radius: 16px !important;
        padding: 1rem 1.2rem !important;
        margin: 1rem 0 !important;
        backdrop-filter: blur(4px);
    }

    .stChatMessage.user {
        background: rgba(30,41,59,0.85) !important;
        border: 1px solid #334155;
    }

    .stChatMessage.assistant {
        background: rgba(30,41,59,0.92) !important;
        border: 1px solid #475569;
        box-shadow: 0 4px 16px rgba(0,0,0,0.5);
    }

    .stChatInput > div > div {
        background: rgba(30,41,59,0.9) !important;
        border: 1px solid #475569 !important;
        color: #e2e8f0 !important;
        border-radius: 9999px !important;
    }

    .sidebar .sidebar-content {
        background: rgba(17,24,39,0.92) !important;
        border-right: 1px solid #1e293b !important;
        backdrop-filter: blur(8px);
    }

    hr { border-top: 1px solid #334155 !important; }
    </style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────
#  User management (multi-user support)
# ────────────────────────────────────────────────
USERS_FILE = "users.json"

def load_users():
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        else:
            default = {"teacher": hashlib.sha256("curriculum2025".encode()).hexdigest()}
            with open(USERS_FILE, "w") as f:
                json.dump(default, f, indent=4)
            return default
    except Exception as e:
        st.error(f"Error loading users: {e}")
        return {}

def save_users(users):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=4)
    except Exception as e:
        st.error(f"Error saving users: {e}")

users = load_users()

# ────────────────────────────────────────────────
#  Login / Register
# ────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Welcome to CurricuForge: Curriculum Designer")
    st.markdown("Please sign in or register")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True, type="primary"):
                if username in users and users[username] == hashlib.sha256(password.encode()).hexdigest():
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Logged in!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")

    with tab2:
        with st.form("register"):
            new_username = st.text_input("New Username")
            new_password = st.text_input("New Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("Register", use_container_width=True, type="primary"):
                if new_password != confirm:
                    st.error("Passwords do not match")
                elif new_username in users:
                    st.error("Username taken")
                elif not new_username or not new_password:
                    st.error("Fields cannot be empty")
                else:
                    users[new_username] = hashlib.sha256(new_password.encode()).hexdigest()
                    save_users(users)
                    st.session_state.logged_in = True
                    st.session_state.username = new_username
                    st.success("Registered & logged in!")
                    st.rerun()

    st.caption("Demo: teacher / curriculum2025")
    st.stop()

# ────────────────────────────────────────────────
#  Logout
# ────────────────────────────────────────────────
def logout():
    st.session_state.logged_in = False
    for k in list(st.session_state.keys()):
        if k != "logged_in":
            del st.session_state[k]
    st.rerun()

# ────────────────────────────────────────────────
#  API Key
# ────────────────────────────────────────────────
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = st.text_input("🔑 Gemini API Key", type="password", placeholder="Enter your key...")

if not GEMINI_API_KEY:
    st.warning("Enter your Gemini API key → https://aistudio.google.com/app/apikey")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

# ────────────────────────────────────────────────
#  System Prompt
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
    st.title("CurricuForge")
    st.caption("Dark mode • Powered by Gemini")
    st.write(f"Welcome, {st.session_state.get('username', 'User')}!")

    model_options = [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-pro"
    ]
    selected_model = st.selectbox("Model", model_options, index=0)

    if st.button("🧹 New Conversation", use_container_width=True):
        for key in ["messages", "notebook_content", "curriculum"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    if st.button("🚪 Logout", use_container_width=True):
        logout()

    st.markdown("---")
    st.subheader("📝 Notebook")

    if "notebook_content" not in st.session_state:
        st.session_state.notebook_content = "# My Curriculum Notes\n\nStart writing..."

    st.session_state.notebook_content = st.text_area(
        "Notes",
        value=st.session_state.notebook_content,
        height=300,
        key="notebook_editor"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✨ Summarize Chat"):
            if st.session_state.get("messages"):
                with st.spinner("Summarizing..."):
                    summary_text = "\n".join(
                        f"**{m['role']}**: {m.get('parts', [m.get('content', '')])[0][:250]}..."
                        for m in st.session_state.messages[-10:]
                    )
                    try:
                        model_sum = genai.GenerativeModel("gemini-2.5-flash-lite")
                        resp = model_sum.generate_content(
                            f"Summarize this curriculum discussion concisely in markdown:\n\n{summary_text}"
                        )
                        st.session_state.notebook_content += f"\n\n## Chat Summary\n{resp.text}"
                        st.rerun()
                    except ResourceExhausted:
                        st.error("Quota limit reached. Try again later or use a different key.")
                    except Exception as e:
                        st.error(f"Summary failed: {e}")
            else:
                st.info("No chat history to summarize.")

    with col2:
        if st.button("➕ Add Section"):
            topic = st.text_input("Topic to expand", key="expand_topic_temp")
            if topic and st.button("Generate", key="gen_expand"):
                with st.spinner("Generating..."):
                    last = ""
                    if st.session_state.get("messages"):
                        last_msg = st.session_state.messages[-1]
                        last = last_msg.get("parts", [last_msg.get("content", "")])[0][:400]
                    try:
                        model_add = genai.GenerativeModel("gemini-2.5-flash-lite")
                        resp = model_add.generate_content(
                            f"Create clean markdown notes on: '{topic}'\nContext: {last}"
                        )
                        st.session_state.notebook_content += f"\n\n## {topic}\n{resp.text}"
                        st.rerun()
                    except ResourceExhausted:
                        st.error("Quota limit reached. Try again later.")
                    except Exception as e:
                        st.error(f"Generation failed: {e}")

    st.download_button(
        "Download Notes (.md)",
        st.session_state.notebook_content,
        "curriculum_notes.md",
        "text/markdown",
        use_container_width=True
    )

# ────────────────────────────────────────────────
#  Model & Chat Setup
# ────────────────────────────────────────────────
@st.cache_resource
def get_model(model_name: str):
    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_PROMPT
    )

model = get_model(selected_model)

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "model",
        "parts": ["Hello! 👋 I'm **Curriculum Designer**.\n\nWhat curriculum would you like to create?\n"
                  "• Subject / Topic?\n• Grade / Age?\n• Duration?\n• Goals?\n• Special needs?\n\nReady! 🚀"]
    }]

for msg in st.session_state.messages:
    role = "assistant" if msg["role"] == "model" else "user"
    with st.chat_message(role):
        content = msg["parts"][0] if "parts" in msg else msg.get("content", "")
        st.markdown(content)

# ────────────────────────────────────────────────
#  Quick Curriculum Generator
# ────────────────────────────────────────────────
st.markdown("### Quick Curriculum Generator")
col1, col2 = st.columns(2)

with col1:
    skill = st.text_input("Skill / Domain", "Machine Learning")
    level = st.selectbox("Level", ["Diploma", "BTech", "Masters", "Certification"])
    semesters = st.slider("Semesters", 1, 8, 4)

with col2:
    weekly_hours = st.slider("Weekly Hours", 10, 40, 20)
    industry = st.text_input("Industry Focus", "AI & Data Science")

if st.button("Generate Quick Curriculum"):
    if not GEMINI_API_KEY:
        st.error("Enter API key first.")
    else:
        prompt = f"""
Generate structured curriculum in pure JSON.

Skill: {skill}
Level: {level}
Semesters: {semesters}
Weekly Hours: {weekly_hours}
Focus: {industry}

Return ONLY valid JSON:

{{
  "program_title": "",
  "semesters": [
    {{
      "semester": 1,
      "courses": [
        {{
          "course_name": "",
          "credits": "",
          "topics": [""],
          "learning_outcomes": [""]
        }}
      ]
    }}
  ]
}}
"""

        with st.spinner("Generating..."):
            try:
                url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}]
                }
                resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
                result = resp.json()

                if "error" in result:
                    st.error(f"API Error: {result['error']['message']}")
                else:
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
                    text = text.replace("```json", "").replace("```", "").strip()
                    curriculum = json.loads(text)
                    st.session_state.curriculum = curriculum
                    st.success("Generated!")
            except Exception as e:
                st.error(f"Failed: {str(e)}")

# Display curriculum
if "curriculum" in st.session_state and st.session_state.curriculum:
    curriculum = st.session_state.curriculum
    st.header(curriculum.get("program_title", "Generated Curriculum"))

    for sem in curriculum.get("semesters", []):
        with st.expander(f"Semester {sem.get('semester')}"):
            for course in sem.get("courses", []):
                st.subheader(course.get("course_name", "Course"))
                st.write("Credits:", course.get("credits", "—"))
                st.markdown("**Topics:**")
                for t in course.get("topics", []):
                    st.write(f"- {t}")
                st.markdown("**Learning Outcomes:**")
                for o in course.get("learning_outcomes", []):
                    st.write(f"- {o}")
                st.markdown("---")

    def generate_pdf(data):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []
        elements.append(Paragraph(data.get("program_title", ""), styles["Title"]))
        elements.append(Spacer(1, 12))

        for sem in data.get("semesters", []):
            elements.append(Paragraph(f"Semester {sem.get('semester')}", styles["Heading2"]))
            elements.append(Spacer(1, 10))
            for course in sem.get("courses", []):
                elements.append(Paragraph(course.get("course_name", ""), styles["Heading3"]))
                elements.append(Paragraph(f"Credits: {course.get('credits', '')}", styles["Normal"]))
                elements.append(Spacer(1, 5))
                elements.append(Paragraph("Topics:", styles["Normal"]))
                for t in course.get("topics", []):
                    elements.append(Paragraph(f"- {t}", styles["Normal"]))
                elements.append(Spacer(1, 5))
                elements.append(Paragraph("Learning Outcomes:", styles["Normal"]))
                for o in course.get("learning_outcomes", []):
                    elements.append(Paragraph(f"- {o}", styles["Normal"]))
                elements.append(Spacer(1, 15))

        doc.build(elements)
        buffer.seek(0)
        return buffer

    pdf = generate_pdf(curriculum)

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button("Download PDF", pdf, "curriculum.pdf", "application/pdf", use_container_width=True)
    with col_d2:
        st.download_button("Download JSON", json.dumps(curriculum, indent=2), "curriculum.json", "application/json", use_container_width=True)

# ────────────────────────────────────────────────
#  Chat Input
# ────────────────────────────────────────────────
if prompt := st.chat_input("Describe the curriculum you need..."):
    st.session_state.messages.append({"role": "user", "parts": [prompt]})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                history = []
                for m in st.session_state.messages[:-1]:
                    role = "model" if m["role"] == "model" else "user"
                    content = m["parts"][0] if "parts" in m else m.get("content", "")
                    history.append({"role": role, "parts": [content]})

                chat = model.start_chat(history=history)
                response = chat.send_message(prompt)
                full_text = response.text
                st.markdown(full_text)
                st.session_state.messages.append({"role": "model", "parts": [full_text]})
            except ResourceExhausted:
                st.error("**Quota limit reached** (429 error).\n\n"
                         "Free tier is usually ~20 requests/day for gemini-2.5-flash.\n"
                         "Solutions:\n"
                         "• Wait until tomorrow (quota reset)\n"
                         "• Create new API key in new project: https://aistudio.google.com/app/apikey\n"
                         "• Try gemini-2.5-flash-lite (often higher limit)\n"
                         "• Add billing for much higher limits (cheap)")
            except Exception as e:
                st.error(f"Error: {str(e)}")