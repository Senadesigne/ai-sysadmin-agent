import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.rag.engine import RagEngine

def main():
    if len(sys.argv) < 2:
        print("Usage: python ask_agent.py <question>")
        sys.exit(1)

    question = sys.argv[1]
    
    print(f"Agent, pitanje: {question}")
    print("-" * 30)

    try:
        engine = RagEngine()
        results = engine.query(question, k=3)
        
        if not results:
            print("Agent: Nemam informacija o tome u svojoj bazi znanja.")
        else:
            print("Agent zna sljedeće:\n")
            for i, res in enumerate(results):
                print(f"--- Izvor {i+1} ---")
                print(res[:500] + "..." if len(res) > 500 else res)
                print("\n")

    except Exception as e:
        print(f"Error querying agent: {e}")

if __name__ == "__main__":
    main()
