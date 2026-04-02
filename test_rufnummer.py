#!/usr/bin/env python3
# coding: utf-8
"""
test_rufnummer.py – Automatisierter Test der Rufnummern-Segmentierung
======================================================================
Strategie:
  1. Bekannte Nummern aus der Vorwahltabelle zufällig auswählen
  2. Für jede Nummer eine "Kontrollnummer" (E.164-Form) berechnen
  3. Diese Kontrollnummer zufällig mit Trennzeichen, Leerzeichen,
     verschiedenen Präfix-Formaten "verschmutzen"
  4. Parser aufrufen und prüfen ob land/ortsnetz/rufnummer stimmen
  5. 10.000 Durchläufe, Statistik am Ende ausgeben
"""

import random
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from rufnummer import parse_rufnummer
from vorwahlen import ALLE_VORWAHLEN

# ---------------------------------------------------------------------------
# Nummern-Generator
# ---------------------------------------------------------------------------

# Alle Vorwahlen die realistisch lange Rufnummern erlauben
# (Sonderrufnummern wie 110, 112 etc. ausschließen – diese haben keine
#  klassische Teilnehmernummer dahinter)
KURZNUMMERN = {"10", "110", "112", "115", "116000", "116006", "116111",
               "116116", "116117", "116123", "116124", "118", "11800",
               "11811", "11833", "11880", "11882", "11890", "191"}

# Nur Vorwahlen verwenden, die KEIN Präfix einer längeren Vorwahl in der
# Tabelle sind. Sonst würde der longest-prefix-match korrekt die längere
# Vorwahl liefern, während der Test die kürzere erwartet.
_alle_keys = set(ALLE_VORWAHLEN.keys())
TESTVORWAHLEN = [
    v for v in _alle_keys
    if v not in KURZNUMMERN
    and len(v) <= 5
    and not any(k.startswith(v) and k != v for k in _alle_keys)
]


def zufaellige_rufnummer(vorwahl: str) -> str:
    """Erzeugt eine plausible Teilnehmernummer passend zur Vorwahl-Länge."""
    # In Deutschland gilt: Vorwahl + Teilnehmernummer = max 11 Stellen (ohne 0-Präfix)
    # Vorwahl 2-stellig → Teilnehmernummer 6-8 Stellen
    # Vorwahl 5-stellig → Teilnehmernummer 2-4 Stellen
    max_gesamt = 11  # nationale Länge ohne führende 0
    min_tn = 2
    max_tn = max(min_tn, max_gesamt - len(vorwahl))
    laenge = random.randint(min_tn, min(max_tn, 8))
    # Erste Ziffer nicht 0 (würde als weitere Vorwahl-0 fehlinterpretiert)
    erste = str(random.randint(1, 9))
    rest = "".join(str(random.randint(0, 9)) for _ in range(laenge - 1))
    return erste + rest


