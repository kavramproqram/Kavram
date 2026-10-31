# rthook_kavram.py — PyInstaller çalışma zamanı kancası (kavram.spec tarafından eklenir).
#
# Paketli sürümde kod ve motorlar salt-okunur paketin içindedir (_internal). Yazılabilir veriler
# (export, veri, ayarlar, kayıtlar) ise kullanıcının kendi dizinine yazılır:  ~/.local/share/kavram
#
# Bu kanca, kavram.py ve programların kullandığı "export" ve "veri" klasörlerini kullanıcı dizinine
# bağlar (sembolik bağlantı) ve KAVRAM_VERI ortam değişkenini ayarlar (media gibi programlar bunu okur).
# Kaynak (paketsiz) çalışmada hiçbir şey yapmaz.

import os
import sys

if getattr(sys, "frozen", False):
    _veri_koku = os.path.join(os.path.expanduser("~"), ".local", "share", "kavram")
    os.environ.setdefault("KAVRAM_VERI", _veri_koku)
    try:
        _paket_koku = sys._MEIPASS
        for _ad in ("export", "veri"):
            _gercek = os.path.join(_veri_koku, _ad)
            os.makedirs(_gercek, exist_ok=True)
            _baglanti = os.path.join(_paket_koku, _ad)
            if not os.path.lexists(_baglanti):
                os.symlink(_gercek, _baglanti)
    except OSError:
        # Paket dizini yazılamıyorsa (ör. /opt altında) klasörler paket içinde kalır; uygulama yine açılır.
        pass
