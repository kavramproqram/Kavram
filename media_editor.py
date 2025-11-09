# Kavram 1.0.0
# Copyright (C) 2025-09-01 Kavram or Contributors
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
# Kavram 1.0.0
# Copyright (C) 2025-09-01 Kavram veya Contributors
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

import os
import shutil
import tempfile
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QFileDialog, QFrame, QSizePolicy, QMessageBox, QSplitter, QDialog, QMenu, QAction, QProgressBar, QComboBox, QShortcut, QGridLayout, QProgressDialog
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QImage, QPixmap, QIcon, QKeySequence
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint, QDir, QSize, QByteArray, QBuffer, QIODevice, QUrl
from PyQt5.QtSvg import QSvgRenderer
import sys
import re
import subprocess
import ctypes
import numpy as np
import time
import queue
import threading
import cv2
import copy
import json
import traceback

# QtMultimedia imports
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

# LuaRuntime import
import lupa
from lupa import LuaRuntime

# Gerekli ses işleme kütüphaneleri
try:
    import soundfile as sf
    import numpy as np
    import noisereduce as nr
    import scipy.signal as sig
    import librosa
    from pydub import AudioSegment
    from pydub.effects import compress_dynamic_range
    AUDIO_LIBS_MISSING = False
except ImportError:
    AUDIO_LIBS_MISSING = True

# --- YENİ EKLENEN FONKSİYON ---
# Bu fonksiyon, programın hem geliştirme ortamında (normal python ile çalışırken)
# hem de PyInstaller ile paketlendiğinde doğru dosya yolunu bulmasını sağlar.
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller, programı çalıştırırken geçici bir klasör oluşturur
        # ve bu klasörün yolunu sys._MEIPASS değişkeninde saklar.
        base_path = sys._MEIPASS
    except Exception:
        # Eğer program paketlenmemişse (geliştirme ortamı),
        # ana dosyanın bulunduğu klasörü temel yol olarak alır.
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
# --- GÜNCELLEME SONU ---


def show_missing_libs_error(parent):
    """Kütüphaneler eksik olduğunda gösterilecek hata mesajı."""
    QMessageBox.critical(parent, "Missing Libraries",
                         "Required audio libraries (soundfile, numpy, noisereduce, scipy, librosa, pydub) are not installed.\n"
                         "Please install them using: pip install soundfile numpy noisereduce scipy librosa pydub")


# --- Yardımcı Fonksiyonlar ve Sabitler ---
def create_svg_icon(svg_content, size=24, color="#eee"):
    """Verilen SVG içeriğinden bir QIcon oluşturur."""
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
# --- Yardımcı Fonksiyonlar ve Sabitler Sonu ---

DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')
SAVE_DIR = os.path.join(os.path.expanduser('~'),  'Kavram', 'medya_cut')
AUDIO_SAVE_DIR = os.path.join(os.path.expanduser('~'),  'Kavram', '_v&s_')

# --- GÜNCELLEME: Dosya yolları resource_path ile dinamik hale getirildi ---
LIB_PATH = resource_path("libmediaengine.so")
SETTINGS_FILE = resource_path("filter_settings c33.json") # Ayar dosyası
# --- GÜNCELLEME SONU ---

class Frame(ctypes.Structure):
    _fields_ = [("data", ctypes.POINTER(ctypes.c_ubyte)),
                ("width", ctypes.c_int),
                ("height", ctypes.c_int),
                ("channels", ctypes.c_int),
                ("data_owner", ctypes.c_bool)]

