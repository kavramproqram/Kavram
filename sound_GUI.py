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

import sys
import os
import ctypes  # To call C++ library
import json    # For saving and loading settings
import noisereduce as nr # For AI noise reduction
import soundfile as sf   # For reading/writing audio files
import numpy as np       # For numerical operations

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QComboBox, QScrollArea, QSizePolicy, QMessageBox, QSlider, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF, QDir
from PyQt5.QtGui import QPainter, QPen, QColor, QCursor, QBrush, QPainterPath

# Constants
BACKGROUND = QColor('#383838')
WAVE_COLOR = QColor('#606060')
CURSOR_COLOR = QColor('#F44336')
SELECT_COLOR = QColor('#A0A0A0')

# Define the path for the settings file
SETTINGS_DIR = os.path.join(QDir.homePath(), '.config', 'concept_sound_editor')
SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'settings.json')

# Temporary files for AI Noise Reduction
TEMP_RAW_RECORDING_FILE = os.path.join(SETTINGS_DIR, "temp_raw_recording.wav")
TEMP_CLEANED_RECORDING_FILE = os.path.join(SETTINGS_DIR, "temp_cleaned_recording.wav")


# --- Load C++ Library ---
lib = None
try:
    if sys.platform.startswith('win'):
        lib_path = 'sound_engine.dll'
    elif sys.platform.startswith('linux'):
        lib_path = './libsound_engine.so'
    elif sys.platform.startswith('darwin'):
        lib_path = './libsound_engine.dylib'
    else:
        lib_path = 'sound_engine'

    lib = ctypes.CDLL(lib_path)

    # --- Define C++ Function Signatures ---
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
    lib.start_microphone_recording.argtypes = [ctypes.c_void_p]
    lib.start_microphone_recording.restype = ctypes.c_int
    lib.stop_microphone_recording.argtypes = [ctypes.c_void_p]
    lib.stop_microphone_recording.restype = ctypes.c_int
    lib.save_recorded_audio_to_file.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.save_recorded_audio_to_file.restype = ctypes.c_int
    lib.save_audio_to_file.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.save_audio_to_file.restype = ctypes.c_int
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
    lib.set_mic_de_hum_level.argtypes = [ctypes.c_void_p, ctypes.c_int]
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

# --- Widget for Waveform Drawing ---
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
        self.selected_segments = []
        self.split_points_ms = []
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background:#282828;")

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

