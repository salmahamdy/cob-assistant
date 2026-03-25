import re
import json
from datetime import datetime
from pathlib import Path

import streamlit as st

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="COB Assistant",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ---------- DATA LOADING ----------
BASE_DIR = Path(__file__).parent
KB_PATH = BASE_DIR / "data" / "knowledge_base.json"

with KB_PATH.open("r", encoding="utf-8") as f:
    KB = json.load(f)

FAQS = KB["faq"]
SERVICES = KB["services"]
APPOINTMENT_TYPES = KB["appointment_types"]
CONTACT = KB["contact"]
LOCATIONS = KB["locations"]
PRICING = KB["pricing"]
POLICIES = KB["policies"]
COMPANY = KB["company"]

INTENT_CONFIG = {
    "KB": {"label": "📚 Knowledge Base", "color": "#00c896", "bg": "rgba(0,200,150,0.08)"},
    "ACTION": {"label": "⚡ Booking Flow", "color": "#6c63ff", "bg": "rgba(108,99,255,0.08)"},
    "HUMAN": {"label": "🙋 Human Escalation", "color": "#ff6584", "bg": "rgba(255,101,132,0.08)"},
}

EXAMPLES = [
    "What services do you offer?",
    "How much does a consultation cost?",
    "I want to book an appointment",
    "Do you offer remote consultations?",
    "What are your office hours?",
    "I need to speak to a human agent",
]

STOPWORDS = {
    "a", "an", "the", "is", "are", "do", "you", "your", "to", "for", "of", "on", "in", "i", "me",
    "we", "our", "and", "or", "can", "how", "what", "when", "where", "please", "want", "need"
}


# ---------- HELPERS ----------
def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9@+\-:/ ]", " ", text.lower())).strip()


def tokens(text: str) -> set[str]:
    return {t for t in normalize_text(text).split() if t and t not in STOPWORDS}


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "booking" not in st.session_state:
        st.session_state.booking = {
            "active": False,
            "service": "",
            "date_time": "",
            "mode": "",
            "name": "",
            "email": "",
        }


