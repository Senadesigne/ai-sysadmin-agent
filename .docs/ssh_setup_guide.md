# Vodič za Postavljanje SSH Ključeva za AI Agenta

Ovaj vodič opisuje kako generirati SSH ključeve na Windows računalu i pripremiti okolinu za "Phase 9: Live Execution".

## 1. Generiranje SSH Ključeva (Windows)

Agentu je potreban **privatni ključ** (bez passphrase-a radi automatizacije) kako bi se spajao na servere.

1.  Otvorite **PowerShell**.
2.  Unesite sljedeću naredbu:
    ```powershell
    ssh-keygen -t ed25519 -C "ai_agent@ai-studio" -f "$HOME\.ssh\ai_agent_key"
    ```
3.  **Važno:** Kada vas pita za *passphrase*, samo pritisnite **Enter** dvaput (da bude prazna lozinka).
    *   *Napomena: Ako sigurnosna politika zahtijeva passphrase, morat ćemo nadograditi Agenta da koristi `ssh-agent`, ali za sada koristimo key-only.*

Ovo će kreirati dvije datoteke u mapi `C:\Users\VašeIme\.ssh\`:
*   `ai_agent_key` (Privatni ključ - **TAJNA**)
*   `ai_agent_key.pub` (Javni ključ - **JAVNO**)

## 2. Povezivanje Ključa s Agentom

Moramo reći Agentu gdje se nalazi privatni ključ.

1.  U korijenu projekta (`ai-sysadmin-agent`), otvorite datoteku `.env`.
2.  Dodajte (ili ažurirajte) sljedeću liniju:

    ```ini
    SSH_KEY_PATH=C:/Users/Senad/.ssh/ai_agent_key
    ```
    *(Zamijenite putanju ako je drugačija, ali pazite na forward-slashes `/` ili dvostruke backslashes `\\`).*

## 3. Priprema Linux Servera (Kada budu instalirani)

Da bi se Agent mogao spojiti, njegov **Javni Ključ** mora biti na serveru.

1.  Otvorite `ai_agent_key.pub` u Notepadu i kopirajte sadržaj (počinje s `ssh-ed25519 ...`).
2.  Na Linux serveru, dodajte taj sadržaj u datoteku `~/.ssh/authorized_keys` za korisnika s kojim će se Agent spajati (npr. `senad` ili namjenski user `ai_agent`).
    ```bash
    # Na serveru:
    echo "ssh-ed25519 AAAAC3Nz..." >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
    ```

## 4. Testiranje

Kada server bude spreman:
1.  Pokrenite Agenta (`run_app.bat`).
2.  U chatu napišite: "Provjeri uptime na serveru [ImeServera]".
3.  Ako se pojavi gumb "ODOBRI", sve je spremno!
