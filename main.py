"""
main.py — Belépési pont (entry point)

Futtatás:
    python main.py

Feladata:
    1. Beállítja a mappaszerkezetet, hogy a többi fájl (core, ui, stb.)
       egymást megtalálják, bárhonnan indítjuk el a scriptet.
    2. Elindítja a Tkinter alapú GUI alkalmazást (App).
    3. Naplózza az indítást és leállítást az app.log fájlba.

Megjegyzés: ez a fájl csak akkor fut le, ha közvetlenül indítják el
(`python main.py`), nem ha egy másik fájl hivatkozik rá.
"""

import sys
from pathlib import Path

# Megadjuk a projekt gyökerének helyét, hogy a többi mappa
# (ui, core, services, utils) megtalálható legyen, bárhonnan futtatják a scriptet.
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ui.main_window import App
from utils.logger import get_logger

if __name__ == "__main__":
    log = get_logger()
    log.info("Alkalmazás indítása")
    app = App()
    app.run()  # Megnyitja az ablakot és vár, amíg a felhasználó be nem zárja
    log.info("Alkalmazás leállítva")
