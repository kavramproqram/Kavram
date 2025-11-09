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
import os
import re
import json
import unicodedata
from PyQt5.QtWidgets import (
    QWidget, QFrame, QPushButton, QVBoxLayout, QHBoxLayout,
    QTextEdit, QFileDialog, QProgressBar, QApplication,
    QLineEdit, QLabel, QMessageBox, QStackedWidget
)
from PyQt5.QtCore import Qt, QTimer, QDir # QDir modülünü ekledik

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
    print("PyPDF2 kütüphanesi yüklü değil. PDF okunamıyor.")


def normalize_text(s: str) -> str:
    """
    Diyakritikleri (â, î, é vb.) kaldırarak ASCII'ye indirger, küçük harfe çevirir.
    Örnek: "ferâset" -> "feraset"
    """
    s = unicodedata.normalize('NFD', s)
    s = s.encode('ascii', 'ignore').decode('utf-8')
    return s.lower()


class AiEditorWindow(QWidget):
    """
    Ana Pencere (Editor + Chat):
    - "File" butonu ile birden fazla PDF/txt dosyası yüklenebilir.
    - "Lean" butonu, metni otomatik kaydırarak 'okuma' efekti verir.
    - "Chat" butonu, editör yerine chat panelini gösterir.
    - "Export" butonu, word_dict verisini .ai (JSON) formatında dışa aktarır.
    - "Ai" butonu, (varsa) showSwitcher() gibi başka modüllere geçiş için kullanılır.
    - Dosya(lar)dan gelen içerik, bir sözlükte saklanır ve Chat'te soru sorulunca
      bu sözlükten anlam/karşılık araması yapılır.
    """
    # Satır 40: Varsayılan dışa aktarma/içe aktarma dizini dinamik olarak oluşturuldu
    # (Default export/import directory created dynamically)
    DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')

    def __init__(self, core_window_ref=None): # core_window_ref eklendi
        super().__init__()
        self.core_window_ref = core_window_ref # core_window_ref'i sakla
        self.scanning_timer = QTimer(self)
        self.scan_progress = 0

        # PDF veya metin dosyalarından gelen kelimeleri saklayacağımız sözlük:
        # { normalize(kelime) : (orijinal_satir, normalize(orijinal_satir)) }
        self.word_dict = {}

        self.initUI()

    def initUI(self):
        self.setWindowTitle("AI Editor")
        self.setStyleSheet("background-color: #333; border: none;")

        # Üst bar (toolbar)
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("""
            QFrame {
                background-color: #222;
                border-bottom: 2px solid #555;
            }
        """)
        toolbar_frame.setFixedHeight(40)

        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)

        # 1) File butonu
        self.file_button = QPushButton("File")
        self.file_button.setStyleSheet(self.buttonStyle())
        self.file_button.setFixedSize(90, 30)
        self.file_button.clicked.connect(self.openFiles)

        # 2) Lean butonu
        self.lean_button = QPushButton("Lean")
        self.lean_button.setStyleSheet(self.buttonStyle())
        self.lean_button.setFixedSize(90, 30)
        self.lean_button.clicked.connect(self.startScanning)

        # 3) Chat butonu
        self.chat_button = QPushButton("Chat")
        self.chat_button.setStyleSheet(self.buttonStyle())
        self.chat_button.setFixedSize(90, 30)
        self.chat_button.clicked.connect(self.showChatPanel)

        # Solda: File, Lean, Chat
        toolbar_layout.addWidget(self.file_button, alignment=Qt.AlignLeft)
        toolbar_layout.addWidget(self.lean_button, alignment=Qt.AlignLeft)
        toolbar_layout.addWidget(self.chat_button, alignment=Qt.AlignLeft)

        # Ortada boşluk
        toolbar_layout.addStretch()

        # --- Sağda: Export ve Ai butonları ---
        self.export_button = QPushButton("Export")
        self.export_button.setStyleSheet(self.buttonStyle())
        self.export_button.setFixedSize(90, 30)
        self.export_button.clicked.connect(self.exportAIFile)
        toolbar_layout.addWidget(self.export_button, alignment=Qt.AlignRight)

        self.ai_button = QPushButton("Ai")
        self.ai_button.setStyleSheet(self.buttonStyle())
        self.ai_button.setFixedSize(90, 30)
        # "Ai" butonuna tıklandığında triggerCoreSwitcher fonksiyonunu çağırır.
        # Bu fonksiyon, ana pencereye (CoreWindow) geçiş yapmanızı veya editör değiştirme diyalogunu açmanızı sağlar.
        self.ai_button.clicked.connect(self.triggerCoreSwitcher)
        toolbar_layout.addWidget(self.ai_button, alignment=Qt.AlignRight)
        # -------------------------------------

        # Stacked widget: editör sayfası ve chat sayfası arasında geçiş
        self.stack = QStackedWidget()

        # Editör sayfası
        self.editor_page = QWidget()
        editor_layout = QVBoxLayout(self.editor_page)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        self.editor = QTextEdit()
        self.editor.setStyleSheet("background-color: #333; color: white;")
        self.editor.setPlaceholderText("Dosya içeriği burada görünecek...")
        editor_layout.addWidget(self.editor)

        # PDF/metin okuma ilerleme çubuğu
        self.progressBar = QProgressBar()
        self.progressBar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 8px;
                text-align: center;
                color: white;
                background-color: #222;
            }
            QProgressBar::chunk {
                background-color: #666;
            }
        """)
        self.progressBar.setFixedHeight(20)
        self.progressBar.hide()
        editor_layout.addWidget(self.progressBar)

        # Chat sayfası
        self.chat_page = ChatPanel(word_dict=self.word_dict)

        # Stacked widget'e iki sayfayı ekle (editör ve chat)
        self.stack.addWidget(self.editor_page)
        self.stack.addWidget(self.chat_page)

        # Ana layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(toolbar_frame)
        main_layout.addWidget(self.stack)
        self.setLayout(main_layout)

    def buttonStyle(self):
        """
        Buton stil ayarları.
        Siyah arka plan, beyaz yazı, kenarlık vb.
        """
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
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

    def openFiles(self):
        """
        Birden fazla dosya seçilebilen iletişim kutusu açar,
        seçilen dosyaları okur ve editöre ekler.
        Dosya okurken ilerleme çubuğunu gösterir ve Chat'te isek Editör'e geçer.
        Ayrıca .ai (JSON) dosyası seçilirse, word_dict yüklenir ve otomatik Chat'e geçilir.
        """
        # Eğer Chat panelindeysek, Editör paneline dön
        self.stack.setCurrentWidget(self.editor_page)

        options = QFileDialog.Options()
        # Satır 171: Varsayılan dizin DEFAULT_BASE_DIR olarak ayarlandı
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Open Files",
            AiEditorWindow.DEFAULT_BASE_DIR, # Burada varsayılan klasör ayarlandı
            "All Files (*);;Text Files (*.txt);;PDF Files (*.pdf);;AI Files (*.ai)",
            options=options
        )
        if file_paths:
            self._process_files(file_paths)

    def openFiles_from_path(self, file_paths):
        """
        Dışarıdan (örn: kare.py'den) dosya yolu listesi alarak dosyaları işler.
        """
        print(f"DEBUG: AiEditorWindow.openFiles_from_path called with: {file_paths}")
        self.stack.setCurrentWidget(self.editor_page) # Editör paneline geç
        self._process_files(file_paths)

    def _process_files(self, file_paths):
        """
        Verilen dosya yollarını işler, içeriği okur ve sözlüğü günceller.
        """
        if not file_paths:
            return

        total_files = len(file_paths)
        self.progressBar.setValue(0)
        self.progressBar.show()

        # Mevcut metne ek olarak yeni metinler eklensin
        combined_text = self.editor.toPlainText().strip()
        if combined_text:
            combined_text += "\n"

        for i, file_path in enumerate(file_paths):
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            try:
                if ext == ".pdf":
                    if PyPDF2 is None:
                        QMessageBox.warning(self, "Hata", "PyPDF2 yüklü değil. PDF okunamıyor.")
                        continue
                    text = self.extractTextFromPDF(file_path)
                    combined_text += text + "\n"

                elif ext == ".ai":
                    # .ai dosyası -> JSON formatında word_dict'i yükle
                    with open(file_path, "r", encoding="utf-8") as f:
                        loaded_dict = json.load(f)
                        # Mevcut sözlüğü tamamen yeni yüklenenle değiştir
                        self.word_dict = loaded_dict
                    # .ai yüklendikten sonra direkt Chat ekranına geç
                    self.showChatPanel()
                    # Ai dosyası yüklendiğinde editör alanını temizle
                    self.editor.setPlainText("") 
                    # Diğer dosyaları işlemeyi durdur (varsa)
                    self.progressBar.hide()
                    return # Ai dosyası yüklendiğinde diğer dosyaları işleme

                else:  # .txt veya diğer dosyalar
                    with open(file_path, "r", encoding="utf-8") as file:
                        text = file.read()
                    combined_text += text + "\n"

            except Exception as e:
                QMessageBox.critical(self, "Hata", f"{file_path} okunurken hata oluştu:\n{str(e)}")

            # İlerleme çubuğunu güncelle
            progress_percent = int(((i + 1) / total_files) * 100)
            self.progressBar.setValue(progress_percent)
            QApplication.processEvents()

        # Editöre yeni metni yükle (sadece .ai dosyası yüklenmediyse)
        if combined_text.strip():
            self.editor.setPlainText(combined_text)
            # PDF/txt dosyası geldiyse sözlüğe ekle
            self.buildDictionaryFromText(combined_text)

        self.progressBar.hide()

    def extractTextFromPDF(self, file_path):
        """
        PDF dosyasından metin çıkarma.
        PyPDF2 kütüphanesiyle sayfa sayfa gezerek text biriktirir.
        """
        text = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def buildDictionaryFromText(self, text):
        """
        Metin içeriğindeki satırları tarar, çeşitli kalıplara göre
        kelime-anlam ayırır. Her kelimenin normalize hali -> orijinal satır
        şeklinde sözlükte saklanır.
        """
        lines = text.splitlines()
        for line in lines:
            original_line = line.strip()
            if not original_line:
                continue

            # Bazı tipik sözlük formatları:
            pattern1 = re.compile(r"^([^,]+), \[.*?\]\s*sf\.\s*(.*)$")
            pattern2 = re.compile(r"^([^:]+):\s*(.*)$")
            pattern3 = re.compile(r"^([^=]+)=\s*(.*)$")
            pattern4 = re.compile(r"^([^–\-]+)[–\-]\s*(.*)$")

            match1 = pattern1.match(original_line)
            match2 = pattern2.match(original_line)
            match3 = pattern3.match(original_line)
            match4 = pattern4.match(original_line)

            if match1:
                word = match1.group(1).strip()
            elif match2:
                word = match2.group(1).strip()
            elif match3:
                word = match3.group(1).strip()
            elif match4:
                word = match4.group(1).strip()
            else:
                parts = original_line.split(None, 1)
                word = parts[0] if parts else original_line

            norm_word = normalize_text(word)
            norm_line = normalize_text(original_line)
            self.word_dict[norm_word] = (original_line, norm_line)

    def startScanning(self):
        """
        Lean butonuna tıklanınca editördeki metni otomatik kaydırarak
        bir 'okuma' animasyonu yapar. 100 adımda scroll sonuna kadar gider.
        """
        content = self.editor.toPlainText()
        if not content.strip():
            QMessageBox.information(self, "Bilgi", "Önce bir dosya açın.")
            return

        self.progressBar.setValue(0)
        self.progressBar.show()
        self.scan_progress = 0

        self.scrollbar = self.editor.verticalScrollBar()
        self.start_value = self.scrollbar.value()
        self.end_value = self.scrollbar.maximum()

        self.scan_steps = 100
        self.timer_interval = 100

        self.scanning_timer = QTimer(self)
        self.scanning_timer.timeout.connect(self.updateScanning)
        self.scanning_timer.start(self.timer_interval)

    def updateScanning(self):
        """
        Lean (okuma) animasyonunda her adımda scrollbar'ı biraz aşağı kaydırır
        ve progressBar'ı günceller.
        """
        self.scan_progress += 1
        progress_percent = int((self.scan_progress / self.scan_steps) * 100)
        self.progressBar.setValue(progress_percent)

        new_value = self.start_value + int(
            (self.end_value - self.start_value) * (self.scan_progress / self.scan_steps)
        )
        self.scrollbar.setValue(new_value)

        if self.scan_progress >= self.scan_steps:
            self.scanning_timer.stop()
            self.progressBar.hide()

    def showChatPanel(self):
        """
        Chat butonuna tıklandığında editör yerine chat paneli gösterilir.
        Sözlüğü chat paneline aktarıp odaklanma ayarı yapılır.
        """
        self.chat_page.word_dict = self.word_dict
        self.stack.setCurrentWidget(self.chat_page)
        self.chat_page.input_line.setFocus()

    def triggerCoreSwitcher(self):
        """
        Ai butonuna tıklandığında, ana pencerede 'showSwitcher()' varsa onu çağırarak
        farklı editörlere (Ai, Sound, Drawing vb.) geçiş yapılabilir.
        """
        # self.window() metodu, mevcut widget'ın üst penceresini (CoreWindow) bulur.
        main_window = self.window() 
        # Eğer ana pencere referansı mevcutsa ve showSwitcher metodu varsa çağır.
        if self.core_window_ref and hasattr(self.core_window_ref, 'showSwitcher'):
            self.core_window_ref.showSwitcher()
        # Aksi takdirde, kullanıcıya bilgi mesajı göster.
        else:
            QMessageBox.information(self, "Bilgi", "Ana pencere referansı bulunamadı veya showSwitcher() metodu mevcut değil.")


    def exportAIFile(self):
        """
        Export butonuna tıklanınca .ai uzantılı dosyaya word_dict'i JSON formatında yazar.
        Kayıt yeri olarak varsayılan '/Kavram/Export/' klasörünü açar.
        """
        # Satır 319: Klasörün mevcut olduğundan emin olun, yoksa oluşturun.
        # (Ensure the directory exists, create it if it doesn't.)
        QDir().mkpath(AiEditorWindow.DEFAULT_BASE_DIR)

        # Satır 322: Varsayılan export klasörü dinamik olarak belirlendi
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export AI File",
            AiEditorWindow.DEFAULT_BASE_DIR,  # Burada varsayılan klasör ayarlandı
            "AI Files (*.ai);;All Files (*)"
        )
        if save_path:
            # Uzantı kontrolü (kullanıcı .ai yazmadıysa ekleyelim)
            if not save_path.lower().endswith(".ai"):
                save_path += ".ai"

            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(self.word_dict, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "Başarılı", f"AI dosyası kaydedildi:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"AI dosyası kaydedilemedi:\n{str(e)}")


class ChatPanel(QWidget):
    """
    Chat arayüzü:
    - Kullanıcı (You) mesajları solda,
    - Bot (Chat) mesajları sağda.
    - Basit "WhatsApp benzeri" baloncuk stili.
    """
    def __init__(self, word_dict=None):
        super().__init__()
        self.word_dict = word_dict if word_dict else {}
        self.initUI()

    def initUI(self):
        # QSS / CSS benzeri stil ayarları
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: white;
                font-family: Arial;
                font-size: 18px;
            }
            QLineEdit {
                background-color: #222;
                color: white;
                padding: 8px;
                border: 1px solid #555;
                border-radius: 4px;
                font-size: 18px;
            }
            QTextEdit {
                background-color: #2b2b2b;
                color: white;
                border: 1px solid #555;
                border-radius: 6px;
                font-size: 18px;
            }
            QPushButton {
                background-color: #444;
                color: white;
                font-size: 18px;
                font-weight: bold;
                border: 1px solid #666;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #555; }
            QPushButton:pressed { background-color: #666; }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Chat metin alanı
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        main_layout.addWidget(self.chat_area)

        # Alt kısım: Giriş ve Gönder butonu
        input_layout = QHBoxLayout()

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("You:")
        self.input_line.returnPressed.connect(self.sendMessage)

        send_button = QPushButton("↑")
        send_button.clicked.connect(self.sendMessage)
        send_button.setFixedWidth(60)

        input_layout.addWidget(self.input_line)
        input_layout.addWidget(send_button)
        main_layout.addLayout(input_layout)

        self.setLayout(main_layout)

    def sendMessage(self):
        message = self.input_line.text().strip()
        if not message:
            return

        # Kullanıcı mesajı (solda)
        user_html = f"""
        <div style="
            display: inline-block;
            float: left;
            clear: both;
            margin: 5px 10px;
            padding: 10px;
            border-radius: 10px;
            background-color: #2b2b2b;
            color: white;
            max-width: 60%;
        ">
            <b>You:</b> {message}
        </div>
        """
        self.chat_area.append(user_html)
        self.input_line.clear()

        # Bot mesajı (sağda)
        response = self.getDefinition(message)
        bot_html = f"""
        <div style="
            display: inline-block;
            float: right;
            clear: both;
            margin: 5px 10px;
            padding: 10px;
            border-radius: 10px;
            background-color: #2b2b2b;
            color: white;
            max-width: 60%;
        ">
            <b>Chat:</b> {response}
        </div>
        """
        self.chat_area.append(bot_html)

        # Otomatik kaydırma
        self.chat_area.verticalScrollBar().setValue(
            self.chat_area.verticalScrollBar().maximum()
        )

    def getDefinition(self, word):
        """
        1) Diyakritiksiz tam eşleşme: self.word_dict[norm_word] varsa orijinal satırı döndürür.
        2) Bulunamazsa kısmi arama (norm_input in norm_line).
        3) Yoksa "Sözlükte bulunamadı." döndürür.
        """
        norm_input = normalize_text(word)

        # Tam eşleşme
        if norm_input in self.word_dict:
            orig_line, _ = self.word_dict[norm_input]
            return orig_line

        # Kısmi arama
        for k, (orig_line, norm_line) in self.word_dict.items():
            if norm_input in k or norm_input in norm_line:
                return orig_line

        # Yoksa
        return "Sözlükte bulunamadı."


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AiEditorWindow()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec_())

