# app.py - COMPLETE WORKING VERSION (Updated Judge support)
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
    from rag.retriever import retrieve
    from rag.db import init_db, get_conn
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
    from agents.prosecutor import ProsecutorAgent
    from agents.defense import DefenseAgent
    from agents.judge import JudgeAgent
    from agents.memory import MemoryManager
    from models.pydantic_models import JudgementModel
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
st.markdown("### Complete System with Database, RAG, and AI Agents")

# ======================
# SIDEBAR - SYSTEM CONTROLS
# ======================
with st.sidebar:
    st.header("🔧 System Status")
    st.checkbox("🔊 Enable Courtroom Voice", value=True, key="voice_enabled")

    # Database status
    db_status = "✅ Ready" if db_initialized else "❌ Offline"
    st.metric("Database", db_status)
    
    # Module status
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
    
    # Evidence management
    st.header("📁 Evidence Management")
    
    # Manual evidence
    st.subheader("Add Evidence")
    manual_evidence = st.text_area("Evidence text:", height=80)
    if st.button("➕ Add Manual Evidence"):
        if manual_evidence:
            st.session_state.evidence.append({
                "text": manual_evidence,
                "score": 0.9,
                "source": "Manual Entry",
                "chunk_id": len(st.session_state.evidence)
            })
            st.success("Evidence added!")
            st.rerun()
    
    # Search database
    st.subheader("🔍 Search Legal Database")
    search_query = st.text_input("Search traffic laws:")
    if st.button("🔎 Search Database"):
        if fact_witness_answer and search_query:
            with st.spinner(f"Searching for '{search_query}'..."):
                try:
                    results = fact_witness_answer(search_query)
                    st.session_state.evidence.extend(results)
                    st.success(f"Found {len(results)} relevant laws")
                    st.rerun()
                except Exception as e:
                    st.error(f"Search failed: {e}")
        else:
            st.error("RAG system not available")
    
    st.markdown("---")
    
    # Clear evidence
    st.write(f"**Total Evidence:** {len(st.session_state.evidence)} items")
    if st.button("🗑️ Clear All Evidence", type="secondary"):
        st.session_state.evidence = []
        st.rerun()
    
    st.markdown("---")
    
    # Debate settings
    st.header("⚙️ Debate Settings")
    rounds = st.slider("Debate Rounds", 1, 3, 2)
    st.session_state.rounds = rounds

# ======================
# MAIN INTERFACE
# ======================
col1, col2 = st.columns([3, 2])

with col1:
    st.header("📝 Case Details")
    st.session_state.case_id = st.text_input("Case ID", value=st.session_state.case_id)
    st.session_state.offence = st.text_input("Offence type", value=st.session_state.offence)
    
    # Case input with examples
    example_cases = {
        "Case 1 - No License": "Driver was caught driving without a valid license at Main Street intersection. Police verified no license exists. Time: 3 PM.",
        "Case 2 - Speeding": "Vehicle was speeding at 90 km/h in a 60 km/h zone. Recorded by speed camera. Weather was clear.",
        "Case 3 - Red Light": "Driver jumped red light at traffic signal. Witnessed by traffic police officer.",
        "Case 4 - No Insurance": "Vehicle was found without valid insurance documents during routine check."
    }
    
    # Case selection
    selected_case = st.selectbox(
        "Choose example case or write your own:",
        ["Write your own case"] + list(example_cases.keys())
    )
    
    if selected_case != "Write your own case":
        case_text = st.text_area(
            "Case details:",
            value=example_cases[selected_case],
            height=150
        )
    else:
        case_text = st.text_area(
            "Case details:",
            height=150,
            placeholder="Describe the traffic violation case in detail..."
        )
    
    st.session_state.case_text = case_text

