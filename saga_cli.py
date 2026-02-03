#!/usr/bin/env python3
import requests

API_URL = "http://127.0.0.1:8000/api/chat"

def main():
    print("Welcome to Saga's hearth! Type 'exit' to quit.\n")

    messages = []

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye from Saga!")
            break

        messages.append({"role": "user", "content": user_input})

        try:
            response = requests.post(
                API_URL,
                json={
                    "messages": messages,
                },
                timeout=300
            )
            response.raise_for_status()
            data = response.json()

            assistant_reply = data["message"]["content"]
            print(f"Saga: {assistant_reply}\n")

            messages.append({"role": "assistant", "content": assistant_reply})

        except Exception as e:
            print(f"Error communicating with Saga: {e}")

if __name__ == "__main__":
    main()
