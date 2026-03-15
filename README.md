# 🔬 OM-1 Macro Focus Stacking Pipeline

**Automated focus stacking workflow for Olympus OM-1 macro photography**

Transform your focus-bracketed RAW images into stunning stacked photos with a beautiful web interface or powerful CLI tools.

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

---

## 📸 Screenshots

### Web Interface
![Web Interface](docs/screenshots/web-interface.png)

### Series Selection
![Series Selection](docs/screenshots/series-selection.png)

### Live Processing
![Live Processing](docs/screenshots/live-processing.png)

---

## 🎯 Quick Start

### Prerequisites

```bash
# macOS with Homebrew
brew install python imagemagick exiftool

# Helicon Focus (required for stacking)
# Download from: https://www.heliconsoft.com/heliconsoft-products/helicon-focus/
```

### Installation

```bash
# Clone repository
git clone https://github.com/okuemmel/om1-stacking-pipeline.git
cd om1-stacking-pipeline

# Install Python dependencies
pip install -r requirements.txt

# Copy example config
cp examples/config_default.yaml ~/.stacking_config.yaml

# Edit config (set Helicon path, output directory, etc.)
nano ~/.stacking_config.yaml
```

### Run Web Interface

```bash
python3 macro_stacking_web_v4.1.py

# Browser opens automatically at http://localhost:8080
```

### Run GUI (Tkinter)

```bash
python3 macro_stacking_v3.4_cached.py
```

---

## 📋 Requirements

### Software Dependencies

