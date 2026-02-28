"""
Nuitka Pro Compiler - Advanced Python to Executable Compiler GUI
Version: 2.0.0
Author: Professional Build System
Description: Fully automated Nuitka compiler with intelligent import handling,
             comprehensive error catching, and real-time logging.
"""

import sys
import os
import subprocess
import threading
import queue
import json
import re
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import traceback
import logging
from logging.handlers import RotatingFileHandler

# Try importing PyQt5 with fallback
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QTextEdit, QFileDialog, QLabel, QProgressBar,
        QMessageBox, QGroupBox, QCheckBox, QComboBox, QSpinBox,
        QTabWidget, QSplitter, QStatusBar, QMenuBar, QMenu, QAction,
        QDialog, QDialogButtonBox, QLineEdit, QFormLayout
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
    from PyQt5.QtGui import QFont, QTextCursor, QIcon, QColor, QPalette
    PYQT5_AVAILABLE = True
except ImportError:
    PYQT5_AVAILABLE = False
    print("ERROR: PyQt5 is required. Install with: pip install PyQt5")
    sys.exit(1)

# Configure logging
LOG_FILE = "nuitka_compiler.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CompilerWorker(QThread):
    """Handles compilation in a separate thread with comprehensive error handling"""
    
    output_signal = pyqtSignal(str, str)  # message, type (info, error, warning, success)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, main_file: str, config: Dict[str, Any]):
        super().__init__()
        self.main_file = main_file
        self.config = config
        self.process = None
        self.is_running = True
        self.error_log = []
        
    def stop(self):
        """Safely stop the compilation process"""
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                except:
                    pass
    
    def run(self):
        """Main compilation process with comprehensive error handling"""
        try:
            self.output_signal.emit("Starting Nuitka compilation process...", "info")
            self.output_signal.emit(f"Main file: {self.main_file}", "info")
            self.output_signal.emit(f"Configuration: {json.dumps(self.config, indent=2)}", "debug")
            
            # Validate inputs
            if not self.validate_inputs():
                return
            
            # Build command with intelligent options
            cmd = self.build_command()
            
            self.output_signal.emit(f"Running command: {' '.join(cmd)}", "info")
            
            # Execute compilation
            success = self.execute_compilation(cmd)
            
            if success:
                self.output_signal.emit("Compilation completed successfully!", "success")
                self.finished_signal.emit(True, "Compilation successful")
            else:
                self.finished_signal.emit(False, "Compilation failed - check logs")
                
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            self.output_signal.emit(error_msg, "error")
            self.finished_signal.emit(False, f"Critical error: {str(e)}")
    
    def validate_inputs(self) -> bool:
        """Validate all input files and directories"""
        try:
            # Check main file
            if not os.path.exists(self.main_file):
                self.output_signal.emit(f"Main file not found: {self.main_file}", "error")
                return False
            
            # Check Python installation
            python_version = sys.version_info
            self.output_signal.emit(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}", "info")
            
            # Check Nuitka installation
            try:
                result = subprocess.run(['python', '-m', 'nuitka', '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    self.output_signal.emit("Nuitka not properly installed. Install with: pip install nuitka", "error")
                    return False
                self.output_signal.emit(f"Nuitka version: {result.stdout.strip()}", "info")
            except Exception as e:
                self.output_signal.emit(f"Error checking Nuitka: {str(e)}", "error")
                return False
            
            return True
            
        except Exception as e:
            self.output_signal.emit(f"Validation error: {str(e)}", "error")
            return False
    
    def scan_project_imports(self, start_path: str) -> Tuple[List[str], List[str]]:
        """
        Intelligently scan project for imports and dependencies
        Returns: (local_modules, external_packages)
        """
        local_modules = []
        external_packages = set()
        import_pattern = re.compile(r'^\s*(?:from|import)\s+([a-zA-Z0-9_\.]+)')
        
        def scan_file(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    for line in content.split('\n'):
                        match = import_pattern.match(line)
                        if match:
                            module = match.group(1).split('.')[0]
                            if module not in sys.builtin_module_names:
                                # Check if it's a local module
                                if os.path.exists(os.path.join(os.path.dirname(filepath), module + '.py')):
                                    if module not in local_modules:
                                        local_modules.append(module)
                                else:
                                    try:
                                        __import__(module)
                                    except ImportError:
                                        external_packages.add(module)
            except Exception as e:
                logger.warning(f"Error scanning {filepath}: {e}")
        
        # Scan all Python files in project
        root_dir = os.path.dirname(start_path)
        for root, dirs, files in os.walk(root_dir):
            # Skip common exclusion directories
            dirs[:] = [d for d in dirs if not d.startswith(('.', '__', 'venv', 'env', 'dist', 'build'))]
            
            for file in files:
                if file.endswith('.py') and file != os.path.basename(start_path):
                    scan_file(os.path.join(root, file))
        
        return local_modules, list(external_packages)
    
    def build_command(self) -> List[str]:
        """Build the Nuitka command with intelligent options"""
        cmd = [
            sys.executable, '-m', 'nuitka',
            '--standalone',
            '--follow-imports',
            '--enable-plugin=tk-inter',  # Enable common plugins
            '--enable-plugin=multiprocessing',
            '--output-dir=./build_output',
            '--windows-console-mode=disable' if sys.platform == 'win32' and not self.config.get('console', True) else '',
            '--macos-create-app-bundle' if sys.platform == 'darwin' else '',
        ]
        
        # Remove empty strings
        cmd = [c for c in cmd if c]
        
        # Add output filename
        if self.config.get('output_name'):
            cmd.extend(['--output-filename', self.config['output_name']])
        
        # Add icon if specified
        if self.config.get('icon_file') and os.path.exists(self.config['icon_file']):
            if sys.platform == 'win32':
                cmd.extend(['--windows-icon-from-ico', self.config['icon_file']])
            elif sys.platform == 'darwin':
                cmd.extend(['--macos-app-icon', self.config['icon_file']])
        
        # Scan for imports
        self.output_signal.emit("Scanning project for imports...", "info")
        local_modules, external_packages = self.scan_project_imports(self.main_file)
        
        # Add local modules
        for module in local_modules:
            cmd.extend(['--include-module', module])
            self.output_signal.emit(f"Including local module: {module}", "debug")
        
        # Add include directories
        if self.config.get('include_dirs'):
            for include_dir in self.config['include_dirs']:
                if os.path.exists(include_dir):
                    cmd.extend(['--include-plugin-directory', include_dir])
        
        # Add data files
        if self.config.get('data_files'):
            for data_file in self.config['data_files']:
                if os.path.exists(data_file):
                    cmd.extend(['--include-data-file', f"{data_file}=./"])
        
        # Add additional options
        if self.config.get('onefile'):
            cmd.append('--onefile')
        
        if self.config.get('enable_console'):
            if sys.platform == 'win32':
                cmd.append('--windows-console-mode=attach')
        
        if self.config.get('disable_console'):
            if sys.platform == 'win32':
                cmd.append('--windows-console-mode=disable')
        
        # Add main file
        cmd.append(self.main_file)
        
        return cmd
    
    def execute_compilation(self, cmd: List[str]) -> bool:
        """Execute the compilation command with real-time output"""
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            # Read output line by line
            error_count = 0
            warning_count = 0
            
            while self.is_running:
                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break
                
                if line:
                    line = line.strip()
                    
                    # Categorize output
                    if "error:" in line.lower():
                        self.output_signal.emit(f"❌ {line}", "error")
                        error_count += 1
                    elif "warning:" in line.lower():
                        self.output_signal.emit(f"⚠️ {line}", "warning")
                        warning_count += 1
                    else:
                        self.output_signal.emit(line, "info")
                    
                    # Update progress based on output
                    if "Progress:" in line:
                        try:
                            progress = int(re.search(r'Progress: (\d+)', line).group(1))
                            self.progress_signal.emit(progress)
                        except:
                            pass
                    
                    QApplication.processEvents()
            
            # Get return code
            return_code = self.process.wait()
            
            if return_code == 0:
                if error_count == 0:
                    self.output_signal.emit(f"✅ Compilation successful! Warnings: {warning_count}", "success")
                else:
                    self.output_signal.emit(f"⚠️ Compilation completed with {error_count} errors and {warning_count} warnings", "warning")
                return True
            else:
                self.output_signal.emit(f"❌ Compilation failed with return code {return_code}", "error")
                return False
                
        except FileNotFoundError as e:
            self.output_signal.emit(f"File not found error: {str(e)}", "error")
            return False
        except PermissionError as e:
            self.output_signal.emit(f"Permission error: {str(e)}", "error")
            return False
        except subprocess.TimeoutExpired:
            self.output_signal.emit("Compilation timed out", "error")
            return False
        except Exception as e:
            self.output_signal.emit(f"Unexpected error during compilation: {str(e)}\n{traceback.format_exc()}", "error")
            return False
        finally:
            self.process = None

class ConfigDialog(QDialog):
    """Advanced configuration dialog for compilation settings"""
    
    def __init__(self, parent=None, current_config=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Compiler Configuration")
        self.setMinimumWidth(500)
        self.config = current_config or {}
        self.setup_ui()
        self.load_config()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Create form layout for settings
        form = QFormLayout()
        
        # Output name
        self.output_name = QLineEdit()
        form.addRow("Output Name:", self.output_name)
        
        # Icon file
        icon_layout = QHBoxLayout()
        self.icon_file = QLineEdit()
        self.icon_file.setReadOnly(True)
        self.icon_button = QPushButton("Browse...")
        self.icon_button.clicked.connect(self.browse_icon)
        icon_layout.addWidget(self.icon_file)
        icon_layout.addWidget(self.icon_button)
        form.addRow("Application Icon:", icon_layout)
        
        # Include directories
        self.include_dirs = QTextEdit()
        self.include_dirs.setMaximumHeight(100)
        self.include_dirs.setPlaceholderText("One directory per line")
        form.addRow("Include Dirs:", self.include_dirs)
        
        # Data files
        self.data_files = QTextEdit()
        self.data_files.setMaximumHeight(100)
        self.data_files.setPlaceholderText("One file per line")
        form.addRow("Data Files:", self.data_files)
        
        # Compilation options
        self.onefile = QCheckBox("Create single executable file")
        form.addRow("", self.onefile)
        
        self.enable_console = QCheckBox("Enable console window")
        form.addRow("", self.enable_console)
        
        self.disable_console = QCheckBox("Disable console window")
        form.addRow("", self.disable_console)
        
        # Advanced options
        self.jobs = QSpinBox()
        self.jobs.setRange(1, 16)
        self.jobs.setValue(4)
        form.addRow("Parallel jobs:", self.jobs)
        
        layout.addLayout(form)
        
        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def browse_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Icon File",
            "",
            "Icon Files (*.ico *.icns *.png);;All Files (*.*)"
        )
        if file_path:
            self.icon_file.setText(file_path)
    
    def load_config(self):
        """Load existing configuration"""
        self.output_name.setText(self.config.get('output_name', ''))
        self.icon_file.setText(self.config.get('icon_file', ''))
        
        if self.config.get('include_dirs'):
            self.include_dirs.setText('\n'.join(self.config['include_dirs']))
        
        if self.config.get('data_files'):
            self.data_files.setText('\n'.join(self.config['data_files']))
        
        self.onefile.setChecked(self.config.get('onefile', False))
        self.enable_console.setChecked(self.config.get('enable_console', True))
        self.disable_console.setChecked(self.config.get('disable_console', False))
        self.jobs.setValue(self.config.get('jobs', 4))
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration from dialog"""
        return {
            'output_name': self.output_name.text().strip(),
            'icon_file': self.icon_file.text().strip(),
            'include_dirs': [d.strip() for d in self.include_dirs.toPlainText().split('\n') if d.strip()],
            'data_files': [f.strip() for f in self.data_files.toPlainText().split('\n') if f.strip()],
            'onefile': self.onefile.isChecked(),
            'enable_console': self.enable_console.isChecked(),
            'disable_console': self.disable_console.isChecked(),
            'jobs': self.jobs.value()
        }

class NuitkaCompilerGUI(QMainWindow):
    """Main GUI window for Nuitka Compiler"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nuitka Pro Compiler v2.0")
        self.setMinimumSize(1200, 800)
        
        # Initialize variables
        self.main_file = ""
        self.compiler_thread = None
        self.output_queue = queue.Queue()
        self.config_file = "compiler_config.json"
        self.current_config = self.load_config()
        
        # Setup UI
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        
        # Start queue processor
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_output_queue)
        self.timer.start(100)
        
        # Apply dark theme
        self.apply_dark_theme()
        
        logger.info("Application started")
    
    def setup_menu(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Main File", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.select_main_file)
        file_menu.addAction(open_action)
        
        load_config_action = QAction("Load Configuration", self)
        load_config_action.triggered.connect(self.load_config_dialog)
        file_menu.addAction(load_config_action)
        
        save_config_action = QAction("Save Configuration", self)
        save_config_action.triggered.connect(self.save_config_dialog)
        file_menu.addAction(save_config_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        check_nuitka_action = QAction("Check Nuitka Installation", self)
        check_nuitka_action.triggered.connect(self.check_nuitka)
        tools_menu.addAction(check_nuitka_action)
        
        clear_logs_action = QAction("Clear Logs", self)
        clear_logs_action.triggered.connect(self.clear_logs)
        tools_menu.addAction(clear_logs_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def setup_ui(self):
        """Setup the main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Top section - File selection
        file_group = QGroupBox("Target File")
        file_layout = QHBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("padding: 5px; background-color: #2b2b2b; border-radius: 3px;")
        file_layout.addWidget(self.file_label, 1)
        
        self.select_btn = QPushButton("📂 Select Main File")
        self.select_btn.setMinimumHeight(40)
        self.select_btn.clicked.connect(self.select_main_file)
        file_layout.addWidget(self.select_btn)
        
        self.config_btn = QPushButton("⚙️ Advanced Config")
        self.config_btn.setMinimumHeight(40)
        self.config_btn.clicked.connect(self.open_config_dialog)
        file_layout.addWidget(self.config_btn)
        
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)
        
        # Middle section - Log output
        log_group = QGroupBox("Compilation Log")
        log_layout = QVBoxLayout()
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Consolas", 10))
        self.log_output.setMinimumHeight(400)
        log_layout.addWidget(self.log_output)
        
        # Log controls
        log_controls = QHBoxLayout()
        
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(self.clear_log)
        log_controls.addWidget(self.clear_log_btn)
        
        self.copy_log_btn = QPushButton("Copy Log")
        self.copy_log_btn.clicked.connect(self.copy_log)
        log_controls.addWidget(self.copy_log_btn)
        
        self.save_log_btn = QPushButton("Save Log")
        self.save_log_btn.clicked.connect(self.save_log)
        log_controls.addWidget(self.save_log_btn)
        
        log_controls.addStretch()
        
        self.word_wrap_check = QCheckBox("Word Wrap")
        self.word_wrap_check.stateChanged.connect(self.toggle_word_wrap)
        log_controls.addWidget(self.word_wrap_check)
        
        log_layout.addLayout(log_controls)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group, 1)
        
        # Bottom section - Progress and controls
        control_group = QGroupBox("Compilation Controls")
        control_layout = QVBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.compile_btn = QPushButton("🚀 Start Compilation")
        self.compile_btn.setMinimumHeight(50)
        self.compile_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.compile_btn.clicked.connect(self.start_compilation)
        button_layout.addWidget(self.compile_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop Compilation")
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_compilation)
        button_layout.addWidget(self.stop_btn)
        
        control_layout.addLayout(button_layout)
        
        # Quick options
        quick_options = QHBoxLayout()
        
        self.onefile_check = QCheckBox("Single File Executable")
        self.onefile_check.setChecked(True)
        quick_options.addWidget(self.onefile_check)
        
        self.console_check = QCheckBox("Show Console")
        self.console_check.setChecked(False)
        quick_options.addWidget(self.console_check)
        
        quick_options.addStretch()
        
        control_layout.addLayout(quick_options)
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
    
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Add permanent widgets
        self.status_label = QLabel("Status: Idle")
        self.status_bar.addPermanentWidget(self.status_label)
    
    def apply_dark_theme(self):
        """Apply dark theme to the application"""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        
        self.setPalette(dark_palette)
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        default_config = {
            'output_name': '',
            'icon_file': '',
            'include_dirs': [],
            'data_files': [],
            'onefile': True,
            'enable_console': False,
            'disable_console': True,
            'jobs': 4,
            'recent_files': []
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
        
        return default_config
    
    def save_config(self):
        """Save configuration to file"""
        try:
            # Update config with current settings
            self.current_config.update({
                'onefile': self.onefile_check.isChecked(),
                'enable_console': self.console_check.isChecked(),
                'disable_console': not self.console_check.isChecked(),
            })
            
            with open(self.config_file, 'w') as f:
                json.dump(self.current_config, f, indent=2)
            
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            self.show_error("Save Error", f"Could not save configuration: {str(e)}")
    
    def select_main_file(self):
        """Open file dialog to select main Python file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Main Python File",
            "",
            "Python Files (*.py);;All Files (*.*)"
        )
        
        if file_path:
            self.main_file = file_path
            self.file_label.setText(f"Selected: {file_path}")
            self.log_output.append(f"✅ Selected main file: {file_path}")
            
            # Add to recent files
            if file_path not in self.current_config['recent_files']:
                self.current_config['recent_files'].insert(0, file_path)
                self.current_config['recent_files'] = self.current_config['recent_files'][:5]
            
            self.save_config()
    
    def open_config_dialog(self):
        """Open advanced configuration dialog"""
        dialog = ConfigDialog(self, self.current_config)
        if dialog.exec_():
            self.current_config.update(dialog.get_config())
            # Update UI with new settings
            self.onefile_check.setChecked(self.current_config.get('onefile', True))
            self.console_check.setChecked(self.current_config.get('enable_console', False))
            self.save_config()
            self.log_output.append("✅ Configuration updated")
    
    def load_config_dialog(self):
        """Load configuration from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Configuration",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    config = json.load(f)
                    self.current_config.update(config)
                    
                    # Update UI
                    self.onefile_check.setChecked(self.current_config.get('onefile', True))
                    self.console_check.setChecked(self.current_config.get('enable_console', False))
                    
                    self.log_output.append(f"✅ Configuration loaded from: {file_path}")
                    self.save_config()
            except Exception as e:
                self.show_error("Load Error", f"Could not load configuration: {str(e)}")
    
    def save_config_dialog(self):
        """Save configuration to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Configuration",
            "compiler_config.json",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            try:
                # Update config with current settings
                self.current_config.update({
                    'onefile': self.onefile_check.isChecked(),
                    'enable_console': self.console_check.isChecked(),
                    'disable_console': not self.console_check.isChecked(),
                })
                
                with open(file_path, 'w') as f:
                    json.dump(self.current_config, f, indent=2)
                
                self.log_output.append(f"✅ Configuration saved to: {file_path}")
            except Exception as e:
                self.show_error("Save Error", f"Could not save configuration: {str(e)}")
    
    def start_compilation(self):
        """Start the compilation process"""
        if not self.main_file:
            self.show_error("No File Selected", "Please select a main Python file to compile.")
            return
        
        # Check if compilation is already running
        if self.compiler_thread and self.compiler_thread.isRunning():
            self.show_warning("Compilation in Progress", "A compilation is already running. Please stop it first.")
            return
        
        # Clear previous log
        self.clear_log()
        
        # Update config with current UI settings
        self.current_config['onefile'] = self.onefile_check.isChecked()
        self.current_config['enable_console'] = self.console_check.isChecked()
        self.current_config['disable_console'] = not self.console_check.isChecked()
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Disable controls
        self.compile_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
        self.config_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Update status
        self.status_label.setText("Status: Compiling...")
        self.status_bar.showMessage("Compilation in progress...")
        
        # Create and start compiler thread
        self.compiler_thread = CompilerWorker(self.main_file, self.current_config)
        self.compiler_thread.output_signal.connect(self.handle_output)
        self.compiler_thread.progress_signal.connect(self.progress_bar.setValue)
        self.compiler_thread.finished_signal.connect(self.compilation_finished)
        self.compiler_thread.start()
        
        logger.info(f"Started compilation for: {self.main_file}")
    
    def stop_compilation(self):
        """Stop the compilation process"""
        if self.compiler_thread and self.compiler_thread.isRunning():
            reply = QMessageBox.question(
                self, 'Stop Compilation',
                'Are you sure you want to stop the compilation?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.log_output.append("⏹️ Stopping compilation...")
                self.compiler_thread.stop()
                self.compiler_thread.wait(5000)  # Wait up to 5 seconds
                
                if self.compiler_thread.isRunning():
                    self.compiler_thread.terminate()
                    self.compiler_thread.wait()
                
                self.compilation_finished(False, "Compilation stopped by user")
    
    def handle_output(self, message: str, msg_type: str):
        """Handle output from compiler thread"""
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color code based on message type
        if msg_type == "error":
            formatted_msg = f'<span style="color: #ff6b6b;">[{timestamp}] ERROR: {message}</span>'
        elif msg_type == "warning":
            formatted_msg = f'<span style="color: #ffd93d;">[{timestamp}] WARNING: {message}</span>'
        elif msg_type == "success":
            formatted_msg = f'<span style="color: #6bff6b;">[{timestamp}] SUCCESS: {message}</span>'
        elif msg_type == "debug":
            formatted_msg = f'<span style="color: #888888;">[{timestamp}] DEBUG: {message}</span>'
        else:
            formatted_msg = f'<span style="color: #ffffff;">[{timestamp}] {message}</span>'
        
        # Queue the message
        self.output_queue.put(formatted_msg)
        
        # Also log to file
        if msg_type == "error":
            logger.error(message)
        elif msg_type == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    
    def process_output_queue(self):
        """Process queued output messages"""
        while not self.output_queue.empty():
            msg = self.output_queue.get()
            self.log_output.append(msg)
            # Auto-scroll to bottom
            cursor = self.log_output.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.log_output.setTextCursor(cursor)
    
    def compilation_finished(self, success: bool, message: str):
        """Handle compilation completion"""
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        # Enable controls
        self.compile_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        self.config_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        # Update status
        if success:
            self.status_label.setText("Status: Completed")
            self.status_bar.showMessage("Compilation completed successfully", 5000)
            self.show_info("Compilation Complete", message)
        else:
            self.status_label.setText("Status: Failed")
            self.status_bar.showMessage("Compilation failed", 5000)
            self.show_error("Compilation Failed", message)
        
        # Clean up thread
        self.compiler_thread = None
    
    def check_nuitka(self):
        """Check Nuitka installation"""
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'nuitka', '--version'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                QMessageBox.information(
                    self, "Nuitka Check",
                    f"Nuitka is installed properly.\nVersion: {result.stdout.strip()}"
                )
            else:
                QMessageBox.warning(
                    self, "Nuitka Check",
                    f"Nuitka may not be installed properly.\nError: {result.stderr}"
                )
        except Exception as e:
            self.show_error("Nuitka Check", f"Error checking Nuitka: {str(e)}")
    
    def clear_logs(self):
        """Clear log files"""
        reply = QMessageBox.question(
            self, 'Clear Logs',
            'Are you sure you want to clear all log files?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(LOG_FILE):
                    os.remove(LOG_FILE)
                self.log_output.clear()
                self.log_output.append("✅ Logs cleared")
                logger.info("Logs cleared")
            except Exception as e:
                self.show_error("Clear Logs", f"Error clearing logs: {str(e)}")
    
    def clear_log(self):
        """Clear the log output"""
        self.log_output.clear()
    
    def copy_log(self):
        """Copy log content to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.log_output.toPlainText())
        self.status_bar.showMessage("Log copied to clipboard", 2000)
    
    def save_log(self):
        """Save log to file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Log",
            f"compilation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_output.toPlainText())
                self.status_bar.showMessage(f"Log saved to {file_path}", 3000)
            except Exception as e:
                self.show_error("Save Error", f"Could not save log: {str(e)}")
    
    def toggle_word_wrap(self, state):
        """Toggle word wrap in log output"""
        if state == Qt.Checked:
            self.log_output.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.log_output.setLineWrapMode(QTextEdit.NoWrap)
    
    def show_error(self, title: str, message: str):
        """Show error dialog"""
        QMessageBox.critical(self, title, message)
    
    def show_warning(self, title: str, message: str):
        """Show warning dialog"""
        QMessageBox.warning(self, title, message)
    
    def show_info(self, title: str, message: str):
        """Show information dialog"""
        QMessageBox.information(self, title, message)
    
    def show_about(self):
        """Show about dialog"""
        about_text = """
        <h2>Nuitka Pro Compiler v2.0</h2>
        <p>A professional GUI for compiling Python applications using Nuitka.</p>
        <p><b>Features:</b></p>
        <ul>
            <li>Automatic import scanning and inclusion</li>
            <li>Real-time compilation logging with color coding</li>
            <li>Advanced configuration options</li>
            <li>Dark theme for comfortable viewing</li>
            <li>Comprehensive error handling</li>
            <li>Cross-platform support</li>
        </ul>
        <p><b>Requirements:</b></p>
        <ul>
            <li>Python 3.6+</li>
            <li>Nuitka (pip install nuitka)</li>
            <li>PyQt5 (pip install PyQt5)</li>
        </ul>
        <p><b>Author:</b> Professional Build System</p>
        <p><b>License:</b> MIT</p>
        """
        
        QMessageBox.about(self, "About Nuitka Pro Compiler", about_text)
    
    def closeEvent(self, event):
        """Handle application close event"""
        if self.compiler_thread and self.compiler_thread.isRunning():
            reply = QMessageBox.question(
                self, 'Exit',
                'Compilation is in progress. Are you sure you want to exit?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.compiler_thread.stop()
                self.compiler_thread.wait(2000)
                event.accept()
            else:
                event.ignore()
        else:
            # Save configuration
            self.save_config()
            event.accept()

def main():
    """Main entry point with comprehensive error handling"""
    try:
        # Check Python version
        if sys.version_info < (3, 6):
            print("ERROR: Python 3.6 or higher is required")
            sys.exit(1)
        
        # Create QApplication
        app = QApplication(sys.argv)
        app.setApplicationName("Nuitka Pro Compiler")
        app.setOrganizationName("Professional Build System")
        
        # Set application icon if available
        # app.setWindowIcon(QIcon("icon.png"))
        
        # Create and show main window
        window = NuitkaCompilerGUI()
        window.show()
        
        # Execute application
        sys.exit(app.exec_())
        
    except ImportError as e:
        print(f"ERROR: Missing required module: {e}")
        print("\nPlease install required packages:")
        print("pip install PyQt5 nuitka")
        sys.exit(1)
    except Exception as e:
        print(f"FATAL ERROR: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()