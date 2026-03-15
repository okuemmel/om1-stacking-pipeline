# Changelog

All notable changes to OM-1 Stacking Pipeline will be documented here.

## [4.1.0] - 2026-03-15

### Added
- 🎨 Modern web interface with Flask + SocketIO
- 📊 Real-time progress tracking with live logs
- 🖼️ Thumbnail preview with intelligent caching
- 🎯 Helicon Focus CLI integration
- ⚡ Smart image handling (prefer OOC JPG over RAW conversion)
- 📦 Native macOS app bundle (.app)
- 💿 DMG installer for easy distribution
- 🔔 macOS notifications on completion
- 🌐 Auto-opens browser on launch
- 📝 Comprehensive configuration system

### Changed
- Switched from Tkinter to web-based UI
- Improved thumbnail generation performance
- Better error handling and logging
- Optimized for py2app bundling

### Fixed
- Unicode handling in config files
- Browser launch in bundled app
- Thumbnail extraction from ORF files
- Memory usage with large image series

## [3.4.0] - 2026-03-10

### Added
- Tkinter GUI with image previews
- Thumbnail caching system
- Matrix layout for series selection
- Progress indicators

### Changed
- Improved series detection algorithm
- Better EXIF metadata handling

## [3.0.0] - 2026-03-05

### Added
- Initial release
- CLI interface
- Automatic series detection
- focus-stack integration
- SD card auto-detection

---

## Versioning

We use [SemVer](http://semver.org/) for versioning.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.
