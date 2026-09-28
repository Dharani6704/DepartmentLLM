# # # flask_app.py# 
import os, uuid, sqlite3, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add backend to import path

from backend.ingest import ingest_file_bytes
from backend.query_engine import answer_query

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "db", "conversations.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# ---------------------------------------------------------------------
# Database Setup
# ---------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY, 
        title TEXT, 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY, 
        conversation_id TEXT, 
        role TEXT, 
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(conversation_id) REFERENCES conversations(id)
    )""")
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------
def save_message(conv_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
        (str(uuid.uuid4()), conv_id, role, content)
    )
    conn.commit()
    conn.close()

def create_conversation(title="New Chat"):
    conv_id = str(uuid.uuid4())
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO conversations (id, title) VALUES (?, ?)", (conv_id, title))
    conn.commit()
    conn.close()
    return conv_id

# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
@app.route("/ingest", methods=["POST"])
def ingest_route():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400
    res = ingest_file_bytes(file.read(), file.filename)
    return jsonify(res)

@app.route("/query", methods=["POST"])
def query_route():
    prompt = request.form.get("prompt")
    conversation_id = request.form.get("conversation_id")

    if not prompt:
        return jsonify({"error": "Prompt missing"}), 400

    # Create conversation if missing
    if not conversation_id:
        conversation_id = create_conversation("New Chat")

    # Save user query
    save_message(conversation_id, "user", prompt)

    # Retrieve and generate concise answer
    try:
        result = answer_query(prompt)
        # ✅ Extract only clean answer
        response_text = result.get("answer", "Not Available").strip()
    except Exception as e:
        response_text = f"Error: {str(e)}"

    # Save assistant reply
    save_message(conversation_id, "assistant", response_text)

    # ✅ Return minimal, frontend-friendly data
    return jsonify({
        "conversation_id": conversation_id,
        "response": response_text
    })

@app.route("/conversations", methods=["GET"])
def get_conversations():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM conversations ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route("/conversations", methods=["POST"])
def create_conv_route():
    title = request.form.get("title", "New Chat")
    conv_id = create_conversation(title)
    return jsonify({"id": conv_id, "title": title})

@app.route("/conversations/<conversation_id>/messages", methods=["GET"])
def get_messages(conversation_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, role, content, created_at FROM messages WHERE conversation_id=? ORDER BY created_at ASC", (conversation_id,))
    rows = cur.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route("/status")
def status():
    return jsonify({"status": "running"})

# ---------------------------------------------------------------------
if __name__ == "__main__":
    print(f"📂 Using CHROMA_DIR: {os.path.join(BASE_DIR, 'db', 'chroma')}")
    print(f"📂 Using DATA_DIR: {os.path.join(BASE_DIR, 'data')}")
    app.run(host="0.0.0.0", port=8000, debug=True)
