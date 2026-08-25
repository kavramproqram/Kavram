import os
import sys
import stat

if hasattr(sys, '_MEIPASS'):
    meipass = sys._MEIPASS

    # 1. Qt Plugin Yolları
    qt_plugin_path = os.path.join(meipass, 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(qt_plugin_path):
        os.environ['QT_PLUGIN_PATH'] = qt_plugin_path

    # 2. GStreamer Yolları
    gst_path = os.path.join(meipass, 'gstreamer-1.0')
    if os.path.exists(gst_path):
        os.environ['GST_PLUGIN_SYSTEM_PATH'] = gst_path
        os.environ['GST_PLUGIN_PATH'] = gst_path

    gst_scanner = os.path.join(meipass, 'gst-plugin-scanner')
    if os.path.exists(gst_scanner):
        os.environ['GST_PLUGIN_SCANNER'] = gst_scanner

    # Linux Mint / GStreamer VA-API ve GL ayarları
    os.environ["GST_VAAPI_ALL_DRIVERS"] = "0"
    os.environ["GST_GL_API"] = "opengl"

    # 3. PATH Güncellemesi (FFmpeg / FFprobe / FFplay erişimi için)
    bin_dir = os.path.join(meipass, 'bin')
    if os.path.exists(bin_dir):
        os.environ['PATH'] = bin_dir + os.pathsep + os.environ.get('PATH', '')

    # 4. LD_LIBRARY_PATH Güncellemesi (C++ .so ve FFmpeg kütüphaneleri için)
    lib_dir = os.path.join(meipass, 'lib')
    ld_paths = [lib_dir, meipass]
    existing_ld = os.environ.get('LD_LIBRARY_PATH', '')
    if existing_ld:
        ld_paths.append(existing_ld)
    os.environ['LD_LIBRARY_PATH'] = os.pathsep.join(filter(None, ld_paths))

    # 5. FFmpeg / FFprobe / FFplay Yürütme İzinlerini (chmod +x) Doğrulama
    if sys.platform.startswith('linux') or sys.platform == 'darwin':
        for exe in ['ffmpeg', 'ffprobe', 'ffplay']:
            exe_p = os.path.join(bin_dir, exe)
            if os.path.exists(exe_p):
                try:
                    st = os.stat(exe_p)
                    os.chmod(exe_p, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
                except Exception:
                    pass
