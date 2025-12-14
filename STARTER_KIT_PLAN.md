# STARTER_KIT_PLAN.md

## Cilj (paid starter kit, source-available)

**Proizvod:** “Chainlit Agent Starter Kit” za brzu izradu komercijalnih Chainlit agenata s provjerenim osnovama (auth, persistence, optional RAG, action approval).

**Model:** source-available + komercijalna licenca (plaća se po timu/organizaciji ili po projektu). Kod je vidljiv kupcu, ali nije slobodan za redistribuciju bez uvjeta.

**Ciljana publika:**
- Timovi koji žele brzo isporučiti internog/copilot agenta (IT, DevOps, support, ops).
- Agencije/konzultanti koji grade “chat + workflow” rješenja za klijente.
- Produkt timovi koji žele POC → produkcijski MVP bez ponovnog izmišljanja temelja.

**Glavni value:** stabilan “skeleton” koji radi out-of-the-box + jasna mjesta gdje se ubacuju vlastiti tools, promptovi i integracije.

---

## Scope v1 (minimum da se može prodavati)

V1 mora isporučiti:
- **Pouzdanu chat history + resume** funkcionalnost (sidebar threads + resume bez grešaka).
- **Konfigurabilan auth** (dev mode i produkcijski mode; bez hardcoded kredencijala).
- **Optional LLM/RAG**: app se digne i radi i bez API ključeva (uz jasan fallback).
- **Standardizirane putanje podataka** (DB, Chroma, temp) i “clean start”.
- **Čist repo**: bez tuđih tajni, bez domenskih PDF-ova u default paketu.
- **Jedan stabilan entrypoint** i quickstart upute.

Non-goals v1:
- license-key verifikacija u runtimeu
- deployment na cloud (docker/k8s) kao “one click”
- enterprise hardening (SSO, RBAC, audit)

---

## Popis problema za riješiti (iz ovog repoa)

- **Hardcoded auth**: `admin/admin` u `app/ui/chat.py`.
- **Secrets u dokumentima**: `env_setup_instructions.txt` sadrži stvarni `CHAINLIT_AUTH_SECRET` (ne smije biti u templateu).
- **Optional LLM/RAG**: `app/llm/client.py` može vratiti `None` → potencijalni crash kad se pozove `.invoke`.
- **Data pathovi**:
  - `chainlit.db` je u rootu (ok), ali treba standardizirati `.data/` ili slično.
  - `inventory.db` je relativan (repo layer u `app/data/inventory_repo.py`).
  - `Chroma` persist je hardcoded `./app/data/chroma_db` u `app/rag/engine.py`.
  - temp fajlovi `temp_<name>` u `app/ui/chat.py`.
- **Knowledge base PDF-ovi**: `app/knowledge_base/*.pdf` su domenski/specifični i ne smiju u starter kittu.
- **Dupli persistence modul**: postoji alternativni `SQLiteDataLayer` u `app/core/persistence.py` (ne koristi se) uz “pravi” u `app/ui/data_layer.py`.

---

## Koraci implementacije (10–12 koraka)

> Pravilo: svaki korak = jedan commit.

### 1) Uspostavi “product” konfiguraciju (paths + mode)
- **Fajlovi:** `app/config/settings.py`, `app/ui/db.py`, `app/rag/engine.py`, `app/data/inventory_repo.py`
- **Što se mijenja:**
  - Uvesti centralne postavke: `DATA_DIR`, `CHAINLIT_DB_PATH`, `INVENTORY_DB_PATH`, `CHROMA_DIR`.
  - Sve relativne putanje prebaciti na te postavke.
  - Default: `.data/` u rootu (gitignored).
- **Test:** pokreni `chainlit run app/ui/chat.py` i provjeri da se `.data/` kreira i da se DB-ovi stvaraju na očekivanoj lokaciji.
- **Commit:** `feat: centralize data paths under .data`

### 2) Očisti tajne iz dokumentacije + uvedi .env.example
- **Fajlovi:** `env_setup_instructions.txt` (ili zamjena), dodati `.env.example`
- **Što se mijenja:**
  - Ukloniti stvarne tajne; zamijeniti placeholderima.
  - Dodati upute kako generirati `CHAINLIT_AUTH_SECRET` lokalno.
