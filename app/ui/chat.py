
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

print(f"[DB] Active data layer (cl_data._data_layer) = {type(cl_data._data_layer).__name__}")
print(f"[DB] Active data layer (cl.data_layer)      = {type(getattr(cl, 'data_layer', None)).__name__}")

import sys
import os
import json
import re

# Ensure the root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.data.inventory_repo import InventoryRepository
from app.llm.client import get_llm
from app.rag.engine import RagEngine
from chainlit.input_widget import Select, Switch, Slider
import app.core.persistence as p
import chainlit.data as cl_data
from app.config import settings

# Debug: Print resolved auth settings (no secrets)
print(f"[AUTH] Resolved settings: AUTH_MODE={settings.AUTH_MODE} DEV_NO_AUTH={settings.DEV_NO_AUTH} ADMIN_IDENTIFIER={settings.ADMIN_IDENTIFIER}")

# (Moved to top - hard registration)

@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    """
    Password authentication callback with dev/prod modes.
    No hardcoded credentials - all validation from environment variables.
    """
    print(f"[AUTH] auth_callback called: AUTH_MODE={settings.AUTH_MODE} DEV_NO_AUTH={settings.DEV_NO_AUTH} username={username}")
    await ensure_db_init()

    # DEV no-auth bypass
    if settings.AUTH_MODE == "dev" and settings.DEV_NO_AUTH:
        print("[AUTH] DEV_NO_AUTH enabled: authentication bypassed")
        return cl.User(identifier=settings.ADMIN_IDENTIFIER, metadata={"role": "admin", "mode": "dev-no-auth"})

    # Prod / Dev with auth: require password configured
    if not settings.ADMIN_PASSWORD:
        print("[AUTH] ADMIN_PASSWORD is missing; refusing login.")
        return None

    if username != settings.ADMIN_IDENTIFIER:
        return None

    if not secrets.compare_digest(password, settings.ADMIN_PASSWORD):
        return None

    return cl.User(identifier=username, metadata={"role": "admin", "mode": settings.AUTH_MODE})

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

from app.core.persistence import SQLiteDataLayer

# Environment variables are loaded in app.config.settings

# Auth startup log
auth_secret = os.getenv("CHAINLIT_AUTH_SECRET")
if auth_secret:
    print(f"[AUTH] CHAINLIT_AUTH_SECRET is present (length: {len(auth_secret)})")
else:
    print("[AUTH] WARNING: CHAINLIT_AUTH_SECRET not found in .env")

rag_engine = RagEngine()

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
        
        msg = cl.Message(content=f"🚀 Izvršavam: `{command}` na `{hostname}`...")
        await msg.send()
        
        # 1. Fetch Device Params from DB
        repo = InventoryRepository()
        device = repo.get_device_by_hostname(hostname)
        
        if not device:
            msg.content = f"❌ Greška: Uređaj `{hostname}` nije pronađen u inventaru."
            await msg.update()
            return

        # 2. Setup Connection Manager
        ssh_key = os.getenv("SSH_KEY_PATH")
        # Warn if no key key but proceed (might be password auth if we implemented it, but we standardized on key)
        
        conn_mgr = ConnectionManager(private_key_path=ssh_key)
        
        # 3. Execute
        result = await conn_mgr.execute(device, command)
        
        msg.content = f"✅ **Rezultat ({hostname}):**\n```\n{result}\n```"
        await msg.update()
        
    except Exception as e:
        await cl.Message(content=f"❌ Greška prilikom izvršavanja callbacka: {e}").send()

