# Rufnummernauflösung

🇬🇧 Command‑line tool and Python library that splits German phone numbers into country code, area code and subscriber number.

🇩🇪 Kommandozeilen-Tool und Python-Bibliothek zur Segmentierung deutscher Telefonnummern.
Zerlegt eine Rufnummer beliebiger Formatierung in die drei Bestandteile **internationale Vorwahl**, **Ortsnetz** und **Teilnehmernummer**.

---

## Dateien

| Datei | Zweck |
|---|---|
| `rufnummer_cli.py` | Interaktive Kommandozeilenanwendung |
| `rufnummer.py` | Bibliotheksmodul mit der Parsing-Funktion `parse_rufnummer()` |
| `vorwahlen.py` | Vorwahldatenbank (BNetzA, Stand 2022-07-27) |
| `test_rufnummer.py` | Automatisierter Test mit 10.000 deutschen Zufallsnummern |
| `test_ausland.py` | Automatisierter Test mit 10.000 europäischen Auslandsnummern |

---

## Voraussetzungen

- Python 3.10 oder neuer (wegen `tuple[...] | None`-Typannotationen)
- Keine externen Abhängigkeiten; nur Python-Stdlib (`re`)

---

## Ausführung

### Interaktiver Modus

```bash
python3 rufnummer_cli.py
```

Das Programm startet eine Eingabeschleife:

```
Rufnummern-Analyse (Deutsche Nummern)
========================================
Bitte Rufnummer (oder x zum Beenden): +49 (069) 12256-15
  Int. Vorwahl: +49
  Ortsnetz:     069  (Frankfurt am Main)
  Rufnummer:    1225615

Bitte Rufnummer (oder x zum Beenden): +44 20 7946 0958
  Keine deutsche Rufnummer erkannt: +44 20 7946 0958

Bitte Rufnummer (oder x zum Beenden): x
```

Beenden mit `x` oder `Strg+C`.

### Als Bibliothek in eigenem Code

```python
from rufnummer import parse_rufnummer

result = parse_rufnummer("+49 (069) 12256-15")
# {'land': '+49', 'ortsnetz': '069', 'rufnummer': '1225615', 'bezeichnung': 'Frankfurt am Main'}

result = parse_rufnummer("+44 20 7946 0958")
# None  (keine deutsche Nummer)

result = parse_rufnummer("ungültig")
# None

# Mit detailliertem Fehlergrund (strict-Modus):
result = parse_rufnummer("+44 20 7946 0958", strict=True)
# {'fehler': 'kein_deutsches_format'}
```

**Rückgabewert bei Erfolg:**

```python
{
    "land":        "+49",
    "ortsnetz":    "069",              # mit führender 0
    "rufnummer":   "1225615",
    "bezeichnung": "Frankfurt am Main" # aus BNetzA-Vorwahltabelle
}
```

**Rückgabewert bei Fehler:** `None` (Standard) oder `{"fehler": "<grund>"}` bei `strict=True`.

### Tests ausführen

```bash
python3 test_rufnummer.py   # 10.000 deutsche Zufallsnummern
python3 test_ausland.py     # 10.000 europäische Auslandsnummern
```

---

## Erkennungsstrategie

### Schritt 1 – Normalisierung

Alle Nicht-Ziffern werden entfernt, um eine reine Ziffernfolge (`digits`) zu erhalten.
Parallel wird der Eingabestring an typischen Trennzeichen (`()`, `-`, `/`, `.`, ` `) in Token zerlegt – diese Token-Liste dient als Fallback.

### Schritt 2 – Länderkennzahl erkennen

Die Erkennung folgt einer festen Prioritätsreihenfolge. Dabei werden auch gängige Tippfehler abgefangen:

| Eingabeformat | Interpretation |
|---|---|
| `+49...` | Standard E.164 |
| `0049...` | Standard IDD |
| `+0049...` | Tippfehler: `+` vor `00` |
| `+049...` | Tippfehler: `+` statt `+49` |
| `+00 49...` | Tippfehler: `+00` statt `00` |
| `49...` (ohne `+`) | Ohne Präfix, wird wie `+49` behandelt |
| `049...` | **Ambig** – siehe unten |
| `0...` | Nationales Format (`0` + Vorwahl) |
| `00<CC>...` mit CC ≠ 49 | Ausländische Nummer → abgelehnt |

