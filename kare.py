# Kavram 1.0.0
# Copyright (C) 2025-0-1 Kavram or Contributors
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

# Core.py'dan EditorSwitcherDialog ve CoreWindow'u içe aktarıyoruz
# Eğer Core.py bulunamazsa veya EditorSwitcherDialog eksikse dummy bir sınıf oluştur
try:
    from Core import EditorSwitcherDialog, CoreWindow
except ImportError:
    class EditorSwitcherDialog(QDialog):
        def __init__(self, editor_names, parent=None):
            super().__init__(parent)
            self.editor_names = editor_names
            self.selected_name = None
            self.initUI()

        def initUI(self):
            layout = QVBoxLayout()
            self.list_widget = QListWidget()
            for name in self.editor_names:
                self.list_widget.addItem(name)
            layout.addWidget(self.list_widget)
            self.setLayout(layout)
            self.list_widget.itemClicked.connect(self.acceptSelection)

        def acceptSelection(self):
            items = self.list_widget.selectedItems()
            if items:
                self.selected_name = items[0].text()
            self.accept()

    class CoreWindow(QWidget): # Dummy CoreWindow
        def __init__(self):
            super().__init__()
            self.editor_map = {
                "Sphere": QWidget, "Text": QWidget, "Drawing": QWidget, "Sound": QWidget,
                "Ai": QWidget, "Media": QWidget, "Rec": QWidget, "Copy": QWidget,
                "Anime": QWidget, "Filter": QWidget, "Settings": QWidget  # Added "Filter" before "Settings"
            }
            self.editors_order = [
                "Sphere", "Text", "Drawing", "Sound", "Ai", "Media", "Rec", "Copy",
                "Anime", "Filter", "Settings"  # Added "Filter" before "Settings"
            ]
            print("Warning: Core.py or EditorSwitcherDialog not found. Some functionalities may be limited.")
            self.stack = QVBoxLayout(self) # Dummy stack
            self.dummy_widget = QWidget()
            self.stack.addWidget(self.dummy_widget)

        def switchToEditor(self, editor_name, close_current=False): # close_current parametresi eklendi
            print(f"Dummy CoreWindow: Request to switch to editor '{editor_name}'.")

        # Dummy loadEditorFile metodu eklendi
        def loadEditorFile(self, editor_name, file_path):
            """
            Dummy method to simulate loading a file into an editor.
            In a real CoreWindow, this would instantiate the specific editor
            and pass the file_path to it.
            """
            print(f"Dummy CoreWindow: Loading file '{file_path}' into editor '{editor_name}'.")
            # Here you would typically instantiate the actual editor and load the file
            # For example:
            # if editor_name == "Media":
            #     from media_editor import MediaEditor
            #     media_editor_instance = MediaEditor()
            #     media_editor_instance.load_file(file_path) # Assuming MediaEditor has a load_file method
            #     self.stack.addWidget(media_editor_instance)
            #     self.stack.setCurrentWidget(media_editor_instance)

        # Dummy ensureEditorInstantiated metodu
        def ensureEditorInstantiated(self, editor_name):
            print(f"Dummy CoreWindow: Ensuring editor '{editor_name}' is instantiated in background.")

# --- Yardımcı Fonksiyonlar ve Sabitler ---

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

SVG_CLOSE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 6L6 18M6 6L18 18" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_FILE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M13 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 21.7893 5.46957 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V9L13 2Z" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 2V9H20" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
# Tik işareti için güncellenmiş SVG (daha belirgin ve ortalanmış)
# stroke-width azaltıldı ve transform translate ayarlandı
SVG_TICK_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path transform="translate(0, 6)" d="M6 12L10 16L18 8" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

# --- Not Alanı için Özel QTextEdit ---
class PassthroughTextEdit(QTextEdit):
    """
    Orta ve sağ fare tıklamalarını yoksayarak üst widget'a (sürükleme için)
    iletilmesini sağlayan ve istenmeyen yapıştırma eylemlerini engelleyen
    özel bir QTextEdit sınıfı.
    """
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        # Eğer tıklama sol tuş değilse, olayı yoksayarak ebeveyn widget'ın
        # (DraggableProxyWidget) sürükleme gibi eylemleri işlemesine izin ver.
        if event.button() != Qt.LeftButton:
            event.ignore()
        else:
            # Sol tuş tıklaması ise normal QTextEdit davranışını uygula.
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent):
        # Normal bırakma olayını işle.
        super().mouseReleaseEvent(event)
        # Eğer bırakılan tuş orta tuş ise, olayı "kabul et".
        # Bu, X11/Linux sistemlerinde orta tuşla yapıştırma eylemini engeller.
        if event.button() == Qt.MiddleButton:
            event.accept()

