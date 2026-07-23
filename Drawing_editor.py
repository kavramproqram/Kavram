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
# ---------------------------------------------

import sys
import math
import os
import json
import base64
import random
import tempfile
import subprocess
import shutil
from collections import deque

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QDialog, QSlider, QLabel,
    QPushButton, QApplication, QFileDialog, QMessageBox, QShortcut, QLineEdit,
    QMenu, QAction, QComboBox, QWidgetAction, QScrollArea, QListWidget,
    QListWidgetItem, QAbstractItemView, QCheckBox, QInputDialog, QToolButton,
    QTextEdit, QSizePolicy, QSpinBox
)
from PyQt5.QtGui import (
    QColor, QPainter, QPen, QImage, QTabletEvent, QKeySequence, QFont,
    QFontMetrics, QCursor, QIcon, QPixmap, QPainterPath, QPolygon, QBrush,
    QDrag, QTransform, QClipboard, QLinearGradient, QRadialGradient, QConicalGradient,
    QRegion
)
from PyQt5.QtCore import (
    Qt, QPoint, QRect, QDir, QSize, QByteArray, QBuffer, QIODevice,
    pyqtSignal, QMimeData, QObject, QPointF, QRectF, QTimer, QEvent, QSettings
)
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtSvg import QSvgRenderer

# --- Yardımcı Fonksiyonlar ve Sabitler ---
def resource_path(relative_path):
    """ PyInstaller vb. derlemeler için dinamik kaynak yolu bulucu. """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ---- Uygulama içi FFmpeg yolu (bin/ altında) ----
FFMPEG_PATH = resource_path("bin/ffmpeg")
if not os.path.exists(FFMPEG_PATH):
    print(f"Uyarı: {FFMPEG_PATH} bulunamadı. Video dışa aktarma çalışmayabilir.")
elif not os.access(FFMPEG_PATH, os.X_OK):
    print(f"Uyarı: {FFMPEG_PATH} çalıştırılabilir değil. Video dışa aktarma çalışmayabilir.")

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
        self.setWindowIcon(QIcon(resource_path('ikon/Kavram.png')))
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
        settings = QSettings("Kavram", "DrawingEditor")
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
        settings = QSettings("Kavram", "DrawingEditor")
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
            w = font_metrics.width(line)
            if w > max_width: max_width = w

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
        if self.is_sensitivity and val == 0: return -1
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
                 if current == -1: current = 50
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

