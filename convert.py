# Kavram 1.0.0
# Copyright (C) 2025-10-23 Kavram or Contributors
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
#
# Kavram 1.0.0
# Copyright (C) 2025-10-23 Kavram veya Contributors
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

# Updated by Google Gemini (Fixed PySide/PyQt conflict and updated button design)

import sys
import os
import time
# SADECE PyQt5 kullanılıyor.
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QMessageBox, QProgressBar, QComboBox,
    QLineEdit, QFormLayout
)
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon
from pydub.effects import normalize, compress_dynamic_range, low_pass_filter, high_pass_filter

# Import the pydub library. FFmpeg must be installed on the system.
try:
    from pydub import AudioSegment
except ImportError:
    print("Error: pydub library not found. Please install it using 'pip install pydub'.")
    sys.exit(1)
except FileNotFoundError:
    print("Error: FFmpeg not found. Please install FFmpeg on your system and add it to PATH.")
    sys.exit(1)

# Define supported file types
AUDIO_EXTENSIONS = ['.mp3', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.aiff', '.saund', '.wav']
VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS + VIDEO_EXTENSIONS

DEFAULT_EXPORT_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')

class ConversionWorker(QObject):
    # PyQt5 sinyal tanımı: QObject dışından pyqtSignal kullanılır.
    finished = pyqtSignal(object, float)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, audio_segment, settings):
        super().__init__()
        self.audio = audio_segment
        self.settings = settings
        self.is_running = True

    def run(self):
        start_time = time.time()
        try:
            self.progress.emit(10)
            processed_audio = self.audio

            # 1. Speed Change
            speed = self.settings['speed']
            if speed != 1.0:
                # pydub'da speedup method'u yok, dolayısıyla frame_rate değiştirme simülasyonu
                # Pydub ile hız değişimi için, audiospeeds kütüphanesi veya manuel yeniden örnekleme gereklidir.
                # Basitçe yeniden örnekleme hızını (frame_rate) değiştirerek hızı simüle ediyoruz,
                # bu da hız ve perdeyi birlikte değiştirir.
                new_frame_rate = int(processed_audio.frame_rate * speed)
                processed_audio = processed_audio.set_frame_rate(new_frame_rate)
            self.progress.emit(25)

            # 2. Pitch Change
            pitch_semitones = self.settings['pitch']
            if pitch_semitones != 0:
                octaves = pitch_semitones / 12.0
                new_sample_rate = int(processed_audio.frame_rate * (2.0 ** octaves))
                processed_audio = processed_audio._spawn(processed_audio.raw_data, overrides={'frame_rate': new_sample_rate})
            self.progress.emit(40)

            # 3. Effects
            effect_index = self.settings['effect']
            if effect_index > 0:
                processed_audio = self.apply_effect(processed_audio, effect_index)
            self.progress.emit(60)

            # 4. Frequency Change (Applied last)
            if self.settings['change_freq_on']:
                new_freq = self.settings['new_freq']
                if new_freq > 0:
                    processed_audio = processed_audio.set_frame_rate(new_freq)
            self.progress.emit(80)

            elapsed_time = time.time() - start_time
            self.finished.emit(processed_audio, elapsed_time)
            self.progress.emit(100)
        except Exception as e:
            # Beklenmedik hataları sinyal olarak gönder
            self.error.emit(str(e))

    def apply_effect(self, audio, index):
        """ Seçilen indekse göre ses efektini uygular. """
        if index == 1: return normalize(audio)
        if index == 2: return compress_dynamic_range(audio)
        if index == 3: return low_pass_filter(audio, 1000)
        if index == 4: return high_pass_filter(audio, 3000)
        if index == 5: return audio.fade_in(1000).fade_out(1000)
        if index == 6: return audio.invert_phase()
        if index == 7: return audio.pan(-0.5) # Pan Left
        if index == 8: return audio.pan(0.5)  # Pan Right
        return audio # Etki yoksa orijinali döndür

    def stop(self):
        self.is_running = False

class UniversalConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.original_audio = None
        self.converted_audio = None
        self.original_format = None
        self.conversion_thread = None
        self.conversion_worker = None
        self.settings = QSettings("Kavram", "UniversalConverter")

        self.init_ui()
        self.load_settings()
        self.update_button_states()

    def init_ui(self):
        # UI TITLE & STYLES (Localized to English)
        self.setWindowTitle('Convert')
        # İkon dosyasının mevcut olduğunu varsayıyoruz
        try:
            self.setWindowIcon(QIcon('ikon/Kavram.png'))
        except:
            pass # İkon bulunamazsa uyarı verme

        self.resize(550, 600)
        # Daha profesyonel koyu tema
        self.setStyleSheet('background-color: #2E2E2E; color: #E0E0E0; font-family: "Inter", sans-serif; font-size: 11pt;')

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)

        content_area = self.create_content_area()
        main_layout.addWidget(content_area)

    def create_top_bar(self):
        top_bar = QFrame()
        top_bar.setFixedHeight(40) # Yüksekliği artırıldı
        top_bar.setStyleSheet('background-color: #1F1F1F; border-bottom: 2px solid #555;')

        bar_layout = QHBoxLayout(top_bar)
        bar_layout.setContentsMargins(15, 5, 15, 5)
        bar_layout.setSpacing(15)

        # Button names localized to English
        self.btn_file = QPushButton('File')
        self.btn_convert = QPushButton('Convert')
        self.btn_reset = QPushButton('Reset')
        self.btn_export = QPushButton('Export')

        self.btn_file.clicked.connect(self.select_file)
        self.btn_convert.clicked.connect(self.start_conversion)
        self.btn_export.clicked.connect(self.export_file)
        self.btn_reset.clicked.connect(self.reset_settings)

        # Yeni stil fonksiyonunu çağır
        button_style = self.get_button_style()
        for btn in [self.btn_file, self.btn_convert, self.btn_reset, self.btn_export]:
            # Kullanıcının isteği üzerine sabit boyut (90x30) uygulandı.
            btn.setFixedSize(90, 30)
            btn.setStyleSheet(button_style)
            btn.setCursor(Qt.PointingHandCursor) # Mouse imlecini değiştir

        bar_layout.addWidget(self.btn_file)
        bar_layout.addWidget(self.btn_convert)
        bar_layout.addWidget(self.btn_reset)
        bar_layout.addStretch()
        bar_layout.addWidget(self.btn_export)

        return top_bar

    def create_content_area(self):
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)

        # Status and Info labels localized to English
        self.status_label = QLabel('Please select an audio or video file.')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 16px; color: #555;")

        self.info_label = QLabel("File Info: - | Frequency: - Hz")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("font-size: 12px; color: #555;")


        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(15)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 7px;
                background-color: #1F1F1F;
                color: #E0E0E0;
                text-align: center;
                padding: 2px;
            }
            QProgressBar::chunk {
                background-color: #5B9AFF; /* Mavi renk */
                border-radius: 6px;
            }
        """)

        settings_frame = self.create_settings_panel()

        content_layout.addWidget(self.status_label)
        content_layout.addWidget(self.info_label)
        content_layout.addWidget(self.progress_bar)
        content_layout.addWidget(settings_frame)
        content_layout.addStretch()

        return content_frame

    def create_settings_panel(self):
        # Ayarlar panelini daha şık hale getir
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                border: 1px solid #444;
                border-radius: 12px;
                background-color: #282828;
            }
            QLabel {
                border: none;
                font-weight: bold;
                color: #E0E0E0;
            }
            QComboBox, QLineEdit {
                padding: 6px;
                border: 1px solid #555;
                border-radius: 6px;
                background-color: #1F1F1F;
                color: #E0E0E0;
            }
            QComboBox::drop-down { border: 0px; }
        """)

        layout = QFormLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.setHorizontalSpacing(30)
        layout.setVerticalSpacing(15)

        # 1. Format
        self.format_combo = QComboBox()
        self.format_combo.addItems(['.wav', '.opus'])

        # 2. Frequency Change (Localized to English)
        self.change_freq_combo = QComboBox()
        self.change_freq_combo.addItems(['Off', 'On'])
        self.freq_input = QLineEdit()
        self.freq_input.setPlaceholderText("E.g.: 44100")
        self.freq_input.setVisible(False)
        self.change_freq_combo.currentIndexChanged.connect(self.toggle_freq_input)

        # 3. Speed
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(['0.5', '1.0', '1.1', '1.2', '1.25', '1.3', '1.4', '1.5', '1.6', '1.9', '2.0', '2.5', '2.7', '3.0'])

        # 4. Pitch (Localized to English)
        self.pitch_combo = QComboBox()
        pitch_items = {f"Higher Pitch ({-i} Semitones)": -i for i in range(6, 0, -1)}
        pitch_items["Normal (0 Semitones)"] = 0
        pitch_items.update({f"Lower Pitch (+{i} Semitones)": i for i in range(1, 7)})
        self.pitch_data = list(pitch_items.values())
        self.pitch_combo.addItems(pitch_items.keys())

        # 5. Effects (Localized to English)
        self.effect_combo = QComboBox()
        self.effect_combo.addItems([
            "No Effect", "Normalize", "Compressor", "Low Pass Filter",
            "High Pass Filter", "Fade In/Out", "Invert Phase",
            "Pan Left", "Pan Right"
        ])

        # Form row labels localized to English
        layout.addRow("Output Format:", self.format_combo)
        layout.addRow("Change Frequency:", self.change_freq_combo)
        layout.addRow("New Frequency (Hz):", self.freq_input)
        layout.addRow("Audio Speed:", self.speed_combo)
        layout.addRow("Audio Pitch:", self.pitch_combo)
        layout.addRow("Audio Effect:", self.effect_combo)

        # Connect signals to save settings
        for widget in [self.format_combo, self.change_freq_combo, self.speed_combo, self.pitch_combo, self.effect_combo]:
            widget.currentIndexChanged.connect(self.save_settings)
        self.freq_input.textChanged.connect(self.save_settings)

        return frame

    def select_file(self):
        initial_dir = DEFAULT_EXPORT_DIR if os.path.exists(DEFAULT_EXPORT_DIR) else os.path.expanduser('~')
        file_filter = f"Supported Files ({' '.join(['*' + ext for ext in SUPPORTED_EXTENSIONS])});;All Files (*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", initial_dir, file_filter)

        if file_path:
            try:
                self.original_audio = AudioSegment.from_file(file_path)
                self.converted_audio = None

                # FIX: Extract the extension/format from the file path
                ext = os.path.splitext(file_path)[1].lstrip('.').upper()
                self.original_format = ext if ext else 'Unknown'

                file_name = os.path.basename(file_path)
                self.status_label.setText(f"File loaded:\n{file_name}")

                # FIX: Use the stored original_format instead of .format
                self.info_label.setText(f"Format: {self.original_format} | Frequency: {self.original_audio.frame_rate} Hz")

            except Exception as e:
                # Error message localized to English
                QMessageBox.critical(self, "Error", f"Could not load file:\n{e}")
                self.original_audio = None
            self.update_button_states()

    def start_conversion(self):
        if not self.original_audio: return

        settings = self.get_current_settings()

        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        # Status message localized to English
        self.status_label.setText("Conversion process is starting...")
        self.update_button_states(is_converting=True)

        self.conversion_thread = QThread()
        self.conversion_worker = ConversionWorker(self.original_audio, settings)
        self.conversion_worker.moveToThread(self.conversion_thread)

        self.conversion_thread.started.connect(self.conversion_worker.run)
        self.conversion_worker.finished.connect(self.on_conversion_finished)
        self.conversion_worker.error.connect(self.on_conversion_error)
        self.conversion_worker.progress.connect(self.progress_bar.setValue)

        self.conversion_thread.start()

    def on_conversion_finished(self, result, elapsed_time):
        self.converted_audio = result
        # Status message localized to English
        self.status_label.setText(f"Conversion completed in {elapsed_time:.2f} seconds.")
        self.clean_up_thread()
        self.update_button_states()

    def on_conversion_error(self, error_msg):
        self.converted_audio = None
        # Error message localized to English
        error_message = f"An error occurred during conversion:\n\n{error_msg}"
        self.status_label.setText("Conversion failed.")
        QMessageBox.critical(self, "Error", error_message)
        self.clean_up_thread()
        self.update_button_states()

    def clean_up_thread(self):
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.quit()
            self.conversion_thread.wait()
        self.progress_bar.setVisible(False)
        self.conversion_thread = None
        self.conversion_worker = None

    def export_file(self):
        if not self.converted_audio:
            # Warning localized to English
            QMessageBox.warning(self, "Warning", "No file to export.")
            return

        if not os.path.exists(DEFAULT_EXPORT_DIR):
            os.makedirs(DEFAULT_EXPORT_DIR)

        output_format = self.format_combo.currentText().replace('.', '')
        file_filter = f"{output_format.upper()} Files (*.{output_format})"
        default_name = f"converted_file.{output_format}"

        # Dialog title localized to English
        save_path, _ = QFileDialog.getSaveFileName(self, "Save File", os.path.join(DEFAULT_EXPORT_DIR, default_name), file_filter)

        if save_path:
            try:
                self.converted_audio.export(save_path, format=output_format)
                # Success message localized to English
                QMessageBox.information(self, "Success", f"File saved successfully:\n{save_path}")
            except Exception as e:
                # Error message localized to English
                QMessageBox.critical(self, "Error", f"Could not save file:\n{e}")

    def update_button_states(self, is_converting=False):
        self.btn_file.setEnabled(not is_converting)
        self.btn_convert.setEnabled(self.original_audio is not None and not is_converting)
        self.btn_export.setEnabled(self.converted_audio is not None and not is_converting)
        self.btn_reset.setEnabled(not is_converting)

    def get_button_style(self):
        # Yeni, modern, siyah temalı buton stili (Kullanıcının isteği üzerine)
        return """
            QPushButton {
                background-color: #0000; /* Koyu Gri/Siyah Arka Plan */
                color: #E0E0E0; /* Açık Beyaz Yazı */
                border: 2px solid #555555; /* Hafif Gri Kenarlık */
                border-radius: 8px; /* Yuvarlak Köşeler */
                padding: 5px 10px; /* Buton içi boşluk (90x30 boyuta uygun ayarlandı) */
                font-weight: bold;
                box-shadow: 0 3px 5px rgba(0, 0, 0, 0.4); /* Derin gölge */
                transition: all 0.15s ease-out;
            }
            QPushButton:hover {
                background-color: #3C3C3C; /* Hover'da biraz daha açık gri */
                border: 1px solid #777777;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.5);
            }
            QPushButton:pressed {
                background-color: #1A1A1A; /* Tıklamada neredeyse tam siyah */
                box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.6); /* İçeriden basılmış efekti */
                padding: 6px 10px 4px 10px; /* Basılma efekti için dikey hizalamayı değiştir */
            }
            QPushButton:disabled {
                background-color: #202020;
                color: #555;
                border: 1px solid #333;
                box-shadow: none;
            }
        """

    def toggle_freq_input(self, index):
        # Index 1 corresponds to 'On'
        self.freq_input.setVisible(index == 1)

    def get_current_settings(self):
        new_freq = 0
        try:
            new_freq = int(self.freq_input.text()) if self.freq_input.text() else 0
        except ValueError:
            pass

        return {
            'format': self.format_combo.currentText(),
            'change_freq_on': self.change_freq_combo.currentIndex() == 1,
            'new_freq': new_freq,
            'speed': float(self.speed_combo.currentText()),
            'pitch': self.pitch_data[self.pitch_combo.currentIndex()],
            'effect': self.effect_combo.currentIndex()
        }

    def reset_settings(self):
        self.format_combo.setCurrentIndex(0)
        self.change_freq_combo.setCurrentIndex(0)
        self.freq_input.setText("")
        self.speed_combo.setCurrentText("1.0")
        self.pitch_combo.setCurrentText("Normal (0 Semitones)") # Set to the correct English default text
        self.effect_combo.setCurrentIndex(0)
        self.save_settings()
        # Message localized to English
        QMessageBox.information(self, "Settings", "All settings have been reset to default.")

    def save_settings(self):
        # Setting keys remain the same, values are saved/loaded based on index/text
        self.settings.setValue("format", self.format_combo.currentIndex())
        self.settings.setValue("change_freq_on", self.change_freq_combo.currentIndex())
        self.settings.setValue("new_freq_text", self.freq_input.text())
        self.settings.setValue("speed", self.speed_combo.currentText())
        self.settings.setValue("pitch", self.pitch_combo.currentIndex())
        self.settings.setValue("effect", self.effect_combo.currentIndex())

    def load_settings(self):
        # Load settings based on index/text
        self.format_combo.setCurrentIndex(self.settings.value("format", 0, type=int))
        self.change_freq_combo.setCurrentIndex(self.settings.value("change_freq_on", 0, type=int))
        self.freq_input.setText(self.settings.value("new_freq_text", "", type=str))

        # Load speed carefully, ensuring '1.0' is the default if missing
        speed_text = self.settings.value("speed", "1.0", type=str)
        if speed_text in [self.speed_combo.itemText(i) for i in range(self.speed_combo.count())]:
             self.speed_combo.setCurrentText(speed_text)
        else:
             self.speed_combo.setCurrentText("1.0")

        # Load pitch (Default is index 6: Normal (0 Semitones))
        self.pitch_combo.setCurrentIndex(self.settings.value("pitch", 6, type=int))
        self.effect_combo.setCurrentIndex(self.settings.value("effect", 0, type=int))
        self.toggle_freq_input(self.change_freq_combo.currentIndex())

    def closeEvent(self, event):
        self.save_settings()
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_worker.stop()
            self.conversion_thread.quit()
            self.conversion_thread.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    converter = UniversalConverter()
    converter.show()
    sys.exit(app.exec_())