# Kavram AI Editörü — .ai arşiv okuma/yazma (Qt gerektirmez)
# Kavram 2.2.2 | GNU GPL v3 veya üstü (ayrıntı: ai.py başlığı ve /Kavram/License/GPLv3.txt)

import os
import shutil
import tarfile
import tempfile
import zipfile


class ArchiveError(Exception):
    """Güvensiz veya bozuk arşiv."""


def _inside(base, target):
    try:
        return os.path.commonpath([base, target]) == base
    except ValueError:  # farklı sürücüler (Windows)
        return False


def _safe_tar_members(tar, dest):
    """Yalnızca dosya/klasör kabul eder; mutlak yol, '..' ve bağlantıları reddeder."""
    base = os.path.realpath(dest)
    members = []
    for m in tar.getmembers():
        if not (m.isfile() or m.isdir()):
            raise ArchiveError(f"Arşivde izin verilmeyen öğe türü: {m.name}")
        target = os.path.realpath(os.path.join(base, m.name))
        if os.path.isabs(m.name) or not _inside(base, target):
            raise ArchiveError(f"Arşivde güvensiz yol: {m.name}")
        members.append(m)
    return members


def extract_tar_safely(tar, dest):
    members = _safe_tar_members(tar, dest)
    if hasattr(tarfile, "data_filter"):      # Python 3.12+ (ve güvenlik yamalı sürümler)
        tar.extractall(dest, members=members, filter="data")
    else:
        tar.extractall(dest, members=members)


def stage_ai_archive(file_path, parent_dir):
    """.ai dosyasını geçici bir klasöre açar ve o klasörün yolunu döndürür.

    Başarısız olursa geçici klasör silinir; çalışma klasörüne hiç dokunulmaz.
    (zipfile zaten '..' ve mutlak yolları kendi temizler; tar için ek doğrulama gerekir.)
    """
    staging = tempfile.mkdtemp(prefix="_ai_load_", dir=parent_dir)
    try:
        if tarfile.is_tarfile(file_path):
            with tarfile.open(file_path, "r:*") as tar:
                extract_tar_safely(tar, staging)
        elif zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, "r") as zf:
                zf.extractall(staging)
        else:  # eski biçim: düz JSON
            shutil.copy2(file_path, os.path.join(staging, "data.json"))
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return staging


def install_staged(staging, dest_dir):
    """dest_dir içeriğini temizleyip staging içeriğini oraya taşır."""
    os.makedirs(dest_dir, exist_ok=True)
    for item in os.listdir(dest_dir):
        p = os.path.join(dest_dir, item)
        if os.path.isdir(p):
            shutil.rmtree(p)
        else:
            os.remove(p)
    for item in os.listdir(staging):
        shutil.move(os.path.join(staging, item), os.path.join(dest_dir, item))


def pack_ai_archive(target_path, files, progress_cb=None):
    """files: [(arcname, yol), ...]. Önce <hedef>.tmp'ye yazar, bitince os.replace ile değiştirir."""
    tmp_path = target_path + ".tmp"
    try:
        with tarfile.open(tmp_path, "w:gz") as tar:
            for idx, (arcname, path) in enumerate(files):
                if progress_cb:
                    progress_cb(idx)
                tar.add(path, arcname=arcname)
        os.replace(tmp_path, target_path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
