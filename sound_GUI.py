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

import sys
import os
import ctypes
import json
import tempfile
import shutil
import subprocess
import time
import soundfile as sf
import numpy as np
import zipfile

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QComboBox, QScrollArea, QSizePolicy, QMessageBox, QSlider, QSplitter,
    QProgressBar, QTextEdit, QAction, QMenu, QShortcut
)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, QDir, QByteArray, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QCursor, QBrush, QPainterPath, QIcon, QPixmap, QFont, QTextCursor, QTextBlockFormat, QKeySequence
from PyQt5.QtSvg import QSvgRenderer

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Sabitler
BACKGROUND = QColor('#383838')
WAVE_COLOR = QColor('#606060')
CURSOR_COLOR = QColor('#F44336')
SELECT_COLOR = QColor('#A0A0A0')

SVG_SAVE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V7L17 3ZM12 17C10.34 17 9 15.66 9 14C9 12.34 10.34 11 12 11C13.66 11 15 12.34 15 14C15 15.66 13.66 17 12 17Z" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_UNDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19C15.866 19 19 15.866 19 12C19 8.13401 15.866 5 12 5C8.13401 5 5 8.13401 5 12C5 13.7909 5.70014 15.4293 6.84594 16.6386L5 18M5 18H9M5 18V14" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_REDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5C8.13401 5 5 8.13401 5 12C5 15.866 8.13401 19 12 19C15.866 19 19 12 19 12C19 10.2091 18.2999 8.57074 17.1541 7.3614L19 6M19 6H15M19 6V10" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

def create_svg_icon(svg_content, size=20, color="#aaa"):
    modified_svg_content = svg_content.replace('stroke="#aaa"', f'stroke="{color}"').replace('fill="#aaa"', f'fill="{color}"')
    renderer = QSvgRenderer(QByteArray(modified_svg_content.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

SETTINGS_DIR = os.path.join(QDir.homePath(), '.config', 'concept_sound_editor')
TEMP_RAW_RECORDING_FILE = os.path.join(SETTINGS_DIR, "temp_raw_recording.wav")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")

lib = None
try:
    if sys.platform.startswith('win'):
        lib_name = 'sound_engine.dll'
    elif sys.platform.startswith('linux'):
        lib_name = 'libsound_engine.so'
    elif sys.platform.startswith('darwin'):
        lib_name = 'libsound_engine.dylib'
    else:
        lib_name = 'sound_engine'

    lib_path = resource_path(os.path.join('lib', lib_name))
    lib = ctypes.CDLL(lib_path)

    # --- C++ Fonksiyon İmzalarını Tanımla ---
    lib.create_audio_engine.restype = ctypes.c_void_p
    lib.destroy_audio_engine.argtypes = [ctypes.c_void_p]
    lib.destroy_audio_engine.restype = ctypes.c_int
    lib.load_audio_files.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p), ctypes.c_int]
    lib.load_audio_files.restype = ctypes.c_int
    lib.play_audio.argtypes = [ctypes.c_void_p]
    lib.play_audio.restype = ctypes.c_int
    lib.pause_audio.argtypes = [ctypes.c_void_p]
    lib.pause_audio.restype = ctypes.c_int
    lib.stop_audio.argtypes = [ctypes.c_void_p]
    lib.stop_audio.restype = ctypes.c_int
    lib.get_position_ms.argtypes = [ctypes.c_void_p]
    lib.get_position_ms.restype = ctypes.c_int
    lib.get_duration_ms.argtypes = [ctypes.c_void_p]
    lib.get_duration_ms.restype = ctypes.c_int
    lib.get_envelope_length.argtypes = [ctypes.c_void_p]
    lib.get_envelope_length.restype = ctypes.c_int
    lib.get_envelope_data.argtypes = [ctypes.c_void_p]
    lib.get_envelope_data.restype = ctypes.POINTER(ctypes.c_float)
    lib.set_speed.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_speed.restype = ctypes.c_int
    lib.set_play_position_ms.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.set_play_position_ms.restype = ctypes.c_int
    lib.get_is_playing.argtypes = [ctypes.c_void_p]
    lib.get_is_playing.restype = ctypes.c_int
    lib.delete_audio_segment.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    lib.delete_audio_segment.restype = ctypes.c_int
    lib.insert_audio_file.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    lib.insert_audio_file.restype = ctypes.c_int

    # Benzer sesleri otomatik tespit edip silme fonksiyonu imzası
    lib.detect_and_delete_similar.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_float]
    lib.detect_and_delete_similar.restype = ctypes.c_int

    # Yeni eklenen kalınlığa (amplitude) göre otomatik boşluk silme C++ imzası
    lib.delete_segments_by_thickness.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    lib.delete_segments_by_thickness.restype = ctypes.c_int

    lib.start_microphone_recording.argtypes = [ctypes.c_void_p]
    lib.start_microphone_recording.restype = ctypes.c_int
    lib.stop_microphone_recording.argtypes = [ctypes.c_void_p]
    lib.stop_microphone_recording.restype = ctypes.c_int
    lib.save_recorded_audio_to_file.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.save_recorded_audio_to_file.restype = ctypes.c_int
    lib.save_audio_to_file.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.save_audio_to_file.restype = ctypes.c_int
    
    # Undo / Redo C++ Imzaları
    lib.undo_audio.argtypes = [ctypes.c_void_p]
    lib.undo_audio.restype = ctypes.c_int
    lib.redo_audio.argtypes = [ctypes.c_void_p]
    lib.redo_audio.restype = ctypes.c_int
    lib.can_undo_audio.argtypes = [ctypes.c_void_p]
    lib.can_undo_audio.restype = ctypes.c_int
    lib.can_redo_audio.argtypes = [ctypes.c_void_p]
    lib.can_redo_audio.restype = ctypes.c_int

    # Mikrofon efektleri
    lib.set_mic_noise_gate_threshold.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_mic_noise_gate_threshold.restype = ctypes.c_int
    lib.set_mic_noise_gate_release.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_mic_noise_gate_release.restype = ctypes.c_int
    lib.set_mic_high_pass_filter_cutoff.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_mic_high_pass_filter_cutoff.restype = ctypes.c_int
    lib.set_mic_input_gain.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_mic_input_gain.restype = ctypes.c_int
    lib.set_mic_low_pass_filter_cutoff.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_mic_low_pass_filter_cutoff.restype = ctypes.c_int
    lib.set_mic_reverb_reduction_level.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.set_mic_reverb_reduction_level.restype = ctypes.c_int
    lib.set_mic_de_esser_level.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.set_mic_de_esser_level.restype = ctypes.c_int
    lib.set_mic_de_hum_level.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.set_mic_de_hum_level.restype = ctypes.c_int
    lib.set_mic_compressor_threshold.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_mic_compressor_threshold.restype = ctypes.c_int
    lib.set_mic_compressor_ratio.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_mic_compressor_ratio.restype = ctypes.c_int
    lib.set_mic_compressor_attack.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_mic_compressor_attack.restype = ctypes.c_int
    lib.set_mic_compressor_release.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_mic_compressor_release.restype = ctypes.c_int
    lib.set_mic_compressor_makeup_gain.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_mic_compressor_makeup_gain.restype = ctypes.c_int
    lib.set_mic_eq_gain.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_mic_eq_gain.restype = ctypes.c_int
    lib.set_mic_eq_frequency.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_mic_eq_frequency.restype = ctypes.c_int
    lib.set_mic_eq_q.argtypes = [ctypes.c_void_p, ctypes.c_float]
    lib.set_mic_eq_q.restype = ctypes.c_int
    lib.calculate_eq_coefficients.argtypes = [ctypes.c_void_p]
    lib.calculate_eq_coefficients.restype = ctypes.c_int
    print(f"C++ library '{lib_path}' loaded successfully.")

except OSError as e:
    print(f"Error: C++ library could not be loaded. Please ensure '{lib_path}' is present and accessible.")
    print(f"Detail: {e}")
    lib = None
    if QApplication.instance():
         QMessageBox.critical(None, 'Library Error', f"C++ library '{lib_path}' could not be loaded.\n{e}")
    else:
        print("Error message box cannot be shown because GUI is not initialized.")