class MenuLayerWidget(QWidget):
    moveUpRequested = pyqtSignal()
    visibilityToggled = pyqtSignal(bool)
    activated = pyqtSignal()

    def __init__(self, name, visible, is_active, parent=None):
        super().__init__(parent)
        self.name = name
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)

        self.up_btn = QPushButton()
        self.up_btn.setFixedSize(24, 24)
        self.up_btn.setIcon(create_svg_icon(SVG_ARROW_UP, 16))
        self.up_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; border-radius: 4px; }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; border: 1px solid #777; }
        """)
        self.up_btn.clicked.connect(self.moveUpRequested.emit)

        self.name_btn = QPushButton(name)
        if is_active:
             self.name_btn.setStyleSheet("color: #4CAF50; font-weight: bold; background: transparent; border: none; text-align: left;")
        else:
             self.name_btn.setStyleSheet("color: white; background: transparent; border: none; text-align: left;")
        self.name_btn.clicked.connect(self.activated.emit)

        self.eye_btn = QPushButton()
        self.eye_btn.setFixedSize(24, 24)
        self.is_visible = visible
        self.updateEyeIcon()
        self.eye_btn.setStyleSheet("background: transparent; border: none;")
        self.eye_btn.clicked.connect(self.toggleVisibility)

    def toggleVisibility(self):
        self.is_visible = not self.is_visible
        self.updateEyeIcon()
        self.visibilityToggled.emit(self.is_visible)

    def updateEyeIcon(self):
        icon = create_svg_icon(SVG_EYE_OPEN if self.is_visible else SVG_EYE_CLOSED, size=20, color="#aaa")
        self.eye_btn.setIcon(icon)

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
        if self.underMouse(): painter.fillRect(self.rect(), QColor(60, 60, 60))
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
        if old_hover != self.hovered_index: self.update()
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
                if rect.contains(pos): clicked_color_index = i; break
            if clicked_color_index != -1: self.colorSelected.emit(self.colors[clicked_color_index], None)
            else:
                if len(self.colors) == 1: self.colorSelected.emit(self.colors[0], None)
                else: self.colorSelected.emit(None, self.colors)
        elif event.button() == Qt.RightButton: self.showContextMenu(event.pos())
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
            if rect.contains(pos): clicked_color_index = i; break
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
        clean_text = "".join(c for c in text.upper() if c in "0123456789ABCDEF")
        if clean_text != text:
            cursor = self.hex_input.cursorPosition()
            self.hex_input.setText(clean_text)
            self.hex_input.setCursorPosition(cursor)

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
            except:
                pass

    def _handleCtrlV(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        clean_hex = text.replace("#", "").replace("#", "").upper()
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
            except:
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
                else: self.colorWheel.setPixelColor(x, y, Qt.transparent)
                
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
            if not self._pickHueSat(event.pos()): self.accept()
            else: self.update()
        else: self.accept()
        
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if self._pickHueSat(event.pos()): self.update()
            
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
        
    def getSelectedColor(self): return QColor.fromHsvF(self.h/360.0, self.s, self.v)
    
    def focusOutEvent(self, event):
        self.accept()
        super().focusOutEvent(event)


class DrawingArea(QWidget):
    MAX_UNDO_REDO_STEPS = 15

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

        # TUVAL BOYUTU DİNAMİKLEŞTİRİLDİ
        canvas_w = self.parent().canvas_width if self.parent() and hasattr(self.parent(), 'canvas_width') else 1100
        canvas_h = self.parent().canvas_height if self.parent() and hasattr(self.parent(), 'canvas_height') else 600

        self.image = QImage(canvas_w, canvas_h, QImage.Format_RGB32)
        bg_color = self.parent().background_color if self.parent() else QColor("#333")
        self.image.fill(bg_color)
        
        self._display_pixmap = None
        self._actively_modifying = False

        self.reference_image = None
        self.reference_display_size = QSize(0, 0)
        self.reference_offset = QPoint(0, 0)

        self.layer_buffer = QImage(canvas_w, canvas_h, QImage.Format_ARGB32)
        self.layer_buffer.fill(Qt.transparent)

        self.image_cache = {}

        self.canvas_offset = QPoint(0, 0)
        self.panning = False
        self.last_pan_pos = QPoint()

        self.zoom_factor = 1.0
        self.view_offset = QPoint(0, 0)
        self.last_mouse_pos = QPoint()

        self.mirror_line_x = canvas_w // 2
        self.mirror_line_y = canvas_h // 2
        self.dragging_mirror_line = False

        self.drawing_elements = []
        
        self.undo_stack = []
        self.redo_stack = []

        self.layer_order = ["Eskiz", "Çizim"]
        self.current_layer_name = "Çizim"
        self.layer_visibility = {name: True for name in self.layer_order}

        self.force_active_layer_bottom = False

        self.text_input_widget = ResizableTextEdit(self)
        self.text_input_widget.hide()
        self.text_input_widget.finished.connect(self.addTextToDrawing)

        self.original_image_for_placement = None
        self.current_image_display_size = QSize(0, 0)
        self.image_placement_offset = QPoint(0, 0)
        self.dragging_image = False
        self.last_drag_pos = QPoint()

        self.placing_reference = False

        self.current_stroke_points = []
        self.current_stroke_pen_info = []
        self.current_mix_index = 0
        self.current_color_fraction = 0.0
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

    def commitImageToPixmap(self):
        self._display_pixmap = QPixmap.fromImage(self.image)
        self._actively_modifying = False

    def saveStateForUndo(self, deep_copy=False):
        if self.parent():
            self.parent().is_project_modified = True
            
        if deep_copy:
            elements_copy = json.loads(json.dumps(self.drawing_elements))
        else:
            elements_copy = self.drawing_elements[:]
            
        self.undo_stack.append((elements_copy, self.image.copy()))
        if len(self.undo_stack) > self.MAX_UNDO_REDO_STEPS:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            current_elements = json.loads(json.dumps(self.drawing_elements))
            self.redo_stack.append((current_elements, self.image.copy()))
            if len(self.redo_stack) > self.MAX_UNDO_REDO_STEPS: 
                self.redo_stack.pop(0)

            elements, img = self.undo_stack.pop()
            self.drawing_elements = json.loads(json.dumps(elements))

            if img.size() != self.image.size():
                self.updateImageFromElements()
            else:
                self.image = img.copy()
                self.commitImageToPixmap()
                self.update()

    def redo(self):
        if self.redo_stack:
            current_elements = json.loads(json.dumps(self.drawing_elements))
            self.undo_stack.append((current_elements, self.image.copy()))
            if len(self.undo_stack) > self.MAX_UNDO_REDO_STEPS: 
                self.undo_stack.pop(0)

            elements, img = self.redo_stack.pop()
            self.drawing_elements = json.loads(json.dumps(elements))

            if img.size() != self.image.size():
                self.updateImageFromElements()
            else:
                self.image = img.copy()
                self.commitImageToPixmap()
                self.update()

    def calculateMixColor(self, x, y, step_accum, mix_colors, mix_mode, mix_angle, sequential_idx=0):
        if not mix_colors: return QColor(0,0,0)
        num_colors = len(mix_colors)
        if num_colors == 1: return mix_colors[0]

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

    def setLayerOrder(self, names_ordered):
        self.layer_order = names_ordered
        self.updateImageFromElements()

    def setLayerVisibility(self, layer_name, visible):
        self.layer_visibility[layer_name] = visible
        self.updateImageFromElements()

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

    def expandImage(self, width, height):
        pass

    def generateSmoothCurvePath(self, points):
        if len(points) < 2: return QPainterPath()
        path = QPainterPath(); path.moveTo(points[0])
        if len(points) == 2: path.lineTo(points[1]); return path
        for i in range(len(points) - 1):
            p0 = points[i - 1] if i > 0 else points[i]
            p1 = points[i]; p2 = points[i + 1]
            p3 = points[i + 2] if i < len(points) - 2 else points[i + 1]
            c1 = p1 + (p2 - p0) / 6.0; c2 = p2 - (p3 - p1) / 6.0
            path.cubicTo(c1, c2, p2)
        return path

    def getMirroredPoint(self, p):
        parent = self.parent()
        if parent.mirror_axis == 'vertical':
            return QPoint(int(self.mirror_line_x - (p.x() - self.mirror_line_x)), int(p.y()))
        else:
            return QPoint(int(p.x()), int(self.mirror_line_y - (p.y() - self.mirror_line_y)))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1a1a1a"))
        painter.save()

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

        widget_rect = self.rect()
        inverted_transform, _ = transform.inverted()
        visible_rect_on_canvas = inverted_transform.mapRect(QRectF(widget_rect)).toRect()
        source_rect = visible_rect_on_canvas.intersected(self.image.rect())

        if not source_rect.isEmpty():
            if self._actively_modifying or self._display_pixmap is None:
                painter.drawImage(source_rect, self.image, source_rect)
            else:
                painter.drawPixmap(source_rect, self._display_pixmap, source_rect)

        parent = self.parent()

        if parent and (parent.mirror_mode or self.dragging_mirror_line):
            painter.save()
            pen = QPen(QColor(100, 100, 100), 1 / self.zoom_factor, Qt.DashLine)
            if self.dragging_mirror_line: pen = QPen(QColor(255, 0, 0), 2 / self.zoom_factor, Qt.SolidLine)
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

        if self.layer_visibility.get(self.current_layer_name, True):
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
                    if parent.eraser_mode: poly_color = parent.background_color
                    elif len(parent.mix_colors) > 1: poly_color = parent.mix_colors[0]
                    else: poly_color = parent.pen_color

                    current_radius = parent.eraser_radius if parent.eraser_mode else parent.pen_radius

                    pen = QPen(poly_color, current_radius, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    painter.setPen(pen)
                    if len(active_points) > 1:
                        if parent.curve_mode:
                            path = self.generateSmoothCurvePath(active_points)
                            painter.setBrush(Qt.NoBrush); painter.drawPath(path)
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
                        for p in active_points: points_to_draw.append((self.getMirroredPoint(p), True))
                    for i, (pt, is_mirrored) in enumerate(points_to_draw):
                        is_hovered = False
                        if not is_mirrored:
                             if i == self.hovered_poly_point_index: is_hovered = True
                        if is_hovered: painter.setBrush(QColor(255, 0, 0))
                        else: painter.setBrush(QColor(0, 255, 255) if not is_mirrored else QColor(0, 150, 150))
                        painter.drawEllipse(pt, radius, radius)
                    painter.restore()

        if self.original_image_for_placement and self.current_image_display_size.isValid():
            scaled_temp_image = self.original_image_for_placement.scaled(
                self.current_image_display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            final_pos = self.image_placement_offset

            if parent.mirror_mode:
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

        if self.placing_reference and self.reference_image and self.reference_display_size.isValid():
            scaled_ref_image = self.reference_image.scaled(
                self.reference_display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            painter.save()
            painter.setOpacity(0.5)  
            painter.drawImage(self.reference_offset, scaled_ref_image)
            painter.restore()

        if parent and not self.drawing_area_is_cursor_hidden():
             if parent.eraser_mode and not parent.nav_button.isChecked():
                 preview_radius = 1 
                 preview_color = QColor(255, 255, 255) 

                 mouse_canvas = self.mapFromGlobal(QCursor.pos())

                 if self.rect().contains(mouse_canvas):
                     painter.save()
                     painter.setPen(QPen(preview_color, 0)) 
                     painter.setBrush(Qt.NoBrush)
                     cursor_r = 0 
                     painter.drawEllipse(mouse_canvas, cursor_r, cursor_r)
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

        painter.restore()

    def drawing_area_is_cursor_hidden(self):
        return False

    def keyPressEvent(self, event):
        parent = self.parent()
        if parent and (parent.polyline_mode or parent.curve_mode):
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
            
        self.reference_image = ref_image
        self.placing_reference = True
        drawing_area_size = self.size()
        max_width = drawing_area_size.width() - 10
        max_height = drawing_area_size.height() - 10
        initial_scaled_size = self.reference_image.size().scaled(max_width, max_height, Qt.KeepAspectRatio)
        self.reference_display_size = initial_scaled_size
        self.reference_offset = QPoint((self.width() - initial_scaled_size.width()) // 2, (self.height() - initial_scaled_size.height()) // 2)
        
        self.parent().nav_button.setChecked(False)
        self.parent().nav_button.updateStyle()
        self.setCursor(Qt.CrossCursor)
        self.update()

    def cancelReferencePlacement(self):
        self.placing_reference = False
        self.setCursor(Qt.ArrowCursor)
        self.updateImageFromElements()
        self.parent().updateButtonStyles()
        self.update()

    def mousePressEvent(self, event):
        parent = self.parent()
        canvas_pos_float = self.toCanvas(event.pos())
        canvas_pos = QPoint(int(canvas_pos_float.x()), int(canvas_pos_float.y()))

        is_o_mode = parent.nav_button.isChecked()

        if event.button() == Qt.LeftButton:
            pass
        elif event.button() == Qt.MidButton and is_o_mode and not parent.placing_image and not self.placing_reference:
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

        layer_active = self.layer_visibility.get(self.current_layer_name, True)

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

        if parent and (parent.polyline_mode or parent.curve_mode) and layer_active:
            active_points = self.polyline_points if parent.polyline_mode else self.curve_points

            if (event.modifiers() & Qt.ControlModifier) and event.button() == Qt.LeftButton:
                self.dragging_whole_polyline = True; self.last_poly_drag_pos = canvas_pos; self.setCursor(Qt.SizeAllCursor); return
            if parent.is_c_pressed and event.button() == Qt.MiddleButton:
                self.dragging_whole_polyline = True; self.last_poly_drag_pos = canvas_pos; self.setCursor(Qt.SizeAllCursor); return
            if event.button() == Qt.LeftButton:
                active_points.append(canvas_pos); self.update(); return
            elif event.button() == Qt.MidButton:
                if self.hovered_poly_point_index != -1 and not parent.is_c_pressed:
                    self.dragging_poly_point_index = self.hovered_poly_point_index; self.setCursor(Qt.ClosedHandCursor)
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
                    if active_points: active_points.pop()
                elif action == reset_action:
                    if parent.polyline_mode: self.polyline_points = []
                    else: self.curve_points = []
                self.update(); return

        if event.button() == Qt.MiddleButton and not is_o_mode:
            if hasattr(parent, 'is_v_pressed') and parent.is_v_pressed:
                 self.dragging_mirror_line = True; self.last_pan_pos = event.pos(); self.setCursor(Qt.SizeHorCursor); return

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

        if parent and parent.placing_image and layer_active:
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

                    self.updateImageFromElements(); self.cancelImagePlacement(); parent.updateButtonStyles()
                return

            elif event.button() == Qt.MiddleButton or event.button() == Qt.RightButton:
                self.dragging_image = True; self.last_drag_pos = event.pos(); self.setCursor(Qt.ClosedHandCursor); event.accept(); return

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
                pen_color = QColor(0,0,0,0)
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
            self.current_color_fraction = 0.0
            self.stroke_length_accumulator = 0.0

            if not parent.eraser_mode and len(parent.mix_colors) > 1:
                pen_color = self.calculateMixColor(canvas_pos.x(), canvas_pos.y(), self.stroke_length_accumulator, parent.mix_colors, parent.mix_mode, parent.mix_angle, self.current_mix_index)
                if parent.mix_mode == 'sequential': self.current_mix_index += 1

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
            if parent.polyline_mode: self.polyline_points = [p + delta for p in active_points]
            else: self.curve_points = [p + delta for p in active_points]
            self.last_poly_drag_pos = canvas_pos
            self.update()
            return

        if parent and (parent.polyline_mode or parent.curve_mode):
            active_points = self.polyline_points if parent.polyline_mode else self.curve_points
            current_radius = parent.eraser_radius if parent.eraser_mode else parent.pen_radius

            if self.dragging_poly_point_index != -1:
                active_points[self.dragging_poly_point_index] = canvas_pos
                self.update()
            else:
                radius = max(5, current_radius + 5) / self.zoom_factor
                found = -1
                for i, pt in enumerate(active_points):
                    if (pt - canvas_pos).manhattanLength() < radius: found = i; break
                if found != self.hovered_poly_point_index:
                    self.hovered_poly_point_index = found
                    self.update()
            if self.dragging_poly_point_index != -1: return

        if self.dragging_image and self.placing_reference:
            delta = event.pos() - self.last_drag_pos
            self.reference_offset += delta
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

        if not self.layer_visibility.get(self.current_layer_name, True): return

        if (event.buttons() & Qt.LeftButton) and self.drawing and not parent.polyline_mode and not parent.curve_mode:
            
            if parent.current_tool_index in [37, 38]:
                if len(self.current_stroke_points) >= 2:
                    self.current_stroke_points[1] = canvas_pos
                    self.update()
                return

            if parent.current_tool_index == 36: return

            if parent.eraser_mode:
                pen_color = QColor(0,0,0,0)
                pen_width = parent.eraser_radius
            elif len(parent.mix_colors) > 1:
                pen_color = random.choice(parent.mix_colors) if parent.mix_mode == 'random' else parent.pen_color
                pen_width = parent.pen_radius
            else: pen_color, pen_width = parent.getCurrentPen()

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
                                if parent.mix_mode == 'sequential': self.current_mix_index += 1

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
        if not points_to_draw or len(points_to_draw) < 3: return

        if parent.eraser_mode: final_fill_color = QColor(0,0,0,0)
        elif len(self.current_stroke_pen_info) > 0 and len(parent.mix_colors) > 1: final_fill_color = self.current_stroke_pen_info[-1][0]
        else: final_fill_color = parent.pen_color

        min_x = min(p.x() for p in points_to_draw); max_x = max(p.x() for p in points_to_draw)
        min_y = min(p.y() for p in points_to_draw); max_y = max(p.y() for p in points_to_draw)
        w = max(1, max_x - min_x); h = max(1, max_y - min_y)

        path = QPainterPath(); path.moveTo(points_to_draw[0])
        for p in points_to_draw[1:]: path.lineTo(p)
        path.closeSubpath()

        painter = QPainter(self.image); painter.setRenderHint(QPainter.Antialiasing)

        if parent.eraser_mode:
            painter.setCompositionMode(QPainter.CompositionMode_Clear)

        border_pen = QPen(final_fill_color, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin); painter.setPen(border_pen)

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

                pattern_img = QImage(w, h, QImage.Format_ARGB32); pattern_img.fill(Qt.transparent)
                p_painter = QPainter(pattern_img); p_painter.setRenderHint(QPainter.Antialiasing)
                local_start = start_point - QPointF(min_x, min_y); local_end = end_point - QPointF(min_x, min_y)
                local_gradient = QLinearGradient(local_start, local_end)
                for i, col in enumerate(parent.mix_colors):
                    pos = i / (len(parent.mix_colors) - 1) if len(parent.mix_colors) > 1 else 0
                    local_gradient.setColorAt(pos, col)
                p_painter.setBrush(QBrush(local_gradient)); p_painter.setPen(Qt.NoPen)
                path_translated = QPainterPath(); path_translated.moveTo(points_to_draw[0] - QPoint(min_x, min_y))
                for p in points_to_draw[1:]: path_translated.lineTo(p - QPoint(min_x, min_y))
                path_translated.closeSubpath()
                p_painter.drawPath(path_translated); p_painter.end()
                if is_mirrored_shape: pattern_img = pattern_img.mirrored(True, False)
                buffer = QByteArray()
                buffer_io = QBuffer(buffer)
                buffer_io.open(QIODevice.WriteOnly)
                pattern_img.save(buffer_io, "PNG")
                texture_b64 = base64.b64encode(buffer.data()).decode('utf-8')
            else:
                pattern_img = QImage(w, h, QImage.Format_ARGB32); pattern_img.fill(final_fill_color)
                p_painter = QPainter(pattern_img); p_painter.setRenderHint(QPainter.Antialiasing)
                num_blobs = int(w * h / 50); mix_idx = 0; angle_rad = math.radians(parent.mix_angle)
                for i in range(max(10, num_blobs)):
                    bx = random.randint(0, w); by = random.randint(0, h); global_x = min_x + bx; global_y = min_y + by
                    if is_mirrored_shape: global_x = self.mirror_line_x - (global_x - self.mirror_line_x)
                    
                    color = self.calculateMixColor(global_x, global_y, 0.0, parent.mix_colors, parent.mix_mode, parent.mix_angle, mix_idx)
                    if parent.mix_mode == 'sequential': mix_idx += 1
                    
                    p_painter.setBrush(QBrush(color)); p_painter.setPen(Qt.NoPen); r = random.randint(5, 25); p_painter.drawEllipse(bx, by, r, r)
                p_painter.end()
                if is_mirrored_shape: pattern_img = pattern_img.mirrored(True, False)
                buffer = QByteArray()
                buffer_io = QBuffer(buffer)
                buffer_io.open(QIODevice.WriteOnly)
                pattern_img.save(buffer_io, "PNG")
                texture_b64 = base64.b64encode(buffer.data()).decode('utf-8')
                brush = QBrush(pattern_img); painter.translate(min_x, min_y)
                path_translated = QPainterPath(); path_translated.moveTo(points_to_draw[0] - QPoint(min_x, min_y))
                for p in points_to_draw[1:]: path_translated.lineTo(p - QPoint(min_x, min_y))
                path_translated.closeSubpath()
                painter.setBrush(brush); painter.drawPath(path_translated); painter.translate(-min_x, -min_y)
        else:
            painter.setBrush(QBrush(final_fill_color)); painter.drawPath(path)

        painter.end()
        element_data = {
            "type": "stroke", "points": [[p.x(), p.y()] for p in points_to_draw],
            "color": [final_fill_color.red(), final_fill_color.green(), final_fill_color.blue(), final_fill_color.alpha()],
            "width": 1, "pressure_enabled": False, "is_solid_fill": True, "layer": self.current_layer_name
        }
        if parent.eraser_mode:
            element_data["is_eraser"] = True

        if texture_b64: element_data["fill_texture"] = texture_b64; element_data["bbox"] = [min_x, min_y, w, h]
        self.drawing_elements.append(element_data)

    def mouseReleaseEvent(self, event):
        parent = self.parent()

        if self.panning:
            self.panning = False
            if self.alt_permanent_pan_mode:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.CrossCursor)
            return

        if self.dragging_mirror_line: self.dragging_mirror_line = False; self.setCursor(Qt.CrossCursor); return
        if self.dragging_whole_polyline: self.dragging_whole_polyline = False; self.setCursor(Qt.CrossCursor); return
        if parent and (parent.polyline_mode or parent.curve_mode):
            self.dragging_poly_point_index = -1
            self.setCursor(Qt.CrossCursor)
            return

        if (event.button() == Qt.MiddleButton or event.button() == Qt.RightButton) and self.dragging_image:
            self.dragging_image = False; self.setCursor(Qt.CrossCursor); event.accept(); return

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
                        if parent.eraser_mode: data["is_eraser"] = True
                        self.drawing_elements.append(data)

                        if parent.mirror_mode:
                            m_pts = [self.getMirroredPoint(p) for p in pts]
                            m_data = {
                                "type": "stroke", "points": [[p.x(), p.y()] for p in m_pts],
                                "color": [pen_color.red(), pen_color.green(), pen_color.blue(), pen_color.alpha()],
                                "width": pen_width, "pressure_enabled": False, "layer": self.current_layer_name
                            }
                            if parent.eraser_mode: m_data["is_eraser"] = True
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
                    def save_stroke(points, info, is_mirrored_call=False):
                        if parent.pen_pressure_enabled or is_mixed or is_special_brush:
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
                                "brush_type": parent.current_tool_index if is_special_brush else 0, "layer": self.current_layer_name
                            }
                            if parent.eraser_mode: data["is_eraser"] = True
                            self.drawing_elements.append(data)
                        else:
                            if parent.eraser_mode:
                                color_to_save = parent.background_color
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
                            if parent.eraser_mode: data["is_eraser"] = True
                            self.drawing_elements.append(data)

                    save_stroke(self.current_stroke_points, self.current_stroke_pen_info)
                    if parent.mirror_mode:
                        save_stroke(self.current_stroke_points, self.current_stroke_pen_info, is_mirrored_call=True)

            self.current_stroke_points = []
            self.current_stroke_pen_info = []
            self.drawing = False
            self._actively_modifying = False
            
            self.lazy_mouse_pos = None
            self.lazy_target_pos = None
            self.lazy_velocity = QPointF(0, 0)

            if parent.eraser_mode or self.force_active_layer_bottom:
                self.updateImageFromElements()
            else:
                self.commitImageToPixmap()
                self.update()

    def finalizePolyline(self):
        active_points = self.polyline_points if self.parent().polyline_mode else self.curve_points
        if not active_points: return
        self.saveStateForUndo(deep_copy=False)
        parent = self.parent()

        if parent.eraser_mode:
            c = parent.background_color
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
                if parent.eraser_mode: data["is_eraser"] = True
                self.drawing_elements.append(data)

        is_arrow = (parent.current_tool_index == 36)
        save_path_as_stroke(active_points, add_arrow=is_arrow)
        if parent.mirror_mode:
            mirrored_pts = [self.getMirroredPoint(p) for p in active_points]
            save_path_as_stroke(mirrored_pts, add_arrow=is_arrow)

        if parent.polyline_mode: self.polyline_points = []
        else: self.curve_points = []
        self.updateImageFromElements()

    def drawBrushStroke(self, painter, p1, p2, color, width, tool_index):
        dist = math.sqrt((p2.x()-p1.x())**2 + (p2.y()-p1.y())**2)
        i_width = int(width) if width > 0 else 1

        if tool_index == 6:
            pen = QPen(color, width); pen.setCapStyle(Qt.SquareCap); painter.setPen(pen)
            painter.save(); painter.translate(p2); painter.rotate(45); painter.drawLine(0, -i_width//2, 0, i_width//2); painter.restore()
            painter.drawLine(p1, p2)
        elif tool_index == 7:
            marker_color = QColor(color); marker_color.setAlpha(40); painter.setPen(Qt.NoPen); painter.setBrush(marker_color)
            rect_size = width * 1.5; painter.drawRect(int(p2.x() - rect_size/2), int(p2.y() - rect_size/2), int(rect_size), int(rect_size))
        elif tool_index == 8:
            density = int(width * 1.5); painter.setPen(QPen(color, 1))
            for _ in range(density):
                angle = random.random() * 2 * math.pi; radius = random.random() * width
                dx = int(radius * math.cos(angle)); dy = int(radius * math.sin(angle)); painter.drawPoint(p2.x() + dx, p2.y() + dy)
        elif tool_index == 9:
            chalk_color = QColor(color); chalk_color.setAlpha(150); painter.setPen(QPen(chalk_color, 1)); steps = max(1, int(dist))
            for i in range(steps):
                t = i / steps; x = p1.x() + (p2.x() - p1.x()) * t; y = p1.y() + (p2.y() - p1.y()) * t
                rx = random.randint(int(-i_width//2), int(i_width//2))
                ry = random.randint(int(-i_width//2), int(i_width//2))
                if random.random() > 0.3: painter.drawPoint(int(x + rx), int(y + ry))
        elif tool_index == 10:
            hl_color = QColor(color); hl_color.setAlpha(60); painter.setPen(Qt.NoPen); painter.setBrush(hl_color); h = width * 2; w = 5
            painter.drawRect(int(p2.x() - w/2), int(p2.y() - h/2), w, int(h))
        elif tool_index == 11:
            gradient = QRadialGradient(p2, width); c1 = QColor(color); c1.setAlpha(20); c2 = QColor(color); c2.setAlpha(0)
            gradient.setColorAt(0, c1); gradient.setColorAt(1, c2); painter.setBrush(QBrush(gradient)); painter.setPen(Qt.NoPen); painter.drawEllipse(p2, width, width)
        elif tool_index == 12: painter.setPen(QPen(color, max(1, i_width//2), Qt.SolidLine)); painter.drawLine(p1, p2)
        elif tool_index == 13: painter.setPen(QPen(color, 1)); painter.drawPoint(p2)
        elif tool_index == 14:
            char_color = QColor(40, 40, 40, 100); painter.setPen(QPen(char_color, 1))
            for _ in range(i_width):
                rx = random.randint(int(-i_width//2), int(i_width//2))
                ry = random.randint(int(-i_width//2), int(i_width//2))
                painter.drawPoint(p2.x() + rx, p2.y() + ry)
        elif tool_index == 15:
            painter.setBrush(color); painter.setPen(Qt.NoPen);
            painter.drawEllipse(p2, int(width/2), int(width/2))
        elif tool_index == 16:
            painter.setPen(QPen(color, 1)); painter.drawPoint(p2)
            if random.random() > 0.8:
                offset_x = random.randint(-50, 50); offset_y = random.randint(-50, 50); painter.setPen(QPen(color, 0.5)); painter.drawLine(p2, QPoint(p2.x()+offset_x, p2.y()+offset_y))
        elif tool_index == 17:
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap)); painter.setOpacity(0.3); painter.drawLine(p1, p2); painter.setOpacity(1.0)
            painter.setPen(QPen(QColor(255, 255, 255), max(1, i_width//3), Qt.SolidLine, Qt.RoundCap)); painter.drawLine(p1, p2)
        elif tool_index == 18:
            if dist > 5:
                painter.setPen(Qt.NoPen)
                for _ in range(3):
                    conf_color = QColor(random.randint(0,255), random.randint(0,255), random.randint(0,255)); painter.setBrush(conf_color)
                    cx = p2.x() + random.randint(int(-i_width), int(i_width))
                    cy = p2.y() + random.randint(int(-i_width), int(i_width))
                    cs = random.randint(2, 6)
                    if random.random() > 0.5: painter.drawEllipse(cx, cy, cs, cs)
                    else: painter.drawRect(cx, cy, cs, cs)

        elif tool_index == 19:
             painter.setPen(Qt.NoPen); painter.setBrush(color)
             painter.save(); painter.translate(p2); painter.rotate(random.randint(0, 360))
             path = QPainterPath(); path.moveTo(0, -width);
             path.quadTo(width/2, -width/2, 0, width); path.quadTo(-width/2, -width/2, 0, -width)
             painter.drawPath(path); painter.restore()

        elif tool_index == 20:
             painter.setPen(QPen(color, 1)); painter.setBrush(Qt.NoBrush); size = i_width
             painter.save(); painter.translate(p2); painter.rotate(random.randint(0, 360))
             points = [QPoint(0, -size), QPoint(size//4, -size//4), QPoint(size, 0), QPoint(size//4, size//4), QPoint(0, size), QPoint(-size//4, size//4), QPoint(-size, 0), QPoint(-size//4, -size//4)]
             painter.drawPolygon(QPolygon(points)); painter.restore()

        elif tool_index == 21:
            painter.setPen(QPen(color, 1)); painter.setBrush(QColor(color.red(), color.green(), color.blue(), 50))
            painter.drawEllipse(p2, width, width)
            painter.setBrush(QColor(255, 255, 200)); painter.setPen(Qt.NoPen)
            painter.drawEllipse(p2.x() - i_width//3, p2.y() - i_width//3, i_width//3, i_width//3)

        elif tool_index == 22:
            if dist > 3:
                painter.setPen(QPen(color, 1))
                for _ in range(3):
                    gx = p2.x() + random.randint(-5, 5)
                    gy = p2.y() + random.randint(-2, 2)
                    gh = random.randint(int(width), int(width * 3)) if width > 1 else random.randint(5, 15)
                    painter.drawLine(gx, gy, gx, gy - gh)

        elif tool_index == 23: hue = (p2.x() + p2.y()) % 360; rb_color = QColor.fromHsv(hue, 200, 250); painter.setPen(QPen(rb_color, width, Qt.SolidLine, Qt.RoundCap)); painter.drawLine(p1, p2)
        elif tool_index == 24:
            painter.setPen(QPen(color, 1)); dx = p2.x() - p1.x(); dy = p2.y() - p1.y(); normal_x = -dy; normal_y = dx; length = math.sqrt(normal_x**2 + normal_y**2)
            if length > 0: normal_x /= length; normal_y /= length; fur_len = width * 1.5; painter.drawLine(p2.x(), p2.y(), int(p2.x() + normal_x * fur_len), int(p2.y() + normal_y * fur_len))

        elif tool_index == 25:
            painter.setPen(QPen(color, 1)); painter.drawLine(p1, p2)
            if random.random() > 0.5:
                w_offset = max(1, int(width // 2))
                offsets = [random.randint(-w_offset, w_offset) for _ in range(4)]
                painter.drawLine(p1.x()+offsets[0], p1.y()+offsets[1], p2.x()+offsets[2], p2.y()+offsets[3])

        elif tool_index == 26: pen = QPen(color, width); pen.setStyle(Qt.DotLine); painter.setPen(pen); painter.drawLine(p1, p2)
        elif tool_index == 27: pen = QPen(color, width); pen.setStyle(Qt.DashLine); painter.setPen(pen); painter.drawLine(p1, p2)
        elif tool_index == 28: pen = QPen(color, max(1, i_width//3)); offset = i_width // 2 + 2; painter.setPen(pen); painter.drawLine(p1.x()-offset, p1.y()-offset, p2.x()-offset, p2.y()-offset); painter.drawLine(p1.x()+offset, p1.y()+offset, p2.x()+offset, p2.y()+offset)
        elif tool_index == 29: shadow_color = QColor(0, 0, 0, 50); painter.setPen(QPen(shadow_color, width, Qt.SolidLine, Qt.RoundCap)); painter.drawLine(p1.x()+5, p1.y()+5, p2.x()+5, p2.y()+5); painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap)); painter.drawLine(p1, p2)
        elif tool_index == 30: darker = color.darker(150); painter.setPen(QPen(darker, width, Qt.SolidLine, Qt.RoundCap)); painter.drawLine(p1.x()+2, p1.y()+2, p2.x()+2, p2.y()+2); painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap)); painter.drawLine(p1, p2)

        elif tool_index == 31:
            if dist > 0:
                painter.setPen(QPen(color, 2))
                amplitude = max(5, width)
                angle = math.atan2(p2.y()-p1.y(), p2.x()-p1.x()); perp_angle = angle + math.pi/2; offset = (p2.x() + p2.y()) / 10.0; off1 = math.sin(offset) * amplitude; off2 = math.sin(offset + math.pi) * amplitude
                pt1_x = p2.x() + math.cos(perp_angle) * off1; pt1_y = p2.y() + math.sin(perp_angle) * off1; pt2_x = p2.x() + math.cos(perp_angle) * off2; pt2_y = p2.y() + math.sin(perp_angle) * off2
                painter.drawPoint(int(pt1_x), int(pt1_y)); painter.drawPoint(int(pt2_x), int(pt2_y))
                if random.random() > 0.8: painter.setPen(QPen(color, 1)); painter.drawLine(int(pt1_x), int(pt1_y), int(pt2_x), int(pt2_y))

        elif tool_index == 32: painter.setPen(QPen(color, 2)); offset = 5 if int(p2.x() / 10) % 2 == 0 else -5; painter.drawPoint(p2.x() + offset, p2.y() + offset)

        elif tool_index == 33:
            painter.setPen(QPen(color, 1))
            grid_size = max(5, int(width * 2))
            snap_x = (p2.x() // grid_size) * grid_size; snap_y = (p2.y() // grid_size) * grid_size; painter.drawLine(snap_x, snap_y, snap_x+grid_size, snap_y); painter.drawLine(snap_x, snap_y, snap_x, snap_y+grid_size)

        elif tool_index == 34:
             painter.setPen(QPen(color, 1))
             if dist > 5:
                 rand_range = max(2, int(width))
                 mx = (p1.x() + p2.x()) / 2 + random.randint(-rand_range, rand_range)
                 my = (p1.y() + p2.y()) / 2 + random.randint(-rand_range, rand_range)
                 painter.drawLine(p1, QPoint(int(mx), int(my))); painter.drawLine(QPoint(int(mx), int(my)), p2)
             else: painter.drawLine(p1, p2)

        else:
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(p1, p2)

    def wheelEvent(self, event):
        parent = self.parent()
        is_o_mode = parent.nav_button.isChecked()

        if self.placing_reference and self.reference_image:
            num_degrees = event.angleDelta().y() / 8
            num_steps = num_degrees / 15
            scale_factor = 1.0 + num_steps * 0.1
            current_size = self.reference_display_size
            new_width = int(current_size.width() * scale_factor)
            new_height = int(current_size.height() * scale_factor)
            
            min_size = 20
            max_size_width = self.width() - 10
            max_size_height = self.height() - 10
            new_width = max(min_size, min(new_width, max_size_width))
            new_height = max(min_size, min(new_height, max_size_height))
            
            if new_width != current_size.width() or new_height != current_size.height():
                current_center = self.reference_offset + QPoint(current_size.width() // 2, current_size.height() // 2)
                self.reference_display_size = QSize(new_width, new_height)
                self.reference_offset = current_center - QPoint(self.reference_display_size.width() // 2, self.reference_display_size.height() // 2)
                self.update()
                event.accept()
                return

        if parent and parent.placing_image and self.original_image_for_placement:
            num_degrees = event.angleDelta().y() / 8
            num_steps = num_degrees / 15
            scale_factor = 1.0 + num_steps * 0.1
            current_image_size = self.current_image_display_size
            new_width = int(current_image_size.width() * scale_factor)
            new_height = int(current_image_size.height() * scale_factor)
            min_size = 20; max_size_width = self.width() - 10; max_size_height = self.height() - 10
            new_width = max(min_size, min(new_width, max_size_width)); new_height = max(min_size, min(new_height, max_size_height))
            if new_width == current_image_size.width() and new_height == current_image_size.height(): event.ignore(); return
            current_center = self.image_placement_offset + QPoint(current_image_size.width() // 2, current_image_size.height() // 2)
            self.current_image_display_size = QSize(new_width, new_height)
            self.image_placement_offset = current_center - QPoint(self.current_image_display_size.width() // 2, self.current_image_display_size.height() // 2)
            self.applyImagePlacementBounds(); self.update(); event.accept()
        elif parent and (parent.polyline_mode or parent.curve_mode):
            active_points = self.polyline_points if parent.polyline_mode else self.curve_points
            if len(active_points) == 0: return
            center_x = sum(p.x() for p in active_points) / len(active_points)
            center_y = sum(p.y() for p in active_points) / len(active_points)
            center = QPoint(int(center_x), int(center_y))
            num_degrees = event.angleDelta().y() / 8
            scale_factor = 1.05 if num_degrees > 0 else 0.95
            new_points = []
            for p in active_points:
                vec = p - center
                new_vec_x = vec.x() * scale_factor; new_vec_y = vec.y() * scale_factor
                new_points.append(QPoint(int(center.x() + new_vec_x), int(center.y() + new_vec_y)))
            if parent.polyline_mode: self.polyline_points = new_points
            else: self.curve_points = new_points
            self.update(); event.accept()
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

    def drawTabletLineTo(self, endPoint, pressure): pass

    def addTextToDrawing(self):
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
            if canvas_font_size < 1: canvas_font_size = 1

            final_x = canvas_pos_f.x()
            final_y = canvas_pos_f.y()

            color = self.parent().pen_color

            self.drawing_elements.append({
                "type": "text", "content": text_content,
                "position": [final_x, final_y],
                "color": [color.red(), color.green(), color.blue(), color.alpha()],
                "font_size": canvas_font_size, "layer": self.current_layer_name
            })
            if self.parent().mirror_mode:
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
        max_width = drawing_area_size.width() - 10; max_height = drawing_area_size.height() - 10
        initial_scaled_size = self.original_image_for_placement.size().scaled(max_width, max_height, Qt.KeepAspectRatio)
        self.current_image_display_size = initial_scaled_size
        self.image_placement_offset = QPoint((self.width() - initial_scaled_size.width()) // 2, (self.height() - initial_scaled_size.height()) // 2)
        self.applyImagePlacementBounds(); self.dragging_image = False
        self.setCursor(Qt.CrossCursor); self.drawing = False
        self.current_stroke_points = []; self.current_stroke_pen_info = []

        self.parent().nav_button.setChecked(False)
        self.parent().nav_button.updateStyle()

        self.update()

    def cancelImagePlacement(self):
        self.original_image_for_placement = None
        self.current_image_display_size = QSize(0, 0)
        self.image_placement_offset = QPoint(0, 0)
        self.dragging_image = False; self.setCursor(Qt.ArrowCursor); self.drawing = False
        self.current_stroke_points = []; self.current_stroke_pen_info = []
        self.update()
        parent = self.parent()
        if parent: parent.placing_image = False; parent.updateButtonStyles()

    def applyImagePlacementBounds(self):
        if not self.original_image_for_placement or not self.current_image_display_size.isValid(): return
        pass

    def updateImageFromElements(self):
        self.setUpdatesEnabled(False)
        try:
            req_w = self.image.width()
            req_h = self.image.height()

            new_image = QImage(req_w, req_h, QImage.Format_RGB32)
            bg_color = self.parent().background_color if self.parent() else QColor("#333")
            new_image.fill(bg_color)

            final_painter = QPainter(new_image)
            final_painter.setRenderHint(QPainter.Antialiasing)

            if self.reference_image and self.reference_display_size.isValid() and not self.placing_reference:
                scaled_ref = self.reference_image.scaled(
                    self.reference_display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                final_painter.save()
                final_painter.setOpacity(0.4) 
                final_painter.drawImage(self.reference_offset, scaled_ref)
                final_painter.restore()

            elements_by_layer = {name: [] for name in self.layer_order}
            for element in self.drawing_elements:
                layer_name = element.get("layer", "Eskiz")
                if layer_name not in elements_by_layer:
                    elements_by_layer.setdefault("Eskiz", []).append(element)
                else:
                    elements_by_layer[layer_name].append(element)

            if self.layer_buffer.size() != QSize(req_w, req_h):
                self.layer_buffer = QImage(req_w, req_h, QImage.Format_ARGB32)

            render_order = list(self.layer_order)

            if self.force_active_layer_bottom:
                if self.current_layer_name in render_order:
                    render_order.remove(self.current_layer_name)
                    render_order.insert(0, self.current_layer_name)

            for layer_name in render_order:
                if not self.layer_visibility.get(layer_name, True): continue
                layer_elements = elements_by_layer.get(layer_name, [])

                if not layer_elements:
                    continue

                self.layer_buffer.fill(Qt.transparent)

                layer_painter = QPainter(self.layer_buffer)
                layer_painter.setRenderHint(QPainter.Antialiasing)

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
                            path = QPainterPath(); path.moveTo(pts[0])
                            for p in pts[1:]: path.lineTo(p)
                            path.closeSubpath()
                            layer_painter.setPen(QPen(c, 1, Qt.SolidLine))

                            if is_eraser:
                                 layer_painter.setBrush(QBrush(Qt.black))
                                 layer_painter.drawPath(path)
                            elif "fill_texture" in element and element["fill_texture"]:
                                 base64_data = element["fill_texture"]; image_data = base64.b64decode(base64_data)
                                 pattern_img = QImage(); pattern_img.loadFromData(image_data, "PNG")
                                 bbox = element.get("bbox", [0, 0, 1, 1]); min_x, min_y = bbox[0], bbox[1]
                                 layer_painter.save(); layer_painter.translate(min_x, min_y)
                                 path_translated = QPainterPath(); path_translated.moveTo(pts[0] - QPoint(int(min_x), int(min_y)))
                                 for p in pts[1:]: path_translated.lineTo(p - QPoint(int(min_x), int(min_y)))
                                 path_translated.closeSubpath()
                                 layer_painter.setBrush(QBrush(pattern_img)); layer_painter.drawPath(path_translated); layer_painter.restore()
                            else:
                                layer_painter.setBrush(QBrush(c)); layer_painter.drawPath(path)
                        continue

                    if element["type"] == "stroke":
                        color = QColor(*element["color"])
                        width = element["width"]

                        pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                        layer_painter.setPen(pen)
                        points = [QPoint(int(p[0]), int(p[1])) for p in element["points"]]
                        if len(points) > 1: layer_painter.drawPolyline(QPolygon(points))
                        elif len(points) == 1: layer_painter.drawPoint(points[0])

                    elif element["type"] == "stroke_pressure":
                        points_data = element["points"]
                        brush_type = element.get("brush_type", 0)

                        if brush_type == 0:
                            for i in range(len(points_data) - 1):
                                p1_data = points_data[i]; p2_data = points_data[i+1]
                                p1 = QPoint(int(p1_data[0]), int(p1_data[1])); p2 = QPoint(int(p2_data[0]), int(p2_data[1]))

                                color = QColor(p1_data[2], p1_data[3], p1_data[4], p1_data[5])
                                width = p1_data[6]

                                pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                                layer_painter.setPen(pen)
                                layer_painter.drawLine(p1, p2)
                        else:
                             for i in range(len(points_data) - 1):
                                p1_data = points_data[i]; p2_data = points_data[i+1]
                                p1 = QPoint(int(p1_data[0]), int(p1_data[1])); p2 = QPoint(int(p2_data[0]), int(p2_data[1]))

                                color = QColor(p1_data[2], p1_data[3], p1_data[4], p1_data[5])
                                width = p1_data[6]
                                self.drawBrushStroke(layer_painter, p1, p2, color, width, brush_type)

                    elif element["type"] == "text":
                        color = QColor(*element["color"])
                        font = QFont("Arial", element["font_size"])
                        layer_painter.setPen(color); layer_painter.setFont(font)
                        text_pos = QPoint(int(element["position"][0]), int(element["position"][1]))
                        font_metrics = QFontMetrics(font)

                        lines = element["content"].split('\n')
                        current_y = text_pos.y()

                        if element.get("is_mirrored", False):
                            layer_painter.save(); layer_painter.translate(text_pos.x(), text_pos.y())
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

                        scaled_image = temp_image.scaled(element["current_width"], element["current_height"], Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        image_pos = QPoint(int(element["position"][0]), int(element["position"][1]))

                        if is_eraser:
                             layer_painter.setCompositionMode(QPainter.CompositionMode_Clear)
                             layer_painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
                             layer_painter.drawImage(image_pos, scaled_image)
                        else:
                            layer_painter.drawImage(image_pos, scaled_image)

                layer_painter.end()

                final_painter.drawImage(0, 0, self.layer_buffer)

            final_painter.end()
            self.image = new_image
            self.commitImageToPixmap()
        finally:
            self.setUpdatesEnabled(True)

        self.update()

    def replaceColor(self, target_color, new_color, is_delete=False, mode='global', pos=None):
        self.saveStateForUndo(deep_copy=True)
        if mode == 'global': self.replaceColorGlobally(target_color, new_color, is_delete)
        elif mode == 'connected' and pos is not None:
            self.floodFill(pos, target_color, new_color if not is_delete else QColor(0,0,0,0))
            buffer = QByteArray()
            buffer_io = QBuffer(buffer)
            buffer_io.open(QIODevice.WriteOnly)
            self.image.save(buffer_io, "PNG")
            base64_data = base64.b64encode(buffer.data()).decode('utf-8')
            w, h = self.image.width(), self.image.height()
            self.drawing_elements = [{"type": "image", "base64_data": base64_data, "position": [0, 0], "original_width": w, "original_height": h, "current_width": w, "current_height": h, "layer": self.current_layer_name}]
            self.updateImageFromElements()

    def replaceColorGlobally(self, target_color, new_color, is_delete=False):
        target_rgba = (target_color.red(), target_color.green(), target_color.blue())
        tolerance = 20
        for element in self.drawing_elements:
            if element["type"] == "stroke":
                ec = element["color"]
                if abs(ec[0]-target_rgba[0]) < tolerance and abs(ec[1]-target_rgba[1]) < tolerance and abs(ec[2]-target_rgba[2]) < tolerance:
                    if is_delete: element["color"][3] = 0
                    else: element["color"] = [new_color.red(), new_color.green(), new_color.blue(), new_color.alpha()]
            elif element["type"] == "stroke_pressure":
                points = element["points"]
                for p in points:
                    if abs(p[2]-target_rgba[0]) < tolerance and abs(p[3]-target_rgba[1]) < tolerance and abs(p[4]-target_rgba[2]) < tolerance:
                         if is_delete: p[5] = 0
                         else: p[2], p[3], p[4], p[5] = new_color.red(), new_color.green(), new_color.blue(), new_color.alpha()
            elif element["type"] == "image":
                base64_data = element["base64_data"]; image_data = base64.b64decode(base64_data)
                temp_image = QImage(); temp_image.loadFromData(image_data, "PNG"); temp_image = temp_image.convertToFormat(QImage.Format_ARGB32)
                width = temp_image.width(); height = temp_image.height(); modified = False
                for y in range(height):
                    for x in range(width):
                        pixel_color = temp_image.pixelColor(x, y)
                        if abs(pixel_color.red()-target_rgba[0]) < tolerance and abs(pixel_color.green()-target_rgba[1]) < tolerance and abs(pixel_color.blue()-target_rgba[2]) < tolerance:
                             if is_delete: temp_image.setPixelColor(x, y, QColor(0,0,0,0))
                             else: temp_image.setPixelColor(x, y, new_color)
                             modified = True
                if modified:
                    buffer = QByteArray()
                    buffer_io = QBuffer(buffer)
                    buffer_io.open(QIODevice.WriteOnly)
                    temp_image.save(buffer_io, "PNG")
                    element["base64_data"] = base64.b64encode(buffer.data()).decode('utf-8')
        self.updateImageFromElements()

    def floodFill(self, pos, target_color, replacement_color, tolerance=20):
        if not (0 <= pos.x() < self.image.width() and 0 <= pos.y() < self.image.height()): return
        image = self.image; w, h = image.width(), image.height()
        queue = deque([pos]); visited = set()
        if target_color == replacement_color: return
        while queue:
            p = queue.popleft(); px, py = p.x(), p.y()
            if not (0 <= px < w and 0 <= py < h): continue
            key = (px, py)
            if key in visited: continue
            visited.add(key)
            current_color = image.pixelColor(px, py)
            if not (abs(current_color.red() - target_color.red()) < tolerance and abs(current_color.green() - target_color.green()) < tolerance and abs(current_color.blue() - target_color.blue()) < tolerance): continue
            image.setPixelColor(px, py, replacement_color)
            queue.append(QPoint(px + 1, py)); queue.append(QPoint(px - 1, py))
            queue.append(QPoint(px, py + 1)); queue.append(QPoint(px, py - 1))
        self.commitImageToPixmap()
        self.update()

    def clear(self):
        self.drawing_elements.clear(); self.undo_stack.clear(); self.redo_stack.clear()
        
        canvas_w = self.parent().canvas_width if self.parent() and hasattr(self.parent(), 'canvas_width') else 1100
        canvas_h = self.parent().canvas_height if self.parent() and hasattr(self.parent(), 'canvas_height') else 600
        
        self.image = QImage(canvas_w, canvas_h, QImage.Format_RGB32)
        bg_color = self.parent().background_color if self.parent() else QColor("#333")
        self.image.fill(bg_color)
        self.layer_buffer = QImage(canvas_w, canvas_h, QImage.Format_ARGB32)
        
        self.commitImageToPixmap()
        self.update()


class DrawingEditorWindow(QWidget):
    DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')

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
        
        # BOŞ PROJE KORUMASI: Dosyaya dokunulup dokunulmadığını izler
        self.is_project_modified = False
        
        settings = QSettings("Kavram", "DrawingEditor")
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

        self.initUI()
        
        self.pages_data.append({"background": self.background_color})
        
        first_json_path = os.path.join(self.drawing_cache_dir, "sx.json")
        with open(first_json_path, 'w', encoding='utf-8') as f:
            json.dump([], f)
        
        empty_img = QImage(self.canvas_width, self.canvas_height, QImage.Format_RGB32)
        empty_img.fill(self.background_color)
        empty_img.save(os.path.join(self.drawing_cache_dir, "s1.png"), "PNG")
        
        self.loadPageData(0, save_current=False)
        
        self.loadLazyMouseSettings()
        self.lazy_mouse_button.updateButtonText(self)
        self.lazy_mouse_button.updateToolTip(self)
        if self.lazy_mouse_enabled:
            self.lazy_mouse_button.setStyleSheet(self.buttonStylePressure(True))
            
        # Program ilk açıldığında tuval boyutunu ekrana tam sığdırır (Auto Fit)
        QTimer.singleShot(100, self.fitCanvasToView)

    def fitCanvasToView(self):
        """Tuvali ekranın ortasına tam sığacak şekilde otomatik ölçekler (Zoom)."""
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
        if os.path.exists(self.drawing_cache_dir):
            try: shutil.rmtree(self.drawing_cache_dir, ignore_errors=True)
            except: pass
        os.makedirs(self.drawing_cache_dir, exist_ok=True)

    def keyPressEvent(self, event):
        import time
        if event.key() == Qt.Key_V:
            self.is_v_pressed = True; self.drawing_area.setCursor(Qt.SizeHorCursor)
        elif event.key() == Qt.Key_C:
            self.is_c_pressed = True
        elif event.key() == Qt.Key_N:
            if not self.drawing_area.text_input_widget.isVisible(): self.pen_style_combo.showPopup()
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
            self.is_v_pressed = False; self.drawing_area.setCursor(Qt.ArrowCursor)
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
        self.setWindowIcon(QIcon(resource_path('ikon/Kavram.png')))
        self.resize(900, 600)
        self.setStyleSheet("background-color: #222;")

        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("background-color: #222; border-bottom: 2px solid #555;")
        toolbar_frame.setFixedHeight(40)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)

        self.file_button = RightClickButton("File")
        self.file_button.setStyleSheet(self.buttonStyle())
        self.file_button.setFixedSize(90, 30)
        self.file_button.clicked.connect(self.importFile)
        self.file_button.rightClicked.connect(self.handleFileButtonRightClick)
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
            QComboBox { background-color: transparent; color: white; border: 2px solid #555; border-radius: 8px; padding: 2px 10px; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView { background-color: #444; color: white; selection-background-color: #666; }
        """)
        self.pen_style_combo.setFixedSize(155, 30)
        self.pen_style_combo.currentIndexChanged.connect(self.changePenStyle)
        toolbar_layout.addWidget(self.pen_style_combo, alignment=Qt.AlignLeft)

        self.nav_button = NavigationModeButton(self)
        self.nav_button.rightClicked.connect(self.openResolutionDialog)
        toolbar_layout.addWidget(self.nav_button, alignment=Qt.AlignLeft)

        self.mix_angle_button = MixAngleButton(f"Mix {self.mix_angle}°")
        self.mix_angle_button.setStyleSheet(self.buttonStyle())
        self.mix_angle_button.setFixedSize(70, 30)
        self.mix_angle_button.deltaChanged.connect(self.changeMixAngle)

        self.mix_angle_menu = QMenu(self)
        self.mix_angle_menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; }")
        for angle in range(0, 361, 10):
            if angle == 360: angle = 0
            act = self.mix_angle_menu.addAction(f"{angle}°")
            act.triggered.connect(lambda checked, a=angle: self.setMixAngle(a))
            if angle == 0: self.mix_angle_menu.addSeparator()
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
        self.layer_button.setFixedSize(0, 0)
        self.layer_button.clicked.connect(self.showLayerMenu)
        icon = create_svg_icon(SVG_LAYER_DRAWING, 16)
        self.layer_button.setIcon(icon)
        toolbar_layout.addWidget(self.layer_button, alignment=Qt.AlignLeft)

        self.always_top_btn = QPushButton("#")
        self.always_top_btn.setFixedSize(0, 0)
        self.always_top_btn.setStyleSheet(self.buttonStylePressure(self.always_top_mode))
        self.always_top_btn.setToolTip("Seçili Olmayan Katmanları Üstte Tut")
        self.always_top_btn.clicked.connect(self.toggleAlwaysTop)
        toolbar_layout.addWidget(self.always_top_btn, alignment=Qt.AlignLeft)

        self.lazy_mouse_button = LazyMouseButton(self)
        self.lazy_mouse_button.setFixedSize(33, 30)
        self.lazy_mouse_button.setStyleSheet(self.buttonStylePressure(self.lazy_mouse_enabled))
        self.lazy_mouse_button.setToolTip("Lazy Mouse: Yavaşlatılmış fare (Blender tarzı)\nVarsayılan: R=30, H=15")
        self.lazy_mouse_button.clicked.connect(self.toggleLazyMouse)
        self.lazy_mouse_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lazy_mouse_button.customContextMenuRequested.connect(self.showLazyMouseMenu)
        toolbar_layout.addWidget(self.lazy_mouse_button, alignment=Qt.AlignLeft)

        self.pressure_button = QPushButton("/")
        self.pressure_button.setStyleSheet(self.buttonStylePressure(self.pen_pressure_enabled))
        self.pressure_button.setFixedSize(30, 30)
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
        self.export_button.setFixedSize(95, 30)
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
        main_layout.addWidget(self.drawing_area)
        self.setLayout(main_layout)

        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self.redo)
        
        QShortcut(QKeySequence("Ctrl+Right"), self, self.goNextPage)
        QShortcut(QKeySequence("Ctrl+Left"), self, self.goPrevPage)
        QShortcut(QKeySequence("Ctrl+Shift+Right"), self, self.duplicateToNextPage)
        QShortcut(QKeySequence("Ctrl+Shift+Left"), self, self.duplicateToPrevPage)

    def openResolutionDialog(self):
        """O butonuna sağ tıklandığında (alan.py entegrasyonu) çalışacak olan fonksiyon.
           Projede çizik bile varsa veya birden fazla sayfa varsa uyararak engeller."""
        if len(self.pages_data) > 1 or self.is_project_modified:
            QMessageBox.warning(self, "Uyarı", "Çözünürlük ve tuval boyutu yalnızca tamamen boş ve yeni bir projede değiştirilebilir.\n\nLütfen çözünürlüğü değiştirmek için programı yeniden başlatın veya yeni, boş bir dosya kullanın.")
            return

        dialog = AspectRatioDialog(self)
        if dialog.exec_():
            settings = dialog.getSettings()
            new_w = settings["width"]
            new_h = settings["height"]
            self.applyNewResolution(new_w, new_h)

    def applyNewResolution(self, w, h):
        """Çözünürlük ve Boyutları, mevcut dosyadaki TÜM sayfalara entegre eder."""
        if w == self.canvas_width and h == self.canvas_height: 
            return
            
        self.saveCurrentPageData()
        
        self.canvas_width = w
        self.canvas_height = h
        
        for i in range(len(self.pages_data)):
            page_file = os.path.join(self.drawing_cache_dir, f"s{i + 1}.png")
            bg_color = self.pages_data[i]["background"]
            
            new_img = QImage(w, h, QImage.Format_RGB32)
            new_img.fill(bg_color)
            
            if os.path.exists(page_file):
                old_img = QImage(page_file)
                painter = QPainter(new_img)
                painter.drawImage(0, 0, old_img)
                painter.end()
                
            new_img.save(page_file, "PNG")
        
        self.drawing_area.image = QImage(w, h, QImage.Format_RGB32)
        self.drawing_area.image.fill(self.background_color)
        self.drawing_area.layer_buffer = QImage(w, h, QImage.Format_ARGB32)
        self.drawing_area.layer_buffer.fill(Qt.transparent)
        
        self.drawing_area.mirror_line_x = w // 2
        self.drawing_area.mirror_line_y = h // 2
        
        self.loadPageData(self.current_page_index, save_current=False)
        
        # Değişimden hemen sonra otomatik ekran sığdırma (Center/Fit) çalışır
        QTimer.singleShot(100, self.fitCanvasToView)

    def handleFileButtonRightClick(self, pos):
        if self.drawing_area.reference_image is not None:
            self.drawing_area.reference_image = None
            self.drawing_area.reference_display_size = QSize(0, 0)
            self.drawing_area.reference_offset = QPoint(0, 0)
            self.drawing_area.placing_reference = False
            self.drawing_area.updateImageFromElements()
            self.updateButtonStyles()
        else:
            options = QFileDialog.Options()
            file_filter = "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Reference Image (Background)", DrawingEditorWindow.DEFAULT_BASE_DIR,
                file_filter,
                options=options
            )
            if file_path:
                ref_img = QImage(file_path)
                if ref_img.isNull():
                    QMessageBox.critical(self, "Error", "Could not load reference image.")
                    return
                ref_img = ref_img.convertToFormat(QImage.Format_ARGB32)
                
                self.drawing_area.startReferencePlacement(ref_img)
                self.updateButtonStyles()

    def showExportMenu(self, pos):
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
        settings = QSettings("Kavram", "DrawingEditor")
        settings.setValue("exportFPS", fps)
        self.promptMKVExport()

    def promptMKVExport(self):
        self.saveCurrentPageData()
        options = QFileDialog.Options()
        file_filter = "Video Files (*.mkv)"
        default_filter = "Video Files (*.mkv)"

        file_path, _ = QFileDialog.getSaveFileName(
            self, f"Export MKV ({self.current_export_fps} fps)", self.current_file_path or DrawingEditorWindow.DEFAULT_BASE_DIR,
            file_filter,
            default_filter,
            options=options
        )
        
        if file_path:
            if not file_path.lower().endswith(".mkv"): file_path += ".mkv"
            self.exportToMKV(file_path)

    def goNextPage(self):
        if len(self.pages_data) > 0:
            new_idx = (self.current_page_index + 1) % len(self.pages_data)
            self.loadPageData(new_idx)

    def goPrevPage(self):
        if len(self.pages_data) > 0:
            new_idx = (self.current_page_index - 1) % len(self.pages_data)
            self.loadPageData(new_idx)

    def duplicateToNextPage(self):
        self.saveCurrentPageData()
        bg_color = QColor(self.background_color)
        dup_img = self.drawing_area.image.copy()
        
        new_idx = self.current_page_index + 1
        
        if new_idx >= len(self.pages_data):
            if len(self.pages_data) >= self.max_pages:
                QMessageBox.warning(self, "Uyarı", f"Sayfa sınırı ({self.max_pages}) aşıldı.")
                return
            self.pages_data.append({"background": bg_color})
        else:
            self.pages_data[new_idx]["background"] = bg_color
            
        new_base = os.path.join(self.drawing_cache_dir, f"s{new_idx + 1}")
        dup_img.save(f"{new_base}.png", "PNG")
            
        self.refreshPageButtonMenu()
        self.loadPageData(new_idx, save_current=False)
        self.is_project_modified = True

    def duplicateToPrevPage(self):
        if self.current_page_index <= 0:
            return 
            
        self.saveCurrentPageData()
        bg_color = QColor(self.background_color)
        dup_img = self.drawing_area.image.copy()
        
        new_idx = self.current_page_index - 1
        
        self.pages_data[new_idx]["background"] = bg_color
        
        new_base = os.path.join(self.drawing_cache_dir, f"s{new_idx + 1}")
        dup_img.save(f"{new_base}.png", "PNG")
        
        self.refreshPageButtonMenu()
        self.loadPageData(new_idx, save_current=False)
        self.is_project_modified = True

    def resetView(self):
        self.drawing_area.zoom_factor = 1.0
        self.drawing_area.view_offset = QPoint(0, 0)
        self.drawing_area.update()

    def toggleAlwaysTop(self):
        self.always_top_mode = not self.always_top_mode
        self.always_top_btn.setStyleSheet(self.buttonStylePressure(self.always_top_mode))
        self.drawing_area.force_active_layer_bottom = self.always_top_mode
        self.drawing_area.updateImageFromElements()

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
        settings = QSettings("Kavram", "DrawingEditor")
        settings.setValue("lazyMouse/enabled", self.lazy_mouse_enabled)
        settings.setValue("lazyMouse/radius", self.lazy_radius)
        settings.setValue("lazyMouse/factor", self.lazy_factor)
    
    def loadLazyMouseSettings(self):
        settings = QSettings("Kavram", "DrawingEditor")
        self.lazy_mouse_enabled = settings.value("lazyMouse/enabled", False, type=bool)
        self.lazy_radius = settings.value("lazyMouse/radius", 30, type=int)
        self.lazy_factor = settings.value("lazyMouse/factor", 15, type=int)

    def showLayerMenu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #333; border: 1px solid #555; }
        """)

        display_order = list(reversed(self.drawing_area.layer_order))

        for layer_name in display_order:
            action_widget = QWidgetAction(menu)

            is_active = (layer_name == self.drawing_area.current_layer_name)
            is_visible = self.drawing_area.layer_visibility.get(layer_name, True)

            item_widget = MenuLayerWidget(layer_name, is_visible, is_active)

            item_widget.activated.connect(lambda n=layer_name: self.activateLayer(n, menu))
            item_widget.visibilityToggled.connect(lambda v, n=layer_name: self.toggleLayerVisibility(n, v))
            item_widget.moveUpRequested.connect(lambda n=layer_name: self.moveLayerUp(n, menu))

            action_widget.setDefaultWidget(item_widget)
            menu.addAction(action_widget)

        menu.exec_(self.layer_button.mapToGlobal(QPoint(0, self.layer_button.height())))

    def activateLayer(self, name, menu):
        self.drawing_area.current_layer_name = name
        self.layer_button.setText(name)
        if name == "Eskiz": icon = create_svg_icon(SVG_LAYER_SKETCH, 16)
        elif name == "Çizim": icon = create_svg_icon(SVG_LAYER_DRAWING, 16)
        else: icon = create_svg_icon(SVG_LAYER_DRAWING, 16)
        self.layer_button.setIcon(icon)

        if self.always_top_mode:
            self.drawing_area.updateImageFromElements()

        menu.close()

    def toggleLayerVisibility(self, name, visible):
        self.drawing_area.setLayerVisibility(name, visible)

    def moveLayerUp(self, name, menu):
        current_order = self.drawing_area.layer_order
        if name not in current_order: return

        idx = current_order.index(name)
        if idx == len(current_order) - 1: return

        current_order[idx], current_order[idx+1] = current_order[idx+1], current_order[idx]

        self.drawing_area.setLayerOrder(current_order)
        menu.close()
        self.showLayerMenu()

    def saveCurrentPageData(self):
        """Mevcut sayfayı dondurur, PNG olarak kaydeder ve RAM'deki geçici değişiklikleri temizler."""
        if 0 <= self.current_page_index < len(self.pages_data):
            page_file_base = os.path.join(self.drawing_cache_dir, f"s{self.current_page_index + 1}")
            
            self.drawing_area.image.save(f"{page_file_base}.png", "PNG")
            
            self.drawing_area.drawing_elements.clear()
            self.drawing_area.undo_stack.clear()
            self.drawing_area.redo_stack.clear()
            
            sx_json = os.path.join(self.drawing_cache_dir, "sx.json")
            if os.path.exists(sx_json):
                try: os.remove(sx_json)
                except: pass
                
            self.pages_data[self.current_page_index]["background"] = self.background_color

    def loadPageData(self, index, save_current=True):
        """Geçiş yapılan yeni sayfa için yeni boş sx.json oluşturur ve arka planda PNG'yi yükler."""
        if 0 <= index < len(self.pages_data):
            if save_current:
                self.saveCurrentPageData()

            self.current_page_index = index
            page_info = self.pages_data[index]

            self.background_color = page_info["background"]
            
            self.drawing_area.undo_stack.clear()
            self.drawing_area.redo_stack.clear()

            sx_json = os.path.join(self.drawing_cache_dir, "sx.json")
            with open(sx_json, 'w', encoding='utf-8') as f:
                json.dump([], f)
            self.drawing_area.drawing_elements = []

            page_file_base = os.path.join(self.drawing_cache_dir, f"s{index + 1}")

            if os.path.exists(f"{page_file_base}.png"):
                self.drawing_area.image.load(f"{page_file_base}.png")
                self.drawing_area.commitImageToPixmap()
                self.drawing_area.update()
            else:
                self.drawing_area.image.fill(self.background_color)
                self.drawing_area.commitImageToPixmap()
                self.drawing_area.update()

            self.page_button.setText(str(self.current_page_index + 1))

    def addNewPage(self):
        if len(self.pages_data) >= self.max_pages:
            QMessageBox.warning(self, "Uyarı", f"Sayfa sınırı ({self.max_pages}) aşıldı.")
            return

        self.saveCurrentPageData()
        self.pages_data.append({"background": self.background_color})
        new_index = len(self.pages_data) - 1
        
        new_base = os.path.join(self.drawing_cache_dir, f"s{new_index + 1}")
            
        empty_img = QImage(self.canvas_width, self.canvas_height, QImage.Format_RGB32)
        empty_img.fill(self.background_color)
        empty_img.save(f"{new_base}.png", "PNG")
            
        self.loadPageData(new_index, save_current=False)
        self.is_project_modified = True

    def removePage(self):
        if len(self.pages_data) <= 1:
            QMessageBox.warning(self, "Uyarı", "En az bir sayfa kalmalıdır.")
            return

        reply = QMessageBox.question(self, "Sayfa Sil", "Mevcut sayfayı silmek istiyor musunuz?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            removed_base = os.path.join(self.drawing_cache_dir, f"s{self.current_page_index + 1}")
            if os.path.exists(f"{removed_base}.png"): os.remove(f"{removed_base}.png")
            
            for i in range(self.current_page_index, len(self.pages_data) - 1):
                old_base = os.path.join(self.drawing_cache_dir, f"s{i + 2}")
                new_base = os.path.join(self.drawing_cache_dir, f"s{i + 1}")
                if os.path.exists(f"{old_base}.png"): os.rename(f"{old_base}.png", f"{new_base}.png")

            self.pages_data.pop(self.current_page_index)
            if self.current_page_index >= len(self.pages_data):
                self.current_page_index = len(self.pages_data) - 1

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
        file_filter = "Supported Files (*.pnf *.drawing *.png *.jpg *.jpeg *.bmp *.gif);;Project Files (*.pnf *.drawing);;Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Drawing or Image", DrawingEditorWindow.DEFAULT_BASE_DIR,
            file_filter,
            options=options
        )
        if file_path:
            self.load_image_from_path(file_path)

    def saveProject(self):
        if self.current_file_path:
            self._save_to_path(self.current_file_path)
            QMessageBox.information(self, "Kaydet", f"Proje kaydedildi:\n{self.current_file_path}")
        else:
            self.exportFile()

    def _save_to_path(self, path):
        self.saveCurrentPageData()

        project_data = []
        for i, page in enumerate(self.pages_data):
            bg_color = page["background"]
            bg_list = [bg_color.red(), bg_color.green(), bg_color.blue(), bg_color.alpha()]
            
            png_file = os.path.join(self.drawing_cache_dir, f"s{i + 1}.png")
            b64_image_data = ""
            if os.path.exists(png_file):
                with open(png_file, 'rb') as img_f:
                    b64_image_data = base64.b64encode(img_f.read()).decode('utf-8')
                    
            project_data.append({
                "elements": [], 
                "image_data": b64_image_data,
                "background": bg_list,
                "resolution": {"width": self.canvas_width, "height": self.canvas_height}
            })

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=4)

        self.current_file_path = path

    def exportToMKV(self, file_path):
        # FFmpeg kontrolü (kendi ffmpeg'imizle)
        if not os.path.exists(FFMPEG_PATH) or not os.access(FFMPEG_PATH, os.X_OK):
            QMessageBox.critical(self, "Hata", 
                f"Video oluşturmak için '{FFMPEG_PATH}' dosyası bulunamadı veya çalıştırılamıyor.\n\n"
                "Lütfen uygulama dizininde 'bin/ffmpeg' olduğundan emin olun.")
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            temp_dir = tempfile.mkdtemp()
            original_index = self.current_page_index
            self.saveCurrentPageData()

            for i, page_data in enumerate(self.pages_data):
                self.background_color = page_data["background"]
                page_file_base = os.path.join(self.drawing_cache_dir, f"s{i + 1}")
                if os.path.exists(f"{page_file_base}.png"):
                    cached_img = QImage(f"{page_file_base}.png")
                    frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                    cached_img.save(frame_path, "PNG")
                else:
                    empty_img = QImage(self.canvas_width, self.canvas_height, QImage.Format_RGB32)
                    empty_img.fill(self.background_color)
                    frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                    empty_img.save(frame_path, "PNG")

            self.loadPageData(original_index, save_current=False)

            cmd = [
                FFMPEG_PATH, "-y", "-framerate", str(self.current_export_fps),
                "-i", os.path.join(temp_dir, "frame_%04d.png"),
                "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
                file_path
            ]

            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            QMessageBox.information(self, "Başarılı", f"Video başarıyla aktarıldı:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Beklenmeyen bir hata oluştu:\n{e}")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            QApplication.restoreOverrideCursor()

    def exportFile(self):
        self.saveCurrentPageData()

        QDir().mkpath(DrawingEditorWindow.DEFAULT_BASE_DIR)
        options = QFileDialog.Options()

        file_filter = "Project Native Format (*.pnf);;PDF Files (*.pdf);;PNG Files (*.png);;Drawing Files (*.drawing);;JPEG Files (*.jpg *.jpeg);;All Files (*)"
        default_filter = "Project Native Format (*.pnf)"

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Project", self.current_file_path or DrawingEditorWindow.DEFAULT_BASE_DIR,
            file_filter,
            default_filter,
            options=options
        )

        if not file_path: return

        if selected_filter.startswith("Project Native Format") or file_path.lower().endswith(".pnf"):
            if not file_path.lower().endswith(".pnf"): file_path += ".pnf"
            try:
                self._save_to_path(file_path)
                QMessageBox.information(self, "Kaydet", f"Proje başarıyla kaydedildi:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Dosya kaydedilemedi: {e}")

        elif selected_filter == "Drawing Files (*.drawing)":
            if not file_path.lower().endswith(".drawing"): file_path += ".drawing"
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=4)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Dosya kaydedilemedi: {e}")

        elif selected_filter == "PDF Files (*.pdf)" or file_path.lower().endswith(".pdf"):
            if not file_path.lower().endswith(".pdf"): file_path += ".pdf"
            try:
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(file_path)
                painter = QPainter(printer)
                original_index = self.current_page_index
                
                self.saveCurrentPageData()
                for i, page_data in enumerate(self.pages_data):
                    if i > 0: printer.newPage()
                    
                    page_file_base = os.path.join(self.drawing_cache_dir, f"s{i + 1}")
                    if os.path.exists(f"{page_file_base}.png"):
                        image = QImage(f"{page_file_base}.png")
                    else:
                        image = QImage(self.canvas_width, self.canvas_height, QImage.Format_RGB32)
                        image.fill(page_data.get("background", QColor("#333")))
                        
                    rect = painter.viewport()
                    size = image.size()
                    size.scale(rect.size(), Qt.KeepAspectRatio)
                    painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
                    painter.setWindow(image.rect())
                    painter.drawImage(0, 0, image)
                
                painter.end()
                self.loadPageData(original_index, save_current=False)
                QMessageBox.information(self, "Success", "PDF Exported successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not export PDF: {e}")
        else:
            if selected_filter == "PNG Files (*.png)":
                if not file_path.lower().endswith(".png"): file_path += ".png"
                file_format = "PNG"
            elif selected_filter == "JPEG Files (*.jpg *.jpeg)":
                if not file_path.lower().endswith((".jpg", ".jpeg")): file_path += ".jpg"
                file_format = "JPEG"
            elif selected_filter == "BMP Files (*.bmp)":
                if not file_path.lower().endswith(".bmp"): file_path += ".bmp"
                file_format = "BMP"
            elif selected_filter == "GIF Files (*.gif)":
                if not file_path.lower().endswith(".gif"): file_path += ".gif"
                file_format = "GIF"
            else:
                if not file_path.lower().endswith(".png"): file_path += ".png"
                file_format = "PNG"

            if not self.drawing_area.image.save(file_path, file_format):
                QMessageBox.critical(self, "Error", "Could not export drawing.")

    def load_image_from_path(self, file_path):
        if file_path.lower().endswith(".pnf"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)

                is_empty_project = (len(self.pages_data) == 1 and len(self.drawing_area.drawing_elements) == 0)

                if is_empty_project:
                    self.clearDrawingCache()
                    self.pages_data.clear()
                    start_index = 0
                else:
                    self.saveCurrentPageData()
                    start_index = len(self.pages_data)

                if isinstance(project_data, list):
                    if len(project_data) > 0 and "resolution" in project_data[0]:
                        res = project_data[0]["resolution"]
                        self.applyNewResolution(res.get("width", 1100), res.get("height", 600))
                    
                    for i, page in enumerate(project_data):
                        bg_list = page.get("background", [51, 51, 51, 255])
                        bg_color = QColor(bg_list[0], bg_list[1], bg_list[2], bg_list[3])
                        
                        page_idx = start_index + i
                        self.pages_data.append({"background": bg_color})
                        
                        new_base = os.path.join(self.drawing_cache_dir, f"s{page_idx + 1}")
                        
                        b64_image = page.get("image_data", "")
                        if b64_image:
                            try:
                                with open(f"{new_base}.png", 'wb') as img_f:
                                    img_f.write(base64.b64decode(b64_image))
                            except:
                                pass

                if len(self.pages_data) > 0:
                    self.refreshPageButtonMenu()
                    self.loadPageData(start_index, save_current=False)

                    if is_empty_project:
                        self.current_file_path = file_path
                        self.setWindowTitle(f"Kavram - {os.path.basename(file_path)}")
                        
                    # PNF yüklenmesinin ardından ekranı otomatik sığdırır (Auto Zoom)
                    QTimer.singleShot(150, self.fitCanvasToView)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"PNF dosyası yüklenemedi: {e}")

        elif file_path.lower().endswith(".drawing"):
            self.drawing_area.drawing_elements = []
            self.drawing_area.updateImageFromElements()
            self.drawing_area.undo_stack.clear()
            self.drawing_area.redo_stack.clear()
        else:
            imported_image = QImage(file_path)
            if imported_image.isNull(): QMessageBox.critical(self, "Error", "Could not load image."); return
            imported_image = imported_image.convertToFormat(QImage.Format_RGB32)
            extracted_colors = []
            small_thumb = imported_image.scaled(50, 50, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            for y in range(0, 50, 10):
                for x in range(0, 50, 10):
                    c = small_thumb.pixelColor(x, y); is_unique = True
                    for ex in extracted_colors:
                        if abs(ex.red() - c.red()) < 30 and abs(ex.green() - c.green()) < 30 and abs(ex.blue() - c.blue()) < 30: is_unique = False; break
                    if is_unique: extracted_colors.append(c)
                    if len(extracted_colors) >= 8: break
                if len(extracted_colors) >= 8: break
            if extracted_colors:
                self.mix_history.append(extracted_colors)
                self.updateColorMenu()
            self.placing_image = True; self.text_mode = False; self.eraser_mode = False
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
            if self.solid_fill_mode: self.pen_radius = 1

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
            self.pen_color = selected; self.mix_colors = [selected]
            self.mix_history.append([selected]); self.updateColorMenu()
            self.eraser_mode = False; self.drawing_area.cancelImagePlacement()
            self.updateButtonStyles(); self.color_button.setText("Color (1)")

    def addColorToMix(self):
        dialog = CircleBrightnessDialog(initialColor=self.pen_color, parent=self)
        button_pos = self.color_button.mapToGlobal(QPoint(0, self.color_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            selected = dialog.getSelectedColor()
            if len(self.mix_colors) >= 4:
                self.mix_colors.pop(0)
            self.mix_colors.append(selected); self.pen_color = selected
            self.mix_history.append(list(self.mix_colors)); self.updateColorMenu()
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

        if logic_id == 0: pass
        elif logic_id == 1: pass
        elif logic_id == 2: pass
        elif logic_id == 3: self.polyline_mode = True
        elif logic_id == 4:
            self.solid_fill_mode = True
            self.pen_radius = 1
            self.radius_button.setText(f"R: 1")
        elif logic_id == 5: self.curve_mode = True
        elif logic_id == 35:
            self.text_mode = True
            font_size = max(10, self.pen_radius * 2)
            self.drawing_area.text_input_widget.setFont(QFont("Arial", font_size))
        elif logic_id == 36: self.polyline_mode = True

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
        if self.placing_image: self.file_button.setStyleSheet(self.buttonStylePressure(True))
        elif self.drawing_area.placing_reference: self.file_button.setStyleSheet(self.buttonStylePressure(True))
        else: self.file_button.setStyleSheet(self.buttonStyle())
        self.nav_button.updateStyle()

    def undo(self): self.drawing_area.undo()
    def redo(self): self.drawing_area.redo()
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
                settings = QSettings("Kavram", "DrawingEditor")
                settings.setValue("backgroundColor", new_color.name())
                if 0 <= self.current_page_index < len(self.pages_data):
                    self.pages_data[self.current_page_index]["background"] = new_color
                self.drawing_area.updateImageFromElements()

    def triggerCoreSwitcher(self):
        main_window = self.window()
        if hasattr(main_window, 'showSwitcher'): main_window.showSwitcher()
        else: pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = DrawingEditorWindow()
    editor.show()
    sys.exit(app.exec_())
