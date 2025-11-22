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

# Константы
MAX_KEY = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140
MIN_KEY = 0x0000000000000000000000000000000000000000000000000000000000000001
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(SCRIPT_DIR, "json")
TXT_DIR = os.path.join(SCRIPT_DIR, "txt")
RESULTS_DIR = os.path.join(SCRIPT_DIR, "results")
STATS_DIR = os.path.join(SCRIPT_DIR, "stats")
THEMES_DIR = os.path.join(SCRIPT_DIR, "themes")
STATE_DIR = os.path.join(SCRIPT_DIR, "state")  # Новая директория для файлов состояния

class MatrixBackground(QWidget):
    """Виджет с матричной анимацией для ПЕРЕДНЕГО фона"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # РАСШИРЕННЫЙ НАБОР СИМВОЛОВ - больше цифр и символов
        self.matrix_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*()_+-=[]{}|;:,.<>?/~`"
        self.drops = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_matrix)
        self.timer.start(8)  # 20 FPS
        # УМЕНЬШИТЬ РАЗМЕР ШРИФТА для большей плотности
        self.font_size = 8  # было 14

        # КРИТИЧЕСКИ ВАЖНО: Убрать прозрачность для событий мыши, но сделать фон полупрозрачным
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)  # События проходят сквозь
        self.setStyleSheet("background: transparent;")

        # Установить высокий Z-порядок, чтобы быть выше других виджетов
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.setup_drops()

    def setup_drops(self):
        """Инициализация падающих символов"""
        if self.width() > 0 and self.height() > 0:
            self.drops = []
            # УВЕЛИЧИТЬ КОЛИЧЕСТВО КОЛОНОК в 2-3 раза
            num_columns = max(1, self.width() // (self.font_size // 2))  # Уменьшить расстояние между колонками

            for i in range(num_columns):
                # Каждая колонка имеет свою скорость и позицию
                self.drops.append({
                    'x': i * (self.font_size // 2),  # Уменьшить расстояние между колонками
                    'y': random.randint(-500, 0),
                    'speed': random.uniform(1, 20),   # Слегка уменьшить диапазон скоростей
                    'length': random.randint(40, 80), # УВЕЛИЧИТЬ ДЛИНУ КАПЛИ
                    'chars': []
                })

    def resizeEvent(self, event):
        """Обработчик события изменения размера"""
        self.setup_drops()
        super().resizeEvent(event)

    def update_matrix(self):
        """Обновление анимации"""
        if self.isVisible():
            self.update()

    def paintEvent(self, event):
        """Отрисовка матричного эффекта"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # Полупрозрачный черный фон для эффекта шлейфа
        painter.fillRect(self.rect(), QColor(0, 0, 0, 120))  # Слегка увеличена прозрачность

        font = QFont("Courier New", self.font_size, QFont.Bold)
        painter.setFont(font)

        for drop in self.drops:
            # Обновить позицию
            drop['y'] += drop['speed']

            # Если капля вышла за границы, перезапустить ее
            if drop['y'] > self.height() + drop['length'] * self.font_size:
                drop['y'] = random.randint(-500, 0)
                drop['speed'] = random.uniform(3, 8)
                drop['length'] = random.randint(12, 35)
                drop['chars'] = []  # Сбросить символы

            # Генерировать новые символы если нужно
            if len(drop['chars']) != drop['length']:
                drop['chars'] = [random.choice(self.matrix_chars) for _ in range(drop['length'])]
            else:
                # УВЕЛИЧИТЬ ВЕРОЯТНОСТЬ СМЕНЫ СИМВОЛОВ для большей динамики
                for i in range(len(drop['chars'])):
                    if random.random() < 0.18:  # Увеличено с 5% до 8%
                        drop['chars'][i] = random.choice(self.matrix_chars)

            # Отрисовать символы капли
            for i, char in enumerate(drop['chars']):
                y_pos = drop['y'] - i * self.font_size

                if -self.font_size <= y_pos < self.height():
                    # Цветовой градиент от ярко-зеленого к темно-зеленому
                    if i == 0:
                        color = QColor(0, 90, 0)  # Белый для первого символа
                    elif i == 1:
                        color = QColor(0, 255, 0)      # Ярко-зеленый
                    elif i == 2:
                        color = QColor(0, 220, 0)      # Зеленый
                    elif i < 6:
                        color = QColor(0, 180, 0)      # Средне-зеленый
                    else:
                        intensity = max(60, 200 - (i * 100 // drop['length']))  # Более плавный градиент
                        color = QColor(0, intensity, 0)

                    painter.setPen(color)
                    painter.drawText(int(drop['x']), int(y_pos), char)

class ThemeManager:
    """Менеджер тем для приложения"""

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
        """Получить путь к файлу темы"""
        theme_file = cls.THEMES.get(theme_name, "light.qss")
        return os.path.join(THEMES_DIR, theme_file)

    @classmethod
    def load_theme(cls, theme_name):
        """Загрузить тему из файла"""
        theme_path = cls.get_theme_path(theme_name)
        try:
            if os.path.exists(theme_path):
                with open(theme_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                print(f"Файл темы не найден: {theme_path}")
                return ""
        except Exception as e:
            print(f"Ошибка загрузки темы {theme_name}: {e}")
            return ""

    @classmethod
    def get_available_themes(cls):
        """Получить список доступных тем"""
        return list(cls.THEMES.keys())

# ==================== МЕХАНИЗМ СОХРАНЕНИЯ СОСТОЯНИЯ ====================
class StateManager:
    """Менеджер для сохранения и загрузки состояний процессов"""

    @staticmethod
    def get_state_filename(proc_id: int, range_start: int, range_end: int, tab_type: str = "decimal", program_name: str = "bitcoin365") -> str:
        """
        Сгенерировать уникальное имя файла состояния на основе параметров и типа вкладки

        Args:
            proc_id: ID процесса (0, 1, 2, ...)
            range_start: Начало диапазона
            range_end: Конец диапазона
            tab_type: Тип вкладки ("decimal", "hex64", "percent")
            program_name: Имя программы для разделения состояний разных скриптов

        Returns:
            str: Путь к файлу состояния
        """
        # Использовать разные форматы в зависимости от типа вкладки
        if tab_type == "decimal":
            # Для десятичной вкладки: использовать десятичные числа
            range_id = f"start_{range_start}_end_{range_end}"
        elif tab_type == "hex64":
            # Для hex64 вкладки: использовать HEX формат
            range_id = f"start_{range_start:064x}_end_{range_end:064x}"
        elif tab_type == "percent":
            # Для процентной вкладки: использовать процентные значения
            range_id = f"start_{range_start}_end_{range_end}"
        else:
            # По умолчанию: использовать HEX
            range_id = f"start_{range_start:064x}_end_{range_end:064x}"

        # Сформировать имя файла с типом вкладки
        filename = f"state_{program_name}_{tab_type}_process_{proc_id}_{range_id}.json"

        return os.path.join(STATE_DIR, filename)

    @staticmethod
    def save_state(proc_id: int, current_key: int, range_start: int, range_end: int, tab_type: str = "decimal", metadata: dict = None):
        """
        Сохранить текущее состояние процесса в JSON файл

        Args:
            proc_id: ID процесса
            current_key: Текущий обработанный ключ
            range_start: Начало диапазона
            range_end: Конец диапазона
            tab_type: Тип вкладки ("decimal", "hex64", "percent")
            metadata: Дополнительные метаданные для сохранения
        """
        try:
            # Сгенерировать имя файла с типом вкладки
            state_file = StateManager.get_state_filename(proc_id, range_start, range_end, tab_type)

            # Сформировать структуру данных
            state_data = {
                # Основные параметры диапазона
                'process_id': proc_id,
                'current_key': current_key,
                'range_start': range_start,
                'range_end': range_end,
                'tab_type': tab_type,

                # Метаданные для проверки совместимости
                'program_version': '1.0.0',
                'timestamp': datetime.now().isoformat(),
                'total_range_size': range_end - range_start + 1,
                'keys_processed': current_key - range_start,

                # Дополнительные пользовательские данные
                'metadata': metadata or {}
            }

            # Создать директорию если не существует
            os.makedirs(os.path.dirname(state_file), exist_ok=True)

            # Сохранить в JSON с красивым форматированием
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Состояние процесса {proc_id} сохранено для вкладки {tab_type}: {hex(current_key)}")

        except Exception as e:
            print(f"❌ Ошибка сохранения состояния процесса {proc_id} для вкладки {tab_type}: {e}")

    @staticmethod
    def load_state(proc_id: int, range_start: int, range_end: int, tab_type: str = "decimal", program_name: str = "bitcoin365") -> Tuple[int, int, int, dict]:
        """
        Загрузить состояние процесса с проверкой совместимости параметров

        Args:
            proc_id: ID процесса для загрузки
            range_start: Ожидаемое начало диапазона
            range_end: Ожидаемый конец диапазона
            tab_type: Тип вкладки ("decimal", "hex64", "percent")
            program_name: Имя программы

        Returns:
            Tuple: (current_key, loaded_start, loaded_end, metadata)
            или (None, None, None, None) если загрузка невозможна
        """
        try:
            state_file = StateManager.get_state_filename(proc_id, range_start, range_end, tab_type, program_name)

            if not os.path.exists(state_file):
                print(f"📭 Файл состояния процесса {proc_id} не найден для вкладки {tab_type}")
                return None, None, None, None

            # Прочитать файл состояния
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)

            # ⚠️ ВАЖНО: Проверить совместимость параметров
            loaded_start = state_data['range_start']
            loaded_end = state_data['range_end']
            loaded_tab_type = state_data.get('tab_type', 'decimal')

            if loaded_start != range_start or loaded_end != range_end or loaded_tab_type != tab_type:
                print(f"🔀 Несоответствие диапазона или типа вкладки для процесса {proc_id}")
                print(f"   Ожидалось: {range_start} - {range_end} (вкладка: {tab_type})")
                print(f"   В файле: {loaded_start} - {loaded_end} (вкладка: {loaded_tab_type})")
                return None, None, None, None

            # Проверить целостность данных
            current_key = state_data['current_key']

            if not (range_start <= current_key <= range_end):
                print(f"⚠️ Ключ вне диапазона в процессе {proc_id}")
                return None, None, None, None

            metadata = state_data.get('metadata', {})

            print(f"✅ Состояние процесса {proc_id} загружено для вкладка {tab_type}")
            print(f"   Текущий ключ: {hex(current_key)}")
            print(f"   Прогресс: {state_data.get('keys_processed', 0):,} ключей")

            return current_key, loaded_start, loaded_end, metadata

        except Exception as e:
            print(f"❌ Ошибка загрузки состояния процесса {proc_id} для вкладки {tab_type}: {e}")
            return None, None, None, None

    @staticmethod
    def cleanup_state_files(range_start: int, range_end: int, tab_type: str = "decimal", program_name: str = "bitcoin365"):
        """
        Очистить ВСЕ файлы состояния для указанного диапазона и типа вкладки

        Args:
            range_start: Начало диапазона для очистки
            range_end: Конец диапазона для очистки
            tab_type: Тип вкладки ("decimal", "hex64", "percent")
            program_name: Имя программы
        """
        try:
            if not os.path.exists(STATE_DIR):
                print("📭 Директория состояний не существует")
                return

            removed_count = 0

            # Сгенерировать целевой суффикс на основе типа вкладки
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
                    print(f"🗑️ Файл состояния удален: {filename}")

            print(f"✅ Очистка завершена для вкладки {tab_type}. Файлов удалено: {removed_count}")

        except Exception as e:
            print(f"❌ Ошибка очистки файлов состояния для вкладки {tab_type}: {e}")

    @staticmethod
    def list_state_files(tab_type: str = "all", program_name: str = "bitcoin365"):
        """
        Показать все файлы состояния для программы и конкретного типа вкладки
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
                print(f"📋 ФАЙЛЫ СОСТОЯНИЯ ({program_name}, вкладка: {tab_type}):")
                for file in sorted(state_files):
                    print(f"  📄 {file}")
            else:
                print(f"📭 Файлы состояния не найдены для {program_name} (вкладка: {tab_type})")

            return state_files

        except Exception as e:
            print(f"❌ Ошибка чтения файлов состояния: {e}")
            return []

class WorkerProcess:
    """Класс для работы в отдельном процессе"""
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
        self.tab_type = config.get('tab_type', 'decimal')  # Сохранить тип вкладки

        # Для последовательного режима - начальная позиция процесса
        if config['search_method'] == 1:  # Последовательный режим
            # Попытаться загрузить предыдущее состояние если включено продолжение поиска
            if config.get('continue_search', False):
                current_key, loaded_start, loaded_end, metadata = StateManager.load_state(
                    self.process_id,
                    config['range_start'],
                    config['range_end'],
                    self.tab_type  # Передать тип вкладки
                )
                if current_key is not None:
                    # Продолжить с последнего ключа + шаг
                    self.current_key = current_key + config['processes']
                    print(f"🔄 Процесс {self.process_id}: ПРОДОЛЖЕНИЕ с ключа {hex(current_key)} -> {hex(self.current_key)} (вкладка: {self.tab_type})")
                else:
                    # Начать с уникальной позиции для процесса
                    self.current_key = config['range_start'] + config['proc_id']
                    print(f"🆕 Процесс {self.process_id}: НОВЫЙ ПОИСК с ключа {hex(self.current_key)} (вкладка: {self.tab_type})")
            else:
                # Новый поиск - начать с уникальной позиции
                self.current_key = config['range_start'] + config['proc_id']
                print(f"🆕 Процесс {self.process_id}: НОВЫЙ ПОИСК с ключа {hex(self.current_key)} (вкладка: {self.tab_type})")

            self.step_size = config['processes']  # Шаг равен количеству процессов

            # Записать информацию о диапазоне для процесса
            self.log_range_info()

    def log_range_info(self):
        """Записать информацию о диапазоне процесса с уникальными начальными позициями"""
        try:
            # Вычислить фактическую начальную позицию для этого процесса
            if self.config['search_method'] == 1:  # Последовательный режим
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
            print(f"Ошибка записи информации о диапазоне: {e}")

    def log_completion_info(self):
        """Записать информацию о завершении диапазона"""
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

            # Также записать в общий файл для немедленного чтения
            immediate_completion_file = os.path.join(RESULTS_DIR, f"completion_{self.process_id}.json")
            os.makedirs(os.path.dirname(immediate_completion_file), exist_ok=True)
            with open(immediate_completion_file, 'w', encoding='utf-8') as f:
                json.dump(completion_info, f, ensure_ascii=False)

        except Exception as e:
            print(f"Ошибка записи информации о завершении: {e}")

    def get_process_memory_usage(self):
        """Получить использование памяти текущим процессом в МБ"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # Конвертировать в МБ
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
        """Сгенерировать последовательный ключ с уникальным диапазоном для процесса"""
        if self.current_key is None:
            # Инициализировать начальную позицию для процесса
            self.current_key = self.config['range_start'] + self.config['proc_id']
            self.step_size = self.config['processes']
            self.log_range_info()

        # Проверить, не превысили ли границы диапазона
        if self.current_key > self.config['range_end']:
            self.range_completed = True
            return None, None

        private_key = self.current_key.to_bytes(32, 'big').rjust(32, b'\x00')
        current_key = self.current_key

        # Перейти к следующему ключу с шагом равным количеству процессов
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
        """Немедленно сохранить найденное совпадение в файл"""
        try:
            match_file = os.path.join(RESULTS_DIR, f"matches_{self.process_id}.json")
            os.makedirs(os.path.dirname(match_file), exist_ok=True)
            with open(match_file, 'a', encoding='utf-8') as f:
                json.dump(match_info, f, ensure_ascii=False)
                f.write('\n')
                f.flush()  # Принудительно записать на диск
            return True
        except Exception as e:
            print(f"Ошибка немедленного сохранения совпадения: {e}")
            return False

    def save_match_to_txt(self, match_info):
        """Сохранить совпадение в текстовый файл со всеми форматами адресов"""
        try:
            txt_file = os.path.join(RESULTS_DIR, f"results_{self.process_id}.txt")
            os.makedirs(os.path.dirname(txt_file), exist_ok=True)

            # Сгенерировать все форматы адресов
            private_key_hex = match_info['private_key']
            legacy_uncompressed = self.private_key_to_address(private_key_hex, "uncompressed")
            legacy_compressed = self.private_key_to_address(private_key_hex, "compressed")
            segwit_address = self.private_key_to_segwit_address(private_key_hex)

            # Формат: key_hex64 \t ripemd160_hash \t legacy_uncompressed \t legacy_compressed \t segwit_address
            line = f"{private_key_hex}\t{match_info['ripemd160']}\t{legacy_uncompressed}\t{legacy_compressed}\t{segwit_address}\n"

            with open(txt_file, 'a', encoding='utf-8') as f:
                f.write(line)
                f.flush()
            return True
        except Exception as e:
            print(f"Ошибка сохранения совпадения в txt: {e}")
            return False

    def private_key_to_address(self, private_key_hex, address_type):
        """Конвертировать приватный ключ в формат legacy адреса"""
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
            return f"Ошибка: {str(e)}"

    def private_key_to_segwit_address(self, private_key_hex):
        """Конвертировать приватный ключ в native segwit bech32 адрес"""
        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            pub_key_obj = coincurve.PublicKey.from_valid_secret(private_key_bytes)
            pub_key = pub_key_obj.format(compressed=True)  # Segwit использует сжатые ключи

            sha256_hash = hashlib.sha256(pub_key).digest()
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()

            # Для native segwit (bech32) - программа свидетеля версии 0
            witness_program = b'\x00\x14' + ripemd160_hash  # версия 0 + 20-байтная программа

            # Использовать bech32 кодирование
            from bech32 import bech32_encode, convertbits
            hrp = "bc"
            data = convertbits(witness_program[2:], 8, 5)  # Конвертировать в 5-битный массив
            address = bech32_encode(hrp, data)

            return address

        except Exception as e:
            return f"Ошибка: {str(e)}"

    def save_stats(self):
        """Сохранить статистику в файл"""
        try:
            stats_file = os.path.join(STATS_DIR, f"stats_{self.process_id}.json")
            os.makedirs(os.path.dirname(stats_file), exist_ok=True)
            elapsed = time.time() - self.start_time
            speed = self.attempts / elapsed if elapsed > 0 else 0

            # Получить реальное использование памяти процессом
            memory_usage = self.get_process_memory_usage()

            # Для последовательного режима добавить информацию о текущей позиции
            current_position = None
            if self.config['search_method'] == 1 and self.current_key is not None:
                current_position = self.current_key - self.step_size  # Текущий обработанный ключ

            stats = {
                'process_id': self.process_id,
                'attempts': self.attempts,
                'targets_found': self.targets_found,
                'speed': speed,
                'memory': memory_usage,  # Реальное использование памяти
                'running': self.running and not self.range_completed,
                'range_completed': self.range_completed,
                'current_position': current_position,
                'tab_type': self.tab_type,
                'timestamp': time.time()
            }
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения статистики: {e}")

    def debug_log_key(self, key_int, private_key, ripemd160_uncompressed, ripemd160_compressed):
        """Записать отладочную информацию о ключе"""
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
            print(f"Ошибка в отладочном журнале: {e}")

    def add_log(self, message):
        """Добавить сообщение в журнал процесса"""
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
            print(f"Ошибка добавления журнала процесса: {e}")

    def run(self):
        """Основной рабочий цикл процесса с корректным логированием"""
        try:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)

            # Записать корректную начальную позицию
            if self.config['search_method'] == 1:  # Последовательный режим
                start_position = self.current_key if self.current_key is not None else self.config['range_start'] + self.config['proc_id']
                self.add_log(f"Процесс {self.process_id} последовательная генерация начинается с: 0x{start_position:064X} с шагом {self.step_size} (вкладка: {self.tab_type})")
            else:
                self.add_log(f"Процесс {self.process_id} случайная генерация в диапазоне: 0x{self.config['range_start']:064X} - 0x{self.config['range_end']:064X} (вкладка: {self.tab_type})")

            last_save_time = time.time()
            last_state_save_time = time.time()

            while self.running and (time.time() - self.start_time < self.config['max_time']) and not self.range_completed:
                try:
                    if self.config['search_method'] == 2:
                        # Случайная генерация
                        key_int, private_key = self.generate_random_key_in_range(
                            self.config['range_start'],
                            self.config['range_end'],
                            self.config['use_secrets']
                        )
                    else:
                        # Последовательная генерация
                        result = self.generate_sequential_key()
                        if result[0] is None:
                            # Диапазон завершен для этого процесса
                            self.range_completed = True
                            break
                        key_int, private_key = result

                    ripemd160_uncompressed = self.private_key_to_ripemd160(private_key, compressed=False)
                    ripemd160_compressed = self.private_key_to_ripemd160(private_key, compressed=True)

                    if ripemd160_uncompressed is None or ripemd160_compressed is None:
                        self.attempts += 1
                        self.batch_counter += 1
                        continue
                    # Отладочное логирование
                    if self.debug_mode:
                        self.debug_log_key(key_int, private_key, ripemd160_uncompressed, ripemd160_compressed)
                    # НЕМЕДЛЕННАЯ обработка найденных совпадений
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
                        # Немедленно сохранить в оба JSON и TXT
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
                        # Немедленно сохранить в оба JSON и TXT
                        self.save_match_immediately(match_info)
                        self.save_match_to_txt(match_info)
                        self.targets_found += 1
                        match_found = True
                    self.attempts += 1
                    self.batch_counter += 1

                    # 💾 ПЕРИОДИЧЕСКОЕ СОХРАНЕНИЕ СОСТОЯНИЯ для последовательной генерации
                    current_time = time.time()
                    if (self.config['search_method'] == 1 and
                        (self.batch_counter >= 50000 or (current_time - last_state_save_time) >= 300)):  # 5 минут

                        # Сохранить состояние процесса с типом вкладки
                        StateManager.save_state(
                            self.process_id,
                            self.current_key - self.step_size,  # Текущий обработанный ключ
                            self.config['range_start'],
                            self.config['range_end'],
                            self.tab_type,  # Передать тип вкладки
                            {
                                'attempts': self.attempts,
                                'targets_found': self.targets_found,
                                'batch_counter': self.batch_counter,
                                'start_time': self.start_time,
                                'step_size': self.step_size
                            }
                        )

                        last_state_save_time = current_time
                        # НЕ сбрасывать batch_counter здесь!

                    # Сохранение статистики отдельно от состояния
                    if self.batch_counter >= 10000:
                        self.save_stats()
                        # НЕ сбрасывать batch_counter здесь!
                        self.batch_counter = 0

                except Exception as e:
                    continue
            # Сохранить финальную статистику
            if self.range_completed:
                # Записать информацию о завершении диапазона
                self.log_completion_info()
                self.add_log(f"Процесс {self.process_id} завершил работу. Ключей проверено: {self.attempts:,}, Совпадений найдено: {self.targets_found} (вкладка: {self.tab_type})")

            # 💾 ФИНАЛЬНОЕ СОХРАНЕНИЕ СОСТОЯНИЯ ПЕРЕД ВЫХОДОМ
            if self.config['search_method'] == 1 and self.current_key is not None:
                StateManager.save_state(
                    self.process_id,
                    self.current_key - self.step_size,
                    self.config['range_start'],
                    self.config['range_end'],
                    self.tab_type,  # Передать тип вкладки
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
            print(f"Ошибка процесса {self.process_id}: {e}")

def worker_process(config):
    """Функция-обертка для выполнения в отдельном процессе"""
    import signal

    def signal_handler(signum, frame):
        print(f"Процесс {config['proc_id']} получил сигнал {signum}, завершаемся...")
        sys.exit(0)

    # Установить обработчики сигналов для корректного завершения
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        worker = WorkerProcess(config)
        worker.run()
    except KeyboardInterrupt:
        print(f"Процесс {config['proc_id']} прерван пользователем")
    except Exception as e:
        print(f"Ошибка в процессе {config['proc_id']}: {e}")
    finally:
        print(f"Процесс {config['proc_id']} завершен")

class ProcessManager:
    """Менеджер для управления независимыми процессами"""
    def __init__(self):
        self.processes = []
        self.running = False
        self.process_configs = {}
        self.terminate_timeout = 5  # Таймаут для принудительного завершения

    def start_processes(self, configs):
        """Запустить процессы с заданными конфигурациями"""
        self.running = True
        self.process_configs = configs
        self.cleanup_old_files()

        for config in configs:
            p = Process(target=worker_process, args=(config,))
            p.daemon = False  # Явно установить daemon=False для контроля
            p.start()
            self.processes.append(p)

    def stop_processes(self):
        """Остановить все процессы корректно"""
        self.running = False

        # Шаг 1: Попытка мягкого завершения
        for p in self.processes:
            if p.is_alive():
                p.terminate()  # Отправить SIGTERM

        # Шаг 2: Ожидание завершения с таймаутом
        timeout_start = time.time()
        while time.time() - timeout_start < self.terminate_timeout:
            alive_processes = [p for p in self.processes if p.is_alive()]
            if not alive_processes:
                break
            time.sleep(0.1)

        # Шаг 3: Принудительное завершение оставшихся процессов
        alive_processes = [p for p in self.processes if p.is_alive()]
        for p in alive_processes:
            try:
                p.kill()  # Принудительно завершить SIGKILL
                print(f"Принудительно завершен процесс {p.pid}")
            except:
                pass

        # Шаг 4: Очистка списка процессов
        for p in self.processes:
            try:
                p.join(timeout=1.0)  # Краткое ожидание
            except:
                pass

        self.processes.clear()

        # Шаг 5: Дополнительная проверка и очистка
        self.cleanup_zombie_processes()

    def cleanup_zombie_processes(self):
        """Очистка zombie процессов"""
        try:
            # Поиск дочерних процессов по имени
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Ищем процессы Python с нашим скриптом
                    if (proc.info['cmdline'] and
                        'python' in proc.info['name'].lower() and
                        any('bitcoin365' in str(arg).lower() for arg in proc.info['cmdline'])):

                        # Завершаем только дочерние процессы
                        parent = proc.parent()
                        if parent and parent.pid == os.getpid():
                            print(f"Найден zombie процесс {proc.info['pid']}, завершаем...")
                            proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"Ошибка очистки zombie процессов: {e}")

    def cleanup_old_files(self):
        """Очистить старые файлы результатов и статистики, но НЕ файлы состояния"""
        try:
            # Очистить только временные файлы, НЕ файлы состояния
            for file in os.listdir(RESULTS_DIR):
                if file.startswith('matches_') or file.startswith('process_log_') or file.startswith('completion_') or file.startswith('results_'):
                    os.remove(os.path.join(RESULTS_DIR, file))
            for file in os.listdir(STATS_DIR):
                if file.startswith('stats_') or file.startswith('range_') or file.startswith('debug_') or file.startswith('completion_'):
                    os.remove(os.path.join(STATS_DIR, file))
        except Exception as e:
            print(f"Ошибка очистки старых файлов: {e}")

    def are_processes_running(self):
        """Проверить, запущены ли процессы"""
        return any(p.is_alive() for p in self.processes)

class SoundPlayer:
    """Кроссплатформенный проигрыватель звуков"""
    def __init__(self):
        self.sound_file = os.path.join(SCRIPT_DIR, "alerta.wav")
        self.pygame_available = False
        self.init_pygame()

    def init_pygame(self):
        """Инициализировать pygame если доступен"""
        try:
            import pygame
            pygame.mixer.init()
            self.pygame_available = True
            print("Pygame успешно инициализирован")
        except Exception as e:
            print(f"Инициализация Pygame не удалась: {e}")
            self.pygame_available = False

    def play(self):
        """Воспроизвести звук"""
        try:
            if not os.path.exists(self.sound_file):
                print(f"Звуковой файл не найден: {self.sound_file}")
                return False

            if self.pygame_available:
                try:
                    import pygame
                    pygame.mixer.music.load(self.sound_file)
                    pygame.mixer.music.play()
                    print("Звук успешно воспроизведен с pygame")
                    return True
                except Exception as e:
                    print(f"Ошибка воспроизведения звука с pygame: {e}")
                    return False
            else:
                print("Pygame недоступен для воспроизведения звука")
                return False
        except Exception as e:
            print(f"Ошибка в проигрывателе звука: {e}")
            return False

class MatchDialog(QDialog):
    """Диалоговое окно для уведомления о совпадении"""
    def __init__(self, match_info, parent=None):
        super().__init__(parent)
        self.match_info = match_info
        self.init_ui()

        # Автоматическое закрытие через 5 секунд
        QTimer.singleShot(5000, self.accept)

    def init_ui(self):
        self.setWindowTitle("Совпадение найдено!")
        self.setModal(False)
        self.resize(600, 300)

        layout = QVBoxLayout(self)

        title_label = QLabel("<h1>Совпадение найдено!</h1>")
        title_label.setStyleSheet("color: #FF0000; font-weight: bold;")
        layout.addWidget(title_label)

        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details_text.setFont(QFont("Consolas", 9))

        details = f"""
Процесс: {self.match_info['process_id']}
Приватный ключ: {self.match_info['private_key']}
RIPEMD-160: {self.match_info['ripemd160']}
Тип: {self.match_info['address_type']}
Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        details_text.setText(details)
        layout.addWidget(details_text)

        button_box = QDialogButtonBox()
        ok_button = button_box.addButton(QDialogButtonBox.Ok)
        ok_button.clicked.connect(self.accept)
        layout.addWidget(button_box)

class StartButtonSource:
    """Перечисление источников кнопки Старт"""
    STATUS_WIDGET = "status_widget"
    SETTINGS_TAB = "settings_tab"
    DECIMAL_TAB = "decimal_tab"
    HEX64_TAB = "hex64_tab"
    PERCENT_TAB = "percent_tab"

class StartManager:
    """Централизованный диспетчер для обработки всех кнопок Старт"""
    def __init__(self, main_window):
        self.main_window = main_window
        self.last_range_tab = None  # Запомнить последнюю вкладку диапазона

    def handle_start_request(self, source):
        """Обработать запрос на старт из любого источника"""
        try:
            self.main_window.add_log("=== Поиск запущен ===")
            self.main_window.add_log(f"Источник: {self._get_source_name(source)}")

            # Определить диапазон и настройки в зависимости от источника
            range_start, range_end, settings, log_details, tab_type = self._determine_range_and_settings(source)

            # Записать детали
            self.main_window.add_log(log_details)
            self.main_window.add_log(f"HEX диапазон: 0x{range_start:064X} - 0x{range_end:064X}")
            self.main_window.add_log(f"Тип вкладки: {tab_type}")

            total_keys = range_end - range_start + 1
            self.main_window.add_log(f"Ключей в диапазоне: {total_keys:,}")

            # Вычислить приблизительное время поиска
            if total_keys > 0:
                estimated_speed = self.main_window.last_speed if self.main_window.last_speed > 0 else 100000
                estimated_years = self.main_window.calculate_search_time_years(total_keys, estimated_speed)
                self.main_window.add_log(f"Примерное время поиска: {estimated_years}")

            self.main_window.add_log("==========================")

            # Применить диапазон и настройки
            self.main_window.range_start = range_start
            self.main_window.range_end = range_end
            self.main_window.expected_search_method = settings['search_method']
            self.main_window.current_tab_type = tab_type  # Сохранить текущий тип вкладки

            # Начать поиск
            self._start_search_with_settings(settings, tab_type)

        except Exception as e:
            self.main_window.add_log(f"Ошибка: {e}")
            QMessageBox.critical(self.main_window, "Ошибка", f"Ошибка запуска поиска: {str(e)}")

    def _get_source_name(self, source):
        """Получить читаемое имя источника"""
        source_names = {
            StartButtonSource.STATUS_WIDGET: "Виджет статуса",
            StartButtonSource.SETTINGS_TAB: "Вкладка настроек",
            StartButtonSource.DECIMAL_TAB: "Десятичная вкладка",
            StartButtonSource.HEX64_TAB: "Hex64 вкладка",
            StartButtonSource.PERCENT_TAB: "Процентная вкладка"
        }
        return source_names.get(source, "Неизвестный источник")

    def _determine_range_and_settings(self, source):
        """Определить диапазон и настройки в зависимости от источника"""
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
            # Резервный вариант - Десятичная
            return self._get_from_decimal_tab()

    def _get_from_active_tab(self):
        """Получить настройки из активной вкладки"""
        current_index = self.main_window.right_panel.currentIndex()

        if current_index == 1:  # Десятичная
            return self._get_from_decimal_tab()
        elif current_index == 2:  # Hex64
            return self._get_from_hex64_tab()
        elif current_index == 3:  # Процентная
            return self._get_from_percent_tab()
        else:
            # Если активная вкладка не имеет диапазона, использовать последнюю или Десятичную
            if self.last_range_tab:
                return self._get_from_tab(self.last_range_tab)
            else:
                return self._get_from_decimal_tab()

    def _get_from_settings_tab(self):
        """Получить настройки для вкладки Настройки"""
        # Использовать последнюю активную вкладку диапазона
        if self.last_range_tab:
            range_start, range_end, settings, log_details, tab_type = self._get_from_tab(self.last_range_tab)
            log_details = f"Используется последняя вкладка: {self.last_range_tab.tab_name}\n" + log_details
            return range_start, range_end, settings, log_details, tab_type
        else:
            # Резервный вариант - Десятичная
            self.main_window.add_log(f"Нет истории вкладок, используется Десятичная по умолчанию")
            return self._get_from_decimal_tab()

    def _get_from_decimal_tab(self):
        """Получить настройки из Десятичной вкладки"""
        tab = self.main_window.decimal_tab
        self.last_range_tab = tab
        return self._get_from_tab(tab)

    def _get_from_hex64_tab(self):
        """Получить настройки из Hex64 вкладки"""
        tab = self.main_window.hex64_tab
        self.last_range_tab = tab
        return self._get_from_tab(tab)

    def _get_from_percent_tab(self):
        """Получить настройки из Процентной вкладки"""
        tab = self.main_window.percent_tab
        self.last_range_tab = tab
        return self._get_from_tab(tab)

    def _get_from_tab(self, tab):
        """Получить настройки из конкретной вкладки"""
        range_start, range_end = tab.calculate_range()

        # Получить настройки из виджетов вкладки
        search_method = tab.method_widget.get_selected_method()
        gen_method = tab.type_widget.get_selected_type()

        # Получить режим сканирования (продолжить или новый)
        scan_mode = tab.mode_widget.get_selected_mode()
        continue_search = (scan_mode == 1)  # 1 = Продолжить сканирование (теперь по умолчанию)

        # Определить тип вкладки
        if hasattr(tab, 'tab_name'):
            if tab.tab_name == "Десятичная":
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

        log_details = f"Настройки: {method_text}, {type_text}, {mode_text}"

        return range_start, range_end, settings, log_details, tab_type

    def _start_search_with_settings(self, settings, tab_type):
        """Начать поиск с заданными настройками"""
        try:
            # Подготовить поиск
            result = self._prepare_search(settings, tab_type)
            if result[0] == 'success':
                self.main_window.on_search_prepared(result)
            else:
                self.main_window.add_log(f"Ошибка подготовки поиска: {result[1]}")
                QMessageBox.warning(self.main_window, "Ошибка", str(result[1]))

        except Exception as e:
            self.main_window.add_log(f"Ошибка запуска поиска: {e}")
            QMessageBox.critical(self.main_window, "Ошибка", f"Ошибка запуска поиска: {str(e)}")

    def _prepare_search(self, settings, tab_type):
        """Подготовить поиск с заданными настройками"""
        try:
            processes = self.main_window.process_spin.value()
            max_time = self.main_window.time_spin.value() * 3600 if self.main_window.time_spin.value() > 0 else float('inf')
            target_hashes = self.main_window.load_hashes_from_file()

            if not target_hashes:
                return ('error', "Целевые хэши не найдены")
            # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Автоматическое ограничение процессов для последовательного режима
            if settings['search_method'] == 1:  # Последовательный режим
                total_keys = self.main_window.range_end - self.main_window.range_start + 1
                actual_processes = min(processes, total_keys)

                if actual_processes < processes:
                    self.main_window.add_log(f"Автоматическое сокращение процессов: {processes} -> {actual_processes}")
                    self.main_window.add_log(f"Ограничение последовательного режима: не может быть больше процессов чем ключей")
                    processes = actual_processes

                # Очистить состояние если выбран режим "Новое сканирование"
                if not settings['continue_search']:
                    self.main_window.add_log(f"🧹 Очистка предыдущих состояний для нового поиска (вкладка: {tab_type})")
                    StateManager.cleanup_state_files(self.main_window.range_start, self.main_window.range_end, tab_type)
                else:
                    # Показать существующие состояния
                    existing_states = StateManager.list_state_files(tab_type)
                    if existing_states:
                        self.main_window.add_log(f"📁 Найдены предыдущие состояния для вкладки {tab_type}. Продолжение...")
                    else:
                        self.main_window.add_log(f"🆕 Предыдущие состояния не найдены для вкладки {tab_type}. Начало с начала.")

            configs = []
            for i in range(processes):
                config = {
                    'proc_id': i,
                    'search_method': settings['search_method'],
                    'range_start': self.main_window.range_start,
                    'range_end': self.main_window.range_end,
                    'use_secrets': settings['use_secrets'],
                    'processes': processes,  # Важно: передать фактическое количество процессов
                    'max_time': max_time,
                    'target_hashes': target_hashes,
                    'continue_search': settings.get('continue_search', False),
                    'debug_mode': self.main_window.debug_mode,
                    'tab_type': tab_type  # Передать тип вкладки воркеру
                }
                configs.append(config)

            return ('success', configs)
        except Exception as e:
            return ('error', str(e))

class GenerationMethodWidget(QWidget):
    """Виджет выбора метода генерации"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.group = QGroupBox("1. Выберите метод генерации:")
        group_layout = QVBoxLayout(self.group)

        self.method_combo = QComboBox()
        self.method_combo.addItem("Последовательная генерация", 1)
        self.method_combo.addItem("Случайная генерация", 2)

        group_layout.addWidget(self.method_combo)
        layout.addWidget(self.group)

    def get_selected_method(self):
        """Получить выбранный метод"""
        return self.method_combo.currentData()

    def get_selected_method_text(self):
        """Получить текст выбранного метода"""
        return self.method_combo.currentText()

class GenerationTypeWidget(QWidget):
    """Виджет выбора типа генерации"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.group = QGroupBox("2. Способ генерации:")
        group_layout = QVBoxLayout(self.group)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Криптографически безопасный", 1)
        self.type_combo.addItem("Стандартный случайный", 2)

        group_layout.addWidget(self.type_combo)
        layout.addWidget(self.group)

    def get_selected_type(self):
        """Получить выбранный тип"""
        return self.type_combo.currentData()

    def get_selected_type_text(self):
        """Получить текст выбранного типа"""
        return self.type_combo.currentText()

class ScanModeWidget(QWidget):
    """Виджет выбора режима сканирования"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.group = QGroupBox("3. Режим сканирования:")
        group_layout = QVBoxLayout(self.group)

        self.mode_combo = QComboBox()
        # Изменен порядок: Продолжить сканирование теперь первый/по умолчанию
        self.mode_combo.addItem("Продолжить сканирование с прошлой остановки", 1)
        self.mode_combo.addItem("Новое сканирование", 2)

        group_layout.addWidget(self.mode_combo)
        layout.addWidget(self.group)

    def get_selected_mode(self):
        """Получить выбранный режим"""
        return self.mode_combo.currentData()

    def get_selected_mode_text(self):
        """Получить текст выбранного режима"""
        return self.mode_combo.currentText()

class StartStopButton(QPushButton):
    """Универсальная кнопка Старт/Стоп для всех вкладок"""
    def __init__(self, parent=None, source=None):
        super().__init__("Старт", parent)
        self.main_window = parent
        self.source = source
        self.setFixedSize(100, 40)
        self.clicked.connect(self.toggle_state)

    def toggle_state(self):
        """Переключить состояние кнопки"""
        if self.text() == "Старт":
            self.set_stop_state()
            if self.main_window and self.main_window.start_manager:
                self.main_window.start_manager.handle_start_request(self.source)
        else:
            self.set_start_state()
            if self.main_window:
                self.main_window.stop_search()

    def set_start_state(self):
        """Установить состояние Старт"""
        self.setText("Старт")

    def set_stop_state(self):
        """Установить состояние Стоп"""
        self.setText("Стоп")

class PauseResumeButton(QPushButton):
    """Универсальная кнопка Пауза/Продолжить для всех вкладок"""
    def __init__(self, parent=None):
        super().__init__("Пауза", parent)
        self.main_window = parent
        self.setFixedSize(120, 40)
        self.clicked.connect(self.toggle_state)

    def toggle_state(self):
        """Переключить состояние кнопки"""
        if self.text() == "Пауза":
            self.set_resume_state()
            if self.main_window:
                self.main_window.pause_search()
        else:
            self.set_pause_state()
            if self.main_window:
                self.main_window.resume_search()

    def set_pause_state(self):
        """Установить состояние Пауза"""
        self.setText("Пауза")

    def set_resume_state(self):
        """Установить состояние Продолжить"""
        self.setText("Продолжить")

class RangeWidget(QWidget):
    """Базовый класс для виджета настройки диапазона"""
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

        # Начальное значение
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("от"))
        self.start_edit = QLineEdit()
        self.start_edit.setMinimumHeight(35)
        start_layout.addWidget(self.start_edit)
        range_layout.addLayout(start_layout)

        # Конечное значение
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("до"))
        self.end_edit = QLineEdit()
        self.end_edit.setMinimumHeight(35)
        end_layout.addWidget(self.end_edit)
        range_layout.addLayout(end_layout)

        # Кнопки применения и управления
        button_layout = QHBoxLayout()

        self.apply_btn = QPushButton("Применить диапазон")
        self.apply_btn.setFixedSize(200, 40)

        self.start_stop_btn = StartStopButton(self.main_window, self._get_source())
        self.pause_resume_btn = PauseResumeButton(self.main_window)

        self.reset_btn = QPushButton("Сброс")
        self.reset_btn.setFixedSize(150, 40)

        self.terminal_btn = QPushButton("Выход в терминал")
        self.terminal_btn.setFixedSize(170, 40)

        self.debug_btn = QPushButton("Отладка")
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
        """Получить источник для кнопки Старт (переопределяется в дочерних классах)"""
        return StartButtonSource.SETTINGS_TAB

    def apply_range(self):
        """Абстрактный метод - должен быть переопределен в дочерних классах"""
        pass

    def get_range_values(self):
        """Получить значения диапазона"""
        return self.start_edit.text(), self.end_edit.text()

    def set_range_values(self, start, end):
        """Установить значения диапазона"""
        self.start_edit.setText(start)
        self.end_edit.setText(end)

    def setup_connections(self):
        """Настроить соединения (переопределяется в дочерних классах)"""
        self.apply_btn.clicked.connect(self.apply_range)
        self.reset_btn.clicked.connect(self.reset_settings)
        self.terminal_btn.clicked.connect(self.exit_to_terminal)
        self.debug_btn.clicked.connect(self.toggle_debug)

    def reset_settings(self):
        """Сбросить настройки (переопределяется в дочерних классах)"""
        pass

    def exit_to_terminal(self):
        """Выход в терминал"""
        if self.main_window:
            self.main_window.emergency_exit()

    def toggle_debug(self):
        """Переключить режим отладки"""
        if self.main_window:
            self.main_window.toggle_debug_mode()

