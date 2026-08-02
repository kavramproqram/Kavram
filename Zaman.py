import sys
import os
import json
import calendar
import time
import math
import subprocess
import wave
import struct
import tempfile
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QTimer, QLocale, QDate, pyqtSignal, QEvent, QObject, QSize, QRect, QPoint
from PyQt5.QtGui import QColor, QFont, QIcon, QTextCharFormat, QKeyEvent, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QSpinBox, QCheckBox, QStackedWidget,
    QFrame, QAbstractItemView, QCalendarWidget, QDialog, 
    QDialogButtonBox, QStyleFactory, QGridLayout, QTextEdit, QLineEdit,
    QSlider, QGroupBox, QMessageBox, QListWidget, QListWidgetItem,
    QSystemTrayIcon, QMenu, QAction, QSizePolicy, QScrollArea, QLayout
)

# Enable High DPI scaling and crisp pixmap rendering at Qt core level
if hasattr(Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# Suppress Qt background system logging on Linux desktop environments
os.environ["QT_LOGGING_RULES"] = "qt.*=false;*.debug=false;qt.x11.*=false;qt.qpa.*=false;qt.accessibility.*=false"

class UIScale:
    """Centralized UI Scaling and Design Token System for High-DPI and multi-resolution scalability."""
    BUTTON_HEIGHT = 36
    BUTTON_MIN_WIDTH = 100
    ICON_SIZE = 18
    INPUT_HEIGHT = 36
    PADDING = 8
    RADIUS = 8
    FONT_FAMILY = "'Inter', 'Segoe UI', 'SF Pro Text', 'Noto Sans', sans-serif"

class ModernButton(QPushButton):
    """
    Standardized Responsive Button component with eye-friendly styling.
    Dynamically adjusts height based on FontMetrics so text never overflows.
    """
    def __init__(self, text="", icon=None, tooltip="", parent=None):
        super().__init__(text, parent)
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(UIScale.ICON_SIZE, UIScale.ICON_SIZE))
        if tooltip:
            self.setToolTip(tooltip)
            
        fm = self.fontMetrics()
        calculated_h = max(UIScale.BUTTON_HEIGHT, fm.height() + 14)
        self.setMinimumHeight(calculated_h)
        self.setMinimumWidth(UIScale.BUTTON_MIN_WIDTH)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

class FlowLayout(QLayout):
    """Custom FlowLayout that wraps child widgets to the next row when horizontal space shrinks."""
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.item_list = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.item_list.append(item)

    def count(self):
        return len(self.item_list)

    def itemAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.item_list:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()

        for item in self.item_list:
            wid = item.widget()
            space_x = spacing + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            space_y = spacing + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                x = rect.x()
                y = y + line_height + space_y
                next_x = x + item.sizeHint().width() + space_x
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            line_height = max(line_height, item.sizeHint().height())

        return y + line_height - rect.y()

def resource_path(relative_path):
    """PyInstaller support and local path resolver."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

DARK_STYLE = f"""
QMainWindow, QDialog {{
    background-color: #16181D;
}}
QWidget {{
    background-color: #16181D;
    color: #E2E8F0;
    font-family: {UIScale.FONT_FAMILY};
}}
QFrame {{
    background-color: #1E222A;
    border-radius: {UIScale.RADIUS}px;
    border: 1px solid #2D333F;
}}
QLabel {{
    background: transparent;
    border: none;
    color: #F1F5F9;
}}
QLabel:disabled {{
    color: #64748B;
}}
QComboBox, QLineEdit, QTextEdit {{
    background-color: #262B35;
    border: 1px solid #3B4252;
    padding: 6px 12px;
    border-radius: {UIScale.RADIUS}px;
    color: #F8FAFC;
    selection-background-color: #2563EB;
    selection-color: #ffffff;
    min-height: {UIScale.INPUT_HEIGHT - 12}px;
}}
QComboBox:hover, QLineEdit:hover, QTextEdit:hover {{
    border: 1px solid #3B82F6;
}}
QComboBox:focus, QLineEdit:focus, QTextEdit:focus {{
    border: 1px solid #60A5FA;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: #262B35;
    selection-background-color: #3B82F6;
    selection-color: #ffffff;
    color: #F8FAFC;
    border: 1px solid #3B4252;
    outline: none;
}}
QPushButton {{
    background-color: #2A2F3B;
    border: 1px solid #3B4252;
    padding: 6px 14px;
    border-radius: {UIScale.RADIUS}px;
    color: #E2E8F0;
    font-weight: 600;
    text-align: center;
}}
QPushButton:hover {{
    background-color: #363C4A;
    border: 1px solid #4C566A;
    color: #FFFFFF;
}}
QPushButton:pressed {{
    background-color: #1E222A;
    color: #94A3B8;
}}
QPushButton:checked {{
    background-color: #2563EB;
    border: 1px solid #3B82F6;
    color: #ffffff;
}}
QPushButton:disabled {{
    background-color: #1E222A;
    border: 1px solid #2D333F;
    color: #64748B;
}}
QTableWidget, QListWidget {{
    background-color: #1E222A;
    alternate-background-color: #222630;
    gridline-color: #2D333F;
    selection-background-color: #333A48;
    selection-color: #ffffff;
    color: #E2E8F0;
    border: 1px solid #2D333F;
    border-radius: {UIScale.RADIUS}px;
    outline: none;
}}
QTableWidget::item, QListWidget::item {{
    padding: 6px;
}}
QTableWidget::item:selected, QListWidget::item:selected {{
    background-color: #2C3545;
    color: #ffffff;
}}
QHeaderView::section {{
    background-color: #262B35;
    padding: 8px;
    border: 1px solid #2D333F;
    font-weight: bold;
    color: #94A3B8;
}}
QProgressBar {{
    border: 1px solid #2D333F;
    border-radius: {UIScale.RADIUS}px;
    text-align: center;
    background-color: #181B22;
    color: #F8FAFC;
    font-weight: bold;
}}
QProgressBar::chunk {{
    background-color: #10B981;
    border-radius: {UIScale.RADIUS - 1}px;
}}
QSpinBox {{
    background-color: #262B35;
    border: 1px solid #3B4252;
    padding: 6px;
    border-radius: {UIScale.RADIUS}px;
    color: #F8FAFC;
    min-height: {UIScale.INPUT_HEIGHT - 12}px;
}}
QSpinBox:hover {{
    border: 1px solid #3B82F6;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: #363C4A;
    border-radius: 3px;
    margin: 1px;
}}
QCheckBox {{
    background: transparent;
    border: none;
    color: #E2E8F0;
    font-weight: 500;
}}
QCheckBox:disabled {{
    color: #64748B;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #3B4252;
    background-color: #262B35;
}}
QCheckBox::indicator:hover {{
    border: 1px solid #3B82F6;
}}
QCheckBox::indicator:checked {{
    background-color: #10B981;
    border: 1px solid #34D399;
}}
QSlider::groove:horizontal {{
    border: 1px solid #3B4252;
    height: 6px;
    background: #262B35;
    margin: 2px 0;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: #3B82F6;
    border: 1px solid #60A5FA;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: #60A5FA;
}}
QGroupBox {{
    border: 1px solid #2D333F;
    border-radius: {UIScale.RADIUS}px;
    margin-top: 1.2ex;
    font-weight: bold;
    padding: 12px;
    background-color: #1E222A;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 8px;
    background-color: #16181D;
    color: #38BDF8;
    border-radius: 4px;
}}
QMenu {{
    background-color: #1E222A;
    border: 1px solid #3B4252;
    color: #E2E8F0;
}}
QMenu::item:selected {{
    background-color: #2563EB;
    color: #ffffff;
}}
QScrollBar:vertical, QScrollBar:horizontal {{
    background-color: #16181D;
    border: none;
    width: 8px;
    height: 8px;
}}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
    background-color: #2D333F;
    border-radius: 4px;
}}
QScrollBar::handle:hover {{
    background-color: #3B82F6;
}}
"""

HINT_STYLE = (
    "color: #94A3B8;"
    "font-style: italic;"
    "font-weight: 500;"
    "padding-bottom: 2px;"
)

def format_sayi(sayi):
    return f"{int(sayi):,}".replace(',', '.')

def create_scrollable_container(child_widget):
    """Wraps any page widget in a transparent QScrollArea so low-res screens never overflow."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
    scroll.setWidget(child_widget)
    return scroll

