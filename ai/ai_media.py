# Kavram AI Editörü — ses/görsel/video/dosya bileşenleri
# Kavram 2.2.2 | GNU GPL v3 veya üstü (ayrıntı: ai.py başlığı ve /Kavram/License/GPLv3.txt)

import os
import random

from PyQt5.QtCore import QRect, QUrl, Qt
from PyQt5.QtGui import QColor, QDesktopServices, QPainter, QPixmap
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout

from ai_common import (
    QMediaContent, QMediaPlayer, QT_MULTIMEDIA_AVAILABLE, SVG_FILE_ICON, SVG_IMAGE_ICON,
    SVG_PAUSE_ICON, SVG_PLAY_ICON, create_svg_icon
)


class WaveformSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.setStyleSheet("""
            QSlider::groove:horizontal { background: transparent; height: 30px; }
            QSlider::handle:horizontal { background: #ffffff; width: 4px; margin: -3px 0; border-radius: 2px; }
        """)
        self.setCursor(Qt.PointingHandCursor)
        self.bars = [random.randint(4, 20) for _ in range(80)]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        bar_width = 2
        spacing = 1
        total_bars = rect.width() // (bar_width + spacing)
        progress_ratio = 0
        if self.maximum() > 0:
            progress_ratio = self.value() / self.maximum()
        for i in range(total_bars):
            x = i * (bar_width + spacing)
            h = self.bars[i % len(self.bars)]
            y = (rect.height() - h) // 2
            bar_rect = QRect(x, y, bar_width, h)
            if (x / rect.width()) <= progress_ratio:
                painter.fillRect(bar_rect, QColor("#ffffff"))
            else:
                painter.fillRect(bar_rect, QColor("#555555"))
        super().paintEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            val = self.minimum() + ((self.maximum() - self.minimum()) * event.x()) / self.width()
            self.setValue(int(val))
            self.sliderMoved.emit(int(val))
        else:
            super().mousePressEvent(event)


class AudioPlayerWidget(QFrame):
    def __init__(self, filepath, parent_window, context_source=None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.parent_window = parent_window
        self.context_source = context_source
        self.is_playing = False
        self.initUI()
        self.player = None
        if QT_MULTIMEDIA_AVAILABLE:
            self.player = QMediaPlayer(None, QMediaPlayer.StreamPlayback)
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(filepath)))
            self.player.positionChanged.connect(self.update_position)
            self.player.durationChanged.connect(self.update_duration)
            self.player.stateChanged.connect(self.state_changed)

    def initUI(self):
        self.setStyleSheet("""
            AudioPlayerWidget {
                background-color: #1e1e1e;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                margin-top: 3px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        self.btn_play = QPushButton()
        self.btn_play.setIcon(create_svg_icon(SVG_PLAY_ICON, 18, "#ffffff"))
        self.btn_play.setFixedSize(30, 30)
        self.btn_play.setStyleSheet("""
            QPushButton { background-color: #2b2b2b; border: 1px solid #444; border-radius: 15px; }
            QPushButton:hover { background-color: #3b3b3b; }
        """)
        self.btn_play.clicked.connect(self.toggle_playback)
        self.slider = WaveformSlider()
        self.slider.sliderMoved.connect(self.set_position)
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: #888; font-size: 11px; font-weight: bold;")
        layout.addWidget(self.btn_play)
        layout.addWidget(self.slider, stretch=1)
        layout.addWidget(self.time_label)

    def toggle_playback(self):
        if not QT_MULTIMEDIA_AVAILABLE or not self.player: return
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            if hasattr(self.parent_window, "pause_all_audio_except"):
                self.parent_window.pause_all_audio_except(self)
            if hasattr(self.parent_window, "last_active_player"):
                self.parent_window.last_active_player = self
            self.player.play()

    def state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.btn_play.setIcon(create_svg_icon(SVG_PAUSE_ICON, 18, "#ffffff"))
        else:
            self.btn_play.setIcon(create_svg_icon(SVG_PLAY_ICON, 18, "#ffffff"))

    def update_position(self, position):
        self.slider.setValue(position)
        self.update_time_label()

    def update_duration(self, duration):
        self.slider.setRange(0, duration)
        self.update_time_label()

    def set_position(self, position):
        if QT_MULTIMEDIA_AVAILABLE and self.player:
            self.player.setPosition(position)

    def update_time_label(self):
        if not QT_MULTIMEDIA_AVAILABLE or not self.player: return
        pos = self.player.position() // 1000
        dur = self.player.duration() // 1000
        pos_str = f"{pos // 60:02d}:{pos % 60:02d}"
        dur_str = f"{dur // 60:02d}:{dur % 60:02d}"
        self.time_label.setText(f"{pos_str} / {dur_str}")

    def closeEvent(self, event):
        if self.player:
            self.player.stop()
            self.player.setMedia(QMediaContent())
            self.player.deleteLater()
            self.player = None
        super().closeEvent(event)


class ImageThumbnailWidget(QFrame):
    def __init__(self, filepath, parent_window, context_source=None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.parent_window = parent_window
        self.context_source = context_source
        self.setFixedSize(100, 100)
        self.setStyleSheet("background-color: #1a1a1a; border-radius: 6px; border: 1px solid #3a3a3a; margin-top: 3px;")
        self.setCursor(Qt.PointingHandCursor)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(filepath)
        if not pixmap.isNull():
            self.label.setPixmap(pixmap.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.label.setPixmap(create_svg_icon(SVG_IMAGE_ICON, 40, "#555").pixmap(40, 40))
        self.layout.addWidget(self.label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent_window.show_media_overlay(self.filepath, is_video=False, context_source=self.context_source)
        else:
            super().mousePressEvent(event)


class VideoThumbnailWidget(QFrame):
    def __init__(self, filepath, parent_window, context_source=None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.parent_window = parent_window
        self.context_source = context_source
        self.setFixedSize(100, 100)
        self.setStyleSheet("background-color: #0a0a0a; border-radius: 6px; border: 1px solid #3a3a3a; margin-top: 3px;")
        self.setCursor(Qt.PointingHandCursor)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setPixmap(create_svg_icon(SVG_PLAY_ICON, 40, "#ffffff").pixmap(40, 40))
        self.layout.addWidget(self.label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent_window.show_media_overlay(self.filepath, is_video=True, context_source=self.context_source)
        else:
            super().mousePressEvent(event)


class FileAttachmentWidget(QFrame):
    def __init__(self, filepath, parent_window, context_source=None, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.parent_window = parent_window
        self.context_source = context_source
        self.setStyleSheet("""
            FileAttachmentWidget {
                background-color: #1a1a1a;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                margin-top: 3px;
            }
            FileAttachmentWidget:hover {
                background-color: #252525;
                border-color: #555;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(create_svg_icon(SVG_FILE_ICON, 20, "#ffffff").pixmap(20, 20))
        
        self.name_lbl = QLabel(os.path.basename(filepath))
        self.name_lbl.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold;")
        self.name_lbl.setWordWrap(False)
        
        layout.addWidget(self.icon_lbl)
        layout.addWidget(self.name_lbl, stretch=1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.filepath))
        else:
            super().mousePressEvent(event)