class PercentRangeWidget(RangeWidget):
    """Виджет процентного диапазона"""
    def __init__(self, parent=None):
        super().__init__("Настройки процентного диапазона: введите от 1 до 100.000.000.000.000", parent)
        self.start_edit.setPlaceholderText("1")
        self.end_edit.setPlaceholderText("100000000000000")
        self.start_edit.setText("1")
        self.end_edit.setText("100000000000000")
        self.setup_connections()

    def _get_source(self):
        return StartButtonSource.PERCENT_TAB

    def apply_range(self):
        """Применить процентный диапазон"""
        try:
            start_num = int(self.start_edit.text())
            end_num = int(self.end_edit.text())

            start_num = max(1, min(100000000000000, start_num))
            end_num = max(1, min(100000000000000, end_num))

            if start_num > end_num:
                start_num, end_num = end_num, start_num

            self.start_edit.setText(str(start_num))
            self.end_edit.setText(str(end_num))

            if self.main_window:
                self.main_window.add_log(f"Процентная вкладка: Диапазон применен {start_num}% до {end_num}%")
                # Отложенное обновление информации о диапазоне
                QTimer.singleShot(100, lambda: self.main_window.update_percent_range_info(start_num, end_num))

        except ValueError:
            self.reset_range()

    def reset_range(self):
        """Сбросить диапазон к значениям по умолчанию"""
        self.start_edit.setText("1")
        self.end_edit.setText("100000000000000")
        if self.main_window:
            self.main_window.add_log(f"Процентная вкладка: Диапазон сброшен")

    def reset_settings(self):
        """Сбросить настройки"""
        self.reset_range()
        if self.main_window:
            self.main_window.add_log(f"Процентная вкладка: Настройки сброшены")

