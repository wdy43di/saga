#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
import requests
import os
import json
import datetime
import re
import psutil
import nltk
from nltk import pos_tag, word_tokenize

print("🔥🔥🔥 SAGA ENGINE ONLINE - VERSION 2.5 (MECHANICAL SYMPATHY) 🔥🔥🔥")
app = Flask(__name__, static_folder='static')

# --- CONFIG ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://saga-ollama:11434")
MODEL = os.environ.get("SAGA_MODEL", "llama3:latest")
SYSTEM_PROMPT_PATH = "/saga/prompts/saga_system_active.txt"
CONSENSUS_FILE = "/saga/memory/consensus.jsonl"
PROJECTS_DIR = "/saga/memory/projects"
UPLOAD_DIR = "/saga/memory/uploads"
THREADS_DIR = "/saga/memory/threads"

# Ensure all scrolls and stones are in place
for d in [PROJECTS_DIR, UPLOAD_DIR, THREADS_DIR]:
    os.makedirs(d, exist_ok=True)

# --- STATE ---
CHAT_HISTORY = []
PROJECT_VIBRATIONS = {}
CONFIDENCE_THRESHOLD = 0.7

# Ensure NLTK data is accessible
nltk.data.path.append('/usr/local/share/nltk_data')

# --- CORE UTILITIES ---

def strip_email_noise(text):
    """Strips signatures and corporate fluff to focus the engine."""
    noise_patterns = [
        r"John Schreckendgust.*?\d{3}-\d{3}-\d{4}",
        r"Regional System Administrator",
        r"www\.tiogadowns\.com",
        r"jschreck@tiogadowns\.com",
        r"From:.*?\nSent:.*?\nTo:.*?\nSubject:.*?\n",
        r"This message is intended for the use of the individual or entity.*",
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()

def extract_essence(text):
    """Filters text to keep only Nouns and Proper Nouns for project detection."""
    try:
        tokens = word_tokenize(text)
        tagged = pos_tag(tokens)
        essence = [word.lower() for word, tag in tagged if tag in ('NN', 'NNP', 'NNS')]
        return essence
    except Exception:
        return [w.strip("?!.,").lower() for w in text.split() if len(w) > 3]

def load_identity():
    try:
        with open(SYSTEM_PROMPT_PATH, "r") as f:
            return f.read().strip()
    except:
        return "You are Saga, a hearthkeeper."

def load_consensus():
    memories = ""
    if os.path.exists(CONSENSUS_FILE):
        with open(CONSENSUS_FILE, "r") as f:
            lines = f.readlines()
            for line in lines[-15:]:
                try:
                    data = json.loads(line)
                    memories += f"- {data['instruction']}\n"
                except: continue
    return memories

def load_project_memory(project_name):
    path = os.path.join(PROJECTS_DIR, f"{project_name}.jsonl")
    notes = ""
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    content = data.get('content') or data.get('note') or ""
                    notes += f"- {content[:1000]}\n"
                except: continue
    return notes

def call_ollama(messages: list, model: str) -> str:
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model, 
                "messages": messages, 
                "stream": False,
                "options": {"num_predict": 1024} # Keep her concise for laptop performance
            },
            timeout=600
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

    # Clean the input
    clean_user_text = strip_email_noise(user_text)

    intent_flag = None
    suggested_project_name = None
    active_project_notes = ""

    # 1. Saga (Project) Detection
    if os.path.exists(PROJECTS_DIR):
        available_projects = [f.replace('.jsonl', '') for f in os.listdir(PROJECTS_DIR) if f.endswith('.jsonl')]
        for project in available_projects:
            if project.replace('_', ' ') in clean_user_text.lower():
                PROJECT_VIBRATIONS[project] = PROJECT_VIBRATIONS.get(project, 0) + 0.4
            else:
                PROJECT_VIBRATIONS[project] = max(0, PROJECT_VIBRATIONS.get(project, 0) - 0.05)

            if PROJECT_VIBRATIONS.get(project, 0) >= CONFIDENCE_THRESHOLD:
                active_project_notes += f"\n[KNOWLEDGE SOURCE: {project.upper()}]\n"
                active_project_notes += load_project_memory(project)

    # 2. Essence Scanner (Suggesting new projects)
    essential_keywords = extract_essence(clean_user_text)
    for word in essential_keywords:
        if len(word) <= 3: continue
        vibe_key = f"NEW_{word}"
        PROJECT_VIBRATIONS[vibe_key] = PROJECT_VIBRATIONS.get(vibe_key, 0) + 0.45
        if PROJECT_VIBRATIONS[vibe_key] >= 0.8:
            intent_flag = "NEW_PROJECT_SUGGESTION"
            suggested_project_name = word
            PROJECT_VIBRATIONS[vibe_key] = 0

    # 3. Context Construction
    identity = load_identity()
    long_term = load_consensus()

    system_msg = f"{identity}\n\n[ETERNAL MEMORIES]\n{long_term}\n{active_project_notes}"
    if len(clean_user_text) > 2000:
        system_msg += "\n[ANALYST MODE: Focus on IPs and technical specs. Be concise.]"

    payload_messages = [{"role": "system", "content": system_msg}]
    for msg in CHAT_HISTORY[-10:]:
        payload_messages.append(msg)
    payload_messages.append({"role": "user", "content": clean_user_text})

    reply = call_ollama(payload_messages, data.get("model", MODEL))

    CHAT_HISTORY.append({"role": "user", "content": clean_user_text})
    CHAT_HISTORY.append({"role": "assistant", "content": reply})

    return jsonify({
        "message": {"role": "assistant", "content": reply},
        "intent": intent_flag,
        "suggested_project": suggested_project_name
    })

