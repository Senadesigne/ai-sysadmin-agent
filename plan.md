# Glavni Plan Projekta: AI SysAdmin Agent (Operation Remote Access)

> [!URGENT]
> **Glavni Cilj**: Osigurati potpunu funkcionalnost upravljanja serverima na daljinu (iLO/IDRAC/VPN) unutar 4 dana fizičkog prisustva u studiju.
> **Status**: 🛠️ Faza Pripreme & "Punjenja Znanjem"

## 1. Status Projekta (Audit Report)
Nakon detaljnog pregleda koda, utvrdili smo točno stanje sustava:

- **Baza Podataka**: Kod (`inventory_repo.py`) je spreman, ali `inventory.db` fizički **nedostaje**.
- **RAG Sustav**: Kod (`rag/engine.py`) postoji, ali podržava samo PDF. **Treba nadogradnju** za čitanje `.md` datoteka (naše baze znanja).
- **Inventar**: Imamo `sample_inventory.csv` popunjen ključnim uređajima (Zyxel, Cisco).

## 2. Kritični Put (Deployment Pipeline)

### Faza 1: Inicijalizacija Sustava (TRENUTNO)
Prije nego krenemo na routere, moramo "upaliti" agenta.
- [ ] **DB Setup**: Kreirati `inventory.db` i učitati podatke iz CSV-a.
- [ ] **Knowledge Base Upgrade**: Omogućiti agentu da čita tekstualne upute (Markdown).

### Faza 2: Prikupljanje Znanja (Data Ingestion)
Skupljamo PDF-ove i "hranimo" agenta da postane ekspert za VAŠU opremu.
- [ ] **Zyxel VMG8623-T50B**: Upute za Bridge Mode.
- [ ] **Cisco ISR 4431**: Day 0 Config & Smart Licensing.

### Faza 3: "Virtualno" Postavljanje (Pre-Configuration)
- [ ] Generirati `config` datoteke pomoću Agenta na temelju naučenog u Fazi 2.

## 3. Struktura Dokumentacije
- **`plan.md`**: Ovaj dokument (Mapa puta).
- **`app/knowledge_base/`**: Mapa gdje ćemo spremati vaše bilješke o uređajima.
