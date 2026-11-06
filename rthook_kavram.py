# rthook_kavram.py — PyInstaller çalışma zamanı kancası (kavram.spec tarafından eklenir).
#
# Paketli sürümde kod ve motorlar salt-okunur paketin içindedir (_internal). Yazılabilir veriler
# (export, veri, ayarlar, kayıtlar) ise kullanıcının kendi dizinine yazılır:
#     Linux   : ~/.local/share/kavram
#     Windows : %LOCALAPPDATA%\kavram
#     macOS   : ~/Library/Application Support/kavram
#
# Bu kanca, kavram.py ve programların kullandığı "export" ve "veri" klasörlerini kullanıcı dizinine
# bağlar (Linux: sembolik bağlantı, Windows: dizin bağlantısı/junction) ve KAVRAM_VERI ortam
# değişkenini ayarlar (media gibi programlar bunu okur).  Windows'ta ayrıca motor DLL'lerinin
# yan kütüphanelerini bulabilmesi için paket klasörleri DLL arama yoluna eklenir.
# Kaynak (paketsiz) çalışmada hiçbir şey yapmaz.

import os
import subprocess
import sys

if getattr(sys, "frozen", False):
    _win = sys.platform.startswith("win")
    if _win:
        _base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        _veri_koku = os.path.join(_base, "kavram")
    elif sys.platform == "darwin":
        _veri_koku = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "kavram")
    else:
        _veri_koku = os.path.join(os.path.expanduser("~"), ".local", "share", "kavram")
    os.environ.setdefault("KAVRAM_VERI", _veri_koku)
    # Pakete eklenen statik FFmpeg (bin/ffmpeg, bin/ffprobe) sistem PATH'ine göre öncelikli olsun
    try:
        os.environ["PATH"] = os.path.join(sys._MEIPASS, "bin") + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass
    try:
        _paket_koku = sys._MEIPASS
        for _ad in ("export", "veri"):
            _gercek = os.path.join(_veri_koku, _ad)
            os.makedirs(_gercek, exist_ok=True)
            _baglanti = os.path.join(_paket_koku, _ad)
            if not os.path.lexists(_baglanti):
                if _win:
                    # Yönetici izni gerektirmeyen dizin bağlantısı (junction)
                    subprocess.run(["cmd", "/c", "mklink", "/J", _baglanti, _gercek],
                                   capture_output=True, creationflags=0x08000000)
                else:
                    os.symlink(_gercek, _baglanti)
    except OSError:
        # Paket dizini yazılamıyorsa klasörler paket içinde kalır; uygulama yine açılır.
        pass
    if _win and hasattr(os, "add_dll_directory"):
        # Motor DLL'leri (sound_engine.dll gibi) kendi yan DLL'lerini bulabilsin
        try:
            _kok = sys._MEIPASS
            os.add_dll_directory(_kok)
            for _d in os.listdir(_kok):
                _t = os.path.join(_kok, _d)
                if os.path.isdir(_t):
                    os.add_dll_directory(_t)
            os.environ["PATH"] = _kok + os.pathsep + os.environ.get("PATH", "")
        except OSError:
            pass
