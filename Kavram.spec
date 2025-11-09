# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
base_path = os.path.abspath(".")

# --- Hidden imports (tüm modüller, collect_submodules ile genişletildi) ---
hiddenimports = (
    collect_submodules('PyQt5') +
    collect_submodules('cv2') +
    collect_submodules('lupa') +  # Lua için genişletildi
    collect_submodules('numpy') +
    collect_submodules('scipy') +
    collect_submodules('librosa') +
    collect_submodules('soundfile') +
    collect_submodules('pydub') +
    collect_submodules('noisereduce') +
    collect_submodules('pyqtgraph') +
    collect_submodules('matplotlib') +
    collect_submodules('pyyaml') +
    collect_submodules('tqdm') +
    collect_submodules('PyPDF2') +
    collect_submodules('pycryptodome') +
    collect_submodules('pyaudio') +
    collect_submodules('sounddevice') +
    # Uygulama modülleri ve ekstra (warn.txt'den)
    ['sphere', 'text_editor', 'Drawing_editor', 'sound_GUI', 'ai_editor', 'media_editor',
     'camera_editor', 'copya', 'Settings', 'filtre', 'convert', 'button_styles',
     'filter_settings_dialog', 'gui', 'kare', 'skript', 'Core', 'importlib_resources',
     'sip'] +  # scipy.special._cdflib kaldırıldı (opsiyonel, hata vermez)
    # Lua binding'leri için ekstra
    ['lupa.lua54', 'lupa.LuaRuntime']
)

# --- Binaries (tüm .so ve kütüphaneler, sistem kurulumuna göre) ---
binaries = []

# OpenCV kütüphaneleri (kurulumdaki 4.6 versiyonu)
opencv_libs = [
    '/usr/lib/x86_64-linux-gnu/libopencv_core.so.406',
    '/usr/lib/x86_64-linux-gnu/libopencv_imgproc.so.406',
    '/usr/lib/x86_64-linux-gnu/libopencv_highgui.so.406',
    '/usr/lib/x86_64-linux-gnu/libopencv_videoio.so.406',
    '/usr/lib/x86_64-linux-gnu/libopencv_imgcodecs.so.406',
    '/usr/lib/x86_64-linux-gnu/libopencv_video.so.406',
    '/usr/lib/x86_64-linux-gnu/libopencv_features2d.so.406',
    '/usr/lib/x86_64-linux-gnu/libopencv_flann.so.406',
    '/usr/lib/x86_64-linux-gnu/libopencv_calib3d.so.406',
    '/usr/lib/x86_64-linux-gnu/libopencv_objdetect.so.406',
    '/usr/lib/x86_64-linux-gnu/libopencv_photo.so.406',
]

