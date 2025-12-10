import google.generativeai as genai
import sys

print(f"GenAI Version: {genai.__version__}")

try:
    print(f"Has GenerationConfig? {hasattr(genai, 'GenerationConfig')}")
    if hasattr(genai, 'GenerationConfig'):
        print(f"Has MediaResolution? {hasattr(genai.GenerationConfig, 'MediaResolution')}")
        # If missing, maybe check if it's in types?
        import google.generativeai.types as types
        print(f"In types? {hasattr(types, 'MediaResolution')}")
        
except Exception as e:
    print(f"Error: {e}")
