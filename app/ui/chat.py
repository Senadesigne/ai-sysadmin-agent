from app.config import settings

# import app.patches # Apply 500 error fix - DISABLED due to auth conflict
import chainlit as cl
import chainlit.data as cl_data
from app.ui.data_layer import SQLiteDataLayer
from app.ui.db import ensure_db_init
import secrets

_dl = SQLiteDataLayer()

# Postavi na sva poznata mjesta (različite Chainlit verzije koriste različito)
cl_data._data_layer = _dl
setattr(cl_data, "data_layer", _dl)
setattr(cl, "data_layer", _dl)

if settings.DEBUG:
    print(f"[DB] Active data layer (cl_data._data_layer) = {type(cl_data._data_layer).__name__}")
    print(f"[DB] Active data layer (cl.data_layer)      = {type(getattr(cl, 'data_layer', None)).__name__}")

import sys
import os
import json
import re
import tempfile
import uuid
from pathlib import Path

# Ensure the root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.data.inventory_repo import InventoryRepository
from app.llm.client import get_llm
from app.rag.engine import get_rag_engine
from chainlit.input_widget import Select, Switch, Slider
import chainlit.data as cl_data


# Debug: Print resolved auth settings (no secrets)
if settings.DEBUG:
    print(f"[AUTH] Resolved settings: AUTH_MODE={settings.AUTH_MODE} DEV_NO_AUTH={settings.DEV_NO_AUTH} ADMIN_IDENTIFIER={settings.ADMIN_IDENTIFIER}")

# (Moved to top - hard registration)

@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    """
    Password authentication callback with dev/prod modes.
    No hardcoded credentials - all validation from environment variables.
    """
    if settings.DEBUG:
        print(f"[AUTH] auth_callback called: AUTH_MODE={settings.AUTH_MODE} DEV_NO_AUTH={settings.DEV_NO_AUTH} username={username}")
    await ensure_db_init()

    # DEV no-auth bypass
    if settings.AUTH_MODE == "dev" and settings.DEV_NO_AUTH:
        if settings.DEBUG:
            print("[AUTH] DEV_NO_AUTH enabled: authentication bypassed")
        return cl.User(identifier=settings.ADMIN_IDENTIFIER, metadata={"role": "admin", "mode": "dev-no-auth"})

    # Prod / Dev with auth: require password configured
    if not settings.ADMIN_PASSWORD:
        print("[AUTH] ADMIN_PASSWORD is missing; refusing login.")
        return None

    # Normalize inputs
    expected_user = (settings.ADMIN_IDENTIFIER or "").strip()
    expected_pass = (settings.ADMIN_PASSWORD or "")
    provided_user = (username or "").strip()
    provided_pass = (password or "")

    # Safe debug logs (DO NOT print the password itself)
    if settings.DEBUG:
        print(f"[AUTH][DEBUG] Expected username: {repr(expected_user)}")
        print(f"[AUTH][DEBUG] Provided username: {repr(provided_user)}")
        print(f"[AUTH][DEBUG] Expected password length: {len(expected_pass)}")
        print(f"[AUTH][DEBUG] Provided password length: {len(provided_pass)}")
        print(f"[AUTH][DEBUG] Username equality: {provided_user.lower() == expected_user.lower()}")
        print(f"[AUTH][DEBUG] Password stripped equality: {provided_pass.strip() == expected_pass.strip()}")

    # Make username check case-insensitive and trimmed
    if provided_user.lower() != expected_user.lower():
        if settings.DEBUG:
            print("[AUTH][DEBUG] Username mismatch -> refusing login")
        return None

    # Make password check robust to whitespace/CRLF
    if not secrets.compare_digest(provided_pass.strip(), expected_pass.strip()):
        if settings.DEBUG:
            print("[AUTH][DEBUG] Password mismatch -> refusing login")
        return None

    # On success return
    return cl.User(identifier=expected_user, metadata={"role": "admin", "mode": settings.AUTH_MODE})

# Disable header auth to force password auth
# @cl.header_auth_callback
# def header_auth(headers):
#     # Auto-login for dev environment to bypass potential session state bugs
#     return cl.User(identifier="antigravity_dev_user", metadata={"role": "admin"})
# MONKEYPATCH: Fix for older libraries expecting langchain.verbose
import langchain
if not hasattr(langchain, 'verbose'):
    setattr(langchain, 'verbose', False)

# MONKEYPATCH: Fix for langchain-google-genai expecting MediaResolution
import google.generativeai as genai
if hasattr(genai, "GenerationConfig") and not hasattr(genai.GenerationConfig, "MediaResolution"):
    class MediaResolution:
        AUTO = "auto"
    setattr(genai.GenerationConfig, "MediaResolution", MediaResolution)

from app.core.execution import ConnectionManager
from langchain_core.messages import HumanMessage


# Environment variables are loaded in app.config.settings

