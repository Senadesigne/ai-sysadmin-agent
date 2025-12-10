import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GOOGLE_API_KEY not found")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if "models" in data:
            print("Available Models:")
            for m in data["models"]:
                # Filter for generateContent support
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    print(f"- {m['name']}")
                    print(f"  Display: {m.get('displayName')}")
                    print("-" * 10)
        else:
            print("No models found in response.")
            print(data)
    else:
        print(f"Error fetching models: {response.status_code} - {response.text}")

except Exception as e:
    print(f"Exception: {e}")