# Diğer kütüphaneler (kurulumdan: Lua, PortAudio, ALSA, JACK, Pulse, FFmpeg, Qt Multimedia, GStreamer, X11, OpenGL, vs.)
other_libs = [
    '/usr/lib/x86_64-linux-gnu/liblua5.4.so.0',  # Lua 5.4 (kritik - lupa için)
    '/usr/lib/x86_64-linux-gnu/libportaudio.so.2',
    '/usr/lib/x86_64-linux-gnu/libsndfile.so.1',
    '/usr/lib/x86_64-linux-gnu/libasound.so.2',
    '/usr/lib/x86_64-linux-gnu/libjack.so.0',
    '/usr/lib/x86_64-linux-gnu/libpulse.so.0',
    '/usr/lib/x86_64-linux-gnu/libavcodec.so.60',
    '/usr/lib/x86_64-linux-gnu/libavformat.so.60',
    '/usr/lib/x86_64-linux-gnu/libavutil.so.58',
    '/usr/lib/x86_64-linux-gnu/libswscale.so.7',
    '/usr/lib/x86_64-linux-gnu/libswresample.so.4',
    '/usr/lib/x86_64-linux-gnu/libpostproc.so.57',
    '/usr/lib/x86_64-linux-gnu/libqt5multimedia.so.5',
    '/usr/lib/x86_64-linux-gnu/libqt5multimediawidgets.so.5',
    '/usr/lib/x86_64-linux-gnu/libportaudiocpp.so.0',
    '/usr/lib/x86_64-linux-gnu/libxcb-xinerama.so.0',
    '/usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0',
    '/usr/lib/x86_64-linux-gnu/libxkbcommon-x11.so.0',
    '/usr/lib/x86_64-linux-gnu/libgl.so.1',
    '/usr/lib/x86_64-linux-gnu/libegl.so.1',
    '/usr/lib/x86_64-linux-gnu/libopengl.so.0',
    '/usr/lib/x86_64-linux-gnu/libpng16.so.16',
    '/usr/lib/x86_64-linux-gnu/libz.so.1',
    '/usr/lib/x86_64-linux-gnu/libjpeg.so.8',
    '/usr/lib/x86_64-linux-gnu/libfreetype.so.6',
    '/usr/lib/x86_64-linux-gnu/libharfbuzz.so.0',
    '/usr/lib/x86_64-linux-gnu/libglib-2.0.so.0',
    '/usr/lib/x86_64-linux-gnu/libgobject-2.0.so.0',
    '/usr/lib/x86_64-linux-gnu/libfontconfig.so.1',
    '/usr/lib/x86_64-linux-gnu/libdbus-1.so.3',
    '/usr/lib/x86_64-linux-gnu/libgstreamer-1.0.so.0',
    '/usr/lib/x86_64-linux-gnu/libgstbase-1.0.so.0',
    '/usr/lib/x86_64-linux-gnu/libgstaudio-1.0.so.0',
    '/usr/lib/x86_64-linux-gnu/libgstvideo-1.0.so.0',
    '/usr/lib/x86_64-linux-gnu/libgstapp-1.0.so.0',
    '/usr/lib/x86_64-linux-gnu/libgstpbutils-1.0.so.0',
    '/usr/lib/x86_64-linux-gnu/libgstgl-1.0.so.0',
    '/usr/lib/x86_64-linux-gnu/libgmodule-2.0.so.0',
    '/usr/lib/x86_64-linux-gnu/libffi.so.8',
    '/usr/lib/x86_64-linux-gnu/libpcre2-8.so.0',
    '/usr/lib/x86_64-linux-gnu/libXrender.so.1',
    '/usr/lib/x86_64-linux-gnu/libxcb-render.so.0',
    '/usr/lib/x86_64-linux-gnu/libpixman-1.so.0',
    '/usr/lib/x86_64-linux-gnu/libogg.so.0',
    '/usr/lib/x86_64-linux-gnu/libvorbis.so.0',
    '/usr/lib/x86_64-linux-gnu/libvorbisenc.so.2',
    '/usr/lib/x86_64-linux-gnu/libFLAC.so.12',
    '/usr/lib/x86_64-linux-gnu/libopus.so.0',
    '/usr/lib/x86_64-linux-gnu/libmp3lame.so.0',
    '/usr/lib/x86_64-linux-gnu/libmpg123.so.0',
    '/usr/lib/x86_64-linux-gnu/libvorbisfile.so.3',
    '/usr/lib/x86_64-linux-gnu/libtheoraenc.so.1',
    '/usr/lib/x86_64-linux-gnu/libtheoradec.so.1',
    '/usr/lib/x86_64-linux-gnu/libtwolame.so.0',
    '/usr/lib/x86_64-linux-gnu/libspeex.so.1',
    '/usr/lib/x86_64-linux-gnu/libwebp.so.7',
    '/usr/lib/x86_64-linux-gnu/libtiff.so.6',
    '/usr/lib/x86_64-linux-gnu/libopenjp2.so.7',
    '/usr/lib/x86_64-linux-gnu/libOpenEXR-3_1.so.30',
    '/usr/lib/x86_64-linux-gnu/libgdal.so.34',
    '/usr/lib/x86_64-linux-gnu/libheif.so.1',
    '/usr/lib/x86_64-linux-gnu/librsvg-2.so.2',
    '/usr/lib/x86_64-linux-gnu/libproj.so.25',
    '/usr/lib/x86_64-linux-gnu/libgeos_c.so.1',
    '/usr/lib/x86_64-linux-gnu/libsqlite3.so.0',
    '/usr/lib/x86_64-linux-gnu/libGLX.so.0',
    '/usr/lib/x86_64-linux-gnu/libGLdispatch.so.0',
    '/usr/lib/x86_64-linux-gnu/libX11.so.6',
    '/usr/lib/x86_64-linux-gnu/libxcb.so.1',
    '/usr/lib/x86_64-linux-gnu/libXext.so.6',
    '/usr/lib/x86_64-linux-gnu/libXfixes.so.3',
    '/usr/lib/x86_64-linux-gnu/libX11-xcb.so.1',
    '/usr/lib/x86_64-linux-gnu/libxcb-dri3.so.0',
    '/usr/lib/x86_64-linux-gnu/libxcb-shape.so.0',
    '/usr/lib/x86_64-linux-gnu/libxcb-shm.so.0',
    '/usr/lib/x86_64-linux-gnu/libxcb-present.so.0',
    '/usr/lib/x86_64-linux-gnu/libxcb-sync.so.1',
    '/usr/lib/x86_64-linux-gnu/libxshmfence.so.1',
    '/usr/lib/x86_64-linux-gnu/libXxf86vm.so.1',
    '/usr/lib/x86_64-linux-gnu/libdrm.so.2',
    '/usr/lib/x86_64-linux-gnu/libpciaccess.so.0',
    '/usr/lib/x86_64-linux-gnu/libdrm_amdgpu.so.1',
    '/usr/lib/x86_64-linux-gnu/libdrm_intel.so.1',
    '/usr/lib/x86_64-linux-gnu/libedit.so.2',
    '/usr/lib/x86_64-linux-gnu/libelf.so.1',
    '/usr/lib/x86_64-linux-gnu/libsensors.so.5',
    '/usr/lib/x86_64-linux-gnu/libLLVM.so.19',
    '/usr/lib/x86_64-linux-gnu/libgallium-25.0.7-0ubuntu0.24.04.1.so',
    '/usr/lib/x86_64-linux-gnu/libexpat.so.1',
    '/usr/lib/x86_64-linux-gnu/libgssapi_krb5.so.2',
    '/usr/lib/x86_64-linux-gnu/libk5crypto.so.3',
    '/usr/lib/x86_64-linux-gnu/libkrb5.so.3',
    '/usr/lib/x86_64-linux-gnu/libkrb5support.so.0',
    '/usr/lib/x86_64-linux-gnu/libkeyutils.so.1',
    '/usr/lib/x86_64-linux-gnu/libcom_err.so.2',
    '/usr/lib/x86_64-linux-gnu/libbz2.so.1',
    '/usr/lib/x86_64-linux-gnu/liblzma.so.5',
    '/usr/lib/x86_64-linux-gnu/libmvec.so.1',
    '/usr/lib/x86_64-linux-gnu/libtinfo.so.6',
    '/usr/lib/x86_64-linux-gnu/libxml2.so.2',
    '/usr/lib/x86_64-linux-gnu/libgthread-2.0.so.0',
    '/usr/lib/x86_64-linux-gnu/libpulse-mainloop-glib.so.0',
    '/usr/lib/x86_64-linux-gnu/libgstreamer-plugins-base-1.0.so.0',
    '/lib/x86_64-linux-gnu/liblapack.so.3',
    '/lib/x86_64-linux-gnu/libblas.so.3',
    '/usr/lib/x86_64-linux-gnu/libgfortran.so.5',
    '/usr/lib/x86_64-linux-gnu/libquadmath.so.0',
    '/usr/lib/x86_64-linux-gnu/libtbb.so.12',
    '/usr/lib/x86_64-linux-gnu/libgstriff-1.0.so.0',
    '/usr/lib/x86_64-linux-gnu/libgsttag-1.0.so.0',
    '/usr/lib/x86_64-linux-gnu/libbrotlicommon.so.1',
    '/usr/lib/x86_64-linux-gnu/libbrotlidec.so.1',
    '/usr/lib/x86_64-linux-gnu/libbrotlienc.so.1',
    '/usr/lib/x86_64-linux-gnu/libicuuc.so.74',
    '/usr/lib/x86_64-linux-gnu/libicudata.so.74',
    '/usr/lib/x86_64-linux-gnu/libgomp.so.1',
    '/usr/lib/x86_64-linux-gnu/libbsd.so.0',
    '/usr/lib/x86_64-linux-gnu/libmd.so.0',
    # Lua bağımlılıkları (eklendi - lupa için)
    '/lib/x86_64-linux-gnu/libm.so.6',
    '/lib/x86_64-linux-gnu/libpthread.so.0',
]

