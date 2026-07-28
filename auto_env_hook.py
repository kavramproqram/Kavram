import os
import sys
import glob

if hasattr(sys, '_MEIPASS'):
    meipass = sys._MEIPASS

    # 1. QT_PLUGIN_PATH
    qt_plugin_path = os.path.join(meipass, 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(qt_plugin_path):
        os.environ['QT_PLUGIN_PATH'] = qt_plugin_path

    # 2. GST_PLUGIN_SYSTEM_PATH
    gst_path = os.path.join(meipass, 'gstreamer-1.0')
    if os.path.exists(gst_path):
        os.environ['GST_PLUGIN_SYSTEM_PATH'] = gst_path
        os.environ['GST_PLUGIN_PATH'] = gst_path

    # 3. GST_PLUGIN_SCANNER
    gst_scanner = os.path.join(meipass, 'gst-plugin-scanner')
    if os.path.exists(gst_scanner):
        os.environ['GST_PLUGIN_SCANNER'] = gst_scanner

    # 4. PATH: bin/ dizinini başa ekle
    bin_dir = os.path.join(meipass, 'bin')
    if os.path.exists(bin_dir):
        os.environ['PATH'] = bin_dir + os.pathsep + os.environ.get('PATH', '')

    # 5. LD_LIBRARY_PATH: lib/ dizinini başa ekle
    lib_dir = os.path.join(meipass, 'lib')
    if os.path.exists(lib_dir):
        os.environ['LD_LIBRARY_PATH'] = lib_dir + os.pathsep + os.environ.get('LD_LIBRARY_PATH', '')

    # 6. X11 / Wayland ortam ayarları
    if 'DISPLAY' not in os.environ:
        os.environ['DISPLAY'] = ':0'
        x_sockets = glob.glob('/tmp/.X11-unix/X*')
        if x_sockets:
            x_sockets.sort(key=lambda s: int(s.replace('/tmp/.X11-unix/X', '')))
            os.environ['DISPLAY'] = ':' + x_sockets[-1].replace('/tmp/.X11-unix/X', '')

    if 'XAUTHORITY' not in os.environ:
        sudo_user = os.environ.get('SUDO_USER')
        if sudo_user:
            os.environ['XAUTHORITY'] = f'/home/{sudo_user}/.Xauthority'
        else:
            home = os.path.expanduser('~')
            os.environ['XAUTHORITY'] = os.path.join(home, '.Xauthority')

    # 7. Qt platform zorlaması
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
