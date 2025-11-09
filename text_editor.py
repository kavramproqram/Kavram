# Kavram 1.0.0
# Copyright (C) 2025-09-01 Kavram or Contributors
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
# Copyright (C) 2025-09-01 Kavram veya Contributors
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
import PyPDF2
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QTextEdit, QPushButton,
    QFileDialog, QDialog, QLabel, QApplication, QMessageBox, QProgressBar,
    QLineEdit, QAction, QShortcut
)
from PyQt5.QtGui import (
    QColor, QIcon, QPixmap, QPainter, QTextCharFormat, QTextCursor, QTextDocument, QKeySequence
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDir, QByteArray
from PyQt5.QtSvg import QSvgRenderer

# --- Yardımcı Fonksiyonlar ve Sabitler ---

# SVG ikonları tanımlıyoruz
SVG_UNDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19C15.866 19 19 15.866 19 12C19 8.13401 15.866 5 12 5C8.13401 5 5 8.13401 5 12C5 13.7909 5.70014 15.4293 6.84594 16.6386L5 18M5 18H9M5 18V14" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_REDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5C8.13401 5 5 8.13401 5 12C5 15.866 8.13401 19 12 19C15.866 19 19 15.866 19 12C19 10.2091 18.2999 8.57074 17.1541 7.3614L19 6M19 6H15M19 6V10" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_SEARCH_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M11 19C15.4183 19 19 15.4183 19 11C19 6.58172 15.4183 3 11 3C6.58172 3 3 6.58172 3 11C3 15.4183 6.58172 19 11 19ZM11 19C12.0294 19 12.9934 18.7909 13.8824 18.4018L21 21L19 13.8824C18.7909 12.9934 19 12.0294 19 11C19 6.58172 15.4183 3 11 3C6.58172 3 3 6.58172 3 11C3 15.4183 6.58172 19 11 19Z" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_ARROW_UP_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19V5M5 12L12 5L19 12" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_ARROW_DOWN_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5V19M5 12L12 19L19 12" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""


def create_svg_icon(svg_content, size=20, color="#eee"):
    """Verilen SVG içeriğinden bir QIcon oluşturur."""
    modified_svg_content = svg_content.replace('stroke="#eee"', f'stroke="{color}"').replace('fill="#eee"', f'fill="{color}"')
    renderer = QSvgRenderer(QByteArray(modified_svg_content.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

# --- Özel Geri Al/Yinele Sistemi İçin Sınıflar ---
class TextChangeCommand:
    """Metin değişikliklerini geri al/yinele için bir komut."""
    def __init__(self, editor_instance, old_text, new_text):
        self.editor = editor_instance
        self.old_text = old_text
        self.new_text = new_text

    def do(self):
        """Komutu uygular (yeni metni ayarlar)."""
        # Sinyal döngüsünü engellemek için blockSignals kullanıyoruz
        self.editor.text_edit.blockSignals(True)
        self.editor.text_edit.setPlainText(self.new_text)
        self.editor.text_edit.blockSignals(False)
        self.editor.clearHighlights() # Değişiklik yapıldığında vurguları temizle

    def undo(self):
        """Komutun etkilerini geri alır (eski metni ayarlar)."""
        self.editor.text_edit.blockSignals(True)
        self.editor.text_edit.setPlainText(self.old_text)
        self.editor.text_edit.blockSignals(False)
        self.editor.clearHighlights() # Geri alma yapıldığında vurguları temizle

class UndoStack:
    """Metin değişiklik komutlarını yöneten geri al/yinele yığını."""
    def __init__(self):
        self.stack = []
        self.index = -1 # Mevcut komutun yığındaki indeksi
        self.max_size = 50 # Yığın boyutu limiti

    def push(self, command):
        """Yeni bir komutu yığına ekler ve uygular."""
        # Geçerli indeksten sonraki tüm komutları sil (yeni bir işlem geri alma sonrası yapılırsa)
        while len(self.stack) > self.index + 1:
            self.stack.pop()

        self.stack.append(command)
        self.index += 1

        # Yığın boyutunu sınırla
        if len(self.stack) > self.max_size:
            self.stack.pop(0) # En eski komutu sil
            self.index -= 1

        command.do() # Komutu hemen uygula

    def undo(self):
        """Son komutu geri alır."""
        if self.index >= 0:
            command = self.stack[self.index]
            command.undo()
            self.index -= 1

    def redo(self):
        """Geri alınan son komutu yeniden uygular."""
        if self.index < len(self.stack) - 1:
            self.index += 1
            command = self.stack[self.index]
            command.do()

class TerminalTextEdit(QTextEdit):
    commandEntered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.history = []
        self.history_index = -1
        # self.setUndoRedoEnabled(True) # Bu özellik ana QTextEdit'te yönetiliyor, burada gerek yok

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            if self.history:
                if self.history_index == -1:
                    self.history_index = len(self.history) - 1
                elif self.history_index > 0:
                    self.history_index -= 1
                self.setPlainText(self.history[self.history_index])
                self.selectAll()
            return
        elif event.key() == Qt.Key_Down:
            if self.history:
                if self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    self.setPlainText(self.history[self.history_index])
                else:
                    self.history_index = -1
                    self.clear()
            return
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            command = self.toPlainText().strip()
            if command:
                self.history.append(command)
                self.history_index = -1
                self.insertPlainText("\n")
                self.commandEntered.emit(command.lower())
            else:
                self.insertPlainText("\n")
            return
        else:
            super().keyPressEvent(event)

class TerminalDialog(QDialog):
    commandEntered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Terminal")
        self.setStyleSheet("background-color: black; color: white;")
        self.resize(600, 400)
        layout = QVBoxLayout(self)
        self.terminal_text = TerminalTextEdit(self)
        self.terminal_text.setStyleSheet("background-color: black; color: white; font-size: 14px; border: none;")
        self.terminal_text.setFocusPolicy(Qt.StrongFocus)
        self.terminal_text.setFocus()
        self.terminal_text.commandEntered.connect(self.handleCommand)
        layout.addWidget(self.terminal_text)
        self.setLayout(layout)

    def handleCommand(self, cmd):
        self.commandEntered.emit(cmd)
        self.terminal_text.clear()

class TextEditorWindow(QWidget):
    DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')

    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        self.undo_stack = UndoStack() # Özel UndoStack'i başlatıyoruz
        self.current_search_matches = []
        self.current_match_index = -1
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Kavram")
        self.resize(800, 600)
        self.setStyleSheet("background-color: #222; border: none;")

        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("background-color: #222; border-bottom: 2px solid #555;")
        toolbar_frame.setFixedHeight(40)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)

        self.file_button = QPushButton("File")
        self.file_button.setStyleSheet(self.buttonStyle())
        self.file_button.setFixedSize(90, 30)
        self.file_button.clicked.connect(self.openFiles)
        toolbar_layout.addWidget(self.file_button, alignment=Qt.AlignLeft)

        # QTextEdit'i diğer butonlardan önce oluşturuyoruz
        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet(
            "QTextEdit { background-color: #333; color: white; font-size: 16px; border: none; }"
            "QTextEdit:focus { outline: none; }"
        )
        self.text_edit.setTextColor(QColor("white"))
        self.text_edit.textChanged.connect(self.updateLineCount)
        # QTextEdit'in kendi undo/redo'sunu kapatıyoruz, özel sistem kullanacağız
        self.text_edit.setUndoRedoEnabled(False)

        # Geri Al/Yinele butonları - şimdi özel undo_stack'e bağlı
        self.undo_button = QPushButton()
        self.undo_button.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20))
        self.undo_button.setStyleSheet(self.buttonStyleMini())
        self.undo_button.setFixedSize(30, 30)
        self.undo_button.clicked.connect(self.undo_stack.undo) # Bağlantı düzeltildi
        toolbar_layout.addWidget(self.undo_button, alignment=Qt.AlignLeft)

        self.redo_button = QPushButton()
        self.redo_button.setIcon(create_svg_icon(SVG_REDO_ICON, size=20))
        self.redo_button.setStyleSheet(self.buttonStyleMini())
        self.redo_button.setFixedSize(30, 30)
        self.redo_button.clicked.connect(self.undo_stack.redo) # Bağlantı düzeltildi
        toolbar_layout.addWidget(self.redo_button, alignment=Qt.AlignLeft)

        self.terminal_button = QPushButton("Terminal")
        self.terminal_button.setStyleSheet(self.buttonStyle())
        self.terminal_button.setFixedSize(110, 30)
        self.terminal_button.clicked.connect(self.openTerminal)
        toolbar_layout.addWidget(self.terminal_button, alignment=Qt.AlignLeft)

        self.line_count_label = QLabel("Line: 0")
        self.line_count_label.setStyleSheet("color: white; font-size: 14px;")
        toolbar_layout.addWidget(self.line_count_label, alignment=Qt.AlignLeft)

        toolbar_layout.addStretch()

        # Arama bölümü
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
        toolbar_layout.addWidget(self.search_input, alignment=Qt.AlignRight)

        self.search_button = QPushButton()
        self.search_button.setIcon(create_svg_icon(SVG_SEARCH_ICON, size=20))
        self.search_button.setStyleSheet(self.buttonStyleMini())
        self.search_button.setFixedSize(28, 28)
        self.search_button.clicked.connect(self.startSearch)
        toolbar_layout.addWidget(self.search_button, alignment=Qt.AlignRight)

        self.prev_match_button = QPushButton()
        self.prev_match_button.setIcon(create_svg_icon(SVG_ARROW_UP_ICON, size=20))
        self.prev_match_button.setStyleSheet(self.buttonStyleMini())
        self.prev_match_button.setFixedSize(28, 28)
        self.prev_match_button.clicked.connect(self.findPrevious)
        toolbar_layout.addWidget(self.prev_match_button, alignment=Qt.AlignRight)

        self.next_match_button = QPushButton()
        self.next_match_button.setIcon(create_svg_icon(SVG_ARROW_DOWN_ICON, size=20))
        self.next_match_button.setStyleSheet(self.buttonStyleMini())
        self.next_match_button.setFixedSize(28, 28)
        self.next_match_button.clicked.connect(self.findNext)
        toolbar_layout.addWidget(self.next_match_button, alignment=Qt.AlignRight)

        self.export_button = QPushButton("Export")
        self.export_button.setStyleSheet(self.buttonStyle())
        self.export_button.setFixedSize(90, 30)
        self.export_button.clicked.connect(self.exportContent)
        toolbar_layout.addWidget(self.export_button, alignment=Qt.AlignRight)

        self.text_button = QPushButton("Text")
        self.text_button.setStyleSheet(self.buttonStyle())
        self.text_button.setFixedSize(90, 30)
        self.text_button.clicked.connect(self.triggerCoreSwitcher)
        toolbar_layout.addWidget(self.text_button, alignment=Qt.AlignRight)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 6px;
                text-align: center;
                color: white;
                background-color: #222;
                height: 10px;
            }
            QProgressBar::chunk {
                background-color: #666;
            }
        """)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(10)
        self.progress_bar.hide()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(toolbar_frame)
        main_layout.addWidget(self.text_edit)
        main_layout.addWidget(self.progress_bar)
        self.setLayout(main_layout)

        # --- Kısayolları QShortcut ile Ayarla ---
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.undo_stack.undo)

        redo_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Z"), self)
        redo_shortcut.activated.connect(self.undo_stack.redo)

        # Standart Ctrl+Y kısayolunu da ekleyelim
        redo_shortcut_std = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo_shortcut_std.activated.connect(self.undo_stack.redo)


    def updateLineCount(self):
        line_count = self.text_edit.document().blockCount()
        self.line_count_label.setText(f"Line: {line_count}")

    def buttonStyle(self):
        return """
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 5px 20px;
            }
            QPushButton:hover {
                background-color: #444;
            }
            QPushButton:pressed {
                background-color: #666;
            }
        """

    def buttonStyleMini(self):
        return """
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 16px;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #444;
            }
            QPushButton:pressed {
                background-color: #666;
            }
        """

    def openTerminal(self):
        self.terminal_dialog = TerminalDialog(self)
        self.terminal_dialog.commandEntered.connect(self.handleTerminalCommand)
        self.terminal_dialog.show()

    # Tüm delete fonksiyonlarını TextChangeCommand ile sarmalıyoruz
    def _apply_text_change_and_push_command(self, new_text):
        old_text = self.text_edit.toPlainText()
        command = TextChangeCommand(self, old_text, new_text)
        self.undo_stack.push(command)
        self.clearHighlights() # Metin değiştiğinde vurguları temizle

    def handleTerminalCommand(self, command):
        if command in ("arabic delete", "delete arabic"):
            self.deleteArabic()
        elif command in ("latine delete", "delete latine"):
            self.deleteLatine()
        elif command in ("rus delete", "delete rus"):
            self.deleteRussian()
        elif command in ("0-9 delete", "delete 0-9"):
            self.deleteDigits()
        elif command in ("a-z delete", "delete a-z"):
            self.deleteLowercase()
        elif command in ("A-Z delete", "delete A-Z"):
            self.deleteUppercase()
        elif command in ("{ delete", "{} delete"):
            self.deleteCurlyBraces()
        elif command in ("< delete", "<> delete"):
            self.deleteAngleBrackets()
        elif command in ("( delete", "() delete"):
            self.deleteParentheses()
        elif command in ("- delete", "delete -"):
            self.deleteHyphen()
        elif command in ("_ delete", "delete _"):
            self.deleteUnderscore()
        elif command in ("? delete", "delete ?"):
            self.deleteQuestionMark()
        elif command in ("! delete", "delete !"):
            self.deleteExclamationMark()
        elif command in ("' delete", "delete '"):
            self.deleteSingleQuote()
        elif command in ("^ delete", "delete ^"):
            self.deleteCaret()
        elif command in ("+ delete", "delete +"):
            self.deletePlus()
        elif command in ("% delete", "delete %"):
            self.deletePercent()
        elif command in ("& delete", "delete &"):
            self.deleteAmpersand()
        elif command in ("/ delete", "delete /"):
            self.deleteSlash()
        elif command in ("= delete", "delete ="):
            self.deleteEquals()
        elif command in (". delete", "delete ."):
            self.deleteDot()
        elif command in (": delete", "delete :"):
            self.deleteColon()
        elif command in ('" delete', 'delete "'):
            self.deleteDoubleQuote()
        elif command in ("é delete", "delete é"):
            self.deleteEAcute()
        elif command in ("| delete", "delete |"):
            self.deletePipe()
        elif command.startswith("delete ") or command.endswith(" delete"):
            chars_to_delete = ""
            if command.startswith("delete "):
                chars_to_delete = command[len("delete "):].strip()
            elif command.endswith(" delete"):
                chars_to_delete = command[:-len(" delete")].strip()

            if chars_to_delete:
                self.deleteCharacters(chars_to_delete)
            else:
                QMessageBox.information(self, "Komut Bilgisi", f"'{command}' komutu için silinecek karakter belirtilmemiş.")
        else:
            QMessageBox.information(self, "Komut Bilgisi", f"'{command}' komutu tanımlı değil.")

    def deleteArabic(self):
        old_text = self.text_edit.toPlainText()
        lines = old_text.splitlines(keepends=True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(lines))
        self.progress_bar.show()
        arabic_range = r'\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF'
        new_lines = []
        for i, line in enumerate(lines):
            line = re.sub(r'\[[^\]]*?[' + arabic_range + r'][^\]]*?\]', '', line)
            line = re.sub(r'\([^\)]*?[' + arabic_range + r'][^\)]*?\)', '', line)
            tokens = re.split(r'(\s+)', line)
            new_tokens = []
            for token in tokens:
                if token.strip() and re.search(r'[' + arabic_range + r']', token):
                    new_tokens.append('')
                else:
                    new_tokens.append(token)
            new_line = ''.join(new_tokens)
            new_lines.append(new_line)
            self.progress_bar.setValue(i + 1)
            QApplication.processEvents()
        final_text = "".join(new_lines)
        self._apply_text_change_and_push_command(final_text) # Komutu yığına ekle
        self.progress_bar.setValue(self.progress_bar.maximum())
        QTimer.singleShot(500, self.progress_bar.hide)
        self.clearHighlights() # İşlem sonunda vurguları temizle

    def deleteLatine(self):
        old_text = self.text_edit.toPlainText()
        new_text = re.sub(r'[a-zA-ZçÇğĞıİöÖşŞüÜəƏ]', '', old_text)
        self._apply_text_change_and_push_command(new_text)

    def deleteRussian(self):
        old_text = self.text_edit.toPlainText()
        new_text = re.sub(r'[\u0400-\u04FF]', '', old_text)
        self._apply_text_change_and_push_command(new_text)

    def deleteDigits(self):
        old_text = self.text_edit.toPlainText()
        new_text = re.sub(r'\d+', '', old_text)
        self._apply_text_change_and_push_command(new_text)

    def deleteUppercase(self):
        old_text = self.text_edit.toPlainText()
        new_text = ''.join(c if not ('A' <= c <= 'Z') else '' for c in old_text)
        self._apply_text_change_and_push_command(new_text)

    def deleteLowercase(self):
        old_text = self.text_edit.toPlainText()
        new_text = ''.join(c if not ('a' <= c <= 'z') else '' for c in old_text)
        self._apply_text_change_and_push_command(new_text)

    def deleteCurlyBraces(self):
        old_text = self.text_edit.toPlainText()
        new_text = re.sub(r'[\{\}]', '', old_text)
        self._apply_text_change_and_push_command(new_text)

    def deleteAngleBrackets(self):
        old_text = self.text_edit.toPlainText()
        new_text = re.sub(r'[<>]', '', old_text)
        self._apply_text_change_and_push_command(new_text)

    def deleteParentheses(self):
        old_text = self.text_edit.toPlainText()
        new_text = re.sub(r'[\(\)]', '', old_text)
        self._apply_text_change_and_push_command(new_text)

    def deleteHyphen(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('-', '')
        self._apply_text_change_and_push_command(new_text)

    def deleteUnderscore(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('_', '')
        self._apply_text_change_and_push_command(new_text)

    def deleteQuestionMark(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('?', '')
        self._apply_text_change_and_push_command(new_text)

    def deleteExclamationMark(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('!', '')
        self._apply_text_change_and_push_command(new_text)

    def deleteSingleQuote(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace("'", '')
        self._apply_text_change_and_push_command(new_text)

    def deleteCaret(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('^', '')
        self._apply_text_change_and_push_command(new_text)

    def deletePlus(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('+', '')
        self._apply_text_change_and_push_command(new_text)

    def deletePercent(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('%', '')
        self._apply_text_change_and_push_command(new_text)

    def deleteAmpersand(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('&', '')
        self._apply_text_change_and_push_command(new_text)

    def deleteSlash(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('/', '')
        self._apply_text_change_and_push_command(new_text)

    def deleteEquals(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('=', '')
        self._apply_text_change_and_push_command(new_text)

    def deleteDot(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('.', '')
        self._apply_text_change_and_push_command(new_text)

    def deleteColon(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace(':', '')
        self._apply_text_change_and_push_command(new_text)

    def deleteDoubleQuote(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('"', '')
        self._apply_text_change_and_push_command(new_text)

    def deleteEAcute(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('é', '')
        self._apply_text_change_and_push_command(new_text)

    def deletePipe(self):
        old_text = self.text_edit.toPlainText()
        new_text = old_text.replace('|', '')
        self._apply_text_change_and_push_command(new_text)

    def deleteCharacters(self, chars_to_delete):
        old_text = self.text_edit.toPlainText()
        text = old_text
        for char in chars_to_delete:
            if char in ".*+?|{}()[]\\^$":
                text = re.sub(re.escape(char), '', text)
            else:
                text = text.replace(char, '')
        self._apply_text_change_and_push_command(text)

    def startSearch(self):
        search_text = self.search_input.text()
        if not search_text:
            self.clearHighlights()
            self.current_search_matches = []
            self.current_match_index = -1
            QMessageBox.information(self, "Arama", "Lütfen aranacak metni girin.")
            return

        self.clearHighlights()
        self.current_search_matches = []

        document = self.text_edit.document()
        cursor = QTextCursor(document)

        # Arama bayraklarını ayarla (büyük/küçük harf duyarsız olabilir)
        find_flags = QTextDocument.FindFlags()

        while True:
            # Mevcut imleç konumundan itibaren ara
            cursor = document.find(search_text, cursor, find_flags)
            if cursor.isNull():
                break

            # Eşleşmenin başlangıç ve bitiş pozisyonlarını saklıyoruz
            self.current_search_matches.append((cursor.selectionStart(), cursor.selectionEnd()))

            # Bir sonraki aramayı mevcut eşleşmenin bitiminden başlatmak için imleci ayarla
            cursor.setPosition(cursor.selectionEnd())

        if not self.current_search_matches:
            QMessageBox.information(self, "Arama", f"'{search_text}' metni bulunamadı.")
            self.current_match_index = -1
        else:
            self.current_match_index = 0
            self.highlightMatch(self.current_search_matches[self.current_match_index])
            self.scrollToMatch(self.current_search_matches[self.current_match_index])


    def findNext(self):
        if not self.current_search_matches:
            QMessageBox.information(self, "Arama", "Önce bir arama yapın.")
            return

        self.clearHighlights()
        self.current_match_index = (self.current_match_index + 1) % len(self.current_search_matches)
        self.highlightMatch(self.current_search_matches[self.current_match_index])
        self.scrollToMatch(self.current_search_matches[self.current_match_index])

    def findPrevious(self):
        if not self.current_search_matches:
            QMessageBox.information(self, "Arama", "Önce bir arama yapın.")
            return

        self.clearHighlights()
        self.current_match_index = (self.current_match_index - 1 + len(self.current_search_matches)) % len(self.current_search_matches)
        self.highlightMatch(self.current_search_matches[self.current_match_index])
        self.scrollToMatch(self.current_search_matches[self.current_match_index])

    def highlightMatch(self, match_positions):
        """Belirtilen pozisyonlardaki metni vurgular."""
        start, end = match_positions

        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("yellow"))
        highlight_format.setForeground(QColor("black"))

        # Vurguyu uygulamak için yeni bir QTextCursor oluştur ve formatı uygula
        cursor = self.text_edit.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        cursor.mergeCharFormat(highlight_format)
        self.text_edit.setTextCursor(cursor) # Vurguyu göster

    def clearHighlights(self):
        """Tüm vurguları temizler."""
        cursor = self.text_edit.textCursor()
        cursor.select(QTextCursor.Document) # Tüm belgeyi seç

        # QTextEdit'in varsayılan arka plan ve metin renklerini kullan
        default_format = QTextCharFormat()
        default_format.setBackground(QColor("#333")) # QTextEdit'in varsayılan arka plan rengi
        default_format.setForeground(QColor("white")) # QTextEdit'in varsayılan metin rengi

        cursor.setCharFormat(default_format) # Seçili alana varsayılan formatı uygula

        # İmleci başlangıca geri taşı
        cursor.movePosition(QTextCursor.Start)
        self.text_edit.setTextCursor(cursor)

    def scrollToMatch(self, match_positions):
        """Eşleşmeye kaydırır ve imleci o konuma getirir."""
        start, end = match_positions
        cursor = self.text_edit.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor) # Metni seçili hale getir
        self.text_edit.setTextCursor(cursor)
        self.text_edit.ensureCursorVisible() # İmlecin görünür olmasını sağla


    def openFiles(self):
        options = QFileDialog.Options()
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Files", TextEditorWindow.DEFAULT_BASE_DIR,
            "All Files (*);;PDF Files (*.pdf);;Text Files (*.txt);;Python Files (*.py)",
            options=options
        )
        if not file_paths:
            return

        self.load_multiple_files_content(file_paths) # Yeni yardımcı metodu çağır

    def load_file_content(self, file_path):
        """Tek bir dosyanın içeriğini yükler ve TextEditor'a yerleştirir."""
        file_content = ""
        file_name = os.path.basename(file_path)
        try:
            if file_path.lower().endswith(".pdf"):
                with open(file_path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page_index in range(len(reader.pages)):
                        page = reader.pages[page_index]
                        extracted_text = page.extract_text()
                        if extracted_text:
                            file_content += extracted_text
            else:
                with open(file_path, "r", encoding="utf-8", errors='replace') as file:
                    file_content = file.read()

            # Mevcut içeriği temizle ve yeni içeriği yükle
            self._apply_text_change_and_push_command(f"{file_name}\n\n{file_content}")
            # QMessageBox.information(self, "Dosya Yüklendi", f"Dosya başarıyla yüklendi:\n{file_path}") # Bu satır kaldırıldı

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya okunurken hata oluştu:\n{file_path}\nHata: {e}")

    def load_multiple_files_content(self, file_paths):
        """Birden fazla dosyanın içeriğini yükler ve mevcut metne ekler."""
        existing_text = self.text_edit.toPlainText().rstrip()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(file_paths))
        self.progress_bar.show()

        combined_content = existing_text
        if combined_content.strip():
            combined_content += "\n\n" # Eğer mevcut metin varsa boşluk ekle

        for i, path in enumerate(file_paths):
            file_name = os.path.basename(path)
            file_content = ""
            try:
                if path.lower().endswith(".pdf"):
                    with open(path, "rb") as f:
                        reader = PyPDF2.PdfReader(f)
                        for page_index in range(len(reader.pages)):
                            page = reader.pages[page_index]
                            extracted_text = page.extract_text()
                            if extracted_text:
                                file_content += extracted_text
                else:
                    with open(path, "r", encoding="utf-8", errors='replace') as file:
                        file_content = file.read()
            except Exception as e:
                print(f"Dosya okunurken hata oluştu: {path}\nHata: {e}")
            finally:
                if combined_content.strip() and i > 0: # İlk dosya değilse boşluk ekle
                    combined_content += "\n\n"
                combined_content += f"{file_name}\n\n{file_content}"
                self.progress_bar.setValue(i + 1)
                QApplication.processEvents()

        self._apply_text_change_and_push_command(combined_content)
        self.progress_bar.setValue(self.progress_bar.maximum())
        QTimer.singleShot(1000, self.progress_bar.hide)


    def triggerCoreSwitcher(self):
        main_window = self.window()
        if hasattr(main_window, 'showSwitcher'):
            main_window.showSwitcher()

    def exportContent(self):
        text_to_export = self.text_edit.toPlainText()
        suspicious_lines = self.checkForVirus(text_to_export)
        if suspicious_lines:
            msg = "Aşağıdaki satırlarda şüpheli ifade tespit edildi:\n\n"
            for line_num, content in suspicious_lines:
                msg += f"Line {line_num + 1}: {content}\n"
            QMessageBox.warning(self, "Virüs Uyarısı", msg)
            return

        QDir().mkpath(TextEditorWindow.DEFAULT_BASE_DIR)

        options = QFileDialog.Options()
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Dosyayı Kaydet", TextEditorWindow.DEFAULT_BASE_DIR,
            "Text Files (*.txt);;All Files (*)",
            options=options
        )
        if not save_path:
            return
        if not save_path.lower().endswith(".txt"):
            save_path += ".txt"
        try:
            with open(save_path, "w", encoding="utf-8") as file:
                file.write(text_to_export)
            QMessageBox.information(self, "Export", f"Dosya başarıyla kaydedildi:\n{save_path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya kaydedilirken hata oluştu:\n{str(e)}")

    def checkForVirus(self, text_content):
        suspicious_patterns = ["exec(", "eval("]
        lines = text_content.splitlines()
        found = []
        for i, line in enumerate(lines):
            for pattern in suspicious_patterns:
                if pattern in line:
                    found.append((i, line.strip()))
                    break
        return found

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = TextEditorWindow()
    editor.show()
    sys.exit(app.exec_())