# Tüm lib'leri binaries'e ekle, sadece var olanları
for lib in opencv_libs + other_libs:
    if os.path.exists(lib):
        binaries.append((lib, 'lib'))  # 'lib' dizinine kopyala (runtime PATH için)

# Uygulama .so'ları root'a
binaries += [
    (os.path.join(base_path, 'libmediaengine.so'), '.'),
    (os.path.join(base_path, 'libsound_engine.so'), '.'),
    (os.path.join(base_path, 'camera_backend.so'), '.'),
    (os.path.join(base_path, 'camera_backend.cpython-312-x86_64-linux-gnu.so'), '.'),  # Eğer varsa
]

# FFmpeg ve FFprobe binary (root'a)
# FFprobe'u da ekleyerek süre/bilgi sorgulama hatalarını gideriyoruz.
if os.path.exists('/usr/bin/ffmpeg'):
    binaries.append(('/usr/bin/ffmpeg', '.'))
if os.path.exists('/usr/bin/ffprobe'):  # <<< FFprobe eklendi!
    binaries.append(('/usr/bin/ffprobe', '.'))

# --- Datas (Lua, JSON, ikon, dizinler dinamik tarama ile) ---
datas = [
    (os.path.join(base_path, 'timeline_logic.lua'), '.'),  # Lua root'a kesin ekle (kritik)
    (os.path.join(base_path, 'ikon/Kavram.png'), 'ikon'),
    (os.path.join(base_path, 'filter_settings c33.json'), '.'),  # Boşluklu JSON - iç tırnaklar kaldırıldı
    # Diğer JSON'lar eğer varsa
    ('filter_settings*.json', '.'),  # Tüm filter_settings JSON'ları
]

