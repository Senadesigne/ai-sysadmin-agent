import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found in .env")
    exit(1)

genai.configure(api_key=api_key)

print("Fetching available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- Name: {m.name}")
            print(f"  Display: {m.display_name}")
            print(f"  Description: {m.description}")
            print("-" * 20)
except Exception as e:
    print(f"Error fetching models: {e}")
