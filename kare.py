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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
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
import subprocess

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QMessageBox, QSizePolicy, QListWidget, QListWidgetItem, QDialog, QComboBox,
    QGraphicsView, QGraphicsScene, QGraphicsProxyWidget, QGraphicsPathItem, QGraphicsItem, QSpacerItem,
    QMenu, QLineEdit, QCheckBox, QGraphicsSceneMouseEvent, QTextEdit
)
from PyQt5.QtCore import Qt, QDir, QPoint, QPointF, QRectF, QByteArray, QSize, QLineF, QEvent, pyqtSignal
from PyQt5.QtGui import (
    QCursor, QPainter, QBrush, QPen, QColor, QPixmap, QIcon, QTransform, QPainterPath, QFont
)
from PyQt5.QtSvg import QSvgRenderer

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

SVG_CLOSE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 6L6 18M6 6L18 18" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_FILE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M13 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 21.7893 5.46957 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V9L13 2Z" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 2V9H20" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_TICK_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path transform="translate(0, 6)" d="M6 12L10 16L18 8" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

class PassthroughTextEdit(QTextEdit):
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        if event.button() != Qt.LeftButton:
            event.ignore()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MiddleButton:
            event.accept()

class DraggableProxyWidget(QGraphicsProxyWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)

        self.mouse_press_scene_pos = QPointF() 
        self.item_pos_at_press = QPointF()     
        self.undo_stack = None

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent): 
        widget = self.widget()
        if not widget:
            super().mousePressEvent(event) 
            return

        if event.button() == Qt.MiddleButton or event.button() == Qt.RightButton:
            if event.button() == Qt.RightButton:
                view = self.scene().views()[0] if self.scene().views() else None
                if view and hasattr(view, 'get_port_at'):
                    port_name = view.get_port_at(widget, event.scenePos())
                    if port_name:
                        event.ignore()
                        return 

            self.mouse_press_scene_pos = event.scenePos()
            self.item_pos_at_press = self.pos() 
            self.setFlag(QGraphicsItem.ItemIsMovable, True) 
            event.accept() 
            return

        if event.button() == Qt.LeftButton:
            drag_handle = getattr(widget, 'drag_handle', None)
            if drag_handle and drag_handle.geometry().contains(event.pos().toPoint()):
                if widget.selected_editor_name in ["Drawing", "Text", "Ai", "Sound", "Media", "Rec", "Copy", "Program"] or \
                   (hasattr(widget.core_window_ref, 'custom_editors') and any(e['name'] == widget.selected_editor_name for e in widget.core_window_ref.custom_editors)):
                    widget.open_editor_file_dialog()
                    event.accept() 
                    return
                else:
                    self.mouse_press_scene_pos = event.scenePos()
                    self.item_pos_at_press = self.pos()
                    self.setFlag(QGraphicsItem.ItemIsMovable, True)
                    super().mousePressEvent(event) 
                    return
            else:
                super().mousePressEvent(event)
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent): 
        if event.buttons() & (Qt.MiddleButton | Qt.RightButton) or (event.buttons() & Qt.LeftButton and self.flags() & QGraphicsItem.ItemIsMovable and not self.mouse_press_scene_pos.isNull()):
            if self.mouse_press_scene_pos.isNull() or self.item_pos_at_press.isNull():
                super().mouseMoveEvent(event)
                return

            delta = event.scenePos() - self.mouse_press_scene_pos
            raw_new_pos = self.item_pos_at_press + delta

            if self.scene().views():
                if hasattr(self.scene().views()[0], 'GRID_SPACING'):
                    grid_size = self.scene().views()[0].GRID_SPACING
                    snapped_x = round(raw_new_pos.x() / grid_size) * grid_size
                    snapped_y = round(raw_new_pos.y() / grid_size) * grid_size
                    snapped_pos = QPointF(snapped_x, snapped_y)
                else:
                    snapped_pos = raw_new_pos 
            else:
                snapped_pos = raw_new_pos 

            self.setPos(snapped_pos)
            event.accept() 
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent): 
        is_drag_button_release = event.button() in [Qt.LeftButton, Qt.MiddleButton, Qt.RightButton]

        if is_drag_button_release and self.flags() & QGraphicsItem.ItemIsMovable:
            current_pos = self.pos()
            if not self.item_pos_at_press.isNull() and self.item_pos_at_press != current_pos and self.undo_stack:
                try:
                    from sphere import MoveBoxCommand 
                except ImportError:
                    class MoveBoxCommand: 
                        def __init__(self, box, old_pos, new_pos):
                            self.box = box
                            self.old_pos = old_pos
                            self.new_pos = new_pos
                        def do(self):
                            if self.box.proxy_widget:
                                self.box.proxy_widget.setPos(self.new_pos)
                        def undo(self):
                            if self.box.proxy_widget:
                                self.box.proxy_widget.setPos(self.old_pos)

                command = MoveBoxCommand(self.widget(), self.item_pos_at_press, current_pos)
                self.undo_stack.push(command)

            self.item_pos_at_press = QPointF()
            self.mouse_press_scene_pos = QPointF()

        super().mouseReleaseEvent(event)

        if event.button() == Qt.MiddleButton:
            event.accept()

