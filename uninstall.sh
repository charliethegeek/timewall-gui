#!/bin/bash
# Timewall GUI Uninstaller v1.0.0
# https://github.com/YOUR_USERNAME/timewall-gui

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║                                                            ║${NC}"
echo -e "${RED}║           Timewall GUI Uninstaller v1.0.0                  ║${NC}"
echo -e "${RED}║                                                            ║${NC}"
echo -e "${RED}║              ⚠️  WARNING: UNINSTALL ⚠️                      ║${NC}"
echo -e "${RED}║                                                            ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
echo

echo -e "${YELLOW}This will remove Timewall GUI and optionally your wallpapers.${NC}"
echo

# First confirmation
echo -e "${BOLD}Are you sure you want to uninstall Timewall GUI?${NC}"
read -p "Type 'yes' to continue: " CONFIRM1

if [ "$CONFIRM1" != "yes" ]; then
    echo "Uninstall cancelled."
    exit 0
fi

echo

# THE SCARY WALLPAPER WARNING
echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
echo -e "${RED}                                                           ${NC}"
echo -e "${RED}              ⚠️  WALLPAPER WARNING ⚠️                      ${NC}"
echo -e "${RED}                                                           ${NC}"
echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
echo

WALLPAPER_COUNT=$(ls "$HOME/Pictures/dynamic_wallpapers"/*.heic 2>/dev/null | wc -l)

if [ $WALLPAPER_COUNT -gt 0 ]; then
    echo -e "${YELLOW}You have ${BOLD}${WALLPAPER_COUNT} wallpapers${NC}${YELLOW} in:${NC}"
    echo -e "${BLUE}$HOME/Pictures/dynamic_wallpapers/${NC}"
    echo
    
    # Show first few wallpapers
    echo "Your wallpapers:"
    ls "$HOME/Pictures/dynamic_wallpapers"/*.heic 2>/dev/null | head -5 | xargs -n1 basename
    if [ $WALLPAPER_COUNT -gt 5 ]; then
        echo "... and $((WALLPAPER_COUNT - 5)) more"
    fi
    echo
    
    echo -e "${RED}${BOLD}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}${BOLD}║                                                           ║${NC}"
    echo -e "${RED}${BOLD}║  DO YOU WANT TO DELETE YOUR WALLPAPER COLLECTION?        ║${NC}"
    echo -e "${RED}${BOLD}║                                                           ║${NC}"
    echo -e "${RED}${BOLD}║  ⚠️  THIS CANNOT BE UNDONE! ⚠️                            ║${NC}"
    echo -e "${RED}${BOLD}║                                                           ║${NC}"
    echo -e "${RED}${BOLD}║  If you extracted these from macOS or curated this       ║${NC}"
    echo -e "${RED}${BOLD}║  collection, you probably want to keep them!              ║${NC}"
    echo -e "${RED}${BOLD}║                                                           ║${NC}"
    echo -e "${RED}${BOLD}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo
    
    echo -e "${YELLOW}Options:${NC}"
    echo "  [K] Keep wallpapers (recommended - you can import them later)"
    echo "  [D] DELETE wallpapers permanently"
    echo "  [C] Cancel uninstall"
    echo
    
    read -p "Your choice [K/D/C]: " WALLPAPER_CHOICE
    
    case "${WALLPAPER_CHOICE^^}" in
        K)
            DELETE_WALLPAPERS=false
            echo -e "${GREEN}Wallpapers will be kept in ~/Pictures/dynamic_wallpapers/${NC}"
            ;;
        D)
            echo
            echo -e "${RED}${BOLD}═══════════════════════════════════════════════════════════${NC}"
            echo -e "${RED}${BOLD}FINAL WARNING: You chose to DELETE your wallpapers!${NC}"
            echo -e "${RED}${BOLD}═══════════════════════════════════════════════════════════${NC}"
            echo
            echo -e "${RED}This will permanently delete ${WALLPAPER_COUNT} wallpapers.${NC}"
            echo
            read -p "Type 'DELETE MY WALLPAPERS' to confirm: " FINAL_CONFIRM
            
            if [ "$FINAL_CONFIRM" = "DELETE MY WALLPAPERS" ]; then
                DELETE_WALLPAPERS=true
                echo -e "${RED}Wallpapers will be deleted.${NC}"
            else
                echo "Confirmation text didn't match. Keeping wallpapers for safety."
                DELETE_WALLPAPERS=false
            fi
            ;;
        C|*)
            echo "Uninstall cancelled."
            exit 0
            ;;
    esac
else
    echo -e "${GREEN}No wallpapers found.${NC}"
    DELETE_WALLPAPERS=false
fi

echo
echo -e "${YELLOW}Proceeding with uninstall...${NC}"
echo

# Stop daemon
echo "Stopping daemon..."
systemctl --user stop timewall.service 2>/dev/null || true
systemctl --user disable timewall.service 2>/dev/null || true
echo -e "${GREEN}✓${NC} Daemon stopped"

# Remove GUI
echo "Removing GUI..."
rm -f "$HOME/.local/bin/timewall-gui"
echo -e "${GREEN}✓${NC} GUI removed"

# Remove desktop entry
echo "Removing desktop entry..."
rm -f "$HOME/.local/share/applications/timewall-gui.desktop"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi
echo -e "${GREEN}✓${NC} Desktop entry removed"

# Remove configs
echo "Removing configuration..."
rm -rf "$HOME/.config/timewall-gui"
rm -rf "$HOME/.config/timewall"
echo -e "${GREEN}✓${NC} Configuration removed"

# Remove systemd service
echo "Removing systemd service..."
rm -f "$HOME/.config/systemd/user/timewall.service"
systemctl --user daemon-reload
echo -e "${GREEN}✓${NC} Service removed"

# Remove thumbnail cache
echo "Removing thumbnail cache..."
rm -rf "$HOME/.cache/timewall-gui"
echo -e "${GREEN}✓${NC} Cache removed"

# Remove wallpapers if requested
if [ "$DELETE_WALLPAPERS" = true ]; then
    echo
    echo -e "${RED}Deleting wallpapers...${NC}"
    rm -rf "$HOME/Pictures/dynamic_wallpapers"
    echo -e "${RED}✓ Wallpapers deleted${NC}"
else
    echo
    echo -e "${GREEN}Keeping wallpapers in ~/Pictures/dynamic_wallpapers/${NC}"
fi

# Optionally remove timewall binary
echo
read -p "Remove timewall binary? (installed via cargo) [y/N]: " REMOVE_TIMEWALL
if [[ "${REMOVE_TIMEWALL^^}" = "Y" ]]; then
    if command -v cargo >/dev/null 2>&1; then
        cargo uninstall timewall 2>/dev/null || rm -f "$HOME/.cargo/bin/timewall"
        echo -e "${GREEN}✓${NC} timewall binary removed"
    fi
fi

# Final summary
echo
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║              Uninstall Complete                            ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo

echo "Removed:"
echo "  ✓ Timewall GUI"
echo "  ✓ Configuration files"
echo "  ✓ Systemd service"
echo "  ✓ Thumbnail cache"
if [ "$DELETE_WALLPAPERS" = true ]; then
    echo -e "  ${RED}✓ Wallpapers (deleted)${NC}"
else
    echo -e "  ${GREEN}✓ Wallpapers (kept in ~/Pictures/dynamic_wallpapers/)${NC}"
fi

echo
echo "Not removed (manual cleanup if desired):"
echo "  - Rust/Cargo (run: rustup self uninstall)"
echo "  - System packages (python3-pyqt6, libheif)"

if [ "$DELETE_WALLPAPERS" = false ]; then
    echo
    echo -e "${BLUE}Your wallpapers are still in:${NC}"
    echo -e "${BLUE}  ~/Pictures/dynamic_wallpapers/${NC}"
    echo
    echo "You can:"
    echo "  - Reinstall Timewall GUI and import them"
    echo "  - Use them with other tools"
    echo "  - Delete manually: rm -rf ~/Pictures/dynamic_wallpapers/"
fi

echo
echo "Thanks for using Timewall GUI!"
