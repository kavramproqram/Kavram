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
import json # JSON işlemleri için
import base64 # Görsel verilerini base64 olarak depolamak için

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QDialog, QSlider, QLabel,
    QPushButton, QApplication, QFileDialog, QMessageBox, QShortcut, QLineEdit
)
from PyQt5.QtGui import QColor, QPainter, QPen, QImage, QTabletEvent, QKeySequence, QFont, QFontMetrics, QCursor, QIcon, QPixmap
from PyQt5.QtCore import Qt, QPoint, QRect, QDir, QSize, QByteArray, QBuffer, QIODevice # Gerekli sınıflar import edildi
from PyQt5.QtSvg import QSvgRenderer # SVG ikonları için

# --- Yardımcı Fonksiyonlar ve Sabitler (sphere.py'den alındı) ---
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

# SVG ikonları (sphere.py'den alındı)
SVG_UNDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19C15.866 19 19 15.866 19 12C19 8.13401 15.866 5 12 5C8.13401 5 5 8.13401 5 12C5 13.7909 5.70014 15.4293 6.84594 16.6386L5 18M5 18H9M5 18V14" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_REDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5C8.13401 5 5 8.13401 5 12C5 15.866 8.13401 19 12 19C15.866 19 19 15.866 19 12C19 10.2091 18.2999 8.57074 17.1541 7.3614L19 6M19 6H15M19 6V10" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
# --- Yardımcı Fonksiyonlar ve Sabitler Sonu ---

# Renk seçimi için kullanılan diyalog (Color selection dialog)
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

        self.setFixedSize(280, 200)

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
            if not self._pickHueSat(event.pos()):
                self.accept()
            else:
                self.update()
        else:
            self.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if self._pickHueSat(event.pos()):
                self.update()

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

    def getSelectedColor(self):
        return QColor.fromHsvF(self.h/360.0, self.s, self.v)

    def focusOutEvent(self, event):
        self.accept()
        super().focusOutEvent(event)

