# text_editor.py - TAM DOSYA
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
import re
import os
import json
import time
from collections import Counter

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QTextEdit, QPushButton,
    QFileDialog, QDialog, QLabel, QApplication, QMessageBox, QProgressBar,
    QLineEdit, QAction, QShortcut, QMenu, QInputDialog, QScrollArea,
    QLayout, QSizePolicy
)
from PyQt5.QtGui import (
    QColor, QIcon, QPixmap, QPainter, QTextCharFormat, QTextCursor, 
    QKeySequence, QFont, QFontMetrics, QTextDocument
)
from PyQt5.QtCore import (
    Qt, QTimer, pyqtSignal, QDir, QByteArray, QPoint, QSize, QRect,
    QRectF, QUrl
)
from PyQt5.QtSvg import QSvgRenderer

# --- Yardımcı Fonksiyonlar ve Sabitler ---

SVG_UNDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19C15.866 19 19 15.866 19 12C19 8.13401 15.866 5 12 5C8.13401 5 5 8.13401 5 12C5 13.7909 5.70014 15.4293 6.84594 16.6386L5 18M5 18H9M5 18V14" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_REDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5C8.13401 5 5 8.13401 5 12C5 15.866 8.13401 19 12 19C15.866 19 19 15.866 19 12C19 10.2091 18.2999 8.57074 17.1541 7.3614L19 6M19 6H15M19 6V10" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_SEARCH_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M11 19C15.4183 19 19 15.8183 19 11C19 6.58172 15.4183 3 11 3C6.58172 3 3 6.58172 3 11C3 15.4183 6.58172 19 11 19ZM11 19C12.0294 19 12.9934 18.7909 13.8824 18.4018L21 21L19 13.8824C18.7909 12.9934 19 12.0294 19 11C19 6.58172 15.4183 3 11 3C6.58172 3 3 6.58172 3 11C3 15.4183 6.58172 19 11 19Z" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_ARROW_UP_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19V5M5 12L12 5L19 12" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_ARROW_DOWN_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5V19M5 12L12 19L19 12" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_SAVE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V7L17 3ZM12 17C10.34 17 9 15.66 9 14C9 12.34 10.34 11 12 11C13.66 11 15 12.34 15 14C15 15.66 13.66 17 12 17Z" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

def create_svg_icon(svg_content, size=20, color="#aaa"):
    modified_svg_content = svg_content.replace('stroke="#aaa"', f'stroke="{color}"').replace('fill="#aaa"', f'fill="{color}"')
    renderer = QSvgRenderer(QByteArray(modified_svg_content.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

# --- Özel FlowLayout Sınıfı ---
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, hSpacing=-1, vSpacing=-1):
        super(FlowLayout, self).__init__(parent)
        self._hSpace = hSpacing
        self._vSpace = vSpacing
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def horizontalSpacing(self):
        if self._hSpace >= 0: return self._hSpace
        return self.smartSpacing(QLayout.StyleFactory.Horizontal)

    def verticalSpacing(self):
        if self._vSpace >= 0: return self._vSpace
        return self.smartSpacing(QLayout.StyleFactory.Vertical)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items): return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items): return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        size += QSize(2 * self.contentsMargins().top(), 2 * self.contentsMargins().top())
        return size

    def doLayout(self, rect, testOnly):
        x, y = rect.x(), rect.y()
        lineHeight = 0
        spacingX = self.horizontalSpacing()
        spacingY = self.verticalSpacing()

        for item in self._items:
            spaceX = spacingX
            spaceY = spacingY
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()

    def smartSpacing(self, pm):
        parent = self.parent()
        if parent is None: return -1
        elif parent.isWidgetType(): return parent.style().pixelMetric(pm, None, parent)
        return parent.spacing()

# --- Özel Geri Al/Yinele Sistemi ---
class TextChangeCommand:
    def __init__(self, editor_instance, old_html, new_html, old_plain, new_plain, final_cursor_pos=None):
        self.editor = editor_instance
        self.old_html = old_html
        self.new_html = new_html
        self.old_plain = old_plain
        self.new_plain = new_plain
        self.final_cursor_pos = final_cursor_pos

    def do(self):
        editor_widget = self.editor.text_edit
        editor_widget.blockSignals(True)
        editor_widget.setHtml(self.new_html)
        self.editor.apply_font_size() # Fontu geri yükler
            
        cursor = editor_widget.textCursor()
        if self.final_cursor_pos is not None:
             pos = min(self.final_cursor_pos, len(self.new_plain))
             cursor.setPosition(pos)
        else:
            cursor.movePosition(QTextCursor.End)
        
        editor_widget.setTextCursor(cursor)
        editor_widget.ensureCursorVisible()
        editor_widget.blockSignals(False)
        self.editor.clearHighlights()

    def undo(self):
        editor_widget = self.editor.text_edit
        editor_widget.blockSignals(True)
        editor_widget.setHtml(self.old_html)
        self.editor.apply_font_size() # Fontu geri yükler
            
        cursor = editor_widget.textCursor()
        cursor.movePosition(QTextCursor.End)
        editor_widget.setTextCursor(cursor)
        editor_widget.ensureCursorVisible()
        editor_widget.blockSignals(False)
        self.editor.clearHighlights()

class UndoStack:
    def __init__(self):
        self.stack = []
        self.index = -1
        self.max_size = 10  # Geri alma sınırı 5'ten 10'a (2 katına) çıkarıldı

    def push(self, command):
        while len(self.stack) > self.index + 1:
            self.stack.pop()
        self.stack.append(command)
        self.index += 1
        if len(self.stack) > self.max_size:
            self.stack.pop(0)
            self.index -= 1

    def undo(self):
        if self.index >= 0:
            command = self.stack[self.index]
            command.undo()
            self.index -= 1
            return True
        return False

    def redo(self):
        if self.index < len(self.stack) - 1:
            self.index += 1
            command = self.stack[self.index]
            command.do()
            return True
        return False

    def can_undo(self):
        return self.index >= 0

    def can_redo(self):
        return self.index < len(self.stack) - 1

# --- Terminal Sınıfları --- 
class TerminalTextEdit(QTextEdit):
    commandEntered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Komut girin... (Örn: delete arabic, delete latine, delete A)")
        self.history = [
            "delete arabic", 
            "delete latine", 
            "delete rus", 
            "delete cin", 
            "delete japonca", 
            "delete fars", 
            "delete 0-9", 
            "delete sembol",
            "delete"
        ]
        self.history_index = len(self.history)
        self.last_temp_command = "" 

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() == Qt.NoModifier:
                command = self.toPlainText().strip()
                if command:
                    self.commandEntered.emit(command)
                    if command not in self.history:
                         self.history.append(command)
                    self.history_index = len(self.history) 
                    self.last_temp_command = ""
                return

        elif event.key() == Qt.Key_Up:
            if self.history:
                if self.history_index == len(self.history):
                    self.last_temp_command = self.toPlainText() 
                self.history_index -= 1
                if self.history_index < 0:
                    self.history_index = len(self.history) - 1 
                self.setPlainText(self.history[self.history_index])
                self.moveCursorToEnd()
            return

        elif event.key() == Qt.Key_Down:
            if self.history:
                self.history_index += 1
                if self.history_index >= len(self.history):
                    self.history_index = 0 
                self.setPlainText(self.history[self.history_index])
                self.moveCursorToEnd()
            return

        super().keyPressEvent(event)

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
            QDialog {
                background-color: #222;
                border: 1px solid #555;
            }
            QLabel {
                color: #aaa;
                font-family: monospace;
            }
        """)
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.terminal_text = TerminalTextEdit(self)
        self.terminal_text.setStyleSheet("""
            QTextEdit {
                background-color: #111;
                color: #ddd;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                border: 1px solid #444;
                padding: 5px;
            }
            QTextEdit:focus {
                border: 1px solid #666;
            }
        """)
        self.terminal_text.setFocusPolicy(Qt.StrongFocus)
        self.terminal_text.setFocus()
        self.terminal_text.commandEntered.connect(self.handleCommand)
        layout.addWidget(self.terminal_text)

        self.setLayout(layout)

    def handleCommand(self, cmd):
        self.commandEntered.emit(cmd)
        self.terminal_text.clear()

# --- Sembol Paneli ---
class SymbolButton(QPushButton):
    def __init__(self, text, index, parent=None, is_custom=False):
        super().__init__(text, parent)
        self.index = index
        self.is_custom = is_custom
        self.full_text = text
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self.clicked.connect(self._on_clicked)
        self._timer.timeout.connect(self._handle_single_click)
        self.is_double = False
        self.setMouseTracking(True)
        self.original_style = ""

    def enterEvent(self, event):
        if self.parent() and hasattr(self.parent(), 'set_hovered_button'):
            self.parent().set_hovered_button(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.parent() and hasattr(self.parent(), 'set_hovered_button'):
            self.parent().set_hovered_button(None)
        super().leaveEvent(event)

    def _on_clicked(self):
        if self._timer.isActive():
            self._timer.stop()
            self.is_double = True
            if self.parent() and hasattr(self.parent(), 'handle_button_click'):
                self.parent().handle_button_click(self.full_text, is_double=False, btn_ref=self)
        else:
            self.is_double = False
            self._timer.start()

    def _handle_single_click(self):
        if self.parent() and hasattr(self.parent(), 'handle_button_click'):
            self.parent().handle_button_click(self.full_text, is_double=False, btn_ref=self)
    
    def contextMenuEvent(self, event):
        if self.is_custom and self.parent() and hasattr(self.parent(), 'main_panel'):
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu { background-color: #333; border: 1px solid #555; color: white; padding: 5px; }
                QMenu::item { padding: 5px 20px; min-width: 100px; }
                QMenu::item:selected { background-color: #555; }
            """)
            
            edit_action = QAction("Düzenle", self)
            edit_action.triggered.connect(lambda: self.parent().main_panel.edit_custom_symbol(self.full_text))
            menu.addAction(edit_action)

            delete_action = QAction("Sil", self)
            delete_action.triggered.connect(lambda: self.parent().main_panel.delete_custom_symbol(self.full_text))
            menu.addAction(delete_action)
            
            menu.exec_(event.globalPos())
        else:
            super().contextMenuEvent(event)

class SymbolPanelWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = FlowLayout(self, margin=5, hSpacing=2, vSpacing=2)
        self.main_panel = None 
    def set_hovered_button(self, btn):
        if self.main_panel and hasattr(self.main_panel, 'set_hovered_button'):
            self.main_panel.set_hovered_button(btn)
    def handle_button_click(self, full_text, is_double, btn_ref):
        if self.main_panel and hasattr(self.main_panel, 'handle_button_click'):
            self.main_panel.handle_button_click(full_text, is_double, btn_ref)

class SymbolPanel(QFrame):
    symbolClicked = pyqtSignal(str, str, bool)
    dotModeChanged = pyqtSignal(bool)
    centerModeChanged = pyqtSignal(bool) 
    customSymbolDeleted = pyqtSignal(str)
    customSymbolAdded = pyqtSignal(str)
    usageCountChanged = pyqtSignal() 
    navModeChanged = pyqtSignal(bool) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #333; border: none;")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.control_frame = QFrame()
        self.control_frame.setStyleSheet("background-color: #333; border-bottom: 2px solid #666;")
        self.control_layout = QHBoxLayout(self.control_frame)
        self.control_layout.setContentsMargins(5, 2, 5, 2)
        self.control_layout.setSpacing(10) 

        self.common_btn_size = QSize(40, 30)

        self.control_btn_style_base = """
            QPushButton { background-color: transparent; color: #ccc; font-size: 11px; font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 2px; }
            QPushButton:hover { background-color: #444; }
        """
        self.control_btn_style_active = """
            QPushButton { background-color: #666; color: white; font-size: 11px; font-weight: bold; border: 2px solid #888; border-radius: 8px; padding: 2px; }
        """
        self.dot_mode_active = True
        self.center_mode_active = False 
        self.nav_mode_active = False 
        self.button_font_size = 10  # Varsayılan başlangıç font boyutu

        self.dot_btn = QPushButton(". ^")
        self.dot_btn.setFixedSize(self.common_btn_size)
        self.dot_btn.setCheckable(True)
        self.dot_btn.setChecked(True)
        self.dot_btn.setFocusPolicy(Qt.NoFocus)
        self.update_dot_btn_style()
        self.dot_btn.clicked.connect(self.toggle_dot_mode)
        self.control_layout.addWidget(self.dot_btn)

        self.caps_btn = QPushButton("A")
        self.caps_btn.setFixedSize(self.common_btn_size)
        self.caps_btn.setCheckable(True)
        self.caps_btn.setChecked(True)
        self.caps_btn.setFocusPolicy(Qt.NoFocus)
        self.update_caps_btn_style()
        self.caps_btn.clicked.connect(self.update_caps_btn_style)
        self.control_layout.addWidget(self.caps_btn)

        self.center_btn = QPushButton("O")
        self.center_btn.setFixedSize(self.common_btn_size)
        self.center_btn.setCheckable(True)
        self.center_btn.setChecked(False)
        self.center_btn.setFocusPolicy(Qt.NoFocus)
        self.update_center_btn_style()
        self.center_btn.clicked.connect(self.toggle_center_mode)
        self.control_layout.addWidget(self.center_btn)
        
        self.nav_btn = QPushButton("@")
        self.nav_btn.setFixedSize(self.common_btn_size)
        self.nav_btn.setCheckable(True)
        self.nav_btn.setChecked(False)
        self.nav_btn.setFocusPolicy(Qt.NoFocus)
        self.update_nav_btn_style()
        self.nav_btn.clicked.connect(self.toggle_nav_mode)
        self.control_layout.addWidget(self.nav_btn)

        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(self.common_btn_size)
        self.add_btn.setStyleSheet(self.control_btn_style_base)
        self.add_btn.setFocusPolicy(Qt.NoFocus)
        self.add_btn.clicked.connect(self.add_new_symbol_dialog)
        self.control_layout.addWidget(self.add_btn)

        self.control_layout.addStretch()
        self.main_layout.addWidget(self.control_frame)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #333; }")
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content_widget = SymbolPanelWidget()
        self.content_widget.main_panel = self 
        self.scroll_area.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll_area)
        self.buttons = []
        self.hovered_button = None
        self.current_nav_index = -1 
        self.is_initialized = False
        self.usage_counts = Counter()
        self.symbol_pairs = [
            ('(', ')'), ('[', ']'), ('{', '}'), ('[[', ']]'),
            ('<', '>'), ('<<', '>>'), ('"', '"'), ("'", "'"),
            ('`', '`'), ('**', '**'), ('__', '__'), ('## ', ''),
            ('<!--', '-->'), ('/* ', ' */'),
            ('.', ''), (';', ''), (':', ''), ('=', ''), ('!=', ''),
            ('->', ''), ('|', '|'), ('@', ''), ('$', ''), ('#', ''),
            ('+', ''), ('−', ''), ('×', ''), ('÷', ''), ('±', ''),
            ('≤', ''), ('≥', ''), ('≈', ''), ('≠', ''), ('√', ''),
            ('∞', ''), ('π', ''), ('∑', ''), ('∫', ''), (' ᵃ ᵇ ᶜ ᵈ ᵉ ᶠ ᵍ ʰ ᶦ ʲ ᵏ ˡ ᵐ ⁿ ᵒ ᵖ ʳ ˢ ᵗ ᵘ ᵛ ʷ ˣ ʸ ᶻ ', ''), (' ⁰ ¹ ² ³ ⁴ ⁵ ⁶ ⁷ ⁸ ⁹ ', ''), ('⁺ ⁻ ⁼ ⁽ ⁰ ⁾ ', ''),
            ('←', ''), ('→', ''), ('↑', ''), ('↓', ''),
            ('⇐', ''), ('⇒', ''), ('⇔', ''),
            ('⌘', ''), ('⇧', ''), ('⌥', ''), ('⌫', ''), ('↩', ''),
            ('∧', ''), ('∨', ''), ('¬', ''), ('∀', ''), ('∃', ''), ('∈', ''),
            ('★', ''), ('✓', ''), ('✕', ''), ('⚠', ''), ('☁', ''),
            ('⚙', ''), ('🔒', ''), ('📅', '')
        ]
        self.default_count = len(self.symbol_pairs)

    def ensure_initialized(self):
        if not self.is_initialized:
            self.rebuild_buttons()
            self.is_initialized = True
    
    def set_hovered_button(self, btn):
        self.hovered_button = btn
    
    def get_hovered_custom_button(self):
        if self.hovered_button and self.hovered_button.is_custom:
            return self.hovered_button
        return None
    
    def delete_custom_symbol(self, text_to_remove):
        found_idx = -1
        for i, pair in enumerate(self.symbol_pairs):
            prefix, suffix = pair
            if prefix == text_to_remove:
                 found_idx = i
                 break
        if found_idx != -1:
            self.symbol_pairs.pop(found_idx)
            self.rebuild_buttons()
            self.customSymbolDeleted.emit(text_to_remove)
            self.hovered_button = None

    def edit_custom_symbol(self, old_text):
        text, ok = QInputDialog.getText(self, "Düzenle", "Yeni metin:", text=old_text)
        if ok and text:
            found_idx = -1
            for i, pair in enumerate(self.symbol_pairs):
                if pair[0] == old_text:
                    found_idx = i
                    break
            if found_idx != -1:
                self.symbol_pairs[found_idx] = (text, "")
                self.rebuild_buttons()
                self.customSymbolDeleted.emit(old_text)
                self.customSymbolAdded.emit(text)
    
    def delete_hovered_button(self):
        btn = self.get_hovered_custom_button()
        if btn:
            self.delete_custom_symbol(btn.full_text)
            
    def get_custom_symbols(self):
        num_customs = len(self.symbol_pairs) - self.default_count
        if num_customs > 0:
            return [pair[0] for pair in self.symbol_pairs[:num_customs]]
        return []

    def set_button_font_size(self, font_size):
        """Alt menüdeki tüm butonların hem fiziksel hem de yazı boyutlarını ölçekler."""
        self.button_font_size = font_size
        
        # Butonun en-boy ölçülerini güncel font boyutuna göre dinamik ölçekle
        btn_h = max(30, int(font_size * 1.5))
        btn_w = max(40, int(font_size * 2.2))
        
        for btn in self.buttons:
            btn.setFixedSize(btn_w, btn_h)
            is_default = (len(self.symbol_pairs) - btn.index) <= self.default_count
            style_border = "#555" if is_default else "#888"
            
            base_style = f"""
                QPushButton {{ 
                    background-color: transparent; 
                    color: #ccc; 
                    font-size: {font_size}px; 
                    font-weight: bold; 
                    border: 2px solid {style_border}; 
                    border-radius: 8px; 
                    padding: 2px; 
                }}
                QPushButton:hover {{ background-color: #444; }}
                QPushButton:pressed {{ background-color: #555; }}
            """
            btn.original_style = base_style
            
            if self.nav_mode_active and self.buttons.index(btn) == self.current_nav_index:
                btn.setStyleSheet(f"""
                    QPushButton {{ 
                        background-color: #666; 
                        color: white; 
                        font-size: {font_size}px; 
                        font-weight: bold; 
                        border: 2px solid #aaa; 
                        border-radius: 8px; 
                        padding: 2px; 
                    }}
                """)
            else:
                btn.setStyleSheet(base_style)
                
        self.content_widget.layout.invalidate()

    def rebuild_buttons(self):
        layout = self.content_widget.layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.buttons = []
        
        font_size = getattr(self, 'button_font_size', 10)
        btn_h = max(30, int(font_size * 1.5))
        btn_w = max(40, int(font_size * 2.2))
        
        for i, (prefix, suffix) in enumerate(self.symbol_pairs):
            btn_text = f"{prefix}{suffix}" if suffix else prefix
            display_text = btn_text
            if len(display_text) > 6: display_text = display_text[:5] + ".."
            is_default = (len(self.symbol_pairs) - i) <= self.default_count
            btn = SymbolButton(prefix, i, self.content_widget, is_custom=not is_default)
            btn.setText(display_text)
            btn.setFixedSize(btn_w, btn_h)
            style_border = "#555" if is_default else "#888"
            
            base_style = f"""
                QPushButton {{ 
                    background-color: transparent; 
                    color: #ccc; 
                    font-size: {font_size}px; 
                    font-weight: bold; 
                    border: 2px solid {style_border}; 
                    border-radius: 8px; 
                    padding: 2px; 
                }}
                QPushButton:hover {{ background-color: #444; }}
                QPushButton:pressed {{ background-color: #555; }}
            """
            btn.original_style = base_style
            btn.setStyleSheet(base_style)
            
            layout.addWidget(btn)
            self.buttons.append(btn)
        self.current_nav_index = -1 

    def add_new_symbol_dialog(self):
        text, ok = QInputDialog.getText(self, "Yeni İşaret Ekle", "Eklenecek işaret veya metin:")
        if ok and text:
            self.add_custom_symbol(text)
    
    def add_custom_symbol(self, text):
        if not any(p[0] == text for p in self.symbol_pairs):
            self.symbol_pairs.insert(0, (text, ""))
            self.rebuild_buttons()
            self.customSymbolAdded.emit(text)
    
    def update_caps_btn_style(self):
        if self.caps_btn.isChecked():
            self.caps_btn.setStyleSheet(self.control_btn_style_active)
        else:
            self.caps_btn.setStyleSheet(self.control_btn_style_base)
    
    def update_dot_btn_style(self):
        if self.dot_btn.isChecked():
            self.dot_btn.setStyleSheet(self.control_btn_style_active)
        else:
            self.dot_btn.setStyleSheet(self.control_btn_style_base)
    
    def update_center_btn_style(self):
        if self.center_btn.isChecked():
            self.center_btn.setStyleSheet(self.control_btn_style_active)
        else:
            self.center_btn.setStyleSheet(self.control_btn_style_base)
    
    def update_nav_btn_style(self):
        if self.nav_btn.isChecked():
            self.nav_btn.setStyleSheet(self.control_btn_style_active)
        else:
            self.nav_btn.setStyleSheet(self.control_btn_style_base)

    def toggle_dot_mode(self):
        self.dot_mode_active = self.dot_btn.isChecked()
        self.update_dot_btn_style()
        self.dotModeChanged.emit(self.dot_mode_active)
    
    def toggle_center_mode(self):
        self.center_mode_active = self.center_btn.isChecked()
        self.update_center_btn_style()
        self.centerModeChanged.emit(self.center_mode_active)

    def toggle_nav_mode(self):
        self.nav_mode_active = self.nav_btn.isChecked()
        self.update_nav_btn_style()
        self.navModeChanged.emit(self.nav_mode_active)
        if self.nav_mode_active and self.buttons:
             if self.current_nav_index == -1:
                 self.set_nav_index(0)
             else:
                 self.set_nav_index(self.current_nav_index)

    def handle_button_click(self, prefix, is_double, btn_ref=None):
        suffix = ""
        for p, s in self.symbol_pairs:
            if p == prefix:
                suffix = s
                break
        self.usage_counts[prefix] += 1
        
        if btn_ref and btn_ref in self.buttons:
            self.current_nav_index = self.buttons.index(btn_ref)
            if self.nav_mode_active:
                self.highlight_nav_button()

        was_active = self.dot_mode_active
        self.symbolClicked.emit(prefix, suffix, False)
        if was_active and not self.dot_btn.isChecked():
             self.dot_btn.setChecked(True)
             self.toggle_dot_mode()
        self.usageCountChanged.emit()

    def set_nav_index(self, index):
        if not self.buttons: return
        self.current_nav_index = max(0, min(index, len(self.buttons) - 1))
        self.highlight_nav_button()
        
        btn = self.buttons[self.current_nav_index]
        self.scroll_area.ensureWidgetVisible(btn)

    def highlight_nav_button(self):
        font_size = getattr(self, 'button_font_size', 10)
        for i, btn in enumerate(self.buttons):
            if i == self.current_nav_index:
                btn.setStyleSheet(f"""
                    QPushButton {{ 
                        background-color: #666; 
                        color: white; 
                        font-size: {font_size}px; 
                        font-weight: bold; 
                        border: 2px solid #aaa; 
                        border-radius: 8px; 
                        padding: 2px; 
                    }}
                """)
            else:
                btn.setStyleSheet(btn.original_style)

    def navigate_grid(self, dx, dy):
        if not self.buttons: return
        
        if self.current_nav_index == -1:
            self.set_nav_index(0)
            return

        if dy == 0:
            new_idx = self.current_nav_index + dx
            if new_idx < 0: new_idx = len(self.buttons) - 1
            elif new_idx >= len(self.buttons): new_idx = 0
            self.set_nav_index(new_idx)
            return

        viewport_width = self.scroll_area.viewport().width()
        font_size = getattr(self, 'button_font_size', 10)
        item_width_approx = max(48, int(font_size * 2.2) + 8) 
        cols = max(1, viewport_width // item_width_approx)
        
        new_idx = self.current_nav_index + (dy * cols)
        
        if new_idx < 0:
            new_idx = 0 
        elif new_idx >= len(self.buttons):
            new_idx = len(self.buttons) - 1
            
        self.set_nav_index(new_idx)

    def trigger_current_nav_symbol(self):
        if self.current_nav_index != -1 and self.current_nav_index < len(self.buttons):
            btn = self.buttons[self.current_nav_index]
            self.handle_button_click(btn.full_text, False, btn)

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
            current_height = self.parent().height()
            new_height = current_height + delta
            new_height = max(80, min(500, new_height))
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

class RightClickButton(QPushButton):
    rightClicked = pyqtSignal()
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit()
        super().mousePressEvent(event)

# --- Ana Editör Bileşeni ---
class CustomTextEdit(QTextEdit):
    # Yalnızca Kavram File Manager'ın özel olarak işaretlediği sürüklemeleri
    # dosya içeriği ekleme işlemi olarak kabul eder.
    FILE_MANAGER_DRAG_MIME = "application/x-kavram-file-manager-drag"

    def __init__(self, editor_window, parent=None):
        super().__init__(parent)
        self.editor_window = editor_window
        self.setUndoRedoEnabled(False)
        self.setMouseTracking(True) 
        self.last_enter_time = 0 
        self.last_shift_press_time = 0 

        # Drop davranışı burada yalnızca özel File Manager payload'ı için
        # devreye girer. Diğer sürüklemeler Qt'nin mevcut davranışına bırakılır.
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasFormat(self.FILE_MANAGER_DRAG_MIME) and mime.hasUrls():
            local_files = [
                url.toLocalFile()
                for url in mime.urls()
                if url.isLocalFile() and os.path.isfile(url.toLocalFile())
            ]
            if local_files:
                event.acceptProposedAction()
                return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        mime = event.mimeData()
        if mime.hasFormat(self.FILE_MANAGER_DRAG_MIME) and mime.hasUrls():
            local_files = [
                url.toLocalFile()
                for url in mime.urls()
                if url.isLocalFile() and os.path.isfile(url.toLocalFile())
            ]
            if local_files:
                event.acceptProposedAction()
                return
        super().dragMoveEvent(event)

    @staticmethod
    def _read_dropped_text_file(file_path):
        """Dosya içeriğini metin olarak güvenli biçimde oku."""
        encodings = ("utf-8", "utf-8-sig", "cp1254", "latin-1")
        last_error = None
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding, newline="") as f:
                    return f.read()
            except UnicodeDecodeError as exc:
                last_error = exc
                continue
            except (OSError, IOError):
                return None
        return None

    def dropEvent(self, event):
        mime = event.mimeData()
        if not mime.hasFormat(self.FILE_MANAGER_DRAG_MIME) or not mime.hasUrls():
            super().dropEvent(event)
            return

        # File Manager'daki sürüklenen dosyalardan ilk gerçek dosyayı kullan.
        # Mevcut imleç konumu korunur; bırakılan ekran noktası imleci taşımaz.
        file_path = None
        for url in mime.urls():
            if url.isLocalFile():
                candidate = url.toLocalFile()
                if os.path.isfile(candidate):
                    file_path = candidate
                    break

        if not file_path:
            event.ignore()
            return

        content = self._read_dropped_text_file(file_path)
        if content is None:
            QMessageBox.information(
                self,
                "Dosya",
                "Bırakılan dosya metin olarak okunamadı."
            )
            event.ignore()
            return

        old_plain = self.toPlainText()
        old_html = self.toHtml()
        cursor = self.textCursor()
        cursor.beginEditBlock()
        cursor.insertText(os.path.basename(file_path))
        cursor.insertText("\n")
        cursor.insertText(content)
        final_position = cursor.position()
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

        new_plain = self.toPlainText()
        new_html = self.toHtml()
        if new_plain != old_plain:
            command = TextChangeCommand(
                self.editor_window,
                old_html,
                new_html,
                old_plain,
                new_plain,
                final_position
            )
            self.editor_window.undo_stack.push(command)
            self.editor_window.update_undo_redo_buttons()
            self.editor_window.clearHighlights()

        event.acceptProposedAction()

    def keyPressEvent(self, event):
        # --- Özel Kısayol Kontrolleri (Tuş Vuruşu Seviyesinde Geri Al / Yinele Çözümü) ---
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Z:
            self.editor_window.undo_action()
            event.accept()
            return
        elif (event.modifiers() == (Qt.ControlModifier | Qt.ShiftModifier) and event.key() == Qt.Key_Z) or \
             (event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_Y):
            self.editor_window.redo_action()
            event.accept()
            return

        panel = self.editor_window.assistant_panel
        symbol_panel = panel.symbol_panel
        
        if event.key() == Qt.Key_Shift:
            current_time = time.time()
            if current_time - self.last_shift_press_time < 0.3: 
                symbol_panel.nav_btn.click() 
                self.last_shift_press_time = 0 
            else:
                self.last_shift_press_time = current_time
            super().keyPressEvent(event)
            return

        if panel.isVisible() and symbol_panel.nav_mode_active:
            is_shift_held = (event.modifiers() & Qt.ShiftModifier)
            
            if is_shift_held:
                cursor = self.textCursor()
                handled = False
                
                if event.key() == Qt.Key_Right:
                    cursor.movePosition(QTextCursor.Right)
                    handled = True
                elif event.key() == Qt.Key_Left:
                    cursor.movePosition(QTextCursor.Left)
                    handled = True
                elif event.key() == Qt.Key_Up:
                    cursor.movePosition(QTextCursor.Up)
                    handled = True
                elif event.key() == Qt.Key_Down:
                    cursor.movePosition(QTextCursor.Down)
                    handled = True
                
                if handled:
                    self.setTextCursor(cursor)
                    return 
                
                super().keyPressEvent(event)
                return

            if event.key() == Qt.Key_Right:
                symbol_panel.navigate_grid(1, 0)
                return
            elif event.key() == Qt.Key_Left:
                symbol_panel.navigate_grid(-1, 0)
                return
            elif event.key() == Qt.Key_Up:
                symbol_panel.navigate_grid(0, -1)
                return
            elif event.key() == Qt.Key_Down:
                symbol_panel.navigate_grid(0, 1)
                return
            
            elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
                current_time = time.time()
                is_double_enter = (current_time - self.last_enter_time) < 0.5
                self.last_enter_time = current_time

                if is_double_enter:
                    dot_mode_enabled = self.editor_window.dot_mode_enabled
                    center_mode_enabled = symbol_panel.center_mode_active
                    
                    if dot_mode_enabled:
                        cursor = self.textCursor()
                        old_plain = self.toPlainText()
                        old_html = self.toHtml()
                        cursor.beginEditBlock()
                        cursor.insertText(" .")
                        cursor.insertBlock() 
                        final_position = cursor.position()
                        cursor.endEditBlock()
                        self.setTextCursor(cursor)
                        self.applyAlignment(center_mode_enabled)
                        QTimer.singleShot(10, lambda: self._handle_undo_stack_after_enter(old_html, old_plain, final_position))
                    else:
                        cursor = self.textCursor()
                        cursor.insertBlock()
                        self.setTextCursor(cursor)
                        self.applyAlignment(center_mode_enabled)
                else:
                    symbol_panel.trigger_current_nav_symbol()
                
                return 
        
        if event.key() == Qt.Key_Delete:
            if panel.isVisible() and symbol_panel.get_hovered_custom_button():
                symbol_panel.delete_hovered_button()
                return

        cursor = self.textCursor()
        is_first_char_position = not self.toPlainText() and cursor.position() == 0

        if is_first_char_position and event.text() and event.text().isalpha() and len(event.text()) == 1:
            is_shift_held = bool(event.modifiers() & Qt.ShiftModifier)
            if is_shift_held:
                self.insertPlainText(event.text().lower())
                return
            else:
                self.insertPlainText(event.text().upper())
                return

        is_caps_active = symbol_panel.caps_btn.isChecked() if panel else False

        if is_caps_active and event.text() and event.text().isalpha() and len(event.text()) == 1:
            current_block_text = cursor.block().text()
            pos_in_block = cursor.positionInBlock()
            text_before_cursor = current_block_text[:pos_in_block]

            if not text_before_cursor.strip():
                is_shift_held = bool(event.modifiers() & Qt.ShiftModifier)
                if not is_shift_held:
                    self.insertPlainText(event.text().upper())
                    return
        
        if event.key() == Qt.Key_Down:
            cursor = self.textCursor()
            block = cursor.block()
            if block.blockNumber() == self.document().blockCount() - 1:
                cursor.movePosition(QTextCursor.EndOfBlock)
                self.setTextCursor(cursor)
                return

            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
            next_char = cursor.selectedText()
            cursor.clearSelection()
            closing_chars = [')', ']', '}', '"', "'", '>', '`', '*', '_']
            if next_char in closing_chars:
                cursor.movePosition(QTextCursor.Right)
                self.setTextCursor(cursor)
                return
        
        if event.key() == Qt.Key_Up:
            cursor = self.textCursor()
            block = cursor.block()
            if block.blockNumber() == 0:
                cursor.movePosition(QTextCursor.StartOfBlock)
                self.setTextCursor(cursor)
                return

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            cursor = self.textCursor()
            current_block_text = cursor.block().text()
            pos_in_block = cursor.positionInBlock()
            text_after_cursor = current_block_text[pos_in_block:].strip()
            is_empty_line = not current_block_text.strip()

            dot_mode_enabled = panel.isVisible() and self.editor_window.dot_mode_enabled
            center_mode_enabled = panel.isVisible() and symbol_panel.center_mode_active

            if text_after_cursor or is_empty_line:
                super().keyPressEvent(event)
                self.applyAlignment(center_mode_enabled)
                return

            if dot_mode_enabled:
                old_plain = self.toPlainText()
                old_html = self.toHtml()
                cursor.beginEditBlock()
                cursor.insertText(" .")
                cursor.insertBlock() 
                final_position = cursor.position()
                cursor.endEditBlock()
                self.setTextCursor(cursor)
                self.applyAlignment(center_mode_enabled) 
                QTimer.singleShot(10, lambda: self._handle_undo_stack_after_enter(old_html, old_plain, final_position))
                return
            else:
                super().keyPressEvent(event)
                self.applyAlignment(center_mode_enabled)
                return

        super().keyPressEvent(event)

    def applyAlignment(self, is_center):
        cursor = self.textCursor()
        block_fmt = cursor.blockFormat()
        if is_center:
            block_fmt.setAlignment(Qt.AlignCenter)
        else:
            block_fmt.setAlignment(Qt.AlignLeft)
        cursor.setBlockFormat(block_fmt)
        self.setTextCursor(cursor)

    def _handle_undo_stack_after_enter(self, old_html, old_plain, final_position):
        new_plain = self.toPlainText()
        new_html = self.toHtml()
        if new_plain != old_plain:
            command = TextChangeCommand(self.editor_window, old_html, new_html, old_plain, new_plain, final_position)
            self.editor_window.undo_stack.push(command)
            self.editor_window.update_undo_redo_buttons()


