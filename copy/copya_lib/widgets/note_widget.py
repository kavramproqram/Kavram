"""Izgaradaki not kartı ve genişletilmiş (tam ekran) görünümü.

Veri `models.Note` içinde tutulur; bu sınıf yalnızca gösterim ve kullanıcı etkileşimini yönetir.
"""
import logging
import os

from PyQt5.QtCore import QMimeData, QPoint, Qt, QTimer, QUrl
from PyQt5.QtGui import QFont, QPixmap, QTextDocument
from PyQt5.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
                             QMenu, QScrollArea, QSizePolicy, QToolButton, QVBoxLayout,
                             QWidget)

from .. import config
from ..models import ITEM_IMG, ITEM_PAGE, ITEM_TXT, Note
from ..storage import ArchiveError
from ..theme import (GALLERY_BUTTON_STYLE, GALLERY_DELETE_STYLE, MENU_STYLE,
                     NOTE_BUTTON_STYLE, NOTE_DELETE_STYLE, NOTE_FRAME_STYLE)
from ..tooltips import set_tip
from .text_widgets import AutoResizingTextEdit, InteractiveTextEdit
from .viewers import DocumentImageWidget, ImageCardWidget, ZoomableImageWidget

log = logging.getLogger("copya.note")


def _tool_button(text, width, height, style, tip_key, font_size=None):
    btn = QToolButton()
    btn.setText(text)
    if font_size:
        btn.setFont(QFont("Segoe UI", font_size, QFont.Bold))
    btn.setFixedSize(width, height)
    btn.setStyleSheet(style)
    btn.setFocusPolicy(Qt.NoFocus)
    set_tip(btn, tip_key)
    return btn


