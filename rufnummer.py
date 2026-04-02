"""
rufnummer.py – Deutsche Rufnummern-Segmentierung
=================================================
Reusable component: from rufnummer import parse_rufnummer

Rückgabe bei Erfolg:
    {
        "land":      "+49",
        "ortsnetz":  "069",    # mit führender 0
        "rufnummer": "983162",
        "bezeichnung": "Frankfurt am Main"  # aus Vorwahltabelle
    }

Rückgabe bei Fehler / keine deutsche Nummer:
    None  oder  {"fehler": "<grund>"}  (je nach strict-Parameter)
"""

import re
from vorwahlen import ALLE_VORWAHLEN

# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _nur_ziffern(s: str) -> str:
    """Entfernt alle Nicht-Ziffern aus einem String."""
    return re.sub(r"[^\d]", "", s)


def _tokens(s: str) -> list[str]:
    """Zerlegt einen String an typischen Trennzeichen in Zifferngruppen."""
    parts = re.split(r"[\s\(\)\-\/\\\.\,]+", s.strip())
    return [_nur_ziffern(p) for p in parts if _nur_ziffern(p)]


def _match_vorwahl(national: str) -> tuple[str, str, str] | tuple[None, None, None]:
    """
    Sucht die längste passende Vorwahl in ALLE_VORWAHLEN.
    national: Ziffernfolge OHNE führende 0 (z.B. "6912312")
    Rückgabe: (ortsnetz_ohne_0, rufnummer, bezeichnung) oder (None, None, None)
    """
    for laenge in (6, 5, 4, 3, 2):
        kandidat = national[:laenge]
        if kandidat in ALLE_VORWAHLEN:
            rufnummer = national[laenge:]
            return kandidat, rufnummer, ALLE_VORWAHLEN[kandidat]
    return None, None, None


def _extrahiere_national(digits: str, raw_starts_with_plus: bool) -> tuple[str | None, str | None]:
    """
    Extrahiert das nationale Rufnummernteil (ohne Länderkennzahl, ohne führende 0).

    Behandelte Fälle:
      +0049...  → Tippfehler (+00 statt +): wie 0049
      +00...    → Tippfehler (+00 statt 00): strips +, dann wie 00xx
      +049...   → Tippfehler (+ vor 049): internationale Absicht → wie 0049
      +49...    → Standard E.164 Deutschland
      0049...   → Standard IDD Deutschland
      049...    → ambig (national 049x ODER Tippfehler 0049);
                  Grundinterpretation hier: national (0 + 49x-Vorwahl).
                  try-both in parse_rufnummer() löst Ambiguität auf.
      49...     → 49 ohne Präfix (behandelt als +49)
      0...      → nationales Format

    Rückgabe: (national, fehlergrund) – genau eines davon ist None.
    """
    # Tippfehler: "+" gefolgt von "00..." → "+" ignorieren, dann 00xx-Logik
    if raw_starts_with_plus and digits.startswith("0049"):
        # z.B. "+0049 30 12345" → wie "0049 30 12345"
        national = digits[4:]
    elif raw_starts_with_plus and digits.startswith("00"):
        # z.B. "+0030 12345" (Ausland) oder "+0049..." → strip leading 00
        national = digits[2:]
        if not national.startswith("49"):
            return None, "kein_deutsches_format"
        national = national[2:]
    # Tippfehler: "+049..." → "+" zeigt internationale Absicht, 049 = Tippfehler für 49
    elif raw_starts_with_plus and digits.startswith("049"):
        national = digits[3:]
    # Standard: +49...
    elif raw_starts_with_plus and digits.startswith("49"):
        national = digits[2:]
    # Standard: 0049...
    elif digits.startswith("0049"):
        national = digits[4:]
    # 00<andere CC>... → Ausland (IDD mit nicht-deutschen Länderkennzahl)
    elif digits.startswith("00"):
        return None, "auslaendische_nummer"
    # 49... ohne + → wie +49 behandeln
    elif digits.startswith("49"):
        national = digits[2:]
    # 0... → nationales Format (inkl. "049xx" als 0 + Vorwahl 49xx)
    elif digits.startswith("0"):
        national = digits[1:]
    else:
        return None, "kein_deutsches_format"

    # Sonderfall: national beginnt noch mit 0 (z.B. +49017... → 017...)
    if national.startswith("00"):
        return None, "amtsvorwahl_oder_pbx"
    if national.startswith("0"):
        national = national[1:]

    if not national:
        return None, "zu_kurz"

    return national, None


# ---------------------------------------------------------------------------
# Haupt-API
# ---------------------------------------------------------------------------

