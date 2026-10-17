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
import os as _os
_PROGRAM_DIR = _os.path.dirname(_os.path.abspath(__file__))
_KAVRAM_DIR = _os.environ.get("KAVRAM_DIR") or _os.path.dirname(_PROGRAM_DIR)
_KAVRAM_EXPORT_DIR = _os.path.join(_KAVRAM_DIR, "export")
# -------------------------------------------------------------------------------
import os
import shutil
import tempfile
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
                             QFileDialog, QFrame, QSizePolicy, QMessageBox, QSplitter, QDialog,
                             QMenu, QAction, QProgressBar, QComboBox, QShortcut, QGridLayout,
                             QProgressDialog)
from PyQt5.QtGui import (QPainter, QColor, QPen, QFont, QImage, QPixmap, QIcon, QKeySequence)
from PyQt5.QtCore import (Qt, QTimer, pyqtSignal, QPoint, QDir, QSize, QByteArray, QBuffer,
                          QIODevice, QUrl)
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
import math

from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

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
    """ffmpeg / ffprobe / ffplay: sistemde (PATH) kurulu olanı kullanır."""
    import shutil as _shutil
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
SAVE_DIR = os.path.join(_PROGRAM_DIR, 'medya_cut')

LIB_PATH = os.path.join(_PROGRAM_DIR, "media_engine.so")

SETTINGS_FILE = os.path.join(_KAVRAM_DIR, "filter", "filter_settings.json")
OVERLAY_SETTINGS_FILE = os.path.join(_KAVRAM_DIR, "rec", "rec_overlay.json")