# Gelişmiş gürültü filtresi ayarları için diyalog penceresi (camera_editor.py'den kopyalandı)
class AdvancedFilterDialog(QDialog):
    """
    filtre.py'daki tüm ayarları içeren, kompakt bir pop-up.
    """
    def __init__(self, initial_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filter Settings")
        self.setWindowFlags(Qt.Popup) # Dışarı tıklayınca kapanma özelliği
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.settings = initial_settings.copy()

        self.setStyleSheet("""
            QDialog {
                background-color: rgba(40, 40, 40, 245);
                border: 1px solid #777;
                border-radius: 8px;
            }
            QLabel {
                color: #e0e0e0;
                background: transparent;
                font-size: 13px;
                font-weight: bold;
                padding-right: 5px;
            }
            QComboBox {
                background-color: #333; color: white; font-size: 13px;
                border: 1px solid #555; border-radius: 4px; padding: 4px;
            }
            QComboBox:hover { background-color: #444; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView {
                background-color: #282828; border: 1px solid #555;
                selection-background-color: #555; color: white;
            }
            QPushButton {
                background-color: #444; color: white; border: 1px solid #666;
                border-radius: 4px; padding: 5px 15px; margin-top: 5px;
            }
            QPushButton:hover { background-color: #555; }
        """)

        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

        # Filtre kontrollerini oluştur
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
        
        # Reverb seviyesi
        level_map_rev = {0: "Off", 1: "Low", 2: "Medium", 3: "High", 4: "Very High"}
        reverb_level = self.settings.get('reverb_reduction_level', 0)
        self.combo_reverb.setCurrentText(level_map_rev.get(reverb_level, "Off"))

        # De-Esser
        de_esser_map = {0: "Off", 1: "Low", 2: "Medium", 3: "High"}
        self.combo_de_esser.setCurrentText(de_esser_map.get(self.settings.get('de_esser_level', 0), "Off"))

        # De-Hum
        de_hum_map = {0: "Off", 1: "Low", 2: "Medium", 3: "High"}
        self.combo_de_hum.setCurrentText(de_hum_map.get(self.settings.get('de_hum_level', 0), "Off"))

        # Compressor Threshold
        comp_thresh = self.settings.get('comp_threshold_db', -990)
        self.combo_comp_thresh.setCurrentText(f"{int(comp_thresh)}dB" if comp_thresh > -990 else "Off")

        # Compressor Ratio
        ratio_map = {"1:1": 1, "2:1": 2, "3:1": 3, "4:1": 4, "5:1": 5, "8:1": 8, "10:1": 10}
        ratio_map_rev = {v: k for k, v in ratio_map.items()}
        self.combo_comp_ratio.setCurrentText(ratio_map_rev.get(self.settings.get('comp_ratio', 1), "1:1"))

        # Attack & Release
        attack_map = {1: "1ms", 5: "5ms", 10: "10ms", 20: "20ms", 50: "50ms", 100: "100ms"}
        self.combo_comp_attack.setCurrentText(attack_map.get(self.settings.get('comp_attack_ms', 10), "10ms"))

        release_map = {50: "50ms", 100: "100ms", 200: "200ms", 500: "500ms", 1000: "1000ms"}
        self.combo_comp_release.setCurrentText(release_map.get(self.settings.get('comp_release_ms', 100), "100ms"))

        # EQ
        self.combo_eq_gain.setCurrentText(f"{int(self.settings.get('eq_gain_db', 0))}dB")
        freq_map = {500: "500Hz", 1000: "1000Hz", 1500: "1500Hz", 2000: "2000Hz", 3000: "3000Hz", 4000: "4000Hz"}
        self.combo_eq_freq.setCurrentText(freq_map.get(self.settings.get('eq_freq_hz', 2000), "2000Hz"))
        q_map = {0.5: "0.5", 1.0: "1.0", 2.0: "2.0", 3.0: "3.0", 5.0: "5.0", 8.0: "8.0"}
        self.combo_eq_q.setCurrentText(q_map.get(self.settings.get('eq_q', 1.0), "1.0"))
        self.combo_de_esser.setCurrentText(level_map_rev.get(self.settings.get('de_esser_level', 0), "Off"))
        self.combo_de_hum.setCurrentText(level_map_rev.get(self.settings.get('de_hum_level', 0), "Off"))
        self.combo_comp_thresh.setCurrentText(f"{int(self.settings.get('compressor_threshold_db', 0))}dB" if self.settings.get('compressor_threshold_db', 0) != 0 else "Off")
        self.combo_comp_ratio.setCurrentText(f"{int(self.settings.get('compressor_ratio', 3))}:1")
        self.combo_comp_attack.setCurrentText(f"{int(self.settings.get('compressor_attack_ms', 5))}ms")
        self.combo_comp_release.setCurrentText(f"{int(self.settings.get('compressor_release_ms', 150))}ms")
        self.combo_eq_gain.setCurrentText(f"{int(self.settings.get('eq_gain_db', 0))}dB")
        self.combo_eq_freq.setCurrentText(f"{int(self.settings.get('eq_freq_hz', 1000))}Hz")
        self.combo_eq_q.setCurrentText(str(self.settings.get('eq_q', 1.0)))

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
        s['compressor_threshold_db'] = float(ct_text.replace('dB', '')) if ct_text != "Off" else 0.0
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

    def __init__(self, lua_runtime):
        super().__init__()
        self.lua = lua_runtime
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
        self.media_segments = segments
        self.active_segment_index = active_index
        self.update()

    def set_position(self, pos):
        self.position = pos
        self.update()

    def set_selected_segment(self, index):
        if self.selected_segment_index != index:
            self.selected_segment_index = index
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        border_radius = 8
        active_section_height = self.row_height_active
        available_dynamic_height = h - active_section_height
        min_dynamic_section_height = self.row_height_played_upcoming
        num_played_segments = self.active_segment_index
        num_upcoming_segments = len(self.media_segments) - (self.active_segment_index + 1)
        ideal_played_height = self.row_height_played_upcoming * max(1, num_played_segments)
        ideal_upcoming_height = self.row_height_played_upcoming * max(1, num_upcoming_segments)

        if num_played_segments == 0 and num_upcoming_segments == 0:
            played_section_height = int(available_dynamic_height / 2)
            upcoming_section_height = int(available_dynamic_height / 2)
        elif num_played_segments == 0:
            played_section_height = min_dynamic_section_height
            upcoming_section_height = available_dynamic_height - played_section_height
        elif num_upcoming_segments == 0:
            upcoming_section_height = min_dynamic_section_height
            played_section_height = available_dynamic_height - upcoming_section_height
        else:
            total_ideal_dynamic_height = ideal_played_height + ideal_upcoming_height
            if total_ideal_dynamic_height > 0:
                played_section_height = int((ideal_played_height / total_ideal_dynamic_height) * available_dynamic_height)
                upcoming_section_height = available_dynamic_height - played_section_height
            else:
                played_section_height = int(available_dynamic_height / 2)
                upcoming_section_height = int(available_dynamic_height / 2)

        played_section_height = max(1, int(played_section_height))
        upcoming_section_height = max(1, int(upcoming_section_height))
        active_section_height = max(1, int(active_section_height))

        if (played_section_height + upcoming_section_height + active_section_height) != h:
            diff = h - (played_section_height + upcoming_section_height + active_section_height)
            if played_section_height >= upcoming_section_height and played_section_height >= active_section_height:
                played_section_height += diff
            elif upcoming_section_height >= played_section_height and upcoming_section_height >= active_section_height:
                upcoming_section_height += diff
            else:
                active_section_height += diff

        played_bar_y = 0
        active_bar_y = played_section_height
        upcoming_bar_y = played_section_height + active_section_height

        painter.setPen(QPen(QColor("#555"), 1))
        painter.setBrush(QColor("#222"))
        painter.drawRect(0, played_bar_y, w, played_section_height)
        actual_row_height_played = played_section_height / max(1, num_played_segments) if num_played_segments > 0 else self.row_height_played_upcoming
        actual_segment_rect_height_played = actual_row_height_played - (2 * self.segment_padding_y_played_upcoming)
        actual_segment_rect_height_played = max(1, int(actual_segment_rect_height_played))
        current_y_offset_in_played_section = 0
        for i in range(self.active_segment_index):
            if current_y_offset_in_played_section + actual_row_height_played > played_section_height: break
            segment = self.media_segments[i]
            segment_top = played_bar_y + current_y_offset_in_played_section + self.segment_padding_y_played_upcoming
            segment_width = int(segment['duration'] * self.pixels_per_second)
            segment_width = max(segment_width, self.min_segment_width_pixels)
            segment_color = QColor("#555555")
            if segment['type'] == 'audio' or segment['type'] == 'recorded_audio': segment_color = QColor("#777777")
            elif segment['type'] == 'media_archive': segment_color = QColor("#444444")
            painter.setPen(Qt.NoPen)
            painter.setBrush(segment_color)
            painter.drawRoundedRect(self.line_number_width + self.segment_gap_x, int(segment_top), segment_width, actual_segment_rect_height_played, border_radius, border_radius)
            if i == self.selected_segment_index:
                painter.setPen(QPen(QColor("#007bff"), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(self.line_number_width + self.segment_gap_x, int(segment_top), segment_width, actual_segment_rect_height_played, border_radius, border_radius)
            painter.setFont(QFont("Arial", 10))
            painter.setPen(QColor("white"))
            row_number_text = str(i + 1)
            fm = painter.fontMetrics()
            row_number_text_rect = fm.boundingRect(row_number_text)
            row_number_x = (self.line_number_width - row_number_text_rect.width()) // 2
            row_number_y = int(played_bar_y + current_y_offset_in_played_section + (actual_row_height_played / 2) + (fm.ascent() / 2))
            painter.drawText(row_number_x, row_number_y, row_number_text)
            painter.setPen(QPen(QColor("#555"), 1))
            painter.drawLine(self.line_number_width, int(played_bar_y + current_y_offset_in_played_section), self.line_number_width, int(played_bar_y + current_y_offset_in_played_section + actual_row_height_played))
            painter.setFont(QFont("Arial", 10))
            painter.setPen(QColor("black"))
            abbreviation_text = f"{segment['abbreviation']} ({segment['formatted_duration_ms']})"
            abbreviation_text_rect = fm.boundingRect(abbreviation_text)
            abbreviation_x = self.line_number_width + self.segment_gap_x + 5
            abbreviation_y = int(played_bar_y + current_y_offset_in_played_section + self.segment_padding_y_played_upcoming + (actual_segment_rect_height_played / 2) + (fm.ascent() / 2))
            if segment_width > abbreviation_text_rect.width() + 10: painter.drawText(abbreviation_x, abbreviation_y, abbreviation_text)
            current_y_offset_in_played_section += actual_row_height_played

        painter.setPen(QPen(QColor("#555"), 1))
        painter.setBrush(QColor("#282c34"))
        painter.drawRect(0, int(active_bar_y), w, int(active_section_height))
        static_red_line_x = w // 8
        if self.active_segment_index != -1 and 0 <= self.active_segment_index < len(self.media_segments):
            active_segment = self.media_segments[self.active_segment_index]
            segment_width = self.lua.execute(f"return calculate_segment_position({active_segment['duration'] * 1000}, {self.pixels_per_second}, 1000)")
            segment_width = int(segment_width)
            segment_width = max(segment_width, self.min_segment_width_pixels)
            timeline_offset_x_active = static_red_line_x - int(self.position * self.pixels_per_second)
            segment_color = QColor("#555555")
            if active_segment['type'] == 'audio' or active_segment['type'] == 'recorded_audio': segment_color = QColor("#777777")
            elif active_segment['type'] == 'media_archive': segment_color = QColor("#444444")
            segment_rect_height_active = active_section_height - (2 * self.segment_padding_y_active)
            segment_rect_height_active = max(1, int(segment_rect_height_active))
            painter.setPen(Qt.NoPen)
            painter.setBrush(segment_color)
            painter.drawRoundedRect(int(timeline_offset_x_active), int(active_bar_y + self.segment_padding_y_active), segment_width, segment_rect_height_active, border_radius, border_radius)
            if self.active_segment_index == self.selected_segment_index:
                painter.setPen(QPen(QColor("#007bff"), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(int(timeline_offset_x_active), int(active_bar_y + self.segment_padding_y_active), segment_width, segment_rect_height_active, border_radius, border_radius)
            painter.setFont(QFont("Arial", 12))
            painter.setPen(QColor("black"))
            fm = painter.fontMetrics()
            abbreviation_text = f"{active_segment['abbreviation']} ({active_segment['formatted_duration_ms']})"
            abbreviation_text_rect = fm.boundingRect(abbreviation_text)
            abbreviation_x = int(timeline_offset_x_active + (segment_width - abbreviation_text_rect.width()) // 2)
            abbreviation_y = int(active_bar_y + self.segment_padding_y_active + (segment_rect_height_active / 2) + (fm.ascent() / 2))
            if segment_width > abbreviation_text_rect.width() + 10: painter.drawText(abbreviation_x, abbreviation_y, abbreviation_text)
            painter.setPen(QPen(QColor("#444"), 0.5))
            for ms_marker in range(0, int(active_segment['duration'] * 1000) + 100, 100):
                marker_x = int(timeline_offset_x_active + (ms_marker / 1000.0) * self.pixels_per_second)
                if -50 < marker_x < w + 50: painter.drawLine(marker_x, int(active_bar_y), marker_x, int(active_bar_y + active_section_height))
            pen = QPen(QColor("red"), 1)
            painter.setPen(pen)
            painter.drawLine(int(static_red_line_x), int(active_bar_y), int(static_red_line_x), int(active_bar_y + active_section_height))

        painter.setPen(QPen(QColor("#555"), 1))
        painter.setBrush(QColor("#222"))
        painter.drawRect(0, int(upcoming_bar_y), w, int(upcoming_section_height))
        actual_row_height_upcoming = upcoming_section_height / max(1, num_upcoming_segments) if num_upcoming_segments > 0 else self.row_height_played_upcoming
        actual_segment_rect_height_upcoming = actual_row_height_upcoming - (2 * self.segment_padding_y_played_upcoming)
        actual_segment_rect_height_upcoming = max(1, int(actual_segment_rect_height_upcoming))
        current_y_offset_in_upcoming_section = 0
        for i in range(self.active_segment_index + 1, len(self.media_segments)):
            if current_y_offset_in_upcoming_section + actual_row_height_upcoming > upcoming_section_height: break
            segment = self.media_segments[i]
            segment_top = upcoming_bar_y + current_y_offset_in_upcoming_section + self.segment_padding_y_played_upcoming
            segment_width = int(segment['duration'] * self.pixels_per_second)
            segment_width = max(segment_width, self.min_segment_width_pixels)
            segment_color = QColor("#555555")
            if segment['type'] == 'audio' or segment['type'] == 'recorded_audio': segment_color = QColor("#777777")
            elif segment['type'] == 'media_archive': segment_color = QColor("#444444")
            painter.setPen(Qt.NoPen)
            painter.setBrush(segment_color)
            painter.drawRoundedRect(self.line_number_width + self.segment_gap_x, int(segment_top), segment_width, actual_segment_rect_height_upcoming, border_radius, border_radius)
            if i == self.selected_segment_index:
                painter.setPen(QPen(QColor("#007bff"), 2))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(self.line_number_width + self.segment_gap_x, int(segment_top), segment_width, actual_segment_rect_height_upcoming, border_radius, border_radius)
            painter.setFont(QFont("Arial", 10))
            painter.setPen(QColor("white"))
            row_number_text = str(i + 1)
            fm = painter.fontMetrics()
            row_number_text_rect = fm.boundingRect(row_number_text)
            row_number_x = (self.line_number_width - row_number_text_rect.width()) // 2
            row_number_y = int(upcoming_bar_y + current_y_offset_in_upcoming_section + (actual_row_height_upcoming / 2) + (fm.ascent() / 2))
            painter.drawText(row_number_x, row_number_y, row_number_text)
            painter.setPen(QPen(QColor("#555"), 1))
            painter.drawLine(self.line_number_width, int(upcoming_bar_y + current_y_offset_in_upcoming_section), self.line_number_width, int(upcoming_bar_y + current_y_offset_in_upcoming_section + actual_row_height_upcoming))
            painter.setFont(QFont("Arial", 10))
            painter.setPen(QColor("black"))
            abbreviation_text = f"{segment['abbreviation']} ({segment['formatted_duration_ms']})"
            abbreviation_text_rect = fm.boundingRect(abbreviation_text)
            abbreviation_x = self.line_number_width + self.segment_gap_x + 5
            abbreviation_y = int(upcoming_bar_y + current_y_offset_in_upcoming_section + self.segment_padding_y_played_upcoming + (actual_segment_rect_height_upcoming / 2) + (fm.ascent() / 2))
            if segment_width > abbreviation_text_rect.width() + 10: painter.drawText(abbreviation_x, abbreviation_y, abbreviation_text)
            current_y_offset_in_upcoming_section += actual_row_height_upcoming

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            click_x = event.x()
            click_y = event.y()
            active_section_height = self.row_height_active
            available_dynamic_height = self.height() - active_section_height
            min_dynamic_section_height = self.row_height_played_upcoming
            num_played_segments = self.active_segment_index
            num_upcoming_segments = len(self.media_segments) - (self.active_segment_index + 1)
            ideal_played_height = self.row_height_played_upcoming * max(1, num_played_segments)
            ideal_upcoming_height = self.row_height_played_upcoming * max(1, num_upcoming_segments)
            if num_played_segments == 0 and num_upcoming_segments == 0:
                played_section_height = int(available_dynamic_height / 2)
                upcoming_section_height = int(available_dynamic_height / 2)
            elif num_played_segments == 0:
                played_section_height = min_dynamic_section_height
                upcoming_section_height = available_dynamic_height - played_section_height
            elif num_upcoming_segments == 0:
                upcoming_section_height = min_dynamic_section_height
                played_section_height = available_dynamic_height - upcoming_section_height
            else:
                total_ideal_dynamic_height = ideal_played_height + ideal_upcoming_height
                if total_ideal_dynamic_height > 0:
                    played_section_height = int((ideal_played_height / total_ideal_dynamic_height) * available_dynamic_height)
                    upcoming_section_height = available_dynamic_height - played_section_height
                else:
                    played_section_height = int(available_dynamic_height / 2)
                    upcoming_section_height = int(available_dynamic_height / 2)
            played_section_height = max(1, int(played_section_height))
            upcoming_section_height = max(1, int(upcoming_section_height))
            active_section_height = max(1, int(active_section_height))
            if (played_section_height + upcoming_section_height + active_section_height) != self.height():
                diff = self.height() - (played_section_height + upcoming_section_height + active_section_height)
                if played_section_height >= upcoming_section_height and played_section_height >= active_section_height: played_section_height += diff
                elif upcoming_section_height >= played_section_height and upcoming_section_height >= active_section_height: upcoming_section_height += diff
                else: active_section_height += diff
            played_bar_y = 0
            active_bar_y = played_section_height
            upcoming_bar_y = played_section_height + active_section_height
            if click_y < active_bar_y:
                actual_row_height_played = played_section_height / max(1, num_played_segments) if num_played_segments > 0 else self.row_height_played_upcoming
                current_y_offset_in_played_section = 0
                for i in range(self.active_segment_index):
                    segment_top = played_bar_y + current_y_offset_in_played_section
                    segment_bottom = segment_top + actual_row_height_played
                    if segment_top <= click_y <= segment_bottom:
                        self.segment_selected.emit(i)
                        return
                    current_y_offset_in_played_section += actual_row_height_played
                self.set_selected_segment(-1)
            elif click_y < upcoming_bar_y:
                if self.active_segment_index != -1: self.segment_selected.emit(self.active_segment_index)
                else: self.set_selected_segment(-1)
            else:
                actual_row_height_upcoming = upcoming_section_height / max(1, num_upcoming_segments) if num_upcoming_segments > 0 else self.row_height_played_upcoming
                current_y_offset_in_upcoming_section = 0
                for i in range(self.active_segment_index + 1, len(self.media_segments)):
                    segment_top = upcoming_bar_y + current_y_offset_in_upcoming_section
                    segment_bottom = segment_top + actual_row_height_upcoming
                    if segment_top <= click_y <= segment_bottom:
                        self.segment_selected.emit(i)
                        return
                    current_y_offset_in_upcoming_section += actual_row_height_upcoming
                self.set_selected_segment(-1)

    def _show_context_menu(self, pos: QPoint):
        click_y = pos.y()
        active_section_height = self.row_height_active
        available_dynamic_height = self.height() - active_section_height
        min_dynamic_section_height = self.row_height_played_upcoming
        num_played_segments = self.active_segment_index
        num_upcoming_segments = len(self.media_segments) - (self.active_segment_index + 1)
        ideal_played_height = self.row_height_played_upcoming * max(1, num_played_segments)
        ideal_upcoming_height = self.row_height_played_upcoming * max(1, num_upcoming_segments)
        if num_played_segments == 0 and num_upcoming_segments == 0:
            played_section_height = int(available_dynamic_height / 2)
            upcoming_section_height = int(available_dynamic_height / 2)
        elif num_played_segments == 0:
            played_section_height = min_dynamic_section_height
            upcoming_section_height = available_dynamic_height - played_section_height
        elif num_upcoming_segments == 0:
            upcoming_section_height = min_dynamic_section_height
            played_section_height = available_dynamic_height - upcoming_section_height
        else:
            total_ideal_dynamic_height = ideal_played_height + ideal_upcoming_height
            if total_ideal_dynamic_height > 0:
                played_section_height = int((ideal_played_height / total_ideal_dynamic_height) * available_dynamic_height)
                upcoming_section_height = available_dynamic_height - played_section_height
            else:
                played_section_height = int(available_dynamic_height / 2)
                upcoming_section_height = int(available_dynamic_height / 2)
        played_section_height = max(1, int(played_section_height))
        upcoming_section_height = max(1, int(upcoming_section_height))
        active_section_height = max(1, int(active_section_height))
        if (played_section_height + upcoming_section_height + active_section_height) != self.height():
            diff = self.height() - (played_section_height + upcoming_section_height + active_section_height)
            if played_section_height >= upcoming_section_height and played_section_height >= active_section_height: played_section_height += diff
            elif upcoming_section_height >= played_section_height and upcoming_section_height >= active_section_height: upcoming_section_height += diff
            else: active_section_height += diff
        played_bar_y = 0
        active_bar_y = played_section_height
        upcoming_bar_y = played_section_height + active_section_height
        clicked_index = -1
        if click_y < active_bar_y:
            actual_row_height_played = played_section_height / max(1, num_played_segments) if num_played_segments > 0 else self.row_height_played_upcoming
            current_y_offset_in_played_section = 0
            for i in range(self.active_segment_index):
                segment_top = played_bar_y + current_y_offset_in_played_section
                segment_bottom = segment_top + actual_row_height_played
                if segment_top <= click_y <= segment_bottom:
                    clicked_index = i
                    break
                current_y_offset_in_played_section += actual_row_height_played
        elif click_y < upcoming_bar_y:
            clicked_index = self.active_segment_index
        else:
            actual_row_height_upcoming = upcoming_section_height / max(1, num_upcoming_segments) if num_upcoming_segments > 0 else self.row_height_played_upcoming
            current_y_offset_in_upcoming_section = 0
            for i in range(self.active_segment_index + 1, len(self.media_segments)):
                segment_top = upcoming_bar_y + current_y_offset_in_upcoming_section
                segment_bottom = segment_top + actual_row_height_upcoming
                if segment_top <= click_y <= segment_bottom:
                    clicked_index = i
                    break
                current_y_offset_in_upcoming_section += actual_row_height_upcoming
        if clicked_index != -1:
            self.set_selected_segment(clicked_index)
            menu = QMenu(self)
            move_up_action = QAction("Move Up ▲", self)
            if clicked_index > 0: move_up_action.triggered.connect(lambda: self.move_segment_request.emit(clicked_index, -1))
            else: move_up_action.setEnabled(False)
            menu.addAction(move_up_action)
            move_down_action = QAction("Move Down ▼", self)
            if clicked_index < len(self.media_segments) - 1: move_down_action.triggered.connect(lambda: self.move_segment_request.emit(clicked_index, 1))
            else: move_down_action.setEnabled(False)
            menu.addAction(move_down_action)
            menu.exec_(self.mapToGlobal(pos))
        else:
            self.set_selected_segment(-1)

class VideoRecordingThread(threading.Thread):
    def __init__(self, output_path, fourcc, fps, frame_size, frame_queue):
        super().__init__()
        self.output_path = output_path
        self.fourcc = fourcc
        self.fps = fps
        self.frame_size = frame_size
        self.frame_queue = frame_queue
        self.running = threading.Event()
        self.running.set()
        self.writer = None
        print(f"VideoRecordingThread: Starting for '{output_path}'.")

    def run(self):
        print(f"Video recording thread started. Output: '{self.output_path}'")
        try:
            self.writer = cv2.VideoWriter(self.output_path, self.fourcc, self.fps, self.frame_size)
            if not self.writer.isOpened():
                print(f"ERROR: Video writer could not be opened in thread: '{self.output_path}'")
                self.running.clear()
                return
            while self.running.is_set():
                try:
                    frame = self.frame_queue.get(timeout=0.1)
                    if frame is None:
                        print("VideoRecordingThread: Stop signal received.")
                        break
                    self.writer.write(frame)
                    self.frame_queue.task_done()
                except queue.Empty:
                    time.sleep(0.01)
                    pass
        except Exception as e:
            print(f"ERROR in video recording thread: {e}")
        finally:
            if self.writer:
                self.writer.release()
                print("Video writer released in thread.")
            print("Video recording thread stopped.")

    def stop(self):
        print("Stopping video recording thread...")
        self.running.clear()
        self.frame_queue.put(None)
        try:
            self.frame_queue.join(timeout=5)
        except RuntimeError:
            pass
        if self.is_alive():
            print("VideoRecordingThread: Still seems to be running, might be forced to stop.")

class MediaEditor(QWidget):
    def __init__(self, core_window_ref=None, parent=None):
        super().__init__(parent)
        self.core_window_ref = core_window_ref
        self.setWindowTitle("Media Timeline Player")
        self.setStyleSheet("background-color: #282c34; color: white;")

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

        # YENİ: Filtreleme özellikleri
        self.noise_filter_enabled = False
        self.filter_settings = {
            'ai_nr_enabled': True, 'noise_gate_threshold_db': -70.0,
            'hp_cutoff_hz': 150, 'lp_cutoff_hz': 10000, 'gain_db': 6.0,
            'reverb_reduction_level': 0, 'de_esser_level': 0, 'de_hum_level': 0,
            'compressor_threshold_db': 0.0, 'compressor_ratio': 3.0,
            'compressor_attack_ms': 5.0, 'compressor_release_ms': 150.0,
            'eq_gain_db': 0.0, 'eq_freq_hz': 1000.0, 'eq_q': 1.0,
        }
        self.load_filter_settings() # Ayarları dosyadan yükle

        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.load_lua_scripts()

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

        self.player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.player.setVideoOutput(self.video_widget)
        self.player.setPlaybackRate(1.0)
        self.player.stateChanged.connect(self._handle_player_state_changed)
        self.player.error.connect(self._handle_player_error)

        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.update_position)

        self.media_save_dir = SAVE_DIR
        self.audio_record_dir = AUDIO_SAVE_DIR
        self._ensure_dirs_exist()

        self.media_engine = None
        try:
            self.media_engine = ctypes.CDLL(LIB_PATH)
            # ... (ctypes function bindings)
            self.media_engine.init_lua_engine.restype = ctypes.c_int
            self.media_engine.close_lua_engine.restype = None
            self.media_engine.call_lua_segment_calculation.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double]
            self.media_engine.call_lua_segment_calculation.restype = ctypes.c_double
            lua_init_result = self.media_engine.init_lua_engine()
            if lua_init_result != 0: self.show_message_box("Error", f"Lua engine could not be initialized. Error code: {lua_init_result}")
            self.media_engine.init_audio_engine.restype = ctypes.c_int
            self.media_engine.terminate_audio_engine.restype = ctypes.c_int
            self.media_engine.start_audio_record.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.start_audio_record.restype = ctypes.c_int
            self.media_engine.stop_audio_record.restype = ctypes.c_int
            self.media_engine.merge_audio_files.argtypes = [ctypes.c_char_p]
            self.media_engine.merge_audio_files.restype = ctypes.c_int
            self.media_engine.start_camera_record.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
            self.media_engine.start_camera_record.restype = ctypes.c_bool
            self.media_engine.stop_camera_record.restype = None
            self.media_engine.is_camera_open.restype = ctypes.c_bool
            self.media_engine.read_frame.argtypes = [ctypes.POINTER(Frame)]
            self.media_engine.read_frame.restype = ctypes.c_bool
            self.media_engine.get_frame_width.restype = ctypes.c_int
            self.media_engine.get_frame_height.restype = ctypes.c_int
            self.media_engine.free_frame_data.argtypes = [ctypes.POINTER(Frame)]
            self.media_engine.free_frame_data.restype = None
            self.media_engine.cut_media_segment.argtypes = [ctypes.c_char_p, ctypes.c_longlong, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.cut_media_segment.restype = ctypes.c_int
            self.media_engine.delete_media_file.argtypes = [ctypes.c_char_p]
            self.media_engine.delete_media_file.restype = ctypes.c_int
            self.media_engine.get_media_duration_ms.argtypes = [ctypes.c_char_p]
            self.media_engine.get_media_duration_ms.restype = ctypes.c_longlong
            self.media_engine.archive_segments.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.archive_segments.restype = ctypes.c_int
            self.media_engine.extract_segments.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.extract_segments.restype = ctypes.c_int
            self.media_engine.merge_timeline_to_video.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.merge_timeline_to_video.restype = ctypes.c_int
            init_result = self.media_engine.init_audio_engine()
            if init_result != 0: self.show_message_box("Error", f"PortAudio initialization failed. Error code: {init_result}")
        except OSError as e:
            self.show_message_box("Error", f"Could not load libmediaengine.so: {e}. Ensure it's compiled and in the correct path.")
            self.media_engine = None
        except AttributeError as e:
            self.show_message_box("Error", f"Could not load Media Engine functions: {e}. Are there missing functions in the library?")
            self.media_engine = None

        self.is_recording = False
        self.is_camera_mode_selected = False
        self.is_audio_mode_selected = False
        self.is_stopping_audio_recording = False

        self.video_record_path = None
        self.audio_record_final_path = None

        self.video_frame_queue = queue.Queue(maxsize=60)
        self.video_record_thread = None

        self.camera_timer = QTimer()
        self.camera_timer.setInterval(30)
        self.camera_timer.timeout.connect(self.update_camera_frame)

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

    # YENİ: Filtreleme ile ilgili metodlar (camera_editor.py'den kopyalandı)
    def load_filter_settings(self):
        """Filtre ayarlarını JSON dosyasından yükler."""
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings_from_file = json.load(f)
                self.filter_settings.update(settings_from_file)
                print(f"Python: Filtre ayarları {SETTINGS_FILE} dosyasından yüklendi.")
        except FileNotFoundError:
            print(f"Python: Ayar dosyası '{SETTINGS_FILE}' bulunamadı. Varsayılan ayarlar kullanılacak.")
            self.save_filter_settings()
        except json.JSONDecodeError:
            print(f"Python: Ayar dosyası '{SETTINGS_FILE}' bozuk. Varsayılan ayarlar kullanılacak.")
        except Exception as e:
            print(f"Python: Ayarlar yüklenirken bir hata oluştu: {e}")

    def save_filter_settings(self):
        """Mevcut filtre ayarlarını JSON dosyasına kaydeder."""
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.filter_settings, f, indent=4)
            print(f"Python: Filtre ayarları {SETTINGS_FILE} dosyasına kaydedildi.")
        except Exception as e:
            print(f"Python: Ayarlar kaydedilirken bir hata oluştu: {e}")

    def _apply_python_audio_filter(self, input_wav_path, progress_dialog):
        """
        filtre.py'den alınan mantıkla ses dosyasına filtreler uygular.
        """
        try:
            s = self.filter_settings
            output_wav_path = input_wav_path.replace('.wav', '_filtered.wav')

            progress_dialog.setLabelText("Reading audio data...")
            QApplication.processEvents()
            data, rate = sf.read(input_wav_path)
            if data.ndim > 1: data = data.mean(axis=1)
            processed = data.copy()
            original_num_samples = len(data)

            gain_db = s.get('gain_db', 0.0)
            if gain_db != 0.0:
                progress_dialog.setLabelText(f"Applying Gain: {gain_db}dB")
                QApplication.processEvents()
                processed *= 10 ** (gain_db / 20.0)

            hp_cutoff = s.get('hp_cutoff_hz', 0)
            if hp_cutoff > 0:
                progress_dialog.setLabelText(f"High-Pass Filter: {hp_cutoff}Hz")
                QApplication.processEvents()
                nyquist = 0.5 * rate
                normalized_cutoff = hp_cutoff / nyquist
                b, a = sig.butter(4, normalized_cutoff, btype='highpass', analog=False)
                processed = sig.filtfilt(b, a, processed)

            lp_cutoff = s.get('lp_cutoff_hz', 0)
            if lp_cutoff > 0:
                progress_dialog.setLabelText(f"Low-Pass Filter: {lp_cutoff}Hz")
                QApplication.processEvents()
                nyquist = 0.5 * rate
                normalized_cutoff = lp_cutoff / nyquist
                b, a = sig.butter(4, normalized_cutoff, btype='lowpass', analog=False)
                processed = sig.filtfilt(b, a, processed)

            threshold_db = s.get('noise_gate_threshold_db', -999)
            if threshold_db > -990:
                progress_dialog.setLabelText(f"Applying Noise Gate: {threshold_db}dB")
                QApplication.processEvents()
                threshold_linear = 10 ** (threshold_db / 20.0)
                processed[np.abs(processed) < threshold_linear] = 0

            de_hum_level = s.get('de_hum_level', 0)
            if de_hum_level > 0:
                q_map = {1: 10.0, 2: 30.0, 3: 60.0}
                q_val = q_map.get(de_hum_level, 30.0)
                progress_dialog.setLabelText(f"Applying De-Hum: Level={de_hum_level}")
                QApplication.processEvents()
                for freq in [50, 60]:
                    b, a = sig.iirnotch(freq, q_val, fs=rate)
                    processed = sig.filtfilt(b, a, processed)

            de_esser_level = s.get('de_esser_level', 0)
            if de_esser_level > 0:
                gain_map = {1: -3.0, 2: -6.0, 3: -9.0}
                gain_db = gain_map.get(de_esser_level, 0.0)
                progress_dialog.setLabelText(f"Applying De-Esser: Level={de_esser_level}")
                QApplication.processEvents()
                b, a = sig.butter(2, 6000, btype='high', fs=rate, analog=False)
                high_freqs = sig.filtfilt(b, a, processed)
                reduction_factor = 10 ** (gain_db / 20.0)
                processed = processed - high_freqs + (high_freqs * reduction_factor)

            reverb_level = s.get('reverb_reduction_level', 0)
            if reverb_level > 0:
                level_map = {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4}
                strength = level_map.get(reverb_level, 0)
                progress_dialog.setLabelText(f"Reverb Reduction: Level={reverb_level}")
                QApplication.processEvents()
                processed = librosa.effects.preemphasis(processed, coef=0.97 - strength)

            comp_threshold_db = s.get('compressor_threshold_db', 0.0)
            if comp_threshold_db != 0.0:
                ratio = s.get('compressor_ratio', 1.0)
                attack = s.get('compressor_attack_ms', 5.0)
                release = s.get('compressor_release_ms', 100.0)
                progress_dialog.setLabelText(f"Compressor: {comp_threshold_db}dB, {ratio}:1")
                QApplication.processEvents()
                processed_int16 = (processed * 32767).astype(np.int16)
                audio_segment = AudioSegment(processed_int16.tobytes(), frame_rate=rate, sample_width=processed_int16.dtype.itemsize, channels=1)
                compressed_segment = compress_dynamic_range(audio_segment, threshold=comp_threshold_db, ratio=ratio, attack=attack, release=release)
                processed = np.array(compressed_segment.get_array_of_samples(), dtype=np.float32) / 32767.0

            eq_gain_db = s.get('eq_gain_db', 0.0)
            if eq_gain_db != 0.0:
                eq_freq = s.get('eq_freq_hz', 1000.0)
                eq_q = s.get('eq_q', 1.0)
                progress_dialog.setLabelText(f"Parametric EQ: {eq_gain_db}dB @ {eq_freq}Hz")
                QApplication.processEvents()
                b, a = sig.iirpeak(eq_freq, eq_q, fs=rate)
                g = 10.0 ** (eq_gain_db / 20.0)
                b_gained = b * g if eq_gain_db > 0 else b / abs(g)
                processed = sig.lfilter(b_gained, a, processed)

            if s.get('ai_nr_enabled', False):
                progress_dialog.setLabelText("Applying AI Noise Reduction...")
                QApplication.processEvents()
                processed = nr.reduce_noise(y=processed, sr=rate, prop_decrease=1.0, freq_mask_smooth_hz=500, time_mask_smooth_ms=100)

            if len(processed) < original_num_samples:
                padding = np.zeros(original_num_samples - len(processed))
                processed = np.concatenate((processed, padding))
            elif len(processed) > original_num_samples:
                processed = processed[:original_num_samples]

            progress_dialog.setLabelText("Saving processed audio...")
            QApplication.processEvents()
            sf.write(output_wav_path, processed, rate)
            return output_wav_path
        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"Python audio filtering error: {e}")

    def showAdvancedFilterDialog(self, pos):
        """Filtre butonu sağ tıklandığında çağrılır."""
        if AUDIO_LIBS_MISSING:
            show_missing_libs_error(self)
            return
        dialog = AdvancedFilterDialog(initial_settings=self.filter_settings, parent=self)
        global_pos = self.noise_filter_button.mapToGlobal(QPoint(0, self.noise_filter_button.height()))
        dialog.move(global_pos)
        if dialog.exec_():
            self.filter_settings = dialog.getSettings()
            self.save_filter_settings()
            print(f"Python: Gürültü filtresi ayarları güncellendi ve kaydedildi.")

    def toggleNoiseFilter(self):
        """Gürültü filtresi durumunu değiştirir ve butonun stilini günceller."""
        if AUDIO_LIBS_MISSING:
            show_missing_libs_error(self)
            self.noise_filter_enabled = False
            self.noise_filter_button.setStyleSheet(self.buttonStylePressure(self.noise_filter_enabled))
            return

        self.noise_filter_enabled = not self.noise_filter_enabled
        self.noise_filter_button.setStyleSheet(self.buttonStylePressure(self.noise_filter_enabled))
        print(f"Python: Gürültü filtresi {'etkin' if self.noise_filter_enabled else 'devre dışı'}.")

    def buttonStylePressure(self, is_active: bool) -> str:
        """Gürültü filtresi butonu için stil döndürür."""
        if is_active:
            return """
                QPushButton {
                    background-color: #555; /* Gray */ color: white;
                    font-size: 14px; font-weight: bold; border: 2px solid #555;
                    border-radius: 8px; padding: 5px;
                }
                QPushButton:hover { background-color: #666; }
                QPushButton:pressed { background-color: #777; }
            """
        else:
            return """
                QPushButton {
                    background-color: transparent; color: white;
                    font-size: 14px; font-weight: bold; border: 2px solid #555;
                    border-radius: 8px; padding: 5px;
                }
                QPushButton:hover { background-color: #444; }
                QPushButton:pressed { background-color: #666; }
            """

    def load_lua_scripts(self):
        try:
            # --- GÜNCELLEME: Lua script yolu resource_path ile dinamik hale getirildi ---
            with open(resource_path('timeline_logic.lua'), 'r') as f:
                self.lua.execute(f.read())
            print("Lua script loaded successfully: timeline_logic.lua")
        except Exception as e:
            print(f"Error loading Lua script: {e}")
            self.show_message_box("Error", f"Error loading Lua script: {e}")

    def _handle_player_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.is_playing = True
            self.play_pause_btn.setText("Pause")
            self.timer.start()
        elif state == QMediaPlayer.PausedState:
            self.is_playing = False
            self.play_pause_btn.setText("Play")
            self.timer.stop()
        elif state == QMediaPlayer.StoppedState:
            self.is_playing = False
            self.play_pause_btn.setText("Play")
            self.timer.stop()
            if self.is_sequence_play_active and \
               self.current_media_index != -1 and \
               self.player.duration() > 0 and \
               self.player.position() >= self.player.duration() - 50:
                print(f"Segment {self.current_media_index} ended in sequence mode. Advancing to next segment.")
                self._advance_to_next_segment()
            else:
                print("Playback stopped (StoppedState).")

    def _handle_player_error(self, error):
        error_string = self.player.errorString()
        print(f"QMediaPlayer Error: {error_string} (Code: {error})")
        self.show_message_box("Playback Error", f"An error occurred during media playback: {error_string}")
        self.stop_media()

    def _ensure_dirs_exist(self):
        QDir().mkpath(self.media_save_dir)
        QDir().mkpath(self.audio_record_dir)
        print(f"Media save directory created/exists: {self.media_save_dir}")
        print(f"Audio record directory created/exists: {self.audio_record_dir}")

    def buttonStyle(self, button_type: str = "default") -> str:
        base_style = """
            QPushButton {
                background-color: transparent; color: white; font-size: 14px;
                font-weight: bold; border: 2px solid #555; border-radius: 8px;
                padding: 5px 15px;
            }
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
                QPushButton {
                    background-color: #6c757d; color: white; border: 2px solid #545b62;
                    padding: 5px 5px; font-size: 14px; font-weight: bold;
                }
                QPushButton:hover { background-color: #5a6268; }
                QPushButton:pressed { background-color: #494f54; }
            """
        elif button_type == "sequence_toggle":
            return base_style + """
                QPushButton {
                    background-color: transparent; color: white; border: 2px solid #555;
                    padding: 5px 5px; font-size: 14px; font-weight: bold;
                }
                QPushButton:hover { background-color: #444; border-color: #777; }
                QPushButton:pressed { background-color: #666; border-color: #999; }
            """
        elif button_type == "combobox_style":
            return """
                QComboBox {
                    background-color: transparent; color: white; border: 2px solid #555;
                    border-radius: 8px; padding: 5px 15px; font-size: 14px; font-weight: bold;
                }
                QComboBox::drop-down { border: none; width: 0px; }
                QComboBox::down-arrow { image: none; }
                QComboBox:hover { background-color: #444; border-color: #777; }
                QComboBox:pressed { background-color: #666; border-color: #999; }
                QComboBox QAbstractItemView {
                    background-color: #282c34; color: white;
                    selection-background-color: #007bff; border: 1px solid #555;
                }
            """
        return base_style

    def buttonStyleMini(self):
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 16px;
                border: 2px solid #555; border-radius: 8px; padding: 5px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.toolbar_frame = QFrame(self)
        self.toolbar_frame.setStyleSheet("background-color: #222; border-bottom: 1px solid #555;")
        self.toolbar_frame.setFixedHeight(40)

        top_buttons_layout = QHBoxLayout(self.toolbar_frame)
        top_buttons_layout.setContentsMargins(10, 5, 10, 5)
        top_buttons_layout.setSpacing(10)

        self.file_btn = QPushButton("File")
        self.file_btn.clicked.connect(self.select_media_files)
        self.file_btn.setStyleSheet(self.buttonStyle("file"))
        self.file_btn.setFixedSize(90, 30)
        top_buttons_layout.addWidget(self.file_btn)

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
        self.play_pause_btn.setStyleSheet(self.buttonStyle("play"))
        self.play_pause_btn.setFixedSize(90, 30)
        top_buttons_layout.addWidget(self.play_pause_btn)

        self.sequence_play_btn = QPushButton("/")
        self.sequence_play_btn.clicked.connect(self._toggle_sequence_play_mode)
        self.sequence_play_btn.setStyleSheet(self.buttonStyle("sequence_toggle"))
        self.sequence_play_btn.setFixedSize(30, 30)
        top_buttons_layout.addWidget(self.sequence_play_btn)

        self.cut_btn = QPushButton("Cut")
        self.cut_btn.clicked.connect(self.cut_media)
        self.cut_btn.setStyleSheet(self.buttonStyle("default"))
        self.cut_btn.setFixedSize(80, 30)
        top_buttons_layout.addWidget(self.cut_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self.delete_selected_media)
        self.delete_btn.setStyleSheet(self.buttonStyle("default"))
        self.delete_btn.setFixedSize(90, 30)
        top_buttons_layout.addWidget(self.delete_btn)

        self.camera_mode_btn = QPushButton("Camera")
        self.camera_mode_btn.clicked.connect(self._handle_camera_button_click)
        self.camera_mode_btn.setStyleSheet(self.buttonStyle("default"))
        self.camera_mode_btn.setFixedSize(90, 30)
        top_buttons_layout.addWidget(self.camera_mode_btn)

        self.audio_mode_btn = QPushButton("Sound")
        self.audio_mode_btn.clicked.connect(self._toggle_audio_mode_selection)
        self.audio_mode_btn.setStyleSheet(self.buttonStyle("default"))
        self.audio_mode_btn.setFixedSize(80, 30)
        top_buttons_layout.addWidget(self.audio_mode_btn)

        # YENİ FİLTRE BUTONU
        self.noise_filter_button = QPushButton("|")
        self.noise_filter_button.setToolTip("Noise Reduction (Left Click: On/Off, Right Click: Settings)")
        self.noise_filter_button.setStyleSheet(self.buttonStylePressure(self.noise_filter_enabled))
        self.noise_filter_button.setFixedSize(30, 30)
        self.noise_filter_button.clicked.connect(self.toggleNoiseFilter)
        self.noise_filter_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.noise_filter_button.customContextMenuRequested.connect(self.showAdvancedFilterDialog)
        top_buttons_layout.addWidget(self.noise_filter_button)

        self.seek_interval_box = QComboBox()
        all_seek_options = {**self.millisecond_seek_intervals, **self.seek_intervals}
        sorted_seek_options_keys = sorted(all_seek_options.keys(), key=lambda x: (all_seek_options[x], x))
        self.seek_interval_box.addItems(sorted_seek_options_keys)
        self.seek_interval_box.setCurrentText('2s')
        self.seek_interval_box.setFixedSize(84, 30)
        self.seek_interval_box.setStyleSheet(self.buttonStyle("combobox_style"))
        self.seek_interval_box.currentTextChanged.connect(self.change_seek_interval)
        top_buttons_layout.addWidget(self.seek_interval_box)

        self.playback_speed_box = QComboBox()
        self.playback_speed_options = ["0.01","0.1", "0.25", "0.5", "1", "1.25", "1.5", "1.75", "2"]
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

        separator_label = QLabel(" / ")
        separator_label.setStyleSheet("color: white; font-size: 12px; font-weight: normal;")
        top_buttons_layout.addWidget(separator_label)

        self.total_time_label = QLabel("00:00:00.000")
        self.total_time_label.setStyleSheet("color: white; font-size: 12px; font-weight: normal;")
        top_buttons_layout.addWidget(self.total_time_label)

        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.export_media_archive)
        self.export_btn.setStyleSheet(self.buttonStyle("default"))
        self.export_btn.setFixedSize(90, 30)
        top_buttons_layout.addWidget(self.export_btn)

        self.media_btn = QPushButton("Media")
        self.media_btn.setStyleSheet(self.buttonStyle("default"))
        self.media_btn.clicked.connect(self.triggerCoreSwitcher)
        self.media_btn.setFixedSize(90, 30)
        top_buttons_layout.addWidget(self.media_btn)

        main_layout.addWidget(self.toolbar_frame)

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

        self.timeline = TimelineBar(self.lua)
        self.timeline.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding)
        self.timeline.setMinimumHeight(120)
        self.timeline.segment_selected.connect(self._on_timeline_segment_selected)

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.video_frame)
        self.splitter.addWidget(self.timeline)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #555;}")

        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)
        self._update_undo_redo_buttons()

        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self.redo)

    def closeEvent(self, event):
        self._stop_all_recording_processes()
        if self.player.state() != QMediaPlayer.StoppedState: self.player.stop()
        self.player.setMedia(QMediaContent())
        if self.media_engine:
            self.media_engine.terminate_audio_engine()
            self.media_engine.close_lua_engine()
            print("PortAudio and Lua engine terminated on exit.")
        if os.path.exists(self.media_save_dir) and len(os.listdir(self.media_save_dir)) > 0:
            reply = QMessageBox.question(self, 'Exit Confirmation',
                                         f"Do you want to delete the media files folder?\nFolder: {self.media_save_dir}",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                try:
                    shutil.rmtree(self.media_save_dir)
                    print(f"Media directory successfully deleted: {self.media_save_dir}")
                except OSError as e:
                    print(f"Error: An error occurred while deleting the media directory: {e}")
            event.accept()
        else:
            event.accept()
        if os.path.exists(self.audio_record_dir) and len(os.listdir(self.audio_record_dir)) > 0:
            print(f"Cleaning up remaining audio segment files: {self.audio_record_dir}")
            try:
                for f in os.listdir(self.audio_record_dir):
                    if re.match(r"recorded_audio_segment_\d+\.wav$", f):
                        os.remove(os.path.join(self.audio_record_dir, f))
                print(f"Temporary audio segment files successfully cleaned up: {self.audio_record_dir}")
            except OSError as e:
                print(f"Error: An error occurred while cleaning the audio temporary directory: {e}")

    # ... (Diğer metodlar buraya gelecek, değişiklik yok)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.active_message_box and self.active_message_box.isVisible():
                self.active_message_box.done(QMessageBox.Yes)
                self.active_message_box = None
                event.accept()
                return
        if event.key() == Qt.Key_F:
            self.toggle_fullscreen()
            event.accept()
            return
        if self.current_media_index != -1:
            current_segment = self.media_queue[self.current_media_index]
            current_position_in_segment_ms = int(self.position * 1000)
            current_playback_rate = self.player.playbackRate()
            effective_frame_seek_step_sec = self.frame_seek_step_sec / current_playback_rate if current_playback_rate != 0 else self.frame_seek_step_sec
            new_position_in_segment_ms = current_position_in_segment_ms
            if event.key() == Qt.Key_Left:
                new_position_in_segment_ms = max(0, current_position_in_segment_ms - int(effective_frame_seek_step_sec * 1000))
            elif event.key() == Qt.Key_Right:
                new_position_in_segment_ms = min(int(current_segment['duration'] * 1000), current_position_in_segment_ms + int(effective_frame_seek_step_sec * 1000))
            if new_position_in_segment_ms != current_position_in_segment_ms:
                self.position = new_position_in_segment_ms / 1000.0
                self.paused_position = self.position
                self.player.setPosition(int(self.position * 1000))
                QApplication.processEvents()
                self.timeline.set_position(self.position)
                self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
                event.accept()
                return
        if event.key() == Qt.Key_Space:
            if self.is_playing: self.toggle_play_pause()
            else: self._advance_to_next_segment()
        elif event.key() == Qt.Key_L and event.modifiers() == Qt.ControlModifier:
            if self.current_media_index != -1:
                self.stop_media()
                self.position = 0
                self.paused_position = 0
                self._set_media_to_player(self.current_media_index)
                self.player.setPosition(0)
                self.timeline.set_position(self.position)
                self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        elif event.key() == Qt.Key_Delete: self.delete_selected_media()
        elif event.key() == Qt.Key_Z and event.modifiers() == Qt.ControlModifier: self.undo()
        elif event.key() == Qt.Key_Z and event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier): self.redo()
        else: super().keyPressEvent(event)

    def keyReleaseEvent(self, event): super().keyReleaseEvent(event)
    def triggerCoreSwitcher(self):
        main_window = self.window()
        if hasattr(main_window, 'showSwitcher'): main_window.showSwitcher()
        print("Python: MEDIA button clicked, showSwitcher called.")
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
        total_milliseconds = int(total_seconds * 1000)
        h = int(total_milliseconds // 3600000); total_milliseconds %= 3600000
        m = int(total_milliseconds // 60000); total_milliseconds %= 60000
        s = int(total_milliseconds // 1000); ms = int(total_milliseconds % 1000)
        return f"{h:02d}{m:02d}{s:02d}_{ms:03d}"
    @staticmethod
    def format_time_display(total_seconds):
        total_milliseconds = int(total_seconds * 1000)
        h = int(total_milliseconds // 3600000); total_milliseconds %= 3600000
        m = int(total_milliseconds // 60000); total_milliseconds %= 60000
        s = int(total_milliseconds // 1000)
        return f"{h:02d}:{m:02d}:{s:02d}"
    @staticmethod
    def format_time_display_with_ms(total_seconds):
        total_milliseconds = int(total_seconds * 1000)
        ms_digit = int(total_milliseconds / 100) % 10
        h = int(total_milliseconds // 3600000); total_milliseconds %= 3600000
        m = int(total_milliseconds // 60000); total_milliseconds %= 60000
        s = int(total_milliseconds // 1000)
        return f"{h:02d}:{m:02d}:{s:02d}.{ms_digit:01d}"
    def get_duration_from_path(self, path):
        duration_ms = -1
        if self.media_engine:
            try: duration_ms = self.media_engine.get_media_duration_ms(path.encode('utf-8'))
            except Exception as e:
                print(f"C++ get_media_duration_ms çağrılırken hata: {e}")
                duration_ms = -1
        if duration_ms != -1: return duration_ms / 1000.0
        else:
            temp_player = QMediaPlayer()
            temp_player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
            timeout_ms = 5000; start_time = time.time()
            while temp_player.duration() <= 0 and (time.time() - start_time) * 1000 < timeout_ms:
                QApplication.processEvents(); time.sleep(0.01)
            duration = temp_player.duration() / 1000.0
            temp_player.setMedia(QMediaContent())
            return duration if duration > 0 else -1
    def get_file_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.rec']: return 'video'
        elif ext in ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.saund']: return 'audio'
        elif ext == '.media':
            try:
                with open(path, 'rb') as f:
                    header = f.read(263)
                    if len(header) >= 2 and header[0] == 0x1f and header[1] == 0x8b: return 'media_archive'
            except Exception as e: print(f"Error checking .media file header: {e}")
            return 'unknown'
        return 'unknown'
    def add_media_to_queue(self, path, media_type, original_name=None):
        duration = self.get_duration_from_path(path)
        if duration == -1:
            self.show_message_box("Error", f"'{os.path.basename(path)}' dosyası için süre alınamadı. Desteklenmeyen format veya bozuk dosya.")
            return False
        prefix_char = ''
        if media_type == 'audio' or media_type == 'recorded_audio': prefix_char = 's'
        elif media_type == 'video' or media_type == 'recorded_video': prefix_char = 'v'
        elif media_type == 'media_archive': prefix_char = 'm'
        else:
            self.show_message_box("Error", f"Bilinmeyen medya türü: '{os.path.basename(path)}'.")
            return False
        existing_numbers = set()
        for segment in self.media_queue:
            if segment['abbreviation'].startswith(prefix_char):
                match = re.match(r'{}(\d+)(?:\.\d+)?$'.format(prefix_char), segment['abbreviation'])
                if match: existing_numbers.add(int(match.group(1)))
        current_sequence_num = (max(existing_numbers) if existing_numbers else 0) + 1
        abbreviation = f"{prefix_char}{current_sequence_num}"
        formatted_duration_str_for_filename = self.format_time(duration)
        original_ext = os.path.splitext(path)[1].lower()
        new_filename_imported = f"{abbreviation}_{formatted_duration_str_for_filename}{original_ext}"
        dest_path_imported = os.path.join(self.media_save_dir, new_filename_imported)
        try:
            shutil.copy2(path, dest_path_imported)
            new_segment_data = {
                'path': dest_path_imported, 'type': media_type, 'duration': duration,
                'abbreviation': abbreviation, 'original_name_prefix': original_name,
                'formatted_duration': self.format_time_display(duration),
                'formatted_duration_ms': self.format_time_display_with_ms(duration),
                'original_ext': original_ext, 'id': str(time.time()) + str(current_sequence_num),
                'is_cut_point': False
            }
            self.stop_media(); self.is_sequence_play_active = False; self._update_sequence_play_button_state()
            if self.current_media_index == -1 or not self.media_queue:
                self.media_queue.append(new_segment_data)
                self.current_media_index = len(self.media_queue) - 1
            else:
                current_segment = self.media_queue[self.current_media_index]
                EPSILON_POSITION = 0.05
                if self.position < EPSILON_POSITION:
                    self.media_queue.insert(self.current_media_index, new_segment_data)
                    self.current_media_index += 1
                elif self.position >= current_segment['duration'] - EPSILON_POSITION:
                    self.media_queue.insert(self.current_media_index + 1, new_segment_data)
                    self.current_media_index += 1
                else:
                    original_segment_index_before_cut = self.current_media_index
                    cut_point_for_active_segment = self.position
                    temp_new_segment_data = new_segment_data
                    part1_after_cut, part2_after_cut = self._perform_cut_at_position(original_segment_index_before_cut, cut_point_for_active_segment)
                    if part1_after_cut or part2_after_cut:
                        insert_point_for_new_segment = self.current_media_index + 1
                        self.media_queue.insert(insert_point_for_new_segment, temp_new_segment_data)
                        self.current_media_index = insert_point_for_new_segment
                    else:
                        self.media_queue.append(new_segment_data)
                        self.current_media_index = len(self.media_queue) - 1
                        self.show_message_box("Warning", "Otomatik kesme işlemi başarısız oldu. Yeni segment zaman çizelgesinin sonuna eklendi.")
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_position(self.position)
            self.timeline.set_selected_segment(self.current_media_index)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            self.update_total_duration_label()
            self._save_state()
            if self.current_media_index != -1:
                self._set_media_to_player(self.current_media_index)
                self.player.setPosition(int(self.position * 1000))
            return True
        except IOError as e:
            self.show_message_box("Error", f"Error copying file: {os.path.basename(path)}")
            return False
    def select_media_files(self):
        all_video_formats = "*.mp4 *.avi *.mov *.mkv *.webm *.flv *.rec"
        all_audio_formats = "*.mp3 *.wav *.ogg *.flac *.aac *.m4a *.saund"
        custom_archive_formats = "*.media"
        filter_str = f"All Supported Media ({all_video_formats} {all_audio_formats} {custom_archive_formats});;Media Archives ({custom_archive_formats});;Video Files ({all_video_formats});;Audio Files ({all_audio_formats});;All Files (*)"
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Media Files", DEFAULT_BASE_DIR, filter_str)
        if not file_paths: return
        total_files = len(file_paths)
        if total_files == 0: return
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Importing Media")
        progress_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        progress_dialog.setAttribute(Qt.WA_DeleteOnClose)
        progress_dialog.setStyleSheet("QDialog { background-color: #3f3f3f; border: 2px solid #007bff; border-radius: 8px; } QLabel { color: #ffffff; font-size: 14px; padding: 5px; } QProgressBar { border: 2px solid #555; border-radius: 5px; background-color: #2e2e2e; text-align: center; color: white; } QProgressBar::chunk { background-color: #007bff; border-radius: 4px; }")
        dialog_layout = QVBoxLayout(progress_dialog)
        dialog_layout.setContentsMargins(20, 20, 20, 20)
        import_label = QLabel("Importing files...")
        dialog_layout.addWidget(import_label)
        self.import_progress_bar = QProgressBar(progress_dialog)
        self.import_progress_bar.setRange(0, 100)
        self.import_progress_bar.setValue(0)
        dialog_layout.addWidget(self.import_progress_bar)
        self.import_status_label = QLabel("Starting import...")
        dialog_layout.addWidget(self.import_status_label)
        progress_dialog.show()
        QApplication.processEvents()
        added_count = 0
        for i, original_path in enumerate(file_paths):
            media_type = self.get_file_type(original_path)
            original_filename_no_ext = os.path.splitext(os.path.basename(original_path))[0]
            import_label.setText("Importing file...")
            self.import_progress_bar.setValue(int(((i + 1) / total_files) * 100))
            self.import_status_label.setText(f"Processing file {i+1} / {total_files}...")
            QApplication.processEvents(); time.sleep(0.01)
            if media_type == 'media_archive':
                self.stop_media(); self.media_queue.clear(); self.current_media_index = -1; self.position = 0; self.paused_position = 0
                self.timeline.set_media_segments(self.media_queue, self.current_media_index)
                self.timeline.set_selected_segment(self.current_media_index)
                self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
                self.update_total_duration_label(); self._save_state()
                if self._process_media_archive(original_path): added_count += 1
            elif media_type != 'unknown':
                if self.add_media_to_queue(original_path, media_type, original_filename_no_ext): added_count += 1
            else: self.show_message_box("Warning", f"Bilinmeyen dosya türü veya geçersiz medya arşivi atlandı: {os.path.basename(original_path)}")
        self.import_progress_bar.setValue(100)
        self.import_status_label.setText("Import complete!")
        QApplication.processEvents()
        progress_dialog.close()
        self.update_total_duration_label()
        if self.media_queue and self.current_media_index == -1:
            self.current_media_index = 0; self.position = 0; self.paused_position = 0
            self._set_media_to_player(self.current_media_index)
        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.timeline.set_selected_segment(self.current_media_index)
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        self.stop_media(); self.is_sequence_play_active = False; self._update_sequence_play_button_state(); self._save_state()
    def load_file(self, file_path: str):
        if not file_path or not os.path.exists(file_path):
            self.show_message_box("Error", "Geçersiz dosya yolu veya dosya bulunamadı.")
            return
        media_type = self.get_file_type(file_path)
        original_filename_no_ext = os.path.splitext(os.path.basename(file_path))[0]
        if media_type == 'media_archive':
            self.stop_media(); self.media_queue.clear(); self.current_media_index = -1; self.position = 0; self.paused_position = 0
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_selected_segment(self.current_media_index)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            self.update_total_duration_label(); self._save_state()
            if not self._process_media_archive(file_path): self.show_message_box("Error", f"Medya arşivi '{os.path.basename(file_path)}' yüklenemedi.")
        elif media_type != 'unknown':
            if not self.add_media_to_queue(file_path, media_type, original_filename_no_ext): self.show_message_box("Error", f"Medya dosyası '{os.path.basename(file_path)}' zaman çizelgesine eklenemedi.")
        else: self.show_message_box("Warning", f"Bilinmeyen dosya türü veya geçersiz medya: {os.path.basename(file_path)}")
        if self.media_queue and self.current_media_index == -1:
            self.current_media_index = 0; self.position = 0; self.paused_position = 0
            self._set_media_to_player(self.current_media_index)
        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.timeline.set_selected_segment(self.current_media_index)
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        self.update_total_duration_label()
        self.stop_media(); self.is_sequence_play_active = False; self._update_sequence_play_button_state(); self._save_state()
    def _process_media_archive(self, archive_path: str) -> bool:
        if not self.media_engine:
            self.show_message_box("Error", "Medya motoru (libmediaengine.so) yüklenemedi. Arşiv işlenemez.")
            return False
        temp_extract_dir = tempfile.mkdtemp(prefix="media_archive_")
        try:
            extract_result = self.media_engine.extract_segments(archive_path.encode('utf-8'), temp_extract_dir.encode('utf-8'))
            if extract_result != 0:
                self.show_message_box("Error", f"Medya arşivi çıkarılamadı. Hata kodu: {extract_result}")
                return False
            manifest_file_name = os.path.splitext(os.path.basename(archive_path))[0] + "_manifest.txt"
            manifest_path = os.path.join(temp_extract_dir, manifest_file_name)
            if not os.path.exists(manifest_path):
                self.show_message_box("Error", "Arşivde manifest dosyası bulunamadı.")
                return False
            segments_to_add_from_archive = []
            with open(manifest_path, 'r') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) == 4:
                        seg_type, seg_path_in_archive, abbreviation_from_archive, original_ext = parts
                        full_seg_path = os.path.join(temp_extract_dir, os.path.basename(seg_path_in_archive))
                        if not os.path.exists(full_seg_path): continue
                        segments_to_add_from_archive.append({'path': full_seg_path, 'type': seg_type, 'original_name_prefix': os.path.splitext(os.path.basename(full_seg_path))[0]})
            for seg_data in segments_to_add_from_archive:
                duration = self.get_duration_from_path(seg_data['path'])
                if duration == -1: continue
                prefix_char = 's' if seg_data['type'] in ['audio', 'recorded_audio'] else 'v'
                existing_numbers = set()
                for segment in self.media_queue:
                    if segment['abbreviation'].startswith(prefix_char):
                        match = re.match(r'{}(\d+)(?:\.\d+)?$'.format(prefix_char), segment['abbreviation'])
                        if match: existing_numbers.add(int(match.group(1)))
                current_sequence_num = (max(existing_numbers) if existing_numbers else 0) + 1
                abbreviation = f"{prefix_char}{current_sequence_num}"
                formatted_duration_str_for_filename = self.format_time(duration)
                original_ext_seg = os.path.splitext(seg_data['path'])[1].lower()
                new_filename_imported = f"{abbreviation}_{formatted_duration_str_for_filename}{original_ext_seg}"
                dest_path_imported = os.path.join(self.media_save_dir, new_filename_imported)
                try:
                    shutil.copy2(seg_data['path'], dest_path_imported)
                    new_segment_data = {
                        'path': dest_path_imported, 'type': seg_data['type'], 'duration': duration, 'abbreviation': abbreviation,
                        'original_name_prefix': seg_data['original_name_prefix'], 'formatted_duration': self.format_time_display(duration),
                        'formatted_duration_ms': self.format_time_display_with_ms(duration), 'original_ext': original_ext_seg,
                        'id': str(time.time()) + str(current_sequence_num), 'is_cut_point': False
                    }
                    self.media_queue.append(new_segment_data)
                except IOError as e:
                    self.show_message_box("Error", f"Arşivden dosya kopyalanırken hata: {os.path.basename(seg_data['path'])}")
                    return False
            if self.media_queue:
                self.current_media_index = 0; self.position = 0; self.paused_position = 0
                self._set_media_to_player(self.current_media_index)
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_selected_segment(self.current_media_index)
            self.timeline.set_position(self.position)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            self.update_total_duration_label()
            return True
        except Exception as e:
            self.show_message_box("Error", f"Medya arşivi işlenirken bir hata oluştu: {e}")
            return False
        finally:
            if os.path.exists(temp_extract_dir): shutil.rmtree(temp_extract_dir)
    def update_total_duration_label(self):
        total_duration = self._get_total_overall_duration()
        self.total_time_label.setText(self.format_time_display_with_ms(total_duration))
    def delete_selected_media(self):
        if self.timeline.selected_segment_index == -1:
            self.show_message_box("Warning", "Lütfen silmek için bir medya seçin!")
            return
        index_to_delete = self.timeline.selected_segment_index
        if not (0 <= index_to_delete < len(self.media_queue)):
            self.timeline.set_selected_segment(-1)
            return
        segment_to_delete = self.media_queue[index_to_delete]
        deleted_file_path = segment_to_delete['path']
        self.stop_media(); self.is_sequence_play_active = False; self._update_sequence_play_button_state()
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
        if self.media_engine:
            delete_result = self.media_engine.delete_media_file(deleted_file_path.encode('utf-8'))
            if delete_result != 0: self.show_message_box("Error/Warning", f"Medya '{segment_to_delete['abbreviation']}' zaman çizelgesinden kaldırıldı, ancak diskten silinirken bir sorun oluştu.\nHata kodu: {delete_result}.")
        else: self.show_message_box("Warning", f"Medya '{segment_to_delete['abbreviation']}' zaman çizelgesinden kaldırıldı, ancak medya motoru yüklenemedi. Fiziksel dosya diskten silinmedi.")
        self._save_state()
    def cut_media(self):
        if not self.media_queue: self.show_message_box("Warning", "Kesmek için lütfen önce medya dosyalarını seçin!"); return
        if self.current_media_index == -1: self.show_message_box("Warning", "Kesme işlemi için aktif segment seçilmedi."); return
        if not self.media_engine: self.show_message_box("Error", "Medya motoru (libmediaengine.so) yüklenemedi. Kesme işlemi gerçekleştirilemez."); return
        if self.is_playing: self.show_message_box("Warning", "Kesme işlemi için medya oynatmayı duraklatın!"); return
        if self.is_sequence_play_active:
            self.is_sequence_play_active = False; self._update_sequence_play_button_state()
            self.show_message_box("Info", "Kesme işlemi için Sıralı Oynatma modu devre dışı bırakıldı.")
        relative_cut_point_sec = self.position
        relative_cut_point_ms = int(relative_cut_point_sec * 1000)
        original_segment = self.media_queue[self.current_media_index]
        original_file_path = original_segment['path']
        original_source_ext = original_segment.get('original_ext', '.mp4')
        original_duration_ms = int(original_segment['duration'] * 1000)
        EPSILON_CUT = 10
        if abs(relative_cut_point_ms) < EPSILON_CUT: relative_cut_point_ms = 0
        elif abs(relative_cut_point_ms - original_duration_ms) < EPSILON_CUT: relative_cut_point_ms = original_duration_ms
        if relative_cut_point_ms == 0 or relative_cut_point_ms == original_duration_ms: return
        base_abbreviation = original_segment['abbreviation']
        base_prefix = base_abbreviation[0]
        base_number = int(re.search(r'\d+', base_abbreviation).group())
        existing_sub_numbers_for_base = []
        for s in self.media_queue:
            match = re.match(r'{}{}\.(\d+)'.format(base_prefix, base_number), s['abbreviation'])
            if match: existing_sub_numbers_for_base.append(int(match.group(1)))
        start_sub_number = (max(existing_sub_numbers_for_base) if existing_sub_numbers_for_base else 0) + 1
        new_abbreviation_1 = f"{base_prefix}{base_number}.{start_sub_number}"
        new_abbreviation_2 = f"{base_prefix}{base_number}.{start_sub_number + 1}"
        intended_duration_part1_ms = relative_cut_point_ms
        intended_duration_part2_ms = original_duration_ms - relative_cut_point_ms
        formatted_duration_str_part1 = self.format_time(intended_duration_part1_ms / 1000.0)
        formatted_duration_str_part2 = self.format_time(intended_duration_part2_ms / 1000.0)
        new_filename_1 = f"{new_abbreviation_1}_{formatted_duration_str_part1}{original_source_ext}"
        new_filename_2 = f"{new_abbreviation_2}_{formatted_duration_str_part2}{original_source_ext}"
        output_file_1_path = os.path.join(self.media_save_dir, new_filename_1)
        output_file_2_path = os.path.join(self.media_save_dir, new_filename_2)
        cut_result = self.media_engine.cut_media_segment(original_file_path.encode('utf-8'), relative_cut_point_ms, output_file_1_path.encode('utf-8'), output_file_2_path.encode('utf-8'), original_segment['type'].encode('utf-8'))
        if cut_result != 0: self.show_message_box("Error", f"C++ motoru kullanılarak medya kesilemedi. Hata kodu: {cut_result}"); return
        try: os.remove(original_file_path)
        except OSError as e: print(f"Error: An error occurred while deleting the original temporary file: {original_file_path} - {e}")
        self.media_queue.pop(self.current_media_index)
        first_part_actual_duration_ms = self.media_engine.get_media_duration_ms(output_file_1_path.encode('utf-8'))
        second_part_actual_duration_ms = self.media_engine.get_media_duration_ms(output_file_2_path.encode('utf-8'))
        if first_part_actual_duration_ms == -1 or second_part_actual_duration_ms == -1:
            self.show_message_box("Error", "Yeni segmentlerin süresi belirlenemedi.")
            if os.path.exists(output_file_1_path): os.remove(output_file_1_path)
            if os.path.exists(output_file_2_path): os.remove(output_file_2_path)
            if not self.media_queue: self.current_media_index = -1; self.position = 0; self.paused_position = 0; self.timeline.set_media_segments(self.media_queue, self.current_media_index); self.timeline.set_selected_segment(self.current_media_index); self.timeline.set_position(self.position); self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position())); self.update_total_duration_label()
            return
        first_part_duration_sec = first_part_actual_duration_ms / 1000.0
        second_part_duration_sec = second_part_actual_duration_ms / 1000.0
        EPSILON_ZERO = 0.001
        add_segment_1 = first_part_duration_sec > EPSILON_ZERO
        add_segment_2 = second_part_duration_sec > EPSILON_ZERO
        if not add_segment_1 and not add_segment_2:
            self.show_message_box("Warning", "Kesme işlemi sonucunda geçerli bir segment oluşturulamadı. İşlem iptal edildi.")
            if os.path.exists(output_file_1_path): os.remove(output_file_1_path)
            if os.path.exists(output_file_2_path): os.remove(output_file_2_path)
            self.current_media_index = -1; self.position = 0; self.paused_position = 0; self.timeline.set_media_segments(self.media_queue, self.current_media_index); self.timeline.set_selected_segment(self.current_media_index); self.timeline.set_position(self.position); self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position())); self.update_total_duration_label(); self._save_state()
            return
        if add_segment_2:
            new_segment_2 = {'path': output_file_2_path, 'type': original_segment['type'], 'duration': second_part_duration_sec, 'abbreviation': new_abbreviation_2, 'original_name_prefix': original_segment['original_name_prefix'], 'formatted_duration': self.format_time_display(second_part_duration_sec), 'formatted_duration_ms': self.format_time_display_with_ms(second_part_duration_sec), 'original_ext': original_source_ext, 'id': str(time.time()) + new_abbreviation_2, 'is_cut_point': False}
            self.media_queue.insert(self.current_media_index, new_segment_2)
        else:
            if os.path.exists(output_file_2_path): os.remove(output_file_2_path)
        if add_segment_1:
            new_segment_1 = {'path': output_file_1_path, 'type': original_segment['type'], 'duration': first_part_duration_sec, 'abbreviation': new_abbreviation_1, 'original_name_prefix': original_segment['original_name_prefix'], 'formatted_duration': self.format_time_display(first_part_duration_sec), 'formatted_duration_ms': self.format_time_display_with_ms(first_part_duration_sec), 'original_ext': original_source_ext, 'id': str(time.time()) + new_abbreviation_1, 'is_cut_point': True}
            self.media_queue.insert(self.current_media_index, new_segment_1)
        else:
            if os.path.exists(output_file_1_path): os.remove(output_file_1_path)
        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.timeline.set_selected_segment(self.current_media_index)
        self.position = relative_cut_point_sec
        self.paused_position = int(relative_cut_point_sec * 1000)
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        if self.current_media_index != -1:
            self._set_media_to_player(self.current_media_index)
            self.player.setPosition(self.paused_position)
        self.update_total_duration_label(); self._save_state()
    def _on_timeline_segment_selected(self, index):
        if not self.media_queue or index < 0 or index >= len(self.media_queue):
            self.current_media_index = -1; self.timeline.set_selected_segment(-1); self.stop_media(); self.is_sequence_play_active = False; self._update_sequence_play_button_state()
            return
        if index == self.current_media_index:
            self.timeline.set_selected_segment(index); self.timeline.set_position(self.position); self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            return
        self.stop_media(); self.is_sequence_play_active = False; self._update_sequence_play_button_state()
        self.current_media_index = index; self.position = 0; self.paused_position = 0
        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.timeline.set_selected_segment(self.current_media_index)
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        self._set_media_to_player(self.current_media_index)
        self._save_state()
    def _perform_play(self):
        if self.player:
            if self.current_media_index != -1:
                relative_play_position_ms = int(self.position * 1000)
                relative_play_position_ms = max(0, relative_play_position_ms)
                self.player.setPosition(relative_play_position_ms)
                self.player.play()
            else: self.show_message_box("Error", "Oynatılacak geçerli bir segment yok. Lütfen dosya yükleyin.")
        else: self.show_message_box("Error", "Medya oynatılamadı. Lütfen başka bir dosya veya format deneyin.")
    def toggle_play_pause(self):
        if not self.media_queue: self.show_message_box("Warning", "Lütfen önce medya dosyalarını seçin!"); return
        if self.is_recording and (self.is_camera_mode_selected or self.is_audio_mode_selected): self.show_message_box("Warning", "Kayıt aktifken medya oynatılamaz. Lütfen önce kaydı durdurun."); return
        if self.player.state() == QMediaPlayer.PlayingState:
            self.paused_position = self.player.position() / 1000.0
            self.player.pause()
        else:
            if self.current_media_index == -1:
                if self.media_queue:
                    self.current_media_index = 0; self.position = 0; self.paused_position = 0
                    self.timeline.set_media_segments(self.media_queue, self.current_media_index)
                    self.timeline.set_selected_segment(self.current_media_index)
                    self.timeline.set_position(self.position)
                    self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
                    self._set_media_to_player(self.current_media_index)
                    QTimer.singleShot(50, self._perform_play)
                else: self.show_message_box("Warning", "Oynatılacak medya bulunamadı."); return
            self._set_media_to_player(self.current_media_index)
            self.position = self.paused_position
            self.timeline.set_position(self.position)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            QTimer.singleShot(50, self._perform_play)
    def _toggle_sequence_play_mode(self):
        if not self.media_queue: self.show_message_box("Warning", "Sıralı oynatılacak medya dosyası yok. Lütfen önce dosya aktarın."); return
        if self.is_recording: self.show_message_box("Warning", "Kayıt aktifken sıralı oynatma modu değiştirilemez. Lütfen önce kaydı durdurun."); return
        self.is_sequence_play_active = not self.is_sequence_play_active
        self._update_sequence_play_button_state()
    def _advance_to_next_segment(self):
        if not self.media_queue: return
        self.stop_media()
        next_index = self.current_media_index + 1
        if next_index < len(self.media_queue):
            self.current_media_index = next_index; self.position = 0; self.paused_position = 0
            self._set_media_to_player(self.current_media_index)
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_selected_segment(self.current_media_index)
            self.timeline.set_position(self.position)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            self._save_state()
            if self.is_sequence_play_active: QTimer.singleShot(50, self._perform_play)
        else:
            self.stop_media(); self.current_media_index = -1; self.position = 0; self.paused_position = 0
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_selected_segment(self.current_media_index)
            self.timeline.set_position(self.position)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            self._save_state()
            self.is_sequence_play_active = False
            self._update_sequence_play_button_state()
    def current_player(self): return self.player
    def stop_media(self):
        self.player.stop()
        self.paused_position = self.position
        self.video_output_widget.hide(); self.audio_icon_label.hide(); self.camera_preview_label.hide()
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
    def _set_media_to_player(self, index):
        if index < 0 or index >= len(self.media_queue): self.player.setMedia(QMediaContent()); return
        current_media_info = self.media_queue[index]
        media_url = QUrl.fromLocalFile(current_media_info['path'])
        self.player.setMedia(QMediaContent(media_url))
        self.player.setPlaybackRate(float(self.playback_speed_box.currentText()))
        if current_media_info['type'] in ['video', 'recorded_video']:
            self.audio_icon_label.hide(); self.camera_preview_label.hide(); self.video_output_widget.show()
            self.player.setVideoOutput(self.video_widget)
        elif current_media_info['type'] in ['audio', 'recorded_audio']:
            self.video_output_widget.hide(); self.camera_preview_label.hide(); self.audio_icon_label.show()
            self.player.setVideoOutput(None)
        elif current_media_info['type'] == 'media_archive':
            self.player.setMedia(QMediaContent()); self.video_output_widget.hide(); self.camera_preview_label.hide(); self.audio_icon_label.hide()
            self.show_message_box("Info", ".media arşivi doğrudan oynatılamaz. Lütfen önce 'Dosya' menüsünden çıkarın.")
            return
        else: self.player.setMedia(QMediaContent())
    def update_position(self):
        if self.current_media_index == -1: return
        current_media = self.media_queue[self.current_media_index]
        current_player_time_ms = self.player.position()
        if current_player_time_ms == -1: return
        self.position = current_player_time_ms / 1000.0
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
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
        if self.player.state() == QMediaPlayer.PlayingState: self.player.setPosition(int(new_position_in_segment_ms))
        else:
            self._set_media_to_player(self.current_media_index)
            self.player.setPosition(int(new_position_in_segment_ms))
        QApplication.processEvents()
    def export_media_archive(self):
        if not self.media_queue: self.show_message_box("Warning", "Dışa aktarılacak medya yok."); return
        if not self.media_engine: self.show_message_box("Error", "Medya motoru (libmediaengine.so) yüklenemedi. Medya dışa aktarılamaz."); return
        default_filename = f"export_timeline_{time.strftime('%H%M%S')}.media"
        output_file_user_selected, _ = QFileDialog.getSaveFileName(self, "Medya Arşivini Dışa Aktar", os.path.join(DEFAULT_BASE_DIR, default_filename), "Medya Arşivi (*.media)")
        if not output_file_user_selected: return
        if not output_file_user_selected.lower().endswith(".media"): output_file_user_selected += ".media"
        temp_export_dir = tempfile.mkdtemp(prefix="media_export_")
        manifest_file_name_prefix = os.path.splitext(os.path.basename(output_file_user_selected))[0]
        manifest_file_name = manifest_file_name_prefix + "_manifest.txt"
        manifest_path = os.path.join(temp_export_dir, manifest_file_name)
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Medya Arşivini Dışa Aktarma")
        progress_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        progress_dialog.setAttribute(Qt.WA_DeleteOnClose)
        progress_dialog.setStyleSheet("QDialog { background-color: #3f3f3f; border: 2px solid #4CAF50; border-radius: 8px; } QLabel { color: #ffffff; font-size: 14px; padding: 5px; } QProgressBar { border: 2px solid #555; border-radius: 5px; background-color: #2e2e2e; text-align: center; color: white; } QProgressBar::chunk { background-color: #4CAF50; border-radius: 4px; }")
        dialog_layout = QVBoxLayout(progress_dialog)
        dialog_layout.setContentsMargins(20, 20, 20, 20)
        export_label = QLabel("Segmentler dışa aktarılıyor...")
        dialog_layout.addWidget(export_label)
        self.progress_bar = QProgressBar(progress_dialog)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        dialog_layout.addWidget(self.progress_bar)
        self.time_estimate_label = QLabel("Kalan süre hesaplanıyor...")
        dialog_layout.addWidget(self.time_estimate_label)
        progress_dialog.show()
        QApplication.processEvents()
        self._export_start_time = time.time()
        try:
            with open(manifest_path, 'w') as f:
                for i, segment in enumerate(self.media_queue):
                    temp_segment_filename = os.path.basename(segment['path'])
                    f.write(f"{segment['type']},{temp_segment_filename},{segment['abbreviation']},{segment['original_ext']}\n")
                    shutil.copy2(segment['path'], os.path.join(temp_export_dir, temp_segment_filename))
                    self.progress_bar.setValue(int(((i + 1) / len(self.media_queue)) * 90))
                    QApplication.processEvents()
            archive_result = self.media_engine.archive_segments(output_file_user_selected.encode('utf-8'), temp_export_dir.encode('utf-8'), manifest_file_name.encode('utf-8'))
            self.progress_bar.setValue(100)
            self.time_estimate_label.setText("Dışa aktarma tamamlandı!")
            if archive_result == 0: self.show_message_box("Dışa Aktarma Başarılı", f"Medya zaman çizelgesi başarıyla dışa aktarıldı:\n{output_file_user_selected}")
            else: self.show_message_box("Error", f"Medya zaman çizelgesi dışa aktarılamadı. Hata kodu: {archive_result}")
        except Exception as e: self.show_message_box("Error", f"Dışa aktarma sırasında bir hata oluştu: {e}")
        finally:
            if os.path.exists(temp_export_dir): shutil.rmtree(temp_export_dir)
            progress_dialog.close()
    def export_single_video(self):
        # ... (Bu fonksiyonun içeriği değişmedi)
        pass
    def _handle_camera_button_click(self):
        self.show_message_box("Info", "Bu fonksiyon geliştirme aşamasındadır.")

    def _toggle_audio_mode_selection(self):
        """Ses modu seçimini yönetir ve doğrudan ses kaydını başlatır/durdurur."""
        if not self.media_engine:
            self.show_message_box("Error", "Medya motoru (libmediaengine.so) yüklenemedi.")
            return

        if self.player.state() == QMediaPlayer.PlayingState:
            self.show_message_box("Warning", "Medya oynatma aktif. Lütfen önce durdurun.")
            return

        if self.is_stopping_audio_recording:
            self.show_message_box("Info", "Ses kaydını durdurma işlemi zaten devam ediyor. Lütfen bekleyin.")
            return

        if self.is_sequence_play_active:
            self.is_sequence_play_active = False
            self._update_sequence_play_button_state()
            self.show_message_box("Info", "Kayıt başlatmak için Sıralı Oynatma modu devre dışı bırakıldı.")

        if not self.is_recording:
            if self.is_camera_mode_selected:
                self.is_camera_mode_selected = False
            self.stop_media()
            self.audio_mode_btn.setEnabled(False)
            self._update_record_button_state()
            QApplication.processEvents()
            existing_rec_s_numbers = []
            for item in os.listdir(self.audio_record_dir):
                match = re.match(r'recorded_audio_(\d+)\.wav$', item)
                if match: existing_rec_s_numbers.append(int(match.group(1)))
            self.recorded_audio_count = (max(existing_rec_s_numbers) if existing_rec_s_numbers else 0) + 1
            final_audio_filename = f"recorded_audio_{self.recorded_audio_count}.wav"
            self.audio_record_final_path = os.path.join(self.audio_record_dir, final_audio_filename)
            segment_pattern = os.path.join(self.audio_record_dir, "recorded_audio_segment_%03d.wav")
            result = self.media_engine.start_audio_record(segment_pattern.encode("utf-8"), self.audio_record_final_path.encode("utf-8"))
            if result == 0:
                self.is_recording = True
                self.is_audio_mode_selected = True
                self.audio_icon_label.show()
            else:
                self.show_message_box("Error", f"Ses kaydı başlatılamadı. Hata kodu: {result}.")
                self.is_recording = False
                self.is_audio_mode_selected = False
            self.audio_mode_btn.setEnabled(True)
            self._update_record_button_state()
        else:
            self.is_stopping_audio_recording = True
            self.audio_mode_btn.setEnabled(False)
            self._update_record_button_state()
            QApplication.processEvents()
            try:
                stop_result = self.media_engine.stop_audio_record()
                if stop_result == 0:
                    merge_result = self.media_engine.merge_audio_files(self.audio_record_final_path.encode("utf-8"))
                    if merge_result == 0:
                        final_path_to_add = self.audio_record_final_path
                        # YENİ: Gürültü filtresini uygula
                        if self.noise_filter_enabled:
                            progress = QProgressDialog("Applying audio filter...", "Cancel", 0, 100, self)
                            progress.setWindowModality(Qt.WindowModal)
                            progress.setWindowTitle("Processing Audio")
                            progress.show()
                            QApplication.processEvents()
                            try:
                                filtered_path = self._apply_python_audio_filter(self.audio_record_final_path, progress)
                                os.remove(self.audio_record_final_path)
                                final_path_to_add = filtered_path
                            except Exception as e:
                                self.show_message_box("Filter Error", f"An error occurred while applying the audio filter: {e}")
                            finally:
                                progress.close()

                        original_filename_no_ext = os.path.splitext(os.path.basename(final_path_to_add))[0]
                        if os.path.exists(final_path_to_add):
                            if not self.add_media_to_queue(final_path_to_add, 'recorded_audio', original_filename_no_ext):
                                self.show_message_box("Error", "Kaydedilen ses zaman çizelgesine eklenemedi.")
                        else:
                            self.show_message_box("Error", "Kaydedilen ve birleştirilen ses dosyası bulunamadı.")
                    else:
                        self.show_message_box("Error", "Ses dosyaları birleştirilirken bir hata oluştu.")
                else:
                    self.show_message_box("Error", "Ses kaydı durdurulurken bir hata oluştu.")
            except Exception as e:
                self.show_message_box("Error", f"Ses durdurma/birleştirme sırasında beklenmeyen bir hata oluştu: {e}")
            finally:
                self.is_recording = False
                self.is_audio_mode_selected = False
                self.audio_record_final_path = None
                self.is_stopping_audio_recording = False
                self.audio_icon_label.hide()
                self.audio_mode_btn.setEnabled(True)
                self._update_record_button_state()

    # ... (Diğer metodlar buraya gelecek, değişiklik yok)
    def _update_record_button_state(self):
        if self.is_recording:
            self.audio_mode_btn.setText("Stop")
            self.audio_mode_btn.setStyleSheet(self.buttonStyle("record_active"))
            self.play_pause_btn.setEnabled(False)
            self.sequence_play_btn.setEnabled(False)
        else:
            self.audio_mode_btn.setText("Sound")
            self.audio_mode_btn.setStyleSheet(self.buttonStyle("default"))
            self.play_pause_btn.setEnabled(True)
            self.sequence_play_btn.setEnabled(True)
        self.audio_mode_btn.setEnabled(not self.is_stopping_audio_recording and self.media_engine is not None)
        self.camera_mode_btn.setEnabled(True)
        self._update_sequence_play_button_state()
    def _update_sequence_play_button_state(self):
        if self.is_sequence_play_active: self.sequence_play_btn.setStyleSheet(self.buttonStyle("sequence_play_active"))
        else: self.sequence_play_btn.setStyleSheet(self.buttonStyle("sequence_toggle"))
        self.sequence_play_btn.setEnabled(not self.is_recording)
    def _stop_all_recording_processes(self):
        if self.media_engine:
            self.media_engine.stop_camera_record()
            if self.is_recording and self.is_audio_mode_selected: self.media_engine.stop_audio_record()
        if self.video_record_thread and self.video_record_thread.is_alive():
            self.video_record_thread.stop()
            self.video_record_thread.join(timeout=5)
            self.video_record_thread = None
        self.camera_timer.stop()
        self.is_recording = False
    def update_camera_frame(self):
        if not self.media_engine or not self.media_engine.is_camera_open() or not self.is_recording or not self.is_camera_mode_selected: self.camera_preview_label.hide(); return
        out_frame = Frame()
        if self.media_engine.read_frame(ctypes.byref(out_frame)):
            frame_np = np.ctypeslib.as_array(out_frame.data, shape=(out_frame.height, out_frame.width, out_frame.channels))
            if out_frame.channels == 3: frame_rgb = cv2.cvtColor(frame_np, cv2.COLOR_BGR2RGB)
            elif out_frame.channels == 1: frame_rgb = cv2.cvtColor(frame_np, cv2.COLOR_GRAY2RGB)
            else: self.media_engine.free_frame_data(ctypes.byref(out_frame)); return
            h, w, ch = frame_rgb.shape
            q_image = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(self.camera_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.camera_preview_label.setPixmap(scaled_pixmap)
            if self.is_recording and self.video_record_thread and self.video_record_thread.is_alive():
                bgr_frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                try: self.video_frame_queue.put_nowait(bgr_frame)
                except queue.Full: pass
            self.media_engine.free_frame_data(ctypes.byref(out_frame))
        else:
            self.camera_timer.stop()
            self.camera_preview_label.hide()
            if self.is_recording and self.is_camera_mode_selected: self._stop_all_recording_processes()
    def handle_move_segment_request(self, index: int, direction: int):
        if not self.media_queue or index < 0 or index >= len(self.media_queue): return
        current_index = index
        target_index = current_index + direction
        if not (0 <= target_index < len(self.media_queue)): return
        self.stop_media(); self.is_sequence_play_active = False; self._update_sequence_play_button_state()
        segment_to_move = self.media_queue.pop(current_index)
        self.media_queue.insert(target_index, segment_to_move)
        if current_index == self.current_media_index: self.current_media_index = target_index
        elif current_index < self.current_media_index and target_index >= self.current_media_index: self.current_media_index -= 1
        elif current_index > self.current_media_index and target_index <= self.current_media_index: self.current_media_index += 1
        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.timeline.set_selected_segment(target_index)
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        if self.current_media_index != -1:
            self._set_media_to_player(self.current_media_index)
            self.player.setPosition(int(self.position * 1000))
        self._save_state()
    def handle_segment_resize_request(self, index: int, delta_ms: int, is_expanding: bool):
        if not self.media_queue or index < 0 or index >= len(self.media_queue): return
        segment = self.media_queue[index]
        original_duration_ms = int(segment['duration'] * 1000)
        new_duration_ms = original_duration_ms + delta_ms
        min_duration_ms = 1000
        max_duration_ms = int(original_duration_ms * 5.0)
        new_duration_ms = max(min_duration_ms, min(max_duration_ms, new_duration_ms))
        if new_duration_ms == original_duration_ms: return
        segment['duration'] = new_duration_ms / 1000.0
        segment['formatted_duration'] = self.format_time_display_with_ms(segment['duration'])
        segment['formatted_duration_ms'] = self.format_time_display_with_ms(segment['duration'])
        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.update_total_duration_label()
        self._save_state()
    def _save_state(self):
        state = {'media_queue': copy.deepcopy(self.media_queue), 'current_media_index': self.current_media_index, 'position': self.position, 'paused_position': self.paused_position}
        self._undo_stack.append(state)
        if len(self._undo_stack) > self._max_undo_states: self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._update_undo_redo_buttons()
    def _restore_state(self, state):
        self.stop_media(); self.is_sequence_play_active = False; self._update_sequence_play_button_state()
        self.media_queue = copy.deepcopy(state['media_queue'])
        self.current_media_index = state['current_media_index']
        self.position = state['position']
        self.paused_position = state['paused_position']
        self.timeline.set_media_segments(self.media_queue, self.current_media_index)
        self.timeline.set_selected_segment(self.current_media_index)
        self.update_total_duration_label()
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        if self.current_media_index != -1:
            self._set_media_to_player(self.current_media_index)
            self.player.setPosition(int(self.position * 1000))
        self._update_undo_redo_buttons()
    def undo(self):
        if len(self._undo_stack) > 1:
            current_state = self._undo_stack.pop()
            self._redo_stack.append(current_state)
            self._restore_state(self._undo_stack[-1])
        else: self.show_message_box("Info", "Geri alınacak başka eylem yok.")
        self._update_undo_redo_buttons()
    def redo(self):
        if self._redo_stack:
            state_to_redo = self._redo_stack.pop()
            self._undo_stack.append(state_to_redo)
            self._restore_state(state_to_redo)
        else: self.show_message_box("Info", "Yinelenecek başka eylem yok.")
        self._update_undo_redo_buttons()
    def _update_undo_redo_buttons(self):
        self.undo_btn.setEnabled(len(self._undo_stack) > 1)
        self.redo_btn.setEnabled(len(self._redo_stack) > 0)
    def populate_seek_interval_menu(self): pass
    def change_seek_interval(self, text: str):
        if text in self.millisecond_seek_intervals: self.seek_interval_ms = self.millisecond_seek_intervals[text]
        elif text in self.seek_intervals: self.seek_interval_ms = self.seek_intervals[text]
    def change_playback_speed(self, text: str):
        try: self.player.setPlaybackRate(float(text))
        except ValueError: self.show_message_box("Error", "Geçersiz oynatma hızı değeri.")
    def _update_selected_segment_info_labels(self): pass
    def _get_overall_timeline_position(self):
        if self.current_media_index == -1 or not self.media_queue: return 0.0
        time_before_current_segment = sum(self.media_queue[i]['duration'] for i in range(self.current_media_index))
        return time_before_current_segment + self.position
    def _get_total_overall_duration(self):
        return sum(segment['duration'] for segment in self.media_queue)
    def _perform_cut_at_position(self, segment_index_to_cut: int, cut_point_sec: float) -> tuple[dict, dict] | tuple[None, None]:
        if not self.media_engine: return None, None
        if segment_index_to_cut < 0 or segment_index_to_cut >= len(self.media_queue): return None, None
        original_segment = self.media_queue[segment_index_to_cut]
        original_file_path = original_segment['path']
        original_source_ext = original_segment.get('original_ext', '.mp4')
        original_duration_ms = int(original_segment['duration'] * 1000)
        relative_cut_point_ms = int(cut_point_sec * 1000)
        EPSILON_CUT = 10
        if abs(relative_cut_point_ms) < EPSILON_CUT or abs(relative_cut_point_ms - original_duration_ms) < EPSILON_CUT: return None, None
        base_abbreviation = original_segment['abbreviation']
        base_prefix = base_abbreviation[0]
        base_number = int(re.search(r'\d+', base_abbreviation).group())
        existing_sub_numbers_for_base = []
        for s in self.media_queue:
            match = re.match(r'{}{}\.(\d+)'.format(base_prefix, base_number), s['abbreviation'])
            if match: existing_sub_numbers_for_base.append(int(match.group(1)))
        start_sub_number = (max(existing_sub_numbers_for_base) if existing_sub_numbers_for_base else 0) + 1
        new_abbreviation_1 = f"{base_prefix}{base_number}.{start_sub_number}"
        new_abbreviation_2 = f"{base_prefix}{base_number}.{start_sub_number + 1}"
        intended_duration_part1_ms = relative_cut_point_ms
        intended_duration_part2_ms = original_duration_ms - relative_cut_point_ms
        formatted_duration_str_part1 = self.format_time(intended_duration_part1_ms / 1000.0)
        formatted_duration_str_part2 = self.format_time(intended_duration_part2_ms / 1000.0)
        new_filename_1 = f"{new_abbreviation_1}_{formatted_duration_str_part1}{original_source_ext}"
        new_filename_2 = f"{new_abbreviation_2}_{formatted_duration_str_part2}{original_source_ext}"
        output_file_1_path = os.path.join(self.media_save_dir, new_filename_1)
        output_file_2_path = os.path.join(self.media_save_dir, new_filename_2)
        cut_result = self.media_engine.cut_media_segment(original_file_path.encode('utf-8'), relative_cut_point_ms, output_file_1_path.encode('utf-8'), output_file_2_path.encode('utf-8'), original_segment['type'].encode('utf-8'))
        if cut_result != 0: return None, None
        try: os.remove(original_file_path)
        except OSError as e: print(f"UYARI: Programatik kesme sonrası orijinal dosya silinemedi: {original_file_path} - {e}")
        self.media_queue.pop(segment_index_to_cut)
        first_part_actual_duration_ms = self.media_engine.get_media_duration_ms(output_file_1_path.encode('utf-8'))
        second_part_actual_duration_ms = self.media_engine.get_media_duration_ms(output_file_2_path.encode('utf-8'))
        if first_part_actual_duration_ms == -1 or second_part_actual_duration_ms == -1:
            if os.path.exists(output_file_1_path): os.remove(output_file_1_path)
            if os.path.exists(output_file_2_path): os.remove(output_file_2_path)
            return None, None
        first_part_duration_sec = first_part_actual_duration_ms / 1000.0
        second_part_duration_sec = second_part_actual_duration_ms / 1000.0
        EPSILON_ZERO = 0.001
        part1_segment = None; part2_segment = None
        if first_part_duration_sec > EPSILON_ZERO:
            part1_segment = {'path': output_file_1_path, 'type': original_segment['type'], 'duration': first_part_duration_sec, 'abbreviation': new_abbreviation_1, 'original_name_prefix': original_segment['original_name_prefix'], 'formatted_duration': self.format_time_display(first_part_duration_sec), 'formatted_duration_ms': self.format_time_display_with_ms(first_part_duration_sec), 'original_ext': original_source_ext, 'id': str(time.time()) + new_abbreviation_1, 'is_cut_point': True}
            self.media_queue.insert(segment_index_to_cut, part1_segment)
            self.current_media_index = segment_index_to_cut
        else:
            if os.path.exists(output_file_1_path): os.remove(output_file_1_path)
        if second_part_duration_sec > EPSILON_ZERO:
            part2_segment = {'path': output_file_2_path, 'type': original_segment['type'], 'duration': second_part_duration_sec, 'abbreviation': new_abbreviation_2, 'original_name_prefix': original_segment['original_name_prefix'], 'formatted_duration': self.format_time_display(second_part_duration_sec), 'formatted_duration_ms': self.format_time_display_with_ms(second_part_duration_sec), 'original_ext': original_source_ext, 'id': str(time.time()) + new_abbreviation_2, 'is_cut_point': False}
            if part1_segment: self.media_queue.insert(segment_index_to_cut + 1, part2_segment)
            else: self.media_queue.insert(segment_index_to_cut, part2_segment); self.current_media_index = segment_index_to_cut
        else:
            if os.path.exists(output_file_2_path): os.remove(output_file_2_path)
        if not part1_segment and not part2_segment:
            if segment_index_to_cut < len(self.media_queue): self.current_media_index = segment_index_to_cut
            elif self.media_queue: self.current_media_index = len(self.media_queue) - 1
            else: self.current_media_index = -1
            return None, None
        self.position = 0.0; self.paused_position = 0.0
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
        self.update_total_duration_label()
        return part1_segment, part2_segment
    def toggle_fullscreen(self):
        if not self.media_queue or self.current_media_index == -1: self.show_message_box("Warning", "Tam ekran moduna geçmek için önce bir medya dosyası yükleyin."); return
        current_media_info = self.media_queue[self.current_media_index]
        if current_media_info['type'] in ['video', 'recorded_video']:
            if self.is_fullscreen:
                self.showMaximized(); self.toolbar_frame.show(); self.timeline.show()
                self.stop_media()
                self.timeline.set_position(self.position)
                self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
                self._set_media_to_player(self.current_media_index)
                self.player.setPosition(int(self.position * 1000))
                self.is_fullscreen = False
            else:
                self.toolbar_frame.hide(); self.timeline.hide(); self.showFullScreen()
                self.is_fullscreen = True
        elif current_media_info['type'] in ['audio', 'recorded_audio']: QMessageBox.information(self, "Fonksiyon Yok", "Ses dosyaları için tam ekran özelliği bulunmamaktadır.")
        else: QMessageBox.information(self, "Fonksiyon Yok", "Desteklenmeyen medya türü için tam ekran özelliği bulunmamaktadır.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = MediaEditor()
    editor.showMaximized()
    sys.exit(app.exec_())