# Auth startup log
auth_secret = os.getenv("CHAINLIT_AUTH_SECRET")
if auth_secret:
    print(f"[AUTH] CHAINLIT_AUTH_SECRET is present (length: {len(auth_secret)})")
else:
    print("[AUTH] WARNING: CHAINLIT_AUTH_SECRET not found in .env")

rag_engine = get_rag_engine()

# --- PERSISTENCE SETUP ---
# (Data layer already registered at top)

def extract_json_action(text: str):
    """
    Attempts to extract a JSON block from the text.
    Looking for ```json ... ``` or just { ... } at the end.
    """
    # Regex for json block code
    json_block = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_block:
        try:
            return json.loads(json_block.group(1))
        except:
            pass
    
    # Fallback: find last curly brace pair
    try:
        # Simplistic heuristic: find first { and last }
        # logic: start searching from the end to find the last valid JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            potential_json = text[start:end+1]
            # Verify if it's valid json
            return json.loads(potential_json)
    except:
        pass
    
    return None

@cl.action_callback("approve_execution")
async def on_approve(action: cl.Action):
    """
    Callback when user clicks '✅ ODOBRI'.
    """
    try:
        # Chainlit 2.x uses .payload (dict), fallback to .value (json string)
        if hasattr(action, 'payload') and action.payload:
            payload = action.payload
        else:
            payload = json.loads(action.value)
            
        hostname = payload.get("hostname")
        command = payload.get("command")
        
        await action.remove() # Remove buttons to prevent double-click
        
        msg = cl.Message(content=f"🚀 Executing: `{command}` on `{hostname}`...")
        await msg.send()
        
        # 1. Fetch Device Params from DB
        repo = InventoryRepository()
        device = repo.get_device_by_hostname(hostname)
        
        if not device:
            msg.content = f"❌ Error: Device `{hostname}` not found in inventory."
            await msg.update()
            return

        # 2. Setup Connection Manager
        ssh_key = os.getenv("SSH_KEY_PATH")
        # Warn if no key key but proceed (might be password auth if we implemented it, but we standardized on key)
        
        conn_mgr = ConnectionManager(private_key_path=ssh_key)
        
        # 3. Execute
        result = await conn_mgr.execute(device, command)
        
        msg.content = f"✅ **Result ({hostname}):**\n```\n{result}\n```"
        await msg.update()
        
    except Exception as e:
        await cl.Message(content=f"❌ Error during callback execution: {e}").send()

@cl.action_callback("reject_execution")
async def on_reject(action: cl.Action):
    """
    Callback when user clicks '❌ ODBIJI'.
    """
    await action.remove()
    await cl.Message(content="🚫 Action cancelled by user.").send()

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Connect Online",
            message="I want to connect to a remote device. (SSH Placeholder)",
            icon="/public/icons/terminal.svg",
            ),
        cl.Starter(
            label="Scan Network",
            message="Scan network for active devices. (Nmap Placeholder)",
            icon="/public/icons/radar.svg",
            ),
        cl.Starter(
            label="System Status",
            message="Check server and service status. (Healthcheck Placeholder)",
            icon="/public/icons/activity.svg",
            ),
        cl.Starter(
            label="Analyze Inventory",
            message="Which devices are currently in the database?",
            icon="/public/icons/inventory.svg",
            ),
    ]

@cl.on_chat_start
async def start():
    await ensure_db_init()
    repo = InventoryRepository()
    repo.initialize_db()
    # Clean start - no welcome message