class DraggableBox(QFrame):
    open_file_dialog_requested = pyqtSignal(str) 

    def __init__(self, parent_view=None, core_window_ref=None, box_id=None):
        super().__init__()
        self.parent_view = parent_view
        self.core_window_ref = core_window_ref
        self.box_id = box_id if box_id is not None else random.randint(1000, 9999)

        self.setFrameShape(QFrame.Box)
        self.setFrameShadow(QFrame.Raised)
        self.setLineWidth(2)
        self.normal_style = """
            QFrame {
                background-color: #282828;
                border: 2px solid #444;
                border-radius: 8px;
            }
            QLabel {
                color: #ddd;
                font-size: 12px;
            }
            QTextEdit { 
                background-color: #333;
                color: #eee;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px 5px;
                font-size: 14px; 
            }
            QScrollBar:vertical {
                border: none;
                background: #282828;
                width: 8px;
                margin: 0px 0px 0px 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #444444;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #555555;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: #282828;
                height: 8px;
                margin: 0px 0px 0px 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #444444;
                min-width: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #555555;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: none;
                width: 0px;
            }
            QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            QCheckBox { 
                color: #eee;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 0px; 
                border-radius: 4px; 
                background-color: #333; 
            }
            QCheckBox::indicator:unchecked {
                image: none; 
            }
            QCheckBox::indicator:checked {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZ3dCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMCw2KSIgZD0iTTYgMTJMTCAxNkwxOCA4IiBzdHJva2U9IiMyODI4MjgiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPC9zdmc+);
            }
        """
        self.selected_style = """
            QFrame {
                background-color: #282828;
                border: 2px solid #FFD700; 
                border-radius: 8px;
            }
            QLabel {
                color: #ddd;
                font-size: 12px;
            }
            QTextEdit { 
                background-color: #333;
                color: #eee;
                border: 1px solid #555; 
                border-radius: 4px;
                padding: 2px 5px;
                font-size: 14px; 
            }
            QScrollBar:vertical {
                border: none;
                background: #282828;
                width: 8px;
                margin: 0px 0px 0px 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #444444;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #555555;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: #282828;
                height: 8px;
                margin: 0px 0px 0px 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #444444;
                min-width: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #555555;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: none;
                width: 0px;
            }
            QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            QCheckBox { 
                color: #eee;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 0px; 
                border-radius: 4px; 
                background-color: #333; 
            }
            QCheckBox::indicator:unchecked {
                image: none; 
            }
            QCheckBox::indicator:checked {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZ3dCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMCw2KSIgZD0iTTYgMTJMTCAxNkwxOCA4IiBzdHJva2U9IiMyODI4MjgiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPC9zdmc+);
            }
        """
        self.drag_handle_normal_style = """
            QLabel {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                font-weight: bold;
                color: #eee;
            }
        """
        self.drag_handle_hover_style = """
            QLabel {
                background-color: #444; 
                border: 1px solid #666;
                border-radius: 4px;
                font-weight: bold;
                color: #eee;
            }
        """
        self.drag_handle_pressed_style = """
            QLabel {
                background-color: #666; 
                border: 1px solid #777;
                border-radius: 4px;
                font-weight: bold;
                color: #eee;
            }
        """

        self.setStyleSheet(self.normal_style)

        self.setFixedSize(200, 200)

        self.selected_editor_name = None
        self.selected_file_path = None 
        self.proxy_widget = None 

        self.port_size = 16
        self.port_offset = 10
        self.ports = self.get_port_positions()

        self.initUI()

    def get_port_positions(self):
        rect = self.rect()
        w, h = rect.width(), rect.height()
        offset = self.port_offset
        return {
            "top": QPointF(w / 2, -offset),
            "bottom": QPointF(w / 2, h + offset),
            "left": QPointF(-offset, h / 2),
            "right": QPointF(w + offset, h / 2),
        }

    def initUI(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        self.main_layout.setSpacing(5)

        self.top_bar_layout = QHBoxLayout()
        self.top_bar_layout.setSpacing(5)

        self.drag_handle = QLabel("::")
        self.drag_handle.setMouseTracking(True) 
        self.drag_handle.installEventFilter(self) 
        self.drag_handle.setStyleSheet(self.drag_handle_normal_style) 

        self.drag_handle.setAlignment(Qt.AlignCenter)
        self.drag_handle.setFixedSize(30, 30)
        self.top_bar_layout.addWidget(self.drag_handle)

        self.top_bar_layout.addStretch()

        self.editor_action_button = QPushButton("")
        if self.parent_view and hasattr(self.parent_view, 'buttonStyle'):
            self.editor_action_button.setStyleSheet(self.parent_view.buttonStyle())
        else:
            self.editor_action_button.setStyleSheet(self.defaultButtonStyle()) 
        self.editor_action_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.editor_action_button.setFixedHeight(30)
        self.editor_action_button.clicked.connect(self.switch_to_selected_editor)
        self.editor_action_button.hide()
        self.top_bar_layout.addWidget(self.editor_action_button, alignment=Qt.AlignCenter)
        self.top_bar_layout.addStretch()

        self.close_button = QPushButton()
        self.close_button.setIcon(create_svg_icon(SVG_CLOSE_ICON, size=16))
        if self.parent_view and hasattr(self.parent_view, 'buttonStyleMini'):
            self.close_button.setStyleSheet(self.parent_view.buttonStyleMini())
        else:
            self.close_button.setStyleSheet(self.defaultButtonStyleMini()) 
        self.close_button.setFixedSize(30, 30)
        if self.parent_view and hasattr(self.parent_view, 'removeBox'):
            self.close_button.clicked.connect(lambda: self.parent_view.removeBox(self))
        self.top_bar_layout.addWidget(self.close_button, alignment=Qt.AlignRight)

        self.main_layout.addLayout(self.top_bar_layout)

        self.select_editor_button = QPushButton("Select Editor")
        if self.parent_view and hasattr(self.parent_view, 'buttonStyle'):
            self.select_editor_button.setStyleSheet(self.parent_view.buttonStyle())
        else:
            self.select_editor_button.setStyleSheet(self.defaultButtonStyle()) 
        self.select_editor_button.setFixedSize(140, 30)
        self.select_editor_button.clicked.connect(self.selectEditor)
        self.main_layout.addWidget(self.select_editor_button, alignment=Qt.AlignCenter)

        self.file_list_widget = QListWidget()
        self.file_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #333;
                color: #eee;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #444;
                color: #fff;
            }
            QScrollBar:vertical {
                border: none;
                background: #333333;
                width: 8px;
                margin: 0px 0px 0px 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #444444;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background: #555555;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: #333333;
                height: 8px;
                margin: 0px 0px 0px 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #444444;
                min-width: 20px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #555555;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: none;
                width: 0px;
            }
            QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
                background: none;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)
        self.file_list_widget.hide() 
        self.file_list_widget.itemClicked.connect(self.on_file_list_item_clicked) 
        self.main_layout.addWidget(self.file_list_widget)

        self.name_input_area = PassthroughTextEdit()
        self.name_input_area.setContextMenuPolicy(Qt.NoContextMenu)
        self.name_input_area.setFixedHeight(60) 
        self.name_input_area.hide() 
        self.main_layout.addWidget(self.name_input_area)

        self.main_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)) 

        self.independent_checkbox = QCheckBox("") 
        self.independent_checkbox.setFixedSize(13, 13) 
        self.independent_checkbox.setFocusPolicy(Qt.NoFocus) 
        self.independent_checkbox.hide() 
        self.main_layout.addWidget(self.independent_checkbox, alignment=Qt.AlignCenter)

        self.independent_checkbox.toggled.connect(self.update_checkbox_style)
        self.update_checkbox_style(self.independent_checkbox.isChecked())

        self.main_layout.addStretch() 

    def update_checkbox_style(self, checked):
        if checked:
            self.independent_checkbox.setStyleSheet("""
                QCheckBox {
                    color: #eee;
                }
                QCheckBox::indicator {
                    width: 13px;
                    height: 13px;
                    border: 0px; 
                    border-radius: 4px;
                    background-color: #FFD700; 
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZ3dCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMCw2KSIgZD0iTTYgMTJMTCAxNkwxOCA4IiBzdHJva2U9IiMyODI4MjgiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWNhcD0icm91bmQiLz4KPC9zdmc+); 
                }
            """)
        else:
            self.independent_checkbox.setStyleSheet("""
                QCheckBox {
                    color: #eee;
                }
                QCheckBox::indicator {
                    width: 13px; 
                    height: 13px; 
                    border: 0px; 
                    border-radius: 4px;
                    background-color: #333; 
                    image: none; 
                }
            """)

    def eventFilter(self, obj, event):
        if obj == self.drag_handle:
            if event.type() == QEvent.MouseButtonPress:
                self.drag_handle.setStyleSheet(self.drag_handle_pressed_style)
            elif event.type() == QEvent.MouseButtonRelease:
                self.drag_handle.setStyleSheet(self.drag_handle_normal_style)
            elif event.type() == QEvent.Enter: 
                self.drag_handle.setStyleSheet(self.drag_handle_hover_style)
            elif event.type() == QEvent.Leave: 
                self.drag_handle.setStyleSheet(self.drag_handle_normal_style)
        return super().eventFilter(obj, event)

    def set_selected(self, selected):
        if selected:
            self.setStyleSheet(self.selected_style)
        else:
            self.setStyleSheet(self.normal_style)

    def selectEditor(self):
        if not self.core_window_ref:
            QMessageBox.warning(self, "Error", "CoreWindow reference not found.")
            return

        filtered_editor_names = [name for name in self.core_window_ref.editors_order if name != "Sphere"]
        if "Program" not in filtered_editor_names:
            try:
                settings_idx = filtered_editor_names.index("Settings")
            except ValueError:
                settings_idx = len(filtered_editor_names)
            filtered_editor_names.insert(settings_idx, "Program")

        menu = QMenu(self)
        if self.parent_view and hasattr(self.parent_view, 'parent_window') and hasattr(self.parent_view.parent_window, 'menuStyle'):
            menu.setStyleSheet(self.parent_view.parent_window.menuStyle())
        else:
            menu.setStyleSheet(self.defaultMenuStyle()) 

        for name in filtered_editor_names:
            action = menu.addAction(name)
            action.triggered.connect(lambda checked, n=name: self._on_editor_selected(n))

        button_pos = self.select_editor_button.mapToGlobal(QPoint(0, self.select_editor_button.height()))
        menu.exec_(button_pos)

    def _on_editor_selected(self, name):
        self.selected_editor_name = name
        self.select_editor_button.hide()
        self.editor_action_button.setText(self.selected_editor_name)
        self.editor_action_button.show()

        if self.core_window_ref and hasattr(self.core_window_ref, 'ensureEditorInstantiated'):
            self.core_window_ref.ensureEditorInstantiated(self.selected_editor_name)

        is_custom = False
        if hasattr(self.core_window_ref, 'custom_editors'):
            is_custom = any(e['name'] == name for e in self.core_window_ref.custom_editors)

        if is_custom:
            exec_path = self.core_window_ref.get_custom_editor_executable(name)
            if exec_path and os.path.exists(exec_path):
                self.selected_file_path = exec_path
                self.file_list_widget.hide()
                self.name_input_area.hide()
                self.independent_checkbox.hide()
            else:
                self.selected_file_path = None
                QMessageBox.warning(self, "Uyarı", f"'{name}' editörünün executable'ı bulunamadı.")
            return

        if self.selected_editor_name in ["Drawing", "Text", "Ai", "Sound", "Media", "Rec", "Copy", "Program"]:
            self.file_list_widget.show()
            self.file_list_widget.clear() 
            self.selected_file_path = None 
            self.name_input_area.show()
            self.name_input_area.clear()
            self.independent_checkbox.show()
        else:
            self.file_list_widget.hide()
            self.file_list_widget.clear() 
            self.selected_file_path = None 
            self.name_input_area.hide() 
            self.name_input_area.clear() 
            self.independent_checkbox.hide() 

    def switch_to_selected_editor(self):
        if self.selected_editor_name and self.core_window_ref:
            print(f"DEBUG: switch_to_selected_editor called. selected_editor_name: {self.selected_editor_name}, selected_file_path: {self.selected_file_path}")
            if self.selected_editor_name in ["Drawing", "Text", "Ai", "Sound", "Media", "Rec", "Copy"] and self.selected_file_path:
                if hasattr(self.core_window_ref, 'loadEditorFile'):
                    self.core_window_ref.loadEditorFile(self.selected_editor_name, self.selected_file_path)
                else:
                    QMessageBox.warning(self, "Hata", "CoreWindow'da dosya yükleme işlevi bulunamadı.")
            elif self.selected_editor_name == "Program" and self.selected_file_path:
                if not os.access(self.selected_file_path, os.X_OK):
                    QMessageBox.warning(self, "Hata", "Seçilen dosya çalıştırılabilir (executable) iznine sahip değil.")
                    return
                try:
                    # Geliştirilmiş başlatma: çalışma dizini ve LD_LIBRARY_PATH ayarı
                    exe = self.selected_file_path
                    cwd = os.path.dirname(exe)
                    env = os.environ.copy()
                    lib_dir = os.path.join(cwd, 'lib')
                    if os.path.exists(lib_dir):
                        env['LD_LIBRARY_PATH'] = lib_dir + os.pathsep + env.get('LD_LIBRARY_PATH', '')
                    # Bazı uygulamalar için ek argümanlar (ör. Blender --factory-startup) isteğe bağlı
                    args = [exe]
                    # Eğer Blender ise ve istenirse --factory-startup eklenebilir, ama şimdilik sadece exe
                    process = subprocess.Popen(args, start_new_session=True, cwd=cwd, env=env)
                    if self.core_window_ref and hasattr(self.core_window_ref, 'spawned_external_processes'):
                        self.core_window_ref.spawned_external_processes.append(process)
                except Exception as e:
                    QMessageBox.warning(self, "Hata", f"Program başlatılamadı: {e}")
            elif hasattr(self.core_window_ref, 'custom_editors') and any(e['name'] == self.selected_editor_name for e in self.core_window_ref.custom_editors) and self.selected_file_path:
                if not os.access(self.selected_file_path, os.X_OK):
                    QMessageBox.warning(self, "Hata", "Seçilen özel editör çalıştırılabilir iznine sahip değil.")
                    return
                try:
                    exe = self.selected_file_path
                    cwd = os.path.dirname(exe)
                    env = os.environ.copy()
                    lib_dir = os.path.join(cwd, 'lib')
                    if os.path.exists(lib_dir):
                        env['LD_LIBRARY_PATH'] = lib_dir + os.pathsep + env.get('LD_LIBRARY_PATH', '')
                    args = [exe]
                    process = subprocess.Popen(args, start_new_session=True, cwd=cwd, env=env)
                    if self.core_window_ref and hasattr(self.core_window_ref, 'spawned_external_processes'):
                        self.core_window_ref.spawned_external_processes.append(process)
                except Exception as e:
                    QMessageBox.warning(self, "Hata", f"Program başlatılamadı: {e}")
            else:
                self.core_window_ref.switchToEditor(self.selected_editor_name)
        else:
            QMessageBox.warning(self, "Error", "No editor selected or CoreWindow reference is invalid.")

    def open_editor_file_dialog(self):
        if hasattr(self.core_window_ref, 'custom_editors') and any(e['name'] == self.selected_editor_name for e in self.core_window_ref.custom_editors):
            # Bilgi mesaj kutusu kaldırıldı. Kullanıcı tıkladığında hiçbir şey olmadan sessizce dönüyor.
            return

        default_dir = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')
        QDir().mkpath(default_dir) 

        options = QFileDialog.Options()
        selected_file_path = None 

        if self.selected_editor_name == "Drawing":
            file_filter = "Desteklenen Dosyalar (*.drawing *.png *.pnf *.jpg *.jpeg *.bmp *.gif);;Drawing Dosyaları (*.drawing);;Görsel Dosyaları (*.png *.pnf *.jpg *.jpeg *.bmp *.gif);;Tüm Dosyalar (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "Drawing veya Görsel İçe Aktar",
                default_dir,
                file_filter,
                options=options
            )
        elif self.selected_editor_name == "Text":
            file_filter = "Kavram Text Arşivi (*.txr);;Tüm Dosyalar (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "Metin Arşivi Aç",
                default_dir,
                file_filter,
                options=options
            )
        elif self.selected_editor_name == "Ai": 
            file_filter = "AI Files (*.ai);;All Files (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "AI Dosyası Aç",
                default_dir,
                file_filter,
                options=options
            )
        elif self.selected_editor_name == "Sound": 
            file_filter = "Desteklenen Ses Dosyaları (*.sound *.wav *.aiff *.flac *.ogg *.mp3);;Concept Sound Files (*.sound);;WAV Audio File (*.wav);;AIFF Audio File (*.aiff);;FLAC Audio File (*.flac);;OGG Audio File (*.ogg);;MP3 Audio File (*.mp3);;Tüm Dosyalar (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "Ses Dosyası Aç",
                default_dir,
                file_filter,
                options=options
            )
        elif self.selected_editor_name == "Media": 
            file_filter = "Medya Arşivleri (*.media);;Tüm Dosyalar (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "Medya Dosyası Aç",
                default_dir,
                file_filter,
                options=options
            )
        elif self.selected_editor_name == "Rec": 
            file_filter = "Kayıt Dosyaları (*.rec *.mp4 *.wav *.mkv);;REC Dosyaları (*.rec);;MP4 Video Dosyaları (*.mp4);;WAV Ses Dosyaları (*.wav);;Tüm Dosyalar (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "Kayıt Dosyası Aç",
                default_dir,
                file_filter,
                options=options
            )
        elif self.selected_editor_name == "Copy": 
            file_filter = "Copya Files (*.copya);;All Files (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "Copya Dosyası Aç",
                default_dir,
                file_filter,
                options=options
            )
        elif self.selected_editor_name == "Program":
            file_filter = "Executable Files (*);;All Files (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "Program Seç",
                default_dir,
                file_filter,
                options=options
            )
        else:
            QMessageBox.information(self, "Bilgi", f"'{self.selected_editor_name}' editörü için dosya açma işlevi henüz tanımlanmadı.")
            return

        if selected_file_path: 
            self.file_list_widget.clear()
            file_name = os.path.basename(selected_file_path)

            item = QListWidgetItem(file_name) 
            item.setData(Qt.UserRole, selected_file_path)
            self.file_list_widget.addItem(item)
            self.file_list_widget.setCurrentItem(item)
            self.selected_file_path = selected_file_path 

            self.name_input_area.show()
            self.name_input_area.clear() 
            self.independent_checkbox.show()

            print(f"DEBUG: File selected in kare.py. Path: {self.selected_file_path}")
        else:
            self.selected_file_path = None
            self.file_list_widget.clear() 
            self.name_input_area.hide() 
            self.name_input_area.clear()
            self.independent_checkbox.hide()
            print("DEBUG: File selection cancelled in kare.py.")

    def on_file_list_item_clicked(self, item):
        self.selected_file_path = item.data(Qt.UserRole)
        self.file_list_widget.setCurrentItem(item)

        self.name_input_area.show()
        self.name_input_area.clear() 
        self.independent_checkbox.show()
        print(f"DEBUG: File list item clicked in kare.py. Path: {self.selected_file_path}")

    def get_port_scene_pos(self, port_name):
        if self.proxy_widget:
            port_pos = self.ports[port_name]
            return self.proxy_widget.mapToScene(port_pos)
        return QPointF()

    def defaultButtonStyle(self):
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

    def defaultButtonStyleMini(self):
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 16px;
                border: 2px solid #555; border-radius: 8px; padding: 5px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """
