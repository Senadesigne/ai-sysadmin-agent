# Plan Implementacije - AI SysAdmin Agent

## Opis Cilja
Razvoj lokalnog AI SysAdmin Agenta ("AI Studio") koji djeluje kao inteligentni konzultant za upravljanje specifičnom hardverskom infrastrukturom (HPE/Dell/IBM serveri, Cisco/Huawei mrežna oprema, Storage sustavi). Agent će ingestirati podatke o inventaru, čitati tehničke priručnike putem RAG-a, validirati kompatibilnost i generirati savjetodavne CLI naredbe.

## Potrebna Recenzija Korisnika (Arhitektonske Odluke)
> [!IMPORTANT]
> **Odluke i Odgovori na Pitanja**
>
> 1.  **SQLite vs PostgreSQL**:
>     *   **Odluka**: Počinjemo sa **SQLite**.
>     *   **Obrazloženje**: Za lokalnu "single-tenant" aplikaciju, SQLite je znatno jednostavniji za distribuciju i upravljanje (jedna datoteka). Koristit ćemo **Repository Pattern** u kodu za apstrakciju pristupa bazi. To osigurava da se, ako kompleksni upiti ili količina podataka (milijuni stavki) postanu usko grlo, možemo prebaciti na PostgreSQL bez prepisivanja poslovne logike.
>
> 2.  **Parsiranje PDF Tablica (RAG)**:
>     *   **Odluka**: **LlamaParse** (kao primarna preporuka) + **Unstructured** (lokalni fallback).
>     *   **Obrazloženje**: Tehnički priručnici (IBM/Cisco) su notorno teški zbog izgleda s više stupaca i tablica koje se protežu kroz stranice. Standardni PyPDF/LangChain loaderi ovdje ne rade dobro. LlamaParse je trenutno najbolje rješenje (SOTA) za ovo.
>     *   **Implementacija**: Dizajnirat ćemo cjevovod (pipeline) za ingestiju da bude modularan.
>
> 3.  **Sigurnosni Modul (Validacija CLI Naredbi)**:
>     *   **Odluka**: **Generiranje temeljeno na predlošcima (Template-based Generation) + Sintaktički Validator**.
>     *   **Prijedlog**: Oslanjanje isključivo na LLM za "generiranje" sintakse je rizično.
>         *   *Sloj 1 (Namjera)*: LLM prepoznaje namjeru (npr. "Konfiguriraj VLAN 10 na sučelju Gi0/1").
>         *   *Sloj 2 (Predlošci)*: Sustav koristi Jinja2 predloške za standardne zadatke (osigurava ispravnu strukturu sintakse).
>         *   *Sloj 3 (Revizija)*: "Critic" LLM prolaz za provjeru opasnih naredbi (rm, delete, format) prema bijeloj listi (whitelist).
>         *   *Sloj 4 (Uzorak)*: Regex validacija za generirane vrijednosti.

## Predložene Promjene

### Struktura Projekta (Skeleton)
Projekt će slijediti modularni pristup "Clean Architecture".

#### [NOVO] Struktura Mapa
`ai-sysadmin-agent/`
*   `.docs/` - Dokumentacija i planovi
*   `app/`
    *   `core/` - Domenske entiteti i poslovna pravila (Logika Inventara, Engine Kompatibilnosti).
    *   `data/` - Modeli baze podataka (SQLAlchemy), repozitoriji i adapteri za vektorsku bazu.
    *   `security/` - Logika validacije, sanitizatori naredbi i engine za predloške.
    *   `rag/` - Cjevovodi za ingestiju dokumenata, PDF parseri i logika dohvaćanja (retrieval).
    *   `ui/` - Chainlit aplikacija i UI helperi.
    *   `llm/` - Integracija LangChain/Gemini i upravljanje promptovima.
*   `config/` - Konfiguracijske postavke.
*   `tests/` - Unit i integracijski testovi.

### Implementacija Tehnološkog Stacka
*   **Inventar**: SQLAlchemy sa SQLite (`inventory.db`).
*   **RAG**: ChromaDB (perzistentni lokalni) + LangChain.
*   **Parseri**: Sučelja za LlamaParse.
*   **UI**: Chainlit (`app.py` ulazna točka).

## Plan Verifikacije
*   **Provjera Strukture**: Potvrditi da su sve mape i `__init__.py` datoteke kreirane.
*   **Zavisnosti**: Potvrditi da `requirements.txt` sadrži sve dogovorene pakete (langchain, chainlit, sqlalchemy, chromadb, google-generativeai).
*   **Dokumentacija**: Osigurati da postoji `.docs/plan.md`.
