# lua_loader.py - Lua için runtime hook (çalışma dizinini düzeltir)
import sys
import os

# PyInstaller bundle modda çalışma dizinini _MEIPASS'e taşı
if hasattr(sys, '_MEIPASS'):
    # Temp dizine geç – C++ Lua'yı burada bulur
    os.chdir(sys._MEIPASS)
    print(f"Lua hook yüklendi - Çalışma dizini: {os.getcwd()} (_MEIPASS modu)")
else:
    # Dev modda mevcut dizini kullan
    print("Lua hook yüklendi - Dev modu")

# Ekstra: Lua yolu fonksiyonu (kodunda kullanmak istersen)
def lua_path(relative_path):
    """ Lua için dinamik yol """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        return os.path.join(os.path.dirname(sys.argv[0]), relative_path)

# Test: Lua dosyasının varlığını kontrol et
lua_file = lua_path('timeline_logic.lua')
if os.path.exists(lua_file):
    print(f"Lua dosyası bulundu: {lua_file}")
else:
    print(f"UYARI: Lua dosyası bulunamadı: {lua_file}")
