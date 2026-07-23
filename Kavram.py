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
import signal
import importlib
import json          # Özel editörler için
import subprocess    # Program başlatmak için
from PyQt5.QtWidgets import (
    QApplication, QWidget, QStackedWidget, QVBoxLayout, QDialog,
    QListWidget, QListWidgetItem, QLabel, QMessageBox, QMenu
)
from PyQt5.QtGui import QCursor, QIcon
from PyQt5.QtCore import Qt, QTimer
import lupa

# --- GÜNCELLENMİŞ FONKSİYON ---
def resource_path(relative_path):
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    elif 'APPDIR' in os.environ:
        base_path = os.path.join(os.environ['APPDIR'], 'usr/bin')
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Lua motoru (güvenlik yamalı)
def initialize_lua_engine():
    lua_file_path = resource_path('timeline_logic.lua')
    try:
        global lua_runtime
        lua_runtime = lupa.LuaRuntime()
        lua_runtime.execute("os = nil; io = nil; package = nil; require = nil; dofile = nil; loadfile = nil;")
        with open(lua_file_path, 'r', encoding='utf-8') as f:
            lua_runtime.execute(f.read())
        print("Lua timeline_logic.lua successfully loaded and secured.")
        return lua_runtime
    except FileNotFoundError:
        print(f"Error: timeline_logic.lua not found at {lua_file_path}")
        QMessageBox.critical(None, "Hata", f"timeline_logic.lua dosyası bulunamadı.")
        sys.exit(1)
    except lupa.LuaError as e:
        print(f"Lua execution error: {e}")
        QMessageBox.critical(None, "Hata", f"Lua motoru hatası: {e}")
        sys.exit(1)

from camera_editor import load_cpp_library

