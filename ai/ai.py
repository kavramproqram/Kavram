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

# --- kavram yol ayarı (otomatik; klasör yapısı: kavram/<program>/<program>.py) ---
import os as _os
_PROGRAM_DIR = _os.path.dirname(_os.path.abspath(__file__))
_KAVRAM_DIR = _os.environ.get("KAVRAM_DIR") or _os.path.dirname(_PROGRAM_DIR)
_KAVRAM_EXPORT_DIR = _os.path.join(_KAVRAM_DIR, "export")
# -------------------------------------------------------------------------------

# modül klasörünü yola ekle (ai_*.py dosyaları ai.py ile aynı klasörde durur)
import sys as _sys
if _PROGRAM_DIR not in _sys.path:
    _sys.path.insert(0, _PROGRAM_DIR)
# -------------------------------------------------------------------------------

import json
import os
import re
import shutil
import sys

from PyQt5.QtCore import QEvent, QSettings, Qt
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLineEdit, QMessageBox, QProgressDialog,
    QPushButton, QStackedWidget, QTextEdit, QVBoxLayout, QWidget
)

from ai_media import AudioPlayerWidget
from ai_chat import ChatPanel
from ai_packet import DataManagementPage, FontSelectorWidget, PacketWidget
from ai_db import KavramDB
from ai_overlay import MediaOverlay
from ai_common import QMediaPlayer, SVG_SAVE_ICON, SVG_X_ICON, create_svg_icon
from ai_archive import install_staged, pack_ai_archive, stage_ai_archive

# Geriye dönük uyumluluk: eskiden ai.py içinde tanımlı olan adlar buradan da içe aktarılabilir.
from ai_text import (  # noqa: F401
    normalize_text
)
from ai_db import (  # noqa: F401
    KavramDB, NORMALIZE_VERSION
)
from ai_common import (  # noqa: F401
    MAX_MEDIA_PER_PACKET, QGraphicsVideoItem, QMediaContent, QMediaPlayer,
    QT_MULTIMEDIA_AVAILABLE, QVideoWidget, SVG_FILE_ICON, SVG_IMAGE_ICON, SVG_PAUSE_ICON,
    SVG_PLAY_ICON, SVG_SAVE_ICON, SVG_X_ICON, create_svg_icon, same_file_content
)
from ai_media import (  # noqa: F401
    AudioPlayerWidget, FileAttachmentWidget, ImageThumbnailWidget, VideoThumbnailWidget,
    WaveformSlider
)
from ai_overlay import (  # noqa: F401
    MediaGraphicsView, MediaOverlay
)
from ai_packet import (  # noqa: F401
    AutoResizingTextEdit, DataManagementPage, FontSelectorWidget, PacketWidget
)
from ai_chat import (  # noqa: F401
    ChatPanel
)

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



