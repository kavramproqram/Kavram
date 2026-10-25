"""Veri modeli: not, öğe ve .copya kayıt biçimine dönüşüm. Arayüzden bağımsızdır.

Kayıt biçimi (.copya içindeki data.json) eski sürümle uyumlu tutuldu.
"""
import logging
import os
from typing import Callable, List, Optional

from . import config

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
                 doc_type=None, doc_size=config.DEFAULT_DOC_SIZE, current_page=0):
        self.kind = kind
        self.title = title
        self.text = text            # yalnızca metin notu için (HTML)
        self.items = list(items) if items else []
        self.doc_type = doc_type
        self.doc_size = doc_size
        self.current_page = current_page

    @property
    def is_media(self) -> bool:
        return self.kind != KIND_TEXT

    @property
    def is_document(self) -> bool:
        return self.kind == KIND_DOCUMENT

    @property
    def max_items(self) -> int:
        return config.MAX_DOCUMENT_ITEMS if self.is_document else config.MAX_GALLERY_ITEMS

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


def clamp_doc_size(value) -> int:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return config.DEFAULT_DOC_SIZE
    return v if v in config.DOC_SIZE_CHOICES else config.DEFAULT_DOC_SIZE


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
                doc_size=clamp_doc_size(raw.get('doc_size')))

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
