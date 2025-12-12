
import logging

import logging
import inspect
from fastapi import Depends
from chainlit.server import app, get_current_user
from chainlit.user import User

logger = logging.getLogger("chainlit.monkeypatch")

# Dynamically extract 'reuseable_oauth' from the original function signature
# because it is not exported in chainlit.server.__all__
try:
    sig = inspect.signature(get_current_user)
    # The 'token' parameter has a default value of Depends(reuseable_oauth)
    # We access .dependency to get the callable
    reuseable_oauth = sig.parameters['token'].default.dependency
    logger.info("Successfully extracted reuseable_oauth dependency.")
except Exception as e:
    logger.error(f"Failed to extract reuseable_oauth: {e}")
    # Fallback: Define a dummy dependency if extraction fails (unlikely)
    async def reuseable_oauth(): return None

async def custom_get_current_user(token: str = Depends(reuseable_oauth)):
    """
    Monkeypatch wrapper for get_current_user.
    Intercepts the return value. If it's a dict (caused by Pydantic v2/Chainlit serialization issues),
    it manually re-hydrates it into a cl.User object.
    """
    # 1. Call the original logic
    # Note: We call it directly as a coroutine, passing the token we got from dependency
    try:
        user = await get_current_user(token)
    except Exception as e:
        logger.error(f"Error in upstream get_current_user: {e}")
        return None

    # 2. Apply the Fix
    if isinstance(user, dict):
        logger.warning(f"HOTFIX: Detected 'dict' user instead of Object. Hydrating... Data: {user}")
        try:
            user_obj = User(
                identifier=user.get("identifier") or user.get("id", "unknown"),
                metadata=user.get("metadata", {}),
            )
            return user_obj
        except Exception as e:
            logger.error(f"Failed to hydrate user from dict: {e}")
            return None
    
    return user

# 3. Apply the Override to the FastAPI app
# This tells FastAPI: "Whenever someone asks for 'get_current_user', run 'custom_get_current_user' instead."
app.dependency_overrides[get_current_user] = custom_get_current_user
logger.info("Monkeypatch applied successfully: get_current_user dependency overridden.")
