# Timewall GUI

A user-friendly GUI for managing Apple dynamic wallpapers on Linux with KDE Plasma.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-Linux-blue)
![Desktop](https://img.shields.io/badge/desktop-KDE%20Plasma-blue)
![Python](https://img.shields.io/badge/python-3.6+-green)

## ✨ Features

- 🎨 **Visual Preview Panel** - Browse wallpaper images with interactive slider
- ⚡ **Instant Thumbnail Cache** - Fast previews without re-extraction
- 📥 **Easy Import** - Drag and drop HEIC files or use the import button
- 🌍 **Location-Aware** - Wallpapers change based on actual sun position
- 🔄 **Multi-Select Rotation** - Set up automatic wallpaper rotation
- ⌨️ **Keyboard Shortcuts** - Power user friendly navigation
- 🔍 **Search & Filter** - Find wallpapers in large collections
- 🗂️ **File Management** - Delete, organize, and manage your collection
- 🎛️ **Full Daemon Control** - Start, stop, configure automatic updates
- 🌅 **Dynamic Image Support** - Handles 1-96+ images per wallpaper

## 📸 Screenshots

<!-- Add screenshots here -->
*Main interface with preview panel and wallpaper list*

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/charliethegeek/timewall-gui.git
cd timewall-gui
chmod +x install.sh
./install.sh
```

The installer will:
- Install all required dependencies
- Install Rust and timewall
- Set up the GUI and desktop entry
- Configure the daemon
- Optionally install the wallpaper collection

### First Run

1. Launch Timewall GUI from your application menu or run:
   ```bash
   timewall-gui
   ```

2. Import wallpapers:
   - Click "Import HEIC Files" to add your own
   - Or download the wallpaper collection (see below)

3. Select a wallpaper and click "Set Wallpaper"

4. (Optional) Start the daemon for automatic updates:
   - Go to Daemon tab → Click "Start Daemon"

## 📦 Getting Wallpapers

### Option 1: Official Collection

Download our curated collection of 19 verified wallpapers:
- [Download from Releases](https://github.com/charliethegeek/timewall-gui/releases/latest)

Extract and import via the GUI's "Import HEIC Files" button.

### Option 2: Extract from macOS

If you have access to a Mac:

```bash
# On macOS, run:
./scripts/extract-from-mac.sh

# Copy the exported wallpapers to your Linux machine
# Then import via GUI
```

### Option 3: Download from Community

- [Dynamic Wallpaper Club](https://dynamicwallpaper.club/gallery/) - Community wallpapers
- [24 Hour Wallpaper](https://www.jetsoncreative.com/mojave) - Professional quality

## 🎮 Usage

### Basic Operations

**Set a wallpaper:**
1. Select wallpaper from list
2. (Optional) Preview with slider
3. Click "Set Wallpaper"

**Enable rotation:**
1. Go to Rotation tab
2. Check "Enable wallpaper rotation"
3. Choose frequency (Daily, 12h, 6h, Hourly)
4. Click "Add Wallpapers..." → Select All
5. Click "Save Rotation Settings"

**Start daemon:**
1. Go to Daemon tab
2. Click "Start Daemon"
3. Wallpaper will update automatically throughout the day!

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `↑` `↓` | Navigate wallpaper list |
| `Enter` | Set selected wallpaper |
| `Delete` | Delete selected wallpaper |
| `Ctrl+F` | Focus search box |
| `Ctrl+I` | Import wallpapers |
| `Ctrl+R` | Refresh list |
| `Escape` | Clear selection/search |

## 🔧 Advanced

### Manual Configuration

Edit `~/.config/timewall/config.toml`:

```toml
[location]
lat = 42.9634  # Your latitude
lon = -71.4547  # Your longitude

[daemon]
update_interval_seconds = 600  # Check every 10 minutes

[setter]
command = ['plasma-apply-wallpaperimage', '%f']
```

### Command Line

```bash
# Set wallpaper manually
timewall set ~/Pictures/dynamic_wallpapers/YourWallpaper.heic

# View wallpaper info
timewall info ~/Pictures/dynamic_wallpapers/YourWallpaper.heic

# Start daemon manually
systemctl --user start timewall.service

# Check daemon status
systemctl --user status timewall.service
```

## 🛠️ Requirements

- **OS:** Linux with KDE Plasma 6 (or Plasma 5 with modifications)
- **Python:** 3.6+
- **Dependencies:**
  - PyQt6
  - libheif >= 1.16
  - Rust/Cargo (for timewall)
  - plasma-apply-wallpaperimage (KDE)

## 🐛 Known Limitations

### Preview Panel May Fail

Due to libheif security limits, thumbnail extraction may fail for some complex Apple wallpapers with the error:

```
Security limit exceeded: ipma box wants to define properties for 1159 items,
but the security limit has been set to 1000 items
```

**This does NOT affect:**
- ✅ Setting wallpapers (works perfectly)
- ✅ Daemon operation (works perfectly)
- ✅ Automatic wallpaper changes (works perfectly)

**Workaround:**
- Use "Set Wallpaper" directly (no preview needed)
- Full-screen "Preview" button may still work
- Update libheif to newer version if available

## 🗑️ Uninstall

```bash
chmod +x uninstall.sh
./uninstall.sh
```

The uninstaller will:
- Ask if you want to keep your wallpaper collection
- Remove all GUI components
- Clean up configuration files
- Stop the daemon
- Give you options for keeping/removing wallpapers

**⚠️ WARNING:** The uninstaller has a very scary wallpaper deletion warning! 
Your collection will be safe unless you explicitly choose to delete it.

## 📚 Documentation

- [Installation Guide](docs/INSTALLATION.md) - Detailed installation instructions
- [User Guide](docs/USAGE.md) - Complete feature documentation
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [FAQ](docs/FAQ.md) - Frequently asked questions

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

- **[timewall](https://github.com/bcyran/timewall)** by bcyran - The core wallpaper engine
- **Apple Inc.** - Original dynamic wallpaper concept
- **Wallpaper sources:**
  - Official Apple wallpapers (extracted from macOS)
  - [Dynamic Wallpaper Club](https://dynamicwallpaper.club/)
  - Community contributions

## 💬 Support

- **Issues:** [GitHub Issues](https://github.com/YOUR_USERNAME/timewall-gui/issues)
- **Discussions:** [GitHub Discussions](https://github.com/YOUR_USERNAME/timewall-gui/discussions)
- **timewall docs:** [bcyran/timewall](https://github.com/bcyran/timewall)

## 🎯 Roadmap

- [ ] Support for GNOME, XFCE, other desktop environments
- [ ] Built-in wallpaper editor
- [ ] Cloud sync for settings
- [ ] Themes for the GUI
- [ ] AppImage/Flatpak packaging

## ⭐ Star History

If you find this project useful, please consider giving it a star!

---

**Enjoy your dynamic wallpapers!** 🌅

Made with ❤️ for the Linux community
