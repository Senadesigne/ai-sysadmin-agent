import logging
from fastapi import Request
from chainlit.server import app, get_current_user
from chainlit.user import User

logger = logging.getLogger("chainlit.monkeypatch")

async def custom_get_current_user_header_auth(request: Request = None):
    """
    Monkeypatch wrapper for get_current_user that works with header_auth.
    Instead of relying on OAuth tokens, it creates a dev user directly.
    """
    try:
        # For header auth, we bypass the token system and return a dev user
        return User(identifier="antigravity_dev_user", metadata={"role": "admin"})
    except Exception as e:
        logger.error(f"Error in custom header auth get_current_user: {e}")
        return None

# Apply the Override to the FastAPI app
app.dependency_overrides[get_current_user] = custom_get_current_user_header_auth
logger.info("Header auth monkeypatch applied successfully: get_current_user dependency overridden.")