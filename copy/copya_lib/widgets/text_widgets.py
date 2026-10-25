"""Metin alanları: otomatik yükseklikli görüntüleyici ve düzenlenebilir not alanı."""
import logging
import re

from PyQt5.QtCore import QPoint, Qt, QUrl
from PyQt5.QtGui import QFont, QImage, QPixmap, QTextCursor, QTextDocument
from PyQt5.QtWidgets import (QAction, QFrame, QHBoxLayout, QTextEdit, QToolButton,
                             QWidget)

from .viewers import ImagePreviewDialog

log = logging.getLogger("copya.text")

_CENTER_RE = re.compile(r'^\s*<center>(.*)</center>\s*$', re.IGNORECASE)


class AutoResizingTextEdit(QTextEdit):
    """.txt / .txr içeriğini gösterir. .txr ise <center> etiketlerini korur.

    `on_change(yeni_içerik)` her düzenlemede çağrılır (düzenleme modunda)."""

    def __init__(self, text: str, is_txr: bool = False, on_change=None, parent=None):
        super().__init__(parent)
        self.is_txr = is_txr
        self.on_change = on_change
        self.setReadOnly(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        self.setStyleSheet("""
            QTextEdit { background: #111; color: #ddd; border: 1px solid #444; padding: 10px; border-radius: 4px; }
        """)
        if is_txr or "<center>" in text:
            self.set_clean_html_content(text)
        else:
            self.setPlainText(text)
        self.adjust_height()
        self.textChanged.connect(self.on_text_changed)

    def set_clean_html_content(self, html_text: str) -> None:
        self.blockSignals(True)
        self.clear()
        cursor = self.textCursor()
        for i, line in enumerate(html_text.split('\n')):
            centered = False
            text = line
            m = _CENTER_RE.match(line)
            if m:
                centered, text = True, m.group(1)
            if i > 0:
                cursor.insertBlock()
            cursor.insertText(text)
            fmt = cursor.blockFormat()
            fmt.setAlignment(Qt.AlignCenter if centered else Qt.AlignLeft)
            cursor.setBlockFormat(fmt)
        self.blockSignals(False)

    def get_clean_html_content(self) -> str:
        lines = []
        block = self.document().begin()
        while block.isValid():
            text = block.text()
            if block.blockFormat().alignment() & Qt.AlignCenter:
                lines.append(f"<center>{text}</center>")
            else:
                lines.append(text)
            block = block.next()
        return "\n".join(lines)

    def on_text_changed(self):
        self.adjust_height()
        if self.on_change is not None:
            self.on_change(self.get_clean_html_content() if self.is_txr else self.toPlainText())

    def adjust_height(self):
        self.setFixedHeight(int(self.document().size().height() + 20))

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


class ImageOverlayTools(QWidget):
    """Metin içindeki resmin üzerinde beliren Sil / Büyüt araç çubuğu."""

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
    """Metin notu düzenleyicisi. Üzerine gelinen gömülü resim için Sil/Büyüt gösterir."""

    def __init__(self, parent_note=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_note = parent_note
        self.setMouseTracking(True)
        self.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        self.overlay = ImageOverlayTools(self, on_expand=self.expand_current_image,
                                         on_delete=self.delete_current_image)
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
            self.overlay.move(self.mapToGlobal(rect.topLeft() + QPoint(5, 5)))
            self.overlay.show()
            self.overlay.raise_()
        elif not self.overlay.geometry().contains(self.mapToGlobal(event.pos())):
            self.overlay.hide()
        super().mouseMoveEvent(event)

    def delete_current_image(self):
        if self.current_cursor_position == -1:
            return
        c = self.textCursor()
        c.setPosition(self.current_cursor_position)
        c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
        if not c.charFormat().isImageFormat():
            c.setPosition(self.current_cursor_position)
            c.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
        if c.charFormat().isImageFormat():
            c.removeSelectedText()
            self.overlay.hide()

    def expand_current_image(self):
        if not self.current_image_name:
            return
        resource = self.document().resource(QTextDocument.ImageResource,
                                            QUrl(self.current_image_name))
        pixmap = QPixmap()
        if isinstance(resource, QPixmap):
            pixmap = resource
        elif isinstance(resource, QImage):
            pixmap = QPixmap.fromImage(resource)
        if pixmap.isNull():
            return
        ImagePreviewDialog(pixmap, self).exec_()
