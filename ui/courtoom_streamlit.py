# app.py - FULL UPDATED VERSION
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

# Initialize session state
for key, default in {
    'evidence': [],
    'case_text': "",
    'case_id': f"CASE-{uuid.uuid4().hex[:6].upper()}",
    'offence': "speeding",
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
# MAIN CASE INPUT
# ======================
col1, col2 = st.columns([3, 2])

with col1:
    st.header("📝 Case Details")
    st.session_state.case_id = st.text_input(
        "Case ID", value=st.session_state.case_id
    )
    st.session_state.offence = st.text_input(
        "Offence type", value=st.session_state.offence
    )
    st.session_state.case_text = st.text_area(
        "Case Facts", height=160, value=st.session_state.case_text
    )

with col2:
    st.header("⚖️ Court Control")
    ready = all([lc_llm, DebatePipeline, st.session_state.case_text.strip()])
    st.success("✅ Ready" if ready else "⚠️ Waiting")

    if st.button("🚀 Start Court", disabled=not ready):
        pipeline = DebatePipeline(llm=lc_llm, debate_id=st.session_state.case_id)
        for ev in st.session_state.evidence:
            pipeline.submit_evidence(ev)

        judgement = pipeline.run(
            case_facts=st.session_state.case_text,
            case_id=st.session_state.case_id,
            offence=st.session_state.offence,
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
    if "Confirmed" in j.verdict or "Guilty" in j.verdict.upper():
        st.error(j.verdict)
    else:
        st.success(j.verdict)

    st.subheader("Reasoning")
    st.write(j.reasoning)
    speak_text(j.reasoning, "Judge")

    st.subheader("Scores")
    st.metric("Prosecution", j.prosecution_score)
    st.metric("Defense", j.defense_score)

    # ======================
    # Tabs: Judgement, Debate, Analysis, Evidence
    # ======================
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Judgement", "🗣️ Debate", "📊 Analysis", "🔍 Evidence"])

    with tab1:
        st.subheader("Judge's Reasoning")
        st.write(j.reasoning)
        st.subheader("Case Facts")
        st.write(j.case_facts)
        st.subheader("Case Info")
        st.write(f"Case ID: {st.session_state.case_id}")
        st.write(f"Offence: {st.session_state.offence}")

    with tab2:
        if st.session_state.debate_log:
            st.subheader("Debate Transcript")
            for turn in st.session_state.debate_log:
                if turn['agent'] == 'prosecutor':
                    st.markdown("##### 👨‍⚖️ Prosecutor")
                    st.info(turn['text'])
                    speak_text(turn['text'], "Prosecutor")
                else:
                    st.markdown("##### 🛡️ Defense")
                    st.success(turn['text'])
                    speak_text(turn['text'], "Defense Lawyer")
                st.markdown("---")
        else:
            st.info("No debate transcript available")

    with tab3:
        st.subheader("Rubric & Confidence")
        if hasattr(j, 'rubric_scores'):
            for k, v in j.rubric_scores.items():
                st.write(f"**{k.replace('_', ' ').title()}:** {v:.1f}/100")
                st.progress(v/100)
        confidence = j.rubric_scores.get("final_score", 0)
        st.metric("Court Confidence", f"{confidence:.1f}%")

    with tab4:
        if hasattr(j, 'evidence_considered') and j.evidence_considered:
            st.subheader("Evidence Considered")
            for i, ev in enumerate(j.evidence_considered, 1):
                st.write(f"**Evidence #{i}**")
                st.write(f"*Relevance Score: {ev.get('score', 0):.2f}*")
                st.write(ev.get('text', 'No text'))
                st.markdown("---")
        else:
            st.info("No evidence available")

    # ======================
    # New case button
    # ======================
    if st.button("🔄 Start New Case"):
        for k in ['evidence', 'case_text', 'judgement', 'debate_log']:
            st.session_state[k] = [] if k == 'evidence' else None
        st.session_state.case_id = f"CASE-{uuid.uuid4().hex[:6].upper()}"
        st.session_state.offence = "speeding"
        st.rerun()
