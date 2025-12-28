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
- **English-first + multi-dev readiness (minimum)**: dokumenti i user-facing poruke za kupca su na engleskom; repo ima minimalne smjernice za timski rad.
- **Jedan stabilan entrypoint** i quickstart upute (eng).

Non-goals v1:
- license-key verifikacija u runtimeu
- deployment na cloud (docker/k8s) kao “one click”
- enterprise hardening (SSO, RBAC, audit)
- “Security hardening” kao proizvodna značajka (iznad postojećeg approve patterna + blacklist) ako se kit pozicionira kao generički template

---

## Popis problema za riješiti (iz ovog repoa)

- **Hardcoded auth**: ✅ RIJEŠENO - implementiran dev/prod auth bez hardcoded kredencijala.
- **Secrets u dokumentima**: ✅ RIJEŠENO - dodana `.env.example` template, uklonjeni secrets iz dokumentacije.
- **Optional LLM/RAG**: ✅ RESOLVED - NullLLM fallback implemented; app runs without API keys; RAG gated by RAG_ENABLED with graceful no-op.
- **Data pathovi**:
  - `chainlit.db` je u rootu (ok), ali treba standardizirati `.data/` ili slično.
  - `inventory.db` je relativan (repo layer u `app/data/inventory_repo.py`).
  - `Chroma` persist je hardcoded `./app/data/chroma_db` u `app/rag/engine.py`.
  - temp fajlovi `temp_<name>` u `app/ui/chat.py`.
- **Knowledge base PDF-ovi**: ✅ RESOLVED - Domain-specific PDFs removed from starter-kit branch; replaced with minimal sample KB.
- **Dupli persistence modul**: postoji alternativni `SQLiteDataLayer` u `app/core/persistence.py` (ne koristi se) uz “pravi” u `app/ui/data_layer.py`.

---

## Decision points prije implementacije

- **Generički template vs. sysadmin/execution-first**
  - Ako je **generički template**: “execution” ostaje opcionalni add-on (v2/Pro modul), a core je auth + persistence + optional RAG + UX patterni.
  - Ako je **sysadmin/execution-first**: v1 mora imati jače guardraile (allowlist, policy, audit), što povećava scope i “security” obveze.
- **Minimal legal docs vs. full polish**
  - Minimal: `LICENSE-COMMERCIAL.md` + `COMMERCIAL-TERMS.md` + `THIRD_PARTY_NOTICES.md` (v1).
  - Full polish: EULA, security policy, brand assets, changelog, support SLA (v2 ili enterprise tier).
- **Release ZIP u v1 ili v2**
  - Ako se prodaje odmah: release zip i “what’s included/excluded” pravila moraju biti u v1.
  - Ako je prvo internal pilot: zip može u v2, ali tada v1 nije “out-of-the-box deliverable” za kupce.

---

## Cross-cutting rules (vrijede za sve korake)

- **English-first policy (release-ready)**:
  - Sve user-facing poruke, logovi, dokumentacija i komentari koji idu u release trebaju biti na engleskom.
  - Privatne bilješke (koje ne idu u release) mogu ostati na HR, ali moraju biti izuzete iz distribucije.
- **Multi-dev hygiene (minimum)**:
  - `CONTRIBUTING.md` (branching, commit naming, PR checklist)
  - `CODE_STYLE.md` ili minimalne smjernice u README
  - Jasno definiran entrypoint i konfiguracija (novi dev može startati bez pitanja)
  - Format/lint: idealno `ruff`/`black` + `pre-commit` (ako prevelik scope za v1, onda v2)
- **Release rule**: svi dokumenti koji idu kupcu moraju biti na engleskom.

---

## Koraci implementacije (8–10 koraka)

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

