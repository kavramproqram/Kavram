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
import math
import os
import json
import base64
import numpy as np # imageio için numpy eklendi
import subprocess  # C++ uygulamasını çağırmak için eklendi
import shutil      # Geçici dizinleri temizlemek için eklendi
import tempfile    # Geçici dizin oluşturmak için eklendi
import time        # İlerleme çubuğu için zaman takibi

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QDialog, QSlider, QLabel,
    QPushButton, QApplication, QFileDialog, QMessageBox, QShortcut, QLineEdit,
    QComboBox, QSpinBox, QInputDialog, QStyle, QSizePolicy, QMenu, QAction,
    QProgressBar # QProgressBar eklendi
)
from PyQt5.QtGui import QColor, QPainter, QPen, QImage, QTabletEvent, QKeySequence, QFont, QFontMetrics, QCursor, QPixmap, QIcon # QPixmap ve QIcon eklendi
from PyQt5.QtCore import Qt, QPoint, QRect, QDir, QSize, QByteArray, QBuffer, QIODevice, QTimer, pyqtSignal
from PyQt5.QtSvg import QSvgRenderer # SVG ikonları için eklendi

# Renk seçimi için kullanılan diyalog
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

        self.setFixedSize(280, 250) # Boyut hex input için artırıldı

        self.colorWheel = QImage(self.hueSatDiameter, self.hueSatDiameter, QImage.Format_ARGB32)
        self._generateColorWheel()

        self.slider = QSlider(Qt.Vertical, self)
        self.slider.setRange(0, 100)
        self.slider.setValue(int(self.v * 100))
        self.slider.setGeometry(self.hueSatDiameter + 20, 10, 20, self.hueSatDiameter)
        self.slider.valueChanged.connect(self.onValueChanged)

        self.brightness_label = QLabel(self)
        self.brightness_label.setStyleSheet("color: white;")
        self.brightness_label.setGeometry(self.hueSatDiameter + 50, 10, 40, 20)
        self.brightness_label.setText(f"{int(self.v*100)}%")

        # Hex kodu girişi için yeni alanlar
        self.hex_input = QLineEdit(self)
        self.hex_input.setGeometry(10, self.hueSatDiameter + 20, 150, 30)
        self.hex_input.setStyleSheet("background-color: #444; color: white; border: 1px solid #777; border-radius: 5px;")
        # Başlangıç renginin hex kodunu '#' olmadan göster
        self.hex_input.setText(initialColor.name().lstrip('#')) 
        self.hex_input.returnPressed.connect(self.applyHexColor)

        self.apply_hex_button = QPushButton("Apply Hex", self)
        self.apply_hex_button.setGeometry(170, self.hueSatDiameter + 20, 100, 30)
        self.apply_hex_button.setStyleSheet(
            "QPushButton { background-color: #555; color: white; border-radius: 5px; padding: 5px; }"
            "QPushButton:hover { background-color: #777; }"
        )
        self.apply_hex_button.clicked.connect(self.applyHexColor)

        self.updateHexInput() # Başlangıçta hex input'u güncelle

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
                else:
                    self.colorWheel.setPixelColor(x, y, Qt.transparent)

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
            if self._pickHueSat(event.pos()):
                self.update()
                self.updateHexInput() # Renk tekerleği ile renk değiştiğinde hex input'u güncelle
            else:
                self.accept()
        else:
            self.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if self._pickHueSat(event.pos()):
                self.update()
                self.updateHexInput() # Renk tekerleği ile renk değiştiğinde hex input'u güncelle

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
                return True
        return False

    def onValueChanged(self, val):
        self.v = val / 100.0
        self.brightness_label.setText(f"{val}%")
        self.update()
        self.updateHexInput() # Parlaklık değiştiğinde hex input'u güncelle

    def getSelectedColor(self):
        return QColor.fromHsvF(self.h/360.0, self.s, self.v)

    def updateHexInput(self):
        # Mevcut seçili rengin hex kodunu al ve input alanına yaz
        current_color = self.getSelectedColor()
        self.hex_input.setText(current_color.name().lstrip('#')) # '#' olmadan göster

    def applyHexColor(self):
        hex_code = self.hex_input.text()
        # Hex kodunun başında '#' yoksa ekle
        if not hex_code.startswith('#'):
            hex_code = '#' + hex_code
        try:
            new_color = QColor(hex_code)
            if new_color.isValid():
                hF, sF, vF, _ = new_color.getHsvF()
                self.h = int(hF * 360)
                self.s = sF
                self.v = vF
                self.slider.setValue(int(self.v * 100)) # Slider'ı da güncelle
                self.update()
            # else: QMessageBox.warning kaldırıldı
        except Exception as e:
            # QMessageBox.critical kaldırıldı
            print(f"Hex kodu uygulanırken hata oluştu: {e}")


    def focusOutEvent(self, event):
        # Hex input alanı dışına tıklanırsa dialogu kapatma
        # Sadece dialogun genel alanına tıklanırsa kapat
        if not self.rect().contains(event.pos()):
            self.accept()
        # super().focusOutEvent(event) # Bu satırın kaldırılması gerekiyor, aksi takdirde input focus kaybedince kapanır

# Radius ayarını yapmak için diyalog
class RadiusDialog(QDialog):
    def __init__(self, initialRadius=7, parent=None): # Varsayılan radius 7 olarak güncellendi
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedSize(200, 100)
        self.radius = initialRadius

        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(1, 100)
        self.slider.setValue(self.radius)
        self.slider.setGeometry(20, 40, 160, 20)
        self.slider.valueChanged.connect(self.onValueChanged)

        self.label = QLabel(self)
        self.label.setGeometry(20, 10, 160, 20)
        self.label.setStyleSheet("color: white;")
        self.label.setText(f"Radius: {self.radius}")

        self.ok_button = QPushButton("OK", self)
        self.ok_button.setGeometry(70, 70, 60, 25)
        self.ok_button.setStyleSheet(
            "QPushButton { background-color: #222; color: white; border: 2px solid #555; border-radius: 8px; padding: 5px 10px; }"
            "QPushButton:hover { background-color: #444; }"
            "QPushButton:pressed { background-color: #666; }"
        )
        self.ok_button.clicked.connect(self.accept)

    def onValueChanged(self, value):
        self.radius = value
        self.label.setText(f"Radius: {self.radius}")

    def getRadius(self):
        return self.radius

