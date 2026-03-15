# OM-1 Makro-Stacking Pipeline

Automatischer Focus-Stacking-Workflow für die OM System OM-1 (und andere ORF-Kameras) auf macOS.

SD-Karte einstecken → Script starten → Fertige gestackte Bilder im Output-Ordner. Keine manuelle Sortierung, keine GUI, vollautomatisch.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- 🔍 **Automatische SD-Karten-Erkennung** - Erkennt gemountete Volumes mit DCIM-Ordner
- 📊 **Intelligente Serien-Erkennung** - Gruppiert Bilder via EXIF-Timestamps
- 🔄 **RAW-Konvertierung** - ORF → 16-bit TIFF mit LibRaw (dcraw_emu)
- 🔬 **Focus-Stacking** - Nutzt focus-stack für hochqualitative Ergebnisse
- 🌍 **GPS-Tagging** (optional) - Merge GPS-Tracks mit Bildern
- ⚙️ **YAML-Config** - Lesbare Konfiguration mit Kommentaren
- 🚀 **Vollautomatisch** - Kein manuelles Eingreifen nötig

## Workflow
SD-Karte einstecken
↓
python3 macro_stacking.py
↓
☕ Kaffee trinken
↓
Fertige Bilder in ~/Pictures/Stacked/

## Quick Start

### Installation

```bash
# Dependencies installieren
brew install python3 exiftool libraw
pip3 install pyyaml

# focus-stack installieren
# Download: https://github.com/PetteriAimonen/focus-stack/releases
mkdir -p ~/bin
mv focus-stack ~/bin/
chmod +x ~/bin/focus-stack

# Script installieren
git clone https://github.com/DEIN-USERNAME/om1-stacking-pipeline.git
cd om1-stacking-pipeline
chmod +x macro_stacking.py
Erste Ausführung
bash

# Erstellt Config-Datei
./macro_stacking.py

# Config anpassen
nano ~/.stacking_config.yaml

# SD-Karte einstecken und starten
./macro_stacking.py
Konfiguration
Die Config liegt in ~/.stacking_config.yaml:
yaml

# SD-Karten-Modus: 'ask', 'first', 'manual'
sd_card_mode: ask

# Serien-Erkennung
time_threshold: 30      # Sekunden zwischen Bildern
min_images: 3           # Mindestanzahl pro Serie

# Stacking-Parameter
consistency: 3          # 2-5, höher = strenger
denoise: 0.5            # 0-2, Rauschunterdrückung

# Output
output_dir: ~/Pictures/Stacked
output_format: jpg
output_quality: 95
Siehe CONFIG.md für alle Optionen.
Beispiel-Output
╔═══════════════════════════════════════════╗
║  OM-1 Makro-Stacking Pipeline            ║
╚═══════════════════════════════════════════╝

🔍 Suche SD-Karten...
✓ SD-Karte: untitled (42 ORF-Files)

✓ Gefunden: 42 Bilder
✓ Erkannt: 3 Serien

━━━ Serie 1/3: series_20260314_083628 ━━━
  📸 Stacke 16 Bilder...
  🔄 Konvertiere RAW...
    [16/16] ✓
  🔬 Stacking...
  ✓ Fertig: series_20260314_083628.jpg

╔═══════════════════════════════════════════╗
║  ✓ 3/3 Serien erfolgreich gestackt!      ║
╚═══════════════════════════════════════════╝
Requirements
Hardware
Kamera: OM System OM-1 (oder andere Olympus/OM System mit ORF)
Computer: macOS (Intel oder Apple Silicon)
RAM: 8GB+ (16GB empfohlen für große Serien)
Software
Python: 3.8+
LibRaw: dcraw_emu für RAW-Konvertierung
focus-stack: Stacking-Engine
exiftool: EXIF-Daten auslesen
PyYAML: Config-Parsing
Architektur
┌─────────────────┐
│   SD-Karte      │
└────────┬────────┘
         │ mount
         ▼
┌─────────────────┐
│ find_sd_cards() │  Erkennt DCIM-Ordner
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ find_series()   │  Gruppiert via EXIF
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ convert_raw()   │  ORF → 16-bit TIFF
└────────┬────────┘  (dcraw_emu)
         │
         ▼
┌─────────────────┐
│ stack_series()  │  Focus-Stacking
└────────┬────────┘  (focus-stack)
         │
         ▼
┌─────────────────┐
│ ~/Pictures/     │
│   Stacked/      │
└─────────────────┘
Dokumentation
Troubleshooting
"Keine SD-Karte gefunden"
bash

# Check ob DCIM-Ordner existiert
ls /Volumes/*/DCIM/

# Manuellen Pfad nutzen
# In ~/.stacking_config.yaml:
sd_card_mode: manual
watch_dir: /Volumes/MEINE_KARTE/DCIM
"dcraw_emu: command not found"
bash

brew install libraw
which dcraw_emu
Schlechte Stacking-Qualität
✅ 16-bit TIFF? (Check: file /tmp/stacking/*/P*.tiff)
✅ Genug Bilder? (min. 5-10 für Makro)
✅ Stativ benutzt?
✅ Parameter anpassen: consistency: 5, denoise: 0
Siehe Troubleshooting Guide
Performance
Benchmark (M1 MacBook Pro, 20MP ORF):
Bilder	RAW → TIFF	Stacking	Total
7	12s	8s	20s
16	28s	22s	50s
32	58s	65s	2m 3s
Roadmap
 Parallele Verarbeitung (mehrere Serien gleichzeitig)
 Hazel-Integration (automatisch bei SD-Karte)
 Web-UI (Flask-Dashboard)
 Qualitäts-Check (verwackelte Bilder aussortieren)
 Linux/Windows Support
 Helicon Focus Support
Contributing
Contributions sind willkommen! Siehe CONTRIBUTING.md
Wie du helfen kannst:
🐛 Bugs reporten
💡 Features vorschlagen
📝 Dokumentation verbessern
🔧 Code beitragen
License
MIT License - siehe LICENSE
Credits
Tools:
LibRaw - RAW-Konvertierung
focus-stack - Stacking-Engine
exiftool - EXIF-Parsing
Inspiration:
Author
Oliver Kümmel
Blog: kmml.uk
E-Mail: o@kuemmel.xyz
Links
Star ⭐ das Repo wenn's dir hilft!
