#server py.
#StockMind  backend database 

import os 
import json 
import sqlite3 
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

app = Flask(__name__, static_folder="public", static_url_path="")

# Fetch Groq API key from .env file
groq_api_key = os.environ.get("GROQ_API_KEY")
if not groq_api_key:
    print("Error: No GROQ_API_KEY found in .env file")
    exit()

client = Groq(api_key=groq_api_key)

# Set up SQLite database
db = sqlite3.connect("stockmind.db", check_same_thread=False)
db.execute("""CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    response TEXT,
    created_at TEXT
)""")
db.commit()


@app.route("/")
def home():
    return send_from_directory("public", "index.html")


@app.route("/api/claude", methods=["POST"])
def ask_claude():
    data = request.get_json() or {}
    messages = data.get("messages", [])
    symbol = data.get("symbol", "unknown")
    system_prompt = data.get("system", "You are a helpful stock market assistant.")

    if not messages:
        return jsonify({"error": "no messages sent"}), 400

    try:
        # Convert Anthropic message format to Groq format
        formatted_messages = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            formatted_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # Call Groq API (Free Tier)
        chat_completion = client.chat.completions.create(
            messages=formatted_messages,
            model="llama-3.3-70b-versatile",
        )

        content_text = chat_completion.choices[0].message.content

        # Match Anthropic output format so your frontend HTML displays it properly
        result = {
            "content": [
                {
                    "type": "text",
                    "text": content_text
                }
            ]
        }

        # Save analysis to database
        db.execute(
            "INSERT INTO analyses (symbol, response, created_at) VALUES (?, ?, ?)",
            (symbol, json.dumps(result), str(datetime.now()))
        )
        db.commit()

        return jsonify(result)

    except Exception as e:
        print("Groq API Error:", str(e))
        return jsonify({"error": str(e)}), 500


@app.route("/api/history")
def history():
    rows = db.execute("SELECT id, symbol, created_at FROM analyses ORDER BY id DESC LIMIT 50").fetchall()
    return jsonify(rows)


if __name__ == "__main__":
    app.run(port=3000, debug=True)
