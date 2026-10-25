"""Belge ve resim işleme: sayfa render, önbellek, Office dönüştürme.

PDF ve diğer sayfalı biçimler PyMuPDF (fitz) ile, Office belgeleri LibreOffice ile
PDF'e çevrilip aynı yoldan gösterilir. Resimler QImage ile okunur.
"""
import logging
import os
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from pathlib import Path

from PyQt5.QtGui import QBitmap, QImage, QPixmap, QRegion

from . import config

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
    if ext in config.IMAGE_EXTS:
        return KIND_IMAGE
    if ext in config.TEXT_EXTS:
        return KIND_TEXT
    if ext in config.PNF_EXTS:
        return KIND_PNF
    if ext in config.PAGED_EXTS:
        return KIND_PAGED
    if ext in config.OFFICE_EXTS:
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
        self._docs = LRUCache(config.OPEN_DOCUMENT_CACHE_SIZE, on_evict=_close_doc)
        self._pages = LRUCache(config.PAGE_CACHE_SIZE)
        self._images = LRUCache(config.IMAGE_CACHE_SIZE)

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
            zoom = config.RENDER_DPI / 72
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
            check=True, timeout=config.OFFICE_TIMEOUT_S,
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
