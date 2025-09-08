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

import sys, os, subprocess, time, cv2, tempfile, signal, platform, json
import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QSplitter, QFileDialog, QMessageBox, QSlider, QStyle, QStyleOptionSlider, QSizePolicy, QProgressDialog, QDialog, QGridLayout, QComboBox, QSpacerItem
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDir, QUrl, QPoint
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen

# QtMultimedia imports for native video playback
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

import traceback
import shutil

# Gerekli ses işleme kütüphaneleri
try:
    import soundfile as sf
    import numpy as np
    import noisereduce as nr
    import scipy.signal as sig
    import librosa
    from pydub import AudioSegment
    from pydub.effects import compress_dynamic_range
except ImportError:
    print("HATA: Gerekli kütüphaneler (soundfile, numpy, noisereduce, scipy, librosa, pydub) bulunamadı.")
    print("Lütfen 'pip install soundfile numpy noisereduce scipy librosa pydub' komutu ile kurun.")
    sys.exit(1)

# --- YENİ EKLENEN FONKSİYON ---
# Bu fonksiyon, programın hem geliştirme ortamında (normal python ile çalışırken)
# hem de PyInstaller ile paketlendiğinde doğru dosya yolunu bulmasını sağlar.
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller, çalışırken geçici bir klasör oluşturur ve yolunu sys._MEIPASS'ta saklar.
        base_path = sys._MEIPASS
    except Exception:
        # Eğer paketlenmemişse, ana dosyanın bulunduğu klasörü temel yol olarak alır.
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
# --- GÜNCELLEME SONU ---


# Video ve ses ayarları
VIDEO_FPS = 20.0 # Hedeflenen FPS (ekran kaydı için)
AUDIO_RATE = 48000 # Örnekleme hızı

# Sabit Dizin Yolları
DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')
SEGMENT_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', '_v&s_')
# --- GÜNCELLEME: SETTINGS_FILE yolu resource_path ile dinamik hale getirildi ---
SETTINGS_FILE = resource_path("filter_settings c33.json") # Ayar dosyası


def load_cpp_library():
    """
    Bu fonksiyon, ana uygulamanın (Kavram.py) import hatası vermemesi için
    geriye dönük uyumluluk amacıyla eklenmiştir. Yeni sürümde C++ ses
    kütüphanesi kullanılmadığı için bu fonksiyonun bir işlevi yoktur.
    """
    print("Python Uyarısı: load_cpp_library çağrıldı, ancak bu fonksiyon artık işlevsel değil.")
    return True


def get_audio_source():
    """
    Detects the appropriate audio source for recording.
    Prioritizes EasyEffects monitor source if available, otherwise returns 'default'.
    """
    try:
        # Run pactl to list all audio sources
        result = subprocess.run(['pactl', 'list', 'sources'], capture_output=True, text=True, check=True, encoding='utf-8')
        output = result.stdout

        sources = output.strip().split('Source #')
        for source_info in sources:
            if not source_info.strip():
                continue

            # Check for EasyEffects source name directly
            if 'easyeffects_sink.monitor' in source_info:
                for line in source_info.split('\n'):
                    if line.strip().startswith('Name:'):
                        source_name = line.split(':', 1)[1].strip()
                        print(f"Python: EasyEffects ses kaynağı bulundu: {source_name}")
                        return source_name

    except FileNotFoundError:
        print("Python Uyarı: 'pactl' komutu bulunamadı. PulseAudio/PipeWire kurulu olmayabilir. 'default' ses kaynağı kullanılacak.")
    except subprocess.CalledProcessError as e:
        print(f"Python Uyarı: 'pactl' komutu çalıştırılamadı veya hata verdi: {e}. 'default' ses kaynağı kullanılacak.")
    except Exception as e:
        print(f"Python Hata: Ses kaynağı aranırken beklenmedik bir hata oluştu: {e}. 'default' ses kaynağı kullanılacak.")

    # If EasyEffects is not found or an error occurs, return 'default'
    print("Python: EasyEffects kaynağı bulunamadı. Varsayılan ('default') ses kaynağı kullanılacak.")
    return 'default'


class BaseFFmpegRecorder(QThread):
    """FFmpeg tabanlı kayıtçılar için temel sınıf."""
    recording_started = pyqtSignal(str)
    recording_stopped = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ffmpeg_process = None
        self.running = False
        self.ffmpeg_log_file = None

    def stop_process(self):
        """FFmpeg sürecini nazikçe durdurur, ardından zorla sonlandırır."""
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            print(f"{self.__class__.__name__}: FFmpeg sürecine 'q' gönderiliyor...")
            try:
                # 'q' komutunu stdin'e yazarak FFmpeg'in dosyayı düzgünce kapatmasını sağlıyoruz.
                self.ffmpeg_process.stdin.write(b'q\n')
                self.ffmpeg_process.stdin.flush()
                # GÜNCELLEME: Sürecin sonlanması için daha uzun bir bekleme süresi ve daha sağlam kontrol.
                self.ffmpeg_process.communicate(timeout=10)
                print(f"{self.__class__.__name__}: FFmpeg süreci nazikçe sonlandırıldı. Dönüş kodu: {self.ffmpeg_process.returncode}")
            except subprocess.TimeoutExpired:
                print(f"{self.__class__.__name__}: FFmpeg süreci nazikçe sonlanmadı, zorla sonlandırılıyor...")
                # GÜNCELLEME: Platforma özel ve daha güvenilir proses sonlandırma.
                if hasattr(os, 'killpg') and platform.system() == "Linux":
                    try:
                        os.killpg(os.getpgid(self.ffmpeg_process.pid), signal.SIGKILL)
                        print(f"{self.__class__.__name__}: FFmpeg süreç grubu (PGID: {os.getpgid(self.ffmpeg_process.pid)}) zorla sonlandırıldı.")
                    except (ProcessLookupError, AttributeError, PermissionError) as e_kill:
                        print(f"{self.__class__.__name__}: Süreç grubunu sonlandırırken hata: {e_kill}. Geriye dönülüyor...")
                        self.ffmpeg_process.kill()
                else: # Windows ve diğer sistemler için
                    self.ffmpeg_process.kill()

                return_code = self.ffmpeg_process.wait()
                print(f"{self.__class__.__name__}: FFmpeg süreci zorla sonlandırıldı. Dönüş kodu: {return_code}")
            except (IOError, ValueError) as e: # stdin kapalıysa veya başka bir I/O hatası varsa
                print(f"{self.__class__.__name__} Uyarı: FFmpeg durdurulurken 'q' gönderilemedi: {e}")
                if self.ffmpeg_process.poll() is None:
                    self.ffmpeg_process.kill()
                    return_code = self.ffmpeg_process.wait()
                    print(f"{self.__class__.__name__}: Hata sonrası FFmpeg süreci zorla sonlandırıldı. Dönüş kodu: {return_code}")
            finally:
                if self.ffmpeg_process.poll() is not None:
                     print(f"{self.__class__.__name__}: FFmpeg süreci başarıyla sonlandırıldı.")
                else:
                     print(f"{self.__class__.__name__}: FFmpeg süreci hala çalışıyor olabilir, kontrol edin.")
            self.ffmpeg_process = None
        else:
            print(f"{self.__class__.__name__}: FFmpeg süreci zaten çalışmıyor veya başlatılmadı.")

        self.running = False
        print(f"{self.__class__.__name__}: stop_process tamamlandı.")


    def run_command(self, command):
        """Verilen FFmpeg komutunu çalıştırır ve süreci yönetir."""
        try:
            self.ffmpeg_log_file = tempfile.TemporaryFile(mode='w+', encoding='utf-8')

            popen_kwargs = {
                'stdin': subprocess.PIPE,
                'stdout': subprocess.PIPE,
                'stderr': self.ffmpeg_log_file
            }
            if platform.system() == "Linux":
                popen_kwargs['preexec_fn'] = os.setsid

            print(f"{self.__class__.__name__}: FFmpeg komutu başlatılıyor: {' '.join(command)}")
            self.ffmpeg_process = subprocess.Popen(command, **popen_kwargs)
            self.running = True

            # Süreç çalışırken bekle
            self.ffmpeg_process.wait()

            # GÜNCELLEME: Çıkış kodunu daha detaylı kontrol et
            if self.running: # Eğer 'stop_process' tarafından durdurulmadıysa ve kendi kendine sonlandıysa
                if self.ffmpeg_process.returncode != 0 and self.ffmpeg_process.returncode != 255:
                    self.ffmpeg_log_file.seek(0)
                    stderr_output = self.ffmpeg_log_file.read()
                    error_message = f"FFmpeg kaydı beklenmedik bir hata kodu ile sonlandı: {self.ffmpeg_process.returncode}.\nFFmpeg Log:\n{stderr_output}"
                    print(f"{self.__class__.__name__} Hata: {error_message}")
                    self.error_occurred.emit(error_message)
                else:
                    print(f"{self.__class__.__name__}: FFmpeg süreci normal şekilde tamamlandı. Dönüş kodu: {self.ffmpeg_process.returncode}")
            else: # stop_process tarafından durdurulduysa
                print(f"{self.__class__.__name__}: FFmpeg süreci harici olarak durduruldu.")


        except FileNotFoundError:
            error_message = "FFmpeg bulunamadı. Lütfen sisteminizde kurulu olduğundan emin olun (örn: sudo apt install ffmpeg)."
            self.error_occurred.emit(error_message)
        except Exception as e:
            error_message = f"{self.__class__.__name__}: Bir hata oluştu: {e}"
            self.error_occurred.emit(error_message)
            traceback.print_exc()
        finally:
            self.running = False
            if self.ffmpeg_log_file:
                self.ffmpeg_log_file.close()
                self.ffmpeg_log_file = None
            self.recording_stopped.emit(f"{self.__class__.__name__} durduruldu.")


