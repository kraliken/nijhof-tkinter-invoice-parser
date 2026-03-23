"""
main.py — Belépési pont (entry point)

Futtatás:
    python main.py

Feladata:
    1. Gondoskodik arról, hogy a projekt gyökere (invoice-parser/) benne legyen
       a Python importálási útban (sys.path), így az összes csomag (core, ui, stb.)
       elérhető relatív importtal, bárhonnan futtatjuk a scriptet.
    2. Elindítja a Tkinter alapú GUI alkalmazást (App).
    3. Naplózza az indítást és leállítást az app.log fájlba.

Megjegyzés: ez a fájl csak akkor fut le, ha közvetlenül hívják meg
(`python main.py`), nem ha importálják — ezt a `if __name__ == "__main__":`
feltétel biztosítja.
"""

import sys
from pathlib import Path

# Hozzáadjuk a projekt gyökerét a Python keresési útjához,
# hogy az `ui`, `core`, `services`, `utils` csomagok importálhatók legyenek
# függetlenül attól, hogy melyik könyvtárból futtatják a scriptet.
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ui.main_window import App
from utils.logger import get_logger

if __name__ == "__main__":
    log = get_logger()
    log.info("Alkalmazás indítása")
    app = App()
    app.run()  # Tkinter event loop — blokkol, amíg az ablakot be nem zárják
    log.info("Alkalmazás leállítva")
