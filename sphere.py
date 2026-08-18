# sphere.py - tam dosya
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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
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
import random
import math
import json
import tarfile
import shutil
import tempfile
import io
import time
import re
import unicodedata

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QMessageBox, QSizePolicy, QListWidget, QListWidgetItem, QDialog, QComboBox,
    QGraphicsView, QGraphicsScene, QGraphicsProxyWidget, QGraphicsPathItem, QGraphicsRectItem, QGraphicsItem, QSpacerItem,
    QMenu, QLineEdit, QProgressBar, QCheckBox, QAction, QTextEdit, QInputDialog
)
from PyQt5.QtCore import Qt, QDir, QPoint, QPointF, QRectF, QByteArray, QSize, QLineF, QEvent, QTimer, pyqtSignal, QSettings
from PyQt5.QtGui import (
    QCursor, QPainter, QBrush, QPen, QColor, QPixmap, QIcon, QTransform, QPainterPath, QTextCursor
)
from PyQt5.QtSvg import QSvgRenderer

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

try:
    from kare import DraggableBox, DraggableProxyWidget
except ImportError:
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
            self.timestamp_text = ""
        def set_selected(self, selected): pass
        def get_port_scene_pos(self, port_name): return QPointF()
        def open_editor_file_dialog(self): pass
        def switch_to_selected_editor(self): pass
        def _on_editor_selected(self, editor_name): pass
        def generate_timestamp_string(self): return ""

try:
    from Kavram import CoreWindow
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
        def ensureEditorInstantiated(self, editor_name): pass

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
SVG_SAVE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M19 21H5C3.89543 21 3 20.1046 3 19V5C3 3.89543 3.89543 3 5 3H16L21 8V19C21 20.1046 20.1046 21 19 21Z" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M17 21V13H7V21" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M7 3V8H15" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

SVG_EYE_OPEN = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M1 12S5 4 12 4s11 8 11 8-4 8-11 8-11-8-11-8z" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_EYE_CLOSED = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24M1 1l22 22" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

class TerminalTextEdit(QTextEdit):
    commandEntered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Komut girin...")
        self.history = []
        self.history_index = len(self.history)
        self.last_temp_command = ""

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() == Qt.NoModifier:
                command = self.toPlainText().strip()
                if command:
                    self.commandEntered.emit(command)
                    if command not in self.history:
                         self.history.append(command)
                    self.history_index = len(self.history)
                    self.last_temp_command = ""
                return

        elif event.key() == Qt.Key_Up:
            if self.history:
                if self.history_index == len(self.history):
                    self.last_temp_command = self.toPlainText()
                self.history_index -= 1
                if self.history_index < 0:
                    self.history_index = len(self.history) - 1
                self.setPlainText(self.history[self.history_index])
                self.moveCursorToEnd()
            return

        elif event.key() == Qt.Key_Down:
            if self.history:
                self.history_index += 1
                if self.history_index >= len(self.history):
                    self.history_index = 0
                self.setPlainText(self.history[self.history_index])
                self.moveCursorToEnd()
            return

        super().keyPressEvent(event)

    def moveCursorToEnd(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)

class TerminalDialog(QDialog):
    commandEntered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Terminal")
        self.setStyleSheet("""
            QDialog {
                background-color: #222;
                border: 1px solid #555;
            }
            QLabel {
                color: #aaa;
                font-family: monospace;
            }
        """)
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.terminal_text = TerminalTextEdit(self)
        self.terminal_text.setStyleSheet("""
            QTextEdit {
                background-color: #111;
                color: #ddd;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                border: 1px solid #444;
                padding: 5px;
            }
            QTextEdit:focus {
                border: 1px solid #666;
            }
        """)
        self.terminal_text.setFocusPolicy(Qt.StrongFocus)
        self.terminal_text.setFocus()
        self.terminal_text.commandEntered.connect(self.handleCommand)
        layout.addWidget(self.terminal_text)

        self.setLayout(layout)

    def handleCommand(self, cmd):
        self.commandEntered.emit(cmd)
        self.terminal_text.clear()

class Command:
    def do(self): raise NotImplementedError
    def undo(self): raise NotImplementedError

