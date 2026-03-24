# Invoice Parser — Fejlesztői dokumentáció

**BPiON Invoice Parser v2.0** — Windows asztali alkalmazás PDF számlák feldolgozásához és Excel exportjához.

---

## Mit csinál?

A felhasználó kiválaszt egy számlatípust (Multi Alarm vagy Volvo), majd betallóz egy PDF számlát. Az alkalmazás kinyeri a számla strukturált adatait (számlaszám, dátumok, rendszámok, összegek) és `.xlsx` fájlként elmenti a `results/` mappába. Sikeres feldolgozás után a keletkezett Excel fájl, az eredeti PDF és a hozzá tartozó Excel makró betöltő egyetlen kattintással megnyitható.

---

## Technológiai stack

| Réteg | Eszköz | Megjegyzés |
|---|---|---|
| Nyelv | Python 3.x | |
| GUI | Tkinter / ttk | Beépített Python csomag, nincs külső függőség |
| PDF olvasás | **pdfplumber** | Szöveg- és táblázat-kinyerés PDF-ből |
| Adatkezelés | **pandas** | `List[Dict]` → DataFrame → Excel |
| Excel írás | **openpyxl** | pandas backend-je az `.xlsx` exporthoz |
| Mintaillesztés | re (stdlib) | Regex alapú adatkinyerés a PDF szövegből |
| Build | **PyInstaller** | Egyfájlos `.exe` csomagolás, nincs konzolablak |

### `requirements.txt`
```
pdfplumber
pandas
openpyxl
```

---

## Projekt struktúra

```
src/
├── main.py                     # Belépési pont: sys.path + GUI indítás
├── requirements.txt            # Python függőségek
│
├── core/
│   ├── registry.py             # Támogatott számlatípusok nyilvántartása
│   ├── multialarm.py           # Multi Alarm PDF parser
│   └── volvo.py                # Volvo Hungaria PDF parser
│
├── services/
│   ├── processing_service.py   # A teljes feldolgozást vezérli: PDF beolvasás → parser → Excel mentés
│   ├── excel_service.py        # Excel export logika
│   └── file_service.py         # Bemeneti validáció
│
├── ui/
│   ├── main_window.py          # Tkinter főablak (App osztály)
│   ├── state.py                # Az alkalmazás lehetséges állapotai (pl. IDLE, PROCESSING, SUCCESS)
│   └── theme.py                # Szín- és stílus konstansok
│
├── utils/
│   ├── paths.py                # Dev / PyInstaller útvonal-kezelés
│   └── logger.py               # Fájlba író logger
│
├── macros/
│   ├── MultiAlarm_betöltő.xlsm # Excel makró (Multi Alarm betöltő)
│   └── Volvo_betöltő.xlsm      # Excel makró (Volvo betöltő)
│
├── results/                    # Output .xlsx fájlok (első feldolgozáskor jön létre)
└── app.log                     # Futásidejű napló (első indításkor jön létre)
```

> **Automatikusan generált, nem forráskód:**
> `build/` és `dist/` — PyInstaller hozza létre build során;
> `.venv/` — fejlesztői Python környezet, `python -m venv .venv` paranccsal jön létre.

---

## Modulok feladata

### `core/registry.py`
Az egyetlen hely, ahol az összes támogatott számlatípus regisztrálva van (`PARSERS` dict). Ha új számlafajtát kell hozzáadni, csak ide kell felvenni egy bejegyzést — a GUI és a feldolgozó logika automatikusan felismeri. Minden bejegyzés tartalmaz megjelenített nevet, parser függvényt, export függvényt és makró fájlnevet.

### `core/multialarm.py` és `core/volvo.py`
Tisztán funkcionális PDF parserek — nem írnak fájlt, nem nyitnak ablakot.

- **Bemenetük:** PDF fájl raw bájtjai (`bytes`)
- **Kimenetük:** `List[Dict]` — soronként egy jármű/időszak adatsor, például:

```python
[
  {
    "invoice_number": "12345",
    "invoice_date": "2024.01.15",
    "payment_due": "2024.02.15",
    "performance_date": "2024.01.15",
    "period_start": "2024.01.01",
    "period_end": "2024.01.31",
    "license_plate": "ABC123",
    "net": 45000.0,
    "vat_percent": 27,       # csak Multi Alarm
    "vat_amount": 12150.0    # csak Multi Alarm
  },
  { ... },  # következő jármű
  { ... }
]
```

| | Multi Alarm | Volvo |
|---|---|---|
| Kinyerés módja | Teljes szöveg + regex | Táblázat-alapú (`extract_tables()`) |
| Dátum formátum | `YYYY.MM.DD` | `DD-MM-YYYY` |
| ÁFA | PDF-ből kinyerve | Számított: `net * 0.27` |
| Számlaszám helye | Regex a szövegből | 1. táblázat, 2. sor, 1. cella |

### `services/processing_service.py`
A teljes pipeline egy függvénybe szervezve (`run()`): beolvassa a PDF-et, meghívja a parsert, generálja a kimeneti fájlnevet, létrehozza a `results/` mappát, majd elvégzi az Excel exportot. Háttérszálból hívódik, hogy a GUI ne fagyjon le.

