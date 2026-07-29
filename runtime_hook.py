# runtime_hook.py
import os
import sys

# PyInstaller tarafından paketlenmiş bir uygulama olarak çalışıp çalışmadığımızı kontrol et
if getattr(sys, 'frozen', False):
    # _MEIPASS, PyInstaller'ın dosyaları geçici olarak çıkardığı klasörün yolunu içerir.
    app_path = sys._MEIPASS

    # 1. GStreamer eklentilerinin yolunu ayarla
    plugin_path = os.path.join(app_path, 'gstreamer-1.0')
    os.environ['GST_PLUGIN_PATH'] = plugin_path

    # 2. GStreamer eklenti tarayıcısının (scanner) yolunu ayarla
    # Bu yardımcı programın paketimizin kök dizininde olacağını varsayıyoruz.
    scanner_path = os.path.join(app_path, 'gst-plugin-scanner')
    os.environ['GST_PLUGIN_SCANNER'] = scanner_path

    print(f"DEBUG: GST_PLUGIN_PATH set to: {plugin_path}")
    print(f"DEBUG: GST_PLUGIN_SCANNER set to: {scanner_path}")