**Sonderfall `049...`:** Diese Zeichenfolge ist mehrdeutig:
- Nationale Nummer: `0` (Wählton) + Vorwahl `49xx` (z.B. `04936` = Baltrum)
- Tippfehler für `0049` (z.B. `049 69 12345` als Fehleingabe für `0049 69 12345`)

Entscheidung: Steht nach `049` ein Trennzeichen im Original, wird es als Tippfehler für `0049` gewertet. Ohne Trennzeichen gewinnt die nationale Interpretation, es sei denn, sie liefert kein gültiges Ergebnis.

### Schritt 3 – Ortsnetzkennzahl erkennen (Longest-Prefix-Match)

Die bereinigte nationale Ziffernfolge wird gegen die BNetzA-Vorwahldatenbank geprüft.
Gesucht wird das **längste Präfix**, das in der Tabelle vorhanden ist (Längen 6 → 5 → 4 → 3 → 2).
Die längste Übereinstimmung gewinnt, da kürzere Vorwahlen oft Präfix einer spezifischeren längeren Vorwahl sind.

Beispiel: `06171` (Friedberg Hessen) wird korrekt bevorzugt gegenüber `0617` (nicht vergeben).

### Schritt 4 – Token-Fallbacks

Schlägt der direkte Longest-Prefix-Match fehl (unbekannte Vorwahl oder Trennzeichen mitten in der Vorwahl), werden drei Fallback-Strategien versucht:

1. **Token-Fallback allgemein:** Erstes Token = Länderkennzahl, zweites Token = Ortsnetzkennzahl (mit oder ohne führende `0`)
2. **`49`-Token-Fallback:** `49` als eigenes Token, nächstes Token = Ortsnetzkennzahl (z.B. `49 / 5754 - 65`)
3. **`049`-Token-Fallback:** `049` als eigenes Token = Tippfehler für `0049`, nächstes Token = Ortsnetzkennzahl

### Schritt 5 – Validierung

- Teilnehmernummer muss mindestens 2 Ziffern haben
- Gesamtlänge der E.164-Nummer darf 15 Stellen nicht überschreiten (ITU-Standard)

---

## Vorwahldatenbank

**Quelle:** Bundesnetzagentur (BNetzA), `NVONB.INTERNET.20220727.ONB.csv`

| Kategorie | Einträge |
|---|---|
| Ortsnetzkennzahlen (geographisch) | 5.200 |
| Mobilfunkpräfixe (015x / 016x / 017x) | 105 |
| Sonderrufnummern (0800, 0900, 0180x, 116xxx, …) | 44 |
| **Gesamt** | **5.349** |

Vorwahlen werden ohne führende `0` gespeichert (z.B. `"30"` für Berlin `030`).
Bei der Ausgabe wird die führende `0` wieder ergänzt.

---

## Testfälle und Testergebnisse

### Fixe Testfälle (Anforderungsbeispiele + Sonderfälle)

| Eingabe | Erwartet | Beschreibung |
|---|---|---|
| `+4917912345678` | `+49` / `0179` | E.164 kompakt, Mobilfunk |
| `+49017912345678` | `+49` / `0179` | E.164 mit überflüssiger `0` |
| `004906171653215` | `+49` / `06171` | IDD kompakt, 5-stellige Vorwahl |
| `0049 069 123589` | `+49` / `069` | IDD mit Leerzeichen |
| `+49 69 123-12` | `+49` / `069` | E.164 mit Bindestrich |
| `+49 (069)12256-15` | `+49` / `069` | E.164 mit Klammern |
| `03012256/15` | `+49` / `030` | National mit Schrägstrich |
| `4969123456` | `+49` / `069` | Ohne jedes Präfix-Zeichen |
| `49 30 12345678` | `+49` / `030` | `49` ohne `+`, mit Leerzeichen |
| `+049 69 123456` | `+49` / `069` | Tippfehler: `+` vor `049` |
| `+0049 30 12345` | `+49` / `030` | Tippfehler: `+` vor `0049` |
| `+00 49 30 12345` | `+49` / `030` | Tippfehler: `+00` statt `00` |
| `049 69 123456` | `+49` / `069` | Tippfehler: `049` statt `0049` |
| `000123456` | nicht erkannt | PBX-Amtsleitung |
| `+44 20 7946 0958` | nicht erkannt | Ausland (Großbritannien) |

