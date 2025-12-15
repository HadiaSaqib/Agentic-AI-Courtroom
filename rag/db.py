import sqlite3
import os
import json

DB_PATH = "database/courtroom.db"

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

   
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        text TEXT,
        embedding TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS evidence_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query_id INTEGER,
        chunk_id INTEGER,
        score REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(query_id) REFERENCES queries(id),
        FOREIGN KEY(chunk_id) REFERENCES chunks(id)
    )
    """)

    

    # Cases (student-provided scenarios)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cases (
        id TEXT PRIMARY KEY,
        title TEXT,
        facts TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Debate sessions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS debates (
        id TEXT PRIMARY KEY,
        case_id TEXT,
        started_at TIMESTAMP,
        finished_at TIMESTAMP,
        FOREIGN KEY(case_id) REFERENCES cases(id)
    )
    """)

    # Each turn by agents (prosecutor, defense, witness, judge)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS agent_turns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        debate_id TEXT,
        agent TEXT,
        text TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(debate_id) REFERENCES debates(id)
    )
    """)

    # Judge evaluation / rubric
    cur.execute("""
    CREATE TABLE IF NOT EXISTS judgements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        debate_id TEXT,
        scores_json TEXT,
        verdict TEXT,
        confidence REAL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(debate_id) REFERENCES debates(id)
    )
    """)

    # Agent memory storage
    cur.execute("""
    CREATE TABLE IF NOT EXISTS memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        debate_id TEXT,
        key TEXT,
        value TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(debate_id) REFERENCES debates(id)
    )
    """)

    conn.commit()
    conn.close()
