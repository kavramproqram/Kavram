"""
_kavram_child.py — Kavram alt-process çalışanı
================================================
Ana GUI process'inden ayrı çalışır.
C++ kütüphanesi segfault verse bile sadece bu process ölür,
GUI sağ kalır ve hata mesajı gösterir.

Çağrı: python3 _kavram_child.py <config_json_path>

config JSON alanları:
  lib_path, in_path, out_path, cover_path (str|null),
  mode, speed, pitch, effect, change_freq, new_freq,
  pdf_invert, pdf_gray, img_invert, img_gray, img_scale,
  progress_file, error_file
"""
import sys, os, json, ctypes, time, traceback, signal

# ── SIGTERM → temiz çıkış ──────────────────────────────────────────
signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

def main():
    if len(sys.argv) < 2:
        sys.exit(2)

    cfg_path = sys.argv[1]
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
    except Exception as e:
        sys.exit(f"CONFIG_READ_ERROR: {e}")

    progress_file = cfg['progress_file']
    error_file    = cfg['error_file']

    def write_progress(v):
        try:
            with open(progress_file, 'w') as pf:
                pf.write(str(v))
        except Exception:
            pass

    def write_error(msg):
        try:
            with open(error_file, 'w', encoding='utf-8') as ef:
                ef.write(msg)
        except Exception:
            pass

    # ── C++ kütüphanesini yükle ───────────────────────────────────
    lib_path = cfg['lib_path']
    if not os.path.exists(lib_path):
        write_error(f"libkavram_core bulunamadı: {lib_path}")
        sys.exit(1)

    try:
        lib = ctypes.CDLL(lib_path)
    except Exception as e:
        write_error(f"C++ kütüphane yükleme hatası: {e}")
        sys.exit(1)

    # ── Fonksiyon imzaları ────────────────────────────────────────
    ProgressCB = ctypes.CFUNCTYPE(None, ctypes.c_int)

    lib.kavram_convert.restype  = ctypes.c_int
    lib.kavram_convert.argtypes = [
        ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
        ctypes.c_int, ctypes.c_float, ctypes.c_float,
        ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ProgressCB,
    ]
    lib.kavram_last_error.restype  = ctypes.c_char_p
    lib.kavram_last_error.argtypes = []
    lib.kavram_reset_cancel.restype  = None
    lib.kavram_reset_cancel.argtypes = []

    lib.kavram_reset_cancel()

    # ── İlerleme callback ──────────────────────────────────────────
    cb = ProgressCB(lambda v: write_progress(v))

    # ── Parametreler ──────────────────────────────────────────────
    in_path    = cfg['in_path'].encode()
    out_path   = cfg['out_path'].encode()
    cover_path = cfg['cover_path'].encode() if cfg.get('cover_path') else None

    try:
        ret = lib.kavram_convert(
            in_path, out_path, cover_path,
            int(cfg['mode']),
            ctypes.c_float(cfg['speed']),
            ctypes.c_float(cfg['pitch']),
            int(cfg['effect']),
            int(cfg['change_freq']),
            int(cfg['new_freq']),
            int(cfg['pdf_invert']),
            int(cfg['pdf_gray']),
            int(cfg['img_invert']),
            int(cfg['img_gray']),
            int(cfg['img_scale']),
            cb
        )
    except Exception as e:
        write_error(f"C++ çağrı istisnası: {traceback.format_exc()}")
        sys.exit(1)

    if ret == -99:
        # Kullanıcı iptali
        sys.exit(99)

    if ret < 0:
        try:
            err = lib.kavram_last_error().decode(errors='replace')
        except Exception:
            err = f"Bilinmeyen hata (kod {ret})"
        write_error(err or f"Hata kodu: {ret}")
        sys.exit(1)

    write_progress(100)
    sys.exit(0)


if __name__ == '__main__':
    main()
