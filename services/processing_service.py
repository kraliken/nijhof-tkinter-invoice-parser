"""
services/processing_service.py — Feldolgozási orchestrátor

Ez a modul köti össze a PDF parsert és az Excel exportot.
A GUI ebből a modulból hívja a `run()` függvényt háttérszálban.

Felelőssége:
  1. A PDF fájl beolvasása bájtként.
  2. A megfelelő parser meghívása (a registry-ből).
  3. Az output fájlnév generálása (típus + számlaszám + timestamp).
  4. A results/ mappa létrehozása, ha nem létezik.
  5. Az Excel export meghívása.
  6. Az output fájl útvonalának visszaadása a GUI-nak.

A `run()` háttérszálból hívódik (threading.Thread), így nem blokkolja a GUI-t.
Kivételt dob, ha a parser üres adatot ad vissza — a GUI ezt kezeli.
"""

from datetime import datetime
from pathlib import Path

from core.registry import PARSERS
from utils.paths import get_app_root


def run(invoice_type: str, pdf_path: Path) -> Path:
    """PDF feldolgozás és Excel export — a teljes pipeline egy függvényben.

    Args:
        invoice_type: Parser kulcs a registry-ből (pl. "multialarm", "volvo").
        pdf_path: A feldolgozandó PDF fájl elérési útja.

    Returns:
        Az elkészült Excel fájl abszolút elérési útja.

    Raises:
        ValueError: Ha a parser nem tud adatot kinyerni a PDF-ből
                    (pl. nem megfelelő PDF struktúra).
    """
    # A registry-ből lekérjük a parser és export függvényeket
    parser = PARSERS[invoice_type]

    # PDF beolvasása bájtként — így a parser nem függ a fájlrendszertől
    pdf_bytes = pdf_path.read_bytes()
    data = parser["process_fn"](pdf_bytes)

    if not data:
        raise ValueError("Nem sikerült adatot kinyerni a PDF-ből.")

    # Fájlnév generálása: típus + számlaszám + timestamp (ütközések elkerülésére)
    # Példa: "volvo_invoice_INV-2024-001_20240115_143022.xlsx"
    invoice_number = data[0].get("invoice_number", "unknown")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{invoice_type}_invoice_{invoice_number}_{timestamp}.xlsx"

    # Az output mappa az alkalmazás gyökerében van (exe mellett, ill. dev-ben a projekt gyökerében)
    result_dir = get_app_root() / "results"
    result_dir.mkdir(exist_ok=True)  # Létrehozza, ha nem létezik; nem dob hibát, ha igen
    output_path = result_dir / filename

    parser["export_fn"](data, output_path)
    return output_path