# Proje kökünden tüm dosyaları tara (venv/dist/build/__pycache__ hariç)
exclude_dirs = ['venv', 'dist', 'build', '__pycache__']
for root, dirs, files in os.walk(base_path):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for f in files:
        if f.endswith(('.py', '.lua', '.json', '.png', '.sh', '.cpp', '.txt')):  # Genişletilmiş uzantılar
            full_path = os.path.join(root, f)
            rel_dir = os.path.relpath(root, base_path)
            datas.append((full_path, rel_dir))

# Dizin içeriklerini ekle (Export, medya_cut, _v&s_)
datas += [
    (os.path.join(base_path, 'Export/*'), 'Export'),
    (os.path.join(base_path, 'medya_cut/*'), 'medya_cut'),
    (os.path.join(base_path, '_v&s_/*'), '_v&s_'),
]

# Qt plugin'leri (var olanları ekle)
qt_plugin_dirs = [
    ('/usr/lib/x86_64-linux-gnu/qt5/plugins/platforms/*', 'platforms'),
    ('/usr/lib/x86_64-linux-gnu/qt5/plugins/imageformats/*', 'imageformats'),
    ('/usr/lib/x86_64-linux-gnu/qt5/plugins/mediaservice/*', 'mediaservice'),
    ('/usr/lib/x86_64-linux-gnu/qt5/plugins/audio/*', 'audio'),
    ('/usr/lib/x86_64-linux-gnu/qt5/plugins/iconengines/*', 'iconengines'),
]

for src, dest in qt_plugin_dirs:
    src_dir = src.rstrip('/*')
    if os.path.exists(src_dir):
        datas.append((src, dest))

# GStreamer plugin'leri (medya için)
gstreamer_dir = '/usr/lib/x86_64-linux-gnu/gstreamer-1.0'
if os.path.exists(gstreamer_dir):
    datas.append((os.path.join(gstreamer_dir, '*'), 'gstreamer-1.0'))

# --- Analysis ---
a = Analysis(
    ['Kavram.py'],
    pathex=[base_path],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['lua_loader.py', 'path_fix_hook.py'],
    excludes=[
        'tkinter', 'tcl', 'tk', 
        'torch', 'tensorflow', 'pytest',  # Ekstra excludes - boyut küçült
        'matplotlib.tests', 'numpy.tests', 'scipy.tests'  # Test modülleri hariç
    ],
    noarchive=False,
)

# --- PYZ ve EXE (tek dosya modu) ---
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],  # Tek dosya için binaries/zipfiles/datas boş
    exclude_binaries=True,  # Tek dosya için
    name='Kavram',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='x86_64',
    codesign_identity=None,
    entitlements_file=None,
    # Icon kaldırıldı - Linux'ta uyarı veriyor
)

# --- COLLECT (tek dosya için her şeyi EXE'ye topla) ---
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Kavram',
)