class Hex64RangeWidget(RangeWidget):
    """Виджет HEX64 диапазона"""
    def __init__(self, parent=None):
        super().__init__("Настройки HEX64 диапазона", parent)
        self.start_edit.setPlaceholderText("0x0000000000000000000000000000000000000000000000000000000000000001")
        self.end_edit.setPlaceholderText("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.start_edit.setText("0x0000000000000000000000000000000000000000000000000000000000000001")
        self.end_edit.setText("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.setup_connections()

    def _get_source(self):
        return StartButtonSource.HEX64_TAB

    def apply_range(self):
        """Применить HEX64 диапазон"""
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
                self.main_window.add_log(f"Hex64 вкладка: Диапазон применен 0x{start_int:064X} до 0x{end_int:064X}")
                # Отложенное обновление информации о диапазоне
                QTimer.singleShot(100, lambda: self.main_window.update_hex64_range_info(start_int, end_int))

        except ValueError:
            self.reset_range()

    def reset_range(self):
        """Сбросить диапазон к значениям по умолчанию"""
        self.start_edit.setText("0x0000000000000000000000000000000000000000000000000000000000000001")
        self.end_edit.setText("0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        if self.main_window:
            self.main_window.add_log(f"Hex64 вкладка: Диапазон сброшен")

    def reset_settings(self):
        """Сбросить настройки"""
        self.reset_range()
        if self.main_window:
            self.main_window.add_log(f"Hex64 вкладка: Настройки сброшены")

class DecimalRangeWidget(RangeWidget):
    """Виджет диапазона в десятичном формате"""
    def __init__(self, parent=None):
        super().__init__("Настройки десятичного диапазона", parent)
        self.start_edit.setPlaceholderText("1")
        self.end_edit.setPlaceholderText("115792089237316195423570985008687907852837564279074904382605163141518161494336")
        self.start_edit.setText("1")
        self.end_edit.setText("115792089237316195423570985008687907852837564279074904382605163141518161494336")
        self.setup_connections()

    def _get_source(self):
        return StartButtonSource.DECIMAL_TAB

    def apply_range(self):
        """Применить диапазон в десятичном формате"""
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
                self.main_window.add_log(f"Десятичная вкладка: Диапазон применен {start_int} до {end_int}")
                # Отложенное обновление информации о диапазоне
                QTimer.singleShot(100, lambda: self.main_window.update_decimal_range_info(start_int, end_int))

        except ValueError:
            self.reset_range()

    def reset_range(self):
        """Сбросить диапазон к значениям по умолчанию"""
        self.start_edit.setText("1")
        self.end_edit.setText("115792089237316195423570985008687907852837564279074904382605163141518161494336")
        if self.main_window:
            self.main_window.add_log(f"Десятичная вкладка: Диапазон сброшен")

    def reset_settings(self):
        """Сбросить настройки"""
        self.reset_range()
        if self.main_window:
            self.main_window.add_log(f"Десятичная вкладка: Настройки сброшены")

class ScrollableTab(QScrollArea):
    """Прокручиваемая область для вкладок"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.content_widget = QWidget()
        self.setWidget(self.content_widget)

    def set_layout(self, layout):
        """Установить layout для содержимого"""
        self.content_widget.setLayout(layout)

class PercentTab(ScrollableTab):
    """Вкладка для работы с процентными диапазонами"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.tab_name = "%%"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Секция метода генерации
        self.method_widget = GenerationMethodWidget(self)
        self.type_widget = GenerationTypeWidget(self)
        self.mode_widget = ScanModeWidget(self)

        layout.addWidget(self.method_widget)
        layout.addWidget(self.type_widget)
        layout.addWidget(self.mode_widget)

        # Настройки процентного диапазона
        self.range_widget = PercentRangeWidget(self.main_window)
        layout.addWidget(self.range_widget)

        # Информация о диапазоне
        self.info_group = QGroupBox("Информация о диапазоне")
        info_layout = QVBoxLayout(self.info_group)

        # Количество ключей
        keys_layout = QHBoxLayout()
        keys_layout.addWidget(QLabel("Ключей в диапазоне:"))
        self.keys_label = QLabel("0")
        self.keys_label.setMinimumHeight(30)
        keys_layout.addWidget(self.keys_label)
        keys_layout.addStretch()
        info_layout.addLayout(keys_layout)

        # Финальный диапазон
        final_range_layout = QVBoxLayout()
        final_range_layout.addWidget(QLabel("Финальный HEX диапазон:"))
        self.final_range_label = QLabel("0x0000000000000000000000000000000000000000000000000000000000000001 - 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.final_range_label.setWordWrap(True)
        self.final_range_label.setMinimumHeight(50)
        final_range_layout.addWidget(self.final_range_label)
        info_layout.addLayout(final_range_layout)

        layout.addWidget(self.info_group)

        layout.addStretch()

        self.set_layout(layout)

        # Подключить сигналы
        self.setup_connections()
        # Отложенная инициализация информации о диапазоне
        QTimer.singleShot(100, self.apply_range)

    def setup_connections(self):
        """Настроить соединения"""
        # Подключить сигналы для выпадающих меню
        self.method_widget.method_combo.currentIndexChanged.connect(self.on_method_changed)
        self.type_widget.type_combo.currentIndexChanged.connect(self.on_type_changed)
        self.mode_widget.mode_combo.currentIndexChanged.connect(self.on_mode_changed)

    def on_method_changed(self, index):
        """Обработчик изменения метода генерации"""
        method_text = self.method_widget.get_selected_method_text()
        self.main_window.add_log(f"Процентная вкладка: Выбран метод '{method_text}'")

    def on_type_changed(self, index):
        """Обработчик изменения типа генерации"""
        type_text = self.type_widget.get_selected_type_text()
        self.main_window.add_log(f"Процентная вкладка: Выбран тип '{type_text}'")

    def on_mode_changed(self, index):
        """Обработчик изменения режима сканирования"""
        mode_text = self.mode_widget.get_selected_mode_text()
        self.main_window.add_log(f"Процентная вкладка: Выбран режим '{mode_text}'")

    def apply_range(self):
        """Применить диапазон"""
        self.range_widget.apply_range()

    def calculate_range(self):
        """Вычислить диапазон на основе процентных значений"""
        try:
            start_num = int(self.range_widget.start_edit.text())
            end_num = int(self.range_widget.end_edit.text())

            total_range = MAX_KEY - MIN_KEY + 1

            start_position = ((start_num - 1) * total_range) // 100000000000000
            end_position = (end_num * total_range) // 100000000000000

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
        """Обновить информацию о диапазоне"""
        total_keys = end_key - start_key + 1

        self.keys_label.setText(f"{total_keys:,}")
        self.final_range_label.setText(f"0x{start_key:064X} - 0x{end_key:064X}")

class Hex64Tab(ScrollableTab):
    """Вкладка для работы с HEX64 диапазонами"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.tab_name = "hex64"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Секция метода генерации
        self.method_widget = GenerationMethodWidget(self)
        self.type_widget = GenerationTypeWidget(self)
        self.mode_widget = ScanModeWidget(self)

        layout.addWidget(self.method_widget)
        layout.addWidget(self.type_widget)
        layout.addWidget(self.mode_widget)

        # Настройки HEX64 диапазона
        self.range_widget = Hex64RangeWidget(self.main_window)
        layout.addWidget(self.range_widget)

        # Информация о диапазоне
        self.info_group = QGroupBox("Информация о диапазоне")
        info_layout = QVBoxLayout(self.info_group)

        # Количество ключей
        keys_layout = QHBoxLayout()
        keys_layout.addWidget(QLabel("Ключей в диапазоне:"))
        self.keys_label = QLabel("0")
        self.keys_label.setMinimumHeight(30)
        keys_layout.addWidget(self.keys_label)
        keys_layout.addStretch()
        info_layout.addLayout(keys_layout)

        # Финальный диапазон
        final_range_layout = QVBoxLayout()
        final_range_layout.addWidget(QLabel("Финальный HEX диапазон:"))
        self.final_range_label = QLabel("0x0000000000000000000000000000000000000000000000000000000000000001 - 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.final_range_label.setWordWrap(True)
        self.final_range_label.setMinimumHeight(50)
        final_range_layout.addWidget(self.final_range_label)
        info_layout.addLayout(final_range_layout)

        layout.addWidget(self.info_group)

        layout.addStretch()

        self.set_layout(layout)

        # Подключить сигналы
        self.setup_connections()
        # Отложенная инициализация информации о диапазоне
        QTimer.singleShot(100, self.apply_range)

    def setup_connections(self):
        """Настроить соединения"""
        # Подключить сигналы для выпадающих меню
        self.method_widget.method_combo.currentIndexChanged.connect(self.on_method_changed)
        self.type_widget.type_combo.currentIndexChanged.connect(self.on_type_changed)
        self.mode_widget.mode_combo.currentIndexChanged.connect(self.on_mode_changed)

    def on_method_changed(self, index):
        """Обработчик изменения метода генерации"""
        method_text = self.method_widget.get_selected_method_text()
        self.main_window.add_log(f"Hex64 вкладка: Выбран метод '{method_text}'")

    def on_type_changed(self, index):
        """Обработчик изменения типа генерации"""
        type_text = self.type_widget.get_selected_type_text()
        self.main_window.add_log(f"Hex64 вкладка: Выбран тип '{type_text}'")

    def on_mode_changed(self, index):
        """Обработчик изменения режима сканирования"""
        mode_text = self.mode_widget.get_selected_mode_text()
        self.main_window.add_log(f"Hex64 вкладка: Выбран режим '{mode_text}'")

    def apply_range(self):
        """Применить диапазон"""
        self.range_widget.apply_range()

    def calculate_range(self):
        """Вычислить диапазон на основе HEX значений"""
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
        """Обновить информацию о диапазоне"""
        total_keys = end_key - start_key + 1

        self.keys_label.setText(f"{total_keys:,}")
        self.final_range_label.setText(f"0x{start_key:064X} - 0x{end_key:064X}")

class DecimalTab(ScrollableTab):
    """Вкладка для работы с десятичными диапазонами"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.tab_name = "Десятичная"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Секция метода генерации
        self.method_widget = GenerationMethodWidget(self)
        self.type_widget = GenerationTypeWidget(self)
        self.mode_widget = ScanModeWidget(self)

        layout.addWidget(self.method_widget)
        layout.addWidget(self.type_widget)
        layout.addWidget(self.mode_widget)

        # Настройки диапазона в десятичном формате
        self.range_widget = DecimalRangeWidget(self.main_window)
        layout.addWidget(self.range_widget)

        # Информация о диапазоне
        self.info_group = QGroupBox("Информация о диапазоне")
        info_layout = QVBoxLayout(self.info_group)

        # Количество ключей
        keys_layout = QHBoxLayout()
        keys_layout.addWidget(QLabel("Ключей в диапазоне:"))
        self.keys_label = QLabel("0")
        self.keys_label.setMinimumHeight(30)
        keys_layout.addWidget(self.keys_label)
        keys_layout.addStretch()
        info_layout.addLayout(keys_layout)

        # Финальный диапазон
        final_range_layout = QVBoxLayout()
        final_range_layout.addWidget(QLabel("Финальный HEX диапазон:"))
        self.final_range_label = QLabel("0x0000000000000000000000000000000000000000000000000000000000000001 - 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364140")
        self.final_range_label.setWordWrap(True)
        self.final_range_label.setMinimumHeight(50)
        final_range_layout.addWidget(self.final_range_label)
        info_layout.addLayout(final_range_layout)

        layout.addWidget(self.info_group)

        layout.addStretch()

        self.set_layout(layout)

        # Подключить сигналы
        self.setup_connections()
        # Отложенная инициализация информации о диапазоне
        QTimer.singleShot(100, self.apply_range)

    def setup_connections(self):
        """Настроить соединения"""
        # Подключить сигналы для выпадающих меню
        self.method_widget.method_combo.currentIndexChanged.connect(self.on_method_changed)
        self.type_widget.type_combo.currentIndexChanged.connect(self.on_type_changed)
        self.mode_widget.mode_combo.currentIndexChanged.connect(self.on_mode_changed)

    def on_method_changed(self, index):
        """Обработчик изменения метода генерации"""
        method_text = self.method_widget.get_selected_method_text()
        self.main_window.add_log(f"Десятичная вкладка: Выбран метод '{method_text}'")

    def on_type_changed(self, index):
        """Обработчик изменения типа генерации"""
        type_text = self.type_widget.get_selected_type_text()
        self.main_window.add_log(f"Десятичная вкладка: Выбран тип '{type_text}'")

    def on_mode_changed(self, index):
        """Обработчик изменения режима сканирования"""
        mode_text = self.mode_widget.get_selected_mode_text()
        self.main_window.add_log(f"Десятичная вкладка: Выбран режим '{mode_text}'")

    def apply_range(self):
        """Применить диапазон"""
        self.range_widget.apply_range()

    def calculate_range(self):
        """Вычислить диапазон на основе десятичных значений"""
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
        """Обновить информацию о диапазоне"""
        total_keys = end_key - start_key + 1

        self.keys_label.setText(f"{total_keys:,}")
        self.final_range_label.setText(f"0x{start_key:064X} - 0x{end_key:064X}")

class ThemeComboBox(QComboBox):
    """Выпадающий список для выбора темы"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.init_ui()

    def init_ui(self):
        """Инициализировать UI"""
        available_themes = ThemeManager.get_available_themes()
        for theme in available_themes:
            self.addItem(theme.replace('_', ' ').title(), theme)

        # Установить тему по умолчанию
        default_theme = "light"
        index = self.findData(default_theme)
        if index >= 0:
            self.setCurrentIndex(index)

        self.currentIndexChanged.connect(self.on_theme_changed)

    def on_theme_changed(self, index):
        """Обработчик изменения темы"""
        theme_name = self.currentData()
        if self.main_window:
            self.main_window.apply_theme(theme_name)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.process_manager = ProcessManager()
        self.sound_player = SoundPlayer()
        self.start_manager = StartManager(self)  # Централизованный диспетчер старта
        self.theme_manager = ThemeManager()
        self.state_manager = StateManager()  # Менеджер состояния для последовательной генерации

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
        self.current_tab_name = "Настройки"
        self.current_tab_type = "decimal"  # Отслеживать текущий тип вкладки
        self.debug_mode = False
        self.expected_search_method = None
        self.found_hashes = set()
        self.completion_shown = False

        # Матричный фон
        self.matrix_background = None

        # Ссылки на все кнопки вкладок для синхронизации
        self.start_stop_buttons = []
        self.pause_resume_buttons = []

        # Ссылки на вкладки
        self.percent_tab = None
        self.hex64_tab = None
        self.decimal_tab = None

        # СОЗДАТЬ ДИРЕКТОРИИ ПРИ ЗАПУСКЕ
        self.create_directories_on_start()

        self.log_text = None
        self.debug_btn = None
        self.init_ui()
        self.setup_connections()

        # Очистить таблицы при запуске
        self.clear_statistics_table()

        # Установить вкладку Настройки активной по умолчанию
        self.right_panel.setCurrentIndex(0)

        # Применить тему по умолчанию
        self.apply_theme("light")

        # Запустить самопроверку при запуске
        QTimer.singleShot(1000, self.run_self_test)

    def create_directories_on_start(self):
        """Создать все необходимые директории при запуске"""
        directories = [JSON_DIR, TXT_DIR, RESULTS_DIR, STATS_DIR, THEMES_DIR, STATE_DIR]
        for directory in directories:
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"✅ Директория создана/проверена: {directory}")
            except Exception as e:
                print(f"❌ Ошибка создания директории {directory}: {e}")

    def get_physical_memory(self):
        """Получить физическую память в ГБ"""
        try:
            return psutil.virtual_memory().total / (1024 ** 3)
        except:
            return 16.0

    def cleanup_old_files_on_start(self):
        """Очистить старые файлы статистики при запуске приложения, но НЕ файлы состояния"""
        try:
            for file in os.listdir(STATS_DIR):
                if file.startswith('stats_') or file.startswith('range_') or file.startswith('debug_') or file.startswith('completion_'):
                    os.remove(os.path.join(STATS_DIR, file))
            for file in os.listdir(RESULTS_DIR):
                if file.startswith('matches_') or file.startswith('completion_') or file.startswith('process_log_') or file.startswith('results_'):
                    os.remove(os.path.join(RESULTS_DIR, file))
        except Exception as e:
            print(f"Ошибка очистки старых файлов при запуске: {e}")

    def init_ui(self):
        self.setWindowTitle("Bitcoin365 Office Suite")
        self.setGeometry(100, 100, 1100, 740)
        self.setMinimumSize(1100, 740)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.right_panel = QTabWidget()

        # Вкладка Настройки
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(10)

        # ВИДЖЕТ СТАТУСА
        self.status_group = QGroupBox("Статус")
        status_layout = QVBoxLayout(self.status_group)

        # Верхняя строка статуса
        status_top_layout = QHBoxLayout()

        self.status_ready = QLabel("Статус: Готов")
        self.status_memory = QLabel("Память: 0 МБ")
        self.status_uptime = QLabel("Время работы: 00:00:00")
        self.status_speed = QLabel("Скорость: 0 ключей/сек")
        self.status_found = QLabel("Найдено: 0")
        self.status_keys = QLabel("Ключи: 0")

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

        # Добавить кнопки управления в строку статуса
        self.start_stop_btn = StartStopButton(self, StartButtonSource.STATUS_WIDGET)
        self.pause_resume_btn = PauseResumeButton(self)

        # Сохранить ссылки для синхронизации
        self.start_stop_buttons.append(self.start_stop_btn)
        self.pause_resume_buttons.append(self.pause_resume_btn)

        status_top_layout.addWidget(self.start_stop_btn)
        status_top_layout.addWidget(self.pause_resume_btn)
        status_top_layout.addStretch()

        status_layout.addLayout(status_top_layout)

        # Информация об использовании памяти
        memory_info_layout = QHBoxLayout()
        self.memory_usage_label = QLabel("Общее использование памяти 0 ГБ, 0%")
        memory_info_layout.addWidget(self.memory_usage_label)
        status_layout.addLayout(memory_info_layout)

        # Прогресс-бар памяти
        memory_progress_layout = QHBoxLayout()
        self.memory_progress = QProgressBar()
        self.memory_progress.setMaximum(100)
        memory_progress_layout.addWidget(self.memory_progress)
        status_layout.addLayout(memory_progress_layout)

        settings_layout.addWidget(self.status_group)

        # Конфигурация процессов
        self.process_group = QGroupBox("Конфигурация процессов")
        process_layout = QVBoxLayout(self.process_group)

        # Верхняя строка - основные настройки
        process_top_layout = QHBoxLayout()

        self.processes_label = QLabel("Количество процессов:")
        process_top_layout.addWidget(self.processes_label)
        self.process_spin = QSpinBox()
        self.process_spin.setRange(1, self.max_processes)
        self.process_spin.setValue(min(self.max_processes, 12))
        process_top_layout.addWidget(self.process_spin)

        self.time_label = QLabel("Лимит времени:")
        process_top_layout.addWidget(self.time_label)
        self.time_spin = QDoubleSpinBox()
        self.time_spin.setRange(0, 1000)
        self.time_spin.setValue(0)
        self.time_spin.setSuffix(" часов (0 = без лимита)")
        process_top_layout.addWidget(self.time_spin)

        # Выбор темы перемещен в ту же строку
        self.theme_label = QLabel("Цветовая тема:")
        process_top_layout.addWidget(self.theme_label)
        self.theme_combo = ThemeComboBox(self)
        process_top_layout.addWidget(self.theme_combo)

        process_top_layout.addStretch()

        process_layout.addLayout(process_top_layout)

        settings_layout.addWidget(self.process_group)

        # Таблица процессов
        self.process_table_group = QGroupBox("Таблица процессов")
        self.process_table_group.setMinimumHeight(400)
        process_table_layout = QVBoxLayout(self.process_table_group)

        self.process_table = QTableWidget()
        self.process_table.setColumnCount(8)
        self.process_table.verticalHeader().setDefaultSectionSize(25)
        self.process_table.setAlternatingRowColors(True)
        process_table_layout.addWidget(self.process_table)

        settings_layout.addWidget(self.process_table_group)
        settings_layout.addStretch(1)

        # Создать вкладки с прокручиваемыми областями
        self.percent_tab = PercentTab(self)
        self.hex64_tab = Hex64Tab(self)
        self.decimal_tab = DecimalTab(self)

        # Сохранить ссылки на кнопки из всех вкладок
        # Кнопки теперь находятся в виджетах диапазона
        for tab in [self.percent_tab, self.hex64_tab, self.decimal_tab]:
            if hasattr(tab.range_widget, 'start_stop_btn'):
                self.start_stop_buttons.append(tab.range_widget.start_stop_btn)
            if hasattr(tab.range_widget, 'pause_resume_btn'):
                self.pause_resume_buttons.append(tab.range_widget.pause_resume_btn)

        # Вкладка результатов
        results_tab = QWidget()
        results_layout = QVBoxLayout(results_tab)

        # Добавить кнопку сохранения результатов сверху
        self.save_results_btn = QPushButton("Сохранить результаты")
        self.save_results_btn.clicked.connect(self.save_results_to_file)
        results_layout.addWidget(self.save_results_btn)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(10)
        self.results_table.setRowCount(0)
        self.update_results_headers()
        results_layout.addWidget(self.results_table)

        # Вкладка журнала
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)

        # Виджет "Параметры запуска"
        self.launch_params_group = QGroupBox("Параметры запуска")
        self.launch_params_group.setMaximumHeight(201)
        launch_params_layout = QVBoxLayout(self.launch_params_group)

        self.launch_params_text = QTextEdit()
        self.launch_params_text.setReadOnly(True)
        self.launch_params_text.setMaximumHeight(200)
        self.launch_params_text.setFont(QFont("Consolas", 8))
        self.launch_params_text.setPlainText("Параметры запуска будут отображены здесь")

        launch_params_layout.addWidget(self.launch_params_text)

        log_layout.addWidget(self.launch_params_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)

        # Вкладка помощи
        help_tab = QWidget()
        help_layout = QVBoxLayout(help_tab)

        self.help_browser = QTextBrowser()
        self.help_browser.setOpenExternalLinks(True)
        help_layout.addWidget(self.help_browser)

        self.load_help_content()

        # Добавить вкладки
        self.right_panel.addTab(settings_tab, "Настройки")
        self.right_panel.addTab(self.decimal_tab, "Десятичная")
        self.right_panel.addTab(self.hex64_tab, "hex64")
        self.right_panel.addTab(self.percent_tab, "%%")
        self.right_panel.addTab(results_tab, "Результаты")
        self.right_panel.addTab(log_tab, "Журнал")
        self.right_panel.addTab(help_tab, "Помощь")

        main_layout.addWidget(self.right_panel)

        # Создать строку статуса с расширенной информацией
        self.status_bar = self.statusBar()
        self.status_label = QLabel()
        self.status_bar.addWidget(self.status_label)

        # Инициализировать строку статуса значениями по умолчанию
        self.update_status_bar()

        # Подключить сигнал изменения вкладки
        self.right_panel.currentChanged.connect(self.on_tab_changed)

        # Убедиться, что центральный виджет правильно настроен для прозрачности
        central_widget.setAutoFillBackground(False)
        central_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        central_widget.setAttribute(Qt.WA_StyledBackground, True)

    def update_status_bar(self):
        """Обновить строку статуса текущей статистикой"""
        try:
            # Получить текущие значения из виджетов статуса
            memory_text = self.status_memory.text().replace("Память: ", "")
            speed_text = self.status_speed.text().replace("Скорость: ", "")
            keys_text = self.status_keys.text().replace("Ключи: ", "")
            uptime_text = self.status_uptime.text().replace("Время работы: ", "")
            found_text = self.status_found.text().replace("Найдено: ", "")

            # Форматировать текст строки статуса
            status_text = f"Память: {memory_text} | Скорость: {speed_text} | Всего ключей: {keys_text} | Время работы: {uptime_text} | Найдено: {found_text} | Директория скрипта: {SCRIPT_DIR}"

            self.status_label.setText(status_text)

        except Exception as e:
            print(f"Ошибка обновления строки статуса: {e}")
            # Резервный вариант - базовая информация
            self.status_label.setText(f"Директория скрипта: {SCRIPT_DIR}")

    def apply_theme(self, theme_name):
        """Применить выбранную тему"""
        try:
            # Удалить матричный фон если существовал
            if self.matrix_background:
                self.matrix_background.setParent(None)
                self.matrix_background.deleteLater()
                self.matrix_background = None

            stylesheet = self.theme_manager.load_theme(theme_name)
            if stylesheet:
                self.setStyleSheet(stylesheet)
                self.current_theme = theme_name

                # Для матричной темы добавить анимированный фон НА ПЕРЕДНИЙ ПЛАН
                if theme_name == "matrix":
                    QTimer.singleShot(100, self.apply_matrix_background)  # Отложенный старт

                self.add_log(f"Применена тема: {theme_name}")
            else:
                self.add_log(f"Не удалось загрузить тему: {theme_name}")
        except Exception as e:
            self.add_log(f"Ошибка применения темы {theme_name}: {e}")

    def apply_matrix_background(self):
        """Добавить матричный фон для матричной темы НА ПЕРЕДНИЙ ПЛАН"""
        try:
            # Удалить старый фон если существовал
            if self.matrix_background:
                self.matrix_background.setParent(None)
                self.matrix_background.deleteLater()
                self.matrix_background = None

            # Создать новый фон
            self.matrix_background = MatrixBackground(self.centralWidget())

            # КРИТИЧЕСКИ ВАЖНО: Установить геометрию и ПОДНЯТЬ НА ПЕРЕДНИЙ ПЛАН
            self.matrix_background.setGeometry(self.centralWidget().rect())

            # ВАЖНО: Поднять на передний план, а не опустить!
            self.matrix_background.raise_()  # Теперь он будет выше всех виджетов

            # Убедиться, что фон не перехватывает события мыши
            self.matrix_background.setAttribute(Qt.WA_TransparentForMouseEvents, True)

            # Показать виджет
            self.matrix_background.show()

            self.add_log("Матричный фон активирован НА ПЕРЕДНЕМ ПЛАНЕ")

        except Exception as e:
            self.add_log(f"Ошибка создания матричного фона: {e}")

    def resizeEvent(self, event):
        """Обработчик события изменения размера окна"""
        super().resizeEvent(event)
        if self.matrix_background:
            # Обновить геометрию фона при изменении размера окна
            self.matrix_background.setGeometry(self.centralWidget().rect())
            # ПЕРЕПОДНЯТЬ на передний план после изменения размера
            self.matrix_background.raise_()

    def update_percent_range_info(self, start_percent, end_percent):
        """Обновить информацию о диапазоне для процентной вкладки"""
        if hasattr(self, 'percent_tab') and self.percent_tab:
            start_key, end_key = self.calculate_percent_range(start_percent, end_percent)
            self.percent_tab.update_range_info(start_key, end_key)

    def update_hex64_range_info(self, start_key, end_key):
        """Обновить информацию о диапазоне для hex64 вкладки"""
        if hasattr(self, 'hex64_tab') and self.hex64_tab:
            self.hex64_tab.update_range_info(start_key, end_key)

    def update_decimal_range_info(self, start_key, end_key):
        """Обновить информацию о диапазоне для десятичной вкладки"""
        if hasattr(self, 'decimal_tab') and self.decimal_tab:
            self.decimal_tab.update_range_info(start_key, end_key)

    def calculate_percent_range(self, start_percent, end_percent):
        """Вычислить диапазон на основе процентных значений"""
        total_range = MAX_KEY - MIN_KEY + 1

        start_position = ((start_percent - 1) * total_range) // 100000000000000
        end_position = (end_percent * total_range) // 100000000000000

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
        """Синхронизировать состояние всех кнопок Старт/Стоп"""
        for button in self.start_stop_buttons:
            if state == "start":
                button.set_stop_state()
            else:
                button.set_start_state()

    def sync_pause_resume_buttons(self, state):
        """Синхронизировать состояние всех кнопок Пауза/Продолжить"""
        for button in self.pause_resume_buttons:
            if state == "pause":
                button.set_resume_state()
            else:
                button.set_pause_state()

    def save_results_to_file(self):
        """Сохранить результаты в TSV файл"""
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить результаты",
                os.path.join(RESULTS_DIR, "results.tsv"),
                "TSV Files (*.tsv);;All Files (*)"
            )

            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # Записать заголовки
                    headers = []
                    for col in range(self.results_table.columnCount()):
                        headers.append(self.results_table.horizontalHeaderItem(col).text())
                    f.write("\t".join(headers) + "\n")

                    # Записать данные
                    for row in range(self.results_table.rowCount()):
                        row_data = []
                        for col in range(self.results_table.columnCount()):
                            item = self.results_table.item(row, col)
                            if item is not None:
                                row_data.append(item.text())
                            else:
                                row_data.append("")
                        f.write("\t".join(row_data) + "\n")

                self.add_log(f"Результаты сохранены: {file_path}")
                QMessageBox.information(self, "Успех", f"Результаты успешно сохранены:\n{file_path}")

        except Exception as e:
            self.add_log(f"Ошибка сохранения результатов: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения результатов:\n{str(e)}")

    def on_tab_changed(self, index):
        """Обработчик изменения вкладки"""
        tab_names = {
            0: "Настройки",
            1: "Десятичная",
            2: "hex64",
            3: "%",
            4: "Результаты",
            5: "Журнал",
            6: "Помощь"
        }

        tab_name = tab_names.get(index, f"Вкладка {index}")
        self.current_tab_name = tab_name

        # Обновить текущий тип вкладки
        if tab_name == "Десятичная":
            self.current_tab_type = "decimal"
        elif tab_name == "hex64":
            self.current_tab_type = "hex64"
        elif tab_name == "%":
            self.current_tab_type = "percent"
        else:
            self.current_tab_type = "decimal"

        self.add_log(f"Выбрана вкладка: '{tab_name}' (тип: {self.current_tab_type})")

    def clear_statistics_table(self):
        """Очистить таблицу статистики и заполнить нулями"""
        processes = self.process_spin.value()
        self.process_table.setRowCount(processes)
        self.update_table_headers()

        # Заполнить таблицу нулями
        for i in range(processes):
            self.process_table.setItem(i, 0, QTableWidgetItem(f"Процесс {i}"))
            self.process_table.setItem(i, 1, QTableWidgetItem("0"))
            self.process_table.setItem(i, 2, QTableWidgetItem("0/сек"))
            self.process_table.setItem(i, 3, QTableWidgetItem("0"))
            self.process_table.setItem(i, 4, QTableWidgetItem("0 МБ"))
            self.process_table.setItem(i, 5, QTableWidgetItem("Готов"))
            self.process_table.setItem(i, 6, QTableWidgetItem("00:00:00"))
            self.process_table.setItem(i, 7, QTableWidgetItem("∞ лет"))

        # Сбросить статус
        self.status_ready.setText("Статус: Готов")
        self.status_memory.setText("Память: 0 МБ")
        self.status_uptime.setText("Время работы: 00:00:00")
        self.status_speed.setText("Скорость: 0 ключей/сек")
        self.status_found.setText("Найдено: 0")
        self.status_keys.setText("Ключи: 0")
        self.memory_usage_label.setText("Общее использование памяти 0 ГБ, 0%")
        self.memory_progress.setValue(0)

        # Обновить строку статуса
        self.update_status_bar()

    def run_self_test(self):
        """Запустить самопроверку"""
        self.add_log("=" * 80)
        self.add_log("Запуск самопроверки")
        self.add_log("=" * 80)

        # Проверить очистку таблицы статистики
        self.add_log("Проверка очистки таблицы статистики:")
        self.clear_statistics_table()

        # Тест директории состояний
        self.add_log("Тест директории состояний:")
        self.test_state_directory()

        # Тест звука
        self.add_log("Тест звукового модуля:")
        self.test_sound()

        # Тест строки статуса
        self.add_log("Тест строки статуса:")
        self.update_status_bar()

        self.add_log("=" * 80)
        self.add_log("Самопроверка завершена")
        self.add_log("=" * 80)

    def test_state_directory(self):
        """Тест функциональности директории состояний"""
        try:
            # Тест создания файла состояния для разных типов вкладок
            test_proc_id = 999
            test_range_start = 1
            test_range_end = 1000

            for tab_type in ["decimal", "hex64", "percent"]:
                self.add_log(f"  Тест StateManager для вкладки {tab_type}")
                StateManager.save_state(
                    test_proc_id,
                    500,
                    test_range_start,
                    test_range_end,
                    tab_type,
                    {'test': True}
                )

                self.add_log(f"  Тест StateManager.load_state() для вкладки {tab_type}")
                current_key, loaded_start, loaded_end, metadata = StateManager.load_state(
                    test_proc_id,
                    test_range_start,
                    test_range_end,
                    tab_type
                )

                if current_key == 500:
                    self.add_log(f"  ✅ StateManager работает корректно для вкладки {tab_type}")
                else:
                    self.add_log(f"  ❌ Тест StateManager не пройден для вкладки {tab_type}")

                # Очистка тестового файла
                StateManager.cleanup_state_files(test_range_start, test_range_end, tab_type)

        except Exception as e:
            self.add_log(f"  Ошибка теста директории состояний: {e}")

    def test_sound(self):
        """Тест звукового модуля"""
        try:
            self.add_log("  Проверка звукового файла")
            if not os.path.exists(self.sound_player.sound_file):
                self.add_log(f"  Звуковой файл не найден: {self.sound_player.sound_file}")
                return

            self.add_log("  Звуковой файл найден")
            self.add_log("  Проверка инициализации pygame")

            if self.sound_player.pygame_available:
                self.add_log("  Pygame успешно инициализирован")
                self.add_log("  Попытка воспроизвести звук")
                sound_played = self.sound_player.play()
                if sound_played:
                    self.add_log("  Звук успешно воспроизведен")
                else:
                    self.add_log("  Воспроизведение звука не удалось")
            else:
                self.add_log("  Pygame недоступен")
                self.add_log("  Pygame не установлен")

        except Exception as e:
            self.add_log(f"  Ошибка тестирования звука: {e}")

    def format_time(self, seconds):
        """Форматировать время в читаемую форму"""
        if seconds < 60:
            return f"{seconds:.1f} секунд"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds_remain = seconds % 60
            return f"{minutes:.0f} минут {seconds_remain:.0f} секунд"
        elif seconds < 86400:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours:.0f} часов {minutes:.0f} минут"
        else:
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            return f"{days:.0f} дней {hours:.0f} часов"

    def calculate_search_time_years(self, total_keys, speed):
        """Вычислить время поиска в годах"""
        if speed <= 0:
            return f"∞ лет"

        seconds = total_keys / speed
        years = seconds / (365 * 24 * 3600)

        if years > 1000:
            return f"∞ лет"
        elif years >= 1:
            return f"{years:.1f} лет"
        else:
            months = years * 12
            if months >= 1:
                return f"{months:.1f} месяцев"
            else:
                days = years * 365
                if days >= 1:
                    return f"{days:.1f} дней"
                else:
                    hours = days * 24
                    if hours >= 1:
                        return f"{hours:.1f} часов"
                    else:
                        minutes = hours * 60
                        return f"{minutes:.1f} минут"

    def load_help_content(self):
        """Загрузить содержимое помощи"""
        default_help = """
            <h1>Bitcoin365 Office Suite - Помощь</h1>
            <h2> </h2>
            <h2>Контакты и поддержка:</h2>
            <p>По вопросам работы программы обращаться:</p>
            <ul>
                <li>Email: <a href="mailto:koare@hotmail.co.uk">koare@hotmail.co.uk</a></li>
                <li>Telegram: <a href="https://t.me/bitscan365">https://t.me/bitscan365</a></li>
                <li>GitHub: <a href="https://github.com">ссылка</a></li>
            </ul>

            <h2>Поддержка разработчика:</h2>
            <p>Если программа полезна для вас, вы можете поддержать разработчика:</p>
            <ul>
                <li>Bitcoin: bc1qq3grmv3mtpf4yp763dj7yv64z3kj0jl07vm357</li>
                <li>Ethereum: 0x1b31a9a4ef160E52Ea57cAc63A60214CC5CF511d</li>
                <li>BuyMeCoffe: <a href="https://buymeacoffee.com">ссылка</a></li>
            </ul>

            <h2>Важно:</h2>
            <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; color: #856404;">
                <strong>Только для образовательных целей!</strong><br>
                Используйте программу ответственно и в соответствии с местными законами.
            </div>
            """
        self.help_browser.setHtml(default_help)

    def update_table_headers(self):
        """Обновить заголовки таблицы процессов"""
        self.process_table.setHorizontalHeaderLabels([
            "Процесс",
            "Ключи",
            "Скорость",
            "Найдено",
            "ОЗУ",
            "Статус",
            "Время работы",
            "Время поиска"
        ])

    def update_results_headers(self):
        """Обновить заголовки таблицы результатов"""
        self.results_table.setHorizontalHeaderLabels([
            "Время",
            "Процесс",
            "Приватный ключ",
            "RIPEMD-160",
            "Тип",
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
        """Обновить UI из файлов результатов и статистики"""
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

        # Обновить строку статуса текущими значениями
        self.update_status_bar()

    def check_method_mismatch(self):
        """Проверить несоответствие метода генерации и немедленно остановить процессы"""
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

                                    if "последовательная генерация" in message:
                                        process_method = 1
                                    elif "случайная генерация" in message:
                                        process_method = 2
                                    else:
                                        continue

                                    if (self.expected_search_method is not None and
                                        process_method != self.expected_search_method):

                                        self.add_log(f"КРИТИЧЕСКАЯ ОШИБКА: Несоответствие метода генерации")
                                        self.add_log(f"Ожидаемый метод: {'Последовательный' if self.expected_search_method == 1 else 'Случайный'}")
                                        self.add_log(f"Фактический метод: {'Последовательный' if process_method == 1 else 'Случайный'}")
                                        self.add_log("Немедленная остановка процессов")

                                        self.process_manager.stop_processes()
                                        self.sync_start_stop_buttons("stop")

                                        QMessageBox.critical(
                                            self,
                                            "Критическая ошибка",
                                            f"Обнаружено несоответствие метода генерации!\n\n"
                                            f"Ожидаемый метод: {'Последовательный' if self.expected_search_method == 1 else 'Случайный'}\n"
                                            f"Фактический метод: {'Последовательный' if process_method == 1 else 'Случайный'}\n\n"
                                            f"Процессы остановлены"
                                        )

                                        os.remove(file_path)
                                        return

                        os.remove(file_path)
                    except json.JSONDecodeError:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Ошибка чтения журнала процесса для проверки метода: {e}")

        except Exception as e:
            print(f"Ошибка проверки несоответствия метода: {e}")

    def check_process_completions(self):
        """Проверить завершение процессов"""
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
                        tab_type = completion_info.get('tab_type', 'неизвестно')

                        self.add_log(f"Процесс {process_id} завершил работу! (вкладка: {tab_type})")
                        self.add_log(f"   Ключей проверено: {total_attempts:,}")
                        self.add_log(f"   Совпадений найдено: {targets_found}")
                        self.add_log(f"   Время работы: {self.format_time(duration)}")
                        self.add_log(f"   Скорость поиска: {total_attempts/duration:,.0f} ключей в секунду")

                        os.remove(file_path)

                    except json.JSONDecodeError:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Ошибка чтения файла завершения: {e}")

            for file in os.listdir(RESULTS_DIR):
                if file.startswith('process_log_'):
                    file_path = os.path.join(RESULTS_DIR, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line:
                                    log_info = json.loads(line)
                                    self.add_log(f"Процесс {log_info['process_id']}: {log_info['message']}")

                        os.remove(file_path)
                    except json.JSONDecodeError:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Ошибка чтения журнала процесса: {e}")

        except Exception as e:
            print(f"Ошибка проверки завершения процессов: {e}")

    def update_range_info_from_files(self):
        """Обновить информацию о диапазоне процесса из файлов с корректным отображением"""
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
                            tab_type = range_info.get('tab_type', 'неизвестно')

                            if process_id not in self.process_progress.get('range_logged', set()):
                                # Показать реальную начальную позицию процесса
                                self.add_log(f"Процесс {process_id} начат с: 0x{actual_start:064X} с шагом {step_size}, сканирует диапазон: 0x{range_start:064X} - 0x{range_end:064X} (вкладка: {tab_type})")
                                if 'range_logged' not in self.process_progress:
                                    self.process_progress['range_logged'] = set()
                                self.process_progress['range_logged'].add(process_id)

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"Ошибка чтения файла диапазона {file}: {e}")
        except Exception as e:
            print(f"Ошибка обновления информации о диапазоне: {e}")

    def update_debug_info(self):
        """Обновить отладочную информацию - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
        if not self.debug_mode:
            return

        try:
            debug_files_to_process = []

            # Сначала собрать все отладочные файлы
            for file in os.listdir(STATS_DIR):
                if file.startswith('debug_'):
                    debug_files_to_process.append(file)

            # Обработать каждый отладочный файл
            for debug_file in debug_files_to_process:
                file_path = os.path.join(STATS_DIR, debug_file)
                try:
                    # Попытаться открыть с эксклюзивной блокировкой чтобы избежать конфликтов доступа к файлу
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()

                    # Если файл пуст, пропустить
                    if not content:
                        try:
                            os.remove(file_path)
                        except:
                            pass
                        continue

                    # Обработать каждую строку
                    lines = content.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            try:
                                debug_info = json.loads(line)
                                self.add_log(f"ОТЛАДКА Процесс {debug_info['process_id']}: Ключ {debug_info['key_int']}, Приватный ключ: {debug_info['private_key_hex']}")
                            except json.JSONDecodeError:
                                # Пропустить невалидные строки JSON
                                continue

                    # Удалить файл после обработки
                    try:
                        os.remove(file_path)
                    except PermissionError:
                        # Файл может быть все еще в использовании, пропустить и попробовать в следующий раз
                        continue
                    except Exception as e:
                        print(f"Ошибка удаления отладочного файла {debug_file}: {e}")

                except PermissionError:
                    # Файл заблокирован другим процессом, пропустить сейчас
                    continue
                except FileNotFoundError:
                    # Файл уже удален, пропустить
                    continue
                except Exception as e:
                    print(f"Ошибка чтения отладочного файла {debug_file}: {e}")

        except Exception as e:
            print(f"Ошибка проверки отладочной информации: {e}")

    def check_new_matches(self):
        """Проверить новые найденные совпадения"""
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
                        print(f"Ошибка чтения файла совпадения: {e}")
        except Exception as e:
            print(f"Ошибка проверки совпадений: {e}")

    def private_key_to_address(self, private_key_hex, address_type):
        """Конвертировать приватный ключ в различные форматы адресов"""
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
            return f"Ошибка: {str(e)}"

    def private_key_to_segwit_address(self, private_key_hex):
        """Конвертировать приватный ключ в native segwit bech32 адрес"""
        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            pub_key_obj = coincurve.PublicKey.from_valid_secret(private_key_bytes)
            pub_key = pub_key_obj.format(compressed=True)  # Segwit использует сжатые ключи

            sha256_hash = hashlib.sha256(pub_key).digest()
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()

            # Для native segwit (bech32) - программа свидетеля версии 0
            witness_program = b'\x00\x14' + ripemd160_hash  # версия 0 + 20-байтная программа

            # Использовать bech32 кодирование
            from bech32 import bech32_encode, convertbits
            hrp = "bc"
            data = convertbits(witness_program[2:], 8, 5)  # Конвертировать в 5-битный массив
            address = bech32_encode(hrp, data)

            return address

        except Exception as e:
            return f"Ошибка: {str(e)}"

    def private_key_to_p2sh_p2wpkh_address(self, private_key_hex, compressed=True):
        """Конвертировать приватный ключ в P2SH-P2WPKH адрес"""
        try:
            private_key_bytes = bytes.fromhex(private_key_hex)
            pub_key_obj = coincurve.PublicKey.from_valid_secret(private_key_bytes)
            pub_key = pub_key_obj.format(compressed=compressed)

            sha256_hash = hashlib.sha256(pub_key).digest()
            ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()

            # Для P2SH-P2WPKH - программа свидетеля версии 0
            witness_program = b'\x00\x14' + ripemd160_hash

            # SHA256 программы свидетеля
            witness_program_hash = hashlib.sha256(witness_program).digest()
            # RIPEMD160 от SHA256
            script_hash = hashlib.new('ripemd160', witness_program_hash).digest()

            # P2SH формат адреса
            extended_hash = b'\x05' + script_hash
            checksum = hashlib.sha256(hashlib.sha256(extended_hash).digest()).digest()[:4]

            from base58 import b58encode
            address_bytes = extended_hash + checksum
            address = b58encode(address_bytes).decode('ascii')

            return address

        except Exception as e:
            return f"Ошибка: {str(e)}"

    def display_match(self, match_info):
        """НЕМЕДЛЕННО отобразить найденное совпадение"""
        try:
            if self.expected_search_method == 2:
                ripemd160 = match_info['ripemd160']
                if ripemd160 in self.found_hashes:
                    self.add_log(f"Дубликат! Хэш {ripemd160} уже найден. Игнорируется.")
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

            # Сгенерировать все форматы адресов
            addr_uncompressed = self.private_key_to_address(private_key_hex, "uncompressed")
            addr_compressed = self.private_key_to_address(private_key_hex, "compressed")
            addr_p2sh_p2wpkh_uncompressed = self.private_key_to_p2sh_p2wpkh_address(private_key_hex, compressed=False)
            addr_p2sh_p2wpkh_compressed = self.private_key_to_p2sh_p2wpkh_address(private_key_hex, compressed=True)
            addr_segwit = self.private_key_to_segwit_address(private_key_hex)

            # Установить фактические адреса в таблицу вместо названий форматов
            self.results_table.setItem(row, 5, QTableWidgetItem(addr_uncompressed))
            self.results_table.setItem(row, 6, QTableWidgetItem(addr_compressed))
            self.results_table.setItem(row, 7, QTableWidgetItem(addr_p2sh_p2wpkh_uncompressed))
            self.results_table.setItem(row, 8, QTableWidgetItem(addr_p2sh_p2wpkh_compressed))
            self.results_table.setItem(row, 9, QTableWidgetItem(addr_segwit))

            self.total_targets += 1

            self.add_log(f"Совпадение найдено! Процесс: {match_info['process_id']}")
            self.add_log(f"  Приватный ключ: {match_info['private_key']}")
            self.add_log(f"  RIPEMD-160: {match_info['ripemd160']}")
            self.add_log(f"  Тип: {match_info['address_type']}")
            self.add_log(f"  Legacy P2PKH UNCOMPRESSED: {addr_uncompressed}")
            self.add_log(f"  Legacy P2PKH COMPRESSED: {addr_compressed}")
            self.add_log(f"  P2SH-P2WPKH UNCOMPRESSED: {addr_p2sh_p2wpkh_uncompressed}")
            self.add_log(f"  P2SH-P2WPKH COMPRESSED: {addr_p2sh_p2wpkh_compressed}")
            self.add_log(f"  Native SegWit Bech32: {addr_segwit}")
            self.add_log(f"  Данные сохранены в таблицу результатов")

            self.add_log(f"  Попытка воспроизвести звук")
            sound_played = self.sound_player.play()
            if sound_played:
                self.add_log(f"  Звук успешно воспроизведен")
            else:
                self.add_log(f"  Воспроизведение звука не удалось")

            match_dialog = MatchDialog(match_info, self)
            match_dialog.show()
            QApplication.processEvents()

        except Exception as e:
            self.add_log(f"Ошибка отображения совпадения: {e}")

    def update_stats_from_files(self):
        """Обновить статистику из файлов"""
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
                                        tab_type = stats.get('tab_type', 'неизвестно')
                                        self.add_log(f"Процесс {process_id} завершил работу (вкладка: {tab_type})")
                                        if 'completed_logged' not in self.process_progress:
                                            self.process_progress['completed_logged'] = set()
                                        self.process_progress['completed_logged'].add(process_id)
                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"Ошибка чтения файла статистики {file}: {e}")

            self.total_attempts = total_attempts
            self.total_targets = total_found
            self.completed_processes_count = completed_processes
        except Exception as e:
            print(f"Ошибка обновления статистики: {e}")

    def check_completion(self):
        """Проверить завершение всех процессов"""
        if (self.completed_processes_count >= self.total_processes and
            not self.completion_shown and
            self.total_processes > 0):
            self.complete_search()

    def complete_search(self):
        """Завершить поиск когда диапазон полностью просканирован"""
        self.completion_shown = True
        self.status_ready.setText("Статус: Завершено")

        completion_message = f"Весь диапазон просканирован! Найдено хэшей: {self.total_targets} (вкладка: {self.current_tab_type})"
        self.add_log(completion_message)

        QMessageBox.information(self, "Поиск завершен",
                               f"Весь диапазон просканирован!\nНайдено хэшей: {self.total_targets}\nВкладка: {self.current_tab_type}")

        # 🔄 ВАЖНО: Сбросить все кнопки в состояние по умолчанию
        self.sync_start_stop_buttons("stop")
        self.sync_pause_resume_buttons("resume")

        # Сбросить состояние поиска
        self.start_time = None
        self.total_processes = 0
        self.completed_processes_count = 0
        self.is_paused = False

    def add_log(self, message: str):
        """Добавить сообщение в журнал"""
        if self.log_text is None:
            print(f"ЖУРНАЛ (не готов): {message}")
            return

        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.log_text.append(log_entry)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def load_hashes_from_file(self, filename: str = "5000000_hash.txt") -> Set[bytes]:
        filepath = os.path.join(TXT_DIR, filename)
        hashes = set()
        if not os.path.exists(filepath):
            self.add_log(f"Файл не найден {filepath}!")
            return hashes

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    hex_hash = line.strip()
                    if hex_hash and len(hex_hash) == 40:
                        hash_bytes = bytes.fromhex(hex_hash)
                        hashes.add(hash_bytes)
            self.add_log(f"Успешно загружено {len(hashes):,} RIPEMD-160 хэшей")
            return hashes
        except Exception as e:
            self.add_log(f"Ошибка загрузки хэшей: {e}")
            return set()

    def on_search_prepared(self, result):
        """Обработать результат подготовки поиска"""
        if result[0] == 'error':
            QMessageBox.warning(self, "Ошибка", str(result[1]))
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

        self.add_log(f"Запуск процессов:")
        self.add_log(f"Количество процессов: {processes}")
        self.add_log(f"Активная вкладка: {self.current_tab_name} (тип: {self.current_tab_type})")

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
            method_text = "Последовательная генерация"
            type_text = "Криптографически безопасный"
            mode_text = "Продолжить сканирование с прошлой остановки"  # Теперь по умолчанию

        params_text = f"""Параметры запуска:
- Вкладка: {self.current_tab_name} (тип: {self.current_tab_type})
- Метод генерации: {method_text}
- Тип генерации: {type_text}
- Режим сканирования: {mode_text}
- Количество процессов: {processes}
- HEX диапазон: 0x{self.range_start:064X} - 0x{self.range_end:064X}
- Десятичный диапазон: {self.range_start} - {self.range_end}
- Ключей в диапазоне: {self.range_end - self.range_start + 1:,}
- Лимит времени: {'Нет' if self.time_spin.value() == 0 else f'{self.time_spin.value()} часов'}"""

        self.launch_params_text.setPlainText(params_text)

        self.add_log(f"Способ генерации ключей: {method_text}")
        self.add_log(f"Тип генерации: {type_text}")
        self.add_log(f"Режим сканирования: {mode_text}")
        self.add_log(f"HEX диапазон: 0x{self.range_start:064X} - 0x{self.range_end:064X}")
        self.add_log(f"Десятичный диапазон: {self.range_start} - {self.range_end}")
        self.add_log(f"Ключей в диапазоне: {self.range_end - self.range_start + 1:,}")

        if self.time_spin.value() > 0:
            self.add_log(f"Лимит времени: {self.time_spin.value()} часов")
        else:
            self.add_log(f"Лимит времени: без лимита")

        self.process_manager.start_processes(configs)

        self.sync_start_stop_buttons("start")

        self.status_ready.setText("Статус: Поиск")
        self.add_log("=" * 80)
        self.add_log(f"Поиск начат!")
        self.add_log("=" * 80)

    def pause_search(self):
        """Приостановить поиск"""
        self.add_log(f"Нажата кнопка Пауза")
        self.add_log(f"Приостановка поиска")

        # 💾 СОХРАНЕНИЕ СОСТОЯНИЯ ПЕРЕД ПАУЗОЙ (для последовательной генерации)
        if self.expected_search_method == 1:  # Последовательный режим
            self.add_log("💾 Сохранение состояния перед паузой...")
            self.save_sequential_state_before_pause()

        self.process_manager.stop_processes()
        self.is_paused = True

        self.sync_pause_resume_buttons("pause")

        self.status_ready.setText("Статус: Приостановлено")
        self.add_log(f"Поиск приостановлен")

    def save_sequential_state_before_pause(self):
        """Сохранить состояние для последовательной генерации перед паузой"""
        try:
            # Сохранить состояние из файлов статистики процессов
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
                            self.current_tab_type,  # Использовать текущий тип вкладки
                            {
                                'attempts': stats.get('attempts', 0),
                                'targets_found': stats.get('targets_found', 0),
                                'pause_time': time.time(),
                                'reason': 'user_pause'
                            }
                        )
                        self.add_log(f"💾 Состояние процесса {i} сохранено перед паузой: {hex(current_position)} (вкладка: {self.current_tab_type})")
        except Exception as e:
            self.add_log(f"❌ Ошибка сохранения состояния перед паузой: {e}")

    def resume_search(self):
        """Возобновить поиск"""
        self.add_log(f"Нажата кнопка Продолжить")
        self.add_log(f"Возобновление поиска")

        # Использовать StartManager для подготовки поиска
        if self.start_manager.last_range_tab:
            source = self.start_manager.last_range_tab.tab_name
            if source == "Десятичная":
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
        """Остановить поиск"""
        self.add_log(f"Нажата кнопка Стоп")
        self.add_log(f"Остановка поиска")

        # 💾 СОХРАНЕНИЕ СОСТОЯНИЯ ПЕРЕД ОСТАНОВКОЙ (для последовательной генерации)
        if self.expected_search_method == 1:  # Последовательный режим
            self.add_log("💾 Сохранение состояния перед остановкой...")
            self.save_sequential_state_before_stop()

        self.process_manager.stop_processes()
        self.sync_start_stop_buttons("stop")
        self.sync_pause_resume_buttons("resume")

        self.status_ready.setText("Статус: Остановлено")
        self.add_log(f"Поиск остановлен")

    def save_sequential_state_before_stop(self):
        """Сохранить состояние для последовательной генерации перед остановкой"""
        try:
            # Сохранить состояние из файлов статистики процессов
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
                            self.current_tab_type,  # Использовать текущий тип вкладки
                            {
                                'attempts': stats.get('attempts', 0),
                                'targets_found': stats.get('targets_found', 0),
                                'stop_time': time.time(),
                                'reason': 'user_stop'
                            }
                        )
                        self.add_log(f"💾 Состояние процесса {i} сохранено перед остановкой: {hex(current_position)} (вкладка: {self.current_tab_type})")
        except Exception as e:
            self.add_log(f"❌ Ошибка сохранения состояния перед остановкой: {e}")

    def toggle_debug_mode(self):
        """Переключить режим отладки"""
        self.debug_mode = not self.debug_mode

        if self.debug_mode:
            # Обновить кнопки отладки во всех виджетах диапазона
            for tab in [self.decimal_tab, self.hex64_tab, self.percent_tab]:
                if hasattr(tab.range_widget, 'debug_btn'):
                    tab.range_widget.debug_btn.setStyleSheet("QPushButton { background-color: #00ff00; color: #000000; }")
            self.add_log(f"Режим отладки включен")
            self.add_log(f"Включено отладочное логирование")
        else:
            for tab in [self.decimal_tab, self.hex64_tab, self.percent_tab]:
                if hasattr(tab.range_widget, 'debug_btn'):
                    tab.range_widget.debug_btn.setStyleSheet("")
            self.add_log(f"Режим отладки выключен")

        if self.process_manager.are_processes_running():
            self.add_log(f"Требуется перезапуск процессов для применения изменений")

    def update_ui(self):
        """Обновить UI с корректными начальными позициями процессов"""
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

                self.process_table.setItem(i, 0, QTableWidgetItem(f"Процесс {i}"))
                self.process_table.setItem(i, 1, QTableWidgetItem(f"{stats['attempts']:,}"))
                self.process_table.setItem(i, 2, QTableWidgetItem(f"{stats['speed']:,.0f}/сек"))

                found_item = QTableWidgetItem(str(stats['targets_found']))
                if stats['targets_found'] > 0:
                    found_item.setBackground(QColor(255, 255, 0))
                    found_item.setForeground(QColor(0, 0, 255))
                    found_item.setFont(QFont("", -1, QFont.Bold))
                self.process_table.setItem(i, 3, found_item)

                memory_usage = stats.get('memory', 0)
                self.process_table.setItem(i, 4, QTableWidgetItem(f"{memory_usage:.1f} МБ"))

                status_text = "Активен" if stats.get('running', True) else "Завершен"
                if self.is_paused:
                    status_text = "Приостановлен"
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
                    search_time = f"∞ лет"
                self.process_table.setItem(i, 7, QTableWidgetItem(search_time))

                if i not in self.process_start_times:
                    self.process_start_times[i] = time.time()
                    self.process_progress[i] = 0

                    # Показать реальную начальную позицию процесса в журналах
                    if self.expected_search_method == 1:  # Последовательный режим
                        process_start = self.range_start + i
                        self.add_log(f"Процесс {i} последовательный старт: 0x{process_start:064X} с шагом {processes} (вкладка: {self.current_tab_type})")
                    else:
                        self.add_log(f"Процесс {i} случайный режим: сканирует диапазон 0x{self.range_start:064X} - 0x{self.range_end:064X} (вкладка: {self.current_tab_type})")

        self.status_ready.setText("Статус: Поиск")
        self.status_memory.setText(f"Память: {total_memory_usage:.1f} МБ")
        self.status_speed.setText(f"Скорость: {total_speed:,.0f} ключей/сек")
        self.status_found.setText(f"Найдено: {total_found}")
        self.status_keys.setText(f"Ключи: {total_attempts:,}")

        if self.start_time:
            elapsed = time.time() - self.start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.status_uptime.setText(f"Время работы: {time_str}")

        estimated_total_memory = total_memory_usage / 1024
        estimated_memory_percent = min(100, (estimated_total_memory / self.physical_memory_gb) * 100)
        self.memory_progress.setValue(int(estimated_memory_percent))

        memory_label_text = f"Общее использование памяти {estimated_total_memory:.2f} ГБ ({estimated_memory_percent:.1f}%)"
        self.memory_usage_label.setText(memory_label_text)

        if self.process_manager.are_processes_running():
            if self.is_paused:
                self.status_ready.setText("Статус: Приостановлено")
            else:
                self.status_ready.setText("Статус: Поиск")
        else:
            self.status_ready.setText("Статус: Готов")

        # Обновить строку статуса текущими значениями
        self.update_status_bar()

    def closeEvent(self, event):
        """Обработчик события закрытия окна"""
        self.add_log(f"Событие закрытия вызвано")

        if self.process_manager.are_processes_running():
            reply = QMessageBox.question(self, "Подтверждение выхода",
                                       "Поиск все еще выполняется. Вы уверены, что хотите выйти?",
                                       QMessageBox.Yes | QMessageBox.No,
                                       QMessageBox.No)
            if reply == QMessageBox.Yes:
                # 💾 СОХРАНЕНИЕ СОСТОЯНИЯ ПЕРЕД ВЫХОДОМ (для последовательной генерации)
                if self.expected_search_method == 1:  # Последовательный режим
                    self.add_log("💾 Сохранение состояния перед выходом...")
                    self.save_sequential_state_before_exit()

                self.stop_search()
                event.accept()
            else:
                event.ignore()
        else:
            # 💾 СОХРАНЕНИЕ СОСТОЯНИЯ ПЕРЕД ВЫХОДОМ (для последовательной генерации)
            if self.expected_search_method == 1:  # Последовательный режим
                self.add_log("💾 Сохранение состояния перед выходом...")
                self.save_sequential_state_before_exit()

            event.accept()

    def save_sequential_state_before_exit(self):
        """Сохранить состояние для последовательной генерации перед выходом"""
        try:
            # Сохранить состояние из файлов статистики процессов
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
                            self.current_tab_type,  # Использовать текущий тип вкладки
                            {
                                'attempts': stats.get('attempts', 0),
                                'targets_found': stats.get('targets_found', 0),
                                'exit_time': time.time(),
                                'reason': 'application_exit'
                            }
                        )
                        self.add_log(f"💾 Состояние процесса {i} сохранено перед выходом: {hex(current_position)} (вкладка: {self.current_tab_type})")
        except Exception as e:
            self.add_log(f"❌ Ошибка сохранения состояния перед выходом: {e}")

    def emergency_exit(self):
        """Функция аварийного выхода"""
        self.add_log("🚨 Аварийный выход!")

        # 💾 СОХРАНЕНИЕ СОСТОЯНИЯ ПРИ АВАРИЙНОМ ВЫХОДЕ
        if self.expected_search_method == 1:  # Последовательный режим
            self.add_log("💾 Аварийное сохранение состояния...")
            self.save_sequential_state_emergency()

        # Принудительная остановка процессов
        self.process_manager.stop_processes()

        # Дополнительная очистка
        import gc
        gc.collect()

        self.add_log("Аварийный выход завершен")
        sys.exit(1)

    def save_sequential_state_emergency(self):
        """Аварийное сохранение состояния для последовательной генерации"""
        try:
            # Попытаться сохранить состояние как можно быстрее
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
                            self.current_tab_type,  # Использовать текущий тип вкладки
                            {
                                'attempts': stats.get('attempts', 0),
                                'targets_found': stats.get('targets_found', 0),
                                'emergency_time': time.time(),
                                'reason': 'emergency_exit'
                            }
                        )
                        self.add_log(f"💾 Аварийное сохранение процесса {i}: {hex(current_position)} (вкладка: {self.current_tab_type})")
        except Exception as e:
            self.add_log(f"❌ Ошибка аварийного сохранения: {e}")

