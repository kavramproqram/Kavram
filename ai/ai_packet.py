# Kavram AI Editörü — paket editörü ve veri yönetimi sayfası
# Kavram 2.2.2 | GNU GPL v3 veya üstü (ayrıntı: ai.py başlığı ve /Kavram/License/GPLv3.txt)

import os
import re
import shutil

from PyQt5.QtCore import QEvent, Qt, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QAction, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMenu,
    QMessageBox, QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget
)

from ai_media import (
    AudioPlayerWidget, FileAttachmentWidget, ImageThumbnailWidget, VideoThumbnailWidget
)
from ai_common import MAX_MEDIA_PER_PACKET, same_file_content

# ---- Kavram File / Export penceresi (file_manager) -------------------------------
# Kavram çekirdeğinden çalışırken "kavram_file_manager" adıyla yüklenir; program tek başına
# çalıştırılırsa kardeş klasördeki file_manager/file_manager.py doğrudan yüklenir.  Hiçbiri
# olmazsa Qt'nin kendi diyaloğuna dönülür (program asla dosya seçemeden kalmaz).
try:
    import kavram_file_manager as _fm
except Exception:
    try:
        import importlib.util as _ilu
        import os as _fm_os
        import sys as _fm_sys
        _fm_yol = _fm_os.path.join(_fm_os.path.dirname(_fm_os.path.abspath(__file__)), "..", "file_manager", "file_manager.py")
        _fm_spec = _ilu.spec_from_file_location("kavram_file_manager", _fm_yol)
        _fm = _ilu.module_from_spec(_fm_spec)
        _fm_sys.modules["kavram_file_manager"] = _fm
        _fm_spec.loader.exec_module(_fm)
    except Exception:
        from PyQt5.QtWidgets import QFileDialog as _QFD

        class _fm:  # yedek: Qt diyaloğu
            ALL_FILES_LABEL = "Bütün Dosyalar (*)"

            @staticmethod
            def get_open_file_name(parent=None, caption="", directory="", filter="", initialFilter="",
                                   options=None, **_kw):
                return _QFD.getOpenFileName(parent, caption, directory, filter)

            @staticmethod
            def get_open_file_names(parent=None, caption="", directory="", filter="", initialFilter="",
                                    options=None, **_kw):
                return _QFD.getOpenFileNames(parent, caption, directory, filter)

            @staticmethod
            def get_save_file_name(parent=None, caption="", directory="", filter="", initialFilter="",
                                   options=None, **_kw):
                return _QFD.getSaveFileName(parent, caption, directory, filter)

            @staticmethod
            def get_existing_directory(parent=None, caption="", directory="", options=None, **_kw):
                return _QFD.getExistingDirectory(parent, caption, directory)

            @staticmethod
            def notify_saved(parent=None, text="Dosya kaydedildi.", msec=400):
                print(text)
# -----------------------------------------------------------------------------------



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
        self.active_layout.setContentsMargins(0, 0, 0, 0)
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
        filepaths, _ = _fm.get_open_file_names(self, "Medyaları Seç", self.parent_panel.parent_window.DEFAULT_BASE_DIR, filters, double_click="select")
        if filepaths:
            self.process_added_files(filepaths)

    def add_generic_file_action_triggered(self):
        filepaths, _ = _fm.get_open_file_names(self, "Dosyaları Seç", self.parent_panel.parent_window.DEFAULT_BASE_DIR, "Tüm Dosyalar (*)", double_click="select")
        if filepaths:
            self.process_added_files(filepaths, force_file_type=True)

    def process_added_files(self, filepaths, force_file_type=False):
        total_current_count = len(self.media_files)
        added_any = False
        excess_total_flag = False
        
        for filepath in filepaths:
            if total_current_count >= MAX_MEDIA_PER_PACKET:
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
                if os.path.exists(dest_path) and not same_file_content(filepath, dest_path):
                    name, extension = os.path.splitext(filename)
                    counter = 1
                    while True:
                        new_filename = f"{name}{counter}{extension}"
                        new_dest_path = os.path.join(self.parent_panel.parent_window.temp_dir, new_filename)
                        if not os.path.exists(new_dest_path) or same_file_content(filepath, new_dest_path):
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
            QMessageBox.warning(self, "Sınır Uyarısı", f"Bir paket içerisine toplam en fazla {MAX_MEDIA_PER_PACKET} adet dosya eklenebilir. Dosyaların bazılarını silerek boş yer açabilirsiniz.")

    def add_text_file_action_triggered(self):
        filepath, _ = _fm.get_open_file_name(self, "Metin Seç", self.parent_panel.parent_window.DEFAULT_BASE_DIR, "Metin Dosyaları (*.txt);;Tüm Dosyalar (*)", double_click="select")
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
