#!/usr/bin/env python3
"""
Timewall GUI - User-friendly interface for Apple dynamic wallpapers on Linux
"""

import sys
import os
import json
import subprocess
import shutil
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QListWidget, QListWidgetItem, QGroupBox,
        QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QProgressBar, QMessageBox,
        QFileDialog, QTabWidget, QTextEdit, QGridLayout, QSlider,
        QFrame, QSizePolicy, QLineEdit
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt6.QtGui import QPixmap, QIcon, QFont, QImage, QKeySequence, QShortcut
except ImportError:
    print("Error: PyQt6 is not installed.")
    print("Please run the installer first: ./install.sh")
    sys.exit(1)


class WallpaperDownloader(QThread):
    """Thread for downloading wallpapers from Internet Archive"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, output_dir: Path):
        super().__init__()
        self.output_dir = output_dir
        
    def run(self):
        try:
            temp_dir = Path.home() / '.cache' / 'timewall-wallpapers'
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            self.progress.emit(5, "Downloading from Internet Archive...")
            
            # Download from Internet Archive (actual HEIC files, not Git LFS)
            archive_url = "https://archive.org/download/apple-dynamic-wallpapers/apple-dynamic-wallpapers.zip"
            zip_path = temp_dir / "wallpapers.zip"
            
            # Use wget to download with progress
            self.progress.emit(10, "Downloading archive (~2GB, please wait)...")
            
            result = subprocess.run(
                ['wget', '--progress=dot:giga', '-O', str(zip_path), archive_url],
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes timeout
            )
            
            if result.returncode != 0:
                # Try with curl as fallback
                self.progress.emit(10, "Trying alternative download method...")
                result = subprocess.run(
                    ['curl', '-L', '-o', str(zip_path), archive_url],
                    capture_output=True,
                    text=True,
                    timeout=1800
                )
                
                if result.returncode != 0:
                    self.finished.emit(False, "Download failed. Please check your internet connection.")
                    return
            
            self.progress.emit(50, "Download complete. Extracting...")
            
            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            self.progress.emit(70, "Finding HEIC files...")
            
            # Find all .heic files and copy them
            heic_files = list(temp_dir.rglob("*.heic"))
            total_files = len(heic_files)
            
            if total_files == 0:
                self.finished.emit(False, "No HEIC files found in archive")
                return
            
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            self.progress.emit(75, f"Copying {total_files} wallpapers...")
            
            copied = 0
            for i, heic_file in enumerate(heic_files):
                # Copy file, overwriting if exists
                dest = self.output_dir / heic_file.name
                shutil.copy2(heic_file, dest)
                copied += 1
                
                progress_pct = 75 + int((i / total_files) * 20)
                self.progress.emit(progress_pct, f"Copying wallpapers... ({copied}/{total_files})")
            
            # Clean up temp directory
            self.progress.emit(98, "Cleaning up...")
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            self.progress.emit(100, f"Downloaded {copied} wallpapers!")
            self.finished.emit(True, f"Successfully downloaded {copied} wallpapers")
            
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}")


class ImageExtractorThread(QThread):
    """Thread for extracting images from HEIC files"""
    progress = pyqtSignal(str)  # Status message
    finished = pyqtSignal(bool, list, str)  # Success, list of image paths, error message
    
    def __init__(self, timewall_path: Path, wallpaper_path: str):
        super().__init__()
        self.timewall_path = timewall_path
        self.wallpaper_path = wallpaper_path
        self._is_running = True
        
    def run(self):
        try:
            if not self._is_running:
                return
                
            self.progress.emit("Extracting images from HEIC file...")
            
            # Create temp directory
            temp_dir = Path(tempfile.mkdtemp(prefix="timewall_preview_"))
            
            # Extract images using timewall with error suppression
            result = subprocess.run(
                [str(self.timewall_path), 'unpack', self.wallpaper_path, str(temp_dir)],
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ, 'PYTHONUNBUFFERED': '1'}  # Unbuffered output
            )
            
            if not self._is_running:
                return
            
            # Check for libheif errors in stderr
            stderr_lower = result.stderr.lower() if result.stderr else ""
            if 'security limit exceeded' in stderr_lower:
                error = (
                    "libheif security limit exceeded.\n\n"
                    "Your libheif version has limits that are too low\n"
                    "for Apple's dynamic wallpapers.\n\n"
                    "Solutions:\n"
                    "1. Update libheif: sudo apt install libheif1\n"
                    "2. Or skip preview for this wallpaper\n\n"
                    "The wallpaper will still work for setting!"
                )
                self.finished.emit(False, [], error)
                return
            
            if result.returncode == 0:
                # timewall extracts as 0.png, 1.png, 2.png, etc.
                # Find all numbered PNG/JPG files
                image_files = []
                
                # Try numbered files (0.png, 1.png, etc.)
                for i in range(20):  # Check up to 20 images
                    if not self._is_running:
                        return
                    for ext in ['.png', '.jpg', '.jpeg']:
                        img_path = temp_dir / f"{i}{ext}"
                        if img_path.exists():
                            image_files.append(img_path)
                            break
                
                # Sort by number
                image_files.sort(key=lambda x: int(x.stem))
                
                if image_files:
                    image_paths = [str(f) for f in image_files]
                    self.finished.emit(True, image_paths, "")
                else:
                    # Fallback: look for any image files
                    all_images = list(temp_dir.glob("*.png")) + list(temp_dir.glob("*.jpg"))
                    if all_images:
                        image_paths = [str(f) for f in sorted(all_images)]
                        self.finished.emit(True, image_paths, "")
                    else:
                        error = "No images extracted. File may be corrupted or incompatible."
                        self.finished.emit(False, [], error)
            else:
                error = f"Extraction failed (exit code {result.returncode})"
                if result.stderr:
                    error += f"\n\nDetails: {result.stderr[:200]}"
                self.finished.emit(False, [], error)
                
        except subprocess.TimeoutExpired:
            self.finished.emit(False, [], "Extraction timed out (>60s)")
        except Exception as e:
            self.finished.emit(False, [], f"Error: {str(e)}")
    
    def stop(self):
        """Stop the thread gracefully"""
        self._is_running = False


class TimewallConfig:
    """Manage timewall configuration"""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self.load()
        
    def load(self) -> Dict:
        """Load configuration from file"""
        if not self.config_path.exists():
            return self.default_config()
        
        try:
            with open(self.config_path, 'r') as f:
                # Parse TOML manually (simple version)
                config = self.default_config()
                current_section = None
                
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.startswith('[') and line.endswith(']'):
                        current_section = line[1:-1]
                    elif '=' in line and current_section:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Parse value
                        if value.lower() == 'true':
                            value = True
                        elif value.lower() == 'false':
                            value = False
                        elif value.replace('.', '').replace('-', '').isdigit():
                            value = float(value) if '.' in value else int(value)
                        
                        if current_section not in config:
                            config[current_section] = {}
                        config[current_section][key] = value
                
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.default_config()
    
    def default_config(self) -> Dict:
        """Return default configuration"""
        return {
            'location': {
                'lat': 42.9634,
                'lon': -71.4547
            },
            'geoclue': {
                'enable': True,
                'cache_fallback': True,
                'prefer': False,
                'timeout': 1000
            },
            'daemon': {
                'update_interval_seconds': 600
            },
            'rotation': {
                'enabled': False,
                'change_daily': True,
                'wallpapers': []
            }
        }
    
    def save(self):
        """Save configuration to file"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.config_path, 'w') as f:
                f.write("# Timewall GUI Configuration\n\n")
                
                for section, values in self.config.items():
                    f.write(f"[{section}]\n")
                    for key, value in values.items():
                        if isinstance(value, bool):
                            value = str(value).lower()
                        elif isinstance(value, list):
                            # Convert list to TOML array
                            value = '[' + ', '.join(f'"{v}"' for v in value) + ']'
                        f.write(f"{key} = {value}\n")
                    f.write("\n")
        except Exception as e:
            print(f"Error saving config: {e}")


