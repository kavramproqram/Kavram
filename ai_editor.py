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
import re
import json
import sqlite3
import unicodedata
import zipfile
import tempfile
import shutil
import random
import tarfile
import time

from PyQt5.QtWidgets import (
    QWidget, QFrame, QPushButton, QVBoxLayout, QHBoxLayout,
    QTextEdit, QFileDialog, QProgressBar, QApplication,
    QLineEdit, QLabel, QMessageBox, QStackedWidget, QScrollArea,
    QSizePolicy, QMenu, QAction, QSlider, QDialog, QShortcut,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGridLayout
)
from PyQt5.QtCore import Qt, QTimer, QDir, QSize, QEvent, QByteArray, QSettings, pyqtSignal, QRect, QUrl, QPointF
from PyQt5.QtGui import QIcon, QPainter, QPixmap, QTextCursor, QFont, QColor, QTransform, QKeySequence, QWheelEvent, QMouseEvent, QDesktopServices
from PyQt5.QtSvg import QSvgRenderer

try:
    from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
    from PyQt5.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
    QT_MULTIMEDIA_AVAILABLE = True
except ImportError:
    QT_MULTIMEDIA_AVAILABLE = False
    QVideoWidget = QWidget
    QGraphicsVideoItem = None
    print("PyQt5.QtMultimedia veya PyQt5.QtMultimediaWidgets kütüphanesi yüklenemedi. Medya özellikleri sınırlı çalışabilir.")