class ScreenRecorder(BaseFFmpegRecorder):
    """Sadece video kaydı yapar (MKV formatında)."""
    def __init__(self, output_dir, fps=VIDEO_FPS, segment_time=60, parent=None):
        super().__init__(parent)
        self.output_dir = output_dir
        self.fps = fps
        self.segment_time = segment_time

    def run(self):
        screen_geometry = QApplication.desktop().screenGeometry()
        timestamp_base = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_pattern = os.path.join(self.output_dir, f"v_segment_{timestamp_base}_%03d.mkv")

        # GÜNCELLEME: Komut, kararlılık ve senkronizasyon için iyileştirildi.
        command = [
            'ffmpeg', '-y',
            '-f', 'x11grab',
            '-vsync', 'cfr',  # Sabit kare hızı senkronizasyonu (zaman kaymasını önler)
            '-s', f'{screen_geometry.width()}x{screen_geometry.height()}',
            '-i', ':0.0',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '25', '-pix_fmt', 'yuv420p',
            '-r', str(self.fps),
            '-map', '0',
            '-f', 'segment',
            '-segment_time', str(self.segment_time),
            '-reset_timestamps', '1', # Her segmentte zaman damgasını sıfırlar (birleştirme için kritik)
            '-segment_format', 'matroska',
            output_pattern
        ]
        self.recording_started.emit("Ekran kaydı başlatıldı (Sadece Video - MKV).")
        self.run_command(command)


class AudioRecorder(BaseFFmpegRecorder):
    """Sadece ses kaydı yapar (WAV formatında)."""
    def __init__(self, output_dir, segment_time=60, parent=None):
        super().__init__(parent)
        self.output_dir = output_dir
        self.segment_time = segment_time

    def run(self):
        audio_source = get_audio_source()
        timestamp_base = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_pattern = os.path.join(self.output_dir, f"s_segment_{timestamp_base}_%03d.wav")

        # GÜNCELLEME: Komut, kararlılık için iyileştirildi.
        command = [
            'ffmpeg', '-y',
            '-f', 'pulse',
            '-i', audio_source,
            '-c:a', 'pcm_s16le', # WAV için standart codec
            '-map', '0',
            '-f', 'segment',
            '-segment_time', str(self.segment_time),
            '-reset_timestamps', '1', # Her segmentte zaman damgasını sıfırlar
            '-segment_format', 'wav',
            output_pattern
        ]
        self.recording_started.emit("Ses kaydı başlatıldı (Sadece Ses - WAV).")
        self.run_command(command)


class CombinedRecorder(BaseFFmpegRecorder):
    """Video ve ses kaydını aynı anda tek dosyada yapar (MKV formatında)."""
    def __init__(self, output_dir, fps=VIDEO_FPS, segment_time=60, parent=None):
        super().__init__(parent)
        self.output_dir = output_dir
        self.fps = fps
        self.segment_time = segment_time

    def run(self):
        screen_geometry = QApplication.desktop().screenGeometry()
        audio_source = get_audio_source()
        timestamp_base = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_pattern = os.path.join(self.output_dir, f"vs_segment_{timestamp_base}_%03d.mkv")

        # GÜNCELLEME: Komut, kararlılık ve senkronizasyon için iyileştirildi.
        command = [
            'ffmpeg', '-y',
            # Video Girişi
            '-f', 'x11grab',
            '-vsync', 'cfr', # Sabit kare hızı senkronizasyonu
            '-s', f'{screen_geometry.width()}x{screen_geometry.height()}',
            '-i', ':0.0',
            # Ses Girişi
            '-f', 'pulse',
            '-i', audio_source,
            # Stream Eşleme
            '-map', '0:v:0', # Video akışı
            '-map', '1:a:0', # Ses akışı
            # Video Codec
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '25', '-pix_fmt', 'yuv420p', '-r', str(self.fps),
            # Ses Codec
            '-c:a', 'aac', '-b:a', '192k',
            # Segmentasyon
            '-f', 'segment',
            '-segment_time', str(self.segment_time),
            '-reset_timestamps', '1', # Her segmentte zaman damgasını sıfırlar
            '-segment_format', 'matroska',
            output_pattern
        ]
        self.recording_started.emit("Birleşik video ve ses kaydı başlatıldı (MKV).")
        self.run_command(command)


# Yeni CameraFeatureWindow sınıfı
class CameraFeatureWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Feature")
        self.setGeometry(200, 200, 400, 150)
        self.layout = QVBoxLayout(self)
        self.message_label = QLabel("Bu fonksiyon geliştirme aşamasındadır.")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.message_label)
        self.setStyleSheet("background-color: #383838; color: white; font-size: 16px;")

# Gelişmiş gürültü filtresi ayarları için diyalog penceresi
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
        # Sütun 1
        self.combo_ai_nr = self.create_filter_combo(0, "AI Noise Reduction", ["Off", "On"])
        self.combo_noise_gate = self.create_filter_combo(1, "Noise Gate", ["Off"] + [f"{i}dB" for i in range(-80, -19, 5)])
        self.combo_hp = self.create_filter_combo(2, "HP Filter", ["Off"] + [f"{i}Hz" for i in range(20, 301, 10)])
        self.combo_lp = self.create_filter_combo(3, "LP Filter", ["Off"] + [f"{i}Hz" for i in range(2000, 20001, 1000)])
        self.combo_gain = self.create_filter_combo(4, "Gain", [f"{i}dB" for i in range(-12, 13, 1)])
        self.combo_reverb = self.create_filter_combo(5, "Reverb Reduction", ["Off", "Low", "Medium", "High", "Very High"])

        # Sütun 2
        self.combo_de_esser = self.create_filter_combo(0, "De-Esser", ["Off", "Low", "Medium", "High"], col_start=2)
        self.combo_de_hum = self.create_filter_combo(1, "De-Hum", ["Off", "Low", "Medium", "High"], col_start=2)
        self.combo_comp_thresh = self.create_filter_combo(2, "Comp. Threshold", ["Off"] + [f"{i}dB" for i in range(-60, 1, 5)], col_start=2)
        self.combo_comp_ratio = self.create_filter_combo(3, "Comp. Ratio", ["1:1", "2:1", "3:1", "4:1", "5:1", "8:1", "10:1"], col_start=2)
        self.combo_comp_attack = self.create_filter_combo(4, "Comp. Attack", [f"{i}ms" for i in [1, 5, 10, 20, 50, 100]], col_start=2)
        self.combo_comp_release = self.create_filter_combo(5, "Comp. Release", [f"{i}ms" for i in [50, 100, 200, 500, 1000]], col_start=2)

        # Sütun 3
        self.combo_eq_gain = self.create_filter_combo(0, "EQ Gain", [f"{i}dB" for i in range(-12, 13, 1)], col_start=4)
        self.combo_eq_freq = self.create_filter_combo(1, "EQ Freq.", [f"{i}Hz" for i in [500, 1000, 1500, 2000, 3000, 4000]], col_start=4)
        self.combo_eq_q = self.create_filter_combo(2, "EQ Q", ["0.5", "1.0", "2.0", "3.0", "5.0", "8.0"], col_start=4)

        # OK Butonu
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
        """Mevcut ayarları ComboBox'lara yükler."""
        self.combo_ai_nr.setCurrentText("On" if self.settings.get('ai_nr_enabled') else "Off")
        self.combo_noise_gate.setCurrentText(f"{int(self.settings.get('noise_gate_threshold_db', -70))}dB" if self.settings.get('noise_gate_threshold_db', -70) > -990 else "Off")
        self.combo_hp.setCurrentText(f"{self.settings.get('hp_cutoff_hz', 150)}Hz" if self.settings.get('hp_cutoff_hz', 150) > 0 else "Off")
        self.combo_lp.setCurrentText(f"{self.settings.get('lp_cutoff_hz', 10000)}Hz" if self.settings.get('lp_cutoff_hz', 10000) > 0 else "Off")
        self.combo_gain.setCurrentText(f"{int(self.settings.get('gain_db', 6))}dB")

        level_map_rev = {0: "Off", 1: "Low", 2: "Medium", 3: "High", 4: "Very High"}
        self.combo_reverb.setCurrentText(level_map_rev.get(self.settings.get('reverb_reduction_level', 0), "Off"))
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
        """ComboBox'lardan güncel değerleri alıp sözlüğe kaydeder."""
        s = {} # Boş bir sözlükle başla
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


# Custom Slider for red playback line
class PlaybackSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.red_line_position = 0
        self.setMinimum(0)
        self.setMaximum(100)
        self.setSingleStep(1)
        self.setPageStep(10)
        self.setTracking(True)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.red_line_position >= 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            opt = QStyleOptionSlider()
            self.initStyleOption(opt)

            groove_rect = self.style().subControlRect(
                QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self
            )

            if self.orientation() == Qt.Horizontal:
                x_pos = groove_rect.left() + (groove_rect.width() * self.red_line_position / 100)
                x_pos = max(groove_rect.left(), min(x_pos, groove_rect.right()))

                y_pos = groove_rect.center().y()
                line_length = 10

                painter.setPen(QPen(QColor(255, 0, 0), 2))
                painter.drawLine(int(x_pos), int(y_pos - line_length / 2), int(x_pos), int(y_pos + line_length / 2))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            groove_rect = self.style().subControlRect(
                QStyle.CC_Slider, opt, QStyle.SC_SliderGroove, self
            )

            if self.orientation() == Qt.Horizontal:
                position = event.pos().x() - groove_rect.left()
                ratio = position / groove_rect.width()
                new_value = self.minimum() + (self.maximum() - self.minimum()) * ratio
                self.setValue(int(new_value))
                self.sliderMoved.emit(int(new_value))
        super().mousePressEvent(event)


