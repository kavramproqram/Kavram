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

"""Kavram File Manager.

Kavram'ın TÜM "File" ve "Export" pencereleri artık bu modülü kullanır
(QFileDialog yerine).  Dışarıya açılan basit API:

    get_open_file_name(parent, caption, directory, filter, ..., editor="Text")
    get_open_file_names(...)
    get_save_file_name(...)
    get_existing_directory(...)

İmzalar QFileDialog ile aynıdır (aynı filtre dizgesi biçimi "Ad (*.a *.b);;..." ),
bu sayede çağıran kod neredeyse hiç değişmez.  Her pencerede otomatik olarak
"Bütün Dosyalar (*)" seçeneği bulunur.

Önemli davranışlar
  * Pencerenin DIŞINA tıklayınca (veya odak başka pencereye geçince) kendiliğinden kapanır.
  * Listeden sürükle-bırak yalnızca bu pencereden desteklenir (özel MIME işareti).
  * Çift tıklama: dosya ilgili editörde doğrudan açılır (bkz. FileManager._on_item_double_clicked).
  * X11 ve Wayland: konumlandırma yalnızca X11'de zorlanır, Wayland'de pencere yöneticisine bırakılır.
"""

import os
import re
import sys
import stat
import ctypes
import shutil
import subprocess
import tempfile
import time
import uuid
from collections import OrderedDict
from urllib.parse import quote, unquote
from pathlib import Path
from datetime import datetime

from PyQt5.QtCore import (Qt, QSize, QSettings, pyqtSignal, QMimeData, QUrl, QTimer, QEvent,
                          QPointF, QRectF, QObject, QEventLoop, QRunnable, QThreadPool, QPoint)
from PyQt5.QtGui import (QIcon, QPixmap, QPainter, QColor, QFont, QPen, QCursor, QDrag, QImage,
                         QImageReader, QPainterPath, QLinearGradient, QRadialGradient, QBrush,
                         QKeySequence, QGuiApplication)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QListWidget, QListWidgetItem, QLineEdit, QMessageBox,
    QListView, QComboBox, QSizePolicy, QFileDialog, QDialog, QProgressBar,
    QAbstractItemView, QMenu, QToolTip, QShortcut
)

BASE_DIR = Path(__file__).resolve().parent
KAVRAM_DIR = Path(os.environ.get("KAVRAM_DIR") or BASE_DIR.parent)
ENGINE_C = BASE_DIR / "file_engine.c"
ENGINE_SO = BASE_DIR / "libfile_engine.so"
VIEW_C = BASE_DIR / "view_engine.c"
VIEW_SO = BASE_DIR / "libview_engine.so"

# Kavram ikonu tüm pencerelerde tek kaynaktan kullanılır.  Linux dosya sistemi
# büyük/küçük harfe duyarlıdır: gerçek dosya adı "kavram.png" (küçük harf).
_ICON_CANDIDATES = (
    KAVRAM_DIR / "ikon" / "kavram.png",
    KAVRAM_DIR / "ikon" / "Kavram.png",
    BASE_DIR / "ikon" / "kavram.png",
    BASE_DIR / "ikon" / "Kavram.png",
    Path.home() / "Kavram" / "ikon" / "kavram.png",
    Path.home() / "Kavram" / "ikon" / "Kavram.png",
)
APP_ICON = next((c for c in _ICON_CANDIDATES if c.is_file()), _ICON_CANDIDATES[0])

# Editörlerin dışa aktarma klasörü (kavram/export).
EXPORT_DIR = str(KAVRAM_DIR / "export")

# Yalnızca bu pencereden başlatılan sürüklemeleri tanıyan MIME işareti.
FM_DRAG_MIME = "application/x-kavram-file-manager-drag"

# CoreWindow (kavram.py) kendini buraya kaydeder; çift tıklama / bırakma yönlendirmesi için.
_CORE = None


def register_core(core):
    """CoreWindow bağlantısını kaydeder (kavram.py çağırır)."""
    global _CORE
    _CORE = core


def get_core():
    return _CORE


# --------------------------------------------------------------------------- #
#  Yerel (C) motorlar: tembel yüklenir, import sırasında derleme yapılmaz
# --------------------------------------------------------------------------- #
class FileItem(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char * 1024),
        ("path", ctypes.c_char * 4096),
        ("is_directory", ctypes.c_bool),
        ("is_hidden", ctypes.c_bool),
        ("size", ctypes.c_uint64),
        ("mtime", ctypes.c_int64),
    ]


def _build_shared_lib(src, so):
    """src -> so derler (yalnızca eksik/eskiyse). Başarısızlık sessizce False döner.

    Derleme başarısız olursa kaynağın yanına .failed işareti bırakılır; böylece
    her açılışta boşuna yeniden denenmez.  Geçici dosyaya derlenip atomik taşınır.
    """
    try:
        if not src.exists():
            return so.exists()
        if so.exists() and so.stat().st_mtime_ns >= src.stat().st_mtime_ns:
            return True
        marker = Path(str(so) + ".failed")
        if marker.exists() and marker.stat().st_mtime_ns >= src.stat().st_mtime_ns:
            return False
        cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
        if not cc:
            return False
        tmp = Path(f"{so}.tmp{os.getpid()}")
        res = subprocess.run(
            [cc, "-std=c11", "-O2", "-fPIC", "-shared", str(src), "-o", str(tmp), "-pthread", "-lm"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
        if res.returncode == 0 and tmp.exists():
            os.replace(tmp, so)
            return True
        try:
            marker.touch()
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return False
    except Exception as exc:  # derleme asla uygulamayı düşürmemeli
        print("[File Engine] Derleme notu:", exc)
        return False


_native_state = {"tried": False, "lib": None}


def get_native_engine():
    """Dizin tarama motorunu döndürür; yoksa/yüklenemezse None (Python yedeği kullanılır)."""
    if _native_state["tried"]:
        return _native_state["lib"]
    _native_state["tried"] = True
    try:
        if not _build_shared_lib(ENGINE_C, ENGINE_SO):
            return None
        lib = ctypes.CDLL(str(ENGINE_SO))
        lib.fetch_directory_items.restype = ctypes.c_int
        lib.fetch_directory_items.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        lib.get_item_name.restype = ctypes.c_char_p
        lib.get_item_name.argtypes = [ctypes.c_int]
        lib.get_item_info.restype = ctypes.c_int
        lib.get_item_info.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int),
                                      ctypes.POINTER(ctypes.c_uint64), ctypes.POINTER(ctypes.c_int64)]
        lib.clear_cache.restype = None
        lib.clear_cache.argtypes = []
        _native_state["lib"] = lib
    except Exception as exc:
        print("[File Engine] Yerel motor kullanılamıyor, Python yedeği devrede:", exc)
        _native_state["lib"] = None
    return _native_state["lib"]


_view_state = {"tried": False, "lib": None}


def get_view_engine():
    """view_engine.c (yakınlaştırma/kaydırma matematiği, kare adımı, RGBA tampon havuzu)."""
    if _view_state["tried"]:
        return _view_state["lib"]
    _view_state["tried"] = True
    try:
        if not _build_shared_lib(VIEW_C, VIEW_SO):
            return None
        lib = ctypes.CDLL(str(VIEW_SO))
        lib.kv_frame_step.restype = ctypes.c_int64
        lib.kv_frame_step.argtypes = [ctypes.c_int64, ctypes.c_int64, ctypes.c_int, ctypes.c_int64]
        lib.kv_buffer_acquire.restype = ctypes.c_void_p
        lib.kv_buffer_acquire.argtypes = [ctypes.c_size_t]
        lib.kv_buffer_release.restype = None
        lib.kv_buffer_release.argtypes = [ctypes.c_void_p]
        lib.kv_buffer_pool_trim.restype = None
        _view_state["lib"] = lib
    except Exception as exc:
        print("[View Engine] Kullanılamıyor:", exc)
        _view_state["lib"] = None
    return _view_state["lib"]


_NAT_SPLIT = re.compile(r"(\d+)")


def _natural_key(name):
    """'dosya2' 'dosya10'dan önce gelsin (doğal sıralama), büyük/küçük harf fark etmesin."""
    return [int(t) if t.isdigit() else t for t in _NAT_SPLIT.split(name.casefold())]


def scan_directory(target, show_hidden=False):
    """Klasörü okur -> [(ad, tam_yol, klasör_mü, boyut)], klasörler önce, doğal sıralı.

    Önce C motoru denenir; motor yoksa/hata verirse os.scandir yedeği aynı sonucu üretir.
    Klasöre işaret eden sembolik bağlar klasör sayılır. Erişilemezse OSError fırlatır.
    """
    rows = None
    lib = get_native_engine()
    if lib is not None:
        try:
            count = lib.fetch_directory_items(os.fsencode(target), 1 if show_hidden else 0, 0)
            if count >= 0:
                is_dir = ctypes.c_int()
                size = ctypes.c_uint64()
                mtime = ctypes.c_int64()
                rows = []
                for i in range(count):
                    raw = lib.get_item_name(i)
                    if raw is None or not lib.get_item_info(i, ctypes.byref(is_dir),
                                                            ctypes.byref(size), ctypes.byref(mtime)):
                        continue
                    name = os.fsdecode(raw)
                    rows.append((name, os.path.join(target, name), bool(is_dir.value), int(size.value)))
        except Exception as exc:
            print("[File Engine] Yerel tarama başarısız, Python yedeğine geçildi:", exc)
            rows = None
        finally:
            try:
                lib.clear_cache()
            except Exception:
                pass
    if rows is None:
        rows = []
        with os.scandir(target) as it:
            for entry in it:
                name = entry.name
                if not show_hidden and name.startswith("."):
                    continue
                try:
                    is_dir = entry.is_dir(follow_symlinks=True)
                    size = entry.stat(follow_symlinks=False).st_size if entry.is_file(follow_symlinks=False) else 0
                except OSError:
                    is_dir, size = False, 0
                rows.append((name, entry.path, is_dir, size))
    rows.sort(key=lambda r: (not r[2], _natural_key(r[0])))
    return rows


