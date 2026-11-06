# -*- coding: utf-8 -*-
"""
kavram_platform.py  —  Linux / Windows (ve macOS) farklarını tek yerde toplar
============================================================================

Programlar işletim sistemine özgü şeyleri (kütüphane uzantısı, süreç başlatma, süreç öldürme,
paylaşımlı bellek klasörü, varsayılan programla açma, veri klasörü ...) doğrudan yazmak yerine
bu modülden çağırır.  Böylece aynı kod hem Linux'ta hem Windows'ta çalışır.

    import kavram_platform as kp
    kp.IS_WIN, kp.IS_LINUX, kp.IS_MAC
    kp.lib_file("sound_engine")        -> "sound_engine.so" | "sound_engine.dll" | "sound_engine.dylib"
    kp.exe_file("media_recorder")      -> "media_recorder"  | "media_recorder.exe"
    kp.popen_kwargs()                  -> subprocess.Popen için "ayrı oturum" ayarları
    kp.add_lib_path(env, lib_dir)      -> LD_LIBRARY_PATH (Linux) / PATH (Windows)
    kp.terminate_tree(proc, force)     -> süreci ve çocuklarını sonlandırır
    kp.open_default(path)              -> xdg-open / os.startfile / open
    kp.data_dir()                      -> kullanıcı veri klasörü
    kp.user_id()                       -> os.getuid() yerine
    kp.shm_dir()                       -> /dev/shm yerine uygun klasör
    kp.activate_window(pid)            -> pencereyi öne getirir (Linux: xdotool/wmctrl, Windows: Win32)
    kp.NATIVE_RECORDING                -> ekran/kamera C++ kayıt motoru bu sistemde destekli mi
"""
import os
import signal
import subprocess
import sys
import tempfile

# ---- Hangi işletim sistemi?  KAVRAM_OS=linux|win|mac ortam değişkeni algılamayı geçersiz kılar (deneme/test için).
_ZORLA = (os.environ.get("KAVRAM_OS") or "").strip().lower()
if _ZORLA in ("win", "windows"):
    OS_ADI = "win"
elif _ZORLA in ("mac", "macos", "darwin"):
    OS_ADI = "mac"
elif _ZORLA == "linux":
    OS_ADI = "linux"
elif sys.platform.startswith("win"):
    OS_ADI = "win"
elif sys.platform == "darwin":
    OS_ADI = "mac"
else:
    OS_ADI = "linux"

IS_WIN = OS_ADI == "win"
IS_MAC = OS_ADI == "mac"
IS_LINUX = OS_ADI == "linux"
IS_POSIX = not IS_WIN

# Her program klasöründe işletim sistemine özel dosyalar bulunur:
#     rec.py (Linux, varsayılan)    rec_win.py (Windows)    rec_mac.py (macOS)
# Sonekleri değiştirmek için yalnızca bu tabloyu düzenleyin (kavram.spec ve yapilandir.py de buradan okur).
SONEKLER = {"linux": "", "win": "_win", "mac": "_mac"}
SONEK = SONEKLER[OS_ADI]


def program_dosyasi(klasor, ad):
    """<klasor>/<ad><sonek>.py varsa onu, yoksa varsayılan <klasor>/<ad>.py dosyasını döndürür (yoksa None)."""
    for aday in (ad + SONEK + ".py", ad + ".py"):
        yol = os.path.join(klasor, aday)
        if os.path.isfile(yol):
            return yol
    return None


def varyant_modulleri(klasorler):
    """Bu işletim sistemine özel dosyaları bulur:  {modül_adı: dosya_yolu}  (örn. sphere_kare -> sphere_kare_win.py)."""
    sonuc = {}
    if not SONEK:
        return sonuc
    for k in klasorler:
        try:
            for f in os.listdir(k):
                if f.endswith(SONEK + ".py") and len(f) > len(SONEK) + 3:
                    sonuc[f[: -(len(SONEK) + 3)]] = os.path.join(k, f)
        except OSError:
            pass
    return sonuc

# C++ ekran/kamera kayıt motorları (GStreamer + PipeWire/X11) şimdilik yalnızca Linux içindir.
NATIVE_RECORDING = IS_LINUX


def lib_ext():
    return ".dll" if IS_WIN else (".dylib" if IS_MAC else ".so")


def lib_file(base):
    """'sound_engine' / 'sound_engine.so' -> bu sisteme uygun dosya adı."""
    for e in (".so", ".dll", ".dylib"):
        if base.endswith(e):
            base = base[: -len(e)]
            break
    return base + lib_ext()


def exe_file(base):
    return base + ".exe" if IS_WIN and not base.lower().endswith(".exe") else base


