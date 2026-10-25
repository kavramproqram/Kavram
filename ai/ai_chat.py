# Kavram AI Editörü — sohbet paneli
# Kavram 2.2.2 | GNU GPL v3 veya üstü (ayrıntı: ai.py başlığı ve /Kavram/License/GPLv3.txt)

import os
import re

from PyQt5.QtCore import QEvent, QTimer, Qt
from PyQt5.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget
)

from ai_media import (
    AudioPlayerWidget, FileAttachmentWidget, ImageThumbnailWidget, VideoThumbnailWidget
)


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
        if not answers:
            suggestions = self.parent_window.db.suggest_words(word)
            if suggestions:
                return "Bilmiyorum\n\nBunu mu demek istediniz: " + ", ".join(suggestions) + "?"
            return "Bilmiyorum"
        unique_answers = list(set(answers))
        unique_answers.sort(key=len)
        return "\n\n".join(unique_answers)
