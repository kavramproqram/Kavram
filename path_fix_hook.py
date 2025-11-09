import sys
import os

if getattr(sys, 'frozen', False):
    base_path_runtime = sys._MEIPASS
    
    # 1. FFmpeg/FFprobe için PATH düzeltmesi (Mevcut)
    os.environ['PATH'] = base_path_runtime + os.pathsep + os.environ['PATH']
    print(f"PATH'e eklendi: {base_path_runtime}")
    
    # 2. GStreamer Eklenti Yolu Düzeltmesi (Yeni eklendi!)
    # Eklentilerin çıkarıldığı dizin (sizin spec dosyanıza göre)
    gstreamer_plugin_path = os.path.join(base_path_runtime, 'gstreamer-1.0')
    
    # GST_PLUGIN_PATH'i ayarlayarak GStreamer'a eklentilerini nerede aramasını söylüyoruz.
    # PyInstaller'ın çıkardığı dizini gösterir.
    os.environ['GST_PLUGIN_PATH'] = gstreamer_plugin_path
    print(f"GST_PLUGIN_PATH ayarlandı: {gstreamer_plugin_path}")
