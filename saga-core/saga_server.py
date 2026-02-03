#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
import requests
import os

# Initialize the Flask application
# static_folder='static' tells Flask to look in the /static directory for UI files
app = Flask(__name__, static_folder='static')

# --- CONFIGURATION FROM ENVIRONMENT ---
# These allow us to change settings in docker-compose.yml without touching the code.
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://saga-ollama:11434")
MODEL = os.environ.get("SAGA_MODEL", "llama3:latest")

# The path where Saga's personality is defined. 
# This is mapped via Docker volume to the local prompts folder.
SYSTEM_PROMPT_PATH = "/saga/prompts/saga_system_active.txt"


# At the top of saga_server.py
CHAT_HISTORY = []

@app.route("/api/chat", methods=["POST"])
def chat():
    global CHAT_HISTORY
    data = request.get_json(force=True)
    
    # Get the new message from the Web UI
    user_msg = ""
    if "messages" in data:
        user_msg = data["messages"][0]["content"]
    
    # Add User's new message to our permanent history
    CHAT_HISTORY.append({"role": "user", "content": user_msg})

    # Keep only the last 10 messages so the prompt doesn't get too long
    # (The 'sliding window' technique)
    # CHAT_HISTORY = CHAT_HISTORY[-10:]

    identity = load_identity()

    # Build the prompt using the ENTIRE history
    convo_str = ""
    for msg in CHAT_HISTORY:
        role = msg["role"].capitalize()
        convo_str += f"{role}: {msg['content']}\n"

    full_prompt = f"{identity}\n\n{convo_str}Saga:"

    reply = call_ollama(full_prompt, data.get("model", MODEL))

    # Add Saga's reply to the permanent history
    CHAT_HISTORY.append({"role": "assistant", "content": reply})

    return jsonify({
        "message": {"role": "assistant", "content": reply}
    })

def load_identity():
    """
    Reads the system prompt from the disk. 
    By loading this every request, we can tweak the .txt file 
    and see changes immediately without restarting the server.
    """
    try:
        with open(SYSTEM_PROMPT_PATH, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        # Fallback if the file is missing so the system doesn't crash.
        return "You are Saga, a helpful Nordic-inspired AI."

def call_ollama(prompt: str, model: str) -> str:
    """
    Sends the formatted string to the Ollama container's API.
    We use the /api/chat endpoint but send a single block of text
    to maintain strict control over how Saga sees the history.
    """
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False, # Set to False for easier JSON handling
            },
            timeout=300, # Long timeout because LLMs can be slow on CPU/older GPUs
        )
        r.raise_for_status()
        return r.json()["message"]["content"]
    except Exception as e:
        return f"Error connecting to the hearth: {str(e)}"

# --- UI ROUTES ---

@app.route("/")
def serve_ui():
    """
    Serves the index.html file to the browser.
    This allows you to access the interface by visiting the server's IP in a browser.
    """
    return send_from_directory(app.static_folder, 'index.html')

# --- API ROUTES ---

@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main entry point for both the CLI and the Web UI.
    Takes a list of messages and wraps them in Saga's identity.
    """
    # force=True ensures we parse JSON even if the Content-Type header is missing
    data = request.get_json(force=True)
    messages = data.get("messages", [])
    
    # Use model from request if provided, otherwise default to ENV setting
    model = data.get("model", MODEL)

    # Always reload identity so Saga's 'soul' stays fresh with prompt updates
    identity = load_identity()

    # Convert the message objects into a single dialogue string for the model
    convo = []
    for msg in messages:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        convo.append(f"{role}: {content}")

    # Build the 'Full Prompt' - This is what the LLM actually sees.
    # We append 'Saga:' at the end to nudge the AI to start typing as her.
    full_prompt = (
        f"{identity}\n\n"
        + "\n".join(convo)
        + "\nSaga:"
    )

    # Get the response from the Ollama backend
    reply = call_ollama(full_prompt, model)

    # Return the response in a format compatible with the CLI and Web UI scripts
    return jsonify({
        "model": model,
        "message": {
            "role": "assistant",
            "content": reply,
        },
        "done": True,
    })

if __name__ == "__main__":
    # host='0.0.0.0' is critical: it tells Flask to listen on all network interfaces,
    # allowing connections from outside the Docker container (like your laptop's browser).
    app.run(host="0.0.0.0", port=8000)
