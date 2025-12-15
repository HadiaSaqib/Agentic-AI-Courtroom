import json
from rag.db import get_conn

# -------------------------
# Debate lifecycle
# -------------------------
def start_debate(debate_id, case_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO debates (id, case_id, started_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (debate_id, case_id)
    )
    conn.commit()
    conn.close()


def end_debate(debate_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE debates SET finished_at=CURRENT_TIMESTAMP WHERE id=?",
        (debate_id,)
    )
    conn.commit()
    conn.close()


# -------------------------
# Agent logs
# -------------------------
def log_agent_turn(debate_id, agent, text):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO agent_turns (debate_id, agent, text) VALUES (?, ?, ?)",
        (debate_id, agent, text)
    )
    conn.commit()
    conn.close()


# -------------------------
# Judge output
# -------------------------
def log_judgement(debate_id, scores, verdict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO judgements (debate_id, scores_json, verdict, confidence) VALUES (?, ?, ?, ?)",
        (
            debate_id,
            json.dumps(scores),
            verdict,
            scores.get("evidence_strength", 0)
        )
    )
    conn.commit()
    conn.close()


# -------------------------
# Memory persistence
# -------------------------
def log_memory(debate_id, key, value):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO memory (debate_id, key, value) VALUES (?, ?, ?)",
        (debate_id, key, value)
    )
    conn.commit()
    conn.close()
