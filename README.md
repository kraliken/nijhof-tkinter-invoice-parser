# BPiON Invoice Parser v2.0

Windows asztali alkalmazás PDF számlák automatikus feldolgozásához és Excel exportjához.

---

## Mit csinál?

A felhasználó kiválaszt egy számlatípust (**Multi Alarm** vagy **Volvo Hungaria**), majd betallóz egy PDF számlát. Az alkalmazás kinyeri a strukturált adatokat (számlaszám, dátumok, rendszámok, összegek), és `.xlsx` fájlként menti el a `results/` mappába. A kész Excel, az eredeti PDF és a hozzá tartozó makrófájl egyetlen kattintással megnyitható.

---

## Képernyőkép

> _GUI screenshot ide kerülhet_

---

## Technológiai stack

| Réteg | Eszköz | Megjegyzés |
|---|---|---|
| Nyelv | Python 3.x | |
| GUI | Tkinter / ttk | Beépített Python csomag |
| PDF olvasás | pdfplumber | Szöveg- és táblázat-kinyerés |
| Adatkezelés | pandas | `List[Dict]` → DataFrame → Excel |
| Excel írás | openpyxl | pandas backend az `.xlsx` exporthoz |
| Mintaillesztés | re (stdlib) | Regex alapú adatkinyerés |
| Build | PyInstaller | Egyfájlos `.exe`, nincs konzolablak |

---

## Projekt struktúra

```
invoice-parser/
├── main.py                     # Belépési pont: sys.path + GUI indítás
├── requirements.txt
│
├── core/
│   ├── registry.py             # Támogatott számlatípusok nyilvántartása
│   ├── multialarm.py           # Multi Alarm PDF parser
│   └── volvo.py                # Volvo Hungaria PDF parser
│
├── services/
│   ├── processing_service.py   # PDF → parser → Excel pipeline
│   ├── excel_service.py        # Excel export logika
│   └── file_service.py         # Bemeneti validáció
│
├── ui/
│   ├── main_window.py          # Tkinter főablak (App osztály)
│   ├── state.py                # Állapotgép (IDLE → SUCCESS / ERROR)
│   └── theme.py                # Szín- és stílus konstansok
│
├── utils/
│   ├── paths.py                # Dev / exe útvonal-kezelés
│   └── logger.py               # Fájlba író logger
│
├── macros/
│   ├── MultiAlarm_betöltő.xlsm
│   └── Volvo_betöltő.xlsm
│
├── results/                    # Output .xlsx fájlok (automatikusan jön létre)
└── app.log                     # Futásidejű napló
```

---

## Adatfolyam

```
1. Típusválasztás      → TYPE_SELECTED állapot
2. PDF tallózás        → FILE_SELECTED állapot
3. ▶ Feldolgozás gomb → háttérszál indul (GUI nem fagy le)
4. PDF beolvasás       → parser meghívása → Excel mentés
5. Kész                → SUCCESS / ERROR állapot, eredmény megjelenik
```

---

## Kinyert mezők

| Mező | Leírás |
|---|---|
| `invoice_number` | Számlaszám |
| `invoice_date` | Számla kelte |
| `payment_due` | Fizetési határidő |
| `performance_date` | Teljesítési dátum |
| `period_start` | Elszámolási időszak kezdete |
| `period_end` | Elszámolási időszak vége |
| `license_plate` | Rendszám (normalizált, kötőjel/szóköz nélkül) |
| `net` | Nettó összeg (float, Ft) |
| `vat_percent` | ÁFA % (csak Multi Alarm) |
| `vat_amount` | ÁFA összege (Multi Alarm: PDF-ből; Volvo: számított) |

### Parsertípusok összehasonlítása

| | Multi Alarm | Volvo |
|---|---|---|
| Kinyerés módja | Teljes szöveg + regex | Táblázat-alapú (`extract_tables()`) |
| Dátum formátum | `YYYY.MM.DD` | `DD-MM-YYYY` |
| ÁFA | PDF-ből kinyerve | Számított: `net × 0.27` |
| Számlaszám helye | Regex a szövegből | 1. táblázat, 2. sor, 1. cella |

---

## Fejlesztői futtatás

```bash
# 1. Virtuális környezet létrehozása (egyszer)
python -m venv .venv

# 2. Aktiválás
source .venv/Scripts/activate        # bash
# .venv\Scripts\activate             # PowerShell

# 3. Függőségek
pip install -r requirements.txt

# 4. Indítás
python main.py
```

---

## .exe build (PyInstaller)

```bash
source .venv/Scripts/activate
pip install pyinstaller

pyinstaller --onefile --windowed --name nijhof_invoice_parser `
  --collect-submodules pdfplumber `
  --collect-submodules pandas `
  --collect-submodules openpyxl `
  main.py
```

A kész exe a `dist/` mappában jelenik meg. Az átadáshoz az exe-t és a `macros/` mappát kell együtt másolni a célgépre — Python nem szükséges.

---

## Futásidejű mappaszerkezet (exe mellett)

```
[telepítési mappa]/
├── invoice_parser.exe
├── macros/
│   ├── MultiAlarm_betöltő.xlsm
│   └── Volvo_betöltő.xlsm
└── results/               ← automatikusan jön létre az első feldolgozáskor
```

---

## Új számlatípus hozzáadása

1. Létrehozni a `core/<típus>.py` parsert — `process_<típus>(pdf_bytes: bytes) -> List[Dict]`
2. Bővíteni a `services/excel_service.py`-t az export függvénnyel
3. Felvenni a `core/registry.py` `PARSERS` dict-jébe — a GUI és a pipeline automatikusan kezeli

---

## Napló

Az alkalmazás minden indítást, állapotváltást és hibát naplóz az `app.log` fájlba.

```
2024-01-15 14:30:22,123 [INFO] Processing started: type=volvo, file=...
```
