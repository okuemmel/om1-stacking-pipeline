#!/bin/bash
# Generate macOS app icon from source image

echo "🎨 OM-1 Stacking Pipeline - Icon Generator"
echo "=========================================="
echo ""

# Check if source image provided
if [ -z "$1" ]; then
    echo "Usage: ./icon_generator.sh <source_image.png>"
    echo ""
    echo "Requirements:"
    echo "  - Source image should be at least 1024x1024 pixels"
    echo "  - PNG format recommended"
    echo ""
    exit 1
fi

SOURCE_IMAGE="$1"

# Check if source exists
if [ ! -f "$SOURCE_IMAGE" ]; then
    echo "❌ Error: Source image not found: $SOURCE_IMAGE"
    exit 1
fi

# Create resources directory
mkdir -p resources/icon.iconset

echo "📐 Generating icon sizes..."

# Generate all required icon sizes
sips -z 16 16     "$SOURCE_IMAGE" --out resources/icon.iconset/icon_16x16.png
sips -z 32 32     "$SOURCE_IMAGE" --out resources/icon.iconset/icon_16x16@2x.png
sips -z 32 32     "$SOURCE_IMAGE" --out resources/icon.iconset/icon_32x32.png
sips -z 64 64     "$SOURCE_IMAGE" --out resources/icon.iconset/icon_32x32@2x.png
sips -z 128 128   "$SOURCE_IMAGE" --out resources/icon.iconset/icon_128x128.png
sips -z 256 256   "$SOURCE_IMAGE" --out resources/icon.iconset/icon_128x128@2x.png
sips -z 256 256   "$SOURCE_IMAGE" --out resources/icon.iconset/icon_256x256.png
sips -z 512 512   "$SOURCE_IMAGE" --out resources/icon.iconset/icon_256x256@2x.png
sips -z 512 512   "$SOURCE_IMAGE" --out resources/icon.iconset/icon_512x512.png
sips -z 1024 1024 "$SOURCE_IMAGE" --out resources/icon.iconset/icon_512x512@2x.png

echo "🔨 Converting to .icns format..."
iconutil -c icns resources/icon.iconset -o resources/app_icon.icns

# Cleanup
rm -rf resources/icon.iconset

echo ""
echo "✅ Icon created: resources/app_icon.icns"
echo ""
echo "Next step: ./build.sh"
