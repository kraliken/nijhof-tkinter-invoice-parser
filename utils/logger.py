"""
utils/logger.py — Naplózás (logging) konfigurációja

Egyetlen, fájlba író logger-t biztosít az egész alkalmazáshoz.
A log fájl helye: invoice-parser/app.log (a projekt gyökerében).

Használat bármelyik modulban:
    from utils.logger import get_logger
    log = get_logger()
    log.info("Valami történt")
    log.error("Hiba", exc_info=True)  # exc_info=True csatolja a stack trace-t

Megjegyzés: a `logging.basicConfig(...)` csak egyszer fut le (modul betöltéskor),
így az összes `get_logger()` hívás ugyanazt a konfigurált handlert használja.
"""

import logging
from pathlib import Path

# A log fájl a projekt gyökerében (utils/ szülője = invoice-parser/)
_LOG_PATH = Path(__file__).parent.parent / "app.log"

# Egyszeri globális konfiguráció: fájlba ír, UTF-8 kódolással,
# timestamp + szint + üzenet formátumban.
logging.basicConfig(
    filename=str(_LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)


def get_logger(name: str = "invoice_parser") -> logging.Logger:
    """Visszaad egy named logger-t. Alapértelmezett név: 'invoice_parser'."""
    return logging.getLogger(name)
