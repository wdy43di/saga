#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
import requests
import os
import json
import datetime
import re
import psutil

# --- LORE VAULT MODULES ---
try:
    from langchain_ollama import OllamaEmbeddings
    from langchain_community.vectorstores import Chroma
    LORE_CAPABLE = True
except ImportError:
    LORE_CAPABLE = False
    print("⚠️ WARNING: LangChain modules not found inside container.")

app = Flask(__name__, static_folder='static')

# --- DOCKER-INTERNAL CONFIG ---
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://saga-ollama:11434")
MODEL = os.environ.get("SAGA_MODEL", "llama3:latest")

# These match your docker-compose.yml mappings exactly
SYSTEM_PROMPT_PATH = "/saga/prompts/saga_system_active.txt"
DM_OVERLAY_PATH = "/saga/prompts/saga_dm_overlay.txt"
VECTOR_DB_DIR = "/saga/memory/vector_store"
CONSENSUS_FILE = "/saga/memory/consensus.jsonl"

CHAT_HISTORY = []

def query_lore(user_query):
    """The 'Scribe Search' - pulls context from your 3,275+ fragments."""
    if not LORE_CAPABLE or not os.path.exists(VECTOR_DB_DIR):
        return ""
    
    try:
        embeddings = OllamaEmbeddings(model="llama3", base_url=OLLAMA_URL)
        db = Chroma(persist_directory=VECTOR_DB_DIR, embedding_function=embeddings)
        
        # Search for top 3 relevant pieces of PDF lore
        docs = db.similarity_search(user_query, k=3)
        if docs:
            context = "\n--- ARCHIVE DATA ---\n"
            context += "\n".join([d.page_content for d in docs])
            return context
    except Exception as e:
        print(f"Lore Search Error: {e}")
    return ""

def load_text(path):
    if os.path.exists(path):
        with open(path, "r") as f: return f.read().strip()
    return ""

@app.route("/")
def serve_ui():
    return send_from_directory(app.static_folder, 'index.html')

@app.route("/api/chat", methods=["POST"])
def chat():
    global CHAT_HISTORY
    data = request.get_json()
    user_text = data.get("message", "")
    mode = data.get("mode", "standard")

    # 1. Start with the Base Persona
    system_msg = load_text(SYSTEM_PROMPT_PATH) or "You are Saga, a Norse Scribe."

    # 2. If in Ragnarok Mode, add the DM Rules and the Lore
    if mode == "ragnarok":
        system_msg += "\n\n" + load_text(DM_OVERLAY_PATH)
        lore_bits = query_lore(user_text)
        if lore_bits:
            # We inject the lore directly into the system prompt for this turn
            system_msg += "\n\nUse the following lore to inform your response:\n" + lore_bits

    # 3. Build the payload
    messages = [{"role": "system", "content": system_msg}]
    for msg in CHAT_HISTORY[-6:]: # Keep last 3 turns of context
        messages.append(msg)
    messages.append({"role": "user", "content": user_text})

    # 4. Talk to the Brain
    try:
        r = requests.post(f"{OLLAMA_URL}/api/chat", json={
            "model": MODEL,
            "messages": messages,
            "stream": False
        }, timeout=120)
        
        reply = r.json()["message"]["content"]
        CHAT_HISTORY.append({"role": "user", "content": user_text})
        CHAT_HISTORY.append({"role": "assistant", "content": reply})
        
        return jsonify({"message": {"role": "assistant", "content": reply}})
    except Exception as e:
        return jsonify({"message": {"role": "assistant", "content": f"*The hearth flickers and dies...* ({str(e)})"}})

@app.route("/api/mind", methods=["GET"])
def get_mind():
    return jsonify({"stress": psutil.cpu_percent(), "status": "Online"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
