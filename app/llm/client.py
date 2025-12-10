import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_llm(model_name: str = "gemini-3-pro-preview", temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    """
    Returns an instance of the Google Gemini Chat model.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key.startswith("ovdje_ide"):
        print("CRITICAL WARNING: GOOGLE_API_KEY is missing or invalid in .env!")
        return None

    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=api_key,
        convert_system_message_to_human=True
    )
    return llm