# --------------------------------------------------------------------------- #
#  Biçim tabloları ve filtre ayrıştırma
# --------------------------------------------------------------------------- #
AUDIO_EXTS = {".sound", ".wav", ".aiff", ".flac", ".ogg", ".mp3", ".m4a", ".aac", ".wma", ".opus"}
VIDEO_EXTS = {".rec", ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff", ".tif"}
RASTER_PREVIEW_EXTS = IMAGE_EXTS          # .pnf/.drawing JSON olduğu için resim gibi önizlenmez
TEXT_FILE_EXTS = {
    ".txt", ".txr", ".text", ".md", ".markdown", ".rst", ".log",
    ".json", ".csv", ".xml", ".html", ".htm", ".py", ".c", ".cpp",
    ".h", ".hpp", ".sh", ".ini", ".cfg", ".conf", ".yaml", ".yml", ".toml"
}
ALL_PDF = {".pdf"}
ALL_MEDIA = AUDIO_EXTS | VIDEO_EXTS | IMAGE_EXTS | ALL_PDF

# Her editörün DOĞRUDAN açabildiği biçimler (sürükle-bırak, çift tıklama ve filtreler için).
EDITOR_FILE_EXTENSIONS = {
    "Sphere": (".kitap", ".kavram"),
    "Text": (".txr", ".txt", ".md", ".log"),
    "Drawing": (".pnf", ".drawing", ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"),
    "Ai": (".ai",),
    "Sound": (".wav", ".sound"),
    "Media": (".media", ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv",
              ".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a"),
    "Rec": (".rec", ".mp4", ".mkv", ".wav"),
    "Copy": (".copya",),
}

# Uzantı -> editör (çift tıklamada hangi editörün açacağı). Sphere'deki eşlemeyle uyumludur.
EXT_TO_EDITOR = {
    ".kitap": "Sphere", ".kavram": "Sphere",
    ".txr": "Text", ".txt": "Text", ".md": "Text", ".log": "Text",
    ".pnf": "Drawing", ".drawing": "Drawing", ".png": "Drawing", ".jpg": "Drawing",
    ".jpeg": "Drawing", ".bmp": "Drawing", ".gif": "Drawing", ".webp": "Drawing",
    ".ai": "Ai",
    ".sound": "Sound", ".wav": "Sound",
    ".media": "Media", ".mp4": "Media", ".avi": "Media", ".mov": "Media", ".mkv": "Media",
    ".webm": "Media", ".flv": "Media", ".mp3": "Media", ".ogg": "Media", ".flac": "Media",
    ".aac": "Media", ".m4a": "Media",
    ".rec": "Rec",
    ".copya": "Copy",
}

# Eski sürümle uyumluluk: set olarak varsayılan uzantılar.
EDITOR_DEFAULT_EXTENSIONS = {name: set(exts) for name, exts in EDITOR_FILE_EXTENSIONS.items()}
EDITOR_DEFAULT_EXTENSIONS["Program"] = "EXEC"
# Sphere (ana ekran) tüm editörlerin açabildiği biçimlerin birleşimini kabul eder: her uzantı,
# EXT_TO_EDITOR tablosundaki editörde açılır.  (Elle yazılmış ayrı bir liste tutulmaz; iki liste
# birbirinden kopup uyumsuzluk çıkarmasın diye türetilir.)
EDITOR_DEFAULT_EXTENSIONS["Sphere"] = {ext for exts in EDITOR_FILE_EXTENSIONS.values() for ext in exts}

ALL_FILES_LABEL = "Bütün Dosyalar (*)"
EXEC_FILTER = "EXEC"


def path_extension(path):
    return os.path.splitext(str(path))[1].lower()


def editor_for_path(path, custom_editors=None):
    """Dosyanın doğrudan açılabileceği editör adı (yoksa None)."""
    ext = path_extension(path)
    if custom_editors:
        for editor in custom_editors:
            exts = editor.get("extensions", []) or []
            if isinstance(exts, str):
                exts = [exts]
            norm = {(e if str(e).startswith(".") else "." + str(e)).lower() for e in exts if e}
            if ext and ext in norm:
                return editor.get("name")
    return EXT_TO_EDITOR.get(ext)


def editor_extensions(editor_name):
    """Editörün doğrudan açabildiği uzantılar (küme); bilinmiyorsa boş küme."""
    return set(EDITOR_FILE_EXTENSIONS.get(editor_name, ()))


def get_editor_default_extensions(editor_name, custom_editors=None):
    """Seçilen editör için varsayılan filtre uzantıları (eski API)."""
    if custom_editors:
        for editor in custom_editors:
            if editor.get("name") == editor_name:
                exts = editor.get("extensions", [])
                if isinstance(exts, str):
                    exts = [exts]
                normalized = {(str(e).lower() if str(e).startswith(".") else "." + str(e).lower())
                              for e in exts if e}
                if normalized:
                    return normalized
    return EDITOR_DEFAULT_EXTENSIONS.get(editor_name)


def parse_qt_filter(filter_str):
    """QFileDialog filtre dizgesini [(etiket, uzantılar)] listesine çevirir.

    uzantılar: tuple (sıralı, küçük harf) | None (Bütün Dosyalar) | "EXEC" (çalıştırılabilir).
    Etiket, QFileDialog'un geri verdiği 'selected filter' ile birebir aynıdır;
    çağıran kod (ör. Drawing) etikete göre dal seçtiği için değiştirilmez.
    """
    out = []
    for chunk in (filter_str or "").split(";;"):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.search(r"\(([^()]*)\)\s*$", chunk)
        patterns = (m.group(1) if m else chunk).split()
        exts, is_all = [], False
        for pat in patterns:
            pat = pat.strip().lower()
            if pat in ("*", "*.*"):
                is_all = True
            elif pat.startswith("*."):
                exts.append(pat[1:])
            elif pat.startswith("."):
                exts.append(pat)
        low = chunk.lower()
        if is_all:
            if low.startswith("executable") or low.startswith("program"):
                out.append((chunk, EXEC_FILTER))
            else:
                out.append((chunk, None))
        elif exts:
            out.append((chunk, tuple(dict.fromkeys(exts))))
    return out


def ensure_all_files_option(filters):
    """Her pencerede 'Bütün Dosyalar' seçeneği bulunsun."""
    result = list(filters)
    if not any(ext is None for _label, ext in result):
        result.append((ALL_FILES_LABEL, None))
    return result


def format_size(size):
    n = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"

_TYPE_ICON_CACHE = {}

# Yalnızca .kitap dışındaki ikonlarda kullanılan görünür gri palet.
# SUN_GOLD / SUN_AMBER değerleri .kitap ikon görünümünü korumak için sabit bırakılır.
ICON_TEXT = QColor("#e2e5e9")
ICON_LIGHT = QColor("#b9bec6")
ICON_MID = QColor("#707782")
ICON_EDGE = QColor("#505762")

def make_type_icon(ext, is_dir):
    """Dark temalı vektör ikonlar üretir; .kitap çizimi mevcut tasarımıyla korunur.

    Metin dosyaları satırlı belge, PDF çizgili/silüetli belge, görseller ise
    çerçeve ve manzara simgesiyle ayrılır. Uzantı alt kenarda okunaklıdır.
    """
    ext = (ext or "").lower()
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

    if is_dir:
        # KLASÖR: koyu gri gövde, belirgin ama sade kenar ve üst sekme.
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#353a41"))
        painter.drawRoundedRect(14, 22, 58, 27, 7, 7)
        grad = QLinearGradient(14, 34, 114, 112)
        grad.setColorAt(0.0, QColor("#31363e"))
        grad.setColorAt(1.0, QColor("#171a1e"))
        painter.setBrush(grad)
        painter.setPen(QPen(ICON_EDGE, 2))
        painter.drawRoundedRect(14, 32, 100, 78, 10, 10)
        painter.setPen(QPen(ICON_LIGHT, 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(29, 45, 58, 45)

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

    elif ext == ".pdf":
        # PDF: belge çizgileri, küçük resim silüeti ve altta açık PDF etiketi.
        painter.setBrush(QColor("#1b1e22"))
        painter.setPen(QPen(ICON_EDGE, 2))
        painter.drawRoundedRect(18, 10, 92, 108, 9, 9)
        fold = QPainterPath()
        fold.moveTo(82, 10)
        fold.lineTo(110, 38)
        fold.lineTo(82, 38)
        fold.closeSubpath()
        painter.setBrush(QColor("#3a4048"))
        painter.setPen(QPen(ICON_EDGE, 1))
        painter.drawPath(fold)
        painter.setPen(QPen(ICON_LIGHT, 2, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(30, 43, 72, 43)
        painter.drawLine(30, 54, 65, 54)
        # Resimimsi küçük silüet
        painter.setBrush(QColor("#454c56"))
        painter.setPen(QPen(ICON_LIGHT, 1.5))
        painter.drawRoundedRect(30, 62, 58, 28, 4, 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#aeb5bf"))
        painter.drawEllipse(70, 66, 8, 8)
        silhouette = QPainterPath()
        silhouette.moveTo(32, 86)
        silhouette.lineTo(45, 73)
        silhouette.lineTo(54, 81)
        silhouette.lineTo(65, 71)
        silhouette.lineTo(86, 86)
        silhouette.closeSubpath()
        painter.setBrush(QColor("#858d98"))
        painter.drawPath(silhouette)
        painter.setPen(QPen(ICON_TEXT))
        painter.setFont(QFont("DejaVu Sans", 12, QFont.Bold))
        painter.drawText(QRectF(20, 94, 88, 20), Qt.AlignCenter, "PDF")

    elif ext in TEXT_FILE_EXTS:
        # TXT/TXR/kod/metin türleri: görünür satırlar ve en altta uzantı.
        painter.setBrush(QColor("#202328"))
        painter.setPen(QPen(ICON_LIGHT, 2))
        painter.drawRoundedRect(17, 10, 94, 108, 9, 9)
        painter.setPen(QPen(ICON_MID, 1.5, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(29, 28, 88, 28)
        painter.setPen(QPen(ICON_TEXT, 2, Qt.SolidLine, Qt.RoundCap))
        for y, x2 in ((41, 94), (52, 98), (63, 87), (74, 97)):
            painter.drawLine(29, y, x2, y)
        label = ext.replace(".", "").upper()[:7] if ext else "TXT"
        painter.setPen(QPen(ICON_TEXT))
        painter.setFont(QFont("DejaVu Sans", 11, QFont.Bold))
        painter.drawText(QRectF(20, 91, 88, 22), Qt.AlignCenter, label)

    elif ext == ".media":
        # Kavram medya zaman çizelgesi/arşivi: üç ayrı gri şerit, genel dosyadan ayırt edilir.
        grad = QLinearGradient(16, 12, 112, 116)
        grad.setColorAt(0.0, QColor("#30353c"))
        grad.setColorAt(1.0, QColor("#141619"))
        painter.setBrush(grad)
        painter.setPen(QPen(ICON_EDGE, 2))
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)
        painter.setPen(QPen(ICON_LIGHT, 1.5))
        for y, x1, x2 in ((30, 28, 100), (47, 28, 100), (64, 28, 100)):
            painter.drawLine(x1, y, x2, y)
        painter.setPen(Qt.NoPen)
        for x, y, w in ((29, 24, 25), (57, 41, 35), (29, 58, 18), (51, 58, 42)):
            painter.setBrush(QColor("#858d98" if y != 41 else "#b9bec6"))
            painter.drawRoundedRect(x, y, w, 12, 3, 3)
        painter.setPen(QPen(ICON_TEXT))
        painter.setFont(QFont("DejaVu Sans", 8, QFont.Bold))
        painter.drawText(QRectF(16, 92, 96, 18), Qt.AlignCenter, "MEDIA")

    elif ext == ".ai":
        # AI proje dosyası: düğüm bağlantılı şema, genel dosya ikonundan ayrı.
        grad = QLinearGradient(16, 12, 112, 116)
        grad.setColorAt(0.0, QColor("#30353c"))
        grad.setColorAt(1.0, QColor("#141619"))
        painter.setBrush(grad)
        painter.setPen(QPen(ICON_EDGE, 2))
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)
        painter.setPen(QPen(ICON_LIGHT, 2, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(39, 37, 63, 54)
        painter.drawLine(88, 37, 63, 54)
        painter.drawLine(63, 54, 42, 72)
        painter.drawLine(63, 54, 87, 72)
        painter.setPen(QPen(ICON_TEXT, 1.5))
        for x, y in ((31, 29), (80, 29), (54, 45), (32, 64), (77, 64)):
            painter.setBrush(QColor("#4a515b"))
            painter.drawEllipse(x, y, 16, 16)
        painter.setPen(QPen(ICON_TEXT))
        painter.setFont(QFont("DejaVu Sans", 10, QFont.Bold))
        painter.drawText(QRectF(16, 91, 96, 20), Qt.AlignCenter, "AI")

    elif ext == ".blend":
        # 3B proje dosyası: nötr gri küp; herhangi bir uygulamanın logosu kullanılmaz.
        grad = QLinearGradient(16, 12, 112, 116)
        grad.setColorAt(0.0, QColor("#30353c"))
        grad.setColorAt(1.0, QColor("#141619"))
        painter.setBrush(grad)
        painter.setPen(QPen(ICON_EDGE, 2))
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)
        cube = QPainterPath()
        cube.moveTo(64, 25)
        cube.lineTo(91, 40)
        cube.lineTo(64, 55)
        cube.lineTo(37, 40)
        cube.closeSubpath()
        painter.setBrush(QColor("#858d98"))
        painter.setPen(QPen(ICON_TEXT, 1.5))
        painter.drawPath(cube)
        painter.setBrush(QColor("#4a515b"))
        left_face = QPainterPath()
        left_face.moveTo(37, 40); left_face.lineTo(64, 55); left_face.lineTo(64, 83); left_face.lineTo(37, 68); left_face.closeSubpath()
        painter.drawPath(left_face)
        painter.setBrush(QColor("#626a75"))
        right_face = QPainterPath()
        right_face.moveTo(64, 55); right_face.lineTo(91, 40); right_face.lineTo(91, 68); right_face.lineTo(64, 83); right_face.closeSubpath()
        painter.drawPath(right_face)
        painter.setPen(QPen(ICON_TEXT))
        painter.setFont(QFont("DejaVu Sans", 9, QFont.Bold))
        painter.drawText(QRectF(16, 91, 96, 18), Qt.AlignCenter, "BLEND")

    elif ext in {".xz", ".tar", ".gz", ".zip", ".7z", ".rar", ".copya"}:
        # Arşiv: koyu metal gövde, gri paket bandı ve uzantı etiketi.
        grad = QLinearGradient(16, 12, 112, 116)
        grad.setColorAt(0.0, QColor("#30353c"))
        grad.setColorAt(1.0, QColor("#171a1e"))
        painter.setBrush(grad)
        painter.setPen(QPen(ICON_EDGE, 2))
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)
        painter.setPen(QPen(ICON_LIGHT, 3, Qt.DashLine, Qt.RoundCap))
        painter.drawLine(64, 20, 64, 80)
        painter.setBrush(QColor("#737b86"))
        painter.setPen(QPen(ICON_TEXT, 1))
        painter.drawRoundedRect(57, 48, 14, 18, 3, 3)
        painter.setPen(QPen(ICON_TEXT))
        painter.setFont(QFont("DejaVu Sans", 9, QFont.Bold))
        painter.drawText(QRectF(16, 90, 96, 20), Qt.AlignCenter, ext.replace(".", "").upper()[:7])

    elif ext in {".pnf", ".drawing"}:
        # Kavram çizim projeleri ham fotoğraflardan farklı bir tuval/kalem simgesi kullanır.
        grad = QLinearGradient(16, 12, 112, 116)
        grad.setColorAt(0.0, QColor("#30353c"))
        grad.setColorAt(1.0, QColor("#141619"))
        painter.setBrush(grad)
        painter.setPen(QPen(ICON_EDGE, 2))
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)
        painter.setBrush(QColor("#1b1e23"))
        painter.setPen(QPen(ICON_LIGHT, 1.5))
        painter.drawRoundedRect(27, 23, 73, 62, 6, 6)
        canvas_mark = QPainterPath()
        canvas_mark.moveTo(34, 73)
        canvas_mark.lineTo(48, 56)
        canvas_mark.lineTo(60, 65)
        canvas_mark.lineTo(75, 42)
        canvas_mark.lineTo(92, 73)
        painter.setPen(QPen(QColor("#aeb5bf"), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(canvas_mark)
        # Kalem
        painter.setPen(QPen(ICON_TEXT, 4, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(80, 29, 94, 17)
        painter.setPen(QPen(ICON_TEXT))
        painter.setFont(QFont("DejaVu Sans", 8, QFont.Bold))
        painter.drawText(QRectF(16, 92, 96, 18), Qt.AlignCenter, ext.replace(".", "").upper()[:7])

    elif ext in IMAGE_EXTS:
        # Görsel türleri: resim çerçevesi + dağ/güneş silüeti; PDF'den ayrı görünür.
        grad = QLinearGradient(16, 12, 112, 116)
        grad.setColorAt(0.0, QColor("#2a2e34"))
        grad.setColorAt(1.0, QColor("#131518"))
        painter.setBrush(grad)
        painter.setPen(QPen(ICON_EDGE, 2))
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)
        painter.setBrush(QColor("#121417"))
        painter.setPen(QPen(ICON_MID, 1.5))
        painter.drawRoundedRect(24, 20, 80, 68, 7, 7)
        painter.setBrush(ICON_TEXT)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(76, 28, 15, 15)
        mountain = QPainterPath()
        mountain.moveTo(25, 81)
        mountain.lineTo(45, 55)
        mountain.lineTo(60, 71)
        mountain.lineTo(78, 49)
        mountain.lineTo(103, 81)
        mountain.closeSubpath()
        painter.setBrush(QColor("#858d98"))
        painter.drawPath(mountain)
        painter.setPen(QPen(ICON_TEXT))
        painter.setFont(QFont("DejaVu Sans", 8, QFont.Bold))
        painter.drawText(QRectF(16, 92, 96, 18), Qt.AlignCenter, ext.replace(".", "").upper()[:7])

    elif ext in AUDIO_EXTS:
        # Ses: farklı yükseklikte, açık gri dalga sütunları.
        grad = QLinearGradient(16, 12, 112, 116)
        grad.setColorAt(0.0, QColor("#30343a"))
        grad.setColorAt(1.0, QColor("#141619"))
        painter.setBrush(grad)
        painter.setPen(QPen(ICON_EDGE, 2))
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)
        painter.setPen(QPen(ICON_LIGHT, 3, Qt.SolidLine, Qt.RoundCap))
        bars = [22, 42, 58, 34, 50, 26]
        for idx, h in enumerate(bars):
            bx = 36 + (idx * 10)
            by = 58 - (h // 2)
            painter.drawLine(bx, by, bx, by + h)
        painter.setPen(QPen(ICON_TEXT))
        painter.setFont(QFont("DejaVu Sans", 9, QFont.Bold))
        painter.drawText(QRectF(16, 92, 96, 18), Qt.AlignCenter, ext.replace(".", "").upper()[:7])

    elif ext in VIDEO_EXTS:
        # Video: belirgin oynat simgesi ve uzantı etiketi.
        grad = QLinearGradient(16, 12, 112, 116)
        grad.setColorAt(0.0, QColor("#30343a"))
        grad.setColorAt(1.0, QColor("#141619"))
        painter.setBrush(grad)
        painter.setPen(QPen(ICON_EDGE, 2))
        painter.drawRoundedRect(16, 12, 96, 104, 12, 12)
        painter.setBrush(QColor("#6e7681"))
        painter.setPen(QPen(ICON_TEXT, 1.5))
        painter.drawRoundedRect(28, 31, 72, 44, 6, 6)
        play_path = QPainterPath()
        play_path.moveTo(56, 41)
        play_path.lineTo(78, 53)
        play_path.lineTo(56, 66)
        play_path.closeSubpath()
        painter.setBrush(ICON_TEXT)
        painter.setPen(Qt.NoPen)
        painter.drawPath(play_path)
        painter.setPen(QPen(ICON_TEXT))
        painter.setFont(QFont("DejaVu Sans", 9, QFont.Bold))
        painter.drawText(QRectF(16, 92, 96, 18), Qt.AlignCenter, ext.replace(".", "").upper()[:7])

    else:
        # Genel dosya: metal gri sayfa, katlanmış köşe ve okunaklı uzantı.
        grad = QLinearGradient(18, 10, 110, 118)
        grad.setColorAt(0.0, QColor("#2d3239"))
        grad.setColorAt(1.0, QColor("#141619"))
        painter.setBrush(grad)
        painter.setPen(QPen(ICON_EDGE, 2))
        painter.drawRoundedRect(18, 10, 92, 108, 10, 10)
        fold = QPainterPath()
        fold.moveTo(82, 10)
        fold.lineTo(110, 38)
        fold.lineTo(82, 38)
        fold.closeSubpath()
        painter.setBrush(QColor("#444b55"))
        painter.setPen(QPen(ICON_EDGE, 1))
        painter.drawPath(fold)
        label_text = ext.replace(".", "").upper()[:7] if ext else "DOSYA"
        painter.setPen(QPen(ICON_TEXT))
        painter.setFont(QFont("DejaVu Sans", 10, QFont.Bold))
        painter.drawText(QRectF(18, 52, 92, 36), Qt.AlignCenter | Qt.TextWordWrap, label_text)

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
        # Üst çubuk sabit ölçülü: uzun yer imi adı düğmeyi büyütmez.
        self.setFixedWidth(90)

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



# --------------------------------------------------------------------------- #
#  Önizleme: arka plan iş parçacığında küçük resim üretimi (arayüzü dondurmaz)
# --------------------------------------------------------------------------- #
class _ThumbSignals(QObject):
    done = pyqtSignal(int, str, QImage)


def _ffmpeg_thumb(path):
    exe = shutil.which("ffmpeg")
    if not exe:
        return QImage()
    for seek in ("2", "0"):          # 2 sn'den kısa videolar için 0. saniyeye düş
        try:
            res = subprocess.run(
                [exe, "-v", "error", "-ss", seek, "-i", path, "-frames:v", "1",
                 "-vf", "scale=260:170:force_original_aspect_ratio=decrease",
                 "-f", "image2pipe", "-vcodec", "png", "-"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=6)
            if res.returncode == 0 and res.stdout:
                img = QImage.fromData(res.stdout)
                if not img.isNull():
                    return img
        except Exception:
            pass
    return QImage()


class _ThumbJob(QRunnable):
    def __init__(self, token, path, kind, signals):
        super().__init__()
        self.token, self.path, self.kind, self.signals = token, path, kind, signals

    def run(self):
        img = QImage()
        try:
            if self.kind == "image":
                reader = QImageReader(self.path)
                reader.setAutoTransform(True)
                size = reader.size()
                if size.isValid() and (size.width() > 260 or size.height() > 170):
                    size.scale(260, 170, Qt.KeepAspectRatio)
                    reader.setScaledSize(size)
                img = reader.read()
            elif self.kind == "video":
                img = _ffmpeg_thumb(self.path)
        except Exception:
            img = QImage()
        try:
            self.signals.done.emit(self.token, self.path, img)
        except RuntimeError:
            pass


class HoverPreviewCard(QWidget):
    _CACHE_MAX = 48

    def __init__(self, parent=None):
        super().__init__(parent, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet("""
            QFrame#card { background-color: #141414; border: 1.5px solid #475569; border-radius: 10px; }
            QLabel { color: #f0f0f0; font-size: 12px; font-weight: 400; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.card_frame = QFrame()
        self.card_frame.setObjectName("card")
        frame_layout = QVBoxLayout(self.card_frame)
        frame_layout.setContentsMargins(6, 6, 6, 6)
        frame_layout.setSpacing(0)

        self.img_label = QLabel("")
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setFixedSize(260, 170)
        self.img_label.setStyleSheet("background-color: #0a0a0a; border-radius: 6px; color: #e2e8f0; font-size: 13px;")
        self.filename_label = QLabel("")
        self.filename_label.setAlignment(Qt.AlignCenter)
        self.filename_label.setWordWrap(True)
        self.filename_label.setFixedWidth(260)
        self.filename_label.setMaximumHeight(38)
        self.filename_label.setStyleSheet("background: transparent; color: #e2e5e9; font-size: 13px; "
                                          "font-weight: 500; padding: 3px 2px 1px 2px;")
        self.info_label = QLabel("")      # eski sürümle uyumluluk
        self.info_label.hide()
        frame_layout.addWidget(self.img_label)
        frame_layout.addWidget(self.filename_label)
        layout.addWidget(self.card_frame)

        self._cache = OrderedDict()       # (yol, mtime_ns) -> QImage
        self._token = 0
        self._current_key = None
        self._signals = _ThumbSignals()
        self._signals.done.connect(self._on_thumb_done)
        self.hide()

    def _set_icon_fallback(self, ext, is_dir):
        pix = make_type_icon(ext, is_dir).pixmap(140, 140)
        self.img_label.setPixmap(pix.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _set_image(self, img):
        pix = QPixmap.fromImage(img)
        self.img_label.setPixmap(pix.scaled(260, 170, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _on_thumb_done(self, token, path, img):
        if token != self._token or not self.isVisible():
            return
        if img.isNull():
            self._set_icon_fallback(path_extension(path), False)
            return
        if self._current_key is not None:
            self._cache[self._current_key] = img
            while len(self._cache) > self._CACHE_MAX:
                self._cache.popitem(last=False)
        self._set_image(img)

    def show_preview(self, filepath, is_dir=False, is_video=False, is_image=False):
        self._token += 1
        self.filename_label.setText(os.path.basename(filepath.rstrip(os.sep)) or filepath)
        ext = "" if is_dir else path_extension(filepath)
        self.img_label.clear()
        self._current_key = None
        kind = "video" if is_video else ("image" if is_image and ext in RASTER_PREVIEW_EXTS else None)
        if kind:
            try:
                key = (filepath, os.stat(filepath).st_mtime_ns)
            except OSError:
                key = None
            if key and key in self._cache:
                self._cache.move_to_end(key)
                self._set_image(self._cache[key])
            else:
                self._current_key = key
                self._set_icon_fallback(ext, False)
                QThreadPool.globalInstance().start(_ThumbJob(self._token, filepath, kind, self._signals))
        else:
            self._set_icon_fallback(ext, is_dir)

        self.adjustSize()
        cur = QCursor.pos()
        screen = QGuiApplication.screenAt(cur) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        w, h = self.width(), self.height()
        x, y = cur.x() + 18, cur.y() + 18
        if x + w > area.right():
            x = cur.x() - w - 12
        if y + h > area.bottom():
            y = area.bottom() - h
        self.move(max(area.left(), min(x, area.right() - w)), max(area.top(), min(y, area.bottom() - h)))
        self.show()
        self.raise_()

    def hide_preview(self):
        self._token += 1                   # bekleyen küçük resim sonuçlarını yok say
        self.hide()


class HoverListWidget(QListWidget):
    itemHovered = pyqtSignal(str, bool, bool, bool)   # yol, klasör, video, resim
    mouseLeft = pyqtSignal()
    dragStarted = pyqtSignal()
    dragFinished = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragOnly)
        self.setDefaultDropAction(Qt.CopyAction)
        self._last_hovered_path = None
        self._hover_timer = QTimer(self)          # hızlı fare geçişlerinde önizleme işi yapma
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(140)
        self._hover_timer.timeout.connect(self._emit_pending_hover)
        self._pending = None
        self.last_drag_paths = []

    def _emit_pending_hover(self):
        if self._pending:
            self.itemHovered.emit(*self._pending)

    def startDrag(self, supported_actions):
        """Seçili GERÇEK dosyaları file:// URL'leriyle ve Kavram işaretiyle sürükler (klasör hariç)."""
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
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
        mime.setData(FM_DRAG_MIME, b"1")
        if path_extension(paths[0]) in IMAGE_EXTS | {".pnf"}:
            mime.setData("application/x-kavram-image-drag", b"1")
        self._hover_timer.stop()
        self.mouseLeft.emit()
        self.last_drag_paths = list(paths)
        print(f"[File] Sürükleme başladı: {len(paths)} dosya")
        drag = QDrag(self)
        drag.setMimeData(mime)
        cur = self.currentItem()
        if cur is not None:
            drag.setPixmap(cur.icon().pixmap(QSize(64, 64)))
        self.dragStarted.emit()
        result = Qt.IgnoreAction
        try:
            result = drag.exec_(Qt.CopyAction)
        finally:
            self.dragFinished.emit(int(result))

    def mouseMoveEvent(self, event):
        item = self.itemAt(event.pos())
        data = item.data(Qt.UserRole) if item else None
        if data:
            full_path, is_dir = data
            if full_path != self._last_hovered_path:
                self._last_hovered_path = full_path
                ext = path_extension(full_path)
                self._pending = (full_path, is_dir, (not is_dir and ext in VIDEO_EXTS),
                                 (not is_dir and ext in IMAGE_EXTS))
                self._hover_timer.start()
        elif self._last_hovered_path is not None:
            self._last_hovered_path = None
            self._hover_timer.stop()
            self.mouseLeft.emit()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self._last_hovered_path = None
        self._hover_timer.stop()
        self.mouseLeft.emit()
        super().leaveEvent(event)


# --------------------------------------------------------------------------- #
#  Pencerenin dışına tıklayınca kapanma  (File penceresi + diğer açılır pencereler)
# --------------------------------------------------------------------------- #
def _is_inside(widget, root):
    """widget, root'un kendisi veya (menü/diyalog dahil) alt öğesi mi?"""
    w = widget
    while w is not None:
        if w is root:
            return True
        w = w.parentWidget()
    return False


class OutsideClickCloser(QObject):
    """Pencere görünürken dışına tıklanırsa ya da odak başka pencereye geçerse pencereyi kapatır.

    Uygulama düzeyi filtre YALNIZCA pencere açıkken takılır (boşta maliyet yok).
    X11'de tıklama doğrudan yakalanır; Wayland'de başka uygulamaya tıklama olay olarak
    görünmediğinden ek olarak odak kaybı (WindowDeactivate) izlenir.
    """

    def __init__(self, widget):
        super().__init__(widget)
        self.w = widget
        self._armed = False
        self._suspended = False
        self._armed_at = 0.0
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self._check_focus)

    def arm(self):
        if self._armed:
            return
        self._armed = True
        self._armed_at = time.monotonic()
        QApplication.instance().installEventFilter(self)

    def disarm(self):
        if not self._armed:
            return
        self._armed = False
        self._timer.stop()
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)

    def suspend(self):
        self._suspended = True

    def resume(self):
        self._suspended = False

    def _check_focus(self):
        if self._suspended or not self._armed or not self.w.isVisible():
            return
        if QApplication.activePopupWidget() is not None or QApplication.activeModalWidget() is not None:
            return
        active = QApplication.activeWindow()
        if active is not None and _is_inside(active, self.w):
            return
        self.w.close()

    def eventFilter(self, obj, event):
        if not self._armed or self._suspended:
            return False
        t = event.type()
        if t == QEvent.MouseButtonPress:
            if time.monotonic() - self._armed_at < 0.2 or not self.w.isVisible():
                return False
            if isinstance(obj, QWidget) and not _is_inside(obj, self.w):
                QTimer.singleShot(0, self.w.close)
        elif t == QEvent.WindowDeactivate and obj is self.w:
            self._timer.start()
        return False


# --------------------------------------------------------------------------- #
#  Sürükle-bırak yönlendirici: yalnızca bu pencereden başlayan sürüklemelerde, sürükleme
#  süresince takılır.  Bırakma hedefi editörler/Sphere'dir; çekirdek (CoreWindow) karar verir.
# --------------------------------------------------------------------------- #
class _FMDragRouter(QObject):
    def __init__(self, fm):
        super().__init__(fm)
        self.fm = fm
        self.enter_seen = False        # Qt, sürüklemeyi FM dışındaki bir pencereye ulaştırdı mı?
        self.drop_seen = False

    def eventFilter(self, obj, event):
        t = event.type()
        if t not in (QEvent.DragEnter, QEvent.DragMove, QEvent.Drop) or not isinstance(obj, QWidget):
            return False
        mime = event.mimeData()
        if mime is None or not mime.hasFormat(FM_DRAG_MIME):
            return False
        core = _CORE
        paths = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
        if core is None or not paths or _is_inside(obj, self.fm):
            event.ignore()
            return True
        if t == QEvent.DragEnter:
            self.enter_seen = True
        try:
            gpos = obj.mapToGlobal(event.pos())
            ok = bool(core.fm_accepts_drop(paths, obj))
        except Exception as exc:
            print("[File] Bırakma denetimi hatası:", exc)
            ok, gpos = False, QPoint()
        if not ok:
            if t == QEvent.DragEnter:
                print(f"[File] Bırakma hedefi dosyaları kabul etmiyor: {type(obj).__name__}")
            event.ignore()
            return True
        event.setDropAction(Qt.CopyAction)
        event.accept()
        if t == QEvent.Drop:
            self.drop_seen = True
            print(f"[File] Bırakıldı: {len(paths)} dosya -> {type(obj).__name__}")
            # Bırakma, sürükleme döngüsünün İÇİNDE gelir; hedef pencere yeniden kurulabileceği
            # için asıl iş olay döngüsüne döndükten sonra yapılır.
            QTimer.singleShot(0, lambda p=list(paths), o=obj, g=gpos: _deliver_drop(p, o, g))
        return True


def _deliver_drop(paths, target, gpos):
    try:
        if _CORE is not None:
            _CORE.fm_handle_drop(paths, target, gpos)
    except Exception as exc:
        print("[File] Bırakma işlenemedi:", exc)

class HoverFilenameOverlay(QWidget):
    """İmleç üzerindeki kartın sol-alt kenarından başlayıp üste dönen ad etiketi."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filename = ""
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.hide()

    def show_for_item(self, filename, rect):
        self.filename = str(filename or "")
        self.setGeometry(rect.adjusted(1, 1, -1, -1))
        self.show()
        self.raise_()
        self.update()

    def paintEvent(self, event):
        if not self.filename:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds = self.rect().adjusted(1, 1, -1, -1)
        painter.setBrush(QColor(8, 9, 11, 36))
        painter.setPen(QPen(QColor("#aeb5bf"), 1.6))
        painter.drawRoundedRect(bounds, 8, 8)

        font = QFont("DejaVu Sans", 8, QFont.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()
        char_h = max(11, fm.height())
        # İlk birkaç harf sol kenarda alttan yukarı; kalan isim üst kenarda yatay akar.
        vertical_capacity = max(3, min(10, (self.height() - 14) // char_h))
        vertical_count = min(len(self.filename), vertical_capacity)
        x = 5
        for i in range(vertical_count):
            y = self.height() - 7 - i * char_h
            glyph = self.filename[i]
            glyph_rect = QRectF(x, y - fm.ascent(), max(15, fm.horizontalAdvance(glyph) + 6), fm.height())
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(10, 11, 13, 220))
            painter.drawRoundedRect(glyph_rect.adjusted(-2, -1, 2, 1), 3, 3)
            painter.setPen(QPen(QColor("#f1f3f6")))
            painter.drawText(glyph_rect, Qt.AlignLeft | Qt.AlignVCenter, glyph)

        remainder = self.filename[vertical_count:]
        if remainder:
            left = 24
            top_y = max(fm.ascent() + 5, 13)
            max_width = max(10, self.width() - left - 18)
            shown = fm.elidedText(remainder, Qt.ElideRight, max_width)
            text_rect = QRectF(left, 3, max_width + 2, fm.height() + 3)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(10, 11, 13, 224))
            painter.drawRoundedRect(text_rect, 3, 3)
            painter.setPen(QPen(QColor("#f1f3f6")))
            painter.drawText(QRectF(left + 3, top_y - fm.ascent(), max_width - 4, fm.height()),
                            Qt.AlignLeft | Qt.AlignVCenter, shown)
            if shown != remainder:
                # İstenen üç dikey nokta: yatay elips yerine ⋮ kullanılır.
                painter.setPen(QPen(QColor("#f1f3f6")))
                painter.setFont(QFont("DejaVu Sans", 12, QFont.Bold))
                painter.drawText(QRectF(self.width() - 18, 3, 16, fm.height() + 4),
                                Qt.AlignCenter, "⋮")
        painter.end()

def apply_kavram_icon(widget):
    """Pencere/dialog başlık çubuğunda daima Kavram ikonunu kullan."""
    try:
        if APP_ICON.is_file():
            widget.setWindowIcon(QIcon(str(APP_ICON)))
    except Exception:
        pass


APP_TRASH_ROOT = Path.home() / ".local" / "share" / "Kavram" / "Trash"
APP_TRASH_FILES = APP_TRASH_ROOT / "files"
APP_TRASH_INFO = APP_TRASH_ROOT / "info"
TRASH_RETENTION_DAYS = 10


def _trash_info_path_for(file_path):
    """Kavram'ın özel çöp kutusundaki dosya için yan metadata yolunu döndürür."""
    return APP_TRASH_INFO / (Path(file_path).name + ".trashinfo")


def _read_trash_info(info_path):
    try:
        values = {}
        for line in Path(info_path).read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line and not line.startswith("["):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
        deleted_at = datetime.fromisoformat(values["DeletionDate"])
        original_path = unquote(values.get("Path", ""))
        return deleted_at, original_path
    except (OSError, ValueError, KeyError, TypeError):
        return None, ""


def purge_expired_app_trash(now=None):
    """Yalnızca metadata'sı okunabilen Kavram çöp öğelerini 10 gün sonra siler."""
    now = now or datetime.now()
    try:
        APP_TRASH_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
        APP_TRASH_FILES.mkdir(parents=True, exist_ok=True, mode=0o700)
        APP_TRASH_INFO.mkdir(parents=True, exist_ok=True, mode=0o700)
        for private_dir in (APP_TRASH_ROOT, APP_TRASH_FILES, APP_TRASH_INFO):
            try:
                os.chmod(private_dir, 0o700)
            except OSError:
                pass
    except OSError:
        return 0

    removed = 0
    cutoff_seconds = TRASH_RETENTION_DAYS * 24 * 60 * 60
    for info_path in APP_TRASH_INFO.glob("*.trashinfo"):
        deleted_at, _original_path = _read_trash_info(info_path)
        if deleted_at is None:
            # Bozuk metadata varsa kullanıcı verisini otomatik silme.
            continue
        age = (now - deleted_at).total_seconds()
        item_path = APP_TRASH_FILES / info_path.name[:-len(".trashinfo")]
        if age < cutoff_seconds:
            if not item_path.exists() and not item_path.is_symlink():
                try:
                    info_path.unlink()
                except OSError:
                    pass
            continue
        try:
            if item_path.is_symlink() or item_path.is_file():
                item_path.unlink()
            elif item_path.is_dir():
                shutil.rmtree(item_path)
            if not item_path.exists() and not item_path.is_symlink():
                info_path.unlink(missing_ok=True)
                removed += 1
        except OSError as exc:
            print(f"[Kavram Trash] Süresi dolan öğe silinemedi: {item_path}: {exc}")
    return removed


class DelayedToolTip(QObject):
    """Bir düğmenin ipucunu fare 2 saniye üzerinde kalınca gösterir."""
    def __init__(self, widget, text, delay_ms=2000):
        super().__init__(widget)
        self.widget = widget
        self.text = text
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(delay_ms)
        self.timer.timeout.connect(self._show)
        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.widget:
            if event.type() == QEvent.Enter:
                self.timer.start()
            elif event.type() in (QEvent.Leave, QEvent.MouseButtonPress, QEvent.Hide, QEvent.EnabledChange):
                self.timer.stop()
                QToolTip.hideText()
        return False

    def _show(self):
        if self.widget.isVisible() and self.widget.isEnabled() and self.widget.underMouse():
            QToolTip.showText(QCursor.pos(), self.text, self.widget, self.widget.rect(), 6000)


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
        self._cancel_tooltip = DelayedToolTip(
            self.button,
            "İşlem sürüyorsa iptal isteği gönderir; işlem tamamlanınca pencereyi kapatır.",
            2000
        )
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





_trash_purged = {"done": False}


def _purge_trash_once():
    if _trash_purged["done"]:
        return
    _trash_purged["done"] = True
    try:
        purge_expired_app_trash()
    except Exception as exc:
        print("[File] Çöp temizliği atlandı:", exc)


def _styled_box(parent, title, text, icon=QMessageBox.Information, buttons=QMessageBox.Ok,
                default=QMessageBox.NoButton):
    box = QMessageBox(parent)
    apply_kavram_icon(box)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    if default != QMessageBox.NoButton:
        box.setDefaultButton(default)
    box.setStyleSheet(_MESSAGE_BOX_STYLE)
    return box.exec_()


_FM_STYLE = """
    QWidget { background-color: #121212; color: #f0f0f0; font-family: 'Segoe UI', sans-serif; font-size: 11pt; }
    QFrame#topBar { background-color: #222222; border-bottom: 2px solid #555555; min-height: 40px; max-height: 40px; }
    QFrame#topBar QPushButton { padding: 5px 10px; }
    QFrame#bottomBar { background-color: #1a1a1a; border-bottom: 1px solid #333333; min-height: 40px; max-height: 40px; }
    QToolTip { color: #f6f7f9; background-color: #24282e; border: 1px solid #7d858f; padding: 5px 8px; }
    QPushButton { background-color: transparent; color: white; font-size: 14px; font-weight: bold;
                  border: 2px solid #555; border-radius: 8px; padding: 5px; }
    QPushButton:hover { background-color: #444; }
    QPushButton:pressed { background-color: #666; }
    QPushButton:disabled { background-color: transparent; color: #9299a3; border-color: #444; }
    QLineEdit { background-color: #0a0a0a; color: #ffffff; border: 1px solid #444444; border-radius: 6px;
                padding: 6px 10px; font-size: 11pt; }
    QLineEdit:focus { border: 1px solid #888888; }
    QListWidget { background-color: #0c0c0c; border: 1px solid #333333; border-radius: 8px; padding: 8px; font-size: 10pt; }
    QListWidget::item { padding: 4px; margin: 2px; border-radius: 7px; background-color: #181818; color: #f0f0f0; }
    QListWidget::item:hover { background-color: #282828; border: 1px solid #555555; }
    QListWidget::item:selected { background-color: #2e3440; border: 1.5px solid #888888; color: #ffffff; font-weight: bold; }
    QComboBox { background-color: #222222; color: #ffffff; font-size: 13px; font-weight: bold;
                border: 1px solid #444444; border-radius: 8px; padding: 5px 15px; }
    QComboBox:hover { border-color: #666666; }
    QComboBox::drop-down { border: 0px; }
    QComboBox QAbstractItemView { background-color: #1c1c1c; border: 1px solid #555555;
                selection-background-color: #333333; selection-color: #ffffff; color: #ffffff; }
"""

_MENU_STYLE = """
    QMenu { background:#202328; color:#f0f2f5; border:1px solid #606771; padding:5px; }
    QMenu::item { padding:7px 24px 7px 12px; border-radius:4px; }
    QMenu::item:selected { background:#3c424a; color:#ffffff; }
    QMenu::separator { height:1px; background:#505762; margin:5px 7px; }
"""


class FileManager(QWidget):
    """Kavram dosya penceresi: 'open' (aç), 'export' (kaydet) ve 'folder' (klasör seç) kipleri."""

    _instance = None

    fileSelected = pyqtSignal(str)
    filesSelected = pyqtSignal(list)
    exportCompleted = pyqtSignal(str)
    exportCancelled = pyqtSignal()
    closed = pyqtSignal()

    @classmethod
    def live_instance(cls):
        inst = cls._instance
        if inst is None:
            return None
        try:
            return inst if inst.isVisible() else None
        except RuntimeError:        # C++ nesnesi silinmiş
            cls._instance = None
            return None

    @classmethod
    def open_singleton(cls, parent=None, target_editor=None, custom_editors=None,
                       filter_extensions=None, mode="open", export_callback=None,
                       export_compression="xz", default_export_name=None, **kwargs):
        """Tek örnek: zaten açıksa yenisini açmaz, mevcut pencereyi öne getirir."""
        inst = cls.live_instance()
        if inst is not None:
            inst.raise_()
            inst.activateWindow()
            return inst
        inst = cls(parent=parent, target_editor=target_editor, custom_editors=custom_editors,
                   filter_extensions=filter_extensions, mode=mode, export_callback=export_callback,
                   export_compression=export_compression, default_export_name=default_export_name, **kwargs)
        inst.show_centered()
        return inst

    def __init__(self, parent=None, target_editor=None, custom_editors=None, filter_extensions=None,
                 mode="open", export_callback=None, export_compression="xz", default_export_name=None,
                 *, filters=None, start_dir=None, title=None, multiple=False,
                 double_click="route", initial_filter="", default_name=""):
        super().__init__(parent, Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        FileManager._instance = self
        apply_kavram_icon(self)
        self.settings = QSettings("Kavram", "KavramFileManager")
        self.preview_enabled = self.settings.value("hover_preview_enabled", True, type=bool)

        self.mode = mode if mode in ("open", "export", "folder") else "open"
        self.target_editor = target_editor
        self.custom_editors = custom_editors or []
        self.export_callback = export_callback
        self.export_compression = export_compression if export_compression in ("xz", "gz") else "xz"
        self.default_export_name = default_export_name or default_name or ""
        self.multiple = bool(multiple)
        self.double_click = double_click if double_click in ("route", "open", "select") else "route"
        self._title = title

        self.result_paths = []
        self.result_path = ""
        self.result_filter = ""

        # Filtre listesi: [(etiket, uzantılar|None|"EXEC")]
        if filters:
            base_filters = list(filters)
        elif filter_extensions:
            exts = filter_extensions if isinstance(filter_extensions, str) else tuple(sorted(filter_extensions))
            label = "Kaydedilecek Dosya" if self.mode == "export" else f"{target_editor or 'Varsayılan'} Dosyaları"
            base_filters = [(label, exts)]
        elif target_editor and editor_extensions(target_editor):
            base_filters = [(f"{target_editor} Dosyaları", tuple(sorted(editor_extensions(target_editor))))]
        else:
            base_filters = []
        self._format_filters = [f for f in base_filters if f[1] is not None]
        self._filters = ensure_all_files_option(base_filters) if self.mode != "folder" else [(ALL_FILES_LABEL, None)]
        union = set()
        accept_any = not self._format_filters
        for _label, ext in self._format_filters:
            if ext == EXEC_FILTER:
                accept_any = True
            else:
                union.update(ext)
        self._accepted_exts = None if accept_any else union      # None: her şeyi kabul eder

        start = start_dir or EXPORT_DIR
        if os.path.isfile(start):
            if not self.default_export_name:
                self.default_export_name = os.path.basename(start)
            start = os.path.dirname(start)
        if not os.path.isdir(start):
            try:
                os.makedirs(start, exist_ok=True)
            except OSError:
                pass
        if not os.path.isdir(start):
            start = EXPORT_DIR if os.path.isdir(EXPORT_DIR) else str(Path.home())
        self.export_dir = EXPORT_DIR if os.path.isdir(EXPORT_DIR) else str(Path.home())
        self.current_path = os.path.abspath(start)
        self.show_hidden = False
        self.selected_filter = self._filters[0][1]
        self.search_text = ""
        self.history, self.history_index = [], -1
        self._rows = []
        self._pending_rows = []
        self._populate_gen = 0
        self._tooltip_filters = []
        self._drag_router = None
        self._initial_filter = initial_filter

        self.hover_card = HoverPreviewCard(self)
        self._closer = OutsideClickCloser(self)
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(120)
        self._search_timer.timeout.connect(self._rebuild_list)

        self._init_ui(self.settings.value("bookmark_path", ""))
        self._select_initial_filter()
        self._navigate_to(self.current_path, push_history=True)
        QTimer.singleShot(1500, _purge_trash_once)

        for seq, fn in (("Alt+Left", self._go_back), ("Alt+Right", self._go_forward), ("Alt+Up", self._go_up)):
            QShortcut(QKeySequence(seq), self, fn)

        self.search_edit.setFocus(Qt.OtherFocusReason)
        if self.mode == "export":
            self.search_edit.setText(os.path.splitext(self.default_export_name)[0] if self.default_export_name else "")
            self.search_edit.selectAll()
        self.btn_ok.setText({"open": "OK", "export": "Kaydet", "folder": "Seç"}[self.mode])

    # ------------------------------------------------------------------ UI
    def _init_ui(self, initial_bookmark):
        titles = {"open": "File", "export": "Export", "folder": "Klasör Seç"}
        self.setWindowTitle(self._title or titles[self.mode])
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(900, max(560, screen.width() - 60)), min(600, max(420, screen.height() - 80)))
        self.setMinimumSize(560, 420)
        self.setStyleSheet(_FM_STYLE)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        top = QFrame()
        top.setObjectName("topBar")
        top.setFixedHeight(40)
        tl = QHBoxLayout(top)
        tl.setContentsMargins(10, 5, 10, 5)
        tl.setSpacing(10)

        self.btn_back = QPushButton("Geri")
        self.btn_forward = QPushButton("İleri")
        self.btn_up = QPushButton("Üst")
        self.btn_home = QPushButton("export")
        self.btn_preview = QPushButton("/")
        self.btn_refresh = QPushButton("Yenile")
        for b in (self.btn_back, self.btn_forward, self.btn_up, self.btn_home, self.btn_preview, self.btn_refresh):
            b.setFixedSize(90, 30)
        self.btn_bookmark = BookmarkButton(initial_bookmark)
        self.btn_bookmark.setFixedSize(90, 30)
        self.e_path = QLineEdit(self.current_path)
        self.e_path.setFixedHeight(30)
        self.e_path.setMinimumWidth(90)

        self.btn_back.clicked.connect(self._go_back)
        self.btn_forward.clicked.connect(self._go_forward)
        self.btn_up.clicked.connect(self._go_up)
        self.btn_home.clicked.connect(lambda: self._navigate_to(self.export_dir, push_history=True))
        self.btn_home.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_home.customContextMenuRequested.connect(lambda _p: self._navigate_to(str(Path.home()), True))
        self.btn_preview.clicked.connect(self._toggle_hover_preview)
        self.btn_refresh.clicked.connect(lambda: self._load_directory(self.current_path))
        self.btn_bookmark.navigateRequested.connect(lambda p: self._navigate_to(p, push_history=True))
        self.btn_bookmark.bindRequested.connect(self._bind_current_location_to_bookmark)

        for w in (self.btn_back, self.btn_forward, self.btn_up, self.btn_home, self.btn_bookmark):
            tl.addWidget(w)
        tl.addWidget(self.e_path, 1)
        tl.addWidget(self.btn_preview)
        tl.addWidget(self.btn_refresh)
        main_layout.addWidget(top)

        self.file_list = HoverListWidget()
        self.file_list.setViewMode(QListView.IconMode)
        self.file_list.setIconSize(QSize(76, 76))
        self.file_list.setGridSize(QSize(148, 126))
        self.file_list.setSpacing(5)
        self.file_list.setResizeMode(QListView.Adjust)
        self.file_list.setMovement(QListView.Static)
        self.file_list.setUniformItemSizes(True)
        self.file_list.setWordWrap(True)
        self.file_list.setSelectionMode(QAbstractItemView.ExtendedSelection if (self.multiple and self.mode == "open")
                                        else QAbstractItemView.SingleSelection)
        self.file_list.installEventFilter(self)
        self.file_list.itemHovered.connect(self._on_item_hovered)
        self.file_list.mouseLeft.connect(self.hover_card.hide_preview)
        self.file_list.dragStarted.connect(self._on_drag_started)
        self.file_list.dragFinished.connect(self._on_drag_finished)
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self._show_file_context_menu)
        self.file_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.file_list.itemClicked.connect(self._on_item_clicked)
        main_layout.addWidget(self.file_list, 1)

        bottom = QFrame()
        bottom.setObjectName("bottomBar")
        bottom.setFixedHeight(44)
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(10, 0, 10, 0)
        bl.setSpacing(10)
        self.lbl_status = QLabel("Öğeler yükleniyor...")
        self.lbl_status.setStyleSheet("color:#f0f0f0; font-size:11pt; font-weight:bold;")
        lbl_filter = QLabel("Filtre:")
        lbl_filter.setStyleSheet("color:#e2e8f0; font-weight:bold; font-size:11pt;")
        self.cmb_filter = QComboBox()
        self.cmb_filter.setFixedHeight(32)
        self.cmb_filter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        for label, data in self._filters:
            self.cmb_filter.addItem(label, data)
        self.cmb_filter.currentIndexChanged.connect(self._on_filter_changed)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText({"open": "Dosya ara...", "folder": "Klasör ara...",
                                             "export": "Dosya adı (uzantı otomatik eklenir)"}[self.mode])
        self.search_edit.setFixedHeight(32)
        self.search_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_edit.textChanged.connect(self._on_search_text_changed)
        self.btn_ok = QPushButton("OK")
        self.btn_ok.setFixedSize(110, 36)
        self.btn_ok.clicked.connect(self._on_ok_clicked)

        bl.addWidget(self.lbl_status)
        bl.addWidget(lbl_filter)
        bl.addWidget(self.cmb_filter, 1)
        bl.addWidget(self.search_edit, 1)
        bl.addWidget(self.btn_ok)
        main_layout.addWidget(bottom)

        for widget, tip in (
            (self.btn_back, "Geçmişteki önceki dizine gider."),
            (self.btn_forward, "Geçmişteki sonraki dizine gider."),
            (self.btn_up, "Bir üst dizine çıkar."),
            (self.btn_home, "Sol tık: Kavram export klasörü. Sağ tık: kullanıcı ana klasörü."),
            (self.btn_bookmark, "Sol tık: kayıtlı konuma gider. Sağ tık: mevcut konumu sabitler."),
            (self.btn_preview, "Dosya üzerine gelince küçük önizleme penceresini açıp kapatır."),
            (self.btn_refresh, "Geçerli dizinin içeriğini yeniden okur."),
            (self.btn_ok, "Seçili dosyayı onaylar / kaydeder."),
        ):
            self._tooltip_filters.append(DelayedToolTip(widget, tip, 2000))

    def _select_initial_filter(self):
        idx = -1
        if self._initial_filter:
            idx = self.cmb_filter.findText(self._initial_filter)
        if idx < 0 and self.default_export_name:
            ext = path_extension(self.default_export_name)
            for i in range(self.cmb_filter.count()):
                data = self.cmb_filter.itemData(i)
                if isinstance(data, (tuple, list, set)) and ext in data:
                    idx = i
                    break
        if idx > 0:
            self.cmb_filter.blockSignals(True)
            self.cmb_filter.setCurrentIndex(idx)
            self.cmb_filter.blockSignals(False)
            self.selected_filter = self.cmb_filter.itemData(idx)

    # ------------------------------------------------------- pencere yaşamı
    def show_centered(self):
        parent = self.parentWidget()
        platform = QGuiApplication.platformName().lower()
        if parent is not None and not platform.startswith("wayland"):
            try:
                pg = parent.window().frameGeometry()
                self.move(pg.center() - self.rect().center())
            except Exception:
                pass
        self.show()
        self.raise_()
        self.activateWindow()

    def showEvent(self, event):
        super().showEvent(event)
        self._closer.arm()

    def hideEvent(self, event):
        self._closer.disarm()
        if hasattr(self, "hover_card"):
            self.hover_card.hide_preview()
        super().hideEvent(event)

    def closeEvent(self, event):
        self._closer.disarm()
        self._populate_gen += 1
        self._pending_rows = []
        self._remove_drag_router()
        self.hover_card.hide_preview()
        if FileManager._instance is self:
            FileManager._instance = None
        event.accept()
        self.closed.emit()

    def set_editor_context(self, editor_name=None, custom_editors=None, filter_extensions=None):
        """Eski API: editör bağlamına göre filtreleri yeniden kurar."""
        self.target_editor = editor_name
        self.custom_editors = custom_editors or self.custom_editors or []
        exts = filter_extensions or get_editor_default_extensions(editor_name, self.custom_editors)
        if self.mode == "export":
            return
        flt = []
        if editor_name and exts and exts != EXEC_FILTER:
            flt.append((f"{editor_name} - Varsayılan Dosyalar", tuple(sorted(exts))))
        elif exts == EXEC_FILTER:
            flt.append(("Program (çalıştırılabilir)", EXEC_FILTER))
        flt = ensure_all_files_option(flt)
        self.cmb_filter.blockSignals(True)
        self.cmb_filter.clear()
        for label, data in flt:
            self.cmb_filter.addItem(label, data)
        self.cmb_filter.setCurrentIndex(0)
        self.cmb_filter.blockSignals(False)
        self._filters = flt
        self.selected_filter = flt[0][1]
        self._load_directory(self.current_path)

    def select_file_path(self, file_path):
        """Dışarıdan seçilen dosyayı bildirir (eski API)."""
        if not file_path or not os.path.isfile(file_path):
            return False
        full = os.path.abspath(file_path)
        if not self._ext_allowed(full):
            return False
        self.lbl_status.setText(f"Seçildi: {full}")
        self.fileSelected.emit(full)
        return True

    # ------------------------------------------------------------ gezinme
    def _set_status(self, text, error=False):
        self.lbl_status.setStyleSheet(
            f"color:{'#ff8a80' if error else '#f0f0f0'}; font-size:11pt; font-weight:bold;")
        self.lbl_status.setText(text)

    def _bind_current_location_to_bookmark(self):
        self.btn_bookmark.set_target_path(self.current_path)
        self.settings.setValue("bookmark_path", self.current_path)
        self._set_status(f"Konum X düğmesine sabitlendi: {os.path.basename(self.current_path) or self.current_path}")

    def _navigate_to(self, path, push_history=True):
        target = os.path.abspath(os.path.expanduser(str(path)))
        if not os.path.isdir(target):
            self._set_status("Dizin bulunamadı.", error=True)
            self.e_path.setText(self.current_path)
            return
        if push_history and (self.history_index < 0 or self.history[self.history_index] != target):
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

    def _is_internal_trash_directory(self, path):
        try:
            return os.path.abspath(path) == os.path.abspath(str(APP_TRASH_FILES))
        except (TypeError, OSError):
            return False

    # ------------------------------------------------------------ listeleme
    def _load_directory(self, target):
        self.current_path = target
        self.e_path.setText(target)
        self.show_hidden = self._is_internal_trash_directory(target)
        self.hover_card.hide_preview()
        try:
            self._rows = scan_directory(target, self.show_hidden)
            error = ""
        except OSError as exc:
            self._rows = []
            error = f"Klasör okunamadı: {exc.strerror or exc}"
        self._rebuild_list()
        if error:
            self._set_status(error, error=True)

    def _ext_allowed(self, path):
        flt = self.selected_filter
        if flt is None:
            return True
        if flt == EXEC_FILTER:
            return os.access(path, os.X_OK)
        return path_extension(path) in flt

    def _rebuild_list(self):
        """Önbellekteki satırları filtre + aramaya göre süzer; dosya sistemi yeniden okunmaz."""
        self._populate_gen += 1
        gen = self._populate_gen
        self.search_text = self.search_edit.text().strip().casefold() if (
            hasattr(self, "search_edit") and self.mode != "export") else ""
        folder_only = self.mode == "folder"
        rows = []
        for name, full, is_dir, size in self._rows:
            if folder_only and not is_dir:
                continue
            if not is_dir and not self._ext_allowed(full):
                continue
            if self.search_text and self.search_text not in name.casefold():
                continue
            rows.append((name, full, is_dir))
        self.file_list.clear()
        self._pending_rows = rows
        self._set_status(f"Toplam öğe: {len(rows)}")
        self.lbl_status.setToolTip(f"Geçerli konum: {self.current_path}")
        self._populate_chunk(gen)

    def _populate_chunk(self, gen):
        """Büyük klasörlerde arayüz donmasın diye öğeler parça parça eklenir."""
        if gen != self._populate_gen or not self._pending_rows:
            return
        chunk, self._pending_rows = self._pending_rows[:400], self._pending_rows[400:]
        self.file_list.setUpdatesEnabled(False)
        try:
            for name, full, is_dir in chunk:
                item = QListWidgetItem(make_type_icon(path_extension(name), is_dir), name)
                item.setData(Qt.UserRole, (full, is_dir))
                item.setTextAlignment(Qt.AlignCenter)
                self.file_list.addItem(item)
        finally:
            self.file_list.setUpdatesEnabled(True)
        if self._pending_rows:
            QTimer.singleShot(0, lambda g=gen: self._populate_chunk(g))

    def _on_filter_changed(self, index):
        self.selected_filter = self.cmb_filter.itemData(index)
        self._rebuild_list()

    def _on_search_text_changed(self, _text):
        if self.mode != "export":
            self._search_timer.start()

    # ----------------------------------------------------- silme / çöp kutusu
    def _safe_delete_target(self, path):
        target = os.path.abspath(path)
        home = os.path.abspath(str(Path.home()))
        protected = ("/bin", "/boot", "/dev", "/etc", "/lib", "/lib64", "/proc", "/root", "/run", "/sbin", "/sys", "/usr", "/var")
        if target in {os.path.abspath(os.sep), home}:
            return False
        try:
            if os.path.commonpath((target, home)) == target:
                return False
            for base in protected:
                if target == base or os.path.commonpath((target, base)) == base:
                    return False
        except ValueError:
            pass
        return True

    def _is_in_app_trash(self, path):
        try:
            target = os.path.abspath(path)
            root = os.path.abspath(str(APP_TRASH_FILES))
            return os.path.commonpath((target, root)) == root and target != root
        except (ValueError, OSError):
            return False

    def _move_path_to_app_trash(self, source):
        source = os.path.abspath(source)
        if not os.path.lexists(source) or not self._safe_delete_target(source):
            return False, "Bu konum taşınamaz veya artık mevcut değil."
        info = None
        try:
            for d in (APP_TRASH_ROOT, APP_TRASH_FILES, APP_TRASH_INFO):
                d.mkdir(parents=True, exist_ok=True, mode=0o700)
                try:
                    os.chmod(d, 0o700)
                except OSError:
                    pass
            base = os.path.basename(source.rstrip(os.sep)) or "dosya"
            dest = APP_TRASH_FILES / base
            if dest.exists() or dest.is_symlink():
                dest = APP_TRASH_FILES / f"{base}.{int(time.time())}.{uuid.uuid4().hex[:8]}"
            info = APP_TRASH_INFO / (dest.name + ".trashinfo")
            deleted_at = datetime.now().replace(microsecond=0)
            info.write_text("[Trash Info]\n" + f"Path={quote(source, safe='/._-~')}\n" +
                            f"DeletionDate={deleted_at.strftime('%Y-%m-%dT%H:%M:%S')}\n", encoding="utf-8")
            shutil.move(source, str(dest))
            return True, ""
        except Exception as exc:
            if info is not None:
                try:
                    info.unlink(missing_ok=True)
                except OSError:
                    pass
            return False, str(exc)

    def _selected_paths(self):
        out = []
        for item in self.file_list.selectedItems():
            data = item.data(Qt.UserRole)
            if data:
                out.append((os.path.abspath(data[0]), bool(data[1])))
        return out

    def _show_file_context_menu(self, pos):
        item = self.file_list.itemAt(pos)
        if item is not None and not item.isSelected():
            self.file_list.clearSelection()
            item.setSelected(True)
            self.file_list.setCurrentItem(item)
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_STYLE)
        selected = self._selected_paths() if item is not None else []
        clicked_path = os.path.abspath(item.data(Qt.UserRole)[0]) if (item is not None and item.data(Qt.UserRole)) else None
        inside_trash = bool(clicked_path and self._is_in_app_trash(clicked_path))
        if clicked_path:
            path, is_dir = item.data(Qt.UserRole)
            if is_dir and not inside_trash:
                menu.addAction("Dizine Gir").triggered.connect(lambda _c=False, p=path: self._navigate_to(p, True))
            elif not is_dir and not inside_trash and self.mode == "open":
                menu.addAction("Aç").triggered.connect(lambda _c=False, p=path: self._open_by_extension(p))
            menu.addSeparator()
        if inside_trash:
            menu.addAction("Özgün Konumuna Geri Yükle").triggered.connect(
                lambda _c=False, p=clicked_path: self._restore_from_app_trash(p))
            menu.addAction("Çöp Kutusundan Kalıcı Sil").triggered.connect(self._delete_selected_permanently)
            menu.addSeparator()
        elif selected:
            menu.addAction("Çöp Kutusuna Taşı").triggered.connect(self._move_selected_to_trash)
            menu.addAction("Sil (Kalıcı)").triggered.connect(self._delete_selected_permanently)
            menu.addSeparator()
        if not self._is_internal_trash_directory(self.current_path):
            menu.addAction("Çöp Kutusunu Aç").triggered.connect(self._open_internal_trash)
        # Menü açıkken odak kaybı penceremizi kapatmasın.
        menu.exec_(self.file_list.viewport().mapToGlobal(pos))

    def _open_internal_trash(self):
        idx = self.cmb_filter.findData(None)
        if idx >= 0:
            self.cmb_filter.blockSignals(True)
            self.cmb_filter.setCurrentIndex(idx)
            self.cmb_filter.blockSignals(False)
            self.selected_filter = None
        self.search_edit.clear()
        APP_TRASH_FILES.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._navigate_to(str(APP_TRASH_FILES), True)

    def _move_selected_to_trash(self):
        failures, moved = [], 0
        for path, _d in self._selected_paths():
            ok, error = self._move_path_to_app_trash(path)
            if ok:
                moved += 1
            else:
                failures.append(f"{os.path.basename(path)}: {error}")
        self._load_directory(self.current_path)
        if failures:
            self._set_status(f"{moved} öğe çöp kutusuna taşındı; {len(failures)} öğe taşınamadı.", error=True)
            self.lbl_status.setToolTip("\n".join(failures[:8]))

    def _delete_selected_permanently(self):
        failures, deleted = [], 0
        for path, _d in self._selected_paths():
            if not self._safe_delete_target(path):
                failures.append(f"{os.path.basename(path)}: korunan konum")
                continue
            try:
                if os.path.islink(path) or os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    failures.append(f"{os.path.basename(path)}: dosya bulunamadı")
                    continue
                if self._is_in_app_trash(path):
                    try:
                        _trash_info_path_for(path).unlink(missing_ok=True)
                    except OSError:
                        pass
                deleted += 1
            except Exception as exc:
                failures.append(f"{os.path.basename(path)}: {exc}")
        self._load_directory(self.current_path)
        if failures:
            self._set_status(f"{deleted} öğe kalıcı silindi; {len(failures)} öğe silinemedi.", error=True)
            self.lbl_status.setToolTip("\n".join(failures[:8]))

    def _restore_from_app_trash(self, trashed_path):
        trashed_path = os.path.abspath(trashed_path)
        if not self._is_in_app_trash(trashed_path):
            return
        info_path = _trash_info_path_for(trashed_path)
        _when, original = _read_trash_info(info_path)
        if not original:
            self._set_status("Özgün konum bilgisi okunamadı; dosya güvenle bırakıldı.", error=True)
            return
        parent_dir = os.path.dirname(original)
        if not os.path.isdir(parent_dir):
            original = os.path.join(str(Path.home()), os.path.basename(original))
        dest = original
        if os.path.lexists(dest):
            base, ext = os.path.splitext(dest)
            dest = f"{base}.geri_yuklendi_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        try:
            shutil.move(trashed_path, dest)
            info_path.unlink(missing_ok=True)
        except Exception as exc:
            self._set_status(f"Geri yükleme hatası: {exc}", error=True)
            return
        self._navigate_to(os.path.dirname(dest), True)

    # --------------------------------------------------------- klavye / fare
    def eventFilter(self, obj, event):
        if obj is self.file_list and event.type() == QEvent.KeyPress and self.mode != "export":
            if event.key() == Qt.Key_Backspace:
                self.search_edit.setFocus()
                self.search_edit.backspace()
                return True
            text = event.text()
            if text and text.isprintable() and not event.modifiers() & (Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier):
                self.search_edit.setFocus()
                self.search_edit.insert(text)
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            event.accept()
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if QApplication.focusWidget() is self.e_path:
                self._navigate_to(self.e_path.text(), push_history=True)
            else:
                self._on_ok_clicked()
            event.accept()
            return
        super().keyPressEvent(event)

    def _toggle_hover_preview(self):
        self.preview_enabled = not self.preview_enabled
        self.settings.setValue("hover_preview_enabled", self.preview_enabled)
        if not self.preview_enabled:
            self.hover_card.hide_preview()

    def _on_item_hovered(self, filepath, is_dir, is_video, is_image):
        if self.preview_enabled and self.isVisible():
            self.hover_card.show_preview(filepath, is_dir=is_dir, is_video=is_video, is_image=is_image)

    # ------------------------------------------------------ sürükle-bırak
    def _on_drag_started(self):
        self._closer.suspend()
        self._remove_drag_router()
        self._drag_router = _FMDragRouter(self)
        QApplication.instance().installEventFilter(self._drag_router)

    def _remove_drag_router(self):
        router, self._drag_router = self._drag_router, None
        if router is not None:
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(router)
            router.deleteLater()

    def _on_drag_finished(self, action):
        router = self._drag_router
        enter_seen = bool(router and router.enter_seen)
        self._remove_drag_router()
        QTimer.singleShot(700, self._closer.resume)
        if action != int(Qt.IgnoreAction):
            QTimer.singleShot(0, self.close)      # bırakma kabul edildi: iş bitti
            return
        # Qt, bırakmayı hiçbir pencereye ulaştırmadıysa (sürükleme protokolü başarısız) imlecin altındaki
        # Kavram penceresine bırakmayı elle teslim et. Kullanıcı Esc ile vazgeçtiyse (Qt hedefe
        # DragEnter göndermişse) yedek yol devreye girmez.
        paths = list(getattr(self.file_list, "last_drag_paths", []))
        if enter_seen or not paths or _CORE is None:
            return
        try:
            cur = QCursor.pos()
            target = QApplication.widgetAt(cur)
            if target is None or _is_inside(target, self):
                return
            if _CORE.fm_accepts_drop(paths, target):
                print("[File] Qt bırakmayı iletmedi; yedek yol kullanıldı")
                QTimer.singleShot(0, lambda p=paths, t=target, g=cur: _deliver_drop(p, t, g))
                QTimer.singleShot(0, self.close)
        except Exception as exc:
            print("[File] Yedek bırakma yolu başarısız:", exc)

    # ------------------------------------------------------------ eylemler
    def _on_ok_clicked(self):
        if self.mode == "export":
            self._export_files()
        elif self.mode == "folder":
            self._choose_folder()
        else:
            self._accept_selected()

    def _on_item_clicked(self, item):
        """Kaydet kipinde bir dosyaya tıklamak adını alana yazar (üzerine yazmak için)."""
        data = item.data(Qt.UserRole)
        if self.mode == "export" and data and not data[1]:
            self.search_edit.setText(os.path.splitext(os.path.basename(data[0]))[0])

    def _accept_selected(self):
        paths = []
        for path, is_dir in self._selected_paths():
            if not is_dir and os.path.isfile(path) and self._ext_allowed(path):
                paths.append(path)
        if not paths:
            self._set_status("Açmak için en az bir dosya seçin.", error=True)
            return []
        self._finish_open(paths)
        return paths

    def _finish_open(self, paths):
        self.result_paths = list(paths)
        self.result_path = paths[0] if paths else ""
        self.result_filter = self.cmb_filter.currentText()
        self.filesSelected.emit(list(paths))
        for p in paths:
            self.fileSelected.emit(p)
        self.close()

    def _choose_folder(self):
        sel = [p for p, d in self._selected_paths() if d]
        self.result_path = sel[0] if sel else self.current_path
        self.result_paths = [self.result_path]
        self.fileSelected.emit(self.result_path)
        self.close()

    def _open_by_extension(self, path):
        """Dosyayı uzantısına uygun editörde açar (çift tıklama / 'Aç')."""
        editor = editor_for_path(path, getattr(_CORE, "custom_editors", None))
        if _CORE is None or not hasattr(_CORE, "open_file_anywhere"):
            try:
                subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
                self.close()
            except Exception as exc:
                self._set_status(f"Dosya açılamadı: {exc}", error=True)
            return
        if not editor:
            self._set_status("Bu dosya türü için bir Kavram editörü yok.", error=True)
            return
        self.close()
        # Çağıran editör bu pencereyi bekliyor olabilir; iş, o yığın boşaldıktan sonra yapılır.
        QTimer.singleShot(0, lambda p=path: _core_open(p))

    def _on_item_double_clicked(self, item):
        data = item.data(Qt.UserRole)
        if not data:
            return
        full_path, is_dir = data
        if is_dir:
            self._navigate_to(full_path, push_history=True)
            return
        if self.mode == "folder":
            return
        ext = path_extension(full_path)
        if self.mode == "export":
            # Kaydet kipinde aynı türden dosya = üzerine yazma adı; farklı tür = kendi editöründe aç.
            known = {e for _l, exts in self._format_filters if isinstance(exts, tuple) for e in exts}
            if not known or ext in known:
                self.search_edit.setText(os.path.splitext(os.path.basename(full_path))[0])
                self.search_edit.setFocus()
                return
            self._open_by_extension(full_path)
            return
        accepted_here = self._accepted_exts is None or ext in self._accepted_exts
        if self.double_click == "select" or (self.double_click == "route" and accepted_here):
            if self._ext_allowed(full_path) or accepted_here:
                self._finish_open([os.path.abspath(full_path)])
                return
        if (self.double_click == "route" and self._ext_allowed(full_path)
                and editor_for_path(full_path, getattr(_CORE, "custom_editors", None)) is None):
            # Hiçbir Kavram editörü bu türü açmıyor ('Bütün Dosyalar' görünümü): hata verme, seç.
            self._finish_open([os.path.abspath(full_path)])
            return
        self._open_by_extension(full_path)

    # -------------------------------------------------------------- kaydet
    def _allowed_save_exts(self):
        flt = self.selected_filter
        if isinstance(flt, (tuple, list, set)):
            return tuple(flt)
        if self._format_filters:
            first = self._format_filters[0][1]
            return tuple(first) if isinstance(first, (tuple, list, set)) else ()
        d = path_extension(self.default_export_name)
        return (d,) if d else ()

    def _compute_save_target(self):
        name = self.search_edit.text().strip()
        if not name or name in (".", ".."):
            self._set_status("Dosya adı gerekli.", error=True)
            self.search_edit.setFocus()
            return None
        if "/" in name or "\x00" in name:
            self._set_status("Dosya adında '/' bulunamaz.", error=True)
            return None
        all_known = {e for _l, ex in self._format_filters if isinstance(ex, tuple) for e in ex}
        typed = path_extension(name)
        label = ""
        if typed and (typed in all_known or self.selected_filter is None):
            # Bilinen bir uzantı yazıldı ya da 'Bütün Dosyalar' seçili: ad yazıldığı gibi kalır.
            for lab, ex in self._format_filters:
                if isinstance(ex, tuple) and typed in ex:
                    label = lab
                    break
            if not label:
                label = self.cmb_filter.currentText()
        else:
            allowed = self._allowed_save_exts()
            name += allowed[0] if allowed else ""
            label = self.cmb_filter.currentText()
            if self.selected_filter is None and self._format_filters:
                label = self._format_filters[0][0]
        return os.path.join(self.current_path, name), label

    def _export_files(self):
        target = self._compute_save_target()
        if target is None:
            return
        save_path, label = target
        if os.path.isdir(save_path):
            self._set_status("Bu ada sahip bir klasör var.", error=True)
            return
        if os.path.exists(save_path):
            answer = _styled_box(self, "Üzerine yaz",
                                 f"'{os.path.basename(save_path)}' zaten var.\nÜzerine yazılsın mı?",
                                 QMessageBox.Question, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        if not os.access(self.current_path, os.W_OK):
            self._set_status("Bu klasöre yazma izni yok.", error=True)
            return
        self.result_path, self.result_paths, self.result_filter = save_path, [save_path], label

        if callable(self.export_callback):         # eski API: gerçek kaydı çağıran yapar
            self.setEnabled(False)
            try:
                result = self.export_callback(save_path, self.export_compression)
                if result is False:
                    if os.path.exists(save_path):
                        try:
                            os.remove(save_path)
                        except OSError:
                            pass
                    self.result_path, self.result_paths = "", []
                    self.exportCancelled.emit()
                    return
                self.exportCompleted.emit(save_path)
            except Exception as exc:
                self.result_path, self.result_paths = "", []
                _styled_box(self, "Hata", f"Kaydetme sırasında hata oluştu:\n{exc}", QMessageBox.Critical)
            finally:
                self.setEnabled(True)
                self.close()
            return
        self.exportCompleted.emit(save_path)
        self.fileSelected.emit(save_path)
        self.close()


def _core_open(path):
    try:
        if _CORE is not None:
            _CORE.open_file_anywhere(path)
    except Exception as exc:
        print("[File] Dosya açılamadı:", exc)


# --------------------------------------------------------------------------- #
#  QFileDialog yerine geçen API
# --------------------------------------------------------------------------- #
def _owner(parent):
    w = parent if isinstance(parent, QWidget) else QApplication.activeWindow()
    return w.window() if w is not None else None


def _run_blocking(fm):
    """FileManager'ı yerel olay döngüsüyle bekletir; kapanınca (veya yok olunca) döner."""
    loop = QEventLoop()
    fm.closed.connect(loop.quit)
    fm.destroyed.connect(loop.quit)
    app = QApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(fm.close)
    fm.show_centered()
    loop.exec_()
    result = (list(fm.result_paths), fm.result_filter)
    try:
        fm.deleteLater()
    except RuntimeError:
        pass
    return result


def _split_directory(directory):
    directory = str(directory or "")
    if directory and not os.path.isdir(directory):
        parent = os.path.dirname(directory)
        return (parent if os.path.isdir(parent) else EXPORT_DIR), os.path.basename(directory)
    return (directory or EXPORT_DIR), ""


def _pick(parent, mode, caption, directory, filter_str, initial_filter, editor, multiple, double_click):
    existing = FileManager.live_instance()
    if existing is not None:               # zaten açık: ikinci pencere açma, öne getir
        existing.raise_()
        existing.activateWindow()
        return [], ""
    start, default_name = _split_directory(directory)
    if os.path.isfile(str(directory or "")):
        start, default_name = os.path.dirname(directory), os.path.basename(directory)
    filters = parse_qt_filter(filter_str)
    fm = FileManager(parent=_owner(parent), target_editor=editor, mode=mode, filters=filters,
                     start_dir=start, title=caption or None, multiple=multiple,
                     double_click=double_click, initial_filter=initial_filter or "",
                     default_name=default_name)
    return _run_blocking(fm)


def get_open_file_name(parent=None, caption="", directory="", filter="", initialFilter="",
                       options=None, *, editor=None, double_click="route"):
    try:
        paths, flt = _pick(parent, "open", caption, directory, filter, initialFilter, editor, False, double_click)
    except Exception as exc:
        print("[File] FileManager açılamadı, Qt diyaloguna dönülüyor:", exc)
        return QFileDialog.getOpenFileName(parent, caption, directory, filter)
    return (paths[0] if paths else ""), flt


def get_open_file_names(parent=None, caption="", directory="", filter="", initialFilter="",
                        options=None, *, editor=None, double_click="route"):
    try:
        paths, flt = _pick(parent, "open", caption, directory, filter, initialFilter, editor, True, double_click)
    except Exception as exc:
        print("[File] FileManager açılamadı, Qt diyaloguna dönülüyor:", exc)
        return QFileDialog.getOpenFileNames(parent, caption, directory, filter)
    return list(paths), flt


def get_save_file_name(parent=None, caption="", directory="", filter="", initialFilter="",
                       options=None, *, editor=None):
    try:
        paths, flt = _pick(parent, "export", caption, directory, filter, initialFilter, editor, False, "route")
    except Exception as exc:
        print("[File] FileManager açılamadı, Qt diyaloguna dönülüyor:", exc)
        return QFileDialog.getSaveFileName(parent, caption, directory, filter)
    return (paths[0] if paths else ""), flt


def get_existing_directory(parent=None, caption="", directory="", options=None, *, editor=None):
    try:
        paths, _f = _pick(parent, "folder", caption, directory, "", "", editor, False, "select")
    except Exception as exc:
        print("[File] FileManager açılamadı, Qt diyaloguna dönülüyor:", exc)
        return QFileDialog.getExistingDirectory(parent, caption, directory)
    return paths[0] if paths else ""


# ---------------------------------------------------------------------------------------
# Kaydetme / dışa aktarma bildirimi: tüm editörlerde aynı küçük pencere ("Dosya kaydedildi.").
# Tıklama istemez, odağı çalmaz, 0,4 sn sonra kendiliğinden kapanır.
# ---------------------------------------------------------------------------------------
SAVED_TEXT = "Dosya kaydedildi."
SAVED_MSEC = 400
_live_toasts = []


def notify_saved(parent=None, text=SAVED_TEXT, msec=SAVED_MSEC):
    """Küçük bildirim penceresi gösterir ve `msec` ms sonra kapatır (engellemez)."""
    try:
        app = QApplication.instance()
        if app is None:
            return
        anchor = parent.window() if isinstance(parent, QWidget) else app.activeWindow()
        toast = QLabel(str(text))
        toast.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
                             | Qt.WindowDoesNotAcceptFocus)
        toast.setAttribute(Qt.WA_ShowWithoutActivating, True)
        toast.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        toast.setAlignment(Qt.AlignCenter)
        toast.setStyleSheet(
            "QLabel { background-color: #2b2b2b; color: #f0f0f0; border: 2px solid #555;"
            " border-radius: 8px; padding: 14px 26px; font-size: 15px; }")
        toast.adjustSize()
        if anchor is not None and anchor.isVisible():
            center = anchor.mapToGlobal(anchor.rect().center())
        else:
            center = app.primaryScreen().availableGeometry().center()
        toast.move(center.x() - toast.width() // 2, center.y() - toast.height() // 2)
        _live_toasts.append(toast)

        def _kapat(t=toast):
            try:
                t.close()
                t.deleteLater()
            finally:
                if t in _live_toasts:
                    _live_toasts.remove(t)

        toast.show()
        QTimer.singleShot(max(50, int(msec)), _kapat)
    except Exception as exc:
        print("[File] Bildirim gösterilemedi:", exc)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    if APP_ICON.is_file():
        app.setWindowIcon(QIcon(str(APP_ICON)))
    win = FileManager()
    win.show_centered()
    sys.exit(app.exec_())
