#!/bin/bash
# Package wallpapers for GitHub release

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Packaging Wallpapers for Release...${NC}"
echo

SOURCE_DIR="$HOME/Pictures/dynamic_wallpapers"
OUTPUT_DIR="./wallpapers"
ARCHIVE_NAME="timewall-wallpapers-v1.0.0.zip"

if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: No wallpapers found in $SOURCE_DIR"
    exit 1
fi

WALLPAPER_COUNT=$(ls "$SOURCE_DIR"/*.heic 2>/dev/null | wc -l)

if [ $WALLPAPER_COUNT -eq 0 ]; then
    echo "Error: No .heic files found"
    exit 1
fi

echo "Found $WALLPAPER_COUNT wallpapers"
echo

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Copy wallpapers
echo "Copying wallpapers..."
cp "$SOURCE_DIR"/*.heic "$OUTPUT_DIR/"
echo -e "${GREEN}✓${NC} Copied $WALLPAPER_COUNT wallpapers"

# Create README for wallpaper package
cat > "$OUTPUT_DIR/README.txt" << 'EOF'
Timewall GUI - Dynamic Wallpaper Collection
============================================

This package contains 19 curated dynamic wallpapers for use with Timewall GUI.

INSTALLATION:

1. Extract this archive
2. Open Timewall GUI
3. Click "Import HEIC Files"
4. Select all .heic files from this folder
5. Enjoy!

Or manually:
cp *.heic ~/Pictures/dynamic_wallpapers/

WALLPAPERS:

These wallpapers vary in image count (1-96 images):
- 1 image: Static wallpapers
- 3-9 images: Simple day cycles  
- 16 images: Full solar-position based cycles
- 19-96 images: Time-based with many transitions

All wallpapers work with Timewall GUI's dynamic display system!

LICENSE:

These wallpapers are provided for personal use. Original wallpapers
are copyright Apple Inc. Community wallpapers have their own licenses.

For more information:
https://github.com/YOUR_USERNAME/timewall-gui

Enjoy your dynamic wallpapers! 🌅
EOF

echo -e "${GREEN}✓${NC} Created README"

# Create archive
echo
echo "Creating archive..."
if command -v zip >/dev/null 2>&1; then
    rm -f "$ARCHIVE_NAME"
    cd wallpapers && zip -r "../$ARCHIVE_NAME" *.heic README.txt && cd ..
    
    SIZE=$(ls -lh "$ARCHIVE_NAME" | awk '{print $5}')
    echo -e "${GREEN}✓${NC} Created: $ARCHIVE_NAME ($SIZE)"
else
    echo -e "${YELLOW}zip not found. Creating tar.gz instead...${NC}"
    ARCHIVE_NAME="timewall-wallpapers-v1.0.0.tar.gz"
    tar -czf "$ARCHIVE_NAME" -C wallpapers .
    
    SIZE=$(ls -lh "$ARCHIVE_NAME" | awk '{print $5}')
    echo -e "${GREEN}✓${NC} Created: $ARCHIVE_NAME ($SIZE)"
fi

echo
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}Packaging Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo

echo "Created:"
echo "  - $OUTPUT_DIR/ (folder with wallpapers)"
echo "  - $ARCHIVE_NAME (release archive)"
echo

echo "Next steps:"
echo "  1. Create GitHub release"
echo "  2. Upload $ARCHIVE_NAME as release asset"
echo "  3. Users can download and import!"
echo

echo "Archive contents:"
echo "  - $WALLPAPER_COUNT .heic files"
echo "  - README.txt"
echo "  - Total size: $SIZE"
