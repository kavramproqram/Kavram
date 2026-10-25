"""Resim ve sayfa görüntüleyicileri (yakınlaştırma, kaydırma, kart)."""
from PyQt5.QtCore import QPoint, QRectF, Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QPixmap
from PyQt5.QtWidgets import (QApplication, QDialog, QHBoxLayout, QPushButton,
                             QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from .. import config
from ..renderers import trim_pixmap_by_alpha
from ..theme import PREVIEW_CLOSE_STYLE


class DocumentImageWidget(QWidget):
    """Belgede tek sayfayı, belge boyutu oranında çizer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = QPixmap()
        self.doc_size = config.DEFAULT_DOC_SIZE
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_pixmap(self, pixmap: QPixmap, doc_size) -> None:
        self.pixmap = pixmap
        self.doc_size = doc_size
        self.update_size()
        self.update()

    def update_size(self) -> None:
        if self.pixmap.isNull():
            return
        scroll = self.get_parent_scroll()
        if scroll:
            view_w = scroll.viewport().width() - 40
        else:
            view_w = self.parentWidget().width() if self.parentWidget() else 800
        if view_w <= 0:
            view_w = 800
        img_w, img_h = self.pixmap.width(), self.pixmap.height()
        if img_w == 0:
            return
        scale = (view_w * self.doc_size / config.DEFAULT_DOC_SIZE) / img_w
        self.setFixedSize(int(img_w * scale), int(img_h * scale))

    def get_parent_scroll(self):
        p = self.parentWidget()
        while p:
            if isinstance(p, QScrollArea):
                return p
            p = p.parentWidget()
        return None

    def paintEvent(self, event):
        if self.pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(self.rect(), self.pixmap)


class ZoomableImageWidget(QWidget):
    """Orta tuşla kaydırma, tekerlekle yakınlaştırma, sağ tıkla sığdırma."""

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.pixmap = trim_pixmap_by_alpha(pixmap)
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
        if self.pixmap.isNull():
            return

        scaled_w = self.pixmap.width() * self.scale_factor
        scaled_h = self.pixmap.height() * self.scale_factor
        draw_x = self.width() / 2 - scaled_w / 2 + self.offset.x()
        draw_y = self.height() / 2 - scaled_h / 2 + self.offset.y()
        if (draw_x + scaled_w < 0 or draw_x > self.width()
                or draw_y + scaled_h < 0 or draw_y > self.height()):
            return
        painter.drawPixmap(QRectF(draw_x, draw_y, scaled_w, scaled_h),
                           self.pixmap, QRectF(self.pixmap.rect()))

    def wheelEvent(self, event):
        if self.pixmap.isNull():
            return
        vec = event.pos() - QPoint(self.width() // 2, self.height() // 2)
        zoom_change = 1.1 if event.angleDelta().y() > 0 else 0.9
        new_scale = min(50.0, max(0.05, self.scale_factor * zoom_change))
        factor = new_scale / self.scale_factor
        self.offset = self.offset * factor + vec * (1 - factor)
        self.scale_factor = new_scale
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.fit_logic()
        elif event.button() == Qt.MiddleButton:
            self.panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.panning:
            self.offset += event.pos() - self.last_mouse_pos
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
        if self.pixmap.isNull() or self.width() == 0:
            return
        scale_w = self.width() / self.pixmap.width()
        viewport_h = 1000.0
        screen = QApplication.primaryScreen()
        if screen:
            viewport_h = screen.size().height() * 0.8
        parent = self.parentWidget()
        while parent:
            if isinstance(parent, QScrollArea):
                viewport_h = parent.viewport().height()
                break
            parent = parent.parentWidget()

        scale_h = viewport_h / self.pixmap.height()
        self.scale_factor = min(1.0, scale_w, scale_h)
        self.offset = QPoint(0, 0)
        new_height = int(self.pixmap.height() * self.scale_factor)
        if abs(self.height() - new_height) > 2:
            self.setFixedHeight(new_height)
        self.update()


class ImageCardWidget(QWidget):
    """Galeri/belge kartının gövdesi (koyu zemin ve alt çizgi)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(False)
        self.setFixedHeight(config.CARD_HEIGHT)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#000000"))
        painter.setPen(QColor("#444"))
        r = self.rect()
        painter.drawLine(0, r.height() - 1, r.width(), r.height() - 1)


class ImagePreviewDialog(QDialog):
    """Bir resmi/sayfayı tam ekran ve yakınlaştırılabilir gösterir."""

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Preview")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.showMaximized()
        self.setStyleSheet("background: black;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 10, 0)
        close_btn = QPushButton("X")
        close_btn.setStyleSheet(PREVIEW_CLOSE_STYLE)
        close_btn.setFixedSize(40, 40)
        close_btn.clicked.connect(self.close)
        top_layout.addStretch()
        top_layout.addWidget(close_btn)
        layout.addWidget(top_bar)

        zoom = ZoomableImageWidget(pixmap)
        layout.addWidget(zoom)
        QTimer.singleShot(10, zoom.fit_logic)
