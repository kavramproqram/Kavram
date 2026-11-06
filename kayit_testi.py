#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kayit_testi.py — Windows / macOS kayıt altyapısı denetimi (ekran, mikrofon, kamera)
==================================================================================
Kurulumdan sonra kavram klasöründe çalıştırın (venv içindeki python ile):
    Windows :  venv\\Scripts\\python kayit_testi.py
    macOS   :  ./venv/bin/python kayit_testi.py
Aygıtları listeler ve 3 saniyelik deneme kayıtları yapar; her adımın sonucunu OK / HATA olarak yazar.
Bir adım HATA verirse çıktıyı olduğu gibi paylaşın.  İzin penceresi çıkarsa (kamera / mikrofon / ekran kaydı) izin verip tekrar çalıştırın.
"""
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kavram_capture as kc   # noqa: E402
import kavram_platform as kp  # noqa: E402

SONUC = []


def adim(ad, fonk):
    print(f"\n--- {ad}")
    try:
        ok, bilgi = fonk()
    except Exception as e:                        # noqa: BLE001
        ok, bilgi = False, f"istisna: {e}"
    print(("OK    " if ok else "HATA  ") + str(bilgi))
    SONUC.append((ad, ok))


def ffmpeg_surum():
    r = kc._run([kc.find_tool("ffmpeg"), "-version"], timeout=10)
    return r.returncode == 0, (r.stdout or "").splitlines()[0] if r.stdout else r.stderr[:200]


def aygitlar():
    d = kc.list_av_devices()
    kam = kc.list_cameras()
    mik = kc.list_audio_inputs()
    print("  Kameralar :", kam)
    print("  Mikrofonlar:", mik)
    if kp.IS_MAC:
        print("  Ekranlar  :", [n for _i, n in d["video"] if n.lower().startswith("capture screen")])
    return bool(kam) or bool(mik), f"{len(kam)} kamera, {len(mik)} mikrofon"


def ekran_kaydi():
    tmp = tempfile.mkdtemp(prefix="kavram_test_")
    pat = os.path.join(tmp, "s%d.mkv")
    cmd = kc.screen_record_command(kc.find_tool("ffmpeg"), 15, 854, 480, 60, 1, pat, audio=None)
    cmd = cmd[:-1] + ["-t", "3"] + cmd[-1:]
    print("  komut:", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=40, encoding="utf-8", errors="replace",
                       env=kc.ffmpeg_env(), **kp.hidden_console_kwargs())
    out = os.path.join(tmp, "s1.mkv")
    if r.returncode == 0 and os.path.isfile(out) and os.path.getsize(out) > 2048:
        return True, f"{out} ({os.path.getsize(out) // 1024} KB)"
    if kp.IS_MAC:
        print("  İpucu: Sistem Ayarları → Gizlilik ve Güvenlik → Ekran Kaydı'ndan Terminal / Kavram'a izin verin.")
    return False, (r.stderr or "")[-400:]


def mikrofon():
    import sounddevice  # noqa: F401  (PortAudio yüklenebiliyor mu?)
    tmp = os.path.join(tempfile.mkdtemp(prefix="kavram_test_"), "mik.wav")
    rec = kc.WavRecorder(tmp)
    rec.start()
    time.sleep(2)
    rec.stop()
    import soundfile as sf
    info = sf.info(tmp)
    return info.duration > 1.0, f"{tmp} ({info.duration:.1f} sn)"


def kamera():
    cap = kc.open_capture("", 640, 480, 30)
    if cap is None:
        return False, "kamera açılamadı (izin / başka programda kullanımda?)"
    try:
        for _ in range(10):
            ok, fr = cap.read()
            if ok and fr is not None:
                return True, f"kare alındı: {fr.shape[1]}x{fr.shape[0]}"
            time.sleep(0.1)
        return False, "kameradan kare alınamadı"
    finally:
        cap.release()


def medya_motoru():
    m = kc.MediaCore()
    return m.engine_version() >= 300, f"MediaCore sürüm {m.engine_version()}"


if __name__ == "__main__":
    if kp.IS_LINUX:
        print("Bu araç Windows ve macOS içindir (Linux'ta kayıt C++ motorlarıyla yapılır).")
        sys.exit(0)
    print(f"Kavram kayıt denetimi — {kp.platform_name()} ({sys.platform}), Python {sys.version.split()[0]}")
    adim("FFmpeg", ffmpeg_surum)
    adim("Aygıt listesi", aygitlar)
    adim("Ekran kaydı (3 sn)", ekran_kaydi)
    adim("Mikrofon kaydı (2 sn)", mikrofon)
    adim("Kamera", kamera)
    adim("Medya motoru (Python)", medya_motoru)
    print("\n=== ÖZET ===")
    for ad, ok in SONUC:
        print(("OK    " if ok else "HATA  ") + ad)
    sys.exit(0 if all(ok for _a, ok in SONUC) else 1)
