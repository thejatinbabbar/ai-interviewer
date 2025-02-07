import os
import sqlite3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Database Service")

# Use an environment variable for the DB file name; default to conversations.db
DB_NAME = os.getenv("DB_NAME", "conversations.db")


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user TEXT,
            conversation TEXT,
            evaluation TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    conn.commit()
    conn.close()


init_db()


class Conversation(BaseModel):
    session_id: str
    user: str
    conversation: str
    evaluation: str


class GetSession(BaseModel):
    session_id: str


@app.post("/log")
async def log_conversation(conv: Conversation):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversation (session_id, user, conversation, evaluation) VALUES (?, ?, ?, ?)",
            (conv.session_id, conv.user, conv.conversation, conv.evaluation),
        )
        conn.commit()
        conn.close()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Optional: An endpoint to retrieve logs (for debugging/demo purposes)
@app.get("/get_log")
async def get_log(request: GetSession):
    session_id = request.session_id
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversation WHERE session_id=?", (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return {"logs": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
