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
import wave
import subprocess
import tempfile
import shutil
import noisereduce as nr
import soundfile as sf
import numpy as np
import scipy.signal as sig
import librosa
from pydub import AudioSegment
import pyaudio
import json
import tarfile
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                             QPushButton, QCheckBox, QLabel,
                             QFileDialog, QSlider, QHBoxLayout, QTextEdit, QGroupBox,
                             QSpacerItem, QSizePolicy, QFrame, QMessageBox, QInputDialog, QProgressBar,
                             QComboBox, QGridLayout)
from PyQt5.QtGui import QIcon

# Ayarlar
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# Varsayılan dosya dizini
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Kavram", "Export")

# Kalıcı ayarlar için dosya adı. Kullanıcının belirttiği dosya adı kullanılıyor.
SETTINGS_FILE = "filter_settings c32.json"

class ProcessThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)
    log = pyqtSignal(str)

    def __init__(self, files_to_process, output_dir, filters, is_from_media_archive=False):
        super().__init__()
        self.files_to_process = files_to_process
        self.output_dir = output_dir
        self.filters = filters
        self.processed_files = []
        self.is_from_media_archive = is_from_media_archive

    def run(self):
        try:
            total_files = len(self.files_to_process)
            for i, (original_path, original_is_video) in enumerate(self.files_to_process):
                self.log.emit(f"İşleniyor {i+1}/{total_files}: {os.path.basename(original_path)}")

                rel_path = os.path.relpath(original_path, self.files_to_process[0][0].split(os.path.basename(original_path))[0]) if self.is_from_media_archive else os.path.basename(original_path)
                final_output_path = os.path.join(self.output_dir, rel_path)
                os.makedirs(os.path.dirname(final_output_path), exist_ok=True)

                temp_audio_path = os.path.join(self.output_dir, f"temp_audio_{i}.wav")
                processed_audio_path = os.path.join(self.output_dir, f"processed_audio_{i}.wav")

                self.progress.emit(int((i / total_files) * 100))

                # Giriş dosyasını WAV formatına dönüştür
                try:
                    self.log.emit(f"Dosya WAV formatına dönüştürülüyor: {rel_path}")
                    cmd = ['ffmpeg', '-y', '-i', original_path, '-ac', '1', '-ar', str(RATE), temp_audio_path]
                    subprocess.run(cmd, check=True, capture_output=True, text=True)
                except subprocess.CalledProcessError as e:
                    self.log.emit(f"ffmpeg dönüştürme hatası. Dosya atlanıyor: {rel_path}. Hata: {e.stderr}")
                    continue

                # WAV ses dosyasını oku ve filtrele
                data, rate = sf.read(temp_audio_path)
                if data.ndim > 1:
                    data = data.mean(axis=1) # Mono'ya çevir
                original_num_samples = len(data)

                processed = data.copy()

                # Filtreleme sırası sound_Engine.cpp'ye göre düzenlendi
                # 1. Gain
                gain_db = self.filters.get('gain', 0.0)
                if gain_db != 0.0:
                    self.log.emit(f"Gain uygulanıyor: {gain_db}dB")
                    processed *= 10 ** (gain_db / 20.0)

                # 2. High-Pass Filter
                hp_cutoff = self.filters.get('hp', 0.0)
                if hp_cutoff > 0:
                    self.log.emit(f"High-Pass Filtresi uygulanıyor: {hp_cutoff}Hz")
                    nyquist = 0.5 * rate
                    normalized_cutoff = hp_cutoff / nyquist
                    b, a = sig.butter(4, normalized_cutoff, btype='highpass', analog=False)
                    processed = sig.filtfilt(b, a, processed)

                # 3. Low-Pass Filter
                lp_cutoff = self.filters.get('lp', 0.0)
                if lp_cutoff > 0:
                    self.log.emit(f"Low-Pass Filtresi uygulanıyor: {lp_cutoff}Hz")
                    nyquist = 0.5 * rate
                    normalized_cutoff = lp_cutoff / nyquist
                    b, a = sig.butter(4, normalized_cutoff, btype='lowpass', analog=False)
                    processed = sig.filtfilt(b, a, processed)

                # 4. Noise Gate
                noise_gate_threshold = self.filters.get('noise_gate_threshold', 0.0)
                if noise_gate_threshold > 0:
                    self.log.emit(f"Noise Gate uygulanıyor: Eşik={noise_gate_threshold}")
                    # Basit bir noise gate implementasyonu
                    abs_data = np.abs(processed)
                    mask = abs_data > noise_gate_threshold
                    processed[~mask] = 0

                # 5. De-Hum
                de_hum_level = self.filters.get('de_hum_level', 0)
                if de_hum_level > 0:
                    q_map = {1: 10.0, 2: 30.0, 3: 60.0}
                    q_val = q_map.get(de_hum_level, 30.0)
                    self.log.emit(f"De-Hum uygulanıyor: Seviye={de_hum_level}, Q={q_val}")
                    for freq in [50, 60]: # 50Hz ve 60Hz için çentik filtre
                        b, a = sig.iirnotch(freq, q_val, fs=rate)
                        processed = sig.filtfilt(b, a, processed)

                # 6. De-Esser
                de_esser_level = self.filters.get('de_esser_level', 0)
                if de_esser_level > 0:
                    gain_map = {1: -3.0, 2: -6.0, 3: -9.0}
                    gain_db = gain_map.get(de_esser_level, 0.0)
                    self.log.emit(f"De-Esser uygulanıyor: Seviye={de_esser_level}, Kazanç={gain_db}dB")
                    # Yüksek frekansları baskılayan basit bir high-shelf filtresi
                    b, a = sig.butter(2, 6000, btype='high', fs=rate, analog=False)
                    high_freqs = sig.filtfilt(b, a, processed)
                    reduction_factor = 10 ** (gain_db / 20.0)
                    processed = processed - high_freqs + (high_freqs * reduction_factor)

                # 7. Reverb Reduction
                reverb_level = self.filters.get('reverb_level', 0)
                if reverb_level > 0:
                    level_map = {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4}
                    strength = level_map.get(reverb_level, 0)
                    self.log.emit(f"Reverb Azaltma uygulanıyor: Seviye={reverb_level}")
                    # Basit bir pre-emphasis filtresi ile simülasyon
                    processed = librosa.effects.preemphasis(processed, coef=0.97 - strength)

                # 8. Compressor
                comp_threshold = self.filters.get('compressor_threshold', 0.0)
                if comp_threshold != 0.0:
                    ratio = self.filters.get('compressor_ratio', 1.0)
                    self.log.emit(f"Compressor uygulanıyor: Eşik={comp_threshold}dB, Oran={ratio}:1")
                    # Pydub kullanarak dinamik aralık sıkıştırması
                    processed_int16 = (processed * 32767).astype(np.int16)
                    audio_segment = AudioSegment(
                        processed_int16.tobytes(),
                        frame_rate=rate,
                        sample_width=processed_int16.dtype.itemsize,
                        channels=1
                    )
                    from pydub.effects import compress_dynamic_range
                    compressed_segment = compress_dynamic_range(
                        audio_segment,
                        threshold=comp_threshold,
                        ratio=ratio,
                        attack=self.filters.get('compressor_attack', 5.0),
                        release=self.filters.get('compressor_release', 100.0)
                    )
                    processed = np.array(compressed_segment.get_array_of_samples(), dtype=np.float32) / 32767.0

                # 9. Parametric EQ
                eq_gain = self.filters.get('eq_gain', 0.0)
                if eq_gain != 0.0:
                    eq_freq = self.filters.get('eq_freq', 1000.0)
                    eq_q = self.filters.get('eq_q', 1.0)
                    self.log.emit(f"Parametrik EQ uygulanıyor: Kazanç={eq_gain}dB, Freq={eq_freq}Hz, Q={eq_q}")
                    b, a = sig.iirpeak(eq_freq, eq_q, fs=rate)
                    g = 10.0 ** (eq_gain / 20.0)
                    b = g * b
                    processed = sig.lfilter(b, a, processed)

                # 10. AI Noise Reduction
                if self.filters.get('ai_nr', False):
                    self.log.emit(f"AI Gürültü Azaltma uygulanıyor...")
                    processed = nr.reduce_noise(y=processed, sr=rate, prop_decrease=1.0, freq_mask_smooth_hz=500, time_mask_smooth_ms=100)

                # Orijinal uzunluğu koru
                if len(processed) < original_num_samples:
                    padding = np.zeros(original_num_samples - len(processed))
                    processed = np.concatenate((processed, padding))
                elif len(processed) > original_num_samples:
                    processed = processed[:original_num_samples]

                self.log.emit(f"İşlenmiş ses geçici WAV dosyasına kaydediliyor.")
                sf.write(processed_audio_path, processed, rate)

                # Video ise sesi birleştir, değilse formatı dönüştür
                if original_is_video:
                    self.log.emit(f"Video, işlenmiş ses ile yeniden birleştiriliyor.")
                    cmd = ['ffmpeg', '-y', '-i', original_path, '-i', processed_audio_path, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                           '-map', '0:v', '-map', '1:a', final_output_path]
                    subprocess.run(cmd, check=True, capture_output=True, text=True)
                else:
                    self.log.emit(f"İşlenmiş ses orijinal formata dönüştürülüyor.")
                    cmd = ['ffmpeg', '-y', '-i', processed_audio_path, final_output_path]
                    subprocess.run(cmd, check=True, capture_output=True, text=True)

                self.processed_files.append(final_output_path)

                # Geçici dosyaları temizle
                if os.path.exists(temp_audio_path): os.remove(temp_audio_path)
                if os.path.exists(processed_audio_path): os.remove(processed_audio_path)

            self.progress.emit(100)
            self.finished.emit(self.output_dir)
        except Exception as e:
            error_details = f"Bir hata oluştu: {type(e).__name__}\nDetaylar: {e}"
            if hasattr(e, 'stderr') and e.stderr:
                error_details += f"\nFFmpeg Stderr: {e.stderr}"
            self.error.emit(error_details)

