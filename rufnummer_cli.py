#!/usr/bin/env python3
# coding: utf-8
"""
rufnummer_cli.py – Kommandozeilen-Interface zur Rufnummern-Segmentierung
"""

from rufnummer import parse_rufnummer


def main():
    print("Rufnummern-Analyse (Deutsche Nummern)")
    print("=" * 40)
    while True:
        try:
            raw = input("Bitte Rufnummer (oder x zum Beenden): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if raw.lower() == "x":
            break

        if not raw:
            continue

        result = parse_rufnummer(raw)
        if result:
            print(f"  Int. Vorwahl: {result['land']}")
            print(f"  Ortsnetz:     {result['ortsnetz']}  ({result['bezeichnung']})")
            print(f"  Rufnummer:    {result['rufnummer']}")
        else:
            print(f"  Keine deutsche Rufnummer erkannt: {raw}")
        print()


if __name__ == "__main__":
    main()
