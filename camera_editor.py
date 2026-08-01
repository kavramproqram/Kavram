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

import sys, os, subprocess, time, cv2, tempfile, signal, platform, json
import datetime
import threading
import re
from collections import defaultdict
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QSplitter, QFileDialog, QMessageBox, QSlider,
    QStyle, QStyleOptionSlider, QSizePolicy, QProgressDialog, QDialog,
    QGridLayout, QComboBox, QSpacerItem, QShortcut, QMenu, QAction)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDir, QUrl, QPoint, QObject
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QKeySequence, QIcon

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

try:
    import soundfile as sf
    import numpy as np
    import noisereduce as nr
    import scipy.signal as sig
    import librosa
    from pydub import AudioSegment
    from pydub.effects import compress_dynamic_range
except ImportError:
    print("HATA: Gerekli kütüphaneler bulunamadı.")
    sys.exit(1)


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ---- Uygulama içi FFmpeg yolları (bin/ altında) ----
FFMPEG_PATH  = resource_path("bin/ffmpeg")
FFPROBE_PATH = resource_path("bin/ffprobe")
FFPLAY_PATH  = resource_path("bin/ffplay")

if not os.path.exists(FFMPEG_PATH):
    print(f"HATA: {FFMPEG_PATH} bulunamadı. Uygulama dizininde bin/ffmpeg olmalı.")
    sys.exit(1)
if not os.path.exists(FFPROBE_PATH):
    print(f"HATA: {FFPROBE_PATH} bulunamadı. Uygulama dizininde bin/ffprobe olmalı.")
    sys.exit(1)
if not os.path.exists(FFPLAY_PATH):
    print(f"HATA: {FFPLAY_PATH} bulunamadı. Uygulama dizininde bin/ffplay olmalı.")
    sys.exit(1)

if not os.access(FFMPEG_PATH, os.X_OK):
    print(f"HATA: {FFMPEG_PATH} çalıştırılabilir değil. Lütfen izinleri kontrol edin.")
    sys.exit(1)
if not os.access(FFPROBE_PATH, os.X_OK):
    print(f"HATA: {FFPROBE_PATH} çalıştırılabilir değil. Lütfen izinleri kontrol edin.")
    sys.exit(1)
if not os.access(FFPLAY_PATH, os.X_OK):
    print(f"HATA: {FFPLAY_PATH} çalıştırılabilir değil. Lütfen izinleri kontrol edin.")
    sys.exit(1)

VIDEO_FPS   = 12.0
AUDIO_RATE  = 48000

DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')
SEGMENT_DIR      = os.path.join(os.path.expanduser('~'), 'Kavram', '_v&s_')
SETTINGS_FILE    = resource_path("filter_settings c33.json")
OVERLAY_SETTINGS_FILE = resource_path("overlay_settings.json")


def load_cpp_library():
    print("Python Uyarısı: load_cpp_library çağrıldı, ancak bu fonksiyon artık işlevsel değil.")
    return True


def get_audio_source():
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
    except Exception as e:
        print(f"Python Uyarı: Ses kaynağı aranırken hata: {e}")
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
        
        # Stil: SİYAH arka plan, BEYAZ yazı
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

        # Kök container
        self._root = QWidget(self)
        self._root.setObjectName("overlay_root")
        self._root.setGeometry(0, 0, 170, self.thickness)
        
        # Layout
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
        
        # ── Ctrl+M: uygulama genelinde ────────────────────────────────
        self._shortcut = QShortcut(QKeySequence("Ctrl+M"), self)
        self._shortcut.setContext(Qt.ApplicationShortcut)
        self._shortcut.activated.connect(self._trigger_play_pause)

        # Sürükleme
        self._drag_active = False
        self._drag_offset = QPoint()

        # Başlangıç konumu: SAĞ alt
        screen = QApplication.desktop().screenGeometry()
        self.move(screen.right() - 190, screen.bottom() - self.thickness - 20)

    def set_thickness(self, value):
        """Kalınlığı ayarla"""
        self.thickness = value
        self.setFixedSize(170, self.thickness)
        self._root.setGeometry(0, 0, 170, self.thickness)

    def _trigger_play_pause(self):
        """Ctrl+M → ana pencerenin Play/Pause butonunu tetikler."""
        if self.recorder_window:
            self.recorder_window.main_play_pause_button.animateClick()

    def update_display(self, time_text: str, is_recording: bool, has_session: bool = True):
        """Ana penceredeki durum değişince çağrılır."""
        self.time_label.setText(time_text)
        if not has_session:
            self.status_label.hide()
        elif is_recording:
            self.status_label.setText("Pause")
            self.status_label.show()
        else:
            self.status_label.setText("Play")
            self.status_label.show()

    # ── Mouse: Ctrl + Sol Tık + Sürükle ──────────────────────────────
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
            # InputOverlay konumunu güncelle
            if self.recorder_window:
                self.recorder_window._update_input_overlay_position()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and getattr(self, '_drag_active', False):
            self._drag_active = False
            # Sürükleme bittiğinde yeni pozisyonu kaydet
            if self.recorder_window:
                pos = self.pos()
                self.recorder_window.overlay_default_pos = (pos.x(), pos.y())
                self.recorder_window.save_overlay_settings()
        super().mouseReleaseEvent(event)


