"""
ui/state.py — Az alkalmazás lehetséges állapotai

Az alkalmazás egy lineáris folyamatot követ:
  IDLE → TYPE_SELECTED → FILE_SELECTED → PROCESSING → SUCCESS
                                                     ↘ ERROR

Az aktuális állapotot az App osztály tárolja, és minden váltáskor
frissíti a felületet:
  - gombok engedélyezettség
  - súgó lépések kiemelése
  - eredményblokk láthatósága

ERROR esetén a felhasználó újra próbálkozhat (visszaesik FILE_SELECTED szintre).
"""

from enum import Enum, auto


class AppState(Enum):
    IDLE = auto()           # Kezdőállapot: semmi sincs kiválasztva
    TYPE_SELECTED = auto()  # Számlatípus kiválasztva, de PDF még nem
    FILE_SELECTED = auto()  # PDF is kiválasztva, feldolgozás indítható
    PROCESSING = auto()     # Feldolgozás folyamatban (a háttérben fut)
    SUCCESS = auto()        # Sikeres feldolgozás, Excel elkészült
    ERROR = auto()          # Hiba történt a feldolgozás során
