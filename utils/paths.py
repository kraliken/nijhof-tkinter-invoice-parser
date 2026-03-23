"""
utils/paths.py — Útvonal-segédfüggvények

Két különböző kontextusban kell az útvonalakat feloldani:
  1. Fejlesztői módban (python main.py): a fájlok a projekt könyvtárában vannak.
  2. PyInstaller onefile exe-ként: az exe egy temp mappába csomagolja ki magát
     (sys._MEIPASS), de az exe maga egy másik helyen fut.

Ez a modul kezeli ezt a kettősséget, hogy a többi kód ne foglalkozzon vele.

Összefoglalás:
  - get_resource_path() → bundled fájlokhoz (pl. app_icon.ico)
  - get_app_root()      → runtime adatokhoz (source/ és results/ mappák)
"""

import sys
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """Visszaadja egy bundled resource fájl abszolút útvonalát.

    Bundled resource: az alkalmazásba beépített statikus fájl (pl. az ikon),
    amelyet a PyInstaller a spec fájl `datas` listájában meghatározottak szerint
    csomagol be az exe-be.

    Args:
        relative_path: A resources/ mappán belüli relatív útvonal (pl. "app_icon.ico").

    Returns:
        Abszolút Path objektum a fájlhoz.

    Kontextus:
        - PyInstaller onefile futás: sys._MEIPASS az ideiglenes kicsomagolási mappa.
        - Dev futás: a projekt gyökere (invoice-parser/).
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller onefile: a kicsomagolt temp mappa tartalmazza a resource-okat
        base_path = Path(sys._MEIPASS)
    else:
        # Dev: utils/paths.py → utils/ → invoice-parser/
        base_path = Path(__file__).resolve().parent.parent

    return base_path / "resources" / relative_path


def get_app_root() -> Path:
    """Visszaadja az alkalmazás gyökérmappáját, ahol a source/ és results/ mappák vannak.

    Ez az exe melletti mappa (éles), ill. a projekt gyökere (dev).
    A results/ mappa ide kerül létrehozásra, és az input PDF-eket is
    innen olvassuk (ha az alkalmazás auto-detektálással működne).

    Returns:
        Abszolút Path objektum az alkalmazás gyökeréhez.

    Kontextus:
        - Frozen exe (sys.frozen=True): az exe mappája (pl. live/invoice-parser/).
        - Dev: a projekt gyökere (invoice-parser/).
    """
    if getattr(sys, "frozen", False):
        # PyInstaller onefile: az exe fizikai helye (nem a temp kicsomagolás)
        return Path(sys.executable).resolve().parent
    # Dev: utils/paths.py → utils/ → invoice-parser/
    return Path(__file__).resolve().parent.parent
