"""
utils/paths.py — Útvonal-segédfüggvények

Fejlesztői futtatáskor és exe-ként futtatva a fájlok elérési útjai eltérőek.
Ez a modul kezeli ezt a különbséget, hogy a többi kód ne foglalkozzon vele.

  - get_resource_path() → az exe-be beépített statikus fájlokhoz (pl. app_icon.ico)
  - get_app_root()      → az exe melletti mappához (results/, macros/)
"""

import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """Visszaadja az exe-be beépített statikus fájl elérési útját (pl. ikon).

    Args:
        relative_path: A resources/ mappán belüli fájlnév (pl. "app_icon.ico").

    Returns:
        A fájl teljes elérési útja.

    Kontextus:
        - Exe-ként futtatva: a PyInstaller egy ideiglenes mappába csomagolja ki
          a beépített fájlokat — onnan olvassuk be.
        - Fejlesztői futtatáskor: a projekt gyökeréből (src/).
    """
    if hasattr(sys, "_MEIPASS"):
        # Exe: a kicsomagolt ideiglenes mappából
        base_path = Path(sys._MEIPASS)
    else:
        # Fejlesztői futtatás: utils/paths.py → utils/ → src/
        base_path = Path(__file__).resolve().parent.parent

    return base_path / "resources" / relative_path


def get_app_root() -> Path:
    """Visszaadja az alkalmazás gyökérmappáját, ahol a results/ és macros/ mappák vannak.

    Returns:
        A mappa teljes elérési útja.

    Kontextus:
        - Exe-ként futtatva: az exe melletti mappa.
        - Fejlesztői futtatáskor: a projekt gyökere (src/).
    """
    if getattr(sys, "frozen", False):
        # Exe: az exe fizikai helye (nem az ideiglenes kicsomagolási mappa)
        return Path(sys.executable).resolve().parent
    # Fejlesztői futtatás: utils/paths.py → utils/ → src/
    return Path(__file__).resolve().parent.parent
