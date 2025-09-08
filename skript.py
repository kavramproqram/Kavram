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
    QFileDialog, QLabel, QApplication, QMessageBox, QProgressBar,
    QLineEdit, QAction, QMenu
)
from PyQt5.QtGui import (
    QColor, QIcon, QPixmap, QPainter, QTextCharFormat, QTextCursor, QTextDocument
)
from PyQt5.QtCore import Qt, QTimer, QDir, QByteArray
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

    def _apply_text_change_and_push_command(self, new_text):
        old_text = self.text_edit.toPlainText()
        command = TextChangeCommand(self, old_text, new_text)
        self.undo_stack.push(command)
        self.clearHighlights() # Metin değiştiğinde vurguları temizle

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
            "All Files (*);;PDF Files (*.pdf);;Text Files (*.txt);;Python Files (*.py);;C++ Files (*.cpp);;Lua Files (*.lua)",
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
        # Dosya adı olarak "Skript" öner ve sadece .py uzantısını filtrele
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Dosyayı Kaydet", os.path.join(TextEditorWindow.DEFAULT_BASE_DIR, f"Skript.py"),
            "Python Files (*.py);;All Files (*)",
            options=options
        )
        if not save_path:
            return

        # Seçilen uzantı ile kaydedildiğinden emin ol
        if not save_path.lower().endswith(".py"):
            save_path += ".py"

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