def zufaelliges_format(vorwahl: str, rufnummer: str) -> tuple[str, str]:
    """
    Erzeugt eine zufällig formatierte Darstellung von +49<vorwahl><rufnummer>.
    Rückgabe: (formatierte_nummer, erwartetes_format_name)
    """
    # Mögliche Präfix-Stile
    praefixe = [
        (f"+49{vorwahl}{rufnummer}",        "E164_kompakt"),
        (f"+490{vorwahl}{rufnummer}",        "E164_plus_null"),   # Fehlerfall: +49 0 Vorwahl
        (f"0049{vorwahl}{rufnummer}",        "IDD_kompakt"),
        (f"00490{vorwahl}{rufnummer}",       "IDD_plus_null"),
        (f"49{vorwahl}{rufnummer}",          "ohne_praefix"),     # 49 ohne + oder 00
        (f"0{vorwahl}{rufnummer}",           "national"),
        (f"049{vorwahl}{rufnummer}",         "tippfehler_049"),   # Tippfehler
    ]
    praefix_raw, stil = random.choice(praefixe)

    # Zerlege die Ziffernfolge an zufälligen Stellen mit Trennzeichen
    trennzeichen = [" ", "-", "/", ".", " - ", " / "]

    # Baue eine formatierte Version
    # Strategie: zerlege in sinnvolle Gruppen (Ländervorwahl | Ortsnetz | Rufnummer)
    # mit zufälligen Trennzeichen und optionalen Klammern
    sep1 = random.choice(trennzeichen)
    sep2 = random.choice(trennzeichen)

    # Basisformat: Präfix + sep + Ortsnetz-Darstellung + sep + Rufnummer
    if stil in ("E164_kompakt", "E164_plus_null", "IDD_kompakt", "IDD_plus_null", "ohne_praefix", "tippfehler_049"):
        # Trenne Ländervorwahl vom Rest
        if stil == "E164_kompakt":
            land_part = "+49"
            rest_part = f"0{vorwahl}" if random.random() < 0.3 else vorwahl
        elif stil == "E164_plus_null":
            land_part = "+49"
            rest_part = f"0{vorwahl}"
        elif stil == "IDD_kompakt":
            land_part = "0049"
            rest_part = f"0{vorwahl}" if random.random() < 0.3 else vorwahl
        elif stil == "IDD_plus_null":
            land_part = "0049"
            rest_part = f"0{vorwahl}"
        elif stil == "ohne_praefix":
            land_part = "49"
            rest_part = f"0{vorwahl}" if random.random() < 0.3 else vorwahl
        else:  # tippfehler_049
            land_part = "049"
            rest_part = vorwahl

        # Zufällig Klammern um Ortsnetz
        use_brackets = random.random() < 0.25
        if use_brackets:
            ov_str = f"({rest_part})"
        else:
            ov_str = rest_part

        # Zufällig Trennzeichen in der Rufnummer
        rn = rufnummer
        if len(rn) >= 4 and random.random() < 0.4:
            split_pos = random.randint(2, len(rn) - 2)
            sep3 = random.choice(trennzeichen)
            rn = rn[:split_pos] + sep3 + rn[split_pos:]

        if use_brackets:
            formatiert = f"{land_part}{ov_str}{sep2}{rn}"
        else:
            formatiert = f"{land_part}{sep1}{ov_str}{sep2}{rn}"

    else:
        # national: 0 + Vorwahl + Rufnummer
        use_brackets = random.random() < 0.2
        ov_str = f"(0{vorwahl})" if use_brackets else f"0{vorwahl}"
        rn = rufnummer
        if len(rn) >= 4 and random.random() < 0.4:
            split_pos = random.randint(2, len(rn) - 2)
            sep3 = random.choice(trennzeichen)
            rn = rn[:split_pos] + sep3 + rn[split_pos:]
        if use_brackets:
            formatiert = f"{ov_str}{sep2}{rn}"
        else:
            formatiert = f"{ov_str}{sep2}{rn}"

    return formatiert, stil


# ---------------------------------------------------------------------------
# Testlauf
# ---------------------------------------------------------------------------

