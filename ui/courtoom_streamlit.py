# app.py - COMPLETE WORKING VERSION
import streamlit as st
import sys
import os
import uuid
from datetime import datetime

# 🔊 NEW: TTS imports
from gtts import gTTS
import io

# ======================
# FIX 1: PATH SETUP
# ======================
current_dir = os.getcwd()
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, 'agents'))
sys.path.append(os.path.join(current_dir, 'rag'))
sys.path.append(os.path.join(current_dir, 'models'))

# ======================
# 🔊 NEW: SPEAK FUNCTION
# ======================
def speak_text(text: str, role: str):
    if not text:
        return
    if not st.session_state.get("voice_enabled", True):
        return

    tts = gTTS(text=f"{role} says. {text}", lang="en")
    audio = io.BytesIO()
    tts.write_to_fp(audio)
    audio.seek(0)
    st.audio(audio, format="audio/mp3")

# ======================
# FIX 2: IMPORT ALL YOUR MODULES
# ======================
try:
    from rag.fact_witness import fact_witness_answer
    from rag.retriever import retrieve
    from rag.db import init_db, get_conn
    print("✅ RAG modules imported")
except Exception as e:
    st.error(f"RAG import error: {e}")
    fact_witness_answer = None

try:
    from llm_openrouter import lc_llm
    print("✅ LLM imported")
except Exception as e:
    st.error(f"LLM import error: {e}")
    lc_llm = None

try:
    from agents.debate_pipeline import DebatePipeline
    from agents.prosecutor import ProsecutorAgent
    from agents.defense import DefenseAgent
    from agents.judge import JudgeAgent
    from agents.memory import MemoryManager
    from models.pydantic_models import JudgementModel
    print("✅ All agents imported")
except Exception as e:
    st.error(f"Agents import error: {e}")
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

# ======================
# SESSION STATE
# ======================
if 'evidence' not in st.session_state:
    st.session_state.evidence = []
if 'case_text' not in st.session_state:
    st.session_state.case_text = ""
if 'judgement' not in st.session_state:
    st.session_state.judgement = None
if 'debate_log' not in st.session_state:
    st.session_state.debate_log = []
if 'rounds' not in st.session_state:
    st.session_state.rounds = 2
# 🔊 NEW
if 'voice_enabled' not in st.session_state:
    st.session_state.voice_enabled = True

# ======================
# TITLE
# ======================
st.title("⚖️ AI Traffic Courtroom")
st.markdown("### Complete System with Database, RAG, and AI Agents")

# ======================
# SIDEBAR
# ======================
with st.sidebar:
    st.header("🔧 System Status")

    # 🔊 NEW: Voice toggle
    st.checkbox("🔊 Enable Courtroom Voice", value=True, key="voice_enabled")

    db_status = "✅ Ready" if db_initialized else "❌ Offline"
    st.metric("Database", db_status)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.write("RAG System")
        st.write("✅" if fact_witness_answer else "❌")
    with col2:
        st.write("AI LLM")
        st.write("✅" if lc_llm else "❌")
    with col3:
        st.write("Agents")
        st.write("✅" if DebatePipeline else "❌")

    st.markdown("---")
    st.header("⚙️ Debate Settings")
    st.session_state.rounds = st.slider("Debate Rounds", 1, 3, 2)

# ======================
# MAIN INTERFACE
# ======================
col1, col2 = st.columns([3, 2])

with col1:
    st.header("📝 Case Details")
    case_text = st.text_area("Case details:", height=150)
    st.session_state.case_text = case_text

with col2:
    st.header("🎮 Court Proceedings")

    system_ready = all([fact_witness_answer, lc_llm, DebatePipeline, case_text.strip()])

    if st.button("🚀 START AI COURT DEBATE", disabled=not system_ready):
        with st.spinner("Court is in session..."):
            debate_id = f"case_{uuid.uuid4().hex[:8]}"
            pipeline = DebatePipeline(llm=lc_llm, debate_id=debate_id)

            for ev in st.session_state.evidence:
                pipeline.submit_evidence(ev)

            judgement = pipeline.run(case_facts=case_text, rounds=st.session_state.rounds)

            st.session_state.judgement = judgement
            st.session_state.debate_log = pipeline.hearing_log
            st.session_state.debate_id = debate_id
            st.rerun()

# ======================
# DISPLAY RESULTS
# ======================
if st.session_state.judgement:
    st.markdown("---")
    st.header("⚖️ Court Judgement")

    judgement = st.session_state.judgement

    # 🔊 Judge speaks verdict
    speak_text(judgement.verdict, "Judge")

    tab1, tab2, tab3, tab4 = st.tabs(["📄 Judgement", "🗣️ Debate", "📊 Analysis", "🔍 Evidence"])

    with tab1:
        st.subheader("Judge's Legal Reasoning")
        st.write(judgement.reasoning)

        # 🔊 Judge speaks reasoning
        speak_text(judgement.reasoning, "Judge")

    with tab2:
        st.subheader("Complete Debate Transcript")
        for turn in st.session_state.debate_log:
            if turn['agent'] == 'prosecutor':
                st.markdown("##### 👨‍⚖️ Prosecutor")
                st.info(turn['text'])

                # 🔊 Prosecutor speaks
                speak_text(turn['text'], "Prosecutor")

            elif turn['agent'] == 'defense':
                st.markdown("##### 🛡️ Defense")
                st.success(turn['text'])

                # 🔊 Defense speaks
                speak_text(turn['text'], "Defense Lawyer")

            st.markdown("---")

    with tab3:
        st.subheader("Scoring Breakdown")
        if hasattr(judgement, 'rubric_scores'):
            for key, value in judgement.rubric_scores.items():
                st.write(f"{key}: {value}")

    with tab4:
        st.subheader("Evidence Considered")
        for ev in getattr(judgement, 'evidence_considered', []):
            st.write(ev.get("text", ""))

# ======================
# FOOTER
# ======================
st.caption("AI Traffic Courtroom | Voice Enabled | No Logic Changed")
