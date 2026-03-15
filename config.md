```markdown
# Konfiguration

Die Konfiguration liegt in `~/.stacking_config.yaml`.

## Vollständige Referenz

### SD-Karten-Erkennung

```yaml
# Modus: 'ask' (fragen), 'first' (erste nehmen), 'manual' (fester Pfad)
sd_card_mode: ask

# Nur für mode='manual'
watch_dir: /Volumes/untitled/DCIM
Modi:
ask - Zeigt alle SD-Karten, fragt welche genutzt werden soll
first - Nimmt automatisch erste gefundene Karte
manual - Nutzt festen Pfad aus watch_dir
Serien-Erkennung
yaml

# Max. Sekunden zwischen Bildern einer Serie
time_threshold: 30

# Mindestanzahl Bilder pro Serie
min_images: 3
Beispiel:
time_threshold: 30 → Bilder innerhalb 30s = eine Serie
min_images: 5 → Mindestens 5 Bilder nötig für Stacking
Stacking-Parameter
yaml

# focus-stack Consistency-Level (2-5)
consistency: 3

# Denoise-Level (0-2)
denoise: 0.5
Tuning:
consistency: 2 → Schnell, tolerant, mehr Artefakte
consistency: 5 → Langsam, streng, beste Qualität
denoise: 0 → Keine Glättung, maximale Schärfe
denoise: 2 → Starke Glättung, weniger Detail
Output
yaml

output_dir: ~/Pictures/Stacked
output_format: jpg      # 'jpg' oder 'tiff'
output_quality: 95      # 1-100 (nur für JPG)
GPS-Tagging (optional)
yaml

gpx_file: ~/Downloads/track.gpx
Wenn gesetzt, werden GPS-Koordinaten aus GPX-Track in Bilder geschrieben.
Debug
yaml

debug: false         # Mehr Output
keep_temp: false     # Temp-Files behalten
Beispiel-Configs
Schnelles Stacking
yaml

sd_card_mode: first
consistency: 2
denoise: 1.0
output_quality: 85
Maximale Qualität
yaml

sd_card_mode: ask
consistency: 5
denoise: 0
output_format: tiff
Mit GPS-Tagging
yaml

sd_card_mode: first
gpx_file: ~/Downloads/hike_20260314.gpx