@cl.action_callback("reject_execution")
async def on_reject(action: cl.Action):
    """
    Callback when user clicks '❌ ODBIJI'.
    """
    await action.remove()
    await cl.Message(content="🚫 Akcija otkazana od strane korisnika.").send()

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Spoji se online",
            message="Želim se spojiti na udaljeni uređaj. (SSH Placeholder)",
            icon="/public/icons/terminal.svg",
            ),
        cl.Starter(
            label="Skeniraj Mrežu",
            message="Skeniraj mrežu za aktivne uređaje. (Nmap Placeholder)",
            icon="/public/icons/radar.svg",
            ),
        cl.Starter(
            label="Status Sustava",
            message="Provjeri status servera i servisa. (Healthcheck Placeholder)",
            icon="/public/icons/activity.svg",
            ),
        cl.Starter(
            label="Analiziraj Inventar",
            message="Koji uređaji su trenutno u bazi?",
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
    system_instruction = f"""Ti si AI SysAdmin Agent.
Tvoj cilj je pomoći korisniku s održavanjem servera i mrežne opreme.

KONTEKST ZNANJA (RAG):
{context_str}

**INSTRUKCIJE ZA VISION (SLIKE)**:
Ako korisnik pošalje sliku, analiziraj je detaljno. 
- Ako je kabel, identificiraj tip (RJ45, DB9, SFP, itd.).
- Ako je screenshot, pročitaj tekst i objasni što se događa.

**INSTRUKCIJE ZA IZVRŠAVANJE NAREDBI**:
Ako korisnik zatraži akciju koja zahtijeva izvršavanje CLI naredbe na serveru (npr. 'provjeri disk', 'restartaj nginx', 'pokaži vlanove'), NE izvršavaj ju odmah.
Umjesto toga, predloži akciju vraćanjem JSON bloka na kraju odgovora.

**OBAVEZAN FORMAT ZA AKCIJE**:
Objasni plan riječima, a zatim dodaj:
```json
{{
  "hostname": "TARGET_HOSTNAME_FROM_DB",
  "command": "EXACT_CLI_COMMAND",
  "reason": "Kratko objašnjenje zašto"
}}
```

Pazi:
1. `hostname` mora odgovarati hostnamu iz inventara (ako znaš, ili pretpostavi iz razgovora).
2. `command` mora biti sigurna (nema `rm -rf` itd.).

DANAŠNJI ZAHTJEV: {message.content}
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
            display_text = "Generirao sam prijedlog akcije (vidi dolje):"

        msg = cl.Message(content=display_text)
        
        if action_data:
            # Create Actions
            # FIX: payload is now required in Chainlit 2.x
            actions = [
                cl.Action(
                    name="approve_execution", 
                    value=json.dumps(action_data), 
                    payload=action_data,
                    label="✅ ODOBRI", 
                    description=f"Run {action_data.get('command')}"
                ),
                cl.Action(
                    name="reject_execution", 
                    value="cancel", 
                    payload={}, # Empty payload for reject
                    label="❌ ODBIJI"
                )
            ]
            msg.actions = actions
            # Add explicit text about the action details in the message body too
            msg.content += f"\n\n> **Prijedlog Akcije** ⚡\n> - **Host:** `{action_data.get('hostname')}`\n> - **Naredba:** `{action_data.get('command')}`\n> - **Razlog:** {action_data.get('reason')}"
            
        await msg.send()

    except Exception as e:
        await cl.Message(content=f"Greška: {str(e)}").send()

# Helpers
async def handle_pdf(element):
    msg = cl.Message(content=f"⚙️ Analiziram PDF: {element.name}...")
    await msg.send()
    try:
        temp_path = f"temp_{element.name}"
        with open(temp_path, "wb") as f:
            with open(element.path, "rb") as s: f.write(s.read())
        num = await cl.make_async(rag_engine.ingest_document)(temp_path)
        msg.content = f"✅ Naučeno {num} segmenata."
        await msg.update()
    except Exception as e:
        msg.content = f"❌ Greška: {e}"
        await msg.update()

async def handle_csv(element):
    msg = cl.Message(content=f"📊 Uvozim CSV: {element.name}...")
    await msg.send()
    try:
        temp_path = f"temp_{element.name}"
        with open(temp_path, "wb") as f:
            with open(element.path, "rb") as s: f.write(s.read())
        repo = InventoryRepository()
        count = await cl.make_async(repo.bulk_import_from_csv)(temp_path)
        msg.content = f"✅ Dodano {count} uređaja."
        await msg.update()
    except Exception as e:
        msg.content = f"❌ Greška: {e}"
        await msg.update()
