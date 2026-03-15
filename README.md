# 🔬 OM-1 Macro Focus Stacking Pipeline

**Automated focus stacking workflow for Olympus OM-1 macro photography**

Transform your focus-bracketed RAW images into stunning stacked photos with a beautiful web interface.

![Version](https://img.shields.io/badge/version-4.1-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-orange)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)

---

## ✨ Features

- 🎨 **Modern Web Interface** - Beautiful, responsive UI with real-time progress tracking
- 🖼️ **Smart Image Preview** - Thumbnail generation with intelligent caching
- ⚡ **Intelligent Processing** - Prefers camera JPEGs, converts RAW only when needed
- 🔍 **Automatic Series Detection** - Groups images by timestamp (configurable threshold)
- 🎯 **Helicon Focus Integration** - Professional stacking with Method A/B/C support
- 📊 **Live Progress Tracking** - Real-time logs and progress bars
- 💾 **Metadata Preservation** - EXIF data maintained in output files
- 🚀 **Performance Optimized** - Thumbnail caching, parallel processing
- 📦 **Native macOS App** - Double-click to launch, no terminal required

---

## 🎯 Quick Start

### Option 1: Download macOS App (Easiest!)

1. **Download** the latest `OM-1-Stacking-Pipeline-4.1.0.dmg` from [Releases](https://github.com/okuemmel/om1-stacking-pipeline/releases)
2. **Open DMG** and drag app to Applications folder
3. **Right-click** app → **Open** (first launch only, for macOS security)
4. **Browser opens automatically** at http://localhost:8080

### Option 2: Run from Source

```bash
# Clone repository
git clone https://github.com/okuemmel/om1-stacking-pipeline.git
cd om1-stacking-pipeline

# Install dependencies
pip3 install -r requirements.txt

# Run web interface
python3 macro_stacking_web_v4.1.py
```

---

## 📋 Requirements

### Software Dependencies

| Tool | Purpose | Installation |
|------|---------|--------------|
| **Python 3.8+** | Runtime | `brew install python` |
| **ImageMagick** | RAW conversion & thumbnails | `brew install imagemagick` |
| **exiftool** | EXIF metadata reading | `brew install exiftool` |
| **Helicon Focus** | Focus stacking engine | [Download](https://www.heliconsoft.com) ($30/year or $115 lifetime) |

### Python Packages

```bash
pip3 install flask flask-socketio pillow pyyaml python-socketio
```

---

## ⚙️ Configuration

Config file: `~/.stacking_config.yaml`

```yaml
# SD Card Settings
sd_card_mode: ask  # 'ask', 'first', or 'manual'

# Output Settings
output_dir: ~/Pictures/Stacked
output_format: jpg  # 'jpg' or 'tiff'
output_quality: 95

# Series Detection
time_threshold: 30  # Max seconds between images
min_images: 3       # Minimum images per series

# Helicon Focus
helicon_binary: /Applications/HeliconFocus.app/Contents/MacOS/HeliconFocus
helicon_method: C   # A=Weighted, B=Depth Map, C=Pyramid (best)
helicon_radius: 8   # 4-20
helicon_smoothing: 4  # 0-10

# Performance
jpg_converter: imagemagick
keep_temp: false
```

---

## 🚀 Usage

### Web Interface

1. **Launch App** (double-click or `python3 macro_stacking_web_v4.1.py`)
2. **Select Source** - SD card auto-detected or browse for folder
3. **Review Series** - Thumbnails show each series with image count
4. **Select & Process** - Choose series to stack, watch live progress
5. **Done!** - Stacks saved to output directory

### Workflow

```
Insert SD Card → Launch App → Select Series → Stack → Done!
```

**Typical Processing Time:**
- 10 images: ~15-45 seconds
- 30 images: ~35-90 seconds

---

## 🎨 Helicon Focus Methods

| Method | Speed | Quality | Best For |
|--------|-------|---------|----------|
| **A - Weighted Average** | ⚡⚡⚡ Fast | ⭐⭐ Good | Quick previews |
| **B - Depth Map** | ⚡⚡ Medium | ⭐⭐⭐ Better | 3D reconstruction |
| **C - Pyramid** | ⚡ Slow | ⭐⭐⭐⭐ Best | Final output ✅ |

**Recommendation:** Use Method C for best quality.

---

## 💡 Tips & Tricks

### Optimal Shooting

1. **Enable Focus Bracketing** on OM-1
   - Menu → Shooting → Focus Bracketing
   - Recommended: 10-30 images, small step size

2. **Shoot RAW + JPG**
   - Enables instant thumbnails
   - Faster processing (no conversion needed)

3. **Use Tripod**
   - Essential for sharp stacks
   - Enable image stabilization
   - Use self-timer or remote

### Performance Optimization

```yaml
# For speed:
jpg_converter: imagemagick
output_format: jpg
keep_temp: false

# For quality:
helicon_method: C
output_quality: 95
output_format: tiff
```

---

## 🛠️ Building from Source

See [BUILD.md](BUILD.md) for detailed instructions.

```bash
# Quick build
./build.sh

# Create DMG installer
./create_dmg.sh

# Result:
# - dist/OM-1 Stacking Pipeline.app
# - dist/OM-1-Stacking-Pipeline-4.1.0.dmg
```

---

## 📁 Project Structure

```
om1-stacking-pipeline/
├── macro_stacking_web_v4.1.py      # Web interface (main)
├── macro_stacking_v3.4_cached.py   # GUI interface (Tkinter)
├── setup.py                        # py2app configuration
├── build.sh                        # Build script
├── create_dmg.sh                   # DMG creator
├── icon_generator.sh               # Icon generator
├── examples/
│   └── config_default.yaml         # Default configuration
├── resources/
│   └── app_icon.icns               # App icon
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── BUILD.md                        # Build instructions
└── LICENSE                         # MIT License
```

---

## 🐛 Troubleshooting

### App won't open (Security Warning)

**macOS Gatekeeper blocks unsigned apps:**

```bash
# Solution 1: Right-click → Open
Right-click "OM-1 Stacking Pipeline.app" → Open → Open

# Solution 2: Remove quarantine
xattr -cr "OM-1 Stacking Pipeline.app"

# Solution 3: System Settings
System Settings → Privacy & Security → "Open Anyway"
```

### Browser doesn't open automatically

```bash
# Manually open browser:
open http://localhost:8080

# Check if server is running:
curl http://localhost:8080
```

### Thumbnails show as gray placeholders

```bash
# Check ImageMagick:
magick --version

# Test RAW conversion:
magick test.ORF -resize 200x133 test.jpg

# Install/reinstall:
brew reinstall imagemagick
```

### Helicon Focus not found

```bash
# Verify installation:
ls /Applications/HeliconFocus.app/Contents/MacOS/HeliconFocus

# Update config:
nano ~/.stacking_config.yaml
# Set correct path to helicon_binary
```

### Series not detected

```yaml
# Adjust thresholds in config:
time_threshold: 60  # Increase if shooting slowly
min_images: 2       # Decrease for smaller series
```

### Config file errors

```bash
# Reset config:
rm ~/.stacking_config.yaml

# App will create new default config on next launch
```

---

## 📊 Performance Benchmarks

**Test Setup:** OM-1, 20MP RAW, MacBook Pro M1

| Scenario | Time | Notes |
|----------|------|-------|
| **10 images (OOC JPG)** | ~15s | No conversion needed |
| **10 images (RAW only)** | ~45s | Includes RAW→JPG |
| **30 images (OOC JPG)** | ~35s | Method C, Radius 8 |
| **30 images (RAW only)** | ~90s | Full pipeline |

**Caching:**
- First run: ~3s per thumbnail
- Cached: <0.1s per thumbnail ⚡

---

## 🤝 Contributing

Contributions welcome!

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file

---

## 👤 Author

**Oliver Kümmel**

- GitHub: [@okuemmel](https://github.com/okuemmel)
- Email: oliver@kuemmel.dev
- Website: https://github.com/okuemmel/om1-stacking-pipeline

---

## 🙏 Acknowledgments

- **Helicon Soft** - Helicon Focus stacking engine
- **Olympus/OM System** - OM-1 camera
- **ImageMagick** - RAW processing
- **Flask & SocketIO** - Web framework
- **py2app** - macOS app bundling

---

## 📚 Additional Resources

- [Helicon Focus Documentation](https://www.heliconsoft.com/heliconsoft-docs/helicon-focus/)
- [OM-1 Focus Bracketing Guide](https://learnandsupport.getolympus.com)
- [Build Instructions](BUILD.md)
- [Changelog](CHANGELOG.md)

---

## 🔄 Version History

### v4.1.0 (2026-03-15)
- ✨ Web interface with live progress
- ✨ Thumbnail caching
- ✨ Native macOS app bundle
- ✨ Helicon Focus integration
- ✨ Smart JPG/RAW handling

### v3.4.0
- ✨ Tkinter GUI with previews
- ✨ Thumbnail generation

### v3.0.0
- ✨ Initial release
- ✨ CLI interface

---

## ⭐ Star History

If you find this useful, please star the repo!

[![Star History](https://img.shields.io/github/stars/okuemmel/om1-stacking-pipeline?style=social)](https://github.com/okuemmel/om1-stacking-pipeline)

---

## 📸 Example Gallery

*Coming soon - add your stacked photos!*

---

**Made with ❤️ for macro photography enthusiasts**

*Happy Stacking! 🔬📸*
