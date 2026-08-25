# -*- mode: python ; coding: utf-8 -*-

import sys
import os
import glob
import ctypes.util
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None
base_path = os.path.abspath(".")

def find_sys_lib(lib_name, fallback_paths):
    """Sistemdeki veya yerel dizindeki .so dosyasını dinamik bulur."""
    found = ctypes.util.find_library(lib_name)
    if found:
        if os.path.isabs(found) and os.path.exists(found):
            return found
    for path in fallback_paths:
        matches = glob.glob(path)
        if matches:
            return matches[0]
    return None

# --- HIDDEN IMPORTS ---
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

# --- BINARIES (.so & Kütüphaneler) ---
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
    'librnnoise.so',
    'librnnoise.so.0',
    'libdeepfilter.so'
]

for lib in custom_libs:
    src_candidates = [
        os.path.join(base_path, lib),
        os.path.join(base_path, 'lib', lib)
    ]
    src = next((c for c in src_candidates if os.path.exists(c)), None)
    if src:
        binaries.append((src, 'lib'))
    else:
        print(f"[UYARI] Özel kütüphane dizinde bulunamadı: {lib}")

# Sistem ses kütüphaneleri (PortAudio, ALSA)
portaudio_path = find_sys_lib('portaudio', [
    '/usr/lib*/libportaudio.so*',
    '/usr/lib/*-linux-gnu/libportaudio.so*'
])
if portaudio_path:
    binaries.append((portaudio_path, 'lib'))
    print(f"[BİLGİ] PortAudio eklendi: {portaudio_path}")

alsa_path = find_sys_lib('asound', [
    '/usr/lib*/libasound.so*',
    '/usr/lib/*-linux-gnu/libasound.so*'
])
if alsa_path:
    binaries.append((alsa_path, 'lib'))
    print(f"[BİLGİ] ALSA eklendi: {alsa_path}")

# FFmpeg ve Yardımcı İcrada Edilebilir Dosyalar (Kavram/ffmpeg/ altında taşınır)
executables = ['ffmpeg', 'ffprobe', 'ffplay']
for exe in executables:
    src_candidates = [
        os.path.join(base_path, 'ffmpeg', exe),
        os.path.join(base_path, exe),
        os.path.join(base_path, 'bin', exe)
    ]
    src = next((c for c in src_candidates if os.path.exists(c)), None)
    if src:
        # ffmpeg klasörü altında çalışacak şekilde paketlenir
        binaries.append((src, 'ffmpeg'))
        print(f"[BİLGİ] {exe} paketlendi -> ffmpeg/{exe}")
    else:
        print(f"[UYARI] {exe} bulunamadı! Lütfen projenin ffmpeg/ dizinine ekleyin.")

# Kamera ve diğer harici çalıştırılabilirler
camera_rec = os.path.join(base_path, 'camera_recorder')
if os.path.exists(camera_rec):
    binaries.append((camera_rec, 'bin'))

# GStreamer Scanner
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

# --- DATAS (Modeller, Statik Dosyalar, Qt Pluginleri) ---
datas = []

# Yapılandırma ve Statik Dosyalar
readonly_files = ['.lua', '.json', '.png', '.glsl', '.txt', '.cfg', '.md', '.onnx', '.pth', '.bin']
for f in os.listdir(base_path):
    full = os.path.join(base_path, f)
    if os.path.isfile(full) and any(f.endswith(ext) for ext in readonly_files):
        datas.append((full, '.'))

# Klasörler (İkon, Veri, Modeller: RNNoise & DeepFilterNet)
folders = ['ikon', 'veri', 'modeller', 'models', 'rnnoise', 'deepfilter']
for folder in folders:
    src = os.path.join(base_path, folder)
    if os.path.exists(src):
        datas.append((src, folder))
        print(f"[BİLGİ] Klasör paketlendi: {folder}")

# Qt Pluginlerinin Eksiksiz Paketlenmesi (xcb, imageformats, styles, xcbglintegrations vs.)
qt_plugin_dirs = [
    os.path.join(sys.prefix, 'lib', f'python{sys.version_info.major}.{sys.version_info.minor}', 'site-packages', 'PyQt5', 'Qt5', 'plugins'),
    '/usr/lib*/qt5/plugins',
    '/usr/lib/*-linux-gnu/qt5/plugins',
    '/usr/lib*/qt/plugins'
]
base_qt_dir = None
for d in qt_plugin_dirs:
    if os.path.exists(d):
        base_qt_dir = d
        print(f"[BİLGİ] Qt Plugin dizini bulundu: {d}")
        break

if base_qt_dir:
    subdirs = ['platforms', 'imageformats', 'styles', 'xcbglintegrations', 'mediaservice', 'audio', 'iconengines', 'platformthemes', 'platforminputcontexts']
    for sd in subdirs:
        target_dir = os.path.join(base_qt_dir, sd)
        if os.path.exists(target_dir):
            for file_path in glob.glob(os.path.join(target_dir, '*')):
                if os.path.isfile(file_path):
                    datas.append((file_path, f'PyQt5/Qt5/plugins/{sd}'))

# GStreamer Pluginleri
gst_plugin_dirs = ['/usr/lib*/gstreamer-1.0', '/usr/lib/*-linux-gnu/gstreamer-1.0']
for d in gst_plugin_dirs:
    matches = glob.glob(d)
    if matches:
        for plugin in glob.glob(os.path.join(matches[0], '*.so')):
            datas.append((plugin, 'gstreamer-1.0'))
        break

# --- RUNTIME HOOK ---
hook_path = os.path.join(base_path, 'auto_env_hook.py')
runtime_hooks = [hook_path]

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
    icon='ikon/Kavram.png'
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
