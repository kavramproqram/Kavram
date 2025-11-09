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
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFileDialog, QToolButton, QScrollArea, QSizePolicy,
    QLineEdit, QTextEdit, QGraphicsDropShadowEffect, QMessageBox, QFrame, QDialog, QListWidget, QListWidgetItem
)
from PyQt5.QtGui import QFont, QColor, QIcon, QPixmap, QPainter
from PyQt5.QtCore import Qt, QDir, QSize, QByteArray
from PyQt5.QtSvg import QSvgRenderer
import os

# Core.py'dan EditorSwitcherDialog ve CoreWindow'u içe aktarıyoruz
# Bu, Core.py'nin aynı dizinde veya Python yolunda olmasını gerektirir.
try:
    from Core import EditorSwitcherDialog, CoreWindow
except ImportError:
    # Eğer Core.py bulunamazsa veya EditorSwitcherDialog eksikse dummy bir sınıf oluştur
    class EditorSwitcherDialog(QDialog):
        def __init__(self, editor_names, parent=None):
            super().__init__(parent)
            self.editor_names = editor_names
            self.selected_name = None
            self.initUI()

        def initUI(self):
            layout = QVBoxLayout()
            self.list_widget = QListWidget()
            for name in self.editor_names:
                self.list_widget.addItem(name)
            layout.addWidget(self.list_widget)
            self.setLayout(layout)
            self.list_widget.itemClicked.connect(self.acceptSelection)

        def acceptSelection(self):
            items = self.list_widget.selectedItems()
            if items:
                self.selected_name = items[0].text()
            self.accept()

    class CoreWindow(QWidget): # Dummy CoreWindow
        def __init__(self):
            super().__init__()
            self.editor_map = {
                "Sphere": QWidget,
                "Text": QWidget, # Placeholder
                "Drawing": QWidget, # Placeholder
                "Sound": QWidget, # Placeholder
                "Ai": QWidget, # Placeholder
                "Media": QWidget, # Placeholder
                "Rec": QWidget, # Placeholder
                "Copy": QWidget, # Placeholder
                "Anime": QWidget, # Placeholder
                "Settings": QWidget # Placeholder
            }
            self.editors_order = list(self.editor_map.keys())
            print("Uyarı: Core.py veya EditorSwitcherDialog bulunamadı. Bazı işlevler sınırlı olabilir.")
            self.stack = QVBoxLayout(self) # Dummy stack
            self.dummy_widget = QWidget()
            self.stack.addWidget(self.dummy_widget) # En az bir widget ekleyin

        def switchToEditor(self, editor_name):
            # Dummy switchToEditor metodu
            print(f"Dummy CoreWindow: '{editor_name}' editörüne geçiş istendi.")

        def showSwitcher(self):
            # Dummy showSwitcher metodu
            print("Dummy CoreWindow: Switcher gösteriliyor.")

        def loadEditorFile(self, editor_name, file_path):
            # Dummy loadEditorFile metodu
            print(f"Dummy CoreWindow: '{file_path}' dosyasını '{editor_name}' editörüne yüklüyor.")


