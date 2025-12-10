from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai

print("Imports successful.")
print(f"GenAI Version: {genai.__version__}")
try:
    print(f"MediaResolution avail in GenConfig? {'MediaResolution' in dir(genai.GenerationConfig)}")
except:
    print("MediaResolution check failed")
