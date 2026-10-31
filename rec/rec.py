# Kavram 2.2.2
# Copyright (C) 2026-07-22 Kavram or Contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see /Kavram/License/GPLv3.txt
#
# ---------------------------------------------
#
# Kavram 2.2.2
# Copyright (C) 2026-07-22 Kavram veya Contributors
#
# Bu program özgür bir yazılımdır: Özgür Yazılım Vakfı tarafından yayınlanan
# GNU Genel Kamu Lisansı'nın 3. sürümü veya (tercihinize bağlı olarak)
# daha sonraki herhangi bir sürümü kapsamında yeniden dağıtabilir ve/veya
# değiştirebilirsiniz.
#
# Bu program, faydalı olacağı umuduyla dağıtılmaktadır, ancak HERHANGİ BİR
# GARANTİ OLMADAN; hatta SATILABİLİRLİK veya BELİRLİ BİR AMACA UYGUNLUK
# zımni garantisi olmaksızın.
#
# Bu programla birlikte GNU Genel Kamu Lisansı'nın bir kopyasını almış olmanız gerekir:
# /Kavram/License/GPLv3.txt

# --- kavram yol ayarı (otomatik; klasör yapısı: kavram/<program>/<program>.py) ---
import os as _os
_PROGRAM_DIR = _os.path.dirname(_os.path.abspath(__file__))
_KAVRAM_DIR = _os.environ.get("KAVRAM_DIR") or _os.path.dirname(_PROGRAM_DIR)
_KAVRAM_EXPORT_DIR = _os.path.join(_KAVRAM_DIR, "export")
# -------------------------------------------------------------------------------
import sys, os, subprocess, time, cv2, tempfile, signal, platform, json
import mmap
import struct
import datetime
import threading
import re
from collections import defaultdict
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QSplitter, QFileDialog, QMessageBox, QSlider,
    QStyle, QStyleOptionSlider, QSizePolicy, QProgressDialog, QDialog,
    QGridLayout, QComboBox, QSpacerItem, QShortcut, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDir, QUrl, QPoint, QObject, QRect
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QKeySequence, QIcon, QFont, QCursor

# Klavye ve mouse dinleme için pynput
try:
    from pynput import keyboard, mouse
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False
    print("Python Uyarısı: pynput bulunamadı, input gösterimi devre dışı.")

from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

import traceback
import shutil

# ---- Kavram File / Export penceresi (file_manager) -------------------------------
# Kavram çekirdeğinden çalışırken "kavram_file_manager" adıyla yüklenir; program tek başına
# çalıştırılırsa kardeş klasördeki file_manager/file_manager.py doğrudan yüklenir.  Hiçbiri
# olmazsa Qt'nin kendi diyaloğuna dönülür (program asla dosya seçemeden kalmaz).
try:
    import kavram_file_manager as _fm
except Exception:
    try:
        import importlib.util as _ilu
        import os as _fm_os
        import sys as _fm_sys
        _fm_yol = _fm_os.path.join(_fm_os.path.dirname(_fm_os.path.abspath(__file__)), "..", "file_manager", "file_manager.py")
        _fm_spec = _ilu.spec_from_file_location("kavram_file_manager", _fm_yol)
        _fm = _ilu.module_from_spec(_fm_spec)
        _fm_sys.modules["kavram_file_manager"] = _fm
        _fm_spec.loader.exec_module(_fm)
    except Exception:
        from PyQt5.QtWidgets import QFileDialog as _QFD

        class _fm:  # yedek: Qt diyaloğu
            ALL_FILES_LABEL = "Bütün Dosyalar (*)"

            @staticmethod
            def get_open_file_name(parent=None, caption="", directory="", filter="", initialFilter="",
                                   options=None, **_kw):
                return _QFD.getOpenFileName(parent, caption, directory, filter)

            @staticmethod
            def get_open_file_names(parent=None, caption="", directory="", filter="", initialFilter="",
                                    options=None, **_kw):
                return _QFD.getOpenFileNames(parent, caption, directory, filter)

            @staticmethod
            def get_save_file_name(parent=None, caption="", directory="", filter="", initialFilter="",
                                   options=None, **_kw):
                return _QFD.getSaveFileName(parent, caption, directory, filter)

            @staticmethod
            def get_existing_directory(parent=None, caption="", directory="", options=None, **_kw):
                return _QFD.getExistingDirectory(parent, caption, directory)

            @staticmethod
            def notify_saved(parent=None, text="Dosya kaydedildi.", msec=400):
                print(text)
# -----------------------------------------------------------------------------------


try:
    import soundfile as sf
    import numpy as np
    import noisereduce as nr
    import scipy.signal as sig
    import librosa
except ImportError:
    print("HATA: Gerekli kütüphaneler bulunamadı.")
    sys.exit(1)


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def _arac_bul(ad):
    """ffmpeg / ffprobe / ffplay: sistemde (PATH) kurulu olanı kullanır."""
    import shutil as _shutil
    return _shutil.which(ad) or ad


FFMPEG_PATH  = _arac_bul("ffmpeg")
FFPROBE_PATH = _arac_bul("ffprobe")
FFPLAY_PATH  = _arac_bul("ffplay")

if not os.path.isabs(FFMPEG_PATH):
    print("Uyarı: ffmpeg sistemde bulunamadı. Kurulum dosyasını (kurulum_deb.txt / kurulum_arch.txt) çalıştırın.")

def _tool_works(path):
    try:
        return subprocess.run([path, '-version'], capture_output=True, timeout=8).returncode == 0
    except Exception:
        return False


def _resolve_tool(path, name):
    """bin/ içindeki araç çalışmıyorsa (ör. 'libavdevice.so.63' eksik) sistemdeki aynı aracı kullanır."""
    if _tool_works(path):
        return path
    alt = shutil.which(name)
    if alt and os.path.abspath(alt) != os.path.abspath(path) and _tool_works(alt):
        print(f"Python Uyarı: {path} çalıştırılamadı (eksik kütüphane olabilir); sistemdeki '{alt}' kullanılacak.")
        return alt
    print(f"Python Uyarı: {path} çalıştırılamıyor ve sistemde çalışan '{name}' bulunamadı.\n"
          f"  Çözüm: kurulum_deb.txt / kurulum_arch.txt dosyasını çalıştırın (ffmpeg kurulur).")
    return path


FFMPEG_PATH  = _resolve_tool(FFMPEG_PATH,  "ffmpeg")
FFPROBE_PATH = _resolve_tool(FFPROBE_PATH, "ffprobe")
FFPLAY_PATH  = _resolve_tool(FFPLAY_PATH,  "ffplay")

VIDEO_FPS   = 12.0
AUDIO_RATE  = 48000

DEFAULT_BASE_DIR = _KAVRAM_EXPORT_DIR
SEGMENT_DIR      = os.path.join(_PROGRAM_DIR, 'v&s')
SETTINGS_FILE    = os.path.join(_KAVRAM_DIR, "filter", "filter_settings.json")
OVERLAY_SETTINGS_FILE = os.path.join(_PROGRAM_DIR, "rec_overlay.json")

# ---- Yerel (C++) motor: önizleme paylaşımlı bellek yolları ve kamera çözünürlükleri ----
_PV_DIR  = '/dev/shm' if os.path.isdir('/dev/shm') else tempfile.gettempdir()
_PV_BASE = os.path.join(_PV_DIR, f"kavram_{os.getuid()}_{os.getpid()}")
PV_SCREEN_PATH = _PV_BASE + "_screen.pv"
PV_CAMERA_PATH = _PV_BASE + "_camera.pv"
PV_AUDIO_PATH  = _PV_BASE + "_audio.lv"
CAMERA_RESOLUTIONS = {"360p": (640, 360), "480p": (640, 480), "720p": (1280, 720), "1080p": (1920, 1080)}
AUDIO_SOURCE_OVERRIDE = ""      # boş = otomatik (EasyEffects / varsayılan)


# =============================================================================
# Ortam / Oturum Tespiti ve C++ recorder yol bulucu
# =============================================================================
def detect_display_server() -> str:
    """
    X11 mi Wayland mı olduğunu döndürür.
    Öncelik: KAVRAM_DISPLAY_SERVER env > XDG_SESSION_TYPE/WAYLAND_DISPLAY > x11
    """
    force = os.environ.get('KAVRAM_DISPLAY_SERVER', '').strip().lower()
    if force in ('x11', 'wayland'):
        return force

    session_type = os.environ.get('XDG_SESSION_TYPE', '').strip().lower()
    if 'wayland' in session_type:
        return 'wayland'
    if os.environ.get('WAYLAND_DISPLAY'):
        return 'wayland'
    if 'x11' in session_type:
        return 'x11'
    # Son çare: X11 kabul et (XWayland da olabilir)
    return 'x11'


def get_camera_recorder_path() -> str | None:
    """
    C++ 'rec_engine' (rec klasöründeki derlenmiş çalıştırılabilir) dosyasını bulur.
    - rec/rec_engine (rec/derleme.txt ile derlenir)
    """
    candidates = [
        os.path.join(_PROGRAM_DIR, "rec_engine"),
    ]
    for c in candidates:
        try:
            if os.path.exists(c) and os.access(c, os.X_OK):
                return c
        except Exception:
            pass
    return None


def get_audio_source():
    if AUDIO_SOURCE_OVERRIDE:
        return AUDIO_SOURCE_OVERRIDE
    try:
        result = subprocess.run(['pactl', 'list', 'sources'],
                                capture_output=True, text=True, check=True, encoding='utf-8')
        for source_info in result.stdout.strip().split('Source #'):
            if 'easyeffects_sink.monitor' in source_info:
                for line in source_info.split('\n'):
                    if line.strip().startswith('Name:'):
                        src = line.split(':', 1)[1].strip()
                        print(f"Python: EasyEffects kaynağı: {src}")
                        return src
    except FileNotFoundError:
        if not getattr(get_audio_source, '_warned', False):
            get_audio_source._warned = True
            print("Python Uyarı: 'pactl' bulunamadı (EasyEffects kaynağı aranamadı). "
                  "Çözüm: sudo apt install pulseaudio-utils")
    except Exception as e:
        print(f"Python Uyarı: Ses kaynağı aranırken hata: {e}")
    if not getattr(get_audio_source, '_default_noted', False):
        get_audio_source._default_noted = True
        print("Python: Varsayılan ('default') ses kaynağı kullanılacak.")
    return 'default'


# =============================================================================
# FloatingOverlay – Süre + Play/Pause (alt pencere)
# =============================================================================
class FloatingOverlay(QWidget):
    """
    Kayıt sırasında ekranda hep üstte görünen süre paneli.
    • Siyah arka plan, beyaz yazı, yuvarlak köşeler
    • Ctrl + Sol Tık + Sürükle ile taşınır
    • InputOverlay bu pencerenin üstünde konumlanır
    """
    def __init__(self, recorder_window, thickness=40):
        super().__init__(
            None,
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.BypassWindowManagerHint
        )
        self.recorder_window = recorder_window
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.thickness = thickness
        
        self.setStyleSheet("""
            QWidget#overlay_root {
                background-color: rgba(0, 0, 0, 230);
                border: 1px solid #555555;
                border-radius: 8px;
            }
            QLabel {
                color: white;
                background: transparent;
                border: none;
            }
        """)

        self._root = QWidget(self)
        self._root.setObjectName("overlay_root")
        self._root.setGeometry(0, 0, 170, self.thickness)
        
        layout = QHBoxLayout(self._root)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)
        
        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet("font-size: 13px; color: white;")
        layout.addWidget(self.time_label)
        
        layout.addStretch()
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: white;")
        self.status_label.hide()
        layout.addWidget(self.status_label)
        
        self.setFixedSize(170, self.thickness)
        
        self._shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        self._shortcut.setContext(Qt.ApplicationShortcut)
        self._shortcut.activated.connect(self._trigger_play_pause)

        self._drag_active = False
        self._drag_offset = QPoint()

        screen = QApplication.desktop().screenGeometry()
        self.move(screen.right() - 190, screen.bottom() - self.thickness - 20)

    def set_thickness(self, value):
        self.thickness = value
        self.setFixedSize(170, self.thickness)
        self._root.setGeometry(0, 0, 170, self.thickness)

    def _trigger_play_pause(self):
        if self.recorder_window:
            self.recorder_window.main_play_pause_button.animateClick()

    def update_display(self, time_text: str, is_recording: bool, has_session: bool = True):
        self.time_label.setText(time_text)
        if not has_session:
            self.status_label.hide()
        elif is_recording:
            self.status_label.setText("Pause")
            self.status_label.show()
        else:
            self.status_label.setText("Play")
            self.status_label.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier):
            self._drag_active = True
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if getattr(self, '_drag_active', False) and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPos() - self._drag_offset)
            if self.recorder_window:
                self.recorder_window._update_input_overlay_position()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and getattr(self, '_drag_active', False):
            self._drag_active = False
            if self.recorder_window:
                pos = self.pos()
                self.recorder_window.overlay_default_pos = (pos.x(), pos.y())
                self.recorder_window.save_overlay_settings()
        super().mouseReleaseEvent(event)


