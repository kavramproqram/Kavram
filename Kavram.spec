# -*- mode: python ; coding: utf-8 -*-

import sys
import os
import glob
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
base_path = os.path.abspath(".")

# ------------------------------------------------------------
# 1. GİZLİ İÇE AKTARIMALAR (Hidden Imports)
# ------------------------------------------------------------
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
    # collect_submodules('webrtcvad')  # <-- KALDIRILDI
    [
        'sphere', 'text_editor', 'Drawing_editor', 'sound_GUI', 'ai_editor',
        'media_editor', 'camera_editor', 'copya', 'Settings', 'filtre',
        'convert', 'button_styles', 'filter_settings_dialog', 'gui', 'kare',
        'skript', 'Zaman', 'Geometri', 'Core', 'importlib_resources', 'sip',
        'lupa.lua54', 'lupa.LuaRuntime'
    ]
)

# ------------------------------------------------------------
# 2. BİNARY DOSYALAR (sadece projeye özel)
# ------------------------------------------------------------
binaries = []

# 2.1 Özel C++ kütüphaneleri -> lib/ klasörüne
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
        print(f"[BİLGİ] Kütüphane eklendi: {lib} -> lib/")
    else:
        print(f"[UYARI] Kütüphane bulunamadı: {lib}")

# 2.2 PortAudio ve ALSA kütüphaneleri (ses için)
portaudio_lib = '/usr/lib/x86_64-linux-gnu/libportaudio.so.2'
if os.path.exists(portaudio_lib):
    binaries.append((portaudio_lib, 'lib'))
    print(f"[BİLGİ] PortAudio kütüphanesi eklendi: {portaudio_lib} -> lib/")
else:
    print(f"[UYARI] PortAudio kütüphanesi bulunamadı: {portaudio_lib}")

alsa_lib = '/usr/lib/x86_64-linux-gnu/libasound.so.2'
if os.path.exists(alsa_lib):
    binaries.append((alsa_lib, 'lib'))
    print(f"[BİLGİ] ALSA kütüphanesi eklendi: {alsa_lib} -> lib/")
else:
    print(f"[UYARI] ALSA kütüphanesi bulunamadı: {alsa_lib}")

# 2.3 Çalıştırılabilir dosyalar -> bin/ klasörüne
executables = [
    'camera_recorder',
    'ffmpeg',
    'ffprobe',
    'ffplay',
]

for exe in executables:
    src_candidates = [
        os.path.join(base_path, exe),
        os.path.join(base_path, 'bin', exe)
    ]
    src = None
    for candidate in src_candidates:
        if os.path.exists(candidate):
            src = candidate
            break
    if src:
        binaries.append((src, 'bin'))
        print(f"[BİLGİ] Binary eklendi: {os.path.basename(src)} -> bin/")
    else:
        print(f"[UYARI] Binary bulunamadı: {exe}")

# 2.4 GStreamer plugin scanner (isteğe bağlı)
gst_scanners = [
    '/usr/lib/x86_64-linux-gnu/gstreamer1.0/gstreamer-1.0/gst-plugin-scanner',
    '/usr/lib/x86_64-linux-gnu/gstreamer-1.0/gst-plugin-scanner',
    '/usr/libexec/gstreamer-1.0/gst-plugin-scanner'
]
for scanner in gst_scanners:
    if os.path.exists(scanner):
        binaries.append((scanner, '.'))
        print(f"[BİLGİ] GStreamer scanner eklendi: {scanner}")
        break

# ------------------------------------------------------------
# 3. DATA DOSYALARI (JSON, Lua, ikon, veri, vs.)
# ------------------------------------------------------------
datas = []

# Kök dizindeki veri dosyaları
for f in os.listdir(base_path):
    full = os.path.join(base_path, f)
    if os.path.isfile(full) and f.endswith(('.lua', '.json', '.png', '.glsl', '.txt', '.cfg', '.md')):
        datas.append((full, '.'))

# Klasörler - her klasörü kontrol et, yoksa oluştur
folders = ['ikon', 'Export', 'medya_cut', '_v&s_', 'Zaman_Veri', 'veri']
for folder in folders:
    src = os.path.join(base_path, folder)
    # Klasör yoksa oluştur (boş da olsa)
    if not os.path.exists(src):
        os.makedirs(src, exist_ok=True)
        print(f"[BİLGİ] Klasör oluşturuldu: {src}")
    # Klasörü datas'a ekle (içindeki tüm dosyaları değil, klasörün kendisini)
    # PyInstaller, klasörü hedefe kopyalayacak
    datas.append((src, folder))
    print(f"[BİLGİ] Klasör eklendi: {src} -> {folder}")

# Qt eklentileri
qt_plugins = [
    ('/usr/lib/x86_64-linux-gnu/qt5/plugins/platforms/*', 'PyQt5/Qt5/plugins/platforms'),
    ('/usr/lib/x86_64-linux-gnu/qt5/plugins/imageformats/*', 'PyQt5/Qt5/plugins/imageformats'),
    ('/usr/lib/x86_64-linux-gnu/qt5/plugins/mediaservice/*', 'PyQt5/Qt5/plugins/mediaservice'),
    ('/usr/lib/x86_64-linux-gnu/qt5/plugins/audio/*', 'PyQt5/Qt5/plugins/audio'),
    ('/usr/lib/x86_64-linux-gnu/qt5/plugins/iconengines/*', 'PyQt5/Qt5/plugins/iconengines'),
]
for src, dest in qt_plugins:
    dirname = src.rstrip('/*')
    if os.path.exists(dirname):
        datas.append((src, dest))
        print(f"[BİLGİ] Qt eklentisi eklendi: {dirname}")

# GStreamer eklentileri
gst_dir = '/usr/lib/x86_64-linux-gnu/gstreamer-1.0'
if os.path.exists(gst_dir):
    datas.append((os.path.join(gst_dir, '*'), 'gstreamer-1.0'))
    print(f"[BİLGİ] GStreamer eklentileri eklendi: {gst_dir}")

# ------------------------------------------------------------
# 4. RUNTIME HOOK (auto_env_hook.py)
# ------------------------------------------------------------
hook_content = '''import os
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
'''

hook_path = os.path.join(base_path, 'auto_env_hook.py')
with open(hook_path, 'w', encoding='utf-8') as f:
    f.write(hook_content)

runtime_hooks = ['auto_env_hook.py']

# ------------------------------------------------------------
# 5. PyInstaller Analiz
# ------------------------------------------------------------
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
        'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineWidgets',
        'webrtcvad'  # <-- EKLENDI
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
