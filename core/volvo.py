"""
core/volvo.py — Volvo Hungaria PDF parser

Ez a modul kizárólag az adatkinyerési logikát tartalmazza.
Nem ír fájlt, nem nyit ablakot — tisztán funkcionális.

Bemenete: PDF fájl raw bájtjai (bytes)
Kimenete: List[Dict] — soronként egy jármű/időszak kombináció

A Volvo számlák táblázat-alapú PDF-ek, ezért pdfplumber `extract_tables()`
metódusát használjuk (nem szöveg-kinyerést mint a Multialarm-nál).

PDF struktúra:
  - 1. oldal: fejléc adatok
      - 1. táblázat [0][1][0]: számlaszám
      - szövegből: az első sor ahol 3 dátum (DD-MM-YYYY) egymás mellett szerepel
        → invoice_date, payment_due, performance_date sorrendben
  - Minden oldal: 2. táblázat (index 1) tartalmazza a tételsorokat
      - Egy sor = egy jármű + időszak
      - Rendszám: a cella sortörés utáni részéből kinyerhető, az első dátum előtt
      - Összegek: "1.234,56" formátumban (ponttal mint ezreselválasztó!)

Egy sor (Dict) mezői:
    invoice_number    — számlaszám
    invoice_date      — számla kelte (DD-MM-YYYY)
    payment_due       — fizetési határidő (DD-MM-YYYY)
    performance_date  — teljesítési dátum (DD-MM-YYYY)
    period_start      — elszámolási időszak kezdete
    period_end        — elszámolási időszak vége
    license_plate     — rendszám (kötőjel és szóköz nélkül)
    net               — nettó összeg (float, Ft-ban)

Megjegyzés: ÁFA nem szerepel a PDF-ben, azt az Excel exportnál számítjuk (27%).
"""

import io
import re
from typing import List, Dict

import pdfplumber


def process_volvo(pdf_bytes: bytes) -> List[Dict]:
    """Kinyeri a strukturált adatokat egy Volvo Hungaria PDF számlából.

    Stratégia:
      1. Az első oldalból kinyeri a fejléc adatokat (számlaszám, dátumok).
      2. Az összes oldalon végigmegy, és a 2. táblázatból (index 1)
         soronként kinyeri a jármű/időszak adatokat.

    Args:
        pdf_bytes: A PDF fájl nyers bájtjai.

    Returns:
        Lista, amelynek minden eleme egy járműhöz/időszakhoz tartozó adatsor.
        Üres lista, ha a PDF nem értelmezhető.
    """
    data: List[Dict] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        if not pdf.pages:
            return data

        first_page = pdf.pages[0]
        first_page_text = first_page.extract_text() or ""
        first_tables = first_page.extract_tables() or []

        # --- Számlaszám kinyerése az első oldal első táblázatából ---
        # Struktúra: tables[0] = fejléc táblázat, [1] = második sor, [0] = első cella
        invoice_number = ""
        if first_tables and len(first_tables[0]) >= 2:
            row = first_tables[0][1]
            if row and len(row) >= 1 and row[0]:
                invoice_number = str(row[0]).strip()

        # --- Dátumok kinyerése az első oldal szövegéből ---
        # Az első sor keresése, amelyen egyszerre 3 "DD-MM-YYYY" formátumú dátum szerepel.
        # A sorrend mindig: számla kelte, fizetési határidő, teljesítési dátum.
        invoice_date = ""
        payment_due = ""
        performance_date = ""
        for line in first_page_text.splitlines():
            dates = re.findall(r"\d{2}-\d{2}-\d{4}", line)
            if len(dates) >= 3:
                invoice_date, payment_due, performance_date = dates[:3]
                break

        # Fejléc: minden tételsorhoz hozzáfűzzük (spread operátorral)
        header_info = {
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "payment_due": payment_due,
            "performance_date": performance_date,
        }

        # --- Tételsorok kinyerése (minden oldal, 2. táblázat) ---
        for page in pdf.pages:
            tables = page.extract_tables() or []
            # Egy oldal csak akkor tartalmaz tételsorokat, ha van legalább 2 táblázata
            if len(tables) < 2:
                continue

            table = tables[1]  # Az index=1 táblázat tartalmazza a tételeket
            for row in table:
                if not row:
                    continue

                # None cellák kiszűrése az összefűzés előtt
                safe_cells = [c for c in row if c is not None]
                if not safe_cells:
                    continue

                # flat_row: sortörések nélküli összefűzött szöveg (dátumok, összegek kereséséhez)
                flat_row = " ".join(str(c) for c in safe_cells).replace("\n", " ")
                # row_with_breaks: sortöréseket megtartjuk (rendszám kinyeréséhez szükséges)
                row_with_breaks = " ".join(str(c) for c in safe_cells).split("\n")

                # --- Rendszám kinyerése ---
                # A rendszám a cella sortörés utáni részében van, az első dátum előtt.
                # Példa cella tartalom: "Valami leírás\nABC123 01-01-2024 ..."
                license_plate = ""
                if len(row_with_breaks) > 1:
                    after_newline = row_with_breaks[1]
                    match = re.search(r"(.+?)\s*\d{2}-\d{2}-\d{4}", after_newline)
                    if match:
                        raw_license = match.group(1)
                        # Normalizálás: kötőjel és szóköz eltávolítása
                        license_plate = (
                            raw_license.replace(" ", "").replace("-", "").strip()
                        )

                # --- Időszak dátumai (flat_row-ból) ---
                dates = re.findall(r"\d{2}-\d{2}-\d{4}", flat_row)
                period_start = dates[0] if len(dates) > 0 else ""
                period_end = dates[1] if len(dates) > 1 else ""

                # --- Nettó összeg kinyerése ---
                # Formátum: "1.234,56" (pont = ezreselválasztó, vessző = tizedesjel)
                # Az utolsó összeg a sorban a nettó érték.
                amounts = re.findall(r"\d{1,3}(?:\.\d{3})*,\d{2}", flat_row)
                amount = amounts[-1] if amounts else ""

                # Csak teljes sorokat veszünk fel (rendszám + időszak + összeg megvan)
                if period_start and license_plate and period_end and amount:
                    net_value = amount
                    try:
                        # "1.234,56" → 1234.56 (python float)
                        net_value = float(amount.replace(".", "").replace(",", "."))
                    except Exception:
                        net_value = amount  # Ha a konverzió nem sikerül, string marad

                    data.append(
                        {
                            **header_info,
                            "period_start": period_start,
                            "period_end": period_end,
                            "license_plate": license_plate,
                            "net": net_value,
                        }
                    )

    return data