### `services/excel_service.py`
`List[Dict]` → pandas DataFrame → `.xlsx` konverzió. Kezeli a dátumformátum-különbségeket és a Volvo ÁFA-számítást.

### `services/file_service.py`
Validálja a feldolgozás előfeltételeit: van-e kiválasztva számlatípus, van-e fájl, létezik-e, PDF-e. GUI-tól független, könnyen tesztelhető.

### `ui/main_window.py`
Az egész GUI egy `App` osztályban. Scrollozható canvas-on belül 6 szekció (fejléc, súgó, típusválasztó, fájlválasztó, feldolgozás, eredmény). A PDF feldolgozás a háttérben fut, hogy az ablak ne fagyjon le közben. Amikor kész, az eredményt visszaküldi a főablaknak, amely frissíti a felületet.

### `ui/state.py`
Nyilvántartja, hogy a felhasználó hol tart a folyamatban: `IDLE` → `TYPE_SELECTED` → `FILE_SELECTED` → `PROCESSING` → `SUCCESS` / `ERROR`. Az aktuális lépés alapján frissülnek a gombok, a súgó kiemelései és az eredményszekció láthatósága.

### `utils/paths.py`
Fejlesztői futtatáskor (`python main.py`) és exe-ként futtatva a fájlok elérési útjai eltérőek. Ez a modul ezt a különbséget kezeli, hogy a többi kód ne foglalkozzon vele:
- `get_resource_path()` — az exe-be beépített statikus fájlok útvonala (pl. ikon)
- `get_app_root()` — az exe melletti mappa útvonala, ahol a `results/` és `macros/` mappák vannak

---

## Input / Output

### Input
- Egy darab `.pdf` fájl — a felhasználó a fájlválasztó dialógusból tallózza ki
- Típus: Multi Alarm Zrt. vagy Volvo Hungaria Kft. szállítói számla

### Output
- `.xlsx` fájl a `results/` mappában
- Fájlnév formátuma: `{típus}_invoice_{számlaszám}_{YYYYMMDD_HHMMSS}.xlsx`
- Példa: `volvo_invoice_INV-2024-001_20240115_143022.xlsx`

### Kinyert mezők (mindkét típusnál)

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

---

## Fejlesztői futtatás

```bash
# 1. Virtuális környezet létrehozása (egyszer szükséges)
python -m venv .venv

# 2. Aktiválás (Windows bash)
source .venv/Scripts/activate

# 3. Függőségek telepítése
pip install -r requirements.txt

# 4. Alkalmazás indítása
python main.py
```

> **PyCharm:** ha a `.venv` mappát felismeri projektinterpreterként, a beépített terminált automatikusan azzal nyitja meg. Ha mégis kézzel kellene aktiválni (PowerShell terminálban): `.venv\Scripts\activate`

---

## Futtatható .exe készítése (PyInstaller build)

### Előfeltételek

A virtuális környezetnek aktívnak kell lennie, és a PyInstallert is telepíteni kell:

```bash
# bash
source .venv/Scripts/activate

# PowerShell (PyCharm terminál)
.venv\Scripts\activate

pip install pyinstaller
pip install -r requirements.txt
```

### Build futtatása

A parancsot az `src/` projekt gyökeréből kell futtatni:

```bash
pyinstaller --onefile --windowed --name nijhof_invoice_parser \
  --collect-submodules pdfplumber \
  --collect-submodules pandas \
  --collect-submodules openpyxl \
  main.py
```

A kapcsolók jelentése:
- `--onefile` — egyetlen `.exe` keletkezik, nincs kicsomagolás szükséges
- `--windowed` — nincs fekete konzolablak, csak a Tkinter ablak jelenik meg
- `--name nijhof_invoice_parser` — a keletkező exe neve
- `--collect-submodules` — gondoskodik róla, hogy a PDF- és Excel-kezelő csomagok teljes egészükben beépüljenek az exe-be

### Build kimenet

```
src/
├── build/                      # PyInstaller közbülső fájlok (törölhető)
└── dist/
    └── invoice_parser.exe      # A kész, terjeszthető alkalmazás
```

### Telepítés / Átadás

Az `invoice_parser.exe` önálló — nem kell mellé Python. Az átadáshoz az exe-t és a `macros/` mappát kell együtt átmásolni a célgépre:

```
[célmappa]/
├── invoice_parser.exe
└── macros/
    ├── MultiAlarm_betöltő.xlsm
    └── Volvo_betöltő.xlsm
```

A `results/` mappa az első feldolgozáskor automatikusan létrejön az exe mellett.

---

## Napló

Az alkalmazás minden indítást, állapotváltást, feldolgozást és hibát naplóz az `app.log` fájlba (projekt gyökerében). Formátum: `2024-01-15 14:30:22,123 [INFO] Processing started: type=volvo, file=...`

---

## Új számlatípus hozzáadása

1. Létrehozni a `core/<típus>.py` parsert — `process_<típus>(pdf_bytes: bytes) -> List[Dict]`
2. Bővíteni a `services/excel_service.py`-t az export függvénnyel
3. Felvenni a `core/registry.py` `PARSERS` dict-jébe — a GUI és a pipeline automatikusan kezeli
