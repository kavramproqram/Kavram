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

# button_styles.py
# Bu dosya, uygulamanın farklı bölümlerinde kullanılan tüm ortak buton ve menü stillerini içerir.

from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QByteArray
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPixmap, QPainter, QIcon

# --- Yardımcı Fonksiyonlar ve Sabitler (İkonlar için) ---
# İkonlar doğrudan bu dosya içinde tanımlandı
def create_svg_icon(svg_content, size=24, color="#eee"):
    """Verilen SVG içeriğinden bir QIcon oluşturur."""
    # SVG içeriğindeki renkleri ve boyutları dinamik olarak değiştir
    modified_svg_content = svg_content.replace('stroke="#eee"', f'stroke="{color}"').replace('fill="#eee"', f'fill="{color}"')
    renderer = QSvgRenderer(QByteArray(modified_svg_content.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent) # Şeffaf arka plan
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

# Ortak SVG ikon tanımları
SVG_ADD_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5V19M5 12H19" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_UNDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19C15.866 19 19 15.866 19 12C19 8.13401 15.866 5 12 5C8.13401 5 5 8.13401 5 12C5 13.7909 5.70014 15.4293 6.84594 16.6386L5 18M5 18H9M5 18V14" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_REDO_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5C8.13401 5 5 8.13401 5 12C5 15.866 8.13401 19 12 19C15.866 19 19 15.866 19 12C19 10.2091 18.2999 8.57074 17.1541 7.3614L19 6M19 6H15M19 6V10" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_FILE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M13 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 21.7893 5.46957 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V9L13 2Z" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M13 2V9H20" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_EXPORT_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M21 15V19C21 19.5304 20.7893 20.0196 20.4142 20.3896C20.0391 20.7596 19.5304 21 19 21H5C4.46957 21 3.98043 20.7893 3.61043 20.4142C3.24043 20.0391 3 19.5304 3 19V15M17 9L12 4M12 4L7 9M12 4V16" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_IMPORT_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M21 15V19C21 19.5304 20.7893 20.0196 20.4142 20.3896C20.0391 20.7596 19.5304 21 19 21H5C4.46957 21 3.98043 20.7893 3.61043 20.4142C3.24043 20.0391 3 19.5304 3 19V15M7 8L12 3M12 3L17 8M12 3V15" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_CLOSE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18 6L6 18M6 6L18 18" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
# Tik işareti için güncellenmiş SVG (daha belirgin ve ortalanmış)
# stroke-width azaltıldı ve transform translate ayarlandı
SVG_TICK_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path transform="translate(0, 6)" d="M6 12L10 16L18 8" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
# Yeni SVG ikonları: Yukarı ok ve Aşağı ok (seçili klasöre gir)
SVG_UP_ARROW_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 5V19M12 5L18 11M12 5L6 11" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_DOWN_ARROW_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 19V5M12 19L18 13M12 19L6 13" stroke="#eee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""


# --- Stil Fonksiyonları ---
class StyleManager:
    """Uygulama genelinde kullanılan stil tanımlarını yönetir."""

    def __init__(self):
        pass

    def buttonStyle(self):
        """Genel buton ve açılır liste (QComboBox) stilini döndürür."""
        return """
            QPushButton, QComboBox {
                background-color: transparent; color: white; font-size: 14px;
                font-weight: bold; border: 2px solid #555; border-radius: 8px;
                padding: 5px 15px;
            }
            QPushButton:hover, QComboBox:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
            QComboBox::drop-down { border: 0px; }
            QComboBox::down-arrow { image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSI yeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTcgMTBMMTIgMTVMMTcgMTAiIHN0cm9rZT0iI2VlZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPj4=); width: 16px; height: 16px; }
            QComboBox QAbstractItemView { background-color: #282828; border: 1px solid #555; selection-background-color: #444; color: white; }
        """

    def buttonStyleMini(self):
        """Küçük boyutlu butonlar için stil döndürür."""
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 16px;
                border: 2px solid #555; border-radius: 8px; padding: 5px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """
    
    def menuStyle(self):
        """QMenu widget'ı için stil döndürür."""
        return """
            QMenu {
                background-color: #282828;
                border: 1px solid #555;
                color: white;
            }
            QMenu::item:selected {
                background-color: #444;
            }
        """

    def dialogStyle(self):
        """Genel diyalog pencereleri için stil döndürür."""
        return """
            QDialog { background-color: #2b2b2b; border: 2px solid #555; border-radius: 8px; }
            QLabel { color: #f0f0f0; font-size: 14px; }
            QLineEdit { background-color: #333; color: #eee; border: 1px solid #555; border-radius: 4px; padding: 5px; }
            QPushButton { background-color: #3a3a3a; color: #ffffff; border: 1px solid #555; border-radius: 6px; padding: 6px 10px; }
            QPushButton:hover { background-color: #555555; }
            QProgressBar { border: 1px solid #555; border-radius: 5px; text-align: center; }
            QProgressBar::chunk { background-color: #4CAF50; border-radius: 5px; }
            QMessageBox { background-color: #2b2b2b; border: 2px solid #555; border-radius: 8px; }
            QMessageBox QLabel { color: #f0f0f0; font-size: 14px; }
            QMessageBox QPushButton { background-color: #3a3a3a; color: #ffffff; border: 1px solid #555; border-radius: 6px; padding: 6px 10px; }
            QMessageBox QPushButton:hover { background-color: #555555; }
        """

    def draggableBoxNormalStyle(self):
        """DraggableBox'ın normal durumu için stil döndürür."""
        return """
            QFrame {
                background-color: #282828;
                border: 2px solid #444;
                border-radius: 8px;
            }
            QLabel {
                color: #ddd;
                font-size: 12px;
            }
            QTextEdit {
                background-color: #333;
                color: #eee;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px 5px;
                font-size: 14px;
            }
            QCheckBox {
                color: #eee;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 0px;
                border-radius: 4px;
                background-color: #333;
            }
            QCheckBox::indicator:unchecked {
                image: none;
            }
            QCheckBox::indicator:checked {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZ3dCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSI yeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMCw2KSIgZD0iTTYgMTJMTAgMTZMMTggOCIgc3Ryb2tlPSIjMjgyODI4IiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPj4=);
            }
        """

    def draggableBoxSelectedStyle(self):
        """DraggableBox'ın seçili durumu için stil döndürür."""
        return """
            QFrame {
                background-color: #282828;
                border: 2px solid #FFD700; /* Yellow color */
                border-radius: 8px;
            }
            QLabel {
                color: #ddd;
                font-size: 12px;
            }
            QTextEdit {
                background-color: #333;
                color: #eee;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px 5px;
                font-size: 14px;
            }
            QCheckBox {
                color: #eee;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 0px;
                border-radius: 4px;
                background-color: #333;
            }
            QCheckBox::indicator:unchecked {
                image: none;
            }
            QCheckBox::indicator:checked {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZ3dCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSI yeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMCw2KSIgZD0iTTYgMTJMTAgMTZMMTggOCIgc3Ryb2tlPSIjMjgyODI4IiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPj4=);
            }
        """

    def dragHandleNormalStyle(self):
        """Sürükleme tutamacının normal durumu için stil döndürür."""
        return """
            QLabel {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                font-weight: bold;
                color: #eee;
            }
        """

    def dragHandleHoverStyle(self):
        """Sürükleme tutamacının üzerine gelindiğinde (hover) stil döndürür."""
        return """
            QLabel {
                background-color: #444;
                border: 1px solid #666;
                border-radius: 4px;
                font-weight: bold;
                color: #eee;
            }
        """

    def dragHandlePressedStyle(self):
        """Sürükleme tutamacına basıldığında (pressed) stil döndürür."""
        return """
            QLabel {
                background-color: #666;
                border: 1px solid #777;
                border-radius: 4px;
                font-weight: bold;
                color: #eee;
            }
        """
    
    def fileDialogStyle(self):
        """QFileDialog için stil döndürür."""
        return """
            QFileDialog {
                background-color: #2b2b2b;
                color: #f0f0f0;
                border: 1px solid #555;
                border-radius: 8px;
            }
            QFileDialog QLabel {
                color: #f0f0f0;
            }
            QFileDialog QLineEdit {
                background-color: #333;
                color: #eee;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
            }
            QFileDialog QPushButton {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 6px 10px;
            }
            QFileDialog QPushButton:hover {
                background-color: #555555;
            }
            QFileDialog QListView, QTreeView {
                background-color: #333;
                color: #eee;
                border: 1px solid #555;
                border-radius: 4px;
            }
            QFileDialog QListView::item, QTreeView::item {
                padding: 3px;
            }
            QFileDialog QListView::item:selected, QTreeView::item:selected {
                background-color: #444;
                color: #fff;
            }
            /* QFileDialog'un varsayılan butonlarını gizlemeye çalış */
            QFileDialog QToolBar, QFileDialog QDialogButtonBox {
                visibility: hidden;
                width: 0px;
                height: 0px;
                margin: 0px;
                padding: 0px;
                border: 0px;
            }
            /* QFileDialog'un varsayılan "Up" butonu ve yol çubuğunu gizlemeye çalış */
            QFileDialog QToolButton { /* ToolButton'lar genellikle navigation bar'da bulunur */
                visibility: hidden;
                width: 0px;
                height: 0px;
                margin: 0px;
                padding: 0px;
                border: 0px;
            }
            QFileDialog QWidget#fileNameLabel,
            QFileDialog QWidget#fileTypeLabel,
            QFileDialog QWidget#lookInLabel,
            QFileDialog QWidget#fileNameEdit,
            QFileDialog QWidget#fileTypeCombo,
            QFileDialog QWidget#lookInCombo,
            QFileDialog QWidget#sidebar {
                /* Bu widget'ların görünürlüğünü kontrol etmek zor olabilir,
                   ancak varsayılan butonları gizlemek için genel bir yaklaşım */
                /* visibility: hidden; */
                /* width: 0px; */
                /* height: 0px; */
                /* margin: 0px; */
                /* padding: 0px; */
                /* border: 0px; */
            }
        """

    def checkBoxIndicatorCheckedStyle(self):
        """QCheckBox işaretli durumu için gösterge stili döndürür."""
        return """
            QCheckBox {
                color: #eee;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
                border: 0px;
                border-radius: 4px;
                background-color: #FFD700; /* Sarı arka plan */
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZ3dCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSI yeG1sbnM9Imh0dHA6Ly93d3cudzMuc3ZnLzIwMDAvc3ZnIj4KPHBhdGggdHJhbnNmb3JtPSJ0cmFuc2xhdGUoMCw2KSIgZD0iTTYgMTJMTAgMTZMMTggOCIgc3Ryb2tlPSIjMjgyODI4IiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPj4=);
            }
        """

    def checkBoxIndicatorUncheckedStyle(self):
        """QCheckBox işaretsiz durumu için gösterge stili döndürür."""
        return """
            QCheckBox {
                color: #eee;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
                border: 0px;
                border-radius: 4px;
                background-color: #333;
                image: none;
            }
        """

