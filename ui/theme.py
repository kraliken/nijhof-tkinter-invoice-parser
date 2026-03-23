"""
ui/theme.py — Vizuális konstansok

Az összes szín és térköz egy helyen van definiálva,
így könnyű az egységes megjelenést fenntartani.

Kártyák (számlatípus választó):
  - CARD_IDLE:     alapállapot (szürke háttér)
  - CARD_SELECTED: kiválasztott típus (kék keret és szöveg, Google kék: #1A73E8)

Visszajelző dobozok:
  - ERROR:   piros árnyalat (Bootstrap "danger" alapján)
  - SUCCESS: zöld árnyalat (Bootstrap "success" alapján)
"""

# Szekciók közötti padding (px) — az összes LabelFrame-nél egységesen
SECTION_PAD = 8

# Számlatípus kártya megjelenése
CARD_IDLE = {"bg": "#F5F5F5", "border": "#CCCCCC", "fg": "black", "sub": "gray"}
CARD_SELECTED = {"bg": "#EBF4FF", "border": "#1A73E8", "fg": "#1A73E8", "sub": "#1A73E8"}

# Hiba visszajelző doboz
ERROR_BG = "#F8D7DA"
ERROR_FG = "#721C24"

# Sikeres feldolgozás visszajelző doboz
SUCCESS_BG = "#D4EDDA"
SUCCESS_FG = "#155724"
