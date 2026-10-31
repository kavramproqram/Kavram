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

# Kavram çekirdeği: drawing.py
# Tek dosya: önceden ayrı olan drawing_common / widgets / layers / select / points /
# canvas / animation / export modülleri bu dosyada birleştirildi.
# --- kavram yol ayarı (otomatik; klasör yapısı: kavram/<program>/<program>.py) ---
import os as _os
_PROGRAM_DIR = _os.path.dirname(_os.path.abspath(__file__))
_KAVRAM_DIR = _os.environ.get("KAVRAM_DIR") or _os.path.dirname(_PROGRAM_DIR)
_KAVRAM_EXPORT_DIR = _os.path.join(_KAVRAM_DIR, "export")
# -------------------------------------------------------------------------------

# ===========================================================================
# BÖLÜM: ORTAK İÇE AKTARMALAR, YARDIMCILAR VE SVG İKONLAR
# ===========================================================================
import sys
import math
import os
import json
import base64
import random
import tempfile
import subprocess
import shutil
import copy
import threading
import time
import glob
from collections import deque

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QDialog, QSlider, QLabel,
    QPushButton, QApplication, QFileDialog, QMessageBox, QShortcut, QLineEdit,
    QMenu, QAction, QComboBox, QWidgetAction, QScrollArea, QListWidget,
    QListWidgetItem, QAbstractItemView, QCheckBox, QInputDialog, QToolButton,
    QTextEdit, QSizePolicy, QSpinBox, QProgressDialog, QDoubleSpinBox, QAbstractButton, QToolTip
)
from PyQt5.QtGui import (
    QColor, QPainter, QPen, QImage, QTabletEvent, QKeySequence, QFont,
    QFontMetrics, QCursor, QIcon, QPixmap, QPainterPath, QPolygon, QPolygonF, QBrush,
    QDrag, QTransform, QClipboard, QLinearGradient, QRadialGradient, QConicalGradient,
    QRegion
)
from PyQt5.QtCore import (
    Qt, QPoint, QRect, QDir, QSize, QByteArray, QBuffer, QIODevice,
    pyqtSignal, QMimeData, QObject, QPointF, QRectF, QTimer, QEvent, QSettings, QThread, QElapsedTimer
)
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtSvg import QSvgRenderer

# --- Yardımcı Fonksiyonlar ve Sabitler ---

def resource_path(relative_path):
    """ PyInstaller vb. derlemeler için dinamik kaynak yolu bulucu. """
    return os.path.join(_KAVRAM_DIR, relative_path)

# ---- FFmpeg bulucu: önce bin/ klasörü, sonra sistem PATH ----
def find_ffmpeg():
    candidates = [resource_path("bin/ffmpeg"), resource_path("bin/ffmpeg.exe")]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    found = shutil.which("ffmpeg")
    return found if found else candidates[0]

FFMPEG_PATH = find_ffmpeg()

def ffmpeg_available():
    return os.path.isfile(FFMPEG_PATH) and os.access(FFMPEG_PATH, os.X_OK)

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
SVG_REDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5C8.13401 5 5 8.13401 5 12C5 15.866 8.13401 19 12 19C15.866 19 19 12 19 12C19 10.2091 18.2999 8.57074 17.1541 7.3614L19 6M19 6H15M19 6V10" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_EYE_OPEN = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1 12C1 12 5 4 12 4C19 4 23 12 23 12C23 12 19 20 12 20C5 20 1 12 1 12Z" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_EYE_CLOSED = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20C5 20 1 12 1 12C1 12 2.33 9.67 4.78 7.64M1 1L23 23M9.9 4.24A9.12 9.12 0 0 1 12 4C19 4 23 12 23 12C23 12 21.72 14.28 19.33 16.3" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M14.12 14.12A3 3 0 1 1 9.88 9.88" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_SAVE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V7L17 3ZM12 17C10.34 17 9 15.66 9 14C9 12.34 10.34 11 12 11C13.66 11 15 12.34 15 14C15 15.66 13.66 17 12 17Z" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_ARROW_UP = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19V5" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 12L12 5L19 12" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

SVG_LAYER_SKETCH = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M15.5 3L21 8.5L12 17.5H6.5V12L15.5 3Z" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 5.5L18.5 11" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_LAYER_DRAFT = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M3 3H21V21H3V3Z" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 9H21" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 21V3" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_LAYER_DRAWING = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 20L8 16" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 12L20 4" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="10" cy="14" r="2" stroke="#eee" stroke-width="2"/><path d="M14 10L10 14" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_LAYER_IMAGE = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="8.5" cy="8.5" r="1.5" fill="#eee"/><path d="M21 15L16 10L5 21" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_ALWAYS_TOP = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 17L12 22L22 17" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 12L12 17L22 12" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

# --- Çözünürlük ve Boyut Modülleri (alan.py Entegrasyonu) ---


_SVG_HEAD = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
SVG_LOCK = _SVG_HEAD + '<rect x="5" y="11" width="14" height="10" rx="2" stroke="#eee" stroke-width="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4" stroke="#eee" stroke-width="2" stroke-linecap="round"/></svg>'
SVG_UNLOCK = _SVG_HEAD + '<rect x="5" y="11" width="14" height="10" rx="2" stroke="#eee" stroke-width="2"/><path d="M8 11V7a4 4 0 0 1 7.5-1.5" stroke="#eee" stroke-width="2" stroke-linecap="round"/></svg>'
SVG_PLAY = _SVG_HEAD + '<path d="M7 4L20 12L7 20Z" fill="#eee" stroke="#eee" stroke-width="2" stroke-linejoin="round"/></svg>'
SVG_PAUSE = _SVG_HEAD + '<rect x="6" y="4" width="4" height="16" fill="#eee"/><rect x="14" y="4" width="4" height="16" fill="#eee"/></svg>'
SVG_STOP = _SVG_HEAD + '<rect x="5" y="5" width="14" height="14" rx="1" fill="#eee"/></svg>'
SVG_ONION = _SVG_HEAD + '<circle cx="9" cy="12" r="6" stroke="#eee" stroke-width="2"/><circle cx="15" cy="12" r="6" stroke="#eee" stroke-width="2"/></svg>'


class SvgIconButton(QAbstractButton):
    """Stil sayfalarından (padding vb.) etkilenmeyen, doğrudan SVG çizen ikon düğmesi.
    (Katman panelindeki göz/kilit ikonlarının nokta gibi görünmesini önler.)"""

    def __init__(self, svg, color="#eeeeee", size=28, icon_px=18, parent=None):
        super().__init__(parent)
        self._svg = svg
        self._color = color
        self._icon_px = icon_px
        self._hover = False
        self._renderer = None
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self._rebuild()

    def _rebuild(self):
        data = self._svg.replace("#eee", self._color)
        self._renderer = QSvgRenderer(QByteArray(data.encode("utf-8")))
        self.update()

    def setSvg(self, svg, color=None):
        self._svg = svg
        if color:
            self._color = color
        self._rebuild()

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._hover or self.isChecked():
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 40 if self.isChecked() else 28))
            p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 5, 5)
        px = self._icon_px
        r = QRectF((self.width() - px) / 2.0, (self.height() - px) / 2.0, px, px)
        self._renderer.render(p, r)


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


# ===========================================================================
# BÖLÜM: KÜÇÜK WIDGET VE DİYALOGLAR
# ===========================================================================
# Kavram - küçük widget ve diyaloglar

class AspectRatioPreviewWidget(QWidget):
    """
    Kullanıcının seçtiği çözünürlüğü ve en-boy oranını,
    ekstrem değerlerde bile kusursuz oranlayıp görselleştiren şık önizleme tuvali.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.target_width = 1920
        self.target_height = 1080
        self.setMinimumSize(240, 200)

    def update_dimensions(self, width, height):
        self.target_width = max(1, width)
        self.target_height = max(1, height)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        painter.fillRect(rect, QColor("#111111"))

        margin = 35
        widget_w = rect.width() - (margin * 2)
        widget_h = rect.height() - (margin * 2)
        
        ratio = self.target_width / self.target_height
        
        if (widget_w / ratio) <= widget_h:
            preview_w = widget_w
            preview_h = widget_w / ratio
        else:
            preview_h = widget_h
            preview_w = widget_h * ratio

        min_thickness = 10.0
        if preview_w < min_thickness:
            preview_w = min_thickness
        if preview_h < min_thickness:
            preview_h = min_thickness

        x = (rect.width() - preview_w) / 2
        y = (rect.height() - preview_h) / 2

        preview_rect = QRectF(x, y, preview_w, preview_h)
        painter.setBrush(QBrush(QColor(255, 255, 255, 8)))
        
        pen = QPen(QColor("#555555"), 1.5)
        painter.setPen(pen)
        painter.drawRoundedRect(preview_rect, 4, 4)

        info_area_height = 32
        info_rect = QRectF(0, rect.height() - info_area_height, rect.width(), info_area_height)
        painter.fillRect(info_rect, QColor("#090909"))
        
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawLine(0, int(rect.height() - info_area_height), rect.width(), int(rect.height() - info_area_height))

        painter.setPen(QColor("#aaaaaa"))
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        
        gcd = math.gcd(self.target_width, self.target_height)
        simple_w = self.target_width // gcd
        simple_h = self.target_height // gcd
        ratio_text = f"{simple_w}:{simple_h}"
        
        painter.drawText(info_rect, Qt.AlignCenter, f"{self.target_width} x {self.target_height}  •  ({ratio_text})")


class AspectRatioDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Çözünürlük (Tuval Boyutu)")
        self.setWindowIcon(QIcon(resource_path('ikon/kavram.png')))
        self.setModal(True)
        self.resize(580, 320)

        self.setStyleSheet("""
            QDialog {
                background-color: #222222;
                color: #FFFFFF;
            }
            QLabel {
                color: #aaaaaa;
                font-family: 'Segoe UI', Arial;
                font-size: 11px;
                font-weight: bold;
            }
            QLabel#section_title {
                color: #eeeeee;
                font-size: 12px;
                font-weight: bold;
            }
            QComboBox {
                background-color: transparent;
                color: white;
                border: 2px solid #555555;
                border-radius: 8px;
                padding: 5px 10px;
                font-family: 'Segoe UI';
                font-size: 12px;
            }
            QComboBox:hover {
                background-color: #444444;
            }
            QComboBox::drop-down {
                border: none;
                width: 0px; 
            }
            QComboBox QAbstractItemView {
                background-color: #222222;
                color: white;
                border: 2px solid #555555;
                selection-background-color: #444444;
                selection-color: white;
                outline: none;
            }
            QSpinBox {
                background-color: transparent;
                color: white;
                border: 2px solid #555555;
                border-radius: 8px;
                padding: 5px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
            QSpinBox:hover {
                background-color: #444444;
            }
            QSpinBox:focus {
                border: 2px solid #888888;
            }
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 8px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:pressed {
                background-color: #666666;
            }
            QFrame#divider {
                background-color: #333333;
                max-height: 1px;
                min-height: 1px;
            }
            QFrame#sidebar {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 8px;
            }
        """)

        # Varsayılanlar başa eklendi
        self.presets = {
            "Varsayılan": [
                ("Klasik Kavram (1100 x 600)", 1100, 600),
                ("Standart Full HD (1920 x 1080)", 1920, 1080),
                ("Kare Tuval (1080 x 1080)", 1080, 1080)
            ],
            "Geniş Ekran (16:9)": [
                ("3840 x 2160 - 4K Ultra HD", 3840, 2160),
                ("2560 x 1440 - 2K / QHD", 2560, 1440),
                ("1920 x 1080 - Full HD", 1920, 1080)
            ],
            "Dikey & Sosyal Medya": [
                ("1080 x 1920 - Reels & TikTok", 1080, 1920),
                ("1080 x 1350 - Instagram Post 4:5", 1080, 1350),
                ("1080 x 1080 - Kare Post 1:1", 1080, 1080)
            ],
            "Kitap, Manga & Yayın": [
                ("2480 x 3508 - A4 Baskı / PDF", 2480, 3508),
                ("1748 x 2480 - A5 Kitap / PDF", 1748, 2480),
                ("1200 x 1600 - 3:4 Dijital Manga", 1200, 1600),
                ("1500 x 2100 - Yüksek Çözünürlüklü Manga", 1500, 2100),
                ("800 x 1280 - Webtoon Panel Parçası", 800, 1280)
            ],
            "Özel Boyut": []
        }

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)

        left_panel.addWidget(QLabel("EN-BOY ORANI:", self))
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(list(self.presets.keys()))
        left_panel.addWidget(self.ratio_combo)

        left_panel.addWidget(QLabel("HAZIR ÇÖZÜNÜKLER:", self))
        self.preset_combo = QComboBox()
        left_panel.addWidget(self.preset_combo)

        divider = QFrame()
        divider.setObjectName("divider")
        left_panel.addWidget(divider)

        dim_layout = QHBoxLayout()
        dim_layout.setSpacing(10)
        
        width_box = QVBoxLayout()
        width_box.setSpacing(4)
        width_box.addWidget(QLabel("GENİŞLİK (PX):"))
        self.width_input = QSpinBox()
        self.width_input.setRange(8, 30000) 
        self.width_input.setValue(1100)
        self.width_input.setButtonSymbols(QSpinBox.NoButtons) 
        width_box.addWidget(self.width_input)
        
        height_box = QVBoxLayout()
        height_box.setSpacing(4)
        height_box.addWidget(QLabel("YÜKSEKLİK (PX):"))
        self.height_input = QSpinBox()
        self.height_input.setRange(8, 30000)
        self.height_input.setValue(600)
        self.height_input.setButtonSymbols(QSpinBox.NoButtons) 
        height_box.addWidget(self.height_input)

        dim_layout.addLayout(width_box)
        dim_layout.addLayout(height_box)
        left_panel.addLayout(dim_layout)

        self.info_label = QLabel("Bilgi: 0.66 Megapiksel")
        self.info_label.setStyleSheet("color: #777777; font-size: 10px;")
        left_panel.addWidget(self.info_label)

        left_panel.addStretch()

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.cancel_button = QPushButton("İptal")
        self.cancel_button.clicked.connect(self.reject)
        
        self.ok_button = QPushButton("Kaydet")
        self.ok_button.setStyleSheet("""
            QPushButton {
                border-color: #777777;
                background-color: #2a2a2a;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """)
        self.ok_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        left_panel.addLayout(button_layout)

        right_panel_container = QFrame()
        right_panel_container.setObjectName("sidebar")
        right_panel_layout = QVBoxLayout(right_panel_container)
        right_panel_layout.setContentsMargins(10, 10, 10, 10)
        
        preview_title = QLabel("ÖNİZLEME")
        preview_title.setObjectName("section_title")
        preview_title.setAlignment(Qt.AlignCenter)
        right_panel_layout.addWidget(preview_title)

        self.preview_widget = AspectRatioPreviewWidget()
        right_panel_layout.addWidget(self.preview_widget)

        main_layout.addLayout(left_panel, stretch=3)
        main_layout.addWidget(right_panel_container, stretch=2)

        self.ratio_combo.currentIndexChanged.connect(self.on_ratio_changed)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        self.width_input.valueChanged.connect(self.on_dimension_changed)
        self.height_input.valueChanged.connect(self.on_dimension_changed)

        self.load_settings()
        self.update_info_label()

    def load_settings(self):
        settings = QSettings("kavram", "DrawingEditor")
        saved_ratio = settings.value("ratio", "Varsayılan")
        saved_width = settings.value("canvasWidth", 1100, type=int)
        saved_height = settings.value("canvasHeight", 600, type=int)

        self.ratio_combo.blockSignals(True)
        self.preset_combo.blockSignals(True)
        self.width_input.blockSignals(True)
        self.height_input.blockSignals(True)

        ratio_index = self.ratio_combo.findText(saved_ratio)
        if ratio_index != -1:
            self.ratio_combo.setCurrentIndex(ratio_index)
        else:
            self.ratio_combo.setCurrentIndex(0)

        selected_ratio = self.ratio_combo.currentText()
        preset_list = self.presets.get(selected_ratio, [])
        if preset_list:
            self.preset_combo.setEnabled(True)
            for text, w, h in preset_list:
                self.preset_combo.addItem(text, (w, h))
        else:
            self.preset_combo.addItem("Serbest Giriş")
            self.preset_combo.setEnabled(False)

        self.width_input.setValue(saved_width)
        self.height_input.setValue(saved_height)

        matched_preset_index = -1
        for i in range(self.preset_combo.count()):
            data = self.preset_combo.itemData(i)
            if data and data == (saved_width, saved_height):
                matched_preset_index = i
                break

        if matched_preset_index != -1:
            self.preset_combo.setCurrentIndex(matched_preset_index)
        else:
            if selected_ratio != "Özel Boyut":
                self.ratio_combo.setCurrentText("Özel Boyut")
                self.preset_combo.clear()
                self.preset_combo.addItem("Serbest Giriş")
                self.preset_combo.setEnabled(False)

        self.ratio_combo.blockSignals(False)
        self.preset_combo.blockSignals(False)
        self.width_input.blockSignals(False)
        self.height_input.blockSignals(False)

        self.preview_widget.update_dimensions(saved_width, saved_height)

    def on_ratio_changed(self, index):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        
        selected_ratio = self.ratio_combo.currentText()
        preset_list = self.presets.get(selected_ratio, [])

        if preset_list:
            self.preset_combo.setEnabled(True)
            for text, w, h in preset_list:
                self.preset_combo.addItem(text, (w, h))
            self.preset_combo.blockSignals(False)
            self.on_preset_changed(0)
        else:
            self.preset_combo.addItem("Serbest Giriş")
            self.preset_combo.setEnabled(False)
            self.preset_combo.blockSignals(False)

    def on_preset_changed(self, index):
        if index < 0:
            return
            
        data = self.preset_combo.currentData()
        if data:
            width, height = data
            self.width_input.blockSignals(True)
            self.height_input.blockSignals(True)
            
            self.width_input.setValue(width)
            self.height_input.setValue(height)
            
            self.width_input.blockSignals(False)
            self.height_input.blockSignals(False)
            
            self.preview_widget.update_dimensions(width, height)
            self.update_info_label()

    def on_dimension_changed(self, value):
        w = self.width_input.value()
        h = self.height_input.value()
        
        self.ratio_combo.blockSignals(True)
        if not self.check_if_matches_preset(w, h):
            self.ratio_combo.setCurrentText("Özel Boyut")
            self.preset_combo.setEnabled(False)
        self.ratio_combo.blockSignals(False)

        self.preview_widget.update_dimensions(w, h)
        self.update_info_label()

    def check_if_matches_preset(self, w, h):
        for ratio_key, preset_list in self.presets.items():
            for text, px_w, px_h in preset_list:
                if px_w == w and px_h == h:
                    return True
        return False

    def update_info_label(self):
        w = self.width_input.value()
        h = self.height_input.value()
        mp = (w * h) / 1000000.0
        
        if w > h:
            orientation = "Yatay"
        elif h > w:
            orientation = "Dikey"
        else:
            orientation = "Kare"
            
        self.info_label.setText(f"Özet: {mp:.2f} Megapiksel • {orientation}")

    def accept(self):
        settings = QSettings("kavram", "DrawingEditor")
        settings.setValue("ratio", self.ratio_combo.currentText())
        settings.setValue("canvasWidth", self.width_input.value())
        settings.setValue("canvasHeight", self.height_input.value())
        super().accept()

    def getSettings(self):
        return {
            "ratio": self.ratio_combo.currentText(),
            "width": self.width_input.value(),
            "height": self.height_input.value()
        }


# --- Özel Widgetlar ---

class ExportMenu(QMenu):
    def __init__(self, parent=None, default_callback=None):
        super().__init__(parent)
        self.default_callback = default_callback

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            active = self.activeAction()
            if active:
                active.trigger()
            elif self.default_callback:
                self.default_callback()
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)

class ResizableTextEdit(QTextEdit):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFrameShape(QFrame.Box)
        self.setFrameShadow(QFrame.Plain)
        self.setLineWidth(1)
        self.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: white;
                border: 1px dashed rgba(255, 255, 255, 150);
                border-radius: 4px;
                padding: 5px;
            }
        """)
        self.textChanged.connect(self.updateGeometry)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if event.modifiers() & Qt.ShiftModifier:
                self.finished.emit()
                event.accept()
                return
            else:
                super().keyPressEvent(event)
                return
        super().keyPressEvent(event)

    def updateGeometry(self):
        document = self.document()
        font_metrics = QFontMetrics(self.font())
        lines = self.toPlainText().split('\n')
        max_width = 0
        for line in lines:
            w = font_metrics.horizontalAdvance(line)
            if w > max_width:
                max_width = w

        new_width = max(100, max_width + 40)
        doc_height = document.size().height()
        new_height = max(40, doc_height + 10)

        self.resize(int(new_width), int(new_height))
        super().updateGeometry()

class NavigationModeButton(QPushButton):
    rightClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("O", parent)
        self.setCheckable(True)
        self.setFixedSize(40, 30)
        self.setStyleSheet(self.getStyle(False))
        self.clicked.connect(self.updateStyle)
        self.setToolTip("Gezinme Modu (Wheel: Zoom, Orta Tuş: Pan, Sol Tık: Çizim, Sağ Tık: Çözünürlük ve Boyutlar)")

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit()
        else:
            super().mousePressEvent(event)

    def updateStyle(self):
        self.setStyleSheet(self.getStyle(self.isChecked()))

    def getStyle(self, active):
        if active:
            return """
                QPushButton { background-color: #777; color: white; font-weight: bold; font-size: 16px; border: 2px solid #999; border-radius: 8px; }
            """
        else:
            return """
                QPushButton { background-color: transparent; color: #aaa; font-weight: bold; font-size: 16px; border: 2px solid #555; border-radius: 8px; }
                QPushButton:hover { background-color: #444; }
            """

class RadiusOverlayDialog(QDialog):
    def __init__(self, current_val, parent=None, is_sensitivity=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 80)
        self.is_sensitivity = is_sensitivity

        is_eraser = False
        if parent and hasattr(parent, 'eraser_mode') and parent.eraser_mode:
            is_eraser = True

        layout = QVBoxLayout(self)

        if self.is_sensitivity:
            title_text = f"Basınç Hassasiyeti: {'Oto' if current_val == -1 else current_val}"
        else:
            title_text = f"Silgi Boyutu: {current_val}" if is_eraser else f"Kalem Boyutu: {current_val}"

        self.label = QLabel(title_text, self)
        self.label.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        self.label.setAlignment(Qt.AlignCenter)

        self.slider = QSlider(Qt.Horizontal, self)

        if self.is_sensitivity:
             self.slider.setRange(0, 100)
             self.slider.setValue(0 if current_val == -1 else current_val)
        else:
             self.slider.setRange(1, 150)
             self.slider.setValue(current_val)

        self.slider.setStyleSheet("""
            QSlider::groove:horizontal { border: 1px solid #555; height: 8px; background: #333; margin: 2px 0; border-radius: 4px; }
            QSlider::handle:horizontal { background: #aaa; border: 1px solid #555; width: 18px; height: 18px; margin: -7px 0; border-radius: 9px; }
        """)
        self.slider.valueChanged.connect(lambda v: self.updateLabel(v, is_eraser))

        layout.addWidget(self.label)
        layout.addWidget(self.slider)

        self.setStyleSheet("background-color: #222; border: 2px solid #555; border-radius: 10px;")

    def updateLabel(self, val, is_eraser):
        if self.is_sensitivity:
            txt = "Oto" if val == 0 else str(val)
            self.label.setText(f"Basınç Hassasiyeti: {txt}")
        else:
            title_text = f"Silgi Boyutu: {val}" if is_eraser else f"Kalem Boyutu: {val}"
            self.label.setText(title_text)

    def getValue(self):
        val = self.slider.value()
        if self.is_sensitivity and val == 0:
            return -1
        return val

class RightClickButton(QPushButton):
    rightClicked = pyqtSignal(object)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit(event.pos())
        else:
            super().mousePressEvent(event)

class MirrorControlButton(QPushButton):
    leftClicked = pyqtSignal()
    rightClicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit()
        else:
            self.leftClicked.emit()
        super().mousePressEvent(event)

class ScrollableButton(QPushButton):
    deltaChanged = pyqtSignal(int)
    def wheelEvent(self, event):
        delta = 1 if event.angleDelta().y() > 0 else -1
        self.deltaChanged.emit(delta)
        event.accept()

class PageNavigatorButton(QPushButton):
    pageChanged = pyqtSignal(int)

    def wheelEvent(self, event):
        delta = 1 if event.angleDelta().y() > 0 else -1
        self.pageChanged.emit(delta)
        event.accept()

class MixAngleButton(QPushButton):
    deltaChanged = pyqtSignal(int)
    def wheelEvent(self, event):
        delta = 1 if event.angleDelta().y() > 0 else -1
        self.deltaChanged.emit(delta)
        event.accept()

class WheelButton(QPushButton):
    def __init__(self, text, parent=None, is_sensitivity=False):
        super().__init__(text, parent)
        self.is_sensitivity = is_sensitivity

    def wheelEvent(self, event):
        main_window = self.window()
        delta = 1 if event.angleDelta().y() > 0 else -1

        if self.is_sensitivity:
             if hasattr(main_window, 'changeSensitivityValue'):
                 current = main_window.sensitivity_value
                 if current == -1:
                     current = 50
                 new_val = max(1, min(100, current + delta))
                 main_window.changeSensitivityValue(new_val)
        else:
            if hasattr(main_window, 'solid_fill_mode') and main_window.solid_fill_mode:
                return

            if hasattr(main_window, 'changeRadiusValue'):
                new_radius = max(1, min(357, main_window.pen_radius + delta))
                main_window.changeRadiusValue(new_radius)
        event.accept()

class LazyMouseButton(QPushButton):
    radiusChanged = pyqtSignal(int)
    factorChanged = pyqtSignal(int)
    rightClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("lm", parent)
        self._adjusting_radius = True
        self.setMouseTracking(True)
        self.setCheckable(True)

        self.setStyleSheet("""
            QPushButton { background-color: transparent; color: #888; border: none; padding: 2px 6px; font-size: 12px; font-weight: normal; }
            QPushButton:hover { color: #aaa; background-color: transparent; }
            QPushButton:checked { color: #4CAF50; }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit()
        else:
            super().mousePressEvent(event)

    def wheelEvent(self, event):
        main_window = self.window()
        delta = 1 if event.angleDelta().y() > 0 else -1
        
        if hasattr(main_window, 'lazy_radius') and hasattr(main_window, 'lazy_factor'):
            modifiers = QApplication.keyboardModifiers()
            if modifiers == Qt.ControlModifier:
                new_factor = max(1, min(100, main_window.lazy_factor + delta))
                main_window.lazy_factor = new_factor
                self.factorChanged.emit(new_factor)
            else:
                new_radius = max(5, min(200, main_window.lazy_radius + delta * 5))
                main_window.lazy_radius = new_radius
                self.radiusChanged.emit(new_radius)
            
            self.updateButtonText(main_window)
            self.updateToolTip(main_window)
            if hasattr(main_window, 'saveLazyMouseSettings'):
                main_window.saveLazyMouseSettings()
        event.accept()
    
    def updateButtonText(self, main_window):
        self.setText("lm")
    
    def updateToolTip(self, main_window):
        self.setToolTip(
            f"Lazy Mouse: Yavaşlatılmış fare (Blender tarzı)\n"
            f"R={main_window.lazy_radius} (Yarıçap), H={main_window.lazy_factor} (Hassasiyet)\n"
            f"Fare tekerleği: Radius, Ctrl+Tekerlek: Hassasiyet\n"
            f"Varsayılan: R=30, H=15"
        )


class ColorHistoryStrip(QWidget):
    colorSelected = pyqtSignal(object, object)
    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.colors = colors
        self.square_size = 24
        self.spacing = 6
        self.margin = 5
        self.cols_per_row = 4
        num_rows = (len(colors) + self.cols_per_row - 1) // self.cols_per_row
        total_width = self.margin * 2 + self.cols_per_row * (self.square_size + self.spacing)
        total_height = self.margin * 2 + num_rows * (self.square_size + self.spacing)
        self.setFixedSize(max(150, total_width), total_height)
        self.setCursor(Qt.PointingHandCursor)
        self.hovered_index = -1
        self.is_pressed = False
        self.setMouseTracking(True)
    def enterEvent(self, event):
        super().enterEvent(event)
    def leaveEvent(self, event):
        self.hovered_index = -1
        self.is_pressed = False
        self.update()
        super().leaveEvent(event)
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.underMouse():
            painter.fillRect(self.rect(), QColor(60, 60, 60))
        for i, color in enumerate(self.colors):
            row = i // self.cols_per_row
            col = i % self.cols_per_row
            x = self.margin + col * (self.square_size + self.spacing)
            y = self.margin + row * (self.square_size + self.spacing)
            rect = QRect(x, y, self.square_size, self.square_size)
            painter.setBrush(QBrush(color))
            if i == self.hovered_index:
                painter.setPen(QPen(Qt.white, 2))
                if self.is_pressed:
                    painter.setBrush(QBrush(color.darker(120)))
            else:
                painter.setPen(QPen(Qt.gray, 1))
            painter.drawRoundedRect(rect, 4, 4)
    def mouseMoveEvent(self, event):
        pos = event.pos()
        old_hover = self.hovered_index
        self.hovered_index = -1
        for i in range(len(self.colors)):
            row = i // self.cols_per_row
            col = i % self.cols_per_row
            x = self.margin + col * (self.square_size + self.spacing)
            y = self.margin + row * (self.square_size + self.spacing)
            rect = QRect(x, y, self.square_size, self.square_size)
            if rect.contains(pos):
                self.hovered_index = i
                break
        if old_hover != self.hovered_index:
            self.update()
        super().mouseMoveEvent(event)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.hovered_index >= 0:
                self.is_pressed = True
                self.update()
            pos = event.pos()
            clicked_color_index = -1
            for i in range(len(self.colors)):
                row = i // self.cols_per_row
                col = i % self.cols_per_row
                x = self.margin + col * (self.square_size + self.spacing)
                y = self.margin + row * (self.square_size + self.spacing)
                rect = QRect(x, y, self.square_size, self.square_size)
                if rect.contains(pos):
                    clicked_color_index = i
                    break
            if clicked_color_index != -1:
                self.colorSelected.emit(self.colors[clicked_color_index], None)
            else:
                if len(self.colors) == 1:
                    self.colorSelected.emit(self.colors[0], None)
                else:
                    self.colorSelected.emit(None, self.colors)
        elif event.button() == Qt.RightButton:
            self.showContextMenu(event.pos())
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_pressed = False
            self.update()
        super().mouseReleaseEvent(event)
    def showContextMenu(self, pos):
        clicked_color_index = -1
        for i in range(len(self.colors)):
            row = i // self.cols_per_row
            col = i % self.cols_per_row
            x = self.margin + col * (self.square_size + self.spacing)
            y = self.margin + row * (self.square_size + self.spacing)
            rect = QRect(x, y, self.square_size, self.square_size)
            if rect.contains(pos):
                clicked_color_index = i
                break
        if clicked_color_index != -1:
            color = self.colors[clicked_color_index]
            menu = QMenu(self)
            menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
            copy_hex_action = menu.addAction(f"Copy Hex: {color.name().upper()}")
            action = menu.exec_(self.mapToGlobal(pos))
            if action == copy_hex_action:
                clipboard = QApplication.clipboard()
                clipboard.setText(color.name().upper())

class CircleBrightnessDialog(QDialog):
    def __init__(self, initialColor=QColor("white"), parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.hueSatDiameter = 150
        self.radius = self.hueSatDiameter // 2
        hF, sF, vF, _ = initialColor.getHsvF()
        self.h = int(hF * 360)
        self.s = sF
        self.v = vF
        self.setFixedSize(280, 280)

        self.colorWheel = QImage(self.hueSatDiameter, self.hueSatDiameter, QImage.Format_ARGB32)
        self._generateColorWheel()

        self.slider = QSlider(Qt.Vertical, self)
        self.slider.setRange(0, 100)
        self.slider.setValue(int(self.v * 100))
        self.slider.setGeometry(self.hueSatDiameter + 20, 10, 20, self.hueSatDiameter)
        self.slider.valueChanged.connect(self.onValueChanged)

        self._updateSliderStyle()

        self.preview_label = QLabel(self)
        self.preview_label.setGeometry(self.hueSatDiameter + 50, 35, 40, 40)
        self.preview_label.setStyleSheet("QLabel { border: 2px solid #FFFFFF; border-radius: 4px; }")
        self._updatePreviewColor()

        self.brightness_label = QLabel(self)
        self.brightness_label.setStyleSheet("color: white; background: transparent;")
        self.brightness_label.setGeometry(self.hueSatDiameter + 50, 10, 40, 20)
        self.brightness_label.setText(f"{int(self.v*100)}%")

        self.hex_input = QLineEdit(self)
        self.hex_input.setGeometry(10, self.hueSatDiameter + 25, 105, 25) 
        self.hex_input.setStyleSheet("""
            QLineEdit { background-color: #000000; color: #FFFFFF; border: 1px solid #444444; border-radius: 4px; padding: 2px 5px; font-family: Consolas, Monaco, monospace; font-size: 12px; }
            QLineEdit:focus { border: 1px solid #00FF00; }
        """)
        self.hex_input.setMaxLength(6)
        self.hex_input.setPlaceholderText("Hex Kodu")
        self.hex_input.textChanged.connect(self.onHexTextChanged)
        self.hex_input.returnPressed.connect(self.onHexEnterPressed)

        self.hex_ok_btn = QPushButton("OK", self)
        self.hex_ok_btn.setGeometry(120, self.hueSatDiameter + 25, 40, 25)
        self.hex_ok_btn.setStyleSheet("""
            QPushButton { background-color: #222; color: #FFFFFF; border: 1px solid #444; border-radius: 4px; font-family: Consolas, Monaco, monospace; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background-color: #4CAF50; border: 1px solid #4CAF50; }
            QPushButton:pressed { background-color: #388E3C; }
        """)
        self.hex_ok_btn.clicked.connect(self.onHexEnterPressed)

        self.hex_label = QLabel(self)
        self.hex_label.setGeometry(165, self.hueSatDiameter + 25, 105, 25)
        self.hex_label.setStyleSheet("""
            QLabel { background-color: #000000; color: #FFFFFF; border: 1px solid #444444; border-radius: 4px; padding: 2px 5px; font-family: Consolas, Monaco, monospace; font-size: 12px; }
        """)
        self.hex_label.setAlignment(Qt.AlignCenter)
        self.hex_label.setText("#" + initialColor.name().upper()[1:])

        self._updateHexFromColor()

    def _updateHexFromColor(self):
        color = QColor.fromHsvF(self.h/360.0, self.s, self.v)
        hex_code = color.name().upper()[1:]  
        self.hex_label.setText("#" + hex_code)
        self.hex_input.setText(hex_code)
        self._updateSliderStyle()
        self._updatePreviewColor()

    def _updateSliderStyle(self):
        hue_color = QColor.fromHsvF(self.h/360.0, 1.0, 1.0)
        hue_hex = hue_color.name()
        self.slider.setStyleSheet(f"""
            QSlider::groove:vertical {{ border: none; width: 4px; background: qlineargradient(x1:0, y1:1, x2:0, y2:0, stop:0 #000000, stop:0.5 {hue_hex}, stop:1 #FFFFFF); margin: 0px; }}
            QSlider::handle:vertical {{ background: {hue_hex}; border: 2px solid #FFFFFF; width: 12px; height: 12px; margin: -6px 0; border-radius: 6px; }}
            QSlider::handle:vertical:hover {{ background: #FFFFFF; border: 2px solid {hue_hex}; }}
        """)

    def _updatePreviewColor(self):
        current_color = QColor.fromHsvF(self.h/360.0, self.s, self.v)
        self.preview_label.setStyleSheet(f"QLabel {{ background-color: {current_color.name()}; border: 2px solid #FFFFFF; border-radius: 4px; }}")

    def onHexTextChanged(self, text):
        self.hex_input.blockSignals(True)
        clean_text = "".join(c for c in text.upper() if c in "0123456789ABCDEF")
        if clean_text != text:
            cursor = self.hex_input.cursorPosition()
            self.hex_input.setText(clean_text)
            self.hex_input.setCursorPosition(cursor)
        self.hex_input.blockSignals(False)

    def onHexEnterPressed(self):
        hex_text = self.hex_input.text().strip()
        if len(hex_text) == 6:
            try:
                color = QColor("#" + hex_text)
                if color.isValid():
                    hF, sF, vF, _ = color.getHsvF()
                    self.h = int(hF * 360)
                    self.s = sF
                    self.v = vF
                    self.slider.setValue(int(self.v * 100))
                    self.hex_label.setText("#" + hex_text.upper())
                    self.update()
            except Exception:
                pass

    def _handleCtrlV(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        clean_hex = text.replace("#", "").upper()
        clean_hex = "".join(c for c in clean_hex if c in "0123456789ABCDEF")
        if len(clean_hex) == 6:
            try:
                color = QColor("#" + clean_hex)
                if color.isValid():
                    hF, sF, vF, _ = color.getHsvF()
                    self.h = int(hF * 360)
                    self.s = sF
                    self.v = vF
                    self.slider.setValue(int(self.v * 100))
                    self.hex_input.setText(clean_hex)
                    self.hex_label.setText("#" + clean_hex)
                    self.update()
            except Exception:
                pass

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_V:
            self._handleCtrlV()
            event.accept()
            return
        super().keyPressEvent(event)
        
    def _generateColorWheel(self):
        center = self.radius
        for y in range(self.hueSatDiameter):
            for x in range(self.hueSatDiameter):
                dx = x - center
                dy = y - center
                r = math.sqrt(dx*dx + dy*dy)
                if r <= self.radius:
                    hue = (math.degrees(math.atan2(dy, dx)) + 360) % 360
                    sat = r / self.radius
                    c = QColor.fromHsvF(hue/360.0, sat, 1.0)
                    self.colorWheel.setPixelColor(x, y, c)
                else:
                    self.colorWheel.setPixelColor(x, y, Qt.transparent)
                
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(30, 30, 30, 220))
        circleX, circleY = 10, 10
        painter.drawImage(circleX, circleY, self.colorWheel)
        hueRad = math.radians(self.h)
        satR = self.s * self.radius
        selX = circleX + self.radius + satR * math.cos(hueRad)
        selY = circleY + self.radius + satR * math.sin(hueRad)
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(Qt.white)
        painter.drawEllipse(QPoint(int(selX), int(selY)), 5, 5)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._pickHueSat(event.pos()):
                self.accept()
            else:
                self.update()
        else:
            self.accept()
        
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if self._pickHueSat(event.pos()):
                self.update()
            
    def _pickHueSat(self, pos):
        x, y = pos.x() - 10, pos.y() - 10
        if 0 <= x < self.hueSatDiameter and 0 <= y < self.hueSatDiameter:
            dx = x - self.radius
            dy = y - self.radius
            r = math.sqrt(dx*dx + dy*dy)
            if r <= self.radius:
                angle = (math.degrees(math.atan2(dy, dx)) + 360) % 360
                self.h = angle
                self.s = r / self.radius
                color = QColor.fromHsvF(self.h/360.0, self.s, self.v)
                hex_code = color.name().upper()[1:]
                self.hex_label.setText("#" + hex_code)
                self.hex_input.setText(hex_code)
                self._updateSliderStyle()
                self._updatePreviewColor()
                return True
        return False
        
    def onValueChanged(self, val):
        self.v = val / 100.0
        self.brightness_label.setText(f"{val}%")
        color = QColor.fromHsvF(self.h/360.0, self.s, self.v)
        hex_code = color.name().upper()[1:]
        self.hex_label.setText("#" + hex_code)
        self.hex_input.setText(hex_code)
        self._updatePreviewColor()
        self.update()
        
    def getSelectedColor(self):
        return QColor.fromHsvF(self.h/360.0, self.s, self.v)
    
    def focusOutEvent(self, event):
        self.accept()
        super().focusOutEvent(event)


# ===========================================================================
# BÖLÜM: GERÇEK KATMAN SİSTEMİ
# ===========================================================================
# Kavram - Gerçek katman sistemi
#
# Eski sistem: tek bir birleşik görüntü (image) + her işlemde TÜM çizim kayıtlarının
# yeniden oynatılması (replay). Eraser / katman değişimi / görünürlük gibi işlemlerde
# bu yüzden kasıyordu.
#
# Yeni sistem:
#   * Her katmanın kendi QImage'ı vardır (ARGB32_Premultiplied).
#   * DrawingArea.image artık AKTİF KATMANIN görüntüsüdür (property). Bu yüzden
#     mevcut tüm fırça/dolgu/silgi kodu değişmeden yalnız aktif katmana çizer.
#   * Görünürlük, opaklık, sıra, blend modu değişimi sadece yeniden boyamadır (replay yok).
#   * Geri alma yalnız değişen katmanı saklar (tüm sayfayı değil).
#   * Katman yapısı (isim/sıra/görünürlük...) tüm sayfalarda ortaktır; her sayfa
#     kendi katman görüntülerini s{n}_L{id}.png olarak önbellekte tutar.

LAYER_FORMAT = QImage.Format_ARGB32_Premultiplied

BLEND_MODES = [
    ("normal", "Normal", QPainter.CompositionMode_SourceOver),
    ("multiply", "Çarpma", QPainter.CompositionMode_Multiply),
    ("screen", "Ekran", QPainter.CompositionMode_Screen),
    ("overlay", "Bindirme", QPainter.CompositionMode_Overlay),
    ("darken", "Koyulaştır", QPainter.CompositionMode_Darken),
    ("lighten", "Açıklaştır", QPainter.CompositionMode_Lighten),
    ("add", "Ekle", QPainter.CompositionMode_Plus),
]
_BLEND_MAP = {k: m for k, _n, m in BLEND_MODES}


def blend_to_mode(key):
    return _BLEND_MAP.get(key, QPainter.CompositionMode_SourceOver)


def new_layer_image(w, h):
    img = QImage(w, h, LAYER_FORMAT)
    img.fill(Qt.transparent)
    return img


def to_layer_format(img):
    return img if img.format() == LAYER_FORMAT else img.convertToFormat(LAYER_FORMAT)


def fit_to_canvas(img, w, h):
    """Görüntüyü katman formatına çevirir; boyut farklıysa (0,0)'a hizalayıp kırpar/genişletir."""
    img = to_layer_format(img)
    if img.width() == w and img.height() == h:
        return img
    out = new_layer_image(w, h)
    p = QPainter(out)
    p.drawImage(0, 0, img)
    p.end()
    return out


# ---------------------------------------------------------------------------
# Katman ve katman yığını
# ---------------------------------------------------------------------------
class Layer:
    def __init__(self, lid, name, w, h, image=None):
        self.id = lid
        self.name = name
        self.visible = True
        self.opacity = 1.0
        self.blend = "normal"
        self.locked = False
        self._image = fit_to_canvas(image, w, h) if image is not None else new_layer_image(w, h)
        self._pixmap = None
        self.saved_key = None

    # -- görüntü / pixmap önbelleği
    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = to_layer_format(value)
        self._pixmap = None

    def get_pixmap(self):
        if self._pixmap is None:
            self._pixmap = QPixmap.fromImage(self._image)
        return self._pixmap

    def refresh_pixmap(self):
        self._pixmap = QPixmap.fromImage(self._image)

    def invalidate(self):
        self._pixmap = None

    # -- diske yazma takibi
    def touch(self):
        self.saved_key = None

    def mark_saved(self):
        self.saved_key = self._image.cacheKey()

    def is_dirty(self):
        return self.saved_key is None or self.saved_key != self._image.cacheKey()

    def composition_mode(self):
        return blend_to_mode(self.blend)

    def meta(self):
        return {"id": self.id, "name": self.name, "visible": self.visible,
                "opacity": round(self.opacity, 4), "blend": self.blend, "locked": self.locked}

    def apply_meta(self, d):
        self.name = d.get("name", self.name)
        self.visible = bool(d.get("visible", True))
        self.opacity = float(d.get("opacity", 1.0))
        self.blend = d.get("blend", "normal")
        self.locked = bool(d.get("locked", False))


class LayerStack:
    """Alttan üste sıralı katman listesi."""

    def __init__(self, w, h, names=("Eskiz", "Çizim", "5", "4", "3", "2", "1"), active="Çizim"):
        self.w = w
        self.h = h
        self.layers = []
        self._next_id = 1
        self.active = None
        for n in names:
            self.add(n)
        self.active = self.by_name(active) or self.layers[-1]

    # -- erişim
    def by_id(self, lid):
        for l in self.layers:
            if l.id == lid:
                return l
        return None

    def by_name(self, name):
        for l in self.layers:
            if l.name == name:
                return l
        return None

    def index_of(self, layer):
        return self.layers.index(layer)

    def unique_name(self, name, ignore=None):
        existing = {l.name for l in self.layers if l is not ignore}
        if name not in existing:
            return name
        i = 2
        while f"{name} {i}" in existing:
            i += 1
        return f"{name} {i}"

    # -- değişiklik
    def add(self, name=None, index=None, lid=None, image=None):
        if lid is None:
            lid = self._next_id
        self._next_id = max(self._next_id, lid + 1)
        name = self.unique_name(name or f"Katman {lid}")
        layer = Layer(lid, name, self.w, self.h, image)
        if index is None or index >= len(self.layers):
            self.layers.append(layer)
        else:
            self.layers.insert(max(0, index), layer)
        return layer

    def remove(self, layer):
        if len(self.layers) <= 1 or layer not in self.layers:
            return False
        i = self.layers.index(layer)
        self.layers.pop(i)
        if self.active is layer:
            self.active = self.layers[min(i, len(self.layers) - 1)]
        return True

    def duplicate(self, layer):
        i = self.index_of(layer)
        new = self.add(layer.name + " kopya", index=i + 1, image=layer.image.copy())
        new.visible, new.opacity, new.blend = layer.visible, layer.opacity, layer.blend
        new.touch()
        return new

    def merge_down(self, layer):
        i = self.index_of(layer)
        if i <= 0:
            return None
        below = self.layers[i - 1]
        if layer.visible:
            p = QPainter(below.image)
            p.setOpacity(layer.opacity)
            p.setCompositionMode(layer.composition_mode())
            p.drawImage(0, 0, layer.image)
            p.end()
        below.invalidate()
        below.touch()
        self.layers.pop(i)
        self.active = below
        return below

    def move(self, layer, delta):
        i = self.index_of(layer)
        j = i + delta
        if j < 0 or j >= len(self.layers):
            return False
        self.layers[i], self.layers[j] = self.layers[j], self.layers[i]
        return True

    def resize(self, w, h):
        self.w, self.h = w, h
        for l in self.layers:
            l.image = fit_to_canvas(l.image, w, h)
            l.touch()

    # -- meta / anlık görüntü
    def export_meta(self):
        return [l.meta() for l in self.layers]

    def import_meta(self, meta_list, active_id=None):
        """Yapıyı verilen meta'dan kurar (görüntüler boş başlar)."""
        self.layers = []
        self._next_id = 1
        for d in meta_list:
            l = self.add(d.get("name", "Katman"), lid=int(d["id"]))
            l.apply_meta(d)
        if not self.layers:
            self.add("Çizim")
        self.active = self.by_id(active_id) or self.layers[-1]

    def snapshot_full(self):
        return {"kind": "full",
                "layers": [(l.meta(), l.image.copy()) for l in self.layers],
                "active": self.active.id, "next": self._next_id}

    def restore_full(self, snap):
        self.layers = []
        for meta, img in snap["layers"]:
            l = Layer(meta["id"], meta["name"], self.w, self.h, img)
            l.apply_meta(meta)
            l.touch()
            self.layers.append(l)
        self._next_id = max(self._next_id, snap.get("next", 1))
        self.active = self.by_id(snap["active"]) or self.layers[-1]


def meta_signature(meta):
    return tuple((m["id"], bool(m.get("visible", True)), round(float(m.get("opacity", 1.0)), 3),
                  m.get("blend", "normal")) for m in meta)


# ---------------------------------------------------------------------------
# Sayfa dosyaları (önbellek klasörü)   -  n = 1 tabanlı sayfa numarası
# ---------------------------------------------------------------------------
def layer_path(cache_dir, page_idx, lid):
    return os.path.join(cache_dir, f"s{page_idx + 1}_L{lid}.png")


def page_files(cache_dir, n):
    out = []
    try:
        names = os.listdir(cache_dir)
    except OSError:
        return out
    for name in names:
        if (name == f"s{n}.png" or name == f"s{n}_elements.json"
                or (name.startswith(f"s{n}_L") and name.endswith(".png"))):
            out.append(name)
    return out


def delete_page_files(cache_dir, n):
    for name in page_files(cache_dir, n):
        try:
            os.remove(os.path.join(cache_dir, name))
        except OSError:
            pass


def copy_page_files(cache_dir, src_n, dst_n):
    delete_page_files(cache_dir, dst_n)
    for name in page_files(cache_dir, src_n):
        suffix = name[len(f"s{src_n}"):]
        shutil.copyfile(os.path.join(cache_dir, name), os.path.join(cache_dir, f"s{dst_n}{suffix}"))


def reorder_page_files(cache_dir, order):
    """order[k] = eski 1-tabanlı sayfa no; yeni konum k+1'e taşınır."""
    for new_n, old_n in enumerate(order, start=1):
        for name in page_files(cache_dir, old_n):
            suffix = name[len(f"s{old_n}"):]
            os.replace(os.path.join(cache_dir, name), os.path.join(cache_dir, f"tmp_{new_n}{suffix}"))
    for name in os.listdir(cache_dir):
        if name.startswith("tmp_"):
            rest = name[4:]
            n_str = rest.split("_")[0].split(".")[0]
            suffix = rest[len(n_str):]
            os.replace(os.path.join(cache_dir, name), os.path.join(cache_dir, f"s{n_str}{suffix}"))


def save_page_layers(cache_dir, page_idx, stack, force=False):
    """Değişen (veya dosyası olmayan) katmanları diske yazar."""
    for l in stack.layers:
        path = layer_path(cache_dir, page_idx, l.id)
        if force or l.is_dirty() or not os.path.isfile(path):
            if not l.image.save(path, "PNG"):
                raise IOError(f"Katman kaydedilemedi: {path}")
            l.mark_saved()


def load_page_layers(cache_dir, page_idx, stack, legacy_layer_name="Çizim"):
    """Sayfanın katman görüntülerini yükler. Katman dosyası yoksa eski s{n}.png'yi
    (tek parça çizim) 'Çizim' katmanına alır."""
    any_found = False
    for l in stack.layers:
        path = layer_path(cache_dir, page_idx, l.id)
        img = QImage(path) if os.path.isfile(path) else QImage()
        if not img.isNull():
            any_found = True
            l.image = fit_to_canvas(img, stack.w, stack.h)
            l.mark_saved()
        else:
            l.image = new_layer_image(stack.w, stack.h)
            l.mark_saved()
    if not any_found:
        legacy = os.path.join(cache_dir, f"s{page_idx + 1}.png")
        if os.path.isfile(legacy):
            img = QImage(legacy)
            if not img.isNull():
                target = stack.by_name(legacy_layer_name) or stack.layers[-1]
                target.image = fit_to_canvas(img, stack.w, stack.h)
                target.touch()


def composite_images(items, w, h, bg=None):
    """items: [(QImage, visible, opacity, blend)] alttan üste."""
    out = QImage(w, h, LAYER_FORMAT)
    if bg is None:
        out.fill(Qt.transparent)
    else:
        out.fill(bg)
    p = QPainter(out)
    for img, visible, opacity, blend in items:
        if not visible or img is None or img.isNull():
            continue
        p.setOpacity(opacity)
        p.setCompositionMode(blend_to_mode(blend))
        p.drawImage(0, 0, img)
    p.end()
    return out


def composite_page(cache_dir, page_idx, meta, w, h, bg=None):
    """Önbellekteki katman dosyalarından sayfayı birleştirir. İş parçacığında güvenle çağrılabilir
    (yalnızca QImage/QPainter kullanır)."""
    items = []
    found = False
    for m in meta:
        path = layer_path(cache_dir, page_idx, m["id"])
        if not os.path.isfile(path):
            continue
        found = True
        if not m.get("visible", True):
            continue
        img = QImage(path)
        if img.isNull():
            continue
        items.append((img, True, float(m.get("opacity", 1.0)), m.get("blend", "normal")))
    if not found:
        legacy = os.path.join(cache_dir, f"s{page_idx + 1}.png")
        if os.path.isfile(legacy):
            img = QImage(legacy)
            if not img.isNull():
                items.append((img, True, 1.0, "normal"))
    return composite_images(items, w, h, bg)


def page_signature(cache_dir, page_idx, meta):
    """Sayfanın dosya değişim imzası (önbellek anahtarı)."""
    parts = []
    for m in meta:
        try:
            parts.append(os.stat(layer_path(cache_dir, page_idx, m["id"])).st_mtime_ns)
        except OSError:
            parts.append(0)
    try:
        parts.append(os.stat(os.path.join(cache_dir, f"s{page_idx + 1}.png")).st_mtime_ns)
    except OSError:
        parts.append(0)
    return (tuple(parts), meta_signature(meta))


# ---------------------------------------------------------------------------
# DrawingArea için karışım sınıfı (mixin)
# ---------------------------------------------------------------------------
class LayerAreaMixin:
    MAX_UNDO_REDO_STEPS = 30

    # -- başlatma
    def initLayers(self, w, h):
        self.layer_stack = LayerStack(w, h)
        self._painted_count = 0
        self._actively_modifying = False

    # -- uyumluluk özellikleri: mevcut kod self.image / current_layer_name kullanır
    @property
    def image(self):
        return self.layer_stack.active.image

    @image.setter
    def image(self, value):
        self.layer_stack.active.image = value

    @property
    def current_layer_name(self):
        return self.layer_stack.active.name

    @current_layer_name.setter
    def current_layer_name(self, name):
        self.setActiveLayer(name=name)

    @property
    def layer_order(self):
        return [l.name for l in self.layer_stack.layers]

    # -- durum
    def isLayerEditable(self):
        l = self.layer_stack.active
        return l.visible and not l.locked

    def syncPaintedCount(self):
        self._painted_count = len(self.drawing_elements)

    def _append_live(self, element):
        """Raster'a zaten canlı çizilmiş bir kaydı günlüğe ekler (tekrar çizilmez)."""
        self.drawing_elements.append(element)
        self._painted_count = len(self.drawing_elements)

    def _structure_changed(self):
        if self.parent():
            self.parent().is_project_modified = True
        self.update()
        self.layersChanged.emit()
        self.contentChanged.emit()

    # -- görüntü / pixmap
    def commitImageToPixmap(self):
        layer = self.layer_stack.active
        layer.refresh_pixmap()
        layer.touch()
        self._actively_modifying = False

    def _paint_layers(self, painter, source_rect):
        st = self.layer_stack
        order = list(st.layers)
        if getattr(self, "force_active_layer_bottom", False) and st.active in order:
            order.remove(st.active)
            order.insert(0, st.active)
        for layer in order:
            if not layer.visible:
                continue
            painter.save()
            painter.setOpacity(layer.opacity)
            painter.setCompositionMode(layer.composition_mode())
            if layer is st.active and (self._actively_modifying or layer._pixmap is None):
                painter.drawImage(source_rect, layer.image, source_rect)
            else:
                painter.drawPixmap(source_rect, layer.get_pixmap(), source_rect)
            painter.restore()

    # -- sayfa dosyaları
    def loadLayersFromCache(self, cache_dir, page_idx):
        load_page_layers(cache_dir, page_idx, self.layer_stack)
        for l in self.layer_stack.layers:
            l.invalidate()
        self._actively_modifying = False
        self.update()

    def saveLayersToCache(self, cache_dir, page_idx):
        save_page_layers(cache_dir, page_idx, self.layer_stack)

    def flattenCurrent(self, bg=None):
        st = self.layer_stack
        return composite_images([(l.image, l.visible, l.opacity, l.blend) for l in st.layers], st.w, st.h, bg)

    # -- geri al / yinele (yalnız değişen katmanı saklar, kopya sayısı düşük)
    def _snapshot(self, full):
        st = self.layer_stack
        if full:
            return st.snapshot_full()
        return {"kind": "layer", "id": st.active.id, "image": st.active.image.copy()}

    def _snapshot_like(self, snap):
        st = self.layer_stack
        if snap["kind"] == "full":
            return st.snapshot_full()
        layer = st.by_id(snap["id"])
        if layer is None:
            return {"kind": "layer", "id": snap["id"], "image": None}
        return {"kind": "layer", "id": layer.id, "image": layer.image.copy()}

    def saveStateForUndo(self, deep_copy=False, all_layers=False):
        if self.parent():
            self.parent().is_project_modified = True
        elements_copy = copy.deepcopy(self.drawing_elements) if deep_copy else self.drawing_elements[:]
        self.undo_stack.append((elements_copy, self._snapshot(deep_copy or all_layers)))
        if len(self.undo_stack) > self.MAX_UNDO_REDO_STEPS:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _apply_history(self, source, target):
        if not source:
            return
        elements, snap = source.pop()
        current = self._snapshot_like(snap)
        target.append((self.drawing_elements, current))
        if len(target) > self.MAX_UNDO_REDO_STEPS:
            target.pop(0)
        self.drawing_elements = elements
        self._painted_count = len(elements)
        st = self.layer_stack
        if snap["kind"] == "full":
            st.restore_full(snap)
        else:
            layer = st.by_id(snap["id"])
            if layer is not None and snap["image"] is not None:
                layer.image = snap["image"]
                layer.touch()
        self._actively_modifying = False
        self.commitImageToPixmap()
        if hasattr(self, "onHistoryApplied"):
            self.onHistoryApplied()
        if self.parent():
            self.parent().is_project_modified = True
        self.update()
        self.layersChanged.emit()
        self.contentChanged.emit()

    def undo(self):
        self._apply_history(self.undo_stack, self.redo_stack)

    def redo(self):
        self._apply_history(self.redo_stack, self.undo_stack)

    # -- çizim kayıtlarını rasterlaştırma
    def _cached_b64_image(self, b64):
        key = (len(b64), b64[:40], b64[-40:])
        img = self.image_cache.get(key)
        if img is None:
            img = QImage()
            img.loadFromData(base64.b64decode(b64), "PNG")
            self.image_cache[key] = img
        return img

    def updateImageFromElements(self, full=False):
        """Varsayılan: yalnızca henüz rasterlaştırılmamış (yeni) kayıtları ilgili katmana çizer.
        full=True: tüm kayıtları yeniden çizer (renk değiştirme gibi işlemler için)."""
        elems = self.drawing_elements if full else self.drawing_elements[self._painted_count:]
        if elems:
            self._render_elements(elems)
        self._painted_count = len(self.drawing_elements)
        self.commitImageToPixmap()
        self.update()
        self.contentChanged.emit()

    # -- katman işlemleri
    def setActiveLayer(self, layer_id=None, name=None):
        st = self.layer_stack
        target = st.by_id(layer_id) if layer_id is not None else st.by_name(name)
        if target is None or target is st.active:
            return
        self.commitImageToPixmap()
        st.active = target
        self.update()
        self.layersChanged.emit()

    def addLayer(self, name=None):
        self.saveStateForUndo(all_layers=True)
        st = self.layer_stack
        self.commitImageToPixmap()
        layer = st.add(name, index=st.index_of(st.active) + 1)
        st.active = layer
        self._structure_changed()
        return layer

    def removeLayer(self, layer=None):
        st = self.layer_stack
        layer = layer or st.active
        if len(st.layers) <= 1:
            return False
        self.saveStateForUndo(all_layers=True)
        ok = st.remove(layer)
        self._structure_changed()
        return ok

    def duplicateLayer(self, layer=None):
        st = self.layer_stack
        layer = layer or st.active
        self.saveStateForUndo(all_layers=True)
        new = st.duplicate(layer)
        st.active = new
        self._structure_changed()

    def mergeLayerDown(self, layer=None):
        st = self.layer_stack
        layer = layer or st.active
        if st.index_of(layer) <= 0:
            return False
        self.saveStateForUndo(all_layers=True)
        st.merge_down(layer)
        self.commitImageToPixmap()
        self._structure_changed()
        return True

    def moveLayer(self, layer, delta):
        st = self.layer_stack
        if not (0 <= st.index_of(layer) + delta < len(st.layers)):
            return False
        self.saveStateForUndo(all_layers=True)
        st.move(layer, delta)
        self._structure_changed()
        return True

    def renameLayer(self, layer, new_name):
        new_name = (new_name or "").strip()
        if not new_name or new_name == layer.name:
            return
        st = self.layer_stack
        new_name = st.unique_name(new_name, ignore=layer)
        old = layer.name
        for el in self.drawing_elements:
            if el.get("layer") == old:
                el["layer"] = new_name
        layer.name = new_name
        self._structure_changed()

    def setLayerVisible(self, layer, visible):
        layer.visible = bool(visible)
        self._structure_changed()

    def setLayerLocked(self, layer, locked):
        layer.locked = bool(locked)
        self.layersChanged.emit()

    def setLayerOpacity(self, layer, opacity):
        layer.opacity = max(0.0, min(1.0, float(opacity)))
        if self.parent():
            self.parent().is_project_modified = True
        self.update()
        self.contentChanged.emit()

    def setLayerBlend(self, layer, key):
        layer.blend = key
        if self.parent():
            self.parent().is_project_modified = True
        self.update()
        self.contentChanged.emit()

    def setLayerOrder(self, names_ordered):
        st = self.layer_stack
        by_name = {l.name: l for l in st.layers}
        new_list = [by_name[n] for n in names_ordered if n in by_name]
        for l in st.layers:
            if l not in new_list:
                new_list.append(l)
        st.layers = new_list
        self._structure_changed()

    def setLayerVisibility(self, layer_name, visible):
        l = self.layer_stack.by_name(layer_name)
        if l:
            self.setLayerVisible(l, visible)

    def clear(self):
        """Sayfadaki tüm katmanları temizler."""
        self.drawing_elements.clear()
        self._painted_count = 0
        self.undo_stack.clear()
        self.redo_stack.clear()
        if self.parent():
            self.parent().is_project_modified = True
        for l in self.layer_stack.layers:
            l.image = new_layer_image(self.layer_stack.w, self.layer_stack.h)
            l.touch()
        self.commitImageToPixmap()
        self.update()
        self.contentChanged.emit()


# ---------------------------------------------------------------------------
# Katman paneli
# ---------------------------------------------------------------------------
_PANEL_CSS = """
QFrame#layerPanel { background-color: #262626; border-left: 2px solid #555; }
QLabel { color: #ddd; background: transparent; }
QListWidget { background-color: #1e1e1e; border: 1px solid #444; border-radius: 6px; outline: none; color: #eee; }
QListWidget::item { border-bottom: 1px solid #2c2c2c; }
QListWidget::item:selected { background-color: #3a4a66; }
QPushButton { background-color: #333; color: #eee; border: 1px solid #555; border-radius: 6px; padding: 3px 6px; }
QPushButton:hover { background-color: #444; }
QPushButton:disabled { color: #777; border-color: #3a3a3a; }
QToolButton { background: transparent; border: none; }
QToolButton:hover { background-color: #444; border-radius: 4px; }
QComboBox { background-color: #333; color: #eee; border: 1px solid #555; border-radius: 6px; padding: 2px 6px; }
QComboBox QAbstractItemView { background-color: #333; color: #eee; selection-background-color: #556; }
QSlider::groove:horizontal { height: 4px; background: #555; border-radius: 2px; }
QSlider::handle:horizontal { background: #ddd; width: 12px; margin: -5px 0; border-radius: 6px; }
"""


class _LayerRow(QWidget):
    def __init__(self, layer, on_eye, on_lock):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(4, 2, 4, 2)
        h.setSpacing(3)
        self.eye = SvgIconButton(SVG_EYE_OPEN if layer.visible else SVG_EYE_CLOSED,
                                 "#eeeeee" if layer.visible else "#777777", size=28, icon_px=19)
        self.eye.setToolTip("Katmanı göster / gizle")
        self.eye.clicked.connect(lambda: on_eye(layer))
        self.lock = SvgIconButton(SVG_LOCK if layer.locked else SVG_UNLOCK,
                                  "#ffb347" if layer.locked else "#777777", size=28, icon_px=17)
        self.lock.setToolTip("Katmanı kilitle / kilidi aç")
        self.lock.clicked.connect(lambda: on_lock(layer))
        self.label = QLabel(layer.name)
        self.label.setStyleSheet("color: %s; font-size: 13px;" % ("#eeeeee" if layer.visible else "#777777"))
        h.addWidget(self.eye)
        h.addWidget(self.lock)
        h.addWidget(self.label, 1)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)


class LayerEditDialog(QDialog):
    """Katmanı düzenle: ad, görünürlük, kilit, opaklık, karışım modu."""

    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Katmanı Düzenle")
        self.setMinimumWidth(320)
        self.setStyleSheet(_PANEL_CSS + "QDialog { background-color: #2b2b2b; } QLineEdit { background-color: #3a3a3a; "
                           "color: #eee; border: 1px solid #555; border-radius: 5px; padding: 3px 6px; } QCheckBox { color: #eee; }")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Katman adı"))
        self.name = QLineEdit(layer.name)
        self.name.selectAll()
        lay.addWidget(self.name)
        self.visible = QCheckBox("Görünür")
        self.visible.setChecked(layer.visible)
        self.locked = QCheckBox("Kilitli (çizilemez)")
        self.locked.setChecked(layer.locked)
        lay.addWidget(self.visible)
        lay.addWidget(self.locked)
        self.op_label = QLabel()
        lay.addWidget(self.op_label)
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.setValue(int(round(layer.opacity * 100)))
        self.opacity.valueChanged.connect(lambda v: self.op_label.setText(f"Opaklık: {v}%"))
        self.op_label.setText(f"Opaklık: {self.opacity.value()}%")
        lay.addWidget(self.opacity)
        lay.addWidget(QLabel("Karışım modu"))
        self.blend = QComboBox()
        for key, label, _m in BLEND_MODES:
            self.blend.addItem(label, key)
        self.blend.setCurrentIndex(max(0, self.blend.findData(layer.blend)))
        lay.addWidget(self.blend)
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("İptal")
        ok = QPushButton("Tamam")
        ok.setDefault(True)
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)


class LayerPanel(QFrame):
    def __init__(self, area, parent=None):
        super().__init__(parent)
        self.setObjectName("layerPanel")
        self.area = area
        self._building = False
        self._refresh_pending = False
        self.setFixedWidth(230)
        self.setStyleSheet(_PANEL_CSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        title = QLabel("Katmanlar")
        title.setStyleSheet("font-weight: bold; font-size: 13px; color: #fff;")
        root.addWidget(title)

        self.list = QListWidget()
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list.currentRowChanged.connect(self._on_row_changed)
        self.list.itemDoubleClicked.connect(self._rename)
        root.addWidget(self.list, 1)

        self.opacity_label = QLabel("Opaklık: 100%")
        root.addWidget(self.opacity_label)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self._on_opacity)
        root.addWidget(self.opacity_slider)

        self.blend_combo = QComboBox()
        for key, label, _m in BLEND_MODES:
            self.blend_combo.addItem(label, key)
        self.blend_combo.currentIndexChanged.connect(self._on_blend)
        root.addWidget(self.blend_combo)

        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        self.btn_add = self._btn("+ Yeni", "Yeni katman (aktifin üstüne)", self._add)
        self.btn_edit = self._btn("Düzenle", "Katmanı düzenle: ad, görünürlük, kilit, opaklık, karışım", self._edit)
        self.btn_merge = self._btn("Birleştir", "Alttaki katmanla birleştir", self._merge)
        self.btn_del = self._btn("Sil", "Katmanı sil", self._delete)
        self.btn_up = self._btn("▲", "Yukarı taşı", lambda: self._move(+1))
        self.btn_down = self._btn("▼", "Aşağı taşı", lambda: self._move(-1))
        for b in (self.btn_add, self.btn_edit, self.btn_up):
            row1.addWidget(b)
        for b in (self.btn_merge, self.btn_del, self.btn_down):
            row2.addWidget(b)
        root.addLayout(row1)
        root.addLayout(row2)

        area.layersChanged.connect(self._schedule_refresh)
        self.refresh()

    def _btn(self, text, tip, fn):
        b = QPushButton(text)
        b.setToolTip(tip)
        b.setFixedHeight(26)
        b.clicked.connect(fn)
        return b

    # -- yenileme (sinyal içinden liste silmemek için ertelenir)
    def _schedule_refresh(self):
        if self._refresh_pending:
            return
        self._refresh_pending = True
        QTimer.singleShot(0, self._do_refresh)

    def _do_refresh(self):
        self._refresh_pending = False
        self.refresh()

    def refresh(self):
        st = self.area.layer_stack
        self._building = True
        try:
            self.list.clear()
            active_row = 0
            for row, layer in enumerate(reversed(st.layers)):
                item = QListWidgetItem()
                item.setData(Qt.UserRole, layer.id)
                item.setSizeHint(QSize(100, 32))
                self.list.addItem(item)
                self.list.setItemWidget(item, _LayerRow(layer, self._toggle_eye, self._toggle_lock))
                if layer is st.active:
                    active_row = row
            self.list.setCurrentRow(active_row)
            a = st.active
            self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(int(round(a.opacity * 100)))
            self.opacity_slider.blockSignals(False)
            self.opacity_label.setText(f"Opaklık: {int(round(a.opacity * 100))}%")
            self.blend_combo.blockSignals(True)
            idx = self.blend_combo.findData(a.blend)
            self.blend_combo.setCurrentIndex(max(0, idx))
            self.blend_combo.blockSignals(False)
            n = len(st.layers)
            i = st.index_of(a)
            self.btn_del.setEnabled(n > 1)
            self.btn_merge.setEnabled(i > 0)
            self.btn_up.setEnabled(i < n - 1)
            self.btn_down.setEnabled(i > 0)
        finally:
            self._building = False

    # -- olaylar
    def _on_row_changed(self, row):
        if self._building or row < 0:
            return
        item = self.list.item(row)
        if item is not None:
            self.area.setActiveLayer(layer_id=item.data(Qt.UserRole))

    def _toggle_eye(self, layer):
        self.area.setLayerVisible(layer, not layer.visible)

    def _toggle_lock(self, layer):
        self.area.setLayerLocked(layer, not layer.locked)

    def _on_opacity(self, v):
        if self._building:
            return
        self.opacity_label.setText(f"Opaklık: {v}%")
        self.area.setLayerOpacity(self.area.layer_stack.active, v / 100.0)

    def _on_blend(self, _i):
        if self._building:
            return
        self.area.setLayerBlend(self.area.layer_stack.active, self.blend_combo.currentData())

    def _rename(self, item):
        layer = self.area.layer_stack.by_id(item.data(Qt.UserRole))
        if layer is not None:
            self._edit_layer(layer)

    def _edit(self):
        self._edit_layer(self.area.layer_stack.active)

    def _edit_layer(self, layer):
        dlg = LayerEditDialog(layer, self)
        if dlg.exec_() != QDialog.Accepted:
            return
        self.area.renameLayer(layer, dlg.name.text())
        layer.visible = dlg.visible.isChecked()
        layer.locked = dlg.locked.isChecked()
        layer.opacity = dlg.opacity.value() / 100.0
        layer.blend = dlg.blend.currentData()
        self.area._structure_changed()

    def _add(self):
        self.area.addLayer()

    def _merge(self):
        self.area.mergeLayerDown()

    def _delete(self):
        st = self.area.layer_stack
        if len(st.layers) <= 1:
            return
        r = QMessageBox.question(self, "Katmanı Sil", f"'{st.active.name}' katmanı tüm kareler için silinsin mi?",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if r == QMessageBox.Yes:
            self.area.removeLayer()

    def _move(self, delta):
        self.area.moveLayer(self.area.layer_stack.active, delta)


def move_page_files(cache_dir, src_n, dst_n):
    """src sayfasının tüm dosyalarını dst numarasına taşır (dst önce temizlenir)."""
    delete_page_files(cache_dir, dst_n)
    for name in page_files(cache_dir, src_n):
        suffix = name[len(f"s{src_n}"):]
        os.replace(os.path.join(cache_dir, name), os.path.join(cache_dir, f"s{dst_n}{suffix}"))


# ===========================================================================
# BÖLÜM: S MODU (PİKSEL SEÇİMİ) + ANAHTAR KARE YARDIMCILARI
# ===========================================================================
# Kavram - S modu (piksel seçimi) + iki mod için ortak anahtar kare (keyframe) yardımcıları
#
# S modu (piksel seçimi):
#   Sürükle = serbest seçim, Shift+sürükle = dikdörtgen seçim (noktalı çizgi).
#   G = taşı, S = büyüt/küçült, R = döndür   (sol tık onayla, Esc / sağ tık iptal; G'de X/Y eksen kısıtı)
#   D = seçimi başka kareye kopyala,  Ctrl+D = aradaki kareleri otomatik doldur
#
# A modu (nokta düzenleme) için bkz. drawing_points.py - aynı kısayollar, aynı D / Ctrl+D mantığı.


# ---------------------------------------------------------------------------
# Ortak yardımcılar (S ve A modu kullanır)
# ---------------------------------------------------------------------------
def bleach_alpha(mask):
    """Maskedeki kısmi saydamlıkları (kenar yumuşatma) güçlendirir; silerken hayalet halka kalmasın."""
    src = mask.copy()
    p = QPainter(mask)
    p.setCompositionMode(QPainter.CompositionMode_Plus)
    for _ in range(3):
        p.drawImage(0, 0, src)
    p.end()


def erase_mask(img, mask):
    """mask'in dolu olduğu yerleri img'den siler."""
    bleach_alpha(mask)
    p = QPainter(img)
    p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
    p.drawImage(0, 0, mask)
    p.end()


def erase_elements(area, img, elements):
    """Çizim kayıtlarının raster karşılığını img'den siler."""
    if not elements:
        return
    mask = new_layer_image(img.width(), img.height())
    area._render_group(mask, elements)
    erase_mask(img, mask)


def edit_layer_file(win, page_idx, layer_id, image_fn):
    """Bir karenin bir katman dosyasını diskte düzenler (kare yüklü olmasa da). image_fn(QImage) görüntüyü değiştirir."""
    st = win.drawing_area.layer_stack
    cache = win.drawing_cache_dir
    path = layer_path(cache, page_idx, layer_id)

    # Eski tek parça dosyası olan karede içeriği kaybetmemek için önce katman dosyasına taşı
    legacy = os.path.join(cache, f"s{page_idx + 1}.png")
    has_layer_files = any(os.path.isfile(layer_path(cache, page_idx, l.id)) for l in st.layers)
    if not has_layer_files and os.path.isfile(legacy):
        target = st.by_name("Çizim") or st.layers[-1]
        shutil.copyfile(legacy, layer_path(cache, page_idx, target.id))

    img = QImage(path) if os.path.isfile(path) else QImage()
    img = fit_to_canvas(img, st.w, st.h) if not img.isNull() else new_layer_image(st.w, st.h)
    image_fn(img)
    if not img.save(path, "PNG"):
        raise IOError(f"Kare dosyası yazılamadı: {path}")


def read_page_elements(win, page_idx):
    """Karenin çizim kayıtlarını diskten okur (önce flushCurrentPageToCache çağrılmış olmalı)."""
    f = os.path.join(win.drawing_cache_dir, f"s{page_idx + 1}_elements.json")
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return []


def write_page_elements(win, page_idx, elements):
    f = os.path.join(win.drawing_cache_dir, f"s{page_idx + 1}_elements.json")
    with open(f, 'w', encoding='utf-8') as fh:
        json.dump(elements, fh)


def ask_target_frame(win):
    """Hedef kare numarasını sorar; 0 tabanlı indeks döner (iptalde None)."""
    cur = win.current_page_index
    total = len(win.pages_data)
    default = total if total > cur + 1 else min(win.max_pages, cur + 2)
    no, ok = QInputDialog.getInt(
        win, "Kareye Kopyala",
        "Kopyanın gönderileceği kare numarası:\n(Olmayan kareler otomatik oluşturulur)",
        default, 1, win.max_pages)
    if not ok:
        return None
    if no - 1 == cur:
        QMessageBox.information(win, "Kareye Kopyala", "Hedef kare, mevcut kareden farklı olmalı.")
        return None
    return no - 1


def ensure_pages(win, target):
    created = False
    while len(win.pages_data) <= target:
        win.pages_data.append({"background": QColor(win.background_color), "hold": 1})
        created = True
    if created:
        win.refreshPageButtonMenu()
    return created


def after_keyframe_change(win, message):
    win.is_project_modified = True
    if hasattr(win, "anim"):
        win.anim.invalidate_onion()
    win.drawing_area.update()
    if hasattr(win, "timeline"):
        win.timeline.schedule_refresh()
    QToolTip.showText(QCursor.pos(), message, win.drawing_area)


# ---------------------------------------------------------------------------
# S modu: tuval davranışı
# ---------------------------------------------------------------------------
class SelectionMixin:
    # ------------------------------------------------------------------ durum
    def initSelection(self):
        self.setMouseTracking(True)
        self.select_active = False
        self.sel_path = None              # QPainterPath (tuval koordinatı)
        self.sel_rect = QRect()
        self.sel_points = []              # çizilmekte olan serbest seçim noktaları
        self.sel_drawing = False
        self.sel_rect_mode = False
        self.sel_floating = None          # tutulan piksel parçası (QImage)
        self.sel_grab = False             # bir işlem (G/S/R) sürüyor mu
        self.sel_op = None                # 'g' / 's' / 'r'
        self.sel_dp = QPointF(0, 0)
        self.sel_k = 1.0
        self.sel_a = 0.0
        self.sel_grab_mouse0 = QPointF(0, 0)
        self.sel_axis = None              # G için: None / 'x' / 'y'
        self.sel_cur = {"p": QPointF(0, 0), "s": 1.0, "r": 0.0}   # takip edilen merkez / ölçek / açı
        self.sel_last_canvas = QPointF(0, 0)
        self.sel_tween = None
        self._keep_selection_once = False
        self._sel_dash = 0
        self._sel_timer = QTimer(self)
        self._sel_timer.setInterval(120)
        self._sel_timer.timeout.connect(self._sel_tick)

    def setSelectActive(self, active):
        active = bool(active)
        if not active:
            if self.sel_grab:
                self.selectCancelGrab()
            self.clearSelection()
        self.select_active = active
        if active:
            self.setCursor(Qt.CrossCursor)
        self.update()

    def clearSelection(self):
        self.sel_path = None
        self.sel_rect = QRect()
        self.sel_points = []
        self.sel_drawing = False
        self._sel_timer.stop()
        self.update()

    def pageChangedReset(self):
        """Sayfa değişince çağrılır. D ile kopyalama sırasındaki geçişte piksel seçimi korunur."""
        if hasattr(self, "ptPageChanged"):
            self.ptPageChanged()
        if self._keep_selection_once:
            self._keep_selection_once = False
            return
        if self.sel_grab:
            self.sel_floating = None
            self.sel_grab = False
            self.sel_op = None
        self.clearSelection()

    def onHistoryApplied(self):
        """Geri al / yinele sonrası seçimler geçersiz olabilir."""
        self.sel_floating = None
        self.sel_grab = False
        self.sel_op = None
        self.clearSelection()
        if hasattr(self, "ptHistoryApplied"):
            self.ptHistoryApplied()

    def hasSelection(self):
        return self.sel_path is not None and not self.sel_rect.isEmpty()

    def _sel_tick(self):
        self._sel_dash = (self._sel_dash + 1) % 8
        if self.hasSelection() or self.sel_drawing:
            self.update()

    # ------------------------------------------------------------------ iki mod için ortak yönlendirme
    def modeStartOp(self, kind):
        if self.select_active:
            self.selectStartOp(kind)
        elif getattr(self, "point_active", False):
            self.ptStartOp(kind)

    def modeEscape(self):
        if self.select_active:
            self.selectEscape()
        elif getattr(self, "point_active", False):
            self.ptEscape()

    def modeDelete(self):
        if self.select_active:
            self.selectDelete()
        elif getattr(self, "point_active", False):
            self.ptDelete()

    def modeAxis(self, axis):
        if self.select_active:
            self.selectSetAxis(axis)
        elif getattr(self, "point_active", False):
            self.ptSetAxis(axis)

    # ------------------------------------------------------------------ fare
    def _select_can_handle(self, event):
        parent = self.parent()
        if parent is None:
            return False
        if self.alt_held or self.alt_permanent_pan_mode or parent.nav_button.isChecked():
            return False
        return True

    def selectMousePress(self, event):
        if not self._select_can_handle(event):
            return False
        if self.sel_grab:
            if event.button() == Qt.RightButton:
                self.selectCancelGrab()
            elif event.button() == Qt.LeftButton:
                self.selectConfirmGrab()
            return True
        if event.button() != Qt.LeftButton:
            return False
        pos = self.toCanvas(event.pos())
        self.sel_drawing = True
        self.sel_rect_mode = bool(event.modifiers() & Qt.ShiftModifier)
        self.sel_points = [QPointF(pos)]
        self.sel_path = None
        self.sel_rect = QRect()
        self._sel_timer.start()
        self.update()
        return True

    def selectMouseMove(self, event):
        if self.panning:
            return False
        pos = self.toCanvas(event.pos())
        self.sel_last_canvas = QPointF(pos)
        if self.sel_grab:
            self._sel_update_op(pos)
            self.update()
            return True
        if self.sel_drawing:
            if self.sel_rect_mode:
                self.sel_points = [self.sel_points[0], QPointF(pos)]
            else:
                last = self.sel_points[-1]
                if abs(pos.x() - last.x()) + abs(pos.y() - last.y()) > 2.0:
                    self.sel_points.append(QPointF(pos))
            self.update()
            return True
        return False

    def selectMouseRelease(self, event):
        if self.sel_grab:
            return True
        if self.sel_drawing and event.button() == Qt.LeftButton:
            self.sel_drawing = False
            self._finish_lasso()
            return True
        return False

    def _finish_lasso(self):
        path = QPainterPath()
        if self.sel_rect_mode and len(self.sel_points) >= 2:
            path.addRect(QRectF(self.sel_points[0], self.sel_points[-1]).normalized())
        elif len(self.sel_points) >= 3:
            path.addPolygon(QPolygonF(self.sel_points))
            path.closeSubpath()
        canvas = QPainterPath()
        canvas.addRect(QRectF(0, 0, self.layer_stack.w, self.layer_stack.h))
        path = path.intersected(canvas)
        rect = path.boundingRect().toAlignedRect().intersected(QRect(0, 0, self.layer_stack.w, self.layer_stack.h))
        self.sel_points = []
        if rect.width() < 2 or rect.height() < 2:
            self.clearSelection()
            return
        self.sel_path = path
        self.sel_rect = rect
        self.sel_cur = {"p": QPointF(rect.x() + rect.width() / 2.0, rect.y() + rect.height() / 2.0),
                        "s": 1.0, "r": 0.0}
        self._sel_timer.start()
        self.update()

    # ------------------------------------------------------------------ piksel işlemleri
    def _extract_clip(self, layer, path, rect):
        clip = QImage(rect.size(), LAYER_FORMAT)
        clip.fill(Qt.transparent)
        p = QPainter(clip)
        local = QPainterPath(path)
        local.translate(-rect.x(), -rect.y())
        p.setClipPath(local)
        p.drawImage(0, 0, layer.image, rect.x(), rect.y(), rect.width(), rect.height())
        p.end()
        return clip

    def _erase_region(self, layer, path, rect):
        p = QPainter(layer.image)
        p.setClipPath(path)
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        p.fillRect(rect, QColor(0, 0, 0, 0))
        p.end()
        layer.invalidate()
        layer.touch()

    # ------------------------------------------------------------------ G / S / R
    def _sel_xf(self):
        """Mevcut önizleme dönüşümü (tuval koordinatından tuval koordinatına, merkez etrafında)."""
        c = self.sel_cur["p"]
        xf = QTransform()
        xf.translate(c.x() + self.sel_dp.x(), c.y() + self.sel_dp.y())
        xf.rotate(self.sel_a)
        xf.scale(self.sel_k, self.sel_k)
        xf.translate(-c.x(), -c.y())
        return xf

    def selectStartOp(self, kind):
        if not self.select_active or not self.hasSelection() or self.sel_grab:
            return
        if not self.isLayerEditable():
            QToolTip.showText(QCursor.pos(), "Aktif katman gizli veya kilitli", self)
            return
        layer = self.layer_stack.active
        self.saveStateForUndo()
        clip = self._extract_clip(layer, self.sel_path, self.sel_rect)
        self._erase_region(layer, self.sel_path, self.sel_rect)
        self.commitImageToPixmap()
        self.sel_floating = clip
        self.sel_op = kind
        self.sel_grab = True
        self.sel_dp = QPointF(0, 0)
        self.sel_k = 1.0
        self.sel_a = 0.0
        self.sel_grab_mouse0 = QPointF(self.sel_last_canvas)
        self.sel_axis = None
        self.setCursor(Qt.SizeAllCursor)
        self.update()

    def selectStartGrab(self):
        self.selectStartOp('g')

    def _sel_update_op(self, pos):
        c = self.sel_cur["p"]
        m0 = self.sel_grab_mouse0
        if self.sel_op == 'g':
            dx = round(pos.x() - m0.x())
            dy = round(pos.y() - m0.y())
            if self.sel_axis == 'x':
                dy = 0
            elif self.sel_axis == 'y':
                dx = 0
            self.sel_dp = QPointF(dx, dy)
        elif self.sel_op == 's':
            d0 = max(8.0, math.hypot(m0.x() - c.x(), m0.y() - c.y()))
            d1 = math.hypot(pos.x() - c.x(), pos.y() - c.y())
            self.sel_k = max(0.02, d1 / d0)
        elif self.sel_op == 'r':
            a0 = math.atan2(m0.y() - c.y(), m0.x() - c.x())
            a1 = math.atan2(pos.y() - c.y(), pos.x() - c.x())
            self.sel_a = math.degrees(a1 - a0)

    def selectSetAxis(self, axis):
        if self.sel_grab and self.sel_op == 'g':
            self.sel_axis = None if self.sel_axis == axis else axis
            self._sel_update_op(self.sel_last_canvas)
            self.update()

    def selectConfirmGrab(self):
        if not self.sel_grab or self.sel_floating is None:
            return
        layer = self.layer_stack.active
        xf = self._sel_xf()
        p = QPainter(layer.image)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setTransform(xf)
        p.drawImage(self.sel_rect.topLeft(), self.sel_floating)
        p.end()
        self.sel_path = xf.map(self.sel_path)
        canvas_rect = QRect(0, 0, self.layer_stack.w, self.layer_stack.h)
        rect = self.sel_path.boundingRect().toAlignedRect().intersected(canvas_rect)
        # takip edilen merkez / ölçek / açı (ara kare hesabı için)
        c = self.sel_cur["p"]
        self.sel_cur = {"p": QPointF(c.x() + self.sel_dp.x(), c.y() + self.sel_dp.y()),
                        "s": self.sel_cur["s"] * self.sel_k, "r": self.sel_cur["r"] + self.sel_a}
        self.sel_rect = rect if not rect.isEmpty() else QRect(self.sel_rect)
        self.sel_floating = None
        self.sel_grab = False
        self.sel_op = None
        self.sel_dp = QPointF(0, 0)
        self.sel_k = 1.0
        self.sel_a = 0.0
        self.setCursor(Qt.CrossCursor)
        self.commitImageToPixmap()
        if self.parent():
            self.parent().is_project_modified = True
        t = self.sel_tween
        win = self.parent()
        if t and win is not None and t.get("kind") == "pixels" and t["layer_id"] == layer.id \
                and win.current_page_index == t["end_page"]:
            t["end"] = {"p": QPointF(self.sel_cur["p"]), "s": self.sel_cur["s"], "r": self.sel_cur["r"]}
        self.update()
        self.contentChanged.emit()

    def selectCancelGrab(self):
        if not self.sel_grab:
            return
        if self.undo_stack:
            _elements, snap = self.undo_stack.pop()
            if snap.get("kind") == "layer":
                layer = self.layer_stack.by_id(snap["id"])
                if layer is not None and snap.get("image") is not None:
                    layer.image = snap["image"]
                    layer.touch()
        self.sel_floating = None
        self.sel_grab = False
        self.sel_op = None
        self.sel_dp = QPointF(0, 0)
        self.sel_k = 1.0
        self.sel_a = 0.0
        self.setCursor(Qt.CrossCursor)
        self.commitImageToPixmap()
        self.update()

    def selectEscape(self):
        if self.sel_grab:
            self.selectCancelGrab()
        elif self.hasSelection() or self.sel_drawing:
            self.clearSelection()

    def selectDelete(self):
        if not self.select_active or not self.hasSelection() or self.sel_grab or not self.isLayerEditable():
            return
        self.saveStateForUndo()
        self._erase_region(self.layer_stack.active, self.sel_path, self.sel_rect)
        self.commitImageToPixmap()
        self.update()
        self.contentChanged.emit()

    # ------------------------------------------------------------------ çizim (noktalı seçim çizgisi)
    def _paint_selection(self, painter):
        if not self.select_active:
            return
        painter.save()
        xf = None
        if self.sel_grab and self.sel_floating is not None:
            xf = self._sel_xf()
            painter.save()
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            painter.setOpacity(self.layer_stack.active.opacity)
            painter.setTransform(xf, True)
            painter.drawImage(self.sel_rect.topLeft(), self.sel_floating)
            painter.restore()

        path = None
        if self.sel_drawing and self.sel_points:
            path = QPainterPath()
            if self.sel_rect_mode and len(self.sel_points) >= 2:
                path.addRect(QRectF(self.sel_points[0], self.sel_points[-1]).normalized())
            else:
                path.addPolygon(QPolygonF(self.sel_points))
        elif self.hasSelection():
            path = QPainterPath(self.sel_path)
            if xf is not None:
                path = xf.map(path)

        if path is not None:
            painter.fillPath(path, QColor(90, 150, 255, 32))
            black = QPen(QColor(0, 0, 0, 230), 1)
            black.setCosmetic(True)
            painter.setPen(black)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
            dotted = QPen(QColor(255, 255, 255), 1)
            dotted.setCosmetic(True)
            dotted.setStyle(Qt.CustomDashLine)
            dotted.setDashPattern([4, 4])
            dotted.setDashOffset(self._sel_dash)
            painter.setPen(dotted)
            painter.drawPath(path)
        painter.restore()


# ---------------------------------------------------------------------------
# S modu: D (kareye kopyala) ve Ctrl+D (ara kareler)
# ---------------------------------------------------------------------------
def _pixel_xf(t, params):
    """Klibin verilen parametrelerle (merkez p, ölçek s, açı r) çizim dönüşümü."""
    p, ref = params["p"], t["ref"]
    xf = QTransform()
    xf.translate(p.x(), p.y())
    xf.rotate(params["r"])
    xf.scale(params["s"], params["s"])
    xf.translate(-ref.x(), -ref.y())
    return xf


def _draw_clip(painter, t, params):
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    painter.setTransform(_pixel_xf(t, params))
    painter.drawImage(0, 0, t["clip"])


def select_copy_to_frame(win):
    """D (S modu): seçimi başka bir kareye kopyalar, o kareye geçer ve kopyayı seçili bırakır."""
    area = win.drawing_area
    if not (area.select_active and area.hasSelection()):
        QToolTip.showText(QCursor.pos(), "Önce bir bölge seçin", area)
        return
    if area.sel_grab:
        area.selectConfirmGrab()
    layer = area.layer_stack.active
    cur = win.current_page_index
    target = ask_target_frame(win)
    if target is None:
        return

    clip = area._extract_clip(layer, area.sel_path, area.sel_rect)
    rect = QRect(area.sel_rect)
    path_copy = QPainterPath(area.sel_path)
    p0 = QPointF(area.sel_cur["p"])
    ref = QPointF(p0.x() - rect.x(), p0.y() - rect.y())     # takip edilen merkez, klip yerel koordinatında

    win.flushCurrentPageToCache()
    ensure_pages(win, target)

    def image_fn(img):
        p = QPainter(img)
        p.drawImage(rect.topLeft(), clip)
        p.end()
    edit_layer_file(win, target, layer.id, image_fn)

    ident = {"p": QPointF(p0), "s": 1.0, "r": 0.0}
    area.sel_tween = {"kind": "pixels", "start_page": cur, "end_page": target, "layer_id": layer.id,
                      "clip": clip, "ref": ref,
                      "start": {"p": QPointF(p0), "s": 1.0, "r": 0.0},
                      "end": {"p": QPointF(p0), "s": 1.0, "r": 0.0}, "drawn": {}}

    area._keep_selection_once = True
    win.loadPageData(target)
    area.sel_path = path_copy
    area.sel_rect = rect
    area.sel_cur = ident
    area._sel_timer.start()
    area.update()
    after_keyframe_change(win, f"Kopya kare {target + 1}'e eklendi. G/S/R ile düzenleyin, sonra Ctrl+D.")


def select_build_tween(win):
    """Ctrl+D (S modu): ara kareleri konum / ölçek / açı geçişiyle otomatik doldurur."""
    area = win.drawing_area
    t = area.sel_tween
    if not t or t.get("kind") != "pixels":
        QMessageBox.information(win, "Ara Kareler",
                                "Önce nesneyi seçip D ile hedef kareye kopyalayın, G / S / R ile düzenleyin;\n"
                                "ardından Ctrl+D ile ara kareler oluşturulur.")
        return
    if area.sel_grab:
        area.selectConfirmGrab()
    start, end = t["start_page"], t["end_page"]
    lo, hi = min(start, end), max(start, end)
    if hi - lo < 2:
        QMessageBox.information(win, "Ara Kareler", "Başlangıç ve hedef kare arasında ara kare yok.")
        return
    if not win.flushCurrentPageToCache():
        return

    sp, ep = t["start"], t["end"]
    span = float(end - start)
    try:
        for pg in range(lo + 1, hi):
            k = (pg - start) / span
            params = {"p": QPointF(sp["p"].x() + (ep["p"].x() - sp["p"].x()) * k,
                                   sp["p"].y() + (ep["p"].y() - sp["p"].y()) * k),
                      "s": sp["s"] + (ep["s"] - sp["s"]) * k,
                      "r": sp["r"] + (ep["r"] - sp["r"]) * k}
            old = t["drawn"].get(pg)

            def image_fn(img, old=old, params=params):
                if old is not None:                         # önceki Ctrl+D izini sil
                    mask = new_layer_image(img.width(), img.height())
                    mp = QPainter(mask)
                    _draw_clip(mp, t, old)
                    mp.end()
                    erase_mask(img, mask)
                dp = QPainter(img)
                _draw_clip(dp, t, params)
                dp.end()
            edit_layer_file(win, pg, t["layer_id"], image_fn)
            t["drawn"][pg] = params
    except Exception as e:
        QMessageBox.critical(win, "Hata", f"Ara kareler oluşturulamadı: {e}")
        return

    if lo < win.current_page_index < hi:
        area._keep_selection_once = True
        saved = (QPainterPath(area.sel_path) if area.sel_path is not None else None, QRect(area.sel_rect),
                 dict(area.sel_cur))
        win.loadPageData(win.current_page_index, save_current=False)
        if saved[0] is not None:
            area.sel_path, area.sel_rect, area.sel_cur = saved
    after_keyframe_change(win, f"{hi - lo - 1} ara kare oluşturuldu.")


# ---------------------------------------------------------------------------
# D / Ctrl+D yönlendirme: hangi mod açıksa onun mantığı çalışır
# ---------------------------------------------------------------------------
def keyframe_copy(win):
    area = win.drawing_area
    if getattr(area, "point_active", False):
        points_copy_to_frame(win)
    elif area.select_active:
        select_copy_to_frame(win)


def keyframe_tween(win):
    area = win.drawing_area
    if getattr(area, "point_active", False):
        points_build_tween(win)
    elif area.select_active:
        select_build_tween(win)


# ===========================================================================
# BÖLÜM: A MODU (NOKTA DÜZENLEME)
# ===========================================================================
# Kavram - A modu (nokta düzenleme)
#
# Çizimler "noktalı görünüme" geçer: her çizginin köşe noktaları arka plan renginde gösterilir
# (düz çizgi 2 nokta, dikdörtgen 4, karmaşık çizim onlarca nokta). Serbest çizimler önce
# sadeleştirilir (Ramer-Douglas-Peucker), böylece yüzlerce fare örneği yerine anlamlı köşeler görünür.
#
#   Tıkla = nokta seç, Shift+tıkla = çoklu seçim, boşlukta sürükle = kutuyla seçim (Shift = ekle)
#   G = taşı, S = büyüt/küçült, R = döndür  (sol tık onayla, Esc / sağ tık iptal; G'de X/Y eksen kısıtı)
#   D = seçili noktaların çizgilerini başka kareye kopyala, Ctrl+D = aradaki kareleri otomatik doldur
#       (nokta konumları kareler arasında geçiş yapar: gerçek "morph" ara kare)
#
# Çizgi, noktalar hareket edince yeniden çizilir: noktaların arasındaki ham örnekler, komşu köşelerin
# yer değiştirmesine göre yumuşakça karıştırılır (eğrilik korunur).


# ---------------------------------------------------------------------------
# Saf yardımcılar (Qt gerektirmez)
# ---------------------------------------------------------------------------
def is_editable(el):
    if el.get("is_eraser"):
        return False
    t = el.get("type")
    if t in ("stroke", "stroke_pressure"):
        return len(el.get("points", [])) >= 1
    if t in ("text", "image"):
        return "position" in el
    return False


def element_xy(el):
    if el["type"] in ("stroke", "stroke_pressure"):
        return [(float(p[0]), float(p[1])) for p in el["points"]]
    return [(float(el["position"][0]), float(el["position"][1]))]


def apply_xy(el, xy):
    if el["type"] in ("stroke", "stroke_pressure"):
        for row, (x, y) in zip(el["points"], xy):
            row[0] = round(x, 2)
            row[1] = round(y, 2)
        if el.get("is_solid_fill") and "bbox" in el and xy:
            xs = [p[0] for p in xy]
            ys = [p[1] for p in xy]
            el["bbox"] = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
    else:
        el["position"] = [round(xy[0][0], 2), round(xy[0][1], 2)]


def copy_element(el):
    """Büyük metinleri (doku, görsel) kopyalamadan, konumları değişebilen alanları kopyalar."""
    new = dict(el)
    if "points" in el:
        new["points"] = [list(r) for r in el["points"]]
    if "position" in el:
        new["position"] = list(el["position"])
    if "bbox" in el:
        new["bbox"] = list(el["bbox"])
    if isinstance(el.get("color"), list):
        new["color"] = list(el["color"])
    return new


def rdp_indices(pts, eps):
    """Ramer-Douglas-Peucker (yinelemesiz). Korunan nokta indekslerini döndürür."""
    n = len(pts)
    if n <= 2:
        return list(range(n))
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        root = math.sqrt(l2)
        dmax, idx = -1.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            if l2 == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dy * (px - ax) - dx * (py - ay)) / root
            if d > dmax:
                dmax, idx = d, i
        if dmax > eps and idx > 0:
            keep[idx] = True
            stack.append((a, idx))
            stack.append((idx, b))
    return [i for i, k in enumerate(keep) if k]


def key_info(xy, max_keys=40, eps0=2.5):
    """Bir çizginin köşe noktaları. 'all' = tüm anahtarlar, 'show' = gösterilenler (kapalı şekilde son = ilk)."""
    n = len(xy)
    if n <= 2:
        keys = list(range(n))
    else:
        eps = eps0
        keys = rdp_indices(xy, eps)
        while len(keys) > max_keys:
            eps *= 1.4
            keys = rdp_indices(xy, eps)
    closed = (n >= 4 and len(keys) >= 3 and keys[0] == 0 and keys[-1] == n - 1
              and math.hypot(xy[0][0] - xy[-1][0], xy[0][1] - xy[-1][1]) <= 1.5)
    return {"all": keys, "show": keys[:-1] if closed else list(keys), "closed": closed, "n": n}


def deform_points(xy, keys_all, disp):
    """Anahtar noktaların yer değiştirmesini (disp) aradaki ham noktalara yay uzunluğuyla dağıtır."""
    n = len(xy)
    if n == 0:
        return []
    if len(keys_all) == 1:
        d = disp[0]
        return [(x + d[0], y + d[1]) for x, y in xy]
    cum = [0.0]
    for i in range(1, n):
        cum.append(cum[-1] + math.hypot(xy[i][0] - xy[i - 1][0], xy[i][1] - xy[i - 1][1]))
    out = [None] * n
    for j in range(len(keys_all) - 1):
        a, b = keys_all[j], keys_all[j + 1]
        da, db = disp[j], disp[j + 1]
        span = cum[b] - cum[a]
        for i in range(a, b + 1):
            if span > 1e-9:
                t = (cum[i] - cum[a]) / span
            else:
                t = (i - a) / float(b - a) if b > a else 0.0
            out[i] = (xy[i][0] + da[0] + (db[0] - da[0]) * t,
                      xy[i][1] + da[1] + (db[1] - da[1]) * t)
    return out


def lerp_element(s, e, k, uid):
    """İki anahtar kare arasındaki ara çizgiyi (nokta konumlarını karıştırarak) üretir."""
    if s.get("type") != e.get("type"):
        return None
    sxy, exy = element_xy(s), element_xy(e)
    if len(sxy) != len(exy):
        return None
    new = copy_element(s)
    new.pop("lk", None)
    new["tw"] = uid
    apply_xy(new, [(sx + (ex - sx) * k, sy + (ey - sy) * k) for (sx, sy), (ex, ey) in zip(sxy, exy)])
    return new


# ---------------------------------------------------------------------------
# Tuval davranışı
# ---------------------------------------------------------------------------
class PointModeMixin:
    def initPoints(self):
        self.point_active = False
        self.pt_selected = set()          # {(eleman_indeksi, nokta_sırası)}
        self.pt_sel_layer = None
        self.pt_cache = {}                # id(eleman) -> köşe bilgisi
        self.pt_marquee = None            # [QPointF, QPointF]
        self.pt_marquee_shift = False
        self.pt_op = None                 # 'g' / 's' / 'r'
        self.pt_data = None
        self.pt_axis = None
        self.pt_mouse0 = QPointF(0, 0)
        self.pt_preview = None
        self.pt_preview_pts = []
        self.pt_tween = None

    def setPointActive(self, active):
        active = bool(active)
        if not active:
            if self.pt_op:
                self.ptCancelOp()
            self.pt_selected = set()
            self.pt_marquee = None
        self.point_active = active
        if active:
            self.setCursor(Qt.CrossCursor)
        self.update()

    def ptPageChanged(self):
        self.pt_selected = set()
        self.pt_cache = {}
        self.pt_marquee = None
        self.pt_op = None
        self.pt_data = None
        self.pt_preview = None

    def ptHistoryApplied(self):
        self.ptPageChanged()

    # ------------------------------------------------------------------ nokta bilgisi
    def _pt_info(self, el):
        n = len(el["points"]) if "points" in el else 1
        info = self.pt_cache.get(id(el))
        if info is None or info["n"] != n or info["el"] is not el:
            info = key_info(element_xy(el))
            info["el"] = el          # güçlü referans: id yeniden kullanımını engeller
            self.pt_cache[id(el)] = info
        return info

    def _pt_candidates(self):
        layer = self.layer_stack.active
        return [(i, el) for i, el in enumerate(self.drawing_elements)
                if el.get("layer") == layer.name and is_editable(el)]

    def _pt_visible(self, x, y):
        img = self.layer_stack.active.image
        xi, yi = int(x), int(y)
        if xi < 0 or yi < 0 or xi >= img.width() or yi >= img.height():
            return True
        return img.pixelColor(xi, yi).alpha() > 8      # silinmiş çizgilerin hayalet noktaları gösterilmesin

    def _pt_positions(self, i, el, check_visible=True):
        info = self._pt_info(el)
        xy = element_xy(el)
        out = []
        for slot, idx in enumerate(info["show"]):
            x, y = xy[idx]
            if check_visible and not self._pt_visible(x, y):
                continue
            out.append((slot, QPointF(x, y)))
        return out

    def _pt_validate(self):
        layer = self.layer_stack.active
        if self.pt_sel_layer is not None and self.pt_sel_layer != layer.id:
            self.pt_selected = set()
        n = len(self.drawing_elements)
        if any(i >= n for i, _s in self.pt_selected):
            self.pt_selected = set()

    def _pt_hit(self, pos):
        radius = 9.0 / max(self.zoom_factor, 0.01)
        best, best_d = None, radius
        for i, el in self._pt_candidates():
            for slot, pt in self._pt_positions(i, el):
                d = math.hypot(pt.x() - pos.x(), pt.y() - pos.y())
                if d <= best_d:
                    best, best_d = (i, slot), d
        return best

    # ------------------------------------------------------------------ fare
    def ptMousePress(self, event):
        if not self._select_can_handle(event):
            return False
        if self.pt_op:
            if event.button() == Qt.RightButton:
                self.ptCancelOp()
            elif event.button() == Qt.LeftButton:
                self.ptConfirmOp()
            return True
        if event.button() != Qt.LeftButton:
            return False
        pos = self.toCanvas(event.pos())
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        self._pt_validate()
        hit = self._pt_hit(pos)
        if hit is not None:
            if shift:
                if hit in self.pt_selected:
                    self.pt_selected.discard(hit)
                else:
                    self.pt_selected.add(hit)
            elif hit not in self.pt_selected:
                self.pt_selected = {hit}
            self.pt_sel_layer = self.layer_stack.active.id
            self.pt_marquee = None
        else:
            self.pt_marquee = [QPointF(pos), QPointF(pos)]
            self.pt_marquee_shift = shift
        self.update()
        return True

    def ptMouseMove(self, event):
        if self.panning:
            return False
        pos = self.toCanvas(event.pos())
        self.sel_last_canvas = QPointF(pos)
        if self.pt_op:
            self._pt_update_preview(pos)
            self.update()
            return True
        if self.pt_marquee:
            self.pt_marquee[1] = QPointF(pos)
            self.update()
            return True
        return False

    def ptMouseRelease(self, event):
        if self.pt_op:
            return True
        if self.pt_marquee and event.button() == Qt.LeftButton:
            a, b = self.pt_marquee
            moved = abs(b.x() - a.x()) + abs(b.y() - a.y()) > 4.0 / max(self.zoom_factor, 0.01)
            if moved:
                rect = QRectF(a, b).normalized()
                picked = set()
                for i, el in self._pt_candidates():
                    for slot, pt in self._pt_positions(i, el):
                        if rect.contains(pt):
                            picked.add((i, slot))
                self._pt_validate()
                self.pt_selected = (self.pt_selected | picked) if self.pt_marquee_shift else picked
                self.pt_sel_layer = self.layer_stack.active.id
            elif not self.pt_marquee_shift:
                self.pt_selected = set()                 # boşluğa tıklama: seçimi kaldır
            self.pt_marquee = None
            self.update()
            return True
        return False

    # ------------------------------------------------------------------ G / S / R
    def ptStartOp(self, kind):
        if not self.point_active or self.pt_op:
            return
        self._pt_validate()
        if not self.pt_selected:
            QToolTip.showText(QCursor.pos(), "Önce nokta seçin", self)
            return
        if not self.isLayerEditable():
            QToolTip.showText(QCursor.pos(), "Aktif katman gizli veya kilitli", self)
            return
        layer = self.layer_stack.active
        idxs = sorted({i for i, _s in self.pt_selected})
        self.saveStateForUndo()
        bases, olds, sel_pts = {}, [], []
        for i in idxs:
            old = self.drawing_elements[i]
            info = self._pt_info(old)
            xy = element_xy(old)
            slots = {s for j, s in self.pt_selected if j == i}
            bases[i] = {"el": old, "xy": xy, "info": info, "slots": slots}
            olds.append(old)
            for s in slots:
                sel_pts.append(xy[info["all"][s]])
            live = copy_element(old)                       # undo yığınındaki eski nesneler bozulmasın
            self.drawing_elements[i] = live
            self.pt_cache[id(live)] = dict(info, el=live)
        erase_elements(self, layer.image, olds)
        layer.invalidate()
        self.commitImageToPixmap()
        pivot = QPointF(sum(p[0] for p in sel_pts) / len(sel_pts), sum(p[1] for p in sel_pts) / len(sel_pts))
        self.pt_op = kind
        self.pt_axis = None
        self.pt_data = {"bases": bases, "pivot": pivot}
        self.pt_mouse0 = QPointF(self.sel_last_canvas)
        self.pt_preview = new_layer_image(self.layer_stack.w, self.layer_stack.h)
        self._pt_update_preview(self.sel_last_canvas)
        self.setCursor(Qt.SizeAllCursor)
        self.update()

    def _pt_transform_fn(self, pos):
        piv, m0 = self.pt_data["pivot"], self.pt_mouse0
        if self.pt_op == 'g':
            dx, dy = round(pos.x() - m0.x()), round(pos.y() - m0.y())
            if self.pt_axis == 'x':
                dy = 0
            elif self.pt_axis == 'y':
                dx = 0
            return lambda x, y: (x + dx, y + dy)
        if self.pt_op == 's':
            d0 = max(8.0, math.hypot(m0.x() - piv.x(), m0.y() - piv.y()))
            k = max(0.02, math.hypot(pos.x() - piv.x(), pos.y() - piv.y()) / d0)
            return lambda x, y: (piv.x() + (x - piv.x()) * k, piv.y() + (y - piv.y()) * k)
        ang = math.atan2(pos.y() - piv.y(), pos.x() - piv.x()) - math.atan2(m0.y() - piv.y(), m0.x() - piv.x())
        c, s = math.cos(ang), math.sin(ang)
        return lambda x, y: (piv.x() + (x - piv.x()) * c - (y - piv.y()) * s,
                             piv.y() + (x - piv.x()) * s + (y - piv.y()) * c)

    def _pt_build_elements(self, f):
        out = {}
        for i, b in self.pt_data["bases"].items():
            xy, info = b["xy"], b["info"]
            keys = info["all"]
            disp = [(0.0, 0.0)] * len(keys)
            for s in b["slots"]:
                kx, ky = xy[keys[s]]
                nx, ny = f(kx, ky)
                disp[s] = (nx - kx, ny - ky)
            if info["closed"]:
                disp[-1] = disp[0]
            el = copy_element(b["el"])
            apply_xy(el, deform_points(xy, keys, disp))
            out[i] = el
        return out

    def _pt_update_preview(self, pos):
        els = self._pt_build_elements(self._pt_transform_fn(pos))
        self.pt_preview.fill(Qt.transparent)
        self._render_group(self.pt_preview, list(els.values()))
        pts = []
        for i, el in els.items():
            info = self.pt_data["bases"][i]["info"]
            xy = element_xy(el)
            for slot, idx in enumerate(info["show"]):
                pts.append((QPointF(xy[idx][0], xy[idx][1]), (i, slot) in self.pt_selected))
        self.pt_preview_pts = pts

    def ptConfirmOp(self):
        if not self.pt_op:
            return
        layer = self.layer_stack.active
        els = self._pt_build_elements(self._pt_transform_fn(self.sel_last_canvas))
        self._render_group(layer.image, list(els.values()))
        for i, el in els.items():
            self.drawing_elements[i] = el
            self.pt_cache[id(el)] = dict(self.pt_data["bases"][i]["info"], el=el)
        self.pt_op = None
        self.pt_data = None
        self.pt_preview = None
        self.pt_preview_pts = []
        self.setCursor(Qt.CrossCursor)
        layer.invalidate()
        self.commitImageToPixmap()
        if self.parent():
            self.parent().is_project_modified = True
        self.update()
        self.contentChanged.emit()

    def ptCancelOp(self):
        if not self.pt_op:
            return
        if self.undo_stack:
            _elements, snap = self.undo_stack.pop()
            if snap.get("kind") == "layer":
                layer = self.layer_stack.by_id(snap["id"])
                if layer is not None and snap.get("image") is not None:
                    layer.image = snap["image"]
                    layer.touch()
        self.pt_op = None
        self.pt_data = None
        self.pt_preview = None
        self.pt_preview_pts = []
        self.setCursor(Qt.CrossCursor)
        self.commitImageToPixmap()
        self.update()

    def ptSetAxis(self, axis):
        if self.pt_op == 'g':
            self.pt_axis = None if self.pt_axis == axis else axis
            self._pt_update_preview(self.sel_last_canvas)
            self.update()

    def ptEscape(self):
        if self.pt_op:
            self.ptCancelOp()
        elif self.pt_selected or self.pt_marquee:
            self.pt_selected = set()
            self.pt_marquee = None
            self.update()

    def ptDelete(self):
        """Seçili noktaların ait olduğu çizgileri tümüyle siler."""
        if self.pt_op or not self.pt_selected or not self.isLayerEditable():
            return
        self._pt_validate()
        idxs = {i for i, _s in self.pt_selected}
        if not idxs:
            return
        layer = self.layer_stack.active
        self.saveStateForUndo()
        olds = [self.drawing_elements[i] for i in sorted(idxs)]
        erase_elements(self, layer.image, olds)
        self.drawing_elements = [el for i, el in enumerate(self.drawing_elements) if i not in idxs]
        self._painted_count = len(self.drawing_elements)
        self.pt_selected = set()
        self.pt_cache = {}
        layer.invalidate()
        self.commitImageToPixmap()
        self.update()
        self.contentChanged.emit()

    def ptRestoreSelection(self, links):
        """{lk: [slot, ...]} bağlantılarına göre seçimi yeniden kurar (D ile kareye geçişten sonra)."""
        sel = set()
        for i, el in enumerate(self.drawing_elements):
            lk = el.get("lk")
            if lk in links and is_editable(el):
                for s in links[lk]:
                    sel.add((i, s))
        self.pt_selected = sel
        self.pt_sel_layer = self.layer_stack.active.id

    # ------------------------------------------------------------------ çizim
    def _paint_points(self, painter):
        if not self.point_active:
            return
        parent = self.parent()
        painter.save()
        layer = self.layer_stack.active
        zoom = max(self.zoom_factor, 0.01)
        if self.pt_op and self.pt_preview is not None:
            painter.setOpacity(layer.opacity)
            painter.drawImage(0, 0, self.pt_preview)
            painter.setOpacity(1.0)

        rad = 4.5 / zoom
        bg = QColor(parent.background_color) if parent is not None else QColor(51, 51, 51)
        lum = 0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()
        edge = QColor(255, 255, 255) if lum < 140 else QColor(20, 20, 20)
        pen = QPen(edge, 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QBrush(bg))                      # noktalar arka plan renginde

        affected = set(self.pt_data["bases"].keys()) if (self.pt_op and self.pt_data) else set()
        selected_draw = []
        for i, el in self._pt_candidates():
            if i in affected:
                continue
            for slot, pt in self._pt_positions(i, el):
                if (i, slot) in self.pt_selected:
                    selected_draw.append(pt)
                else:
                    painter.drawEllipse(pt, rad, rad)
        if self.pt_op:
            for pt, sel in self.pt_preview_pts:
                if sel:
                    selected_draw.append(pt)
                else:
                    painter.drawEllipse(pt, rad, rad)

        sel_pen = QPen(QColor(255, 255, 255), 1.5)
        sel_pen.setCosmetic(True)
        painter.setPen(sel_pen)
        painter.setBrush(QColor(255, 150, 0))
        for pt in selected_draw:
            painter.drawEllipse(pt, rad * 1.2, rad * 1.2)

        if self.pt_marquee:
            rect = QRectF(self.pt_marquee[0], self.pt_marquee[1]).normalized()
            painter.fillRect(rect, QColor(90, 150, 255, 35))
            dash = QPen(QColor(255, 255, 255), 1)
            dash.setCosmetic(True)
            dash.setStyle(Qt.DashLine)
            painter.setPen(dash)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)
        painter.restore()


# ---------------------------------------------------------------------------
# D (kareye kopyala) ve Ctrl+D (ara kareler) - nokta modu
# ---------------------------------------------------------------------------
def points_copy_to_frame(win):
    area = win.drawing_area
    if not (area.point_active and area.pt_selected):
        QToolTip.showText(QCursor.pos(), "Önce nokta seçin", area)
        return
    if area.pt_op:
        area.ptConfirmOp()
    area._pt_validate()
    idxs = sorted({i for i, _s in area.pt_selected})
    if not idxs:
        return
    slots_by_idx = {i: sorted(s for j, s in area.pt_selected if j == i) for i in idxs}
    target = ask_target_frame(win)
    if target is None:
        return
    layer = area.layer_stack.active
    cur = win.current_page_index

    base = str(int(time.time() * 1000) % 1000000000)
    links = {}
    for n, i in enumerate(idxs):                           # başlangıç çizgilerini bağlantı etiketiyle işaretle
        lk = f"{base}_{n}"
        area.drawing_elements[i]["lk"] = lk
        links[lk] = slots_by_idx[i]

    win.flushCurrentPageToCache()
    ensure_pages(win, target)
    copies = [copy_element(area.drawing_elements[i]) for i in idxs]
    existing = read_page_elements(win, target)
    write_page_elements(win, target, existing + copies)
    edit_layer_file(win, target, layer.id, lambda img: area._render_group(img, copies))

    area.pt_tween = {"kind": "points", "start_page": cur, "end_page": target, "layer_id": layer.id,
                     "links": list(links.keys()), "uid": base}
    win.loadPageData(target)
    area.ptRestoreSelection(links)
    area.update()
    after_keyframe_change(win, f"Kopya kare {target + 1}'e eklendi. G/S/R ile noktaları düzenleyin, sonra Ctrl+D.")


def points_build_tween(win):
    area = win.drawing_area
    t = area.pt_tween
    if not t or t.get("kind") != "points":
        QMessageBox.information(win, "Ara Kareler",
                                "Önce noktaları seçip D ile hedef kareye kopyalayın, G / S / R ile düzenleyin;\n"
                                "ardından Ctrl+D ile ara kareler oluşturulur.")
        return
    if area.pt_op:
        area.ptConfirmOp()
    start, end = t["start_page"], t["end_page"]
    lo, hi = min(start, end), max(start, end)
    if hi - lo < 2:
        QMessageBox.information(win, "Ara Kareler", "Başlangıç ve hedef kare arasında ara kare yok.")
        return
    if not win.flushCurrentPageToCache():
        return

    s_elems = read_page_elements(win, start)
    e_elems = read_page_elements(win, end)
    pairs = []
    for lk in t["links"]:
        s = next((e for e in s_elems if e.get("lk") == lk), None)
        e = next((e for e in e_elems if e.get("lk") == lk), None)
        if s is not None and e is not None and lerp_element(s, e, 0.0, "x") is not None:
            pairs.append((s, e))
    if not pairs:
        QMessageBox.information(win, "Ara Kareler",
                                "Eşleşen çizgi bulunamadı (nokta sayısı değişmiş veya çizgiler silinmiş olabilir).")
        return

    uid, lid, span = t["uid"], t["layer_id"], float(end - start)
    try:
        for pg in range(lo + 1, hi):
            k = (pg - start) / span
            new_elems = [lerp_element(s, e, k, uid) for s, e in pairs]
            page_elems = read_page_elements(win, pg)
            old = [e for e in page_elems if e.get("tw") == uid]
            kept = [e for e in page_elems if e.get("tw") != uid]

            def image_fn(img, old=old, new_elems=new_elems):
                erase_elements(area, img, old)           # önceki Ctrl+D izini sil
                area._render_group(img, new_elems)
            edit_layer_file(win, pg, lid, image_fn)
            write_page_elements(win, pg, kept + new_elems)
    except Exception as ex:
        QMessageBox.critical(win, "Hata", f"Ara kareler oluşturulamadı: {ex}")
        return

    if lo < win.current_page_index < hi:
        win.loadPageData(win.current_page_index, save_current=False)
    after_keyframe_change(win, f"{hi - lo - 1} ara kare oluşturuldu.")


# ===========================================================================
# BÖLÜM: ÇİZİM TUVALİ (DrawingArea)
# ===========================================================================
# Kavram - Çizim tuvali (DrawingArea)


class DrawingArea(PointModeMixin, SelectionMixin, LayerAreaMixin, QWidget):
    layersChanged = pyqtSignal()   # katman yapısı / aktif katman değişti
    contentChanged = pyqtSignal()  # kare içeriği değişti (küçük resim, soğan zarı)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StaticContents)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.modified = False
        self.drawing = False
        self.lastPoint = QPoint()
        self.last_widget_pos = QPoint() 
        self.last_pressure = 1.0

        # --- EKSİK NİTELİKLER EKLENDİ ---
        self.zoom_factor = 1.0
        self.view_offset = QPoint(0, 0)
        self.panning = False
        self.last_pan_pos = QPoint()

        # TUVAL BOYUTU DİNAMİKLEŞTİRİLDİ
        canvas_w = self.parent().canvas_width if self.parent() and hasattr(self.parent(), 'canvas_width') else 1100
        canvas_h = self.parent().canvas_height if self.parent() and hasattr(self.parent(), 'canvas_height') else 600

        # Katman sistemi: her katmanın kendi görüntüsü var; self.image = aktif katman (bkz. drawing_layers.py)
        self.initLayers(canvas_w, canvas_h)
        self.initSelection()
        self.initPoints()

        # Animasyon bağlantıları (drawing_animation.py doldurur)
        self.playback_frame = None       # oynatma sırasında gösterilen hazır kare (QImage)
        self.playback_stop_cb = None
        self.onion_provider = None       # () -> [(QImage, opaklık), ...]

        # Referans görsel değişkenleri (sayfaya özel)
        # Yeni sistem: sadece 1 referans
        self.reference_image = None          # {'id': int, 'image': QImage, 'offset': QPoint, 'display_size': QSize, 'visible': bool}
        self._reference_scaled_cache = {}   # Önbellek (id, width, height) -> scaled QImage

        self.placing_reference = False         # yerleştirme modunda mı?


        self.image_cache = {}

        self.mirror_line_x = canvas_w // 2
        self.mirror_line_y = canvas_h // 2
        self.dragging_mirror_line = False

        self.drawing_elements = []
        
        self.undo_stack = []
        self.redo_stack = []

        self.force_active_layer_bottom = False

        self.text_input_widget = ResizableTextEdit(self)
        self.text_input_widget.hide()
        self.text_input_widget.finished.connect(self.addTextToDrawing)

        self.original_image_for_placement = None
        self.current_image_display_size = QSize(0, 0)
        self.image_placement_offset = QPoint(0, 0)
        self.dragging_image = False
        self.last_drag_pos = QPoint()

        self.current_stroke_points = []
        self.current_stroke_pen_info = []
        self.current_mix_index = 0
        self.stroke_length_accumulator = 0.0

        self.polyline_points = []
        self.hovered_poly_point_index = -1
        self.dragging_poly_point_index = -1
        self.dragging_whole_polyline = False
        self.last_poly_drag_pos = QPoint()

        self.curve_points = []

        self.lazy_mouse_pos = None  
        self.lazy_damping = 0.40    
        self.lazy_target_pos = None 
        self.lazy_velocity = QPointF(0, 0)  

        self.alt_permanent_pan_mode = False  
        self.alt_held = False                

        # Referans katman konumu: 0 üstte, 1 altta
        self.reference_layer_position = 0

    def clearImageCache(self):
        """Görsel önbelleğini temizler (bellek sızıntısını önlemek için)."""
        self.image_cache.clear()

    def calculateMixColor(self, x, y, step_accum, mix_colors, mix_mode, mix_angle, sequential_idx=0):
        if not mix_colors:
            return QColor(0,0,0)
        num_colors = len(mix_colors)
        if num_colors == 1:
            return mix_colors[0]

        def lerp(c1, c2, frac):
            return QColor(
                int(c1.red() + (c2.red() - c1.red()) * frac),
                int(c1.green() + (c2.green() - c1.green()) * frac),
                int(c1.blue() + (c2.blue() - c1.blue()) * frac)
            )

        if mix_mode == 'random':
            return random.choice(mix_colors)
        elif mix_mode == 'sequential':
            return mix_colors[int(sequential_idx) % num_colors]
        elif mix_mode == 'gradient':
            angle_rad = math.radians(mix_angle)
            proj = x * math.cos(angle_rad) + y * math.sin(angle_rad)
            idx = int(abs(proj) / 100.0) % num_colors
            return mix_colors[idx]
        elif mix_mode == 'smooth':
            transition_length = 200.0
            pos = step_accum / transition_length
            idx1 = int(pos) % num_colors
            idx2 = (idx1 + 1) % num_colors
            frac = pos - int(pos)
            return lerp(mix_colors[idx1], mix_colors[idx2], frac)
        elif mix_mode == 'harman':
            freq = 0.15
            noise = (math.sin(x * freq) + math.cos(y * freq) + math.sin((x + y) * freq * 0.5)) / 3.0
            noise = max(0.0, min(1.0, (noise + 1.0) / 2.0 + random.uniform(-0.05, 0.05)))
            scaled_noise = noise * (num_colors - 1)
            idx1 = int(scaled_noise)
            idx2 = min(num_colors - 1, idx1 + 1)
            return lerp(mix_colors[idx1], mix_colors[idx2], scaled_noise - idx1)
        elif mix_mode == 'gradient_soft':
            transition_length = 500.0
            pos = (step_accum / transition_length) % 1.0
            scaled_pos = pos * (num_colors - 1)
            idx1 = int(scaled_pos)
            idx2 = min(num_colors - 1, idx1 + 1)
            return lerp(mix_colors[idx1], mix_colors[idx2], scaled_pos - idx1)
        elif mix_mode == 'marble':
            freq1, freq2 = 0.03, 0.015
            noise = math.sin(x * freq1 + math.cos(y * freq1)) + math.sin(y * freq2)
            noise = (noise + 2.0) / 4.0
            noise = max(0.0, min(1.0, noise))
            scaled_noise = noise * (num_colors - 1)
            idx1 = int(scaled_noise)
            idx2 = min(num_colors - 1, idx1 + 1)
            return lerp(mix_colors[idx1], mix_colors[idx2], scaled_noise - idx1)
        elif mix_mode == 'splatter':
            if random.random() > 0.8:
                return random.choice(mix_colors)
            return mix_colors[0]
        elif mix_mode == 'wave':
            wave = (math.sin(step_accum * 0.05) + 1.0) / 2.0
            scaled_wave = wave * (num_colors - 1)
            idx1 = int(scaled_wave)
            idx2 = min(num_colors - 1, idx1 + 1)
            return lerp(mix_colors[idx1], mix_colors[idx2], scaled_wave - idx1)
        elif mix_mode == 'pixel':
            return mix_colors[random.randint(0, num_colors - 1)]
        elif mix_mode == 'sponge':
            block_size = 15
            bx, by = int(x / block_size), int(y / block_size)
            seed = (bx * 73856093 ^ by * 19349663)
            return mix_colors[seed % num_colors]
        elif mix_mode == 'radial':
            cx, cy = self.mirror_line_x, self.mirror_line_y
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            pos = (dist / 300.0) % 1.0
            scaled_pos = pos * (num_colors - 1)
            idx1 = int(scaled_pos)
            idx2 = min(num_colors - 1, idx1 + 1)
            return lerp(mix_colors[idx1], mix_colors[idx2], scaled_pos - idx1)
        elif mix_mode == 'mist':
            freq = 0.08
            noise = (math.sin(x * freq) * math.cos(y * freq) + 1.0) / 2.0
            noise = max(0.0, min(1.0, noise + random.uniform(-0.1, 0.1)))
            scaled_noise = noise * (num_colors - 1)
            idx1 = int(scaled_noise)
            idx2 = min(num_colors - 1, idx1 + 1)
            return lerp(mix_colors[idx1], mix_colors[idx2], scaled_noise - idx1)
        else:
            return mix_colors[0]

    def enterEvent(self, event):
        self.setCursor(Qt.CrossCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def toCanvas(self, widget_pos):
        center_offset_x = 0
        center_offset_y = 0
        if self.width() > self.image.width() * self.zoom_factor:
            center_offset_x = (self.width() - self.image.width() * self.zoom_factor) / 2
        if self.height() > self.image.height() * self.zoom_factor:
            center_offset_y = (self.height() - self.image.height() * self.zoom_factor) / 2

        final_offset = self.view_offset + QPoint(int(center_offset_x), int(center_offset_y))
        return (widget_pos - final_offset) / self.zoom_factor

    def resizeEvent(self, event):
        self.mirror_line_x = self.image.width() // 2
        self.mirror_line_y = self.image.height() // 2
        super().resizeEvent(event)

    def generateSmoothCurvePath(self, points):
        if len(points) < 2:
            return QPainterPath()
        path = QPainterPath()
        path.moveTo(points[0])
        if len(points) == 2:
            path.lineTo(points[1])
            return path
        for i in range(len(points) - 1):
            p0 = points[i - 1] if i > 0 else points[i]
            p1 = points[i]
            p2 = points[i + 1]
            p3 = points[i + 2] if i < len(points) - 2 else points[i + 1]
            c1 = p1 + (p2 - p0) / 6.0
            c2 = p2 - (p3 - p1) / 6.0
            path.cubicTo(c1, c2, p2)
        return path

    def getMirroredPoint(self, p):
        parent = self.parent()
        if not parent:
            return p
        if parent.mirror_axis == 'vertical':
            return QPoint(int(self.mirror_line_x - (p.x() - self.mirror_line_x)), int(p.y()))
        else:
            return QPoint(int(p.x()), int(self.mirror_line_y - (p.y() - self.mirror_line_y)))

    def _get_scaled_reference(self, ref):
        """Önbellekten veya yeniden ölçekleyerek referans görselini döndür."""
        key = (ref['id'], ref['display_size'].width(), ref['display_size'].height())
        cached = self._reference_scaled_cache.get(key)
        if cached is not None and not cached.isNull():
            return cached
        scaled = ref['image'].scaled(ref['display_size'], Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._reference_scaled_cache[key] = scaled
        return scaled

    def _draw_reference(self, painter, parent, placing=False):
        """Referans görselini çizer. placing=True ise yerleştirme modunda tam opak çizer."""
        if self.reference_image is None:
            return
        painter.save()
        if not placing:
            transparency = max(0, min(95, int(getattr(parent, 'reference_transparency', 55)))) / 100.0
            painter.setOpacity(1.0 - transparency)
        else:
            painter.setOpacity(1.0)
        ref = self.reference_image
        if ref.get('visible', True) or placing:
            scaled = self._get_scaled_reference(ref)
            if scaled:
                painter.drawImage(ref['offset'], scaled)
        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1a1a1a"))
        painter.save()  # 1. save

        center_offset_x = 0
        center_offset_y = 0
        scaled_w = self.image.width() * self.zoom_factor
        scaled_h = self.image.height() * self.zoom_factor

        if self.width() > scaled_w:
            center_offset_x = (self.width() - scaled_w) / 2
        if self.height() > scaled_h:
            center_offset_y = (self.height() - scaled_h) / 2

        final_offset_x = self.view_offset.x() + center_offset_x
        final_offset_y = self.view_offset.y() + center_offset_y

        transform = QTransform()
        transform.translate(final_offset_x, final_offset_y)
        transform.scale(self.zoom_factor, self.zoom_factor)
        painter.setTransform(transform)

        parent = self.parent()

        # ---- ARKA PLAN RENGİ (EN ALTTA) ----
        if parent:
            painter.save()
            painter.fillRect(QRectF(0, 0, self.image.width(), self.image.height()), parent.background_color)
            painter.restore()
        else:
            painter.save()
            painter.fillRect(QRectF(0, 0, self.image.width(), self.image.height()), QColor("#333333"))
            painter.restore()

        # ---- OYNATMA: hazır kareyi göster, gerisini çizme ----
        if self.playback_frame is not None:
            painter.drawImage(0, 0, self.playback_frame)
            painter.restore()
            return

        # ---- REFERANS (ALTTA) ----
        if parent and not self.placing_reference and parent.global_reference_visible and self.reference_layer_position == 1:
            self._draw_reference(painter, parent, placing=False)

        # ---- ANA ÇİZİM (image) ----
        widget_rect = self.rect()
        inverted_transform, _ = transform.inverted()
        visible_rect_on_canvas = inverted_transform.mapRect(QRectF(widget_rect)).toRect()
        source_rect = visible_rect_on_canvas.intersected(self.image.rect())

        if not source_rect.isEmpty():
            self._paint_layers(painter, source_rect)
            # Soğan zarı (önceki/sonraki kareler): yalnızca ekranda, dışa aktarımda yok
            if self.onion_provider is not None:
                for onion_img, onion_opacity in self.onion_provider():
                    painter.save()
                    painter.setOpacity(onion_opacity)
                    painter.drawImage(source_rect, onion_img, source_rect)
                    painter.restore()

        self._paint_selection(painter)
        self._paint_points(painter)

        # ---- REFERANS (ÜSTTE) ----
        if parent and (self.placing_reference or (parent.global_reference_visible and self.reference_layer_position == 0)):
            self._draw_reference(painter, parent, placing=self.placing_reference)

        # ---- MİROR ÇİZGİSİ ----
        if parent and (parent.mirror_mode or self.dragging_mirror_line):
            painter.save()
            pen = QPen(QColor(100, 100, 100), 1 / self.zoom_factor, Qt.DashLine)
            if self.dragging_mirror_line:
                pen = QPen(QColor(255, 0, 0), 2 / self.zoom_factor, Qt.SolidLine)
            painter.setPen(pen)

            if parent.mirror_axis == 'vertical':
                line_pos = int(self.mirror_line_x)
                painter.drawLine(line_pos, visible_rect_on_canvas.top(), line_pos, visible_rect_on_canvas.bottom())
            else:
                line_pos = int(self.mirror_line_y)
                painter.drawLine(visible_rect_on_canvas.left(), line_pos, visible_rect_on_canvas.right(), line_pos)
            painter.restore()

        # Şekil Araçları Önizleme
        if parent and parent.current_tool_index in [37, 38] and self.drawing and len(self.current_stroke_points) >= 2:
            painter.save()
            pen_color, pen_width = parent.getCurrentPen()
            painter.setPen(QPen(pen_color, pen_width / self.zoom_factor, Qt.SolidLine))
            
            if parent.solid_fill_mode:
                if parent.eraser_mode:
                    painter.setBrush(Qt.NoBrush)
                else:
                    painter.setBrush(QBrush(QColor(pen_color.red(), pen_color.green(), pen_color.blue(), 100)))
            else:
                painter.setBrush(Qt.NoBrush)

            p1 = self.current_stroke_points[0]
            p2 = self.current_stroke_points[1]

            if parent.current_tool_index == 37: 
                rect = QRect(p1, p2).normalized()
                painter.drawRect(rect)
                if parent.mirror_mode:
                    m_p1 = self.getMirroredPoint(p1)
                    m_p2 = self.getMirroredPoint(p2)
                    m_rect = QRect(m_p1, m_p2).normalized()
                    painter.drawRect(m_rect)

            elif parent.current_tool_index == 38: 
                r = math.hypot(p2.x() - p1.x(), p2.y() - p1.y())
                painter.drawEllipse(p1, int(r), int(r))
                if parent.mirror_mode:
                    m_p1 = self.getMirroredPoint(p1)
                    painter.drawEllipse(m_p1, int(r), int(r))

            painter.restore()

        if self.isLayerEditable():
            if parent and not parent.polyline_mode and not parent.curve_mode and parent.current_tool_index not in [37, 38]:
                if self.current_stroke_points and len(self.current_stroke_points) > 2 and parent.solid_fill_mode and self.drawing:
                    painter.save()
                    if parent.eraser_mode:
                        painter.setBrush(Qt.NoBrush)
                    else:
                        fill_color = QColor(parent.pen_color.red(), parent.pen_color.green(), parent.pen_color.blue(), 100)
                        painter.setBrush(QBrush(fill_color))

                    painter.setPen(QPen(QColor(255, 255, 255, 150), 1, Qt.SolidLine))
                    painter.drawPolygon(QPolygon(self.current_stroke_points))

                    if parent.mirror_mode:
                        mirrored_poly = [self.getMirroredPoint(p) for p in self.current_stroke_points]
                        painter.drawPolygon(QPolygon(mirrored_poly))

                    painter.restore()

                elif self.current_stroke_points and len(self.current_stroke_points) > 1 and parent.current_tool_index != 36:
                    painter.save()
                    if parent.solid_fill_mode:
                        if parent.eraser_mode:
                             painter.setBrush(Qt.NoBrush)
                             painter.setPen(QPen(QColor(255, 255, 255, 150), 1 / self.zoom_factor, Qt.SolidLine))
                        else:
                            c = parent.pen_color
                            fill_color = QColor(c.red(), c.green(), c.blue(), 150)
                            painter.setBrush(QBrush(fill_color))
                            painter.setPen(QPen(c, 1 / self.zoom_factor, Qt.SolidLine))

                        painter.drawPolygon(QPolygon(self.current_stroke_points))
                        if parent.mirror_mode:
                            mirrored_poly = [self.getMirroredPoint(p) for p in self.current_stroke_points]
                            painter.drawPolygon(QPolygon(mirrored_poly))
                    painter.restore()

            if parent and (parent.polyline_mode or parent.curve_mode):
                active_points = self.polyline_points if parent.polyline_mode else self.curve_points
                if active_points:
                    painter.save()
                    if parent.eraser_mode:
                        poly_color = parent.background_color
                    elif len(parent.mix_colors) > 1:
                        poly_color = parent.mix_colors[0]
                    else:
                        poly_color = parent.pen_color

                    current_radius = parent.eraser_radius if parent.eraser_mode else parent.pen_radius

                    pen = QPen(poly_color, current_radius, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    painter.setPen(pen)
                    if len(active_points) > 1:
                        if parent.curve_mode:
                            path = self.generateSmoothCurvePath(active_points)
                            painter.setBrush(Qt.NoBrush)
                            painter.drawPath(path)
                            if parent.mirror_mode:
                                mirrored_pts = [self.getMirroredPoint(p) for p in active_points]
                                m_path = self.generateSmoothCurvePath(mirrored_pts)
                                painter.drawPath(m_path)
                        else:
                            if parent.current_tool_index == 36 and len(active_points) >= 2:
                                p1 = active_points[0]
                                p2 = active_points[-1]
                                painter.drawPolyline(QPolygon(active_points))
                                angle = math.atan2(active_points[-2].y() - p2.y(), active_points[-2].x() - p2.x())
                                arrow_len = current_radius * 3
                                p3 = QPoint(int(p2.x() + arrow_len * math.cos(angle + math.pi / 6)), int(p2.y() + arrow_len * math.sin(angle + math.pi / 6)))
                                p4 = QPoint(int(p2.x() + arrow_len * math.cos(angle - math.pi / 6)), int(p2.y() + arrow_len * math.sin(angle - math.pi / 6)))
                                painter.drawLine(p2, p3)
                                painter.drawLine(p2, p4)

                                if parent.mirror_mode:
                                    mirrored_pts = [self.getMirroredPoint(p) for p in active_points]
                                    painter.drawPolyline(QPolygon(mirrored_pts))
                                    mp2 = mirrored_pts[-1]
                                    mp_prev = mirrored_pts[-2]
                                    m_angle = math.atan2(mp_prev.y() - mp2.y(), mp_prev.x() - mp2.x())
                                    mp3 = QPoint(int(mp2.x() + arrow_len * math.cos(m_angle + math.pi / 6)), int(mp2.y() + arrow_len * math.sin(m_angle + math.pi / 6)))
                                    mp4 = QPoint(int(mp2.x() + arrow_len * math.cos(m_angle - math.pi / 6)), int(mp2.y() + arrow_len * math.sin(m_angle - math.pi / 6)))
                                    painter.drawLine(mp2, mp3)
                                    painter.drawLine(mp2, mp4)
                            else:
                                painter.drawPolyline(QPolygon(active_points))
                                if parent.mirror_mode:
                                    mirrored_pts = [self.getMirroredPoint(p) for p in active_points]
                                    painter.drawPolyline(QPolygon(mirrored_pts))

                    painter.setPen(Qt.NoPen)
                    radius = max(5, (current_radius + 2)) / self.zoom_factor
                    points_to_draw = [(p, False) for p in active_points]
                    if parent.mirror_mode:
                        for p in active_points:
                            points_to_draw.append((self.getMirroredPoint(p), True))
                    for i, (pt, is_mirrored) in enumerate(points_to_draw):
                        is_hovered = False
                        if not is_mirrored:
                             if i == self.hovered_poly_point_index:
                                 is_hovered = True
                        if is_hovered:
                            painter.setBrush(QColor(255, 0, 0))
                        else:
                            painter.setBrush(QColor(0, 255, 255) if not is_mirrored else QColor(0, 150, 150))
                        painter.drawEllipse(pt, radius, radius)
                    painter.restore()

        if self.original_image_for_placement and self.current_image_display_size.isValid():
            scaled_temp_image = self.original_image_for_placement.scaled(
                self.current_image_display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            final_pos = self.image_placement_offset

            if parent and parent.mirror_mode:
                painter.save()
                if parent.mirror_axis == 'vertical':
                    mirror_line_screen = self.mirror_line_x
                    painter.setClipRect(0, 0, int(mirror_line_screen) + 1, self.image.height())
                    painter.drawImage(final_pos, scaled_temp_image)

                    painter.setClipRect(int(mirror_line_screen), 0, self.image.width(), self.image.height())

                    mirrored_x = 2 * mirror_line_screen - final_pos.x() - scaled_temp_image.width()
                    mirrored_pos = QPoint(int(mirrored_x), final_pos.y())
                    mirrored_image = scaled_temp_image.mirrored(True, False)
                    painter.drawImage(mirrored_pos, mirrored_image)

                else:
                    mirror_line_screen = self.mirror_line_y
                    painter.setClipRect(0, 0, self.image.width(), int(mirror_line_screen) + 1)
                    painter.drawImage(final_pos, scaled_temp_image)

                    painter.setClipRect(0, int(mirror_line_screen), self.image.width(), self.image.height())

                    mirrored_y = 2 * mirror_line_screen - final_pos.y() - scaled_temp_image.height()
                    mirrored_pos = QPoint(final_pos.x(), int(mirrored_y))

                    mirrored_image = scaled_temp_image.mirrored(False, True)
                    painter.drawImage(mirrored_pos, mirrored_image)

                painter.restore()
            else:
                painter.drawImage(final_pos, scaled_temp_image)

        # Cursor preview (sadece parent varsa)
        if parent:
            if parent.eraser_mode and not parent.nav_button.isChecked():
                mouse_canvas = self.mapFromGlobal(QCursor.pos())
                if self.rect().contains(mouse_canvas):
                    painter.save()
                    painter.setPen(QPen(QColor(255, 255, 255), 0))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(mouse_canvas, 0, 0)
                    painter.restore()

            if parent.lazy_mouse_enabled and self.lazy_mouse_pos is not None:
                painter.save()

                transform = QTransform()
                transform.translate(final_offset_x, final_offset_y)
                transform.scale(self.zoom_factor, self.zoom_factor)
                painter.setTransform(transform)

                if self.lazy_target_pos is not None:
                    lazy_radius = parent.lazy_radius
                    painter.setPen(QPen(QColor(100, 200, 255, 150), 1 / self.zoom_factor, Qt.DashLine))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(self.lazy_target_pos, lazy_radius, lazy_radius)

                    painter.setPen(QPen(QColor(255, 150, 0), 2 / self.zoom_factor)) 
                    painter.setBrush(QColor(255, 200, 100, 200))
                    painter.drawEllipse(self.lazy_mouse_pos, 5 / self.zoom_factor, 5 / self.zoom_factor)

                    painter.setPen(QPen(QColor(255, 150, 0, 100), 1 / self.zoom_factor, Qt.DotLine))
                    painter.drawLine(self.lazy_target_pos, self.lazy_mouse_pos)

                painter.restore()

        painter.restore()  # 1. restore

    def keyPressEvent(self, event):
        parent = self.parent()
        if not parent:
            super().keyPressEvent(event)
            return
        if parent.polyline_mode or parent.curve_mode:
            active_points = self.polyline_points if parent.polyline_mode else self.curve_points
            if event.key() == Qt.Key_Delete:
                if active_points:
                    active_points.pop()
                    self.hovered_poly_point_index = -1
                    self.update()
        super().keyPressEvent(event)

    def tabletEvent(self, event):
        if event.type() == QTabletEvent.TabletPress or event.type() == QTabletEvent.TabletMove:
            self.last_pressure = event.pressure()
        elif event.type() == QTabletEvent.TabletRelease:
            self.last_pressure = 1.0
        event.ignore()

    def startReferencePlacement(self, ref_image):
        if self.parent():
            self.parent().is_project_modified = True

        # Önceki referansı temizle (sadece bir tane)
        self.reference_image = None

        max_width = max(20, int(self.image.width() * 0.85))
        max_height = max(20, int(self.image.height() * 0.85))
        initial_size = ref_image.size().scaled(max_width, max_height, Qt.KeepAspectRatio)

        ref_id = 1
        if self.parent() and hasattr(self.parent(), 'next_reference_id'):
            ref_id = self.parent().next_reference_id
            self.parent().next_reference_id += 1
        else:
            ref_id = 1

        new_ref = {
            'id': ref_id,
            'image': ref_image.convertToFormat(QImage.Format_ARGB32),
            'offset': QPoint(
                max(0, (self.image.width() - initial_size.width()) // 2),
                max(0, (self.image.height() - initial_size.height()) // 2)
            ),
            'display_size': initial_size,
            'visible': True
        }
        self.reference_image = new_ref
        self.placing_reference = True
        self._reference_scaled_cache.clear()

        if self.parent():
            self.parent().nav_button.setChecked(False)
            self.parent().nav_button.updateStyle()
        self.setCursor(Qt.CrossCursor)
        self.update()

    def cancelReferencePlacement(self):
        self.placing_reference = False
        self.setCursor(Qt.ArrowCursor)
        self.updateImageFromElements()
        if self.parent():
            self.parent().updateButtonStyles()
        self.update()

    def mousePressEvent(self, event):
        parent = self.parent()
        if not parent:
            return
        if self.playback_frame is not None:
            if self.playback_stop_cb:
                self.playback_stop_cb()
            return
        if self.select_active and self.selectMousePress(event):
            return
        if self.point_active and self.ptMousePress(event):
            return
        canvas_pos_float = self.toCanvas(event.pos())
        canvas_pos = QPoint(int(canvas_pos_float.x()), int(canvas_pos_float.y()))

        is_o_mode = parent.nav_button.isChecked()

        if event.button() == Qt.LeftButton:
            pass
        elif event.button() == Qt.MidButton and is_o_mode and not parent.placing_image:
            self.panning = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return

        if self.alt_held and event.button() == Qt.LeftButton:
            pass

        if (event.modifiers() & Qt.ShiftModifier) and event.button() == Qt.LeftButton and is_o_mode:
            self.panning = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return

        layer_active = self.isLayerEditable()

        if parent.text_mode and layer_active and event.button() == Qt.LeftButton:
             self.text_input_widget.move(event.pos())
             self.text_input_widget.show()
             self.text_input_widget.setFocus()
             self.text_input_widget.clear()
             base_size = max(10, parent.pen_radius * 2)
             scaled_size = int(base_size * self.zoom_factor)
             self.text_input_widget.setFont(QFont("Arial", scaled_size))
             self.text_input_widget.updateGeometry() 
             return

        if parent.polyline_mode or parent.curve_mode:
            if not layer_active:
                return
            active_points = self.polyline_points if parent.polyline_mode else self.curve_points

            if (event.modifiers() & Qt.ControlModifier) and event.button() == Qt.LeftButton:
                self.dragging_whole_polyline = True
                self.last_poly_drag_pos = canvas_pos
                self.setCursor(Qt.SizeAllCursor)
                return
            if parent.is_c_pressed and event.button() == Qt.MiddleButton:
                self.dragging_whole_polyline = True
                self.last_poly_drag_pos = canvas_pos
                self.setCursor(Qt.SizeAllCursor)
                return
            if event.button() == Qt.LeftButton:
                active_points.append(canvas_pos)
                self.update()
                return
            elif event.button() == Qt.MidButton:
                if self.hovered_poly_point_index != -1 and not parent.is_c_pressed:
                    self.dragging_poly_point_index = self.hovered_poly_point_index
                    self.setCursor(Qt.ClosedHandCursor)
                return
            elif event.button() == Qt.RightButton:
                menu = QMenu(self)
                menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")

                finish_action = menu.addAction("Bitir (Enter)")
                menu.addSeparator()

                delete_last_action = menu.addAction("Delete Last Point")
                menu.addSeparator()
                reset_action = menu.addAction("Reset")
                action = menu.exec_(self.mapToGlobal(event.pos()))

                if action == finish_action:
                    self.finalizePolyline()
                elif action == delete_last_action:
                    if active_points:
                        active_points.pop()
                elif action == reset_action:
                    if parent.polyline_mode:
                        self.polyline_points = []
                    else:
                        self.curve_points = []
                self.update()
                return

        if event.button() == Qt.MiddleButton and not is_o_mode:
            if hasattr(parent, 'is_v_pressed') and parent.is_v_pressed:
                 self.dragging_mirror_line = True
                 self.last_pan_pos = event.pos()
                 self.setCursor(Qt.SizeHorCursor)
                 return

        if event.button() == Qt.RightButton and not parent.placing_image and not parent.polyline_mode and not parent.curve_mode:
            if self.rect().contains(event.pos()):
                if 0 <= canvas_pos.x() < self.image.width() and 0 <= canvas_pos.y() < self.image.height():
                    picked_color = self.image.pixelColor(canvas_pos)
                    menu = QMenu(self)
                    menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
                    info_action = QAction(create_svg_icon(SVG_UNDO_ICON, size=16, color=picked_color.name()), f"Selected Color: {picked_color.name()}", self)
                    info_action.setEnabled(False)
                    menu.addAction(info_action)
                    menu.addSeparator()
                    copy_action = menu.addAction(f"Copy Hex ({picked_color.name().upper()})")
                    change_action = menu.addAction("Change This Color")
                    delete_action = menu.addAction("Delete This Color (Remove)")
                    action = menu.exec_(self.mapToGlobal(event.pos()))
                    if action == copy_action:
                        clipboard = QApplication.clipboard()
                        clipboard.setText(picked_color.name().upper())
                    elif action == change_action or action == delete_action:
                        reply = QMessageBox.question(self, "Replacement Mode", "Apply to entire drawing (Global) or only connected area (Connected)?",
                                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                        mode = 'global' if reply == QMessageBox.Yes else 'connected'
                        if action == change_action:
                            dialog = CircleBrightnessDialog(initialColor=picked_color, parent=self)
                            dialog.move(self.mapToGlobal(event.pos()))
                            if dialog.exec_():
                                new_color = dialog.getSelectedColor()
                                self.replaceColor(picked_color, new_color, is_delete=False, mode=mode, pos=canvas_pos)
                        elif action == delete_action:
                            bg_col = parent.background_color
                            self.replaceColor(picked_color, bg_col, is_delete=True, mode=mode, pos=canvas_pos)
            return

        if self.placing_reference and event.button() == Qt.LeftButton:
            self.placing_reference = False
            if parent:
                parent.updateCurrentPageReferenceData()
            self.setCursor(Qt.ArrowCursor)
            self.updateImageFromElements()
            parent.updateButtonStyles()
            return

        if self.placing_reference and (event.button() == Qt.MiddleButton or event.button() == Qt.RightButton):
            self.dragging_image = True
            self.last_drag_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if parent.placing_image and layer_active:
            if event.button() == Qt.LeftButton:
                if self.original_image_for_placement and self.current_image_display_size.isValid():
                    self.saveStateForUndo(deep_copy=True)

                    if parent.mirror_mode:
                        final_pos = self.image_placement_offset
                        orig_img = self.original_image_for_placement
                        scale_x = orig_img.width() / self.current_image_display_size.width()
                        scale_y = orig_img.height() / self.current_image_display_size.height()

                        if parent.mirror_axis == 'vertical':
                            mirror_line = self.mirror_line_x
                            rect_1 = QRect(final_pos, self.current_image_display_size)
                            clip_rect_1 = QRect(rect_1.x(), rect_1.y(), int(mirror_line - rect_1.x()) + 1, rect_1.height())
                            final_rect_1 = rect_1.intersected(clip_rect_1)

                            if final_rect_1.width() > 0 and final_rect_1.height() > 0:
                                off_x = (final_rect_1.x() - rect_1.x()) * scale_x
                                off_y = (final_rect_1.y() - rect_1.y()) * scale_y
                                cw = final_rect_1.width() * scale_x
                                ch = final_rect_1.height() * scale_y
                                cropped_1 = orig_img.copy(int(off_x), int(off_y), int(cw), int(ch))
                                b1 = QByteArray()
                                bu1 = QBuffer(b1)
                                bu1.open(QIODevice.WriteOnly)
                                cropped_1.save(bu1, "PNG")
                                b64_1 = base64.b64encode(b1.data()).decode('utf-8')
                                self.drawing_elements.append({
                                    "type": "image", "base64_data": b64_1,
                                    "position": [final_rect_1.x(), final_rect_1.y()],
                                    "original_width": cropped_1.width(), "original_height": cropped_1.height(),
                                    "current_width": final_rect_1.width(), "current_height": final_rect_1.height(),
                                    "layer": self.current_layer_name
                                })

                            scaled_w = self.current_image_display_size.width()
                            mirrored_x = 2 * mirror_line - final_pos.x() - scaled_w
                            mirrored_pos = QPoint(int(mirrored_x), final_pos.y())
                            rect_2 = QRect(mirrored_pos, self.current_image_display_size)
                            clip_rect_2 = QRect(int(mirror_line), rect_2.y(), 99999, rect_2.height())
                            final_rect_2 = rect_2.intersected(clip_rect_2)

                            if final_rect_2.width() > 0 and final_rect_2.height() > 0:
                                full_mirrored = orig_img.mirrored(True, False)
                                off_x_2 = (final_rect_2.x() - rect_2.x()) * scale_x
                                off_y_2 = (final_rect_2.y() - rect_2.y()) * scale_y
                                cw_2 = final_rect_2.width() * scale_x
                                ch_2 = final_rect_2.height() * scale_y
                                cropped_2 = full_mirrored.copy(int(off_x_2), int(off_y_2), int(cw_2), int(ch_2))
                                b2 = QByteArray()
                                bu2 = QBuffer(b2)
                                bu2.open(QIODevice.WriteOnly)
                                cropped_2.save(bu2, "PNG")
                                b64_2 = base64.b64encode(b2.data()).decode('utf-8')
                                self.drawing_elements.append({
                                    "type": "image", "base64_data": b64_2,
                                    "position": [final_rect_2.x(), final_rect_2.y()],
                                    "original_width": cropped_2.width(), "original_height": cropped_2.height(),
                                    "current_width": final_rect_2.width(), "current_height": final_rect_2.height(),
                                    "layer": self.current_layer_name
                                })
                        else:
                            mirror_line = self.mirror_line_y
                            rect_1 = QRect(final_pos, self.current_image_display_size)
                            clip_rect_1 = QRect(rect_1.x(), rect_1.y(), rect_1.width(), int(mirror_line - rect_1.y()) + 1)
                            final_rect_1 = rect_1.intersected(clip_rect_1)

                            if final_rect_1.height() > 0:
                                off_x = (final_rect_1.x() - rect_1.x()) * scale_x
                                off_y = (final_rect_1.y() - rect_1.y()) * scale_y
                                cw = final_rect_1.width() * scale_x
                                ch = final_rect_1.height() * scale_y
                                cropped_1 = orig_img.copy(int(off_x), int(off_y), int(cw), int(ch))
                                b1 = QByteArray()
                                bu1 = QBuffer(b1)
                                bu1.open(QIODevice.WriteOnly)
                                cropped_1.save(bu1, "PNG")
                                b64_1 = base64.b64encode(b1.data()).decode('utf-8')
                                self.drawing_elements.append({
                                    "type": "image", "base64_data": b64_1,
                                    "position": [final_rect_1.x(), final_rect_1.y()],
                                    "original_width": cropped_1.width(), "original_height": cropped_1.height(),
                                    "current_width": final_rect_1.width(), "current_height": final_rect_1.height(),
                                    "layer": self.current_layer_name
                                })

                            scaled_h = self.current_image_display_size.height()
                            mirrored_y = 2 * mirror_line - final_pos.y() - scaled_h
                            mirrored_pos = QPoint(final_pos.x(), int(mirrored_y))
                            rect_2 = QRect(mirrored_pos, self.current_image_display_size)
                            clip_rect_2 = QRect(rect_2.x(), int(mirror_line), rect_2.width(), 99999)
                            final_rect_2 = rect_2.intersected(clip_rect_2)

                            if final_rect_2.height() > 0:
                                full_mirrored = orig_img.mirrored(False, True)
                                off_x_2 = (final_rect_2.x() - rect_2.x()) * scale_x
                                off_y_2 = (final_rect_2.y() - rect_2.y()) * scale_y
                                cw_2 = final_rect_2.width() * scale_x
                                ch_2 = final_rect_2.height() * scale_y
                                cropped_2 = full_mirrored.copy(int(off_x_2), int(off_y_2), int(cw_2), int(ch_2))
                                b2 = QByteArray()
                                bu2 = QBuffer(b2)
                                bu2.open(QIODevice.WriteOnly)
                                cropped_2.save(bu2, "PNG")
                                b64_2 = base64.b64encode(b2.data()).decode('utf-8')
                                self.drawing_elements.append({
                                    "type": "image", "base64_data": b64_2,
                                    "position": [final_rect_2.x(), final_rect_2.y()],
                                    "original_width": cropped_2.width(), "original_height": cropped_2.height(),
                                    "current_width": final_rect_2.width(), "current_height": final_rect_2.height(),
                                    "layer": self.current_layer_name
                                })
                    else:
                        buffer = QByteArray()
                        buffer_io = QBuffer(buffer)
                        buffer_io.open(QIODevice.WriteOnly)
                        self.original_image_for_placement.save(buffer_io, "PNG")
                        base64_data = base64.b64encode(buffer.data()).decode('utf-8')
                        self.drawing_elements.append({
                            "type": "image", "base64_data": base64_data,
                            "position": [self.image_placement_offset.x(), self.image_placement_offset.y()],
                            "original_width": self.original_image_for_placement.width(), "original_height": self.original_image_for_placement.height(),
                            "current_width": self.current_image_display_size.width(), "current_height": self.current_image_display_size.height(),
                            "layer": self.current_layer_name
                        })

                    self.updateImageFromElements()
                    self.cancelImagePlacement()
                    parent.updateButtonStyles()
                return

            elif event.button() == Qt.MiddleButton or event.button() == Qt.RightButton:
                self.dragging_image = True
                self.last_drag_pos = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return

        elif event.button() == Qt.LeftButton and layer_active:
            self.saveStateForUndo(deep_copy=False)
            
            self.lastPoint = canvas_pos
            self.last_widget_pos = event.pos() 
            self.drawing = True
            
            self._actively_modifying = True

            if parent.lazy_mouse_enabled:
                self.lazy_mouse_pos = QPointF(canvas_pos)
                self.lazy_target_pos = QPointF(canvas_pos)
                self.lazy_velocity = QPointF(0, 0)

            if parent.current_tool_index in [37, 38]:
                self.current_stroke_points = [canvas_pos, canvas_pos]
                self.update()
                return

            if parent.eraser_mode:
                pen_color = QColor(0, 0, 0)
                pen_width = parent.eraser_radius
            else:
                pen_color, pen_width = parent.getCurrentPen()

            if parent.pen_pressure_enabled:
                sensitivity_multiplier = 1.0
                if parent.sensitivity_value != -1: 
                    sensitivity_multiplier = parent.sensitivity_value / 50.0

                adjusted_pressure = self.last_pressure * sensitivity_multiplier
                pen_width = max(1, pen_width * adjusted_pressure)

            self.current_stroke_points = [canvas_pos]
            self.current_mix_index = 0
            self.stroke_length_accumulator = 0.0

            if not parent.eraser_mode and len(parent.mix_colors) > 1:
                pen_color = self.calculateMixColor(canvas_pos.x(), canvas_pos.y(), self.stroke_length_accumulator, parent.mix_colors, parent.mix_mode, parent.mix_angle, self.current_mix_index)
                if parent.mix_mode == 'sequential':
                    self.current_mix_index += 1

            self.current_stroke_pen_info = [[pen_color, pen_width]]

            if not parent.solid_fill_mode:
                painter = QPainter(self.image)
                painter.setRenderHint(QPainter.Antialiasing)

                if parent.eraser_mode:
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)

                if parent.current_tool_index >= 6 and parent.current_tool_index != 36:
                    self.drawBrushStroke(painter, canvas_pos, canvas_pos, pen_color, pen_width, parent.current_tool_index)
                    if parent.mirror_mode:
                        mirrored_pos = self.getMirroredPoint(canvas_pos)
                        self.drawBrushStroke(painter, mirrored_pos, mirrored_pos, pen_color, pen_width, parent.current_tool_index)
                else:
                    painter.setPen(QPen(pen_color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    painter.drawPoint(canvas_pos)
                    if parent.mirror_mode:
                        mirrored_pos = self.getMirroredPoint(canvas_pos)
                        painter.drawPoint(mirrored_pos)
                painter.end()

            self.update()

    def mouseMoveEvent(self, event):
        parent = self.parent()
        if not parent:
            return
        if self.select_active and self.selectMouseMove(event):
            return
        if self.point_active and self.ptMouseMove(event):
            return
        is_o_mode = parent.nav_button.isChecked()

        needs_full_update = False
        if parent.eraser_mode or parent.lazy_mouse_enabled or self.dragging_image or (self.panning and is_o_mode) or self.dragging_mirror_line or self.dragging_whole_polyline or self.placing_reference:
            needs_full_update = True
        elif parent.polyline_mode or parent.curve_mode or parent.mirror_mode:
            needs_full_update = True

        if needs_full_update:
            self.update()

        if self.panning and is_o_mode:
            delta = event.pos() - self.last_pan_pos
            self.view_offset += delta

            scaled_w = self.image.width() * self.zoom_factor
            scaled_h = self.image.height() * self.zoom_factor
            limit_x = max(self.width(), int(scaled_w)) + 200
            limit_y = max(self.height(), int(scaled_h)) + 200

            x = max(-limit_x, min(limit_x, self.view_offset.x()))
            y = max(-limit_y, min(limit_y, self.view_offset.y()))

            self.view_offset = QPoint(x, y)

            self.last_pan_pos = event.pos()
            self.update()
            return

        canvas_pos_float = self.toCanvas(event.pos())
        canvas_pos = QPoint(int(canvas_pos_float.x()), int(canvas_pos_float.y()))
        
        if parent.lazy_mouse_enabled:
            target_pos = QPointF(canvas_pos_float)
            self.lazy_target_pos = target_pos
            
            lazy_radius = parent.lazy_radius
            lazy_factor = parent.lazy_factor / 100.0  
            
            if self.lazy_mouse_pos is None:
                self.lazy_mouse_pos = QPointF(canvas_pos_float)
                self.lazy_velocity = QPointF(0, 0)
            
            if self.drawing:
                dx = target_pos.x() - self.lazy_mouse_pos.x()
                dy = target_pos.y() - self.lazy_mouse_pos.y()
                distance = math.sqrt(dx * dx + dy * dy)

                if distance > lazy_radius:
                    excess_distance = distance - lazy_radius
                    if distance > 0:
                        nx = dx / distance
                        ny = dy / distance
                    else:
                        nx, ny = 0, 0

                    self.lazy_velocity.setX(self.lazy_velocity.x() * (1 - self.lazy_damping) + nx * excess_distance * lazy_factor * 2)
                    self.lazy_velocity.setY(self.lazy_velocity.y() * (1 - self.lazy_damping) + ny * excess_distance * lazy_factor * 2)

                    new_x = self.lazy_mouse_pos.x() + self.lazy_velocity.x()
                    new_y = self.lazy_mouse_pos.y() + self.lazy_velocity.y()
                    self.lazy_mouse_pos = QPointF(new_x, new_y)
                else:
                    self.lazy_velocity.setX(self.lazy_velocity.x() * (1 - self.lazy_damping * 0.5))
                    self.lazy_velocity.setY(self.lazy_velocity.y() * (1 - self.lazy_damping * 0.5))

                canvas_pos = QPoint(int(self.lazy_mouse_pos.x()), int(self.lazy_mouse_pos.y()))
            else:
                self.lazy_mouse_pos = QPointF(canvas_pos_float)

        if self.dragging_mirror_line:
            if parent.mirror_axis == 'vertical':
                delta_x = event.pos().x() - self.last_pan_pos.x()
                self.mirror_line_x += delta_x / self.zoom_factor
            else:
                delta_y = event.pos().y() - self.last_pan_pos.y()
                self.mirror_line_y += delta_y / self.zoom_factor
            self.last_pan_pos = event.pos()
            self.update()
            return

        if self.dragging_whole_polyline:
            active_points = self.polyline_points if parent.polyline_mode else self.curve_points
            delta = canvas_pos - self.last_poly_drag_pos
            if parent.polyline_mode:
                self.polyline_points = [p + delta for p in active_points]
            else:
                self.curve_points = [p + delta for p in active_points]
            self.last_poly_drag_pos = canvas_pos
            self.update()
            return

        if parent.polyline_mode or parent.curve_mode:
            active_points = self.polyline_points if parent.polyline_mode else self.curve_points
            current_radius = parent.eraser_radius if parent.eraser_mode else parent.pen_radius

            if self.dragging_poly_point_index != -1:
                active_points[self.dragging_poly_point_index] = canvas_pos
                self.update()
            else:
                radius = max(5, current_radius + 5) / self.zoom_factor
                found = -1
                for i, pt in enumerate(active_points):
                    if (pt - canvas_pos).manhattanLength() < radius:
                        found = i
                        break
                if found != self.hovered_poly_point_index:
                    self.hovered_poly_point_index = found
                    self.update()
            if self.dragging_poly_point_index != -1:
                return

        if self.dragging_image and self.placing_reference:
            delta_widget = event.pos() - self.last_drag_pos
            delta_canvas = QPoint(
                int(round(delta_widget.x() / max(self.zoom_factor, 0.0001))),
                int(round(delta_widget.y() / max(self.zoom_factor, 0.0001)))
            )
            if self.reference_image is not None:
                self.reference_image['offset'] += delta_canvas
                self._reference_scaled_cache.clear()
            self.last_drag_pos = event.pos()
            self.update()
            event.accept()
            return

        if self.dragging_image:
            delta = event.pos() - self.last_drag_pos
            self.image_placement_offset += delta
            self.last_drag_pos = event.pos()
            self.applyImagePlacementBounds()
            self.update()
            event.accept()
            return

        if not self.isLayerEditable():
            return

        if (event.buttons() & Qt.LeftButton) and self.drawing and not parent.polyline_mode and not parent.curve_mode:
            
            if parent.current_tool_index in [37, 38]:
                if len(self.current_stroke_points) >= 2:
                    self.current_stroke_points[1] = canvas_pos
                    self.update()
                return

            if parent.current_tool_index == 36:
                return

            if parent.eraser_mode:
                pen_color = QColor(0, 0, 0)
                pen_width = parent.eraser_radius
            elif len(parent.mix_colors) > 1:
                pen_color = random.choice(parent.mix_colors) if parent.mix_mode == 'random' else parent.pen_color
                pen_width = parent.pen_radius
            else: 
                pen_color, pen_width = parent.getCurrentPen()

            if parent.pen_pressure_enabled:
                 sensitivity_multiplier = 1.0
                 if parent.sensitivity_value != -1:
                     sensitivity_multiplier = parent.sensitivity_value / 50.0
                 adjusted_pressure = self.last_pressure * sensitivity_multiplier
                 pen_width = max(1, pen_width * adjusted_pressure)

            if not self.current_stroke_points:
                self.current_stroke_points.append(canvas_pos)
                self.current_stroke_pen_info.append([pen_color, pen_width])
                self.lastPoint = canvas_pos
            else:
                last_point_in_stroke = self.current_stroke_points[-1]
                dx = canvas_pos.x() - last_point_in_stroke.x()
                dy = canvas_pos.y() - last_point_in_stroke.y()
                distance = math.sqrt(dx*dx + dy*dy)

                step_size = max(1, pen_width / 2.0)

                scatter_tools = [15, 18, 19, 20, 21, 22] 
                if parent.current_tool_index in scatter_tools:
                    step_size = max(15, pen_width * 1.5)
                elif parent.current_tool_index >= 6:
                    step_size = 2

                if not parent.solid_fill_mode:
                    painter = QPainter(self.image)
                    painter.setRenderHint(QPainter.Antialiasing)

                    if parent.eraser_mode:
                        painter.setCompositionMode(QPainter.CompositionMode_Clear)

                    if distance > step_size:
                        num_steps = int(distance / step_size)
                        for i in range(1, num_steps + 1):
                            interp_x = last_point_in_stroke.x() + (dx * i / num_steps)
                            interp_y = last_point_in_stroke.y() + (dy * i / num_steps)
                            interpolated_point = QPoint(int(interp_x), int(interp_y))

                            interp_color = pen_color
                            if not parent.eraser_mode and len(parent.mix_colors) > 1:
                                self.stroke_length_accumulator += step_size
                                interp_color = self.calculateMixColor(interp_x, interp_y, self.stroke_length_accumulator, parent.mix_colors, parent.mix_mode, parent.mix_angle, self.current_mix_index)
                                if parent.mix_mode == 'sequential':
                                    self.current_mix_index += 1

                            if parent.current_tool_index >= 6:
                                self.drawBrushStroke(painter, self.lastPoint, interpolated_point, interp_color, pen_width, parent.current_tool_index)
                                if parent.mirror_mode:
                                    mirrored_last = self.getMirroredPoint(self.lastPoint)
                                    mirrored_interp = self.getMirroredPoint(interpolated_point)
                                    self.drawBrushStroke(painter, mirrored_last, mirrored_interp, interp_color, pen_width, parent.current_tool_index)
                            else:
                                painter.setPen(QPen(interp_color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                                painter.drawLine(self.lastPoint, interpolated_point)
                                if parent.mirror_mode:
                                    mirrored_last = self.getMirroredPoint(self.lastPoint)
                                    mirrored_curr = self.getMirroredPoint(interpolated_point)
                                    painter.drawLine(mirrored_last, mirrored_curr)

                            self.current_stroke_points.append(interpolated_point)
                            self.current_stroke_pen_info.append([interp_color, pen_width])
                            self.lastPoint = interpolated_point

                    if parent.current_tool_index >= 6:
                        self.drawBrushStroke(painter, self.lastPoint, canvas_pos, pen_color, pen_width, parent.current_tool_index)
                        if parent.mirror_mode:
                            mirrored_last = self.getMirroredPoint(self.lastPoint)
                            mirrored_curr = self.getMirroredPoint(canvas_pos)
                            self.drawBrushStroke(painter, mirrored_last, mirrored_curr, pen_color, pen_width, parent.current_tool_index)
                    else:
                        painter.setPen(QPen(pen_color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                        painter.drawLine(self.lastPoint, canvas_pos)
                        if parent.mirror_mode:
                            mirrored_last = self.getMirroredPoint(self.lastPoint)
                            mirrored_curr = self.getMirroredPoint(canvas_pos)
                            painter.drawLine(mirrored_last, mirrored_curr)

                    painter.end()

                self.current_stroke_points.append(canvas_pos)
                self.current_stroke_pen_info.append([pen_color, pen_width])
                self.lastPoint = canvas_pos

                if parent.solid_fill_mode or needs_full_update:
                    self.update()
                else:
                    padding = int((pen_width * self.zoom_factor) + 100)
                    min_x = min(self.last_widget_pos.x(), event.pos().x()) - padding
                    min_y = min(self.last_widget_pos.y(), event.pos().y()) - padding
                    max_x = max(self.last_widget_pos.x(), event.pos().x()) + padding
                    max_y = max(self.last_widget_pos.y(), event.pos().y()) + padding
                    update_rect = QRect(min_x, min_y, max_x - min_x, max_y - min_y)
                    self.update(update_rect)

                self.last_widget_pos = event.pos()

    def createSolidFill(self, points_to_draw, is_mirrored_shape=False):
        parent = self.parent()
        if not parent:
            return
        if not points_to_draw or len(points_to_draw) < 3:
            return

        if parent.eraser_mode:
            final_fill_color = QColor(0, 0, 0)
        elif len(self.current_stroke_pen_info) > 0 and len(parent.mix_colors) > 1:
            final_fill_color = self.current_stroke_pen_info[-1][0]
        else:
            final_fill_color = parent.pen_color

        min_x = min(p.x() for p in points_to_draw)
        max_x = max(p.x() for p in points_to_draw)
        min_y = min(p.y() for p in points_to_draw)
        max_y = max(p.y() for p in points_to_draw)
        w = max(1, max_x - min_x)
        h = max(1, max_y - min_y)

        path = QPainterPath()
        path.moveTo(points_to_draw[0])
        for p in points_to_draw[1:]:
            path.lineTo(p)
        path.closeSubpath()

        painter = QPainter(self.image)
        painter.setRenderHint(QPainter.Antialiasing)

        if parent.eraser_mode:
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(Qt.black))
            painter.drawPath(path)
            painter.end()
            element_data = {
                "type": "stroke", "points": [[p.x(), p.y()] for p in points_to_draw],
                "color": [0, 0, 0, 0],
                "width": 1, "pressure_enabled": False, "is_solid_fill": True, "is_eraser": True,
                "layer": self.current_layer_name
            }
            self._append_live(element_data)
            return

        border_pen = QPen(final_fill_color, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(border_pen)

        texture_b64 = None
        if not parent.eraser_mode and len(parent.mix_colors) > 1:
            if parent.mix_mode == 'smooth':
                center = QPointF(min_x + w/2, min_y + h/2)
                angle_rad = math.radians(parent.mix_angle)
                r = math.sqrt(w*w + h*h) / 2
                start_point = QPointF(center.x() - r * math.cos(angle_rad), center.y() - r * math.sin(angle_rad))
                end_point = QPointF(center.x() + r * math.cos(angle_rad), center.y() + r * math.sin(angle_rad))
                gradient = QLinearGradient(start_point, end_point)
                for i, col in enumerate(parent.mix_colors):
                    pos = i / (len(parent.mix_colors) - 1) if len(parent.mix_colors) > 1 else 0
                    gradient.setColorAt(pos, col)
                painter.setBrush(QBrush(gradient))
                painter.drawPath(path)

                pattern_img = QImage(w, h, QImage.Format_ARGB32)
                pattern_img.fill(Qt.transparent)
                p_painter = QPainter(pattern_img)
                p_painter.setRenderHint(QPainter.Antialiasing)
                local_start = start_point - QPointF(min_x, min_y)
                local_end = end_point - QPointF(min_x, min_y)
                local_gradient = QLinearGradient(local_start, local_end)
                for i, col in enumerate(parent.mix_colors):
                    pos = i / (len(parent.mix_colors) - 1) if len(parent.mix_colors) > 1 else 0
                    local_gradient.setColorAt(pos, col)
                p_painter.setBrush(QBrush(local_gradient))
                p_painter.setPen(Qt.NoPen)
                path_translated = QPainterPath()
                path_translated.moveTo(points_to_draw[0] - QPoint(min_x, min_y))
                for p in points_to_draw[1:]:
                    path_translated.lineTo(p - QPoint(min_x, min_y))
                path_translated.closeSubpath()
                p_painter.drawPath(path_translated)
                p_painter.end()
                if is_mirrored_shape:
                    pattern_img = pattern_img.mirrored(True, False)
                buffer = QByteArray()
                buffer_io = QBuffer(buffer)
                buffer_io.open(QIODevice.WriteOnly)
                pattern_img.save(buffer_io, "PNG")
                texture_b64 = base64.b64encode(buffer.data()).decode('utf-8')
            else:
                pattern_img = QImage(w, h, QImage.Format_ARGB32)
                pattern_img.fill(final_fill_color)
                p_painter = QPainter(pattern_img)
                p_painter.setRenderHint(QPainter.Antialiasing)
                num_blobs = int(w * h / 50)
                mix_idx = 0
                angle_rad = math.radians(parent.mix_angle)
                for i in range(max(10, num_blobs)):
                    bx = random.randint(0, w)
                    by = random.randint(0, h)
                    global_x = min_x + bx
                    global_y = min_y + by
                    if is_mirrored_shape:
                        global_x = self.mirror_line_x - (global_x - self.mirror_line_x)
                    
                    color = self.calculateMixColor(global_x, global_y, 0.0, parent.mix_colors, parent.mix_mode, parent.mix_angle, mix_idx)
                    if parent.mix_mode == 'sequential':
                        mix_idx += 1
                    
                    p_painter.setBrush(QBrush(color))
                    p_painter.setPen(Qt.NoPen)
                    r = random.randint(5, 25)
                    p_painter.drawEllipse(bx, by, r, r)
                p_painter.end()
                if is_mirrored_shape:
                    pattern_img = pattern_img.mirrored(True, False)
                buffer = QByteArray()
                buffer_io = QBuffer(buffer)
                buffer_io.open(QIODevice.WriteOnly)
                pattern_img.save(buffer_io, "PNG")
                texture_b64 = base64.b64encode(buffer.data()).decode('utf-8')
                brush = QBrush(pattern_img)
                painter.translate(min_x, min_y)
                path_translated = QPainterPath()
                path_translated.moveTo(points_to_draw[0] - QPoint(min_x, min_y))
                for p in points_to_draw[1:]:
                    path_translated.lineTo(p - QPoint(min_x, min_y))
                path_translated.closeSubpath()
                painter.setBrush(brush)
                painter.drawPath(path_translated)
                painter.translate(-min_x, -min_y)
        else:
            painter.setBrush(QBrush(final_fill_color))
            painter.drawPath(path)

        painter.end()
        element_data = {
            "type": "stroke", "points": [[p.x(), p.y()] for p in points_to_draw],
            "color": [final_fill_color.red(), final_fill_color.green(), final_fill_color.blue(), final_fill_color.alpha()],
            "width": 1, "pressure_enabled": False, "is_solid_fill": True, "layer": self.current_layer_name
        }
        if parent.eraser_mode:
            element_data["is_eraser"] = True

        if texture_b64:
            element_data["fill_texture"] = texture_b64
            element_data["bbox"] = [min_x, min_y, w, h]
        self._append_live(element_data)

    def _save_stroke(self, points, info, is_mirrored_call=False):
        parent = self.parent()
        if not parent:
            return
        if parent.pen_pressure_enabled or len(parent.mix_colors) > 1 or parent.current_tool_index >= 6:
            extended_points = []
            for i, point in enumerate(points):
                color_info = info[i][0]
                width_info = info[i][1]
                pt = self.getMirroredPoint(point) if is_mirrored_call else point
                extended_points.append([
                    pt.x(), pt.y(),
                    color_info.red(), color_info.green(), color_info.blue(), color_info.alpha(),
                    width_info
                ])
            data = {
                "type": "stroke_pressure", "points": extended_points, "pressure_enabled": True,
                "brush_type": parent.current_tool_index if parent.current_tool_index >= 6 else 0, "layer": self.current_layer_name
            }
            if parent.eraser_mode:
                data["is_eraser"] = True
            self._append_live(data)
        else:
            if parent.eraser_mode:
                color_to_save = QColor(0, 0, 0, 0)
                width_to_save = parent.eraser_radius
            else:
                color_to_save, width_to_save = parent.getCurrentPen()

            final_points = []
            for p in points:
                pt = self.getMirroredPoint(p) if is_mirrored_call else p
                final_points.append([pt.x(), pt.y()])
            data = {
                "type": "stroke", "points": final_points,
                "color": [color_to_save.red(), color_to_save.green(), color_to_save.blue(), color_to_save.alpha()],
                "width": width_to_save, "pressure_enabled": False, "layer": self.current_layer_name
            }
            if parent.eraser_mode:
                data["is_eraser"] = True
            self._append_live(data)

    def mouseReleaseEvent(self, event):
        parent = self.parent()
        if not parent:
            return
        if self.select_active and self.selectMouseRelease(event):
            return
        if self.point_active and self.ptMouseRelease(event):
            return

        if self.panning:
            self.panning = False
            if self.alt_permanent_pan_mode:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.CrossCursor)
            return

        if self.dragging_mirror_line:
            self.dragging_mirror_line = False
            self.setCursor(Qt.CrossCursor)
            return
        if self.dragging_whole_polyline:
            self.dragging_whole_polyline = False
            self.setCursor(Qt.CrossCursor)
            return
        if parent.polyline_mode or parent.curve_mode:
            self.dragging_poly_point_index = -1
            self.setCursor(Qt.CrossCursor)
            return

        if (event.button() == Qt.MiddleButton or event.button() == Qt.RightButton) and self.dragging_image:
            self.dragging_image = False
            self.setCursor(Qt.CrossCursor)
            event.accept()
            return

        if event.button() == Qt.LeftButton and self.drawing:
            
            if parent.current_tool_index in [37, 38]:
                if len(self.current_stroke_points) >= 2:
                    p1 = self.current_stroke_points[0]
                    p2 = self.current_stroke_points[1]
                    pts = []

                    if parent.current_tool_index == 37: 
                        pts = [p1, QPoint(p2.x(), p1.y()), p2, QPoint(p1.x(), p2.y()), p1]
                    elif parent.current_tool_index == 38: 
                        r = math.hypot(p2.x() - p1.x(), p2.y() - p1.y())
                        steps = max(30, min(100, int(r))) 
                        if steps > 0:
                            for i in range(steps + 1):
                                angle = 2 * math.pi * i / steps
                                pts.append(QPoint(int(p1.x() + r * math.cos(angle)), int(p1.y() + r * math.sin(angle))))
                        else:
                            pts = [p1, p1]

                    if parent.solid_fill_mode:
                        self.createSolidFill(pts, is_mirrored_shape=False)
                        if parent.mirror_mode:
                            mirrored_pts = [self.getMirroredPoint(p) for p in pts]
                            mirrored_pts.reverse()
                            self.createSolidFill(mirrored_pts, is_mirrored_shape=True)
                    else:
                        pen_color, pen_width = parent.getCurrentPen()
                        data = {
                            "type": "stroke", "points": [[p.x(), p.y()] for p in pts],
                            "color": [pen_color.red(), pen_color.green(), pen_color.blue(), pen_color.alpha()],
                            "width": pen_width, "pressure_enabled": False, "layer": self.current_layer_name
                        }
                        if parent.eraser_mode:
                            data["is_eraser"] = True
                        self.drawing_elements.append(data)

                        if parent.mirror_mode:
                            m_pts = [self.getMirroredPoint(p) for p in pts]
                            m_data = {
                                "type": "stroke", "points": [[p.x(), p.y()] for p in m_pts],
                                "color": [pen_color.red(), pen_color.green(), pen_color.blue(), pen_color.alpha()],
                                "width": pen_width, "pressure_enabled": False, "layer": self.current_layer_name
                            }
                            if parent.eraser_mode:
                                m_data["is_eraser"] = True
                            self.drawing_elements.append(m_data)

                self.current_stroke_points = []
                self.drawing = False
                self._actively_modifying = False
                self.updateImageFromElements()
                return

            if parent.solid_fill_mode:
                if len(self.current_stroke_points) > 2:
                    self.createSolidFill(self.current_stroke_points, is_mirrored_shape=False)
                    if parent.mirror_mode:
                        mirrored_points = [self.getMirroredPoint(p) for p in self.current_stroke_points]
                        mirrored_points.reverse()
                        self.createSolidFill(mirrored_points, is_mirrored_shape=True)
                    self.update()
            else:
                is_mixed = len(parent.mix_colors) > 1 and not parent.eraser_mode
                is_special_brush = parent.current_tool_index >= 6

                if parent.current_tool_index == 36:
                     pass

                else:
                    self._save_stroke(self.current_stroke_points, self.current_stroke_pen_info, is_mirrored_call=False)
                    if parent.mirror_mode:
                        self._save_stroke(self.current_stroke_points, self.current_stroke_pen_info, is_mirrored_call=True)

            self.current_stroke_points = []
            self.current_stroke_pen_info = []
            self.drawing = False
            self._actively_modifying = False
            
            self.lazy_mouse_pos = None
            self.lazy_target_pos = None
            self.lazy_velocity = QPointF(0, 0)

            # Eski sistem silgide/"üstte tut" modunda TÜM kayıtları yeniden oynatıyordu (kasma nedeni).
            # Artık çizim zaten aktif katmanın raster'ında; yalnızca pixmap tazelenir.
            self.commitImageToPixmap()
            self.update()
            self.contentChanged.emit()

    def finalizePolyline(self):
        if not self.parent():
            return
        parent = self.parent()
        active_points = self.polyline_points if parent.polyline_mode else self.curve_points
        if not active_points:
            return
        self.saveStateForUndo(deep_copy=False)

        if parent.eraser_mode:
            c = QColor(0, 0, 0, 0)
            w = parent.eraser_radius
        elif len(parent.mix_colors) > 1:
            c = random.choice(parent.mix_colors)
            w = parent.pen_radius
        else:
            c = parent.pen_color
            w = parent.pen_radius

        def save_path_as_stroke(pts, add_arrow=False):
            data = None
            if parent.curve_mode:
                path = self.generateSmoothCurvePath(pts)
                rasterized_points = []
                for i in range(101):
                    pt = path.pointAtPercent(i / 100.0)
                    rasterized_points.append([pt.x(), pt.y()])
                data = {
                    "type": "stroke", "points": rasterized_points,
                    "color": [c.red(), c.green(), c.blue(), c.alpha()],
                    "width": w, "pressure_enabled": False, "layer": self.current_layer_name
                }
            else:
                final_pts = [[p.x(), p.y()] for p in pts]
                if add_arrow and len(pts) >= 2:
                    p_end = pts[-1]
                    p_prev = pts[-2]
                    angle = math.atan2(p_prev.y() - p_end.y(), p_prev.x() - p_end.x())
                    arrow_len = w * 3
                    p3 = QPoint(int(p_end.x() + arrow_len * math.cos(angle + math.pi / 6)), int(p_end.y() + arrow_len * math.sin(angle + math.pi / 6)))
                    p4 = QPoint(int(p_end.x() + arrow_len * math.cos(angle - math.pi / 6)), int(p_end.y() + arrow_len * math.sin(angle - math.pi / 6)))
                    final_pts.append([p3.x(), p3.y()])
                    final_pts.append([p_end.x(), p_end.y()])
                    final_pts.append([p4.x(), p4.y()])

                data = {
                    "type": "stroke", "points": final_pts,
                    "color": [c.red(), c.green(), c.blue(), c.alpha()],
                    "width": w, "pressure_enabled": False, "layer": self.current_layer_name
                }

            if data:
                if parent.eraser_mode:
                    data["is_eraser"] = True
                self.drawing_elements.append(data)

        is_arrow = (parent.current_tool_index == 36)
        save_path_as_stroke(active_points, add_arrow=is_arrow)
        if parent.mirror_mode:
            mirrored_pts = [self.getMirroredPoint(p) for p in active_points]
            save_path_as_stroke(mirrored_pts, add_arrow=is_arrow)

        if parent.polyline_mode:
            self.polyline_points = []
        else:
            self.curve_points = []
        self.updateImageFromElements()

    def drawBrushStroke(self, painter, p1, p2, color, width, tool_index):
        dist = math.sqrt((p2.x()-p1.x())**2 + (p2.y()-p1.y())**2)
        i_width = int(width) if width > 0 else 1

        if tool_index == 6:
            pen = QPen(color, width)
            pen.setCapStyle(Qt.SquareCap)
            painter.setPen(pen)
            painter.save()
            painter.translate(p2)
            painter.rotate(45)
            painter.drawLine(0, -i_width//2, 0, i_width//2)
            painter.restore()
            painter.drawLine(p1, p2)
        elif tool_index == 7:
            marker_color = QColor(color)
            marker_color.setAlpha(40)
            painter.setPen(Qt.NoPen)
            painter.setBrush(marker_color)
            rect_size = width * 1.5
            painter.drawRect(int(p2.x() - rect_size/2), int(p2.y() - rect_size/2), int(rect_size), int(rect_size))
        elif tool_index == 8:
            density = int(width * 1.5)
            painter.setPen(QPen(color, 1))
            for _ in range(density):
                angle = random.random() * 2 * math.pi
                radius = random.random() * width
                dx = int(radius * math.cos(angle))
                dy = int(radius * math.sin(angle))
                painter.drawPoint(p2.x() + dx, p2.y() + dy)
        elif tool_index == 9:
            chalk_color = QColor(color)
            chalk_color.setAlpha(150)
            painter.setPen(QPen(chalk_color, 1))
            steps = max(1, int(dist))
            for i in range(steps):
                t = i / steps
                x = p1.x() + (p2.x() - p1.x()) * t
                y = p1.y() + (p2.y() - p1.y()) * t
                rx = random.randint(int(-i_width//2), int(i_width//2))
                ry = random.randint(int(-i_width//2), int(i_width//2))
                if random.random() > 0.3:
                    painter.drawPoint(int(x + rx), int(y + ry))
        elif tool_index == 10:
            hl_color = QColor(color)
            hl_color.setAlpha(60)
            painter.setPen(Qt.NoPen)
            painter.setBrush(hl_color)
            h = width * 2
            w = 5
            painter.drawRect(int(p2.x() - w/2), int(p2.y() - h/2), w, int(h))
        elif tool_index == 11:
            gradient = QRadialGradient(p2, width)
            c1 = QColor(color)
            c1.setAlpha(20)
            c2 = QColor(color)
            c2.setAlpha(0)
            gradient.setColorAt(0, c1)
            gradient.setColorAt(1, c2)
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(p2, width, width)
        elif tool_index == 12:
            painter.setPen(QPen(color, max(1, i_width//2), Qt.SolidLine))
            painter.drawLine(p1, p2)
        elif tool_index == 13:
            painter.setPen(QPen(color, 1))
            painter.drawPoint(p2)
        elif tool_index == 14:
            char_color = QColor(40, 40, 40, 100)
            painter.setPen(QPen(char_color, 1))
            for _ in range(i_width):
                rx = random.randint(int(-i_width//2), int(i_width//2))
                ry = random.randint(int(-i_width//2), int(i_width//2))
                painter.drawPoint(p2.x() + rx, p2.y() + ry)
        elif tool_index == 15:
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(p2, int(width/2), int(width/2))
        elif tool_index == 16:
            painter.setPen(QPen(color, 1))
            painter.drawPoint(p2)
            if random.random() > 0.8:
                offset_x = random.randint(-50, 50)
                offset_y = random.randint(-50, 50)
                painter.setPen(QPen(color, 0.5))
                painter.drawLine(p2, QPoint(p2.x()+offset_x, p2.y()+offset_y))
        elif tool_index == 17:
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap))
            painter.setOpacity(0.3)
            painter.drawLine(p1, p2)
            painter.setOpacity(1.0)
            painter.setPen(QPen(QColor(255, 255, 255), max(1, i_width//3), Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1, p2)
        elif tool_index == 18:
            if dist > 5:
                painter.setPen(Qt.NoPen)
                for _ in range(3):
                    conf_color = QColor(random.randint(0,255), random.randint(0,255), random.randint(0,255))
                    painter.setBrush(conf_color)
                    cx = p2.x() + random.randint(int(-i_width), int(i_width))
                    cy = p2.y() + random.randint(int(-i_width), int(i_width))
                    cs = random.randint(2, 6)
                    if random.random() > 0.5:
                        painter.drawEllipse(cx, cy, cs, cs)
                    else:
                        painter.drawRect(cx, cy, cs, cs)

        elif tool_index == 19:
             painter.setPen(Qt.NoPen)
             painter.setBrush(color)
             painter.save()
             painter.translate(p2)
             painter.rotate(random.randint(0, 360))
             path = QPainterPath()
             path.moveTo(0, -width)
             path.quadTo(width/2, -width/2, 0, width)
             path.quadTo(-width/2, -width/2, 0, -width)
             painter.drawPath(path)
             painter.restore()

        elif tool_index == 20:
             painter.setPen(QPen(color, 1))
             painter.setBrush(Qt.NoBrush)
             size = i_width
             painter.save()
             painter.translate(p2)
             painter.rotate(random.randint(0, 360))
             points = [QPoint(0, -size), QPoint(size//4, -size//4), QPoint(size, 0), QPoint(size//4, size//4), QPoint(0, size), QPoint(-size//4, size//4), QPoint(-size, 0), QPoint(-size//4, -size//4)]
             painter.drawPolygon(QPolygon(points))
             painter.restore()

        elif tool_index == 21:
            painter.setPen(QPen(color, 1))
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 50))
            painter.drawEllipse(p2, width, width)
            painter.setBrush(QColor(255, 255, 200))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(p2.x() - i_width//3, p2.y() - i_width//3, i_width//3, i_width//3)

        elif tool_index == 22:
            if dist > 3:
                painter.setPen(QPen(color, 1))
                for _ in range(3):
                    gx = p2.x() + random.randint(-5, 5)
                    gy = p2.y() + random.randint(-2, 2)
                    gh = random.randint(int(width), int(width * 3)) if width > 1 else random.randint(5, 15)
                    painter.drawLine(gx, gy, gx, gy - gh)

        elif tool_index == 23:
            hue = (p2.x() + p2.y()) % 360
            rb_color = QColor.fromHsv(hue, 200, 250)
            painter.setPen(QPen(rb_color, width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1, p2)
        elif tool_index == 24:
            painter.setPen(QPen(color, 1))
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            normal_x = -dy
            normal_y = dx
            length = math.sqrt(normal_x**2 + normal_y**2)
            if length > 0:
                normal_x /= length
                normal_y /= length
                fur_len = width * 1.5
                painter.drawLine(p2.x(), p2.y(), int(p2.x() + normal_x * fur_len), int(p2.y() + normal_y * fur_len))

        elif tool_index == 25:
            painter.setPen(QPen(color, 1))
            painter.drawLine(p1, p2)
            if random.random() > 0.5:
                w_offset = max(1, int(width // 2))
                offsets = [random.randint(-w_offset, w_offset) for _ in range(4)]
                painter.drawLine(p1.x()+offsets[0], p1.y()+offsets[1], p2.x()+offsets[2], p2.y()+offsets[3])

        elif tool_index == 26:
            pen = QPen(color, width)
            pen.setStyle(Qt.DotLine)
            painter.setPen(pen)
            painter.drawLine(p1, p2)
        elif tool_index == 27:
            pen = QPen(color, width)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(p1, p2)
        elif tool_index == 28:
            pen = QPen(color, max(1, i_width//3))
            offset = i_width // 2 + 2
            painter.setPen(pen)
            painter.drawLine(p1.x()-offset, p1.y()-offset, p2.x()-offset, p2.y()-offset)
            painter.drawLine(p1.x()+offset, p1.y()+offset, p2.x()+offset, p2.y()+offset)
        elif tool_index == 29:
            shadow_color = QColor(0, 0, 0, 50)
            painter.setPen(QPen(shadow_color, width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1.x()+5, p1.y()+5, p2.x()+5, p2.y()+5)
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1, p2)
        elif tool_index == 30:
            darker = color.darker(150)
            painter.setPen(QPen(darker, width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1.x()+2, p1.y()+2, p2.x()+2, p2.y()+2)
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1, p2)

        elif tool_index == 31:
            if dist > 0:
                painter.setPen(QPen(color, 2))
                amplitude = max(5, width)
                angle = math.atan2(p2.y()-p1.y(), p2.x()-p1.x())
                perp_angle = angle + math.pi/2
                offset = (p2.x() + p2.y()) / 10.0
                off1 = math.sin(offset) * amplitude
                off2 = math.sin(offset + math.pi) * amplitude
                pt1_x = p2.x() + math.cos(perp_angle) * off1
                pt1_y = p2.y() + math.sin(perp_angle) * off1
                pt2_x = p2.x() + math.cos(perp_angle) * off2
                pt2_y = p2.y() + math.sin(perp_angle) * off2
                painter.drawPoint(int(pt1_x), int(pt1_y))
                painter.drawPoint(int(pt2_x), int(pt2_y))
                if random.random() > 0.8:
                    painter.setPen(QPen(color, 1))
                    painter.drawLine(int(pt1_x), int(pt1_y), int(pt2_x), int(pt2_y))

        elif tool_index == 32:
            painter.setPen(QPen(color, 2))
            offset = 5 if int(p2.x() / 10) % 2 == 0 else -5
            painter.drawPoint(p2.x() + offset, p2.y() + offset)

        elif tool_index == 33:
            painter.setPen(QPen(color, 1))
            grid_size = max(5, int(width * 2))
            snap_x = (p2.x() // grid_size) * grid_size
            snap_y = (p2.y() // grid_size) * grid_size
            painter.drawLine(snap_x, snap_y, snap_x+grid_size, snap_y)
            painter.drawLine(snap_x, snap_y, snap_x, snap_y+grid_size)

        elif tool_index == 34:
             painter.setPen(QPen(color, 1))
             if dist > 5:
                 rand_range = max(2, int(width))
                 mx = (p1.x() + p2.x()) / 2 + random.randint(-rand_range, rand_range)
                 my = (p1.y() + p2.y()) / 2 + random.randint(-rand_range, rand_range)
                 painter.drawLine(p1, QPoint(int(mx), int(my)))
                 painter.drawLine(QPoint(int(mx), int(my)), p2)
             else:
                 painter.drawLine(p1, p2)

        else:
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(p1, p2)

    def wheelEvent(self, event):
        parent = self.parent()
        if not parent:
            super().wheelEvent(event)
            return
        is_o_mode = parent.nav_button.isChecked()

        if self.placing_reference and self.reference_image is not None and not is_o_mode:
            ref = self.reference_image
            num_degrees = event.angleDelta().y() / 8
            num_steps = num_degrees / 15
            scale_factor = 1.0 + num_steps * 0.1
            current_size = ref['display_size']
            new_width = int(current_size.width() * scale_factor)
            new_height = int(current_size.height() * scale_factor)
            
            min_size = 20
            max_size_width = self.image.width()
            max_size_height = self.image.height()
            new_width = max(min_size, min(new_width, max_size_width))
            new_height = max(min_size, min(new_height, max_size_height))
            
            if new_width != current_size.width() or new_height != current_size.height():
                current_center = ref['offset'] + QPoint(current_size.width() // 2, current_size.height() // 2)
                ref['display_size'] = QSize(new_width, new_height)
                ref['offset'] = current_center - QPoint(ref['display_size'].width() // 2, ref['display_size'].height() // 2)
                self._reference_scaled_cache.clear()
                self.update()
                event.accept()
                return

        if parent.placing_image and self.original_image_for_placement:
            num_degrees = event.angleDelta().y() / 8
            num_steps = num_degrees / 15
            scale_factor = 1.0 + num_steps * 0.1
            current_image_size = self.current_image_display_size
            new_width = int(current_image_size.width() * scale_factor)
            new_height = int(current_image_size.height() * scale_factor)
            min_size = 20
            max_size_width = self.width() - 10
            max_size_height = self.height() - 10
            new_width = max(min_size, min(new_width, max_size_width))
            new_height = max(min_size, min(new_height, max_size_height))
            if new_width == current_image_size.width() and new_height == current_image_size.height():
                event.ignore()
                return
            current_center = self.image_placement_offset + QPoint(current_image_size.width() // 2, current_image_size.height() // 2)
            self.current_image_display_size = QSize(new_width, new_height)
            self.image_placement_offset = current_center - QPoint(self.current_image_display_size.width() // 2, self.current_image_display_size.height() // 2)
            self.applyImagePlacementBounds()
            self.update()
            event.accept()
        elif parent.polyline_mode or parent.curve_mode:
            active_points = self.polyline_points if parent.polyline_mode else self.curve_points
            if len(active_points) == 0:
                return
            center_x = sum(p.x() for p in active_points) / len(active_points)
            center_y = sum(p.y() for p in active_points) / len(active_points)
            center = QPoint(int(center_x), int(center_y))
            num_degrees = event.angleDelta().y() / 8
            scale_factor = 1.05 if num_degrees > 0 else 0.95
            new_points = []
            for p in active_points:
                vec = p - center
                new_vec_x = vec.x() * scale_factor
                new_vec_y = vec.y() * scale_factor
                new_points.append(QPoint(int(center.x() + new_vec_x), int(center.y() + new_vec_y)))
            if parent.polyline_mode:
                self.polyline_points = new_points
            else:
                self.curve_points = new_points
            self.update()
            event.accept()
        else:
            if is_o_mode:
                old_zoom = self.zoom_factor
                delta = event.angleDelta().y()
                factor = 1.1 if delta > 0 else 0.9
                new_zoom = old_zoom * factor
                new_zoom = max(0.1, min(30.0, new_zoom))

                if new_zoom != old_zoom:
                    mouse_pos = event.pos()
                    p_img = self.toCanvas(mouse_pos)
                    self.zoom_factor = new_zoom
                    center_offset_x = 0
                    center_offset_y = 0
                    scaled_w = self.image.width() * self.zoom_factor
                    scaled_h = self.image.height() * self.zoom_factor

                    if self.width() > scaled_w:
                         center_offset_x = (self.width() - scaled_w) / 2
                    if self.height() > scaled_h:
                         center_offset_y = (self.height() - scaled_h) / 2

                    new_vx = mouse_pos.x() - (p_img.x() * new_zoom) - center_offset_x
                    new_vy = mouse_pos.y() - (p_img.y() * new_zoom) - center_offset_y

                    self.view_offset = QPoint(int(new_vx), int(new_vy))
                    self.update()

                event.accept()
            else:
                super().wheelEvent(event)

    def drawTabletLineTo(self, endPoint, pressure):
        pass

    def addTextToDrawing(self):
        parent = self.parent()
        if not parent:
            return
        text_content = self.text_input_widget.toPlainText()
        if text_content:
            self.saveStateForUndo(deep_copy=False)

            cursor = self.text_input_widget.textCursor()
            cursor.setPosition(0)
            rect = self.text_input_widget.cursorRect(cursor)

            text_start_in_widget = self.text_input_widget.viewport().mapToParent(rect.topLeft())
            absolute_text_pos = self.text_input_widget.pos() + text_start_in_widget
            canvas_pos_f = self.toCanvas(absolute_text_pos)

            screen_font_size = self.text_input_widget.font().pointSize()
            canvas_font_size = int(screen_font_size / self.zoom_factor)
            if canvas_font_size < 1:
                canvas_font_size = 1

            final_x = canvas_pos_f.x()
            final_y = canvas_pos_f.y()

            color = parent.pen_color

            self.drawing_elements.append({
                "type": "text", "content": text_content,
                "position": [final_x, final_y],
                "color": [color.red(), color.green(), color.blue(), color.alpha()],
                "font_size": canvas_font_size, "layer": self.current_layer_name
            })
            if parent.mirror_mode:
                 p_canvas = QPoint(int(final_x), int(final_y))
                 mirrored_pos = self.getMirroredPoint(p_canvas)
                 self.drawing_elements.append({
                    "type": "text", "content": text_content,
                    "position": [mirrored_pos.x(), mirrored_pos.y()],
                    "color": [color.red(), color.green(), color.blue(), color.alpha()],
                    "font_size": canvas_font_size, "is_mirrored": True, "layer": self.current_layer_name
                })
            self.updateImageFromElements()

        self.text_input_widget.hide()
        self.text_input_widget.clear()

    def startImagePlacement(self, original_image_qimage):
        if self.parent():
            self.parent().is_project_modified = True
            
        self.original_image_for_placement = original_image_qimage
        drawing_area_size = self.size()
        max_width = drawing_area_size.width() - 10
        max_height = drawing_area_size.height() - 10
        initial_scaled_size = self.original_image_for_placement.size().scaled(max_width, max_height, Qt.KeepAspectRatio)
        self.current_image_display_size = initial_scaled_size
        self.image_placement_offset = QPoint((self.width() - initial_scaled_size.width()) // 2, (self.height() - initial_scaled_size.height()) // 2)
        self.applyImagePlacementBounds()
        self.dragging_image = False
        self.setCursor(Qt.CrossCursor)
        self.drawing = False
        self.current_stroke_points = []
        self.current_stroke_pen_info = []

        parent = self.parent()
        if parent:
            parent.nav_button.setChecked(False)
            parent.nav_button.updateStyle()

        self.update()

    def cancelImagePlacement(self):
        self.original_image_for_placement = None
        self.current_image_display_size = QSize(0, 0)
        self.image_placement_offset = QPoint(0, 0)
        self.dragging_image = False
        self.setCursor(Qt.ArrowCursor)
        self.drawing = False
        self.current_stroke_points = []
        self.current_stroke_pen_info = []
        self.update()
        parent = self.parent()
        if parent:
            parent.placing_image = False
            parent.updateButtonStyles()

    def applyImagePlacementBounds(self):
        if not self.original_image_for_placement or not self.current_image_display_size.isValid():
            return
        pass

    def _render_elements(self, elements, target_image=None):
        """Kayıtları rasterlaştırır. target_image verilirse hepsi oraya çizilir; yoksa her kayıt kendi katmanına."""
        if target_image is not None:
            self._render_group(target_image, elements)
            return
        st = self.layer_stack
        groups = {}
        order = []
        for element in elements:
            layer = st.by_name(element.get("layer", "")) or st.active
            if layer.id not in groups:
                groups[layer.id] = (layer, [])
                order.append(layer.id)
            groups[layer.id][1].append(element)

        for lid in order:
            layer, layer_elements = groups[lid]
            self._render_group(layer.image, layer_elements)
            layer.invalidate()
            layer.touch()

    def _render_group(self, image, layer_elements):
        """Kayıtları verilen görüntüye çizer (katmana bağlı değildir; A modu ve ara kareler de kullanır)."""
        layer_painter = QPainter(image)
        layer_painter.setRenderHint(QPainter.Antialiasing)
        try:
            for element in layer_elements:
                is_eraser = element.get("is_eraser", False)
                if is_eraser:
                    layer_painter.setCompositionMode(QPainter.CompositionMode_Clear)
                else:
                    layer_painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

                if element.get("is_solid_fill", False):
                    c = QColor(*element["color"])
                    pts = [QPoint(int(p[0]), int(p[1])) for p in element["points"]]
                    if len(pts) > 2:
                        path = QPainterPath()
                        path.moveTo(pts[0])
                        for p in pts[1:]:
                            path.lineTo(p)
                        path.closeSubpath()
                        layer_painter.setPen(QPen(c, 1, Qt.SolidLine))
                        if is_eraser:
                            layer_painter.setBrush(QBrush(Qt.black))
                            layer_painter.drawPath(path)
                        elif "fill_texture" in element and element["fill_texture"]:
                            pattern_img = self._cached_b64_image(element["fill_texture"])
                            bbox = element.get("bbox", [0, 0, 1, 1])
                            min_x, min_y = bbox[0], bbox[1]
                            layer_painter.save()
                            layer_painter.translate(min_x, min_y)
                            path_translated = QPainterPath()
                            path_translated.moveTo(pts[0] - QPoint(int(min_x), int(min_y)))
                            for p in pts[1:]:
                                path_translated.lineTo(p - QPoint(int(min_x), int(min_y)))
                            path_translated.closeSubpath()
                            layer_painter.setBrush(QBrush(pattern_img))
                            layer_painter.drawPath(path_translated)
                            layer_painter.restore()
                        else:
                            layer_painter.setBrush(QBrush(c))
                            layer_painter.drawPath(path)
                    continue

                if element["type"] == "stroke":
                    color = QColor(*element["color"])
                    width = element["width"]
                    pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    layer_painter.setPen(pen)
                    points = [QPoint(int(p[0]), int(p[1])) for p in element["points"]]
                    if len(points) > 1:
                        layer_painter.drawPolyline(QPolygon(points))
                    elif len(points) == 1:
                        layer_painter.drawPoint(points[0])

                elif element["type"] == "stroke_pressure":
                    points_data = element["points"]
                    brush_type = element.get("brush_type", 0)
                    if brush_type == 0:
                        reuse_pen = QPen(Qt.black, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                        last_pen_key = None
                        for i in range(len(points_data) - 1):
                            p1_data = points_data[i]
                            p2_data = points_data[i+1]
                            p1 = QPoint(int(p1_data[0]), int(p1_data[1]))
                            p2 = QPoint(int(p2_data[0]), int(p2_data[1]))
                            pen_key = (p1_data[2], p1_data[3], p1_data[4], p1_data[5], p1_data[6])
                            if pen_key != last_pen_key:
                                reuse_pen.setColor(QColor(p1_data[2], p1_data[3], p1_data[4], p1_data[5]))
                                reuse_pen.setWidthF(float(p1_data[6]))
                                layer_painter.setPen(reuse_pen)
                                last_pen_key = pen_key
                            layer_painter.drawLine(p1, p2)
                    else:
                        for i in range(len(points_data) - 1):
                            p1_data = points_data[i]
                            p2_data = points_data[i+1]
                            p1 = QPoint(int(p1_data[0]), int(p1_data[1]))
                            p2 = QPoint(int(p2_data[0]), int(p2_data[1]))
                            color = QColor(p1_data[2], p1_data[3], p1_data[4], p1_data[5])
                            width = p1_data[6]
                            self.drawBrushStroke(layer_painter, p1, p2, color, width, brush_type)

                elif element["type"] == "text":
                    color = QColor(*element["color"])
                    font = QFont("Arial", element["font_size"])
                    layer_painter.setPen(color)
                    layer_painter.setFont(font)
                    text_pos = QPoint(int(element["position"][0]), int(element["position"][1]))
                    font_metrics = QFontMetrics(font)
                    lines = element["content"].split('\n')
                    current_y = text_pos.y()
                    if element.get("is_mirrored", False):
                        layer_painter.save()
                        layer_painter.translate(text_pos.x(), text_pos.y())
                        layer_painter.scale(-1, 1)
                        for line in lines:
                            current_y += font_metrics.ascent()
                            layer_painter.drawText(0, current_y - text_pos.y(), line)
                            current_y += 5
                        layer_painter.restore()
                    else:
                        for line in lines:
                            current_y += font_metrics.ascent()
                            layer_painter.drawText(text_pos.x(), current_y, line)
                            current_y += 5

                elif element["type"] == "image":
                    base64_data = element["base64_data"]
                    cache_key = str(len(base64_data)) + base64_data[:30]
                    if cache_key in self.image_cache:
                        temp_image = self.image_cache[cache_key]
                    else:
                        image_data = base64.b64decode(base64_data)
                        temp_image = QImage()
                        temp_image.loadFromData(image_data, "PNG")
                        self.image_cache[cache_key] = temp_image
                    scaled_image = temp_image.scaled(
                        element["current_width"], element["current_height"],
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    image_pos = QPoint(int(element["position"][0]), int(element["position"][1]))
                    if is_eraser:
                        layer_painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
                        layer_painter.drawImage(image_pos, scaled_image)
                    else:
                        layer_painter.drawImage(image_pos, scaled_image)
        finally:
            layer_painter.end()

    def replaceColor(self, target_color, new_color, is_delete=False, mode='global', pos=None):
        self.saveStateForUndo(deep_copy=True)
        if mode == 'global':
            self.replaceColorGlobally(target_color, new_color, is_delete)
        elif mode == 'connected' and pos is not None:
            self.floodFill(pos, target_color, new_color if not is_delete else QColor(0,0,0,0))

    def replaceColorGlobally(self, target_color, new_color, is_delete=False):
        target_rgba = (target_color.red(), target_color.green(), target_color.blue())
        tolerance = 20
        for element in self.drawing_elements:
            if element["type"] == "stroke":
                ec = element["color"]
                if abs(ec[0]-target_rgba[0]) < tolerance and abs(ec[1]-target_rgba[1]) < tolerance and abs(ec[2]-target_rgba[2]) < tolerance:
                    if is_delete:
                        element["color"][3] = 0
                    else:
                        element["color"] = [new_color.red(), new_color.green(), new_color.blue(), new_color.alpha()]
            elif element["type"] == "stroke_pressure":
                points = element["points"]
                for p in points:
                    if abs(p[2]-target_rgba[0]) < tolerance and abs(p[3]-target_rgba[1]) < tolerance and abs(p[4]-target_rgba[2]) < tolerance:
                         if is_delete:
                             p[5] = 0
                         else:
                             p[2], p[3], p[4], p[5] = new_color.red(), new_color.green(), new_color.blue(), new_color.alpha()
            elif element["type"] == "text":
                if (abs(element["color"][0]-target_rgba[0]) < tolerance and
                    abs(element["color"][1]-target_rgba[1]) < tolerance and
                    abs(element["color"][2]-target_rgba[2]) < tolerance):
                    if is_delete:
                        element["color"] = [0, 0, 0, 0]
                    else:
                        element["color"] = [new_color.red(), new_color.green(), new_color.blue(), new_color.alpha()]
            elif element["type"] == "image":
                base64_data = element["base64_data"]
                image_data = base64.b64decode(base64_data)
                temp_image = QImage()
                temp_image.loadFromData(image_data, "PNG")
                temp_image = temp_image.convertToFormat(QImage.Format_ARGB32)
                width = temp_image.width()
                height = temp_image.height()
                modified = False
                for y in range(height):
                    for x in range(width):
                        pixel_color = temp_image.pixelColor(x, y)
                        if abs(pixel_color.red()-target_rgba[0]) < tolerance and abs(pixel_color.green()-target_rgba[1]) < tolerance and abs(pixel_color.blue()-target_rgba[2]) < tolerance:
                             if is_delete:
                                 temp_image.setPixelColor(x, y, QColor(0,0,0,0))
                             else:
                                 temp_image.setPixelColor(x, y, new_color)
                             modified = True
                if modified:
                    buffer = QByteArray()
                    buffer_io = QBuffer(buffer)
                    buffer_io.open(QIODevice.WriteOnly)
                    temp_image.save(buffer_io, "PNG")
                    element["base64_data"] = base64.b64encode(buffer.data()).decode('utf-8')
        self.updateImageFromElements(full=True)

    def floodFill(self, pos, target_color, replacement_color, tolerance=20):
        if not (0 <= pos.x() < self.image.width() and 0 <= pos.y() < self.image.height()):
            return
        image = self.image
        w, h = image.width(), image.height()
        queue = deque([pos])
        visited = set()
        if target_color == replacement_color:
            return
        while queue:
            p = queue.popleft()
            px, py = p.x(), p.y()
            if not (0 <= px < w and 0 <= py < h):
                continue
            key = (px, py)
            if key in visited:
                continue
            visited.add(key)
            current_color = image.pixelColor(px, py)
            if not (abs(current_color.red() - target_color.red()) < tolerance and abs(current_color.green() - target_color.green()) < tolerance and abs(current_color.blue() - target_color.blue()) < tolerance):
                continue
            image.setPixelColor(px, py, replacement_color)
            queue.append(QPoint(px + 1, py))
            queue.append(QPoint(px - 1, py))
            queue.append(QPoint(px, py + 1))
            queue.append(QPoint(px, py - 1))
        self.commitImageToPixmap()
        self.update()


# ===========================================================================
# BÖLÜM: ANİMASYON: SOĞAN ZARI, OYNATMA, ZAMAN ÇİZELGESİ
# ===========================================================================
# Kavram - Animasyon: soğan zarı (onion skin), oynatma, kare süresi (hold), zaman çizelgesi
from collections import OrderedDict



def expand_sequence(pages_data):
    """Kare sürelerini (hold) açar: [0, 0, 1, 2, 2, 2] gibi sayfa indeks dizisi döner."""
    seq = []
    for i, page in enumerate(pages_data):
        seq.extend([i] * max(1, int(page.get("hold", 1))))
    return seq


# ---------------------------------------------------------------------------
# Denetleyici: soğan zarı + oynatma
# ---------------------------------------------------------------------------
class AnimationController(QObject):
    onionChanged = pyqtSignal()
    playStateChanged = pyqtSignal(bool)
    playheadMoved = pyqtSignal(int)       # oynatma sırasında gösterilen sayfa indeksi

    ONION_OPACITY = [0.38, 0.22, 0.12]
    PREV_TINT = QColor(255, 80, 80)
    NEXT_TINT = QColor(70, 170, 255)
    PREFETCH = 10
    CACHE_MAX = 48

    def __init__(self, window):
        super().__init__(window)
        self.win = window
        s = QSettings("kavram", "DrawingEditor")
        self.onion_enabled = s.value("onionEnabled", True, type=bool)
        self.onion_before = s.value("onionBefore", 1, type=int)
        self.onion_after = s.value("onionAfter", 0, type=int)
        self.loop = s.value("loopPlayback", True, type=bool)

        self.is_playing = False
        self._onion_dirty = True
        self._onion_list = []
        self._tint_cache = {}

        # oynatma
        self._seq = []
        self._shown_page = -1
        self._start_page = 0
        self._frames = OrderedDict()
        self._lock = threading.Lock()
        self._prefetch_thread = None
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._tick)

        area = window.drawing_area
        area.onion_provider = self.onion_frames
        area.layersChanged.connect(self.invalidate_onion)

    # -------------------------------------------------- ayarlar
    def _save(self):
        s = QSettings("kavram", "DrawingEditor")
        s.setValue("onionEnabled", self.onion_enabled)
        s.setValue("onionBefore", self.onion_before)
        s.setValue("onionAfter", self.onion_after)
        s.setValue("loopPlayback", self.loop)

    def set_onion_enabled(self, v):
        self.onion_enabled = bool(v)
        self._save()
        self._refresh_onion()

    def set_onion_range(self, before=None, after=None):
        if before is not None:
            self.onion_before = max(0, min(3, int(before)))
        if after is not None:
            self.onion_after = max(0, min(3, int(after)))
        self._save()
        self._refresh_onion()

    def set_loop(self, v):
        self.loop = bool(v)
        self._save()

    def toggle_onion(self):
        self.set_onion_enabled(not self.onion_enabled)

    # -------------------------------------------------- soğan zarı
    def invalidate_onion(self):
        self._onion_dirty = True
        self._tint_cache.clear()

    def _refresh_onion(self):
        self.invalidate_onion()
        self.win.drawing_area.update()
        self.onionChanged.emit()

    def on_page_changed(self):
        self._onion_dirty = True
        self.win.drawing_area.update()

    def onion_frames(self):
        if not self.onion_enabled or self.is_playing:
            return []
        if self._onion_dirty:
            self._rebuild_onion()
        return self._onion_list

    def _rebuild_onion(self):
        self._onion_dirty = False
        self._onion_list = []
        w = self.win
        cur = w.current_page_index
        n = len(w.pages_data)
        jobs = [(cur - d, self.PREV_TINT, d) for d in range(1, self.onion_before + 1)]
        jobs += [(cur + d, self.NEXT_TINT, d) for d in range(1, self.onion_after + 1)]
        for idx, tint, dist in jobs:
            if 0 <= idx < n:
                img = self._tinted(idx, tint)
                if img is not None:
                    op = self.ONION_OPACITY[min(dist, len(self.ONION_OPACITY)) - 1]
                    self._onion_list.append((img, op))

    def _tinted(self, idx, tint):
        w = self.win
        st = w.drawing_area.layer_stack
        meta = st.export_meta()
        key = (idx, tint.rgb())
        sig = page_signature(w.drawing_cache_dir, idx, meta)
        cached = self._tint_cache.get(key)
        if cached and cached[0] == sig:
            return cached[1]
        img = composite_page(w.drawing_cache_dir, idx, meta, st.w, st.h, None)
        p = QPainter(img)
        p.setCompositionMode(QPainter.CompositionMode_SourceIn)
        p.fillRect(img.rect(), tint)
        p.end()
        self._tint_cache[key] = (sig, img)
        return img

    # -------------------------------------------------- kare süresi
    def get_hold(self, idx):
        if 0 <= idx < len(self.win.pages_data):
            return max(1, int(self.win.pages_data[idx].get("hold", 1)))
        return 1

    def set_hold(self, idx, n):
        if 0 <= idx < len(self.win.pages_data):
            self.win.pages_data[idx]["hold"] = max(1, min(120, int(n)))
            self.win.is_project_modified = True

    # -------------------------------------------------- oynatma
    @property
    def fps(self):
        return max(1, int(self.win.current_export_fps))

    def toggle_play(self):
        if self.is_playing:
            self.stop()
        else:
            self.start()

    def start(self):
        if self.is_playing or len(self.win.pages_data) == 0:
            return
        w = self.win
        w.flushCurrentPageToCache()
        self._seq = expand_sequence(w.pages_data)
        if not self._seq:
            return
        self._start_page = w.current_page_index
        self._shown_page = -1
        with self._lock:
            self._frames.clear()
        area = w.drawing_area
        area.playback_stop_cb = self.stop
        # editör araçlarının oynatma sırasında kullanılmaması için metin kutusunu kapat
        try:
            area.text_input_widget.hide()
        except Exception:
            pass
        self.is_playing = True
        self._clock.start()
        self._timer.start(12)
        self.playStateChanged.emit(True)
        self._tick()

    def stop(self):
        if not self.is_playing:
            return
        self._timer.stop()
        self.is_playing = False
        area = self.win.drawing_area
        area.playback_frame = None
        area.playback_stop_cb = None
        with self._lock:
            self._frames.clear()
        self._onion_dirty = True
        area.update()
        self.playStateChanged.emit(False)
        self.playheadMoved.emit(self.win.current_page_index)

    def _page_frame(self, page):
        with self._lock:
            img = self._frames.get(page)
            if img is not None:
                self._frames.move_to_end(page)
                return img
        img = self._render_frame(page)
        self._store(page, img)
        return img

    def _render_frame(self, page):
        w = self.win
        st = w.drawing_area.layer_stack
        bg = QColor(w.pages_data[page].get("background", w.background_color))
        return composite_page(w.drawing_cache_dir, page, st.export_meta(), st.w, st.h, bg)

    def _store(self, page, img):
        with self._lock:
            self._frames[page] = img
            self._frames.move_to_end(page)
            while len(self._frames) > self.CACHE_MAX:
                self._frames.popitem(last=False)

    def _tick(self):
        if not self.is_playing:
            return
        seq = self._seq
        pos = int(self._clock.elapsed() * self.fps / 1000.0)
        if pos >= len(seq):
            if not self.loop:
                self.stop()
                return
            pos %= len(seq)
        page = seq[pos]
        if page != self._shown_page:
            self._shown_page = page
            area = self.win.drawing_area
            area.playback_frame = self._page_frame(page)
            area.update()
            self.playheadMoved.emit(page)
        self._kick_prefetch(pos)

    def _kick_prefetch(self, pos):
        if self._prefetch_thread is not None and self._prefetch_thread.is_alive():
            return
        seq = self._seq
        upcoming = []
        for k in range(pos + 1, pos + 1 + self.PREFETCH * 4):
            page = seq[k % len(seq)] if (self.loop or k < len(seq)) else None
            if page is None:
                break
            if page not in upcoming:
                upcoming.append(page)
            if len(upcoming) >= self.PREFETCH:
                break
        with self._lock:
            missing = [p for p in upcoming if p not in self._frames]
        if not missing:
            return
        # QColor/pages_data okuması ana iş parçacığında yapılır; iş parçacığı yalnız QImage ile çalışır
        w = self.win
        st = w.drawing_area.layer_stack
        meta = st.export_meta()
        jobs = [(p, QColor(w.pages_data[p].get("background", w.background_color))) for p in missing]
        cache_dir, cw, ch = w.drawing_cache_dir, st.w, st.h

        def work():
            for p, bg in jobs:
                if not self.is_playing:
                    return
                img = composite_page(cache_dir, p, meta, cw, ch, bg)
                self._store(p, img)

        self._prefetch_thread = threading.Thread(target=work, daemon=True)
        self._prefetch_thread.start()


# ---------------------------------------------------------------------------
# Zaman çizelgesi paneli
# ---------------------------------------------------------------------------
_TL_CSS = """
QFrame#timelinePanel { background-color: #262626; border-top: 2px solid #555; }
QLabel { color: #ddd; background: transparent; }
QCheckBox { color: #ddd; spacing: 4px; }
QSpinBox { background-color: #333; color: #eee; border: 1px solid #555; border-radius: 5px; padding: 1px 3px; }
QPushButton, QToolButton { background-color: #333; color: #eee; border: 1px solid #555; border-radius: 6px; padding: 2px 8px; }
QPushButton:hover, QToolButton:hover { background-color: #444; }
QPushButton:checked, QToolButton:checked { background-color: #4a5f8a; border-color: #7f97c9; }
QListWidget { background-color: #1b1b1b; border: 1px solid #444; border-radius: 6px; outline: none; }
QListWidget::item { border: 2px solid transparent; border-radius: 4px; margin: 1px; }
QListWidget::item:selected { border: 2px solid #6fa8ff; background-color: #2b3550; }
"""


class TimelinePanel(QFrame):
    def __init__(self, window, controller):
        super().__init__(window)
        self.setObjectName("timelinePanel")
        self.win = window
        self.ctrl = controller
        self._block = False
        self.show_thumbs = QSettings("kavram", "DrawingEditor").value("timelineThumbs", True, type=bool)
        self._thumbs = {}            # sayfa -> (imza, QPixmap)
        self._pending = []
        self._refresh_pending = False
        self.setStyleSheet(_TL_CSS)
        self.setFixedHeight(118 if self.show_thumbs else 90)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 6)
        root.setSpacing(4)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.play_btn = QToolButton()
        self.play_btn.setIcon(create_svg_icon(SVG_PLAY, 18))
        self.play_btn.setToolTip("Oynat / Durdur (Ctrl+Boşluk)")
        self.play_btn.clicked.connect(self.ctrl.toggle_play)
        bar.addWidget(self.play_btn)

        self.loop_chk = QCheckBox("Döngü")
        self.loop_chk.setChecked(self.ctrl.loop)
        self.loop_chk.toggled.connect(self.ctrl.set_loop)
        bar.addWidget(self.loop_chk)

        bar.addWidget(QLabel("FPS"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(self.win.current_export_fps)
        self.fps_spin.valueChanged.connect(self._on_fps)
        bar.addWidget(self.fps_spin)

        bar.addSpacing(10)
        self.onion_btn = QToolButton()
        self.onion_btn.setCheckable(True)
        self.onion_btn.setChecked(self.ctrl.onion_enabled)
        self.onion_btn.setIcon(create_svg_icon(SVG_ONION, 18))
        self.onion_btn.setToolTip("Soğan zarı: önceki/sonraki kareleri soluk göster (Ctrl+Shift+O)")
        self.onion_btn.toggled.connect(self.ctrl.set_onion_enabled)
        bar.addWidget(self.onion_btn)
        bar.addWidget(QLabel("Önce"))
        self.before_spin = QSpinBox()
        self.before_spin.setRange(0, 3)
        self.before_spin.setValue(self.ctrl.onion_before)
        self.before_spin.valueChanged.connect(lambda v: self.ctrl.set_onion_range(before=v))
        bar.addWidget(self.before_spin)
        bar.addWidget(QLabel("Sonra"))
        self.after_spin = QSpinBox()
        self.after_spin.setRange(0, 3)
        self.after_spin.setValue(self.ctrl.onion_after)
        self.after_spin.valueChanged.connect(lambda v: self.ctrl.set_onion_range(after=v))
        bar.addWidget(self.after_spin)

        bar.addSpacing(10)
        self.thumb_btn = SvgIconButton(SVG_EYE_OPEN if self.show_thumbs else SVG_EYE_CLOSED,
                                       "#eeeeee" if self.show_thumbs else "#888888", size=28, icon_px=19)
        self.thumb_btn.setToolTip("Kare küçük resimlerini göster / gizle\n(Gizliyken karelerde yalnız numara görünür, sistem daha az yorulur)")
        self.thumb_btn.clicked.connect(lambda: self._set_thumbs(not self.show_thumbs))
        bar.addWidget(self.thumb_btn)
        bar.addWidget(QLabel("Küçük resim"))

        bar.addSpacing(10)
        bar.addWidget(QLabel("Kare süresi"))
        self.hold_spin = QSpinBox()
        self.hold_spin.setRange(1, 120)
        self.hold_spin.setSuffix(" kare")
        self.hold_spin.setToolTip("Seçili karenin kaç kare boyunca tutulacağı")
        self.hold_spin.valueChanged.connect(self._on_hold)
        bar.addWidget(self.hold_spin)

        bar.addStretch(1)
        for text, tip, fn in (("+ Boş", "Sonrasına boş kare ekle", self.win.insertBlankPageAfter),
                              ("Çoğalt", "Kareyi sonrasına çoğalt", self.win.duplicateToNextPage),
                              ("Sil", "Kareyi sil", self.win.removePage)):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            bar.addWidget(b)
        root.addLayout(bar)

        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ListMode)
        self.list.setFlow(QListWidget.LeftToRight)
        self.list.setWrapping(False)
        self.list.setSpacing(3)
        self.list.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        self.list.currentRowChanged.connect(self._on_row)
        self.list.model().rowsMoved.connect(self._rows_moved)
        root.addWidget(self.list, 1)

        self.ctrl.playStateChanged.connect(self._on_play_state)
        self.ctrl.playheadMoved.connect(self._on_playhead)
        area = self.win.drawing_area
        area.contentChanged.connect(self._content_changed)

        self._content_timer = QTimer(self)
        self._content_timer.setSingleShot(True)
        self._content_timer.timeout.connect(self._refresh_current_thumb)

        self._fill_timer = QTimer(self)
        self._fill_timer.setSingleShot(True)
        self._fill_timer.timeout.connect(self._fill_next)

        self.refresh()

    # ------------------------------------------------------------ boyutlar
    def _thumb_size(self):
        if not self.show_thumbs:
            return 46, 30
        cw, ch = max(1, self.win.canvas_width), max(1, self.win.canvas_height)
        th = 58
        tw = max(40, min(140, int(round(th * cw / float(ch)))))
        return tw, th

    def _scroll_to_current(self):
        item = self.list.currentItem()
        if item is not None:
            self.list.scrollToItem(item)

    # ------------------------------------------------------------ yenileme
    def schedule_refresh(self):
        if self._refresh_pending:
            return
        self._refresh_pending = True
        QTimer.singleShot(0, self._do_refresh)

    def _do_refresh(self):
        self._refresh_pending = False
        self.refresh()

    def refresh(self):
        w = self.win
        tw, th = self._thumb_size()
        self._block = True
        try:
            self.list.clear()
            self.list.setIconSize(QSize(tw, th))
            blank = QPixmap(tw, th)
            blank.fill(QColor("#222"))
            for i in range(len(w.pages_data)):
                item = QListWidgetItem(QIcon(blank), "")
                item.setSizeHint(QSize(tw + 8, th + 8))
                item.setToolTip(f"Kare {i + 1}")
                self.list.addItem(item)
            self.list.setCurrentRow(min(w.current_page_index, self.list.count() - 1))
            self._scroll_to_current()
        finally:
            self._block = False
        self._sync_hold()
        self._queue_all()

    def sync_current(self):
        """Sayfa değiştiğinde seçimi günceller (sayfayı yeniden yüklemeden)."""
        if self.list.count() != len(self.win.pages_data):
            self.schedule_refresh()
            return
        self._block = True
        try:
            self.list.setCurrentRow(self.win.current_page_index)
            self._scroll_to_current()
        finally:
            self._block = False
        self._sync_hold()
        self._queue_thumb(self.win.current_page_index, front=True)

    def _sync_hold(self):
        self.hold_spin.blockSignals(True)
        self.hold_spin.setValue(self.ctrl.get_hold(self.win.current_page_index))
        self.hold_spin.blockSignals(False)

    # ------------------------------------------------------------ küçük resimler
    def _signature(self, i):
        w = self.win
        st = w.drawing_area.layer_stack
        bg = QColor(w.background_color if i == w.current_page_index else w.pages_data[i].get("background", w.background_color))
        if i == w.current_page_index:
            return ("live", id(self), w.canvas_width, bg.rgba(), self.ctrl.get_hold(i), self._live_rev)
        return (page_signature(w.drawing_cache_dir, i, st.export_meta()), bg.rgba(), self.ctrl.get_hold(i),
                w.canvas_width, w.canvas_height)

    _live_rev = 0

    def _set_thumbs(self, value):
        self.show_thumbs = bool(value)
        QSettings("kavram", "DrawingEditor").setValue("timelineThumbs", self.show_thumbs)
        self.thumb_btn.setSvg(SVG_EYE_OPEN if self.show_thumbs else SVG_EYE_CLOSED,
                              "#eeeeee" if self.show_thumbs else "#888888")
        self.setFixedHeight(118 if self.show_thumbs else 90)
        self._thumbs.clear()
        self._pending = []
        self.refresh()

    def _number_tile(self, i):
        """Küçük resim kapalıyken: yalnız kare numarası (ucuz)."""
        tw, th = self._thumb_size()
        pm = QPixmap(tw, th)
        pm.fill(QColor("#2a303c"))
        p = QPainter(pm)
        f = QFont()
        f.setPixelSize(15)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRect(0, 0, tw, th), Qt.AlignCenter, str(i + 1))
        hold = self.ctrl.get_hold(i)
        if hold > 1:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 170, 40, 230))
            p.drawRoundedRect(QRect(tw - 22, th - 12, 21, 11), 3, 3)
            p.setPen(QColor("#111"))
            f2 = QFont()
            f2.setPixelSize(9)
            f2.setBold(True)
            p.setFont(f2)
            p.drawText(QRect(tw - 22, th - 12, 21, 11), Qt.AlignCenter, f"×{hold}")
        p.end()
        return pm

    def _set_tile(self, i):
        if 0 <= i < self.list.count():
            self.list.item(i).setIcon(QIcon(self._number_tile(i)))

    def _queue_all(self):
        if not self.show_thumbs:
            for i in range(self.list.count()):
                self._set_tile(i)
            return
        cur = self.win.current_page_index
        order = sorted(range(len(self.win.pages_data)), key=lambda i: abs(i - cur))
        self._pending = [i for i in order if self._thumb_stale(i)]
        for i in range(len(self.win.pages_data)):
            cached = self._thumbs.get(i)
            if cached is not None and i < self.list.count():
                self.list.item(i).setIcon(QIcon(cached[1]))
        self._schedule_fill()

    def _thumb_stale(self, i):
        cached = self._thumbs.get(i)
        return cached is None or cached[0] != self._signature(i)

    def _queue_thumb(self, i, front=False):
        if not self.show_thumbs:
            self._set_tile(i)
            return
        if i in self._pending:
            self._pending.remove(i)
        if front:
            self._pending.insert(0, i)
        else:
            self._pending.append(i)
        self._schedule_fill()

    def _schedule_fill(self):
        if self._pending and not self._fill_timer.isActive():
            self._fill_timer.start(5)

    def _fill_next(self):
        budget = 3
        while self._pending and budget > 0:
            i = self._pending.pop(0)
            if i >= self.list.count() or i >= len(self.win.pages_data):
                continue
            sig = self._signature(i)
            cached = self._thumbs.get(i)
            if cached is None or cached[0] != sig:
                pm = self._make_thumb(i)
                self._thumbs[i] = (sig, pm)
            else:
                pm = cached[1]
            self.list.item(i).setIcon(QIcon(pm))
            budget -= 1
        self._schedule_fill()

    def _make_thumb(self, i):
        w = self.win
        area = w.drawing_area
        st = area.layer_stack
        tw, th = self._thumb_size()
        if i == w.current_page_index:
            img = area.flattenCurrent(QColor(w.background_color))
        else:
            bg = QColor(w.pages_data[i].get("background", w.background_color))
            img = composite_page(w.drawing_cache_dir, i, st.export_meta(), st.w, st.h, bg)
        scaled = img.scaled(tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pm = QPixmap(tw, th)
        pm.fill(QColor("#111"))
        p = QPainter(pm)
        p.drawImage((tw - scaled.width()) // 2, (th - scaled.height()) // 2, scaled)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 170))
        p.drawRoundedRect(QRect(2, 2, 26, 15), 3, 3)
        p.setPen(QColor("#fff"))
        f = QFont()
        f.setPixelSize(10)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRect(2, 2, 26, 15), Qt.AlignCenter, str(i + 1))
        hold = self.ctrl.get_hold(i)
        if hold > 1:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 170, 40, 220))
            p.drawRoundedRect(QRect(tw - 30, th - 17, 28, 15), 3, 3)
            p.setPen(QColor("#111"))
            p.drawText(QRect(tw - 30, th - 17, 28, 15), Qt.AlignCenter, f"×{hold}")
        p.end()
        return pm

    def _content_changed(self):
        if not self.show_thumbs:
            return
        self._live_rev += 1
        self._content_timer.start(450)

    def _refresh_current_thumb(self):
        i = self.win.current_page_index
        if 0 <= i < self.list.count():
            self._queue_thumb(i, front=True)

    # ------------------------------------------------------------ olaylar
    def _on_row(self, row):
        if self._block or row < 0 or self.ctrl.is_playing:
            return
        if row != self.win.current_page_index:
            self.win.loadPageData(row)

    def _on_fps(self, v):
        self.win.current_export_fps = int(v)
        QSettings("kavram", "DrawingEditor").setValue("exportFPS", int(v))

    def _on_hold(self, v):
        i = self.win.current_page_index
        self.ctrl.set_hold(i, v)
        self._queue_thumb(i, front=True)

    def _rows_moved(self, _parent, start, _end, _dest_parent, row):
        src = start
        dst = row - 1 if row > start else row
        if src == dst:
            return
        QTimer.singleShot(0, lambda: self.win.movePage(src, dst))

    def _on_play_state(self, playing):
        self.play_btn.setIcon(create_svg_icon(SVG_STOP if playing else SVG_PLAY, 18))
        self.list.setEnabled(not playing)
        if not playing:
            self.sync_current()

    def _on_playhead(self, page):
        if not self.ctrl.is_playing:
            return
        self._block = True
        try:
            if 0 <= page < self.list.count():
                self.list.setCurrentRow(page)
                self._scroll_to_current()
        finally:
            self._block = False

    def _context_menu(self, pos):
        item = self.list.itemAt(pos)
        if item is None:
            return
        row = self.list.row(item)
        if row != self.win.current_page_index:
            self.win.loadPageData(row)
        menu = QMenu(self)
        a_hold = menu.addAction("Kare süresini ayarla…")
        a_blank = menu.addAction("Sonrasına boş kare ekle")
        a_dup = menu.addAction("Sonrasına çoğalt")
        menu.addSeparator()
        a_del = menu.addAction("Sil")
        chosen = menu.exec_(self.list.mapToGlobal(pos))
        if chosen == a_hold:
            v, ok = QInputDialog.getInt(self, "Kare Süresi", "Kaç kare boyunca tutulsun?",
                                        self.ctrl.get_hold(row), 1, 120)
            if ok:
                self.hold_spin.setValue(v)
        elif chosen == a_blank:
            self.win.insertBlankPageAfter()
        elif chosen == a_dup:
            self.win.duplicateToNextPage()
        elif chosen == a_del:
            self.win.removePage()


# ===========================================================================
# BÖLÜM: ANİMASYON DIŞA AKTARMA
# ===========================================================================
# Kavram - Animasyon dışa aktarma (MP4, WebM, MKV, GIF, APNG, PNG dizisi)
# Kareler ayrı bir iş parçacığında (QThread) üretilir; arayüz donmaz, iptal edilebilir.



# anahtar, etiket, uzantı, saydamlık desteği
EXPORT_FORMATS = [
    ("mp4", "MP4 (H.264)", ".mp4", False),
    ("webm", "WebM (VP9, saydamlık destekli)", ".webm", True),
    ("mkv", "MKV (H.264)", ".mkv", False),
    ("gif", "GIF (animasyonlu)", ".gif", True),
    ("apng", "APNG (animasyonlu PNG)", ".png", True),
    ("png_seq", "PNG dizisi (klasöre tüm kareler)", "", True),
]
_FMT = {k: (label, ext, alpha) for k, label, ext, alpha in EXPORT_FORMATS}


class ExportCancelled(Exception):
    pass


class ExportWorker(QThread):
    progress = pyqtSignal(int, str)
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, params, parent=None):
        super().__init__(parent)
        self.p = params
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _check(self):
        if self._cancel:
            raise ExportCancelled()

    def run(self):
        p = self.p
        tmp = None
        try:
            fmt = p["fmt"]
            transparent = p["transparent"] and _FMT[fmt][2]
            tmp = tempfile.mkdtemp(prefix="kavram_export_")
            if fmt == "png_seq":
                frame_dir = p["out_path"]
                os.makedirs(frame_dir, exist_ok=True)
                name_fmt = "kare_%05d.png"
            else:
                frame_dir = tmp
                name_fmt = "frame_%05d.png"

            jobs = p["jobs"]                       # [(sayfa_idx, (r,g,b,a), hold)]
            total = max(1, sum(h for _i, _bg, h in jobs))
            scale = p["scale"] / 100.0
            out_w = max(2, int(round(p["w"] * scale)))
            out_h = max(2, int(round(p["h"] * scale)))

            frame_no = 1
            for k, (idx, bg, hold) in enumerate(jobs):
                self._check()
                bgc = None if transparent else QColor(*bg)
                img = composite_page(p["cache_dir"], idx, p["meta"], p["w"], p["h"], bgc)
                if (out_w, out_h) != (p["w"], p["h"]):
                    img = img.scaled(out_w, out_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                if not transparent:
                    img = img.convertToFormat(QImage.Format_RGB32)
                first = os.path.join(frame_dir, name_fmt % frame_no)
                if not img.save(first, "PNG"):
                    raise IOError(f"Kare yazılamadı: {first}")
                for r in range(1, hold):          # kare süresi: aynı kareyi kopyala
                    shutil.copyfile(first, os.path.join(frame_dir, name_fmt % (frame_no + r)))
                frame_no += hold
                pct = int(5 + 80 * (frame_no - 1) / total) if fmt != "png_seq" else int(100 * (frame_no - 1) / total)
                self.progress.emit(min(pct, 99), f"Kare {k + 1}/{len(jobs)} hazırlanıyor…")

            if fmt == "png_seq":
                self.done.emit(frame_dir)
                return

            self._check()
            self.progress.emit(88, "Video kodlanıyor…")
            self._encode(fmt, transparent, tmp, p)
            self.progress.emit(100, "Tamamlandı")
            self.done.emit(p["out_path"])
        except ExportCancelled:
            try:
                if p["fmt"] != "png_seq" and os.path.exists(p["out_path"]):
                    os.remove(p["out_path"])
            except OSError:
                pass
            self.failed.emit("")           # boş mesaj = kullanıcı iptal etti
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)

    def _encode(self, fmt, transparent, tmp, p):
        ff = p["ffmpeg"]
        out = p["out_path"]
        inp = os.path.join(tmp, "frame_%05d.png")
        base = [ff, "-y", "-framerate", str(p["fps"]), "-i", inp]
        if fmt in ("mp4", "mkv"):
            cmd = base + ["-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "18", "-pix_fmt", "yuv420p"]
            if fmt == "mp4":
                cmd += ["-movflags", "+faststart"]
            cmd += [out]
        elif fmt == "webm":
            pix = "yuva420p" if transparent else "yuv420p"
            cmd = base + ["-c:v", "libvpx-vp9", "-pix_fmt", pix, "-b:v", "0", "-crf", "30"]
            if transparent:
                cmd += ["-auto-alt-ref", "0"]
            cmd += [out]
        elif fmt == "gif":
            flt = ("split[s0][s1];[s0]palettegen=reserve_transparent=%d[pal];"
                   "[s1][pal]paletteuse=alpha_threshold=128") % (1 if transparent else 0)
            cmd = base + ["-filter_complex", flt, "-loop", "0", out]
        elif fmt == "apng":
            cmd = base + ["-plays", "0", "-pix_fmt", "rgba", "-f", "apng", out]
        else:
            raise ValueError("Bilinmeyen format: " + fmt)

        log_path = os.path.join(tmp, "ffmpeg.log")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        with open(log_path, "w", encoding="utf-8", errors="replace") as log:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=log, creationflags=flags)
            while proc.poll() is None:
                if self._cancel:
                    proc.kill()
                    proc.wait()
                    raise ExportCancelled()
                time.sleep(0.05)
        if proc.returncode != 0:
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    tail = "".join(f.readlines()[-8:])
            except OSError:
                tail = ""
            raise RuntimeError(f"ffmpeg hata kodu {proc.returncode}\n{tail}")


class ExportDialog(QDialog):
    def __init__(self, win, fps, preset=None):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Animasyonu Dışa Aktar")
        self.setMinimumWidth(460)
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; }
            QLabel, QCheckBox { color: #eee; }
            QLineEdit, QSpinBox, QComboBox { background-color: #3a3a3a; color: #eee; border: 1px solid #555;
                                              border-radius: 5px; padding: 3px 6px; }
            QComboBox QAbstractItemView { background-color: #3a3a3a; color: #eee; }
            QPushButton { background-color: #3a3a3a; color: #eee; border: 1px solid #666; border-radius: 6px; padding: 5px 14px; }
            QPushButton:hover { background-color: #4a4a4a; }
        """)
        lay = QVBoxLayout(self)
        form_rows = []

        self.fmt = QComboBox()
        for key, label, _ext, _alpha in EXPORT_FORMATS:
            self.fmt.addItem(label, key)
        if preset:
            i = self.fmt.findData(preset)
            if i >= 0:
                self.fmt.setCurrentIndex(i)
        self.fmt.currentIndexChanged.connect(self._on_format)

        self.fps = QSpinBox()
        self.fps.setRange(1, 120)
        self.fps.setValue(fps)

        self.scale = QSpinBox()
        self.scale.setRange(10, 400)
        self.scale.setValue(100)
        self.scale.setSuffix(" %")

        self.transparent = QCheckBox("Saydam arka plan (arka plan rengi olmadan)")

        self.path = QLineEdit()
        browse = QPushButton("Gözat…")
        browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path, 1)
        path_row.addWidget(browse)

        n_frames = sum(max(1, int(pg.get("hold", 1))) for pg in win.pages_data)
        self.info = QLabel()
        self.info.setStyleSheet("color: #aaa;")

        for text, widget in (("Biçim", self.fmt), ("Kare hızı (FPS)", self.fps), ("Ölçek", self.scale)):
            row = QHBoxLayout()
            lbl = QLabel(text)
            lbl.setMinimumWidth(110)
            row.addWidget(lbl)
            row.addWidget(widget, 1)
            lay.addLayout(row)
        lay.addWidget(self.transparent)
        lay.addWidget(QLabel("Kayıt yeri"))
        lay.addLayout(path_row)
        lay.addWidget(self.info)

        btns = QHBoxLayout()
        btns.addStretch(1)
        ok = QPushButton("Dışa Aktar")
        ok.setDefault(True)
        cancel = QPushButton("İptal")
        ok.clicked.connect(self._accept)
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)

        self._n_frames = n_frames
        self.fps.valueChanged.connect(self._update_info)
        self.scale.valueChanged.connect(self._update_info)
        self._on_format()

    def _update_info(self):
        secs = self._n_frames / float(max(1, self.fps.value()))
        w = int(round(self.win.canvas_width * self.scale.value() / 100.0))
        h = int(round(self.win.canvas_height * self.scale.value() / 100.0))
        self.info.setText(f"{self._n_frames} kare  •  {secs:.1f} sn  •  {w}×{h}")

    def _on_format(self):
        key = self.fmt.currentData()
        alpha = _FMT[key][2]
        self.transparent.setEnabled(alpha)
        if not alpha:
            self.transparent.setChecked(False)
        # uzantıyı yeni biçime uydur
        cur = self.path.text().strip()
        if cur and key != "png_seq":
            root, _ = os.path.splitext(cur)
            self.path.setText(root + _FMT[key][1])
        self._update_info()

    def _default_dir(self):
        p = getattr(self.win, "current_file_path", None)
        if p:
            return os.path.dirname(p)
        return self.win.DEFAULT_BASE_DIR

    def _browse(self):
        key = self.fmt.currentData()
        if key == "png_seq":
            d = _fm.get_existing_directory(self, "Kare klasörünü seç", self._default_dir(), editor="Drawing")
            if d:
                self.path.setText(d)
        else:
            ext = _FMT[key][1]
            f, _ = _fm.get_save_file_name(self, "Dışa aktar", os.path.join(self._default_dir(), "animasyon" + ext),
                                               f"{_FMT[key][0]} (*{ext})", editor="Drawing")
            if f:
                if not f.lower().endswith(ext):
                    f += ext
                self.path.setText(f)

    def _accept(self):
        if not self.path.text().strip():
            self._browse()
            if not self.path.text().strip():
                return
        self.accept()

    def options(self):
        key = self.fmt.currentData()
        out = self.path.text().strip()
        if key != "png_seq" and not out.lower().endswith(_FMT[key][1]):
            out += _FMT[key][1]
        return {"fmt": key, "fps": self.fps.value(), "scale": self.scale.value(),
                "transparent": self.transparent.isChecked(), "out_path": out}


def start_export(win, preset=None):
    """Dışa aktarma penceresini açar ve işi arka planda başlatır."""
    old = getattr(win, "_export_worker", None)
    if old is not None and old.isRunning():
        QMessageBox.information(win, "Dışa Aktarma", "Önceki dışa aktarma hâlâ sürüyor.")
        return
    win.flushCurrentPageToCache()
    dlg = ExportDialog(win, win.current_export_fps, preset)
    if dlg.exec_() != QDialog.Accepted:
        return
    o = dlg.options()
    if o["fmt"] != "png_seq" and not ffmpeg_available():
        QMessageBox.critical(win, "Hata",
                             f"Bu biçim için ffmpeg gerekli, bulunamadı:\n{FFMPEG_PATH}\n\n"
                             "Uygulama dizinine 'bin/ffmpeg' koyun veya ffmpeg'i sisteme kurun.\n"
                             "PNG dizisi biçimi ffmpeg gerektirmez.")
        return
    win.current_export_fps = o["fps"]
    QSettings("kavram", "DrawingEditor").setValue("exportFPS", o["fps"])

    st = win.drawing_area.layer_stack
    jobs = []
    for i, pg in enumerate(win.pages_data):
        c = QColor(pg.get("background", win.background_color))
        jobs.append((i, (c.red(), c.green(), c.blue(), c.alpha()), max(1, int(pg.get("hold", 1)))))
    params = {"cache_dir": win.drawing_cache_dir, "meta": st.export_meta(), "w": st.w, "h": st.h,
              "jobs": jobs, "ffmpeg": FFMPEG_PATH, **o}

    worker = ExportWorker(params)
    prog = QProgressDialog("Hazırlanıyor…", "İptal", 0, 100, win)
    prog.setWindowTitle("Dışa Aktarılıyor")
    prog.setWindowModality(Qt.WindowModal)
    prog.setMinimumDuration(0)
    prog.setAutoClose(False)
    prog.setAutoReset(False)
    prog.setValue(0)

    def on_progress(v, msg):
        prog.setValue(v)
        prog.setLabelText(msg)

    def close_prog():
        try:
            prog.canceled.disconnect()
        except TypeError:
            pass
        prog.close()

    def on_done(path):
        close_prog()
        win._export_worker = None
        _fm.notify_saved(win)

    def on_failed(msg):
        close_prog()
        win._export_worker = None
        if msg:
            QMessageBox.critical(win, "Hata", f"Dışa aktarma başarısız:\n{msg}")

    worker.progress.connect(on_progress)
    worker.done.connect(on_done)
    worker.failed.connect(on_failed)
    prog.canceled.connect(worker.cancel)
    win._export_worker = worker
    worker.start()


# ===========================================================================
# BÖLÜM: ANA PENCERE (DrawingEditorWindow)
# ===========================================================================
class DrawingEditorWindow(QWidget):
    DEFAULT_BASE_DIR = _KAVRAM_EXPORT_DIR

    TOOL_ORDER = [
        ("Normal", 0),
        ("Yazı (Text)", 35),
        ("Ok İşareti (Arrow)", 36),
        ("Pencil", 1),
        ("Brush", 2),
        ("Line (Nokta)", 3),
        ("Solid Fill", 4),
        ("Curve (Eğri)", 5),
        ("Calligraphy", 6),
        ("Marker (Keçeli)", 7),
        ("Spray (Sprey)", 8),
        ("Chalk (Tebeşir)", 9),
        ("Highlighter", 10),
        ("Airbrush", 11),
        ("Ink (Dolma)", 12),
        ("Pixel", 13),
        ("Charcoal (Karakalem)", 14),
        ("Stamp (Damga)", 15),
        ("Web (Örümcek)", 16),
        ("Neon", 17),
        ("Confetti", 18),
        ("Leaf (Yaprak)", 19),
        ("Star (Yıldız)", 20),
        ("Bubble (Balon)", 21),
        ("Grass (Çim)", 22),
        ("Rainbow", 23),
        ("Fur (Kürk)", 24),
        ("Sketchy", 25),
        ("Dotted (Noktalı)", 26),
        ("Dashed (Kesik)", 27),
        ("Double (Çift)", 28),
        ("Shadow (Gölge)", 29),
        ("3D", 30),
        ("DNA", 31),
        ("Sawtooth (Testere)", 32),
        ("Grid (Izgara)", 33),
        ("Lightning (Şimşek)", 34),
        ("Dikdörtgen (Rectangle)", 37),
        ("Daire (Circle)", 38)
    ]

    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        
        self.is_project_modified = False
        
        settings = QSettings("kavram", "DrawingEditor")
        self.canvas_width = settings.value("canvasWidth", 1100, type=int)
        self.canvas_height = settings.value("canvasHeight", 600, type=int)

        self.drawing_cache_dir = os.path.join(DrawingEditorWindow.DEFAULT_BASE_DIR, "Drawing")
        self.clearDrawingCache()

        self.pen_color = QColor("#cccccc")
        self.mix_colors = [QColor("#cccccc")]
        self.mix_history = [[QColor("#cccccc")]]
        self.mix_mode = 'random'
        self.mix_angle = 0

        saved_bg = settings.value("backgroundColor", "#333", type=str)
        self.background_color = QColor(saved_bg)

        self.pen_radius = 8
        self.eraser_radius = 15
        self.sensitivity_value = -1

        self.eraser_mode = False
        self.pen_pressure_enabled = False
        self.text_mode = False
        self.placing_image = False
        self.polyline_mode = False
        self.curve_mode = False
        self.solid_fill_mode = False
        self.mirror_mode = False
        self.mirror_axis = 'vertical'
        self.is_v_pressed = False
        self.is_c_pressed = False
        self.always_top_mode = False
        self.current_file_path = None

        self.pages_data = []
        self.current_page_index = 0
        self.max_pages = 500

        self.normal_tool_index = 0
        self.eraser_tool_index = 4

        self.tool_radiuses = {
            0: 8, 1: 3, 2: 15, 3: 5, 4: 1, 5: 5,
            6: 8, 7: 15, 8: 30, 9: 5, 10: 20, 11: 40, 12: 3, 13: 1, 14: 10, 15: 30, 16: 2,
            17: 10, 18: 20, 19: 15, 20: 20, 21: 15, 22: 5, 23: 5, 24: 10, 25: 1, 26: 3, 27: 3,
            28: 6, 29: 5, 30: 5, 31: 10, 32: 2, 33: 1, 34: 2,
            35: 8, 36: 4, 37: 5, 38: 5
        }
        self.current_tool_index = 0
        
        self.lazy_mouse_enabled = False
        self.lazy_radius = 30
        self.lazy_factor = 15
        
        self.current_export_fps = settings.value("exportFPS", 24, type=int)
        
        self.alt_last_press_time = 0
        self.alt_double_click_threshold = 300

        self.reference_transparency = settings.value("referenceTransparency", 55, type=int)
        self.reference_transparency = max(0, min(95, self.reference_transparency))

        self.global_reference_visible = True
        self.next_reference_id = 1

        # Araç ipuçları (özellik + kısayol yazısı): siyah arka plan, beyaz metin
        _app = QApplication.instance()
        if _app is not None and "Kavram-tooltip" not in _app.styleSheet():
            _app.setStyleSheet(_app.styleSheet() + "\n/* Kavram-tooltip */\nQToolTip { background-color: #000000; color: #ffffff; "
                               "border: 1px solid #5a5a5a; padding: 4px 7px; font-size: 12px; }")
        self.initUI()
        
        self.pages_data.append({"background": self.background_color, "hold": 1})
        
        first_json_path = os.path.join(self.drawing_cache_dir, "sx.json")
        with open(first_json_path, 'w', encoding='utf-8') as f:
            json.dump([], f)
        
        self.loadPageData(0, save_current=False)
        
        self.loadLazyMouseSettings()
        self.lazy_mouse_button.updateButtonText(self)
        self.lazy_mouse_button.updateToolTip(self)
        if self.lazy_mouse_enabled:
            self.lazy_mouse_button.setStyleSheet(self.buttonStylePressure(True))
            
        QTimer.singleShot(100, self.fitCanvasToView)

    def fitCanvasToView(self):
        margin = 40
        w = self.drawing_area.width() - margin
        h = self.drawing_area.height() - margin
        
        if w > 0 and h > 0:
            zoom_x = w / float(self.canvas_width)
            zoom_y = h / float(self.canvas_height)
            
            new_zoom = min(zoom_x, zoom_y)
            new_zoom = max(0.05, min(10.0, new_zoom))
            
            self.drawing_area.zoom_factor = new_zoom
            self.drawing_area.view_offset = QPoint(0, 0)
            self.drawing_area.update()

    def clearDrawingCache(self):
        os.makedirs(self.drawing_cache_dir, exist_ok=True)
        try:
            for name in os.listdir(self.drawing_cache_dir):
                if (name.startswith("s") or name.startswith("r")) and (name.endswith(".png") or name.endswith("_elements.json") or name == "sx.json"):
                    path = os.path.join(self.drawing_cache_dir, name)
                    if os.path.isfile(path):
                        os.remove(path)
        except Exception:
            pass

    def keyPressEvent(self, event):
        import time
        if event.key() == Qt.Key_V:
            self.is_v_pressed = True
            self.drawing_area.setCursor(Qt.SizeHorCursor)
        elif event.key() == Qt.Key_C:
            self.is_c_pressed = True
        elif event.key() == Qt.Key_N:
            if not self.drawing_area.text_input_widget.isVisible():
                self.pen_style_combo.showPopup()
        elif event.key() == Qt.Key_R:
            self.showRadiusSliderDialog()
        
        elif event.key() == Qt.Key_Right:
            if len(self.pages_data) > 0:
                new_idx = (self.current_page_index + 1) % len(self.pages_data)
                self.loadPageData(new_idx)
        elif event.key() == Qt.Key_Left:
            if len(self.pages_data) > 0:
                new_idx = (self.current_page_index - 1) % len(self.pages_data)
                self.loadPageData(new_idx)

        elif event.key() == Qt.Key_Alt:
            current_time = int(time.time() * 1000)
            if current_time - self.alt_last_press_time < self.alt_double_click_threshold:
                self.drawing_area.alt_permanent_pan_mode = not self.drawing_area.alt_permanent_pan_mode
                if self.drawing_area.alt_permanent_pan_mode:
                    self.drawing_area.setCursor(Qt.OpenHandCursor)
                else:
                    self.drawing_area.setCursor(Qt.CrossCursor)
            else:
                self.drawing_area.alt_held = True
            self.alt_last_press_time = current_time
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.polyline_mode or self.curve_mode:
                self.drawing_area.finalizePolyline()

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_V:
            self.is_v_pressed = False
            self.drawing_area.setCursor(Qt.ArrowCursor)
        elif event.key() == Qt.Key_C:
            self.is_c_pressed = False
        elif event.key() == Qt.Key_Alt:
            self.drawing_area.alt_held = False
            if not self.drawing_area.alt_permanent_pan_mode:
                self.drawing_area.setCursor(Qt.CrossCursor)
        
        super().keyReleaseEvent(event)

    def showRadiusSliderDialog(self):
        current_val = self.eraser_radius if self.eraser_mode else self.pen_radius
        dialog = RadiusOverlayDialog(current_val, self)
        dialog_x = (self.width() - dialog.width()) // 2
        dialog_y = (self.height() - dialog.height()) // 2
        dialog.move(self.mapToGlobal(QPoint(dialog_x, dialog_y)))
        dialog.slider.valueChanged.connect(self.changeRadiusValue)
        dialog.exec_()

    def showSensitivitySliderDialog(self):
        dialog = RadiusOverlayDialog(self.sensitivity_value, self, is_sensitivity=True)
        dialog_x = (self.width() - dialog.width()) // 2
        dialog_y = (self.height() - dialog.height()) // 2
        dialog.move(self.mapToGlobal(QPoint(dialog_x, dialog_y)))
        dialog.exec_()

    def initUI(self):
        self.setWindowTitle("Kavram")
        self.setWindowIcon(QIcon(resource_path('ikon/kavram.png')))
        self.resize(900, 600)
        self.setStyleSheet("background-color: #222;")

        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("background-color: #222; border-bottom: 2px solid #555;")
        toolbar_frame.setFixedHeight(40)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.setSpacing(10)

        self.file_button = RightClickButton("File")
        self.file_button.setStyleSheet(self.buttonStyle())
        self.file_button.setFixedSize(90, 30)
        self.file_button.clicked.connect(self.importFile)
        self.file_button.rightClicked.connect(self.importReferenceImage)  # Sağ tık referans ekle
        toolbar_layout.addWidget(self.file_button, alignment=Qt.AlignLeft)

        self.save_button = QPushButton()
        self.save_button.setIcon(create_svg_icon(SVG_SAVE_ICON, size=20))
        self.save_button.setStyleSheet(self.buttonStyleMini())
        self.save_button.setFixedSize(30, 30)
        self.save_button.setToolTip("Projeyi Kaydet")
        self.save_button.clicked.connect(self.saveProject)
        toolbar_layout.addWidget(self.save_button, alignment=Qt.AlignLeft)

        page_control_widget = QWidget()
        page_control_widget.setFixedSize(140, 30)
        page_control_layout = QHBoxLayout(page_control_widget)
        page_control_layout.setContentsMargins(0,0,0,0)
        page_control_layout.setSpacing(2)

        self.page_button = PageNavigatorButton("1")
        self.page_button.setStyleSheet(self.buttonStyle())
        self.page_button.setFixedSize(40, 30)
        self.page_button.pageChanged.connect(self.cyclePages)

        self.page_menu = QMenu(self)
        self.page_menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; }")
        self.page_button.setMenu(self.page_menu)
        self.page_menu.aboutToShow.connect(self.refreshPageButtonMenu)
        page_control_layout.addWidget(self.page_button)

        self.add_page_btn = QPushButton("+")
        self.add_page_btn.setStyleSheet(self.buttonStyle())
        self.add_page_btn.setFixedSize(30, 30)
        self.add_page_btn.clicked.connect(self.addNewPage)
        page_control_layout.addWidget(self.add_page_btn)

        self.remove_page_btn = QPushButton("-")
        self.remove_page_btn.setStyleSheet(self.buttonStyle())
        self.remove_page_btn.setFixedSize(30, 30)
        self.remove_page_btn.clicked.connect(self.removePage)
        page_control_layout.addWidget(self.remove_page_btn)

        toolbar_layout.addWidget(page_control_widget, alignment=Qt.AlignLeft)

        self.undo_button = QPushButton()
        self.undo_button.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20))
        self.undo_button.setStyleSheet(self.buttonStyleMini())
        self.undo_button.setFixedSize(30, 30)
        self.undo_button.clicked.connect(self.undo)
        toolbar_layout.addWidget(self.undo_button, alignment=Qt.AlignLeft)

        self.redo_button = QPushButton()
        self.redo_button.setIcon(create_svg_icon(SVG_REDO_ICON, size=20))
        self.redo_button.setStyleSheet(self.buttonStyleMini())
        self.redo_button.setFixedSize(30, 30)
        self.redo_button.clicked.connect(self.redo)
        toolbar_layout.addWidget(self.redo_button, alignment=Qt.AlignLeft)

        self.pen_style_combo = QComboBox()
        self.pen_style_combo.addItems([name for name, _ in self.TOOL_ORDER])
        self.pen_style_combo.setStyleSheet("""
            QComboBox { background-color: transparent; color: white; border: 2px solid #555; border-radius: 8px; padding: 5px 10px; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView { background-color: #444; color: white; selection-background-color: #666; }
        """)
        self.pen_style_combo.setFixedSize(155, 30)
        self.pen_style_combo.currentIndexChanged.connect(self.changePenStyle)
        toolbar_layout.addWidget(self.pen_style_combo, alignment=Qt.AlignLeft)

        self.nav_button = NavigationModeButton(self)
        self.nav_button.rightClicked.connect(self.openResolutionDialog)
        toolbar_layout.addWidget(self.nav_button, alignment=Qt.AlignLeft)

        # S butonu kaldırıldı

        # G butonu (sadece sol tık ile aç/kapa, sağ tık ile menü)
        self.g_button = RightClickButton("G")
        self.g_button.setFixedSize(35, 30)
        self.g_button.setToolTip("Referans görseli tüm sayfalarda göster/gizle (sağ tık: ayarlar)")
        self.g_button.setStyleSheet("""
            QPushButton { background-color: transparent; color: white; font-weight: bold; font-size: 14px; border: 2px solid #555; border-radius: 8px; }
            QPushButton:hover { background-color: #444; color: white; }
        """)
        self.g_button.clicked.connect(self.toggle_global_reference)
        self.g_button.rightClicked.connect(self.showReferenceTransparencyMenu)  # Sağ tık menü
        toolbar_layout.addWidget(self.g_button, alignment=Qt.AlignLeft)

        self.mix_angle_button = MixAngleButton(f"Mix {self.mix_angle}°")
        self.mix_angle_button.setStyleSheet(self.buttonStyle())
        self.mix_angle_button.setFixedSize(70, 30)
        self.mix_angle_button.deltaChanged.connect(self.changeMixAngle)

        self.mix_angle_menu = QMenu(self)
        self.mix_angle_menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; }")
        for angle in range(0, 361, 10):
            if angle == 360:
                angle = 0
            act = self.mix_angle_menu.addAction(f"{angle}°")
            act.triggered.connect(lambda checked, a=angle: self.setMixAngle(a))
            if angle == 0:
                self.mix_angle_menu.addSeparator()
        self.mix_angle_button.setMenu(self.mix_angle_menu)
        self.mix_angle_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mix_angle_button.customContextMenuRequested.connect(self.showMixTypeMenu)
        toolbar_layout.addWidget(self.mix_angle_button, alignment=Qt.AlignLeft)

        self.color_button = QPushButton(f"Color ({len(self.mix_colors)})")
        self.color_button.setStyleSheet(self.buttonStyle())
        self.color_button.setFixedSize(80, 30)
        self.color_menu = QMenu()
        self.color_menu.setStyleSheet("""
            QMenu { background-color: #333; color: white; border: 1px solid #555; padding: 5px; }
            QMenu::item:selected { background-color: #444; }
        """)
        self.updateColorMenu()
        self.color_button.setMenu(self.color_menu)
        toolbar_layout.addWidget(self.color_button, alignment=Qt.AlignLeft)

        self.eraser_button = QPushButton("Eraser")
        self.eraser_button.setStyleSheet(self.buttonStylePressure(self.eraser_mode))
        self.eraser_button.setFixedSize(70, 30)
        self.eraser_button.clicked.connect(self.toggleEraser)
        self.eraser_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.eraser_button.customContextMenuRequested.connect(self.changeBackgroundColor)
        toolbar_layout.addWidget(self.eraser_button, alignment=Qt.AlignLeft)

        self.radius_button = WheelButton(f"R: {self.pen_radius}", parent=self)
        self.radius_button.setStyleSheet(self.buttonStyle())
        self.radius_button.setFixedSize(60, 30)
        self.radius_button.clicked.connect(self.showRadiusMenu)
        toolbar_layout.addWidget(self.radius_button, alignment=Qt.AlignLeft)

        self.layer_button = QPushButton("Çizim")
        self.layer_button.setStyleSheet(self.buttonStyle())
        self.layer_button.setFixedSize(80, 30)
        self.layer_button.clicked.connect(self.toggleLayerPanel)
        self.layer_button.setToolTip("Katman panelini aç / kapat")
        icon = create_svg_icon(SVG_LAYER_DRAWING, 16)
        self.layer_button.setIcon(icon)
        toolbar_layout.addWidget(self.layer_button, alignment=Qt.AlignLeft)

        self.always_top_btn = QPushButton("#")
        self.always_top_btn.setFixedSize(40, 30)
        self.always_top_btn.setStyleSheet(self.buttonStylePressure(self.always_top_mode))
        self.always_top_btn.setToolTip("Seçili Olmayan Katmanları Üstte Tut")
        self.always_top_btn.clicked.connect(self.toggleAlwaysTop)
        toolbar_layout.addWidget(self.always_top_btn, alignment=Qt.AlignLeft)
        self.select_button = QPushButton("S")
        self.select_button.setFixedSize(40, 30)
        self.select_button.setStyleSheet(self.buttonStylePressure(False))
        self.select_button.setToolTip("S modu: piksel seçimi  (A modu ile aynı anda açık olamaz)\n"
                                      "Sürükle: serbest seçim  •  Shift+sürükle: dikdörtgen\n"
                                      "G: taşı  •  S: büyüt/küçült  •  R: döndür  (X / Y: eksen kısıtı)\n"
                                      "D: seçimi başka kareye kopyala  •  Ctrl+D: ara kareleri otomatik oluştur\n"
                                      "Delete: sil  •  Esc: iptal")
        self.select_button.clicked.connect(lambda: self.setEditMode('s'))
        toolbar_layout.addWidget(self.select_button, alignment=Qt.AlignLeft)
        self.point_button = QPushButton("A")
        self.point_button.setFixedSize(40, 30)
        self.point_button.setStyleSheet(self.buttonStylePressure(False))
        self.point_button.setToolTip("A modu: nokta düzenleme  (S modu ile aynı anda açık olamaz)\n"
                                     "Çizimler köşe noktalarıyla görünür. Tıkla: seç  •  Shift: çoklu seçim\n"
                                     "Boşlukta sürükle: kutuyla seç\n"
                                     "G: taşı  •  S: büyüt/küçült  •  R: döndür  (X / Y: eksen kısıtı)\n"
                                     "D: seçili çizgileri başka kareye kopyala  •  Ctrl+D: ara kareleri otomatik oluştur\n"
                                     "Delete: çizgiyi sil  •  Esc: iptal")
        self.point_button.clicked.connect(lambda: self.setEditMode('a'))
        toolbar_layout.addWidget(self.point_button, alignment=Qt.AlignLeft)

        self.lazy_mouse_button = LazyMouseButton(self)
        self.lazy_mouse_button.setFixedSize(33, 30)
        self.lazy_mouse_button.setStyleSheet(self.buttonStylePressure(self.lazy_mouse_enabled))
        self.lazy_mouse_button.setToolTip("Lazy Mouse: Yavaşlatılmış fare (Blender tarzı)\nVarsayılan: R=30, H=15")
        self.lazy_mouse_button.clicked.connect(self.toggleLazyMouse)
        self.lazy_mouse_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lazy_mouse_button.customContextMenuRequested.connect(self.showLazyMouseMenu)
        toolbar_layout.addWidget(self.lazy_mouse_button, alignment=Qt.AlignLeft)

        self.pressure_button = RightClickButton("/", self)
        self.pressure_button.setStyleSheet(self.buttonStylePressure(self.pen_pressure_enabled))
        self.pressure_button.setFixedSize(30, 30)
        self.pressure_button.setToolTip("Sol: Basınç hassasiyeti")
        self.pressure_button.clicked.connect(self.togglePressure)
        toolbar_layout.addWidget(self.pressure_button, alignment=Qt.AlignLeft)

        self.mirror_button = MirrorControlButton("» «")
        self.mirror_button.setStyleSheet(self.buttonStylePressure(self.mirror_mode))
        self.mirror_button.setFixedSize(50, 30)
        self.mirror_button.leftClicked.connect(lambda: self.toggleMirrorMode('vertical'))
        self.mirror_button.rightClicked.connect(lambda: self.toggleMirrorMode('horizontal'))
        toolbar_layout.addWidget(self.mirror_button, alignment=Qt.AlignLeft)

        toolbar_layout.addStretch()

        self.export_button = QPushButton("Export")
        self.export_button.setStyleSheet(self.buttonStyle())
        self.export_button.setFixedSize(90, 30)
        self.export_button.clicked.connect(self.exportFile)
        self.export_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.export_button.customContextMenuRequested.connect(self.showExportMenu)
        toolbar_layout.addWidget(self.export_button, alignment=Qt.AlignRight)

        self.drawing_button = QPushButton("Drawing")
        self.drawing_button.setStyleSheet(self.buttonStyle())
        self.drawing_button.setFixedSize(90, 30)
        self.drawing_button.clicked.connect(self.triggerCoreSwitcher)
        toolbar_layout.addWidget(self.drawing_button, alignment=Qt.AlignRight)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(toolbar_frame)

        self.drawing_area = DrawingArea(self)

        # Katman paneli (sağ) + tuval
        self.layer_panel = LayerPanel(self.drawing_area, self)
        self.layer_panel.setVisible(QSettings("kavram", "DrawingEditor").value("layerPanelVisible", True, type=bool))
        middle = QHBoxLayout()
        middle.setContentsMargins(0, 0, 0, 0)
        middle.setSpacing(0)
        middle.addWidget(self.drawing_area, 1)
        middle.addWidget(self.layer_panel)
        main_layout.addLayout(middle, 1)

        # Animasyon: soğan zarı + oynatma + zaman çizelgesi (altta)
        self.anim = AnimationController(self)
        self.timeline = TimelinePanel(self, self.anim)
        main_layout.addWidget(self.timeline)
        self.setLayout(main_layout)
        self.drawing_area.layersChanged.connect(self.onLayersChanged)

        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self.redo)
        
        QShortcut(QKeySequence("Ctrl+Right"), self, self.goNextPage)
        QShortcut(QKeySequence("Ctrl+Left"), self, self.goPrevPage)
        QShortcut(QKeySequence("Ctrl+Shift+Right"), self, self.duplicateToNextPage)
        QShortcut(QKeySequence("Ctrl+Shift+Left"), self, self.duplicateToPrevPage)

        # Animasyon kısayolları
        QShortcut(QKeySequence("Ctrl+Space"), self, self.anim.toggle_play)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, lambda: self.timeline.onion_btn.toggle())
        self.esc_shortcut = QShortcut(QKeySequence("Esc"), self, self.onEscapePressed)
        self.esc_shortcut.setEnabled(False)            # yalnızca oynatma / S veya A modunda etkin
        self.anim.playStateChanged.connect(lambda _p: self.updateEscShortcut())

        # S ve A modu ortak kısayolları (yalnız bir mod açıkken etkin; metin yazarken tuşlar çalınmaz)
        self.select_shortcuts = []
        for seq, fn in (("G", lambda: self.drawing_area.modeStartOp('g')),
                        ("S", lambda: self.drawing_area.modeStartOp('s')),
                        ("R", lambda: self.drawing_area.modeStartOp('r')),
                        ("D", lambda: keyframe_copy(self)),
                        ("Ctrl+D", lambda: keyframe_tween(self)),
                        ("X", lambda: self.drawing_area.modeAxis('x')),
                        ("Y", lambda: self.drawing_area.modeAxis('y')),
                        ("Delete", lambda: self.drawing_area.modeDelete())):
            sc = QShortcut(QKeySequence(seq), self, fn)
            sc.setEnabled(False)
            self.select_shortcuts.append(sc)

    def openResolutionDialog(self):
        """Nav butonuna sağ tık ile çözünürlük ayarlarını açar."""
        if len(self.pages_data) > 1 or self.is_project_modified:
            QMessageBox.warning(self, "Uyarı", "Çözünürlük yalnızca boş ve yeni bir projede değiştirilebilir.\n\nYeni, boş bir proje açın.")
            return

        dialog = AspectRatioDialog(self)
        if dialog.exec_():
            settings = dialog.getSettings()
            new_w = settings["width"]
            new_h = settings["height"]
            self.applyNewResolution(new_w, new_h)

    def applyNewResolution(self, w, h):
        """Tuval boyutunu değiştirir; tüm karelerin tüm katmanlarını yeni boyuta uyarlar."""
        if w == self.canvas_width and h == self.canvas_height:
            return

        self.saveCurrentPageData()

        old_w = self.canvas_width
        old_h = self.canvas_height

        self.canvas_width = w
        self.canvas_height = h

        st = self.drawing_area.layer_stack
        meta = st.export_meta()
        for i in range(len(self.pages_data)):
            paths = [layer_path(self.drawing_cache_dir, i, m["id"]) for m in meta]
            paths.append(os.path.join(self.drawing_cache_dir, f"s{i + 1}.png"))      # eski tek parça dosya
            for path in paths:
                if os.path.isfile(path):
                    img = QImage(path)
                    if not img.isNull():
                        fit_to_canvas(img, w, h).save(path, "PNG")
        st.resize(w, h)

        self.drawing_area.mirror_line_x = w // 2
        self.drawing_area.mirror_line_y = h // 2

        scale_x = w / old_w
        scale_y = h / old_h
        for element in self.drawing_area.drawing_elements:
            if element["type"] == "image":
                element["position"][0] = int(element["position"][0] * scale_x)
                element["position"][1] = int(element["position"][1] * scale_y)
                element["current_width"] = int(element["current_width"] * scale_x)
                element["current_height"] = int(element["current_height"] * scale_y)
                element["original_width"] = int(element["original_width"] * scale_x)
                element["original_height"] = int(element["original_height"] * scale_y)

        self.loadPageData(self.current_page_index, save_current=False)
        if hasattr(self, "timeline"):
            self.timeline.schedule_refresh()

        QTimer.singleShot(100, self.fitCanvasToView)

    def importReferenceImage(self):
        """File butonuna sağ tık: referans görsel ekle (sadece 1)"""
        path, _ = _fm.get_open_file_name(self, "Referans Görsel Seç", "",
                                              "Görseller (*.png *.jpg *.jpeg *.bmp *.gif *.webp)", editor="Drawing", double_click="select")
        if path:
            img = QImage(path)
            if not img.isNull():
                self.drawing_area.startReferencePlacement(img)
                self.is_project_modified = True
                # Referans PNF'ye kaydedilmez, sadece DrawingArea'da tutulur

    def toggle_global_reference(self):
        """G butonu sol tık: referans görünürlüğünü aç/kapa"""
        self.global_reference_visible = not self.global_reference_visible
        self.g_button.setStyleSheet(self.buttonStylePressure(self.global_reference_visible))
        self.drawing_area.update()

    def showReferenceTransparencyMenu(self, pos):
        """G butonu sağ tık: saydamlık ve katman konumu menüsü"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #252525;
                color: white;
                border: 1px solid #555;
                padding: 8px;
            }
        """)

        # Saydamlık kaydırıcı
        container = QWidget(menu)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        title = QLabel("Referans Saydamlığı")
        title.setStyleSheet("color: #eee; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        value_label = QLabel()
        value_label.setStyleSheet("color: #aaa; font-size: 10px;")
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)

        slider = QSlider(Qt.Vertical, container)
        slider.setRange(0, 95)
        slider.setValue(int(self.reference_transparency))
        slider.setFixedHeight(150)
        slider.setToolTip("0 = opak, 95 = neredeyse tamamen saydam")
        slider.setStyleSheet("""
            QSlider::groove:vertical {
                width: 6px; background: #444; border-radius: 3px;
            }
            QSlider::handle:vertical {
                width: 16px; height: 16px; margin: 0 -5px;
                background: #aaa; border: 1px solid #666; border-radius: 8px;
            }
        """)
        layout.addWidget(slider, alignment=Qt.AlignHCenter)

        def update_value(value):
            value_label.setText(f"{int(value)}% saydam")
            self.setReferenceTransparency(value)

        slider.valueChanged.connect(update_value)
        update_value(slider.value())

        slider_action = QWidgetAction(menu)
        slider_action.setDefaultWidget(container)
        menu.addAction(slider_action)

        # Katman konumu butonları (sadece Alt ve Üst)
        button_widget = QWidget(menu)
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)

        btn_top = QPushButton("Üst")
        btn_top.setCheckable(True)
        btn_bottom = QPushButton("Alt")
        btn_bottom.setCheckable(True)

        # Varsayılan olarak "Üst" seçili
        btn_top.setChecked(True)

        def set_position(pos_val):
            self.drawing_area.reference_layer_position = pos_val
            btn_top.setChecked(pos_val == 0)
            btn_bottom.setChecked(pos_val == 1)
            self.drawing_area.update()

        btn_top.clicked.connect(lambda: set_position(0))
        btn_bottom.clicked.connect(lambda: set_position(1))

        button_layout.addWidget(btn_top)
        button_layout.addWidget(btn_bottom)

        button_action = QWidgetAction(menu)
        button_action.setDefaultWidget(button_widget)
        menu.addAction(button_action)

        menu.exec_(self.g_button.mapToGlobal(QPoint(0, self.g_button.height())))

    def setReferenceTransparency(self, value):
        self.reference_transparency = max(0, min(95, int(value)))
        settings = QSettings("kavram", "DrawingEditor")
        settings.setValue("referenceTransparency", self.reference_transparency)
        self.drawing_area.update()

    # Aşağıdaki metotlar artık kullanılmıyor (referans kaydetme/yükleme kaldırıldı)
    def updateCurrentPageReferenceData(self):
        pass  # Referans kaydedilmez

    def loadPageData(self, index, save_current=True, elements=None):
        if 0 <= index < len(self.pages_data):
            if save_current:
                self.saveCurrentPageData()

            self.current_page_index = index
            page_info = self.pages_data[index]

            self.background_color = page_info["background"]

            area = self.drawing_area
            area.undo_stack.clear()
            area.redo_stack.clear()
            area.clearImageCache()
            area.pageChangedReset()

            if elements is not None:
                area.drawing_elements = elements
            else:
                elements_file = os.path.join(self.drawing_cache_dir, f"s{index + 1}_elements.json")
                try:
                    with open(elements_file, 'r', encoding='utf-8') as f:
                        area.drawing_elements = json.load(f)
                except Exception:
                    area.drawing_elements = []
            area.syncPaintedCount()

            # Katman görüntüleri (her katman ayrı dosya; eski tek parça dosya varsa 'Çizim' katmanına alınır)
            area.loadLayersFromCache(self.drawing_cache_dir, index)
            area.layersChanged.emit()
            area.update()

            self.page_button.setText(str(self.current_page_index + 1))

            # Referans yüklenmez (sadece mevcut DrawingArea'daki referans korunur)
            area.placing_reference = False

            if hasattr(self, "anim"):
                self.anim.on_page_changed()
            if hasattr(self, "timeline"):
                self.timeline.sync_current()

    def flushCurrentPageToCache(self):
        """Geçerli kareyi önbelleğe yazar (katman PNG'leri + kayıtlar). Durumu/undo'yu TEMİZLEMEZ.
        Oynatma, dışa aktarma ve proje kaydı bunu kullanır."""
        if 0 <= self.current_page_index < len(self.pages_data):
            try:
                self.drawing_area.saveLayersToCache(self.drawing_cache_dir, self.current_page_index)
                elements_file = os.path.join(self.drawing_cache_dir, f"s{self.current_page_index + 1}_elements.json")
                with open(elements_file, 'w', encoding='utf-8') as f:
                    json.dump(self.drawing_area.drawing_elements, f)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Sayfa kaydedilemedi: {e}")
                return False
            self.pages_data[self.current_page_index]["background"] = self.background_color
        return True

    def saveCurrentPageData(self):
        if 0 <= self.current_page_index < len(self.pages_data):
            if not self.flushCurrentPageToCache():
                return
            self.drawing_area.drawing_elements.clear()
            self.drawing_area.syncPaintedCount()
            self.drawing_area.undo_stack.clear()
            self.drawing_area.redo_stack.clear()

    def showExportMenu(self, pos):
        """Export butonuna sağ tık menüsü"""
        menu = ExportMenu(self, default_callback=lambda: self.setFpsAndExport(self.current_export_fps))
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
        
        save_action = menu.addAction(f"MKV Olarak Kaydet ({self.current_export_fps} fps)")
        font = save_action.font()
        font.setBold(True)
        save_action.setFont(font)
        menu.setDefaultAction(save_action)
        save_action.triggered.connect(lambda: self.setFpsAndExport(self.current_export_fps))
        
        menu.addSeparator()
        
        fps_options = [3, 6, 12, 24, 25, 30, 60]
        
        for fps in fps_options:
            text = f"{fps} fps" if fps == self.current_export_fps else str(fps)
            action = menu.addAction(text)
            action.triggered.connect(lambda checked, f=fps: self.setFpsAndExport(f))
            
        menu.exec_(self.export_button.mapToGlobal(pos))

    def setFpsAndExport(self, fps):
        self.current_export_fps = fps
        settings = QSettings("kavram", "DrawingEditor")
        settings.setValue("exportFPS", fps)
        self.promptMKVExport()

    def promptMKVExport(self):
        """Eski ad korunuyor: artık çok biçimli dışa aktarma penceresini açar."""
        start_export(self, "mkv")

    def goNextPage(self):
        if len(self.pages_data) > 0:
            new_idx = (self.current_page_index + 1) % len(self.pages_data)
            self.loadPageData(new_idx)

    def goPrevPage(self):
        if len(self.pages_data) > 0:
            new_idx = (self.current_page_index - 1) % len(self.pages_data)
            self.loadPageData(new_idx)

    def duplicateToNextPage(self):
        elements_copy = copy.deepcopy(self.drawing_area.drawing_elements)
        self.saveCurrentPageData()
        bg_color = QColor(self.background_color)
        cur = self.current_page_index
        new_idx = cur + 1
        if new_idx >= len(self.pages_data):
            if len(self.pages_data) >= self.max_pages:
                QMessageBox.warning(self, "Uyarı", f"Sayfa sınırı ({self.max_pages}) aşıldı.")
                return
            self.pages_data.append({"background": bg_color, "hold": 1})
        else:
            self.pages_data[new_idx]["background"] = bg_color
        copy_page_files(self.drawing_cache_dir, cur + 1, new_idx + 1)
        self.refreshPageButtonMenu()
        self.loadPageData(new_idx, save_current=False, elements=elements_copy)
        self.is_project_modified = True

    def duplicateToPrevPage(self):
        if self.current_page_index <= 0:
            return
        elements_copy = copy.deepcopy(self.drawing_area.drawing_elements)
        self.saveCurrentPageData()
        bg_color = QColor(self.background_color)
        cur = self.current_page_index
        new_idx = cur - 1
        self.pages_data[new_idx]["background"] = bg_color
        copy_page_files(self.drawing_cache_dir, cur + 1, new_idx + 1)
        self.refreshPageButtonMenu()
        self.loadPageData(new_idx, save_current=False, elements=elements_copy)
        self.is_project_modified = True

    def resetView(self):
        self.drawing_area.zoom_factor = 1.0
        self.drawing_area.view_offset = QPoint(0, 0)
        self.drawing_area.update()

    def toggleAlwaysTop(self):
        self.always_top_mode = not self.always_top_mode
        self.always_top_btn.setStyleSheet(self.buttonStylePressure(self.always_top_mode))
        self.drawing_area.force_active_layer_bottom = self.always_top_mode
        self.drawing_area.update()      # yalnızca yeniden boyama: tekrar oynatma yok

    def toggleLazyMouse(self):
        self.lazy_mouse_enabled = not self.lazy_mouse_enabled
        self.lazy_mouse_button.setStyleSheet(self.buttonStylePressure(self.lazy_mouse_enabled))
        self.updateButtonStyles()
        self.saveLazyMouseSettings()
    
    def showLazyMouseMenu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #333; color: white; border: 1px solid #555; padding: 5px; }
            QMenu::item:selected { background-color: #555; }
        """)
        toggle_action = menu.addAction("✓ Aktif" if self.lazy_mouse_enabled else "Pasif")
        toggle_action.triggered.connect(self.toggleLazyMouse)
        menu.addSeparator()
        radius_menu = menu.addMenu(f"Yarıçap: {self.lazy_radius}")
        for r in [10, 20, 30, 40, 50, 75, 100, 150, 200]:
            action = radius_menu.addAction(f"{r} px")
            action.triggered.connect(lambda checked, val=r: self.setLazyRadius(val))
        factor_menu = menu.addMenu(f"Hassasiyet: {self.lazy_factor}")
        for f in [5, 10, 15, 20, 30, 50, 75, 100]:
            action = factor_menu.addAction(f"{f}")
            action.triggered.connect(lambda checked, val=f: self.setLazyFactor(val))
        menu.addSeparator()
        reset_action = menu.addAction("Varsayılana Sıfırla")
        reset_action.triggered.connect(self.resetLazyMouseSettings)
        menu.exec_(self.lazy_mouse_button.mapToGlobal(pos))
    
    def setLazyRadius(self, value):
        self.lazy_radius = value
        self.lazy_mouse_button.updateButtonText(self)
        self.lazy_mouse_button.updateToolTip(self)
        self.saveLazyMouseSettings()
    
    def setLazyFactor(self, value):
        self.lazy_factor = value
        self.lazy_mouse_button.updateButtonText(self)
        self.lazy_mouse_button.updateToolTip(self)
        self.saveLazyMouseSettings()
    
    def resetLazyMouseSettings(self):
        self.lazy_radius = 30
        self.lazy_factor = 15
        self.lazy_mouse_button.updateButtonText(self)
        self.lazy_mouse_button.updateToolTip(self)
        self.saveLazyMouseSettings()
    
    def saveLazyMouseSettings(self):
        settings = QSettings("kavram", "DrawingEditor")
        settings.setValue("lazyMouse/enabled", self.lazy_mouse_enabled)
        settings.setValue("lazyMouse/radius", self.lazy_radius)
        settings.setValue("lazyMouse/factor", self.lazy_factor)
    
    def loadLazyMouseSettings(self):
        settings = QSettings("kavram", "DrawingEditor")
        self.lazy_mouse_enabled = settings.value("lazyMouse/enabled", False, type=bool)
        self.lazy_radius = settings.value("lazyMouse/radius", 30, type=int)
        self.lazy_factor = settings.value("lazyMouse/factor", 15, type=int)

    def setEditMode(self, mode):
        """S (piksel seçimi) ve A (nokta düzenleme) modları aynı anda açık kalamaz:
        birine basılınca diğeri otomatik kapanır; açık olana tekrar basılınca o kapanır."""
        area = self.drawing_area
        current = 's' if area.select_active else ('a' if area.point_active else None)
        if mode == current:
            mode = None
        area.setSelectActive(mode == 's')
        area.setPointActive(mode == 'a')
        self.select_button.setStyleSheet(self.buttonStylePressure(mode == 's'))
        self.point_button.setStyleSheet(self.buttonStylePressure(mode == 'a'))
        for sc in self.select_shortcuts:
            sc.setEnabled(mode is not None)
        self.updateEscShortcut()

    def updateEscShortcut(self):
        area = self.drawing_area
        self.esc_shortcut.setEnabled(bool(self.anim.is_playing or area.select_active or area.point_active))

    def onEscapePressed(self):
        if self.anim.is_playing:
            self.anim.stop()
        else:
            self.drawing_area.modeEscape()

    def toggleLayerPanel(self):
        visible = not self.layer_panel.isVisible()
        self.layer_panel.setVisible(visible)
        QSettings("kavram", "DrawingEditor").setValue("layerPanelVisible", visible)

    def onLayersChanged(self):
        """Aktif katman değişince araç çubuğundaki katman düğmesini günceller."""
        layer = self.drawing_area.layer_stack.active
        fm = QFontMetrics(self.layer_button.font())
        self.layer_button.setText(fm.elidedText(layer.name, Qt.ElideRight, 48))
        self.layer_button.setToolTip(f"Aktif katman: {layer.name}  (paneli aç/kapat)")
        icon = create_svg_icon(SVG_LAYER_SKETCH if layer.name == "Eskiz" else SVG_LAYER_DRAWING, 16)
        self.layer_button.setIcon(icon)

    def addNewPage(self):
        if len(self.pages_data) >= self.max_pages:
            QMessageBox.warning(self, "Uyarı", f"Sayfa sınırı ({self.max_pages}) aşıldı.")
            return
        self.saveCurrentPageData()
        self.pages_data.append({"background": self.background_color, "hold": 1})
        new_index = len(self.pages_data) - 1
        self.refreshPageButtonMenu()
        self.loadPageData(new_index, save_current=False)
        self.is_project_modified = True

    def insertBlankPageAfter(self):
        """Geçerli karenin hemen sonrasına boş kare ekler (diğer kareleri kaydırır)."""
        if len(self.pages_data) >= self.max_pages:
            QMessageBox.warning(self, "Uyarı", f"Sayfa sınırı ({self.max_pages}) aşıldı.")
            return
        self.saveCurrentPageData()
        cur = self.current_page_index
        total = len(self.pages_data)
        for i in range(total - 1, cur, -1):
            move_page_files(self.drawing_cache_dir, i + 1, i + 2)
        self.pages_data.insert(cur + 1, {"background": QColor(self.background_color), "hold": 1})
        self.refreshPageButtonMenu()
        self.loadPageData(cur + 1, save_current=False)
        self.is_project_modified = True

    def movePage(self, src, dst):
        """Zaman çizelgesinde sürükle-bırak ile kare sırasını değiştirir."""
        n = len(self.pages_data)
        if not (0 <= src < n and 0 <= dst < n) or src == dst:
            return
        current_page_obj = self.pages_data[self.current_page_index]
        self.saveCurrentPageData()
        order = list(range(1, n + 1))
        order.insert(dst, order.pop(src))
        reorder_page_files(self.drawing_cache_dir, order)
        page = self.pages_data.pop(src)
        self.pages_data.insert(dst, page)
        new_cur = next((i for i, p in enumerate(self.pages_data) if p is current_page_obj), 0)
        self.refreshPageButtonMenu()
        self.loadPageData(new_cur, save_current=False)
        self.is_project_modified = True

    def removePage(self):
        if len(self.pages_data) <= 1:
            QMessageBox.warning(self, "Uyarı", "En az bir sayfa kalmalıdır.")
            return
        reply = QMessageBox.question(self, "Sayfa Sil", "Mevcut sayfayı silmek istiyor musunuz?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            delete_page_files(self.drawing_cache_dir, self.current_page_index + 1)
            for i in range(self.current_page_index, len(self.pages_data) - 1):
                move_page_files(self.drawing_cache_dir, i + 2, i + 1)
            self.pages_data.pop(self.current_page_index)
            if self.current_page_index >= len(self.pages_data):
                self.current_page_index = len(self.pages_data) - 1
            self.drawing_area.undo_stack.clear()
            self.drawing_area.redo_stack.clear()
            self.refreshPageButtonMenu()
            self.loadPageData(self.current_page_index, save_current=False)
            self.is_project_modified = True

    def cyclePages(self, delta):
        new_index = self.current_page_index + delta
        if 0 <= new_index < len(self.pages_data):
            self.loadPageData(new_index)

    def refreshPageButtonMenu(self):
        self.page_menu.clear()
        for i in range(len(self.pages_data)):
            action = self.page_menu.addAction(f"Sayfa {i+1}")
            action.triggered.connect(lambda checked, idx=i: self.loadPageData(idx))
        if hasattr(self, "timeline"):
            self.timeline.schedule_refresh()

    def changeMixAngle(self, delta):
        self.mix_angle = (self.mix_angle + delta) % 360
        self.mix_angle_button.setText(f"Mix {self.mix_angle}°")

    def setMixAngle(self, angle):
        self.mix_angle = angle
        self.mix_angle_button.setText(f"Mix {self.mix_angle}°")

    def showMixTypeMenu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; }")
        menu.addAction("--- Mix Modes ---").setEnabled(False)
        types = [
            ('Random (Rastgele)', 'random'), 
            ('Sequential (Sıralı)', 'sequential'), 
            ('Gradient (Açısal)', 'gradient'), 
            ('Smooth (Pürüzsüz)', 'smooth'), 
            ('Harman (Doku)', 'harman'),
            ('Gradyan Geçiş (Yumuşak)', 'gradient_soft'),
            ('Mermer Efekti (Marble)', 'marble'),
            ('Renk Serpiştirme (Splatter)', 'splatter'),
            ('Dalgalı (Wave)', 'wave'),
            ('Piksel Gürültüsü (Pixel)', 'pixel'),
            ('Sünger (Sponge)', 'sponge'),
            ('Gökkuşağı Dairesel (Radial)', 'radial'),
            ('Puslu (Mist)', 'mist')
        ]
        for label, key in types:
            action = menu.addAction(label)
            action.setCheckable(True)
            if self.mix_mode == key:
                action.setChecked(True)
            action.triggered.connect(lambda checked, k=key: self.setMixMode(k))
        menu.addSeparator()
        menu.addAction(f"--- Active Mix Colors ({len(self.mix_colors)}) ---").setEnabled(False)
        strip_widget = QWidgetAction(menu)
        strip = ColorHistoryStrip(self.mix_colors)
        strip.colorSelected.connect(self.onHistoryColorSelected)
        strip_widget.setDefaultWidget(strip)
        menu.addAction(strip_widget)
        menu.exec_(self.mix_angle_button.mapToGlobal(pos))

    def updateColorMenu(self):
        self.color_menu.clear()
        select_action = self.color_menu.addAction("Select Single Color")
        select_action.triggered.connect(self.changeColor)
        add_action = self.color_menu.addAction("Add Color to Mix (+)")
        add_action.triggered.connect(self.addColorToMix)
        self.color_menu.addSeparator()
        history_label_action = QWidgetAction(self.color_menu)
        history_label = QLabel("  Color History:", self.color_menu)
        history_label.setStyleSheet("color: #aaa; font-weight: bold; padding: 2px 5px;")
        history_label_action.setDefaultWidget(history_label)
        self.color_menu.addAction(history_label_action)
        for i, colors in enumerate(reversed(self.mix_history)):
            action_widget = QWidgetAction(self.color_menu)
            strip = ColorHistoryStrip(colors)
            strip.colorSelected.connect(self.onHistoryColorSelected)
            action_widget.setDefaultWidget(strip)
            self.color_menu.addAction(action_widget)

    def onHistoryColorSelected(self, single_color, mix_colors):
        if single_color:
            self.pen_color = single_color
            self.mix_colors = [single_color]
            self.eraser_mode = False
            self.drawing_area.cancelImagePlacement()
            self.color_button.setText("Color (1)")
            if not self.mix_history or self.mix_history[-1] != [single_color]:
                self.mix_history.append([single_color])
                self.updateColorMenu()
        elif mix_colors:
            self.mix_colors = list(mix_colors)
            self.pen_color = mix_colors[0]
            self.eraser_mode = False
            self.drawing_area.cancelImagePlacement()
            self.color_button.setText(f"Color ({len(self.mix_colors)})")
        self.color_menu.close()
        self.updateButtonStyles()

    def buttonStyle(self):
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 14px; font-weight: bold;
                border: 2px solid #555; border-radius: 8px; padding: 5px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
            QPushButton::menu-indicator { image: none; }
        """

    def buttonStyleMini(self):
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 16px;
                border: 2px solid #555; border-radius: 8px; padding: 5px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

    def buttonStylePressure(self, pressed):
        if pressed:
            return """
                QPushButton {
                    background-color: #555; color: white; font-size: 16px;
                    border: 2px solid #555; border-radius: 8px; padding: 5px;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: transparent; color: white; font-size: 16px;
                    border: 2px solid #555; border-radius: 8px; padding: 5px;
                }
                QPushButton:hover { background-color: #444; }
                QPushButton:pressed { background-color: #666; }
            """

    def importFile(self):
        options = QFileDialog.Options()
        file_filter = "Supported Files (*.pnf *.drawing *.png *.jpg *.jpeg *.bmp *.gif *.webp);;Project Files (*.pnf *.drawing);;Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        file_path, _ = _fm.get_open_file_name(
            self, "Import Drawing or Image", DrawingEditorWindow.DEFAULT_BASE_DIR,
            file_filter,
            options=options
        , editor="Drawing")
        if file_path:
            self.load_image_from_path(file_path)

    def saveProject(self):
        if self.current_file_path:
            self._save_to_path(self.current_file_path)
            _fm.notify_saved(self)
        else:
            self.exportFile()

    def _save_to_path(self, path):
        # Not: durumu/undo'yu temizlemeden yalnız önbelleğe yazar
        self.flushCurrentPageToCache()

        st = self.drawing_area.layer_stack
        meta = st.export_meta()
        project_data = []
        for i, page in enumerate(self.pages_data):
            bg_color = page["background"]
            bg_list = [bg_color.red(), bg_color.green(), bg_color.blue(), bg_color.alpha()]

            layers_b64 = {}
            for m in meta:
                lp = layer_path(self.drawing_cache_dir, i, m["id"])
                if os.path.exists(lp):
                    with open(lp, 'rb') as img_f:
                        layers_b64[str(m["id"])] = base64.b64encode(img_f.read()).decode('utf-8')

            legacy_png = os.path.join(self.drawing_cache_dir, f"s{i + 1}.png")
            legacy_b64 = ""
            if not layers_b64 and os.path.exists(legacy_png):
                with open(legacy_png, 'rb') as img_f:
                    legacy_b64 = base64.b64encode(img_f.read()).decode('utf-8')

            elements_file = os.path.join(self.drawing_cache_dir, f"s{i + 1}_elements.json")
            elements_data = []
            if os.path.exists(elements_file):
                with open(elements_file, 'r', encoding='utf-8') as f:
                    elements_data = json.load(f)

            page_dict = {
                "elements": elements_data,
                "image_data": legacy_b64,
                "layers": layers_b64,
                "hold": max(1, int(page.get("hold", 1))),
                "background": bg_list,
                "resolution": {"width": self.canvas_width, "height": self.canvas_height}
            }
            project_data.append(page_dict)

        full_data = {
            "version": 2,
            "pages": project_data,
            "layers_meta": meta,
            "active_layer": st.active.id,
            "global_reference_visible": self.global_reference_visible,
            "reference_transparency": self.reference_transparency
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(full_data, f)

        self.current_file_path = path
        self.is_project_modified = False

    def exportFile(self):
        self.flushCurrentPageToCache()

        QDir().mkpath(DrawingEditorWindow.DEFAULT_BASE_DIR)
        options = QFileDialog.Options()

        file_filter = "Project Native Format (*.pnf);;PDF Files (*.pdf);;PNG Files (*.png);;Drawing Files (*.drawing);;JPEG Files (*.jpg *.jpeg);;BMP Files (*.bmp);;All Files (*)"
        default_filter = "Project Native Format (*.pnf)"

        file_path, selected_filter = _fm.get_save_file_name(
            self, "Projeyi Dışa Aktar", self.current_file_path or DrawingEditorWindow.DEFAULT_BASE_DIR,
            file_filter,
            default_filter,
            options=options
        , editor="Drawing")

        if not file_path:
            return

        if selected_filter.startswith("Project Native Format") or file_path.lower().endswith(".pnf"):
            if not file_path.lower().endswith(".pnf"):
                file_path += ".pnf"
            try:
                self._save_to_path(file_path)
                _fm.notify_saved(self)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya kaydedilemedi: {e}")

        elif selected_filter == "Drawing Files (*.drawing)" or file_path.lower().endswith(".drawing"):
            if not file_path.lower().endswith(".drawing"):
                file_path += ".drawing"
            try:
                payload = {"version": 2,
                           "resolution": {"width": self.canvas_width, "height": self.canvas_height},
                           "elements": self.drawing_area.drawing_elements}
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, indent=4)
                _fm.notify_saved(self)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya kaydedilemedi: {e}")

        elif selected_filter == "PDF Files (*.pdf)" or file_path.lower().endswith(".pdf"):
            if not file_path.lower().endswith(".pdf"):
                file_path += ".pdf"
            try:
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(file_path)
                painter = QPainter(printer)
                try:
                    st = self.drawing_area.layer_stack
                    meta = st.export_meta()
                    for i, page_data in enumerate(self.pages_data):
                        if i > 0:
                            printer.newPage()
                        bg = QColor(page_data.get("background", QColor("#333")))
                        image = composite_page(self.drawing_cache_dir, i, meta, st.w, st.h, bg)

                        rect = painter.viewport()
                        size = image.size()
                        size.scale(rect.size(), Qt.KeepAspectRatio)
                        painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
                        painter.setWindow(image.rect())
                        painter.drawImage(0, 0, image)

                    painter.end()
                    _fm.notify_saved(self)
                except Exception as e:
                    painter.end()
                    raise e
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"PDF dışa aktarılamadı: {e}")
        else:
            if selected_filter == "JPEG Files (*.jpg *.jpeg)":
                if not file_path.lower().endswith((".jpg", ".jpeg")):
                    file_path += ".jpg"
                file_format = "JPEG"
            elif selected_filter == "BMP Files (*.bmp)":
                if not file_path.lower().endswith(".bmp"):
                    file_path += ".bmp"
                file_format = "BMP"
            else:
                if not file_path.lower().endswith(".png"):
                    file_path += ".png"
                file_format = "PNG"

            if file_format == "PNG":
                export_img = self.drawing_area.flattenCurrent(None)          # saydam arka plan
            else:
                export_img = self.drawing_area.flattenCurrent(QColor(self.background_color)).convertToFormat(QImage.Format_RGB32)
            if not export_img.save(file_path, file_format):
                QMessageBox.critical(self, "Hata", "Çizim dışa aktarılamadı.")
            else:
                _fm.notify_saved(self)

    def load_image_from_path(self, file_path):
        if file_path.lower().endswith(".pnf"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, list):
                    project_data = data
                    global_ref_vis = True
                else:
                    project_data = data.get("pages", [])
                    global_ref_vis = data.get("global_reference_visible", True)
                    if "reference_transparency" in data:
                        self.reference_transparency = max(0, min(95, int(data.get("reference_transparency", self.reference_transparency))))
                        QSettings("kavram", "DrawingEditor").setValue("referenceTransparency", self.reference_transparency)

                self.global_reference_visible = global_ref_vis
                self.g_button.setStyleSheet(self.buttonStylePressure(self.global_reference_visible))

                is_empty_project = (len(self.pages_data) == 1 and len(self.drawing_area.drawing_elements) == 0)

                if is_empty_project:
                    self.clearDrawingCache()
                    self.pages_data.clear()
                    start_index = 0
                else:
                    self.saveCurrentPageData()
                    start_index = len(self.pages_data)

                file_layers_meta = data.get("layers_meta") if isinstance(data, dict) else None

                if isinstance(project_data, list) and len(project_data) > 0:
                    if "resolution" in project_data[0]:
                        res = project_data[0]["resolution"]
                        self.applyNewResolution(res.get("width", 1100), res.get("height", 600))

                    # Boş projeye açılıyorsa dosyanın katman yapısı aynen benimsenir
                    adopt_layers = bool(file_layers_meta) and is_empty_project
                    if adopt_layers:
                        self.drawing_area.layer_stack.import_meta(file_layers_meta, data.get("active_layer"))
                    current_ids = {str(m["id"]) for m in self.drawing_area.layer_stack.export_meta()}

                    for i, page in enumerate(project_data):
                        bg_list = page.get("background", [51, 51, 51, 255])
                        bg_color = QColor(bg_list[0], bg_list[1], bg_list[2], bg_list[3])
                        
                        page_idx = start_index + i
                        self.pages_data.append({"background": bg_color, "hold": max(1, int(page.get("hold", 1)))})
                        
                        new_base = os.path.join(self.drawing_cache_dir, f"s{page_idx + 1}")

                        page_layers = page.get("layers") or {}
                        if page_layers and set(page_layers.keys()) <= current_ids:
                            for lid, b64 in page_layers.items():
                                try:
                                    with open(layer_path(self.drawing_cache_dir, page_idx, int(lid)), 'wb') as img_f:
                                        img_f.write(base64.b64decode(b64))
                                except Exception:
                                    pass
                        elif page_layers:
                            # Katman yapısı uyuşmuyor (projeye ekleme): sayfayı düzleştirip 'Çizim' katmanına al
                            try:
                                items = []
                                for fm in (file_layers_meta or []):
                                    b64 = page_layers.get(str(fm["id"]))
                                    if b64:
                                        li = QImage()
                                        li.loadFromData(base64.b64decode(b64), "PNG")
                                        items.append((li, fm.get("visible", True), float(fm.get("opacity", 1.0)), fm.get("blend", "normal")))
                                flat = composite_images(items, self.canvas_width, self.canvas_height, None)
                                flat.save(f"{new_base}.png", "PNG")
                            except Exception:
                                pass
                        else:
                            b64_image = page.get("image_data", "")
                            if b64_image:
                                try:
                                    with open(f"{new_base}.png", 'wb') as img_f:
                                        img_f.write(base64.b64decode(b64_image))
                                except Exception:
                                    pass
                        
                        elements_data = page.get("elements", [])
                        elements_file = f"{new_base}_elements.json"
                        with open(elements_file, 'w', encoding='utf-8') as ef:
                            json.dump(elements_data, ef, indent=4)

                if len(self.pages_data) > 0:
                    self.refreshPageButtonMenu()
                    self.loadPageData(start_index, save_current=False)
                    self.drawing_area.layersChanged.emit()

                    if is_empty_project:
                        self.current_file_path = file_path
                        self.setWindowTitle(f"Kavram - {os.path.basename(file_path)}")
                        self.is_project_modified = False
                        
                    QTimer.singleShot(150, self.fitCanvasToView)

            except Exception as e:
                QMessageBox.critical(self, "Hata", f"PNF dosyası yüklenemedi: {e}")

        elif file_path.lower().endswith(".drawing"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                elems = data.get("elements", []) if isinstance(data, dict) else data
                self.drawing_area.saveStateForUndo()
                self.drawing_area.drawing_elements.extend(elems)
                self.drawing_area.updateImageFromElements()      # yalnızca yeni kayıtlar çizilir
                self.is_project_modified = True
            except Exception as e:
                QMessageBox.critical(self, "Hata", f".drawing dosyası yüklenemedi: {e}")
        else:
            imported_image = QImage(file_path)
            if imported_image.isNull():
                QMessageBox.critical(self, "Hata", "Could not load image.")
                return
            imported_image = imported_image.convertToFormat(QImage.Format_ARGB32)
            extracted_colors = []
            small_thumb = imported_image.scaled(50, 50, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            for y in range(0, 50, 10):
                for x in range(0, 50, 10):
                    c = small_thumb.pixelColor(x, y)
                    is_unique = True
                    for ex in extracted_colors:
                        if abs(ex.red() - c.red()) < 30 and abs(ex.green() - c.green()) < 30 and abs(ex.blue() - c.blue()) < 30:
                            is_unique = False
                            break
                    if is_unique:
                        extracted_colors.append(c)
                    if len(extracted_colors) >= 8:
                        break
                if len(extracted_colors) >= 8:
                    break
            if extracted_colors:
                self.mix_history.append(extracted_colors)
                self.updateColorMenu()
            self.placing_image = True
            self.text_mode = False
            self.eraser_mode = False
            self.drawing_area.text_input_widget.hide()
            self.drawing_area.startImagePlacement(imported_image)
            self.updateButtonStyles()

    def toggleEraser(self):
        self.eraser_mode = not self.eraser_mode
        self.text_mode = False
        self.drawing_area.cancelImagePlacement()

        if self.eraser_mode:
            self.normal_tool_index = self.current_tool_index
            self.current_tool_index = self.eraser_tool_index

            if self.eraser_tool_index == 4:
                self.pen_radius = 1
                self.solid_fill_mode = True
            else:
                self.pen_radius = self.tool_radiuses.get(self.eraser_tool_index, 15)
                self.solid_fill_mode = (self.eraser_tool_index == 4)

            self.pen_style_combo.blockSignals(True)
            combo_idx = -1
            for i, (name, logic_id) in enumerate(self.TOOL_ORDER):
                if logic_id == self.eraser_tool_index:
                    combo_idx = i
                    break
            if combo_idx != -1:
                self.pen_style_combo.setCurrentIndex(combo_idx)
            self.pen_style_combo.blockSignals(False)

        else:
            self.eraser_tool_index = self.current_tool_index
            self.current_tool_index = self.normal_tool_index

            self.pen_radius = self.tool_radiuses.get(self.normal_tool_index, 8)
            self.solid_fill_mode = (self.normal_tool_index == 4)
            if self.solid_fill_mode:
                self.pen_radius = 1

            self.pen_style_combo.blockSignals(True)
            combo_idx = -1
            for i, (name, logic_id) in enumerate(self.TOOL_ORDER):
                if logic_id == self.normal_tool_index:
                    combo_idx = i
                    break
            if combo_idx != -1:
                self.pen_style_combo.setCurrentIndex(combo_idx)
            self.pen_style_combo.blockSignals(False)

        self.updateButtonStyles()
        self.radius_button.setText(f"R: {self.pen_radius}")

    def toggleMirrorMode(self, axis):
        if self.mirror_mode and self.mirror_axis == axis:
             self.mirror_mode = False
        else:
             self.mirror_mode = True
             self.mirror_axis = axis

        if self.mirror_mode:
            self.drawing_area.mirror_line_x = self.drawing_area.image.width() // 2
            self.drawing_area.mirror_line_y = self.drawing_area.image.height() // 2

        self.updateButtonStyles()
        self.drawing_area.update()

    def changeColor(self):
        dialog = CircleBrightnessDialog(initialColor=self.pen_color, parent=self)
        button_pos = self.color_button.mapToGlobal(QPoint(0, self.color_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            selected = dialog.getSelectedColor()
            self.pen_color = selected
            self.mix_colors = [selected]
            self.mix_history.append([selected])
            self.updateColorMenu()
            self.eraser_mode = False
            self.drawing_area.cancelImagePlacement()
            self.updateButtonStyles()
            self.color_button.setText("Color (1)")

    def addColorToMix(self):
        dialog = CircleBrightnessDialog(initialColor=self.pen_color, parent=self)
        button_pos = self.color_button.mapToGlobal(QPoint(0, self.color_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            selected = dialog.getSelectedColor()
            if len(self.mix_colors) >= 4:
                self.mix_colors.pop(0)
            self.mix_colors.append(selected)
            self.pen_color = selected
            self.mix_history.append(list(self.mix_colors))
            self.updateColorMenu()
            self.color_button.setText(f"Color ({len(self.mix_colors)})")

    def setMixMode(self, mode):
        self.mix_mode = mode

    def changePenStyle(self, index):
        if self.polyline_mode or self.curve_mode:
            self.drawing_area.finalizePolyline()

        logic_id = self.TOOL_ORDER[index][1]
        self.current_tool_index = logic_id

        if self.eraser_mode:
            self.eraser_tool_index = logic_id
        else:
            self.normal_tool_index = logic_id

        self.polyline_mode = False
        self.curve_mode = False
        self.solid_fill_mode = False
        self.text_mode = False

        if logic_id == 0:
            pass
        elif logic_id == 1:
            pass
        elif logic_id == 2:
            pass
        elif logic_id == 3:
            self.polyline_mode = True
        elif logic_id == 4:
            self.solid_fill_mode = True
            self.pen_radius = 1
            self.radius_button.setText(f"R: 1")
        elif logic_id == 5:
            self.curve_mode = True
        elif logic_id == 35:
            self.text_mode = True
            font_size = max(10, self.pen_radius * 2)
            self.drawing_area.text_input_widget.setFont(QFont("Arial", font_size))
        elif logic_id == 36:
            self.polyline_mode = True

        if logic_id != 4:
             self.pen_radius = self.tool_radiuses.get(logic_id, self.pen_radius)
             self.radius_button.setText(f"R: {self.pen_radius}")
        self.updateButtonStyles()

    def clearDrawing(self):
        self.updateButtonStyles()
        self.drawing_area.clear()

    def changeRadiusValue(self, new_value):
        if self.solid_fill_mode or (self.eraser_mode and self.eraser_tool_index == 4) or (not self.eraser_mode and self.normal_tool_index == 4):
             self.pen_radius = 1
             self.radius_button.setText("R: 1")
             return

        if self.eraser_mode:
            self.eraser_radius = new_value
            self.pen_radius = new_value
            self.tool_radiuses[self.eraser_tool_index] = new_value
            self.radius_button.setText(f"R: {self.pen_radius}")
        else:
            self.pen_radius = new_value
            self.tool_radiuses[self.normal_tool_index] = new_value
            self.radius_button.setText(f"R: {self.pen_radius}")

            if self.text_mode:
                self.drawing_area.text_input_widget.setFont(QFont("Arial", max(10, self.pen_radius * 2)))
                self.drawing_area.text_input_widget.updateGeometry()

    def showRadiusMenu(self):
        if self.solid_fill_mode:
             return
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
        custom_values = [1, 3, 5]
        custom_values.extend(range(10, 61, 5))
        for val in custom_values:
            action = menu.addAction(f"{val}")
            action.triggered.connect(lambda checked, v=val: self.changeRadiusValue(v))
        menu.exec_(self.radius_button.mapToGlobal(QPoint(0, self.radius_button.height())))

    def togglePressure(self):
        self.pen_pressure_enabled = not self.pen_pressure_enabled
        self.drawing_area.cancelImagePlacement()
        self.updateButtonStyles()

    def updateButtonStyles(self):
        self.eraser_button.setStyleSheet(self.buttonStylePressure(self.eraser_mode))
        self.pressure_button.setStyleSheet(self.buttonStylePressure(self.pen_pressure_enabled))
        self.mirror_button.setStyleSheet(self.buttonStylePressure(self.mirror_mode))
        self.always_top_btn.setStyleSheet(self.buttonStylePressure(self.always_top_mode))
        self.lazy_mouse_button.setStyleSheet(self.buttonStylePressure(self.lazy_mouse_enabled))
        self.g_button.setStyleSheet(self.buttonStylePressure(self.global_reference_visible))
        if self.placing_image:
            self.file_button.setStyleSheet(self.buttonStylePressure(True))
        elif self.drawing_area.placing_reference:
            self.file_button.setStyleSheet(self.buttonStylePressure(True))
        else:
            self.file_button.setStyleSheet(self.buttonStyle())
        self.nav_button.updateStyle()

    def undo(self):
        self.drawing_area.undo()
    def redo(self):
        self.drawing_area.redo()
    def getCurrentPen(self):
        color = self.background_color if self.eraser_mode else self.pen_color
        return color, self.pen_radius
    def changeBackgroundColor(self, pos=None):
        dialog = CircleBrightnessDialog(initialColor=self.background_color, parent=self)
        button_pos = self.eraser_button.mapToGlobal(QPoint(0, self.eraser_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            new_color = dialog.getSelectedColor()
            if self.background_color != new_color:
                self.background_color = new_color
                settings = QSettings("kavram", "DrawingEditor")
                settings.setValue("backgroundColor", new_color.name())
                if 0 <= self.current_page_index < len(self.pages_data):
                    self.pages_data[self.current_page_index]["background"] = new_color
                self.drawing_area.update()          # arka plan paintEvent'te çizilir
                if hasattr(self, "timeline"):
                    self.timeline.sync_current()
                    self.timeline._content_changed()

    def triggerCoreSwitcher(self):
        main_window = self.window()
        if hasattr(main_window, 'showSwitcher'):
            main_window.showSwitcher()
        else:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = DrawingEditorWindow()
    editor.show()
    sys.exit(app.exec_())
