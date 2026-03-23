"""
core/multialarm.py — Multi Alarm PDF parser

Ez a modul kizárólag az adatkinyerési logikát tartalmazza.
Nem ír fájlt, nem nyit ablakot — tisztán funkcionális.

Bemenete: PDF fájl raw bájtjai (bytes)
Kimenete: List[Dict] — soronként egy jármű/időszak kombináció

A Multi Alarm számlák szövegalapú PDF-ek (nem táblázatos struktúra),
ezért az adatokat teljes szöveg kinyerésével + regex mintákkal olvassuk.

Egy sor (Dict) mezői:
    invoice_number    — számla azonosítója (pl. "12345")
    invoice_date      — számla kelte (YYYY.MM.DD)
    payment_due       — fizetési határidő (YYYY.MM.DD)
    performance_date  — teljesítési dátum (YYYY.MM.DD)
    period_start      — elszámolási időszak kezdete
    period_end        — elszámolási időszak vége
    license_plate     — rendszám (kötőjel és szóköz nélkül, pl. "ABC123")
    net               — nettó összeg (float, Ft-ban)
    vat_percent       — ÁFA mértéke (int, pl. 27)
    vat_amount        — ÁFA összege (float, Ft-ban)
"""

import io
import re
from typing import List, Dict

import pdfplumber


def process_multialarm(pdf_bytes: bytes) -> List[Dict]:
    """Kinyeri a strukturált adatokat egy Multi Alarm PDF számlából.

    Stratégia:
      1. Az összes oldal szövegét összefűzi egy nagy stringbe.
      2. Regex-szel megkeresi a fejléc adatokat (számla száma, dátumok).
      3. Párhuzamosan listázza a (időszak, rendszám, tételsor) hármasokat,
         majd összeilleszti őket index szerint.

    Args:
        pdf_bytes: A PDF fájl nyers bájtjai.

    Returns:
        Lista, amelynek minden eleme egy járműhöz/időszakhoz tartozó adatsor.
        Üres lista, ha a PDF nem értelmezhető.
    """
    full_text = ""

    # Az összes oldal szövegét összefűzzük — a Multialarm számla
    # szövegfolyamként van felépítve, nem táblázatokban.
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += "\n" + text

    # --- Fejléc adatok kinyerése (az egész számlán egységes) ---
    invoice_number = re.search(r"Számla száma:\s*(\d+)", full_text)
    invoice_date = re.search(r"Számla kelte:\s*([\d\.]+)", full_text)
    performance_date = re.search(r"Teljesítési dátum:\s*([\d\.]+)", full_text)
    payment_due = re.search(r"Fizetési határidő:\s*([\d\.]+)", full_text)

    # A dátumok végéről levágjuk a felesleges pontot (pl. "2024.01.15." → "2024.01.15")
    header_info = {
        "invoice_number": invoice_number.group(1) if invoice_number else "",
        "invoice_date": invoice_date.group(1).rstrip(".") if invoice_date else "",
        "payment_due": payment_due.group(1).rstrip(".") if payment_due else "",
        "performance_date": (
            performance_date.group(1).rstrip(".") if performance_date else ""
        ),
    }

    # --- Sorspecifikus minták (egy sor = egy jármű + időszak) ---
    period_pattern = r"Időszak:\s*([\d\.]+ - [\d\.]+)"
    license_plate_pattern = r"Felszerelési hely:\s+(\S+)"
    # A tételsor a "Menetlevél + útdíj alapszolgáltatás" szöveggel kezdődik,
    # és az összes összeg ugyanazon a sorban szerepel.
    line_pattern = r"Menetlevél \+ útdíj alapszolgáltatás[^\n]+"

    lines = re.findall(line_pattern, full_text)
    periods = re.findall(period_pattern, full_text)
    license_plates = re.findall(license_plate_pattern, full_text)

    # Csak annyit dolgozunk fel, amennyi mindhárom listából megvan —
    # hiányos sorok kihagyása helyett biztonságos csonkítás.
    min_len = min(len(periods), len(license_plates), len(lines))
    data: List[Dict] = []

    for i in range(min_len):
        line = lines[i]

        # Összegek kinyerése a tételsorból: pl. "12 345,67Ft"
        # amounts[0] = egységár, [1] = nettó, [2] = ÁFA összeg, [3] = bruttó
        amounts = re.findall(r"(\d{1,3}(?: \d{3})*,\d{2})Ft", line)
        vat_percent = re.search(r"(\d{1,2})\s?%", line)

        if len(amounts) >= 4 and vat_percent:
            # "12 345,67" → 12345.67 (magyar → Python float formátum)
            net = float(amounts[1].replace(" ", "").replace(",", "."))
            vat = int(vat_percent.group(1))
            vat_amount = float(amounts[2].replace(" ", "").replace(",", "."))

            period_start, period_end = [p.strip() for p in periods[i].split(" - ")]
            # Rendszám normalizálása: szóköz és kötőjel eltávolítása
            license_plate = license_plates[i].replace(" ", "").replace("-", "")

            row = {
                **header_info,
                "period_start": period_start,
                "period_end": period_end,
                "license_plate": license_plate,
                "net": net,
                "vat_percent": vat,
                "vat_amount": vat_amount,
            }
            data.append(row)

    return data