@cl.on_message
async def main(message: cl.Message):
    llm = get_llm()
    
    # --- FILE HANDLING (CSV/PDF/IMAGES) ---
    image_content = []
    
    if message.elements:
        for element in message.elements:
            if "pdf" in element.mime:
                await handle_pdf(element)
            elif "csv" in element.mime or element.name.endswith(".csv"):
                await handle_csv(element)
            elif "image" in element.mime:
                # Store images to send to LLM
                with open(element.path, "rb") as f:
                    image_data = f.read()
                    import base64
                    b64_img = base64.b64encode(image_data).decode('utf-8')
                    image_content.append(
                        {"type": "image_url", "image_url": {"url": f"data:{element.mime};base64,{b64_img}"}}
                    )
        
        # If message has no text AND no images, prompt might be empty.
        if not message.content and not image_content:
            return 
    
    # --- RAG ---
    # Only use RAG if there is text to query, otherwise context is empty
    context_str = ""
    if message.content:
        context_chunks = rag_engine.query(message.content)
        context_str = "\n\n".join(context_chunks)

    # --- PROMPT FOR ACTION ---
    system_instruction = f"""You are an AI SysAdmin Agent.
Your goal is to help the user with server and network equipment maintenance.

KNOWLEDGE CONTEXT (RAG):
{context_str}

**VISION INSTRUCTIONS (IMAGES)**:
If the user sends an image, analyze it in detail.
- If it's a cable, identify the type (RJ45, DB9, SFP, etc.).
- If it's a screenshot, read the text and explain what's happening.

**COMMAND EXECUTION INSTRUCTIONS**:
If the user requests an action that requires executing a CLI command on a server (e.g., 'check disk', 'restart nginx', 'show vlans'), DO NOT execute it immediately.
Instead, propose the action by returning a JSON block at the end of your response.

**REQUIRED FORMAT FOR ACTIONS**:
Explain the plan in words, then add:
```json
{{
  "hostname": "TARGET_HOSTNAME_FROM_DB",
  "command": "EXACT_CLI_COMMAND",
  "reason": "Brief explanation why"
}}
```

Note:
1. `hostname` must match a hostname from the inventory (if you know it, or assume from conversation).
2. `command` must be safe (no `rm -rf` etc.).

TODAY'S REQUEST: {message.content}
"""

    try:
        # Construct message payload
        # System prompt + User Message (Text + Optional Images)
        
        # Note: ChatGoogleGenerativeAI (Langchain) handles list of content blocks for multimodal
        user_message_content = []
        if message.content:
            user_message_content.append({"type": "text", "text": system_instruction})
        else:
             # If no text, at least send the system instructions as context? 
             # For vision-only turn, we usually put system prompt in SystemMessage or merge.
             # Simplification: Append system prompt header to the text block.
             user_message_content.append({"type": "text", "text": system_instruction})
             
        user_message_content.extend(image_content)
        
        response = llm.invoke([HumanMessage(content=user_message_content)])
        
        # Langchain response content handling
        content_text = response.content
        if isinstance(content_text, list):
            content_text = "".join([p['text'] for p in content_text if 'text' in p])
        else:
            content_text = str(content_text)
            
        # Detect Action
        action_data = extract_json_action(content_text)
        
        # Remove JSON from display text to make it cleaner
        display_text = re.sub(r"```json\s*\{.*?\}\s*```", "", content_text, flags=re.DOTALL).strip()
        if not display_text:
            display_text = "I generated an action proposal (see below):"

        msg = cl.Message(content=display_text)
        
        if action_data:
            # Create Actions
            # FIX: payload is now required in Chainlit 2.x
            actions = [
                cl.Action(
                    name="approve_execution", 
                    value=json.dumps(action_data), 
                    payload=action_data,
                    label="✅ APPROVE", 
                    description=f"Run {action_data.get('command')}"
                ),
                cl.Action(
                    name="reject_execution", 
                    value="cancel", 
                    payload={}, # Empty payload for reject
                    label="❌ REJECT"
                )
            ]
            msg.actions = actions
            # Add explicit text about the action details in the message body too
            msg.content += f"\n\n> **Action Proposal** ⚡\n> - **Host:** `{action_data.get('hostname')}`\n> - **Command:** `{action_data.get('command')}`\n> - **Reason:** {action_data.get('reason')}"
            
        await msg.send()

    except Exception as e:
        await cl.Message(content=f"Error: {str(e)}").send()

# Helpers
def create_temp_file(original_filename: str) -> str:
    """
    Create a safe temporary file path with unique name.
    Uses .data/tmp/ directory and ensures it exists.
    Returns the full path to the temporary file.
    """
    # Create .data/tmp directory if it doesn't exist
    temp_dir = Path(".data/tmp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename to avoid collisions
    file_ext = Path(original_filename).suffix
    unique_name = f"{uuid.uuid4().hex}_{Path(original_filename).stem}{file_ext}"
    
    return str(temp_dir / unique_name)

async def handle_pdf(element):
    msg = cl.Message(content=f"⚙️ Analyzing PDF: {element.name}...")
    await msg.send()
    temp_path = None
    try:
        # Create safe temporary file
        temp_path = create_temp_file(element.name)
        with open(temp_path, "wb") as f:
            with open(element.path, "rb") as s: 
                f.write(s.read())
        
        num = await cl.make_async(rag_engine.ingest_document)(temp_path)
        msg.content = f"✅ Learned {num} segments."
        await msg.update()
    except Exception as e:
        msg.content = f"❌ Error: {e}"
        await msg.update()
    finally:
        # Always cleanup temp file if it was created
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass  # Ignore cleanup errors

async def handle_csv(element):
    msg = cl.Message(content=f"📊 Importing CSV: {element.name}...")
    await msg.send()
    temp_path = None
    try:
        # Create safe temporary file
        temp_path = create_temp_file(element.name)
        with open(temp_path, "wb") as f:
            with open(element.path, "rb") as s: 
                f.write(s.read())
        
        repo = InventoryRepository()
        count = await cl.make_async(repo.bulk_import_from_csv)(temp_path)
        msg.content = f"✅ Added {count} devices."
        await msg.update()
    except Exception as e:
        msg.content = f"❌ Error: {e}"
        await msg.update()
    finally:
        # Always cleanup temp file if it was created
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass  # Ignore cleanup errors
