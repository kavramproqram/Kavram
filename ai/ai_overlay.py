# Kavram AI Editörü — tam ekran medya katmanı
# Kavram 2.2.2 | GNU GPL v3 veya üstü (ayrıntı: ai.py başlığı ve /Kavram/License/GPLv3.txt)

import os
import time

from PyQt5.QtCore import QTimer, QUrl, Qt
from PyQt5.QtGui import QColor, QFont, QMouseEvent, QPainter, QPixmap, QWheelEvent
from PyQt5.QtWidgets import (
    QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QPushButton,
    QSlider, QVBoxLayout, QWidget
)

from ai_common import (
    QGraphicsVideoItem, QMediaContent, QMediaPlayer, QT_MULTIMEDIA_AVAILABLE,
    SVG_PAUSE_ICON, SVG_PLAY_ICON, create_svg_icon
)


class MediaGraphicsView(QGraphicsView):
    def __init__(self, parent_overlay):
        super().__init__(parent_overlay)
        self.parent_overlay = parent_overlay
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet("background-color: black; border: none;")
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

    def wheelEvent(self, event: QWheelEvent):
        self.parent_overlay.handle_wheel(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.parent_overlay.close_overlay()
            event.accept()
        elif event.button() == Qt.MidButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            fake_event = QMouseEvent(event.type(), event.pos(), Qt.LeftButton, Qt.LeftButton, event.modifiers())
            super().mousePressEvent(fake_event)
        elif event.button() == Qt.RightButton:
            self.parent_overlay.reset_view_transform()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MidButton:
            self.setDragMode(QGraphicsView.NoDrag)
            fake_event = QMouseEvent(event.type(), event.pos(), Qt.LeftButton, Qt.LeftButton, event.modifiers())
            super().mouseReleaseEvent(fake_event)
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        self.parent_overlay.keyPressEvent(event)


class MediaOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: black;")
        self.setFocusPolicy(Qt.StrongFocus)
        
        self.current_filepath = None
        self.context_source = None
        
        self.nav_timer = QTimer(self)
        self.nav_timer.setSingleShot(True)
        self.nav_timer.timeout.connect(self._apply_media_switch)
        self.playlist_data = []
        self.current_playlist_idx = -1
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.view = MediaGraphicsView(self)
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.layout.addWidget(self.view)
        
        self.control_widget = QWidget()
        self.control_widget.setFixedHeight(45)
        self.control_widget.setStyleSheet("background-color: #0f0f0f; border-top: 1px solid #2a2a2a;")
        self.control_widget.hide()
        
        control_layout = QHBoxLayout(self.control_widget)
        control_layout.setContentsMargins(15, 0, 15, 0)
        control_layout.setSpacing(15)
        
        self.play_btn = QPushButton()
        self.play_btn.setIcon(create_svg_icon(SVG_PLAY_ICON, 24, "#ffffff"))
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.setStyleSheet("QPushButton { background-color: #333; border-radius: 4px; border: 1px solid #444; } QPushButton:hover { background-color: #444; }")
        self.play_btn.setFocusPolicy(Qt.NoFocus)
        self.play_btn.clicked.connect(self.toggle_video_playback)
        
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setCursor(Qt.PointingHandCursor)
        self.position_slider.setStyleSheet("QSlider::groove:horizontal { background: #333; height: 8px; border-radius: 4px; } QSlider::sub-page:horizontal { background: #888; border-radius: 4px; } QSlider::handle:horizontal { background: #fff; width: 16px; margin: -4px 0; border-radius: 8px; }")
        self.position_slider.setFocusPolicy(Qt.NoFocus)
        self.position_slider.sliderMoved.connect(self.set_video_position)
        
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet("color: white; font-size: 13px; font-weight: bold; border: 1px solid #555; padding: 4px 8px; border-radius: 4px; background-color: #222;")
        
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.position_slider, stretch=1)
        control_layout.addWidget(self.time_label)
        
        self.layout.addWidget(self.control_widget)
        
        self.current_item = None
        self.video_item = None
        self.has_paused_initial = False
        self.is_video = False
        
        self.player = None
        if QT_MULTIMEDIA_AVAILABLE:
            self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
            self.player.positionChanged.connect(self.update_video_position)
            self.player.durationChanged.connect(self.update_video_duration)
            self.player.stateChanged.connect(self.update_video_controls)
            self.player.stateChanged.connect(self._initial_pause)
            
        self.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(50, self.reset_view_transform)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, self.reset_view_transform)

    def set_context(self, current_filepath, context_source):
        self.current_filepath = current_filepath
        self.context_source = context_source
        self.build_playlist()

    def build_playlist(self):
        self.playlist_data = []
        self.current_playlist_idx = -1
        
        if hasattr(self.context_source, 'media_files'):
            media_list = self.context_source.media_files
        elif isinstance(self.context_source, list):
            media_list = self.context_source
        else:
            return

        parent_win = self.parent() if hasattr(self, 'parent') else None
        if not parent_win: return
        temp_dir = parent_win.temp_dir

        for mf in media_list:
            if mf['type'] in ('IMAGE', 'VIDEO'):
                full_path = os.path.join(temp_dir, mf['file'])
                self.playlist_data.append({
                    'filepath': full_path,
                    'is_video': mf['type'] == 'VIDEO'
                })

        for i, item in enumerate(self.playlist_data):
            if os.path.abspath(item['filepath']) == os.path.abspath(self.current_filepath):
                self.current_playlist_idx = i
                break

    def _initial_pause(self, state):
        if state == QMediaPlayer.PlayingState and not self.has_paused_initial:
            self.has_paused_initial = True
            QTimer.singleShot(100, self.player.pause)

    def set_media(self, filepath, is_video):
        self.scene.clear()
        self.is_video = is_video
        self.control_widget.hide()
        
        if self.player:
            self.player.stop()
            self.player.setVideoOutput(None)
            self.player.setMedia(QMediaContent())
        
        self.video_item = None
        self.current_item = None
        
        abs_filepath = os.path.abspath(filepath)
        
        if not os.path.exists(abs_filepath):
            fallback_dir = self.parent().temp_dir if hasattr(self.parent(), 'temp_dir') else ""
            fallback_path = os.path.join(fallback_dir, os.path.basename(filepath))
            if os.path.exists(fallback_path):
                abs_filepath = os.path.abspath(fallback_path)
            else:
                self.scene.clear()
                text_item = self.scene.addText(f"Hata: Kaynak dosya bulunamadı!\n{os.path.basename(filepath)}", QFont("Arial", 16))
                text_item.setDefaultTextColor(QColor("red"))
                self.current_item = text_item
                self.view.setSceneRect(0, 0, 400, 300)
                self.reset_view_transform()
                self.show()
                self.raise_()
                self.setFocus()
                return

        if is_video and QT_MULTIMEDIA_AVAILABLE and QGraphicsVideoItem is not None:
            self.video_item = QGraphicsVideoItem()
            self.video_item.nativeSizeChanged.connect(self._video_size_changed)
            self.scene.addItem(self.video_item)
            
            self.player.setVideoOutput(self.video_item)
            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(abs_filepath)))
            self.current_item = self.video_item
            
            self.has_paused_initial = False
            self.player.play()
            self.control_widget.show()
        else:
            pixmap = QPixmap(abs_filepath)
            if pixmap.isNull():
                self.scene.clear()
                text_item = self.scene.addText(f"Görsel yüklenemedi veya desteklenmeyen format!\n{os.path.basename(filepath)}", QFont("Arial", 16))
                text_item.setDefaultTextColor(QColor("orange"))
                self.current_item = text_item
                self.view.setSceneRect(0, 0, 400, 300)
                self.reset_view_transform()
            else:
                item = QGraphicsPixmapItem(pixmap)
                self.scene.addItem(item)
                self.current_item = item
                self.view.setSceneRect(0, 0, pixmap.width(), pixmap.height())
                self.reset_view_transform()
        
        self.show()
        self.raise_()
        self.setFocus()
        
        QTimer.singleShot(50, self.reset_view_transform)

    def _video_size_changed(self, size):
        if self.current_item == self.video_item and size.isValid():
            self.video_item.setSize(size)
            self.view.setSceneRect(0, 0, size.width(), size.height())
            self.reset_view_transform()

    def reset_view_transform(self):
        if self.current_item:
            try:
                self.view.resetTransform()
                self.view.fitInView(self.current_item, Qt.KeepAspectRatio)
            except RuntimeError:
                pass

    def handle_wheel(self, event: QWheelEvent):
        if self.current_item is None: return
        factor = 1.15 if event.angleDelta().y() > 0 else 0.85
        self.view.scale(factor, factor)
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close_overlay()
        elif event.key() == Qt.Key_Space and self.is_video and self.player:
            self.toggle_video_playback()
            event.accept()
        elif self.is_video and self.player and event.key() in (Qt.Key_Left, Qt.Key_Right):
            if self.player.state() != QMediaPlayer.PlayingState:
                step = 33  
                current_pos = self.player.position()
                new_pos = max(0, current_pos - step) if event.key() == Qt.Key_Left else min(self.player.duration(), current_pos + step)
                self.player.setPosition(new_pos)
                if self.player.duration() > 0:
                    self.position_slider.blockSignals(True)
                    self.position_slider.setValue(int(new_pos))
                    self.position_slider.blockSignals(False)
                self.update_time_label()
                event.accept()
            else:
                super().keyPressEvent(event)
        elif event.key() in (Qt.Key_Up, Qt.Key_Down):
            current_time = time.time()
            if not hasattr(self, 'last_nav_time'):
                self.last_nav_time = 0
                
            if event.isAutoRepeat() and (current_time - self.last_nav_time) < 0.25:
                event.accept()
                return
                
            self.last_nav_time = current_time

            if self.context_source:
                self.navigate_media(1 if event.key() == Qt.Key_Down else -1)
                event.accept()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def navigate_media(self, direction):
        if not self.playlist_data:
            self.build_playlist()
            
        if not self.playlist_data: return
        
        self.current_playlist_idx = (self.current_playlist_idx + direction) % len(self.playlist_data)
        
        if self.player:
            self.player.stop()
            self.player.setVideoOutput(None)
            self.player.setMedia(QMediaContent())
            
        self.video_item = None
        self.current_item = None
        self.scene.clear()
        self.control_widget.hide()
        
        self.nav_timer.start(200)

    def _apply_media_switch(self):
        if 0 <= self.current_playlist_idx < len(self.playlist_data):
            next_item = self.playlist_data[self.current_playlist_idx]
            self.current_filepath = next_item['filepath']
            self.set_media(next_item['filepath'], next_item['is_video'])

    def toggle_video_playback(self):
        if self.player and self.is_video:
            if self.player.state() == QMediaPlayer.PlayingState:
                self.player.pause()
            else:
                self.player.play()

    def update_video_position(self, position):
        if self.player and self.player.duration() > 0:
            self.position_slider.blockSignals(True)
            self.position_slider.setValue(position)
            self.position_slider.blockSignals(False)
            self.update_time_label()

    def update_video_duration(self, duration):
        if duration > 0:
            self.position_slider.setRange(0, duration)
            self.update_time_label()

    def update_video_controls(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setIcon(create_svg_icon(SVG_PAUSE_ICON, 24, "#ffffff"))
        else:
            self.play_btn.setIcon(create_svg_icon(SVG_PLAY_ICON, 24, "#ffffff"))

    def set_video_position(self, value):
        if self.player: self.player.setPosition(value)

    def update_time_label(self):
        if self.player:
            pos = self.player.position() // 1000
            dur = self.player.duration() // 1000
            self.time_label.setText(f"{pos // 60:02d}:{pos % 60:02d} / {dur // 60:02d}:{dur % 60:02d}")

    def close_overlay(self):
        self.nav_timer.stop()
        if self.player:
            self.player.stop()
            self.player.setVideoOutput(None)
            self.player.setMedia(QMediaContent())
        self.video_item = None
        self.current_item = None
        self.scene.clear()
        self.hide()
        if self.parent(): self.parent().setFocus()

    def closeEvent(self, event):
        self.nav_timer.stop()
        if self.player:
            self.player.stop()
            self.player.setVideoOutput(None)
            self.player.setMedia(QMediaContent())
            self.player.deleteLater()
            self.player = None
        super().closeEvent(event)