# --- Ana Pencere ---
class TextEditorWindow(QWidget):
    DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')
    TEXT_WORK_DIR = os.path.join(DEFAULT_BASE_DIR, 'text')
    SETTINGS_FILE = "kavram_settings.cfg"
    current_file = None
    custom_symbols_list = []
    symbol_usage_data = {}
    
    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        self.undo_stack = UndoStack()
        self.current_search_matches = []
        self.current_match_index = -1
        self.terminal_dialog = None 

        QDir().mkpath(self.TEXT_WORK_DIR)

        self.dot_mode_enabled = True
        self.current_font_size = 10
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self.autoScrollDown)
        self.scroll_accumulator = 0.0
        self.scroll_speeds = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]
        self.current_scroll_speed_index = 4
        self.scroll_rate = self.scroll_speeds[self.current_scroll_speed_index]
        
        self.loaded_panel_visible = False
        self.loaded_dot_mode = True
        self.loaded_caps_mode = True
        self.loaded_center_mode = False
        self.loaded_nav_mode = False

        self.load_settings()
        self.initUI()
        
        self.apply_font_size()
        self.update_scroll_button_style()
        self.update_scroll_speed_button_text()
        self.update_undo_redo_buttons()

    def get_clean_content(self):
        doc = self.text_edit.document()
        blocks = []
        block = doc.begin()
        while block.isValid():
            text = block.text()
            alignment = block.blockFormat().alignment()
            if alignment & Qt.AlignCenter:
                blocks.append(f"<center>{text}</center>")
            else:
                blocks.append(text)
            block = block.next()
        return "\n".join(blocks)

    def set_clean_content(self, content):
        self.text_edit.blockSignals(True)
        self.text_edit.clear()
        
        cursor = self.text_edit.textCursor()
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            is_centered = False
            text = line
            
            center_match = re.match(r'^\s*<center>(.*)</center>\s*$', line, re.IGNORECASE)
            p_center_match = re.match(r'^\s*<p align="center">(.*)</p>\s*$', line, re.IGNORECASE)
            
            if center_match:
                is_centered = True
                text = center_match.group(1)
            elif p_center_match:
                is_centered = True
                text = p_center_match.group(1)
            
            if i > 0:
                cursor.insertBlock()
                
            cursor.insertText(text)
            
            # Hizalamayı uygula
            block_fmt = cursor.blockFormat()
            if is_centered:
                block_fmt.setAlignment(Qt.AlignCenter)
            else:
                block_fmt.setAlignment(Qt.AlignLeft)
            cursor.setBlockFormat(block_fmt)
            
        self.apply_font_size()
        self.text_edit.blockSignals(False)

    def _push_manual_undo(self):
        new_plain = self.text_edit.toPlainText()
        new_html = self.text_edit.toHtml()
        
        old_plain = ""
        old_html = ""
        if self.undo_stack.index >= 0:
             old_plain = self.undo_stack.stack[self.undo_stack.index].new_plain
             old_html = self.undo_stack.stack[self.undo_stack.index].new_html
        
        command = TextChangeCommand(self, old_html, new_html, old_plain, new_plain)
        self.undo_stack.push(command)
        self.update_undo_redo_buttons()

    def _apply_text_change_and_push_command(self, new_text):
        old_plain = self.text_edit.toPlainText()
        old_html = self.text_edit.toHtml()
        
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(new_text)
        self.apply_font_size()
        self.text_edit.blockSignals(False)
        
        new_plain = self.text_edit.toPlainText()
        new_html = self.text_edit.toHtml()
        
        command = TextChangeCommand(self, old_html, new_html, old_plain, new_plain)
        self.undo_stack.push(command)
        self.update_undo_redo_buttons()
        self.clearHighlights()

    def openTerminal(self):
        if not self.terminal_dialog:
            self.terminal_dialog = TerminalDialog(self)
            self.terminal_dialog.commandEntered.connect(self.handleTerminalCommand)
        self.terminal_dialog.show()
        self.terminal_dialog.raise_()
        self.terminal_dialog.activateWindow()

    def handleTerminalCommand(self, command):
        cmd = command.strip()
        cmd_lower = cmd.lower()
        
        if cmd_lower == "delete" or cmd_lower == "delete all":
             self.text_edit.clear()
             return

        patterns = {
            "arabic": r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+",
            "fars": r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]+", 
            "latine": r"[a-zA-Z\u00C0-\u024F\u1E00-\u1EFF]+", 
            "rus": r"[\u0400-\u04FF\u0500-\u052F]+", 
            "cin": r"[\u4E00-\u9FFF\u3400-\u4DBF]+", 
            "japonca": r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+", 
            "0-9": r"[0-9]+",
        }

        if cmd_lower == "delete sembol":
            self.process_deletion(r"[^\w\s\u0600-\u06FF\u0400-\u04FF]+") 
            return

        parts = cmd.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "delete":
            target = parts[1]
            target_lower = target.lower()
            
            if target_lower in patterns:
                self.process_deletion(patterns[target_lower])
            else:
                safe_target = re.escape(target)
                self.process_deletion(safe_target)

    def process_deletion(self, regex_pattern):
        cursor = self.text_edit.textCursor()
        cursor.beginEditBlock()
        doc = self.text_edit.document()
        block = doc.begin()
        
        while block.isValid():
            text = block.text()
            matches = list(re.finditer(regex_pattern, text))
            
            for match in reversed(matches):
                start = match.start()
                end = match.end()
                
                block_pos = block.position()
                cursor.setPosition(block_pos + start)
                cursor.setPosition(block_pos + end, QTextCursor.KeepAnchor)
                
                cursor.removeSelectedText()
            
            block = block.next()
        
        cursor.endEditBlock()
        self._push_manual_undo()

    def load_file_content(self, file_path):
        if not file_path or not os.path.exists(file_path): return

        self.current_file = file_path
        self.setWindowTitle(f"Kavram - {os.path.basename(file_path)}")
        try:
            with open(file_path, "r", encoding="utf-8", errors='replace') as file:
                content = file.read()
                
            # Eğer eski biçimdeki gibi hantal HTML yapısı içeriyorsa setHtml yap
            if "<!DOCTYPE HTML" in content or "style=\" font-family" in content:
                self.text_edit.setHtml(content)
            else:
                # Yeni temiz şablon veya düz metinse akıllı şablonu çözerek yükle
                self.set_clean_content(content)
                
            self.apply_font_size() # Font ayarının korunduğundan emin olmak için
            self.undo_stack = UndoStack() 
            self.update_undo_redo_buttons()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya yüklenirken hata oluştu:\n{str(e)}")

    def load_package(self, package_path):
        # Eski paket yükleme desteği, artık düz metin dosyası olarak yüklenecektir.
        self.load_file_content(package_path)

    def autoScrollDown(self):
        scroll_bar = self.text_edit.verticalScrollBar()
        self.scroll_accumulator += self.scroll_rate
        if self.scroll_accumulator >= 1.0:
            pixels_to_move = int(self.scroll_accumulator)
            self.scroll_accumulator -= pixels_to_move
            scroll_bar.setValue(scroll_bar.value() + pixels_to_move)
        if scroll_bar.value() >= scroll_bar.maximum():
            self.scroll_timer.stop()
            self.update_scroll_button_style()

    def load_settings(self):
        try:
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    loaded_size = data.get("font_size", 10)
                    self.current_font_size = max(15, min(72, loaded_size))
                    loaded_speed_index = data.get("scroll_speed_index", 4)
                    self.current_scroll_speed_index = max(0, min(len(self.scroll_speeds) - 1, loaded_speed_index))
                    self.scroll_rate = self.scroll_speeds[self.current_scroll_speed_index]
                    self.custom_symbols_list = data.get("custom_symbols", [])
                    self.symbol_usage_data = data.get("symbol_usage", {})
                    
                    self.loaded_panel_visible = data.get("panel_visible", False)
                    self.loaded_dot_mode = data.get("dot_mode_active", True)
                    self.loaded_caps_mode = data.get("caps_mode_active", True)
                    self.loaded_center_mode = data.get("center_mode_active", False)
                    self.loaded_nav_mode = data.get("nav_mode_active", False)
        except: pass

    def save_settings(self):
        current_customs = self.custom_symbols_list
        current_usage = self.symbol_usage_data
        
        current_panel_visible = getattr(self, 'loaded_panel_visible', False)
        current_dot = getattr(self, 'loaded_dot_mode', True)
        current_caps = getattr(self, 'loaded_caps_mode', True)
        current_center = getattr(self, 'loaded_center_mode', False)
        current_nav = getattr(self, 'loaded_nav_mode', False)
        
        if hasattr(self, 'assistant_panel'):
            current_usage = dict(self.assistant_panel.symbol_panel.usage_counts)
            current_customs = self.assistant_panel.symbol_panel.get_custom_symbols()
            current_panel_visible = self.assistant_panel.isVisible()
            current_dot = self.assistant_panel.symbol_panel.dot_btn.isChecked()
            current_caps = self.assistant_panel.symbol_panel.caps_btn.isChecked()
            current_center = self.assistant_panel.symbol_panel.center_btn.isChecked()
            current_nav = self.assistant_panel.symbol_panel.nav_btn.isChecked()

        settings = {
            "font_size": self.current_font_size,
            "scroll_speed_index": self.current_scroll_speed_index,
            "custom_symbols": current_customs,
            "symbol_usage": current_usage,
            "panel_visible": current_panel_visible,
            "dot_mode_active": current_dot,
            "caps_mode_active": current_caps,
            "center_mode_active": current_center,
            "nav_mode_active": current_nav
        }
        try:
            with open(self.SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=4)
        except: pass

    def handle_symbol_added_or_removed(self, text=None):
        self.save_settings()

    def handle_usage_changed(self):
        self.save_settings()

    def apply_font_size(self):
        self.text_edit.setStyleSheet(
            f"QTextEdit {{ background-color: #333; color: white; font-size: {self.current_font_size}px; border: none; }}"
            "QTextEdit:focus { outline: none; }"
        )
        font = self.text_edit.font()
        font.setPointSize(self.current_font_size)
        self.text_edit.setFont(font)
        self.text_edit.document().setDefaultFont(font)
        self.font_size_button.setText(str(self.current_font_size))
        
        # Değişen font boyutunu alt paneldeki butonlara ve yazılarına uygula
        if hasattr(self, 'assistant_panel') and self.assistant_panel:
            self.assistant_panel.symbol_panel.set_button_font_size(self.current_font_size)

    def changeFontSizeByWheel(self, event):
        if event.angleDelta().y() > 0:
            self.current_font_size = min(72, self.current_font_size + 1)
        else:
            self.current_font_size = max(15, self.current_font_size - 1)
        self.apply_font_size()
        self.save_settings()
        event.accept()

    def changeScrollSpeedByWheel(self, event):
        if event.angleDelta().y() > 0:
            self.current_scroll_speed_index = min(len(self.scroll_speeds) - 1, self.current_scroll_speed_index + 1)
        else:
            self.current_scroll_speed_index = max(0, self.current_scroll_speed_index - 1)

        self.setScrollSpeed(self.current_scroll_speed_index)
        self.save_settings()
        event.accept()

    def showFontSizeMenu(self):
        menu = QMenu(self)
        menu.setStyleSheet(self.menuStyle())
        standard_sizes = [15, 18, 20, 24, 28, 32, 36, 48, 72]
        for size in standard_sizes:
            action_text = f"{size} px"
            if size == self.current_font_size: action_text += " (Aktif)"
            action = QAction(action_text, self)
            action.triggered.connect(lambda checked, s=size: self.setFontSize(s))
            menu.addAction(action)
        point = self.font_size_button.mapToGlobal(QPoint(0, self.font_size_button.height()))
        menu.exec_(point)

    def setFontSize(self, size):
        self.current_font_size = min(72, size)
        self.apply_font_size()
        self.save_settings()

    def update_undo_redo_buttons(self):
        if self.undo_stack.can_undo():
            self.undo_button.setEnabled(True)
            self.undo_button.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20, color="#ccc"))
        else:
            self.undo_button.setEnabled(False)
            self.undo_button.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20, color="#555"))

        if self.undo_stack.can_redo():
            self.redo_button.setEnabled(True)
            self.redo_button.setIcon(create_svg_icon(SVG_REDO_ICON, size=20, color="#ccc"))
        else:
            self.redo_button.setEnabled(False)
            self.redo_button.setIcon(create_svg_icon(SVG_REDO_ICON, size=20, color="#555"))

    def undo_action(self):
        if self.undo_stack.undo():
            self.update_undo_redo_buttons()

    def redo_action(self):
        if self.undo_stack.redo():
            self.update_undo_redo_buttons()

    def update_scroll_speed_button_text(self):
        self.scroll_speed_button.setText(str(self.scroll_rate))

    def _push_text_to_undo_stack(self):
        new_plain = self.text_edit.toPlainText()
        new_html = self.text_edit.toHtml()
        
        old_plain = ""
        old_html = ""
        if self.undo_stack.index >= 0 and self.undo_stack.index < len(self.undo_stack.stack):
            old_plain = self.undo_stack.stack[self.undo_stack.index].new_plain
            old_html = self.undo_stack.stack[self.undo_stack.index].new_html
        elif not self.undo_stack.stack and self.undo_stack.index == -1 and not new_plain:
            return

        if new_plain != old_plain:
            command = TextChangeCommand(self, old_html, new_html, old_plain, new_plain, final_cursor_pos=self.text_edit.textCursor().position())
            self.undo_stack.push(command)
            self.update_undo_redo_buttons()

    def initUI(self):
        self.setWindowTitle("Kavram")
        self.resize(1000, 700) 
        self.setStyleSheet("background-color: #222; border: none;")

        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("background-color: #222; border-bottom: 2px solid #555;")
        toolbar_frame.setFixedHeight(40)
        toolbar_frame_layout = QHBoxLayout(toolbar_frame)
        toolbar_frame_layout.setContentsMargins(10, 5, 10, 5)

        self.file_button = QPushButton("File")
        self.file_button.setStyleSheet(self.buttonStyle())
        self.file_button.setFixedSize(90, 30)
        self.file_button.clicked.connect(self.openFiles)
        toolbar_frame_layout.addWidget(self.file_button, alignment=Qt.AlignLeft)

        self.save_button = QPushButton()
        self.save_button.setIcon(create_svg_icon(SVG_SAVE_ICON, size=20))
        self.save_button.setStyleSheet(self.buttonStyleMini())
        self.save_button.setFixedSize(30, 30)
        self.save_button.setToolTip("Kaydet")
        self.save_button.clicked.connect(self.quickSave)
        toolbar_frame_layout.addWidget(self.save_button, alignment=Qt.AlignLeft)

        self.text_edit = CustomTextEdit(self)
        self.text_edit.setTextColor(QColor("white"))
        self.text_edit.textChanged.connect(self.updateLineCount)
        self.text_edit.textChanged.connect(self.handleTextChange)

        self.undo_button = QPushButton()
        self.undo_button.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20))
        self.undo_button.setStyleSheet(self.buttonStyleMini())
        self.undo_button.setFixedSize(30, 30)
        self.undo_button.clicked.connect(self.undo_action)
        toolbar_frame_layout.addWidget(self.undo_button, alignment=Qt.AlignLeft)

        self.redo_button = QPushButton()
        self.redo_button.setIcon(create_svg_icon(SVG_REDO_ICON, size=20))
        self.redo_button.setStyleSheet(self.buttonStyleMini())
        self.redo_button.setFixedSize(30, 30)
        self.redo_button.clicked.connect(self.redo_action)
        toolbar_frame_layout.addWidget(self.redo_button, alignment=Qt.AlignLeft)

        self.font_size_button = QPushButton(str(self.current_font_size))
        self.font_size_button.setStyleSheet(self.buttonStyle())
        self.font_size_button.setFixedSize(70, 30)
        self.font_size_button.clicked.connect(self.showFontSizeMenu)
        self.font_size_button.wheelEvent = self.changeFontSizeByWheel
        toolbar_frame_layout.addWidget(self.font_size_button, alignment=Qt.AlignLeft)

        self.symbol_toggle_button = QPushButton("/")
        self.symbol_toggle_button.setStyleSheet(self.buttonStyleMini())
        self.symbol_toggle_button.setFixedSize(30, 30)
        self.symbol_toggle_button.clicked.connect(self.toggleSymbolPanel)
        toolbar_frame_layout.addWidget(self.symbol_toggle_button, alignment=Qt.AlignLeft)

        self.read_mode_button = QPushButton("I")
        self.read_mode_button.setStyleSheet(self.buttonStyleMini() + " font-weight: bold; color: white;")
        self.read_mode_button.setFixedSize(30, 30)
        self.read_mode_button.setToolTip("Auto Scroll / Read Mode")
        self.read_mode_button.clicked.connect(self.toggleAutoScroll)
        toolbar_frame_layout.addWidget(self.read_mode_button, alignment=Qt.AlignLeft)

        self.scroll_speed_button = QPushButton(str(self.scroll_rate))
        self.scroll_speed_button.setStyleSheet(self.buttonStyleMini())
        self.scroll_speed_button.setFixedSize(40, 30)
        self.scroll_speed_button.clicked.connect(self.showScrollSpeedMenu)
        self.scroll_speed_button.wheelEvent = self.changeScrollSpeedByWheel
        toolbar_frame_layout.addWidget(self.scroll_speed_button, alignment=Qt.AlignLeft)

        self.terminal_button = QPushButton("Terminal")
        self.terminal_button.setStyleSheet(self.buttonStyle())
        self.terminal_button.setFixedSize(110, 30)
        self.terminal_button.clicked.connect(self.openTerminal)
        toolbar_frame_layout.addWidget(self.terminal_button, alignment=Qt.AlignLeft)

        self.line_count_label = QLabel("Line: 0")
        self.line_count_label.setStyleSheet("color: white; font-size: 14px;")
        toolbar_frame_layout.addWidget(self.line_count_label, alignment=Qt.AlignLeft)

        toolbar_frame_layout.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ara...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #444; color: white; border: 1px solid #555;
                border-radius: 5px; padding: 3px; font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #777;
            }
        """)
        self.search_input.setFixedSize(150, 28)
        self.search_input.returnPressed.connect(self.startSearch)
        toolbar_frame_layout.addWidget(self.search_input, alignment=Qt.AlignRight)

        self.search_button = QPushButton()
        self.search_button.setIcon(create_svg_icon(SVG_SEARCH_ICON, size=20))
        self.search_button.setStyleSheet(self.buttonStyleMini())
        self.search_button.setFixedSize(28, 28)
        self.search_button.clicked.connect(self.startSearch)
        toolbar_frame_layout.addWidget(self.search_button, alignment=Qt.AlignRight)

        self.prev_match_button = QPushButton()
        self.prev_match_button.setIcon(create_svg_icon(SVG_ARROW_UP_ICON, size=20))
        self.prev_match_button.setStyleSheet(self.buttonStyleMini())
        self.prev_match_button.setFixedSize(28, 28)
        self.prev_match_button.clicked.connect(self.findPrevious)
        toolbar_frame_layout.addWidget(self.prev_match_button, alignment=Qt.AlignRight)

        self.next_match_button = QPushButton()
        self.next_match_button.setIcon(create_svg_icon(SVG_ARROW_DOWN_ICON, size=20))
        self.next_match_button.setStyleSheet(self.buttonStyleMini())
        self.next_match_button.setFixedSize(28, 28)
        self.next_match_button.clicked.connect(self.findNext)
        toolbar_frame_layout.addWidget(self.next_match_button, alignment=Qt.AlignRight)

        self.export_button = QPushButton("Export")
        self.export_button.setStyleSheet(self.buttonStyle())
        self.export_button.setFixedSize(90, 30)
        self.export_button.clicked.connect(self.exportContent)
        toolbar_frame_layout.addWidget(self.export_button, alignment=Qt.AlignRight)

        self.text_button = QPushButton("Text")
        self.text_button.setStyleSheet(self.buttonStyle())
        self.text_button.setFixedSize(90, 30)
        self.text_button.clicked.connect(self.triggerCoreSwitcher)
        toolbar_frame_layout.addWidget(self.text_button, alignment=Qt.AlignRight)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #555; border-radius: 6px; text-align: center; color: white; background-color: #222; height: 10px; }
            QProgressBar::chunk { background-color: #666; }
        """)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.hide()

        self.assistant_panel = SmartAssistantPanel(self)
        self.assistant_panel.hide()
        self.assistant_panel.symbol_panel.symbolClicked.connect(self.insertSymbolFromPanel)
        self.assistant_panel.symbol_panel.dotModeChanged.connect(self.updateDotMode)
        self.assistant_panel.symbol_panel.customSymbolAdded.connect(self.handle_symbol_added_or_removed)
        self.assistant_panel.symbol_panel.customSymbolDeleted.connect(self.handle_symbol_added_or_removed)
        self.assistant_panel.symbol_panel.usageCountChanged.connect(self.handle_usage_changed)

        self.assistant_panel.symbol_panel.usage_counts.update(self.symbol_usage_data)

        for sym in self.custom_symbols_list:
             self.assistant_panel.symbol_panel.add_custom_symbol(sym)

        if getattr(self, 'loaded_panel_visible', False):
            self.assistant_panel.show()
            self.assistant_panel.symbol_panel.ensure_initialized()
        else:
            self.assistant_panel.hide()

        panel = self.assistant_panel.symbol_panel
        panel.dot_btn.setChecked(getattr(self, 'loaded_dot_mode', True))
        panel.toggle_dot_mode()

        panel.caps_btn.setChecked(getattr(self, 'loaded_caps_mode', True))
        panel.update_caps_btn_style()

        panel.center_btn.setChecked(getattr(self, 'loaded_center_mode', False))
        panel.toggle_center_mode()

        panel.nav_btn.setChecked(getattr(self, 'loaded_nav_mode', False))
        panel.toggle_nav_mode()

        panel.dot_btn.clicked.connect(self.save_settings)
        panel.caps_btn.clicked.connect(self.save_settings)
        panel.center_btn.clicked.connect(self.save_settings)
        panel.nav_btn.clicked.connect(self.save_settings)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(toolbar_frame)
        main_layout.addWidget(self.text_edit) 
        main_layout.addWidget(self.assistant_panel)
        main_layout.addWidget(self.progress_bar)
        self.setLayout(main_layout)

        # --- Geri Al / Yinele Kısayolları (Pencere Seviyesi) ---
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.setContext(Qt.WindowShortcut)
        undo_shortcut.activated.connect(self.undo_action)
        
        redo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        redo_shortcut.setContext(Qt.WindowShortcut)
        redo_shortcut.activated.connect(self.redo_action)
        
        redo_shortcut_std = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo_shortcut_std.setContext(Qt.WindowShortcut)
        redo_shortcut_std.activated.connect(self.redo_action)

    def quickSave(self):
        """Hızlı kaydet: dosya açık ise doğrudan kaydet, değilse File Manager'da export."""
        if self.current_file:
            self.save_package(self.current_file)
        else:
            self.exportContent("Hızlı Kaydet")

    def updateDotMode(self, active):
        self.dot_mode_enabled = active

    def toggleSymbolPanel(self):
        if self.assistant_panel.isVisible():
            self.assistant_panel.hide()
        else:
            self.assistant_panel.show()
            self.assistant_panel.symbol_panel.ensure_initialized()
            self.text_edit.setFocus()
        self.save_settings() 

    def insertSymbolFromPanel(self, prefix, suffix, should_close):
        cursor = self.text_edit.textCursor()
        old_plain = self.text_edit.toPlainText()
        old_html = self.text_edit.toHtml()

        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            new_text = f"{prefix}{selected_text}{suffix}"
            cursor.insertText(new_text)
        else:
            cursor.insertText(f"{prefix}{suffix}")
            if suffix:
                cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, len(suffix))
                self.text_edit.setTextCursor(cursor)

        self.text_edit.ensureCursorVisible()
        self.text_edit.setFocus()

        new_plain = self.text_edit.toPlainText()
        new_html = self.text_edit.toHtml()

        if new_plain != old_plain:
            command = TextChangeCommand(self, old_html, new_html, old_plain, new_plain, cursor.position())
            self.undo_stack.push(command)
            self.update_undo_redo_buttons()

    def update_scroll_button_style(self):
        style = self.buttonStyleMini()
        if self.scroll_timer.isActive():
            style = style.replace("background-color: transparent", "background-color: #555")
        self.read_mode_button.setStyleSheet(style)

    def toggleAutoScroll(self):
        if self.scroll_timer.isActive():
            self.scroll_timer.stop()
        else:
            self.scroll_timer.start(50)
        self.update_scroll_button_style()

    def setScrollSpeed(self, speed_index):
        self.current_scroll_speed_index = speed_index
        self.scroll_rate = self.scroll_speeds[speed_index]
        self.save_settings()
        self.update_scroll_button_style()
        self.update_scroll_speed_button_text()

    def menuStyle(self):
        return """
            QMenu { background-color: #333; border: 1px solid #555; color: white; padding: 5px; }
            QMenu::item { padding: 5px 20px; min-width: 100px; }
            QMenu::item:selected { background-color: #555; }
        """

    def showScrollSpeedMenu(self):
        menu = QMenu(self)
        menu.setStyleSheet(self.menuStyle())
        for i, speed in enumerate(self.scroll_speeds):
            action_text = f"Hız: {speed}"
            if i == self.current_scroll_speed_index: action_text += " (Aktif)"
            action = QAction(action_text, self)
            action.setCheckable(True)
            if i == self.current_scroll_speed_index: action.setChecked(True)
            action.triggered.connect(lambda checked, idx=i: self.setScrollSpeed(idx))
            menu.addAction(action)
        point = self.scroll_speed_button.mapToGlobal(QPoint(0, self.scroll_speed_button.height()))
        menu.exec_(point)

    def handleTextChange(self):
        if hasattr(self, '_save_timer'): self._save_timer.stop()
        else:
            self._save_timer = QTimer(self)
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self._push_text_to_undo_stack)
        self._save_timer.start(500)

    def updateLineCount(self):
        line_count = self.text_edit.document().blockCount()
        self.line_count_label.setText(f"Line: {line_count}")

    def buttonStyle(self):
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 14px; font-weight: bold;
                border: 2px solid #555; border-radius: 8px; padding: 5px 20px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

    def buttonStyleMini(self):
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 16px;
                border: 2px solid #555; border-radius: 8px; padding: 2px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

    def startSearch(self):
        search_term = self.search_input.text()
        if not search_term:
            self.clearHighlights()
            return
        self.clearHighlights()
        self.current_search_matches = []
        document = self.text_edit.document()
        cursor = QTextCursor(document)
        extra_selections = []
        format_ = QTextCharFormat()
        format_.setBackground(QColor("#FFC107"))
        while not cursor.isNull() and not cursor.atEnd():
            cursor = document.find(search_term, cursor)
            if not cursor.isNull():
                selection = QTextEdit.ExtraSelection()
                selection.cursor = cursor
                selection.format = format_
                extra_selections.append(selection)
                self.current_search_matches.append(cursor.position())
        self.text_edit.setExtraSelections(extra_selections)
        if self.current_search_matches:
            self.current_match_index = 0
            self.highlightCurrentMatch()
        else: self.current_match_index = -1

    def clearHighlights(self):
        self.text_edit.setExtraSelections([])
        self.current_search_matches = []
        self.current_match_index = -1

    def highlightCurrentMatch(self):
        if not self.current_search_matches or self.current_match_index == -1: return
        extra_selections = []
        search_term = self.search_input.text()
        standard_format = QTextCharFormat()
        standard_format.setBackground(QColor("#FFC107"))
        current_format = QTextCharFormat()
        current_format.setBackground(QColor("#FF5722"))
        document = self.text_edit.document()
        for i, pos in enumerate(self.current_search_matches):
            cursor = QTextCursor(document)
            cursor.setPosition(pos - len(search_term), QTextCursor.MoveAnchor)
            cursor.setPosition(pos, QTextCursor.KeepAnchor)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format = current_format if i == self.current_match_index else standard_format
            extra_selections.append(selection)
        self.text_edit.setExtraSelections(extra_selections)

        cursor_to_move = QTextCursor(document)
        cursor_to_move.setPosition(self.current_search_matches[self.current_match_index])
        self.text_edit.setTextCursor(cursor_to_move)

    def findNext(self):
        if not self.current_search_matches:
            self.startSearch()
            if not self.current_search_matches: return
        self.current_match_index = (self.current_match_index + 1) % len(self.current_search_matches)
        self.highlightCurrentMatch()

    def findPrevious(self):
        if not self.current_search_matches:
            self.startSearch()
            if not self.current_search_matches: return
        self.current_match_index = (self.current_match_index - 1 + len(self.current_search_matches)) % len(self.current_search_matches)
        self.highlightCurrentMatch()

    def triggerCoreSwitcher(self):
        if self.core_window_ref and hasattr(self.core_window_ref, 'switch_to_core'):
            self.core_window_ref.switch_to_core('core')
            return
        main_window = self.window()
        if hasattr(main_window, 'showSwitcher'):
            main_window.showSwitcher()

    def openFiles(self):
        """File Manager üzerinden dosya aç. Varsayılan filtre .txr, yanında .txt de göster."""
        if not self.core_window_ref:
            QMessageBox.warning(self, "Hata", "CoreWindow referansı yok.")
            return
        # Editör bağlamı Text (.txr) olarak ayarlanır, ancak filtre açılır listede .txt de bulunur.
        manager = self.core_window_ref.open_file_manager_for_editor("Text", all_files=False)
        if manager:
            # Daha önce bağlanmış sinyalleri temizle
            try:
                manager.fileSelected.disconnect(self.load_file_content)
            except (TypeError, RuntimeError):
                pass
            manager.fileSelected.connect(self.load_file_content)

    def saveContent(self):
        """Eski QFileDialog ile kaydet - artık kullanılmıyor, exportContent ile değiştirildi."""
        self.exportContent("Kaydet")

    def save_package(self, package_path):
        try:
            # Sadece ortalanmış kısımları işaretleyen hafif ve tertemiz metin biçimini kaydet
            content = self.get_clean_content()
            with open(package_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.current_file = package_path
            self.setWindowTitle(f"Kavram - {os.path.basename(package_path)}")
            # Tek bildirim: save_package içinde
            QMessageBox.information(self, "Kaydedildi", f"Dosya başarıyla kaydedildi.\n{package_path}")
        except Exception as e:
            QMessageBox.critical(self, "Kaydetme Hatası", str(e))

    def exportContent(self, title=None):
        """File Manager üzerinden dışa aktar (sadece .txr)."""
        if not self.core_window_ref:
            QMessageBox.warning(self, "Hata", "CoreWindow referansı yok.")
            return

        def export_to_path(path, compression=None):
            try:
                self.save_package(path)
                return True
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Kaydedilemedi: {e}")
                return False

        manager = self.core_window_ref.open_file_manager_for_export(
            exporter=export_to_path,
            compression=None,  # metin için sıkıştırma yok
            default_export_name="belge",
            filter_extensions={".txr"}
        )
        # exportCompleted bağlantısı KALDIRILDI, çünkü save_package zaten bildirim gösteriyor
        # Sadece iptal durumu için
        if manager:
            manager.exportCancelled.connect(
                lambda: QMessageBox.information(self, "İptal", "Kaydetme iptal edildi.")
            )

    def closeEvent(self, event):
        self.save_settings()
        event.accept()

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