# ----- DİYALOG (orijinal görünüm + silme menüsü) -----
class EditorSwitcherDialog(QDialog):
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
            QMenu {
                background-color: #2b2b2b;
                border: 1px solid #555;
            }
            QMenu::item {
                color: #ffffff;
                background-color: transparent;
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #555555;
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

    def initUI(self):
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
        self.resize(240, int(final_height))

        mouse_pos = QCursor.pos()
        x, y = mouse_pos.x(), mouse_pos.y()
        if x + self.width() > screen_geometry.right():
            x = screen_geometry.right() - self.width()
        if y + self.height() > screen_geometry.bottom():
            y = screen_geometry.bottom() - self.height()
        if x < screen_geometry.left():
            x = screen_geometry.left()
        if y < screen_geometry.top():
            y = screen_geometry.top()
        self.move(x, y)

        self.list_widget.itemClicked.connect(self.acceptSelection)
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        item = self.list_widget.itemAt(position)
        if not item:
            return
        editor_name = item.text()
        parent = self.parent()
        if parent and hasattr(parent, 'custom_editors'):
            if any(e['name'] == editor_name for e in parent.custom_editors):
                menu = QMenu(self)  # Sistem temasını ezmesi için 'self' parent olarak eklendi
                delete_action = menu.addAction("Sil")
                action = menu.exec_(self.list_widget.mapToGlobal(position))
                if action == delete_action:
                    if parent.remove_custom_editor(editor_name):
                        self.close()

    def refresh_list(self):
        self.list_widget.clear()
        parent = self.parent()
        if parent:
            for name in parent.editors_order:
                self.list_widget.addItem(QListWidgetItem(name))
            # Dialog boyutunu yeniden hesapla (deformasyonu önlemek için)
            self.list_widget.adjustSize()
            item_height = self.list_widget.sizeHintForRow(0)
            if item_height <= 0:
                item_height = 32
            list_content_height = len(parent.editors_order) * item_height + (self.list_widget.contentsMargins().top() + self.list_widget.contentsMargins().bottom()) + self.list_widget.frameWidth() * 2
            dialog_height = list_content_height + (self.layout().contentsMargins().top() + self.layout().contentsMargins().bottom()) + self.frameGeometry().height() - self.geometry().height()
            screen_geometry = QApplication.primaryScreen().geometry()
            max_dialog_height = screen_geometry.height() * 0.8
            final_height = min(dialog_height, max_dialog_height)
            self.resize(240, int(final_height))

    def mousePressEvent(self, event):
        if not self.rect().contains(event.pos()):
            self.reject()
        super().mousePressEvent(event)


# ----- ANA PENCERE -----
class CoreWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kavram")
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

        # ---- SIRALAMA MANTIĞI ----
        self.mru_editor_names = ["Sphere", "Text", "Drawing", "Sound", "Ai", "Media", "Rec", "Copy"]
        self.fixed_base_names = ["Settings", "Filter", "Convert"]
        self.editors_order = self.mru_editor_names.copy() + self.fixed_base_names.copy()

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
        self.settings_window_instance = None
        self.filter_window_instance = None
        self.convert_window_instance = None

        self.media_filter_connection_active = False
        self.is_filtering_in_progress = False

        self.custom_editors = []
        self.load_custom_editors()

        # Sphere başlangıç
        module = __import__("sphere", fromlist=["SphereWindow"])
        SphereWindow = getattr(module, "SphereWindow")
        sphere_editor_instance = SphereWindow(core_window_ref=self)
        self.stack.addWidget(sphere_editor_instance)
        self.instantiated_editors["Sphere"] = sphere_editor_instance
        self.stack.setCurrentWidget(sphere_editor_instance)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

        self.showMaximized()
        self.force_close = False
        self.spawned_external_processes = []

    # ----- ÖZEL EDİTÖR YÖNETİMİ -----
    def get_custom_editors_dir(self):
        base = resource_path('veri')
        custom_dir = os.path.join(base, 'custom_editors')
        os.makedirs(custom_dir, exist_ok=True)
        return custom_dir

    def get_custom_editors_json_path(self):
        return os.path.join(self.get_custom_editors_dir(), 'custom_editors.json')

    def load_custom_editors(self):
        json_path = self.get_custom_editors_json_path()
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.custom_editors = data.get('editors', [])
            except Exception as e:
                print(f"Özel editörler yüklenemedi: {e}")
                self.custom_editors = []
        else:
            self.custom_editors = []

        existing_names = set(self.editor_map.keys())
        custom_names = [e['name'] for e in self.custom_editors]
        for name in custom_names:
            if name not in existing_names:
                self.editor_map[name] = 'CUSTOM'

        try:
            settings_idx = self.editors_order.index("Settings")
        except ValueError:
            settings_idx = len(self.editors_order)
        self.editors_order = self.mru_editor_names.copy()
        self.editors_order[settings_idx:settings_idx] = custom_names
        self.editors_order.extend(self.fixed_base_names)

    def save_custom_editors(self):
        json_path = self.get_custom_editors_json_path()
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({'editors': self.custom_editors}, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Özel editörler kaydedilemedi: {e}")

    def add_custom_editor(self, name, executable_path):
        if len(self.custom_editors) >= 9:
            self.show_error_message("En fazla 9 özel editör eklenebilir.")
            return False
        if any(e['name'] == name for e in self.custom_editors):
            self.show_error_message(f"'{name}' zaten var.")
            return False
        self.custom_editors.append({'name': name, 'executable': executable_path})
        self.editor_map[name] = 'CUSTOM'
        try:
            settings_idx = self.editors_order.index("Settings")
        except ValueError:
            settings_idx = len(self.editors_order)
        self.editors_order.insert(settings_idx, name)
        self.save_custom_editors()
        return True

    def remove_custom_editor(self, name):
        editor = next((e for e in self.custom_editors if e['name'] == name), None)
        if not editor:
            return False
        self.cleanup_boxes_for_custom_editor(name)
        exec_path = editor['executable']
        if os.path.exists(exec_path):
            try:
                os.remove(exec_path)
                parent_dir = os.path.dirname(exec_path)
                if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                    os.rmdir(parent_dir)
            except Exception as e:
                print(f"Executable silinemedi: {e}")
        self.custom_editors = [e for e in self.custom_editors if e['name'] != name]
        if name in self.editor_map:
            del self.editor_map[name]
        if name in self.editors_order:
            self.editors_order.remove(name)
        self.save_custom_editors()
        return True

    def get_custom_editor_executable(self, name):
        for e in self.custom_editors:
            if e['name'] == name:
                return e['executable']
        return None

    def cleanup_boxes_for_custom_editor(self, editor_name):
        sphere_window = self.instantiated_editors.get("Sphere")
        if sphere_window and hasattr(sphere_window, 'view'):
            for box in sphere_window.view.boxes:
                if hasattr(box, 'selected_editor_name') and box.selected_editor_name == editor_name:
                    box.selected_editor_name = None
                    box.selected_file_path = None
                    box.select_editor_button.show()
                    box.editor_action_button.hide()
                    box.file_list_widget.hide()
                    box.name_input_area.hide()
                    box.independent_checkbox.hide()

    def show_error_message(self, text):
        QMessageBox.critical(self, "Hata", text)

    # ----- EDİTÖR GEÇİŞ -----
    def switchToEditor(self, editor_name, close_current=False):
        if editor_name in self.editor_map and self.editor_map[editor_name] == 'CUSTOM':
            executable = self.get_custom_editor_executable(editor_name)
            if executable and os.path.exists(executable):
                try:
                    process = subprocess.Popen([executable], start_new_session=True)
                    self.spawned_external_processes.append(process)
                except Exception as e:
                    QMessageBox.warning(self, "Hata", f"Program başlatılamadı: {e}")
            else:
                QMessageBox.warning(self, "Hata", f"'{editor_name}' executable'ı bulunamadı.")
            return

        current_widget = self.stack.currentWidget()
        current_editor_name = None
        for name, widget_instance in self.instantiated_editors.items():
            if widget_instance == current_widget:
                current_editor_name = name
                break

        if close_current and current_editor_name and current_editor_name != editor_name and current_editor_name not in ["Settings", "Filter", "Convert"]:
            if hasattr(current_widget, 'save_state_to_temp_file'):
                current_widget.save_state_to_temp_file()
            self.stack.removeWidget(current_widget)
            del self.instantiated_editors[current_editor_name]
            current_widget.deleteLater()
            print(f"'{current_editor_name}' editörü kapatıldı.")

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
            self.stack.setCurrentWidget(self.instantiated_editors[editor_name])
            self.instantiated_editors[editor_name].showMaximized()
        else:
            try:
                module_path, class_name = self.editor_map.get(editor_name).rsplit('.', 1)
                module = importlib.import_module(module_path)
                editor_class = getattr(module, class_name)
            except (ImportError, AttributeError, ValueError) as e:
                print(f"Hata: {e}")
                QMessageBox.critical(self, "Hata", f"'{editor_name}' yüklenemedi.")
                return

            if editor_name in ["Sphere", "Text", "Ai", "Sound", "Media", "Rec", "Copy"]:
                w = editor_class(core_window_ref=self)
            else:
                w = editor_class()

            self.stack.addWidget(w)
            self.instantiated_editors[editor_name] = w
            self.stack.setCurrentWidget(w)
            w.showMaximized()
            if hasattr(w, 'load_state_from_temp_file'):
                w.load_state_from_temp_file()

        self.setWindowTitle("Kavram")

        # MRU sıralama (sadece hareketli editörler)
        if editor_name in self.mru_editor_names:
            if editor_name in self.editors_order:
                self.editors_order.remove(editor_name)
            self.editors_order.insert(0, editor_name)

    # ----- TUŞ KOMUTLARI (Güvenlik Protokolü Entegre Edildi) -----
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_S and ((event.modifiers() & Qt.ControlModifier) or (event.modifiers() & Qt.MetaModifier)):
            # Kayıt devam ediyor mu kontrolü (Hem Rec, Sound ve Media için)
            is_recording = False
            for editor_name, editor_instance in self.instantiated_editors.items():
                if editor_name == "Rec" and getattr(editor_instance, 'recording', False):
                    is_recording = True
                    break
                if editor_name == "Sound" and getattr(editor_instance, 'is_recording_mode', False):
                    is_recording = True
                    break
                # --- YENİ: Media Editörü Kayıt Kontrolü ---
                if editor_name == "Media" and getattr(editor_instance, 'is_recording', False):
                    is_recording = True
                    break

            if is_recording:
                msg = QMessageBox(self)
                msg.setWindowTitle("Kayıt Devam Ediyor")
                msg.setText("Kaydınız şu anda devam ediyor.\n\n"
                            "Editörü değiştirmek istiyor musunuz?\n"
                            "(Kayıt otomatik olarak durdurulup temizlenecektir)")
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setDefaultButton(QMessageBox.No)
                msg.setStyleSheet("""
                    QMessageBox {
                        background-color: #1e1e1e;
                        color: white;
                    }
                    QLabel {
                        color: white;
                        font-size: 14px;
                        padding: 10px;
                    }
                    QPushButton {
                        padding: 8px 20px;
                        font-weight: bold;
                        border-radius: 4px;
                    }
                    QPushButton[text="Yes"] {
                        background-color: #c42b1c;
                        color: white;
                    }
                    QPushButton[text="No"] {
                        background-color: #333333;
                        color: white;
                    }
                """)
                reply = msg.exec_()
                if reply == QMessageBox.Yes:
                    print("Python: Kullanıcı editör geçişini onayladı → kayıt durduruluyor.")
                    if "Rec" in self.instantiated_editors:
                        rec_editor = self.instantiated_editors["Rec"]
                        if hasattr(rec_editor, '_pause_recording_session'):
                            rec_editor._pause_recording_session()
                    if "Sound" in self.instantiated_editors:
                        sound_editor = self.instantiated_editors["Sound"]
                        if getattr(sound_editor, 'is_recording_mode', False):
                            if hasattr(sound_editor, 'lib') and hasattr(sound_editor, 'audio_engine'):
                                sound_editor.lib.stop_microphone_recording(sound_editor.audio_engine)
                            sound_editor.is_recording_mode = False
                            if hasattr(sound_editor, 'btn_enter'):
                                sound_editor.btn_enter.setText('Record')
                    # --- YENİ: Media Editörü Kayıt Durdurma Bloğu ---
                    if "Media" in self.instantiated_editors:
                        media_editor = self.instantiated_editors["Media"]
                        if getattr(media_editor, 'is_recording', False):
                            if hasattr(media_editor, '_stop_all_recording_processes'):
                                media_editor._stop_all_recording_processes()
                            media_editor.is_recording = False
                            if hasattr(media_editor, 'audio_mode_btn'):
                                media_editor.audio_mode_btn.setText("Sound")
                            if hasattr(media_editor, '_update_record_button_state'):
                                media_editor._update_record_button_state()

                    self.switchToEditor("Sphere", close_current=True)
                else:
                    print("Python: Kullanıcı editör geçişini iptal etti.")
            else:
                self.switchToEditor("Sphere", close_current=True)
                
            event.accept()
        elif event.key() == Qt.Key_Q and (event.modifiers() & Qt.ControlModifier) and not (event.modifiers() & Qt.AltModifier):
            self.showSwitcher()
            event.accept()
        elif event.key() == Qt.Key_Q and (event.modifiers() & Qt.ControlModifier) and (event.modifiers() & Qt.AltModifier):
            self.showIdeSwitcher()
            event.accept()
        else:
            super().keyPressEvent(event)

    def showSwitcher(self):
        dlg = EditorSwitcherDialog(self.editors_order, self)
        if dlg.exec_() == QDialog.Accepted and dlg.selected_name:
            self.switchToEditor(dlg.selected_name, close_current=False)

    def showIdeSwitcher(self):
        try:
            from IDE_switcher import IDE_Switcher
            self.ide_switcher_dialog = IDE_Switcher(core_window_ref=self)
            self.ide_switcher_dialog.show()
        except ImportError as e:
            QMessageBox.critical(self, "Hata", f"IDE_switcher.py bulunamadı: {e}")

    # ----- DOSYA YÜKLEME (orijinal, hiç değişmedi) -----
    def loadEditorFile(self, editor_name, file_path):
        print(f"DEBUG: CoreWindow.loadEditorFile called. editor_name: {editor_name}, file_path: {file_path}")
        
        if editor_name == "Drawing":
            if "Drawing" in self.instantiated_editors:
                current_drawing_editor = self.instantiated_editors["Drawing"]
                if hasattr(current_drawing_editor, 'save_state_to_temp_file'):
                    current_drawing_editor.save_state_to_temp_file()
                self.stack.removeWidget(current_drawing_editor)
                del self.instantiated_editors["Drawing"]
                current_drawing_editor.deleteLater()
                print("DEBUG: Mevcut Drawing editörü kapatıldı.")
            from Drawing_editor import DrawingEditorWindow
            drawing_editor = DrawingEditorWindow()
            self.stack.addWidget(drawing_editor)
            self.instantiated_editors[editor_name] = drawing_editor
            self.stack.setCurrentWidget(drawing_editor)
            drawing_editor.showMaximized()
            QTimer.singleShot(0, lambda: drawing_editor.load_image_from_path(file_path))
            self.setWindowTitle("Kavram")
            print(f"DEBUG: Drawing editörü yüklendi ve dosya {file_path} için hazırlandı.")
        elif editor_name == "Text":
            print("DEBUG: Text editörü için dosya yükleme bloğuna girildi.")
            if "Text" in self.instantiated_editors:
                current_text_editor = self.instantiated_editors["Text"]
                if hasattr(current_text_editor, 'save_state_to_temp_file'):
                    current_text_editor.save_state_to_temp_file()
                self.stack.removeWidget(current_text_editor)
                del self.instantiated_editors["Text"]
                current_text_editor.deleteLater()
                print("DEBUG: Mevcut Text editörü kapatıldı.")
            from text_editor import TextEditorWindow
            text_editor = TextEditorWindow(core_window_ref=self)
            self.stack.addWidget(text_editor)
            self.instantiated_editors[editor_name] = text_editor
            self.stack.setCurrentWidget(text_editor)
            text_editor.showMaximized()
            QTimer.singleShot(0, lambda: text_editor.load_file_content(file_path))
            self.setWindowTitle("Kavram")
            print(f"DEBUG: Text editörü yüklendi ve dosya {file_path} için hazırlandı.")
        elif editor_name == "Ai":
            print("DEBUG: Ai editörü için dosya yükleme bloğuna girildi.")
            if "Ai" in self.instantiated_editors:
                current_ai_editor = self.instantiated_editors["Ai"]
                if hasattr(current_ai_editor, 'save_state_to_temp_file'):
                    current_ai_editor.save_state_to_temp_file()
                self.stack.removeWidget(current_ai_editor)
                del self.instantiated_editors["Ai"]
                current_ai_editor.deleteLater()
                print("DEBUG: Mevcut Ai editörü kapatıldı.")
            from ai_editor import AiEditorWindow
            ai_editor = AiEditorWindow(core_window_ref=self)
            self.stack.addWidget(ai_editor)
            self.instantiated_editors[editor_name] = ai_editor
            self.stack.setCurrentWidget(ai_editor)
            ai_editor.showMaximized()
            QTimer.singleShot(0, lambda: ai_editor.openFiles_from_path([file_path]))
            self.setWindowTitle("Kavram")
            print(f"DEBUG: Ai editörü yüklendi ve dosya {file_path} için hazırlandı.")
        elif editor_name == "Sound":
            print("DEBUG: Sound editörü için dosya yükleme bloğuna girildi.")
            if "Sound" in self.instantiated_editors:
                current_sound_editor = self.instantiated_editors["Sound"]
                if hasattr(current_sound_editor, 'save_state_to_temp_file'):
                    current_sound_editor.save_state_to_temp_file()
                self.stack.removeWidget(current_sound_editor)
                del self.instantiated_editors["Sound"]
                current_sound_editor.deleteLater()
                print("DEBUG: Mevcut Sound editörü kapatıldı.")
            from sound_GUI import SoundEditorWindow
            sound_editor = SoundEditorWindow(core_window_ref=self)
            self.stack.addWidget(sound_editor)
            self.instantiated_editors[editor_name] = sound_editor
            self.stack.setCurrentWidget(sound_editor)
            sound_editor.showMaximized()
            QTimer.singleShot(0, lambda: sound_editor.load_files_from_path([file_path]))
            self.setWindowTitle("Kavram")
            print(f"DEBUG: Sound editörü yüklendi ve dosya {file_path} için hazırlandı.")
        elif editor_name == "Media":
            print("DEBUG: Media editörü için dosya yükleme bloğuna girildi.")
            if "Media" in self.instantiated_editors:
                current_media_editor = self.instantiated_editors["Media"]
                if hasattr(current_media_editor, 'save_state_to_temp_file'):
                    current_media_editor.save_state_to_temp_file()
                self.stack.removeWidget(current_media_editor)
                del self.instantiated_editors["Media"]
                current_media_editor.deleteLater()
                print("DEBUG: Mevcut Media editörü kapatıldı.")
            from media_editor import MediaEditor
            media_editor = MediaEditor(core_window_ref=self)
            self.stack.addWidget(media_editor)
            self.instantiated_editors[editor_name] = media_editor
            self.stack.setCurrentWidget(media_editor)
            media_editor.showMaximized()
            QTimer.singleShot(0, lambda: media_editor.load_file(file_path))
            self.setWindowTitle("Kavram")
            print(f"DEBUG: Media editörü yüklendi ve dosya {file_path} için hazırlandı.")
        elif editor_name == "Rec":
            print("DEBUG: Rec editörü için dosya yükleme bloğuna girildi.")
            if "Rec" in self.instantiated_editors:
                current_rec_editor = self.instantiated_editors["Rec"]
                if hasattr(current_rec_editor, 'save_state_to_temp_file'):
                    current_rec_editor.save_state_to_temp_file()
                self.stack.removeWidget(current_rec_editor)
                del self.instantiated_editors["Rec"]
                current_rec_editor.deleteLater()
                print("DEBUG: Mevcut Rec editörü kapatıldı.")
            from camera_editor import CameraRecorderWindow
            rec_editor = CameraRecorderWindow(core_window_ref=self)
            self.stack.addWidget(rec_editor)
            self.instantiated_editors[editor_name] = rec_editor
            self.stack.setCurrentWidget(rec_editor)
            rec_editor.showMaximized()
            QTimer.singleShot(0, lambda: rec_editor.load_file(file_path))
            self.setWindowTitle("Kavram")
            print(f"DEBUG: Rec editörü yüklendi ve dosya {file_path} için hazırlandı.")
        elif editor_name == "Copy":
            print("DEBUG: Copy editörü için dosya yükleme bloğuna girildi.")
            if "Copy" in self.instantiated_editors:
                current_copy_editor = self.instantiated_editors["Copy"]
                if hasattr(current_copy_editor, 'save_state_to_temp_file'):
                    current_copy_editor.save_state_to_temp_file()
                self.stack.removeWidget(current_copy_editor)
                del self.instantiated_editors["Copy"]
                current_copy_editor.deleteLater()
                print("DEBUG: Mevcut Copy editörü kapatıldı.")
            from copya import MainWindow
            copy_editor = MainWindow(core_window_ref=self)
            self.stack.addWidget(copy_editor)
            self.instantiated_editors[editor_name] = copy_editor
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

    # ----- MEDIA-FILTER BAĞLANTISI -----
    def set_media_filter_connection(self, active):
        self.media_filter_connection_active = active
        print(f"Kavram: Media-Filter baglantisi {'aktif' if active else 'pasif'}")

    def is_media_filter_connected(self):
        return self.media_filter_connection_active

    def process_audio_with_filter(self, audio_path, callback=None):
        if self.is_filtering_in_progress:
            print("Kavram: Filtreleme zaten devam ediyor, yeni istek reddedildi")
            if callback:
                callback(False, None, "Filtreleme devam ediyor")
            return False
        if not self.filter_window_instance:
            try:
                import importlib
                module = importlib.import_module("filtre")
                AudioCleanerUI = getattr(module, "AudioCleanerUI")
                self.filter_window_instance = AudioCleanerUI()
                print("Kavram: Filter penceresi arka planda olusturuldu")
            except Exception as e:
                print(f"Kavram: Filter penceresi olusturulamadi: {e}")
                if callback:
                    callback(False, None, f"Filter olusturulamadi: {e}")
                return False
        self.is_filtering_in_progress = True
        def wrapped_callback(success, output_path, message):
            try:
                if callback:
                    callback(success, output_path, message)
            finally:
                self.is_filtering_in_progress = False
        try:
            result = self.filter_window_instance.process_audio_background(audio_path, wrapped_callback)
            if not result:
                self.is_filtering_in_progress = False
            return result
        except Exception as e:
            print(f"Kavram: Filtreleme hatasi: {e}")
            self.is_filtering_in_progress = False
            if callback:
                callback(False, None, str(e))
            return False

    def on_filtering_completed(self, success, output_path, message):
        self.is_filtering_in_progress = False
        print(f"Kavram: Filtreleme tamamlandi - Basari: {success}, Mesaj: {message}")

    def get_filter_window(self):
        return self.filter_window_instance

    # ----- TEMİZLİK VE KAPANIŞ -----
    def clean_up_external_processes(self):
        if hasattr(self, 'spawned_external_processes'):
            for p in self.spawned_external_processes:
                try:
                    if p.poll() is None:
                        try:
                            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                except Exception as e:
                    print(f"Harici program sonlandırma hatası: {e}")
            self.spawned_external_processes.clear()

    def closeEvent(self, event):
        if self.force_close:
            self.clean_up_external_processes()
            
            # Kavram zorla kapatıldığında Sound editörü oynatmayı kesmeli
            if "Sound" in self.instantiated_editors:
                sound_editor = self.instantiated_editors["Sound"]
                if hasattr(sound_editor, '_cleanup_engine'):
                    sound_editor._cleanup_engine()
                elif hasattr(sound_editor, 'lib') and hasattr(sound_editor, 'audio_engine'):
                    if sound_editor.lib and sound_editor.audio_engine:
                        try:
                            sound_editor.lib.stop_audio(sound_editor.audio_engine)
                        except Exception:
                            pass
                            
            event.accept()
            return
            
        if self.settings_window_instance and self.settings_window_instance.isVisible():
            self.settings_window_instance.close()
        if self.filter_window_instance and self.filter_window_instance.isVisible():
            self.filter_window_instance.close()
        if self.convert_window_instance and self.convert_window_instance.isVisible():
            self.convert_window_instance.close()

        # Kayıt devam ediyor mu kontrolü (Hem Rec, Sound ve Media için)
        is_recording = False
        for editor_name, editor_instance in self.instantiated_editors.items():
            if editor_name == "Rec" and getattr(editor_instance, 'recording', False):
                is_recording = True
                break
            if editor_name == "Sound" and getattr(editor_instance, 'is_recording_mode', False):
                is_recording = True
                break
            # --- YENİ: Media Editörü Kayıt Kontrolü ---
            if editor_name == "Media" and getattr(editor_instance, 'is_recording', False):
                is_recording = True
                break

        if is_recording:
            msg = QMessageBox(self)
            msg.setWindowTitle("Kayıt Devam Ediyor")
            msg.setText("Kaydınız şu anda devam ediyor.\n\n"
                        "Pencereyi kapatmak istiyor musunuz?\n"
                        "(Kayıt otomatik olarak durdurulup temizlenecektir)")
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #1e1e1e;
                    color: white;
                }
                QLabel {
                    color: white;
                    font-size: 14px;
                    padding: 10px;
                }
                QPushButton {
                    padding: 8px 20px;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton[text="Yes"] {
                    background-color: #c42b1c;
                    color: white;
                }
                QPushButton[text="No"] {
                    background-color: #333333;
                    color: white;
                }
            """)
            reply = msg.exec_()
            if reply == QMessageBox.Yes:
                print("Python: Kullanıcı kapatma onayladı → güvenlik protokolü çalışıyor.")
                if "Rec" in self.instantiated_editors:
                    rec_editor = self.instantiated_editors["Rec"]
                    if hasattr(rec_editor, '_pause_recording_session'):
                        rec_editor._pause_recording_session()
                if "Sound" in self.instantiated_editors:
                    sound_editor = self.instantiated_editors["Sound"]
                    if getattr(sound_editor, 'is_recording_mode', False):
                        if hasattr(sound_editor, 'lib') and hasattr(sound_editor, 'audio_engine'):
                            sound_editor.lib.stop_microphone_recording(sound_editor.audio_engine)
                        sound_editor.is_recording_mode = False
                        if hasattr(sound_editor, 'btn_enter'):
                            sound_editor.btn_enter.setText('Record')
                # --- YENİ: Media Editörü Kapanış Kontrol Bloğu ---
                if "Media" in self.instantiated_editors:
                    media_editor = self.instantiated_editors["Media"]
                    if getattr(media_editor, 'is_recording', False):
                        if hasattr(media_editor, '_stop_all_recording_processes'):
                            media_editor._stop_all_recording_processes()
                        media_editor.is_recording = False
                        if hasattr(media_editor, 'audio_mode_btn'):
                            media_editor.audio_mode_btn.setText("Sound")
                        if hasattr(media_editor, '_update_record_button_state'):
                            media_editor._update_record_button_state()
                            
                self.force_close = True
                self.clean_up_external_processes()
                QTimer.singleShot(650, self.close)
                event.ignore()
            else:
                event.ignore()
            return

        # Normal kapanış işlemi onaylandığında Sound editörünün oynatmasını hemen durdur
        if "Sound" in self.instantiated_editors:
            sound_editor = self.instantiated_editors["Sound"]
            if hasattr(sound_editor, '_cleanup_engine'):
                sound_editor._cleanup_engine()
            elif hasattr(sound_editor, 'lib') and hasattr(sound_editor, 'audio_engine'):
                if sound_editor.lib and sound_editor.audio_engine:
                    try:
                        sound_editor.lib.stop_audio(sound_editor.audio_engine)
                    except Exception:
                        pass

        self.clean_up_external_processes()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Kavram")
    load_cpp_library()
    initialize_lua_engine()
    window = CoreWindow()
    window.show()
    sys.exit(app.exec_())
