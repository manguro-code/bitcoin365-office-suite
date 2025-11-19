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

# Constantes
MAX_KEY = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140
MIN_KEY = 0x0000000000000000000000000000000000000000000000000000000000000001
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(SCRIPT_DIR, "json")
TXT_DIR = os.path.join(SCRIPT_DIR, "txt")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
STATS_DIR = os.path.join(SCRIPT_DIR, "stats")
THEMES_DIR = os.path.join(SCRIPT_DIR, "themes")
STATE_DIR = os.path.join(SCRIPT_DIR, "state")  # Nuevo directorio para archivos de estado

class MatrixBackground(QWidget):
    """Widget con animación matricial para el fondo DELANTERO"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # CONJUNTO EXTENDIDO DE CARACTERES - más números y símbolos
        self.matrix_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*()_+-=[]{}|;:,.<>?/~`"
        self.drops = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_matrix)
        self.timer.start(8)  # 20 FPS
        # REDUCIR TAMAÑO DE FUENTE para mayor densidad
        self.font_size = 8  # era 14
        
        # CRÍTICAMENTE IMPORTANTE: Eliminar transparencia para eventos de ratón, pero hacer fondo semi-transparente
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # Los eventos pasan a través
        self.setStyleSheet("background: transparent;")
        
        # Establecer alto orden Z para estar por encima de otros widgets
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.setup_drops()
        
    def setup_drops(self):
        """Inicializar caracteres que caen"""
        if self.width() > 0 and self.height() > 0:
            self.drops = []
            # AUMENTAR NÚMERO DE COLUMNAS 2-3 veces
            num_columns = max(1, self.width() // (self.font_size // 2))  # Reducir distancia entre columnas
            
            for i in range(num_columns):
                # Cada columna tiene su propia velocidad y posición
                self.drops.append({
                    'x': i * (self.font_size // 2),  # Reducir distancia entre columnas
                    'y': random.randint(-500, 0),
                    'speed': random.uniform(1, 20),   # Reducir ligeramente el rango de velocidades
                    'length': random.randint(40, 80), # AUMENTAR LONGITUD DE GOTA
                    'chars': []
                })
    
    def resizeEvent(self, event):
        """Manejador de evento de cambio de tamaño"""
        self.setup_drops()
        super().resizeEvent(event)
    
    def update_matrix(self):
        """Actualizar animación"""
        if self.isVisible():
            self.update()
    
    def paintEvent(self, event):
        """Dibujar efecto matricial"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        
        # Fondo negro semi-transparente para efecto de estela
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))  # Ligeramente aumentada la transparencia
        
        font = QFont("Courier New", self.font_size, QFont.Bold)
        painter.setFont(font)
        
        for drop in self.drops:
            # Actualizar posición
            drop['y'] += drop['speed']
            
            # Si la gota sale de los límites, reiniciarla
            if drop['y'] > self.height() + drop['length'] * self.font_size:
                drop['y'] = random.randint(-500, 0)
                drop['speed'] = random.uniform(3, 8)
                drop['length'] = random.randint(12, 35)
                drop['chars'] = []  # Reiniciar caracteres
            
            # Generar nuevos caracteres si es necesario
            if len(drop['chars']) != drop['length']:
                drop['chars'] = [random.choice(self.matrix_chars) for _ in range(drop['length'])]
            else:
                # AUMENTAR PROBABILIDAD DE CAMBIO DE CARACTERES para mayor dinamismo
                for i in range(len(drop['chars'])):
                    if random.random() < 0.18:  # Aumentado del 5% al 8%
                        drop['chars'][i] = random.choice(self.matrix_chars)
            
            # Dibujar caracteres de la gota
            for i, char in enumerate(drop['chars']):
                y_pos = drop['y'] - i * self.font_size
                
                if -self.font_size <= y_pos < self.height():
                    # Gradiente de color de verde brillante a verde oscuro
                    if i == 0:
                        color = QColor(0, 90, 0)  # Blanco para el primer carácter
                    elif i == 1:
                        color = QColor(0, 255, 0)      # Verde brillante
                    elif i == 2:
                        color = QColor(0, 220, 0)      # Verde
                    elif i < 6:
                        color = QColor(0, 180, 0)      # Verde medio
                    else:
                        intensity = max(60, 200 - (i * 100 // drop['length']))  # Gradiente más suave
                        color = QColor(0, intensity, 0)
                    
                    painter.setPen(color)
                    painter.drawText(int(drop['x']), int(y_pos), char)

class ThemeManager:
    """Gestor de temas para la aplicación"""
    
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
        """Obtener ruta al archivo de tema"""
        theme_file = cls.THEMES.get(theme_name, "light.qss")
        return os.path.join(THEMES_DIR, theme_file)
    
    @classmethod
    def load_theme(cls, theme_name):
        """Cargar tema desde archivo"""
        theme_path = cls.get_theme_path(theme_name)
        try:
            if os.path.exists(theme_path):
                with open(theme_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                print(f"Archivo de tema no encontrado: {theme_path}")
                return ""
        except Exception as e:
            print(f"Error cargando tema {theme_name}: {e}")
            return ""
    
    @classmethod
    def get_available_themes(cls):
        """Obtener lista de temas disponibles"""
        return list(cls.THEMES.keys())

# ==================== MECANISMO DE GUARDADO DE ESTADO ====================
class StateManager:
    """Gestor para guardar y cargar estados de procesos"""
    
    @staticmethod
    def get_state_filename(proc_id: int, range_start: int, range_end: int, tab_type: str = "decimal", program_name: str = "bitcoin365") -> str:
        """
        Generar nombre único de archivo de estado basado en parámetros y tipo de pestaña
        
        Args:
            proc_id: ID del proceso (0, 1, 2, ...)
            range_start: Inicio del rango
            range_end: Fin del rango
            tab_type: Tipo de pestaña ("decimal", "hex64", "percent")
            program_name: Nombre del programa para separar estados de diferentes scripts
        
        Returns:
            str: Ruta al archivo de estado
        """
        # Usar diferentes formatos dependiendo del tipo de pestaña
        if tab_type == "decimal":
            # Para pestaña decimal: usar números decimales
            range_id = f"start_{range_start}_end_{range_end}"
        elif tab_type == "hex64":
            # Para pestaña hex64: usar formato HEX
            range_id = f"start_{range_start:064x}_end_{range_end:064x}"
        elif tab_type == "percent":
            # Para pestaña porcentual: usar valores porcentuales
            range_id = f"start_{range_start}_end_{range_end}"
        else:
            # Por defecto: usar HEX
            range_id = f"start_{range_start:064x}_end_{range_end:064x}"
        
        # Formar nombre de archivo con tipo de pestaña
        filename = f"state_{program_name}_{tab_type}_process_{proc_id}_{range_id}.json"
        
        return os.path.join(STATE_DIR, filename)
    
    @staticmethod
    def save_state(proc_id: int, current_key: int, range_start: int, range_end: int, tab_type: str = "decimal", metadata: dict = None):
        """
        Guardar estado actual del proceso en archivo JSON
        
        Args:
            proc_id: ID del proceso
            current_key: Clave actual procesada
            range_start: Inicio del rango
            range_end: Fin del rango  
            tab_type: Tipo de pestaña ("decimal", "hex64", "percent")
            metadata: Metadatos adicionales para guardar
        """
        try:
            # Generar nombre de archivo con tipo de pestaña
            state_file = StateManager.get_state_filename(proc_id, range_start, range_end, tab_type)
            
            # Formar estructura de datos
            state_data = {
                # Parámetros principales del rango
                'process_id': proc_id,
                'current_key': current_key,
                'range_start': range_start,
                'range_end': range_end,
                'tab_type': tab_type,
                
                # Metadatos para verificación de compatibilidad
                'program_version': '1.0.0',
                'timestamp': datetime.now().isoformat(),
                'total_range_size': range_end - range_start + 1,
                'keys_processed': current_key - range_start,
                
                # Datos personalizados adicionales
                'metadata': metadata or {}
            }
            
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(state_file), exist_ok=True)
            
            # Guardar en JSON con formato bonito
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Estado del proceso {proc_id} guardado para pestaña {tab_type}: {hex(current_key)}")
            
        except Exception as e:
            print(f"❌ Error guardando estado del proceso {proc_id} para pestaña {tab_type}: {e}")
    
    @staticmethod
    def load_state(proc_id: int, range_start: int, range_end: int, tab_type: str = "decimal", program_name: str = "bitcoin365") -> Tuple[int, int, int, dict]:
        """
        Cargar estado del proceso con verificación de compatibilidad de parámetros
        
        Args:
            proc_id: ID del proceso a cargar
            range_start: Inicio esperado del rango
            range_end: Fin esperado del rango
            tab_type: Tipo de pestaña ("decimal", "hex64", "percent")
            program_name: Nombre del programa
        
        Returns:
            Tuple: (current_key, loaded_start, loaded_end, metadata)
            o (None, None, None, None) si la carga no es posible
        """
        try:
            state_file = StateManager.get_state_filename(proc_id, range_start, range_end, tab_type, program_name)
            
            if not os.path.exists(state_file):
                print(f"📭 Archivo de estado del proceso {proc_id} no encontrado para pestaña {tab_type}")
                return None, None, None, None
            
            # Leer archivo de estado
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # ⚠️ IMPORTANTE: Verificar compatibilidad de parámetros
            loaded_start = state_data['range_start']
            loaded_end = state_data['range_end']
            loaded_tab_type = state_data.get('tab_type', 'decimal')
            
            if loaded_start != range_start or loaded_end != range_end or loaded_tab_type != tab_type:
                print(f"🔀 Discrepancia de rango o tipo de pestaña para proceso {proc_id}")
                print(f"   Esperado: {range_start} - {range_end} (pestaña: {tab_type})")
                print(f"   En archivo: {loaded_start} - {loaded_end} (pestaña: {loaded_tab_type})")
                return None, None, None, None
                
            # Verificar integridad de datos
            current_key = state_data['current_key']
            
            if not (range_start <= current_key <= range_end):
                print(f"⚠️ Clave fuera de rango en proceso {proc_id}")
                return None, None, None, None
            
            metadata = state_data.get('metadata', {})
            
            print(f"✅ Estado del proceso {proc_id} cargado para pestaña {tab_type}")
            print(f"   Clave actual: {hex(current_key)}")
            print(f"   Progreso: {state_data.get('keys_processed', 0):,} claves")
            
            return current_key, loaded_start, loaded_end, metadata
            
        except Exception as e:
            print(f"❌ Error cargando estado del proceso {proc_id} para pestaña {tab_type}: {e}")
            return None, None, None, None
    
    @staticmethod
    def cleanup_state_files(range_start: int, range_end: int, tab_type: str = "decimal", program_name: str = "bitcoin365"):
        """
        Limpiar TODOS los archivos de estado para el rango y tipo de pestaña especificados
        
        Args:
            range_start: Inicio del rango para limpiar
            range_end: Fin del rango para limpiar  
            tab_type: Tipo de pestaña ("decimal", "hex64", "percent")
            program_name: Nombre del programa
        """
        try:
            if not os.path.exists(STATE_DIR):
                print("📭 Directorio de estados no existe")
                return
                
            removed_count = 0
            
            # Generar sufijo objetivo basado en tipo de pestaña
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
                    print(f"🗑️ Archivo de estado eliminado: {filename}")
            
            print(f"✅ Limpieza completada para pestaña {tab_type}. Archivos eliminados: {removed_count}")
            
        except Exception as e:
            print(f"❌ Error limpiando archivos de estado para pestaña {tab_type}: {e}")
    
    @staticmethod
    def list_state_files(tab_type: str = "all", program_name: str = "bitcoin365"):
        """
        Mostrar todos los archivos de estado para el programa y tipo de pestaña específico
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
                print(f"📋 ARCHIVOS DE ESTADO ({program_name}, pestaña: {tab_type}):")
                for file in sorted(state_files):
                    print(f"  📄 {file}")
            else:
                print(f"📭 Archivos de estado no encontrados para {program_name} (pestaña: {tab_type})")
                
            return state_files
            
        except Exception as e:
            print(f"❌ Error leyendo archivos de estado: {e}")
            return []

class WorkerProcess:
    """Clase para trabajar en proceso separado"""
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
        self.tab_type = config.get('tab_type', 'decimal')  # Guardar tipo de pestaña
        
        # Para modo secuencial - posición inicial del proceso
        if config['search_method'] == 1:  # Modo secuencial
            # Intentar cargar estado previo si está habilitada la continuación de búsqueda
            if config.get('continue_search', False):
                current_key, loaded_start, loaded_end, metadata = StateManager.load_state(
                    self.process_id, 
                    config['range_start'], 
                    config['range_end'],
                    self.tab_type  # Pasar tipo de pestaña
                )
                if current_key is not None:
                    # Continuar desde última clave + paso
                    self.current_key = current_key + config['processes']
                    print(f"🔄 Proceso {self.process_id}: CONTINUACIÓN desde clave {hex(current_key)} -> {hex(self.current_key)} (pestaña: {self.tab_type})")
                else:
                    # Comenzar desde posición única para el proceso
                    self.current_key = config['range_start'] + config['proc_id']
                    print(f"🆕 Proceso {self.process_id}: NUEVA BÚSQUEDA desde clave {hex(self.current_key)} (pestaña: {self.tab_type})")
            else:
                # Nueva búsqueda - comenzar desde posición única
                self.current_key = config['range_start'] + config['proc_id']
                print(f"🆕 Proceso {self.process_id}: NUEVA BÚSQUEDA desde clave {hex(self.current_key)} (pestaña: {self.tab_type})")
            
            self.step_size = config['processes']  # Paso igual al número de procesos
            
            # Escribir información sobre el rango del proceso
            self.log_range_info()

    def log_range_info(self):
        """Escribir información sobre el rango del proceso con posiciones iniciales únicas"""
        try:
            # Calcular posición inicial real para este proceso
            if self.config['search_method'] == 1:  # Modo secuencial
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
            print(f"Error escribiendo información de rango: {e}")

    def log_completion_info(self):
        """Escribir información sobre finalización del rango"""
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
                
            # También escribir en archivo general para lectura inmediata
            immediate_completion_file = os.path.join(RESULTS_DIR, f"completion_{self.process_id}.json")
            os.makedirs(os.path.dirname(immediate_completion_file), exist_ok=True)
            with open(immediate_completion_file, 'w', encoding='utf-8') as f:
                json.dump(completion_info, f, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error escribiendo información de finalización: {e}")

    def get_process_memory_usage(self):
        """Obtener uso de memoria del proceso actual en MB"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Convertir a MB
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
        """Generar clave secuencial con rango único para el proceso"""
        if self.current_key is None:
            # Inicializar posición inicial para el proceso
            self.current_key = self.config['range_start'] + self.config['proc_id']
            self.step_size = self.config['processes']
            self.log_range_info()
        
        # Verificar si se excedieron los límites del rango
        if self.current_key > self.config['range_end']:
            self.range_completed = True
            return None, None
        
        private_key = self.current_key.to_bytes(32, 'big').rjust(32, b'\x00')
        current_key = self.current_key
        
        # Ir a la siguiente clave con paso igual al número de procesos
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
        """Guardar inmediatamente coincidencia encontrada en archivo"""
        try:
            match_file = os.path.join(RESULTS_DIR, f"matches_{self.process_id}.json")
            os.makedirs(os.path.dirname(match_file), exist_ok=True)
            with open(match_file, 'a', encoding='utf-8') as f:
                json.dump(match_info, f, ensure_ascii=False)
                f.write('\n')
                f.flush()  # Forzar escritura a disco
            return True
        except Exception as e:
            print(f"Error guardando inmediatamente coincidencia: {e}")
            return False

    def save_match_to_txt(self, match_info):
        """Guardar coincidencia en archivo de texto con todos los formatos de direcciones"""
        try:
            txt_file = os.path.join(RESULTS_DIR, f"results_{self.process_id}.txt")
            os.makedirs(os.path.dirname(txt_file), exist_ok=True)
            
            # Generar todos los formatos de direcciones
            private_key_hex = match_info['private_key']
            legacy_uncompressed = self.private_key_to_address(private_key_hex, "uncompressed")
            legacy_compressed = self.private_key_to_address(private_key_hex, "compressed")
            segwit_address = self.private_key_to_segwit_address(private_key_hex)
            
            # Formato: key_hex64 \t ripemd160_hash \t legacy_uncompressed \t legacy_compressed \t segwit_address
            line = f"{private_key_hex}\t{match_info['ripemd160']}\t{legacy_uncompressed}\t{legacy_compressed}\t{segwit_address}\n"
            
            with open(txt_file, 'a', encoding='utf-8') as f:
                f.write(line)
                f.flush()
            return True
        except Exception as e:
            print(f"Error guardando coincidencia en txt: {e}")
            return False

    def private_key_to_address(self, private_key_hex, address_type):
        """Convertir clave privada a formato de dirección legacy"""
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
        """Convertir clave privada a dirección native segwit bech32"""
        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            pub_key_obj = coincurve.PublicKey.from_valid_secret(private_key_bytes)
            pub_key = pub_key_obj.format(compressed=True)  # Segwit usa claves comprimidas
            
            sha256_hash = hashlib.sha256(pub_key).digest()
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
            
            # Para native segwit (bech32) - programa de testigo versión 0
            witness_program = b'\x00\x14' + ripemd160_hash  # versión 0 + programa de 20 bytes
            
            # Usar codificación bech32
            from bech32 import bech32_encode, convertbits
            hrp = "bc"
            data = convertbits(witness_program[2:], 8, 5)  # Convertir a array de 5 bits
            address = bech32_encode(hrp, data)
            
            return address
            
        except Exception as e:
            return f"Error: {str(e)}"

    def save_stats(self):
        """Guardar estadísticas en archivo"""
        try:
            stats_file = os.path.join(STATS_DIR, f"stats_{self.process_id}.json")
            os.makedirs(os.path.dirname(stats_file), exist_ok=True)
            elapsed = time.time() - self.start_time
            speed = self.attempts / elapsed if elapsed > 0 else 0
            
            # Obtener uso real de memoria del proceso
            memory_usage = self.get_process_memory_usage()
            
            # Para modo secuencial añadir información sobre posición actual
            current_position = None
            if self.config['search_method'] == 1 and self.current_key is not None:
                current_position = self.current_key - self.step_size  # Clave actual procesada
            
            stats = {
                'process_id': self.process_id,
                'attempts': self.attempts,
                'targets_found': self.targets_found,
                'speed': speed,
                'memory': memory_usage,  # Uso real de memoria
                'running': self.running and not self.range_completed,
                'range_completed': self.range_completed,
                'current_position': current_position,
                'tab_type': self.tab_type,
                'timestamp': time.time()
            }
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False)
        except Exception as e:
            print(f"Error guardando estadísticas: {e}")

    def debug_log_key(self, key_int, private_key, ripemd160_uncompressed, ripemd160_compressed):
        """Escribir información de depuración sobre la clave"""
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
            print(f"Error en registro de depuración: {e}")

    def add_log(self, message):
        """Añadir mensaje al registro del proceso"""
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
            print(f"Error añadiendo registro del proceso: {e}")

    def run(self):
        """Bucle principal de trabajo del proceso con registro correcto"""
        try:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            
            # Escribir posición inicial correcta
            if self.config['search_method'] == 1:  # Modo secuencial
                start_position = self.current_key if self.current_key is not None else self.config['range_start'] + self.config['proc_id']
                self.add_log(f"Proceso {self.process_id} generación secuencial comienza desde: 0x{start_position:064X} con paso {self.step_size} (pestaña: {self.tab_type})")
            else:
                self.add_log(f"Proceso {self.process_id} generación aleatoria en rango: 0x{self.config['range_start']:064X} - 0x{self.config['range_end']:064X} (pestaña: {self.tab_type})")
            
            last_save_time = time.time()
            last_state_save_time = time.time()
            
            while self.running and (time.time() - self.start_time < self.config['max_time']) and not self.range_completed:
                try:
                    if self.config['search_method'] == 2:
                        # Generación aleatoria
                        key_int, private_key = self.generate_random_key_in_range(
                            self.config['range_start'],
                            self.config['range_end'],
                            self.config['use_secrets']
                        )
                    else:
                        # Generación secuencial
                        result = self.generate_sequential_key()
                        if result[0] is None:
                            # Rango completado para este proceso
                            self.range_completed = True
                            break
                        key_int, private_key = result
                    
                    ripemd160_uncompressed = self.private_key_to_ripemd160(private_key, compressed=False)
                    ripemd160_compressed = self.private_key_to_ripemd160(private_key, compressed=True)
                    
                    if ripemd160_uncompressed is None or ripemd160_compressed is None:
                        self.attempts += 1
                        self.batch_counter += 1
                        continue
                    # Registro de depuración
                    if self.debug_mode:
                        self.debug_log_key(key_int, private_key, ripemd160_uncompressed, ripemd160_compressed)
                    # PROCESAMIENTO INMEDIATO de coincidencias encontradas
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
                        # Guardar inmediatamente en ambos JSON y TXT
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
                        # Guardar inmediatamente en ambos JSON y TXT
                        self.save_match_immediately(match_info)
                        self.save_match_to_txt(match_info)
                        self.targets_found += 1
                        match_found = True
                    self.attempts += 1
                    self.batch_counter += 1
                    
                    # 💾 GUARDADO PERIÓDICO DE ESTADO para generación secuencial
                    current_time = time.time()
                    if (self.config['search_method'] == 1 and 
                        (self.batch_counter >= 50000 or (current_time - last_state_save_time) >= 300)):  # 5 minutos
                        
                        # Guardar estado del proceso con tipo de pestaña
                        StateManager.save_state(
                            self.process_id, 
                            self.current_key - self.step_size,  # Clave actual procesada
                            self.config['range_start'],
                            self.config['range_end'],
                            self.tab_type,  # Pasar tipo de pestaña
                            {
                                'attempts': self.attempts,
                                'targets_found': self.targets_found,
                                'batch_counter': self.batch_counter,
                                'start_time': self.start_time,
                                'step_size': self.step_size
                            }
                        )
                        
                        last_state_save_time = current_time
                        # NO reiniciar batch_counter aquí!
                    
                    # Guardado de estadísticas separado del estado
                    if self.batch_counter >= 10000:
                        self.save_stats()
                        # NO reiniciar batch_counter aquí!
                        self.batch_counter = 0
                        
                except Exception as e:
                    continue
            # Guardar estadísticas finales
            if self.range_completed:
                # Escribir información sobre finalización del rango
                self.log_completion_info()
                self.add_log(f"Proceso {self.process_id} completó trabajo. Claves verificadas: {self.attempts:,}, Coincidencias encontradas: {self.targets_found} (pestaña: {self.tab_type})")
            
            # 💾 GUARDADO FINAL DE ESTADO ANTES DE SALIR
            if self.config['search_method'] == 1 and self.current_key is not None:
                StateManager.save_state(
                    self.process_id, 
                    self.current_key - self.step_size,
                    self.config['range_start'],
                    self.config['range_end'],
                    self.tab_type,  # Pasar tipo de pestaña
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
            print(f"Error proceso {self.process_id}: {e}")

def worker_process(config):
    """Función envoltorio para ejecutar en proceso separado"""
    worker = WorkerProcess(config)
    worker.run()

class ProcessManager:
    """Gestor para manejar procesos independientes"""
    def __init__(self):
        self.processes = []
        self.running = False
        self.process_configs = {}

    def start_processes(self, configs):
        """Iniciar procesos con configuraciones dadas"""
        self.running = True
        self.process_configs = configs
        self.cleanup_old_files()
        
        for config in configs:
            p = Process(target=worker_process, args=(config,))
            p.daemon = True
            p.start()
            self.processes.append(p)

    def cleanup_old_files(self):
        """Limpiar archivos antiguos de resultados y estadísticas, pero NO archivos de estado"""
        try:
            # Limpiar solo archivos temporales, NO archivos de estado
            for file in os.listdir(RESULTS_DIR):
                if file.startswith('matches_') or file.startswith('process_log_') or file.startswith('completion_') or file.startswith('results_'):
                    os.remove(os.path.join(RESULTS_DIR, file))
            for file in os.listdir(STATS_DIR):
                if file.startswith('stats_') or file.startswith('range_') or file.startswith('debug_') or file.startswith('completion_'):
                    os.remove(os.path.join(STATS_DIR, file))
        except Exception as e:
            print(f"Error limpiando archivos antiguos: {e}")

    def stop_processes(self):
        """Detener todos los procesos"""
        self.running = False
        for p in self.processes:
            if p.is_alive():
                p.terminate()
        for p in self.processes:
            p.join(timeout=0.5)
        self.processes.clear()

    def are_processes_running(self):
        """Verificar si los procesos están ejecutándose"""
        return any(p.is_alive() for p in self.processes)

class SoundPlayer:
    """Reproductor de sonido multiplataforma"""
    def __init__(self):
        self.sound_file = os.path.join(SCRIPT_DIR, "alerta.wav")
        self.pygame_available = False
        self.init_pygame()

    def init_pygame(self):
        """Inicializar pygame si está disponible"""
        try:
            import pygame
            pygame.mixer.init()
            self.pygame_available = True
            print("Pygame inicializado exitosamente")
        except Exception as e:
            print(f"Falló inicialización de Pygame: {e}")
            self.pygame_available = False

    def play(self):
        """Reproducir sonido"""
        try:
            if not os.path.exists(self.sound_file):
                print(f"Archivo de sonido no encontrado: {self.sound_file}")
                return False
                
            if self.pygame_available:
                try:
                    import pygame
                    pygame.mixer.music.load(self.sound_file)
                    pygame.mixer.music.play()
                    print("Sonido reproducido exitosamente con pygame")
                    return True
                except Exception as e:
                    print(f"Error reproduciendo sonido con pygame: {e}")
                    return False
            else:
                print("Pygame no disponible para reproducir sonido")
                return False
        except Exception as e:
            print(f"Error en reproductor de sonido: {e}")
            return False

class MatchDialog(QDialog):
    """Ventana de diálogo para notificación de coincidencia"""
    def __init__(self, match_info, parent=None):
        super().__init__(parent)
        self.match_info = match_info
        self.init_ui()
        
        # Cierre automático después de 5 segundos
        QTimer.singleShot(5000, self.accept)

    def init_ui(self):
        self.setWindowTitle("¡Coincidencia encontrada!")
        self.setModal(False)
        self.resize(600, 300)
        
        layout = QVBoxLayout(self)
        
        title_label = QLabel("<h1>¡Coincidencia encontrada!</h1>")
        title_label.setStyleSheet("color: #FF0000; font-weight: bold;")
        layout.addWidget(title_label)
        
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details_text.setFont(QFont("Consolas", 9))
        
        details = f"""
Proceso: {self.match_info['process_id']}
Clave privada: {self.match_info['private_key']}
RIPEMD-160: {self.match_info['ripemd160']}
Tipo: {self.match_info['address_type']}
Tiempo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        details_text.setText(details)
        layout.addWidget(details_text)
        
        button_box = QDialogButtonBox()
        ok_button = button_box.addButton(QDialogButtonBox.Ok)
        ok_button.clicked.connect(self.accept)
        layout.addWidget(button_box)

class StartButtonSource:
    """Enumeración de fuentes del botón Iniciar"""
    STATUS_WIDGET = "status_widget"
    SETTINGS_TAB = "settings_tab"
    DECIMAL_TAB = "decimal_tab"
    HEX64_TAB = "hex64_tab"
    PERCENT_TAB = "percent_tab"

class StartManager:
    """Gestor centralizado para manejar todos los botones Iniciar"""
    def __init__(self, main_window):
        self.main_window = main_window
        self.last_range_tab = None  # Recordar última pestaña de rango
    
    def handle_start_request(self, source):
        """Manejar solicitud de inicio desde cualquier fuente"""
        try:
            self.main_window.add_log("=== Búsqueda iniciada ===")
            self.main_window.add_log(f"Fuente: {self._get_source_name(source)}")
            
            # Determinar rango y configuraciones dependiendo de la fuente
            range_start, range_end, settings, log_details, tab_type = self._determine_range_and_settings(source)
            
            # Escribir detalles
            self.main_window.add_log(log_details)
            self.main_window.add_log(f"Rango HEX: 0x{range_start:064X} - 0x{range_end:064X}")
            self.main_window.add_log(f"Tipo de pestaña: {tab_type}")
            
            total_keys = range_end - range_start + 1
            self.main_window.add_log(f"Claves en rango: {total_keys:,}")
            
            # Calcular tiempo aproximado de búsqueda
            if total_keys > 0:
                estimated_speed = self.main_window.last_speed if self.main_window.last_speed > 0 else 100000
                estimated_years = self.main_window.calculate_search_time_years(total_keys, estimated_speed)
                self.main_window.add_log(f"Tiempo estimado de búsqueda: {estimated_years}")
            
            self.main_window.add_log("==========================")
            
            # Aplicar rango y configuraciones
            self.main_window.range_start = range_start
            self.main_window.range_end = range_end
            self.main_window.expected_search_method = settings['search_method']
            self.main_window.current_tab_type = tab_type  # Guardar tipo actual de pestaña
            
            # Comenzar búsqueda
            self._start_search_with_settings(settings, tab_type)
            
        except Exception as e:
            self.main_window.add_log(f"Error: {e}")
            QMessageBox.critical(self.main_window, "Error", f"Error iniciando búsqueda: {str(e)}")
    
    def _get_source_name(self, source):
        """Obtener nombre legible de la fuente"""
        source_names = {
            StartButtonSource.STATUS_WIDGET: "Widget de estado",
            StartButtonSource.SETTINGS_TAB: "Pestaña de configuraciones", 
            StartButtonSource.DECIMAL_TAB: "Pestaña decimal",
            StartButtonSource.HEX64_TAB: "Pestaña hex64",
            StartButtonSource.PERCENT_TAB: "Pestaña porcentual"
        }
        return source_names.get(source, "Fuente desconocida")
    
    def _determine_range_and_settings(self, source):
        """Determinar rango y configuraciones dependiendo de la fuente"""
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
            # Opción de respaldo - Decimal
            return self._get_from_decimal_tab()
    
    def _get_from_active_tab(self):
        """Obtener configuraciones desde pestaña activa"""
        current_index = self.main_window.right_panel.currentIndex()
        
        if current_index == 1:  # Decimal
            return self._get_from_decimal_tab()
        elif current_index == 2:  # Hex64
            return self._get_from_hex64_tab()
        elif current_index == 3:  # Porcentual
            return self._get_from_percent_tab()
        else:
            # Si la pestaña activa no tiene rango, usar última o Decimal
            if self.last_range_tab:
                return self._get_from_tab(self.last_range_tab)
            else:
                return self._get_from_decimal_tab()
    
    def _get_from_settings_tab(self):
        """Obtener configuraciones para pestaña Configuraciones"""
        # Usar última pestaña de rango activa
        if self.last_range_tab:
            range_start, range_end, settings, log_details, tab_type = self._get_from_tab(self.last_range_tab)
            log_details = f"Usando última pestaña: {self.last_range_tab.tab_name}\n" + log_details
            return range_start, range_end, settings, log_details, tab_type
        else:
            # Opción de respaldo - Decimal
            self.main_window.add_log(f"Sin historial de pestañas, usando Decimal por defecto")
            return self._get_from_decimal_tab()
    
    def _get_from_decimal_tab(self):
        """Obtener configuraciones desde pestaña Decimal"""
        tab = self.main_window.decimal_tab
        self.last_range_tab = tab
        return self._get_from_tab(tab)
    
    def _get_from_hex64_tab(self):
        """Obtener configuraciones desde pestaña Hex64"""
        tab = self.main_window.hex64_tab
        self.last_range_tab = tab
        return self._get_from_tab(tab)
    
    def _get_from_percent_tab(self):
        """Obtener configuraciones desde pestaña Porcentual"""
        tab = self.main_window.percent_tab
        self.last_range_tab = tab
        return self._get_from_tab(tab)
    
    def _get_from_tab(self, tab):
        """Obtener configuraciones desde pestaña específica"""
        range_start, range_end = tab.calculate_range()
        
        # Obtener configuraciones desde widgets de la pestaña
        search_method = tab.method_widget.get_selected_method()
        gen_method = tab.type_widget.get_selected_type()
        
        # Obtener modo de escaneo (continuar o nuevo)
        scan_mode = tab.mode_widget.get_selected_mode()
        continue_search = (scan_mode == 1)  # 1 = Continuar escaneo (ahora por defecto)
        
        # Determinar tipo de pestaña
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
        
        log_details = f"Configuraciones: {method_text}, {type_text}, {mode_text}"
        
        return range_start, range_end, settings, log_details, tab_type
    
    def _start_search_with_settings(self, settings, tab_type):
        """Comenzar búsqueda con configuraciones dadas"""
        try:
            # Preparar búsqueda
            result = self._prepare_search(settings, tab_type)
            if result[0] == 'success':
                self.main_window.on_search_prepared(result)
            else:
                self.main_window.add_log(f"Error preparando búsqueda: {result[1]}")
                QMessageBox.warning(self.main_window, "Error", str(result[1]))
                
        except Exception as e:
            self.main_window.add_log(f"Error iniciando búsqueda: {e}")
            QMessageBox.critical(self.main_window, "Error", f"Error iniciando búsqueda: {str(e)}")
    
    def _prepare_search(self, settings, tab_type):
        """Preparar búsqueda con configuraciones dadas"""
        try:
            processes = self.main_window.process_spin.value()
            max_time = self.main_window.time_spin.value() * 3600 if self.main_window.time_spin.value() > 0 else float('inf')
            target_hashes = self.main_window.load_hashes_from_file()
            
            if not target_hashes:
                return ('error', "Hashes objetivo no encontrados")
            # CORRECCIÓN CRÍTICA: Limitación automática de procesos para modo secuencial
            if settings['search_method'] == 1:  # Modo secuencial
                total_keys = self.main_window.range_end - self.main_window.range_start + 1
                actual_processes = min(processes, total_keys)
                
                if actual_processes < processes:
                    self.main_window.add_log(f"Reducción automática de procesos: {processes} -> {actual_processes}")
                    self.main_window.add_log(f"Limitación modo secuencial: no puede haber más procesos que claves")
                    processes = actual_processes
                    
                # Limpiar estado si se selecciona modo "Nuevo escaneo"
                if not settings['continue_search']:
                    self.main_window.add_log(f"🧹 Limpiando estados anteriores para nueva búsqueda (pestaña: {tab_type})")
                    StateManager.cleanup_state_files(self.main_window.range_start, self.main_window.range_end, tab_type)
                else:
                    # Mostrar estados existentes
                    existing_states = StateManager.list_state_files(tab_type)
                    if existing_states:
                        self.main_window.add_log(f"📁 Encontrados estados anteriores para pestaña {tab_type}. Continuando...")
                    else:
                        self.main_window.add_log(f"🆕 Estados anteriores no encontrados para pestaña {tab_type}. Comenzando desde inicio.")
            
            configs = []
            for i in range(processes):
                config = {
                    'proc_id': i,
                    'search_method': settings['search_method'],
                    'range_start': self.main_window.range_start,
                    'range_end': self.main_window.range_end,
                    'use_secrets': settings['use_secrets'],
                    'processes': processes,  # Importante: pasar número real de procesos
                    'max_time': max_time,
                    'target_hashes': target_hashes,
                    'continue_search': settings.get('continue_search', False),
                    'debug_mode': self.main_window.debug_mode,
                    'tab_type': tab_type  # Pasar tipo de pestaña al trabajador
                }
                configs.append(config)
                
            return ('success', configs)
        except Exception as e:
            return ('error', str(e))

class GenerationMethodWidget(QWidget):
    """Widget de selección de método de generación"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.group = QGroupBox("1. Seleccione método de generación:")
        group_layout = QVBoxLayout(self.group)
        
        self.method_combo = QComboBox()
        self.method_combo.addItem("Generación secuencial", 1)
        self.method_combo.addItem("Generación aleatoria", 2)
        
        group_layout.addWidget(self.method_combo)
        layout.addWidget(self.group)
        
    def get_selected_method(self):
        """Obtener método seleccionado"""
        return self.method_combo.currentData()
    
    def get_selected_method_text(self):
        """Obtener texto del método seleccionado"""
        return self.method_combo.currentText()

class GenerationTypeWidget(QWidget):
    """Widget de selección de tipo de generación"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.group = QGroupBox("2. Método de generación:")
        group_layout = QVBoxLayout(self.group)
        
        self.type_combo = QComboBox()
        self.type_combo.addItem("Criptográficamente seguro", 1)
        self.type_combo.addItem("Aleatorio estándar", 2)
        
        group_layout.addWidget(self.type_combo)
        layout.addWidget(self.group)
        
    def get_selected_type(self):
        """Obtener tipo seleccionado"""
        return self.type_combo.currentData()
    
    def get_selected_type_text(self):
        """Obtener texto del tipo seleccionado"""
        return self.type_combo.currentText()

class ScanModeWidget(QWidget):
    """Widget de selección de modo de escaneo"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.group = QGroupBox("3. ¿Modo de escaneo?")
        group_layout = QVBoxLayout(self.group)
        
        self.mode_combo = QComboBox()
        # Orden cambiado: Continuar escaneo ahora es primero/por defecto
        self.mode_combo.addItem("Continuar escaneo", 1)
        self.mode_combo.addItem("Nuevo escaneo", 2)
        
        group_layout.addWidget(self.mode_combo)
        layout.addWidget(self.group)
        
    def get_selected_mode(self):
        """Obtener modo seleccionado"""
        return self.mode_combo.currentData()
    
    def get_selected_mode_text(self):
        """Obtener texto del modo seleccionado"""
        return self.mode_combo.currentText()

class StartStopButton(QPushButton):
    """Botón universal Iniciar/Detener para todas las pestañas"""
    def __init__(self, parent=None, source=None):
        super().__init__("Iniciar", parent)
        self.main_window = parent
        self.source = source
        self.setFixedSize(100, 40)
        self.clicked.connect(self.toggle_state)
        
    def toggle_state(self):
        """Cambiar estado del botón"""
        if self.text() == "Iniciar":
            self.set_stop_state()
            if self.main_window and self.main_window.start_manager:
                self.main_window.start_manager.handle_start_request(self.source)
        else:
            self.set_start_state()
            if self.main_window:
                self.main_window.stop_search()
                
    def set_start_state(self):
        """Establecer estado Iniciar"""
        self.setText("Iniciar")
        
    def set_stop_state(self):
        """Establecer estado Detener"""
        self.setText("Detener")

class PauseResumeButton(QPushButton):
    """Botón universal Pausar/Continuar para todas las pestañas"""
    def __init__(self, parent=None):
        super().__init__("Pausar", parent)
        self.main_window = parent
        self.setFixedSize(120, 40)
        self.clicked.connect(self.toggle_state)
        
    def toggle_state(self):
        """Cambiar estado del botón"""
        if self.text() == "Pausar":
            self.set_resume_state()
            if self.main_window:
                self.main_window.pause_search()
        else:
            self.set_pause_state()
            if self.main_window:
                self.main_window.resume_search()
                
    def set_pause_state(self):
        """Establecer estado Pausar"""
        self.setText("Pausar")
        
    def set_resume_state(self):
        """Establecer estado Continuar"""
        self.setText("Continuar")

class RangeWidget(QWidget):
    """Clase base para widget de configuración de rango"""
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
        
        # Valor inicial
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("desde"))
        self.start_edit = QLineEdit()
        self.start_edit.setMinimumHeight(35)
        start_layout.addWidget(self.start_edit)
        range_layout.addLayout(start_layout)
        
        # Valor final
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("hasta"))
        self.end_edit = QLineEdit()
        self.end_edit.setMinimumHeight(35)
        end_layout.addWidget(self.end_edit)
        range_layout.addLayout(end_layout)
        
        # Botones de aplicación y control
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Aplicar rango")
        self.apply_btn.setFixedSize(200, 40)
        
        self.start_stop_btn = StartStopButton(self.main_window, self._get_source())
        self.pause_resume_btn = PauseResumeButton(self.main_window)
        
        self.reset_btn = QPushButton("Restablecer")
        self.reset_btn.setFixedSize(150, 40)
        
        self.terminal_btn = QPushButton("Salir a terminal")
        self.terminal_btn.setFixedSize(170, 40)
        
        self.debug_btn = QPushButton("Depuración")
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
        """Obtener fuente para botón Iniciar (se sobrescribe en clases hijas)"""
        return StartButtonSource.SETTINGS_TAB
        
    def apply_range(self):
        """Método abstracto - debe ser sobrescrito en clases hijas"""
        pass
        
    def get_range_values(self):
        """Obtener valores del rango"""
        return self.start_edit.text(), self.end_edit.text()
        
    def set_range_values(self, start, end):
        """Establecer valores del rango"""
        self.start_edit.setText(start)
        self.end_edit.setText(end)
        
    def setup_connections(self):
        """Configurar conexiones (se sobrescribe en clases hijas)"""
        self.apply_btn.clicked.connect(self.apply_range)
        self.reset_btn.clicked.connect(self.reset_settings)
        self.terminal_btn.clicked.connect(self.exit_to_terminal)
        self.debug_btn.clicked.connect(self.toggle_debug)
        
    def reset_settings(self):
        """Restablecer configuraciones (se sobrescribe en clases hijas)"""
        pass
        
    def exit_to_terminal(self):
        """Salir a terminal"""
        if self.main_window:
            self.main_window.close()
            
    def toggle_debug(self):
        """Cambiar modo de depuración"""
        if self.main_window:
            self.main_window.toggle_debug_mode()

