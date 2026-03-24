"""
core/registry.py — Támogatott számlatípusok nyilvántartása

Ez a modul az egyetlen hely, ahol az összes támogatott számlatípus regisztrálva van.
Ha új számlatípust kell hozzáadni (pl. "bmw"), elég ide felvenni egy új bejegyzést —
a GUI és a feldolgozó logika automatikusan felismeri.

PARSERS struktúra (minden kulcs egy számlatípus):
    label       — megjelenített név a GUI kártyán
    subtitle    — alcím a kártyán (pl. a cég teljes neve)
    card_col    — a kártya helye a rácson (0 = bal, 1 = jobb)
    card_value  — belső azonosítószám a kártyához
                  (1-től indul, mert 0 = "nincs kiválasztva")
    process_fn  — az a függvény, amely a PDF-ből kinyeri az adatokat
    export_fn   — az a függvény, amely az adatokat Excel fájlba írja
    macro       — a macros/ mappában lévő Excel betöltő fájl nevének előtagja
"""

from core.multialarm import process_multialarm
from core.volvo import process_volvo
from services.excel_service import export_multialarm_to_excel, export_volvo_to_excel

PARSERS = {
    "multialarm": {
        "label": "Multi Alarm",
        "subtitle": "Multi Alarm Zrt. szállítói számla",
        "card_col": 0,
        "card_value": 1,
        "process_fn": process_multialarm,
        "export_fn": export_multialarm_to_excel,
        "macro": "MultiAlarm_betöltő",
    },
    "volvo": {
        "label": "Volvo",
        "subtitle": "Volvo Hungaria Kft. szállítói számla",
        "card_col": 1,
        "card_value": 2,
        "process_fn": process_volvo,
        "export_fn": export_volvo_to_excel,
        "macro": "Volvo_betöltő",
    },
}

# Fordított keresés: belső azonosítószám → számlatípus neve.
# Szükséges, mert a GUI Radiobutton integer értékekkel dolgozik (card_value),
# de a feldolgozó kódnak a típus nevére van szüksége (pl. "multialarm").
VALUE_TO_TYPE = {cfg["card_value"]: key for key, cfg in PARSERS.items()}
