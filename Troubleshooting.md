```markdown
# Troubleshooting

## Installation

### "dcraw_emu: command not found"

**Lösung:**
```bash
brew install libraw
which dcraw_emu
"PyYAML not found"
Lösung:
bash

pip3 install pyyaml
"focus-stack not found"
Lösung:
bash

# Binary von GitHub herunterladen
# https://github.com/PetteriAimonen/focus-stack/releases
mkdir -p ~/bin
mv focus-stack ~/bin/
chmod +x ~/bin/focus-stack

# In Config anpassen:
nano ~/.stacking_config.yaml
# stacker_binary: ~/bin/focus-stack
Runtime
"Keine SD-Karte gefunden"
Check:
bash

ls /Volumes/
ls /Volumes/*/DCIM/
Lösungen:
SD-Karte neu einstecken
Manuellen Pfad nutzen:
yaml

sd_card_mode: manual
   watch_dir: /Volumes/MEINE_KARTE/DCIM
"Keine Serien erkannt"
Mögliche Ursachen:
Zu wenig Bilder (< min_images)
Zu großer Zeitabstand (> time_threshold)
Keine EXIF-Daten
Lösung:
yaml

time_threshold: 60    # Erhöhen
min_images: 2         # Reduzieren
Schlechte Stacking-Qualität
Checklist:
✅ 16-bit TIFF?
bash

file /tmp/stacking/series_*/P*.tiff
   # Sollte zeigen: "16-bit"
✅ Genug Bilder? (min. 5-10 für Makro)
✅ Stativ benutzt?
✅ Parameter anpassen:
yaml

consistency: 5
   denoise: 0
✅ Temp-Files inspizieren:
yaml

keep_temp: true
Dann TIFFs in /tmp/stacking/ prüfen
"Unexpected end of file" bei dcraw_emu
Ursache: Probleme beim Lesen von SD-Karte
Lösung: Script kopiert Bilder erst nach /tmp - sollte nicht mehr auftreten.
Falls doch:
yaml

temp_dir: ~/tmp/stacking
focus-stack crashed
Mögliche Ursachen:
Zu wenig RAM
Korrupte Files
Bilder zu unterschiedlich
Debug:
yaml

keep_temp: true
debug: true
Dann manuell testen:
bash

cd /tmp/stacking/series_*/
~/bin/focus-stack --output=test.jpg *.tiff
Performance
Langsam
Optimierungen:
SSD statt HDD für temp_dir
Mehr RAM (16GB+)
consistency reduzieren
Hoher RAM-Verbrauch
Lösung:
yaml

# Kleinere Batches (TODO: Feature)
# Oder: Serien manuell aufteilen

