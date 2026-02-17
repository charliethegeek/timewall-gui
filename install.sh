#!/bin/bash
# Timewall GUI Installer v1.0.0
# https://github.com/YOUR_USERNAME/timewall-gui

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║           Timewall GUI Installer v1.0.0                    ║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}║  Apple Dynamic Wallpapers for Linux/KDE                    ║${NC}"
echo -e "${BLUE}║                                                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo

# Detect package manager
if command -v apt >/dev/null 2>&1; then
    PKG_MGR="apt"
elif command -v dnf >/dev/null 2>&1; then
    PKG_MGR="dnf"
elif command -v pacman >/dev/null 2>&1; then
    PKG_MGR="pacman"
else
    PKG_MGR="unknown"
fi

print_step() {
    echo
    echo -e "${YELLOW}━━━ $1 ━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check Python 3
if ! command -v python3 >/dev/null 2>&1; then
    print_error "Python 3 is required but not found"
    exit 1
fi

# Step 1: Install system dependencies
print_step "Step 1: Installing system dependencies"

case $PKG_MGR in
    apt)
        echo "Using apt package manager..."
        sudo apt update
        sudo apt install -y python3-pyqt6 libheif1 curl wget
        ;;
    dnf)
        echo "Using dnf package manager..."
        sudo dnf install -y python3-pyqt6 libheif curl wget
        ;;
    pacman)
        echo "Using pacman package manager..."
        sudo pacman -S --noconfirm python-pyqt6 libheif curl wget
        ;;
    *)
        echo -e "${YELLOW}Unknown package manager. Please install manually:${NC}"
        echo "  - PyQt6 (python3-pyqt6 or via pip)"
        echo "  - libheif"
        echo "  - curl, wget"
        read -p "Continue anyway? (y/n) " -r
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 1
        ;;
esac

print_success "System dependencies installed"

# Step 2: Install Rust/Cargo
print_step "Step 2: Installing Rust (for timewall)"

if ! command -v cargo >/dev/null 2>&1; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
    print_success "Rust installed"
else
    print_success "Rust already installed"
fi

export PATH="$HOME/.cargo/bin:$PATH"

# Step 3: Install timewall
print_step "Step 3: Installing timewall"

if ! command -v timewall >/dev/null 2>&1; then
    echo "Installing timewall via cargo..."
    cargo install timewall
    print_success "timewall installed"
else
    print_success "timewall already installed"
fi

# Step 4: Create directories
print_step "Step 4: Creating directories"

mkdir -p "$HOME/.local/bin"
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.config/timewall"
mkdir -p "$HOME/.config/timewall-gui"
mkdir -p "$HOME/.config/systemd/user"
mkdir -p "$HOME/Pictures/dynamic_wallpapers"
mkdir -p "$HOME/.cache/timewall-gui/thumbnails"

print_success "Directories created"

# Step 5: Install GUI
print_step "Step 5: Installing Timewall GUI"

if [ ! -f "timewall-gui.py" ]; then
    print_error "timewall-gui.py not found in current directory"
    echo "Please run this script from the timewall-gui directory"
    exit 1
fi

cp timewall-gui.py "$HOME/.local/bin/timewall-gui"
chmod +x "$HOME/.local/bin/timewall-gui"

print_success "GUI installed to ~/.local/bin/timewall-gui"

# Step 6: Create desktop entry
print_step "Step 6: Creating desktop entry"

cat > "$HOME/.local/share/applications/timewall-gui.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Timewall GUI
GenericName=Dynamic Wallpaper Manager
Comment=Manage Apple dynamic wallpapers on Linux
Exec=sh -c 'python3 $HOME/.local/bin/timewall-gui'
Icon=preferences-desktop-wallpaper
Terminal=false
Categories=Settings;DesktopSettings;Utility;Qt;
Keywords=wallpaper;background;dynamic;macos;heic;
StartupNotify=true
StartupWMClass=timewall-gui
EOF

chmod +x "$HOME/.local/share/applications/timewall-gui.desktop"

# Update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

# Refresh KDE menu
if command -v kbuildsycoca6 >/dev/null 2>&1; then
    kbuildsycoca6 >/dev/null 2>&1 &
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
    kbuildsycoca5 >/dev/null 2>&1 &
