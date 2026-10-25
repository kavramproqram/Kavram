"""Ana pencere: üst araç çubuğu, ızgara/genişletilmiş görünüm geçişi, kaydet/yükle."""
import html
import json
import logging
import os
import zipfile

from PyQt5.QtCore import QPoint, Qt, QTimer
from PyQt5.QtGui import QFontMetrics, QKeySequence, QTextDocument
from PyQt5.QtWidgets import (QApplication, QFileDialog, QFrame, QHBoxLayout, QMainWindow,
                             QMenu, QMessageBox, QProgressDialog, QPushButton, QScrollArea,
                             QShortcut, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)

from . import config
from .gallery_builder import BuildError, build_document, build_gallery
from .models import KIND_TEXT, Note
from .renderers import KIND_IMAGE, KIND_TEXT as KIND_TEXT_FILE, DocumentRenderer, classify
from .storage import ArchiveError, Workspace
from .theme import (BUTTON_STYLE, MENU_STYLE, NAV_MENU_STYLE, SVG_SAVE_ICON,
                    TOOL_DELETE_STYLE, create_svg_icon)
from .tooltips import install_tooltip_palette, set_tip
from .widgets.note_widget import NoteWidget

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
        _fm_yol = _fm_os.path.join(_fm_os.path.dirname(_fm_os.path.abspath(__file__)), "..", "..", "file_manager", "file_manager.py")
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


log = logging.getLogger("copya.window")

# Üst çubuktaki "_" düğmesinin kısayolu (Alt+X)
COLLAPSE_SHORTCUT = "Alt+X"


def _filter(exts) -> str:
    return " ".join(f"*{e}" for e in exts)


