#!/bin/bash
# Create DMG installer for OM-1 Stacking Pipeline

set -e

echo "💿 Creating DMG Installer"
echo "========================="
echo ""

APP_NAME="OM-1 Stacking Pipeline"
VERSION="4.1.0"
DMG_NAME="OM-1-Stacking-Pipeline-${VERSION}"
APP_PATH="dist/${APP_NAME}.app"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if app exists
if [ ! -d "$APP_PATH" ]; then
    echo -e "${RED}❌ Error: App not found at $APP_PATH${NC}"
    echo "   Run ./build.sh first!"
    exit 1
fi

# Create temporary DMG directory
echo "📁 Creating DMG structure..."
DMG_DIR="dmg_temp"
rm -rf "$DMG_DIR"
mkdir -p "$DMG_DIR"

# Copy app to DMG directory
echo "📦 Copying application..."
cp -r "$APP_PATH" "$DMG_DIR/"

# Create Applications symlink
echo "🔗 Creating Applications symlink..."
ln -s /Applications "$DMG_DIR/Applications"

# Create README
echo "📝 Creating README..."
cat > "$DMG_DIR/README.txt" << EOF
OM-1 Macro Focus Stacking Pipeline v${VERSION}
==============================================

Installation:
1. Drag "OM-1 Stacking Pipeline.app" to the Applications folder
2. Double-click to launch
3. Browser will open automatically at http://localhost:8080

Requirements:
- macOS 10.13 or later
- ImageMagick (install via: brew install imagemagick)
- exiftool (install via: brew install exiftool)
- Helicon Focus (download from heliconsoft.com)

First Launch:
- Right-click the app and select "Open" (macOS security)
- Or: System Preferences → Security → "Open Anyway"

Configuration:
- Config file: ~/.stacking_config.yaml
- Edit settings before first use

Support:
- GitHub: https://github.com/okuemmel/om1-stacking-pipeline
- Issues: https://github.com/okuemmel/om1-stacking-pipeline/issues

© 2026 Oliver Kümmel - MIT License
EOF

# Create background image (optional)
# You can replace this with a custom background
mkdir -p "$DMG_DIR/.background"

# Create DMG
echo ""
echo "🔨 Creating DMG file..."
rm -f "dist/${DMG_NAME}.dmg"

hdiutil create -volname "$APP_NAME" \
    -srcfolder "$DMG_DIR" \
    -ov \
    -format UDZO \
    -imagekey zlib-level=9 \
    "dist/${DMG_NAME}.dmg"

if [ $? -eq 0 ]; then
    # Cleanup
    rm -rf "$DMG_DIR"
    
    # Get DMG size
    dmg_size=$(du -sh "dist/${DMG_NAME}.dmg" | awk '{print $1}')
    
    echo ""
    echo -e "${GREEN}✅ DMG created successfully!${NC}"
    echo ""
    echo "📍 Location: dist/${DMG_NAME}.dmg"
    echo "📦 Size: $dmg_size"
    echo ""
    echo "🧪 Testing DMG..."
    hdiutil verify "dist/${DMG_NAME}.dmg" > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ DMG verification passed${NC}"
    else
        echo -e "${YELLOW}⚠️  DMG verification warning (might still work)${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}🎉 All done!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Test DMG: open dist/${DMG_NAME}.dmg"
    echo "  2. Distribute to users"
    echo "  3. Optional: Code sign with Apple Developer account"
    echo ""
else
    echo -e "${RED}❌ DMG creation failed!${NC}"
    rm -rf "$DMG_DIR"
    exit 1
fi
