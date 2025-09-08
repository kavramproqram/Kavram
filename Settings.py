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

import subprocess
import json
import os
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QMessageBox, QSpacerItem, QSizePolicy, QGroupBox, QCheckBox, QPushButton, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

class Settings(QWidget):
    SETTINGS_FILE = "blue_light_filter_settings.json"

    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_settings()
        # Uygulama başlatıldığında mevcut filtreleri ve ayarları uygula
        self.apply_display_settings()

    def initUI(self):
        # Pencere başlığını "Settings" olarak ayarla
        self.setWindowTitle("Settings")
        # Pencere boyutunu ayarla (genişlik 700, yükseklik 500)
        self.setGeometry(100, 100, 700, 500)

        # Uygulama ikonunu belirtilen yolla ayarla
        # İkon dosyanızın yolu: 'ikon/Kavram.png'
        self.setWindowIcon(QIcon('ikon/Kavram.png'))

        self.setStyleSheet("""
            QWidget {
                background-color: #202020;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial;
                font-size: 14px;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 16px;
            }
            QGroupBox {
                border: 1px solid #404040;
                border-radius: 8px;
                margin-top: 1ex;
                font-size: 14px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                background-color: #202020;
            }
            QSlider::groove:horizontal {
                border: 1px solid #333333;
                height: 10px;
                background: #505050;
                margin: 2px 0;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #a0a0a0;
                border: 1px solid #707070;
                width: 20px;
                height: 20px;
                margin: -5px 0;
                border-radius: 10px;
            }
            QSlider::sub-page:horizontal {
                background: #606060;
                border: 1px solid #505050;
                height: 10px;
                border-radius: 5px;
            }
            /* Genel QCheckBox stilleri kaldırıldı, Gri Mod için özel stil aşağıda tanımlanacak */
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #444;
            }
            QPushButton:pressed {
                background-color: #666;
            }
        """)

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # Üst araç çubuğu (Toolbar)
        self.toolbar_frame = QFrame()
        self.toolbar_frame.setStyleSheet("""
            QFrame {
                background-color: #222;
                border-bottom: 2px solid #555;
            }
        """)
        self.toolbar_frame.setFixedHeight(40)

        self.toolbar_layout = QHBoxLayout(self.toolbar_frame)
        self.toolbar_layout.setContentsMargins(10, 5, 10, 5)

        # Reset butonu
        self.reset_button = QPushButton("Reset")
        self.reset_button.setFixedSize(90, 30) # Sabit boyut eklendi
        self.reset_button.setStyleSheet(self.buttonStyle()) # Sphere stilinden alındı
        self.reset_button.clicked.connect(self.set_default_settings)
        self.toolbar_layout.addWidget(self.reset_button, alignment=Qt.AlignLeft)

        # Boşluk (Stretch)
        self.toolbar_layout.addStretch()

        # Gri Mod onay kutusu (artık buton gibi görünecek)
        self.grayscale_checkbox = QCheckBox("Gri Mod")
        self.grayscale_checkbox.setFixedSize(90, 30) # Reset butonu ile aynı boyut
        self.grayscale_checkbox.setStyleSheet("""
            QCheckBox {
                background-color: transparent;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #555; /* Varsayılan kenarlık */
                border-radius: 6px;
                padding: 3px 10px;
            }
            QCheckBox:hover { background-color: #444; }
            QCheckBox:pressed { background-color: #666; } /* Basıldığında QPushButton gibi */
            QCheckBox:checked {
                background-color: #555555; /* Aktif olduğunda gri arka plan */
                color: white;
                border: none; /* Aktif olduğunda kenarlıksız */
            }
            QCheckBox::indicator {
                width: 0px; /* Göstergeyi gizle */
                height: 0px; /* Göstergeyi gizle */
            }
        """)
        self.grayscale_checkbox.stateChanged.connect(self.on_grayscale_checkbox_changed)
        self.toolbar_layout.addWidget(self.grayscale_checkbox, alignment=Qt.AlignRight)

        self.main_layout.addWidget(self.toolbar_frame)

        status_group = QGroupBox("Filtre Durumu")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("Durum: Yükleniyor...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px;")
        status_layout.addWidget(self.status_label)

        self.description_label = QLabel()
        self.description_label.setAlignment(Qt.AlignCenter)
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("font-size: 13px; color: #b0b0b0; padding: 5px;")
        status_layout.addWidget(self.description_label)

        status_group.setLayout(status_layout)
        self.main_layout.addWidget(status_group)

        # Gamma ayar grubu
        gamma_group = QGroupBox("Gamma Ayarları (Renk Yoğunluğu)")
        gamma_layout = QVBoxLayout()

        # Kırmızı (Red) Gamma Ayarı
        self.red_gamma_slider_label = QLabel("Red (Kırmızı) Gamma:")
        self.red_gamma_slider_label.setAlignment(Qt.AlignCenter)
        gamma_layout.addWidget(self.red_gamma_slider_label)

        self.red_gamma_slider = QSlider(Qt.Horizontal)
        self.red_gamma_slider.setRange(1, 200) # 0.01'den 2.00'e kadar (100 ile çarpıldı)
        self.red_gamma_slider.setValue(100) # Varsayılan 1.0
        self.red_gamma_slider.setSingleStep(1)
        self.red_gamma_slider.setPageStep(10)
        self.red_gamma_slider.setFixedWidth(600) # Genişlik artırıldı
        self.red_gamma_slider.valueChanged.connect(self.on_slider_value_changed)
        gamma_layout.addWidget(self.red_gamma_slider, alignment=Qt.AlignCenter)

        # Yeşil (Green) Gamma Ayarı
        self.green_gamma_slider_label = QLabel("Green (Yeşil) Gamma:")
        self.green_gamma_slider_label.setAlignment(Qt.AlignCenter)
        gamma_layout.addWidget(self.green_gamma_slider_label)

        self.green_gamma_slider = QSlider(Qt.Horizontal)
        self.green_gamma_slider.setRange(1, 200) # 0.01'den 2.00'e kadar
        self.green_gamma_slider.setValue(100) # Varsayılan 1.0
        self.green_gamma_slider.setSingleStep(1)
        self.green_gamma_slider.setPageStep(10)
        self.green_gamma_slider.setFixedWidth(600) # Genişlik artırıldı
        self.green_gamma_slider.valueChanged.connect(self.on_slider_value_changed)
        gamma_layout.addWidget(self.green_gamma_slider, alignment=Qt.AlignCenter)

        # Mavi (Blue) Gamma Ayarı (Çok Daha Fazla Mavi Işık Azaltma)
        self.blue_gamma_slider_label = QLabel("Blue (Mavi) Gamma (Mavi Işık Azaltma):")
        self.blue_gamma_slider_label.setAlignment(Qt.AlignCenter)
        gamma_layout.addWidget(self.blue_gamma_slider_label)

        self.blue_gamma_slider = QSlider(Qt.Horizontal)
        # 1'den 1000'e kadar: 1 (0.001 gamma) ile 1000 (1.0 gamma) arasında
        # Bu, çok daha agresif mavi ışık azaltma sağlar.
        self.blue_gamma_slider.setRange(1, 1000)
        self.blue_gamma_slider.setValue(1000) # Varsayılan 1.0 (mavi ışık azaltma yok)
        self.blue_gamma_slider.setSingleStep(1)
        self.blue_gamma_slider.setPageStep(10)
        self.blue_gamma_slider.setFixedWidth(600) # Genişlik artırıldı
        self.blue_gamma_slider.valueChanged.connect(self.on_slider_value_changed)
        gamma_layout.addWidget(self.blue_gamma_slider, alignment=Qt.AlignCenter)

        gamma_group.setLayout(gamma_layout)
        self.main_layout.addWidget(gamma_group)

        # Parlaklık ve Karanlık Filtre grubu
        brightness_darkness_group = QGroupBox("Parlaklık ve Karanlık Filtre")
        bd_layout = QVBoxLayout()

        # Parlaklık Ayarı
        self.brightness_slider_label = QLabel("Brightness (Ekran Parlaklığı):")
        self.brightness_slider_label.setAlignment(Qt.AlignCenter)
        bd_layout.addWidget(self.brightness_slider_label)

        self.brightness_slider = QSlider(Qt.Horizontal)
        self.brightness_slider.setRange(0, 200) # 0.0 (kapalı) ile 2.0 (iki kat parlaklık)
        self.brightness_slider.setValue(100) # Varsayılan 1.0
        self.brightness_slider.setSingleStep(1)
        self.brightness_slider.setPageStep(10)
        self.brightness_slider.setFixedWidth(600) # Genişlik artırıldı
        self.brightness_slider.valueChanged.connect(self.on_slider_value_changed)
        bd_layout.addWidget(self.brightness_slider, alignment=Qt.AlignCenter)

        # Karanlık Filtre Ayarı
        self.darkness_filter_slider_label = QLabel("Darkness Filter (Ekstra Karanlık):")
        self.darkness_filter_slider_label.setAlignment(Qt.AlignCenter)
        bd_layout.addWidget(self.darkness_filter_slider_label)

        self.darkness_filter_slider = QSlider(Qt.Horizontal)
        self.darkness_filter_slider.setRange(0, 100) # 0 (normal) ile 100 (maksimum karanlık)
        self.darkness_filter_slider.setValue(0) # Varsayılan 0 (ekstra karanlık yok)
        self.darkness_filter_slider.setSingleStep(1)
        self.darkness_filter_slider.setPageStep(10)
        self.darkness_filter_slider.setFixedWidth(600) # Genişlik artırıldı
        self.darkness_filter_slider.valueChanged.connect(self.on_slider_value_changed)
        bd_layout.addWidget(self.darkness_filter_slider, alignment=Qt.AlignCenter)

        brightness_darkness_group.setLayout(bd_layout)
        self.main_layout.addWidget(brightness_darkness_group)

        # Alt kısımdaki boşluğu ekle
        self.main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.MinimumExpanding))


    def buttonStyle(self):
        """
        Ortak buton stil ayarları (sphere.py'den örnek alındı).
        """
        return """
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 6px;
                padding: 3px 10px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

    def check_xrandr_installed(self):
        """xrandr'ın yüklü olup olmadığını kontrol eder."""
        try:
            subprocess.run(["xrandr", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def set_screen_settings(self, gamma_r, gamma_g, gamma_b, brightness):
        """Ekranın gamma ve parlaklık değerlerini ayarlar."""
        gamma_string = f"{gamma_r:.3f}:{gamma_g:.3f}:{gamma_b:.3f}" # Daha hassas gamma için .3f
        try:
            # Mevcut bağlı ekranları bul
            output = subprocess.check_output("xrandr --current", shell=True).decode("utf-8")
            displays = []
            for line in output.splitlines():
                if " connected" in line:
                    parts = line.split(" connected")[0].strip().split(" ")
                    if parts:
                        display_name = parts[-1]
                        displays.append(display_name)

            if not displays:
                QMessageBox.critical(self, "Hata", "Bağlı ekran bulunamadı. Lütfen bir ekranın bağlı olduğundan emin olun.")
                return False

            # Her bağlı ekran için gamma ve parlaklık ayarını uygula
            for display in displays:
                command = ["xrandr", "--output", display, "--gamma", gamma_string, "--brightness", f"{brightness:.2f}"]
                subprocess.run(command, check=True)
            return True
        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Hata", f"Ekran ayarları yapılamadı: {e.stderr.decode('utf-8')}")
            return False
        except FileNotFoundError:
            QMessageBox.critical(self, "Hata", "xrandr bulunamadı. Lütfen yüklü olduğundan emin olun.")
            return False
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Bilinmeyen bir hata oluştu: {str(e)}")
            return False

    def apply_display_settings(self):
        """Kaydırıcı değerlerine göre ekran ayarlarını uygular."""
        # Gamma değerlerini 0.01-2.00 aralığına dönüştür
        gamma_r = self.red_gamma_slider.value() / 100.0
        gamma_g = self.green_gamma_slider.value() / 100.0
        # Mavi gamma için çok daha geniş aralık (0.001 - 1.0)
        gamma_b = self.blue_gamma_slider.value() / 1000.0

        # Parlaklık değerini 0.0-2.0 aralığına dönüştür
        brightness = self.brightness_slider.value() / 100.0

        # Karanlık filtre değerini 1.0 (normal) ile 0.0 (tamamen karanlık) arasına dönüştür
        # Slider 0 olduğunda çarpan 1.0 (etki yok), 100 olduğunda çarpan 0.0 (tamamen karanlık)
        darkness_factor = (100 - self.darkness_filter_slider.value()) / 100.0

        # Gri Mod etkinse kırmızı, yeşil ve mavi gammayı aynı değere ayarla (grinin tonları için)
        if self.grayscale_checkbox.isChecked():
            # Tüm renk kanallarını aynı değere ayarlayarak gri tonlama sağlar
            # 0.5 gibi bir değer, ekranı çok karartmadan gri yapar.
            grayscale_gamma_value = 0.5
            gamma_r = grayscale_gamma_value
            gamma_g = grayscale_gamma_value
            gamma_b = grayscale_gamma_value

        # Karanlık filtreyi gamma değerlerine uygula
        gamma_r *= darkness_factor
        gamma_g *= darkness_factor
        gamma_b *= darkness_factor

        # Minimum gamma değerlerini koru (ekranın tamamen kararmasını engellemek için)
        gamma_r = max(0.001, gamma_r)
        gamma_g = max(0.001, gamma_g)
        gamma_b = max(0.001, gamma_b)

        self.set_screen_settings(gamma_r, gamma_g, gamma_b, brightness)

        self.update_status(gamma_r, gamma_g, gamma_b, brightness, darkness_factor)
        self.save_settings() # Ayarları her değişiklikte kaydet

    def on_slider_value_changed(self, value):
        """Kaydırıcı değeri değiştiğinde ekran ayarlarını uygular."""
        self.apply_display_settings()

    def on_grayscale_checkbox_changed(self, state):
        """Gri Mod onay kutusu değiştiğinde ekran ayarlarını uygular."""
        # Gri mod etkinleştirildiğinde veya devre dışı bırakıldığında kaydırıcıları etkisiz hale getir/etkinleştir
        is_grayscale = self.grayscale_checkbox.isChecked()
        self.red_gamma_slider.setEnabled(not is_grayscale)
        self.green_gamma_slider.setEnabled(not is_grayscale)
        self.blue_gamma_slider.setEnabled(not is_grayscale)
        self.brightness_slider.setEnabled(not is_grayscale) # Parlaklık da gri modda devre dışı bırakılabilir
        self.darkness_filter_slider.setEnabled(not is_grayscale) # Karanlık filtre de gri modda devre dışı bırakılabilir

        self.apply_display_settings() # Ayarları yeniden uygula

    def update_status(self, gamma_r, gamma_g, gamma_b, brightness, darkness_factor):
        """Uygulamanın durum etiketlerini günceller."""

        status_text = (
            f"Durum: Aktif (R: {gamma_r:.3f}, G: {gamma_g:.3f}, B: {gamma_b:.3f}, "
            f"Parlaklık: {brightness:.2f}, Karanlık Filtre: {((1-darkness_factor)*100):.0f}%)"
        )

        description = (
            f"Kırmızı, Yeşil ve Mavi renk kanallarının gamma değerleri ayarlanmıştır. "
            f"Mavi gamma değeri düştükçe mavi ışık azalır ve ekran daha sıcak görünür. "
            f"Ekran parlaklığı ve ek karanlık filtresi de uygulanmıştır."
        )

        # Mavi gamma değeri düştükçe renk sıcaklığı artar, buna göre renk verelim
        if self.grayscale_checkbox.isChecked():
            color = "#cccccc" # Gri modda gri renk
            description = "Ekran gri tonlamalı moda ayarlandı. Renk ve parlaklık ayarları devre dışı bırakıldı."
        elif gamma_b < 0.2: # Çok sıcak ve karanlık
            color = "#ff3300"
        elif gamma_b < 0.7: # Orta sıcak
            color = "#ff9966"
        else: # Normal veya soğuk
            color = "#4da6ff"

        self.status_label.setText(status_text)
        self.description_label.setText(description)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")

    def load_settings(self):
        """Kayıtlı ayarları yükler ve uygular."""
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)

                    # Gamma değerlerini yükle, varsayılan olarak 1.0 (yani slider'da 100 veya 1000)
                    self.red_gamma_slider.setValue(max(1, min(200, int(settings.get('red_gamma_value', 100)))))
                    self.green_gamma_slider.setValue(max(1, min(200, int(settings.get('green_gamma_value', 100)))))
                    self.blue_gamma_slider.setValue(max(1, min(1000, int(settings.get('blue_gamma_value', 1000)))))

                    # Parlaklık ve Karanlık Filtre değerlerini yükle
                    self.brightness_slider.setValue(max(0, min(200, int(settings.get('brightness_value', 100)))))
                    self.darkness_filter_slider.setValue(max(0, min(100, int(settings.get('darkness_filter_value', 0)))))

                    # Gri Mod ayarını yükle
                    self.grayscale_checkbox.setChecked(settings.get('grayscale_mode', False))

                    self.apply_display_settings() # Yüklenen ayarları uygula
                    self.status_label.setText("Durum: Ayarlar Yüklendi")
                    self.status_label.setStyleSheet("color: #4da6ff; font-size: 16px; font-weight: bold;")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Ayarlar yüklenirken hata: {str(e)}. Varsayılan ayarlar uygulanıyor.")
                self.set_default_settings()
        else:
            self.set_default_settings()

    def save_settings(self):
        """Mevcut ayarları dosyaya kaydeder."""
        settings = {
            'red_gamma_value': self.red_gamma_slider.value(),
            'green_gamma_value': self.green_gamma_slider.value(),
            'blue_gamma_value': self.blue_gamma_slider.value(),
            'brightness_value': self.brightness_slider.value(),
            'darkness_filter_value': self.darkness_filter_slider.value(),
            'grayscale_mode': self.grayscale_checkbox.isChecked() # Gri Mod durumunu kaydet
        }

        try:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(settings, f)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Ayarlar kaydedilirken hata: {str(e)}")

    def set_default_settings(self):
        """Varsayılan ayarları uygular ve kaydeder."""
        self.red_gamma_slider.setValue(100)
        self.green_gamma_slider.setValue(100)
        self.blue_gamma_slider.setValue(1000) # Varsayılan olarak mavi ışık azaltma yok (gamma 1.0)
        self.brightness_slider.setValue(100) # Varsayılan parlaklık 1.0
        self.darkness_filter_slider.setValue(0) # Varsayılan ekstra karanlık yok
        self.grayscale_checkbox.setChecked(False) # Varsayılan olarak gri mod kapalı

        self.apply_display_settings()
        self.status_label.setText("Durum: Varsayılan Ayarlar Uygulandı")
        self.status_label.setStyleSheet("color: #a0a0a0; font-size: 16px; font-weight: bold;")
        self.save_settings()

    def closeEvent(self, event):
        """Uygulama kapatılırken ayarları kaydeder."""
        self.save_settings()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = Settings()
    ex.show()
    sys.exit(app.exec_())

