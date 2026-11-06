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

# --- kavram yol ayarı (otomatik; klasör yapısı: kavram/<program>/<program>.py) ---


# --- Tüm içe aktarmalar (tek yerde) ---
import os as _os
import sys as _sys
import re
import math
import base64
import binascii
import html
import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Callable, List, Optional

from PyQt5.QtCore import QByteArray, QMimeData, QPoint, QRect, QRectF, Qt, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import (QBitmap, QBrush, QColor, QFont, QFontMetrics, QIcon, QImage, QKeySequence,
                         QPainter, QPalette, QPen, QPixmap, QRegion, QTextCharFormat, QTextCursor,
                         QTextDocument, QTextFormat)
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import (
    QAction, QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu,
    QMessageBox, QProgressDialog, QScrollArea, QShortcut, QSizePolicy, QSlider, QStackedWidget,
    QTextEdit, QToolTip, QVBoxLayout, QWidget
)
# --- Kavram ortak arayüz dili (kavram_ui.py: tema, düğme, üst bar, Türkçe açıklamalar) ---
import os as _kui_os
import sys as _kui_sys
try:
    import kavram_ui as kui
except ImportError:      # program tek başına çalıştırılırsa ortak modül bir üst klasörde aranır
    _kui_sys.path.insert(0, _kui_os.path.dirname(_kui_os.path.dirname(_kui_os.path.abspath(__file__))))
    import kavram_ui as kui
from kavram_ui import KButton, KToolButton
# ---------------------------------------------------------------------------------------

_PROGRAM_DIR = _os.path.dirname(_os.path.abspath(__file__))
_KAVRAM_DIR = _os.environ.get("KAVRAM_DIR") or _os.path.dirname(_PROGRAM_DIR)
_KAVRAM_EXPORT_DIR = _os.path.join(_KAVRAM_DIR, "export")
# -------------------------------------------------------------------------------


# ======================================================================
# config
# ======================================================================
"""Copya sabitleri. Limit, boyut ve kısayol gibi ayarlar yalnızca bu dosyada tutulur."""

# --- Sınırlar ---
MAX_NOTES = 200
MAX_GALLERY_ITEMS = 35
MAX_DOCUMENT_ITEMS = 500          # belge sayfası / resmi üst sınırı
ARCHIVE_MAX_MEMBERS = 10_000      # .copya içindeki en fazla dosya sayısı
ARCHIVE_MAX_BYTES = 4 * 1024**3   # .copya açılınca toplam açılmış boyut üst sınırı

# --- Kaydırma ve belge boyutu ---
SCROLL_SPEEDS = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]
DEFAULT_SCROLL_INDEX = 4
DEFAULT_DOC_SIZE = 15
DOC_SIZE_CHOICES = [0.5] + list(range(1, 21))

# --- Önbellek ve performans ---
RENDER_DPI = 150
PAGE_CACHE_SIZE = 8               # önbellekte tutulan render edilmiş sayfa sayısı
IMAGE_CACHE_SIZE = 8              # önbellekte tutulan tam çözünürlüklü resim sayısı
OPEN_DOCUMENT_CACHE_SIZE = 3      # açık tutulan PDF/belge tanıtıcısı sayısı
TEXT_DEBOUNCE_MS = 300            # metin değişikliğinde HTML üretimini geciktirme süresi

# --- Arayüz ---
NOTE_HEIGHT = 220
CARD_HEIGHT = 180
COLLAPSE_SHORTCUT = "Alt+X"
DEFAULT_COVER = "#333333"   # üst çubuktaki "_" (notu küçült) düğmesi

# --- Dönüştürme ---
OFFICE_TIMEOUT_S = 180

# --- Desteklenen dosya türleri (küçük harf, nokta ile) ---
IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tif', '.tiff')
TEXT_EXTS = ('.txt', '.txr')
PAGED_EXTS = ('.pdf', '.xps', '.epub', '.mobi', '.fb2', '.cbz', '.svg')
OFFICE_EXTS = ('.doc', '.docx', '.odt', '.rtf', '.txt', '.xls', '.xlsx', '.ods',
               '.csv', '.ppt', '.pptx', '.odp')
PNF_EXTS = ('.pnf',)

GALLERY_EXTS = IMAGE_EXTS + TEXT_EXTS
DOCUMENT_EXTS = PAGED_EXTS + OFFICE_EXTS + PNF_EXTS + IMAGE_EXTS

# ======================================================================
# theme
# ======================================================================
"""Stiller ve ikonlar. Değerler önceki sürümle birebir aynıdır (arayüz değişmedi)."""

SVG_SAVE_ICON = """<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M17 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V7L17 3ZM12 17C10.34 17 9 15.66 9 14C9 12.34 10.34 11 12 11C13.66 11 15 12.34 15 14C15 15.66 13.66 17 12 17Z" stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>"""

BUTTON_STYLE = kui.style_text()

TOOL_DELETE_STYLE = "QPushButton { background-color: transparent; color: white; font-size: 14px; font-weight: bold; border: 2px solid #555; border-radius: 8px; padding: 5px; } QPushButton:hover { background-color: #000000; border-color: #999; } QPushButton:pressed { background-color: #222; } QPushButton:disabled { color: #555; border-color: #333; }"

NOTE_FRAME_STYLE = "NoteWidget { background-color: #2b2b2b; border: 1px solid #444; border-radius: 8px; }"

NOTE_BUTTON_STYLE = kui.style_tool_button()

NOTE_DELETE_STYLE = "QToolButton { background-color: #444; color: #aaa; border: 1px solid #666; border-radius: 6px; } QToolButton:hover { background-color: #000000; color: #fff; border-color: #999; }"

GALLERY_BUTTON_STYLE = kui.style_tool_button()

GALLERY_DELETE_STYLE = "QToolButton { background-color: #333; color: #aaa; border: 1px solid #555; border-radius: 6px; font-weight: bold; font-family: 'Segoe UI'; } QToolButton:hover { background-color: #000000; color: #fff; border-color: #999; } QToolButton:pressed { background-color: #222; }"

MENU_STYLE = kui.style_menu()

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

# ======================================================================
# models
# ======================================================================
"""Veri modeli: not, öğe ve .copya kayıt biçimine dönüşüm. Arayüzden bağımsızdır.

Kayıt biçimi (.copya içindeki data.json) eski sürümle uyumlu tutuldu.
"""


log = logging.getLogger("copya.models")

KIND_TEXT = "text"
KIND_GALLERY = "gallery"
KIND_DOCUMENT = "document"

ITEM_IMG = "img"
ITEM_PAGE = "pdf_page"     # sayfalı belgenin bir sayfası (eski biçimle aynı ad)
ITEM_TXT = "txt"

GALLERY_MARK = "[GALLERY_PACKAGE]"
DOCUMENT_MARK_PREFIX = "[DOCUMENT_PACKAGE_"


class Item:
    """Galeri veya belgede tek bir öğe (resim, belge sayfası ya da metin)."""

    def __init__(self, type, content, name, page_index=0, is_txr=False):
        self.type = type            # ITEM_IMG, ITEM_PAGE veya ITEM_TXT
        self.content = content      # img/pdf_page için dosya yolu, txt için metin
        self.name = name
        self.page_index = page_index
        self.is_txr = is_txr


class Note:
    """Bir kartın verisi. Arayüz bu sınıfın alanlarını okur/yazar."""

    def __init__(self, kind=KIND_TEXT, title="", text="", items=None,
                 doc_type=None, doc_size=DEFAULT_DOC_SIZE, current_page=0, cover=DEFAULT_COVER):
        self.kind = kind
        self.title = title
        self.text = text            # yalnızca metin notu için (HTML)
        self.items = list(items) if items else []
        self.doc_type = doc_type
        self.doc_size = doc_size
        self.current_page = current_page
        self.cover = cover

    @property
    def is_media(self) -> bool:
        return self.kind != KIND_TEXT

    @property
    def is_document(self) -> bool:
        return self.kind == KIND_DOCUMENT

    @property
    def max_items(self) -> int:
        return MAX_DOCUMENT_ITEMS if self.is_document else MAX_GALLERY_ITEMS

    def can_add(self, count: int = 1) -> bool:
        return len(self.items) + count <= self.max_items

    def unique_name(self, base: str) -> str:
        """'a.png' zaten varsa 'a (1).png', 'a (2).png' ... üretir."""
        existing = {it.name for it in self.items}
        if base not in existing:
            return base
        root, ext = os.path.splitext(base)
        n = 1
        while f"{root} ({n}){ext}" in existing:
            n += 1
        return f"{root} ({n}){ext}"

    def add_item(self, item: Item) -> bool:
        if not self.can_add():
            return False
        self.items.append(item)
        return True


def clean_cover(value) -> str:
    s = str(value or "")
    return s.upper() if re.fullmatch(r"#[0-9A-Fa-f]{6}", s) else DEFAULT_COVER


def clamp_doc_size(value) -> int:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return DEFAULT_DOC_SIZE
    return v if v in DOC_SIZE_CHOICES else DEFAULT_DOC_SIZE


# --- .copya kayıt dönüşümleri ---

def note_to_dict(note: Note) -> dict:
    data = {
        'package': note.title,
        'doc_size': note.doc_size,
        'is_document_mode': note.is_document,
        'doc_type': note.doc_type,
    }
    if not note.is_media:
        data['note'] = note.text
        return data

    entries = []
    for it in note.items:
        if it.type == ITEM_TXT:
            entries.append({'type': ITEM_TXT, 'data': it.content,
                            'name': it.name, 'is_txr': it.is_txr})
        elif it.type == ITEM_PAGE:
            entries.append({'type': ITEM_PAGE, 'filename': os.path.basename(it.content),
                            'page_index': it.page_index, 'name': it.name})
        else:
            entries.append({'type': ITEM_IMG, 'filename': os.path.basename(it.content),
                            'name': it.name})
    data['cover'] = note.cover
    data['gallery_data'] = entries
    if note.is_document:
        data['note'] = f"{DOCUMENT_MARK_PREFIX}{(note.doc_type or '').upper()}]"
    else:
        data['note'] = GALLERY_MARK
    return data


def note_from_dict(raw, resolve: Callable[[str], Optional[str]]) -> Note:
    """Ham sözlükten not üretir. `resolve(dosya_adı)` çalışma alanındaki tam yolu döndürür
    (dosya yoksa None). Geçersiz öğeler atlanır, hata fırlatılmaz."""
    if not isinstance(raw, dict):
        raise ValueError("Not kaydı sözlük değil.")

    note_str = str(raw.get('note', ''))
    is_doc = bool(raw.get('is_document_mode'))
    is_media = (isinstance(raw.get('gallery_data'), list)
                or note_str == GALLERY_MARK
                or note_str.startswith(DOCUMENT_MARK_PREFIX))

    if not is_media:
        return Note(kind=KIND_TEXT, title=str(raw.get('package', ''))[:300],
                    text=note_str)

    note = Note(kind=KIND_DOCUMENT if is_doc else KIND_GALLERY,
                title=str(raw.get('package', ''))[:300],
                doc_type=raw.get('doc_type'),
                doc_size=clamp_doc_size(raw.get('doc_size')),
                cover=clean_cover(raw.get('cover')))

    for g in raw.get('gallery_data') or []:
        if not isinstance(g, dict):
            continue
        name = str(g.get('name') or 'Unknown')
        kind = g.get('type')
        if kind == ITEM_TXT:
            item = Item(ITEM_TXT, str(g.get('data', '')), name,
                        is_txr=bool(g.get('is_txr', False)))
        elif kind in (ITEM_IMG, ITEM_PAGE):
            path = resolve(str(g.get('filename', '')))
            if path is None:
                log.warning("Kayıtta eksik dosya atlandı: %s", g.get('filename'))
                continue
            try:
                page = int(g.get('page_index', 0) or 0)
            except (TypeError, ValueError):
                page = 0
            item = Item(kind, path, name, page_index=page)
        else:
            continue
        if not note.add_item(item):
            log.warning("Öğe limiti aşıldı, kalan öğeler atlandı.")
            break
    return note

# ======================================================================
# renderers
# ======================================================================
"""Belge ve resim işleme: sayfa render, önbellek, Office dönüştürme.

PDF ve diğer sayfalı biçimler PyMuPDF (fitz) ile, Office belgeleri LibreOffice ile
PDF'e çevrilip aynı yoldan gösterilir. Resimler QImage ile okunur.
"""



try:
    import fitz  # PyMuPDF
    PDF_SUPPORT = True
except ImportError:  # pragma: no cover
    fitz = None
    PDF_SUPPORT = False

log = logging.getLogger("copya.render")

KIND_IMAGE = 'image'
KIND_PNF = 'pnf'
KIND_PAGED = 'paged'
KIND_OFFICE = 'office'
KIND_TEXT = 'text'


class ConversionError(Exception):
    """Belge dönüştürülemedi; mesaj kullanıcıya gösterilebilir."""


def classify(path: str):
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXTS:
        return KIND_IMAGE
    if ext in TEXT_EXTS:
        return KIND_TEXT
    if ext in PNF_EXTS:
        return KIND_PNF
    if ext in PAGED_EXTS:
        return KIND_PAGED
    if ext in OFFICE_EXTS:
        return KIND_OFFICE
    return None