def user_id():
    try:
        return os.getuid()
    except AttributeError:       # Windows
        return 0


def shm_dir():
    if IS_LINUX and os.path.isdir("/dev/shm"):
        return "/dev/shm"
    return tempfile.gettempdir()


def data_dir():
    """Yazılabilir kullanıcı verileri (paketli sürümde export/veri/ayarlar buraya gider)."""
    if IS_WIN:
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "kavram")
    if IS_MAC:
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "kavram")
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "kavram")


def popen_kwargs(new_session=True):
    """subprocess.Popen için 'ana süreçten bağımsız başlat' ayarı (start_new_session karşılığı)."""
    if not new_session:
        return {}
    if IS_WIN:
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
        return {"creationflags": flags}
    return {"start_new_session": True}


def hidden_console_kwargs():
    """Windows'ta yardımcı komutlar (ffmpeg vb.) için siyah konsol penceresi açılmasın."""
    if IS_WIN and hasattr(subprocess, "STARTUPINFO"):        # (gerçek Windows'ta her zaman vardır)
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return {"startupinfo": si, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {}


def add_lib_path(env, lib_dir):
    """Alt sürecin yan kütüphanelerini bulabilmesi için kütüphane yolunu ekler."""
    if not lib_dir:
        return env
    key = "PATH" if IS_WIN else ("DYLD_LIBRARY_PATH" if IS_MAC else "LD_LIBRARY_PATH")
    env[key] = lib_dir + os.pathsep + env.get(key, "")
    return env


def terminate_tree(proc, force=False):
    """Süreci (varsa çocuklarıyla) sonlandırır.  Linux: process group; Windows: taskkill /T."""
    try:
        if IS_WIN:
            cmd = ["taskkill", "/PID", str(proc.pid), "/T"] + (["/F"] if force else [])
            subprocess.run(cmd, capture_output=True, timeout=5, **hidden_console_kwargs())
            return
        sig = signal.SIGKILL if force else signal.SIGTERM
        try:
            os.killpg(os.getpgid(proc.pid), sig)
        except (ProcessLookupError, PermissionError, OSError):
            proc.send_signal(sig)
    except Exception:
        try:
            proc.kill() if force else proc.terminate()
        except Exception:
            pass


def send_interrupt(proc):
    """Nazik durdurma (Linux: SIGINT, Windows: CTRL_BREAK)."""
    try:
        if IS_WIN:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.send_signal(signal.SIGINT)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass


def open_default(path):
    """Dosyayı / klasörü sistemin varsayılan programıyla açar."""
    try:
        if IS_WIN:
            os.startfile(path)                                   # noqa: S606  (yalnızca Windows)
            return True
        cmd = ["open", path] if IS_MAC else ["xdg-open", path]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True
    except Exception:
        return False


def default_qt_platform():
    """Qt platform eklentisi: yalnızca Linux'ta 'xcb' zorlanır; Windows/macOS kendi varsayılanını kullanır."""
    return "xcb" if IS_LINUX else None


def activate_window(pid, exe_name=""):
    """PID'ye ait pencereyi öne getirir.  Başarılıysa True."""
    if IS_WIN:
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            found = []

            @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            def _enum(hwnd, _lp):
                if user32.IsWindowVisible(hwnd):
                    p = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
                    if p.value == pid:
                        found.append(hwnd)
                return True

            user32.EnumWindows(_enum, 0)
            if found:
                user32.ShowWindow(found[0], 9)        # SW_RESTORE
                user32.SetForegroundWindow(found[0])
                return True
        except Exception:
            pass
        return False
    if IS_MAC:
        try:
            script = ('tell application "System Events" to set frontmost of '
                      f'(first process whose unix id is {int(pid)}) to true')
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
            return True
        except Exception:
            return False
    # Linux: xdotool / wmctrl
    try:
        r = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(pid)],
                           capture_output=True, text=True, timeout=1)
        for wid in r.stdout.split():
            subprocess.run(["xdotool", "windowactivate", wid.strip()], timeout=1)
            return True
    except Exception:
        pass
    try:
        r = subprocess.run(["wmctrl", "-lp"], capture_output=True, text=True, timeout=1)
        for line in r.stdout.splitlines():
            parts = line.split()
            if len(parts) > 2 and parts[2] == str(pid):
                subprocess.run(["wmctrl", "-i", "-a", parts[0]], timeout=1)
                return True
    except Exception:
        pass
    return False


def platform_name():
    return "Windows" if IS_WIN else ("macOS" if IS_MAC else "Linux")


def tum_sonekler():
    return [s for s in SONEKLER.values() if s]