class MainWindow(QMainWindow):
    def __init__(self, core_window_ref=None, export_dir=None):
        super().__init__()
        if export_dir is None:
            raise ValueError("export_dir zorunlu.")
        self.core_window_ref = core_window_ref
        self.export_dir = export_dir
        self.settings_file = os.path.join(export_dir, 'settings.json')

        self.setWindowTitle("Copya")
        self.resize(1100, 750)
        self.current_file_path = None
        self.expanded_note_widget = None
        self.notes_list = []

        self.workspace = Workspace(export_dir)
        self.renderer = DocumentRenderer()

        self.scroll_speeds = config.SCROLL_SPEEDS
        self.current_scroll_speed_index = config.DEFAULT_SCROLL_INDEX
        self.current_doc_size = config.DEFAULT_DOC_SIZE
        self.load_settings()
        self.scroll_rate = self.scroll_speeds[self.current_scroll_speed_index]
        self.scroll_accumulator = 0.0
        self.auto_scroll_active = False
        self.auto_scroll_timer = QTimer(self)
        self.auto_scroll_timer.timeout.connect(self.process_auto_scroll)

        install_tooltip_palette()
        self.init_ui()

    # ------------------------------------------------------------ ayarlar

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.current_scroll_speed_index = int(data.get('scroll_speed_index',
                                                               config.DEFAULT_SCROLL_INDEX))
                self.current_doc_size = data.get('doc_size', config.DEFAULT_DOC_SIZE)
                if not 0 <= self.current_scroll_speed_index < len(self.scroll_speeds):
                    self.current_scroll_speed_index = config.DEFAULT_SCROLL_INDEX
        except (OSError, ValueError, TypeError) as e:
            log.warning("Ayarlar okunamadı: %s", e)

    def save_settings(self):
        try:
            os.makedirs(self.export_dir, exist_ok=True)
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump({'scroll_speed_index': self.current_scroll_speed_index,
                           'doc_size': self.current_doc_size}, f)
        except OSError as e:
            log.warning("Ayarlar kaydedilemedi: %s", e)

    # ------------------------------------------------------------ arayüz kurulumu

    def _tool(self, text, width, height, style, slot, tip, enabled=True):
        btn = QPushButton(text)
        btn.setStyleSheet(style)
        btn.setFixedSize(width, height)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setEnabled(enabled)
        if slot is not None:
            btn.clicked.connect(slot)
        set_tip(btn, tip)
        return btn

    def init_ui(self):
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #222;")
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.toolbar_frame = QFrame()
        self.toolbar_frame.setObjectName("MainToolbar")
        self.toolbar_frame.setStyleSheet("#MainToolbar { background-color: #222222; border-bottom: 2px solid #555555; }")
        self.toolbar_frame.setFixedHeight(40)
        tl = QHBoxLayout(self.toolbar_frame)
        tl.setContentsMargins(10, 5, 10, 5)
        tl.setSpacing(10)

        self.file_btn = self._tool("File", 90, 30, BUTTON_STYLE,
                                   lambda: self.load_copya(), "file")
        tl.addWidget(self.file_btn)

        self.save_btn = QPushButton()
        self.save_btn.setIcon(create_svg_icon(SVG_SAVE_ICON, size=20, color="#ffffff"))
        self.save_btn.setStyleSheet(BUTTON_STYLE)
        self.save_btn.setFixedSize(30, 30)
        self.save_btn.setFocusPolicy(Qt.NoFocus)
        self.save_btn.clicked.connect(self.quick_save)
        set_tip(self.save_btn, "save")
        tl.addWidget(self.save_btn)

        self.add_btn = self._tool("+", 30, 30, BUTTON_STYLE,
                                  lambda: self.add_text_note(), "add")
        tl.addWidget(self.add_btn)

        self.gallery_btn = self._tool("Galeri", 80, 30, BUTTON_STYLE,
                                      self.handle_gallery_click, "gallery")
        tl.addWidget(self.gallery_btn)

        self.belge_btn = self._tool("Belge", 80, 30, BUTTON_STYLE,
                                    self.handle_document_click, "belge")
        tl.addWidget(self.belge_btn)

        self.nav_btn = self._tool("#1", 55, 30, BUTTON_STYLE, self.show_nav_menu, "nav",
                                  enabled=False)
        tl.addWidget(self.nav_btn)

        self.read_mode_btn = self._tool("I", 30, 30,
                                        BUTTON_STYLE + " font-weight: bold; color: white;",
                                        self.toggle_auto_scroll, "auto_scroll")
        tl.addWidget(self.read_mode_btn)

        self.scroll_speed_btn = self._tool(str(self.scroll_rate), 40, 30, BUTTON_STYLE,
                                           self.show_speed_menu, "speed", enabled=False)
        tl.addWidget(self.scroll_speed_btn)

        self.doc_size_btn = self._tool(f"{self.current_doc_size}", 50, 30, BUTTON_STYLE,
                                       self.show_size_menu, "doc_size", enabled=False)
        tl.addWidget(self.doc_size_btn)

        self.tool_delete_btn = self._tool("X", 30, 30, TOOL_DELETE_STYLE,
                                          self.delete_active_package, "toolbar_delete",
                                          enabled=False)
        tl.addWidget(self.tool_delete_btn)

        self.tool_min_btn = self._tool("_", 30, 30, BUTTON_STYLE,
                                       self.collapse_active_note, "toolbar_min", enabled=False)
        tl.addWidget(self.tool_min_btn)

        self.tool_copy_btn = self._tool("/", 30, 30, BUTTON_STYLE,
                                        self.copy_active_note, "toolbar_copy", enabled=False)
        tl.addWidget(self.tool_copy_btn)

        self.right_spacer = QWidget()
        self.right_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tl.addWidget(self.right_spacer)

        self.export_btn = self._tool("Export", 90, 30, BUTTON_STYLE,
                                     self.export_copya, "export")
        tl.addWidget(self.export_btn)

        self.switcher_btn = self._tool("Copy", 90, 30, BUTTON_STYLE,
                                       self.triggerCoreSwitcher, "switcher")
        tl.addWidget(self.switcher_btn)

        main_layout.addWidget(self.toolbar_frame)
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)

        # Izgara sayfası: üç sütun
        self.grid_page = QWidget()
        grid_layout = QVBoxLayout(self.grid_page)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background-color: #121212;")
        self.columns_layout = QHBoxLayout(container)
        self.columns_layout.setAlignment(Qt.AlignTop)
        self.columns_layout.setSpacing(15)
        self.columns_layout.setContentsMargins(15, 20, 15, 20)

        self.columns = []
        for _ in range(3):
            w = QWidget()
            lay = QVBoxLayout(w)
            lay.setAlignment(Qt.AlignTop)
            lay.setSpacing(10)
            lay.setContentsMargins(0, 0, 0, 0)
            self.columns.append(lay)
            self.columns_layout.addWidget(w, 1)
        self.scroll.setWidget(container)
        grid_layout.addWidget(self.scroll)
        self.content_stack.addWidget(self.grid_page)

        # Genişletilmiş sayfa
        self.expanded_page = QWidget()
        self.expanded_page.setStyleSheet("background-color: #000000;")
        self.expanded_layout = QVBoxLayout(self.expanded_page)
        self.expanded_layout.setContentsMargins(0, 0, 0, 0)
        self.content_stack.addWidget(self.expanded_page)

        # Ok tuşu gezinmesi (değişmedi)
        self._bind_shortcut(Qt.Key_Left, lambda: self.navigate_package(-1))
        self._bind_shortcut(Qt.Key_Right, lambda: self.navigate_package(1))
        self._bind_shortcut(Qt.Key_Up, self.navigate_page_up)
        self._bind_shortcut(Qt.Key_Down, self.navigate_page_down)
        # Üst çubuktaki "_" düğmesinin kısayolu (Alt+X)
        self._bind_shortcut(COLLAPSE_SHORTCUT, self.collapse_active_note)

    def _bind_shortcut(self, key, slot):
        shortcut = QShortcut(QKeySequence(key), self)
        shortcut.activated.connect(slot)
        return shortcut

    # ------------------------------------------------------------ not ekleme

    def add_note_model(self, note: Note, refresh=True):
        """Bir `Note` modelinden kart oluşturur. Limit doluysa None döner."""
        if len(self.notes_list) >= config.MAX_NOTES:
            return None
        widget = NoteWidget(self, note)
        self.notes_list.append(widget)
        if refresh:
            self.refresh_layout()
        return widget

    def add_text_note(self, text_html: str = ""):
        widget = self.add_note_model(Note(kind=KIND_TEXT, text=text_html))
        if widget is not None and not text_html:
            widget.pkg_edit.setFocus()
        return widget

    def remove_note(self, widget):
        if widget in self.notes_list:
            self.notes_list.remove(widget)
            widget.setParent(None)
            widget.deleteLater()
            self.refresh_layout()

    def refresh_layout(self):
        if self.content_stack.currentIndex() == 1:
            return
        for note in self.notes_list:
            note.setParent(None)
        for idx, widget in enumerate(self.notes_list):
            widget.set_column_mode()
            self.columns[idx % 3].addWidget(widget)
            widget.setFixedHeight(config.NOTE_HEIGHT)
            widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            widget.show()

    # ------------------------------------------------------------ dosya ekleme

    def handle_gallery_click(self):
        os.makedirs(self.export_dir, exist_ok=True)
        flt = (f"Galeri Dosyaları ({_filter(config.GALLERY_EXTS)});;"
               f"Resimler ({_filter(config.IMAGE_EXTS)});;"
               f"Metin Dosyaları ({_filter(config.TEXT_EXTS)})")
        files, _ = _fm.get_open_file_names(self, "Dosyaları Seç", self.export_dir, flt, double_click="select")
        files = [f for f in files if classify(f) in (KIND_IMAGE, KIND_TEXT_FILE)]
        if not files:
            return

        current = self.expanded_note_widget
        if current is not None and current.note.is_media:
            self._append_to_open_media(current, files)
            return

        if len(self.notes_list) >= config.MAX_NOTES:
            return
        note = build_gallery(files, self.workspace)
        if note.items:
            self.add_note_model(note)

    def _append_to_open_media(self, widget, files):
        note = widget.note
        room = note.max_items - len(note.items)
        if room <= 0:
            return
        if note.is_document:
            # Belgede yalnızca resimler sayfa olarak gösterilir
            files = [f for f in files if classify(f) == KIND_IMAGE]
        extra = build_gallery(files[:room], self.workspace).items
        if not extra:
            return
        note.items.extend(extra)
        widget.invalidate_cache()
        widget.refresh_expanded_view()

    def handle_document_click(self):
        os.makedirs(self.export_dir, exist_ok=True)
        flt = (f"Desteklenen Belgeler ({_filter(config.DOCUMENT_EXTS)});;"
               f"PDF Belgeleri ({_filter(config.PAGED_EXTS)});;"
               f"Office Belgeleri ({_filter(config.OFFICE_EXTS)});;"
               f"Drawing Projeleri ({_filter(config.PNF_EXTS)});;"
               f"Resimler ({_filter(config.IMAGE_EXTS)})")
        files, _ = _fm.get_open_file_names(self, "Belge Seç", self.export_dir, flt, double_click="select")
        if not files:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for path in files:
                if len(self.notes_list) >= config.MAX_NOTES:
                    break
                try:
                    note = build_document(path, self.workspace, self.renderer)
                except (BuildError, OSError) as e:
                    QMessageBox.critical(self, "Belge Hatası", f"{os.path.basename(path)}\n\n{e}")
                    continue
                note.doc_size = self.current_doc_size
                self.add_note_model(note, refresh=False)
            self.refresh_layout()
        finally:
            QApplication.restoreOverrideCursor()

    def paste_from_clipboard(self):
        mime = QApplication.clipboard().mimeData()
        if mime.hasUrls():
            files = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
            if files:
                note = build_gallery(files, self.workspace)
                if note.items:
                    self.add_note_model(note)
        elif mime.hasText():
            text = mime.text()
            if text:
                # Düz metni HTML olarak yorumlanmasın diye kaçırıyoruz
                formatted = html.escape(text, quote=False).replace("\n", "<br>")
                widget = self.add_text_note(formatted)
                if widget is not None:
                    self.update_nav_button_text_mode(widget)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Paste):
            self.paste_from_clipboard()
        super().keyPressEvent(event)

    # ------------------------------------------------------------ gezinme

    def navigate_package(self, delta):
        if not self.notes_list:
            return
        if self.expanded_note_widget:
            try:
                current = self.notes_list.index(self.expanded_note_widget)
            except ValueError:
                current = 0
            new_idx = (current + delta) % len(self.notes_list)
            self.collapse_note(self.expanded_note_widget)
        else:
            new_idx = 0 if delta > 0 else -1
        target = self.notes_list[new_idx]
        self.expand_note(target, target_item_index=target.note.current_page)

    def navigate_page_up(self):
        self._navigate_page(-1)

    def navigate_page_down(self):
        self._navigate_page(1)

    def _navigate_page(self, delta):
        widget = self.expanded_note_widget
        if widget is None or not widget.note.is_media:
            return
        if widget.note.is_document:
            self.change_document_page(delta)
        else:
            self.scroll_to_relative_item(delta)

    def scroll_to_relative_item(self, delta):
        note = self.expanded_note_widget.note
        if not note.items:
            return
        note.current_page = (note.current_page + delta) % len(note.items)
        self.scroll_to_item(note.current_page)

    def change_document_page(self, delta):
        note = self.expanded_note_widget.note
        if not note.items:
            return
        note.current_page = (note.current_page + delta) % len(note.items)
        self.expanded_note_widget.update_document_view()

    def on_gallery_scroll(self, val):
        widget = self.expanded_note_widget
        if widget is None or not widget.note.is_media or widget.note.is_document:
            return
        found = 0
        for i, w in enumerate(widget.item_widgets):
            g = w.geometry()
            if g.y() + g.height() > val:
                found = i
                break
        widget.note.current_page = found
        self.nav_btn.setText(f"#{found + 1}")

    def scroll_to_item(self, index):
        widget = self.expanded_note_widget
        if widget is None:
            return
        QApplication.processEvents()
        try:
            if widget.note.is_document:
                widget.note.current_page = index
                widget.update_document_view()
            elif index < len(widget.item_widgets) and widget.active_scroll_area:
                widget.active_scroll_area.ensureWidgetVisible(widget.item_widgets[index])
                widget.note.current_page = index
                self.nav_btn.setText(f"#{index + 1}")
        except RuntimeError:
            pass

    def show_nav_menu(self):
        widget = self.expanded_note_widget
        if widget is None or not widget.note.is_media:
            return
        menu = QMenu(self)
        menu.setStyleSheet(NAV_MENU_STYLE)
        menu.setFixedHeight(min(600, 35 * len(widget.note.items) + 20))
        for idx in range(len(widget.note.items)):
            action = menu.addAction(f"#{idx + 1}")
            action.triggered.connect(lambda _checked=False, i=idx: self.scroll_to_item(i))
        menu.exec_(self.nav_btn.mapToGlobal(QPoint(0, self.nav_btn.height())))

    # ------------------------------------------------------------ otomatik kaydırma

    def toggle_auto_scroll(self):
        if self.auto_scroll_active:
            self.auto_scroll_timer.stop()
            self.auto_scroll_active = False
            self.read_mode_btn.setStyleSheet(BUTTON_STYLE)
        else:
            if not self.expanded_note_widget:
                return
            self.auto_scroll_timer.start(50)
            self.auto_scroll_active = True
            self.read_mode_btn.setStyleSheet(BUTTON_STYLE.replace("transparent", "#555"))

    def process_auto_scroll(self):
        widget = self.expanded_note_widget
        if widget is None:
            self.toggle_auto_scroll()
            return
        bar = None
        if widget.active_scroll_area:
            bar = widget.active_scroll_area.verticalScrollBar()
        elif widget.expanded_text_edit:
            bar = widget.expanded_text_edit.verticalScrollBar()
        if not bar:
            return
        self.scroll_accumulator += self.scroll_rate
        if self.scroll_accumulator >= 1.0:
            pixels = int(self.scroll_accumulator)
            self.scroll_accumulator -= pixels
            bar.setValue(bar.value() + pixels)
        if bar.value() >= bar.maximum():
            self.toggle_auto_scroll()

    def show_speed_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        for i, speed in enumerate(self.scroll_speeds):
            action = menu.addAction(f"Speed: {speed}")
            action.setCheckable(True)
            action.setChecked(i == self.current_scroll_speed_index)
            action.triggered.connect(lambda _checked=False, idx=i: self.set_scroll_speed(idx))
        menu.exec_(self.scroll_speed_btn.mapToGlobal(QPoint(0, self.scroll_speed_btn.height())))

    def set_scroll_speed(self, index):
        self.current_scroll_speed_index = index
        self.scroll_rate = self.scroll_speeds[index]
        self.scroll_speed_btn.setText(str(self.scroll_rate))
        self.save_settings()

    def show_size_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        current = self.current_doc_size
        if self.expanded_note_widget and self.expanded_note_widget.note.is_document:
            current = self.expanded_note_widget.note.doc_size
        for val in config.DOC_SIZE_CHOICES:
            action = menu.addAction(f"Boyut: {val}")
            action.setCheckable(True)
            action.setChecked(val == current)
            action.triggered.connect(lambda _checked=False, v=val: self.set_doc_size(v))
        menu.exec_(self.doc_size_btn.mapToGlobal(QPoint(0, self.doc_size_btn.height())))

    def set_doc_size(self, size):
        self.current_doc_size = size
        self.doc_size_btn.setText(str(size))
        self.save_settings()
        widget = self.expanded_note_widget
        if widget and widget.note.is_document:
            widget.note.doc_size = size
            widget.update_document_view()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        widget = self.expanded_note_widget
        if widget and widget.note.is_document and widget.doc_image_widget is not None:
            try:
                widget.doc_image_widget.update_size()
            except RuntimeError:
                pass

    # ------------------------------------------------------------ genişletme / küçültme

    def _detach_expanded_children(self, owner):
        while self.expanded_layout.count():
            child = self.expanded_layout.takeAt(0)
            w = child.widget()
            if w:
                w.setParent(owner)
                w.hide()

    def expand_note(self, note_widget, maintain_scroll=False, target_item_index=None):
        self.setUpdatesEnabled(False)
        try:
            current_scroll = 0
            if maintain_scroll and self.expanded_note_widget:
                area = self.expanded_note_widget.active_scroll_area
                if area and not area.isHidden():
                    current_scroll = area.verticalScrollBar().value()

            if self.expanded_note_widget:
                old = self.expanded_note_widget
                old.update_text_from_expanded()
                old.is_expanded = False
                old.setFixedHeight(config.NOTE_HEIGHT)
                self._detach_expanded_children(old)
                self.expanded_note_widget = None

            self.expanded_note_widget = note_widget
            note_widget.is_expanded = True
            content = note_widget.get_or_create_expanded_content(current_scroll)
            self.expanded_layout.addWidget(content)
            content.show()

            self.content_stack.setCurrentIndex(1)
            self.update_toolbar_state(True, note_widget)

            if target_item_index is not None and note_widget.note.is_media:
                QTimer.singleShot(100, lambda: self.scroll_to_item(target_item_index))
        finally:
            self.setUpdatesEnabled(True)

    def collapse_note(self, note_widget):
        if self.auto_scroll_active:
            self.toggle_auto_scroll()
        note_widget.update_text_from_expanded()
        note_widget.is_expanded = False
        self._detach_expanded_children(note_widget)
        self.expanded_note_widget = None
        self.content_stack.setCurrentIndex(0)
        self.refresh_layout()
        self.update_toolbar_state(False)

    def collapse_active_note(self):
        if self.expanded_note_widget is not None:
            self.collapse_note(self.expanded_note_widget)

    def copy_active_note(self):
        if self.expanded_note_widget is not None:
            self.expanded_note_widget.copy_to_clipboard()

    def delete_active_package(self):
        widget = self.expanded_note_widget
        if widget is not None:
            self.collapse_note(widget)
            self.remove_note(widget)

    def update_toolbar_state(self, is_expanded, note_widget=None):
        if not is_expanded:
            self.add_btn.setEnabled(True)
            self.gallery_btn.setEnabled(True)
            self.belge_btn.setEnabled(True)
            self.tool_delete_btn.setEnabled(False)
            self.tool_copy_btn.setEnabled(False)
            self.tool_min_btn.setEnabled(False)
            self.nav_btn.setEnabled(False)
            self.nav_btn.setText("#1")
            self.nav_btn.setMinimumWidth(40)
            self.read_mode_btn.setEnabled(False)
            self.scroll_speed_btn.setEnabled(False)
            self.doc_size_btn.setEnabled(False)
            if self.auto_scroll_active:
                self.toggle_auto_scroll()
            return

        self.read_mode_btn.setEnabled(True)
        self.scroll_speed_btn.setEnabled(True)
        if note_widget is not None:
            note = note_widget.note
            if note.is_media:
                self.add_btn.setEnabled(False)
                self.gallery_btn.setEnabled(True)
                self.belge_btn.setEnabled(True)
                self.nav_btn.setEnabled(True)
                self.nav_btn.setText(f"#{note.current_page + 1 if note.is_document else 1}")
                self.doc_size_btn.setEnabled(note.is_document)
                if note.is_document:
                    self.doc_size_btn.setText(str(note.doc_size))
            else:
                self.add_btn.setEnabled(False)
                self.gallery_btn.setEnabled(False)
                self.belge_btn.setEnabled(False)
                self.doc_size_btn.setEnabled(False)
                self.update_nav_button_text_mode(note_widget)
        self.tool_delete_btn.setEnabled(True)
        self.tool_copy_btn.setEnabled(True)
        self.tool_min_btn.setEnabled(True)

    def update_nav_button_text_mode(self, widget):
        if widget.note.is_media:
            return
        doc = QTextDocument()
        doc.setHtml(widget.note.text)
        line_count = doc.blockCount()
        if line_count <= 1 and widget.note.text:
            line_count = widget.note.text.count("<br") + 1
        text = f"#{line_count}"
        self.nav_btn.setText(text)
        self.nav_btn.setEnabled(False)
        width = QFontMetrics(self.nav_btn.font()).width(text) + 30
        self.nav_btn.setMinimumWidth(max(40, width))

    # ------------------------------------------------------------ kaydet / yükle

    def flush_all_text(self):
        for widget in self.notes_list:
            widget.flush_text()
        if self.expanded_note_widget is not None:
            self.expanded_note_widget.update_text_from_expanded()

    def clear_view(self):
        if self.expanded_note_widget:
            self.collapse_note(self.expanded_note_widget)
        for widget in self.notes_list:
            widget.setParent(None)
            widget.deleteLater()
        self.notes_list.clear()

    def load_copya(self, path=None):
        if path is None:
            os.makedirs(self.export_dir, exist_ok=True)
            path, _ = _fm.get_open_file_name(self, "Open", self.export_dir,
                                                  "Copya Files (*.copya)", editor="Copy")
        if not path:
            return

        # Açık belge tanıtıcıları dosyaları kilitleyebilir; yüklemeden önce bırak.
        self.renderer.close()
        try:
            notes = self.workspace.load_archive(path)
        except (ArchiveError, zipfile.BadZipFile, OSError) as e:
            QMessageBox.critical(self, "Error", f"Could not load file:\n{e}")
            return

        self.clear_view()
        progress = QProgressDialog("Proje Yükleniyor...", "İptal", 0, len(notes), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        for idx, note in enumerate(notes):
            if progress.wasCanceled():
                break
            progress.setValue(idx)
            QApplication.processEvents()
            self.add_note_model(note, refresh=False)
        progress.setValue(len(notes))
        self.current_file_path = path
        self.refresh_layout()

    def quick_save(self):
        if self.current_file_path:
            self.save_to_path(self.current_file_path)
        else:
            self.export_copya()

    def export_copya(self):
        os.makedirs(self.export_dir, exist_ok=True)
        path, _ = _fm.get_save_file_name(
            self, "Save", os.path.join(self.export_dir, "untitled.copya"), "Copya Files (*.copya)", editor="Copy")
        if not path:
            return
        if not path.endswith('.copya'):
            path += '.copya'
        self.save_to_path(path)

    def save_to_path(self, path):
        self.flush_all_text()
        try:
            self.workspace.save_archive([w.note for w in self.notes_list], path)
        except (OSError, ArchiveError) as e:
            QMessageBox.critical(self, "Error", f"Could not save:\n{e}")
            return
        self.current_file_path = path
        _fm.notify_saved(self)

    def triggerCoreSwitcher(self):
        if self.core_window_ref and hasattr(self.core_window_ref, 'showSwitcher'):
            self.core_window_ref.showSwitcher()

    def closeEvent(self, event):
        self.flush_all_text()
        self.renderer.close()
        super().closeEvent(event)