class TimewallGUI(QMainWindow):
    """Main GUI window"""
    
    def __init__(self):
        super().__init__()
        
        # Paths
        self.config_dir = Path.home() / '.config' / 'timewall-gui'
        self.wallpaper_dir = Path.home() / 'Pictures' / 'dynamic_wallpapers'
        self.config_path = self.config_dir / 'config.toml'
        self.state_path = self.config_dir / 'state.json'
        
        # Configuration
        self.config = TimewallConfig(self.config_path)
        self.current_wallpaper = None
        self.rotation_wallpapers = []
        
        # Load state
        self.load_state()
        
        # Check if timewall is installed
        self.timewall_path = self.find_timewall()
        
        # Setup UI
        self.init_ui()
        
        # Setup timer for daemon check
        self.daemon_timer = QTimer()
        self.daemon_timer.timeout.connect(self.check_daemon_status)
        self.daemon_timer.start(5000)  # Check every 5 seconds
        
        # Initial status check
        self.check_daemon_status()
        self.refresh_wallpaper_list()
        
        # Setup keyboard shortcuts
        self.setup_shortcuts()
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Enter - Set wallpaper
        set_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Return), self)
        set_shortcut.activated.connect(self.shortcut_set_wallpaper)
        
        # Delete - Delete wallpaper
        del_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        del_shortcut.activated.connect(self.shortcut_delete_wallpaper)
        
        # Ctrl+I - Import
        import_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
        import_shortcut.activated.connect(self.import_wallpapers)
        
        # Ctrl+R - Refresh
        refresh_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        refresh_shortcut.activated.connect(self.refresh_wallpaper_list)
        
        # Ctrl+F - Focus search
        search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        search_shortcut.activated.connect(self.focus_search)
        
        # Escape - Clear selection/search
        escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape_shortcut.activated.connect(self.clear_selection)
    
    def shortcut_set_wallpaper(self):
        """Handle Enter key to set wallpaper"""
        if self.wallpaper_list.currentItem() and self.set_button.isEnabled():
            self.set_wallpaper()
    
    def shortcut_delete_wallpaper(self):
        """Handle Delete key to delete wallpaper"""
        if self.wallpaper_list.currentItem() and self.delete_button.isEnabled():
            self.delete_wallpaper()
    
    def focus_search(self):
        """Focus the search box"""
        self.search_box.setFocus()
        self.search_box.selectAll()
    
    def clear_selection(self):
        """Clear wallpaper selection or search"""
        if self.search_box.text():
            self.search_box.clear()
        else:
            self.wallpaper_list.clearSelection()
            self.set_button.setEnabled(False)
            self.preview_button.setEnabled(False)
            self.info_button.setEnabled(False)
            self.delete_button.setEnabled(False)
    
    def find_timewall(self) -> Optional[Path]:
        """Find timewall executable"""
        # Check common locations
        locations = [
            Path.home() / '.cargo' / 'bin' / 'timewall',
            Path('/usr/local/bin/timewall'),
            Path('/usr/bin/timewall')
        ]
        
        for loc in locations:
            if loc.exists():
                return loc
        
        # Check PATH
        result = shutil.which('timewall')
        if result:
            return Path(result)
        
        return None
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Timewall GUI - Dynamic Wallpapers")
        self.setMinimumSize(900, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        
        # Status bar at top
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        status_layout = QHBoxLayout(status_frame)
        
        self.status_label = QLabel("Status: Checking...")
        self.status_label.setFont(QFont("", 10, QFont.Weight.Bold))
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.daemon_button = QPushButton("Start Daemon")
        self.daemon_button.clicked.connect(self.toggle_daemon)
        status_layout.addWidget(self.daemon_button)
        
        layout.addWidget(status_frame)
        
        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Tab 1: Wallpapers
        wallpaper_tab = self.create_wallpaper_tab()
        tabs.addTab(wallpaper_tab, "Wallpapers")
        
        # Tab 2: Settings
        settings_tab = self.create_settings_tab()
        tabs.addTab(settings_tab, "Settings")
        
        # Tab 3: Rotation
        rotation_tab = self.create_rotation_tab()
        tabs.addTab(rotation_tab, "Rotation")
        
        # Tab 4: About
        about_tab = self.create_about_tab()
        tabs.addTab(about_tab, "About")
    
    def create_wallpaper_tab(self) -> QWidget:
        """Create the wallpapers tab"""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        
        # Download section
        download_group = QGroupBox("Download Wallpapers")
        download_layout = QVBoxLayout(download_group)
        
        label = QLabel("Download the official macOS dynamic wallpaper collection:")
        download_layout.addWidget(label)
        
        button_layout = QHBoxLayout()
        self.download_button = QPushButton("Download Wallpapers")
        self.download_button.clicked.connect(self.download_wallpapers)
        button_layout.addWidget(self.download_button)
        
        self.import_button = QPushButton("Import HEIC Files")
        self.import_button.clicked.connect(self.import_wallpapers)
        button_layout.addWidget(self.import_button)
        
        self.manage_button = QPushButton("Manage Files")
        self.manage_button.clicked.connect(self.manage_wallpapers)
        button_layout.addWidget(self.manage_button)
        
        button_layout.addStretch()
        download_layout.addLayout(button_layout)
        
        self.download_progress = QProgressBar()
        self.download_progress.setVisible(False)
        download_layout.addWidget(self.download_progress)
        
        self.download_status = QLabel("")
        download_layout.addWidget(self.download_status)
        
        main_layout.addWidget(download_group)
        
        # Main content - split between list and preview
        content_layout = QHBoxLayout()
        
        # Left side - Wallpaper list
        list_group = QGroupBox("Available Wallpapers")
        list_layout = QVBoxLayout(list_group)
        
        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type to filter wallpapers...")
        self.search_box.textChanged.connect(self.filter_wallpapers)
        self.search_box.setClearButtonEnabled(True)
        search_layout.addWidget(self.search_box)
        
        list_layout.addLayout(search_layout)
        
        self.wallpaper_list = QListWidget()
        self.wallpaper_list.itemClicked.connect(self.on_wallpaper_selected)
        list_layout.addWidget(self.wallpaper_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.set_button = QPushButton("Set Wallpaper")
        self.set_button.clicked.connect(self.set_wallpaper)
        self.set_button.setEnabled(False)
        button_layout.addWidget(self.set_button)
        
        self.preview_button = QPushButton("Preview")
        self.preview_button.clicked.connect(self.preview_wallpaper)
        self.preview_button.setEnabled(False)
        button_layout.addWidget(self.preview_button)
        
        self.info_button = QPushButton("Info")
        self.info_button.clicked.connect(self.show_wallpaper_info)
        self.info_button.setEnabled(False)
        button_layout.addWidget(self.info_button)
        
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete_wallpaper)
        self.delete_button.setEnabled(False)
        self.delete_button.setStyleSheet("QPushButton { color: #ff6b6b; }")
        button_layout.addWidget(self.delete_button)
        
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_wallpaper_list)
        button_layout.addWidget(refresh_button)
        
        button_layout.addStretch()
        list_layout.addLayout(button_layout)
        
        content_layout.addWidget(list_group, stretch=1)
        
        # Right side - Preview panel
        preview_group = QGroupBox("Image Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Image display
        self.preview_label = QLabel("Select a wallpaper to preview")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setFrameStyle(QFrame.Shape.StyledPanel)
        self.preview_label.setStyleSheet("QLabel { background-color: #2a2a2a; color: #888; }")
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        preview_layout.addWidget(self.preview_label)
        
        # Slider for browsing images
        slider_layout = QVBoxLayout()
        
        self.preview_time_label = QLabel("Time of Day")
        self.preview_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slider_layout.addWidget(self.preview_time_label)
        
        self.preview_slider = QSlider(Qt.Orientation.Horizontal)
        self.preview_slider.setMinimum(0)
        self.preview_slider.setMaximum(15)
        self.preview_slider.setValue(0)
        self.preview_slider.setEnabled(False)
        self.preview_slider.valueChanged.connect(self.on_preview_slider_changed)
        slider_layout.addWidget(self.preview_slider)
        
        self.preview_index_label = QLabel("Image 1 of 16")
        self.preview_index_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        slider_layout.addWidget(self.preview_index_label)
        
        preview_layout.addLayout(slider_layout)
        
        content_layout.addWidget(preview_group, stretch=1)
        
        main_layout.addLayout(content_layout)
        
        # Store for extracted images
        self.current_preview_images = []
        self.current_preview_wallpaper = None
        
        return tab
    
    def create_settings_tab(self) -> QWidget:
        """Create the settings tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Location settings
        location_group = QGroupBox("Location")
        location_layout = QGridLayout(location_group)
        
        location_layout.addWidget(QLabel("Latitude:"), 0, 0)
        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90, 90)
        self.lat_spin.setDecimals(4)
        self.lat_spin.setSingleStep(0.0001)
        self.lat_spin.setValue(self.config.config['location']['lat'])
        location_layout.addWidget(self.lat_spin, 0, 1)
        
        location_layout.addWidget(QLabel("Longitude:"), 1, 0)
        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180, 180)
        self.lon_spin.setDecimals(4)
        self.lon_spin.setSingleStep(0.0001)
        self.lon_spin.setValue(self.config.config['location']['lon'])
        location_layout.addWidget(self.lon_spin, 1, 1)
        
        help_label = QLabel('<a href="https://www.latlong.net/">Find your coordinates</a>')
        help_label.setOpenExternalLinks(True)
        location_layout.addWidget(help_label, 2, 0, 1, 2)
        
        layout.addWidget(location_group)
        
        # GeoClue settings
        geoclue_group = QGroupBox("Automatic Location (GeoClue)")
        geoclue_layout = QVBoxLayout(geoclue_group)
        
        self.geoclue_check = QCheckBox("Enable automatic location detection")
        self.geoclue_check.setChecked(self.config.config['geoclue']['enable'])
        geoclue_layout.addWidget(self.geoclue_check)
        
        self.geoclue_prefer_check = QCheckBox("Prefer automatic over manual location")
        self.geoclue_prefer_check.setChecked(self.config.config['geoclue']['prefer'])
        geoclue_layout.addWidget(self.geoclue_prefer_check)
        
        layout.addWidget(geoclue_group)
        
        # Update interval
        interval_group = QGroupBox("Update Interval")
        interval_layout = QHBoxLayout(interval_group)
        
        interval_layout.addWidget(QLabel("Check for updates every:"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(60, 3600)
        self.interval_spin.setValue(self.config.config['daemon']['update_interval_seconds'])
        self.interval_spin.setSuffix(" seconds")
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        
        layout.addWidget(interval_group)
        
        # Save button
        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)
        
        layout.addStretch()
        
        return tab
    
    def create_rotation_tab(self) -> QWidget:
        """Create the rotation tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Enable rotation
        self.rotation_check = QCheckBox("Enable wallpaper rotation")
        self.rotation_check.setChecked(self.config.config.get('rotation', {}).get('enabled', False))
        layout.addWidget(self.rotation_check)
        
        # Rotation frequency
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Change wallpaper:"))
        self.rotation_combo = QComboBox()
        self.rotation_combo.addItems(["Daily", "Every 12 hours", "Every 6 hours", "Hourly"])
        freq_layout.addWidget(self.rotation_combo)
        freq_layout.addStretch()
        layout.addLayout(freq_layout)
        
        # Wallpaper selection for rotation
        select_group = QGroupBox("Wallpapers in Rotation")
        select_layout = QVBoxLayout(select_group)
        
        self.rotation_list = QListWidget()
        select_layout.addWidget(self.rotation_list)
        
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Wallpapers...")
        add_button.clicked.connect(self.add_to_rotation)
        button_layout.addWidget(add_button)
        
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_from_rotation)
        button_layout.addWidget(remove_button)
        
        button_layout.addStretch()
        select_layout.addLayout(button_layout)
        
        layout.addWidget(select_group)
        
        # Save button
        save_rotation_button = QPushButton("Save Rotation Settings")
        save_rotation_button.clicked.connect(self.save_rotation_settings)
        layout.addWidget(save_rotation_button)
        
        layout.addStretch()
        
        return tab
    
    def create_about_tab(self) -> QWidget:
        """Create the about tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setHtml("""
        <h2>Timewall GUI</h2>
        <p><b>Version:</b> 1.0.0</p>
        
        <p>A user-friendly interface for Apple dynamic wallpapers on Linux.</p>
        
        <h3>Features:</h3>
        <ul>
            <li>Browse and set macOS dynamic wallpapers</li>
            <li>Automatic wallpaper updates based on sun position</li>
            <li>Wallpaper rotation support</li>
            <li>One-click wallpaper downloads</li>
            <li>Location-based solar calculations</li>
        </ul>
        
        <h3>Credits:</h3>
        <ul>
            <li><b>timewall</b> by bcyran - Core wallpaper engine</li>
            <li><b>Apple Inc.</b> - Original dynamic wallpaper concept</li>
            <li><b>macOS Wallpaper Archive</b> - Community wallpaper collection</li>
        </ul>
        
        <h3>Links:</h3>
        <ul>
            <li><a href="https://github.com/bcyran/timewall">timewall GitHub</a></li>
            <li><a href="https://github.com/benediktkr/Deeeee-macOS-Wallpapers">Wallpaper Archive</a></li>
        </ul>
        
        <h3>Status:</h3>
        <p><b>Timewall installed:</b> {}</p>
        <p><b>Wallpaper directory:</b> {}</p>
        <p><b>Config directory:</b> {}</p>
        """.format(
            "Yes" if self.timewall_path else "No",
            self.wallpaper_dir,
            self.config_dir
        ))
        
        layout.addWidget(about_text)
        
        return tab
    
    def download_wallpapers(self):
        """Download wallpaper collection"""
        if not shutil.which('git'):
            QMessageBox.warning(
                self,
                "Git Not Found",
                "Git is required to download wallpapers. Please install git first."
            )
            return
        
        self.download_button.setEnabled(False)
        self.download_progress.setVisible(True)
        self.download_progress.setValue(0)
        
        self.downloader = WallpaperDownloader(self.wallpaper_dir)
        self.downloader.progress.connect(self.on_download_progress)
        self.downloader.finished.connect(self.on_download_finished)
        self.downloader.start()
    
    def import_wallpapers(self):
        """Import HEIC files - copy only, no thumbnail generation"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select HEIC Wallpaper Files",
            str(Path.home()),
            "HEIC Files (*.heic);;All Files (*)"
        )
        
        if not files:
            return
        
        self.wallpaper_dir.mkdir(parents=True, exist_ok=True)
        
        imported = 0
        for file_path in files:
            try:
                src = Path(file_path)
                dst = self.wallpaper_dir / src.name
                
                # Copy file only - no thumbnail generation
                shutil.copy2(src, dst)
                imported += 1
                
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Import Error",
                    f"Failed to import {src.name}:\n{str(e)}"
                )
        
        if imported > 0:
            QMessageBox.information(
                self,
                "Import Complete",
                f"Imported {imported} wallpaper(s).\n\n"
                f"Files are ready to use.\n"
                f"Thumbnails will generate when you select each wallpaper."
            )
            self.refresh_wallpaper_list()
    
    def delete_wallpaper(self):
        """Delete selected wallpaper with confirmation"""
        item = self.wallpaper_list.currentItem()
        if not item:
            return
        
        wallpaper_path = item.data(Qt.ItemDataRole.UserRole)
        wallpaper_name = Path(wallpaper_path).stem
        
        # Create custom dialog
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle("Delete Wallpaper")
        msg.setText(f"Delete '{wallpaper_name}'?")
        msg.setInformativeText("Choose how to delete this wallpaper:")
        
        # Add custom buttons
        remove_from_list = msg.addButton("Remove from List Only", QMessageBox.ButtonRole.ActionRole)
        delete_file = msg.addButton("Delete File from Disk", QMessageBox.ButtonRole.DestructiveRole)
        cancel = msg.addButton(QMessageBox.StandardButton.Cancel)
        
        msg.setDefaultButton(cancel)
        msg.exec()
        
        clicked = msg.clickedButton()
        
        if clicked == cancel:
            return
        
        # Always clean up thumbnails
        self.delete_thumbnails(wallpaper_name)
        
        # Delete file if requested
        if clicked == delete_file:
            try:
                Path(wallpaper_path).unlink()
                QMessageBox.information(
                    self,
                    "Deleted",
                    f"'{wallpaper_name}' has been deleted from disk.\nThumbnails have been removed."
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Delete Error",
                    f"Failed to delete file:\n{str(e)}"
                )
                return
        else:
            # Just removed from list
            QMessageBox.information(
                self,
                "Removed",
                f"'{wallpaper_name}' removed from list.\nThumbnails have been cleaned up.\n\nFile remains in:\n{wallpaper_path}"
            )
        
        # Refresh the list
        self.refresh_wallpaper_list()
        
        # Clear preview
        self.preview_label.setText("Select a wallpaper to preview")
        self.preview_slider.setEnabled(False)
        self.current_preview_images = []
        self.current_preview_wallpaper = None
    
    def delete_thumbnails(self, wallpaper_name: str):
        """Delete thumbnail cache for a wallpaper"""
        cache_dir = Path.home() / '.cache' / 'timewall-gui' / 'thumbnails' / wallpaper_name
        
        if cache_dir.exists():
            try:
                shutil.rmtree(cache_dir)
            except Exception as e:
                print(f"Warning: Failed to delete thumbnails: {e}")
    
    def manage_wallpapers(self):
        """Open file management dialog"""
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setWindowTitle("Manage Wallpapers")
        
        # Count wallpapers and thumbnails
        wallpaper_count = len(list(self.wallpaper_dir.glob("*.heic")))
        
        cache_dir = Path.home() / '.cache' / 'timewall-gui' / 'thumbnails'
        cached_wallpapers = len(list(cache_dir.iterdir())) if cache_dir.exists() else 0
        
        # Calculate cache size
        cache_size = 0
        if cache_dir.exists():
            for item in cache_dir.rglob('*'):
                if item.is_file():
                    cache_size += item.stat().st_size
        
        cache_size_mb = cache_size / (1024 * 1024)
        
        dialog.setText("File Management")
        dialog.setInformativeText(
            f"Wallpapers: {wallpaper_count}\n"
            f"Cached thumbnails: {cached_wallpapers}\n"
            f"Cache size: {cache_size_mb:.1f} MB\n\n"
            f"What would you like to do?"
        )
        
        # Add buttons
        clear_cache = dialog.addButton("Clear All Thumbnails", QMessageBox.ButtonRole.ActionRole)
        regenerate = dialog.addButton("Regenerate Thumbnails", QMessageBox.ButtonRole.ActionRole)
        open_folder = dialog.addButton("Open Wallpaper Folder", QMessageBox.ButtonRole.ActionRole)
        close_btn = dialog.addButton(QMessageBox.StandardButton.Close)
        
        dialog.exec()
        clicked = dialog.clickedButton()
        
        if clicked == clear_cache:
            self.clear_thumbnail_cache()
        elif clicked == regenerate:
            self.regenerate_all_thumbnails()
        elif clicked == open_folder:
            self.open_wallpaper_folder()
    
    def clear_thumbnail_cache(self):
        """Clear all thumbnail cache"""
        cache_dir = Path.home() / '.cache' / 'timewall-gui' / 'thumbnails'
        
        if not cache_dir.exists():
            QMessageBox.information(self, "Cache", "No cache to clear.")
            return
        
        reply = QMessageBox.question(
            self,
            "Clear Cache",
            "Delete all cached thumbnails?\n\nThey will be regenerated when you select wallpapers.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)
                QMessageBox.information(self, "Cache Cleared", "All thumbnails have been deleted.")
                
                # Clear current preview
                self.preview_label.setText("Select a wallpaper to preview")
                self.preview_slider.setEnabled(False)
                self.current_preview_images = []
                self.current_preview_wallpaper = None
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to clear cache:\n{str(e)}")
    
    def regenerate_all_thumbnails(self):
        """Regenerate thumbnails for all wallpapers"""
        wallpapers = list(self.wallpaper_dir.glob("*.heic"))
        
        if not wallpapers:
            QMessageBox.information(self, "No Wallpapers", "No wallpapers to process.")
            return
        
        reply = QMessageBox.question(
            self,
            "Regenerate Thumbnails",
            f"Regenerate thumbnails for {len(wallpapers)} wallpaper(s)?\n\n"
            f"This will delete existing thumbnails and create new ones.\n"
            f"This may take several minutes.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear cache first
            cache_dir = Path.home() / '.cache' / 'timewall-gui' / 'thumbnails'
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate for each wallpaper
            for wallpaper in wallpapers:
                self.generate_thumbnails_for_wallpaper(str(wallpaper))
            
            QMessageBox.information(
                self,
                "Regenerating",
                f"Regenerating thumbnails for {len(wallpapers)} wallpaper(s) in background.\n\n"
                f"Preview panel will load them as they're ready."
            )
    
    def open_wallpaper_folder(self):
        """Open wallpaper folder in file manager"""
        try:
            subprocess.Popen(['xdg-open', str(self.wallpaper_dir)])
        except Exception as e:
            QMessageBox.warning(
                self,
                "Error",
                f"Failed to open folder:\n{str(e)}\n\nFolder: {self.wallpaper_dir}"
            )
    
    def generate_thumbnails_for_wallpaper(self, wallpaper_path: str):
        """Generate thumbnails for a single wallpaper in background"""
        if not self.timewall_path:
            return
        
        wallpaper_name = Path(wallpaper_path).stem
        cache_dir = Path.home() / '.cache' / 'timewall-gui' / 'thumbnails' / wallpaper_name
        
        # Skip if thumbnails already exist
        if cache_dir.exists() and list(cache_dir.glob("*.jpg")):
            return
        
        # Start thumbnail generation in background thread
        try:
            thumb_generator = ImageExtractorThread(self.timewall_path, wallpaper_path)
            thumb_generator.finished.connect(
                lambda success, paths, err: self.on_thumbnail_generated(success, paths, wallpaper_name)
            )
            thumb_generator.start()
            
            # Store reference to prevent garbage collection
            if not hasattr(self, 'thumbnail_threads'):
                self.thumbnail_threads = []
            self.thumbnail_threads.append(thumb_generator)
            
        except Exception as e:
            print(f"Warning: Failed to start thumbnail generation for {wallpaper_name}: {e}")
    
    def on_thumbnail_generated(self, success: bool, image_paths: list, wallpaper_name: str):
        """Handle thumbnail generation completion"""
        if success and image_paths:
            # Move extracted images to cache
            cache_dir = Path.home() / '.cache' / 'timewall-gui' / 'thumbnails' / wallpaper_name
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                for img_path in image_paths:
                    src = Path(img_path)
                    dst = cache_dir / src.name
                    try:
                        shutil.copy2(src, dst)
                    except Exception as e:
                        print(f"Warning: Failed to copy thumbnail {src.name}: {e}")
            except Exception as e:
                print(f"Warning: Failed to cache thumbnails for {wallpaper_name}: {e}")
        
        # Clean up thread reference
        if hasattr(self, 'thumbnail_threads'):
            try:
                self.thumbnail_threads = [t for t in self.thumbnail_threads if t.isRunning()]
            except:
                pass
    
    def on_download_progress(self, percent: int, message: str):
        """Update download progress"""
        self.download_progress.setValue(percent)
        self.download_status.setText(message)
    
    def on_download_finished(self, success: bool, message: str):
        """Handle download completion"""
        self.download_button.setEnabled(True)
        self.download_progress.setVisible(False)
        
        if success:
            QMessageBox.information(self, "Download Complete", message)
            self.refresh_wallpaper_list()
        else:
            QMessageBox.warning(self, "Download Failed", message)
    
    def refresh_wallpaper_list(self):
        """Refresh the list of available wallpapers"""
        self.wallpaper_list.clear()
        
        if not self.wallpaper_dir.exists():
            return
        
        heic_files = sorted(self.wallpaper_dir.glob("*.heic"))
        
        for heic_file in heic_files:
            item = QListWidgetItem(heic_file.stem)
            item.setData(Qt.ItemDataRole.UserRole, str(heic_file))
            self.wallpaper_list.addItem(item)
        
        # Apply current search filter if exists
        if hasattr(self, 'search_box') and self.search_box.text():
            self.filter_wallpapers(self.search_box.text())
    
    def filter_wallpapers(self, text: str):
        """Filter wallpaper list based on search text"""
        search_text = text.lower()
        
        for i in range(self.wallpaper_list.count()):
            item = self.wallpaper_list.item(i)
            if item:
                item_text = item.text().lower()
                # Show item if search text is in name
                matches = search_text in item_text
                item.setHidden(not matches)
    
    def on_wallpaper_selected(self, item: QListWidgetItem):
        """Handle wallpaper selection"""
        self.set_button.setEnabled(True)
        self.preview_button.setEnabled(True)
        self.info_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        
        # Load preview images in background
        wallpaper_path = item.data(Qt.ItemDataRole.UserRole)
        self.load_preview_images(wallpaper_path)
    
    def set_wallpaper(self):
        """Set the selected wallpaper"""
        if not self.timewall_path:
            QMessageBox.warning(
                self,
                "Timewall Not Found",
                "Timewall is not installed. Please run the installer first."
            )
            return
        
        item = self.wallpaper_list.currentItem()
        if not item:
            return
        
        wallpaper_path = item.data(Qt.ItemDataRole.UserRole)
        
        try:
            result = subprocess.run(
                [str(self.timewall_path), 'set', wallpaper_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.current_wallpaper = wallpaper_path
                self.save_state()
                QMessageBox.information(self, "Success", f"Wallpaper set to: {item.text()}")
            else:
                QMessageBox.warning(self, "Error", f"Failed to set wallpaper:\n{result.stderr}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to set wallpaper:\n{str(e)}")
    
    def preview_wallpaper(self):
        """Preview the selected wallpaper"""
        if not self.timewall_path:
            return
        
        item = self.wallpaper_list.currentItem()
        if not item:
            return
        
        wallpaper_path = item.data(Qt.ItemDataRole.UserRole)
        
        try:
            # Remove --repeat flag so preview stops after one cycle
            subprocess.Popen(
                [str(self.timewall_path), 'preview', wallpaper_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            QMessageBox.information(
                self,
                "Preview Started",
                f"Previewing {item.text()}\n\n"
                "The wallpaper will cycle through all images once.\n"
                "This will take a few minutes to complete."
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to preview wallpaper:\n{str(e)}")
    
    def show_wallpaper_info(self):
        """Show information about the selected wallpaper"""
        if not self.timewall_path:
            return
        
        item = self.wallpaper_list.currentItem()
        if not item:
            return
        
        wallpaper_path = item.data(Qt.ItemDataRole.UserRole)
        
        try:
            result = subprocess.run(
                [str(self.timewall_path), 'info', wallpaper_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                QMessageBox.information(
                    self,
                    f"Info: {item.text()}",
                    result.stdout
                )
            else:
                QMessageBox.warning(self, "Error", f"Failed to get info:\n{result.stderr}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get info:\n{str(e)}")
    
    def save_settings(self):
        """Save settings to config file"""
        self.config.config['location']['lat'] = self.lat_spin.value()
        self.config.config['location']['lon'] = self.lon_spin.value()
        self.config.config['geoclue']['enable'] = self.geoclue_check.isChecked()
        self.config.config['geoclue']['prefer'] = self.geoclue_prefer_check.isChecked()
        self.config.config['daemon']['update_interval_seconds'] = self.interval_spin.value()
        
        self.config.save()
        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
        
        # Restart daemon if running
        if self.is_daemon_running():
            reply = QMessageBox.question(
                self,
                "Restart Daemon",
                "Settings changed. Restart daemon to apply changes?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.stop_daemon()
                self.start_daemon()
    
    def add_to_rotation(self):
        """Add wallpapers to rotation via multi-select dialog"""
        try:
            print("DEBUG: add_to_rotation called")
            
            # Get all available wallpapers
            available_wallpapers = []
            already_in_rotation = set()
            
            # Get wallpapers already in rotation
            for i in range(self.rotation_list.count()):
                already_in_rotation.add(self.rotation_list.item(i).text())
            
            print(f"DEBUG: Already in rotation: {already_in_rotation}")
            
            # Get all wallpapers
            if not self.wallpaper_dir.exists():
                QMessageBox.warning(self, "No Wallpapers", "No wallpapers found to add.")
                return
            
            for heic_file in sorted(self.wallpaper_dir.glob("*.heic")):
                name = heic_file.stem
                if name not in already_in_rotation:
                    available_wallpapers.append((name, str(heic_file)))
            
            print(f"DEBUG: Available wallpapers: {len(available_wallpapers)}")
            
            if not available_wallpapers:
                QMessageBox.information(
                    self,
                    "All Added",
                    "All available wallpapers are already in the rotation list."
                )
                return
            
            # Create multi-select dialog
            from PyQt6.QtWidgets import QDialog
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Add Wallpapers to Rotation")
            dialog.setMinimumWidth(500)
            dialog.setMinimumHeight(400)
            
            layout = QVBoxLayout(dialog)
            
            # Instructions
            label = QLabel("Select wallpapers to add to rotation:")
            layout.addWidget(label)
            
            # List widget with multi-select
            select_list = QListWidget()
            select_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
            
            for name, path in available_wallpapers:
                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, path)
                select_list.addItem(item)
            
            layout.addWidget(select_list)
            
            # Info label
            info_label = QLabel(f"{len(available_wallpapers)} wallpaper(s) available to add")
            layout.addWidget(info_label)
            
            # Buttons
            button_layout = QHBoxLayout()
            
            select_all_button = QPushButton("Select All")
            select_all_button.clicked.connect(select_list.selectAll)
            button_layout.addWidget(select_all_button)
            
            clear_button = QPushButton("Clear Selection")
            clear_button.clicked.connect(select_list.clearSelection)
            button_layout.addWidget(clear_button)
            
            button_layout.addStretch()
            
            add_button = QPushButton("Add Selected")
            add_button.clicked.connect(dialog.accept)
            add_button.setDefault(True)
            button_layout.addWidget(add_button)
            
            cancel_button = QPushButton("Cancel")
            cancel_button.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_button)
            
            layout.addLayout(button_layout)
            
            print("DEBUG: Showing dialog")
            
            # Show dialog
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_items = select_list.selectedItems()
                
                print(f"DEBUG: Selected {len(selected_items)} items")
                
                if not selected_items:
                    return
                
                # Add selected items to rotation list
                for item in selected_items:
                    rotation_item = QListWidgetItem(item.text())
                    rotation_item.setData(Qt.ItemDataRole.UserRole, item.data(Qt.ItemDataRole.UserRole))
                    self.rotation_list.addItem(rotation_item)
                
                QMessageBox.information(
                    self,
                    "Added",
                    f"Added {len(selected_items)} wallpaper(s) to rotation."
                )
        except Exception as e:
            print(f"DEBUG: Error in add_to_rotation: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to add wallpapers:\n{str(e)}")
    
    def remove_from_rotation(self):
        """Remove selected wallpaper from rotation"""
        item = self.rotation_list.currentItem()
        if item:
            self.rotation_list.takeItem(self.rotation_list.row(item))
    
    def save_rotation_settings(self):
        """Save rotation settings"""
        wallpapers = []
        for i in range(self.rotation_list.count()):
            item = self.rotation_list.item(i)
            wallpapers.append(item.data(Qt.ItemDataRole.UserRole))
        
        if 'rotation' not in self.config.config:
            self.config.config['rotation'] = {}
        
        self.config.config['rotation']['enabled'] = self.rotation_check.isChecked()
        self.config.config['rotation']['wallpapers'] = wallpapers
        
        self.config.save()
        QMessageBox.information(self, "Rotation Saved", "Rotation settings have been saved.")
    
    def toggle_daemon(self):
        """Toggle daemon on/off"""
        if self.is_daemon_running():
            self.stop_daemon()
        else:
            self.start_daemon()
    
    def is_daemon_running(self) -> bool:
        """Check if daemon is running"""
        try:
            result = subprocess.run(
                ['systemctl', '--user', 'is-active', 'timewall.service'],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except:
            return False
    
    def start_daemon(self):
        """Start the daemon"""
        try:
            subprocess.run(
                ['systemctl', '--user', 'start', 'timewall.service'],
                check=True
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to start daemon:\n{str(e)}")
    
    def stop_daemon(self):
        """Stop the daemon"""
        try:
            subprocess.run(
                ['systemctl', '--user', 'stop', 'timewall.service'],
                check=True
            )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to stop daemon:\n{str(e)}")
    
    def check_daemon_status(self):
        """Check and update daemon status"""
        if self.is_daemon_running():
            self.status_label.setText("Status: Daemon Running ✓")
            self.status_label.setStyleSheet("color: green;")
            self.daemon_button.setText("Stop Daemon")
        else:
            self.status_label.setText("Status: Daemon Stopped")
            self.status_label.setStyleSheet("color: red;")
            self.daemon_button.setText("Start Daemon")
    
    def load_preview_images(self, wallpaper_path: str):
        """Load preview images from cache or extract from HEIC file"""
        if not self.timewall_path or wallpaper_path == self.current_preview_wallpaper:
            return
        
        # Stop any running extraction thread
        if hasattr(self, 'extractor') and self.extractor.isRunning():
            self.extractor.stop()
            self.extractor.wait(1000)
        
        self.current_preview_wallpaper = wallpaper_path
        self.current_preview_images = []
        
        # Check for cached thumbnails first
        wallpaper_name = Path(wallpaper_path).stem
        cache_dir = Path.home() / '.cache' / 'timewall-gui' / 'thumbnails' / wallpaper_name
        
        if cache_dir.exists():
            # Load from cache (instant!)
            cached_images = sorted(cache_dir.glob("*.jpg")) + sorted(cache_dir.glob("*.png"))
            
            if cached_images:
                # Sort by number
                cached_images.sort(key=lambda x: int(x.stem) if x.stem.isdigit() else 0)
                self.current_preview_images = [str(f) for f in cached_images]
                self.preview_slider.setMaximum(len(self.current_preview_images) - 1)
                self.preview_slider.setValue(0)
                self.preview_slider.setEnabled(True)
                self.display_preview_image(0)
                return
        
        # No cache - extract from HEIC (slower)
        self.preview_label.setText("Extracting images...\n\nNote: If this fails with 'security limit exceeded',\nyour libheif version is too old.\nThe wallpaper will still work for setting!")
        self.preview_slider.setEnabled(False)
        self.preview_slider.setValue(0)
        
        # Start extraction in background thread
        self.extractor = ImageExtractorThread(self.timewall_path, wallpaper_path)
        self.extractor.progress.connect(self.on_extraction_progress)
        self.extractor.finished.connect(self.on_extraction_finished)
        self.extractor.start()
    
    def on_extraction_progress(self, message: str):
        """Update progress message"""
        self.preview_label.setText(message)
    
    def on_extraction_finished(self, success: bool, image_paths: list, error_msg: str):
        """Handle extraction completion"""
        if success and image_paths:
            self.current_preview_images = image_paths
            self.preview_slider.setMaximum(len(self.current_preview_images) - 1)
            self.preview_slider.setValue(0)
            self.preview_slider.setEnabled(True)
            
            # Display first image
            self.display_preview_image(0)
        else:
            if error_msg:
                self.preview_label.setText(f"Extraction failed:\n\n{error_msg}\n\nTry using the 'Preview' button\nfor full-screen preview instead")
            else:
                self.preview_label.setText("No images found\n\nTry using the 'Preview' button\nfor full-screen preview")
            self.current_preview_images = []
            self.preview_slider.setEnabled(False)
    
    def on_preview_slider_changed(self, value: int):
        """Handle preview slider change"""
        if self.current_preview_images:
            self.display_preview_image(value)
    
    def display_preview_image(self, index: int):
        """Display preview image at given index"""
        if not self.current_preview_images or index >= len(self.current_preview_images):
            return
        
        try:
            image_path = self.current_preview_images[index]
            pixmap = QPixmap(image_path)
            
            if not pixmap.isNull():
                # Scale to fit label while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
                
                # Update labels
                total = len(self.current_preview_images)
                self.preview_index_label.setText(f"Image {index + 1} of {total}")
                
                # Dynamic time labels based on actual image count
                time_label = self.get_time_label(index, total)
                self.preview_time_label.setText(time_label)
            else:
                self.preview_label.setText("Failed to load image")
                
        except Exception as e:
            self.preview_label.setText(f"Error displaying image:\n{str(e)}")
    
    def get_time_label(self, index: int, total: int) -> str:
        """Generate time label based on image index and total count"""
        if total == 1:
            return "Static Image"
        elif total == 2:
            return ["Light/Day Mode", "Dark/Night Mode"][index]
        elif total <= 4:
            # Simple day cycle
            labels = ["Night", "Morning", "Day", "Evening"]
            proportion = index / (total - 1) if total > 1 else 0
            label_index = int(proportion * (len(labels) - 1))
            return labels[label_index]
        elif total <= 8:
            # 8-point day cycle
            labels = ["Midnight", "Dawn", "Morning", "Midday", "Afternoon", "Sunset", "Dusk", "Night"]
            proportion = index / (total - 1) if total > 1 else 0
            label_index = int(proportion * (len(labels) - 1))
            return labels[label_index]
        elif total <= 16:
            # Standard solar cycle (most common)
            labels = [
                "Midnight/Late Night", "Deep Night", "Pre-Dawn", "Early Dawn",
                "Dawn/First Light", "Early Morning", "Morning", "Late Morning",
                "Midday", "Early Afternoon", "Afternoon", "Late Afternoon",
                "Golden Hour", "Sunset", "Dusk/Twilight", "Evening/Night"
            ]
            # Map current index to available labels
            proportion = index / (total - 1) if total > 1 else 0
            label_index = int(proportion * (len(labels) - 1))
            return labels[label_index]
        else:
            # Many images (like Pittsburgh with 96)
            # Divide day into 24 hours
            hours = 24
            proportion = index / (total - 1) if total > 1 else 0
            hour = int(proportion * hours)
            
            if hour == 0 or hour == 24:
                return "Midnight (12 AM)"
            elif hour < 12:
                return f"Morning ({hour} AM)"
            elif hour == 12:
                return "Noon (12 PM)"
            else:
                return f"Afternoon/Evening ({hour - 12} PM)"
    
    def closeEvent(self, event):
        """Handle application close - cleanup threads"""
        # Stop and wait for extraction thread
        if hasattr(self, 'extractor') and self.extractor.isRunning():
            try:
                self.extractor.stop()
                self.extractor.wait(2000)  # Wait up to 2 seconds
            except:
                pass
        
        # Stop and wait for downloader thread
        if hasattr(self, 'downloader') and self.downloader.isRunning():
            try:
                self.downloader.wait(2000)
            except:
                pass
        
        # Stop and wait for thumbnail generation threads
        if hasattr(self, 'thumbnail_threads'):
            for thread in self.thumbnail_threads:
                try:
                    if thread.isRunning():
                        thread.stop()
                        thread.wait(1000)
                except:
                    pass
        
        # Stop daemon timer
        if hasattr(self, 'daemon_timer'):
            try:
                self.daemon_timer.stop()
            except:
                pass
        
        # Save state
        try:
            self.save_state()
        except:
            pass
        
        event.accept()
    
    def load_state(self):
        """Load application state"""
        if not self.state_path.exists():
            return
        
        try:
            with open(self.state_path, 'r') as f:
                state = json.load(f)
                self.current_wallpaper = state.get('current_wallpaper')
        except:
            pass
    
    def save_state(self):
        """Save application state"""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            'current_wallpaper': self.current_wallpaper
        }
        
        with open(self.state_path, 'w') as f:
            json.dump(state, f, indent=2)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Timewall GUI")
    
    window = TimewallGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