fi

print_success "Desktop entry created"

# Step 7: Detect location
print_step "Step 7: Configuring location"

LAT=42.9634
LON=-71.4547

if command -v curl >/dev/null 2>&1; then
    echo "Attempting to detect your location..."
    LOCATION=$(curl -s --max-time 5 https://ipapi.co/json/ 2>/dev/null || echo "{}")
    DETECTED_LAT=$(echo "$LOCATION" | grep -oP '"latitude":\s*\K[-0-9.]+' 2>/dev/null || echo "")
    DETECTED_LON=$(echo "$LOCATION" | grep -oP '"longitude":\s*\K[-0-9.]+' 2>/dev/null || echo "")
    
    if [ -n "$DETECTED_LAT" ] && [ -n "$DETECTED_LON" ]; then
        LAT=$DETECTED_LAT
        LON=$DETECTED_LON
        echo "Detected: $LAT, $LON"
    else
        echo "Could not detect location, using default (Manchester, NH)"
    fi
fi

# Step 8: Create timewall config
print_step "Step 8: Creating timewall configuration"

cat > "$HOME/.config/timewall/config.toml" << EOF
[location]
lat = $LAT
lon = $LON

[geoclue]
enable = true
cache_fallback = true
prefer = false
timeout = 1000

[daemon]
update_interval_seconds = 600

[setter]
command = ['plasma-apply-wallpaperimage', '%f']
quiet = true
overlap = 0
EOF

print_success "Configuration created"

# Step 9: Create systemd service
print_step "Step 9: Creating systemd service"

cat > "$HOME/.config/systemd/user/timewall.service" << EOF
[Unit]
Description=Timewall Dynamic Wallpaper Daemon
After=graphical-session.target

[Service]
Type=simple
ExecStart=$HOME/.cargo/bin/timewall set --daemon
Restart=on-failure
RestartSec=10
Environment="PATH=$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload

print_success "Systemd service created"

# Step 10: Update PATH
print_step "Step 10: Updating PATH"

if ! grep -q '.local/bin.*PATH' "$HOME/.bashrc" 2>/dev/null; then
    echo '' >> "$HOME/.bashrc"
    echo '# Added by Timewall GUI installer' >> "$HOME/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"' >> "$HOME/.bashrc"
    print_success "PATH updated in .bashrc"
fi

export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# Step 11: Copy wallpapers if available
print_step "Step 11: Installing wallpapers"

if [ -d "wallpapers" ] && [ "$(ls -A wallpapers/*.heic 2>/dev/null | wc -l)" -gt 0 ]; then
    WALLPAPER_COUNT=$(ls wallpapers/*.heic | wc -l)
    echo "Found $WALLPAPER_COUNT wallpapers to install..."
    cp wallpapers/*.heic "$HOME/Pictures/dynamic_wallpapers/"
    print_success "Installed $WALLPAPER_COUNT wallpapers"
else
    echo -e "${YELLOW}No wallpapers found in ./wallpapers/${NC}"
    echo "You can:"
    echo "  1. Download from releases page"
    echo "  2. Use Import button in GUI to add your own"
fi

# Final summary
echo
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║              Installation Complete! 🎉                     ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo

echo -e "${YELLOW}Next Steps:${NC}"
echo
echo "1. Launch Timewall GUI:"
echo -e "   ${BLUE}timewall-gui${NC}"
echo "   Or search for 'Timewall GUI' in your application menu"
echo
echo "2. Import wallpapers (if not done automatically):"
echo "   - Click 'Import HEIC Files' button"
echo "   - Or manually copy .heic files to ~/Pictures/dynamic_wallpapers/"
echo
echo "3. Select a wallpaper and click 'Set Wallpaper'"
echo
echo "4. Start the daemon for automatic updates:"
echo "   - Click 'Start Daemon' in the Daemon tab"
echo "   - Or run: systemctl --user start timewall.service"
echo
echo "5. (Optional) Enable auto-start on login:"
echo "   - systemctl --user enable timewall.service"
echo
echo -e "${BLUE}Enjoy your dynamic wallpapers! 🌅${NC}"
echo
echo "For help: https://github.com/YOUR_USERNAME/timewall-gui"
