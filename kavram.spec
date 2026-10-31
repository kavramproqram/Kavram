# -*- mode: python ; coding: utf-8 -*-
# =====================================================================================
# KAVRAM — PyInstaller paket tarifi (onedir)
#
#   Doğrudan derleme (kavram klasöründe; normalde paketle.sh bunu çağırır):
#       ./venv/bin/pyinstaller --noconfirm --clean --distpath paket --workpath build_tmp kavram.spec
#   Çıktı:  paket/kavram/kavram (çalıştırılabilir)  +  paket/kavram/_internal/ (kütüphaneler ve kaynaklar)
#
# Bu dosya:
#   * Çekirdeği (kavram.py) ve 12 programın TÜM kaynaklarını paketler: alt paketler dahil
#     (ör. copy/copya_lib). Programlar <ad>/<ad>.py olarak _internal/<ad>/ altına girer; çekirdek
#     bunları "kavram_<ad>" adıyla yükler.
#   * Motorları paketler:
#       sound_engine.so, media_engine.so, filter_engine.so, converter_engine.so  (kütüphane, bağımlılıkları toplanır)
#       libfile_engine.so, libview_engine.so                                    (file_manager, ctypes ile açılır)
#       media_recorder, rec_engine                                              (ayrı süreç olarak çalışır)
#     Eksik motor varsa ilgili programın derleme.txt'si çalıştırılır.
#   * Programların kullandığı kütüphaneler kaynak taranarak otomatik bulunur (gizli import listesi elle tutulmaz).
#   * rec_engine ve media_recorder sistemdeki GStreamer'ı kullanır; GStreamer eklentileri pakete girmez.
#   * Yazılabilir veriler (export, veri) çalışma zamanında ~/.local/share/kavram altına yönlendirilir
#     (rthook_kavram.py).
#   * Varsa bin/ffmpeg, bin/ffprobe, bin/ffplay (statik FFmpeg) pakete girer; yoksa sistem ffmpeg'i kullanılır.
#
# Dağıtımlardan bağımsız çalışması için paket, desteklenecek EN ESKİ dağıtımda derlenmelidir.
# Motorlar taşınabilir derlenir: paketle.sh KAVRAM_MARCH=x86-64 ayarlar (sound/derleme.txt bunu kullanır).
# =====================================================================================
import ast
import importlib.util
import os
import subprocess

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

KOK = os.path.abspath(SPECPATH)          # kavram klasörü (kavram.py'nin yanı)


def yol(*p):
    return os.path.join(KOK, *p)


PROGRAMLAR = ("sphere", "terminal", "text", "drawing", "sound", "ai", "media",
              "rec", "copy", "filter", "converter", "file_manager")

# (program, dosya, tür)
#   tür "kutuphane"        : .so — bağımlı kütüphaneleri de (portaudio, sndfile, ffmpeg, ...) toplanır
#   tür "calistirilabilir" : ayrı süreç olarak çalışır — değişmeden kopyalanır
MOTORLAR = [
    ("sound",        "sound_engine.so",     "kutuphane"),
    ("media",        "media_engine.so",     "kutuphane"),
    ("media",        "media_recorder",      "calistirilabilir"),
    ("filter",       "filter_engine.so",    "kutuphane"),
    ("converter",    "converter_engine.so", "kutuphane"),
    ("rec",          "rec_engine",          "calistirilabilir"),
    ("file_manager", "libfile_engine.so",   "kutuphane"),
    ("file_manager", "libview_engine.so",   "kutuphane"),
]
MOTOR_DOSYALARI = {_d for _, _d, _ in MOTORLAR}

# -------------------------------------------------------------------- 1) eksik motorları derle
for _prog in sorted({_p for _p, _, _ in MOTORLAR}):
    _eksik = [_d for _p, _d, _ in MOTORLAR if _p == _prog and not os.path.isfile(yol(_prog, _d))]
    if _eksik and os.path.isfile(yol(_prog, "derleme.txt")):
        print(f"[kavram.spec] {_prog}: eksik motor {_eksik}; derleme.txt çalıştırılıyor...")
        subprocess.run(["bash", "derleme.txt"], cwd=yol(_prog))
    for _d in _eksik:
        if not os.path.isfile(yol(_prog, _d)):
            print(f"[kavram.spec] UYARI: {_prog}/{_d} bulunamadı; ilgili özellik paketli sürümde çalışmayabilir.")

# -------------------------------------------------------------------- 2) veri ve kaynak dosyaları
HARIC_ADLAR = {"derleme.txt", "__pycache__"}
HARIC_UZANTILAR = (".c", ".cpp", ".h", ".o", ".so", ".pyc")

datas = []
binaries = []

# Programların tüm dosyaları, klasör yapısı korunarak (alt paketler dahil)
for _prog in PROGRAMLAR:
    for _dir, _altklasorler, _dosyalar in os.walk(yol(_prog)):
        _altklasorler[:] = [_k for _k in _altklasorler if _k not in HARIC_ADLAR]
        _rel = os.path.relpath(_dir, KOK)
        for _f in _dosyalar:
            if _f in HARIC_ADLAR or _f in MOTOR_DOSYALARI or _f.endswith(HARIC_UZANTILAR):
                continue
            datas.append((os.path.join(_dir, _f), _rel))

# Motorlar
for _prog, _dosya, _tur in MOTORLAR:
    _tam = yol(_prog, _dosya)
    if not os.path.isfile(_tam):
        continue
    if _tur == "kutuphane":
        binaries.append((_tam, _prog))
    else:
        datas.append((_tam, _prog))

datas.append((yol("ikon"), "ikon"))
if os.path.isdir(yol("license")):
    datas.append((yol("license"), "license"))
for _arac in ("ffmpeg", "ffprobe", "ffplay"):            # isteğe bağlı statik FFmpeg
    if os.path.isfile(yol("bin", _arac)):
        datas.append((yol("bin", _arac), "bin"))

# -------------------------------------------------------------------- 3) gizli importlar (kaynak taraması)
# Yerel modül/paket adları: dış kütüphane sanılmasın diye hariç tutulur.
_yerel = set(PROGRAMLAR)
for _prog in PROGRAMLAR:
    for _dir, _altklasorler, _dosyalar in os.walk(yol(_prog)):
        if "__init__.py" in _dosyalar:
            _yerel.add(os.path.basename(_dir))
        for _f in _dosyalar:
            if _f.endswith(".py"):
                _yerel.add(_f[:-3])


def _var_mi(ad):
    try:
        return importlib.util.find_spec(ad) is not None
    except Exception:
        return False


_adaylar = set()
for _prog in PROGRAMLAR:
    for _dir, _altklasorler, _dosyalar in os.walk(yol(_prog)):
        for _f in _dosyalar:
            if not _f.endswith(".py"):
                continue
            try:
                with open(os.path.join(_dir, _f), encoding="utf-8") as _fh:
                    _agac = ast.parse(_fh.read())
            except (SyntaxError, UnicodeDecodeError):
                continue
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
    runtime_hooks=[yol("rthook_kavram.py")],
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
    console=True,       # terminalden başlatılınca günlükler görünür
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="kavram",
)
