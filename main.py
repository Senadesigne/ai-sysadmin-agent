import os
import subprocess
import sys

def main():
    """
    Entry point to run the Chainlit application.
    """
    print("Starting AI SysAdmin Agent...")
    
    # Path to the chainlit application file
    # unique entry point for chainlit is usually needed
    app_path = os.path.join("app", "ui", "chat.py")
    
    if not os.path.exists(app_path):
        print(f"Error: UI file not found at {app_path}")
        return
            
    # Run chainlit
    cmd = ["chainlit", "run", app_path, "-w"]
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
