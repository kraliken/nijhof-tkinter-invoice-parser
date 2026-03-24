"""
services/processing_service.py — A teljes feldolgozás összefogása

Ez a modul köti össze a PDF feldolgozást és az Excel exportot.
A GUI ebből a modulból indítja el a `run()` függvényt a háttérben.

Felelőssége:
  1. A PDF fájl beolvasása.
  2. A megfelelő feldolgozó meghívása (a registry-ből).
  3. A kimeneti fájlnév összeállítása (típus + számlaszám + dátum/időbélyeg).
  4. A results/ mappa létrehozása, ha nem létezik.
  5. Az Excel fájl kiírása.
  6. Az elkészült fájl helyének visszaadása a GUI-nak.

A `run()` a háttérben fut, így az ablak nem fagy le feldolgozás közben.
Ha a feldolgozó nem talál adatot a PDF-ben, hibát jelez — a GUI ezt kezeli.
"""

from datetime import datetime
from pathlib import Path

from core.registry import PARSERS
from utils.paths import get_app_root


def run(invoice_type: str, pdf_path: Path) -> Path:
    """PDF feldolgozás és Excel export — a teljes folyamat egy függvényben.

    Args:
        invoice_type: A számlatípus neve (pl. "multialarm", "volvo").
        pdf_path: A feldolgozandó PDF fájl helye.

    Returns:
        Az elkészült Excel fájl helye.

    Raises:
        ValueError: Ha a feldolgozó nem talál értelmezhető adatot a PDF-ben.
    """
    # A registry-ből lekérjük a megfelelő feldolgozó és export függvényeket
    parser = PARSERS[invoice_type]

    # PDF beolvasása
    pdf_bytes = pdf_path.read_bytes()
    data = parser["process_fn"](pdf_bytes)

    if not data:
        raise ValueError("Nem sikerült adatot kinyerni a PDF-ből.")

    # Fájlnév összeállítása: típus + számlaszám + dátum/időbélyeg
    # Az időbélyeg azért kell, hogy két feldolgozás ne írja felül egymást.
    # Példa: "volvo_invoice_INV-2024-001_20240115_143022.xlsx"
    invoice_number = data[0].get("invoice_number", "unknown")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{invoice_type}_invoice_{invoice_number}_{timestamp}.xlsx"

    # A results/ mappa az exe mellett (vagy fejlesztéskor a projekt gyökerében) van
    result_dir = get_app_root() / "results"
    result_dir.mkdir(exist_ok=True)  # Létrehozza, ha még nem létezik
    output_path = result_dir / filename

    parser["export_fn"](data, output_path)
    return output_path
