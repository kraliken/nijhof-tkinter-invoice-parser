"""
utils/logger.py — Naplózás

Az egész alkalmazáshoz egyetlen közös naplózót biztosít, amely az app.log fájlba ír.

Használat bármelyik modulban:
    from utils.logger import get_logger
    log = get_logger()
    log.info("Valami történt")
    log.error("Hiba", exc_info=True)  # exc_info=True: a hiba részleteit is naplózza

Megjegyzés: a naplózó beállítása egyszer fut le az alkalmazás indulásakor,
ezután minden `get_logger()` hívás ugyanezt a beállítást használja.
"""

import logging
from pathlib import Path

# A log fájl helye: utils/ szülője = src/
_LOG_PATH = Path(__file__).parent.parent / "app.log"

# Naplózó beállítása: fájlba ír, időbélyeg + szint + üzenet formátumban.
logging.basicConfig(
    filename=str(_LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8",
)


def get_logger(name: str = "invoice_parser") -> logging.Logger:
    """Visszaadja az alkalmazás naplózóját."""
    return logging.getLogger(name)
