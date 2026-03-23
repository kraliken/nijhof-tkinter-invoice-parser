"""
services/file_service.py — Bemeneti validáció

Ez a modul ellenőrzi, hogy a felhasználó által megadott adatok
helyesek-e a feldolgozás megkezdése előtt.

A validáció a GUI-tól független (nem tkinter-specifikus),
ezért könnyen tesztelhető és cserélhető.
"""

from pathlib import Path
from typing import Optional


def validate_pdf(invoice_type: Optional[str], pdf_path: Optional[Path]) -> Optional[str]:
    """Validálja a feldolgozáshoz szükséges bemenetet.

    Sorrendben ellenőrzi:
      1. Választott-e számlatípust a felhasználó?
      2. Választott-e fájlt?
      3. Létezik-e a fájl a lemezen?
      4. PDF kiterjesztésű-e?

    Args:
        invoice_type: A kiválasztott számlatípus kulcsa (pl. "multialarm"), vagy None.
        pdf_path: A kiválasztott PDF fájl útvonala, vagy None.

    Returns:
        Hibaüzenet string ha valami nem stimmel, None ha minden rendben.
        A GUI ezt a visszatérési értéket jeleníti meg a felhasználónak.
    """
    if not invoice_type:
        return "Válassz számlatípust."
    if not pdf_path:
        return "Válassz PDF fájlt."
    if not pdf_path.exists():
        return "A fájl nem található."
    if pdf_path.suffix.lower() != ".pdf":
        return "Csak .pdf fájl fogadható el."
    return None