# --- Özel Proxy Widget ---
class DraggableProxyWidget(QGraphicsProxyWidget):
    """Sadece sürükleme tutamacından sürüklemeye izin veren özel QGraphicsProxyWidget."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)

        self.mouse_press_scene_pos = QPointF() # Mouse position in scene coordinates when pressed
        self.item_pos_at_press = QPointF()     # Item position in scene coordinates when pressed
        self.undo_stack = None

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent): # Tip ipucunu ekledim
        """Sürükleme ve diğer fare olaylarını yönetir."""
        widget = self.widget()
        if not widget:
            super().mousePressEvent(event) # Fallback if no widget
            return

        # Orta veya Sağ tuş ile sürükleme için
        if event.button() == Qt.MiddleButton or event.button() == Qt.RightButton:
            # Sağ tuş tıklaması bir port üzerinde mi diye kontrol et
            if event.button() == Qt.RightButton:
                # Sahnenin view'ini al
                view = self.scene().views()[0] if self.scene().views() else None
                # Eğer view, port kontrolü yapabiliyorsa (SphereView gibi)
                if view and hasattr(view, 'get_port_at'):
                    port_name = view.get_port_at(widget, event.scenePos())
                    if port_name:
                        # Tıklama bir port üzerinde. Olayı yoksayarak SphereView'in
                        # bağlantı oluşturma mantığını tetiklemesine izin ver.
                        event.ignore()
                        return # Olayı daha fazla işleme

            # Tıklama port üzerinde değil veya orta tuş, sürüklemeyi başlat
            self.mouse_press_scene_pos = event.scenePos()
            self.item_pos_at_press = self.pos() # Item's current scene position
            self.setFlag(QGraphicsItem.ItemIsMovable, True) # Ensure it's movable
            event.accept() # Consume the event, do NOT call super().mousePressEvent(event)
            return

        # Sol tıklama ile sürükleme tutamacını (::) ve dosya açma işlevini yönet
        if event.button() == Qt.LeftButton:
            drag_handle = getattr(widget, 'drag_handle', None)
            # Check if the click is on the drag handle
            # "Rec" ve "Copy" editörleri de dahil edildi
            if drag_handle and drag_handle.geometry().contains(event.pos().toPoint()):
                if widget.selected_editor_name in ["Drawing", "Text", "Ai", "Sound", "Media", "Rec", "Copy"]:
                    widget.open_editor_file_dialog()
                    event.accept() # Accept as we handled the click
                    return
                else:
                    # For other editors, allow drag from handle
                    self.mouse_press_scene_pos = event.scenePos()
                    self.item_pos_at_press = self.pos()
                    self.setFlag(QGraphicsItem.ItemIsMovable, True)
                    super().mousePressEvent(event) # Let base class start drag
                    return
            else:
                # If click is not on drag handle, let the base class handle it.
                # This ensures child widgets like QCheckBox receive their events.
                # Do NOT call event.accept() here. Let the child widget accept it if it handles it.
                # If no child handles it, it will propagate up the scene.
                super().mousePressEvent(event)
                return

        # Fallback for other buttons or unhandled cases
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent): # Tip ipucunu ekledim
        # Sadece orta veya sağ tuş basılıysa veya sol tuşla sürükleme yapılıyorsa (QGraphicsView tarafından başlatılan)
        if event.buttons() & (Qt.MiddleButton | Qt.RightButton) or (event.buttons() & Qt.LeftButton and self.flags() & QGraphicsItem.ItemIsMovable and not self.mouse_press_scene_pos.isNull()):
            # Başlangıç pozisyonları ayarlanmamışsa, varsayılan davranışı kullan
            if self.mouse_press_scene_pos.isNull() or self.item_pos_at_press.isNull():
                super().mouseMoveEvent(event)
                return

            # Sahne koordinatlarında delta hesapla
            delta = event.scenePos() - self.mouse_press_scene_pos

            # Yeni ham pozisyonu hesapla
            raw_new_pos = self.item_pos_at_press + delta

            # Izgaraya hizalama
            if self.scene().views():
                # SphereView'den grid boyutunu al, eğer mevcutsa
                if hasattr(self.scene().views()[0], 'GRID_SPACING'):
                    grid_size = self.scene().views()[0].GRID_SPACING
                    snapped_x = round(raw_new_pos.x() / grid_size) * grid_size
                    snapped_y = round(raw_new_pos.y() / grid_size) * grid_size
                    snapped_pos = QPointF(snapped_x, snapped_y)
                else:
                    snapped_pos = raw_new_pos # Eğer grid boyutu yoksa hizalama yapma
            else:
                snapped_pos = raw_new_pos # Eğer view yoksa hizalama yapma

            self.setPos(snapped_pos)
            event.accept() # Olayı kabul et, daha fazla yayılmasını önle
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent): # Tip ipucunu ekledim
        # Orta, Sağ veya Sol tuş sürüklemesi bittiğinde MoveBoxCommand ekle
        is_drag_button_release = event.button() in [Qt.LeftButton, Qt.MiddleButton, Qt.RightButton]

        if is_drag_button_release and self.flags() & QGraphicsItem.ItemIsMovable:
            current_pos = self.pos()
            # Sadece öğe başlangıç pozisyonundan hareket ettiyse komutu push et
            if not self.item_pos_at_press.isNull() and self.item_pos_at_press != current_pos and self.undo_stack:
                try:
                    from sphere import MoveBoxCommand # sphere.py'den içe aktarmaya çalış
                except ImportError:
                    class MoveBoxCommand: # Geçici dummy sınıf
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
                    print("Warning: MoveBoxCommand not found in sphere.py. Using dummy MoveBoxCommand.")

                command = MoveBoxCommand(self.widget(), self.item_pos_at_press, current_pos)
                self.undo_stack.push(command)

            # Sürükleme ile ilgili durumu sıfırla
            self.item_pos_at_press = QPointF()
            self.mouse_press_scene_pos = QPointF()

        super().mouseReleaseEvent(event)

        # İstek 1: Orta tuş bırakıldığında olayı kabul ederek yapıştırma eylemini engelle.
        # Bu, super() çağrısından sonra yapılmalı ki Qt'nin kendi işlemleri tamamlansın,
        # ancak olay daha fazla yayılmasın.
        if event.button() == Qt.MiddleButton:
            event.accept()

# --- DraggableBox ---
class DraggableBox(QFrame):
    """Sahnede sürüklenip bağlanabilen kutu widget'ı."""
    # Yeni sinyal tanımla
    open_file_dialog_requested = pyqtSignal(str) # Seçilen editör adını gönderecek

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
            QTextEdit { /* QTextEdit stili */
                background-color: #333;
                color: #eee;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px 5px;
                font-size: 14px; /* Yazı boyutu büyütüldü */
            }
            QCheckBox { /* QCheckBox stili */
                color: #eee;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 0px; /* Kenarlık kaldırıldı */
                border-radius: 4px; /* Köşeleri yuvarladık */
                background-color: #333; /* Arka plan rengi */
            }
            QCheckBox::indicator:unchecked {
                image: none; /* Boş kare */
            }
            QCheckBox::indicator:checked {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZ3dCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMCw2KSIgZD0iTTYgMTJMTAgMTZMMTggOCIgc3Ryb2tlPSIjMjgyODI4IiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPj4=);
            }
        """
        self.selected_style = """
            QFrame {
                background-color: #282828;
                border: 2px solid #FFD700; /* Yellow color */
                border-radius: 8px;
            }
            QLabel {
                color: #ddd;
                font-size: 12px;
            }
            QTextEdit { /* QTextEdit stili - seçili olsa da sarı çerçeve yok */
                background-color: #333;
                color: #eee;
                border: 1px solid #555; /* Normal çerçeve */
                border-radius: 4px;
                padding: 2px 5px;
                font-size: 14px; /* Yazı boyutu büyütüldü */
            }
            QCheckBox { /* QCheckBox stili - seçili olsa da sarı çerçeve yok */
                color: #eee;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 0px; /* Kenarlık kaldırıldı */
                border-radius: 4px; /* Köşeleri yuvarladık */
                background-color: #333; /* Arka plan rengi */
            }
            QCheckBox::indicator:unchecked {
                image: none; /* Boş kare */
            }
            QCheckBox::indicator:checked {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZ3dCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMCw2KSIgZD0iTTYgMTJMTAgMTZMMTggOCIgc3Ryb2tlPSIjMjgyODI4IiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPj4=);
            }
        """
        # Yeni stil tanımları: drag_handle için normal ve basılı durumlar
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
                background-color: #444; /* Hover durumunda daha açık */
                border: 1px solid #666;
                border-radius: 4px;
                font-weight: bold;
                color: #eee;
            }
        """
        self.drag_handle_pressed_style = """
            QLabel {
                background-color: #666; /* Basıldığında daha koyu */
                border: 1px solid #777;
                border-radius: 4px;
                font-weight: bold;
                color: #eee;
            }
        """

        self.setStyleSheet(self.normal_style)

        self.setFixedSize(200, 200)

        self.selected_editor_name = None
        self.selected_file_path = None # Seçilen dosya yolunu saklamak için yeni değişken
        self.proxy_widget = None # This will hold the DraggableProxyWidget instance

        self.port_size = 16
        self.port_offset = 10
        self.ports = self.get_port_positions()

        self.initUI()

    def get_port_positions(self):
        """Returns port positions based on the current box size."""
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

        # drag_handle artık bir QLabel olarak kalıyor, tıklama proxy widget'ta yönetilecek
        self.drag_handle = QLabel("::")
        # drag_handle için tıklama efektini sağlamak üzere mousePressEvent ve mouseReleaseEvent'i etkinleştir
        self.drag_handle.setMouseTracking(True) # Mouse hareketlerini takip et
        self.drag_handle.installEventFilter(self) # Event filter'ı yükle
        self.drag_handle.setStyleSheet(self.drag_handle_normal_style) # Normal stili uygula

        self.drag_handle.setAlignment(Qt.AlignCenter)
        self.drag_handle.setFixedSize(30, 30)
        self.top_bar_layout.addWidget(self.drag_handle)

        self.top_bar_layout.addStretch()

        self.editor_action_button = QPushButton("")
        # Ensure parent_view has buttonStyle method or pass it directly
        if self.parent_view and hasattr(self.parent_view, 'buttonStyle'):
            self.editor_action_button.setStyleSheet(self.parent_view.buttonStyle())
        else:
            self.editor_action_button.setStyleSheet(self.defaultButtonStyle()) # Fallback
        self.editor_action_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.editor_action_button.setFixedHeight(30)
        self.editor_action_button.clicked.connect(self.switch_to_selected_editor)
        self.editor_action_button.hide()
        self.top_bar_layout.addWidget(self.editor_action_button, alignment=Qt.AlignCenter)
        self.top_bar_layout.addStretch()

        self.close_button = QPushButton()
        self.close_button.setIcon(create_svg_icon(SVG_CLOSE_ICON, size=16))
        # Ensure parent_view has buttonStyleMini method or pass it directly
        if self.parent_view and hasattr(self.parent_view, 'buttonStyleMini'):
            self.close_button.setStyleSheet(self.parent_view.buttonStyleMini())
        else:
            self.close_button.setStyleSheet(self.defaultButtonStyleMini()) # Fallback
        self.close_button.setFixedSize(30, 30)
        # Ensure parent_view has removeBox method
        if self.parent_view and hasattr(self.parent_view, 'removeBox'):
            self.close_button.clicked.connect(lambda: self.parent_view.removeBox(self))
        self.top_bar_layout.addWidget(self.close_button, alignment=Qt.AlignRight)

        self.main_layout.addLayout(self.top_bar_layout)
        # self.main_layout.addSpacerItem(QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)) # Bu spacer kaldırıldı

        self.select_editor_button = QPushButton("Select Editor")
        if self.parent_view and hasattr(self.parent_view, 'buttonStyle'):
            self.select_editor_button.setStyleSheet(self.parent_view.buttonStyle())
        else:
            self.select_editor_button.setStyleSheet(self.defaultButtonStyle()) # Fallback
        self.select_editor_button.setFixedSize(140, 30)
        self.select_editor_button.clicked.connect(self.selectEditor)
        self.main_layout.addWidget(self.select_editor_button, alignment=Qt.AlignCenter)

        # Dosya listesi widget'ı
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
        """)
        self.file_list_widget.hide() # Başlangıçta gizli
        self.file_list_widget.itemClicked.connect(self.on_file_list_item_clicked) # Sinyal bağlandı
        self.main_layout.addWidget(self.file_list_widget)

        # Not alanı artık özel PassthroughTextEdit sınıfını kullanıyor
        self.name_input_area = PassthroughTextEdit()
        # Sağ tık menüsünü de kesin olarak engelliyoruz
        self.name_input_area.setContextMenuPolicy(Qt.NoContextMenu)
        self.name_input_area.setFixedHeight(60) # 3 satır için yeterli yükseklik
        self.name_input_area.hide() # Başlangıçta gizli
        self.main_layout.addWidget(self.name_input_area)

        # Spacer between text area and checkbox
        self.main_layout.addSpacerItem(QSpacerItem(0, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)) # Bu spacer eklendi

        # Yeni eklenen bağımsız tik kutusu
        self.independent_checkbox = QCheckBox("") # Metni kaldırıldı
        self.independent_checkbox.setFixedSize(13, 13) # Boyutu ayarlandı
        self.independent_checkbox.setFocusPolicy(Qt.NoFocus) # Odak politikasını değiştirdik
        self.independent_checkbox.hide() # Başlangıçta gizli
        self.main_layout.addWidget(self.independent_checkbox, alignment=Qt.AlignCenter)

        # Sinyal bağlantısı eklendi
        self.independent_checkbox.toggled.connect(self.update_checkbox_style)
        # Başlangıç stilini ayarla
        self.update_checkbox_style(self.independent_checkbox.isChecked())

        self.main_layout.addStretch() # Bu stretch en sona eklendi

    def update_checkbox_style(self, checked):
        """
        QCheckBox'ın işaretli durumuna göre stilini günceller.
        """
        if checked:
            # İşaretliyse sarı arka plan
            self.independent_checkbox.setStyleSheet("""
                QCheckBox {
                    color: #eee;
                }
                QCheckBox::indicator {
                    width: 13px;
                    height: 13px;
                    border: 0px; /* Kenarlık kaldırıldı */
                    border-radius: 4px;
                    background-color: #FFD700; /* Sarı arka plan */
                    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZ3dCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMCw2KSIgZD0iTTYgMTJMTAgMTZMMTggOCIgc3Ryb2tlPSIjMjgyODI4IiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPj4=); /* Tik işareti rengini koyu yaptık ve stroke-width 2 yapıldı */
                }
            """)
        else:
            # İşaretsizse varsayılan arka plan
            self.independent_checkbox.setStyleSheet("""
                QCheckBox {
                    color: #eee;
                }
                QCheckBox::indicator {
                    width: 13px; /* Boyutu 13x13 olarak güncellendi */
                    height: 13px; /* Boyutu 13x13 olarak güncellendi */
                    border: 0px; /* Kenarlık kaldırıldı */
                    border-radius: 4px;
                    background-color: #333; /* Varsayılan arka plan */
                    image: none; /* Boş kare */
                }
            """)


    def eventFilter(self, obj, event):
        # drag_handle'a özel tıklama efektini yönet
        if obj == self.drag_handle:
            if event.type() == QEvent.MouseButtonPress:
                self.drag_handle.setStyleSheet(self.drag_handle_pressed_style)
            elif event.type() == QEvent.MouseButtonRelease:
                self.drag_handle.setStyleSheet(self.drag_handle_normal_style)
            elif event.type() == QEvent.Enter: # Hover efekti
                self.drag_handle.setStyleSheet(self.drag_handle_hover_style)
            elif event.type() == QEvent.Leave: # Hover bitiş efekti
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

        menu = QMenu(self)
        if self.parent_view and hasattr(self.parent_view, 'parent_window') and hasattr(self.parent_view.parent_window, 'menuStyle'):
            menu.setStyleSheet(self.parent_view.parent_window.menuStyle())
        else:
            menu.setStyleSheet(self.defaultMenuStyle()) # Fallback

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

        # Yeni eklenen kısım: Editörü arka planda hazırla
        # CoreWindow'da ensureEditorInstantiated metodu varsa çağır
        if self.core_window_ref and hasattr(self.core_window_ref, 'ensureEditorInstantiated'):
            self.core_window_ref.ensureEditorInstantiated(self.selected_editor_name)

        # Eğer seçilen editör "Drawing", "Text", "Ai", "Sound", "Media", "Rec" veya "Copy" ise dosya listesini göster
        if self.selected_editor_name in ["Drawing", "Text", "Ai", "Sound", "Media", "Rec", "Copy"]:
            self.file_list_widget.show()
            self.file_list_widget.clear() # Editör seçildiğinde listeyi temizle, otomatik doldurma yapma
            self.selected_file_path = None # Seçilen dosya yolunu sıfırla
            # Dosya seçildiğinde isim alanı ve tik kutusunu göster (Ai, Sound, Media, Rec ve Copy için de geçerli olacak şekilde)
            self.name_input_area.show()
            self.name_input_area.clear()
            self.independent_checkbox.show()
        else:
            self.file_list_widget.hide()
            self.file_list_widget.clear() # Başka editöre geçildiğinde listeyi temizle
            self.selected_file_path = None # Seçilen dosya yolunu sıfırla
            self.name_input_area.hide() # İsim alanını gizle
            self.name_input_area.clear() # Alanı temizle
            self.independent_checkbox.hide() # Tik kutusunu gizle


    def switch_to_selected_editor(self):
        if self.selected_editor_name and self.core_window_ref:
            print(f"DEBUG: switch_to_selected_editor called. selected_editor_name: {self.selected_editor_name}, selected_file_path: {self.selected_file_path}")
            # Eğer seçilen editör "Drawing", "Text", "Ai", "Sound", "Media", "Rec" veya "Copy" ise ve bir dosya seçilmişse, dosyayı yükle
            if self.selected_editor_name in ["Drawing", "Text", "Ai", "Sound", "Media", "Rec", "Copy"] and self.selected_file_path:
                if hasattr(self.core_window_ref, 'loadEditorFile'):
                    self.core_window_ref.loadEditorFile(self.selected_editor_name, self.selected_file_path)
                    # Dosya yüklendikten sonra selected_file_path'i sıfırlamıyoruz.
                    # Bu, aynı dosyanın tekrar açılmasına izin verir.
                else:
                    QMessageBox.warning(self, "Hata", "CoreWindow'da dosya yükleme işlevi bulunamadı.")
            else:
                self.core_window_ref.switchToEditor(self.selected_editor_name)
        else:
            QMessageBox.warning(self, "Error", "No editor selected or CoreWindow reference is invalid.")

    def open_editor_file_dialog(self):
        """
        Seçilen editör tipine göre dosya iletişim kutusunu açar.
        Drawing_editor.py ve TextEditor.py'deki gibi kapsamlı dosya yöneticisi.
        """
        default_dir = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export') # '' changed to ''
        QDir().mkpath(default_dir) # Dizin yoksa oluştur

        options = QFileDialog.Options()
        selected_file_path = None # Initialize to None

        if self.selected_editor_name == "Drawing":
            file_filter = "Desteklenen Dosyalar (*.drawing *.png *.jpg *.jpeg *.bmp *.gif);;Drawing Dosyaları (*.drawing);;Görsel Dosyaları (*.png *.jpg *.jpeg *.bmp *.gif);;Tüm Dosyalar (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "Drawing veya Görsel İçe Aktar",
                default_dir,
                file_filter,
                options=options
            )
        elif self.selected_editor_name == "Text":
            file_filter = "Text Dosyalar (*.ai *.pdf *.py *.txt *.cpp);;PDF Files (*.pdf);;Text Files (*.txt);;Python Files (*.py)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "Metin Dosyası Aç",
                default_dir,
                file_filter,
                options=options
            )
        elif self.selected_editor_name == "Ai": # Ai editörü için dosya filtresi eklendi
            file_filter = "AI Files (*.ai);;All Files (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "AI Dosyası Aç",
                default_dir,
                file_filter,
                options=options
            )
        elif self.selected_editor_name == "Sound": # Sound editörü için dosya filtresi eklendi
            file_filter = "Desteklenen Ses Dosyaları (*.saund *.wav *.aiff *.flac *.ogg *.mp3);;Concept Sound Files (*.saund);;WAV Audio File (*.wav);;AIFF Audio File (*.aiff);;FLAC Audio File (*.flac);;OGG Audio File (*.ogg);;MP3 Audio File (*.mp3);;Tüm Dosyalar (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "Ses Dosyası Aç",
                default_dir,
                file_filter,
                options=options
            )
        elif self.selected_editor_name == "Media": # Media editörü için dosya filtresi güncellendi
            # Sadece .media uzantısını destekleyecek şekilde güncellendi
            file_filter = "Medya Arşivleri (*.media);;Tüm Dosyalar (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "Medya Dosyası Aç",
                default_dir,
                file_filter,
                options=options
            )
        elif self.selected_editor_name == "Rec": # Rec editörü için dosya filtresi güncellendi
            # .rec, .mp4 ve .wav uzantılarını destekleyecek şekilde güncellendi
            file_filter = "Kayıt Dosyaları (*.rec *.mp4 *.wav *.mkv);;REC Dosyaları (*.rec);;MP4 Video Dosyaları (*.mp4);;WAV Ses Dosyaları (*.wav);;Tüm Dosyalar (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "Kayıt Dosyası Aç",
                default_dir,
                file_filter,
                options=options
            )
        elif self.selected_editor_name == "Copy": # Copy editörü için dosya filtresi eklendi
            file_filter = "Copya Files (*.copya);;All Files (*)"
            selected_file_path, _ = QFileDialog.getOpenFileName(
                self.core_window_ref,
                "Copya Dosyası Aç",
                default_dir,
                file_filter,
                options=options
            )
        else:
            QMessageBox.information(self, "Bilgi", f"'{self.selected_editor_name}' editörü için dosya açma işlevi henüz tanımlanmadı.")
            return

        if selected_file_path: # Only proceed if a file was actually selected
            self.file_list_widget.clear()
            file_name = os.path.basename(selected_file_path)

            item = QListWidgetItem(file_name) # Tam dosya adını göster
            item.setData(Qt.UserRole, selected_file_path)
            self.file_list_widget.addItem(item)
            self.file_list_widget.setCurrentItem(item)
            self.selected_file_path = selected_file_path # Set the instance variable

            # Dosya seçildiğinde isim alanını ve tik kutusunu göster (Ai, Sound, Media, Rec ve Copy editörü için de)
            self.name_input_area.show()
            self.name_input_area.clear() # Otomatik doldurmayı kaldırdık
            self.independent_checkbox.show()

            print(f"DEBUG: File selected in kare.py. Path: {self.selected_file_path}")
        else:
            # User cancelled the file dialog, clear any previously selected file path
            self.selected_file_path = None
            self.file_list_widget.clear() # Clear the list widget as well
            self.name_input_area.hide() # Hide fields if no file selected
            self.name_input_area.clear()
            self.independent_checkbox.hide()
            print("DEBUG: File selection cancelled in kare.py.")


    def on_file_list_item_clicked(self, item):
        """
        Dosya listesinden bir öğeye tıklandığında, seçilen dosya yolunu saklar.
        İsim alanını boş bırakır ve alanları gösterir.
        """
        self.selected_file_path = item.data(Qt.UserRole)
        # Tıklanan öğeyi seçili hale getir (görsel geri bildirim için)
        self.file_list_widget.setCurrentItem(item)

        # Dosya seçildiğinde isim alanını ve tik kutusunu göster (Ai, Sound, Media, Rec ve Copy editörü için de)
        self.name_input_area.show()
        self.name_input_area.clear() # Otomatik doldurmayı kaldırdık
        self.independent_checkbox.show()
        print(f"DEBUG: File list item clicked in kare.py. Path: {self.selected_file_path}")


    def get_port_scene_pos(self, port_name):
        if self.proxy_widget:
            port_pos = self.ports[port_name]
            return self.proxy_widget.mapToScene(port_pos)
        return QPointF()

    # Fallback stilleri (eğer parent_view'den alınamazsa)
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

    def defaultMenuStyle(self):
        return """
            QMenu {
                background-color: #282828;
                border: 1px solid #555;
                color: white;
            }
            QMenu::item:selected {
                background-color: #444;
            }
        """