def trim_pixmap_by_alpha(pixmap: QPixmap) -> QPixmap:
    """Şeffaf kenarları kırpar (mevcut görünümü korur)."""
    if pixmap.isNull():
        return pixmap
    mask = pixmap.mask()
    if mask.isNull():
        return pixmap
    rect = QRegion(QBitmap(mask)).boundingRect()
    if rect.isEmpty():
        return pixmap
    rect = rect.intersected(pixmap.rect())
    return pixmap.copy(rect)


class LRUCache:
    def __init__(self, size: int, on_evict=None):
        self.size = size
        self.on_evict = on_evict
        self._data = OrderedDict()

    def get(self, key):
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def put(self, key, value):
        self._data[key] = value
        self._data.move_to_end(key)
        while len(self._data) > self.size:
            _, old = self._data.popitem(last=False)
            if self.on_evict:
                self.on_evict(old)

    def clear(self):
        while self._data:
            _, old = self._data.popitem(last=False)
            if self.on_evict:
                self.on_evict(old)


def _close_doc(doc):
    try:
        doc.close()
    except Exception as e:  # kapatma hatası kritik değil
        log.debug("Belge kapatılamadı: %s", e)


class DocumentRenderer:
    """Açık belgeleri ve render edilmiş sayfaları önbellekte tutar."""

    def __init__(self):
        self._docs = LRUCache(OPEN_DOCUMENT_CACHE_SIZE, on_evict=_close_doc)
        self._pages = LRUCache(PAGE_CACHE_SIZE)
        self._images = LRUCache(IMAGE_CACHE_SIZE)

    def _open(self, path: str):
        if not PDF_SUPPORT:
            raise ConversionError("Sayfalı belgeler için PyMuPDF (fitz) gereklidir.")
        doc = self._docs.get(path)
        if doc is None:
            doc = fitz.open(path)
            self._docs.put(path, doc)
        return doc

    def page_count(self, path: str) -> int:
        return len(self._open(path))

    def render_page(self, path: str, index: int) -> QPixmap:
        key = (path, index)
        cached = self._pages.get(key)
        if cached is not None:
            return cached
        try:
            doc = self._open(path)
            if not 0 <= index < len(doc):
                return QPixmap()
            zoom = RENDER_DPI / 72
            pix = doc.load_page(index).get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                         QImage.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(img)
        except Exception as e:
            log.warning("Sayfa render edilemedi (%s #%s): %s", path, index, e)
            return QPixmap()
        self._pages.put(key, pixmap)
        return pixmap

    def image(self, path: str) -> QPixmap:
        cached = self._images.get(path)
        if cached is not None:
            return cached
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self._images.put(path, pixmap)
        return pixmap

    def close(self):
        self._pages.clear()
        self._images.clear()
        self._docs.clear()


# --- Office dönüştürme ---

def find_office():
    for exe in ("soffice", "libreoffice"):
        found = shutil.which(exe)
        if found:
            return found
    return None


