# ARCHITECTURE.md (HR) — Starter kit B2B

## Visoka slika (modules)
- UI: Chainlit app (`app/ui/chat.py`)
- Persistence (history/resume): `app/ui/data_layer.py` + `app/ui/db.py` -> SQLite
- LLM client: `app/llm/` (provider-agnostic: API ili local endpoint)
- RAG (optional): `app/rag/engine.py` -> Chroma (persist u .data/)
- Inventory/data: `app/data/` (optional)
- Execution/tools: `app/core/execution.py` (optional / može biti add-on)

## Entrypoint
- Preporučeni: `start.bat` / `chainlit run app/ui/chat.py -w`

## Data paths (pravilo)
- Svi lokalni artefakti idu u `.data/` (DB, chroma, tmp)
- `.data/` je gitignored