| Tool | Purpose | Installation |
|------|---------|--------------|
| **Python 3.8+** | Runtime | `brew install python` |
| **ImageMagick** | RAW conversion & thumbnails | `brew install imagemagick` |
| **exiftool** | EXIF metadata reading | `brew install exiftool` |
| **Helicon Focus** | Focus stacking engine | [Download](https://www.heliconsoft.com) |

### Python Packages

```bash
# Web version
flask>=2.3.0
flask-socketio>=5.3.0
pillow>=10.0.0
pyyaml>=6.0

# GUI version (additional)
tkinter  # Usually included with Python
```

---

## ⚙️ Configuration

Edit `~/.stacking_config.yaml`:

```yaml
# SD Card Settings
sd_card_mode: ask  # 'ask', 'first', or 'manual'
watch_dir: /Volumes/SD-CARD/DCIM  # For manual mode

# Output Settings
output_dir: ~/Pictures/Stacked
output_format: jpg  # 'jpg' or 'tiff'
output_quality: 95

# Series Detection
time_threshold: 30  # Max seconds between images in a series
min_images: 3       # Minimum images per series

# Helicon Focus Settings
helicon_binary: /Applications/HeliconFocus.app/Contents/MacOS/HeliconFocus
helicon_method: C   # A=Weighted, B=Depth Map, C=Pyramid (best quality)
helicon_radius: 8   # 4-20
helicon_smoothing: 4  # 0-10

# Image Processing
jpg_quality: 95
jpg_converter: imagemagick  # 'imagemagick' or 'dcraw'

# Performance
keep_temp: false  # Keep temporary files for debugging
```

---

## 🚀 Usage

### Web Interface (Recommended)

1. **Start Server**
   ```bash
   python3 macro_stacking_web_v4.1.py
   ```

2. **Select Source**
   - Auto-detects SD cards
   - Or browse for DCIM folder

3. **Review Series**
   - Thumbnails generated automatically
   - Select/deselect series to stack
   - See image count and duration

4. **Process**
   - Watch live progress
   - View detailed logs
   - Get completion summary

### GUI Interface (Tkinter)

```bash
python3 macro_stacking_v3.4_cached.py
```

- Native macOS window
- Thumbnail preview grid
- Interactive selection
- Progress tracking

---

## 📁 Project Structure

```
om1-stacking-pipeline/
├── macro_stacking_web_v4.1.py      # Web interface (recommended)
├── macro_stacking_v3.4_cached.py   # GUI interface
├── examples/
│   └── config_default.yaml         # Default configuration
├── docs/
│   ├── screenshots/                # UI screenshots
│   └── workflow.md                 # Detailed workflow guide
├── requirements.txt                # Python dependencies
├── README.md                       # This file
└── LICENSE                         # MIT License
```

---

## 🔧 How It Works

### 1. Image Detection
```
SD Card → Scan for ORF files → Extract EXIF timestamps
```

### 2. Series Grouping
```
Sort by time → Group images within threshold → Filter by min count
```

### 3. Smart Processing
```
Check for OOC JPG → Use directly (fast!) ⚡
  ↓ No JPG?
Convert ORF → JPG (ImageMagick) → Cache thumbnail
```

### 4. Focus Stacking
```
Prepare images → Helicon Focus CLI → Apply metadata → Done! ✅
```

---

## 🎨 Helicon Focus Methods

| Method | Speed | Quality | Best For |
|--------|-------|---------|----------|
| **A - Weighted Average** | ⚡⚡⚡ Fast | ⭐⭐ Good | Quick previews |
| **B - Depth Map** | ⚡⚡ Medium | ⭐⭐⭐ Better | 3D reconstruction |
| **C - Pyramid** | ⚡ Slow | ⭐⭐⭐⭐ Best | Final output (recommended) |

**Recommendation:** Use Method C for best quality. Adjust `helicon_radius` (4-20) and `helicon_smoothing` (0-10) for fine-tuning.

---

## 💡 Tips & Tricks

### Optimal Shooting Technique

1. **Use Focus Bracketing**
   - OM-1: Menu → Shooting → Focus Bracketing
   - Recommended: 10-30 images, small step size

2. **Shoot RAW + JPG**
   - Enables instant thumbnails
   - Faster processing
   - Config: `RAW+JPG` in camera

3. **Keep Camera Stable**
   - Use tripod
   - Enable image stabilization
   - Use self-timer or remote

### Performance Optimization

```yaml
# For faster processing:
jpg_converter: imagemagick  # Faster than dcraw
keep_temp: false            # Auto-cleanup
output_format: jpg          # Faster than TIFF

# For best quality:
helicon_method: C
output_quality: 95
output_format: tiff         # 16-bit output
```

### Troubleshooting

**Problem:** Thumbnails show as gray placeholders
```bash
# Check ImageMagick installation
magick --version

# Test RAW conversion
magick P3150001.ORF -resize 200x133 test.jpg
```

**Problem:** Helicon Focus not found
```bash
# Verify path
ls /Applications/HeliconFocus.app/Contents/MacOS/HeliconFocus

# Update config
nano ~/.stacking_config.yaml
```

**Problem:** Series not detected
```yaml
# Adjust detection threshold
time_threshold: 60  # Increase if shooting slowly
min_images: 2       # Decrease for smaller series
```

---

## 📊 Performance Benchmarks

**Test Setup:** OM-1, 20MP RAW files, MacBook Pro M1

| Scenario | Time per Stack | Notes |
|----------|----------------|-------|
| **10 images (OOC JPG)** | ~15s | Fastest (no conversion) |
| **10 images (RAW only)** | ~45s | Includes RAW→JPG conversion |
| **30 images (OOC JPG)** | ~35s | Method C, Radius 8 |
| **30 images (RAW only)** | ~90s | Full pipeline |

**Caching Impact:**
- First run: ~3s per thumbnail (RAW extraction)
- Cached runs: <0.1s per thumbnail (instant!)

---

## 🛠️ Development

### Running Tests

```bash
# Dry run mode (no actual stacking)
python3 macro_stacking_web_v4.1.py --dry-run

# Debug mode (verbose logging)
python3 macro_stacking_web_v4.1.py --debug
```

### Project Roadmap

- [x] Web interface with live progress
- [x] Thumbnail caching
- [x] Helicon Focus integration
- [ ] Focus-stack fallback option
- [ ] Batch processing API
- [ ] Docker container
- [ ] Windows/Linux support
- [ ] GPU acceleration
- [ ] Cloud processing option

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 👤 Author

**Oliver Kümmel**

- GitHub: [@okuemmel](https://github.com/okuemmel)
- Email: oliver@kuemmel.dev

---

## 🙏 Acknowledgments

- **Helicon Soft** - For Helicon Focus stacking engine
- **Olympus/OM System** - For the amazing OM-1 camera
- **ImageMagick** - For RAW processing capabilities
- **Flask & SocketIO** - For web framework

---

## 📚 Additional Resources

- [Helicon Focus Documentation](https://www.heliconsoft.com/heliconsoft-docs/helicon-focus/)
- [OM-1 Focus Bracketing Guide](https://learnandsupport.getolympus.com)
- [Focus Stacking Tutorial](docs/tutorial.md)
- [API Documentation](docs/api.md)

---

## ⭐ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=okuemmel/om1-stacking-pipeline&type=Date)](https://star-history.com/#okuemmel/om1-stacking-pipeline&Date)

---

**Made with ❤️ for macro photography enthusiasts**
