# Starter kit B2B — Project Brief (radno: HR, release: EN)

## Proizvod
**Naziv:** Chainlit Agent Starter Kit (B2B, paid, source-available)  
**Cilj:** Omogućiti timovima da brzo isporuče “production-ready” Chainlit agente s provjerenim temeljima:
- autentifikacija (dev/prod friendly)
- pouzdana povijest chata + resume (threads/steps/users)
- optional LLM + optional RAG (aplikacija radi i bez ključeva, bez crasha)
- “action approval” UX pattern (sigurno po defaultu)

## Ciljani kupci
- interni copiloti za IT/DevOps/Support/Ops timove
- agencije koje rade chat + workflow rješenja za klijente
- product timovi koji žele POC → stabilan MVP bez ponovnog izmišljanja osnova

## Glavna vrijednost
Čist, template-ready kostur koji radi “out-of-the-box”, plus jasne točke proširenja za:
- alate/integracije
- promptove i sistemske politike
- ingestion znanja (RAG)
- opcionalni on-prem deployment

## V1 Scope (mora imati)
- persistence + resume stabilan (sidebar threads, refresh `/thread/<id>`)
- nema hardcoded kredencijala; auth konfigurabilan (dev/prod)
- optional LLM/RAG s graceful fallbackom (bez API ključa app se i dalje koristi)
- standardizirane putanje podataka pod jedan direktorij (npr. `.data/`)
- **kod + customer-facing dokumentacija/poruke na engleskom** (release-ready)
- **radni dio projekta na hrvatskom** (naš internal workflow)
- multi-dev spremnost: contributing + code style osnove
- “paid v1 legal minimum” dokumenti:
  - `LICENSE-COMMERCIAL.md`
  - `COMMERCIAL-TERMS.md` (jasno “no reselling as a template”)
  - `THIRD_PARTY_NOTICES.md`

## Non-goals (V1)
- license key verifikacija u runtimeu
- one-click cloud deployment
- enterprise SSO/RBAC/audit (v2/pro)
- advanced security hardening iznad postojećeg approve patterna (v2/pro add-on)

## Kratki opis arhitekture
- UI: Chainlit app (`app/ui/chat.py`)
- Persistence: SQLite data layer (`app/ui/data_layer.py` + `app/ui/db.py`)
- LLM: pluggable provider (cloud ili lokalni endpoint)
- RAG: opcionalni modul (Chroma ili alternativa)
- Opcionalni moduli: inventory, execution tools

## Ideja za sinergiju s tvojim AI hosting studijem (Phase 2)
Ponuda “Private Agent Kit” (on-prem):
- starter kit + lokalni LLM endpoint + privatni RAG
- podaci ostaju u mreži kupca
- target: firme s compliance/privatnost zahtjevima

## Pravila rada
- **Interno komuniciramo na hrvatskom**
- **Sve što ide kupcu / u release (docs + UI poruke + komentari u kodu) ide na engleskom**
- jedan commit po planiranom koraku (malo i pregledno)
- template mora biti čist: bez tajni, bez customer podataka, bez velikih DB/binarnih artefakata