# Radius ayarını yapmak için diyalog (Radius adjustment dialog)
class RadiusDialog(QDialog):
    def __init__(self, initialRadius=8, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedSize(200, 100)
        self.radius = initialRadius

        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.setRange(1, 50)
        self.slider.setValue(self.radius)
        self.slider.setGeometry(20, 40, 160, 20)
        self.slider.valueChanged.connect(self.onValueChanged)

        self.label = QLabel(self)
        self.label.setGeometry(20, 10, 160, 20)
        self.label.setStyleSheet("color: white;")
        self.label.setText(f"Radius: {self.radius}")

        self.ok_button = QPushButton("OK", self)
        self.ok_button.setGeometry(70, 70, 60, 25)
        self.ok_button.clicked.connect(self.accept)

    def onValueChanged(self, value):
        self.radius = value
        self.label.setText(f"Radius: {self.radius}")

    def getRadius(self):
        return self.radius

# Çizim yapılacak alan (Drawing area)
class DrawingArea(QWidget):
    # Geri al/yinele yığınlarının maksimum boyutu
    MAX_UNDO_REDO_STEPS = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StaticContents)
        self.modified = False
        self.drawing = False
        self.lastPoint = QPoint()
        
        # Temel çizim alanı (her zaman güncel, düzleştirilmiş resim)
        # Başlangıçta widget'ın mevcut boyutunu kullanır
        self.image = QImage(self.size(), QImage.Format_RGB32)
        # GÜNCELLEME: Arka plan rengini parent pencereden al
        bg_color = self.parent().background_color if self.parent() else QColor("#333")
        self.image.fill(bg_color)

        # Çizim öğelerini depolayan liste (strokes, text, images)
        self.drawing_elements = []

        # Undo/Redo yığınları (drawing_elements listesinin kopyalarını tutar)
        self.undo_stack = []
        self.redo_stack = []

        self.text_input_field = QLineEdit(self)
        self.text_input_field.hide()
        self.text_input_field.returnPressed.connect(self.addTextToDrawing)
        self.text_input_field.setStyleSheet("background-color: #444; color: white; border: 1px solid #777;")

        # Resim yerleştirme ve manipülasyonu için değişkenler
        self.original_image_for_placement = None # Yerleştirilecek resmin orijinal QImage'ı
        self.current_image_display_size = QSize(0, 0) # Anlık gösterilen resmin boyutu
        self.image_placement_offset = QPoint(0, 0) # Resmin çizim alanındaki konumu
        self.dragging_image = False # Resim sürükleniyor mu?
        self.last_drag_pos = QPoint() # Sürükleme başlangıç pozisyonu

        # Geçici fırça vuruşları için
        self.current_stroke_points = []
        # Geçici fırça vuruşlarının renk ve genişlik bilgileri
        self.current_stroke_pen_info = [] 

    def resizeEvent(self, event):
        # Eğer çizim alanı genişlerse, temel QImage'ı da genişlet
        # Bu, çizim alanının boyutları değiştiğinde mevcut içeriğin korunmasını sağlar.
        if self.width() > self.image.width() or self.height() > self.image.height():
            newWidth = max(self.width() + 128, self.image.width())
            newHeight = max(self.height() + 128, self.image.height())
            newImage = QImage(newWidth, newHeight, QImage.Format_RGB32)
            # GÜNCELLEME: Arka plan rengini parent pencereden al
            bg_color = self.parent().background_color if self.parent() else QColor("#333")
            newImage.fill(bg_color)
            
            # Eski içeriği yeni, daha büyük resme kopyala
            painter = QPainter(newImage)
            painter.drawImage(QPoint(0, 0), self.image)
            painter.end()
            self.image = newImage
        
        # Çizim öğelerinden resmi yeniden oluştur
        self.updateImageFromElements()
        super().resizeEvent(event)


    def paintEvent(self, event):
        painter = QPainter(self)
        rect = event.rect()
        painter.drawImage(rect, self.image, rect) # Temel, düzleştirilmiş resmi çiz

        # Eğer geçici bir resim varsa (yerleştirme modunda), onu en üste çiz
        if self.original_image_for_placement and self.current_image_display_size.isValid():
            scaled_temp_image = self.original_image_for_placement.scaled(
                self.current_image_display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            painter.drawImage(self.image_placement_offset, scaled_temp_image)

        # Not: Canlı çizim artık mouseMoveEvent/drawTabletLineTo içinde doğrudan self.image üzerine yapıldığı için,
        # current_stroke_points'i burada çizmeye gerek yok. paintEvent sadece self.image'ı gösterir.
        # Bu, performansı artırır.


    def mousePressEvent(self, event):
        parent = self.parent()
        if parent and parent.placing_image:
            if event.button() == Qt.LeftButton or event.button() == Qt.RightButton:
                # Sol veya sağ tuşla tıklanırsa resmi yerleştir
                if self.original_image_for_placement and self.current_image_display_size.isValid():
                    self.undo_stack.append(list(self.drawing_elements)) # Mevcut durumu kaydet
                    # Undo yığını boyutunu kontrol et
                    if len(self.undo_stack) > self.MAX_UNDO_REDO_STEPS:
                        self.undo_stack.pop(0) # En eski öğeyi kaldır
                    self.redo_stack.clear()

                    # Resim öğesini drawing_elements'a ekle
                    # Orijinal resmin base64'ünü ve yerleştirme bilgilerini kaydet
                    buffer = QByteArray()
                    buffer_io = QBuffer(buffer)
                    buffer_io.open(QIODevice.WriteOnly)
                    # Resmin kalitesini korumak için PNG formatında kaydedin
                    self.original_image_for_placement.save(buffer_io, "PNG") 
                    # QByteArray.data() doğrudan bytes döndürür, bu yüzden bytes() ile sarmalamak daha güvenli
                    base64_data = base64.b64encode(bytes(buffer.data())).decode('utf-8') 

                    self.drawing_elements.append({
                        "type": "image",
                        "base64_data": base64_data,
                        "position": [self.image_placement_offset.x(), self.image_placement_offset.y()],
                        "original_width": self.original_image_for_placement.width(),
                        "original_height": self.original_image_for_placement.height(),
                        "current_width": self.current_image_display_size.width(),
                        "current_height": self.current_image_display_size.height()
                    })
                    self.updateImageFromElements() # Temel resmi güncelle
                    self.cancelImagePlacement() # Resim yerleştirmeyi iptal et ve moddan çık
                    parent.updateButtonStyles() # Buton stillerini güncelle
                return
            elif event.button() == Qt.MiddleButton:
                # Orta tuşla tıklanırsa sürüklemeye başla
                self.dragging_image = True
                self.last_drag_pos = event.pos()
                self.setCursor(Qt.ClosedHandCursor) # İmleci kapalı el ikonuna çevir
                event.accept()
                return # Diğer olayları işleme

        elif parent and parent.text_mode:
            self.text_input_field.move(event.pos())
            self.text_input_field.show()
            self.text_input_field.setFocus()
            self.text_input_field.clear()
        elif event.button() == Qt.LeftButton:
            # Başlamadan önce mevcut durumu undo yığınına ekle
            self.undo_stack.append(list(self.drawing_elements))
            # Undo yığını boyutunu kontrol et
            if len(self.undo_stack) > self.MAX_UNDO_REDO_STEPS:
                self.undo_stack.pop(0) # En eski öğeyi kaldır
            self.redo_stack.clear()
            self.lastPoint = event.pos()
            self.drawing = True
            # Yeni fırça vuruşunu başlatırken ilk noktayı doğrudan çizime ekle
            pen_color, pen_width = parent.getCurrentPen()
            self.current_stroke_points = [event.pos()]
            self.current_stroke_pen_info = [[pen_color, pen_width]]
            
            # İlk noktayı doğrudan self.image üzerine çiz
            painter = QPainter(self.image)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(pen_color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPoint(event.pos())
            painter.end()
            self.update(QRect(event.pos(), event.pos()).adjusted(-pen_width, -pen_width, pen_width, pen_width)) # Sadece değişen alanı güncelle


    def mouseMoveEvent(self, event):
        if self.dragging_image:
            # Orta tuşla sürükleme
            delta = event.pos() - self.last_drag_pos
            self.image_placement_offset += delta
            self.last_drag_pos = event.pos()
            self.applyImagePlacementBounds() # Sınırları kontrol et
            self.update()
            event.accept()
            return # Diğer olayları işleme

        if (event.buttons() & Qt.LeftButton) and self.drawing:
            parent = self.parent()
            pen_color, pen_width = parent.getCurrentPen()
            
            # Fare ile çizim yaparken stabiliteyi artırmak için,
            # son noktadan mevcut noktaya bir çizgi çekmek yerine,
            # aradaki tüm noktaları interpolasyon yaparak ekleyelim.
            # Bu, hızlı fare hareketlerinde oluşan boşlukları doldurur.
            
            if not self.current_stroke_points: # İlk nokta ise (olmamalı ama kontrol amaçlı)
                self.current_stroke_points.append(event.pos())
                self.current_stroke_pen_info.append([pen_color, pen_width])
                self.lastPoint = event.pos() # lastPoint'i güncelle
            else:
                last_point_in_stroke = self.current_stroke_points[-1]
                dx = event.pos().x() - last_point_in_stroke.x()
                dy = event.pos().y() - last_point_in_stroke.y()
                distance = math.sqrt(dx*dx + dy*dy)
                
                if parent.pen_pressure_enabled:
                    step_size = max(1, parent.pen_radius / 2.0) 
                else:
                    step_size = 1.0 # Fare için sabit 1 piksellik adım boyutu
                
                painter = QPainter(self.image)
                painter.setRenderHint(QPainter.Antialiasing)
                
                # Sadece değişen alanı güncellemek için bir QRect oluştur
                update_rect = QRect(event.pos(), last_point_in_stroke).normalized()

                if distance > step_size:
                    num_steps = int(distance / step_size)
                    for i in range(1, num_steps + 1):
                        interp_x = last_point_in_stroke.x() + (dx * i / num_steps)
                        interp_y = last_point_in_stroke.y() + (dy * i / num_steps)
                        interpolated_point = QPoint(int(interp_x), int(interp_y))
                        
                        # Interpolasyon noktalarını doğrudan self.image üzerine çiz
                        painter.setPen(QPen(pen_color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                        painter.drawLine(self.lastPoint, interpolated_point)
                        
                        self.current_stroke_points.append(interpolated_point)
                        self.current_stroke_pen_info.append([pen_color, pen_width])
                        self.lastPoint = interpolated_point # lastPoint'i güncelle
                        
                        update_rect = update_rect.united(QRect(self.lastPoint, interpolated_point).normalized())
                
                # Son noktayı doğrudan self.image üzerine çiz
                painter.setPen(QPen(pen_color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.drawLine(self.lastPoint, event.pos())
                
                self.current_stroke_points.append(event.pos()) # Son noktayı ekle
                self.current_stroke_pen_info.append([pen_color, pen_width]) # Kalem bilgisini de ekle
                self.lastPoint = event.pos() # lastPoint'i güncelle
                
                painter.end()
                
                # Sadece değişen alanı güncelle
                self.update(update_rect.adjusted(-pen_width, -pen_width, pen_width, pen_width))


    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self.dragging_image:
            # Orta tuş bırakılırsa sürüklemeyi bitir
            self.dragging_image = False
            self.setCursor(Qt.CrossCursor) # İmleci tekrar çapraz oka çevir
            event.accept()
            return # Diğer olayları işleme

        if event.button() == Qt.LeftButton and self.drawing:
            # Fırça vuruşunu drawing_elements'a ekle
            parent = self.parent()
            
            if parent.pen_pressure_enabled and self.current_stroke_pen_info:
                # Basınç hassasiyeti etkinse, her bir nokta için kaydedilen renk ve genişlik bilgisini kullan
                extended_points = []
                for i, point in enumerate(self.current_stroke_points):
                    color_info = self.current_stroke_pen_info[i][0]
                    width_info = self.current_stroke_pen_info[i][1]
                    extended_points.append([
                        point.x(), point.y(),
                        color_info.red(), color_info.green(), color_info.blue(), color_info.alpha(),
                        width_info
                    ])
                
                self.drawing_elements.append({
                    "type": "stroke_pressure", # Yeni tip: basınç hassasiyetli çizim tipi
                    "points": extended_points,
                    "pressure_enabled": True 
                })
            else:
                # Basınç hassasiyeti etkin değilse veya fare kullanılıyorsa, tek bir renk ve genişlik kullan.
                color_to_save, width_to_save = parent.getCurrentPen()
                self.drawing_elements.append({
                    "type": "stroke",
                    "points": [[p.x(), p.y()] for p in self.current_stroke_points],
                    "color": [color_to_save.red(), color_to_save.green(), color_to_save.blue(), color_to_save.alpha()],
                    "width": width_to_save,
                    "pressure_enabled": False 
                })
            
            self.current_stroke_points = [] # Geçici fırça vuruşunu temizle
            self.current_stroke_pen_info = [] # Geçici kalem bilgilerini temizle
            self.drawing = False
            # updateImageFromElements burada hala gerekli çünkü nihai, düzleştirilmiş resim güncellenmeli.
            # Ancak, eğer çizim sırasında zaten self.image üzerine çizim yapıldıysa,
            # bu çağrı sadece drawing_elements'ı güncelleyip tam bir yeniden çizim yapmayabilir.
            # Mevcut durumda, tam bir yeniden çizim yapar, bu da undo/redo için tutarlılık sağlar.
            self.updateImageFromElements() 

    def wheelEvent(self, event):
        parent = self.parent()
        if parent and parent.placing_image and self.original_image_for_placement:
            # Resim yerleştirme modundaysa fare tekerleği ile boyutlandır
            num_degrees = event.angleDelta().y() / 8 # Tekerlek dönüş miktarını al
            num_steps = num_degrees / 15 # Adım sayısına çevir (hassasiyet ayarı)
            
            scale_factor = 1.0 + num_steps * 0.1 # Ölçek faktörü (0.1 hassasiyet)
            
            current_image_size = self.current_image_display_size
            new_width = int(current_image_size.width() * scale_factor)
            new_height = int(current_image_size.height() * scale_factor)

            # Minimum ve maksimum boyutları kontrol et
            min_size = 20 # Minimum resim boyutu
            # Çizim alanı genişliği - 5px sol - 5px sağ boşluk = 10px toplam boşluk
            max_size_width = self.width() - 10 
            # Çizim alanı yüksekliği - 5px üst - 5px alt boşluk = 10px toplam boşluk
            max_size_height = self.height() - 10 

            new_width = max(min_size, min(new_width, max_size_width))
            new_height = max(min_size, min(new_height, max_size_height))

            if new_width == current_image_size.width() and new_height == current_image_size.height():
                event.ignore() # Boyut değişmediyse olayı yoksay
                return

            # Resmin merkezini sabit tutarak ölçekle
            current_center = self.image_placement_offset + QPoint(current_image_size.width() // 2, current_image_size.height() // 2)
            
            self.current_image_display_size = QSize(new_width, new_height)
            
            # Yeni ofseti hesapla
            self.image_placement_offset = current_center - QPoint(self.current_image_display_size.width() // 2, self.current_image_display_size.height() // 2)
            
            self.applyImagePlacementBounds() # Sınırları kontrol et
            self.update()
            event.accept()
        else:
            super().wheelEvent(event) # Diğer durumlarda varsayılan tekerlek olayını işle

    def tabletEvent(self, event):
        parent = self.parent()
        if parent and (parent.text_mode or parent.placing_image):
            return # Tablet eventi metin veya resim yerleştirme modunda devre dışı
        
        if event.type() == QTabletEvent.TabletPress:
            self.undo_stack.append(list(self.drawing_elements))
            # Undo yığını boyutunu kontrol et
            if len(self.undo_stack) > self.MAX_UNDO_REDO_STEPS:
                self.undo_stack.pop(0) # En eski öğeyi kaldır
            self.redo_stack.clear()
            self.lastPoint = event.pos()
            self.drawing = True
            self.current_stroke_points = [event.pos()]
            
            # Tablet basıncına göre ilk kalem bilgilerini kaydet
            # GÜNCELLEME: Silgi rengini parent'ın arkaplan renginden al
            pen_color = parent.background_color if parent.eraser_mode else parent.pen_color
            # Minimum genişlik 1 olmalı
            pen_width = max(1, int(parent.pen_radius * event.pressure())) if parent.pen_pressure_enabled else parent.pen_radius
            self.current_stroke_pen_info = [[pen_color, pen_width]]

            # İlk noktayı doğrudan self.image üzerine çiz
            painter = QPainter(self.image)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(pen_color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPoint(event.pos())
            painter.end()
            self.update(QRect(event.pos(), event.pos()).adjusted(-pen_width, -pen_width, pen_width, pen_width)) # Sadece değişen alanı güncelle

            event.accept()
        elif event.type() == QTabletEvent.TabletMove:
            if self.drawing:
                self.drawTabletLineTo(event.pos(), event.pressure())
            event.accept()
        elif event.type() == QTabletEvent.TabletRelease:
            if self.drawing:
                # Tablet olaylarında da mouseReleaseEvent'teki aynı kaydetme mantığını kullan.
                # Tek bir stroke öğesi olarak kaydediyoruz.
                if parent.pen_pressure_enabled and self.current_stroke_pen_info:
                    # Basınç hassasiyeti etkinse, her bir nokta için kaydedilen renk ve genişlik bilgisini kullan
                    extended_points = []
                    for i, point in enumerate(self.current_stroke_points):
                        color_info = self.current_stroke_pen_info[i][0]
                        width_info = self.current_stroke_pen_info[i][1]
                        extended_points.append([
                            point.x(), point.y(),
                            color_info.red(), color_info.green(), color_info.blue(), color_info.alpha(),
                            width_info
                        ])
                    
                    self.drawing_elements.append({
                        "type": "stroke_pressure", # Yeni tip: basınç hassasiyetli çizim tipi
                        "points": extended_points,
                        "pressure_enabled": True 
                    })
                else:
                    color_to_save, width_to_save = parent.getCurrentPen() # Normal kalem rengi ve genişliği
                    self.drawing_elements.append({
                        "type": "stroke",
                        "points": [[p.x(), p.y()] for p in self.current_stroke_points],
                        "color": [color_to_save.red(), color_to_save.green(), color_to_save.blue(), color_to_save.alpha()],
                        "width": width_to_save,
                        "pressure_enabled": False 
                    })
                self.current_stroke_points = []
                self.current_stroke_pen_info = [] # Kalem bilgilerini de temizle
                self.drawing = False
                self.updateImageFromElements()
            event.accept()

    def drawTabletLineTo(self, endPoint, pressure):
        parent = self.parent()
        # GÜNCELLEME: Silgi rengini parent'ın arkaplan renginden al
        pen_color = parent.background_color if parent.eraser_mode else parent.pen_color
        # Minimum genişlik 1 olmalı
        pen_width = max(1, int(parent.pen_radius * pressure)) if parent.pen_pressure_enabled else parent.pen_radius
        
        # Doğrudan self.image üzerine çizim yap
        painter = QPainter(self.image)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(pen_color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(self.lastPoint, endPoint)
        painter.end()

        # Sadece değişen alanı güncelle
        update_rect = QRect(self.lastPoint, endPoint).normalized().adjusted(-pen_width, -pen_width, pen_width, pen_width)
        self.update(update_rect)

        self.current_stroke_points.append(endPoint) # Noktayı fırça vuruşuna ekle
        self.current_stroke_pen_info.append([pen_color, pen_width]) # Kalem bilgisini de ekle
        self.lastPoint = endPoint # lastPoint'i güncelle


    def addTextToDrawing(self):
        text = self.text_input_field.text()
        if text:
            self.undo_stack.append(list(self.drawing_elements))
            # Undo yığını boyutunu kontrol et
            if len(self.undo_stack) > self.MAX_UNDO_REDO_STEPS:
                self.undo_stack.pop(0) # En eski öğeyi kaldır
            self.redo_stack.clear()

            parent = self.parent()
            font_size = max(10, parent.pen_radius * 2)
            text_color = [parent.pen_color.red(), parent.pen_color.green(), parent.pen_color.blue(), parent.pen_color.alpha()]
            text_pos = self.text_input_field.pos()
            
            self.drawing_elements.append({
                "type": "text",
                "content": text,
                "position": [text_pos.x(), text_pos.y()],
                "font_size": font_size,
                "color": text_color
            })
            self.updateImageFromElements() # Temel resmi güncelle
        self.text_input_field.hide()
        self.text_input_field.clear()

    def startImagePlacement(self, original_image_qimage):
        """
        Resim yerleştirme modunu başlatır ve geçici resmi ayarlar.
        original_image_qimage: QImage nesnesi (henüz ölçeklenmemiş orijinal resim)
        """
        self.original_image_for_placement = original_image_qimage
        
        # Resmin yerleştirileceği alanı hesapla (5px boşluk bırakarak)
        drawing_area_size = self.size()
        # 5px sol + 5px sağ = 10px toplam boşluk
        max_width = drawing_area_size.width() - 10 
        # 5px üst + 5px alt = 10px toplam boşluk
        max_height = drawing_area_size.height() - 10 

        # Orijinal resmin boyutuna göre ilk ölçeklemeyi yap
        # Resmin en boy oranını koruyarak çizim alanına sığacak şekilde ölçekle
        initial_scaled_size = self.original_image_for_placement.size().scaled(
            max_width, max_height, Qt.KeepAspectRatio
        )
        self.current_image_display_size = initial_scaled_size

        # Resmi başlangıçta ekranın ortasına yakın bir yere yerleştir (5px boşluk bırakarak)
        self.image_placement_offset = QPoint(
            (self.width() - initial_scaled_size.width()) // 2,
            (self.height() - initial_scaled_size.height()) // 2
        )
        self.applyImagePlacementBounds() # Başlangıçta sınırları kontrol et
        self.dragging_image = False
        self.setCursor(Qt.CrossCursor) # İmleci çapraz oka çevir

        # Resim yerleştirme modu başladığında devam eden çizimi iptal et
        self.drawing = False
        self.current_stroke_points = []
        self.current_stroke_pen_info = []

        self.update()

    def cancelImagePlacement(self):
        """
        Resim yerleştirme modunu iptal eder ve geçici resmi temizler.
        """
        self.original_image_for_placement = None
        self.current_image_display_size = QSize(0, 0)
        self.image_placement_offset = QPoint(0, 0)
        self.dragging_image = False
        self.setCursor(Qt.ArrowCursor) # İmleci normale döndür
        
        # Resim yerleştirme modu iptal edildiğinde çizim durumunu sıfırla
        self.drawing = False
        self.current_stroke_points = []
        self.current_stroke_pen_info = []

        self.update()
        # Parent'ın placing_image durumunu güncelle
        parent = self.parent()
        if parent:
            parent.placing_image = False
            parent.updateButtonStyles()

    def applyImagePlacementBounds(self):
        """
        Geçici resmin çizim alanı içinde ve 5px boşlukla kalmasını sağlar.
        """
        if not self.original_image_for_placement or not self.current_image_display_size.isValid():
            return

        # Minimum 5px boşluk
        min_x = 5
        min_y = 5
        # Maksimum konum, resmin genişliği/yüksekliği ve 5px boşluk düşülerek hesaplanır
        max_x = self.width() - self.current_image_display_size.width() - 5
        max_y = self.height() - self.current_image_display_size.height() - 5

        # Eğer resim çok büyükse ve 5px boşluk bırakarak sığmıyorsa, min/max değerlerini ayarla
        # Bu, resim çizim alanından büyükse kenarlara yapışmasını sağlar.
        self.image_placement_offset.setX(max(min_x, min(max_x, self.image_placement_offset.x())))
        self.image_placement_offset.setY(max(min_y, min(max_y, self.image_placement_offset.y())))


    def updateImageFromElements(self):
        """
        drawing_elements listesindeki tüm öğeleri self.image üzerine yeniden çizer.
        Bu, herhangi bir değişiklik olduğunda çağrılmalıdır.
        """
        # Mevcut resmin boyutunu koru veya yeni boyuta ayarla
        new_image = QImage(self.size(), QImage.Format_RGB32)
        # GÜNCELLEME: Arka plan rengini parent pencereden al
        bg_color = self.parent().background_color if self.parent() else QColor("#333")
        new_image.fill(bg_color) # Arka planı temizle

        painter = QPainter(new_image)
        painter.setRenderHint(QPainter.Antialiasing)

        for element in self.drawing_elements:
            if element["type"] == "stroke":
                color = QColor(*element["color"])
                width = element["width"]
                pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                points = [QPoint(p[0], p[1]) for p in element["points"]]
                for i in range(len(points) - 1):
                    painter.drawLine(points[i], points[i+1])
            elif element["type"] == "stroke_pressure": # Yeni basınç hassasiyetli çizim tipi
                # Her bir nokta için kaydedilen renk ve genişlik bilgisini kullanarak çizim yap
                points_data = element["points"]
                for i in range(len(points_data) - 1):
                    p1_data = points_data[i]
                    p2_data = points_data[i+1]
                    
                    p1 = QPoint(p1_data[0], p1_data[1])
                    p2 = QPoint(p2_data[0], p2_data[1])
                    
                    color = QColor(p1_data[2], p1_data[3], p1_data[4], p1_data[5])
                    width = p1_data[6]
                    
                    pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    painter.setPen(pen)
                    painter.drawLine(p1, p2)
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
                base64_data = element["base64_data"]
                image_data = base64.b64decode(base64_data)
                temp_image = QImage()
                temp_image.loadFromData(image_data, "PNG") # PNG olarak yükle

                # Kaydedilen boyutlara göre ölçekle
                scaled_image = temp_image.scaled(
                    element["current_width"], element["current_height"],
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                image_pos = QPoint(element["position"][0], element["position"][1])
                painter.drawImage(image_pos, scaled_image)
        
        painter.end()
        self.image = new_image
        self.update() # Ekranı güncelle

    def clear(self):
        self.drawing_elements.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        # Çizim temizlendiğinde QImage'ı mevcut widget boyutuna sıfırla.
        # Bu, daha önce büyük bir çizim yapıldıysa RAM kullanımını azaltmaya yardımcı olur.
        self.image = QImage(self.size(), QImage.Format_RGB32)
        # GÜNCELLEME: Arka plan rengini parent pencereden al
        bg_color = self.parent().background_color if self.parent() else QColor("#333")
        self.image.fill(bg_color)
        self.update() # Ekranı güncelle

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(list(self.drawing_elements))
            # Redo yığını boyutunu kontrol et
            if len(self.redo_stack) > self.MAX_UNDO_REDO_STEPS:
                self.redo_stack.pop(0) # En eski öğeyi kaldır
            self.drawing_elements = self.undo_stack.pop()
            self.updateImageFromElements() # Temel resmi güncelle

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(list(self.drawing_elements))
            # Undo yığını boyutunu kontrol et
            if len(self.undo_stack) > self.MAX_UNDO_REDO_STEPS:
                self.undo_stack.pop(0) # En eski öğeyi kaldır
            self.drawing_elements = self.redo_stack.pop()
            self.updateImageFromElements() # Temel resmi güncelle

# Çizim editörü penceresi (Drawing editor window)
class DrawingEditorWindow(QWidget):
    # Varsayılan dışa aktarma dizini
    DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')

    def __init__(self, core_window_ref=None): # core_window_ref argümanını kabul et
        super().__init__()
        self.core_window_ref = core_window_ref # core_window_ref'i sakla
        self.pen_color = QColor("white")
        # YENİ: Arka plan ve silgi için ortak renk
        self.background_color = QColor("#333")
        self.pen_radius = 8
        self.eraser_mode = False
        self.pen_pressure_enabled = False
        self.text_mode = False # Metin modu değişkeni
        self.placing_image = False # Resim yerleştirme modu değişkeni
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Kavram")
        self.resize(800, 600)
        self.setStyleSheet("background-color: #222;")

        # Üst araç çubuğu (Top toolbar)
        toolbar_frame = QFrame()
        # TextEditorWindow'daki gibi araç çubuğu stili
        toolbar_frame.setStyleSheet("background-color: #222; border-bottom: 2px solid #555;")
        toolbar_frame.setFixedHeight(40)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)

        # File butonu (File button)
        self.file_button = QPushButton("File")
        self.file_button.setStyleSheet(self.buttonStyle())
        self.file_button.setFixedSize(90, 30)
        self.file_button.clicked.connect(self.importFile) # Yeni import metodu
        toolbar_layout.addWidget(self.file_button, alignment=Qt.AlignLeft)

        # Yeni UNDO butonu
        self.undo_button = QPushButton()
        self.undo_button.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20))
        self.undo_button.setStyleSheet(self.buttonStyleMini())
        self.undo_button.setFixedSize(30, 30)
        self.undo_button.clicked.connect(self.undo)
        toolbar_layout.addWidget(self.undo_button, alignment=Qt.AlignLeft)

        # Yeni REDO butonu
        self.redo_button = QPushButton()
        self.redo_button.setIcon(create_svg_icon(SVG_REDO_ICON, size=20))
        self.redo_button.setStyleSheet(self.buttonStyleMini())
        self.redo_button.setFixedSize(30, 30)
        self.redo_button.clicked.connect(self.redo)
        toolbar_layout.addWidget(self.redo_button, alignment=Qt.AlignLeft)

        # Eraser butonu (Eraser button)
        self.eraser_button = QPushButton("Eraser")
        self.eraser_button.setStyleSheet(self.buttonStylePressure(self.eraser_mode)) # Başlangıçta stilini ayarla
        self.eraser_button.setFixedSize(95, 30)
        self.eraser_button.clicked.connect(self.toggleEraser)
        # YENİ: Sağ tık menüsü için
        self.eraser_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.eraser_button.customContextMenuRequested.connect(self.changeBackgroundColor)
        toolbar_layout.addWidget(self.eraser_button, alignment=Qt.AlignLeft)

        # Color butonu (Color button)
        self.color_button = QPushButton("Color")
        self.color_button.setStyleSheet(self.buttonStyle())
        self.color_button.setFixedSize(90, 30)
        self.color_button.clicked.connect(self.changeColor)
        toolbar_layout.addWidget(self.color_button, alignment=Qt.AlignLeft)

        # Delete butonu (Delete button)
        self.delete_button = QPushButton("Delete")
        self.delete_button.setStyleSheet(self.buttonStyle())
        self.delete_button.setFixedSize(95, 30)
        self.delete_button.clicked.connect(self.clearDrawing)
        toolbar_layout.addWidget(self.delete_button, alignment=Qt.AlignLeft)

        # Radius butonu (Radius button)
        self.radius_button = QPushButton(f"Radius: {self.pen_radius}")
        self.radius_button.setStyleSheet(self.buttonStyle())
        self.radius_button.setFixedSize(125, 30)
        self.radius_button.clicked.connect(self.changeRadius)
        toolbar_layout.addWidget(self.radius_button, alignment=Qt.AlignLeft)

        # Kalem basınç butonu (Pen pressure button)
        self.pressure_button = QPushButton("/")
        self.pressure_button.setStyleSheet(self.buttonStylePressure(self.pen_pressure_enabled)) # Başlangıçta stilini ayarla
        self.pressure_button.setFixedSize(30, 30)
        self.pressure_button.clicked.connect(self.togglePressure)
        toolbar_layout.addWidget(self.pressure_button, alignment=Qt.AlignLeft)

        # A (Text) butonu
        self.text_button = QPushButton("A")
        self.text_button.setStyleSheet(self.buttonStylePressure(self.text_mode)) # Başlangıçta stilini ayarla
        self.text_button.setFixedSize(30, 30)
        self.text_button.clicked.connect(self.toggleTextMode)
        toolbar_layout.addWidget(self.text_button, alignment=Qt.AlignLeft)

        # Sağ tarafta boşluk (Spacer on the right)
        toolbar_layout.addStretch()

        # Export butonu en sağda (Export button on the far right)
        self.export_button = QPushButton("Export")
        self.export_button.setStyleSheet(self.buttonStyle())
        self.export_button.setFixedSize(90, 30)
        self.export_button.clicked.connect(self.exportFile) # Yeni export metodu
        toolbar_layout.addWidget(self.export_button, alignment=Qt.AlignRight)

        # Drawing butonu (artık editör geçişi için kullanılıyor)
        self.drawing_button = QPushButton("Drawing")
        self.drawing_button.setStyleSheet(self.buttonStyle())
        self.drawing_button.setFixedSize(100, 30)
        self.drawing_button.clicked.connect(self.triggerCoreSwitcher)
        toolbar_layout.addWidget(self.drawing_button, alignment=Qt.AlignRight) # AlignRight olarak değiştirildi


        # Çerçeveyi ana layout'a ekle
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(toolbar_frame)

        # Çizim alanı
        self.drawing_area = DrawingArea(self)
        main_layout.addWidget(self.drawing_area)
        self.setLayout(main_layout)

        # Kısayollar
        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self.redo)

    def buttonStyle(self):
        """
        Genel butonlar için TextEditorWindow'daki gibi stil.
        """
        return """
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 5px 20px;
            }
            QPushButton:hover {
                background-color: #444;
            }
            QPushButton:pressed {
                background-color: #666;
            }
        """

    def buttonStyleMini(self):
        """
        Küçük ikon butonları için stil.
        """
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 16px;
                border: 2px solid #555; border-radius: 8px; padding: 5px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

    def buttonStylePressure(self, pressed):
        """
        Basınç, silgi ve metin modları için özel buton stili.
        TextEditorWindow'daki genel buton stiline daha uygun hale getirildi.
        """
        if pressed:
            return """
                QPushButton {
                    background-color: #555; /* Aktifken daha koyu gri */
                    color: white;
                    font-size: 16px;
                    border: 2px solid #555;
                    border-radius: 8px; /* Genel butonlarla uyumlu */
                    padding: 5px;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: transparent;
                    color: white;
                    font-size: 16px;
                    border: 2px solid #555;
                    border-radius: 8px; /* Genel butonlarla uyumlu */
                    padding: 5px;
                }
                QPushButton:hover { background-color: #444; }
                QPushButton:pressed { background-color: #666; }
            """

    def importFile(self):
        """
        Dosya iletişim kutusunu açar.
        Hem yaygın görsel formatları hem de özel '.drawing' dosyalarını destekler.
        """
        options = QFileDialog.Options()
        # Varsayılan olarak hem .drawing hem de yaygın görsel formatlarını içeren bir filtre
        file_filter = "Desteklenen Dosyalar (*.drawing *.png *.jpg *.jpeg *.bmp *.gif);;Drawing Dosyaları (*.drawing);;Görsel Dosyaları (*.png *.jpg *.jpeg *.bmp *.gif);;Tüm Dosyalar (*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Drawing veya Görsel İçe Aktar", DrawingEditorWindow.DEFAULT_BASE_DIR,
            file_filter,
            options=options
        )
        if file_path:
            self.load_image_from_path(file_path) # Yeni metod ile yükle


    def exportFile(self):
        """
        Dosya kaydetme iletişim kutusunu açar.
        '.drawing' formatında veya düzleştirilmiş görsel olarak kaydetmeyi destekler.
        """
        QDir().mkpath(DrawingEditorWindow.DEFAULT_BASE_DIR)

        options = QFileDialog.Options()
        # Varsayılan olarak PNG dosya türünü seçili getir
        file_filter = "PNG Dosyaları (*.png);;Drawing Dosyaları (*.drawing);;JPEG Dosyaları (*.jpg *.jpeg);;BMP Dosyaları (*.bmp);;GIF Dosyaları (*.gif);;Tüm Dosyalar (*)"
        
        # Varsayılan olarak seçili filtreyi belirtmek için 'selectedFilter' parametresini kullanın
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self, "Çizimi Dışa Aktar", DrawingEditorWindow.DEFAULT_BASE_DIR,
            file_filter,
            "PNG Dosyaları (*.png)", # Varsayılan olarak PNG seçili gelecek
            options=options
        )
        if file_path:
            if selected_filter == "Drawing Dosyaları (*.drawing)":
                if not file_path.lower().endswith(".drawing"):
                    file_path += ".drawing"
                try:
                    # Kaydetmeden önce 'stroke_pressure' tipini eski 'stroke' tipine dönüştür (uyumluluk için)
                    # Veya daha iyisi, yeni formatı kaydet ve yüklerken her iki formatı da destekle.
                    # Mevcut durumda, yükleme kısmı zaten iki tipi de destekliyor.
                    # Bu nedenle, burada sadece mevcut drawing_elements'ı olduğu gibi kaydedelim.
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(self.drawing_area.drawing_elements, f, indent=4)
                    QMessageBox.information(self, "Dışa Aktırma", f"Çizim başarıyla dışa aktarıldı:\n{file_path}")
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"Drawing dosyası kaydedilemedi: {e}")
            else: # Görsel formatları
                # Dosya uzantısını filtreye göre ayarla
                if selected_filter == "PNG Dosyaları (*.png)":
                    if not file_path.lower().endswith(".png"): file_path += ".png"
                    file_format = "PNG"
                elif selected_filter == "JPEG Dosyaları (*.jpg *.jpeg)":
                    if not file_path.lower().endswith((".jpg", ".jpeg")): file_path += ".jpg"
                    file_format = "JPEG"
                elif selected_filter == "BMP Dosyaları (*.bmp)":
                    if not file_path.lower().endswith(".bmp"): file_path += ".bmp"
                    file_format = "BMP"
                elif selected_filter == "GIF Dosyaları (*.gif)":
                    if not file_path.lower().endswith(".gif"): file_path += ".gif"
                    file_format = "GIF"
                else: # Varsayılan olarak PNG
                    if not file_path.lower().endswith(".png"): file_path += ".png"
                    file_format = "PNG"

                # Mevcut çizim alanının görüntüsünü kaydet
                # QImage.save() metodunun kalitesi, format parametresine göre değişir.
                # PNG kayıpsız bir formattır, JPEG ise sıkıştırma seviyesine göre kalite kaybedebilir.
                # Burada varsayılan kalite ayarları kullanılmaktadır.
                if not self.drawing_area.image.save(file_path, file_format):
                    QMessageBox.critical(self, "Hata", "Çizim dışa aktarılamadı.")
                else:
                    QMessageBox.information(self, "Dışa Aktırma", f"Çizim başarıyla dışa aktarıldı:\n{file_path}")

    def load_image_from_path(self, file_path):
        """
        Verilen dosya yolundan bir görseli yükler ve çizim alanına yerleştirme modunu başlatır.
        """
        if file_path.lower().endswith(".drawing"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    drawing_data = json.load(f)
                processed_elements = []
                for element in drawing_data:
                    if element["type"] == "stroke" and "pressure_enabled" not in element:
                        points_with_info = []
                        color = QColor(*element["color"])
                        width = element["width"]
                        for p in element["points"]:
                            points_with_info.append([p[0], p[1], color.red(), color.green(), color.blue(), color.alpha(), width])
                        processed_elements.append({
                            "type": "stroke_pressure",
                            "points": points_with_info,
                            "pressure_enabled": False
                        })
                    else:
                        processed_elements.append(element)

                self.drawing_area.drawing_elements = processed_elements
                self.drawing_area.updateImageFromElements()
                self.drawing_area.undo_stack.clear()
                self.drawing_area.redo_stack.clear()
                QMessageBox.information(self, "İçe Aktırma", "Çizim başarıyla yüklendi.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Drawing dosyası yüklenemedi: {e}")
        else: # Görsel dosyası
            imported_image = QImage(file_path)
            if imported_image.isNull():
                QMessageBox.critical(self, "Hata", "Görsel yüklenemedi.")
                return
            imported_image = imported_image.convertToFormat(QImage.Format_RGB32)

            self.placing_image = True # Resim yerleştirme modunu aktif et
            self.text_mode = False # Metin modunu kapat
            self.eraser_mode = False # Silgi modunu kapat
            self.drawing_area.text_input_field.hide() # Metin giriş alanını gizle
            self.drawing_area.startImagePlacement(imported_image) # Resim manipülasyonunu başlat
            self.updateButtonStyles() # Buton stillerini güncelle


    def toggleEraser(self):
        self.eraser_mode = not self.eraser_mode
        self.text_mode = False # Metin modunu kapat
        self.drawing_area.text_input_field.hide() # Metin giriş alanını gizle
        self.drawing_area.cancelImagePlacement() # Resim yerleştirme modunu iptal et
        self.updateButtonStyles()

    def changeColor(self):
        dialog = CircleBrightnessDialog(initialColor=self.pen_color, parent=self)
        button_pos = self.color_button.mapToGlobal(QPoint(0, self.color_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            self.pen_color = dialog.getSelectedColor()
            self.eraser_mode = False # Renk seçildiğinde silgi modunu kapat
            self.drawing_area.cancelImagePlacement() # Resim yerleştirme modunu iptal et
            self.updateButtonStyles()

    def clearDrawing(self):
        self.drawing_area.clear()

    def changeRadius(self):
        dialog = RadiusDialog(initialRadius=self.pen_radius, parent=self)
        button_pos = self.radius_button.mapToGlobal(QPoint(0, self.radius_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            self.pen_radius = dialog.getRadius()
            self.radius_button.setText(f"Radius: {self.pen_radius}")
            # Metin modundaysa input alanının font boyutunu güncelle
            if self.text_mode:
                self.drawing_area.text_input_field.setFont(QFont("Arial", max(10, self.pen_radius * 2)))

    def togglePressure(self):
        self.pen_pressure_enabled = not self.pen_pressure_enabled
        self.drawing_area.cancelImagePlacement() # Resim yerleştirme modunu iptal et
        self.updateButtonStyles()

    def toggleTextMode(self):
        self.text_mode = not self.text_mode
        if self.text_mode:
            self.eraser_mode = False # Metin moduna geçildiğinde silgi modunu kapat
            self.drawing_area.cancelImagePlacement() # Resim yerleştirme modunu iptal et
            self.drawing_area.text_input_field.setFont(QFont("Arial", max(10, self.pen_radius * 2)))
        else:
            self.drawing_area.text_input_field.hide() # Metin modundan çıkınca input alanını gizle
        self.updateButtonStyles()

    def updateButtonStyles(self):
        self.eraser_button.setStyleSheet(self.buttonStylePressure(self.eraser_mode))
        self.pressure_button.setStyleSheet(self.buttonStylePressure(self.pen_pressure_enabled))
        self.text_button.setStyleSheet(self.buttonStylePressure(self.text_mode))
        # Resim yerleştirme modu için File butonunun stilini güncelle
        if self.placing_image:
            self.file_button.setStyleSheet(self.buttonStylePressure(True))
        else:
            self.file_button.setStyleSheet(self.buttonStyle())


    def undo(self):
        self.drawing_area.undo()

    def redo(self):
        self.drawing_area.redo()

    def newDrawing(self):
        ret = QMessageBox.question(
            self, "Yeni Çizim", # Title updated to Turkish
            "Mevcut çizimi temizleyip yeni bir çizime başlamak ister misiniz?", # Message updated to Turkish
            QMessageBox.Yes | QMessageBox.No
        )
        if ret == QMessageBox.Yes:
            self.drawing_area.clear()

    def getCurrentPen(self):
        # GÜNCELLEME: Silgi rengini dinamik arkaplan renginden al
        color = self.background_color if self.eraser_mode else self.pen_color
        return color, self.pen_radius

    # YENİ: Arka plan/silgi rengini değiştirmek için
    def changeBackgroundColor(self, pos=None):
        """Arka plan ve silgi rengini değiştirmek için renk seçme diyaloğunu açar."""
        dialog = CircleBrightnessDialog(initialColor=self.background_color, parent=self)
        # Diyaloğu butonun altında konumlandır
        button_pos = self.eraser_button.mapToGlobal(QPoint(0, self.eraser_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            new_color = dialog.getSelectedColor()
            if self.background_color != new_color:
                self.background_color = new_color
                # Çizim alanını yeni arkaplan rengiyle yeniden çiz
                self.drawing_area.updateImageFromElements()

    # GÜNCELLEME: triggerCoreSwitcher fonksiyonu hatayı gidermek için değiştirildi.
    def triggerCoreSwitcher(self):
        """
        Drawing butonuna tıklandığında, ana pencerede 'showSwitcher()' varsa onu çağırarak
        farklı editörlere geçiş yapılabilir.
        """
        # self.window() metodu, mevcut widget'ın üst seviye penceresini (CoreWindow) bulur.
        main_window = self.window()
        # self.core_window_ref yerine doğrudan main_window'u kullan.
        # Bu, TextEditor'daki yaklaşımla tutarlıdır ve daha sağlamdır.
        if hasattr(main_window, 'showSwitcher'):
            main_window.showSwitcher()
        # Aksi takdirde, kullanıcıya bilgi mesajı göster.
        else:
            QMessageBox.information(self, "Bilgi", "Ana pencere referansı bulunamadı veya showSwitcher() metodu mevcut değil.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = DrawingEditorWindow()
    editor.show()
    sys.exit(app.exec_())

