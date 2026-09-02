# Reproduzierbare Laufzeitumgebung

Stand: 2. September 2026

## Python-Referenzumgebung

Die geprüfte Referenzumgebung verwendet:

- CPython **3.12.13**, 64-bit, Windows
- die exakt gepinnten direkten und transitiven Pakete aus
  [`requirements.lock.txt`](requirements.lock.txt)

Installation in einer neuen virtuellen Umgebung:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
python -m pip check
python -m pytest -q
```

`requirements.txt` enthält weiterhin die unterstützten Mindestversionen für eine
flexible Entwicklungsumgebung. `requirements.lock.txt` ist für die reproduzierbare
Referenzumgebung maßgeblich. Die Lockdatei fixiert Versionen, enthält aber keine
plattformabhängigen Paket-Hashes.

## Externe Abhängigkeiten

### Tesseract-OCR

Die OCR-Stufe benötigt Tesseract mit den Sprachpaketen `lat` und `eng`. Im Repository
war keine historische Tesseract-Versionsnummer protokolliert, und auf dem bei der
Erstellung dieser Datei verwendeten Rechner war Tesseract nicht installiert. Daher
wird keine vermeintlich exakte Version nachträglich behauptet.

Für einen vollständigen Neulauf müssen folgende Angaben protokolliert werden:

```powershell
tesseract --version
tesseract --list-langs
```

Die Pipeline erwartet standardmäßig `tesseract` auf `PATH`; alternativ kann der
ausführbare Pfad über `TESSERACT_CMD` gesetzt werden. Die verwendete Konfiguration
ist `lat+eng`, OEM `1`, PSM `6` und 300 dpi für die gerenderten Seiten.

### Mistral-API und Modelle

Die Pipeline verwendet derzeit folgende konfigurierbare Modellbezeichner:

- Extraktion: `mistral-medium-latest`
- Judge: `mistral-large-latest`
- OCR-Evaluation: `mistral-ocr-latest`, `mistral-medium-latest`,
  `mistral-large-latest`

Die Bezeichner mit dem Suffix `-latest` sind serverseitig veränderliche Aliase und
keine unveränderlichen Modell-Snapshots. Deshalb sind erneute API-Ausgaben trotz
identischer lokaler Abhängigkeiten nicht vollständig deterministisch reproduzierbar.
Bei einem neuen API-Lauf sollten Datum, tatsächlich aufgelöste Modellversion (sofern
vom Anbieter ausgegeben) und relevante Parameter zusammen mit den Ergebnissen
protokolliert werden. Der API-Schlüssel gehört ausschließlich in die Umgebungsvariable
`MISTRAL_API_KEY` und niemals in das Repository.

## Reproduzierbarkeitsgrenze

Die bereits geprüften Stufen 5, Korrekturoverlay, RDF-Erzeugung und Regressionstests
können mit der Python-Lockdatei ohne Tesseract und ohne API-Schlüssel ausgeführt
werden. Für einen vollständigen Neulauf ab Quell-PDF werden zusätzlich die konkrete
Quell-PDF, Tesseract samt Sprachpaketen und der Mistral-Zugang benötigt.