def generate_pleasant_chime(volume_factor=0.85):
    """Generates a pleasant bell chime audio file (WAV) scaled by user volume setting."""
    temp_dir = tempfile.gettempdir()
    vol_int = int(volume_factor * 100)
    wav_path = os.path.join(temp_dir, f"kavram_chime_v{vol_int}.wav")
    
    if os.path.exists(wav_path):
        return wav_path

    sample_rate = 44100
    duration = 1.2
    n_samples = int(sample_rate * duration)
    
    freq1, freq2, freq3 = 659.25, 987.77, 1318.51
    
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        envelope = math.exp(-3.5 * t)
        if t < 0.01:
            envelope *= (t / 0.01)
            
        val = (0.5 * math.sin(2 * math.pi * freq1 * t) +
               0.3 * math.sin(2 * math.pi * freq2 * t) +
               0.2 * math.sin(2 * math.pi * freq3 * t))
               
        val *= envelope * 0.8 * volume_factor
        sample_int = int(val * 32767)
        sample_int = max(-32768, min(32767, sample_int))
        samples.append(sample_int)

    try:
        with wave.open(wav_path, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            packed_data = struct.pack(f'<{len(samples)}h', *samples)
            wav_file.writeframes(packed_data)
    except Exception as e:
        print(f"Chime WAV generation error: {e}")
        
    return wav_path

def play_sound_file(wav_path, volume=0.85):
    """Plays WAV audio file across platforms using QtMultimedia or native fallbacks."""
    if not os.path.exists(wav_path):
        return

    try:
        from PyQt5.QtMultimedia import QSoundEffect
        from PyQt5.QtCore import QUrl
        if not hasattr(play_sound_file, "_sound_effect"):
            play_sound_file._sound_effect = QSoundEffect()
        play_sound_file._sound_effect.setSource(QUrl.fromLocalFile(os.path.abspath(wav_path)))
        play_sound_file._sound_effect.setVolume(volume)
        play_sound_file._sound_effect.play()
        return
    except Exception:
        pass

    if sys.platform.startswith("win"):
        try:
            import winsound
            winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception:
            pass
    elif sys.platform.startswith("darwin"):
        try:
            subprocess.Popen(["afplay", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except Exception:
            pass
    else:
        for cmd in ["paplay", "aplay", "pw-play", "canberra-gtk-play"]:
            try:
                subprocess.Popen([cmd, wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                continue

class DataManager:
    def __init__(self):
        self.dir_name = "Zaman_Veri"
        self.file_name = os.path.join(self.dir_name, "veriler.json")
        self.data = {
            "keep_notes": [],
            "tasks": [],
            "settings": {
                "time_offset_seconds": 0,
                "life_target_ts": None,
                "mod3_seg1": 0,
                "mod3_seg2": 8,
                "mod3_seg3": 11,
                "mod3_show_seconds": False,
                "pomodoro": {
                    "sound_enabled": True,
                    "volume": 85,
                    "sound_work_end": True,
                    "sound_break_end": True,
                    "show_notification": True,
                    "work_min": 25,
                    "short_break_min": 5,
                    "long_break_min": 15,
                    "active_task_id": None
                },
                "screen": {
                    "red": 100,
                    "green": 100,
                    "blue_filter": 0,
                    "brightness": 100,
                    "darkness": 0,
                    "gray": False,
                    "reading": False,
                    "blue_mode": "Her Zaman",
                    "blue_start_hour": 20,
                    "blue_end_hour": 7,
                    "gray_mode": "Her Zaman",
                    "gray_start_hour": 22,
                    "gray_end_hour": 6
                }
            }
        }
        self.load()

    def load(self):
        if not os.path.exists(self.dir_name):
            os.makedirs(self.dir_name)
        
        if os.path.exists(self.file_name):
            try:
                with open(self.file_name, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if "keep_notes" in loaded: self.data["keep_notes"] = loaded["keep_notes"]
                    if "tasks" in loaded: self.data["tasks"] = loaded["tasks"]
                    if "settings" in loaded: 
                        for k, v in loaded["settings"].items():
                            if isinstance(v, dict) and k in self.data["settings"]:
                                self.data["settings"][k].update(v)
                            else:
                                self.data["settings"][k] = v
            except Exception as e:
                print(f"Veri okunurken hata: {e}")
                
    def save(self):
        if not os.path.exists(self.dir_name):
            os.makedirs(self.dir_name)
        try:
            with open(self.file_name, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Veri kaydedilirken hata: {e}")

    def add_keep_note(self, title, text, date_str=None):
        if not date_str:
            date_str = get_now().strftime("%Y-%m-%d %H:%M")
        note = {
            "id": str(time.time()),
            "title": title.strip(),
            "text": text.strip(),
            "date": date_str
        }
        self.data["keep_notes"].insert(0, note)
        self.save()
        return note

    def delete_keep_note(self, note_id):
        self.data["keep_notes"] = [n for n in self.data["keep_notes"] if n["id"] != note_id]
        self.save()

    def update_keep_note(self, note_id, title, text):
        for n in self.data["keep_notes"]:
            if n["id"] == note_id:
                n["title"] = title.strip()
                n["text"] = text.strip()
                break
        self.save()

    def add_task(self, title, priority="Orta", task_date="", task_time=""):
        task = {
            "id": str(time.time()),
            "title": title.strip(),
            "priority": priority,
            "date": task_date,
            "time": task_time,
            "completed": False,
            "pomodoro_sessions": 0
        }
        self.data["tasks"].append(task)
        self.save()
        return task

    def toggle_task(self, task_id):
        for t in self.data["tasks"]:
            if t["id"] == task_id:
                t["completed"] = not t["completed"]
                break
        self.save()

    def delete_task(self, task_id):
        self.data["tasks"] = [t for t in self.data["tasks"] if t["id"] != task_id]
        self.save()

    def increment_task_pomo(self, task_id):
        for t in self.data["tasks"]:
            if t["id"] == task_id:
                t["pomodoro_sessions"] += 1
                break
        self.save()

db = DataManager()

def get_now():
    """Returns synchronized reference time based on custom time offset."""
    offset = db.data["settings"].get("time_offset_seconds", 0)
    return datetime.now() + timedelta(seconds=offset)

class PomodoroEngine(QObject):
    """Global Pomodoro Engine running independently of active tab."""
    tick_signal = pyqtSignal()
    phase_changed_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        pomo_cfg = db.data["settings"].get("pomodoro", {})
        self.work_sec = pomo_cfg.get("work_min", 25) * 60
        self.short_break_sec = pomo_cfg.get("short_break_min", 5) * 60
        self.long_break_sec = pomo_cfg.get("long_break_min", 15) * 60
        self.cycles_before_long = 4

        self.phase = "Çalışma"
        self.remaining_seconds = self.work_sec
        self.cycles_done = 0
        self.running = False
        self.target_ts = None
        self.on_alarm_callback = None

    def reset(self):
        self.phase = "Çalışma"
        self.remaining_seconds = self.work_sec
        self.cycles_done = 0
        self.running = False
        self.target_ts = None
        self.tick_signal.emit()

    def start_or_pause(self):
        if not self.running:
            self.running = True
            self.target_ts = get_now() + timedelta(seconds=self.remaining_seconds)
        else:
            self.running = False
            if self.target_ts:
                self.remaining_seconds = max(0, int((self.target_ts - get_now()).total_seconds()))
            self.target_ts = None
        self.tick_signal.emit()

    def tick(self):
        if self.running and self.target_ts:
            secs = (self.target_ts - get_now()).total_seconds()
            if secs <= 0:
                self._next_phase()
            else:
                self.remaining_seconds = int(secs)
        self.tick_signal.emit()

    def _next_phase(self):
        old_phase = self.phase
        active_task_id = db.data["settings"].get("pomodoro", {}).get("active_task_id")
        if old_phase == "Çalışma" and active_task_id:
            db.increment_task_pomo(active_task_id)

        if self.phase == "Çalışma":
            self.cycles_done += 1
            if self.cycles_done % self.cycles_before_long == 0:
                self.phase = "Uzun Mola"
                self.remaining_seconds = self.long_break_sec
            else:
                self.phase = "Kısa Mola"
                self.remaining_seconds = self.short_break_sec
        else:
            self.phase = "Çalışma"
            self.remaining_seconds = self.work_sec

        self.running = False
        self.target_ts = None
        
        pomo_cfg = db.data["settings"].get("pomodoro", {})
        snd_enabled = pomo_cfg.get("sound_enabled", True)
        snd_work = pomo_cfg.get("sound_work_end", True)
        snd_break = pomo_cfg.get("sound_break_end", True)
        vol = pomo_cfg.get("volume", 85) / 100.0

        should_play = False
        if snd_enabled:
            if old_phase == "Çalışma" and snd_work:
                should_play = True
            elif old_phase != "Çalışma" and snd_break:
                should_play = True

        if should_play:
            wav_path = generate_pleasant_chime(vol)
            play_sound_file(wav_path, vol)

        if self.on_alarm_callback:
            self.on_alarm_callback(old_phase, self.phase)

        self.phase_changed_signal.emit(self.phase)

class PomodoroWidget(QWidget):
    def __init__(self, engine: PomodoroEngine, on_note_added_cb):
        super().__init__()
        self.engine = engine
        self.on_note_added_cb = on_note_added_cb
        self.engine.tick_signal.connect(self.update_display)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        display_frame = QFrame()
        display_layout = QVBoxLayout(display_frame)
        
        self.phase_label = QLabel(self.engine.phase)
        self.phase_label.setAlignment(Qt.AlignCenter)
        phase_font = QFont()
        phase_font.setPointSize(16)
        phase_font.setBold(True)
        self.phase_label.setFont(phase_font)
        display_layout.addWidget(self.phase_label)

        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        time_font = QFont()
        time_font.setPointSize(44)
        time_font.setBold(True)
        self.time_label.setFont(time_font)
        display_layout.addWidget(self.time_label)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setMinimumHeight(10)
        display_layout.addWidget(self.progress)
        
        layout.addWidget(display_frame)

        task_frame = QFrame()
        task_layout = QHBoxLayout(task_frame)
        task_layout.setContentsMargins(8, 4, 8, 4)
        
        task_lbl = QLabel("Göreve Bağla:")
        task_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        task_layout.addWidget(task_lbl)
        
        self.task_combo = QComboBox()
        self.task_combo.setMinimumHeight(UIScale.INPUT_HEIGHT)
        self.task_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.task_combo.currentIndexChanged.connect(self.on_task_selected)
        task_layout.addWidget(self.task_combo, 1)
        layout.addWidget(task_frame)

        btn_layout = QHBoxLayout()
        self.start_btn = ModernButton("▶ Başlat / Duraklat", tooltip="Zamanlayıcıyı Başlat/Duraklat")
        self.start_btn.setStyleSheet("background-color: #1E3A8A; color: #FFFFFF; font-weight: bold;")
        self.start_btn.clicked.connect(self.engine.start_or_pause)
        btn_layout.addWidget(self.start_btn, 1)

        self.reset_btn = ModernButton("↺ Sıfırla", tooltip="Süreyi Sıfırla")
        self.reset_btn.clicked.connect(self.engine.reset)
        btn_layout.addWidget(self.reset_btn, 1)

        layout.addLayout(btn_layout)

        sound_gb = QGroupBox("Zil ve Ses Ayarları")
        sound_layout = QGridLayout(sound_gb)
        sound_layout.setSpacing(8)

        pomo_cfg = db.data["settings"].get("pomodoro", {})

        self.sound_check = QCheckBox("Zil Sesi Açık")
        self.sound_check.setChecked(pomo_cfg.get("sound_enabled", True))
        self.sound_check.toggled.connect(self.save_sound_settings)
        sound_layout.addWidget(self.sound_check, 0, 0)

        self.work_sound_check = QCheckBox("Çalışma Bitince Ses")
        self.work_sound_check.setChecked(pomo_cfg.get("sound_work_end", True))
        self.work_sound_check.toggled.connect(self.save_sound_settings)
        sound_layout.addWidget(self.work_sound_check, 0, 1)

        self.break_sound_check = QCheckBox("Mola Bitince Ses")
        self.break_sound_check.setChecked(pomo_cfg.get("sound_break_end", True))
        self.break_sound_check.toggled.connect(self.save_sound_settings)
        sound_layout.addWidget(self.break_sound_check, 0, 2)

        self.notif_check = QCheckBox("Masaüstü Bildirimi")
        self.notif_check.setChecked(pomo_cfg.get("show_notification", True))
        self.notif_check.toggled.connect(self.save_sound_settings)
        sound_layout.addWidget(self.notif_check, 1, 0)

        sound_layout.addWidget(QLabel("Ses Seviyesi:"), 1, 1)
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(pomo_cfg.get("volume", 85))
        self.vol_slider.valueChanged.connect(self.save_sound_settings)
        sound_layout.addWidget(self.vol_slider, 1, 2)

        dur_layout = QHBoxLayout()
        dur_layout.addWidget(QLabel("Çalışma (dk):"))
        self.work_spin = QSpinBox()
        self.work_spin.setRange(1, 120)
        self.work_spin.setValue(self.engine.work_sec // 60)
        self.work_spin.valueChanged.connect(self.on_durations_changed)
        dur_layout.addWidget(self.work_spin, 1)

        dur_layout.addWidget(QLabel("Kısa Mola:"))
        self.short_spin = QSpinBox()
        self.short_spin.setRange(1, 60)
        self.short_spin.setValue(self.engine.short_break_sec // 60)
        self.short_spin.valueChanged.connect(self.on_durations_changed)
        dur_layout.addWidget(self.short_spin, 1)

        dur_layout.addWidget(QLabel("Uzun Mola:"))
        self.long_spin = QSpinBox()
        self.long_spin.setRange(1, 120)
        self.long_spin.setValue(self.engine.long_break_sec // 60)
        self.long_spin.valueChanged.connect(self.on_durations_changed)
        dur_layout.addWidget(self.long_spin, 1)

        sound_layout.addLayout(dur_layout, 2, 0, 1, 3)
        layout.addWidget(sound_gb)

        quick_note_frame = QFrame()
        qn_layout = QHBoxLayout(quick_note_frame)
        qn_layout.setContentsMargins(8, 6, 8, 6)

        self.qn_input = QLineEdit()
        self.qn_input.setPlaceholderText("Hızlı bir not yazın... (Notlar sekmesine kaydedilir)")
        self.qn_input.returnPressed.connect(self.add_quick_note)
        qn_layout.addWidget(self.qn_input, 3)

        self.qn_btn = ModernButton("+ Not Ekle", tooltip="Notlar Sekmesine Hızlı Not Ekle")
        self.qn_btn.setStyleSheet("background-color: #15803D; color: white; font-weight: bold;")
        self.qn_btn.clicked.connect(self.add_quick_note)
        qn_layout.addWidget(self.qn_btn, 1)

        layout.addWidget(quick_note_frame)
        layout.addStretch()
        self.refresh_task_combo()

    def refresh_task_combo(self):
        self.task_combo.blockSignals(True)
        self.task_combo.clear()
        self.task_combo.addItem("--- Bağımsız Pomodoro ---", None)
        active_id = db.data["settings"].get("pomodoro", {}).get("active_task_id")
        sel_idx = 0
        for idx, task in enumerate(db.data["tasks"]):
            if not task["completed"]:
                txt = f"[{task['priority']}] {task['title']} (Pomo: {task['pomodoro_sessions']})"
                self.task_combo.addItem(txt, task["id"])
                if task["id"] == active_id:
                    sel_idx = self.task_combo.count() - 1
        self.task_combo.setCurrentIndex(sel_idx)
        self.task_combo.blockSignals(False)

    def on_task_selected(self, index):
        task_id = self.task_combo.itemData(index)
        db.data["settings"]["pomodoro"]["active_task_id"] = task_id
        db.save()

    def add_quick_note(self):
        txt = self.qn_input.text().strip()
        if txt:
            db.add_keep_note("Pomodoro Notu", txt)
            self.qn_input.clear()
            if self.on_note_added_cb:
                self.on_note_added_cb()

    def save_sound_settings(self):
        pomo_cfg = db.data["settings"].get("pomodoro", {})
        pomo_cfg["sound_enabled"] = self.sound_check.isChecked()
        pomo_cfg["sound_work_end"] = self.work_sound_check.isChecked()
        pomo_cfg["sound_break_end"] = self.break_sound_check.isChecked()
        pomo_cfg["show_notification"] = self.notif_check.isChecked()
        pomo_cfg["volume"] = self.vol_slider.value()
        db.save()

    def on_durations_changed(self):
        w = self.work_spin.value()
        s = self.short_spin.value()
        l = self.long_spin.value()

        self.engine.work_sec = w * 60
        self.engine.short_break_sec = s * 60
        self.engine.long_break_sec = l * 60

        pomo_cfg = db.data["settings"].get("pomodoro", {})
        pomo_cfg["work_min"] = w
        pomo_cfg["short_break_min"] = s
        pomo_cfg["long_break_min"] = l
        db.save()

        if not self.engine.running:
            if self.engine.phase == "Çalışma":
                self.engine.remaining_seconds = self.engine.work_sec
            elif self.engine.phase == "Kısa Mola":
                self.engine.remaining_seconds = self.engine.short_break_sec
            else:
                self.engine.remaining_seconds = self.engine.long_break_sec
            self.engine.tick_signal.emit()

    def trigger_enter(self):
        self.engine.start_or_pause()

    def update_display(self):
        mins, secs = divmod(self.engine.remaining_seconds, 60)
        self.time_label.setText(f"{int(mins):02d}:{int(secs):02d}")
        self.phase_label.setText(self.engine.phase)

        if self.engine.phase == "Çalışma":
            total = self.engine.work_sec
            color = "#10B981"
        elif self.engine.phase == "Kısa Mola":
            total = self.engine.short_break_sec
            color = "#3B82F6"
        else:
            total = self.engine.long_break_sec
            color = "#F59E0B"
            
        self.time_label.setStyleSheet(f"color: {color}; border: none;")
        self.progress.setMaximum(max(1, total))
        self.progress.setValue(int(total - self.engine.remaining_seconds))

class TaskPlannerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        input_frame = QFrame()
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 8, 8, 8)

        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Yeni görev tanımı yazın...")
        self.task_input.returnPressed.connect(self.add_task)
        input_layout.addWidget(self.task_input, 3)

        self.prio_combo = QComboBox()
        self.prio_combo.addItems(["Yüksek", "Orta", "Düşük"])
        self.prio_combo.setCurrentIndex(1)
        input_layout.addWidget(self.prio_combo, 1)

        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("Tarih (YYYY-AA-GG)")
        self.date_input.setText(get_now().strftime("%Y-%m-%d"))
        self.date_input.setMinimumWidth(100)
        input_layout.addWidget(self.date_input, 1)

        self.time_input = QLineEdit()
        self.time_input.setPlaceholderText("Saat (SS:DD)")
        self.time_input.setMinimumWidth(80)
        input_layout.addWidget(self.time_input, 1)

        self.add_btn = ModernButton("+ Ekle", tooltip="Yeni Görev Ekle")
        self.add_btn.setStyleSheet("background-color: #15803D; color: white; font-weight: bold;")
        self.add_btn.clicked.connect(self.add_task)
        input_layout.addWidget(self.add_btn, 1)

        layout.addWidget(input_frame)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Durum", "Öncelik", "Görev Başlığı", "Tarih/Saat", "Pomodoro", "İşlem"])
        
        # Configure table column resizing properly
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 75)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout.addWidget(self.table)
        self.refresh_tasks()

    def add_task(self):
        title = self.task_input.text().strip()
        if not title:
            return
        prio_map = {0: "Yüksek", 1: "Orta", 2: "Düşük"}
        prio = prio_map[self.prio_combo.currentIndex()]
        d_str = self.date_input.text().strip()
        t_str = self.time_input.text().strip()

        db.add_task(title, prio, d_str, t_str)
        self.task_input.clear()
        self.refresh_tasks()

    def refresh_tasks(self):
        self.table.setRowCount(0)
        prio_icon = {"Yüksek": "[!]", "Orta": "[-]", "Düşük": "[o]"}

        for task in db.data["tasks"]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 36)

            chk = QCheckBox()
            chk.setChecked(task["completed"])
            chk.toggled.connect(lambda _, tid=task["id"]: self.toggle_task(tid))
            chk_widget = QWidget()
            l = QHBoxLayout(chk_widget)
            l.addWidget(chk)
            l.setAlignment(Qt.AlignCenter)
            l.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, chk_widget)

            p_item = QTableWidgetItem(f"{prio_icon.get(task['priority'], '')} {task['priority']}")
            p_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, p_item)

            t_item = QTableWidgetItem(task["title"])
            if task["completed"]:
                font = t_item.font()
                font.setStrikeOut(True)
                t_item.setFont(font)
                t_item.setForeground(QColor("#64748B"))
            self.table.setItem(row, 2, t_item)

            dt_str = f"{task['date']} {task['time']}".strip()
            dt_item = QTableWidgetItem(dt_str if dt_str else "-")
            dt_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, dt_item)

            pomo_item = QTableWidgetItem(f"Pomo: {task['pomodoro_sessions']}")
            pomo_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, pomo_item)

            # Compact, well-proportioned delete button inside table cell
            btn_container = QWidget()
            btn_lay = QHBoxLayout(btn_container)
            btn_lay.setContentsMargins(2, 2, 2, 2)
            btn_lay.setAlignment(Qt.AlignCenter)

            del_btn = QPushButton("Sil")
            del_btn.setFixedSize(55, 26)
            del_btn.setToolTip("Görevi Sil")
            del_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5C2328;
                    color: #F87171;
                    border: 1px solid #7F1D1D;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #7F1D1D;
                    color: #FFFFFF;
                }
                QPushButton:pressed {
                    background-color: #451A1D;
                }
            """)
            del_btn.clicked.connect(lambda _, tid=task["id"]: self.delete_task(tid))
            btn_lay.addWidget(del_btn)
            self.table.setCellWidget(row, 5, btn_container)

    def toggle_task(self, task_id):
        db.toggle_task(task_id)
        self.refresh_tasks()

    def delete_task(self, task_id):
        db.delete_task(task_id)
        self.refresh_tasks()

    def update_display(self):
        pass

class KeepNoteDialog(QDialog):
    def __init__(self, title="", text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Not Düzenle")
        self.setMinimumSize(420, 320)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Başlık:"))
        self.title_in = QLineEdit(title)
        layout.addWidget(self.title_in)

        layout.addWidget(QLabel("Not Metni:"))
        self.text_in = QTextEdit()
        self.text_in.setPlainText(text)
        layout.addWidget(self.text_in)

        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Save).setText("Kaydet")
        btn_box.button(QDialogButtonBox.Cancel).setText("İptal")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def get_data(self):
        return self.title_in.text(), self.text_in.toPlainText()

class NotesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        top_bar = QFrame()
        top_layout = QHBoxLayout(top_bar)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Notlarda ara...")
        self.search_input.textChanged.connect(self.refresh_notes)
        top_layout.addWidget(self.search_input, 3)

        self.add_btn = ModernButton("+ Yeni Not Ekle", tooltip="Yeni Not Oluştur")
        self.add_btn.setStyleSheet("background-color: #15803D; color: white; font-weight: bold;")
        self.add_btn.clicked.connect(self.open_add_dialog)
        top_layout.addWidget(self.add_btn, 1)

        layout.addWidget(top_bar)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget::item { margin: 4px; border-radius: 8px; }")
        self.list_widget.itemDoubleClicked.connect(self.open_edit_dialog)
        layout.addWidget(self.list_widget)

        self.refresh_notes()

    def open_add_dialog(self):
        dlg = KeepNoteDialog("", "", self)
        if dlg.exec_() == QDialog.Accepted:
            t, txt = dlg.get_data()
            if t or txt:
                db.add_keep_note(t if t else "Başlıksız Not", txt)
                self.refresh_notes()

    def open_edit_dialog(self, item):
        note_id = item.data(Qt.UserRole)
        note = next((n for n in db.data["keep_notes"] if n["id"] == note_id), None)
        if not note: return

        dlg = KeepNoteDialog(note["title"], note["text"], self)
        if dlg.exec_() == QDialog.Accepted:
            t, txt = dlg.get_data()
            db.update_keep_note(note_id, t, txt)
            self.refresh_notes()

    def refresh_notes(self):
        self.list_widget.clear()
        query = self.search_input.text().lower()

        colors = ["#1E222A", "#1A1D24"]

        for idx, note in enumerate(db.data["keep_notes"]):
            if query and query not in note["title"].lower() and query not in note["text"].lower():
                continue

            card = QFrame()
            bg_color = colors[idx % 2]
            card.setStyleSheet(f"QFrame {{ background-color: {bg_color}; border: 1px solid #2D333F; border-radius: 8px; padding: 8px; }}")

            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(6)
            card_layout.setContentsMargins(10, 8, 10, 8)

            header_layout = QHBoxLayout()
            title_lbl = QLabel(f"[Not] {note['title']}")
            title_lbl.setStyleSheet("font-weight: bold; color: #38BDF8; border: none;")
            title_font = QFont()
            title_font.setPointSize(11)
            title_lbl.setFont(title_font)
            header_layout.addWidget(title_lbl, 1)

            date_lbl = QLabel(note["date"])
            date_lbl.setStyleSheet("color: #64748B; border: none;")
            header_layout.addWidget(date_lbl)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(26, 26)
            del_btn.setToolTip("Notu Sil")
            del_btn.setStyleSheet("background: transparent; color: #F87171; font-weight: bold; border: none;")
            del_btn.clicked.connect(lambda _, nid=note["id"]: self.delete_note(nid))
            header_layout.addWidget(del_btn)

            card_layout.addLayout(header_layout)

            # Fix cut-off notes: properly display wrapped text with ample dynamic spacing
            raw_text = note["text"] if note["text"] else "(Boş not)"
            text_lbl = QLabel(raw_text)
            text_lbl.setWordWrap(True)
            text_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            text_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
            text_lbl.setStyleSheet("color: #CBD5E1; border: none; line-height: 1.3;")
            card_layout.addWidget(text_lbl)

            card.adjustSize()
            
            item = QListWidgetItem()
            # Calculate dynamic height so text is never cut off
            calculated_height = max(80, card.sizeHint().height() + 12)
            item.setSizeHint(QSize(self.list_widget.width() - 20, calculated_height))
            item.setData(Qt.UserRole, note["id"])

            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, card)

    def delete_note(self, note_id):
        db.delete_keep_note(note_id)
        self.refresh_notes()

    def update_display(self):
        pass

class NormalCalendarWidget(QWidget):
    def __init__(self):
        super().__init__()
        now = get_now()
        self.view_year = now.year
        self.view_month = now.month
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        clock_frame = QFrame()
        clock_layout = QVBoxLayout(clock_frame)
        self.digital_clock = QLabel("00:00:00")
        self.digital_clock.setAlignment(Qt.AlignCenter)
        c_font = QFont()
        c_font.setPointSize(28)
        c_font.setBold(True)
        self.digital_clock.setFont(c_font)
        self.digital_clock.setStyleSheet("color: #F8FAFC; border: none;")
        clock_layout.addWidget(self.digital_clock)

        half_layout = QHBoxLayout()
        self.first_half_bar = QProgressBar()
        self.first_half_bar.setFormat("İlk 12 Saat %p%")
        half_layout.addWidget(self.first_half_bar, 1)
        
        self.second_half_bar = QProgressBar()
        self.second_half_bar.setFormat("Son 12 Saat %p%")
        half_layout.addWidget(self.second_half_bar, 1)
        clock_layout.addLayout(half_layout)
        layout.addWidget(clock_frame)

        nav_frame = QFrame()
        nav_layout = QHBoxLayout(nav_frame)

        self.btn_prev = ModernButton("◀ Önceki Ay", tooltip="Bir Önceki Aya Git")
        self.btn_prev.clicked.connect(self.prev_month)
        nav_layout.addWidget(self.btn_prev, 1)

        self.header_label = QLabel()
        self.header_label.setAlignment(Qt.AlignCenter)
        h_font = QFont()
        h_font.setPointSize(14)
        h_font.setBold(True)
        self.header_label.setFont(h_font)
        self.header_label.setStyleSheet("color: #F8FAFC;")
        nav_layout.addWidget(self.header_label, 2)

        self.btn_today = ModernButton("Bugün", tooltip="Bugünün Tarihine Git")
        self.btn_today.clicked.connect(self.go_today)
        nav_layout.addWidget(self.btn_today, 1)

        self.btn_next = ModernButton("Sonraki Ay ▶", tooltip="Bir Sonraki Aya Git")
        self.btn_next.clicked.connect(self.next_month)
        nav_layout.addWidget(self.btn_next, 1)

        layout.addWidget(nav_frame)

        self.table = QTableWidget(6, 7)
        headers = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        for col, col_name in enumerate(headers):
            hdr_item = QTableWidgetItem(col_name)
            if col in (5, 6):
                hdr_item.setForeground(QColor("#F87171"))
                font = QFont()
                font.setBold(True)
                hdr_item.setFont(font)
            else:
                hdr_item.setForeground(QColor("#CBD5E1"))
            self.table.setHorizontalHeaderItem(col, hdr_item)

        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellClicked.connect(self.cell_clicked)

        layout.addWidget(self.table)
        self.render_month()

    def prev_month(self):
        self.view_month -= 1
        if self.view_month < 1:
            self.view_month = 12
            self.view_year -= 1
        self.render_month()

    def next_month(self):
        self.view_month += 1
        if self.view_month > 12:
            self.view_month = 1
            self.view_year += 1
        self.render_month()

    def go_today(self):
        now = get_now()
        self.view_year = now.year
        self.view_month = now.month
        self.render_month()

    def render_month(self):
        m_name = QLocale(QLocale.Turkish).monthName(self.view_month)
        self.header_label.setText(f"{m_name.capitalize()} {self.view_year}")

        cal = calendar.monthcalendar(self.view_year, self.view_month)
        self.table.clearContents()

        now = get_now()

        for r in range(6):
            week = cal[r] if r < len(cal) else [0]*7
            for c in range(7):
                day = week[c]
                if day != 0:
                    item = QTableWidgetItem(str(day))
                    item.setTextAlignment(Qt.AlignCenter)
                    
                    d_str = f"{self.view_year}-{self.view_month:02d}-{day:02d}"
                    has_task = any(t["date"] == d_str for t in db.data["tasks"])
                    
                    if self.view_year == now.year and self.view_month == now.month and day == now.day:
                        item.setBackground(QColor("#2563EB"))
                        item.setForeground(QColor("white"))
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                    elif has_task:
                        item.setBackground(QColor("#1E3A8A"))
                        item.setForeground(QColor("white"))
                    elif c in (5, 6):
                        item.setForeground(QColor("#F87171"))
                    else:
                        item.setForeground(QColor("#F8FAFC"))

                    self.table.setItem(r, c, item)

    def cell_clicked(self, row, col):
        item = self.table.item(row, col)
        if item and item.text():
            day = int(item.text())
            d_str = f"{self.view_year}-{self.view_month:02d}-{day:02d}"
            tasks = [t for t in db.data["tasks"] if t["date"] == d_str]
            msg = f"{day} {QLocale(QLocale.Turkish).monthName(self.view_month)} {self.view_year}\n\n"
            if tasks:
                msg += "Görevler:\n" + "\n".join([f"- [{t['priority']}] {t['title']}" for t in tasks])
            else:
                msg += "Bu tarihe ait görev yok."
            QMessageBox.information(self, "Gün Detayı", msg)

    def update_display(self):
        now = get_now()
        self.digital_clock.setText(now.strftime("%H:%M:%S"))
        hour, minute = now.hour, now.minute
        if hour < 12:
            v1 = int(((hour * 60) + minute) / 720 * 100)
            v2 = 0
        else:
            v1 = 100
            v2 = int((((hour - 12) * 60) + minute) / 720 * 100)
        self.first_half_bar.setValue(v1)
        self.second_half_bar.setValue(v2)

class NumericCalendarWidget(QWidget):
    def __init__(self):
        super().__init__()
        now = get_now()
        self.view_year = now.year
        self.view_month = now.month
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        clock_frame = QFrame()
        clock_layout = QVBoxLayout(clock_frame)
        self.digital_clock = QLabel("00:00:00")
        self.digital_clock.setAlignment(Qt.AlignCenter)
        c_font = QFont()
        c_font.setPointSize(28)
        c_font.setBold(True)
        self.digital_clock.setFont(c_font)
        self.digital_clock.setStyleSheet("color: #F8FAFC; border:none;")
        clock_layout.addWidget(self.digital_clock)
        layout.addWidget(clock_frame)

        nav_frame = QFrame()
        nav_layout = QHBoxLayout(nav_frame)

        self.btn_prev = ModernButton("◀ Önceki Ay", tooltip="Bir Önceki Aya Git")
        self.btn_prev.clicked.connect(self.prev_month)
        nav_layout.addWidget(self.btn_prev, 1)

        self.month_year_label = QLabel()
        self.month_year_label.setAlignment(Qt.AlignCenter)
        h_font = QFont()
        h_font.setPointSize(14)
        h_font.setBold(True)
        self.month_year_label.setFont(h_font)
        self.month_year_label.setStyleSheet("color: #F8FAFC;")
        nav_layout.addWidget(self.month_year_label, 2)

        self.btn_today = ModernButton("Bugün", tooltip="Bugünün Tarihine Git")
        self.btn_today.clicked.connect(self.go_today)
        nav_layout.addWidget(self.btn_today, 1)

        self.btn_next = ModernButton("Sonraki Ay ▶", tooltip="Bir Sonraki Aya Git")
        self.btn_next.clicked.connect(self.next_month)
        nav_layout.addWidget(self.btn_next, 1)

        layout.addWidget(nav_frame)

        self.table = QTableWidget(6, 7)
        for col, col_name in enumerate(["1", "2", "3", "4", "5", "6", "7"]):
            hdr_item = QTableWidgetItem(col_name)
            if col in (5, 6):
                hdr_item.setForeground(QColor("#F87171"))
                font = QFont()
                font.setBold(True)
                hdr_item.setFont(font)
            else:
                hdr_item.setForeground(QColor("#CBD5E1"))
            self.table.setHorizontalHeaderItem(col, hdr_item)

        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        self.render_month()

    def prev_month(self):
        self.view_month -= 1
        if self.view_month < 1:
            self.view_month = 12
            self.view_year -= 1
        self.render_month()

    def next_month(self):
        self.view_month += 1
        if self.view_month > 12:
            self.view_month = 1
            self.view_year += 1
        self.render_month()

    def go_today(self):
        now = get_now()
        self.view_year = now.year
        self.view_month = now.month
        self.render_month()

    def render_month(self):
        self.month_year_label.setText(f"Ay {self.view_month}, Yıl {self.view_year}")
        cal = calendar.monthcalendar(self.view_year, self.view_month)
        self.table.clearContents()
        now = get_now()

        for r in range(6):
            week = cal[r] if r < len(cal) else [0]*7
            for c in range(7):
                day = week[c]
                if day != 0:
                    item = QTableWidgetItem(str(day))
                    item.setTextAlignment(Qt.AlignCenter)
                    if self.view_year == now.year and self.view_month == now.month and day == now.day:
                        item.setBackground(QColor("#2563EB"))
                        item.setForeground(QColor("white"))
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                    elif c in (5, 6):
                        item.setForeground(QColor("#F87171"))
                    else:
                        item.setForeground(QColor("#F8FAFC"))
                    self.table.setItem(r, c, item)

    def update_display(self):
        now = get_now()
        self.digital_clock.setText(now.strftime("%H:%M:%S"))

class OctalCalendarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.show_seconds = db.data["settings"].get("mod3_show_seconds", False)
        self.seg1_start = db.data["settings"].get("mod3_seg1", 0)
        self.seg2_start = db.data["settings"].get("mod3_seg2", 8)
        self.seg3_start = db.data["settings"].get("mod3_seg3", 11)
        
        self.view_year = get_now().year
        self.view_month = self.get_current_octal_month()
        self.init_ui()

    def get_current_octal_month(self):
        now = get_now()
        doy = now.timetuple().tm_yday
        return min(((doy - 1) // 40) + 1, 9)

    def save_segments(self):
        self.seg1_start = self.spin_seg1.value()
        self.seg2_start = self.spin_seg2.value()
        self.seg3_start = self.spin_seg3.value()
        db.data["settings"]["mod3_seg1"] = self.seg1_start
        db.data["settings"]["mod3_seg2"] = self.seg2_start
        db.data["settings"]["mod3_seg3"] = self.seg3_start
        db.save()

    def init_ui(self):
        layout = QVBoxLayout(self)

        clock_frame = QFrame()
        clock_layout = QVBoxLayout(clock_frame)
        self.small_clock = QLabel("00:00:00")
        self.small_clock.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.small_clock.setStyleSheet("color: #94A3B8; border: none;")
        clock_layout.addWidget(self.small_clock)

        self.segment_label = QLabel("1. Bölüm - 0:00")
        self.segment_label.setAlignment(Qt.AlignCenter)
        s_font = QFont()
        s_font.setPointSize(28)
        s_font.setBold(True)
        self.segment_label.setFont(s_font)
        self.segment_label.setStyleSheet("color: #10B981; border: none;")
        clock_layout.addWidget(self.segment_label)

        self.sec_check = QCheckBox("Saniyeyi Göster")
        self.sec_check.setChecked(self.show_seconds)
        self.sec_check.toggled.connect(self.toggle_seconds)
        clock_layout.addWidget(self.sec_check, 0, Qt.AlignHCenter)
        layout.addWidget(clock_frame)

        seg_settings_frame = QFrame()
        seg_layout = QHBoxLayout(seg_settings_frame)
        seg_layout.addWidget(QLabel("1. Bölüm:"))
        self.spin_seg1 = QSpinBox()
        self.spin_seg1.setRange(0, 23)
        self.spin_seg1.setValue(self.seg1_start)
        self.spin_seg1.valueChanged.connect(self.save_segments)
        seg_layout.addWidget(self.spin_seg1, 1)
        
        seg_layout.addWidget(QLabel("2. Bölüm:"))
        self.spin_seg2 = QSpinBox()
        self.spin_seg2.setRange(0, 23)
        self.spin_seg2.setValue(self.seg2_start)
        self.spin_seg2.valueChanged.connect(self.save_segments)
        seg_layout.addWidget(self.spin_seg2, 1)

        seg_layout.addWidget(QLabel("3. Bölüm:"))
        self.spin_seg3 = QSpinBox()
        self.spin_seg3.setRange(0, 23)
        self.spin_seg3.setValue(self.seg3_start)
        self.spin_seg3.valueChanged.connect(self.save_segments)
        seg_layout.addWidget(self.spin_seg3, 1)
        layout.addWidget(seg_settings_frame)

        nav_frame = QFrame()
        nav_layout = QHBoxLayout(nav_frame)
        
        self.btn_prev = ModernButton("◀ Önceki Ay", tooltip="Bir Önceki Sekizli Aya Git")
        self.btn_prev.clicked.connect(self.prev_month)
        nav_layout.addWidget(self.btn_prev, 1)
        
        self.month_info_label = QLabel()
        self.month_info_label.setAlignment(Qt.AlignCenter)
        h_font = QFont()
        h_font.setPointSize(14)
        h_font.setBold(True)
        self.month_info_label.setFont(h_font)
        self.month_info_label.setStyleSheet("color: #F8FAFC;")
        nav_layout.addWidget(self.month_info_label, 2)

        self.btn_today = ModernButton("Bugün", tooltip="Bugünün Tarihine Git")
        self.btn_today.clicked.connect(self.go_today)
        nav_layout.addWidget(self.btn_today, 1)
        
        self.btn_next = ModernButton("Sonraki Ay ▶", tooltip="Bir Sonraki Sekizli Aya Git")
        self.btn_next.clicked.connect(self.next_month)
        nav_layout.addWidget(self.btn_next, 1)
        layout.addWidget(nav_frame)

        self.grid_table = QTableWidget(5, 8)
        for col, col_name in enumerate([f"{i+1}" for i in range(8)]):
            hdr_item = QTableWidgetItem(col_name)
            if col in (5, 6, 7):
                hdr_item.setForeground(QColor("#F87171"))
                font = QFont()
                font.setBold(True)
                hdr_item.setFont(font)
            else:
                hdr_item.setForeground(QColor("#CBD5E1"))
            self.grid_table.setHorizontalHeaderItem(col, hdr_item)

        self.grid_table.setVerticalHeaderLabels([f"{i+1}" for i in range(5)])
        self.grid_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.grid_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.grid_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.grid_table)
        self.update_calendar_grid()

    def toggle_seconds(self, checked):
        self.show_seconds = checked
        db.data["settings"]["mod3_show_seconds"] = checked
        db.save()

    def prev_month(self):
        self.view_month -= 1
        if self.view_month < 1:
            self.view_month = 9
            self.view_year -= 1
        self.update_calendar_grid()

    def next_month(self):
        self.view_month += 1
        if self.view_month > 9:
            self.view_month = 1
            self.view_year += 1
        self.update_calendar_grid()

    def go_today(self):
        self.view_year = get_now().year
        self.view_month = self.get_current_octal_month()
        self.update_calendar_grid()

    def update_calendar_grid(self):
        self.month_info_label.setText(f"Sekizli Ay: {self.view_month}, Yıl: {self.view_year}")
        days_in_year = 366 if calendar.isleap(self.view_year) else 365
        days_in_this_month = 40 if self.view_month < 9 else days_in_year - 320

        self.grid_table.clearContents()
        required_rows = (days_in_this_month + 7) // 8
        self.grid_table.setRowCount(required_rows)
        self.grid_table.setVerticalHeaderLabels([f"{i+1}" for i in range(required_rows)])

        now = get_now()
        current_doy = now.timetuple().tm_yday
        current_oct_month = self.get_current_octal_month()
        current_oct_day = ((current_doy - 1) % 40) + 1 if current_oct_month < 9 else current_doy - 320

        for r in range(required_rows):
            for c in range(8):
                gun_no = (r * 8) + c + 1
                if gun_no <= days_in_this_month:
                    item = QTableWidgetItem(str(gun_no))
                    item.setTextAlignment(Qt.AlignCenter)
                    if self.view_year == now.year and self.view_month == current_oct_month and gun_no == current_oct_day:
                        item.setBackground(QColor("#2563EB"))
                        item.setForeground(QColor("white"))
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                    elif c in (5, 6, 7) or r >= 5:
                        item.setForeground(QColor("#F87171"))
                    else:
                        item.setForeground(QColor("#F8FAFC"))
                    self.grid_table.setItem(r, c, item)

    def update_display(self):
        now = get_now()
        self.small_clock.setText(now.strftime("%H:%M:%S"))
        hour, minute, second = now.hour, now.minute, now.second

        times = [(self.seg1_start, 1), (self.seg2_start, 2), (self.seg3_start, 3)]
        times.sort(reverse=True)
        current_seg, seg_start_hour = times[-1][1], times[-1][0]
        
        for start_h, seg_idx in times:
            if hour >= start_h:
                current_seg, seg_start_hour = seg_idx, start_h
                break

        seg_hour = (hour - seg_start_hour) % 24
        seg_time_str = f"{current_seg}. Bölüm  |  {seg_hour}:{minute:02d}"
        if self.show_seconds: seg_time_str += f":{second:02d}"
        self.segment_label.setText(seg_time_str)

class LifeCountdownWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.target_ts = self.load_target()
        self.init_ui()

    def load_target(self):
        val = db.data["settings"].get("life_target_ts")
        if val:
            try: return datetime.fromisoformat(val)
            except ValueError: pass
        return None

    def save_target(self):
        db.data["settings"]["life_target_ts"] = self.target_ts.isoformat() if self.target_ts else None
        db.save()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        display_frame = QFrame()
        disp_layout = QVBoxLayout(display_frame)

        self.sec_label = QLabel("0 Saniye")
        self.sec_label.setAlignment(Qt.AlignCenter)
        f1 = QFont(); f1.setPointSize(20); f1.setBold(True)
        self.sec_label.setFont(f1)
        self.sec_label.setStyleSheet("color: #94A3B8; border: none;")
        disp_layout.addWidget(self.sec_label)

        self.min_label = QLabel("0 Dakika")
        self.min_label.setAlignment(Qt.AlignCenter)
        f2 = QFont(); f2.setPointSize(26); f2.setBold(True)
        self.min_label.setFont(f2)
        self.min_label.setStyleSheet("color: #CBD5E1; border: none;")
        disp_layout.addWidget(self.min_label)

        self.hour_label = QLabel("0 Saat")
        self.hour_label.setAlignment(Qt.AlignCenter)
        f3 = QFont(); f3.setPointSize(32); f3.setBold(True)
        self.hour_label.setFont(f3)
        self.hour_label.setStyleSheet("color: #F8FAFC; border: none;")
        disp_layout.addWidget(self.hour_label)

        self.day_label = QLabel("0 Gün")
        self.day_label.setAlignment(Qt.AlignCenter)
        f4 = QFont(); f4.setPointSize(40); f4.setBold(True)
        self.day_label.setFont(f4)
        self.day_label.setStyleSheet("color: #38BDF8; border: none;")
        disp_layout.addWidget(self.day_label)

        layout.addWidget(display_frame)

        cfg_frame = QFrame()
        cfg_layout = QHBoxLayout(cfg_frame)
        cfg_layout.addWidget(QLabel("Ömür Hedefi (Yıl):"))
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1, 1000)
        self.year_spin.setValue(40)
        cfg_layout.addWidget(self.year_spin, 1)
        
        self.set_btn = ModernButton("▶ Sayaç Başlat", tooltip="Belirtilen Yıla Göre Geri Sayımı Başlat")
        self.set_btn.setStyleSheet("background-color: #1E3A8A; color: white; font-weight: bold;")
        self.set_btn.clicked.connect(self.start_countdown)
        cfg_layout.addWidget(self.set_btn, 1)
        layout.addWidget(cfg_frame)
        layout.addStretch()

    def start_countdown(self):
        years = self.year_spin.value()
        self.target_ts = get_now() + timedelta(days=years * 365.25)
        self.save_target()
        self.update_display()

    def update_display(self):
        if not self.target_ts: return
        delta = self.target_ts - get_now()
        if delta.total_seconds() <= 0: return

        total_secs = delta.total_seconds()
        self.sec_label.setText(f"{format_sayi(total_secs)} Saniye")
        self.min_label.setText(f"{format_sayi(total_secs / 60)} Dakika")
        self.hour_label.setText(f"{format_sayi(total_secs / 3600)} Saat")
        self.day_label.setText(f"{format_sayi(total_secs / 86400)} Gün")

class DateSettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        info_frame = QFrame()
        info_layout = QVBoxLayout(info_frame)
        lbl_title = QLabel("Tarih ve Saat Referans Ayarı")
        lbl_title.setStyleSheet("font-weight: bold; color: #38BDF8; border: none;")
        f = QFont(); f.setPointSize(14)
        lbl_title.setFont(f)
        info_layout.addWidget(lbl_title)

        lbl_desc = QLabel("Belirleyeceğiniz tarih/saat referans alınarak tüm modlar senkronize çalışır.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lbl_desc.setStyleSheet("color: #CBD5E1; border: none;")
        info_layout.addWidget(lbl_desc)
        layout.addWidget(info_frame)

        input_frame = QFrame()
        input_layout = QGridLayout(input_frame)
        now = get_now()

        input_layout.addWidget(QLabel("Yıl:"), 0, 0)
        self.spin_year = QSpinBox()
        self.spin_year.setRange(1900, 2100)
        self.spin_year.setValue(now.year)
        input_layout.addWidget(self.spin_year, 0, 1)

        input_layout.addWidget(QLabel("Ay:"), 0, 2)
        self.spin_month = QSpinBox()
        self.spin_month.setRange(1, 12)
        self.spin_month.setValue(now.month)
        input_layout.addWidget(self.spin_month, 0, 3)

        input_layout.addWidget(QLabel("Gün:"), 0, 4)
        self.spin_day = QSpinBox()
        self.spin_day.setRange(1, 31)
        self.spin_day.setValue(now.day)
        input_layout.addWidget(self.spin_day, 0, 5)

        input_layout.addWidget(QLabel("Saat:"), 1, 0)
        self.spin_hour = QSpinBox()
        self.spin_hour.setRange(0, 23)
        self.spin_hour.setValue(now.hour)
        input_layout.addWidget(self.spin_hour, 1, 1)

        input_layout.addWidget(QLabel("Dakika:"), 1, 2)
        self.spin_minute = QSpinBox()
        self.spin_minute.setRange(0, 59)
        self.spin_minute.setValue(now.minute)
        input_layout.addWidget(self.spin_minute, 1, 3)

        input_layout.addWidget(QLabel("Saniye:"), 1, 4)
        self.spin_second = QSpinBox()
        self.spin_second.setRange(0, 59)
        self.spin_second.setValue(now.second)
        input_layout.addWidget(self.spin_second, 1, 5)
        layout.addWidget(input_frame)

        btn_layout = QHBoxLayout()
        self.btn_update = ModernButton("Referans Zamanı Güncelle", tooltip="Girilen Saati Tüm Modlar İçin Geçerli Kıl")
        self.btn_update.setStyleSheet("background-color: #15803D; color: #ffffff; font-weight: bold;")
        self.btn_update.clicked.connect(self.apply_custom_time)
        btn_layout.addWidget(self.btn_update, 1)

        self.btn_reset = ModernButton("Sistem Zamanına Sıfırla", tooltip="Gerçek Sistem Saatine Dön")
        self.btn_reset.setStyleSheet("background-color: #991B1B; color: #ffffff; font-weight: bold;")
        self.btn_reset.clicked.connect(self.reset_to_system_time)
        btn_layout.addWidget(self.btn_reset, 1)
        layout.addLayout(btn_layout)

        disp_frame = QFrame()
        disp_lay = QVBoxLayout(disp_frame)
        self.lbl_real_time = QLabel()
        self.lbl_app_time = QLabel()
        disp_lay.addWidget(self.lbl_real_time)
        disp_lay.addWidget(self.lbl_app_time)
        layout.addWidget(disp_frame)
        layout.addStretch()

    def apply_custom_time(self):
        try:
            target_dt = datetime(
                self.spin_year.value(), self.spin_month.value(), self.spin_day.value(),
                self.spin_hour.value(), self.spin_minute.value(), self.spin_second.value()
            )
            db.data["settings"]["time_offset_seconds"] = (target_dt - datetime.now()).total_seconds()
            db.save()
            QMessageBox.information(self, "Başarılı", "Referans saat güncellendi!")
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def reset_to_system_time(self):
        db.data["settings"]["time_offset_seconds"] = 0
        db.save()

    def update_display(self):
        real_now = datetime.now()
        app_now = get_now()
        self.lbl_real_time.setText(f"Bilgisayar Saati: {real_now.strftime('%d.%m.%Y %H:%M:%S')}")
        self.lbl_app_time.setText(f"Referans Saati: {app_now.strftime('%d.%m.%Y %H:%M:%S')}")

class ScreenSettingsWidget(QWidget):
    """
    Ekran Ayarı & Mavi Işık Filtresi Modu
    - Referans saatine duyarlı kademeli / saatli filtreleme
    - CTM, Picom GLX Shader ve Gamma fallback mekanizmaları
    """
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    VERI_DIR = os.path.join(BASE_DIR, "veri")
    SHADER_FILE = os.path.join(VERI_DIR, "grayscale.glsl")

    def __init__(self):
        super().__init__()
        self.session_type = os.environ.get("XDG_SESSION_TYPE", "x11").lower()
        self.grayscale_method = None
        self._block_save = True
        self._displays_cache = None
        
        self._apply_timer = QTimer(self)
        self._apply_timer.setSingleShot(True)
        self._apply_timer.timeout.connect(self._apply_now)

        self.has_gammastep = self._has_cmd("gammastep")
        self.has_wlsunset = self._has_cmd("wlsunset")
        self.picom_was_running = self._check_picom()
        self.xfce_compositing_was_on = self._check_xfce_comp()
        self._original_cursor_theme = self._get_cursor_theme()

        self._build_ui()
        self._load_settings()
        self._block_save = False
        self._refresh_displays()
        self._apply_now()
        self.installEventFilter(self)

    def _has_cmd(self, cmd):
        try:
            subprocess.run(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except Exception:
            return False

    def _check_picom(self):
        try:
            subprocess.check_output(["pgrep", "-x", "picom"])
            return True
        except Exception:
            return False

    def _check_xfce_comp(self):
        try:
            o = subprocess.check_output(
                ["xfconf-query", "-c", "xfwm4", "-p", "/general/use_compositing"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            return o.lower() == "true"
        except Exception:
            return False

    def _get_cursor_theme(self):
        try:
            return subprocess.check_output(
                ["xfconf-query", "-c", "xsettings", "-p", "/Gtk/CursorThemeName"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except Exception:
            return ""

    def _refresh_displays(self):
        if self.session_type == "wayland":
            self._displays_cache = ["Wayland-Display"]
            return self._displays_cache
        try:
            out = subprocess.check_output("xrandr --current", shell=True, stderr=subprocess.DEVNULL).decode()
            self._displays_cache = [l.split()[0] for l in out.splitlines() if " connected" in l]
        except Exception:
            self._displays_cache = []
        return self._displays_cache

    def _connected_displays(self):
        if self._displays_cache is None:
            return self._refresh_displays()
        return self._displays_cache

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        clock_frame = QFrame()
        clock_box = QHBoxLayout(clock_frame)
        clock_box.setContentsMargins(12, 8, 12, 8)
        
        self.ref_clock_label = QLabel("Referans Saati: --:--:--")
        self.ref_clock_label.setStyleSheet("font-weight: bold; color: #38BDF8; border: none;")
        f = QFont(); f.setPointSize(11)
        self.ref_clock_label.setFont(f)
        clock_box.addWidget(self.ref_clock_label, 2)

        self.reset_button = ModernButton("↺ Sıfırla", tooltip="Ekran Ayarlarını Varsayılana Döndür")
        self.reset_button.setCursor(Qt.PointingHandCursor)
        self.reset_button.clicked.connect(self._reset)
        clock_box.addWidget(self.reset_button, 1)

        self.refresh_btn = ModernButton("⟳ Ekranları Yenile", tooltip="Bağlı Ekran Monitörlerini Tekrar Tara")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        clock_box.addWidget(self.refresh_btn, 1)

        self.autostart_button = ModernButton("⚙ Otomatik Başlat", tooltip="Sistem Açılışında Otomatik Çalıştır")
        self.autostart_button.setCheckable(True)
        autostart_path = os.path.expanduser("~/.config/autostart/kavram_blf.desktop")
        self.autostart_button.setChecked(os.path.exists(autostart_path))
        self.autostart_button.toggled.connect(self._on_autostart_toggled)
        clock_box.addWidget(self.autostart_button, 1)

        main_layout.addWidget(clock_frame)

        sg = QGroupBox("Sistem Durumu")
        sl = QVBoxLayout()
        self.status_label = QLabel("Durum: Aktif")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #10B981; font-weight: bold; border: none;")
        sl.addWidget(self.status_label)
        sg.setLayout(sl)
        main_layout.addWidget(sg)

        sched_group = QGroupBox("Zamanlı & Kademeli Filtreleme Ayarları")
        sched_layout = QGridLayout()
        sched_layout.setSpacing(10)

        sched_layout.addWidget(QLabel("Mavi Işık Modu:"), 0, 0)
        self.combo_blue_mode = QComboBox()
        self.combo_blue_mode.addItems(["Her Zaman", "Saat Aralığı", "Kademeli Otomatik"])
        self.combo_blue_mode.currentIndexChanged.connect(self._apply)
        sched_layout.addWidget(self.combo_blue_mode, 0, 1)

        sched_layout.addWidget(QLabel("Başlangıç Saati:"), 0, 2)
        self.spin_blue_start = QSpinBox()
        self.spin_blue_start.setRange(0, 23)
        self.spin_blue_start.setValue(20)
        self.spin_blue_start.valueChanged.connect(self._apply)
        sched_layout.addWidget(self.spin_blue_start, 0, 3)

        sched_layout.addWidget(QLabel("Bitiş Saati:"), 0, 4)
        self.spin_blue_end = QSpinBox()
        self.spin_blue_end.setRange(0, 23)
        self.spin_blue_end.setValue(7)
        self.spin_blue_end.valueChanged.connect(self._apply)
        sched_layout.addWidget(self.spin_blue_end, 0, 5)

        sched_layout.addWidget(QLabel("Gri Mod Çalışma:"), 1, 0)
        self.combo_gray_mode = QComboBox()
        self.combo_gray_mode.addItems(["Her Zaman", "Saat Aralığı"])
        self.combo_gray_mode.currentIndexChanged.connect(self._apply)
        sched_layout.addWidget(self.combo_gray_mode, 1, 1)

        sched_layout.addWidget(QLabel("Başlangıç Saati:"), 1, 2)
        self.spin_gray_start = QSpinBox()
        self.spin_gray_start.setRange(0, 23)
        self.spin_gray_start.setValue(22)
        self.spin_gray_start.valueChanged.connect(self._apply)
        sched_layout.addWidget(self.spin_gray_start, 1, 3)

        sched_layout.addWidget(QLabel("Bitiş Saati:"), 1, 4)
        self.spin_gray_end = QSpinBox()
        self.spin_gray_end.setRange(0, 23)
        self.spin_gray_end.setValue(6)
        self.spin_gray_end.valueChanged.connect(self._apply)
        sched_layout.addWidget(self.spin_gray_end, 1, 5)

        sched_group.setLayout(sched_layout)
        main_layout.addWidget(sched_group)

        bg = QGroupBox("Mavi Işık Filtresi (Hedef Seviye)")
        bv = QVBoxLayout()
        self.blue_filter_slider = self._make_row(
            bv, "Mavi Işık Filtre Şiddeti",
            "0–40: Hafif filtre | 40–80: Derin gece koruması | 80–100: Ultra sıcak okuma modu",
            0, 100, 0
        )
        bg.setLayout(bv)
        main_layout.addWidget(bg)

        cg = QGroupBox("RGB Renk Dengesi")
        cv = QVBoxLayout()
        self.red_slider = self._make_row(cv, "Kırmızı Kanalı", "Sıcaklığı artırır", 50, 160, 100)
        self.green_slider = self._make_row(cv, "Yeşil Kanalı", "Yeşil ton ayarı", 50, 160, 100)
        cg.setLayout(cv)
        main_layout.addWidget(cg)

        pg = QGroupBox("Parlaklık & Gama Karartma")
        pv = QVBoxLayout()
        self.brightness_slider = self._make_row(pv, "Ekran Parlaklığı", "Genel ekran ışık gücü", 20, 150, 100)
        self.darkness_slider = self._make_row(pv, "Gama Karartma", "Karanlık ortamlarda gözü korur", 0, 80, 0)
        pg.setLayout(pv)
        main_layout.addWidget(pg)

        bottom_bar = QHBoxLayout()
        self.reading_button = ModernButton("📖 Okuma Modu", tooltip="Hızlı Sıcak Okuma Tonu")
        self.reading_button.setCheckable(True)
        self.reading_button.toggled.connect(self._on_reading)
        
        self.gray_button = ModernButton("◐ Gri Mod (Grayscale)", tooltip="Ekranı Siyah Beyaz Yap")
        self.gray_button.setCheckable(True)
        self.gray_button.toggled.connect(self._apply)
        
        bottom_bar.addWidget(self.reading_button, 1)
        bottom_bar.addWidget(self.gray_button, 1)
        main_layout.addLayout(bottom_bar)

        shortcut_lbl = QLabel("Kısayol: Ekran bozulursa düzeltmek için Alt + V tuşlarına basın.")
        shortcut_lbl.setStyleSheet(HINT_STYLE)
        shortcut_lbl.setAlignment(Qt.AlignCenter)
        shortcut_lbl.setWordWrap(True)
        shortcut_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        main_layout.addWidget(shortcut_lbl)

    def _make_row(self, layout, name, hint_text, min_v=0, max_v=100, def_v=0):
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("color: #E2E8F0; font-weight: bold; border: none;")
        layout.addWidget(name_lbl)
        
        sld = QSlider(Qt.Horizontal)
        sld.setRange(min_v, max_v)
        sld.setValue(def_v)
        sld.valueChanged.connect(self._apply)
        layout.addWidget(sld)
        
        hint_lbl = QLabel(hint_text)
        hint_lbl.setStyleSheet(HINT_STYLE)
        hint_lbl.setWordWrap(True)
        hint_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(hint_lbl)
        return sld

    def _on_refresh_clicked(self):
        self._refresh_displays()
        self._apply_now()

    def _on_autostart_toggled(self, checked):
        autostart_dir = os.path.expanduser("~/.config/autostart")
        desktop_file = os.path.join(autostart_dir, "kavram_blf.desktop")
        if checked:
            os.makedirs(autostart_dir, exist_ok=True)
            script_path = os.path.abspath(__file__)
            content = f"""[Desktop Entry]
Type=Application
Exec={sys.executable} "{script_path}" --startupHidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Kavram Screen Manager
Comment=Applies custom screen color profile on login"""
            try:
                with open(desktop_file, "w") as f:
                    f.write(content)
                os.chmod(desktop_file, 0o755)
            except Exception as e:
                print("Autostart dosyası oluşturulamadı:", e)
        else:
            if os.path.exists(desktop_file):
                try: os.remove(desktop_file)
                except Exception: pass

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.modifiers() == Qt.AltModifier and event.key() == Qt.Key_V:
                self._reset()
                return True
        return super().eventFilter(obj, event)

    def _apply_ctm(self, displays, enable):
        gray_ctm = ("913110047,0,3071760610,0,310096639,0,"
                    "913110047,0,3071760610,0,310096639,0,"
                    "913110047,0,3071760610,0,310096639,0")
        id_ctm   = "0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1"
        for d in displays:
            try:
                subprocess.run(["xrandr", "--output", d, "--set", "CTM",
                                 gray_ctm if enable else id_ctm],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception: pass

    def _apply_shader(self, enable):
        os.makedirs(self.VERI_DIR, exist_ok=True)
        if enable:
            subprocess.call(["pkill", "picom"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.2)
            shader = """#version 330
in vec2 texcoord;
uniform sampler2D tex;
uniform float opacity;
vec4 default_post_processing(vec4 c);
vec4 window_shader() {
    vec2 sz = textureSize(tex, 0);
    vec4 c  = texture2D(tex, texcoord / sz, 0);
    float g = 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b;
    c = vec4(vec3(g) * opacity, c.a * opacity);
    return default_post_processing(c);
}"""
            with open(self.SHADER_FILE, "w") as f: f.write(shader)
            subprocess.Popen(
                ["picom", "--backend", "glx", "--window-shader-fg", self.SHADER_FILE, "--no-use-damage"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        else:
            subprocess.call(["pkill", "picom"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if self.picom_was_running:
                subprocess.Popen(["picom"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return False

    def _enable_gray(self):
        if self.grayscale_method: return
        displays = self._connected_displays()
        if not displays or self.session_type == "wayland":
            self.grayscale_method = "gamma"
            return
        try:
            verbose = subprocess.check_output(
                f"xrandr --output {displays[0]} --verbose", shell=True, stderr=subprocess.DEVNULL
            ).decode()
            if "CTM" in verbose:
                self._apply_ctm(displays, True)
                self.grayscale_method = "ctm"
            elif self._apply_shader(True):
                self.grayscale_method = "shader"
            else:
                self.grayscale_method = "gamma"
        except Exception:
            self.grayscale_method = "gamma"

    def _disable_gray(self):
        if self.grayscale_method == "ctm":
            self._apply_ctm(self._connected_displays(), False)
        elif self.grayscale_method == "shader":
            self._apply_shader(False)
        self.grayscale_method = None

    def _is_in_hours(self, start_h, end_h, current_h):
        if start_h <= end_h:
            return start_h <= current_h < end_h
        else:
            return current_h >= start_h or current_h < end_h

    def _calculate_effective_blue_level(self):
        target_val = self.blue_filter_slider.value()
        mode = self.combo_blue_mode.currentText()
        now = get_now()
        cur_h = now.hour

        if mode == "Her Zaman":
            return target_val
        elif mode == "Saat Aralığı":
            start_h = self.spin_blue_start.value()
            end_h = self.spin_blue_end.value()
            if self._is_in_hours(start_h, end_h, cur_h):
                return target_val
            return 0
        elif mode == "Kademeli Otomatik":
            start_h = self.spin_blue_start.value()
            end_h = self.spin_blue_end.value()
            if not self._is_in_hours(start_h, end_h, cur_h):
                return 0
            if start_h <= end_h:
                duration = max(1, end_h - start_h)
                elapsed = cur_h - start_h
            else:
                duration = max(1, (24 - start_h) + end_h)
                elapsed = (cur_h - start_h) if cur_h >= start_h else ((24 - start_h) + cur_h)
            factor = min(1.0, max(0.2, (elapsed + 1) / duration))
            return int(target_val * factor)
        return target_val

    def _apply(self):
        if self._block_save:
            return
        self._apply_timer.start(50)

    def _apply_now(self):
        now = get_now()
        self.ref_clock_label.setText(f"Referans Saati: {now.strftime('%H:%M:%S')}")

        is_gray = self.gray_button.isChecked()
        gray_mode = self.combo_gray_mode.currentText()
        cur_h = now.hour

        if is_gray and gray_mode == "Saat Aralığı":
            g_start = self.spin_gray_start.value()
            g_end = self.spin_gray_end.value()
            if not self._is_in_hours(g_start, g_end, cur_h):
                is_gray = False

        if is_gray:
            self._enable_gray()
        else:
            self._disable_gray()

        eff_blue = self._calculate_effective_blue_level()

        r_val = (self.red_slider.value() / 100.0)
        g_val = (self.green_slider.value() / 100.0)
        b_val = 1.0

        g_val -= (eff_blue * 0.003)
        b_val -= (eff_blue * 0.008)

        br_factor = (self.brightness_slider.value() / 100.0)
        dark_factor = 1.0 - (self.darkness_slider.value() / 100.0)
        effective_br = max(0.1, min(1.5, br_factor * dark_factor))

        if self.grayscale_method == "gamma" and is_gray:
            gray_lum = (0.299 * r_val) + (0.587 * g_val) + (0.114 * b_val)
            r_val = g_val = b_val = gray_lum

        r = max(0.1, min(1.0, r_val))
        g = max(0.1, min(1.0, g_val))
        b = max(0.1, min(1.0, b_val))

        displays = self._connected_displays()
        if self.session_type != "wayland" and displays:
            for d in displays:
                try:
                    subprocess.run(
                        ["xrandr", "--output", d, "--gamma", f"{r:.2f}:{g:.2f}:{b:.2f}", "--brightness", f"{effective_br:.2f}"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass

        if not self._block_save:
            self._save_settings()

    def _on_reading(self, checked):
        if checked:
            self.red_slider.setValue(110)
            self.green_slider.setValue(90)
            self.blue_filter_slider.setValue(60)
        else:
            self.red_slider.setValue(100)
            self.green_slider.setValue(100)
            self.blue_filter_slider.setValue(0)
        self._apply()

    def _reset(self):
        self._block_save = True
        self.combo_blue_mode.setCurrentIndex(0)
        self.spin_blue_start.setValue(20)
        self.spin_blue_end.setValue(7)
        self.combo_gray_mode.setCurrentIndex(0)
        self.spin_gray_start.setValue(22)
        self.spin_gray_end.setValue(6)
        self.blue_filter_slider.setValue(0)
        self.red_slider.setValue(100)
        self.green_slider.setValue(100)
        self.brightness_slider.setValue(100)
        self.darkness_slider.setValue(0)
        self.reading_button.setChecked(False)
        self.gray_button.setChecked(False)
        self._block_save = False

        displays = self._connected_displays()
        if self.session_type != "wayland" and displays:
            for d in displays:
                try:
                    subprocess.run(
                        ["xrandr", "--output", d, "--gamma", "1.0:1.0:1.0", "--brightness", "1.0"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass
        self._apply_now()

    def _save_settings(self):
        screen_data = db.data["settings"]["screen"]
        screen_data["blue_filter"] = self.blue_filter_slider.value()
        screen_data["brightness"] = self.brightness_slider.value()
        screen_data["darkness"] = self.darkness_slider.value()
        screen_data["red"] = self.red_slider.value()
        screen_data["green"] = self.green_slider.value()
        screen_data["gray"] = self.gray_button.isChecked()
        screen_data["reading"] = self.reading_button.isChecked()
        screen_data["blue_mode"] = self.combo_blue_mode.currentText()
        screen_data["blue_start_hour"] = self.spin_blue_start.value()
        screen_data["blue_end_hour"] = self.spin_blue_end.value()
        screen_data["gray_mode"] = self.combo_gray_mode.currentText()
        screen_data["gray_start_hour"] = self.spin_gray_start.value()
        screen_data["gray_end_hour"] = self.spin_gray_end.value()
        db.save()

    def _load_settings(self):
        s = db.data["settings"].get("screen", {})
        self.gray_button.setChecked(s.get("gray", False))
        self.reading_button.setChecked(s.get("reading", False))
        self.blue_filter_slider.setValue(s.get("blue_filter", 0))
        self.brightness_slider.setValue(s.get("brightness", 100))
        self.darkness_slider.setValue(s.get("darkness", 0))
        self.red_slider.setValue(s.get("red", 100))
        self.green_slider.setValue(s.get("green", 100))

        mode = s.get("blue_mode", "Her Zaman")
        idx = self.combo_blue_mode.findText(mode)
        if idx >= 0: self.combo_blue_mode.setCurrentIndex(idx)

        self.spin_blue_start.setValue(s.get("blue_start_hour", 20))
        self.spin_blue_end.setValue(s.get("blue_end_hour", 7))

        g_mode = s.get("gray_mode", "Her Zaman")
        g_idx = self.combo_gray_mode.findText(g_mode)
        if g_idx >= 0: self.combo_gray_mode.setCurrentIndex(g_idx)

        self.spin_gray_start.setValue(s.get("gray_start_hour", 22))
        self.spin_gray_end.setValue(s.get("gray_end_hour", 6))

    def update_display(self):
        self._apply_now()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zaman")
        self.setMinimumSize(920, 620)

        icon_path = resource_path("ikon/Kavram.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet(DARK_STYLE)

        self.pomo_engine = PomodoroEngine()
        self.pomo_engine.on_alarm_callback = self.on_global_pomodoro_alarm

        self.init_ui()
        self.init_tray()

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.global_tick)
        self.timer.start()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        top_bar = QFrame()
        top_layout = QHBoxLayout(top_bar)
        
        mode_lbl = QLabel("Çalışma Modu:")
        mode_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        top_layout.addWidget(mode_lbl)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Mod 0: Pomodoro",
            "Mod 1: Görev / Planlayıcı",
            "Mod 2: Notlar",
            "Mod 3: Normal Takvim",
            "Mod 4: Rakamlı Takvim",
            "Mod 5: Sekizli Takvim",
            "Mod 6: Ömür Sayacı",
            "Mod 7: Tarih Ayarı",
            "Mod 8: Ekran Ayarı"
        ])
        self.mode_combo.setMinimumHeight(38)
        self.mode_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        mode_font = QFont()
        mode_font.setBold(True)
        mode_font.setPointSize(11)
        self.mode_combo.setFont(mode_font)
        self.mode_combo.currentIndexChanged.connect(self.change_mode)

        top_layout.addWidget(self.mode_combo, 1)
        main_layout.addWidget(top_bar)

        self.stack = QStackedWidget()

        self.pomodoro_widget = PomodoroWidget(self.pomo_engine, self.on_quick_note_added)
        self.task_widget = TaskPlannerWidget()
        self.notes_widget = NotesWidget()
        self.normal_cal = NormalCalendarWidget()
        self.numeric_cal = NumericCalendarWidget()
        self.octal_cal = OctalCalendarWidget()
        self.life_widget = LifeCountdownWidget()
        self.date_widget = DateSettingsWidget()
        self.screen_widget = ScreenSettingsWidget()

        # Wrap pages in scrollable containers for low-res scaling safety
        self.stack.addWidget(create_scrollable_container(self.pomodoro_widget)) # Mod 0
        self.stack.addWidget(create_scrollable_container(self.task_widget))     # Mod 1
        self.stack.addWidget(create_scrollable_container(self.notes_widget))    # Mod 2
        self.stack.addWidget(create_scrollable_container(self.normal_cal))      # Mod 3
        self.stack.addWidget(create_scrollable_container(self.numeric_cal))     # Mod 4
        self.stack.addWidget(create_scrollable_container(self.octal_cal))       # Mod 5
        self.stack.addWidget(create_scrollable_container(self.life_widget))     # Mod 6
        self.stack.addWidget(create_scrollable_container(self.date_widget))     # Mod 7
        self.stack.addWidget(create_scrollable_container(self.screen_widget))   # Mod 8

        main_layout.addWidget(self.stack)

    def init_tray(self):
        icon_path = resource_path("ikon/Kavram.png")
        if os.path.exists(icon_path):
            self.tray_icon = QSystemTrayIcon(QIcon(icon_path), self)
            tray_menu = QMenu()
            show_action = QAction("Göster / Gizle", self)
            show_action.triggered.connect(self.toggle_window)
            quit_action = QAction("Çıkış", self)
            quit_action.triggered.connect(QApplication.instance().quit)
            tray_menu.addAction(show_action)
            tray_menu.addAction(quit_action)
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
        else:
            self.tray_icon = None

    def toggle_window(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.activateWindow()

    def change_mode(self, index):
        self.stack.setCurrentIndex(index)
        self.global_tick()

    def global_tick(self):
        self.pomo_engine.tick()
        curr_widget = self.stack.currentWidget()
        if curr_widget:
            child = curr_widget.widget() if isinstance(curr_widget, QScrollArea) else curr_widget
            if hasattr(child, "update_display"):
                child.update_display()

    def on_quick_note_added(self):
        if hasattr(self, 'notes_widget'):
            self.notes_widget.refresh_notes()

    def on_global_pomodoro_alarm(self, old_phase, new_phase):
        pomo_cfg = db.data["settings"].get("pomodoro", {})
        if pomo_cfg.get("show_notification", True) and hasattr(self, 'tray_icon') and self.tray_icon:
            msg = f"{old_phase} tamamlandı! Yeni evre: {new_phase}"
            self.tray_icon.showMessage("Pomodoro Zamanlayıcı", msg, QSystemTrayIcon.Information, 5000)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