class Frame(ctypes.Structure):
    _fields_ = [("data", ctypes.POINTER(ctypes.c_ubyte)),
                ("width", ctypes.c_int),
                ("height", ctypes.c_int),
                ("channels", ctypes.c_int),
                ("data_owner", ctypes.c_bool)]


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

    def run(self):
        try:
            self.writer = cv2.VideoWriter(self.output_path, self.fourcc, self.fps, self.frame_size)
            if not self.writer.isOpened():
                self.running.clear(); return
            while self.running.is_set():
                try:
                    frame = self.frame_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                try:
                    if frame is not None:
                        self.writer.write(frame)
                finally:
                    self.frame_queue.task_done()
        except Exception as e:
            print(f"ERROR in video recording thread: {e}")
        finally:
            if self.writer: self.writer.release()

    def stop(self):
        self.running.clear()


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

        # QMediaPlayer + QVideoWidget
        self.player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)
        self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.player.setVideoOutput(self.video_widget)
        self.player.setPlaybackRate(1.0)
        self.player.stateChanged.connect(self._handle_player_state_changed)
        self.player.error.connect(self._handle_player_error)

        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.update_position)

        self.media_save_dir = SAVE_DIR
        self.audio_record_dir = SAVE_DIR
        self._ensure_dirs_exist()
        self._clean_save_dir_on_startup()

        self.media_engine = None
        try:
            self.media_engine = ctypes.CDLL(LIB_PATH)

            # --- Timeline logic (native C++) ---
            self.media_engine.calculate_segment_position.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double]
            self.media_engine.calculate_segment_position.restype = ctypes.c_double
            self.media_engine.update_timeline_smoothly.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double]
            self.media_engine.update_timeline_smoothly.restype = ctypes.c_double

            # Ses motoru
            self.media_engine.init_audio_engine.restype = ctypes.c_int
            self.media_engine.terminate_audio_engine.restype = ctypes.c_int
            self.media_engine.start_audio_record.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.start_audio_record.restype = ctypes.c_int
            self.media_engine.stop_audio_record.restype = ctypes.c_int
            self.media_engine.merge_audio_files.argtypes = [ctypes.c_char_p]
            self.media_engine.merge_audio_files.restype = ctypes.c_int

            # Kamera
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

            # Medya işlemleri
            self.media_engine.cut_media_segment.argtypes = [ctypes.c_char_p, ctypes.c_longlong, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.cut_media_segment.restype = ctypes.c_int
            self.media_engine.delete_media_file.argtypes = [ctypes.c_char_p]
            self.media_engine.delete_media_file.restype = ctypes.c_int
            self.media_engine.get_media_duration_ms.argtypes = [ctypes.c_char_p]
            self.media_engine.get_media_duration_ms.restype = ctypes.c_longlong

            # Arşiv (yeni + eski)
            self.media_engine.archive_segments.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.archive_segments.restype = ctypes.c_int
            self.media_engine.archive_segments_with_compression.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.archive_segments_with_compression.restype = ctypes.c_int
            self.media_engine.extract_segments.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.extract_segments.restype = ctypes.c_int

            # Render (yeni + eski)
            self.media_engine.merge_timeline_to_video.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.merge_timeline_to_video.restype = ctypes.c_int
            self.media_engine.export_timeline_media.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
            self.media_engine.export_timeline_media.restype = ctypes.c_int

            # Video boyut sorgu
            self.media_engine.get_video_dimensions.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
            self.media_engine.get_video_dimensions.restype = ctypes.c_int

            init_result = self.media_engine.init_audio_engine()
            if init_result != 0:
                self.show_message_box("Error", f"PortAudio initialization failed. Error code: {init_result}")
        except OSError as e:
            self.show_message_box("Error", f"Could not load media_engine.so: {e}.")
            self.media_engine = None
        except AttributeError as e:
            self.show_message_box("Error", f"Could not load Media Engine functions: {e}.")
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
               self.player.position() >= self.player.duration() - 150:
                print(f"Segment {self.current_media_index} ended in sequence mode. Advancing.")
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
        self.play_pause_btn.setStyleSheet(self.buttonStyle("play"))
        self.play_pause_btn.setFixedSize(88, 30)
        top_buttons_layout.addWidget(self.play_pause_btn)

        self.sequence_play_btn = QPushButton("/")
        self.sequence_play_btn.clicked.connect(self._toggle_sequence_play_mode)
        self.sequence_play_btn.setStyleSheet(self.buttonStyle("sequence_toggle"))
        self.sequence_play_btn.setFixedSize(30, 30)
        top_buttons_layout.addWidget(self.sequence_play_btn)

        self.cut_btn = QPushButton("Cut")
        self.cut_btn.clicked.connect(self.cut_media)
        self.cut_btn.setStyleSheet(self.buttonStyle("default"))
        self.cut_btn.setFixedSize(60, 30)
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
        self.export_btn.setStyleSheet(self.buttonStyle("default"))
        self.export_btn.setFixedSize(90, 30)
        self.export_btn.clicked.connect(self._on_export_left_click)
        top_buttons_layout.addWidget(self.export_btn)

        self.media_btn = QPushButton("Media")
        self.media_btn.setStyleSheet(self.buttonStyle("default"))
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
        output_file_user_selected, _ = QFileDialog.getSaveFileName(
            self, f"Medya Arşivini Dışa Aktar ({compression.upper()})",
            default_name, filter_str)
        if not output_file_user_selected:
            return
        if not output_file_user_selected.lower().endswith(".media"):
            output_file_user_selected += ".media"
        self._save_project_internal(output_file_user_selected, compression)

    def _show_export_format_menu(self, pos: QPoint):
        """Sağ tık: video/ses format seçenekleri."""
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

        menu.addSeparator()

        audio_menu = menu.addMenu("🎵 Ses Olarak (Sadece Ses)")
        audio_menu.addAction("WAV (.wav - kayıpsız)").triggered.connect(lambda: self._export_timeline_with_format("wav"))
        audio_menu.addAction("MP3 (.mp3 - 192kbps)").triggered.connect(lambda: self._export_timeline_with_format("mp3"))
        audio_menu.addAction("Opus (.opus - 128kbps)").triggered.connect(lambda: self._export_timeline_with_format("opus"))
        audio_menu.addAction("AAC (.m4a - 192kbps)").triggered.connect(lambda: self._export_timeline_with_format("m4a"))
        audio_menu.addAction("FLAC (.flac - kayıpsız)").triggered.connect(lambda: self._export_timeline_with_format("flac"))

        menu.exec_(self.export_btn.mapToGlobal(pos))

    def _export_timeline_with_format(self, fmt: str):
        if not self.media_queue:
            self.show_message_box("Warning", "Dışa aktarılacak medya yok.")
            return
        if not self.media_engine:
            self.show_message_box("Error", "Medya motoru yüklenemedi.")
            return
        fmt = str(fmt).lower()
        allowed_formats = {"mkv", "mp4", "wav", "mp3", "opus", "m4a", "aac", "flac", "ogg"}
        if fmt not in allowed_formats:
            self.show_message_box("Hata", f"Desteklenmeyen dışa aktarma biçimi: {fmt}")
            return

        is_audio_only = fmt in ("wav", "mp3", "opus", "m4a", "aac", "flac", "ogg")
        default_name = os.path.join(DEFAULT_BASE_DIR, f"kavram_cikti.{fmt}")
        file_filter = f"*.{fmt}"
        output_file_path, _ = QFileDialog.getSaveFileName(
            self, f"{'Ses' if is_audio_only else 'Video'} Olarak Dışa Aktar",
            default_name, file_filter)
        if not output_file_path:
            return
        if not output_file_path.lower().endswith(f".{fmt}"):
            output_file_path += f".{fmt}"

        progress = QProgressDialog("Hazırlanıyor...", "İptal", 0, len(self.media_queue) + 5, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Dışa Aktarılıyor")
        progress.show()
        QApplication.processEvents()

        temp_render_dir = tempfile.mkdtemp(prefix="kavram_export_")
        video_manifest_path = os.path.join(temp_render_dir, "video_list.txt")
        audio_manifest_path = os.path.join(temp_render_dir, "audio_list.txt")

        try:
            target_width, target_height = 1920, 1080
            if not is_audio_only:
                for seg in self.media_queue:
                    if seg['type'] in ('video', 'recorded_video'):
                        w, h = ctypes.c_int(0), ctypes.c_int(0)
                        if self.media_engine.get_video_dimensions(
                                seg['path'].encode('utf-8'),
                                ctypes.byref(w), ctypes.byref(h)) == 0 and w.value > 0 and h.value > 0:
                            target_width, target_height = w.value, h.value
                            break

            video_files_for_concat = []
            audio_files_for_concat = []
            placeholder_image = os.path.join(temp_render_dir, "audio_placeholder.png")
            if not is_audio_only and any(s['type'] in ('audio', 'recorded_audio') for s in self.media_queue):
                self._create_audio_placeholder_image(placeholder_image, target_width, target_height)
                if not os.path.exists(placeholder_image):
                    raise RuntimeError("Ses segmentleri için geçici video görüntüsü oluşturulamadı.")

            for i, segment in enumerate(self.media_queue):
                if progress.wasCanceled():
                    raise InterruptedError("User canceled operation")

                progress.setLabelText(f"İşleniyor {i+1}/{len(self.media_queue)}: {segment['abbreviation']}")
                progress.setValue(i)
                QApplication.processEvents()

                original_path = segment['path']
                seg_type = segment['type']

                if is_audio_only:
                    if seg_type in ('audio', 'recorded_audio'):
                        audio_files_for_concat.append(os.path.abspath(original_path))
                    elif seg_type in ('video', 'recorded_video'):
                        extracted = os.path.join(temp_render_dir, f"extracted_{i}.wav")
                        if self._extract_audio_from_video(original_path, extracted):
                            audio_files_for_concat.append(extracted)
                        else:
                            raise RuntimeError(f"Video segment {i} için ses çıkarılamadı; dışa aktarma eksik içerikle devam etmeyecek.")
                    continue

                temp_seg = os.path.join(temp_render_dir, f"seg_{i}.mp4")

                if seg_type in ('video', 'recorded_video'):
                    vf = (f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                          f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black,"
                          f"setsar=1")
                    cmd = [
                        FFMPEG_PATH, "-y", "-i", original_path,
                        "-vf", vf,
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                        "-c:a", "aac", "-b:a", "192k",
                        "-pix_fmt", "yuv420p",
                        temp_seg
                    ]
                    r = subprocess.run(cmd, capture_output=True, text=True)
                    if r.returncode == 0:
                        video_files_for_concat.append(temp_seg)
                    else:
                        error_text = (r.stderr or r.stdout or "").strip()
                        raise RuntimeError(f"Segment {i} dönüştürülemedi: {error_text[-1000:]}")
                else:
                    audio_dur = segment['duration']
                    temp_seg_audio = os.path.join(temp_render_dir, f"seg_audio_{i}.mp4")
                    cmd = [
                        FFMPEG_PATH, "-y",
                        "-loop", "1", "-framerate", "30",
                        "-t", str(audio_dur),
                        "-i", placeholder_image,
                        "-i", original_path,
                        "-vf", f"scale={target_width}:{target_height},setsar=1",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                        "-c:a", "aac", "-b:a", "192k",
                        "-pix_fmt", "yuv420p",
                        "-shortest",
                        temp_seg_audio
                    ]
                    r = subprocess.run(cmd, capture_output=True, text=True)
                    if r.returncode == 0:
                        video_files_for_concat.append(temp_seg_audio)
                    else:
                        error_text = (r.stderr or r.stdout or "").strip()
                        raise RuntimeError(f"Ses segmenti {i} video parçasına dönüştürülemedi: {error_text[-1000:]}")

            # GÜNCELLEME (2.2.6): Sadece moda uygun manifest yazılır; diğeri
            # için b"" gönderilir. Boş manifest C++'a gönderilseydi -22
            # hatası oluşabilirdi (C++ tarafında da artık defans var ama
            # Python tarafını da temiz tutuyoruz).
            if is_audio_only:
                with open(audio_manifest_path, 'w', encoding='utf-8') as f:
                    for p in audio_files_for_concat:
                        safe = p.replace("'", "'\\''")
                        f.write(f"file '{safe}'\n")
                video_manifest_arg = b""
                audio_manifest_arg = b"audio_list.txt"
            else:
                with open(video_manifest_path, 'w', encoding='utf-8') as f:
                    for p in video_files_for_concat:
                        safe = p.replace("'", "'\\''")
                        f.write(f"file '{safe}'\n")
                video_manifest_arg = b"video_list.txt"
                audio_manifest_arg = b""

            progress.setLabelText("FFmpeg ile birleştiriliyor...")
            progress.setValue(len(self.media_queue))
            QApplication.processEvents()

            result = self.media_engine.export_timeline_media(
                output_file_path.encode('utf-8'),
                temp_render_dir.encode('utf-8'),
                video_manifest_arg,
                audio_manifest_arg,
                fmt.encode('utf-8')
            )
            progress.setValue(len(self.media_queue) + 5)

            if result == 0:
                self.show_message_box("Dışa Aktarma Başarılı",
                                      f"Medya başarıyla oluşturuldu:\n{output_file_path}")
            else:
                self.show_message_box("Dışa Aktarma Hatası",
                                      f"İşlem başarısız oldu. Hata kodu: {result}\n"
                                      f"Konsol loglarını kontrol edin.")
        except InterruptedError:
            print("Dışa aktarma kullanıcı tarafından iptal edildi.")
        except Exception as e:
            traceback.print_exc()
            self.show_message_box("Dışa Aktarma Hatası", f"Beklenmeyen hata: {str(e)}")
        finally:
            progress.close()
            try:
                shutil.rmtree(temp_render_dir)
            except OSError:
                pass

    # ============================================================
    # ESKİ EXPORT (uyumluluk için bırakıldı; yeni akışta kullanılmıyor)
    # ============================================================
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
                    f.write(f"{segment['type']},{temp_segment_filename},{segment['abbreviation']},{segment['original_ext']}\n")
                    shutil.copy2(segment['path'], os.path.join(temp_export_dir, temp_segment_filename))
                    self.progress_bar.setValue(int(((i + 1) / len(self.media_queue)) * 90))
                    QApplication.processEvents()

            archive_result = None
            if hasattr(self.media_engine, 'archive_segments_with_compression'):
                archive_result = self.media_engine.archive_segments_with_compression(
                    target_path.encode('utf-8'),
                    temp_export_dir.encode('utf-8'),
                    manifest_file_name.encode('utf-8'),
                    compression.encode('utf-8')
                )
            else:
                archive_result = self.media_engine.archive_segments(
                    target_path.encode('utf-8'),
                    temp_export_dir.encode('utf-8'),
                    manifest_file_name.encode('utf-8')
                )
            self.progress_bar.setValue(100)
            self.time_estimate_label.setText("Kayıt tamamlandı!")

            if archive_result == 0:
                self.current_project_path = target_path
                self.show_message_box("Kayıt Başarılı",
                                      f"Proje kaydedildi ({compression}):\n{target_path}")
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

    def _extract_audio_from_video(self, video_path, output_wav_path):
        cmd = [
            FFMPEG_PATH, "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "1",
            "-y", output_wav_path
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg extraction error: {e.stderr}")
            return False

    def _replace_audio_in_video(self, video_path, audio_wav_path, output_video_path):
        cmd = [
            FFMPEG_PATH, "-i", video_path, "-i", audio_wav_path,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-map", "0:v:0", "-map", "1:a:0", "-shortest",
            "-y", output_video_path
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg remux error: {e.stderr}")
            return False

    def _apply_filter_to_media(self, original_path, media_type, original_name, callback):
        if not self.noise_filter_enabled or media_type == 'media_archive':
            if callback: callback(original_path, media_type, original_name)
            return

        if self.core_window_ref is None:
            print("Python: Core window bağlantısı yok; medya orijinal haliyle içe aktarılıyor.")
            if callback:
                callback(original_path, media_type, original_name)
            return

        temp_dir = tempfile.mkdtemp(prefix="media_filter_")
        def cleanup_temp():
            try: shutil.rmtree(temp_dir)
            except Exception as e: print(f"Temp cleanup error: {e}")

        if media_type == 'audio':
            def on_audio_filtered(success, output_path, message):
                if success and output_path and os.path.exists(output_path):
                    callback(output_path, media_type, original_name)
                else:
                    callback(original_path, media_type, original_name)
                cleanup_temp()
            self.core_window_ref.process_audio_with_filter(original_path, on_audio_filtered)

        elif media_type == 'video':
            extracted_audio = os.path.join(temp_dir, "extracted_audio.wav")
            if not self._extract_audio_from_video(original_path, extracted_audio):
                callback(original_path, media_type, original_name); cleanup_temp(); return
            def on_video_audio_filtered(success, filtered_audio_path, message):
                if success and filtered_audio_path and os.path.exists(filtered_audio_path):
                    base, ext = os.path.splitext(original_path)
                    output_video = f"{base}_filtered{ext}"
                    if self._replace_audio_in_video(original_path, filtered_audio_path, output_video):
                        callback(output_video, media_type, original_name)
                    else:
                        callback(original_path, media_type, original_name)
                else:
                    callback(original_path, media_type, original_name)
                cleanup_temp()
            self.core_window_ref.process_audio_with_filter(extracted_audio, on_video_audio_filtered)
        else:
            callback(original_path, media_type, original_name); cleanup_temp()

    def select_media_files(self):
        all_video_formats = "*.mp4 *.avi *.mov *.mkv *.webm *.flv *.rec"
        all_audio_formats = "*.mp3 *.wav *.ogg *.flac *.aac *.m4a *.saund"
        custom_archive_formats = "*.media"
        filter_str = (f"Tüm Desteklenen Medya ({all_video_formats} {all_audio_formats} {custom_archive_formats});;"
                      f"Medya Arşivleri ({custom_archive_formats});;"
                      f"Video ({all_video_formats});;"
                      f"Ses ({all_audio_formats});;"
                      f"Tüm Dosyalar (*)")
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Medya Dosyalarını Seç", DEFAULT_BASE_DIR, filter_str)
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
            self._process_media_archive(original_path)
            self._import_index += 1
            self._import_progress.setValue(self._import_index)
            QTimer.singleShot(10, self._import_next)
        elif media_type != 'unknown':
            def on_filtered(file_path, mtype, orig_name):
                self.add_media_to_queue(file_path, mtype, orig_name)
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
                    if len(parts) == 4:
                        seg_type, seg_path, abbreviation, original_ext = parts
                        full_seg_path = os.path.join(temp_extract_dir, os.path.basename(seg_path))
                        if not os.path.exists(full_seg_path): continue
                        segments_to_add.append({'path': full_seg_path, 'type': seg_type,
                                                'original_name_prefix': os.path.splitext(os.path.basename(full_seg_path))[0]})
            for seg_data in segments_to_add:
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
                        'original_ext': original_ext_seg,
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
        if self.media_engine:
            delete_result = self.media_engine.delete_media_file(deleted_file_path.encode('utf-8'))
            if delete_result != 0:
                self.show_message_box("Uyarı", f"'{segment_to_delete['abbreviation']}' diskten silinemedi (kod: {delete_result}).")
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
        original_source_ext = original_segment.get('original_ext', '.mp4')
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

        cut_result = self.media_engine.cut_media_segment(
            original_file_path.encode('utf-8'), relative_cut_point_ms,
            out1.encode('utf-8'), out2.encode('utf-8'),
            original_segment['type'].encode('utf-8'))
        if cut_result != 0:
            self.show_message_box("Hata", f"Kesme başarısız. Kod: {cut_result}"); return

        d1 = self.media_engine.get_media_duration_ms(out1.encode('utf-8')) if os.path.exists(out1) else -1
        d2 = self.media_engine.get_media_duration_ms(out2.encode('utf-8')) if os.path.exists(out2) else -1
        if d1 == -1 or d2 == -1:
            self.show_message_box("Hata", "Yeni segment süreleri alınamadı; orijinal medya korunuyor.")
            if os.path.exists(out1): os.remove(out1)
            if os.path.exists(out2): os.remove(out2)
            return
        dur1_sec = d1 / 1000.0; dur2_sec = d2 / 1000.0
        if dur1_sec < self.MIN_SEGMENT_DURATION_SEC or dur2_sec < self.MIN_SEGMENT_DURATION_SEC:
            self.show_message_box("Uyarı", "Kesme sonucu parçalardan biri 1.1sn'den kısa olduğu için işlem geri alındı.")
            if os.path.exists(out1): os.remove(out1)
            if os.path.exists(out2): os.remove(out2)
            return
        add1 = dur1_sec > 0.001; add2 = dur2_sec > 0.001

        try:
            os.remove(original_file_path)
        except OSError as e:
            print(f"Orijinal silinemedi: {e}")
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
            self.player.setPosition(self.paused_position)
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
        if self.player:
            if self.current_media_index != -1:
                relative_play_position_ms = max(0, int(self.position * 1000))
                self.player.setPosition(relative_play_position_ms)
                self.player.play()
            else:
                self.show_message_box("Hata", "Oynatılacak segment yok.")
        else:
            self.show_message_box("Hata", "Medya oynatılamadı.")

    def toggle_play_pause(self):
        if not self.media_queue:
            self.show_message_box("Uyarı", "Önce medya yükleyin!"); return
        if self.is_recording and (self.is_camera_mode_selected or self.is_audio_mode_selected):
            self.show_message_box("Uyarı", "Kayıt aktifken medya oynatılamaz."); return
        if self.player.state() == QMediaPlayer.PlayingState:
            self.paused_position = self.player.position() / 1000.0
            self.player.pause()
        else:
            if self.current_media_index == -1:
                if self.media_queue:
                    self.current_media_index = 0
                    self.position = 0
                    self.paused_position = 0
                    self.timeline.set_media_segments(self.media_queue, self.current_media_index)
                    self.timeline.set_selected_segment(self.current_media_index)
                    self.timeline.set_position(self.position)
                    self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
                    self._set_media_to_player(self.current_media_index)
                    QTimer.singleShot(50, self._perform_play)
                else:
                    self.show_message_box("Uyarı", "Oynatılacak medya yok."); return
            self._set_media_to_player(self.current_media_index)
            current_segment = self.media_queue[self.current_media_index]
            max_duration = max(0.0, float(current_segment.get('duration', 0.0)))
            self.position = max(0.0, min(float(self.paused_position), max_duration))
            self.paused_position = self.position
            self.timeline.set_position(self.position)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            QTimer.singleShot(50, self._perform_play)

    def _toggle_sequence_play_mode(self):
        if not self.media_queue:
            self.show_message_box("Uyarı", "Sıralı oynatılacak medya yok."); return
        if self.is_recording:
            self.show_message_box("Uyarı", "Kayıt aktifken mod değiştirilemez."); return
        self.is_sequence_play_active = not self.is_sequence_play_active
        self._update_sequence_play_button_state()

    def _advance_to_next_segment(self):
        if not self.media_queue: return
        self.stop_media()
        next_index = self.current_media_index + 1
        if next_index < len(self.media_queue):
            self.current_media_index = next_index
            self.position = 0
            self.paused_position = 0
            self.player.stop()
            self.player.setMedia(QMediaContent())
            QApplication.processEvents()
            self._set_media_to_player(self.current_media_index)
            self.timeline.set_media_segments(self.media_queue, self.current_media_index)
            self.timeline.set_selected_segment(self.current_media_index)
            self.timeline.set_position(self.position)
            self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))
            self._save_state()
            if self.is_sequence_play_active:
                QTimer.singleShot(50, self._perform_play)
        else:
            self.stop_media()
            self.current_media_index = -1
            self.position = 0
            self.paused_position = 0
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
        self.video_output_widget.hide()
        self.audio_icon_label.hide()
        self.camera_preview_label.hide()
        self.timeline.set_position(self.position)
        self.current_time_label.setText(self.format_time_display_with_ms(self._get_overall_timeline_position()))

    def _set_media_to_player(self, index):
        if index < 0 or index >= len(self.media_queue):
            self.player.setMedia(QMediaContent()); return
        current_media_info = self.media_queue[index]
        media_url = QUrl.fromLocalFile(current_media_info['path'])
        self.player.setMedia(QMediaContent(media_url))
        self.player.setPlaybackRate(float(self.playback_speed_box.currentText()))
        if current_media_info['type'] in ['video', 'recorded_video']:
            self.audio_icon_label.hide()
            self.camera_preview_label.hide()
            self.video_output_widget.show()
            self.player.setVideoOutput(self.video_widget)
        elif current_media_info['type'] in ['audio', 'recorded_audio']:
            self.video_output_widget.hide()
            self.camera_preview_label.hide()
            self.audio_icon_label.show()
            self.player.setVideoOutput(None)
        elif current_media_info['type'] == 'media_archive':
            self.player.setMedia(QMediaContent())
            self.video_output_widget.hide()
            self.camera_preview_label.hide()
            self.audio_icon_label.hide()
            self.show_message_box("Bilgi", ".media arşivi doğrudan oynatılamaz.")
            return
        else:
            self.player.setMedia(QMediaContent())

    def update_position(self):
        if self.current_media_index == -1: return
        if self.player.duration() <= 0:
            return
        current_player_time_ms = self.player.position()
        if current_player_time_ms == -1: return
        try:
            segment_duration = max(0.0, float(self.media_queue[self.current_media_index].get('duration', 0.0)))
        except (TypeError, ValueError):
            segment_duration = 0.0
        self.position = max(0.0, min(current_player_time_ms / 1000.0, segment_duration))
        self.paused_position = self.position
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
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.setPosition(int(new_position_in_segment_ms))
        else:
            self._set_media_to_player(self.current_media_index)
            self.player.setPosition(int(new_position_in_segment_ms))
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
                self.is_recording = False
                if hasattr(self, 'audio_mode_btn'): self.audio_mode_btn.setText("Sound")
                self._update_record_button_state()
            else:
                event.ignore(); return
        self._stop_all_recording_processes()
        if self.player.state() != QMediaPlayer.StoppedState:
            self.player.stop()
        self.player.setMedia(QMediaContent())
        if self.media_engine:
            try:
                self.media_engine.terminate_audio_engine()
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
        else:
            event.accept()
        if os.path.exists(self.audio_record_dir) and len(os.listdir(self.audio_record_dir)) > 0:
            try:
                for f in os.listdir(self.audio_record_dir):
                    if re.match(r"recorded_audio_segment_\d+\.wav$", f):
                        os.remove(os.path.join(self.audio_record_dir, f))
            except OSError as e:
                print(f"Ses temp klasörü temizleme hatası: {e}")

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
                self.player.setPosition(int(self.position * 1000))
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
                self.player.setPosition(0)
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

    def get_duration_from_path(self, path):
        duration_ms = -1
        if self.media_engine:
            try:
                duration_ms = self.media_engine.get_media_duration_ms(path.encode('utf-8'))
            except Exception as e:
                print(f"C++ get_media_duration_ms hatası: {e}")
                duration_ms = -1
        if duration_ms >= 0:
            duration = duration_ms / 1000.0
            if math.isfinite(duration) and duration > 0.0:
                return duration
        temp_player = QMediaPlayer()
        temp_player.setMedia(QMediaContent(QUrl.fromLocalFile(path)))
        start_time = time.time()
        while temp_player.duration() <= 0 and (time.time() - start_time) * 1000 < 5000:
            QApplication.processEvents(); time.sleep(0.01)
        duration = temp_player.duration() / 1000.0
        temp_player.setMedia(QMediaContent())
        return duration if math.isfinite(duration) and duration > 0.0 else -1

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

    def add_media_to_queue(self, path, media_type, original_name=None):
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
            if self.current_media_index == -1 or not self.media_queue:
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
        except IOError:
            self.show_message_box("Hata", f"Dosya kopyalanamadı: {os.path.basename(path)}")
            return False

    def _perform_cut_at_position(self, segment_index_to_cut: int, cut_point_sec: float):
        if not self.media_engine: return None, None
        if segment_index_to_cut < 0 or segment_index_to_cut >= len(self.media_queue): return None, None
        original_segment = self.media_queue[segment_index_to_cut]
        original_file_path = original_segment['path']
        original_source_ext = original_segment.get('original_ext', '.mp4')
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
        cut_result = self.media_engine.cut_media_segment(
            original_file_path.encode('utf-8'), relative_cut_point_ms,
            out1.encode('utf-8'), out2.encode('utf-8'),
            original_segment['type'].encode('utf-8'))
        if cut_result != 0: return None, None
        d1 = self.media_engine.get_media_duration_ms(out1.encode('utf-8')) if os.path.exists(out1) else -1
        d2 = self.media_engine.get_media_duration_ms(out2.encode('utf-8')) if os.path.exists(out2) else -1
        if d1 == -1 or d2 == -1:
            if os.path.exists(out1): os.remove(out1)
            if os.path.exists(out2): os.remove(out2)
            return None, None
        dur1_sec = d1 / 1000.0; dur2_sec = d2 / 1000.0
        if dur1_sec < self.MIN_SEGMENT_DURATION_SEC or dur2_sec < self.MIN_SEGMENT_DURATION_SEC:
            if os.path.exists(out1): os.remove(out1)
            if os.path.exists(out2): os.remove(out2)
            return None, None
        try:
            os.remove(original_file_path)
        except OSError as e:
            print(f"Orijinal silinemedi: {e}")
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
            self.player.setPosition(int(self.position * 1000))
        self._save_state()

    def handle_segment_resize_request(self, index: int, delta_ms: int, is_expanding: bool):
        if not self.media_queue or index < 0 or index >= len(self.media_queue): return
        segment = self.media_queue[index]
        original_duration_ms = int(segment['duration'] * 1000)
        new_duration_ms = original_duration_ms + int(delta_ms)
        new_duration_ms = max(int(self.MIN_SEGMENT_DURATION_SEC * 1000), min(original_duration_ms, new_duration_ms))
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

    def _restore_state(self, state):
        self.stop_media()
        self.is_sequence_play_active = False
        self._update_sequence_play_button_state()
        self.media_queue = copy.deepcopy(state.get('media_queue', []))
        cleaned_queue = []
        for segment in self.media_queue:
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
            self.player.setPosition(int(self.position * 1000))
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
                self.player.setPosition(int(self.position * 1000))
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
    def _handle_camera_button_click(self):
        self.show_message_box("Bilgi", "Bu fonksiyon geliştirme aşamasındadır.")

    def _toggle_audio_mode_selection(self):
        if not self.media_engine:
            self.show_message_box("Hata", "Medya motoru yüklenemedi."); return
        if self.player.state() == QMediaPlayer.PlayingState:
            self.show_message_box("Uyarı", "Medya oynatma aktif. Durdurun."); return
        if self.is_stopping_audio_recording:
            self.show_message_box("Bilgi", "Durdurma zaten sürüyor."); return
        if self.is_sequence_play_active:
            self.is_sequence_play_active = False
            self._update_sequence_play_button_state()
            self.show_message_box("Bilgi", "Sıralı oynatma devre dışı bırakıldı.")

        if not self.is_recording:
            if self.is_camera_mode_selected:
                self.is_camera_mode_selected = False
            self.stop_media()
            self.audio_mode_btn.setEnabled(False)
            self._update_record_button_state()
            QApplication.processEvents()
            existing_rec_s_numbers = []
            for item in os.listdir(self.audio_record_dir):
                m = re.match(r'recorded_audio_(\d+)\.wav$', item)
                if m: existing_rec_s_numbers.append(int(m.group(1)))
            self.recorded_audio_count = (max(existing_rec_s_numbers) if existing_rec_s_numbers else 0) + 1
            final_audio_filename = f"recorded_audio_{self.recorded_audio_count}.wav"
            self.audio_record_final_path = os.path.join(self.audio_record_dir, final_audio_filename)
            segment_pattern = os.path.join(self.audio_record_dir, "recorded_audio_segment_%03d.wav")
            result = self.media_engine.start_audio_record(
                segment_pattern.encode("utf-8"), self.audio_record_final_path.encode("utf-8"))
            if result == 0:
                self.is_recording = True
                self.is_audio_mode_selected = True
                self.audio_icon_label.show()
            else:
                self.show_message_box("Hata", f"Ses kaydı başlatılamadı. Kod: {result}.")
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
                        def add_audio(file_path):
                            if not os.path.exists(file_path):
                                self.show_message_box("Hata", "Kaydedilen ses bulunamadı."); return
                            orig_name = os.path.splitext(os.path.basename(file_path))[0]
                            self.add_media_to_queue(file_path, 'recorded_audio', orig_name)
                            try:
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                            except Exception as e:
                                print(f"Temp ses silinemedi: {e}")
                        if self.noise_filter_enabled and self.core_window_ref:
                            def on_filter_complete(success, output_path, message):
                                if success and output_path and os.path.exists(output_path):
                                    add_audio(output_path)
                                else:
                                    if os.path.exists(self.audio_record_final_path):
                                        add_audio(self.audio_record_final_path)
                                self.is_recording = False
                                self.is_audio_mode_selected = False
                                self.audio_record_final_path = None
                                self.is_stopping_audio_recording = False
                                self.audio_icon_label.hide()
                                self.audio_mode_btn.setEnabled(True)
                                self._update_record_button_state()
                            filter_started = self.core_window_ref.process_audio_with_filter(
                                self.audio_record_final_path, on_filter_complete)
                            if not filter_started:
                                add_audio(self.audio_record_final_path)
                                self.is_recording = False
                                self.is_audio_mode_selected = False
                                self.audio_record_final_path = None
                                self.is_stopping_audio_recording = False
                                self.audio_icon_label.hide()
                                self.audio_mode_btn.setEnabled(True)
                                self._update_record_button_state()
                        elif self.noise_filter_enabled:
                            progress = QProgressDialog("Ses filtresi uygulanıyor...", "İptal", 0, 100, self)
                            progress.setWindowModality(Qt.WindowModal)
                            progress.setWindowTitle("Ses İşleniyor")
                            progress.show()
                            QApplication.processEvents()
                            try:
                                filtered_path = self._apply_python_audio_filter(self.audio_record_final_path, progress)
                                add_audio(filtered_path)
                            except Exception as e:
                                self.show_message_box("Filtre Hatası", f"Filtre uygulanamadı: {e}")
                                add_audio(self.audio_record_final_path)
                            finally:
                                progress.close()
                            self.is_recording = False
                            self.is_audio_mode_selected = False
                            self.audio_record_final_path = None
                            self.is_stopping_audio_recording = False
                            self.audio_icon_label.hide()
                            self.audio_mode_btn.setEnabled(True)
                            self._update_record_button_state()
                        else:
                            add_audio(self.audio_record_final_path)
                            self.is_recording = False
                            self.is_audio_mode_selected = False
                            self.audio_record_final_path = None
                            self.is_stopping_audio_recording = False
                            self.audio_icon_label.hide()
                            self.audio_mode_btn.setEnabled(True)
                            self._update_record_button_state()
                    else:
                        self.show_message_box("Hata", "Ses birleştirme hatası.")
                        self.is_recording = False; self.is_audio_mode_selected = False
                        self.audio_record_final_path = None; self.is_stopping_audio_recording = False
                        self.audio_icon_label.hide(); self.audio_mode_btn.setEnabled(True)
                        self._update_record_button_state()
                else:
                    self.show_message_box("Hata", "Ses durdurma hatası.")
                    self.is_recording = False; self.is_audio_mode_selected = False
                    self.audio_record_final_path = None; self.is_stopping_audio_recording = False
                    self.audio_icon_label.hide(); self.audio_mode_btn.setEnabled(True)
                    self._update_record_button_state()
            except Exception as e:
                self.show_message_box("Hata", f"Ses işlemi sırasında hata: {e}")
                self.is_recording = False; self.is_audio_mode_selected = False
                self.audio_record_final_path = None; self.is_stopping_audio_recording = False
                self.audio_icon_label.hide(); self.audio_mode_btn.setEnabled(True)
                self._update_record_button_state()

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
        if self.is_sequence_play_active:
            self.sequence_play_btn.setStyleSheet(self.buttonStyle("sequence_play_active"))
        else:
            self.sequence_play_btn.setStyleSheet(self.buttonStyle("sequence_toggle"))
        self.sequence_play_btn.setEnabled(not self.is_recording)

    def _stop_all_recording_processes(self):
        if self.media_engine:
            try:
                self.media_engine.stop_camera_record()
            except Exception as e:
                print(f"stop_camera_record hatası: {e}")
            if self.is_recording and self.is_audio_mode_selected:
                try:
                    self.media_engine.stop_audio_record()
                except Exception as e:
                    print(f"stop_audio_record hatası: {e}")
        if self.video_record_thread and self.video_record_thread.is_alive():
            self.video_record_thread.stop()
            self.video_record_thread.join(timeout=5)
            self.video_record_thread = None
        self.camera_timer.stop()
        self.is_recording = False

    def update_camera_frame(self):
        if not self.media_engine or not self.media_engine.is_camera_open() or \
           not self.is_recording or not self.is_camera_mode_selected:
            self.camera_preview_label.hide(); return
        out_frame = Frame()
        if self.media_engine.read_frame(ctypes.byref(out_frame)):
            frame_np = np.ctypeslib.as_array(out_frame.data, shape=(out_frame.height, out_frame.width, out_frame.channels))
            if out_frame.channels == 3:
                frame_rgb = cv2.cvtColor(frame_np, cv2.COLOR_BGR2RGB)
            elif out_frame.channels == 1:
                frame_rgb = cv2.cvtColor(frame_np, cv2.COLOR_GRAY2RGB)
            else:
                self.media_engine.free_frame_data(ctypes.byref(out_frame)); return
            h, w, ch = frame_rgb.shape
            q_image = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(self.camera_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.camera_preview_label.setPixmap(scaled_pixmap)
            if self.is_recording and self.video_record_thread and self.video_record_thread.is_alive():
                bgr_frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                try:
                    self.video_frame_queue.put_nowait(bgr_frame)
                except queue.Full:
                    pass
            self.media_engine.free_frame_data(ctypes.byref(out_frame))
        else:
            self.camera_timer.stop()
            self.camera_preview_label.hide()
            if self.is_recording and self.is_camera_mode_selected:
                self._stop_all_recording_processes()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = MediaEditor()
    editor.showMaximized()
    sys.exit(app.exec_())
