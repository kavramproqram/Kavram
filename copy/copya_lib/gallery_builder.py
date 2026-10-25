"""Galeri ve belge notlarını dosya listelerinden üreten TEK giriş noktası.

Önceki sürümde aynı işi yapan 5 ayrı fonksiyon vardı; artık hepsi buradan geçer.
"""
import base64
import binascii
import json
import logging
import os

from . import config
from .models import (KIND_DOCUMENT, KIND_GALLERY, Item, ITEM_IMG, ITEM_PAGE,
                     ITEM_TXT, Note)
from .renderers import (KIND_IMAGE, KIND_OFFICE, KIND_PAGED, KIND_PNF, KIND_TEXT,
                        ConversionError, DocumentRenderer, classify, convert_to_pdf)
from .storage import Workspace

log = logging.getLogger("copya.builder")


class BuildError(Exception):
    """Kullanıcıya gösterilecek oluşturma hatası."""


def _read_text(path: str) -> str:
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def build_gallery(paths, workspace: Workspace, title: str = "") -> Note:
    """Resim ve metin dosyalarından galeri notu üretir (desteklenmeyenler atlanır)."""
    note = Note(kind=KIND_GALLERY, title=title)
    for path in paths[:config.MAX_GALLERY_ITEMS]:
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
        count = min(renderer.page_count(pdf_path), config.MAX_DOCUMENT_ITEMS)
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
