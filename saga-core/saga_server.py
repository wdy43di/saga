#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
import requests
import os
import json
import datetime
import nltk
from nltk import pos_tag, word_tokenize
from pypdf import PdfReader

print("🔥🔥🔥 SAGA ENGINE ONLINE - VERSION 2.2 (GROWTH ENABLED) 🔥🔥🔥")
app = Flask(__name__, static_folder='static')

# --- CONFIG ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://saga-ollama:11434")
MODEL = os.environ.get("SAGA_MODEL", "llama3:latest")
SYSTEM_PROMPT_PATH = "/saga/prompts/saga_system_active.txt"
CONSENSUS_FILE = "/saga/memory/consensus.jsonl"
PROJECTS_DIR = "/saga/memory/projects"
UPLOAD_DIR = "/saga/memory/uploads"

# Ensure directories exist
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- STATE ---
CHAT_HISTORY = []
PROJECT_VIBRATIONS = {}
CONFIDENCE_THRESHOLD = 0.7 # Mention project twice to trigger RAG

# --- NLTK SETUP ---
nltk.data.path.append('/usr/local/share/nltk_data')

# --- CORE FUNCTIONS ---

def extract_essence(text):
    """Filters text to keep only Nouns and Proper Nouns."""
    try:
        tokens = word_tokenize(text)
        tagged = pos_tag(tokens)
        essence = [word.lower() for word, tag in tagged if tag in ('NN', 'NNP', 'NNS')]
        return essence
    except Exception as e:
        print(f"❌ Grammar Error: {e}", flush=True)
        return [w.strip("?!.,").lower() for w in text.split() if len(w) > 3]

def read_pdf(file_path):
    """Extracts text and generates a noun-based summary from a PDF."""
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
        summary_nouns = extract_essence(text[:5000])
        unique_nouns = list(dict.fromkeys(summary_nouns))
        summary = f"Key Concepts: {', '.join(unique_nouns[:15])}"
        return text, summary
    except Exception as e:
        return f"Error: {str(e)}", "No summary."

def load_identity():
    try:
        with open(SYSTEM_PROMPT_PATH, "r") as f:
            return f.read().strip()
    except:
        return "You are Saga, a Nordic-inspired AI hearthkeeper."

def load_consensus():
    memories = ""
    if os.path.exists(CONSENSUS_FILE):
        with open(CONSENSUS_FILE, "r") as f:
            lines = f.readlines()
            for line in lines[-15:]:
                data = json.loads(line)
                memories += f"- {data['instruction']}\n"
    return memories

def load_project_memory(project_name):
    path = os.path.join(PROJECTS_DIR, f"{project_name}.jsonl")
    notes = ""
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                data = json.loads(line)
                content = data.get('content') or data.get('note') or ""
                notes += f"- {content[:1000]}\n"
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
        return r.json()["message"]["content"]
    except Exception as e:
        return f"Connection Cold: {str(e)}"

# --- ROUTES ---

@app.route("/")
def serve_ui():
    return send_from_directory(app.static_folder, 'index.html')

@app.route("/api/chat", methods=["POST"])
def chat():
    global CHAT_HISTORY, PROJECT_VIBRATIONS
    data = request.get_json(force=True)
    user_text = data.get("messages", [])[-1].get("content", "")

    intent_flag = None
    suggested_project_name = None
    active_project_notes = ""

    # 1. Project Recall & Logs
    if os.path.exists(PROJECTS_DIR):
        available_projects = [f.replace('.jsonl', '') for f in os.listdir(PROJECTS_DIR) if f.endswith('.jsonl')]
        for project in available_projects:
            if project.replace('_', ' ') in user_text.lower():
                PROJECT_VIBRATIONS[project] = PROJECT_VIBRATIONS.get(project, 0) + 0.4
            else:
                PROJECT_VIBRATIONS[project] = max(0, PROJECT_VIBRATIONS.get(project, 0) - 0.05)

            if PROJECT_VIBRATIONS.get(project, 0) >= CONFIDENCE_THRESHOLD:
                print(f"✨ RECALL: '{project}' triggered.", flush=True)
                active_project_notes += f"\n[KNOWLEDGE SOURCE: {project.upper()}]\n"
                active_project_notes += load_project_memory(project)

    # 2. Essence Scanner (Debugging Restored)
    essential_keywords = extract_essence(user_text)
    print(f"DEBUG: Nouns detected: {essential_keywords}", flush=True)

    for word in essential_keywords:
        if len(word) <= 3: continue
        vibe_key = f"NEW_{word}"
        PROJECT_VIBRATIONS[vibe_key] = PROJECT_VIBRATIONS.get(vibe_key, 0) + 0.45
        print(f"✨ Vibe for '{word}': {PROJECT_VIBRATIONS[vibe_key]:.2f}", flush=True)

        if PROJECT_VIBRATIONS[vibe_key] >= 0.8:
            intent_flag = "NEW_PROJECT_SUGGESTION"
            suggested_project_name = word
            PROJECT_VIBRATIONS[vibe_key] = 0

    # 3. Consensus Detection
    keywords = ["remember this", "from now on", "scribe this", "always"]
    if any(k in user_text.lower() for k in keywords):
        intent_flag = "PENDING_CONSENSUS"

    # 4. Prompt Construction
    identity = load_identity()
    long_term = load_consensus()
    CHAT_HISTORY.append({"role": "user", "content": user_text})
    CHAT_HISTORY = CHAT_HISTORY[-10:]

    history_str = "\n".join([f"{'User' if m['role']=='user' else 'Saga'}: {m['content']}" for m in CHAT_HISTORY])

    full_prompt = f"{identity}\n\n[ETERNAL MEMORIES]\n{long_term}\n{active_project_notes}\n\nRecent Conversation:\n{history_str}\nSaga:"

    reply = call_ollama(full_prompt, data.get("model", MODEL))
    CHAT_HISTORY.append({"role": "assistant", "content": reply})

    return jsonify({
        "message": {"role": "assistant", "content": reply},
        "intent": intent_flag,
        "suggested_project": suggested_project_name
    })

@app.route("/api/upload", methods=["POST"])
def upload_file():
    file = request.files['file']
    project_name = request.form.get("project", "general").lower()
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    file.save(save_path)
    content, summary = read_pdf(save_path)
    project_path = os.path.join(PROJECTS_DIR, f"{project_name}.jsonl")
    entry = {"timestamp": datetime.datetime.now().isoformat(), "source": file.filename, "content": content[:3000]}
    with open(project_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return jsonify({"success": True, "summary": summary})

@app.route("/api/save-consensus", methods=["POST"])
def save_consensus():
    data = request.get_json(force=True)
    entry = {"timestamp": datetime.datetime.now().isoformat(), "instruction": data.get("text", "")}
    with open(CONSENSUS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return jsonify({"success": True})

@app.route("/api/create-project", methods=["POST"])
def create_project():
    data = request.get_json(force=True)
    name = data.get("name", "").lower().replace(" ", "_")
    path = os.path.join(PROJECTS_DIR, f"{name}.jsonl")
    with open(path, "w") as f:
        f.write(json.dumps({"note": "Project started."}) + "\n")
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
