# Invoice Parser — Fejlesztői dokumentáció

> **Alkalmazás neve:** BPiON Invoice Parser v2.0
> **Cél:** Multi Alarm Zrt. és Volvo Hungaria Kft. PDF számláinak automatikus feldolgozása Excel formátumba
> **Platform:** Windows (Tkinter GUI, `os.startfile` API)
> **Python:** 3.10+

---

## Tartalomjegyzék

1. [Projekt áttekintés](#1-projekt-áttekintés)
2. [Könyvtárstruktúra](#2-könyvtárstruktúra)
3. [Architektúra és rétegek](#3-architektúra-és-rétegek)
4. [Adatfolyam — a teljes pipeline](#4-adatfolyam--a-teljes-pipeline)
5. [Állapotgép (State Machine)](#5-állapotgép-state-machine)
6. [Modulok részletes leírása](#6-modulok-részletes-leírása)
   - [main.py](#mainpy)
   - [core/registry.py](#coreregistrypy)
   - [core/multialarm.py](#coremultialarmpy)
   - [core/volvo.py](#corevolvo)
   - [services/file\_service.py](#servicesfile_servicepy)
   - [services/excel\_service.py](#servicesexcel_servicepy)
   - [services/processing\_service.py](#servicesprocessing_servicepy)
   - [ui/state.py](#uistatepy)
   - [ui/theme.py](#uithemepy)
   - [ui/main\_window.py](#uimain_windowpy)
   - [utils/logger.py](#utilsloggerpy)
   - [utils/paths.py](#utilspathspy)
7. [Adatsémák](#7-adatsémák)
8. [PDF feldolgozási stratégiák](#8-pdf-feldolgozási-stratégiák)
9. [Függőségek](#9-függőségek)
10. [Fejlesztői környezet beállítása](#10-fejlesztői-környezet-beállítása)
11. [Új számlatípus hozzáadása](#11-új-számlatípus-hozzáadása)
12. [Ismert korlátok és edge case-ek](#12-ismert-korlátok-és-edge-case-ek)

---

## 1. Projekt áttekintés

Az alkalmazás célja, hogy a könyvelési munkafolyamat egy ismétlődő, manuális lépését automatizálja: a bejövő PDF formátumú szállítói számlákat strukturált Excel táblává alakítja, amelyet egy Excel makró betöltő (`macros/`) importál, majd könyvelési programba tölthető formátumra alakít.

### A teljes könyvelési munkafolyamat

```
PDF számla érkezik
      ↓
[Invoice Parser alkalmazás]
  Felhasználó kiválasztja a számlatípust és a PDF fájlt
      ↓
  Alkalmazás kinyeri az adatokat → .xlsx fájl a results/ mappába
      ↓
[Excel makró betöltő — macros/]
  Felhasználó megnyitja a megfelelő betöltő makrót (pl. MultiAlarm_betöltő.xlsm)
      ↓
  A makró importálja a kinyert .xlsx adatait
      ↓
  A makrós Excel átalakítja és kiegészíti az adatokat a szükséges formára
  (pl. főkönyvi számok, cost centerek, könyvelési mezők hozzárendelése)
      ↓
  A makrós Excel legenerálja és lementi a könyvelési programba importálható fájlt
      ↓
[Könyvelési program]
  A fájl importálásával a számla rögzítésre kerül
```

### Két támogatott számlatípus összehasonlítása

| Tulajdonság | Multi Alarm | Volvo |
|---|---|---|
| Cég | Multi Alarm Zrt. | Volvo Hungaria Kft. |
| PDF struktúra | Szövegalapú | Táblázatalapú |
| Kinyerési módszer | `extract_text()` + regex | `extract_tables()` + regex |
| Dátum formátum | `YYYY.MM.DD` | `DD-MM-YYYY` |
| ÁFA forrása | PDF-ből kinyerve | Kalkulált: `net × 0.27` |
| Számlaszám forrása | Regex a szövegből | Első táblázat, 2. sor, 1. cella |
| Tételek azonosítása | "Menetlevél + útdíj..." sor | 2. táblázat sorai |

---

## 2. Könyvtárstruktúra

```
invoice-parser/
│
├── main.py                        # Belépési pont
├── requirements.txt               # Python függőségek
├── DEVELOPER_GUIDE.md             # Ez a dokumentáció
├── app.log                        # Futásidejű napló (automatikusan keletkezik)
│
├── core/                          # Üzleti logika — PDF adatkinyerés
│   ├── __init__.py
│   ├── registry.py                # Parser konfiguráció (central registry)
│   ├── multialarm.py              # Multi Alarm PDF parser
│   └── volvo.py                   # Volvo PDF parser
│
├── services/                      # Alkalmazásszolgáltatások
│   ├── __init__.py
│   ├── file_service.py            # Bemeneti validáció
│   ├── excel_service.py           # Excel export (pandas)
│   └── processing_service.py     # Pipeline orchestrátor
│
├── ui/                            # Tkinter GUI
│   ├── __init__.py
│   ├── state.py                   # AppState enum
│   ├── theme.py                   # Vizuális konstansok (színek, padding)
│   └── main_window.py             # Főablak (App osztály)
│
├── utils/                         # Segédeszközök
│   ├── __init__.py
│   ├── logger.py                  # Naplózás konfiguráció
│   └── paths.py                   # Útvonal-feloldás (dev + PyInstaller)
│
├── resources/                     # Bundled statikus fájlok
│   └── app_icon.ico               # Alkalmazás ikon
│
├── macros/                        # Excel makró betöltők
│   ├── MultiAlarm_betöltő.xlsm   #   importálja a results/.xlsx-et, átalakítja,
│   └── Volvo_betöltő.xlsm        #   és könyvelési programba importálható fájlt generál
│
├── results/                       # Generált Excel fájlok (runtime)
│   └── <típus>_invoice_<szám>_<timestamp>.xlsx
│
└── .venv/                         # Virtuális Python környezet
```

---

## 3. Architektúra és rétegek

Az alkalmazás három jól elkülönített rétegre épül:

```
┌─────────────────────────────────────────────────────┐
│                     UI réteg                        │
│   ui/main_window.py  •  ui/state.py  •  ui/theme.py │
│   Tkinter GUI, állapotgép, vizuális visszajelzés    │
└───────────────────────┬─────────────────────────────┘
                        │ hívja
┌───────────────────────▼─────────────────────────────┐
│                  Services réteg                      │
│  processing_service.py  •  excel_service.py         │
│  file_service.py                                    │
│  Pipeline orchestráció, validáció, export           │
└──────────┬────────────────────────┬─────────────────┘
           │ hívja                  │ hívja
┌──────────▼──────────┐  ┌──────────▼──────────────────┐
│    Core réteg       │  │       Utils réteg            │
│  registry.py        │  │  logger.py  •  paths.py      │
│  multialarm.py      │  │  Naplózás, útvonalak         │
│  volvo.py           │  └─────────────────────────────┘
│  PDF → List[Dict]   │
└─────────────────────┘
```

### Tervezési elvek

- **Szétválasztott felelősségek:** A core réteg tisztán funkcionális (nincs mellékhatás), a services réteg koordinál, az ui réteg csak megjelenítéssel foglalkozik.
- **Registry pattern:** Új számlatípus hozzáadása egyetlen helyen (`core/registry.py`) elvégezhető — a GUI és a pipeline automatikusan felismeri.
- **Thread-safety:** A feldolgozás háttérszálban fut, a GUI frissítés `root.after(0, callback)` mechanizmuson keresztül történik.
- **Dev/PyInstaller kettősség:** Az útvonal-feloldás (`utils/paths.py`) transzparensen kezeli mindkét kontextust.

---

## 4. Adatfolyam — a teljes pipeline

```
[PDF fájl a lemezen]
         │
         │ pdf_path.read_bytes()
         ▼
[pdf_bytes: bytes]
         │
         │ parser["process_fn"](pdf_bytes)
         ▼
[data: List[Dict]]           ← pdfplumber + regex
         │
         │ if not data → ValueError
         │
         │ parser["export_fn"](data, output_path)
         ▼
[.xlsx fájl a results/ mappában]
         │
         │ return output_path
         ▼
[GUI megjeleníti az eredményt]
```

### Hívási lánc részletesen

```
ui/main_window.py
  App._start_processing()
    → threading.Thread(_processing_worker)
        → services/processing_service.run(invoice_type, pdf_path)
            → PARSERS[invoice_type]["process_fn"](pdf_bytes)
               # multialarm: core/multialarm.process_multialarm()
               # volvo:      core/volvo.process_volvo()
            → PARSERS[invoice_type]["export_fn"](data, output_path)
               # multialarm: services/excel_service.export_multialarm_to_excel()
               # volvo:      services/excel_service.export_volvo_to_excel()
        → root.after(0, _on_processing_done)
```

---

## 5. Állapotgép (State Machine)

Az alkalmazás állapotát az `AppState` enum tartalmazza, az átmenetek a `App.set_state()` metóduson keresztül történnek.

```
         ┌─────────────────────────────┐
         │           IDLE              │
         │  (nincs semmi kiválasztva)  │
         └──────────────┬──────────────┘
                        │ számlatípus kiválasztva
         ┌──────────────▼──────────────┐
         │       TYPE_SELECTED         │
         │  (típus van, PDF nincs)     │
         └──────────────┬──────────────┘
                        │ PDF kiválasztva
         ┌──────────────▼──────────────┐
    ┌───►│       FILE_SELECTED         │◄──┐
    │    │  (feldolgozás indítható)    │   │
    │    └──────────────┬──────────────┘   │
    │                   │ ▶ gomb           │
    │    ┌──────────────▼──────────────┐   │
    │    │         PROCESSING          │   │
    │    │  (háttérszál fut)           │   │
    │    └────────┬────────────┬───────┘   │
    │             │ siker      │ hiba      │
    │    ┌────────▼───────┐  ┌─▼────────┐ │
    │    │    SUCCESS     │  │  ERROR   │─┘
    │    │ (Excel kész)   │  │          │
    │    └────────────────┘  └──────────┘
    │                                  │
    └──── "Új feldolgozás" menü ───────┘
```

### Állapot hatásai a GUI-ra

| Állapot | ▶ Gomb | Progressbar | Súgó aktív lépés | Eredmény szekció |
|---|---|---|---|---|
| `IDLE` | disabled | rejtve | ① | rejtve |
| `TYPE_SELECTED` | disabled | rejtve | ② | rejtve |
| `FILE_SELECTED` | **enabled** | rejtve | ③ | rejtve |
| `PROCESSING` | disabled | **látható** | ④ | rejtve |
| `SUCCESS` | **enabled** | rejtve | ⑤ | **látható** |
| `ERROR` | **enabled** | rejtve | ③ | rejtve |

---

## 6. Modulok részletes leírása

### `main.py`

**Felelősség:** Belépési pont. Gondoskodik a `sys.path` beállításáról és elindítja az alkalmazást.

```python
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))   # ui, core, services, utils importálhatóvá válik

app = App()
app.run()   # Tkinter mainloop — blokkoló
```

**Megjegyzés:** A `sys.path` manipuláció azért szükséges, mert az alkalmazás bármely könyvtárból futtatható (`python invoice-parser/main.py`), és a relatív importok csak akkor működnek, ha a projekt gyökere benne van a keresési útban.

---

### `core/registry.py`

**Felelősség:** Central registry — az összes támogatott számlatípus konfigurációja egy helyen.

**`PARSERS` szótár struktúrája:**

```python
PARSERS = {
    "<kulcs>": {
        "label":      str,       # GUI kártya főcíme
        "subtitle":   str,       # GUI kártya alcíme
        "card_col":   int,       # Kártya oszlop indexe (0 vagy 1)
        "card_value": int,       # IntVar értéke (1-től, 0 = "nincs kiválasztva")
        "process_fn": Callable,  # PDF → List[Dict]
        "export_fn":  Callable,  # List[Dict] → Excel fájl
        "macro":      str,       # Makró fájl neve (kiterjesztés nélkül)
    }
}
```

**`VALUE_TO_TYPE`:** Fordított leképezés az IntVar értékéről a string kulcsra. A GUI Radiobutton integer értékekkel dolgozik, a pipeline string kulcsokat vár.

```python
VALUE_TO_TYPE = {1: "multialarm", 2: "volvo"}
```

---

### `core/multialarm.py`

**Felelősség:** Multi Alarm PDF számlák adatkinyerése.

**Stratégia:** Teljes szöveg kinyerés (`extract_text()`) + regex minták.

#### Kinyerési logika

**1. lépés — Fejléc adatok (az egész számlán egységes):**

| Mező | Regex minta | Példa érték |
|---|---|---|
| `invoice_number` | `Számla száma:\s*(\d+)` | `260106605` |
| `invoice_date` | `Számla kelte:\s*([\d\.]+)` | `2026.01.06` |
| `payment_due` | `Fizetési határidő:\s*([\d\.]+)` | `2026.01.20` |
| `performance_date` | `Teljesítési dátum:\s*([\d\.]+)` | `2025.12.31` |

*A dátumokból a végső pont `.rstrip(".")` hívással kerül eltávolításra.*

**2. lépés — Tételsorok (járművenként/időszakonként):**

Három párhuzamos lista épül fel:
- `periods`: `Időszak:\s*([\d\.]+ - [\d\.]+)` → `"2025.12.01 - 2025.12.31"`
- `license_plates`: `Felszerelési hely:\s+(\S+)` → `"ABC-123"`
- `lines`: A `"Menetlevél + útdíj alapszolgáltatás"` szöveggel kezdődő teljes sor

A három lista index szerint van összeillesztve (`min_len = min(len(...), len(...), len(...))`).

**3. lépés — Összegek kinyerése a tételsorból:**

```
Menetlevél + útdíj alapszolgáltatás  1 234,56Ft  5 678,90Ft  1 532,91Ft  7 211,81Ft  27 %
                                     ─────────── ─────────── ─────────── ─────────── ─────
                                     amounts[0]  amounts[1]  amounts[2]  amounts[3]
                                     (egységár)  (nettó)     (ÁFA össz.) (bruttó)
```

Regex: `r"(\d{1,3}(?: \d{3})*,\d{2})Ft"` (szóközzel elválasztott ezresek, vesszős tizedes)

**Adat normalizálás:**
- `"5 678,90"` → `float("5678.90")` = `5678.9`
- Rendszám: `"ABC-123"` → `"ABC123"` (kötőjel és szóköz eltávolítása)

---

### `core/volvo.py`

**Felelősség:** Volvo Hungaria PDF számlák adatkinyerése.

**Stratégia:** Táblázat kinyerés (`extract_tables()`) + regex.

#### PDF struktúra

```
1. oldal:
  ├── tables[0]   → Fejléc táblázat
  │     └── [1][0] → Számlaszám (pl. "70260001279")
  └── szöveg      → Dátumsor: "XX-XX-XXXX  XX-XX-XXXX  XX-XX-XXXX"
                               invoice_date  payment_due  performance_date

Minden oldal:
  └── tables[1]   → Tétel táblázat
        └── sorok → Egy sor = egy jármű + időszak
```

#### Egy tételsor kinyerési logikája

```
Sor cellák összefűzve (flat_row):
  "Leírás szöveg ABC123 01-01-2026 31-01-2026 ... 1.234,56"
                 ──────── ──────────── ────────────          ──────────
                 rendszám  period_start period_end            net (utolsó összeg)

Sortörések megtartásával (row_with_breaks):
  ["Leírás szöveg", "ABC123 01-01-2026 ...", ...]
                     ───────────────────────
                     rendszám kinyerése innen
```

**Rendszám kinyerése:** A sortörés utáni rész első dátum előtti szövege.
```python
re.search(r"(.+?)\s*\d{2}-\d{2}-\d{4}", after_newline).group(1)
```

**Összeg formátum:** `"1.234,56"` (pont = ezreselválasztó, vessző = tizedesjel)
```python
float(amount.replace(".", "").replace(",", "."))  # → 1234.56
```

---

### `services/file_service.py`

**Felelősség:** Bemeneti validáció — ellenőrzi, hogy a feldolgozás megkezdése előtt minden szükséges adat rendelkezésre áll.

**`validate_pdf(invoice_type, pdf_path) → Optional[str]`**

Sorrendben ellenőrzi:
1. Van-e kiválasztott számlatípus?
2. Van-e kiválasztott fájl?
3. Létezik-e a fájl a lemezen?
4. PDF kiterjesztésű-e?

Visszatér: hibaüzenet stringgel, vagy `None` ha minden rendben. A GUI ezt a stringet jeleníti meg a piros hibadobozban.

---

### `services/excel_service.py`

**Felelősség:** A kinyert `List[Dict]` adatot Excel fájlba írja pandas DataFrame-en keresztül.

#### `export_multialarm_to_excel(data, output_path)`

- Dátum konverzió: `"%Y.%m.%d"` formátumból pandas datetime-ra
- Érintett oszlopok: `period_start`, `period_end`, `invoice_date`, `payment_due`, `performance_date`
- ÁFA: a PDF-ből jön, nincs számítás

#### `export_volvo_to_excel(data, output_path)`

- Dátum konverzió: `"%d-%m-%Y"` formátumból pandas datetime-ra
- ÁFA számítás: `df["vat"] = (df["net"] * 0.27).round(0)`
- Az ÁFA az Excel fájlban kerül hozzáadásra (a PDF nem tartalmazza)

**Megjegyzés a dátum konverzióhoz:** Ha a konverzió bármely okból meghiúsul (pl. szokatlan PDF formátum), a `except: pass` blokk csendesen átugorja — a dátum string-ként marad az Excelben, ami vizuálisan jelzi a problémát, de nem okoz összeomlást.

---

### `services/processing_service.py`

**Felelősség:** Pipeline orchestrátor — összefogja a PDF kinyerést és az Excel exportot.

**`run(invoice_type, pdf_path) → Path`**

```python
1. parser = PARSERS[invoice_type]
2. pdf_bytes = pdf_path.read_bytes()
3. data = parser["process_fn"](pdf_bytes)
4. if not data: raise ValueError(...)
5. filename = f"{type}_invoice_{number}_{timestamp}.xlsx"
6. result_dir = get_app_root() / "results"
7. result_dir.mkdir(exist_ok=True)
8. parser["export_fn"](data, result_dir / filename)
9. return output_path
```

**Output fájlnév konvenció:**
```
multialarm_invoice_260106605_20260323_092031.xlsx
──────────────────────────── ──────── ────────────
      számlatípus             számlasz. timestamp
```

**Kivételkezelés:** A `ValueError` a GUI `_on_processing_done()` metódusáig propagál, ahol hibaüzenetként jelenik meg.

---

### `ui/state.py`

**Felelősség:** Az `AppState` enum definíciója — az alkalmazás lehetséges állapotai.

```python
class AppState(Enum):
    IDLE           # Kezdőállapot
    TYPE_SELECTED  # Típus kiválasztva, PDF még nem
    FILE_SELECTED  # PDF is kiválasztva, kész a feldolgozásra
    PROCESSING     # Háttérszál fut
    SUCCESS        # Excel sikeresen elkészült
    ERROR          # Hiba a feldolgozás során
```

---

### `ui/theme.py`

**Felelősség:** Vizuális konstansok — színek és padding értékek egy helyen.

```python
SECTION_PAD = 8              # px, szekciók közötti függőleges távolság

CARD_IDLE     = { bg, border, fg, sub }   # Nem kiválasztott kártya
CARD_SELECTED = { bg, border, fg, sub }   # Kiválasztott kártya (Google kék: #1A73E8)

ERROR_BG / ERROR_FG     # Piros visszajelző doboz
SUCCESS_BG / SUCCESS_FG # Zöld visszajelző doboz
```

---

### `ui/main_window.py`

**Felelősség:** A teljes GUI megvalósítása egyetlen `App` osztályban.

#### Osztály attribútumok

| Attribútum | Típus | Leírás |
|---|---|---|
| `root` | `tk.Tk` | Főablak |
| `state` | `AppState` | Aktuális állapot |
| `selected_type` | `Optional[str]` | `"multialarm"` vagy `"volvo"` |
| `selected_file` | `Optional[Path]` | Kiválasztott PDF útvonala |
| `parsed_data` | `Optional[list]` | Parser kimenete (tárolt referencia) |
| `result_path` | `Optional[Path]` | Elkészült Excel fájl útvonala |

#### Szekciók és widgetek

```
_build_layout()
├── menubar                      → Új feldolgozás | Kilépés
├── canvas + scrollbar           → Scrollozható tartalom
└── content (ttk.Frame)
    ├── _build_header()
    │     header_frame
    │       └── ikon (📄) + cím + alcím
    │
    ├── _build_help_section()
    │     help_frame (LabelFrame)
    │       ├── _help_num_labels[]   → ①②③④⑤ / ✔
    │       └── _help_step_labels[]  → lépés szövegek
    │
    ├── _build_type_section()
    │     type_frame (LabelFrame)
    │       ├── _type_var (IntVar)   → 0/1/2
    │       └── _type_cards{}        → {key: (card, radiobutton, label)}
    │
    ├── _build_file_section()
    │     file_frame (LabelFrame)
    │       ├── _browse_btn          → Tallózás...
    │       ├── _clear_btn           → × (rejtve fájl nélkül)
    │       ├── _file_name_label     → fájlnév
    │       └── _file_path_label     → teljes útvonal
    │
    ├── _build_processing_section()
    │     processing_frame (LabelFrame)
    │       ├── _process_btn         → ▶ Feldolgozás
    │       ├── _progress_bar        → (rejtve feldolgozáson kívül)
    │       ├── _process_hint        → útmutató szöveg
    │       ├── _error_box           → (rejtve ERROR-on kívül)
    │       │     └── _error_msg_label
    │       └── _success_box         → (rejtve SUCCESS-en kívül)
    │
    └── _build_result_section()
          result_frame (LabelFrame)  → (rejtve SUCCESS-en kívül)
            ├── _result_name_label
            ├── _open_excel_btn      → Kinyert adatok megnyitása
            ├── _open_macro_btn      → Betöltő megnyitása (makró importál + könyvelési fájlt generál)
            ├── _open_pdf_btn        → Számla megnyitása
            └── _result_path_label
```

#### Threading mechanizmus

```
Fő szál (Tkinter event loop)
    │
    │   _start_processing() hívódik
    │
    ├──► set_state(PROCESSING)          ← GUI frissítés a fő szálban ✓
    │
    ├──► threading.Thread(              ← Háttérszál indul
    │      target=_processing_worker,
    │      daemon=True                  ← Ablak bezárásakor leáll
    │    ).start()
    │
    │   [Háttérszál fut]
    │      processing_service.run(...)
    │      root.after(0, callback)      ← GUI frissítés visszaütemezése
    │
    └──► _on_processing_done()          ← Fő szálban fut ✓
```

**Fontos:** Tkinter nem thread-safe. A háttérszálból soha nem szabad közvetlenül widget-et módosítani. A `root.after(0, callback)` biztosítja, hogy a callback a Tkinter event loop-ban, a fő szálban fusson le.

---

### `utils/logger.py`

**Felelősség:** Egyetlen, fájlba író logger az alkalmazás számára.

```python
_LOG_PATH = project_root / "app.log"

logging.basicConfig(
    filename=_LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)
```

**Log fájl helye:** `invoice-parser/app.log`

**Napló bejegyzések:** Alkalmazás indítás/leállítás, állapotváltások, feldolgozás eredménye, hibák (stack trace-szel).

---

### `utils/paths.py`

**Felelősség:** Útvonal-feloldás a fejlesztői és a PyInstaller onefile kontextusban.

#### A két kontextus közötti különbség

| | Dev (`python main.py`) | Frozen (`.exe`) |
|---|---|---|
| `sys.frozen` | `False` | `True` |
| `sys._MEIPASS` | nincs | temp kicsomagolási mappa |
| `sys.executable` | python.exe | az .exe maga |
| App root | `invoice-parser/` | az .exe melletti mappa |
| Resources | `invoice-parser/resources/` | `sys._MEIPASS/resources/` |

#### `get_resource_path(relative_path)`

Bundled resource fájlokhoz (ikon). A PyInstaller spec fájlban meghatározott `datas` lista szerint kerülnek be az exe-be.

```python
# Dev:      invoice-parser/resources/app_icon.ico
# Frozen:   <temp_meipass>/resources/app_icon.ico
```

#### `get_app_root()`

Az alkalmazás "munkamappa" — itt vannak a `results/` és `source/` mappák.

```python
# Dev:      invoice-parser/
# Frozen:   az .exe melletti mappa (pl. live/invoice-parser/)
```

---

## 7. Adatsémák

### Multi Alarm — egy sor (`Dict`)

| Mező | Típus | Leírás | Példa |
|---|---|---|---|
| `invoice_number` | `str` | Számlaszám | `"260106605"` |
| `invoice_date` | `str` | Számla kelte (YYYY.MM.DD) | `"2026.01.06"` |
| `payment_due` | `str` | Fizetési határidő (YYYY.MM.DD) | `"2026.01.20"` |
| `performance_date` | `str` | Teljesítési dátum (YYYY.MM.DD) | `"2025.12.31"` |
| `period_start` | `str` | Időszak kezdete (YYYY.MM.DD) | `"2025.12.01"` |
| `period_end` | `str` | Időszak vége (YYYY.MM.DD) | `"2025.12.31"` |
| `license_plate` | `str` | Rendszám (normalizált) | `"ABC123"` |
| `net` | `float` | Nettó összeg (Ft) | `5678.9` |
| `vat_percent` | `int` | ÁFA kulcs (%) | `27` |
| `vat_amount` | `float` | ÁFA összeg (Ft) | `1533.3` |

### Volvo — egy sor (`Dict`)

| Mező | Típus | Leírás | Példa |
|---|---|---|---|
| `invoice_number` | `str` | Számlaszám | `"70260001279"` |
| `invoice_date` | `str` | Számla kelte (DD-MM-YYYY) | `"06-01-2026"` |
| `payment_due` | `str` | Fizetési határidő (DD-MM-YYYY) | `"20-01-2026"` |
| `performance_date` | `str` | Teljesítési dátum (DD-MM-YYYY) | `"31-12-2025"` |
| `period_start` | `str` | Időszak kezdete (DD-MM-YYYY) | `"01-12-2025"` |
| `period_end` | `str` | Időszak vége (DD-MM-YYYY) | `"31-12-2025"` |
| `license_plate` | `str` | Rendszám (normalizált) | `"ABC123"` |
| `net` | `float` | Nettó összeg (Ft) | `1234.56` |
| *(Excel-ben)* | | | |
| `vat` | `float` | ÁFA összeg — `round(net * 0.27, 0)` | `333.0` |

---

## 8. PDF feldolgozási stratégiák

### Miért különböző stratégia?

A két számlatípus PDF-je eltérő belső struktúrával rendelkezik:

**Multi Alarm** — "folyó szöveg" stílusú PDF: az adatok fix kulcsszavak (`Számla száma:`, `Felszerelési hely:` stb.) után helyezkednek el a szövegfolyamban. A `pdfplumber.extract_text()` egy összefüggő stringet ad vissza, amelyen regex keresés hatékony.

**Volvo** — táblázat-alapú PDF: az adatok strukturált cellarácsban vannak. A `pdfplumber.extract_tables()` 3D listát ad vissza (`táblázatok → sorok → cellák`). A cellák tartalmazhatnak sortörést, ami miatt kétféle összefűzési módra van szükség (flat és sortöréses).

### Regex minták összefoglalása

**Multi Alarm:**
```python
r"Számla száma:\s*(\d+)"                     # Számlaszám
r"Számla kelte:\s*([\d\.]+)"                 # Dátumok
r"Időszak:\s*([\d\.]+ - [\d\.]+)"           # Elszámolási időszak
r"Felszerelési hely:\s+(\S+)"               # Rendszám
r"Menetlevél \+ útdíj alapszolgáltatás[^\n]+"  # Tételsor
r"(\d{1,3}(?: \d{3})*,\d{2})Ft"             # Összegek (pl. "5 678,90Ft")
r"(\d{1,2})\s?%"                             # ÁFA százalék
```

**Volvo:**
```python
r"\d{2}-\d{2}-\d{4}"                        # Dátumok (DD-MM-YYYY)
r"(.+?)\s*\d{2}-\d{2}-\d{4}"               # Rendszám (dátum előtti szöveg)
r"\d{1,3}(?:\.\d{3})*,\d{2}"               # Összegek (pl. "1.234,56")
```

---

## 9. Függőségek

**`requirements.txt`:**
```
pdfplumber    # PDF szöveg és táblázat kinyerés (pdfminer.six wrapper)
pandas        # DataFrame → Excel export
openpyxl      # pandas Excel backend (.xlsx írás)
```

**Beépített Python könyvtárak (nincs telepítés):**
```
tkinter       # GUI framework
threading     # Háttérszál a feldolgozáshoz
re            # Regex minták
io            # BytesIO (PDF bytes → fájlszerű objektum)
pathlib       # Path műveletek
logging       # Naplózás
datetime      # Timestamp generálás
os            # os.startfile (Windows fájlmegnyitás)
sys           # sys.path, sys.frozen, sys._MEIPASS
enum          # AppState enum
```

---

## 10. Fejlesztői környezet beállítása

```bash
# 1. Virtuális környezet létrehozása és aktiválása
python -m venv .venv
source .venv/Scripts/activate

# 2. Függőségek telepítése
pip install -r requirements.txt

# 3. Futtatás fejlesztői módban
python main.py
```

**A `results/` mappa** automatikusan létrejön az első feldolgozáskor — nem kell kézzel létrehozni.

---

## 11. Új számlatípus hozzáadása

Az alkalmazás registry pattern-t használ, ezért egy új számlatípus hozzáadása minimális változtatást igényel.

### Lépések

**1. Hozd létre a parser modult** (`core/<nev>.py`):

```python
# core/bmw.py
import io, re
from typing import List, Dict
import pdfplumber

def process_bmw(pdf_bytes: bytes) -> List[Dict]:
    data: List[Dict] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        # ... adatkinyerési logika ...
    return data
```

**2. Hozd létre az export függvényt** (`services/excel_service.py`):

```python
def export_bmw_to_excel(data: List[Dict], output_path: Path) -> None:
    df = pd.DataFrame(data)
    # ... dátum konverzió, számítások ...
    df.to_excel(output_path, index=False)
```

**3. Regisztráld a `core/registry.py`-ban:**

```python
from core.bmw import process_bmw
from services.excel_service import export_bmw_to_excel

PARSERS = {
    # ... meglévők ...
    "bmw": {
        "label":      "BMW",
        "subtitle":   "BMW Group Financial Services számlája",
        "card_col":   2,               # Következő oszlop
        "card_value": 3,               # Következő egész
        "process_fn": process_bmw,
        "export_fn":  export_bmw_to_excel,
        "macro":      "BMW_betöltő",
    },
}
```

**4. Helyezd el a makró fájlt:** `macros/BMW_betöltő.xlsm`

**Ennyi.** A GUI automatikusan megjelenik egy harmadik kártyával, és a pipeline automatikusan az új parser/export függvényt fogja használni.

> **Megjegyzés a `card_col` és `card_value` értékekről:** A `card_col` a grid oszlopindexe (0-tól), a `card_value` az IntVar értéke (1-től indul, 0 = "nincs kiválasztva"). Ha 2-nél több kártyát szeretnél, a `_build_type_section()` grid konfigurációját (`columnconfigure`) is frissíteni kell.

---

## 12. Ismert korlátok és edge case-ek

### Multi Alarm parser

- **Összeg indexelés:** A parser feltételezi, hogy egy tételsorban legalább 4 `"...Ft"` összeg szerepel (`amounts[0..3]`). Ha a PDF struktúrája változik (pl. kedvezmény sor bekerül), az indexek eltolódhatnak.
- **Párhuzamos listák illesztése:** A `periods`, `license_plates` és `lines` listák `min_len` csonkítással vannak összeillesztve. Ha a PDF-ben egy blokk hiányzik (pl. nincs rendszám), az összes utána következő sor elcsúszhat.
- **Dátum végső pont:** A `.rstrip(".")` eltávolítja a dátumok után lévő pontot. Ha a forrás PDF-ben nincs pont, ez nem okoz hibát (a `rstrip` biztonságos).

### Volvo parser

- **`tables[1]` feltételezés:** Minden oldaltól várja, hogy a 2. táblázat (index 1) tartalmazza a tételeket. Ha egy oldal csak fejléc táblázatot tartalmaz (`len(tables) < 2`), az oldal ki van hagyva — ez helyes viselkedés.
- **`None` cellák:** A `safe_cells` szűrés kezeli, de ha egy egész sor `None`-ból áll, az kihagyódik.
- **Rendszám kinyerése:** A sortörés utáni szövegből a legelső dátum előtti részt veszi. Ha a cella formátuma eltér (pl. nincs sortörés), `license_plate` üres lesz, és a sor nem kerül be az outputba.
- **Utolsó összeg:** `amounts[-1]` — az utolsó szám a sorban. Ha a PDF-ben kiegészítő összegek jelennek meg a nettó után, a kinyert érték helytelen lehet.

### Általános

- **Windows-only:** `os.startfile()` csak Windowson működik. Linux/macOS-re `subprocess.run(["xdg-open", ...])` ill. `subprocess.run(["open", ...])` kellene.
- **Egyetlen PDF:** Az alkalmazás egyszerre egy PDF-et dolgoz fel. Batch feldolgozás nincs implementálva.
- **results/ tisztítás:** A `results/` mappa sosem kerül automatikusan kiürítésre — hosszabb használat esetén manuálisan kell törölni a régi fájlokat.
- **ÁFA kulcs:** A Volvo ÁFA kalkuláció `0.27` konstanssal dolgozik. Ha az ÁFA kulcs változik, a `services/excel_service.py` fájlban kell frissíteni.
