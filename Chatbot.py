import os

from openai import OpenAI
from google import genai

# API Clients

openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

gemini_client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# OpenAI configration

def ask_openai(prompt: str):
    response = openai_client.responses.create(
        model="gpt-5.5",
        instructions=SYSTEM_GUARDRAILS,
        input=prompt,
    )

    return response.output_text


# Gemini config

# def ask_gemini(prompt: str):
#     response = gemini_client.models.generate_content(
#         model="gemini-2.5-pro",
#         contents=f"""
# {SYSTEM_GUARDRAILS}

# User:
# {prompt}
# """,
#     )

#     return response.text


# Main

while True:
    print("\nChoose Model")
    print("1. OpenAI")
    print("2. Gemini")
    print("3. Exit")

    choice = input("Enter choice: ")

    if choice == "3":
        break

    print("\nQuestion: Where am I working?")
    prompt = input("\nYou: ")

    try:
        if choice == "1":
            answer = ask_openai(prompt)

        elif choice == "2":
            answer = ask_gemini(prompt)

        else:
            print("Invalid choice")
            continue

        print("\nAI:")
        print(answer)

    except Exception as e:
        print("\nError:")
        print(e)
