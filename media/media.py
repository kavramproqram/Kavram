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
# along with this program. If not, see /Kavram/License/GPLv3.txt
#
# ---------------------------------------------
# GÜNCELLEME NOTU (2.2.3):
#  - Export butonu: Sol tık → .media (gz/xz seçimli), Sağ tık → format menüsü.
#  - Video widget: KeepAspectRatio modu eklendi.
#  - Timeline: segment sayısına göre dinamik min yükseklik.
#
# GÜNCELLEME NOTU (2.2.5):
#  - Lua uyumluluk katmanı TAMAMEN KALDIRILDI.
#  - _python_calculate_segment_position ve _python_update_timeline_smoothly
#    kaldırıldı. Zaman çizelgesi matematiği artık yalnızca C++ tarafında.
#
# GÜNCELLEME NOTU (2.2.6):
#  - _export_timeline_with_format: video export'ta boş audio_list.txt
#    gönderilmiyor (C++ tarafı artık boş manifest'i de yok sayıyor ama
#    Python da temiz gönderiyor). Bu, exit 183 / -22 hatasını ortadan kaldırdı.
#  - TimelineBar.paintEvent ACTIVE bölümü artık segment genişliğini
#    süre * pixels_per_second ile hesaplıyor (eski kod
#    calculate_segment_position(ms, w, 1000.0) kullandığı için 1 sn'den
#    uzun her segment aynı genişlikte görünüyordu).

# --- kavram yol ayarı (otomatik; klasör yapısı: kavram/<program>/<program>.py) ---
# _PROGRAM_DIR / _KAVRAM_DIR : salt-okunur kısım (kod, motorlar, ikon) — paketli sürümde paketin içi
# _KAVRAM_VERI               : YAZILABİLİR kök. Kaynak sürümde = _KAVRAM_DIR,
#                              paketli sürümde = ~/.local/share/kavram (çekirdek ayarlar)
import os as _os
_PROGRAM_DIR = _os.path.dirname(_os.path.abspath(__file__))
_KAVRAM_DIR = _os.environ.get("KAVRAM_DIR") or _os.path.dirname(_PROGRAM_DIR)
_KAVRAM_VERI = _os.environ.get("KAVRAM_VERI") or _KAVRAM_DIR
_KAVRAM_EXPORT_DIR = _os.path.join(_KAVRAM_VERI, "export")
_PROGRAM_VERI = _os.path.join(_KAVRAM_VERI, _os.path.basename(_PROGRAM_DIR))
# -------------------------------------------------------------------------------
import os
import shutil
import tempfile
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
                             QFileDialog, QFrame, QSizePolicy, QMessageBox, QSplitter, QDialog,
                             QMenu, QAction, QProgressBar, QComboBox, QShortcut, QGridLayout,
                             QProgressDialog, QActionGroup)
from PyQt5.QtGui import (QPainter, QColor, QPen, QFont, QImage, QPixmap, QIcon, QKeySequence)
from PyQt5.QtCore import (Qt, QTimer, pyqtSignal, QPoint, QDir, QSize, QByteArray, QBuffer,
                          QIODevice, QUrl, QProcess, QEventLoop, QRect, QObject)
from PyQt5.QtSvg import QSvgRenderer
import sys
import re
import subprocess
import ctypes
import numpy as np
import time
import queue
import threading
import struct
import mmap
import copy
import json
import traceback
import math

from PyQt5.QtMultimedia import (QMediaPlayer, QMediaContent, QAbstractVideoSurface, QVideoFrame,
                                QVideoSurfaceFormat, QAbstractVideoBuffer)

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
    import noisereduce as nr
    import scipy.signal as sig
    import librosa
    from pydub import AudioSegment
    from pydub.effects import compress_dynamic_range
    AUDIO_LIBS_MISSING = False
except ImportError:
    AUDIO_LIBS_MISSING = True


def resource_path(relative_path):
    """PyInstaller ve normal kaynak çalışma ortamı için güvenli kaynak yolu."""
    if not relative_path:
        return os.path.dirname(os.path.abspath(__file__))
    base_path = getattr(sys, "_MEIPASS", None)
    if not base_path:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def _arac_bul(ad):
    """ffmpeg / ffprobe / ffplay: önce paketle gelen bin/<ad> (varsa ve çalışıyorsa), yoksa sistem PATH'i."""
    import shutil as _shutil
    import subprocess as _sp
    yerel = _os.path.join(_KAVRAM_DIR, "bin", ad)
    if _os.path.isfile(yerel) and _os.access(yerel, _os.X_OK):
        try:
            if _sp.run([yerel, "-version"], stdout=_sp.DEVNULL, stderr=_sp.DEVNULL, timeout=8).returncode == 0:
                return yerel
        except Exception:
            pass
    return _shutil.which(ad) or ad


FFMPEG_PATH  = _arac_bul("ffmpeg")
FFPROBE_PATH = _arac_bul("ffprobe")
FFPLAY_PATH  = _arac_bul("ffplay")

if not os.path.isabs(FFMPEG_PATH):
    print("Uyarı: ffmpeg sistemde bulunamadı. Kurulum dosyasını (kurulum_deb.txt / kurulum_arch.txt) çalıştırın.")


def show_missing_libs_error(parent):
    QMessageBox.critical(parent, "Missing Libraries",
                         "Required audio libraries are not installed.\n"
                         "Please install: pip install soundfile numpy noisereduce scipy librosa pydub")