def parse_rufnummer(raw: str, strict: bool = False) -> dict | None:
    """
    Analysiert eine deutsche Rufnummer in beliebigem Format.

    Parameter:
        raw    – Eingabestring (beliebige Formatierung)
        strict – True: bei Fehler dict mit "fehler"-Key zurückgeben
                 False (Standard): bei Fehler None zurückgeben

    Rückgabe bei Erfolg:
        {"land": "+49", "ortsnetz": "069", "rufnummer": "...", "bezeichnung": "..."}
    Rückgabe bei Fehler:
        None  (strict=False)  oder  {"fehler": "<grund>"}  (strict=True)
    """

    def fehlschlag(grund: str):
        return {"fehler": grund} if strict else None

    if not raw or not raw.strip():
        return fehlschlag("leer")

    raw = raw.strip()
    digits = _nur_ziffern(raw)
    raw_starts_with_plus = raw.startswith("+")

    if len(digits) < 3:
        return fehlschlag("zu_kurz")

    # ── Schritt 1: Länderkennzahl extrahieren ──────────────────────────────
    national, fehler = _extrahiere_national(digits, raw_starts_with_plus)
    if fehler:
        return fehlschlag(fehler)

    # ── Schritt 2: Vorwahl per longest-prefix-match finden ─────────────────
    vorwahl, rufnummer, bezeichnung = _match_vorwahl(national)

    # ── Schritt 2b: try-both für "049..." ohne "+" ──────────────────────────
    # Ohne "+" ist "049xxx" ambig:
    #   Interpretation A (Schritt 1): 0 (national) + Vorwahl 49xx → national = "49xx..."
    #   Interpretation B (hier):      0049 (Tippfehler) + Vorwahl xx → national = "xx..."
    #
    # Entscheidungslogik:
    #   1. Trennzeichen zwischen "049" und dem Rest im Original → B gewinnt
    #      (explizit getrenntes Präfix signalisiert internationale Absicht)
    #   2. B liefert gültige Vorwahl, A nicht → B gewinnt
    #   3. Beide gültig + gleiche Vorwahllänge → A gewinnt (nationaler Kontext wahrsch.)
    #   4. B hat längere Vorwahl → B gewinnt (spezifischer)
    # Mit "+" wurde 049 bereits als Tippfehler für +49 behandelt → kein try-both nötig.
    if digits.startswith("049") and not raw_starts_with_plus:
        # Prüfe ob "049" durch Trennzeichen vom Rest getrennt ist
        sep_nach_049 = bool(re.match(r'^049[\s\(\)\-\/\\\.\,]', raw))

        nat_b = digits[3:]
        if nat_b.startswith("0"):
            nat_b = nat_b[1:]
        if nat_b:
            vw_b, rn_b, bez_b = _match_vorwahl(nat_b)
            if vw_b is not None and len(rn_b or "") >= 2:
                a_ok = vorwahl is not None and len(rufnummer or "") >= 2
                if sep_nach_049:
                    # Trennzeichen nach "049": definitiv Tippfehler-Präfix → B
                    vorwahl, rufnummer, bezeichnung = vw_b, rn_b, bez_b
                elif not a_ok:
                    # A hat kein gültiges Ergebnis → B
                    vorwahl, rufnummer, bezeichnung = vw_b, rn_b, bez_b
                # Bei Gleichwertigkeit gewinnt A (nationaler Kontext wahrscheinlicher
                # wenn kein explizites Trennzeichen hinter 049 vorhanden)

    # ── Schritt 3: Fallback via Whitespace-Tokens ──────────────────────────
    # Greift wenn primary parse keine Vorwahl gefunden hat.
    # Nützlich wenn Trennzeichen die Tokens klar abgrenzen.
    if vorwahl is None:
        tok = _tokens(raw)
        start = 0
        # Länderkennzahl-Token identifizieren und überspringen
        if tok and tok[0] in ("0049", "49", "049", "0"):
            start = 1
        elif tok and tok[0] == "+49":
            start = 1
        elif tok and tok[0] == "00":
            # "00 <CC> ..." → zweites Token ist Ländercode; nur wenn CC == "49"
            if len(tok) >= 2 and tok[1] == "49":
                start = 2   # skip "00" and "49", next is Ortsnetz
            else:
                return fehlschlag("auslaendische_nummer")
        if start < len(tok):
            kandidat_tok = tok[start].lstrip("0") if tok[start].startswith("0") else tok[start]
            vw, rn, bez = _match_vorwahl(kandidat_tok + "".join(tok[start + 1:]))
            if vw is not None:
                vorwahl, rufnummer, bezeichnung = vw, rn, bez

    # ── Schritt 3b: Token-Fallback "49 <sep> Ortsnetz..." ───────────────────
    # z.B. "49/5754 65", "49 - 30 - 12345" – "49" als eigenes Token
    if vorwahl is None:
        tok = _tokens(raw)
        if tok and tok[0] == "49" and len(tok) >= 2:
            kandidat_tok = tok[1].lstrip("0") if tok[1].startswith("0") else tok[1]
            vw, rn, bez = _match_vorwahl(kandidat_tok + "".join(tok[2:]))
            if vw is not None:
                vorwahl, rufnummer, bezeichnung = vw, rn, bez

    # ── Schritt 3c: Token-Fallback "049 <sep> Ortsnetz..." ──────────────────
    # z.B. "049 (1511) / 749" – "049" als eigenes Token, Tippfehler für 0049.
    # Nur ohne "+", da "+049" bereits in _extrahiere_national als +49 behandelt.
    if vorwahl is None and not raw_starts_with_plus:
        tok = _tokens(raw)
        if tok and tok[0] == "049" and len(tok) >= 2:
            kandidat_tok = tok[1].lstrip("0") if tok[1].startswith("0") else tok[1]
            vw, rn, bez = _match_vorwahl(kandidat_tok + "".join(tok[2:]))
            if vw is not None:
                vorwahl, rufnummer, bezeichnung = vw, rn, bez

    if vorwahl is None:
        return fehlschlag("vorwahl_unbekannt")

    # ── Schritt 4: Validierung ─────────────────────────────────────────────
    if len(rufnummer) < 2:
        return fehlschlag("rufnummer_zu_kurz")

    # E.164: max 15 Stellen gesamt (ohne +)
    if len("49" + vorwahl + rufnummer) > 15:
        return fehlschlag("nummer_zu_lang")

    return {
        "land":        "+49",
        "ortsnetz":    "0" + vorwahl,
        "rufnummer":   rufnummer,
        "bezeichnung": bezeichnung,
    }