with col2:
    st.header("⚖️ Court Proceedings")
    
    # System readiness check
    system_ready = all([fact_witness_answer, lc_llm, DebatePipeline, case_text.strip()])
    
    if system_ready:
        st.success("✅ System ready for debate")
    else:
        missing = []
        if not fact_witness_answer: missing.append("RAG")
        if not lc_llm: missing.append("LLM")
        if not DebatePipeline: missing.append("Agents")
        if not case_text.strip(): missing.append("Case details")
        st.warning(f"⚠️ Waiting for: {', '.join(missing)}")
    
    # Evidence preview
    if st.session_state.evidence:
        with st.expander(f"📋 Relevant Laws ({len(st.session_state.evidence)} items)"):
            for i, ev in enumerate(st.session_state.evidence[:3]):
                st.caption(f"**#{i+1}** - Score: {ev.get('score', 0):.2f}")
                st.write(ev.get('text', ''))
    
    # Start debate button
    if st.button(
        "🚀 START AI COURT DEBATE",
        type="primary",
        disabled=not system_ready,
        use_container_width=True
    ):
        with st.spinner("Court is in session..."):
            try:
                debate_id = st.session_state.case_id
                pipeline = DebatePipeline(llm=lc_llm, debate_id=debate_id)
                
                for ev in st.session_state.evidence:
                    pipeline.submit_evidence(ev)
                
                judgement = pipeline.run(
                    case_facts=case_text,
                    offence=st.session_state.offence,
                    rounds=st.session_state.rounds
                )
                
                st.session_state.judgement = judgement
                st.session_state.debate_log = pipeline.hearing_log
                
                st.success("✅ Court proceedings completed!")
                st.balloons()
                st.rerun()
                
            except Exception as e:
                st.error(f"Courtroom error: {str(e)}")
                import traceback
                with st.expander("Technical details"):
                    st.code(traceback.format_exc())

# ======================
# DISPLAY RESULTS
# ======================
if st.session_state.judgement:
    st.markdown("---")
    st.header("⚖️ Court Judgement")
    
    judgement = st.session_state.judgement
    speak_text(judgement.verdict, "Judge")
    
    if "Confirmed" in judgement.verdict.upper():
        st.markdown(f"<div style='background: #dc2626; color: white; padding: 15px; border-radius:10px'>{judgement.verdict}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='background: #16a34a; color: white; padding: 15px; border-radius:10px'>{judgement.verdict}</div>", unsafe_allow_html=True)

    st.subheader("Reasoning")
    st.write(judgement.reasoning)
    speak_text(judgement.reasoning, "Judge")

    st.subheader("Scores")
    st.metric("Prosecution Score", judgement.prosecution_score)
    st.metric("Defense Score", judgement.defense_score)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Judgement", "🗣️ Debate", "📊 Analysis", "🔍 Evidence"])
    
    with tab1:
        st.subheader("Judge's Legal Reasoning")
        st.write(judgement.reasoning)
        st.subheader("Case Facts")
        st.write(judgement.case_facts)
        st.write(f"Case ID: {st.session_state.case_id}")
        st.write(f"Offence: {st.session_state.offence}")
    
    with tab2:
        if st.session_state.debate_log:
            st.subheader("Complete Debate Transcript")
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
        st.subheader("Scoring Breakdown")
        if hasattr(judgement, 'rubric_scores'):
            for key, value in judgement.rubric_scores.items():
                st.write(f"**{key.replace('_',' ').title()}:** {value:.1f}/100")
                st.progress(value/100)
            st.metric("Court Confidence", f"{judgement.rubric_scores.get('final_score',0):.1f}%")
        else:
            st.info("Detailed scoring not available")
    
    with tab4:
        if hasattr(judgement, 'evidence_considered') and judgement.evidence_considered:
            st.subheader("Evidence Considered by Court")
            for i, ev in enumerate(judgement.evidence_considered, 1):
                st.write(f"**Evidence #{i}**")
                st.write(f"*Relevance Score: {ev.get('score',0):.2f}*")
                st.write(ev.get('text',''))
                st.markdown("---")
        else:
            st.info("No evidence details available")
    
    if st.button("🔄 Start New Case", type="secondary"):
        for k in ['evidence','case_text','judgement','debate_log']:
            st.session_state[k] = [] if k=='evidence' else None
        st.session_state.case_id = f"CASE-{uuid.uuid4().hex[:6].upper()}"
        st.session_state.offence = "speeding"
        st.rerun()