### Automatisierter Zufallstest – Deutsche Nummern

10.000 Nummern, zufällig aus 5.349 Vorwahlen gezogen, in 7 Formatstilen formatiert:

| Format-Stil | Beispiel | Erkennungsrate |
|---|---|---|
| `E164_kompakt` | `+4969123456` | 100 % |
| `E164_plus_null` | `+49 069 123456` | 100 % |
| `IDD_kompakt` | `004969123456` | 100 % |
| `IDD_plus_null` | `0049 069 123456` | 100 % |
| `national` | `069 123456` | 100 % |
| `ohne_praefix` | `49 69 123456` | 100 % |
| `tippfehler_049` | `049 69 123456` | 100 % |
| **Gesamt** | | **100 %** |

Zusätzlich werden in jedem Format zufällig Trennzeichen (` `, `-`, `/`, `.`) und Klammern eingefügt sowie die Teilnehmernummer intern aufgeteilt.

### Automatisierter Zufallstest – Europäische Auslandsnummern

10.000 Nummern aus 46 europäischen Ländern (alle außer Deutschland), in 3 Formatstilen:

| Format-Stil | Beispiel | Erkennungsrate (korrekt → None) |
|---|---|---|
| `plus` | `+33 6 12 34 56 78` | 100 % |
| `idd` | `0033612345678` | 100 % |
| `idd_sep` | `00 33 6 12 34 56 78` | 100 % |
| **Gesamt** | | **100 %** |

---

## Bekannte Limitierungen

### 1. Rein nationale Auslandsnummern nicht erkennbar

Eine Nummer ohne Länderkennung und ohne `00`-Präfix, die zufällig mit einer deutschen Vorwahl beginnt, wird als deutsch interpretiert:

```
06 12 34 56 78   →  wird als 06123 / 456789 (deutsch) erkannt
                     (könnte aber Frankreich national sein: 06 = Mobilnetz)
```

**Grund:** Ohne `+CC` oder `00CC` ist eine ausländische nationale Nummer strukturell nicht von einer deutschen zu unterscheiden. Dies ist ein inhärentes Limit jedes heuristischen Ansatzes ohne Länderkennung.

**Empfehlung:** Im Zweifelsfall immer mit Länderkennzahl eingeben.

### 2. `049xx`-Vorwahlen vs. `049`-Tippfehler

Vorwahlen die mit `049` beginnen (z.B. `04936` Baltrum, `04920` Insel Baltrum-Umgebung) sind ohne Trennzeichen nicht von einem `0049`-Tippfehler zu unterscheiden:

```
04936 1234   →  korrekt als 04936 (Baltrum) erkannt
049 36 1234  →  wegen Trennzeichen als 0049 + 36 + 1234 interpretiert
```

Die Entscheidung orientiert sich am Trennzeichen nach `049`: mit Trennzeichen → Tippfehler für `0049`; ohne → nationale Vorwahl.

### 3. Amtsleitungen und PBX-Vorwahlen

Nummern mit mehrfacher führender `0` (z.B. `000 30 12345` für eine Amtsleitung mit Wählton `0` + `0030 12345`) werden nicht aufgelöst und als nicht erkennbar zurückgegeben. Die interne PBX-Ziffer muss vor der Übergabe an die Funktion entfernt werden.

### 4. Nummerportierung bei Mobilfunk

Die Vorwahltabelle enthält die **ursprüngliche Netzbetreiber-Zuweisung**. Durch Rufnummernportierung kann eine `0176`-Nummer heute bei einem anderen Anbieter als Vodafone liegen. Das Feld `bezeichnung` gibt nur den ursprünglichen Vergabeinhaber an.

### 5. Vorwahldatenstand

Die Datenbank basiert auf dem BNetzA-Verzeichnis vom 2022-07-27. Neu vergebene oder geänderte Ortsnetzkennzahlen nach diesem Datum sind nicht enthalten.

### 6. Keine Validierung der Teilnehmernummer

Der Parser prüft nur, ob die Vorwahl bekannt ist und die Teilnehmernummer die Mindestlänge (2 Ziffern) sowie die E.164-Gesamtlänge (15 Stellen) erfüllt. Ob die konkrete Teilnehmernummer tatsächlich vergeben ist, wird nicht geprüft.