# SVG ikonlarını oluşturmak için yardımcı fonksiyon
def create_svg_icon(svg_content, size=24, color="#eee"):
    """
    Verilen SVG içeriğinden bir QIcon oluşturur.
    :param svg_content: SVG XML stringi.
    :param size: İkonun genişlik ve yüksekliği (piksel).
    :param color: SVG içindeki stroke rengi için varsayılan renk.
    :return: QIcon nesnesi.
    """
    # SVG içeriğindeki rengi dinamik olarak değiştir
    # Basit bir replace ile stroke ve fill renklerini güncelleyebiliriz
    # Daha karmaşık SVG'ler için daha gelişmiş bir parser gerekebilir.
    modified_svg_content = svg_content.replace('stroke="#eee"', f'stroke="{color}"')
    modified_svg_content = modified_svg_content.replace('fill="#eee"', f'fill="{color}"')

    renderer = QSvgRenderer(QByteArray(modified_svg_content.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent) # Arka planı şeffaf yap
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

# "+" ikonu için SVG içeriği (Drawing_editor.py'den alındı)
SVG_ADD_ICON = """
<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M12 5V19M5 12H19" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

class FullScreenNoteDialog(QDialog):
    def __init__(self, note_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Not Detayı")
        self.setModal(True)
        self.setWindowFlags(Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.init_ui(note_text)

    def init_ui(self, note_text):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Top bar for close button
        top_bar_layout = QHBoxLayout()
        top_bar_layout.addStretch() # Push button to the right

        self.close_btn = QToolButton()
        self.close_btn.setText("X")
        self.close_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.close_btn.setFixedSize(30, 30)
        # "X" butonu için stil, silme butonu gibi ama farklı bir renk tonuyla
        self.close_btn.setStyleSheet(
            "QToolButton { background-color: #555; color: white; border: 2px solid #777; border-radius: 8px; padding: 4px 12px; }"
            "QToolButton:hover { background-color: #777; }"
        )
        self.close_btn.clicked.connect(self.accept) # Sadece dialogu kapatır
        top_bar_layout.addWidget(self.close_btn)
        main_layout.addLayout(top_bar_layout)

        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(note_text)
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont("Segoe UI", 12, QFont.Normal)) # Yazı kalınlığı artırıldı
        self.text_edit.setStyleSheet(
            "border: 1px solid #444; border-radius: 4px; background-color: #2a2a2a; color: #ffffff;"
        )
        main_layout.addWidget(self.text_edit)

class NoteWidget(QWidget):
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.expanded = False
        self.main_window = main_window # MainWindow referansını sakla
        self.init_ui()

    def init_ui(self):
        # Note heights
        self.base_note_height = 70
        # Genişletilmiş not yüksekliği, ana pencereye göre dinamik olarak ayarlanacak
        # Başlangıçta varsayılan bir değer verilebilir, toggle_single_note_view'da güncellenecek
        self.expanded_note_height_factor = 2.5

        self.setStyleSheet("background-color: #1f1f1f; border-radius: 8px;")
        self.setGraphicsEffect(self._make_shadow())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4) # Not alanı butonlara daha yakın olsun diye spacing azaltıldı

        hlayout = QHBoxLayout()

        # Package name input
        self.pkg_name = QLineEdit()
        self.pkg_name.setPlaceholderText("Package Name")
        # Kalınlık ayarı ve font kalınlığı
        self.pkg_name.setMinimumHeight(30) # Minimum yükseklik 30 piksel
        self.pkg_name.setFont(QFont("Segoe UI", 11, QFont.DemiBold)) # Yazı kalınlığı artırıldı
        self.pkg_name.setStyleSheet(
            "border: 1px solid #444; border-radius: 4px; background-color: #2a2a2a; color: #ffffff;"
        )

        # Copy button
        self.copy_btn = QToolButton()
        self.copy_btn.setText("Copy")
        self.copy_btn.setFont(QFont("Segoe UI", 10, QFont.DemiBold))
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.setFixedSize(60, 30) # Buton kalınlığı 30x
        self.copy_btn.setStyleSheet(
            "QToolButton { background-color: transparent; color: white; font-size: 14px; font-weight: bold; "
            "border: 2px solid #555; border-radius: 8px; padding: 5px 10px; }"
            "QToolButton:hover { background-color: #444; }"
        )

        # Expand/Single Note toggle button
        self.expand_btn = QToolButton()
        self.expand_btn.setText("/")
        self.expand_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.expand_btn.setCursor(Qt.PointingHandCursor)
        self.expand_btn.clicked.connect(self.toggle_single_note_view) # Yeni işlevsellik
        self.expand_btn.setFixedSize(40, 30) # Buton kalınlığı 30x
        self.expand_btn.setStyleSheet(
            "QToolButton { background-color: transparent; color: white; font-size: 16px; font-weight: bold; "
            "border: 2px solid #555; border-radius: 8px; padding: 4px 12px; }"
            "QToolButton:hover { background-color: #444; }"
            "QToolButton:checked { background-color: #555; }" # Aktif olduğunda gri renk
        )
        self.expand_btn.setCheckable(True) # Butonu checkable yap

        # Delete button (tasarımı '/' butonuna benzetildi, rengi korundu)
        self.delete_btn = QToolButton()
        self.delete_btn.setText("X")
        self.delete_btn.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.clicked.connect(self.delete_note)
        self.delete_btn.setFixedSize(40, 30) # Buton kalınlığı 30x
        self.delete_btn.setStyleSheet(
            "QToolButton { background-color: transparent; color: white; font-size: 16px; font-weight: bold; "
            "border: 2px solid #555; border-radius: 8px; padding: 4px 12px; }" # '/' butonu gibi tasarım
            "QToolButton:hover { background-color: #444; }"
        )

        hlayout.addWidget(self.pkg_name)
        hlayout.addWidget(self.copy_btn)
        hlayout.addWidget(self.expand_btn)
        hlayout.addWidget(self.delete_btn)
        hlayout.setStretch(0, 6) # pkg_name'in genişlemesine daha fazla izin ver (3.6 kat gibi)
        hlayout.setStretch(1, 0)
        hlayout.setStretch(2, 0)
        hlayout.setStretch(3, 0)

        # Note area
        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText("Enter your note...")
        self.note_edit.setFont(QFont("Segoe UI", 11, QFont.Normal)) # Yazı kalınlığı artırıldı
        self.note_edit.setStyleSheet(
            "border: 1px solid #444; border-radius: 4px; background-color: #2a2a2a; color: #ffffff;"
        )
        self.note_edit.setFixedHeight(self.base_note_height)

        layout.addLayout(hlayout)
        layout.addWidget(self.note_edit)

    def _make_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 200))
        return shadow

    def copy_to_clipboard(self):
        QApplication.clipboard().setText(self.note_edit.toPlainText())
        # QMessageBox.information(self, "Copya", "Not kopyalandı!") # İsteğe bağlı bilgilendirme

    def show_full_screen_note(self):
        # Bu fonksiyon artık kullanılmıyor, "View" butonu kaldırıldı.
        dialog = FullScreenNoteDialog(self.note_edit.toPlainText(), self)
        dialog.exec_()

    def delete_note(self):
        # Kullanıcıya silme onayı sorulmadan doğrudan silme işlemi
        # Eğer tek not görünümündeysek, silinen not mevcut tek not ise
        # ana pencereyi normal görünüme döndür.
        if self.main_window and self.main_window.single_note_mode and self.main_window.current_single_note_widget == self:
            self.main_window.exit_single_note_view() # Tek not görünümünden çık

        if self.parentWidget() and isinstance(self.parentWidget().layout(), QVBoxLayout):
            self.parentWidget().layout().removeWidget(self)
        self.deleteLater() # Widget'ı güvenli bir şekilde sil
        # Not: Bu işlem sadece seçili notu siler, diğer notları etkilemez.

    def toggle_single_note_view(self):
        if self.main_window:
            self.main_window.toggle_single_note_view(self)
            # expand_btn'nin check durumunu MainWindow'daki toggle_single_note_view yönetecek
            # self.expanded = not self.expanded # Bu satır artık burada gerekli değil
            # self.expand_btn.setChecked(self.expanded) # Bu satır artık burada gerekli değil

    def to_dict(self):
        return {'package': self.pkg_name.text(), 'note': self.note_edit.toPlainText()}

class MainWindow(QMainWindow):
    DEFAULT_BASE_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')

    def __init__(self, core_window_ref=None): # core_window_ref parametresi eklendi
        super().__init__()
        self.core_window_ref = core_window_ref # core_window_ref'i sakla
        self.setWindowTitle("Copya")
        self.resize(960, 700)
        self.single_note_mode = False # Tek not görünümü modunu takip et
        self.current_single_note_widget = None # Hangi notun tekli modda olduğunu takip et
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        central.setStyleSheet("background-color: #121212;")
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Drawing_editor.py'deki gibi toolbar_frame oluştur
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("background-color: #222; border-bottom: 2px solid #555;")
        toolbar_frame.setFixedHeight(40)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.setSpacing(10)

        # File button
        self.file_btn = QToolButton()
        self.file_btn.setText("File")
        self.file_btn.setCursor(Qt.PointingHandCursor)
        self.file_btn.clicked.connect(self.load_copya)
        self.file_btn.setFixedSize(90, 30) # Buton kalınlığı 30x
        self.file_btn.setStyleSheet(self.buttonStyle())
        toolbar_layout.addWidget(self.file_btn, alignment=Qt.AlignLeft)

        # Add note button
        self.add_btn = QToolButton()
        self.add_btn.setText("+") # Metin eklendi
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self.add_note)
        self.add_btn.setFixedSize(30, 30) # Buton kalınlığı 30x
        self.add_btn.setStyleSheet(self.buttonStyle())
        toolbar_layout.addWidget(self.add_btn, alignment=Qt.AlignLeft)

        # Spacer to push right-aligned buttons
        toolbar_layout.addStretch()

        # Export button
        self.export_btn = QToolButton()
        self.export_btn.setText("Export")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.clicked.connect(self.export_copya)
        self.export_btn.setFixedSize(90, 30) # Buton kalınlığı 30x
        self.export_btn.setStyleSheet(self.buttonStyle())
        toolbar_layout.addWidget(self.export_btn, alignment=Qt.AlignRight)

        # Drawing button (Sphere.py'deki gibi editör geçişi için)
        self.drawing_button = QToolButton()
        self.drawing_button.setText("Copy")
        self.drawing_button.setCursor(Qt.PointingHandCursor)
        self.drawing_button.clicked.connect(self.triggerCoreSwitcher) # Fonksiyonu bağla
        self.drawing_button.setFixedSize(90, 30) # Buton kalınlığı 30x
        self.drawing_button.setStyleSheet(self.buttonStyle())
        toolbar_layout.addWidget(self.drawing_button, alignment=Qt.AlignRight)

        # Toolbar'ı ana layout'a ekle
        main_layout.addWidget(toolbar_frame)

        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        container = QWidget()
        self.note_layout = QVBoxLayout(container)
        self.note_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(container)
        main_layout.addWidget(self.scroll)

        self.setCentralWidget(central)

    def buttonStyle(self):
        """
        Genel butonlar için DrawingEditorWindow'daki gibi stil.
        """
        return """
            QToolButton {
                background-color: transparent;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                padding: 5px 20px;
            }
            QToolButton:hover {
                background-color: #444;
            }
            QToolButton:pressed {
                background-color: #666;
            }
        """

    def add_note(self):
        # Yeni notu en üste ekle
        self.note_layout.insertWidget(0, NoteWidget(main_window=self))

    def load_copya(self, path=None): # path parametresi eklendi
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, "Open .copya file", MainWindow.DEFAULT_BASE_DIR, "Copya Files (*.copya)")
        if not path: return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Mevcut notları temizle
            for i in reversed(range(self.note_layout.count())):
                self.note_layout.itemAt(i).widget().setParent(None)
            # Yeni notları yükle
            for item in data.get('notes', []):
                note = NoteWidget(main_window=self) # MainWindow referansını geçir
                note.pkg_name.setText(item.get('package', ''))
                note.note_edit.setPlainText(item.get('note', ''))
                self.note_layout.addWidget(note)
            QMessageBox.information(self, "Load", f"Dosya başarıyla yüklendi:\n{path}") # Bilgilendirme eklendi
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya yüklenirken hata oluştu:\n{str(e)}")

    def export_copya(self):
        QDir().mkpath(MainWindow.DEFAULT_BASE_DIR)
        path, _ = QFileDialog.getSaveFileName(self, "Save .copya file", os.path.join(MainWindow.DEFAULT_BASE_DIR, "untitled.copya"), "Copya Files (*.copya)")
        if not path: return
        if not path.endswith('.copya'): path += '.copya'
        notes = [self.note_layout.itemAt(i).widget().to_dict() for i in range(self.note_layout.count())]
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({'notes': notes}, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Export", f"Dosya başarıyla kaydedildi:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya kaydedilirken hata oluştu:\n{str(e)}")

    def triggerCoreSwitcher(self):
        """
        Ana uygulama penceresindeki (CoreWindow) editör değiştirme işlevini tetikler.
        """
        # self.window() yerine core_window_ref kullanıyoruz
        if self.core_window_ref and hasattr(self.core_window_ref, 'showSwitcher'):
            self.core_window_ref.showSwitcher()
        else:
            QMessageBox.warning(self, "Uyarı", "Ana pencere 'showSwitcher' fonksiyonuna sahip değil veya referans geçersiz.")

    def toggle_single_note_view(self, clicked_note_widget):
        # Eğer zaten tek not modundaysak ve tıklanan widget mevcut tek not ise,
        # tek not modundan çıkıyoruz.
        if self.single_note_mode and self.current_single_note_widget == clicked_note_widget:
            self.exit_single_note_view()
        # Eğer tek not modunda değilsek veya farklı bir not tıklandıysa,
        # tıklanan widget için tek not moduna giriyoruz.
        else:
            self.enter_single_note_view(clicked_note_widget)

    def enter_single_note_view(self, target_note_widget):
        self.single_note_mode = True
        self.current_single_note_widget = target_note_widget

        available_height = self.scroll.height() - self.note_layout.contentsMargins().top() - self.note_layout.contentsMargins().bottom()

        for i in range(self.note_layout.count()):
            widget = self.note_layout.itemAt(i).widget()
            if widget:
                if widget == target_note_widget:
                    widget.show()
                    target_height = max(300, int(available_height * widget.expanded_note_height_factor))
                    widget.note_edit.setFixedHeight(target_height)
                    widget.expand_btn.setChecked(True) # Tıklanan butonu işaretli yap
                else:
                    widget.hide()
                    widget.expand_btn.setChecked(False) # Diğer butonların işaretini kaldır

    def exit_single_note_view(self):
        self.single_note_mode = False
        self.current_single_note_widget = None

        for i in range(self.note_layout.count()):
            widget = self.note_layout.itemAt(i).widget()
            if widget:
                widget.show()
                widget.note_edit.setFixedHeight(widget.base_note_height)
                widget.expand_btn.setChecked(False) # Tüm butonların işaretini kaldır


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec_())

