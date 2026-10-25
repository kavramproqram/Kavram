"""Stiller ve ikonlar. Değerler önceki sürümle birebir aynıdır (arayüz değişmedi)."""
from PyQt5.QtCore import QByteArray, Qt
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer

SVG_SAVE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V7L17 3ZM12 17C10.34 17 9 15.66 9 14C9 12.34 10.34 11 12 11C13.66 11 15 12.34 15 14C15 15.66 13.66 17 12 17Z" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

BUTTON_STYLE = "QPushButton { background-color: transparent; color: white; font-size: 14px; font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 5px; } QPushButton:hover { background-color: #444; } QPushButton:pressed { background-color: #666; } QPushButton:disabled { color: #555; border-color: #333; }"

TOOL_DELETE_STYLE = "QPushButton { background-color: transparent; color: white; font-size: 14px; font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 5px; } QPushButton:hover { background-color: #000000; border-color: #999; } QPushButton:pressed { background-color: #222; } QPushButton:disabled { color: #555; border-color: #333; }"

NOTE_FRAME_STYLE = "NoteWidget { background-color: #2b2b2b; border: 1px solid #444; border-radius: 8px; }"

NOTE_BUTTON_STYLE = """
            QToolButton { background-color: #444; color: #eee; border: 1px solid #666; border-radius: 6px; font-weight: bold; font-family: 'Segoe UI'; }
            QToolButton:hover { background-color: #555; color: white; border-color: #888; }
            QToolButton:pressed { background-color: #333; }
        """

NOTE_DELETE_STYLE = "QToolButton { background-color: #444; color: #aaa; border: 1px solid #666; border-radius: 6px; } QToolButton:hover { background-color: #000000; color: #fff; border-color: #999; }"

GALLERY_BUTTON_STYLE = "QToolButton { background-color: #444; color: #eee; border: 1px solid #666; border-radius: 6px; font-weight: bold; font-family: 'Segoe UI'; } QToolButton:hover { background-color: #555; color: white; border-color: #888; } QToolButton:pressed { background-color: #333; }"

GALLERY_DELETE_STYLE = "QToolButton { background-color: #333; color: #aaa; border: 1px solid #555; border-radius: 6px; font-weight: bold; font-family: 'Segoe UI'; } QToolButton:hover { background-color: #000000; color: #fff; border-color: #999; } QToolButton:pressed { background-color: #222; }"

MENU_STYLE = "QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item { padding: 5px 20px; } QMenu::item:selected { background-color: #555; }"

NAV_MENU_STYLE = "QMenu { background-color: #333; color: white; border: 1px solid #555; font-size: 14px; } QMenu::item { padding: 8px 25px; } QMenu::item:selected { background-color: #555; }"

PREVIEW_CLOSE_STYLE = "background: #333; color: white; font-weight: bold; font-size: 16px; border: none;"


def create_svg_icon(svg_content: str, size: int = 20, color: str = "#ffffff") -> QIcon:
    modified = svg_content.replace('stroke="#aaa"', f'stroke="{color}"').replace(
        'fill="#aaa"', f'fill="{color}"')
    renderer = QSvgRenderer(QByteArray(modified.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)
