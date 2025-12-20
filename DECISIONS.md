# DECISIONS.md (HR) — Starter kit B2B

## Core odluke
- Proizvod je paid starter kit (source-available, komercijalni uvjeti).
- Kod starter kitta i customer-facing dokumentacija (za kupca) su na ENG.
- Naš interni rad (chatovi/planiranje) je na HR.
- Starter kit je provider-agnostic:
  - radi s cloud API providerima (ključ)
  - i s lokalnim LLM endpointom (base URL).
- “Bez API ključeva” znači: app se ne ruši i radi u no-LLM modu (UI + auth + history + resume).

## Kako idemo na tržište
- Repo pripremamo kao “sell-ready” (legal minimum + eng docs + jasno što se isporučuje).
- Stvarna prodaja/go-live tek nakon što mi prvo potvrdimo da sve radi na clean installu (pilot/test).

## Kako ćemo isporučivati drugima (paket)
- SADA: definiramo popis “što ide u paket / što ne ide” i to radimo ručno.
- KASNIJE: dodajemo skriptu koja automatski napravi release ZIP.

## Što radimo SADA (prioriteti)
- Auth (dev/prod) bez hardcoded credsa
- Persistence + resume stabilno
- Optional LLM/RAG s graceful fallback
- Standardizirane putanje (.data/)
- Clean repo (bez tajni, bez domenskih PDF-ova)
- Minimal multi-dev hygiene (CONTRIBUTING + CODE_STYLE + jasni entrypoint)
- Legal minimum docs (LICENSE-COMMERCIAL, COMMERCIAL-TERMS, THIRD_PARTY_NOTICES)

## Što radimo KASNIJE
- Automatski build release ZIP paketa
- License key verification
- On-prem bundle kao ponuda (setup/hosting/maintenance)
- Deployment (docker/service), SSO/RBAC, observability