# =============================================================================
# InputOverlay – Klavye/Mouse/Tablet input gösterimi (üst pencere)
# =============================================================================
class InputOverlay(QWidget):
    """
    Input gösterimi için ayrı pencere.
    • FloatingOverlay'in üstünde konumlanır
    • Aynı tasarım (siyah arka plan, beyaz yazı)
    • Aynı kalınlık ve genişlik
    • Çok satırlı input için yukarı doğru genişler (max 5 kat)
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
        
        self.base_thickness = thickness  # Tek satır yüksekliği
        self.current_lines = 0  # Mevcut satır sayısı
        
        # 1.5 saniye tuşları ekranda tutma timer'ı
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._do_hide)
        
        # Sürükleme state
        self._drag_active = False
        self._drag_offset = QPoint()
        
        # Stil: SİYAH arka plan, BEYAZ yazı
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

        # Kök container
        self._root = QWidget(self)
        self._root.setObjectName("input_root")
        
        # Layout
        self.layout = QVBoxLayout(self._root)
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(2)
        
        # Input etiketi
        self.input_label = QLabel("")
        self.input_label.setStyleSheet("""
            font-size: 14px; 
            font-weight: bold; 
            color: white;
        """)
        self.input_label.setAlignment(Qt.AlignCenter)
        self.input_label.setWordWrap(True)
        self.layout.addWidget(self.input_label)
        
        # Başlangıçta gizli
        self.setFixedSize(170, self.base_thickness)
        self._root.setGeometry(0, 0, 170, self.base_thickness)
        self.hide()

    def set_thickness(self, value):
        """Temel kalınlığı ayarla"""
        self.base_thickness = value
        if self.current_lines <= 1:
            self.setFixedSize(170, self.base_thickness)
            self._root.setGeometry(0, 0, 170, self.base_thickness)

    def show_input(self, text: str):
        """Input göster - gerekirse yukarı doğru büyü"""
        if not text:
            # Boş yollanırsa 1.5 saniye sonra ekranı temizle
            self.hide_timer.start(1500)
            return
            
        # Yeni bir tuşa basılırsa hemen timer'ı durdur ve göster
        self.hide_timer.stop()
        self.input_label.setText(text)
        
        # Metin genişliğine göre satır sayısı hesapla
        fm = self.input_label.fontMetrics()
        text_width = fm.horizontalAdvance(text)
        available_width = 170 - 20  # padding
        
        # Satır sayısı (max 5)
        lines = max(1, min(5, (text_width // available_width) + 1))
        height_changed = (self.current_lines != lines)
        self.current_lines = lines
        
        # Yükseklik hesapla
        height = self.base_thickness * lines
        if lines > 1:
            height += 4  # Ekstra padding
        
        self.setFixedSize(170, height)
        self._root.setGeometry(0, 0, 170, height)
        self.show()

        if height_changed and self.recorder_window:
            self.recorder_window._update_input_overlay_position()

    def hide_input(self):
        """Zorla hemen gizle"""
        self.hide_timer.stop()
        self._do_hide()

    def _do_hide(self):
        self.input_label.setText("")
        self.current_lines = 0
        self.setFixedSize(170, self.base_thickness)
        self._root.setGeometry(0, 0, 170, self.base_thickness)
        self.hide()

    def update_position(self, overlay_pos, overlay_thickness):
        """FloatingOverlay'in üstüne konumlan (veya varsayılan pozisyona)"""
        self.move(overlay_pos.x(), overlay_pos.y() - self.height() - 4)

    # ── Mouse: Ctrl + Sol Tık + Sürükle (Bağımsız kontrol) ─────────────────────────
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
            # Sürüklerken altındaki (veya gizli olan) FloatingOverlay'i de hizala
            if self.recorder_window:
                self.recorder_window._update_floating_overlay_from_input(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and getattr(self, '_drag_active', False):
            self._drag_active = False
            # Sürükleme bitince pozisyonları merkeze kaydet
            if self.recorder_window:
                self.recorder_window._save_overlay_positions_from_input()
        super().mouseReleaseEvent(event)


# =============================================================================
# InputSignaler – Thread-safe Sinyal Köprüsü
# =============================================================================
class InputSignaler(QObject):
    """
    Arka plandaki InputListener thread'i ile ana GUI thread'i arasında
    güvenli ve çökmeyen Qt sinyal iletişimi kurar.
    """
    input_received = pyqtSignal(list)
    input_released = pyqtSignal(list)


# =============================================================================
# InputListener – Global klavye ve mouse dinleyici
# =============================================================================
class InputListener:
    """
    pynput kullanarak arka planda global klavye ve mouse hareketlerini yakalar.
    Elde edilen verileri thread-safe sinyaller aracılığıyla ana ekrana iletir.
    """
    def __init__(self, signaler: InputSignaler):
        self.signaler = signaler
        self.keyboard_listener = None
        self.mouse_listener = None
        self.running = False
        self._pressed_keys = set()
        self._pressed_buttons = set()
        self._lock = threading.Lock()
        
    def start(self):
        """Dinleyicileri başlat"""
        if not PYNPUT_AVAILABLE:
            print("Python: pynput mevcut değil, input dinleme başlatılamadı.")
            return False
            
        if self.running:
            return True
            
        try:
            # Klavye dinleyici
            self.keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            self.keyboard_listener.start()
            
            # Mouse dinleyici
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
        """Dinleyicileri durdur"""
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
        """Tuş basıldığında"""
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
        """Tuş bırakıldığında"""
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
        """Mouse tıklandığında"""
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
        """Basılı olan tüm tuş ve butonları döndür"""
        all_pressed = list(self._pressed_keys) + list(self._pressed_buttons)
        return all_pressed
            
    def _get_mouse_button_name(self, button):
        """Mouse buton ismini standardize et"""
        try:
            if button == mouse.Button.left:
                return "🖱L"  # Sol tık
            elif button == mouse.Button.right:
                return "🖱R"  # Sağ tık
            elif button == mouse.Button.middle:
                return "🖱M"  # Orta tık
            elif hasattr(button, 'name'):
                # Ekstra butonlar (ileri/geri)
                if 'x1' in str(button).lower() or 'back' in str(button).lower():
                    return "🖱B"  # Geri
                elif 'x2' in str(button).lower() or 'forward' in str(button).lower():
                    return "🖱F"  # İleri
                return f"🖱{button.name[0].upper()}"
            return None
        except Exception:
            return None
            
    def _get_key_name(self, key):
        """Tuş ismini standardize et"""
        try:
            # Özel tuşlar
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
                return "⌫"  # Backspace sembolü
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
                # Normal karakterler
                return key.char.upper()
            elif hasattr(key, 'name'):
                # Diğer tuşlar
                name = key.name
                if len(name) == 1:
                    return name.upper()
                # Uzun isimleri kısalt
                return name.title()[:6]
            return None
        except Exception:
            return None
            
    def get_pressed(self):
        """Şu an basılı olan her şeyi döndür"""
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
# ScreenRecorder  –  Sadece video (MKV) [Geliştirilmiş CFR Segmentleme]
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

        # --- DİNAMİK DISPLAY ---
        display = os.environ.get('DISPLAY', ':0.0')
        if display.startswith(':'):
            display = display.split('.')[0]  # :0.0 -> :0

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
            '-vsync', 'cfr',
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
# CombinedRecorder  –  Video + Ses (MKV) [Geliştirilmiş CFR Segmentleme ve Senkronizasyon]
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

        # --- DİNAMİK DISPLAY ---
        display = os.environ.get('DISPLAY', ':0.0')
        if display.startswith(':'):
            display = display.split('.')[0]  # :0.0 -> :0

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
            '-vsync', 'cfr',
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
    """Fare tekerleği ile kalınlık ayarlanabilen buton"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.thickness = 40
        self.setText("40")
        self.setFixedSize(40, 30)
        self.setToolTip("Kalınlık (30-50)\nSol Tık: Varsayılan konuma git\nSağ Tık: Mevcut konumu varsayılan yap\nFare Tekerleği: Değiştir")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        
    def wheelEvent(self, event):
        """Fare tekerleği ile kalınlığı ayarla"""
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
        self.keystroke_display_enabled = False
        self.noise_filter_enabled = self._load_noise_filter_setting()

        self.segment_duration       = 30
        self.timed_record_limit_sec = 0
        self.force_export_state     = False

        self.timed_record_timer = QTimer(self)
        self.timed_record_timer.setSingleShot(True)
        self.timed_record_timer.timeout.connect(self.auto_stop_recording)

        self.record_limit_map = {
            "1 dk": 60, "3 dk": 180, "5 dk": 300, "7 dk": 420, "10 dk": 600,
            "11 dk": 660, "13 dk": 780, "17 dk": 1020, "19 dk": 1140,
            "20 dk": 1200, "30 dk": 1800
        }
        self.segment_duration_map = {
            "20 sn": 20, "30 sn": 30, "45 sn": 45,
            "1 dk": 60, "1.5 dk": 90, "2 dk": 120, "3 dk": 180
        }

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

        # ── Overlay ayarları ─────────────────────────────────────────────────
        self.overlay_thickness = 40
        self.overlay_default_pos = None
        self.overlay_visible = True
        self.default_record_limit = "5 dk"
        self.default_segment_duration = "30 sn"
        self.load_overlay_settings()
        # ────────────────────────────────────────────────────────────────────

        self.camera_feature_window = None
        self.floating_overlay: FloatingOverlay | None = None
        self._last_files = []

        # ── Oynatma & Kapatma Durum Değişkenleri ──────────────────────────────
        self.force_close = False
        self.playback_mode        = None
        self.playback_filepath    = None
        self.is_playing           = False
        self.audio_player_process = None
        
        # ── Input Dinleme Sistemi (Sinyal Köprüsü ile Thread-safe Yapıldı) ───
        self.input_signaler = InputSignaler()
        self.input_signaler.input_received.connect(self._safe_on_input_press)
        self.input_signaler.input_released.connect(self._safe_on_input_release)
        
        self.input_overlay: InputOverlay | None = None
        self.input_listener: InputListener | None = None

        QDir().mkpath(DEFAULT_BASE_DIR)
        QDir().mkpath(SEGMENT_DIR)

        self.initUI()
        self._cleanup_segments()

        # Overlaylerin oluşturulması
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
        try:
            if os.path.exists(OVERLAY_SETTINGS_FILE):
                with open(OVERLAY_SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    self.overlay_thickness = settings.get('thickness', 40)
                    self.overlay_visible = settings.get('overlay_visible', True)
                    pos = settings.get('default_position', None)
                    if pos and len(pos) == 2:
                        self.overlay_default_pos = tuple(pos)
                    self.default_record_limit = settings.get('record_limit', "5 dk")
                    self.default_segment_duration = settings.get('segment_duration', "30 sn")
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
            if hasattr(self, 'record_limit_combo'):
                settings['record_limit'] = self.record_limit_combo.currentText()
            if hasattr(self, 'segment_duration_combo'):
                settings['segment_duration'] = self.segment_duration_combo.currentText()
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
        
        # Eğer aktif değilse ekranı temizli tutmasını sağla (arka planda sadece dinlemeye kapalı olur)
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
            # Sürüklenen InputOverlay'in her zaman bir alt kutusu olarak hizalanmasını sağla
            new_y = input_pos.y() + self.input_overlay.height() + 4
            self.floating_overlay.move(input_pos.x(), new_y)

    def _save_overlay_positions_from_input(self):
        if self.input_overlay:
            # InputOverlay yeni yerine bırakıldığında FloatingOverlay varsayılan yerini onun altına göre alır
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
        """Z Butonu ile Yüzen Zaman Göstergesinin Durumunu (Görünürlük) Yönetir"""
        self.overlay_visible = not getattr(self, 'overlay_visible', True)
        if self.overlay_visible:
            # '/' butonu ile aynı tasarım mantığı (aktif ise pressed stili)
            self.z_toggle_button.setStyleSheet(self.buttonStyleMiniPressed())
            if self.floating_overlay:
                self.floating_overlay.show()
                self._update_overlay(self.time_label.text())
            else:
                self._ensure_overlay()
        else:
            # '/' butonu ile aynı tasarım mantığı (deaktif ise normal stil)
            self.z_toggle_button.setStyleSheet(self.buttonStyleMini())
            if self.floating_overlay:
                self.floating_overlay.hide()
        self.save_overlay_settings()

    def toggle_keystroke_display(self):
        # Eğer pynput yüklü değilse kullanıcıya modülün eksik olduğunu söyleyelim
        if not PYNPUT_AVAILABLE:
            QMessageBox.warning(
                self, "Modül Eksik",
                "Klavye/Mouse gösterimi için 'pynput' kütüphanesi yüklü olmalıdır.\n\n"
                "Lütfen terminalinizde veya sanal ortamınızda (venv) şu komutu çalıştırıp uygulamayı yeniden başlatın:\n"
                "pip install pynput"
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

    # ─── Thread-safe Sinyal Alıcıları ─────────────────────────────────────────
    def _safe_on_input_press(self, inputs):
        if not self.keystroke_display_enabled or not self.input_overlay: return
        text = " + ".join(inputs)
        self.input_overlay.show_input(text)

    def _safe_on_input_release(self, inputs):
        if not self.keystroke_display_enabled or not self.input_overlay: return
        if not inputs: 
            self.input_overlay.show_input("") # 1.5 sn gecikmeli gizlenme timer'ını başlatır
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

        def add(widget, side=Qt.AlignLeft):
            self.toolbar_layout.addWidget(widget, alignment=side)

        self.file_button = QPushButton("File")
        self.file_button.setFixedSize(90, 30)
        self.file_button.setStyleSheet(self.buttonStyle())
        self.file_button.clicked.connect(self.openFileForPlayback)
        add(self.file_button)

        self.camera_button_feature = QPushButton("Camera")
        self.camera_button_feature.setFixedSize(80, 30)
        self.camera_button_feature.setStyleSheet(self.buttonStyle())
        self.camera_button_feature.setToolTip("Bu fonksiyon geliştirme aşamasındadır.")
        add(self.camera_button_feature)

        self.windows_button = QPushButton("Windows")
        self.windows_button.setFixedSize(90, 30)
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

        # ── Z Butonu Yüzen Zaman Göstergesini kontrol eder ────────────────
        self.z_toggle_button = QPushButton("Z")
        if getattr(self, 'overlay_visible', True):
            self.z_toggle_button.setStyleSheet(self.buttonStyleMiniPressed())
        else:
            self.z_toggle_button.setStyleSheet(self.buttonStyleMini())
        self.z_toggle_button.setFixedSize(30, 30)
        self.z_toggle_button.clicked.connect(self.toggle_overlay_visibility)
        add(self.z_toggle_button)
        # ───────────────────────────────────────────────────────────────────

        self.record_limit_combo = QComboBox()
        self.record_limit_combo.addItems(self.record_limit_map.keys())
        self.record_limit_combo.setCurrentText(self.default_record_limit)
        self.record_limit_combo.setFixedWidth(66)
        self.record_limit_combo.setStyleSheet(self.comboStyle())
        self.record_limit_combo.currentIndexChanged.connect(self.handle_record_limit_changed)
        self.record_limit_combo.setContextMenuPolicy(Qt.CustomContextMenu)
        self.record_limit_combo.customContextMenuRequested.connect(self._reset_record_limit_to_default)
        self.toolbar_layout.addWidget(self.record_limit_combo)
        self.handle_record_limit_changed(self.record_limit_combo.currentIndex())

        self.segment_duration_combo = QComboBox()
        self.segment_duration_combo.addItems(self.segment_duration_map.keys())
        self.segment_duration_combo.setCurrentText(self.default_segment_duration)
        self.segment_duration_combo.setFixedWidth(80)
        self.segment_duration_combo.setStyleSheet(self.comboStyle())
        self.segment_duration_combo.currentIndexChanged.connect(self.handle_segment_duration_changed)
        self.segment_duration_combo.setContextMenuPolicy(Qt.CustomContextMenu)
        self.segment_duration_combo.customContextMenuRequested.connect(self._reset_segment_duration_to_default)
        self.toolbar_layout.addWidget(self.segment_duration_combo)
        self.handle_segment_duration_changed(self.segment_duration_combo.currentIndex())

        self.main_play_pause_button = QPushButton("Play")
        self.main_play_pause_button.setFixedSize(75, 30)
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

        # Süre Gösterimi
        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet("color: white; font-size: 14px; margin-right: 10px;")
        add(self.time_label, Qt.AlignRight)

        # ── Segment Menü Butonu (Yeni Arayüz) ─────────────────────────────
        self.segment_menu_button = QPushButton("Segment 0")
        self.segment_menu_button.setFixedSize(120, 30) # Segment 10+ için biraz genişlik bırakıldı
        self.segment_menu_button.setStyleSheet(self.segmentButtonStyle())
        add(self.segment_menu_button, Qt.AlignRight)
        # ───────────────────────────────────────────────────────────────────

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
        self.info_label = QLabel("No Video Preview")
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
        self.layout.addWidget(self.splitter)
        self.splitter.setSizes([self.height() - self.toolbar_frame.height(), 0])

    # ─── Stiller ──────────────────────────────────────────────────────────────

    def segmentButtonStyle(self): return self.buttonStyle() + """
        QPushButton::menu-indicator { image: none; width: 0px; }
    """

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

    def handle_record_limit_changed(self, idx):
        txt = self.record_limit_combo.itemText(idx)
        self.timed_record_limit_sec = self.record_limit_map.get(txt, 0)
        self.save_overlay_settings()

    def handle_segment_duration_changed(self, idx):
        txt = self.segment_duration_combo.itemText(idx)
        self.segment_duration = self.segment_duration_map.get(txt, 30)
        self.save_overlay_settings()

    def _reset_record_limit_to_default(self):
        self.record_limit_combo.setCurrentText("5 dk")
        self.save_overlay_settings()

    def _reset_segment_duration_to_default(self):
        self.segment_duration_combo.setCurrentText("30 sn")
        self.save_overlay_settings()

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
        if self.recording:
            QMessageBox.information(self, "Mod Değiştirilemez", "Kayıt devam ederken modlar değiştirilemez.")
            return
        if name == "windows": self.windows_active = not self.windows_active
        elif name == "sound":  self.sound_active   = not self.sound_active
        self.windows_button.setStyleSheet(self.toggleButtonStyle(self.windows_active))
        self.sound_button.setStyleSheet(self.toggleButtonStyle(self.sound_active))
        self.updateMainPlayPauseButtonState()
        self.save_overlay_settings()

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

    def _start_recorder(self):
        start_num = self._get_next_segment_number(SEGMENT_DIR)
        args = {'output_dir': SEGMENT_DIR, 'start_number': start_num, 'segment_time': self.segment_duration}
        rc = None; info = ""

        if self.windows_active and self.sound_active:
            rc = CombinedRecorder
            args.update({'fps': self.selected_fps,
                         'resolution': self.selected_resolution,
                         'audio_rate': self.selected_audio_rate})
            info = "Birleşik Ekran (MKV) ve Ses Kaydı Aktif"
        elif self.windows_active:
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
            self.recorder_thread.error_occurred.connect(self._handle_recorder_error)
            self.recorder_thread.start()
            self.info_label.setText(info)
            if self.overlay_visible:
                self._ensure_overlay()
        else:
            self.info_label.setText("Kayıt modu seçilmedi.")

        self.info_label.show()
        self.video_widget.hide()

    def _handle_recorder_error(self, msg):
        QMessageBox.critical(self, "Kaydedici Hatası", msg)
        self._stop_full_recording_session(cleanup=False)

    def _pause_recording_session(self):
        self.timed_record_timer.stop()
        stop_time = time.time()
        if self.recorder_thread and self.recorder_thread.isRunning():
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

    def _stop_full_recording_session(self, cleanup=True):
        self.timed_record_timer.stop()
        if self.recorder_thread and self.recorder_thread.isRunning():
            self.recorder_thread.stop_process()
            self.recorder_thread.wait()
            self.recorder_thread = None
        self.time_timer.stop()
        self.recording = False
        self.updateMainPlayPauseButtonState()
        self.info_label.setText("Video Önizlemesi Yok")
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

        if not self.recording:
            self.record_start_time_segment = time.time()
            self._start_recorder()
            self.time_timer.start()
            self.recording = True
            if self.timed_record_limit_sec > 0:
                self.timed_record_timer.start(self.timed_record_limit_sec * 1000)
        else:
            self._pause_recording_session()

        self.updateMainPlayPauseButtonState()

    def auto_stop_recording(self):
        if self.recording:
            self._pause_recording_session()
            QMessageBox.information(self, "Süre Doldu", f"{self.record_limit_combo.currentText()} süresi doldu. Kayıt durduruldu.")

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

    # ─── Yeni Segment UI & Silme İşlemleri ────────────────────────────────────

    def sort_segment_files(self, filename):
        match = re.search(r'^s(\d+)\.', os.path.basename(filename))
        return int(match.group(1)) if match else 0

    def updateSegmentUI(self):
        current_files = self._get_segment_files(full_path=False)
        # Sadece değişim olduğunda arayüzü güncelle
        if hasattr(self, '_last_files') and self._last_files == current_files:
            return
        self._last_files = current_files

        count = len(current_files)
        self.segment_menu_button.setText(f"Segment {count}")

        # Dinamik Menü Oluşturma
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #282828; color: white; border: 1px solid #555; }
            QMenu::item { padding: 5px 30px 5px 20px; }
            QMenu::item:selected { background-color: #444; }
            QMenu::separator { height: 1px; background: #555; margin: 2px 0px; }
        """)

        if current_files:
            sorted_files = sorted(current_files, key=self.sort_segment_files)
            for fn in sorted_files:
                match = re.search(r'^s(\d+)\.', fn)
                num_str = match.group(1) if match else "?"
                action = menu.addAction(f"s{num_str}")
                action.triggered.connect(lambda checked, f=fn: self.prompt_delete_segment(f))
            
            menu.addSeparator()

        action_all = menu.addAction("Hepsi")
        action_all.triggered.connect(self.delete_all_segments_prompt)
        if not current_files:
            action_all.setEnabled(False)

        # Eski menü varsa temizleyip yenisini ekliyoruz
        old_menu = self.segment_menu_button.menu()
        self.segment_menu_button.setMenu(menu)
        if old_menu:
            old_menu.deleteLater()

        # Dışa aktarma butonunu pasif/aktif et
        self.export_button.setEnabled(count > 0)

    def prompt_delete_segment(self, filename):
        filepath = os.path.join(SEGMENT_DIR, filename)
        reply = QMessageBox.question(
            self, "Segmenti Sil",
            f"Kayıtlı '{filename}' dosyasını kalıcı olarak silmek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
                self.updateSegmentUI()
            except Exception as e:
                QMessageBox.warning(self, "Silme Hatası", f"Dosya silinemedi:\n{e}")

    def delete_all_segments_prompt(self):
        reply = QMessageBox.question(
            self, "Tüm Segmentleri Sil",
            "Kayıtlı bütün segmentleri KALICI OLARAK silmek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._cleanup_segments()

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

        # Nümerik olarak sıraya diz (eksik rakamlar olsa bile sırayla alır)
        all_segs = sorted(self._get_segment_files(full_path=True), key=self.sort_segment_files)
        if not all_segs:
            QMessageBox.information(self, "Dışa Aktarılamadı", "Dışa aktarılacak kayıt yok.")
            return

        has_video = any(f.endswith('.mkv') for f in all_segs)
        ext = ".mkv" if has_video else ".wav"
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Kaydı Dışa Aktar", DEFAULT_BASE_DIR,
            "MKV Video Dosyası (*.mkv);;WAV Ses Dosyası (*.wav);;Tüm Dosyalar (*)")
        if not out_path: return
        if not out_path.lower().endswith(ext): out_path += ext

        progress = QProgressDialog("Dışa aktarılıyor...", "İptal", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("İşleniyor")
        progress.show()

        lf = tm = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as f: tm = f.name + ext
            progress.setLabelText("Segmentler birleştiriliyor..."); progress.setValue(10)
            QApplication.processEvents()

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as lfile:
                lf = lfile.name
                for seg in all_segs:
                    lfile.write(f"file '{os.path.abspath(seg)}'\n")

            r = subprocess.run(
                [FFMPEG_PATH, '-y','-f','concat','-safe','0','-i',lf,'-c','copy',tm],
                capture_output=True, text=True, encoding='utf-8')
            if r.returncode != 0:
                raise RuntimeError(f"Birleştirme hatası:\n{r.stderr}")

            progress.setLabelText("Filtre uygulanıyor..."); progress.setValue(50)
            QApplication.processEvents()

            def on_filtered(final_path):
                try:
                    shutil.copy(final_path, out_path)
                    progress.setValue(100)
                    QMessageBox.information(self, "Başarılı", f"Dosya dışa aktarıldı:\n{out_path}")
                    self.cumulative_time = 0
                    self.updateTimeLabel()
                    self.info_label.setText("Video Önizlemesi Yok")
                    self._cleanup_segments()
                    self.updateMainPlayPauseButtonState()
                except Exception as e:
                    QMessageBox.critical(self, "Dışa Aktarma Hatası", str(e))
                finally:
                    progress.close()
                    for f in [lf, tm, final_path]:
                        if f and f != out_path and os.path.exists(f):
                            try: os.remove(f)
                            except: pass

            is_video_file = False
            try:
                probe = subprocess.run(
                    [FFPROBE_PATH, '-v', 'error', '-select_streams', 'v:0',
                     '-show_entries', 'stream=codec_type', '-of', 'default=noprint_wrappers=1:nokey=1', tm],
                    capture_output=True, text=True, timeout=5)
                if probe.stdout.strip() == 'video':
                    is_video_file = True
            except: pass

            self._filter_media_file(tm, is_video_file, on_filtered)

        except Exception as e:
            QMessageBox.critical(self, "Dışa Aktarma Hatası", str(e))
            progress.close()
            for f in [lf, tm]:
                if f and os.path.exists(f):
                    try: os.remove(f)
                    except: pass

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
        fp, _ = QFileDialog.getOpenFileName(
            self, "Dosya Seç", DEFAULT_BASE_DIR,
            "Video (*.rec *.mp4 *.mkv);;Ses (*.wav);;Tümü (*)")
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

    def disableRecordingButtons(self, disable):
        for w in [self.windows_button, self.sound_button, self.file_button]:
            w.setEnabled(not disable)
        self.record_limit_combo.setEnabled(not disable)
        self.segment_duration_combo.setEnabled(not disable)
        self.export_button.setEnabled(self._has_segments())
        self.windows_button.setStyleSheet(
            self.toggleButtonStyle(self.windows_active) if not disable else self.disabledButtonStyle())
        self.sound_button.setStyleSheet(
            self.toggleButtonStyle(self.sound_active) if not disable else self.disabledButtonStyle())
        self.file_button.setStyleSheet(
            self.buttonStyle() if not disable else self.disabledButtonStyle())
        self.export_button.setStyleSheet(
            self.buttonStyle() if self.export_button.isEnabled() else self.disabledButtonStyle())

    def updateMainPlayPauseButtonState(self):
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
                if self.playback_bar_frame.isHidden(): self.playback_bar_frame.show()
                total = self.height() - self.toolbar_frame.height()
                pbh   = self.playback_bar_frame.height()
                if total - pbh < 100: pbh = max(0, total - 100)
                self.splitter.setSizes([total - pbh, pbh])
            else:
                self.showFullScreen(); self.toolbar_frame.hide()
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
            if self.recording: self._pause_recording_session()
            self._cleanup_segments()
            
            self.sound_active = False
            self.windows_active = False
            self.sound_button.setStyleSheet(self.toggleButtonStyle(False))
            self.windows_button.setStyleSheet(self.toggleButtonStyle(False))
            
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

            self.record_limit_combo.setCurrentText("5 dk")
            self.segment_duration_combo.setCurrentText("30 sn")
            
            self.save_overlay_settings()  
            self._update_input_overlay_position()
            
            self.recorder_thread = None; self.recording = False
            self.cumulative_time = 0
            self.updateTimeLabel()
            self.updateSegmentUI()
            self.updateMainPlayPauseButtonState()
            
            QMessageBox.information(self,"Başarılı",
                "Geçici klasör temizlendi.\n• Kayıtlar durduruldu\n• Modlar ve tüm ayarlar varsayılana sıfırlandı.")

    def closeEvent(self, event):
        self._close_overlay()
        
        # Kamera penceresi açıksa otomatik kapatıyoruz
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
                if self.recording:
                    self._pause_recording_session()
                self._cleanup_segments()
                self.recording = False
                self.cumulative_time = 0
                self.updateTimeLabel()
                self.updateSegmentUI()
                self.updateMainPlayPauseButtonState()
                event.accept()
                QApplication.closeAllWindows() # Tüm bağlıları sonlandır
            else:
                event.ignore()
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
    
    # ── İkon yolu – paket içi ve geliştirme ortamında çalışır ──
    icon_path = resource_path("Kavram/ikon/Kavram.png")
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
