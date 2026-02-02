#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
import requests
import os
import json
import datetime

app = Flask(__name__, static_folder='static')

# --- CONFIG ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://saga-ollama:11434")
MODEL = os.environ.get("SAGA_MODEL", "llama3:latest")
SYSTEM_PROMPT_PATH = "/saga/prompts/saga_system_active.txt"
CONSENSUS_FILE = "/saga/memory/consensus.jsonl"

CHAT_HISTORY = []

def load_identity():
    try:
        with open(SYSTEM_PROMPT_PATH, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "You are Saga, a Nordic-inspired AI hearthkeeper."

def load_consensus():
    """Reads the eternal memories from the stone."""
    memories = ""
    if os.path.exists(CONSENSUS_FILE):
        try:
            with open(CONSENSUS_FILE, "r") as f:
                lines = f.readlines()
                for line in lines[-10:]: # Get last 10 permanent memories
                    data = json.loads(line)
                    memories += f"- {data['instruction']}\n"
        except Exception as e:
            print(f"Error reading stone: {e}")
    return memories

def call_ollama(prompt: str, model: str) -> str:
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=300,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]
    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/")
def serve_ui():
    return send_from_directory(app.static_folder, 'index.html')

@app.route("/api/chat", methods=["POST"])
def chat():
    global CHAT_HISTORY
    data = request.get_json(force=True)

    input_messages = data.get("messages", [])
    if not input_messages:
        return jsonify({"error": "No messages"}), 400

    user_text = input_messages[-1].get("content", "")

    # --- 1. DETECT IF USER WANTS TO REMEMBER SOMETHING ---
    intent_flag = None
    keywords = ["remember this", "from now on", "i prefer", "always", "scribe this"]
    if any(k in user_text.lower() for k in keywords):
        intent_flag = "PENDING_CONSENSUS"

    # --- 2. GATHER ALL MEMORY LAYERS ---
    identity = load_identity()      # The "Soul" (.txt file)
    long_term = load_consensus()    # The "Stone" (.jsonl file)
    
    # Update Short-term History (RAM)
    CHAT_HISTORY.append({"role": "user", "content": user_text})
    CHAT_HISTORY = CHAT_HISTORY[-14:] # Keep last 7 exchanges

    # Build the conversation string
    history_str = ""
    for msg in CHAT_HISTORY:
        role = "User" if msg["role"] == "user" else "Saga"
        history_str += f"{role}: {msg['content']}\n"

    # --- 3. THE MASTER PROMPT (The "Memory Sandwich") ---
    full_prompt = (
        f"{identity}\n\n"
        f"[ETERNAL MEMORIES]\n{long_term if long_term else 'The stone is currently blank.'}\n\n"
        f"Recent Conversation:\n{history_str}"
        f"Saga:"
    )

    # --- 4. SEND TO OLLAMA ---
    model = data.get("model", MODEL)
    reply = call_ollama(full_prompt, model)

    # Add Saga's voice to history
    CHAT_HISTORY.append({"role": "assistant", "content": reply})

    return jsonify({
        "model": model,
        "message": {"role": "assistant", "content": reply},
        "intent": intent_flag,
        "done": True
    })

    # --- 1. CONSENSUS DETECTION ---
    intent_flag = None
    keywords = ["remember this", "from now on", "i prefer", "always", "scribe this"]
    if any(k in user_text.lower() for k in keywords):
        intent_flag = "PENDING_CONSENSUS"

    # --- 2. MEMORY ASSEMBLY ---
    CHAT_HISTORY.append({"role": "user", "content": user_text})
    CHAT_HISTORY = CHAT_HISTORY[-14:] # Keep 7 exchanges

    identity = load_identity()
    long_term = load_consensus()
    
    history_str = ""
    for msg in CHAT_HISTORY:
        role = "User" if msg["role"] == "user" else "Saga"
        history_str += f"{role}: {msg['content']}\n"

    # Injecting long-term memory into the prompt
    full_prompt = f"{identity}\n\n[ETERNAL MEMORIES]\n{long_term}\n\n{history_str}Saga:"

    # --- 3. EXECUTION ---
    reply = call_ollama(full_prompt, data.get("model", MODEL))
    CHAT_HISTORY.append({"role": "assistant", "content": reply})

    return jsonify({
        "message": {"role": "assistant", "content": reply},
        "intent": intent_flag
    })

@app.route("/api/save-consensus", methods=["POST"])
def save_consensus():
    data = request.get_json(force=True)
    text = data.get("text", "")
    if not text:
        return jsonify({"success": False}), 400

    try:
        os.makedirs(os.path.dirname(CONSENSUS_FILE), exist_ok=True)
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "instruction": text
        }
        with open(CONSENSUS_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
