#!/usr/bin/env python3
"""
Automatischer Makro-Stacking-Workflow für OM-1 auf macOS
Mit focus-stack, LibRaw und automatischer SD-Karten-Erkennung
"""

import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timedelta

class OM1StackingPipeline:
    
    def __init__(self, config_path="~/.stacking_config.yaml"):
        self.config = self.load_config(config_path)
        self.output_dir = Path(self.config['output_dir']).expanduser()
        self.temp_dir = Path(self.config['temp_dir']).expanduser()
        self.gpx_file = Path(self.config.get('gpx_file', '')).expanduser() if self.config.get('gpx_file') else None
        self.stacker_bin = Path(self.config['stacker_binary']).expanduser()
        self.watch_dir = None
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self, path):
        """Config laden oder Default erstellen"""
        config_path = Path(path).expanduser()
        
        if not config_path.exists():
            default_config = """# ═══════════════════════════════════════════════════════════
# OM-1 Makro-Stacking Pipeline - Konfiguration
# ═══════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────────
# SD-Karten-Erkennung
# ───────────────────────────────────────────────────────────

# Modus: 'ask' (immer fragen), 'first' (erste nehmen), 'manual' (fester Pfad)
sd_card_mode: ask

# Nur für sd_card_mode='manual': Fester Pfad zum DCIM-Ordner
watch_dir: /Volumes/untitled/DCIM

# ───────────────────────────────────────────────────────────
# Output-Einstellungen
# ───────────────────────────────────────────────────────────

# Wo sollen die fertigen Stacks gespeichert werden?
output_dir: ~/Pictures/Stacked

# Temporäres Verzeichnis (wird automatisch aufgeräumt)
temp_dir: /tmp/stacking

# ───────────────────────────────────────────────────────────
# Serien-Erkennung
# ───────────────────────────────────────────────────────────

# Max. Sekunden zwischen Bildern einer Serie
# Beispiel: 30 = Bilder innerhalb 30 Sekunden gehören zusammen
time_threshold: 30

# Mindestanzahl Bilder pro Serie
# Beispiel: 3 = mindestens 3 Bilder für Stacking nötig
min_images: 3

# ───────────────────────────────────────────────────────────
# GPS-Tagging (optional)
# ───────────────────────────────────────────────────────────

# Pfad zu GPX-Track-File für GPS-Tagging
# Leer lassen ("") wenn nicht benötigt
gpx_file: ""

# ───────────────────────────────────────────────────────────
# Stacking-Software
# ───────────────────────────────────────────────────────────

# Stacker: 'focus-stack' oder 'shinestacker'
stacker: focus-stack

# Pfad zum Stacker-Binary
stacker_binary: ~/bin/focus-stack/focus-stack.app/Contents/MacOS/focus-stack

# ───────────────────────────────────────────────────────────
# focus-stack Parameter
# ───────────────────────────────────────────────────────────

# Consistency-Level (2-5)
# Höher = strenger beim Alignment, besser für statische Motive
# Niedriger = toleranter, besser bei leichter Bewegung
consistency: 3

# Denoise-Level (0-2)
# 0 = aus, höher = mehr Rauschunterdrückung
# Empfohlen: 0.5 für Makro
denoise: 0.5

# Zwischenschritte speichern? (für Debugging)
save_steps: false

# ───────────────────────────────────────────────────────────
# RAW-Konvertierung
# ───────────────────────────────────────────────────────────

# ORF zu TIFF konvertieren?
# true = konvertieren (empfohlen für focus-stack)
# false = RAW direkt nutzen (funktioniert nur bei manchen Stackern)
convert_raw: true

# RAW-Konverter
# 'libraw' = empfohlen für OM-1 (aktuell, unterstützt neue Kameras)
# 'dcraw' = veraltet (funktioniert nicht gut mit OM-1)
raw_converter: libraw

# ───────────────────────────────────────────────────────────
# Debug-Optionen
# ───────────────────────────────────────────────────────────

# Debug-Modus aktivieren? (mehr Output)
debug: false

# Temporäre Dateien behalten statt löschen?
# Nützlich zum Debuggen, um konvertierte TIFFs zu inspizieren
keep_temp: false

# ───────────────────────────────────────────────────────────
# Output-Format
# ───────────────────────────────────────────────────────────

# Format: 'jpg' oder 'tiff'
output_format: jpg

# JPG-Qualität (1-100)
# 95 = hohe Qualität, guter Kompromiss
output_quality: 95
"""
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                f.write(default_config)
            print(f"✓ Config erstellt: {config_path}")
            print(f"  Bitte anpassen und erneut starten!")
            
            import yaml
            return yaml.safe_load(default_config)
        
        try:
            import yaml
        except ImportError:
            print("❌ PyYAML nicht installiert!")
            print("   Installiere mit: pip3 install pyyaml")
            exit(1)
        
        with open(config_path) as f:
            return yaml.safe_load(f)
    
    def find_sd_cards(self):
        """Finde alle gemounteten SD-Karten/Volumes mit DCIM-Ordner"""
        volumes_path = Path("/Volumes")
        sd_cards = []
        
        for volume in volumes_path.iterdir():
            if not volume.is_dir():
                continue
            
            if volume.name in ['Macintosh HD', 'Preboot', 'Recovery', 'VM', 'Data']:
                continue
            
            dcim_path = volume / "DCIM"
            if dcim_path.exists() and dcim_path.is_dir():
                orf_count = len(list(dcim_path.rglob("*.ORF"))) + len(list(dcim_path.rglob("*.orf")))
                
                sd_cards.append({
                    'name': volume.name,
                    'path': volume,
                    'dcim': dcim_path,
                    'orf_count': orf_count
                })
        
        return sd_cards
    
    def select_sd_card(self, sd_cards):
        """SD-Karte auswählen (automatisch oder interaktiv)"""
        
        if not sd_cards:
            return None
        
        mode = self.config.get('sd_card_mode', 'ask')
        
        if mode == 'first':
            selected = sd_cards[0]
            print(f"✓ SD-Karte automatisch gewählt: {selected['name']} ({selected['orf_count']} ORF-Files)")
            return selected
        
        elif mode == 'manual':
            manual_path = Path(self.config['watch_dir']).expanduser()
            if manual_path.exists():
                print(f"✓ Manueller Pfad aus Config: {manual_path}")
                return {
                    'name': manual_path.name,
                    'path': manual_path.parent,
                    'dcim': manual_path,
                    'orf_count': len(list(manual_path.rglob("*.ORF"))) + len(list(manual_path.rglob("*.orf")))
                }
            else:
                print(f"⚠️  Manueller Pfad existiert nicht: {manual_path}")
                return None
        
        else:
            print("\n📸 SD-Karten gefunden:\n")
            for i, card in enumerate(sd_cards, 1):
                print(f"  [{i}] {card['name']}")
                print(f"      Pfad: {card['path']}")
                print(f"      ORF-Files: {card['orf_count']}\n")
            
            while True:
                try:
                    choice = input("Welche SD-Karte verwenden? [1]: ").strip()
                    
                    if not choice:
                        choice = "1"
                    
                    idx = int(choice) - 1
                    
                    if 0 <= idx < len(sd_cards):
                        selected = sd_cards[idx]
                        print(f"\n✓ Gewählt: {selected['name']}\n")
                        return selected
                    else:
                        print("❌ Ungültige Auswahl!\n")
                except ValueError:
                    print("❌ Bitte eine Zahl eingeben!\n")
                except KeyboardInterrupt:
                    print("\n\n⚠️  Abgebrochen")
                    return None
    
    def get_exif_data(self, image_path):
        """EXIF-Daten mit exiftool auslesen"""
        try:
            result = subprocess.run(
                ['exiftool', '-DateTimeOriginal', '-json', str(image_path)],
                capture_output=True,
                text=True,
                check=True
            )
            import json
            data = json.loads(result.stdout)[0]
            timestamp_str = data.get('DateTimeOriginal', '')
            if not timestamp_str:
                return None
            timestamp = datetime.strptime(timestamp_str, "%Y:%m:%d %H:%M:%S")
            return timestamp
        except Exception as e:
            if self.config.get('debug', False):
                print(f"⚠️  Fehler beim Auslesen von {image_path.name}: {e}")
            return None
    
    def find_series(self, images):
        """Bilder in Serien gruppieren"""
        print("\n📊 Analysiere Bilder...")
        
        images_with_time = []
        for img in images:
            timestamp = self.get_exif_data(img)
            if timestamp:
                images_with_time.append((img, timestamp))
        
        if not images_with_time:
            return []
        
        images_with_time.sort(key=lambda x: x[1])
        
        series = []
        current_series = []
        last_time = None
        
        threshold = timedelta(seconds=self.config['time_threshold'])
        
        for img, timestamp in images_with_time:
            if last_time and (timestamp - last_time) > threshold:
                if len(current_series) >= self.config['min_images']:
                    series.append(current_series)
                current_series = [img]
            else:
                current_series.append(img)
            
            last_time = timestamp
        
        if len(current_series) >= self.config['min_images']:
            series.append(current_series)
        
        return series
    
    def convert_raw(self, orf_file, output_dir):
        """ORF zu 16-bit TIFF konvertieren mit LibRaw"""
        
        converter = self.config.get('raw_converter', 'libraw')
        
        try:
            if converter == 'libraw':
                subprocess.run([
                    'dcraw_emu',
                    '-6',
                    '-T',
                    '-w',
                    '-o', '1',
                    '-q', '3',
                    orf_file.name
                ], cwd=str(output_dir), check=True, capture_output=True)
                
                output_file_raw = output_dir / f"{orf_file.name}.tiff"
                output_file = output_dir / f"{orf_file.stem}.tiff"
                
                if output_file_raw.exists():
                    output_file_raw.rename(output_file)
                else:
                    raise RuntimeError(f"dcraw_emu erstellte kein Output")
                
                return output_file
            
            elif converter == 'dcraw':
                output_file = output_dir / f"{orf_file.stem}.tiff"
                subprocess.run([
                    'dcraw',
                    '-T', '-6', '-w', '-o', '1', '-q', '3', '-c',
                    str(orf_file)
                ], stdout=open(output_file, 'wb'), check=True, stderr=subprocess.DEVNULL)
                return output_file
            
            else:
                raise ValueError(f"Unbekannter Konverter: {converter}")
        
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Konvertierung fehlgeschlagen: {orf_file.name}")
        
        if not output_file.exists() or output_file.stat().st_size == 0:
            raise RuntimeError(f"Konvertierung produzierte leere Datei")
        
        return output_file
    
    def add_gps_data(self, images):
        """GPS-Daten aus GPX hinzufügen"""
        if not self.gpx_file or not self.gpx_file.exists():
            return
        
        print(f"🌍 Füge GPS-Daten hinzu: {self.gpx_file.name}")
        try:
            subprocess.run([
                'exiftool',
                '-geotag',
                str(self.gpx_file),
                '-overwrite_original',
                *[str(img) for img in images]
            ], check=True, capture_output=True)
            print("  ✓ GPS-Daten hinzugefügt")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  GPS-Tagging fehlgeschlagen: {e}")
    
    def stack_with_focus_stack(self, images, output_file):
        """Stacking mit focus-stack"""
        cmd = [
            str(self.stacker_bin),
            f'--output={output_file}',
            f'--consistency={self.config["consistency"]}',
            f'--denoise={self.config["denoise"]}',
        ]
        
        if self.config.get('save_steps', False):
            cmd.append('--save-steps')
        
        cmd.extend([str(img) for img in images])
        
        subprocess.run(cmd, check=True, capture_output=True)
    
    def stack_with_shinestacker(self, images, output_file):
        """Stacking mit shinestacker"""
        cmd = [
            str(self.stacker_bin),
            '-o', str(output_file),
            *[str(img) for img in images]
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
    
    def stack_series(self, images, output_name):
        """Focus-Stacking"""
        
        temp_series = self.temp_dir / output_name
        temp_series.mkdir(parents=True, exist_ok=True)
        
        print(f"  📸 Stacke {len(images)} Bilder...")
        
        print(f"  📁 Kopiere Bilder...")
        copied_images = []
        for img in images:
            dest = temp_series / img.name
            shutil.copy2(img, dest)
            copied_images.append(dest)
        
        if self.config.get('convert_raw', True):
            print(f"  🔄 Konvertiere RAW ({self.config['raw_converter']})...")
            converted = []
            for i, img in enumerate(copied_images, 1):
                try:
                    print(f"    [{i}/{len(copied_images)}] {img.name}", end=" ")
                    tiff = self.convert_raw(img, temp_series)
                    converted.append(tiff)
                    print("✓")
                except Exception as e:
                    print(f"✗ ({e})")
                    continue
            
            if not converted:
                raise RuntimeError("❌ Keine Bilder erfolgreich konvertiert!")
            
            print(f"  ✓ {len(converted)}/{len(copied_images)} Bilder konvertiert")
            images_to_stack = converted
        else:
            print(f"  📷 Stacke RAW-Files direkt")
            images_to_stack = copied_images
        
        print(f"  🔬 Stacking ({self.config['stacker']})...")
        output_file = self.output_dir / f"{output_name}.{self.config['output_format']}"
        
        if self.config['stacker'] == 'focus-stack':
            self.stack_with_focus_stack(images_to_stack, output_file)
        elif self.config['stacker'] == 'shinestacker':
            self.stack_with_shinestacker(images_to_stack, output_file)
        else:
            raise ValueError(f"Unbekannter Stacker: {self.config['stacker']}")
        
        if not self.config.get('keep_temp', False):
            shutil.rmtree(temp_series)
        else:
            print(f"  🐛 Debug: Temp-Files behalten in: {temp_series}")
        
        return output_file
    
    def notify(self, title, message):
        """macOS Notification"""
        try:
            subprocess.run([
                'osascript', '-e',
                f'display notification "{message}" with title "{title}"'
            ], check=True, capture_output=True)
        except:
            pass
    
    def run(self):
        """Haupt-Pipeline"""
        
        print("╔═══════════════════════════════════════════╗")
        print("║  OM-1 Makro-Stacking Pipeline            ║")
        print("╚═══════════════════════════════════════════╝")
        
        if not self.stacker_bin.exists():
            print(f"\n❌ Stacker Binary nicht gefunden: {self.stacker_bin}")
            print(f"   Bitte installieren oder Pfad in Config anpassen:")
            print(f"   nano ~/.stacking_config.yaml")
            return
        
        mode = self.config.get('sd_card_mode', 'ask')
        
        if mode in ['ask', 'first']:
            print("\n🔍 Suche SD-Karten...")
            sd_cards = self.find_sd_cards()
            
            if not sd_cards:
                print("❌ Keine SD-Karte mit DCIM-Ordner gefunden!")
                print("   Stecke SD-Karte ein oder nutze 'sd_card_mode: manual' in Config")
                return
            
            selected_card = self.select_sd_card(sd_cards)
            
            if not selected_card:
                print("❌ Keine SD-Karte ausgewählt")
                return
            
            self.watch_dir = selected_card['dcim']
        
        else:
            self.watch_dir = Path(self.config['watch_dir']).expanduser()
            print(f"\n📁 Nutze manuellen Pfad: {self.watch_dir}")
        
        images = list(self.watch_dir.rglob("*.ORF"))
        images.extend(self.watch_dir.rglob("*.orf"))
        
        if not images:
            print(f"\n❌ Keine ORF-Bilder gefunden in: {self.watch_dir}")
            return
        
        print(f"\n✓ Gefunden: {len(images)} Bilder")
        
        if self.gpx_file:
            self.add_gps_data(images)
        
        series = self.find_series(images)
        
        if not series:
            print("\n❌ Keine Serien erkannt")
            print(f"   (zu wenig Bilder pro Serie oder Zeitabstand > {self.config['time_threshold']}s)")
            self.notify("Makro-Stacking", "❌ Keine Serien erkannt")
            return
        
        print(f"✓ Erkannt: {len(series)} Serien\n")
        
        success_count = 0
        for i, imgs in enumerate(series, 1):
            timestamp = self.get_exif_data(imgs[0])
            series_name = f"series_{timestamp.strftime('%Y%m%d_%H%M%S')}"
            
            print(f"━━━ Serie {i}/{len(series)}: {series_name} ━━━")
            print(f"  Bilder: {len(imgs)}")
            
            try:
                output = self.stack_series(imgs, series_name)
                print(f"  ✓ Fertig: {output.name}\n")
                success_count += 1
            except Exception as e:
                print(f"  ❌ Fehler: {e}\n")
                self.notify("Makro-Stacking", f"❌ Fehler bei Serie {i}")
        
        print("╔═══════════════════════════════════════════╗")
        print(f"║  ✓ {success_count}/{len(series)} Serien erfolgreich gestackt!    ║")
        print("╚═══════════════════════════════════════════╝")
        print(f"\nOutput: {self.output_dir}")
        
        if success_count > 0:
            self.notify("Makro-Stacking", f"✓ {success_count} Serien fertig!")


if __name__ == "__main__":
    try:
        pipeline = OM1StackingPipeline()
        pipeline.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Abgebrochen durch Benutzer")
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()