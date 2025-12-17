# app.py - UPDATED FOR NEW JudgeAgent
import streamlit as st
import sys
import os
import uuid
from datetime import datetime
from gtts import gTTS
import io

# ======================
# PATH SETUP
# ======================
current_dir = os.getcwd()
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'agents'))
sys.path.append(os.path.join(current_dir, 'rag'))
sys.path.append(os.path.join(current_dir, 'models'))

# ======================
# TEXT TO SPEECH
# ======================
def speak_text(text: str, role: str):
    if not text or not st.session_state.get("voice_enabled", True):
        return
    try:
        tts = gTTS(text=f"{role} says. {text}", lang="en")
        audio = io.BytesIO()
        tts.write_to_fp(audio)
        audio.seek(0)
        st.audio(audio, format="audio/mp3")
    except Exception as e:
        st.warning(f"Voice error: {e}")

# ======================
# IMPORT MODULES
# ======================
try:
    from rag.fact_witness import fact_witness_answer
    from rag.db import init_db
except Exception as e:
    st.error(f"RAG import error: {e}")
    fact_witness_answer = None

try:
    from llm_openrouter import lc_llm
except Exception as e:
    st.error(f"LLM import error: {e}")
    lc_llm = None

try:
    from agents.debate_pipeline import DebatePipeline
    from models.pydantic_models import JudgementModel
except Exception as e:
    st.error(f"Agent import error: {e}")
    DebatePipeline = None

# ======================
# INITIALIZE DATABASE
# ======================
@st.cache_resource
def initialize_database():
    try:
        init_db()
        return True
    except:
        return False

db_initialized = initialize_database()

# ======================
# STREAMLIT UI
# ======================
st.set_page_config(page_title="AI Traffic Court", page_icon="⚖️", layout="wide")

# SESSION STATE
for key, default in {
    'evidence': [],
    'case_text': "",
    'case_id': "",
    'judgement': None,
    'debate_log': [],
    'rounds': 2,
    'voice_enabled': True
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("⚖️ AI Traffic Courtroom")
st.markdown("### Law-Validated Judicial System")

# ======================
# SIDEBAR
# ======================
with st.sidebar:
    st.header("🔧 System Status")
    st.checkbox("🔊 Enable Courtroom Voice", key="voice_enabled")
    st.metric("Database", "✅ Ready" if db_initialized else "❌ Offline")

    st.markdown("---")
    st.header("📁 Evidence Management")
    manual = st.text_area("Add Evidence")
    if st.button("➕ Add Evidence") and manual:
        st.session_state.evidence.append({
            "text": manual,
            "score": 0.9,
            "source": "Manual"
        })
        st.rerun()

    st.markdown("---")
    st.header("⚙️ Debate Settings")
    st.session_state.rounds = st.slider("Rounds", 1, 3, st.session_state.rounds)

# ======================
# MAIN
# ======================
col1, col2 = st.columns([3, 2])

with col1:
    st.header("📝 Case Details")
    case_text = st.text_area("Case Facts", height=160, value=st.session_state.case_text)
    st.session_state.case_text = case_text

    case_id = st.text_input("Manual Case ID", value=st.session_state.case_id)
    st.session_state.case_id = case_id

    offence = st.text_input("Offence / Violation Type", value="speeding")

with col2:
    st.header("⚖️ Court Control")
    ready = all([lc_llm, DebatePipeline, case_text.strip(), case_id.strip()])
    st.success("Ready" if ready else "Waiting")

    if st.button("🚀 Start Court", disabled=not ready):
        pipeline = DebatePipeline(llm=lc_llm, debate_id=case_id)
        for ev in st.session_state.evidence:
            pipeline.submit_evidence(ev)

        judgement = pipeline.run(
            case_facts=case_text,
            case_id=case_id,
            offence=offence,
            rounds=st.session_state.rounds
        )
        st.session_state.judgement = judgement
        st.session_state.debate_log = pipeline.hearing_log
        st.rerun()

# ======================
# RESULTS
# ======================
if st.session_state.judgement:
    j = st.session_state.judgement
    st.markdown("---")
    st.header("⚖️ Final Verdict")
    speak_text(j.verdict, "Judge")
    st.success(j.verdict)

    st.subheader("Reasoning")
    st.write(j.reasoning)
    speak_text(j.reasoning, "Judge")

    st.subheader("Scores")
    st.metric("Prosecution", j.prosecution_score)
    st.metric("Defense", j.defense_score)

    st.subheader("📊 Analysis")
    st.write("**Confidence / Final Score:**", j.rubric_scores.get("final_score", 0))
    st.write("**Rubric Scores:**")
    for k, v in j.rubric_scores.items():
        st.write(f"{k}: {v}/100")

    if st.button("🔄 New Case"):
        for k in ['evidence', 'case_text', 'case_id', 'judgement', 'debate_log']:
            st.session_state[k] = [] if k == 'evidence' else "" if k=='case_id' else None
        st.rerun()
