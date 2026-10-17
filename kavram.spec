# -*- mode: python ; coding: utf-8 -*-
# =====================================================================================
# KAVRAM — PyInstaller paket tarifi (onedir)
#
#   Derleme (kavram klasöründe, kurulum_deb.txt / kurulum_arch.txt çalıştırıldıktan sonra):
#       ./venv/bin/pip install pyinstaller
#       ./venv/bin/pyinstaller --noconfirm --clean --distpath paket --workpath /tmp/kavram_build kavram.spec
#   Çıktı:  paket/kavram/kavram   (çalıştırılabilir)  +  paket/kavram/_internal/ (kütüphaneler)
#
# Bu dosya şunları yapar:
#   * C++ motorları (sound_engine.so, media_engine.so, filter_engine.so, converter_engine.so, rec_engine)
#     yoksa her programın derleme.txt dosyasıyla derler.
#   * Çekirdeği (kavram.py) paketler; programları <ad>/<ad>.py kaynak dosyası olarak pakete koyar
#     (çekirdek bunları "kavram_<ad>" adıyla yükler). Programların kullandığı tüm kütüphaneler,
#     kaynak dosyalar taranarak otomatik bulunur (elle gizli import listesi tutmak gerekmez).
#   * .so motorlarının bağımlı olduğu kütüphaneleri (portaudio, sndfile, opencv, ffmpeg...) pakete katar.
#   * rec_engine, sistemdeki GStreamer'ı kullanır (eklentileri dağıtıma özeldir) — pakete katılmaz.
#   * Qt: hem xcb (X11 / XWayland) hem wayland eklentisi pakete girer; seçimi kavram.py yapar.
#   * Yazılabilir veriler (export, ayarlar, kayıtlar) pakete değil ~/.local/share/kavram altına yazılır.
#   * Varsa bin/ffmpeg, bin/ffprobe, bin/ffplay (statik FFmpeg) pakete girer ve sistem ffmpeg'ine tercih edilir.
#
# Tüm Linux dağıtımlarında çalışması için paket, desteklenecek EN ESKİ dağıtımda (glibc'si en düşük olan,
# ör. Ubuntu 22.04 / Debian 12) derlenmelidir; paket yeni dağıtımlarda sorunsuz çalışır, tersi olmaz.
# =====================================================================================
import ast
import importlib.util
import os
import subprocess
import sys

from PyInstaller.utils.hooks import (collect_data_files, collect_submodules, copy_metadata)

KOK = os.path.abspath(SPECPATH)          # kavram klasörü (kavram.py'nin yanı)

PROGRAMLAR = ("sphere", "terminal", "text", "drawing", "sound", "ai", "media",
              "rec", "copy", "filter", "converter")

# program -> derlenmesi gereken motor dosyası ve türü
MOTORLAR = {
    "sound":     ("sound_engine.so", "kutuphane"),
    "media":     ("media_engine.so", "kutuphane"),
    "filter":    ("filter_engine.so", "kutuphane"),
    "converter": ("converter_engine.so", "kutuphane"),
    "rec":       ("rec_engine", "calistirilabilir"),
}


def yol(*p):
    return os.path.join(KOK, *p)


# -------------------------------------------------------------------- 1) C++ motorları
for _prog, (_dosya, _tur) in MOTORLAR.items():
    if not os.path.isfile(yol(_prog, _dosya)) and os.path.isfile(yol(_prog, "derleme.txt")):
        print(f"[kavram.spec] {_prog}/{_dosya} yok, derleniyor...")
        subprocess.run(["bash", "derleme.txt"], cwd=yol(_prog))
    if not os.path.isfile(yol(_prog, _dosya)):
        print(f"[kavram.spec] UYARI: {_prog}/{_dosya} bulunamadı; {_prog} programı motorsuz kalır.")

# -------------------------------------------------------------------- 2) veri dosyaları (salt-okunur)
datas = []
binaries = []

for _prog in PROGRAMLAR:
    _klasor = yol(_prog)
    for _ad in sorted(os.listdir(_klasor)):
        _tam = os.path.join(_klasor, _ad)
        if _ad.endswith(".py") or _ad.endswith(".json"):
            datas.append((_tam, _prog))                  # program kaynakları + varsayılan ayarlar

