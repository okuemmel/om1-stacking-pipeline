#!/bin/bash
set -e

echo "🔬 OM-1 Stacking Pipeline - App Builder v2.3"
echo "============================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}❌ macOS required${NC}"
    exit 1
fi

echo "🐍 Checking Python..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "   ${GREEN}✓ Python $python_version${NC}"

echo ""
echo "📦 Installing build tools..."
python3 -m pip install --quiet "setuptools<70" wheel py2app

echo "📦 Installing dependencies..."
python3 -m pip install --quiet flask flask-socketio pillow pyyaml python-socketio

echo -e "${GREEN}✓ Dependencies installed${NC}"

echo ""
echo "🧹 Cleaning..."
rm -rf build dist *.egg-info
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
echo -e "${GREEN}✓ Clean${NC}"

# Icon
mkdir -p resources
if [ ! -f "resources/app_icon.icns" ]; then
    echo -e "${YELLOW}⚠️  Creating icon...${NC}"
    
    python3 << 'PYTHON_ICON'
from PIL import Image, ImageDraw
import os
size = 1024
img = Image.new('RGB', (size, size), '#667eea')
draw = ImageDraw.Draw(img)
draw.rectangle([300, 800, 700, 900], fill='#2c3e50')
draw.rectangle([450, 400, 550, 800], fill='#34495e')
draw.ellipse([400, 200, 600, 400], fill='#3498db')
draw.rectangle([470, 100, 530, 200], fill='#34495e')
os.makedirs('resources', exist_ok=True)
img.save('resources/temp_icon.png')
PYTHON_ICON

    mkdir -p resources/icon.iconset
    for size in 16 32 64 128 256 512; do
        sips -z $size $size resources/temp_icon.png \
            --out resources/icon.iconset/icon_${size}x${size}.png &>/dev/null
    done
    iconutil -c icns resources/icon.iconset -o resources/app_icon.icns
    rm -rf resources/icon.iconset resources/temp_icon.png
    echo -e "${GREEN}✓ Icon created${NC}"
fi

echo ""
echo "🏗️  Building app..."
echo ""

# Filter warnings (fixed grep patterns)
python3 setup.py py2app 2>&1 | \
    grep -v "SetuptoolsDeprecationWarning" | \
    grep -v "License classifiers" | \
    grep -v "\*\*\*\*\*\*\*\*" | \
    grep -v "!!" || true

# Check build status from PIPESTATUS
BUILD_STATUS=${PIPESTATUS[0]}

if [ $BUILD_STATUS -eq 0 ] && [ -d "dist/OM-1 Stacking Pipeline.app" ]; then
    echo ""
    echo -e "${GREEN}✅ Build successful!${NC}"
    echo ""
    
    APP_PATH="dist/OM-1 Stacking Pipeline.app"
    app_size=$(du -sh "$APP_PATH" | awk '{print $1}')
    
    echo "📍 $APP_PATH"
    echo "📦 Size: $app_size"
    
    echo ""
    echo "🔧 Fixing permissions..."
    xattr -cr "$APP_PATH" 2>/dev/null || true
    chmod +x "$APP_PATH/Contents/MacOS/"* 2>/dev/null || true
    
    echo -e "${GREEN}✓ App ready${NC}"
    
    echo ""
    echo -e "${GREEN}🎉 Build complete!${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Next steps:"
    echo ""
    echo "  Test:     open '$APP_PATH'"
    echo "  Install:  cp -r '$APP_PATH' /Applications/"
    echo "  Package:  ./create_dmg.sh"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Auto-launch
    open "$APP_PATH" &
else
    echo ""
    echo -e "${RED}❌ Build failed!${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Run: pip3 install 'setuptools<70' --force-reinstall"
    echo "  2. Check: python3 setup.py py2app (manual)"
    echo "  3. Delete pyproject.toml if issues persist"
    echo ""
    exit 1
fi