def normalize_text(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize('NFD', s)
    s = s.encode('ascii', 'ignore').decode('utf-8')
    return s.lower()

def create_svg_icon(svg_content, size=20, color="#ffffff"):
    modified_svg_content = svg_content.replace('stroke="#aaa"', f'stroke="{color}"').replace('fill="#aaa"', f'fill="{color}"')
    renderer = QSvgRenderer(QByteArray(modified_svg_content.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

SVG_SAVE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V7L17 3ZM12 17C10.34 17 9 15.66 9 14C9 12.34 10.34 11 12 11C13.66 11 15 12.34 15 14C15 15.66 13.66 17 12 17Z" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_X_ICON = """<svg viewBox="0 0 24 24" fill="none" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>"""
SVG_PLAY_ICON = """<svg viewBox="0 0 24 24" fill="white"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>"""
SVG_PAUSE_ICON = """<svg viewBox="0 0 24 24" fill="white"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>"""
SVG_IMAGE_ICON = """<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>"""
SVG_FILE_ICON = """<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>"""

class KavramDB:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS words
                     (id INTEGER PRIMARY KEY, norm_word TEXT, raw_word TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS definitions
                     (id INTEGER PRIMARY KEY, word_id INTEGER, raw_def TEXT)''')
        
        c.execute('DROP TABLE IF EXISTS chat_history')
        self.conn.commit()

    def migrate_from_dict(self, word_dict):
        c = self.conn.cursor()
        c.execute("DELETE FROM words")
        c.execute("DELETE FROM definitions")
        
        for k, entries in word_dict.items():
            if k == "__chat_history__":
                continue 
            
            c.execute("INSERT INTO words (norm_word, raw_word) VALUES (?, ?)", (k, k))
            word_id = c.lastrowid
            
            for entry in entries:
                raw_def = entry[0] if isinstance(entry, list) else str(entry)
                c.execute("INSERT INTO definitions (word_id, raw_def) VALUES (?, ?)", (word_id, raw_def))
        self.conn.commit()

    def get_all_packets(self):
        c = self.conn.cursor()
        c.execute('''SELECT d.id, w.raw_word, d.raw_def FROM definitions d
                     JOIN words w ON d.word_id = w.id ORDER BY d.id DESC''')
        return c.fetchall()

    def add_packet(self, word, definition):
        norm = normalize_text(word)
        c = self.conn.cursor()
        c.execute("SELECT id FROM words WHERE norm_word=?", (norm,))
        row = c.fetchone()
        if row:
            word_id = row[0]
        else:
            c.execute("INSERT INTO words (norm_word, raw_word) VALUES (?, ?)", (norm, word))
            word_id = c.lastrowid
        c.execute("INSERT INTO definitions (word_id, raw_def) VALUES (?, ?)", (word_id, definition))
        self.conn.commit()
        return c.lastrowid

    def update_packet(self, def_id, new_word, new_def):
        c = self.conn.cursor()
        norm = normalize_text(new_word)
        c.execute("SELECT id FROM words WHERE norm_word=?", (norm,))
        row = c.fetchone()
        if row:
            new_word_id = row[0]
        else:
            c.execute("INSERT INTO words (norm_word, raw_word) VALUES (?, ?)", (norm, new_word))
            new_word_id = c.lastrowid
        c.execute("UPDATE definitions SET word_id=?, raw_def=? WHERE id=?", (new_word_id, new_def, def_id))
        
        c.execute("DELETE FROM words WHERE id NOT IN (SELECT word_id FROM definitions)")
        self.conn.commit()

    def delete_packet(self, def_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM definitions WHERE id=?", (def_id,))
        c.execute("DELETE FROM words WHERE id NOT IN (SELECT word_id FROM definitions)")
        self.conn.commit()

    def is_duplicate_word(self, word, current_def_id=None):
        norm = normalize_text(word)
        if not norm: return False
        c = self.conn.cursor()
        if current_def_id is not None:
            c.execute('''SELECT d.id FROM definitions d 
                         JOIN words w ON d.word_id = w.id 
                         WHERE w.norm_word = ? AND d.id != ?''', (norm, current_def_id))
        else:
            c.execute('''SELECT d.id FROM definitions d 
                         JOIN words w ON d.word_id = w.id 
                         WHERE w.norm_word = ?''', (norm,))
        return c.fetchone() is not None

    def search_definitions(self, word):
        norm = normalize_text(word)
        c = self.conn.cursor()
        c.execute('''SELECT d.raw_def FROM definitions d
                     JOIN words w ON d.word_id = w.id WHERE w.norm_word = ?''', (norm,))
        exact_matches = [r[0] for r in c.fetchall()]
        return exact_matches

    def get_valid_words(self):
        c = self.conn.cursor()
        c.execute("""SELECT DISTINCT w.raw_word FROM words w
                     JOIN definitions d ON w.id = d.word_id
                     ORDER BY w.id ASC""")
        return [r[0] for r in c.fetchall()]

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
        
        # Sadece bir kere oluşturulan Tekil (Persistent) Oynatıcı mimarisi GStreamer sızıntılarını önler.
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
        
        # Eski oynatma durdurulur ve kaynak serbest bırakılır.
        if self.player:
            self.player.stop()
            self.player.setVideoOutput(None)
            self.player.setMedia(QMediaContent())
        
        self.video_item = None
        self.current_item = None
        
        abs_filepath = os.path.abspath(filepath)
        
        # Kritik Hata Önleme: Fiziksel dosya doğrulama testi
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
            # Kritik Hata Önleme: NaN Matris Hatasını engelleyen bozuk resim testi
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
        
        # UI ölçeklendirme kuyruğuna gecikmeli tetikleyici eklenir
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
                
            # Tuşa basılı tutulduğunda çok hızlı geçmesini engelleyip, 0.25 saniyelik limit koyar. (Sistemi yormaz)
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
        
        # Oynatıcıyı asenkron olarak silmek yerine sıfırlayarak koruruz.
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


class AutoResizingTextEdit(QTextEdit):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.setPlainText(text)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textChanged.connect(self.adjustHeight)
        self.setStyleSheet("background: #1a1a1a; color: #bbbbbb; border: 1px solid #555; padding: 5px; border-radius: 4px;")
        self.setContextMenuPolicy(Qt.CustomContextMenu)

    def adjustHeight(self):
        doc_height = self.document().size().height()
        new_height = int(doc_height + 15)
        self.setFixedHeight(new_height)

    def showEvent(self, event):
        super().showEvent(event)
        self.adjustHeight()


class FontSelectorWidget(QPushButton):
    fontSizeChanged = pyqtSignal(int)

    def __init__(self, initial_value=16, parent=None):
        super().__init__(str(initial_value), parent)
        self.current_value = initial_value
        self.setFixedSize(50, 30)
        self.setStyleSheet("""
            QPushButton { background-color: transparent; color: white; font-size: 14px; font-weight: bold; border: 2px solid #555; border-radius: 8px; }
            QPushButton:hover { background-color: #444; }
        """)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Font Boyutu: Tıkla veya Scroll Yap")

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0: self.changeValue(1)
        else: self.changeValue(-1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.showMenu()
        super().mousePressEvent(event)

    def showMenu(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
        for size in [8, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72]:
            action = QAction(str(size), self)
            action.triggered.connect(lambda checked, s=size: self.setValue(s))
            menu.addAction(action)
        menu.exec_(self.mapToGlobal(self.rect().bottomLeft()))

    def changeValue(self, delta):
        self.setValue(max(8, min(self.current_value + delta, 72)))

    def setValue(self, val):
        if val != self.current_value:
            self.current_value = val
            self.setText(str(val))
            self.fontSizeChanged.emit(val)

    def updateDisplay(self, val):
        self.current_value = val
        self.setText(str(val))

class PacketWidget(QFrame):
    def __init__(self, def_id, word, definition, parent_panel):
        super().__init__()
        self.parent_panel = parent_panel
        self.def_id = def_id
        self.word = str(word)
        self.raw_definition = str(definition)
        self.media_files = []
        self.media_widgets = []
        self.is_active = False
        
        self.initUI()
        self.set_inactive()

    def initUI(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(5, 5, 5, 5)
        
        self.summary_btn = QPushButton()
        self.summary_btn.setStyleSheet("""
            QPushButton { background-color: #1a1a1a; color: #777; border: 1px solid #333; border-radius: 6px; padding: 10px; text-align: left; font-size: 14px; }
            QPushButton:hover { background-color: #222; color: #aaa; border: 1px solid #555; }
        """)
        self.summary_btn.clicked.connect(self.request_activation)
        self.summary_btn.setCursor(Qt.PointingHandCursor)
        self.main_layout.addWidget(self.summary_btn)
        
        self.active_container = QWidget()
        self.active_layout = QVBoxLayout(self.active_container)
        self.active_layout.setContentsMargins(0,0,0,0)
        self.active_layout.setSpacing(5)
        
        self.top_row_widget = QWidget()
        self.top_row_layout = QHBoxLayout(self.top_row_widget)
        self.top_row_layout.setContentsMargins(0, 0, 0, 0)
        self.top_row_layout.setSpacing(5)
        
        self.btn_delete_packet = QPushButton("x")
        self.btn_delete_packet.setFixedSize(30, 30)
        self.btn_delete_packet.setStyleSheet("""
            QPushButton { background-color: transparent; color: #FFF; font-size: 16px; font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 0px; }
            QPushButton:hover { background-color: #444; }
        """)
        self.btn_delete_packet.setToolTip("Bu paketi sil")
        self.btn_delete_packet.clicked.connect(self.delete_packet)
        self.top_row_layout.addWidget(self.btn_delete_packet)
        
        self.word_edit = QLineEdit(self.word)
        self.word_edit.setPlaceholderText("Soru")
        self.word_edit.editingFinished.connect(self.on_word_editing_finished)
        self.word_edit.installEventFilter(self)
        self.top_row_layout.addWidget(self.word_edit, stretch=1)
        self.active_layout.addWidget(self.top_row_widget)

        self.def_edit = AutoResizingTextEdit("")
        self.def_edit.setPlaceholderText("Cevap")
        self.def_edit.textChanged.connect(self.update_data)
        self.def_edit.installEventFilter(self)
        self.def_edit.customContextMenuRequested.connect(self.show_context_menu)
        self.active_layout.addWidget(self.def_edit)
        
        self.media_container_widget = QWidget()
        self.media_container_layout = QVBoxLayout(self.media_container_widget)
        self.media_container_layout.setContentsMargins(0, 0, 0, 0)
        self.media_container_layout.setSpacing(5)
        
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(5)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(4)
        self.list_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        self.media_container_layout.addWidget(self.grid_widget)
        self.media_container_layout.addWidget(self.list_widget)
        self.active_layout.addWidget(self.media_container_widget)
        
        self.main_layout.addWidget(self.active_container)
        
        self.applyFontSize(self.parent_panel.current_font_size)

    def on_word_editing_finished(self):
        if not self.is_active: return
        new_word = self.word_edit.text().strip()
        if new_word == self.word: return
        
        db = self.parent_panel.parent_window.db
        if db and db.is_duplicate_word(new_word, self.def_id):
            QMessageBox.warning(self, "Uyarı", f"'{new_word}' sorusu zaten mevcut!\nAynı soruya sahip iki paket oluşturulamaz.")
            self.word_edit.setText(self.word)
            return
            
        self.update_data()

    def request_activation(self):
        self.parent_panel.set_packet_active(self)

    def set_inactive(self):
        self.is_active = False
        self.setStyleSheet("PacketWidget { background-color: transparent; margin-bottom: 2px; }")
        
        self.clear_media()
        
        clean_text = re.sub(r'\[(?:AUDIO|IMAGE|VIDEO|FILE):.+?\]', '', self.raw_definition).strip()
        preview = clean_text[:60] + "..." if len(clean_text) > 60 else clean_text
        self.summary_btn.setText(f"{self.word}   —   {preview}")
        
        self.active_container.hide()
        self.summary_btn.show()

    def set_active(self, force=False):
        if self.is_active and not force: return
        self.is_active = True
        self.setStyleSheet("PacketWidget { background-color: #2b2b2b; border: 1px solid #555; border-radius: 8px; margin-bottom: 5px; padding: 5px; }")
        
        self.summary_btn.hide()
        
        self.media_files = []
        matches = re.findall(r'\[(AUDIO|IMAGE|VIDEO|FILE):(.+?)\]', self.raw_definition)
        for m in matches: self.media_files.append({'type': m[0], 'file': m[1]})
        
        clean_definition = re.sub(r'\[(?:AUDIO|IMAGE|VIDEO|FILE):.+?\]', '', self.raw_definition).strip()
        
        self.def_edit.blockSignals(True)
        self.def_edit.setPlainText(clean_definition)
        self.def_edit.blockSignals(False)
        self.def_edit.adjustHeight()
        
        self.clear_media()
        for mf in self.media_files:
            self.add_media_player_ui(mf['type'], mf['file'])
            
        self.active_container.show()
        if not force:
            self.word_edit.setFocus()

    def clear_media(self):
        for widget in self.media_widgets:
            widget.setParent(None)
            widget.deleteLater()
        self.media_widgets.clear()
        
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
                
        for i in reversed(range(self.list_layout.count())):
            item = self.list_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)

    def delete_packet(self):
        if self.def_id is not None:
            self.parent_panel.parent_window.db.delete_packet(self.def_id)
        if self in self.parent_panel.active_packets:
            self.parent_panel.active_packets.remove(self)
        self.setParent(None)
        self.deleteLater()
        self.parent_panel.parent_window.chat_page.sync_history_with_dict()

    def show_context_menu(self, pos):
        menu = self.def_edit.createStandardContextMenu()
        menu.addSeparator()
        
        add_media_action = QAction("Medya Ekle", self)
        add_media_action.triggered.connect(self.add_multiple_media_action_triggered)
        menu.addAction(add_media_action)
        
        add_text_action = QAction("Metin Ekle", self)
        add_text_action.triggered.connect(self.add_text_file_action_triggered)
        menu.addAction(add_text_action)
        
        menu.exec_(self.def_edit.viewport().mapToGlobal(pos))

    def add_multiple_media_action_triggered(self):
        filters = "Medya Dosyaları (*.png *.jpg *.jpeg *.gif *.bmp *.webp *.mp3 *.wav *.ogg *.m4a *.aac *.flac *.mp4 *.avi *.mkv *.mov *.webm);;Tüm Dosyalar (*)"
        filepaths, _ = QFileDialog.getOpenFileNames(self, "Medyaları Seç", AiEditorWindow.DEFAULT_BASE_DIR, filters)
        if filepaths:
            self.process_added_files(filepaths)

    def add_generic_file_action_triggered(self):
        filepaths, _ = QFileDialog.getOpenFileNames(self, "Dosyaları Seç", AiEditorWindow.DEFAULT_BASE_DIR, "Tüm Dosyalar (*)")
        if filepaths:
            self.process_added_files(filepaths, force_file_type=True)

    def process_added_files(self, filepaths, force_file_type=False):
        total_current_count = len(self.media_files)
        added_any = False
        excess_total_flag = False
        
        for filepath in filepaths:
            if total_current_count >= 16:
                excess_total_flag = True
                break
                
            filename = os.path.basename(filepath)
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            
            if force_file_type:
                m_type = "FILE"
            elif ext in ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'):
                m_type = "IMAGE"
            elif ext in ('.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac'):
                m_type = "AUDIO"
            elif ext in ('.mp4', '.avi', '.mkv', '.mov', '.webm'):
                m_type = "VIDEO"
            else:
                m_type = "FILE"
                
            dest_path = os.path.join(self.parent_panel.parent_window.temp_dir, filename)
            if os.path.abspath(filepath) != os.path.abspath(dest_path):
                if os.path.exists(dest_path) and os.path.getsize(filepath) != os.path.getsize(dest_path):
                    name, extension = os.path.splitext(filename)
                    counter = 1
                    while True:
                        new_filename = f"{name}{counter}{extension}"
                        new_dest_path = os.path.join(self.parent_panel.parent_window.temp_dir, new_filename)
                        if not os.path.exists(new_dest_path) or os.path.getsize(filepath) == os.path.getsize(new_dest_path):
                            filename = new_filename
                            dest_path = new_dest_path
                            break
                        counter += 1
                shutil.copy2(filepath, dest_path)
                
            self.media_files.append({'type': m_type, 'file': filename})
            self.add_media_player_ui(m_type, filename)
            added_any = True
            total_current_count += 1
            
        if added_any:
            self.update_data()
            
        if excess_total_flag:
            QMessageBox.warning(self, "Sınır Uyarısı", "Bir paket içerisine toplam en fazla 16 adet dosya eklenebilir. Dosyaların bazılarını silerek boş yer açabilirsiniz.")

    def add_text_file_action_triggered(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Metin Seç", AiEditorWindow.DEFAULT_BASE_DIR, "Metin Dosyaları (*.txt);;Tüm Dosyalar (*)")
        if filepath:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    current_text = self.def_edit.toPlainText().strip()
                    new_text = f"{current_text}\n{content}" if current_text else content
                    self.def_edit.setPlainText(new_text)
                    self.update_data()
            except Exception as e:
                QMessageBox.critical(self, "Hata", str(e))

    def add_media_player_ui(self, media_type, filename):
        full_path = os.path.join(self.parent_panel.parent_window.temp_dir, filename)
        widget = None
        
        if media_type == "AUDIO":
            widget = AudioPlayerWidget(full_path, self.parent_panel.parent_window, context_source=self)
            widget.setFixedWidth(415)
            self.list_layout.addWidget(widget)
        elif media_type == "FILE":
            widget = FileAttachmentWidget(full_path, self.parent_panel.parent_window, context_source=self)
            widget.setFixedWidth(415)
            self.list_layout.addWidget(widget)
        elif media_type in ("IMAGE", "VIDEO"):
            if media_type == "IMAGE":
                widget = ImageThumbnailWidget(full_path, self.parent_panel.parent_window, context_source=self)
            else:
                widget = VideoThumbnailWidget(full_path, self.parent_panel.parent_window, context_source=self)
                
            current_grid_count = 0
            for i in range(self.grid_layout.count()):
                if self.grid_layout.itemAt(i).widget():
                    current_grid_count += 1
            row = current_grid_count // 4
            col = current_grid_count % 4
            self.grid_layout.addWidget(widget, row, col)
            
        if widget:
            widget.media_type = media_type
            widget.filename = filename
            widget.setContextMenuPolicy(Qt.CustomContextMenu)
            widget.customContextMenuRequested.connect(lambda pos, w=widget: self.show_media_context_menu(w, pos))
            self.media_widgets.append(widget)

    def show_media_context_menu(self, widget, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #1a1a1a; color: white; border: 1px solid #555; }
            QMenu::item { padding: 5px 25px; font-weight: bold; }
            QMenu::item:selected { background-color: #444; }
        """)
        
        # Değiştir seçeneği tamamen kaldırılarak sadece "Sil" seçeneği bırakılmıştır.
        del_action = QAction("Sil", self)
        menu.addAction(del_action)
        
        action = menu.exec_(widget.mapToGlobal(pos))
        if action == del_action:
            self.remove_media_item(widget)

    def remove_media_item(self, widget):
        filename_to_remove = getattr(widget, 'filename', None)
        if not filename_to_remove: return
        
        file_path = os.path.join(self.parent_panel.parent_window.temp_dir, filename_to_remove)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Silme hatası: {e}")
            
        self.media_files = [mf for mf in self.media_files if mf['file'] != filename_to_remove]
        
        self.refresh_media_ui()
        self.update_data()

    def refresh_media_ui(self):
        self.clear_media()
        for mf in self.media_files:
            self.add_media_player_ui(mf['type'], mf['file'])

    def applyFontSize(self, size):
        style_line = f"background: #1a1a1a; color: #ffffff; border: 1px solid #555; padding: 5px; border-radius: 4px; font-size: {size}px;"
        style_text = f"background: #1a1a1a; color: #bbbbbb; border: 1px solid #555; padding: 5px; border-radius: 4px; font-size: {size}px;"
        if hasattr(self, 'word_edit'): self.word_edit.setStyleSheet(style_line)
        if hasattr(self, 'def_edit'): self.def_edit.setStyleSheet(style_text)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn and not self.is_active:
            self.request_activation()
            
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if obj == self.word_edit:
                if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Down):
                    self.def_edit.setFocus()
                    if key == Qt.Key_Down:
                        cursor = self.def_edit.textCursor()
                        cursor.movePosition(QTextCursor.Start)
                        self.def_edit.setTextCursor(cursor)
                    return True
                elif key == Qt.Key_Up:
                    self.navigate_packet(direction=-1, target_field='def', move_to_end=True)
                    return True
            elif obj == self.def_edit:
                if key == Qt.Key_Up:
                    cursor = self.def_edit.textCursor()
                    if not cursor.atBlockStart():
                        cursor.movePosition(QTextCursor.StartOfBlock)
                        self.def_edit.setTextCursor(cursor)
                        return True
                    if cursor.atStart() and self.word_edit:
                        self.word_edit.setFocus()
                        return True
                elif key == Qt.Key_Down:
                    cursor = self.def_edit.textCursor()
                    if not cursor.atBlockEnd():
                        cursor.movePosition(QTextCursor.EndOfBlock)
                        self.def_edit.setTextCursor(cursor)
                        return True
                    if cursor.atEnd():
                        self.navigate_packet(direction=1, target_field='word')
                        return True
        return super().eventFilter(obj, event)

    def navigate_packet(self, direction, target_field, move_to_end=False):
        layout = self.parent_panel.scroll_layout
        count = layout.count()
        current_index = -1
        for i in range(count):
            if layout.itemAt(i).widget() == self:
                current_index = i
                break
        if current_index == -1: return
        target_index = (current_index + direction) % count
        target_widget = layout.itemAt(target_index).widget()
        if isinstance(target_widget, PacketWidget):
            self.parent_panel.set_packet_active(target_widget)
            self.parent_panel.scroll.ensureWidgetVisible(target_widget)
            if target_field == 'word':
                t_edit = target_widget.word_edit
                t_edit.setFocus()
                t_edit.setCursorPosition(len(t_edit.text()) if move_to_end else 0)
            elif target_field == 'def':
                target_widget.def_edit.setFocus()
                cursor = target_widget.def_edit.textCursor()
                cursor.movePosition(QTextCursor.End if move_to_end else QTextCursor.Start)
                target_widget.def_edit.setTextCursor(cursor)

    def update_data(self):
        if not self.is_active: return
        new_word_raw = self.word_edit.text().strip()
        
        db = self.parent_panel.parent_window.db
        if db and new_word_raw != self.word and db.is_duplicate_word(new_word_raw, self.def_id):
            return 

        clean_text = self.def_edit.toPlainText().strip()
        new_def = clean_text
        for mf in self.media_files:
            new_def += f"\n[{mf['type']}:{mf['file']}]"
        new_def = new_def.strip()
        
        db = self.parent_panel.parent_window.db
        if db:
            if self.def_id is None:
                if new_word_raw or new_def:
                    self.def_id = db.add_packet(new_word_raw, new_def)
            else:
                db.update_packet(self.def_id, new_word_raw, new_def)
                
        self.word = new_word_raw
        self.raw_definition = new_def
        self.parent_panel.parent_window.chat_page.sync_history_with_dict()


class DataManagementPage(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.current_font_size = parent_window.data_font_size
        self.active_packets = [] 
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        header_layout = QHBoxLayout()
        title = QLabel("Hafıza (SQLite & Lazy Mode)")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

    def set_packet_active(self, packet_widget):
        if packet_widget in self.active_packets: return
        
        self.active_packets.append(packet_widget)
        packet_widget.set_active()
        
        if len(self.active_packets) > 3:
            oldest = self.active_packets.pop(0)
            oldest.set_inactive()

    def refreshList(self):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self.active_packets.clear()
        
        if not self.parent_window.db: return
        
        packets_data = self.parent_window.db.get_all_packets()
        for i, (def_id, word, definition) in enumerate(packets_data):
            pw = PacketWidget(def_id, word, definition, self)
            self.scroll_layout.addWidget(pw)
            if i < 3:
                self.active_packets.append(pw)
                pw.set_active(force=True)

    def addNewPacket(self):
        pw = PacketWidget(None, "", "", self)
        self.scroll_layout.insertWidget(0, pw)
        self.set_packet_active(pw)
        pw.word_edit.setFocus()

    def set_font_size(self, size):
        self.current_font_size = size
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if isinstance(widget, PacketWidget):
                widget.applyFontSize(size)


class ChatPanel(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self.parent_window = parent_window
        self.history = []
        self.history_index = -1  
        self.current_font_size = 16
        self.initUI()

    def initUI(self):
        self.setStyleSheet(f"""
            QWidget {{ background-color: #2b2b2b; color: white; font-family: Arial; font-size: {self.current_font_size}px; }}
            QLineEdit {{ background-color: #222; color: white; padding: 8px; border: 1px solid #555; border-radius: 4px; font-size: {self.current_font_size}px; }}
            QPushButton {{ background-color: #444; color: white; font-size: 18px; font-weight: bold; border: 1px solid #666; border-radius: 6px; padding: 8px 16px; }}
            QPushButton:hover {{ background-color: #555; }}
            QPushButton:pressed {{ background-color: #666; }}
        """)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("background-color: #2b2b2b; border: 1px solid #555; border-radius: 6px;")
        self.chat_scroll.verticalScrollBar().rangeChanged.connect(
            lambda min, max: self.chat_scroll.verticalScrollBar().setValue(max)
        )
        self.chat_content = QWidget()
        self.chat_content.setStyleSheet("background-color: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_scroll.setWidget(self.chat_content)
        main_layout.addWidget(self.chat_scroll)
        
        input_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("You:")
        self.input_line.returnPressed.connect(self.sendMessage)
        self.input_line.installEventFilter(self)
        send_button = QPushButton("↑")
        send_button.clicked.connect(self.sendMessage)
        send_button.setFixedWidth(60)
        input_layout.addWidget(self.input_line)
        input_layout.addWidget(send_button)
        main_layout.addLayout(input_layout)

    def set_font_size(self, size):
        self.current_font_size = size
        self.input_line.setStyleSheet(f"background-color: #222; color: white; padding: 8px; border: 1px solid #555; border-radius: 4px; font-size: {size}px;")

    def sync_history_with_dict(self):
        if not self.parent_window.db: return
        self.history = self.parent_window.db.get_valid_words()
        self.history_index = -1

    def eventFilter(self, obj, event):
        if obj == self.input_line and event.type() == QEvent.KeyPress:
            key = event.key()
            if not self.history: return super().eventFilter(obj, event)
            
            if key == Qt.Key_Up:
                if self.history_index == -1:
                    self.history_index = len(self.history) - 1
                else:
                    self.history_index = (self.history_index - 1) % len(self.history)
                self.input_line.setText(self.history[self.history_index])
                return True
            elif key == Qt.Key_Down:
                if self.history_index == -1:
                    self.history_index = 0
                else:
                    self.history_index = (self.history_index + 1) % len(self.history)
                self.input_line.setText(self.history[self.history_index])
                return True
        return super().eventFilter(obj, event)

    def add_bubble(self, sender, text, is_user=False, media_files=None):
        bubble_container = QWidget()
        bubble_layout = QVBoxLayout(bubble_container)
        bubble_layout.setContentsMargins(5, 5, 5, 5)
        bubble_layout.setSpacing(4)
        
        bubble = QFrame()
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        bg_color = "#3a3a3a" if is_user else "#252525"
        bubble.setStyleSheet(f"QFrame {{ background-color: {bg_color}; border-radius: 10px; border: 1px solid #444; }}")
        inner_layout = QVBoxLayout(bubble)
        inner_layout.setContentsMargins(10, 10, 10, 10)
        lbl_text = f"<b>{sender}:</b> {text.replace(chr(10), '<br>')}" if text else f"<b>{sender}:</b>"
        lbl = QLabel(lbl_text)
        lbl.setWordWrap(True)
        lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        lbl.setStyleSheet(f"color: white; font-size: {self.current_font_size}px; background: transparent; border: none;")
        inner_layout.addWidget(lbl)
        
        if media_files:
            bubble_media_widget = QWidget()
            bubble_media_layout = QVBoxLayout(bubble_media_widget)
            bubble_media_layout.setContentsMargins(0, 5, 0, 0)
            bubble_media_layout.setSpacing(5)
            
            b_grid_widget = QWidget()
            b_grid_layout = QGridLayout(b_grid_widget)
            b_grid_layout.setContentsMargins(0, 0, 0, 0)
            b_grid_layout.setSpacing(5)
            b_grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            
            b_list_widget = QWidget()
            b_list_layout = QVBoxLayout(b_list_widget)
            b_list_layout.setContentsMargins(0, 0, 0, 0)
            b_list_layout.setSpacing(4)
            b_list_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            
            bubble_media_layout.addWidget(b_grid_widget)
            bubble_media_layout.addWidget(b_list_widget)
            
            img_vid_count = 0
            for mf in media_files:
                full_path = os.path.join(self.parent_window.temp_dir, mf['file'])
                m_type = mf['type']
                widget = None
                
                if m_type == "AUDIO":
                    widget = AudioPlayerWidget(full_path, self.parent_window)
                    widget.setFixedWidth(415)
                    b_list_layout.addWidget(widget)
                elif m_type == "FILE":
                    widget = FileAttachmentWidget(full_path, self.parent_window)
                    widget.setFixedWidth(415)
                    b_list_layout.addWidget(widget)
                elif m_type in ("IMAGE", "VIDEO"):
                    if m_type == "IMAGE":
                        widget = ImageThumbnailWidget(full_path, self.parent_window, context_source=media_files)
                    else:
                        widget = VideoThumbnailWidget(full_path, self.parent_window, context_source=media_files)
                        
                    row = img_vid_count // 4
                    col = img_vid_count % 4
                    b_grid_layout.addWidget(widget, row, col)
                    img_vid_count += 1
            
            inner_layout.addWidget(bubble_media_widget)
        
        bubble_layout.addWidget(bubble)
        self.chat_layout.addWidget(bubble_container)
        
        while self.chat_layout.count() > 10:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum()))

    def sendMessage(self):
        message = self.input_line.text().strip()
        if not message: return
        
        self.add_bubble("You", message, is_user=True)
        self.input_line.clear()
        response = self.getDefinition(message)
        
        medias = re.findall(r'\[(AUDIO|IMAGE|VIDEO|FILE):(.+?)\]', response)
        text_only = re.sub(r'\[(?:AUDIO|IMAGE|VIDEO|FILE):.+?\]', '', response).strip()
        unique_medias = []
        seen_files = set()
        for m_type, m_file in medias:
            if m_file not in seen_files:
                seen_files.add(m_file)
                unique_medias.append({'type': m_type, 'file': m_file})
        self.add_bubble("Chat", text_only, is_user=False, media_files=unique_medias)

    def getDefinition(self, word):
        if not self.parent_window.db: return "Veritabanı yüklü değil."
        answers = self.parent_window.db.search_definitions(word)
        if not answers: return "Bilmiyorum"
        unique_answers = list(set(answers))
        unique_answers.sort(key=len)
        return "\n\n".join(unique_answers)


class AiEditorWindow(QWidget):
    DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')

    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        self.current_ai_path = None
        
        self.temp_dir = os.path.join(self.DEFAULT_BASE_DIR, "ai")
        
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                print(f"ai klasörü temizlenirken hata oluştu: {e}")
                
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.db = None
        self.last_active_player = None
        self.settings = QSettings("Kavram", "AiEditor")
        self.chat_font_size = self.settings.value("chat_font_size", 16, type=int)
        self.data_font_size = self.settings.value("data_font_size", 14, type=int)
        
        self.media_overlay = MediaOverlay(self)
        self.media_overlay.hide()
        self.initUI()
        
        self.stack.setCurrentWidget(self.chat_page)
        self.update_font_toolbar_state(1)
        self.check_initial_db()

    def initUI(self):
        self.setWindowTitle("AI Editor")
        self.setStyleSheet("background-color: #333; border: none;")
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("QFrame { background-color: #222; border-bottom: 2px solid #555; }")
        toolbar_frame.setFixedHeight(40)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        
        self.file_button = QPushButton("File")
        self.file_button.setStyleSheet(self.buttonStyle())
        self.file_button.setFixedSize(90, 30)
        self.file_button.clicked.connect(self.openFiles)
        
        self.save_button = QPushButton()
        self.save_button.setIcon(create_svg_icon(SVG_SAVE_ICON, size=20, color="#ffffff"))
        self.save_button.setStyleSheet(self.buttonStyleMini())
        self.save_button.setFixedSize(30, 30)
        self.save_button.setToolTip("Kaydet")
        self.save_button.clicked.connect(self.saveContent)
        
        self.new_button = QPushButton("New")
        self.new_button.setStyleSheet(self.buttonStyle())
        self.new_button.setFixedSize(90, 30)
        self.new_button.clicked.connect(self.createNewPacketAction)
        
        self.chat_button = QPushButton("Chat")
        self.chat_button.setStyleSheet(self.buttonStyle())
        self.chat_button.setFixedSize(90, 30)
        self.chat_button.clicked.connect(self.showChatPanel)
        
        self.edit_button = QPushButton("Edit")
        self.edit_button.setStyleSheet(self.buttonStyle())
        self.edit_button.setFixedSize(90, 30)
        self.edit_button.clicked.connect(self.showDataPage)
        
        self.clear_chat_button = QPushButton()
        self.clear_chat_button.setIcon(create_svg_icon(SVG_X_ICON, size=20, color="#ffffff"))
        self.clear_chat_button.setStyleSheet(self.buttonStyleMini())
        self.clear_chat_button.setFixedSize(30, 30)
        self.clear_chat_button.setToolTip("Sohbeti Temizle")
        self.clear_chat_button.clicked.connect(self.clearChatAction)
        
        self.font_widget = FontSelectorWidget(self.chat_font_size)
        self.font_widget.fontSizeChanged.connect(self.change_font_size)
        
        self.exit_fullscreen_button = QPushButton("_")
        self.exit_fullscreen_button.setStyleSheet(self.buttonStyleMini())
        self.exit_fullscreen_button.setFixedSize(30, 30)
        self.exit_fullscreen_button.setToolTip("Tam Ekrandan Çık")
        self.exit_fullscreen_button.clicked.connect(self.close_media_overlay)
        
        toolbar_layout.addWidget(self.file_button, alignment=Qt.AlignLeft)
        toolbar_layout.addWidget(self.save_button, alignment=Qt.AlignLeft)
        toolbar_layout.addWidget(self.new_button, alignment=Qt.AlignLeft)
        toolbar_layout.addWidget(self.chat_button, alignment=Qt.AlignLeft)
        toolbar_layout.addWidget(self.exit_fullscreen_button, alignment=Qt.AlignLeft)
        toolbar_layout.addWidget(self.edit_button, alignment=Qt.AlignLeft)
        toolbar_layout.addWidget(self.clear_chat_button, alignment=Qt.AlignLeft)
        toolbar_layout.addSpacing(10)
        toolbar_layout.addWidget(self.font_widget, alignment=Qt.AlignLeft)
        
        self.clear_ai_button = QPushButton("S")
        self.clear_ai_button.setStyleSheet(self.buttonStyleMini())
        self.clear_ai_button.setFixedSize(30, 30)
        self.clear_ai_button.setToolTip("Açık Verileri ve 'ai' Klasörünü Temizle")
        self.clear_ai_button.clicked.connect(self.clearAiFolderAction)
        toolbar_layout.addWidget(self.clear_ai_button, alignment=Qt.AlignLeft)
        toolbar_layout.addStretch()
        
        self.export_button = QPushButton("Export")
        self.export_button.setStyleSheet(self.buttonStyle())
        self.export_button.setFixedSize(90, 30)
        self.export_button.clicked.connect(self.exportAIFile)
        toolbar_layout.addWidget(self.export_button, alignment=Qt.AlignRight)
        
        self.ai_button = QPushButton("Ai")
        self.ai_button.setStyleSheet(self.buttonStyle())
        self.ai_button.setFixedSize(90, 30)
        self.ai_button.clicked.connect(self.triggerCoreSwitcher)
        toolbar_layout.addWidget(self.ai_button, alignment=Qt.AlignRight)

        self.stack = QStackedWidget()
        self.stack.currentChanged.connect(self.update_font_toolbar_state)
        
        self.chat_page = ChatPanel(self)
        self.chat_page.set_font_size(self.chat_font_size)
        self.data_page = DataManagementPage(self)
        self.data_page.set_font_size(self.data_font_size)
        
        self.stack.addWidget(self.chat_page)
        self.stack.addWidget(self.data_page)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(toolbar_frame)
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

        self.media_overlay.lower()
        self.media_overlay.raise_()
        self.stack.installEventFilter(self)

    def check_initial_db(self):
        db_path = os.path.join(self.temp_dir, 'data.db')
        if os.path.exists(db_path):
            self.db = KavramDB(db_path)
            self.chat_page.sync_history_with_dict()
        else:
            self.db = KavramDB(db_path) 

    def eventFilter(self, obj, event):
        if obj == self.stack and event.type() == QEvent.Resize:
            if hasattr(self, 'media_overlay'):
                self.media_overlay.setGeometry(self.stack.geometry())
        return super().eventFilter(obj, event)

    def show_media_overlay(self, filepath, is_video=False, context_source=None):
        # ÖNEMLİ DÜZENLEME: Önce pencere boyutunu veriyoruz, sonra içeriği yüklüyoruz.
        # Bu sayede fitInView çağrısı 0x0 veya küçük pencere boyutuyla değil, tam hedef boyutuyla hesaplanır.
        self.media_overlay.setGeometry(self.stack.geometry())
        self.media_overlay.set_context(filepath, context_source)
        self.media_overlay.set_media(filepath, is_video)
        self.media_overlay.show()
        self.media_overlay.setFocus()

    def close_media_overlay(self):
        if hasattr(self, 'media_overlay'):
            self.media_overlay.close_overlay()

    def buttonStyle(self):
        return "QPushButton { background-color: transparent; color: white; font-size: 14px; font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 5px; } QPushButton:hover { background-color: #444; } QPushButton:pressed { background-color: #666; }"

    def buttonStyleMini(self):
        return "QPushButton { background-color: transparent; color: white; font-size: 16px; border: 2px solid #555; border-radius: 8px; padding: 2px; } QPushButton:hover { background-color: #444; } QPushButton:pressed { background-color: #666; }"

    def keyPressEvent(self, event):
        focus_widget = QApplication.focusWidget()
        if isinstance(focus_widget, (QLineEdit, QTextEdit)):
            super().keyPressEvent(event)
            return
        if event.key() == Qt.Key_Space and self.last_active_player:
            self.last_active_player.toggle_playback()
            event.accept()
            return
        super().keyPressEvent(event)

    def pause_all_audio_except(self, player_to_keep=None):
        for i in range(self.data_page.scroll_layout.count()):
            widget = self.data_page.scroll_layout.itemAt(i).widget()
            if isinstance(widget, PacketWidget) and widget.is_active:
                for p in widget.findChildren((AudioPlayerWidget,)):
                    if p != player_to_keep and hasattr(p, 'player') and p.player and p.player.state() == QMediaPlayer.PlayingState:
                        p.player.pause()
        for i in range(self.chat_page.chat_layout.count()):
            bubble_container = self.chat_page.chat_layout.itemAt(i).widget()
            if bubble_container:
                for p in bubble_container.findChildren((AudioPlayerWidget,)):
                    if p != player_to_keep and hasattr(p, 'player') and p.player and p.player.state() == QMediaPlayer.PlayingState:
                        p.player.pause()

    def update_font_toolbar_state(self, index):
        widget = self.stack.currentWidget()
        self.font_widget.blockSignals(True)
        if widget == self.chat_page:
            self.font_widget.updateDisplay(self.chat_font_size)
            self.font_widget.setEnabled(True)
        elif widget == self.data_page:
            self.font_widget.updateDisplay(self.data_font_size)
            self.font_widget.setEnabled(True)
        else: self.font_widget.setEnabled(False)
        self.font_widget.blockSignals(False)

    def change_font_size(self, val):
        widget = self.stack.currentWidget()
        if widget == self.chat_page:
            self.chat_font_size = val
            self.chat_page.set_font_size(val)
            self.settings.setValue("chat_font_size", val)
        elif widget == self.data_page:
            self.data_font_size = val
            self.data_page.set_font_size(val)
            self.settings.setValue("data_font_size", val)

    def createNewPacketAction(self):
        self.showDataPage()
        self.data_page.addNewPacket()

    def openFiles(self):
        options = QFileDialog.Options()
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Files", self.DEFAULT_BASE_DIR,
            "AI Files (*.ai);;All Files (*)", options=options
        )
        if file_paths: self._process_files(file_paths)

    def openFiles_from_path(self, file_paths):
        self._process_files(file_paths)

    def _process_files(self, file_paths):
        if not file_paths: return
        for file_path in file_paths:
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            if ext == ".ai":
                try:
                    self.current_ai_path = file_path
                    for item in os.listdir(self.temp_dir):
                        p = os.path.join(self.temp_dir, item)
                        if os.path.isdir(p): shutil.rmtree(p)
                        else: os.remove(p)
                    
                    if tarfile.is_tarfile(file_path):
                        with tarfile.open(file_path, 'r:*') as tar: tar.extractall(self.temp_dir)
                    elif zipfile.is_zipfile(file_path):
                        with zipfile.ZipFile(file_path, 'r') as zip_ref: zip_ref.extractall(self.temp_dir)
                    else:
                        shutil.copy2(file_path, os.path.join(self.temp_dir, "data.json")) 
                    
                    db_path = os.path.join(self.temp_dir, 'data.db')
                    json_path = os.path.join(self.temp_dir, 'data.json')
                    
                    self.db = KavramDB(db_path)
                    
                    if os.path.exists(json_path):
                        with open(json_path, "r", encoding="utf-8") as f:
                            loaded_dict = json.load(f)
                        self.db.migrate_from_dict(loaded_dict)
                        os.remove(json_path)

                    self.chat_page.sync_history_with_dict()
                    self.stack.setCurrentWidget(self.chat_page)
                    return
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"{file_path} okunurken hata oluştu:\n{str(e)}")

    def showChatPanel(self):
        self.chat_page.sync_history_with_dict()
        self.stack.setCurrentWidget(self.chat_page)
        self.chat_page.input_line.setFocus()

    def showDataPage(self):
        if self.stack.currentWidget() != self.data_page:
            self.data_page.refreshList()
            self.stack.setCurrentWidget(self.data_page)

    def clearChatAction(self):
        while self.chat_page.chat_layout.count():
            item = self.chat_page.chat_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

    def clearAiFolderAction(self):
        reply = QMessageBox.question(self, 'Onay', "Verileriniz, sohbetleriniz ve 'ai' klasöründeki tüm dosyalar silinecek. Onaylıyor musunuz?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if self.db:
                    self.db.conn.close()
                    self.db = None
                for item in os.listdir(self.temp_dir):
                    p = os.path.join(self.temp_dir, item)
                    if os.path.isdir(p): shutil.rmtree(p)
                    else: os.remove(p)
                
                db_path = os.path.join(self.temp_dir, 'data.db')
                self.db = KavramDB(db_path)
                
                self.chat_page.history.clear()
                self.chat_page.history_index = -1
                self.clearChatAction()
                self.data_page.refreshList()
                self.current_ai_path = None
                QMessageBox.information(self, "Bilgi", "Açık olan tüm veriler ve 'ai' klasörü başarıyla temizlendi.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Temizleme sırasında hata oluştu: {str(e)}")

    def triggerCoreSwitcher(self):
        if self.core_window_ref and hasattr(self.core_window_ref, 'showSwitcher'):
            self.core_window_ref.showSwitcher()

    def saveContent(self):
        if not self.current_ai_path:
            self.exportAIFile()
            return
        try:
            self.pack_ai_file(self.current_ai_path)
            QMessageBox.information(self, "Başarılı", "Dosya başarıyla kaydedildi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydetme hatası: {str(e)}")

    def exportAIFile(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export AI File", self.DEFAULT_BASE_DIR, "AI Files (*.ai)")
        if not file_path: return
        if not file_path.endswith('.ai'): file_path += '.ai'
        self.current_ai_path = file_path
        try:
            self.pack_ai_file(file_path)
            QMessageBox.information(self, "Başarılı", "Dosya başarıyla dışa aktarıldı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dışa aktarma hatası: {str(e)}")

    def pack_ai_file(self, target_path):
        if not self.db: return
        
        used_files = set()
        for _, _, definition in self.db.get_all_packets():
            medias = re.findall(r'\[(?:AUDIO|IMAGE|VIDEO|FILE):(.+?)\]', definition)
            used_files.update(medias)
            
        with tarfile.open(target_path, "w:xz") as tar:
            db_path = os.path.join(self.temp_dir, "data.db")
            if os.path.exists(db_path):
                tar.add(db_path, arcname="data.db")
            for media_file in used_files:
                media_path = os.path.join(self.temp_dir, media_file)
                if os.path.exists(media_path):
                    tar.add(media_path, arcname=media_file)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AiEditorWindow()
    window.show()
    sys.exit(app.exec_())
