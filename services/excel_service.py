"""
services/excel_service.py — Excel export

Ez a modul a kinyert adatokat (List[Dict]) Excel fájllá alakítja
pandas DataFrame-en keresztül, openpyxl backend-del.

Dátumkezelés:
  - Multialarm: "YYYY.MM.DD" formátum → pandas datetime
  - Volvo: "DD-MM-YYYY" formátum → pandas datetime
  Ha az átalakítás nem sikerül, a dátum string-ként marad az Excelben
  (silent fallback a `except: pass` blokkokban).

ÁFA kezelése:
  - Multialarm: az ÁFA összege és százaléka a PDF-ből jön, exportálva van.
  - Volvo: az ÁFA nincs a PDF-ben, az exportnál számítjuk: net * 0.27, kerekítve 0 tizedesre.
"""

from pathlib import Path
from typing import List, Dict

import pandas as pd


def export_multialarm_to_excel(data: List[Dict], output_path: Path) -> None:
    """Multialarm adatokat ír ki Excel fájlba.

    Args:
        data: A process_multialarm() által visszaadott lista.
        output_path: A kimeneti .xlsx fájl teljes útvonala.
    """
    df = pd.DataFrame(data)

    # Dátum oszlopok konvertálása Python datetime-ra (→ Excel dátum cellák lesznek)
    # A Multialarm formátuma: "2024.01.15"
    for col in [
        "period_start",
        "period_end",
        "invoice_date",
        "payment_due",
        "performance_date",
    ]:
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], format="%Y.%m.%d")
            except Exception:
                pass  # Ha a konverzió nem sikerül, string-ként hagyja

    df.to_excel(output_path, index=False)


def export_volvo_to_excel(data: List[Dict], output_path: Path) -> None:
    """Volvo adatokat ír ki Excel fájlba, ÁFA kiszámítással.

    Args:
        data: A process_volvo() által visszaadott lista.
        output_path: A kimeneti .xlsx fájl teljes útvonala.
    """
    if not data:
        return

    df = pd.DataFrame(data)

    # Dátum oszlopok konvertálása: a Volvo formátuma "15-01-2024" (DD-MM-YYYY)
    for col in [
        "period_start",
        "period_end",
        "invoice_date",
        "payment_due",
        "performance_date",
    ]:
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], format="%d-%m-%Y", errors="raise")
            except Exception:
                pass  # Ha a konverzió nem sikerül, string-ként hagyja

    # ÁFA kiszámítása: a Volvo PDF nem tartalmazza, 27%-os fix kulcsot alkalmazunk
    df["vat"] = (df["net"] * 0.27).round(0)

    df.to_excel(output_path, index=False)


def export_to_excel(invoice_type: str, data: List[Dict], output_path: Path) -> None:
    """Egységes export interfész — a registry által hívott változat.

    Args:
        invoice_type: "multialarm" vagy "volvo"
        data: A megfelelő parser által visszaadott lista.
        output_path: A kimeneti .xlsx fájl teljes útvonala.
    """
    if invoice_type == "multialarm":
        export_multialarm_to_excel(data, output_path)
    else:
        export_volvo_to_excel(data, output_path)