# Yeni Frame Ekleme Diyaloğu
class AddFramesDialog(QDialog):
    def __init__(self, initialFrames=12, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedSize(200, 100)
        self.frames_to_add = initialFrames

        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(1, 100) # 1'den 100'e kadar kare ekleme aralığı
        self.slider.setValue(self.frames_to_add)
        self.slider.setGeometry(20, 40, 160, 20)
        self.slider.valueChanged.connect(self.onValueChanged)

        self.label = QLabel(self)
        self.label.setGeometry(20, 10, 160, 20)
        self.label.setStyleSheet("color: white;")
        self.label.setText(f"Add Frames: {self.frames_to_add}")

        self.ok_button = QPushButton("OK", self)
        self.ok_button.setGeometry(70, 70, 60, 25)
        self.ok_button.setStyleSheet(
            "QPushButton { background-color: #222; color: white; border: 2px solid #555; border-radius: 8px; padding: 5px 10px; }"
            "QPushButton:hover { background-color: #444; }"
            "QPushButton:pressed { background-color: #666; }"
        )
        self.ok_button.clicked.connect(self.accept)

    def onValueChanged(self, value):
        self.frames_to_add = value
        self.label.setText(f"Add Frames: {self.frames_to_add}")

    def getFramesToAdd(self):
        return self.frames_to_add

# Animasyon başlangıç ayarları diyalogu
class AnimationSettingsDialog(QDialog):
    def __init__(self, parent=None, initial_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Animasyon Ayarları")
        self.setWindowIcon(QIcon('ikon/Kavram.png'))
        self.setModal(True)
        self.setFixedSize(350, 300)
        self.setStyleSheet("background-color: #222; color: white;")

        # QComboBox'ları layout'a eklenmeden önce tanımla
        self.fps_combo = QComboBox()
        self.duration_combo = QComboBox()

        layout = QVBoxLayout(self)
        
        # Çözünürlük
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("Çözünürlük:"))
        self.width_input = QSpinBox()
        self.width_input.setRange(100, 4096)
        self.width_input.setStyleSheet("background-color: #333; color: white; border: 1px solid #555;")
        self.height_input = QSpinBox()
        self.height_input.setRange(100, 4096)
        self.height_input.setStyleSheet("background-color: #333; color: white; border: 1px solid #555;")
        res_layout.addWidget(self.width_input)
        res_layout.addWidget(QLabel("x"))
        res_layout.addWidget(self.height_input)
        layout.addLayout(res_layout)

        # Arka Plan Rengi
        bg_color_layout = QHBoxLayout()
        bg_color_layout.addWidget(QLabel("Arka Plan Rengi:"))
        self.bg_color_button = QPushButton("Renk Seç")
        self.bg_color_button.setStyleSheet(
            "QPushButton { background-color: white; border: 1px solid #555; border-radius: 5px; padding: 5px; }"
            "QPushButton:hover { background-color: #eee; }"
        )
        self.bg_color_button.clicked.connect(self.chooseBackgroundColor)
        self.selected_bg_color = QColor("#333")
        bg_color_layout.addWidget(self.bg_color_button)
        layout.addLayout(bg_color_layout)

        # Kare Hızı (FPS)
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("Kare Hızı (FPS):"))
        self.fps_combo.addItems(["3", "6", "12", "24", "25", "30"])
        self.fps_combo.setStyleSheet("background-color: #333; color: white; border: 1px solid #555;")
        fps_layout.addWidget(self.fps_combo)
        layout.addLayout(fps_layout)

        # Animasyon Süresi (Saniye)
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Animasyon Süresi (saniye):"))
        durations = [str(i) for i in range(10, 121, 10)] # 10'dan 120'ye 10'ar artarak
        self.duration_combo.addItems(durations)
        self.duration_combo.setStyleSheet("background-color: #333; color: white; border: 1px solid #555;")
        duration_layout.addWidget(self.duration_combo)
        layout.addLayout(duration_layout)

        # Onay Butonları
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.setStyleSheet(
            "QPushButton { background-color: #222; color: white; border: 2px solid #555; border-radius: 8px; padding: 8px 15px; }"
            "QPushButton:hover { background-color: #444; }"
            "QPushButton:pressed { background-color: #666; }"
        )
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.setStyleSheet(
            "QPushButton { background-color: #222; color: white; border: 2px solid #555; border-radius: 8px; padding: 8px 15px; }"
            "QPushButton:hover { background-color: #444; }"
            "QPushButton:pressed { background-color: #666; }"
        )
        cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Ayarları yükle
        if initial_settings:
            self.width_input.setValue(initial_settings.get("width", 1920))
            self.height_input.setValue(initial_settings.get("height", 1080))
            bg_color_list = initial_settings.get("background_color", [51, 51, 51, 255])
            self.selected_bg_color = QColor(*bg_color_list)
            self.fps_combo.setCurrentText(str(initial_settings.get("fps", 24)))
            self.duration_combo.setCurrentText(str(initial_settings.get("duration", 30)))
        else: # Varsayılan değerler
            self.width_input.setValue(1920)
            self.height_input.setValue(1080)
            self.fps_combo.setCurrentText("24")
            self.duration_combo.setCurrentText("30")

        self.updateBgColorButton()

    def chooseBackgroundColor(self):
        dialog = CircleBrightnessDialog(initialColor=self.selected_bg_color, parent=self)
        # Butonun global pozisyonunu al ve dialogu onun altına aç
        button_pos = self.bg_color_button.mapToGlobal(QPoint(0, self.bg_color_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            self.selected_bg_color = dialog.getSelectedColor()
            self.updateBgColorButton()

    def updateBgColorButton(self):
        # Butonun arka plan rengini seçilen renge göre ayarla
        self.bg_color_button.setStyleSheet(
            f"QPushButton {{ background-color: {self.selected_bg_color.name()}; border: 1px solid #555; border-radius: 5px; padding: 5px; }}"
            "QPushButton:hover { background-color: #eee; }"
        )
        # Yazı rengini arka plan rengine göre ayarla (okunabilirlik için)
        if (self.selected_bg_color.red() * 0.299 + self.selected_bg_color.green() * 0.587 + self.selected_bg_color.blue() * 0.114) > 186:
            self.bg_color_button.setStyleSheet(self.bg_color_button.styleSheet() + "color: black;")
        else:
            self.bg_color_button.setStyleSheet(self.bg_color_button.styleSheet() + "color: white;")

    def getSettings(self):
        return {
            "width": self.width_input.value(),
            "height": self.height_input.value(),
            "background_color": [self.selected_bg_color.red(), self.selected_bg_color.green(), self.selected_bg_color.blue(), self.selected_bg_color.alpha()],
            "fps": int(self.fps_combo.currentText()),
            "duration": int(self.duration_combo.currentText())
        }

# Çizim yapılacak alan
class DrawingArea(QWidget):
    def __init__(self, width, height, bg_color, total_frames, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StaticContents)
        self.modified = False
        self.drawing = False
        self.panning = False # Pan durumu için yeni değişken
        self.lastPoint = QPoint()
        self.last_pan_pos = QPoint() # Pan başlangıç pozisyonu için

        self.bg_color = bg_color
        self.image_width = width
        self.image_height = height

        # Tuvalin yakınlaştırma ve gezinme durumu
        self.canvas_scale = 1.0 / 3.0 # Başlangıç ölçeği 1/3 olarak ayarlandı
        self.canvas_offset = QPoint(0, 0) # resizeEvent içinde güncellenecek
        self.min_canvas_scale = 0.1
        self.max_canvas_scale = 5.0

        # DrawingArea'nın boyutlandırma politikasını ayarla
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Tüm karelerin çizim öğelerini depolayan liste
        # Her bir eleman, o kareye ait drawing_elements listesidir.
        self.all_frames_elements = [] # setTotalFrames tarafından doldurulacak
        self.current_frame_index = 0
        self.total_frames = 0 # setTotalFrames tarafından ayarlanacak

        # Undo/Redo yığınları (drawing_elements listesinin kopyalarını tutar)
        self.undo_stack = []
        self.redo_stack = []

        self.text_input_field = QLineEdit(self)
        self.text_input_field.hide()
        self.text_input_field.returnPressed.connect(self.addTextToDrawing)
        self.text_input_field.setStyleSheet("background-color: #444; color: white; border: 1px solid #777;")

        self.current_stroke_points = []
        # Geçici fırça vuruşlarının renk ve genişlik bilgileri
        self.current_stroke_pen_info = [] 

        # Önbelleğe alınmış kare resmi ve indeksi
        self.cached_frame_image = None
        self.cached_frame_index = -1

        # Metin manipülasyonu için yeni değişkenler
        self.current_text_element = None # Şu anda manipüle edilen metin öğesi
        self.text_panning = False # Metin taşıma durumu
        self.last_text_pan_pos = QPoint() # Metin taşıma başlangıç pozisyonu

        # Resim manipülasyonu için yeni değişkenler
        self.current_image_element = None # Şu anda manipüle edilen resim öğesi
        self.image_panning = False # Resim taşıma durumu
        self.last_image_pan_pos = QPoint() # Resim taşıma başlangıç pozisyonu

        # Kalem ayarları (DrawingEditorWindow'dan buraya taşındı)
        self.pen_color = QColor("white")
        self.pen_radius = 7 # Varsayılan kalem kalınlığı 7 olarak güncellendi
        self.eraser_mode = False
        self.pen_pressure_enabled = False
        self.text_mode = False
        self.placing_image = False 
        self.picking_color = False # Renk seçme (damlalık) modu için yeni değişken

        # Tablet tuş durumları
        self.tablet_button_1_pressed = False # Kalem 1. tuşu (pan)
        self.tablet_button_2_pressed = False # Kalem 2. tuşu (zoom)
        self.last_zoom_pos = QPoint() # Zoom için son pozisyon

        # initFrames yerine setTotalFrames çağrısı ile başlangıç karelerini oluştur
        self.setTotalFrames(total_frames)

    def setTotalFrames(self, total_frames):
        """Toplam kare sayısını ayarlar ve kare listesini günceller."""
        # Eğer yeni toplam kare sayısı farklıysa veya kareler henüz oluşturulmamışsa
        if total_frames != self.total_frames or not self.all_frames_elements:
            self.total_frames = total_frames
            # Yeni boş kareler oluştur veya mevcutları kes
            new_all_frames_elements = [[] for _ in range(self.total_frames)]
            # Mevcut karelerin içeriğini yeni listeye kopyala
            for i in range(min(len(self.all_frames_elements), self.total_frames)):
                new_all_frames_elements[i] = self.all_frames_elements[i]
            self.all_frames_elements = new_all_frames_elements
        
        # Geçerli kare indeksini kontrol et
        if self.current_frame_index >= self.total_frames:
            self.current_frame_index = max(0, self.total_frames - 1)
        self.updateImageFromElements() # Toplam kare sayısı değiştiğinde veya ilk kez ayarlandığında önbelleği güncelle

    def setCurrentFrame(self, index):
        """Görüntülenecek ve düzenlenecek kareyi değiştirir."""
        if 0 <= index < self.total_frames:
            if self.current_frame_index != index: # Sadece kare değiştiyse güncelle
                self.current_frame_index = index
                self.updateImageFromElements() # Yeni kareye geçildiğinde önbelleği güncelle
                # Parent'ın timeline'ını güncellemek için sinyal gönder
                parent = self.parent()
                if parent and hasattr(parent, 'timeline_widget'): # Check if timeline_widget exists
                    parent.timeline_widget.setSliderValue(index) # Update slider value
                if parent and hasattr(parent, 'updateFrameInfoLabel'):
                    parent.updateFrameInfoLabel() # Üst bardaki frame bilgisini güncelle
            return True
        return False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Mevcut ölçekte içeriği ortalamak için offset'i yeniden hesapla
        widget_width = self.width()
        widget_height = self.height()

        if widget_width <= 0 or widget_height <= 0 or self.image_width <= 0 or self.image_height <= 0:
            return

        scaled_content_width = self.image_width * self.canvas_scale
        scaled_content_height = self.image_height * self.canvas_scale

        offset_x = (widget_width - scaled_content_width) / 2.0
        offset_y = (widget_height - scaled_content_height) / 2.0

        # Ekran alanı ofsetini tuval alanı ofsetine dönüştür
        self.canvas_offset = QPoint(int(offset_x / self.canvas_scale), int(offset_y / self.canvas_scale))
        self.update() # Yeniden çizim iste


    def sizeHint(self):
        """DrawingArea'nın tercih edilen boyutunu döndürür."""
        # Çizim alanının mantıksal boyutunu döndürüyoruz.
        # Bu, layout yöneticisinin widget'ı doğru boyutta yerleştirmesine yardımcı olur.
        return QSize(self.image_width, self.image_height)

    def minimumSizeHint(self):
        """DrawingArea'nın minimum boyutunu döndürür."""
        return QSize(self.image_width, self.image_height)

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = event.rect()
        
        painter.save() # Mevcut painter durumunu kaydet

        # Tuvalin ölçeklendirme ve öteleme dönüşümlerini uygula
        painter.scale(self.canvas_scale, self.canvas_scale)
        painter.translate(self.canvas_offset)
        
        # Önbelleğe alınmış mevcut karenin görüntüsünü çiz
        if self.cached_frame_image and self.cached_frame_index == self.current_frame_index:
            painter.drawImage(0, 0, self.cached_frame_image)
        else:
            # Eğer önbellek geçerli değilse, yeniden oluştur ve çiz
            self.updateImageFromElements()
            if self.cached_frame_image:
                painter.drawImage(0, 0, self.cached_frame_image)

        # Eğer bir fırça vuruşu devam ediyorsa, onu da çiz
        # current_stroke_points zaten tuval koordinatlarında olmalı
        if self.drawing and self.current_stroke_points:
            # Buradaki çizim, anlık olarak kullanıcıya geri bildirim sağlamak içindir.
            # Gerçek çizim verisi current_stroke_pen_info'da tutulur.
            for i in range(len(self.current_stroke_points) - 1):
                p1, p2 = self.current_stroke_points[i], self.current_stroke_points[i+1]
                color, width = self.current_stroke_pen_info[i]
                painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.drawLine(p1, p2)

        # Eğer geçici bir metin öğesi varsa, onu da çiz
        if self.current_text_element:
            element = self.current_text_element
            color = QColor(*element["color"])
            font = QFont("Arial", element["font_size"])
            painter.setPen(color)
            painter.setFont(font)
            text_pos = QPoint(element["position"][0], element["position"][1])
            
            # Metnin doğru yerleştirilmesi için font metriklerini kullan
            font_metrics = QFontMetrics(font)
            adjusted_y = text_pos.y() + font_metrics.ascent()
            painter.drawText(text_pos.x(), adjusted_y, element["content"])

        # Eğer geçici bir resim öğesi varsa, onu da çiz
        if self.current_image_element:
            element = self.current_image_element
            # Önbellekten QImage'i al, yoksa base64'ten yükle
            if "_qimage_cache" not in element:
                image_data = base64.b64decode(element["base64_data"])
                temp_image = QImage()
                temp_image.loadFromData(image_data, "PNG")
                element["_qimage_cache"] = temp_image
            else:
                temp_image = element["_qimage_cache"]

            scaled_image = temp_image.scaled(
                element["current_width"], element["current_height"],
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            image_pos = QPoint(element["position"][0], element["position"][1])
            painter.drawImage(image_pos, scaled_image)

        painter.restore() # Painter durumunu geri yükle

    def _renderFrameToImage(self, frame_index):
        """Belirtilen karedeki tüm öğeleri yeni bir QImage üzerine çizer."""
        frame_image = QImage(self.image_width, self.image_height, QImage.Format_RGB32)
        frame_image.fill(self.bg_color) # Kare arka planını ayarla

        painter = QPainter(frame_image)
        painter.setRenderHint(QPainter.Antialiasing)

        if frame_index < len(self.all_frames_elements):
            elements = self.all_frames_elements[frame_index]
            for element in elements:
                if element["type"] == "stroke":
                    color = QColor(*element["color"])
                    width = element["width"]
                    pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    painter.setPen(pen)
                    points = [QPoint(p[0], p[1]) for p in element["points"]]
                    for i in range(len(points) - 1):
                        painter.drawLine(points[i], points[i+1])
                elif element["type"] == "text":
                    color = QColor(*element["color"])
                    font = QFont("Arial", element["font_size"])
                    painter.setPen(color)
                    painter.setFont(font)
                    text_pos = QPoint(element["position"][0], element["position"][1])
                    
                    # Metnin doğru yerleştirilmesi için font metriklerini kullan
                    font_metrics = QFontMetrics(font)
                    adjusted_y = text_pos.y() + font_metrics.ascent()
                    painter.drawText(text_pos.x(), adjusted_y, element["content"])
                elif element["type"] == "image":
                    # Önbellekten QImage'i al, yoksa base64'ten yükle
                    if "_qimage_cache" not in element:
                        image_data = base64.b64decode(element["base64_data"])
                        temp_image = QImage()
                        temp_image.loadFromData(image_data, "PNG")
                        element["_qimage_cache"] = temp_image
                    else:
                        temp_image = element["_qimage_cache"]

                    scaled_image = temp_image.scaled(
                        element["current_width"], element["current_height"],
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    image_pos = QPoint(element["position"][0], element["position"][1])
                    painter.drawImage(image_pos, scaled_image)
        
        painter.end()
        return frame_image

    def mousePressEvent(self, event):
        # Renk seçme modu aktifse
        if self.picking_color:
            if event.button() == Qt.LeftButton:
                # Fare konumunu tuval koordinatlarına dönüştür
                canvas_x = int((event.pos().x() / self.canvas_scale) - self.canvas_offset.x())
                canvas_y = int((event.pos().y() / self.canvas_scale) - self.canvas_offset.y())

                # Piksel rengini al
                if self.cached_frame_image and 0 <= canvas_x < self.cached_frame_image.width() and \
                   0 <= canvas_y < self.cached_frame_image.height():
                    picked_color = self.cached_frame_image.pixelColor(canvas_x, canvas_y)
                    self.pen_color = picked_color # Kalem rengini seçilen renge ayarla
                
                self.picking_color = False # Renk seçme modundan çık
                self.setCursor(Qt.ArrowCursor) # İmleci varsayılana döndür
                self.parent().updateButtonStyles() # Buton stillerini güncelle
                event.accept()
                return # İşlem tamamlandı, diğer modlara geçme

        # DrawingArea'daki modları doğrudan kullan
        if self.text_mode:
            if self.current_text_element:
                # Metin manipülasyonu aktifken tıklama
                if event.button() == Qt.LeftButton or event.button() == Qt.RightButton:
                    # Sol veya sağ tuşla "yapıştırma" (kalıcı hale getirme)
                    self.undo_stack.append(list(self.all_frames_elements[self.current_frame_index]))
                    self.redo_stack.clear()
                    self.all_frames_elements[self.current_frame_index].append(self.current_text_element)
                    self.current_text_element = None # Geçici metni temizle
                    self.text_mode = False # Metin modundan çık
                    self.setCursor(Qt.ArrowCursor) # İmleci varsayılana döndür
                    self.parent().updateButtonStyles() # Metin butonu stilini güncelle
                    self.updateImageFromElements() # Çizimi güncelle
                    self.modified = True
                elif event.button() == Qt.MiddleButton:
                    # Orta tuşla metin taşıma başlat
                    self.text_panning = True
                    self.last_text_pan_pos = event.pos()
                    self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return # Metin modu işlendi, başka bir şey yapma
            else:
                # Metin modu aktif ama henüz metin girilmemişse, input alanını göster
                if event.button() == Qt.LeftButton:
                    text_pos_screen = event.pos()
                    # Input alanını ekran koordinatlarına taşı
                    self.text_input_field.move(int(text_pos_screen.x()), int(text_pos_screen.y())) 
                    self.text_input_field.show()
                    self.text_input_field.setFocus()
                    self.text_input_field.clear()
                    # Tuval koordinatlarını sakla (bu sadece ilk tıklama pozisyonu, metin taşınırken güncellenecek)
                    self.text_input_field.setProperty("canvas_x", (text_pos_screen.x() / self.canvas_scale) - self.canvas_offset.x())
                    self.text_input_field.setProperty("canvas_y", (text_pos_screen.y() / self.canvas_scale) - self.canvas_offset.y())
                    event.accept()
                    return
        
        elif self.placing_image:
            if self.current_image_element:
                # Resim manipülasyonu aktifken tıklama
                if event.button() == Qt.LeftButton or event.button() == Qt.RightButton:
                    # Sol veya sağ tuşla "yapıştırma" (kalıcı hale getirme)
                    self.undo_stack.append(list(self.all_frames_elements[self.current_frame_index]))
                    self.redo_stack.clear()
                    self.all_frames_elements[self.current_frame_index].append(self.current_image_element)
                    self.current_image_element = None # Geçici resmi temizle
                    self.placing_image = False # Resim yerleştirme modundan çık
                    self.setCursor(Qt.ArrowCursor) # İmleci varsayılana döndür
                    self.parent().updateButtonStyles() # Buton stilini güncelle
                    self.updateImageFromElements() # Çizimi güncelle
                    self.modified = True
                elif event.button() == Qt.MiddleButton:
                    # Orta tuşla resim taşıma başlat
                    self.image_panning = True
                    self.last_image_pan_pos = event.pos()
                    self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return # Resim modu işlendi, başka bir şey yapma
            # else: resim yeni yüklendi, ilk pozisyonu zaten ayarlanmış durumda.
            # İlk tıklamada manipülasyon başlamaz, sadece resim görünür olur.
            # Kullanıcı orta tuş veya tekerlek ile manipülasyonu başlatır.

        # Normal çizim veya tuval panlama
        if event.button() == Qt.LeftButton:
            # Mevcut kare için undo yığınına ekle
            self.undo_stack.append(list(self.all_frames_elements[self.current_frame_index]))
            self.redo_stack.clear()
            # Fare konumunu tuval koordinatlarına dönüştür
            self.lastPoint = QPoint(int((event.pos().x() / self.canvas_scale) - self.canvas_offset.x()),
                                    int((event.pos().y() / self.canvas_scale) - self.canvas_offset.y()))
            self.drawing = True
            self.current_stroke_points = [self.lastPoint]
            # İlk nokta için kalem bilgisini kaydet (farede basınç yok, varsayılan kalem kullan)
            pen_color, pen_width = self.getCurrentPen()
            self.current_stroke_pen_info = [[pen_color, pen_width]] 
        elif event.button() == Qt.MiddleButton: # Orta tuşla pan başlat
            self.panning = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.RightButton: # Sağ tıklama menüsü
            self.contextMenuEvent(event) # contextMenuEvent'i çağır
            event.accept()

    def mouseMoveEvent(self, event):
        if self.text_panning and self.current_text_element: # Metin taşıma devam ediyorsa
            delta = event.pos() - self.last_text_pan_pos
            # Metin pozisyonunu tuval koordinatlarında güncelle
            current_x = self.current_text_element["position"][0]
            current_y = self.current_text_element["position"][1]
            new_x = current_x + int(delta.x() / self.canvas_scale)
            new_y = current_y + int(delta.y() / self.canvas_scale)
            self.current_text_element["position"] = [new_x, new_y]
            self.last_text_pan_pos = event.pos()
            self.update() # Sadece geçici öğeyi güncelle
            event.accept()
            return
        
        elif self.image_panning and self.current_image_element: # Resim taşıma devam ediyorsa
            delta = event.pos() - self.last_image_pan_pos
            # Resim pozisyonunu tuval koordinatlarında güncelle
            current_x = self.current_image_element["position"][0]
            current_y = self.current_image_element["position"][1]
            new_x = current_x + int(delta.x() / self.canvas_scale)
            new_y = current_y + int(delta.y() / self.canvas_scale)
            self.current_image_element["position"] = [new_x, new_y]
            self.last_image_pan_pos = event.pos()
            self.update() # Sadece geçici öğeyi güncelle
            event.accept()
            return

        if self.panning: # Tuval pan işlemi devam ediyorsa
            delta = event.pos() - self.last_pan_pos
            # Offset'i canvas_scale'e bölerek dünya koordinatlarında hareket et
            self.canvas_offset += QPoint(int(delta.x() / self.canvas_scale), int(delta.y() / self.canvas_scale))
            self.last_pan_pos = event.pos()
            self.update()
            event.accept()
            return

        if (event.buttons() & Qt.LeftButton) and self.drawing:
            # Fare konumunu tuval koordinatlarına dönüştür
            current_point_canvas = QPoint(int((event.pos().x() / self.canvas_scale) - self.canvas_offset.x()),
                                          int((event.pos().y() / self.canvas_scale) - self.canvas_offset.y()))
            self.current_stroke_points.append(current_point_canvas)
            # Fare için basınç hassasiyeti devre dışı olduğundan,
            # fırça rengi ve genişliğini her zaman geçerli ayarlardan al.
            pen_color, pen_width = self.getCurrentPen()
            self.current_stroke_pen_info.append([pen_color, pen_width]) # Kalem bilgisini de ekle
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            if self.text_panning: # Metin taşıma bitiyorsa
                self.text_panning = False
                self.setCursor(Qt.ArrowCursor)
                event.accept()
                return
            elif self.image_panning: # Resim taşıma bitiyorsa
                self.image_panning = False
                # Resim manipülasyonu bitse de, kullanıcı hala resmi yapıştırmadıysa imleci taşıma imlecinde tut.
                # Ancak, kullanıcı "yapıştır" düğmesine bastığında imleç otomatik olarak ArrowCursor'a dönecek.
                self.setCursor(Qt.SizeAllCursor) 
                event.accept()
                return
            elif self.panning: # Tuval pan işlemi bitiyorsa
                self.panning = False
                self.setCursor(Qt.ArrowCursor)
                event.accept()
                return

        if event.button() == Qt.LeftButton and self.drawing:
            # Basınç hassasiyeti etkinse, `current_stroke_pen_info`'dan ortalama bir genişlik al.
            # Basınç hassasiyeti etkin değilse, `self.pen_radius` kullan.
            if self.pen_pressure_enabled and self.current_stroke_pen_info:
                avg_width = sum(p[1] for p in self.current_stroke_pen_info) / len(self.current_stroke_pen_info)
                color_to_save = self.current_stroke_pen_info[0][0]
            else:
                color_to_save, avg_width = self.getCurrentPen() # Normal kalem rengi ve genişliği

            self.all_frames_elements[self.current_frame_index].append({
                "type": "stroke",
                "points": [[p.x(), p.y()] for p in self.current_stroke_points],
                "color": [color_to_save.red(), color_to_save.green(), color_to_save.blue(), color_to_save.alpha()],
                "width": avg_width,
                "pressure_enabled": self.pen_pressure_enabled,
            })
            self.current_stroke_points = []
            self.current_stroke_pen_info = [] # Geçici kalem bilgilerini temizle
            self.drawing = False
            self.updateImageFromElements() # Çizim bittiğinde önbelleği güncelle

    def wheelEvent(self, event):
        if self.text_mode and self.current_text_element:
            # Metin ölçeklendirme
            old_font_size = self.current_text_element["font_size"]
            zoom_factor = 1.0 + (event.angleDelta().y() / 120) * 0.1 # Daha küçük adımlar için 0.1 ile çarpıyoruz.
            
            new_font_size = max(5, min(200, int(old_font_size * zoom_factor))) # Minimum 5, maksimum 200 font boyutu
            
            if new_font_size != old_font_size:
                # Metnin merkezini koruyarak yeniden konumlandır
                text_content = self.current_text_element["content"]
                
                # Eski font metrikleri
                old_font = QFont("Arial", old_font_size)
                old_metrics = QFontMetrics(old_font)
                old_width = old_metrics.width(text_content)
                old_height = old_metrics.height()
                
                # Yeni font metrikleri
                new_font = QFont("Arial", new_font_size)
                new_metrics = QFontMetrics(new_font)
                new_width = new_metrics.width(text_content)
                new_height = new_metrics.height()

                # Metnin mevcut pozisyonu (sol üst köşe)
                current_x = self.current_text_element["position"][0]
                current_y = self.current_text_element["position"][1]

                # Metnin merkezini hesapla (tuval koordinatlarında)
                center_x = current_x + old_width / 2
                center_y = current_y + old_height / 2

                # Yeni sol üst köşeyi hesapla (merkezi koruyarak)
                new_x = center_x - new_width / 2
                new_y = center_y - new_height / 2
                
                self.current_text_element["font_size"] = new_font_size
                self.current_text_element["position"] = [int(new_x), int(new_y)]
                self.update() # Sadece geçici öğeyi güncelle
            event.accept()
            return
        
        elif self.placing_image and self.current_image_element:
            # Resim ölçeklendirme (sınırsız)
            old_width = self.current_image_element["current_width"]
            old_height = self.current_image_element["current_height"]
            
            # Orijinal genişlik ve yükseklik
            original_width = self.current_image_element["original_width"]
            original_height = self.current_image_element["original_height"]

            zoom_factor = 1.0 + (event.angleDelta().y() / 120) * 0.1 # Daha küçük adımlar için 0.1 ile çarpıyoruz.
            
            new_width = int(old_width * zoom_factor)
            new_height = int(old_height * zoom_factor)

            # Minimum boyut kontrolü (çok küçük olmasını engellemek için)
            min_dim = 5 # Minimum 5x5 piksel
            if new_width < min_dim or new_height < min_dim:
                # Oranına göre minimum boyutu ayarla
                if original_width > original_height:
                    new_width = min_dim
                    new_height = int(min_dim * (original_height / original_width))
                else:
                    new_height = min_dim
                    new_width = int(min_dim * (original_width / original_height))
                # Eğer hala sıfır olursa, 1 yap
                if new_width == 0: new_width = 1
                if new_height == 0: new_height = 1


            if new_width != old_width or new_height != old_height:
                # Resmin merkezini koruyarak yeniden konumlandır
                current_x = self.current_image_element["position"][0]
                current_y = self.current_image_element["position"][1]

                center_x = current_x + old_width / 2
                center_y = current_y + old_height / 2

                new_x = center_x - new_width / 2
                new_y = center_y - new_height / 2

                self.current_image_element["current_width"] = new_width
                self.current_image_element["current_height"] = new_height
                self.current_image_element["position"] = [int(new_x), int(new_y)]
                self.update() # Sadece geçici öğeyi güncelle
            event.accept()
            return

        # Tuval zoom'u
        old_scale = self.canvas_scale
        # Standart fare tekerleği delta değeri 120'dir. Daha küçük adımlar için 0.1 ile çarpıyoruz.
        zoom_factor = 1.0 + (event.angleDelta().y() / 120) * 0.1 
        
        new_scale = max(self.min_canvas_scale, min(self.max_canvas_scale, old_scale * zoom_factor))
        
        # Fare pozisyonunu tuval koordinatlarına dönüştür (zoom'dan önce)
        mouse_pos_canvas_x = (event.pos().x() / old_scale) - self.canvas_offset.x()
        mouse_pos_canvas_y = (event.pos().y() / old_scale) - self.canvas_offset.y()

        self.canvas_scale = new_scale

        # Yeni offset'i hesapla, böylece fare imlecinin altındaki nokta aynı kalır
        # Sonuçları int'e dönüştürerek TypeError'ı engelle
        self.canvas_offset.setX(int((event.pos().x() / new_scale) - mouse_pos_canvas_x))
        self.canvas_offset.setY(int((event.pos().y() / new_scale) - mouse_pos_canvas_y))

        self.update()
        event.accept()


    def tabletEvent(self, event):
        # Eğer metin, resim yerleştirme veya renk seçme modundaysak tablet olaylarını devre dışı bırak
        if self.text_mode or self.placing_image or self.picking_color:
            return
        
        # Kalem tuşlarının durumunu güncelle
        if event.type() == QTabletEvent.TabletPress:
            if event.button() == Qt.NoButton: # Kalem ucu
                self.tablet_button_1_pressed = False
                self.tablet_button_2_pressed = False
                self.undo_stack.append(list(self.all_frames_elements[self.current_frame_index]))
                self.redo_stack.clear()
                # Tablet konumunu tuval koordinatlarına dönüştür
                self.lastPoint = QPoint(int((event.pos().x() / self.canvas_scale) - self.canvas_offset.x()),
                                        int((event.pos().y() / self.canvas_scale) - self.canvas_offset.y()))
                self.drawing = True
                self.current_stroke_points = [self.lastPoint]
                # Tablet basıncına göre ilk kalem bilgilerini kaydet
                pen_color = QColor("#333") if self.eraser_mode else self.pen_color
                # Minimum genişlik 1 olmalı
                pen_width = max(1, int(self.pen_radius * event.pressure())) if self.pen_pressure_enabled else self.pen_radius
                self.current_stroke_pen_info = [[pen_color, pen_width]]
                event.accept()
            elif event.button() == Qt.BackButton: # Genellikle 1. tuş (geri tuşu)
                # Shift veya Ctrl tuşları basılıysa zoom, değilse pan
                if event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier):
                    self.tablet_button_2_pressed = True # Zoom modunu aktif et
                    self.last_zoom_pos = event.pos() # Zoom için başlangıç pozisyonu
                    self.setCursor(Qt.SizeVerCursor) # Dikey yeniden boyutlandırma imleci (zoom için görsel ipucu)
                else:
                    self.tablet_button_1_pressed = True # Pan modunu aktif et
                    self.last_pan_pos = event.pos() # Pan için başlangıç pozisyonu
                    self.setCursor(Qt.ClosedHandCursor) # İmleci kapalı ele çevir
                event.accept()
            elif event.button() == Qt.ForwardButton: # Genellikle 2. tuş (ileri tuşu)
                # Bu tuşa özel bir işlev atanmadı, şimdilik yoksay.
                event.ignore()

        elif event.type() == QTabletEvent.TabletMove:
            if self.drawing:
                # Tablet konumunu tuval koordinatlarına dönüştür
                current_point_canvas = QPoint(int((event.pos().x() / self.canvas_scale) - self.canvas_offset.x()),
                                              int((event.pos().y() / self.canvas_scale) - self.canvas_offset.y()))
                self.drawTabletLineTo(current_point_canvas, event.pressure())
                event.accept()
            elif self.tablet_button_1_pressed: # 1. tuş basılıysa pan yap
                delta = event.pos() - self.last_pan_pos
                self.canvas_offset += QPoint(int(delta.x() / self.canvas_scale), int(delta.y() / self.canvas_scale))
                self.last_pan_pos = event.pos()
                self.update()
                event.accept()
            elif self.tablet_button_2_pressed: # 2. tuş basılıysa zoom yap (Shift/Ctrl ile 1. tuş)
                old_scale = self.canvas_scale
                # Y eksenindeki harekete göre zoom yap
                delta_y = event.pos().y() - self.last_zoom_pos.y()
                # Delta_y'yi daha küçük bir faktörle çarp (hassasiyet ayarı)
                zoom_factor = 1.0 + (-delta_y / 100.0) * 0.1 # Yukarı hareket yakınlaştırır, aşağı hareket uzaklaştırır
                
                new_scale = max(self.min_canvas_scale, min(self.max_canvas_scale, old_scale * zoom_factor))
                
                # Fare pozisyonunu tuval koordinatlarına dönüştür (zoom'dan önce)
                mouse_pos_canvas_x = (event.pos().x() / old_scale) - self.canvas_offset.x()
                mouse_pos_canvas_y = (event.pos().y() / old_scale) - self.canvas_offset.y()

                self.canvas_scale = new_scale

                # Yeni offset'i hesapla, böylece fare imlecinin altındaki nokta aynı kalır
                self.canvas_offset.setX(int((event.pos().x() / new_scale) - mouse_pos_canvas_x))
                self.canvas_offset.setY(int((event.pos().y() / new_scale) - mouse_pos_canvas_y))

                self.last_zoom_pos = event.pos() # Son zoom pozisyonunu güncelle
                self.update()
                event.accept()

        elif event.type() == QTabletEvent.TabletRelease:
            if self.drawing:
                # Tablet olaylarında da mouseReleaseEvent'teki aynı kaydetme mantığını kullan.
                # Tek bir stroke öğesi olarak kaydediyoruz.
                if self.pen_pressure_enabled and self.current_stroke_pen_info:
                    avg_width = sum(p[1] for p in self.current_stroke_pen_info) / len(self.current_stroke_pen_info)
                    color_to_save = self.current_stroke_pen_info[0][0]
                else:
                    color_to_save, avg_width = self.getCurrentPen() # Normal kalem rengi ve genişliği

                self.all_frames_elements[self.current_frame_index].append({
                    "type": "stroke",
                    "points": [[p.x(), p.y()] for p in self.current_stroke_points],
                    "color": [color_to_save.red(), color_to_save.green(), color_to_save.blue(), color_to_save.alpha()],
                    "width": avg_width,
                    "pressure_enabled": self.pen_pressure_enabled, 
                })
                self.current_stroke_points = []
                self.current_stroke_pen_info = [] # Kalem bilgilerini de temizle
                self.drawing = False
                self.updateImageFromElements()
                event.accept()
            elif event.button() == Qt.BackButton: # 1. tuş bırakıldı
                self.tablet_button_1_pressed = False
                self.tablet_button_2_pressed = False # Her iki zoom/pan modunu da kapat
                self.setCursor(Qt.ArrowCursor) # İmleci normale döndür
                event.accept()
            elif event.button() == Qt.ForwardButton: # 2. tuş bırakıldı
                self.tablet_button_1_pressed = False # Her iki zoom/pan modunu da kapat
                self.tablet_button_2_pressed = False
                self.setCursor(Qt.ArrowCursor) # İmleci normale döndür
                event.accept()

    def drawTabletLineTo(self, endPoint, pressure):
        # Geçici fırça vuruşuna noktayı ekle
        self.current_stroke_points.append(endPoint)
        pen_color = QColor("#333") if self.eraser_mode else self.pen_color
        # Minimum genişlik 1 olmalı
        pen_width = max(1, int(self.pen_radius * pressure)) if self.pen_pressure_enabled else self.pen_radius
        self.current_stroke_pen_info.append([pen_color, pen_width]) # Kalem bilgisini de ekle
        self.update() # Anlık çizimi göstermek için güncelle

    def addTextToDrawing(self):
        text = self.text_input_field.text()
        if text:
            # Metin input alanının tuval koordinatlarını al
            text_pos_canvas_x = self.text_input_field.property("canvas_x")
            text_pos_canvas_y = self.text_input_field.property("canvas_y")

            font_size = max(10, self.pen_radius * 2) # Başlangıç font boyutu
            text_color = [self.pen_color.red(), self.pen_color.green(), self.pen_color.blue(), self.pen_color.alpha()]
            
            # current_text_element'ı oluştur ve manipülasyon için hazırla
            self.current_text_element = {
                "type": "text",
                "content": text,
                "position": [int(text_pos_canvas_x), int(text_pos_canvas_y)], # Tuval koordinatlarını kullan
                "font_size": font_size,
                "color": text_color
            }
            self.setCursor(Qt.SizeAllCursor) # Taşıma imleci göster
            self.update() # Dinamik metni göstermek için güncelle
        self.text_input_field.hide()
        self.text_input_field.clear()

    def updateImageFromElements(self):
        """Mevcut karenin içeriğini günceller ve ekranı yeniden çizer."""
        # Önbelleği güncelle
        self.cached_frame_image = self._renderFrameToImage(self.current_frame_index)
        self.cached_frame_index = self.current_frame_index
        self.update() # paintEvent'i tetikler

    def clearCurrentFrame(self):
        """Mevcut karenin içeriğini temizler."""
        if self.total_frames > 0:
            self.undo_stack.append(list(self.all_frames_elements[self.current_frame_index]))
            self.redo_stack.clear()
            self.all_frames_elements[self.current_frame_index].clear()
            self.updateImageFromElements() # Kare temizlendiğinde önbelleği güncelle

    def clearAllFrames(self):
        # Bu fonksiyon artık doğrudan kullanılmıyor, menüden çağrılmıyor.
        # Eğer kullanılacaksa, onay penceresi kaldırılmalı veya isteğe bağlı hale getirilmeli.
        ret = QMessageBox.question(
            self, "Tüm Kareleri Temizle",
            "Tüm kareleri temizlemek istediğinizden emin misiniz? Bu işlem geri alınamaz.",
            QMessageBox.Yes | QMessageBox.No
        )
        if ret == QMessageBox.Yes:
            self.all_frames_elements = [[] for _ in range(self.total_frames)]
            self.current_frame_index = 0
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.updateImageFromElements() # Tüm kareler temizlendiğinde önbelleği güncelle

    def undo(self):
        # Undo/Redo mevcut karedeki öğeler için çalışır
        if self.undo_stack:
            self.redo_stack.append(list(self.all_frames_elements[self.current_frame_index]))
            self.all_frames_elements[self.current_frame_index] = self.undo_stack.pop()
            self.updateImageFromElements() # Undo yapıldığında önbelleği güncelle

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(list(self.all_frames_elements[self.current_frame_index]))
            self.all_frames_elements[self.current_frame_index] = self.redo_stack.pop()
            self.updateImageFromElements() # Redo yapıldığında önbelleği güncelle

    def getCurrentPen(self):
        """Mevcut kalem rengini ve kalınlığını döndürür."""
        color = QColor("#333") if self.eraser_mode else self.pen_color
        return color, self.pen_radius

    def contextMenuEvent(self, event):
        """Sağ tıklama menüsünü oluşturur ve gösterir."""
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { color: white; background-color: #333; border: 1px solid #555; }"
                           "QMenu::item:selected { background-color: #555; color: white; }")

        # Mevcut karedeki tüm renkleri topla
        available_colors = set()
        for element in self.all_frames_elements[self.current_frame_index]:
            if element["type"] == "stroke" or element["type"] == "text": # Metin renklerini de dahil et
                if "color" in element: # Renk özelliği olanları kontrol et
                    color_list = element["color"]
                    available_colors.add(tuple(color_list)) # Listeyi tuple'a çevirerek hashlenebilir yap

        # "Copy Elements by Color to Next Frame" menüsü
        if available_colors:
            color_copy_menu = menu.addMenu("Copy Elements by Color to Next Frame")
            color_copy_menu.setStyleSheet("QMenu { color: white; background-color: #333; border: 1px solid #555; }"
                                          "QMenu::item:selected { background-color: #555; color: white; }")

            from PyQt5.QtGui import QPixmap, QIcon # QPixmap ve QIcon burada tanımlandı
            for color_tuple in sorted(list(available_colors)):
                qcolor = QColor(*color_tuple)
                color_name = qcolor.name() # Renk kodunu al (#RRGGBB)
                action = QAction(f"Copy {color_name}", self)
                # Renk kutusu eklemek için bir pixmap oluştur
                pixmap = QPixmap(16, 16)
                pixmap.fill(qcolor)
                action.setIcon(QIcon(pixmap))
                action.triggered.connect(lambda checked, c=color_tuple: self.parent().copyElementsToNextFrameByColor(c)) # Parent'taki metodu çağır
                color_copy_menu.addAction(action)
        else:
            no_color_copy_action = QAction("No colored elements to copy", self)
            no_color_copy_action.setEnabled(False)
            menu.addAction(no_color_copy_action)

        menu.addSeparator() # Ayırıcı ekle

        # "Delete Elements by Color" menüsü
        if available_colors:
            color_delete_menu = menu.addMenu("Delete Elements by Color")
            color_delete_menu.setStyleSheet("QMenu { color: white; background-color: #333; border: 1px solid #555; }"
                                            "QMenu::item:selected { background-color: #555; color: white; }")
            for color_tuple in sorted(list(available_colors)):
                qcolor = QColor(*color_tuple)
                color_name = qcolor.name() # Renk kodunu al (#RRGGBB)
                action = QAction(f"Delete {color_name}", self)
                pixmap = QPixmap(16, 16)
                pixmap.fill(qcolor)
                action.setIcon(QIcon(pixmap))
                action.triggered.connect(lambda checked, c=color_tuple: self.parent().deleteElementsByColor(c)) # Parent'taki metodu çağır
                color_delete_menu.addAction(action)
        else:
            no_color_delete_action = QAction("No colored elements to delete", self)
            no_color_delete_action.setEnabled(False)
            menu.addAction(no_color_delete_action)

        menu.addSeparator() # Ayırıcı ekle

        # "Pick Color (Eyedropper)" seçeneği
        pick_color_action = QAction("Pick Color (Eyedropper)", self)
        pick_color_action.triggered.connect(self.parent().startColorPicking) # Parent'taki metodu çağır
        menu.addAction(pick_color_action)

        menu.exec_(event.globalPos()) # Menüyü fare konumunda göster

    def startColorPicking(self):
        """Renk seçme (damlalık) modunu başlatır."""
        # Bu metod artık DrawingArea'nın içinde değil, DrawingEditorWindow'da olmalı
        # Çünkü modları ve imleci DrawingEditorWindow yönetiyor.
        pass # Bu metod DrawingEditorWindow'a taşındı


    def copyElementsToNextFrameByColor(self, target_color_tuple):
        """Belirtilen renkteki öğeleri bir sonraki kareye kopyalar."""
        # Bu metod artık DrawingArea'nın içinde değil, DrawingEditorWindow'da olmalı
        # Çünkü DrawingArea'nın total_frames ve diğer DrawingEditorWindow özelliklerine doğrudan erişimi yok.
        pass # Bu metod DrawingEditorWindow'a taşındı

    def deleteElementsByColor(self, target_color_tuple):
        """Belirtilen renkteki öğeleri mevcut kareden siler."""
        # Bu metod artık DrawingArea'nın içinde değil, DrawingEditorWindow'da olmalı
        # Çünkü DrawingArea'nın total_frames ve diğer DrawingEditorWindow özelliklerine doğrudan erişimi yok.
        pass # Bu metod DrawingEditorWindow'a taşındı


# Zaman çizelgesi için özel widget
class TimelineWidget(QFrame):
    frameChanged = pyqtSignal(int) # Özel sinyal tanımlandı

    def __init__(self, total_frames, animation_fps, animation_duration, drawing_area_ref, parent=None):
        super().__init__(parent)
        self.setFixedHeight(60) # Yüksekliği biraz artırıldı
        self.setStyleSheet("background-color: #1a1a1a;") # Daha koyu bir arka plan rengi

        self.total_frames = total_frames
        self.animation_fps = animation_fps
        self.animation_duration = animation_duration
        self.current_frame_index = 0 # Mevcut kareyi takip etmek için

        self.zoom_level = 1.0 # Zaman çizelgesi zoom seviyesi (şu an kullanılmıyor)
        self.min_zoom_level = 0.1
        self.max_zoom_level = 5.0

        self.dragging_timeline = False # Zaman çizelgesi sürükleme durumu
        self.drawing_area_ref = drawing_area_ref # DrawingArea referansı eklendi

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5) # Kenar boşlukları ayarlandı
        layout.setSpacing(0) # Öğeler arası boşluk kaldırıldı

    def _onSliderInternalChanged(self, value):
        # QSlider kaldırıldığı için bu metod artık doğrudan çağrılmayacak.
        # Bunun yerine mouse event'lerinden current_frame_index güncellenecek.
        self.current_frame_index = value
        self.frameChanged.emit(value) # Özel sinyali yay
        self.update() # Yeniden çiz

    def setSliderValue(self, value):
        # Bu metod, DrawingArea tarafından kaydırıcıyı güncellemek için çağrılacak
        # QSlider kaldırıldığı için doğrudan current_frame_index'i günceller
        if 0 <= value < self.total_frames:
            self.current_frame_index = value
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_timeline = True
            self.updateFrameFromMousePos(event.pos().x())
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging_timeline:
            self.updateFrameFromMousePos(event.pos().x())
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_timeline = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()

    def updateFrameFromMousePos(self, mouse_x):
        # Fare pozisyonuna göre kare indeksini hesapla
        # Widget'ın genişliğini kullanarak orantısal olarak hesaplama
        if self.total_frames > 1:
            # Kenar boşluklarını dikkate alarak etkin çizim genişliği
            effective_width = self.width() - 20 # 10px sol, 10px sağ boşluk
            if effective_width <= 0: return

            # Fare pozisyonunu etkin alana göre normalize et
            normalized_x = (mouse_x - 10) / effective_width # 10px sol boşluk
            normalized_x = max(0.0, min(1.0, normalized_x)) # 0 ile 1 arasında tut

            new_frame_index = int(normalized_x * (self.total_frames - 1))
            if new_frame_index != self.current_frame_index:
                self._onSliderInternalChanged(new_frame_index) # _onSliderInternalChanged'ı çağır

    def wheelEvent(self, event):
        # Zaman çizelgesini zoomlama özelliğini devre dışı bırak
        event.ignore()
        return


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Zaman çizelgesi çerçevesinin arka planını çiz
        painter.fillRect(self.rect(), QColor("#1a1a1a")) # Daha koyu arka plan

        # Kenar boşlukları
        padding_x = 10
        
        # Sayılar için üst çizim alanı
        numbers_y_pos = 15 # Rakamların dikey konumu (üstten)

        # Çizgiler için alt çizim alanı
        lines_y_start = self.height() - 25 # Çizgilerin başlangıç dikey konumu (alttan yukarı)
        lines_y_end = self.height() - 5 # Çizgilerin bitiş dikey konumu (en alt)

        # Saniye işaretleri ve gri şeritler
        if self.total_frames > 1:
            # Çizgilerin çizileceği toplam genişlik
            draw_width = self.width() - (2 * padding_x)
            if draw_width <= 0: draw_width = 1 # Negatif veya sıfır olmaması için kontrol

            for i in range(self.total_frames):
                # Kare pozisyonunu toplam çizim genişliğine göre hesapla
                x_pos = padding_x + int((i / (self.total_frames - 1)) * draw_width)
                
                # Her saniyede bir sayı ve daha kalın çizgi
                if i % self.animation_fps == 0:
                    # Sayı çizimi (üst kısımda)
                    second_text = str(i // self.animation_fps)
                    font = QFont("Arial", 8)
                    painter.setFont(font)
                    metrics = QFontMetrics(font)
                    text_width = metrics.width(second_text)
                    painter.setPen(QColor("#ffffff")) # Beyaz renk
                    painter.drawText(x_pos - text_width // 2, numbers_y_pos + metrics.height() // 2, second_text)

                    # Kalın çizgi (alt kısımda)
                    # Saniye işaretindeki karede çizim varsa sarı, yoksa beyaz
                    if self.drawing_area_ref and i < len(self.drawing_area_ref.all_frames_elements) and \
                       self.drawing_area_ref.all_frames_elements[i]:
                        painter.setPen(QPen(QColor("yellow"), 1.5)) # Sarı ve biraz kalın çizgi
                    else:
                        painter.setPen(QPen(QColor("#ffffff"), 1.5)) # Beyaz ve biraz kalın çizgi
                    painter.drawLine(x_pos, lines_y_start, x_pos, lines_y_end)
                else:
                    # FPS'ye göre ince dikey şeritler (alt kısımda)
                    # Çizilmiş kareler için sarı çizgi, diğerleri için gri şeritler
                    if self.drawing_area_ref and i < len(self.drawing_area_ref.all_frames_elements) and \
                       self.drawing_area_ref.all_frames_elements[i]:
                        painter.setPen(QPen(QColor("yellow"), 1.5)) # Sarı çizgi
                    elif (i % (self.animation_fps * 2) < self.animation_fps):
                        painter.setPen(QPen(QColor(40, 40, 40), 1)) # Koyu gri şerit
                    else:
                        # Hata veren satır düzeltildi: QPen nesnesi kullanıldı
                        painter.setPen(QPen(QColor(50, 50, 50), 1)) # Açık gri şerit
                    
                    painter.drawLine(x_pos, lines_y_start + 5, x_pos, lines_y_end - 5) # Biraz daha kısa çizgiler

        # Mevcut kare için kırmızı çizgiyi çiz
        if self.total_frames > 0:
            draw_width = self.width() - (2 * padding_x)
            if draw_width <= 0: draw_width = 1

            current_frame_x_pos = padding_x + int((self.current_frame_index / (self.total_frames - 1)) * draw_width)

            painter.setPen(QPen(QColor("red"), 2)) # Daha kalın kırmızı çizgi
            # Kırmızı çizgiyi tam olarak düz bir çizgi haline getir ve en alta çek
            painter.drawLine(current_frame_x_pos, lines_y_start, current_frame_x_pos, lines_y_end)


# SVG ikonlarını oluşturmak için yardımcı fonksiyon
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

# SVG ikon tanımları (sphere.py'den kopyalandı)
SVG_UNDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19C15.866 19 19 15.866 19 12C19 8.13401 15.866 5 12 5C8.13401 5 5 8.13401 5 12C5 13.7909 5.70014 15.4293 6.84594 16.6386L5 18M5 18H9M5 18V14" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_REDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5C8.13401 5 5 8.13401 5 12C5 15.866 8.13401 19 12 19C15.866 19 19 15.866 19 12C19 10.2091 18.2999 8.57074 17.1541 7.3614L19 6M19 6H15M19 6V10" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
# Geri sarma ve ileri sarma ikonları kaldırıldı.


# Çizim editörü penceresi
class DrawingEditorWindow(QWidget):
    DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')
    AUTOSAVE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Autosave')
    # C++ yürütülebilir dosyasının adı
    CPP_EXECUTABLE_NAME = "Anime_engine" 

    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        self.project_file_path = None

        self.animation_fps = 24
        self.animation_duration = 30
        self.total_frames = self.animation_fps * self.animation_duration
        self.current_play_frame = 0
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.advanceFrame)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(60 * 1000)
        self.autosave_timer.timeout.connect(self.autoSaveProject)
        self.autosave_timer.start()

        # _init_project'i çağır ve dönüş değerini kontrol et.
        # Eğer False dönerse, kullanıcı kurulumu iptal etmiştir.
        if not self._init_project(new_session=True):
            # Widget'ın kapatılmasını zamanla. 0ms'lik bir zamanlayıcı kullanmak,
            # bu işlemin constructor bittikten sonra yapılmasını sağlar.
            QTimer.singleShot(0, self.close)

    def _init_project(self, new_session=False, settings=None):
        """Proje ayarlarını başlatır veya günceller."""
        if new_session:
            dialog = AnimationSettingsDialog(self)
            if dialog.exec_():
                settings = dialog.getSettings()
            else:
                # Kullanıcı iptal etti. Başarısızlığı belirtmek için False döndür.
                # __init__ metodu widget'ı kapatmayı ele alacaktır.
                return False

        if settings:
            self.image_width = settings["width"]
            self.image_height = settings["height"]
            self.bg_color = QColor(*settings["background_color"])
            self.animation_fps = settings["fps"]
            self.animation_duration = settings["duration"]
            self.total_frames = self.animation_fps * self.animation_duration
            self.project_file_path = None
            
            if hasattr(self, 'drawing_area'):
                self.drawing_area.image_width = self.image_width
                self.drawing_area.image_height = self.image_height
                self.drawing_area.bg_color = self.bg_color
                self.drawing_area.setTotalFrames(self.total_frames)
                self.drawing_area.current_frame_index = 0
                self.drawing_area.undo_stack.clear()
                self.drawing_area.redo_stack.clear()
                self.drawing_area.current_text_element = None
                self.drawing_area.text_panning = False
                self.drawing_area.current_image_element = None
                self.drawing_area.image_panning = False
                self.drawing_area.setCursor(Qt.ArrowCursor)
                self.drawing_area.picking_color = False
                self.drawing_area.tablet_button_1_pressed = False
                self.drawing_area.tablet_button_2_pressed = False
                self.drawing_area.pen_color = QColor("white")
                self.drawing_area.pen_radius = 7
                self.drawing_area.eraser_mode = False
                self.drawing_area.pen_pressure_enabled = False
                self.drawing_area.text_mode = False
                self.drawing_area.placing_image = False 
                self.timeline_widget.total_frames = self.total_frames
                self.timeline_widget.animation_fps = self.animation_fps
                self.timeline_widget.animation_duration = self.animation_duration
                self.timeline_widget.setSliderValue(0)
            else:
                self.initUI()
            
            self.updateFrameInfoLabel()
            self.updateButtonStyles()
            return True
        
        return False

    def initUI(self):
        self.setWindowTitle("Kavram - Animasyon Düzenleyici")
        self.setStyleSheet("background-color: #222;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Çizim alanı (drawing_area) önce tanımlanmalı
        self.drawing_area = DrawingArea(self.image_width, self.image_height, self.bg_color, self.total_frames, self)

        # Üst araç çubuğu
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("background-color: #222; border-bottom: 2px solid #555;")
        toolbar_frame.setFixedHeight(40)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)

        self.file_button = QPushButton("File")
        self.file_button.setStyleSheet(self.buttonStyle())
        self.file_button.setFixedSize(90, 30)
        self.file_button.setMenu(self._createFileMenu()) # Menü atandı
        toolbar_layout.addWidget(self.file_button, alignment=Qt.AlignLeft)

        # Geri al butonu (Undo)
        self.undo_button = QPushButton()
        self.undo_button.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20))
        self.undo_button.setStyleSheet(self.buttonStyleMini())
        self.undo_button.setFixedSize(30, 30)
        self.undo_button.clicked.connect(self.undo) # Undo metoduna bağla
        toolbar_layout.addWidget(self.undo_button)

        # Yinele butonu (Redo)
        self.redo_button = QPushButton()
        self.redo_button.setIcon(create_svg_icon(SVG_REDO_ICON, size=20))
        self.redo_button.setStyleSheet(self.buttonStyleMini())
        self.redo_button.setFixedSize(30, 30)
        self.redo_button.clicked.connect(self.redo) # Redo metoduna bağla
        toolbar_layout.addWidget(self.redo_button)

        # Geri sarma ve ileri sarma butonları kaldırıldı.

        self.eraser_button = QPushButton("Eraser")
        self.eraser_button.setStyleSheet(self.buttonStyle())
        self.eraser_button.setFixedSize(95, 30)
        self.eraser_button.clicked.connect(self.toggleEraser)
        toolbar_layout.addWidget(self.eraser_button, alignment=Qt.AlignLeft)

        self.color_button = QPushButton("Color")
        self.color_button.setStyleSheet(self.buttonStyle())
        self.color_button.setFixedSize(90, 30)
        self.color_button.clicked.connect(self.changeColor)
        toolbar_layout.addWidget(self.color_button, alignment=Qt.AlignLeft)

        # Clear Frame butonu adı "Delete" olarak değiştirildi
        self.clear_frame_button = QPushButton("Delete")
        self.clear_frame_button.setStyleSheet(self.buttonStyle())
        self.clear_frame_button.setFixedSize(90, 30)
        # Bu buton artık sadece mevcut karenin içeriğini temizler
        self.clear_frame_button.clicked.connect(self.drawing_area.clearCurrentFrame)
        toolbar_layout.addWidget(self.clear_frame_button, alignment=Qt.AlignLeft)

        self.radius_button = QPushButton(f"Radius: {self.drawing_area.pen_radius}")
        self.radius_button.setStyleSheet(self.buttonStyle())
        self.radius_button.setFixedSize(100, 30)
        self.radius_button.clicked.connect(self.changeRadius)
        toolbar_layout.addWidget(self.radius_button, alignment=Qt.AlignLeft)

        # Pressure butonu boyutu küçültüldü
        self.pressure_button = QPushButton("/") 
        self.pressure_button.setStyleSheet(self.buttonStylePressure(False))
        self.pressure_button.setFixedSize(40, 30) # Boyut ayarlandı
        self.pressure_button.clicked.connect(self.togglePressure)
        toolbar_layout.addWidget(self.pressure_button, alignment=Qt.AlignLeft)

        # Text butonu boyutu küçültüldü
        self.text_button = QPushButton("A") 
        self.text_button.setStyleSheet(self.buttonStylePressure(False))
        self.text_button.setFixedSize(40, 30) # Boyut ayarlandı
        self.text_button.clicked.connect(self.toggleTextMode)
        toolbar_layout.addWidget(self.text_button, alignment=Qt.AlignLeft)

        # Play butonu
        self.play_button = QPushButton("Play")
        self.play_button.setStyleSheet(self.buttonStyle())
        self.play_button.setFixedSize(90, 30)
        self.play_button.clicked.connect(self.toggleAnimationPlayback)
        toolbar_layout.addWidget(self.play_button, alignment=Qt.AlignLeft)

        # Yeni Frame Info Label
        self.frame_info_label = QLabel(self)
        self.frame_info_label.setStyleSheet("color: #cccccc; font-size: 12px; margin-left: 20px;")
        toolbar_layout.addWidget(self.frame_info_label, alignment=Qt.AlignCenter)
        self.updateFrameInfoLabel() # Başlangıçta etiketi güncelle

        toolbar_layout.addStretch()

        # "Frame +" butonu artık doğrudan kare ekleme diyaloğunu açacak
        self.add_frames_button = QPushButton("Frame +")
        self.add_frames_button.setStyleSheet(self.buttonStyle())
        self.add_frames_button.setFixedSize(90, 30)
        self.add_frames_button.clicked.connect(self.addFrames) # Doğrudan addFrames metoduna bağla
        toolbar_layout.addWidget(self.add_frames_button, alignment=Qt.AlignRight)

        # Export butonu
        self.export_button = QPushButton("Export")
        self.export_button.setStyleSheet(self.buttonStyle())
        self.export_button.setFixedSize(90, 30)
        # Mouse olayını dinlemek için custom bir metod kullanıyoruz
        self.export_button.mousePressEvent = self.handleExportButtonPress # mousePressEvent'i override ettik
        toolbar_layout.addWidget(self.export_button, alignment=Qt.AlignRight)

        self.anime_button = QPushButton("Anime") 
        self.anime_button.setStyleSheet(self.buttonStyle())
        self.anime_button.setFixedSize(90, 30)
        self.anime_button.clicked.connect(self.triggerCoreSwitcher)
        toolbar_layout.addWidget(self.anime_button, alignment=Qt.AlignRight)

        main_layout.addWidget(toolbar_frame)

        # Çizim alanı
        main_layout.addWidget(self.drawing_area, 1) # Stretch factor 1 olarak ayarlandı

        # Zaman Çizelgesi (Timeline) - Yeni TimelineWidget kullanılıyor
        # TimelineWidget'a drawing_area referansı geçirildi
        self.timeline_widget = TimelineWidget(self.total_frames, self.animation_fps, self.animation_duration, self.drawing_area, self)
        self.timeline_widget.frameChanged.connect(self.onTimelineChanged) # Custom sinyale bağlan
        
        main_layout.addWidget(self.timeline_widget)

        self.setLayout(main_layout)

        # Ekran boyutunu al ve başlangıç boyutunu dinamik olarak ayarla
        screen = QApplication.primaryScreen().geometry()
        # Ekranın %80'i kadar bir başlangıç boyutu belirle, ancak maksimum 1280x720 olsun
        initial_width = min(1280, int(screen.width() * 0.8))
        initial_height = min(720, int(screen.height() * 0.8))
        self.resize(initial_width, initial_height) # Dinamik başlangıç boyutunu ayarla

        self.setMinimumSize(600, 400) # Makul bir minimum boyut belirle
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Ana pencerenin genişlemesine izin ver

        # Pencereyi ortala
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        # Kısayollar
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self.redo)
        QShortcut(QKeySequence(Qt.Key_Left), self, self.prevFrame)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.nextFrame)

    def _createFileMenu(self):
        """File butonu için menü oluşturur."""
        file_menu = QMenu(self)
        # Menüdeki yazı rengini beyaz yapmak için stil eklendi
        file_menu.setStyleSheet("QMenu { color: white; background-color: #333; border: 1px solid #555; }"
                                "QMenu::item:selected { background-color: #555; color: white; }")

        new_action = QAction("New Project", self)
        new_action.triggered.connect(self.newProject)
        file_menu.addAction(new_action)

        open_action = QAction("Open Project", self)
        open_action.triggered.connect(self.loadProject)
        file_menu.addAction(open_action)

        save_action = QAction("Save Project", self)
        save_action.triggered.connect(self.saveProject)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        file_menu.addAction(save_action)

        save_as_action = QAction("Save Project As...", self)
        save_as_action.triggered.connect(self.saveProjectAs)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        import_action = QAction("Import File...", self)
        import_action.triggered.connect(self.importFile)
        file_menu.addAction(import_action)

        # Yeni "Delete Frames After Current" eylemi eklendi
        delete_after_current_action = QAction("Delete Frames After Current", self)
        delete_after_current_action.triggered.connect(self.deleteFramesAfterCurrent)
        file_menu.addAction(delete_after_current_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        return file_menu

    def newProject(self):
        """Yeni bir animasyon projesi başlatır."""
        # Mevcut çalışmayı kaydetmek isteyip istemediğini sor
        if self.drawing_area.modified: # Eğer çizim alanında değişiklik varsa
            reply = QMessageBox.question(self, "New Project",
                                         "Mevcut projeyi kaydetmek ister misiniz?",
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if reply == QMessageBox.Save:
                if not self.saveProject(): # Kaydetme başarısız olursa veya iptal edilirse
                    return
            elif reply == QMessageBox.Cancel:
                return
        
        self._init_project(new_session=True) # Yeni proje ayarlarını sorarak başlat
        self.setWindowTitle("Kavram - Animasyon Düzenleyici (Untitled)") # Başlığı sıfırla


    def saveProject(self):
        """Mevcut projeyi kaydeder."""
        if not self.project_file_path:
            return self.saveProjectAs() # Eğer daha önce kaydedilmemişse "Farklı Kaydet"i çağır
        
        try:
            project_data = {
                "project_settings": {
                    "width": self.image_width,
                    "height": self.image_height,
                    "background_color": [self.bg_color.red(), self.bg_color.green(), self.bg_color.blue(), self.bg_color.alpha()],
                    "fps": self.animation_fps,
                    "duration": self.animation_duration,
                    "total_frames": self.total_frames
                },
                "frames_data": self.drawing_area.all_frames_elements
            }
            with open(self.project_file_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=4)
            self.drawing_area.modified = False # Kaydedildi olarak işaretle
            self.setWindowTitle(f"Kavram - Animasyon Düzenleyici ({os.path.basename(self.project_file_path)})")
            return True
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Proje kaydedilirken hata oluştu: {e}")
            return False

    def saveProjectAs(self):
        """Projeyi yeni bir isimle kaydeder."""
        QDir().mkpath(DrawingEditorWindow.DEFAULT_BASE_DIR)
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Projeyi Farklı Kaydet", DrawingEditorWindow.DEFAULT_BASE_DIR,
            "Kavram Projesi (*.kavram);;Tüm Dosyalar (*)",
            options=options
        )
        if file_path:
            if not file_path.lower().endswith(".kavram"):
                file_path += ".kavram"
            self.project_file_path = file_path
            return self.saveProject() # Yeni yola kaydet

        return False # Kullanıcı iptal etti

    def loadProject(self):
        """Kaydedilmiş bir projeyi yükler."""
        # Mevcut çalışmayı kaydetmek isteyip istemediğini sor
        if self.drawing_area.modified:
            reply = QMessageBox.question(self, "Open Project",
                                         "Mevcut projeyi kaydetmek ister misiniz?",
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if reply == QMessageBox.Save:
                if not self.saveProject():
                    return
            elif reply == QMessageBox.Cancel:
                return

        QDir().mkpath(DrawingEditorWindow.DEFAULT_BASE_DIR)
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Proje Yükle", DrawingEditorWindow.DEFAULT_BASE_DIR,
            "Kavram Projesi (*.kavram);;Tüm Dosyalar (*)",
            options=options

        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)
                
                settings = project_data.get("project_settings", {})
                frames_data = project_data.get("frames_data", [])

                # Yeni ayarları uygula
                self._init_project(new_session=False, settings=settings)

                # Kare verilerini yükle
                self.drawing_area.all_frames_elements = frames_data
                self.drawing_area.total_frames = len(frames_data)
                self.drawing_area.current_frame_index = 0 # İlk kareye git
                self.drawing_area.updateImageFromElements()
                self.drawing_area.undo_stack.clear()
                self.drawing_area.redo_stack.clear()
                self.drawing_area.modified = False # Yüklendiği için değiştirilmedi olarak işaretle
                # Yükleme sırasında geçici metni ve resmi temizle
                self.drawing_area.current_text_element = None
                self.drawing_area.text_panning = False
                self.drawing_area.current_image_element = None
                self.drawing_area.image_panning = False
                self.drawing_area.setCursor(Qt.ArrowCursor)
                self.drawing_area.picking_color = False # Renk seçme modunu sıfırla
                # Tablet tuş durumlarını sıfırla
                self.drawing_area.tablet_button_1_pressed = False
                self.drawing_area.tablet_button_2_pressed = False


                self.timeline_widget.total_frames = self.drawing_area.total_frames
                self.timeline_widget.animation_fps = self.animation_fps
                self.timeline_widget.animation_duration = self.drawing_area.total_frames / self.animation_fps
                self.timeline_widget.setSliderValue(0)
                self.updateFrameInfoLabel()
                self.updateButtonStyles()

                self.project_file_path = file_path
                self.setWindowTitle(f"Kavram - Animasyon Düzenleyici ({os.path.basename(self.project_file_path)})")
            except Exception as e:
                QMessageBox.critical(self, "Load Error", f"Proje yüklenirken hata oluştu: {e}")

    def autoSaveProject(self):
        """Projeyi otomatik olarak kaydeder."""
        if not self.drawing_area.modified: # Değişiklik yoksa kaydetme
            return

        QDir().mkpath(DrawingEditorWindow.AUTOSAVE_DIR)
        
        # Eğer proje kaydedilmemişse, isimsiz bir autosave dosyası oluştur
        autosave_filename = "untitled_autosave.kavram"
        if self.project_file_path:
            base_name = os.path.basename(self.project_file_path).replace(".kavram", "")
            autosave_filename = f"{base_name}_autosave.kavram"
        
        autosave_path = os.path.join(DrawingEditorWindow.AUTOSAVE_DIR, autosave_filename)

        try:
            project_data = {
                "project_settings": {
                    "width": self.image_width,
                    "height": self.image_height,
                    "background_color": [self.bg_color.red(), self.bg_color.green(), self.bg_color.blue(), self.bg_color.alpha()],
                    "fps": self.animation_fps,
                    "duration": self.animation_duration,
                    "total_frames": self.total_frames
                },
                "frames_data": self.drawing_area.all_frames_elements
            }
            with open(autosave_path, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=4)
            print(f"Otomatik kaydetme başarılı: {autosave_path}")
        except Exception as e:
            print(f"Otomatik kaydetme hatası: {e}")


    def buttonStyle(self):
        return """
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 5px 10px; /* Padding ayarlandı */
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
            QPushButton::menu-indicator { image: none; } /* Menü göstergesini kaldır */
        """

    def buttonStyleMini(self):
        # sphere.py'deki buttonStyleMini'den kopyalandı
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
                    background-color: #555;
                    color: white;
                    font-size: 14px; /* Font boyutu ayarlandı */
                    border: 2px solid #555;
                    border-radius: 8px; /* Radius ayarlandı */
                    padding: 5px 10px; /* Padding ayarlandı */
                }
            """
        else:
            return """
                QPushButton {
                    background-color: transparent;
                    color: white;
                    font-size: 14px; /* Font boyutu ayarlandı */
                    border: 2px solid #555;
                    border-radius: 8px; /* Radius ayarlandı */
                    padding: 5px 10px; /* Padding ayarlandı */
                }
                QPushButton:hover { background-color: #444; }
                QPushButton:pressed { background-color: #666; }
            """

    def wheelEvent(self, event):
        # Bu wheelEvent artık DrawingArea'ya iletilmiyor, DrawingArea kendi zoom'unu yönetiyor.
        # Bu metot devre dışı bırakıldı, çünkü DrawingArea'nın kendi wheelEvent'i var.
        event.ignore() # Olayı daha alt widget'lara iletmez.

    def importFile(self):
        options = QFileDialog.Options()
        file_filter = "Desteklenen Dosyalar (*.drawing *.png *.jpg *.jpeg *.bmp *.gif);;Drawing Dosyaları (*.drawing);;Görsel Dosyaları (*.png *.jpg *.jpeg *.bmp *.gif);;Tüm Dosyalar (*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Drawing veya Görsel İçe Aktar", DrawingEditorWindow.DEFAULT_BASE_DIR,
            file_filter,
            options=options
        )
        if file_path:
            # İçe aktarım yapmadan önce tüm modları kapat
            self.drawing_area.picking_color = False
            self.drawing_area.text_mode = False
            self.drawing_area.eraser_mode = False
            self.drawing_area.text_input_field.hide()
            self.drawing_area.current_text_element = None
            self.drawing_area.text_panning = False
            self.drawing_area.current_image_element = None
            self.drawing_area.image_panning = False
            self.drawing_area.setCursor(Qt.ArrowCursor)
            # Tablet tuş durumlarını sıfırla
            self.drawing_area.tablet_button_1_pressed = False
            self.drawing_area.tablet_button_2_pressed = False


            if file_path.lower().endswith(".drawing"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        drawing_data = json.load(f)
                    if self.drawing_area.current_frame_index < len(self.drawing_area.all_frames_elements):
                        self.drawing_area.all_frames_elements[self.drawing_area.current_frame_index] = drawing_data
                        self.drawing_area.updateImageFromElements() # İçe aktarım sonrası önbelleği güncelle
                        self.drawing_area.undo_stack.clear()
                        self.drawing_area.redo_stack.clear()
                        self.drawing_area.modified = True # Değişiklik yapıldı olarak işaretle
                    # else: QMessageBox.warning kaldırıldı
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"Drawing dosyası yüklenemedi: {e}")
            else: # Görsel dosyası
                imported_image = QImage(file_path)
                if imported_image.isNull():
                    QMessageBox.critical(self, "Hata", "Görsel yüklenemedi.")
                    return
                imported_image = imported_image.convertToFormat(QImage.Format_RGB32)

                # Resim base64 olarak kaydedilir (veri kaybını önlemek için orijinal veri)
                buffer = QByteArray()
                buffer_io = QBuffer(buffer)
                buffer_io.open(QIODevice.WriteOnly)
                imported_image.save(buffer_io, "PNG") 
                base64_data = base64.b64encode(bytes(buffer.data())).decode('utf-8') 

                # Resmin tuvalde ortalanmış ve uygun boyutta olmasını sağla
                # Orijinal boyutları koruyarak ölçeklendirme için başlangıç değerleri
                # Tuval boyutlarına göre başlangıç ölçeğini ayarla
                max_width = self.image_width 
                max_height = self.image_height
                scaled_size = imported_image.size().scaled(
                    max_width, max_height, Qt.KeepAspectRatio
                )
                image_placement_offset = QPoint(
                    (self.image_width - scaled_size.width()) // 2,
                    (self.image_height - scaled_size.height()) // 2
                )

                # current_image_element'ı oluştur ve manipülasyon için hazırla
                self.drawing_area.current_image_element = {
                    "type": "image",
                    "base64_data": base64_data,
                    "position": [image_placement_offset.x(), image_placement_offset.y()],
                    "original_width": imported_image.width(), # Orijinal genişliği sakla
                    "original_height": imported_image.height(), # Orijinal yüksekliği sakla
                    "current_width": scaled_size.width(), # Mevcut görüntüleme genişliği
                    "current_height": scaled_size.height(), # Mevcut görüntüleme yüksekliği
                    "_qimage_cache": imported_image # QImage nesnesini önbelleğe al
                }
                
                # Modları DrawingArea'da ayarla
                self.drawing_area.placing_image = True 
                self.drawing_area.text_mode = False
                self.drawing_area.eraser_mode = False
                self.drawing_area.text_input_field.hide()
                self.drawing_area.current_text_element = None # Metin manipülasyonunu temizle
                self.drawing_area.text_panning = False
                self.drawing_area.setCursor(Qt.SizeAllCursor) # Taşıma imleci göster
                self.updateButtonStyles() # Buton stillerini güncelle
                self.drawing_area.update() # Dinamik resmi göstermek için güncelle


    def handleExportButtonPress(self, event):
        """Export butonuna yapılan fare tıklamalarını yönetir."""
        if event.button() == Qt.LeftButton:
            self.exportAnimationAsMp4()
        elif event.button() == Qt.RightButton:
            # Sağ tıklama menüsünü açmak yerine doğrudan PNG dışa aktarma
            self.exportCurrentFrameAsPng()
        # Temel mousePressEvent'i çağır, böylece butonun görsel geri bildirimi çalışır
        QPushButton.mousePressEvent(self.export_button, event)

    def exportAnimationAsMp4(self):
        """Animasyonu MP4 formatında dışa aktarır (C++ uygulaması kullanılarak)."""
        QDir().mkpath(DrawingEditorWindow.DEFAULT_BASE_DIR)
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Animasyonu MP4 Olarak Dışa Aktar", DrawingEditorWindow.DEFAULT_BASE_DIR,
            "MP4 Video (*.mp4);;Tüm Dosyalar (*)",
            options=options
        )
        if file_path:
            if not file_path.lower().endswith(".mp4"):
                file_path += ".mp4"
            
            temp_dir = None
            progress_dialog = None
            try:
                # Geçici bir dizin oluştur
                temp_dir = tempfile.mkdtemp(prefix="kavram_frames_")
                
                # İlerleme çubuğu diyaloğunu oluştur
                progress_dialog = QDialog(self)
                progress_dialog.setWindowTitle("Video Dışa Aktarılıyor")
                progress_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
                progress_dialog.setAttribute(Qt.WA_DeleteOnClose)
                progress_dialog.setStyleSheet("""
                    QDialog { background-color: #3f3f3f; border: 2px solid #007bff; border-radius: 8px; }
                    QLabel { color: #ffffff; font-size: 14px; padding: 5px; }
                    QProgressBar { border: 2px solid #555; border-radius: 5px; background-color: #2e2e2e; text-align: center; color: white; }
                    QProgressBar::chunk { background-color: #007bff; border-radius: 4px; }
                """)
                dialog_layout = QVBoxLayout(progress_dialog)
                dialog_layout.setContentsMargins(20, 20, 20, 20)
                
                self.export_status_label = QLabel("Kareler kaydediliyor...")
                dialog_layout.addWidget(self.export_status_label)
                
                self.export_progress_bar = QProgressBar(progress_dialog)
                self.export_progress_bar.setRange(0, 100)
                self.export_progress_bar.setValue(0)
                dialog_layout.addWidget(self.export_progress_bar)

                progress_dialog.show()
                QApplication.processEvents() # Diyaloğun görünür olduğundan emin ol

                # Her kareyi PNG olarak geçici dizine kaydet
                for i in range(len(self.drawing_area.all_frames_elements)):
                    frame_image = self.drawing_area._renderFrameToImage(i) # Doğrudan render metodunu kullan
                    # Dosya adlarını sıralanabilir olması için sıfır dolgulu yap
                    frame_filename = os.path.join(temp_dir, f"frame_{i:04d}.png")
                    frame_image.save(frame_filename, "PNG")
                    
                    progress_percent = int(((i + 1) / len(self.drawing_area.all_frames_elements)) * 50) # İlk %50 kare kaydetme için
                    self.export_progress_bar.setValue(progress_percent)
                    self.export_status_label.setText(f"Kareler kaydediliyor: {i+1}/{len(self.drawing_area.all_frames_elements)}")
                    QApplication.processEvents() # UI'yı güncelle
                
                self.export_status_label.setText("Video kodlanıyor...")
                self.export_progress_bar.setValue(50) # %50'ye ayarla
                QApplication.processEvents()

                # C++ yürütülebilir dosyasının yolu
                cpp_executable_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.CPP_EXECUTABLE_NAME)
                
                # C++ uygulamasını çalıştırmak için komut
                command = [
                    cpp_executable_path,
                    temp_dir,
                    file_path,
                    str(self.image_width),
                    str(self.image_height),
                    str(self.animation_fps)
                ]
                
                # C++ uygulamasını subprocess ile çalıştır
                # stdout ve stderr'ı yakalayarak konsola yazdırabiliriz
                process = subprocess.run(command, capture_output=True, text=True, check=False)
                
                if process.returncode == 0:
                    self.export_progress_bar.setValue(100) # %100'e ayarla
                    self.export_status_label.setText("Video başarıyla dışa aktarıldı!")
                    QApplication.processEvents()
                    time.sleep(1) # Kullanıcının mesajı görmesi için kısa bir bekleme
                    QMessageBox.information(self, "Dışa Aktarma Başarılı", f"Animasyon başarıyla MP4 olarak dışa aktarıldı:\n{file_path}")
                else:
                    self.export_progress_bar.setValue(0) # Hata durumunda ilerleme çubuğunu sıfırla
                    self.export_status_label.setText("Dışa aktarma hatası!")
                    QApplication.processEvents()
                    time.sleep(1)
                    QMessageBox.critical(
                        self, "Dışa Aktarma Hatası",
                        f"C++ video kodlayıcı hatayla çıktı ({process.returncode}).\n"
                        f"Standart Çıktı:\n{process.stdout}\n"
                        f"Hata Çıktısı:\n{process.stderr}"
                    )
            except FileNotFoundError:
                QMessageBox.critical(self, "Hata", f"'{self.CPP_EXECUTABLE_NAME}' yürütülebilir dosyası bulunamadı.\n"
                                                 f"Lütfen C++ kodunu derlediğinizden ve aynı dizinde olduğundan emin olun.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"MP4 video kaydedilemedi: {e}")
            finally:
                # Geçici dizini temizle
                if temp_dir and os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                        print(f"Geçici dizin temizlendi: {temp_dir}")
                    except Exception as e:
                        print(f"Geçici dizin temizlenirken hata oluştu: {e}")
                if progress_dialog:
                    progress_dialog.close() # Diyaloğu kapat

        
    def exportCurrentFrameAsPng(self):
        """Mevcut kareyi PNG formatında tam çözünürlüğünde dışa aktarır."""
        QDir().mkpath(DrawingEditorWindow.DEFAULT_BASE_DIR)
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Kareyi PNG Olarak Dışa Aktar", DrawingEditorWindow.DEFAULT_BASE_DIR,
            "PNG Görüntüsü (*.png);;Tüm Dosyalar (*)",
            options=options
        )
        if file_path:
            if not file_path.lower().endswith(".png"):
                file_path += ".png"
            try:
                current_frame_image = self.drawing_area._renderFrameToImage(self.drawing_area.current_frame_index)
                current_frame_image.save(file_path, "PNG")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Kare PNG olarak kaydedilemedi: {e}")

    def toggleEraser(self):
        self.drawing_area.eraser_mode = not self.drawing_area.eraser_mode
        self.drawing_area.text_mode = False
        self.drawing_area.placing_image = False 
        self.drawing_area.picking_color = False # Renk seçme modunu kapat
        self.drawing_area.text_input_field.hide()
        # Metin ve resim modundan çıkışta geçici öğeleri temizle
        self.drawing_area.current_text_element = None
        self.drawing_area.text_panning = False
        self.drawing_area.current_image_element = None
        self.drawing_area.image_panning = False
        self.drawing_area.setCursor(Qt.ArrowCursor)
        # Tablet tuş durumlarını sıfırla
        self.drawing_area.tablet_button_1_pressed = False
        self.drawing_area.tablet_button_2_pressed = False
        self.updateButtonStyles()
        self.drawing_area.modified = True # Değişiklik yapıldı olarak işaretle

    def changeColor(self):
        # Renk seçme diyaloğunu açmadan önce damlalık modunu kapat
        self.drawing_area.picking_color = False
        self.drawing_area.setCursor(Qt.ArrowCursor)
        # Tablet tuş durumlarını sıfırla
        self.drawing_area.tablet_button_1_pressed = False
        self.drawing_area.tablet_button_2_pressed = False


        dialog = CircleBrightnessDialog(initialColor=self.drawing_area.pen_color, parent=self)
        button_pos = self.color_button.mapToGlobal(QPoint(0, self.color_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            self.drawing_area.pen_color = dialog.getSelectedColor()
            self.drawing_area.eraser_mode = False
            self.drawing_area.placing_image = False 
            # Metin ve resim modundan çıkışta geçici öğeleri temizle
            self.drawing_area.current_text_element = None
            self.drawing_area.text_panning = False
            self.drawing_area.current_image_element = None
            self.drawing_area.image_panning = False
            self.drawing_area.setCursor(Qt.ArrowCursor)
            self.updateButtonStyles()
            self.drawing_area.modified = True # Değişiklik yapıldı olarak işaretle

    def clearDrawing(self): # Bu metod Animation_editor.py'da clearCurrentFrame olarak geçiyor.
        self.drawing_area.clearCurrentFrame() # Mevcut kareyi temizle
        self.drawing_area.modified = True # Değişiklik yapıldı olarak işaretle

    def changeRadius(self):
        dialog = RadiusDialog(initialRadius=self.drawing_area.pen_radius, parent=self)
        button_pos = self.radius_button.mapToGlobal(QPoint(0, self.radius_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            self.drawing_area.pen_radius = dialog.getRadius()
            self.radius_button.setText(f"Radius: {self.drawing_area.pen_radius}")
            # Metin modunda font boyutunu güncelle (eğer geçici metin varsa)
            if self.drawing_area.text_mode and self.drawing_area.current_text_element:
                self.drawing_area.current_text_element["font_size"] = max(10, self.drawing_area.pen_radius * 2)
                self.drawing_area.update()
            self.drawing_area.modified = True # Değişiklik yapıldı olarak işaretle

    def togglePressure(self):
        self.drawing_area.pen_pressure_enabled = not self.drawing_area.pen_pressure_enabled
        self.drawing_area.placing_image = False 
        self.drawing_area.picking_color = False # Renk seçme modunu kapat
        # Metin ve resim modundan çıkışta geçici öğeleri temizle
        self.drawing_area.current_text_element = None
        self.drawing_area.text_panning = False
        self.drawing_area.current_image_element = None
        self.drawing_area.image_panning = False
        self.drawing_area.setCursor(Qt.ArrowCursor)
        # Tablet tuş durumlarını sıfırla
        self.drawing_area.tablet_button_1_pressed = False
        self.drawing_area.tablet_button_2_pressed = False
        self.updateButtonStyles()
        self.drawing_area.modified = True # Değişiklik yapıldı olarak işaretle

    def toggleTextMode(self):
        self.drawing_area.text_mode = not self.drawing_area.text_mode
        if self.drawing_area.text_mode:
            self.drawing_area.eraser_mode = False
            self.drawing_area.placing_image = False 
            self.drawing_area.picking_color = False # Renk seçme modunu kapat
            # Metin modu aktifken input alanını gizle ve geçici metni ve resmi temizle (yeni metin için)
            self.drawing_area.text_input_field.hide()
            self.drawing_area.current_text_element = None
            self.drawing_area.text_panning = False
            self.drawing_area.current_image_element = None
            self.drawing_area.image_panning = False
            self.drawing_area.setCursor(Qt.ArrowCursor)
            # Tablet tuş durumlarını sıfırla
            self.drawing_area.tablet_button_1_pressed = False
            self.drawing_area.tablet_button_2_pressed = False
        else:
            self.drawing_area.text_input_field.hide()
            # Metin modundan çıkışta geçici metni ve resmi temizle
            self.drawing_area.current_text_element = None
            self.drawing_area.text_panning = False
            self.drawing_area.current_image_element = None
            self.drawing_area.image_panning = False
            self.drawing_area.setCursor(Qt.ArrowCursor)
            self.drawing_area.update() # Ekranı temizle (geçici metin/resim kaybolsun)
        self.updateButtonStyles()
        self.drawing_area.modified = True # Değişiklik yapıldı olarak işaretle

    def startColorPicking(self):
        """Renk seçme (damlalık) modunu başlatır."""
        self.drawing_area.picking_color = True
        # Diğer modları devre dışı bırak
        self.drawing_area.drawing = False
        self.drawing_area.panning = False
        self.drawing_area.text_mode = False
        self.drawing_area.placing_image = False
        self.drawing_area.eraser_mode = False
        self.drawing_area.text_input_field.hide()
        self.drawing_area.current_text_element = None
        self.drawing_area.text_panning = False
        self.drawing_area.current_image_element = None
        self.drawing_area.image_panning = False
        self.drawing_area.setCursor(Qt.CrossCursor) # Çapraz imleç (damlalık benzeri)
        # Tablet tuş durumlarını sıfırla
        self.drawing_area.tablet_button_1_pressed = False
        self.drawing_area.tablet_button_2_pressed = False
        self.updateButtonStyles() # Parent'taki buton stillerini güncelle

    def copyElementsToNextFrameByColor(self, target_color_tuple):
        """Belirtilen renkteki öğeleri bir sonraki kareye kopyalar."""
        if self.drawing_area.current_frame_index >= self.total_frames - 1:
            QMessageBox.information(self, "Kopyalama Hatası", "Son karede olduğunuz için sonraki kareye kopyalayamazsınız.")
            return

        current_frame_elements = self.drawing_area.all_frames_elements[self.drawing_area.current_frame_index]
        next_frame_index = self.drawing_area.current_frame_index + 1
        
        elements_to_copy = []
        for element in current_frame_elements:
            if element["type"] == "stroke" and tuple(element["color"]) == target_color_tuple:
                elements_to_copy.append(element)
            elif element["type"] == "text" and tuple(element["color"]) == target_color_tuple:
                elements_to_copy.append(element)
            # Resimler için renk filtresi daha karmaşık olabilir (örneğin, bir resmin baskın rengini bulmak).
            # Şimdilik, resim öğeleri rengine göre kopyalanmaz.
            # Eğer resimlerin de kopyalanmasını isterseniz, bu mantığı daha karmaşık bir şekilde uygulamanız gerekir.

        if elements_to_copy:
            # Bir sonraki kareye kopyala
            self.drawing_area.undo_stack.append(list(self.drawing_area.all_frames_elements[next_frame_index])) # İleriye kopyalamadan önce undo için kaydet
            self.drawing_area.redo_stack.clear()

            # Mevcut öğeleri koruyarak ekle
            self.drawing_area.all_frames_elements[next_frame_index].extend(elements_to_copy)
            self.drawing_area.modified = True
            self.drawing_area.updateImageFromElements() # Güncellenen kareyi yeniden çiz
            # QMessageBox.information(self, "Kopyalama Başarılı", f"{len(elements_to_copy)} öğe bir sonraki kareye kopyalandı.")
        # else:
            # QMessageBox.information(self, "Kopyalama", "Kopyalanacak renkli öğe bulunamadı.")

    def deleteElementsByColor(self, target_color_tuple):
        """Belirtilen renkteki öğeleri mevcut kareden siler."""
        current_frame_elements = self.drawing_area.all_frames_elements[self.drawing_area.current_frame_index]
        
        # Silinecek öğeleri içeren yeni bir liste oluştur
        new_elements = []
        deleted_count = 0
        for element in current_frame_elements:
            # Sadece çizim ve metin öğelerini renge göre sil
            if (element["type"] == "stroke" or element["type"] == "text") and \
               "color" in element and tuple(element["color"]) == target_color_tuple:
                deleted_count += 1
            else:
                new_elements.append(element)
        
        if deleted_count > 0:
            self.drawing_area.undo_stack.append(list(self.drawing_area.all_frames_elements[self.drawing_area.current_frame_index])) # Silmeden önce undo için kaydet
            self.drawing_area.redo_stack.clear()
            self.drawing_area.all_frames_elements[self.drawing_area.current_frame_index] = new_elements
            self.drawing_area.modified = True
            self.drawing_area.updateImageFromElements() # Güncellenen kareyi yeniden çiz
            # QMessageBox.information(self, "Silme Başarılı", f"{deleted_count} öğe silindi.")
       #  else:
           #  QMessageBox.information(self, "Silme", "Silinecek renkli öğe bulunamadı.")


    def updateButtonStyles(self):
        self.eraser_button.setStyleSheet(self.buttonStylePressure(self.drawing_area.eraser_mode))
        self.pressure_button.setStyleSheet(self.buttonStylePressure(self.drawing_area.pen_pressure_enabled))
        self.text_button.setStyleSheet(self.buttonStylePressure(self.drawing_area.text_mode))

        # Play butonu stilini oynatma durumuna göre güncelle
        if self.animation_timer.isActive():
            self.play_button.setStyleSheet(self.buttonStylePressure(True))
            self.play_button.setText("Stop")
        else:
            self.play_button.setStyleSheet(self.buttonStylePressure(False))
            self.play_button.setText("Play")

        # Renk seçme modu aktifse imleci ayarla
        if self.drawing_area.picking_color:
            self.drawing_area.setCursor(Qt.CrossCursor)
        elif self.drawing_area.tablet_button_1_pressed and not self.drawing_area.tablet_button_2_pressed: # Kalem 1. tuşu basılıysa pan imleci
            self.drawing_area.setCursor(Qt.ClosedHandCursor)
        elif self.drawing_area.tablet_button_2_pressed: # Kalem 2. tuşu basılıysa zoom imleci (Shift/Ctrl ile 1. tuş)
            self.drawing_area.setCursor(Qt.SizeVerCursor)
        elif not self.drawing_area.text_mode and not self.drawing_area.placing_image and \
             not self.drawing_area.panning and not self.drawing_area.drawing:
            self.drawing_area.setCursor(Qt.ArrowCursor) # Varsayılan imleç

    def updateFrameInfoLabel(self):
        current_time = self.drawing_area.current_frame_index / self.animation_fps
        self.frame_info_label.setText(
            f"Frame: {self.drawing_area.current_frame_index} / {self.total_frames - 1} "
            f"({current_time:.2f}s / {self.animation_duration:.2f}s)"
        )

    def addFrames(self):
        """Animasyona yeni kareler eklemek için bir diyalog açar."""
        dialog = AddFramesDialog(initialFrames=1, parent=self) # Varsayılan 1 kare
        button_pos = self.add_frames_button.mapToGlobal(QPoint(0, self.add_frames_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            num_frames = dialog.getFramesToAdd()
            # Yeni kareleri mevcut kare indeksinden sonra ekle
            current_idx = self.drawing_area.current_frame_index
            for _ in range(num_frames):
                self.drawing_area.all_frames_elements.insert(current_idx + 1, [])
            
            self.total_frames = len(self.drawing_area.all_frames_elements)
            self.animation_duration = self.total_frames / self.animation_fps # Süreyi güncelle

            self.drawing_area.setTotalFrames(self.total_frames) # DrawingArea'yı güncelle
            self.timeline_widget.total_frames = self.total_frames # TimelineWidget'ı güncelle
            self.timeline_widget.animation_duration = self.animation_duration # TimelineWidget'ı güncelle
            
            self.drawing_area.setCurrentFrame(current_idx + 1) # Yeni eklenen ilk kareye git
            self.updateFrameInfoLabel() # Frame bilgisini güncelle
            self.timeline_widget.update() # Timeline'ı yeniden çiz
            self.drawing_area.modified = True # Değişiklik yapıldı olarak işaretle

    def deleteFramesAfterCurrent(self):
        """Mevcut kareden sonraki tüm kareleri siler."""
        current_idx = self.drawing_area.current_frame_index
        if current_idx >= self.total_frames - 1:
            QMessageBox.information(self, "Kare Silme", "Silinecek sonraki kare bulunamadı.")
            return

        reply = QMessageBox.question(
            self, "Delete Frames",
            f"Mevcut kare ({current_idx}) dahil olmak üzere, bu kareden sonraki tüm kareleri silmek istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Mevcut kareden sonraki tüm kareleri sil
            self.drawing_area.all_frames_elements = self.drawing_area.all_frames_elements[:current_idx + 1]
            self.total_frames = len(self.drawing_area.all_frames_elements)
            self.animation_duration = self.total_frames / self.animation_fps

            self.drawing_area.setTotalFrames(self.total_frames)
            self.timeline_widget.total_frames = self.total_frames
            self.timeline_widget.animation_duration = self.animation_duration
            self.timeline_widget.setSliderValue(current_idx) # Mevcut karede kal
            self.updateFrameInfoLabel()
            self.timeline_widget.update()
            self.drawing_area.modified = True # Değişiklik yapıldı olarak işaretle

    def undo(self):
        self.drawing_area.undo()
        self.drawing_area.modified = True # Değişiklik yapıldı olarak işaretle

    def redo(self):
        # DrawingArea içindeki redo metodunu çağır
        self.drawing_area.redo()
        self.drawing_area.modified = True # Değişiklik yapıldı olarak işaretle

    def onTimelineChanged(self, value):
        """Zaman çizelgesi kaydırıcısı değiştiğinde kareyi günceller."""
        # Bu metod, TimelineWidget'in dahili kaydırıcısı değiştiğinde çağrılır
        self.drawing_area.setCurrentFrame(value)
        # updateFrameInfoLabel artık DrawingArea.setCurrentFrame içinde çağrılıyor

    def prevFrame(self):
        """Bir önceki kareye geçer."""
        if self.drawing_area.current_frame_index > 0:
            self.drawing_area.setCurrentFrame(self.drawing_area.current_frame_index - 1)

    def nextFrame(self):
        """Bir sonraki kareye geçer."""
        if self.drawing_area.current_frame_index < self.total_frames - 1:
            self.drawing_area.setCurrentFrame(self.drawing_area.current_frame_index + 1)

    def toggleAnimationPlayback(self):
        if self.animation_timer.isActive():
            self.animation_timer.stop()
            self.updateButtonStyles()
        else:
            self.current_play_frame = self.drawing_area.current_frame_index # Oynatmaya mevcut kareden başla
            self.animation_timer.start(1000 // self.animation_fps) # FPS'ye göre milisaniye cinsinden gecikme
            self.updateButtonStyles()

    def advanceFrame(self):
        """Animasyon oynatılırken bir sonraki kareye geçer."""
        self.current_play_frame += 1
        if self.current_play_frame >= self.total_frames:
            self.current_play_frame = 0 # Başa dön
        
        self.drawing_area.setCurrentFrame(self.current_play_frame)

    def triggerCoreSwitcher(self):
        main_window = self.window()
        if hasattr(main_window, 'showSwitcher'):
            main_window.showSwitcher()

    def closeEvent(self, event):
        # drawing_area nesnesinin var olup olmadığını ve None olmadığını kontrol ediyoruz.
        if hasattr(self, 'drawing_area') and self.drawing_area is not None and self.drawing_area.modified:
            reply = QMessageBox.question(self, 'Çıkış',
                                         "Değişiklikler kaydedilmedi. Çıkmak istediğinizden emin misiniz?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply == QMessageBox.Yes:
                self.drawing_area.modified = False
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = DrawingEditorWindow()
    # Pencerenin tam ekran olarak başlamasını istiyorsanız aşağıdaki satırı kullanın:
    # editor.showMaximized() 
    # Aksi takdirde, pencere yöneticisinin tam ekran yapma özelliğini kullanmak için sadece show() kullanın:
    editor.show() 
    sys.exit(app.exec_())

