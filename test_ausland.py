#!/usr/bin/env python3
# coding: utf-8
"""
test_ausland.py – Test der Nicht-Erkennungsrate für ausländische Rufnummern
===========================================================================
Strategie:
  1. Zufällige europäische Rufnummern erzeugen (ohne Deutschland +49)
  2. In verschiedenen Formaten "verschmutzen" (Trennzeichen, Leerzeichen etc.)
  3. Parser aufrufen: Erwartetes Ergebnis ist immer None (keine deutsche Nummer)
  4. 10.000 Durchläufe, Statistik nach Land und Format
"""

import random
import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from rufnummer import parse_rufnummer

# ---------------------------------------------------------------------------
# Europäische Ländervorwahlen mit typischer NSN-Länge (Ziffern nach Ländercode)
# Quelle: ITU-T E.164, Wikipedia
# ---------------------------------------------------------------------------
EUROPAEISCHE_LAENDER = {
    "30":  {"name": "Griechenland",         "min": 10, "max": 10},
    "31":  {"name": "Niederlande",           "min":  9, "max":  9},
    "32":  {"name": "Belgien",               "min":  9, "max": 10},
    "33":  {"name": "Frankreich",            "min":  9, "max":  9},
    "34":  {"name": "Spanien",               "min":  9, "max":  9},
    "36":  {"name": "Ungarn",                "min":  9, "max":  9},
    "39":  {"name": "Italien",               "min":  6, "max": 11},
    "40":  {"name": "Rumänien",              "min":  9, "max": 10},
    "41":  {"name": "Schweiz",               "min":  9, "max":  9},
    "43":  {"name": "Österreich",            "min":  4, "max": 13},
    "44":  {"name": "Großbritannien",        "min":  9, "max": 11},
    "45":  {"name": "Dänemark",              "min":  8, "max":  8},
    "46":  {"name": "Schweden",              "min":  7, "max":  9},
    "47":  {"name": "Norwegen",              "min":  8, "max":  8},
    "48":  {"name": "Polen",                 "min":  9, "max":  9},
    "350": {"name": "Gibraltar",             "min":  8, "max":  8},
    "351": {"name": "Portugal",              "min":  9, "max":  9},
    "352": {"name": "Luxemburg",             "min":  6, "max":  9},
    "353": {"name": "Irland",                "min":  7, "max":  9},
    "354": {"name": "Island",                "min":  7, "max":  7},
    "355": {"name": "Albanien",              "min":  8, "max":  9},
    "356": {"name": "Malta",                 "min":  8, "max":  8},
    "357": {"name": "Zypern",               "min":  8, "max":  8},
    "358": {"name": "Finnland",              "min":  6, "max": 10},
    "359": {"name": "Bulgarien",             "min":  8, "max":  9},
    "370": {"name": "Litauen",               "min":  8, "max":  9},
    "371": {"name": "Lettland",              "min":  8, "max":  8},
    "372": {"name": "Estland",               "min":  7, "max":  8},
    "373": {"name": "Moldau",                "min":  8, "max":  8},
    "374": {"name": "Armenien",              "min":  8, "max":  8},
    "375": {"name": "Belarus",               "min":  9, "max":  9},
    "376": {"name": "Andorra",               "min":  6, "max":  6},
    "377": {"name": "Monaco",                "min":  8, "max":  8},
    "378": {"name": "San Marino",            "min":  6, "max": 10},
    "380": {"name": "Ukraine",               "min":  9, "max":  9},
    "381": {"name": "Serbien",               "min":  8, "max": 10},
    "382": {"name": "Montenegro",            "min":  8, "max":  9},
    "383": {"name": "Kosovo",                "min":  8, "max":  9},
    "385": {"name": "Kroatien",              "min":  8, "max":  9},
    "386": {"name": "Slowenien",             "min":  8, "max":  9},
    "387": {"name": "Bosnien-Herzegowina",   "min":  8, "max":  9},
    "389": {"name": "Nordmazedonien",        "min":  8, "max":  9},
    "420": {"name": "Tschechien",            "min":  9, "max":  9},
    "421": {"name": "Slowakei",              "min":  9, "max":  9},
    "423": {"name": "Liechtenstein",         "min":  7, "max":  9},
    "7":   {"name": "Russland",              "min": 10, "max": 10},
}

# ---------------------------------------------------------------------------
# Nummern- und Format-Generator
# ---------------------------------------------------------------------------

