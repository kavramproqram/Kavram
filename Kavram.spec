# -*- mode: python ; coding: utf-8 -*-

import sys
import os
import glob
import ctypes.util
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
base_path = os.path.abspath(".")

def find_sys_lib(lib_name, fallback_paths):
    """Sistemdeki .so dosyasını dinamik bulur."""
    found = ctypes.util.find_library(lib_name)
    if found:
        if os.path.isabs(found) and os.path.exists(found):
            return found
    for path in fallback_paths:
        matches = glob.glob(path)
        if matches:
            return matches[0]
    return None

hiddenimports = (
    collect_submodules('PyQt5') +
    collect_submodules('cv2') +
    collect_submodules('lupa') +
    collect_submodules('numpy') +
    collect_submodules('scipy') +
    collect_submodules('librosa') +
    collect_submodules('soundfile') +
    collect_submodules('pydub') +
    collect_submodules('noisereduce') +
    collect_submodules('pyqtgraph') +
    collect_submodules('matplotlib') +
    collect_submodules('pyyaml') +
    collect_submodules('PyPDF2') +
    collect_submodules('pycryptodome') +
    collect_submodules('pyaudio') +
    collect_submodules('sounddevice') +
    collect_submodules('tqdm') +
    collect_submodules('pynput') +
    ['pynput.keyboard._xorg', 'pynput.mouse._xorg'] +
    collect_submodules('PIL') +
    collect_submodules('fitz') +
    collect_submodules('pytesseract') +
    collect_submodules('pdf2image') +
    collect_submodules('img2pdf') +
    collect_submodules('psutil') +
    collect_submodules('pyloudnorm') +
    [
        'sphere', 'text_editor', 'Drawing_editor', 'sound_GUI', 'ai_editor',
        'media_editor', 'camera_editor', 'copya', 'filtre',
        'convert', 'button_styles', 'filter_settings_dialog', 'gui', 'kare',
        'skript', 'Zaman', 'Geometri', 'Core', 'importlib_resources', 'sip',
        'lupa.lua54', 'lupa.LuaRuntime'
    ]
)

binaries = []

custom_libs = [
    'libsound_engine.so',
    'libmediaengine.so',
    'libconverter_engine.so',
    'libsoundengine.so',
    'libaudioengine.so',
    'libKavramAudioEngine.so',
    'camera_backend.so',
    'camera_backend.cpython-312-x86_64-linux-gnu.so',
]

for lib in custom_libs:
    src = os.path.join(base_path, lib)
    if os.path.exists(src):
        binaries.append((src, 'lib'))
    else:
        print(f"[UYARI] Kütüphane bulunamadı: {lib}")

portaudio_path = find_sys_lib('portaudio', [
    '/usr/lib*/libportaudio.so*',
    '/usr/lib/*-linux-gnu/libportaudio.so*'
])
if portaudio_path:
    binaries.append((portaudio_path, 'lib'))
    print(f"[BİLGİ] PortAudio bulundu: {portaudio_path}")

alsa_path = find_sys_lib('asound', [
    '/usr/lib*/libasound.so*',
    '/usr/lib/*-linux-gnu/libasound.so*'
])
if alsa_path:
    binaries.append((alsa_path, 'lib'))
    print(f"[BİLGİ] ALSA bulundu: {alsa_path}")

executables = ['camera_recorder', 'ffmpeg', 'ffprobe', 'ffplay']
for exe in executables:
    src_candidates = [os.path.join(base_path, exe), os.path.join(base_path, 'bin', exe)]
    src = next((c for c in src_candidates if os.path.exists(c)), None)
    if src:
        binaries.append((src, 'bin'))

gst_scanners = [
    '/usr/lib*/gstreamer-1.0/gst-plugin-scanner',
    '/usr/lib/*-linux-gnu/gstreamer-1.0/gst-plugin-scanner',
    '/usr/lib/*-linux-gnu/gstreamer1.0/gstreamer-1.0/gst-plugin-scanner',
    '/usr/libexec/gstreamer-1.0/gst-plugin-scanner'
]
for pattern in gst_scanners:
    matches = glob.glob(pattern)
    if matches:
        binaries.append((matches[0], '.'))
        print(f"[BİLGİ] GStreamer scanner eklendi: {matches[0]}")
        break

datas = []

readonly_files = ['.lua', '.json', '.png', '.glsl', '.txt', '.cfg', '.md']
for f in os.listdir(base_path):
    full = os.path.join(base_path, f)
    if os.path.isfile(full) and any(f.endswith(ext) for ext in readonly_files):
        datas.append((full, '.'))

folders = ['ikon', 'veri']
for folder in folders:
    src = os.path.join(base_path, folder)
    if os.path.exists(src):
        datas.append((src, folder))

qt_plugin_dirs = [
    '/usr/lib*/qt5/plugins',
    '/usr/lib/*-linux-gnu/qt5/plugins',
    '/usr/lib*/qt/plugins'
]
base_qt_dir = None
for d in qt_plugin_dirs:
    matches = glob.glob(d)
    if matches:
        base_qt_dir = matches[0]
        break

if base_qt_dir:
    subdirs = ['platforms', 'imageformats', 'mediaservice', 'audio', 'iconengines']
    for sd in subdirs:
        target_dir = os.path.join(base_qt_dir, sd)
        if os.path.exists(target_dir):
            for file_path in glob.glob(os.path.join(target_dir, '*')):
                datas.append((file_path, f'PyQt5/Qt5/plugins/{sd}'))

gst_plugin_dirs = ['/usr/lib*/gstreamer-1.0', '/usr/lib/*-linux-gnu/gstreamer-1.0']
for d in gst_plugin_dirs:
    matches = glob.glob(d)
    if matches:
        for plugin in glob.glob(os.path.join(matches[0], '*.so')):
            datas.append((plugin, 'gstreamer-1.0'))
        break

hook_content = '''import os
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
'''

hook_path = os.path.join(base_path, 'auto_env_hook.py')
with open(hook_path, 'w', encoding='utf-8') as f:
    f.write(hook_content)

runtime_hooks = ['auto_env_hook.py']

a = Analysis(
    ['Kavram.py'],
    pathex=[base_path],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=[
        'torch', 'tensorflow', 'pytest', 'tkinter', 'tcl', 'tk',
        'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineWidgets', 'webrtcvad'
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Kavram',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x86_64',
    codesign_identity=None,
    entitlements_file=None,
    icon='ikon/Kavram.png' # Derlenmiş dosya ikonu (Masaüstü için de geçerli)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Kavram',
)
