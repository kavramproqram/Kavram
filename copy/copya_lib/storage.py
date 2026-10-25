"""Çalışma alanı (copi klasörü) ve .copya arşiv kaydet/yükle işlemleri.

Güvenlik kuralları:
- Arşiv içindeki dosya adları yalnızca temel ad (basename) olarak kullanılır;
  mutlak yol veya '..' ile klasör dışına çıkılamaz.
- Arşiv önce geçici bir klasöre açılıp doğrulanır. Doğrulama başarılı olmadan
  mevcut çalışma alanı silinmez.
"""
import json
import logging
import os
import shutil
import tempfile
import uuid
import zipfile
from typing import List

from . import config
from .models import Note, note_from_dict, note_to_dict, ITEM_IMG, ITEM_PAGE

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
            for raw in raw_notes[:config.MAX_NOTES]:
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
            if len(infos) > config.ARCHIVE_MAX_MEMBERS:
                raise ArchiveError("Arşivde çok fazla dosya var.")
            if sum(i.file_size for i in infos) > config.ARCHIVE_MAX_BYTES:
                raise ArchiveError("Arşiv açıldığında çok büyük olur.")

            for info in infos:
                name = safe_basename(info.filename)
                with zf.open(info) as src, open(os.path.join(target, name), 'wb') as dst:
                    shutil.copyfileobj(src, dst)