class AddBoxCommand(Command):
    def __init__(self, view, box, initial_proxy_pos):
        self.view = view
        self.box = box
        self.initial_proxy_pos = initial_proxy_pos
        self.connected_signals = False
        self.removed_connections = []

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

        for conn in getattr(self, 'removed_connections', []):
            if conn not in self.view.connections:
                self.view.connections.append(conn)
                self.view.scene().addItem(conn)
                conn.update_path()
        self.removed_connections.clear()

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

            self.removed_connections = conns_to_remove[:]

            for conn in conns_to_remove:
                if conn in self.view.connections:
                    self.view.connections.remove(conn)
                    self.view.scene().removeItem(conn)

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
        
        # Scrollbar stilleri - ince ve yuvarlak köşeli
        self.setStyleSheet("""
            QScrollBar:vertical {
                background: transparent;
                width: 10px;
                margin: 0px;
                border: none;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.2);
                min-height: 30px;
                border-radius: 3px;
                margin: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.35);
            }
            QScrollBar::handle:vertical:pressed {
                background: rgba(255, 255, 255, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QScrollBar:horizontal {
                background: transparent;
                height: 10px;
                margin: 0px;
                border: none;
                border-radius: 3px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(255, 255, 255, 0.2);
                min-width: 30px;
                border-radius: 3px;
                margin: 2px;
            }
            QScrollBar::handle:horizontal:hover {
                background: rgba(255, 255, 255, 0.35);
            }
            QScrollBar::handle:horizontal:pressed {
                background: rgba(255, 255, 255, 0.5);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
                border: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: transparent;
            }
        """)
        
        self.pan_active = False
        self.last_pan_pos = QPoint()
        self.connecting_line = None
        self.start_connection_info = None
        self.selected_boxes_list = []
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        # Grid görünürlüğü (varsayılan kapalı)
        self.grid_visible = False

        # Arka plan resmi
        self.background_pixmap = None

        # Sanal seçim karesi (RubberBand)
        self.rubber_band_active = False
        self.rubber_band_origin = QPoint()
        self.rubber_band_rect_item = None

        # Sıralı bağlantı animasyonu için timer
        self.connection_animation_timer = QTimer()
        self.connection_animation_timer.setInterval(200)
        self.connection_animation_timer.timeout.connect(self._process_next_connection)
        self.connection_queue = []

    def set_grid_visible(self, visible):
        self.grid_visible = visible
        self.viewport().update()

    def set_background_pixmap(self, pixmap):
        self.background_pixmap = pixmap
        self.viewport().update()

    def reset_background(self):
        self.background_pixmap = None
        self.viewport().update()

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
            # Zaman damgası her zaman gösterilir
            box.name_input_area.show()
            box.independent_checkbox.show()
            box.editor_action_button.setText(editor_name)
            box.editor_action_button.show()
            box.select_editor_button.hide()

        if box_data:
            ts = box_data.get("timestamp_text", "")
            if ts:
                box.timestamp_text = ts
                box.name_input_area.setPlainText(ts)
            else:
                box.name_input_area.setPlainText(box_data.get("name_input", ""))
            box.independent_checkbox.setChecked(box_data.get("independent", False))

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
            self.pan_active = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if event.button() == Qt.RightButton:
            box = self.get_box_at(event.pos())
            if box:
                scene_pos = self.mapToScene(event.pos())
                port_name = self.get_port_at(box, scene_pos)
                if port_name:
                    self.start_connection(box, port_name)
                    event.accept()
                    return
            else:
                self.rubber_band_active = True
                self.rubber_band_origin = event.pos()
                self.rubber_band_rect_item = QGraphicsRectItem()
                self.rubber_band_rect_item.setPen(QPen(QColor(200, 200, 100), 1, Qt.DashLine))
                self.rubber_band_rect_item.setBrush(QBrush(QColor(200, 200, 100, 30)))
                self.rubber_band_rect_item.setZValue(100)
                self.scene().addItem(self.rubber_band_rect_item)
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
        if QApplication.keyboardModifiers() == Qt.ShiftModifier and not event.buttons():
            center_x = self.viewport().width() / 2
            delta_from_center = event.pos().x() - center_x
            neutral_zone_width = 50

            if abs(delta_from_center) < neutral_zone_width:
                event.accept()
                return

            if delta_from_center > 0:
                adjusted_delta = delta_from_center - neutral_zone_width
            else:
                adjusted_delta = delta_from_center + neutral_zone_width

            sensitivity = 0.0007
            zoom_factor = 1.0 - (adjusted_delta * sensitivity)
            zoom_factor = max(0.99, min(1.01, zoom_factor))

            original_anchor = self.transformationAnchor()
            self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
            self.scale(zoom_factor, zoom_factor)
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

        if self.rubber_band_active and self.rubber_band_rect_item:
            rect = QRectF(self.mapToScene(self.rubber_band_origin), self.mapToScene(event.pos()))
            self.rubber_band_rect_item.setRect(rect.normalized())
            event.accept()
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

        if self.rubber_band_active and self.rubber_band_rect_item and event.button() == Qt.RightButton:
            rect = self.rubber_band_rect_item.rect()
            items = self.scene().items(rect)
            self.selected_boxes_list.clear()
            for item in items:
                if isinstance(item, QGraphicsProxyWidget):
                    box = item.widget()
                    if isinstance(box, DraggableBox):
                        if box not in self.selected_boxes_list:
                            self.selected_boxes_list.append(box)
                            item.setSelected(True)
                            box.set_selected(True)
            self.update_selection_visuals()

            self.scene().removeItem(self.rubber_band_rect_item)
            self.rubber_band_rect_item = None
            self.rubber_band_active = False
            event.accept()
            return

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

    def animate_sequential_connections(self):
        if len(self.selected_boxes_list) < 2:
            return

        sorted_boxes = sorted(self.selected_boxes_list, key=lambda b: b.proxy_widget.x())
        self.connection_queue = []
        for i in range(len(sorted_boxes) - 1):
            box1, box2 = sorted_boxes[i], sorted_boxes[i+1]
            min_dist, best_ports = float('inf'), None
            for p1_name in box1.ports:
                for p2_name in box2.ports:
                    dist = QLineF(box1.get_port_scene_pos(p1_name), box2.get_port_scene_pos(p2_name)).length()
                    if dist < min_dist:
                        min_dist, best_ports = dist, (p1_name, p2_name)
            if best_ports:
                self.connection_queue.append((box1, best_ports[0], box2, best_ports[1]))

        if self.connection_queue:
            self.connection_animation_timer.start()

    def _process_next_connection(self):
        if not self.connection_queue:
            self.connection_animation_timer.stop()
            return

        start_box, start_port, end_box, end_port = self.connection_queue.pop(0)
        connection = ConnectionItem(start_box, start_port, end_box, end_port, color_type="special")
        command = AddConnectionCommand(self, connection)
        self.undo_stack.push(command)

        if not self.connection_queue:
            for box in self.selected_boxes_list:
                box.proxy_widget.setSelected(False)
                box.set_selected(False)
            self.selected_boxes_list.clear()
            self.update_selection_visuals()
            self.connection_animation_timer.stop()

    def update_selection_visuals(self):
        for box in self.boxes:
            box.set_selected(box in self.selected_boxes_list)

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            if event.key() == Qt.Key_D:
                event.accept()
                return
            elif event.key() in (Qt.Key_A, Qt.Key_F):
                event.accept()
                return

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

        elif event.key() == Qt.Key_A and not event.modifiers():
            self.selected_boxes_list.clear()
            for box in self.boxes:
                box.proxy_widget.setSelected(True)
                box.set_selected(True)
                self.selected_boxes_list.append(box)
            self.update_selection_visuals()
            event.accept()
            return

        elif event.key() == Qt.Key_F and not event.modifiers():
            if len(self.selected_boxes_list) == 2:
                self.connect_selected_boxes()
            elif len(self.selected_boxes_list) > 2:
                self.animate_sequential_connections()
            event.accept()
            return

        elif event.key() == Qt.Key_D and not event.modifiers():
            if self.selected_boxes_list:
                target_box = self.selected_boxes_list[-1]
                current_pos = target_box.proxy_widget.pos()

                new_pos = current_pos + QPointF(self.GRID_SPACING, self.GRID_SPACING)

                new_box = self.addDraggableBox(
                    pos=new_pos,
                    editor_name=target_box.selected_editor_name,
                    file_path=target_box.selected_file_path
                )

                note_text = target_box.name_input_area.toPlainText()
                if note_text:
                    new_box.name_input_area.setPlainText(note_text)

                if target_box.timestamp_text:
                    new_box.timestamp_text = target_box.timestamp_text
            event.accept()
            return

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

        connections_to_del = [item for item in items_to_delete if isinstance(item, ConnectionItem)]
        proxies_to_del = [item for item in items_to_delete if isinstance(item, QGraphicsProxyWidget)]

        for proxy in proxies_to_del:
            box = proxy.widget()
            if box:
                self.removeBox(box)
                connections_to_del = [c for c in connections_to_del if c.start_box != box and c.end_box != box]

        for conn in connections_to_del:
            command = RemoveConnectionCommand(self, conn)
            self.undo_stack.push(command)

        self.parent_window.update_connection_dropdown()

    def dragEnterEvent(self, event):
        """File Manager'dan gelen yerel dosya URL'lerini Sphere'e kabul eder."""
        if event.mimeData().hasUrls():
            local_files = [
                url.toLocalFile()
                for url in event.mimeData().urls()
                if url.isLocalFile()
            ]
            if any(os.path.isfile(path) for path in local_files):
                event.acceptProposedAction()
                return
        event.ignore()

    def dragMoveEvent(self, event):
        """Yerel dosya sürüklenirken Sphere yüzeyini bırakılabilir tutar."""
        if event.mimeData().hasUrls():
            local_files = [
                url.toLocalFile()
                for url in event.mimeData().urls()
                if url.isLocalFile()
            ]
            if any(os.path.isfile(path) for path in local_files):
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        """Dosya URL'sini uzantısına göre otomatik editör karesine dönüştürür."""
        paths = []
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = os.path.abspath(url.toLocalFile())
            if os.path.isfile(path):
                paths.append(path)

        if not paths:
            event.ignore()
            return

        drop_scene_pos = self.mapToScene(event.pos())
        created_count = 0
        unsupported = []

        for index, path in enumerate(paths):
            editor_name = self.parent_window.get_editor_name_for_file(path)
            if not editor_name:
                unsupported.append(os.path.basename(path))
                continue

            offset = QPointF(index * self.GRID_SPACING, index * self.GRID_SPACING)
            box = self.addDraggableBox(
                pos=drop_scene_pos + offset,
                editor_name=editor_name,
                file_path=path
            )
            if box:
                box.timestamp_text = box.generate_timestamp_string()
                box.name_input_area.setPlainText(box.timestamp_text)
                created_count += 1

        if unsupported:
            self.parent_window.show_warning_message(
                "Aşağıdaki dosyalar için desteklenen bir editör bulunamadı ve atlandı:\n\n"
                + "\n".join(unsupported)
            )

        if created_count:
            event.acceptProposedAction()
        else:
            event.ignore()

    def wheelEvent(self, event):
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(zoom_factor, zoom_factor)

    def drawBackground(self, painter, rect):
        # 1. Arka plan rengi (resim yoksa görünür)
        painter.fillRect(rect, QColor("#1e1e1e"))

        # 2. Arka plan resmi (sabit, tam ekran, zoom/pan'den etkilenmez)
        if self.background_pixmap is not None and not self.background_pixmap.isNull():
            painter.save()
            painter.setTransform(QTransform())
            painter.drawPixmap(painter.viewport(), self.background_pixmap)
            painter.restore()

        # 3. Grid (zoom'dan etkilenir)
        if self.grid_visible:
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

