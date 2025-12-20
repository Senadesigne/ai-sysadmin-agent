# POSITIONING.md (HR) — Starter kit B2B

## Što prodajemo
Paid starter kit (source-available) za izradu Chainlit AI agenata koji imaju:
- stabilan chat history + resume (threads sidebar radi)
- konfigurabilan auth (dev/prod)
- pluggable LLM provider (cloud API ili local endpoint)
- optional RAG (privatni dokumenti)
- jasnu strukturu modula (lak onboarding više developera)

## Kome je namijenjeno
1) B2B timovi (IT/Ops/Support) koji žele internog “copilota” brzo.
2) Agencije/konzultanti koji grade AI chat/workflow rješenja za klijente.
3) Produkt timovi koji trebaju POC → MVP bez izmišljanja infrastrukture.

## Najjače poruke (value props)
- “Skip the plumbing”: auth + persistence + resume + config riješeni.
- “Works even without keys”: app se ne ruši bez API ključeva (no-LLM mode).
- “Provider-agnostic”: može cloud ili local LLM.
- “Private-by-design” (kad se koristi lokalni LLM + lokalni RAG).

## 3 glavna use-casea (primjeri)
- Internal IT agent: Q&A + procedure + odobravanje akcija (approve pattern).
- Support agent: knowledge base + ticket triage + internal docs.
- Ops agent: inventory/status + standard upiti + integracije po potrebi.

## Što kupac dobije u praksi
- Repo koji se pokrene na Windows dev mašini uz minimalni setup
- Dokumentaciju (ENG) i primjer konfiguracije (.env.example)
- Jasne “hooks” točke gdje ubacuje vlastite alate i promptove
- Clean strukturu za timski rad (CONTRIBUTING, CODE_STYLE)