class CameraRecorderWindow(QWidget):
    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        self.setWindowTitle("Camera Editor")
        self.resize(900, 600)
        self.setStyleSheet("background-color: #383838; color: white; border: none;")

        self.player = QMediaPlayer(self)
        self.video_widget = QVideoWidget(self)

        self.frame_width = 640
        self.frame_height = 480
        self.fps = VIDEO_FPS

        self.recording = False
        self.recorder_thread = None

        self.record_start_time_segment = None
        self.cumulative_time = 0

        self.windows_active = False
        self.sound_active = False
        self.noise_filter_enabled = False

        # YENİ: Zamanlayıcı ve segment ayarları için değişkenler
        self.segment_duration = 30  # Saniye cinsinden, varsayılan 30sn
        self.timed_record_limit_sec = 0  # Saniye cinsinden, 0 = limitsiz
        self.force_export_state = False # Dışa aktarma zorunlu mu?

        self.timed_record_timer = QTimer(self)
        self.timed_record_timer.setSingleShot(True)
        self.timed_record_timer.timeout.connect(self.auto_stop_recording)

        # YENİ: Açılır menüler için veri haritaları
        self.record_limit_map = {
            "1 dk": 60, "3 dk": 180, "5 dk": 300, "7 dk": 420, "10 dk": 600,
            "11 dk": 660, "13 dk": 780, "17 dk": 1020, "19 dk": 1140, "20 dk": 1200, "30 dk": 1800
        }
        self.segment_duration_map = {
            "20 sn": 20, "30 sn": 30, "45 sn": 45, "1 dk": 60, "1.5 dk": 90, "2 dk": 120, "3 dk": 180
        }

        # Genişletilmiş filtre ayarları için varsayılan sözlük (filtre.py'den)
        self.filter_settings = {
            'ai_nr_enabled': True,
            'noise_gate_threshold_db': -70.0,
            'hp_cutoff_hz': 150,
            'lp_cutoff_hz': 10000,
            'gain_db': 6.0,
            'reverb_reduction_level': 0,
            'de_esser_level': 0,
            'de_hum_level': 0,
            'compressor_threshold_db': 0.0, # 0.0 "Off" anlamına gelir
            'compressor_ratio': 3.0,
            'compressor_attack_ms': 5.0,
            'compressor_release_ms': 150.0,
            'eq_gain_db': 0.0,
            'eq_freq_hz': 1000.0,
            'eq_q': 1.0,
        }
        self.load_filter_settings() # Ayarları dosyadan yükle

        self.camera_feature_window = None

        QDir().mkpath(DEFAULT_BASE_DIR)
        QDir().mkpath(SEGMENT_DIR)

        self.playback_mode = None
        self.playback_filepath = None
        self.audio_player_process = None
        self.playback_start_time = 0
        self.playback_duration_seconds = 0
        self.is_playing = False

        # HATA DÜZELTME: initUI() çağrısı _cleanup_segments() çağrısından önceye alındı.
        self.initUI()

        # GÜNCELLEME: Uygulama başlangıcında eski segmentleri temizle
        self._cleanup_segments()

        self.player.stateChanged.connect(self._handle_player_state_changed)
        self.player.positionChanged.connect(self._handle_player_position_changed)
        self.player.durationChanged.connect(self._handle_player_duration_changed)
        self.player.error.connect(self._handle_player_error)

        self.time_timer = QTimer(self)
        self.time_timer.setInterval(50)
        self.time_timer.timeout.connect(self.updateTimeLabel)

        self.segment_monitor_timer = QTimer(self)
        self.segment_monitor_timer.setInterval(1000)
        self.segment_monitor_timer.timeout.connect(self.updateSegmentCountLabel)
        self.segment_monitor_timer.start()

        self.audio_playback_timer = QTimer(self)
        self.audio_playback_timer.setInterval(50)
        self.audio_playback_timer.timeout.connect(self.updateAudioPlaybackProgress)


    def initUI(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.layout.setSpacing(0)

        self.toolbar_frame = QFrame()
        self.toolbar_frame.setStyleSheet("background-color: #222; border-bottom: 2px solid #555;")
        self.toolbar_frame.setFixedHeight(40)
        self.toolbar_layout = QHBoxLayout(self.toolbar_frame)
        self.toolbar_layout.setContentsMargins(10,5,10,5)

        self.file_button = QPushButton("File")
        self.file_button.setFixedSize(90,30)
        self.file_button.setStyleSheet(self.fileButtonStyle())
        self.file_button.clicked.connect(self.openFileForPlayback)
        self.toolbar_layout.addWidget(self.file_button, alignment=Qt.AlignLeft)

        self.camera_button_feature = QPushButton("Camera")
        self.camera_button_feature.setFixedSize(90,30)
        self.camera_button_feature.setStyleSheet(self.fileButtonStyle())
        self.camera_button_feature.clicked.connect(self.showCameraFeatureWindow)
        self.toolbar_layout.addWidget(self.camera_button_feature, alignment=Qt.AlignLeft)

        self.windows_button = QPushButton("Windows")
        self.windows_button.setFixedSize(90,30)
        self.windows_button.setStyleSheet(self.toggleButtonStyle(self.windows_active))
        self.windows_button.clicked.connect(lambda: self.toggleButtonState("windows"))
        self.toolbar_layout.addWidget(self.windows_button, alignment=Qt.AlignLeft)

        self.sound_button = QPushButton("Sound")
        self.sound_button.setFixedSize(90,30)
        self.sound_button.setStyleSheet(self.toggleButtonStyle(self.sound_active))
        self.sound_button.clicked.connect(lambda: self.toggleButtonState("sound"))
        self.toolbar_layout.addWidget(self.sound_button, alignment=Qt.AlignLeft)

        self.noise_filter_button = QPushButton("|")
        self.noise_filter_button.setToolTip("Noise Reduction (Left Click: On/Off, Right Click: Settings)")
        self.noise_filter_button.setStyleSheet(self.buttonStylePressure(self.noise_filter_enabled))
        self.noise_filter_button.setFixedSize(30, 30)
        self.noise_filter_button.clicked.connect(self.toggleNoiseFilter)
        self.noise_filter_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.noise_filter_button.customContextMenuRequested.connect(self.showAdvancedFilterDialog)
        self.toolbar_layout.addWidget(self.noise_filter_button, alignment=Qt.AlignLeft)

        # YENİ: Ayar menüleri için ayırıcı
        self.toolbar_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Fixed, QSizePolicy.Minimum))

        # YENİ: Kayıt Süresi Sınırlayıcı ComboBox
        self.record_limit_combo = QComboBox()
        self.record_limit_combo.addItems(self.record_limit_map.keys())
        self.record_limit_combo.setCurrentText("5 dk") # Varsayılan
        self.record_limit_combo.setFixedWidth(110)
        self.record_limit_combo.setStyleSheet(self.comboStyle())
        self.record_limit_combo.currentIndexChanged.connect(self.handle_record_limit_changed)
        self.toolbar_layout.addWidget(self.record_limit_combo)
        self.handle_record_limit_changed(self.record_limit_combo.currentIndex()) # Başlangıç değerini ayarla

        # YENİ: Segment Uzunluğu ComboBox
        self.segment_duration_combo = QComboBox()
        self.segment_duration_combo.addItems(self.segment_duration_map.keys())
        self.segment_duration_combo.setCurrentText("30 sn") # Varsayılan
        self.segment_duration_combo.setFixedWidth(110)
        self.segment_duration_combo.setStyleSheet(self.comboStyle())
        self.segment_duration_combo.currentIndexChanged.connect(self.handle_segment_duration_changed)
        self.toolbar_layout.addWidget(self.segment_duration_combo)
        self.handle_segment_duration_changed(self.segment_duration_combo.currentIndex()) # Başlangıç değerini ayarla

        self.main_play_pause_button = QPushButton("Play")
        self.main_play_pause_button.setFixedSize(90,30)
        self.main_play_pause_button.setStyleSheet(self.playButtonStyle())
        self.main_play_pause_button.clicked.connect(self.handleMainPlayPause)
        self.toolbar_layout.addWidget(self.main_play_pause_button, alignment=Qt.AlignLeft)

        self.main_close_playback_button = QPushButton("X")
        self.main_close_playback_button.setFixedSize(30,30)
        self.main_close_playback_button.setStyleSheet(self.fileButtonStyle())
        self.main_close_playback_button.clicked.connect(self.closePlaybackBar)
        self.main_close_playback_button.setEnabled(False)
        self.toolbar_layout.addWidget(self.main_close_playback_button, alignment=Qt.AlignLeft)

        self.toolbar_layout.addStretch()

        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet("color: white; font-size: 14px; margin-right: 10px;")
        self.toolbar_layout.addWidget(self.time_label, alignment=Qt.AlignRight)

        self.segment_count_label = QLabel("Segments: 0")
        self.segment_count_label.setStyleSheet("color: white; font-size: 14px; margin-right: 10px;")
        self.toolbar_layout.addWidget(self.segment_count_label, alignment=Qt.AlignRight)

        self.export_button = QPushButton("Export")
        self.export_button.setFixedSize(90,30)
        self.export_button.setStyleSheet(self.fileButtonStyle())
        self.export_button.clicked.connect(self.exportRecording)
        self.toolbar_layout.addWidget(self.export_button, alignment=Qt.AlignRight)

        self.camera_button = QPushButton("Rec")
        self.camera_button.setFixedSize(90,30)
        self.camera_button.setStyleSheet(self.fileButtonStyle())
        self.camera_button.clicked.connect(self.cameraButtonClicked)
        self.toolbar_layout.addWidget(self.camera_button, alignment=Qt.AlignRight)

        self.layout.addWidget(self.toolbar_frame)

        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: black;")
        self.video_layout = QVBoxLayout(self.video_frame)
        self.video_layout.setContentsMargins(0,0,0,0)

        self.video_widget.setStyleSheet("background-color: black;")
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_layout.addWidget(self.video_widget)
        self.video_widget.hide()

        self.info_label = QLabel("No Video Preview")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #777; font-size: 18px;")
        self.info_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_layout.addWidget(self.info_label)

        self.playback_bar_frame = QFrame()
        self.playback_bar_frame.setStyleSheet("background-color: #222; border-top: 2px solid #555;")
        self.playback_bar_frame.setFixedHeight(60)
        self.playback_bar_layout = QHBoxLayout(self.playback_bar_frame)
        self.playback_bar_layout.setContentsMargins(10, 5, 10, 5)
        self.playback_bar_frame.hide()
        self.playback_bar_frame.setMinimumHeight(0)

        self.playback_time_label = QLabel("00:00")
        self.playback_time_label.setStyleSheet("color: white; font-size: 12px; margin-right: 5px;")
        self.playback_bar_layout.addWidget(self.playback_time_label)

        self.playback_slider = PlaybackSlider(Qt.Horizontal)
        self.playback_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #444;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 0px;
                height: 0px;
                margin: 0px;
                background: transparent;
                border: none;
            }
        """)
        self.playback_slider.sliderMoved.connect(self.seekPlayback)
        self.playback_bar_layout.addWidget(self.playback_slider)

        self.playback_total_time_label = QLabel("00:00")
        self.playback_total_time_label.setStyleSheet("color: white; font-size: 12px; margin-left: 5px;")
        self.playback_bar_layout.addWidget(self.playback_total_time_label)

        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(self.video_frame)
        self.splitter.addWidget(self.playback_bar_frame)
        self.splitter.setStretchFactor(0,1)
        self.splitter.setStretchFactor(1,0)
        self.splitter.setStyleSheet("QSplitter::handle { background-color: #555; }")
        self.layout.addWidget(self.splitter)

        self.splitter.setSizes([self.height() - self.toolbar_frame.height(), 0])

    # YENİ: Açılır menülerin değerlerini işleyen fonksiyonlar
    def handle_record_limit_changed(self, index):
        selected_text = self.record_limit_combo.itemText(index)
        self.timed_record_limit_sec = self.record_limit_map.get(selected_text, 0)
        print(f"Python: Kayıt limiti ayarlandı: {selected_text} ({self.timed_record_limit_sec} saniye)")

    def handle_segment_duration_changed(self, index):
        selected_text = self.segment_duration_combo.itemText(index)
        self.segment_duration = self.segment_duration_map.get(selected_text, 30)
        print(f"Python: Segment süresi ayarlandı: {selected_text} ({self.segment_duration} saniye)")

    def load_filter_settings(self):
        """Filtre ayarlarını JSON dosyasından yükler."""
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings_from_file = json.load(f)
                self.filter_settings.update(settings_from_file)
                print(f"Python: Filtre ayarları {SETTINGS_FILE} dosyasından yüklendi.")
        except FileNotFoundError:
            print(f"Python: Ayar dosyası '{SETTINGS_FILE}' bulunamadı. Varsayılan ayarlar kullanılacak.")
            self.save_filter_settings() # İlk çalıştırmada varsayılan ayarları kaydet
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
        filtre.py'den alınan GÜNCELLENMİŞ ve GELİŞMİŞ mantıkla ses dosyasına filtreler uygular.
        İşlenmiş WAV dosyasının yolunu döndürür.
        """
        try:
            s = self.filter_settings
            output_wav_path = input_wav_path.replace('.wav', '_filtered.wav')

            progress_dialog.setLabelText("Ses verisi okunuyor...")
            QApplication.processEvents()
            data, rate = sf.read(input_wav_path)
            if data.ndim > 1:
                data = data.mean(axis=1) # Mono'ya çevir
            processed = data.copy()
            original_num_samples = len(data)

            # 1. Gain
            gain_db = s.get('gain_db', 0.0)
            if gain_db != 0.0:
                progress_dialog.setLabelText(f"Gain uygulanıyor: {gain_db}dB")
                QApplication.processEvents()
                processed *= 10 ** (gain_db / 20.0)

            # 2. High-Pass Filter
            hp_cutoff = s.get('hp_cutoff_hz', 0)
            if hp_cutoff > 0:
                progress_dialog.setLabelText(f"High-Pass filtresi: {hp_cutoff}Hz")
                QApplication.processEvents()
                nyquist = 0.5 * rate
                normalized_cutoff = hp_cutoff / nyquist
                b, a = sig.butter(4, normalized_cutoff, btype='highpass', analog=False)
                processed = sig.filtfilt(b, a, processed)

            # 3. Low-Pass Filter
            lp_cutoff = s.get('lp_cutoff_hz', 0)
            if lp_cutoff > 0:
                progress_dialog.setLabelText(f"Low-Pass filtresi: {lp_cutoff}Hz")
                QApplication.processEvents()
                nyquist = 0.5 * rate
                normalized_cutoff = lp_cutoff / nyquist
                b, a = sig.butter(4, normalized_cutoff, btype='lowpass', analog=False)
                processed = sig.filtfilt(b, a, processed)

            # 4. Noise Gate
            threshold_db = s.get('noise_gate_threshold_db', -999)
            if threshold_db > -990:
                progress_dialog.setLabelText(f"Noise Gate uygulanıyor: {threshold_db}dB")
                QApplication.processEvents()
                threshold_linear = 10 ** (threshold_db / 20.0)
                processed[np.abs(processed) < threshold_linear] = 0

            # 5. De-Hum
            de_hum_level = s.get('de_hum_level', 0)
            if de_hum_level > 0:
                q_map = {1: 10.0, 2: 30.0, 3: 60.0}
                q_val = q_map.get(de_hum_level, 30.0)
                progress_dialog.setLabelText(f"De-Hum uygulanıyor: Seviye={de_hum_level}")
                QApplication.processEvents()
                for freq in [50, 60]:
                    b, a = sig.iirnotch(freq, q_val, fs=rate)
                    processed = sig.filtfilt(b, a, processed)

            # 6. De-Esser
            de_esser_level = s.get('de_esser_level', 0)
            if de_esser_level > 0:
                gain_map = {1: -3.0, 2: -6.0, 3: -9.0}
                gain_db = gain_map.get(de_esser_level, 0.0)
                progress_dialog.setLabelText(f"De-Esser uygulanıyor: Seviye={de_esser_level}")
                QApplication.processEvents()
                b, a = sig.butter(2, 6000, btype='high', fs=rate, analog=False)
                high_freqs = sig.filtfilt(b, a, processed)
                reduction_factor = 10 ** (gain_db / 20.0)
                processed = processed - high_freqs + (high_freqs * reduction_factor)

            # 7. Reverb Reduction
            reverb_level = s.get('reverb_reduction_level', 0)
            if reverb_level > 0:
                level_map = {1: 0.1, 2: 0.2, 3: 0.3, 4: 0.4}
                strength = level_map.get(reverb_level, 0)
                progress_dialog.setLabelText(f"Reverb Azaltma: Seviye={reverb_level}")
                QApplication.processEvents()
                processed = librosa.effects.preemphasis(processed, coef=0.97 - strength)

            # 8. Compressor
            comp_threshold_db = s.get('compressor_threshold_db', 0.0)
            if comp_threshold_db != 0.0:
                ratio = s.get('compressor_ratio', 1.0)
                attack = s.get('compressor_attack_ms', 5.0)
                release = s.get('compressor_release_ms', 100.0)
                progress_dialog.setLabelText(f"Compressor: {comp_threshold_db}dB, {ratio}:1")
                QApplication.processEvents()

                # pydub float32 yerine int16 ile çalışır
                processed_int16 = (processed * 32767).astype(np.int16)
                audio_segment = AudioSegment(
                    processed_int16.tobytes(),
                    frame_rate=rate,
                    sample_width=processed_int16.dtype.itemsize,
                    channels=1
                )
                compressed_segment = compress_dynamic_range(
                    audio_segment,
                    threshold=comp_threshold_db,
                    ratio=ratio,
                    attack=attack,
                    release=release
                )
                processed = np.array(compressed_segment.get_array_of_samples(), dtype=np.float32) / 32767.0

            # 9. Parametric EQ
            eq_gain_db = s.get('eq_gain_db', 0.0)
            if eq_gain_db != 0.0:
                eq_freq = s.get('eq_freq_hz', 1000.0)
                eq_q = s.get('eq_q', 1.0)
                progress_dialog.setLabelText(f"Parametrik EQ: {eq_gain_db}dB @ {eq_freq}Hz")
                QApplication.processEvents()

                b, a = sig.iirpeak(eq_freq, eq_q, fs=rate)
                g = 10.0 ** (eq_gain_db / 20.0)
                # Kazanç sadece b katsayılarına uygulanır
                b_gained = b * g if eq_gain_db > 0 else b / abs(g)
                processed = sig.lfilter(b_gained, a, processed)


            # 10. AI Noise Reduction (En sonda uygulanır)
            if s.get('ai_nr_enabled', False):
                progress_dialog.setLabelText("AI Gürültü Azaltma uygulanıyor...")
                QApplication.processEvents()
                processed = nr.reduce_noise(y=processed, sr=rate, prop_decrease=1.0, freq_mask_smooth_hz=500, time_mask_smooth_ms=100)

            # Orijinal uzunluğu koru
            if len(processed) < original_num_samples:
                padding = np.zeros(original_num_samples - len(processed))
                processed = np.concatenate((processed, padding))
            elif len(processed) > original_num_samples:
                processed = processed[:original_num_samples]

            progress_dialog.setLabelText("İşlenmiş ses kaydediliyor...")
            QApplication.processEvents()
            sf.write(output_wav_path, processed, rate)
            return output_wav_path

        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"Python ses filtreleme hatası: {e}")


    def showAdvancedFilterDialog(self, pos):
        """Filtre butonu sağ tıklandığında çağrılır."""
        dialog = AdvancedFilterDialog(initial_settings=self.filter_settings, parent=self)
        global_pos = self.noise_filter_button.mapToGlobal(QPoint(0, self.noise_filter_button.height()))
        dialog.move(global_pos)

        if dialog.exec_():
            self.filter_settings = dialog.getSettings()
            self.save_filter_settings() # Ayarları kaydet
            print(f"Python: Gürültü filtresi ayarları güncellendi ve kaydedildi.")

    def fileButtonStyle(self) -> str:
        return """
            QPushButton {
                background-color: black;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 6px;
                padding: 3px;
            }
            QPushButton:hover {
                background-color: #222;
            }
            QPushButton:pressed {
                background-color: #444;
            }
        """

    def playButtonStyle(self) -> str:
        return """
            QPushButton {
                background-color: black;
                color: white;
                border: 2px solid #555;
                border-radius: 6px;
                padding: 3px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #222;
            }
            QPushButton:pressed {
                background-color: #444;
            }
        """

    def toggleButtonStyle(self, is_active: bool) -> str:
        if is_active:
            return """
                QPushButton {
                    background-color: #555;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    border: 2px solid #555;
                    border-radius: 6px;
                    padding: 3px;
                }
                QPushButton:hover {
                    background-color: #666;
                }
                QPushButton:pressed {
                    background-color: #777;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: black;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    border: 2px solid #555;
                    border-radius: 6px;
                    padding: 3px;
                }
                QPushButton:hover {
                    background-color: #222;
                }
                QPushButton:pressed {
                    background-color: #444;
                }
            """

    def buttonStylePressure(self, is_active: bool) -> str:
        """Gürültü filtresi butonu için stil döndürür."""
        if is_active:
            return """
                QPushButton {
                    background-color: #555; /* Gray */
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    border: 2px solid #555;
                    border-radius: 6px;
                    padding: 3px;
                }
                QPushButton:hover { background-color: #666; }
                QPushButton:pressed { background-color: #777; }
            """
        else:
            return """
                QPushButton {
                    background-color: black;
                    color: white;
                    font-size: 14px;
                    font-weight: bold;
                    border: 2px solid #555;
                    border-radius: 6px;
                    padding: 3px;
                }
                QPushButton:hover { background-color: #222; }
                QPushButton:pressed { background-color: #444; }
            """

    def comboStyle(self) -> str:
        # sound_GUI.py'dan ilham alan yeni stil
        return """
            QComboBox {
                background-color: black;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 6px;
                padding: 3px;
                padding-left: 10px;
            }
            QComboBox:hover {
                background-color: #222;
            }
            QComboBox::drop-down {
                border: 0px;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTcgMTBMMTIgMTVMMTcgMTAiIHN0cm9rZT0iI2VlZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lSm9pbj0icm91bmQiLz4KPC9zdmc+);
                width: 16px;
                height: 16px;
            }
            QComboBox QAbstractItemView {
                background-color: #282828;
                border: 1px solid #555;
                selection-background-color: #444;
                color: white;
            }
        """

    def disabledButtonStyle(self) -> str:
        return """
            QPushButton {
                background-color: #333;
                color: #777;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #444;
                border-radius: 6px;
                padding: 3px;
            }
        """

    def toggleNoiseFilter(self):
        """Gürültü filtresi durumunu değiştirir ve butonun stilini günceller."""
        self.noise_filter_enabled = not self.noise_filter_enabled
        self.noise_filter_button.setStyleSheet(self.buttonStylePressure(self.noise_filter_enabled))
        print(f"Python: Gürültü filtresi {'etkin' if self.noise_filter_enabled else 'devre dışı'}.")

    def toggleButtonState(self, button_name: str):
        if self.recording:
            QMessageBox.information(self, "Mod Değiştirilemez", "Kayıt devam ederken kayıt modları değiştirilemez. Lütfen önce kaydı duraklatın.")
            print("Python: Kayıt devam ederken mod değiştirme engellendi.")
            return

        if button_name == "windows":
            self.windows_active = not self.windows_active
        elif button_name == "sound":
            self.sound_active = not self.sound_active

        self.windows_button.setStyleSheet(self.toggleButtonStyle(self.windows_active))
        self.sound_button.setStyleSheet(self.toggleButtonStyle(self.sound_active))

        print(f"Windows Aktif: {self.windows_active}, Ses Aktif: {self.sound_active}")
        self.updateMainPlayPauseButtonState()

    def _start_recorder(self):
        """Seçilen modlara göre uygun kayıt iş parçacığını başlatır."""
        recorder_class = None
        # GÜNCELLEME: segment_time parametresi artık ayarlanabilir
        recorder_args = {'output_dir': SEGMENT_DIR, 'segment_time': self.segment_duration}
        info_text = ""

        if self.windows_active and self.sound_active:
            recorder_class = CombinedRecorder
            recorder_args.update({'fps': VIDEO_FPS})
            info_text = "Birleşik Ekran (MKV) ve Ses Kaydı Aktif"
        elif self.windows_active:
            recorder_class = ScreenRecorder
            recorder_args['fps'] = VIDEO_FPS
            info_text = "Ekran Kaydı Aktif (MKV)"
        elif self.sound_active:
            recorder_class = AudioRecorder
            info_text = "Ses Kaydı Aktif (WAV)"

        if recorder_class:
            self.recorder_thread = recorder_class(**recorder_args)
            self.recorder_thread.recording_started.connect(lambda msg: print(f"Recorder: {msg}"))
            self.recorder_thread.error_occurred.connect(self._handle_recorder_error)
            self.recorder_thread.start()
            self.info_label.setText(info_text)
        else:
            self.info_label.setText("Kayıt modu seçilmedi.")

        self.info_label.show()
        self.video_widget.hide()

    # GÜNCELLEME: Kaydedici hatalarını yakalamak için yeni bir metod
    def _handle_recorder_error(self, msg):
        QMessageBox.critical(self, "Kaydedici Hatası", msg)
        # Hata durumunda kaydı güvenli bir şekilde durdur
        self._stop_full_recording_session(cleanup=False) # Hata sonrası segmentleri silme, inceleme için kalsın

    def _pause_recording_session(self):
        """Kayıt oturumunu duraklatır."""
        print("Python: Kayıt oturumu duraklatılıyor...")
        self.timed_record_timer.stop() # Zamanlayıcıyı durdur

        if self.recorder_thread and self.recorder_thread.isRunning():
            self.recorder_thread.stop_process()
            self.recorder_thread.wait() # Thread'in tamamen bittiğinden emin ol
            self.recorder_thread = None
            print("Python: Kayıt süreci duraklatıldı.")

        if self.record_start_time_segment:
            self.cumulative_time += (time.time() - self.record_start_time_segment)
        self.time_timer.stop()
        self.recording = False

        # YENİ: Duraklatıldığında dışa aktarmayı zorunlu kıl
        if self._has_segments():
            self.force_export_state = True
            print("Python: Dışa aktarma zorunlu durumu aktif.")

        self.updateMainPlayPauseButtonState()
        self.info_label.setText("Kayıt Duraklatıldı - Dışa Aktarma Bekleniyor")
        print("Python: Kayıt oturumu duraklatma tamamlandı.")

    # GÜNCELLEME: Bu metod artık segmentleri temizleme seçeneği sunuyor.
    def _stop_full_recording_session(self, cleanup=True):
        """Tüm kayıt oturumunu tamamen durdurur ve isteğe bağlı olarak segmentleri temizler."""
        print("Python: Tüm kayıt oturumu tamamen durduruluyor...")
        self.timed_record_timer.stop()

        if self.recorder_thread and self.recorder_thread.isRunning():
            self.recorder_thread.stop_process()
            self.recorder_thread.wait()
            self.recorder_thread = None
            print("Python: Kayıt süreci sonlandırıldı.")

        self.time_timer.stop()
        self.recording = False
        self.updateMainPlayPauseButtonState()
        self.info_label.setText("Video Önizlemesi Yok")

        if cleanup:
            self._cleanup_segments()
            self.cumulative_time = 0
            self.force_export_state = False
            self.updateTimeLabel()

        print("Python: Tüm kayıt oturumu durdurma tamamlandı.")

    def handleMainPlayPause(self):
        """Tek Play/Pause butonunun işlevini yönetir."""
        if self.playback_mode:
            self.togglePlayback()
        else:
            self.toggleRecording()

    def toggleRecording(self):
        """Kayıt başlatma/durdurma/duraklatma işlemini yönetir."""
        if self.playback_mode:
            QMessageBox.information(self, "Kayıt Engellendi", "Bir dosya oynatılırken kayıt başlatılamaz. Lütfen önce oynatmayı durdurun.")
            return

        # YENİ: Dışa aktarma zorunluysa kaydı engelle
        if self.force_export_state:
            QMessageBox.warning(self, "Dışa Aktarma Gerekli", "Yeni bir kayda başlamadan önce mevcut kaydı 'Export' butonu ile dışa aktarmanız gerekmektedir.")
            return

        if not self.windows_active and not self.sound_active:
            QMessageBox.information(self, "Kayıt Başlatılamadı", "Kayıt başlatmak için 'Sound' veya 'Windows' butonunu aktif hale getirmelisiniz.")
            return

        if not self.recording:
            # GÜNCELLEME: Yeni bir kayda başlarken eski segmentleri temizle
            self._cleanup_segments()
            self.cumulative_time = 0
            self.updateTimeLabel()

            self.record_start_time_segment = time.time()
            self._start_recorder()
            self.time_timer.start()
            self.recording = True

            # YENİ: Zamanlayıcıyı başlat
            if self.timed_record_limit_sec > 0:
                self.timed_record_timer.start(self.timed_record_limit_sec * 1000)
                print(f"Python: Kayıt zamanlayıcı {self.timed_record_limit_sec} saniyeye ayarlandı.")
        else:
            self._pause_recording_session()
            # YENİ: Duraklatma sonrası bildirim
            if self.force_export_state:
                QMessageBox.information(self, "Kayıt Duraklatıldı", "Kayıt duraklatıldı. Devam etmek için 'Export' ile dosyayı kaydedin veya uygulamayı kapatarak kaydı silin.")


        self.updateMainPlayPauseButtonState()

    # YENİ: Zamanlayıcı dolduğunda kaydı durduran fonksiyon
    def auto_stop_recording(self):
        print("Python: Kayıt zaman limiti doldu. Kayıt durduruluyor...")
        if self.recording:
            self._pause_recording_session()
            QMessageBox.information(self, "Süre Doldu", f"Belirttiğiniz {self.record_limit_combo.currentText()} süre doldu. Kayıt durduruldu.\nLütfen 'Export' butonu ile dosyayı kaydedin.")

    def updateTimeLabel(self):
        """Zaman etiketini sadece saat:dakika:saniye olarak günceller."""
        if self.recording and self.record_start_time_segment:
            elapsed = time.time() - self.record_start_time_segment
            total = self.cumulative_time + elapsed
        else:
            total = self.cumulative_time

        hours = int(total // 3600)
        minutes = int((total % 3600) // 60)
        seconds = int(total % 60)
        self.time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def updateSegmentCountLabel(self):
        """Segment sayısını günceller."""
        self.segment_count_label.setText(f"Segments: {len(self._get_segment_files())}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F:
            self.toggleFullscreen()
        elif event.key() == Qt.Key_B:
            self.handleMainPlayPause()
        else:
            super().keyPressEvent(event)

    def exportRecording(self):
        """Kaydedilen segmentleri birleştirir ve gerekirse son dosyayı filtreleyerek dışa aktarır."""
        if self.recording:
            QMessageBox.warning(self, "Dışa Aktarılamadı", "Dışa aktarmadan önce kaydı duraklatmalısınız.")
            return

        if self.playback_mode:
            QMessageBox.information(self, "Dışa Aktarma Engellendi", "Bir dosya oynatılırken dışa aktarma yapılamaz.")
            return

        # GÜNCELLEME: Dışa aktarma öncesi kaydı durdur ama segmentleri silme.
        # Bu satır, _pause_recording_session'ın zaten force_export_state'i yönetmesi nedeniyle gereksiz olabilir,
        # ancak her ihtimale karşı burada bırakmak güvenlidir.
        if self.recorder_thread and self.recorder_thread.isRunning():
             self._stop_full_recording_session(cleanup=False)

        all_segments = self._get_segment_files(full_path=True)
        if not all_segments:
            QMessageBox.information(self, "Dışa Aktarılamadı", "Dışa aktarılacak bir kayıt bulunamadı.")
            return

        has_video = any(f.endswith('.mkv') for f in all_segments)
        has_audio = any(f.endswith(('.mkv', '.wav')) for f in all_segments)
        default_ext = ".mkv" if has_video else ".wav"
        file_filter = "MKV Video Dosyası (*.mkv);;WAV Ses Dosyası (*.wav);;Tüm Dosyalar (*)"

        output_file_user_selected, _ = QFileDialog.getSaveFileName(self, "Kaydı Dışa Aktar", DEFAULT_BASE_DIR, file_filter)
        if not output_file_user_selected:
            return

        if not output_file_user_selected.lower().endswith(default_ext):
            output_file_user_selected += default_ext

        progress = QProgressDialog("Dışa aktarılıyor...", "İptal", 0, 100, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("İşleniyor")
        progress.show()

        list_file_path = None
        temp_merged_file = None
        temp_audio_file = None
        temp_filtered_audio_file = None
        temp_final_file = None

        try:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                temp_merged_file = f.name + default_ext

            # Adım 1: Segmentleri birleştir
            progress.setLabelText("Segmentler birleştiriliyor...")
            progress.setValue(10)
            QApplication.processEvents()

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as list_file:
                list_file_path = list_file.name
                for segment in sorted(all_segments, key=os.path.getmtime):
                    list_file.write(f"file '{os.path.abspath(segment)}'\n")

            merge_command = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_file_path, '-c', 'copy', temp_merged_file]
            merge_process = subprocess.run(merge_command, capture_output=True, text=True, encoding='utf-8')
            if merge_process.returncode != 0:
                raise RuntimeError(f"FFmpeg birleştirme hatası:\n{merge_process.stderr}")

            # Adım 2: Gerekirse filtrele (Yeni Python Tabanlı Yöntem)
            if self.noise_filter_enabled and has_audio:
                progress.setLabelText("Ses kanalı ayıklanıyor...")
                progress.setValue(30)
                QApplication.processEvents()

                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                    temp_audio_file = f.name

                extract_cmd = ['ffmpeg', '-y', '-i', temp_merged_file, '-vn', '-acodec', 'pcm_s16le', '-ar', str(AUDIO_RATE), '-ac', '1', temp_audio_file]
                extract_process = subprocess.run(extract_cmd, capture_output=True, text=True, encoding='utf-8')
                if extract_process.returncode != 0:
                    raise RuntimeError(f"FFmpeg ses ayıklama hatası:\n{extract_process.stderr}")

                progress.setValue(50)
                # Python ile ses filtresi uygula
                temp_filtered_audio_file = self._apply_python_audio_filter(temp_audio_file, progress)

                progress.setLabelText("Filtrelenmiş ses birleştiriliyor...")
                progress.setValue(80)
                QApplication.processEvents()

                with tempfile.NamedTemporaryFile(delete=False) as f:
                    temp_final_file = f.name + default_ext

                if has_video:
                    # Video ve filtrelenmiş sesi birleştir
                    recombine_cmd = ['ffmpeg', '-y', '-i', temp_merged_file, '-i', temp_filtered_audio_file, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-map', '0:v:0', '-map', '1:a:0', '-shortest', temp_final_file]
                else:
                    # Sadece filtrelenmiş sesi dönüştür
                    recombine_cmd = ['ffmpeg', '-y', '-i', temp_filtered_audio_file, temp_final_file]

                recombine_process = subprocess.run(recombine_cmd, capture_output=True, text=True, encoding='utf-8')
                if recombine_process.returncode != 0:
                    raise RuntimeError(f"FFmpeg yeniden birleştirme hatası:\n{recombine_process.stderr}")

                shutil.copy(temp_final_file, output_file_user_selected)

            else:
                # Filtreleme yoksa, birleştirilmiş dosyayı direkt kopyala
                shutil.copy(temp_merged_file, output_file_user_selected)

            progress.setValue(100)
            QMessageBox.information(self, "Başarılı", f"Dosya başarıyla dışa aktarıldı:\n{output_file_user_selected}")

            # YENİ: Başarılı dışa aktarma sonrası durumu sıfırla
            self.force_export_state = False
            self.cumulative_time = 0
            self.updateTimeLabel()
            self.info_label.setText("Video Önizlemesi Yok")
            self._cleanup_segments()
            self.updateMainPlayPauseButtonState()


        except InterruptedError as e:
            QMessageBox.warning(self, "İptal Edildi", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Dışa Aktarma Hatası", f"Beklenmedik bir hata oluştu: {e}")
            traceback.print_exc()
        finally:
            # Tüm geçici dosyaları temizle
            for f in [list_file_path, temp_merged_file, temp_audio_file, temp_filtered_audio_file, temp_final_file]:
                if f and os.path.exists(f):
                    try: os.remove(f)
                    except Exception as e_clean: print(f"Geçici dosya silinemedi {f}: {e_clean}")

            if 'progress' in locals() and progress:
                progress.close()

    def _has_segments(self):
        """Segment dizininde kayıt dosyası olup olmadığını kontrol eder."""
        return len(self._get_segment_files()) > 0

    def _get_segment_files(self, full_path=False):
        """Segment dizinindeki tüm kayıt dosyalarını listeler."""
        segment_files = []
        if not os.path.exists(SEGMENT_DIR):
            return segment_files
        try:
            for filename in os.listdir(SEGMENT_DIR):
                if filename.startswith(('v_segment_', 's_segment_', 'vs_segment_')):
                    file_path = os.path.join(SEGMENT_DIR, filename)
                    segment_files.append(file_path if full_path else filename)
        except Exception as e:
            print(f"Python Hata: Segment dosyaları okunurken hata: {e}")
        return segment_files

    # GÜNCELLEME: Segmentleri güvenli bir şekilde temizlemek için yeni metod
    def _cleanup_segments(self):
        """Geçici segment klasöründeki tüm kayıt dosyalarını siler."""
        print("Python: Segmentler temizleniyor...")
        for file_to_remove in self._get_segment_files(full_path=True):
            try:
                os.remove(file_to_remove)
            except Exception as e:
                print(f"Python Hata: Segment dosyası {file_to_remove} silinirken hata: {e}")

        print("Python: Segmentler başarıyla temizlendi.")
        self.updateSegmentCountLabel()

    def cameraButtonClicked(self):
        main_window = self.window()
        if hasattr(main_window, 'showSwitcher'):
            main_window.showSwitcher()
        print("Python: Rec butonu tıklandı.")

    def showCameraFeatureWindow(self):
        if self.camera_feature_window is None:
            self.camera_feature_window = CameraFeatureWindow()
        self.camera_feature_window.show()
        print("Python: Camera özelliği penceresi açıldı.")

    def openFileForPlayback(self):
        if self.recording:
            QMessageBox.warning(self, "Playback Engellendi", "Kayıt devam ederken dosya oynatılamaz.")
            return

        self._stop_full_recording_session()

        file_path, _ = QFileDialog.getOpenFileName(self, "Dosya Seç", DEFAULT_BASE_DIR, "Video Dosyaları (*.rec *.mp4 *.mkv);;Ses Dosyaları (*.wav);;Tüm Dosyalar (*)")
        if not file_path:
            return

        self.closePlaybackBar()

        self.playback_filepath = file_path
        ext = os.path.splitext(file_path)[1].lower()

        if ext in [".rec", ".mp4", ".mkv"]:
            self.startVideoPlayback(file_path)
        elif ext == ".wav":
            self.startAudioPlayback(file_path)
        else:
            QMessageBox.warning(self, "Desteklenmeyen Dosya", "Lütfen .rec, .mp4, .mkv veya .wav dosyası seçin.")
            self.playback_filepath = None
            return

        self.playback_bar_frame.show()
        total_height = self.height() - self.toolbar_frame.height()
        playback_bar_height = self.playback_bar_frame.height()
        min_video_height = 100

        available_video_height = total_height - playback_bar_height

        if available_video_height < min_video_height:
            playback_bar_height = max(0, total_height - min_video_height)
            available_video_height = total_height - playback_bar_height

        self.splitter.setSizes([available_video_height, playback_bar_height])

        self.is_playing = True
        self.updateMainPlayPauseButtonState()
        self.main_play_pause_button.setEnabled(True)
        self.main_close_playback_button.setEnabled(True)
        if self.playback_mode == "audio":
            self.audio_playback_timer.start()
        self.disableRecordingButtons(True)

    def load_file(self, file_path):
        print(f"Python: CameraRecorderWindow.load_file çağrıldı. Dosya yolu: {file_path}")
        if not os.path.exists(file_path):
            QMessageBox.critical(self, "Dosya Bulunamadı", f"Belirtilen dosya bulunamadı: {file_path}")
            return

        self._stop_full_recording_session()
        self.closePlaybackBar()

        self.playback_filepath = file_path
        ext = os.path.splitext(file_path)[1].lower()

        if ext in [".rec", ".mp4", ".mkv"]:
            self.startVideoPlayback(file_path)
        elif ext == ".wav":
            self.startAudioPlayback(file_path)
        else:
            QMessageBox.warning(self, "Desteklenmeyen Dosya", "Lütfen .rec, .mp4, .mkv veya .wav dosyası seçin.")
            self.playback_filepath = None
            return

        self.playback_bar_frame.show()
        total_height = self.height() - self.toolbar_frame.height()
        playback_bar_height = self.playback_bar_frame.height()
        min_video_height = 100
        available_video_height = total_height - playback_bar_height
        if available_video_height < min_video_height:
            playback_bar_height = max(0, total_height - min_video_height)
            available_video_height = total_height - playback_bar_height
        self.splitter.setSizes([available_video_height, playback_bar_height])

        self.is_playing = True
        self.updateMainPlayPauseButtonState()
        self.main_play_pause_button.setEnabled(True)
        self.main_close_playback_button.setEnabled(True)
        if self.playback_mode == "audio":
            self.audio_playback_timer.start()
        self.disableRecordingButtons(True)


    def togglePlayback(self):
        if not self.playback_mode or not self.playback_filepath:
            return

        if self.is_playing:
            self.is_playing = False
            self.updateMainPlayPauseButtonState()
            if self.playback_mode == "video":
                self.player.pause()
            elif self.playback_mode == "audio" and self.audio_player_process:
                if self.audio_player_process.poll() is None:
                    self.audio_player_process.terminate()
                    self.audio_player_process.wait()
                self.audio_player_process = None
                self.audio_playback_timer.stop()
            print("Python: Oynatma duraklatıldı.")
        else:
            self.is_playing = True
            self.updateMainPlayPauseButtonState()
            if self.playback_mode == "video":
                self.player.play()
            elif self.playback_mode == "audio" and self.playback_filepath:
                current_time = self.playback_duration_seconds * (self.playback_slider.value() / 100.0)
                command = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', '-ss', str(current_time), self.playback_filepath]
                try:
                    self.audio_player_process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self.playback_start_time = time.time() - current_time
                except Exception as e:
                    QMessageBox.critical(self, "Ses Hatası", f"Ses oynatılırken hata oluştu: {e}")
                    self.closePlaybackBar()
                self.audio_playback_timer.start()
            print("Python: Oynatma devam ediyor.")


    def startVideoPlayback(self, filepath):
        self.playback_mode = "video"
        self.player.setVideoOutput(self.video_widget)
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(filepath)))

        if self.player.mediaStatus() == QMediaPlayer.NoMedia:
            QMessageBox.critical(self, "Video Hatası", f"Video dosyası yüklenemedi: {filepath}")
            self.closePlaybackBar()
            return

        self.info_label.hide()
        self.video_widget.show()

        self.playback_slider.setValue(0)
        self.playback_slider.red_line_position = 0
        self.playback_slider.update()
        self.playback_time_label.setText("00:00")
        self.playback_total_time_label.setText("00:00")
        print(f"Python: Video oynatılıyor: {filepath}")
        self.player.play()

    def startAudioPlayback(self, filepath):
        self.playback_mode = "audio"
        self.player.setVideoOutput(None)
        self.video_widget.hide()

        try:
            duration_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', filepath]
            duration_process = subprocess.run(duration_cmd, capture_output=True, text=True, check=True)
            self.playback_duration_seconds = float(duration_process.stdout.strip())
        except Exception as e:
            QMessageBox.critical(self, "Ses Hatası", f"Ses dosyası süresi alınamadı: {e}")
            self.closePlaybackBar()
            return

        command = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', filepath]
        try:
            self.audio_player_process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.playback_start_time = time.time()
            self.info_label.setText(f"Ses Kaydı Oynatılıyor: {os.path.basename(filepath)}")
            self.info_label.show()
            self.playback_slider.setValue(0)
            self.playback_slider.red_line_position = 0
            self.playback_slider.update()
            self.playback_time_label.setText("00:00")
            self.playback_total_time_label.setText(self.formatTime(self.playback_duration_seconds))
            print(f"Python: Ses oynatılıyor: {filepath}")
            self.audio_playback_timer.start()
        except FileNotFoundError:
            QMessageBox.critical(self, "Hata", "ffplay bulunamadı. Lütfen sisteminizde kurulu olduğundan emin olun.")
            self.closePlaybackBar()
        except Exception as e:
            QMessageBox.critical(self, "Ses Hatası", f"Ses oynatılırken hata oluştu: {e}")
            self.closePlaybackBar()

    def _handle_player_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.is_playing = True
            self.updateMainPlayPauseButtonState()
        elif state == QMediaPlayer.PausedState:
            self.is_playing = False
            self.updateMainPlayPauseButtonState()
        elif state == QMediaPlayer.StoppedState:
            self.is_playing = False
            self.updateMainPlayPauseButtonState()
            self.playback_slider.setValue(100)
            self.playback_slider.red_line_position = 100
            self.playback_slider.update()
            if self.playback_duration_seconds > 0:
                self.playback_time_label.setText(self.formatTime(self.playback_duration_seconds))
            self.closePlaybackBar()
            print("Python: Video oynatma tamamlandı (StoppedState).")

    def _handle_player_position_changed(self, position_ms):
        if self.playback_mode == "video" and self.player.duration() > 0:
            current_pos_seconds = position_ms / 1000.0
            progress_percent = (position_ms / self.player.duration()) * 100
            self.playback_slider.setValue(int(progress_percent))
            self.playback_slider.red_line_position = int(progress_percent)
            self.playback_slider.update()
            self.playback_time_label.setText(self.formatTime(current_pos_seconds))

    def _handle_player_duration_changed(self, duration_ms):
        if duration_ms > 0:
            self.playback_duration_seconds = duration_ms / 1000.0
            self.playback_total_time_label.setText(self.formatTime(self.playback_duration_seconds))

    def _handle_player_error(self, error):
        error_string = self.player.errorString()
        print(f"QMediaPlayer Error: {error_string} (Code: {error})")
        QMessageBox.critical(self, "Playback Error", f"Medya oynatılırken bir hata oluştu: {error_string}")
        self.closePlaybackBar()

    def updateAudioPlaybackProgress(self):
        if not self.is_playing:
            return

        if self.playback_mode == "audio" and self.audio_player_process:
            if self.audio_player_process.poll() is None:
                elapsed_time = time.time() - self.playback_start_time
                if self.playback_duration_seconds > 0:
                    progress_percent = (elapsed_time / self.playback_duration_seconds) * 100
                    self.playback_slider.setValue(int(progress_percent))
                    self.playback_slider.red_line_position = int(progress_percent)
                    self.playback_slider.update()
                    self.playback_time_label.setText(self.formatTime(elapsed_time))
            else:
                self.playback_slider.setValue(100)
                self.playback_slider.red_line_position = 100
                self.playback_slider.update()
                if self.playback_duration_seconds > 0:
                    self.playback_time_label.setText(self.formatTime(self.playback_duration_seconds))
                self.is_playing = False
                self.updateMainPlayPauseButtonState()
                self.closePlaybackBar()
                print("Python: Ses oynatma tamamlandı.")


    def seekPlayback(self, value):
        if self.playback_mode == "video" and self.player.mediaStatus() != QMediaPlayer.NoMedia:
            target_position_ms = int(self.player.duration() * (value / 100.0))
            self.player.setPosition(target_position_ms)
            self.playback_slider.red_line_position = value
            self.playback_slider.update()
            print(f"Python: Video seek to {self.formatTime(target_position_ms / 1000.0)}")

        elif self.playback_mode == "audio" and self.playback_filepath:
            if self.audio_player_process and self.audio_player_process.poll() is None:
                self.audio_player_process.terminate()
                self.audio_player_process.wait()

            seek_time_seconds = self.playback_duration_seconds * (value / 100.0)
            command = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', '-ss', str(seek_time_seconds), self.playback_filepath]
            try:
                self.is_playing = True
                self.updateMainPlayPauseButtonState()
                self.audio_player_process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.playback_start_time = time.time() - seek_time_seconds
                self.playback_slider.red_line_position = value
                self.playback_slider.update()
                self.audio_playback_timer.start()
            except Exception as e:
                print(f"Python Hata: Ses oynatılırken seek hatası: {e}")
                QMessageBox.critical(self, "Ses Hatası", f"Ses oynatılırken seek hatası: {e}")
                self.is_playing = False
                self.updateMainPlayPauseButtonState()


    def closePlaybackBar(self):
        if self.playback_mode == "video":
            self.player.stop()
            self.player.setMedia(QMediaContent())
            self.video_widget.hide()
            self.info_label.setText("Video Önizlemesi Yok")
            self.info_label.show()
            print("Python: Video oynatıcı durduruldu.")
        elif self.playback_mode == "audio" and self.audio_player_process:
            if self.audio_player_process.poll() is None:
                self.audio_player_process.terminate()
                self.audio_player_process.wait()
            self.audio_player_process = None
            self.audio_playback_timer.stop()
            self.info_label.setText("Video Önizlemesi Yok")
            self.info_label.show()
            print("Python: Ses oynatıcı durduruldu.")

        self.playback_bar_frame.hide()
        self.splitter.setSizes([self.height() - self.toolbar_frame.height(), 0])

        self.playback_mode = None
        self.playback_filepath = None
        self.is_playing = False
        self.playback_slider.setValue(0)
        self.playback_slider.red_line_position = 0
        self.playback_slider.update()
        self.playback_time_label.setText("00:00")
        self.playback_total_time_label.setText("00:00")
        self.disableRecordingButtons(False)
        self.main_play_pause_button.setEnabled(True)
        self.main_close_playback_button.setEnabled(False)
        self.updateMainPlayPauseButtonState()


    def disableRecordingButtons(self, disable: bool):
        is_disabled = disable or self.force_export_state

        self.windows_button.setEnabled(not is_disabled)
        self.sound_button.setEnabled(not is_disabled)
        # self.camera_button.setEnabled(not is_disabled) # REC BUTONU ARTIK DEVRE DIŞI BIRAKILMIYOR
        self.file_button.setEnabled(not is_disabled)
        self.record_limit_combo.setEnabled(not is_disabled)
        self.segment_duration_combo.setEnabled(not is_disabled)

        # Export butonu sadece dışa aktarma zorunluysa veya normal duraklatma durumunda aktif olmalı
        self.export_button.setEnabled(self.force_export_state or self._has_segments())


        self.windows_button.setStyleSheet(self.toggleButtonStyle(self.windows_active) if not is_disabled else self.disabledButtonStyle())
        self.sound_button.setStyleSheet(self.toggleButtonStyle(self.sound_active) if not is_disabled else self.disabledButtonStyle())
        # self.camera_button.setStyleSheet(self.fileButtonStyle() if not is_disabled else self.disabledButtonStyle()) # REC BUTONU ARTIK DEVRE DIŞI BIRAKILMIYOR
        self.file_button.setStyleSheet(self.fileButtonStyle() if not is_disabled else self.disabledButtonStyle())
        self.export_button.setStyleSheet(self.fileButtonStyle() if self.export_button.isEnabled() else self.disabledButtonStyle())


    def updateMainPlayPauseButtonState(self):
        """Main Play/Pause butonunun metnini ve durumunu günceller."""
        # Oynatma modu her şeye önceliklidir
        if self.playback_mode:
            self.main_play_pause_button.setEnabled(True)
            self.main_close_playback_button.setEnabled(True)
            self.main_play_pause_button.setText("Pause" if self.is_playing else "Play")
            self.disableRecordingButtons(True) # Oynatma sırasında kayıt butonlarını devre dışı bırak
            return

        # Dışa aktarma zorunluysa, oynat/duraklat butonunu devre dışı bırak
        if self.force_export_state:
            self.main_play_pause_button.setEnabled(False)
            self.main_play_pause_button.setText("Play")
            self.main_close_playback_button.setEnabled(False)
            self.disableRecordingButtons(True) # Diğer butonları da devre dışı bırak
            return

        # Kayıt modu
        if self.recording:
            self.main_play_pause_button.setEnabled(True)
            self.main_close_playback_button.setEnabled(False)
            self.main_play_pause_button.setText("Pause")
            self.disableRecordingButtons(True) # Kayıt sırasında diğer butonları devre dışı bırak
        # Kayda hazır mod
        elif self.windows_active or self.sound_active:
            self.main_play_pause_button.setEnabled(True)
            self.main_close_playback_button.setEnabled(False)
            self.main_play_pause_button.setText("Play")
            self.disableRecordingButtons(False)
        # Hiçbir mod seçili değil
        else:
            self.main_play_pause_button.setEnabled(False)
            self.main_close_playback_button.setEnabled(False)
            self.main_play_pause_button.setText("Play")
            self.disableRecordingButtons(False)


    def formatTime(self, seconds):
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def toggleFullscreen(self):
        if self.playback_mode == "video":
            if self.isFullScreen():
                self.showNormal()
                self.toolbar_frame.show()
                if self.playback_bar_frame.isHidden():
                    self.playback_bar_frame.show()
                total_height = self.height() - self.toolbar_frame.height()
                playback_bar_height = self.playback_bar_frame.height()
                min_video_height = 100

                if total_height - playback_bar_height < min_video_height:
                    playback_bar_height = max(0, total_height - min_video_height)

                self.splitter.setSizes([total_height - playback_bar_height, playback_bar_height])
            else:
                self.showFullScreen()
                self.toolbar_frame.hide()
                self.playback_bar_frame.hide()
                self.splitter.setSizes([self.height(), 0])
            print("Python: Tam ekran modu değiştirildi.")
        elif self.playback_mode == "audio":
            QMessageBox.information(self, "Fonksiyon Yok", "Ses dosyaları için tam ekran özelliği bulunmamaktadır.")
            print("Python: Ses dosyaları için tam ekran özelliği çalıştırılamadı.")

    # GÜNCELLEME: Uygulama kapatılırken tüm işlemleri durdur ve segmentleri temizle
    def closeEvent(self, event):
        print("Python: Uygulama kapatılıyor, tüm kayıt işlemleri durduruluyor...")
        self._stop_full_recording_session(cleanup=True) # Kapatırken segmentleri her zaman temizle
        self.closePlaybackBar()
        if self.camera_feature_window:
            self.camera_feature_window.close()

        event.accept()
        print("Python: Uygulama başarıyla kapatıldı.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    recorder = CameraRecorderWindow()

    # YENİ GÜNCELLEME: Ctrl+C (SIGINT) sinyalini yakalamak için handler
    # Bu, terminalden programı kapattığınızda bile temizleme kodunun çalışmasını sağlar.
    def sigint_handler(*args):
        """Handler for the SIGINT signal."""
        print("\nPython: Ctrl+C algılandı. Uygulama güvenli bir şekilde kapatılıyor...")
        # closeEvent'i tetiklemek için pencereyi kapat
        recorder.close()
        # Uygulamadan çık
        QApplication.quit()

    signal.signal(signal.SIGINT, sigint_handler)

    # Python'un sinyalleri işleyebilmesi için bir QTimer kullanmak daha güvenlidir.
    # Bu, Qt event loop'unun kesintiye uğramamasını sağlar.
    timer = QTimer()
    timer.start(500) # Her 500ms'de bir Python'un çalışmasına izin ver
    timer.timeout.connect(lambda: None) # Hiçbir şey yapmayan bir lambda

    recorder.show()
    sys.exit(app.exec_())