class AudioCleanerUI(QWidget):
    def __init__(self):
        super().__init__()
        if not os.path.exists(DEFAULT_DIR):
            os.makedirs(DEFAULT_DIR)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.setWindowTitle("Filter")
        self.setWindowIcon(QIcon('ikon/Kavram.png'))  # Pencere ikonu eklendi
        self.setGeometry(100, 100, 850, 600) # Pencere boyutu ayarlandı
        self.setStyleSheet("""
            QWidget { background-color: #202020; color: #e0e0e0; font-family: 'Segoe UI', Arial; font-size: 14px; }
            QLabel { color: #e0e0e0; font-size: 14px; font-weight: bold; }
            QGroupBox { border: 1px solid #404040; border-radius: 8px; margin-top: 1ex; font-size: 14px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 5px; background-color: #202020; }
            QPushButton { background-color: transparent; color: white; font-size: 14px; font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 5px 15px; }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
            QPushButton:disabled { border: 2px solid #444; color: #888; }
            QTextEdit { background-color: #333333; border: 1px solid #555555; color: #e0e0e0; padding: 5px; border-radius: 5px; }
            #topBar { background-color: #282828; min-height: 40px; max-height: 40px; border-bottom: 2px solid #555; }
            QComboBox { background-color: #333; color: white; font-size: 14px; border: 1px solid #555; border-radius: 5px; padding: 5px; }
            QComboBox:hover { background-color: #444; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView { background-color: #282828; border: 1px solid #555; selection-background-color: #444; color: white; }
        """)

        main_layout = QVBoxLayout(self)
        self.input_path = ""
        self.extracted_files_list = []
        self.processed_files_dir = ""
        self.thread = None
        self.is_video_input = False
        self.is_from_media_archive = False
        self.temp_extract_dir = None
        self.tempdir = None

        # --- Üst Bar ---
        top_bar_frame = QFrame()
        top_bar_frame.setObjectName("topBar")
        top_bar_layout = QHBoxLayout(top_bar_frame)
        top_bar_layout.setContentsMargins(10, 5, 10, 5)

        self.file_btn = QPushButton("File")
        self.file_btn.clicked.connect(self.select_file)
        top_bar_layout.addWidget(self.file_btn)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_settings)
        top_bar_layout.addWidget(self.reset_btn)

        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.export_file)
        self.export_btn.setEnabled(False)
        top_bar_layout.addWidget(self.export_btn)

        top_bar_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.process_btn = QPushButton("Process")
        self.process_btn.clicked.connect(self.start_processing)
        self.process_btn.setEnabled(False)
        top_bar_layout.addWidget(self.process_btn)

        main_layout.addWidget(top_bar_frame)

        self.file_label = QLabel("Selected: No file selected")
        self.file_label.setAlignment(Qt.AlignCenter)
        self.file_label.setStyleSheet("padding: 5px; font-size: 12px; color: #aaa;")
        main_layout.addWidget(self.file_label)

        # --- Filtreler (2 Sütunlu Tasarım) ---
        filter_group = QGroupBox("Filters")
        filter_grid_layout = QGridLayout()

        # Sütun 1
        self.combo_ai_noise_reduction = self.create_filter_combo(filter_grid_layout, 0, 0, "AI Noise Reduction", ["Off", "On"])
        self.combo_noise_gate_threshold = self.create_filter_combo(filter_grid_layout, 1, 0, "Noise Gate", [f"{i}dB" for i in range(-80, -19, 5)] + ["Off"])
        self.combo_hp_filter = self.create_filter_combo(filter_grid_layout, 2, 0, "HP Filter", ["Off"] + [f"{i}Hz" for i in range(20, 301, 10)])
        self.combo_lp_filter_mic = self.create_filter_combo(filter_grid_layout, 3, 0, "LP Filter", ["Off"] + [f"{i}Hz" for i in range(2000, 20001, 1000)])
        self.combo_gain = self.create_filter_combo(filter_grid_layout, 4, 0, "Gain", [f"{i}dB" for i in range(-12, 13, 3)])
        self.combo_reverb_reduction = self.create_filter_combo(filter_grid_layout, 5, 0, "Reverb Reduction", ["Off", "Low", "Medium", "High", "Very High"])
        self.combo_de_esser = self.create_filter_combo(filter_grid_layout, 6, 0, "De-Esser", ["Off", "Low", "Medium", "High"])
        self.combo_de_hum = self.create_filter_combo(filter_grid_layout, 7, 0, "De-Hum", ["Off", "Low", "Medium", "High"])

        # Sütun 2
        self.combo_comp_threshold = self.create_filter_combo(filter_grid_layout, 0, 2, "Comp. Threshold", ["Off"] + [f"{i}dB" for i in range(-60, 1, 5)])
        self.combo_comp_ratio = self.create_filter_combo(filter_grid_layout, 1, 2, "Comp. Ratio", ["1:1", "2:1", "3:1", "4:1", "5:1", "8:1", "10:1", "Inf:1"])
        self.combo_comp_attack = self.create_filter_combo(filter_grid_layout, 2, 2, "Comp. Attack", [f"{i}ms" for i in [1, 5, 10, 20, 50, 100, 200]])
        self.combo_comp_release = self.create_filter_combo(filter_grid_layout, 3, 2, "Comp. Release", [f"{i}ms" for i in [50, 100, 200, 500, 1000, 2000]])
        self.combo_eq_gain = self.create_filter_combo(filter_grid_layout, 4, 2, "EQ Gain", [f"{i}dB" for i in range(-12, 13, 3)])
        self.combo_eq_frequency = self.create_filter_combo(filter_grid_layout, 5, 2, "EQ Freq.", [f"{i}Hz" for i in [500, 1000, 1500, 2000, 2500, 3000, 4000]])
        self.combo_eq_q = self.create_filter_combo(filter_grid_layout, 6, 2, "EQ Q", ["0.5", "1.0", "2.0", "3.0", "5.0", "8.0", "10.0"])

        filter_grid_layout.setColumnStretch(1, 1)
        filter_grid_layout.setColumnStretch(3, 1)
        filter_grid_layout.setColumnMinimumWidth(2, 40) # Sütunlar arasına boşluk ekle

        filter_group.setLayout(filter_grid_layout)
        main_layout.addWidget(filter_group)

        # --- Durum ve Log ---
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        self.status_label = QLabel("Status: Waiting...")
        status_layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        log_layout.addWidget(self.log)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

    def create_filter_combo(self, layout, row, col_start, label_text, items):
        """Yardımcı fonksiyon: Etiket ve ComboBox oluşturup grid'e ekler."""
        label = QLabel(label_text)
        combo = QComboBox()
        combo.addItems(items)
        layout.addWidget(label, row, col_start)
        layout.addWidget(combo, row, col_start + 1)
        return combo

    def start_processing(self):
        if not self.extracted_files_list:
            QMessageBox.warning(self, "Warning", "Please select a file or archive first.")
            return

        self.process_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Status: Processing...")

        if self.processed_files_dir and os.path.exists(self.processed_files_dir):
            shutil.rmtree(self.processed_files_dir)
        if self.tempdir is None:
            self.tempdir = tempfile.TemporaryDirectory()
        self.processed_files_dir = tempfile.mkdtemp(dir=self.tempdir.name)

        filters = {}
        # Tüm filtrelerin değerlerini al
        filters['ai_nr'] = self.combo_ai_noise_reduction.currentText() == "On"

        ng_text = self.combo_noise_gate_threshold.currentText()
        filters['noise_gate_threshold'] = 0.0 if ng_text == "Off" else 10 ** (float(ng_text.replace('dB', '')) / 20.0)

        hp_text = self.combo_hp_filter.currentText()
        filters['hp'] = 0.0 if hp_text == "Off" else float(hp_text.replace('Hz', ''))
        lp_text = self.combo_lp_filter_mic.currentText()
        filters['lp'] = 0.0 if lp_text == "Off" else float(lp_text.replace('Hz', ''))

        filters['gain'] = float(self.combo_gain.currentText().replace('dB', ''))

        level_map = {"Off": 0, "Low": 1, "Medium": 2, "High": 3, "Very High": 4}
        filters['reverb_level'] = level_map.get(self.combo_reverb_reduction.currentText(), 0)
        filters['de_esser_level'] = level_map.get(self.combo_de_esser.currentText(), 0)
        filters['de_hum_level'] = level_map.get(self.combo_de_hum.currentText(), 0)

        comp_thresh_text = self.combo_comp_threshold.currentText()
        filters['compressor_threshold'] = 0.0 if comp_thresh_text == "Off" else float(comp_thresh_text.replace('dB', ''))

        comp_ratio_text = self.combo_comp_ratio.currentText()
        filters['compressor_ratio'] = 1000.0 if comp_ratio_text == "Inf:1" else float(comp_ratio_text.replace(':1', ''))

        filters['compressor_attack'] = float(self.combo_comp_attack.currentText().replace('ms', ''))
        filters['compressor_release'] = float(self.combo_comp_release.currentText().replace('ms', ''))

        filters['eq_gain'] = float(self.combo_eq_gain.currentText().replace('dB', ''))
        filters['eq_freq'] = float(self.combo_eq_frequency.currentText().replace('Hz', ''))
        filters['eq_q'] = float(self.combo_eq_q.currentText())

        self.thread = ProcessThread(self.extracted_files_list, self.processed_files_dir, filters, self.is_from_media_archive)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.thread.progress.connect(self.progress_bar.setValue)
        self.thread.log.connect(self.log.append)
        self.thread.start()

    def load_settings(self):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)

            self.combo_ai_noise_reduction.setCurrentText(str(settings.get('ai_noise_reduction', "On")))
            self.combo_noise_gate_threshold.setCurrentText(str(settings.get('noise_gate_threshold', "-70dB")))
            self.combo_hp_filter.setCurrentText(str(settings.get('hp_filter', "150Hz")))
            self.combo_lp_filter_mic.setCurrentText(str(settings.get('lp_filter_mic', "10000Hz")))
            self.combo_gain.setCurrentText(str(settings.get('gain', "+6dB")))
            self.combo_reverb_reduction.setCurrentText(str(settings.get('reverb_reduction', "Off")))
            self.combo_de_esser.setCurrentText(str(settings.get('de_esser', "Off")))
            self.combo_de_hum.setCurrentText(str(settings.get('de_hum', "Off")))
            self.combo_comp_threshold.setCurrentText(str(settings.get('comp_threshold', "Off")))
            self.combo_comp_ratio.setCurrentText(str(settings.get('comp_ratio', "3:1")))
            self.combo_comp_attack.setCurrentText(str(settings.get('comp_attack', "5ms")))
            self.combo_comp_release.setCurrentText(str(settings.get('comp_release', "150ms")))
            self.combo_eq_gain.setCurrentText(str(settings.get('eq_gain', "0dB")))
            self.combo_eq_frequency.setCurrentText(str(settings.get('eq_freq', "1000Hz")))
            self.combo_eq_q.setCurrentText(str(settings.get('eq_q', "1.0")))

            self.log.append("Filtre ayarları dosyadan yüklendi.")
        except FileNotFoundError:
            self.log.append(f"Ayar dosyası '{SETTINGS_FILE}' bulunamadı. Varsayılan ayarlar kullanılıyor.")
            self.reset_settings(show_message=False)
        except Exception as e:
            self.log.append(f"Ayarlar yüklenemedi: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to load settings: {str(e)}")
            self.reset_settings(show_message=False)

    def save_settings(self):
        settings = {
            'ai_noise_reduction': self.combo_ai_noise_reduction.currentText(),
            'noise_gate_threshold': self.combo_noise_gate_threshold.currentText(),
            'hp_filter': self.combo_hp_filter.currentText(),
            'lp_filter_mic': self.combo_lp_filter_mic.currentText(),
            'gain': self.combo_gain.currentText(),
            'reverb_reduction': self.combo_reverb_reduction.currentText(),
            'de_esser': self.combo_de_esser.currentText(),
            'de_hum': self.combo_de_hum.currentText(),
            'comp_threshold': self.combo_comp_threshold.currentText(),
            'comp_ratio': self.combo_comp_ratio.currentText(),
            'comp_attack': self.combo_comp_attack.currentText(),
            'comp_release': self.combo_comp_release.currentText(),
            'eq_gain': self.combo_eq_gain.currentText(),
            'eq_freq': self.combo_eq_frequency.currentText(),
            'eq_q': self.combo_eq_q.currentText(),
        }
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=4)
            self.log.append("Filtre ayarları kaydedildi.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    def select_file(self):
        self._cleanup_temp_dirs()
        self.reset_ui_state()

        file_filter = "All Media Files (*.media *.wav *.mp3 *.aac *.m4a *.flac *.ogg *.mp4 *.avi *.mov *.mkv *.webm *.flv *.rec *.saund);;All Files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select File", DEFAULT_DIR, file_filter)
        if not path:
            return

        self.input_path = path
        self.file_label.setText(f"Selected: {os.path.basename(self.input_path)}")
        self.is_from_media_archive = self.input_path.lower().endswith('.media')

        if self.tempdir: self.tempdir.cleanup()
        self.tempdir = tempfile.TemporaryDirectory()

        if self.is_from_media_archive:
            self.log.append(f"Özel arşiv dosyası seçildi: {self.input_path}. Çıkarılıyor...")
            self.temp_extract_dir = tempfile.mkdtemp(dir=self.tempdir.name)
            try:
                with tarfile.open(self.input_path, 'r:*') as tar_ref:
                    tar_ref.extractall(self.temp_extract_dir)
                self.log.append(f"Arşiv çıkarıldı: {self.temp_extract_dir}")
                self.extracted_files_list = self._find_all_media_files(self.temp_extract_dir)
                if not self.extracted_files_list:
                    QMessageBox.warning(self, "Warning", "Arşivde medya dosyası bulunamadı.")
                    self.reset_ui_state()
                    return
                self.log.append(f"Arşivde {len(self.extracted_files_list)} medya dosyası bulundu. İşleme hazır.")
                self.process_btn.setEnabled(True)
            except Exception as e:
                self.on_error(f"Arşiv çıkarılırken hata: {str(e)}")
        else:
            self.is_video_input = any(self.input_path.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.rec'])
            self.extracted_files_list = [(self.input_path, self.is_video_input)]
            self.log.append(f"Tek dosya seçildi: {self.input_path}")
            self.process_btn.setEnabled(True)

    def _find_all_media_files(self, directory):
        found_files = []
        media_exts = ['.wav', '.mp3', '.aac', '.m4a', '.flac', '.ogg', '.saund', '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.rec']
        video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.rec']
        for root, _, files in os.walk(directory):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in media_exts:
                    full_path = os.path.join(root, file)
                    is_video = ext in video_exts
                    found_files.append((full_path, is_video))
        return found_files

    def on_finished(self, output_dir):
        self.status_label.setText("Processing finished. Ready to Export.")
        self.process_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.log.append("Tüm dosyalar işlendi. Şimdi dışa aktarabilirsiniz.")
        self.save_settings()

    def on_error(self, msg):
        self.status_label.setText("An error occurred.")
        self.process_btn.setEnabled(True)
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.log.append(msg)
        QMessageBox.critical(self, "Error", msg)
        self._cleanup_temp_dirs()

    def export_file(self):
        if not self.processed_files_dir or not os.path.exists(self.processed_files_dir):
            QMessageBox.warning(self, "Warning", "Please process files first.")
            return

        export_dir = os.path.join(DEFAULT_DIR, "filtre")
        os.makedirs(export_dir, exist_ok=True)
        input_base_name = os.path.basename(self.input_path)
        default_filename = os.path.join(export_dir, input_base_name)

        if self.is_from_media_archive:
            output_path, _ = QFileDialog.getSaveFileName(self, "Save Filtered Archive", default_filename, "*.media")
            if not output_path: return
            if not output_path.lower().endswith('.media'): output_path += '.media'

            try:
                self.log.append(f"Yeni .media arşivi oluşturuluyor: {output_path}")
                with tarfile.open(output_path, 'w:gz') as tar:
                    tar.add(self.processed_files_dir, arcname='.')
                self.status_label.setText("Export completed.")
                self.log.append(f"Arşiv dosyası oluşturuldu: {output_path}")
            except Exception as e:
                self.on_error(f"Dışa aktarma sırasında hata: {e}")
        else:
            original_ext = os.path.splitext(self.input_path)[1]
            output_path, _ = QFileDialog.getSaveFileName(self, "Save Filtered File", default_filename, f"*{original_ext}")
            if not output_path: return

            try:
                processed_file = os.listdir(self.processed_files_dir)[0]
                shutil.move(os.path.join(self.processed_files_dir, processed_file), output_path)
                self.status_label.setText("Export completed.")
                self.log.append(f"Dosya kaydedildi: {output_path}")
            except Exception as e:
                self.on_error(f"Dışa aktarma sırasında hata: {e}")

        self._cleanup_temp_dirs()
        self.reset_ui_state()

    def _cleanup_temp_dirs(self):
        if self.tempdir:
            self.tempdir.cleanup()
            self.tempdir = None
        self.temp_extract_dir = None
        self.processed_files_dir = None

    def reset_ui_state(self):
        self.process_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("Status: Waiting...")
        self.file_label.setText("Selected: No file selected")
        self.extracted_files_list = []
        self.input_path = ""
        self.is_from_media_archive = False
        self.is_video_input = False

    def reset_settings(self, show_message=True):
        """Ayarları varsayılana sıfırlar."""
        self.combo_ai_noise_reduction.setCurrentText("On")
        self.combo_noise_gate_threshold.setCurrentText("-70dB")
        self.combo_hp_filter.setCurrentText("150Hz")
        self.combo_lp_filter_mic.setCurrentText("10000Hz")
        self.combo_gain.setCurrentText("+6dB")
        self.combo_reverb_reduction.setCurrentText("Off")
        self.combo_de_esser.setCurrentText("Off")
        self.combo_de_hum.setCurrentText("Off")
        self.combo_comp_threshold.setCurrentText("Off")
        self.combo_comp_ratio.setCurrentText("3:1")
        self.combo_comp_attack.setCurrentText("5ms")
        self.combo_comp_release.setCurrentText("150ms")
        self.combo_eq_gain.setCurrentText("0dB")
        self.combo_eq_frequency.setCurrentText("1000Hz")
        self.combo_eq_q.setCurrentText("1.0")

        self.log.append("Filtre ayarları varsayılana sıfırlandı.")
        if show_message:
            QMessageBox.information(self, "Reset", "Ayarlar varsayılana sıfırlandı.")
        self.save_settings()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ui = AudioCleanerUI()
    ui.show()
    sys.exit(app.exec_())
