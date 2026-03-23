# Invoice Parser

Tkinter GUI alkalmazás Multi Alarm Zrt. és Volvo Hungaria Kft. PDF számláinak automatikus feldolgozásához. A kinyert adatokat Excel fájlba exportálja, amelyet egy makró betöltő importál, átalakít, és könyvelési programba importálható fájlt generál belőle.

---

## Gyors indítás

```bash
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt
python main.py
```

---

## Könyvtárstruktúra

```
invoice-parser/
├── main.py                    # Belépési pont
├── core/
│   ├── registry.py            # Parser konfiguráció (ide kell új típust felvenni)
│   ├── multialarm.py          # Multi Alarm PDF → List[Dict]
│   └── volvo.py               # Volvo PDF → List[Dict]
├── services/
│   ├── processing_service.py  # Pipeline: PDF olvasás → parse → Excel export
│   ├── excel_service.py       # List[Dict] → .xlsx (pandas)
│   └── file_service.py        # Bemeneti validáció
├── ui/
│   ├── main_window.py         # Tkinter főablak (App osztály)
│   ├── state.py               # AppState enum
│   └── theme.py               # Színek, padding konstansok
├── utils/
│   ├── logger.py              # app.log konfiguráció
│   └── paths.py               # Útvonalak (dev és PyInstaller exe kontextus)
├── macros/                    # Excel betöltők (importál + könyvelési fájlt generál)
├── resources/                 # app_icon.ico
└── results/                   # Generált .xlsx fájlok (runtime, auto-keletkezik)
```

---

## Architektúra

```
UI (main_window.py)
  └─► services/processing_service.run()       ← háttérszálban fut
            ├─► core/<típus>.process_*()      ← PDF → List[Dict]
            └─► services/excel_service.*()    ← List[Dict] → .xlsx
```

A feldolgozás `threading.Thread`-ben fut, hogy a GUI ne fagyjon le. A GUI frissítés `root.after(0, callback)` mechanizmuson keresztül történik vissza a fő szálba.

---

## Két számlatípus

| | Multi Alarm | Volvo |
|---|---|---|
| PDF típus | Szövegalapú | Táblázatalapú |
| Kinyerés | `extract_text()` + regex | `extract_tables()` + regex |
| Dátum | `YYYY.MM.DD` | `DD-MM-YYYY` |
| ÁFA | PDF-ből kinyerve | Kalkulált: `net × 0.27` |

---

## Adatséma (egy sor = egy jármű + időszak)

**Közös mezők:** `invoice_number`, `invoice_date`, `payment_due`, `performance_date`, `period_start`, `period_end`, `license_plate`, `net`

**Csak Multi Alarm:** `vat_percent`, `vat_amount`

**Csak Volvo (Excel-ben számított):** `vat`

---

## Állapotgép

```
IDLE → TYPE_SELECTED → FILE_SELECTED → PROCESSING → SUCCESS
                                                  ↘ ERROR → FILE_SELECTED
```

---

## Új számlatípus hozzáadása

1. **`core/<nev>.py`** — `process_<nev>(pdf_bytes: bytes) -> List[Dict]`
2. **`services/excel_service.py`** — `export_<nev>_to_excel(data, output_path)`
3. **`core/registry.py`** — új bejegyzés a `PARSERS` szótárba:

```python
"<nev>": {
    "label":      "...",
    "subtitle":   "...",
    "card_col":   2,           # következő oszlop
    "card_value": 3,           # következő int (0 = nincs kiválasztva)
    "process_fn": process_<nev>,
    "export_fn":  export_<nev>_to_excel,
    "macro":      "<Nev>_betöltő",
}
```

4. **`macros/<Nev>_betöltő.xlsm`** — makró betöltő fájl elhelyezése

A GUI és a pipeline automatikusan felismeri az új típust.

---

## Függőségek

```
pdfplumber   # PDF kinyerés
pandas       # DataFrame → Excel
openpyxl     # .xlsx backend
```

---

## Részletes dokumentáció

Lásd: [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md)