# --- Main Window Class ---
class SoundEditorWindow(QWidget):
    DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')
    MIN_EFFECT_BAR_HEIGHT = 100
    MAX_EFFECT_BAR_HEIGHT_RATIO = 0.5
    CLOSED_BAR_HEIGHT = 20 + 10

    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        self.audio_engine = None
        self.lib = lib
        self.is_recording_mode = False
        self.scroll_step_ms = 5000

        if self.lib:
            self.audio_engine = self.lib.create_audio_engine()
            if not self.audio_engine:
                QMessageBox.critical(self, 'Error', 'C++ AudioEngine could not be created.')
                self.lib = None
        else:
            QMessageBox.critical(self, 'Error', 'Audio engine is not available because the C++ library could not be loaded.')

        self.waveform_widget = WaveformWidget(self, sound_editor_window=self)
        self.combo_noise_gate_threshold = QComboBox()
        self.combo_noise_gate_threshold.addItems([f"{i}dB" for i in range(-80, -19, 5)] + ["Off"])
        self.combo_noise_gate_threshold.currentTextChanged.connect(self.set_noise_gate_threshold)
        self.combo_noise_gate_release = QComboBox()
        self.combo_noise_gate_release.addItems([f"{i}ms" for i in [10, 20, 30, 50, 75, 100, 150, 200, 300, 400, 500, 750, 1000]])
        self.combo_noise_gate_release.currentTextChanged.connect(self.set_noise_gate_release)
        self.combo_hp_filter = QComboBox()
        self.combo_hp_filter.addItems(["Off"] + [f"{i}Hz" for i in range(20, 301, 10)])
        self.combo_hp_filter.currentTextChanged.connect(self.set_high_pass_filter)
        self.combo_lp_filter_mic = QComboBox()
        self.combo_lp_filter_mic.addItems(["Off"] + [f"{i}Hz" for i in range(2000, 20001, 1000)])
        self.combo_lp_filter_mic.currentTextChanged.connect(self.set_microphone_low_pass_filter)
        self.combo_gain = QComboBox()
        self.combo_gain.addItems([f"{i}dB" for i in range(-12, 13, 3)])
        self.combo_gain.currentTextChanged.connect(self.set_microphone_gain)
        self.combo_reverb_reduction = QComboBox()
        self.combo_reverb_reduction.addItems(["Off", "Low", "Medium", "High", "Very High"])
        self.combo_reverb_reduction.currentTextChanged.connect(self.set_reverb_reduction)
        self.combo_de_esser = QComboBox()
        self.combo_de_esser.addItems(["Off", "Low", "Medium", "High"])
        self.combo_de_esser.currentTextChanged.connect(self.set_de_esser)
        self.combo_de_hum = QComboBox()
        self.combo_de_hum.addItems(["Off", "Low", "Medium", "High"])
        self.combo_de_hum.currentTextChanged.connect(self.set_de_hum)
        self.combo_ai_noise_reduction = QComboBox()
        self.combo_ai_noise_reduction.addItems(["Off", "On"])
        self.combo_ai_noise_reduction.currentTextChanged.connect(self.set_ai_noise_reduction_mode)
        self.combo_comp_ratio = QComboBox()
        self.combo_comp_ratio.addItems(["1:1", "2:1", "3:1", "4:1", "5:1", "8:1", "10:1", "Inf:1"])
        self.combo_comp_ratio.setCurrentText("1:1")
        self.combo_comp_ratio.currentTextChanged.connect(self.set_compressor_ratio)
        self.combo_comp_attack = QComboBox()
        self.combo_comp_attack.addItems([f"{i}ms" for i in [1, 5, 10, 20, 50, 100, 200]])
        self.combo_comp_attack.setCurrentText("10ms")
        self.combo_comp_attack.currentTextChanged.connect(self.set_compressor_attack)
        self.combo_comp_release = QComboBox()
        self.combo_comp_release.addItems([f"{i}ms" for i in [50, 100, 200, 500, 1000, 2000]])
        self.combo_comp_release.setCurrentText("100ms")
        self.combo_comp_release.currentTextChanged.connect(self.set_compressor_release)
        self.combo_comp_makeup_gain = QComboBox()
        self.combo_comp_makeup_gain.addItems([f"{i}dB" for i in range(0, 13, 3)])
        self.combo_comp_makeup_gain.setCurrentText("0dB")
        self.combo_comp_makeup_gain.currentTextChanged.connect(self.set_compressor_makeup_gain)
        self.combo_eq_gain = QComboBox()
        self.combo_eq_gain.addItems([f"{i}dB" for i in range(-12, 13, 3)])
        self.combo_eq_gain.setCurrentText("0dB")
        self.combo_eq_gain.currentTextChanged.connect(self.set_eq_gain)
        self.combo_eq_frequency = QComboBox()
        self.combo_eq_frequency.addItems([f"{i}Hz" for i in [500, 1000, 1500, 2000, 2500, 3000, 4000]])
        self.combo_eq_frequency.setCurrentText("1000Hz")
        self.combo_eq_frequency.currentTextChanged.connect(self.set_eq_frequency)
        self.combo_eq_q = QComboBox()
        self.combo_eq_q.addItems(["0.5", "1.0", "2.0", "3.0", "5.0", "8.0", "10.0"])
        self.combo_eq_q.setCurrentText("1.0")
        self.combo_eq_q.currentTextChanged.connect(self.set_eq_q)

        self.init_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_ui)
        self.timer.start(50)
        self.set_default_microphone_effects()
        self.load_settings()

    def __del__(self):
        if self.audio_engine and self.lib:
            if self.is_recording_mode:
                self.lib.stop_microphone_recording(self.audio_engine)
            self.lib.destroy_audio_engine(self.audio_engine)
            print("C++ AudioEngine cleaned up.")
        for temp_file in [TEMP_RAW_RECORDING_FILE, TEMP_CLEANED_RECORDING_FILE]:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    print(f"Error cleaning up {temp_file}: {e}")

    def init_ui(self):
        self.setWindowTitle('Concept Sound Editor')
        self.resize(1000, 600)
        self.setStyleSheet('background:#383838; color:white;')
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        top_bar = QFrame()
        top_bar.setFixedHeight(40)
        top_bar.setStyleSheet('background:#222; border-bottom:1px solid #555;')
        bar_layout = QHBoxLayout(top_bar)
        bar_layout.setContentsMargins(10, 5, 10, 5)
        self.btn_file = QPushButton('File')
        self.btn_cut = QPushButton('Cut')
        self.btn_del = QPushButton('Delete')
        self.btn_play = QPushButton('Play')
        self.btn_enter = QPushButton('Record')
        self.btn_sound = QPushButton('Sound')
        self.btn_export = QPushButton('Export')
        for btn in [self.btn_file, self.btn_cut, self.btn_del, self.btn_play, self.btn_enter, self.btn_export, self.btn_sound]:
            btn.setFixedSize(90, 30)
            btn.setStyleSheet(self.buttonStyle())
        self.speed_box = QComboBox()
        self.speed_box.addItems(['0.5x', '1x', '1.5x', '2x'])
        self.speed_box.setCurrentText('1x')
        self.speed_box.setFixedSize(90, 30)
        self.speed_box.setStyleSheet(self.buttonStyle())
        self.speed_box.currentTextChanged.connect(self.change_speed)
        self.scroll_step_box = QComboBox()
        self.scroll_step_box.addItems(['1s', '3s', '5s', '10s', '15s', '20s', '30s'])
        self.scroll_step_box.setCurrentText('5s')
        self.scroll_step_box.setFixedSize(90, 30)
        self.scroll_step_box.setStyleSheet(self.buttonStyle())
        self.scroll_step_box.currentTextChanged.connect(self.change_scroll_step)
        self.lbl_time = QLabel('00:00 / 00:00')
        self.lbl_file = QLabel('File: None')
        self.lbl_time.setAlignment(Qt.AlignCenter)
        self.lbl_file.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.btn_file.clicked.connect(self.load_files)
        self.btn_play.clicked.connect(self.toggle_playback)
        self.btn_sound.clicked.connect(self.triggerCoreSwitcher)
        self.btn_export.clicked.connect(self.export_audio_file)
        self.btn_del.clicked.connect(self.delete_selected_segments)
        self.btn_cut.clicked.connect(self.add_split_point_from_playhead)
        self.btn_enter.clicked.connect(self.handle_record_insert)
        for w in [self.btn_file, self.btn_cut, self.btn_del, self.btn_play, self.btn_enter, self.speed_box, self.scroll_step_box]:
            bar_layout.addWidget(w)
        bar_layout.addStretch()
        bar_layout.addWidget(self.lbl_time)
        bar_layout.addWidget(self.lbl_file)
        bar_layout.addWidget(self.btn_export)
        bar_layout.addWidget(self.btn_sound)
        main_layout.addWidget(top_bar)
        self.main_splitter = QSplitter(Qt.Vertical)
        self.main_splitter.addWidget(self.waveform_widget)
        self.bottom_bar_content_frame = QFrame(self)
        self.bottom_bar_content_frame.setStyleSheet('background:#222; border-top:1px solid #555;')
        self.bottom_bar_main_layout = QVBoxLayout(self.bottom_bar_content_frame)
        self.bottom_bar_main_layout.setContentsMargins(10, 5, 10, 5)
        self.bottom_bar_main_layout.setSpacing(0)
        bar_row_1_frame = QFrame(self.bottom_bar_content_frame)
        bar_row_1_frame.setFixedHeight(40)
        bar_row_1_layout = QHBoxLayout(bar_row_1_frame)
        bar_row_1_layout.setContentsMargins(0, 0, 0, 0)
        bar_row_1_layout.setSpacing(20)
        self.btn_save = QPushButton('Save')
        self.btn_save.setFixedSize(90, 30)
        self.btn_save.setStyleSheet(self.buttonStyle())
        self.btn_save.clicked.connect(self.save_settings)
        bar_row_1_layout.addWidget(self.btn_save)
        bar_row_1_layout.addStretch()
        self.btn_reset = QPushButton('Reset')
        self.btn_reset.setFixedSize(90, 30)
        self.btn_reset.setStyleSheet(self.buttonStyle())
        self.btn_reset.clicked.connect(self.reset_settings)
        bar_row_1_layout.addWidget(self.btn_reset)
        self.bottom_bar_main_layout.addWidget(bar_row_1_frame)
        bar_row_2_frame = QFrame(self.bottom_bar_content_frame)
        bar_row_2_frame.setFixedHeight(40)
        bar_row_2_layout = QHBoxLayout(bar_row_2_frame)
        bar_row_2_layout.setContentsMargins(0, 0, 0, 0)
        bar_row_2_layout.setSpacing(15)
        self.add_effect_labels_to_layout_row1(bar_row_2_layout)
        self.bottom_bar_main_layout.addWidget(bar_row_2_frame)
        bar_row_3_frame = QFrame(self.bottom_bar_content_frame)
        bar_row_3_frame.setFixedHeight(40)
        bar_row_3_layout = QHBoxLayout(bar_row_3_frame)
        bar_row_3_layout.setContentsMargins(0, 0, 0, 0)
        bar_row_3_layout.setSpacing(15)
        self.add_effect_comboboxes_to_layout_row1(bar_row_3_layout)
        self.bottom_bar_main_layout.addWidget(bar_row_3_frame)
        bar_row_4_frame = QFrame(self.bottom_bar_content_frame)
        bar_row_4_frame.setFixedHeight(40)
        bar_row_4_layout = QHBoxLayout(bar_row_4_frame)
        bar_row_4_layout.setContentsMargins(0, 0, 0, 0)
        bar_row_4_layout.setSpacing(15)
        self.add_effect_labels_to_layout_row2(bar_row_4_layout)
        self.bottom_bar_main_layout.addWidget(bar_row_4_frame)
        bar_row_5_frame = QFrame(self.bottom_bar_content_frame)
        bar_row_5_frame.setFixedHeight(40)
        bar_row_5_layout = QHBoxLayout(bar_row_5_frame)
        bar_row_5_layout.setContentsMargins(0, 0, 0, 0)
        bar_row_5_layout.setSpacing(15)
        self.add_effect_comboboxes_to_layout_row2(bar_row_5_layout)
        self.bottom_bar_main_layout.addWidget(bar_row_5_frame)
        self.effect_descriptions_scroll_area = QScrollArea(self.bottom_bar_content_frame)
        self.effect_descriptions_scroll_area.setWidgetResizable(True)
        self.effect_descriptions_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.effect_descriptions_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.effect_descriptions_scroll_area.setStyleSheet("QScrollArea { border: none; } QScrollBar:vertical { border: none; background: #383838; width: 10px; margin: 0px 0px 0px 0px; } QScrollBar::handle:vertical { background: #555; border-radius: 5px; min-height: 20px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; } QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }")
        self.effect_descriptions_widget = QWidget()
        self.effect_descriptions_layout = QVBoxLayout(self.effect_descriptions_widget)
        self.effect_descriptions_layout.setContentsMargins(0, 0, 0, 0)
        self.effect_descriptions_layout.setSpacing(10)
        self.add_effect_descriptions_to_layout(self.effect_descriptions_layout)
        self.effect_descriptions_scroll_area.setWidget(self.effect_descriptions_widget)
        self.bottom_bar_main_layout.addWidget(self.effect_descriptions_scroll_area)
        self.button_explanation_label = QLabel("<b>Save:</b> Mikrofon efekt ayarlarını kaydeder.\n<b>Reset:</b> Mikrofon efekt ayarlarını varsayılana sıfırlar ve kaydedilen ayarları siler.")
        self.button_explanation_label.setStyleSheet("font-size: 12px; color: #AAA; padding-top: 10px;")
        self.button_explanation_label.setWordWrap(True)
        self.button_explanation_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.effect_descriptions_layout.addWidget(self.button_explanation_label)
        self.bottom_bar_main_layout.addStretch()
        self.main_splitter.addWidget(self.bottom_bar_content_frame)
        main_layout.addWidget(self.main_splitter)
        initial_bottom_bar_height = 200 + 50
        self.main_splitter.setSizes([self.height() - initial_bottom_bar_height, initial_bottom_bar_height])
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)

    def add_effect_labels_to_layout_row1(self, layout):
        labels_data = [("Noise Gate:", "noise_gate_threshold"), ("Release:", "noise_gate_release"), ("HP Filter:", "hp_filter"), ("LP Filter:", "lp_filter_mic"), ("Gain:", "gain"), ("Reverb Red.:", "reverb_reduction"), ("De-Esser:", "de_esser"), ("De-Hum:", "de_hum")]
        for text, _ in labels_data:
            label = QLabel(text)
            label.setStyleSheet("font-weight: bold; color: #EEE; font-size: 12px;")
            label.setAlignment(Qt.AlignCenter)
            label.setFixedSize(115, 20)
            layout.addWidget(label)
        layout.addStretch()

    def add_effect_comboboxes_to_layout_row1(self, layout):
        comboboxes = [self.combo_noise_gate_threshold, self.combo_noise_gate_release, self.combo_hp_filter, self.combo_lp_filter_mic, self.combo_gain, self.combo_reverb_reduction, self.combo_de_esser, self.combo_de_hum]
        for combo in comboboxes:
            combo.setFixedSize(115, 30)
            combo.setStyleSheet(self.buttonStyle())
            layout.addWidget(combo)
        layout.addStretch()

    def add_effect_labels_to_layout_row2(self, layout):
        labels_data = [("AI Noise Red.:", "ai_noise_reduction"), ("Comp. Ratio:", "comp_ratio"), ("Comp. Attack:", "comp_attack"), ("Comp. Release:", "comp_release"), ("Comp. Makeup:", "comp_makeup_gain"), ("EQ Gain:", "eq_gain"), ("EQ Freq.:", "eq_frequency"), ("EQ Q:", "eq_q")]
        for text, _ in labels_data:
            label = QLabel(text)
            label.setStyleSheet("font-weight: bold; color: #EEE; font-size: 12px;")
            label.setAlignment(Qt.AlignCenter)
            label.setFixedSize(115, 20)
            layout.addWidget(label)
        layout.addStretch()

    def add_effect_comboboxes_to_layout_row2(self, layout):
        comboboxes = [self.combo_ai_noise_reduction, self.combo_comp_ratio, self.combo_comp_attack, self.combo_comp_release, self.combo_comp_makeup_gain, self.combo_eq_gain, self.combo_eq_frequency, self.combo_eq_q]
        for combo in comboboxes:
            combo.setFixedSize(115, 30)
            combo.setStyleSheet(self.buttonStyle())
            layout.addWidget(combo)
        layout.addStretch()

    def triggerCoreSwitcher(self):
        if self.core_window_ref and hasattr(self.core_window_ref, 'showSwitcher'):
            self.core_window_ref.showSwitcher()
        else:
            QMessageBox.information(self, 'Sound', 'Main window or showSwitcher not found.')

    def set_default_microphone_effects(self):
        if not self.lib or not self.audio_engine: return
        self.combo_noise_gate_threshold.setCurrentText("-70dB")
        self.combo_noise_gate_release.setCurrentText("20ms")
        self.combo_hp_filter.setCurrentText("150Hz")
        self.combo_lp_filter_mic.setCurrentText("10000Hz")
        self.combo_gain.setCurrentText("+6dB")
        self.combo_reverb_reduction.setCurrentText("Off")
        self.combo_de_esser.setCurrentText("Off")
        self.combo_de_hum.setCurrentText("Off")
        self.combo_ai_noise_reduction.setCurrentText("On")
        self.combo_comp_ratio.setCurrentText("3:1")
        self.combo_comp_attack.setCurrentText("5ms")
        self.combo_comp_release.setCurrentText("150ms")
        self.combo_comp_makeup_gain.setCurrentText("+3dB")
        self.combo_eq_gain.setCurrentText("0dB")
        self.combo_eq_frequency.setCurrentText("1000Hz")
        self.combo_eq_q.setCurrentText("1.0")
        print("Default microphone effect settings applied.")

    def save_settings(self):
        settings = {
            "noise_gate_threshold": self.combo_noise_gate_threshold.currentText(),
            "noise_gate_release": self.combo_noise_gate_release.currentText(),
            "hp_filter": self.combo_hp_filter.currentText(),
            "lp_filter_mic": self.combo_lp_filter_mic.currentText(),
            "gain": self.combo_gain.currentText(),
            "reverb_reduction": self.combo_reverb_reduction.currentText(),
            "de_esser": self.combo_de_esser.currentText(),
            "de_hum": self.combo_de_hum.currentText(),
            "ai_noise_reduction": self.combo_ai_noise_reduction.currentText(),
            "comp_ratio": self.combo_comp_ratio.currentText(),
            "comp_attack": self.combo_comp_attack.currentText(),
            "comp_release": self.combo_comp_release.currentText(),
            "comp_makeup_gain": self.combo_comp_makeup_gain.currentText(),
            "eq_gain": self.combo_eq_gain.currentText(),
            "eq_frequency": self.combo_eq_frequency.currentText(),
            "eq_q": self.combo_eq_q.currentText(),
        }
        try:
            os.makedirs(SETTINGS_DIR, exist_ok=True)
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
            print(f"Ayarlar kaydedildi: {SETTINGS_FILE}")
        except Exception as e:
            QMessageBox.critical(self, 'Save Settings Error', f'Ayarlar kaydedilirken bir hata oluştu: {e}')

    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
            self.combo_noise_gate_threshold.setCurrentText(settings.get("noise_gate_threshold", "-70dB"))
            self.combo_noise_gate_release.setCurrentText(settings.get("noise_gate_release", "20ms"))
            self.combo_hp_filter.setCurrentText(settings.get("hp_filter", "150Hz"))
            self.combo_lp_filter_mic.setCurrentText(settings.get("lp_filter_mic", "10000Hz"))
            self.combo_gain.setCurrentText(settings.get("gain", "+6dB"))
            self.combo_reverb_reduction.setCurrentText(settings.get("reverb_reduction", "Off"))
            self.combo_de_esser.setCurrentText(settings.get("de_esser", "Off"))
            self.combo_de_hum.setCurrentText(settings.get("de_hum", "Off"))
            self.combo_ai_noise_reduction.setCurrentText(settings.get("ai_noise_reduction", "On"))
            self.combo_comp_ratio.setCurrentText(settings.get("comp_ratio", "3:1"))
            self.combo_comp_attack.setCurrentText(settings.get("comp_attack", "5ms"))
            self.combo_comp_release.setCurrentText(settings.get("comp_release", "150ms"))
            self.combo_comp_makeup_gain.setCurrentText(settings.get("comp_makeup_gain", "+3dB"))
            self.combo_eq_gain.setCurrentText(settings.get("eq_gain", "0dB"))
            self.combo_eq_frequency.setCurrentText(settings.get("eq_frequency", "1000Hz"))
            self.combo_eq_q.setCurrentText(settings.get("eq_q", "1.0"))
            print(f"Ayarlar yüklendi: {SETTINGS_FILE}")
        except Exception as e:
            QMessageBox.critical(self, 'Load Settings Error', f'Ayarlar yüklenirken bir hata oluştu: {e}\nVarsayılan ayarlar kullanılacak.')
            self.set_default_microphone_effects()

    def reset_settings(self):
        reply = QMessageBox.question(self, 'Reset Settings', "Tüm ayarları varsayılana sıfırlamak istediğinizden emin misiniz? Kaydedilen ayarlar silinecek.", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return
        self.set_default_microphone_effects()
        try:
            if os.path.exists(SETTINGS_FILE):
                os.remove(SETTINGS_FILE)
            QMessageBox.information(self, 'Reset Settings', 'Ayarlar varsayılana sıfırlandı.')
        except Exception as e:
            QMessageBox.critical(self, 'Reset Settings Error', f'Ayar dosyası silinirken bir hata oluştu: {e}')

    def add_effect_descriptions_to_layout(self, layout):
        descriptions = {
            "Noise Gate:": "Gürültü Kapısı, belirli bir eşiğin altındaki sesleri keserek arka plan gürültüsünü azaltır. Fan sesi gibi sürekli gürültüler için etkilidir.",
            "Release:": "Gürültü kapısı kapandıktan sonra sesin ne kadar süreyle kesileceğini belirler.",
            "HP Filter:": "Yüksek Geçiren Filtre, belirli bir frekansın altındaki tüm sesleri keser.",
            "LP Filter:": "Düşük Geçiren Filtre, belirli bir frekansın üzerindeki tüm sesleri keser.",
            "Gain:": "Mikrofon giriş kazancını ayarlar. Ses seviyesini artırır veya azaltır.",
            "Reverb Red.:": "Yankı Azaltma, kayıt ortamındaki yankıyı azaltmaya çalışır.",
            "De-Esser:": "De-Esser, 's' ve 'ş' gibi seslerdeki sert tıslama seslerini (sibilans) azaltır.",
            "De-Hum:": "De-Hum, elektrik şebekesinden kaynaklanan 50Hz veya 60Hz uğultu seslerini (hum) giderir.",
            "AI Noise Red.:": "Yapay Zeka Destekli Gürültü Azaltma, gürültüleri etkili bir şekilde azaltır.",
            "Comp. Ratio:": "Kompresör Oranı, eşiği aşan seslerin ne kadar sıkıştırılacağını belirler.",
            "Comp. Attack:": "Kompresörün sıkıştırmaya başlaması için geçen süreyi belirler.",
            "Comp. Release:": "Kompresörün sıkıştırmayı bırakması için geçen süreyi belirler.",
            "Comp. Makeup:": "Kompresör sonrası kaybedilen ses seviyesini telafi etmek için eklenen kazançtır.",
            "EQ Gain:": "Parametrik EQ bandının kazancını ayarlar.",
            "EQ Freq.:": "Parametrik EQ bandının merkez frekansını ayarlar.",
            "EQ Q:": "Parametrik EQ bandının Q faktörünü ayarlar (etki genişliği)."
        }
        for label_text, description_text in descriptions.items():
            description_label = QLabel(f"<b>{label_text}</b> {description_text}")
            description_label.setStyleSheet("font-size: 12px; color: #AAA;")
            description_label.setWordWrap(True)
            description_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(description_label)

    def load_files(self):
        """
        Dosya seçme diyaloğunu açar ve SADECE .wav dosyalarını C++ motoruna yükler.
        """
        if not self.lib or not self.audio_engine:
            QMessageBox.warning(self, 'Warning', 'Audio engine is not available.')
            return

        filter_str = "WAV Ses Dosyası (*.wav);;Tüm Dosyalar (*)"

        QDir().mkpath(SoundEditorWindow.DEFAULT_BASE_DIR)
        file_paths, _ = QFileDialog.getOpenFileNames(self, "WAV Dosyalarını Seç", SoundEditorWindow.DEFAULT_BASE_DIR, filter_str)

        if file_paths:
            self.load_wav_files_into_engine(file_paths)

    def load_files_from_path(self, file_paths):
        """
        Verilen dosya yollarını doğrudan C++ motoruna yükler.
        Sadece .wav dosyaları beklendiği varsayılır. Bu metod Kavram.py tarafından kullanılır.
        """
        if not file_paths:
            return

        # Sadece .wav dosyalarını filtrele, diğerlerini yoksay
        wav_paths = [path for path in file_paths if path.lower().endswith('.wav')]
        if not wav_paths:
            QMessageBox.warning(self, 'Uyarı', 'Seçilen dosyalar arasında .wav formatında dosya bulunamadı.')
            return

        self.load_wav_files_into_engine(wav_paths)

    def load_wav_files_into_engine(self, file_paths):
        """
        Verilen .wav dosya yollarını C++ motoruna yükler.
        """
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
                self.update_waveform()
                self.update_ui()
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
        if not self.lib or not self.audio_engine: return
        speed = float(txt.replace('x', ''))
        self.lib.set_speed(self.audio_engine, ctypes.c_float(speed))

    def change_scroll_step(self, txt):
        try:
            self.scroll_step_ms = int(txt.replace('s', '')) * 1000
        except ValueError:
            pass

    def add_split_point_from_playhead(self):
        if not self.lib or not self.audio_engine: return
        if self.lib.get_is_playing(self.audio_engine): return
        if self.lib.get_duration_ms(self.audio_engine) == 0: return
        current_pos_ms = self.lib.get_position_ms(self.audio_engine)
        self.waveform_widget.add_split_point(current_pos_ms)

    def delete_selected_segments(self):
        if not self.lib or not self.audio_engine: return
        selected_segments = self.waveform_widget.get_selected_segments()
        if not selected_segments: return

        original_split_points = list(self.waveform_widget.split_points_ms)
        new_split_points = []
        segments_to_delete = sorted(selected_segments, key=lambda x: x[1], reverse=True)
        successful_deletions = []

        for start_ms, end_ms in segments_to_delete:
            if self.lib.delete_audio_segment(self.audio_engine, start_ms, end_ms) == 0:
                successful_deletions.append((start_ms, end_ms))

        current_shift = 0
        deleted_segment_index = 0
        for original_sp in original_split_points:
            while deleted_segment_index < len(successful_deletions) and original_sp >= successful_deletions[deleted_segment_index][1]:
                current_shift += successful_deletions[deleted_segment_index][1] - successful_deletions[deleted_segment_index][0]
                deleted_segment_index += 1
            is_inside_deleted = any(del_start < original_sp < del_end for del_start, del_end in successful_deletions)
            if not is_inside_deleted:
                new_sp = original_sp - current_shift
                new_duration = self.lib.get_duration_ms(self.audio_engine)
                if new_sp > 0 and new_sp < new_duration:
                    new_split_points.append(new_sp)

        self.waveform_widget.split_points_ms = sorted(list(set(new_split_points)))

        if successful_deletions:
            self.update_waveform()
            self.update_ui()
            self.waveform_widget.clear_selection()

    def export_audio_file(self):
        if not self.lib or not self.audio_engine or self.lib.get_duration_ms(self.audio_engine) <= 0:
            QMessageBox.warning(self, 'Warning', 'Dışa aktarılacak ses verisi yok.')
            return
        QDir().mkpath(self.DEFAULT_BASE_DIR)
        save_path, _ = QFileDialog.getSaveFileName(self, "Sesi WAV Olarak Dışa Aktar", os.path.join(self.DEFAULT_BASE_DIR, "untitled.wav"), "WAV Ses Dosyası (*.wav)")
        if save_path:
            if not save_path.lower().endswith('.wav'):
                save_path += '.wav'
            c_file_path = save_path.encode('utf-8')
            if self.lib.save_audio_to_file(self.audio_engine, c_file_path) == 0:
                QMessageBox.information(self, 'Başarılı', f'Ses başarıyla kaydedildi:\n{save_path}')
            else:
                QMessageBox.critical(self, 'Hata', f'Ses kaydedilirken bir hata oluştu:\n{save_path}')

    def handle_record_insert(self):
        if not self.lib or not self.audio_engine: return
        if self.lib.get_is_playing(self.audio_engine): return
        if not self.is_recording_mode:
            if self.lib.start_microphone_recording(self.audio_engine) == 0:
                self.is_recording_mode = True
                self.btn_enter.setText('Stop')
        else:
            if self.lib.stop_microphone_recording(self.audio_engine) == 0:
                self.is_recording_mode = False
                self.btn_enter.setText('Record')
                current_pos_ms = self.lib.get_position_ms(self.audio_engine)
                os.makedirs(SETTINGS_DIR, exist_ok=True)
                file_to_insert = TEMP_RAW_RECORDING_FILE
                try:
                    if self.lib.save_recorded_audio_to_file(self.audio_engine, file_to_insert.encode('utf-8')) != 0:
                        QMessageBox.critical(self, 'Error', 'Could not save raw recorded audio.')
                        return
                    if self.combo_ai_noise_reduction.currentText() == "On":
                        try:
                            data, samplerate = sf.read(file_to_insert)
                            original_ndim = data.ndim
                            if original_ndim > 1: data = data.mean(axis=1)
                            reduced_noise_audio = nr.reduce_noise(y=data, sr=samplerate, prop_decrease=1.0, freq_mask_smooth_hz=500, time_mask_smooth_ms=100)
                            if original_ndim > 1: reduced_noise_audio = np.stack([reduced_noise_audio, reduced_noise_audio], axis=1)
                            sf.write(TEMP_CLEANED_RECORDING_FILE, reduced_noise_audio, samplerate)
                            file_to_insert = TEMP_CLEANED_RECORDING_FILE
                        except Exception as e:
                            QMessageBox.warning(self, 'AI Error', f'AI Noise Reduction sırasında hata oluştu: {e}\nRaw kayıt eklenecek.')
                    if self.lib.insert_audio_file(self.audio_engine, file_to_insert.encode('utf-8'), ctypes.c_int(current_pos_ms)) == 0:
                        self.update_waveform()
                        self.update_ui()
                    else:
                        QMessageBox.critical(self, 'Error', 'An error occurred while inserting recorded audio.')
                finally:
                    for temp_file in [TEMP_RAW_RECORDING_FILE, TEMP_CLEANED_RECORDING_FILE]:
                        if os.path.exists(temp_file):
                            try: os.remove(temp_file)
                            except Exception: pass

    def set_noise_gate_threshold(self, text):
        if not self.lib or not self.audio_engine: return
        threshold_map = {"Off": 1.0, "-80dB": 0.0001, "-75dB": 0.000178, "-70dB": 0.000316, "-65dB": 0.000562, "-60dB": 0.001, "-55dB": 0.00178, "-50dB": 0.00316, "-45dB": 0.00562, "-40dB": 0.01, "-35dB": 0.0178, "-30dB": 0.0316, "-25dB": 0.0562, "-20dB": 0.1}
        self.lib.set_mic_noise_gate_threshold(self.audio_engine, ctypes.c_float(threshold_map.get(text, 1.0)))

    def set_noise_gate_release(self, text):
        if not self.lib or not self.audio_engine: return
        self.lib.set_mic_noise_gate_release(self.audio_engine, ctypes.c_float(float(text.replace('ms', ''))))

    def set_high_pass_filter(self, text):
        if not self.lib or not self.audio_engine: return
        self.lib.set_mic_high_pass_filter_cutoff(self.audio_engine, ctypes.c_float(0.0 if text == "Off" else float(text.replace('Hz', ''))))

    def set_microphone_low_pass_filter(self, text):
        if not self.lib or not self.audio_engine: return
        self.lib.set_mic_low_pass_filter_cutoff(self.audio_engine, ctypes.c_float(0.0 if text == "Off" else float(text.replace('Hz', ''))))

    def set_microphone_gain(self, text):
        if not self.lib or not self.audio_engine: return
        gain_map = {"-12dB": 0.251, "-9dB": 0.355, "-6dB": 0.501, "-3dB": 0.707, "0dB": 1.0, "+3dB": 1.413, "+6dB": 1.995, "+9dB": 2.818, "+12dB": 3.981}
        self.lib.set_mic_input_gain(self.audio_engine, ctypes.c_float(gain_map.get(text, 1.0)))

    def set_reverb_reduction(self, text):
        if not self.lib or not self.audio_engine: return
        self.lib.set_mic_reverb_reduction_level(self.audio_engine, ctypes.c_int(["Off", "Low", "Medium", "High", "Very High"].index(text)))

    def set_de_esser(self, text):
        if not self.lib or not self.audio_engine: return
        self.lib.set_mic_de_esser_level(self.audio_engine, ctypes.c_int(["Off", "Low", "Medium", "High"].index(text)))

    def set_de_hum(self, text):
        if not self.lib or not self.audio_engine: return
        self.lib.set_mic_de_hum_level(self.audio_engine, ctypes.c_int(["Off", "Low", "Medium", "High"].index(text)))

    def set_ai_noise_reduction_mode(self, text):
        print(f"AI Noise Reduction mode set to: {text}")

    def set_compressor_ratio(self, text):
        if not self.lib or not self.audio_engine: return
        ratio = 1000.0 if text == "Inf:1" else float(text.replace(':1', ''))
        self.lib.set_mic_compressor_ratio(self.audio_engine, ctypes.c_float(ratio))

    def set_compressor_attack(self, text):
        if not self.lib or not self.audio_engine: return
        self.lib.set_mic_compressor_attack(self.audio_engine, ctypes.c_float(float(text.replace('ms', ''))))

    def set_compressor_release(self, text):
        if not self.lib or not self.audio_engine: return
        self.lib.set_mic_compressor_release(self.audio_engine, ctypes.c_float(float(text.replace('ms', ''))))

    def set_compressor_makeup_gain(self, text):
        if not self.lib or not self.audio_engine: return
        self.lib.set_mic_compressor_makeup_gain(self.audio_engine, ctypes.c_float(float(text.replace('dB', ''))))

    def set_eq_gain(self, text):
        if not self.lib or not self.audio_engine: return
        self.lib.set_mic_eq_gain(self.audio_engine, ctypes.c_float(float(text.replace('dB', ''))))
        self.lib.calculate_eq_coefficients(self.audio_engine)

    def set_eq_frequency(self, text):
        if not self.lib or not self.audio_engine: return
        self.lib.set_mic_eq_frequency(self.audio_engine, ctypes.c_float(float(text.replace('Hz', ''))))
        self.lib.calculate_eq_coefficients(self.audio_engine)

    def set_eq_q(self, text):
        if not self.lib or not self.audio_engine: return
        self.lib.set_mic_eq_q(self.audio_engine, ctypes.c_float(float(text)))
        self.lib.calculate_eq_coefficients(self.audio_engine)

    def buttonStyle(self):
        return """
            QPushButton, QComboBox {
                background-color: transparent; color: white; font-size: 14px;
                font-weight: bold; border: 2px solid #555; border-radius: 8px;
                padding: 5px 15px;
            }
            QPushButton:hover, QComboBox:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
            QComboBox::drop-down { border: 0px; }
            QComboBox::down-arrow { image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTcgMTBMMTIgMTVMMTcgMTAiIHN0cm9rZT0iI2VlZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lSm9pbj0icm91bmQiLz4KPC9sYXZnPg==); width: 16px; height: 16px; }
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

# Main application loop
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
