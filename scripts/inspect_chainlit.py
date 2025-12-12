
import inspect
import chainlit.server
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:




    # Inspect chainlit.types to see what is available
    import chainlit.types
    print("\nCONTENTS OF chainlit.types:")
    print("---------------------------------------------------")
    print(dir(chainlit.types))
    
    # Check BaseDataLayer signature
    import chainlit.data
    print("\nSIGNATURE OF BaseDataLayer.get_user:")
    print("---------------------------------------------------")
    try:
        sig = inspect.signature(chainlit.data.BaseDataLayer.get_user)
        print(f"Signature: {sig}")
    except Exception as e:
        print(f"Error inspecting get_user: {e}")




except Exception as e:
    print(f"Error getting source: {e}")

try:
    print("\nDEPENDENCY OVERRIDES:")
    print(chainlit.server.app.dependency_overrides)
except Exception as e:
    print(f"Error checking overrides: {e}")
