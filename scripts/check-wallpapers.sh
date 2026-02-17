#!/bin/bash
# Check wallpaper quality and detect issues

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

WALLPAPER_DIR="$HOME/Pictures/dynamic_wallpapers"

echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}  Wallpaper Quality Checker${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo

if [ ! -d "$WALLPAPER_DIR" ]; then
    echo "No wallpaper directory found"
    exit 1
fi

TOTAL=$(ls "$WALLPAPER_DIR"/*.heic 2>/dev/null | wc -l)
echo "Checking $TOTAL wallpapers..."
echo

GOOD=0
ISSUES=0
TEMP_DIR=$(mktemp -d)

for HEIC_FILE in "$WALLPAPER_DIR"/*.heic; do
    BASENAME=$(basename "$HEIC_FILE" .heic)
    
    # Get info
    INFO=$(timewall info "$HEIC_FILE" 2>/dev/null)
    
    # Extract to count images
    EXTRACT_DIR="$TEMP_DIR/extract"
    rm -rf "$EXTRACT_DIR"
    mkdir -p "$EXTRACT_DIR"
    
    timewall unpack "$HEIC_FILE" "$EXTRACT_DIR" >/dev/null 2>&1
    
    IMG_COUNT=$(ls "$EXTRACT_DIR"/*.png "$EXTRACT_DIR"/*.jpg 2>/dev/null | wc -l)
    
    # Check for issues
    ISSUE=""
    
    if [ $IMG_COUNT -lt 16 ]; then
        ISSUE="Only $IMG_COUNT images (expected 16)"
    elif [ $IMG_COUNT -gt 16 ]; then
        ISSUE="Too many images ($IMG_COUNT)"
    fi
    
    # Check schedule type
    if echo "$INFO" | grep -q "Schedule: solar"; then
        SCHEDULE="Solar"
    elif echo "$INFO" | grep -q "Schedule: time"; then
        SCHEDULE="Time"
    elif echo "$INFO" | grep -q "Schedule: appearance"; then
        SCHEDULE="Appearance"
    else
        SCHEDULE="Unknown"
    fi
    
    if [ -z "$ISSUE" ]; then
        echo -e "${GREEN}✓${NC} $BASENAME ($IMG_COUNT images, $SCHEDULE)"
        GOOD=$((GOOD + 1))
    else
        echo -e "${YELLOW}⚠${NC} $BASENAME - $ISSUE ($SCHEDULE)"
        ISSUES=$((ISSUES + 1))
    fi
done

rm -rf "$TEMP_DIR"

echo
echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${GREEN}Good: $GOOD${NC}"
echo -e "${YELLOW}Issues: $ISSUES${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"

if [ $ISSUES -gt 0 ]; then
    echo
    echo "Wallpapers with issues may:"
    echo "  • Have missing time stages"
    echo "  • Show images out of order"
    echo "  • Not transition smoothly"
    echo
    echo "These can be replaced by:"
    echo "  1. Using the Import button to add better versions"
    echo "  2. Downloading from other sources"
    echo "  3. Creating your own with wallpapper tool"
fi
