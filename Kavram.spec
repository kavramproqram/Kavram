# -*- mode: python ; coding: utf-8 -*-

# Bu dosya, Kavram uygulaması için PyInstaller yapılandırmasını içerir.
# GStreamer (ses/video işlemleri) ve diğer .so kütüphanelerinin paketlenmiş
# uygulamada doğru çalışması için özel olarak yapılandırılmıştır.

import os

# 'lupa' modülünün dosyalarını sanal ortam (venv) içinden bulmak için
# güvenilir bir yol.
lupa_dir = os.path.join(os.getcwd(), 'venv', 'lib', 'python3.13', 'site-packages', 'lupa')

a = Analysis(
    ['Kavram.py'],
    pathex=['.'],
    binaries=[
        # Projenizin kendi C++ .so kütüphaneleri.
        ('camera_backend.so', '.'),
        ('libmediaengine.so', '.'),
        ('libsound_engine.so', '.'),

        # Not: Aşağıdaki sistem kütüphanelerinin birçoğu PyInstaller tarafından
        # otomatik olarak bulunabilir. Eğer sorun yaşanmazsa, bu listeyi
        # sadeleştirmeyi düşünebilirsiniz. Şimdilik, her şeyin dahil
        # edildiğinden emin olmak için bu şekilde bırakıyoruz.
        ('/usr/lib/libopencv_core.so.412', '.'),
        ('/usr/lib/libopencv_highgui.so.412', '.'),
        ('/usr/lib/libopencv_imgproc.so.412', '.'),
        ('/usr/lib/libopencv_videoio.so.412', '.'),
        ('/usr/lib/libopencv_imgcodecs.so.412', '.'),
        # Lua kütüphanesini 'binaries' listesine ekleyerek paketlenmesini garantiliyoruz.
        ('/usr/lib/liblua.so.5.4', '.'),
        ('/usr/lib/libavformat.so.61', '.'),
        ('/usr/lib/libavcodec.so.61', '.'),
        ('/usr/lib/libswscale.so.8', '.'),
        ('/usr/lib/libavutil.so.59', '.'),
        ('/usr/lib/libswresample.so.5', '.'),
        ('/usr/lib/libgstbase-1.0.so.0', '.'),
        ('/usr/lib/libgstreamer-1.0.so.0', '.'),
        ('/usr/lib/libgobject-2.0.so.0', '.'),
        ('/usr/lib/libglib-2.0.so.0', '.'),
        ('/usr/lib/libgstapp-1.0.so.0', '.'),
        ('/usr/lib/libgstriff-1.0.so.0', '.'),
        ('/usr/lib/libgstpbutils-1.0.so.0', '.'),
        ('/usr/lib/libgstvideo-1.0.so.0', '.'),
        ('/usr/lib/libgstaudio-1.0.so.0', '.'),
        ('/usr/lib/libgsttag-1.0.so.0', '.'),
        ('/usr/lib/libtbb.so.12', '.'),
        ('/usr/lib/libvpx.so.9', '.'),
        ('/usr/lib/libx264.so.164', '.'),
        ('/usr/lib/libx265.so.215', '.'),
        ('/usr/lib/libaom.so.3', '.'),
        ('/usr/lib/libdav1d.so.7', '.'),
        ('/usr/lib/libxml2.so.16', '.'),
        ('/usr/lib/libbluray.so.2', '.'),
        ('/usr/lib/libsrt.so.1.5', '.'),
        ('/usr/lib/libssh.so.4', '.'),
        ('/usr/lib/libzmq.so.5', '.'),
        ('/usr/lib/libcrypto.so.3', '.'),
    ],

    datas=[
        # Uygulamanın ihtiyaç duyduğu tüm ek dosyalar (ikonlar, ayarlar, scriptler vb.)
        ('ikon', 'ikon'),
        ('filter_settings c33.json', '.'),
        ('blue_light_filter_settings.json', '.'),
        ('timeline_logic.lua', '.'),
        (lupa_dir, 'lupa'),

        # --- GStreamer HATALARINI ÇÖZMEK İÇİN EKLENEN BÖLÜM ---
        # GStreamer'ın çalışmak için ihtiyaç duyduğu tüm eklentileri (.so dosyaları)
        # paketimizin içine 'gstreamer-1.0' adında bir klasöre kopyalıyoruz.
        # Bu yol Arch/EndeavourOS için standart yoldur.
        ('/usr/lib/gstreamer-1.0', 'gstreamer-1.0')
    ],
    hiddenimports=[
        # PyInstaller'ın otomatik olarak bulamadığı modüller.
        'sphere', 'kare', 'text_editor', 'Drawing_editor', 'sound_GUI',
        'ai_editor', 'media_editor', 'camera_editor', 'copya',
        'Animation_editor', 'Settings', 'filtre', 'convert',
        'soundfile', 'numpy', 'noisereduce', 'scipy', 'scipy.signal',
        'librosa', 'pydub', 'lupa', 'cv2', 'moviepy',
        'PyQt5.sip', 'PyQt5.QtSvg',
    ],
    hookspath=[],
    hooksconfig={
        'QT_PLUGIN_PATH': ['{abs_path}']
    },
    # --- GStreamer HATALARINI ÇÖZMEK İÇİN EKLENEN BÖLÜM ---
    # Uygulama başladığında çalışacak olan ve GStreamer'a eklentilerinin
    # nerede olduğunu söyleyecek olan hook dosyamız.
    runtime_hooks=['runtime_hook.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Kavram',
    debug=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