def create_svg_icon(svg_content, size=24, color="#eee"):
    modified_svg_content = svg_content.replace('stroke="#eee"', f'stroke="{color}"').replace('fill="#eee"', f'fill="{color}"')
    renderer = QSvgRenderer(QByteArray(modified_svg_content.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


SVG_UNDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19C15.866 19 19 15.866 19 12C19 8.13401 15.866 5 12 5C8.13401 5 5 8.13401 5 12C5 13.7909 5.70014 15.4293 6.84594 16.6386L5 18M5 18H9M5 18V14" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_REDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5C8.13401 5 5 8.13401 5 12C5 15.866 8.13401 19 12 19C15.866 19 19 15.866 19 12C19 10.2091 18.2999 8.57074 17.1541 7.3614L19 6M19 6H15M19 6V10" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_SAVE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V7L17 3ZM12 17C10.34 17 9 15.66 9 14C9 12.34 10.34 11 12 11C13.66 11 15 12.34 15 14C15 15.66 13.66 17 12 17Z" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

DEFAULT_BASE_DIR = _KAVRAM_EXPORT_DIR
SAVE_DIR = os.path.join(_PROGRAM_VERI, 'medya_cut')

LIB_PATH = os.path.join(_PROGRAM_DIR, "media_engine.so")

SETTINGS_FILE = os.path.join(_KAVRAM_VERI, "filter", "filter_settings.json")
OVERLAY_SETTINGS_FILE = os.path.join(_KAVRAM_VERI, "rec", "rec_overlay.json")



# =============================================================================
# YENİ BİLEŞENLER (3.0): video yüzeyi, FFmpeg görevi, kayıt oturumu
# =============================================================================
CAMERA_SETTINGS_FILE = os.path.join(_PROGRAM_VERI, "media_camera.json")
RECORDER_PATH = os.path.join(_PROGRAM_DIR, "media_recorder")

# Kamera görüntü oranları: ad -> (çıkış genişliği, çıkış yüksekliği); (0, 0) = kameranın kendi boyutu
CAMERA_ASPECTS = {
    "16:9": (1280, 720),
    "9:16": (540, 960),
    "1:1": (720, 720),
    "4:3": (960, 720),
    "3:4": (540, 720),
    "Kamera (orijinal)": (0, 0),
}

# Export tuval oranları
EXPORT_CANVAS_PRESETS = {"16:9": (16, 9), "9:16": (9, 16), "1:1": (1, 1), "4:3": (4, 3), "3:4": (3, 4)}


class VideoCanvas(QWidget):
    """Video karelerini kendimiz çizeriz (QVideoWidget'ın yerel pencere/overlay'i yerine).

    Neden: QVideoWidget, X11 ve özellikle Wayland/XWayland'de segment değişince (dikey -> yatay)
    eski boyutu/konumu tutup görüntüyü kaydırabiliyor. Burada her kare, widget'ın o anki boyutuna ve
    karenin KENDİ en-boy oranına göre ortalanarak çizilir; kaydırma/sıçrama olmaz."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image = None
        self._par = 1.0
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(2, 2)

    def sizeHint(self):
        return QSize(640, 360)

    def set_frame(self, image, par=1.0):
        self._image = image
        self._par = par if (par and par > 0) else 1.0
        self.update()

    def clear_frame(self):
        self._image = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0))
        img = self._image
        if img is None or img.isNull() or self.width() < 2 or self.height() < 2:
            return
        iw = img.width() * self._par
        ih = float(img.height())
        scale = min(self.width() / iw, self.height() / ih)
        tw = max(1, int(round(iw * scale)))
        th = max(1, int(round(ih * scale)))
        x = (self.width() - tw) // 2
        y = (self.height() - th) // 2
        painter.setRenderHint(QPainter.SmoothPixmapTransform, tw * th <= 2400000)
        painter.drawImage(QRect(x, y, tw, th), img)


class VideoSurface(QAbstractVideoSurface):
    """QMediaPlayer'ın video çıkışı: kareyi QImage'a çevirip VideoCanvas'a verir."""

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self._canvas = canvas
        self._fmt = None
        self._par = 1.0
        self._detached = False

    def detach(self):
        """Oynatıcı bırakıldı: bu yüzey artık tuvale dokunmaz."""
        self._detached = True

    def supportedPixelFormats(self, handleType=QAbstractVideoBuffer.NoHandle):
        if handleType != QAbstractVideoBuffer.NoHandle:
            return []
        candidates = [QVideoFrame.Format_RGB32, QVideoFrame.Format_ARGB32,
                      QVideoFrame.Format_ARGB32_Premultiplied, QVideoFrame.Format_RGB24,
                      QVideoFrame.Format_RGB565, QVideoFrame.Format_RGB555]
        return [f for f in candidates if QVideoFrame.imageFormatFromPixelFormat(f) != QImage.Format_Invalid]

    def start(self, fmt):
        if QVideoFrame.imageFormatFromPixelFormat(fmt.pixelFormat()) == QImage.Format_Invalid or fmt.frameSize().isEmpty():
            return False
        self._fmt = fmt
        par = fmt.pixelAspectRatio()
        self._par = (par.width() / par.height()) if (par.isValid() and par.height() > 0 and par.width() > 0) else 1.0
        return super().start(fmt)

    def stop(self):
        self._fmt = None
        if not self._detached:
            try:
                self._canvas.clear_frame()
            except RuntimeError:
                self._detached = True        # pencere zaten yok edilmiş (kapanış)
        super().stop()

    def present(self, frame):
        if self._detached:
            return True
        if not frame.isValid() or self._fmt is None:
            return False
        f = QVideoFrame(frame)
        if not f.map(QAbstractVideoBuffer.ReadOnly):
            return False
        try:
            img_fmt = QVideoFrame.imageFormatFromPixelFormat(f.pixelFormat())
            if img_fmt == QImage.Format_Invalid:
                self.setError(QAbstractVideoSurface.IncorrectFormatError)
                return False
            img = QImage(f.bits(), f.width(), f.height(), f.bytesPerLine(), img_fmt).copy()
        finally:
            f.unmap()
        flip_v = self._fmt.scanLineDirection() == QVideoSurfaceFormat.BottomToTop
        flip_h = bool(getattr(self._fmt, "isMirrored", lambda: False)())
        if flip_v or flip_h:
            img = img.mirrored(flip_h, flip_v)
        try:
            self._canvas.set_frame(img, self._par)
        except RuntimeError:
            self._detached = True
            return True
        return True


class ShmReader:
    """media_recorder'ın /dev/shm'ye yazdığı önizleme karelerini (seqlock) okur (rec ile aynı biçim)."""
    VHDR = struct.Struct('<6IQQ2I')       # 48 bayt (başlık 64 bayt, veri 64'ten başlar)
    VMAGIC = 0x5650564B

    def __init__(self, path):
        self.path = path
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

    def close(self):
        self.reset()

    def _open(self):
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        except OSError:
            return False
        try:
            st = os.fstat(fd)
            self._ino = st.st_ino
            if st.st_size < 64:
                return False
            self.mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        except Exception:
            self.mm = None
            return False
        finally:
            os.close(fd)
        if struct.unpack_from('<I', self.mm, 0)[0] != self.VMAGIC:
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
                    try:
                        if os.stat(self.path).st_ino != self._ino:
                            self.reset()
                    except OSError:
                        self.reset()
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


class FFmpegTask(QObject):
    """FFmpeg'i QProcess ile çalıştırır (arayüzü dondurmaz). İlerleme, '-progress pipe:1' çıktısından okunur."""
    progress = pyqtSignal(float)            # işlenen süre (saniye)
    done = pyqtSignal(bool, str)            # başarı, hata günlüğü (son kısım)

    def __init__(self, ffmpeg, args, parent=None):
        super().__init__(parent)
        self._ffmpeg = ffmpeg
        self._args = list(args)
        self._proc = QProcess(self)
        self._buf = b""
        self._err = b""
        self._cancelled = False
        self._finished = False
        self._proc.readyReadStandardOutput.connect(self._on_out)
        self._proc.readyReadStandardError.connect(self._on_err)
        self._proc.finished.connect(self._on_finished)
        self._proc.errorOccurred.connect(self._on_error)

    def start(self):
        self._proc.start(self._ffmpeg, self._args)

    def cancel(self):
        self._cancelled = True
        if self._proc.state() != QProcess.NotRunning:
            self._proc.terminate()
            QTimer.singleShot(2500, self._kill_if_running)

    def _kill_if_running(self):
        if self._proc.state() != QProcess.NotRunning:
            self._proc.kill()

    def is_running(self):
        return self._proc.state() != QProcess.NotRunning

    def _on_out(self):
        self._buf += bytes(self._proc.readAllStandardOutput())
        while b"\n" in self._buf:
            line, self._buf = self._buf.split(b"\n", 1)
            line = line.decode("utf-8", "replace").strip()
            if line.startswith("out_time_us=") or line.startswith("out_time_ms="):
                try:
                    v = float(line.split("=", 1)[1])
                    if v >= 0:
                        self.progress.emit(v / 1000000.0)
                except ValueError:
                    pass

    def _on_err(self):
        self._err += bytes(self._proc.readAllStandardError())
        if len(self._err) > 65536:
            self._err = self._err[-32768:]

    def _on_error(self, err):
        if err == QProcess.FailedToStart and not self._finished:
            self._finished = True
            self.done.emit(False, "FFmpeg başlatılamadı (kurulu mu?).")

    def _on_finished(self, code, status):
        if self._finished:
            return
        self._finished = True
        self._on_err()
        ok = (code == 0 and status == QProcess.NormalExit and not self._cancelled)
        tail = self._err.decode("utf-8", "replace")[-1500:]
        if self._cancelled:
            tail = "İptal edildi."
        self.done.emit(ok, tail)


class RecorderSession(QObject):
    """media_recorder sürecini yönetir (kamera+mikrofon ya da yalnızca mikrofon)."""
    started = pyqtSignal()
    finished = pyqtSignal(int, str, str)    # çıkış kodu, çıkış dosyası, günlük

    def __init__(self, binary, args, out_path, parent=None):
        super().__init__(parent)
        self.out_path = out_path
        self._binary = binary
        self._args = list(args)
        self._proc = QProcess(self)
        self._out_buf = b""
        self._log = b""
        self._stop_requested = False
        self._done = False
        self._proc.readyReadStandardOutput.connect(self._on_out)
        self._proc.readyReadStandardError.connect(self._on_err)
        self._proc.finished.connect(self._on_finished)
        self._proc.errorOccurred.connect(self._on_error)

    def start(self):
        self._proc.start(self._binary, self._args)
        return self._proc.waitForStarted(4000)

    def is_running(self):
        return self._proc.state() != QProcess.NotRunning

    def request_stop(self):
        """Temiz kapanış: STOP gönder -> motor EOS ile dosyayı sonlandırır."""
        if self._stop_requested or not self.is_running():
            return
        self._stop_requested = True
        self._proc.write(b"STOP\n")
        QTimer.singleShot(20000, self._terminate_if_running)

    def _terminate_if_running(self):
        if self.is_running():
            self._proc.terminate()
            QTimer.singleShot(5000, self._kill_if_running)

    def _kill_if_running(self):
        if self.is_running():
            self._proc.kill()

    def kill(self):
        if self.is_running():
            self._proc.kill()
            self._proc.waitForFinished(2000)

    def _on_out(self):
        self._out_buf += bytes(self._proc.readAllStandardOutput())
        while b"\n" in self._out_buf:
            line, self._out_buf = self._out_buf.split(b"\n", 1)
            text = line.decode("utf-8", "replace").strip()
            self._log += (text + "\n").encode("utf-8", "replace")
            if text.startswith("EVENT started"):
                self.started.emit()

    def _on_err(self):
        self._log += bytes(self._proc.readAllStandardError())
        if len(self._log) > 65536:
            self._log = self._log[-32768:]

    def _on_error(self, err):
        if err == QProcess.FailedToStart and not self._done:
            self._done = True
            self.finished.emit(-1, self.out_path, "media_recorder başlatılamadı.")

    def _on_finished(self, code, status):
        if self._done:
            return
        self._done = True
        self._on_out()
        self._on_err()
        if status != QProcess.NormalExit:
            code = -1
        self.finished.emit(code, self.out_path, self._log.decode("utf-8", "replace")[-2000:])



class AdvancedFilterDialog(QDialog):
    def __init__(self, initial_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filter Settings")
        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.settings = initial_settings.copy()

        self.setStyleSheet("""
            QDialog { background-color: rgba(40, 40, 40, 245); border: 1px solid #777; border-radius: 8px; }
            QLabel { color: #e0e0e0; background: transparent; font-size: 13px; font-weight: bold; padding-right: 5px; }
            QComboBox { background-color: #333; color: white; font-size: 13px; border: 1px solid #555; border-radius: 4px; padding: 4px; }
            QComboBox:hover { background-color: #444; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView { background-color: #282828; border: 1px solid #555; selection-background-color: #555; color: white; }
            QPushButton { background-color: #444; color: white; border: 1px solid #666; border-radius: 4px; padding: 5px 15px; margin-top: 5px; }
            QPushButton:hover { background-color: #555; }
        """)

        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

        self.combo_ai_nr = self.create_filter_combo(0, "AI Noise Reduction", ["Off", "On"])
        self.combo_noise_gate = self.create_filter_combo(1, "Noise Gate", ["Off"] + [f"{i}dB" for i in range(-80, -19, 5)])
        self.combo_hp = self.create_filter_combo(2, "HP Filter", ["Off"] + [f"{i}Hz" for i in range(20, 301, 10)])
        self.combo_lp = self.create_filter_combo(3, "LP Filter", ["Off"] + [f"{i}Hz" for i in range(2000, 20001, 1000)])
        self.combo_gain = self.create_filter_combo(4, "Gain", [f"{i}dB" for i in range(-12, 13, 1)])
        self.combo_reverb = self.create_filter_combo(5, "Reverb Reduction", ["Off", "Low", "Medium", "High", "Very High"])

        self.combo_de_esser = self.create_filter_combo(0, "De-Esser", ["Off", "Low", "Medium", "High"], col_start=2)
        self.combo_de_hum = self.create_filter_combo(1, "De-Hum", ["Off", "Low", "Medium", "High"], col_start=2)
        self.combo_comp_thresh = self.create_filter_combo(2, "Comp. Threshold", ["Off"] + [f"{i}dB" for i in range(-60, 1, 5)], col_start=2)
        self.combo_comp_ratio = self.create_filter_combo(3, "Comp. Ratio", ["1:1", "2:1", "3:1", "4:1", "5:1", "8:1", "10:1"], col_start=2)
        self.combo_comp_attack = self.create_filter_combo(4, "Comp. Attack", [f"{i}ms" for i in [1, 5, 10, 20, 50, 100]], col_start=2)
        self.combo_comp_release = self.create_filter_combo(5, "Comp. Release", [f"{i}ms" for i in [50, 100, 200, 500, 1000]], col_start=2)

        self.combo_eq_gain = self.create_filter_combo(0, "EQ Gain", [f"{i}dB" for i in range(-12, 13, 1)], col_start=4)
        self.combo_eq_freq = self.create_filter_combo(1, "EQ Freq.", [f"{i}Hz" for i in [500, 1000, 1500, 2000, 3000, 4000]], col_start=4)
        self.combo_eq_q = self.create_filter_combo(2, "EQ Q", ["0.5", "1.0", "2.0", "3.0", "5.0", "8.0"], col_start=4)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.layout.addWidget(self.ok_button, 6, 0, 1, 6, Qt.AlignCenter)

        self.load_initial_settings()
        self.setFixedSize(self.sizeHint())

    def create_filter_combo(self, row, label_text, items, col_start=0):
        label = QLabel(label_text)
        combo = QComboBox()
        combo.addItems(items)
        self.layout.addWidget(label, row, col_start, Qt.AlignRight)
        self.layout.addWidget(combo, row, col_start + 1)
        return combo

    def load_initial_settings(self):
        self.combo_ai_nr.setCurrentText("On" if self.settings.get('ai_nr_enabled') else "Off")
        self.combo_noise_gate.setCurrentText(f"{int(self.settings.get('noise_gate_threshold_db', -70))}dB" if self.settings.get('noise_gate_threshold_db', -70) > -990 else "Off")
        self.combo_hp.setCurrentText(f"{self.settings.get('hp_cutoff_hz', 150)}Hz" if self.settings.get('hp_cutoff_hz', 150) > 0 else "Off")
        self.combo_lp.setCurrentText(f"{self.settings.get('lp_cutoff_hz', 10000)}Hz" if self.settings.get('lp_cutoff_hz', 10000) > 0 else "Off")
        self.combo_gain.setCurrentText(f"{int(self.settings.get('gain_db', 6))}dB")

        level_map_rev = {0: "Off", 1: "Low", 2: "Medium", 3: "High", 4: "Very High"}
        self.combo_reverb.setCurrentText(level_map_rev.get(self.settings.get('reverb_reduction_level', 0), "Off"))
        de_esser_map = {0: "Off", 1: "Low", 2: "Medium", 3: "High"}
        self.combo_de_esser.setCurrentText(de_esser_map.get(self.settings.get('de_esser_level', 0), "Off"))
        self.combo_de_hum.setCurrentText(de_esser_map.get(self.settings.get('de_hum_level', 0), "Off"))

        comp_thresh = self.settings.get('compressor_threshold_db', -999)
        self.combo_comp_thresh.setCurrentText(f"{int(comp_thresh)}dB" if comp_thresh > -990 else "Off")
        ratio_value = float(self.settings.get('compressor_ratio', 1.0))
        if ratio_value in (1.0, 2.0, 3.0, 4.0, 5.0, 8.0, 10.0):
            self.combo_comp_ratio.setCurrentText(f"{int(ratio_value)}:1")
        else:
            self.combo_comp_ratio.setCurrentText("1:1")
        attack_map = {1: "1ms", 5: "5ms", 10: "10ms", 20: "20ms", 50: "50ms", 100: "100ms"}
        self.combo_comp_attack.setCurrentText(attack_map.get(self.settings.get('compressor_attack_ms', 10), "10ms"))
        release_map = {50: "50ms", 100: "100ms", 200: "200ms", 500: "500ms", 1000: "1000ms"}
        self.combo_comp_release.setCurrentText(release_map.get(self.settings.get('compressor_release_ms', 100), "100ms"))

        self.combo_eq_gain.setCurrentText(f"{int(self.settings.get('eq_gain_db', 0))}dB")
        freq_map = {500: "500Hz", 1000: "1000Hz", 1500: "1500Hz", 2000: "2000Hz", 3000: "3000Hz", 4000: "4000Hz"}
        self.combo_eq_freq.setCurrentText(freq_map.get(self.settings.get('eq_freq_hz', 2000), "2000Hz"))
        q_map = {0.5: "0.5", 1.0: "1.0", 2.0: "2.0", 3.0: "3.0", 5.0: "5.0", 8.0: "8.0"}
        self.combo_eq_q.setCurrentText(q_map.get(self.settings.get('eq_q', 1.0), "1.0"))

    def getSettings(self):
        s = {}
        s['ai_nr_enabled'] = self.combo_ai_nr.currentText() == "On"
        ng_text = self.combo_noise_gate.currentText()
        s['noise_gate_threshold_db'] = float(ng_text.replace('dB', '')) if ng_text != "Off" else -999
        hp_text = self.combo_hp.currentText()
        s['hp_cutoff_hz'] = int(hp_text.replace('Hz', '')) if hp_text != "Off" else 0
        lp_text = self.combo_lp.currentText()
        s['lp_cutoff_hz'] = int(lp_text.replace('Hz', '')) if lp_text != "Off" else 0
        s['gain_db'] = float(self.combo_gain.currentText().replace('dB', ''))
        level_map = {"Off": 0, "Low": 1, "Medium": 2, "High": 3, "Very High": 4}
        s['reverb_reduction_level'] = level_map.get(self.combo_reverb.currentText(), 0)
        s['de_esser_level'] = level_map.get(self.combo_de_esser.currentText(), 0)
        s['de_hum_level'] = level_map.get(self.combo_de_hum.currentText(), 0)
        ct_text = self.combo_comp_thresh.currentText()
        s['compressor_threshold_db'] = float(ct_text.replace('dB', '')) if ct_text != "Off" else -999.0
        s['compressor_ratio'] = float(self.combo_comp_ratio.currentText().replace(':1', ''))
        s['compressor_attack_ms'] = float(self.combo_comp_attack.currentText().replace('ms', ''))
        s['compressor_release_ms'] = float(self.combo_comp_release.currentText().replace('ms', ''))
        s['eq_gain_db'] = float(self.combo_eq_gain.currentText().replace('dB', ''))
        s['eq_freq_hz'] = float(self.combo_eq_freq.currentText().replace('Hz', ''))
        s['eq_q'] = float(self.combo_eq_q.currentText())
        return s

    def focusOutEvent(self, event):
        self.accept()
        super().focusOutEvent(event)


class TimelineBar(QWidget):
    segment_selected = pyqtSignal(int)
    move_segment_request = pyqtSignal(int, int)
    segment_resized = pyqtSignal(int, int, bool)

    def __init__(self, calculate_segment_position_func):
        super().__init__()
        self.calculate_segment_position = calculate_segment_position_func
        self.media_segments = []
        self.position = 0
        self.selected_segment_index = -1
        self.active_segment_index = -1
        self.pixels_per_second = 100
        self.min_segment_width_pixels = 30
        self.row_height_played_upcoming = 60
        self.row_height_active = 60
        self.segment_padding_y_played_upcoming = 5
        self.segment_padding_y_active = 5
        self.line_number_width = 40
        self.segment_gap_x = 5
        self.setMinimumHeight(120)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_media_segments(self, segments, active_index):
        self.media_segments = list(segments or [])
        self.active_segment_index = int(active_index) if isinstance(active_index, int) else -1

        n = len(self.media_segments)
        has_active = 0 <= self.active_segment_index < n
        num_played_segments = self.active_segment_index if has_active else 0
        num_upcoming_segments = (n - self.active_segment_index - 1) if has_active else n

        played_required = self.row_height_played_upcoming * max(1, num_played_segments)
        upcoming_required = self.row_height_played_upcoming * max(1, num_upcoming_segments)
        dynamic_min = max(120, self.row_height_active + played_required + upcoming_required)
        self.setMinimumHeight(dynamic_min)
        self.setMaximumHeight(max(400, dynamic_min))
        self.update()

    def set_position(self, pos):
        try:
            pos = float(pos)
        except (TypeError, ValueError):
            pos = 0.0
        self.position = pos if math.isfinite(pos) and pos >= 0.0 else 0.0
        self.update()

    def set_selected_segment(self, index):
        if self.selected_segment_index != index:
            self.selected_segment_index = index
            self.update()

    def _compute_section_heights(self, h):
        h = max(1, int(h))
        n = len(self.media_segments)
        has_active = 0 <= self.active_segment_index < n
        num_played_segments = self.active_segment_index if has_active else 0
        num_upcoming_segments = (n - self.active_segment_index - 1) if has_active else n

        active_section_height = min(self.row_height_active, h)
        available_dynamic_height = max(0, h - active_section_height)

        played_required = self.row_height_played_upcoming * max(1, num_played_segments)
        upcoming_required = self.row_height_played_upcoming * max(1, num_upcoming_segments)
        total_required = played_required + upcoming_required

        if available_dynamic_height >= total_required:
            extra = available_dynamic_height - total_required
            if total_required > 0:
                played_section_height = played_required
                upcoming_section_height = upcoming_required
                if num_played_segments > 0 and num_upcoming_segments > 0:
                    played_extra = int(extra * (played_required / total_required))
                    played_section_height += played_extra
                    upcoming_section_height += extra - played_extra
                elif num_played_segments > 0:
                    played_section_height += extra
                else:
                    upcoming_section_height += extra
            else:
                played_section_height = available_dynamic_height // 2
                upcoming_section_height = available_dynamic_height - played_section_height
        else:
            if total_required > 0 and available_dynamic_height > 0:
                played_section_height = int(available_dynamic_height * (played_required / total_required))
                upcoming_section_height = available_dynamic_height - played_section_height
            else:
                played_section_height = available_dynamic_height // 2
                upcoming_section_height = available_dynamic_height - played_section_height

        played_section_height = max(0, int(played_section_height))
        upcoming_section_height = max(0, int(upcoming_section_height))

        diff = h - (played_section_height + active_section_height + upcoming_section_height)
        upcoming_section_height = max(0, upcoming_section_height + diff)
        if played_section_height + active_section_height + upcoming_section_height != h:
            active_section_height = max(0, h - played_section_height - upcoming_section_height)

        return played_section_height, active_section_height, upcoming_section_height

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        border_radius = 8

        played_section_height, active_section_height, upcoming_section_height = self._compute_section_heights(h)
        played_bar_y = 0
        active_bar_y = played_section_height
        upcoming_bar_y = played_section_height + active_section_height

        num_played_segments = self.active_segment_index
        num_upcoming_segments = len(self.media_segments) - (self.active_segment_index + 1)

        # --- PLAYED ---
        painter.setPen(QPen(QColor("#555"), 1))
        painter.setBrush(QColor("#222"))
        painter.drawRect(0, played_bar_y, w, played_section_height)
        actual_row_height_played = played_section_height / max(1, num_played_segments) if num_played_segments > 0 else self.row_height_played_upcoming
        actual_segment_rect_height_played = max(1, int(actual_row_height_played - (2 * self.segment_padding_y_played_upcoming)))
        y_off = 0
        for i in range(self.active_segment_index):
            if y_off + actual_row_height_played > played_section_height: break
            segment = self.media_segments[i]
            segment_top = played_bar_y + y_off + self.segment_padding_y_played_upcoming
            try:
                duration = float(segment.get('duration', 0.0))
            except (TypeError, ValueError):
                duration = 0.0
            if not math.isfinite(duration) or duration < 0.0:
                duration = 0.0
            segment_width = max(int(duration * self.pixels_per_second), self.min_segment_width_pixels)
            segment_color = QColor("#555555")
            if segment['type'] in ('audio', 'recorded_audio'): segment_color = QColor("#777777")
            elif segment['type'] == 'media_archive': segment_color = QColor("#444444")
            painter.setPen(Qt.NoPen); painter.setBrush(segment_color)
            painter.drawRoundedRect(self.line_number_width + self.segment_gap_x, int(segment_top), segment_width, actual_segment_rect_height_played, border_radius, border_radius)
            if i == self.selected_segment_index:
                painter.setPen(QPen(QColor("#007bff"), 2)); painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(self.line_number_width + self.segment_gap_x, int(segment_top), segment_width, actual_segment_rect_height_played, border_radius, border_radius)
            painter.setFont(QFont("Arial", 10)); painter.setPen(QColor("white"))
            fm = painter.fontMetrics()
            row_num = str(i + 1)
            rn_rect = fm.boundingRect(row_num)
            painter.drawText((self.line_number_width - rn_rect.width()) // 2,
                             int(played_bar_y + y_off + (actual_row_height_played / 2) + (fm.ascent() / 2)), row_num)
            painter.setPen(QPen(QColor("#555"), 1))
            painter.drawLine(self.line_number_width, int(played_bar_y + y_off), self.line_number_width, int(played_bar_y + y_off + actual_row_height_played))
            painter.setFont(QFont("Arial", 10)); painter.setPen(QColor("black"))
            abbr = f"{segment['abbreviation']} ({segment['formatted_duration_ms']})"
            abbr_rect = fm.boundingRect(abbr)
            if segment_width > abbr_rect.width() + 10:
                painter.drawText(self.line_number_width + self.segment_gap_x + 5,
                                 int(played_bar_y + y_off + self.segment_padding_y_played_upcoming + (actual_segment_rect_height_played / 2) + (fm.ascent() / 2)), abbr)
            y_off += actual_row_height_played

        # --- ACTIVE ---
        painter.setPen(QPen(QColor("#555"), 1)); painter.setBrush(QColor("#282c34"))
        painter.drawRect(0, int(active_bar_y), w, int(active_section_height))
        static_red_line_x = w // 8
        if self.active_segment_index != -1 and 0 <= self.active_segment_index < len(self.media_segments):
            active_segment = self.media_segments[self.active_segment_index]
            try:
                active_duration = float(active_segment.get('duration', 0.0))
            except (TypeError, ValueError):
                active_duration = 0.0
            if not math.isfinite(active_duration) or active_duration < 0.0:
                active_duration = 0.0

            # GÜNCELLEME (2.2.6): Eski kod
            #   calculate_segment_position(active_duration * 1000.0, pps, 1000.0)
            # kullandığı için oran [0,1]'e clamp'leniyordu ve 1 sn'den uzun
            # her segment aynı genişlikte (pps px) görünüyordu. Played ve
            # Upcoming satırlarının kullandığı formülle aynı hizaya getirildi.
            segment_width = max(int(active_duration * self.pixels_per_second),
                                self.min_segment_width_pixels)

            timeline_offset_x_active = static_red_line_x - int(self.position * self.pixels_per_second)
            segment_color = QColor("#555555")
            if active_segment['type'] in ('audio', 'recorded_audio'): segment_color = QColor("#777777")
            elif active_segment['type'] == 'media_archive': segment_color = QColor("#444444")
            segment_rect_height_active = max(1, int(active_section_height - (2 * self.segment_padding_y_active)))
            painter.setPen(Qt.NoPen); painter.setBrush(segment_color)
            painter.drawRoundedRect(int(timeline_offset_x_active), int(active_bar_y + self.segment_padding_y_active), segment_width, segment_rect_height_active, border_radius, border_radius)
            if self.active_segment_index == self.selected_segment_index:
                painter.setPen(QPen(QColor("#007bff"), 2)); painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(int(timeline_offset_x_active), int(active_bar_y + self.segment_padding_y_active), segment_width, segment_rect_height_active, border_radius, border_radius)
            painter.setFont(QFont("Arial", 12)); painter.setPen(QColor("black"))
            fm = painter.fontMetrics()
            abbr = f"{active_segment['abbreviation']} ({active_segment['formatted_duration_ms']})"
            abbr_rect = fm.boundingRect(abbr)
            if segment_width > abbr_rect.width() + 10:
                painter.drawText(int(timeline_offset_x_active + (segment_width - abbr_rect.width()) // 2),
                                 int(active_bar_y + self.segment_padding_y_active + (segment_rect_height_active / 2) + (fm.ascent() / 2)), abbr)
            painter.setPen(QPen(QColor("#444"), 0.5))
            for ms_marker in range(0, int(active_duration * 1000.0) + 100, 100):
                mx = int(timeline_offset_x_active + (ms_marker / 1000.0) * self.pixels_per_second)
                if -50 < mx < w + 50:
                    painter.drawLine(mx, int(active_bar_y), mx, int(active_bar_y + active_section_height))
            painter.setPen(QPen(QColor("red"), 1))
            painter.drawLine(int(static_red_line_x), int(active_bar_y), int(static_red_line_x), int(active_bar_y + active_section_height))

        # --- UPCOMING ---
        painter.setPen(QPen(QColor("#555"), 1)); painter.setBrush(QColor("#222"))
        painter.drawRect(0, int(upcoming_bar_y), w, int(upcoming_section_height))
        actual_row_height_upcoming = upcoming_section_height / max(1, num_upcoming_segments) if num_upcoming_segments > 0 else self.row_height_played_upcoming
        actual_segment_rect_height_upcoming = max(1, int(actual_row_height_upcoming - (2 * self.segment_padding_y_played_upcoming)))
        y_off = 0
        for i in range(self.active_segment_index + 1, len(self.media_segments)):
            if y_off + actual_row_height_upcoming > upcoming_section_height: break
            segment = self.media_segments[i]
            segment_top = upcoming_bar_y + y_off + self.segment_padding_y_played_upcoming
            try:
                duration = float(segment.get('duration', 0.0))
            except (TypeError, ValueError):
                duration = 0.0
            if not math.isfinite(duration) or duration < 0.0:
                duration = 0.0
            segment_width = max(int(duration * self.pixels_per_second), self.min_segment_width_pixels)
            segment_color = QColor("#555555")
            if segment['type'] in ('audio', 'recorded_audio'): segment_color = QColor("#777777")
            elif segment['type'] == 'media_archive': segment_color = QColor("#444444")
            painter.setPen(Qt.NoPen); painter.setBrush(segment_color)
            painter.drawRoundedRect(self.line_number_width + self.segment_gap_x, int(segment_top), segment_width, actual_segment_rect_height_upcoming, border_radius, border_radius)
            if i == self.selected_segment_index:
                painter.setPen(QPen(QColor("#007bff"), 2)); painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(self.line_number_width + self.segment_gap_x, int(segment_top), segment_width, actual_segment_rect_height_upcoming, border_radius, border_radius)
            painter.setFont(QFont("Arial", 10)); painter.setPen(QColor("white"))
            fm = painter.fontMetrics()
            row_num = str(i + 1)
            rn_rect = fm.boundingRect(row_num)
            painter.drawText((self.line_number_width - rn_rect.width()) // 2,
                             int(upcoming_bar_y + y_off + (actual_row_height_upcoming / 2) + (fm.ascent() / 2)), row_num)
            painter.setPen(QPen(QColor("#555"), 1))
            painter.drawLine(self.line_number_width, int(upcoming_bar_y + y_off), self.line_number_width, int(upcoming_bar_y + y_off + actual_row_height_upcoming))
            painter.setFont(QFont("Arial", 10)); painter.setPen(QColor("black"))
            abbr = f"{segment['abbreviation']} ({segment['formatted_duration_ms']})"
            abbr_rect = fm.boundingRect(abbr)
            if segment_width > abbr_rect.width() + 10:
                painter.drawText(self.line_number_width + self.segment_gap_x + 5,
                                 int(upcoming_bar_y + y_off + self.segment_padding_y_played_upcoming + (actual_segment_rect_height_upcoming / 2) + (fm.ascent() / 2)), abbr)
            y_off += actual_row_height_upcoming

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            click_y = event.y()
            played_section_height, active_section_height, upcoming_section_height = self._compute_section_heights(self.height())
            played_bar_y = 0
            active_bar_y = played_section_height
            upcoming_bar_y = played_section_height + active_section_height
            num_played_segments = self.active_segment_index
            num_upcoming_segments = len(self.media_segments) - (self.active_segment_index + 1)

            if click_y < active_bar_y:
                actual_row_height_played = played_section_height / max(1, num_played_segments) if num_played_segments > 0 else self.row_height_played_upcoming
                y_off = 0
                for i in range(self.active_segment_index):
                    if played_bar_y + y_off <= click_y <= played_bar_y + y_off + actual_row_height_played:
                        self.segment_selected.emit(i); return
                    y_off += actual_row_height_played
                self.set_selected_segment(-1)
            elif click_y < upcoming_bar_y:
                if self.active_segment_index != -1:
                    self.segment_selected.emit(self.active_segment_index)
                else:
                    self.set_selected_segment(-1)
            else:
                actual_row_height_upcoming = upcoming_section_height / max(1, num_upcoming_segments) if num_upcoming_segments > 0 else self.row_height_played_upcoming
                y_off = 0
                for i in range(self.active_segment_index + 1, len(self.media_segments)):
                    if upcoming_bar_y + y_off <= click_y <= upcoming_bar_y + y_off + actual_row_height_upcoming:
                        self.segment_selected.emit(i); return
                    y_off += actual_row_height_upcoming
                self.set_selected_segment(-1)

    def _show_context_menu(self, pos: QPoint):
        click_y = pos.y()
        played_section_height, active_section_height, upcoming_section_height = self._compute_section_heights(self.height())
        played_bar_y = 0
        active_bar_y = played_section_height
        upcoming_bar_y = played_section_height + active_section_height
        num_played_segments = self.active_segment_index
        num_upcoming_segments = len(self.media_segments) - (self.active_segment_index + 1)
        clicked_index = -1
        if click_y < active_bar_y:
            actual_row_height_played = played_section_height / max(1, num_played_segments) if num_played_segments > 0 else self.row_height_played_upcoming
            y_off = 0
            for i in range(self.active_segment_index):
                if played_bar_y + y_off <= click_y <= played_bar_y + y_off + actual_row_height_played:
                    clicked_index = i; break
                y_off += actual_row_height_played
        elif click_y < upcoming_bar_y:
            clicked_index = self.active_segment_index
        else:
            actual_row_height_upcoming = upcoming_section_height / max(1, num_upcoming_segments) if num_upcoming_segments > 0 else self.row_height_played_upcoming
            y_off = 0
            for i in range(self.active_segment_index + 1, len(self.media_segments)):
                if upcoming_bar_y + y_off <= click_y <= upcoming_bar_y + y_off + actual_row_height_upcoming:
                    clicked_index = i; break
                y_off += actual_row_height_upcoming
        if clicked_index != -1:
            self.set_selected_segment(clicked_index)
            menu = QMenu(self)
            move_up_action = QAction("Move Up ▲", self)
            if clicked_index > 0:
                move_up_action.triggered.connect(lambda: self.move_segment_request.emit(clicked_index, -1))
            else:
                move_up_action.setEnabled(False)
            menu.addAction(move_up_action)
            move_down_action = QAction("Move Down ▼", self)
            if clicked_index < len(self.media_segments) - 1:
                move_down_action.triggered.connect(lambda: self.move_segment_request.emit(clicked_index, 1))
            else:
                move_down_action.setEnabled(False)
            menu.addAction(move_down_action)
            menu.exec_(self.mapToGlobal(pos))
        else:
            self.set_selected_segment(-1)



class MediaEditor(QWidget):
    MIN_SEGMENT_DURATION_SEC = 1.1

    def __init__(self, core_window_ref=None, parent=None):
        super().__init__(parent)
        self.core_window_ref = core_window_ref
        self.setWindowTitle("Media Timeline Player")
        self.setStyleSheet("background-color: #282c34; color: white;")

        self.noise_filter_enabled = self._load_noise_filter_setting()

        self.media_queue = []
        self.current_media_index = -1
        self.is_playing = False
        self.position = 0
        self.paused_position = 0
        self.audio_sequence_counter = 0
        self.video_sequence_counter = 0
        self.media_sequence_counter = 0
        self.shift_pressed = False
        self.active_message_box = None
        self.is_sequence_play_active = False
        self.is_fullscreen = False

        self.current_project_path = None

        self.filter_settings = {
            'ai_nr_enabled': True, 'noise_gate_threshold_db': -70.0,
            'hp_cutoff_hz': 150, 'lp_cutoff_hz': 10000, 'gain_db': 6.0,
            'reverb_reduction_level': 0, 'de_esser_level': 0, 'de_hum_level': 0,
            'compressor_threshold_db': 0.0, 'compressor_ratio': 3.0,
            'compressor_attack_ms': 5.0, 'compressor_release_ms': 150.0,
            'eq_gain_db': 0.0, 'eq_freq_hz': 1000.0, 'eq_q': 1.0,
        }
        self.load_filter_settings()
        self._normalize_filter_settings()

        self.seek_interval_ms = 2000
        self.seek_intervals = {
            "2s": 2000, "3s": 3000, "5s": 5000, "10s": 10000, "15s": 15000,
            "30s": 30000, "1m": 60000, "1.5m": 90000, "2m": 120000, "5m": 300000,
            "10m": 600000, "30m": 1800000
        }
        self.millisecond_seek_intervals = {"100ms": 100, "200ms": 200, "500ms": 500, "1s": 1000}
        self.frame_seek_step_sec = 0.04

        self._undo_stack = []
        self._redo_stack = []
        self._max_undo_states = 4

        # QMediaPlayer + kendi video yüzeyimiz (VideoCanvas/VideoSurface); her segment için taze oynatıcı
        self.video_widget = VideoCanvas(self)
        # Oynatma durum makinesi (segment yükleme/bitiş)
        self._media_ready = False
        self._pending_play = False
        self._pending_seek_ms = None
        self._segment_end_handled = False
        self._loaded_index = -1
        self._loaded_path = None
        self._create_player()

        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.update_position)

        self.media_save_dir = SAVE_DIR
        self.audio_record_dir = SAVE_DIR
        self._ensure_dirs_exist()
        self._clean_save_dir_on_startup()

        self.media_engine = None
        self._pa_inited = False
        try:
            self.media_engine = ctypes.CDLL(LIB_PATH)
            self.media_engine.calculate_segment_position.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double]
            self.media_engine.calculate_segment_position.restype = ctypes.c_double
            self.media_engine.update_timeline_smoothly.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double]
            self.media_engine.update_timeline_smoothly.restype = ctypes.c_double
            self.media_engine.engine_version.restype = ctypes.c_int
            if self.media_engine.engine_version() < 300:
                raise AttributeError("media_engine.so eski sürüm; media/derleme.txt ile yeniden derleyin")
            self.media_engine.set_tool_paths.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.set_tool_paths(FFMPEG_PATH.encode('utf-8'), FFPROBE_PATH.encode('utf-8'))
            self.media_engine.init_audio_engine.restype = ctypes.c_int
            self.media_engine.terminate_audio_engine.restype = ctypes.c_int
            self.media_engine.start_audio_record.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.start_audio_record.restype = ctypes.c_int
            self.media_engine.stop_audio_record.restype = ctypes.c_int
            self.media_engine.merge_audio_files.argtypes = [ctypes.c_char_p]
            self.media_engine.merge_audio_files.restype = ctypes.c_int
            self.media_engine.cut_media_segment.argtypes = [ctypes.c_char_p, ctypes.c_longlong, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.cut_media_segment.restype = ctypes.c_int
            self.media_engine.delete_media_file.argtypes = [ctypes.c_char_p]
            self.media_engine.delete_media_file.restype = ctypes.c_int
            self.media_engine.get_media_duration_ms.argtypes = [ctypes.c_char_p]
            self.media_engine.get_media_duration_ms.restype = ctypes.c_longlong
            self.media_engine.get_video_dimensions.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
            self.media_engine.get_video_dimensions.restype = ctypes.c_int
            self.media_engine.media_probe_json.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
            self.media_engine.media_probe_json.restype = ctypes.c_int
            self.media_engine.archive_segments_with_compression.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.archive_segments_with_compression.restype = ctypes.c_int
            self.media_engine.archive_segments.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.archive_segments.restype = ctypes.c_int
            self.media_engine.extract_segments.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.extract_segments.restype = ctypes.c_int
        except (OSError, AttributeError) as e:
            print(f"Media engine yüklenemedi: {e}")
            self.media_engine = None

        self.is_recording = False
        self.is_camera_mode_selected = False
        self.is_audio_mode_selected = False
        self.is_stopping_audio_recording = False

        # Kayıt oturumu (media_recorder süreci)
        self.camera_settings = self._load_camera_settings()
        self._rec_session = None
        self._rec_kind = None            # 'camera' | 'audio' | 'audio_pa' (yedek PortAudio)
        self._rec_out = None
        self._rec_dir = None
        self._rec_counter = 0
        self._rec_started_at = 0.0
        self._pv_path = None
        self._pv_reader = None
        self.camera_timer = QTimer()
        self.camera_timer.setInterval(66)
        self.camera_timer.timeout.connect(self._update_camera_preview)

        # Export / dosya yönetimi
        self._import_after_index = None
        self._last_added_index = -1
        self._export_task = None
        self.export_canvas_mode = "auto"
        self._discarded_paths = set()

        self.init_ui()
        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        self.total_time_label.setText(self.format_time_display_with_ms(self._get_total_overall_duration()))
        self._update_record_button_state()
        self._update_sequence_play_button_state()
        self.timeline.move_segment_request.connect(self.handle_move_segment_request)
        self.timeline.segment_resized.connect(self.handle_segment_resize_request)
        self._save_state()

    # -------------------- C++ zaman çizelgesi sarmalayıcıları --------------------
    def _calculate_segment_position(self, start_time_ms, timeline_width, total_timeline_duration_ms):
        """Zaman çizelgesi segment konumu (saf C++)."""
        if self.media_engine is None:
            return 0.0
        try:
            value = float(self.media_engine.calculate_segment_position(
                float(start_time_ms), float(timeline_width), float(total_timeline_duration_ms)))
            return value if (math.isfinite(value) and value >= 0.0) else 0.0
        except Exception as e:
            print(f"MediaEditor: calculate_segment_position çağrısı başarısız: {e}")
            return 0.0

    def _update_timeline_smoothly(self, current_value, target_value, step_size):
        """Zaman çizelgesi yumuşak güncelleme (saf C++)."""
        if self.media_engine is None:
            return float(target_value)
        try:
            value = float(self.media_engine.update_timeline_smoothly(
                float(current_value), float(target_value), float(step_size)))
            return value if math.isfinite(value) else float(current_value)
        except Exception as e:
            print(f"MediaEditor: update_timeline_smoothly çağrısı başarısız: {e}")
            return float(target_value)

    def _clean_save_dir_on_startup(self):
        try:
            if os.path.exists(self.media_save_dir):
                for filename in os.listdir(self.media_save_dir):
                    file_path = os.path.join(self.media_save_dir, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f"Startup: Dosya silinemedi: {file_path}. Hata: {e}")
                print(f"Startup: {self.media_save_dir} kalıcı olarak temizlendi.")
        except Exception as e:
            print(f"Startup temizleme hatası: {e}")

    def load_filter_settings(self):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                aliases = {
                    'comp_threshold_db': 'compressor_threshold_db',
                    'comp_ratio': 'compressor_ratio',
                    'comp_attack_ms': 'compressor_attack_ms',
                    'comp_release_ms': 'compressor_release_ms',
                }
                for old_key, new_key in aliases.items():
                    if new_key not in loaded and old_key in loaded:
                        loaded[new_key] = loaded[old_key]
                self.filter_settings.update(loaded)
                self._normalize_filter_settings()
            else:
                print("Python: Filtre ayar dosyası sözlük biçiminde değil; varsayılan ayarlar korunuyor.")
            print(f"Python: Filtre ayarları {SETTINGS_FILE} dosyasından yüklendi.")
        except FileNotFoundError:
            print(f"Python: Ayar dosyası '{SETTINGS_FILE}' bulunamadı. Varsayılan ayarlar.")
            self.save_filter_settings()
        except json.JSONDecodeError:
            print(f"Python: Ayar dosyası '{SETTINGS_FILE}' bozuk. Varsayılan ayarlar.")
        except Exception as e:
            print(f"Python: Ayarlar yüklenirken hata: {e}")

    def _normalize_filter_settings(self):
        bool_value = self.filter_settings.get('ai_nr_enabled', True)
        self.filter_settings['ai_nr_enabled'] = bool(bool_value)

        float_defaults = {
            'noise_gate_threshold_db': -70.0,
            'hp_cutoff_hz': 150.0,
            'lp_cutoff_hz': 10000.0,
            'gain_db': 6.0,
            'compressor_threshold_db': 0.0,
            'compressor_ratio': 3.0,
            'compressor_attack_ms': 5.0,
            'compressor_release_ms': 150.0,
            'eq_gain_db': 0.0,
            'eq_freq_hz': 1000.0,
            'eq_q': 1.0,
        }
        for key, default in float_defaults.items():
            try:
                value = float(self.filter_settings.get(key, default))
            except (TypeError, ValueError):
                value = default
            if not math.isfinite(value):
                value = default
            self.filter_settings[key] = value

        for key in ('reverb_reduction_level', 'de_esser_level', 'de_hum_level'):
            try:
                value = int(self.filter_settings.get(key, 0))
            except (TypeError, ValueError):
                value = 0
            self.filter_settings[key] = max(0, min(4 if key == 'reverb_reduction_level' else 3, value))

    def save_filter_settings(self):
        try:
            self.filter_settings['noise_filter_enabled'] = self.noise_filter_enabled
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.filter_settings, f, indent=4)
            print(f"Python: Filtre ayarları {SETTINGS_FILE} dosyasına kaydedildi.")
        except Exception as e:
            print(f"Python: Ayarlar kaydedilirken hata: {e}")

    def _load_noise_filter_setting(self):
        try:
            if os.path.exists(OVERLAY_SETTINGS_FILE):
                with open(OVERLAY_SETTINGS_FILE, 'r') as f:
                    return json.load(f).get('noise_filter_enabled', False)
        except Exception as e:
            print(f"Python: I butonu ayarı yüklenemedi: {e}")
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
        except Exception as e:
            print(f"Python: I butonu ayarı kaydedilemedi: {e}")

    @staticmethod
    def _safe_filtfilt(b, a, data):
        try:
            if len(data) <= 1:
                return data
            padlen = 3 * max(len(a), len(b))
            if len(data) <= padlen:
                print("Python: Ses çok kısa; filtfilt adımı atlandı.")
                return data
            return sig.filtfilt(b, a, data)
        except Exception as e:
            print(f"Python: filtfilt adımı atlandı: {e}")
            return data

    def _apply_python_audio_filter(self, input_wav_path, progress_dialog):
        try:
            s = self.filter_settings
            output_wav_path = input_wav_path.replace('.wav', '_filtered.wav')
            progress_dialog.setLabelText("Reading audio data..."); QApplication.processEvents()
            data, rate = sf.read(input_wav_path)
            if data.ndim > 1: data = data.mean(axis=1)
            processed = data.copy()
            original_num_samples = len(data)

            gain_db = s.get('gain_db', 0.0)
            if gain_db != 0.0:
                progress_dialog.setLabelText(f"Applying Gain: {gain_db}dB"); QApplication.processEvents()
                processed *= 10 ** (gain_db / 20.0)

            hp_cutoff = s.get('hp_cutoff_hz', 0)
            if hp_cutoff > 0:
                progress_dialog.setLabelText(f"High-Pass Filter: {hp_cutoff}Hz"); QApplication.processEvents()
                nyquist = 0.5 * rate
                if 0.0 < hp_cutoff < nyquist:
                    b, a = sig.butter(4, hp_cutoff / nyquist, btype='highpass', analog=False)
                    processed = self._safe_filtfilt(b, a, processed)
                else:
                    print(f"Python: HP filtresi atlandı; cutoff {hp_cutoff}Hz, Nyquist {nyquist}Hz.")

            lp_cutoff = s.get('lp_cutoff_hz', 0)
            if lp_cutoff > 0:
                progress_dialog.setLabelText(f"Low-Pass Filter: {lp_cutoff}Hz"); QApplication.processEvents()
                nyquist = 0.5 * rate
                if 0.0 < lp_cutoff < nyquist:
                    b, a = sig.butter(4, lp_cutoff / nyquist, btype='lowpass', analog=False)
                    processed = self._safe_filtfilt(b, a, processed)
                else:
                    print(f"Python: LP filtresi atlandı; cutoff {lp_cutoff}Hz, Nyquist {nyquist}Hz.")

            threshold_db = s.get('noise_gate_threshold_db', -999)
            if threshold_db > -990:
                progress_dialog.setLabelText(f"Applying Noise Gate: {threshold_db}dB"); QApplication.processEvents()
                threshold_linear = 10 ** (threshold_db / 20.0)
                processed[np.abs(processed) < threshold_linear] = 0

            de_hum_level = s.get('de_hum_level', 0)
            if de_hum_level > 0:
                q_map = {1: 10.0, 2: 30.0, 3: 60.0}
                q_val = q_map.get(de_hum_level, 30.0)
                progress_dialog.setLabelText(f"Applying De-Hum: Level={de_hum_level}"); QApplication.processEvents()
                for freq in [50, 60]:
                    b, a = sig.iirnotch(freq, q_val, fs=rate)
                    processed = self._safe_filtfilt(b, a, processed)

            de_esser_level = s.get('de_esser_level', 0)
            if de_esser_level > 0:
                gain_map = {1: -3.0, 2: -6.0, 3: -9.0}
                gain_db = gain_map.get(de_esser_level, 0.0)
                progress_dialog.setLabelText(f"Applying De-Esser: Level={de_esser_level}"); QApplication.processEvents()
                if 0.0 < 6000.0 < (0.5 * rate):
                    b, a = sig.butter(2, 6000, btype='high', fs=rate, analog=False)
                    high_freqs = self._safe_filtfilt(b, a, processed)
                else:
                    print("Python: De-Esser atlandı; 6kHz örnekleme hızı için geçersiz.")
                    high_freqs = processed
                reduction_factor = 10 ** (gain_db / 20.0)
                processed = processed - high_freqs + (high_freqs * reduction_factor)

            reverb_level = s.get('reverb_reduction_level', 0)
            if reverb_level > 0:
                level_map = {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4}
                strength = level_map.get(reverb_level, 0)
                progress_dialog.setLabelText(f"Reverb Reduction: Level={reverb_level}"); QApplication.processEvents()
                processed = librosa.effects.preemphasis(processed, coef=0.97 - strength)

            comp_threshold_db = s.get('compressor_threshold_db', -999.0)
            if comp_threshold_db > -990.0:
                ratio = s.get('compressor_ratio', 1.0)
                attack = s.get('compressor_attack_ms', 5.0)
                release = s.get('compressor_release_ms', 100.0)
                progress_dialog.setLabelText(f"Compressor: {comp_threshold_db}dB, {ratio}:1"); QApplication.processEvents()
                processed_int16 = (processed * 32767).astype(np.int16)
                audio_segment = AudioSegment(processed_int16.tobytes(), frame_rate=rate, sample_width=processed_int16.dtype.itemsize, channels=1)
                compressed_segment = compress_dynamic_range(audio_segment, threshold=comp_threshold_db, ratio=ratio, attack=attack, release=release)
                processed = np.array(compressed_segment.get_array_of_samples(), dtype=np.float32) / 32767.0

            eq_gain_db = s.get('eq_gain_db', 0.0)
            if eq_gain_db != 0.0:
                eq_freq = s.get('eq_freq_hz', 1000.0)
                eq_q = s.get('eq_q', 1.0)
                progress_dialog.setLabelText(f"Parametric EQ: {eq_gain_db}dB @ {eq_freq}Hz"); QApplication.processEvents()
                if 0.0 < eq_freq < (0.5 * rate) and eq_q > 0.0:
                    b, a = sig.iirpeak(eq_freq, eq_q, fs=rate)
                    g = 10.0 ** (eq_gain_db / 20.0)
                    b_gained = b * g if eq_gain_db > 0 else b / abs(g)
                    processed = sig.lfilter(b_gained, a, processed)
                else:
                    print(f"Python: EQ atlandı; freq={eq_freq}, Q={eq_q}, Nyquist={0.5 * rate}.")

            if s.get('ai_nr_enabled', False):
                progress_dialog.setLabelText("Applying AI Noise Reduction..."); QApplication.processEvents()
                processed = nr.reduce_noise(y=processed, sr=rate, prop_decrease=1.0, freq_mask_smooth_hz=500, time_mask_smooth_ms=100)

            if len(processed) < original_num_samples:
                processed = np.concatenate((processed, np.zeros(original_num_samples - len(processed))))
            elif len(processed) > original_num_samples:
                processed = processed[:original_num_samples]

            progress_dialog.setLabelText("Saving processed audio..."); QApplication.processEvents()
            sf.write(output_wav_path, processed, rate)
            return output_wav_path
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"Python audio filtering error: {e}")

    def showAdvancedFilterDialog(self, pos):
        if AUDIO_LIBS_MISSING:
            show_missing_libs_error(self); return
        dialog = AdvancedFilterDialog(initial_settings=self.filter_settings, parent=self)
        global_pos = self.noise_filter_button.mapToGlobal(QPoint(0, self.noise_filter_button.height()))
        dialog.move(global_pos)
        if dialog.exec_():
            self.filter_settings = dialog.getSettings()
            self.save_filter_settings()

    def toggleNoiseFilter(self):
        if AUDIO_LIBS_MISSING:
            show_missing_libs_error(self)
            self.noise_filter_enabled = False
            self.noise_filter_button.setStyleSheet(self.buttonStylePressure(self.noise_filter_enabled))
            return
        self.noise_filter_enabled = not self.noise_filter_enabled
        self.noise_filter_button.setStyleSheet(self.buttonStylePressure(self.noise_filter_enabled))
        self._save_noise_filter_setting()
        self.save_filter_settings()
        if self.core_window_ref:
            self.core_window_ref.set_media_filter_connection(self.noise_filter_enabled)

    def buttonStylePressure(self, is_active: bool) -> str:
        if is_active:
            return """
                QPushButton { background-color: #555; color: white; font-size: 14px; font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 5px; }
                QPushButton:hover { background-color: #666; }
                QPushButton:pressed { background-color: #777; }
            """
        return """
            QPushButton { background-color: transparent; color: white; font-size: 14px; font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 5px; }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

    def _create_player(self):
        """Yeni QMediaPlayer + kendi video yüzeyi. Her segment yüklemesinde taze oynatıcı kullanılır:
        aynı GStreamer playbin'i farklı akışlı dosyalar (dikey video -> yatay video -> ses) arasında
        yeniden kullanmak, bazı sistemlerde playsink'te iç hataya (uygulamanın kapanmasına) yol açıyordu."""
        player = QMediaPlayer(self)
        surface = VideoSurface(self.video_widget, self)
        player.setVideoOutput(surface)
        player.setPlaybackRate(1.0)
        player.stateChanged.connect(self._handle_player_state_changed)
        player.error.connect(self._handle_player_error)
        player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player = player
        self.video_surface = surface

    def _recycle_player(self):
        """Eski oynatıcıyı güvenle bırakır (durdurur, boşaltır, gecikmeli siler) ve yenisini oluşturur."""
        old = getattr(self, 'player', None)
        old_surface = getattr(self, 'video_surface', None)
        if old_surface is not None:
            old_surface.detach()
        if old is not None:
            try:
                old.stop()
                old.setMedia(QMediaContent())
            except Exception as e:
                print(f"Eski oynatıcı durdurulamadı: {e}")
            QTimer.singleShot(2000, old.deleteLater)
            if old_surface is not None:
                QTimer.singleShot(2000, old_surface.deleteLater)
        self._create_player()

    def _handle_player_state_changed(self, state):
        if self.sender() is not None and self.sender() is not self.player:
            return                                   # eski (bırakılmış) oynatıcıdan gelen sinyal
        if state == QMediaPlayer.PlayingState:
            self.is_playing = True
            self.play_pause_btn.setText("Pause")
            self.timer.start()
        else:
            self.is_playing = False
            self.play_pause_btn.setText("Play")
            self.timer.stop()

    def _on_media_status_changed(self, status):
        """Segment yüklenince bekleyen konum/oynatma isteğini uygular; segment bitince ilerler.
        (Eski sürümde setMedia hemen ardından setPosition/play çağrılıyordu; yükleme bitmeden
        yapılan bu çağrılar kayboluyor ve görüntü/ses karışıyordu.)"""
        if self.sender() is not None and self.sender() is not self.player:
            return
        if status in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia):
            if not self._media_ready:
                self._media_ready = True
                if self._pending_seek_ms is not None:
                    self.player.setPosition(int(self._pending_seek_ms))
                    self._pending_seek_ms = None
                if self._pending_play:
                    self._pending_play = False
                    self.player.play()
                elif (0 <= self.current_media_index < len(self.media_queue) and
                      self.media_queue[self.current_media_index]['type'] in ('video', 'recorded_video')):
                    self.player.pause()      # duraklatılmış önizleme: seçili karenin görüntüsü ekranda kalsın
        elif status == QMediaPlayer.EndOfMedia:
            self._on_segment_end()

    def _on_segment_end(self):
        """Segmentin (kırpılmış süresi dahil) sonuna gelindi."""
        if self._segment_end_handled or self.current_media_index == -1:
            return
        self._segment_end_handled = True
        if self.is_sequence_play_active:
            QTimer.singleShot(0, self._advance_to_next_segment)
            return
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        try:
            seg_dur = max(0.0, float(self.media_queue[self.current_media_index].get('duration', 0.0)))
        except (IndexError, TypeError, ValueError):
            seg_dur = 0.0
        self.position = seg_dur
        self.paused_position = seg_dur
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))

    def _handle_player_error(self, error):
        if self.sender() is not None and self.sender() is not self.player:
            return
        error_string = self.player.errorString()
        print(f"QMediaPlayer Error: {error_string} (Code: {error})")
        if getattr(self, '_player_error_shown', False):
            return
        self._player_error_shown = True
        try:
            self.stop_media()
            self.show_message_box("Oynatma Hatası",
                                  f"Bu dosya oynatılamadı:\n{error_string}\n\n"
                                  "Gerekli GStreamer çözücüleri kurulu mu? (gstreamer1.0-libav, plugins-good/bad/ugly)")
        finally:
            self._player_error_shown = False

    def _seek(self, ms):
        """Konuma git. Medya henüz yüklenmediyse istek saklanır ve yükleme bitince uygulanır."""
        ms = max(0, int(ms))
        if self._media_ready:
            self.player.setPosition(ms)
        else:
            self._pending_seek_ms = ms

    def _ensure_dirs_exist(self):
        QDir().mkpath(self.media_save_dir)
        QDir().mkpath(self.audio_record_dir)

    def topBarStyle(self) -> str:
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 14px; font-weight: bold;
                border: 2px solid #555; border-radius: 8px; padding: 5px 10px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

    def buttonStyle(self, button_type: str = "default") -> str:
        base_style = """
            QPushButton { background-color: transparent; color: white; font-size: 14px; font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 5px 15px; }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
            QPushButton:disabled { background-color: #111; color: #888; border-color: #333; }
            QPushButton::menu-indicator { image: none; width: 0px; }
        """
        if button_type == "record_active":
            return base_style + """
                QPushButton { background-color: #6c757d; color: white; border: 2px solid #545b62; }
                QPushButton:hover { background-color: #5a6268; }
                QPushButton:pressed { background-color: #494f54; }
            """
        elif button_type == "sequence_play_active":
            return base_style + """
                QPushButton { background-color: #6c757d; color: white; border: 2px solid #545b62; padding: 5px 5px; font-size: 14px; font-weight: bold; }
                QPushButton:hover { background-color: #5a6268; }
                QPushButton:pressed { background-color: #494f54; }
            """
        elif button_type == "sequence_toggle":
            return base_style + """
                QPushButton { background-color: transparent; color: white; border: 2px solid #555; padding: 5px 5px; font-size: 14px; font-weight: bold; }
                QPushButton:hover { background-color: #444; border-color: #777; }
                QPushButton:pressed { background-color: #666; border-color: #999; }
            """
        elif button_type == "combobox_style":
            return """
                QComboBox { background-color: transparent; color: white; border: 2px solid #555; border-radius: 8px; padding: 5px 15px; font-size: 14px; font-weight: bold; }
                QComboBox::drop-down { border: none; width: 0px; }
                QComboBox::down-arrow { image: none; }
                QComboBox:hover { background-color: #444; border-color: #777; }
                QComboBox:pressed { background-color: #666; border-color: #999; }
                QComboBox QAbstractItemView { background-color: #282c34; color: white; selection-background-color: #007bff; border: 1px solid #555; }
            """
        return base_style

    def buttonStyleMini(self):
        return """
            QPushButton { background-color: transparent; color: white; font-size: 16px; border: 2px solid #555; border-radius: 8px; padding: 2px; }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- ÜST BAR (TASARIM KORUNDU) ---
        self.toolbar_frame = QFrame(self)
        self.toolbar_frame.setStyleSheet("background-color: #222; border-bottom: 2px solid #555;")
        self.toolbar_frame.setFixedHeight(40)

        top_buttons_layout = QHBoxLayout(self.toolbar_frame)
        top_buttons_layout.setContentsMargins(10, 5, 10, 5)
        top_buttons_layout.setSpacing(10)

        self.file_btn = QPushButton("File")
        self.file_btn.clicked.connect(self.select_media_files)
        self.file_btn.setStyleSheet(self.topBarStyle())
        self.file_btn.setFixedSize(90, 30)
        top_buttons_layout.addWidget(self.file_btn)

        self.save_button = QPushButton()
        self.save_button.setIcon(create_svg_icon(SVG_SAVE_ICON, size=20, color="white"))
        self.save_button.setStyleSheet(self.buttonStyleMini())
        self.save_button.setFixedSize(30, 30)
        self.save_button.setToolTip("Quick Save")
        self.save_button.clicked.connect(self.quick_save_media)
        top_buttons_layout.addWidget(self.save_button)

        self.undo_btn = QPushButton()
        self.undo_btn.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20))
        self.undo_btn.setStyleSheet(self.buttonStyleMini())
        self.undo_btn.setFixedSize(30, 30)
        self.undo_btn.clicked.connect(self.undo)
        top_buttons_layout.addWidget(self.undo_btn)

        self.redo_btn = QPushButton()
        self.redo_btn.setIcon(create_svg_icon(SVG_REDO_ICON, size=20))
        self.redo_btn.setStyleSheet(self.buttonStyleMini())
        self.redo_btn.setFixedSize(30, 30)
        self.redo_btn.clicked.connect(self.redo)
        top_buttons_layout.addWidget(self.redo_btn)

        self.play_pause_btn = QPushButton("Play")
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.play_pause_btn.setStyleSheet(self.topBarStyle())
        self.play_pause_btn.setFixedSize(90, 30)
        top_buttons_layout.addWidget(self.play_pause_btn)

        self.sequence_play_btn = QPushButton("/")
        self.sequence_play_btn.clicked.connect(self._toggle_sequence_play_mode)
        self.sequence_play_btn.setStyleSheet(self.buttonStyle("sequence_toggle"))
        self.sequence_play_btn.setFixedSize(30, 30)
        top_buttons_layout.addWidget(self.sequence_play_btn)

        self.cut_btn = QPushButton("Cut")
        self.cut_btn.clicked.connect(self.cut_media)
        self.cut_btn.setStyleSheet(self.topBarStyle())
        self.cut_btn.setFixedSize(60, 30)
        top_buttons_layout.addWidget(self.cut_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_selected_media)
        self.delete_btn.setStyleSheet(self.topBarStyle())
        self.delete_btn.setFixedSize(90, 30)
        top_buttons_layout.addWidget(self.delete_btn)

        self.camera_mode_btn = QPushButton("Camera")
        self.camera_mode_btn.clicked.connect(self._handle_camera_button_click)
        self.camera_mode_btn.setContextMenuPolicy(Qt.CustomContextMenu)
        self.camera_mode_btn.customContextMenuRequested.connect(self._show_camera_menu)
        self.camera_mode_btn.setStyleSheet(self.topBarStyle())
        self.camera_mode_btn.setFixedSize(95, 30)
        top_buttons_layout.addWidget(self.camera_mode_btn)

        self.audio_mode_btn = QPushButton("Sound")
        self.audio_mode_btn.clicked.connect(self._toggle_audio_mode_selection)
        self.audio_mode_btn.setStyleSheet(self.topBarStyle())
        self.audio_mode_btn.setFixedSize(80, 30)
        top_buttons_layout.addWidget(self.audio_mode_btn)

        self.noise_filter_button = QPushButton("I")
        self.noise_filter_button.setToolTip("Noise Reduction Filter (On/Off)")
        self.noise_filter_button.setStyleSheet(self.buttonStylePressure(self.noise_filter_enabled))
        self.noise_filter_button.setFixedSize(30, 30)
        self.noise_filter_button.clicked.connect(self.toggleNoiseFilter)
        top_buttons_layout.addWidget(self.noise_filter_button)

        self.clear_folders_btn = QPushButton("S")
        self.clear_folders_btn.setToolTip("Klasörü Temizle")
        self.clear_folders_btn.setStyleSheet(self.buttonStyleMini())
        self.clear_folders_btn.setFixedSize(30, 30)
        self.clear_folders_btn.clicked.connect(self.clear_media_folders)
        top_buttons_layout.addWidget(self.clear_folders_btn)

        self.seek_interval_box = QComboBox()
        all_seek_options = {**self.millisecond_seek_intervals, **self.seek_intervals}
        sorted_keys = sorted(all_seek_options.keys(), key=lambda x: (all_seek_options[x], x))
        self.seek_interval_box.addItems(sorted_keys)
        self.seek_interval_box.setCurrentText('2s')
        self.seek_interval_box.setFixedSize(84, 30)
        self.seek_interval_box.setStyleSheet(self.buttonStyle("combobox_style"))
        self.seek_interval_box.currentTextChanged.connect(self.change_seek_interval)
        top_buttons_layout.addWidget(self.seek_interval_box)

        self.playback_speed_box = QComboBox()
        self.playback_speed_options = ["0.01", "0.1", "0.25", "0.5", "1", "1.25", "1.5", "1.75", "2"]
        self.playback_speed_box.addItems(self.playback_speed_options)
        self.playback_speed_box.setCurrentText("1")
        self.playback_speed_box.setFixedSize(65, 30)
        self.playback_speed_box.setStyleSheet(self.buttonStyle("combobox_style"))
        self.playback_speed_box.currentTextChanged.connect(self.change_playback_speed)
        top_buttons_layout.addWidget(self.playback_speed_box)

        top_buttons_layout.addStretch()

        self.current_time_label = QLabel("00:00:00.000")
        self.current_time_label.setStyleSheet("color: white; font-size: 12px; font-weight: normal;")
        top_buttons_layout.addWidget(self.current_time_label)

        sep = QLabel(" / ")
        sep.setStyleSheet("color: white; font-size: 12px; font-weight: normal;")
        top_buttons_layout.addWidget(sep)

        self.total_time_label = QLabel("00:00:00.000")
        self.total_time_label.setStyleSheet("color: white; font-size: 12px; font-weight: normal;")
        top_buttons_layout.addWidget(self.total_time_label)

        self.export_btn = QPushButton("Export")
        self.export_btn.setContextMenuPolicy(Qt.CustomContextMenu)
        self.export_btn.customContextMenuRequested.connect(self._show_export_format_menu)
        self.export_btn.setStyleSheet(self.topBarStyle())
        self.export_btn.setFixedSize(90, 30)
        self.export_btn.clicked.connect(self._on_export_left_click)
        top_buttons_layout.addWidget(self.export_btn)

        self.media_btn = QPushButton("Media")
        self.media_btn.setStyleSheet(self.topBarStyle())
        self.media_btn.clicked.connect(self.triggerCoreSwitcher)
        self.media_btn.setFixedSize(90, 30)
        top_buttons_layout.addWidget(self.media_btn)

        main_layout.addWidget(self.toolbar_frame)

        # --- VIDEO ALANI ---
        self.video_output_widget = self.video_widget
        self.video_output_widget.setStyleSheet("background-color: black;")
        self.video_output_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_frame = QFrame(self)
        self.video_frame.setStyleSheet("background-color: black;")
        self.video_frame_layout = QVBoxLayout(self.video_frame)
        self.video_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.video_frame_layout.addWidget(self.video_output_widget)
        self.video_output_widget.hide()

        self.camera_preview_label = QLabel(self.video_frame)
        self.camera_preview_label.setAlignment(Qt.AlignCenter)
        self.camera_preview_label.setStyleSheet("background-color: black;")
        self.camera_preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_frame_layout.addWidget(self.camera_preview_label)
        self.camera_preview_label.hide()

        self.audio_icon_label = QLabel("♪", self.video_frame)
        self.audio_icon_label.setAlignment(Qt.AlignCenter)
        self.audio_icon_label.setFont(QFont("Arial", 100))
        self.audio_icon_label.setStyleSheet("color: #AAAAAA; background-color: #333333;")
        self.audio_icon_label.hide()
        self.video_frame_layout.addWidget(self.audio_icon_label)
        self.audio_icon_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- TIMELINE (DİNAMİK) ---
        self.timeline = TimelineBar(self._calculate_segment_position)
        self.timeline.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.timeline.setMinimumHeight(120)
        self.timeline.setMaximumHeight(400)
        self.timeline.segment_selected.connect(self._on_timeline_segment_selected)

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.video_frame)
        self.splitter.addWidget(self.timeline)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([700, 180])
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #555;}")

        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)
        self._update_undo_redo_buttons()

        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self.redo)

    # ============================================================
    # EXPORT BUTONU MANTIĞI
    # ============================================================
    def _on_export_left_click(self):
        """Sol tık: .media arşiv kaydı. Sıkıştırma türü kullanıcıya sorulur (gz/xz)."""
        if not self.media_queue:
            self.show_message_box("Warning", "Dışa aktarılacak medya yok.")
            return
        if not self.media_engine:
            self.show_message_box("Error", "Medya motoru yüklenemedi.")
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #282c34; color: white; border: 1px solid #555; }
            QMenu::item:selected { background-color: #007bff; }
        """)
        act_gz = menu.addAction("Hızlı Kaydet  (.media / gzip)")
        act_xz = menu.addAction("Yüksek Sıkıştırma  (.media / xz)")
        chosen = menu.exec_(self.export_btn.mapToGlobal(QPoint(0, self.export_btn.height())))
        if chosen == act_gz:
            self._save_project_with_compression("gz")
        elif chosen == act_xz:
            self._save_project_with_compression("xz")

    def _save_project_with_compression(self, compression: str):
        if not self.media_queue:
            return
        filter_str = "Medya Arşivi (*.media)"
        default_name = (self.current_project_path
                        if self.current_project_path
                        else os.path.join(DEFAULT_BASE_DIR, "kavram_projesi.media"))
        output_file_user_selected, _ = _fm.get_save_file_name(
            self, f"Medya Arşivini Dışa Aktar ({compression.upper()})",
            default_name, filter_str, editor="Media")
        if not output_file_user_selected:
            return
        if not output_file_user_selected.lower().endswith(".media"):
            output_file_user_selected += ".media"
        self._save_project_internal(output_file_user_selected, compression)

    def _show_export_format_menu(self, pos: QPoint):
        """Sağ tık: video/ses format seçenekleri ve tuval (en-boy oranı) seçimi."""
        if not self.media_queue:
            self.show_message_box("Warning", "Dışa aktarılacak medya yok.")
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #282c34; color: white; border: 1px solid #555; }
            QMenu::item:selected { background-color: #007bff; }
            QMenu::separator { height: 1px; background: #555; margin: 4px 8px; }
        """)

        video_menu = menu.addMenu("🎬 Video Olarak (Görüntü + Ses)")
        video_menu.addAction("MKV (.mkv)").triggered.connect(lambda: self._export_timeline_with_format("mkv"))
        video_menu.addAction("MP4 (.mp4)").triggered.connect(lambda: self._export_timeline_with_format("mp4"))

        canvas_menu = menu.addMenu("📐 Tuval (en-boy oranı)")
        canvas_group = QActionGroup(canvas_menu)
        canvas_group.setExclusive(True)
        for label, key in (("Otomatik (en uzun yöne göre)", "auto"), ("Yatay 16:9", "16:9"), ("Dikey 9:16", "9:16"),
                           ("Kare 1:1", "1:1"), ("Yatay 4:3", "4:3"), ("Dikey 3:4", "3:4")):
            act = canvas_menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(self.export_canvas_mode == key)
            canvas_group.addAction(act)
            act.triggered.connect(lambda checked, k=key: setattr(self, "export_canvas_mode", k))

        menu.addSeparator()

        audio_menu = menu.addMenu("🎵 Ses Olarak (Sadece Ses)")
        audio_menu.addAction("WAV (.wav - kayıpsız)").triggered.connect(lambda: self._export_timeline_with_format("wav"))
        audio_menu.addAction("MP3 (.mp3 - 192kbps)").triggered.connect(lambda: self._export_timeline_with_format("mp3"))
        audio_menu.addAction("Opus (.opus - 128kbps)").triggered.connect(lambda: self._export_timeline_with_format("opus"))
        audio_menu.addAction("AAC (.m4a - 192kbps)").triggered.connect(lambda: self._export_timeline_with_format("m4a"))
        audio_menu.addAction("FLAC (.flac - kayıpsız)").triggered.connect(lambda: self._export_timeline_with_format("flac"))

        menu.exec_(self.export_btn.mapToGlobal(pos))

    # ------------------------------------------------------------------ export (render)
    @staticmethod
    def _parse_probe(data):
        """ffprobe JSON -> sade sözlük."""
        info = {'duration': 0.0, 'has_video': False, 'has_audio': False, 'width': 0, 'height': 0,
                'rotation': 0, 'fps': 0.0, 'sar': 1.0}
        stream_dur = 0.0
        for s in data.get('streams', []) or []:
            ctype = s.get('codec_type')
            try:
                sd = float(s.get('duration'))
                if sd > stream_dur:
                    stream_dur = sd
            except (TypeError, ValueError):
                pass
            if ctype == 'video' and not info['has_video'] and not (s.get('disposition') or {}).get('attached_pic'):
                info['has_video'] = True
                w, h = int(s.get('width') or 0), int(s.get('height') or 0)
                rot = 0
                for sdata in s.get('side_data_list', []) or []:
                    if 'rotation' in sdata:
                        try:
                            rot = int(round(float(sdata['rotation'])))
                        except (TypeError, ValueError):
                            pass
                try:
                    rot = int((s.get('tags') or {}).get('rotate', rot))
                except (TypeError, ValueError):
                    pass
                rot = ((rot % 360) + 360) % 360
                if rot in (90, 270):
                    w, h = h, w
                info['width'], info['height'], info['rotation'] = w, h, rot
                for key in ('avg_frame_rate', 'r_frame_rate'):
                    try:
                        num, den = str(s.get(key, '0/1')).split('/')
                        val = float(num) / float(den)
                        if val > 0:
                            info['fps'] = val
                            break
                    except (ValueError, ZeroDivisionError):
                        pass
                try:
                    a, b = str(s.get('sample_aspect_ratio', '1:1')).split(':')
                    sar = float(a) / float(b)
                    if sar > 0:
                        info['sar'] = sar
                except (ValueError, ZeroDivisionError):
                    pass
            elif ctype == 'audio' and not info['has_audio']:
                info['has_audio'] = True
        try:
            d = float((data.get('format') or {}).get('duration'))
        except (TypeError, ValueError):
            d = 0.0
        info['duration'] = d if d > 0 else stream_dur
        return info

    def _probe_media(self, path):
        """ffprobe ile ölçüm (süre, akışlar, boyut, döndürme, fps). Başarısızsa None."""
        data = None
        if self.media_engine is not None and hasattr(self.media_engine, 'media_probe_json'):
            try:
                buf = ctypes.create_string_buffer(1 << 20)
                n = self.media_engine.media_probe_json(path.encode('utf-8'), buf, len(buf))
                if n > 0:
                    data = json.loads(buf.value.decode('utf-8', 'replace'))
            except Exception as e:
                print(f"media_probe_json hatası: {e}")
        if data is None:
            try:
                r = subprocess.run([FFPROBE_PATH, "-v", "error", "-print_format", "json",
                                    "-show_format", "-show_streams", path],
                                   capture_output=True, text=True, timeout=30)
                if r.returncode == 0:
                    data = json.loads(r.stdout)
            except Exception as e:
                print(f"ffprobe hatası: {e}")
        if not data:
            return None
        return self._parse_probe(data)

    def _plan_export_canvas(self, entries, mode):
        """Tuval boyutu ve fps. entries: [{'info','duration','has_video'}].
        Otomatik modda, süreye göre en baskın en-boy oranına en yakın hazır oran seçilir."""
        videos = [e for e in entries if e['has_video']]
        import math
        if mode in EXPORT_CANVAS_PRESETS:
            ratio_key = mode
        elif videos:
            best_key, best_score = "16:9", None
            for key, (a, b) in EXPORT_CANVAS_PRESETS.items():
                score = 0.0
                for e in videos:
                    w, h = e['info']['width'], e['info']['height']
                    sar = e['info']['sar'] if e['info']['sar'] > 0 else 1.0
                    if w <= 0 or h <= 0:
                        continue
                    score -= e['duration'] * abs(math.log((w * sar / h) / (a / b)))
                if best_score is None or score > best_score:
                    best_key, best_score = key, score
            ratio_key = best_key
        else:
            ratio_key = "16:9"
        a, b = EXPORT_CANVAS_PRESETS[ratio_key]
        if videos:
            long_side = max(max(e['info']['width'], e['info']['height']) for e in videos)
            long_side = max(640, min(1920, long_side))
        else:
            long_side = 1280
        if a >= b:
            width, height = long_side, long_side * b / a
        else:
            height, width = long_side, long_side * a / b
        width = max(2, int(round(width / 2.0)) * 2)
        height = max(2, int(round(height / 2.0)) * 2)
        # fps: süreye göre en yaygın (yuvarlanmış) değer
        votes = {}
        for e in videos:
            f = int(round(e['info']['fps'])) if e['info']['fps'] > 0 else 30
            f = max(15, min(60, f))
            votes[f] = votes.get(f, 0.0) + e['duration']
        fps = max(votes, key=votes.get) if votes else 30
        return width, height, fps, ratio_key

    def _export_timeline_with_format(self, fmt: str):
        """Zaman çizelgesini TEK geçişli FFmpeg filtre grafiğiyle render eder.

        Her segment ayrı ayrı normalize edilir: aynı tuval (siyah bantlı, oran bozulmadan), aynı fps,
        aynı ses biçimi (48 kHz stereo). Sesi olmayan videolar sessizlikle, görüntüsü olmayan sesler
        siyah ekranla doldurulur ve her segment TAM süresine kırpılır/doldurulur; böylece sıra,
        süre ve ses/görüntü senkronu çizelgedekiyle birebir aynı olur."""
        if not self.media_queue:
            self.show_message_box("Warning", "Dışa aktarılacak medya yok.")
            return
        if self._export_task is not None:
            self.show_message_box("Uyarı", "Zaten bir dışa aktarma sürüyor.")
            return
        if self.is_recording:
            self.show_message_box("Uyarı", "Kayıt sürerken dışa aktarılamaz.")
            return
        fmt = str(fmt).lower()
        allowed_formats = {"mkv", "mp4", "wav", "mp3", "opus", "m4a", "aac", "flac", "ogg"}
        if fmt not in allowed_formats:
            self.show_message_box("Hata", f"Desteklenmeyen dışa aktarma biçimi: {fmt}")
            return
        if not os.path.isabs(FFMPEG_PATH):
            self.show_message_box("Hata", "ffmpeg bulunamadı. Kurulum dosyasını (kurulum_deb.txt / kurulum_arch.txt) çalıştırın.")
            return

        is_audio_only = fmt in ("wav", "mp3", "opus", "m4a", "aac", "flac", "ogg")
        default_name = os.path.join(DEFAULT_BASE_DIR, f"kavram_cikti.{fmt}")
        output_file_path, _ = _fm.get_save_file_name(
            self, f"{'Ses' if is_audio_only else 'Video'} Olarak Dışa Aktar", default_name, f"{fmt.upper()} Dosyası (*.{fmt})", editor="Media")
        if not output_file_path:
            return
        if not output_file_path.lower().endswith(f".{fmt}"):
            output_file_path += f".{fmt}"

        # 1) Ölçüm
        entries = []
        for seg in self.media_queue:
            path = seg.get('path', '')
            if seg.get('type') == 'media_archive':
                continue
            if not path or not os.path.exists(path):
                self.show_message_box("Hata", f"Dosya bulunamadı: {seg.get('name', path)}")
                return
            info = self._probe_media(path)
            if info is None:
                self.show_message_box("Hata", f"Dosya okunamadı: {seg.get('name', path)}")
                return
            duration = float(seg.get('duration') or info['duration'] or 0.0)
            if duration <= 0.0:
                self.show_message_box("Hata", f"Süre alınamadı: {seg.get('name', path)}")
                return
            is_video_seg = seg.get('type') in ('video', 'recorded_video') and info['has_video']
            entries.append({'seg': seg, 'path': path, 'info': info, 'duration': duration,
                            'has_video': is_video_seg, 'has_audio': info['has_audio']})
        if not entries:
            self.show_message_box("Hata", "Dışa aktarılacak geçerli medya yok.")
            return

        total_duration = sum(e['duration'] for e in entries)
        temp_render_dir = tempfile.mkdtemp(prefix="kavram_export_")
        width = height = 0
        fps = 30
        try:
            inputs = []                     # ffmpeg giriş argümanları
            lines = []                      # filtre grafiği satırları
            labels = []
            idx = 0

            if not is_audio_only:
                width, height, fps, _ = self._plan_export_canvas(entries, self.export_canvas_mode)
                placeholder = os.path.join(temp_render_dir, "audio_placeholder.png")
                if any(not e['has_video'] for e in entries):
                    self._create_audio_placeholder_image(placeholder, width, height)

            for n, e in enumerate(entries):
                d = f"{e['duration']:.6f}"
                v_idx = a_idx = None
                if not is_audio_only and e['has_video']:
                    inputs += ["-i", e['path']]
                    v_idx = idx
                    idx += 1
                    a_idx = v_idx if e['has_audio'] else None
                elif not is_audio_only:
                    inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{e['duration'] + 1.0:.3f}", "-i", placeholder]
                    v_idx = idx
                    idx += 1
                    if e['has_audio']:
                        inputs += ["-i", e['path']]
                        a_idx = idx
                        idx += 1
                else:
                    if e['has_audio']:
                        inputs += ["-i", e['path']]
                        a_idx = idx
                        idx += 1

                if not is_audio_only:
                    if e['has_video']:
                        lines.append(
                            f"[{v_idx}:v:0]setpts=PTS-STARTPTS,fps={fps},"
                            f"scale='trunc(iw*sar/2)*2':ih,setsar=1,"
                            f"scale={width}:{height}:force_original_aspect_ratio=decrease:flags=bicubic,"
                            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1,format=yuv420p,"
                            f"tpad=stop_mode=clone:stop_duration={d},trim=duration={d},setpts=PTS-STARTPTS[v{n}]")
                    else:
                        lines.append(
                            f"[{v_idx}:v:0]setpts=PTS-STARTPTS,fps={fps},scale={width}:{height},setsar=1,"
                            f"format=yuv420p,trim=duration={d},setpts=PTS-STARTPTS[v{n}]")
                if a_idx is not None:
                    lines.append(
                        f"[{a_idx}:a:0]asetpts=PTS-STARTPTS,aresample=48000,"
                        f"aformat=sample_fmts=fltp:channel_layouts=stereo,apad,atrim=duration={d},"
                        f"asetpts=PTS-STARTPTS[a{n}]")
                else:
                    lines.append(
                        f"anullsrc=r=48000:cl=stereo,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                        f"atrim=duration={d},asetpts=PTS-STARTPTS[a{n}]")
                labels.append((f"[v{n}]" if not is_audio_only else "") + f"[a{n}]")

            if is_audio_only:
                lines.append("".join(labels) + f"concat=n={len(entries)}:v=0:a=1[aout]")
                maps = ["-map", "[aout]"]
            else:
                lines.append("".join(labels) + f"concat=n={len(entries)}:v=1:a=1[vout][aout]")
                maps = ["-map", "[vout]", "-map", "[aout]"]

            script_path = os.path.join(temp_render_dir, "grafik.txt")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(";\n".join(lines) + "\n")

            if is_audio_only:
                codec = {
                    "wav": ["-c:a", "pcm_s16le"],
                    "mp3": ["-c:a", "libmp3lame", "-b:a", "192k"],
                    "opus": ["-c:a", "libopus", "-b:a", "128k"],
                    "m4a": ["-c:a", "aac", "-b:a", "192k"],
                    "aac": ["-c:a", "aac", "-b:a", "192k"],
                    "flac": ["-c:a", "flac"],
                    "ogg": ["-c:a", "libvorbis", "-q:a", "5"],
                }[fmt] + ["-ar", "48000", "-ac", "2", "-vn"]
            else:
                codec = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                         "-profile:v", "high", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
                if fmt == "mp4":
                    codec += ["-movflags", "+faststart"]

            out_dir = os.path.dirname(output_file_path) or "."
            tmp_out = os.path.join(out_dir, f".kavram_export_{os.getpid()}_{int(time.time())}.{fmt}")
            args = ["-hide_banner", "-v", "error", "-nostdin", "-y"] + inputs + \
                   ["-filter_complex_script", script_path] + maps + codec + \
                   ["-progress", "pipe:1", "-nostats", tmp_out]
        except Exception as e:
            shutil.rmtree(temp_render_dir, ignore_errors=True)
            self.show_message_box("Hata", f"Dışa aktarma hazırlanamadı: {e}")
            return

        progress = QProgressDialog("Render alınıyor...", "İptal", 0, 1000, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Dışa Aktarılıyor")
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setValue(0)
        progress.show()

        task = FFmpegTask(FFMPEG_PATH, args, self)
        self._export_task = task

        def on_progress(seconds):
            progress.setValue(max(0, min(999, int(seconds / total_duration * 1000))))
            progress.setLabelText(f"Render alınıyor... %{min(99, int(seconds / total_duration * 100))}")

        def on_done(ok, log_tail):
            self._export_task = None
            was_cancelled = progress.wasCanceled()
            progress.close()
            shutil.rmtree(temp_render_dir, ignore_errors=True)
            if ok and os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 0:
                try:
                    os.replace(tmp_out, output_file_path)
                except OSError as err:
                    self.show_message_box("Hata", f"Dosya kaydedilemedi: {err}")
                    return
                _fm.notify_saved(self)
            else:
                try:
                    if os.path.exists(tmp_out):
                        os.remove(tmp_out)
                except OSError:
                    pass
                if not was_cancelled:
                    self.show_message_box("Hata", "Dışa aktarma başarısız oldu.\n\n" + (log_tail or "").strip()[-900:])
            task.deleteLater()

        task.progress.connect(on_progress)
        task.done.connect(on_done)
        progress.canceled.connect(task.cancel)
        task.start()

    def export_media_archive(self):
        """Geriye dönük uyumluluk: sol tık davranışı."""
        self._on_export_left_click()

    def _save_project_internal(self, target_path, compression="gz"):
        if not self.media_engine:
            self.show_message_box("Hata", "Medya motoru yüklenemedi.")
            return
        if compression not in ("gz", "xz"):
            self.show_message_box("Hata", f"Geçersiz sıkıştırma türü: {compression}")
            return
        temp_export_dir = tempfile.mkdtemp(prefix="media_export_")
        manifest_file_name_prefix = os.path.splitext(os.path.basename(target_path))[0]
        manifest_file_name = manifest_file_name_prefix + "_manifest.txt"
        manifest_path = os.path.join(temp_export_dir, manifest_file_name)

        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Proje Kaydediliyor")
        progress_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        progress_dialog.setAttribute(Qt.WA_DeleteOnClose)
        progress_dialog.setStyleSheet("QDialog { background-color: #3f3f3f; border: 2px solid #4CAF50; border-radius: 8px; } QLabel { color: #ffffff; font-size: 14px; padding: 5px; } QProgressBar { border: 2px solid #555; border-radius: 5px; background-color: #2e2e2e; text-align: center; color: white; } QProgressBar::chunk { background-color: #4CAF50; border-radius: 4px; }")
        dialog_layout = QVBoxLayout(progress_dialog)
        dialog_layout.setContentsMargins(20, 20, 20, 20)
        export_label = QLabel(f"Kaydediliyor: {os.path.basename(target_path)} ({compression})")
        dialog_layout.addWidget(export_label)
        self.progress_bar = QProgressBar(progress_dialog)
        self.progress_bar.setRange(0, 100)
        dialog_layout.addWidget(self.progress_bar)
        self.time_estimate_label = QLabel("Segmentler işleniyor...")
        dialog_layout.addWidget(self.time_estimate_label)
        progress_dialog.show()
        QApplication.processEvents()

        try:
            with open(manifest_path, 'w') as f:
                for i, segment in enumerate(self.media_queue):
                    temp_segment_filename = os.path.basename(segment['path'])
                    f.write(f"{segment['type']},{temp_segment_filename},{segment['abbreviation']},{segment['original_ext']},{float(segment['duration']):.6f}\n")
                    shutil.copy2(segment['path'], os.path.join(temp_export_dir, temp_segment_filename))
                    self.progress_bar.setValue(int(((i + 1) / len(self.media_queue)) * 90))
                    QApplication.processEvents()

            def do_archive():
                if hasattr(self.media_engine, 'archive_segments_with_compression'):
                    return self.media_engine.archive_segments_with_compression(
                        target_path.encode('utf-8'), temp_export_dir.encode('utf-8'),
                        manifest_file_name.encode('utf-8'), compression.encode('utf-8'))
                return self.media_engine.archive_segments(
                    target_path.encode('utf-8'), temp_export_dir.encode('utf-8'), manifest_file_name.encode('utf-8'))
            archive_result = self._run_blocking(do_archive, "Arşiv oluşturuluyor...")
            if archive_result is None:
                archive_result = -1
            self.progress_bar.setValue(100)
            self.time_estimate_label.setText("Kayıt tamamlandı!")

            if archive_result == 0:
                self.current_project_path = target_path
                _fm.notify_saved(self)
            else:
                self.show_message_box("Hata", f"Proje kaydedilemedi. Kod: {archive_result}")
        except Exception as e:
            self.show_message_box("Hata", f"Kayıt sırasında hata: {e}")
        finally:
            if os.path.exists(temp_export_dir):
                shutil.rmtree(temp_export_dir)
            progress_dialog.close()

    def export_timeline_to_mkv(self):
        """Geriye dönük uyumluluk — sağ tık menüsü yeni format seçimini kullanır."""
        self._show_export_format_menu(self.export_btn.rect().bottomRight())

    def _create_audio_placeholder_image(self, output_path, width, height):
        image = QImage(width, height, QImage.Format_RGB32)
        image.fill(QColor("black"))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)
        font = QFont("Arial", max(50, int(height * 0.4)))
        painter.setFont(font)
        painter.setPen(QColor("#AAAAAA"))
        painter.drawText(image.rect(), Qt.AlignCenter, "♪")
        painter.end()
        image.save(output_path)

    def _run_blocking(self, func, label="İşleniyor..."):
        """func'ı ayrı iş parçacığında çalıştırır, bu sırada arayüz canlı kalır (modal ilerleme penceresi)."""
        holder = {}

        def target():
            try:
                holder['value'] = func()
            except Exception as e:
                holder['error'] = e

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        dialog = QProgressDialog(label, None, 0, 0, self)
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setCancelButton(None)
        dialog.setMinimumDuration(300)
        dialog.setWindowTitle("Lütfen bekleyin")
        while thread.is_alive():
            QApplication.processEvents(QEventLoop.AllEvents, 50)
            thread.join(0.02)
        dialog.close()
        if 'error' in holder:
            print(f"_run_blocking hatası: {holder['error']}")
            return None
        return holder.get('value')

    def _run_ffmpeg_blocking(self, args, label):
        """Kısa FFmpeg işleri: arayüz canlı kalır. Dönüş: True/False."""
        def work():
            r = subprocess.run([FFMPEG_PATH, "-hide_banner", "-v", "error", "-nostdin", "-y"] + args,
                               capture_output=True, text=True)
            if r.returncode != 0:
                print(f"FFmpeg hatası: {r.stderr[-800:]}")
            return r.returncode == 0
        return bool(self._run_blocking(work, label))

    def _extract_audio_from_video(self, video_path, output_wav_path):
        info = self._probe_media(video_path)
        if info is not None and not info['has_audio']:
            return False                         # sesi yok: filtrelenecek bir şey yok
        return self._run_ffmpeg_blocking(
            ["-i", video_path, "-map", "0:a:0", "-vn", "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "1", output_wav_path],
            "Videodan ses ayrılıyor...")

    def _replace_audio_in_video(self, video_path, audio_wav_path, output_video_path):
        # apad + -shortest: görüntü uzunluğu korunur (filtrelenmiş ses kısaysa sessizlikle tamamlanır)
        return self._run_ffmpeg_blocking(
            ["-i", video_path, "-i", audio_wav_path, "-map", "0:v:0", "-map", "1:a:0",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", "apad", "-shortest", output_video_path],
            "Filtrelenmiş ses videoya ekleniyor...")

    def _normalize_rotation(self, video_path, temp_dir):
        """Telefon videolarındaki döndürme bilgisini piksellere işler. Böylece oynatıcı ve export aynı yönü gösterir."""
        info = self._probe_media(video_path)
        if info is None or info['rotation'] == 0:
            return video_path
        out = os.path.join(temp_dir, "yon_duzeltilmis.mp4")
        ok = self._run_ffmpeg_blocking(
            ["-i", video_path, "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out],
            "Video yönü düzeltiliyor...")
        return out if ok and os.path.exists(out) and os.path.getsize(out) > 0 else video_path

    def _python_filter_wav(self, wav_path):
        """Core bağlantısı yoksa yedek: Python ses filtresi. Başarısızsa (ya da kütüphaneler yoksa) None."""
        if AUDIO_LIBS_MISSING:
            print("Python: ses filtre kütüphaneleri eksik; ses filtrelenmeden eklendi.")
            return None
        try:
            pd = QProgressDialog("Ses filtreleniyor...", None, 0, 100, self)
            pd.setWindowModality(Qt.WindowModal)
            pd.setCancelButton(None)
            pd.setMinimumDuration(0)
            pd.show()
            QApplication.processEvents()
            out = self._apply_python_audio_filter(wav_path, pd)
            pd.close()
            return out if (out and os.path.exists(out)) else None
        except Exception as e:
            print(f"Python filtre hatası: {e}")
            return None

    def _apply_filter_to_media(self, original_path, media_type, original_name, callback):
        """İçe aktarma / kayıt sonrası ortak işlem hattı:
        1) video yönü normalize edilir, 2) filtre butonu (I) aktifse SES filtrelenir (video görüntüsü aynen kalır)."""
        base_type = {'recorded_video': 'video', 'recorded_audio': 'audio'}.get(media_type, media_type)
        temp_dir = tempfile.mkdtemp(prefix="media_filter_")
        finished = {'done': False}

        def cleanup_temp():
            shutil.rmtree(temp_dir, ignore_errors=True)

        def finish(path):
            if finished['done']:
                return
            finished['done'] = True
            try:
                if callback:
                    callback(path, media_type, original_name)
            finally:
                cleanup_temp()

        work_path = original_path
        if base_type == 'video':
            work_path = self._normalize_rotation(original_path, temp_dir)

        if not self.noise_filter_enabled or media_type == 'media_archive' or base_type not in ('audio', 'video'):
            finish(work_path)
            return

        use_core = self.core_window_ref is not None and hasattr(self.core_window_ref, 'process_audio_with_filter')

        if base_type == 'audio':
            if use_core:
                def on_audio_filtered(success, output_path, message):
                    finish(output_path if (success and output_path and os.path.exists(output_path)) else work_path)
                started = self.core_window_ref.process_audio_with_filter(work_path, on_audio_filtered)
                if not started:
                    finish(work_path)
            else:
                out = self._python_filter_wav(work_path)
                finish(out or work_path)
            return

        # video
        extracted_audio = os.path.join(temp_dir, "extracted_audio.wav")
        if not self._extract_audio_from_video(work_path, extracted_audio):
            finish(work_path)
            return
        _, ext = os.path.splitext(work_path)
        ext = ext if ext else ".mp4"

        def on_filtered(filtered_audio_path):
            if filtered_audio_path and os.path.exists(filtered_audio_path):
                output_video = os.path.join(temp_dir, f"filtrelenmis{ext}")
                if self._replace_audio_in_video(work_path, filtered_audio_path, output_video) and os.path.exists(output_video):
                    finish(output_video)
                    return
            finish(work_path)

        if use_core:
            def on_video_audio_filtered(success, filtered_audio_path, message):
                on_filtered(filtered_audio_path if success else None)
            started = self.core_window_ref.process_audio_with_filter(extracted_audio, on_video_audio_filtered)
            if not started:
                finish(work_path)
        else:
            on_filtered(self._python_filter_wav(extracted_audio))

    def get_duration_from_path(self, path):
        """Süre (saniye); alınamazsa -1. (Eski QMediaPlayer yoklama döngüsü kaldırıldı: arayüzü kilitliyordu.)"""
        info = self._probe_media(path)
        if info and info['duration'] > 0:
            return info['duration']
        return -1

    # ------------------------------------------------------------------ kesme yardımcıları
    @staticmethod
    def _cut_output_ext(media_type, original_ext):
        """Kesilen parçaların uzantısı: kodlayıcı/kapsayıcı uyumlu olsun diye."""
        ext = (original_ext or "").lower()
        if media_type in ('video', 'recorded_video'):
            return ".mkv" if ext == ".mkv" else ".mp4"
        return ext if ext in (".wav", ".mp3", ".flac", ".ogg", ".aac", ".m4a", ".saund") else ".wav"

    def _cut_with_ui(self, input_path, cut_ms, out1, out2, media_type):
        """Kesme uzun sürebilir (yeniden kodlama): ayrı iş parçacığında, arayüz canlı."""
        def work():
            return self.media_engine.cut_media_segment(
                input_path.encode('utf-8'), int(cut_ms), out1.encode('utf-8'), out2.encode('utf-8'),
                media_type.encode('utf-8'))
        result = self._run_blocking(work, "Medya kesiliyor...")
        return -999 if result is None else int(result)

    def _discard_file(self, path):
        """Dosya geri-al (undo) için hemen silinmez; hiçbir durumda kullanılmayınca silinir."""
        if path:
            self._discarded_paths.add(path)

    def _gc_discarded(self):
        referenced = {s.get('path') for s in self.media_queue}
        for stack in (self._undo_stack, self._redo_stack):
            for st in stack:
                for s in st.get('media_queue', []) if isinstance(st, dict) else []:
                    referenced.add(s.get('path'))
        for p in list(self._discarded_paths):
            if p not in referenced:
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except OSError as e:
                    print(f"Dosya silinemedi: {e}")
                self._discarded_paths.discard(p)

    def select_media_files(self):
        all_video_formats = "*.mp4 *.avi *.mov *.mkv *.webm *.flv *.rec"
        all_audio_formats = "*.mp3 *.wav *.ogg *.flac *.aac *.m4a *.saund"
        custom_archive_formats = "*.media"
        filter_str = (f"Tüm Desteklenen Medya ({all_video_formats} {all_audio_formats} {custom_archive_formats});;"
                      f"Medya Arşivleri ({custom_archive_formats});;"
                      f"Video ({all_video_formats});;"
                      f"Ses ({all_audio_formats});;"
                      f"Tüm Dosyalar (*)")
        file_paths, _ = _fm.get_open_file_names(self, "Medya Dosyalarını Seç", DEFAULT_BASE_DIR, filter_str, editor="Media")
        if not file_paths:
            return

        total_files = len(file_paths)
        progress_dialog = QProgressDialog("İçe aktarılıyor ve filtreleniyor...", "İptal", 0, total_files, self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowTitle("İçe Aktarma")
        progress_dialog.setMinimumDuration(500)
        progress_dialog.show()
        QApplication.processEvents()

        self._import_queue = list(file_paths)
        self._import_after_index = None
        self._import_index = 0
        self._import_progress = progress_dialog
        self._import_progress.setValue(0)
        self._import_next()

    def _import_next(self):
        if self._import_index >= len(self._import_queue):
            self._import_progress.close()
            self._import_queue = None
            self._import_progress = None
            self.update_total_duration_label()
            if self.media_queue and self.current_media_index == -1:
                self.current_media_index = 0
                self.position = 0
                self.paused_position = 0
                self._set_media_to_player(self.current_media_index)
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_selected_segment(self.current_media_index)
            self.timeline.set_position(self.position)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            self.stop_media()
            self.is_sequence_play_active = False
            self._update_sequence_play_button_state()
            self._save_state()
            return

        original_path = self._import_queue[self._import_index]
        self._import_progress.setLabelText(f"İşleniyor {os.path.basename(original_path)}...")
        QApplication.processEvents()

        media_type = self.get_file_type(original_path)
        original_filename_no_ext = os.path.splitext(os.path.basename(original_path))[0]

        if media_type == 'media_archive':
            self.stop_media()
            self.media_queue.clear()
            self.current_media_index = -1
            self.position = 0
            self.paused_position = 0
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_selected_segment(self.current_media_index)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            self.update_total_duration_label()
            self._save_state()
            self._import_after_index = None
            self._process_media_archive(original_path)
            self._import_index += 1
            self._import_progress.setValue(self._import_index)
            QTimer.singleShot(10, self._import_next)
        elif media_type != 'unknown':
            def on_filtered(file_path, mtype, orig_name):
                if self.add_media_to_queue(file_path, mtype, orig_name, after_index=self._import_after_index):
                    self._import_after_index = self._last_added_index
                self._import_index += 1
                self._import_progress.setValue(self._import_index)
                QTimer.singleShot(10, self._import_next)
            self._apply_filter_to_media(original_path, media_type, original_filename_no_ext, on_filtered)
        else:
            self.show_message_box("Uyarı", f"Bilinmeyen dosya türü atlandı: {os.path.basename(original_path)}")
            self._import_index += 1
            self._import_progress.setValue(self._import_index)
            QTimer.singleShot(10, self._import_next)

    def load_file(self, file_path: str):
        if not file_path or not os.path.exists(file_path):
            self.show_message_box("Hata", "Geçersiz dosya yolu.")
            return
        media_type = self.get_file_type(file_path)
        original_filename_no_ext = os.path.splitext(os.path.basename(file_path))[0]

        if media_type == 'media_archive':
            self.stop_media()
            self.media_queue.clear()
            self.current_media_index = -1
            self.position = 0
            self.paused_position = 0
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_selected_segment(self.current_media_index)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            self.update_total_duration_label()
            self._save_state()
            if not self._process_media_archive(file_path):
                self.show_message_box("Hata", f"Medya arşivi yüklenemedi: {os.path.basename(file_path)}")
        elif media_type != 'unknown':
            def on_filtered(filtered_path, mtype, orig_name):
                self.add_media_to_queue(filtered_path, mtype, orig_name)
                if self.media_queue and self.current_media_index == -1:
                    self.current_media_index = 0
                    self.position = 0
                    self.paused_position = 0
                    self._set_media_to_player(self.current_media_index)
                self.timeline.set_media_segments(self.media_queue, self.current_media_index)
                self.timeline.set_selected_segment(self.current_media_index)
                self.timeline.set_position(self.position)
                self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
                self.update_total_duration_label()
                self.stop_media()
                self.is_sequence_play_active = False
                self._update_sequence_play_button_state()
                self._save_state()
            self._apply_filter_to_media(file_path, media_type, original_filename_no_ext, on_filtered)
        else:
            self.show_message_box("Uyarı", f"Bilinmeyen dosya türü: {os.path.basename(file_path)}")

    def _process_media_archive(self, archive_path: str) -> bool:
        if not self.media_engine:
            self.show_message_box("Hata", "Medya motoru yüklenemedi.")
            return False
        temp_extract_dir = tempfile.mkdtemp(prefix="media_archive_")
        try:
            extract_result = self.media_engine.extract_segments(
                archive_path.encode('utf-8'), temp_extract_dir.encode('utf-8'))
            if extract_result != 0:
                self.show_message_box("Hata", f"Medya arşivi çıkarılamadı. Kod: {extract_result}")
                return False
            manifest_file_name = os.path.splitext(os.path.basename(archive_path))[0] + "_manifest.txt"
            manifest_path = os.path.join(temp_extract_dir, manifest_file_name)
            if not os.path.exists(manifest_path):
                self.show_message_box("Hata", "Arşivde manifest dosyası bulunamadı.")
                return False
            segments_to_add = []
            with open(manifest_path, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) in (4, 5):
                        seg_type, seg_path, abbreviation, original_ext = parts[:4]
                        try:
                            stored_duration = float(parts[4]) if len(parts) == 5 else None
                        except ValueError:
                            stored_duration = None
                        full_seg_path = os.path.join(temp_extract_dir, os.path.basename(seg_path))
                        if not os.path.exists(full_seg_path): continue
                        segments_to_add.append({'path': full_seg_path, 'type': seg_type, 'stored_duration': stored_duration,
                                                'original_name_prefix': os.path.splitext(os.path.basename(full_seg_path))[0]})
            for seg_data in segments_to_add:
                duration = self.get_duration_from_path(seg_data['path'])
                if duration == -1: continue
                source_duration = duration
                stored = seg_data.get('stored_duration')
                if stored and 0.0 < stored < duration:
                    duration = stored                      # kaydedilmiş (kırpılmış) süre
                prefix_char = 's' if seg_data['type'] in ['audio', 'recorded_audio'] else 'v'
                existing_numbers = set()
                for segment in self.media_queue:
                    if segment['abbreviation'].startswith(prefix_char):
                        match = re.match(r'{}(\d+)(?:\.\d+)?$'.format(prefix_char), segment['abbreviation'])
                        if match: existing_numbers.add(int(match.group(1)))
                current_sequence_num = (max(existing_numbers) if existing_numbers else 0) + 1
                abbreviation = f"{prefix_char}{current_sequence_num}"
                formatted_duration_str = self.format_time(duration)
                original_ext_seg = os.path.splitext(seg_data['path'])[1].lower()
                new_filename = f"{abbreviation}_{formatted_duration_str}{original_ext_seg}"
                dest_path = os.path.join(self.media_save_dir, new_filename)
                try:
                    shutil.copy2(seg_data['path'], dest_path)
                    new_segment_data = {
                        'path': dest_path, 'type': seg_data['type'], 'duration': duration,
                        'abbreviation': abbreviation, 'original_name_prefix': seg_data['original_name_prefix'],
                        'formatted_duration': self.format_time_display(duration),
                        'formatted_duration_ms': self.format_time_display_with_ms(duration),
                        'original_ext': original_ext_seg, 'source_duration': source_duration,
                        'id': str(time.time()) + str(current_sequence_num),
                        'is_cut_point': False
                    }
                    self.media_queue.append(new_segment_data)
                except IOError:
                    self.show_message_box("Hata", f"Arşivden kopyalanamadı: {os.path.basename(seg_data['path'])}")
                    return False
            if self.media_queue:
                self.current_media_index = 0
                self.position = 0
                self.paused_position = 0
                self._set_media_to_player(self.current_media_index)
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_selected_segment(self.current_media_index)
            self.timeline.set_position(self.position)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            self.update_total_duration_label()
            self.current_project_path = archive_path
            print(f"Proje yüklendi: {self.current_project_path}")
            return True
        except Exception as e:
            self.show_message_box("Hata", f"Medya arşivi işlenirken hata: {e}")
            return False
        finally:
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)

    def update_total_duration_label(self):
        self.total_time_label.setText(self.format_time_display_with_ms(self._get_total_overall_duration()))

    def delete_selected_media(self):
        if self.timeline.selected_segment_index == -1:
            self.show_message_box("Uyarı", "Lütfen silmek için bir medya seçin!")
            return
        index_to_delete = self.timeline.selected_segment_index
        if not (0 <= index_to_delete < len(self.media_queue)):
            self.timeline.set_selected_segment(-1); return
        segment_to_delete = self.media_queue[index_to_delete]
        deleted_file_path = segment_to_delete['path']
        self.stop_media()
        self.is_sequence_play_active = False
        self._update_sequence_play_button_state()
        self.media_queue.pop(index_to_delete)
        if not self.media_queue:
            self.current_media_index = -1; self.position = 0; self.paused_position = 0
        elif index_to_delete == self.current_media_index:
            if self.current_media_index < len(self.media_queue):
                self.position = 0; self.paused_position = 0
                self._set_media_to_player(self.current_media_index)
            else:
                self.current_media_index = -1; self.position = 0; self.paused_position = 0
        elif index_to_delete < self.current_media_index:
            self.current_media_index -= 1
        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.timeline.set_selected_segment(self.current_media_index)
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        self.update_total_duration_label()
        self._discard_file(deleted_file_path)           # geri al (undo) için hemen silinmez
        self._save_state()

    def cut_media(self):
        if not self.media_queue:
            self.show_message_box("Uyarı", "Kesmek için önce medya yükleyin!"); return
        if self.current_media_index == -1:
            self.show_message_box("Uyarı", "Aktif segment yok."); return
        if not self.media_engine:
            self.show_message_box("Hata", "Medya motoru yüklenemedi."); return
        if self.is_playing:
            self.show_message_box("Uyarı", "Kesme için oynatmayı durdurun!"); return
        if self.is_sequence_play_active:
            self.is_sequence_play_active = False
            self._update_sequence_play_button_state()
            self.show_message_box("Bilgi", "Sıralı oynatma modu devre dışı bırakıldı.")

        relative_cut_point_sec = self.position
        relative_cut_point_ms = int(relative_cut_point_sec * 1000)
        original_segment = self.media_queue[self.current_media_index]
        original_file_path = original_segment['path']
        original_source_ext = self._cut_output_ext(original_segment['type'], original_segment.get('original_ext', '.mp4'))
        original_duration_ms = int(original_segment['duration'] * 1000)

        if relative_cut_point_sec < self.MIN_SEGMENT_DURATION_SEC or \
           (original_segment['duration'] - relative_cut_point_sec) < self.MIN_SEGMENT_DURATION_SEC:
            self.show_message_box("Uyarı", "Kesme iptal: Parçalardan biri 1.1sn'den kısa.")
            return
        EPSILON_CUT = 10
        if abs(relative_cut_point_ms) < EPSILON_CUT: relative_cut_point_ms = 0
        elif abs(relative_cut_point_ms - original_duration_ms) < EPSILON_CUT: relative_cut_point_ms = original_duration_ms
        if relative_cut_point_ms in (0, original_duration_ms): return

        base_abbreviation = original_segment['abbreviation']
        base_prefix = base_abbreviation[0]
        base_number = int(re.search(r'\d+', base_abbreviation).group())
        existing_sub = []
        for s in self.media_queue:
            m = re.match(r'{}{}\.(\d+)'.format(base_prefix, base_number), s['abbreviation'])
            if m: existing_sub.append(int(m.group(1)))
        start_sub = (max(existing_sub) if existing_sub else 0) + 1
        new_abbr_1 = f"{base_prefix}{base_number}.{start_sub}"
        new_abbr_2 = f"{base_prefix}{base_number}.{start_sub + 1}"
        dur1_str = self.format_time(relative_cut_point_ms / 1000.0)
        dur2_str = self.format_time((original_duration_ms - relative_cut_point_ms) / 1000.0)
        out1 = os.path.join(self.media_save_dir, f"{new_abbr_1}_{dur1_str}{original_source_ext}")
        out2 = os.path.join(self.media_save_dir, f"{new_abbr_2}_{dur2_str}{original_source_ext}")

        cut_result = self._cut_with_ui(original_file_path, relative_cut_point_ms, out1, out2, original_segment['type'])
        if cut_result != 0:
            self.show_message_box("Hata", f"Kesme başarısız. Kod: {cut_result}"); return

        d1 = self.media_engine.get_media_duration_ms(out1.encode('utf-8')) if os.path.exists(out1) else -1
        d2 = self.media_engine.get_media_duration_ms(out2.encode('utf-8')) if os.path.exists(out2) else -1
        if d1 == -1 or d2 == -1:
            self.show_message_box("Hata", "Yeni segment süreleri alınamadı; orijinal medya korunuyor.")
            if os.path.exists(out1): os.remove(out1)
            if os.path.exists(out2): os.remove(out2)
            return
        dur1_sec = min(d1 / 1000.0, relative_cut_point_ms / 1000.0)
        dur2_sec = min(d2 / 1000.0, max(0.0, (original_duration_ms - relative_cut_point_ms) / 1000.0))
        if dur1_sec < self.MIN_SEGMENT_DURATION_SEC or dur2_sec < self.MIN_SEGMENT_DURATION_SEC:
            self.show_message_box("Uyarı", "Kesme sonucu parçalardan biri 1.1sn'den kısa olduğu için işlem geri alındı.")
            if os.path.exists(out1): os.remove(out1)
            if os.path.exists(out2): os.remove(out2)
            return
        add1 = dur1_sec > 0.001; add2 = dur2_sec > 0.001

        self._discard_file(original_file_path)          # geri al (undo) için hemen silinmez
        self.media_queue.pop(self.current_media_index)
        if not add1 and not add2:
            if os.path.exists(out1): os.remove(out1)
            if os.path.exists(out2): os.remove(out2)
            return
        if add2:
            self.media_queue.insert(self.current_media_index, {
                'path': out2, 'type': original_segment['type'], 'duration': dur2_sec,
                'abbreviation': new_abbr_2, 'original_name_prefix': original_segment['original_name_prefix'],
                'formatted_duration': self.format_time_display(dur2_sec),
                'formatted_duration_ms': self.format_time_display_with_ms(dur2_sec),
                'original_ext': original_source_ext,
                'id': str(time.time()) + new_abbr_2, 'is_cut_point': False
            })
        else:
            if os.path.exists(out2): os.remove(out2)
        if add1:
            self.media_queue.insert(self.current_media_index, {
                'path': out1, 'type': original_segment['type'], 'duration': dur1_sec,
                'abbreviation': new_abbr_1, 'original_name_prefix': original_segment['original_name_prefix'],
                'formatted_duration': self.format_time_display(dur1_sec),
                'formatted_duration_ms': self.format_time_display_with_ms(dur1_sec),
                'original_ext': original_source_ext,
                'id': str(time.time()) + new_abbr_1, 'is_cut_point': True
            })
        else:
            if os.path.exists(out1): os.remove(out1)

        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.timeline.set_selected_segment(self.current_media_index)
        self.position = relative_cut_point_sec
        self.paused_position = int(relative_cut_point_sec * 1000)
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        if self.current_media_index != -1:
            self._set_media_to_player(self.current_media_index)
            self._seek(self.paused_position)
        self.update_total_duration_label()
        self._save_state()

    def _on_timeline_segment_selected(self, index):
        if not self.media_queue or index < 0 or index >= len(self.media_queue):
            self.current_media_index = -1
            self.timeline.set_selected_segment(-1)
            self.stop_media()
            self.is_sequence_play_active = False
            self._update_sequence_play_button_state()
            return
        if index == self.current_media_index:
            self.timeline.set_selected_segment(index)
            self.timeline.set_position(self.position)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            return
        self.stop_media()
        self.is_sequence_play_active = False
        self._update_sequence_play_button_state()
        self.current_media_index = index
        self.position = 0
        self.paused_position = 0
        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.timeline.set_selected_segment(self.current_media_index)
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        self._set_media_to_player(self.current_media_index)
        self._save_state()

    def _perform_play(self):
        if self.current_media_index == -1:
            self.show_message_box("Hata", "Oynatılacak segment yok.")
            return
        position_ms = max(0, int(self.position * 1000))
        if self._media_ready:
            self.player.setPosition(position_ms)
            self.player.play()
        else:
            self._pending_seek_ms = position_ms
            self._pending_play = True

    def toggle_play_pause(self):
        if not self.media_queue:
            self.show_message_box("Uyarı", "Önce medya yükleyin!"); return
        if self.is_recording and (self.is_camera_mode_selected or self.is_audio_mode_selected):
            self.show_message_box("Uyarı", "Kayıt aktifken medya oynatılamaz."); return
        if self.player.state() == QMediaPlayer.PlayingState:
            self.paused_position = self.player.position() / 1000.0
            self.player.pause()
            return
        if self.current_media_index == -1:
            self.current_media_index = 0
            self.position = 0.0
            self.paused_position = 0.0
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_selected_segment(self.current_media_index)
            self._set_media_to_player(self.current_media_index)
        elif (self._loaded_index != self.current_media_index or
              self.player.mediaStatus() in (QMediaPlayer.NoMedia, QMediaPlayer.InvalidMedia)):
            self._set_media_to_player(self.current_media_index)
        current_segment = self.media_queue[self.current_media_index]
        max_duration = max(0.0, float(current_segment.get('duration', 0.0)))
        start = max(0.0, min(float(self.paused_position), max_duration))
        if start >= max_duration - 0.05:
            start = 0.0                              # segment sonundaysa baştan oynat
        self.position = start
        self.paused_position = start
        self._segment_end_handled = False
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        self._perform_play()

    def _toggle_sequence_play_mode(self):
        if not self.media_queue:
            self.show_message_box("Uyarı", "Sıralı oynatılacak medya yok."); return
        if self.is_recording:
            self.show_message_box("Uyarı", "Kayıt aktifken mod değiştirilemez."); return
        self.is_sequence_play_active = not self.is_sequence_play_active
        self._update_sequence_play_button_state()

    def _advance_to_next_segment(self):
        if not self.media_queue:
            return
        was_sequence = self.is_sequence_play_active
        self.stop_media()
        next_index = self.current_media_index + 1
        if next_index < len(self.media_queue):
            self.current_media_index = next_index
            self.position = 0.0
            self.paused_position = 0.0
            self._set_media_to_player(self.current_media_index, play=was_sequence)
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_selected_segment(self.current_media_index)
            self.timeline.set_position(self.position)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            if not was_sequence:
                self._save_state()
        else:
            self.current_media_index = -1
            self.position = 0.0
            self.paused_position = 0.0
            self._set_media_to_player(-1)
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_selected_segment(self.current_media_index)
            self.timeline.set_position(self.position)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            self.is_sequence_play_active = False
            self._update_sequence_play_button_state()

    def current_player(self): return self.player

    def stop_media(self):
        self.player.stop()
        self.paused_position = self.position
        self.video_output_widget.hide()
        self.audio_icon_label.hide()
        self.camera_preview_label.hide()
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))

    def _set_media_to_player(self, index, play=False, start_ms=None, force=False):
        """Segmenti oynatıcıya yükler. Konum/oynatma isteği (play, start_ms) yükleme bitince uygulanır.
        Aynı dosya zaten yüklüyse yeniden yüklenmez; farklı dosyada taze oynatıcı kullanılır."""
        valid = 0 <= index < len(self.media_queue)
        info = self.media_queue[index] if valid else None
        media_type = info['type'] if info else None
        if valid and media_type == 'media_archive':
            self.video_output_widget.hide()
            self.camera_preview_label.hide()
            self.audio_icon_label.hide()
            self._loaded_index = -1
            self._loaded_path = None
            self._media_ready = False
            self.show_message_box("Bilgi", ".media arşivi doğrudan oynatılamaz.")
            return
        if valid and media_type in ('video', 'recorded_video'):
            self.audio_icon_label.hide()
            self.camera_preview_label.hide()
            self.video_output_widget.show()
        elif valid and media_type in ('audio', 'recorded_audio'):
            self.video_output_widget.hide()
            self.camera_preview_label.hide()
            self.audio_icon_label.show()
        else:
            valid = False

        if not valid:
            self._pending_play = False
            self._pending_seek_ms = None
            self._segment_end_handled = False
            self._media_ready = False
            self._loaded_index = -1
            self._loaded_path = None
            self.video_widget.clear_frame()
            self._recycle_player()
            return

        path = info['path']
        self._segment_end_handled = False
        if (not force and index == self._loaded_index and path == self._loaded_path and self._media_ready and
                self.player.mediaStatus() not in (QMediaPlayer.InvalidMedia, QMediaPlayer.NoMedia)):
            # Aynı dosya hazır: yeniden yükleme yok
            if start_ms is not None:
                self.player.setPosition(int(start_ms))
            if play:
                self.player.play()
            return

        self._recycle_player()
        self._media_ready = False
        self._pending_play = bool(play)
        self._pending_seek_ms = start_ms
        self._loaded_index = index
        self._loaded_path = path
        self.video_widget.clear_frame()               # önceki segmentin karesi/oranı ekranda kalmasın
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
        try:
            self.player.setPlaybackRate(float(self.playback_speed_box.currentText()))
        except ValueError:
            self.player.setPlaybackRate(1.0)

    def update_position(self):
        if self.current_media_index == -1 or not (0 <= self.current_media_index < len(self.media_queue)):
            return
        if self.player.duration() <= 0:
            return
        current_player_time_ms = self.player.position()
        if current_player_time_ms == -1:
            return
        try:
            segment_duration = max(0.0, float(self.media_queue[self.current_media_index].get('duration', 0.0)))
        except (TypeError, ValueError):
            segment_duration = 0.0
        self.position = max(0.0, min(current_player_time_ms / 1000.0, segment_duration))
        self.paused_position = self.position
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        # Kırpılmış (kısaltılmış) segmentler dosya bitmeden bitmelidir
        if (self.player.state() == QMediaPlayer.PlayingState and segment_duration > 0.0 and
                current_player_time_ms / 1000.0 >= segment_duration - 0.03):
            self._on_segment_end()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        seek_interval_ms = self.seek_interval_ms
        if self.current_media_index == -1: return
        current_segment = self.media_queue[self.current_media_index]
        current_position_in_segment_ms = int(self.position * 1000)
        new_position_in_segment_ms = current_position_in_segment_ms + (seek_interval_ms if delta > 0 else -seek_interval_ms)
        new_position_in_segment_ms = max(0, min(new_position_in_segment_ms, int(current_segment['duration'] * 1000)))
        self.position = new_position_in_segment_ms / 1000.0
        self.paused_position = new_position_in_segment_ms / 1000.0
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        if self.player.state() == QMediaPlayer.PlayingState:
            self._seek(int(new_position_in_segment_ms))
        else:
            self._set_media_to_player(self.current_media_index)
            self._seek(int(new_position_in_segment_ms))
        QApplication.processEvents()

    def quick_save_media(self):
        if not self.media_queue:
            self.show_message_box("Uyarı", "Kaydedilecek medya yok."); return
        if self.current_project_path:
            self._save_project_internal(self.current_project_path, "gz")
        else:
            self._on_export_left_click()

    def clear_media_folders(self):
        reply = QMessageBox.question(self, 'Temizleme Onayı',
                                     "medya_cut klasörünü ve zaman çizelgesini sıfırlamak istiyor musunuz?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if os.path.exists(self.media_save_dir):
                    for filename in os.listdir(self.media_save_dir):
                        fp = os.path.join(self.media_save_dir, filename)
                        if os.path.isfile(fp) or os.path.islink(fp): os.unlink(fp)
                        elif os.path.isdir(fp): shutil.rmtree(fp)
                self.stop_media()
                self.player.setMedia(QMediaContent())
                self.media_queue.clear()
                self.current_media_index = -1
                self.position = 0
                self.paused_position = 0
                self.is_sequence_play_active = False
                self.current_project_path = None
                self.timeline.set_media_segments(self.media_queue, self.current_media_index)
                self.timeline.set_selected_segment(self.current_media_index)
                self.timeline.set_position(self.position)
                self.current_time_label.setText(self.format_time_display_with_ms(0))
                self.update_total_duration_label()
                self._update_sequence_play_button_state()
                self._undo_stack.clear(); self._redo_stack.clear()
                self._save_state(); self._update_undo_redo_buttons()
            except Exception as e:
                print(f"Temizleme hatası: {e}")
                self.show_message_box("Hata", f"Temizleme sırasında hata: {e}")

    def closeEvent(self, event):
        if getattr(self, 'is_recording', False):
            msg = QMessageBox(self)
            msg.setWindowTitle("Kayıt Devam Ediyor")
            msg.setText("Kaydınız devam ediyor.\nPencereyi kapatmak istiyor musunuz?\n(Kayıt iptal edilecektir)")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            msg.setStyleSheet("""
                QMessageBox { background-color: #1e1e1e; color: white; }
                QLabel { color: white; font-size: 14px; padding: 10px; }
                QPushButton { padding: 8px 20px; font-weight: bold; border-radius: 4px; }
                QPushButton[text="Yes"] { background-color: #c42b1c; color: white; }
                QPushButton[text="No"] { background-color: #333333; color: white; }
            """)
            if msg.exec_() == QMessageBox.Yes:
                self._stop_all_recording_processes()
                self._update_record_button_state()
            else:
                event.ignore(); return
        if self._export_task is not None and self._export_task.is_running():
            reply = QMessageBox.question(self, 'Dışa Aktarma Sürüyor',
                                         "Dışa aktarma devam ediyor. İptal edip kapatılsın mı?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                event.ignore(); return
            self._export_task.cancel()
        self._stop_all_recording_processes()
        if self.player.state() != QMediaPlayer.StoppedState:
            self.player.stop()
        self.player.setMedia(QMediaContent())
        if self.media_engine and self._pa_inited:
            try:
                self.media_engine.terminate_audio_engine()
                self._pa_inited = False
            except Exception as e:
                print(f"terminate_audio_engine hatası: {e}")
        if os.path.exists(self.media_save_dir) and len(os.listdir(self.media_save_dir)) > 0:
            reply = QMessageBox.question(self, 'Çıkış Onayı',
                                         f"Medya klasörünü silmek ister misiniz?\n{self.media_save_dir}",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    shutil.rmtree(self.media_save_dir)
                except OSError as e:
                    print(f"Medya klasörü silme hatası: {e}")
        event.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.active_message_box and self.active_message_box.isVisible():
                self.active_message_box.done(QMessageBox.Yes)
                self.active_message_box = None
                event.accept(); return
        if event.key() == Qt.Key_F:
            self.toggle_fullscreen(); event.accept(); return
        if self.current_media_index != -1:
            current_segment = self.media_queue[self.current_media_index]
            cur_ms = int(self.position * 1000)
            rate = self.player.playbackRate()
            step = self.frame_seek_step_sec / rate if rate != 0 else self.frame_seek_step_sec
            new_ms = cur_ms
            if event.key() == Qt.Key_Left:
                new_ms = max(0, cur_ms - int(step * 1000))
            elif event.key() == Qt.Key_Right:
                new_ms = min(int(current_segment['duration'] * 1000), cur_ms + int(step * 1000))
            if new_ms != cur_ms:
                self.position = new_ms / 1000.0
                self.paused_position = self.position
                self._seek(int(self.position * 1000))
                QApplication.processEvents()
                self.timeline.set_position(self.position)
                self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
                event.accept(); return
        if event.key() == Qt.Key_Space:
            if self.is_playing: self.toggle_play_pause()
            else: self._advance_to_next_segment()
        elif event.key() == Qt.Key_L and event.modifiers() == Qt.ControlModifier:
            if self.current_media_index != -1:
                self.stop_media()
                self.position = 0
                self.paused_position = 0
                self._set_media_to_player(self.current_media_index)
                self._seek(0)
                self.timeline.set_position(self.position)
                self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        elif event.key() == Qt.Key_Delete:
            self.delete_selected_media()
        elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier:
            self.undo()
        elif event.key() == Qt.Key_Z and event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier):
            self.redo()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        super().keyReleaseEvent(event)

    def triggerCoreSwitcher(self):
        if getattr(self, 'is_recording', False):
            msg = QMessageBox(self)
            msg.setWindowTitle("Kayıt Devam Ediyor")
            msg.setText("Kaydınız devam ediyor.\nEditörü değiştirmek istiyor musunuz?")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            msg.setStyleSheet("""
                QMessageBox { background-color: #1e1e1e; color: white; }
                QLabel { color: white; font-size: 14px; padding: 10px; }
                QPushButton { padding: 8px 20px; font-weight: bold; border-radius: 4px; }
                QPushButton[text="Yes"] { background-color: #c42b1c; color: white; }
                QPushButton[text="No"] { background-color: #333333; color: white; }
            """)
            if msg.exec_() == QMessageBox.Yes:
                self._stop_all_recording_processes()
                self.is_recording = False
                self.is_audio_mode_selected = False
                self.is_camera_mode_selected = False
                if hasattr(self, 'audio_mode_btn'): self.audio_mode_btn.setText("Sound")
                self._update_record_button_state()
            else:
                return
        main_window = self.window()
        if hasattr(main_window, 'showSwitcher'):
            main_window.showSwitcher()

    def show_message_box(self, title, message):
        msg = QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Information)
        msg.setStyleSheet("QMessageBox { background-color: #282c34; color: white; font-size: 14px; } QLabel { color: white; } QPushButton { background-color: #222; color: white; border: 1px solid #555; border-radius: 4px; padding: 5px 15px; } QPushButton:hover { background-color: #555; }")
        self.active_message_box = msg
        msg.exec_()
        self.active_message_box = None

    @staticmethod
    def format_time(total_seconds):
        total_ms = int(total_seconds * 1000)
        h = total_ms // 3600000; total_ms %= 3600000
        m = total_ms // 60000; total_ms %= 60000
        s = total_ms // 1000; ms = total_ms % 1000
        return f"{h:02d}{m:02d}{s:02d}_{ms:03d}"

    @staticmethod
    def format_time_display(total_seconds):
        total_ms = int(total_seconds * 1000)
        h = total_ms // 3600000; total_ms %= 3600000
        m = total_ms // 60000; total_ms %= 60000
        s = total_ms // 1000
        return f"{h:02d}:{m:02d}:{s:02d}"

    @staticmethod
    def format_time_display_with_ms(total_seconds):
        try:
            total_seconds = float(total_seconds)
        except (TypeError, ValueError):
            total_seconds = 0.0
        if not math.isfinite(total_seconds) or total_seconds < 0.0:
            total_seconds = 0.0
        total_ms = int(round(total_seconds * 1000.0))
        h = total_ms // 3600000; total_ms %= 3600000
        m = total_ms // 60000; total_ms %= 60000
        s = total_ms // 1000
        ms = total_ms % 1000
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

    def get_file_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.rec']: return 'video'
        elif ext in ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.saund']: return 'audio'
        elif ext == '.media':
            try:
                with open(path, 'rb') as f:
                    header = f.read(263)
                    if len(header) >= 2 and header[0] == 0x1f and header[1] == 0x8b: return 'media_archive'
                    if len(header) >= 6 and header[0] == 0xFD and header[1] == 0x37 and header[2] == 0x7A and header[3] == 0x58 and header[4] == 0x5A: return 'media_archive'
            except Exception as e:
                print(f".media header hatası: {e}")
            return 'unknown'
        return 'unknown'

    def add_media_to_queue(self, path, media_type, original_name=None, after_index=None):
        duration = self.get_duration_from_path(path)
        if not math.isfinite(duration) or duration <= 0.0:
            self.show_message_box("Hata", f"'{os.path.basename(path)}' süresi alınamadı.")
            return False
        prefix_char = ''
        if media_type in ('audio', 'recorded_audio'): prefix_char = 's'
        elif media_type in ('video', 'recorded_video'): prefix_char = 'v'
        elif media_type == 'media_archive': prefix_char = 'm'
        else:
            self.show_message_box("Hata", f"Bilinmeyen tür: '{os.path.basename(path)}'."); return False
        existing_numbers = set()
        for segment in self.media_queue:
            if segment['abbreviation'].startswith(prefix_char):
                m = re.match(r'{}(\d+)(?:\.\d+)?$'.format(prefix_char), segment['abbreviation'])
                if m: existing_numbers.add(int(m.group(1)))
        cur_seq = (max(existing_numbers) if existing_numbers else 0) + 1
        abbreviation = f"{prefix_char}{cur_seq}"
        formatted_dur_str = self.format_time(duration)
        original_ext = os.path.splitext(path)[1].lower()
        new_filename = f"{abbreviation}_{formatted_dur_str}{original_ext}"
        dest_path = os.path.join(self.media_save_dir, new_filename)
        try:
            shutil.copy2(path, dest_path)
            new_segment_data = {
                'path': dest_path, 'type': media_type, 'duration': duration,
                'abbreviation': abbreviation, 'original_name_prefix': original_name,
                'formatted_duration': self.format_time_display(duration),
                'formatted_duration_ms': self.format_time_display_with_ms(duration),
                'original_ext': original_ext, 'id': str(time.time()) + str(cur_seq),
                'is_cut_point': False
            }
            self.stop_media()
            self.is_sequence_play_active = False
            self._update_sequence_play_button_state()
            if after_index is not None and 0 <= after_index < len(self.media_queue):
                # Toplu içe aktarma: önceki eklenenin hemen arkasına (dosya sırası korunur)
                self.media_queue.insert(after_index + 1, new_segment_data)
                self.current_media_index = after_index + 1
                self.position = 0.0
                self.paused_position = 0.0
            elif self.current_media_index == -1 or not self.media_queue:
                self.media_queue.append(new_segment_data)
                self.current_media_index = len(self.media_queue) - 1
            else:
                current_segment = self.media_queue[self.current_media_index]
                EPS = 0.05
                if self.position < EPS:
                    self.media_queue.insert(self.current_media_index, new_segment_data)
                    self.current_media_index += 1
                elif self.position >= current_segment['duration'] - EPS:
                    self.media_queue.insert(self.current_media_index + 1, new_segment_data)
                    self.current_media_index += 1
                else:
                    if self.position < self.MIN_SEGMENT_DURATION_SEC or \
                       (current_segment['duration'] - self.position) < self.MIN_SEGMENT_DURATION_SEC:
                        self.media_queue.insert(self.current_media_index, new_segment_data)
                        self.current_media_index += 1
                        self.position = 0.0
                        self.paused_position = 0.0
                        self.show_message_box("Bilgi", "Ses dosyası mevcut segmentin önüne eklendi.")
                    else:
                        orig_idx = self.current_media_index
                        cut_point = self.position
                        temp_data = new_segment_data
                        p1, p2 = self._perform_cut_at_position(orig_idx, cut_point)
                        if p1 or p2:
                            self.media_queue.insert(self.current_media_index + 1, temp_data)
                            self.current_media_index += 1
                        else:
                            self.media_queue.insert(self.current_media_index, new_segment_data)
                            self.current_media_index += 1
                            self.position = 0.0
                            self.paused_position = 0.0
                            self.show_message_box("Uyarı", "Otomatik kesme başarısız.")
            self._last_added_index = next((i for i, s in enumerate(self.media_queue) if s is new_segment_data), -1)
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_position(self.position)
            self.timeline.set_selected_segment(self.current_media_index)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            self.update_total_duration_label()
            self._save_state()
            if self.current_media_index != -1:
                self._set_media_to_player(self.current_media_index)
                self._seek(int(self.position * 1000))
            return True
        except IOError:
            self.show_message_box("Hata", f"Dosya kopyalanamadı: {os.path.basename(path)}")
            return False

    def _perform_cut_at_position(self, segment_index_to_cut: int, cut_point_sec: float):
        if not self.media_engine: return None, None
        if segment_index_to_cut < 0 or segment_index_to_cut >= len(self.media_queue): return None, None
        original_segment = self.media_queue[segment_index_to_cut]
        original_file_path = original_segment['path']
        original_source_ext = self._cut_output_ext(original_segment['type'], original_segment.get('original_ext', '.mp4'))
        original_duration_ms = int(original_segment['duration'] * 1000)
        relative_cut_point_ms = int(cut_point_sec * 1000)
        EPSILON_CUT = 10
        if abs(relative_cut_point_ms) < EPSILON_CUT or abs(relative_cut_point_ms - original_duration_ms) < EPSILON_CUT:
            return None, None
        base_abbreviation = original_segment['abbreviation']
        base_prefix = base_abbreviation[0]
        base_number = int(re.search(r'\d+', base_abbreviation).group())
        existing_sub = []
        for s in self.media_queue:
            m = re.match(r'{}{}\.(\d+)'.format(base_prefix, base_number), s['abbreviation'])
            if m: existing_sub.append(int(m.group(1)))
        start_sub = (max(existing_sub) if existing_sub else 0) + 1
        new_abbr_1 = f"{base_prefix}{base_number}.{start_sub}"
        new_abbr_2 = f"{base_prefix}{base_number}.{start_sub + 1}"
        dur1_str = self.format_time(relative_cut_point_ms / 1000.0)
        dur2_str = self.format_time((original_duration_ms - relative_cut_point_ms) / 1000.0)
        out1 = os.path.join(self.media_save_dir, f"{new_abbr_1}_{dur1_str}{original_source_ext}")
        out2 = os.path.join(self.media_save_dir, f"{new_abbr_2}_{dur2_str}{original_source_ext}")
        cut_result = self._cut_with_ui(original_file_path, relative_cut_point_ms, out1, out2, original_segment['type'])
        if cut_result != 0: return None, None
        d1 = self.media_engine.get_media_duration_ms(out1.encode('utf-8')) if os.path.exists(out1) else -1
        d2 = self.media_engine.get_media_duration_ms(out2.encode('utf-8')) if os.path.exists(out2) else -1
        if d1 == -1 or d2 == -1:
            if os.path.exists(out1): os.remove(out1)
            if os.path.exists(out2): os.remove(out2)
            return None, None
        dur1_sec = min(d1 / 1000.0, relative_cut_point_ms / 1000.0)
        dur2_sec = min(d2 / 1000.0, max(0.0, (original_duration_ms - relative_cut_point_ms) / 1000.0))
        if dur1_sec < self.MIN_SEGMENT_DURATION_SEC or dur2_sec < self.MIN_SEGMENT_DURATION_SEC:
            if os.path.exists(out1): os.remove(out1)
            if os.path.exists(out2): os.remove(out2)
            return None, None
        self._discard_file(original_file_path)          # geri al (undo) için hemen silinmez
        self.media_queue.pop(segment_index_to_cut)
        add1 = dur1_sec > 0.001; add2 = dur2_sec > 0.001
        p1 = p2 = None
        if add1:
            p1 = {'path': out1, 'type': original_segment['type'], 'duration': dur1_sec,
                  'abbreviation': new_abbr_1, 'original_name_prefix': original_segment['original_name_prefix'],
                  'formatted_duration': self.format_time_display(dur1_sec),
                  'formatted_duration_ms': self.format_time_display_with_ms(dur1_sec),
                  'original_ext': original_source_ext,
                  'id': str(time.time()) + new_abbr_1, 'is_cut_point': True}
            self.media_queue.insert(segment_index_to_cut, p1)
            self.current_media_index = segment_index_to_cut
        else:
            if os.path.exists(out1): os.remove(out1)
        if add2:
            p2 = {'path': out2, 'type': original_segment['type'], 'duration': dur2_sec,
                  'abbreviation': new_abbr_2, 'original_name_prefix': original_segment['original_name_prefix'],
                  'formatted_duration': self.format_time_display(dur2_sec),
                  'formatted_duration_ms': self.format_time_display_with_ms(dur2_sec),
                  'original_ext': original_source_ext,
                  'id': str(time.time()) + new_abbr_2, 'is_cut_point': False}
            if p1: self.media_queue.insert(segment_index_to_cut + 1, p2)
            else:
                self.media_queue.insert(segment_index_to_cut, p2)
                self.current_media_index = segment_index_to_cut
        else:
            if os.path.exists(out2): os.remove(out2)
        if not p1 and not p2:
            if segment_index_to_cut < len(self.media_queue):
                self.current_media_index = segment_index_to_cut
            elif self.media_queue:
                self.current_media_index = len(self.media_queue) - 1
            else:
                self.current_media_index = -1
            return None, None
        self.position = 0.0; self.paused_position = 0.0
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        self.update_total_duration_label()
        return p1, p2

    def handle_move_segment_request(self, index: int, direction: int):
        if not self.media_queue or index < 0 or index >= len(self.media_queue): return
        current_index = index
        target_index = current_index + direction
        if not (0 <= target_index < len(self.media_queue)): return
        self.stop_media()
        self.is_sequence_play_active = False
        self._update_sequence_play_button_state()
        segment_to_move = self.media_queue.pop(current_index)
        self.media_queue.insert(target_index, segment_to_move)
        if current_index == self.current_media_index:
            self.current_media_index = target_index
        elif current_index < self.current_media_index and target_index >= self.current_media_index:
            self.current_media_index -= 1
        elif current_index > self.current_media_index and target_index <= self.current_media_index:
            self.current_media_index += 1
        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.timeline.set_selected_segment(target_index)
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        if self.current_media_index != -1:
            self._set_media_to_player(self.current_media_index)
            self._seek(int(self.position * 1000))
        self._save_state()

    def handle_segment_resize_request(self, index: int, delta_ms: int, is_expanding: bool):
        if not self.media_queue or index < 0 or index >= len(self.media_queue): return
        segment = self.media_queue[index]
        original_duration_ms = int(segment['duration'] * 1000)
        source_ms = int(segment.setdefault('source_duration', segment['duration']) * 1000)
        max_ms = max(original_duration_ms, source_ms)
        new_duration_ms = max(int(self.MIN_SEGMENT_DURATION_SEC * 1000), min(max_ms, original_duration_ms + int(delta_ms)))
        if new_duration_ms == original_duration_ms: return
        segment['duration'] = new_duration_ms / 1000.0
        segment['formatted_duration'] = self.format_time_display_with_ms(segment['duration'])
        segment['formatted_duration_ms'] = self.format_time_display_with_ms(segment['duration'])
        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.update_total_duration_label()
        self._save_state()

    def _save_state(self):
        state = {'media_queue': copy.deepcopy(self.media_queue),
                 'current_media_index': self.current_media_index,
                 'position': self.position, 'paused_position': self.paused_position}
        self._undo_stack.append(state)
        if len(self._undo_stack) > self._max_undo_states:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._update_undo_redo_buttons()
        self._gc_discarded()

    def _restore_state(self, state):
        self.stop_media()
        self.is_sequence_play_active = False
        self._update_sequence_play_button_state()
        self.media_queue = copy.deepcopy(state.get('media_queue', []))
        cleaned_queue = []
        for segment in self.media_queue:
            if not os.path.exists(segment.get('path', '')):
                continue                                # dosya artık yok (silinmiş): atla
            try:
                duration = float(segment.get('duration', 0.0))
            except (TypeError, ValueError):
                duration = 0.0
            if not math.isfinite(duration) or duration <= 0.0:
                continue
            segment['duration'] = duration
            segment['formatted_duration'] = self.format_time_display(duration)
            segment['formatted_duration_ms'] = self.format_time_display_with_ms(duration)
            cleaned_queue.append(segment)
        self.media_queue = cleaned_queue
        try:
            self.current_media_index = int(state.get('current_media_index', -1))
        except (TypeError, ValueError):
            self.current_media_index = -1
        self.current_media_index = self.current_media_index if 0 <= self.current_media_index < len(self.media_queue) else (-1 if not self.media_queue else 0)
        try:
            self.position = float(state.get('position', 0.0))
        except (TypeError, ValueError):
            self.position = 0.0
        try:
            self.paused_position = float(state.get('paused_position', 0.0))
        except (TypeError, ValueError):
            self.paused_position = 0.0
        if not math.isfinite(self.position) or self.position < 0.0:
            self.position = 0.0
        if not math.isfinite(self.paused_position) or self.paused_position < 0.0:
            self.paused_position = 0.0
        if self.current_media_index >= 0:
            duration = self.media_queue[self.current_media_index]['duration']
            self.position = min(self.position, duration)
            self.paused_position = min(self.paused_position, duration)
        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.timeline.set_selected_segment(self.current_media_index)
        self.update_total_duration_label()
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        if self.current_media_index != -1:
            self._set_media_to_player(self.current_media_index)
            self._seek(int(self.position * 1000))
        self._update_undo_redo_buttons()

    def undo(self):
        if len(self._undo_stack) > 1:
            current_state = self._undo_stack.pop()
            self._redo_stack.append(current_state)
            self._restore_state(self._undo_stack[-1])
        else:
            self.show_message_box("Bilgi", "Geri alınacak eylem yok.")
        self._update_undo_redo_buttons()

    def redo(self):
        if self._redo_stack:
            state_to_redo = self._redo_stack.pop()
            self._undo_stack.append(state_to_redo)
            self._restore_state(state_to_redo)
        else:
            self.show_message_box("Bilgi", "Yinelenecek eylem yok.")
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self):
        self.undo_btn.setEnabled(len(self._undo_stack) > 1)
        self.redo_btn.setEnabled(len(self._redo_stack) > 0)

    def populate_seek_interval_menu(self): pass

    def change_seek_interval(self, text: str):
        if text in self.millisecond_seek_intervals:
            self.seek_interval_ms = self.millisecond_seek_intervals[text]
        elif text in self.seek_intervals:
            self.seek_interval_ms = self.seek_intervals[text]

    def change_playback_speed(self, text: str):
        try:
            self.player.setPlaybackRate(float(text))
        except ValueError:
            self.show_message_box("Hata", "Geçersiz oynatma hızı.")

    def _update_selected_segment_info_labels(self): pass

    def _get_overall_timeline_position(self):
        if self.current_media_index == -1 or not self.media_queue:
            return 0.0
        time_before = 0.0
        for i in range(max(0, self.current_media_index)):
            try:
                duration = float(self.media_queue[i].get('duration', 0.0))
            except (TypeError, ValueError):
                duration = 0.0
            if math.isfinite(duration) and duration > 0.0:
                time_before += duration
        try:
            current_duration = float(self.media_queue[self.current_media_index].get('duration', 0.0))
        except (TypeError, ValueError):
            current_duration = 0.0
        if not math.isfinite(current_duration) or current_duration < 0.0:
            current_duration = 0.0
        try:
            current_position = float(self.position)
        except (TypeError, ValueError):
            current_position = 0.0
        current_position = max(0.0, min(current_position, current_duration))
        return time_before + current_position

    def _get_total_overall_duration(self):
        total = 0.0
        for segment in self.media_queue:
            try:
                duration = float(segment.get('duration', 0.0))
            except (TypeError, ValueError):
                duration = 0.0
            if math.isfinite(duration) and duration > 0.0:
                total += duration
        return total

    def toggle_fullscreen(self):
        if not self.media_queue or self.current_media_index == -1:
            self.show_message_box("Uyarı", "Tam ekran için önce medya yükleyin."); return
        current_media_info = self.media_queue[self.current_media_index]
        if current_media_info['type'] in ['video', 'recorded_video']:
            if self.is_fullscreen:
                self.showMaximized()
                self.toolbar_frame.show()
                self.timeline.show()
                self.stop_media()
                self.timeline.set_position(self.position)
                self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
                self._set_media_to_player(self.current_media_index)
                self._seek(int(self.position * 1000))
                self.is_fullscreen = False
            else:
                self.toolbar_frame.hide()
                self.timeline.hide()
                self.showFullScreen()
                self.is_fullscreen = True
        elif current_media_info['type'] in ['audio', 'recorded_audio']:
            QMessageBox.information(self, "Fonksiyon Yok", "Ses dosyaları için tam ekran yok.")
        else:
            QMessageBox.information(self, "Fonksiyon Yok", "Bu tür için tam ekran yok.")

    # ============================================================
    # KAMERA / SES KAYDI
    # ============================================================
    # ------------------------------------------------------------------ kamera / ses kaydı
    def _load_camera_settings(self):
        defaults = {"aspect": "16:9", "camera": "auto", "mic": True}
        try:
            with open(CAMERA_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if data.get("aspect") in CAMERA_ASPECTS:
                    defaults["aspect"] = data["aspect"]
                if isinstance(data.get("camera"), str):
                    defaults["camera"] = data["camera"]
                if isinstance(data.get("mic"), bool):
                    defaults["mic"] = data["mic"]
        except (OSError, ValueError):
            pass
        return defaults

    def _save_camera_settings(self):
        try:
            os.makedirs(os.path.dirname(CAMERA_SETTINGS_FILE), exist_ok=True)
            with open(CAMERA_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.camera_settings, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"Kamera ayarı kaydedilemedi: {e}")

    def _recorder_available(self):
        return os.path.isfile(RECORDER_PATH) and os.access(RECORDER_PATH, os.X_OK)

    def _list_cameras(self):
        """media_recorder --list-cameras -> [(yol, ad), ...]"""
        if not self._recorder_available():
            return []
        try:
            r = subprocess.run([RECORDER_PATH, "--list-cameras"], capture_output=True, text=True, timeout=8)
        except Exception as e:
            print(f"Kamera listesi alınamadı: {e}")
            return []
        cams = []
        for line in r.stdout.splitlines():
            if "|" in line:
                path, name = line.split("|", 1)
                cams.append((path.strip(), name.strip()))
        return cams

    def _show_camera_menu(self, pos):
        """Camera butonuna sağ tık: görüntü oranı, kamera seçimi, mikrofon."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #282c34; color: white; border: 1px solid #555; }
            QMenu::item:selected { background-color: #007bff; }
            QMenu::separator { height: 1px; background: #555; margin: 4px 8px; }
        """)
        aspect_menu = menu.addMenu("📐 Görüntü oranı")
        aspect_group = QActionGroup(aspect_menu)
        aspect_group.setExclusive(True)
        for name in CAMERA_ASPECTS:
            act = aspect_menu.addAction(name)
            act.setCheckable(True)
            act.setChecked(self.camera_settings["aspect"] == name)
            aspect_group.addAction(act)
            act.triggered.connect(lambda checked, n=name: self._set_camera_setting("aspect", n))

        cam_menu = menu.addMenu("📷 Kamera")
        cam_group = QActionGroup(cam_menu)
        cam_group.setExclusive(True)
        auto_act = cam_menu.addAction("Otomatik (ilk kamera)")
        auto_act.setCheckable(True)
        auto_act.setChecked(self.camera_settings["camera"] == "auto")
        cam_group.addAction(auto_act)
        auto_act.triggered.connect(lambda checked: self._set_camera_setting("camera", "auto"))
        for path, name in self._list_cameras():
            act = cam_menu.addAction(f"{name}  ({path})")
            act.setCheckable(True)
            act.setChecked(self.camera_settings["camera"] == path)
            cam_group.addAction(act)
            act.triggered.connect(lambda checked, p=path: self._set_camera_setting("camera", p))

        mic_act = menu.addAction("🎤 Mikrofonu da kaydet")
        mic_act.setCheckable(True)
        mic_act.setChecked(self.camera_settings["mic"])
        mic_act.triggered.connect(lambda checked: self._set_camera_setting("mic", bool(checked)))
        menu.exec_(self.camera_mode_btn.mapToGlobal(pos))

    def _set_camera_setting(self, key, value):
        self.camera_settings[key] = value
        self._save_camera_settings()

    def _handle_camera_button_click(self):
        if self.is_recording and self._rec_kind == 'camera':
            self._stop_recorder_session()
            return
        if self.is_recording or self.is_stopping_audio_recording:
            self.show_message_box("Uyarı", "Başka bir kayıt aktif. Önce onu durdurun.")
            return
        self._start_recorder('camera')

    def _toggle_audio_mode_selection(self):
        """Sound butonu: mikrofon kaydını başlatır / durdurur."""
        if self.is_recording and self._rec_kind in ('audio', 'audio_pa'):
            self._stop_recorder_session()
            return
        if self.is_recording or self.is_stopping_audio_recording:
            self.show_message_box("Uyarı", "Başka bir kayıt aktif. Önce onu durdurun.")
            return
        self._start_recorder('audio')

    def _start_recorder(self, kind):
        if self._rec_session is not None:
            return
        if self.player.state() == QMediaPlayer.PlayingState:
            self.stop_media()
        out_dir = tempfile.mkdtemp(prefix="media_kayit_")
        self._rec_dir = out_dir
        if not self._recorder_available():
            if kind == 'audio':
                self._start_audio_fallback(out_dir)
            else:
                shutil.rmtree(out_dir, ignore_errors=True)
                self.show_message_box("Hata", "Kamera kaydı için media_recorder bulunamadı.\n"
                                      "media/derleme.txt içindeki komutla derleyin (kurulum dosyası bunu yapar).")
            return

        self._rec_counter += 1
        if kind == 'camera':
            out_path = os.path.join(out_dir, f"recorded_video_{self._rec_counter}.mkv")
            w, h = CAMERA_ASPECTS.get(self.camera_settings["aspect"], (1280, 720))
            self._pv_path = f"/dev/shm/kavram_media_pv_{os.getpid()}_{self._rec_counter}"
            args = ["--record", "mode=camera", f"out={out_path}", f"camera={self.camera_settings['camera']}",
                    f"audio={'default' if self.camera_settings['mic'] else 'none'}",
                    f"w={w}", f"h={h}", "fps=30", "aspect=crop", "cw=1280", "ch=720",
                    f"pv={self._pv_path}", "pv_w=480", "pv_fps=15"]
        else:
            out_path = os.path.join(out_dir, f"recorded_audio_{self._rec_counter}.wav")
            self._pv_path = None
            args = ["--record", "mode=audio", f"out={out_path}", "audio=default"]

        session = RecorderSession(RECORDER_PATH, args, out_path, self)
        session.finished.connect(self._on_recorder_finished)
        self._rec_session = session
        self._rec_kind = kind
        self._rec_out = out_path
        self._rec_stopping = False
        self._rec_started_at = time.time()
        self.is_recording = True
        self.is_camera_mode_selected = (kind == 'camera')
        self.is_audio_mode_selected = (kind == 'audio')
        if not session.start():
            self._rec_session = None
            self.is_recording = False
            self.is_camera_mode_selected = self.is_audio_mode_selected = False
            self._rec_kind = None
            shutil.rmtree(out_dir, ignore_errors=True)
            if kind == 'audio':
                self._start_audio_fallback(tempfile.mkdtemp(prefix="media_kayit_"))
            else:
                self.show_message_box("Hata", "Kayıt programı başlatılamadı.")
            self._update_record_button_state()
            return

        # Arayüz: kamera önizlemesi ya da ses simgesi
        self.video_output_widget.hide()
        if kind == 'camera':
            self.audio_icon_label.hide()
            self.camera_preview_label.clear()
            self.camera_preview_label.show()
            if self._pv_path:
                self._pv_reader = ShmReader(self._pv_path)
            self.camera_timer.start()
        else:
            self.camera_preview_label.hide()
            self.audio_icon_label.show()
            self.camera_timer.start()          # yalnızca süre göstergesi için
        self._update_record_button_state()

    def _start_audio_fallback(self, out_dir):
        """media_recorder yoksa: PortAudio ile yedek ses kaydı (halka tamponlu, tek WAV)."""
        if not self.media_engine or not hasattr(self.media_engine, 'start_audio_record'):
            shutil.rmtree(out_dir, ignore_errors=True)
            self.show_message_box("Hata", "Ses kaydı için ne media_recorder ne de medya motoru kullanılabilir.")
            return
        if not self._pa_inited:
            self.media_engine.init_audio_engine()
            self._pa_inited = True
        self._rec_counter += 1
        out_path = os.path.join(out_dir, f"recorded_audio_{self._rec_counter}.wav")
        res = self.media_engine.start_audio_record(b"", out_path.encode("utf-8"))
        if res != 0:
            shutil.rmtree(out_dir, ignore_errors=True)
            self.show_message_box("Hata", f"Ses kaydı başlatılamadı (kod {res}). Mikrofon bağlı mı?")
            return
        self._rec_dir = out_dir
        self._rec_kind = 'audio_pa'
        self._rec_out = out_path
        self._rec_started_at = time.time()
        self.is_recording = True
        self.is_audio_mode_selected = True
        self.video_output_widget.hide()
        self.camera_preview_label.hide()
        self.audio_icon_label.show()
        self.camera_timer.start()
        self._update_record_button_state()

    def _stop_recorder_session(self):
        if self.is_stopping_audio_recording:
            return
        self.is_stopping_audio_recording = True
        self._update_record_button_state()
        if self._rec_kind == 'audio_pa':
            try:
                self.media_engine.stop_audio_record()
            except Exception as e:
                print(f"stop_audio_record hatası: {e}")
            QTimer.singleShot(0, lambda: self._on_recorder_finished(0, self._rec_out, ""))
            return
        if self._rec_session is not None:
            self._rec_session.request_stop()

    def _update_camera_preview(self):
        """Kayıt sürerken: süre göstergesi + kamera önizlemesi (66 ms)."""
        if not self.is_recording:
            return
        elapsed = max(0.0, time.time() - self._rec_started_at)
        self.current_time_label.setText(self.format_time_display_with_ms(elapsed))
        if self._rec_kind == 'camera' and self._pv_reader is not None:
            img = self._pv_reader.read_frame()
            if img is not None:
                pm = QPixmap.fromImage(img).scaled(self.camera_preview_label.size(), Qt.KeepAspectRatio,
                                                   Qt.SmoothTransformation)
                self.camera_preview_label.setPixmap(pm)

    def _on_recorder_finished(self, code, out_path, log):
        kind = self._rec_kind
        out_dir = self._rec_dir
        session = self._rec_session
        self._rec_session = None
        self._rec_kind = None
        self.camera_timer.stop()
        if self._pv_reader is not None:
            self._pv_reader.close()
            self._pv_reader = None
        self.is_recording = False
        self.is_camera_mode_selected = False
        self.is_audio_mode_selected = False
        self.is_stopping_audio_recording = False
        self.camera_preview_label.hide()
        self.camera_preview_label.clear()
        self.audio_icon_label.hide()
        if 0 <= self.current_media_index < len(self.media_queue):
            self._set_media_to_player(self.current_media_index)
        self._update_record_button_state()
        if session is not None:
            session.deleteLater()

        have_file = bool(out_path) and os.path.exists(out_path) and os.path.getsize(out_path) > 2048
        if code != 0:
            hints = {2: "Kamera açılamadı. Kamera başka bir programda kullanılıyor olabilir ya da erişim izni yok\n"
                        "('video' grubunda olduğunuzdan emin olun).",
                     4: "Mikrofon açılamadı. Sağ tık menüsünden mikrofonu kapatıp tekrar deneyebilirsiniz.",
                     5: "Eksik GStreamer eklentisi var:\n" + log[-400:]}
            if not have_file:
                if kind == 'audio' and code in (4, 5, -1):
                    # ses için yedek yöntem
                    shutil.rmtree(out_dir, ignore_errors=True) if out_dir else None
                    self._start_audio_fallback(tempfile.mkdtemp(prefix="media_kayit_"))
                    return
                self.show_message_box("Kayıt Hatası", hints.get(code, f"Kayıt başarısız oldu (kod {code}).\n{log[-500:]}"))
                if out_dir:
                    shutil.rmtree(out_dir, ignore_errors=True)
                return
        if not have_file:
            if out_dir:
                shutil.rmtree(out_dir, ignore_errors=True)
            self.show_message_box("Uyarı", "Kayıt boş görünüyor; eklenmedi.")
            return
        self._finish_recording(kind, out_path, out_dir)

    def _finish_recording(self, kind, out_path, out_dir):
        """Kaydı kontrol eder (gerekirse onarır), filtre (I) aktifse SESİ filtreler, medya listesine ekler."""
        media_type = 'recorded_video' if kind == 'camera' else 'recorded_audio'
        name = os.path.splitext(os.path.basename(out_path))[0]
        info = self._probe_media(out_path)
        if info is None or info['duration'] <= 0:
            repaired = os.path.join(out_dir, "onarilmis" + os.path.splitext(out_path)[1])
            if self._run_ffmpeg_blocking(["-i", out_path, "-c", "copy", repaired], "Kayıt onarılıyor..."):
                os.replace(repaired, out_path)
                info = self._probe_media(out_path)
        if info is None or info['duration'] <= 0:
            self.show_message_box("Hata", "Kayıt dosyası okunamadı.")
            shutil.rmtree(out_dir, ignore_errors=True)
            return

        def on_done(path, mtype, original_name):
            try:
                self.add_media_to_queue(path, media_type, original_name)
            finally:
                shutil.rmtree(out_dir, ignore_errors=True)

        self._apply_filter_to_media(out_path, media_type, name, on_done)

    def _update_record_button_state(self):
        rec_audio = self.is_recording and self._rec_kind in ('audio', 'audio_pa')
        rec_camera = self.is_recording and self._rec_kind == 'camera'
        busy = self.is_stopping_audio_recording
        self.audio_mode_btn.setText("Stop" if rec_audio else "Sound")
        self.audio_mode_btn.setStyleSheet(self.buttonStyle("record_active" if rec_audio else "default"))
        self.camera_mode_btn.setText("Stop" if rec_camera else "Camera")
        self.camera_mode_btn.setStyleSheet(self.buttonStyle("record_active" if rec_camera else "default"))
        self.play_pause_btn.setEnabled(not self.is_recording)
        self.sequence_play_btn.setEnabled(not self.is_recording)
        can_audio = self._recorder_available() or self.media_engine is not None
        self.audio_mode_btn.setEnabled(not busy and not rec_camera and can_audio)
        self.camera_mode_btn.setEnabled(not busy and not rec_audio)
        self._update_sequence_play_button_state()

    def _stop_all_recording_processes(self):
        if self._rec_session is not None:
            self._rec_session.kill()
        if self._rec_kind == 'audio_pa' and self.media_engine:
            try:
                self.media_engine.stop_audio_record()
            except Exception as e:
                print(f"stop_audio_record hatası: {e}")
        self.camera_timer.stop()
        if self._pv_reader is not None:
            self._pv_reader.close()
            self._pv_reader = None
        self.is_recording = False
        self.is_stopping_audio_recording = False
        self.is_camera_mode_selected = False
        self.is_audio_mode_selected = False
        self._rec_kind = None
        if self._rec_dir:
            shutil.rmtree(self._rec_dir, ignore_errors=True)
            self._rec_dir = None

    def _update_sequence_play_button_state(self):
        if self.is_sequence_play_active:
            self.sequence_play_btn.setStyleSheet(self.buttonStyle("sequence_play_active"))
        else:
            self.sequence_play_btn.setStyleSheet(self.buttonStyle("sequence_toggle"))
        self.sequence_play_btn.setEnabled(not self.is_recording)

