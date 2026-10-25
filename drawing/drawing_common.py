# Kavram - ortak içe aktarmalar, yardımcılar ve SVG ikonlar
# (Drawing_editor.py çekirdeği ve kv_*.py modülleri bunu kullanır)


# --- kavram yol ayarı (otomatik; klasör yapısı: kavram/<program>/<program>.py) ---
import os as _os
_PROGRAM_DIR = _os.path.dirname(_os.path.abspath(__file__))
_KAVRAM_DIR = _os.environ.get("KAVRAM_DIR") or _os.path.dirname(_PROGRAM_DIR)
_KAVRAM_EXPORT_DIR = _os.path.join(_KAVRAM_DIR, "export")
# -------------------------------------------------------------------------------
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