class PercentRangeWidget(RangeWidget):
    """Widget de rango porcentual"""
    def __init__(self, parent=None):
        super().__init__("Configuraciones de rango porcentual", parent)
        self.start_edit.setPlaceholderText("1")
        self.end_edit.setPlaceholderText("1000000")
        self.start_edit.setText("1")
        self.end_edit.setText("1000000")
        self.setup_connections()
        
    def _get_source(self):
        return StartButtonSource.PERCENT_TAB
        
    def apply_range(self):
        """Aplicar rango porcentual"""
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
                self.main_window.add_log(f"Pestaña porcentual: Rango aplicado {start_num}% hasta {end_num}%")
                # Actualización diferida de información de rango
                QTimer.singleShot(100, lambda: self.main_window.update_percent_range_info(start_num, end_num))
            
        except ValueError:
            self.reset_range()
            
    def reset_range(self):
        """Restablecer rango a valores por defecto"""
        self.start_edit.setText("1")
        self.end_edit.setText("1000000")
        if self.main_window:
            self.main_window.add_log(f"Pestaña porcentual: Rango restablecido")
            
    def reset_settings(self):
        """Restablecer configuraciones"""
        self.reset_range()
        if self.main_window:
            self.main_window.add_log(f"Pestaña porcentual: Configuraciones restablecidas")

