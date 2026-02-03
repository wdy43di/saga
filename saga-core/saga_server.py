#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
import requests
import os
import json
import datetime
import nltk
from nltk import pos_tag, word_tokenize

print("🔥🔥🔥 SAGA ENGINE ONLINE - VERSION 2.1 🔥🔥🔥")
app = Flask(__name__, static_folder='static')

# --- CONFIG ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://saga-ollama:11434")
MODEL = os.environ.get("SAGA_MODEL", "llama3:latest")
SYSTEM_PROMPT_PATH = "/saga/prompts/saga_system_active.txt"
CONSENSUS_FILE = "/saga/memory/consensus.jsonl"
PROJECTS_DIR = "/saga/memory/projects"

# --- STATE ---
CHAT_HISTORY = []
PROJECT_VIBRATIONS = {} 
CONFIDENCE_THRESHOLD = 0.7
NEW_PROJECT_THRESHOLD = 0.9


# --- NLTK SETUP ---
# We tell NLTK exactly where to look (the path from the Dockerfile)
nltk.data.path.append('/usr/local/share/nltk_data')

def extract_essence(text):
    """Filters text to keep only Nouns and Proper Nouns."""
    try:
        tokens = word_tokenize(text)
        tagged = pos_tag(tokens)
        # We only want Nouns (NN), Proper Nouns (NNP), or Plural Nouns (NNS)
        essence = [word.lower() for word, tag in tagged if tag in ('NN', 'NNP', 'NNS')]
        return essence
    except Exception as e:
        print(f"❌ Grammar Error: {e}")
        # Manual fallback: if the tagger fails, at least ignore these common non-nouns
        manual_stop = ['hate', 'much', 'very', 'really', 'want', 'need', 'this', 'that']
        return [w.strip("?!.,").lower() for w in text.split() if len(w) > 2 and w.lower() not in manual_stop]

def load_identity():
    try:
        with open(SYSTEM_PROMPT_PATH, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "You are Saga, a Nordic-inspired AI hearthkeeper."

def load_consensus():
    memories = ""
    if os.path.exists(CONSENSUS_FILE):
        try:
            with open(CONSENSUS_FILE, "r") as f:
                lines = f.readlines()
                for line in lines[-15:]:
                    data = json.loads(line)
                    memories += f"- {data['instruction']}\n"
        except Exception as e:
            print(f"Error reading stone: {e}")
    return memories

def load_project_memory(project_name):
    path = os.path.join(PROJECTS_DIR, f"{project_name}.jsonl")
    notes = ""
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                for line in f:
                    data = json.loads(line)
                    content = data.get('note') or data.get('content') or ""
                    notes += f"- {content}\n"
        except Exception as e:
            print(f"Error reading project {project_name}: {e}")
    return notes

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
    global CHAT_HISTORY, PROJECT_VIBRATIONS
    data = request.get_json(force=True)

    input_messages = data.get("messages", [])
    if not input_messages:
        return jsonify({"error": "No messages"}), 400

    user_text = input_messages[-1].get("content", "")
    intent_flag = None
    suggested_project_name = None

    # --- 1. PROJECT INTUITION ---
    active_project_notes = ""
    if os.path.exists(PROJECTS_DIR):
        available_projects = [f.replace('.jsonl', '') for f in os.listdir(PROJECTS_DIR) if f.endswith('.jsonl')]
        for project in available_projects:
            if project.replace('_', ' ') in user_text.lower():
                PROJECT_VIBRATIONS[project] = PROJECT_VIBRATIONS.get(project, 0) + 0.4
            else:
                PROJECT_VIBRATIONS[project] = max(0, PROJECT_VIBRATIONS.get(project, 0) - 0.05)

            if PROJECT_VIBRATIONS.get(project, 0) >= CONFIDENCE_THRESHOLD:
                print(f"✨ RECALL: '{project}' score: {PROJECT_VIBRATIONS[project]:.2f}")
                active_project_notes += f"\n[PROJECT DATA: {project.upper()}]\n"
                active_project_notes += load_project_memory(project)

    # --- 2. THE ESSENCE SCANNER ---
    essential_keywords = extract_essence(user_text)
    print(f"DEBUG: Nouns detected: {essential_keywords}")

    for word in essential_keywords:
        if len(word) <= 2: continue
        vibe_key = f"NEW_{word}"
        PROJECT_VIBRATIONS[vibe_key] = PROJECT_VIBRATIONS.get(vibe_key, 0) + 0.45
        print(f"✨ Vibe for '{word}': {PROJECT_VIBRATIONS[vibe_key]:.2f}")

        if PROJECT_VIBRATIONS[vibe_key] >= 0.8:
            print(f"🎯 ESSENCE FOUND: {word}")
            intent_flag = "NEW_PROJECT_SUGGESTION"
            suggested_project_name = word
            PROJECT_VIBRATIONS[vibe_key] = 0

    # --- 3. CONSENSUS DETECTION ---
    keywords = ["remember this", "from now on", "i prefer", "always", "scribe this"]
    if any(k in user_text.lower() for k in keywords):
        intent_flag = "PENDING_CONSENSUS"

    # --- 4. PROMPT ASSEMBLY ---
    identity = load_identity()
    long_term = load_consensus()
    
    CHAT_HISTORY.append({"role": "user", "content": user_text})
    CHAT_HISTORY = CHAT_HISTORY[-14:] 

    history_str = ""
    for msg in CHAT_HISTORY:
        role = "User" if msg["role"] == "user" else "Saga"
        history_str += f"{role}: {msg['content']}\n"

    full_prompt = (
        f"{identity}\n\n"
        f"[ETERNAL MEMORIES]\n{long_term if long_term else 'The stone is blank.'}\n"
        f"{active_project_notes}\n"
        f"Recent Conversation:\n{history_str}"
        f"Saga:"
    )

    # --- 5. EXECUTION ---
    model = data.get("model", MODEL)
    reply = call_ollama(full_prompt, model)
    CHAT_HISTORY.append({"role": "assistant", "content": reply})

    return jsonify({
        "message": {"role": "assistant", "content": reply},
        "intent": intent_flag,
        "suggested_project": suggested_project_name,
        "done": True
    })

@app.route("/api/save-consensus", methods=["POST"])
def save_consensus():
    data = request.get_json(force=True)
    text = data.get("text", "")
    if not text: return jsonify({"success": False}), 400
    try:
        os.makedirs(os.path.dirname(CONSENSUS_FILE), exist_ok=True)
        entry = {"timestamp": datetime.datetime.now().isoformat(), "instruction": text}
        with open(CONSENSUS_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/create-project", methods=["POST"])
def create_project():
    data = request.get_json(force=True)
    name = data.get("name", "").lower().replace(" ", "_")
    note = data.get("note", "Project initiated.")
    if not name: return jsonify({"success": False}), 400
    path = os.path.join(PROJECTS_DIR, f"{name}.jsonl")
    try:
        os.makedirs(PROJECTS_DIR, exist_ok=True)
        entry = {"timestamp": datetime.datetime.now().isoformat(), "note": note}
        with open(path, "w") as f:
            f.write(json.dumps(entry) + "\n")
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
