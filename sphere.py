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
import random
import math
import json
import tarfile
import shutil
import tempfile
import io
import time

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QMessageBox, QSizePolicy, QListWidget, QListWidgetItem, QDialog, QComboBox,
    QGraphicsView, QGraphicsScene, QGraphicsProxyWidget, QGraphicsPathItem, QGraphicsItem, QSpacerItem,
    QMenu, QLineEdit, QProgressBar, QCheckBox
)
from PyQt5.QtCore import Qt, QDir, QPoint, QPointF, QRectF, QByteArray, QSize, QLineF, QEvent, QTimer
from PyQt5.QtGui import (
    QCursor, QPainter, QBrush, QPen, QColor, QPixmap, QIcon, QTransform, QPainterPath
)
from PyQt5.QtSvg import QSvgRenderer

# PyCryptodome kütüphanesini içe aktarmaya çalışın
try:
    from Crypto.Cipher import AES
    from Crypto.Protocol.KDF import PBKDF2
    from Crypto.Random import get_random_bytes
    from Crypto.Util.Padding import pad, unpad
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Uyarı: PyCryptodome kütüphanesi bulunamadı. Şifreleme/Şifre Çözme işlevleri devre dışı bırakılacaktır.")
    print("Yüklemek için: pip install pycryptodome")


# kare.py'den DraggableBox ve DraggableProxyWidget'ı içe aktarın
try:
    from kare import DraggableBox, DraggableProxyWidget
except ImportError:
    # Dummy sınıflar, eğer kare.py bulunamazsa uygulamanın çökmemesi için
    print("Warning: kare.py or DraggableBox/DraggableProxyWidget not found. Some functionalities may be limited.")
    class DraggableProxyWidget(QGraphicsProxyWidget):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.setFlag(QGraphicsItem.ItemIsMovable)
            self.setFlag(QGraphicsItem.ItemIsSelectable)
            self.undo_stack = None
        def mousePressEvent(self, event): super().mousePressEvent(event)
        def mouseMoveEvent(self, event): super().mouseMoveEvent(event)
        def mouseReleaseEvent(self, event): super().mouseReleaseEvent(event)

    class DraggableBox(QFrame):
        def __init__(self, parent_view=None, core_window_ref=None, box_id=None):
            super().__init__()
            self.proxy_widget = None
            self.box_id = box_id if box_id is not None else random.randint(1000, 9999)
            self.ports = {"top": QPointF(0,0), "bottom": QPointF(0,0), "left": QPointF(0,0), "right": QPointF(0,0)}
            self.selected_editor_name = None
            self.selected_file_path = None
            self.file_list_widget = QListWidget()
            self.name_input_area = QLineEdit()
            self.independent_checkbox = QCheckBox()
            self.editor_action_button = QPushButton()
            self.select_editor_button = QPushButton()
        def set_selected(self, selected): pass
        def get_port_scene_pos(self, port_name): return QPointF()
        def open_editor_file_dialog(self): pass
        def switch_to_selected_editor(self): pass
        def _on_editor_selected(self, editor_name): pass


# Core.py'dan CoreWindow'u içe aktarıyoruz
try:
    from Core import CoreWindow
except ImportError:
    class CoreWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.editor_map = { "Sphere": QWidget }
            self.editors_order = list(self.editor_map.keys())
            print("Warning: Core.py not found. Some functionalities may be limited.")
            self.stack = QVBoxLayout(self)
            self.dummy_widget = QWidget()
            self.stack.addWidget(self.dummy_widget)
        def switchToEditor(self, editor_name, close_current=False): pass
        def loadEditorFile(self, editor_name, file_path): pass


# --- Yardımcı Fonksiyonlar ve Sabitler ---

