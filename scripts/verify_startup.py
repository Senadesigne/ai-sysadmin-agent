import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath("."))

print("Attempting to import app.ui.chat...")
try:
    import app.ui.chat
    print("SUCCESS: app.ui.chat imported.")
except ImportError as e:
    print(f"FAILURE: ImportError: {e}")
except AttributeError as e:
    print(f"FAILURE: AttributeError: {e}")
except Exception as e:
    print(f"FAILURE: Exception: {e}")
