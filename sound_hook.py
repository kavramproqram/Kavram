import os
import sys
import platform
import subprocess # Yeni eklenti: Kullanıcı ID'sini almak için

if platform.system() == "Linux":
    # --- 1. Dinamik Kütüphane Yolu Fix (Önceki Adım) ---
    if hasattr(sys, '_MEIPASS'):
        library_dir = sys._MEIPASS
    else:
        # Uygulamanın çıkarıldığı (onedir) dizini al
        library_dir = os.path.dirname(sys.executable)

    current_path = os.environ.get('LD_LIBRARY_PATH', '')
    if library_dir not in current_path: # Aynı yolu tekrar eklemeyi önle
        new_path = f"{library_dir}{os.path.sep}{current_path}" if current_path else library_dir
        os.environ['LD_LIBRARY_PATH'] = new_path
    
    # --- 2. Ses Sunucusu Zorlaması (YENİ DESTEKLEYİCİ ADIM) ---

    # A. PortAudio'yu ALSA'nın düşük seviye yerine Pulse/PipeWire'a yönlendir.
    # Bu, PipeWire'ın PulseAudio uyumluluk katmanını kullanmasını teşvik eder.
    if 'PA_ALSA_PLUGHW' not in os.environ:
        os.environ['PA_ALSA_PLUGHW'] = '1'
        print("[SOUND HOOK] PA_ALSA_PLUGHW=1 ayarlandı.")

    # B. PulseAudio/PipeWire sunucusunun adını/socket yolunu zorlamayı dene.
    # Özellikle sandboxing (yalıtım) veya Wayland ortamında IPC sorunlarını çözer.
    
    # Güncel kullanıcı ID'sini al (Soket yolunu belirlemek için)
    try:
        # uname komutunu kullanmak yerine, Python'un os modülünü kullanalım.
        uid = os.getuid()
        
        # PulseAudio/PipeWire'ın varsayılan soket yolu
        default_pulse_socket = f'/run/user/{uid}/pulse/native'
        
        # Eğer PULSE_SERVER ayarlı değilse ve varsayılan soket varsa, zorla.
        if 'PULSE_SERVER' not in os.environ and os.path.exists(default_pulse_socket):
            os.environ['PULSE_SERVER'] = default_pulse_socket
            print(f"[SOUND HOOK] PULSE_SERVER={default_pulse_socket} ayarlandı.")
            
    except Exception as e:
        print(f"[SOUND HOOK] Kullanıcı ID'si veya soket yolu alınamadı: {e}")

    # --- Debug için (PyInstaller'ın warn.txt dosyasına yazılır) ---
    # print(f"[SOUND HOOK] LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH')}")
