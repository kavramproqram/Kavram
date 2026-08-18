# file_manager.py - TAM DOSYA
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

import os
import sys
import ctypes
import subprocess
import tempfile
import tarfile
import time
from pathlib import Path
from datetime import datetime

from PyQt5.QtCore import (Qt, QSize, QSettings, pyqtSignal, QMimeData, QUrl, QTimer, QEvent, QPointF, QRectF)
from PyQt5.QtGui import (QIcon, QPixmap, QPainter, QColor, QFont, QPen, QCursor, QDrag,
                         QPainterPath, QLinearGradient, QRadialGradient, QBrush)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QListWidget, QListWidgetItem, QLineEdit, QMessageBox,
    QListView, QComboBox, QSizePolicy, QProgressDialog, QFileDialog, QDialog, QProgressBar, QAbstractItemView
)

BASE_DIR = Path(__file__).resolve().parent
ENGINE_C = BASE_DIR / "file_engine.c"
ENGINE_SO = BASE_DIR / "libfile_engine.so"
VIEW_C = BASE_DIR / "view_engine.c"
VIEW_SO = BASE_DIR / "libview_engine.so"

# Kavram ikonu tüm File Manager pencerelerinde tek kaynaktan kullanılır.
# Öncelik kullanıcı ev dizinindeki Kavram/ikon yapısındadır; paketlenmiş/
# farklı konumda çalışan sürümlerde dosyanın yanındaki ikon güvenli geri dönüş yoludur.
_ICON_CANDIDATES = (
    Path("/home/lts/Kavram/ikon/Kavram.png"),
    Path.home() / "Kavram" / "ikon" / "Kavram.png",
    BASE_DIR / "ikon" / "Kavram.png",
)
APP_ICON = next((candidate for candidate in _ICON_CANDIDATES if candidate.is_file()), _ICON_CANDIDATES[0])

FILE_ENGINE_C_SRC = r"""#define _GNU_SOURCE
#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <pthread.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include <limits.h>
#include <math.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    char name[256];
    char path[1024];
    bool is_directory;
    bool is_hidden;
    uint64_t size;
    int64_t mtime;
} FileItem;

static _Thread_local FileItem *g_items = NULL;
static _Thread_local size_t g_items_count = 0;
static _Thread_local size_t g_items_capacity = 0;

static void copy_str(char *dst, size_t cap, const char *src) {
    if (!dst || cap == 0) return;
    if (!src) src = "";
    size_t n = strlen(src);
    if (n >= cap) n = cap - 1;
    memcpy(dst, src, n);
    dst[n] = '\0';
}

static int append_item(const FileItem *item) {
    if (g_items_count == g_items_capacity) {
        size_t next = g_items_capacity ? g_items_capacity * 2 : 128;
        FileItem *p = (FileItem *)realloc(g_items, next * sizeof(*g_items));
        if (!p) return 0;
        g_items = p;
        g_items_capacity = next;
    }
    g_items[g_items_count++] = *item;
    return 1;
}

int fetch_directory_items(const char *dir_path, int show_hidden, int sort_mode) {
    g_items_count = 0;
    if (!dir_path || !*dir_path) return -1;
    DIR *dir = opendir(dir_path);
    if (!dir) return -1;
    struct dirent *de;
    while ((de = readdir(dir)) != NULL) {
        const char *name = de->d_name;
        if (!name[0] || (!show_hidden && name[0] == '.')) continue;
        FileItem item;
        memset(&item, 0, sizeof(item));
        copy_str(item.name, sizeof(item.name), name);
        snprintf(item.path, sizeof(item.path), "%s/%s", dir_path, name);
        item.is_hidden = (name[0] == '.');
        struct stat st;
        if (stat(item.path, &st) == 0) {
            item.is_directory = S_ISDIR(st.st_mode);
            item.size = S_ISREG(st.st_mode) ? (uint64_t)st.st_size : 0;
            item.mtime = (int64_t)st.st_mtime;
        }
        if (!append_item(&item)) { closedir(dir); return -1; }
    }
    closedir(dir);
    return (int)g_items_count;
}

bool get_item_at(int index, FileItem *out_item) {
    if (!out_item || index < 0 || (size_t)index >= g_items_count) return false;
    *out_item = g_items[(size_t)index];
    return true;
}

void clear_cache(void) {
    free(g_items);
    g_items = NULL;
    g_items_count = 0;
    g_items_capacity = 0;
}

int trash_item(const char *file_path) {
    if (!file_path || !*file_path) return 0;
    return (remove(file_path) == 0) ? 1 : 0;
}

#ifdef __cplusplus
}
#endif
"""

def _ensure_c_files():
    if not ENGINE_C.exists():
        ENGINE_C.write_text(FILE_ENGINE_C_SRC, encoding="utf-8")

def _compile_engine():
    _ensure_c_files()
    try:
        if not ENGINE_SO.exists() or ENGINE_C.stat().st_mtime_ns > ENGINE_SO.stat().st_mtime_ns:
            subprocess.run(["cc", "-O3", "-fPIC", "-shared", str(ENGINE_C), "-o", str(ENGINE_SO), "-pthread"], check=True)
    except Exception as e:
        print("[Engine] Compile note:", e)

_compile_engine()

class FileItem(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char * 256),
        ("path", ctypes.c_char * 1024),
        ("is_directory", ctypes.c_bool),
        ("is_hidden", ctypes.c_bool),
        ("size", ctypes.c_uint64),
        ("mtime", ctypes.c_int64),
    ]

def load_native_engine():
    try:
        if not ENGINE_SO.exists():
            return None
        lib = ctypes.CDLL(str(ENGINE_SO))
        lib.fetch_directory_items.restype = ctypes.c_int
        lib.fetch_directory_items.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        lib.get_item_at.restype = ctypes.c_bool
        lib.get_item_at.argtypes = [ctypes.c_int, ctypes.POINTER(FileItem)]
        lib.clear_cache.restype = None
        lib.trash_item.restype = ctypes.c_int
        lib.trash_item.argtypes = [ctypes.c_char_p]
        return lib
    except Exception:
        return None

_native_engine = load_native_engine()

