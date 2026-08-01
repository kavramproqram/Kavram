import os
import sys
import glob

if hasattr(sys, '_MEIPASS'):
    meipass = sys._MEIPASS

    qt_plugin_path = os.path.join(meipass, 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(qt_plugin_path):
        os.environ['QT_PLUGIN_PATH'] = qt_plugin_path

    gst_path = os.path.join(meipass, 'gstreamer-1.0')
    if os.path.exists(gst_path):
        os.environ['GST_PLUGIN_SYSTEM_PATH'] = gst_path
        os.environ['GST_PLUGIN_PATH'] = gst_path

    gst_scanner = os.path.join(meipass, 'gst-plugin-scanner')
    if os.path.exists(gst_scanner):
        os.environ['GST_PLUGIN_SCANNER'] = gst_scanner

    bin_dir = os.path.join(meipass, 'bin')
    if os.path.exists(bin_dir):
        os.environ['PATH'] = bin_dir + os.pathsep + os.environ.get('PATH', '')

    lib_dir = os.path.join(meipass, 'lib')
    if os.path.exists(lib_dir):
        os.environ['LD_LIBRARY_PATH'] = lib_dir + os.pathsep + os.environ.get('LD_LIBRARY_PATH', '')

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
