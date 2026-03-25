# Nijhof számlafeldolgozó — Felhasználói útmutató

Windows asztali alkalmazás PDF számlák automatikus feldolgozásához és Excel exportjához.

---

## Mit csinál?

Beolvas egy PDF számlát (Multi Alarm Zrt. vagy Volvo Hungaria Kft.), kinyeri a strukturált adatokat (számlaszám, dátumok, rendszámok, összegek), és `.xlsx` fájlként elmenti a `results/` mappába.

---

## Használat lépései

Az alkalmazás végigvezet a folyamaton — a **Feldolgozás lépései** szekció mindig az aktuális teendőt emeli ki.

**1. Számlatípus kiválasztása**
Kattints a megfelelő kártyára: **Multi Alarm** vagy **Volvo**.

**2. PDF fájl kiválasztása**
Kattints a **Tallózás...** gombra, és válaszd ki a feldolgozandó PDF számlát.
> A × gombbal törölheted a kiválasztást és másikat tallózhatsz be.

**3. Feldolgozás indítása**
Kattints a **▶ Számlafeldolgozása** gombra. Feldolgozás közben egy folyamatjelző sáv látható.

**4. Eredmény**
Sikeres feldolgozás után az **Eredmény** szekció jelenik meg az elkészült fájl nevével és elérési útjával.

---

## Eredmény szekció gombok

| Gomb | Megnyit |
|---|---|
| **Kinyert adatok megnyitása** | Az elkészült `.xlsx` fájlt (pl. Excelben) |
| **Betöltő megnyitása** | A számlatípushoz tartozó Excel makrót (`macros/` mappából) |
| **Számla megnyitása** | Az eredeti PDF-et |

---

## Kimeneti fájl

A generált Excel a `results/` mappába kerül, neve:

```
{típus}_invoice_{számlaszám}_{YYYYMMDD_HHMMSS}.xlsx
```

Példa: `volvo_invoice_INV-2024-001_20240115_143022.xlsx`

---

## Kinyert adatok

Mindkét számlatípusnál az alábbi mezők kerülnek az Excel fájlba:

| Mező | Leírás |
|---|---|
| Számlaszám | Az eredeti számla azonosítója |
| Számla kelte | Kiállítás dátuma |
| Fizetési határidő | Befizetendő határidő |
| Teljesítési dátum | Szolgáltatás teljesítésének dátuma |
| Elszámolási időszak | Kezdő és záró dátum |
| Rendszám | Normalizált formátumban (kötőjel/szóköz nélkül) |
| Nettó összeg | Ft-ban |
| ÁFA % és összeg | Multi Alarm: PDF-ből; Volvo: számított (27%) |

---

## Hibakezelés

Ha a feldolgozás sikertelen, piros **⊗ Feldolgozási hiba** doboz jelenik meg a hibaüzenettel. Javítás után a **▶ Számlafeldolgozása** gombbal újra lehet próbálni.

Gyakori okok:
- Nem a megfelelő számlatípust választottad ki
- A PDF sérült vagy jelszóval védett
- A fájl nem az adott szállítótól származó számla

---

## Menü

- **Új feldolgozás** — visszaáll a kezdőállapotba (típus, fájl, eredmény törlése)
- **Kilépés** — bezárja az alkalmazást