- **Test:** “fresh clone” scenarij: kopiraj `.env.example` → `.env`, start app, nema leakova.
- **Commit:** `docs: add .env.example and remove embedded secrets`

### 3) Auth: ukloni hardcoded admin/admin, uvedi dev/prod režime
- **Fajlovi:** `app/ui/chat.py`, `.chainlit/config.toml` (po potrebi)
- **Što se mijenja:**
  - `DEV_AUTH_ENABLED=true` (default) i `DEV_AUTH_USER/DEV_AUTH_PASS` iz env-a.
  - Produkcijski mode: zahtijeva konfiguriran `CHAINLIT_AUTH_SECRET` i/ili integraciju (v1 minimalno: env-based basic auth).
- **Test:** login radi s env kredencijalima; bez env-a u dev modu koristi sigurne defaulte ili blokira s jasnom porukom.
- **Commit:** `feat: configurable auth (dev/prod) without hardcoded creds`

### 4) Optional LLM: sigurni fallback kad nema API ključa
- **Fajlovi:** `app/llm/client.py`, `app/ui/chat.py`
- **Što se mijenja:**
  - `get_llm()` uvijek vraća objekt ili eksplicitno baca “configuration error” koji UI hvata i prikazuje korisniku.
  - U `on_message`: ako LLM nije konfiguriran, vrati uputu kako ga uključiti.
- **Test:** bez `GOOGLE_API_KEY` chat se diže i odgovara “LLM nije konfiguriran”; s ključem radi normalno.
- **Commit:** `fix: graceful no-LLM mode`

### 5) Optional RAG: radi bez Chroma/embeddings, i ne ruši ingest
- **Fajlovi:** `app/rag/engine.py`, `app/ui/chat.py`, `requirements.txt`
- **Što se mijenja:**
  - `RagEngine` se inicijalizira samo ako je omogućen (`RAG_ENABLED`) i ako postoje preduvjeti.
  - Ingest PDF/MD: ako RAG off, vrati poruku i preskoči.
- **Test:** upload PDF bez ključa → poruka “RAG isključen”; s ključem → ingest i query vraćaju kontekst.
- **Commit:** `feat: optional RAG with safe fallbacks`

### 6) Ukloni dupli persistence modul (jedna istina)
- **Fajlovi:** `app/core/persistence.py`, `app/ui/data_layer.py`, `app/ui/chat.py`
- **Što se mijenja:**
  - Odabrati jednu implementaciju (preporuka: `app/ui/data_layer.py`).
  - Drugu ukloniti ili pretvoriti u `legacy/` uz jasnu oznaku (bez importanja).
- **Test:** sidebar threads + resume rade; nema import konfuzije.
- **Commit:** `chore: remove unused legacy persistence implementation`

### 7) Stabiliziraj persistence init lifecycle
- **Fajlovi:** `app/ui/chat.py`, `app/ui/db.py`
- **Što se mijenja:**
  - Inicijalizaciju DB-a raditi prije nego UI zatraži threadove (startup hook).
  - Ukloniti suvišne debug printove ili ih staviti pod `DEBUG` flag.
- **Test:** refresh na `/thread/<id>` radi; sidebar se puni bez “Thread not found”.
- **Commit:** `fix: ensure persistence DB initialized before UI queries`

### 8) Uredi temp file handling (sigurno + cleanup)
- **Fajlovi:** `app/ui/chat.py`
- **Što se mijenja:**
  - Spremanje u OS temp folder ili `.data/tmp/`.
  - Brisanje temp fajla nakon ingest/importa.
- **Test:** upload CSV/PDF, provjeri da se temp ne gomila.
- **Commit:** `fix: store uploads in temp dir and cleanup`

### 9) Knowledge base: ukloni domenske PDF-ove iz default paketa
- **Fajlovi:** `app/knowledge_base/*`, dodati `app/knowledge_base/README.md` (ili `SAMPLE.md`)
- **Što se mijenja:**
  - Maknuti PDF-ove iz distribucije (ostaviti jedan mali neutralni sample doc).
  - Jasne upute kako korisnik dodaje vlastite dokumente.