class PasswordDialog(QDialog):
    """
    .kitap export/import için tek parolalı giriş penceresi.

    Enter tuşu doğrudan Tamam ile aynı davranır.
    Önceki sürümlerde bulunan iki parçalı parola düzeniyle uyumluluk
    için get_password() parolayı 1_<parola>2_ biçiminde üretir.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Şifre Gerekli")
        self.setModal(True)
        self.setFixedSize(430, 190)
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; border: 2px solid #555; border-radius: 8px; }
            QLabel { color: #f0f0f0; font-size: 14px; }
            QLineEdit {
                background-color: #333; color: #eee;
                border: 1px solid #555; border-radius: 4px;
                padding: 6px; padding-right: 35px;
            }
            QPushButton {
                background-color: #3a3a3a; color: #ffffff;
                border: 1px solid #555; border-radius: 6px;
                padding: 6px 15px;
            }
            QPushButton:hover { background-color: #555555; }
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(20, 15, 20, 15)

        info = QLabel("Şifreyi bir kez girin ve Enter'a basın.")
        info.setWordWrap(True)
        self.layout.addWidget(info)

        self.password_label = QLabel("Şifre:")
        self.layout.addWidget(self.password_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setClearButtonEnabled(True)
        self.layout.addWidget(self.password_input)

        self.eye_open_icon = create_svg_icon(SVG_EYE_OPEN, size=20)
        self.eye_closed_icon = create_svg_icon(SVG_EYE_CLOSED, size=20)

        self.toggle_eye_action = QAction(self.password_input)
        self.toggle_eye_action.setIcon(self.eye_closed_icon)
        self.toggle_eye_action.triggered.connect(
            lambda: self.toggle_password_visibility(
                self.password_input, self.toggle_eye_action
            )
        )
        self.password_input.addAction(
            self.toggle_eye_action, QLineEdit.TrailingPosition
        )

        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()

        self.ok_button = QPushButton("Tamam")
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)

        self.cancel_button = QPushButton("İptal")
        self.cancel_button.clicked.connect(self.reject)

        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)

        # Enter artık ikinci alan açmaz; doğrudan dialog'u kabul eder.
        self.password_input.returnPressed.connect(self.accept)

        self.password_input.setFocus()
        QTimer.singleShot(0, self.password_input.setFocus)

    def toggle_password_visibility(self, field, action):
        if field.echoMode() == QLineEdit.Password:
            field.setEchoMode(QLineEdit.Normal)
            action.setIcon(self.eye_open_icon)
        else:
            field.setEchoMode(QLineEdit.Password)
            action.setIcon(self.eye_closed_icon)

    def get_password(self):
        """UI tarafından girilen gerçek parolayı tek değer olarak döndürür."""
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

SALT_SIZE = 16
ITERATIONS_LEGACY = 100000
ITERATIONS_GCM = 600000
KEY_SIZE = 32
CHUNK_SIZE = 1024 * 1024  # 1 MB'lık Bloklar (Akış için)

def derive_key(password, salt, iterations):
    password_bytes = password.encode('utf-8') if password else b''
    return PBKDF2(password_bytes, salt, dkLen=KEY_SIZE, count=iterations)

def encrypt_file_stream_gcm(input_path, output_path, password, progress_callback=None):
    """Dosyayı bellek harcamadan 1MB'lık bloklar halinde GCM modunda şifreleyip yazar."""
    if not CRYPTO_AVAILABLE:
        raise ImportError("PyCryptodome kütüphanesi bulunamadı.")

    salt = get_random_bytes(SALT_SIZE)
    key = derive_key(password, salt, ITERATIONS_GCM)
    nonce = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

    total_size = os.path.getsize(input_path) if os.path.exists(input_path) else 1
    processed_bytes = 0

    with open(input_path, "rb") as f_in, open(output_path, "wb") as f_out:
        # Başlık ve Parola Doğrulama Bilgilerini Yaz
        f_out.write(b"KITAP_V2 ")
        f_out.write(salt)
        f_out.write(nonce)

        # Tag alanı için yer ayır (GCM tag'ı en son hesaplanır)
        tag_position = f_out.tell()
        f_out.write(b'\x00' * 16)

        # 1 MB'lık bloklar halinde okuyup şifrele ve yaz
        while True:
            chunk = f_in.read(CHUNK_SIZE)
            if not chunk:
                break
            encrypted_chunk = cipher.encrypt(chunk)
            f_out.write(encrypted_chunk)
            processed_bytes += len(chunk)
            if progress_callback:
                progress_callback(processed_bytes, total_size)

        # Şifreleme bittiğinde doğrulama imzasını (Tag) başa yaz
        tag = cipher.digest()
        f_out.seek(tag_position)
        f_out.write(tag)

def decrypt_file_stream_gcm(input_path, output_path, password, progress_callback=None):
    """Şifreli dosyayı bellek harcamadan 1MB'lık bloklar halinde çözer ve doğrular."""
    if not CRYPTO_AVAILABLE:
        raise ImportError("PyCryptodome kütüphanesi bulunamadı.")

    file_size = os.path.getsize(input_path)
    if file_size < 9 + 16 + 16 + 16:
        raise ValueError("Güvenlik Hatası: Şifreli \nveri çok kısa veya bozuk!")

    with open(input_path, "rb") as f_in:
        header = f_in.read(9)
        if header != b"KITAP_V2 ":
            raise ValueError("Geçersiz dosya başlığı!")

        salt = f_in.read(16)
        nonce = f_in.read(16)
        tag = f_in.read(16)

        key = derive_key(password, salt, ITERATIONS_GCM)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

        ciphertext_size = file_size - (9 + 16 + 16 + 16)
        processed_bytes = 0

        with open(output_path, "wb") as f_out:
            while True:
                chunk = f_in.read(CHUNK_SIZE)
                if not chunk:
                    break
                decrypted_chunk = cipher.decrypt(chunk)
                f_out.write(decrypted_chunk)
                processed_bytes += len(chunk)
                if progress_callback:
                    progress_callback(processed_bytes, ciphertext_size)

        try:
            cipher.verify(tag)
        except ValueError:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise ValueError("Güvenlik Hatası: Şifre yanlış \nveya dosya bütünlüğü bozulmuş!")

def decrypt_file_stream_legacy(input_path, output_path, password, progress_callback=None):
    """Eski sürümler için güvenli, akış ve unpad hataları giderilmiş CBC şifre çözme."""
    if not CRYPTO_AVAILABLE:
        raise ImportError("PyCryptodome kütüphanesi bulunamadı.")

    file_size = os.path.getsize(input_path)
    with open(input_path, "rb") as f_in:
        header = f_in.read(9)
        salt = f_in.read(SALT_SIZE)
        iv = f_in.read(16)

        key = derive_key(password, salt, ITERATIONS_LEGACY)
        cipher = AES.new(key, AES.MODE_CBC, iv)

        ciphertext_size = file_size - (9 + SALT_SIZE + 16)
        processed_bytes = 0

        with open(output_path, "wb") as f_out:
            accumulator = bytearray()
            while True:
                chunk = f_in.read(CHUNK_SIZE)
                if not chunk:
                    break
                decrypted_chunk = cipher.decrypt(chunk)
                accumulator.extend(decrypted_chunk)
                processed_bytes += len(chunk)
                if progress_callback:
                    progress_callback(processed_bytes, ciphertext_size)

            try:
                # PKCS7 dolgusu yalnızca en sonda çözülür
                unpadded_data = unpad(bytes(accumulator), 16)
                f_out.write(unpadded_data)
            except Exception:
                if os.path.exists(output_path):
                    os.remove(output_path)
                raise ValueError("Güvenlik Hatası: Eski sürüm dosyasında \nşifre yanlış veya veri bozuk!")