@app.route("/api/new-chat", methods=["POST"])
def new_chat():
    global CHAT_HISTORY, PROJECT_VIBRATIONS
    if CHAT_HISTORY:
        # 1. Generate Story Title
        title_prompt = [
            {"role": "system", "content": "Provide a 3-5 word title for this conversation. Return ONLY the title text."},
            {"role": "user", "content": f"Summarize: {str(CHAT_HISTORY[-3:])}"}
        ]
        raw_title = call_ollama(title_prompt, MODEL).strip()
        story_title = re.sub(r'[^\w\s-]', '', raw_title).replace(" ", "_")

        # 2. Find the Active Saga
        active_saga = "General"
        highest_vibe = 0
        for proj, vibe in PROJECT_VIBRATIONS.items():
            if vibe > highest_vibe and not proj.startswith("NEW_"):
                highest_vibe = vibe
                active_saga = proj

        # 3. Archive the Story
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        filename = f"{active_saga}--{story_title}--{timestamp}.json"
        with open(os.path.join(THREADS_DIR, filename), "w") as f:
            json.dump(CHAT_HISTORY, f)

    CHAT_HISTORY = []
    PROJECT_VIBRATIONS = {k: 0 for k in PROJECT_VIBRATIONS}
    return jsonify({"success": True})

@app.route("/api/threads", methods=["GET"])
def list_threads():
    if not os.path.exists(THREADS_DIR): return jsonify([])
    threads = []
    for f in sorted(os.listdir(THREADS_DIR), reverse=True):
        if f.endswith(".json"):
            # ID is the filename, display is the text used for splitting in JS
            threads.append({"id": f, "display": f.replace(".json", "")})
    return jsonify(threads)

@app.route("/api/load-thread/<thread_id>", methods=["GET"])
def load_thread(thread_id):
    global CHAT_HISTORY
    path = os.path.join(THREADS_DIR, thread_id)
    if os.path.exists(path):
        with open(path, "r") as f:
            CHAT_HISTORY = json.load(f)
        return jsonify({"success": True, "history": CHAT_HISTORY})
    return jsonify({"success": False}), 404

@app.route("/api/mind", methods=["GET"])
def get_mind():
    # 1. Identify Active Project
    active_project = "None"
    highest_vibe = 0
    for proj, vibe in PROJECT_VIBRATIONS.items():
        if not proj.startswith("NEW_") and vibe > highest_vibe:
            highest_vibe = vibe
            active_project = proj

    # 2. Get Memories
    eternal_memories = []
    if os.path.exists(CONSENSUS_FILE):
        with open(CONSENSUS_FILE, "r") as f:
            lines = f.readlines()
            for line in lines[-5:]:
                try:
                    data = json.loads(line)
                    eternal_memories.append(data.get('instruction', 'Untitled Memory'))
                except: continue

    # 3. Mechanical Sympathy (Hardware Pulse)
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent
    stress_level = (cpu_usage + ram_usage) / 2

    return jsonify({
        "active_project": active_project, 
        "eternal_memories": eternal_memories,
        "stress": stress_level
    })

@app.route("/api/save-consensus", methods=["POST"])
def save_consensus():
    data = request.json
    text = data.get("text", "")
    cleaned_text = re.sub(r'^(saga|saga[:,\-\s]+)', '', text, flags=re.IGNORECASE).strip()
    entry = {"timestamp": datetime.datetime.now().isoformat(), "instruction": cleaned_text}
    with open(CONSENSUS_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return jsonify({"success": True})

@app.route("/api/create-project", methods=["POST"])
def create_project():
    data = request.get_json(force=True)
    name = data.get("name", "").lower().replace(" ", "_")
    path = os.path.join(PROJECTS_DIR, f"{name}.jsonl")
    with open(path, "w") as f:
        f.write(json.dumps({"note": f"Saga {name} initiated."}) + "\n")
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