- **Test:** RAG ingest radi nad sample dokumentom.
- **Commit:** `chore: replace domain PDFs with minimal sample knowledge base`

### 10) “One command” quickstart + health check
- **Fajlovi:** `start.bat`, `run_app.bat`, `main.py`, `scripts/verify_startup.py`, `CHAINLIT_SETUP.md` (ili novi quickstart doc)
- **Što se mijenja:**
  - Jedan preporučeni način pokretanja.
  - Skripta koja provjeri env + dependency + pokaže jasne greške.
- **Test:** clean venv → `run_app.bat` → app se digne; verify skripta prolazi.
- **Commit:** `docs: streamline quickstart and add startup verification`

### 11) Minimalno “product hardening” za v1
- **Fajlovi:** `app/core/execution.py`, `app/ui/chat.py`
- **Što se mijenja:**
  - Proširiti blacklist + logging (bez osjetljivih podataka).
  - Jasna pravila oko “approve execution”.
- **Test:** pokušaj zabranjenih naredbi → blokirano; normalne → prolaze.
- **Commit:** `security: tighten command validation and auditing`

---

## Licenciranje i distribucija (paid, source-available)

### Fajlovi koje dodati (u kasnijim commitovima)
- `LICENSE-COMMERCIAL.md` (glavna licenca)
- `COMMERCIAL-TERMS.md` (uvjeti korištenja, seat/project licensing, support)
- `THIRD_PARTY_NOTICES.md` (Chainlit, LangChain, Chroma, itd.)
- `EULA.md` (ako treba “click-through”)
- `SECURITY.md` (vulnerability reporting; opcionalno)

### Release ZIP (što uključiti/isključiti)
**Uključiti:**
- source kod (`app/`, `public/`, `scripts/`, `requirements.txt`, `start.bat`, `run_app.bat`, `main.py`)
- docs: quickstart + plan + license/terms + third-party notices
- `.env.example`

**Isključiti:**
- sve `.db` datoteke (`*.db`)
- `app/data/chroma_db/**` i binarne artefakte
- `app/knowledge_base/*.pdf` (osim malog sample-a)
- lokalne planove/dev bilješke (`plan_za_sidebar.md`, `NEXT_SESSION_BRIEF.md`, itd.)

**Kako buildati zip:**
- napraviti `release/` pipeline ili skriptu (npr. `scripts/build_release_zip.py`) koja kopira samo whitelist set.

---

## Što ostaje za v2

- **License key verification** (online/offline, periodic check, grace period).
- **Deployment opcije**: Docker image, docker-compose, systemd service, Windows service.
- **Auth upgrade**: SSO (OIDC/SAML), RBAC, per-user policies.
- **Observability**: structured logging, trace IDs, metrics.
- **Advanced hardening**: allowlist commands per host, approval policies, secrets management.
- **Pluggable providers**: OpenAI/Anthropic/Azure/GCP, embeddings switch.

---

## Checklista: “Ready to sell”

- [ ] Repo nema nikakve stvarne tajne (ni u docovima ni u primjerima).
- [ ] `chainlit run app/ui/chat.py` radi na clean setupu (Windows) s `.env.example`.
- [ ] Chat history + resume radi (sidebar prikazuje threadove; refresh `/thread/<id>` radi).
- [ ] Auth je konfigurabilan i nema hardcoded kredencijala.
- [ ] Bez `GOOGLE_API_KEY` app se i dalje koristi (jasan fallback).
- [ ] RAG je opcionalan i ne ruši ingest/upload flow.
- [ ] Svi podatkovni artefakti idu u `.data/` i ignorirani su.
- [ ] Release ZIP radi i ne uključuje DB/Chroma/temp/tuđe PDF-ove.
- [ ] `LICENSE-COMMERCIAL.md` + `COMMERCIAL-TERMS.md` + `THIRD_PARTY_NOTICES.md` postoje i pokrivaju distribuciju.
- [ ] Postoji minimalni support/upgrade policy (u TERMS).