def safe_tar_extract(tar, path="."):
    safe_members = []
    abs_path = os.path.abspath(path)
    for member in tar.getmembers():
        member_abs_path = os.path.abspath(os.path.join(abs_path, member.name))
        if not member_abs_path.startswith(abs_path):
            raise Exception("Güvenlik İhlali: Tar dosyası \ndış dizinlere erişmeye çalışıyor!")
        safe_members.append(member)
    tar.extractall(path, members=safe_members)

class SphereWindow(QWidget):
    DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')

    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        self.undo_stack = UndoStack()
        self._export_in_progress = False
        self._import_in_progress = False
        self.terminal_dialog = None
        self.custom_editors_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'veri', 'custom_editors')
        os.makedirs(self.custom_editors_dir, exist_ok=True)

        # Grid görünürlüğünü QSettings'ten oku
        self.settings = QSettings("Kavram", "Sphere")
        self.grid_visible = self.settings.value("grid_visible", False, type=bool)

        self.initUI()
        self.view.set_grid_visible(self.grid_visible)

        # Kayıtlı arka plan resmini yükle
        saved_bg_path = self.settings.value("background_image_path", "", type=str)
        if saved_bg_path and os.path.exists(saved_bg_path):
            pixmap = QPixmap(saved_bg_path)
            if not pixmap.isNull():
                self.view.set_background_pixmap(pixmap)

        self.add_initial_boxes()
        self.update_connection_dropdown()
        if not CRYPTO_AVAILABLE:
            self.show_error_message("PyCryptodome kütüphanesi bulunamadı. \nLütfen yükleyin: pip install pycryptodome")
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
        self.file_button.clicked.connect(lambda: self.open_file_manager())
        # Sağ tık için mevcut "Tüm Dosyalar" davranışı korunur, fakat aynı
        # File Manager penceresi kullanılır.
        self.file_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_button.customContextMenuRequested.connect(lambda pos: self.open_file_manager(all_files=True))
        self.toolbar_layout.addWidget(self.file_button)

        # Hızlı Kaydet Butonu (File butonunun hemen yanında)
        self.quick_save_button = QPushButton()
        self.quick_save_button.setIcon(create_svg_icon(SVG_SAVE_ICON, size=20))
        self.quick_save_button.setStyleSheet(self.buttonStyleMini())
        self.quick_save_button.setFixedSize(30, 30)
        self.quick_save_button.setToolTip("Hızlı Kaydet (Sahne Konumlarını ve Yapısını Kaydet)")
        self.quick_save_button.clicked.connect(self.quick_save_layout)
        self.toolbar_layout.addWidget(self.quick_save_button)

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
        self.toolbar_layout.addWidget(self.redo_button)
        self.redo_button.clicked.connect(self.undo_stack.redo)

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

        self.terminal_button = QPushButton("Terminal")
        self.terminal_button.setStyleSheet(self.buttonStyle())
        self.terminal_button.setFixedSize(110, 30)
        self.terminal_button.clicked.connect(self.openTerminal)
        self.toolbar_layout.addWidget(self.terminal_button)

        # Grid görünürlüğü butonu ("/")
        self.grid_toggle_button = QPushButton("/")
        self.grid_toggle_button.setStyleSheet(self.buttonStyleMini())
        self.grid_toggle_button.setFixedSize(35, 30)
        self.grid_toggle_button.setCheckable(False)
        self.grid_toggle_button.clicked.connect(self.toggle_grid_visibility)
        self.toolbar_layout.addWidget(self.grid_toggle_button)

        self.toolbar_layout.addStretch()

        self.export_button = QPushButton("Export")
        self.export_button.setStyleSheet(self.buttonStyle())
        self.export_button.setFixedSize(90, 30)
        # Sol tık: xz sıkıştırmalı export
        self.export_button.clicked.connect(lambda: self.export_data(compression="xz"))
        # Sağ tık: gz hızlı export
        self.export_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.export_button.customContextMenuRequested.connect(lambda pos: self.export_data(compression="gz"))
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

    def get_quick_layout_filepath(self):
        """Hızlı kaydetme için JSON dosyasının yolunu döndürür."""
        return os.path.join(self.custom_editors_dir, "quick_layout.json")

    def quick_save_layout(self):
        """Koordinat sistemindeki kutuların konumlarını ve bağlantılarını şifrelemeden hızlıca kaydeder."""
        try:
            boxes_data = []
            for box in self.view.boxes:
                proxy_pos = box.proxy_widget.pos() if box.proxy_widget else QPointF(0, 0)
                boxes_data.append({
                    "box_id": box.box_id,
                    "editor_name": box.selected_editor_name,
                    "file_path": box.selected_file_path,
                    "name_input": box.name_input_area.toPlainText(),
                    "timestamp_text": getattr(box, 'timestamp_text', ""),
                    "independent": box.independent_checkbox.isChecked(),
                    "pos_x": proxy_pos.x(),
                    "pos_y": proxy_pos.y()
                })

            connections_data = [{
                "start_box_id": c.start_box.box_id,
                "start_port": c.start_port,
                "end_box_id": c.end_box.box_id,
                "end_port": c.end_port,
                "color_type": c.color_type
            } for c in self.view.connections]

            layout_data = {
                "boxes": boxes_data,
                "connections": connections_data
            }

            file_path = self.get_quick_layout_filepath()
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(layout_data, f, indent=4, ensure_ascii=False)

            self.show_info_message("Sahne konumları ve dosya \nbağlantıları kaydedildi.")
        except Exception as e:
            self.show_error_message(f"Hızlı kaydetme sırasında hata oluştu: {e}")

    def load_quick_layout(self):
        """Daha önce kaydedilmiş hızlı sahne yapısını yükler."""
        file_path = self.get_quick_layout_filepath()
        if not os.path.exists(file_path):
            return False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)

            self._clear_all_boxes_and_connections()
            recreated_boxes = {}

            for box_data in loaded_data.get("boxes", []):
                file_path = box_data.get("file_path")
                if file_path and not os.path.exists(file_path):
                    print(f"Uyarı: Hızlı yüklemede '{file_path}' bulunamadı.")
                box = self.view.addDraggableBox(box_data=box_data)
                recreated_boxes[box_data["box_id"]] = box

            for conn_data in loaded_data.get("connections", []):
                start_box = recreated_boxes.get(conn_data["start_box_id"])
                end_box = recreated_boxes.get(conn_data["end_box_id"])
                if start_box and end_box:
                    conn = ConnectionItem(
                        start_box, conn_data["start_port"],
                        end_box, conn_data["end_port"],
                        conn_data.get("color_type", "default")
                    )
                    self.view.connections.append(conn)
                    self.view.scene().addItem(conn)
                    conn.update_path()

            self.update_connection_dropdown()
            return True
        except Exception as e:
            print(f"Hızlı düzen yüklenirken hata oluştu: {e}")
            return False

    def toggle_grid_visibility(self):
        self.grid_visible = not self.grid_visible
        self.settings.setValue("grid_visible", self.grid_visible)
        self.view.set_grid_visible(self.grid_visible)

    def openTerminal(self):
        if not self.terminal_dialog:
            self.terminal_dialog = TerminalDialog(self)
            self.terminal_dialog.commandEntered.connect(self.handleTerminalCommand)
        self.terminal_dialog.show()
        self.terminal_dialog.raise_()
        self.terminal_dialog.activateWindow()

    def reset_environment(self):
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout

        base_dir = os.path.dirname(os.path.abspath(__file__))
        folders_to_clean = [
            os.path.join(base_dir, "medya_cut"),
            os.path.join(base_dir, "_v&s_"),
            os.path.join(base_dir, "Export"),
            os.path.join(base_dir, "ai"),
            os.path.join(base_dir, "convert"),
            os.path.join(base_dir, "veri", "custom_editors")
        ]

        custom_editors = self.core_window_ref.custom_editors if self.core_window_ref else []
        custom_editor_names = [e['name'] for e in custom_editors]

        confirm_dialog = QDialog(self)
        confirm_dialog.setWindowTitle("Sıfırlama Onayı")
        confirm_dialog.setModal(True)
        confirm_dialog.setMinimumSize(500, 400)
        confirm_dialog.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: #f0f0f0; }
            QLabel, QTextEdit { color: #f0f0f0; background-color: #333; border: 1px solid #555; }
            QPushButton { background-color: #3a3a3a; color: white; border: 1px solid #555; border-radius: 5px; padding: 5px 15px; }
            QPushButton:hover { background-color: #555; }
        """)
        layout = QVBoxLayout(confirm_dialog)

        info_label = QLabel("Aşağıdaki klasörlerin içeriği KALICI OLARAK silinecek ve özel editörler kaldırılacaktır.\nBu işlem GERİ ALINAMAZ. Devam etmeden önce yedek alınız.\n\nSilinecek klasörler:")
        layout.addWidget(info_label)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        folder_list = "\n".join([f"• {f}" for f in folders_to_clean if os.path.exists(f)])
        text_edit.append(folder_list)
        text_edit.append("\nSilinecek özel editörler:")
        if custom_editor_names:
            text_edit.append("\n".join([f"• {name}" for name in custom_editor_names]))
        else:
            text_edit.append("(Hiçbir özel editör yok)")
        layout.addWidget(text_edit)

        button_layout = QHBoxLayout()
        yes_btn = QPushButton("Evet, temizle")
        no_btn = QPushButton("Hayır, iptal")
        button_layout.addWidget(yes_btn)
        button_layout.addWidget(no_btn)
        layout.addLayout(button_layout)

        def do_reset():
            # Klasör temizliği
            for folder in folders_to_clean:
                if os.path.exists(folder):
                    try:
                        for item in os.listdir(folder):
                            item_path = os.path.join(folder, item)
                            if os.path.isfile(item_path) or os.path.islink(item_path):
                                os.unlink(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                    except Exception as e:
                        print(f"Temizleme hatası {folder}: {e}")

            # Özel editör temizliği
            if self.core_window_ref:
                json_path = self.core_window_ref.get_custom_editors_json_path()
                if os.path.exists(json_path):
                    try:
                        os.remove(json_path)
                    except Exception as e:
                        print(f"custom_editors.json silinemedi: {e}")
                self.core_window_ref.custom_editors.clear()
                self.core_window_ref.save_custom_editors_json()
                for editor_name in custom_editor_names:
                    self.core_window_ref.cleanup_boxes_for_custom_editor(editor_name)
                for name in custom_editor_names:
                    if name in self.core_window_ref.editor_map:
                        del self.core_window_ref.editor_map[name]
                    if name in self.core_window_ref.editors_order:
                        self.core_window_ref.editors_order.remove(name)

            # Hızlı düzen kayıt dosyasını temizle
            quick_layout_path = self.get_quick_layout_filepath()
            if os.path.exists(quick_layout_path):
                try:
                    os.remove(quick_layout_path)
                except Exception as e:
                    print(f"quick_layout.json silinemedi: {e}")

            # Arka plan resmini sıfırla
            self.settings.remove("background_image_path")
            self.view.reset_background()

            self.update_connection_dropdown()
            confirm_dialog.accept()
            self.show_info_message("Sıfırlama işlemi başarıyla tamamlandı.\nTüm belirtilen klasörler temizlendi \nve özel editörler kaldırıldı.\nArka plan resmi varsayılana döndürüldü.")

        yes_btn.clicked.connect(do_reset)
        no_btn.clicked.connect(confirm_dialog.reject)

        confirm_dialog.exec_()

    # ---------- YARDIMCI FONKSİYON: Komut Normalizasyonu ----------
    def normalize_command(self, raw_input: str) -> str:
        """
        Terminal komutlarını Unicode (NFC) normalleştirir, fazla boşlukları temizler
        ve casefold ile büyük/küçük harf duyarsız hale getirir.
        Türkçe karakterler (ı, İ, ş, ç vb.) sorunsuz çalışır.
        """
        if not raw_input:
            return ""
        # NFC normalizasyonu (birleşik karakter formu)
        normalized = unicodedata.normalize('NFC', raw_input.strip())
        # casefold, lower()'dan daha kapsamlıdır (Türkçe I/i sorununu çözer)
        return normalized.casefold()

    def handleTerminalCommand(self, command):
        """
        Terminal komutlarını işler. Girdi normalleştirilir, büyük/küçük harf ve
        Türkçe karakter toleransı sağlanır.
        """
        raw_cmd = command
        cmd = self.normalize_command(raw_cmd)
        if not cmd:
            return

        print(f"Terminal Komutu Girildi: {raw_cmd} (normalleştirilmiş: {cmd})")

        # reset komutu
        if cmd == "reset":
            self.reset_environment()
            return

        # ap komutu (arka plan)
        if cmd == "ap":
            self.settings.remove("background_image_path")
            self.view.reset_background()
            self.show_info_message("Arka plan varsayılana döndürüldü.")
            return
        if cmd.startswith("ap "):
            image_path = raw_cmd[3:].strip()
            if os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    self.view.set_background_pixmap(pixmap)
                    self.settings.setValue("background_image_path", image_path)
                    self.show_info_message(f"Arka plan resmi ayarlandı: {os.path.basename(image_path)}")
                else:
                    self.show_error_message("Resim dosyası okunamadı (geçersiz format).")
            else:
                self.show_error_message("Dosya bulunamadı.")
            return

        # Türkçe karakterler ve semboller dahil olmak üzere komut satırını düzgünce parçala
        pattern = r'(?:"[^"]*"|\'[^\']*\'|\S+)'
        parts = [p.strip('"\'' ) for p in re.findall(pattern, raw_cmd)]

        if not parts:
            return

        command_head = parts[0].lower()

        # ---------- add_editor veya yazı/yazi (Türkçe destekli) ----------
        if command_head in ["add_editor", "yazi", "yazı"]:
            # Eğer komut "yazı" veya "yazi" ise ve ikinci parametre "k" ise, bu <editör_adı> k <uzantı> formatıdır
            if command_head in ["yazi", "yazı"] and len(parts) >= 2 and parts[1].casefold() == "k":
                # Format: yazı k <uzantı1> [uzantı2] [uzantı3]
                # editör_adı = parts[0] ("yazı")
                # uzantılar = parts[2:]
                editor_name = parts[0].strip()  # "yazı" veya "yazi"
                valid_extensions = []
                if len(parts) > 2:
                    raw_exts = parts[2:]
                    for ext in raw_exts:
                        cleaned = ext.replace(',', '').replace('_', '').strip()
                        if cleaned:
                            if not cleaned.startswith('.'):
                                cleaned = '.' + cleaned
                            if cleaned not in valid_extensions:
                                valid_extensions.append(cleaned)
                    valid_extensions = valid_extensions[:3]

                # Seçili kutu kontrolü
                if not self.view.selected_boxes_list:
                    self.show_error_message("Önce bir kutu seçin ve o kutuda 'Program' editörü ile bir executable dosyası seçili olmalı.")
                    return

                selected_box = self.view.selected_boxes_list[0]
                if selected_box.selected_editor_name != "Program":
                    self.show_error_message("Seçili kutunun editörü 'Program' olmalıdır.")
                    return

                if not selected_box.selected_file_path or not os.path.exists(selected_box.selected_file_path):
                    self.show_error_message("Seçili kutuda geçerli bir executable dosyası yok.")
                    return

                source_exec = selected_box.selected_file_path

                if self.core_window_ref and hasattr(self.core_window_ref, 'add_custom_editor'):
                    first_ext = valid_extensions[0] if valid_extensions else ""
                    success = self.core_window_ref.add_custom_editor(editor_name, source_exec, first_ext)
                    if success:
                        if len(valid_extensions) > 1:
                            for ed in self.core_window_ref.custom_editors:
                                if ed['name'] == editor_name:
                                    ed['extensions'] = valid_extensions
                                    break
                            if hasattr(self.core_window_ref, 'save_custom_editors_json'):
                                self.core_window_ref.save_custom_editors_json()
                        if valid_extensions:
                            ext_display = ", ".join(valid_extensions)
                            self.show_info_message(f"'{editor_name}' editörü başarıyla eklendi.\nUzantılar: {ext_display}")
                        else:
                            self.show_info_message(f"'{editor_name}' editörü **uzantısız** olarak eklendi.\n(Dosya ilişkisi yok, doğrudan program çalıştırılır.)")
                    else:
                        self.show_error_message("Editör eklenemedi.")
                else:
                    self.show_error_message("CoreWindow referansı bulunamadı.")
                return

            # Normal add_editor / yazı formatı: add_editor <editör_adı> <exe_yolu> [uzantı1] [uzantı2] [uzantı3]
            if len(parts) < 3:
                self.show_error_message(
                    "Kullanım: add_editor <İsim> <ExecutableYolu> [<Uzantı1> <Uzantı2> <Uzantı3>]\n"
                    "veya: yazı <İsim> <ExecutableYolu> [<Uzantı1> <Uzantı2> <Uzantı3>]\n"
                    "veya: yazı k <Uzantı1> [<Uzantı2> <Uzantı3>] (seçili kutudan executable alır)"
                )
                return

            editor_name = parts[1]
            exec_path = parts[2]

            valid_extensions = []
            if len(parts) > 3:
                raw_ext_args = parts[3:]
                raw_ext_string = " ".join(raw_ext_args)
                extracted_exts = re.findall(r'\.?[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+', raw_ext_string)
                for ext in extracted_exts:
                    cleaned_ext = ext.replace(',', '').replace('_', '').strip()
                    if cleaned_ext:
                        if not cleaned_ext.startswith('.'):
                            cleaned_ext = '.' + cleaned_ext
                        if cleaned_ext not in valid_extensions:
                            valid_extensions.append(cleaned_ext)
                valid_extensions = valid_extensions[:3]

            if not os.path.exists(exec_path):
                self.show_error_message(f"Executable dosyası bulunamadı: {exec_path}")
                return

            if not os.access(exec_path, os.X_OK):
                self.show_error_message(f"Dosya çalıştırılabilir değil: {exec_path}")
                return

            if self.core_window_ref and hasattr(self.core_window_ref, 'add_custom_editor'):
                first_ext = valid_extensions[0] if valid_extensions else ""
                success = self.core_window_ref.add_custom_editor(editor_name, exec_path, first_ext)
                if success:
                    if len(valid_extensions) > 1:
                        for ed in self.core_window_ref.custom_editors:
                            if ed['name'] == editor_name:
                                ed['extensions'] = valid_extensions
                                break
                        if hasattr(self.core_window_ref, 'save_custom_editors_json'):
                            self.core_window_ref.save_custom_editors_json()
                    if valid_extensions:
                        ext_display = ", ".join(valid_extensions)
                        self.show_info_message(f"'{editor_name}' editörü başarıyla eklendi.\nUzantılar: {ext_display}")
                    else:
                        self.show_info_message(f"'{editor_name}' editörü **uzantısız** olarak eklendi.\n(Dosya ilişkisi yok, doğrudan program çalıştırılır.)")
                else:
                    self.show_error_message("Editör eklenemedi.")
            else:
                self.show_error_message("CoreWindow referansı bulunamadı veya gerekli metod yok.")
            return

        # ---------- ESKİ KULLANIM: <editör_adı> k <uzantı> (UZANTI OPSİYONEL) ----------
        if len(parts) >= 2 and parts[1].casefold() == "k":
            editor_name = parts[0].strip()

            valid_extensions = []
            if len(parts) > 2:
                raw_exts = parts[2:]
                for ext in raw_exts:
                    cleaned = ext.replace(',', '').replace('_', '').strip()
                    if cleaned:
                        if not cleaned.startswith('.'):
                            cleaned = '.' + cleaned
                        if cleaned not in valid_extensions:
                            valid_extensions.append(cleaned)
                valid_extensions = valid_extensions[:3]

            if not self.view.selected_boxes_list:
                self.show_error_message("Önce bir kutu seçin ve o kutuda 'Program' editörü ile bir executable dosyası seçili olmalı.")
                return

            selected_box = self.view.selected_boxes_list[0]
            if selected_box.selected_editor_name != "Program":
                self.show_error_message("Seçili kutunun editörü 'Program' olmalıdır.")
                return

            if not selected_box.selected_file_path or not os.path.exists(selected_box.selected_file_path):
                self.show_error_message("Seçili kutuda geçerli bir executable dosyası yok.")
                return

            source_exec = selected_box.selected_file_path

            if self.core_window_ref and hasattr(self.core_window_ref, 'add_custom_editor'):
                first_ext = valid_extensions[0] if valid_extensions else ""
                success = self.core_window_ref.add_custom_editor(editor_name, source_exec, first_ext)
                if success:
                    if len(valid_extensions) > 1:
                        for ed in self.core_window_ref.custom_editors:
                            if ed['name'] == editor_name:
                                ed['extensions'] = valid_extensions
                                break
                        if hasattr(self.core_window_ref, 'save_custom_editors_json'):
                            self.core_window_ref.save_custom_editors_json()
                    if valid_extensions:
                        ext_display = ", ".join(valid_extensions)
                        self.show_info_message(f"'{editor_name}' editörü başarıyla eklendi.\nUzantılar: {ext_display}")
                    else:
                        self.show_info_message(f"'{editor_name}' editörü **uzantısız** olarak eklendi.\n(Dosya ilişkisi yok, doğrudan program çalıştırılır.)")
                else:
                    self.show_error_message("Editör eklenemedi.")
            else:
                self.show_error_message("CoreWindow referansı bulunamadı.")
            return

        # Geçersiz komut
        self.show_error_message(
            "Geçersiz komut. Kullanılabilir komutlar: \n"
            "reset, ap, ap <resim_yolu>, \n"
            "add_editor <isim> <exe_yolu> [<uzanti1> <uzanti2> <uzanti3>], \n"
            "yazı <isim> <exe_yolu> [<uzanti1> <uzanti2> <uzanti3>], \n"
            "yazı k [<uzantı1> <uzantı2> <uzantı3>], \n"
            "<editör_adı> k [<uzantı1> <uzantı2> <uzantı3>]"
        )

    def _handle_file_path(self, source_path):
        if not source_path or not os.path.exists(source_path):
            return None

        target_dir = self.DEFAULT_BASE_DIR
        os.makedirs(target_dir, exist_ok=True)
        file_name = os.path.basename(source_path)
        dest_path = os.path.join(target_dir, file_name)

        if os.path.normpath(source_path) == os.path.normpath(dest_path):
            return source_path

        base, ext = os.path.splitext(file_name)
        counter = 1
        while os.path.exists(dest_path):
            if os.path.getsize(source_path) == os.path.getsize(dest_path):
                return dest_path

            dest_path = os.path.join(target_dir, f"{base}_{counter}{ext}")
            counter += 1

        try:
            shutil.copy2(source_path, dest_path)
            self.show_info_message(f"'{os.path.basename(dest_path)}' dosyasının bir kopyası\n{target_dir} klasörüne oluşturuldu.")
            return dest_path
        except Exception as e:
            self.show_error_message(f"Dosya kopyalanamadı: {e}")
            return None

    def _add_file_to_tar_stream(self, tar, source_path, arcname,
                                processed_bytes=0, total_bytes=1,
                                progress_callback=None, progress_start=30,
                                progress_span=30):
        """
        tarfile.add() büyük dosyalarda uzun süre event loop'u bloke eder.
        Bunun yerine dosyayı blok blok tar'a yazar ve her blokta Qt arayüzünü
        günceller. Böylece export ilerleme çubuğu büyük dosyalarda da akar.
        """
        file_size = os.path.getsize(source_path)

        stat = os.stat(source_path)
        ti = tarfile.TarInfo(name=arcname)
        ti.size = file_size
        ti.mtime = stat.st_mtime
        ti.mode = stat.st_mode

        tar.addfile(ti)

        written = 0
        with open(source_path, "rb") as src_file:
            while written < file_size:
                chunk = src_file.read(CHUNK_SIZE)
                if not chunk:
                    break

                tar.fileobj.write(chunk)
                written += len(chunk)
                processed_bytes += len(chunk)

                if progress_callback:
                    ratio = processed_bytes / max(1, total_bytes)
                    value = progress_start + int(ratio * progress_span)
                    value = max(progress_start, min(progress_start + progress_span, value))
                    if not progress_callback(
                        value,
                        f"Arşive akıtılıyor: {os.path.basename(source_path)} "
                        f"(%{int(ratio * 100)})"
                    ):
                        return False, processed_bytes

                # Qt event loop'unun güncellenmesini garanti et.
                QApplication.processEvents()

        # POSIX tar kayıtlarını 512 byte hizasına tamamla.
        remainder = file_size % 512
        if remainder:
            tar.fileobj.write(b"\0" * (512 - remainder))

        return True, processed_bytes

    def _export_data_to_path(self, file_name, compression="xz", progress_callback=None):
        """
        File Manager tarafından seçilmiş tek hedef yola Sphere projesini export eder.

        Sorumluluk sınırı:
          - File Manager: dosya adı/yolu + OK
          - Sphere: parola, arşivleme, şifreleme ve sonuç
          - Core: yönlendirme ve pencere yaşam döngüsü
        """
        if self._export_in_progress:
            self.show_warning_message("Zaten devam eden bir dışa aktarma işlemi var.")
            return False

        if not CRYPTO_AVAILABLE:
            self.show_error_message("Dışa aktarma için \nPyCryptodome kütüphanesi gerekli.")
            return False

        if not file_name:
            return False
        if not file_name.lower().endswith(".kitap"):
            file_name += ".kitap"

        self._export_in_progress = True

        def report(value, text):
            if progress_callback is None:
                return True

            # File Manager'ın progress.update_progress() metodu başarı
            # durumunda None döndürebilir. None'ı False kabul etmek export'u
            # ilk ilerleme güncellemesinde iptal ettiriyordu.
            callback_result = progress_callback(value, text)
            return callback_result is not False

        password_dialog = PasswordDialog(self)
        if password_dialog.exec_() != QDialog.Accepted:
            return False
        password = password_dialog.get_password()

        progress_dialog = None if progress_callback is not None else OperationProgressDialog("Dışa Aktarılıyor", self)
        if progress_dialog is not None:
            progress_dialog.show()
            QApplication.processEvents()

        # Harici callback yoksa eski Sphere akışındaki tek ilerleme penceresini
        # doğrudan burada besle. Böylece çubuk 0'da kalmaz.
        if progress_callback is None and progress_dialog is not None:
            def report(value, text):
                progress_dialog.update_progress(value, text)
                # Bu ilerleme penceresinde iptal düğmesi yoktur;
                # dolayısıyla burada wasCanceled() çağrısı yapılmaz.
                return True

        tmp_tar_path = file_name + ".tar.tmp"
        tmp_output_path = file_name + ".part"
        try:
            if not report(10, "Veriler toplanıyor..."):
                return False
            boxes_data = []
            files_to_export = {}

            for box in self.view.boxes:
                file_path = box.selected_file_path
                file_basename = None

                if file_path and os.path.exists(file_path):
                    base_name = os.path.basename(file_path)
                    name, ext = os.path.splitext(base_name)

                    final_name = base_name
                    counter = 1

                    while final_name in files_to_export:
                        existing_path = files_to_export[final_name]
                        if existing_path == file_path or os.path.getsize(existing_path) == os.path.getsize(file_path):
                            break

                        final_name = f"{name}_{counter}{ext}"
                        counter += 1

                    files_to_export[final_name] = file_path
                    file_basename = final_name

                proxy_pos = box.proxy_widget.pos()
                boxes_data.append({
                    "box_id": box.box_id,
                    "editor_name": box.selected_editor_name,
                    "file_path": file_basename,
                    "name_input": box.name_input_area.toPlainText(),
                    "timestamp_text": getattr(box, 'timestamp_text', ""),
                    "independent": box.independent_checkbox.isChecked(),
                    "pos_x": proxy_pos.x(),
                    "pos_y": proxy_pos.y()
                })

            connections_data = [{"start_box_id": c.start_box.box_id, "start_port": c.start_port,
                                 "end_box_id": c.end_box.box_id, "end_port": c.end_port,
                                 "color_type": c.color_type} for c in self.view.connections]

            final_data = json.dumps({"boxes": boxes_data, "connections": connections_data}, indent=4).encode('utf-8')

            if not report(30, f"Arşiv doğrudan akış ile oluşturuluyor ({compression.upper()})..."):
                return False

            tar_mode = "w:gz" if compression == "gz" else "w:xz"

            # İlerleme artık dosya sayısına değil gerçek byte miktarına göre
            # hesaplanıyor. Büyük bir video/ses/dosya eklenirken çubuk akar.
            total_export_bytes = sum(
                os.path.getsize(path)
                for path in files_to_export.values()
                if os.path.exists(path)
            )
            processed_export_bytes = 0

            with tarfile.open(tmp_tar_path, tar_mode) as tar:
                ti = tarfile.TarInfo(name="data.json")
                ti.size = len(final_data)
                tar.addfile(ti, io.BytesIO(final_data))

                if not files_to_export:
                    report(55, "Arşiv hazırlanıyor...")

                for final_name, origin_path in files_to_export.items():
                    if not os.path.exists(origin_path):
                        continue

                    ok, processed_export_bytes = self._add_file_to_tar_stream(
                        tar,
                        origin_path,
                        final_name,
                        processed_bytes=processed_export_bytes,
                        total_bytes=max(1, total_export_bytes),
                        progress_callback=report,
                        progress_start=30,
                        progress_span=30
                    )
                    if not ok:
                        return False

            if not report(60, "Arşiv tamamlandı; veri şifrelemeye hazırlanıyor..."):
                return False

            if not report(60, "Şifreleme hazırlanıyor..."):
                return False

            def enc_progress(proc, total):
                ratio = proc / max(1, total)
                p_val = 60 + int(ratio * 35)
                return report(
                    p_val,
                    f"Şifreleniyor... (%{int(ratio * 100)})"
                )

            # Nihai dosya ancak şifreleme tamamen başarıyla bittikten sonra görünür olsun.
            encrypt_file_stream_gcm(
                tmp_tar_path,
                tmp_output_path,
                password,
                progress_callback=enc_progress
            )
            os.replace(tmp_output_path, file_name)

            if not report(100, "Tamamlandı!"):
                return False
            fmt_info = "Hızlı (gz)" if compression == "gz" else "Yüksek Sıkıştırma (xz)"
            if progress_callback is None:
                self.show_info_message(f"Proje {fmt_info} formatında başarıyla \n'{os.path.basename(file_name)}' olarak dışa aktarıldı.")

            return True

        except Exception as e:
            if progress_callback is None:
                self.show_error_message(f"Dışa aktarma sırasında hata: {e}")
            else:
                raise
        finally:
            if os.path.exists(tmp_tar_path):
                os.remove(tmp_tar_path)
            if os.path.exists(tmp_output_path):
                try:
                    os.remove(tmp_output_path)
                except OSError:
                    pass
            if progress_dialog is not None:
                progress_dialog.close()
            self._export_in_progress = False

    def export_data(self, compression="xz"):
        """
        Sphere Export yalnızca Kavram.py'ye istek gönderir.
        Sol tık xz, sağ tık gz davranışı korunur; kayıt arayüzü File Manager'dır.
        """
        if not self.core_window_ref:
            self.show_error_message("Kavram CoreWindow bağlantısı bulunamadı.")
            return None
        try:
            return self.core_window_ref.open_file_manager_for_export(
                self._export_data_to_path,
                compression=compression,
                default_export_name="Sphere"
            )
        except Exception as e:
            self.show_error_message(f"File Manager export isteği başarısız: {e}")
            return None

    def import_project_file(self, file_path):
        """Bellek şişmesi yaratmadan 1MB'lık bloklar halinde şifre çözüp içe aktaran yöntem."""
        if self._import_in_progress:
            self.show_warning_message("Zaten devam eden bir içe aktarma işlemi var.")
            return

        if not CRYPTO_AVAILABLE:
            self.show_error_message("İçe aktarma için \nPyCryptodome kütüphanesi gerekli.")
            return

        self._import_in_progress = True
        progress_dialog = None
        tmp_decrypted_tar = file_path + ".decrypted.tmp"
        try:
            with open(file_path, "rb") as f:
                header = f.read(9)
                if header not in (b"KAVRAM_V3", b"KITAP_V1 ", b"KITAP_V2 "):
                    self.show_error_message("Geçersiz veya desteklenmeyen .kitap veya .kavram dosyası formatı.")
                    return

            import_successful = False
            for attempt in range(3):
                password_dialog = PasswordDialog(self)
                if password_dialog.exec_() != QDialog.Accepted:
                    return
                password = password_dialog.get_password()

                progress_dialog = OperationProgressDialog("İçe Aktarılıyor", self)
                progress_dialog.show()

                decryption_error = None

                def dec_progress(proc, total):
                    p_val = int((proc / max(1, total)) * 70)
                    progress_dialog.update_progress(p_val, f"Şifre akış halinde çözülüyor... (%{int((proc / max(1, total)) * 100)})")

                try:
                    if header == b"KITAP_V2 ":
                        decrypt_file_stream_gcm(file_path, tmp_decrypted_tar, password, progress_callback=dec_progress)
                    else:
                        decrypt_file_stream_legacy(file_path, tmp_decrypted_tar, password, progress_callback=dec_progress)
                except ValueError as ve:
                    decryption_error = ve
                except Exception as e:
                    decryption_error = e

                if decryption_error is None:
                    try:
                        progress_dialog.update_progress(75, "Arşiv güvenli şekilde ayıklanıyor...")
                        with tarfile.open(tmp_decrypted_tar, mode="r:*") as tar:
                            safe_tar_extract(tar, path=self.DEFAULT_BASE_DIR)

                        json_path = os.path.join(self.DEFAULT_BASE_DIR, "data.json")
                        with open(json_path, "r", encoding='utf-8') as f:
                            loaded_data = json.load(f)
                        os.remove(json_path)

                        progress_dialog.update_progress(90, "Sahne yükleniyor...")
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
                        time.sleep(0.3)
                        import_successful = True
                        if progress_dialog:
                            progress_dialog.close()
                        break
                    except Exception as e:
                        if progress_dialog: progress_dialog.close()
                        self.show_error_message(f"Dosya başarıyla çözüldü ancak içeriği bozuk görünüyor: {e}")
                        return
                else:
                    if progress_dialog: progress_dialog.close()
                    print(f"İçe aktarma hatası (deneme {attempt + 1}): {decryption_error}")
                    self.show_warning_message(f"Şifre yanlış veya dosya bozuk/değiştirilmiş.\nKalan deneme hakkı: {2 - attempt}")

            if not import_successful and attempt == 2:
                 self.show_error_message("3 hatalı şifre denemesi. İçe aktarma iptal edildi.")

        except Exception as e:
            self.show_error_message(f"İçe aktarma sırasında beklenmedik bir hata oluştu: {e}")
            if progress_dialog is not None and progress_dialog.isVisible():
                 progress_dialog.close()
        finally:
            if os.path.exists(tmp_decrypted_tar):
                os.remove(tmp_decrypted_tar)
            self._import_in_progress = False

    def get_editor_name_for_file(self, path):
        """Sphere'in mevcut dosya->editör eşlemesini tek noktadan sağlar."""
        if not path:
            return None

        final_path = self._handle_file_path(path)
        if not final_path:
            return None

        file_extension = os.path.splitext(final_path)[1].lower()
        editor_map = {
            ".copya": "Copy",
            ".rec": "Rec",
            ".txr": "Text",
            ".png": "Drawing",
            ".pnf": "Drawing",
            ".jpg": "Drawing",
            ".jpeg": "Drawing",
            ".bmp": "Drawing",
            ".gif": "Drawing",
            ".ai": "Ai",
            ".sound": "Sound",
            ".wav": "Sound",
            ".aiff": "Sound",
            ".flac": "Sound",
            ".ogg": "Sound",
            ".mp3": "Sound",
            ".aac": "Sound",
            ".m4a": "Sound",
            ".media": "Media",
            ".mp4": "Media",
            ".avi": "Media",
            ".mov": "Media",
            ".mkv": "Media",
            ".webm": "Media",
            ".flv": "Media",
            ".blend": "Blender",
        }
        editor_name = editor_map.get(file_extension)

        if editor_name is None:
            program_extensions = ('.py', '.sh', '.bash', '.lua', '.pl', '.appimage', '.bin', '.out', '.run')
            if os.access(final_path, os.X_OK) or final_path.lower().endswith(program_extensions):
                editor_name = "Program"

        return editor_name

    def open_file_manager(self, all_files=False):
        """Sphere File butonu yalnızca Kavram.py'ye File Manager açma isteği gönderir."""
        if not self.core_window_ref:
            self.show_error_message("Kavram CoreWindow bağlantısı bulunamadı.")
            return None
        try:
            manager = self.core_window_ref.open_file_manager_for_editor("Sphere", all_files=all_files)
            if manager is None:
                return None
            try:
                manager.fileSelected.disconnect(self._receive_file_manager_file)
            except (TypeError, RuntimeError):
                pass
            manager.fileSelected.connect(self._receive_file_manager_file)
            return manager
        except Exception as e:
            self.show_error_message(f"File Manager isteği başarısız: {e}")
            return None

    def _receive_file_manager_file(self, file_path):
        """File Manager'ın seçtiği gerçek dosya yolunu doğrudan Sphere'e bağlar."""
        if not file_path or not os.path.isfile(file_path):
            return

        final_path = os.path.abspath(file_path)

        # .kitap/.kavram için dosyayı başka bir File Manager arayüzüne geri
        # göndermiyoruz ve yeniden kopyalamıyoruz; decrypt doğrudan seçilen
        # gerçek dosya üzerinden yapılır.
        if final_path.lower().endswith((".kitap", ".kavram")):
            self.import_project_file(final_path)
            return

        editor_name = self.get_editor_name_for_file(final_path)
        if not editor_name:
            self.show_warning_message(
                f"Bu dosya için Sphere içinde desteklenen bir editör bulunamadı:\n\n"
                f"{os.path.basename(final_path)}"
            )
            return

        box = self.view.addDraggableBox(
            editor_name=editor_name,
            file_path=final_path
        )
        box.timestamp_text = box.generate_timestamp_string()
        box.name_input_area.setPlainText(box.timestamp_text)

    def open_file_dialog_for_new_box(self, all_files=False):
        """File butonu için geriye dönük uyumluluk: seçim isteğini Kavram.py'ye yönlendirir."""
        return self.open_file_manager(all_files=all_files)

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
        if not self.load_quick_layout():
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
            QComboBox::down-arrow { image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZ3dCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTcgMTBMMTIgMTVMMTcgMTAiIHN0cm9rZT0iI2VlZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPj4=); width: 16px; height: 16px; }
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
    app.setWindowIcon(QIcon(resource_path("ikon/Kavram.png")))
    main_window = CoreWindow()
    main_window.show()
    sys.exit(app.exec_())