def zufaellige_nsn(cc: str) -> str:
    """Erzeugt eine zufällige NSN (national significant number) für das Land."""
    info = EUROPAEISCHE_LAENDER[cc]
    laenge = random.randint(info["min"], info["max"])
    # Erste Ziffer nicht 0 (würde ggf. als Ortsnetz-Präfix fehlinterpretiert)
    erste = str(random.randint(1, 9))
    rest = "".join(str(random.randint(0, 9)) for _ in range(laenge - 1))
    return erste + rest


def zufaelliges_format(cc: str, nsn: str) -> tuple[str, str]:
    """
    Erzeugt eine zufällig formatierte Darstellung von +<cc><nsn>.
    Rückgabe: (formatierte_nummer, stil_name)
    """
    sep_varianten = [" ", "-", "/", ".", " - ", " / "]
    s1 = random.choice(sep_varianten)
    s2 = random.choice(sep_varianten)

    # NSN ggf. in 2-3 Teile aufteilen
    def split_nsn(n):
        if len(n) >= 6 and random.random() < 0.5:
            p1 = random.randint(2, len(n) - 3)
            p2 = random.randint(p1 + 1, len(n) - 1)
            sep = random.choice(sep_varianten)
            sep2 = random.choice(sep_varianten)
            return n[:p1] + sep + n[p1:p2] + sep2 + n[p2:]
        elif len(n) >= 4 and random.random() < 0.4:
            p = random.randint(2, len(n) - 2)
            return n[:p] + random.choice(sep_varianten) + n[p:]
        return n

    nsn_fmt = split_nsn(nsn)
    use_brackets = random.random() < 0.15

    stil = random.choice([
        "plus",        # +CC NSN
        "idd",         # 00CC NSN
        "idd_sep",     # 00 CC NSN (mit Trennzeichen)
    ])

    if stil == "plus":
        if use_brackets:
            result = f"+{cc}{s1}({nsn_fmt})"
        else:
            result = f"+{cc}{s1}{nsn_fmt}"
    elif stil == "idd":
        result = f"00{cc}{s1}{nsn_fmt}"
    else:  # idd_sep
        result = f"00{s1}{cc}{s2}{nsn_fmt}"

    return result, stil


# ---------------------------------------------------------------------------
# Testlauf
# ---------------------------------------------------------------------------

def run_tests(n: int = 10000, seed: int = 42) -> None:
    random.seed(seed)

    ok = 0           # korrekt als Nicht-DE erkannt (None)
    falsch_positiv = 0  # fälschlich als DE erkannt
    fp_detail: dict[str, int] = {}   # Ländername → Anzahl FP
    fp_stile: dict[str, int] = {}    # Stil → Anzahl FP
    fp_beispiele: list = []

    laender_keys = list(EUROPAEISCHE_LAENDER.keys())

    print(f"Starte Ausland-Test mit {n:,} zufälligen europäischen Nummern...\n")

    for _ in range(n):
        cc = random.choice(laender_keys)
        nsn = zufaellige_nsn(cc)
        formatiert, stil = zufaelliges_format(cc, nsn)

        res = parse_rufnummer(formatiert)

        if res is None:
            ok += 1
        else:
            falsch_positiv += 1
            land_name = EUROPAEISCHE_LAENDER[cc]["name"]
            fp_detail[land_name] = fp_detail.get(land_name, 0) + 1
            fp_stile[stil] = fp_stile.get(stil, 0) + 1
            if len(fp_beispiele) < 20:
                fp_beispiele.append((formatiert, cc, nsn, res))

    # ── Ausgabe ─────────────────────────────────────────────────────────────
    print("=" * 65)
    print(f"ERGEBNIS: {ok:,}/{n:,} korrekt als Ausland erkannt  ({100*ok/n:.2f}%)")
    print(f"          {falsch_positiv:,} Falsch-Positive (fälschlich als DE erkannt)")

    if falsch_positiv:
        print(f"\nFalsch-Positive nach Land ({falsch_positiv} gesamt):")
        for land, c in sorted(fp_detail.items(), key=lambda x: -x[1]):
            print(f"  {land:30s}: {c:4d}")
        print(f"\nFalsch-Positive nach Format-Stil:")
        for s, c in sorted(fp_stile.items(), key=lambda x: -x[1]):
            print(f"  {s:15s}: {c:4d}")
        print(f"\nBeispiele (max. 20):")
        for fmt, cc, nsn, res in fp_beispiele:
            print(f"  {repr(fmt):45s}  CC={cc}  NSN={nsn}")
            print(f"    → {res}")
    print("=" * 65)


if __name__ == "__main__":
    run_tests(10000)