def convert_to_pdf(src: str, out_dir: str) -> str:
    """LibreOffice ile belgeyi PDF'e çevirir. Bulunamazsa ConversionError fırlatır."""
    exe = find_office()
    if exe is None:
        raise ConversionError(
            "Bu belge türünü göstermek için LibreOffice (soffice) kurulu olmalı.")

    profile = tempfile.mkdtemp(prefix='copya_lo_')
    try:
        subprocess.run(
            [exe, f"-env:UserInstallation={Path(profile).as_uri()}",
             "--headless", "--convert-to", "pdf", "--outdir", out_dir, src],
            check=True, timeout=OFFICE_TIMEOUT_S,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.TimeoutExpired:
        raise ConversionError("Belge dönüştürme zaman aşımına uğradı.")
    except (subprocess.CalledProcessError, OSError) as e:
        raise ConversionError(f"Belge dönüştürülemedi: {e}")
    finally:
        shutil.rmtree(profile, ignore_errors=True)

    out = os.path.join(out_dir, os.path.splitext(os.path.basename(src))[0] + '.pdf')
    if not os.path.isfile(out):
        raise ConversionError("Dönüştürülen PDF oluşturulamadı.")
    return out

# ======================================================================
# storage
# ======================================================================
"""Çalışma alanı (copi klasörü) ve .copya arşiv kaydet/yükle işlemleri.

Güvenlik kuralları:
- Arşiv içindeki dosya adları yalnızca temel ad (basename) olarak kullanılır;
  mutlak yol veya '..' ile klasör dışına çıkılamaz.
- Arşiv önce geçici bir klasöre açılıp doğrulanır. Doğrulama başarılı olmadan
  mevcut çalışma alanı silinmez.
"""


log = logging.getLogger("copya.storage")


class ArchiveError(Exception):
    """Kullanıcıya gösterilebilir arşiv/çalışma alanı hatası."""


def safe_basename(name) -> str:
    base = os.path.basename(str(name).replace("\\", "/"))
    if base in ("", ".", ".."):
        raise ArchiveError(f"Geçersiz dosya adı: {name!r}")
    return base


def _clear_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
    for name in os.listdir(path):
        full = os.path.join(path, name)
        try:
            if os.path.isdir(full) and not os.path.islink(full):
                shutil.rmtree(full)
            else:
                os.unlink(full)
        except OSError as e:
            log.warning("Silinemedi %s: %s", full, e)


class Workspace:
    def __init__(self, export_dir: str):
        self.export_dir = export_dir
        self.copi_dir = os.path.join(export_dir, 'copi')
        self.clip_dir = os.path.join(export_dir, 'temp_clip')
        _clear_dir(self.copi_dir)
        _clear_dir(self.clip_dir)

    # --- dosya işlemleri ---

    def import_file(self, src: str) -> str:
        """Kaynağı çalışma alanına benzersiz bir adla kopyalar ve yolunu döndürür."""
        dst = os.path.join(self.copi_dir, f"{uuid.uuid4()}_{safe_basename(src)}")
        shutil.copy2(src, dst)
        return dst

    def write_bytes(self, data: bytes, name: str) -> str:
        dst = os.path.join(self.copi_dir, f"{uuid.uuid4()}_{safe_basename(name)}")
        with open(dst, 'wb') as f:
            f.write(data)
        return dst

    def clip_path(self, name: str) -> str:
        os.makedirs(self.clip_dir, exist_ok=True)
        return os.path.join(self.clip_dir, safe_basename(name))

    def resolve(self, filename: str):
        """Kayıttaki dosya adını çalışma alanındaki tam yola çevirir (yoksa None)."""
        try:
            path = os.path.join(self.copi_dir, safe_basename(filename))
        except ArchiveError:
            return None
        return path if os.path.isfile(path) else None

    # --- kaydetme ---

    def save_archive(self, notes: List[Note], dest: str) -> None:
        """Yalnızca notların kullandığı dosyaları paketler (yetim dosyalar dahil edilmez)."""
        payload = {'notes': [note_to_dict(n) for n in notes]}
        used = set()
        for note in notes:
            for item in note.items:
                if item.type in (ITEM_IMG, ITEM_PAGE) and item.content:
                    used.add(os.path.basename(item.content))

        tmp = dest + '.tmp'
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('data.json', json.dumps(payload, ensure_ascii=False, indent=2))
            for name in sorted(used):
                path = os.path.join(self.copi_dir, name)
                if os.path.isfile(path):
                    zf.write(path, name)
        os.replace(tmp, dest)

    # --- yükleme ---

    def load_archive(self, path: str) -> List[Note]:
        """Arşivi doğrular, başarılıysa çalışma alanını değiştirir ve notları döndürür."""
        staging = tempfile.mkdtemp(prefix='copya_', dir=self.export_dir)
        try:
            self._extract_safely(path, staging)

            data_path = os.path.join(staging, 'data.json')
            if not os.path.isfile(data_path):
                raise ArchiveError("Arşivde data.json bulunamadı.")
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
            except (ValueError, UnicodeDecodeError) as e:
                raise ArchiveError(f"data.json okunamadı: {e}")

            raw_notes = payload.get('notes') if isinstance(payload, dict) else None
            if not isinstance(raw_notes, list):
                raise ArchiveError("Geçersiz proje yapısı.")

            # Doğrulama tamam: şimdi mevcut çalışma alanını değiştir.
            _clear_dir(self.copi_dir)
            for name in os.listdir(staging):
                if name != 'data.json':
                    shutil.move(os.path.join(staging, name), os.path.join(self.copi_dir, name))

            notes = []
            for raw in raw_notes[:MAX_NOTES]:
                try:
                    notes.append(note_from_dict(raw, self.resolve))
                except ValueError as e:
                    log.warning("Geçersiz not atlandı: %s", e)
            return notes
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    def _extract_safely(self, archive: str, target: str) -> None:
        try:
            zf = zipfile.ZipFile(archive)
        except (zipfile.BadZipFile, OSError) as e:
            raise ArchiveError(f"Dosya geçerli bir .copya arşivi değil: {e}")

        with zf:
            infos = [i for i in zf.infolist() if not i.is_dir()]
            if len(infos) > ARCHIVE_MAX_MEMBERS:
                raise ArchiveError("Arşivde çok fazla dosya var.")
            if sum(i.file_size for i in infos) > ARCHIVE_MAX_BYTES:
                raise ArchiveError("Arşiv açıldığında çok büyük olur.")

            for info in infos:
                name = safe_basename(info.filename)
                with zf.open(info) as src, open(os.path.join(target, name), 'wb') as dst:
                    shutil.copyfileobj(src, dst)

# ======================================================================
# tooltips
# ======================================================================
"""Düğmelerin Türkçe açıklamaları. Fare düğmenin üzerine geldiğinde siyah zeminli,
beyaz yazılı ipucu olarak görünür."""


TIPS = {
    # Üst araç çubuğu
    "file": "Dosya: Kayıtlı bir .copya projesini açar.",
    "save": "Kaydet: Projeyi son kullanılan dosyaya kaydeder. Dosya yoksa 'Farklı kaydet' penceresi açılır.",
    "add": "Ekle: Boş bir metin notu oluşturur.",
    "gallery": "Galeri: Resim ve metin dosyalarından galeri notu oluşturur. Bir galeri açıkken o galeriye öğe ekler.",
    "belge": "Belge: PDF, Word, Excel, PowerPoint, PNF ve resim dosyalarını sayfalı belge olarak açar.",
    "nav": "Sayfa listesi: Açık galeri veya belgede istediğin sayfaya geçmeni sağlar.",
    "auto_scroll": "Otomatik kaydırma (okuma modu): Açık notu seçilen hızda kendiliğinden kaydırır. Tekrar basınca durur.",
    "speed": "Kaydırma hızı: Otomatik kaydırma hızını seçer.",
    "doc_size": "Belge boyutu: Açık belgenin sayfa genişliğini yüzde olarak ayarlar.",
    "toolbar_delete": "Sil: Açık notu kalıcı olarak siler.",
    "toolbar_min": f"Küçült: Açık notu kapatıp ızgaraya döner. Kısayol: {COLLAPSE_SHORTCUT}",
    "toolbar_copy": "Kopyala: Açık notun içeriğini panoya kopyalar.",
    "export": "Dışa aktar: Tüm projeyi yeni bir .copya dosyası olarak kaydeder.",
    "switcher": "Copy: Kavram program geçiş menüsünü açar.",

    # Not kartı
    "note_title": "Not başlığı: Notun adını buraya yazabilirsin.",
    "note_copy": "Kopyala: Notu panoya kopyalar. Metin notları düz metin olarak, galeri ve belgeler dosya olarak kopyalanır.",
    "note_max": "Büyüt: Notu tam ekranda açar.",
    "note_delete": "Sil: Bu notu kalıcı olarak siler.",

    # Galeri ve belge satırları
    "item_delete": "Öğeyi sil: Bu resmi veya sayfayı listeden çıkarır.",
    "item_up": "Yukarı taşı: Öğeyi bir sıra yukarı alır.",
    "item_down": "Aşağı taşı: Öğeyi bir sıra aşağı indirer.",
    "item_num": "Sıra: Tıklayınca öğenin sırasını doğrudan seçebilirsin.",

    # Belge sayfası
    "doc_page": "Sayfa numarası: Belgenin hangi sayfada olduğunu gösterir.",
}


def set_tip(widget, key: str) -> None:
    widget.setToolTip(TIPS[key])


def install_tooltip_palette() -> None:
    """Tüm ipuçlarını siyah zeminli, beyaz yazılı yapar. Diğer pencereleri etkilemez."""
    palette = QToolTip.palette()
    palette.setColor(QPalette.ToolTipBase, QColor("#000000"))
    palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
    QToolTip.setPalette(palette)

# ======================================================================
# viewers
# ======================================================================
"""Resim ve sayfa görüntüleyicileri (yakınlaştırma, kaydırma, kart)."""



class DocumentImageWidget(QWidget):
    """Belgede tek sayfayı, belge boyutu oranında çizer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = QPixmap()
        self.doc_size = DEFAULT_DOC_SIZE
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_pixmap(self, pixmap: QPixmap, doc_size) -> None:
        self.pixmap = pixmap
        self.doc_size = doc_size
        self.update_size()
        self.update()

    def update_size(self) -> None:
        if self.pixmap.isNull():
            return
        scroll = self.get_parent_scroll()
        if scroll:
            view_w = scroll.viewport().width() - 40
        else:
            view_w = self.parentWidget().width() if self.parentWidget() else 800
        if view_w <= 0:
            view_w = 800
        img_w, img_h = self.pixmap.width(), self.pixmap.height()
        if img_w == 0:
            return
        scale = (view_w * self.doc_size / DEFAULT_DOC_SIZE) / img_w
        self.setFixedSize(int(img_w * scale), int(img_h * scale))

    def get_parent_scroll(self):
        p = self.parentWidget()
        while p:
            if isinstance(p, QScrollArea):
                return p
            p = p.parentWidget()
        return None

    def paintEvent(self, event):
        if self.pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(self.rect(), self.pixmap)


class ZoomableImageWidget(QWidget):
    """Orta tuşla kaydırma, tekerlekle yakınlaştırma, sağ tıkla sığdırma."""

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.pixmap = trim_pixmap_by_alpha(pixmap)
        self.scale_factor = 1.0
        self.offset = QPoint(0, 0)
        self.last_mouse_pos = QPoint()
        self.panning = False

        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        self.setStyleSheet("background-color: #000000;")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), Qt.black)
        if self.pixmap.isNull():
            return

        scaled_w = self.pixmap.width() * self.scale_factor
        scaled_h = self.pixmap.height() * self.scale_factor
        draw_x = self.width() / 2 - scaled_w / 2 + self.offset.x()
        draw_y = self.height() / 2 - scaled_h / 2 + self.offset.y()
        if (draw_x + scaled_w < 0 or draw_x > self.width()
                or draw_y + scaled_h < 0 or draw_y > self.height()):
            return
        painter.drawPixmap(QRectF(draw_x, draw_y, scaled_w, scaled_h),
                           self.pixmap, QRectF(self.pixmap.rect()))

    def wheelEvent(self, event):
        if self.pixmap.isNull():
            return
        vec = event.pos() - QPoint(self.width() // 2, self.height() // 2)
        zoom_change = 1.1 if event.angleDelta().y() > 0 else 0.9
        new_scale = min(50.0, max(0.05, self.scale_factor * zoom_change))
        factor = new_scale / self.scale_factor
        self.offset = self.offset * factor + vec * (1 - factor)
        self.scale_factor = new_scale
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.fit_logic()
        elif event.button() == Qt.MiddleButton:
            self.panning = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.panning:
            self.offset += event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        self.fit_logic()
        super().resizeEvent(event)

    def fit_logic(self):
        if self.pixmap.isNull() or self.width() == 0:
            return
        scale_w = self.width() / self.pixmap.width()
        viewport_h = 1000.0
        screen = QApplication.primaryScreen()
        if screen:
            viewport_h = screen.size().height() * 0.8
        parent = self.parentWidget()
        while parent:
            if isinstance(parent, QScrollArea):
                viewport_h = parent.viewport().height()
                break
            parent = parent.parentWidget()

        scale_h = viewport_h / self.pixmap.height()
        self.scale_factor = min(1.0, scale_w, scale_h)
        self.offset = QPoint(0, 0)
        new_height = int(self.pixmap.height() * self.scale_factor)
        if abs(self.height() - new_height) > 2:
            self.setFixedHeight(new_height)
        self.update()


DARK_MENU_STYLE = """
    QMenu { background-color: #333; color: white; border: 1px solid #555; padding: 4px; }
    QMenu::item { padding: 5px 20px; }
    QMenu::item:selected { background-color: #555; }
"""

DARK_BTN_STYLE = """
    QPushButton { background-color: #2a2a2a; color: #dddddd; border: 1px solid #555; border-radius: 4px;
                  padding: 3px 8px; font-weight: bold; }
    QPushButton:hover { background-color: #3a3a3a; }
    QPushButton:pressed { background-color: #444; }
    QPushButton:checked { background-color: #5a1f1f; border: 1px solid #8a3a3a; color: #ffb3b3; }
"""


# --- Renk Paneli (Drawing_editor'dan uyarlandı; tek renk seçimi, karıştırma yok) ---

class ColorPickerWidget(QWidget):
    """Renk tekerleği + parlaklık kaydırıcısı + HEX alanı."""
    colorChanged = pyqtSignal(object)

    def __init__(self, initial_color=None, parent=None):
        super().__init__(parent)
        self.diameter = 150
        self.radius = self.diameter // 2
        self.setFixedSize(250, 212)

        init = initial_color or QColor(WHITE_HEX)
        h, s, v, _ = init.getHsvF()
        self.h = max(0.0, h) * 360.0
        self.s = max(0.0, s)
        self.v = max(0.0, v)

        self.wheel = QImage(self.diameter, self.diameter, QImage.Format_ARGB32)
        self._generate_wheel()

        self.slider = QSlider(Qt.Vertical, self)
        self.slider.setRange(0, 100)
        self.slider.setValue(int(self.v * 100))
        self.slider.setGeometry(self.diameter + 20, 10, 20, self.diameter)
        self.slider.valueChanged.connect(self._on_slider)

        self.brightness_label = QLabel(self)
        self.brightness_label.setGeometry(self.diameter + 50, 10, 40, 20)
        self.brightness_label.setStyleSheet("color: white; background: transparent;")

        self.preview = QLabel(self)
        self.preview.setGeometry(self.diameter + 50, 35, 40, 40)

        self.hex_input = QLineEdit(self)
        self.hex_input.setGeometry(10, self.diameter + 22, 120, 26)
        self.hex_input.setMaxLength(6)
        self.hex_input.setPlaceholderText("RRGGBB")
        self.hex_input.setStyleSheet(
            "QLineEdit { background-color: #000; color: #FFF; border: 1px solid #444; border-radius: 4px; "
            "padding: 2px 5px; font-family: monospace; font-size: 12px; }"
        )
        self.hex_input.textEdited.connect(self._on_hex_edited)
        self.hex_input.returnPressed.connect(self._on_hex_entered)


        self._refresh()

    # -- durum --
    def current_color(self):
        return QColor.fromHsvF(self.h / 360.0, self.s, self.v)

    def set_color(self, color):
        h, s, v, _ = color.getHsvF()
        self.h = max(0.0, h) * 360.0
        self.s = max(0.0, s)
        self.v = max(0.0, v)
        self.slider.blockSignals(True)
        self.slider.setValue(int(self.v * 100))
        self.slider.blockSignals(False)
        self._refresh()

    def _emit(self):
        self._refresh()
        self.colorChanged.emit(self.current_color())

    def _refresh(self, update_hex=True):
        c = self.current_color()
        hue_hex = QColor.fromHsvF(self.h / 360.0, 1.0, 1.0).name()
        self.slider.setStyleSheet(f"""
            QSlider::groove:vertical {{ border: none; width: 4px; background: qlineargradient(x1:0, y1:1, x2:0, y2:0, stop:0 #000000, stop:0.5 {hue_hex}, stop:1 #FFFFFF); margin: 0px; }}
            QSlider::handle:vertical {{ background: {hue_hex}; border: 2px solid #FFFFFF; width: 12px; height: 12px; margin: -6px 0; border-radius: 6px; }}
        """)
        self.preview.setStyleSheet(
            f"QLabel {{ background-color: {c.name()}; border: 2px solid #FFFFFF; border-radius: 4px; }}"
        )
        self.brightness_label.setText(f"{int(self.v * 100)}%")
        if update_hex:
            self.hex_input.setText(c.name().upper()[1:])
        self.update()

    # -- olaylar --
    def _on_slider(self, val):
        self.v = val / 100.0
        self._emit()

    def _on_hex_edited(self, text):
        clean = "".join(ch for ch in text.upper() if ch in "0123456789ABCDEF")[:6]
        if clean != text:
            self.hex_input.setText(clean)
        if len(clean) == 6:
            c = QColor("#" + clean)
            if c.isValid():
                self.set_color(c)
                self.colorChanged.emit(self.current_color())

    def _on_hex_entered(self):
        clean = self.hex_input.text().strip().upper()
        if len(clean) == 6:
            c = QColor("#" + clean)
            if c.isValid():
                self.set_color(c)
                self.colorChanged.emit(self.current_color())

    def _generate_wheel(self):
        center = self.radius
        for y in range(self.diameter):
            for x in range(self.diameter):
                dx = x - center
                dy = y - center
                r = math.sqrt(dx * dx + dy * dy)
                if r <= self.radius:
                    hue = (math.degrees(math.atan2(dy, dx)) + 360) % 360
                    self.wheel.setPixelColor(x, y, QColor.fromHsvF(hue / 360.0, r / self.radius, 1.0))
                else:
                    self.wheel.setPixelColor(x, y, QColor(0, 0, 0, 0))

    def _pick(self, pos):
        dx = (pos.x() - 10) - self.radius
        dy = (pos.y() - 10) - self.radius
        r = math.sqrt(dx * dx + dy * dy)
        if r <= self.radius:
            self.h = (math.degrees(math.atan2(dy, dx)) + 360) % 360
            self.s = r / self.radius
            return True
        return False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._pick(event.pos()):
            self._emit()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._pick(event.pos()):
            self._emit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.drawImage(10, 10, self.wheel)
        rad = math.radians(self.h)
        sat_r = self.s * self.radius
        sx = 10 + self.radius + sat_r * math.cos(rad)
        sy = 10 + self.radius + sat_r * math.sin(rad)
        p.setPen(QPen(Qt.black, 2))
        p.setBrush(Qt.white)
        p.drawEllipse(QPoint(int(sx), int(sy)), 5, 5)
        p.end()


class SavedColorsWidget(QWidget):
    """Renk listesi: ilk hücre Varsayılan, sonra seçilen renkler (HEX kodlu). 4 sütun, küçük hücreler."""
    colorChosen = pyqtSignal(object)   # QColor veya None (varsayılan)
    colorRemoved = pyqtSignal(int)     # seçilen renkler listesindeki indeks

    CELL_W = 56
    CELL_H = 34
    COLS = 4
    MARGIN = 4

    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.colors = colors          # ana pencerenin listesiyle aynı nesne
        self.delete_mode = False
        self.hover = -1
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self.refresh()

    def _items(self):
        return [None] + list(self.colors)

    def refresh(self):
        count = len(self.colors) + 1
        rows = max(1, (count + self.COLS - 1) // self.COLS)
        self.setFixedSize(self.MARGIN * 2 + self.COLS * self.CELL_W,
                          self.MARGIN * 2 + rows * self.CELL_H)
        self.update()

    def _cell_rect(self, i):
        r, c = divmod(i, self.COLS)
        return QRect(self.MARGIN + c * self.CELL_W, self.MARGIN + r * self.CELL_H,
                     self.CELL_W - 4, self.CELL_H - 4)

    def _index_at(self, pos):
        for i in range(len(self.colors) + 1):
            if self._cell_rect(i).contains(pos):
                return i
        return -1

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for i, hex_code in enumerate(self._items()):
            rect = self._cell_rect(i)
            is_hover = (i == self.hover)
            swatch = QRect(rect.x() + 3, rect.y() + 2, rect.width() - 6, 16)
            if hex_code is None:
                p.setBrush(QBrush(QColor(WHITE_HEX)))
                label = "Varsayılan"
            else:
                p.setBrush(QBrush(QColor(hex_code)))
                label = hex_code.upper()
            p.setPen(QPen(Qt.white if is_hover else QColor("#555555"), 2 if is_hover else 1))
            p.drawRoundedRect(swatch, 3, 3)
            if self.delete_mode and is_hover and hex_code is not None:
                p.setPen(QPen(QColor("#FF5555"), 2))
                p.drawLine(swatch.topLeft(), swatch.bottomRight())
                p.drawLine(swatch.topRight(), swatch.bottomLeft())
            p.setPen(QColor("#aaaaaa"))
            p.setFont(QFont("Monospace", 7))
            p.drawText(QRect(rect.x(), rect.y() + 19, rect.width(), 12), Qt.AlignCenter, label)
        p.end()

    def mouseMoveEvent(self, event):
        self.hover = self._index_at(event.pos())
        self.update()

    def leaveEvent(self, event):
        self.hover = -1
        self.update()

    def mousePressEvent(self, event):
        i = self._index_at(event.pos())
        if i < 0:
            return
        if i == 0:
            # Varsayılan hücresi: silinemez, sadece seçilir
            if event.button() == Qt.LeftButton:
                self.colorChosen.emit(None)
            return
        idx = i - 1
        if event.button() == Qt.LeftButton:
            if self.delete_mode:
                self.colorRemoved.emit(idx)
            else:
                self.colorChosen.emit(QColor(self.colors[idx]))
        elif event.button() == Qt.RightButton:
            menu = QMenu(self)
            menu.setStyleSheet(DARK_MENU_STYLE)
            copy_action = menu.addAction(f"HEX kopyala: {self.colors[idx]}")
            delete_action = menu.addAction("Sil")
            chosen = menu.exec_(event.globalPos())
            if chosen == delete_action:
                self.colorRemoved.emit(idx)
            elif chosen == copy_action:
                QApplication.clipboard().setText(self.colors[idx])


class ColorPanel(QFrame):
    """Color butonuna basınca açılan panel: seçici, renk listesi ve seçili renk butonu."""
    colorApplied = pyqtSignal(object)    # QColor veya None (varsayılan)
    colorConfirmed = pyqtSignal(object)  # seçiciyle elle seçilen renk (listeye eklenir)
    colorRemoved = pyqtSignal(int)

    def __init__(self, saved_colors, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("colorPanel")
        self.setStyleSheet("#colorPanel { background-color: #222; border: 1px solid #555; border-radius: 8px; }")
        self.setFixedWidth(256)
        self._picker_touched = False
        self._current = QColor(WHITE_HEX)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.picker = ColorPickerWidget(QColor(WHITE_HEX), self)
        self.picker.colorChanged.connect(self._on_picker)
        layout.addWidget(self.picker)

        title = QLabel("Seçilen Renkler", self)
        title.setStyleSheet("color: #aaa; font-weight: bold;")
        layout.addWidget(title)

        self.saved = SavedColorsWidget(saved_colors, self)
        self.saved.colorChosen.connect(self._on_chosen)
        self.saved.colorRemoved.connect(self.colorRemoved.emit)

        scroll = QScrollArea(self)
        scroll.setWidget(self.saved)
        scroll.setWidgetResizable(False)
        scroll.setFixedHeight(120)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #222; }")
        layout.addWidget(scroll)

        row = QHBoxLayout()
        row.addStretch()
        self.delete_btn = KButton("Sil", self)
        self.delete_btn.setStyleSheet(DARK_BTN_STYLE)
        self.delete_btn.setCheckable(True)
        self.delete_btn.setToolTip("Silme modu: açıkken renge tıklayınca renk silinir")
        self.delete_btn.toggled.connect(self._toggle_delete)
        row.addWidget(self.delete_btn)
        layout.addLayout(row)

        # Seçili renk: panelin altında buton olarak durur, tıklanınca uygulanır
        self.current_btn = KButton(self)
        self.current_btn.setFixedHeight(28)
        self.current_btn.clicked.connect(self._on_current_clicked)
        layout.addWidget(self.current_btn)
        self._update_current_btn(self._current)

    def open_with(self, color):
        self._picker_touched = False
        self.picker.set_color(color)
        self._update_current_btn(color)
        self.saved.refresh()
        self.saved.delete_mode = False
        self.delete_btn.setChecked(False)

    def _update_current_btn(self, color):
        self._current = QColor(color)
        fg = "#000000" if color.lightness() > 128 else "#FFFFFF"
        self.current_btn.setText(color.name().upper())
        self.current_btn.setStyleSheet(
            f"QPushButton {{ background-color: {color.name()}; color: {fg}; border: 2px solid #888; "
            "border-radius: 4px; font-family: monospace; font-weight: bold; }"
            "QPushButton:hover { border: 2px solid #FFFFFF; }"
        )

    def _toggle_delete(self, checked):
        self.saved.delete_mode = checked
        self.saved.update()

    def _on_picker(self, color):
        self._picker_touched = True
        self._update_current_btn(color)
        self.colorApplied.emit(color)

    def _on_current_clicked(self):
        self.colorApplied.emit(QColor(self._current))
        self.hide()

    def _on_chosen(self, color):
        self.colorApplied.emit(color)
        self.hide()

    def hideEvent(self, event):
        # Seçiciyle yeni bir renk seçildiyse listeye eklenir
        if self._picker_touched:
            self.colorConfirmed.emit(QColor(self._current))
            self._picker_touched = False
        super().hideEvent(event)


class ImageCardWidget(QWidget):
    """Galeri/belge kartının kapağı. Sağ tıkla text'teki renk paneli açılır."""

    def __init__(self, color=DEFAULT_COVER, on_menu=None, parent=None):
        super().__init__(parent)
        self.setMouseTracking(False)
        self.setFixedHeight(CARD_HEIGHT)
        self.color = QColor(color)
        self.on_menu = on_menu

    def set_color(self, hex_code):
        self.color = QColor(hex_code)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.color)
        painter.setPen(QColor("#444"))
        r = self.rect()
        painter.drawLine(0, r.height() - 1, r.width(), r.height() - 1)
        painter.end()

    def contextMenuEvent(self, event):
        if self.on_menu is not None:
            self.on_menu(event.globalPos())


class ImagePreviewDialog(QDialog):
    """Bir resmi/sayfayı tam ekran ve yakınlaştırılabilir gösterir."""

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Preview")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.showMaximized()
        self.setStyleSheet("background: black;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 10, 0)
        close_btn = KButton("X")
        close_btn.setStyleSheet(PREVIEW_CLOSE_STYLE)
        close_btn.setFixedSize(40, 40)
        close_btn.clicked.connect(self.close)
        top_layout.addStretch()
        top_layout.addWidget(close_btn)
        layout.addWidget(top_bar)

        zoom = ZoomableImageWidget(pixmap)
        layout.addWidget(zoom)
        QTimer.singleShot(10, zoom.fit_logic)

# ======================================================================
# text_widgets
# ======================================================================
"""Metin alanları: otomatik yükseklikli görüntüleyici ve düzenlenebilir not alanı."""



log = logging.getLogger("copya.text")

_CENTER_RE = re.compile(r'^\s*<center>(.*)</center>\s*$', re.IGNORECASE)


WHITE_HEX = "#FFFFFF"
TXR_HEADER = "<!--kavram-txr:2-->"
_TXR_TOKEN_RE = re.compile(r'\\(.)|</b>|<b>|<c=(#[0-9A-Fa-f]{6})>|</c>', re.S)


def txr_escape(text):
    return text.replace('\\', '\\\\').replace('<', '\\<')


def _txr_fmt(bold, color):
    fmt = QTextCharFormat()
    if bold:
        fmt.setFontWeight(QFont.Bold)
    if color:
        fmt.setForeground(QBrush(QColor(color)))
    return fmt


def txr_load(edit, content):
    """.txr içeriğini QTextEdit'e yükler (kalın, renk, ortalama).
    Başlık yoksa eski düz biçim okunur; yalnızca <center> etiketleri yorumlanır."""
    edit.clear()
    cursor = edit.textCursor()
    rich = False
    first, _, rest = content.partition('\n')
    if first.strip() == TXR_HEADER:
        rich = True
        content = rest
    for i, raw in enumerate(content.split('\n')):
        line = raw[:-1] if raw.endswith('\r') else raw
        centered = False
        m = _CENTER_RE.match(line)
        if m:
            centered, line = True, m.group(1)
        if i > 0:
            cursor.insertBlock()
        if rich:
            bold, color, pos = False, None, 0
            for tok in _TXR_TOKEN_RE.finditer(line):
                if tok.start() > pos:
                    cursor.insertText(line[pos:tok.start()], _txr_fmt(bold, color))
                pos = tok.end()
                t = tok.group(0)
                if t[0] == '\\':
                    cursor.insertText(tok.group(1), _txr_fmt(bold, color))
                elif t == '<b>':
                    bold = True
                elif t == '</b>':
                    bold = False
                elif t == '</c>':
                    color = None
                elif tok.group(2):
                    color = tok.group(2).upper()
            if pos < len(line):
                cursor.insertText(line[pos:], _txr_fmt(bold, color))
        else:
            cursor.insertText(line, QTextCharFormat())
        fmt = cursor.blockFormat()
        fmt.setAlignment(Qt.AlignCenter if centered else Qt.AlignLeft)
        cursor.setBlockFormat(fmt)
    edit.setTextCursor(cursor)


def _char_styles(doc, block):
    text = block.text()
    cur = QTextCursor(doc)
    styles = []
    for pos in range(len(text)):
        cur.setPosition(block.position() + pos)
        cur.setPosition(block.position() + pos + 1, QTextCursor.KeepAnchor)
        fmt = cur.charFormat()
        bold = fmt.hasProperty(QTextFormat.FontWeight) and fmt.fontWeight() >= QFont.Bold
        color = None
        if fmt.hasProperty(QTextFormat.ForegroundBrush):
            c = fmt.foreground().color().name().upper()
            if c != WHITE_HEX:
                color = c
        styles.append((bool(bold), color))
    return text, styles


def _txr_runs(text, styles):
    runs = []
    for ch, st in zip(text, styles):
        if runs and runs[-1][1] == st:
            runs[-1][0] += ch
        else:
            runs.append([ch, st])
    return runs


def _txr_rich_line(text, styles):
    parts, bold, color = [], False, None
    for seg, (b, c) in _txr_runs(text, styles):
        if b != bold or c != color:
            if color:
                parts.append('</c>')
            if bold:
                parts.append('</b>')
            if b:
                parts.append('<b>')
            if c:
                parts.append(f'<c={c}>')
            bold, color = b, c
        parts.append(txr_escape(seg))
    if color:
        parts.append('</c>')
    if bold:
        parts.append('</b>')
    return ''.join(parts)


def txr_serialize(doc):
    """Belgeyi .txr metnine çevirir. Kalın/renk yoksa düz (eski) biçim, varsa başlıklı zengin biçim."""
    plain, rich, has_inline = [], [], False
    block = doc.begin()
    while block.isValid():
        text, styles = _char_styles(doc, block)
        if any(b or c for b, c in styles):
            has_inline = True
        p = text
        r = _txr_rich_line(text, styles)
        if block.blockFormat().alignment() & Qt.AlignCenter:
            p, r = f"<center>{p}</center>", f"<center>{r}</center>"
        plain.append(p)
        rich.append(r)
        block = block.next()
    if has_inline:
        return TXR_HEADER + "\n" + "\n".join(rich)
    return "\n".join(plain)


class AutoResizingTextEdit(QTextEdit):
    """.txt / .txr içeriğini gösterir. .txr ise kalın, renk ve ortalama biçimlerini korur.

    `on_change(yeni_içerik)` her düzenlemede çağrılır (düzenleme modunda)."""

    def __init__(self, text: str, is_txr: bool = False, on_change=None, parent=None):
        super().__init__(parent)
        self.is_txr = is_txr
        self.on_change = on_change
        self.setReadOnly(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        self.setStyleSheet("""
            QTextEdit { background: #111; color: #ddd; border: 1px solid #444; padding: 10px; border-radius: 4px; }
        """)
        self.blockSignals(True)
        if is_txr or "<center>" in text:
            txr_load(self, text)
        else:
            self.setPlainText(text)
        self.blockSignals(False)
        self.adjust_height()
        self.textChanged.connect(self.on_text_changed)

    def get_clean_html_content(self) -> str:
        return txr_serialize(self.document())

    def on_text_changed(self):
        self.adjust_height()
        if self.on_change is not None:
            self.on_change(self.get_clean_html_content() if self.is_txr else self.toPlainText())

    def adjust_height(self):
        self.setFixedHeight(int(self.document().size().height() + 20))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_height()

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        edit_action = QAction("Düzenle", self)
        edit_action.triggered.connect(self.enable_editing)
        menu.insertAction(menu.actions()[0], edit_action)
        menu.insertSeparator(menu.actions()[1])
        menu.exec_(event.globalPos())

    def enable_editing(self):
        self.setReadOnly(False)
        self.setStyleSheet("""
            QTextEdit { background: #222; color: #fff; border: 1px solid #666; padding: 10px; border-radius: 4px; }
        """)
        self.setFocus()


class ImageOverlayTools(QWidget):
    """Metin içindeki resmin üzerinde beliren Sil / Büyüt araç çubuğu."""

    def __init__(self, parent=None, on_expand=None, on_delete=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(80, 35)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        btn_style = "QToolButton { background: rgba(0,0,0,200); color: white; border: 1px solid #777; border-radius: 3px; font-weight: bold; } QToolButton:hover { background: #000000; border-color: #999; }"
        expand_style = "QToolButton { background: rgba(0,0,0,200); color: white; border: 1px solid #777; border-radius: 3px; font-weight: bold; } QToolButton:hover { background: rgba(0,200,0,200); border-color: lime; }"

        self.btn_del = KToolButton()
        self.btn_del.setText("X")
        self.btn_del.setFixedSize(30, 30)
        self.btn_del.setStyleSheet(btn_style)
        self.btn_del.clicked.connect(on_delete)
        self.btn_exp = KToolButton()
        self.btn_exp.setText("_")
        self.btn_exp.setFixedSize(30, 30)
        self.btn_exp.setStyleSheet(expand_style)
        self.btn_exp.clicked.connect(on_expand)
        layout.addWidget(self.btn_del)
        layout.addWidget(self.btn_exp)


class InteractiveTextEdit(QTextEdit):
    """Metin notu düzenleyicisi. Üzerine gelinen gömülü resim için Sil/Büyüt gösterir."""

    def __init__(self, parent_note=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_note = parent_note
        self.setMouseTracking(True)
        self.setFont(QFont("Segoe UI", 13, QFont.DemiBold))
        self.overlay = ImageOverlayTools(self, on_expand=self.expand_current_image,
                                         on_delete=self.delete_current_image)
        self.overlay.hide()
        self.current_image_name = None
        self.current_cursor_position = -1

    def mouseMoveEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        fmt = cursor.charFormat()
        if fmt.isImageFormat():
            self.current_image_name = fmt.toImageFormat().name()
            self.current_cursor_position = cursor.position()
            rect = self.cursorRect(cursor)
            self.overlay.move(self.mapToGlobal(rect.topLeft() + QPoint(5, 5)))
            self.overlay.show()
            self.overlay.raise_()
        elif not self.overlay.geometry().contains(self.mapToGlobal(event.pos())):
            self.overlay.hide()
        super().mouseMoveEvent(event)

    def delete_current_image(self):
        if self.current_cursor_position == -1:
            return
        c = self.textCursor()
        c.setPosition(self.current_cursor_position)
        c.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)
        if not c.charFormat().isImageFormat():
            c.setPosition(self.current_cursor_position)
            c.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor)
        if c.charFormat().isImageFormat():
            c.removeSelectedText()
            self.overlay.hide()

    def expand_current_image(self):
        if not self.current_image_name:
            return
        resource = self.document().resource(QTextDocument.ImageResource,
                                            QUrl(self.current_image_name))
        pixmap = QPixmap()
        if isinstance(resource, QPixmap):
            pixmap = resource
        elif isinstance(resource, QImage):
            pixmap = QPixmap.fromImage(resource)
        if pixmap.isNull():
            return
        ImagePreviewDialog(pixmap, self).exec_()

# ======================================================================
# note_widget
# ======================================================================
"""Izgaradaki not kartı ve genişletilmiş (tam ekran) görünümü.

Veri `models.Note` içinde tutulur; bu sınıf yalnızca gösterim ve kullanıcı etkileşimini yönetir.
"""



log = logging.getLogger("copya.note")


def _tool_button(text, width, height, style, tip_key, font_size=None):
    btn = KToolButton()
    btn.setText(text)
    if font_size:
        btn.setFont(QFont("Segoe UI", font_size, QFont.Bold))
    btn.setFixedSize(width, height)
    btn.setStyleSheet(style)
    btn.setFocusPolicy(Qt.NoFocus)
    set_tip(btn, tip_key)
    return btn


class NoteWidget(QFrame):
    def __init__(self, parent_window, note: Note):
        super().__init__()
        self.parent_window = parent_window
        self.note = note
        self.is_expanded = False

        self.item_widgets = []
        self.active_scroll_area = None
        self.expanded_text_edit = None
        self.temp_large_edit = None
        self.doc_image_widget = None
        self.doc_page_label = None
        self.cached_expanded_widget = None
        self.text_edit = None
        self.image_card = None

        self._text_timer = QTimer(self)
        self._text_timer.setSingleShot(True)
        self._text_timer.setInterval(TEXT_DEBOUNCE_MS)
        self._text_timer.timeout.connect(self.flush_text)

        self._build_controls()
        self._setup_layout()
        self.setStyleSheet(NOTE_FRAME_STYLE)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setFixedHeight(NOTE_HEIGHT)

    # ------------------------------------------------------------------ kurulum

    def _build_controls(self):
        self.pkg_edit = QLineEdit(self.note.title)
        self.pkg_edit.setPlaceholderText("Note Title")
        self.pkg_edit.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.pkg_edit.setStyleSheet("QLineEdit { background: #1a1a1a; color: #ffffff; border: 1px solid #555; padding: 4px; border-radius: 4px; }")
        self.pkg_edit.textChanged.connect(lambda t: setattr(self.note, 'title', t))
        set_tip(self.pkg_edit, "note_title")

        self.copy_btn = _tool_button("/", 30, 30, NOTE_BUTTON_STYLE, "note_copy", 10)
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.max_btn = _tool_button("_", 30, 30, NOTE_BUTTON_STYLE, "note_max", 10)
        self.max_btn.clicked.connect(self.toggle_maximize)
        self.delete_btn = _tool_button("X", 40, 30, NOTE_DELETE_STYLE, "note_delete", 10)
        self.delete_btn.clicked.connect(self.delete_self)

        if self.note.is_media:
            self.image_card = ImageCardWidget(self.note.cover, self.open_cover_panel)
        else:
            self.text_edit = InteractiveTextEdit(self)
            self.text_edit.setHtml(self.note.text)
            self.text_edit.setPlaceholderText("Content")
            self.text_edit.setStyleSheet("QTextEdit { background: #1a1a1a; color: #dddddd; border: 1px solid #555; padding: 4px; border-radius: 4px; }")
            self.text_edit.textChanged.connect(self.on_text_changed)

    def _setup_layout(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(4)
        self.header_layout = QHBoxLayout()
        self.header_layout.setSpacing(4)
        self.main_layout.addLayout(self.header_layout)
        self.main_layout.addWidget(self.text_edit if self.text_edit is not None else self.image_card)

    def set_column_mode(self):
        while self.header_layout.count():
            item = self.header_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self.header_layout.addWidget(self.delete_btn)
        self.header_layout.addWidget(self.pkg_edit, 1)
        self.header_layout.addWidget(self.max_btn)
        self.header_layout.addWidget(self.copy_btn)
        for w in (self.delete_btn, self.pkg_edit, self.max_btn, self.copy_btn):
            w.show()

    # ------------------------------------------------------- metin senkronu

    def on_text_changed(self):
        """Her tuşta HTML üretmek yerine kısa bir gecikmeyle senkronize eder."""
        self._text_timer.start()

    def flush_text(self):
        """Bekleyen metin değişikliğini nota yazar (kaydetmeden ve geçişlerden önce çağrılır)."""
        self._text_timer.stop()
        if self.note.is_media:
            return
        source = None
        if self.is_expanded and self.temp_large_edit is not None:
            source = self.temp_large_edit
        elif self.text_edit is not None:
            source = self.text_edit
        if source is not None:
            self.note.text = source.toHtml()
        if self.is_expanded and self.parent_window.expanded_note_widget is self:
            self.parent_window.update_nav_button_text_mode(self)

    def update_text_from_expanded(self):
        if self.temp_large_edit is None or self.text_edit is None:
            return
        self._text_timer.stop()
        try:
            html = self.temp_large_edit.toHtml()
            self.note.text = html
            self.text_edit.blockSignals(True)
            self.text_edit.setHtml(html)
            self.text_edit.blockSignals(False)
        except RuntimeError as _e: # widget silinmiş olabilir
            kui.log_exc(_e)

    # ------------------------------------------------------- öğe işlemleri

    def item_pixmap(self, item) -> QPixmap:
        renderer = self.parent_window.renderer
        if item.type == ITEM_PAGE:
            return renderer.render_page(item.content, item.page_index)
        if item.type == ITEM_IMG:
            return renderer.image(item.content)
        return QPixmap()

    def remove_sub_item(self, index):
        # Not: önceki sürümde bu noktada çalışmayan bir solma animasyonu vardı
        # (bayrak hiç işaretlenmediği için). Arayüzü değiştirmemek adına kaldırıldı.
        self.finalize_removal(index)

    def finalize_removal(self, index):
        if not 0 <= index < len(self.note.items):
            return
        del self.note.items[index]
        new_len = len(self.note.items)
        target = 0 if new_len == 0 else (new_len - 1 if index >= new_len else index)
        self.invalidate_cache()
        self.parent_window.expand_note(self, maintain_scroll=True, target_item_index=target)

    def move_item_up(self, index):
        if index > 0:
            self.swap_items(index, index - 1)

    def move_item_down(self, index):
        if index < len(self.note.items) - 1:
            self.swap_items(index, index + 1)

    def swap_items(self, from_idx, to_idx):
        items = self.note.items
        if 0 <= from_idx < len(items) and 0 <= to_idx < len(items):
            items[from_idx], items[to_idx] = items[to_idx], items[from_idx]
            self.invalidate_cache()
            self.parent_window.expand_note(self, maintain_scroll=False, target_item_index=to_idx)

    def show_order_menu(self, btn, current_idx):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        menu.setFixedHeight(min(600, 35 * len(self.note.items) + 20))
        for i in range(len(self.note.items)):
            text = f"#{i + 1}" + (" <" if i == current_idx else "")
            action = menu.addAction(text)
            action.triggered.connect(lambda _checked=False, t=i: self.swap_items(current_idx, t))
        menu.exec_(btn.mapToGlobal(QPoint(0, btn.height())))

    # ------------------------------------------------------- genişletilmiş görünüm

    def invalidate_cache(self):
        if self.cached_expanded_widget is not None:
            self.cached_expanded_widget.deleteLater()
            self.cached_expanded_widget = None
        self.temp_large_edit = None
        self.doc_image_widget = None

    def get_or_create_expanded_content(self, scroll_val=0):
        if self.cached_expanded_widget is None:
            self.cached_expanded_widget = self._build_expanded(scroll_val)
        elif self.note.is_document and self.doc_image_widget is not None:
            try:
                self.doc_image_widget.doc_size = self.note.doc_size
                self.doc_image_widget.update_size()
            except RuntimeError as _e:
                kui.log_exc(_e)
        elif not self.note.is_media and self.temp_large_edit is not None:
            # Izgaradaki metin kapalıyken değiştiyse önbellekteki görünümü güncelle
            try:
                if self.temp_large_edit.toHtml() != self.note.text:
                    self.temp_large_edit.blockSignals(True)
                    self.temp_large_edit.setHtml(self.note.text)
                    self.temp_large_edit.blockSignals(False)
            except RuntimeError as _e:
                kui.log_exc(_e)
        return self.cached_expanded_widget

    def _build_expanded(self, scroll_val):
        self.item_widgets = []
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        if self.note.is_media:
            scroll = QScrollArea()
            scroll.setObjectName("expanded_scroll_area")
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

            content = QWidget()
            content.setStyleSheet("background-color: #444;")
            scroll_layout = QVBoxLayout(content)
            scroll_layout.setAlignment(Qt.AlignTop)

            if self.note.is_document:
                self._build_document_view(scroll_layout)
            else:
                scroll.verticalScrollBar().valueChanged.connect(self.parent_window.on_gallery_scroll)
                self._build_gallery_view(scroll_layout)

            scroll.setWidget(content)
            if scroll_val > 0 and not self.note.is_document:
                def restore():
                    try:
                        if not scroll.isHidden():
                            scroll.verticalScrollBar().setValue(scroll_val)
                    except RuntimeError as _e:
                        kui.log_exc(_e)
                QTimer.singleShot(10, restore)

            layout.addWidget(scroll)
            self.active_scroll_area = scroll
            self.expanded_text_edit = None
        else:
            text_container = QWidget()
            text_container.setStyleSheet("background-color: #444;")
            text_layout = QVBoxLayout(text_container)
            text_layout.setContentsMargins(30, 30, 30, 30)
            text_layout.setAlignment(Qt.AlignCenter)

            large = InteractiveTextEdit(self)
            large.setStyleSheet("background: #111; color: #fff; font-size: 16px; border: none;")
            large.setReadOnly(False)
            large.setHtml(self.note.text)
            large.textChanged.connect(self.on_text_changed)
            self.temp_large_edit = large
            self.expanded_text_edit = large
            self.active_scroll_area = None

            text_layout.addWidget(large)
            layout.addWidget(text_container)
        return container

    def _build_document_view(self, layout):
        layout.setContentsMargins(10, 20, 10, 60)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        self.doc_page_label = QLabel("Sayfa 1")
        self.doc_page_label.setStyleSheet("color: #888; font-weight: bold; font-size: 14px;")
        self.doc_page_label.setAlignment(Qt.AlignCenter)
        set_tip(self.doc_page_label, "doc_page")
        layout.addWidget(self.doc_page_label)

        page_container = QWidget()
        page_layout = QVBoxLayout(page_container)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.doc_image_widget = DocumentImageWidget()
        page_layout.addWidget(self.doc_image_widget)
        layout.addWidget(page_container)

        QTimer.singleShot(50, self.update_document_view)

    def _build_gallery_view(self, layout):
        layout.setContentsMargins(60, 30, 200, 60)
        layout.setSpacing(20)
        for idx, item in enumerate(self.note.items):
            row = self._gallery_row(idx, item)
            self.item_widgets.append(row)
            layout.addWidget(row)

    def _gallery_row(self, idx, item):
        container = QWidget()
        container.setAttribute(Qt.WA_LayoutUsesWidgetRect)
        cl = QVBoxLayout(container)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(5)

        label = QLabel(item.name)
        label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        label.setStyleSheet("color: #aaa; padding-left: 110px;")
        label.setAlignment(Qt.AlignLeft)
        cl.addWidget(label)

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(30)

        controls = QWidget()
        controls.setFixedWidth(100)
        controls.setStyleSheet("background: transparent;")
        ctl = QHBoxLayout(controls)
        ctl.setContentsMargins(0, 0, 0, 0)
        ctl.setSpacing(10)
        ctl.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        del_btn = _tool_button("X", 30, 30, GALLERY_DELETE_STYLE, "item_delete")
        del_btn.clicked.connect(lambda _checked=False, i=idx: self.remove_sub_item(i))
        ctl.addWidget(del_btn)
        ctl.addSpacing(10)

        stack = QWidget()
        sl = QVBoxLayout(stack)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(2)
        up_btn = _tool_button("▲", 50, 20, GALLERY_BUTTON_STYLE, "item_up")
        up_btn.clicked.connect(lambda _checked=False, i=idx: self.move_item_up(i))
        num_btn = _tool_button(f"#{idx + 1}", 50, 30, GALLERY_BUTTON_STYLE, "item_num")
        num_btn.clicked.connect(lambda _checked=False, b=num_btn, i=idx: self.show_order_menu(b, i))
        down_btn = _tool_button("▼", 50, 20, GALLERY_BUTTON_STYLE, "item_down")
        down_btn.clicked.connect(lambda _checked=False, i=idx: self.move_item_down(i))
        for b in (up_btn, num_btn, down_btn):
            sl.addWidget(b)
        ctl.addWidget(stack)
        row_layout.addWidget(controls)

        view = self._item_view(item)
        row_layout.addWidget(view, 1)
        cl.addWidget(row_widget)
        return container

    def _item_view(self, item):
        if item.type == ITEM_TXT:
            def store(text, it=item):
                it.content = text
            return AutoResizingTextEdit(item.content, item.is_txr, on_change=store)
        zoom = ZoomableImageWidget(self.item_pixmap(item))
        QTimer.singleShot(10, zoom.fit_logic)
        return zoom

    def update_document_view(self):
        if not self.note.is_document or not self.note.items:
            return
        if self.doc_image_widget is None:
            return
        try:
            idx = min(max(self.note.current_page, 0), len(self.note.items) - 1)
            self.note.current_page = idx
            pixmap = self.item_pixmap(self.note.items[idx])
            if self.doc_page_label is not None:
                self.doc_page_label.setText(f"Sayfa {idx + 1} / {len(self.note.items)}")
            self.doc_image_widget.set_pixmap(pixmap, self.note.doc_size)
            if self.active_scroll_area and self.active_scroll_area.verticalScrollBar():
                self.active_scroll_area.verticalScrollBar().setValue(0)
            if self.parent_window.expanded_note_widget is self:
                self.parent_window.nav_btn.setText(f"#{idx + 1}")
        except RuntimeError as _e:
            kui.log_exc(_e)

    def refresh_expanded_view(self):
        last = len(self.note.items) - 1
        self.invalidate_cache()
        QApplication.processEvents()
        self.parent_window.expand_note(self, maintain_scroll=False, target_item_index=last)

    # ------------------------------------------------------- diğer işlemler

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        if self.note.is_media:
            urls = self._media_urls()
            if urls:
                mime = QMimeData()
                mime.setUrls(urls)
                clipboard.setMimeData(mime)
                self._flash_copy_button("OK")
            return

        if self.is_expanded and self.temp_large_edit is not None:
            text = self.temp_large_edit.toPlainText()
        elif self.text_edit is not None:
            text = self.text_edit.toPlainText()
        else:
            doc = QTextDocument()
            doc.setHtml(self.note.text)
            text = doc.toPlainText()
        clipboard.setText(text)
        self._flash_copy_button("TXT")

    def _media_urls(self):
        urls = []
        ws = self.parent_window.workspace
        for item in self.note.items:
            try:
                if item.type == ITEM_IMG and os.path.exists(item.content):
                    urls.append(QUrl.fromLocalFile(item.content))
                elif item.type == ITEM_TXT:
                    path = ws.clip_path(item.name)
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(item.content)
                    urls.append(QUrl.fromLocalFile(path))
                elif item.type == ITEM_PAGE:
                    pix = self.parent_window.renderer.render_page(item.content, item.page_index)
                    if not pix.isNull():
                        path = ws.clip_path(item.name + '.png')
                        pix.save(path, "PNG")
                        urls.append(QUrl.fromLocalFile(path))
            except (OSError, ArchiveError) as e:
                log.warning("Panoya eklenemedi (%s): %s", item.name, e)
        return urls

    def _flash_copy_button(self, text):
        if self.is_expanded:
            return
        self.copy_btn.setText(text)
        QTimer.singleShot(1000, lambda: self.copy_btn.setText("/"))

    def toggle_maximize(self):
        if self.parent_window.expanded_note_widget is self:
            self.parent_window.collapse_note(self)
        else:
            self.parent_window.expand_note(self)

    def open_cover_panel(self, global_pos):
        self.parent_window.open_cover_panel(self, global_pos)

    def mouseDoubleClickEvent(self, event):
        # Pakete çift tıklayınca aç. Başlık, düğme ve metin alanlarındaki tıklamalar kendi işini yapar.
        child = self.childAt(event.pos())
        if (event.button() == Qt.LeftButton and not self.is_expanded
                and (child is None or child is self.image_card)):
            self.parent_window.expand_note(self)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def delete_self(self):
        if self.is_expanded:
            self.parent_window.collapse_note(self)
        self.parent_window.remove_note(self)

# ======================================================================
# gallery_builder
# ======================================================================
"""Galeri ve belge notlarını dosya listelerinden üreten TEK giriş noktası.

Önceki sürümde aynı işi yapan 5 ayrı fonksiyon vardı; artık hepsi buradan geçer.
"""


log = logging.getLogger("copya.builder")


class BuildError(Exception):
    """Kullanıcıya gösterilecek oluşturma hatası."""


def _read_text(path: str) -> str:
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def build_gallery(paths, workspace: Workspace, title: str = "") -> Note:
    """Resim ve metin dosyalarından galeri notu üretir (desteklenmeyenler atlanır)."""
    note = Note(kind=KIND_GALLERY, title=title)
    for path in paths[:MAX_GALLERY_ITEMS]:
        kind = classify(path)
        base = os.path.basename(path)
        try:
            if kind == KIND_IMAGE:
                item = Item(ITEM_IMG, workspace.import_file(path), note.unique_name(base))
            elif kind == KIND_TEXT:
                item = Item(ITEM_TXT, _read_text(path), note.unique_name(base),
                            is_txr=path.lower().endswith('.txr'))
            else:
                continue
        except OSError as e:
            log.warning("Dosya okunamadı, atlandı (%s): %s", base, e)
            continue
        note.add_item(item)
    return note


def build_document(path: str, workspace: Workspace, renderer: DocumentRenderer) -> Note:
    """Tek bir belge dosyasından (PDF, Office, PNF, resim) sayfalı belge notu üretir."""
    kind = classify(path)
    ext = os.path.splitext(path)[1].lower().lstrip('.')
    base = os.path.basename(path)
    note = Note(kind=KIND_DOCUMENT, title=base, doc_type=ext)

    if kind == KIND_IMAGE:
        try:
            note.add_item(Item(ITEM_IMG, workspace.import_file(path), base))
        except OSError as e:
            raise BuildError(f"Dosya okunamadı: {e}")

    elif kind == KIND_PNF:
        _add_pnf_pages(note, path, workspace)

    elif kind == KIND_PAGED:
        _add_paged(note, workspace.import_file(path), renderer)

    elif kind == KIND_OFFICE or (kind == KIND_TEXT and ext == 'txt'):
        # .txt de LibreOffice ile PDF'e çevrilip sayfalı olarak gösterilir
        src = workspace.import_file(path)
        try:
            pdf = convert_to_pdf(src, workspace.copi_dir)
        except ConversionError as e:
            raise BuildError(str(e))
        _add_paged(note, pdf, renderer)

    else:
        raise BuildError(f"Bu dosya türü belge olarak açılamaz: .{ext}")

    if not note.items:
        raise BuildError("Belgede gösterilecek sayfa bulunamadı.")
    return note


def _add_paged(note: Note, pdf_path: str, renderer: DocumentRenderer) -> None:
    try:
        count = min(renderer.page_count(pdf_path), MAX_DOCUMENT_ITEMS)
    except Exception as e:
        raise BuildError(f"Belge açılamadı: {e}")
    for i in range(count):
        note.add_item(Item(ITEM_PAGE, pdf_path, f"Sayfa {i + 1}", page_index=i))


def _add_pnf_pages(note: Note, pnf_path: str, workspace: Workspace) -> None:
    try:
        with open(pnf_path, 'r', encoding='utf-8') as f:
            project = json.load(f)
    except (ValueError, OSError) as e:
        raise BuildError(f"PNF dosyası okunamadı: {e}")
    if not isinstance(project, list):
        raise BuildError("Geçersiz PNF veri yapısı.")

    for idx, page in enumerate(project):
        if not isinstance(page, dict):
            continue
        b64 = page.get("image_data", "")
        if not b64:
            continue
        try:
            data = base64.b64decode(b64)
        except (binascii.Error, ValueError):
            log.warning("PNF sayfası %s çözülemedi", idx + 1)
            continue
        path = workspace.write_bytes(data, f"page_{idx + 1}.png")
        if not note.add_item(Item(ITEM_IMG, path, f"Sayfa {idx + 1}")):
            break

# ======================================================================
# main_window
# ======================================================================
"""Ana pencere: üst araç çubuğu, ızgara/genişletilmiş görünüm geçişi, kaydet/yükle."""



# ---- Kavram File / Export penceresi (file_manager) -------------------------------
# Kavram çekirdeğinden çalışırken "kavram_file_manager" adıyla yüklenir; program tek başına
# çalıştırılırsa kardeş klasördeki file_manager/file_manager.py doğrudan yüklenir.  Hiçbiri
# olmazsa Qt'nin kendi diyaloğuna dönülür (program asla dosya seçemeden kalmaz).
try:
    import kavram_file_manager as _fm
except Exception:
    try:
        import importlib.util as _ilu
        import os as _fm_os
        import sys as _fm_sys
        _fm_yol = _fm_os.path.join(_fm_os.path.dirname(_fm_os.path.abspath(__file__)), "..", "..", "file_manager", "file_manager.py")
        _fm_spec = _ilu.spec_from_file_location("kavram_file_manager", _fm_yol)
        _fm = _ilu.module_from_spec(_fm_spec)
        _fm_sys.modules["kavram_file_manager"] = _fm
        _fm_spec.loader.exec_module(_fm)
    except Exception:
        from PyQt5.QtWidgets import QFileDialog as _QFD

        class _fm:  # yedek: Qt diyaloğu
            ALL_FILES_LABEL = "Bütün Dosyalar (*)"

            @staticmethod
            def get_open_file_name(parent=None, caption="", directory="", filter="", initialFilter="",
                                   options=None, **_kw):
                return _QFD.getOpenFileName(parent, caption, directory, filter)

            @staticmethod
            def get_open_file_names(parent=None, caption="", directory="", filter="", initialFilter="",
                                    options=None, **_kw):
                return _QFD.getOpenFileNames(parent, caption, directory, filter)

            @staticmethod
            def get_save_file_name(parent=None, caption="", directory="", filter="", initialFilter="",
                                   options=None, **_kw):
                return _QFD.getSaveFileName(parent, caption, directory, filter)

            @staticmethod
            def get_existing_directory(parent=None, caption="", directory="", options=None, **_kw):
                return _QFD.getExistingDirectory(parent, caption, directory)

            @staticmethod
            def notify_saved(parent=None, text="Dosya kaydedildi.", msec=400):
                print(text)
# -----------------------------------------------------------------------------------


log = logging.getLogger("copya.window")

# Üst çubuktaki "_" düğmesinin kısayolu (Alt+X)
COLLAPSE_SHORTCUT = "Alt+X"


def _filter(exts) -> str:
    return " ".join(f"*{e}" for e in exts)


class _CopyWindow(QMainWindow):
    def __init__(self, core_window_ref=None, export_dir=None):
        super().__init__()
        if export_dir is None:
            raise ValueError("export_dir zorunlu.")
        self.core_window_ref = core_window_ref
        self.export_dir = export_dir
        self.settings_file = os.path.join(export_dir, 'settings.json')

        self.setWindowTitle("Copya")
        self.resize(1100, 750)
        self.current_file_path = None
        self.expanded_note_widget = None
        self.notes_list = []

        self.workspace = Workspace(export_dir)
        self.renderer = DocumentRenderer()

        self.scroll_speeds = SCROLL_SPEEDS
        self.current_scroll_speed_index = DEFAULT_SCROLL_INDEX
        self.current_doc_size = DEFAULT_DOC_SIZE
        self.saved_colors = []
        self.last_cover = DEFAULT_COVER
        self.cover_panel = None
        self.cover_target = None
        self.load_settings()
        self.scroll_rate = self.scroll_speeds[self.current_scroll_speed_index]
        self.scroll_accumulator = 0.0
        self.auto_scroll_active = False
        self.auto_scroll_timer = QTimer(self)
        self.auto_scroll_timer.timeout.connect(self.process_auto_scroll)

        install_tooltip_palette()
        self.init_ui()

    # ------------------------------------------------------------ ayarlar

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.current_scroll_speed_index = int(data.get('scroll_speed_index',
                                                               DEFAULT_SCROLL_INDEX))
                self.current_doc_size = data.get('doc_size', DEFAULT_DOC_SIZE)
                saved = data.get('saved_colors', [])
                self.saved_colors[:] = [c.upper() for c in saved
                                        if isinstance(c, str) and re.fullmatch(r'#[0-9A-Fa-f]{6}', c)]
                self.last_cover = clean_cover(data.get('last_cover'))
                if not 0 <= self.current_scroll_speed_index < len(self.scroll_speeds):
                    self.current_scroll_speed_index = DEFAULT_SCROLL_INDEX
        except (OSError, ValueError, TypeError) as e:
            log.warning("Ayarlar okunamadı: %s", e)

    def save_settings(self):
        try:
            os.makedirs(self.export_dir, exist_ok=True)
            kui.atomic_write_json(self.settings_file, {'scroll_speed_index': self.current_scroll_speed_index,
                           'doc_size': self.current_doc_size,
                           'saved_colors': list(self.saved_colors),
                           'last_cover': self.last_cover})
        except OSError as e:
            log.warning("Ayarlar kaydedilemedi: %s", e)

    # ------------------------------------------------------------ arayüz kurulumu

    def _tool(self, text, width, height, style, slot, tip, enabled=True):
        btn = KButton(text)
        btn.setStyleSheet(style)
        btn.setFixedSize(width, height)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setEnabled(enabled)
        if slot is not None:
            btn.clicked.connect(slot)
        set_tip(btn, tip)
        return btn

    def init_ui(self):
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: #222;")
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.toolbar_frame = QFrame()
        self.toolbar_frame.setObjectName("MainToolbar")
        self.toolbar_frame.setStyleSheet("#MainToolbar { background-color: #222222; border-bottom: 2px solid #555555; }")
        kui.prepare_toolbar(self.toolbar_frame)
        tl = kui.ToolbarLayout(self.toolbar_frame)
        tl.setContentsMargins(10, 5, 10, 5)
        tl.setSpacing(10)

        self.file_btn = self._tool("File", 90, 30, BUTTON_STYLE,
                                   lambda: self.load_copya(), "file")
        tl.addWidget(self.file_btn)

        self.save_btn = KButton()
        self.save_btn.setIcon(create_svg_icon(SVG_SAVE_ICON, size=20, color="#ffffff"))
        self.save_btn.setStyleSheet(BUTTON_STYLE)
        self.save_btn.setFixedSize(30, 30)
        self.save_btn.setFocusPolicy(Qt.NoFocus)
        self.save_btn.clicked.connect(self.quick_save)
        set_tip(self.save_btn, "save")
        tl.addWidget(self.save_btn)

        self.add_btn = self._tool("+", 30, 30, BUTTON_STYLE,
                                  lambda: self.add_text_note(), "add")
        tl.addWidget(self.add_btn)

        self.gallery_btn = self._tool("Galeri", 80, 30, BUTTON_STYLE,
                                      self.handle_gallery_click, "gallery")
        tl.addWidget(self.gallery_btn)

        self.belge_btn = self._tool("Belge", 80, 30, BUTTON_STYLE,
                                    self.handle_document_click, "belge")
        tl.addWidget(self.belge_btn)

        self.nav_btn = self._tool("#1", 55, 30, BUTTON_STYLE, self.show_nav_menu, "nav",
                                  enabled=False)
        tl.addWidget(self.nav_btn)

        self.read_mode_btn = self._tool("I", 30, 30,
                                        BUTTON_STYLE + " font-weight: bold; color: white;",
                                        self.toggle_auto_scroll, "auto_scroll")
        tl.addWidget(self.read_mode_btn)

        self.scroll_speed_btn = self._tool(str(self.scroll_rate), 40, 30, BUTTON_STYLE,
                                           self.show_speed_menu, "speed", enabled=False)
        tl.addWidget(self.scroll_speed_btn)

        self.doc_size_btn = self._tool(f"{self.current_doc_size}", 50, 30, BUTTON_STYLE,
                                       self.show_size_menu, "doc_size", enabled=False)
        tl.addWidget(self.doc_size_btn)

        self.tool_delete_btn = self._tool("X", 30, 30, TOOL_DELETE_STYLE,
                                          self.delete_active_package, "toolbar_delete",
                                          enabled=False)
        tl.addWidget(self.tool_delete_btn)

        self.tool_min_btn = self._tool("_", 30, 30, BUTTON_STYLE,
                                       self.collapse_active_note, "toolbar_min", enabled=False)
        tl.addWidget(self.tool_min_btn)

        self.tool_copy_btn = self._tool("/", 30, 30, BUTTON_STYLE,
                                        self.copy_active_note, "toolbar_copy", enabled=False)
        tl.addWidget(self.tool_copy_btn)

        tl.addStretch()   # sol grup | sağ köşe grubu (Export + Copy)

        self.export_btn = self._tool("Export", 90, 30, BUTTON_STYLE,
                                     self.export_copya, "export")
        tl.addWidget(self.export_btn)

        self.switcher_btn = self._tool("Copy", 90, 30, BUTTON_STYLE,
                                       self.triggerCoreSwitcher, "switcher")
        tl.addWidget(self.switcher_btn)

        main_layout.addWidget(self.toolbar_frame)
        self.content_stack = QStackedWidget()
        main_layout.addWidget(self.content_stack)

        # Izgara sayfası: üç sütun
        self.grid_page = QWidget()
        grid_layout = QVBoxLayout(self.grid_page)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background-color: #121212;")
        self.columns_layout = QHBoxLayout(container)
        self.columns_layout.setAlignment(Qt.AlignTop)
        self.columns_layout.setSpacing(15)
        self.columns_layout.setContentsMargins(15, 20, 15, 20)

        self.columns = []
        for _ in range(3):
            w = QWidget()
            lay = QVBoxLayout(w)
            lay.setAlignment(Qt.AlignTop)
            lay.setSpacing(10)
            lay.setContentsMargins(0, 0, 0, 0)
            self.columns.append(lay)
            self.columns_layout.addWidget(w, 1)
        self.scroll.setWidget(container)
        grid_layout.addWidget(self.scroll)
        self.content_stack.addWidget(self.grid_page)

        # Genişletilmiş sayfa
        self.expanded_page = QWidget()
        self.expanded_page.setStyleSheet("background-color: #000000;")
        self.expanded_layout = QVBoxLayout(self.expanded_page)
        self.expanded_layout.setContentsMargins(0, 0, 0, 0)
        self.content_stack.addWidget(self.expanded_page)

        # Ok tuşu gezinmesi (değişmedi)
        self._bind_shortcut(Qt.Key_Left, lambda: self.navigate_package(-1))
        self._bind_shortcut(Qt.Key_Right, lambda: self.navigate_package(1))
        self._bind_shortcut(Qt.Key_Up, self.navigate_page_up)
        self._bind_shortcut(Qt.Key_Down, self.navigate_page_down)
        # Üst çubuktaki "_" düğmesinin kısayolu (Alt+X)
        collapse_sc = QShortcut(QKeySequence(COLLAPSE_SHORTCUT), self)
        collapse_sc.setContext(Qt.ApplicationShortcut)
        collapse_sc.activated.connect(self.collapse_active_note)

    def _bind_shortcut(self, key, slot):
        shortcut = QShortcut(QKeySequence(key), self)
        shortcut.activated.connect(slot)
        return shortcut

    # ------------------------------------------------------------ not ekleme

    def add_note_model(self, note: Note, refresh=True):
        """Bir `Note` modelinden kart oluşturur. Limit doluysa None döner."""
        if len(self.notes_list) >= MAX_NOTES:
            return None
        widget = NoteWidget(self, note)
        self.notes_list.append(widget)
        if refresh:
            self.refresh_layout()
        return widget

    def add_text_note(self, text_html: str = ""):
        widget = self.add_note_model(Note(kind=KIND_TEXT, text=text_html))
        if widget is not None and not text_html:
            widget.pkg_edit.setFocus()
        return widget

    def remove_note(self, widget):
        if widget in self.notes_list:
            self.notes_list.remove(widget)
            widget.setParent(None)
            widget.deleteLater()
            self.refresh_layout()

    def refresh_layout(self):
        if self.content_stack.currentIndex() == 1:
            return
        for note in self.notes_list:
            note.setParent(None)
        for idx, widget in enumerate(self.notes_list):
            widget.set_column_mode()
            self.columns[idx % 3].addWidget(widget)
            widget.setFixedHeight(NOTE_HEIGHT)
            widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            widget.show()

    # ------------------------------------------------------------ dosya ekleme

    def handle_gallery_click(self):
        os.makedirs(self.export_dir, exist_ok=True)
        flt = (f"Galeri Dosyaları ({_filter(GALLERY_EXTS)});;"
               f"Resimler ({_filter(IMAGE_EXTS)});;"
               f"Metin Dosyaları ({_filter(TEXT_EXTS)})")
        files, _ = _fm.get_open_file_names(self, "Dosyaları Seç", self.export_dir, flt, double_click="select")
        files = [f for f in files if classify(f) in (KIND_IMAGE, KIND_TEXT)]
        if not files:
            return

        current = self.expanded_note_widget
        if current is not None and current.note.is_media:
            self._append_to_open_media(current, files)
            return

        if len(self.notes_list) >= MAX_NOTES:
            return
        note = build_gallery(files, self.workspace)

        note.cover = self.last_cover
        if note.items:
            self.add_note_model(note)

    def _append_to_open_media(self, widget, files):
        note = widget.note
        room = note.max_items - len(note.items)
        if room <= 0:
            return
        if note.is_document:
            # Belgede yalnızca resimler sayfa olarak gösterilir
            files = [f for f in files if classify(f) == KIND_IMAGE]
        extra = build_gallery(files[:room], self.workspace).items
        if not extra:
            return
        note.items.extend(extra)
        widget.invalidate_cache()
        widget.refresh_expanded_view()

    def handle_document_click(self):
        os.makedirs(self.export_dir, exist_ok=True)
        flt = (f"Desteklenen Belgeler ({_filter(DOCUMENT_EXTS)});;"
               f"PDF Belgeleri ({_filter(PAGED_EXTS)});;"
               f"Office Belgeleri ({_filter(OFFICE_EXTS)});;"
               f"Drawing Projeleri ({_filter(PNF_EXTS)});;"
               f"Resimler ({_filter(IMAGE_EXTS)})")
        files, _ = _fm.get_open_file_names(self, "Belge Seç", self.export_dir, flt, double_click="select")
        if not files:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for path in files:
                if len(self.notes_list) >= MAX_NOTES:
                    break
                try:
                    note = build_document(path, self.workspace, self.renderer)

                    note.cover = self.last_cover
                except (BuildError, OSError) as e:
                    QMessageBox.critical(self, "Belge Hatası", f"{os.path.basename(path)}\n\n{e}")
                    continue
                note.doc_size = self.current_doc_size
                self.add_note_model(note, refresh=False)
            self.refresh_layout()
        finally:
            QApplication.restoreOverrideCursor()

    def paste_from_clipboard(self):
        mime = QApplication.clipboard().mimeData()
        if mime.hasUrls():
            files = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
            if files:
                note = build_gallery(files, self.workspace)

                note.cover = self.last_cover
                if note.items:
                    self.add_note_model(note)
        elif mime.hasText():
            text = mime.text()
            if text:
                # Düz metni HTML olarak yorumlanmasın diye kaçırıyoruz
                formatted = html.escape(text, quote=False).replace("\n", "<br>")
                widget = self.add_text_note(formatted)
                if widget is not None:
                    self.update_nav_button_text_mode(widget)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Paste):
            self.paste_from_clipboard()
        super().keyPressEvent(event)

    # ------------------------------------------------------------ gezinme

    def navigate_package(self, delta):
        if not self.notes_list:
            return
        if self.expanded_note_widget:
            try:
                current = self.notes_list.index(self.expanded_note_widget)
            except ValueError:
                current = 0
            new_idx = (current + delta) % len(self.notes_list)
            self.collapse_note(self.expanded_note_widget)
        else:
            new_idx = 0 if delta > 0 else -1
        target = self.notes_list[new_idx]
        self.expand_note(target, target_item_index=target.note.current_page)

    def navigate_page_up(self):
        self._navigate_page(-1)

    def navigate_page_down(self):
        self._navigate_page(1)

    def _navigate_page(self, delta):
        widget = self.expanded_note_widget
        if widget is None or not widget.note.is_media:
            return
        if widget.note.is_document:
            self.change_document_page(delta)
        else:
            self.scroll_to_relative_item(delta)

    def scroll_to_relative_item(self, delta):
        note = self.expanded_note_widget.note
        if not note.items:
            return
        note.current_page = (note.current_page + delta) % len(note.items)
        self.scroll_to_item(note.current_page)

    def change_document_page(self, delta):
        note = self.expanded_note_widget.note
        if not note.items:
            return
        note.current_page = (note.current_page + delta) % len(note.items)
        self.expanded_note_widget.update_document_view()

    def on_gallery_scroll(self, val):
        widget = self.expanded_note_widget
        if widget is None or not widget.note.is_media or widget.note.is_document:
            return
        found = 0
        for i, w in enumerate(widget.item_widgets):
            g = w.geometry()
            if g.y() + g.height() > val:
                found = i
                break
        widget.note.current_page = found
        self.nav_btn.setText(f"#{found + 1}")

    def scroll_to_item(self, index):
        widget = self.expanded_note_widget
        if widget is None:
            return
        QApplication.processEvents()
        try:
            if widget.note.is_document:
                widget.note.current_page = index
                widget.update_document_view()
            elif index < len(widget.item_widgets) and widget.active_scroll_area:
                widget.active_scroll_area.ensureWidgetVisible(widget.item_widgets[index])
                widget.note.current_page = index
                self.nav_btn.setText(f"#{index + 1}")
        except RuntimeError as _e:
            kui.log_exc(_e)

    def show_nav_menu(self):
        widget = self.expanded_note_widget
        if widget is None or not widget.note.is_media:
            return
        menu = QMenu(self)
        menu.setStyleSheet(NAV_MENU_STYLE)
        menu.setFixedHeight(min(600, 35 * len(widget.note.items) + 20))
        for idx in range(len(widget.note.items)):
            action = menu.addAction(f"#{idx + 1}")
            action.triggered.connect(lambda _checked=False, i=idx: self.scroll_to_item(i))
        menu.exec_(self.nav_btn.mapToGlobal(QPoint(0, self.nav_btn.height())))

    # ------------------------------------------------------------ otomatik kaydırma

    def toggle_auto_scroll(self):
        if self.auto_scroll_active:
            self.auto_scroll_timer.stop()
            self.auto_scroll_active = False
            self.read_mode_btn.setStyleSheet(BUTTON_STYLE)
        else:
            if not self.expanded_note_widget:
                return
            self.auto_scroll_timer.start(50)
            self.auto_scroll_active = True
            self.read_mode_btn.setStyleSheet(BUTTON_STYLE.replace("transparent", "#555"))

    def process_auto_scroll(self):
        widget = self.expanded_note_widget
        if widget is None:
            self.toggle_auto_scroll()
            return
        bar = None
        if widget.active_scroll_area:
            bar = widget.active_scroll_area.verticalScrollBar()
        elif widget.expanded_text_edit:
            bar = widget.expanded_text_edit.verticalScrollBar()
        if not bar:
            return
        self.scroll_accumulator += self.scroll_rate
        if self.scroll_accumulator >= 1.0:
            pixels = int(self.scroll_accumulator)
            self.scroll_accumulator -= pixels
            bar.setValue(bar.value() + pixels)
        if bar.value() >= bar.maximum():
            self.toggle_auto_scroll()

    def show_speed_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        for i, speed in enumerate(self.scroll_speeds):
            action = menu.addAction(f"Speed: {speed}")
            action.setCheckable(True)
            action.setChecked(i == self.current_scroll_speed_index)
            action.triggered.connect(lambda _checked=False, idx=i: self.set_scroll_speed(idx))
        menu.exec_(self.scroll_speed_btn.mapToGlobal(QPoint(0, self.scroll_speed_btn.height())))

    def set_scroll_speed(self, index):
        self.current_scroll_speed_index = index
        self.scroll_rate = self.scroll_speeds[index]
        self.scroll_speed_btn.setText(str(self.scroll_rate))
        self.save_settings()

    def show_size_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet(MENU_STYLE)
        current = self.current_doc_size
        if self.expanded_note_widget and self.expanded_note_widget.note.is_document:
            current = self.expanded_note_widget.note.doc_size
        for val in DOC_SIZE_CHOICES:
            action = menu.addAction(f"Boyut: {val}")
            action.setCheckable(True)
            action.setChecked(val == current)
            action.triggered.connect(lambda _checked=False, v=val: self.set_doc_size(v))
        menu.exec_(self.doc_size_btn.mapToGlobal(QPoint(0, self.doc_size_btn.height())))

    def set_doc_size(self, size):
        self.current_doc_size = size
        self.doc_size_btn.setText(str(size))
        self.save_settings()
        widget = self.expanded_note_widget
        if widget and widget.note.is_document:
            widget.note.doc_size = size
            widget.update_document_view()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        widget = self.expanded_note_widget
        if widget and widget.note.is_document and widget.doc_image_widget is not None:
            try:
                widget.doc_image_widget.update_size()
            except RuntimeError as _e:
                kui.log_exc(_e)

    # ------------------------------------------------------------ genişletme / küçültme

    def _detach_expanded_children(self, owner):
        while self.expanded_layout.count():
            child = self.expanded_layout.takeAt(0)
            w = child.widget()
            if w:
                w.setParent(owner)
                w.hide()

    def expand_note(self, note_widget, maintain_scroll=False, target_item_index=None):
        self.setUpdatesEnabled(False)
        try:
            current_scroll = 0
            if maintain_scroll and self.expanded_note_widget:
                area = self.expanded_note_widget.active_scroll_area
                if area and not area.isHidden():
                    current_scroll = area.verticalScrollBar().value()

            if self.expanded_note_widget:
                old = self.expanded_note_widget
                old.update_text_from_expanded()
                old.is_expanded = False
                old.setFixedHeight(NOTE_HEIGHT)
                self._detach_expanded_children(old)
                self.expanded_note_widget = None

            self.expanded_note_widget = note_widget
            note_widget.is_expanded = True
            content = note_widget.get_or_create_expanded_content(current_scroll)
            self.expanded_layout.addWidget(content)
            content.show()

            self.content_stack.setCurrentIndex(1)
            self.update_toolbar_state(True, note_widget)

            if target_item_index is not None and note_widget.note.is_media:
                QTimer.singleShot(100, lambda: self.scroll_to_item(target_item_index))
        finally:
            self.setUpdatesEnabled(True)

    def collapse_note(self, note_widget):
        if self.auto_scroll_active:
            self.toggle_auto_scroll()
        note_widget.update_text_from_expanded()
        note_widget.is_expanded = False
        self._detach_expanded_children(note_widget)
        self.expanded_note_widget = None
        self.content_stack.setCurrentIndex(0)
        self.refresh_layout()
        self.update_toolbar_state(False)

    def collapse_active_note(self):
        if self.expanded_note_widget is not None:
            self.collapse_note(self.expanded_note_widget)

    def copy_active_note(self):
        if self.expanded_note_widget is not None:
            self.expanded_note_widget.copy_to_clipboard()

    def delete_active_package(self):
        widget = self.expanded_note_widget
        if widget is not None:
            self.collapse_note(widget)
            self.remove_note(widget)

    def update_toolbar_state(self, is_expanded, note_widget=None):
        if not is_expanded:
            self.add_btn.setEnabled(True)
            self.gallery_btn.setEnabled(True)
            self.belge_btn.setEnabled(True)
            self.tool_delete_btn.setEnabled(False)
            self.tool_copy_btn.setEnabled(False)
            self.tool_min_btn.setEnabled(False)
            self.nav_btn.setEnabled(False)
            self.nav_btn.setText("#1")
            self.nav_btn.setMinimumWidth(40)
            self.read_mode_btn.setEnabled(False)
            self.scroll_speed_btn.setEnabled(False)
            self.doc_size_btn.setEnabled(False)
            if self.auto_scroll_active:
                self.toggle_auto_scroll()
            return

        self.read_mode_btn.setEnabled(True)
        self.scroll_speed_btn.setEnabled(True)
        if note_widget is not None:
            note = note_widget.note
            if note.is_media:
                self.add_btn.setEnabled(False)
                self.gallery_btn.setEnabled(True)
                self.belge_btn.setEnabled(True)
                self.nav_btn.setEnabled(True)
                self.nav_btn.setText(f"#{note.current_page + 1 if note.is_document else 1}")
                self.doc_size_btn.setEnabled(note.is_document)
                if note.is_document:
                    self.doc_size_btn.setText(str(note.doc_size))
            else:
                self.add_btn.setEnabled(False)
                self.gallery_btn.setEnabled(False)
                self.belge_btn.setEnabled(False)
                self.doc_size_btn.setEnabled(False)
                self.update_nav_button_text_mode(note_widget)
        self.tool_delete_btn.setEnabled(True)
        self.tool_copy_btn.setEnabled(True)
        self.tool_min_btn.setEnabled(True)

    def update_nav_button_text_mode(self, widget):
        if widget.note.is_media:
            return
        doc = QTextDocument()
        doc.setHtml(widget.note.text)
        line_count = doc.blockCount()
        if line_count <= 1 and widget.note.text:
            line_count = widget.note.text.count("<br") + 1
        text = f"#{line_count}"
        self.nav_btn.setText(text)
        self.nav_btn.setEnabled(False)
        width = QFontMetrics(self.nav_btn.font()).width(text) + 30
        self.nav_btn.setMinimumWidth(max(40, width))

    # ------------------------------------------------------------ kaydet / yükle

    def flush_all_text(self):
        for widget in self.notes_list:
            widget.flush_text()
        if self.expanded_note_widget is not None:
            self.expanded_note_widget.update_text_from_expanded()

    def clear_view(self):
        if self.expanded_note_widget:
            self.collapse_note(self.expanded_note_widget)
        for widget in self.notes_list:
            widget.setParent(None)
            widget.deleteLater()
        self.notes_list.clear()

    def load_copya(self, path=None):
        if path is None:
            os.makedirs(self.export_dir, exist_ok=True)
            path, _ = _fm.get_open_file_name(self, "Open", self.export_dir,
                                                  "Copya Files (*.copya)", editor="Copy")
        if not path:
            return

        # Açık belge tanıtıcıları dosyaları kilitleyebilir; yüklemeden önce bırak.
        self.renderer.close()
        try:
            notes = self.workspace.load_archive(path)
        except (ArchiveError, zipfile.BadZipFile, OSError) as e:
            QMessageBox.critical(self, "Error", f"Could not load file:\n{e}")
            return

        self.clear_view()
        progress = QProgressDialog("Proje Yükleniyor...", "İptal", 0, len(notes), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        for idx, note in enumerate(notes):
            if progress.wasCanceled():
                break
            progress.setValue(idx)
            QApplication.processEvents()
            self.add_note_model(note, refresh=False)
        progress.setValue(len(notes))
        self.current_file_path = path
        self.refresh_layout()

    def quick_save(self):
        if self.current_file_path:
            self.save_to_path(self.current_file_path)
        else:
            self.export_copya()

    def export_copya(self):
        os.makedirs(self.export_dir, exist_ok=True)
        path, _ = _fm.get_save_file_name(
            self, "Save", os.path.join(self.export_dir, "untitled.copya"), "Copya Files (*.copya)", editor="Copy")
        if not path:
            return
        if not path.endswith('.copya'):
            path += '.copya'
        self.save_to_path(path)

    def save_to_path(self, path):
        self.flush_all_text()
        try:
            self.workspace.save_archive([w.note for w in self.notes_list], path)
        except (OSError, ArchiveError) as e:
            QMessageBox.critical(self, "Error", f"Could not save:\n{e}")
            return
        self.current_file_path = path
        _fm.notify_saved(self)

    def open_cover_panel(self, note_widget, global_pos):
        if self.cover_panel is None:
            self.cover_panel = ColorPanel(self.saved_colors, self)
            self.cover_panel.colorApplied.connect(self._apply_cover_color)
            self.cover_panel.colorConfirmed.connect(self.add_cover_color)
            self.cover_panel.colorRemoved.connect(self.remove_cover_color)
        self.cover_target = note_widget
        self.cover_panel.open_with(QColor(note_widget.note.cover))
        self.cover_panel.move(global_pos)
        self.cover_panel.show()
        self.cover_panel.raise_()

    def _apply_cover_color(self, color):
        target = self.cover_target
        if target is None:
            return
        hex_code = color.name().upper() if color is not None else DEFAULT_COVER
        target.note.cover = hex_code
        if target.image_card is not None:
            target.image_card.set_color(hex_code)
        if color is not None:
            self.last_cover = hex_code
        self.save_settings()

    def add_cover_color(self, color):
        hex_code = color.name().upper()
        if hex_code not in self.saved_colors:
            self.saved_colors.append(hex_code)
            self.save_settings()
        if self.cover_panel is not None:
            self.cover_panel.saved.refresh()

    def remove_cover_color(self, index):
        if 0 <= index < len(self.saved_colors):
            self.saved_colors.pop(index)
            self.save_settings()
        if self.cover_panel is not None:
            self.cover_panel.saved.refresh()

    def triggerCoreSwitcher(self):
        if self.core_window_ref and hasattr(self.core_window_ref, 'showSwitcher'):
            self.core_window_ref.showSwitcher()

    def closeEvent(self, event):
        self.flush_all_text()
        self.renderer.close()
        super().closeEvent(event)


class MainWindow(_CopyWindow):
    """Kavram'ın çağırdığı giriş noktası. export_dir verilmezse Kavram export klasörü kullanılır."""

    def __init__(self, core_window_ref=None, export_dir=None):
        super().__init__(core_window_ref=core_window_ref,
                         export_dir=export_dir or _KAVRAM_EXPORT_DIR)


if __name__ == '__main__':
    app = QApplication(_sys.argv)
    window = MainWindow(export_dir=_KAVRAM_EXPORT_DIR)
    window.show()
    _sys.exit(app.exec_())