class Hex64RangeWidget(RangeWidget):
    """Widget de rango HEX64"""
    def __init__(self, parent=None):
        super().__init__("Configuraciones de rango HEX64", parent)
        self.start_edit.setPlaceholderText("0x0000000000000000000000000000000000000000000000000000000000000001")
        self.end_edit.setPlaceholderText("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.start_edit.setText("0x0000000000000000000000000000000000000000000000000000000000000001")
        self.end_edit.setText("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.setup_connections()
        
    def _get_source(self):
        return StartButtonSource.HEX64_TAB
        
    def apply_range(self):
        """Aplicar rango HEX64"""
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
                self.main_window.add_log(f"Pestaña Hex64: Rango aplicado 0x{start_int:064X} hasta 0x{end_int:064X}")
                # Actualización diferida de información de rango
                QTimer.singleShot(100, lambda: self.main_window.update_hex64_range_info(start_int, end_int))
            
        except ValueError:
            self.reset_range()
            
    def reset_range(self):
        """Restablecer rango a valores por defecto"""
        self.start_edit.setText("0x0000000000000000000000000000000000000000000000000000000000000001")
        self.end_edit.setText("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        if self.main_window:
            self.main_window.add_log(f"Pestaña Hex64: Rango restablecido")
            
    def reset_settings(self):
        """Restablecer configuraciones"""
        self.reset_range()
        if self.main_window:
            self.main_window.add_log(f"Pestaña Hex64: Configuraciones restablecidas")

class DecimalRangeWidget(RangeWidget):
    """Widget de rango en formato decimal"""
    def __init__(self, parent=None):
        super().__init__("Configuraciones de rango decimal", parent)
        self.start_edit.setPlaceholderText("1")
        self.end_edit.setPlaceholderText("115792089237316195423570985008687907852837564279074904382605163141518161494336")
        self.start_edit.setText("1")
        self.end_edit.setText("115792089237316195423570985008687907852837564279074904382605163141518161494336")
        self.setup_connections()
        
    def _get_source(self):
        return StartButtonSource.DECIMAL_TAB
        
    def apply_range(self):
        """Aplicar rango en formato decimal"""
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
                self.main_window.add_log(f"Pestaña decimal: Rango aplicado {start_int} hasta {end_int}")
                # Actualización diferida de información de rango
                QTimer.singleShot(100, lambda: self.main_window.update_decimal_range_info(start_int, end_int))
            
        except ValueError:
            self.reset_range()
            
    def reset_range(self):
        """Restablecer rango a valores por defecto"""
        self.start_edit.setText("1")
        self.end_edit.setText("115792089237316195423570985008687907852837564279074904382605163141518161494336")
        if self.main_window:
            self.main_window.add_log(f"Pestaña decimal: Rango restablecido")
            
    def reset_settings(self):
        """Restablecer configuraciones"""
        self.reset_range()
        if self.main_window:
            self.main_window.add_log(f"Pestaña decimal: Configuraciones restablecidas")

class ScrollableTab(QScrollArea):
    """Área desplazable para pestañas"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.content_widget = QWidget()
        self.setWidget(self.content_widget)
        
    def set_layout(self, layout):
        """Establecer layout para contenido"""
        self.content_widget.setLayout(layout)

class PercentTab(ScrollableTab):
    """Pestaña para trabajar con rangos porcentuales"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.tab_name = "%%"
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Sección de método de generación
        self.method_widget = GenerationMethodWidget(self)
        self.type_widget = GenerationTypeWidget(self)
        self.mode_widget = ScanModeWidget(self)
        
        layout.addWidget(self.method_widget)
        layout.addWidget(self.type_widget)
        layout.addWidget(self.mode_widget)
        
        # Configuraciones de rango porcentual
        self.range_widget = PercentRangeWidget(self.main_window)
        layout.addWidget(self.range_widget)
        
        # Información sobre el rango
        self.info_group = QGroupBox("Información del rango")
        info_layout = QVBoxLayout(self.info_group)
        
        # Cantidad de claves
        keys_layout = QHBoxLayout()
        keys_layout.addWidget(QLabel("Claves en rango:"))
        self.keys_label = QLabel("0")
        self.keys_label.setMinimumHeight(30)
        keys_layout.addWidget(self.keys_label)
        keys_layout.addStretch()
        info_layout.addLayout(keys_layout)
        
        # Rango final
        final_range_layout = QVBoxLayout()
        final_range_layout.addWidget(QLabel("Rango HEX final:"))
        self.final_range_label = QLabel("0x0000000000000000000000000000000000000000000000000000000000000001 - 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.final_range_label.setWordWrap(True)
        self.final_range_label.setMinimumHeight(50)
        final_range_layout.addWidget(self.final_range_label)
        info_layout.addLayout(final_range_layout)
        
        layout.addWidget(self.info_group)
        
        layout.addStretch()
        
        self.set_layout(layout)
        
        # Conectar señales
        self.setup_connections()
        # Inicialización diferida de información de rango
        QTimer.singleShot(100, self.apply_range)
        
    def setup_connections(self):
        """Configurar conexiones"""
        # Conectar señales para menús desplegables
        self.method_widget.method_combo.currentIndexChanged.connect(self.on_method_changed)
        self.type_widget.type_combo.currentIndexChanged.connect(self.on_type_changed)
        self.mode_widget.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        
    def on_method_changed(self, index):
        """Manejador de cambio de método de generación"""
        method_text = self.method_widget.get_selected_method_text()
        self.main_window.add_log(f"Pestaña porcentual: Método seleccionado '{method_text}'")
        
    def on_type_changed(self, index):
        """Manejador de cambio de tipo de generación"""
        type_text = self.type_widget.get_selected_type_text()
        self.main_window.add_log(f"Pestaña porcentual: Tipo seleccionado '{type_text}'")
        
    def on_mode_changed(self, index):
        """Manejador de cambio de modo de escaneo"""
        mode_text = self.mode_widget.get_selected_mode_text()
        self.main_window.add_log(f"Pestaña porcentual: Modo seleccionado '{mode_text}'")
        
    def apply_range(self):
        """Aplicar rango"""
        self.range_widget.apply_range()
            
    def calculate_range(self):
        """Calcular rango basado en valores porcentuales"""
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
        """Actualizar información del rango"""
        total_keys = end_key - start_key + 1
        
        self.keys_label.setText(f"{total_keys:,}")
        self.final_range_label.setText(f"0x{start_key:064X} - 0x{end_key:064X}")

class Hex64Tab(ScrollableTab):
    """Pestaña para trabajar con rangos HEX64"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.tab_name = "hex64"
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Sección de método de generación
        self.method_widget = GenerationMethodWidget(self)
        self.type_widget = GenerationTypeWidget(self)
        self.mode_widget = ScanModeWidget(self)
        
        layout.addWidget(self.method_widget)
        layout.addWidget(self.type_widget)
        layout.addWidget(self.mode_widget)
        
        # Configuraciones de rango HEX64
        self.range_widget = Hex64RangeWidget(self.main_window)
        layout.addWidget(self.range_widget)
        
        # Información sobre el rango
        self.info_group = QGroupBox("Información del rango")
        info_layout = QVBoxLayout(self.info_group)
        
        # Cantidad de claves
        keys_layout = QHBoxLayout()
        keys_layout.addWidget(QLabel("Claves en rango:"))
        self.keys_label = QLabel("0")
        self.keys_label.setMinimumHeight(30)
        keys_layout.addWidget(self.keys_label)
        keys_layout.addStretch()
        info_layout.addLayout(keys_layout)
        
        # Rango final
        final_range_layout = QVBoxLayout()
        final_range_layout.addWidget(QLabel("Rango HEX final:"))
        self.final_range_label = QLabel("0x0000000000000000000000000000000000000000000000000000000000000001 - 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.final_range_label.setWordWrap(True)
        self.final_range_label.setMinimumHeight(50)
        final_range_layout.addWidget(self.final_range_label)
        info_layout.addLayout(final_range_layout)
        
        layout.addWidget(self.info_group)
        
        layout.addStretch()
        
        self.set_layout(layout)
        
        # Conectar señales
        self.setup_connections()
        # Inicialización diferida de información de rango
        QTimer.singleShot(100, self.apply_range)
        
    def setup_connections(self):
        """Configurar conexiones"""
        # Conectar señales para menús desplegables
        self.method_widget.method_combo.currentIndexChanged.connect(self.on_method_changed)
        self.type_widget.type_combo.currentIndexChanged.connect(self.on_type_changed)
        self.mode_widget.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        
    def on_method_changed(self, index):
        """Manejador de cambio de método de generación"""
        method_text = self.method_widget.get_selected_method_text()
        self.main_window.add_log(f"Pestaña Hex64: Método seleccionado '{method_text}'")
        
    def on_type_changed(self, index):
        """Manejador de cambio de tipo de generación"""
        type_text = self.type_widget.get_selected_type_text()
        self.main_window.add_log(f"Pestaña Hex64: Tipo seleccionado '{type_text}'")
        
    def on_mode_changed(self, index):
        """Manejador de cambio de modo de escaneo"""
        mode_text = self.mode_widget.get_selected_mode_text()
        self.main_window.add_log(f"Pestaña Hex64: Modo seleccionado '{mode_text}'")
            
    def apply_range(self):
        """Aplicar rango"""
        self.range_widget.apply_range()
            
    def calculate_range(self):
        """Calcular rango basado en valores HEX"""
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
        """Actualizar información del rango"""
        total_keys = end_key - start_key + 1
        
        self.keys_label.setText(f"{total_keys:,}")
        self.final_range_label.setText(f"0x{start_key:064X} - 0x{end_key:064X}")

class DecimalTab(ScrollableTab):
    """Pestaña para trabajar con rangos decimales"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.tab_name = "Decimal"
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Sección de método de generación
        self.method_widget = GenerationMethodWidget(self)
        self.type_widget = GenerationTypeWidget(self)
        self.mode_widget = ScanModeWidget(self)
        
        layout.addWidget(self.method_widget)
        layout.addWidget(self.type_widget)
        layout.addWidget(self.mode_widget)
        
        # Configuraciones de rango en formato decimal
        self.range_widget = DecimalRangeWidget(self.main_window)
        layout.addWidget(self.range_widget)
        
        # Información sobre el rango
        self.info_group = QGroupBox("Información del rango")
        info_layout = QVBoxLayout(self.info_group)
        
        # Cantidad de claves
        keys_layout = QHBoxLayout()
        keys_layout.addWidget(QLabel("Claves en rango:"))
        self.keys_label = QLabel("0")
        self.keys_label.setMinimumHeight(30)
        keys_layout.addWidget(self.keys_label)
        keys_layout.addStretch()
        info_layout.addLayout(keys_layout)
        
        # Rango final
        final_range_layout = QVBoxLayout()
        final_range_layout.addWidget(QLabel("Rango HEX final:"))
        self.final_range_label = QLabel("0x0000000000000000000000000000000000000000000000000000000000000001 - 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.final_range_label.setWordWrap(True)
        self.final_range_label.setMinimumHeight(50)
        final_range_layout.addWidget(self.final_range_label)
        info_layout.addLayout(final_range_layout)
        
        layout.addWidget(self.info_group)
        
        layout.addStretch()
        
        self.set_layout(layout)
        
        # Conectar señales
        self.setup_connections()
        # Inicialización diferida de información de rango
        QTimer.singleShot(100, self.apply_range)
        
    def setup_connections(self):
        """Configurar conexiones"""
        # Conectar señales para menús desplegables
        self.method_widget.method_combo.currentIndexChanged.connect(self.on_method_changed)
        self.type_widget.type_combo.currentIndexChanged.connect(self.on_type_changed)
        self.mode_widget.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        
    def on_method_changed(self, index):
        """Manejador de cambio de método de generación"""
        method_text = self.method_widget.get_selected_method_text()
        self.main_window.add_log(f"Pestaña decimal: Método seleccionado '{method_text}'")
        
    def on_type_changed(self, index):
        """Manejador de cambio de tipo de generación"""
        type_text = self.type_widget.get_selected_type_text()
        self.main_window.add_log(f"Pestaña decimal: Tipo seleccionado '{type_text}'")
        
    def on_mode_changed(self, index):
        """Manejador de cambio de modo de escaneo"""
        mode_text = self.mode_widget.get_selected_mode_text()
        self.main_window.add_log(f"Pestaña decimal: Modo seleccionado '{mode_text}'")
            
    def apply_range(self):
        """Aplicar rango"""
        self.range_widget.apply_range()
            
    def calculate_range(self):
        """Calcular rango basado en valores decimales"""
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
        """Actualizar información del rango"""
        total_keys = end_key - start_key + 1
        
        self.keys_label.setText(f"{total_keys:,}")
        self.final_range_label.setText(f"0x{start_key:064X} - 0x{end_key:064X}")

class ThemeComboBox(QComboBox):
    """Lista desplegable para selección de tema"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()
        
    def init_ui(self):
        """Inicializar UI"""
        available_themes = ThemeManager.get_available_themes()
        for theme in available_themes:
            self.addItem(theme.replace('_', ' ').title(), theme)
        
        # Establecer tema por defecto
        default_theme = "light"
        index = self.findData(default_theme)
        if index >= 0:
            self.setCurrentIndex(index)
        
        self.currentIndexChanged.connect(self.on_theme_changed)
    
    def on_theme_changed(self, index):
        """Manejador de cambio de tema"""
        theme_name = self.currentData()
        if self.main_window:
            self.main_window.apply_theme(theme_name)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.process_manager = ProcessManager()
        self.sound_player = SoundPlayer()
        self.start_manager = StartManager(self)  # Gestor centralizado de inicio
        self.theme_manager = ThemeManager()
        self.state_manager = StateManager()  # Gestor de estado para generación secuencial
        
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
        self.current_tab_name = "Configuraciones"
        self.current_tab_type = "decimal"  # Rastrear tipo actual de pestaña
        self.debug_mode = False
        self.expected_search_method = None
        self.found_hashes = set()
        self.completion_shown = False
        
        # Fondo matricial
        self.matrix_background = None
        
        # Referencias a todos los botones de pestañas para sincronización
        self.start_stop_buttons = []
        self.pause_resume_buttons = []
        
        # Referencias a pestañas
        self.percent_tab = None
        self.hex64_tab = None  
        self.decimal_tab = None
        
        # CREAR DIRECTORIOS AL INICIAR
        self.create_directories_on_start()
        
        self.log_text = None
        self.debug_btn = None
        self.init_ui()
        self.setup_connections()
        
        # Limpiar tablas al iniciar
        self.clear_statistics_table()
        
        # Establecer pestaña Configuraciones como activa por defecto
        self.right_panel.setCurrentIndex(0)
        
        # Aplicar tema por defecto
        self.apply_theme("light")
        
        # Ejecutar autocomprobación al iniciar
        QTimer.singleShot(1000, self.run_self_test)

    def create_directories_on_start(self):
        """Crear todos los directorios necesarios al iniciar"""
        directories = [JSON_DIR, TXT_DIR, RESULTS_DIR, STATS_DIR, THEMES_DIR, STATE_DIR]
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"✅ Directorio creado/verificado: {directory}")
            except Exception as e:
                print(f"❌ Error creando directorio {directory}: {e}")

    def get_physical_memory(self):
        """Obtener memoria física en GB"""
        try:
            return psutil.virtual_memory().total / (1024 ** 3)
        except:
            return 16.0

    def cleanup_old_files_on_start(self):
        """Limpiar archivos antiguos de estadísticas al iniciar aplicación, pero NO archivos de estado"""
        try:
            for file in os.listdir(STATS_DIR):
                if file.startswith('stats_') or file.startswith('range_') or file.startswith('debug_') or file.startswith('completion_'):
                    os.remove(os.path.join(STATS_DIR, file))
            for file in os.listdir(RESULTS_DIR):
                if file.startswith('matches_') or file.startswith('completion_') or file.startswith('process_log_') or file.startswith('results_'):
                    os.remove(os.path.join(RESULTS_DIR, file))
        except Exception as e:
            print(f"Error limpiando archivos antiguos al iniciar: {e}")

    def init_ui(self):
        self.setWindowTitle("Bitcoin365 Office Suite")
        self.setGeometry(100, 100, 1100, 740)
        self.setMinimumSize(1100, 740)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.right_panel = QTabWidget()
        
        # Pestaña Configuraciones
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(10)
        
        # WIDGET DE ESTADO
        self.status_group = QGroupBox("Estado")
        status_layout = QVBoxLayout(self.status_group)
        
        # Fila superior de estado
        status_top_layout = QHBoxLayout()
        
        self.status_ready = QLabel("Estado: Listo")
        self.status_memory = QLabel("Memoria: 0 MB")
        self.status_uptime = QLabel("Tiempo activo: 00:00:00")
        self.status_speed = QLabel("Velocidad: 0 claves/seg")
        self.status_found = QLabel("Encontrados: 0")
        self.status_keys = QLabel("Claves: 0")
        
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
        
        # Añadir botones de control a fila de estado
        self.start_stop_btn = StartStopButton(self, StartButtonSource.STATUS_WIDGET)
        self.pause_resume_btn = PauseResumeButton(self)
        
        # Guardar referencias para sincronización
        self.start_stop_buttons.append(self.start_stop_btn)
        self.pause_resume_buttons.append(self.pause_resume_btn)
        
        status_top_layout.addWidget(self.start_stop_btn)
        status_top_layout.addWidget(self.pause_resume_btn)
        status_top_layout.addStretch()
        
        status_layout.addLayout(status_top_layout)
        
        # Información de uso de memoria
        memory_info_layout = QHBoxLayout()
        self.memory_usage_label = QLabel("Uso total de memoria 0 GB, 0%")
        memory_info_layout.addWidget(self.memory_usage_label)
        status_layout.addLayout(memory_info_layout)
        
        # Barra de progreso de memoria
        memory_progress_layout = QHBoxLayout()
        self.memory_progress = QProgressBar()
        self.memory_progress.setMaximum(100)
        memory_progress_layout.addWidget(self.memory_progress)
        status_layout.addLayout(memory_progress_layout)
        
        settings_layout.addWidget(self.status_group)
        
        # Configuración de procesos
        self.process_group = QGroupBox("Configuración de procesos")
        process_layout = QVBoxLayout(self.process_group)
        
        # Fila superior - configuraciones principales
        process_top_layout = QHBoxLayout()
        
        self.processes_label = QLabel("Número de procesos:")
        process_top_layout.addWidget(self.processes_label)
        self.process_spin = QSpinBox()
        self.process_spin.setRange(1, self.max_processes)
        self.process_spin.setValue(min(self.max_processes, 12))
        process_top_layout.addWidget(self.process_spin)
        
        self.time_label = QLabel("Límite de tiempo:")
        process_top_layout.addWidget(self.time_label)
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(0, 1000)
        self.time_spin.setValue(0)
        self.time_spin.setSuffix(" horas (0 = sin límite)")
        self.time_spin.setMinimumWidth(260)
        process_top_layout.addWidget(self.time_spin)
        
        # Selección de tema movida a misma fila
        self.theme_label = QLabel("Tema de color:")
        process_top_layout.addWidget(self.theme_label)
        self.theme_combo = ThemeComboBox(self)
        process_top_layout.addWidget(self.theme_combo)
        
        process_top_layout.addStretch()
        
        process_layout.addLayout(process_top_layout)
        
        settings_layout.addWidget(self.process_group)
        
        # Tabla de procesos
        self.process_table_group = QGroupBox("Tabla de procesos")
        self.process_table_group.setMinimumHeight(400)
        process_table_layout = QVBoxLayout(self.process_table_group)
        
        self.process_table = QTableWidget()
        self.process_table.setColumnCount(8)
        self.process_table.verticalHeader().setDefaultSectionSize(25)
        self.process_table.setAlternatingRowColors(True)
        process_table_layout.addWidget(self.process_table)
        
        settings_layout.addWidget(self.process_table_group)
        settings_layout.addStretch(1)
        
        # Crear pestañas con áreas desplazables
        self.percent_tab = PercentTab(self)
        self.hex64_tab = Hex64Tab(self)
        self.decimal_tab = DecimalTab(self)
        
        # Guardar referencias a botones de todas las pestañas
        # Los botones ahora están en widgets de rango
        for tab in [self.percent_tab, self.hex64_tab, self.decimal_tab]:
            if hasattr(tab.range_widget, 'start_stop_btn'):
                self.start_stop_buttons.append(tab.range_widget.start_stop_btn)
            if hasattr(tab.range_widget, 'pause_resume_btn'):
                self.pause_resume_buttons.append(tab.range_widget.pause_resume_btn)
        
        # Pestaña de resultados
        results_tab = QWidget()
        results_layout = QVBoxLayout(results_tab)
        
        # Añadir botón de guardar resultados arriba
        self.save_results_btn = QPushButton("Guardar resultados")
        self.save_results_btn.clicked.connect(self.save_results_to_file)
        results_layout.addWidget(self.save_results_btn)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(10)
        self.results_table.setRowCount(0)
        self.update_results_headers()
        results_layout.addWidget(self.results_table)
        
        # Pestaña de registro
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        
        # Widget "Parámetros de inicio"
        self.launch_params_group = QGroupBox("Parámetros de inicio")
        self.launch_params_group.setMaximumHeight(201)
        launch_params_layout = QVBoxLayout(self.launch_params_group)
        
        self.launch_params_text = QTextEdit()
        self.launch_params_text.setReadOnly(True)
        self.launch_params_text.setMaximumHeight(200)
        self.launch_params_text.setFont(QFont("Consolas", 8))
        self.launch_params_text.setPlainText("Los parámetros de inicio se mostrarán aquí")
        
        launch_params_layout.addWidget(self.launch_params_text)
        
        log_layout.addWidget(self.launch_params_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        # Pestaña de ayuda
        help_tab = QWidget()
        help_layout = QVBoxLayout(help_tab)
        
        self.help_browser = QTextBrowser()
        self.help_browser.setOpenExternalLinks(True)
        help_layout.addWidget(self.help_browser)
        
        self.load_help_content()
        
        # Añadir pestañas
        self.right_panel.addTab(settings_tab, "Configuraciones")
        self.right_panel.addTab(self.decimal_tab, "Decimal")
        self.right_panel.addTab(self.hex64_tab, "hex64")
        self.right_panel.addTab(self.percent_tab, "%%")
        self.right_panel.addTab(results_tab, "Resultados")
        self.right_panel.addTab(log_tab, "Registro")
        self.right_panel.addTab(help_tab, "Ayuda")
        
        main_layout.addWidget(self.right_panel)
        
        # Crear barra de estado con información extendida
        self.status_bar = self.statusBar()
        self.status_label = QLabel()
        self.status_bar.addWidget(self.status_label)
        
        # Inicializar barra de estado con valores por defecto
        self.update_status_bar()
        
        # Conectar señal de cambio de pestaña
        self.right_panel.currentChanged.connect(self.on_tab_changed)
        
        # Asegurar que widget central esté correctamente configurado para transparencia
        central_widget.setAutoFillBackground(False)
        central_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        central_widget.setAttribute(Qt.WA_StyledBackground, True)

    def update_status_bar(self):
        """Actualizar barra de estado con estadísticas actuales"""
        try:
            # Obtener valores actuales desde widgets de estado
            memory_text = self.status_memory.text().replace("Memoria: ", "")
            speed_text = self.status_speed.text().replace("Velocidad: ", "")
            keys_text = self.status_keys.text().replace("Claves: ", "")
            uptime_text = self.status_uptime.text().replace("Tiempo activo: ", "")
            found_text = self.status_found.text().replace("Encontrados: ", "")
            
            # Formatear texto de barra de estado
            status_text = f"Memoria: {memory_text} | Velocidad: {speed_text} | Total claves: {keys_text} | Tiempo activo: {uptime_text} | Encontrados: {found_text} | Directorio script: {SCRIPT_DIR}"
            
            self.status_label.setText(status_text)
            
        except Exception as e:
            print(f"Error actualizando barra de estado: {e}")
            # Opción de respaldo - información básica
            self.status_label.setText(f"Directorio script: {SCRIPT_DIR}")

    def apply_theme(self, theme_name):
        """Aplicar tema seleccionado"""
        try:
            # Eliminar fondo matricial si existía
            if self.matrix_background:
                self.matrix_background.setParent(None)
                self.matrix_background.deleteLater()
                self.matrix_background = None
            
            stylesheet = self.theme_manager.load_theme(theme_name)
            if stylesheet:
                self.setStyleSheet(stylesheet)
                self.current_theme = theme_name
                
                # Para tema matricial añadir fondo animado EN PRIMER PLANO
                if theme_name == "matrix":
                    QTimer.singleShot(100, self.apply_matrix_background)  # Inicio diferido
                
                self.add_log(f"Tema aplicado: {theme_name}")
            else:
                self.add_log(f"No se pudo cargar tema: {theme_name}")
        except Exception as e:
            self.add_log(f"Error aplicando tema {theme_name}: {e}")
    
    def apply_matrix_background(self):
        """Añadir fondo matricial para tema matricial EN PRIMER PLANO"""
        try:
            # Eliminar fondo antiguo si existía
            if self.matrix_background:
                self.matrix_background.setParent(None)
                self.matrix_background.deleteLater()
                self.matrix_background = None
            
            # Crear nuevo fondo
            self.matrix_background = MatrixBackground(self.centralWidget())
            
            # CRÍTICAMENTE IMPORTANTE: Establecer geometría y ELEVAR A PRIMER PLANO
            self.matrix_background.setGeometry(self.centralWidget().rect())
            
            # IMPORTANTE: Elevar a primer plano, ¡no bajar!
            self.matrix_background.raise_()  # Ahora estará por encima de todos los widgets
            
            # Asegurar que fondo no intercepte eventos de ratón
            self.matrix_background.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            
            # Mostrar widget
            self.matrix_background.show()
            
            self.add_log("Fondo matricial activado EN PRIMER PLANO")
            
        except Exception as e:
            self.add_log(f"Error creando fondo matricial: {e}")
    
    def resizeEvent(self, event):
        """Manejador de evento de cambio de tamaño de ventana"""
        super().resizeEvent(event)
        if self.matrix_background:
            # Actualizar geometría del fondo al cambiar tamaño de ventana
            self.matrix_background.setGeometry(self.centralWidget().rect())
            # RE-ELEVAR a primer plano después de cambiar tamaño
            self.matrix_background.raise_()

    def update_percent_range_info(self, start_percent, end_percent):
        """Actualizar información de rango para pestaña porcentual"""
        if hasattr(self, 'percent_tab') and self.percent_tab:
            start_key, end_key = self.calculate_percent_range(start_percent, end_percent)
            self.percent_tab.update_range_info(start_key, end_key)
            
    def update_hex64_range_info(self, start_key, end_key):
        """Actualizar información de rango para pestaña hex64"""
        if hasattr(self, 'hex64_tab') and self.hex64_tab:
            self.hex64_tab.update_range_info(start_key, end_key)
            
    def update_decimal_range_info(self, start_key, end_key):
        """Actualizar información de rango para pestaña decimal"""
        if hasattr(self, 'decimal_tab') and self.decimal_tab:
            self.decimal_tab.update_range_info(start_key, end_key)
            
    def calculate_percent_range(self, start_percent, end_percent):
        """Calcular rango basado en valores porcentuales"""
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
        """Sincronizar estado de todos los botones Iniciar/Detener"""
        for button in self.start_stop_buttons:
            if state == "start":
                button.set_stop_state()
            else:
                button.set_start_state()
                
    def sync_pause_resume_buttons(self, state):
        """Sincronizar estado de todos los botones Pausar/Continuar"""
        for button in self.pause_resume_buttons:
            if state == "pause":
                button.set_resume_state()
            else:
                button.set_pause_state()

    def save_results_to_file(self):
        """Guardar resultados en archivo TSV"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "Guardar resultados", 
                os.path.join(RESULTS_DIR, "results.tsv"), 
                "TSV Files (*.tsv);;All Files (*)"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # Escribir encabezados
                    headers = []
                    for col in range(self.results_table.columnCount()):
                        headers.append(self.results_table.horizontalHeaderItem(col).text())
                    f.write("\t".join(headers) + "\n")
                    
                    # Escribir datos
                    for row in range(self.results_table.rowCount()):
                        row_data = []
                        for col in range(self.results_table.columnCount()):
                            item = self.results_table.item(row, col)
                            if item is not None:
                                row_data.append(item.text())
                            else:
                                row_data.append("")
                        f.write("\t".join(row_data) + "\n")
                
                self.add_log(f"Resultados guardados: {file_path}")
                QMessageBox.information(self, "Éxito", f"Resultados guardados exitosamente:\n{file_path}")
                
        except Exception as e:
            self.add_log(f"Error guardando resultados: {e}")
            QMessageBox.critical(self, "Error", f"Error guardando resultados:\n{str(e)}")

    def on_tab_changed(self, index):
        """Manejador de cambio de pestaña"""
        tab_names = {
            0: "Configuraciones",
            1: "Decimal", 
            2: "hex64",
            3: "%",
            4: "Resultados",
            5: "Registro",
            6: "Ayuda"
        }
        
        tab_name = tab_names.get(index, f"Pestaña {index}")
        self.current_tab_name = tab_name
        
        # Actualizar tipo actual de pestaña
        if tab_name == "Decimal":
            self.current_tab_type = "decimal"
        elif tab_name == "hex64":
            self.current_tab_type = "hex64"
        elif tab_name == "%":
            self.current_tab_type = "percent"
        else:
            self.current_tab_type = "decimal"
            
        self.add_log(f"Pestaña seleccionada: '{tab_name}' (tipo: {self.current_tab_type})")

    def clear_statistics_table(self):
        """Limpiar tabla de estadísticas y llenar con ceros"""
        processes = self.process_spin.value()
        self.process_table.setRowCount(processes)
        self.update_table_headers()
        
        # Llenar tabla con ceros
        for i in range(processes):
            self.process_table.setItem(i, 0, QTableWidgetItem(f"Proceso {i}"))
            self.process_table.setItem(i, 1, QTableWidgetItem("0"))
            self.process_table.setItem(i, 2, QTableWidgetItem("0/seg"))
            self.process_table.setItem(i, 3, QTableWidgetItem("0"))
            self.process_table.setItem(i, 4, QTableWidgetItem("0 MB"))
            self.process_table.setItem(i, 5, QTableWidgetItem("Listo"))
            self.process_table.setItem(i, 6, QTableWidgetItem("00:00:00"))
            self.process_table.setItem(i, 7, QTableWidgetItem("∞ años"))
        
        # Restablecer estado
        self.status_ready.setText("Estado: Listo")
        self.status_memory.setText("Memoria: 0 MB")
        self.status_uptime.setText("Tiempo activo: 00:00:00")
        self.status_speed.setText("Velocidad: 0 claves/seg")
        self.status_found.setText("Encontrados: 0")
        self.status_keys.setText("Claves: 0")
        self.memory_usage_label.setText("Uso total de memoria 0 GB, 0%")
        self.memory_progress.setValue(0)
        
        # Actualizar barra de estado
        self.update_status_bar()

    def run_self_test(self):
        """Ejecutar autocomprobación"""
        self.add_log("=" * 80)
        self.add_log("Ejecutando autocomprobación")
        self.add_log("=" * 80)
        
        # Verificar limpieza de tabla de estadísticas
        self.add_log("Verificando limpieza de tabla de estadísticas:")
        self.clear_statistics_table()
        
        # Test de directorio de estados
        self.add_log("Test de directorio de estados:")
        self.test_state_directory()
        
        # Test de sonido
        self.add_log("Test de módulo de sonido:")
        self.test_sound()
        
        # Test de barra de estado
        self.add_log("Test de barra de estado:")
        self.update_status_bar()
        
        self.add_log("=" * 80)
        self.add_log("Autocomprobación completada")
        self.add_log("=" * 80)

    def test_state_directory(self):
        """Test de funcionalidad de directorio de estados"""
        try:
            # Test de creación de archivo de estado para diferentes tipos de pestañas
            test_proc_id = 999
            test_range_start = 1
            test_range_end = 1000
            
            for tab_type in ["decimal", "hex64", "percent"]:
                self.add_log(f"  Test StateManager para pestaña {tab_type}")
                StateManager.save_state(
                    test_proc_id, 
                    500, 
                    test_range_start, 
                    test_range_end,
                    tab_type,
                    {'test': True}
                )
                
                self.add_log(f"  Test StateManager.load_state() para pestaña {tab_type}")
                current_key, loaded_start, loaded_end, metadata = StateManager.load_state(
                    test_proc_id, 
                    test_range_start, 
                    test_range_end,
                    tab_type
                )
                
                if current_key == 500:
                    self.add_log(f"  ✅ StateManager funciona correctamente para pestaña {tab_type}")
                else:
                    self.add_log(f"  ❌ Test StateManager no pasado para pestaña {tab_type}")
                    
                # Limpieza de archivo de test
                StateManager.cleanup_state_files(test_range_start, test_range_end, tab_type)
            
        except Exception as e:
            self.add_log(f"  Error test directorio de estados: {e}")

    def test_sound(self):
        """Test de módulo de sonido"""
        try:
            self.add_log("  Verificando archivo de sonido")
            if not os.path.exists(self.sound_player.sound_file):
                self.add_log(f"  Archivo de sonido no encontrado: {self.sound_player.sound_file}")
                return
                
            self.add_log("  Archivo de sonido encontrado")
            self.add_log("  Verificando inicialización de pygame")
            
            if self.sound_player.pygame_available:
                self.add_log("  Pygame inicializado exitosamente")
                self.add_log("  Intentando reproducir sonido")
                sound_played = self.sound_player.play()
                if sound_played:
                    self.add_log("  Sonido reproducido exitosamente")
                else:
                    self.add_log("  Reproducción de sonido falló")
            else:
                self.add_log("  Pygame no disponible")
                self.add_log("  Pygame no instalado")
                
        except Exception as e:
            self.add_log(f"  Error testeando sonido: {e}")

    def format_time(self, seconds):
        """Formatear tiempo a forma legible"""
        if seconds < 60:
            return f"{seconds:.1f} segundos"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds_remain = seconds % 60
            return f"{minutes:.0f} minutos {seconds_remain:.0f} segundos"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours:.0f} horas {minutes:.0f} minutos"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days:.0f} días {hours:.0f} horas"

    def calculate_search_time_years(self, total_keys, speed):
        """Calcular tiempo de búsqueda en años"""
        if speed <= 0:
            return f"∞ años"
        
        seconds = total_keys / speed
        years = seconds / (365 * 24 * 3600)
        
        if years > 1000:
            return f"∞ años"
        elif years >= 1:
            return f"{years:.1f} años"
        else:
            months = years * 12
            if months >= 1:
                return f"{months:.1f} meses"
            else:
                days = years * 365
                if days >= 1:
                    return f"{days:.1f} días"
                else:
                    hours = days * 24
                    if hours >= 1:
                        return f"{hours:.1f} horas"
                    else:
                        minutes = hours * 60
                        return f"{minutes:.1f} minutos"

    def load_help_content(self):
        """Cargar contenido de ayuda"""
        default_help = """
            <h1>Bitcoin365 Office Suite - Ayuda</h1>
            <h2> </h2>
            <h2>Contactos y soporte:</h2>
            <p>Para preguntas sobre el funcionamiento del programa contactar:</p>
            <ul>
                <li>Email: <a href="mailto:koare@hotmail.co.uk">koare@hotmail.co.uk</a></li>
                <li>Telegram: <a href="https://t.me/bitscan365">https://t.me/bitscan365</a></li>
                <li>GitHub: <a href="https://github.com">enlace</a></li>
            </ul>
            
            <h2>Soporte al desarrollador:</h2>
            <p>Si el programa es útil para usted, puede apoyar al desarrollador:</p>
            <ul>
                <li>Bitcoin: bc1qq3grmv3mtpf4yp763dj7yv64z3kj0jl07vm357</li>
                <li>Ethereum: 0x1b31a9a4ef160E52Ea57cAc63A60214CC5CF511d</li>
                <li>BuyMeCoffe: <a href="https://buymeacoffee.com">enlace</a></li>
            </ul>
            
            <h2>Importante:</h2>
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; color: #856404;">
                <strong>¡Solo para fines educativos!</strong><br>
                Use el programa responsablemente y de acuerdo con las leyes locales.
            </div>
            """
        self.help_browser.setHtml(default_help)

    def update_table_headers(self):
        """Actualizar encabezados de tabla de procesos"""
        self.process_table.setHorizontalHeaderLabels([
            "Proceso",
            "Claves",
            "Velocidad",
            "Encontrados",
            "Memoria usada",
            "Estado",
            "Tiempo activo",
            "Tiempo de búsqueda"
        ])

    def update_results_headers(self):
        """Actualizar encabezados de tabla de resultados"""
        self.results_table.setHorizontalHeaderLabels([
            "Tiempo",
            "Proceso",
            "Clave privada",
            "RIPEMD-160",
            "Tipo",
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
        """Actualizar UI desde archivos de resultados y estadísticas"""
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
        
        # Actualizar barra de estado con valores actuales
        self.update_status_bar()

    def check_method_mismatch(self):
        """Verificar discrepancia de método de generación y detener procesos inmediatamente"""
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
                                    
                                    if "generación secuencial" in message:
                                        process_method = 1
                                    elif "generación aleatoria" in message:
                                        process_method = 2
                                    else:
                                        continue
                                    
                                    if (self.expected_search_method is not None and 
                                        process_method != self.expected_search_method):
                                        
                                        self.add_log(f"ERROR CRÍTICO: Discrepancia de método de generación")
                                        self.add_log(f"Método esperado: {'Secuencial' if self.expected_search_method == 1 else 'Aleatorio'}")
                                        self.add_log(f"Método actual: {'Secuencial' if process_method == 1 else 'Aleatorio'}")
                                        self.add_log("Deteniendo procesos inmediatamente")
                                        
                                        self.process_manager.stop_processes()
                                        self.sync_start_stop_buttons("stop")
                                        
                                        QMessageBox.critical(
                                            self, 
                                            "Error crítico", 
                                            f"¡Discrepancia de método de generación detectada!\n\n"
                                            f"Método esperado: {'Secuencial' if self.expected_search_method == 1 else 'Aleatorio'}\n"
                                            f"Método actual: {'Secuencial' if process_method == 1 else 'Aleatorio'}\n\n"
                                            f"Procesos detenidos"
                                        )
                                        
                                        os.remove(file_path)
                                        return
                        
                        os.remove(file_path)
                    except json.JSONDecodeError:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error leyendo registro de proceso para verificación de método: {e}")
                        
        except Exception as e:
            print(f"Error verificando discrepancia de método: {e}")

    def check_process_completions(self):
        """Verificar finalización de procesos"""
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
                        tab_type = completion_info.get('tab_type', 'desconocido')
                        
                        self.add_log(f"¡Proceso {process_id} completó trabajo! (pestaña: {tab_type})")
                        self.add_log(f"   Claves verificadas: {total_attempts:,}")
                        self.add_log(f"   Coincidencias encontradas: {targets_found}")
                        self.add_log(f"   Tiempo de trabajo: {self.format_time(duration)}")
                        self.add_log(f"   Velocidad de búsqueda: {total_attempts/duration:,.0f} claves por segundo")
                        
                        os.remove(file_path)
                        
                    except json.JSONDecodeError:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error leyendo archivo de finalización: {e}")
                        
            for file in os.listdir(RESULTS_DIR):
                if file.startswith('process_log_'):
                    file_path = os.path.join(RESULTS_DIR, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    log_info = json.loads(line)
                                    self.add_log(f"Proceso {log_info['process_id']}: {log_info['message']}")
                        
                        os.remove(file_path)
                    except json.JSONDecodeError:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error leyendo registro de proceso: {e}")
                        
        except Exception as e:
            print(f"Error verificando finalización de procesos: {e}")

    def update_range_info_from_files(self):
        """Actualizar información de rango de proceso desde archivos con visualización correcta"""
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
                            tab_type = range_info.get('tab_type', 'desconocido')
                            
                            if process_id not in self.process_progress.get('range_logged', set()):
                                # Mostrar posición inicial real del proceso
                                self.add_log(f"Proceso {process_id} iniciado desde: 0x{actual_start:064X} con paso {step_size}, escaneando rango: 0x{range_start:064X} - 0x{range_end:064X} (pestaña: {tab_type})")
                                if 'range_logged' not in self.process_progress:
                                    self.process_progress['range_logged'] = set()
                                self.process_progress['range_logged'].add(process_id)
                                
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"Error leyendo archivo de rango {file}: {e}")
        except Exception as e:
            print(f"Error actualizando información de rango: {e}")

    def update_debug_info(self):
        """Actualizar información de depuración - VERSIÓN CORREGIDA"""
        if not self.debug_mode:
            return
            
        try:
            debug_files_to_process = []
            
            # Primero recolectar todos los archivos de depuración
            for file in os.listdir(STATS_DIR):
                if file.startswith('debug_'):
                    debug_files_to_process.append(file)
            
            # Procesar cada archivo de depuración
            for debug_file in debug_files_to_process:
                file_path = os.path.join(STATS_DIR, debug_file)
                try:
                    # Intentar abrir con bloqueo exclusivo para evitar conflictos de acceso a archivo
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    
                    # Si archivo vacío, saltar
                    if not content:
                        try:
                            os.remove(file_path)
                        except:
                            pass
                        continue
                    
                    # Procesar cada línea
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            try:
                                debug_info = json.loads(line)
                                self.add_log(f"DEPURACIÓN Proceso {debug_info['process_id']}: Clave {debug_info['key_int']}, Clave privada: {debug_info['private_key_hex']}")
                            except json.JSONDecodeError:
                                # Saltar líneas JSON inválidas
                                continue
                    
                    # Eliminar archivo después de procesar
                    try:
                        os.remove(file_path)
                    except PermissionError:
                        # Archivo puede estar aún en uso, saltar e intentar siguiente vez
                        continue
                    except Exception as e:
                        print(f"Error eliminando archivo de depuración {debug_file}: {e}")
                        
                except PermissionError:
                    # Archivo bloqueado por otro proceso, saltar ahora
                    continue
                except FileNotFoundError:
                    # Archivo ya eliminado, saltar
                    continue
                except Exception as e:
                    print(f"Error leyendo archivo de depuración {debug_file}: {e}")
                    
        except Exception as e:
            print(f"Error verificando información de depuración: {e}")

    def check_new_matches(self):
        """Verificar nuevas coincidencias encontradas"""
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
                        print(f"Error leyendo archivo de coincidencia: {e}")
        except Exception as e:
            print(f"Error verificando coincidencias: {e}")

    def private_key_to_address(self, private_key_hex, address_type):
        """Convertir clave privada a varios formatos de direcciones"""
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
        """Convertir clave privada a dirección native segwit bech32"""
        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            pub_key_obj = coincurve.PublicKey.from_valid_secret(private_key_bytes)
            pub_key = pub_key_obj.format(compressed=True)  # Segwit usa claves comprimidas
            
            sha256_hash = hashlib.sha256(pub_key).digest()
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
            
            # Para native segwit (bech32) - programa de testigo versión 0
            witness_program = b'\x00\x14' + ripemd160_hash  # versión 0 + programa de 20 bytes
            
            # Usar codificación bech32
            from bech32 import bech32_encode, convertbits
            hrp = "bc"
            data = convertbits(witness_program[2:], 8, 5)  # Convertir a array de 5 bits
            address = bech32_encode(hrp, data)
            
            return address
            
        except Exception as e:
            return f"Error: {str(e)}"

    def private_key_to_p2sh_p2wpkh_address(self, private_key_hex, compressed=True):
        """Convertir clave privada a dirección P2SH-P2WPKH"""
        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            pub_key_obj = coincurve.PublicKey.from_valid_secret(private_key_bytes)
            pub_key = pub_key_obj.format(compressed=compressed)
            
            sha256_hash = hashlib.sha256(pub_key).digest()
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
            
            # Para P2SH-P2WPKH - programa de testigo versión 0
            witness_program = b'\x00\x14' + ripemd160_hash
            
            # SHA256 del programa de testigo
            witness_program_hash = hashlib.sha256(witness_program).digest()
            # RIPEMD160 de SHA256
            script_hash = hashlib.new('ripemd160', witness_program_hash).digest()
            
            # Formato de dirección P2SH
            extended_hash = b'\x05' + script_hash
            checksum = hashlib.sha256(hashlib.sha256(extended_hash).digest()).digest()[:4]
            
            from base58 import b58encode
            address_bytes = extended_hash + checksum
            address = b58encode(address_bytes).decode('ascii')
            
            return address
            
        except Exception as e:
            return f"Error: {str(e)}"

    def display_match(self, match_info):
        """Mostrar INMEDIATAMENTE coincidencia encontrada"""
        try:
            if self.expected_search_method == 2:
                ripemd160 = match_info['ripemd160']
                if ripemd160 in self.found_hashes:
                    self.add_log(f"¡Duplicado! Hash {ripemd160} ya encontrado. Ignorado.")
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
            
            # Generar todos los formatos de direcciones
            addr_uncompressed = self.private_key_to_address(private_key_hex, "uncompressed")
            addr_compressed = self.private_key_to_address(private_key_hex, "compressed")
            addr_p2sh_p2wpkh_uncompressed = self.private_key_to_p2sh_p2wpkh_address(private_key_hex, compressed=False)
            addr_p2sh_p2wpkh_compressed = self.private_key_to_p2sh_p2wpkh_address(private_key_hex, compressed=True)
            addr_segwit = self.private_key_to_segwit_address(private_key_hex)
            
            # Establecer direcciones reales en tabla en lugar de nombres de formatos
            self.results_table.setItem(row, 5, QTableWidgetItem(addr_uncompressed))
            self.results_table.setItem(row, 6, QTableWidgetItem(addr_compressed))
            self.results_table.setItem(row, 7, QTableWidgetItem(addr_p2sh_p2wpkh_uncompressed))
            self.results_table.setItem(row, 8, QTableWidgetItem(addr_p2sh_p2wpkh_compressed))
            self.results_table.setItem(row, 9, QTableWidgetItem(addr_segwit))
            
            self.total_targets += 1
            
            self.add_log(f"¡Coincidencia encontrada! Proceso: {match_info['process_id']}")
            self.add_log(f"  Clave privada: {match_info['private_key']}")
            self.add_log(f"  RIPEMD-160: {match_info['ripemd160']}")
            self.add_log(f"  Tipo: {match_info['address_type']}")
            self.add_log(f"  Legacy P2PKH UNCOMPRESSED: {addr_uncompressed}")
            self.add_log(f"  Legacy P2PKH COMPRESSED: {addr_compressed}")
            self.add_log(f"  P2SH-P2WPKH UNCOMPRESSED: {addr_p2sh_p2wpkh_uncompressed}")
            self.add_log(f"  P2SH-P2WPKH COMPRESSED: {addr_p2sh_p2wpkh_compressed}")
            self.add_log(f"  Native SegWit Bech32: {addr_segwit}")
            self.add_log(f"  Datos guardados en tabla de resultados")
            
            self.add_log(f"  Intentando reproducir sonido")
            sound_played = self.sound_player.play()
            if sound_played:
                self.add_log(f"  Sonido reproducido exitosamente")
            else:
                self.add_log(f"  Reproducción de sonido falló")
            
            match_dialog = MatchDialog(match_info, self)
            match_dialog.show()
            QApplication.processEvents()
            
        except Exception as e:
            self.add_log(f"Error mostrando coincidencia: {e}")

    def update_stats_from_files(self):
        """Actualizar estadísticas desde archivos"""
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
                                        tab_type = stats.get('tab_type', 'desconocido')
                                        self.add_log(f"Proceso {process_id} completó trabajo (pestaña: {tab_type})")
                                        if 'completed_logged' not in self.process_progress:
                                            self.process_progress['completed_logged'] = set()
                                        self.process_progress['completed_logged'].add(process_id)
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"Error leyendo archivo de estadísticas {file}: {e}")
            
            self.total_attempts = total_attempts
            self.total_targets = total_found
            self.completed_processes_count = completed_processes
        except Exception as e:
            print(f"Error actualizando estadísticas: {e}")

    def check_completion(self):
        """Verificar finalización de todos los procesos"""
        if (self.completed_processes_count >= self.total_processes and 
            not self.completion_shown and 
            self.total_processes > 0):
            self.complete_search()

    def complete_search(self):
        """Completar búsqueda cuando rango completamente escaneado"""
        self.completion_shown = True
        self.status_ready.setText("Estado: Completado")
        
        completion_message = f"¡Rango completamente escaneado! Hashes encontrados: {self.total_targets} (pestaña: {self.current_tab_type})"
        self.add_log(completion_message)
        
        QMessageBox.information(self, "Búsqueda completada", 
                               f"¡Rango completamente escaneado!\nHashes encontrados: {self.total_targets}\nPestaña: {self.current_tab_type}")
        
        # 🔄 IMPORTANTE: Restablecer todos los botones a estado por defecto
        self.sync_start_stop_buttons("stop")
        self.sync_pause_resume_buttons("resume")
        
        # Restablecer estado de búsqueda
        self.start_time = None
        self.total_processes = 0
        self.completed_processes_count = 0
        self.is_paused = False

    def add_log(self, message: str):
        """Añadir mensaje al registro"""
        if self.log_text is None:
            print(f"REGISTRO (no listo): {message}")
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_text.append(log_entry)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def load_hashes_from_file(self, filename: str = "5000000_hash.txt") -> Set[bytes]:
        filepath = os.path.join(TXT_DIR, filename)
        hashes = set()
        if not os.path.exists(filepath):
            self.add_log(f"¡Archivo no encontrado {filepath}!")
            return hashes
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    hex_hash = line.strip()
                    if hex_hash and len(hex_hash) == 40:
                        hash_bytes = bytes.fromhex(hex_hash)
                        hashes.add(hash_bytes)
            self.add_log(f"Exitósamente cargados {len(hashes):,} hashes RIPEMD-160")
            return hashes
        except Exception as e:
            self.add_log(f"Error cargando hashes: {e}")
            return set()

    def on_search_prepared(self, result):
        """Procesar resultado de preparación de búsqueda"""
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
            
        self.add_log(f"Iniciando procesos:")
        self.add_log(f"Número de procesos: {processes}")
        self.add_log(f"Pestaña activa: {self.current_tab_name} (tipo: {self.current_tab_type})")
        
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
            method_text = "Generación secuencial"
            type_text = "Criptográficamente seguro"
            mode_text = "Continuar escaneo"  # Ahora por defecto
            
        params_text = f"""Parámetros de inicio:
- Pestaña: {self.current_tab_name} (tipo: {self.current_tab_type})
- Método de generación: {method_text}
- Tipo de generación: {type_text}
- Modo de escaneo: {mode_text}
- Número de procesos: {processes}
- Rango HEX: 0x{self.range_start:064X} - 0x{self.range_end:064X}
- Rango decimal: {self.range_start} - {self.range_end}
- Claves en rango: {self.range_end - self.range_start + 1:,}
- Límite de tiempo: {'No' if self.time_spin.value() == 0 else f'{self.time_spin.value()} horas'}"""
        
        self.launch_params_text.setPlainText(params_text)
            
        self.add_log(f"Método de generación: {method_text}")
        self.add_log(f"Tipo de generación: {type_text}")
        self.add_log(f"Modo de escaneo: {mode_text}")
        self.add_log(f"Rango HEX: 0x{self.range_start:064X} - 0x{self.range_end:064X}")
        self.add_log(f"Rango decimal: {self.range_start} - {self.range_end}")
        self.add_log(f"Claves en rango: {self.range_end - self.range_start + 1:,}")
        
        if self.time_spin.value() > 0:
            self.add_log(f"Límite de tiempo: {self.time_spin.value()} horas")
        else:
            self.add_log(f"Límite de tiempo: sin límite")
            
        self.process_manager.start_processes(configs)
        
        self.sync_start_stop_buttons("start")
        
        self.status_ready.setText("Estado: Búsqueda")
        self.add_log("=" * 80)
        self.add_log(f"¡Búsqueda iniciada!")
        self.add_log("=" * 80)

    def pause_search(self):
        """Pausar búsqueda"""
        self.add_log(f"Botón Pausar presionado")
        self.add_log(f"Pausando búsqueda")
        
        # 💾 GUARDADO DE ESTADO ANTES DE PAUSA (para generación secuencial)
        if self.expected_search_method == 1:  # Modo secuencial
            self.add_log("💾 Guardando estado antes de pausa...")
            self.save_sequential_state_before_pause()
        
        self.process_manager.stop_processes()
        self.is_paused = True
        
        self.sync_pause_resume_buttons("pause")
        
        self.status_ready.setText("Estado: Pausado")
        self.add_log(f"Búsqueda pausada")

    def save_sequential_state_before_pause(self):
        """Guardar estado para generación secuencial antes de pausa"""
        try:
            # Guardar estado desde archivos de estadísticas de procesos
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
                            self.current_tab_type,  # Usar tipo actual de pestaña
                            {
                                'attempts': stats.get('attempts', 0),
                                'targets_found': stats.get('targets_found', 0),
                                'pause_time': time.time(),
                                'reason': 'user_pause'
                            }
                        )
                        self.add_log(f"💾 Estado proceso {i} guardado antes de pausa: {hex(current_position)} (pestaña: {self.current_tab_type})")
        except Exception as e:
            self.add_log(f"❌ Error guardando estado antes de pausa: {e}")

    def resume_search(self):
        """Reanudar búsqueda"""
        self.add_log(f"Botón Continuar presionado")
        self.add_log(f"Reanudando búsqueda")
        
        # Usar StartManager para preparar búsqueda
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
        """Detener búsqueda"""
        self.add_log(f"Botón Detener presionado")
        self.add_log(f"Deteniendo búsqueda")
        
        # 💾 GUARDADO DE ESTADO ANTES DE DETENER (para generación secuencial)
        if self.expected_search_method == 1:  # Modo secuencial
            self.add_log("💾 Guardando estado antes de detener...")
            self.save_sequential_state_before_stop()
        
        self.process_manager.stop_processes()
        self.sync_start_stop_buttons("stop")
        self.sync_pause_resume_buttons("resume")
        
        self.status_ready.setText("Estado: Detenido")
        self.add_log(f"Búsqueda detenida")

    def save_sequential_state_before_stop(self):
        """Guardar estado para generación secuencial antes de detener"""
        try:
            # Guardar estado desde archivos de estadísticas de procesos
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
                            self.current_tab_type,  # Usar tipo actual de pestaña
                            {
                                'attempts': stats.get('attempts', 0),
                                'targets_found': stats.get('targets_found', 0),
                                'stop_time': time.time(),
                                'reason': 'user_stop'
                            }
                        )
                        self.add_log(f"💾 Estado proceso {i} guardado antes de detener: {hex(current_position)} (pestaña: {self.current_tab_type})")
        except Exception as e:
            self.add_log(f"❌ Error guardando estado antes de detener: {e}")

    def toggle_debug_mode(self):
        """Cambiar modo de depuración"""
        self.debug_mode = not self.debug_mode
        
        if self.debug_mode:
            # Actualizar botones de depuración en todos los widgets de rango
            for tab in [self.decimal_tab, self.hex64_tab, self.percent_tab]:
                if hasattr(tab.range_widget, 'debug_btn'):
                    tab.range_widget.debug_btn.setStyleSheet("QPushButton { background-color: #00ff00; color: #000000; }")
            self.add_log(f"Modo de depuración activado")
            self.add_log(f"Registro de depuración activado")
        else:
            for tab in [self.decimal_tab, self.hex64_tab, self.percent_tab]:
                if hasattr(tab.range_widget, 'debug_btn'):
                    tab.range_widget.debug_btn.setStyleSheet("")
            self.add_log(f"Modo de depuración desactivado")
            
        if self.process_manager.are_processes_running():
            self.add_log(f"Se requiere reinicio de procesos para aplicar cambios")

    def update_ui(self):
        """Actualizar UI con posiciones iniciales correctas de procesos"""
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
                
                self.process_table.setItem(i, 0, QTableWidgetItem(f"Proceso {i}"))
                self.process_table.setItem(i, 1, QTableWidgetItem(f"{stats['attempts']:,}"))
                self.process_table.setItem(i, 2, QTableWidgetItem(f"{stats['speed']:,.0f}/seg"))
                
                found_item = QTableWidgetItem(str(stats['targets_found']))
                if stats['targets_found'] > 0:
                    found_item.setBackground(QColor(255, 255, 0))
                    found_item.setForeground(QColor(0, 0, 255))
                    found_item.setFont(QFont("", -1, QFont.Bold))
                self.process_table.setItem(i, 3, found_item)
                
                memory_usage = stats.get('memory', 0)
                self.process_table.setItem(i, 4, QTableWidgetItem(f"{memory_usage:.1f} MB"))
                
                status_text = "Activo" if stats.get('running', True) else "Completado"
                if self.is_paused:
                    status_text = "Pausado"
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
                    search_time = f"∞ años"
                self.process_table.setItem(i, 7, QTableWidgetItem(search_time))
                
                if i not in self.process_start_times:
                    self.process_start_times[i] = time.time()
                    self.process_progress[i] = 0
                    
                    # Mostrar posición inicial real del proceso en registros
                    if self.expected_search_method == 1:  # Modo secuencial
                        process_start = self.range_start + i
                        self.add_log(f"Proceso {i} inicio secuencial: 0x{process_start:064X} con paso {processes} (pestaña: {self.current_tab_type})")
                    else:
                        self.add_log(f"Proceso {i} modo aleatorio: escaneando rango 0x{self.range_start:064X} - 0x{self.range_end:064X} (pestaña: {self.current_tab_type})")
                    
        self.status_ready.setText("Estado: Búsqueda")
        self.status_memory.setText(f"Memoria: {total_memory_usage:.1f} MB")
        self.status_speed.setText(f"Velocidad: {total_speed:,.0f} claves/seg")
        self.status_found.setText(f"Encontrados: {total_found}")
        self.status_keys.setText(f"Claves: {total_attempts:,}")
        
        if self.start_time:
            elapsed = time.time() - self.start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.status_uptime.setText(f"Tiempo activo: {time_str}")
            
        estimated_total_memory = total_memory_usage / 1024
        estimated_memory_percent = min(100, (estimated_total_memory / self.physical_memory_gb) * 100)
        self.memory_progress.setValue(int(estimated_memory_percent))
        
        memory_label_text = f"Uso total de memoria {estimated_total_memory:.2f} GB ({estimated_memory_percent:.1f}%)"
        self.memory_usage_label.setText(memory_label_text)
        
        if self.process_manager.are_processes_running():
            if self.is_paused:
                self.status_ready.setText("Estado: Pausado")
            else:
                self.status_ready.setText("Estado: Búsqueda")
        else:
            self.status_ready.setText("Estado: Listo")
            
        # Actualizar barra de estado con valores actuales
        self.update_status_bar()

    def closeEvent(self, event):
        """Manejador de evento de cierre de ventana"""
        self.add_log(f"Evento de cierre llamado")
        
        if self.process_manager.are_processes_running():
            reply = QMessageBox.question(self, "Confirmar salida",
                                       "La búsqueda aún se está ejecutando. ¿Está seguro de que desea salir?",
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)
            if reply == QMessageBox.Yes:
                # 💾 GUARDADO DE ESTADO ANTES DE SALIR (para generación secuencial)
                if self.expected_search_method == 1:  # Modo secuencial
                    self.add_log("💾 Guardando estado antes de salir...")
                    self.save_sequential_state_before_exit()
                
                self.stop_search()
                event.accept()
            else:
                event.ignore()
        else:
            # 💾 GUARDADO DE ESTADO ANTES DE SALIR (para generación secuencial)
            if self.expected_search_method == 1:  # Modo secuencial
                self.add_log("💾 Guardando estado antes de salir...")
                self.save_sequential_state_before_exit()
            
            event.accept()

    def save_sequential_state_before_exit(self):
        """Guardar estado para generación secuencial antes de salir"""
        try:
            # Guardar estado desde archivos de estadísticas de procesos
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
                            self.current_tab_type,  # Usar tipo actual de pestaña
                            {
                                'attempts': stats.get('attempts', 0),
                                'targets_found': stats.get('targets_found', 0),
                                'exit_time': time.time(),
                                'reason': 'application_exit'
                            }
                        )
                        self.add_log(f"💾 Estado proceso {i} guardado antes de salir: {hex(current_position)} (pestaña: {self.current_tab_type})")
        except Exception as e:
            self.add_log(f"❌ Error guardando estado antes de salir: {e}")

    def emergency_exit(self):
        """Función de salida de emergencia"""
        self.add_log("🚨 ¡Salida de emergencia!")
        
        # 💾 GUARDADO DE ESTADO EN SALIDA DE EMERGENCIA
        if self.expected_search_method == 1:  # Modo secuencial
            self.add_log("💾 Guardando estado de emergencia...")
            self.save_sequential_state_emergency()
        
        self.process_manager.stop_processes()
        self.add_log("Salida de emergencia completada")
        sys.exit(1)

    def save_sequential_state_emergency(self):
        """Guardado de emergencia de estado para generación secuencial"""
        try:
            # Intentar guardar estado lo más rápido posible
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
                            self.current_tab_type,  # Usar tipo actual de pestaña
                            {
                                'attempts': stats.get('attempts', 0),
                                'targets_found': stats.get('targets_found', 0),
                                'emergency_time': time.time(),
                                'reason': 'emergency_exit'
                            }
                        )
                        self.add_log(f"💾 Guardado de emergencia proceso {i}: {hex(current_position)} (pestaña: {self.current_tab_type})")
        except Exception as e:
            self.add_log(f"❌ Error guardado de emergencia: {e}")

def signal_handler(sig, frame):
    """Manejador de señal de interrupción"""
    print("\nSeñal de interrupción recibida. Cerrando...")
    
    # Intento de guardar estado durante cierre de emergencia
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
    signal.signal(signal.SIGTERM, signal_handler)  # Añadir manejador SIGTERM
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    
    # Añadir salida de emergencia a botón de terminal
    def emergency_exit_to_terminal():
        window.emergency_exit()
    
    # Conectar botones "Salir a terminal" con salida de emergencia
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
        print("Por favor instale: pip install coincurve PyQt5 psutil")
        print("Para soporte de sonido, también instale: pip install pygame")
        print("Para generación de direcciones, también instale: pip install bech32 base58")
        sys.exit(1)