# Building the macOS App

## Prerequisites

```bash
# Install Xcode Command Line Tools
xcode-select --install

# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.8+
brew install python

# Install py2app
pip3 install py2app
```

## Quick Build

```bash
# Make scripts executable
chmod +x build.sh create_dmg.sh icon_generator.sh

# Build app
./build.sh

# Create DMG installer
./create_dmg.sh
```

## Step-by-Step Build

### 1. Prepare Icon (Optional)

```bash
# If you have a logo/image (1024x1024 PNG):
./icon_generator.sh path/to/your/logo.png

# This creates: resources/app_icon.icns
```

### 2. Install Dependencies

```bash
pip3 install -r requirements.txt
```

### 3. Build Application

```bash
python3 setup.py py2app
```

This creates:
- `dist/OM-1 Stacking Pipeline.app` - The standalone app

### 4. Test the App

```bash
open "dist/OM-1 Stacking Pipeline.app"
```

### 5. Create DMG Installer

```bash
./create_dmg.sh
```

This creates:
- `dist/OM-1-Stacking-Pipeline-4.1.0.dmg` - Installer for distribution

## Troubleshooting

### App won't open (Security Warning)

```bash
# Remove quarantine attribute
xattr -cr "dist/OM-1 Stacking Pipeline.app"

# Or right-click → Open
```

### Missing Dependencies

```bash
# Reinstall all dependencies
pip3 install --force-reinstall -r requirements.txt
```

### Build fails

```bash
# Clean and rebuild
rm -rf build dist
python3 setup.py py2app
```

## Code Signing (Optional)

For distribution without security warnings:

```bash
# Requires Apple Developer Account ($99/year)
codesign --deep --force --sign "Developer ID Application: Your Name" \
  "dist/OM-1 Stacking Pipeline.app"

# Notarize (requires Xcode)
xcrun notarytool submit "dist/OM-1-Stacking-Pipeline-4.1.0.dmg" \
  --apple-id "your@email.com" \
  --team-id "TEAMID" \
  --password "app-specific-password"
```

## Distribution

### For Testing

Share the `.app` file directly:
```bash
zip -r "OM-1-Stacking-Pipeline.zip" "dist/OM-1 Stacking Pipeline.app"
```

### For Public Release

Share the `.dmg` file:
```bash
# Upload to GitHub Releases, website, etc.
dist/OM-1-Stacking-Pipeline-4.1.0.dmg
```

## File Sizes

Expected sizes:
- `.app` bundle: ~50-80 MB
- `.dmg` installer: ~40-60 MB (compressed)

## Advanced Options

### Optimize Size

Edit `setup.py`:
```python
OPTIONS = {
    'optimize': 2,  # Maximum optimization
    'compressed': True,
    'strip': True,
}
```

### Include Additional Resources

Edit `setup.py`:
```python
DATA_FILES = [
    ('examples', ['examples/config_default.yaml']),
    ('docs', ['README.md', 'LICENSE']),
]
```

### Custom Launch Behavior

Edit `macro_stacking_web_v4.1.py`:
```python
# Change port, host, etc.
socketio.run(app, host='127.0.0.1', port=8080)
```
