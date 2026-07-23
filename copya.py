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
import json
import os
import base64
import uuid
import shutil
import zipfile
import re

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFileDialog, QToolButton, QScrollArea, QSizePolicy,
    QLineEdit, QTextEdit, QFrame, QMessageBox, QPushButton, QStackedWidget,
    QLabel,  QGraphicsOpacityEffect, QDialog, QMenu, QAction, QProgressDialog,
    QShortcut
)
from PyQt5.QtGui import (
    QFont, QColor, QTextCursor, QIcon, QPainter, QPixmap, QImage, 
    QTransform, QBrush, QTextFormat, QCursor, QKeySequence, QFontMetrics,
    QRegion, QBitmap
)
from PyQt5.QtCore import (
    Qt, QTimer, QEvent, QByteArray, QBuffer, QIODevice, 
    QRectF, QPoint, QSize, QUrl, QMimeData, QRect, QDir,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QAbstractAnimation
)
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QTextDocument

# PDF desteği için PyMuPDF (fitz)
try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    fitz = None

try:
    from Core import CoreWindow
except ImportError:
    class CoreWindow(QWidget):
        def showSwitcher(self): print("Switcher placeholder")

# --- İKONLAR VE YARDIMCI FONKSİYONLAR ---

def create_svg_icon(svg_content, size=20, color="#ffffff"):
    modified_svg_content = svg_content.replace('stroke="#aaa"', f'stroke="{color}"').replace('fill="#aaa"', f'fill="{color}"')
    renderer = QSvgRenderer(QByteArray(modified_svg_content.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

def trim_pixmap_by_alpha(pixmap, margin=0):
    if pixmap.isNull():
        return pixmap
    mask = pixmap.mask()
    if mask.isNull(): 
        return pixmap
    region = QRegion(QBitmap(mask))
    rect = region.boundingRect()
    if rect.isEmpty():
        return pixmap 
    rect.adjust(-margin, -margin, margin, margin)
    rect = rect.intersected(pixmap.rect())
    return pixmap.copy(rect)

SVG_SAVE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V7L17 3ZM12 17C10.34 17 9 15.66 9 14C9 12.34 10.34 11 12 11C13.66 11 15 12.34 15 14C15 15.66 13.66 17 12 17Z" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

class AutoResizingTextEdit(QTextEdit):
    def __init__(self, text, item_ref=None, parent=None):
        super().__init__(parent)
        self.item_ref = item_ref
        self.setReadOnly(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        self.setStyleSheet("""
            QTextEdit { background: #111; color: #ddd; border: 1px solid #444; padding: 10px; border-radius: 4px; }
        """)
        
        # Eğer içerik .txr formatına aitse HTML şeklinde akıllı yükleme yap
        if text.strip().startswith("<center>") or "<center>" in text:
            self.set_clean_html_content(text)
        else:
            self.setPlainText(text)
            
        self.adjust_height()
        self.textChanged.connect(self.on_text_changed)

    def set_clean_html_content(self, html_text):
        self.blockSignals(True)
        self.clear()
        cursor = self.textCursor()
        lines = html_text.split('\n')
        for i, line in enumerate(lines):
            is_centered = False
            text = line
            center_match = re.match(r'^\s*<center>(.*)</center>\s*$', line, re.IGNORECASE)
            if center_match:
                is_centered = True
                text = center_match.group(1)
            if i > 0:
                cursor.insertBlock()
            cursor.insertText(text)
            block_fmt = cursor.blockFormat()
            if is_centered:
                block_fmt.setAlignment(Qt.AlignCenter)
            else:
                block_fmt.setAlignment(Qt.AlignLeft)
            cursor.setBlockFormat(block_fmt)
        self.blockSignals(False)

    def get_clean_html_content(self):
        doc = self.document()
        blocks = []
        block = doc.begin()
        while block.isValid():
            text = block.text()
            alignment = block.blockFormat().alignment()
            if alignment & Qt.AlignCenter:
                blocks.append(f"<center>{text}</center>")
            else:
                blocks.append(text)
            block = block.next()
        return "\n".join(blocks)

    def on_text_changed(self):
        self.adjust_height()
        if self.item_ref is not None:
            # .txr içeriğini korumak için temiz html biçimini kullanıyoruz
            if self.item_ref.get('is_txr', False):
                self.item_ref['content'] = self.get_clean_html_content()
            else:
                self.item_ref['content'] = self.toPlainText()

    def adjust_height(self):
        doc_height = self.document().size().height()
        self.setFixedHeight(int(doc_height + 20))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_height()

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        edit_action = QAction("Düzenle", self)
        edit_action.triggered.connect(self.enable_editing)
        menu.insertAction(menu.actions()[0], edit_action)
        menu.insertSeparator(menu.actions()[1])
        menu.exec_(event.globalPos())

    def enable_editing(self):
        self.setReadOnly(False)
        self.setStyleSheet("""
            QTextEdit { background: #222; color: #fff; border: 1px solid #666; padding: 10px; border-radius: 4px; }
        """)
        self.setFocus()

# Dinamik Belge Görüntüleyici: Sadece kendisine verilen pixmap'i doc_size oranında çizer.
class DocumentImageWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = QPixmap()
        self.doc_size = 15
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_pixmap(self, pixmap, doc_size):
        self.pixmap = pixmap
        self.doc_size = doc_size
        self.update_size()
        self.update()

    def update_size(self):
        if self.pixmap.isNull(): return
        
        # Parent QScrollArea'nın genişliğini al
        parent_scroll = self.get_parent_scroll()
        if parent_scroll:
            view_w = parent_scroll.viewport().width() - 40 # Marjinler için pay
        else:
            view_w = self.parentWidget().width() if self.parentWidget() else 800
            
        if view_w <= 0: view_w = 800

        img_w = self.pixmap.width()
        img_h = self.pixmap.height()
        if img_w == 0: return

        ratio = self.doc_size / 15.0
        target_w = view_w * ratio
        scale = target_w / img_w

        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        
        self.setFixedSize(new_w, new_h)

    def get_parent_scroll(self):
        p = self.parentWidget()
        while p:
            if isinstance(p, QScrollArea): return p
            p = p.parentWidget()
        return None

    def paintEvent(self, event):
        if self.pixmap.isNull(): return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(self.rect(), self.pixmap)

class ZoomableImageWidget(QWidget):
    def __init__(self, image_path=None, pixmap=None, parent=None):
        super().__init__(parent)
        raw_pixmap = QPixmap()
        if image_path: raw_pixmap = QPixmap(image_path)
        elif pixmap: raw_pixmap = pixmap
            
        self.pixmap = trim_pixmap_by_alpha(raw_pixmap, margin=0)
        self.scale_factor = 1.0
        self.offset = QPoint(0, 0)
        self.last_mouse_pos = QPoint()
        self.panning = False
        
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setStyleSheet("background-color: #000000;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False) 
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), Qt.black)
        if self.pixmap.isNull(): return

        scaled_w = self.pixmap.width() * self.scale_factor
        scaled_h = self.pixmap.height() * self.scale_factor
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        draw_x = center_x - (scaled_w / 2) + self.offset.x()
        draw_y = center_y - (scaled_h / 2) + self.offset.y()
        
        if (draw_x + scaled_w < 0) or (draw_x > self.width()) or (draw_y + scaled_h < 0) or (draw_y > self.height()):
            return 

        target_rect = QRectF(draw_x, draw_y, scaled_w, scaled_h)
        source_rect = QRectF(self.pixmap.rect())
        painter.drawPixmap(target_rect, self.pixmap, source_rect)

    def wheelEvent(self, event):
        if self.pixmap.isNull(): return
        cursor_pos = event.pos()
        center = QPoint(self.width() // 2, self.height() // 2)
        vec = cursor_pos - center
        delta = event.angleDelta().y()
        zoom_change = 1.1 if delta > 0 else 0.9
        new_scale = self.scale_factor * zoom_change
        
        if new_scale < 0.05: new_scale = 0.05
        if new_scale > 50.0: new_scale = 50.0
        
        effective_factor = new_scale / self.scale_factor
        self.offset = self.offset * effective_factor + vec * (1 - effective_factor)
        self.scale_factor = new_scale
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton: self.fit_logic()
        elif event.button() == Qt.MiddleButton:
            self.panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.panning:
            delta = event.pos() - self.last_mouse_pos
            self.offset += delta
            self.last_mouse_pos = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        self.fit_logic()
        super().resizeEvent(event)

    def fit_logic(self):
        if self.pixmap.isNull() or self.width() == 0: return
        view_w = self.width()
        img_w = self.pixmap.width()
        img_h = self.pixmap.height()
        scale_w = view_w / img_w
        viewport_h = 1000.0 
        try:
            screen = QApplication.primaryScreen()
            if screen: viewport_h = screen.size().height() * 0.8 
            parent = self.parentWidget()
            while parent:
                if isinstance(parent, QScrollArea):
                    viewport_h = parent.viewport().height()
                    break
                parent = parent.parentWidget()
        except: pass

        scale_h = viewport_h / img_h
        self.scale_factor = min(1.0, scale_w, scale_h)
        self.offset = QPoint(0, 0)
        new_height = int(self.pixmap.height() * self.scale_factor)
        if abs(self.height() - new_height) > 2: self.setFixedHeight(new_height)
        self.update()


class ImageOverlayTools(QWidget):
    def __init__(self, parent=None, on_expand=None, on_delete=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(80, 35)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        btn_style = "QToolButton { background: rgba(0,0,0,200); color: white; border: 1px solid #777; border-radius: 3px; font-weight: bold; } QToolButton:hover { background: #000000; border-color: #999; }"
        expand_style = "QToolButton { background: rgba(0,0,0,200); color: white; border: 1px solid #777; border-radius: 3px; font-weight: bold; } QToolButton:hover { background: rgba(0,200,0,200); border-color: lime; }"
        
        self.btn_del = QToolButton()
        self.btn_del.setText("X")
        self.btn_del.setFixedSize(30, 30)
        self.btn_del.setStyleSheet(btn_style)
        self.btn_del.clicked.connect(on_delete)
        self.btn_exp = QToolButton()
        self.btn_exp.setText("_")
        self.btn_exp.setFixedSize(30, 30)
        self.btn_exp.setStyleSheet(expand_style)
        self.btn_exp.clicked.connect(on_expand)
        layout.addWidget(self.btn_del)
        layout.addWidget(self.btn_exp)

class InteractiveTextEdit(QTextEdit):
    def __init__(self, parent_note, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_note = parent_note
        self.setMouseTracking(True)
        self.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        self.overlay = ImageOverlayTools(self, on_expand=self.expand_current_image, on_delete=self.delete_current_image)
        self.overlay.hide()
        self.current_image_name = None
        self.current_cursor_position = -1

    def mouseMoveEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        fmt = cursor.charFormat()
        if fmt.isImageFormat():
            self.current_image_name = fmt.toImageFormat().name()
            self.current_cursor_position = cursor.position()
            rect = self.cursorRect(cursor)
            overlay_pos = self.mapToGlobal(rect.topLeft() + QPoint(5, 5))
            self.overlay.move(overlay_pos)
            self.overlay.show()
            self.overlay.raise_()
        else:
            if not self.overlay.geometry().contains(self.mapToGlobal(event.pos())):
                self.overlay.hide()
        super().mouseMoveEvent(event)

    def delete_current_image(self):
        if self.current_cursor_position != -1:
            c = self.textCursor()
            c.setPosition(self.current_cursor_position)
            c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            if c.charFormat().isImageFormat():
                c.removeSelectedText()
                self.overlay.hide()
            else:
                c.setPosition(self.current_cursor_position)
                c.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
                if c.charFormat().isImageFormat():
                    c.removeSelectedText()
                    self.overlay.hide()

    def expand_current_image(self):
        if not self.current_image_name: return
        dialog = QDialog(self)
        dialog.setWindowTitle("Image Preview")
        dialog.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        dialog.showMaximized()
        dialog.setStyleSheet("background: black;")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 10, 0)
        close_btn = QPushButton("X")
        close_btn.setStyleSheet("background: #333; color: white; font-weight: bold; font-size: 16px; border: none;")
        close_btn.setFixedSize(40, 40)
        close_btn.clicked.connect(dialog.close)
        top_layout.addStretch()
        top_layout.addWidget(close_btn)
        layout.addWidget(top_bar)
        pixmap = QPixmap()
        document = self.document()
        image_resource = document.resource(QTextDocument.ImageResource, QUrl(self.current_image_name))
        if image_resource:
            if isinstance(image_resource, QPixmap): pixmap = image_resource
            elif isinstance(image_resource, QImage): pixmap = QPixmap.fromImage(image_resource)
            elif isinstance(image_resource, (bytes, QByteArray)):
                img = QImage()
                img.loadFromData(image_resource)
                pixmap = QPixmap.fromImage(img)
        if pixmap.isNull() and os.path.exists(self.current_image_name):
             pixmap = QPixmap(self.current_image_name)
        zoom_widget = ZoomableImageWidget(pixmap=pixmap)
        layout.addWidget(zoom_widget)
        QTimer.singleShot(10, zoom_widget.fit_logic)
        dialog.exec_()

# --- ANA KART YAPISI ---

class ImageCardWidget(QWidget):
    def __init__(self, image_path, parent_note, is_gallery=False):
        super().__init__()
        self.parent_note = parent_note
        self.is_gallery = is_gallery
        
        if image_path and not is_gallery:
            self.pixmap = QPixmap(image_path)
            self.pixmap = trim_pixmap_by_alpha(self.pixmap)
        else:
            self.pixmap = QPixmap()
            
        self.setMouseTracking(False)
        self.setFixedHeight(180)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.is_gallery:
            painter.fillRect(self.rect(), QColor("#000000"))
            painter.setPen(QColor("#444"))
            r = self.rect()
            painter.drawLine(0, r.height()-1, r.width(), r.height()-1)
            return

        painter.fillRect(self.rect(), QColor("#1a1a1a"))
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.pixmap.isNull(): return
        target_w = self.width()
        target_h = self.height()
        img_w = self.pixmap.width()
        img_h = self.pixmap.height()
        if img_w == 0 or img_h == 0: return
        scale = max(target_w / img_w, target_h / img_h)
        new_w = img_w * scale
        new_h = img_h * scale
        x = (target_w - new_w) / 2
        y = (target_h - new_h) / 2
        painter.drawPixmap(QRectF(x, y, new_w, new_h), self.pixmap, QRectF(self.pixmap.rect()))
        painter.setPen(QColor("#444"))
        painter.drawRoundedRect(0, 0, target_w-1, target_h-1, 4, 4)

class NoteWidget(QFrame):
    MAX_GALLERY_ITEMS = 35 

    def __init__(self, parent_window, pkg_text="", note_text="", image_path=None, is_gallery=False, is_document=False, doc_type=None):
        super().__init__()
        self.parent_window = parent_window
        self.pkg_text_val = pkg_text
        self.is_image_mode = True if (image_path or is_gallery or is_document) else False
        self.is_gallery_mode = is_gallery
        self.is_document_mode = is_document
        self.doc_type = doc_type 
        self.sub_items = []
        
        self.item_widgets_refs = []
        self.active_scroll_area = None
        self.expanded_text_edit = None
        self.active_animations = [] 

        # Belgelere özel kalıcı ayarlar
        self.doc_size = 15
        self.current_page_idx = 0

        self.cached_expanded_widget = None
        self.cached_doc_size = None

        if self.is_image_mode and image_path:
            self.add_sub_item(image_path, 'img')
        self.note_text_val = note_text 
        self.is_expanded = False
        self.init_components()
        self.setup_layout_structure()
        self.setStyleSheet("NoteWidget { background-color: #2b2b2b; border: 1px solid #444; border-radius: 8px; }")
        if not self.is_expanded:
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.setFixedHeight(220)

    def init_components(self):
        self.pkg_edit = QLineEdit(self.pkg_text_val)
        self.pkg_edit.setPlaceholderText("Note Title")
        self.pkg_edit.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.pkg_edit.setStyleSheet("QLineEdit { background: #1a1a1a; color: #ffffff; border: 1px solid #555; padding: 4px; border-radius: 4px; }")
        
        self.btn_style_visible = """
            QToolButton { background-color: #444; color: #eee; border: 1px solid #666; border-radius: 6px; font-weight: bold; font-family: 'Segoe UI'; } 
            QToolButton:hover { background-color: #555; color: white; border-color: #888; }
            QToolButton:pressed { background-color: #333; }
        """
        
        self.copy_btn = QToolButton()
        self.copy_btn.setText("/") 
        self.copy_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.copy_btn.setFixedSize(30, 30)
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.setStyleSheet(self.btn_style_visible)
        self.copy_btn.setFocusPolicy(Qt.NoFocus)

        self.max_btn = QToolButton()
        self.max_btn.setText("_") 
        self.max_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.max_btn.setFixedSize(30, 30)
        self.max_btn.clicked.connect(self.toggle_maximize)
        self.max_btn.setStyleSheet(self.btn_style_visible)
        self.max_btn.setFocusPolicy(Qt.NoFocus)

        self.delete_btn = QToolButton()
        self.delete_btn.setText("X")
        self.delete_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.delete_btn.setFixedSize(40, 30)
        self.delete_btn.clicked.connect(self.delete_self)
        self.delete_btn.setStyleSheet("QToolButton { background-color: #444; color: #aaa; border: 1px solid #666; border-radius: 6px; } QToolButton:hover { background-color: #000000; color: #fff; border-color: #999; }")
        self.delete_btn.setFocusPolicy(Qt.NoFocus)

        if self.is_image_mode:
            first_img = ""
            for item in self.sub_items:
                if item['type'] == 'img':
                    first_img = item['content']
                    break
            self.image_card = ImageCardWidget(first_img, self, is_gallery=(self.is_gallery_mode or self.is_document_mode))
            self.text_edit = None
        else:
            self.text_edit = InteractiveTextEdit(self)
            self.text_edit.setHtml(self.note_text_val)
            self.text_edit.setPlaceholderText("Content")
            self.text_edit.setStyleSheet("QTextEdit { background: #1a1a1a; color: #dddddd; border: 1px solid #555; padding: 4px; border-radius: 4px; }")
            self.text_edit.textChanged.connect(self.on_text_changed)
            self.image_card = None

    def on_text_changed(self):
        self.note_text_val = self.text_edit.toHtml()
        if self.is_expanded and self.parent_window.expanded_note_widget == self:
             self.parent_window.update_nav_button_text_mode(self)

    def setup_layout_structure(self):
        if self.layout(): QWidget().setLayout(self.layout())
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(4)
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(4)
        self.main_layout.addLayout(self.header_layout)
        if not self.is_image_mode and self.text_edit: self.main_layout.addWidget(self.text_edit)
        elif self.image_card: self.main_layout.addWidget(self.image_card)

    def set_column_mode(self):
        while self.header_layout.count():
            item = self.header_layout.takeAt(0)
            if item.widget(): item.widget().setParent(None)
        self.header_layout.addWidget(self.delete_btn)
        self.header_layout.addWidget(self.pkg_edit, 1)
        self.header_layout.addWidget(self.max_btn)
        self.header_layout.addWidget(self.copy_btn)
        self.delete_btn.show()
        self.pkg_edit.show()
        self.max_btn.show()
        self.copy_btn.show()

    def get_pdf_page_pixmap(self, pdf_path, page_index):
        if not fitz: return QPixmap()
        try:
            doc = fitz.open(pdf_path)
            if page_index < 0 or page_index >= len(doc): return QPixmap()
            page = doc.load_page(page_index)
            pix = page.get_pixmap(matrix=fitz.Matrix(150/72, 150/72))
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
            doc.close()
            return QPixmap.fromImage(img)
        except Exception as e:
            print(f"PDF Render Error: {e}")
            return QPixmap()

    def add_sub_item(self, file_path, file_type='img', forced_name=None, is_raw_content=False, page_index=None, is_txr=False):
        limit = 500 if (getattr(self, 'is_document_mode', False) and self.doc_type in ['pdf', 'pnf']) else (200 if getattr(self, 'is_document_mode', False) else self.MAX_GALLERY_ITEMS)
        if len(self.sub_items) >= limit: return 

        content_obj = {'type': file_type, 'content': file_path, 'is_txr': is_txr}
        
        if file_type == 'txt':
            if is_raw_content: content_obj['content'] = file_path
            else:
                 try:
                    with open(file_path, 'r', encoding='utf-8') as f: content_obj['content'] = f.read()
                 except: content_obj['content'] = "Error reading file."
        elif file_type == 'pdf_page':
            content_obj['page_index'] = page_index

        if forced_name: display_name = forced_name
        else:
            if is_raw_content: display_name = "Text Note"
            elif file_type == 'pdf_page': display_name = f"Sayfa {len(self.sub_items)+1}"
            else:
                base_name = os.path.basename(file_path)
                name_root, name_ext = os.path.splitext(base_name)
                existing_names = [item.get('name', '') for item in self.sub_items]
                display_name = base_name
                counter = 1
                while display_name in existing_names:
                    display_name = f"{name_root} ({counter}){name_ext}"
                    counter += 1
        content_obj['name'] = display_name
        self.sub_items.append(content_obj)
        self.invalidate_cache()

    def remove_sub_item(self, index):
        if self.is_expanded and index < len(self.item_widgets_refs):
            target_widget = self.item_widgets_refs[index]
            effect = QGraphicsOpacityEffect(target_widget)
            target_widget.setGraphicsEffect(effect)
            anim_group = QParallelAnimationGroup()
            anim_height = QPropertyAnimation(target_widget, b"maximumHeight")
            anim_height.setDuration(300) 
            anim_height.setStartValue(target_widget.height())
            anim_height.setEndValue(0)
            anim_height.setEasingCurve(QEasingCurve.InOutQuart)
            anim_opacity = QPropertyAnimation(effect, b"opacity")
            anim_opacity.setDuration(250)
            anim_opacity.setStartValue(1.0)
            anim_opacity.setEndValue(0.0)
            anim_opacity.setEasingCurve(QEasingCurve.Linear)
            anim_group.addAnimation(anim_height)
            anim_group.addAnimation(anim_opacity)
            anim_group.finished.connect(lambda: self.finalize_removal(index))
            anim_group.start()
            self.active_animations.append(anim_group)
        else:
            self.finalize_removal(index)

    def finalize_removal(self, index):
        if 0 <= index < len(self.sub_items):
            del self.sub_items[index]
            new_len = len(self.sub_items)
            target_index = 0 if new_len == 0 else (new_len - 1 if index >= new_len else index)
            self.invalidate_cache()
            self.parent_window.expand_note(self, maintain_scroll=True, target_item_index=target_index, show_progress=False)

    def move_item_up(self, index):
        if index > 0: self.swap_items(index, index - 1)

    def move_item_down(self, index):
        if index < len(self.sub_items) - 1: self.swap_items(index, index + 1)
    
    def swap_items(self, from_idx, to_idx):
        if 0 <= from_idx < len(self.sub_items) and 0 <= to_idx < len(self.sub_items):
            self.sub_items[from_idx], self.sub_items[to_idx] = self.sub_items[to_idx], self.sub_items[from_idx]
            self.invalidate_cache()
            self.parent_window.expand_note(self, maintain_scroll=False, target_item_index=to_idx, show_progress=False)

    def show_order_menu(self, btn, current_idx):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item { padding: 5px 20px; } QMenu::item:selected { background-color: #555; }")
        menu.setFixedHeight(min(600, 35 * len(self.sub_items) + 20))
        for i in range(len(self.sub_items)):
            action_text = f"#{i+1}"
            if i == current_idx: action_text += " <"
            action = menu.addAction(action_text)
            action.triggered.connect(lambda checked, t=i: self.swap_items(current_idx, t))
        menu.exec_(btn.mapToGlobal(QPoint(0, btn.height())))

    def toggle_maximize(self):
        if self.parent_window.expanded_note_widget == self: self.parent_window.collapse_note(self)
        else: self.parent_window.expand_note(self)

    def invalidate_cache(self):
        if self.cached_expanded_widget:
            self.cached_expanded_widget.deleteLater()
            self.cached_expanded_widget = None
        self.cached_doc_size = None

    def get_or_create_expanded_content(self, current_scroll_val=0, show_progress=False, doc_size=15):
        # Belge boyutu çakışmalarını ve bellek silinme çökmelerini engellemek için cache kullanımı düzeltildi.
        if self.cached_expanded_widget is not None:
            if getattr(self, 'is_document_mode', False) and hasattr(self, 'doc_image_widget'):
                # Önbellekteki belge görünümünün boyutunu güvenli bir şekilde tazele
                try:
                    self.doc_image_widget.doc_size = self.doc_size
                    self.doc_image_widget.update_size()
                except RuntimeError:
                    pass
            return self.cached_expanded_widget
        else:
            if self.cached_expanded_widget:
                self.cached_expanded_widget.deleteLater()
                self.cached_expanded_widget = None
            # Sadece yükleme anı dışında progress bar iptal edildi.
            widget = self.get_expanded_content(current_scroll_val, False, self.doc_size)
            self.cached_expanded_widget = widget
            return widget

    def update_document_view(self):
        if not getattr(self, 'is_document_mode', False) or not self.sub_items: return
        
        # Çökmeleri önlemek için çalışma zamanı C++ nesne bütünlüğünü test et
        try:
            if not hasattr(self, 'doc_image_widget') or not self.doc_image_widget: return
            idx = self.current_page_idx
            item = self.sub_items[idx]

            pixmap = QPixmap()
            if item['type'] == 'pdf_page':
                pixmap = self.get_pdf_page_pixmap(item['content'], item.get('page_index', 0))
            elif item['type'] == 'img':
                pixmap = QPixmap(item['content'])
            
            if hasattr(self, 'doc_page_label'):
                self.doc_page_label.setText(f"Sayfa {idx + 1} / {len(self.sub_items)}")
            
            # Belge her zaman bu nota özel olan "self.doc_size" boyutunu kullanır
            self.doc_image_widget.set_pixmap(pixmap, self.doc_size)
            
            if self.active_scroll_area and self.active_scroll_area.verticalScrollBar():
                self.active_scroll_area.verticalScrollBar().setValue(0)
                
            if self.parent_window.expanded_note_widget == self:
                self.parent_window.nav_btn.setText(f"#{idx + 1}")
        except RuntimeError:
            pass

    def get_expanded_content(self, current_scroll_val=0, show_progress=False, doc_size=15):
        self.item_widgets_refs = [] 
        # Bellek sızıntılarını önlemek için widget ebeveyni NoteWidget(self) yapıldı
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if self.is_image_mode:
            scroll = QScrollArea()
            scroll.setObjectName("expanded_scroll_area")
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
            
            # Yalnızca galeri modunda aşağı kaydırma ile sayfa numarasını güncelle
            if not getattr(self, 'is_document_mode', False):
                scroll.verticalScrollBar().valueChanged.connect(self.parent_window.on_gallery_scroll)
            
            scroll_content = QWidget()
            scroll_content.setStyleSheet("background-color: #444;") 
            scroll_layout = QVBoxLayout(scroll_content)
            scroll_layout.setAlignment(Qt.AlignTop)
            
            total_items = len(self.sub_items)

            if getattr(self, 'is_document_mode', False):
                # SADECE TEK SAYFA/RESİM GÖRÜNÜMÜ
                scroll_layout.setContentsMargins(10, 20, 10, 60)
                scroll_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

                self.doc_page_label = QLabel("Sayfa 1")
                self.doc_page_label.setStyleSheet("color: #888; font-weight: bold; font-size: 14px;")
                self.doc_page_label.setAlignment(Qt.AlignCenter)
                scroll_layout.addWidget(self.doc_page_label)

                page_container = QWidget()
                page_layout = QVBoxLayout(page_container)
                page_layout.setContentsMargins(0, 0, 0, 0)
                page_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

                self.doc_image_widget = DocumentImageWidget()
                page_layout.addWidget(self.doc_image_widget)
                scroll_layout.addWidget(page_container)

                # Belge görünümünü ilk kurulumda güncelle (layout otursun diye zamanı 50ms yaptık)
                QTimer.singleShot(50, self.update_document_view)

            else:
                # NORMAL GALERİ GÖRÜNÜMÜ
                scroll_layout.setContentsMargins(60, 30, 200, 60)
                scroll_layout.setSpacing(20) 
                
                gallery_btn_style = "QToolButton { background-color: #444; color: #eee; border: 1px solid #666; border-radius: 6px; font-weight: bold; font-family: 'Segoe UI'; } QToolButton:hover { background-color: #555; color: white; border-color: #888; } QToolButton:pressed { background-color: #333; }"
                del_style = "QToolButton { background-color: #333; color: #aaa; border: 1px solid #555; border-radius: 6px; font-weight: bold; font-family: 'Segoe UI'; } QToolButton:hover { background-color: #000000; color: #fff; border-color: #999; } QToolButton:pressed { background-color: #222; }"

                for idx, item in enumerate(self.sub_items):
                    item_container = QWidget()
                    item_container.setAttribute(Qt.WA_LayoutUsesWidgetRect)
                    self.item_widgets_refs.append(item_container)
                    
                    item_layout = QVBoxLayout(item_container)
                    item_layout.setContentsMargins(0, 0, 0, 0)
                    item_layout.setSpacing(5)

                    file_name = item.get('name', 'Unknown')
                    label = QLabel(file_name)
                    label.setFont(QFont("Segoe UI", 14, QFont.Bold))
                    label.setStyleSheet("color: #aaa; padding-left: 110px;") 
                    label.setAlignment(Qt.AlignLeft)
                    item_layout.addWidget(label)

                    row_widget = QWidget()
                    row_layout = QHBoxLayout(row_widget)
                    row_layout.setContentsMargins(0, 0, 0, 0)
                    row_layout.setSpacing(30) 

                    controls_panel = QWidget()
                    controls_panel.setFixedWidth(100)
                    controls_panel.setStyleSheet("background: transparent;") 
                    controls_panel_layout = QHBoxLayout(controls_panel)
                    controls_panel_layout.setContentsMargins(0, 0, 0, 0)
                    controls_panel_layout.setSpacing(10)
                    controls_panel_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

                    sub_del_btn = QToolButton()
                    sub_del_btn.setText("X")
                    sub_del_btn.setFixedSize(30, 30)
                    sub_del_btn.setStyleSheet(del_style)
                    sub_del_btn.clicked.connect(lambda _, i=idx: self.remove_sub_item(i))
                    sub_del_btn.setFocusPolicy(Qt.NoFocus)
                    controls_panel_layout.addWidget(sub_del_btn)

                    controls_panel_layout.addSpacing(10)

                    stack_widget = QWidget()
                    stack_layout = QVBoxLayout(stack_widget)
                    stack_layout.setContentsMargins(0, 0, 0, 0)
                    stack_layout.setSpacing(2)

                    up_btn = QToolButton()
                    up_btn.setText("▲")
                    up_btn.setFixedSize(50, 20)
                    up_btn.setStyleSheet(gallery_btn_style)
                    up_btn.clicked.connect(lambda _, i=idx: self.move_item_up(i))
                    up_btn.setFocusPolicy(Qt.NoFocus)
                    
                    num_btn = QToolButton()
                    num_btn.setText(f"#{idx + 1}")
                    num_btn.setFixedSize(50, 30)
                    num_btn.setStyleSheet(gallery_btn_style)
                    num_btn.clicked.connect(lambda _, b=num_btn, i=idx: self.show_order_menu(b, i))
                    num_btn.setFocusPolicy(Qt.NoFocus)

                    down_btn = QToolButton()
                    down_btn.setText("▼")
                    down_btn.setFixedSize(50, 20)
                    down_btn.setStyleSheet(gallery_btn_style)
                    down_btn.clicked.connect(lambda _, i=idx: self.move_item_down(i))
                    down_btn.setFocusPolicy(Qt.NoFocus)

                    stack_layout.addWidget(up_btn)
                    stack_layout.addWidget(num_btn)
                    stack_layout.addWidget(down_btn)
                    
                    controls_panel_layout.addWidget(stack_widget)
                    row_layout.addWidget(controls_panel)

                    if item['type'] == 'img':
                        zoom_widget = ZoomableImageWidget(image_path=item['content'])
                        row_layout.addWidget(zoom_widget, 1)
                        QTimer.singleShot(10, zoom_widget.fit_logic)
                    elif item['type'] == 'txt':
                        txt_widget = AutoResizingTextEdit(item['content'], item_ref=item)
                        row_layout.addWidget(txt_widget, 1)

                    item_layout.addWidget(row_widget)
                    scroll_layout.addWidget(item_container)
            
            scroll.setWidget(scroll_content)
            
            if current_scroll_val > 0 and not getattr(self, 'is_document_mode', False):
                 def safe_scroll_restore():
                     try:
                         if not scroll.isHidden() and scroll.verticalScrollBar():
                             scroll.verticalScrollBar().setValue(current_scroll_val)
                     except RuntimeError: pass
                 QTimer.singleShot(10, safe_scroll_restore)
                 
            layout.addWidget(scroll)
            self.active_scroll_area = scroll
            self.expanded_text_edit = None
            
        else:
            text_container = QWidget()
            text_container.setStyleSheet("background-color: #444;")
            text_layout = QVBoxLayout(text_container)
            text_layout.setContentsMargins(30, 30, 30, 30)
            text_layout.setAlignment(Qt.AlignCenter)

            large_edit = InteractiveTextEdit(self)
            large_edit.setStyleSheet("background: #111; color: #fff; font-size: 16px; border: none;")
            large_edit.setReadOnly(False)
            
            large_edit.textChanged.connect(lambda: [
                setattr(self, 'note_text_val', large_edit.toHtml()),
                self.parent_window.update_nav_button_text_mode(self)
            ])
            
            large_edit.setHtml(self.note_text_val)
            self.temp_large_edit = large_edit
            
            text_layout.addWidget(large_edit)
            layout.addWidget(text_container)
            self.expanded_text_edit = large_edit
            self.active_scroll_area = None

        return container

    def update_text_from_expanded(self):
        try:
            if hasattr(self, 'temp_large_edit') and self.text_edit:
                current_html = self.temp_large_edit.toHtml()
                self.text_edit.setHtml(current_html)
                self.note_text_val = current_html
        except RuntimeError: pass

    def refresh_expanded_view(self):
        last_index = len(self.sub_items) - 1
        self.invalidate_cache()
        QApplication.processEvents() 
        self.parent_window.expand_note(self, maintain_scroll=False, target_item_index=last_index, show_progress=False)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        mime_data = QMimeData()

        if self.is_image_mode:
            urls = []
            temp_dir = os.path.join(self.parent_window.DEFAULT_BASE_DIR, 'temp_clip')
            if not os.path.exists(temp_dir): os.makedirs(temp_dir)

            for item in self.sub_items:
                path = item['content']
                if item['type'] == 'img':
                     if os.path.exists(path):
                        urls.append(QUrl.fromLocalFile(path))
                elif item['type'] == 'txt':
                    try:
                        safe_name = item.get('name', f"{uuid.uuid4()}.txt")
                        temp_path = os.path.join(temp_dir, safe_name)
                        with open(temp_path, 'w', encoding='utf-8') as f:
                            f.write(item['content'])
                        urls.append(QUrl.fromLocalFile(temp_path))
                    except: pass
                elif item['type'] == 'pdf_page':
                    try:
                        pixmap = self.get_pdf_page_pixmap(item['content'], item.get('page_index', 0))
                        if not pixmap.isNull():
                            safe_name = item.get('name', f"page_{uuid.uuid4()}.png")
                            temp_path = os.path.join(temp_dir, safe_name)
                            pixmap.save(temp_path, "PNG")
                            urls.append(QUrl.fromLocalFile(temp_path))
                    except: pass

            if urls:
                mime_data.setUrls(urls)
                clipboard.setMimeData(mime_data)
                if not self.is_expanded: 
                    self.copy_btn.setText("OK")
                    QTimer.singleShot(1000, lambda: self.copy_btn.setText("/"))
        else:
            text_val = ""
            if self.text_edit: text_val = self.text_edit.toPlainText()
            elif hasattr(self, 'temp_large_edit'): text_val = self.temp_large_edit.toPlainText()
            else: 
                doc = QTextDocument()
                doc.setHtml(self.note_text_val)
                text_val = doc.toPlainText()
            
            clipboard.setText(text_val)
            if not self.is_expanded:
                self.copy_btn.setText("TXT")
                QTimer.singleShot(1000, lambda: self.copy_btn.setText("/"))

    def delete_self(self):
        if self.is_expanded:
            self.parent_window.collapse_note(self)
        self.parent_window.remove_note(self)

    def to_dict(self):
        data = { 
            'package': self.pkg_edit.text(),
            'doc_size': getattr(self, 'doc_size', 15),
            'is_document_mode': getattr(self, 'is_document_mode', False),
            'doc_type': getattr(self, 'doc_type', None)
        }
        if self.is_image_mode:
            serialized_items = []
            for item in self.sub_items:
                filename = os.path.basename(item['content']) if item.get('content') and os.path.isabs(item['content']) else item.get('content', '')
                
                if item['type'] == 'pdf_page':
                    serialized_items.append({'type': 'pdf_page', 'filename': filename, 'page_index': item.get('page_index', 0), 'name': item.get('name', '')})
                elif item['type'] == 'img':
                    serialized_items.append({'type': 'img', 'filename': filename, 'name': item.get('name', '')})
                elif item['type'] == 'txt':
                    serialized_items.append({'type': 'txt', 'data': item['content'], 'name': item.get('name', 'text.txt'), 'is_txr': item.get('is_txr', False)})
            data['gallery_data'] = serialized_items
            
            if getattr(self, 'is_document_mode', False):
                data['note'] = f"[DOCUMENT_PACKAGE_{self.doc_type.upper()}]"
            else:
                data['note'] = "[GALLERY_PACKAGE]" 
        else:
            data['note'] = self.note_text_val
        return data


class MainWindow(QMainWindow):
    DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')
    SETTINGS_FILE = os.path.join(DEFAULT_BASE_DIR, 'settings.json')
    MAX_NOTES = 200

    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        self.setWindowTitle("Copya")
        self.resize(1100, 750)
        self.current_file_path = None
        self.expanded_note_widget = None 
        
        # Çalışma alanı klasörü: Export/copi
        self.COPI_DIR = os.path.join(self.DEFAULT_BASE_DIR, 'copi')
        os.makedirs(self.COPI_DIR, exist_ok=True)
        self.clear_copi_folder() # Her başlangıçta tertemiz bir workspace
        
        self.auto_scroll_timer = QTimer(self)
        self.auto_scroll_timer.timeout.connect(self.process_auto_scroll)
        self.scroll_speeds = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]
        
        self.current_scroll_speed_index = 4
        self.current_doc_size = 15
        self.load_settings()
        self.scroll_rate = self.scroll_speeds[self.current_scroll_speed_index]
        self.scroll_accumulator = 0.0
        self.auto_scroll_active = False

        self.init_ui()

    def clear_copi_folder(self):
        try:
            for filename in os.listdir(self.COPI_DIR):
                filepath = os.path.join(self.COPI_DIR, filename)
                if os.path.isfile(filepath) or os.path.islink(filepath): os.unlink(filepath)
                elif os.path.isdir(filepath): shutil.rmtree(filepath)
        except Exception: pass

    def copy_to_copi(self, source_path):
        filename = os.path.basename(source_path)
        unique_name = f"{uuid.uuid4()}_{filename}"
        copi_path = os.path.join(self.COPI_DIR, unique_name)
        shutil.copy2(source_path, copi_path)
        return copi_path

    def load_settings(self):
        try:
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    self.current_scroll_speed_index = data.get('scroll_speed_index', 4)
                    self.current_doc_size = data.get('doc_size', 15)
        except: pass

    def save_settings(self):
        try:
            QDir().mkpath(self.DEFAULT_BASE_DIR)
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump({'scroll_speed_index': self.current_scroll_speed_index, 'doc_size': self.current_doc_size}, f)
        except: pass

    # ---------- KLAVYE GEZİNTİ METOTLARI (QShortcut ile bağlı) ----------
    def navigate_package_left(self):
        self.navigate_package(-1)

    def navigate_package_right(self):
        self.navigate_package(1)

    def navigate_package(self, delta):
        if not self.notes_list:
            return
        if self.expanded_note_widget:
            try:
                current_idx = self.notes_list.index(self.expanded_note_widget)
            except ValueError:
                current_idx = 0
            new_idx = (current_idx + delta) % len(self.notes_list)
            self.collapse_note(self.expanded_note_widget)
            target_note = self.notes_list[new_idx]
            self.expand_note(target_note, target_item_index=target_note.current_page_idx)
        else:
            new_idx = 0 if delta > 0 else -1
            target_note = self.notes_list[new_idx]
            self.expand_note(target_note, target_item_index=target_note.current_page_idx)

    def navigate_page_up(self):
        if self.expanded_note_widget and self.expanded_note_widget.is_image_mode:
            if getattr(self.expanded_note_widget, 'is_document_mode', False):
                self.change_document_page(-1)
            else:
                self.scroll_to_relative_item(-1)

    def navigate_page_down(self):
        if self.expanded_note_widget and self.expanded_note_widget.is_image_mode:
            if getattr(self.expanded_note_widget, 'is_document_mode', False):
                self.change_document_page(1)
            else:
                self.scroll_to_relative_item(1)

    def scroll_to_relative_item(self, delta):
        note = self.expanded_note_widget
        if not note.sub_items:
            return
        new_idx = (note.current_page_idx + delta) % len(note.sub_items)
        note.current_page_idx = new_idx
        self.scroll_to_item(new_idx)

    def change_document_page(self, delta):
        if not self.expanded_note_widget: return
        note = self.expanded_note_widget
        if not note.sub_items: return
        new_idx = (note.current_page_idx + delta) % len(note.sub_items)
        note.current_page_idx = new_idx
        note.update_document_view()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.expanded_note_widget and getattr(self.expanded_note_widget, 'is_document_mode', False):
            try:
                if hasattr(self.expanded_note_widget, 'doc_image_widget') and self.expanded_note_widget.doc_image_widget:
                    self.expanded_note_widget.doc_image_widget.update_size()
            except RuntimeError:
                pass

    def init_ui(self):
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #222;")
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.toolbar_frame = QFrame()
        self.toolbar_frame.setObjectName("MainToolbar")
        self.toolbar_frame.setStyleSheet("#MainToolbar { background-color: #222222; border-bottom: 2px solid #555555; }")
        self.toolbar_frame.setFixedHeight(40)
        toolbar_layout = QHBoxLayout(self.toolbar_frame)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.setSpacing(10)

        self.file_btn = QPushButton("File")
        self.file_btn.setStyleSheet(self.buttonStyle())
        self.file_btn.setFixedSize(90, 30)
        self.file_btn.clicked.connect(lambda: self.load_copya())
        self.file_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.file_btn)

        self.save_btn = QPushButton()
        self.save_btn.setIcon(create_svg_icon(SVG_SAVE_ICON, size=20, color="#ffffff"))
        self.save_btn.setStyleSheet(self.buttonStyle())
        self.save_btn.setFixedSize(30, 30)
        self.save_btn.clicked.connect(self.quick_save)
        self.save_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.save_btn)

        self.add_btn = QPushButton("+")
        self.add_btn.setStyleSheet(self.buttonStyle())
        self.add_btn.setFixedSize(30, 30)
        self.add_btn.clicked.connect(lambda: self.add_note())
        self.add_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.add_btn)

        self.gallery_btn = QPushButton("Galeri")
        self.gallery_btn.setStyleSheet(self.buttonStyle())
        self.gallery_btn.setFixedSize(80, 30)
        self.gallery_btn.clicked.connect(self.handle_gallery_click)
        self.gallery_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.gallery_btn)

        self.belge_btn = QPushButton("Belge")
        self.belge_btn.setStyleSheet(self.buttonStyle())
        self.belge_btn.setFixedSize(80, 30)
        self.belge_btn.clicked.connect(self.handle_document_click)
        self.belge_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.belge_btn)

        self.nav_btn = QPushButton("#1")
        self.nav_btn.setStyleSheet(self.buttonStyle())
        self.nav_btn.setFixedSize(55, 30)
        self.nav_btn.setEnabled(False)
        self.nav_btn.clicked.connect(self.show_nav_menu)
        self.nav_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.nav_btn)

        self.read_mode_btn = QPushButton("I") 
        self.read_mode_btn.setStyleSheet(self.buttonStyle() + " font-weight: bold; color: white;")
        self.read_mode_btn.setFixedSize(30, 30)
        self.read_mode_btn.clicked.connect(self.toggle_auto_scroll)
        self.read_mode_btn.setToolTip("Auto Scroll (Read Mode)")
        self.read_mode_btn.setEnabled(True) 
        self.read_mode_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.read_mode_btn)

        self.scroll_speed_btn = QPushButton(str(self.scroll_rate))
        self.scroll_speed_btn.setStyleSheet(self.buttonStyle())
        self.scroll_speed_btn.setFixedSize(40, 30)
        self.scroll_speed_btn.clicked.connect(self.show_speed_menu)
        self.scroll_speed_btn.setToolTip("Scroll Speed")
        self.scroll_speed_btn.setEnabled(False)
        self.scroll_speed_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.scroll_speed_btn)

        self.doc_size_btn = QPushButton(f"{self.current_doc_size}")
        self.doc_size_btn.setStyleSheet(self.buttonStyle())
        self.doc_size_btn.setFixedSize(50, 30) 
        self.doc_size_btn.clicked.connect(self.show_size_menu)
        self.doc_size_btn.setToolTip("Belge Boyutu")
        self.doc_size_btn.setEnabled(False)
        self.doc_size_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.doc_size_btn)

        self.tool_delete_btn = QPushButton("X")
        self.tool_delete_btn.setStyleSheet("QPushButton { background-color: transparent; color: white; font-size: 14px; font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 5px; } QPushButton:hover { background-color: #000000; border-color: #999; } QPushButton:pressed { background-color: #222; } QPushButton:disabled { color: #555; border-color: #333; }")
        self.tool_delete_btn.setFixedSize(30, 30)
        self.tool_delete_btn.setEnabled(False) 
        self.tool_delete_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.tool_delete_btn)

        self.tool_min_btn = QPushButton("_")
        self.tool_min_btn.setStyleSheet(self.buttonStyle())
        self.tool_min_btn.setFixedSize(30, 30)
        self.tool_min_btn.setEnabled(False)
        self.tool_min_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.tool_min_btn)

        self.tool_copy_btn = QPushButton("/")
        self.tool_copy_btn.setStyleSheet(self.buttonStyle()) 
        self.tool_copy_btn.setFixedSize(30, 30)
        self.tool_copy_btn.setEnabled(False)
        self.tool_copy_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.tool_copy_btn)

        self.right_spacer = QWidget()
        self.right_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar_layout.addWidget(self.right_spacer)

        self.export_btn = QPushButton("Export")
        self.export_btn.setStyleSheet(self.buttonStyle())
        self.export_btn.setFixedSize(90, 30)
        self.export_btn.clicked.connect(self.export_copya)
        self.export_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.export_btn)

        self.switcher_btn = QPushButton("Copy") 
        self.switcher_btn.setStyleSheet(self.buttonStyle())
        self.switcher_btn.setFixedSize(90, 30)
        self.switcher_btn.clicked.connect(self.triggerCoreSwitcher)
        self.switcher_btn.setFocusPolicy(Qt.NoFocus)
        toolbar_layout.addWidget(self.switcher_btn)

        main_layout.addWidget(self.toolbar_frame)
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)

        self.grid_page = QWidget()
        grid_layout = QVBoxLayout(self.grid_page)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        container.setStyleSheet("background-color: #121212;")
        self.columns_layout = QHBoxLayout(container)
        self.columns_layout.setAlignment(Qt.AlignTop)
        self.columns_layout.setSpacing(15)
        self.columns_layout.setContentsMargins(15, 20, 15, 20)

        self.col1_widget = QWidget()
        self.col1_layout = QVBoxLayout(self.col1_widget)
        self.col1_layout.setAlignment(Qt.AlignTop)
        self.col1_layout.setSpacing(10)
        self.col1_layout.setContentsMargins(0, 0, 0, 0)

        self.col2_widget = QWidget()
        self.col2_layout = QVBoxLayout(self.col2_widget)
        self.col2_layout.setAlignment(Qt.AlignTop)
        self.col2_layout.setSpacing(10)
        self.col2_layout.setContentsMargins(0, 0, 0, 0)

        self.col3_widget = QWidget()
        self.col3_layout = QVBoxLayout(self.col3_widget)
        self.col3_layout.setAlignment(Qt.AlignTop)
        self.col3_layout.setSpacing(10)
        self.col3_layout.setContentsMargins(0, 0, 0, 0)

        self.columns_layout.addWidget(self.col1_widget, 1)
        self.columns_layout.addWidget(self.col2_widget, 1)
        self.columns_layout.addWidget(self.col3_widget, 1)
        self.scroll.setWidget(container)
        grid_layout.addWidget(self.scroll)
        self.content_stack.addWidget(self.grid_page)

        self.expanded_page = QWidget()
        self.expanded_page.setStyleSheet("background-color: #000000;")
        self.expanded_layout = QVBoxLayout(self.expanded_page)
        self.expanded_layout.setContentsMargins(0, 0, 0, 0)
        self.content_stack.addWidget(self.expanded_page)

        self.notes_list = []

        # --- QShortcut ile ok tuşu navigasyonu ---
        self.shortcut_left = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.shortcut_left.activated.connect(self.navigate_package_left)
        self.shortcut_right = QShortcut(QKeySequence(Qt.Key_Right), self)
        self.shortcut_right.activated.connect(self.navigate_package_right)

        self.shortcut_up = QShortcut(QKeySequence(Qt.Key_Up), self)
        self.shortcut_up.activated.connect(self.navigate_page_up)
        self.shortcut_down = QShortcut(QKeySequence(Qt.Key_Down), self)
        self.shortcut_down.activated.connect(self.navigate_page_down)

    def handle_document_click(self):
        # Belge butonu artık PDF'lerin yanında .pnf formatını da destekliyor
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Belge Seç", self.DEFAULT_BASE_DIR, 
            "Desteklenen Belgeler (*.pdf *.pnf);;PDF Belgeleri (*.pdf);;Drawing Projeleri (*.pnf)"
        )
        if not file_paths: return
        
        pnf_files = [f for f in file_paths if f.lower().endswith('.pnf')]
        pdf_files = [f for f in file_paths if f.lower().endswith('.pdf')]
        
        if len(pnf_files) > 0:
            self.create_pnf_note(pnf_files[0])
        elif len(pdf_files) > 0:
            if not PDF_SUPPORT:
                QMessageBox.critical(self, "Eksik Kütüphane", "PDF desteği için PyMuPDF (fitz) kütüphanesi gereklidir.")
                return
            self.create_pdf_note(pdf_files[0])

    def create_pnf_note(self, pnf_path):
        try:
            # PNF projesini çalışma alanına kopyala
            copi_pnf_path = self.copy_to_copi(pnf_path)
            
            with open(copi_pnf_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
                
            if not isinstance(project_data, list):
                QMessageBox.critical(self, "Hata", "Geçersiz PNF veri yapısı.")
                return
                
            new_note = self.add_note(pkg_text=os.path.basename(pnf_path), note_text="", image_path=None, is_gallery=False, is_document=True, doc_type='pnf')
            new_note.is_image_mode = True
            new_note.doc_size = self.current_doc_size
            
            if new_note.text_edit:
                new_note.text_edit.setParent(None)
                new_note.text_edit.deleteLater()
                new_note.text_edit = None
            if not new_note.image_card:
                new_note.image_card = ImageCardWidget(None, new_note, is_gallery=True)
                new_note.main_layout.addWidget(new_note.image_card)
                
            for idx, page in enumerate(project_data):
                b64_image = page.get("image_data", "")
                if b64_image:
                    image_data = base64.b64decode(b64_image)
                    unique_img_name = f"{uuid.uuid4()}_page_{idx+1}.png"
                    img_path = os.path.join(self.COPI_DIR, unique_img_name)
                    with open(img_path, 'wb') as img_f:
                        img_f.write(image_data)
                        
                    new_note.add_sub_item(img_path, 'img', forced_name=f"Sayfa {idx+1}")
                    
            self.refresh_layout()
        except Exception as e:
            QMessageBox.critical(self, "PNF Hatası", f"PNF işlenirken hata oluştu:\n{str(e)}")

    def create_pdf_note(self, pdf_path):
        if not PDF_SUPPORT: return
        try:
            copi_pdf_path = self.copy_to_copi(pdf_path)
            
            doc = fitz.open(copi_pdf_path)
            total_pages = len(doc)
            doc.close()
            
            new_note = self.add_note(pkg_text=os.path.basename(pdf_path), note_text="", image_path=None, is_gallery=False, is_document=True, doc_type='pdf')
            new_note.is_image_mode = True
            new_note.doc_size = self.current_doc_size
            
            if new_note.text_edit:
                new_note.text_edit.setParent(None)
                new_note.text_edit.deleteLater()
                new_note.text_edit = None
            if not new_note.image_card:
                new_note.image_card = ImageCardWidget(None, new_note, is_gallery=True)
                new_note.main_layout.addWidget(new_note.image_card)
            
            for page_num in range(total_pages):
                new_note.add_sub_item(copi_pdf_path, 'pdf_page', forced_name=f"Sayfa {page_num+1}", page_index=page_num)
            
            self.refresh_layout()
        except Exception as e: QMessageBox.critical(self, "PDF Hatası", f"PDF işlenirken hata oluştu:\n{str(e)}")

    def create_gallery_from_images(self, image_paths):
        if len(self.notes_list) >= self.MAX_NOTES: return
        limit = 200 
        if len(image_paths) > limit: image_paths = image_paths[:limit]
        
        new_note = self.add_note(pkg_text="Belge (Resimler)", note_text="", image_path=None, is_gallery=False, is_document=True, doc_type='image')
        new_note.is_image_mode = True
        new_note.doc_size = self.current_doc_size
        
        for i, file_path in enumerate(image_paths):
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                copi_path = self.copy_to_copi(file_path)
                new_note.add_sub_item(copi_path, 'img')
            else:
                new_note.add_sub_item(file_path, 'txt')
        
        if new_note.text_edit:
            new_note.text_edit.deleteLater()
            new_note.text_edit = None
        new_note.init_components()
        new_note.main_layout.addWidget(new_note.image_card)
        self.refresh_layout()

    def on_gallery_scroll(self, val):
        if not self.expanded_note_widget or not self.expanded_note_widget.is_image_mode: return
        if getattr(self.expanded_note_widget, 'is_document_mode', False): return
        refs = self.expanded_note_widget.item_widgets_refs
        found_idx = 0
        for i, widget in enumerate(refs):
            if widget.geometry().y() + widget.geometry().height() > val:
                found_idx = i
                break
        self.expanded_note_widget.current_page_idx = found_idx
        self.nav_btn.setText(f"#{found_idx + 1}")

    def toggle_auto_scroll(self):
        if self.auto_scroll_active:
            self.auto_scroll_timer.stop()
            self.auto_scroll_active = False
            self.read_mode_btn.setStyleSheet(self.buttonStyle())
        else:
            if not self.expanded_note_widget: return
            self.auto_scroll_timer.start(50)
            self.auto_scroll_active = True
            style = self.buttonStyle().replace("transparent", "#555")
            self.read_mode_btn.setStyleSheet(style)

    def process_auto_scroll(self):
        if not self.expanded_note_widget:
            self.toggle_auto_scroll()
            return
        scroll_bar = None
        if self.expanded_note_widget.active_scroll_area: scroll_bar = self.expanded_note_widget.active_scroll_area.verticalScrollBar()
        elif self.expanded_note_widget.expanded_text_edit: scroll_bar = self.expanded_note_widget.expanded_text_edit.verticalScrollBar()
        if not scroll_bar: return

        self.scroll_accumulator += self.scroll_rate
        if self.scroll_accumulator >= 1.0:
            pixels = int(self.scroll_accumulator)
            self.scroll_accumulator -= pixels
            scroll_bar.setValue(scroll_bar.value() + pixels)
        
        if scroll_bar.value() >= scroll_bar.maximum(): self.toggle_auto_scroll()

    def show_speed_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item { padding: 5px 20px; } QMenu::item:selected { background-color: #555; }")
        for i, speed in enumerate(self.scroll_speeds):
            action = menu.addAction(f"Speed: {speed}")
            action.setCheckable(True)
            if i == self.current_scroll_speed_index: action.setChecked(True)
            action.triggered.connect(lambda checked, idx=i: self.set_scroll_speed(idx))
        menu.exec_(self.scroll_speed_btn.mapToGlobal(QPoint(0, self.scroll_speed_btn.height())))

    def set_scroll_speed(self, index):
        self.current_scroll_speed_index = index
        self.scroll_rate = self.scroll_speeds[index]
        self.scroll_speed_btn.setText(str(self.scroll_rate))
        self.save_settings()

    def show_size_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item { padding: 5px 20px; } QMenu::item:selected { background-color: #555; }")
        sizes = [0.5] + list(range(1, 21))
        
        current_val = self.current_doc_size
        if self.expanded_note_widget and getattr(self.expanded_note_widget, 'is_document_mode', False):
            current_val = self.expanded_note_widget.doc_size

        for val in sizes:
            action = menu.addAction(f"Boyut: {val}")
            action.setCheckable(True)
            if val == current_val: action.setChecked(True)
            action.triggered.connect(lambda checked, v=val: self.set_doc_size(v))
        menu.exec_(self.doc_size_btn.mapToGlobal(QPoint(0, self.doc_size_btn.height())))

    def set_doc_size(self, size):
        self.current_doc_size = size
        self.doc_size_btn.setText(str(size))
        self.save_settings()
        if self.expanded_note_widget and getattr(self.expanded_note_widget, 'is_document_mode', False):
            # Sadece o anki belgenin bağımsız boyutunu günceller ve çizer
            self.expanded_note_widget.doc_size = size
            self.expanded_note_widget.update_document_view()

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Paste): self.paste_from_clipboard()
        super().keyPressEvent(event)

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()
        if mime.hasUrls():
            urls = mime.urls()
            files = [u.toLocalFile() for u in urls if u.isLocalFile()]
            if files: self.create_duplicate_gallery_package(files)
        elif mime.hasText():
            text = mime.text()
            if text:
                formatted_text = text.replace("\n", "<br>")
                new_note = self.add_note(pkg_text="", note_text=formatted_text, image_path=None)
                if new_note: self.update_nav_button_text_mode(new_note)

    def create_duplicate_gallery_package(self, files):
        if len(self.notes_list) >= self.MAX_NOTES: return
        if len(files) > 35: files = files[:35]

        new_files_paths = []
        for f in files:
            try:
                copi_path = self.copy_to_copi(f)
                new_files_paths.append(copi_path)
            except: pass
        if not new_files_paths: return

        new_note = self.add_note(pkg_text="", note_text="", image_path=None, is_gallery=True)
        new_note.is_image_mode = True
        
        for i, fp in enumerate(new_files_paths):
             if fp.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')): new_note.add_sub_item(fp, 'img')
             elif fp.lower().endswith(('.txt', '.txr')): new_note.add_sub_item(fp, 'txt', is_txr=fp.lower().endswith('.txr'))

        if new_note.text_edit: new_note.text_edit.deleteLater(); new_note.text_edit = None
        new_note.init_components()
        new_note.main_layout.addWidget(new_note.image_card)
        self.refresh_layout()

    def buttonStyle(self):
        return "QPushButton { background-color: transparent; color: white; font-size: 14px; font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 5px; } QPushButton:hover { background-color: #444; } QPushButton:pressed { background-color: #666; } QPushButton:disabled { color: #555; border-color: #333; }"

    def add_note(self, pkg_text="", note_text="", image_path=None, is_gallery=False, is_document=False, doc_type=None):
        if len(self.notes_list) >= self.MAX_NOTES: return
        note = NoteWidget(self, pkg_text, note_text, image_path, is_gallery, is_document, doc_type)
        self.notes_list.append(note)
        self.refresh_layout()
        if not pkg_text and not note_text and not image_path: note.pkg_edit.setFocus()
        return note

    def remove_note(self, note_widget):
        if note_widget in self.notes_list:
            self.notes_list.remove(note_widget)
            note_widget.setParent(None)
            note_widget.deleteLater()
            self.refresh_layout()

    def handle_gallery_click(self):
        QDir().mkpath(self.DEFAULT_BASE_DIR)
        
        # Sadece resim formatlarını, .txt ve .txr formatlarını kabul edecek şekilde güncellendi
        file_filter = "Galeri Dosyaları (*.png *.jpg *.jpeg *.bmp *.gif *.txt *.txr);;Resimler (*.png *.jpg *.jpeg *.bmp *.gif);;Metin Dosyaları (*.txt *.txr)"
        files, _ = QFileDialog.getOpenFileNames(self, "Dosyaları Seç", self.DEFAULT_BASE_DIR, file_filter)
        if not files: return
        
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.txt', '.txr')
        filtered_files = [f for f in files if f.lower().endswith(valid_extensions)]
        if not filtered_files: return

        if self.expanded_note_widget and self.expanded_note_widget.is_image_mode:
            current_count = len(self.expanded_note_widget.sub_items)
            available = 35 - current_count
            if len(filtered_files) > available: filtered_files = filtered_files[:available]
            if not filtered_files: return

            for i, file_path in enumerate(filtered_files):
                copi_path = self.copy_to_copi(file_path)
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')): 
                    self.expanded_note_widget.add_sub_item(copi_path, 'img')
                else: 
                    self.expanded_note_widget.add_sub_item(copi_path, 'txt', is_txr=file_path.lower().endswith('.txr'))
            self.expanded_note_widget.refresh_expanded_view()
        else:
            if len(self.notes_list) >= self.MAX_NOTES: return
            if len(filtered_files) > 35: filtered_files = filtered_files[:35]

            new_note = self.add_note(pkg_text="", note_text="", image_path=None, is_gallery=True)
            new_note.is_image_mode = True
            
            for i, file_path in enumerate(filtered_files):
                copi_path = self.copy_to_copi(file_path)
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')): 
                    new_note.add_sub_item(copi_path, 'img')
                else: 
                    new_note.add_sub_item(copi_path, 'txt', is_txr=file_path.lower().endswith('.txr'))
            
            if new_note.text_edit: new_note.text_edit.deleteLater(); new_note.text_edit = None
            new_note.init_components()
            new_note.main_layout.addWidget(new_note.image_card)
            self.refresh_layout()

    def update_toolbar_state(self, is_expanded, note_widget=None):
        if not is_expanded:
            self.add_btn.setEnabled(True)
            self.gallery_btn.setEnabled(True)
            self.belge_btn.setEnabled(True)
            self.tool_delete_btn.setEnabled(False)
            self.tool_copy_btn.setEnabled(False)
            self.tool_min_btn.setEnabled(False)
            self.nav_btn.setEnabled(False) 
            self.nav_btn.setText("#1")
            self.nav_btn.setMinimumWidth(40)
            self.read_mode_btn.setEnabled(False)
            self.scroll_speed_btn.setEnabled(False)
            self.doc_size_btn.setEnabled(False)
            if self.auto_scroll_active: self.toggle_auto_scroll()
        else:
            self.read_mode_btn.setEnabled(True)
            self.scroll_speed_btn.setEnabled(True)
            
            if note_widget:
                if note_widget.is_image_mode:
                    self.add_btn.setEnabled(False)
                    self.gallery_btn.setEnabled(True)
                    self.belge_btn.setEnabled(True)  
                    self.nav_btn.setEnabled(True)
                    self.nav_btn.setText(f"#{note_widget.current_page_idx + 1 if getattr(note_widget, 'is_document_mode', False) else 1}")
                    
                    if getattr(note_widget, 'is_document_mode', False):
                        self.doc_size_btn.setEnabled(True)
                        self.doc_size_btn.setText(str(note_widget.doc_size))
                    else: self.doc_size_btn.setEnabled(False)
                else:
                    self.add_btn.setEnabled(False)
                    self.gallery_btn.setEnabled(False)
                    self.belge_btn.setEnabled(False)
                    self.doc_size_btn.setEnabled(False)
                    self.update_nav_button_text_mode(note_widget)
            
            self.tool_delete_btn.setEnabled(True)
            self.tool_copy_btn.setEnabled(True)
            self.tool_min_btn.setEnabled(True)

    def update_nav_button_text_mode(self, note_widget):
        if not note_widget.is_image_mode:
            text = note_widget.note_text_val
            doc = QTextDocument()
            doc.setHtml(text)
            line_count = doc.blockCount()
            if line_count <= 1 and text: line_count = text.count("<br") + 1
            text_str = f"#{line_count}"
            self.nav_btn.setText(text_str)
            self.nav_btn.setEnabled(False) 
            fm = QFontMetrics(self.nav_btn.font())
            width = fm.width(text_str) + 30
            self.nav_btn.setMinimumWidth(max(40, width))

    def show_nav_menu(self):
        if not self.expanded_note_widget or not self.expanded_note_widget.is_image_mode: return
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; font-size: 14px; } QMenu::item { padding: 8px 25px; } QMenu::item:selected { background-color: #555; }")
        menu.setFixedHeight(min(600, 35 * len(self.expanded_note_widget.sub_items) + 20))
        for idx in range(len(self.expanded_note_widget.sub_items)):
            action = menu.addAction(f"#{idx+1}")
            action.triggered.connect(lambda checked, i=idx: self.scroll_to_item(i))
        menu.exec_(self.nav_btn.mapToGlobal(QPoint(0, self.nav_btn.height())))

    def scroll_to_item(self, index):
        if not self.expanded_note_widget: return
        QApplication.processEvents()
        try:
            if getattr(self.expanded_note_widget, 'is_document_mode', False):
                self.expanded_note_widget.current_page_idx = index
                self.expanded_note_widget.update_document_view()
            else:
                if index < len(self.expanded_note_widget.item_widgets_refs):
                    target_widget = self.expanded_note_widget.item_widgets_refs[index]
                    if self.expanded_note_widget.active_scroll_area:
                        self.expanded_note_widget.active_scroll_area.ensureWidgetVisible(target_widget)
                        self.expanded_note_widget.current_page_idx = index # Kaldığı sayfayı koruması için
                        self.nav_btn.setText(f"#{index + 1}")
        except: pass

    def delete_active_package(self):
        if self.expanded_note_widget:
            target_note = self.expanded_note_widget
            self.collapse_note(target_note)
            self.remove_note(target_note)

    def expand_note(self, note_widget, maintain_scroll=False, target_item_index=None, show_progress=False):
        self.setUpdatesEnabled(False)
        try:
            current_scroll = 0
            if maintain_scroll and self.expanded_note_widget:
                 try:
                     if hasattr(self.expanded_note_widget, 'active_scroll_area'):
                         area = self.expanded_note_widget.active_scroll_area
                         if area and not area.isHidden(): current_scroll = area.verticalScrollBar().value()
                 except RuntimeError: current_scroll = 0
            
            if self.expanded_note_widget:
                 old_widget = self.expanded_note_widget
                 try:
                    old_widget.update_text_from_expanded()
                    old_widget.is_expanded = False
                    old_widget.setFixedHeight(220)
                 except RuntimeError: pass

                 while self.expanded_layout.count():
                     child = self.expanded_layout.takeAt(0)
                     w = child.widget()
                     if w:
                         # Çökmeleri engellemek için önbellekteki araç silinmez (deleteLater değil), saklanır
                         w.setParent(old_widget)
                         w.hide()
                 self.expanded_note_widget = None

            self.expanded_note_widget = note_widget
            content_widget = note_widget.get_or_create_expanded_content(current_scroll_val=current_scroll, show_progress=show_progress, doc_size=self.current_doc_size)
            self.expanded_layout.addWidget(content_widget)
            content_widget.show()
            
            self.content_stack.setCurrentIndex(1)
            self.update_toolbar_state(True, note_widget)

            try: self.tool_delete_btn.clicked.disconnect()
            except: pass
            try: self.tool_copy_btn.clicked.disconnect()
            except: pass
            try: self.tool_min_btn.clicked.disconnect()
            except: pass

            self.tool_delete_btn.clicked.connect(self.delete_active_package)
            self.tool_copy_btn.clicked.connect(note_widget.copy_to_clipboard)
            self.tool_min_btn.clicked.connect(lambda: self.collapse_note(note_widget))

            if target_item_index is not None and note_widget.is_image_mode:
                 QTimer.singleShot(100, lambda: self.scroll_to_item(target_item_index))
        finally:
            self.setUpdatesEnabled(True)

    def collapse_note(self, note_widget):
        if self.auto_scroll_active: self.toggle_auto_scroll()
        try: self.tool_delete_btn.clicked.disconnect()
        except: pass
        try: self.tool_copy_btn.clicked.disconnect()
        except: pass
        try: self.tool_min_btn.clicked.disconnect()
        except: pass

        try: note_widget.update_text_from_expanded()
        except RuntimeError: pass
        
        while self.expanded_layout.count():
            child = self.expanded_layout.takeAt(0)
            w = child.widget()
            if w:
                w.setParent(note_widget)
                w.hide()
            
        self.expanded_note_widget = None
        self.content_stack.setCurrentIndex(0)
        self.refresh_layout()
        self.update_toolbar_state(False)

    def refresh_layout(self):
        if self.content_stack.currentIndex() == 1: return
        for note in self.notes_list: note.setParent(None)
        for idx, note in enumerate(self.notes_list):
            note.set_column_mode()
            mod = idx % 3
            if mod == 0: self.col1_layout.addWidget(note)
            elif mod == 1: self.col2_layout.addWidget(note)
            else: self.col3_layout.addWidget(note)
            note.setFixedHeight(220)
            note.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            note.show()

    def clear_workspace(self):
        if self.expanded_note_widget: self.collapse_note(self.expanded_note_widget)
        for note in self.notes_list: note.setParent(None); note.deleteLater()
        self.notes_list.clear()
        self.clear_copi_folder()

    def load_copya(self, path=None):
        if path is None: 
            QDir().mkpath(self.DEFAULT_BASE_DIR)
            path, _ = QFileDialog.getOpenFileName(self, "Open", self.DEFAULT_BASE_DIR, "Copya Files (*.copya)")
            
        if not path: return
        
        # Yeni bir proje yüklenirken mevcut olan copi klasörü temizlenir.
        self.clear_workspace()
        
        try:
            with zipfile.ZipFile(path, 'r') as zipf:
                zipf.extractall(self.COPI_DIR)
                
            data_file = os.path.join(self.COPI_DIR, 'data.json')
            with open(data_file, 'r', encoding='utf-8') as f: data = json.load(f)
            
            notes_data = data.get('notes', [])
            total_notes = len(notes_data)
            
            # Sadece yükleme esnasında çıkan ilerleme çubuğu
            progress = QProgressDialog("Proje Yükleniyor...", "İptal", 0, total_notes, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0) 
            progress.show()
            
            for idx, item in enumerate(notes_data):
                if progress.wasCanceled(): break
                progress.setValue(idx)
                QApplication.processEvents()

                if len(self.notes_list) >= self.MAX_NOTES: break
                pkg = item.get('package', '')
                note_content = item.get('note', '')
                gallery_data = item.get('gallery_data', [])
                doc_size = item.get('doc_size', 15)
                is_doc = item.get('is_document_mode', False)
                doc_type = item.get('doc_type', None)
                
                if gallery_data:
                    new_note = self.add_note(pkg, "", None, is_gallery=(not is_doc), is_document=is_doc, doc_type=doc_type)
                    new_note.is_image_mode = True
                    new_note.doc_size = doc_size # Aktarılırken eski bağımsız boyut yüklenir
                    new_note.sub_items = []
                    
                    if new_note.text_edit: 
                        new_note.text_edit.setParent(None)
                        new_note.text_edit.deleteLater()
                        new_note.text_edit = None
                    
                    if not new_note.image_card:
                         new_note.image_card = ImageCardWidget(None, new_note, is_gallery=True)
                         new_note.main_layout.addWidget(new_note.image_card)

                    for g_item in gallery_data:
                        file_name = g_item.get('name', None)
                        is_txr_item = g_item.get('is_txr', False)
                        if g_item['type'] == 'img':
                            real_path = os.path.join(self.COPI_DIR, g_item.get('filename', ''))
                            new_note.add_sub_item(real_path, 'img', forced_name=file_name)
                        elif g_item['type'] == 'txt':
                            new_note.add_sub_item(g_item['data'], 'txt', forced_name=file_name, is_raw_content=True, is_txr=is_txr_item)
                        elif g_item['type'] == 'pdf_page':
                            real_path = os.path.join(self.COPI_DIR, g_item.get('filename', ''))
                            new_note.add_sub_item(real_path, 'pdf_page', forced_name=file_name, page_index=g_item.get('page_index', 0))
                    
                    if new_note.image_card: new_note.image_card.update()
                else: self.add_note(pkg, note_content, None)

            progress.setValue(total_notes)
            self.current_file_path = path
            self.refresh_layout()
        except Exception as e: QMessageBox.critical(self, "Error", f"Could not load file:\n{e}")

    def quick_save(self):
        if self.current_file_path: self.save_to_path(self.current_file_path)
        else: self.export_copya()

    def export_copya(self):
        QDir().mkpath(self.DEFAULT_BASE_DIR)
        path, _ = QFileDialog.getSaveFileName(self, "Save", os.path.join(self.DEFAULT_BASE_DIR, "untitled.copya"), "Copya Files (*.copya)")
        if not path: return
        if not path.endswith('.copya'): path += '.copya'
        self.save_to_path(path)

    def save_to_path(self, path):
        if self.expanded_note_widget: self.expanded_note_widget.update_text_from_expanded()
        
        notes_data = []
        for note in self.notes_list: notes_data.append(note.to_dict())
        
        data_file = os.path.join(self.COPI_DIR, 'data.json')
        try:
            with open(data_file, 'w', encoding='utf-8') as f: json.dump({'notes': notes_data}, f, ensure_ascii=False, indent=2)
            
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.COPI_DIR):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, self.COPI_DIR)
                        zipf.write(file_path, arcname)
                        
            self.current_file_path = path
            # EXPORT İŞLEMİNDE ÇALIŞMA ALANI SİLİNMESİ (copi) KALDIRILDI, DOSYALAR KORUNUYOR.
            QMessageBox.information(self, "Başarılı", "Proje başarıyla arşivlenerek dışa aktarıldı.\nDosyalar çalışma alanında korunuyor.")
        except Exception as e: QMessageBox.critical(self, "Error", f"Could not save:\n{e}")

    def triggerCoreSwitcher(self):
        if self.core_window_ref and hasattr(self.core_window_ref, 'showSwitcher'):
            self.core_window_ref.showSwitcher()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
