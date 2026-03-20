#!/usr/bin/env python3
import requests
import sys

API_URL = "http://127.0.0.1:8000/api/chat"

def main():
    current_mode = "standard"
    print("Welcome to Saga's hearth! Type 'exit' to quit.")
    print("Commands: /mode (toggle Ragnarok), exit (quit)\n")

    while True:
        user_input = input(f"[{current_mode}] You: ").strip()
        
        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye from Saga!")
            break
        
        # Simple toggle for testing the different server paths
        if user_input.lower() == "/mode":
            current_mode = "ragnarok" if current_mode == "standard" else "standard"
            print(f"--- Mode switched to: {current_mode} ---")
            continue

        try:
            # The server expects "message" as a STRING and "mode" as a STRING
            payload = {
                "message": user_input,
                "mode": current_mode
            }

            response = requests.post(API_URL, json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()

            # Server returns: {"message": {"role": "assistant", "content": "..."}}
            reply = data.get("message", {}).get("content", "The Scribe is silent...")
            print(f"Saga: {reply}\n")

        except Exception as e:
            print(f"\n*The hearth flickers and dies...*")
            print(f"Error: {e}\n")

if __name__ == "__main__":
    main()
