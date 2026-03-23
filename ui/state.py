"""
ui/state.py — Alkalmazás állapotgép (state machine)

Az alkalmazás egy lineáris folyamatot követ:
  IDLE → TYPE_SELECTED → FILE_SELECTED → PROCESSING → SUCCESS
                                                     ↘ ERROR

Az AppState enum értékét az App osztály tárolja (`self.state`),
és minden állapotváltáskor (`set_state()`) frissíti a GUI elemeket:
  - gomb engedélyezettség
  - súgó lépések kiemelése
  - eredményblokk láthatósága

ERROR esetén a felhasználó újra próbálkozhat (visszaesik FILE_SELECTED szintre).
"""

from enum import Enum, auto


class AppState(Enum):
    IDLE = auto()           # Kezdőállapot: semmi sincs kiválasztva
    TYPE_SELECTED = auto()  # Számlatípus kiválasztva, de PDF még nem
    FILE_SELECTED = auto()  # PDF is kiválasztva, feldolgozás indítható
    PROCESSING = auto()     # Feldolgozás folyamatban (háttérszál fut)
    SUCCESS = auto()        # Sikeres feldolgozás, Excel elkészült
    ERROR = auto()          # Hiba történt a feldolgozás során