def create_svg_icon(svg_content, size=24, color="#eee"):
    modified_svg_content = svg_content.replace('stroke="#eee"', f'stroke="{color}"').replace('fill="#eee"', f'fill="{color}"')
    renderer = QSvgRenderer(QByteArray(modified_svg_content.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

SVG_ADD_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5V19M5 12H19" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_UNDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19C15.866 19 19 15.866 19 12C19 8.13401 15.866 5 12 5C8.13401 5 5 8.13401 5 12C5 13.7909 5.70014 15.4293 6.84594 16.6386L5 18M5 18H9M5 18V14" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_REDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5C8.13401 5 5 8.13401 5 12C5 15.866 8.13401 19 12 19C15.866 19 19 15.866 19 12C19 10.2091 18.2999 8.57074 17.1541 7.3614L19 6M19 6H15M19 6V10" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_FILE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M13 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 21.7893 5.46957 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V9L13 2Z" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 2V9H20" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""


# --- Undo/Redo Komut Sistemi ---
class Command:
    def do(self): raise NotImplementedError
    def undo(self): raise NotImplementedError

class AddBoxCommand(Command):
    def __init__(self, view, box, initial_proxy_pos):
        self.view = view
        self.box = box
        self.initial_proxy_pos = initial_proxy_pos
        self.connected_signals = False

    def do(self):
        if self.box not in self.view.boxes:
            self.view.boxes.append(self.box)
        if self.box.proxy_widget not in self.view.scene().items():
            self.view.scene().addItem(self.box.proxy_widget)
            self.box.proxy_widget.setPos(self.initial_proxy_pos)
            if not self.connected_signals:
                self.box.proxy_widget.xChanged.connect(self.view.update_connections_for_box)
                self.box.proxy_widget.yChanged.connect(self.view.update_connections_for_box)
                self.connected_signals = True
        self.view.parent_window.update_connection_dropdown()

    def undo(self):
        if self.box in self.view.boxes:
            if self.connected_signals:
                try:
                    self.box.proxy_widget.xChanged.disconnect(self.view.update_connections_for_box)
                    self.box.proxy_widget.yChanged.disconnect(self.view.update_connections_for_box)
                except TypeError: pass
                self.connected_signals = False
            conns_to_remove = [conn for conn in self.view.connections if conn.start_box == self.box or conn.end_box == self.box]
            for conn in conns_to_remove:
                if conn in self.view.connections:
                    self.view.connections.remove(conn)
                    self.view.scene().removeItem(conn)
            self.removed_connections = conns_to_remove
            if self.box in self.view.selected_boxes_list:
                self.view.selected_boxes_list.remove(self.box)
            self.view.boxes.remove(self.box)
            self.view.scene().removeItem(self.box.proxy_widget)
        self.view.parent_window.update_connection_dropdown()

class RemoveBoxCommand(Command):
    def __init__(self, view, box):
        self.view = view
        self.box = box
        self.original_proxy_pos = box.proxy_widget.pos() if box.proxy_widget else QPointF(0,0)
        self.removed_connections = []

    def do(self):
        if self.box in self.view.boxes:
            try:
                self.box.proxy_widget.xChanged.disconnect(self.view.update_connections_for_box)
                self.box.proxy_widget.yChanged.disconnect(self.view.update_connections_for_box)
            except TypeError: pass
            self.removed_connections = []
            for conn in list(self.view.connections):
                if conn.start_box == self.box or conn.end_box == self.box:
                    self.view.connections.remove(conn)
                    self.view.scene().removeItem(conn)
                    self.removed_connections.append(conn)
            if self.box in self.view.selected_boxes_list:
                self.view.selected_boxes_list.remove(self.box)
            self.view.boxes.remove(self.box)
            self.view.scene().removeItem(self.box.proxy_widget)
        self.view.parent_window.update_connection_dropdown()

    def undo(self):
        if self.box not in self.view.boxes:
            self.view.boxes.append(self.box)
            self.view.scene().addItem(self.box.proxy_widget)
            self.box.proxy_widget.setPos(self.original_proxy_pos)
            self.box.proxy_widget.xChanged.connect(self.view.update_connections_for_box)
            self.box.proxy_widget.yChanged.connect(self.view.update_connections_for_box)
            for conn in self.removed_connections:
                if conn not in self.view.connections:
                    self.view.connections.append(conn)
                    self.view.scene().addItem(conn)
                    conn.update_path()
        self.view.parent_window.update_connection_dropdown()

class MoveBoxCommand(Command):
    def __init__(self, box, old_pos, new_pos):
        self.box = box
        self.old_pos = old_pos
        self.new_pos = new_pos

    def do(self):
        if self.box.proxy_widget: self.box.proxy_widget.setPos(self.new_pos)
    def undo(self):
        if self.box.proxy_widget: self.box.proxy_widget.setPos(self.old_pos)

class MoveMultipleBoxesCommand(Command):
    def __init__(self, moves):
        # moves, {'box': box, 'old': old_pos, 'new': new_pos} sözlüklerinden oluşan bir listedir
        self.moves = moves

    def do(self):
        for move in self.moves:
            move['box'].proxy_widget.setPos(move['new'])

    def undo(self):
        for move in self.moves:
            move['box'].proxy_widget.setPos(move['old'])

class AddConnectionCommand(Command):
    def __init__(self, view, connection):
        self.view = view
        self.connection = connection

    def do(self):
        if self.connection not in self.view.connections:
            self.view.connections.append(self.connection)
            self.view.scene().addItem(self.connection)
            self.connection.update_path()
        self.view.parent_window.update_connection_dropdown()

    def undo(self):
        if self.connection in self.view.connections:
            self.view.connections.remove(self.connection)
            self.view.scene().removeItem(self.connection)
        self.view.parent_window.update_connection_dropdown()

class RemoveConnectionCommand(Command):
    def __init__(self, view, connection):
        self.view = view
        self.connection = connection

    def do(self):
        if self.connection in self.view.connections:
            self.view.connections.remove(self.connection)
            self.view.scene().removeItem(self.connection)
        self.view.parent_window.update_connection_dropdown()

    def undo(self):
        if self.connection not in self.view.connections:
            self.view.connections.append(self.connection)
            self.view.scene().addItem(self.connection)
            self.connection.update_path()
        self.view.parent_window.update_connection_dropdown()

class UndoStack:
    def __init__(self):
        self.stack = []
        self.index = -1
        self.max_size = 50

    def push(self, command):
        while len(self.stack) > self.index + 1: self.stack.pop()
        self.stack.append(command)
        self.index += 1
        if len(self.stack) > self.max_size:
            self.stack.pop(0)
            self.index -= 1
        command.do()

    def undo(self):
        if self.index >= 0:
            command = self.stack[self.index]
            command.undo()
            self.index -= 1

    def redo(self):
        if self.index < len(self.stack) - 1:
            self.index += 1
            command = self.stack[self.index]
            command.do()

# --- ConnectionItem ---
class ConnectionItem(QGraphicsPathItem):
    def __init__(self, start_box, start_port, end_box, end_port, color_type="default"):
        super().__init__()
        self.start_box = start_box
        self.start_port = start_port
        self.end_box = end_box
        self.end_port = end_port
        self.color_type = color_type
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.update_path()

    def paint(self, painter, option, widget=None):
        if self.isSelected():
            pen_color, pen_width = QColor(255, 100, 100), 4
        else:
            pen_color = QColor(255, 255, 0) if self.color_type == "special" else QColor(150, 200, 255)
            pen_width = 2
        pen = QPen(pen_color, pen_width)
        pen.setCapStyle(Qt.RoundCap)
        self.setPen(pen)
        super().paint(painter, option, widget)

    def update_path(self):
        p1 = self.start_box.get_port_scene_pos(self.start_port)
        p2 = self.end_box.get_port_scene_pos(self.end_port)
        path = QPainterPath()
        path.moveTo(p1)
        ext_amount = 75
        cp1, cp2 = QPointF(p1), QPointF(p2)
        if self.start_port == "right": cp1.setX(p1.x() + ext_amount)
        elif self.start_port == "left": cp1.setX(p1.x() - ext_amount)
        elif self.start_port == "bottom": cp1.setY(p1.y() + ext_amount)
        elif self.start_port == "top": cp1.setY(p1.y() - ext_amount)
        if self.end_port == "right": cp2.setX(p2.x() + ext_amount)
        elif self.end_port == "left": cp2.setX(p2.x() - ext_amount)
        elif self.end_port == "bottom": cp2.setY(p2.y() + ext_amount)
        elif self.end_port == "top": cp2.setY(p2.y() - ext_amount)
        path.cubicTo(cp1, cp2, p2)
        self.setPath(path)

# --- SphereView ---
class SphereView(QGraphicsView):
    GRID_SPACING = 50
    GRID_COLOR = QColor(60, 60, 60)
    PORT_COLOR = QColor(255, 105, 180)
    SNAP_DISTANCE = 30
    MAX_SELECTED_BOXES = 2

    def __init__(self, scene, parent_window, core_window_ref, undo_stack):
        super().__init__(scene)
        self.parent_window = parent_window
        self.core_window_ref = core_window_ref
        self.undo_stack = undo_stack
        self.boxes = []
        self.connections = []
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setBackgroundBrush(QColor("#1e1e1e"))
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.pan_active = False
        self.last_pan_pos = QPoint()
        self.connecting_line = None
        self.start_connection_info = None
        self.selected_boxes_list = []
        # Mouse move olaylarını, tuş basılı olmasa bile almak için
        self.setMouseTracking(True)

    def addDraggableBox(self, pos=None, editor_name=None, file_path=None, box_data=None):
        if pos is None:
            pos = self.mapToScene(self.viewport().rect().center())

        snapped_x = round(pos.x() / self.GRID_SPACING) * self.GRID_SPACING
        snapped_y = round(pos.y() / self.GRID_SPACING) * self.GRID_SPACING
        snapped_pos = QPointF(snapped_x, snapped_y)

        box = DraggableBox(parent_view=self, core_window_ref=self.core_window_ref)
        proxy = DraggableProxyWidget()
        proxy.setWidget(box)
        box.proxy_widget = proxy
        proxy.undo_stack = self.undo_stack

        if box_data:
            box.box_id = box_data.get("box_id", random.randint(1000, 9999))
            editor_name = box_data.get("editor_name")
            file_path = box_data.get("file_path")
            box.name_input_area.setPlainText(box_data.get("name_input", ""))
            box.independent_checkbox.setChecked(box_data.get("independent", False))
            snapped_pos = QPointF(box_data.get("pos_x", snapped_pos.x()), box_data.get("pos_y", snapped_pos.y()))

        if editor_name:
            box._on_editor_selected(editor_name)
        if file_path and os.path.exists(file_path):
            box.selected_file_path = file_path
            box.file_list_widget.clear()
            file_name = os.path.basename(file_path)
            item = QListWidgetItem(file_name)
            item.setData(Qt.UserRole, file_path)
            box.file_list_widget.addItem(item)
            box.file_list_widget.setCurrentItem(item)
            box.file_list_widget.show()
            box.name_input_area.show()
            box.independent_checkbox.show()
            box.editor_action_button.setText(editor_name)
            box.editor_action_button.show()
            box.select_editor_button.hide()

        if not box_data:
            command = AddBoxCommand(self, box, snapped_pos - QPointF(box.width()/2, box.height()/2))
            self.undo_stack.push(command)
        else:
            self.boxes.append(box)
            self.scene().addItem(proxy)
            proxy.setPos(snapped_pos)
            proxy.xChanged.connect(self.update_connections_for_box)
            proxy.yChanged.connect(self.update_connections_for_box)

        return box

    def removeBox(self, box_to_remove):
        command = RemoveBoxCommand(self, box_to_remove)
        self.undo_stack.push(command)

    def update_connections_for_box(self):
        proxy = self.sender()
        if not isinstance(proxy, QGraphicsProxyWidget): return
        box = proxy.widget()
        if not box: return
        for conn in self.connections:
            if conn.start_box == box or conn.end_box == box:
                conn.update_path()

    def get_box_at(self, pos):
        item = self.itemAt(pos)
        while item:
            if isinstance(item, QGraphicsProxyWidget):
                widget = item.widget()
                if isinstance(widget, DraggableBox):
                    return widget
            item = item.parentItem()
        return None

    def get_port_at(self, box, scene_pos):
        min_dist = float('inf')
        closest_port = None
        for name, local_pos in box.ports.items():
            port_scene_pos = box.proxy_widget.mapToScene(local_pos)
            dist = QLineF(scene_pos, port_scene_pos).length()
            if dist < self.SNAP_DISTANCE and dist < min_dist:
                min_dist = dist
                closest_port = name
        return closest_port

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            # --- DEĞİŞİKLİK ---
            # Kullanıcının isteği üzerine, orta tuşa basıldığında
            # alttaki öğenin ne olduğuna bakılmaksızın (kare olsa bile)
            # her zaman gezinme (pan) özelliğini aktifleştir.
            
            # item = self.itemAt(event.pos()) # Orijinal kontrol kaldırıldı
            # if isinstance(item, QGraphicsProxyWidget) and isinstance(item.widget(), DraggableBox): # Orijinal kontrol kaldırıldı
            #     self.pan_active = False
            #     super().mousePressEvent(event)
            #     return
            # else:
            
            # Doğrudan pan'ı aktifleştir
            self.pan_active = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
            # --- DEĞİŞİKLİK SONU ---

        if event.button() == Qt.RightButton:
            box = self.get_box_at(event.pos())
            if box:
                scene_pos = self.mapToScene(event.pos())
                port_name = self.get_port_at(box, scene_pos)
                if port_name:
                    self.start_connection(box, port_name)
                    event.accept()
                    return

        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if isinstance(item, QGraphicsProxyWidget):
                box = item.widget()
                if isinstance(box, DraggableBox):
                    if box not in self.selected_boxes_list:
                        if len(self.selected_boxes_list) >= self.MAX_SELECTED_BOXES:
                            oldest_selected_box = self.selected_boxes_list.pop(0)
                            oldest_selected_box.proxy_widget.setSelected(False)
                            oldest_selected_box.set_selected(False)
                        self.selected_boxes_list.append(box)
                        item.setSelected(True)
                        box.set_selected(True)
                    else:
                        self.selected_boxes_list.remove(box)
                        item.setSelected(False)
                        box.set_selected(False)
            else:
                for box in self.selected_boxes_list:
                    box.proxy_widget.setSelected(False)
                    box.set_selected(False)
                self.selected_boxes_list.clear()

            super().mousePressEvent(event)
            self.update_selection_visuals()
            return

        super().mousePressEvent(event)
        self.update_selection_visuals()

    def mouseMoveEvent(self, event):
        # Shift'e basılıyken tıklama olmadan zoom yapma
        if QApplication.keyboardModifiers() == Qt.ShiftModifier and not event.buttons():
            center_x = self.viewport().width() / 2
            delta_from_center = event.pos().x() - center_x

            # Merkezde yakınlaştırmayı durdurmak için 50 piksellik bir "nötr bölge"
            neutral_zone_width = 50

            if abs(delta_from_center) < neutral_zone_width:
                # Nötr bölgedeyse hiçbir şey yapma
                event.accept()
                return

            # Nötr bölgenin dışındaki mesafeye göre delta'yı ayarla
            if delta_from_center > 0:
                adjusted_delta = delta_from_center - neutral_zone_width
            else:
                adjusted_delta = delta_from_center + neutral_zone_width

            # Hassasiyeti düşürerek daha yavaş ve kontrollü bir zoom sağlayalım
            sensitivity = 0.0007

            zoom_factor = 1.0 - (adjusted_delta * sensitivity)

            # Maksimum zoom hızını sınırlayarak ani sıçramaları önleyelim
            # Bu, daha pürüzsüz bir deneyim sunar
            zoom_factor = max(0.99, min(1.01, zoom_factor))

            original_anchor = self.transformationAnchor()
            # Yakınlaştırmanın merkezden yapılmasını sağlıyoruz
            self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
            self.scale(zoom_factor, zoom_factor)
            # Orijinal anchor ayarını geri yüklüyoruz
            self.setTransformationAnchor(original_anchor)

            event.accept()
            return

        if self.pan_active:
            delta = event.pos() - self.last_pan_pos
            self.last_pan_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        if self.connecting_line:
            p2 = self.mapToScene(event.pos())
            path = QPainterPath()
            path.moveTo(self.connecting_line.start_pos)
            path.lineTo(p2)
            self.connecting_line.setPath(path)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            if self.pan_active:
                self.pan_active = False
                self.setCursor(Qt.ArrowCursor)
                event.accept()
                return

        if self.connecting_line and event.button() == Qt.RightButton:
            self.end_connection(self.mapToScene(event.pos()))

        self.cancel_connection()
        super().mouseReleaseEvent(event)

    def start_connection(self, start_box, start_port):
        self.start_connection_info = (start_box, start_port)
        self.connecting_line = QGraphicsPathItem()
        pen = QPen(self.PORT_COLOR, 2, Qt.DotLine)
        self.connecting_line.setPen(pen)
        self.connecting_line.start_pos = start_box.get_port_scene_pos(start_port)
        self.scene().addItem(self.connecting_line)

    def end_connection(self, scene_pos):
        box = self.get_box_at(self.mapFromScene(scene_pos))
        if box and self.start_connection_info:
            start_box, start_port = self.start_connection_info
            if box != start_box:
                end_port = self.get_port_at(box, scene_pos)
                if end_port:
                    connection = ConnectionItem(start_box, start_port, box, end_port)
                    command = AddConnectionCommand(self, connection)
                    self.undo_stack.push(command)

    def cancel_connection(self):
        if self.connecting_line:
            self.scene().removeItem(self.connecting_line)
            self.connecting_line = None
        self.start_connection_info = None

    def create_connection(self, start_box, start_port, end_box, end_port, color_type="default"):
        for conn in self.connections:
            if (conn.start_box, conn.start_port, conn.end_box, conn.end_port) in [
                (start_box, start_port, end_box, end_port),
                (end_box, end_port, start_box, start_port)
            ]:
                return
        connection = ConnectionItem(start_box, start_port, end_box, end_port, color_type)
        self.connections.append(connection)
        self.scene().addItem(connection)
        self.parent_window.update_connection_dropdown()

    def update_selection_visuals(self):
        for box in self.boxes:
            box.set_selected(box in self.selected_boxes_list)

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ShiftModifier and len(self.selected_boxes_list) > 0:
            delta = QPointF(0, 0)
            key_map = {
                Qt.Key_Up: QPointF(0, -self.GRID_SPACING),
                Qt.Key_Down: QPointF(0, self.GRID_SPACING),
                Qt.Key_Left: QPointF(-self.GRID_SPACING, 0),
                Qt.Key_Right: QPointF(self.GRID_SPACING, 0)
            }
            delta = key_map.get(event.key())

            if delta:
                moves = []
                for box in self.selected_boxes_list:
                    old_pos = box.proxy_widget.pos()
                    new_pos = old_pos + delta
                    moves.append({'box': box, 'old': old_pos, 'new': new_pos})

                if moves:
                    command = MoveMultipleBoxesCommand(moves)
                    self.undo_stack.push(command)
                event.accept()
                return

        if event.modifiers() == Qt.AltModifier and event.key() == Qt.Key_F:
            self.connect_selected_boxes()
        elif event.key() == Qt.Key_Delete:
            self.delete_selected_items()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Z:
            self.undo_stack.undo()
        elif event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Y:
            self.undo_stack.redo()
        else:
             super().keyPressEvent(event)



    def connect_selected_boxes(self):
        if len(self.selected_boxes_list) != 2: return
        box1, box2 = self.selected_boxes_list[0], self.selected_boxes_list[1]
        min_dist, best_ports = float('inf'), None
        for p1_name in box1.ports:
            for p2_name in box2.ports:
                dist = QLineF(box1.get_port_scene_pos(p1_name), box2.get_port_scene_pos(p2_name)).length()
                if dist < min_dist:
                    min_dist, best_ports = dist, (p1_name, p2_name)
        if best_ports:
            connection = ConnectionItem(box1, best_ports[0], box2, best_ports[1], color_type="special")
            command = AddConnectionCommand(self, connection)
            self.undo_stack.push(command)
            for box in self.selected_boxes_list:
                box.proxy_widget.setSelected(False)
                box.set_selected(False)
            self.selected_boxes_list.clear()
            self.update_selection_visuals()

    def delete_selected_items(self):
        items_to_delete = list(self.scene().selectedItems())
        for item in items_to_delete:
            if isinstance(item, ConnectionItem):
                command = RemoveConnectionCommand(self, item)
                self.undo_stack.push(command)
            elif isinstance(item, QGraphicsProxyWidget):
                self.removeBox(item.widget())
        self.parent_window.update_connection_dropdown()

    def wheelEvent(self, event):
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(zoom_factor, zoom_factor)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        scene_rect = self.sceneRect()
        grid_size = self.GRID_SPACING
        pen_width = 1.0 / self.transform().m11()
        visible_rect = rect.intersected(scene_rect)
        painter.setPen(QPen(self.GRID_COLOR, pen_width))
        left = int(visible_rect.left() / grid_size)
        right = int(visible_rect.right() / grid_size)
        top = int(visible_rect.top() / grid_size)
        bottom = int(visible_rect.bottom() / grid_size)
        for x in range(left, right + 1):
            painter.drawLine(QPointF(x * grid_size, scene_rect.top()), QPointF(x * grid_size, scene_rect.bottom()))
        for y in range(top, bottom + 1):
            painter.drawLine(QPointF(scene_rect.left(), y * grid_size), QPointF(scene_rect.right(), y * grid_size))

    def buttonStyle(self): return self.parent_window.buttonStyle()
    def buttonStyleMini(self): return self.parent_window.buttonStyleMini()


# --- Export/Import Dialogs ---
class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Şifre Gerekli")
        self.setModal(True)
        self.setFixedSize(350, 120)
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; border: 2px solid #555; border-radius: 8px; }
            QLabel { color: #f0f0f0; font-size: 14px; }
            QLineEdit { background-color: #333; color: #eee; border: 1px solid #555; border-radius: 4px; padding: 5px; }
            QPushButton { background-color: #3a3a3a; color: #ffffff; border: 1px solid #555; border-radius: 6px; padding: 6px 15px; }
            QPushButton:hover { background-color: #555555; }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(20, 15, 20, 15)

        self.password_label = QLabel("Lütfen şifreyi girin:")
        self.layout.addWidget(self.password_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.password_input)
        self.password_input.returnPressed.connect(self.accept)

        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()
        self.ok_button = QPushButton("Tamam")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("İptal")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)

    def get_password(self):
        return self.password_input.text()

class OperationProgressDialog(QDialog):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(400, 120)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint & ~Qt.WindowCloseButtonHint)
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; border: 2px solid #555; border-radius: 8px; }
            QLabel { color: #f0f0f0; font-size: 14px; }
            QProgressBar { border: 1px solid #555; border-radius: 5px; text-align: center; color: #fff; height: 25px;}
            QProgressBar::chunk { background-color: #4CAF50; border-radius: 5px; }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.addStretch()

        self.progress_label = QLabel("İşlem başlatılıyor...")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)
        self.layout.addStretch()

    def update_progress(self, value, message=""):
        self.progress_bar.setValue(value)
        if message:
            self.progress_label.setText(message)
        QApplication.processEvents()

# --- Encryption/Decryption Functions ---
SALT_SIZE = 16
ITERATIONS = 100000
KEY_SIZE = 32

def derive_key(password, salt):
    password_bytes = password.encode('utf-8') if password else b''
    return PBKDF2(password_bytes, salt, dkLen=KEY_SIZE, count=ITERATIONS)

def encrypt_data(data, password):
    if not CRYPTO_AVAILABLE: raise ImportError("PyCryptodome library not found.")
    salt = get_random_bytes(SALT_SIZE)
    key = derive_key(password, salt)
    cipher = AES.new(key, AES.MODE_CBC)
    padded_data = pad(data, AES.block_size)
    ciphertext = cipher.encrypt(padded_data)
    return salt + cipher.iv + ciphertext

def decrypt_data(encrypted_data, password):
    if not CRYPTO_AVAILABLE: raise ImportError("PyCryptodome library not found.")
    salt = encrypted_data[:SALT_SIZE]
    iv = encrypted_data[SALT_SIZE:SALT_SIZE + AES.block_size]
    ciphertext = encrypted_data[SALT_SIZE + AES.block_size:]
    key = derive_key(password, salt)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_padded_data = cipher.decrypt(ciphertext)
    return unpad(decrypted_padded_data, AES.block_size)


# --- SphereWindow (Main Window) ---
class SphereWindow(QWidget):
    DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')

    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        self.undo_stack = UndoStack()
        self.initUI()
        self.add_initial_boxes()
        self.update_connection_dropdown()
        if not CRYPTO_AVAILABLE:
            self.show_error_message("PyCryptodome kütüphanesi bulunamadı. Lütfen yükleyin: pip install pycryptodome")
            self.export_button.setEnabled(False)

    def initUI(self):
        self.setWindowTitle("Kavram")
        self.resize(1200, 800)
        self.setStyleSheet("background-color: #1e1e1e; color: #f0f0f0; border: none;")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.toolbar_frame = QFrame()
        self.toolbar_frame.setStyleSheet("background-color: #222; border-bottom: 2px solid #555;")
        self.toolbar_frame.setFixedHeight(40)
        self.toolbar_layout = QHBoxLayout(self.toolbar_frame)
        self.toolbar_layout.setContentsMargins(10, 5, 10, 5)
        self.toolbar_layout.setSpacing(10)

        self.file_button = QPushButton("File")
        self.file_button.setStyleSheet(self.buttonStyle())
        self.file_button.setFixedSize(90, 30)
        self.file_button.clicked.connect(self.open_file_dialog_for_new_box)
        self.toolbar_layout.addWidget(self.file_button)

        self.undo_button = QPushButton()
        self.undo_button.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20))
        self.undo_button.setStyleSheet(self.buttonStyleMini())
        self.undo_button.setFixedSize(30, 30)
        self.undo_button.clicked.connect(self.undo_stack.undo)
        self.toolbar_layout.addWidget(self.undo_button)

        self.redo_button = QPushButton()
        self.redo_button.setIcon(create_svg_icon(SVG_REDO_ICON, size=20))
        self.redo_button.setStyleSheet(self.buttonStyleMini())
        self.redo_button.setFixedSize(30, 30)
        self.redo_button.clicked.connect(self.undo_stack.redo)
        self.toolbar_layout.addWidget(self.redo_button)

        self.add_box_button = QPushButton()
        self.add_box_button.setIcon(create_svg_icon(SVG_ADD_ICON, size=20))
        self.add_box_button.setStyleSheet(self.buttonStyleMini())
        self.add_box_button.setFixedSize(30, 30)
        self.add_box_button.clicked.connect(lambda: self.view.addDraggableBox())
        self.toolbar_layout.addWidget(self.add_box_button)

        self.connection_dropdown = QComboBox()
        self.connection_dropdown.setStyleSheet(self.buttonStyle())
        self.connection_dropdown.setFixedSize(180, 30)
        self.connection_dropdown.currentIndexChanged.connect(self.zoom_to_connection_by_index)
        self.toolbar_layout.addWidget(self.connection_dropdown)

        self.toolbar_layout.addStretch()

        self.export_button = QPushButton("Export")
        self.export_button.setStyleSheet(self.buttonStyle())
        self.export_button.setFixedSize(90, 30)
        self.export_button.clicked.connect(self.export_data)
        self.toolbar_layout.addWidget(self.export_button)

        self.sphere_button = QPushButton("Sphere")
        self.sphere_button.setStyleSheet(self.buttonStyle())
        self.sphere_button.setFixedSize(90, 30)
        self.sphere_button.clicked.connect(self.triggerCoreSwitcher)
        self.toolbar_layout.addWidget(self.sphere_button)

        self.layout.addWidget(self.toolbar_frame)

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.view = SphereView(self.scene, self, self.core_window_ref, self.undo_stack)
        self.layout.addWidget(self.view)

    def _handle_file_path(self, source_path):
        """
        Dosyayı, varsayılan dizinde değilse, oraya kopyalar.
        Her zaman varsayılan dizindeki dosyanın yolunu döndürür.
        """
        if not source_path or not os.path.exists(source_path):
            return None

        target_dir = self.DEFAULT_BASE_DIR
        os.makedirs(target_dir, exist_ok=True)
        file_name = os.path.basename(source_path)
        dest_path = os.path.join(target_dir, file_name)

        # Eğer dosya zaten hedef dizindeyse, kopyalamaya gerek yok.
        if os.path.normpath(source_path) == os.path.normpath(dest_path):
            return source_path

        try:
            # shutil.copy2, meta verileri de korur.
            shutil.copy2(source_path, dest_path)
            self.show_info_message(f"'{file_name}' dosyasının bir kopyası\n{target_dir} klasörüne oluşturuldu.")
            return dest_path
        except Exception as e:
            self.show_error_message(f"Dosya kopyalanamadı: {e}")
            return None

    def export_data(self):
        if not CRYPTO_AVAILABLE:
            self.show_error_message("Dışa aktarma için PyCryptodome kütüphanesi gerekli.")
            return

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Kitap Dosyasını Kaydet",
            self.DEFAULT_BASE_DIR, # Varsayılan dizin
            "Kitap Files (*.kitap);;All Files (*)", options=options)

        if not file_name: return
        if not file_name.lower().endswith(".kitap"): file_name += ".kitap"

        password_dialog = PasswordDialog(self)
        if password_dialog.exec_() != QDialog.Accepted:
            return
        password = password_dialog.get_password()

        progress_dialog = OperationProgressDialog("Dışa Aktarılıyor", self)
        progress_dialog.show()

        temp_dir = tempfile.mkdtemp()
        try:
            progress_dialog.update_progress(10, "Veriler toplanıyor...")
            boxes_data, files_to_copy = [], set()
            for box in self.view.boxes:
                file_path = box.selected_file_path
                file_basename = os.path.basename(file_path) if file_path and os.path.exists(file_path) else None
                if file_basename: files_to_copy.add(file_path)

                proxy_pos = box.proxy_widget.pos()
                boxes_data.append({
                    "box_id": box.box_id, "editor_name": box.selected_editor_name,
                    "file_path": file_basename, "name_input": box.name_input_area.toPlainText(),
                    "independent": box.independent_checkbox.isChecked(),
                    "pos_x": proxy_pos.x(), "pos_y": proxy_pos.y()
                })

            connections_data = [{"start_box_id": c.start_box.box_id, "start_port": c.start_port,
                                 "end_box_id": c.end_box.box_id, "end_port": c.end_port,
                                 "color_type": c.color_type} for c in self.view.connections]

            final_data = json.dumps({"boxes": boxes_data, "connections": connections_data}, indent=4).encode('utf-8')
            with open(os.path.join(temp_dir, "data.json"), "wb") as f: f.write(final_data)

            progress_dialog.update_progress(30, "Dosyalar arşivleniyor...")
            for file_path in files_to_copy:
                shutil.copy2(file_path, os.path.join(temp_dir, os.path.basename(file_path)))

            progress_dialog.update_progress(60, "Arşiv sıkıştırılıyor...")
            with tarfile.open(file_name + ".tmp", "w:xz") as tar:
                tar.add(temp_dir, arcname='.')

            progress_dialog.update_progress(80, "Veri şifreleniyor...")
            with open(file_name + ".tmp", "rb") as f: tar_data = f.read()
            encrypted_data = encrypt_data(tar_data, password)

            with open(file_name, "wb") as f: f.write(b"KITAP_V1 " + encrypted_data)

            progress_dialog.update_progress(100, "Tamamlandı!")
            time.sleep(0.5)
            self.show_info_message(f"Proje başarıyla '{os.path.basename(file_name)}' olarak dışa aktarıldı.")

        except Exception as e:
            self.show_error_message(f"Dışa aktarma sırasında hata: {e}")
        finally:
            if os.path.exists(file_name + ".tmp"): os.remove(file_name + ".tmp")
            shutil.rmtree(temp_dir)
            progress_dialog.close()

    def import_project_file(self, file_path):
        if not CRYPTO_AVAILABLE:
            self.show_error_message("İçe aktarma için PyCryptodome kütüphanesi gerekli.")
            return

        progress_dialog = None
        try:
            with open(file_path, "rb") as f:
                header = f.read(9)
                if header not in (b"KAVRAM_V3", b"KITAP_V1 "):
                    self.show_error_message("Geçersiz veya desteklenmeyen .kitap veya .kavram dosyası formatı.")
                    return
                encrypted_data = f.read()

            file_size = len(encrypted_data)
            simulated_duration_ms = max(1500, min(10000, (file_size / (5 * 1024 * 1024)) * 1000))
            
            import_successful = False
            for attempt in range(3):
                password_dialog = PasswordDialog(self)
                if password_dialog.exec_() != QDialog.Accepted:
                    return
                password = password_dialog.get_password()
                
                progress_dialog = OperationProgressDialog("İçe Aktarılıyor", self)
                progress_dialog.show()

                decryption_result = None
                decryption_error = None

                try:
                    decrypted_data = decrypt_data(encrypted_data, password)
                    decryption_result = decrypted_data
                except Exception as e:
                    decryption_error = e

                start_time = time.time()
                while (time.time() - start_time) * 1000 < simulated_duration_ms:
                    elapsed_ms = (time.time() - start_time) * 1000
                    progress_value = int((elapsed_ms / simulated_duration_ms) * 100)
                    progress_dialog.update_progress(progress_value, "Dosya doğrulanıyor ve açılıyor...")
                    time.sleep(0.02)
                
                progress_dialog.update_progress(100, "İşlem tamamlanıyor...")
                time.sleep(0.1)

                if decryption_error is None:
                    try:
                        progress_dialog.update_progress(100, "Arşiv açılıyor...")
                        with tarfile.open(fileobj=io.BytesIO(decryption_result), mode="r:xz") as tar:
                            tar.extractall(path=self.DEFAULT_BASE_DIR)

                        json_path = os.path.join(self.DEFAULT_BASE_DIR, "data.json")
                        with open(json_path, "r", encoding='utf-8') as f:
                            loaded_data = json.load(f)
                        os.remove(json_path)

                        progress_dialog.update_progress(100, "Sahne yükleniyor...")
                        self._clear_all_boxes_and_connections()
                        recreated_boxes = {}
                        
                        for box_data in loaded_data.get("boxes", []):
                            file_basename = box_data.get("file_path")
                            new_abs_path = os.path.join(self.DEFAULT_BASE_DIR, file_basename) if file_basename else None
                            if new_abs_path and not os.path.exists(new_abs_path):
                                print(f"Uyarı: '{new_abs_path}' bulunamadı.")
                                new_abs_path = None
                            box_data["file_path"] = new_abs_path
                            box = self.view.addDraggableBox(box_data=box_data)
                            recreated_boxes[box_data["box_id"]] = box

                        for conn_data in loaded_data.get("connections", []):
                            start_box = recreated_boxes.get(conn_data["start_box_id"])
                            end_box = recreated_boxes.get(conn_data["end_box_id"])
                            if start_box and end_box:
                                conn = ConnectionItem(start_box, conn_data["start_port"], end_box, conn_data["end_port"], conn_data.get("color_type", "default"))
                                self.view.connections.append(conn)
                                self.view.scene().addItem(conn)
                                conn.update_path()

                        self.update_connection_dropdown()
                        progress_dialog.update_progress(100, "Tamamlandı!")
                        time.sleep(0.5)
                        import_successful = True
                        break
                    except Exception as e:
                        progress_dialog.close()
                        self.show_error_message(f"Dosya başarıyla çözüldü ancak içeriği bozuk görünüyor: {e}")
                        return
                else:
                    progress_dialog.close()
                    print(f"İçe aktarma hatası (deneme {attempt + 1}): {decryption_error}")
                    self.show_warning_message(f"Şifre yanlış veya dosya bozuk.\nKalan deneme hakkı: {2 - attempt}")
            
            if progress_dialog: progress_dialog.close()

            if not import_successful and attempt == 2:
                 self.show_error_message("3 hatalı şifre denemesi. İçe aktarma iptal edildi.")

        except Exception as e:
            self.show_error_message(f"İçe aktarma sırasında beklenmedik bir hata oluştu: {e}")
            if progress_dialog is not None and progress_dialog.isVisible():
                 progress_dialog.close()

    def open_file_dialog_for_new_box(self):
        QDir().mkpath(self.DEFAULT_BASE_DIR)
        options = QFileDialog.Options()
        file_filter = "All Supported Files (*.kitap *.kavram *.txt *.png *.jpg *.jpeg *.bmp *.gif *.ai *.saund *.wav *.aiff *.flac *.ogg *.mp3 *.media *.mp4 *.avi *.mov *.mkv *.webm *.flv *.rec *.aac *.m4a *.copya);;Kitap Files (*.kitap);;Kavram Files (*.kavram);;All Files (*)"

        selected_file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Dosya Seç veya Proje İçe Aktar",
            self.DEFAULT_BASE_DIR, # Varsayılan dizin
            file_filter,
            options=options
        )

        if not selected_file_paths:
            return

        project_files = [path for path in selected_file_paths if path.lower().endswith((".kitap", ".kavram"))]

        if len(project_files) > 1:
            self.show_error_message("Aynı anda sadece bir tane proje dosyası (.kitap veya .kavram) içe aktarabilirsiniz.")
            return

        if len(project_files) == 1 and len(selected_file_paths) > 1:
            self.show_error_message("Proje dosyası (.kitap veya .kavram), diğer dosyalarla birlikte içe aktarılamaz.")
            return

        if len(project_files) == 1:
            self.import_project_file(project_files[0])
            return

        unsupported_files = []
        for path in selected_file_paths:
            final_path = self._handle_file_path(path)
            if not final_path:
                continue

            file_extension = os.path.splitext(final_path)[1].lower()
            editor_map = {
                ".copya": "Copy", ".rec": "Rec", ".txt": "Text",
                ".png": "Drawing", ".jpg": "Drawing", ".jpeg": "Drawing", ".bmp": "Drawing", ".gif": "Drawing",
                ".ai": "Ai",
                ".saund": "Sound", ".wav": "Sound", ".aiff": "Sound", ".flac": "Sound", ".ogg": "Sound", ".mp3": "Sound", ".aac": "Sound", ".m4a": "Sound",
                ".media": "Media", ".mp4": "Media", ".avi": "Media", ".mov": "Media", ".mkv": "Media", ".webm": "Media", ".flv": "Media"
            }
            editor_name = editor_map.get(file_extension)

            if editor_name:
                self.view.addDraggableBox(editor_name=editor_name, file_path=final_path)
            else:
                unsupported_files.append(os.path.basename(path))

        if unsupported_files:
            self.show_warning_message(f"Aşağıdaki dosyalar için desteklenen bir editör bulunamadı ve atlandı:\n\n" + "\n".join(unsupported_files))


    def _clear_all_boxes_and_connections(self):
        for conn in list(self.view.connections):
            self.view.connections.remove(conn)
            self.view.scene().removeItem(conn)
        for box in list(self.view.boxes):
            self.view.boxes.remove(box)
            if box.proxy_widget:
                self.view.scene().removeItem(box.proxy_widget)
                box.proxy_widget.deleteLater()
        self.view.selected_boxes_list.clear()
        self.undo_stack = UndoStack()
        self.view.undo_stack = self.undo_stack
        self.update_connection_dropdown()

    def add_initial_boxes(self):
        self.view.addDraggableBox(pos=QPointF(-200, -100))
        self.view.addDraggableBox(pos=QPointF(200, -100))

    def update_connection_dropdown(self):
        self.connection_dropdown.blockSignals(True)
        self.connection_dropdown.clear()
        self.connection_dropdown.addItem("Select Connection")
        if not self.view.connections:
            self.connection_dropdown.setEnabled(False)
        else:
            self.connection_dropdown.setEnabled(True)
            for i, conn in enumerate(self.view.connections):
                start_id = conn.start_box.box_id if conn.start_box else 'N/A'
                end_id = conn.end_box.box_id if conn.end_box else 'N/A'
                item_text = f"Conn {i+1}: {start_id} -> {end_id}"
                self.connection_dropdown.addItem(item_text, i)
        self.connection_dropdown.blockSignals(False)

    def zoom_to_connection_by_index(self, index):
        if index <= 0: return
        conn_index = self.connection_dropdown.itemData(index)
        if 0 <= conn_index < len(self.view.connections):
            conn = self.view.connections[conn_index]
            self.view.fitInView(conn.boundingRect(), Qt.KeepAspectRatio)
        self.connection_dropdown.setCurrentIndex(0)

    def triggerCoreSwitcher(self):
        main_window = self.window()
        if hasattr(main_window, 'showSwitcher'):
            main_window.showSwitcher()

    def show_error_message(self, text, parent=None):
        msg_box = QMessageBox(parent or self)
        msg_box.setWindowTitle("Hata")
        msg_box.setText(text)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setStyleSheet(self.messageBoxStyle())
        msg_box.exec_()

    def show_info_message(self, text, parent=None):
        msg_box = QMessageBox(parent or self)
        msg_box.setWindowTitle("Bilgi")
        msg_box.setText(text)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setStyleSheet(self.messageBoxStyle())
        msg_box.exec_()

    def show_warning_message(self, text, parent=None):
        msg_box = QMessageBox(parent or self)
        msg_box.setWindowTitle("Uyarı")
        msg_box.setText(text)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.setStyleSheet(self.messageBoxStyle())
        msg_box.exec_()

    def messageBoxStyle(self):
        return """
            QMessageBox { background-color: #2b2b2b; border: 2px solid #555; border-radius: 8px; }
            QMessageBox QLabel { color: #f0f0f0; font-size: 14px; min-width: 300px;}
            QMessageBox QPushButton { background-color: #3a3a3a; color: #ffffff; border: 1px solid #555; border-radius: 6px; padding: 6px 10px; min-width: 60px; }
            QMessageBox QPushButton:hover { background-color: #555555; }
        """

    def menuStyle(self):
        return """
            QMenu { background-color: #282828; border: 1px solid #555; color: white; }
            QMenu::item:selected { background-color: #444; }
        """

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
            QComboBox::down-arrow { image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTcgMTBMMTIgMTVMMTcgMTAiIHN0cm9rZT0iI2VlZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPj4=); width: 16px; height: 16px; }
            QComboBox QAbstractItemView { background-color: #282828; border: 1px solid #555; selection-background-color: #444; color: white; }
        """

    def buttonStyleMini(self):
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 16px;
                border: 2px solid #555; border-radius: 8px; padding: 5px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = CoreWindow()
    main_window.show()
    sys.exit(app.exec_())

