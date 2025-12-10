# Zahtjev za korištenje vlastite terminalne opreme i Bridge Mode

**Datum:** 09.12.2025.
**Primatelj:** Telemach Hrvatska
**Status:** Nacrt (Draft)
**Vezani Uređaji:** Zyxel VMG8623-T50B, Cisco ISR 4431

---

**Naslov:** Zahtjev za korištenje vlastite terminalne opreme i Bridge Mode - [Vaše Ime i Prezime]

**Tekst:**

Poštovani,

Kao vaš korisnik na adresi ****, ovim putem podnosim službeni zahtjev za prilagodbu CPE opreme (Zyxel VMG8623-T50B) radi korištenja vlastite terminalne opreme, sukladno članku 139. stavku 2. Zakona o elektroničkim komunikacijama te HAKOM-ovim pravilnicima o mrežnoj neutralnosti.

U svrhu postavljanja poslovne serverske infrastrukture, planiram koristiti vlastiti usmjerivač (Cisco ISR 4431) koji će obavljati usmjeravanje i mrežnu sigurnost. Kako bih to omogućio, potrebne su mi sljedeće prilagodbe i informacije s vaše strane:

1.  **Prebacivanje u Bridge Mode (Mosni rad):** Molim vas da na isporučenom uređaju Zyxel VMG8623-T50B daljinski deaktivirate "Routing" funkcije (NAT, DHCP, Firewall, Wi-Fi) i konfigurirate uređaj u transparentni Bridge Mode na WAN sučelju za internetski promet.

2.  **Dostava PPPoE Autentifikacijskih Podataka:** Budući da će moj Cisco usmjerivač inicirati PPPoE sesiju, molim vas da mi dostavite (ili potvrdite ako su već poslani):
    *   PPPoE Korisničko ime (Username):
    *   PPPoE Lozinku (Password):

3.  **Potvrda Mrežnih Parametara:** Molim potvrdu točnih parametara za konfiguraciju mog WAN sučelja kako bi se usluga uspješno uspostavila:
    *   VLAN ID za Internet promet: (Je li to VLAN 3980, 100, 1203 ili neki drugi specifičan za moju lokaciju/optičku nit?)
    *   MTU Veličina: (Pretpostavljam 1492 bajta za PPPoE, molim potvrdu).

Napominjem da mi nije potrebna podrška za konfiguraciju moje vlastite opreme (Cisco), već isključivo priprema vaše linije da tu opremu prihvati ("VLAN transparent bridge").

Molim vas povratnu informaciju o terminu kada će promjena biti izvršena ili kada mogu očekivati dostavu traženih podataka.

Unaprijed hvala na stručnoj suradnji.

Srdačan pozdrav,