# =============================================================================
# InputOverlay – Klavye/Mouse/Tablet input gösterimi (üst pencere)
# =============================================================================
class InputOverlay(QWidget):
    def __init__(self, recorder_window, thickness=40):
        super().__init__(
            None,
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.BypassWindowManagerHint
        )
        self.recorder_window = recorder_window
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.base_thickness = thickness
        self.current_lines = 0
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._do_hide)
        
        self._drag_active = False
        self._drag_offset = QPoint()
        
        self.setStyleSheet("""
            QWidget#input_root {
                background-color: rgba(0, 0, 0, 230);
                border: 1px solid #555555;
                border-radius: 8px;
            }
            QLabel {
                color: white;
                background: transparent;
                border: none;
            }
        """)

        self._root = QWidget(self)
        self._root.setObjectName("input_root")
        
        self.layout = QVBoxLayout(self._root)
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(2)
        
        self.input_label = QLabel("")
        self.input_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            color: white;
        """)
        self.input_label.setAlignment(Qt.AlignCenter)
        self.input_label.setWordWrap(True)
        self.layout.addWidget(self.input_label)
        
        self.setFixedSize(170, self.base_thickness)
        self._root.setGeometry(0, 0, 170, self.base_thickness)
        self.hide()

    def set_thickness(self, value):
        self.base_thickness = value
        if self.current_lines <= 1:
            self.setFixedSize(170, self.base_thickness)
            self._root.setGeometry(0, 0, 170, self.base_thickness)

    def show_input(self, text: str):
        if not text:
            self.hide_timer.start(1500)
            return
            
        self.hide_timer.stop()
        self.input_label.setText(text)
        
        fm = self.input_label.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        available_width = 170 - 20
        
        lines = max(1, min(5, (text_width // available_width) + 1))
        height_changed = (self.current_lines != lines)
        self.current_lines = lines
        
        height = self.base_thickness * lines
        if lines > 1:
            height += 4
        
        self.setFixedSize(170, height)
        self._root.setGeometry(0, 0, 170, height)
        self.show()

        if height_changed and self.recorder_window:
            self.recorder_window._update_input_overlay_position()

    def hide_input(self):
        self.hide_timer.stop()
        self._do_hide()

    def _do_hide(self):
        self.input_label.setText("")
        self.current_lines = 0
        self.setFixedSize(170, self.base_thickness)
        self._root.setGeometry(0, 0, 170, self.base_thickness)
        self.hide()

    def update_position(self, overlay_pos, overlay_thickness):
        self.move(overlay_pos.x(), overlay_pos.y() - self.height() - 4)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and (event.modifiers() & Qt.ControlModifier):
            self._drag_active = True
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if getattr(self, '_drag_active', False) and (event.buttons() & Qt.LeftButton):
            new_pos = event.globalPos() - self._drag_offset
            self.move(new_pos)
            if self.recorder_window:
                self.recorder_window._update_floating_overlay_from_input(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and getattr(self, '_drag_active', False):
            self._drag_active = False
            if self.recorder_window:
                self.recorder_window._save_overlay_positions_from_input()
        super().mouseReleaseEvent(event)


# =============================================================================
# InputSignaler – Thread-safe Sinyal Köprüsü
# =============================================================================
class InputSignaler(QObject):
    input_received = pyqtSignal(list)
    input_released = pyqtSignal(list)


# =============================================================================
# InputListener – Global klavye ve mouse dinleyici
# =============================================================================
class InputListener:
    def __init__(self, signaler: InputSignaler):
        self.signaler = signaler
        self.keyboard_listener = None
        self.mouse_listener = None
        self.running = False
        self._pressed_keys = set()
        self._pressed_buttons = set()
        self._lock = threading.Lock()
        
    def start(self):
        if not PYNPUT_AVAILABLE:
            print("Python: pynput mevcut değil, input dinleme başlatılamadı.")
            return False
            
        if self.running:
            return True
            
        try:
            self.keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            self.keyboard_listener.start()
            
            self.mouse_listener = mouse.Listener(
                on_click=self._on_mouse_click
            )
            self.mouse_listener.start()
            
            self.running = True
            print("Python: Input dinleyiciler başlatıldı.")
            return True
        except Exception as e:
            print(f"Python: Input dinleyici başlatılamadı: {e}")
            return False
            
    def stop(self):
        if self.keyboard_listener and self.running:
            try:
                self.keyboard_listener.stop()
            except Exception:
                pass
        if self.mouse_listener and self.running:
            try:
                self.mouse_listener.stop()
            except Exception:
                pass
        self.running = False
        self._pressed_keys.clear()
        self._pressed_buttons.clear()
        print("Python: Input dinleyiciler durduruldu.")
                
    def _on_key_press(self, key):
        try:
            with self._lock:
                key_name = self._get_key_name(key)
                if key_name and key_name not in self._pressed_keys:
                    self._pressed_keys.add(key_name)
                    if self.signaler:
                        self.signaler.input_received.emit(self._get_all_pressed())
        except Exception:
            pass
            
    def _on_key_release(self, key):
        try:
            with self._lock:
                key_name = self._get_key_name(key)
                if key_name and key_name in self._pressed_keys:
                    self._pressed_keys.discard(key_name)
                    if self.signaler:
                        self.signaler.input_released.emit(self._get_all_pressed())
        except Exception:
            pass
            
    def _on_mouse_click(self, x, y, button, pressed):
        try:
            with self._lock:
                button_name = self._get_mouse_button_name(button)
                if button_name:
                    if pressed:
                        self._pressed_buttons.add(button_name)
                        if self.signaler:
                            self.signaler.input_received.emit(self._get_all_pressed())
                    else:
                        self._pressed_buttons.discard(button_name)
                        if self.signaler:
                            self.signaler.input_released.emit(self._get_all_pressed())
        except Exception:
            pass
            
    def _get_all_pressed(self):
        all_pressed = list(self._pressed_keys) + list(self._pressed_buttons)
        return all_pressed
            
    def _get_mouse_button_name(self, button):
        try:
            if button == mouse.Button.left:
                return "🖱L"
            elif button == mouse.Button.right:
                return "🖱R"
            elif button == mouse.Button.middle:
                return "🖱M"
            elif hasattr(button, 'name'):
                if 'x1' in str(button).lower() or 'back' in str(button).lower():
                    return "🖱B"
                elif 'x2' in str(button).lower() or 'forward' in str(button).lower():
                    return "🖱F"
                return f"🖱{button.name[0].upper()}"
            return None
        except Exception:
            return None
            
    def _get_key_name(self, key):
        try:
            if key == keyboard.Key.ctrl or key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                return "Ctrl"
            elif key == keyboard.Key.alt or key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                return "Alt"
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                return "Shift"
            elif key == keyboard.Key.cmd or key == keyboard.Key.cmd_l or key == keyboard.Key.cmd_r:
                return "Super"
            elif key == keyboard.Key.caps_lock:
                return "Caps"
            elif key == keyboard.Key.tab:
                return "Tab"
            elif key == keyboard.Key.enter:
                return "Enter"
            elif key == keyboard.Key.backspace:
                return "⌫"
            elif key == keyboard.Key.delete:
                return "Del"
            elif key == keyboard.Key.esc:
                return "Esc"
            elif key == keyboard.Key.space:
                return "Space"
            elif key == keyboard.Key.up:
                return "↑"
            elif key == keyboard.Key.down:
                return "↓"
            elif key == keyboard.Key.left:
                return "←"
            elif key == keyboard.Key.right:
                return "→"
            elif key == keyboard.Key.home:
                return "Home"
            elif key == keyboard.Key.end:
                return "End"
            elif key == keyboard.Key.page_up:
                return "PgUp"
            elif key == keyboard.Key.page_down:
                return "PgDn"
            elif key == keyboard.Key.insert:
                return "Ins"
            elif key == keyboard.Key.print_screen:
                return "PrtSc"
            elif key == keyboard.Key.scroll_lock:
                return "ScrLk"
            elif key == keyboard.Key.pause:
                return "Pause"
            elif key == keyboard.Key.f1:
                return "F1"
            elif key == keyboard.Key.f2:
                return "F2"
            elif key == keyboard.Key.f3:
                return "F3"
            elif key == keyboard.Key.f4:
                return "F4"
            elif key == keyboard.Key.f5:
                return "F5"
            elif key == keyboard.Key.f6:
                return "F6"
            elif key == keyboard.Key.f7:
                return "F7"
            elif key == keyboard.Key.f8:
                return "F8"
            elif key == keyboard.Key.f9:
                return "F9"
            elif key == keyboard.Key.f10:
                return "F10"
            elif key == keyboard.Key.f11:
                return "F11"
            elif key == keyboard.Key.f12:
                return "F12"
            elif hasattr(key, 'char') and key.char:
                return key.char.upper()
            elif hasattr(key, 'name'):
                name = key.name
                if len(name) == 1:
                    return name.upper()
                return name.title()[:6]
            return None
        except Exception:
            return None
            
    def get_pressed(self):
        with self._lock:
            return self._get_all_pressed()


# =============================================================================
# BaseFFmpegRecorder
# =============================================================================
class BaseFFmpegRecorder(QThread):
    recording_started = pyqtSignal(str)
    recording_stopped = pyqtSignal(str)
    error_occurred    = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ffmpeg_process  = None
        self.running         = False
        self.ffmpeg_log_file = None

    def stop_process(self):
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            print(f"{self.__class__.__name__}: FFmpeg'e 'q' gönderiliyor...")
            try:
                self.ffmpeg_process.stdin.write(b'q\n')
                self.ffmpeg_process.stdin.flush()
                self.ffmpeg_process.communicate(timeout=10)
                print(f"{self.__class__.__name__}: FFmpeg nazikçe durdu. "
                      f"Kod: {self.ffmpeg_process.returncode}")
            except subprocess.TimeoutExpired:
                print(f"{self.__class__.__name__}: Zaman aşımı, zorla durduruluyor...")
                if hasattr(os, 'killpg') and platform.system() == "Linux":
                    try:
                        os.killpg(os.getpgid(self.ffmpeg_process.pid), signal.SIGKILL)
                    except Exception:
                        self.ffmpeg_process.kill()
                else:
                    self.ffmpeg_process.kill()
                self.ffmpeg_process.wait()
            except (IOError, ValueError) as e:
                print(f"{self.__class__.__name__}: 'q' gönderilemedi: {e}")
                if self.ffmpeg_process.poll() is None:
                    self.ffmpeg_process.kill()
                    self.ffmpeg_process.wait()
            self.ffmpeg_process = None
        self.running = False

    def run_command(self, command):
        try:
            self.ffmpeg_log_file = tempfile.TemporaryFile(mode='w+', encoding='utf-8')
            kwargs = {'stdin': subprocess.PIPE, 'stdout': subprocess.PIPE,
                      'stderr': self.ffmpeg_log_file}
            if platform.system() == "Linux":
                kwargs['preexec_fn'] = os.setsid
            print(f"{self.__class__.__name__}: {' '.join(command)}")
            self.ffmpeg_process = subprocess.Popen(command, **kwargs)
            self.running = True
            self.ffmpeg_process.wait()
            if self.running and self.ffmpeg_process.returncode not in (0, 255):
                self.ffmpeg_log_file.seek(0)
                self.error_occurred.emit(
                    f"FFmpeg hata kodu {self.ffmpeg_process.returncode}:\n"
                    f"{self.ffmpeg_log_file.read()}")
        except FileNotFoundError:
            self.error_occurred.emit(
                "FFmpeg bulunamadı (sudo apt install ffmpeg).")
        except Exception as e:
            self.error_occurred.emit(f"{self.__class__.__name__}: {e}")
            traceback.print_exc()
        finally:
            self.running = False
            if self.ffmpeg_log_file:
                self.ffmpeg_log_file.close()
                self.ffmpeg_log_file = None
            self.recording_stopped.emit(f"{self.__class__.__name__} durduruldu.")


# =============================================================================
# ScreenRecorder  –  Sadece video (MKV) [X11 - ffmpeg x11grab]
# =============================================================================
class ScreenRecorder(BaseFFmpegRecorder):
    def __init__(self, output_dir, start_number=1, fps=VIDEO_FPS, segment_time=60,
                 parent=None, resolution="480p"):
        super().__init__(parent)
        self.output_dir   = output_dir
        self.start_number = start_number
        self.fps          = fps
        self.segment_time = segment_time
        self.resolution   = resolution

    def run(self):
        screen_geo = QApplication.desktop().screenGeometry()
        out_pattern = os.path.join(self.output_dir, "s%d.mkv")

        resolution_map = {"1080p": "1920x1080", "720p": "1280x720",
                          "480p": "854x480",    "360p": "640x360"}
        res_str = resolution_map.get(self.resolution, "854x480")
        rw, rh  = map(int, res_str.split('x'))
        if rw > screen_geo.width() or rh > screen_geo.height():
            sf_    = min(screen_geo.width() / rw, screen_geo.height() / rh)
            rw     = (int(rw * sf_) // 2) * 2
            rh     = (int(rh * sf_) // 2) * 2
            res_str = f"{rw}x{rh}"

        fps_val          = int(self.fps)
        keyframe_interval = fps_val

        display = os.environ.get('DISPLAY', ':0.0')
        if display.startswith(':'):
            display = display.split('.')[0]

        command = [
            FFMPEG_PATH, '-y',
            '-threads', '1',
            '-f', 'x11grab',
            '-framerate', str(fps_val),
            '-s', res_str,
            '-i', display,
            '-c:v', 'libx264', '-preset', 'ultrafast',
            '-crf', '25', '-pix_fmt', 'yuv420p',
            '-g', str(keyframe_interval),
            '-sc_threshold', '0',
            '-fps_mode', 'cfr',
            '-map', '0',
            '-f', 'segment',
            '-segment_time', str(self.segment_time),
            '-segment_start_number', str(self.start_number),
            '-reset_timestamps', '1',
            '-segment_format', 'matroska',
            out_pattern
        ]
        self.recording_started.emit("Ekran kaydı başlatıldı (MKV).")
        self.run_command(command)


# =============================================================================
# AudioRecorder  –  Sadece ses (WAV)
# =============================================================================
class AudioRecorder(BaseFFmpegRecorder):
    def __init__(self, output_dir, start_number=1, segment_time=60, parent=None, audio_rate=48000):
        super().__init__(parent)
        self.output_dir   = output_dir
        self.start_number = start_number
        self.segment_time = segment_time
        self.audio_rate   = audio_rate

    def run(self):
        audio_src   = get_audio_source()
        out_pattern = os.path.join(self.output_dir, "s%d.wav")

        command = [
            FFMPEG_PATH, '-y',
            '-threads', '1',
            '-f', 'pulse',
            '-i', audio_src,
            '-c:a', 'pcm_s16le',
            '-ar', str(self.audio_rate),
            '-map', '0',
            '-f', 'segment',
            '-segment_time', str(self.segment_time),
            '-segment_start_number', str(self.start_number),
            '-reset_timestamps', '1',
            '-segment_format', 'wav',
            out_pattern
        ]
        self.recording_started.emit("Ses kaydı başlatıldı (WAV).")
        self.run_command(command)


# =============================================================================
# CombinedRecorder  –  Video + Ses (MKV) [X11 - ffmpeg x11grab + pulse]
# =============================================================================
class CombinedRecorder(BaseFFmpegRecorder):
    def __init__(self, output_dir, start_number=1, fps=VIDEO_FPS, segment_time=60,
                 parent=None, resolution="480p", audio_rate=48000):
        super().__init__(parent)
        self.output_dir   = output_dir
        self.start_number = start_number
        self.fps          = fps
        self.segment_time = segment_time
        self.resolution   = resolution
        self.audio_rate   = audio_rate

    def run(self):
        screen_geo  = QApplication.desktop().screenGeometry()
        audio_src   = get_audio_source()
        out_pattern = os.path.join(self.output_dir, "s%d.mkv")

        resolution_map = {"1080p": "1920x1080", "720p": "1280x720",
                          "480p": "854x480",    "360p": "640x360"}
        res_str = resolution_map.get(self.resolution, "854x480")
        rw, rh  = map(int, res_str.split('x'))
        if rw > screen_geo.width() or rh > screen_geo.height():
            sf_     = min(screen_geo.width() / rw, screen_geo.height() / rh)
            rw      = (int(rw * sf_) // 2) * 2
            rh      = (int(rh * sf_) // 2) * 2
            res_str = f"{rw}x{rh}"

        fps_val           = int(self.fps)
        keyframe_interval = fps_val

        display = os.environ.get('DISPLAY', ':0.0')
        if display.startswith(':'):
            display = display.split('.')[0]

        command = [
            FFMPEG_PATH, '-y',
            '-threads', '1',
            '-f', 'x11grab',
            '-framerate', str(fps_val),
            '-s', res_str,
            '-i', display,
            '-f', 'pulse',
            '-i', audio_src,
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-c:v', 'libx264', '-preset', 'ultrafast',
            '-crf', '25', '-pix_fmt', 'yuv420p',
            '-g', str(keyframe_interval),
            '-sc_threshold', '0',
            '-c:a', 'aac', '-b:a', '128k', '-ar', str(self.audio_rate),
            '-fps_mode', 'cfr',
            '-f', 'segment',
            '-segment_time', str(self.segment_time),
            '-segment_start_number', str(self.start_number),
            '-reset_timestamps', '1',
            '-segment_format', 'matroska',
            out_pattern
        ]
        self.recording_started.emit("Birleşik kayıt başlatıldı (MKV).")
        self.run_command(command)


# =============================================================================
# WaylandScreenRecorder  –  Sadece video (Wayland + Portal + PipeWire + C++)
#
# C++ 'camera_recorder --record-wayland' sürecini çağırır.
# C++ tarafı portal izni alır, PipeWire node id'sini alır, GStreamer
# pipeline'ını başlatır ve s%d.mkv segmentlerini üretir.
# =============================================================================
class WaylandScreenRecorder(QThread):
    recording_started = pyqtSignal(str)
    recording_stopped = pyqtSignal(str)
    error_occurred    = pyqtSignal(str)

    def __init__(self, camera_recorder_path, output_dir,
                 start_number=1, fps=12, segment_time=60,
                 width=854, height=480, parent=None):
        super().__init__(parent)
        self.camera_recorder_path = camera_recorder_path
        self.output_dir   = output_dir
        self.start_number = start_number
        self.fps          = fps
        self.segment_time = segment_time
        self.width        = width
        self.height       = height

        self.process = None
        self._process_lock = threading.RLock()
        self.stdout_log_file = None
        self.stderr_log_file = None
        self.running = False

    def run(self):
        proc = None
        try:
            cmd = [
                self.camera_recorder_path,
                "--record-wayland",
                self.output_dir,
                str(self.start_number),
                str(self.segment_time),
                str(int(self.fps)),
                str(int(self.width)),
                str(int(self.height)),
            ]
            print(f"{self.__class__.__name__}: {' '.join(cmd)}")
            self.stdout_log_file = tempfile.TemporaryFile(mode='w+b')
            self.stderr_log_file = tempfile.TemporaryFile(mode='w+b')

            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=self.stdout_log_file,
                stderr=self.stderr_log_file,
                preexec_fn=os.setsid if platform.system() == "Linux" else None,
            )
            with self._process_lock:
                self.process = proc
                self.running = True

            self.recording_started.emit("Wayland ekran kaydı başlatıldı (Portal).")
            proc.wait()

            if self.running and proc.returncode not in (0, -signal.SIGINT, 130):
                try:
                    self.stderr_log_file.seek(0)
                    err = self.stderr_log_file.read().decode('utf-8', errors='replace')
                except Exception:
                    err = ""
                self.error_occurred.emit(
                    f"Wayland kayıt hatası (kod {proc.returncode}):\n{err[-2000:]}"
                )
        except FileNotFoundError:
            self.error_occurred.emit(
                f"camera_recorder bulunamadı: {self.camera_recorder_path}"
            )
        except Exception as e:
            self.error_occurred.emit(f"{self.__class__.__name__}: {e}")
            traceback.print_exc()
        finally:
            with self._process_lock:
                self.running = False
                if self.process is proc:
                    self.process = None
            for log_file_name in ("stdout_log_file", "stderr_log_file"):
                log_file = getattr(self, log_file_name, None)
                if log_file:
                    try:
                        log_file.close()
                    except Exception:
                        pass
                    setattr(self, log_file_name, None)
            self.recording_stopped.emit(f"{self.__class__.__name__} durduruldu.")

    def stop_process(self):
        with self._process_lock:
            self.running = False
            proc = self.process
        if proc and proc.poll() is None:
            print(f"{self.__class__.__name__}: C++ recorder'a SIGINT gönderiliyor...")
            try:
                # C++ tarafı SIGINT ile GMainLoop'u kırar ve EOS gönderir
                proc.send_signal(signal.SIGINT)
                proc.wait(timeout=12)
                print(f"{self.__class__.__name__}: Recorder nazikçe durdu. "
                      f"Kod: {proc.returncode}")
            except subprocess.TimeoutExpired:
                print(f"{self.__class__.__name__}: Zaman aşımı, zorla durduruluyor...")
                try:
                    if platform.system() == "Linux":
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    else:
                        proc.terminate()
                    proc.wait(timeout=4)
                except Exception:
                    try:
                        proc.kill()
                        proc.wait(timeout=3)
                    except Exception:
                        pass
            except Exception as e:
                print(f"{self.__class__.__name__}: Durdurma hatası: {e}")
                try:
                    proc.kill()
                except Exception:
                    pass
        with self._process_lock:
            if self.process is proc:
                self.process = None


# =============================================================================
# WaylandCombinedRecorder  –  Video (Wayland) + Ses (ffmpeg pulse)
#
# C++ Wayland recorder'ı video için, ayrı bir ffmpeg sürecini de ses
# için çalıştırır. İki süreç de aynı segment_time / start_number ile
# segment üretir; dışa aktarımda birleştirilir.
# =============================================================================
class WaylandCombinedRecorder(QThread):
    recording_started = pyqtSignal(str)
    recording_stopped = pyqtSignal(str)
    error_occurred    = pyqtSignal(str)

    def __init__(self, camera_recorder_path, output_dir,
                 start_number=1, fps=12, segment_time=60,
                 width=854, height=480, audio_rate=48000, parent=None):
        super().__init__(parent)
        self.camera_recorder_path = camera_recorder_path
        self.output_dir   = output_dir
        self.start_number = start_number
        self.fps          = fps
        self.segment_time = segment_time
        self.width        = width
        self.height       = height
        self.audio_rate   = audio_rate

        self.video_process = None
        self.audio_process = None
        self.audio_log_file = None
        self.running = False
        self._process_lock = threading.RLock()

    def run(self):
        video_proc = None
        audio_proc = None
        try:
            # --- Video (C++ Wayland) ---
            video_cmd = [
                self.camera_recorder_path,
                "--record-wayland",
                self.output_dir,
                str(self.start_number),
                str(self.segment_time),
                str(int(self.fps)),
                str(int(self.width)),
                str(int(self.height)),
            ]
            print(f"{self.__class__.__name__} (video): {' '.join(video_cmd)}")

            # PIPE kullanmak yerine geçici dosyaya yazıyoruz. Böylece uzun kayıtta
            # stdout/stderr tamponunun dolup C++ sürecini kilitlemesi engellenir.
            video_stdout = tempfile.TemporaryFile(mode='w+b')
            video_stderr = tempfile.TemporaryFile(mode='w+b')
            try:
                video_proc = subprocess.Popen(
                    video_cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=video_stdout,
                    stderr=video_stderr,
                    preexec_fn=os.setsid if platform.system() == "Linux" else None,
                )
            except Exception:
                video_stdout.close()
                video_stderr.close()
                raise

            with self._process_lock:
                self.video_process = video_proc

            # --- Ses (ffmpeg pulse) ---
            audio_src   = get_audio_source()
            out_pattern = os.path.join(self.output_dir, "s%d.wav")
            self.audio_log_file = tempfile.TemporaryFile(mode='w+', encoding='utf-8')
            audio_cmd = [
                FFMPEG_PATH, '-y',
                '-threads', '1',
                '-f', 'pulse',
                '-i', audio_src,
                '-c:a', 'pcm_s16le',
                '-ar', str(self.audio_rate),
                '-map', '0',
                '-f', 'segment',
                '-segment_time', str(self.segment_time),
                '-segment_start_number', str(self.start_number),
                '-reset_timestamps', '1',
                '-segment_format', 'wav',
                out_pattern
            ]
            print(f"{self.__class__.__name__} (audio): {' '.join(audio_cmd)}")
            audio_kwargs = {
                'stdin': subprocess.PIPE,
                'stdout': subprocess.DEVNULL,
                'stderr': self.audio_log_file,
            }
            if platform.system() == "Linux":
                audio_kwargs['preexec_fn'] = os.setsid
            audio_proc = subprocess.Popen(audio_cmd, **audio_kwargs)

            with self._process_lock:
                self.audio_process = audio_proc
                self.running = True

            self.recording_started.emit("Wayland ekran + ses kaydı başlatıldı.")

            # Video süreci bitene kadar bekle. Yerel process referansları kullanılıyor;
            # stop_process() bunları self.* üzerinden temizlese bile burada None'a dönüşmez.
            video_proc.wait()

            if audio_proc.poll() is None:
                self._stop_audio(audio_proc)

            if self.running and video_proc.returncode not in (0, -signal.SIGINT, 130):
                try:
                    video_stderr.seek(0)
                    err = video_stderr.read().decode('utf-8', errors='replace')
                except Exception:
                    err = ""
                self.error_occurred.emit(
                    f"Wayland kayıt hatası (kod {video_proc.returncode}):\n{err[-4000:]}"
                )

        except FileNotFoundError:
            self.error_occurred.emit(
                f"camera_recorder bulunamadı: {self.camera_recorder_path}"
            )
        except Exception as e:
            self.error_occurred.emit(f"{self.__class__.__name__}: {e}")
            traceback.print_exc()
        finally:
            with self._process_lock:
                self.running = False

            # Hangi süreç stop_process tarafından zaten durdurulmuş olursa olsun,
            # yerel referans ile güvenli biçimde sonlandır.
            if audio_proc is not None:
                self._stop_audio(audio_proc)

            for proc_name, proc in (("video_process", video_proc),):
                if proc is not None:
                    try:
                        if proc.poll() is None:
                            if platform.system() == "Linux":
                                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                            else:
                                proc.terminate()
                            proc.wait(timeout=3)
                    except Exception:
                        try:
                            if proc.poll() is None:
                                proc.kill()
                                proc.wait(timeout=3)
                        except Exception:
                            pass

            if self.audio_log_file:
                try:
                    self.audio_log_file.close()
                except Exception:
                    pass
                self.audio_log_file = None

            with self._process_lock:
                if self.video_process is video_proc:
                    self.video_process = None
                if self.audio_process is audio_proc:
                    self.audio_process = None

            for log_file in (locals().get('video_stdout'), locals().get('video_stderr')):
                if log_file:
                    try:
                        log_file.close()
                    except Exception:
                        pass

            self.recording_stopped.emit(f"{self.__class__.__name__} durduruldu.")

    def _stop_audio(self, proc=None):
        if proc is None:
            with self._process_lock:
                proc = self.audio_process

        if proc and proc.poll() is None:
            try:
                proc.stdin.write(b'q\n')
                proc.stdin.flush()
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    if platform.system() == "Linux":
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    else:
                        proc.kill()
                    proc.wait(timeout=3)
                except Exception:
                    pass
            except (IOError, ValueError, BrokenPipeError):
                if proc.poll() is None:
                    try:
                        proc.kill()
                        proc.wait(timeout=3)
                    except Exception:
                        pass
            except Exception:
                try:
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait(timeout=3)
                except Exception:
                    pass

        with self._process_lock:
            if self.audio_process is proc:
                self.audio_process = None

    def stop_process(self):
        with self._process_lock:
            self.running = False
            audio_proc = self.audio_process
            video_proc = self.video_process

        # Önce sesi kapat; WAV segmenti düzgün finalize edilsin.
        self._stop_audio(audio_proc)

        # Sonra C++ Wayland recorder'a SIGINT gönder; C++ tarafı EOS ile kapatır.
        if video_proc and video_proc.poll() is None:
            print(f"{self.__class__.__name__}: C++ recorder'a SIGINT gönderiliyor...")
            try:
                video_proc.send_signal(signal.SIGINT)
                video_proc.wait(timeout=12)
                print(
                    f"{self.__class__.__name__}: Recorder nazikçe durdu. "
                    f"Kod: {video_proc.returncode}"
                )
            except subprocess.TimeoutExpired:
                print(f"{self.__class__.__name__}: Zaman aşımı, zorla durduruluyor...")
                try:
                    if platform.system() == "Linux":
                        os.killpg(os.getpgid(video_proc.pid), signal.SIGTERM)
                    else:
                        video_proc.terminate()
                    video_proc.wait(timeout=4)
                except Exception:
                    try:
                        video_proc.kill()
                        video_proc.wait(timeout=3)
                    except Exception:
                        pass
            except Exception as e:
                print(f"{self.__class__.__name__}: Video durdurma hatası: {e}")
                try:
                    if video_proc.poll() is None:
                        video_proc.kill()
                        video_proc.wait(timeout=3)
                except Exception:
                    pass


# =============================================================================
# Yardımcı pencereler
# =============================================================================
class CameraFeatureWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Feature")
        self.setGeometry(200, 200, 400, 150)
        layout = QVBoxLayout(self)
        lbl = QLabel("Bu fonksiyon geliştirme aşamasındadır.")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)
        self.setStyleSheet("background-color: #383838; color: white; font-size: 16px;")


# =============================================================================
# PlaybackSlider
# =============================================================================
class PlaybackSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.red_line_position = 0
        self.setMinimum(0); self.setMaximum(100)
        self.setSingleStep(1); self.setPageStep(10)
        self.setTracking(True)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.red_line_position >= 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            gr = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self)
            if self.orientation() == Qt.Horizontal:
                x = gr.left() + gr.width() * self.red_line_position / 100
                x = max(gr.left(), min(x, gr.right()))
                cy = gr.center().y()
                painter.setPen(QPen(QColor(255, 0, 0), 2))
                painter.drawLine(int(x), int(cy - 5), int(x), int(cy + 5))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            gr = self.style().subControlRect(QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self)
            if self.orientation() == Qt.Horizontal:
                ratio = (event.pos().x() - gr.left()) / gr.width()
                val   = self.minimum() + (self.maximum() - self.minimum()) * ratio
                self.setValue(int(val))
                self.sliderMoved.emit(int(val))
        super().mousePressEvent(event)


# =============================================================================
# ThicknessButton – Kalınlık ayar butonu
# =============================================================================
class ThicknessButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.thickness = 40
        self.setText("40")
        self.setFixedSize(40, 30)
        self.setToolTip("Kalınlık (30-50)\nSol Tık: Varsayılan konuma git\nSağ Tık: Mevcut konumu varsayılan yap\nFare Tekerleği: Değiştir")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        
    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self.thickness = min(50, self.thickness + 1)
        else:
            self.thickness = max(30, self.thickness - 1)
        self.setText(str(self.thickness))
        if self.parent_window:
            self.parent_window.set_overlay_thickness(self.thickness)
            self.parent_window.save_overlay_settings()


# =============================================================================
# Yerel (C++) motor yardımcıları  –  camera_recorder --record / --preview
#
# PyQt yalnızca arayüzü ve bağlantıları yönetir; kayıt ve önizleme C++ tarafındadır.
# Önizleme kareleri /dev/shm üzerindeki küçük bir paylaşımlı bellekten okunur
# (boru/dosya trafiği yok -> eski bilgisayarlarda bile akıcı).
# =============================================================================
def native_capabilities(binary_path):
    """camera_recorder --capabilities çıktısını sözlük olarak döndürür. Eski ikili dosyada {} döner."""
    if not binary_path:
        return {}
    try:
        r = subprocess.run([binary_path, '--capabilities'], capture_output=True,
                           text=True, timeout=8)
        if r.returncode != 0:
            return {}
        caps = {}
        for line in r.stdout.splitlines():
            if '=' in line:
                k, v = line.split('=', 1)
                caps[k.strip()] = v.strip()
        if caps.get('engine', '0').isdigit() and int(caps['engine']) >= 1:
            return caps
    except Exception as e:
        print(f"Python Uyarı: camera_recorder --capabilities okunamadı: {e}")
    return {}


def list_cameras(binary_path):
    """[(yol, ad), ...] döndürür."""
    cams = []
    if not binary_path:
        return cams
    try:
        r = subprocess.run([binary_path, '--list-cameras'], capture_output=True,
                           text=True, timeout=6)
        for line in r.stdout.splitlines():
            if '|' in line:
                p, n = line.split('|', 1)
                cams.append((p.strip(), n.strip()))
    except Exception as e:
        print(f"Python Uyarı: kamera listesi alınamadı: {e}")
    return cams


def list_audio_sources():
    """[(ad, monitor_mu), ...] döndürür (pactl list short sources)."""
    out = []
    try:
        r = subprocess.run(['pactl', 'list', 'short', 'sources'], capture_output=True,
                           text=True, timeout=4)
        for line in r.stdout.splitlines():
            parts = line.split('\t')
            if len(parts) >= 2:
                name = parts[1].strip()
                out.append((name, name.endswith('.monitor')))
    except Exception as e:
        print(f"Python Uyarı: ses kaynakları listelenemedi: {e}")
    return out


class ShmReader:
    """C++ motorunun yazdığı paylaşımlı bellek dosyasını (seqlock) okur."""
    VHDR = struct.Struct('<6IQQ2I')      # 48 bayt (başlık 64 bayt, veri 64'ten başlar)
    LHDR = struct.Struct('<IIQQ4fI')
    VMAGIC = 0x5650564B
    LMAGIC = 0x564C564B

    def __init__(self, path, kind='video'):
        self.path = path
        self.kind = kind
        self.mm = None
        self.last_seq = -1
        self._ino = None
        self._idle = 0

    def reset(self):
        if self.mm is not None:
            try:
                self.mm.close()
            except Exception:
                pass
        self.mm = None
        self.last_seq = -1
        self._idle = 0

    def _check_stale(self):
        """Motor yeniden başlatıldıysa dosya yenilenir; eski eşlemeyi bırak."""
        try:
            if os.stat(self.path).st_ino != self._ino:
                self.reset()
        except OSError:
            self.reset()

    def _open(self):
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        except OSError:
            return False
        try:
            st = os.fstat(fd)
            size = st.st_size
            self._ino = st.st_ino
            if size < 48:
                return False
            self.mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        except Exception:
            self.mm = None
            return False
        finally:
            os.close(fd)
        magic = struct.unpack_from('<I', self.mm, 0)[0]
        want = self.VMAGIC if self.kind == 'video' else self.LMAGIC
        if magic != want:
            self.reset()
            return False
        return True

    def read_frame(self):
        """Yeni kare varsa QImage (RGB32) döndürür, yoksa None."""
        if self.mm is None and not self._open():
            return None
        try:
            (magic, ver, w, h, stride, fmt, seq, stamp, payload, cap) = self.VHDR.unpack_from(self.mm, 0)
            if seq == self.last_seq:
                self._idle += 1
                if self._idle % 20 == 0:
                    self._check_stale()
                return None
            self._idle = 0
            if magic != self.VMAGIC or (seq & 1) or w == 0 or h == 0:
                return None
            if payload <= 0 or payload > cap or stride * h > payload + stride:
                return None
            data = self.mm[64:64 + payload]
            if struct.unpack_from('<Q', self.mm, 24)[0] != seq:
                return None            # yazma sırasında okundu, bu kareyi atla
            self.last_seq = seq
            img = QImage(data, w, h, stride, QImage.Format_RGB32)
            img._kv_data = data         # arabelleği QImage ile birlikte canlı tut
            return img
        except Exception:
            self.reset()
            return None

    def read_levels(self):
        """(peak_l, peak_r, rms_l, rms_r) dB cinsinden ya da None."""
        if self.mm is None and not self._open():
            return None
        try:
            (magic, ver, seq, stamp, pl, pr, rl, rr, ch) = self.LHDR.unpack_from(self.mm, 0)
            if magic != self.LMAGIC or (seq & 1):
                return None
            return (pl, pr, rl, rr)
        except Exception:
            self.reset()
            return None


# =============================================================================
# NativeEngine – C++ motor sürecini yöneten iş parçacığı (kayıt ya da önizleme)
#
# BaseFFmpegRecorder / Wayland* sınıflarıyla aynı sinyalleri kullanır; böylece
# mevcut bağlantılar (recording_started/stopped/error_occurred) aynen çalışır.
# =============================================================================
class NativeEngine(QThread):
    recording_started = pyqtSignal(str)
    recording_stopped = pyqtSignal(str)
    error_occurred    = pyqtSignal(str)
    finished_code     = pyqtSignal(int, str)

    def __init__(self, camera_recorder_path, args, preview_only=False, parent=None):
        super().__init__(parent)
        self.camera_recorder_path = camera_recorder_path
        self.args = list(args)
        self.preview_only = preview_only
        self.running = False
        self._proc = None
        self._stopping = False
        self._lock = threading.RLock()

    @staticmethod
    def _friendly(code, err_text):
        lines = [l for l in err_text.splitlines() if l.strip()]
        hata = [l for l in lines if 'Hata' in l or 'hata' in l]
        detail = (hata[-1] if hata else (lines[-1] if lines else "")).replace("C++ Hata: ", "")
        if code == 3:
            return "Ekran paylaşımı iptal edildi veya izin verilmedi."
        if code == 2:
            return f"Kamera açılamadı.\n{detail}"
        if code == 4:
            return f"Ses kaynağı açılamadı.\n{detail}"
        if code == 5:
            return detail or "Eksik GStreamer eklentisi."
        return f"Kayıt motoru hatası (kod {code}):\n{err_text[-1500:]}"

    def run(self):
        proc = None
        err_file = tempfile.TemporaryFile(mode='w+b')
        try:
            with self._lock:
                if self._stopping:
                    return
            cmd = [self.camera_recorder_path] + self.args
            print(f"{self.__class__.__name__}: {' '.join(cmd)}")
            proc = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err_file,
                preexec_fn=os.setsid if platform.system() == "Linux" else None)
            with self._lock:
                self._proc = proc
                self.running = True
                stop_now = self._stopping
            if stop_now:
                proc.send_signal(signal.SIGINT)

            for raw in iter(proc.stdout.readline, b''):
                line = raw.decode('utf-8', errors='replace').strip()
                if line == 'EVENT ready':
                    self.recording_started.emit("Yerel motor hazır.")
            proc.wait()

            code = proc.returncode
            try:
                err_file.seek(0)
                err_text = err_file.read().decode('utf-8', errors='replace')
            except Exception:
                err_text = ""
            msg = "" if code in (0, -signal.SIGINT, 130, -signal.SIGTERM) else self._friendly(code, err_text)
            self.finished_code.emit(code, msg)
            if msg and not self._stopping and not self.preview_only:
                self.error_occurred.emit(msg)
        except FileNotFoundError:
            self.finished_code.emit(1, "camera_recorder bulunamadı.")
            if not self.preview_only:
                self.error_occurred.emit(f"camera_recorder bulunamadı: {self.camera_recorder_path}")
        except Exception as e:
            self.finished_code.emit(1, str(e))
            if not self.preview_only:
                self.error_occurred.emit(f"{self.__class__.__name__}: {e}")
            traceback.print_exc()
        finally:
            with self._lock:
                self.running = False
                self._proc = None
            try:
                err_file.close()
            except Exception:
                pass
            self.recording_stopped.emit(f"{self.__class__.__name__} durduruldu.")

    def send_command(self, command: str):
        """C++ motoruna satır komutu gönderir (PAUSE / RESUME)."""
        with self._lock:
            proc = self._proc
        if proc and proc.poll() is None and proc.stdin:
            try:
                proc.stdin.write((command + "\n").encode())
                proc.stdin.flush()
            except Exception as e:
                print(f"NativeEngine: komut gönderilemedi ({command}): {e}")

    def pause(self):
        self.send_command("PAUSE")

    def resume(self):
        self.send_command("RESUME")

    def send_preview(self, enabled: bool):
        """Kayıt sürerken önizlemeyi aç/kapat (SIGUSR1/SIGUSR2) – kapalıyken işlemci harcamaz."""
        with self._lock:
            proc = self._proc
        if proc and proc.poll() is None:
            try:
                proc.send_signal(signal.SIGUSR1 if enabled else signal.SIGUSR2)
            except Exception:
                pass

    def stop_process(self, timeout=12):
        with self._lock:
            self._stopping = True
            proc = self._proc
        if proc and proc.poll() is None:
            print(f"{self.__class__.__name__}: C++ motoruna SIGINT gönderiliyor...")
            try:
                proc.send_signal(signal.SIGINT)
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                print(f"{self.__class__.__name__}: Zaman aşımı, zorla durduruluyor...")
                try:
                    if platform.system() == "Linux":
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    else:
                        proc.terminate()
                    proc.wait(timeout=4)
                except Exception:
                    try:
                        proc.kill()
                        proc.wait(timeout=3)
                    except Exception:
                        pass
            except Exception as e:
                print(f"{self.__class__.__name__}: Durdurma hatası: {e}")
                try:
                    proc.kill()
                except Exception:
                    pass


# =============================================================================
# InfoPreviewLabel – ortadaki büyük alan: ekran önizlemesi
# Mevcut info_label'ın yerini alır; önizleme kapalıyken tamamen eski QLabel gibi davranır
# (setText/show/hide çağrıları aynen çalışır).
# =============================================================================
class InfoPreviewLabel(QLabel):
    def __init__(self, text, path, parent=None):
        super().__init__(text, parent)
        self.reader = ShmReader(path, 'video')
        self.image = None
        self.preview_on = False
        self.recording = False
        self.timer = QTimer(self)
        self.timer.setInterval(66)
        self.timer.timeout.connect(self._poll)

    def set_preview(self, on):
        if on == self.preview_on:
            return
        self.preview_on = on
        if on:
            self.timer.start()
        else:
            self.timer.stop()
            self.reader.reset()
            self.image = None
        self.update()

    def set_recording(self, rec):
        if rec != self.recording:
            self.recording = rec
            self.update()

    def reset_frame(self):
        self.reader.reset()
        self.image = None
        self.update()

    def _poll(self):
        if not self.isVisible():
            return
        img = self.reader.read_frame()
        if img is not None:
            self.image = img
            self.update()

    def paintEvent(self, event):
        if not (self.preview_on and self.image is not None and not self.image.isNull()):
            super().paintEvent(event)
            return
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0))
        iw, ih = self.image.width(), self.image.height()
        scale = min(self.width() / iw, self.height() / ih)
        tw, th = max(1, int(iw * scale)), max(1, int(ih * scale))
        p.drawImage(QRect((self.width() - tw) // 2, (self.height() - th) // 2, tw, th), self.image)
        if self.recording:
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setBrush(QColor(255, 68, 68))
            p.setPen(Qt.NoPen)
            p.drawEllipse(self.width() - 22, 10, 11, 11)


# =============================================================================
# AudioMeter – ince stereo ses seviyesi çubuğu
# =============================================================================
class AudioMeter(QWidget):
    FLOOR_DB = -60.0

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.reader = ShmReader(path, 'level')
        self.levels = [self.FLOOR_DB, self.FLOOR_DB]
        self.setFixedHeight(16)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def reset(self):
        self.reader.reset()
        self.levels = [self.FLOOR_DB, self.FLOOR_DB]
        self.update()

    def poll(self):
        lv = self.reader.read_levels()
        new = [self.FLOOR_DB, self.FLOOR_DB]
        if lv:
            new = [max(self.FLOOR_DB, lv[0]), max(self.FLOOR_DB, lv[1])]
        changed = False
        for i in range(2):
            cur = max(new[i], self.levels[i] - 4.0)      # yumuşak düşüş
            if abs(cur - self.levels[i]) > 0.2:
                changed = True
            self.levels[i] = cur
        if changed:
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(17, 17, 17))
        label_w = 34
        p.setPen(QColor(170, 170, 170))
        f = QFont(p.font())
        f.setPixelSize(11)
        p.setFont(f)
        p.drawText(QRect(4, 0, label_w, self.height()), Qt.AlignVCenter | Qt.AlignLeft, "Ses")
        x0, x1 = label_w + 6, self.width() - 6
        if x1 <= x0:
            return
        bar_h = 5
        for i, y in enumerate((2, self.height() - bar_h - 2)):
            p.fillRect(QRect(x0, y, x1 - x0, bar_h), QColor(50, 50, 50))
            frac = (self.levels[i] - self.FLOOR_DB) / (-self.FLOOR_DB)
            frac = max(0.0, min(1.0, frac))
            w = int((x1 - x0) * frac)
            if w > 0:
                color = QColor(76, 175, 80) if frac < 0.75 else (QColor(255, 193, 7) if frac < 0.92 else QColor(244, 67, 54))
                p.fillRect(QRect(x0, y, w, bar_h), color)


# =============================================================================
# AudioPanel – alt panel: yalnızca ses dalgalanması (seviye çubuğu)
# =============================================================================
class AudioPanel(QFrame):
    context_requested = pyqtSignal(QPoint)

    def __init__(self, audio_path, parent=None):
        super().__init__(parent)
        self.setObjectName("audio_panel")
        self.setStyleSheet("QFrame#audio_panel { background-color: #222; border-top: 2px solid #555; }")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        self.meter = AudioMeter(audio_path)
        lay.addWidget(self.meter)
        self.setFixedHeight(30)
        self.timer = QTimer(self)
        self.timer.setInterval(66)
        self.timer.timeout.connect(self._poll)
        self.hide()

    def configure(self, show):
        if show:
            self.show()
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()
            self.meter.reset()
            self.hide()

    def reset(self):
        self.meter.reset()

    def _poll(self):
        if self.isVisible():
            self.meter.poll()

    def contextMenuEvent(self, event):
        self.context_requested.emit(event.globalPos())
        event.accept()


# =============================================================================
# CameraHotkeys – yüzen kamera penceresi için genel kısayollar (pynput varsa)
#   Ctrl + Shift        : tam ekran aç/kapat
#   Ctrl + Yukarı/Aşağı : büyüt / küçült   (Ctrl + fare tekerleği de çalışır)
# Kısayollar yalnızca fare kamera penceresinin üzerindeyken uygulanır.
# =============================================================================
class CameraHotkeys(QObject):
    fullscreen_requested = pyqtSignal()
    resize_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ctrl = False
        self._shift = False
        self._fired = False
        self._listener = None

    @property
    def active(self):
        return self._listener is not None

    def start(self):
        if not PYNPUT_AVAILABLE or self._listener is not None:
            return
        try:
            self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
            self._listener.daemon = True
            self._listener.start()
        except Exception as e:
            print(f"Python Uyarı: kamera kısayolları başlatılamadı: {e}")
            self._listener = None

    def stop(self):
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
        self._ctrl = self._shift = self._fired = False

    @staticmethod
    def _is(key, *names):
        return any(key == getattr(keyboard.Key, n, None) for n in names)

    def _on_press(self, key):
        try:
            if self._is(key, 'ctrl', 'ctrl_l', 'ctrl_r'):
                self._ctrl = True
            elif self._is(key, 'shift', 'shift_l', 'shift_r'):
                self._shift = True
            elif self._ctrl and not self._shift:
                char = getattr(key, 'char', None)
                if self._is(key, 'up') or char in ('+', '='):
                    self.resize_requested.emit(1)
                elif self._is(key, 'down') or char == '-':
                    self.resize_requested.emit(-1)
            if self._ctrl and self._shift and not self._fired:
                self._fired = True
                self.fullscreen_requested.emit()
        except Exception:
            pass

    def _on_release(self, key):
        try:
            if self._is(key, 'ctrl', 'ctrl_l', 'ctrl_r'):
                self._ctrl = False
            elif self._is(key, 'shift', 'shift_l', 'shift_r'):
                self._shift = False
            if not (self._ctrl and self._shift):
                self._fired = False
        except Exception:
            pass


# =============================================================================
# CameraOverlay – ekranda hep üstte duran yüzen kamera penceresi
#   • Ctrl + Sol Tık + Sürükle : taşı           • Ctrl + Tekerlek / Ctrl + ↑↓ : boyut
#   • Ctrl + Shift (fare üstündeyken) : tam ekran aç/kapat
#   • Sağ tık : kamera / çözünürlük / ses kaynağı menüsü
# Ekran kaydı bu pencereyi de kaydeder; kamera ayrı dosyaya yazılmaz.
# =============================================================================
class CameraOverlay(QWidget):
    context_requested = pyqtSignal(QPoint)

    MIN_W = 120

    def __init__(self, recorder_window, path, width=260, mirror=True):
        super().__init__(
            None,
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.BypassWindowManagerHint
        )
        self.recorder_window = recorder_window
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.reader = ShmReader(path, 'video')
        self.image = None
        self.mirror = mirror
        self.aspect = 4.0 / 3.0
        self.message = "Kamera bekleniyor…"
        self._fullscreen = False
        self._normal_geom = None
        self._drag_active = False
        self._drag_offset = QPoint()
        self._mods_prev = False
        self.resize(int(width), int(width / self.aspect))

        self.timer = QTimer(self)
        self.timer.setInterval(66)
        self.timer.timeout.connect(self._poll)

        self.hotkeys = CameraHotkeys(self)
        self.hotkeys.fullscreen_requested.connect(self._hotkey_fullscreen)
        self.hotkeys.resize_requested.connect(self._hotkey_resize)

    # -- yaşam döngüsü --
    def start(self):
        self.show()
        self.timer.start()
        self.hotkeys.start()

    def stop(self):
        self.timer.stop()
        self.hotkeys.stop()
        self.reader.reset()
        self.hide()

    def reset_frame(self, message="Kamera bekleniyor…"):
        self.reader.reset()
        self.image = None
        self.message = message
        self.update()

    def set_message(self, text):
        self.image = None
        self.message = text
        self.update()

    def set_mirror(self, mirror):
        self.mirror = bool(mirror)
        self.update()

    # -- kare okuma --
    def _poll(self):
        img = self.reader.read_frame()
        if img is not None:
            self.image = img
            ar = img.width() / max(1, img.height())
            if abs(ar - self.aspect) > 0.01:
                self.aspect = ar
                if not self._fullscreen:
                    self.resize(self.width(), max(60, int(self.width() / self.aspect)))
            self.update()
        # pynput yoksa (ya da Wayland'de) Ctrl+Shift'i Qt üzerinden izle
        if not self.hotkeys.active:
            mods = QApplication.queryKeyboardModifiers()
            both = bool(mods & Qt.ControlModifier) and bool(mods & Qt.ShiftModifier)
            if both and not self._mods_prev:
                self._hotkey_fullscreen()
            self._mods_prev = both

    # -- kısayol işleyicileri (yalnızca fare pencerenin üstündeyken) --
    def _hover(self):
        return self.isVisible() and self.frameGeometry().contains(QCursor.pos())

    def _hotkey_fullscreen(self):
        if self._hover():
            self.toggle_fullscreen()

    def _hotkey_resize(self, step):
        if self._hover():
            self.resize_step(step)

    def _screen_geometry(self):
        scr = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        return scr.geometry()

    def toggle_fullscreen(self):
        if not self._fullscreen:
            self._normal_geom = self.geometry()
            self._fullscreen = True
            self.setGeometry(self._screen_geometry())
        else:
            self._fullscreen = False
            if self._normal_geom is not None:
                self.setGeometry(self._normal_geom)
            self._save_geometry()
        self.update()

    def resize_step(self, step):
        if self._fullscreen:
            return
        geo = self._screen_geometry()
        factor = 1.12 if step > 0 else 1 / 1.12
        new_w = int(max(self.MIN_W, min(geo.width() * 0.9, self.width() * factor)))
        self.resize(new_w, max(60, int(new_w / self.aspect)))
        self._save_geometry()

    def _save_geometry(self):
        if self.recorder_window and not self._fullscreen:
            self.recorder_window.camera_overlay_geom = (self.x(), self.y(), self.width())
            self.recorder_window.save_overlay_settings()

    # -- fare / klavye --
    def mousePressEvent(self, event):
        mods = event.modifiers()
        if event.button() == Qt.LeftButton and (mods & Qt.ControlModifier) and (mods & Qt.ShiftModifier):
            self.toggle_fullscreen()
            event.accept()
        elif event.button() == Qt.LeftButton and (mods & Qt.ControlModifier) and not self._fullscreen:
            self._drag_active = True
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if self._drag_active and (event.buttons() & Qt.LeftButton):
            self.move(event.globalPos() - self._drag_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_active:
            self._drag_active = False
            self._save_geometry()
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self.resize_step(1 if event.angleDelta().y() > 0 else -1)
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self._fullscreen:
            self.toggle_fullscreen()
        elif event.modifiers() & Qt.ControlModifier and event.key() in (Qt.Key_Up, Qt.Key_Plus, Qt.Key_Equal):
            self.resize_step(1)
        elif event.modifiers() & Qt.ControlModifier and event.key() in (Qt.Key_Down, Qt.Key_Minus):
            self.resize_step(-1)
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        self.context_requested.emit(event.globalPos())
        event.accept()

    def closeEvent(self, event):
        self.timer.stop()
        self.hotkeys.stop()
        super().closeEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        radius = 0 if self._fullscreen else 8
        p.setPen(QPen(QColor(85, 85, 85), 1))
        p.setBrush(QColor(0, 0, 0, 235))
        p.drawRoundedRect(rect.adjusted(0, 0, -1, -1), radius, radius)
        if self.image is not None and not self.image.isNull():
            inner = rect.adjusted(2, 2, -2, -2)
            iw, ih = self.image.width(), self.image.height()
            scale = min(inner.width() / iw, inner.height() / ih)
            tw, th = max(1, int(iw * scale)), max(1, int(ih * scale))
            x, y = inner.x() + (inner.width() - tw) // 2, inner.y() + (inner.height() - th) // 2
            p.setRenderHint(QPainter.Antialiasing, False)
            if self.mirror:
                p.translate(x * 2 + tw, 0)
                p.scale(-1, 1)
            p.drawImage(QRect(x, y, tw, th), self.image)
        else:
            p.setPen(QColor(150, 150, 150))
            p.drawText(rect, Qt.AlignCenter | Qt.TextWordWrap, self.message)


# =============================================================================
# CameraRecorderWindow – Ana pencere
# =============================================================================
class CameraRecorderWindow(QWidget):
    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        self.setWindowTitle("Camera Editor")
        self.resize(900, 600)
        self.setStyleSheet("background-color: #383838; color: white; border: none;")

        self.player       = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.video_widget.setToolTip("")

        self.frame_width  = 640
        self.frame_height = 480
        self.fps          = VIDEO_FPS

        self.recording        = False
        self.recorder_thread  = None

        self.record_start_time_segment = None
        self.cumulative_time           = 0

        self.windows_active       = False
        self.sound_active         = False
        self.camera_active        = False
        self.camera_device        = ""          # boş = otomatik
        self.camera_resolution    = "480p"
        self.preview_mirror       = True
        self.camera_overlay_geom  = None        # (x, y, genişlik)
        self.audio_source_choice  = ""
        self.keystroke_display_enabled = False
        self.noise_filter_enabled = self._load_noise_filter_setting()

        self.segment_duration       = 31536000   # yalnızca eski ffmpeg yedek yolu için: fiilen tek dosya
        self.force_export_state     = False

        # Oturum tipini ve C++ recorder yolunu şimdiden belirle
        self.display_server = detect_display_server()
        self.camera_recorder_path = get_camera_recorder_path()
        print(f"Python: Display server = {self.display_server}")
        print(f"Python: camera_recorder = {self.camera_recorder_path}")
        self.native_caps = native_capabilities(self.camera_recorder_path)
        print(f"Python: yerel motor = {'var' if self.native_caps else 'yok (ffmpeg yedeği kullanılacak)'}")

        sg = QApplication.desktop().screenGeometry()
        self.screen_width  = sg.width()
        self.screen_height = sg.height()

        self.resolution_map  = {"1080p":"1920x1080","720p":"1280x720","480p":"854x480","360p":"640x360"}
        self.fps_map         = {"6":6,"12":12,"24":24,"25":25,"30":30,"60":60}
        self.audio_rate_map  = {"32000":32000,"44100":44100,"48000":48000,"96000":96000}

        self.selected_resolution = self._best_resolution()
        self.selected_fps        = 12
        self.selected_audio_rate = 48000

        self.filter_settings = {
            'ai_nr_enabled': True, 'noise_gate_threshold_db': -70.0,
            'hp_cutoff_hz': 150, 'lp_cutoff_hz': 10000, 'gain_db': 6.0,
            'reverb_reduction_level': 0, 'de_esser_level': 0, 'de_hum_level': 0,
            'compressor_threshold_db': 0.0, 'compressor_ratio': 3.0,
            'compressor_attack_ms': 5.0, 'compressor_release_ms': 150.0,
            'eq_gain_db': 0.0, 'eq_freq_hz': 1000.0, 'eq_q': 1.0,
        }
        self.load_filter_settings()

        self.overlay_thickness = 40
        self.overlay_default_pos = None
        self.overlay_visible = True
        self.load_overlay_settings()

        self.camera_feature_window = None
        self.floating_overlay: FloatingOverlay | None = None
        self._last_files = []
        self._closing = False
        self._preview_runner = None
        self._preview_sig = None
        self._cam_runner = None
        self._cam_sig = None
        self.camera_overlay = None
        self._preview_sync_pending = False
        self._zombie_threads = []

        self.force_close = False
        self.playback_mode        = None
        self.playback_filepath    = None
        self.is_playing           = False
        self.audio_player_process = None
        
        self.input_signaler = InputSignaler()
        self.input_signaler.input_received.connect(self._safe_on_input_press)
        self.input_signaler.input_released.connect(self._safe_on_input_release)
        
        self.input_overlay: InputOverlay | None = None
        self.input_listener: InputListener | None = None

        QDir().mkpath(DEFAULT_BASE_DIR)
        QDir().mkpath(SEGMENT_DIR)

        self.initUI()
        self._cleanup_segments()

        self._ensure_overlay()
        self._ensure_input_overlay()

        self.player.stateChanged.connect(self._handle_player_state_changed)
        self.player.positionChanged.connect(self._handle_player_position_changed)
        self.player.durationChanged.connect(self._handle_player_duration_changed)
        self.player.error.connect(self._handle_player_error)

        self.time_timer = QTimer(self)
        self.time_timer.setInterval(50)
        self.time_timer.timeout.connect(self.updateTimeLabel)

        self.segment_monitor_timer = QTimer(self)
        self.segment_monitor_timer.setInterval(1000)
        self.segment_monitor_timer.timeout.connect(self.updateSegmentUI)
        self.segment_monitor_timer.start()

        self.audio_playback_timer = QTimer(self)
        self.audio_playback_timer.setInterval(50)
        self.audio_playback_timer.timeout.connect(self.updateAudioPlaybackProgress)

        if self.keystroke_display_enabled:
            self._start_input_listener()

    # ─── Yardımcılar ve Ayarlar ──────────────────────────────────────────────

    def _best_resolution(self):
        sg = QApplication.desktop().screenGeometry()
        w, h = sg.width(), sg.height()
        if w <= 640 or h <= 360:   return "360p"
        if w <= 854 or h <= 480:   return "480p"
        if w <= 1280 or h <= 720:  return "720p"
        return "1080p"

    def _load_noise_filter_setting(self):
        try:
            if os.path.exists(OVERLAY_SETTINGS_FILE):
                with open(OVERLAY_SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('noise_filter_enabled', False)
        except Exception: pass
        return False

    def _save_noise_filter_setting(self):
        try:
            data = {}
            if os.path.exists(OVERLAY_SETTINGS_FILE):
                with open(OVERLAY_SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
            data['noise_filter_enabled'] = self.noise_filter_enabled
            with open(OVERLAY_SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception: pass

    def load_overlay_settings(self):
        global AUDIO_SOURCE_OVERRIDE
        try:
            if os.path.exists(OVERLAY_SETTINGS_FILE):
                with open(OVERLAY_SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    self.overlay_thickness = settings.get('thickness', 40)
                    self.overlay_visible = settings.get('overlay_visible', True)
                    pos = settings.get('default_position', None)
                    if pos and len(pos) == 2:
                        self.overlay_default_pos = tuple(pos)
                    self.camera_active = settings.get('camera_active', False)
                    self.camera_device = settings.get('camera_device', "")
                    self.camera_resolution = settings.get('camera_resolution', "480p")
                    if self.camera_resolution not in CAMERA_RESOLUTIONS:
                        self.camera_resolution = "480p"
                    self.preview_mirror = settings.get('preview_mirror', True)
                    geom = settings.get('camera_overlay')
                    self.camera_overlay_geom = tuple(geom) if isinstance(geom, list) and len(geom) == 3 else None
                    self.audio_source_choice = settings.get('audio_source', "")
                    AUDIO_SOURCE_OVERRIDE = self.audio_source_choice
                    self.windows_active = settings.get('windows_active', False)
                    self.sound_active = settings.get('sound_active', False)
                    self.keystroke_display_enabled = settings.get('keystroke_display_enabled', False)
        except Exception: pass

    def save_overlay_settings(self):
        try:
            settings = {}
            if os.path.exists(OVERLAY_SETTINGS_FILE):
                with open(OVERLAY_SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
            settings['thickness'] = self.overlay_thickness
            settings['overlay_visible'] = getattr(self, 'overlay_visible', True)
            settings['default_position'] = list(self.overlay_default_pos) if self.overlay_default_pos else None
            settings['camera_active'] = getattr(self, 'camera_active', False)
            settings['camera_device'] = getattr(self, 'camera_device', "")
            settings['camera_resolution'] = getattr(self, 'camera_resolution', "480p")
            settings['preview_mirror'] = getattr(self, 'preview_mirror', True)
            if getattr(self, 'camera_overlay_geom', None):
                settings['camera_overlay'] = list(self.camera_overlay_geom)
            settings['audio_source'] = getattr(self, 'audio_source_choice', "")
            settings['windows_active'] = getattr(self, 'windows_active', False)
            settings['sound_active'] = getattr(self, 'sound_active', False)
            settings['keystroke_display_enabled'] = getattr(self, 'keystroke_display_enabled', False)
            with open(OVERLAY_SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception: pass

    def set_overlay_thickness(self, value):
        self.overlay_thickness = value
        if self.floating_overlay:
            self.floating_overlay.set_thickness(value)
        if self.input_overlay:
            self.input_overlay.set_thickness(value)
            self._update_input_overlay_position()

    def _ensure_overlay(self):
        if self.floating_overlay is None:
            self.floating_overlay = FloatingOverlay(self, self.overlay_thickness)
            if self.overlay_default_pos:
                self.floating_overlay.move(*self.overlay_default_pos)
            else:
                screen = QApplication.desktop().screenGeometry()
                self.floating_overlay.move(
                    screen.right() - 190, 
                    screen.bottom() - self.overlay_thickness - 20
                )
        
        if getattr(self, 'overlay_visible', True):
            self.floating_overlay.show()
            if hasattr(self, 'time_label'):
                self._update_overlay(self.time_label.text())
        else:
            self.floating_overlay.hide()

    def _ensure_input_overlay(self):
        if self.input_overlay is None:
            self.input_overlay = InputOverlay(self, self.overlay_thickness)
        
        self._update_input_overlay_position()
        
        if not self.keystroke_display_enabled:
            self.input_overlay.hide()

    def _update_input_overlay_position(self):
        if self.input_overlay:
            pos = None
            if self.floating_overlay:
                pos = self.floating_overlay.pos()
            elif self.overlay_default_pos:
                pos = QPoint(self.overlay_default_pos[0], self.overlay_default_pos[1])
            
            if pos is not None:
                self.input_overlay.move(pos.x(), pos.y() - self.input_overlay.height() - 4)

    def _update_floating_overlay_from_input(self, input_pos):
        if self.floating_overlay:
            new_y = input_pos.y() + self.input_overlay.height() + 4
            self.floating_overlay.move(input_pos.x(), new_y)

    def _save_overlay_positions_from_input(self):
        if self.input_overlay:
            pos_x = self.input_overlay.pos().x()
            pos_y = self.input_overlay.pos().y() + self.input_overlay.height() + 4
            self.overlay_default_pos = (pos_x, pos_y)
            self.save_overlay_settings()

    def _close_overlay(self):
        if self.input_overlay is not None:
            try:
                self.input_overlay.hide()
                self.input_overlay.deleteLater()
            except: pass
            self.input_overlay = None
            
        if self.floating_overlay is not None:
            try:
                self.floating_overlay.hide()
                self.floating_overlay.deleteLater()
            except: pass
            self.floating_overlay = None

    def _update_overlay(self, time_text: str):
        if self.floating_overlay is not None:
            has_session = self.recording or self.cumulative_time > 0
            self.floating_overlay.update_display(time_text, self.recording, has_session)

    def _reset_overlay_to_default_position(self):
        if self.floating_overlay:
            screen = QApplication.desktop().screenGeometry()
            self.floating_overlay.move(
                screen.right() - 190,
                screen.bottom() - self.overlay_thickness - 20
            )
            self.overlay_thickness = 40
            self.thickness_button.thickness = 40
            self.thickness_button.setText("40")
            self.floating_overlay.set_thickness(40)
            self._update_input_overlay_position()
            self.save_overlay_settings()

    def _set_current_as_default_position(self):
        if self.floating_overlay:
            pos = self.floating_overlay.pos()
            self.overlay_default_pos = (pos.x(), pos.y())
            self.save_overlay_settings()

    def toggle_overlay_visibility(self):
        self.overlay_visible = not getattr(self, 'overlay_visible', True)
        if self.overlay_visible:
            self.z_toggle_button.setStyleSheet(self.buttonStyleMiniPressed())
            if self.floating_overlay:
                self.floating_overlay.show()
                self._update_overlay(self.time_label.text())
            else:
                self._ensure_overlay()
        else:
            self.z_toggle_button.setStyleSheet(self.buttonStyleMini())
            if self.floating_overlay:
                self.floating_overlay.hide()
        self.save_overlay_settings()

    def toggle_keystroke_display(self):
        if not PYNPUT_AVAILABLE:
            QMessageBox.warning(
                self, "Modül Eksik",
                "Klavye/Mouse gösterimi için 'pynput' gerekli.\n\n"
                "Kavram klasöründe kurulum dosyasını yeniden çalıştırın\n"
                "(venv içinde: pip install pynput)."
            )
            self.keystroke_display_enabled = False
            self.keystroke_toggle_button.setStyleSheet(self.buttonStyleMini())
            self.save_overlay_settings()
            return

        self.keystroke_display_enabled = not self.keystroke_display_enabled
        if self.keystroke_display_enabled:
            self.keystroke_toggle_button.setStyleSheet(self.buttonStyleMiniPressed())
            self._start_input_listener()
            self._ensure_input_overlay()
        else:
            self.keystroke_toggle_button.setStyleSheet(self.buttonStyleMini())
            self._stop_input_listener()
            if self.input_overlay is not None:
                self.input_overlay.hide_input()
        self.save_overlay_settings()

    def _start_input_listener(self):
        if self.input_listener is None:
            self.input_listener = InputListener(self.input_signaler)
        self.input_listener.start()

    def _stop_input_listener(self):
        if self.input_listener is not None:
            self.input_listener.stop()

    def _safe_on_input_press(self, inputs):
        if not self.keystroke_display_enabled or not self.input_overlay: return
        text = " + ".join(inputs)
        self.input_overlay.show_input(text)

    def _safe_on_input_release(self, inputs):
        if not self.keystroke_display_enabled or not self.input_overlay: return
        if not inputs: 
            self.input_overlay.show_input("")
        else:
            text = " + ".join(inputs)
            self.input_overlay.show_input(text)


    # ─── UI Mimarisi ──────────────────────────────────────────────────────────

    def initUI(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.toolbar_frame = QFrame()
        self.toolbar_frame.setStyleSheet(
            "QFrame { background-color: #222; border-bottom: 2px solid #555; }")
        self.toolbar_frame.setFixedHeight(40)
        self.toolbar_layout = QHBoxLayout(self.toolbar_frame)
        self.toolbar_layout.setContentsMargins(10, 5, 10, 5)
        self.toolbar_layout.setSpacing(10)

        def add(widget, side=Qt.AlignLeft):
            self.toolbar_layout.addWidget(widget, alignment=side)

        self.file_button = QPushButton("File")
        self.file_button.setFixedSize(90, 30)
        self.file_button.setStyleSheet(self.buttonStyle())
        self.file_button.clicked.connect(self.openFileForPlayback)
        add(self.file_button)

        self.camera_button_feature = QPushButton("Camera")
        self.camera_button_feature.setFixedSize(90, 30)
        self.camera_button_feature.setStyleSheet(self.toggleButtonStyle(self.camera_active))
        self.camera_button_feature.setToolTip(
            "Yüzen kamera penceresi (ekran kaydına girer)\n"
            "Ctrl+Sol tık sürükle: taşı • Ctrl+tekerlek / Ctrl+↑↓: boyut • Ctrl+Shift: tam ekran\n"
            "Sağ tık: kamera / çözünürlük / ses kaynağı")
        self.camera_button_feature.clicked.connect(lambda: self.toggleButtonState("camera"))
        add(self.camera_button_feature)

        self.windows_button = QPushButton("Windows")
        self.windows_button.setFixedSize(95, 30)
        self.windows_button.setStyleSheet(self.toggleButtonStyle(self.windows_active))
        self.windows_button.clicked.connect(lambda: self.toggleButtonState("windows"))
        add(self.windows_button)

        self.sound_button = QPushButton("Sound")
        self.sound_button.setFixedSize(90, 30)
        self.sound_button.setStyleSheet(self.toggleButtonStyle(self.sound_active))
        self.sound_button.clicked.connect(lambda: self.toggleButtonState("sound"))
        add(self.sound_button)

        self.noise_filter_button = QPushButton("I")
        self.noise_filter_button.setStyleSheet(self.buttonStylePressure(self.noise_filter_enabled))
        self.noise_filter_button.setFixedSize(30, 30)
        self.noise_filter_button.clicked.connect(self.toggleNoiseFilter)
        self.noise_filter_button.setContextMenuPolicy(Qt.NoContextMenu)
        add(self.noise_filter_button)

        self.btn_s_kurtarma = QPushButton("S")
        self.btn_s_kurtarma.setFixedSize(30, 30)
        self.btn_s_kurtarma.setStyleSheet(self.buttonStyleMini())
        self.btn_s_kurtarma.clicked.connect(self.s_buton_denetimi)
        add(self.btn_s_kurtarma)

        self.toolbar_layout.addSpacerItem(
            QSpacerItem(0, 0, QSizePolicy.Fixed, QSizePolicy.Minimum))

        self.thickness_button = ThicknessButton(self)
        self.thickness_button.thickness = self.overlay_thickness
        self.thickness_button.setText(str(self.overlay_thickness))
        self.thickness_button.setStyleSheet(self.buttonStyleMini())
        self.thickness_button.clicked.connect(self._reset_overlay_to_default_position)
        self.thickness_button.customContextMenuRequested.connect(
            self._set_current_as_default_position)
        add(self.thickness_button)
        
        self.keystroke_toggle_button = QPushButton("/")
        if self.keystroke_display_enabled:
            self.keystroke_toggle_button.setStyleSheet(self.buttonStyleMiniPressed())
        else:
            self.keystroke_toggle_button.setStyleSheet(self.buttonStyleMini())
        self.keystroke_toggle_button.setFixedSize(30, 30)
        self.keystroke_toggle_button.clicked.connect(self.toggle_keystroke_display)
        add(self.keystroke_toggle_button)

        self.z_toggle_button = QPushButton("Z")
        if getattr(self, 'overlay_visible', True):
            self.z_toggle_button.setStyleSheet(self.buttonStyleMiniPressed())
        else:
            self.z_toggle_button.setStyleSheet(self.buttonStyleMini())
        self.z_toggle_button.setFixedSize(30, 30)
        self.z_toggle_button.clicked.connect(self.toggle_overlay_visibility)
        add(self.z_toggle_button)

        self.main_play_pause_button = QPushButton("Play")
        self.main_play_pause_button.setFixedSize(80, 30)
        self.main_play_pause_button.setStyleSheet(self.buttonStyle())
        self.main_play_pause_button.clicked.connect(self.handleMainPlayPause)
        add(self.main_play_pause_button)

        self.main_close_playback_button = QPushButton("X")
        self.main_close_playback_button.setFixedSize(30, 30)
        self.main_close_playback_button.setStyleSheet(self.buttonStyleMini())
        self.main_close_playback_button.clicked.connect(self.closePlaybackBar)
        self.main_close_playback_button.setEnabled(False)
        add(self.main_close_playback_button)

        self.toolbar_layout.addStretch()

        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet("color: white; font-size: 14px; margin-right: 10px;")
        add(self.time_label, Qt.AlignRight)

        self.export_button = QPushButton("Export")
        self.export_button.setFixedSize(90, 30)
        self.export_button.setStyleSheet(self.buttonStyle())
        self.export_button.clicked.connect(self.exportRecording)
        add(self.export_button, Qt.AlignRight)

        self.camera_button = QPushButton("Rec")
        self.camera_button.setFixedSize(90, 30)
        self.camera_button.setStyleSheet(self.buttonStyle())
        self.camera_button.clicked.connect(self.cameraButtonClicked)
        add(self.camera_button, Qt.AlignRight)

        self.layout.addWidget(self.toolbar_frame)

        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black;")
        vfl = QVBoxLayout(self.video_frame)
        vfl.setContentsMargins(0, 0, 0, 0)
        self.video_widget.setStyleSheet("background-color: black;")
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        vfl.addWidget(self.video_widget)
        self.video_widget.hide()
        self.info_label = InfoPreviewLabel("No Video Preview", PV_SCREEN_PATH)
        self.info_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.info_label.customContextMenuRequested.connect(
            lambda pos: self._show_preview_menu(self.info_label.mapToGlobal(pos)))
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #777; font-size: 18px;")
        self.info_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        vfl.addWidget(self.info_label)

        self.playback_bar_frame = QFrame()
        self.playback_bar_frame.setStyleSheet("background-color: #222; border-top: 2px solid #555;")
        self.playback_bar_frame.setFixedHeight(60)
        pbl = QHBoxLayout(self.playback_bar_frame)
        pbl.setContentsMargins(10, 5, 10, 5)
        self.playback_bar_frame.hide()

        self.playback_time_label = QLabel("00:00")
        self.playback_time_label.setStyleSheet("color: white; font-size: 12px; margin-right: 5px;")
        pbl.addWidget(self.playback_time_label)

        self.playback_slider = PlaybackSlider(Qt.Horizontal)
        self.playback_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999; height: 8px;
                background: #444; margin: 2px 0; border-radius: 4px; }
            QSlider::handle:horizontal {
                width: 0; height: 0; margin: 0;
                background: transparent; border: none; }
        """)
        self.playback_slider.sliderMoved.connect(self.seekPlayback)
        pbl.addWidget(self.playback_slider)

        self.playback_total_time_label = QLabel("00:00")
        self.playback_total_time_label.setStyleSheet("color: white; font-size: 12px; margin-left: 5px;")
        pbl.addWidget(self.playback_total_time_label)

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.video_frame)
        self.splitter.addWidget(self.playback_bar_frame)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #555; }")
        self.layout.addWidget(self.splitter, 1)
        self.splitter.setSizes([self.height() - self.toolbar_frame.height(), 0])

        # Alt panel: yalnızca ses dalgalanması (ekran önizlemesi ortadaki büyük alanda, kamera yüzen pencerede)
        self.audio_panel = AudioPanel(PV_AUDIO_PATH)
        self.audio_panel.context_requested.connect(self._show_preview_menu)
        self.layout.addWidget(self.audio_panel, 0)

    # ─── Stiller ──────────────────────────────────────────────────────────────

    def buttonStyle(self): return """
        QPushButton { background-color:transparent; color:white; font-size:14px;
            font-weight:bold; border:2px solid #555; border-radius:8px; padding:5px; }
        QPushButton:hover   { background-color:#444; }
        QPushButton:pressed { background-color:#666; }"""

    def buttonStyleMini(self): return """
        QPushButton { background-color:transparent; color:white; font-size:16px;
            border:2px solid #555; border-radius:8px; padding:2px; }
        QPushButton:hover   { background-color:#444; }
        QPushButton:pressed { background-color:#666; }"""

    def buttonStyleMiniBlack(self): return """
        QPushButton { background-color:#111; color:#aaa; font-size:16px;
            border:2px solid #333; border-radius:8px; padding:2px; }
        QPushButton:hover   { background-color:#222; }
        QPushButton:pressed { background-color:#000; }"""

    def toggleButtonStyle(self, active): return ("""
        QPushButton { background-color:#555; color:white; font-size:14px;
            font-weight:bold; border:2px solid #555; border-radius:8px; padding:5px; }
        QPushButton:hover   { background-color:#666; }
        QPushButton:pressed { background-color:#777; }""" if active else """
        QPushButton { background-color:transparent; color:white; font-size:14px;
            font-weight:bold; border:2px solid #555; border-radius:8px; padding:5px; }
        QPushButton:hover   { background-color:#444; }
        QPushButton:pressed { background-color:#666; }""")

    def buttonStylePressure(self, active): return ("""
        QPushButton { background-color:#555; color:white; font-size:16px;
            border:2px solid #555; border-radius:8px; padding:2px; }
        QPushButton:hover   { background-color:#666; }
        QPushButton:pressed { background-color:#777; }""" if active else """
        QPushButton { background-color:transparent; color:white; font-size:16px;
            border:2px solid #555; border-radius:8px; padding:2px; }
        QPushButton:hover   { background-color:#444; }
        QPushButton:pressed { background-color:#666; }""")

    def buttonStyleMiniPressed(self): return """
        QPushButton { background-color:#666; color:white; font-size:16px;
            border:2px solid #888; border-radius:8px; padding:2px; }
        QPushButton:hover   { background-color:#777; }
        QPushButton:pressed { background-color:#888; }"""

    def comboStyle(self): return """
        QComboBox { background-color:transparent; color:white; font-size:14px;
            font-weight:bold; border:2px solid #555; border-radius:8px;
            padding:5px; padding-left:10px; }
        QComboBox:hover { background-color:#444; }
        QComboBox::drop-down { border:0px; subcontrol-origin:padding;
            subcontrol-position:top right; width:20px; }
        QComboBox::down-arrow { image:url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNNyAxMEwxMiAxNUwxNyAxMCIgc3Ryb2tlPSIjZWVlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwvc3ZnPg==);
            width:16px; height:16px; }
        QComboBox QAbstractItemView { background-color:#282828; border:1px solid #555;
            selection-background-color:#444; color:white; }"""

    def disabledButtonStyle(self): return """
        QPushButton { background-color:#333; color:#777; font-size:14px;
            font-weight:bold; border:2px solid #444; border-radius:8px; padding:5px; }"""

    # ─── Ayarlar ve Buton Aksiyonları ─────────────────────────────────────────

    def load_filter_settings(self):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                self.filter_settings.update(json.load(f))
        except Exception: pass

    def save_filter_settings(self):
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.filter_settings, f, indent=4)
        except Exception: pass

    def toggleNoiseFilter(self):
        self.noise_filter_enabled = not self.noise_filter_enabled
        self.noise_filter_button.setStyleSheet(self.buttonStylePressure(self.noise_filter_enabled))
        self._save_noise_filter_setting()

    def toggleButtonState(self, name: str):
        # Kamera, kayıt sırasında da açılıp kapatılabilir (yüzen pencere ekran kaydına girer)
        if name != "camera" and (self.recording or self._native_session_alive()):
            QMessageBox.information(
                self, "Mod Değiştirilemez",
                "Kayıt oturumu açıkken Windows/Sound modları değiştirilemez.\n"
                "Önce Export edin ya da S ile temizleyin.")
            return
        if name == "camera" and not self.camera_active and not self._native_available():
            QMessageBox.information(
                self, "Kamera Önizlemesi",
                "Kamera için C++ kaydedici gerekir.\n\n"
                "rec/rec_engine.cpp dosyasını derleyin (komut: rec/derleme.txt).")
            return
        if name == "windows": self.windows_active = not self.windows_active
        elif name == "sound":  self.sound_active   = not self.sound_active
        elif name == "camera": self.camera_active  = not self.camera_active
        self.windows_button.setStyleSheet(self.toggleButtonStyle(self.windows_active))
        self.sound_button.setStyleSheet(self.toggleButtonStyle(self.sound_active))
        self.camera_button_feature.setStyleSheet(self.toggleButtonStyle(self.camera_active))
        self.updateMainPlayPauseButtonState()
        self.save_overlay_settings()
        self._update_panel_state()
        self._schedule_preview_sync()

    # ─── Kayıt Başlatma & Durdurma ───────────────────────────────────────────

    def _get_next_segment_number(self, directory):
        max_num = 0
        if not os.path.exists(directory): return 1
        try:
            for fn in os.listdir(directory):
                match = re.match(r'^s(\d+)\.(mkv|wav)$', fn)
                if match:
                    num = int(match.group(1))
                    if num > max_num: max_num = num
        except Exception: pass
        return max_num + 1

    def _resolution_to_wh(self):
        """Seçilen çözünürlükten (W, H) üret."""
        res_str = self.resolution_map.get(self.selected_resolution, "854x480")
        try:
            w, h = map(int, res_str.split('x'))
            # Ekran boyutundan büyükse küçült
            screen_geo = QApplication.desktop().screenGeometry()
            if w > screen_geo.width() or h > screen_geo.height():
                sf = min(screen_geo.width() / w, screen_geo.height() / h)
                w = (int(w * sf) // 2) * 2
                h = (int(h * sf) // 2) * 2
            return w, h
        except Exception:
            return 854, 480

    def _start_recorder(self):
        if self._native_available():
            return self._start_native_recorder()

        start_num = self._get_next_segment_number(SEGMENT_DIR)
        args = {'output_dir': SEGMENT_DIR, 'start_number': start_num, 'segment_time': self.segment_duration}
        rc = None; info = ""

        use_wayland = (self.display_server == 'wayland')

        # Wayland seçiliyse ve C++ binary bulunamadıysa uyar
        if use_wayland and self.camera_recorder_path is None and self.windows_active:
            QMessageBox.critical(
                self, "Wayland Recorder Bulunamadı",
                "Wayland için 'rec_engine' bulunamadı.\n\n"
                "rec/derleme.txt ile derleyin veya\n"
                "X11 oturumunda çalıştırın."
            )
            self.info_label.setText("Wayland recorder yok")
            self.info_label.show()
            self.video_widget.hide()
            return False

        if self.windows_active and self.sound_active:
            if use_wayland:
                rc = WaylandCombinedRecorder
                w, h = self._resolution_to_wh()
                args.update({
                    'camera_recorder_path': self.camera_recorder_path,
                    'fps': self.selected_fps,
                    'width': w,
                    'height': h,
                    'audio_rate': self.selected_audio_rate,
                })
            else:
                rc = CombinedRecorder
                args.update({'fps': self.selected_fps,
                             'resolution': self.selected_resolution,
                             'audio_rate': self.selected_audio_rate})
            info = "Birleşik Ekran (MKV) ve Ses Kaydı Aktif"

        elif self.windows_active:
            if use_wayland:
                rc = WaylandScreenRecorder
                w, h = self._resolution_to_wh()
                args.update({
                    'camera_recorder_path': self.camera_recorder_path,
                    'fps': self.selected_fps,
                    'width': w,
                    'height': h,
                })
            else:
                rc = ScreenRecorder
                args.update({'fps': self.selected_fps, 'resolution': self.selected_resolution})
            info = "Ekran Kaydı Aktif (MKV)"

        elif self.sound_active:
            rc = AudioRecorder
            args['audio_rate'] = self.selected_audio_rate
            info = "Ses Kaydı Aktif (WAV)"

        if rc:
            self.recorder_thread = rc(**args)
            self.recorder_thread.recording_started.connect(lambda m: print(f"Recorder: {m}"))
            self.recorder_thread.recording_stopped.connect(self._handle_recorder_stopped)
            self.recorder_thread.error_occurred.connect(self._handle_recorder_error)
            self.recorder_thread.start()
            self.info_label.setText(info)
            if self.overlay_visible:
                self._ensure_overlay()
        else:
            self.info_label.setText("Kayıt modu seçilmedi.")
            self.info_label.show()
            self.video_widget.hide()
            return False

        self.info_label.show()
        self.video_widget.hide()
        return self.recorder_thread is not None and self.recorder_thread.isRunning()

    def _handle_recorder_error(self, msg):
        QMessageBox.critical(self, "Kaydedici Hatası", msg)
        self._stop_full_recording_session(cleanup=False)

    def _handle_recorder_stopped(self, msg):
        # Kullanıcı stop_process() çağırmadan recorder dışarıdan sonlanırsa
        # arayüzün "kayıt sürüyor" durumunda kilitli kalmasını önler.
        if not self.recording:
            return

        stop_time = time.time()

        if self.record_start_time_segment:
            self.cumulative_time += stop_time - self.record_start_time_segment

        self.record_start_time_segment = None
        self.time_timer.stop()
        self.recording = False

        if self.recorder_thread and not self.recorder_thread.isRunning():
            self.recorder_thread = None

        self.updateTimeLabel()
        self.updateMainPlayPauseButtonState()
        self.info_label.setText("Kayıt Durduruldu")
        self._update_panel_state()
        self._schedule_preview_sync()

    def _pause_recording_session(self):
        stop_time = time.time()
        if self._native_session_alive():
            # Yerel motor: süreç açık kalır, dosya tek parça sürer (zaman damgaları kesintisiz)
            self.recorder_thread.pause()
        elif self.recorder_thread and self.recorder_thread.isRunning():
            self.recorder_thread.stop_process()
            self.recorder_thread.wait()
            self.recorder_thread = None
        if self.record_start_time_segment:
            self.cumulative_time += stop_time - self.record_start_time_segment
        self.record_start_time_segment = None
        self.time_timer.stop()
        self.recording = False
        self.updateMainPlayPauseButtonState()
        self.info_label.setText("Kayıt Duraklatıldı")
        self._update_panel_state()
        self._schedule_preview_sync()

    def _stop_full_recording_session(self, cleanup=True):
        if self.recorder_thread and self.recorder_thread.isRunning():
            self.recorder_thread.stop_process()
            self.recorder_thread.wait()
            self.recorder_thread = None
        self.time_timer.stop()
        self.recording = False
        self.updateMainPlayPauseButtonState()
        self.info_label.setText("Video Önizlemesi Yok")
        self._update_panel_state()
        self._schedule_preview_sync()
        if cleanup:
            self._cleanup_segments()
            self.cumulative_time = 0
            self.updateTimeLabel()

    def handleMainPlayPause(self):
        if self.playback_mode: self.togglePlayback()
        else: self.toggleRecording()

    def toggleRecording(self):
        if self.playback_mode:
            QMessageBox.information(self, "Kayıt Engellendi", "Oynatma devam ederken kayıt başlatılamaz.")
            return
        if not self.windows_active and not self.sound_active:
            QMessageBox.information(self, "Kayıt Başlatılamadı", "'Sound' veya 'Windows' modunu aktif hale getirin.")
            return

        if not self.recording and self._native_session_alive():
            # Duraklatılmış oturum: aynı dosyaya devam et
            self._resume_native_recorder()
            self.record_start_time_segment = time.time()
            self.time_timer.start()
            self.recording = True
        elif not self.recording:
            if not self._start_recorder():
                self.recording = False
                self.record_start_time_segment = None
                self.updateMainPlayPauseButtonState()
                return

            self.record_start_time_segment = time.time()
            self.time_timer.start()
            self.recording = True
        else:
            self._pause_recording_session()

        self.updateMainPlayPauseButtonState()

    def updateTimeLabel(self):
        if self.recording and self.record_start_time_segment:
            total = self.cumulative_time + (time.time() - self.record_start_time_segment)
        else:
            total = self.cumulative_time
        h = int(total // 3600)
        m = int((total % 3600) // 60)
        s = int(total % 60)
        txt = f"{h:02d}:{m:02d}:{s:02d}"
        self.time_label.setText(txt)
        self._update_overlay(txt)

    # ─── Yerel (C++) motor, ekran önizlemesi, yüzen kamera ve ses paneli ───────

    def _native_available(self):
        return bool(self.camera_recorder_path) and bool(getattr(self, 'native_caps', None))

    def _portal_restore_ok(self):
        return self.native_caps.get('portal_restore', '0') == '1'

    def _screen_preview_allowed(self):
        """Wayland'da portal izni hatırlanamıyorsa (portal < v4) ekran önizlemesi
        her seferinde izin penceresi açacağından yalnızca kayıt sırasında gösterilir."""
        if not self.windows_active:
            return False
        if self.display_server == 'wayland' and not self._portal_restore_ok():
            return False
        return True

    def _screen_region(self):
        """Çok monitörlü X11'de birincil ekranın bölgesi (tek monitörde None → tüm ekran)."""
        try:
            if len(QApplication.screens()) <= 1:
                return None
            scr = QApplication.primaryScreen()
            g = scr.geometry()
            r = scr.devicePixelRatio()
            return int(g.x() * r), int(g.y() * r), int(g.width() * r), int(g.height() * r)
        except Exception:
            return None

    def _audio_source_cached(self):
        # pactl her çağrıda çalışmasın (önizleme eşitlemesi sık tetiklenir)
        now = time.time()
        cache = getattr(self, '_audio_src_cache', None)
        if cache and now - cache[0] < 5.0 and cache[2] == AUDIO_SOURCE_OVERRIDE:
            return cache[1]
        src = get_audio_source()
        self._audio_src_cache = (now, src, AUDIO_SOURCE_OVERRIDE)
        return src

    def _build_native_args(self, record):
        """Ekran + ses için C++ argümanları. Kayıt: tek dosya, süre sınırı yok."""
        a = ["--record" if record else "--preview"]

        def kv(k, v):
            a.append(f"{k}={v}")

        screen_on = self.windows_active if record else self._screen_preview_allowed()

        if record:
            w, h = self._resolution_to_wh()
            kv("dir", SEGMENT_DIR)
            kv("start", self._get_next_segment_number(SEGMENT_DIR))
            kv("fps", self.selected_fps)
            kv("w", w)
            kv("h", h)

        if screen_on:
            kv("screen", self.display_server)
            if self.display_server == 'x11':
                reg = self._screen_region()
                if reg:
                    kv("rx", reg[0]); kv("ry", reg[1]); kv("rw", reg[2]); kv("rh", reg[3])

        if self.sound_active:
            kv("audio", self._audio_source_cached())
            kv("rate", self.selected_audio_rate)

        if screen_on:
            kv("pv_screen", PV_SCREEN_PATH)
        if self.sound_active:
            kv("pv_audio", PV_AUDIO_PATH)
        kv("pv_w", 960)
        kv("pv_fps", 8)
        return a

    def _build_camera_args(self):
        cw, ch = CAMERA_RESOLUTIONS.get(self.camera_resolution, (640, 480))
        return ["--preview", f"camera={self.camera_device or 'auto'}", f"cw={cw}", f"ch={ch}",
                f"pv_camera={PV_CAMERA_PATH}", f"pv_cw={cw}", "pv_cfps=15"]

    # ── kayıt oturumu (tek süreç, tek dosya; duraklat/devam aynı dosyada sürer) ──
    def _native_session_alive(self):
        t = self.recorder_thread
        return isinstance(t, NativeEngine) and t.isRunning()

    def _start_native_recorder(self):
        # Ekran/ses aygıtları için önce ana önizleme sürecini bırak (kamera önizlemesi kesintisiz sürer)
        self._stop_preview_now()
        args = self._build_native_args(True)
        rt = NativeEngine(self.camera_recorder_path, args)
        rt.recording_started.connect(self._on_native_recording_started)
        rt.recording_stopped.connect(self._handle_recorder_stopped)
        rt.error_occurred.connect(self._handle_recorder_error)
        self.recorder_thread = rt
        rt.start()

        parts = []
        if self.windows_active: parts.append("Ekran")
        if self.sound_active:   parts.append("Ses")
        fmt = "WAV" if parts == ["Ses"] else "MKV"
        self.info_label.setText(" + ".join(parts) + f" Kaydı Aktif ({fmt})")
        if self.overlay_visible:
            self._ensure_overlay()
        self.info_label.show()
        self.video_widget.hide()
        self._update_panel_state()
        return rt.isRunning()

    def _resume_native_recorder(self):
        self._stop_preview_now()
        self.recorder_thread.resume()
        self.info_label.show()
        self.video_widget.hide()
        self._update_panel_state()

    def _on_native_recording_started(self, msg):
        # Süre sayacı, motor gerçekten çalışmaya başladığında (ör. Wayland izninden sonra) başlar
        if not self.recording or self.recorder_thread is None:
            return
        self.record_start_time_segment = time.time()

    # ── arayüz durumu ──
    def _update_panel_state(self):
        if getattr(self, 'audio_panel', None) is None:
            return
        usable = (self._native_available() and not self.playback_mode
                  and not self.isFullScreen() and not self._closing)
        self.audio_panel.configure(usable and self.sound_active)
        self.info_label.set_preview(usable and self.windows_active)
        self.info_label.set_recording(bool(self.recording))
        if usable and self.camera_active:
            self._ensure_camera_overlay()
        else:
            self._close_camera_overlay()

    def _ensure_camera_overlay(self):
        if self.camera_overlay is None:
            geom = self.camera_overlay_geom
            width = geom[2] if geom else 260
            self.camera_overlay = CameraOverlay(self, PV_CAMERA_PATH, width, self.preview_mirror)
            self.camera_overlay.context_requested.connect(self._show_preview_menu)
            if geom:
                self.camera_overlay.move(geom[0], geom[1])
            else:
                screen = QApplication.desktop().screenGeometry()
                self.camera_overlay.move(screen.left() + 20,
                                         screen.bottom() - self.camera_overlay.height() - 60)
        if not self.camera_overlay.isVisible():
            self.camera_overlay.start()

    def _close_camera_overlay(self):
        if self.camera_overlay is not None:
            try:
                self.camera_overlay.stop()
                self.camera_overlay.close()
            except RuntimeError:
                pass
            self.camera_overlay = None

    # ── önizleme süreçleri: ana (ekran+ses) ve kamera ayrı ayrı yönetilir ──
    def _schedule_preview_sync(self, delay=0):
        if getattr(self, '_preview_sync_pending', False):
            return
        self._preview_sync_pending = True
        QTimer.singleShot(delay, self._sync_preview)

    def _desired_main_preview(self):
        if (not self._native_available() or self._closing or self.recording
                or self.playback_mode or self.isFullScreen()):
            return None
        if not (self._screen_preview_allowed() or self.sound_active):
            return None
        return tuple(self._build_native_args(False))

    def _desired_camera_preview(self):
        if (not self._native_available() or self._closing or self.playback_mode
                or not self.camera_active):
            return None
        return tuple(self._build_camera_args())

    def _sync_preview(self):
        self._preview_sync_pending = False
        if getattr(self, 'audio_panel', None) is None:
            return
        self._update_panel_state()

        desired = self._desired_main_preview()
        if not (desired == self._preview_sig and (desired is None or self._preview_runner is not None)):
            self._stop_preview_now()
            if self.windows_active and not self._screen_preview_allowed() and not self.recording:
                self.info_label.setText("Wayland: bu sistemde ekran önizlemesi\nkayıt başlayınca görünür.")
            if desired is not None:
                runner = NativeEngine(self.camera_recorder_path, list(desired), preview_only=True)
                runner.finished_code.connect(lambda c, m, rr=runner: self._on_preview_finished(c, m, rr))
                self._preview_runner = runner
                self._preview_sig = desired
                runner.start()

        cdesired = self._desired_camera_preview()
        if not (cdesired == self._cam_sig and (cdesired is None or self._cam_runner is not None)):
            self._stop_preview_now(camera=True)
            if cdesired is not None:
                runner = NativeEngine(self.camera_recorder_path, list(cdesired), preview_only=True)
                runner.finished_code.connect(lambda c, m, rr=runner: self._on_camera_preview_finished(c, m, rr))
                self._cam_runner = runner
                self._cam_sig = cdesired
                runner.start()

    def _stop_preview_now(self, camera=False):
        if camera:
            r, self._cam_runner, self._cam_sig = self._cam_runner, None, None
        else:
            r, self._preview_runner, self._preview_sig = self._preview_runner, None, None
        if r is not None:
            r.stop_process(timeout=5)
            if not r.wait(5000):
                self._zombie_threads.append(r)     # QThread çalışırken yok edilmesin
        if camera:
            if self.camera_overlay is not None:
                self.camera_overlay.reset_frame()
        elif getattr(self, 'audio_panel', None) is not None:
            self.info_label.reset_frame()
            self.audio_panel.reset()

    def _stop_all_preview(self):
        self._stop_preview_now()
        self._stop_preview_now(camera=True)

    def _restart_preview(self):
        self._stop_all_preview()
        self._schedule_preview_sync()

    def _on_preview_finished(self, code, msg, runner):
        if runner is not self._preview_runner or not msg:
            return
        print(f"Python: Önizleme motoru kapandı (kod {code}): {msg}")
        if code == 3:
            self.info_label.setText("Ekran paylaşımı izni verilmedi.\n(Rec ile kayıt başlarken tekrar sorulur)")
        elif code != 4:
            self.info_label.setText(msg.splitlines()[0])

    def _on_camera_preview_finished(self, code, msg, runner):
        if runner is not self._cam_runner or not msg:
            return
        print(f"Python: Kamera önizlemesi kapandı (kod {code}): {msg}")
        if self.camera_overlay is not None:
            self.camera_overlay.set_message(msg.splitlines()[0])

    # ── seçenekler ──
    def _set_camera_device(self, dev):
        self.camera_device = dev
        self.save_overlay_settings()
        self._restart_preview()

    def _set_camera_resolution(self, name):
        self.camera_resolution = name
        self.save_overlay_settings()
        self._restart_preview()

    def _set_preview_mirror(self, on):
        self.preview_mirror = bool(on)
        if self.camera_overlay is not None:
            self.camera_overlay.set_mirror(self.preview_mirror)
        self.save_overlay_settings()

    def _set_audio_source(self, name):
        global AUDIO_SOURCE_OVERRIDE
        self.audio_source_choice = name
        AUDIO_SOURCE_OVERRIDE = name
        self.save_overlay_settings()
        self._restart_preview()

    def _show_preview_menu(self, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #282828; color: white; border: 1px solid #555; }
            QMenu::item { padding: 5px 30px 5px 20px; }
            QMenu::item:selected { background-color: #444; }
            QMenu::item:disabled { color: #777; }
            QMenu::separator { height: 1px; background: #555; margin: 2px 0px; }
        """)
        cam_menu = menu.addMenu("Kamera")
        act_auto = cam_menu.addAction("Otomatik")
        act_auto.setCheckable(True)
        act_auto.setChecked(not self.camera_device)
        act_auto.triggered.connect(lambda: self._set_camera_device(""))
        for path, name in list_cameras(self.camera_recorder_path):
            act = cam_menu.addAction(f"{name}  ({path})")
            act.setCheckable(True)
            act.setChecked(self.camera_device == path)
            act.triggered.connect(lambda checked, p=path: self._set_camera_device(p))
        cam_menu.addSeparator()
        for res_name, (rw, rh) in CAMERA_RESOLUTIONS.items():
            act = cam_menu.addAction(f"Çözünürlük {rw}x{rh}")
            act.setCheckable(True)
            act.setChecked(self.camera_resolution == res_name)
            act.triggered.connect(lambda checked, n=res_name: self._set_camera_resolution(n))
        cam_menu.addSeparator()
        act_mirror = cam_menu.addAction("Görüntüyü aynala")
        act_mirror.setCheckable(True)
        act_mirror.setChecked(self.preview_mirror)
        act_mirror.triggered.connect(lambda checked: self._set_preview_mirror(checked))

        aud_menu = menu.addMenu("Ses kaynağı")
        aud_menu.setEnabled(not self._native_session_alive())     # kayıt oturumu açıkken değiştirilemez
        act_a = aud_menu.addAction("Otomatik (EasyEffects / varsayılan)")
        act_a.setCheckable(True)
        act_a.setChecked(not self.audio_source_choice)
        act_a.triggered.connect(lambda: self._set_audio_source(""))
        for name, is_monitor in list_audio_sources():
            act = aud_menu.addAction(("Sistem sesi: " if is_monitor else "") + name)
            act.setCheckable(True)
            act.setChecked(self.audio_source_choice == name)
            act.triggered.connect(lambda checked, n=name: self._set_audio_source(n))

        menu.addSeparator()
        act_ref = menu.addAction("Önizlemeyi yenile")
        act_ref.setEnabled(not self.recording)
        act_ref.triggered.connect(self._restart_preview)
        menu.exec_(global_pos)

    def showEvent(self, event):
        super().showEvent(event)
        self._update_panel_state()
        self._schedule_preview_sync(250)


    # ─── Yeni Segment UI & Silme İşlemleri ────────────────────────────────────

    def sort_segment_files(self, filename):
        match = re.search(r'^s(\d+)\.', os.path.basename(filename))
        return int(match.group(1)) if match else 0

    def updateSegmentUI(self):
        current_files = self._get_segment_files(full_path=False)
        if hasattr(self, '_last_files') and self._last_files == current_files:
            return
        self._last_files = current_files
        self.export_button.setEnabled(len(current_files) > 0)

    def _has_segments(self):
        return len(self._get_segment_files()) > 0

    def _get_segment_files(self, full_path=False):
        segs = []
        if not os.path.exists(SEGMENT_DIR): return segs
        try:
            for fn in os.listdir(SEGMENT_DIR):
                if re.match(r'^s\d+\.(mkv|wav)$', fn):
                    fp = os.path.join(SEGMENT_DIR, fn)
                    segs.append(fp if full_path else fn)
        except Exception as e:
            print(f"Python Hata: Segment okunurken: {e}")
        return segs

    def _cleanup_segments(self):
        for fp in self._get_segment_files(full_path=True):
            try: os.remove(fp)
            except Exception: pass
        self.updateSegmentUI()

    # ─── Dışa Aktarma ve Filtreleme ───────────────────────────────────────────

    def _filter_media_file(self, input_path, is_video, callback):
        if not self.noise_filter_enabled:
            callback(input_path)
            return

        if not self.core_window_ref:
            callback(input_path)
            return

        try:
            filter_win = self.core_window_ref.get_filter_window()
            if filter_win and hasattr(filter_win, 'profile_manager'):
                filter_win.profile_manager.ensure_at_least_one_active()
        except Exception as e:
            print(f"Filtre aktifleştirme hatası: {e}")

        if is_video:
            temp_dir = tempfile.mkdtemp(prefix="camera_filter_")
            extracted_audio = os.path.join(temp_dir, "extracted_audio.wav")
            cmd_extract = [FFMPEG_PATH, '-y', '-i', input_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '48000', '-ac', '1', extracted_audio]
            try:
                subprocess.run(cmd_extract, check=True, capture_output=True, text=True)
            except Exception as e:
                shutil.rmtree(temp_dir, ignore_errors=True)
                callback(input_path)
                return

            def on_audio_filtered(success, filtered_audio_path, message):
                if success and filtered_audio_path and os.path.exists(filtered_audio_path):
                    base, ext = os.path.splitext(input_path)
                    output_video = f"{base}_filtered{ext}"
                    counter = 1
                    while os.path.exists(output_video):
                        output_video = f"{base}_filtered_{counter}{ext}"
                        counter += 1
                    cmd_merge = [FFMPEG_PATH, '-y', '-i', input_path, '-i', filtered_audio_path, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-map', '0:v:0', '-map', '1:a:0', '-shortest', output_video]
                    try:
                        subprocess.run(cmd_merge, check=True, capture_output=True, text=True)
                        callback(output_video)
                    except Exception:
                        callback(input_path)
                else:
                    callback(input_path)
                shutil.rmtree(temp_dir, ignore_errors=True)

            self.core_window_ref.process_audio_with_filter(extracted_audio, on_audio_filtered)
        else:
            def on_audio_filtered(success, filtered_audio_path, message):
                if success and filtered_audio_path and os.path.exists(filtered_audio_path):
                    callback(filtered_audio_path)
                else:
                    callback(input_path)
            self.core_window_ref.process_audio_with_filter(input_path, on_audio_filtered)

    def exportRecording(self):
        if self.recording:
            QMessageBox.warning(self, "Dışa Aktarılamadı", "Önce kaydı duraklatın.")
            return
        if self.playback_mode:
            QMessageBox.information(self, "Dışa Aktarma Engellendi", "Oynatma devam ederken dışa aktarılamaz.")
            return
        if self.recorder_thread and self.recorder_thread.isRunning():
            self._stop_full_recording_session(cleanup=False)

        all_segs = self._get_segment_files(full_path=True)
        if not all_segs:
            QMessageBox.information(self, "Dışa Aktarılamadı", "Dışa aktarılacak kayıt yok.")
            return

        video_segs = sorted(
            [f for f in all_segs if f.lower().endswith(".mkv")],
            key=self.sort_segment_files
        )
        audio_segs = sorted(
            [f for f in all_segs if f.lower().endswith(".wav")],
            key=self.sort_segment_files
        )

        has_video = bool(video_segs)
        has_audio = bool(audio_segs)
        ext = ".mkv" if has_video else ".wav"

        out_path, _ = _fm.get_save_file_name(
            self, "Kaydı Dışa Aktar", DEFAULT_BASE_DIR,
            ("MKV Video Dosyası (*.mkv)" if has_video else "WAV Ses Dosyası (*.wav)"), editor="Rec")
        if not out_path:
            return
        if not out_path.lower().endswith(ext):
            out_path += ext

        progress = QProgressDialog("Dışa aktarılıyor...", "İptal", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("İşleniyor")
        progress.show()

        temp_paths = []

        def make_temp(suffix):
            fd, path = tempfile.mkstemp(prefix="camera_export_", suffix=suffix)
            os.close(fd)
            temp_paths.append(path)
            return path

        def make_concat_list(paths):
            list_path = make_temp(".txt")
            with open(list_path, "w", encoding="utf-8") as lfile:
                for seg in paths:
                    # FFmpeg concat demuxer için tek tırnaklı yolları güvenli biçimde kaçır.
                    escaped = os.path.abspath(seg).replace("\\", "\\\\").replace("'", "'\\''")
                    lfile.write(f"file '{escaped}'\n")
            return list_path

        try:
            progress.setLabelText("Segmentler birleştiriliyor...")
            progress.setValue(10)
            QApplication.processEvents()

            video_concat = None
            audio_concat = None

            if has_video:
                video_list = make_concat_list(video_segs)
                video_concat = make_temp(".mkv")
                r = subprocess.run(
                    [FFMPEG_PATH, '-y', '-f', 'concat', '-safe', '0',
                     '-i', video_list, '-c', 'copy', video_concat],
                    capture_output=True, text=True, encoding='utf-8')
                if r.returncode != 0:
                    raise RuntimeError(f"Video segmentleri birleştirilemedi:\n{r.stderr}")

            if has_audio:
                audio_list = make_concat_list(audio_segs)
                audio_concat = make_temp(".wav")
                r = subprocess.run(
                    [FFMPEG_PATH, '-y', '-f', 'concat', '-safe', '0',
                     '-i', audio_list, '-c', 'copy', audio_concat],
                    capture_output=True, text=True, encoding='utf-8')
                if r.returncode != 0:
                    raise RuntimeError(f"Ses segmentleri birleştirilemedi:\n{r.stderr}")

            # Wayland birleşik kayıtlarında video ve ses ayrı segmentlendiği için
            # önce kendi türlerinde birleştirilir, sonra tek MKV içinde mux edilir.
            if has_video and has_audio:
                media_path = make_temp(".mkv")
                r = subprocess.run(
                    [FFMPEG_PATH, '-y',
                     '-i', video_concat,
                     '-i', audio_concat,
                     '-map', '0:v:0',
                     '-map', '1:a:0',
                     '-c:v', 'copy',
                     '-c:a', 'aac',
                     '-b:a', '192k',
                     '-shortest',
                     media_path],
                    capture_output=True, text=True, encoding='utf-8')
                if r.returncode != 0:
                    raise RuntimeError(f"Video ve ses birleştirilemedi:\n{r.stderr}")
                is_video_file = True
            elif has_video:
                media_path = video_concat
                is_video_file = True
            else:
                media_path = audio_concat
                is_video_file = False

            progress.setLabelText("Filtre uygulanıyor...")
            progress.setValue(50)
            QApplication.processEvents()

            def on_filtered(final_path):
                try:
                    shutil.copy2(final_path, out_path)
                    progress.setValue(100)
                    _fm.notify_saved(self)
                    self.cumulative_time = 0
                    self.updateTimeLabel()
                    self.info_label.setText("Video Önizlemesi Yok")
                    self._cleanup_segments()
                    self.updateMainPlayPauseButtonState()
                except Exception as e:
                    QMessageBox.critical(self, "Dışa Aktarma Hatası", str(e))
                finally:
                    progress.close()
                    for path in temp_paths:
                        if path and os.path.exists(path):
                            try:
                                os.remove(path)
                            except Exception:
                                pass

            self._filter_media_file(media_path, is_video_file, on_filtered)

        except Exception as e:
            QMessageBox.critical(self, "Dışa Aktarma Hatası", str(e))
            progress.close()
            for path in temp_paths:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception:
                        pass

    # ─── Diğer Olaylar ────────────────────────────────────────────────────────

    def cameraButtonClicked(self):
        mw = self.window()
        if hasattr(mw, 'showSwitcher'): mw.showSwitcher()

    def showCameraFeatureWindow(self):
        if self.camera_feature_window is None:
            self.camera_feature_window = CameraFeatureWindow()
        self.camera_feature_window.show()

    def openFileForPlayback(self):
        if self.recording:
            QMessageBox.warning(self, "Engellendi", "Kayıt devam ederken dosya oynatılamaz.")
            return
        self._stop_full_recording_session()
        fp, _ = _fm.get_open_file_name(
            self, "Dosya Seç", DEFAULT_BASE_DIR,
            "Desteklenen Kayıtlar (*.rec *.mp4 *.mkv *.wav);;Video (*.rec *.mp4 *.mkv);;Ses (*.wav)", editor="Rec")
        if not fp: return
        self.closePlaybackBar()
        self._open_playback_file(fp)

    def load_file(self, fp):
        if not os.path.exists(fp):
            QMessageBox.critical(self, "Dosya Bulunamadı", fp); return
        self._stop_full_recording_session()
        self.closePlaybackBar()
        self._open_playback_file(fp)

    def _open_playback_file(self, fp):
        self.playback_filepath = fp
        ext = os.path.splitext(fp)[1].lower()
        if ext in [".rec",".mp4",".mkv"]: self.startVideoPlayback(fp)
        elif ext == ".wav":               self.startAudioPlayback(fp)
        else:
            QMessageBox.warning(self, "Desteklenmeyen Dosya", ".rec .mp4 .mkv .wav bekleniyor")
            self.playback_filepath = None; return

        self.playback_bar_frame.show()
        total = self.height() - self.toolbar_frame.height()
        pbh   = self.playback_bar_frame.height()
        avail = max(100, total - pbh)
        self.splitter.setSizes([avail, total - avail])
        self.is_playing = True
        self.updateMainPlayPauseButtonState()
        self.main_play_pause_button.setEnabled(True)
        self.main_close_playback_button.setEnabled(True)
        if self.playback_mode == "audio": self.audio_playback_timer.start()
        self.disableRecordingButtons(True)
        self._update_panel_state()
        self._schedule_preview_sync()

    def togglePlayback(self):
        if not self.playback_mode or not self.playback_filepath: return
        if self.is_playing:
            self.is_playing = False
            self.updateMainPlayPauseButtonState()
            if self.playback_mode == "video": self.player.pause()
            elif self.playback_mode == "audio" and self.audio_player_process:
                if self.audio_player_process.poll() is None:
                    self.audio_player_process.terminate()
                    self.audio_player_process.wait()
                self.audio_player_process = None
                self.audio_playback_timer.stop()
        else:
            self.is_playing = True
            self.updateMainPlayPauseButtonState()
            if self.playback_mode == "video": self.player.play()
            elif self.playback_mode == "audio":
                ct = self.playback_duration_seconds * (self.playback_slider.value()/100.0)
                try:
                    self.audio_player_process = subprocess.Popen(
                        [FFPLAY_PATH, '-nodisp','-autoexit','-loglevel','quiet','-ss',str(ct),self.playback_filepath],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self.playback_start_time = time.time() - ct
                except Exception as e:
                    QMessageBox.critical(self,"Ses Hatası",str(e)); self.closePlaybackBar()
                self.audio_playback_timer.start()

    def startVideoPlayback(self, fp):
        self.playback_mode = "video"
        self.player.setVideoOutput(self.video_widget)
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(fp)))
        self.info_label.hide(); self.video_widget.show()
        self.playback_slider.setValue(0); self.playback_slider.red_line_position = 0
        self.playback_slider.update()
        self.playback_time_label.setText("00:00")
        self.playback_total_time_label.setText("00:00")
        self.player.play()

    def startAudioPlayback(self, fp):
        self.playback_mode = "audio"
        self.player.setVideoOutput(None); self.video_widget.hide()
        try:
            r = subprocess.run(
                [FFPROBE_PATH, '-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',fp],
                capture_output=True, text=True, check=True)
            self.playback_duration_seconds = float(r.stdout.strip())
        except Exception as e:
            QMessageBox.critical(self,"Ses Hatası",str(e)); self.closePlaybackBar(); return
        try:
            self.audio_player_process = subprocess.Popen(
                [FFPLAY_PATH, '-nodisp','-autoexit','-loglevel','quiet',fp],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.playback_start_time = time.time()
            self.info_label.setText(f"Ses: {os.path.basename(fp)}"); self.info_label.show()
            self.playback_slider.setValue(0); self.playback_slider.red_line_position = 0
            self.playback_slider.update()
            self.playback_time_label.setText("00:00")
            self.playback_total_time_label.setText(self.formatTime(self.playback_duration_seconds))
            self.audio_playback_timer.start()
        except Exception as e:
            QMessageBox.critical(self,"Ses Hatası",str(e)); self.closePlaybackBar()

    def _handle_player_state_changed(self, state):
        self.is_playing = (state == QMediaPlayer.PlayingState)
        self.updateMainPlayPauseButtonState()
        if state == QMediaPlayer.StoppedState:
            self.playback_slider.setValue(100); self.playback_slider.red_line_position = 100
            self.playback_slider.update()
            if getattr(self,'playback_duration_seconds',0) > 0:
                self.playback_time_label.setText(self.formatTime(self.playback_duration_seconds))
            self.closePlaybackBar()

    def _handle_player_position_changed(self, pos_ms):
        if self.playback_mode == "video" and self.player.duration() > 0:
            pct = (pos_ms / self.player.duration()) * 100
            self.playback_slider.setValue(int(pct))
            self.playback_slider.red_line_position = int(pct)
            self.playback_slider.update()
            self.playback_time_label.setText(self.formatTime(pos_ms/1000.0))

    def _handle_player_duration_changed(self, dur_ms):
        if dur_ms > 0:
            self.playback_duration_seconds = dur_ms / 1000.0
            self.playback_total_time_label.setText(self.formatTime(self.playback_duration_seconds))

    def _handle_player_error(self, error):
        QMessageBox.critical(self,"Playback Error",self.player.errorString())
        self.closePlaybackBar()

    def updateAudioPlaybackProgress(self):
        if not self.is_playing: return
        if self.playback_mode == "audio" and self.audio_player_process:
            if self.audio_player_process.poll() is None:
                elapsed = time.time() - self.playback_start_time
                if self.playback_duration_seconds > 0:
                    pct = (elapsed / self.playback_duration_seconds) * 100
                    self.playback_slider.setValue(int(pct))
                    self.playback_slider.red_line_position = int(pct)
                    self.playback_slider.update()
                    self.playback_time_label.setText(self.formatTime(elapsed))
            else:
                self.playback_slider.setValue(100)
                self.playback_slider.red_line_position = 100
                self.playback_slider.update()
                self.is_playing = False
                self.updateMainPlayPauseButtonState()
                self.closePlaybackBar()

    def seekPlayback(self, val):
        if self.playback_mode == "video" and self.player.mediaStatus() != QMediaPlayer.NoMedia:
            self.player.setPosition(int(self.player.duration() * val / 100.0))
            self.playback_slider.red_line_position = val; self.playback_slider.update()
        elif self.playback_mode == "audio" and self.playback_filepath:
            if self.audio_player_process and self.audio_player_process.poll() is None:
                self.audio_player_process.terminate(); self.audio_player_process.wait()
            st = self.playback_duration_seconds * (val / 100.0)
            try:
                self.is_playing = True; self.updateMainPlayPauseButtonState()
                self.audio_player_process = subprocess.Popen(
                    [FFPLAY_PATH, '-nodisp','-autoexit','-loglevel','quiet','-ss',str(st),self.playback_filepath],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.playback_start_time = time.time() - st
                self.playback_slider.red_line_position = val; self.playback_slider.update()
                self.audio_playback_timer.start()
            except Exception as e:
                self.is_playing = False; self.updateMainPlayPauseButtonState()

    def closePlaybackBar(self):
        if self.playback_mode == "video":
            self.player.stop(); self.player.setMedia(QMediaContent())
            self.video_widget.hide()
            self.info_label.setText("Video Önizlemesi Yok"); self.info_label.show()
        elif self.playback_mode == "audio" and self.audio_player_process:
            if self.audio_player_process.poll() is None:
                self.audio_player_process.terminate(); self.audio_player_process.wait()
            self.audio_player_process = None; self.audio_playback_timer.stop()
            self.info_label.setText("Video Önizlemesi Yok"); self.info_label.show()

        self.playback_bar_frame.hide()
        self.splitter.setSizes([self.height()-self.toolbar_frame.height(), 0])
        self.playback_mode = None; self.playback_filepath = None; self.is_playing = False
        self.playback_slider.setValue(0); self.playback_slider.red_line_position = 0
        self.playback_slider.update()
        self.playback_time_label.setText("00:00"); self.playback_total_time_label.setText("00:00")
        self.disableRecordingButtons(False)
        self.main_play_pause_button.setEnabled(True)
        self.main_close_playback_button.setEnabled(False)
        self.updateMainPlayPauseButtonState()
        self._update_panel_state()
        self._schedule_preview_sync()

    def disableRecordingButtons(self, disable):
        for w in [self.windows_button, self.sound_button, self.file_button]:
            w.setEnabled(not disable)
        # Camera: kayıt sırasında da kullanılabilir; yalnızca oynatma sırasında kapalı
        self.camera_button_feature.setEnabled(not self.playback_mode)
        self.export_button.setEnabled(self._has_segments())
        self.windows_button.setStyleSheet(
            self.toggleButtonStyle(self.windows_active) if not disable else self.disabledButtonStyle())
        self.sound_button.setStyleSheet(
            self.toggleButtonStyle(self.sound_active) if not disable else self.disabledButtonStyle())
        self.camera_button_feature.setStyleSheet(
            self.toggleButtonStyle(self.camera_active) if not self.playback_mode else self.disabledButtonStyle())
        self.file_button.setStyleSheet(
            self.buttonStyle() if not disable else self.disabledButtonStyle())
        self.export_button.setStyleSheet(
            self.buttonStyle() if self.export_button.isEnabled() else self.disabledButtonStyle())

    def updateMainPlayPauseButtonState(self):
        if getattr(self, 'info_label', None) is not None and hasattr(self.info_label, 'set_recording'):
            self.info_label.set_recording(bool(self.recording))
        if self.playback_mode:
            self.main_play_pause_button.setEnabled(True)
            self.main_close_playback_button.setEnabled(True)
            self.main_play_pause_button.setText("Pause" if self.is_playing else "Play")
            self.disableRecordingButtons(True)
            return
        if self.recording:
            self.main_play_pause_button.setEnabled(True)
            self.main_close_playback_button.setEnabled(False)
            self.main_play_pause_button.setText("Pause")
            self.disableRecordingButtons(True)
        elif self.windows_active or self.sound_active:
            self.main_play_pause_button.setEnabled(True)
            self.main_close_playback_button.setEnabled(False)
            self.main_play_pause_button.setText("Play")
            self.disableRecordingButtons(False)
        else:
            self.main_play_pause_button.setEnabled(False)
            self.main_close_playback_button.setEnabled(False)
            self.main_play_pause_button.setText("Play")
            self.disableRecordingButtons(False)
        if self.floating_overlay is not None:
            current_time = self.time_label.text()
            has_session = self.recording or self.cumulative_time > 0
            self.floating_overlay.update_display(current_time, self.recording, has_session)

    def formatTime(self, s):
        return f"{int(s//60):02d}:{int(s%60):02d}"

    def toggleFullscreen(self):
        if self.playback_mode == "video":
            if self.isFullScreen():
                self.showNormal(); self.toolbar_frame.show()
                self._update_panel_state()
                if self.playback_bar_frame.isHidden(): self.playback_bar_frame.show()
                total = self.height() - self.toolbar_frame.height()
                pbh   = self.playback_bar_frame.height()
                if total - pbh < 100: pbh = max(0, total - 100)
                self.splitter.setSizes([total - pbh, pbh])
            else:
                self.showFullScreen(); self.toolbar_frame.hide()
                self.audio_panel.hide()
                self.playback_bar_frame.hide()
                self.splitter.setSizes([self.height(), 0])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F: self.toggleFullscreen()
        elif event.key() == Qt.Key_B: self.handleMainPlayPause()
        else: super().keyPressEvent(event)

    def s_buton_denetimi(self):
        if QMessageBox.question(
            self, "Sistem Temizliği ve Sıfırlama",
            "Sistem temizlenecek ve üst bardaki tüm ayarlar varsayılana döndürülecek.\n\nOnaylıyor musunuz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) == QMessageBox.Yes:
            if self.recording or (self.recorder_thread and self.recorder_thread.isRunning()):
                self._stop_full_recording_session(cleanup=False)
            self._cleanup_segments()
            
            self.sound_active = False
            self.windows_active = False
            self.sound_button.setStyleSheet(self.toggleButtonStyle(False))
            self.windows_button.setStyleSheet(self.toggleButtonStyle(False))
            self.camera_active = False
            self.camera_button_feature.setStyleSheet(self.toggleButtonStyle(False))
            
            self.noise_filter_enabled = False
            self.noise_filter_button.setStyleSheet(self.buttonStylePressure(False))
            self._save_noise_filter_setting()
            
            if self.keystroke_display_enabled:
                self.keystroke_display_enabled = False
                self.keystroke_toggle_button.setStyleSheet(self.buttonStyleMini())
                self._stop_input_listener()
                if self.input_overlay is not None:
                    self.input_overlay.hide_input()
            
            if not getattr(self, 'overlay_visible', True):
                self.overlay_visible = True
                self.z_toggle_button.setStyleSheet(self.buttonStyleMiniPressed())

            self.overlay_thickness = 40
            self.thickness_button.thickness = 40
            self.thickness_button.setText("40")
            if self.floating_overlay:
                self.floating_overlay.set_thickness(40)
                self.floating_overlay.show()
            else:
                self._ensure_overlay()
            
            self.overlay_default_pos = None
            if self.floating_overlay:
                screen = QApplication.desktop().screenGeometry()
                self.floating_overlay.move(
                    screen.right() - 190,
                    screen.bottom() - 40 - 20
                )

            
            self.save_overlay_settings()  
            self._update_input_overlay_position()
            
            self.recorder_thread = None; self.recording = False
            self.cumulative_time = 0
            self.updateTimeLabel()
            self.updateSegmentUI()
            self.updateMainPlayPauseButtonState()
            
            self._update_panel_state()
            self._schedule_preview_sync()

            QMessageBox.information(self,"Başarılı",
                "Geçici klasör temizlendi.\n• Kayıtlar durduruldu\n• Modlar ve tüm ayarlar varsayılana sıfırlandı.")

    def closeEvent(self, event):
        self._closing = True
        self._stop_all_preview()
        self._close_camera_overlay()
        self._close_overlay()
        
        if hasattr(self, 'camera_feature_window') and self.camera_feature_window is not None:
            try:
                self.camera_feature_window.close()
            except:
                pass

        if self.recording or (self.recorder_thread and self.recorder_thread.isRunning()):
            msg = QMessageBox(self)
            msg.setWindowTitle("Kayıt Devam Ediyor")
            msg.setText("Kaydınız şu anda devam ediyor.\n\n"
                        "Pencereyi kapatmak istiyor musunuz?\n"
                        "(Kayıt otomatik olarak durdurulup temizlenecektir)")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            msg.setStyleSheet("""
                QMessageBox { background-color:#1e1e1e; color:white; }
                QLabel { color:white; font-size:14px; padding:10px; }
                QPushButton { padding:8px 20px; font-weight:bold; border-radius:4px; }
                QPushButton[text="Yes"] { background-color:#c42b1c; color:white; }
                QPushButton[text="No"]  { background-color:#333333; color:white; }
            """)
            if msg.exec_() == QMessageBox.Yes:
                if self.recording or (self.recorder_thread and self.recorder_thread.isRunning()):
                    self._stop_full_recording_session(cleanup=False)
                self._cleanup_segments()
                self.recording = False
                self.cumulative_time = 0
                self.updateTimeLabel()
                self.updateSegmentUI()
                self.updateMainPlayPauseButtonState()
                event.accept()
                QApplication.closeAllWindows()
            else:
                event.ignore()
                self._closing = False
                self._update_panel_state()
                self._schedule_preview_sync()
            return

        if self._has_segments():
            reply = QMessageBox.question(self, 'Çıkış Onayı',
                                         "Kaydedilmemiş segmentler var. Bunları silmek istiyor musunuz?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                self._cleanup_segments()
        
        event.accept()
        QApplication.closeAllWindows()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    icon_path = os.path.join(_KAVRAM_DIR, "ikon", "kavram.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    recorder = CameraRecorderWindow()

    def sigint_handler(*args):
        recorder.close()
        QApplication.quit()

    signal.signal(signal.SIGINT, sigint_handler)

    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    recorder.show()
    sys.exit(app.exec_())