def render_message(role: str, text: str, intent: str | None = None, booking: dict | None = None) -> None:
    avatar = "🤖" if role == "bot" else "👤"
    row_class = "bot" if role == "bot" else "user"

    intent_html = ""
    if intent in INTENT_CONFIG:
        cfg = INTENT_CONFIG[intent]
        intent_html = (
            f'<div class="intent-badge" style="background:{cfg["bg"]};color:{cfg["color"]};'
            f'border:1px solid {cfg["color"]}33">{cfg["label"]}</div><br>'
        )

    safe_text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    safe_text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", safe_text)
    safe_text = safe_text.replace("\n", "<br>")

    st.markdown(
        f"""
        <div class="chat-row {row_class}">
          <div class="msg-avatar-icon">{avatar}</div>
          <div class="bubble">{intent_html}{safe_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if booking:
        details = "".join(
            f'<div class="booking-row"><span class="booking-label">{k}:</span><strong>{v}</strong></div>'
            for k, v in booking.items()
        )
        st.markdown(
            f"""
            <div class="booking-card">
              <div class="booking-title">📋 Booking Request Confirmed</div>
              {details}
              <div style="margin-top:10px;font-size:12px;color:#00a070">
                ✉️ A team member can follow up at {booking.get('Email', 'your email')}.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if intent == "HUMAN":
        st.markdown(
            f"""
            <div class="escalation-card">
              <div class="esc-title">🙋 Human Support</div>
              📧 <strong>{CONTACT['email']}</strong><br>
              📞 Cairo: <strong>{CONTACT['phone_cairo']}</strong><br>
              📞 Dubai: <strong>{CONTACT['phone_dubai']}</strong><br>
              💬 {CONTACT['live_chat']}<br><br>
              <span style='font-size:12px;color:#c06070'>A human agent can handle complex billing, legal, or urgent cases.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def add_bot_message(text: str, intent: str, booking: dict | None = None) -> None:
    st.session_state.messages.append(
        {"role": "bot", "content": text, "intent": intent, "booking": booking}
    )


def start_booking() -> tuple[str, str, None]:
    st.session_state.booking["active"] = True
    return (
        "ACTION",
        "Sure — I can help with that. Which appointment type would you like?\n\n"
        + "\n".join(f"- {item}" for item in APPOINTMENT_TYPES),
        None,
    )


def detect_human_escalation(user_text: str) -> bool:
    lowered = normalize_text(user_text)
    triggers = [
        "human", "agent", "representative", "real person", "manager", "complaint",
        "billing dispute", "legal", "lawyer", "refund issue", "angry", "frustrated"
    ]
    return any(trigger in lowered for trigger in triggers)


def detect_booking_start(user_text: str) -> bool:
    lowered = normalize_text(user_text)
    return any(phrase in lowered for phrase in [
        "book", "appointment", "schedule", "meeting", "consultation", "discovery call"
    ])


def extract_email(text: str) -> str:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else ""


def looks_like_name(text: str) -> bool:
    txt = text.strip()
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,60}", txt)) and "@" not in txt


def booking_step_response(user_text: str) -> tuple[str, str, dict | None]:
    booking = st.session_state.booking
    cleaned = user_text.strip()
    lowered = normalize_text(user_text)

    if not booking["service"]:
        for item in APPOINTMENT_TYPES:
            if normalize_text(item) in lowered or any(tok in lowered for tok in normalize_text(item).split()):
                booking["service"] = item
                break
        if not booking["service"]:
            booking["service"] = cleaned
        return "ACTION", "Great. What date and time work best for you?", None

    if not booking["date_time"]:
        booking["date_time"] = cleaned
        return "ACTION", "Would you like this to be remote or in-person?", None

    if not booking["mode"]:
        if "remote" in lowered or "zoom" in lowered or "meet" in lowered or "online" in lowered:
            booking["mode"] = "Remote"
        elif "in person" in lowered or "in-person" in lowered or "office" in lowered:
            booking["mode"] = "In-person"
        else:
            booking["mode"] = cleaned.title()
        return "ACTION", "Perfect. Please share your full name.", None

    if not booking["name"]:
        if looks_like_name(cleaned):
            booking["name"] = cleaned
            return "ACTION", "Thanks. Lastly, what email should we use for the booking?", None
        return "ACTION", "Please send your full name so I can complete the booking request.", None

    if not booking["email"]:
        email = extract_email(cleaned)
        if not email:
            return "ACTION", "Please send a valid email address to finish the booking request.", None
        booking["email"] = email
        confirmed = {
            "Name": booking["name"],
            "Email": booking["email"],
            "Service": booking["service"],
            "Date & Time": booking["date_time"],
            "Mode": booking["mode"],
        }
        st.session_state.booking = {
            "active": False,
            "service": "",
            "date_time": "",
            "mode": "",
            "name": "",
            "email": "",
        }
        return "ACTION", "Your booking request is ready and has been summarized below.", confirmed

    return "ACTION", "Your booking request is already complete.", None


def kb_answer(user_text: str) -> str:
    q = normalize_text(user_text)
    q_tokens = tokens(user_text)

    if any(word in q for word in ["service", "offer", "provide"]):
        services_text = "\n".join(f"- **{name}**: {desc}" for name, desc in SERVICES.items())
        return f"We offer these services:\n{services_text}"

    if any(word in q for word in ["price", "pricing", "cost", "consultation", "retainer"]):
        return (
            f"Pricing highlights:\n"
            f"- Consultation sessions start at **{PRICING['consultation_sessions']}**\n"
            f"- {PRICING['project_pricing']}\n"
            f"- {PRICING['discovery_call']}\n"
            f"- Monthly retainers start at **{PRICING['retainer_packages']}**"
        )

    if any(word in q for word in ["location", "office", "hours", "open", "cairo", "dubai", "london"]):
        lines = []
        for office, details in LOCATIONS.items():
            lines.append(f"- **{office}**: {details['address']} — {details['hours']}")
        return "Here are our office locations and hours:\n" + "\n".join(lines)

    if any(word in q for word in ["cancel", "refund", "reschedule", "no show", "no-show"]):
        return (
            "Here is the cancellation and refund policy:\n"
            f"- {POLICIES['cancellation_refund'][0]}\n"
            f"- {POLICIES['cancellation_refund'][1]}\n"
            f"- {POLICIES['cancellation_refund'][2]}\n"
            f"- {POLICIES['cancellation_refund'][3]}"
        )

    if any(word in q for word in ["remote", "zoom", "meet", "online"]):
        return FAQS["remote_consultations"]

    if any(word in q for word in ["industry", "industries", "specialize"]):
        return f"We specialize in {', '.join(COMPANY['industries'])}."

    if any(word in q for word in ["project", "long", "timeline", "take"]):
        return FAQS["project_duration"]

    if any(word in q for word in ["contact", "email", "phone", "support"]):
        return (
            f"You can reach us at **{CONTACT['email']}**, call Cairo at **{CONTACT['phone_cairo']}**, "
            f"call Dubai at **{CONTACT['phone_dubai']}**, or use {CONTACT['live_chat']}."
        )

    scored_items = []
    searchable = {
        "about": COMPANY["about"],
        "services": " ".join(SERVICES.keys()),
        "pricing": " ".join(PRICING.values()),
        "locations": " ".join(v["address"] + " " + v["hours"] for v in LOCATIONS.values()),
        "appointment_types": " ".join(APPOINTMENT_TYPES),
        "faq_remote": FAQS["remote_consultations"],
        "faq_reschedule": FAQS["reschedule"],
        "faq_duration": FAQS["project_duration"],
    }
    for _, text in searchable.items():
        score = len(q_tokens & tokens(text))
        scored_items.append((score, text))

    scored_items.sort(reverse=True, key=lambda item: item[0])
    if scored_items and scored_items[0][0] > 0:
        return scored_items[0][1]

    return (
        "I can help with services, pricing, office hours, appointment types, booking, contact details, and policies. "
        "Please ask about one of those topics and I’ll answer directly."
    )


def generate_response(user_text: str) -> tuple[str, str, dict | None]:
    if st.session_state.booking["active"]:
        return booking_step_response(user_text)

    if detect_human_escalation(user_text):
        return (
            "HUMAN",
            "I’m routing this to human support. Please use the contact options below and include any relevant booking or billing details.",
            None,
        )

    if detect_booking_start(user_text):
        return start_booking()

    return "KB", kb_answer(user_text), None


# ---------- STYLES ----------
st.markdown(
    """
    <style>
      html, body, [class*="css"] { font-family: Inter, Arial, sans-serif; }
      .stApp { background: #0d0d14; }
      #MainMenu, footer, header { visibility: hidden; }
      .block-container { padding: 2rem 1.5rem 6rem; max-width: 780px; }
      .brand-bar {
        display: flex; align-items: center; gap: 14px; padding: 18px 22px; margin-bottom: 24px;
        background: #13131e; border: 1px solid #252535; border-radius: 18px;
      }
      .brand-avatar {
        width: 46px; height: 46px; border-radius: 14px; background: linear-gradient(135deg, #6c63ff, #ff6584);
        display: flex; align-items: center; justify-content: center; font-size: 22px; flex-shrink: 0;
      }
      .brand-name { font-weight: 800; font-size: 18px; color: #e8e8f0; }
      .brand-sub  { font-size: 12px; color: #7f7fb2; margin-top: 2px; }
      .brand-badge {
        margin-left: auto; background: rgba(108,99,255,0.15); border: 1px solid rgba(108,99,255,0.3);
        color: #6c63ff; font-size: 11px; font-weight: 700; padding: 4px 12px; border-radius: 20px;
      }
      .chat-row { display: flex; margin-bottom: 12px; gap: 10px; }
      .chat-row.user  { flex-direction: row-reverse; }
      .chat-row.bot   { flex-direction: row; }
      .msg-avatar-icon {
        width: 32px; height: 32px; border-radius: 10px; flex-shrink: 0; display: flex;
        align-items: center; justify-content: center; font-size: 16px;
      }
      .user .msg-avatar-icon { background: #252535; }
      .bot .msg-avatar-icon { background: linear-gradient(135deg,#6c63ff,#ff6584); }
      .bubble { max-width: 76%; padding: 12px 16px; border-radius: 16px; font-size: 14.5px; line-height: 1.65; }
      .user .bubble { background: #6c63ff; color: #fff; border-bottom-right-radius: 4px; }
      .bot .bubble { background: #181825; border: 1px solid #252535; color: #dcdce8; border-bottom-left-radius: 4px; }
      .intent-badge {
        display: inline-block; font-size: 10px; font-weight: 700; letter-spacing: 0.6px;
        padding: 2px 8px; border-radius: 20px; margin-bottom: 7px;
      }
      .booking-card {
        background: rgba(0,200,150,0.07); border: 1px solid rgba(0,200,150,0.22);
        border-radius: 14px; padding: 14px 16px; margin-top: 10px; font-size: 13.5px; color: #c8f7ed;
      }
      .booking-title { font-weight: 800; font-size: 14px; color: #00c896; margin-bottom: 10px; }
      .booking-row { margin: 4px 0; }
      .booking-label { color: #8f90b5; margin-right: 6px; }
      .escalation-card {
        background: rgba(255,101,132,0.07); border: 1px solid rgba(255,101,132,0.22);
        border-radius: 14px; padding: 14px 16px; margin-top: 10px; font-size: 13.5px; color: #f8c8d0;
      }
      .esc-title { font-weight: 800; color: #ff6584; margin-bottom: 10px; }
      .date-pill { text-align: center; color: #666685; font-size: 11.5px; letter-spacing: 0.4px; margin: 8px 0 18px; }
      [data-testid="stSidebar"] { background: #0f0f18 !important; border-right: 1px solid #1e1e2e; }
      .stChatInput textarea {
        background: #181825 !important; border: 1px solid #252535 !important; color: #e8e8f0 !important;
        border-radius: 14px !important;
      }
      .stChatInput button { background: #6c63ff !important; border-radius: 12px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- APP ----------
init_state()

with st.sidebar:
    st.markdown(
        """
        <div style='font-size:20px;font-weight:800;color:#e8e8f0;margin-bottom:4px'>🤖 COB Assistant</div>
        <div style='font-size:12px;color:#6d6d9b;margin-bottom:20px'>Free demo · no API key required</div>
        """,
        unsafe_allow_html=True,
    )
    st.success("Runs fully offline with Streamlit only.")
    st.markdown("### 💬 Capabilities")
    st.markdown(
        "- 📚 **KB Q&A** — services, pricing, policies, locations\n"
        "- 📅 **Book Appointment** — guided multi-turn flow\n"
        "- 🙋 **Human Escalation** — routes complex queries"
    )
    st.divider()
    st.markdown("### 🧪 Try These")
    for ex in EXAMPLES:
        if st.button(ex, use_container_width=True, key=f"ex_{ex}"):
            st.session_state["pending_input"] = ex
            st.rerun()
    st.divider()
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.booking = {
            "active": False,
            "service": "",
            "date_time": "",
            "mode": "",
            "name": "",
            "email": "",
        }
        st.rerun()

st.markdown(
    """
    <div class="brand-bar">
      <div class="brand-avatar">🤖</div>
      <div>
        <div class="brand-name">COB Assistant</div>
        <div class="brand-sub">● Online · Free local support demo</div>
      </div>
      <div class="brand-badge">FREE</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f'<div class="date-pill">Today · {datetime.now().strftime("%B %d, %Y")}</div>',
    unsafe_allow_html=True,
)

if not st.session_state.messages:
    render_message(
        "bot",
        "👋 **Welcome to COB Company Support!**\n\nI can answer questions about services, pricing, office hours, policies, and appointments — and I can also collect a booking request step by step.",
        "KB",
    )
else:
    for msg in st.session_state.messages:
        render_message(msg["role"], msg["content"], msg.get("intent"), msg.get("booking"))

user_text = st.session_state.pop("pending_input") if "pending_input" in st.session_state else None
typed = st.chat_input("Ask anything — or type 'book appointment'…")
if typed:
    user_text = typed

if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    render_message("user", user_text)

    intent, reply, booking = generate_response(user_text)
    add_bot_message(reply, intent, booking)
    render_message("bot", reply, intent, booking)
    st.rerun()