for _prog, (_dosya, _tur) in MOTORLAR.items():
    _tam = yol(_prog, _dosya)
    if os.path.isfile(_tam):
        if _tur == "kutuphane":
            binaries.append((_tam, _prog))               # bağımlı kütüphaneleri de toplanır
        else:
            datas.append((_tam, _prog))                  # rec_engine: sistem GStreamer'ını kullanır

datas.append((yol("ikon"), "ikon"))
if os.path.isdir(yol("license")):
    datas.append((yol("license"), "license"))
for _arac in ("ffmpeg", "ffprobe", "ffplay"):            # isteğe bağlı statik FFmpeg
    if os.path.isfile(yol("bin", _arac)):
        datas.append((yol("bin", _arac), "bin"))

# -------------------------------------------------------------------- 3) gizli importlar (kaynak taraması)
_yerel = set()
for _prog in PROGRAMLAR:
    for _f in os.listdir(yol(_prog)):
        if _f.endswith(".py"):
            _yerel.add(_f[:-3])


def _var_mi(ad):
    try:
        return importlib.util.find_spec(ad) is not None
    except Exception:
        return False


_adaylar = set()
for _prog in PROGRAMLAR:
    for _f in os.listdir(yol(_prog)):
        if not _f.endswith(".py"):
            continue
        with open(yol(_prog, _f), encoding="utf-8") as _fh:
            _agac = ast.parse(_fh.read())
        for _n in ast.walk(_agac):
            if isinstance(_n, ast.Import):
                for _a in _n.names:
                    _adaylar.add(_a.name)
            elif isinstance(_n, ast.ImportFrom) and _n.level == 0 and _n.module:
                _adaylar.add(_n.module)
                for _a in _n.names:
                    _adaylar.add(_n.module + "." + _a.name)

hiddenimports = set()
for _ad in sorted(_adaylar):
    _ust = _ad.split(".")[0]
    if _ust in _yerel or _ust.startswith("kavram_"):
        continue
    if _var_mi(_ad):
        hiddenimports.add(_ad)

# Qt: X11 (xcb) ve Wayland için gereken modüller her koşulda pakete girsin
hiddenimports.update(["PyQt5.sip", "PyQt5.QtSvg", "PyQt5.QtMultimedia", "PyQt5.QtPrintSupport",
                      "PyQt5.QtNetwork", "PyQt5.QtDBus"])


def _guvenli(fonk, *a, **k):
    try:
        return fonk(*a, **k)
    except Exception as _e:
        print(f"[kavram.spec] bilgi: {a[0] if a else ''} toplanamadı ({_e.__class__.__name__})")
        return []


# Dinamik/yavaş yüklenen paketler: alt modüller, veri dosyaları, sürüm bilgisi
for _p in ("pynput", "librosa", "noisereduce", "pydub", "sounddevice", "soundfile",
           "numba", "scipy", "sklearn", "lazy_loader", "pooch", "fitz", "pymupdf", "Crypto"):
    if _var_mi(_p):
        hiddenimports.update(_guvenli(collect_submodules, _p))
        datas += _guvenli(collect_data_files, _p)
for _p in ("librosa", "numba", "noisereduce", "pydub", "soundfile", "sounddevice", "pynput",
           "scipy", "numpy", "pooch", "lazy_loader"):
    if _var_mi(_p):
        datas += _guvenli(copy_metadata, _p)

# -------------------------------------------------------------------- 4) analiz / paketleme
a = Analysis(
    [yol("kavram.py")],
    pathex=[KOK],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(hiddenimports),
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "IPython", "jupyter", "notebook", "pytest", "sphinx",
              "PyQt6", "PySide2", "PySide6", "wx"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="kavram",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,        # strip Qt/ffmpeg kütüphanelerini bozabilir
    upx=False,          # UPX Qt eklentilerini bozar
    console=True,       # terminalden başlatılınca günlükler görünür; menüden başlatınca pencere açılmaz
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="kavram",
)
