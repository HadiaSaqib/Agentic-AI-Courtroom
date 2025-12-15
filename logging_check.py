import sqlite3  # Change to psycopg2 or mysql.connector if using Postgres/MySQL



DEBATE_ID = "TEST123"  # Replace with your test debate ID

def check_logging():
    # Connect to database
    conn = sqlite3.connect("your_database.db")  # Change DB path if needed
    cursor = conn.cursor()

    print(f"Checking logs for id = {DEBATE_ID}\n")

    # 1️⃣ Check debate start/end
    cursor.execute("SELECT * FROM debates WHERE id=?", (DEBATE_ID,))
    debates = cursor.fetchall()
    if debates:
        print(f"✅ Debate found: {debates[0]}")
    else:
        print("❌ Debate not logged")

    # 2️⃣ Check agent turns
    cursor.execute("SELECT agent, text FROM agent_turns WHERE id=?", (DEBATE_ID,))
    turns = cursor.fetchall()
    if turns:
        print("\n✅ Agent turns logged:")
        for agent, text in turns:
            print(f" - {agent}: {text}")
    else:
        print("❌ No agent turns logged")

    # 3️⃣ Check memory logging
    cursor.execute("SELECT speaker, text FROM memories WHERE id=?", (DEBATE_ID,))
    memories = cursor.fetchall()
    if memories:
        print("\n✅ Memory logged:")
        for speaker, text in memories:
            print(f" - {speaker}: {text}")
    else:
        print("❌ No memory logged")

    # 4️⃣ Check judgement
    cursor.execute("SELECT scores, verdict FROM judgements WHERE id=?", (DEBATE_ID,))
    judgements = cursor.fetchall()
    if judgements:
        print("\n✅ Judgement logged:")
        for scores, verdict in judgements:
            print(f" - Scores: {scores}, Verdict: {verdict}")
    else:
        print("❌ Judgement not logged")

    conn.close()

if __name__ == "__main__":
    check_logging()
