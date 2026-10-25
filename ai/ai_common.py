# Kavram AI Editörü — ortak yardımcılar, ikonlar, sabitler
# Kavram 2.2.2 | GNU GPL v3 veya üstü (ayrıntı: ai.py başlığı ve /Kavram/License/GPLv3.txt)

import filecmp
import os

from PyQt5.QtCore import Qt, QByteArray
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer

try:
    from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
    from PyQt5.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
    QT_MULTIMEDIA_AVAILABLE = True
except ImportError:
    from PyQt5.QtWidgets import QWidget
    QT_MULTIMEDIA_AVAILABLE = False
    QMediaPlayer = None
    QMediaContent = None
    QVideoWidget = QWidget
    QGraphicsVideoItem = None
    print("PyQt5.QtMultimedia veya PyQt5.QtMultimediaWidgets kütüphanesi yüklenemedi. Medya özellikleri sınırlı çalışabilir.")

# Bir pakete eklenebilecek en fazla dosya sayısı
MAX_MEDIA_PER_PACKET = 16


def same_file_content(path_a, path_b):
    """İki dosyanın içeriği birebir aynı mı? (yalnızca boyut karşılaştırması yanıltıcıydı)"""
    try:
        return filecmp.cmp(path_a, path_b, shallow=False)
    except OSError:
        return False


def create_svg_icon(svg_content, size=20, color="#ffffff"):
    modified_svg_content = svg_content.replace('stroke="#aaa"', f'stroke="{color}"').replace('fill="#aaa"', f'fill="{color}"')
    renderer = QSvgRenderer(QByteArray(modified_svg_content.encode('utf-8')))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

SVG_SAVE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V7L17 3ZM12 17C10.34 17 9 15.66 9 14C9 12.34 10.34 11 12 11C13.66 11 15 12.34 15 14C15 15.66 13.66 17 12 17Z" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""
SVG_X_ICON = """<svg viewBox="0 0 24 24" fill="none" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>"""
SVG_PLAY_ICON = """<svg viewBox="0 0 24 24" fill="white"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>"""
SVG_PAUSE_ICON = """<svg viewBox="0 0 24 24" fill="white"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>"""
SVG_IMAGE_ICON = """<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>"""
SVG_FILE_ICON = """<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>"""
