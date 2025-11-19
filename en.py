import sys
import hashlib
import time
import os
import json
import signal
import secrets
import random
from datetime import datetime
from multiprocessing import cpu_count, Process
from typing import Dict, Any, Set, Tuple
import coincurve
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QGroupBox, QRadioButton, QCheckBox, QComboBox, QSpinBox,
                             QDoubleSpinBox, QPushButton, QTextEdit, QProgressBar,
                             QLabel, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                             QMessageBox, QDialog, QDialogButtonBox, QTextBrowser,
                             QLineEdit, QSizePolicy, QFileDialog, QScrollArea)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPixmap, QPainter
import psutil

# Constants
MAX_KEY = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140
MIN_KEY = 0x0000000000000000000000000000000000000000000000000000000000000001
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(SCRIPT_DIR, "json")
TXT_DIR = os.path.join(SCRIPT_DIR, "txt")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
STATS_DIR = os.path.join(SCRIPT_DIR, "stats")
THEMES_DIR = os.path.join(SCRIPT_DIR, "themes")
STATE_DIR = os.path.join(SCRIPT_DIR, "state")  # New directory for state files

class MatrixBackground(QWidget):
    """Widget with matrix animation for FOREGROUND background"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # EXPAND CHARACTER SET - more numbers and symbols
        self.matrix_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*()_+-=[]{}|;:,.<>?/~`"
        self.drops = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_matrix)
        self.timer.start(8)  # 20 FPS
        # REDUCE FONT SIZE for higher density
        self.font_size = 8  # was 14
        
        # CRITICALLY IMPORTANT: Remove transparency for mouse events but make background semi-transparent
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # Events pass through
        self.setStyleSheet("background: transparent;")
        
        # Set high Z-order to be above other widgets
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.setup_drops()
        
    def setup_drops(self):
        """Initialize falling characters"""
        if self.width() > 0 and self.height() > 0:
            self.drops = []
            # INCREASE NUMBER OF COLUMNS by 2-3 times
            num_columns = max(1, self.width() // (self.font_size // 2))  # Reduce distance between columns
            
            for i in range(num_columns):
                # Each column has its own speed and position
                self.drops.append({
                    'x': i * (self.font_size // 2),  # Reduce distance between columns
                    'y': random.randint(-500, 0),
                    'speed': random.uniform(1, 20),   # Slightly reduce speed range
                    'length': random.randint(40, 80), # INCREASE DROP LENGTH
                    'chars': []
                })
    
    def resizeEvent(self, event):
        """Resize event handler"""
        self.setup_drops()
        super().resizeEvent(event)
    
    def update_matrix(self):
        """Update animation"""
        if self.isVisible():
            self.update()
    
    def paintEvent(self, event):
        """Draw matrix effect"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        
        # Semi-transparent black background for trail effect
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))  # Slightly increased transparency
        
        font = QFont("Courier New", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        for drop in self.drops:
            # Update position
            drop['y'] += drop['speed']
            
            # If drop went beyond bounds, restart it
            if drop['y'] > self.height() + drop['length'] * self.font_size:
                drop['y'] = random.randint(-500, 0)
                drop['speed'] = random.uniform(3, 8)
                drop['length'] = random.randint(12, 35)
                drop['chars'] = []  # Reset characters
            
            # Generate new characters if needed
            if len(drop['chars']) != drop['length']:
                drop['chars'] = [random.choice(self.matrix_chars) for _ in range(drop['length'])]
            else:
                # INCREASE CHARACTER CHANGE PROBABILITY for more dynamics
                for i in range(len(drop['chars'])):
                    if random.random() < 0.18:  # Increased from 5% to 8%
                        drop['chars'][i] = random.choice(self.matrix_chars)
            
            # Draw drop characters
            for i, char in enumerate(drop['chars']):
                y_pos = drop['y'] - i * self.font_size
                
                if -self.font_size <= y_pos < self.height():
                    # Color gradient from bright green to dark green
                    if i == 0:
                        color = QColor(0, 90, 0)  # White for first character
                    elif i == 1:
                        color = QColor(0, 255, 0)      # Bright green
                    elif i == 2:
                        color = QColor(0, 220, 0)      # Green
                    elif i < 6:
                        color = QColor(0, 180, 0)      # Medium green
                    else:
                        intensity = max(60, 200 - (i * 100 // drop['length']))  # Smoother gradient
                        color = QColor(0, intensity, 0)
                    
                    painter.setPen(color)
                    painter.drawText(int(drop['x']), int(y_pos), char)

class ThemeManager:
    """Theme manager for the application"""
    
    THEMES = {
        "light": "light.qss",
        "dark_green": "dark_green.qss", 
        "dark_cyan": "dark_cyan.qss",
        "dark_blue": "dark_blue.qss",
        "dark_yellow": "dark_yellow.qss",
        "rainbow": "rainbow.qss",
        "matrix": "matrix.qss",
        "system": "system.qss"
    }
    
    @classmethod
    def get_theme_path(cls, theme_name):
        """Get path to theme file"""
        theme_file = cls.THEMES.get(theme_name, "light.qss")
        return os.path.join(THEMES_DIR, theme_file)
    
    @classmethod
    def load_theme(cls, theme_name):
        """Load theme from file"""
        theme_path = cls.get_theme_path(theme_name)
        try:
            if os.path.exists(theme_path):
                with open(theme_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                print(f"Theme file not found: {theme_path}")
                return ""
        except Exception as e:
            print(f"Error loading theme {theme_name}: {e}")
            return ""
    
    @classmethod
    def get_available_themes(cls):
        """Get list of available themes"""
        return list(cls.THEMES.keys())

# ==================== STATE SAVING MECHANISM ====================
class StateManager:
    """Manager for saving and loading process states"""
    
    @staticmethod
    def get_state_filename(proc_id: int, range_start: int, range_end: int, tab_type: str = "decimal", program_name: str = "bitcoin365") -> str:
        """
        Generate unique state filename based on parameters and tab type
        
        Args:
            proc_id: Process ID (0, 1, 2, ...)
            range_start: Range start
            range_end: Range end
            tab_type: Type of tab ("decimal", "hex64", "percent")
            program_name: Program name for separating states of different scripts
        
        Returns:
            str: Path to state file
        """
        # Use different formats based on tab type
        if tab_type == "decimal":
            # For decimal tab: use decimal numbers
            range_id = f"start_{range_start}_end_{range_end}"
        elif tab_type == "hex64":
            # For hex64 tab: use HEX format
            range_id = f"start_{range_start:064x}_end_{range_end:064x}"
        elif tab_type == "percent":
            # For percent tab: use percentage values
            range_id = f"start_{range_start}_end_{range_end}"
        else:
            # Default: use HEX
            range_id = f"start_{range_start:064x}_end_{range_end:064x}"
        
        # Form filename with tab type
        filename = f"state_{program_name}_{tab_type}_process_{proc_id}_{range_id}.json"
        
        return os.path.join(STATE_DIR, filename)
    
    @staticmethod
    def save_state(proc_id: int, current_key: int, range_start: int, range_end: int, tab_type: str = "decimal", metadata: dict = None):
        """
        Save current process state to JSON file
        
        Args:
            proc_id: Process ID
            current_key: Current processed key
            range_start: Range start
            range_end: Range end  
            tab_type: Type of tab ("decimal", "hex64", "percent")
            metadata: Additional metadata to save
        """
        try:
            # Generate filename with tab type
            state_file = StateManager.get_state_filename(proc_id, range_start, range_end, tab_type)
            
            # Form data structure
            state_data = {
                # Main range parameters
                'process_id': proc_id,
                'current_key': current_key,
                'range_start': range_start,
                'range_end': range_end,
                'tab_type': tab_type,
                
                # Metadata for compatibility check
                'program_version': '1.0.0',
                'timestamp': datetime.now().isoformat(),
                'total_range_size': range_end - range_start + 1,
                'keys_processed': current_key - range_start,
                
                # Additional custom data
                'metadata': metadata or {}
            }
            
            # Create directory if doesn't exist
            os.makedirs(os.path.dirname(state_file), exist_ok=True)
            
            # Save to JSON with pretty formatting
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Process {proc_id} state saved for {tab_type} tab: {hex(current_key)}")
            
        except Exception as e:
            print(f"❌ Error saving process {proc_id} state for {tab_type} tab: {e}")
    
    @staticmethod
    def load_state(proc_id: int, range_start: int, range_end: int, tab_type: str = "decimal", program_name: str = "bitcoin365") -> Tuple[int, int, int, dict]:
        """
        Load process state with parameter compatibility check
        
        Args:
            proc_id: Process ID to load
            range_start: Expected range start
            range_end: Expected range end
            tab_type: Type of tab ("decimal", "hex64", "percent")
            program_name: Program name
        
        Returns:
            Tuple: (current_key, loaded_start, loaded_end, metadata)
            or (None, None, None, None) if loading impossible
        """
        try:
            state_file = StateManager.get_state_filename(proc_id, range_start, range_end, tab_type, program_name)
            
            if not os.path.exists(state_file):
                print(f"📭 Process {proc_id} state file not found for {tab_type} tab")
                return None, None, None, None
            
            # Read state file
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # ⚠️ IMPORTANT: Check parameter compatibility
            loaded_start = state_data['range_start']
            loaded_end = state_data['range_end']
            loaded_tab_type = state_data.get('tab_type', 'decimal')
            
            if loaded_start != range_start or loaded_end != range_end or loaded_tab_type != tab_type:
                print(f"🔀 Range or tab type mismatch for process {proc_id}")
                print(f"   Expected: {range_start} - {range_end} (tab: {tab_type})")
                print(f"   In file: {loaded_start} - {loaded_end} (tab: {loaded_tab_type})")
                return None, None, None, None
                
            # Check data integrity
            current_key = state_data['current_key']
            
            if not (range_start <= current_key <= range_end):
                print(f"⚠️ Key out of range in process {proc_id}")
                return None, None, None, None
            
            metadata = state_data.get('metadata', {})
            
            print(f"✅ Process {proc_id} state loaded for {tab_type} tab")
            print(f"   Current key: {hex(current_key)}")
            print(f"   Progress: {state_data.get('keys_processed', 0):,} keys")
            
            return current_key, loaded_start, loaded_end, metadata
            
        except Exception as e:
            print(f"❌ Error loading process {proc_id} state for {tab_type} tab: {e}")
            return None, None, None, None
    
    @staticmethod
    def cleanup_state_files(range_start: int, range_end: int, tab_type: str = "decimal", program_name: str = "bitcoin365"):
        """
        Clean ALL state files for specified range and tab type
        
        Args:
            range_start: Range start for cleanup
            range_end: Range end for cleanup  
            tab_type: Type of tab ("decimal", "hex64", "percent")
            program_name: Program name
        """
        try:
            if not os.path.exists(STATE_DIR):
                print("📭 State directory doesn't exist")
                return
                
            removed_count = 0
            
            # Generate target suffix based on tab type
            if tab_type == "decimal":
                target_suffix = f"start_{range_start}_end_{range_end}.json"
            elif tab_type == "hex64":
                target_suffix = f"start_{range_start:064x}_end_{range_end:064x}.json"
            elif tab_type == "percent":
                target_suffix = f"start_{range_start}_end_{range_end}.json"
            else:
                target_suffix = f"start_{range_start:064x}_end_{range_end:064x}.json"
            
            target_prefix = f"state_{program_name}_{tab_type}_process_"
            
            for filename in os.listdir(STATE_DIR):
                if filename.startswith(target_prefix) and filename.endswith(target_suffix):
                    file_path = os.path.join(STATE_DIR, filename)
                    os.remove(file_path)
                    removed_count += 1
                    print(f"🗑️ State file deleted: {filename}")
            
            print(f"✅ Cleanup completed for {tab_type} tab. Files removed: {removed_count}")
            
        except Exception as e:
            print(f"❌ Error cleaning state files for {tab_type} tab: {e}")
    
    @staticmethod
    def list_state_files(tab_type: str = "all", program_name: str = "bitcoin365"):
        """
        Show all state files for program and specific tab type
        """
        try:
            if not os.path.exists(STATE_DIR):
                return []
                
            state_files = []
            for filename in os.listdir(STATE_DIR):
                if filename.startswith(f"state_{program_name}_") and filename.endswith(".json"):
                    if tab_type == "all" or f"_{tab_type}_" in filename:
                        state_files.append(filename)
            
            if state_files:
                print(f"📋 STATE FILES ({program_name}, tab: {tab_type}):")
                for file in sorted(state_files):
                    print(f"  📄 {file}")
            else:
                print(f"📭 No state files found for {program_name} (tab: {tab_type})")
                
            return state_files
            
        except Exception as e:
            print(f"❌ Error reading state files: {e}")
            return []

class WorkerProcess:
    """Class for work in separate process"""
    def __init__(self, config):
        self.config = config
        self.running = True
        self.attempts = 0
        self.targets_found = 0
        self.start_time = time.time()
        self.batch_counter = 0
        self.current_key = None
        self.range_completed = False
        self.process_id = config['proc_id']
        self.stats_buffer = []
        self.matches_buffer = []
        self.debug_mode = config.get('debug_mode', False)
        self.debug_counter = 0
        self.debug_logged = False
        self.tab_type = config.get('tab_type', 'decimal')  # Store tab type
        
        # For sequential mode - initial process position
        if config['search_method'] == 1:  # Sequential mode
            # Try to load previous state if continue_search is enabled
            if config.get('continue_search', False):
                current_key, loaded_start, loaded_end, metadata = StateManager.load_state(
                    self.process_id, 
                    config['range_start'], 
                    config['range_end'],
                    self.tab_type  # Pass tab type
                )
                if current_key is not None:
                    # Continue from last key + step
                    self.current_key = current_key + config['processes']
                    print(f"🔄 Process {self.process_id}: CONTINUING from key {hex(current_key)} -> {hex(self.current_key)} (tab: {self.tab_type})")
                else:
                    # Start from unique position for process
                    self.current_key = config['range_start'] + config['proc_id']
                    print(f"🆕 Process {self.process_id}: STARTING NEW from key {hex(self.current_key)} (tab: {self.tab_type})")
            else:
                # New search - start from unique position
                self.current_key = config['range_start'] + config['proc_id']
                print(f"🆕 Process {self.process_id}: NEW SEARCH from key {hex(self.current_key)} (tab: {self.tab_type})")
            
            self.step_size = config['processes']  # Step equals number of processes
            
            # Log range information for process
            self.log_range_info()

    def log_range_info(self):
        """Log process range information with unique start positions"""
        try:
            # Calculate actual start position for this process
            if self.config['search_method'] == 1:  # Sequential mode
                actual_start = self.current_key if self.current_key is not None else self.config['range_start'] + self.config['proc_id']
            else:
                actual_start = self.config['range_start']
                
            range_info = {
                'process_id': self.process_id,
                'range_start': self.config['range_start'],
                'range_end': self.config['range_end'],
                'current_key': self.current_key,
                'actual_start_position': actual_start,
                'step_size': self.step_size,
                'tab_type': self.tab_type,
                'timestamp': time.time()
            }
            
            range_file = os.path.join(STATS_DIR, f"range_{self.process_id}.json")
            os.makedirs(os.path.dirname(range_file), exist_ok=True)
            with open(range_file, 'w', encoding='utf-8') as f:
                json.dump(range_info, f, ensure_ascii=False)
        except Exception as e:
            print(f"Error logging range info: {e}")

    def log_completion_info(self):
        """Log range completion information"""
        try:
            completion_info = {
                'type': 'completion',
                'process_id': self.process_id,
                'range_start': self.config['range_start'],
                'range_end': self.config['range_end'],
                'tab_type': self.tab_type,
                'total_attempts': self.attempts,
                'targets_found': self.targets_found,
                'start_time': self.start_time,
                'end_time': time.time(),
                'duration': time.time() - self.start_time,
                'timestamp': datetime.now().isoformat()
            }
            
            completion_file = os.path.join(STATS_DIR, f"completion_{self.process_id}.json")
            os.makedirs(os.path.dirname(completion_file), exist_ok=True)
            with open(completion_file, 'w', encoding='utf-8') as f:
                json.dump(completion_info, f, ensure_ascii=False)
                
            # Also write to common file for immediate reading
            immediate_completion_file = os.path.join(RESULTS_DIR, f"completion_{self.process_id}.json")
            os.makedirs(os.path.dirname(immediate_completion_file), exist_ok=True)
            with open(immediate_completion_file, 'w', encoding='utf-8') as f:
                json.dump(completion_info, f, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error logging completion info: {e}")

    def get_process_memory_usage(self):
        """Get current process memory usage in MB"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convert to MB
        except:
            return 0

    def generate_random_key_in_range(self, range_start, range_end, use_secrets):
        range_size = range_end - range_start
        if use_secrets:
            random_num = secrets.randbelow(range_size + 1)
        else:
            random_num = random.randint(0, range_size)
        key_int = range_start + random_num
        private_key = key_int.to_bytes(32, 'big').rjust(32, b'\x00')
        return key_int, private_key

    def generate_sequential_key(self):
        """Generate sequential key with unique range for process"""
        if self.current_key is None:
            # Initialize start position for process
            self.current_key = self.config['range_start'] + self.config['proc_id']
            self.step_size = self.config['processes']
            self.log_range_info()
        
        # Check if we've exceeded range bounds
        if self.current_key > self.config['range_end']:
            self.range_completed = True
            return None, None
        
        private_key = self.current_key.to_bytes(32, 'big').rjust(32, b'\x00')
        current_key = self.current_key
        
        # Move to next key with step equal to number of processes
        self.current_key += self.step_size
        
        return current_key, private_key

    def private_key_to_ripemd160(self, private_key, compressed=False):
        try:
            pub_key_obj = coincurve.PublicKey.from_valid_secret(private_key)
            pub_key = pub_key_obj.format(compressed=compressed)
            sha256_hash = hashlib.sha256(pub_key).digest()
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
            return ripemd160_hash
        except Exception as e:
            return None

    def save_match_immediately(self, match_info):
        """Immediately save found match to file"""
        try:
            match_file = os.path.join(RESULTS_DIR, f"matches_{self.process_id}.json")
            os.makedirs(os.path.dirname(match_file), exist_ok=True)
            with open(match_file, 'a', encoding='utf-8') as f:
                json.dump(match_info, f, ensure_ascii=False)
                f.write('\n')
                f.flush()  # Force write to disk
            return True
        except Exception as e:
            print(f"Error saving match immediately: {e}")
            return False

    def save_match_to_txt(self, match_info):
        """Save match to text file with all address formats"""
        try:
            txt_file = os.path.join(RESULTS_DIR, f"results_{self.process_id}.txt")
            os.makedirs(os.path.dirname(txt_file), exist_ok=True)
            
            # Generate all address formats
            private_key_hex = match_info['private_key']
            legacy_uncompressed = self.private_key_to_address(private_key_hex, "uncompressed")
            legacy_compressed = self.private_key_to_address(private_key_hex, "compressed")
            segwit_address = self.private_key_to_segwit_address(private_key_hex)
            
            # Format: key_hex64 \t ripemd160_hash \t legacy_uncompressed \t legacy_compressed \t segwit_address
            line = f"{private_key_hex}\t{match_info['ripemd160']}\t{legacy_uncompressed}\t{legacy_compressed}\t{segwit_address}\n"
            
            with open(txt_file, 'a', encoding='utf-8') as f:
                f.write(line)
                f.flush()
            return True
        except Exception as e:
            print(f"Error saving match to txt: {e}")
            return False

    def private_key_to_address(self, private_key_hex, address_type):
        """Convert private key to legacy address format"""
        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            
            if address_type == "uncompressed":
                compressed = False
            else:
                compressed = True
                
            pub_key_obj = coincurve.PublicKey.from_valid_secret(private_key_bytes)
            pub_key = pub_key_obj.format(compressed=compressed)
            
            sha256_hash = hashlib.sha256(pub_key).digest()
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
            
            if address_type == "uncompressed":
                extended_hash = b'\x00' + ripemd160_hash
            else:
                extended_hash = b'\x00' + ripemd160_hash
                
            checksum = hashlib.sha256(hashlib.sha256(extended_hash).digest()).digest()[:4]
            
            from base58 import b58encode
            address_bytes = extended_hash + checksum
            address = b58encode(address_bytes).decode('ascii')
            
            return address
            
        except Exception as e:
            return f"Error: {str(e)}"

    def private_key_to_segwit_address(self, private_key_hex):
        """Convert private key to native segwit bech32 address"""
        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            pub_key_obj = coincurve.PublicKey.from_valid_secret(private_key_bytes)
            pub_key = pub_key_obj.format(compressed=True)  # Segwit uses compressed keys
            
            sha256_hash = hashlib.sha256(pub_key).digest()
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
            
            # For native segwit (bech32) - version 0 witness program
            witness_program = b'\x00\x14' + ripemd160_hash  # version 0 + 20-byte program
            
            # Use bech32 encoding
            from bech32 import bech32_encode, convertbits
            hrp = "bc"
            data = convertbits(witness_program[2:], 8, 5)  # Convert to 5-bit array
            address = bech32_encode(hrp, data)
            
            return address
            
        except Exception as e:
            return f"Error: {str(e)}"

    def save_stats(self):
        """Save statistics to file"""
        try:
            stats_file = os.path.join(STATS_DIR, f"stats_{self.process_id}.json")
            os.makedirs(os.path.dirname(stats_file), exist_ok=True)
            elapsed = time.time() - self.start_time
            speed = self.attempts / elapsed if elapsed > 0 else 0
            
            # Get real process memory usage
            memory_usage = self.get_process_memory_usage()
            
            # For sequential mode add current position information
            current_position = None
            if self.config['search_method'] == 1 and self.current_key is not None:
                current_position = self.current_key - self.step_size  # Current processed key
            
            stats = {
                'process_id': self.process_id,
                'attempts': self.attempts,
                'targets_found': self.targets_found,
                'speed': speed,
                'memory': memory_usage,  # Real memory usage
                'running': self.running and not self.range_completed,
                'range_completed': self.range_completed,
                'current_position': current_position,
                'tab_type': self.tab_type,
                'timestamp': time.time()
            }
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving stats: {e}")

    def debug_log_key(self, key_int, private_key, ripemd160_uncompressed, ripemd160_compressed):
        """Log debug information about key"""
        if not self.debug_mode or self.debug_counter >= 1000:
            return
            
        try:
            debug_info = {
                'process_id': self.process_id,
                'key_int': key_int,
                'private_key_hex': private_key.hex().upper(),
                'ripemd160_uncompressed': ripemd160_uncompressed.hex().upper() if ripemd160_uncompressed else None,
                'ripemd160_compressed': ripemd160_compressed.hex().upper() if ripemd160_compressed else None,
                'timestamp': time.time()
            }
            
            debug_file = os.path.join(STATS_DIR, f"debug_{self.process_id}.json")
            os.makedirs(os.path.dirname(debug_file), exist_ok=True)
            with open(debug_file, 'a', encoding='utf-8') as f:
                json.dump(debug_info, f, ensure_ascii=False)
                f.write('\n')
                
            self.debug_counter += 1
            
        except Exception as e:
            print(f"Error in debug log: {e}")

    def add_log(self, message):
        """Add message to process log"""
        try:
            log_info = {
                'type': 'log',
                'process_id': self.process_id,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            
            log_file = os.path.join(RESULTS_DIR, f"process_log_{self.process_id}.json")
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'a', encoding='utf-8') as f:
                json.dump(log_info, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            print(f"Error adding process log: {e}")

    def run(self):
        """Main process work loop with correct logging"""
        try:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            
            # Log correct start position
            if self.config['search_method'] == 1:  # Sequential mode
                start_position = self.current_key if self.current_key is not None else self.config['range_start'] + self.config['proc_id']
                self.add_log(f"Process {self.process_id} sequential generation starting at: 0x{start_position:064X} with step {self.step_size} (tab: {self.tab_type})")
            else:
                self.add_log(f"Process {self.process_id} random generation in range: 0x{self.config['range_start']:064X} - 0x{self.config['range_end']:064X} (tab: {self.tab_type})")
            
            last_save_time = time.time()
            last_state_save_time = time.time()
            
            while self.running and (time.time() - self.start_time < self.config['max_time']) and not self.range_completed:
                try:
                    if self.config['search_method'] == 2:
                        # Random generation
                        key_int, private_key = self.generate_random_key_in_range(
                            self.config['range_start'],
                            self.config['range_end'],
                            self.config['use_secrets']
                        )
                    else:
                        # Sequential generation
                        result = self.generate_sequential_key()
                        if result[0] is None:
                            # Range completed for this process
                            self.range_completed = True
                            break
                        key_int, private_key = result
                    
                    ripemd160_uncompressed = self.private_key_to_ripemd160(private_key, compressed=False)
                    ripemd160_compressed = self.private_key_to_ripemd160(private_key, compressed=True)
                    
                    if ripemd160_uncompressed is None or ripemd160_compressed is None:
                        self.attempts += 1
                        self.batch_counter += 1
                        continue
                    # Debug logging
                    if self.debug_mode:
                        self.debug_log_key(key_int, private_key, ripemd160_uncompressed, ripemd160_compressed)
                    # IMMEDIATE processing of found matches
                    match_found = False
                    if ripemd160_uncompressed in self.config['target_hashes']:
                        match_info = {
                            'type': 'match',
                            'process_id': self.process_id,
                            'private_key': private_key.hex().upper(),
                            'ripemd160': ripemd160_uncompressed.hex().upper(),
                            'key_int': key_int,
                            'address_type': 'uncompressed',
                            'timestamp': datetime.now().isoformat()
                        }
                        # Immediately save to both JSON and TXT
                        self.save_match_immediately(match_info)
                        self.save_match_to_txt(match_info)
                        self.targets_found += 1
                        match_found = True
                    
                    if ripemd160_compressed in self.config['target_hashes']:
                        match_info = {
                            'type': 'match',
                            'process_id': self.process_id,
                            'private_key': private_key.hex().upper(),
                            'ripemd160': ripemd160_compressed.hex().upper(),
                            'key_int': key_int,
                            'address_type': 'compressed',
                            'timestamp': datetime.now().isoformat()
                        }
                        # Immediately save to both JSON and TXT
                        self.save_match_immediately(match_info)
                        self.save_match_to_txt(match_info)
                        self.targets_found += 1
                        match_found = True
                    self.attempts += 1
                    self.batch_counter += 1
                    
                    # 💾 PERIODIC STATE SAVING for sequential generation
                    current_time = time.time()
                    if (self.config['search_method'] == 1 and 
                        (self.batch_counter >= 50000 or (current_time - last_state_save_time) >= 300)):  # 5 minutes
                        
                        # Save process state with tab type
                        StateManager.save_state(
                            self.process_id, 
                            self.current_key - self.step_size,  # Current processed key
                            self.config['range_start'],
                            self.config['range_end'],
                            self.tab_type,  # Pass tab type
                            {
                                'attempts': self.attempts,
                                'targets_found': self.targets_found,
                                'batch_counter': self.batch_counter,
                                'start_time': self.start_time,
                                'step_size': self.step_size
                            }
                        )
                        
                        last_state_save_time = current_time
                        # DON'T reset batch_counter here!
                    
                    # Statistics saving separately from state
                    if self.batch_counter >= 10000:
                        self.save_stats()
                        # DON'T reset batch_counter here!
                        self.batch_counter = 0
                        
                except Exception as e:
                    continue
            # Save final statistics
            if self.range_completed:
                # Log range completion information
                self.log_completion_info()
                self.add_log(f"Process {self.process_id} completed work. Keys checked: {self.attempts:,}, Matches found: {self.targets_found} (tab: {self.tab_type})")
            
            # 💾 FINAL STATE SAVING BEFORE EXIT
            if self.config['search_method'] == 1 and self.current_key is not None:
                StateManager.save_state(
                    self.process_id, 
                    self.current_key - self.step_size,
                    self.config['range_start'],
                    self.config['range_end'],
                    self.tab_type,  # Pass tab type
                    {
                        'attempts': self.attempts,
                        'targets_found': self.targets_found,
                        'batch_counter': self.batch_counter,
                        'start_time': self.start_time,
                        'step_size': self.step_size,
                        'final_save': True
                    }
                )
            
            self.save_stats()
        except Exception as e:
            print(f"Process {self.process_id} error: {e}")

def worker_process(config):
    """Wrapper function for execution in separate process"""
    worker = WorkerProcess(config)
    worker.run()

class ProcessManager:
    """Manager for managing independent processes"""
    def __init__(self):
        self.processes = []
        self.running = False
        self.process_configs = {}

    def start_processes(self, configs):
        """Start processes with given configurations"""
        self.running = True
        self.process_configs = configs
        self.cleanup_old_files()
        
        for config in configs:
            p = Process(target=worker_process, args=(config,))
            p.daemon = True
            p.start()
            self.processes.append(p)

    def cleanup_old_files(self):
        """Clean old results and statistics files, but NOT state files"""
        try:
            # Clean only temporary files, NOT state files
            for file in os.listdir(RESULTS_DIR):
                if file.startswith('matches_') or file.startswith('process_log_') or file.startswith('completion_') or file.startswith('results_'):
                    os.remove(os.path.join(RESULTS_DIR, file))
            for file in os.listdir(STATS_DIR):
                if file.startswith('stats_') or file.startswith('range_') or file.startswith('debug_') or file.startswith('completion_'):
                    os.remove(os.path.join(STATS_DIR, file))
        except Exception as e:
            print(f"Error cleaning old files: {e}")

    def stop_processes(self):
        """Stop all processes"""
        self.running = False
        for p in self.processes:
            if p.is_alive():
                p.terminate()
        for p in self.processes:
            p.join(timeout=0.5)
        self.processes.clear()

    def are_processes_running(self):
        """Check if processes are running"""
        return any(p.is_alive() for p in self.processes)

class SoundPlayer:
    """Cross-platform sound player"""
    def __init__(self):
        self.sound_file = os.path.join(SCRIPT_DIR, "alerta.wav")
        self.pygame_available = False
        self.init_pygame()

    def init_pygame(self):
        """Initialize pygame if available"""
        try:
            import pygame
            pygame.mixer.init()
            self.pygame_available = True
            print("Pygame initialized successfully")
        except Exception as e:
            print(f"Pygame initialization failed: {e}")
            self.pygame_available = False

    def play(self):
        """Play sound"""
        try:
            if not os.path.exists(self.sound_file):
                print(f"Sound file not found: {self.sound_file}")
                return False
                
            if self.pygame_available:
                try:
                    import pygame
                    pygame.mixer.music.load(self.sound_file)
                    pygame.mixer.music.play()
                    print("Sound played successfully with pygame")
                    return True
                except Exception as e:
                    print(f"Error playing sound with pygame: {e}")
                    return False
            else:
                print("Pygame not available for sound playback")
                return False
        except Exception as e:
            print(f"Error in sound player: {e}")
            return False

class MatchDialog(QDialog):
    """Dialog window for match notification"""
    def __init__(self, match_info, parent=None):
        super().__init__(parent)
        self.match_info = match_info
        self.init_ui()
        
        # Auto close after 5 seconds
        QTimer.singleShot(5000, self.accept)

    def init_ui(self):
        self.setWindowTitle("Match Found!")
        self.setModal(False)
        self.resize(600, 300)
        
        layout = QVBoxLayout(self)
        
        title_label = QLabel("<h1>Match Found!</h1>")
        title_label.setStyleSheet("color: #FF0000; font-weight: bold;")
        layout.addWidget(title_label)
        
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details_text.setFont(QFont("Consolas", 9))
        
        details = f"""
Process: {self.match_info['process_id']}
Private Key: {self.match_info['private_key']}
RIPEMD-160: {self.match_info['ripemd160']}
Type: {self.match_info['address_type']}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        details_text.setText(details)
        layout.addWidget(details_text)
        
        button_box = QDialogButtonBox()
        ok_button = button_box.addButton(QDialogButtonBox.Ok)
        ok_button.clicked.connect(self.accept)
        layout.addWidget(button_box)

class StartButtonSource:
    """Enumeration of Start button sources"""
    STATUS_WIDGET = "status_widget"
    SETTINGS_TAB = "settings_tab"
    DECIMAL_TAB = "decimal_tab"
    HEX64_TAB = "hex64_tab"
    PERCENT_TAB = "percent_tab"

class StartManager:
    """Centralized dispatcher for handling all Start buttons"""
    def __init__(self, main_window):
        self.main_window = main_window
        self.last_range_tab = None  # Remember last range tab
    
    def handle_start_request(self, source):
        """Handle start request from any source"""
        try:
            self.main_window.add_log("=== Search Started ===")
            self.main_window.add_log(f"Source: {self._get_source_name(source)}")
            
            # Determine range and settings depending on source
            range_start, range_end, settings, log_details, tab_type = self._determine_range_and_settings(source)
            
            # Log details
            self.main_window.add_log(log_details)
            self.main_window.add_log(f"HEX range: 0x{range_start:064X} - 0x{range_end:064X}")
            self.main_window.add_log(f"Tab type: {tab_type}")
            
            total_keys = range_end - range_start + 1
            self.main_window.add_log(f"Keys in range: {total_keys:,}")
            
            # Calculate approximate search time
            if total_keys > 0:
                estimated_speed = self.main_window.last_speed if self.main_window.last_speed > 0 else 100000
                estimated_years = self.main_window.calculate_search_time_years(total_keys, estimated_speed)
                self.main_window.add_log(f"Estimated search time: {estimated_years}")
            
            self.main_window.add_log("==========================")
            
            # Apply range and settings
            self.main_window.range_start = range_start
            self.main_window.range_end = range_end
            self.main_window.expected_search_method = settings['search_method']
            self.main_window.current_tab_type = tab_type  # Store current tab type
            
            # Start search
            self._start_search_with_settings(settings, tab_type)
            
        except Exception as e:
            self.main_window.add_log(f"Error: {e}")
            QMessageBox.critical(self.main_window, "Error", f"Search start error: {str(e)}")
    
    def _get_source_name(self, source):
        """Get readable source name"""
        source_names = {
            StartButtonSource.STATUS_WIDGET: "Status Widget",
            StartButtonSource.SETTINGS_TAB: "Settings Tab", 
            StartButtonSource.DECIMAL_TAB: "Decimal Tab",
            StartButtonSource.HEX64_TAB: "Hex64 Tab",
            StartButtonSource.PERCENT_TAB: "Percent Tab"
        }
        return source_names.get(source, "Unknown source")
    
    def _determine_range_and_settings(self, source):
        """Determine range and settings depending on source"""
        if source == StartButtonSource.STATUS_WIDGET:
            return self._get_from_active_tab()
        elif source == StartButtonSource.SETTINGS_TAB:
            return self._get_from_settings_tab()
        elif source == StartButtonSource.DECIMAL_TAB:
            return self._get_from_decimal_tab()
        elif source == StartButtonSource.HEX64_TAB:
            return self._get_from_hex64_tab()
        elif source == StartButtonSource.PERCENT_TAB:
            return self._get_from_percent_tab()
        else:
            # Fallback to Decimal
            return self._get_from_decimal_tab()
    
    def _get_from_active_tab(self):
        """Get settings from active tab"""
        current_index = self.main_window.right_panel.currentIndex()
        
        if current_index == 1:  # Decimal
            return self._get_from_decimal_tab()
        elif current_index == 2:  # Hex64
            return self._get_from_hex64_tab()
        elif current_index == 3:  # Percent
            return self._get_from_percent_tab()
        else:
            # If active tab has no range, use last or Decimal
            if self.last_range_tab:
                return self._get_from_tab(self.last_range_tab)
            else:
                return self._get_from_decimal_tab()
    
    def _get_from_settings_tab(self):
        """Get settings for Settings tab"""
        # Use last active range tab
        if self.last_range_tab:
            range_start, range_end, settings, log_details, tab_type = self._get_from_tab(self.last_range_tab)
            log_details = f"Using last tab: {self.last_range_tab.tab_name}\n" + log_details
            return range_start, range_end, settings, log_details, tab_type
        else:
            # Fallback to Decimal
            self.main_window.add_log(f"No tab history, using Decimal by default")
            return self._get_from_decimal_tab()
    
    def _get_from_decimal_tab(self):
        """Get settings from Decimal tab"""
        tab = self.main_window.decimal_tab
        self.last_range_tab = tab
        return self._get_from_tab(tab)
    
    def _get_from_hex64_tab(self):
        """Get settings from Hex64 tab"""
        tab = self.main_window.hex64_tab
        self.last_range_tab = tab
        return self._get_from_tab(tab)
    
    def _get_from_percent_tab(self):
        """Get settings from Percent tab"""
        tab = self.main_window.percent_tab
        self.last_range_tab = tab
        return self._get_from_tab(tab)
    
    def _get_from_tab(self, tab):
        """Get settings from specific tab"""
        range_start, range_end = tab.calculate_range()
        
        # Get settings from tab widgets
        search_method = tab.method_widget.get_selected_method()
        gen_method = tab.type_widget.get_selected_type()
        
        # Get scan mode (continue or new)
        scan_mode = tab.mode_widget.get_selected_mode()
        continue_search = (scan_mode == 1)  # 1 = Continue scan (now default)
        
        # Determine tab type
        if hasattr(tab, 'tab_name'):
            if tab.tab_name == "Decimal":
                tab_type = "decimal"
            elif tab.tab_name == "hex64":
                tab_type = "hex64"
            elif tab.tab_name == "%%":
                tab_type = "percent"
            else:
                tab_type = "decimal"
        else:
            tab_type = "decimal"
        
        settings = {
            'search_method': search_method,
            'gen_method': gen_method,
            'use_secrets': gen_method == 1,
            'continue_search': continue_search,
            'tab_type': tab_type
        }
        
        method_text = tab.method_widget.get_selected_method_text()
        type_text = tab.type_widget.get_selected_type_text()
        mode_text = tab.mode_widget.get_selected_mode_text()
        
        log_details = f"Settings: {method_text}, {type_text}, {mode_text}"
        
        return range_start, range_end, settings, log_details, tab_type
    
    def _start_search_with_settings(self, settings, tab_type):
        """Start search with given settings"""
        try:
            # Prepare search
            result = self._prepare_search(settings, tab_type)
            if result[0] == 'success':
                self.main_window.on_search_prepared(result)
            else:
                self.main_window.add_log(f"Search preparation error: {result[1]}")
                QMessageBox.warning(self.main_window, "Error", str(result[1]))
                
        except Exception as e:
            self.main_window.add_log(f"Search start error: {e}")
            QMessageBox.critical(self.main_window, "Error", f"Search start error: {str(e)}")
    
    def _prepare_search(self, settings, tab_type):
        """Prepare search with given settings"""
        try:
            processes = self.main_window.process_spin.value()
            max_time = self.main_window.time_spin.value() * 3600 if self.main_window.time_spin.value() > 0 else float('inf')
            target_hashes = self.main_window.load_hashes_from_file()
            
            if not target_hashes:
                return ('error', "No target hashes found")
            # CRITICAL FIX: Automatic process limitation for sequential mode
            if settings['search_method'] == 1:  # Sequential mode
                total_keys = self.main_window.range_end - self.main_window.range_start + 1
                actual_processes = min(processes, total_keys)
                
                if actual_processes < processes:
                    self.main_window.add_log(f"Automatic process reduction: {processes} -> {actual_processes}")
                    self.main_window.add_log(f"Sequential mode limitation: cannot have more processes than keys")
                    processes = actual_processes
                    
                # Clean state if "New scan" mode selected
                if not settings['continue_search']:
                    self.main_window.add_log(f"🧹 Cleaning previous states for new search (tab: {tab_type})")
                    StateManager.cleanup_state_files(self.main_window.range_start, self.main_window.range_end, tab_type)
                else:
                    # Show existing states
                    existing_states = StateManager.list_state_files(tab_type)
                    if existing_states:
                        self.main_window.add_log(f"📁 Found previous states for {tab_type} tab. Continuing...")
                    else:
                        self.main_window.add_log(f"🆕 No previous states found for {tab_type} tab. Starting from beginning.")
            
            configs = []
            for i in range(processes):
                config = {
                    'proc_id': i,
                    'search_method': settings['search_method'],
                    'range_start': self.main_window.range_start,
                    'range_end': self.main_window.range_end,
                    'use_secrets': settings['use_secrets'],
                    'processes': processes,  # Important: pass actual process count
                    'max_time': max_time,
                    'target_hashes': target_hashes,
                    'continue_search': settings.get('continue_search', False),
                    'debug_mode': self.main_window.debug_mode,
                    'tab_type': tab_type  # Pass tab type to worker
                }
                configs.append(config)
                
            return ('success', configs)
        except Exception as e:
            return ('error', str(e))

class GenerationMethodWidget(QWidget):
    """Generation method selection widget"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.group = QGroupBox("1. Select generation method:")
        group_layout = QVBoxLayout(self.group)
        
        self.method_combo = QComboBox()
        self.method_combo.addItem("Sequential generation", 1)
        self.method_combo.addItem("Random generation", 2)
        
        group_layout.addWidget(self.method_combo)
        layout.addWidget(self.group)
        
    def get_selected_method(self):
        """Get selected method"""
        return self.method_combo.currentData()
    
    def get_selected_method_text(self):
        """Get selected method text"""
        return self.method_combo.currentText()

class GenerationTypeWidget(QWidget):
    """Generation type selection widget"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.group = QGroupBox("2. Generation method:")
        group_layout = QVBoxLayout(self.group)
        
        self.type_combo = QComboBox()
        self.type_combo.addItem("Cryptographically secure", 1)
        self.type_combo.addItem("Standard random", 2)
        
        group_layout.addWidget(self.type_combo)
        layout.addWidget(self.group)
        
    def get_selected_type(self):
        """Get selected type"""
        return self.type_combo.currentData()
    
    def get_selected_type_text(self):
        """Get selected type text"""
        return self.type_combo.currentText()

class ScanModeWidget(QWidget):
    """Scan mode selection widget"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.group = QGroupBox("3. Scan mode?")
        group_layout = QVBoxLayout(self.group)
        
        self.mode_combo = QComboBox()
        # Changed order: Continue scan is now first/default
        self.mode_combo.addItem("Continue scan", 1)
        self.mode_combo.addItem("New scan", 2)
        
        group_layout.addWidget(self.mode_combo)
        layout.addWidget(self.group)
        
    def get_selected_mode(self):
        """Get selected mode"""
        return self.mode_combo.currentData()
    
    def get_selected_mode_text(self):
        """Get selected mode text"""
        return self.mode_combo.currentText()

class StartStopButton(QPushButton):
    """Universal Start/Stop button for all tabs"""
    def __init__(self, parent=None, source=None):
        super().__init__("Start", parent)
        self.main_window = parent
        self.source = source
        self.setFixedSize(100, 40)
        self.clicked.connect(self.toggle_state)
        
    def toggle_state(self):
        """Toggle button state"""
        if self.text() == "Start":
            self.set_stop_state()
            if self.main_window and self.main_window.start_manager:
                self.main_window.start_manager.handle_start_request(self.source)
        else:
            self.set_start_state()
            if self.main_window:
                self.main_window.stop_search()
                
    def set_start_state(self):
        """Set Start state"""
        self.setText("Start")
        
    def set_stop_state(self):
        """Set Stop state"""
        self.setText("Stop")

class PauseResumeButton(QPushButton):
    """Universal Pause/Resume button for all tabs"""
    def __init__(self, parent=None):
        super().__init__("Pause", parent)
        self.main_window = parent
        self.setFixedSize(120, 40)
        self.clicked.connect(self.toggle_state)
        
    def toggle_state(self):
        """Toggle button state"""
        if self.text() == "Pause":
            self.set_resume_state()
            if self.main_window:
                self.main_window.pause_search()
        else:
            self.set_pause_state()
            if self.main_window:
                self.main_window.resume_search()
                
    def set_pause_state(self):
        """Set Pause state"""
        self.setText("Pause")
        
    def set_resume_state(self):
        """Set Resume state"""
        self.setText("Resume")

class RangeWidget(QWidget):
    """Base class for range setting widget"""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.title = title
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        self.range_group = QGroupBox(self.title)
        range_layout = QVBoxLayout(self.range_group)
        
        # Start value
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("from"))
        self.start_edit = QLineEdit()
        self.start_edit.setMinimumHeight(35)
        start_layout.addWidget(self.start_edit)
        range_layout.addLayout(start_layout)
        
        # End value
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("to"))
        self.end_edit = QLineEdit()
        self.end_edit.setMinimumHeight(35)
        end_layout.addWidget(self.end_edit)
        range_layout.addLayout(end_layout)
        
        # Apply and control buttons
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Apply range")
        self.apply_btn.setFixedSize(200, 40)
        
        self.start_stop_btn = StartStopButton(self.main_window, self._get_source())
        self.pause_resume_btn = PauseResumeButton(self.main_window)
        
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setFixedSize(150, 40)
        
        self.terminal_btn = QPushButton("Exit to terminal")
        self.terminal_btn.setFixedSize(170, 40)
        
        self.debug_btn = QPushButton("Debug")
        self.debug_btn.setFixedSize(100, 40)
        
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.start_stop_btn)
        button_layout.addWidget(self.pause_resume_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addWidget(self.terminal_btn)
        button_layout.addWidget(self.debug_btn)
        button_layout.addStretch()
        
        range_layout.addLayout(button_layout)
        
        layout.addWidget(self.range_group)
        
    def _get_source(self):
        """Get source for Start button (overridden in child classes)"""
        return StartButtonSource.SETTINGS_TAB
        
    def apply_range(self):
        """Abstract method - must be overridden in child classes"""
        pass
        
    def get_range_values(self):
        """Get range values"""
        return self.start_edit.text(), self.end_edit.text()
        
    def set_range_values(self, start, end):
        """Set range values"""
        self.start_edit.setText(start)
        self.end_edit.setText(end)
        
    def setup_connections(self):
        """Setup connections (overridden in child classes)"""
        self.apply_btn.clicked.connect(self.apply_range)
        self.reset_btn.clicked.connect(self.reset_settings)
        self.terminal_btn.clicked.connect(self.exit_to_terminal)
        self.debug_btn.clicked.connect(self.toggle_debug)
        
    def reset_settings(self):
        """Reset settings (overridden in child classes)"""
        pass
        
    def exit_to_terminal(self):
        """Exit to terminal"""
        if self.main_window:
            self.main_window.close()
            
    def toggle_debug(self):
        """Toggle debug mode"""
        if self.main_window:
            self.main_window.toggle_debug_mode()

class PercentRangeWidget(RangeWidget):
    """Percentage range widget"""
    def __init__(self, parent=None):
        super().__init__("Percentage range settings", parent)
        self.start_edit.setPlaceholderText("1")
        self.end_edit.setPlaceholderText("1000000")
        self.start_edit.setText("1")
        self.end_edit.setText("1000000")
        self.setup_connections()
        
    def _get_source(self):
        return StartButtonSource.PERCENT_TAB
        
    def apply_range(self):
        """Apply percentage range"""
        try:
            start_num = int(self.start_edit.text())
            end_num = int(self.end_edit.text())
            
            start_num = max(1, min(1000000, start_num))
            end_num = max(1, min(1000000, end_num))
            
            if start_num > end_num:
                start_num, end_num = end_num, start_num
                
            self.start_edit.setText(str(start_num))
            self.end_edit.setText(str(end_num))
            
            if self.main_window:
                self.main_window.add_log(f"Percent Tab: Range applied {start_num}% to {end_num}%")
                # Delayed range information update
                QTimer.singleShot(100, lambda: self.main_window.update_percent_range_info(start_num, end_num))
            
        except ValueError:
            self.reset_range()
            
    def reset_range(self):
        """Reset range to default values"""
        self.start_edit.setText("1")
        self.end_edit.setText("1000000")
        if self.main_window:
            self.main_window.add_log(f"Percent Tab: Range reset")
            
    def reset_settings(self):
        """Reset settings"""
        self.reset_range()
        if self.main_window:
            self.main_window.add_log(f"Percent Tab: Settings reset")

class Hex64RangeWidget(RangeWidget):
    """HEX64 range widget"""
    def __init__(self, parent=None):
        super().__init__("HEX64 range settings", parent)
        self.start_edit.setPlaceholderText("0x0000000000000000000000000000000000000000000000000000000000000001")
        self.end_edit.setPlaceholderText("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.start_edit.setText("0x0000000000000000000000000000000000000000000000000000000000000001")
        self.end_edit.setText("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.setup_connections()
        
    def _get_source(self):
        return StartButtonSource.HEX64_TAB
        
    def apply_range(self):
        """Apply HEX64 range"""
        try:
            start_text = self.start_edit.text().strip()
            end_text = self.end_edit.text().strip()
            
            if start_text.startswith('0x'):
                start_text = start_text[2:]
            if end_text.startswith('0x'):
                end_text = end_text[2:]
                
            start_int = int(start_text, 16)
            end_int = int(end_text, 16)
            
            start_int = max(MIN_KEY, min(MAX_KEY, start_int))
            end_int = max(MIN_KEY, min(MAX_KEY, end_int))
            
            if start_int > end_int:
                start_int, end_int = end_int, start_int
                
            self.start_edit.setText(f"0x{start_int:064X}")
            self.end_edit.setText(f"0x{end_int:064X}")
            
            if self.main_window:
                self.main_window.add_log(f"Hex64 Tab: Range applied 0x{start_int:064X} to 0x{end_int:064X}")
                # Delayed range information update
                QTimer.singleShot(100, lambda: self.main_window.update_hex64_range_info(start_int, end_int))
            
        except ValueError:
            self.reset_range()
            
    def reset_range(self):
        """Reset range to default values"""
        self.start_edit.setText("0x0000000000000000000000000000000000000000000000000000000000000001")
        self.end_edit.setText("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        if self.main_window:
            self.main_window.add_log(f"Hex64 Tab: Range reset")
            
    def reset_settings(self):
        """Reset settings"""
        self.reset_range()
        if self.main_window:
            self.main_window.add_log(f"Hex64 Tab: Settings reset")

class DecimalRangeWidget(RangeWidget):
    """Decimal format range widget"""
    def __init__(self, parent=None):
        super().__init__("Decimal range settings", parent)
        self.start_edit.setPlaceholderText("1")
        self.end_edit.setPlaceholderText("115792089237316195423570985008687907852837564279074904382605163141518161494336")
        self.start_edit.setText("1")
        self.end_edit.setText("115792089237316195423570985008687907852837564279074904382605163141518161494336")
        self.setup_connections()
        
    def _get_source(self):
        return StartButtonSource.DECIMAL_TAB
        
    def apply_range(self):
        """Apply range in decimal format"""
        try:
            start_int = int(self.start_edit.text())
            end_int = int(self.end_edit.text())
            
            start_int = max(MIN_KEY, min(MAX_KEY, start_int))
            end_int = max(MIN_KEY, min(MAX_KEY, end_int))
            
            if start_int > end_int:
                start_int, end_int = end_int, start_int
                
            self.start_edit.setText(str(start_int))
            self.end_edit.setText(str(end_int))
            
            if self.main_window:
                self.main_window.add_log(f"Decimal Tab: Range applied {start_int} to {end_int}")
                # Delayed range information update
                QTimer.singleShot(100, lambda: self.main_window.update_decimal_range_info(start_int, end_int))
            
        except ValueError:
            self.reset_range()
            
    def reset_range(self):
        """Reset range to default values"""
        self.start_edit.setText("1")
        self.end_edit.setText("115792089237316195423570985008687907852837564279074904382605163141518161494336")
        if self.main_window:
            self.main_window.add_log(f"Decimal Tab: Range reset")
            
    def reset_settings(self):
        """Reset settings"""
        self.reset_range()
        if self.main_window:
            self.main_window.add_log(f"Decimal Tab: Settings reset")

class ScrollableTab(QScrollArea):
    """Scrollable area for tabs"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.content_widget = QWidget()
        self.setWidget(self.content_widget)
        
    def set_layout(self, layout):
        """Set layout for content"""
        self.content_widget.setLayout(layout)

class PercentTab(ScrollableTab):
    """Tab for working with percentage ranges"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.tab_name = "%%"
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Generation method section
        self.method_widget = GenerationMethodWidget(self)
        self.type_widget = GenerationTypeWidget(self)
        self.mode_widget = ScanModeWidget(self)
        
        layout.addWidget(self.method_widget)
        layout.addWidget(self.type_widget)
        layout.addWidget(self.mode_widget)
        
        # Percentage range settings
        self.range_widget = PercentRangeWidget(self.main_window)
        layout.addWidget(self.range_widget)
        
        # Range information
        self.info_group = QGroupBox("Range information")
        info_layout = QVBoxLayout(self.info_group)
        
        # Number of keys
        keys_layout = QHBoxLayout()
        keys_layout.addWidget(QLabel("Keys in range:"))
        self.keys_label = QLabel("0")
        self.keys_label.setMinimumHeight(30)
        keys_layout.addWidget(self.keys_label)
        keys_layout.addStretch()
        info_layout.addLayout(keys_layout)
        
        # Final range
        final_range_layout = QVBoxLayout()
        final_range_layout.addWidget(QLabel("Final HEX range:"))
        self.final_range_label = QLabel("0x0000000000000000000000000000000000000000000000000000000000000001 - 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.final_range_label.setWordWrap(True)
        self.final_range_label.setMinimumHeight(50)
        final_range_layout.addWidget(self.final_range_label)
        info_layout.addLayout(final_range_layout)
        
        layout.addWidget(self.info_group)
        
        layout.addStretch()
        
        self.set_layout(layout)
        
        # Connect signals
        self.setup_connections()
        # Delayed range information initialization
        QTimer.singleShot(100, self.apply_range)
        
    def setup_connections(self):
        """Setup connections"""
        # Connect signals for dropdown menus
        self.method_widget.method_combo.currentIndexChanged.connect(self.on_method_changed)
        self.type_widget.type_combo.currentIndexChanged.connect(self.on_type_changed)
        self.mode_widget.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        
    def on_method_changed(self, index):
        """Generation method change handler"""
        method_text = self.method_widget.get_selected_method_text()
        self.main_window.add_log(f"Percent Tab: Selected method '{method_text}'")
        
    def on_type_changed(self, index):
        """Generation type change handler"""
        type_text = self.type_widget.get_selected_type_text()
        self.main_window.add_log(f"Percent Tab: Selected type '{type_text}'")
        
    def on_mode_changed(self, index):
        """Scan mode change handler"""
        mode_text = self.mode_widget.get_selected_mode_text()
        self.main_window.add_log(f"Percent Tab: Selected mode '{mode_text}'")
        
    def apply_range(self):
        """Apply range"""
        self.range_widget.apply_range()
            
    def calculate_range(self):
        """Calculate range based on percentage values"""
        try:
            start_num = int(self.range_widget.start_edit.text())
            end_num = int(self.range_widget.end_edit.text())
            
            total_range = MAX_KEY - MIN_KEY + 1
            
            start_position = ((start_num - 1) * total_range) // 1000000
            end_position = (end_num * total_range) // 1000000
            
            start_position = max(0, min(total_range - 1, start_position))
            end_position = max(0, min(total_range - 1, end_position))
            
            start_key = MIN_KEY + start_position
            end_key = MIN_KEY + end_position
            
            start_key = max(MIN_KEY, min(MAX_KEY, start_key))
            end_key = max(MIN_KEY, min(MAX_KEY, end_key))
            
            if end_key <= start_key:
                end_key = min(MAX_KEY, start_key + 1)
            
            return start_key, end_key
        except ValueError:
            return MIN_KEY, MAX_KEY
        
    def update_range_info(self, start_key, end_key):
        """Update range information"""
        total_keys = end_key - start_key + 1
        
        self.keys_label.setText(f"{total_keys:,}")
        self.final_range_label.setText(f"0x{start_key:064X} - 0x{end_key:064X}")

class Hex64Tab(ScrollableTab):
    """Tab for working with HEX64 ranges"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.tab_name = "hex64"
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Generation method section
        self.method_widget = GenerationMethodWidget(self)
        self.type_widget = GenerationTypeWidget(self)
        self.mode_widget = ScanModeWidget(self)
        
        layout.addWidget(self.method_widget)
        layout.addWidget(self.type_widget)
        layout.addWidget(self.mode_widget)
        
        # HEX64 range settings
        self.range_widget = Hex64RangeWidget(self.main_window)
        layout.addWidget(self.range_widget)
        
        # Range information
        self.info_group = QGroupBox("Range information")
        info_layout = QVBoxLayout(self.info_group)
        
        # Number of keys
        keys_layout = QHBoxLayout()
        keys_layout.addWidget(QLabel("Keys in range:"))
        self.keys_label = QLabel("0")
        self.keys_label.setMinimumHeight(30)
        keys_layout.addWidget(self.keys_label)
        keys_layout.addStretch()
        info_layout.addLayout(keys_layout)
        
        # Final range
        final_range_layout = QVBoxLayout()
        final_range_layout.addWidget(QLabel("Final HEX range:"))
        self.final_range_label = QLabel("0x0000000000000000000000000000000000000000000000000000000000000001 - 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.final_range_label.setWordWrap(True)
        self.final_range_label.setMinimumHeight(50)
        final_range_layout.addWidget(self.final_range_label)
        info_layout.addLayout(final_range_layout)
        
        layout.addWidget(self.info_group)
        
        layout.addStretch()
        
        self.set_layout(layout)
        
        # Connect signals
        self.setup_connections()
        # Delayed range information initialization
        QTimer.singleShot(100, self.apply_range)
        
    def setup_connections(self):
        """Setup connections"""
        # Connect signals for dropdown menus
        self.method_widget.method_combo.currentIndexChanged.connect(self.on_method_changed)
        self.type_widget.type_combo.currentIndexChanged.connect(self.on_type_changed)
        self.mode_widget.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        
    def on_method_changed(self, index):
        """Generation method change handler"""
        method_text = self.method_widget.get_selected_method_text()
        self.main_window.add_log(f"Hex64 Tab: Selected method '{method_text}'")
        
    def on_type_changed(self, index):
        """Generation type change handler"""
        type_text = self.type_widget.get_selected_type_text()
        self.main_window.add_log(f"Hex64 Tab: Selected type '{type_text}'")
        
    def on_mode_changed(self, index):
        """Scan mode change handler"""
        mode_text = self.mode_widget.get_selected_mode_text()
        self.main_window.add_log(f"Hex64 Tab: Selected mode '{mode_text}'")
            
    def apply_range(self):
        """Apply range"""
        self.range_widget.apply_range()
            
    def calculate_range(self):
        """Calculate range based on HEX values"""
        try:
            start_text = self.range_widget.start_edit.text().strip()
            end_text = self.range_widget.end_edit.text().strip()
            
            if start_text.startswith('0x'):
                start_text = start_text[2:]
            if end_text.startswith('0x'):
                end_text = end_text[2:]
                
            start_int = int(start_text, 16)
            end_int = int(end_text, 16)
            
            start_int = max(MIN_KEY, min(MAX_KEY, start_int))
            end_int = max(MIN_KEY, min(MAX_KEY, end_int))
            
            if start_int > end_int:
                start_int, end_int = end_int, start_int
                
            return start_int, end_int
            
        except ValueError:
            return MIN_KEY, MAX_KEY
        
    def update_range_info(self, start_key, end_key):
        """Update range information"""
        total_keys = end_key - start_key + 1
        
        self.keys_label.setText(f"{total_keys:,}")
        self.final_range_label.setText(f"0x{start_key:064X} - 0x{end_key:064X}")

class DecimalTab(ScrollableTab):
    """Tab for working with decimal ranges"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.tab_name = "Decimal"
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Generation method section
        self.method_widget = GenerationMethodWidget(self)
        self.type_widget = GenerationTypeWidget(self)
        self.mode_widget = ScanModeWidget(self)
        
        layout.addWidget(self.method_widget)
        layout.addWidget(self.type_widget)
        layout.addWidget(self.mode_widget)
        
        # Decimal format range settings
        self.range_widget = DecimalRangeWidget(self.main_window)
        layout.addWidget(self.range_widget)
        
        # Range information
        self.info_group = QGroupBox("Range information")
        info_layout = QVBoxLayout(self.info_group)
        
        # Number of keys
        keys_layout = QHBoxLayout()
        keys_layout.addWidget(QLabel("Keys in range:"))
        self.keys_label = QLabel("0")
        self.keys_label.setMinimumHeight(30)
        keys_layout.addWidget(self.keys_label)
        keys_layout.addStretch()
        info_layout.addLayout(keys_layout)
        
        # Final range
        final_range_layout = QVBoxLayout()
        final_range_layout.addWidget(QLabel("Final HEX range:"))
        self.final_range_label = QLabel("0x0000000000000000000000000000000000000000000000000000000000000001 - 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.final_range_label.setWordWrap(True)
        self.final_range_label.setMinimumHeight(50)
        final_range_layout.addWidget(self.final_range_label)
        info_layout.addLayout(final_range_layout)
        
        layout.addWidget(self.info_group)
        
        layout.addStretch()
        
        self.set_layout(layout)
        
        # Connect signals
        self.setup_connections()
        # Delayed range information initialization
        QTimer.singleShot(100, self.apply_range)
        
    def setup_connections(self):
        """Setup connections"""
        # Connect signals for dropdown menus
        self.method_widget.method_combo.currentIndexChanged.connect(self.on_method_changed)
        self.type_widget.type_combo.currentIndexChanged.connect(self.on_type_changed)
        self.mode_widget.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        
    def on_method_changed(self, index):
        """Generation method change handler"""
        method_text = self.method_widget.get_selected_method_text()
        self.main_window.add_log(f"Decimal Tab: Selected method '{method_text}'")
        
    def on_type_changed(self, index):
        """Generation type change handler"""
        type_text = self.type_widget.get_selected_type_text()
        self.main_window.add_log(f"Decimal Tab: Selected type '{type_text}'")
        
    def on_mode_changed(self, index):
        """Scan mode change handler"""
        mode_text = self.mode_widget.get_selected_mode_text()
        self.main_window.add_log(f"Decimal Tab: Selected mode '{mode_text}'")
            
    def apply_range(self):
        """Apply range"""
        self.range_widget.apply_range()
            
    def calculate_range(self):
        """Calculate range based on decimal values"""
        try:
            start_int = int(self.range_widget.start_edit.text())
            end_int = int(self.range_widget.end_edit.text())
            
            start_int = max(MIN_KEY, min(MAX_KEY, start_int))
            end_int = max(MIN_KEY, min(MAX_KEY, end_int))
            
            if start_int > end_int:
                start_int, end_int = end_int, start_int
                
            return start_int, end_int
            
        except ValueError:
            return MIN_KEY, MAX_KEY
        
    def update_range_info(self, start_key, end_key):
        """Update range information"""
        total_keys = end_key - start_key + 1
        
        self.keys_label.setText(f"{total_keys:,}")
        self.final_range_label.setText(f"0x{start_key:064X} - 0x{end_key:064X}")

class ThemeComboBox(QComboBox):
    """Dropdown list for theme selection"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()
        
    def init_ui(self):
        """Initialize UI"""
        available_themes = ThemeManager.get_available_themes()
        for theme in available_themes:
            self.addItem(theme.replace('_', ' ').title(), theme)
        
        # Set default theme
        default_theme = "light"
        index = self.findData(default_theme)
        if index >= 0:
            self.setCurrentIndex(index)
        
        self.currentIndexChanged.connect(self.on_theme_changed)
    
    def on_theme_changed(self, index):
        """Theme change handler"""
        theme_name = self.currentData()
        if self.main_window:
            self.main_window.apply_theme(theme_name)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.process_manager = ProcessManager()
        self.sound_player = SoundPlayer()
        self.start_manager = StartManager(self)  # Centralized start dispatcher
        self.theme_manager = ThemeManager()
        self.state_manager = StateManager()  # State manager for sequential generation
        
        self.process_stats = {}
        self.total_attempts = 0
        self.total_targets = 0
        self.start_time = None
        self.current_theme = "light"
        self.is_paused = False
        self.physical_memory_gb = self.get_physical_memory()
        self.range_start = MIN_KEY
        self.range_end = MAX_KEY
        self.max_processes = cpu_count()
        self.completed_processes_count = 0
        self.total_processes = 0
        self.last_speed = 0
        self.process_start_times = {}
        self.process_progress = {}
        self.current_tab_name = "Settings"
        self.current_tab_type = "decimal"  # Track current tab type
        self.debug_mode = False
        self.expected_search_method = None
        self.found_hashes = set()
        self.completion_shown = False
        
        # Matrix background
        self.matrix_background = None
        
        # References to all tab buttons for synchronization
        self.start_stop_buttons = []
        self.pause_resume_buttons = []
        
        # Tab references
        self.percent_tab = None
        self.hex64_tab = None  
        self.decimal_tab = None
        
        # CREATE DIRECTORIES ON STARTUP
        self.create_directories_on_start()
        
        self.log_text = None
        self.debug_btn = None
        self.init_ui()
        self.setup_connections()
        
        # Clear tables on startup
        self.clear_statistics_table()
        
        # Set Settings tab as active by default
        self.right_panel.setCurrentIndex(0)
        
        # Apply default theme
        self.apply_theme("light")
        
        # Run self-test on startup
        QTimer.singleShot(1000, self.run_self_test)

    def create_directories_on_start(self):
        """Create all necessary directories on startup"""
        directories = [JSON_DIR, TXT_DIR, RESULTS_DIR, STATS_DIR, THEMES_DIR, STATE_DIR]
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"✅ Directory created/verified: {directory}")
            except Exception as e:
                print(f"❌ Error creating directory {directory}: {e}")

    def get_physical_memory(self):
        """Get physical memory in GB"""
        try:
            return psutil.virtual_memory().total / (1024 ** 3)
        except:
            return 16.0

    def cleanup_old_files_on_start(self):
        """Clean old statistics files on application startup, but NOT state files"""
        try:
            for file in os.listdir(STATS_DIR):
                if file.startswith('stats_') or file.startswith('range_') or file.startswith('debug_') or file.startswith('completion_'):
                    os.remove(os.path.join(STATS_DIR, file))
            for file in os.listdir(RESULTS_DIR):
                if file.startswith('matches_') or file.startswith('completion_') or file.startswith('process_log_') or file.startswith('results_'):
                    os.remove(os.path.join(RESULTS_DIR, file))
        except Exception as e:
            print(f"Error cleaning old files on start: {e}")

    def init_ui(self):
        self.setWindowTitle("Bitcoin365 Office Suite")
        self.setGeometry(100, 100, 1100, 740)
        self.setMinimumSize(1100, 740)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.right_panel = QTabWidget()
        
        # Settings Tab
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(10)
        
        # STATUS WIDGET
        self.status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(self.status_group)
        
        # Top status row
        status_top_layout = QHBoxLayout()
        
        self.status_ready = QLabel("Status: Ready")
        self.status_memory = QLabel("Memory: 0 MB")
        self.status_uptime = QLabel("Uptime: 00:00:00")
        self.status_speed = QLabel("Speed: 0 keys/sec")
        self.status_found = QLabel("Found: 0")
        self.status_keys = QLabel("Keys: 0")
        
        for status_label in [self.status_ready, self.status_memory, self.status_uptime, 
                           self.status_speed, self.status_found, self.status_keys]:
            status_label.setMinimumWidth(120)
            status_label.setAlignment(Qt.AlignCenter)
        
        status_top_layout.addWidget(self.status_ready)
        status_top_layout.addWidget(self.status_memory)
        status_top_layout.addWidget(self.status_uptime)
        status_top_layout.addWidget(self.status_speed)
        status_top_layout.addWidget(self.status_found)
        status_top_layout.addWidget(self.status_keys)
        
        # Add control buttons to status row
        self.start_stop_btn = StartStopButton(self, StartButtonSource.STATUS_WIDGET)
        self.pause_resume_btn = PauseResumeButton(self)
        
        # Save references for synchronization
        self.start_stop_buttons.append(self.start_stop_btn)
        self.pause_resume_buttons.append(self.pause_resume_btn)
        
        status_top_layout.addWidget(self.start_stop_btn)
        status_top_layout.addWidget(self.pause_resume_btn)
        status_top_layout.addStretch()
        
        status_layout.addLayout(status_top_layout)
        
        # Memory usage information
        memory_info_layout = QHBoxLayout()
        self.memory_usage_label = QLabel("Total memory usage 0 GB, 0%")
        memory_info_layout.addWidget(self.memory_usage_label)
        status_layout.addLayout(memory_info_layout)
        
        # Memory progress bar
        memory_progress_layout = QHBoxLayout()
        self.memory_progress = QProgressBar()
        self.memory_progress.setMaximum(100)
        memory_progress_layout.addWidget(self.memory_progress)
        status_layout.addLayout(memory_progress_layout)
        
        settings_layout.addWidget(self.status_group)
        
        # Process configuration
        self.process_group = QGroupBox("Process Configuration")
        process_layout = QVBoxLayout(self.process_group)
        
        # Top row - main settings
        process_top_layout = QHBoxLayout()
        
        self.processes_label = QLabel("Number of processes:")
        process_top_layout.addWidget(self.processes_label)
        self.process_spin = QSpinBox()
        self.process_spin.setRange(1, self.max_processes)
        self.process_spin.setValue(min(self.max_processes, 12))
        process_top_layout.addWidget(self.process_spin)
        
        self.time_label = QLabel("Time limit:")
        process_top_layout.addWidget(self.time_label)
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(0, 1000)
        self.time_spin.setValue(0)
        self.time_spin.setSuffix(" hours (0 = no limit)")
        process_top_layout.addWidget(self.time_spin)
        
        # Theme selection moved to same row
        self.theme_label = QLabel("Color theme:")
        process_top_layout.addWidget(self.theme_label)
        self.theme_combo = ThemeComboBox(self)
        process_top_layout.addWidget(self.theme_combo)
        
        process_top_layout.addStretch()
        
        process_layout.addLayout(process_top_layout)
        
        settings_layout.addWidget(self.process_group)
        
        # Process table
        self.process_table_group = QGroupBox("Process Table")
        self.process_table_group.setMinimumHeight(400)
        process_table_layout = QVBoxLayout(self.process_table_group)
        
        self.process_table = QTableWidget()
        self.process_table.setColumnCount(8)
        self.process_table.verticalHeader().setDefaultSectionSize(25)
        self.process_table.setAlternatingRowColors(True)
        process_table_layout.addWidget(self.process_table)
        
        settings_layout.addWidget(self.process_table_group)
        settings_layout.addStretch(1)
        
        # Create tabs with scrollable areas
        self.percent_tab = PercentTab(self)
        self.hex64_tab = Hex64Tab(self)
        self.decimal_tab = DecimalTab(self)
        
        # Save references to buttons from all tabs
        # Buttons are now in range widgets
        for tab in [self.percent_tab, self.hex64_tab, self.decimal_tab]:
            if hasattr(tab.range_widget, 'start_stop_btn'):
                self.start_stop_buttons.append(tab.range_widget.start_stop_btn)
            if hasattr(tab.range_widget, 'pause_resume_btn'):
                self.pause_resume_buttons.append(tab.range_widget.pause_resume_btn)
        
        # Results tab
        results_tab = QWidget()
        results_layout = QVBoxLayout(results_tab)
        
        # Add save results button at top
        self.save_results_btn = QPushButton("Save results")
        self.save_results_btn.clicked.connect(self.save_results_to_file)
        results_layout.addWidget(self.save_results_btn)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(10)
        self.results_table.setRowCount(0)
        self.update_results_headers()
        results_layout.addWidget(self.results_table)
        
        # Log tab
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        
        # "Launch Parameters" widget
        self.launch_params_group = QGroupBox("Launch Parameters")
        self.launch_params_group.setMaximumHeight(201)
        launch_params_layout = QVBoxLayout(self.launch_params_group)
        
        self.launch_params_text = QTextEdit()
        self.launch_params_text.setReadOnly(True)
        self.launch_params_text.setMaximumHeight(200)
        self.launch_params_text.setFont(QFont("Consolas", 8))
        self.launch_params_text.setPlainText("Launch parameters will be displayed here")
        
        launch_params_layout.addWidget(self.launch_params_text)
        
        log_layout.addWidget(self.launch_params_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        # Help tab
        help_tab = QWidget()
        help_layout = QVBoxLayout(help_tab)
        
        self.help_browser = QTextBrowser()
        self.help_browser.setOpenExternalLinks(True)
        help_layout.addWidget(self.help_browser)
        
        self.load_help_content()
        
        # Add tabs
        self.right_panel.addTab(settings_tab, "Settings")
        self.right_panel.addTab(self.decimal_tab, "Decimal")
        self.right_panel.addTab(self.hex64_tab, "hex64")
        self.right_panel.addTab(self.percent_tab, "%%")
        self.right_panel.addTab(results_tab, "Results")
        self.right_panel.addTab(log_tab, "Log")
        self.right_panel.addTab(help_tab, "Help")
        
        main_layout.addWidget(self.right_panel)
        
        # Create status bar with extended information
        self.status_bar = self.statusBar()
        self.status_label = QLabel()
        self.status_bar.addWidget(self.status_label)
        
        # Initialize status bar with default values
        self.update_status_bar()
        
        # Connect tab change signal
        self.right_panel.currentChanged.connect(self.on_tab_changed)
        
        # Ensure central widget is properly configured for transparency
        central_widget.setAutoFillBackground(False)
        central_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        central_widget.setAttribute(Qt.WA_StyledBackground, True)

    def update_status_bar(self):
        """Update status bar with current statistics"""
        try:
            # Get current values from status widgets
            memory_text = self.status_memory.text().replace("Memory: ", "")
            speed_text = self.status_speed.text().replace("Speed: ", "")
            keys_text = self.status_keys.text().replace("Keys: ", "")
            uptime_text = self.status_uptime.text().replace("Uptime: ", "")
            found_text = self.status_found.text().replace("Found: ", "")
            
            # Format status bar text
            status_text = f"Memory: {memory_text} | Speed: {speed_text} | Total keys: {keys_text} | Uptime: {uptime_text} | Found: {found_text} | Script directory: {SCRIPT_DIR}"
            
            self.status_label.setText(status_text)
            
        except Exception as e:
            print(f"Error updating status bar: {e}")
            # Fallback to basic information
            self.status_label.setText(f"Script directory: {SCRIPT_DIR}")

    def apply_theme(self, theme_name):
        """Apply selected theme"""
        try:
            # Remove matrix background if it existed
            if self.matrix_background:
                self.matrix_background.setParent(None)
                self.matrix_background.deleteLater()
                self.matrix_background = None
            
            stylesheet = self.theme_manager.load_theme(theme_name)
            if stylesheet:
                self.setStyleSheet(stylesheet)
                self.current_theme = theme_name
                
                # For matrix theme add animated background ON FOREGROUND
                if theme_name == "matrix":
                    QTimer.singleShot(100, self.apply_matrix_background)  # Delayed start
                
                self.add_log(f"Applied theme: {theme_name}")
            else:
                self.add_log(f"Failed to load theme: {theme_name}")
        except Exception as e:
            self.add_log(f"Error applying theme {theme_name}: {e}")
    
    def apply_matrix_background(self):
        """Add matrix background for matrix theme ON FOREGROUND"""
        try:
            # Remove old background if existed
            if self.matrix_background:
                self.matrix_background.setParent(None)
                self.matrix_background.deleteLater()
                self.matrix_background = None
            
            # Create new background
            self.matrix_background = MatrixBackground(self.centralWidget())
            
            # CRITICALLY IMPORTANT: Set geometry and RAISE TO FOREGROUND
            self.matrix_background.setGeometry(self.centralWidget().rect())
            
            # IMPORTANT: Raise to foreground, not lower!
            self.matrix_background.raise_()  # Now it will be above all widgets
            
            # Ensure background doesn't intercept mouse events
            self.matrix_background.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            
            # Show widget
            self.matrix_background.show()
            
            self.add_log("Matrix background activated ON FOREGROUND")
            
        except Exception as e:
            self.add_log(f"Error creating matrix background: {e}")
    
    def resizeEvent(self, event):
        """Window resize event handler"""
        super().resizeEvent(event)
        if self.matrix_background:
            # Update background geometry when window size changes
            self.matrix_background.setGeometry(self.centralWidget().rect())
            # RE-RAISE to foreground after resize
            self.matrix_background.raise_()

    def update_percent_range_info(self, start_percent, end_percent):
        """Update range information for percent tab"""
        if hasattr(self, 'percent_tab') and self.percent_tab:
            start_key, end_key = self.calculate_percent_range(start_percent, end_percent)
            self.percent_tab.update_range_info(start_key, end_key)
            
    def update_hex64_range_info(self, start_key, end_key):
        """Update range information for hex64 tab"""
        if hasattr(self, 'hex64_tab') and self.hex64_tab:
            self.hex64_tab.update_range_info(start_key, end_key)
            
    def update_decimal_range_info(self, start_key, end_key):
        """Update range information for decimal tab"""
        if hasattr(self, 'decimal_tab') and self.decimal_tab:
            self.decimal_tab.update_range_info(start_key, end_key)
            
    def calculate_percent_range(self, start_percent, end_percent):
        """Calculate range based on percentage values"""
        total_range = MAX_KEY - MIN_KEY + 1
        
        start_position = ((start_percent - 1) * total_range) // 1000000
        end_position = (end_percent * total_range) // 1000000
        
        start_position = max(0, min(total_range - 1, start_position))
        end_position = max(0, min(total_range - 1, end_position))
        
        start_key = MIN_KEY + start_position
        end_key = MIN_KEY + end_position
        
        start_key = max(MIN_KEY, min(MAX_KEY, start_key))
        end_key = max(MIN_KEY, min(MAX_KEY, end_key))
        
        if end_key <= start_key:
            end_key = min(MAX_KEY, start_key + 1)
        
        return start_key, end_key

    def sync_start_stop_buttons(self, state):
        """Synchronize state of all Start/Stop buttons"""
        for button in self.start_stop_buttons:
            if state == "start":
                button.set_stop_state()
            else:
                button.set_start_state()
                
    def sync_pause_resume_buttons(self, state):
        """Synchronize state of all Pause/Resume buttons"""
        for button in self.pause_resume_buttons:
            if state == "pause":
                button.set_resume_state()
            else:
                button.set_pause_state()

    def save_results_to_file(self):
        """Save results to TSV file"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Save results", 
                os.path.join(RESULTS_DIR, "results.tsv"), 
                "TSV Files (*.tsv);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # Write headers
                    headers = []
                    for col in range(self.results_table.columnCount()):
                        headers.append(self.results_table.horizontalHeaderItem(col).text())
                    f.write("\t".join(headers) + "\n")
                    
                    # Write data
                    for row in range(self.results_table.rowCount()):
                        row_data = []
                        for col in range(self.results_table.columnCount()):
                            item = self.results_table.item(row, col)
                            if item is not None:
                                row_data.append(item.text())
                            else:
                                row_data.append("")
                        f.write("\t".join(row_data) + "\n")
                
                self.add_log(f"Results saved: {file_path}")
                QMessageBox.information(self, "Success", f"Results successfully saved:\n{file_path}")
                
        except Exception as e:
            self.add_log(f"Error saving results: {e}")
            QMessageBox.critical(self, "Error", f"Error saving results:\n{str(e)}")

    def on_tab_changed(self, index):
        """Tab change handler"""
        tab_names = {
            0: "Settings",
            1: "Decimal", 
            2: "hex64",
            3: "%",
            4: "Results",
            5: "Log",
            6: "Help"
        }
        
        tab_name = tab_names.get(index, f"Tab {index}")
        self.current_tab_name = tab_name
        
        # Update current tab type
        if tab_name == "Decimal":
            self.current_tab_type = "decimal"
        elif tab_name == "hex64":
            self.current_tab_type = "hex64"
        elif tab_name == "%":
            self.current_tab_type = "percent"
        else:
            self.current_tab_type = "decimal"
            
        self.add_log(f"Selected tab: '{tab_name}' (type: {self.current_tab_type})")

    def clear_statistics_table(self):
        """Clear statistics table and fill with zeros"""
        processes = self.process_spin.value()
        self.process_table.setRowCount(processes)
        self.update_table_headers()
        
        # Fill table with zeros
        for i in range(processes):
            self.process_table.setItem(i, 0, QTableWidgetItem(f"Process {i}"))
            self.process_table.setItem(i, 1, QTableWidgetItem("0"))
            self.process_table.setItem(i, 2, QTableWidgetItem("0/s"))
            self.process_table.setItem(i, 3, QTableWidgetItem("0"))
            self.process_table.setItem(i, 4, QTableWidgetItem("0 MB"))
            self.process_table.setItem(i, 5, QTableWidgetItem("Ready"))
            self.process_table.setItem(i, 6, QTableWidgetItem("00:00:00"))
            self.process_table.setItem(i, 7, QTableWidgetItem("∞ years"))
        
        # Reset status
        self.status_ready.setText("Status: Ready")
        self.status_memory.setText("Memory: 0 MB")
        self.status_uptime.setText("Uptime: 00:00:00")
        self.status_speed.setText("Speed: 0 keys/sec")
        self.status_found.setText("Found: 0")
        self.status_keys.setText("Keys: 0")
        self.memory_usage_label.setText("Total memory usage 0 GB, 0%")
        self.memory_progress.setValue(0)
        
        # Update status bar
        self.update_status_bar()

    def run_self_test(self):
        """Run self-testing"""
        self.add_log("=" * 80)
        self.add_log("Running self-test")
        self.add_log("=" * 80)
        
        # Check statistics table clearing
        self.add_log("Checking statistics table:")
        self.clear_statistics_table()
        
        # Test state directory
        self.add_log("Testing state directory:")
        self.test_state_directory()
        
        # Sound testing
        self.add_log("Testing sound module:")
        self.test_sound()
        
        # Test status bar
        self.add_log("Testing status bar:")
        self.update_status_bar()
        
        self.add_log("=" * 80)
        self.add_log("Self-test completed")
        self.add_log("=" * 80)

    def test_state_directory(self):
        """Test state directory functionality"""
        try:
            # Test creating state file for different tab types
            test_proc_id = 999
            test_range_start = 1
            test_range_end = 1000
            
            for tab_type in ["decimal", "hex64", "percent"]:
                self.add_log(f"  Testing StateManager for {tab_type} tab")
                StateManager.save_state(
                    test_proc_id, 
                    500, 
                    test_range_start, 
                    test_range_end,
                    tab_type,
                    {'test': True}
                )
                
                self.add_log(f"  Testing StateManager.load_state() for {tab_type} tab")
                current_key, loaded_start, loaded_end, metadata = StateManager.load_state(
                    test_proc_id, 
                    test_range_start, 
                    test_range_end,
                    tab_type
                )
                
                if current_key == 500:
                    self.add_log(f"  ✅ StateManager working correctly for {tab_type} tab")
                else:
                    self.add_log(f"  ❌ StateManager test failed for {tab_type} tab")
                    
                # Cleanup test file
                StateManager.cleanup_state_files(test_range_start, test_range_end, tab_type)
            
        except Exception as e:
            self.add_log(f"  State directory test error: {e}")

    def test_sound(self):
        """Test sound module"""
        try:
            self.add_log("  Checking sound file")
            if not os.path.exists(self.sound_player.sound_file):
                self.add_log(f"  Sound file not found: {self.sound_player.sound_file}")
                return
                
            self.add_log("  Sound file found")
            self.add_log("  Checking pygame initialization")
            
            if self.sound_player.pygame_available:
                self.add_log("  Pygame successfully initialized")
                self.add_log("  Attempting to play sound")
                sound_played = self.sound_player.play()
                if sound_played:
                    self.add_log("  Sound successfully played")
                else:
                    self.add_log("  Sound playback failed")
            else:
                self.add_log("  Pygame not available")
                self.add_log("  Pygame not installed")
                
        except Exception as e:
            self.add_log(f"  Sound testing error: {e}")

    def format_time(self, seconds):
        """Format time to readable form"""
        if seconds < 60:
            return f"{seconds:.1f} seconds"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds_remain = seconds % 60
            return f"{minutes:.0f} minutes {seconds_remain:.0f} seconds"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours:.0f} hours {minutes:.0f} minutes"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days:.0f} days {hours:.0f} hours"

    def calculate_search_time_years(self, total_keys, speed):
        """Calculate search time in years"""
        if speed <= 0:
            return f"∞ years"
        
        seconds = total_keys / speed
        years = seconds / (365 * 24 * 3600)
        
        if years > 1000:
            return f"∞ years"
        elif years >= 1:
            return f"{years:.1f} years"
        else:
            months = years * 12
            if months >= 1:
                return f"{months:.1f} months"
            else:
                days = years * 365
                if days >= 1:
                    return f"{days:.1f} days"
                else:
                    hours = days * 24
                    if hours >= 1:
                        return f"{hours:.1f} hours"
                    else:
                        minutes = hours * 60
                        return f"{minutes:.1f} minutes"

    def load_help_content(self):
        """Load help content"""
        default_help = """
            <h1>Bitcoin365 Office Suite - Help</h1>
            <h2> </h2>
            <h2>Contacts and support:</h2>
            <p>For program operation questions contact:</p>
            <ul>
                <li>Email: <a href="mailto:koare@hotmail.co.uk">koare@hotmail.co.uk</a></li>
                <li>Telegram: <a href="https://t.me/bitscan365">https://t.me/bitscan365</a></li>
                <li>GitHub: <a href="https://github.com">link</a></li>
            </ul>
            
            <h2>Developer support:</h2>
            <p>If the program is useful to you, you can support the developer:</p>
            <ul>
                <li>Bitcoin: bc1qq3grmv3mtpf4yp763dj7yv64z3kj0jl07vm357</li>
                <li>Ethereum: 0x1b31a9a4ef160E52Ea57cAc63A60214CC5CF511d</li>
                <li>BuyMeCoffe: <a href="https://buymeacoffee.com">link</a></li>
            </ul>
            
            <h2>Important:</h2>
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; color: #856404;">
                <strong>For educational purposes only!</strong><br>
                Use the program responsibly and in accordance with local laws.
            </div>
            """
        self.help_browser.setHtml(default_help)

    def update_table_headers(self):
        """Update process table headers"""
        self.process_table.setHorizontalHeaderLabels([
            "Process",
            "Keys",
            "Speed",
            "Found",
            "Memory Used",
            "Status",
            "Uptime",
            "Search Time"
        ])

    def update_results_headers(self):
        """Update results table headers"""
        self.results_table.setHorizontalHeaderLabels([
            "Time",
            "Process",
            "Private Key",
            "RIPEMD-160",
            "Type",
            "Legacy P2PKH UNCOMPRESSED",
            "Legacy P2PKH COMPRESSED", 
            "SegWit P2SH-P2WPKH UNCOMPRESSED",
            "SegWit P2SH-P2WPKH COMPRESSED",
            "Native SegWit Bech32"
        ])

    def setup_connections(self):
        self.ui_timer = QTimer()
        self.ui_timer.timeout.connect(self.update_ui_from_files)
        self.ui_timer.start(1000)

    def update_ui_from_files(self):
        """Update UI from results and statistics files"""
        if not self.process_manager.are_processes_running() and self.start_time:
            self.check_completion()
            return
            
        self.check_new_matches()
        self.check_process_completions()
        self.check_method_mismatch()
        self.update_stats_from_files()
        self.update_range_info_from_files()
        self.update_debug_info()
        self.update_ui()
        
        # Update status bar with current values
        self.update_status_bar()

    def check_method_mismatch(self):
        """Check generation method mismatch and immediately stop processes"""
        try:
            for file in os.listdir(RESULTS_DIR):
                if file.startswith('process_log_'):
                    file_path = os.path.join(RESULTS_DIR, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    log_info = json.loads(line)
                                    message = log_info.get('message', '')
                                    
                                    if "sequential generation" in message:
                                        process_method = 1
                                    elif "random generation" in message:
                                        process_method = 2
                                    else:
                                        continue
                                    
                                    if (self.expected_search_method is not None and 
                                        process_method != self.expected_search_method):
                                        
                                        self.add_log(f"CRITICAL ERROR: Generation method mismatch")
                                        self.add_log(f"Expected method: {'Sequential' if self.expected_search_method == 1 else 'Random'}")
                                        self.add_log(f"Actual method: {'Sequential' if process_method == 1 else 'Random'}")
                                        self.add_log("Immediately stopping processes")
                                        
                                        self.process_manager.stop_processes()
                                        self.sync_start_stop_buttons("stop")
                                        
                                        QMessageBox.critical(
                                            self, 
                                            "Critical Error", 
                                            f"Generation method mismatch detected!\n\n"
                                            f"Expected method: {'Sequential' if self.expected_search_method == 1 else 'Random'}\n"
                                            f"Actual method: {'Sequential' if process_method == 1 else 'Random'}\n\n"
                                            f"Processes stopped"
                                        )
                                        
                                        os.remove(file_path)
                                        return
                        
                        os.remove(file_path)
                    except json.JSONDecodeError:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error reading process log for method check: {e}")
                        
        except Exception as e:
            print(f"Error checking method mismatch: {e}")

    def check_process_completions(self):
        """Check process completion"""
        try:
            for file in os.listdir(RESULTS_DIR):
                if file.startswith('completion_'):
                    file_path = os.path.join(RESULTS_DIR, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            completion_info = json.load(f)
                            
                        process_id = completion_info['process_id']
                        total_attempts = completion_info['total_attempts']
                        targets_found = completion_info['targets_found']
                        duration = completion_info['duration']
                        tab_type = completion_info.get('tab_type', 'unknown')
                        
                        self.add_log(f"Process {process_id} completed work! (tab: {tab_type})")
                        self.add_log(f"   Keys checked: {total_attempts:,}")
                        self.add_log(f"   Matches found: {targets_found}")
                        self.add_log(f"   Work time: {self.format_time(duration)}")
                        self.add_log(f"   Search speed: {total_attempts/duration:,.0f} keys per second")
                        
                        os.remove(file_path)
                        
                    except json.JSONDecodeError:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error reading completion file: {e}")
                        
            for file in os.listdir(RESULTS_DIR):
                if file.startswith('process_log_'):
                    file_path = os.path.join(RESULTS_DIR, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    log_info = json.loads(line)
                                    self.add_log(f"Process {log_info['process_id']}: {log_info['message']}")
                        
                        os.remove(file_path)
                    except json.JSONDecodeError:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error reading process log: {e}")
                        
        except Exception as e:
            print(f"Error checking process completions: {e}")

    def update_range_info_from_files(self):
        """Update process range information from files with correct display"""
        try:
            for file in os.listdir(STATS_DIR):
                if file.startswith('range_'):
                    file_path = os.path.join(STATS_DIR, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            range_info = json.load(f)
                            
                            process_id = range_info['process_id']
                            range_start = range_info['range_start']
                            range_end = range_info['range_end']
                            current_key = range_info['current_key']
                            step_size = range_info['step_size']
                            actual_start = range_info.get('actual_start_position', range_start + process_id)
                            tab_type = range_info.get('tab_type', 'unknown')
                            
                            if process_id not in self.process_progress.get('range_logged', set()):
                                # Show real process start position
                                self.add_log(f"Process {process_id} started at: 0x{actual_start:064X} with step {step_size}, scanning range: 0x{range_start:064X} - 0x{range_end:064X} (tab: {tab_type})")
                                if 'range_logged' not in self.process_progress:
                                    self.process_progress['range_logged'] = set()
                                self.process_progress['range_logged'].add(process_id)
                                
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"Error reading range file {file}: {e}")
        except Exception as e:
            print(f"Error updating range info: {e}")

    def update_debug_info(self):
        """Update debug information - FIXED VERSION"""
        if not self.debug_mode:
            return
            
        try:
            debug_files_to_process = []
            
            # First collect all debug files
            for file in os.listdir(STATS_DIR):
                if file.startswith('debug_'):
                    debug_files_to_process.append(file)
            
            # Process each debug file
            for debug_file in debug_files_to_process:
                file_path = os.path.join(STATS_DIR, debug_file)
                try:
                    # Try to open with exclusive lock to avoid file access conflicts
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    
                    # If file is empty, skip
                    if not content:
                        try:
                            os.remove(file_path)
                        except:
                            pass
                        continue
                    
                    # Process each line
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            try:
                                debug_info = json.loads(line)
                                self.add_log(f"DEBUG Process {debug_info['process_id']}: Key {debug_info['key_int']}, Private key: {debug_info['private_key_hex']}")
                            except json.JSONDecodeError:
                                # Skip invalid JSON lines
                                continue
                    
                    # Delete the file after processing
                    try:
                        os.remove(file_path)
                    except PermissionError:
                        # File might still be in use, skip and try next time
                        continue
                    except Exception as e:
                        print(f"Error removing debug file {debug_file}: {e}")
                        
                except PermissionError:
                    # File is locked by another process, skip for now
                    continue
                except FileNotFoundError:
                    # File was already deleted, skip
                    continue
                except Exception as e:
                    print(f"Error reading debug file {debug_file}: {e}")
                    
        except Exception as e:
            print(f"Error checking debug info: {e}")

    def check_new_matches(self):
        """Check for new found matches"""
        try:
            for file in os.listdir(RESULTS_DIR):
                if file.startswith('matches_'):
                    file_path = os.path.join(RESULTS_DIR, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    match_info = json.loads(line)
                                    self.display_match(match_info)
                        
                        os.remove(file_path)
                    except json.JSONDecodeError:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error reading match file: {e}")
        except Exception as e:
            print(f"Error checking matches: {e}")

    def private_key_to_address(self, private_key_hex, address_type):
        """Convert private key to various address formats"""
        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            
            if address_type == "uncompressed":
                compressed = False
            else:
                compressed = True
                
            pub_key_obj = coincurve.PublicKey.from_valid_secret(private_key_bytes)
            pub_key = pub_key_obj.format(compressed=compressed)
            
            sha256_hash = hashlib.sha256(pub_key).digest()
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
            
            if address_type == "uncompressed":
                extended_hash = b'\x00' + ripemd160_hash
            else:
                extended_hash = b'\x00' + ripemd160_hash
                
            checksum = hashlib.sha256(hashlib.sha256(extended_hash).digest()).digest()[:4]
            
            from base58 import b58encode
            address_bytes = extended_hash + checksum
            address = b58encode(address_bytes).decode('ascii')
            
            return address
            
        except Exception as e:
            return f"Error: {str(e)}"

    def private_key_to_segwit_address(self, private_key_hex):
        """Convert private key to native segwit bech32 address"""
        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            pub_key_obj = coincurve.PublicKey.from_valid_secret(private_key_bytes)
            pub_key = pub_key_obj.format(compressed=True)  # Segwit uses compressed keys
            
            sha256_hash = hashlib.sha256(pub_key).digest()
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
            
            # For native segwit (bech32) - version 0 witness program
            witness_program = b'\x00\x14' + ripemd160_hash  # version 0 + 20-byte program
            
            # Use bech32 encoding
            from bech32 import bech32_encode, convertbits
            hrp = "bc"
            data = convertbits(witness_program[2:], 8, 5)  # Convert to 5-bit array
            address = bech32_encode(hrp, data)
            
            return address
            
        except Exception as e:
            return f"Error: {str(e)}"

    def private_key_to_p2sh_p2wpkh_address(self, private_key_hex, compressed=True):
        """Convert private key to P2SH-P2WPKH address"""
        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            pub_key_obj = coincurve.PublicKey.from_valid_secret(private_key_bytes)
            pub_key = pub_key_obj.format(compressed=compressed)
            
            sha256_hash = hashlib.sha256(pub_key).digest()
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
            
            # For P2SH-P2WPKH - version 0 witness program
            witness_program = b'\x00\x14' + ripemd160_hash
            
            # SHA256 of witness program
            witness_program_hash = hashlib.sha256(witness_program).digest()
            # RIPEMD160 of SHA256
            script_hash = hashlib.new('ripemd160', witness_program_hash).digest()
            
            # P2SH address format
            extended_hash = b'\x05' + script_hash
            checksum = hashlib.sha256(hashlib.sha256(extended_hash).digest()).digest()[:4]
            
            from base58 import b58encode
            address_bytes = extended_hash + checksum
            address = b58encode(address_bytes).decode('ascii')
            
            return address
            
        except Exception as e:
            return f"Error: {str(e)}"

    def display_match(self, match_info):
        """IMMEDIATELY display found match"""
        try:
            if self.expected_search_method == 2:
                ripemd160 = match_info['ripemd160']
                if ripemd160 in self.found_hashes:
                    self.add_log(f"Duplicate! Hash {ripemd160} already found. Ignoring.")
                    return
                else:
                    self.found_hashes.add(ripemd160)
            
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            timestamp = datetime.fromisoformat(match_info['timestamp']).strftime("%H:%M:%S")
            self.results_table.setItem(row, 0, QTableWidgetItem(timestamp))
            self.results_table.setItem(row, 1, QTableWidgetItem(str(match_info['process_id'])))
            
            private_key_item = QTableWidgetItem(match_info['private_key'])
            private_key_item.setToolTip(match_info['private_key'])
            self.results_table.setItem(row, 2, private_key_item)
            
            self.results_table.setItem(row, 3, QTableWidgetItem(match_info['ripemd160']))
            self.results_table.setItem(row, 4, QTableWidgetItem(match_info['address_type']))
            
            private_key_hex = match_info['private_key']
            
            # Generate all address formats
            addr_uncompressed = self.private_key_to_address(private_key_hex, "uncompressed")
            addr_compressed = self.private_key_to_address(private_key_hex, "compressed")
            addr_p2sh_p2wpkh_uncompressed = self.private_key_to_p2sh_p2wpkh_address(private_key_hex, compressed=False)
            addr_p2sh_p2wpkh_compressed = self.private_key_to_p2sh_p2wpkh_address(private_key_hex, compressed=True)
            addr_segwit = self.private_key_to_segwit_address(private_key_hex)
            
            # Set actual addresses in table instead of format names
            self.results_table.setItem(row, 5, QTableWidgetItem(addr_uncompressed))
            self.results_table.setItem(row, 6, QTableWidgetItem(addr_compressed))
            self.results_table.setItem(row, 7, QTableWidgetItem(addr_p2sh_p2wpkh_uncompressed))
            self.results_table.setItem(row, 8, QTableWidgetItem(addr_p2sh_p2wpkh_compressed))
            self.results_table.setItem(row, 9, QTableWidgetItem(addr_segwit))
            
            self.total_targets += 1
            
            self.add_log(f"Match found! Process: {match_info['process_id']}")
            self.add_log(f"  Private key: {match_info['private_key']}")
            self.add_log(f"  RIPEMD-160: {match_info['ripemd160']}")
            self.add_log(f"  Type: {match_info['address_type']}")
            self.add_log(f"  Legacy P2PKH UNCOMPRESSED: {addr_uncompressed}")
            self.add_log(f"  Legacy P2PKH COMPRESSED: {addr_compressed}")
            self.add_log(f"  P2SH-P2WPKH UNCOMPRESSED: {addr_p2sh_p2wpkh_uncompressed}")
            self.add_log(f"  P2SH-P2WPKH COMPRESSED: {addr_p2sh_p2wpkh_compressed}")
            self.add_log(f"  Native SegWit Bech32: {addr_segwit}")
            self.add_log(f"  Data saved to results table")
            
            self.add_log(f"  Attempting to play sound")
            sound_played = self.sound_player.play()
            if sound_played:
                self.add_log(f"  Sound successfully played")
            else:
                self.add_log(f"  Sound playback failed")
            
            match_dialog = MatchDialog(match_info, self)
            match_dialog.show()
            QApplication.processEvents()
            
        except Exception as e:
            self.add_log(f"Error displaying match: {e}")

    def update_stats_from_files(self):
        """Update statistics from files"""
        if not self.process_manager.are_processes_running():
            return
            
        try:
            total_attempts = 0
            total_speed = 0
            total_found = 0
            total_memory_usage = 0
            completed_processes = 0
            
            for file in os.listdir(STATS_DIR):
                if file.startswith('stats_'):
                    file_path = os.path.join(STATS_DIR, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            stats = json.load(f)
                            
                            process_id = stats['process_id']
                            if process_id < self.total_processes:
                                self.process_stats[process_id] = stats
                                
                                total_attempts += stats['attempts']
                                total_speed += stats['speed']
                                total_found += stats['targets_found']
                                total_memory_usage += stats.get('memory', 0)
                                
                                if stats.get('range_completed', False):
                                    completed_processes += 1
                                    if process_id not in self.process_progress.get('completed_logged', set()):
                                        tab_type = stats.get('tab_type', 'unknown')
                                        self.add_log(f"Process {process_id} completed work (tab: {tab_type})")
                                        if 'completed_logged' not in self.process_progress:
                                            self.process_progress['completed_logged'] = set()
                                        self.process_progress['completed_logged'].add(process_id)
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"Error reading stats file {file}: {e}")
            
            self.total_attempts = total_attempts
            self.total_targets = total_found
            self.completed_processes_count = completed_processes
        except Exception as e:
            print(f"Error updating stats: {e}")

    def check_completion(self):
        """Check completion of all processes"""
        if (self.completed_processes_count >= self.total_processes and 
            not self.completion_shown and 
            self.total_processes > 0):
            self.complete_search()

    def complete_search(self):
        """Complete search when range is fully scanned"""
        self.completion_shown = True
        self.status_ready.setText("Status: Completed")
        
        completion_message = f"Entire range scanned! Hashes found: {self.total_targets} (tab: {self.current_tab_type})"
        self.add_log(completion_message)
        
        QMessageBox.information(self, "Search Completed", 
                               f"Entire range scanned!\nHashes found: {self.total_targets}\nTab: {self.current_tab_type}")
        
        # 🔄 IMPORTANT: Reset all buttons to default state
        self.sync_start_stop_buttons("stop")
        self.sync_pause_resume_buttons("resume")
        
        # Reset search state
        self.start_time = None
        self.total_processes = 0
        self.completed_processes_count = 0
        self.is_paused = False

    def add_log(self, message: str):
        """Add message to log"""
        if self.log_text is None:
            print(f"LOG (not ready): {message}")
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_text.append(log_entry)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def load_hashes_from_file(self, filename: str = "5000000_hash.txt") -> Set[bytes]:
        filepath = os.path.join(TXT_DIR, filename)
        hashes = set()
        if not os.path.exists(filepath):
            self.add_log(f"File not found {filepath}!")
            return hashes
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    hex_hash = line.strip()
                    if hex_hash and len(hex_hash) == 40:
                        hash_bytes = bytes.fromhex(hex_hash)
                        hashes.add(hash_bytes)
            self.add_log(f"Successfully loaded {len(hashes):,} RIPEMD-160 hashes")
            return hashes
        except Exception as e:
            self.add_log(f"Error loading hashes: {e}")
            return set()

    def on_search_prepared(self, result):
        """Handle search preparation result"""
        if result[0] == 'error':
            QMessageBox.warning(self, "Error", str(result[1]))
            return
            
        configs = result[1]
        processes = len(configs)
        self.total_processes = processes
        self.completed_processes_count = 0
        
        self.process_stats = {}
        self.total_attempts = 0
        self.total_targets = 0
        self.start_time = time.time()
        self.is_paused = False
        self.process_start_times = {}
        self.process_progress = {}
        
        self.process_table.setRowCount(processes)
        self.update_table_headers()
        
        for i in range(processes):
            self.process_stats[i] = {
                'attempts': 0,
                'targets_found': 0,
                'speed': 0,
                'memory': 0,
                'active': True
            }
            
        self.add_log(f"Starting processes:")
        self.add_log(f"Number of processes: {processes}")
        self.add_log(f"Active tab: {self.current_tab_name} (type: {self.current_tab_type})")
        
        current_tab_index = self.right_panel.currentIndex()
        if current_tab_index == 1:
            current_tab_widget = self.right_panel.widget(1)
        elif current_tab_index == 2:
            current_tab_widget = self.right_panel.widget(2)
        elif current_tab_index == 3:
            current_tab_widget = self.right_panel.widget(3)
        else:
            current_tab_widget = self.right_panel.widget(1)
            
        if hasattr(current_tab_widget, 'method_widget'):
            method_text = current_tab_widget.method_widget.get_selected_method_text()
            type_text = current_tab_widget.type_widget.get_selected_type_text()
            mode_text = current_tab_widget.mode_widget.get_selected_mode_text()
        else:
            method_text = "Sequential generation"
            type_text = "Cryptographically secure"
            mode_text = "Continue scan"  # Now default
            
        params_text = f"""Launch parameters:
- Tab: {self.current_tab_name} (type: {self.current_tab_type})
- Generation method: {method_text}
- Generation type: {type_text}
- Scan mode: {mode_text}
- Number of processes: {processes}
- HEX range: 0x{self.range_start:064X} - 0x{self.range_end:064X}
- Decimal range: {self.range_start} - {self.range_end}
- Keys in range: {self.range_end - self.range_start + 1:,}
- Time limit: {'None' if self.time_spin.value() == 0 else f'{self.time_spin.value()} hours'}"""
        
        self.launch_params_text.setPlainText(params_text)
            
        self.add_log(f"Generation method: {method_text}")
        self.add_log(f"Generation type: {type_text}")
        self.add_log(f"Scan mode: {mode_text}")
        self.add_log(f"HEX range: 0x{self.range_start:064X} - 0x{self.range_end:064X}")
        self.add_log(f"Decimal range: {self.range_start} - {self.range_end}")
        self.add_log(f"Keys in range: {self.range_end - self.range_start + 1:,}")
        
        if self.time_spin.value() > 0:
            self.add_log(f"Time limit: {self.time_spin.value()} hours")
        else:
            self.add_log(f"Time limit: no limit")
            
        self.process_manager.start_processes(configs)
        
        self.sync_start_stop_buttons("start")
        
        self.status_ready.setText("Status: Searching")
        self.add_log("=" * 80)
        self.add_log(f"Search started!")
        self.add_log("=" * 80)

    def pause_search(self):
        """Pause search"""
        self.add_log(f"Pause button pressed")
        self.add_log(f"Pausing search")
        
        # 💾 STATE SAVING BEFORE PAUSE (for sequential generation)
        if self.expected_search_method == 1:  # Sequential mode
            self.add_log("💾 Saving state before pause...")
            self.save_sequential_state_before_pause()
        
        self.process_manager.stop_processes()
        self.is_paused = True
        
        self.sync_pause_resume_buttons("pause")
        
        self.status_ready.setText("Status: Paused")
        self.add_log(f"Search paused")

    def save_sequential_state_before_pause(self):
        """Save state for sequential generation before pause"""
        try:
            # Save state from process statistics files
            for i in range(self.total_processes):
                stats_file = os.path.join(STATS_DIR, f"stats_{i}.json")
                if os.path.exists(stats_file):
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        stats = json.load(f)
                    
                    current_position = stats.get('current_position')
                    if current_position is not None:
                        StateManager.save_state(
                            i,
                            current_position,
                            self.range_start,
                            self.range_end,
                            self.current_tab_type,  # Use current tab type
                            {
                                'attempts': stats.get('attempts', 0),
                                'targets_found': stats.get('targets_found', 0),
                                'pause_time': time.time(),
                                'reason': 'user_pause'
                            }
                        )
                        self.add_log(f"💾 Process {i} state saved before pause: {hex(current_position)} (tab: {self.current_tab_type})")
        except Exception as e:
            self.add_log(f"❌ Error saving state before pause: {e}")

    def resume_search(self):
        """Resume search"""
        self.add_log(f"Resume button pressed")
        self.add_log(f"Resuming search")
        
        # Use StartManager to prepare search
        if self.start_manager.last_range_tab:
            source = self.start_manager.last_range_tab.tab_name
            if source == "Decimal":
                self.start_manager.handle_start_request(StartButtonSource.DECIMAL_TAB)
            elif source == "hex64":
                self.start_manager.handle_start_request(StartButtonSource.HEX64_TAB)
            elif source == "%%":
                self.start_manager.handle_start_request(StartButtonSource.PERCENT_TAB)
            else:
                self.start_manager.handle_start_request(StartButtonSource.DECIMAL_TAB)
        else:
            self.start_manager.handle_start_request(StartButtonSource.DECIMAL_TAB)

    def stop_search(self):
        """Stop search"""
        self.add_log(f"Stop button pressed")
        self.add_log(f"Stopping search")
        
        # 💾 STATE SAVING BEFORE STOP (for sequential generation)
        if self.expected_search_method == 1:  # Sequential mode
            self.add_log("💾 Saving state before stop...")
            self.save_sequential_state_before_stop()
        
        self.process_manager.stop_processes()
        self.sync_start_stop_buttons("stop")
        self.sync_pause_resume_buttons("resume")
        
        self.status_ready.setText("Status: Stopped")
        self.add_log(f"Search stopped")

    def save_sequential_state_before_stop(self):
        """Save state for sequential generation before stop"""
        try:
            # Save state from process statistics files
            for i in range(self.total_processes):
                stats_file = os.path.join(STATS_DIR, f"stats_{i}.json")
                if os.path.exists(stats_file):
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        stats = json.load(f)
                    
                    current_position = stats.get('current_position')
                    if current_position is not None:
                        StateManager.save_state(
                            i,
                            current_position,
                            self.range_start,
                            self.range_end,
                            self.current_tab_type,  # Use current tab type
                            {
                                'attempts': stats.get('attempts', 0),
                                'targets_found': stats.get('targets_found', 0),
                                'stop_time': time.time(),
                                'reason': 'user_stop'
                            }
                        )
                        self.add_log(f"💾 Process {i} state saved before stop: {hex(current_position)} (tab: {self.current_tab_type})")
        except Exception as e:
            self.add_log(f"❌ Error saving state before stop: {e}")

    def toggle_debug_mode(self):
        """Toggle debug mode"""
        self.debug_mode = not self.debug_mode
        
        if self.debug_mode:
            # Update debug buttons in all range widgets
            for tab in [self.decimal_tab, self.hex64_tab, self.percent_tab]:
                if hasattr(tab.range_widget, 'debug_btn'):
                    tab.range_widget.debug_btn.setStyleSheet("QPushButton { background-color: #00ff00; color: #000000; }")
            self.add_log(f"Debug mode enabled")
            self.add_log(f"Debug logging enabled")
        else:
            for tab in [self.decimal_tab, self.hex64_tab, self.percent_tab]:
                if hasattr(tab.range_widget, 'debug_btn'):
                    tab.range_widget.debug_btn.setStyleSheet("")
            self.add_log(f"Debug mode disabled")
            
        if self.process_manager.are_processes_running():
            self.add_log(f"Process restart required to apply changes")

    def update_ui(self):
        """Update UI with correct process start positions"""
        if not self.process_manager.are_processes_running() and self.start_time:
            return
            
        total_attempts = 0
        total_speed = 0
        total_found = 0
        total_memory_usage = 0
        processes = self.process_spin.value()
        
        if self.process_table.rowCount() != processes:
            self.process_table.setRowCount(processes)
            self.update_table_headers()
            
        for i in range(processes):
            if i in self.process_stats:
                stats = self.process_stats[i]
                total_attempts += stats['attempts']
                total_speed += stats['speed']
                total_found += stats['targets_found']
                total_memory_usage += stats.get('memory', 0)
                
                self.last_speed = total_speed
                
                self.process_table.setItem(i, 0, QTableWidgetItem(f"Process {i}"))
                self.process_table.setItem(i, 1, QTableWidgetItem(f"{stats['attempts']:,}"))
                self.process_table.setItem(i, 2, QTableWidgetItem(f"{stats['speed']:,.0f}/s"))
                
                found_item = QTableWidgetItem(str(stats['targets_found']))
                if stats['targets_found'] > 0:
                    found_item.setBackground(QColor(255, 255, 0))
                    found_item.setForeground(QColor(0, 0, 255))
                    found_item.setFont(QFont("", -1, QFont.Bold))
                self.process_table.setItem(i, 3, found_item)
                
                memory_usage = stats.get('memory', 0)
                self.process_table.setItem(i, 4, QTableWidgetItem(f"{memory_usage:.1f} MB"))
                
                status_text = "Active" if stats.get('running', True) else "Completed"
                if self.is_paused:
                    status_text = "Paused"
                self.process_table.setItem(i, 5, QTableWidgetItem(status_text))
                
                if i in self.process_start_times:
                    elapsed = time.time() - self.process_start_times[i]
                    hours = int(elapsed // 3600)
                    minutes = int((elapsed % 3600) // 60)
                    seconds = int(elapsed % 60)
                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    self.process_start_times[i] = time.time()
                    time_str = "00:00:00"
                self.process_table.setItem(i, 6, QTableWidgetItem(time_str))
                
                if stats['speed'] > 0:
                    process_range = (self.range_end - self.range_start + 1) // processes
                    search_time = self.calculate_search_time_years(process_range, stats['speed'])
                else:
                    search_time = f"∞ years"
                self.process_table.setItem(i, 7, QTableWidgetItem(search_time))
                
                if i not in self.process_start_times:
                    self.process_start_times[i] = time.time()
                    self.process_progress[i] = 0
                    
                    # Show real process start position in logs
                    if self.expected_search_method == 1:  # Sequential mode
                        process_start = self.range_start + i
                        self.add_log(f"Process {i} sequential start: 0x{process_start:064X} with step {processes} (tab: {self.current_tab_type})")
                    else:
                        self.add_log(f"Process {i} random mode: scanning range 0x{self.range_start:064X} - 0x{self.range_end:064X} (tab: {self.current_tab_type})")
                    
        self.status_ready.setText("Status: Searching")
        self.status_memory.setText(f"Memory: {total_memory_usage:.1f} MB")
        self.status_speed.setText(f"Speed: {total_speed:,.0f} keys/sec")
        self.status_found.setText(f"Found: {total_found}")
        self.status_keys.setText(f"Keys: {total_attempts:,}")
        
        if self.start_time:
            elapsed = time.time() - self.start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.status_uptime.setText(f"Uptime: {time_str}")
            
        estimated_total_memory = total_memory_usage / 1024
        estimated_memory_percent = min(100, (estimated_total_memory / self.physical_memory_gb) * 100)
        self.memory_progress.setValue(int(estimated_memory_percent))
        
        memory_label_text = f"Total memory usage {estimated_total_memory:.2f} GB ({estimated_memory_percent:.1f}%)"
        self.memory_usage_label.setText(memory_label_text)
        
        if self.process_manager.are_processes_running():
            if self.is_paused:
                self.status_ready.setText("Status: Paused")
            else:
                self.status_ready.setText("Status: Searching")
        else:
            self.status_ready.setText("Status: Ready")
            
        # Update status bar with current values
        self.update_status_bar()

    def closeEvent(self, event):
        """Window close event handler"""
        self.add_log(f"Close event triggered")
        
        if self.process_manager.are_processes_running():
            reply = QMessageBox.question(self, "Exit Confirmation",
                                       "Search is still running. Are you sure you want to exit?",
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)
            if reply == QMessageBox.Yes:
                # 💾 STATE SAVING BEFORE EXIT (for sequential generation)
                if self.expected_search_method == 1:  # Sequential mode
                    self.add_log("💾 Saving state before exit...")
                    self.save_sequential_state_before_exit()
                
                self.stop_search()
                event.accept()
            else:
                event.ignore()
        else:
            # 💾 STATE SAVING BEFORE EXIT (for sequential generation)
            if self.expected_search_method == 1:  # Sequential mode
                self.add_log("💾 Saving state before exit...")
                self.save_sequential_state_before_exit()
            
            event.accept()

    def save_sequential_state_before_exit(self):
        """Save state for sequential generation before exit"""
        try:
            # Save state from process statistics files
            for i in range(self.total_processes):
                stats_file = os.path.join(STATS_DIR, f"stats_{i}.json")
                if os.path.exists(stats_file):
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        stats = json.load(f)
                    
                    current_position = stats.get('current_position')
                    if current_position is not None:
                        StateManager.save_state(
                            i,
                            current_position,
                            self.range_start,
                            self.range_end,
                            self.current_tab_type,  # Use current tab type
                            {
                                'attempts': stats.get('attempts', 0),
                                'targets_found': stats.get('targets_found', 0),
                                'exit_time': time.time(),
                                'reason': 'application_exit'
                            }
                        )
                        self.add_log(f"💾 Process {i} state saved before exit: {hex(current_position)} (tab: {self.current_tab_type})")
        except Exception as e:
            self.add_log(f"❌ Error saving state before exit: {e}")

    def emergency_exit(self):
        """Emergency exit function"""
        self.add_log("🚨 Emergency exit!")
        
        # 💾 STATE SAVING DURING EMERGENCY EXIT
        if self.expected_search_method == 1:  # Sequential mode
            self.add_log("💾 Emergency state saving...")
            self.save_sequential_state_emergency()
        
        self.process_manager.stop_processes()
        self.add_log("Emergency exit completed")
        sys.exit(1)

    def save_sequential_state_emergency(self):
        """Emergency state save for sequential generation"""
        try:
            # Try to save state as quickly as possible
            for i in range(self.total_processes):
                stats_file = os.path.join(STATS_DIR, f"stats_{i}.json")
                if os.path.exists(stats_file):
                    with open(stats_file, 'r', encoding='utf-8') as f:
                        stats = json.load(f)
                    
                    current_position = stats.get('current_position')
                    if current_position is not None:
                        StateManager.save_state(
                            i,
                            current_position,
                            self.range_start,
                            self.range_end,
                            self.current_tab_type,  # Use current tab type
                            {
                                'attempts': stats.get('attempts', 0),
                                'targets_found': stats.get('targets_found', 0),
                                'emergency_time': time.time(),
                                'reason': 'emergency_exit'
                            }
                        )
                        self.add_log(f"💾 Emergency save process {i}: {hex(current_position)} (tab: {self.current_tab_type})")
        except Exception as e:
            self.add_log(f"❌ Emergency save error: {e}")

def signal_handler(sig, frame):
    """Interrupt signal handler"""
    print("\nReceived interrupt signal. Shutting down...")
    
    # Attempt to save state during emergency shutdown
    try:
        if hasattr(QApplication, 'instance') and QApplication.instance():
            main_window = QApplication.instance().activeWindow()
            if isinstance(main_window, MainWindow):
                main_window.emergency_exit()
    except:
        pass
    
    QApplication.quit()

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)  # Add SIGTERM handler
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    
    # Add emergency exit to terminal button
    def emergency_exit_to_terminal():
        window.emergency_exit()
    
    # Connect "Exit to terminal" buttons with emergency exit
    for tab in [window.decimal_tab, window.hex64_tab, window.percent_tab]:
        if hasattr(tab.range_widget, 'terminal_btn'):
            tab.range_widget.terminal_btn.clicked.connect(emergency_exit_to_terminal)
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    try:
        import coincurve
        main()
    except ImportError as e:
        print(f"Error: {e}")
        print("Please install: pip install coincurve PyQt5 psutil")
        print("For sound support, also install: pip install pygame")
        print("For address generation, also install: pip install bech32 base58")
        sys.exit(1)