class AiEditorWindow(QWidget):
    DEFAULT_BASE_DIR = _KAVRAM_EXPORT_DIR

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
        self.settings = QSettings("kavram", "AiEditor")
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
        toolbar_layout.setSpacing(10)
        
        self.file_button = QPushButton("File")
        self.file_button.setStyleSheet(self.topBarStyle())
        self.file_button.setFixedSize(90, 30)
        self.file_button.clicked.connect(self.openFiles)
        
        self.save_button = QPushButton()
        self.save_button.setIcon(create_svg_icon(SVG_SAVE_ICON, size=20, color="#ffffff"))
        self.save_button.setStyleSheet(self.buttonStyleMini())
        self.save_button.setFixedSize(30, 30)
        self.save_button.setToolTip("Kaydet")
        self.save_button.clicked.connect(self.saveContent)
        
        self.new_button = QPushButton("New")
        self.new_button.setStyleSheet(self.topBarStyle())
        self.new_button.setFixedSize(90, 30)
        self.new_button.clicked.connect(self.createNewPacketAction)
        
        self.chat_button = QPushButton("Chat")
        self.chat_button.setStyleSheet(self.topBarStyle())
        self.chat_button.setFixedSize(90, 30)
        self.chat_button.clicked.connect(self.showChatPanel)
        
        self.edit_button = QPushButton("Edit")
        self.edit_button.setStyleSheet(self.topBarStyle())
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
        self.export_button.setStyleSheet(self.topBarStyle())
        self.export_button.setFixedSize(90, 30)
        self.export_button.clicked.connect(self.exportAIFile)
        toolbar_layout.addWidget(self.export_button, alignment=Qt.AlignRight)
        
        self.ai_button = QPushButton("Ai")
        self.ai_button.setStyleSheet(self.topBarStyle())
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
        self.media_overlay.setGeometry(self.stack.geometry())
        self.media_overlay.set_context(filepath, context_source)
        self.media_overlay.set_media(filepath, is_video)
        self.media_overlay.show()
        self.media_overlay.setFocus()

    def close_media_overlay(self):
        if hasattr(self, 'media_overlay'):
            self.media_overlay.close_overlay()

    def topBarStyle(self):
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 14px; font-weight: bold;
                border: 2px solid #555; border-radius: 8px; padding: 5px 10px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

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
        file_paths, _ = _fm.get_open_file_names(
            self, "Open Files", self.DEFAULT_BASE_DIR,
            "AI Files (*.ai);;All Files (*)", options=options
        , editor="Ai")
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
                    
                    progress = QProgressDialog("AI Dosyası Yükleniyor...", "İptal", 0, 0, self)
                    progress.setWindowTitle("Lütfen Bekleyin")
                    progress.setWindowModality(Qt.WindowModal)
                    progress.setCancelButton(None)
                    progress.show()
                    QApplication.processEvents()

                    staging = stage_ai_archive(file_path, os.path.dirname(self.temp_dir))
                    try:
                        if self.db:
                            self.db.close()
                            self.db = None
                        install_staged(staging, self.temp_dir)
                    finally:
                        shutil.rmtree(staging, ignore_errors=True)
                    
                    db_path = os.path.join(self.temp_dir, 'data.db')
                    json_path = os.path.join(self.temp_dir, 'data.json')
                    
                    self.db = KavramDB(db_path)
                    
                    if os.path.exists(json_path):
                        with open(json_path, "r", encoding="utf-8") as f:
                            loaded_dict = json.load(f)
                        self.db.migrate_from_dict(loaded_dict)
                        os.remove(json_path)

                    self.chat_page.sync_history_with_dict()
                    self.current_ai_path = file_path
                    
                    progress.close()
                    
                    self.stack.setCurrentWidget(self.chat_page)
                    return
                except Exception as e:
                    if 'progress' in locals():
                        progress.close()
                    if self.db is None:
                        try:
                            self.db = KavramDB(os.path.join(self.temp_dir, 'data.db'))
                            self.chat_page.sync_history_with_dict()
                        except Exception:
                            pass
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
            _fm.notify_saved(self)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kaydetme hatası: {str(e)}")

    def exportAIFile(self):
        file_path, _ = _fm.get_save_file_name(self, "Export AI File", self.DEFAULT_BASE_DIR, "AI Files (*.ai)", editor="Ai")
        if not file_path: return
        if not file_path.endswith('.ai'): file_path += '.ai'
        self.current_ai_path = file_path
        try:
            self.pack_ai_file(file_path)
            _fm.notify_saved(self)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dışa aktarma hatası: {str(e)}")

    def pack_ai_file(self, target_path):
        if not self.db: return
        self.db.conn.commit()
        
        used_files = set()
        for _, _, definition in self.db.get_all_packets():
            medias = re.findall(r'\[(?:AUDIO|IMAGE|VIDEO|FILE):(.+?)\]', definition)
            used_files.update(medias)
            
        db_path = os.path.join(self.temp_dir, "data.db")
        files_to_pack = []
        if os.path.exists(db_path):
            files_to_pack.append(("data.db", db_path))
            
        for media_file in used_files:
            media_path = os.path.join(self.temp_dir, media_file)
            if os.path.exists(media_path):
                files_to_pack.append((media_file, media_path))

        total_files = len(files_to_pack)
        
        progress = QProgressDialog("AI Dosyası Dışa Aktarılıyor...", "İptal", 0, total_files, self)
        progress.setWindowTitle("Lütfen Bekleyin")
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None)
        progress.show()

        def _on_progress(idx):
            progress.setValue(idx)
            QApplication.processEvents()

        try:
            # Önce geçici dosyaya yazılır, bitince hedefin yerine geçer (yarım kalan kayıt dosyayı bozmaz)
            pack_ai_archive(target_path, files_to_pack, _on_progress)
            progress.setValue(total_files)
        finally:
            progress.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AiEditorWindow()
    window.show()
    sys.exit(app.exec_())
