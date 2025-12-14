# Chainlit Perzistencija - Setup Guide

## Problem
Chainlit aplikacija nije spremala povijest razgovora i javila je grešku "Couldn't resume chat: Thread not found".

## Rješenje
Implementiran je **Custom Data Layer** koristeći **aiosqlite** za lokalnu perzistenciju.

## Implementirane datoteke

### 1. `app/ui/db.py`
- Inicijalizacija SQLite baze (`chainlit.db`)
- Kreiranje tablica: `users`, `threads`, `steps`, `elements`, `feedbacks`
- Asinkrona konekcija s `aiosqlite`

### 2. `app/ui/data_layer.py`
- Klasa `SQLiteDataLayer` koja nasljeđuje `chainlit.data.BaseDataLayer`
- Implementirane sve potrebne metode:
  - **User management**: `get_user`, `create_user`
  - **Thread management**: `list_threads`, `get_thread`, `create_thread`, `update_thread`, `delete_thread`
  - **Step management**: `create_step`, `update_step`, `delete_step`
  - **Element management**: `create_element`, `get_element`, `delete_element`
  - **Feedback management**: `upsert_feedback`, `delete_feedback`

### 3. `app/ui/chat.py` - Ažuriran
- Importiran novi `SQLiteDataLayer` i `init_db`
- Postavljen global data layer: `cl_data._data_layer = SQLiteDataLayer()`
- **Implementirana password autentifikacija** (`@cl.password_auth_callback`)
- Dodana inicijalizacija baze u `@cl.on_chat_start`

## Ključne značajke

### Password Authentication
```python
@cl.password_auth_callback
def password_auth(username: str, password: str) -> Optional[cl.User]:
    if username == "admin" and password == "admin":
        return cl.User(identifier="admin", metadata={"role": "admin"})
    return None
```

### Automatska inicijalizacija baze
```python
@cl.on_chat_start
async def on_chat_start():
    await init_db()  # Kreira tablice ako ne postoje
    # ... ostatak koda
```

### Thread naming za sidebar
Threadovi se automatski imenuju prema prvoj poruci korisnika (prvih 50 znakova).

## Instalacija i pokretanje

1. **Instaliraj dependency**:
   ```bash
   pip install aiosqlite
   ```

2. **Pokreni test** (opcionalno):
   ```bash
   python test_chainlit_persistence.py
   ```

3. **Pokreni aplikaciju**:
   ```bash
   chainlit run app/ui/chat.py
   ```

4. **Login podaci**:
   - Username: `admin`
   - Password: `admin`

## Rezultat

- ✅ Povijest razgovora se sprema u `chainlit.db`
- ✅ Sidebar prikazuje stare razgovore
- ✅ Refresh stranice ne briše povijest
- ✅ Greška "Thread not found" je riješena
- ✅ Lokalna perzistencija bez vanjskih servisa

## Baza podataka

Datoteka `chainlit.db` će se kreirati u root direktoriju aplikacije i sadržavat će sve potrebne tablice za Chainlit perzistenciju.

## Kompatibilnost

Implementacija je kompatibilna s Chainlit 2.x verzijama i koristi standardne Chainlit tipove i interface.