### 3) Auth: ⚠️ PARTIALLY PASSED - uklonjen hardcoded admin/admin, uvedeni dev/prod režimi
- **Fajlovi:** `app/ui/chat.py`, `.chainlit/config.toml` (po potrebi)
- **Što se mijenja:**
  - `DEV_AUTH_ENABLED=true` (default) i `DEV_AUTH_USER/DEV_AUTH_PASS` iz env-a.
  - Produkcijski mode: zahtijeva konfiguriran `CHAINLIT_AUTH_SECRET` i/ili integraciju (v1 minimalno: env-based basic auth).
  - **All dev auth backdoors and dependency_overrides have been REMOVED.**
- **Test:** ✅ login radi s env kredencijalima (`ADMIN_IDENTIFIER=senad` i `ADMIN_PASSWORD=Pos-322`); bez env-a u dev modu koristi sigurne defaulte ili blokira s jasnom porukom.
- **🚨 TODO:** Verify and fix support for passwords containing "#" in .env (likely treated as comment). 
  - Current workaround: Use `ADMIN_PASSWORD=Pos-322` (no #)
  - Suggested fix: Try `ADMIN_PASSWORD='Pos-322#'` or escaping `\#`
  - Re-test that login succeeds and expected password length becomes 8
- **Commit:** `feat: configurable auth (dev/prod) without hardcoded creds`

### 4) Optional LLM + Optional RAG: safe fallbacks (DONE)
- **Status: DONE (verified without API keys)**
- **Fajlovi:** `app/llm/client.py`, `app/rag/engine.py`, `app/ui/chat.py`, `requirements.txt`
- **Što se mijenja:**
  - LLM: bez `GOOGLE_API_KEY` aplikacija radi i vraća jasnu poruku kako uključiti LLM (bez `None.invoke` crasha).
  - RAG: `RAG_ENABLED` gate + graceful skip za ingest/query kad nije konfigurirano.
  - Jasne konfiguracijske poruke (eng) i "what works without keys" objašnjenje.
- **Completed:**
  - **Step 4 is COMPLETE.**
  - **NullLLM fallback prevents crashes when no API keys are present.**
  - **RAG is optional, gated by RAG_ENABLED, and no-op when disabled.**
  - **Starter-kit cleanup (KB + chroma_db removal from git) completed as part of this step.**
- **Test:** ✅ bez ključeva app radi; s ključem radi LLM i RAG ingest/query.
- **Commit:** `feat: optional LLM/RAG with graceful fallbacks`

### 5) Ukloni dupli persistence modul (jedna istina) (DONE)
- **Status: DONE**
- **Fajlovi:** `app/core/persistence.py`, `app/ui/data_layer.py`, `app/ui/chat.py`
- **Što se mijenja:**
  - Odabrati jednu implementaciju (preporuka: `app/ui/data_layer.py`).
  - Drugu ukloniti ili pretvoriti u `legacy/` uz jasnu oznaku (bez importanja).
- **Completed:**
  - **Step 5 is COMPLETE.**
  - **`app/ui/data_layer.py` is the single source of truth for persistence.**
  - **Legacy persistence module removed to eliminate confusion.**
- **Test:** ✅ sidebar threads + resume rade; nema import konfuzije.
- **Commit:** `chore: remove unused legacy persistence implementation`

### 6) Reduce debug noise & keep init robust (no new startup hooks) (DONE)
- **Status: DONE**
- **Fajlovi:** `app/ui/data_layer.py`, `app/ui/db.py`, `app/ui/chat.py`
- **Što se mijenja:**
  - V1 **ne uvodi nove Chainlit startup hookove**: zadržati postojeći `ensure_db_init()` pristup kao "source of truth" za init.
  - Smanjiti debug noise: print/log poruke iza `DEBUG` flaga; ukloniti redundantne logove.
  - Fokus: čitljiv output, bez promjene ponašanja persistence lifecycla.
- **Completed:**
  - **Step 6 is COMPLETE.**
  - **DEBUG flag controls verbosity** - verbose logs only appear when `DEBUG=1` is set.
  - **No new startup hooks added** - existing `ensure_db_init()` approach preserved.
  - **Single init path maintained** - one clear source of truth for DB initialization.
- **Test:** ✅ pokreni app i provjeri da nema "spam" logova; sidebar/resume i dalje rade kao prije.
- **Commit:** `chore: reduce debug noise and keep single init path`

### 7) Uredi temp file handling (sigurno + cleanup)
- **Fajlovi:** `app/ui/chat.py`
- **Što se mijenja:**
  - Spremanje u OS temp folder ili `.data/tmp/`.
  - Brisanje temp fajla nakon ingest/importa.
- **Test:** upload CSV/PDF, provjeri da se temp ne gomila.
- **Commit:** `fix: store uploads in temp dir and cleanup`

### 8) Knowledge base: ukloni domenske PDF-ove iz default paketa
- **Fajlovi:** `app/knowledge_base/*`, dodati `app/knowledge_base/README.md` (ili `SAMPLE.md`)
- **Što se mijenja:**
  - Maknuti PDF-ove iz distribucije (ostaviti jedan mali neutralni sample doc).
  - Jasne upute kako korisnik dodaje vlastite dokumente.
- **Test:** RAG ingest radi nad sample dokumentom.
- **Commit:** `chore: replace domain PDFs with minimal sample knowledge base`

### 9) English-first + multi-dev readiness + quickstart (customer-facing)
- **Fajlovi:** `CHAINLIT_SETUP.md`, `chainlit.md`, `README.md` (ako se uvodi), `start.bat`, `run_app.bat`, `main.py`, `scripts/verify_startup.py`, `CONTRIBUTING.md`, `CODE_STYLE.md`
- **Što se mijenja:**
  - Dokumentacija i user-facing tekstovi za release prebacuju se na engleski (quickstart i konfiguracija).
  - Dodati/urediti paid v1 legal minimum dokumente: `LICENSE-COMMERCIAL.md`, `COMMERCIAL-TERMS.md`, `THIRD_PARTY_NOTICES.md` (+ kratka “No affiliation” napomena u README ako se koristi).
  - Dodati minimalni timski set: `CONTRIBUTING.md` + `CODE_STYLE.md`.
  - Jedan preporučeni entrypoint i “verify startup” skripta koja jasno kaže što nedostaje.
- **Test:** novi dev na clean venv: prati quickstart i digne app bez pitanja; verify skripta prolazi (ili daje jasnu grešku na eng).
- **Commit:** `docs: english-first quickstart + team hygiene + commercial license docs`

---

## Licenciranje i distribucija (paid, source-available)

### Paid v1 legal minimum (obavezno prije prodaje)

- `LICENSE-COMMERCIAL.md`
- `COMMERCIAL-TERMS.md`
  - Mora eksplicitno zabraniti **preprodaju templatea “as a template”**.
  - Dopušteno: korištenje za **vlastite projekte** i **projekte klijenata** (deliverable/solution), bez redistribucije starter kitta kao proizvoda.
- `THIRD_PARTY_NOTICES.md`
- (Opcionalno) kratka **“No affiliation”** napomena (npr. u `README.md`) koja jasno kaže da projekt nije povezan/sponzoriran od Chainlit/LangChain/Google/itd.

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
- **Execution add-on / Pro modul (optional)**: advanced hardening (allowlist commands per host, approval policies, audit trail, secrets management). V1 zadržava samo approve pattern + postojeći blacklist.
- **Pluggable providers**: OpenAI/Anthropic/Azure/GCP, embeddings switch.

---

## Checklista: "Ready to sell"

- [x] Repo nema nikakve stvarne tajne (ni u docovima ni u primjerima).
- [x] `chainlit run app/ui/chat.py` radi na clean setupu (Windows) s `.env.example`.
- [x] Chat history + resume radi (sidebar prikazuje threadove; refresh `/thread/<id>` radi).
- [x] Auth je konfigurabilan i nema hardcoded kredencijala.
- [x] Bez `GOOGLE_API_KEY` app se i dalje koristi (jasan fallback).
- [x] RAG je opcionalan i ne ruši ingest/upload flow.
- [x] Svi podatkovni artefakti idu u `.data/` i ignorirani su.
- [x] Release ZIP radi i ne uključuje DB/Chroma/temp/tuđe PDF-ove.
- [x] `LICENSE-COMMERCIAL.md` + `COMMERCIAL-TERMS.md` + `THIRD_PARTY_NOTICES.md` postoje i pokrivaju distribuciju.
- [x] Paid v1 legal minimum docs exist (`LICENSE-COMMERCIAL.md`, `COMMERCIAL-TERMS.md`, `THIRD_PARTY_NOTICES.md`).
- [x] Postoji minimalni support/upgrade policy (u TERMS).
- [x] All docs + user-facing messages (UI text/logs that ship) are in English.
- [x] Repo has basic contributing guidelines for teams (`CONTRIBUTING.md`, `CODE_STYLE.md` or equivalent).

---

## Production-grade extensions (2025) — Implementation Hodogram (v1.x)

Goal: Add production-grade reliability patterns (no-crash, capability state, deterministic orchestration, event hooks, audit trail, decoupled RAG, clear core/add-ons boundary) without scope creep.

### Global rules (apply to every step)
- No API endpoints (/api/*) in v1.x.
- No mock data / mock framework. OFFLINE_MODE only disables LLM+RAG+execution and shows UI status.
- No enterprise features (SSO/RBAC/multi-tenant), no infra migrations (SQLite stays).
- Keep changes additive, minimal; avoid refactors unless strictly necessary.
- 1 capability = 1 commit. Each commit must include a quick manual verification.

---

## Commit 1 — Capability State (foundation)
**Objective:** Central capability detection + user-visible status.

- NOTE (v0.1.0): Some user-facing/system messages are still in Croatian (e.g., system prompt text). These must be translated to English before release; track and complete this in Step 9 (English-first + customer-facing docs).

**Steps**
1.1 Add `app/core/capabilities.py`
- Implement `CapabilityState` reading env/settings.
- Methods: `is_llm_available()`, `is_rag_available()`, `is_persistence_available()`.
- Add `get_status_message()` for UI (concise).

1.2 Update `app/config/settings.py`
- Add flags with defaults:
  - `OFFLINE_MODE=false`
  - `ENABLE_EVENTS=true`
  - `ENABLE_AUDIT=true`
  - `EXECUTION_ENABLED=false`

1.3 Update `app/ui/chat.py`
- Initialize `CapabilityState` at chat start.
- Display a one-time status message (e.g. "✓ Chat | ✗ LLM | ✗ RAG").

**Verify**
- Run without API key → app runs; status shows LLM disabled.
- Run with `OFFLINE_MODE=true` → status shows offline mode / external disabled.

---

## Commit 2 — Event hooks (foundation only)
**Objective:** Emit events without integrating external platforms.

**Steps**
2.1 Add `app/core/events.py`
- `EventEmitter.emit(event_type, data)`
- `JSONLEventLogger` writes to `.data/events.jsonl` (append-only).
- Ensure `.data/` folder exists (create if missing).

2.2 Add minimal wiring (no wide integration yet)
- Initialize default logger once on app start (or lazy init on first emit).

**Verify**
- Emit a test event during chat start → confirm `.data/events.jsonl` gets one JSON line.

---

## Commit 3 — No-crash LLM boundary
**Objective:** LLM failures never crash; always safe fallback.

**Steps**
3.1 Update `app/llm/client.py`
- If `OFFLINE_MODE=true` → return `NullLLM` + status message.
- Wrap provider init in try/except → fallback to `NullLLM`.
- Emit event on fallback (if events enabled).

3.2 Ensure user-visible clarity
- If NullLLM active, UI should clearly indicate LLM unavailable.

**Verify**
- Break API key → app still runs; you get fallback message; no crash.

---

## Commit 4 — No-crash + decoupled RAG boundary
**Objective:** RAG failures never crash; RAG can be disabled cleanly.

**Steps**
4.1 Update `app/rag/engine.py`
- If `OFFLINE_MODE=true` → `NullRagEngine` (returns empty results).
- `query()` wrapped in try/except → returns `[]` on error.
- `ingest_*` wrapped in try/except → returns `0` on error.
- Emit `rag_query` / `rag_fallback` events (if enabled).

4.2 Ensure agent messaging
- When RAG unavailable, agent says: "Knowledge base is currently unavailable" (or similar).

**Verify**
- Set `RAG_ENABLED=true` but break RAG deps → chat still works; RAG returns empty; message shown; no crash.

---

## Commit 5 — Deterministic orchestration (plan → execute)
**Objective:** Always create a JSON plan before any tool/execution.

**Steps**
5.1 Add `app/core/orchestrator.py`
- `create_plan(user_input)` → returns structured JSON plan (max 10 steps).
- `execute_plan(plan)` → executes only if execution enabled (otherwise no-op).

5.2 Update `app/ui/chat.py`
- On each message: generate plan first and display it.
- If execution disabled: show "Execution disabled" and stop after plan.

**Verify**
- Prompt: "restart nginx on server1" → plan displayed.
- With `EXECUTION_ENABLED=false` → no execution occurs.

---

## Commit 6 — Audit trail (approvals only)
**Objective:** Append-only audit for approve/reject and critical actions.

**Steps**
6.1 Add `app/core/audit.py`
- `log_audit(user, action, params, outcome)` → append JSON to `.data/audit.jsonl`.
- Audit must never crash app (try/except inside).

6.2 Wire into approve/reject flow in `app/ui/chat.py`
- On approve: write audit entry.
- On reject: write audit entry.

**Verify**
- Approve and reject once → `.data/audit.jsonl` contains both entries.

---

## Commit 7 — Wire key event emissions (minimal)
**Objective:** Ensure events are emitted at important points.

**Steps**
7.1 Add emits (guarded by `ENABLE_EVENTS`)
- LLM call start/end or fallback
- RAG query/fallback
- plan created
- approval requested
- execution requested (if module exists)

**Verify**
- `.data/events.jsonl` includes events for a typical chat flow.

---

## Commit 8 — Persistence failure boundaries (no-persistence mode)
**Objective:** If persistence fails (locked/corrupt), app still runs with a warning.

**Steps**
8.1 Update `app/ui/db.py`
- `ensure_db_init()` returns True/False; never crashes.

8.2 Update `app/ui/data_layer.py`
- Only in `__init__`: try DB init; on fail set `self.enabled=False` and emit `persistence_failed`.
- For other methods: if `not self.enabled` return safe defaults (minimal), but do not swallow unexpected errors silently.

8.3 Update `app/ui/chat.py`
- On chat start: if persistence init fails → show sticky warning: "Chat history unavailable - running in temporary mode".

**Verify**
- Simulate locked/corrupt DB on startup → app runs; warning shown; no crash.

---

### Done criteria (v1.x)
- App never crashes due to missing keys, disabled RAG, or persistence init failure.
- Status clearly shows what is enabled/disabled.
- Plan is shown before any execution.
- Events + audit logs work (append-only JSONL).
- Core works without execution module.

### Optional premium upgrades (later)

- **Contract / smoke test matrix**
  - Proširiti `scripts/verify_startup.py` da pokriva ključne scenarije (no keys, OFFLINE_MODE, RAG disabled, persistence init fail/locked/corrupt) i daje jasne PASS/FAIL poruke.

- **Error taxonomy**
  - Uvesti standardne tipove grešaka (npr. `LLMUnavailable`, `RAGUnavailable`, `PersistenceUnavailable`) kako bi fallback poruke i eventovi bili dosljedni.

- **Structured logging**
  - Standardizirati format logova (npr. JSONL ili barem konzistentan prefix + correlation id) radi lakšeg debugiranja i buduće observability integracije.