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
import sys
import re
import os
import json
import time
from collections import Counter  # noqa: F401  (gerekirse ileride kullanılabilir)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QTextEdit, QPushButton,
    QFileDialog, QDialog, QLabel, QApplication, QMessageBox,
    QLineEdit, QAction, QMenu, QInputDialog, QScrollArea,
    QLayout, QStyle
)
from PyQt5.QtGui import (
    QColor, QIcon, QPixmap, QPainter, QTextCharFormat, QTextCursor, QTextDocument
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDir, QByteArray, QPoint, QSize, QRect
from PyQt5.QtSvg import QSvgRenderer

# ---- Kavram File / Export penceresi (file_manager) -------------------------------
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


# =============================================================================
# Sabitler
# =============================================================================

SVG_UNDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19C15.866 19 19 15.866 19 12C19 8.13401 15.866 5 12 5C8.13401 5 5 8.13401 5 12C5 13.7909 5.70014 15.4293 6.84594 16.6386L5 18M5 18H9M5 18V14" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_REDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5C8.13401 5 5 8.13401 5 12C5 15.866 8.13401 19 12 19C15.866 19 19 15.866 19 12C19 10.2091 18.2999 8.57074 17.1541 7.3614L19 6M19 6H15M19 6V10" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_SEARCH_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M11 19C15.4183 19 19 15.8183 19 11C19 6.58172 15.4183 3 11 3C6.58172 3 3 6.58172 3 11C3 15.4183 6.58172 19 11 19ZM11 19C12.0294 19 12.9934 18.7909 13.8824 18.4018L21 21L19 13.8824C18.7909 12.9934 19 12.0294 19 11C19 6.58172 15.4183 3 11 3C6.58172 3 3 6.58172 3 11C3 15.4183 6.58172 19 11 19Z" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_ARROW_UP_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19V5M5 12L12 5L19 12" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_ARROW_DOWN_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5V19M5 12L12 19L19 12" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_SAVE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V7L17 3ZM12 17C10.34 17 9 15.66 9 14C9 12.34 10.34 11 12 11C13.66 11 15 12.34 15 14C15 15.66 13.66 17 12 17Z" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

TOP_BAR_STYLE = """
    QPushButton {
        background-color: transparent; color: white; font-size: 14px; font-weight: bold;
        border: 2px solid #555; border-radius: 8px; padding: 5px 10px;
    }
    QPushButton:hover { background-color: #444; }
    QPushButton:pressed { background-color: #666; }
"""

MINI_BUTTON_STYLE = """
    QPushButton {
        background-color: transparent; color: white; font-size: 16px;
        border: 2px solid #555; border-radius: 8px; padding: 2px;
    }
    QPushButton:hover { background-color: #444; }
    QPushButton:pressed { background-color: #666; }
"""

BOLD_MINI_BUTTON_STYLE = MINI_BUTTON_STYLE.replace("font-size: 16px;", "font-size: 16px; font-weight: bold;")

MENU_STYLE = """
    QMenu { background-color: #333; border: 1px solid #555; color: white; padding: 5px; }
    QMenu::item { padding: 5px 20px; min-width: 100px; }
    QMenu::item:selected { background-color: #555; }
"""

# Terminal silme desenleri
DELETE_PATTERNS = {
    "arabic": r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+",
    "fars": r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+",
    "latine": r"[a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]+",
    "rus": r"[\u0400-\u04FF\u0500-\u052F]+",
    "cin": r"[\u4E00-\u9FFF\u3400-\u4DBF]+",
    "japonca": r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+",
    "0-9": r"[0-9]+",
}
SYMBOL_DELETE_PATTERN = r"[^\w\s\u0600-\u06FF\u0400-\u04FF]+"

TERMINAL_HISTORY_DEFAULT = [
    "delete arabic", "delete latine", "delete rus", "delete cin",
    "delete japonca", "delete fars", "delete 0-9", "delete sembol",
]

# <center>...</center> veya <p align="center">...</p> satırları
CENTER_TAG_RE = re.compile(r'^\s*(?:<center>(.*)</center>|<p align="center">(.*)</p>)\s*$', re.IGNORECASE)

# Sembol paneli: (görünen/eklenen metin, kapanış eki)
_SUP_LETTERS = "ᵃᵇᶜᵈᵉᶠᵍʰᶦʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ"
_SUP_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"
DEFAULT_SYMBOLS = [
    ('(', ')'), ('[', ']'), ('{', '}'), ('[[', ']]'),
    ('<', '>'), ('<<', '>>'), ('"', '"'), ("'", "'"),
    ('`', '`'), ('**', '**'), ('__', '__'), ('## ', ''),
    ('<!--', '-->'), ('/* ', ' */'),
    ('.', ''), (';', ''), (':', ''), ('=', ''), ('!=', ''),
    ('->', ''), ('|', '|'), ('@', ''), ('$', ''), ('#', ''),
    ('+', ''), ('−', ''), ('×', ''), ('÷', ''), ('±', ''),
    ('≤', ''), ('≥', ''), ('≈', ''), ('≠', ''), ('√', ''),
    ('∞', ''), ('π', ''), ('∑', ''), ('∫', ''),
] + [(c, '') for c in _SUP_LETTERS + _SUP_DIGITS + "⁺⁻⁼⁽⁾"] + [
    ('←', ''), ('→', ''), ('↑', ''), ('↓', ''),
    ('⇐', ''), ('⇒', ''), ('⇔', ''),
    ('⌘', ''), ('⇧', ''), ('⌥', ''), ('⌫', ''), ('↩', ''),
    ('∧', ''), ('∨', ''), ('¬', ''), ('∀', ''), ('∃', ''), ('∈', ''),
    ('★', ''), ('✓', ''), ('✕', ''), ('⚠', ''), ('☁', ''),
    ('⚙', ''), ('🔒', ''), ('📅', ''),
]


# =============================================================================
# Yardımcılar
# =============================================================================

def create_svg_icon(svg_content, size=20, color="#aaa"):
    modified = svg_content.replace('stroke="#aaa"', f'stroke="{color}"').replace('fill="#aaa"', f'fill="{color}"')
    renderer = QSvgRenderer(QByteArray(modified.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def tr_lower(ch):
    """Türkçe küçük harf: I → ı, İ → i; diğerleri standart."""
    if ch == "I":
        return "ı"
    if ch == "İ":
        return "i"
    return ch.lower()


def tr_upper(ch):
    """Türkçe büyük harf: i → İ, ı → I; diğerleri standart."""
    if ch == "i":
        return "İ"
    if ch == "ı":
        return "I"
    return ch.upper()


def tr_fold(text):
    """Büyük/küçük harf duyarsız arama için katlama. Uzunluğu korur, böylece konumlar değişmez."""
    return "".join(tr_lower(c) for c in text)


def _iter_blocks(doc):
    block = doc.begin()
    while block.isValid():
        yield block
        block = block.next()


def _warn(message):
    sys.stderr.write(message + "\n")


def _set_enabled_icon(btn, svg, enabled):
    btn.setEnabled(enabled)
    btn.setIcon(create_svg_icon(svg, 20, "#ccc" if enabled else "#555"))


# =============================================================================
# FlowLayout
# =============================================================================

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, hSpacing=-1, vSpacing=-1):
        super().__init__(parent)
        self._hSpace = hSpacing
        self._vSpace = vSpacing
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def horizontalSpacing(self):
        if self._hSpace >= 0:
            return self._hSpace
        return self._smart_spacing(QStyle.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self):
        if self._vSpace >= 0:
            return self._vSpace
        return self._smart_spacing(QStyle.PM_LayoutVerticalSpacing)

    def _smart_spacing(self, pixel_metric):
        parent = self.parent()
        if isinstance(parent, QWidget):
            return parent.style().pixelMetric(pixel_metric, None, parent)
        return 6

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def doLayout(self, rect, testOnly):
        x, y = rect.x(), rect.y()
        line_h = 0
        sx = self.horizontalSpacing()
        sy = self.verticalSpacing()
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + sx
            if next_x - sx > rect.right() and line_h > 0:
                x = rect.x()
                y = y + line_h + sy
                next_x = x + hint.width() + sx
                line_h = 0
            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_h = max(line_h, hint.height())
        return y + line_h - rect.y()


# =============================================================================
# Sembol paneli
# =============================================================================

class SymbolButton(QPushButton):
    def __init__(self, prefix, suffix, index, panel, is_custom=False):
        label = prefix + suffix if suffix else prefix
        if len(label) > 6:
            label = label[:5] + ".."
        super().__init__(label, panel.content_widget)
        self.prefix = prefix
        self.suffix = suffix
        self.index = index
        self.panel = panel
        self.is_custom = is_custom
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        self.panel.on_button_clicked(self.index)

    def contextMenuEvent(self, event):
        if not self.is_custom:
            super().contextMenuEvent(event)
            return
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        edit_action = QAction("Düzenle", self)
        edit_action.triggered.connect(lambda: self.panel.edit_custom_symbol(self.prefix))
        menu.addAction(edit_action)
        delete_action = QAction("Sil", self)
        delete_action.triggered.connect(lambda: self.panel.delete_custom_symbol(self.prefix))
        menu.addAction(delete_action)
        menu.exec_(event.globalPos())


class SymbolPanel(QFrame):
    symbolClicked = pyqtSignal(str, str)   # (önek, kapanış eki)
    settingsChanged = pyqtSignal()         # ayar kaydı gerektiren değişiklik

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #333; border: none;")

        self.custom_symbols = []
        self.buttons = []
        self.current_nav_index = -1
        self.nav_mode_active = False
        self.font_size = 10
        self.common_btn_size = QSize(40, 30)

        self.control_btn_style_base = """
            QPushButton { background-color: transparent; color: #ccc; font-size: 11px; font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 2px; }
            QPushButton:hover { background-color: #444; }
        """
        self.control_btn_style_active = """
            QPushButton { background-color: #666; color: white; font-size: 11px; font-weight: bold; border: 2px solid #888; border-radius: 8px; padding: 2px; }
        """

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.control_frame = QFrame()
        self.control_frame.setStyleSheet("background-color: #333; border-bottom: 2px solid #666;")
        self.control_layout = QHBoxLayout(self.control_frame)
        self.control_layout.setContentsMargins(5, 2, 5, 2)
        self.control_layout.setSpacing(10)

        self.dot_btn = self._make_toggle(". ^", True, None)
        self.caps_btn = self._make_toggle("A", True, None)
        self.center_btn = self._make_toggle("O", False, None)
        self.nav_btn = self._make_toggle("@", False, self._on_nav_toggled)

        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(self.common_btn_size)
        self.add_btn.setStyleSheet(self.control_btn_style_base)
        self.add_btn.setFocusPolicy(Qt.NoFocus)
        self.add_btn.clicked.connect(self.add_new_symbol_dialog)
        self.control_layout.addWidget(self.add_btn)
        self.control_layout.addStretch()

        main_layout.addWidget(self.control_frame)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #333; }")
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.flow = FlowLayout(self.content_widget, margin=5, hSpacing=2, vSpacing=2)
        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)

    # --- Kontrol düğmeleri ---

    def _make_toggle(self, text, checked, handler):
        btn = QPushButton(text)
        btn.setFixedSize(self.common_btn_size)
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.setFocusPolicy(Qt.NoFocus)
        self.control_layout.addWidget(btn)
        self._style_toggle(btn)
        btn.toggled.connect(lambda state, b=btn, h=handler: self._on_toggle(b, h, state))
        return btn

    def _style_toggle(self, btn):
        btn.setStyleSheet(self.control_btn_style_active if btn.isChecked() else self.control_btn_style_base)

    def _on_toggle(self, btn, handler, state):
        self._style_toggle(btn)
        if handler:
            handler(state)
        self.settingsChanged.emit()

    def _on_nav_toggled(self, state):
        self.nav_mode_active = state
        if state and self.buttons:
            self.set_nav_index(self.current_nav_index if self.current_nav_index >= 0 else 0)
        else:
            self._restyle_all()

    def flags(self):
        return {
            "dot_mode_active": self.dot_btn.isChecked(),
            "caps_mode_active": self.caps_btn.isChecked(),
            "center_mode_active": self.center_btn.isChecked(),
            "nav_mode_active": self.nav_btn.isChecked(),
        }

    def apply_state(self, cfg):
        self.set_custom_symbols(cfg.get("custom_symbols", []))
        self.dot_btn.setChecked(bool(cfg.get("dot_mode_active", True)))
        self.caps_btn.setChecked(bool(cfg.get("caps_mode_active", True)))
        self.center_btn.setChecked(bool(cfg.get("center_mode_active", False)))
        self.nav_btn.setChecked(bool(cfg.get("nav_mode_active", False)))

    # --- Sembol listesi ---

    def _all_pairs(self):
        return [(c, '') for c in self.custom_symbols] + DEFAULT_SYMBOLS

    def set_custom_symbols(self, items):
        seen = []
        for s in items:
            if isinstance(s, str) and s and s not in seen:
                seen.append(s)
        self.custom_symbols = seen
        self.rebuild_buttons()

    def rebuild_buttons(self):
        while self.flow.count():
            item = self.flow.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.buttons = []
        n_custom = len(self.custom_symbols)
        for i, (prefix, suffix) in enumerate(self._all_pairs()):
            btn = SymbolButton(prefix, suffix, i, self, is_custom=(i < n_custom))
            self.flow.addWidget(btn)
            self.buttons.append(btn)
        if self.current_nav_index >= len(self.buttons):
            self.current_nav_index = -1
        self._restyle_all()

    def set_button_font_size(self, font_size):
        self.font_size = font_size
        self._restyle_all()

    def _restyle_button(self, i):
        if not (0 <= i < len(self.buttons)):
            return
        btn = self.buttons[i]
        fs = self.font_size
        selected = self.nav_mode_active and i == self.current_nav_index
        border = "#aaa" if selected else ("#888" if btn.is_custom else "#555")
        bg = "#666" if selected else "transparent"
        fg = "white" if selected else "#ccc"
        btn.setFixedSize(max(40, int(fs * 2.2)), max(30, int(fs * 1.5)))
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                font-size: {fs}px;
                font-weight: bold;
                border: 2px solid {border};
                border-radius: 8px;
                padding: 2px;
            }}
            QPushButton:hover {{ background-color: #444; }}
            QPushButton:pressed {{ background-color: #555; }}
        """)

    def _restyle_all(self):
        for i in range(len(self.buttons)):
            self._restyle_button(i)

    def _all_prefixes(self):
        return [p for p, _ in self._all_pairs()]

    def add_new_symbol_dialog(self):
        text, ok = QInputDialog.getText(self, "Yeni İşaret Ekle", "Eklenecek işaret veya metin:")
        if ok and text:
            self.add_custom_symbol(text)

    def add_custom_symbol(self, text):
        if not text or text in self._all_prefixes():
            return
        self.custom_symbols.insert(0, text)
        self.rebuild_buttons()
        self.settingsChanged.emit()

    def edit_custom_symbol(self, old_text):
        text, ok = QInputDialog.getText(self, "Düzenle", "Yeni metin:", text=old_text)
        if not ok or not text or text == old_text:
            return
        if text in self._all_prefixes():
            return
        idx = self.custom_symbols.index(old_text)
        self.custom_symbols[idx] = text
        self.rebuild_buttons()
        self.settingsChanged.emit()

    def delete_custom_symbol(self, text):
        if text not in self.custom_symbols:
            return
        answer = QMessageBox.question(
            self, "Sil", f"'{text}' sembolü silinsin mi?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if answer != QMessageBox.Yes:
            return
        self.custom_symbols.remove(text)
        self.rebuild_buttons()
        self.settingsChanged.emit()

    def current_custom_button(self):
        if not self.nav_mode_active:
            return None
        if 0 <= self.current_nav_index < len(self.buttons):
            btn = self.buttons[self.current_nav_index]
            if btn.is_custom:
                return btn
        return None

    def delete_current_custom(self):
        btn = self.current_custom_button()
        if btn is not None:
            self.delete_custom_symbol(btn.prefix)

    # --- Tıklama ve gezinme ---

    def on_button_clicked(self, index):
        if not (0 <= index < len(self.buttons)):
            return
        self.set_nav_index(index)
        btn = self.buttons[index]
        self.symbolClicked.emit(btn.prefix, btn.suffix)

    def set_nav_index(self, index):
        if not self.buttons:
            return
        old = self.current_nav_index
        new = max(0, min(index, len(self.buttons) - 1))
        self.current_nav_index = new
        if old != new:
            self._restyle_button(old)
        self._restyle_button(new)
        self.scroll_area.ensureWidgetVisible(self.buttons[new])

    def navigate_grid(self, dx, dy):
        if not self.buttons:
            return
        if self.current_nav_index < 0:
            self.set_nav_index(0)
            return
        if dy == 0:
            self.set_nav_index((self.current_nav_index + dx) % len(self.buttons))
            return
        step = self.buttons[0].width() + self.flow.horizontalSpacing()
        cols = max(1, self.scroll_area.viewport().width() // max(1, step))
        self.set_nav_index(self.current_nav_index + dy * cols)

    def trigger_current_nav_symbol(self):
        if 0 <= self.current_nav_index < len(self.buttons):
            self.on_button_clicked(self.current_nav_index)


class ResizeHandle(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(6)
        self.setCursor(Qt.SizeVerCursor)
        self.setStyleSheet("background-color: #444; border-top: 1px solid #666; border-bottom: 1px solid #222;")
        self.is_dragging = False
        self.start_y = 0

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.start_y = event.globalY()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging and self.parent():
            delta = self.start_y - event.globalY()
            self.start_y = event.globalY()
            new_height = max(80, min(500, self.parent().height() + delta))
            self.parent().setFixedHeight(new_height)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False


class SmartAssistantPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #333; border: none;")
        self.setFixedHeight(120)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.resize_handle = ResizeHandle(self)
        layout.addWidget(self.resize_handle)
        self.symbol_panel = SymbolPanel(self)
        layout.addWidget(self.symbol_panel)


# =============================================================================
# Editör bileşeni
# =============================================================================

class CustomTextEdit(QTextEdit):
    def __init__(self, editor_window, parent=None):
        super().__init__(parent)
        self.editor_window = editor_window
        self.setUndoRedoEnabled(True)   # Geri al / yinele Qt'nin kendi sisteminden gelir
        self._last_enter = -1e9
        self._shift_tap = 0.0

    def _symbol_panel(self):
        return self.editor_window.symbol_panel

    def _nav_active(self):
        return self.editor_window.assistant_panel.isVisible() and self._symbol_panel().nav_mode_active

    def _center_on(self):
        return self._symbol_panel().center_btn.isChecked()

    def applyAlignment(self, center):
        cursor = self.textCursor()
        fmt = cursor.blockFormat()
        target = Qt.AlignHCenter if center else Qt.AlignLeft
        if int(fmt.alignment()) != int(target):
            fmt.setAlignment(target)
            cursor.setBlockFormat(fmt)

    def _insert_line(self, dot, center):
        cursor = self.textCursor()
        cursor.beginEditBlock()
        if dot:
            cursor.insertText(" .")
        cursor.insertBlock()
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self.applyAlignment(center)

    def _nav_enter(self):
        now = time.monotonic()
        if now - self._last_enter < 0.5:
            # Çift Enter: satır sonu (nokta modu açıksa " ." ile birlikte)
            self._last_enter = -1e9
            self._insert_line(self.editor_window.dot_mode_enabled, self._center_on())
        else:
            self._last_enter = now
            self._symbol_panel().trigger_current_nav_symbol()

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()

        # Çift Shift → nav modu. Shift'ler arasına başka tuş girerse sayaç sıfırlanır,
        # böylece "AB" gibi büyük harf yazımı nav modunu açmaz.
        if key == Qt.Key_Shift:
            if not event.isAutoRepeat():
                now = time.monotonic()
                if self._shift_tap and now - self._shift_tap < 0.35:
                    self._shift_tap = 0.0
                    self._symbol_panel().nav_btn.click()
                else:
                    self._shift_tap = now
            super().keyPressEvent(event)
            return
        self._shift_tap = 0.0

        sp = self._symbol_panel()

        # --- Nav modu (yalnızca modifiyesiz tuşlar) ---
        if self._nav_active() and mods == Qt.NoModifier:
            moves = {
                Qt.Key_Left: (-1, 0), Qt.Key_Right: (1, 0),
                Qt.Key_Up: (0, -1), Qt.Key_Down: (0, 1),
            }
            if key in moves:
                sp.navigate_grid(*moves[key])
                return
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._nav_enter()
                return
            if key == Qt.Key_Delete and sp.current_custom_button() is not None:
                sp.delete_current_custom()
                return
            # Diğer tuşlar normal metin davranışına düşer.

        # --- Satır sonu (nokta modu / ortalama) ---
        center = self._center_on()
        if key in (Qt.Key_Return, Qt.Key_Enter) and mods == Qt.NoModifier:
            cursor = self.textCursor()
            line = cursor.block().text()
            after = line[cursor.positionInBlock():].strip()
            if self.editor_window.dot_mode_enabled and not after and line.strip():
                self._insert_line(True, center)
                return
            super().keyPressEvent(event)
            self.applyAlignment(center)
            return

        # --- Harf büyütme (Türkçe kurallarıyla) ---
        text = event.text()
        if mods in (Qt.NoModifier, Qt.ShiftModifier) and len(text) == 1 and text.isalpha():
            shift = bool(mods & Qt.ShiftModifier)
            cursor = self.textCursor()
            if not self.toPlainText() and cursor.position() == 0:
                self.insertPlainText(tr_lower(text) if shift else tr_upper(text))
                return
            if sp.caps_btn.isChecked() and not shift:
                before = cursor.block().text()[:cursor.positionInBlock()]
                if not before.strip():
                    self.insertPlainText(tr_upper(text))
                    return

        super().keyPressEvent(event)


# =============================================================================
# Terminal
# =============================================================================

class TerminalTextEdit(QTextEdit):
    commandEntered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Komut girin... (Örn: delete arabic, delete latine, delete A)")
        self.history = list(TERMINAL_HISTORY_DEFAULT)
        self.history_index = len(self.history)
        self.last_temp_command = ""

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and event.modifiers() == Qt.NoModifier:
            command = self.toPlainText().strip()
            if command:
                if command not in self.history:
                    self.history.append(command)
                self.history_index = len(self.history)
                self.last_temp_command = ""
                self.commandEntered.emit(command)
            return

        if event.key() == Qt.Key_Up:
            self._history_step(-1)
            return
        if event.key() == Qt.Key_Down:
            self._history_step(1)
            return

        super().keyPressEvent(event)

    def _history_step(self, delta):
        if not self.history:
            return
        if self.history_index == len(self.history):
            self.last_temp_command = self.toPlainText()
        idx = max(0, min(len(self.history), self.history_index + delta))
        self.history_index = idx
        text = self.history[idx] if idx < len(self.history) else self.last_temp_command
        self.setPlainText(text)
        self.moveCursorToEnd()

    def moveCursorToEnd(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)


class TerminalDialog(QDialog):
    commandEntered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Terminal")
        self.setStyleSheet("""
            QDialog { background-color: #222; border: 1px solid #555; }
            QLabel { color: #aaa; font-family: monospace; }
        """)
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.terminal_text = TerminalTextEdit(self)
        self.terminal_text.setStyleSheet("""
            QTextEdit {
                background-color: #111; color: #ddd; font-family: 'Courier New', monospace;
                font-size: 14px; border: 1px solid #444; padding: 5px;
            }
            QTextEdit:focus { border: 1px solid #666; }
        """)
        self.terminal_text.setFocusPolicy(Qt.StrongFocus)
        self.terminal_text.commandEntered.connect(self.handleCommand)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        layout.addWidget(self.terminal_text, 1)
        layout.addWidget(self.status_label)
        self.terminal_text.setFocus()

    def handleCommand(self, cmd):
        self.commandEntered.emit(cmd)
        self.terminal_text.clear()

    def set_status(self, message):
        self.status_label.setText(message)


# =============================================================================
# Ana pencere
# =============================================================================

class TextEditorWindow(QWidget):
    DEFAULT_BASE_DIR = _KAVRAM_EXPORT_DIR
    SETTINGS_FILE = os.path.join(_PROGRAM_DIR, "text_settings.cfg")
    OPEN_FILTER = "Desteklenen Metinler (*.txr *.txt *.md *.log);;Kavram Dosyası (*.txr);;Metin Dosyaları (*.txt *.md *.log)"
    SAVE_FILTER = "Kavram Dosyası (*.txr);;Metin (*.txt);;Markdown (*.md);;Tüm Dosyalar (*)"
    SAVE_EXTENSIONS = (".txr", ".txt", ".md", ".log")
    FONT_CHOICES = [10, 15, 18, 20, 24, 28, 32, 36, 48, 72]
    FONT_MIN, FONT_MAX = 10, 72
    SCROLL_SPEEDS = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]

    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        self.current_file = None
        self.terminal_dialog = None
        self.applied_font_size = None
        self.scroll_accumulator = 0.0

        self.search_matches = []
        self.search_index = -1
        self.search_term_cached = ""
        self.search_stale = True

        QDir().mkpath(self.DEFAULT_BASE_DIR)

        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self.autoScrollDown)

        # Ayar kaydı: sık değişikliklerde diski yormamak için gecikmeli yazılır
        self.settings_timer = QTimer(self)
        self.settings_timer.setSingleShot(True)
        self.settings_timer.setInterval(1500)
        self.settings_timer.timeout.connect(self.save_settings)

        cfg = self.load_settings()
        self.current_font_size = cfg["font_size"]
        self.current_scroll_speed_index = cfg["scroll_speed_index"]

        self.initUI(cfg)
        self.apply_font_size()
        self.update_scroll_speed_button_text()
        self.update_scroll_button_style()
        self._update_title()

    # ------------------------------------------------------------------
    # Özellikler
    # ------------------------------------------------------------------

    @property
    def scroll_rate(self):
        return self.SCROLL_SPEEDS[self.current_scroll_speed_index]

    @property
    def dot_mode_enabled(self):
        return self.symbol_panel.dot_btn.isChecked()

    # ------------------------------------------------------------------
    # Arayüz kurulumu
    # ------------------------------------------------------------------

    def _make_button(self, text="", style=MINI_BUTTON_STYLE, size=(30, 30), slot=None,
                     tooltip=None, icon=None):
        btn = QPushButton(text)
        btn.setStyleSheet(style)
        btn.setFixedSize(*size)
        if icon:
            btn.setIcon(create_svg_icon(icon, size=20))
        if tooltip:
            btn.setToolTip(tooltip)
        if slot:
            btn.clicked.connect(slot)
        return btn

    def initUI(self, cfg):
        self.setWindowTitle("Kavram")
        self.resize(1000, 700)
        self.setStyleSheet("background-color: #222; border: none;")

        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #222; border-bottom: 2px solid #555;")
        toolbar.setFixedHeight(40)
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(10, 5, 10, 5)
        tb.setSpacing(8)

        self.file_button = self._make_button("Dosya", TOP_BAR_STYLE, (90, 30), self.openFiles)
        self.save_button = self._make_button("", MINI_BUTTON_STYLE, (30, 30), self.quickSave,
                                             "Kaydet", SVG_SAVE_ICON)
        self.undo_button = self._make_button("", MINI_BUTTON_STYLE, (30, 30), self.undo_action,
                                             "Geri Al", SVG_UNDO_ICON)
        self.redo_button = self._make_button("", MINI_BUTTON_STYLE, (30, 30), self.redo_action,
                                             "Yinele", SVG_REDO_ICON)
        self.font_size_button = self._make_button("", TOP_BAR_STYLE, (70, 30), self.showFontSizeMenu)
        self.font_size_button.wheelEvent = self.changeFontSizeByWheel
        self.symbol_toggle_button = self._make_button("/", MINI_BUTTON_STYLE, (30, 30),
                                                      self.toggleSymbolPanel, "Sembol paneli")
        self.read_mode_button = self._make_button("I", BOLD_MINI_BUTTON_STYLE, (30, 30),
                                                  self.toggleAutoScroll, "Otomatik kaydırma")
        self.scroll_speed_button = self._make_button(str(self.scroll_rate), MINI_BUTTON_STYLE, (40, 30),
                                                     self.showScrollSpeedMenu)
        self.scroll_speed_button.wheelEvent = self.changeScrollSpeedByWheel
        self.terminal_button = self._make_button("Terminal", TOP_BAR_STYLE, (110, 30), self.openTerminal)
        self.line_count_label = QLabel("Satır: 0")
        self.line_count_label.setStyleSheet("color: white; font-size: 14px;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ara...")
        self.search_input.setStyleSheet("""
            QLineEdit { background-color: #444; color: white; border: 1px solid #555;
                        border-radius: 5px; padding: 3px; font-size: 14px; }
            QLineEdit:focus { border: 1px solid #777; }
        """)
        self.search_input.setFixedSize(150, 30)
        self.search_input.returnPressed.connect(self.startSearch)
        self.search_input.textChanged.connect(self._invalidate_search)

        self.search_button = self._make_button("", MINI_BUTTON_STYLE, (30, 30), self.startSearch,
                                               "Ara", SVG_SEARCH_ICON)
        self.prev_match_button = self._make_button("", MINI_BUTTON_STYLE, (30, 30), self.findPrevious,
                                                   "Önceki eşleşme", SVG_ARROW_UP_ICON)
        self.next_match_button = self._make_button("", MINI_BUTTON_STYLE, (30, 30), self.findNext,
                                                   "Sonraki eşleşme", SVG_ARROW_DOWN_ICON)
        self.export_button = self._make_button("Dışa Aktar", TOP_BAR_STYLE, (110, 30), self.exportContent)
        self.text_button = self._make_button("Metin", TOP_BAR_STYLE, (90, 30), self.triggerCoreSwitcher)

        for w in (self.file_button, self.save_button, self.undo_button, self.redo_button,
                  self.font_size_button, self.symbol_toggle_button, self.read_mode_button,
                  self.scroll_speed_button, self.terminal_button, self.line_count_label):
            tb.addWidget(w)
        tb.addStretch()
        for w in (self.search_input, self.search_button, self.prev_match_button,
                  self.next_match_button, self.export_button, self.text_button):
            tb.addWidget(w)

        # Metin alanı
        self.text_edit = CustomTextEdit(self)
        self.text_edit.setTextColor(QColor("white"))
        self.text_edit.setAcceptRichText(False)
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.undoAvailable.connect(lambda ok: _set_enabled_icon(self.undo_button, SVG_UNDO_ICON, ok))
        self.text_edit.redoAvailable.connect(lambda ok: _set_enabled_icon(self.redo_button, SVG_REDO_ICON, ok))
        self.text_edit.document().modificationChanged.connect(lambda _modified=False: self._update_title())
        _set_enabled_icon(self.undo_button, SVG_UNDO_ICON, False)
        _set_enabled_icon(self.redo_button, SVG_REDO_ICON, False)

        # Sembol paneli
        self.assistant_panel = SmartAssistantPanel(self)
        self.symbol_panel = self.assistant_panel.symbol_panel
        self.symbol_panel.apply_state(cfg)
        self.symbol_panel.symbolClicked.connect(self.insertSymbol)
        self.symbol_panel.settingsChanged.connect(self.schedule_save)
        self.assistant_panel.setVisible(bool(cfg["panel_visible"]))

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(toolbar)
        main_layout.addWidget(self.text_edit)
        main_layout.addWidget(self.assistant_panel)

    # ------------------------------------------------------------------
    # Ayarlar
    # ------------------------------------------------------------------

    def load_settings(self):
        defaults = {
            "font_size": 15,
            "scroll_speed_index": 4,
            "custom_symbols": [],
            "panel_visible": False,
            "dot_mode_active": True,
            "caps_mode_active": True,
            "center_mode_active": False,
            "nav_mode_active": False,
        }
        try:
            with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for key in defaults:
                    if key in data:
                        defaults[key] = data[key]
        except FileNotFoundError:
            pass
        except Exception as e:
            _warn(f"Ayarlar okunamadı, varsayılanlar kullanılıyor: {e}")

        defaults["font_size"] = self._clamp(defaults["font_size"], self.FONT_MIN, self.FONT_MAX, 15)
        defaults["scroll_speed_index"] = self._clamp(
            defaults["scroll_speed_index"], 0, len(self.SCROLL_SPEEDS) - 1, 4)
        if not isinstance(defaults["custom_symbols"], list):
            defaults["custom_symbols"] = []
        return defaults

    @staticmethod
    def _clamp(value, lo, hi, default):
        try:
            return max(lo, min(hi, int(value)))
        except (TypeError, ValueError):
            return default

    def schedule_save(self):
        self.settings_timer.start()

    def save_settings(self):
        if not hasattr(self, "symbol_panel"):
            return
        settings = {
            "font_size": self.current_font_size,
            "scroll_speed_index": self.current_scroll_speed_index,
            "custom_symbols": self.symbol_panel.custom_symbols,
            "panel_visible": not self.assistant_panel.isHidden(),
        }
        settings.update(self.symbol_panel.flags())
        tmp_path = self.SETTINGS_FILE + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            os.replace(tmp_path, self.SETTINGS_FILE)
        except OSError as e:
            _warn(f"Ayarlar kaydedilemedi: {e}")

    # ------------------------------------------------------------------
    # Dosya işlemleri ve kirli durum takibi
    # ------------------------------------------------------------------

    def _update_title(self):
        name = os.path.basename(self.current_file) if self.current_file else ""
        base = "Kavram" + (f" - {name}" if name else "")
        mark = " *" if self.text_edit.document().isModified() else ""
        self.setWindowTitle(base + mark)

    def _confirm_unsaved(self):
        """Kaydedilmemiş değişiklik varsa kullanıcıya sorar. Devam edilebilirse True döner."""
        if not self.text_edit.document().isModified():
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Kaydedilmemiş değişiklikler")
        box.setText("Kaydedilmemiş değişiklikler var. Kaydetmek ister misiniz?")
        save_btn = box.addButton("Kaydet", QMessageBox.AcceptRole)
        discard_btn = box.addButton("Kaydetme", QMessageBox.DestructiveRole)
        box.addButton("İptal", QMessageBox.RejectRole)
        box.setDefaultButton(save_btn)
        box.exec_()
        clicked = box.clickedButton()
        if clicked is save_btn:
            return self.quickSave()
        if clicked is discard_btn:
            return True
        return False

    @staticmethod
    def _with_default_ext(path, default=".txr"):
        if os.path.splitext(path)[1].lower() in TextEditorWindow.SAVE_EXTENSIONS:
            return path
        return path + default

    def _get_clean_content(self):
        lines = []
        for block in _iter_blocks(self.text_edit.document()):
            text = block.text()
            if int(block.blockFormat().alignment()) & int(Qt.AlignHCenter):
                lines.append(f"<center>{text}</center>")
            else:
                lines.append(text)
        return "\n".join(lines)

    def _set_clean_content(self, content):
        texts = []
        centered = []
        for line in content.split("\n"):
            m = CENTER_TAG_RE.match(line)
            if m:
                text = m.group(1) if m.group(1) is not None else m.group(2)
                texts.append(text)
                centered.append(True)
            else:
                texts.append(line)
                centered.append(False)

        self.text_edit.setPlainText("\n".join(texts))
        doc = self.text_edit.document()
        for block, is_centered in zip(_iter_blocks(doc), centered):
            if is_centered:
                cursor = QTextCursor(block)
                fmt = block.blockFormat()
                fmt.setAlignment(Qt.AlignHCenter)
                cursor.setBlockFormat(fmt)

    def load_file_content(self, path):
        if not path or not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as e:
            QMessageBox.critical(self, "Hata", f"Dosya yüklenirken hata oluştu:\n{e}")
            return

        if content.lstrip()[:15].lower().startswith("<!doctype html"):
            self.text_edit.setHtml(content)   # eski biçim desteği
        else:
            self._set_clean_content(content)

        doc = self.text_edit.document()
        doc.clearUndoRedoStacks()          # yüklenen içerik geri alınamaz taban durum olur
        doc.setModified(False)
        self.current_file = path
        self.apply_font_size()
        self.clearHighlights()
        self._update_title()

    def save_package(self, path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._get_clean_content())
        except OSError as e:
            QMessageBox.critical(self, "Kaydetme Hatası", str(e))
            return False
        self.current_file = path
        self.text_edit.document().setModified(False)
        self._update_title()
        _fm.notify_saved(self)
        return True

    def quickSave(self):
        if self.current_file:
            return self.save_package(self.current_file)
        return self.saveContent()

    def saveContent(self):
        start = self.current_file or os.path.join(self.DEFAULT_BASE_DIR, "belge.txr")
        path, _ = _fm.get_save_file_name(
            self, "Farklı Kaydet", start, self.SAVE_FILTER,
            options=QFileDialog.Options(), editor="Text"
        )
        if not path:
            return False
        return self.save_package(self._with_default_ext(path))

    def exportContent(self):
        """Dışarı aktarır; mevcut dosya ve kirli durum değişmez."""
        QDir().mkpath(self.DEFAULT_BASE_DIR)
        path, _ = _fm.get_save_file_name(
            self, "Dışa Aktar", os.path.join(self.DEFAULT_BASE_DIR, "belge.txr"), self.SAVE_FILTER,
            options=QFileDialog.Options(), editor="Text"
        )
        if not path:
            return
        path = self._with_default_ext(path)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._get_clean_content())
        except OSError as e:
            QMessageBox.critical(self, "Dışa Aktarma Hatası", str(e))
            return
        _fm.notify_saved(self)

    def openFiles(self):
        path, _ = _fm.get_open_file_name(
            self, "Dosya Aç", self.DEFAULT_BASE_DIR, self.OPEN_FILTER,
            options=QFileDialog.Options(), editor="Text"
        )
        if not path:
            return
        if not self._confirm_unsaved():
            return
        self.load_file_content(path)

    # ------------------------------------------------------------------
    # Geri al / yinele (Qt'nin yerleşik sistemi)
    # ------------------------------------------------------------------

    def undo_action(self):
        self.text_edit.undo()

    def redo_action(self):
        self.text_edit.redo()

    # ------------------------------------------------------------------
    # Metin değişikliği ve arama geçersizleme
    # ------------------------------------------------------------------

    def _on_text_changed(self):
        self.line_count_label.setText(f"Satır: {self.text_edit.document().blockCount()}")
        self._invalidate_search()

    def _invalidate_search(self, *_):
        self.search_stale = True
        self.text_edit.setExtraSelections([])

    # ------------------------------------------------------------------
    # Sembol ekleme
    # ------------------------------------------------------------------

    def insertSymbol(self, prefix, suffix):
        cursor = self.text_edit.textCursor()
        cursor.beginEditBlock()
        if cursor.hasSelection():
            selected = cursor.selection().toPlainText()
            cursor.insertText(f"{prefix}{selected}{suffix}")
        else:
            cursor.insertText(f"{prefix}{suffix}")
            if suffix:
                cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, len(suffix))
        cursor.endEditBlock()
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()
        self.text_edit.setFocus()

    def toggleSymbolPanel(self):
        self.assistant_panel.setVisible(self.assistant_panel.isHidden())
        if not self.assistant_panel.isHidden():
            self.text_edit.setFocus()
        self.schedule_save()

    # ------------------------------------------------------------------
    # Yazı boyutu
    # ------------------------------------------------------------------

    def apply_font_size(self):
        size = self.current_font_size
        if size != self.applied_font_size:
            self.applied_font_size = size
            self.text_edit.setStyleSheet(
                f"QTextEdit {{ background-color: #333; color: white; font-size: {size}px; border: none; }}"
                "QTextEdit:focus { outline: none; }"
            )
            font = self.text_edit.font()
            font.setPixelSize(size)
            self.text_edit.document().setDefaultFont(font)
            self.symbol_panel.set_button_font_size(size)
        self.font_size_button.setText(str(size))

    def setFontSize(self, size):
        self.current_font_size = self._clamp(size, self.FONT_MIN, self.FONT_MAX, self.current_font_size)
        self.apply_font_size()
        self.schedule_save()

    def changeFontSizeByWheel(self, event):
        step = 1 if event.angleDelta().y() > 0 else -1
        self.setFontSize(self.current_font_size + step)
        event.accept()

    def showFontSizeMenu(self):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        for size in self.FONT_CHOICES:
            text = f"{size} px" + (" (Aktif)" if size == self.current_font_size else "")
            action = QAction(text, self)
            action.triggered.connect(lambda checked=False, s=size: self.setFontSize(s))
            menu.addAction(action)
        point = self.font_size_button.mapToGlobal(QPoint(0, self.font_size_button.height()))
        menu.exec_(point)

    # ------------------------------------------------------------------
    # Otomatik kaydırma
    # ------------------------------------------------------------------

    def autoScrollDown(self):
        bar = self.text_edit.verticalScrollBar()
        self.scroll_accumulator += self.scroll_rate
        if self.scroll_accumulator >= 1.0:
            pixels = int(self.scroll_accumulator)
            self.scroll_accumulator -= pixels
            bar.setValue(bar.value() + pixels)
        if bar.value() >= bar.maximum():
            self.scroll_timer.stop()
            self.update_scroll_button_style()

    def toggleAutoScroll(self):
        if self.scroll_timer.isActive():
            self.scroll_timer.stop()
        else:
            self.scroll_timer.start(50)
        self.update_scroll_button_style()

    def update_scroll_button_style(self):
        style = BOLD_MINI_BUTTON_STYLE
        if self.scroll_timer.isActive():
            style = style.replace("background-color: transparent", "background-color: #555")
        self.read_mode_button.setStyleSheet(style)

    def update_scroll_speed_button_text(self):
        self.scroll_speed_button.setText(str(self.scroll_rate))

    def setScrollSpeed(self, speed_index):
        self.current_scroll_speed_index = max(0, min(len(self.SCROLL_SPEEDS) - 1, speed_index))
        self.update_scroll_button_style()
        self.update_scroll_speed_button_text()
        self.schedule_save()

    def changeScrollSpeedByWheel(self, event):
        step = 1 if event.angleDelta().y() > 0 else -1
        self.setScrollSpeed(self.current_scroll_speed_index + step)
        event.accept()

    def showScrollSpeedMenu(self):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        for i, speed in enumerate(self.SCROLL_SPEEDS):
            text = f"Hız: {speed}" + (" (Aktif)" if i == self.current_scroll_speed_index else "")
            action = QAction(text, self)
            action.setCheckable(True)
            action.setChecked(i == self.current_scroll_speed_index)
            action.triggered.connect(lambda checked=False, idx=i: self.setScrollSpeed(idx))
            menu.addAction(action)
        point = self.scroll_speed_button.mapToGlobal(QPoint(0, self.scroll_speed_button.height()))
        menu.exec_(point)

    # ------------------------------------------------------------------
    # Arama (büyük/küçük harf duyarsız, Türkçe uyumlu)
    # ------------------------------------------------------------------

    def _find_all(self, term):
        needle = tr_fold(term)
        matches = []
        if not needle:
            return matches
        for block in _iter_blocks(self.text_edit.document()):
            hay = tr_fold(block.text())
            start = 0
            while True:
                idx = hay.find(needle, start)
                if idx < 0:
                    break
                matches.append((block.position() + idx, len(needle)))
                start = idx + len(needle)
        return matches

    def _search_refresh(self):
        term = self.search_input.text()
        self.search_term_cached = term
        self.search_stale = False
        self.search_matches = self._find_all(term) if term else []
        if not self.search_matches:
            self.search_index = -1
            self.text_edit.setExtraSelections([])
            return False
        return True

    def _highlight_current(self):
        doc = self.text_edit.document()
        normal = QTextCharFormat()
        normal.setBackground(QColor("#FFC107"))
        current = QTextCharFormat()
        current.setBackground(QColor("#FF5722"))

        selections = []
        for i, (pos, length) in enumerate(self.search_matches):
            cursor = QTextCursor(doc)
            cursor.setPosition(pos)
            cursor.setPosition(pos + length, QTextCursor.KeepAnchor)
            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            sel.format = current if i == self.search_index else normal
            selections.append(sel)
        self.text_edit.setExtraSelections(selections)

        pos, length = self.search_matches[self.search_index]
        cursor = QTextCursor(doc)
        cursor.setPosition(pos)
        cursor.setPosition(pos + length, QTextCursor.KeepAnchor)
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible()

    def _step_search(self, delta):
        term = self.search_input.text()
        if not term:
            self.clearHighlights()
            return
        if self.search_stale or term != self.search_term_cached:
            if not self._search_refresh():
                return
            self.search_index = 0 if delta > 0 else len(self.search_matches) - 1
        else:
            if not self.search_matches:
                return
            self.search_index = (self.search_index + delta) % len(self.search_matches)
        self._highlight_current()

    def startSearch(self):
        self._step_search(1)

    def findNext(self):
        self._step_search(1)

    def findPrevious(self):
        self._step_search(-1)

    def clearHighlights(self):
        self.text_edit.setExtraSelections([])
        self.search_matches = []
        self.search_index = -1
        self.search_stale = True

    # ------------------------------------------------------------------
    # Terminal
    # ------------------------------------------------------------------

    def openTerminal(self):
        if self.terminal_dialog is None:
            self.terminal_dialog = TerminalDialog(self)
            self.terminal_dialog.commandEntered.connect(self.handleTerminalCommand)
        self.terminal_dialog.show()
        self.terminal_dialog.raise_()
        self.terminal_dialog.activateWindow()

    def _term_status(self, message):
        if self.terminal_dialog is not None:
            self.terminal_dialog.set_status(message)

    def _clear_document(self):
        cursor = QTextCursor(self.text_edit.document())
        cursor.beginEditBlock()
        cursor.select(QTextCursor.Document)
        cursor.removeSelectedText()
        cursor.endEditBlock()

    def handleTerminalCommand(self, command):
        cmd = command.strip()
        if not cmd:
            return
        low = cmd.lower()

        if low in ("delete", "delete all"):
            parent = self.terminal_dialog if self.terminal_dialog is not None else self
            answer = QMessageBox.question(
                parent, "Onay", "Bütün metin silinecek. Emin misiniz?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if answer != QMessageBox.Yes:
                self._term_status("İptal edildi.")
                return
            self._clear_document()
            self._term_status("Metin temizlendi.")
            return

        if low == "delete sembol":
            n = self.process_deletion(SYMBOL_DELETE_PATTERN)
            self._term_status(f"{n} sembol silindi." if n else "Silinecek sembol bulunamadı.")
            return

        parts = cmd.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "delete":
            target = parts[1]
            pattern = DELETE_PATTERNS.get(target.lower(), re.escape(target))
            n = self.process_deletion(pattern)
            self._term_status(f"{n} eşleşme silindi." if n else "Eşleşme bulunamadı.")
            return

        self._term_status(f"Bilinmeyen komut: {cmd}")

    def process_deletion(self, regex_pattern):
        doc = self.text_edit.document()
        spans = []
        for block in _iter_blocks(doc):
            text = block.text()
            base = block.position()
            for m in re.finditer(regex_pattern, text):
                if m.end() > m.start():
                    spans.append((base + m.start(), base + m.end()))

        if not spans:
            return 0

        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        for start, end in reversed(spans):   # sondan başa: konumlar kaymaz
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
        cursor.endEditBlock()
        return len(spans)

    # ------------------------------------------------------------------
    # Pencere geçişleri ve kapanış
    # ------------------------------------------------------------------

    def triggerCoreSwitcher(self):
        if not self._confirm_unsaved():
            return
        if self.core_window_ref and hasattr(self.core_window_ref, 'switch_to_core'):
            self.core_window_ref.switch_to_core('core')
            return
        main_window = self.window()
        if hasattr(main_window, 'showSwitcher'):
            main_window.showSwitcher()

    def closeEvent(self, event):
        if not self._confirm_unsaved():
            event.ignore()
            return
        self.settings_timer.stop()
        self.save_settings()
        event.accept()


# =============================================================================
# Giriş noktası
# =============================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyleSheet("""
        QMessageBox { background-color: #333; color: white; }
        QMessageBox QLabel { color: white; }

        QInputDialog { background-color: #333; color: white; }
        QInputDialog QLabel { color: white; }

        QFileDialog { background-color: #333; color: white; }
        QFileDialog QLabel { color: white; }
        QFileDialog QListView, QFileDialog QTreeView {
            background-color: #333;
            color: white;
            border: 1px solid #555;
        }
        QFileDialog QListView::item:hover, QFileDialog QTreeView::item:hover {
            background-color: #555;
        }
        QFileDialog QListView::item:selected, QFileDialog QTreeView::item:selected {
            background-color: #666;
        }

        QLineEdit { background-color: #555; color: white; border: 1px solid #666; padding: 4px; }

        QDialog QPushButton, QMessageBox QPushButton {
            background-color: #444;
            color: white;
            border: 1px solid #555;
            padding: 5px;
            border-radius: 3px;
            min-width: 60px;
        }
        QDialog QPushButton:hover, QMessageBox QPushButton:hover {
            background-color: #555;
        }

        QMenu { background-color: #333; color: white; border: 1px solid #555; }
        QMenu::item { background-color: transparent; padding: 5px 20px; }
        QMenu::item:selected { background-color: #555; }
    """)

    editor = TextEditorWindow(core_window_ref=None)
    editor.show()
    sys.exit(app.exec_())