def cleanup_orphaned_processes():
    """Очистка orphaned процессов при запуске"""
    try:
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if (proc.info['pid'] != current_pid and
                    proc.info['cmdline'] and
                    'python' in proc.info['name'].lower() and
                    any('bitcoin365' in str(arg).lower() for arg in proc.info['cmdline'])):

                    print(f"Найден orphaned процесс {proc.info['pid']}, завершаем...")
                    proc.terminate()
                    time.sleep(0.5)
                    if proc.is_running():
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        print(f"Ошибка очистки orphaned процессов: {e}")

def signal_handler(sig, frame):
    """Обработчик сигнала прерывания"""
    print("\nПолучен сигнал прерывания. Завершение работы...")

    # Попытка сохранить состояние во время аварийного завершения
    try:
        if hasattr(QApplication, 'instance') and QApplication.instance():
            main_window = QApplication.instance().activeWindow()
            if isinstance(main_window, MainWindow):
                main_window.emergency_exit()
    except:
        pass

    QApplication.quit()

def main():
    # Очистка orphaned процессов при запуске
    cleanup_orphaned_processes()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)  # Добавить обработчик SIGTERM

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    try:
        import coincurve
        main()
    except ImportError as e:
        print(f"Ошибка: {e}")
        print("Пожалуйста, установите: pip install coincurve PyQt5 psutil")
        print("Для поддержки звука, также установите: pip install pygame")
        print("Для генерации адресов, также установите: pip install bech32 base58")
        sys.exit(1)
