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

# Updated by Google Gemini
import sys
import os
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QMessageBox, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon

# Import the pydub library. FFmpeg must be installed on the system.
try:
    from pydub import AudioSegment
except ImportError:
    print("Hata: pydub kütüphanesi bulunamadı. Lütfen 'pip install pydub' komutu ile yükleyin.")
    sys.exit(1)
except FileNotFoundError:
    print("Hata: FFmpeg bulunamadı. Lütfen sisteminize FFmpeg'i kurun ve PATH'e ekleyin.")
    sys.exit(1)

# Define supported file types
# The user wants to convert audio and video files to WAV.
AUDIO_EXTENSIONS = ['.mp3', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.aiff', '.saund' '.wav']
VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS + VIDEO_EXTENSIONS

# Kullanıcının istediği varsayılan dışa aktarma dizini
DEFAULT_EXPORT_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')

class ConversionWorker(QObject):
    """
    Worker class that performs the conversion in the background without freezing the UI.
    """
    finished = pyqtSignal(object, float) # (converted_data, elapsed_time)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, input_path):
        super().__init__()
        self.input_path = input_path
        self.is_running = True

    def run(self):
        """Starts the conversion process."""
        start_time = time.time()
        try:
            self.progress.emit(5)

            # Load the file with pydub
            # This handles both audio and video files. For video, it extracts the audio stream.
            audio = AudioSegment.from_file(self.input_path)
            self.progress.emit(50)

            # Since the goal is to convert to WAV, we will export it directly as a WAV AudioSegment object.
            # pydub can directly convert the audio stream from various formats to an in-memory AudioSegment.
            # We don't need a separate export step for the worker itself.
            self.progress.emit(100)
            elapsed_time = time.time() - start_time
            self.finished.emit(audio, elapsed_time)

        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self.is_running = False

class UniversalConverter(QWidget):
    """
    A PyQt5 application designed to convert media files to WAV format.
    """
    def __init__(self):
        super().__init__()
        self.input_file_path = None
        self.converted_audio = None
        self.is_video_file = False
        self.conversion_thread = None
        self.conversion_worker = None

        self.setWindowTitle('Convert')
        self.setWindowIcon(QIcon('ikon/Kavram.png')) # Set the window icon as requested.
        self.resize(500, 450)
        self.setStyleSheet('background-color: #383838; color: white;')

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)

        content_area = self.create_content_area()
        main_layout.addWidget(content_area)
        main_layout.addStretch()

        self.update_button_states()

    def create_top_bar(self):
        """Creates the top bar and buttons."""
        top_bar = QFrame()
        top_bar.setFixedHeight(40)
        top_bar.setStyleSheet('background-color: #222; border-bottom: 1px solid #555;')

        bar_layout = QHBoxLayout(top_bar)
        bar_layout.setContentsMargins(10, 5, 10, 5)
        bar_layout.setSpacing(10)

        self.btn_file = QPushButton('File')
        self.btn_convert = QPushButton('Convert')
        self.btn_export = QPushButton('Export')

        self.btn_file.clicked.connect(self.select_file)
        self.btn_convert.clicked.connect(self.start_conversion)
        self.btn_export.clicked.connect(self.export_file)

        for btn in [self.btn_file, self.btn_convert, self.btn_export]:
            btn.setFixedSize(100, 30)
            btn.setStyleSheet(self.get_button_style())

        # Place buttons in the layout
        bar_layout.addWidget(self.btn_file)
        bar_layout.addWidget(self.btn_convert)
        bar_layout.addStretch() # Add space
        bar_layout.addWidget(self.btn_export) # Push Export to the right

        return top_bar

    def create_content_area(self):
        """Creates the content area (status label, progress bar)."""
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setAlignment(Qt.AlignCenter)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(20, 40, 20, 20)

        # The large SVG icon and its related code have been removed as per the user's request.

        self.status_label = QLabel('Lütfen bir ses veya video dosyası seçin.')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("font-size: 14px; color: #ccc;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                background-color: #222;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #606060;
                width: 10px;
                margin: 0.5px;
            }
        """)

        content_layout.addWidget(self.status_label)
        content_layout.addWidget(self.progress_bar)

        return content_frame

    def select_file(self):
        """Opens the file dialog that accepts all supported file types."""
        # Check if the custom default directory exists, otherwise use the home directory.
        initial_dir = DEFAULT_EXPORT_DIR if os.path.exists(DEFAULT_EXPORT_DIR) else os.path.expanduser('~')

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Dosya Seç", initial_dir,
            f"Desteklenen Dosyalar ({' '.join(['*' + ext for ext in SUPPORTED_EXTENSIONS])});;Tüm Dosyalar (*)"
        )

        if file_path:
            self.input_file_path = file_path
            self.converted_audio = None
            file_name = os.path.basename(file_path)
            _, ext = os.path.splitext(file_name)

            if ext.lower() in VIDEO_EXTENSIONS:
                self.is_video_file = True
                self.status_label.setText(f"Video dosyası seçildi:\n{file_name}")
            elif ext.lower() in AUDIO_EXTENSIONS:
                self.is_video_file = False
                self.status_label.setText(f"Ses dosyası seçildi:\n{file_name}")
            else:
                self.is_video_file = False # Treat as audio by default
                self.status_label.setText(f"Desteklenmeyen dosya seçildi:\n{file_name}\n(Ses dosyası olarak deneniyor)")

            print(f"Dosya seçildi: {self.input_file_path}")
            self.update_button_states()

    def start_conversion(self):
        """Starts the conversion process to WAV."""
        if not self.input_file_path:
            return

        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Dönüştürme işlemi başlatılıyor...")
        self.update_button_states(is_converting=True)

        self.conversion_thread = QThread()
        self.conversion_worker = ConversionWorker(self.input_file_path)
        self.conversion_worker.moveToThread(self.conversion_thread)

        self.conversion_thread.started.connect(self.conversion_worker.run)
        self.conversion_worker.finished.connect(self.on_conversion_finished)
        self.conversion_worker.error.connect(self.on_conversion_error)
        self.conversion_worker.progress.connect(self.update_progress)

        self.conversion_thread.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_conversion_finished(self, result, elapsed_time):
        """Runs when conversion is successful."""
        self.converted_audio = result
        self.status_label.setText(f"Dönüştürme {elapsed_time:.2f} saniyede tamamlandı.\nDosyayı dışa aktarabilirsiniz.")
        self.clean_up_thread()
        self.update_button_states()

    def on_conversion_error(self, error_msg):
        """Runs when an error occurs during conversion."""
        self.converted_audio = None
        error_message = f"Dönüştürme sırasında bir hata oluştu:\n\n{error_msg}\n\nLütfen FFmpeg'in sisteminizde doğru bir şekilde kurulu olduğundan emin olun."
        self.status_label.setText("Dönüştürme başarısız oldu.")
        QMessageBox.critical(self, "Hata", error_message)
        self.clean_up_thread()
        self.update_button_states()

    def clean_up_thread(self):
        """Cleans up the background thread."""
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.quit()
            self.conversion_thread.wait()
        self.progress_bar.setVisible(False)
        self.conversion_thread = None
        self.conversion_worker = None

    def export_file(self):
        """Saves the converted audio as a WAV file."""
        if not self.converted_audio:
            QMessageBox.warning(self, "Uyarı", "Dışa aktarılacak dönüştürülmüş bir ses dosyası yok.")
            return

        # Varsa, varsayılan dışa aktarma dizinini oluşturun.
        if not os.path.exists(DEFAULT_EXPORT_DIR):
            os.makedirs(DEFAULT_EXPORT_DIR)

        default_name = os.path.splitext(os.path.basename(self.input_file_path))[0] + ".wav"
        save_path, _ = QFileDialog.getSaveFileName(
            self, "WAV Dosyasını Kaydet", os.path.join(DEFAULT_EXPORT_DIR, default_name), "WAV Ses Dosyaları (*.wav)"
        )

        if save_path:
            try:
                self.converted_audio.export(save_path, format="wav")
                self.status_label.setText(f"Dosya başarıyla kaydedildi:\n{os.path.basename(save_path)}")
                QMessageBox.information(self, "Başarılı", f"Dosya başarıyla '{save_path}' konumuna kaydedildi.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya kaydedilirken bir hata oluştu:\n{e}")

    def update_button_states(self, is_converting=False):
        """Updates the active/inactive state of the buttons."""
        if is_converting:
            self.btn_file.setEnabled(False)
            self.btn_convert.setEnabled(False)
            self.btn_export.setEnabled(False)
        else:
            self.btn_file.setEnabled(True)
            self.btn_convert.setEnabled(self.input_file_path is not None)
            self.btn_export.setEnabled(self.converted_audio is not None)

    def get_button_style(self):
        """Returns the CSS style for the buttons."""
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 14px;
                font-weight: bold; border: 2px solid #555; border-radius: 8px;
                padding: 5px 15px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
            QPushButton:disabled { color: #777; border-color: #444; }
        """

    def closeEvent(self, event):
        """Ensures the thread stops when the window is closed."""
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
