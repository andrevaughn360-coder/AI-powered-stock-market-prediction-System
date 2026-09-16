#server py.
#StockMind  backend database 

import os 
import time 
import json 
import sqlite3 
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
import requests

load_dotenv()

app = Flask(__name__, static_folder="public", static_url_path="")

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("no api key found, check your .env file")
    exit()

# set up the database
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
    data = request.get_json()
    messages = data.get("messages")
    symbol = data.get("symbol", "unknown")

    if not messages:
        return jsonify({"error": "no messages sent"}), 400

    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1000,
        "messages": messages
    }
    if data.get("system"):
        payload["system"] = data["system"]

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        },
        json=payload
    )

    result = response.json()

    if response.status_code != 200:
        print("something went wrong:", result)
        return jsonify({"error": "AI request failed"}), response.status_code

    # save it to the database
    db.execute(
        "INSERT INTO analyses (symbol, response, created_at) VALUES (?, ?, ?)",
        (symbol, json.dumps(result), str(datetime.now()))
    )
    db.commit()

    return jsonify(result)


@app.route("/api/history")
def history():
    rows = db.execute("SELECT id, symbol, created_at FROM analyses ORDER BY id DESC LIMIT 50").fetchall()
    return jsonify(rows)


if __name__ == "__main__":
    app.run(port=3000, debug=True)