AUDIO_EXTS = {".sound", ".wav", ".aiff", ".flac", ".ogg", ".mp3", ".m4a", ".aac", ".wma", ".opus"}
VIDEO_EXTS = {".rec", ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
IMAGE_EXTS = {".drawing", ".png", ".pnf", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff", ".tif"}
TEXT_EXTS = {".txr", ".txt", ".json", ".pdf"}

ALL_AUDIO = AUDIO_EXTS
ALL_VIDEO = VIDEO_EXTS
ALL_IMAGE = IMAGE_EXTS
ALL_PDF = {".pdf"}
ALL_MEDIA = ALL_AUDIO | ALL_VIDEO | ALL_IMAGE | ALL_PDF

# Editör bağlamı için varsayılan uzantı kümeleri.
# Bu tablo mevcut File Manager filtrelerini bozmaz; yalnızca başka bir
# Kavram penceresinden açıldığında başlangıç filtresini seçmek için kullanılır.
EDITOR_DEFAULT_EXTENSIONS = {
    "Drawing": ALL_IMAGE | {".drawing"},
    "Text": {".txr"},
    "Ai": {".ai"},
    "Sound": {".sound", ".wav", ".aiff", ".flac", ".ogg", ".mp3"},
    "Media": {".media"},
    "Rec": {".rec"},
    "Copy": {".copya"},
    "Program": "EXEC",
    "Sphere": {
        ".kitap",
        ".copya", ".rec", ".txr",
        ".png", ".pnf", ".jpg", ".jpeg", ".bmp", ".gif",
        ".ai",
        ".sound", ".wav", ".aiff", ".flac", ".ogg", ".mp3",
        ".aac", ".m4a",
        ".media", ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv",
        ".blend",
    },
}


def get_editor_default_extensions(editor_name, custom_editors=None):
    """Seçilen editör için File Manager'ın varsayılan filtre uzantılarını döndürür."""
    if custom_editors:
        for editor in custom_editors:
            if editor.get("name") == editor_name:
                extensions = editor.get("extensions", [])
                if isinstance(extensions, str):
                    extensions = [extensions]
                normalized = set()
                for ext in extensions:
                    if ext:
                        ext = str(ext).lower()
                        normalized.add(ext if ext.startswith(".") else "." + ext)
                if normalized:
                    return normalized
    return EDITOR_DEFAULT_EXTENSIONS.get(editor_name)

FILTER_CATEGORIES = [
    # Sphere açma penceresinde kullanılacak üç temel filtre.
    ("Sphere Dosyaları", EDITOR_DEFAULT_EXTENSIONS["Sphere"]),
    ("Tüm Dosyalar (*)", None),
    (".kitap Dosyaları", {".kitap"}),
]

_TYPE_ICON_CACHE = {}

def format_size(size):
    n = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"

def make_type_icon(ext, is_dir):
    """
    Siyah, Gri ve Güneş (Sarı/Gold) temalı son derece modern vektörel ikonlar üretir.
    - .kitap: Dark temalı şık kitap kaplaması + dairesel fon olmadan tam kapağı kaplayan saydam Kavram logosu
    - Klasörler, Arşivler (.xz, .tar, .zip) ve diğer türler: Siyah/Gri + Güneş Vurgulu modern görünüm
    - .txr: Beyaz zemin üzerine büyük ve siyah "txr" yazısı, sayfa çizgileriyle belge görünümü
    """
    cache_key = (ext, is_dir)
    if cache_key in _TYPE_ICON_CACHE:
        return _TYPE_ICON_CACHE[cache_key]

    px = QPixmap(128, 128)
    px.fill(Qt.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)

    SUN_GOLD = QColor("#999999")
    SUN_AMBER = QColor("#222222")
    DARK_BG_1 = QColor("#1e2022")
    DARK_BG_2 = QColor("#121416")
    GRAY_BORDER = QColor("#3f444c")

    if is_dir:
        # --- KLASÖR İKONU (Dark Obsidian + Güneş Sarısı Vurgu) ---
        # Arka tab
        painter.setBrush(QColor("#333333"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(14, 24, 56, 24, 8, 8)

        # Klasör Gövdesi
        grad = QLinearGradient(14, 34, 114, 110)
        grad.setColorAt(0.0, QColor("#22252a"))
        grad.setColorAt(1.0, QColor("#141618"))
        painter.setBrush(grad)
        painter.setPen(QPen(GRAY_BORDER, 2))
        painter.drawRoundedRect(14, 32, 100, 78, 10, 10)

        # Güneş Vurgu Çizgisi
        painter.setPen(QPen(SUN_AMBER, 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(28, 44, 58, 44)

    elif ext == ".kitap":
        # --- .KİTAP İKONU (Siyah/Koyu Gri Dark Tema + Güneş Vurgulu + Tam Kapağı Kaplayan İkon) ---
        DARK_COVER = QColor("#1b1e23")
        DARK_GRAD_START = QColor("#2c3038")
        DARK_GRAD_END = QColor("#111316")
        PAGE_COLOR = QColor("#404652")

        # Gölgeli Zemin
        painter.setBrush(QColor("#08090a"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(16, 12, 96, 108, 10, 10)

        # Kitap Sayfaları Yan Kenarı
        painter.setBrush(PAGE_COLOR)
        painter.drawRoundedRect(22, 16, 90, 100, 8, 8)

        # Kitap Kapağı (Siyah/Dark Gri Gradyan)
        grad = QLinearGradient(16, 10, 106, 114)
        grad.setColorAt(0.0, DARK_GRAD_START)
        grad.setColorAt(0.5, DARK_COVER)
        grad.setColorAt(1.0, DARK_GRAD_END)

        painter.setBrush(grad)
        painter.setPen(QPen(SUN_AMBER, 2))
        painter.drawRoundedRect(16, 10, 90, 106, 9, 9)

        # Kitap Sırtı / Spine Çizgisi (Güneş Sarısı Accent)
        painter.setPen(QPen(SUN_GOLD, 3))
        painter.drawLine(28, 10, 28, 116)

        # Otomatik Kavram Logosu Overlay
        # Daire FON OLMADAN, transparan amblem doğrudan kitap kapağını kaplar
        cover_x, cover_y, cover_w, cover_h = 32, 16, 70, 94
        logo_drawn = False
        if APP_ICON.is_file():
            logo = QPixmap(str(APP_ICON))
            if not logo.isNull():
                logo_scaled = logo.scaled(cover_w, cover_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                lx = cover_x + (cover_w - logo_scaled.width()) // 2
                ly = cover_y + (cover_h - logo_scaled.height()) // 2
                painter.drawPixmap(lx, ly, logo_scaled)
                logo_drawn = True

        if not logo_drawn:
            painter.setPen(QPen(SUN_GOLD, 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(52, 46, 32, 32)

    elif ext == ".txr":
        # --- METİN DOSYASI (.txr) İKONU ---
        # Beyaz zemin (belge kağıdı)
        painter.setBrush(QColor("#222222"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)
        # Kenarlık çizgisi
        painter.setPen(QPen(QColor("#999999"), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)
        # Sayfa çizgileri (metin satırı görünümü)
        painter.setPen(QPen(QColor("#cccccc"), 1))
        for i in range(3):
            y = 30 + i * 22
            painter.drawLine(26, y, 102, y)
        # "txr" yazısı - büyük ve siyah, sayfanın alt kısmına
        painter.setPen(QPen(QColor("#000000"), 2))
        font = QFont("Segoe UI", 20, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(16, 12, 96, 104), Qt.AlignBottom | Qt.AlignHCenter, "txr")

    elif ext in {".xz", ".tar", ".gz", ".zip", ".7z", ".rar", ".copya"}:
        # --- ARŞİV DOSYALARI (.xz, .tar vb.) ---
        grad = QLinearGradient(16, 12, 112, 116)
        grad.setColorAt(0.0, QColor("#28231d"))
        grad.setColorAt(1.0, QColor("#15120e"))
        painter.setBrush(grad)
        painter.setPen(QPen(SUN_AMBER, 2))
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)

        # Fermuar / Paket Vektörü
        painter.setPen(QPen(SUN_GOLD, 3, Qt.DashLine))
        painter.drawLine(64, 20, 64, 80)
        painter.setBrush(SUN_AMBER)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(58, 50, 12, 18, 3, 3)

        painter.setPen(QPen(QColor("#fff3d6")))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(QRectF(16, 90, 96, 20), Qt.AlignCenter, ext.replace(".", "").upper())

    elif ext in IMAGE_EXTS:
        # --- RESİM DOSYALARI ---
        grad = QLinearGradient(16, 12, 112, 116)
        grad.setColorAt(0.0, DARK_BG_1)
        grad.setColorAt(1.0, DARK_BG_2)
        painter.setBrush(grad)
        painter.setPen(QPen(GRAY_BORDER, 2))
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)

        # Çerçeve
        painter.setBrush(QColor("#0d0e10"))
        painter.setPen(QPen(SUN_AMBER, 1.5))
        painter.drawRoundedRect(24, 20, 80, 70, 8, 8)

        # Güneş Sembolü
        painter.setBrush(SUN_GOLD)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(76, 28, 16, 16)

        # Dağlar Vektör Path
        mountain = QPainterPath()
        mountain.moveTo(24, 82)
        mountain.lineTo(46, 56)
        mountain.lineTo(62, 72)
        mountain.lineTo(78, 50)
        mountain.lineTo(104, 82)
        mountain.closeSubpath()

        painter.setBrush(SUN_AMBER)
        painter.drawPath(mountain)

        painter.setPen(QPen(QColor("#e0e0e0")))
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        painter.drawText(QRectF(16, 94, 96, 18), Qt.AlignCenter, ext.replace(".", "").upper())

    elif ext in AUDIO_EXTS:
        # --- SES DOSYALARI ---
        grad = QLinearGradient(16, 12, 112, 116)
        grad.setColorAt(0.0, QColor("#221d15"))
        grad.setColorAt(1.0, QColor("#120f0a"))
        painter.setBrush(grad)
        painter.setPen(QPen(SUN_AMBER, 2))
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)

        painter.setPen(QPen(SUN_GOLD, 3, Qt.SolidLine, Qt.RoundCap))
        bars = [22, 42, 58, 34, 50, 26]
        for idx, h in enumerate(bars):
            bx = 36 + (idx * 10)
            by = 60 - (h // 2)
            painter.drawLine(bx, by, bx, by + h)

        painter.setPen(QPen(QColor("#fff3d6")))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(QRectF(16, 92, 96, 18), Qt.AlignCenter, ext.replace(".", "").upper())

    elif ext in VIDEO_EXTS:
        # --- VİDEO DOSYALARI ---
        grad = QLinearGradient(16, 12, 112, 116)
        grad.setColorAt(0.0, QColor("#282015"))
        grad.setColorAt(1.0, QColor("#14100a"))
        painter.setBrush(grad)
        painter.setPen(QPen(SUN_AMBER, 2))
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)

        play_path = QPainterPath()
        play_path.moveTo(56, 42)
        play_path.lineTo(80, 58)
        play_path.lineTo(56, 74)
        play_path.closeSubpath()

        painter.setBrush(SUN_GOLD)
        painter.setPen(Qt.NoPen)
        painter.drawPath(play_path)

        painter.setPen(QPen(QColor("#fff3d6")))
        painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
        painter.drawText(QRectF(16, 92, 96, 18), Qt.AlignCenter, ext.replace(".", "").upper())

    else:
        # --- GENEL DOSYA İKONU ---
        grad = QLinearGradient(18, 10, 110, 118)
        grad.setColorAt(0.0, QColor("#25282e"))
        grad.setColorAt(1.0, QColor("#141619"))
        painter.setBrush(grad)
        painter.setPen(QPen(GRAY_BORDER, 2))
        painter.drawRoundedRect(18, 10, 92, 108, 10, 10)

        fold = QPainterPath()
        fold.moveTo(82, 10)
        fold.lineTo(110, 38)
        fold.lineTo(82, 38)
        fold.closeSubpath()
        painter.setBrush(QColor("#353a43"))
        painter.setPen(QPen(GRAY_BORDER, 1))
        painter.drawPath(fold)

        label_text = ext.replace(".", "").upper()[:6] if ext else "DOSYA"
        painter.setPen(QPen(SUN_AMBER))
        painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
        painter.drawText(QRectF(18, 56, 92, 24), Qt.AlignCenter, label_text)

    painter.end()
    icon = QIcon(px)
    _TYPE_ICON_CACHE[cache_key] = icon
    return icon



_MESSAGE_BOX_STYLE = """
    QMessageBox { background:#1b1b1b; color:#f0f0f0; border:1px solid #555; border-radius:6px; }
    QMessageBox QLabel { color:#f0f0f0; font-size:13px; min-width:280px; }
    QMessageBox QPushButton { background:#333; color:#f0f0f0; border:1px solid #666; border-radius:5px; padding:6px 14px; min-width:68px; }
    QMessageBox QPushButton:hover { background:#444; }
    QMessageBox QPushButton:pressed { background:#555; }
"""


class BookmarkButton(QPushButton):
    bindRequested = pyqtSignal()
    navigateRequested = pyqtSignal(str)

    def __init__(self, default_path, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.target_path = ""
        self.set_target_path(default_path)

    def set_target_path(self, path):
        if path and os.path.exists(path):
            self.target_path = os.path.abspath(path)
            folder_name = os.path.basename(self.target_path)
            if not folder_name:
                folder_name = self.target_path
            self.setText(f"X ({folder_name})")
        else:
            self.target_path = ""
            self.setText("X")

        fm = self.fontMetrics()
        text_width = fm.horizontalAdvance(self.text())
        new_width = max(110, text_width + 24)
        self.setFixedWidth(new_width)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.bindRequested.emit()
        elif event.button() == Qt.LeftButton:
            if self.target_path and os.path.exists(self.target_path):
                self.navigateRequested.emit(self.target_path)
            else:
                QMessageBox.information(self, "Bilgi", "Pimlenmiş bir konum yok. Sağ tıklayarak mevcut klasörü pimleyebilirsiniz.")
        else:
            super().mousePressEvent(event)

class HoverPreviewCard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.ToolTip | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QFrame#card {
                background-color: #141414;
                border: 1.5px solid #475569;
                border-radius: 10px;
            }
            QLabel {
                color: #f0f0f0;
                font-size: 13px;
                font-weight: 600;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.card_frame = QFrame()
        self.card_frame.setObjectName("card")
        frame_layout = QVBoxLayout(self.card_frame)
        frame_layout.setContentsMargins(12, 12, 12, 12)
        frame_layout.setSpacing(8)

        self.img_label = QLabel("Yükleniyor...")
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setFixedSize(320, 210)
        self.img_label.setStyleSheet("background-color: #0a0a0a; border-radius: 6px; color: #e2e8f0; font-size: 14px; font-weight: bold;")

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)

        frame_layout.addWidget(self.img_label)
        frame_layout.addWidget(self.info_label)
        layout.addWidget(self.card_frame)

        self.hide()

    def show_preview(self, filepath, is_dir=False, is_video=False, is_image=False):
        filename = os.path.basename(filepath)
        size_text = format_size(os.path.getsize(filepath)) if not is_dir and os.path.exists(filepath) else "Dizin"
        ext = Path(filepath).suffix.lower() if not is_dir else "Klasör"

        mtime_str = ""
        try:
            mtime = os.path.getmtime(filepath)
            mtime_str = datetime.fromtimestamp(mtime).strftime('%d.%m.%Y %H:%M')
        except Exception:
            mtime_str = "Bilinmiyor"

        if is_dir:
            kind = "Klasör Konumu"
        elif ext == ".kitap":
            kind = "Kavram Kitap Arşivi"
        elif ext in {".xz", ".tar", ".gz", ".zip", ".7z"}:
            kind = f"Sıkıştırılmış Arşiv ({ext.upper()})"
        elif is_video:
            kind = "Video Dosyası"
        elif is_image:
            kind = "Görsel Dosya"
        else:
            kind = f"Dosya ({ext.upper()})"

        self.info_label.setText(f"<span style='color:#e2e8f0; font-size:14px;'><b>{kind}</b></span><br/>"
                                f"<b>Adı:</b> {filename}<br/>"
                                f"<b>Boyut:</b> {size_text} &nbsp;|&nbsp; <b>Tarih:</b> {mtime_str}")

        if is_image:
            pix = QPixmap(filepath)
            if not pix.isNull():
                scaled = pix.scaled(320, 210, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.img_label.setPixmap(scaled)
            else:
                self.img_label.setText("Görsel Yüklenemedi")
        elif is_video:
            thumb_path = os.path.join(tempfile.gettempdir(), "kavram_hover_thumb.png")
            cmd = ["ffmpeg", "-y", "-ss", "00:00:02.000", "-i", filepath, "-vframes", "1", "-vf", "scale=320:210:force_original_aspect_ratio=decrease", thumb_path]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                if os.path.exists(thumb_path):
                    pix = QPixmap(thumb_path)
                    self.img_label.setPixmap(pix)
                else:
                    self.img_label.setText("Video Önizlemesi Alınamadı")
            except Exception:
                self.img_label.setText("FFmpeg Yok / Önizleme Yok")
        else:
            icon = make_type_icon(ext, is_dir)
            large_pix = icon.pixmap(160, 160)
            self.img_label.setPixmap(large_pix)

        cursor_pos = QCursor.pos()
        screen = QApplication.primaryScreen().geometry()
        x = cursor_pos.x() + 20
        y = cursor_pos.y() + 20

        if x + 350 > screen.width():
            x = cursor_pos.x() - 360
        if y + 280 > screen.height():
            y = cursor_pos.y() - 290

        self.move(x, y)
        self.show()
        self.raise_()

    def hide_preview(self):
        self.hide()


class HoverListWidget(QListWidget):
    itemHovered = pyqtSignal(str, bool, bool, bool)  # path, is_dir, is_video, is_image
    mouseLeft = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragOnly)
        self.setDefaultDropAction(Qt.CopyAction)
        self._last_hovered_path = None

    def startDrag(self, supported_actions):
        """
        File Manager içindeki seçili gerçek dosyaları Qt'nin standart
        file:// MIME biçiminde sürükler. Klasörler sürüklenmez.
        """
        paths = []
        for item in self.selectedItems():
            data = item.data(Qt.UserRole)
            if not data:
                continue
            full_path, is_dir = data
            if not is_dir and os.path.isfile(full_path):
                paths.append(os.path.abspath(full_path))

        if not paths:
            return

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(path) for path in paths])

        # Text Editor'a özel sürükleme işareti.
        # Standart file:// URL'leri aynen korunur; yalnızca Kavram File
        # Manager'dan gelen sürüklemeleri Text Editor özel olarak algılar.
        mime_data.setData("application/x-kavram-file-manager-drag", b"1")

        # Drawing Editor'a özel: sürüklenen dosyanın türünü belirt
        if paths:
            ext = os.path.splitext(paths[0])[1].lower()
            if ext in {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".pnf"}:
                mime_data.setData("application/x-kavram-image-drag", b"1")

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        selected_item = self.currentItem()
        if selected_item:
            drag.setPixmap(selected_item.icon().pixmap(QSize(64, 64)))

        drag.exec_(Qt.CopyAction)

    def mouseMoveEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            data = item.data(Qt.UserRole)
            if data:
                full_path, is_dir = data
                if full_path != self._last_hovered_path:
                    self._last_hovered_path = full_path
                    ext = Path(full_path).suffix.lower()
                    is_image = not is_dir and ext in IMAGE_EXTS
                    is_video = not is_dir and ext in VIDEO_EXTS
                    self.itemHovered.emit(full_path, is_dir, is_video, is_image)
        else:
            if self._last_hovered_path is not None:
                self._last_hovered_path = None
                self.mouseLeft.emit()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._last_hovered_path = None
        self.mouseLeft.emit()
        super().leaveEvent(event)


def apply_kavram_icon(widget):
    """Pencere/dialog başlık çubuğunda daima Kavram ikonunu kullan."""
    try:
        if APP_ICON.is_file():
            widget.setWindowIcon(QIcon(str(APP_ICON)))
    except Exception:
        pass


class KitapOperationDialog(QDialog):
    """.kitap içe/dışa aktarma için ortak, genişleyebilir işlem penceresi."""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        apply_kavram_icon(self)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.resize(520, 190)
        self.cancelled = False
        self._finished = False
        self._base_height = 190
        self._expanded = False

        self.setStyleSheet("""
            QDialog { background:#1b1b1b; color:#f0f0f0; border:1px solid #555; }
            QLabel { color:#f0f0f0; }
            QProgressBar {
                border:1px solid #555; border-radius:5px; background:#2b2b2b;
                height:22px; text-align:center; color:#f0f0f0;
            }
            QProgressBar::chunk { background:#8a8a8a; border-radius:4px; }
            QPushButton {
                background:#333; color:#f0f0f0; border:1px solid #666;
                border-radius:5px; padding:6px 18px; min-width:72px;
            }
            QPushButton:hover { background:#444; }
            QPushButton:pressed { background:#555; }
        """)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        self.label=QLabel("Hazırlanıyor...")
        self.label.setWordWrap(True)
        self.size_label=QLabel("Dosya boyutu: 0 B")
        self.progress=QProgressBar()
        self.progress.setRange(0,100)
        self.detail_label=QLabel("")
        self.detail_label.setWordWrap(True)
        self.detail_label.setStyleSheet("color:#bcbcbc; padding-top:4px;")
        self.detail_label.hide()
        self.button=QPushButton("İptal")
        self.button.clicked.connect(self._button_clicked)
        layout.addWidget(self.label)
        layout.addWidget(self.size_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.detail_label)
        row=QHBoxLayout()
        row.addStretch()
        row.addWidget(self.button)
        layout.addLayout(row)
        self.timer=QTimer(self)
        self.timer.timeout.connect(self.refresh_size)

    def _button_clicked(self):
        if not self._finished:
            self.cancelled=True
            self.label.setText("İptal ediliyor...")
            self.button.setEnabled(False)
        else:
            self.accept()

    def start(self, path):
        self.output_path=path
        self.timer.start(150)
        self.show()
        self.raise_()
        self.activateWindow()
        QApplication.processEvents()

    def refresh_size(self):
        size=0
        try:
            if getattr(self, 'output_path', None) and os.path.exists(self.output_path):
                size=os.path.getsize(self.output_path)
        except OSError:
            pass
        self.size_label.setText(f"Dosya boyutu: {format_size(size)}")

    def update_progress(self, value, text=""):
        if self.cancelled:
            return False
        self.progress.setValue(max(0,min(100,int(value))))
        if text:
            self.label.setText(text)
        self.refresh_size()
        QApplication.processEvents()
        return not self.cancelled

    def finish(self, path, summary="İşlem başarıyla tamamlandı."):
        self.refresh_size()
        final_size=os.path.getsize(path) if os.path.exists(path) else 0
        self.progress.setValue(100)
        self.label.setText("Tamamlandı")
        self.size_label.setText(f"Dosya boyutu: {format_size(final_size)}")
        self.detail_label.setText(summary)
        self.detail_label.show()
        self.button.setText("OK")
        self.button.setEnabled(True)
        self._finished=True
        self.timer.stop()
        if not self._expanded:
            self._expanded = True
            self.resize(self.width(), self._base_height + 68)
            self.adjustSize()
        QApplication.processEvents()

    def finish_message(self, summary):
        self.label.setText("Tamamlandı")
        self.detail_label.setText(summary)
        self.detail_label.show()
        self.button.setText("OK")
        self.button.setEnabled(True)
        self._finished=True
        self.timer.stop()
        if not self._expanded:
            self._expanded = True
            self.resize(self.width(), self._base_height + 68)
            self.adjustSize()
        QApplication.processEvents()

    def reject(self):
        if not self._finished:
            self.cancelled=True
            return
        super().reject()



class FileManager(QWidget):
    _instance = None          # Tek örnek
    _is_opening = False       # Açılış sırasında tekrar açmayı engellemek için

    @classmethod
    def open_singleton(cls, parent=None, target_editor=None, custom_editors=None,
                       filter_extensions=None, mode="open",
                       export_callback=None, export_compression="xz",
                       default_export_name=None):
        """FileManager'ın tek örneğini açar; varsa eskisini kapatır."""
        if cls._is_opening:
            return None
        cls._is_opening = True
        try:
            # Eğer örnek varsa ve hâlâ geçerliyse kapat
            if cls._instance is not None:
                try:
                    cls._instance.close()
                except Exception:
                    pass
                cls._instance = None

            # Yeni örneği oluştur
            cls._instance = cls(
                parent=parent,
                target_editor=target_editor,
                custom_editors=custom_editors,
                filter_extensions=filter_extensions,
                mode=mode,
                export_callback=export_callback,
                export_compression=export_compression,
                default_export_name=default_export_name
            )
            # Pencere kapatıldığında _instance temizlensin
            cls._instance.destroyed.connect(cls._on_instance_destroyed)
            cls._instance.show()
            cls._instance.raise_()
            cls._instance.activateWindow()
            return cls._instance
        finally:
            cls._is_opening = False

    @classmethod
    def _on_instance_destroyed(cls):
        """Örnek yok edildiğinde class variable'ı temizle."""
        if cls._instance is not None:
            cls._instance = None

    fileSelected = pyqtSignal(str)
    filesSelected = pyqtSignal(list)
    exportCompleted = pyqtSignal(str)
    exportCancelled = pyqtSignal()

    def __init__(self, parent=None, target_editor=None, custom_editors=None, filter_extensions=None, mode="open", export_callback=None, export_compression="xz", default_export_name=None):
        super().__init__(parent)
        apply_kavram_icon(self)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.settings = QSettings("Kavram", "KavramFileManager")
        self.preview_enabled = self.settings.value("hover_preview_enabled", True, type=bool)

        # Başka bir Kavram editöründen açıldığında File Manager bu bağlamı
        # korur. Normal tek başına kullanımda davranış değişmez.
        self.target_editor = target_editor
        self.custom_editors = custom_editors or []
        self.context_filter_extensions = filter_extensions
        self.integration_mode = target_editor is not None
        # File Manager her zaman Kavram.py tarafından yönetilir.
        # mode="export" yalnızca dışa aktarma arayüzünü etkinleştirir;
        # gerçek arşivleme işlemi çağıran editöre callback ile geri teslim edilir.
        self.mode = mode or "open"
        self.export_callback = export_callback
        self.export_compression = export_compression if export_compression in ("xz", "gz") else "xz"
        self.default_export_name = default_export_name

        default_export_lts = Path("/home/lts/Kavram/Export")
        default_export_home = Path.home() / "Kavram" / "Export"

        if default_export_lts.exists():
            self.export_dir = str(default_export_lts)
        else:
            try:
                default_export_home.mkdir(parents=True, exist_ok=True)
                self.export_dir = str(default_export_home)
            except Exception:
                self.export_dir = os.path.expanduser("~")

        saved_bookmark = self.settings.value("bookmark_path", "")

        self.current_path = self.export_dir
        self.show_hidden = False
        self.selected_filter = None
        self.search_text = ""  # Arama metni

        self.history = []
        self.history_index = -1

        self.hover_card = HoverPreviewCard(self)
        self._init_ui(saved_bookmark)
        self._navigate_to(self.current_path, push_history=True)

        if self.target_editor is not None:
            self.set_editor_context(
                self.target_editor,
                self.custom_editors,
                self.context_filter_extensions
            )

        # File Manager açıldığında klavye doğrudan alt alana odaklanır.
        # Export modunda alan gerçek dosya adıdır ve kullanıcıya varsayılan
        # "Sphere" gibi bir ad dayatılmaz.
        self.search_edit.setFocus(Qt.OtherFocusReason)
        if self.mode == "export":
            self.search_edit.clear()
            self.search_edit.setPlaceholderText("Dosya adı (.txr otomatik eklenir)")

    def _init_ui(self, initial_bookmark):
        self.setWindowTitle("File")
        self.resize(1120, 720)

        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: #f0f0f0;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11pt;
            }
            QFrame#topBar, QFrame#bottomBar {
                background-color: #1a1a1a;
                border-bottom: 1px solid #333333;
                min-height: 44px;
                max-height: 44px;
            }
            QPushButton {
                background-color: #222222;
                color: #f0f0f0;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #333333;
                color: #ffffff;
                border-color: #666666;
            }
            QPushButton:pressed {
                background-color: #444444;
                color: #ffffff;
            }
            QPushButton:disabled {
                background-color: #181818;
                color: #555555;
                border-color: #2c2c2c;
            }
            QLineEdit {
                background-color: #0a0a0a;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11pt;
            }
            QLineEdit:focus {
                border: 1px solid #888888;
            }
            QListWidget {
                background-color: #0c0c0c;
                border: 1px solid #333333;
                border-radius: 8px;
                padding: 8px;
                font-size: 11pt;
            }
            QListWidget::item {
                padding: 10px;
                margin: 4px;
                border-radius: 8px;
                background-color: #181818;
                color: #f0f0f0;
            }
            QListWidget::item:hover {
                background-color: #282828;
                border: 1px solid #555555;
            }
            QListWidget::item:selected {
                background-color: #2e3440;
                border: 1.5px solid #888888;
                color: #ffffff;
                font-weight: bold;
            }
            QComboBox {
                background-color: #222222;
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 5px 15px;
            }
            QComboBox:hover {
                border-color: #666666;
            }
            QComboBox::drop-down {
                border: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #1c1c1c;
                border: 1px solid #555555;
                selection-background-color: #333333;
                selection-color: #ffffff;
                color: #ffffff;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        top_bar_frame = QFrame()
        top_bar_frame.setObjectName("topBar")
        top_bar_frame.setFixedHeight(44)

        top_bar_layout = QHBoxLayout(top_bar_frame)
        top_bar_layout.setContentsMargins(6, 0, 6, 0)
        top_bar_layout.setSpacing(6)

        self.btn_back = QPushButton("Geri")
        self.btn_forward = QPushButton("İleri")
        self.btn_up = QPushButton("Üst Dizin")
        self.btn_home = QPushButton("Ana Klasör")
        self.btn_preview = QPushButton("/")
        self.btn_refresh = QPushButton("Yenile")

        for btn in (self.btn_back, self.btn_forward, self.btn_up, self.btn_home, self.btn_preview, self.btn_refresh):
            btn.setFixedHeight(32)

        self.btn_bookmark = BookmarkButton(initial_bookmark)
        self.btn_bookmark.setFixedHeight(32)

        self.e_path = QLineEdit(self.current_path)
        self.e_path.setFixedHeight(32)

        self.btn_back.clicked.connect(self._go_back)
        self.btn_forward.clicked.connect(self._go_forward)
        self.btn_up.clicked.connect(self._go_up)
        self.btn_home.clicked.connect(lambda: self._navigate_to(Path.home(), push_history=True))
        self.btn_preview.setFixedSize(30, 30)
        self.btn_preview.clicked.connect(self._toggle_hover_preview)
        self.btn_refresh.clicked.connect(lambda: self._load_directory(self.current_path))
        # e_path returnPressed bağlantısı kaldırıldı; Enter tuşu keyPressEvent ile yönetilecek.

        self.btn_bookmark.navigateRequested.connect(lambda path: self._navigate_to(path, push_history=True))
        self.btn_bookmark.bindRequested.connect(self._bind_current_location_to_bookmark)

        top_bar_layout.addWidget(self.btn_back)
        top_bar_layout.addWidget(self.btn_forward)
        top_bar_layout.addWidget(self.btn_up)
        top_bar_layout.addWidget(self.btn_home)
        top_bar_layout.addWidget(self.btn_bookmark)
        top_bar_layout.addWidget(self.e_path, 1)
        top_bar_layout.addWidget(self.btn_preview)
        top_bar_layout.addWidget(self.btn_refresh)

        main_layout.addWidget(top_bar_frame)

        self.file_list = HoverListWidget()
        self.file_list.setViewMode(QListView.IconMode)
        self.file_list.setIconSize(QSize(96, 96))
        self.file_list.setGridSize(QSize(150, 136))
        self.file_list.setSpacing(8)
        self.file_list.setResizeMode(QListView.Adjust)
        self.file_list.setWordWrap(True)
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.file_list.installEventFilter(self)

        self.file_list.itemHovered.connect(self._on_item_hovered)
        self.file_list.mouseLeft.connect(self.hover_card.hide_preview)
        self.file_list.itemDoubleClicked.connect(self._on_item_double_clicked)

        main_layout.addWidget(self.file_list, 1)

        bottom_bar_frame = QFrame()
        bottom_bar_frame.setObjectName("bottomBar")
        bottom_bar_frame.setFixedHeight(44)

        bottom_layout = QHBoxLayout(bottom_bar_frame)
        bottom_layout.setContentsMargins(10, 0, 10, 0)
        bottom_layout.setSpacing(10)

        self.lbl_status = QLabel("Öğeler yükleniyor...")
        self.lbl_status.setStyleSheet("color:#f0f0f0; font-size:11pt; font-weight:bold;")

        lbl_filter_title = QLabel("Filtre:")
        lbl_filter_title.setStyleSheet("color:#e2e8f0; font-weight:bold; font-size:11pt;")

        self.cmb_filter = QComboBox()
        self.cmb_filter.setFixedHeight(32)
        self.cmb_filter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        if self.mode == "export":
            # Export modunda sadece .txr veya belirtilen uzantılar
            if self.context_filter_extensions:
                label = "Kaydedilecek Dosya"
                self.cmb_filter.addItem(label, self.context_filter_extensions)
            else:
                self.cmb_filter.addItem("Kitap Dosyası (.kitap)", {".kitap"})
            self.cmb_filter.setCurrentIndex(0)
        else:
            for label, filter_data in FILTER_CATEGORIES:
                self.cmb_filter.addItem(label, filter_data)

        self.cmb_filter.currentIndexChanged.connect(self._on_filter_changed)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Dosya ara...")
        self.search_edit.setFixedHeight(32)
        self.search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        # Enter tuşu keyPressEvent ile yönetilecek.

        self.btn_ok = QPushButton("OK")
        self.btn_ok.setFixedSize(100, 32)
        self.btn_ok.clicked.connect(self._on_ok_clicked)

        bottom_layout.addWidget(self.lbl_status)
        bottom_layout.addWidget(lbl_filter_title)
        bottom_layout.addWidget(self.cmb_filter, 1)
        bottom_layout.addWidget(self.search_edit, 1)
        bottom_layout.addWidget(self.btn_ok)

        main_layout.addWidget(bottom_bar_frame)


    def set_editor_context(self, editor_name=None, custom_editors=None, filter_extensions=None):
        """
        File Manager'ı belirli bir editörün varsayılan dosya biçimleriyle
        senkronize eder. Kullanıcının filtreyi sonradan değiştirmesine engel olmaz.
        """
        self.target_editor = editor_name
        self.custom_editors = custom_editors or self.custom_editors or []
        self.integration_mode = editor_name is not None
        if filter_extensions is None:
            filter_extensions = get_editor_default_extensions(
                editor_name, self.custom_editors
            )
        self.context_filter_extensions = filter_extensions

        if not hasattr(self, "cmb_filter") or self.mode == "export":
            return

        # Editör bağlamında ilk seçenek editörün kendi formatları,
        # ikinci seçenek her zaman tüm dosyalardır.
        if editor_name:
            self.cmb_filter.blockSignals(True)
            self.cmb_filter.clear()

            # Sphere için tam olarak üç filtre:
            # 1) Sphere Dosyaları
            # 2) Tüm Dosyalar
            # 3) .kitap Dosyaları
            if editor_name == "Sphere":
                sphere_filter = EDITOR_DEFAULT_EXTENSIONS["Sphere"]
                self.cmb_filter.addItem("Sphere Dosyaları", sphere_filter)
                self.cmb_filter.addItem("Tüm Dosyalar (*)", None)
                self.cmb_filter.addItem(".kitap Dosyaları", {".kitap"})
                self.cmb_filter.setCurrentIndex(0)
                self.selected_filter = sphere_filter
            elif editor_name == "Drawing":
                # Drawing'in gerçek/ana formatı .pnf ayrı ve ilk varsayılan filtre.
                # Diğer desteklenen Drawing formatları ikinci seçenek olarak kalır.
                drawing_exts = set(filter_extensions or EDITOR_DEFAULT_EXTENSIONS["Drawing"])
                drawing_primary = {".pnf"}
                drawing_other = drawing_exts - drawing_primary
                self.cmb_filter.addItem("Drawing Ana Dosyaları (.pnf)", drawing_primary)
                self.cmb_filter.addItem("Drawing Diğer Dosyaları", drawing_other)
                self.cmb_filter.addItem("Tüm Dosyalar (*)", None)
                self.cmb_filter.setCurrentIndex(0)
                self.selected_filter = drawing_primary
            else:
                context_label = f"{editor_name} - Varsayılan Dosyalar"
                self.cmb_filter.addItem(context_label, filter_extensions)
                self.cmb_filter.addItem("Tüm Dosyalar (*)", None)
                self.cmb_filter.setCurrentIndex(0)
                self.selected_filter = filter_extensions

            self.cmb_filter.blockSignals(False)
            self._load_directory(self.current_path)
        else:
            # Merkez File Manager normal kullanımına dönüldüğünde
            # varsayılan filtreler tekrar yüklenir.
            self.cmb_filter.blockSignals(True)
            self.cmb_filter.clear()
            for label, filter_data in FILTER_CATEGORIES:
                self.cmb_filter.addItem(label, filter_data)
            self.cmb_filter.setCurrentIndex(0)
            self.cmb_filter.blockSignals(False)
            self.selected_filter = self.cmb_filter.itemData(0)
            self._load_directory(self.current_path)

    def select_file_path(self, file_path):
        """Dışarıdan seçilen dosyayı mevcut File Manager görünümüne ve bağlama aktarır."""
        if not file_path or not os.path.isfile(file_path):
            return False

        full_path = os.path.abspath(file_path)

        if self.selected_filter is not None:
            ext = Path(full_path).suffix.lower()
            allowed = self.selected_filter
            if allowed == "EXEC":
                if not os.access(full_path, os.X_OK):
                    return False
            elif isinstance(allowed, set) and ext not in allowed:
                return False

        self.file_list.clear()
        ext = Path(full_path).suffix.lower()
        item = QListWidgetItem(
            make_type_icon(ext, False),
            f"{os.path.basename(full_path)}\\n{format_size(os.path.getsize(full_path))}"
        )
        item.setData(Qt.UserRole, (full_path, False))
        item.setTextAlignment(Qt.AlignCenter)
        self.file_list.addItem(item)
        self.file_list.setCurrentItem(item)
        self.lbl_status.setText(f"Seçildi: {full_path}")
        self.fileSelected.emit(full_path)
        return True

    def _bind_current_location_to_bookmark(self):
        new_path = self.current_path
        self.btn_bookmark.set_target_path(new_path)
        self.settings.setValue("bookmark_path", new_path)
        msg = QMessageBox(self)
        apply_kavram_icon(msg)
        msg.setWindowTitle("Pimleme Başarılı")
        msg.setText(f"Konum X butonuna sabitlendi:\n{new_path}")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet(_MESSAGE_BOX_STYLE)
        msg.exec_()

    def _navigate_to(self, path, push_history=True):
        target = os.path.abspath(os.path.expanduser(str(path)))
        if not os.path.isdir(target):
            msg = QMessageBox(self)
            apply_kavram_icon(msg)
            msg.setWindowTitle("Hata")
            msg.setText("Dizin bulunamadı.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setStyleSheet(_MESSAGE_BOX_STYLE)
            msg.exec_()
            return

        if push_history:
            if self.history_index < 0 or self.history[self.history_index] != target:
                self.history = self.history[:self.history_index + 1]
                self.history.append(target)
                self.history_index = len(self.history) - 1

        self._update_history_buttons()
        self._load_directory(target)

    def _go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self._navigate_to(self.history[self.history_index], push_history=False)

    def _go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self._navigate_to(self.history[self.history_index], push_history=False)

    def _go_up(self):
        parent = os.path.dirname(self.current_path)
        if parent and parent != self.current_path:
            self._navigate_to(parent, push_history=True)

    def _update_history_buttons(self):
        self.btn_back.setEnabled(self.history_index > 0)
        self.btn_forward.setEnabled(self.history_index < len(self.history) - 1)

    def _load_directory(self, target):
        self.current_path = target
        self.e_path.setText(target)
        self.file_list.clear()

        # Arama metnini al
        self.search_text = self.search_edit.text().strip().lower() if hasattr(self, 'search_edit') else ""

        rows = []
        if _native_engine:
            count = _native_engine.fetch_directory_items(target.encode("utf-8"), 1 if self.show_hidden else 0, 0)
            item = FileItem()
            for i in range(max(0, count)):
                if _native_engine.get_item_at(i, ctypes.byref(item)):
                    rows.append((item.name.decode("utf-8", errors="replace"),
                                 item.path.decode("utf-8", errors="replace"),
                                 bool(item.is_directory), int(item.size)))
            _native_engine.clear_cache()
        else:
            try:
                with os.scandir(target) as it:
                    for entry in it:
                        rows.append((entry.name, entry.path, entry.is_dir(), entry.stat().st_size if not entry.is_dir() else 0))
            except Exception as e:
                print("Directory scan error:", e)

        displayed_count = 0
        for name, full_path, is_dir, size in rows:
            ext = Path(name).suffix.lower()

            # Filtre kontrolü (kategori ve arama)
            if not is_dir and self.selected_filter:
                if self.selected_filter == "EXEC":
                    if not os.access(full_path, os.X_OK):
                        continue
                elif isinstance(self.selected_filter, set):
                    if ext not in self.selected_filter:
                        continue

            # Arama filtresi (büyük/küçük harf duyarsız)
            if self.search_text and self.search_text not in name.lower():
                continue

            displayed_count += 1
            
            # İçerik önizlemesi (sadece .txr dosyaları için)
            preview_text = ""
            if not is_dir and ext == ".txr":
                try:
                    with open(full_path, "r", encoding="utf-8", errors='replace') as f:
                        first_line = f.readline().strip()
                        if first_line:
                            preview_text = first_line[:80]  # ilk 80 karakter
                            if len(first_line) > 80:
                                preview_text += "..."
                except Exception:
                    pass
            
            # Item metni: ad, boyut, önizleme (varsa)
            if not is_dir:
                if preview_text:
                    display_text = f"{name}\n{format_size(size)}\n{preview_text}"
                else:
                    display_text = f"{name}\n{format_size(size)}"
            else:
                display_text = name
                
            item = QListWidgetItem(make_type_icon(ext, is_dir), display_text)
            item.setData(Qt.UserRole, (full_path, is_dir))
            item.setTextAlignment(Qt.AlignCenter)
            self.file_list.addItem(item)

        self.lbl_status.setText(f"Toplam Öğe: {displayed_count} | Konum: {target}")

    def _on_filter_changed(self, index):
        self.selected_filter = self.cmb_filter.itemData(index)
        self._load_directory(self.current_path)

    def eventFilter(self, obj, event):
        """Dosya listesindeyken klavye girişini alttaki arama alanına aktarır."""
        if obj is self.file_list and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Backspace:
                self.search_edit.setFocus()
                self.search_edit.backspace()
                return True
            text = event.text()
            if text and not event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
                self.search_edit.setFocus()
                self.search_edit.insert(text)
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        """Klavye akışı: Enter tuşu OK işlemini tetikler; e_path odakta ise dizin değiştirir."""
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            fw = QApplication.focusWidget()
            if fw is self.e_path:
                # Eğer odak dizin giriş kutusundaysa, dizine git.
                self._navigate_to(self.e_path.text(), push_history=True)
            else:
                # Diğer tüm durumlarda OK işlemini çalıştır.
                self._on_ok_clicked()
            event.accept()
            return

        # Metin giriş alanı zaten odaktaysa Qt'nin normal davranışını bozma.
        fw = QApplication.focusWidget()
        if fw is not self.search_edit and not isinstance(fw, QLineEdit):
            if event.key() == Qt.Key_Backspace:
                self.search_edit.setFocus()
                self.search_edit.backspace()
                event.accept()
                return
            text = event.text()
            if text and not event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
                self.search_edit.setFocus()
                self.search_edit.insert(text)
                event.accept()
                return
        super().keyPressEvent(event)

    def _on_search_text_changed(self, text):
        """Normal modda aramayı güncelle; export modunda bu alan dosya adıdır."""
        if self.mode != "export":
            self._load_directory(self.current_path)

    def _toggle_hover_preview(self):
        self.preview_enabled = not self.preview_enabled
        self.settings.setValue("hover_preview_enabled", self.preview_enabled)
        if not self.preview_enabled:
            self.hover_card.hide_preview()

    def _on_item_hovered(self, filepath, is_dir, is_video, is_image):
        if not self.preview_enabled:
            return
        self.hover_card.show_preview(filepath, is_dir=is_dir, is_video=is_video, is_image=is_image)

    def _on_ok_clicked(self):
        """Tek OK düğmesi: export'ta adı onaylar, açma modunda seçimi onaylar."""
        if self.mode == "export":
            self._export_files()
        else:
            self._open_selected_files(close_after=True)

    def _validate_open_path(self, full_path):
        if not full_path or not os.path.isfile(full_path):
            return False
        if self.selected_filter is None:
            return True
        ext=Path(full_path).suffix.lower()
        if self.selected_filter == "EXEC":
            return os.access(full_path, os.X_OK)
        if isinstance(self.selected_filter, set):
            return ext in self.selected_filter
        return True

    def _open_selected_files(self, close_after=True):
        items=self.file_list.selectedItems()
        paths=[]
        for item in items:
            data=item.data(Qt.UserRole)
            if not data:
                continue
            full_path,is_dir=data
            if not is_dir and self._validate_open_path(full_path):
                paths.append(os.path.abspath(full_path))
        if not paths:
            msg = QMessageBox(self)
            apply_kavram_icon(msg)
            msg.setWindowTitle("Dosya seçilmedi")
            msg.setText("Açmak için en az bir dosya seçin.")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setStyleSheet(_MESSAGE_BOX_STYLE)
            msg.exec_()
            return []

        # Entegre kullanımda pencere önce kaybolur; sürükle-bırak yolunda ise açık kalır.
        if self.integration_mode:
            if close_after:
                self.hide()
            self.filesSelected.emit(paths)
            for path in paths:
                self.fileSelected.emit(path)
            if close_after:
                self.hide()
            return paths

        # Bağımsız File Manager'da çoklu seçim işletim sistemine açılır.
        for path in paths:
            try:
                if sys.platform.startswith("darwin"):
                    subprocess.call(("open", path))
                elif os.name == "nt":
                    os.startfile(path)
                else:
                    subprocess.call(("xdg-open", path))
            except Exception as exc:
                msg = QMessageBox(self)
                apply_kavram_icon(msg)
                msg.setWindowTitle("Dosya açılamadı")
                msg.setText(f"{os.path.basename(path)}\n{exc}")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.setStyleSheet(_MESSAGE_BOX_STYLE)
                msg.exec_()
        return paths

    def _on_item_double_clicked(self, item):
        full_path, is_dir = item.data(Qt.UserRole)
        if is_dir:
            self._navigate_to(full_path, push_history=True)
            return
        if self.integration_mode:
            self.file_list.setCurrentItem(item)
            self._open_selected_files(close_after=True)
            return
        try:
            self._open_selected_files(close_after=False)
        except Exception:
            msg = QMessageBox(self)
            apply_kavram_icon(msg)
            msg.setWindowTitle("Bilgi")
            msg.setText(f"Dosya açılıyor: {full_path}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setStyleSheet(_MESSAGE_BOX_STYLE)
            msg.exec_()

    # ------------------- EXPORT İŞLEMİ (GÜNCELLENDİ) -------------------
    def _export_files(self):
        """Export işlemi: callback ile dosya kaydetme."""
        if self.mode == "export" and callable(self.export_callback):
            base_name = self.search_edit.text().strip()
            if not base_name:
                self.lbl_status.setText("Dosya adı gerekli.")
                self.search_edit.setFocus()
                return
            # Uzantıyı temizle (kullanıcı girmiş olabilir)
            base_name = os.path.splitext(base_name)[0].strip()
            if not base_name:
                self.lbl_status.setText("Dosya adı gerekli.")
                self.search_edit.setFocus()
                return
            # Hangi uzantı? filter_extensions'dan al veya varsayılan .txr
            ext = ".txr"
            if self.context_filter_extensions and isinstance(self.context_filter_extensions, set):
                for e in self.context_filter_extensions:
                    if e.startswith("."):
                        ext = e
                        break
            save_path = os.path.join(self.current_path, f"{base_name}{ext}")

            self.setEnabled(False)
            try:
                Path(self.current_path).mkdir(parents=True, exist_ok=True)
                result = self.export_callback(save_path, self.export_compression)
                if result is False:
                    if os.path.exists(save_path):
                        try:
                            os.remove(save_path)
                        except OSError:
                            pass
                    self.exportCancelled.emit()
                    return
                final_size = os.path.getsize(save_path) if os.path.exists(save_path) else 0
                self.lbl_status.setText(
                    f"Kaydedildi: {os.path.basename(save_path)} | Boyut: {format_size(final_size)}"
                )
                self.exportCompleted.emit(save_path)
            except Exception as e:
                err = QMessageBox(self)
                apply_kavram_icon(err)
                err.setWindowTitle("Hata")
                err.setText(f"Kaydetme sırasında hata oluştu:\n{e}")
                err.setIcon(QMessageBox.Critical)
                err.setStandardButtons(QMessageBox.Ok)
                err.setStyleSheet(_MESSAGE_BOX_STYLE)
                err.exec_()
            finally:
                self.setEnabled(True)
                self.close()
            return

        # Eğer export_callback yoksa (bağımsız kullanımda) eski akışa düşer.
        # Burada eski .kitap export'u devre dışı bırakıldı.
        QMessageBox.warning(self, "Uyarı", "Export işlemi için callback gerekli.")
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    if APP_ICON.is_file():
        app.setWindowIcon(QIcon(str(APP_ICON)))
    window = FileManager()
    window.show()
    sys.exit(app.exec_())