class WaveformWidget(QWidget):
    def __init__(self, parent=None, sound_editor_window=None):
        super().__init__(parent)
        self.sound_editor_window = sound_editor_window
        self.envelope_data = None
        self.envelope_length = 0
        self.duration_ms = 0
        self.current_position_ms = 0
        self.playhead_x_ratio = 0.1
        self.display_duration_ms = 300000
        self.width_scale = 1
        self.zoom_level = 1
        self.selected_segments = []
        self.split_points_ms = []
        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background:#282828;")

    def set_width_scale(self, scale: int):
        self.width_scale = scale
        self.display_duration_ms = 300000 / scale
        self.update()

    def set_audio_data(self, envelope_data, envelope_length, duration_ms):
        self.envelope_data = envelope_data
        self.envelope_length = envelope_length
        self.duration_ms = duration_ms
        self.current_position_ms = 0
        self.selected_segments = []
        self.split_points_ms = []
        self.update()

    def set_position(self, position_ms):
        self.current_position_ms = position_ms
        self.update()

    def set_zoom_level(self, level: int):
        level = max(1, min(7, level))
        self.zoom_level = level
        if self.duration_ms > 0:
            self.display_duration_ms = max(1000, self.duration_ms // level)
        self.update()

    def add_split_point(self, split_ms):
        if 0 < split_ms < self.duration_ms and split_ms not in self.split_points_ms:
            self.split_points_ms.append(split_ms)
            self.split_points_ms.sort()
            print(f"Split point added: {split_ms} ms. All points: {self.split_points_ms}")
        else:
            print(f"Invalid or existing split point: {split_ms} ms. Not added.")
        self.clear_selection()
        self.update()

    def get_selected_segments(self):
        return self.selected_segments

    def clear_selection(self):
        self.selected_segments = []
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            click_x = event.x()
            self.selected_segments = []
            if self.duration_ms > 0:
                click_time_ms = self.map_pixel_to_time(click_x)
                start_boundary_ms = 0
                end_boundary_ms = self.duration_ms
                for sp in reversed(self.split_points_ms):
                    if sp <= click_time_ms:
                        start_boundary_ms = sp
                        break
                for sp in self.split_points_ms:
                    if sp > click_time_ms:
                        end_boundary_ms = sp
                        break
                if start_boundary_ms != end_boundary_ms:
                    self.selected_segments.append((start_boundary_ms, end_boundary_ms))
                    print(f"Segment selected: {start_boundary_ms} ms - {end_boundary_ms} ms")
            self.update()

    def wheelEvent(self, event):
        if not self.sound_editor_window or not self.sound_editor_window.lib or not self.sound_editor_window.audio_engine:
            return
        duration_ms = self.sound_editor_window.lib.get_duration_ms(self.sound_editor_window.audio_engine)
        if duration_ms == 0:
            return
        delta = event.angleDelta().y()
        scroll_step_ms = self.sound_editor_window.scroll_step_ms
        scroll_amount_ms = int((delta / 120) * scroll_step_ms)
        current_pos_ms = self.sound_editor_window.lib.get_position_ms(self.sound_editor_window.audio_engine)
        new_pos_ms = current_pos_ms + scroll_amount_ms
        new_pos_ms = max(0, min(new_pos_ms, duration_ms))
        result = self.sound_editor_window.lib.set_play_position_ms(self.sound_editor_window.audio_engine, ctypes.c_int(new_pos_ms))
        if result == 0:
            self.set_position(new_pos_ms)

    def map_pixel_to_time(self, x_coordinate):
        width = self.width()
        if width <= 0 or self.duration_ms == 0 or self.envelope_length == 0:
            return -1
        ms_per_envelope_point = self.duration_ms / self.envelope_length if self.envelope_length > 0 else 0
        if ms_per_envelope_point == 0: return -1
        points_to_display = self.display_duration_ms / ms_per_envelope_point
        playhead_x = int(width * self.playhead_x_ratio)
        scrollable_width = width - playhead_x
        if scrollable_width <= 0 or points_to_display <= 0:
            return -1
        current_envelope_index_float = self.current_position_ms / ms_per_envelope_point
        envelope_points_before_playhead = playhead_x / (scrollable_width / points_to_display) if points_to_display > 0 else 0
        start_envelope_index_float_at_x0 = current_envelope_index_float - envelope_points_before_playhead
        target_envelope_index_float = start_envelope_index_float_at_x0 + (x_coordinate / (scrollable_width / points_to_display)) if points_to_display > 0 else 0
        time_ms = int(target_envelope_index_float * ms_per_envelope_point)
        time_ms = max(0, min(time_ms, self.duration_ms))
        return time_ms

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()
        painter.fillRect(0, 0, width, height, self.palette().window())
        if self.envelope_data is None or self.envelope_length == 0 or width <= 0 or height <= 0 or self.duration_ms == 0:
            painter.setPen(QColor('white'))
            painter.drawText(self.rect(), Qt.AlignCenter, "Audio file not loaded or cannot be drawn.")
            painter.end()
            return
        center_y = height / 2
        waveform_height = height / 3.0
        ms_per_envelope_point = self.duration_ms / self.envelope_length if self.envelope_length > 0 else 0
        if ms_per_envelope_point == 0:
            painter.end()
            return
        points_to_display = self.display_duration_ms / ms_per_envelope_point
        playhead_x = int(width * self.playhead_x_ratio)
        scrollable_width = width - playhead_x
        if scrollable_width <= 0 or points_to_display <= 0:
            painter.end()
            return
        current_envelope_index_float = self.current_position_ms / ms_per_envelope_point
        envelope_points_before_playhead = playhead_x / (scrollable_width / points_to_display) if points_to_display > 0 else 0
        start_envelope_index_float_at_x0 = current_envelope_index_float - envelope_points_before_playhead
        for i in range(width):
            envelope_index_float = start_envelope_index_float_at_x0 + (i / (scrollable_width / points_to_display)) if points_to_display > 0 else 0
            envelope_index = int(envelope_index_float)
            pixel_time_ms = (start_envelope_index_float_at_x0 + (i / (scrollable_width / points_to_display))) * ms_per_envelope_point if points_to_display > 0 else 0
            pixel_time_ms = max(0, min(int(pixel_time_ms), self.duration_ms))
            y_top = center_y
            y_bottom = center_y
            if 0 <= envelope_index < self.envelope_length:
                amplitude = self.envelope_data[envelope_index]
                y_top = center_y - amplitude * (waveform_height / 2)
                y_bottom = center_y + amplitude * (waveform_height / 2)
            is_selected = False
            for seg_start_ms, seg_end_ms in self.selected_segments:
                if seg_start_ms <= pixel_time_ms < seg_end_ms:
                    is_selected = True
                    break
            if is_selected:
                painter.setPen(QPen(SELECT_COLOR, 1))
            else:
                painter.setPen(QPen(WAVE_COLOR, 1))
            painter.drawLine(i, int(y_top), i, int(y_bottom))
        painter.setPen(QPen(CURSOR_COLOR, 2))
        painter.drawLine(playhead_x, 0, playhead_x, height)
        painter.end()


class ResizeHandle(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(6)
        self.setCursor(Qt.SizeVerCursor)
        self.setStyleSheet("background-color: #444; border-top: 1px solid #666; border-bottom: 1px solid #222;")
        self.is_dragging = False
        self.start_y = 0

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.start_y = event.globalY()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging and self.parent():
            delta = self.start_y - event.globalY()
            self.start_y = event.globalY()
            current_height = self.parent().height()
            new_height = current_height + delta
            new_height = max(80, min(500, new_height))
            self.parent().setFixedHeight(new_height)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False


class TemporaryTextPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #333; border: none;")
        self.setFixedHeight(120)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.resize_handle = ResizeHandle(self)
        layout.addWidget(self.resize_handle)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(" Text ")
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #252525;
                color: #ffffff;
                border: none;
                padding: 10px;
                font-family: sans-serif;
            }
        """)
        self.text_edit.setFont(QFont("sans-serif", 14))
        layout.addWidget(self.text_edit)


class SoundEditorWindow(QWidget):
    DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')

    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        self.audio_engine = None
        self.lib = lib
        self.is_recording_mode = False
        self.scroll_step_ms = 5000
        self.current_file = None
        self._engine_cleaned = False

        self.current_text_font_size = 14
        self.waveform_scale = 1

        self._load_settings()

        if self.lib:
            self.audio_engine = self.lib.create_audio_engine()
            if not self.audio_engine:
                QMessageBox.critical(self, 'Error', 'C++ AudioEngine could not be created.')
                self.lib = None
            else:
                self._set_default_microphone_effects()
        else:
            QMessageBox.critical(self, 'Error', 'Audio engine is not available because the C++ library could not be loaded.')

        self.waveform_widget = WaveformWidget(self, sound_editor_window=self)
        self.waveform_widget.set_width_scale(self.waveform_scale)
        self.filter_overlay = None

        self.temporary_text_panel = TemporaryTextPanel(self)
        if self.panel_visible:
            self.temporary_text_panel.show()
        else:
            self.temporary_text_panel.hide()

        self.init_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(50)
        
        self.destroyed.connect(self._cleanup_engine)
        self.update_undo_redo_buttons()

    @property
    def recording(self):
        return getattr(self, 'is_recording_mode', False)

    def _cleanup_engine(self):
        if getattr(self, '_engine_cleaned', False):
            return
        self._engine_cleaned = True
        
        if self.audio_engine and self.lib:
            try:
                if self.lib.get_is_playing(self.audio_engine):
                    self.lib.stop_audio(self.audio_engine)
                self.lib.destroy_audio_engine(self.audio_engine)
                self.audio_engine = None
                print("C++ AudioEngine stopped and cleaned up safely.")
            except Exception as e:
                print(f"Error during AudioEngine cleanup: {e}")

    def hideEvent(self, event):
        if self.audio_engine and self.lib:
            try:
                if self.lib.get_is_playing(self.audio_engine):
                    self.lib.pause_audio(self.audio_engine)
                    self.btn_play.setText('Play')
            except Exception:
                pass
        super().hideEvent(event)

    def _load_settings(self):
        self.noise_filter_enabled = False
        self.scroll_step_ms = 5000
        self.panel_visible = False
        self.text_alignment_center = False
        self.current_text_font_size = 14
        self.waveform_scale = 1
        try:
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    self.noise_filter_enabled = data.get('noise_filter_enabled', False)
                    self.scroll_step_ms = data.get('scroll_step_ms', 5000)
                    self.panel_visible = data.get('panel_visible', False)
                    self.text_alignment_center = data.get('text_alignment_center', False)
                    self.current_text_font_size = data.get('text_font_size', 14)
                    self.waveform_scale = data.get('waveform_scale', 1)
        except Exception as e:
            print(f"Error loading settings: {e}")

    def _save_settings(self):
        try:
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            data = {
                'noise_filter_enabled': self.noise_filter_enabled,
                'scroll_step_ms': self.scroll_step_ms,
                'panel_visible': self.temporary_text_panel.isVisible(),
                'text_alignment_center': self.text_alignment_center,
                'text_font_size': self.current_text_font_size,
                'waveform_scale': self.waveform_scale
            }
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def _set_default_microphone_effects(self):
        if not self.lib or not self.audio_engine:
            return
        self.lib.set_mic_noise_gate_threshold(self.audio_engine, ctypes.c_float(0.000316))
        self.lib.set_mic_noise_gate_release(self.audio_engine, ctypes.c_float(20.0))
        self.lib.set_mic_high_pass_filter_cutoff(self.audio_engine, ctypes.c_float(150.0))
        self.lib.set_mic_low_pass_filter_cutoff(self.audio_engine, ctypes.c_float(10000.0))
        self.lib.set_mic_input_gain(self.audio_engine, ctypes.c_float(1.995))
        self.lib.set_mic_reverb_reduction_level(self.audio_engine, ctypes.c_int(0))
        self.lib.set_mic_de_esser_level(self.audio_engine, ctypes.c_int(0))
        self.lib.set_mic_de_hum_level(self.audio_engine, ctypes.c_int(0))
        self.lib.set_mic_compressor_threshold(self.audio_engine, ctypes.c_float(0.0))
        self.lib.set_mic_compressor_ratio(self.audio_engine, ctypes.c_float(1.0))
        self.lib.set_mic_compressor_attack(self.audio_engine, ctypes.c_float(5.0))
        self.lib.set_mic_compressor_release(self.audio_engine, ctypes.c_float(150.0))
        self.lib.set_mic_compressor_makeup_gain(self.audio_engine, ctypes.c_float(3.0))
        self.lib.set_mic_eq_gain(self.audio_engine, ctypes.c_float(0.0))
        self.lib.set_mic_eq_frequency(self.audio_engine, ctypes.c_float(1000.0))
        self.lib.set_mic_eq_q(self.audio_engine, ctypes.c_float(1.0))
        self.lib.calculate_eq_coefficients(self.audio_engine)
        print("Default microphone effects set in C++ engine.")

    def init_ui(self):
        self.setWindowTitle('Concept Sound Editor')
        self.resize(1000, 600)
        self.setStyleSheet('background:#383838; color:white;')
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top bar
        top_bar = QFrame()
        top_bar.setFixedHeight(40)
        top_bar.setStyleSheet('background:#222; border-bottom:1px solid #555;')
        self.toolbar_layout = QHBoxLayout(top_bar)  # Ana toolbar layout
        self.toolbar_layout.setContentsMargins(10, 5, 10, 5)

        # --- File butonu (sabit 90x30) ---
        self.file_button = QPushButton("File")
        self.file_button.setStyleSheet(self.buttonStyle())
        self.file_button.setFixedSize(90, 30)
        self.file_button.clicked.connect(self.load_files)
        self.toolbar_layout.addWidget(self.file_button)
        self.btn_file = self.file_button  # Eski referans

        # --- Quick Save butonu (sabit 30x30) ---
        self.quick_save_button = QPushButton()
        self.quick_save_button.setIcon(create_svg_icon(SVG_SAVE_ICON, size=20))
        self.quick_save_button.setStyleSheet(self.buttonStyleMini())
        self.quick_save_button.setFixedSize(30, 30)
        self.quick_save_button.setToolTip("Kaydet")
        self.quick_save_button.clicked.connect(self.saveContent)
        self.toolbar_layout.addWidget(self.quick_save_button)

        # --- Undo butonu (sabit 30x30) ---
        self.undo_button = QPushButton()
        self.undo_button.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20))
        self.undo_button.setStyleSheet(self.buttonStyleMini())
        self.undo_button.setFixedSize(30, 30)
        self.undo_button.setToolTip("Geri Al (Ctrl+Z)")
        self.undo_button.clicked.connect(self.undo_action)
        self.toolbar_layout.addWidget(self.undo_button)
        self.btn_undo = self.undo_button

        # --- Redo butonu (sabit 30x30) ---
        self.redo_button = QPushButton()
        self.redo_button.setIcon(create_svg_icon(SVG_REDO_ICON, size=20))
        self.redo_button.setStyleSheet(self.buttonStyleMini())
        self.redo_button.setFixedSize(30, 30)
        self.redo_button.setToolTip("İleri Al (Ctrl+Shift+Z)")
        self.redo_button.clicked.connect(self.redo_action)
        self.toolbar_layout.addWidget(self.redo_button)
        self.btn_redo = self.redo_button

        # --- Cut butonu (yazı boyutuna göre otomatik genişlik) ---
        self.cut_button = QPushButton("Cut")
        self.cut_button.setStyleSheet(self.buttonStyle())
        self.cut_button.setFixedHeight(30)
        self.cut_button.adjustSize()
        self.cut_button.setFixedWidth(self.cut_button.sizeHint().width() + 20)
        self.cut_button.clicked.connect(self.add_split_point_from_playhead)
        self.toolbar_layout.addWidget(self.cut_button)
        self.btn_cut = self.cut_button

# --- Similar Delete butonu (yazı boyutuna göre otomatik genişlik) ---
        self.similar_delete_button = QPushButton("::")
        # Tooltip güncellendi (Tek işlev: Kalınlığa/sessizliğe göre silme)
        self.similar_delete_button.setToolTip("Seçili alanın kalınlığındaki (volume/sessizlik) tüm boşlukları siler")
        self.similar_delete_button.setStyleSheet(self.buttonStyle())
        self.similar_delete_button.setFixedHeight(30)
        self.similar_delete_button.adjustSize()
        self.similar_delete_button.setFixedWidth(self.similar_delete_button.sizeHint().width() + 20)
        
        # Sol tık (clicked) artık önceden sağ tıkta olan kalınlık silme fonksiyonunu çalıştıracak:
        self.similar_delete_button.clicked.connect(self.delete_thickness_segments_action)
        
        # Kapatılan eski sol tık fonksiyonu:
        # self.similar_delete_button.clicked.connect(self.delete_similar_segments_action)
        
        # Kapatılan sağ tık olayı:
        # self.similar_delete_button.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.similar_delete_button.customContextMenuRequested.connect(self.delete_thickness_segments_action)
        
        self.toolbar_layout.addWidget(self.similar_delete_button)
        self.btn_similar_delete = self.similar_delete_button

        # --- Delete butonu (yazı boyutuna göre otomatik genişlik) ---
        self.delete_button = QPushButton("Delete")
        self.delete_button.setStyleSheet(self.buttonStyle())
        self.delete_button.setFixedHeight(30)
        self.delete_button.adjustSize()
        self.delete_button.setFixedWidth(self.delete_button.sizeHint().width() + 20)
        self.delete_button.clicked.connect(self.delete_selected_segments)
        self.toolbar_layout.addWidget(self.delete_button)
        self.btn_del = self.delete_button

        # --- Play butonu (yazı boyutuna göre otomatik genişlik) ---
        self.play_button = QPushButton("Play")
        self.play_button.setStyleSheet(self.buttonStyle())
        self.play_button.setFixedHeight(30)
        self.play_button.adjustSize()
        self.play_button.setFixedWidth(self.play_button.sizeHint().width() + 20)
        self.play_button.clicked.connect(self.toggle_playback)
        self.toolbar_layout.addWidget(self.play_button)
        self.btn_play = self.play_button

        # --- Record butonu (yazı boyutuna göre otomatik genişlik) ---
        self.record_button = QPushButton("Record")
        self.record_button.setStyleSheet(self.buttonStyle())
        self.record_button.setFixedHeight(30)
        self.record_button.adjustSize()
        self.record_button.setFixedWidth(self.record_button.sizeHint().width() + 20)
        self.record_button.clicked.connect(self.handle_record_insert)
        self.toolbar_layout.addWidget(self.record_button)
        self.btn_enter = self.record_button

        # --- Filter butonu (sabit 30x30) ---
        self.filter_button = QPushButton("I")
        self.filter_button.setToolTip("Aktif filtreleri uygula (I butonu) - kalıcıdır")
        self.filter_button.setStyleSheet(self.buttonStylePressure(self.noise_filter_enabled))
        self.filter_button.setFixedSize(30, 30)
        self.filter_button.clicked.connect(self.toggle_noise_filter)
        self.filter_button.setContextMenuPolicy(Qt.NoContextMenu)
        self.toolbar_layout.addWidget(self.filter_button)
        self.btn_filter = self.filter_button

        # --- Wave Scale butonu (sabit 30x30) ---
        self.wave_scale_button = QPushButton(str(self.waveform_scale))
        self.wave_scale_button.setStyleSheet(self.buttonStylePressure(False))
        self.wave_scale_button.setFixedSize(30, 30)
        self.wave_scale_button.setToolTip("Dalga Formu Genişliği (1-7)")
        self.wave_scale_button.clicked.connect(self.show_wave_scale_menu)
        self.toolbar_layout.addWidget(self.wave_scale_button)
        self.btn_wave_scale = self.wave_scale_button

        # --- Speed combobox (sabit 100x30) ---
        self.speed_box = QComboBox()
        self.speed_box.addItems([
            '0.1x', '0.2x', '0.3x', '0.4x', '0.5x', '0.6x', '0.7x', '0.8x', '0.9x',
            '1x', '1.1x', '1.2x', '1.25x', '1.3x', '1.4x', '1.5x', '1.7x', '1.8x',
            '2x', '2.5x', '3x'
        ])
        self.speed_box.setCurrentText('1x')
        self.speed_box.setFixedSize(75, 30)
        self.speed_box.setStyleSheet(self.buttonStyle())
        self.speed_box.currentTextChanged.connect(self.change_speed)
        self.toolbar_layout.addWidget(self.speed_box)

        # --- Scroll step combobox (sabit 90x30) ---
        self.scroll_step_box = QComboBox()
        self.scroll_step_box.addItems(['0.1s', '0.2s', '0.3s', '0.5s', '1s', '3s', '5s', '10s', '15s', '20s', '30s'])
        saved_step_s = self.scroll_step_ms / 1000.0
        saved_step_text = f"{saved_step_s}s" if saved_step_s != int(saved_step_s) else f"{int(saved_step_s)}s"
        if saved_step_text not in ['0.1s', '0.2s', '0.3s', '0.5s', '1s', '3s', '5s', '10s', '15s', '20s', '30s']:
            saved_step_text = '5s'
            self.scroll_step_ms = 5000
        self.scroll_step_box.setCurrentText(saved_step_text)
        self.scroll_step_box.setFixedSize(75, 30)
        self.scroll_step_box.setStyleSheet(self.buttonStyle())
        self.scroll_step_box.currentTextChanged.connect(self.change_scroll_step)
        self.toolbar_layout.addWidget(self.scroll_step_box)

        # --- Panel toggle butonu (sabit 30x30) ---
        self.panel_toggle_button = QPushButton('/')
        self.panel_toggle_button.setToolTip("Geçici Metin Panelini Aç/Kapat")
        self.panel_toggle_button.setStyleSheet(self.buttonStylePressure(self.temporary_text_panel.isVisible()))
        self.panel_toggle_button.setFixedSize(30, 30)
        self.panel_toggle_button.clicked.connect(self.toggle_text_panel)
        self.toolbar_layout.addWidget(self.panel_toggle_button)
        self.btn_panel_toggle = self.panel_toggle_button

        # --- Center text butonu (sabit 30x30) ---
        self.center_text_button = QPushButton('O')
        self.center_text_button.setToolTip("Metni Ortala / Sola Yasla")
        self.center_text_button.setStyleSheet(self.buttonStylePressure(self.text_alignment_center))
        self.center_text_button.setFixedSize(30, 30)
        self.center_text_button.clicked.connect(self.toggle_text_alignment)
        self.toolbar_layout.addWidget(self.center_text_button)
        self.btn_center_text = self.center_text_button

        # --- Font size butonu (yazı boyutuna göre otomatik genişlik) ---
        self.font_size_button = QPushButton(str(self.current_text_font_size))
        self.font_size_button.setToolTip("Geçici Metin Boyutunu Ayarla")
        self.font_size_button.setStyleSheet(self.buttonStyle())
        self.font_size_button.setFixedHeight(30)
        self.font_size_button.adjustSize()
        self.font_size_button.setFixedWidth(self.font_size_button.sizeHint().width() + 20)
        self.font_size_button.clicked.connect(self.show_text_font_size_menu)
        self.font_size_button.wheelEvent = self.change_text_font_size_by_wheel
        self.toolbar_layout.addWidget(self.font_size_button)
        self.btn_text_font_size = self.font_size_button

        # --- Zaman etiketi ---
        self.lbl_time = QLabel('00:00 / 00:00')
        self.lbl_time.setAlignment(Qt.AlignCenter)
        self.toolbar_layout.addWidget(self.lbl_time)

        # --- Dosya etiketi ---
        #self.lbl_file = QLabel('File: None')
        #self.lbl_file.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        #self.toolbar_layout.addWidget(self.lbl_file)
        # Dosya etiketi toolbar'a eklenmez; mevcut kodun
        # self.lbl_file referanslarının güvenli şekilde çalışması için nesne oluşturulur.
        self.lbl_file = QLabel('File: None', self)
        self.lbl_file.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_file.hide()

        # --- Stretch (boşluk) ---
        self.toolbar_layout.addStretch()

        # --- Export butonu (sabit 90x30) ---
        self.Export_button = QPushButton('Export')
        self.Export_button.setStyleSheet(self.buttonStyle())
        self.Export_button.setFixedSize(90, 30)
        self.Export_button.clicked.connect(self.Export_audio_file)
        self.Export_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.Export_button.customContextMenuRequested.connect(lambda pos: self.Export_sound_package())
        self.toolbar_layout.addWidget(self.Export_button)
        self.btn_Export = self.Export_button

        # --- Sound butonu (sabit 90x30) ---
        self.sound_button = QPushButton('Sound')
        self.sound_button.setStyleSheet(self.buttonStyle())
        self.sound_button.setFixedSize(90, 30)
        self.sound_button.clicked.connect(self.triggerCoreSwitcher)
        self.toolbar_layout.addWidget(self.sound_button)
        self.btn_sound = self.sound_button

        # Ana layout'a ekle
        main_layout.addWidget(top_bar)
        main_layout.addWidget(self.waveform_widget, 1)
        main_layout.addWidget(self.temporary_text_panel)
        self.setLayout(main_layout)

        # Yazı tipi ve hizalama başlangıç
        self.set_text_font_size(self.current_text_font_size)
        self.temporary_text_panel.text_edit.textChanged.connect(self.on_text_changed)
        self.apply_text_alignment()

        # --- Kısayollar ---
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.setContext(Qt.WindowShortcut)
        undo_shortcut.activated.connect(self.undo_action)
        
        redo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        redo_shortcut.setContext(Qt.WindowShortcut)
        redo_shortcut.activated.connect(self.redo_action)
        
        redo_shortcut_std = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo_shortcut_std.setContext(Qt.WindowShortcut)
        redo_shortcut_std.activated.connect(self.redo_action)

    def show_wave_scale_menu(self):
        if self.is_recording_mode:
            return
        if self.lib and self.audio_engine and self.lib.get_is_playing(self.audio_engine) != 0:
            return

        menu = QMenu(self)
        menu.setStyleSheet(self.menuStyle())
        for scale in range(1, 8):
            action_text = f"{scale}"
            if scale == self.waveform_scale:
                action_text += " (Aktif)"
            action = QAction(action_text, self)
            action.triggered.connect(lambda checked, s=scale: self.set_waveform_scale(s))
            menu.addAction(action)
        point = self.btn_wave_scale.mapToGlobal(QPoint(0, self.btn_wave_scale.height()))
        menu.exec_(point)

    def set_waveform_scale(self, scale):
        self.waveform_scale = scale
        self.btn_wave_scale.setText(str(scale))
        self.waveform_widget.set_width_scale(scale)
        self._save_settings()
        self.log_sound(f"Dalga formu ölçeklemesi ayarlandı: {scale}x")

    def update_undo_redo_buttons(self):
        if not self.lib or not self.audio_engine:
            self.btn_undo.setEnabled(False)
            self.btn_redo.setEnabled(False)
            self.btn_undo.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20, color="#555"))
            self.btn_redo.setIcon(create_svg_icon(SVG_REDO_ICON, size=20, color="#555"))
            return

        can_undo = self.lib.can_undo_audio(self.audio_engine) == 1
        can_redo = self.lib.can_redo_audio(self.audio_engine) == 1

        if can_undo:
            self.btn_undo.setEnabled(True)
            self.btn_undo.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20, color="#ccc"))
        else:
            self.btn_undo.setEnabled(False)
            self.btn_undo.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20, color="#555"))

        if can_redo:
            self.btn_redo.setEnabled(True)
            self.btn_redo.setIcon(create_svg_icon(SVG_REDO_ICON, size=20, color="#ccc"))
        else:
            self.btn_redo.setEnabled(False)
            self.btn_redo.setIcon(create_svg_icon(SVG_REDO_ICON, size=20, color="#555"))

    def undo_action(self):
        if not self.lib or not self.audio_engine: return
        if self.lib.get_is_playing(self.audio_engine):
            self.lib.pause_audio(self.audio_engine)
            
        if self.lib.undo_audio(self.audio_engine) == 0:
            self.update_waveform()
            self.update_ui()
            self.update_undo_redo_buttons()
            self.waveform_widget.clear_selection()
            print("Undo carried out.")

    def redo_action(self):
        if not self.lib or not self.audio_engine: return
        if self.lib.get_is_playing(self.audio_engine):
            self.lib.pause_audio(self.audio_engine)

        if self.lib.redo_audio(self.audio_engine) == 0:
            self.update_waveform()
            self.update_ui()
            self.update_undo_redo_buttons()
            self.waveform_widget.clear_selection()
            print("Redo carried out.")

    def buttonStyle(self):
        return """
            QPushButton, QComboBox {
                background-color: transparent; color: white; font-size: 14px;
                font-weight: bold; border: 2px solid #555; border-radius: 8px;
                padding: 5px 10px;
            }
            QPushButton:hover, QComboBox:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
            QComboBox::drop-down { border: 0px; }
            QComboBox::down-arrow { image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTcgMTBMMTIgMTVMMTcgMTAiIHN0cm9rZT0iI2VlZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm9udW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPg==); width: 16px; height: 16px; }
            QComboBox QAbstractItemView { background-color: #282828; border: 1px solid #555; selection-background-color: #444; color: white; }
        """

    def buttonStyleMini(self):
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 12px;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 3px 8px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

    def buttonStylePressure(self, active):
        if active:
            return """
                QPushButton { background-color: #555; color: white; font-size: 14px;
                    font-weight: bold; border: 2px solid #888; border-radius: 8px; padding: 2px; }
                QPushButton:hover { background-color: #666; }
                QPushButton:pressed { background-color: #777; }
            """
        else:
            return """
                QPushButton { background-color: transparent; color: white; font-size: 14px;
                    font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 2px; }
                QPushButton:hover { background-color: #444; }
                QPushButton:pressed { background-color: #666; }
            """

    def menuStyle(self):
        return """
            QMenu { background-color: #333; border: 1px solid #555; color: white; padding: 5px; }
            QMenu::item { padding: 5px 20px; min-width: 100px; }
            QMenu::item:selected { background-color: #555; }
        """

    def toggle_text_panel(self):
        if self.temporary_text_panel.isVisible():
            self.temporary_text_panel.hide()
        else:
            self.temporary_text_panel.show()
            self.temporary_text_panel.text_edit.setFocus()
        self.btn_panel_toggle.setStyleSheet(self.buttonStylePressure(self.temporary_text_panel.isVisible()))
        self._save_settings()

    def toggle_text_alignment(self):
        self.text_alignment_center = not self.text_alignment_center
        self.btn_center_text.setStyleSheet(self.buttonStylePressure(self.text_alignment_center))
        self.apply_text_alignment()
        self._save_settings()

    def apply_text_alignment(self):
        alignment = Qt.AlignCenter if self.text_alignment_center else Qt.AlignLeft
        text_edit = self.temporary_text_panel.text_edit
        text_edit.setAlignment(alignment)
        doc = text_edit.document()
        block = doc.begin()
        while block.isValid():
            cursor = QTextCursor(block)
            block_format = block.blockFormat()
            block_format.setAlignment(alignment)
            block_format.setLineHeight(150, QTextBlockFormat.ProportionalHeight)
            cursor.setBlockFormat(block_format)
            block = block.next()

    def on_text_changed(self):
        text_edit = self.temporary_text_panel.text_edit
        text_edit.textChanged.disconnect(self.on_text_changed)
        self.apply_text_alignment()
        text_edit.textChanged.connect(self.on_text_changed)

    def show_text_font_size_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(self.menuStyle())
        standard_sizes = [10, 12, 14, 15, 16, 18, 20, 24, 28, 32, 36, 48, 72]
        for size in standard_sizes:
            action_text = f"{size} px"
            if size == self.current_text_font_size:
                action_text += " (Aktif)"
            action = QAction(action_text, self)
            action.triggered.connect(lambda checked, s=size: self.set_text_font_size(s))
            menu.addAction(action)
        point = self.btn_text_font_size.mapToGlobal(QPoint(0, self.btn_text_font_size.height()))
        menu.exec_(point)

    def set_text_font_size(self, size):
        self.current_text_font_size = size
        self.btn_text_font_size.setText(str(size))
        # Buton genişliğini yazıya göre ayarla
        self.btn_text_font_size.adjustSize()
        self.btn_text_font_size.setFixedWidth(self.btn_text_font_size.sizeHint().width() + 20)
        self.temporary_text_panel.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: #252525;
                color: #ffffff;
                border: none;
                padding: 10px;
                font-family: sans-serif;
                font-size: {size}px;
            }}
        """)
        font = self.temporary_text_panel.text_edit.font()
        font.setPixelSize(size)
        self.temporary_text_panel.text_edit.setFont(font)
        self._save_settings()

    def change_text_font_size_by_wheel(self, event):
        if event.angleDelta().y() > 0:
            new_size = min(200, self.current_text_font_size + 1)
        else:
            new_size = max(10, self.current_text_font_size - 1)
        self.set_text_font_size(new_size)
        event.accept()

    def toggle_noise_filter(self):
        self.noise_filter_enabled = not self.noise_filter_enabled
        self.btn_filter.setStyleSheet(self.buttonStylePressure(self.noise_filter_enabled))
        self._save_settings()   
        self.log_sound(f"I butonu {'aktif' if self.noise_filter_enabled else 'pasif'} (kalıcı)")

    def triggerCoreSwitcher(self):
        if self.core_window_ref and hasattr(self.core_window_ref, 'showSwitcher'):
            self.core_window_ref.showSwitcher()
        else:
            QMessageBox.information(self, 'Sound', 'Main window or showSwitcher not found.')

    def log_sound(self, text):
        timestamp = time.strftime("%H:%M:%S")
        print(f"[SoundEditor {timestamp}] {text}")

    def load_files(self):
        if not self.lib or not self.audio_engine:
            QMessageBox.warning(self, 'Warning', 'Audio engine is not available.')
            return

        QDir().mkpath(SoundEditorWindow.DEFAULT_BASE_DIR)
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "Ses/Paket Dosyalarını Seç", 
            SoundEditorWindow.DEFAULT_BASE_DIR, 
            "Desteklenen Dosyalar (*.wav *.sound);;WAV Ses Dosyası (*.wav);;Concept Sound Paketi (*.sound);;Tüm Dosyalar (*)"
        )

        if file_paths:
            if len(file_paths) == 1 and file_paths[0].lower().endswith('.sound'):
                self.load_sound_package(file_paths[0])
            else:
                if len(file_paths) == 1:
                    self.current_file = file_paths[0]
                else:
                    self.current_file = None
                self.load_wav_files_into_engine(file_paths)

    def load_files_from_path(self, file_paths):
        if not file_paths:
            return
        valid_paths = [path for path in file_paths if path.lower().endswith('.wav') or path.lower().endswith('.sound')]
        if not valid_paths:
            QMessageBox.warning(self, 'Uyarı', 'Seçilen dosyalar arasında .wav veya .sound formatında dosya bulunamadı.')
            return

        if len(valid_paths) == 1 and valid_paths[0].lower().endswith('.sound'):
            self.load_sound_package(valid_paths[0])
        else:
            if len(valid_paths) == 1:
                self.current_file = valid_paths[0]
            else:
                self.current_file = None
            self.load_wav_files_into_engine(valid_paths)

    def load_wav_files_into_engine(self, file_paths):
        if not self.lib or not self.audio_engine:
            QMessageBox.warning(self, 'Warning', 'Audio engine is not available.')
            return

        if file_paths:
            c_file_paths = (ctypes.c_char_p * len(file_paths))()
            for i, path in enumerate(file_paths):
                c_file_paths[i] = path.encode('utf-8')

            result = self.lib.load_audio_files(self.audio_engine, c_file_paths, len(file_paths))

            if result == 0:
                print(f'{len(file_paths)} files loaded successfully.')
                self.lbl_file.setText(f'File: {os.path.basename(file_paths[0])}...')
                if len(file_paths) == 1:
                    self.current_file = file_paths[0]
                self.update_waveform()
                self.update_ui()
                self.update_undo_redo_buttons()
                self.btn_play.setText('Play')
                self.waveform_widget.clear_selection()
                self.waveform_widget.split_points_ms = []
            else:
                QMessageBox.warning(self, 'Error', 'An error occurred while loading audio files.')
                self.lbl_file.setText('File: None')
                self.waveform_widget.set_audio_data(None, 0, 0)
                self.lbl_time.setText('00:00 / 00:00')
                self.waveform_widget.clear_selection()
                self.waveform_widget.split_points_ms = []
                self.update_undo_redo_buttons()

    def load_sound_package(self, file_path):
        if not self.lib or not self.audio_engine:
            return
        try:
            temp_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            audio_path = os.path.join(temp_dir, 'audio.wav')
            metadata_path = os.path.join(temp_dir, 'metadata.json')
            
            if not os.path.exists(audio_path) or not os.path.exists(metadata_path):
                raise Exception("Geçersiz .sound paketi içeriği eksik.")
            
            self.load_wav_files_into_engine([audio_path])
            self.current_file = file_path 
            self.lbl_file.setText(f'File: {os.path.basename(file_path)}')

            with open(metadata_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
                
            text_content = meta.get('text', '')
            alignment_center = meta.get('alignment_center', False)
            font_size = meta.get('font_size', 14)
            
            self.temporary_text_panel.text_edit.setPlainText(text_content)
            self.text_alignment_center = alignment_center
            self.btn_center_text.setStyleSheet(self.buttonStylePressure(self.text_alignment_center))
            self.set_text_font_size(font_size)
            self.apply_text_alignment()
            
            if not self.temporary_text_panel.isVisible():
                self.toggle_text_panel()
            
            try:
                shutil.rmtree(temp_dir)
            except Exception as ex:
                print(f"Geçici dizin temizleme hatası: {ex}")
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f".sound dosyası yüklenirken hata oluştu:\n{str(e)}")

    def Export_sound_package(self):
        if not self.lib or not self.audio_engine or self.lib.get_duration_ms(self.audio_engine) <= 0:
            QMessageBox.warning(self, 'Warning', 'Dışa aktarılacak ses verisi yok.')
            return
        QDir().mkpath(self.DEFAULT_BASE_DIR)
        save_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Sesi Metinli Ses Olarak Dışa Aktar (.sound)", 
            os.path.join(self.DEFAULT_BASE_DIR, "untitled.sound"), 
            "Concept Sound Paketi (*.sound)"
        )
        if save_path:
            if not save_path.lower().endswith('.sound'):
                save_path += '.sound'
            
            try:
                temp_dir = tempfile.mkdtemp()
                temp_audio_path = os.path.join(temp_dir, 'audio.wav')
                
                c_file_path = temp_audio_path.encode('utf-8')
                if self.lib.save_audio_to_file(self.audio_engine, c_file_path) != 0:
                    raise Exception("Geçici ses dosyası oluşturulamadı.")
                
                metadata_path = os.path.join(temp_dir, 'metadata.json')
                meta = {
                    "text": self.temporary_text_panel.text_edit.toPlainText(),
                    "alignment_center": self.text_alignment_center,
                    "font_size": self.current_text_font_size
                }
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, indent=4, ensure_ascii=False)
                
                with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    zip_file.write(temp_audio_path, 'audio.wav')
                    zip_file.write(metadata_path, 'metadata.json')
                    
                self.current_file = save_path
                self.lbl_file.setText(f'File: {os.path.basename(save_path)}')
                QMessageBox.information(self, 'Başarılı', f'Metinli ses dosyası (.sound) başarıyla kaydedildi:\n{save_path}')
                
                shutil.rmtree(temp_dir)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f".sound dosyası kaydedilirken hata oluştu:\n{str(e)}")

    def toggle_playback(self):
        if not self.lib or not self.audio_engine: return
        is_playing = self.lib.get_is_playing(self.audio_engine)
        if is_playing:
            self.lib.pause_audio(self.audio_engine)
        else:
            if self.lib.get_duration_ms(self.audio_engine) == 0:
                return
            self.lib.play_audio(self.audio_engine)

    def update_ui(self):
        if not self.lib or not self.audio_engine: return
        current_pos_ms = self.lib.get_position_ms(self.audio_engine)
        duration_ms = self.lib.get_duration_ms(self.audio_engine)
        is_playing = self.lib.get_is_playing(self.audio_engine)
        if duration_ms > 0:
            current_pos_str = f"{current_pos_ms // 60000:02}:{(current_pos_ms % 60000) // 1000:02}"
            duration_str = f"{duration_ms // 60000:02}:{(duration_ms % 60000) // 1000:02}"
            self.lbl_time.setText(f"{current_pos_str} / {duration_str}")
            self.waveform_widget.set_position(current_pos_ms)
        else:
            self.lbl_time.setText('00:00 / 00:00')
        self.btn_play.setText('Pause' if is_playing else 'Play')

    def update_waveform(self):
        if not self.lib or not self.audio_engine: return
        envelope_length = self.lib.get_envelope_length(self.audio_engine)
        duration_ms = self.lib.get_duration_ms(self.audio_engine)
        if duration_ms > 0 and envelope_length > 0:
            envelope_ptr = self.lib.get_envelope_data(self.audio_engine)
            self.waveform_widget.set_audio_data(envelope_ptr, envelope_length, duration_ms)
        else:
            self.waveform_widget.set_audio_data(None, 0, 0)

    def change_speed(self, txt):
        if not self.lib or not self.audio_engine:
            return
        try:
            speed = float(txt.replace('x', ''))
        except ValueError:
            return
        was_playing = self.lib.get_is_playing(self.audio_engine) != 0
        if was_playing:
            self.lib.pause_audio(self.audio_engine)
        self.lib.set_speed(self.audio_engine, ctypes.c_float(speed))
        if was_playing:
            self.lib.play_audio(self.audio_engine)
        self.log_sound(f"Playback speed changed to: {speed}x")

    def change_scroll_step(self, txt):
        try:
            self.scroll_step_ms = int(float(txt.replace('s', '')) * 1000)
            self._save_settings()  
        except ValueError:
            pass

    def add_split_point_from_playhead(self):
        if not self.lib or not self.audio_engine: return
        if self.lib.get_is_playing(self.audio_engine): return
        if self.lib.get_duration_ms(self.audio_engine) == 0: return
        current_pos_ms = self.lib.get_position_ms(self.audio_engine)
        self.waveform_widget.add_split_point(current_pos_ms)

    def delete_selected_segments(self):
        if not self.lib or not self.audio_engine:
            return
        selected_segments = self.waveform_widget.get_selected_segments()
        if not selected_segments:
            print("No segments selected for deletion.")
            return
        original_pos_ms = self.lib.get_position_ms(self.audio_engine)
        original_split_points = list(self.waveform_widget.split_points_ms)
        segments_to_delete = sorted(selected_segments, key=lambda x: x[1], reverse=True)
        successful_deletions = []
        for start_ms, end_ms in segments_to_delete:
            if self.lib.delete_audio_segment(self.audio_engine, ctypes.c_int(start_ms), ctypes.c_int(end_ms)) == 0:
                print(f"Successfully deleted segment: {start_ms}-{end_ms}")
                successful_deletions.append((start_ms, end_ms))
            else:
                print(f"Failed to delete segment: {start_ms}-{end_ms}")
        if not successful_deletions:
            print("No deletions were successful.")
            return
        
        self.update_undo_redo_buttons()
        
        sorted_deletions = sorted(successful_deletions, key=lambda x: x[0])
        new_pos_ms = original_pos_ms
        for start_ms, end_ms in sorted_deletions:
            length = end_ms - start_ms
            if original_pos_ms > start_ms:
                if original_pos_ms >= end_ms:
                    new_pos_ms -= length
                else:
                    new_pos_ms -= (original_pos_ms - start_ms)
        new_pos_ms = max(0, new_pos_ms)
        new_split_points = []
        for sp in original_split_points:
            time_deleted_before_sp = 0
            is_inside_deleted_segment = False
            for start_ms, end_ms in sorted_deletions:
                if sp > start_ms:
                    if sp < end_ms:
                        is_inside_deleted_segment = True
                        break
                    else:
                        time_deleted_before_sp += (end_ms - start_ms)
            if not is_inside_deleted_segment:
                new_sp = sp - time_deleted_before_sp
                new_duration = self.lib.get_duration_ms(self.audio_engine)
                if new_sp > 0 and new_sp < new_duration:
                    new_split_points.append(new_sp)
        self.waveform_widget.split_points_ms = sorted(list(set(new_split_points)))
        self.lib.set_play_position_ms(self.audio_engine, ctypes.c_int(new_pos_ms))
        self.update_waveform()
        self.update_ui()
        self.waveform_widget.clear_selection()
        print(f"New split points: {self.waveform_widget.split_points_ms}")

    def delete_similar_segments_action(self):
        if not self.lib or not self.audio_engine:
            return
        
        selected_segments = self.waveform_widget.get_selected_segments()
        if not selected_segments:
            QMessageBox.information(self, 'Bilgi', 'Lütfen önce silmek istediğiniz örnek aralığı seçin.')
            return

        start_ms, end_ms = selected_segments[0]
        
        if self.lib.get_is_playing(self.audio_engine):
            self.lib.pause_audio(self.audio_engine)

        similarity_threshold = 0.80
        result = self.lib.detect_and_delete_similar(
            self.audio_engine, 
            ctypes.c_int(start_ms), 
            ctypes.c_int(end_ms), 
            ctypes.c_float(similarity_threshold)
        )

        if result == 0:
            print("Similar parts successfully analyzed and deleted.")
            self.update_undo_redo_buttons()
            self.waveform_widget.clear_selection()
            self.waveform_widget.split_points_ms = []
            self.lib.set_play_position_ms(self.audio_engine, ctypes.c_int(0))
            self.update_waveform()
            self.update_ui()
        else:
            QMessageBox.critical(self, 'Hata', 'Benzer sesler silinirken motor hatası oluştu.')

    def delete_thickness_segments_action(self, pos=None):
        if not self.lib or not self.audio_engine:
            return

        selected_segments = self.waveform_widget.get_selected_segments()
        if not selected_segments:
            QMessageBox.information(
                self,
                'Bilgi',
                'Lütfen önce farenin sol tuşuyla, silmek istediğiniz kalınlığı temsil eden bir kesit seçin.'
            )
            return

        start_ms, end_ms = selected_segments[0]
        original_pos_ms = self.lib.get_position_ms(self.audio_engine)

        if self.lib.get_is_playing(self.audio_engine):
            self.lib.pause_audio(self.audio_engine)

        result = self.lib.delete_segments_by_thickness(
            self.audio_engine, 
            ctypes.c_int(start_ms), 
            ctypes.c_int(end_ms)
        )

        if result == 0:
            print("Thickness based deep full-track scan successfully completed.")
            self.update_undo_redo_buttons()
            self.waveform_widget.clear_selection()
            self.waveform_widget.split_points_ms = []

            # Silme sonrasında mümkün olduğunca önceki oynatma konumunu koru.
            new_duration_ms = self.lib.get_duration_ms(self.audio_engine)
            safe_pos_ms = max(0, min(original_pos_ms, new_duration_ms))
            self.lib.set_play_position_ms(
                self.audio_engine,
                ctypes.c_int(safe_pos_ms)
            )

            self.update_waveform()
            self.update_ui()
        else:
            QMessageBox.critical(
                self,
                'Hata',
                'Kalınlığa dayalı kapsamlı tarama/silme işlemi sırasında motor hatası oluştu.'
            )

    def Export_audio_file(self):
        if not self.lib or not self.audio_engine or self.lib.get_duration_ms(self.audio_engine) <= 0:
            QMessageBox.warning(self, 'Warning', 'Dışa aktarılacak ses verisi yok.')
            return
        QDir().mkpath(self.DEFAULT_BASE_DIR)
        save_path, _ = QFileDialog.getSaveFileName(self, "Sesi WAV Olarak Dışa Aktar", os.path.join(self.DEFAULT_BASE_DIR, "untitled.wav"), "WAV Ses Dosyası (*.wav)")
        if save_path:
            if not save_path.lower().endswith('.wav'):
                save_path += '.wav'
            c_file_path = save_path.encode('utf-8')
            result = self.lib.save_audio_to_file(self.audio_engine, c_file_path)
            if result == 0:
                self.current_file = save_path
                self.lbl_file.setText(f'File: {os.path.basename(save_path)}')
                QMessageBox.information(self, 'Başarılı', f'Ses başarıyla kaydedildi:\n{save_path}')
            else:
                QMessageBox.critical(self, 'Hata', f'Ses kaydedilirken bir hata oluştu:\n{save_path}')

    def saveContent(self):
        if not self.current_file:
            self.Export_sound_package()
        else:
            try:
                if self.current_file.lower().endswith('.sound'):
                    temp_dir = tempfile.mkdtemp()
                    temp_audio_path = os.path.join(temp_dir, 'audio.wav')
                    c_file_path = temp_audio_path.encode('utf-8')
                    if self.lib.save_audio_to_file(self.audio_engine, c_file_path) == 0:
                        metadata_path = os.path.join(temp_dir, 'metadata.json')
                        meta = {
                            "text": self.temporary_text_panel.text_edit.toPlainText(),
                            "alignment_center": self.text_alignment_center,
                            "font_size": self.current_text_font_size
                        }
                        with open(metadata_path, 'w', encoding='utf-8') as f:
                            json.dump(meta, f, indent=4, ensure_ascii=False)
                        
                        with zipfile.ZipFile(self.current_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            zip_file.write(temp_audio_path, 'audio.wav')
                            zip_file.write(metadata_path, 'metadata.json')
                        
                        QMessageBox.information(self, "Kaydet", f"Dosya kaydedildi: {self.current_file}")
                    else:
                        QMessageBox.critical(self, 'Hata', f'Dosya kaydedilirken hata oluştu:\n{self.current_file}')
                    shutil.rmtree(temp_dir)
                else:
                    c_file_path = self.current_file.encode('utf-8')
                    if self.lib.save_audio_to_file(self.audio_engine, c_file_path) == 0:
                        QMessageBox.information(self, "Kaydet", f"Dosya kaydedildi: {self.current_file}")
                    else:
                        QMessageBox.critical(self, 'Hata', f'Dosya kaydedilirken hata oluştu:\n{self.current_file}')
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya kaydedilirken hata oluştu:\n{str(e)}")

    def handle_record_insert(self):
        if not self.lib or not self.audio_engine: return
        if self.lib.get_is_playing(self.audio_engine): return

        if not self.is_recording_mode:
            if self.lib.start_microphone_recording(self.audio_engine) == 0:
                self.is_recording_mode = True
                self.btn_enter.setText('Stop')
                self.log_sound("Mikrofon kaydı başladı.")
        else:
            if self.lib.stop_microphone_recording(self.audio_engine) == 0:
                self.is_recording_mode = False
                self.btn_enter.setText('Record')
                current_pos_ms = self.lib.get_position_ms(self.audio_engine)
                os.makedirs(SETTINGS_DIR, exist_ok=True)
                raw_file = TEMP_RAW_RECORDING_FILE

                try:
                    if self.lib.save_recorded_audio_to_file(self.audio_engine, raw_file.encode('utf-8')) != 0:
                        QMessageBox.critical(self, 'Error', 'Could not save raw recorded audio.')
                        return

                    time.sleep(0.2)
                    if not os.path.exists(raw_file):
                        self.log_sound("Ham ses dosyası bulunamadı, tekrar deneniyor...")
                        time.sleep(0.2)
                        if not os.path.exists(raw_file):
                            raise Exception("Raw recording file not found after multiple attempts.")

                    if self.noise_filter_enabled and self.core_window_ref:
                        self.log_sound("Kayıt tamamlandı, filtre.py'ye gönderiliyor (arka plan)...")
                        def on_filter_complete(success, filtered_path, message):
                            if self.audio_engine is None or not self.lib:
                                self.log_sound("Engine kapatıldı, ses eklenemedi.")
                                return
                            if success and filtered_path and os.path.exists(filtered_path):
                                self.log_sound(f"Filtreleme başarılı: {filtered_path}")
                                if self.lib.insert_audio_file(self.audio_engine, filtered_path.encode('utf-8'), ctypes.c_int(current_pos_ms)) == 0:
                                    self.update_waveform()
                                    self.update_ui()
                                    self.update_undo_redo_buttons()
                                else:
                                    QMessageBox.critical(self, 'Error', 'Filtrelenmiş ses eklenemedi.')
                                try:
                                    os.remove(filtered_path)
                                except:
                                    pass
                            else:
                                self.log_sound(f"Filtreleme başarısız ({message}), ham ses ekliyor.")
                                if os.path.exists(raw_file):
                                    if self.lib.insert_audio_file(self.audio_engine, raw_file.encode('utf-8'), ctypes.c_int(current_pos_ms)) == 0:
                                        self.update_waveform()
                                        self.update_ui()
                                        self.update_undo_redo_buttons()
                                    else:
                                        QMessageBox.critical(self, 'Error', 'Ham ses eklenemedi.')
                                else:
                                    QMessageBox.critical(self, 'Error', 'Ham ses dosyası bulunamadı.')
                            try:
                                if os.path.exists(raw_file):
                                    os.remove(raw_file)
                            except:
                                pass

                        self.core_window_ref.process_audio_with_filter(raw_file, on_filter_complete)
                    else:
                        if self.lib.insert_audio_file(self.audio_engine, raw_file.encode('utf-8'), ctypes.c_int(current_pos_ms)) == 0:
                            self.update_waveform()
                            self.update_ui()
                            self.update_undo_redo_buttons()
                        else:
                            QMessageBox.critical(self, 'Error', 'An error occurred while inserting recorded audio.')
                        try:
                            os.remove(raw_file)
                        except:
                            pass

                except Exception as e:
                    QMessageBox.critical(self, 'Error', f'Recording handling error: {e}')
                    self.log_sound(f"Hata: {e}")

    def closeEvent(self, event):
        if self.is_recording_mode:
            msg = QMessageBox(self)
            msg.setWindowTitle("Kayıt Devam Ediyor")
            msg.setText("Mikrofon kaydınız şu anda devam ediyor.\n\n"
                        "Pencereyi kapatmak istiyor musunuz?\n"
                        "(Kayıt otomatik olarak durdurulup iptal edilecektir)")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #1e1e1e;
                    color: white;
                }
                QLabel {
                    color: white;
                    font-size: 14px;
                    padding: 10px;
                }
                QPushButton {
                    padding: 8px 20px;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton[text="Yes"] {
                    background-color: #c42b1c;
                    color: white;
                }
                QPushButton[text="No"] {
                    background-color: #333333;
                    color: white;
                }
            """)
            reply = msg.exec_()
            if reply == QMessageBox.Yes:
                print("Python: Kullanıcı kapatmayı onayladı → ses kaydı iptal ediliyor.")
                if self.audio_engine and self.lib:
                    self.lib.stop_microphone_recording(self.audio_engine)
                self.is_recording_mode = False
                self.btn_enter.setText('Record')
            else:
                event.ignore()
                return

        self._cleanup_engine()

        for temp_file in [TEMP_RAW_RECORDING_FILE]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    print(f"Error cleaning up {temp_file}: {e}")
        event.accept()


if __name__ == '__main__':
    if lib is None:
        print("Critical Error: Application cannot be started because the C++ library could not be loaded.")
        app_instance = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, 'Startup Error', "Application cannot be started because the C++ library could not be loaded.")
        sys.exit(1)

    app = QApplication(sys.argv)
    win = SoundEditorWindow()
    win.show()
    sys.exit(app.exec_())
