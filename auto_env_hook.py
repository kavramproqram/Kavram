import os
import sys
import glob

# ==============================================================================
# 1. ÇALIŞMA KÜTÜPHANELERİ VE ORTAM DEĞİŞKENLERİ HAZIRLIĞI
# ==============================================================================
if hasattr(sys, '_MEIPASS'):
    meipass = sys._MEIPASS

    # 1. Qt Plugin Yolları ve XCB Hatası Önleme
    qt_plugin_path = os.path.join(meipass, 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(qt_plugin_path):
        os.environ['QT_PLUGIN_PATH'] = qt_plugin_path
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(qt_plugin_path, 'platforms')

    # 2. FFmpeg Yolunun Ortama Eklenmesi (Gömülü ffmpeg/ffmpeg)
    ffmpeg_dir = os.path.join(meipass, 'ffmpeg')
    bin_dir = os.path.join(meipass, 'bin')
    
    path_entries = [ffmpeg_dir, bin_dir, meipass]
    existing_path = os.environ.get('PATH', '')
    for p in path_entries:
        if os.path.exists(p):
            os.environ['PATH'] = p + os.pathsep + os.environ.get('PATH', '')

    # 3. Dinamik Kütüphaneler (.so) İçin LD_LIBRARY_PATH Yapılandırması
    lib_dir = os.path.join(meipass, 'lib')
    ld_paths = [lib_dir, meipass]
    for ld in ld_paths:
        if os.path.exists(ld):
            os.environ['LD_LIBRARY_PATH'] = ld + os.pathsep + os.environ.get('LD_LIBRARY_PATH', '')

    # 4. GStreamer Yolları
    gst_path = os.path.join(meipass, 'gstreamer-1.0')
    if os.path.exists(gst_path):
        os.environ['GST_PLUGIN_SYSTEM_PATH'] = gst_path
        os.environ['GST_PLUGIN_PATH'] = gst_path

    gst_scanner = os.path.join(meipass, 'gst-plugin-scanner')
    if os.path.exists(gst_scanner):
        os.environ['GST_PLUGIN_SCANNER'] = gst_scanner

    # 5. Display ve Wayland / XCB Ortam Kontrolü
    session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
    if session_type == 'wayland' and 'WAYLAND_DISPLAY' in os.environ:
        pass
    else:
        os.environ['QT_QPA_PLATFORM'] = 'xcb'
        if 'DISPLAY' not in os.environ:
            x_sockets = glob.glob('/tmp/.X11-unix/X*')
            if x_sockets:
                x_sockets.sort(key=lambda s: int(s.replace('/tmp/.X11-unix/X', '')))
                os.environ['DISPLAY'] = ':' + x_sockets[-1].replace('/tmp/.X11-unix/X', '')
            else:
                os.environ['DISPLAY'] = ':0'

# ==============================================================================
# 2. İLK AÇILIŞTA KULLANICI DİZİNLERİNİ OTOMATİK OLUŞTURMA
# ~/.local/share/Kavram/{cache, logs, projects, autosave, plugins, themes}
# ==============================================================================
user_data_base = os.path.expanduser('~/.local/share/Kavram')
required_directories = [
    'cache',
    'logs',
    'projects',
    'autosave',
    'plugins',
    'themes'
]

for sub_dir in required_directories:
    target_path = os.path.join(user_data_base, sub_dir)
    try:
        os.makedirs(target_path, exist_ok=True)
    except Exception as err:
        print(f"[Kavram Hook] Dizin oluşturulamadı ({target_path}): {err}")