class NoteWidget(QFrame):
    def __init__(self, parent_window, note: Note):
        super().__init__()
        self.parent_window = parent_window
        self.note = note
        self.is_expanded = False

        self.item_widgets = []
        self.active_scroll_area = None
        self.expanded_text_edit = None
        self.temp_large_edit = None
        self.doc_image_widget = None
        self.doc_page_label = None
        self.cached_expanded_widget = None
        self.text_edit = None
        self.image_card = None

        self._text_timer = QTimer(self)
        self._text_timer.setSingleShot(True)
        self._text_timer.setInterval(config.TEXT_DEBOUNCE_MS)
        self._text_timer.timeout.connect(self.flush_text)

        self._build_controls()
        self._setup_layout()
        self.setStyleSheet(NOTE_FRAME_STYLE)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setFixedHeight(config.NOTE_HEIGHT)

    # ------------------------------------------------------------------ kurulum

    def _build_controls(self):
        self.pkg_edit = QLineEdit(self.note.title)
        self.pkg_edit.setPlaceholderText("Note Title")
        self.pkg_edit.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.pkg_edit.setStyleSheet("QLineEdit { background: #1a1a1a; color: #ffffff; border: 1px solid #555; padding: 4px; border-radius: 4px; }")
        self.pkg_edit.textChanged.connect(lambda t: setattr(self.note, 'title', t))
        set_tip(self.pkg_edit, "note_title")

        self.copy_btn = _tool_button("/", 30, 30, NOTE_BUTTON_STYLE, "note_copy", 10)
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.max_btn = _tool_button("_", 30, 30, NOTE_BUTTON_STYLE, "note_max", 10)
        self.max_btn.clicked.connect(self.toggle_maximize)
        self.delete_btn = _tool_button("X", 40, 30, NOTE_DELETE_STYLE, "note_delete", 10)
        self.delete_btn.clicked.connect(self.delete_self)

        if self.note.is_media:
            self.image_card = ImageCardWidget()
        else:
            self.text_edit = InteractiveTextEdit(self)
            self.text_edit.setHtml(self.note.text)
            self.text_edit.setPlaceholderText("Content")
            self.text_edit.setStyleSheet("QTextEdit { background: #1a1a1a; color: #dddddd; border: 1px solid #555; padding: 4px; border-radius: 4px; }")
            self.text_edit.textChanged.connect(self.on_text_changed)

    def _setup_layout(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(4)
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(4)
        self.main_layout.addLayout(self.header_layout)
        self.main_layout.addWidget(self.text_edit if self.text_edit is not None else self.image_card)

    def set_column_mode(self):
        while self.header_layout.count():
            item = self.header_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self.header_layout.addWidget(self.delete_btn)
        self.header_layout.addWidget(self.pkg_edit, 1)
        self.header_layout.addWidget(self.max_btn)
        self.header_layout.addWidget(self.copy_btn)
        for w in (self.delete_btn, self.pkg_edit, self.max_btn, self.copy_btn):
            w.show()

    # ------------------------------------------------------- metin senkronu

    def on_text_changed(self):
        """Her tuşta HTML üretmek yerine kısa bir gecikmeyle senkronize eder."""
        self._text_timer.start()

    def flush_text(self):
        """Bekleyen metin değişikliğini nota yazar (kaydetmeden ve geçişlerden önce çağrılır)."""
        self._text_timer.stop()
        if self.note.is_media:
            return
        source = None
        if self.is_expanded and self.temp_large_edit is not None:
            source = self.temp_large_edit
        elif self.text_edit is not None:
            source = self.text_edit
        if source is not None:
            self.note.text = source.toHtml()
        if self.is_expanded and self.parent_window.expanded_note_widget is self:
            self.parent_window.update_nav_button_text_mode(self)

    def update_text_from_expanded(self):
        if self.temp_large_edit is None or self.text_edit is None:
            return
        self._text_timer.stop()
        try:
            html = self.temp_large_edit.toHtml()
            self.note.text = html
            self.text_edit.blockSignals(True)
            self.text_edit.setHtml(html)
            self.text_edit.blockSignals(False)
        except RuntimeError:  # widget silinmiş olabilir
            pass

    # ------------------------------------------------------- öğe işlemleri

    def item_pixmap(self, item) -> QPixmap:
        renderer = self.parent_window.renderer
        if item.type == ITEM_PAGE:
            return renderer.render_page(item.content, item.page_index)
        if item.type == ITEM_IMG:
            return renderer.image(item.content)
        return QPixmap()

    def remove_sub_item(self, index):
        # Not: önceki sürümde bu noktada çalışmayan bir solma animasyonu vardı
        # (bayrak hiç işaretlenmediği için). Arayüzü değiştirmemek adına kaldırıldı.
        self.finalize_removal(index)

    def finalize_removal(self, index):
        if not 0 <= index < len(self.note.items):
            return
        del self.note.items[index]
        new_len = len(self.note.items)
        target = 0 if new_len == 0 else (new_len - 1 if index >= new_len else index)
        self.invalidate_cache()
        self.parent_window.expand_note(self, maintain_scroll=True, target_item_index=target)

    def move_item_up(self, index):
        if index > 0:
            self.swap_items(index, index - 1)

    def move_item_down(self, index):
        if index < len(self.note.items) - 1:
            self.swap_items(index, index + 1)

    def swap_items(self, from_idx, to_idx):
        items = self.note.items
        if 0 <= from_idx < len(items) and 0 <= to_idx < len(items):
            items[from_idx], items[to_idx] = items[to_idx], items[from_idx]
            self.invalidate_cache()
            self.parent_window.expand_note(self, maintain_scroll=False, target_item_index=to_idx)

    def show_order_menu(self, btn, current_idx):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        menu.setFixedHeight(min(600, 35 * len(self.note.items) + 20))
        for i in range(len(self.note.items)):
            text = f"#{i + 1}" + (" <" if i == current_idx else "")
            action = menu.addAction(text)
            action.triggered.connect(lambda _checked=False, t=i: self.swap_items(current_idx, t))
        menu.exec_(btn.mapToGlobal(QPoint(0, btn.height())))

    # ------------------------------------------------------- genişletilmiş görünüm

    def invalidate_cache(self):
        if self.cached_expanded_widget is not None:
            self.cached_expanded_widget.deleteLater()
            self.cached_expanded_widget = None
        self.temp_large_edit = None
        self.doc_image_widget = None

    def get_or_create_expanded_content(self, scroll_val=0):
        if self.cached_expanded_widget is None:
            self.cached_expanded_widget = self._build_expanded(scroll_val)
        elif self.note.is_document and self.doc_image_widget is not None:
            try:
                self.doc_image_widget.doc_size = self.note.doc_size
                self.doc_image_widget.update_size()
            except RuntimeError:
                pass
        elif not self.note.is_media and self.temp_large_edit is not None:
            # Izgaradaki metin kapalıyken değiştiyse önbellekteki görünümü güncelle
            try:
                if self.temp_large_edit.toHtml() != self.note.text:
                    self.temp_large_edit.blockSignals(True)
                    self.temp_large_edit.setHtml(self.note.text)
                    self.temp_large_edit.blockSignals(False)
            except RuntimeError:
                pass
        return self.cached_expanded_widget

    def _build_expanded(self, scroll_val):
        self.item_widgets = []
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        if self.note.is_media:
            scroll = QScrollArea()
            scroll.setObjectName("expanded_scroll_area")
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

            content = QWidget()
            content.setStyleSheet("background-color: #444;")
            scroll_layout = QVBoxLayout(content)
            scroll_layout.setAlignment(Qt.AlignTop)

            if self.note.is_document:
                self._build_document_view(scroll_layout)
            else:
                scroll.verticalScrollBar().valueChanged.connect(self.parent_window.on_gallery_scroll)
                self._build_gallery_view(scroll_layout)

            scroll.setWidget(content)
            if scroll_val > 0 and not self.note.is_document:
                def restore():
                    try:
                        if not scroll.isHidden():
                            scroll.verticalScrollBar().setValue(scroll_val)
                    except RuntimeError:
                        pass
                QTimer.singleShot(10, restore)

            layout.addWidget(scroll)
            self.active_scroll_area = scroll
            self.expanded_text_edit = None
        else:
            text_container = QWidget()
            text_container.setStyleSheet("background-color: #444;")
            text_layout = QVBoxLayout(text_container)
            text_layout.setContentsMargins(30, 30, 30, 30)
            text_layout.setAlignment(Qt.AlignCenter)

            large = InteractiveTextEdit(self)
            large.setStyleSheet("background: #111; color: #fff; font-size: 16px; border: none;")
            large.setReadOnly(False)
            large.setHtml(self.note.text)
            large.textChanged.connect(self.on_text_changed)
            self.temp_large_edit = large
            self.expanded_text_edit = large
            self.active_scroll_area = None

            text_layout.addWidget(large)
            layout.addWidget(text_container)
        return container

    def _build_document_view(self, layout):
        layout.setContentsMargins(10, 20, 10, 60)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self.doc_page_label = QLabel("Sayfa 1")
        self.doc_page_label.setStyleSheet("color: #888; font-weight: bold; font-size: 14px;")
        self.doc_page_label.setAlignment(Qt.AlignCenter)
        set_tip(self.doc_page_label, "doc_page")
        layout.addWidget(self.doc_page_label)

        page_container = QWidget()
        page_layout = QVBoxLayout(page_container)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.doc_image_widget = DocumentImageWidget()
        page_layout.addWidget(self.doc_image_widget)
        layout.addWidget(page_container)

        QTimer.singleShot(50, self.update_document_view)

    def _build_gallery_view(self, layout):
        layout.setContentsMargins(60, 30, 200, 60)
        layout.setSpacing(20)
        for idx, item in enumerate(self.note.items):
            row = self._gallery_row(idx, item)
            self.item_widgets.append(row)
            layout.addWidget(row)

    def _gallery_row(self, idx, item):
        container = QWidget()
        container.setAttribute(Qt.WA_LayoutUsesWidgetRect)
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(5)

        label = QLabel(item.name)
        label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        label.setStyleSheet("color: #aaa; padding-left: 110px;")
        label.setAlignment(Qt.AlignLeft)
        cl.addWidget(label)

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(30)

        controls = QWidget()
        controls.setFixedWidth(100)
        controls.setStyleSheet("background: transparent;")
        ctl = QHBoxLayout(controls)
        ctl.setContentsMargins(0, 0, 0, 0)
        ctl.setSpacing(10)
        ctl.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        del_btn = _tool_button("X", 30, 30, GALLERY_DELETE_STYLE, "item_delete")
        del_btn.clicked.connect(lambda _checked=False, i=idx: self.remove_sub_item(i))
        ctl.addWidget(del_btn)
        ctl.addSpacing(10)

        stack = QWidget()
        sl = QVBoxLayout(stack)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(2)
        up_btn = _tool_button("▲", 50, 20, GALLERY_BUTTON_STYLE, "item_up")
        up_btn.clicked.connect(lambda _checked=False, i=idx: self.move_item_up(i))
        num_btn = _tool_button(f"#{idx + 1}", 50, 30, GALLERY_BUTTON_STYLE, "item_num")
        num_btn.clicked.connect(lambda _checked=False, b=num_btn, i=idx: self.show_order_menu(b, i))
        down_btn = _tool_button("▼", 50, 20, GALLERY_BUTTON_STYLE, "item_down")
        down_btn.clicked.connect(lambda _checked=False, i=idx: self.move_item_down(i))
        for b in (up_btn, num_btn, down_btn):
            sl.addWidget(b)
        ctl.addWidget(stack)
        row_layout.addWidget(controls)

        view = self._item_view(item)
        row_layout.addWidget(view, 1)
        cl.addWidget(row_widget)
        return container

    def _item_view(self, item):
        if item.type == ITEM_TXT:
            def store(text, it=item):
                it.content = text
            return AutoResizingTextEdit(item.content, item.is_txr, on_change=store)
        zoom = ZoomableImageWidget(self.item_pixmap(item))
        QTimer.singleShot(10, zoom.fit_logic)
        return zoom

    def update_document_view(self):
        if not self.note.is_document or not self.note.items:
            return
        if self.doc_image_widget is None:
            return
        try:
            idx = min(max(self.note.current_page, 0), len(self.note.items) - 1)
            self.note.current_page = idx
            pixmap = self.item_pixmap(self.note.items[idx])
            if self.doc_page_label is not None:
                self.doc_page_label.setText(f"Sayfa {idx + 1} / {len(self.note.items)}")
            self.doc_image_widget.set_pixmap(pixmap, self.note.doc_size)
            if self.active_scroll_area and self.active_scroll_area.verticalScrollBar():
                self.active_scroll_area.verticalScrollBar().setValue(0)
            if self.parent_window.expanded_note_widget is self:
                self.parent_window.nav_btn.setText(f"#{idx + 1}")
        except RuntimeError:
            pass

    def refresh_expanded_view(self):
        last = len(self.note.items) - 1
        self.invalidate_cache()
        QApplication.processEvents()
        self.parent_window.expand_note(self, maintain_scroll=False, target_item_index=last)

    # ------------------------------------------------------- diğer işlemler

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        if self.note.is_media:
            urls = self._media_urls()
            if urls:
                mime = QMimeData()
                mime.setUrls(urls)
                clipboard.setMimeData(mime)
                self._flash_copy_button("OK")
            return

        if self.is_expanded and self.temp_large_edit is not None:
            text = self.temp_large_edit.toPlainText()
        elif self.text_edit is not None:
            text = self.text_edit.toPlainText()
        else:
            doc = QTextDocument()
            doc.setHtml(self.note.text)
            text = doc.toPlainText()
        clipboard.setText(text)
        self._flash_copy_button("TXT")

    def _media_urls(self):
        urls = []
        ws = self.parent_window.workspace
        for item in self.note.items:
            try:
                if item.type == ITEM_IMG and os.path.exists(item.content):
                    urls.append(QUrl.fromLocalFile(item.content))
                elif item.type == ITEM_TXT:
                    path = ws.clip_path(item.name)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(item.content)
                    urls.append(QUrl.fromLocalFile(path))
                elif item.type == ITEM_PAGE:
                    pix = self.parent_window.renderer.render_page(item.content, item.page_index)
                    if not pix.isNull():
                        path = ws.clip_path(item.name + '.png')
                        pix.save(path, "PNG")
                        urls.append(QUrl.fromLocalFile(path))
            except (OSError, ArchiveError) as e:
                log.warning("Panoya eklenemedi (%s): %s", item.name, e)
        return urls

    def _flash_copy_button(self, text):
        if self.is_expanded:
            return
        self.copy_btn.setText(text)
        QTimer.singleShot(1000, lambda: self.copy_btn.setText("/"))

    def toggle_maximize(self):
        if self.parent_window.expanded_note_widget is self:
            self.parent_window.collapse_note(self)
        else:
            self.parent_window.expand_note(self)

    def delete_self(self):
        if self.is_expanded:
            self.parent_window.collapse_note(self)
        self.parent_window.remove_note(self)
