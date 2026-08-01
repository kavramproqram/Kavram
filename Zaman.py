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

from PyQt5.QtCore import Qt, QTimer, QSettings, QLocale, QDate, pyqtSignal, QEvent
from PyQt5.QtGui import QColor, QPalette, QFont, QIcon, QTextCharFormat, QKeyEvent
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QSpinBox, QCheckBox, QStackedWidget,
    QFrame, QAbstractItemView, QCalendarWidget, QDateTimeEdit, QDialog, 
    QDialogButtonBox, QStyleFactory, QGridLayout, QTextEdit, QLineEdit,
    QSlider, QGroupBox, QMessageBox
)

# Suppress Qt background logging
os.environ["QT_LOGGING_RULES"] = "qt.*=false;*.debug=false;qt.x11.*=false;qt.qpa.*=false;qt.accessibility.*=false"

def resource_path(relative_path):
    """PyInstaller support and local path resolver"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def generate_pleasant_chime():
    """Generates a pleasant 1.0-second chime audio file (WAV) dynamically."""
    temp_dir = tempfile.gettempdir()
    wav_path = os.path.join(temp_dir, "kavram_chime.wav")
    
    if os.path.exists(wav_path):
        return wav_path

    sample_rate = 44100
    duration = 1.0
    n_samples = int(sample_rate * duration)
    
    # Pleasant chime harmonic frequencies (E5, B5, E6 notes)
    freq1 = 659.25
    freq2 = 987.77
    freq3 = 1318.51
    
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        # Exponential decay envelope for bell-like fade out
        envelope = math.exp(-3.8 * t)
        
        # Attack envelope (10ms fade in)
        if t < 0.01:
            envelope *= (t / 0.01)
            
        val = (0.5 * math.sin(2 * math.pi * freq1 * t) +
               0.3 * math.sin(2 * math.pi * freq2 * t) +
               0.2 * math.sin(2 * math.pi * freq3 * t))
               
        val *= envelope * 0.75
        
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

def play_sound_file(wav_path):
    """Plays WAV audio file across platforms using QtMultimedia or native tools"""
    if not os.path.exists(wav_path):
        return

    # Method 1: QtMultimedia QSoundEffect
    try:
        from PyQt5.QtMultimedia import QSoundEffect
        from PyQt5.QtCore import QUrl
        if not hasattr(play_sound_file, "_sound_effect"):
            play_sound_file._sound_effect = QSoundEffect()
            play_sound_file._sound_effect.setSource(QUrl.fromLocalFile(os.path.abspath(wav_path)))
            play_sound_file._sound_effect.setVolume(0.85)
        play_sound_file._sound_effect.play()
        return
    except Exception:
        pass

    # Method 2: OS Native Fallbacks
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
        # Linux (PulseAudio, ALSA, PipeWire, Canberra)
        for cmd in ["paplay", "aplay", "pw-play", "canberra-gtk-play"]:
            try:
                subprocess.Popen([cmd, wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                continue

# ---------- MODERN DARK STYLESHEET (Zaman.py Unified Design) ----------
DARK_STYLE = """
QMainWindow {
    background-color: #121212;
}
QWidget {
    background-color: #121212;
    color: #e0e0e0;
    font-family: 'Segoe UI', 'Ubuntu', sans-serif;
    font-size: 14px;
}
QFrame {
    background-color: #1e1e1e;
    border-radius: 8px;
    border: 1px solid #2d2d2d;
}
QLabel {
    background: transparent;
    border: none;
    color: #ffffff;
}
QComboBox, QLineEdit, QTextEdit {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
    padding: 6px 12px;
    border-radius: 6px;
    color: #ffffff;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #2b2b2b;
    selection-background-color: #4CAF50;
    color: #ffffff;
    border: 1px solid #3d3d3d;
}
QPushButton {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
    padding: 8px 16px;
    border-radius: 6px;
    color: #ffffff;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #383838;
    border: 1px solid #4d4d4d;
}
QPushButton:pressed {
    background-color: #1e1e1e;
}
QPushButton:checked {
    background-color: #4CAF50;
    border: 1px solid #66BB6A;
    color: #ffffff;
}
QTableWidget {
    background-color: #1e1e1e;
    alternate-background-color: #252525;
    gridline-color: #2d2d2d;
    selection-background-color: #3d3d3d;
    color: #ffffff;
    border: 1px solid #2d2d2d;
    border-radius: 8px;
}
QTableWidget::item {
    padding: 8px;
}
QHeaderView::section {
    background-color: #2b2b2b;
    padding: 6px;
    border: 1px solid #2d2d2d;
    font-weight: bold;
}
QProgressBar {
    border: 1px solid #2d2d2d;
    border-radius: 6px;
    text-align: center;
    background-color: #1a1a1a;
    color: #ffffff;
    font-weight: bold;
    height: 20px;
}
QProgressBar::chunk {
    background-color: #4CAF50;
    border-radius: 5px;
}
QSpinBox {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
    padding: 6px;
    border-radius: 6px;
    color: #ffffff;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #3d3d3d;
    border-radius: 3px;
    margin: 1px;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #2b2b2b;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QCalendarWidget QToolButton {
    color: #ffffff;
    background-color: transparent;
    border-radius: 4px;
    padding: 4px;
}
QCalendarWidget QToolButton:hover {
    background-color: #3d3d3d;
}
QCalendarWidget QMenu {
    background-color: #2b2b2b;
    color: #ffffff;
}
QCalendarWidget QSpinBox {
    background-color: #3d3d3d;
    color: #ffffff;
}
QCalendarWidget QTableView {
    background-color: #1e1e1e;
    alternate-background-color: #252525;
    color: #ffffff;
    selection-background-color: #4CAF50;
    selection-color: #ffffff;
}
QCheckBox {
    background: transparent;
    border: none;
    color: #ffffff;
    font-weight: bold;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #3d3d3d;
    background-color: #2b2b2b;
}
QCheckBox::indicator:checked {
    background-color: #4CAF50;
    border: 1px solid #66BB6A;
}
QSlider::groove:horizontal {
    border: 1px solid #3D3D3D;
    height: 8px;
    background: #2B2B2B;
    margin: 2px 0;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #4CAF50;
    border: 1px solid #81C784;
    width: 18px;
    height: 18px;
    margin: -5px 0;
    border-radius: 9px;
}
QSlider::handle:horizontal:hover {
    background: #66BB6A;
}
QGroupBox {
    border: 1px solid #3D3D3D;
    border-radius: 8px;
    margin-top: 1.2ex;
    font-weight: bold;
    padding: 12px;
    background-color: #1E1E1E;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top center;
    padding: 0 8px;
    background-color: #121212;
    color: #4CAF50;
    border-radius: 4px;
}
QDialog {
    background-color: #121212;
}
"""

HINT_STYLE = (
    "color: #8A8A8A;"
    "font-size: 11px;"
    "font-style: italic;"
    "font-weight: 600;"
    "padding-bottom: 4px;"
)

def format_sayi(sayi):
    return f"{int(sayi):,}".replace(',', '.')

class DataManager:
    def __init__(self):
        self.dir_name = "Zaman_Veri"
        self.file_name = os.path.join(self.dir_name, "veriler.json")
        self.data = {
            "notes": {},
            "settings": {
                "time_offset_seconds": 0,
                "life_target_ts": None,
                "mod3_seg1": 0,
                "mod3_seg2": 8,
                "mod3_seg3": 11,
                "mod3_show_seconds": False,
                "pomodoro": {
                    "sound_enabled": True,
                    "work_min": 25,
                    "short_break_min": 5,
                    "long_break_min": 15
                },
                "screen": {
                    "red": 100,
                    "green": 100,
                    "blue_filter": 0,
                    "brightness": 100,
                    "darkness": 0,
                    "gray": False,
                    "reading": False,
                    "blue_mode": "Her Zaman",  # "Her Zaman", "Saat Aralığı", "Kademeli Otomatik"
                    "blue_start_hour": 20,
                    "blue_end_hour": 7,
                    "gray_mode": "Her Zaman",  # "Her Zaman", "Saat Aralığı"
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
                    if "notes" in loaded: self.data["notes"] = loaded["notes"]
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

    def get_note(self, mm_dd):
        return self.data["notes"].get(mm_dd, {"title": "", "text": ""})

    def set_note(self, mm_dd, title, text):
        if not title.strip() and not text.strip():
            if mm_dd in self.data["notes"]:
                del self.data["notes"][mm_dd]
        else:
            self.data["notes"][mm_dd] = {"title": title, "text": text}
        self.save()

db = DataManager()

def get_now():
    """Returns synchronized reference time based on Mod 5 custom offset"""
    offset = db.data["settings"].get("time_offset_seconds", 0)
    return datetime.now() + timedelta(seconds=offset)

class NoteDialog(QDialog):
    def __init__(self, date_str_mm_dd, display_date_str, parent=None):
        super().__init__(parent)
        self.date_str = date_str_mm_dd
        self.setWindowTitle(f"Not Ekle/Düzenle - {display_date_str}")
        self.setMinimumSize(400, 300)
        self.setStyleSheet(DARK_STYLE)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Başlık:"))
        self.title_input = QLineEdit()
        layout.addWidget(self.title_input)
        
        layout.addWidget(QLabel("Metin:"))
        self.text_input = QTextEdit()
        layout.addWidget(self.text_input)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Save).setText("Kaydet")
        btn_box.button(QDialogButtonBox.Cancel).setText("İptal")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
        note = db.get_note(self.date_str)
        self.title_input.setText(note["title"])
        self.text_input.setPlainText(note["text"])

    def get_data(self):
        return self.title_input.text(), self.text_input.toPlainText()

class PomodoroState:
    def __init__(self):
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
        self.on_phase_ended = None 

    def reset(self):
        self.phase = "Çalışma"
        self.remaining_seconds = self.work_sec
        self.cycles_done = 0
        self.running = False
        self.target_ts = None

    def start_or_pause(self):
        if not self.running:
            self.running = True
            self.target_ts = get_now() + timedelta(seconds=self.remaining_seconds)
        else:
            self.running = False
            self.remaining_seconds = max(0, (self.target_ts - get_now()).total_seconds())
            self.target_ts = None

    def update(self):
        if self.running and self.target_ts:
            secs = (self.target_ts - get_now()).total_seconds()
            if secs <= 0:
                self._next_phase()
            else:
                self.remaining_seconds = int(secs)

    def _next_phase(self):
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
        
        if self.on_phase_ended:
            self.on_phase_ended()

class PomodoroWidget(QWidget):
    def __init__(self, state: PomodoroState, save_callback, alert_callback):
        super().__init__()
        self.state = state
        self.save_callback = save_callback
        self.alert_callback = alert_callback
        self.state.on_phase_ended = self.phase_ended_event
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        settings_frame = QFrame()
        settings_layout = QHBoxLayout(settings_frame)
        
        settings_layout.addWidget(QLabel("Çalışma(dk):"))
        self.work_spin = QSpinBox()
        self.work_spin.setRange(1, 120)
        self.work_spin.setValue(self.state.work_sec // 60)
        self.work_spin.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.work_spin)

        settings_layout.addWidget(QLabel("Kısa Mola(dk):"))
        self.short_spin = QSpinBox()
        self.short_spin.setRange(1, 60)
        self.short_spin.setValue(self.state.short_break_sec // 60)
        self.short_spin.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.short_spin)

        settings_layout.addWidget(QLabel("Uzun Mola(dk):"))
        self.long_spin = QSpinBox()
        self.long_spin.setRange(1, 120)
        self.long_spin.setValue(self.state.long_break_sec // 60)
        self.long_spin.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.long_spin)

        # Sound toggle checkbox
        self.sound_check = QCheckBox("🔔 Zil Sesini Aç")
        snd_enabled = db.data["settings"].get("pomodoro", {}).get("sound_enabled", True)
        self.sound_check.setChecked(snd_enabled)
        self.sound_check.toggled.connect(self.on_sound_toggled)
        settings_layout.addWidget(self.sound_check)

        layout.addWidget(settings_frame)

        display_frame = QFrame()
        display_layout = QVBoxLayout(display_frame)
        
        self.phase_label = QLabel(self.state.phase)
        self.phase_label.setAlignment(Qt.AlignCenter)
        self.phase_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #e0e0e0;")
        display_layout.addWidget(self.phase_label)

        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("font-size: 72px; font-weight: bold; color: #4CAF50;")
        display_layout.addWidget(self.time_label)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(12)
        display_layout.addWidget(self.progress)
        
        layout.addWidget(display_frame)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Başlat / Duraklat (Enter)")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.on_start_pause)
        btn_layout.addWidget(self.start_btn)

        self.reset_btn = QPushButton("Sıfırla")
        self.reset_btn.setMinimumHeight(40)
        self.reset_btn.clicked.connect(self.on_reset)
        btn_layout.addWidget(self.reset_btn)

        layout.addLayout(btn_layout)
        
        note_frame = QFrame()
        note_layout = QVBoxLayout(note_frame)
        note_layout.setContentsMargins(10, 5, 10, 10)
        
        self.note_title_lbl = QLabel("Günün Notu")
        self.note_title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #aaaaaa;")
        note_layout.addWidget(self.note_title_lbl)
        
        self.note_text_display = QTextEdit()
        self.note_text_display.setReadOnly(True)
        self.note_text_display.setStyleSheet("background-color: transparent; border: none; color: #e0e0e0;")
        self.note_text_display.setMinimumHeight(60)
        note_layout.addWidget(self.note_text_display)
        
        layout.addWidget(note_frame)

    def play_chime(self):
        """Plays short sweet chime sound when phase finishes if sound is enabled"""
        if self.sound_check.isChecked():
            wav_path = generate_pleasant_chime()
            play_sound_file(wav_path)

    def on_sound_toggled(self, checked):
        if "pomodoro" not in db.data["settings"]:
            db.data["settings"]["pomodoro"] = {}
        db.data["settings"]["pomodoro"]["sound_enabled"] = checked
        db.save()

    def phase_ended_event(self):
        self.play_chime()
        self.save_callback()
        self.alert_callback()

    def trigger_enter(self):
        self.on_start_pause()

    def on_settings_changed(self):
        w_min = self.work_spin.value()
        s_min = self.short_spin.value()
        l_min = self.long_spin.value()

        self.state.work_sec = w_min * 60
        self.state.short_break_sec = s_min * 60
        self.state.long_break_sec = l_min * 60
        
        if "pomodoro" not in db.data["settings"]:
            db.data["settings"]["pomodoro"] = {}
            
        db.data["settings"]["pomodoro"]["work_min"] = w_min
        db.data["settings"]["pomodoro"]["short_break_min"] = s_min
        db.data["settings"]["pomodoro"]["long_break_min"] = l_min
        db.save()

        if not self.state.running:
            if self.state.phase == "Çalışma":
                self.state.remaining_seconds = self.state.work_sec
            elif self.state.phase == "Kısa Mola":
                self.state.remaining_seconds = self.state.short_break_sec
            else:
                self.state.remaining_seconds = self.state.long_break_sec
        self.save_callback()

    def on_start_pause(self):
        self.state.start_or_pause()
        self.save_callback()

    def on_reset(self):
        self.state.reset()
        self.work_spin.setValue(self.state.work_sec // 60)
        self.short_spin.setValue(self.state.short_break_sec // 60)
        self.long_spin.setValue(self.state.long_break_sec // 60)
        self.save_callback()

    def update_display(self):
        self.state.update()
        mins, secs = divmod(self.state.remaining_seconds, 60)
        self.time_label.setText(f"{int(mins):02d}:{int(secs):02d}")
        self.phase_label.setText(self.state.phase)

        if self.state.phase == "Çalışma":
            total = self.state.work_sec
            color = "#4CAF50"
        elif self.state.phase == "Kısa Mola":
            total = self.state.short_break_sec
            color = "#0A84FF"
        else:
            total = self.state.long_break_sec
            color = "#FF9F0A"
            
        self.time_label.setStyleSheet(f"font-size: 72px; font-weight: bold; color: {color}; border: none;")

        self.progress.setMaximum(total)
        self.progress.setValue(int(total - self.state.remaining_seconds))
        
        today_mm_dd = get_now().strftime("%m-%d")
        note = db.get_note(today_mm_dd)
        if note["title"] or note["text"]:
            self.note_title_lbl.setText(f"📋 {note['title']}" if note['title'] else "📋 Günün Notu")
            self.note_text_display.setPlainText(note["text"])
        else:
            self.note_title_lbl.setText("Günün Notu Yok")
            self.note_text_display.setPlainText("")

class NormalCalendarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        clock_frame = QFrame()
        clock_layout = QVBoxLayout(clock_frame)
        
        self.digital_clock = QLabel("00:00:00")
        self.digital_clock.setAlignment(Qt.AlignCenter)
        self.digital_clock.setStyleSheet("font-size: 48px; font-weight: bold; color: #ffffff; border: none;")
        clock_layout.addWidget(self.digital_clock)

        half_layout = QHBoxLayout()
        self.first_half_bar = QProgressBar()
        self.first_half_bar.setFormat("İlk 12 Saat %p%")
        half_layout.addWidget(self.first_half_bar)
        
        self.second_half_bar = QProgressBar()
        self.second_half_bar.setFormat("Son 12 Saat %p%")
        half_layout.addWidget(self.second_half_bar)
        
        clock_layout.addLayout(half_layout)
        layout.addWidget(clock_frame)

        self.calendar = QCalendarWidget(self)
        self.calendar.setLocale(QLocale(QLocale.Turkish, QLocale.Turkey))
        self.calendar.setFirstDayOfWeek(Qt.Monday)
        self.calendar.setGridVisible(True)
        self.calendar.setStyleSheet("border-radius: 8px; border: 1px solid #2d2d2d;")
        
        # Highlight Saturday and Sunday in Red
        fmt_weekend = QTextCharFormat()
        fmt_weekend.setForeground(QColor("#FF5252"))
        self.calendar.setWeekdayTextFormat(Qt.Saturday, fmt_weekend)
        self.calendar.setWeekdayTextFormat(Qt.Sunday, fmt_weekend)

        self.calendar.activated.connect(self.date_clicked)
        self.calendar.clicked.connect(self.date_clicked)

        layout.addWidget(self.calendar)

    def date_clicked(self, qdate):
        mm_dd = f"{qdate.month():02d}-{qdate.day():02d}"
        display_str = f"{qdate.day()} {QLocale(QLocale.Turkish).monthName(qdate.month())}"
        dlg = NoteDialog(mm_dd, display_str, self)
        if dlg.exec_() == QDialog.Accepted:
            t, txt = dlg.get_data()
            db.set_note(mm_dd, t, txt)

    def update_display(self):
        now = get_now()
        self.digital_clock.setText(now.strftime("%H:%M:%S"))
        
        hour = now.hour
        minute = now.minute
        
        if hour < 12:
            val1 = int(((hour * 60) + minute) / (12 * 60) * 100)
            val2 = 0
        else:
            val1 = 100
            val2 = int((((hour - 12) * 60) + minute) / (12 * 60) * 100)
            
        self.first_half_bar.setValue(val1)
        self.second_half_bar.setValue(val2)
        
        fmt_note = QTextCharFormat()
        fmt_note.setBackground(QColor("#555555"))
        fmt_note.setForeground(QColor("#ffffff"))
        
        fmt_clear = QTextCharFormat()

        y = self.calendar.yearShown()
        m = self.calendar.monthShown()
        days_in_month = calendar.monthrange(y, m)[1]
        
        for d in range(1, days_in_month + 1):
            date_obj = QDate(y, m, d)
            mm_dd = f"{m:02d}-{d:02d}"
            
            if db.get_note(mm_dd)["title"] or db.get_note(mm_dd)["text"]:
                self.calendar.setDateTextFormat(date_obj, fmt_note)
            else:
                self.calendar.setDateTextFormat(date_obj, fmt_clear)

class NumericCalendarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        clock_frame = QFrame()
        clock_layout = QVBoxLayout(clock_frame)
        self.digital_clock = QLabel("00:00:00")
        self.digital_clock.setAlignment(Qt.AlignCenter)
        self.digital_clock.setStyleSheet("font-size: 48px; font-weight: bold; color: #ffffff; border:none;")
        clock_layout.addWidget(self.digital_clock)
        
        half_layout = QHBoxLayout()
        self.first_half_bar = QProgressBar()
        self.first_half_bar.setFormat("İlk 12 Saat %p%")
        half_layout.addWidget(self.first_half_bar)
        self.second_half_bar = QProgressBar()
        self.second_half_bar.setFormat("Son 12 Saat %p%")
        half_layout.addWidget(self.second_half_bar)
        
        clock_layout.addLayout(half_layout)
        layout.addWidget(clock_frame)

        self.month_year_label = QLabel()
        self.month_year_label.setAlignment(Qt.AlignCenter)
        self.month_year_label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px; color: #ffffff;")
        layout.addWidget(self.month_year_label)

        self.table = QTableWidget(6, 7)
        
        # Red highlights on 6 and 7 in header
        for col, col_name in enumerate(["1", "2", "3", "4", "5", "6", "7"]):
            hdr_item = QTableWidgetItem(col_name)
            if col in (5, 6):  # 6 and 7
                hdr_item.setForeground(QColor("#FF5252"))
                font = QFont()
                font.setBold(True)
                hdr_item.setFont(font)
            else:
                hdr_item.setForeground(QColor("#E0E0E0"))
            self.table.setHorizontalHeaderItem(col, hdr_item)

        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellClicked.connect(self.cell_clicked)
        layout.addWidget(self.table)

    def cell_clicked(self, row, col):
        item = self.table.item(row, col)
        if item and item.text():
            day = int(item.text())
            now = get_now()
            mm_dd = f"{now.month:02d}-{day:02d}"
            display_str = f"{day} (Ay: {now.month})"
            dlg = NoteDialog(mm_dd, display_str, self)
            if dlg.exec_() == QDialog.Accepted:
                t, txt = dlg.get_data()
                db.set_note(mm_dd, t, txt)

    def update_display(self):
        now = get_now()
        self.digital_clock.setText(now.strftime("%H:%M:%S"))
        
        hour = now.hour
        minute = now.minute
        if hour < 12:
            val1 = int(((hour * 60) + minute) / (12 * 60) * 100)
            val2 = 0
        else:
            val1 = 100
            val2 = int((((hour - 12) * 60) + minute) / (12 * 60) * 100)
            
        self.first_half_bar.setValue(val1)
        self.second_half_bar.setValue(val2)

        year = now.year
        month = now.month
        self.month_year_label.setText(f"Ay: {month}  |  Yıl: {year}")

        cal = calendar.monthcalendar(year, month)
        
        self.table.clearContents()
        
        for row_idx, week in enumerate(cal[:6]):
            for col_idx, day in enumerate(week):
                if day != 0:
                    item = QTableWidgetItem(str(day))
                    item.setTextAlignment(Qt.AlignCenter)
                    
                    mm_dd = f"{month:02d}-{day:02d}"
                    has_note = bool(db.get_note(mm_dd)["title"] or db.get_note(mm_dd)["text"])
                    
                    if day == now.day:
                        item.setBackground(QColor("#4CAF50"))
                        item.setForeground(QColor("white"))
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                    elif has_note:
                        item.setBackground(QColor("#555555"))
                        item.setForeground(QColor("white"))
                    elif col_idx in (5, 6):  # 6 and 7 weekend columns
                        item.setForeground(QColor("#FF5252"))
                    else:
                        item.setForeground(QColor("#ffffff"))
                        
                    self.table.setItem(row_idx, col_idx, item)

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
        self.small_clock.setStyleSheet("font-size: 16px; color: #aaaaaa; border: none;")
        clock_layout.addWidget(self.small_clock)

        self.segment_label = QLabel("1. Bölüm - 0:00")
        self.segment_label.setAlignment(Qt.AlignCenter)
        self.segment_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #4CAF50; border: none;")
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
        seg_layout.addWidget(self.spin_seg1)
        
        seg_layout.addWidget(QLabel("2. Bölüm:"))
        self.spin_seg2 = QSpinBox()
        self.spin_seg2.setRange(0, 23)
        self.spin_seg2.setValue(self.seg2_start)
        self.spin_seg2.valueChanged.connect(self.save_segments)
        seg_layout.addWidget(self.spin_seg2)
        
        seg_layout.addWidget(QLabel("3. Bölüm:"))
        self.spin_seg3 = QSpinBox()
        self.spin_seg3.setRange(0, 23)
        self.spin_seg3.setValue(self.seg3_start)
        self.spin_seg3.valueChanged.connect(self.save_segments)
        seg_layout.addWidget(self.spin_seg3)

        layout.addWidget(seg_settings_frame)

        nav_frame = QFrame()
        nav_layout = QHBoxLayout(nav_frame)
        
        self.btn_prev = QPushButton("< Önceki Ay")
        self.btn_prev.clicked.connect(self.prev_month)
        nav_layout.addWidget(self.btn_prev)
        
        self.month_info_label = QLabel()
        self.month_info_label.setAlignment(Qt.AlignCenter)
        self.month_info_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        nav_layout.addWidget(self.month_info_label, 1)
        
        self.btn_next = QPushButton("Sonraki Ay >")
        self.btn_next.clicked.connect(self.next_month)
        nav_layout.addWidget(self.btn_next)
        
        self.btn_today = QPushButton("Bugün")
        self.btn_today.clicked.connect(self.go_today)
        nav_layout.addWidget(self.btn_today)
        
        layout.addWidget(nav_frame)

        self.grid_table = QTableWidget(5, 8)
        
        # Red highlights on 6, 7 and 8 in octal table header
        for col, col_name in enumerate([f"{i+1}" for i in range(8)]):
            hdr_item = QTableWidgetItem(col_name)
            if col in (5, 6, 7):  # 6, 7, 8
                hdr_item.setForeground(QColor("#FF5252"))
                font = QFont()
                font.setBold(True)
                hdr_item.setFont(font)
            else:
                hdr_item.setForeground(QColor("#E0E0E0"))
            self.grid_table.setHorizontalHeaderItem(col, hdr_item)

        self.grid_table.setVerticalHeaderLabels([f"{i+1}" for i in range(5)])
        self.grid_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.grid_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.grid_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.grid_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.grid_table.cellClicked.connect(self.cell_clicked)
        layout.addWidget(self.grid_table)

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

    def cell_clicked(self, row, col):
        item = self.grid_table.item(row, col)
        if item and item.text():
            day = int(item.text())
            doy = ((self.view_month - 1) * 40) + day
            try:
                target_date = datetime(self.view_year, 1, 1) + timedelta(days=doy - 1)
                mm_dd = target_date.strftime("%m-%d")
                
                dlg = NoteDialog(mm_dd, f"Sekizli {day}. Gün ({target_date.strftime('%d.%m.%Y')})", self)
                if dlg.exec_() == QDialog.Accepted:
                    t, txt = dlg.get_data()
                    db.set_note(mm_dd, t, txt)
                    self.update_calendar_grid()
            except ValueError:
                pass

    def update_calendar_grid(self):
        self.month_info_label.setText(f"Yıl: {self.view_year}  |  Ay: {self.view_month}")
        
        days_in_year = 366 if calendar.isleap(self.view_year) else 365
        if self.view_month < 9:
            days_in_this_month = 40
        else:
            days_in_this_month = days_in_year - 320

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
                    
                    doy = ((self.view_month - 1) * 40) + gun_no
                    has_note = False
                    try:
                        target_date = datetime(self.view_year, 1, 1) + timedelta(days=doy - 1)
                        mm_dd = target_date.strftime("%m-%d")
                        has_note = bool(db.get_note(mm_dd)["title"] or db.get_note(mm_dd)["text"])
                    except: pass
                    
                    if self.view_year == now.year and self.view_month == current_oct_month and gun_no == current_oct_day:
                        item.setBackground(QColor("#4CAF50"))
                        item.setForeground(QColor("white"))
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                    elif has_note:
                        item.setBackground(QColor("#555555"))
                        item.setForeground(QColor("white"))
                    elif c in (5, 6, 7):  # 6, 7 and 8 weekend columns
                        item.setForeground(QColor("#FF5252"))
                    else:
                        item.setForeground(QColor("#ffffff"))
                        
                    self.grid_table.setItem(r, c, item)

    def update_display(self):
        now = get_now()
        self.small_clock.setText(now.strftime("%H:%M:%S"))
        
        hour = now.hour
        minute = now.minute
        second = now.second

        times = [
            (self.seg1_start, 1),
            (self.seg2_start, 2),
            (self.seg3_start, 3)
        ]
        times.sort(reverse=True)

        current_seg = times[-1][1]
        seg_start_hour = times[-1][0]
        
        for start_h, seg_idx in times:
            if hour >= start_h:
                current_seg = seg_idx
                seg_start_hour = start_h
                break

        seg_hour = (hour - seg_start_hour) % 24
        
        seg_time_str = f"{current_seg}. Bölüm  |  {seg_hour}:{minute:02d}"
        if self.show_seconds:
            seg_time_str += f":{second:02d}"
            
        self.segment_label.setText(seg_time_str)
        self.update_calendar_grid()

class LifeCountdownWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.target_ts = self.load_target()
        self.init_ui()

    def load_target(self):
        val = db.data["settings"].get("life_target_ts")
        if val:
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                pass
        return None

    def save_target(self):
        if self.target_ts:
            db.data["settings"]["life_target_ts"] = self.target_ts.isoformat()
        else:
            db.data["settings"]["life_target_ts"] = None
        db.save()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        display_frame = QFrame()
        disp_layout = QVBoxLayout(display_frame)
        disp_layout.setSpacing(20)

        self.sec_label = QLabel("0 Saniye")
        self.sec_label.setAlignment(Qt.AlignCenter)
        self.sec_label.setStyleSheet("font-size: 42px; font-weight: bold; color: #aaaaaa; border: none;")
        disp_layout.addWidget(self.sec_label)

        self.min_label = QLabel("0 Dakika")
        self.min_label.setAlignment(Qt.AlignCenter)
        self.min_label.setStyleSheet("font-size: 52px; font-weight: bold; color: #cccccc; border: none;")
        disp_layout.addWidget(self.min_label)

        self.hour_label = QLabel("0 Saat")
        self.hour_label.setAlignment(Qt.AlignCenter)
        self.hour_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #ffffff; border: none;")
        disp_layout.addWidget(self.hour_label)

        self.day_label = QLabel("0 Gün")
        self.day_label.setAlignment(Qt.AlignCenter)
        self.day_label.setStyleSheet("font-size: 80px; font-weight: bold; color: #4CAF50; border: none;")
        disp_layout.addWidget(self.day_label)

        layout.addWidget(display_frame)

        cfg_frame = QFrame()
        cfg_layout = QHBoxLayout(cfg_frame)
        
        cfg_layout.addWidget(QLabel("Ömür Hedefi (Yıl):"))
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1, 1000)
        self.year_spin.setValue(40)
        self.year_spin.setStyleSheet("font-size: 16px; padding: 4px;")
        cfg_layout.addWidget(self.year_spin)
        
        self.set_btn = QPushButton("Sayacı Başlat / Güncelle")
        self.set_btn.clicked.connect(self.start_countdown)
        cfg_layout.addWidget(self.set_btn)
        
        layout.addWidget(cfg_frame)

    def start_countdown(self):
        years = self.year_spin.value()
        days = years * 365.25
        self.target_ts = get_now() + timedelta(days=days)
        self.save_target()
        self.update_display()

    def update_display(self):
        if not self.target_ts:
            self.sec_label.setText("-- Saniye")
            self.min_label.setText("-- Dakika")
            self.hour_label.setText("-- Saat")
            self.day_label.setText("-- Gün")
            return
            
        now = get_now()
        delta = self.target_ts - now
        
        if delta.total_seconds() <= 0:
            self.sec_label.setText("0 Saniye")
            self.min_label.setText("0 Dakika")
            self.hour_label.setText("0 Saat")
            self.day_label.setText("0 Gün")
            return

        total_secs = delta.total_seconds()
        
        total_mins = total_secs / 60
        total_hours = total_secs / 3600
        total_days = total_secs / 86400

        self.sec_label.setText(f"{format_sayi(total_secs)} Saniye")
        self.min_label.setText(f"{format_sayi(total_mins)} Dakika")
        self.hour_label.setText(f"{format_sayi(total_hours)} Saat")
        self.day_label.setText(f"{format_sayi(total_days)} Gün")

class DateSettingsWidget(QWidget):
    """Mod 5 : Tarih Ayarı - Kullanıcının özel referans saat belirlemesini ve senkronizasyonunu sağlar"""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        info_frame = QFrame()
        info_layout = QVBoxLayout(info_frame)
        
        lbl_title = QLabel("Tarih ve Saat Referans Ayarı")
        lbl_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #4CAF50; border: none;")
        info_layout.addWidget(lbl_title)

        lbl_desc = QLabel(
            "Bu alanda belirleyeceğiniz tarih ve saat, bilgisayarınızın saati ile kıyaslanarak aradaki fark kaydedilir.\n"
            "Uygulamadaki tüm modlar (Pomodoro, Takvimler, Ömür Sayacı, Ekran Ayarı) bu referans zamana göre otomatik senkronize çalışır."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #cccccc; font-size: 13px; border: none;")
        info_layout.addWidget(lbl_desc)

        layout.addWidget(info_frame)

        input_frame = QFrame()
        input_layout = QGridLayout(input_frame)
        input_layout.setSpacing(10)

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
        
        self.btn_update = QPushButton("Referans Zamanı Güncelle")
        self.btn_update.setMinimumHeight(42)
        self.btn_update.setStyleSheet("background-color: #2e7d32; color: #ffffff; font-weight: bold;")
        self.btn_update.clicked.connect(self.apply_custom_time)
        btn_layout.addWidget(self.btn_update)

        self.btn_reset = QPushButton("Sistem Zamanına Sıfırla")
        self.btn_reset.setMinimumHeight(42)
        self.btn_reset.setStyleSheet("background-color: #c62828; color: #ffffff; font-weight: bold;")
        self.btn_reset.clicked.connect(self.reset_to_system_time)
        btn_layout.addWidget(self.btn_reset)

        layout.addLayout(btn_layout)

        display_frame = QFrame()
        disp_layout = QVBoxLayout(display_frame)

        self.lbl_real_time = QLabel("Bilgisayar Saati: --")
        self.lbl_real_time.setStyleSheet("font-size: 16px; color: #aaaaaa; border: none;")
        disp_layout.addWidget(self.lbl_real_time)

        self.lbl_app_time = QLabel("Uygulama (Referans) Saati: --")
        self.lbl_app_time.setStyleSheet("font-size: 22px; font-weight: bold; color: #4CAF50; border: none;")
        disp_layout.addWidget(self.lbl_app_time)

        self.lbl_diff_time = QLabel("Uygulanan Zaman Farkı: --")
        self.lbl_diff_time.setStyleSheet("font-size: 14px; color: #FF9F0A; border: none;")
        disp_layout.addWidget(self.lbl_diff_time)

        layout.addWidget(display_frame)
        layout.addStretch()

    def apply_custom_time(self):
        try:
            target_dt = datetime(
                self.spin_year.value(),
                self.spin_month.value(),
                self.spin_day.value(),
                self.spin_hour.value(),
                self.spin_minute.value(),
                self.spin_second.value()
            )
            real_now = datetime.now()
            offset = (target_dt - real_now).total_seconds()

            db.data["settings"]["time_offset_seconds"] = offset
            db.save()
            QMessageBox.information(self, "Başarılı", "Referans zaman güncellendi!")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Geçersiz tarih seçimi: {e}")

    def reset_to_system_time(self):
        db.data["settings"]["time_offset_seconds"] = 0
        db.save()

        now = datetime.now()
        self.spin_year.setValue(now.year)
        self.spin_month.setValue(now.month)
        self.spin_day.setValue(now.day)
        self.spin_hour.setValue(now.hour)
        self.spin_minute.setValue(now.minute)
        self.spin_second.setValue(now.second)

        QMessageBox.information(self, "Sıfırlandı", "Uygulama saati bilgisayar saatiyle senkronize edildi.")

    def update_display(self):
        real_now = datetime.now()
        app_now = get_now()
        offset_sec = int(db.data["settings"].get("time_offset_seconds", 0))

        self.lbl_real_time.setText(f"Bilgisayar Saati: {real_now.strftime('%d.%m.%Y %H:%M:%S')}")
        self.lbl_app_time.setText(f"Uygulama (Referans) Saati: {app_now.strftime('%d.%m.%Y %H:%M:%S')}")

        sign = "+" if offset_sec >= 0 else "-"
        abs_sec = abs(offset_sec)
        days, remainder = divmod(abs_sec, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        diff_str = f"{sign} "
        if days > 0: diff_str += f"{days} Gün "
        diff_str += f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        self.lbl_diff_time.setText(f"Uygulanan Zaman Farkı: {diff_str}")

class ScreenSettingsWidget(QWidget):
    """
    Mod 6: Ekran Ayarı & Mavi Işık Filtresi
    - Zaman.py tasarım diliyle tam uyumlu
    - Mod 5 Referans saatine duyarlı kademeli / saatli filtreleme
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

    def _set_cursor_theme(self, theme):
        if not theme: return
        try:
            subprocess.run(["xfconf-query", "-c", "xsettings", "-p", "/Gtk/CursorThemeName", "--set", theme], check=False)
        except Exception:
            pass

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

        # Reference Clock Banner
        clock_frame = QFrame()
        clock_box = QHBoxLayout(clock_frame)
        clock_box.setContentsMargins(12, 8, 12, 8)
        
        self.ref_clock_label = QLabel("Mod 5 Referans Saati: --:--:--")
        self.ref_clock_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50; border: none;")
        clock_box.addWidget(self.ref_clock_label)

        self.reset_button = QPushButton("Sıfırla")
        self.reset_button.setCursor(Qt.PointingHandCursor)
        self.reset_button.clicked.connect(self._reset)
        clock_box.addWidget(self.reset_button)

        self.refresh_btn = QPushButton("Ekranları Yenile")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        clock_box.addWidget(self.refresh_btn)

        self.autostart_button = QPushButton("Otomatik Başlat")
        self.autostart_button.setCheckable(True)
        autostart_path = os.path.expanduser("~/.config/autostart/kavram_blf.desktop")
        self.autostart_button.setChecked(os.path.exists(autostart_path))
        self.autostart_button.toggled.connect(self._on_autostart_toggled)
        clock_box.addWidget(self.autostart_button)

        main_layout.addWidget(clock_frame)

        # Status Group
        sg = QGroupBox("Sistem Durumu")
        sl = QVBoxLayout()
        self.status_label = QLabel("Durum: Aktif")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold; border: none;")
        sl.addWidget(self.status_label)
        sg.setLayout(sl)
        main_layout.addWidget(sg)

        # Mode Selection & Scheduling Group
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

        # Blue Light Filter Slider
        bg = QGroupBox("Mavi Işık Filtresi (Hedef Seviye)")
        bv = QVBoxLayout()
        self.blue_filter_slider = self._make_row(
            bv, "Mavi Işık Filtre Şiddeti",
            "0–40: Hafif filtre | 40–80: Derin gece koruması | 80–100: Ultra sıcak okuma modu",
            0, 100, 0
        )
        bg.setLayout(bv)
        main_layout.addWidget(bg)

        # Color Channels
        cg = QGroupBox("RGB Renk Dengesi")
        cv = QVBoxLayout()
        self.red_slider = self._make_row(cv, "Kırmızı Kanalı", "Sıcaklığı artırır", 50, 160, 100)
        self.green_slider = self._make_row(cv, "Yeşil Kanalı", "Yeşil ton ayarı", 50, 160, 100)
        cg.setLayout(cv)
        main_layout.addWidget(cg)

        # Brightness & Darkness
        pg = QGroupBox("Parlaklık & Gama Karartma")
        pv = QVBoxLayout()
        self.brightness_slider = self._make_row(pv, "Ekran Parlaklığı", "Genel ekran ışık gücü", 20, 150, 100)
        self.darkness_slider = self._make_row(pv, "Gama Karartma", "Karanlık ortamlarda gözü korur", 0, 80, 0)
        pg.setLayout(pv)
        main_layout.addWidget(pg)

        # Modes Bottom Bar
        bottom_bar = QHBoxLayout()
        self.reading_button = QPushButton("Okuma Modu")
        self.reading_button.setCheckable(True)
        self.reading_button.toggled.connect(self._on_reading)

        self.gray_button = QPushButton("Gri Mod (Grayscale)")
        self.gray_button.setCheckable(True)
        self.gray_button.toggled.connect(self._apply)

        bottom_bar.addWidget(self.reading_button)
        bottom_bar.addWidget(self.gray_button)
        main_layout.addLayout(bottom_bar)

        shortcut_lbl = QLabel("Kısayol: Ekran bozulursa düzeltmek için Alt + V tuşlarına basın.")
        shortcut_lbl.setStyleSheet(HINT_STYLE)
        shortcut_lbl.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(shortcut_lbl)

    def _make_row(self, layout, name, hint_text, min_v=0, max_v=100, def_v=0):
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("color: #EEEEEE; font-size: 13px; font-weight: bold; border: none;")
        layout.addWidget(name_lbl)

        sld = QSlider(Qt.Horizontal)
        sld.setRange(min_v, max_v)
        sld.setValue(def_v)
        sld.valueChanged.connect(self._apply)
        layout.addWidget(sld)

        hint_lbl = QLabel(hint_text)
        hint_lbl.setStyleSheet(HINT_STYLE)
        hint_lbl.setWordWrap(True)
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
Exec={sys.executable} "{script_path}" --startup
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Kavram Screen Manager
Comment=Applies custom screen color profile on login
"""
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
            if self.xfce_compositing_was_on: self._set_xfce_comp(False)
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
            if self.xfce_compositing_was_on:
                self._set_xfce_comp(True)
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
        """Calculates effective blue light filter level based on Mod 5 reference time & user scheduling"""
        target_val = self.blue_filter_slider.value()
        mode = self.combo_blue_mode.currentText()
        now = get_now()
        cur_h = now.hour + (now.minute / 60.0)

        if mode == "Her Zaman":
            return target_val
        elif mode == "Saat Aralığı":
            start_h = self.spin_blue_start.value()
            end_h = self.spin_blue_end.value()
            if self._is_in_hours(start_h, end_h, now.hour):
                return target_val
            else:
                return 0
        elif mode == "Kademeli Otomatik":
            # Smooth curve increase during evening hours (18:00 to 23:00)
            if cur_h < 18.0:
                factor = 0.0
            elif cur_h >= 23.0 or cur_h < 6.0:
                factor = 1.0
            else:
                factor = (cur_h - 18.0) / 5.0  # Linear ramp over 5 hours
            return int(target_val * factor)
        return target_val

    def _blue_params(self, blue_val):
        val = blue_val / 100.0
        if val <= 0.40:
            norm = val / 0.40
            blue_g = 1.0 - (norm * 0.60)
            extra_br = 1.0
        elif val <= 0.80:
            norm = (val - 0.40) / 0.40
            blue_g = 0.40 - (norm * 0.32)
            extra_br = 1.0 - (norm * 0.15)
        else:
            norm = (val - 0.80) / 0.20
            blue_g = 0.08 - (norm * 0.06)
            extra_br = 0.85 - (norm * 0.15)
        return blue_g, extra_br

    def _apply(self, *_):
        self._apply_timer.start(35)

    def _apply_now(self):
        now = get_now()
        self.ref_clock_label.setText(f"Mod 5 Referans Saati: {now.strftime('%H:%M:%S')}")

        # Determine Grayscale State
        is_gray_user = self.gray_button.isChecked()
        gray_mode = self.combo_gray_mode.currentText()
        is_gray = False
        if is_gray_user:
            if gray_mode == "Her Zaman":
                is_gray = True
            elif gray_mode == "Saat Aralığı":
                is_gray = self._is_in_hours(self.spin_gray_start.value(), self.spin_gray_end.value(), now.hour)

        # Calculate effective blue filter level
        eff_blue = self._calculate_effective_blue_level()

        darkness_val = self.darkness_slider.value() / 100.0
        dark_coef = (1.0 - darkness_val) ** 1.35

        br_base = self.brightness_slider.value() / 100.0
        blue_g, extra_br = self._blue_params(eff_blue)

        br = br_base * extra_br
        r = (self.red_slider.value() / 100.0) * dark_coef
        g = (self.green_slider.value() / 100.0) * dark_coef
        b = blue_g * dark_coef

        if is_gray:
            self._enable_gray()
            if self.grayscale_method == "gamma":
                avg = 0.2126 * r + 0.7152 * g + 0.0722 * b
                r = g = b = avg
        else:
            if self.grayscale_method:
                self._disable_gray()

        clamp = lambda v: max(0.05, round(v, 4))
        r_c, g_c, b_c = clamp(r), clamp(g), clamp(b)
        br_str = f"{max(0.1, round(br, 4))}"
        gamma_str = f"{r_c}:{g_c}:{b_c}"

        # Execution based on Session
        if self.session_type == "wayland":
            if self.has_gammastep:
                temp = int(6500 - (eff_blue * 47))
                subprocess.Popen(["gammastep", "-O", str(temp), "-b", f"{br_str}:0.8"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif self.has_wlsunset:
                temp = int(6500 - (eff_blue * 47))
                subprocess.Popen(["wlsunset", "-T", str(temp)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            displays = self._connected_displays()
            for d in displays:
                try:
                    subprocess.run(["xrandr", "--output", d, "--gamma", gamma_str, "--brightness", br_str],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception: pass

        self._update_status(eff_blue, is_gray)
        if not self._block_save:
            self._save()

    def update_display(self):
        """Called regularly by main window timer to update scheduled screen settings live"""
        self._apply_now()

    def _on_reading(self, checked):
        self._block_save = True
        if checked:
            self.red_slider.setValue(120)
            self.green_slider.setValue(92)
            self.blue_filter_slider.setValue(65)
            self.brightness_slider.setValue(82)
            self.darkness_slider.setValue(12)
        else:
            self.red_slider.setValue(100)
            self.green_slider.setValue(100)
            self.blue_filter_slider.setValue(0)
            self.brightness_slider.setValue(100)
            self.darkness_slider.setValue(0)
        self._block_save = False
        self._apply_now()

    def _save(self):
        os.makedirs(self.VERI_DIR, exist_ok=True)
        scr_data = {
            "red": self.red_slider.value(),
            "green": self.green_slider.value(),
            "blue_filter": self.blue_filter_slider.value(),
            "brightness": self.brightness_slider.value(),
            "darkness": self.darkness_slider.value(),
            "gray": self.gray_button.isChecked(),
            "reading": self.reading_button.isChecked(),
            "blue_mode": self.combo_blue_mode.currentText(),
            "blue_start_hour": self.spin_blue_start.value(),
            "blue_end_hour": self.spin_blue_end.value(),
            "gray_mode": self.combo_gray_mode.currentText(),
            "gray_start_hour": self.spin_gray_start.value(),
            "gray_end_hour": self.spin_gray_end.value(),
        }
        db.data["settings"]["screen"] = scr_data
        db.save()

    def _load_settings(self):
        self._block_save = True
        s = db.data["settings"].get("screen", {})
        
        self.blue_filter_slider.setValue(s.get("blue_filter", 0))
        self.red_slider.setValue(s.get("red", 100))
        self.green_slider.setValue(s.get("green", 100))
        self.brightness_slider.setValue(s.get("brightness", 100))
        self.darkness_slider.setValue(s.get("darkness", 0))
        self.gray_button.setChecked(s.get("gray", False))
        self.reading_button.setChecked(s.get("reading", False))

        bm = s.get("blue_mode", "Her Zaman")
        idx = self.combo_blue_mode.findText(bm)
        if idx >= 0: self.combo_blue_mode.setCurrentIndex(idx)

        self.spin_blue_start.setValue(s.get("blue_start_hour", 20))
        self.spin_blue_end.setValue(s.get("blue_end_hour", 7))

        gm = s.get("gray_mode", "Her Zaman")
        idx_g = self.combo_gray_mode.findText(gm)
        if idx_g >= 0: self.combo_gray_mode.setCurrentIndex(idx_g)

        self.spin_gray_start.setValue(s.get("gray_start_hour", 22))
        self.spin_gray_end.setValue(s.get("gray_end_hour", 6))
        self._block_save = False

    def _reset(self):
        self._block_save = True
        self.red_slider.setValue(100)
        self.green_slider.setValue(100)
        self.blue_filter_slider.setValue(0)
        self.brightness_slider.setValue(100)
        self.darkness_slider.setValue(0)
        self.gray_button.setChecked(False)
        self.reading_button.setChecked(False)
        self.combo_blue_mode.setCurrentIndex(0)
        self.combo_gray_mode.setCurrentIndex(0)
        self._block_save = False
        self._apply_now()

    def _update_status(self, eff_blue, is_gray):
        m = f" [{self.grayscale_method}]" if self.grayscale_method else ""
        gray = f"GRİ MOD: AÇIK{m}" if is_gray else "GRİ MOD: Kapalı"
        flt = f"Mavi Filtre: %{eff_blue} (Aktif)"
        rd = " | Okuma Modu" if self.reading_button.isChecked() else ""
        self.status_label.setText(f"Durum: Aktif ({self.session_type.upper()})  |  {gray}  |  {flt}{rd}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zaman")
        self.setMinimumSize(860, 680)

        # Set window icon
        icon_path = resource_path("ikon/Kavram.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet(DARK_STYLE)

        self.pomodoro_state = PomodoroState()

        self.init_ui()

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.global_update)
        self.timer.start()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Top Mode Switcher Bar
        top_bar = QFrame()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 6, 8, 6)
        top_layout.setSpacing(8)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Mod 0: Pomodoro",
            "Mod 1: Normal Takvim",
            "Mod 2: Rakamlı Takvim",
            "Mod 3: Sekizli Takvim",
            "Mod 4: Ömür Sayacı",
            "Mod 5: Tarih Ayarı",
            "Mod 6: Ekran Ayarı"
        ])
        self.mode_combo.setMinimumHeight(38)
        self.mode_combo.setStyleSheet("font-weight: bold; font-size: 15px;")
        self.mode_combo.currentIndexChanged.connect(self.change_mode)

        top_layout.addWidget(QLabel("Çalışma Modu:"))
        top_layout.addWidget(self.mode_combo, 1)

        main_layout.addWidget(top_bar)

        # Stacked Widget
        self.stack = QStackedWidget()

        self.pomodoro_widget = PomodoroWidget(
            self.pomodoro_state, 
            self.save_pomo_state, 
            self.pomo_alert
        )
        self.normal_cal_widget = NormalCalendarWidget()
        self.numeric_cal_widget = NumericCalendarWidget()
        self.octal_cal_widget = OctalCalendarWidget()
        self.life_widget = LifeCountdownWidget()
        self.date_widget = DateSettingsWidget()
        self.screen_widget = ScreenSettingsWidget()

        self.stack.addWidget(self.pomodoro_widget)     # Mod 0
        self.stack.addWidget(self.normal_cal_widget)   # Mod 1
        self.stack.addWidget(self.numeric_cal_widget)  # Mod 2
        self.stack.addWidget(self.octal_cal_widget)    # Mod 3
        self.stack.addWidget(self.life_widget)         # Mod 4
        self.stack.addWidget(self.date_widget)         # Mod 5
        self.stack.addWidget(self.screen_widget)       # Mod 6

        main_layout.addWidget(self.stack)

    def change_mode(self, index):
        self.stack.setCurrentIndex(index)
        self.global_update()

    def save_pomo_state(self):
        db.save()

    def pomo_alert(self):
        QApplication.alert(self)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.stack.currentIndex() == 0:
                self.pomodoro_widget.trigger_enter()
        else:
            super().keyPressEvent(event)

    def global_update(self):
        curr_idx = self.stack.currentIndex()
        if curr_idx == 0:
            self.pomodoro_widget.update_display()
        elif curr_idx == 1:
            self.normal_cal_widget.update_display()
        elif curr_idx == 2:
            self.numeric_cal_widget.update_display()
        elif curr_idx == 3:
            self.octal_cal_widget.update_display()
        elif curr_idx == 4:
            self.life_widget.update_display()
        elif curr_idx == 5:
            self.date_widget.update_display()
        elif curr_idx == 6:
            self.screen_widget.update_display()

        # Always keep background screen schedule updated
        if curr_idx != 6:
            self.screen_widget.update_display()

    def closeEvent(self, event):
        self.screen_widget._save()
        db.save()
        event.accept()

if __name__ == "__main__":
    if "--startup" in sys.argv:
        time.sleep(3)

    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))

    main_win = MainWindow()

    if "--startup" in sys.argv:
        sys.exit(0)

    main_win.show()
    sys.exit(app.exec_())