def run_tests(n: int = 10000, seed: int = 42) -> None:
    random.seed(seed)

    ok = 0
    fehler_detail: dict[str, int] = {}
    stile_ok: dict[str, int] = {}
    stile_fehler: dict[str, int] = {}

    # Sonderfälle aus der Anforderung (immer testen)
    fixe_faelle = [
        ("+4917912345678",    "+49", "0179", None),
        ("+49017912345678",   "+49", "0179", None),
        ("004906171653215",   "+49", "06171", None),
        ("0049 069 123589",   "+49", "069",  None),
        ("+49 69 123-12",     "+49", "069",  None),
        ("+49 (069)12256-15", "+49", "069",  None),
        ("03012256/15",       "+49", "030",  None),
        # 49 ohne + oder 00
        ("4969123456",        "+49", "069",  None),
        ("49 30 12345678",    "+49", "030",  None),
        # Tippfehler mit +
        ("+049 69 123456",    "+49", "069", None), # +049 → Tippfehler für +49
        ("+0049 30 12345",    "+49", "030", None), # +0049 → Tippfehler (+00 statt 00)
        ("+00 49 30 12345",   "+49", "030", None), # +00 49 → Tippfehler
        # Ohne +
        ("049 69 123456",     "+49", "069", None), # Tippfehler 049 (kein Leerzeichen zu Ortsnetz)
        # Fehler-/Sonderfälle → None erwartet
        ("000123456",         None, None, None),   # PBX-Amtsvorwahl
        ("+44 20 7946 0958",  None, None, None),   # Ausland
        ("abc",               None, None, None),   # kein Sinn
        ("x",                 None, None, None),   # einzelne Buchstabe
    ]

    print(f"Starte Test mit {n:,} zufälligen Nummern + {len(fixe_faelle)} Fixfällen...\n")

    # ── Fixe Fälle ──────────────────────────────────────────────────────────
    fix_ok = 0
    fix_fehler = 0
    for raw, erw_land, erw_ov, _ in fixe_faelle:
        res = parse_rufnummer(raw)
        if erw_land is None:
            # Fehler erwartet
            if res is None:
                fix_ok += 1
            else:
                fix_fehler += 1
                print(f"  [FEHLER Fixfall] '{raw}' → erwartet None, got {res}")
        else:
            if res and res["land"] == erw_land and res["ortsnetz"] == erw_ov:
                fix_ok += 1
            else:
                fix_fehler += 1
                print(f"  [FEHLER Fixfall] '{raw}' → erwartet land={erw_land} ov={erw_ov}, got {res}")

    print(f"Fixfälle: {fix_ok}/{len(fixe_faelle)} OK\n")

    # ── Zufällige Nummern ───────────────────────────────────────────────────
    for _ in range(n):
        vorwahl = random.choice(TESTVORWAHLEN)
        rufnummer = zufaellige_rufnummer(vorwahl)
        formatiert, stil = zufaelliges_format(vorwahl, rufnummer)

        erw_ov = "0" + vorwahl

        # Für die Tippfehler-Variante "049..." ist das Ergebnis abhängig davon,
        # ob die Vorwahl nach Abzug von "049" erkannt wird → als "erwartet OK" zählen
        res = parse_rufnummer(formatiert)

        if res and res["land"] == "+49" and res["ortsnetz"] == erw_ov and res["rufnummer"] == rufnummer:
            ok += 1
            stile_ok[stil] = stile_ok.get(stil, 0) + 1
        else:
            fehlergrund = res["fehler"] if (res and "fehler" in res) else ("falsch" if res else "None")
            fehler_detail[fehlergrund] = fehler_detail.get(fehlergrund, 0) + 1
            stile_fehler[stil] = stile_fehler.get(stil, 0) + 1
            # Erste 5 Fehler im Detail ausgeben
            if sum(fehler_detail.values()) <= 5:
                print(f"  [DBG] '{formatiert}' | erw: ov={erw_ov} rn={rufnummer} | got: {res}")

    # ── Ergebnis ────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"ERGEBNIS: {ok:,}/{n:,} korrekt  ({100*ok/n:.2f}%)")
    fehlgesamt = n - ok
    if fehlgesamt:
        print(f"\nFehler nach Grund ({fehlgesamt} gesamt):")
        for g, c in sorted(fehler_detail.items(), key=lambda x: -x[1]):
            print(f"  {g:30s}: {c:5d}")
        print(f"\nFehler nach Format-Stil:")
        for s, c in sorted(stile_fehler.items(), key=lambda x: -x[1]):
            gesamt_s = stile_ok.get(s, 0) + c
            print(f"  {s:25s}: {c:5d} Fehler von {gesamt_s:5d}  ({100*c/gesamt_s:.1f}%)")
    print(f"\nErfolge nach Format-Stil:")
    alle_stile = set(stile_ok) | set(stile_fehler)
    for s in sorted(alle_stile):
        o = stile_ok.get(s, 0)
        f = stile_fehler.get(s, 0)
        gesamt_s = o + f
        print(f"  {s:25s}: {o:5d}/{gesamt_s:5d}  ({100*o/gesamt_s:.1f}%)")
    print("=" * 60)


if __name__ == "__main__":
    run_tests(10000)
