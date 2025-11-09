# Kavram 1.0.0
# Copyright (C) 2025-10-23 Kavram or Contributors
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
# Copyright (C) 2025-10-23 Kavram veya Contributors
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
import importlib
from PyQt5.QtWidgets import (
    QApplication, QWidget, QStackedWidget, QVBoxLayout, QDialog,
    QListWidget, QListWidgetItem, QLabel, QMessageBox
)
from PyQt5.QtGui import QCursor, QIcon
from PyQt5.QtCore import Qt, QTimer
import lupa

# --- GÜNCELLENMİŞ FONKSİYON ---
# Bu fonksiyon, programın hem normal çalışırken, hem PyInstaller ile paketlendiğinde,
# hem de AppImage olarak paketlendiğinde doğru dosya yolunu bulmasını sağlar.
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev, PyInstaller, and AppImage """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstaller geçici bir klasör oluşturur ve yolu _MEIPASS içinde saklar
        base_path = sys._MEIPASS
    elif 'APPDIR' in os.environ:
        # AppImage, programı bağlı bir dizinden çalıştırır ve yol APPDIR ortam değişkenindedir.
        # Genellikle varlıklar 'usr/bin' altında olur.
        base_path = os.path.join(os.environ['APPDIR'], 'usr/bin')
    else:
        # Paketlenmemiş, normal bir ortamda çalışıyor
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
# --- GÜNCELLEME SONU ---

# Lua motorunu ve betiğini uygulamaya dahil etmek için bir fonksiyon
def initialize_lua_engine():
    lua_file_path = resource_path('timeline_logic.lua')

    try:
        global lua_runtime
        lua_runtime = lupa.LuaRuntime()
        with open(lua_file_path, 'r', encoding='utf-8') as f:
            lua_runtime.execute(f.read())
        print("Lua timeline_logic.lua successfully loaded.")
        return lua_runtime
    except FileNotFoundError:
        print(f"Error: timeline_logic.lua not found at {lua_file_path}")
        QMessageBox.critical(None, "Hata", f"timeline_logic.lua dosyası bulunamadı. Lütfen dosyanın uygulamanızla birlikte paketlendiğinden emin olun.")
        sys.exit(1)
    except lupa.LuaError as e:
        print(f"Lua execution error: {e}")
        QMessageBox.critical(None, "Hata", f"Lua motorunu başlatırken bir hata oluştu: {e}")
        sys.exit(1)


# CameraRecorderWindow ile birlikte yeni kütüphane yükleme fonksiyonunu da import ediyoruz
# Not: Bu import, camera_editor.py'nin de resource_path'e erişimi olmasını sağlar.
from camera_editor import load_cpp_library

class EditorSwitcherDialog(QDialog):
    # ... (Bu sınıfın içeriği olduğu gibi kalıyor, değişiklik yok) ...
    def __init__(self, editor_names, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Editör Seçimi")

        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                border: 2px solid #555;
                border-radius: 8px;
            }
            QPushButton, QToolButton {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 14px;
            }
            QPushButton:hover, QToolButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed, QToolButton:pressed {
                background-color: #777777;
            }
            QListWidget {
                background-color: #3a3a3a;
                color: #ffffff;
                border: none;
                padding: 10px;
                font-size: 16px;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:hover {
                background-color: #555555;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background-color: #777777;
                color: #ffffff;
            }
        """)

        self.editor_names = editor_names
        self.selected_name = None
        self.initUI()

    def acceptSelection(self):
        items = self.list_widget.selectedItems()
        if items:
            self.selected_name = items[0].text()
        self.accept()

    def initUI(self, *args, **kwargs):
        from PyQt5.QtWidgets import QVBoxLayout
        layout = QVBoxLayout()
        self.list_widget = QListWidget()

        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        for name in self.editor_names:
            item = QListWidgetItem(name)
            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)
        self.setLayout(layout)

        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)

        item_height = self.list_widget.sizeHintForRow(0)
        if item_height <= 0:
            item_height = 32

        list_content_height = len(self.editor_names) * item_height + (self.list_widget.contentsMargins().top() + self.list_widget.contentsMargins().bottom()) + self.list_widget.frameWidth() * 2

        dialog_height = list_content_height + (layout.contentsMargins().top() + layout.contentsMargins().bottom()) + self.frameGeometry().height() - self.geometry().height()

        screen_geometry = QApplication.primaryScreen().geometry()
        max_dialog_height = screen_geometry.height() * 0.8

        final_height = min(dialog_height, max_dialog_height)

        self.resize(240, final_height)

        mouse_pos = QCursor.pos()

        x = mouse_pos.x()
        y = mouse_pos.y()

        if x + self.width() > screen_geometry.right():
            x = screen_geometry.right() - self.width()
        if y + self.height() > screen_geometry.bottom():
            y = screen_geometry.bottom() - self.height()
        if x < screen_geometry.left():
            x = screen_geometry.left()
        if y < screen_geometry.top():
            y = screen_geometry.top()

        self.move(x, y)

        print(f"DEBUG: EditorSwitcherDialog initUI: has acceptSelection: {hasattr(self, 'acceptSelection')}")
        self.list_widget.itemClicked.connect(self.acceptSelection)

    def mousePressEvent(self, event):
        if not self.rect().contains(event.pos()):
            self.reject()
        super().mousePressEvent(event)


class CoreWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kavram")

        # --- İkon yolu zaten resource_path ile güncellenmiş, bu şekilde kalmalı ---
        self.setWindowIcon(QIcon(resource_path('ikon/Kavram.png')))

        self.setStyleSheet("""
            QWidget {
                background-color: #222;
                color: #fff;
                border: none;
            }
            QStackedWidget {
                background-color: #222;
                border: none;
            }
            QPushButton, QToolButton {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover, QToolButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed, QToolButton:pressed {
                background-color: #777777;
            }
        """)

        self.editors_order = [
            "Sphere", "Text", "Drawing", "Sound", "Ai", "Media", "Rec", "Copy", "Settings", "Filter", "Convert"
        ]

        self.editor_map = {
            "Sphere": "sphere.SphereWindow",
            "Text": "text_editor.TextEditorWindow",
            "Drawing": "Drawing_editor.DrawingEditorWindow",
            "Sound": "sound_GUI.SoundEditorWindow",
            "Ai": "ai_editor.AiEditorWindow",
            "Media": "media_editor.MediaEditor",
            "Rec": "camera_editor.CameraRecorderWindow",
            "Copy": "copya.MainWindow",
            "Settings": "Settings.SettingsWindow",
            "Filter": "filtre.AudioCleanerUI",
            "Convert": "convert.UniversalConverter"
        }

        self.stack = QStackedWidget()
        self.instantiated_editors = {}
        self.editor_indices = {}
        self.settings_window_instance = None
        self.filter_window_instance = None
        self.convert_window_instance = None

        # Sadece başlangıç ekranı olan Sphere'ı önceden yüklüyoruz.
        module = __import__("sphere", fromlist=["SphereWindow"])
        SphereWindow = getattr(module, "SphereWindow")
        sphere_editor_instance = SphereWindow(core_window_ref=self)
        sphere_idx = self.stack.addWidget(sphere_editor_instance)
        self.instantiated_editors["Sphere"] = sphere_editor_instance
        self.editor_indices["Sphere"] = sphere_idx

        self.stack.setCurrentIndex(sphere_idx)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

        self.showMaximized()

    def switchToEditor(self, editor_name, close_current=False):
        current_widget = self.stack.currentWidget()
        current_editor_name = None
        for name, widget_instance in self.instantiated_editors.items():
            if widget_instance == current_widget:
                current_editor_name = name
                break

        if close_current and current_editor_name and current_editor_name != editor_name and current_editor_name != "Settings" and current_editor_name != "Filter" and current_editor_name != "Convert":
            if hasattr(current_widget, 'save_state_to_temp_file'):
                current_widget.save_state_to_temp_file()

            self.stack.removeWidget(current_widget)
            del self.instantiated_editors[current_editor_name]
            del self.editor_indices[current_editor_name]
            current_widget.deleteLater()
            print(f"'{current_editor_name}' editörü kapatıldı ve hafızadan temizlendi.")

        if editor_name == "Settings":
            if not self.settings_window_instance:
                module = importlib.import_module("Settings")
                SettingsWindow = getattr(module, "Settings")
                self.settings_window_instance = SettingsWindow()
            self.settings_window_instance.showNormal()
            self.settings_window_instance.activateWindow()
        elif editor_name == "Filter":
            if not self.filter_window_instance:
                module = importlib.import_module("filtre")
                AudioCleanerUI = getattr(module, "AudioCleanerUI")
                self.filter_window_instance = AudioCleanerUI()
            self.filter_window_instance.showNormal()
            self.filter_window_instance.activateWindow()
        elif editor_name == "Convert":
            if not self.convert_window_instance:
                module = importlib.import_module("convert")
                UniversalConverter = getattr(module, "UniversalConverter")
                self.convert_window_instance = UniversalConverter()
            self.convert_window_instance.showNormal()
            self.convert_window_instance.activateWindow()
        elif editor_name in self.instantiated_editors:
            idx = self.editor_indices[editor_name]
            self.stack.setCurrentIndex(idx)
            self.instantiated_editors[editor_name].showMaximized()
        else:
            try:
                module_path, class_name = self.editor_map.get(editor_name).rsplit('.', 1)
                module = importlib.import_module(module_path)
                editor_class = getattr(module, class_name)
            except (ImportError, AttributeError, ValueError) as e:
                print(f"Hata: '{editor_name}' için editör sınıfı bulunamadı. Detay: {e}")
                QMessageBox.critical(self, "Hata", f"'{editor_name}' editörünü yüklerken bir hata oluştu.")
                return

            if editor_name in ["Sphere", "Text", "Ai", "Sound", "Media", "Rec", "Copy"]:
                w = editor_class(core_window_ref=self)
            else:
                w = editor_class()

            idx = self.stack.addWidget(w)
            self.instantiated_editors[editor_name] = w
            self.editor_indices[editor_name] = idx
            self.stack.setCurrentIndex(idx)
            w.showMaximized()
            if hasattr(w, 'load_state_from_temp_file'):
                w.load_state_from_temp_file()

        self.setWindowTitle("Kavram")

        if editor_name in self.editors_order and editor_name not in ["Settings", "Filter", "Convert"]:
            self.editors_order.remove(editor_name)
            self.editors_order.insert(0, editor_name)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_S and (event.modifiers() & Qt.ControlModifier):
            self.switchToEditor("Sphere", close_current=True)
            event.accept()
        elif event.key() == Qt.Key_S and (event.modifiers() & Qt.MetaModifier):
            self.switchToEditor("Sphere", close_current=True)
            event.accept()
        elif event.key() == Qt.Key_Q and (event.modifiers() & Qt.ControlModifier):
            self.showSwitcher()
            event.accept()
        elif event.key() == Qt.Key_Q and (event.modifiers() & Qt.ControlModifier and event.modifiers() & Qt.AltModifier):
            # Yeni eklenen IDE listesini açar.
            self.showIdeSwitcher()
            event.accept()
        else:
            super().keyPressEvent(event)

    def showSwitcher(self):
        editor_list = [name for name in self.editors_order]
        dlg = EditorSwitcherDialog(editor_list, self)
        if dlg.exec_() == QDialog.Accepted:
            selected = dlg.selected_name
            if selected:
                self.switchToEditor(selected, close_current=False)

    def showIdeSwitcher(self):
        try:
            from IDE_switcher import IDE_Switcher
            self.ide_switcher_dialog = IDE_Switcher(core_window_ref=self)
            self.ide_switcher_dialog.show()
        except ImportError as e:
            QMessageBox.critical(self, "Hata", f"IDE_switcher.py dosyası bulunamadı. Detay: {e}")


    def loadEditorFile(self, editor_name, file_path):
        print(f"DEBUG: CoreWindow.loadEditorFile called. editor_name: {editor_name}, file_path: {file_path}")
        if editor_name == "Drawing":
            if "Drawing" in self.instantiated_editors:
                current_drawing_editor = self.instantiated_editors["Drawing"]
                self.stack.removeWidget(current_drawing_editor)
                del self.instantiated_editors["Drawing"]
                del self.editor_indices["Drawing"]
                current_drawing_editor.deleteLater()
                print("DEBUG: Mevcut Drawing editörü kapatıldı.")

            from Drawing_editor import DrawingEditorWindow
            drawing_editor = DrawingEditorWindow()
            idx = self.stack.addWidget(drawing_editor)
            self.instantiated_editors[editor_name] = drawing_editor
            self.editor_indices[editor_name] = idx

            self.stack.setCurrentWidget(drawing_editor)
            drawing_editor.showMaximized()

            QTimer.singleShot(0, lambda: drawing_editor.load_image_from_path(file_path))

            self.setWindowTitle("Kavram")
            print(f"DEBUG: Drawing editörü yüklendi ve dosya {file_path} için hazırlandı.")
        elif editor_name == "Text":
            print("DEBUG: Text editörü için dosya yükleme bloğuna girildi.")
            if "Text" in self.instantiated_editors:
                current_text_editor = self.instantiated_editors["Text"]
                self.stack.removeWidget(current_text_editor)
                del self.instantiated_editors["Text"]
                del self.editor_indices["Text"]
                current_text_editor.deleteLater()
                print("DEBUG: Mevcut Text editörü kapatıldı.")

            from text_editor import TextEditorWindow
            text_editor = TextEditorWindow(core_window_ref=self)
            idx = self.stack.addWidget(text_editor)
            self.instantiated_editors[editor_name] = text_editor
            self.editor_indices[editor_name] = idx

            self.stack.setCurrentWidget(text_editor)
            text_editor.showMaximized()

            QTimer.singleShot(0, lambda: text_editor.load_file_content(file_path))

            self.setWindowTitle("Kavram")
            print(f"DEBUG: Text editörü yüklendi ve dosya {file_path} için hazırlandı.")
        elif editor_name == "Ai":
            print("DEBUG: Ai editörü için dosya yükleme bloğuna girildi.")
            if "Ai" in self.instantiated_editors:
                current_ai_editor = self.instantiated_editors["Ai"]
                self.stack.removeWidget(current_ai_editor)
                del self.instantiated_editors["Ai"]
                del self.editor_indices["Ai"]
                current_ai_editor.deleteLater()
                print("DEBUG: Mevcut Ai editörü kapatıldı.")

            from ai_editor import AiEditorWindow
            ai_editor = AiEditorWindow(core_window_ref=self)
            idx = self.stack.addWidget(ai_editor)
            self.instantiated_editors[editor_name] = ai_editor
            self.editor_indices[editor_name] = idx

            self.stack.setCurrentWidget(ai_editor)
            ai_editor.showMaximized()

            QTimer.singleShot(0, lambda: ai_editor.openFiles_from_path([file_path]))

            self.setWindowTitle("Kavram")
            print(f"DEBUG: Ai editörü yüklendi ve dosya {file_path} için hazırlandı.")
        elif editor_name == "Sound":
            print("DEBUG: Sound editörü için dosya yükleme bloğuna girildi.")
            if "Sound" in self.instantiated_editors:
                current_sound_editor = self.instantiated_editors["Sound"]
                self.stack.removeWidget(current_sound_editor)
                del self.instantiated_editors["Sound"]
                del self.editor_indices["Sound"]
                current_sound_editor.deleteLater()
                print("DEBUG: Mevcut Sound editörü kapatıldı.")

            from sound_GUI import SoundEditorWindow
            sound_editor = SoundEditorWindow(core_window_ref=self)
            idx = self.stack.addWidget(sound_editor)
            self.instantiated_editors[editor_name] = sound_editor
            self.editor_indices[editor_name] = idx

            self.stack.setCurrentWidget(sound_editor)
            sound_editor.showMaximized()

            QTimer.singleShot(0, lambda: sound_editor.load_files_from_path([file_path]))

            self.setWindowTitle("Kavram")
            print(f"DEBUG: Sound editörü yüklendi ve dosya {file_path} için hazırlandı.")
        elif editor_name == "Media":
            print("DEBUG: Media editörü için dosya yükleme bloğuna girildi.")
            if "Media" in self.instantiated_editors:
                current_media_editor = self.instantiated_editors["Media"]
                self.stack.removeWidget(current_media_editor)
                del self.instantiated_editors["Media"]
                del self.editor_indices["Media"]
                current_media_editor.deleteLater()
                print("DEBUG: Mevcut Media editörü kapatıldı.")

            from media_editor import MediaEditor
            media_editor = MediaEditor(core_window_ref=self)
            idx = self.stack.addWidget(media_editor)
            self.instantiated_editors[editor_name] = media_editor
            self.editor_indices[editor_name] = idx

            self.stack.setCurrentWidget(media_editor)
            media_editor.showMaximized()

            QTimer.singleShot(0, lambda: media_editor.load_file(file_path))

            self.setWindowTitle("Kavram")
            print(f"DEBUG: Media editörü yüklendi ve dosya {file_path} için hazırlandı.")
        elif editor_name == "Rec":
            print("DEBUG: Rec editörü için dosya yükleme bloğuna girildi.")
            if "Rec" in self.instantiated_editors:
                current_rec_editor = self.instantiated_editors["Rec"]
                self.stack.removeWidget(current_rec_editor)
                del self.instantiated_editors["Rec"]
                del self.editor_indices["Rec"]
                current_rec_editor.deleteLater()
                print("DEBUG: Mevcut Rec editörü kapatıldı.")

            from camera_editor import CameraRecorderWindow
            rec_editor = CameraRecorderWindow(core_window_ref=self)
            idx = self.stack.addWidget(rec_editor)
            self.instantiated_editors[editor_name] = rec_editor
            self.editor_indices[editor_name] = idx

            self.stack.setCurrentWidget(rec_editor)
            rec_editor.showMaximized()

            QTimer.singleShot(0, lambda: rec_editor.load_file(file_path))

            self.setWindowTitle("Kavram")
            print(f"DEBUG: Rec editörü yüklendi ve dosya {file_path} için hazırlandı.")
        elif editor_name == "Copy":
            print("DEBUG: Copy editörü için dosya yükleme bloğuna girildi.")
            if "Copy" in self.instantiated_editors:
                current_copy_editor = self.instantiated_editors["Copy"]
                self.stack.removeWidget(current_copy_editor)
                del self.instantiated_editors["Copy"]
                del self.editor_indices["Copy"]
                current_copy_editor.deleteLater()
                print("DEBUG: Mevcut Copy editörü kapatıldı.")

            from copya import MainWindow
            copy_editor = MainWindow(core_window_ref=self)
            idx = self.stack.addWidget(copy_editor)
            self.instantiated_editors[editor_name] = copy_editor
            self.editor_indices[editor_name] = idx

            self.stack.setCurrentWidget(copy_editor)
            copy_editor.showMaximized()

            QTimer.singleShot(0, lambda: copy_editor.load_copya(file_path))

            self.setWindowTitle("Kavram")
            print(f"DEBUG: Copy editörü yüklendi ve dosya {file_path} için hazırlandı.")
        else:
            print(f"DEBUG: loadEditorFile: Desteklenmeyen editör adı: {editor_name}")
            QMessageBox.information(self, "Bilgi", f"'{editor_name}' editörü için dosya yükleme desteklenmiyor.")
            self.switchToEditor(editor_name)

    def ensureEditorInstantiated(self, editor_name):
        pass

    def closeEvent(self, event):
        if self.settings_window_instance and self.settings_window_instance.isVisible():
            self.settings_window_instance.close()
        if self.filter_window_instance and self.filter_window_instance.isVisible():
            self.filter_window_instance.close()
        if self.convert_window_instance and self.convert_window_instance.isVisible():
            self.convert_window_instance.close()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Kavram")

    # Uygulama başlangıcında C++ kütüphanesini ve Lua motorunu yükle
    load_cpp_library()
    initialize_lua_engine()

    window = CoreWindow()
    window.show()
    sys.exit(app.exec_())
