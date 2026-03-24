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
import sys
from pathlib import Path


def _get_log_path() -> Path:
    """
    Meghatározza a log fájl helyét:
    - EXE futás esetén: az exe mappája
    - Fejlesztés (python main.py): projekt gyökér (src/)
    """
    if getattr(sys, "frozen", False):
        # PyInstaller exe futás
        return Path(sys.executable).parent / "app.log"
    else:
        # Fejlesztői futás
        return Path(__file__).parent.parent / "app.log"


_LOG_PATH = _get_log_path()

# Logger konfigurálása
logging.basicConfig(
    filename=str(_LOG_PATH),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    encoding="utf-8",
)


def get_logger(name: str = "invoice_parser") -> logging.Logger:
    return logging.getLogger(name)
