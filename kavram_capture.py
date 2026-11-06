# -*- coding: utf-8 -*-
"""
kavram_capture.py  —  Windows ve macOS için kayıt altyapısı (ekran / kamera / mikrofon / medya motoru)
=====================================================================================================

Linux'ta kayıt C++ motorlarıyla yapılır (rec_engine: PipeWire/X11 + GStreamer, media_recorder, media_engine).
Bu motorlar Linux'a özeldir.  Windows ve macOS sürümleri (rec_win.py / rec_mac.py, media_win.py / media_mac.py,
sound_*.py) aynı işi bu modülle yapar:

  * Ekran kaydı     : FFmpeg  gdigrab (Windows)  /  avfoundation (macOS)
  * Mikrofon        : FFmpeg  dshow   (Windows)  /  avfoundation (macOS);  sound/media için PortAudio (sounddevice)
  * Kamera          : OpenCV (DirectShow / AVFoundation) — canlı önizleme + kayıt
  * Medya motoru    : MediaCore — media_engine.so'nun Python karşılığı (FFmpeg/FFprobe + PortAudio)

Dışa açılanlar
--------------
  list_av_devices(ffmpeg)           aygıt listesi (FFmpeg çıktısından)
  list_cameras() / list_audio_inputs()
  default_audio_input(ffmpeg)       varsayılan mikrofon (FFmpeg için ad/indeks)
  screen_record_command(...)        ekran (+ses) kaydı için tam FFmpeg komutu (segmentli)
  audio_record_command(...)         yalnızca ses
  ffmpeg_env()                      alt süreç ortamı (Windows yüksek DPI düzeltmesi)
  PreviewReader / publish_frame     canlı önizleme kareleri (Linux'taki ShmReader'ın yerine)
  CvCameraSource                    OpenCV kamera okuyucu (iş parçacıklı, Qt sinyalli)
  MediaCore                         media_engine karşılığı
  PyRecorderSession                 media_recorder karşılığı (kamera+mikrofon / yalnızca mikrofon)
"""
import ctypes
import math
import os
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time

import kavram_platform as kp

try:                                   # günlük (sessiz hata yutma yerine)
    import kavram_ui as _kui
    _log = _kui.log_exc
except Exception:                      # pragma: no cover
    def _log(_e=None):
        pass

# =============================================================================================
# Araç yolları ve alt süreç ortamı
# =============================================================================================
_TOOLS = {"ffmpeg": None, "ffprobe": None}


def find_tool(name):
    """ffmpeg / ffprobe yolunu bulur (paketli bin/ -> PATH)."""
    if _TOOLS.get(name):
        return _TOOLS[name]
    exe = kp.exe_file(name)
    cands = []
    base = getattr(sys, "_MEIPASS", None)
    if base:
        cands.append(os.path.join(base, "bin", exe))
    here = os.path.dirname(os.path.abspath(__file__))
    cands.append(os.path.join(here, "bin", exe))
    for c in cands:
        if os.path.isfile(c):
            _TOOLS[name] = c
            return c
    _TOOLS[name] = shutil.which(name) or name
    return _TOOLS[name]


def set_tool_paths(ffmpeg=None, ffprobe=None):
    for k, v in (("ffmpeg", ffmpeg), ("ffprobe", ffprobe)):
        if v:
            _TOOLS[k] = v.decode("utf-8") if isinstance(v, bytes) else v


def ffmpeg_env():
    """Alt süreç ortamı.  Windows'ta ffmpeg.exe'nin ekran ölçeklemesinden (DPI) etkilenmemesi için."""
    env = os.environ.copy()
    if kp.IS_WIN:
        env["__COMPAT_LAYER"] = "HIGHDPIAWARE"
    return env


def _run(cmd, timeout=30, capture=True, text=True):
    kw = dict(kp.hidden_console_kwargs())
    kw["env"] = ffmpeg_env()
    return subprocess.run(cmd, capture_output=capture, text=text, timeout=timeout,
                          encoding="utf-8" if text else None, errors="replace" if text else None, **kw)


# =============================================================================================
# Aygıt listeleri (FFmpeg çıktısı ayrıştırma)
# =============================================================================================
def parse_dshow_devices(text):
    """Windows:  ffmpeg -list_devices true -f dshow -i dummy  çıktısı -> {'video': [ad], 'audio': [ad]}."""
    video, audio = [], []
    section = None
    for line in text.splitlines():
        low = line.lower()
        if "directshow video devices" in low:
            section = "video"
            continue
        if "directshow audio devices" in low:
            section = "audio"
            continue
        if "alternative name" in low:
            continue
        m = re.search(r'"([^"]+)"\s*\((video|audio|none)(?:,\s*(video|audio))?\)', line)
        if m:
            name = m.group(1)
            kinds = {m.group(2), m.group(3)} - {None, "none"}
            if "video" in kinds and name not in video:
                video.append(name)
            if "audio" in kinds and name not in audio:
                audio.append(name)
            continue
        m = re.search(r'\]\s+"([^"]+)"\s*$', line)      # eski sürüm biçimi: bölüm başlığı + yalnızca ad
        if m and section:
            (video if section == "video" else audio).append(m.group(1))
    return {"video": video, "audio": audio}


def parse_avfoundation_devices(text):
    """macOS:  ffmpeg -f avfoundation -list_devices true -i ""  çıktısı -> {'video': [(idx, ad)], 'audio': [...]}."""
    video, audio = [], []
    section = None
    for line in text.splitlines():
        low = line.lower()
        if "avfoundation video devices" in low:
            section = "video"
            continue
        if "avfoundation audio devices" in low:
            section = "audio"
            continue
        m = re.search(r"\[(\d+)\]\s+(.+?)\s*$", line)
        if m and section:
            (video if section == "video" else audio).append((int(m.group(1)), m.group(2)))
    return {"video": video, "audio": audio}


_DEV_CACHE = {"t": 0.0, "v": None}


def list_av_devices(ffmpeg=None, max_age=15.0):
    """İşletim sistemine göre aygıt listesi (kısa süre önbelleğe alınır)."""
    now = time.time()
    if _DEV_CACHE["v"] is not None and now - _DEV_CACHE["t"] < max_age:
        return _DEV_CACHE["v"]
    ffmpeg = ffmpeg or find_tool("ffmpeg")
    result = {"video": [], "audio": []}
    try:
        if kp.IS_WIN:
            r = _run([ffmpeg, "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"], timeout=12)
            result = parse_dshow_devices((r.stderr or "") + "\n" + (r.stdout or ""))
        elif kp.IS_MAC:
            r = _run([ffmpeg, "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""], timeout=12)
            result = parse_avfoundation_devices((r.stderr or "") + "\n" + (r.stdout or ""))
    except Exception as e:
        _log(e)
    _DEV_CACHE.update(t=now, v=result)
    return result


def list_cameras(ffmpeg=None):
    """[(kimlik, ad), ...]  kimlik = OpenCV indeksi (metin).  Ekran yakalama aygıtları hariç."""
    cams = []
    dev = list_av_devices(ffmpeg)
    if kp.IS_WIN:
        cams = [(str(i), n) for i, n in enumerate(dev["video"])]
    elif kp.IS_MAC:
        real = [(i, n) for i, n in dev["video"] if not n.lower().startswith("capture screen")]
        cams = [(str(k), n) for k, (_i, n) in enumerate(real)]       # OpenCV yalnızca kameraları sayar
    if not cams:
        cams = [(str(i), f"Kamera {i}") for i in range(2)]
    return cams


def list_audio_inputs(ffmpeg=None):
    """[(ad, sistem_sesi_mi), ...]  — menüler için."""
    dev = list_av_devices(ffmpeg)
    if kp.IS_WIN:
        return [(n, False) for n in dev["audio"]]
    return [(n, False) for _i, n in dev["audio"]]


def default_audio_input(ffmpeg=None):
    """FFmpeg için varsayılan mikrofon (Windows: aygıt adı, macOS: indeks metni)."""
    dev = list_av_devices(ffmpeg)
    if kp.IS_WIN:
        names = dev["audio"]
        for n in names:                       # önce gerçek mikrofon
            if re.search(r"mic|mikrofon|microphone", n, re.I):
                return n
        return names[0] if names else ""
    if kp.IS_MAC:
        return str(dev["audio"][0][0]) if dev["audio"] else "0"
    return "default"


def _audio_spec(ffmpeg, choice):
    """Menüden seçilen/otomatik ses kaynağını FFmpeg'in anlayacağı belirtece çevirir."""
    if not choice:
        return default_audio_input(ffmpeg)
    if kp.IS_MAC:
        if str(choice).isdigit():
            return str(choice)
        for i, n in list_av_devices(ffmpeg)["audio"]:
            if n == choice:
                return str(i)
        return default_audio_input(ffmpeg)
    return choice


def _screen_index_mac(ffmpeg):
    for i, n in list_av_devices(ffmpeg)["video"]:
        if n.lower().startswith("capture screen"):
            return i
    return 1


# =============================================================================================
# FFmpeg komut kurucular (rec_win.py / rec_mac.py)
# =============================================================================================
def _even(v):
    return max(2, int(v) // 2 * 2)


def screen_record_command(ffmpeg, fps, out_w, out_h, segment_time, start_number, pattern,
                          audio=None, audio_rate=48000, region=None):
    """Segmentli (MKV) ekran kaydı komutu.  audio: None = yalnızca video, '' = otomatik, ad = o aygıt.
    region: (x, y, w, h) fiziksel piksel (çok monitörde birincil ekran) ya da None."""
    fps = int(fps)
    out_w, out_h = _even(out_w), _even(out_h)
    if audio is not None and not _audio_spec(ffmpeg, audio):
        audio = None                       # mikrofon bulunamadı: yalnızca video kaydet
    cmd = [ffmpeg, "-y", "-hide_banner"]
    if kp.IS_WIN:
        cmd += ["-f", "gdigrab", "-framerate", str(fps), "-draw_mouse", "1"]
        if region:
            cmd += ["-offset_x", str(region[0]), "-offset_y", str(region[1]),
                    "-video_size", f"{region[2]}x{region[3]}"]
        cmd += ["-i", "desktop"]
        if audio is not None:
            cmd += ["-f", "dshow", "-rtbufsize", "150M", "-thread_queue_size", "1024",
                    "-i", f"audio={_audio_spec(ffmpeg, audio)}"]
    else:  # macOS
        scr = _screen_index_mac(ffmpeg)
        spec = f"{scr}:{_audio_spec(ffmpeg, audio)}" if audio is not None else f"{scr}:none"
        cmd += ["-f", "avfoundation", "-framerate", str(min(fps, 60)), "-capture_cursor", "1",
                "-i", spec]
    cmd += ["-vf", f"scale={out_w}:{out_h}:flags=bicubic",
            "-map", "0:v:0"]
    if audio is not None:
        cmd += ["-map", "1:a:0" if kp.IS_WIN else "0:a:0"]
    cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "25", "-pix_fmt", "yuv420p",
            "-g", str(fps), "-sc_threshold", "0"]
    if audio is not None:
        cmd += ["-c:a", "aac", "-b:a", "128k", "-ar", str(audio_rate)]
    cmd += ["-fps_mode", "cfr",
            "-f", "segment", "-segment_time", str(segment_time),
            "-segment_start_number", str(start_number), "-reset_timestamps", "1",
            "-segment_format", "matroska", pattern]
    return cmd


def audio_record_command(ffmpeg, audio, audio_rate, segment_time, start_number, pattern):
    """Yalnızca ses (WAV, segmentli)."""
    cmd = [ffmpeg, "-y", "-hide_banner"]
    if kp.IS_WIN:
        cmd += ["-f", "dshow", "-rtbufsize", "150M", "-i", f"audio={_audio_spec(ffmpeg, audio)}"]
    else:
        cmd += ["-f", "avfoundation", "-i", f":{_audio_spec(ffmpeg, audio)}"]
    cmd += ["-c:a", "pcm_s16le", "-ar", str(audio_rate),
            "-f", "segment", "-segment_time", str(segment_time),
            "-segment_start_number", str(start_number), "-reset_timestamps", "1",
            "-segment_format", "wav", pattern]
    return cmd


# =============================================================================================
# Canlı önizleme veri yolu (Linux'taki paylaşımlı bellek yerine)
# =============================================================================================
_BUS = {}
_BUS_LOCK = threading.Lock()


def publish_frame(path, image):
    """Üretici (kamera iş parçacığı): son kareyi 'path' adı altında yayınlar (QImage)."""
    with _BUS_LOCK:
        e = _BUS.setdefault(path, [0, None])
        e[0] += 1
        e[1] = image


def clear_frames(path):
    with _BUS_LOCK:
        _BUS.pop(path, None)


class PreviewReader:
    """ShmReader ile aynı arayüz:  read_frame() -> QImage | None,  reset(),  close()."""

    def __init__(self, path, kind="video"):
        self.path = path
        self.kind = kind
        self.last_seq = -1

    def read_frame(self):
        with _BUS_LOCK:
            e = _BUS.get(self.path)
            if not e or e[1] is None or e[0] == self.last_seq:
                return None
            self.last_seq = e[0]
            return e[1]

    def reset(self):
        self.last_seq = -1

    def close(self):
        self.reset()


def _bgr_to_qimage(frame):
    from PyQt5.QtGui import QImage
    import cv2
    bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
    h, w = bgra.shape[:2]
    return QImage(bgra.data, w, h, int(bgra.strides[0]), QImage.Format_RGB32).copy()


# =============================================================================================
# OpenCV kamera
# =============================================================================================
def open_capture(device="", width=640, height=480, fps=30):
    """cv2.VideoCapture açar.  device: '' / 'auto' / indeks metni.  Başarısızsa None."""
    import cv2
    idxs = []
    if str(device).strip().isdigit():
        idxs = [int(device)]
    else:
        idxs = [0, 1, 2, 3]
    backends = [None]
    if kp.IS_WIN:
        backends = [getattr(cv2, "CAP_DSHOW", None), getattr(cv2, "CAP_MSMF", None), None]
    elif kp.IS_MAC:
        backends = [getattr(cv2, "CAP_AVFOUNDATION", None), None]
    for i in idxs:
        for be in backends:
            try:
                cap = cv2.VideoCapture(i, be) if be is not None else cv2.VideoCapture(i)
                if cap is not None and cap.isOpened():
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
                    cap.set(cv2.CAP_PROP_FPS, int(fps))
                    return cap
                if cap is not None:
                    cap.release()
            except Exception as e:
                _log(e)
    return None


def _make_status_object():
    from PyQt5.QtCore import QObject, pyqtSignal

    class _Status(QObject):
        status = pyqtSignal(str)
    return _Status()


class CvCameraSource:
    """Kamerayı iş parçacığında okur; kareleri 'bus_path' altında yayınlar (CameraOverlay okur)."""

    def __init__(self, bus_path, device="", size=(640, 480), fps=30):
        self.bus_path = bus_path
        self.device = device
        self.size = size
        self.fps = fps
        self._stop = threading.Event()
        self._thread = None
        self._notifier = _make_status_object()
        self.status = self._notifier.status            # pyqtSignal(str): hata / durum iletileri
        self.latest = None                             # son ham kare (numpy BGR)
        self._lock = threading.Lock()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="kavram-kamera", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        t = self._thread
        if t:
            t.join(timeout=3)
        self._thread = None
        clear_frames(self.bus_path)

    def last_frame(self):
        with self._lock:
            return None if self.latest is None else self.latest.copy()

    def _run(self):
        cap = open_capture(self.device, self.size[0], self.size[1], self.fps)
        if cap is None:
            msg = "Kamera açılamadı."
            if kp.IS_MAC:
                msg += "\nSistem Ayarları → Gizlilik ve Güvenlik → Kamera bölümünden izin verin."
            elif kp.IS_WIN:
                msg += "\nWindows Ayarları → Gizlilik → Kamera'dan masaüstü uygulamalarına izin verin."
            self.status.emit(msg)
            return
        period = 1.0 / max(5, self.fps)
        fails = 0
        try:
            while not self._stop.is_set():
                t0 = time.time()
                ok, frame = cap.read()
                if not ok or frame is None:
                    fails += 1
                    if fails > 60:
                        self.status.emit("Kameradan görüntü alınamıyor.")
                        break
                    time.sleep(0.03)
                    continue
                fails = 0
                with self._lock:
                    self.latest = frame
                try:
                    publish_frame(self.bus_path, _bgr_to_qimage(frame))
                except Exception as e:
                    _log(e)
                dt = time.time() - t0
                if dt < period:
                    time.sleep(period - dt)
        finally:
            try:
                cap.release()
            except Exception as e:
                _log(e)


# =============================================================================================
# MediaCore  —  media_engine.so'nun Python karşılığı (Windows / macOS)
# =============================================================================================
def _b2s(v):
    return v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else str(v)


def _lower_ext(p):
    return os.path.splitext(p)[1].lower()


def _safe_extract(tar, path):
    base = os.path.realpath(path)
    for m in tar.getmembers():
        if m.issym() or m.islnk() or m.isdev() or os.path.isabs(m.name):
            raise ValueError(f"izin verilmeyen arşiv öğesi: {m.name}")
        tgt = os.path.realpath(os.path.join(base, m.name))
        if os.path.commonpath([base, tgt]) != base:
            raise ValueError(f"arşiv dış dizine yazmaya çalışıyor: {m.name}")
    tar.extractall(base)


class MediaCore:
    """Medya motoru çağrılarının Python uygulaması (aynı adlar, aynı dönüş kodları)."""

    def __init__(self):
        self._rec = None            # ses kaydı durumu
        self._lock = threading.Lock()

    # ---- genel
    def engine_version(self):
        return 300

    def set_tool_paths(self, ffmpeg_path, ffprobe_path):
        set_tool_paths(_b2s(ffmpeg_path) if ffmpeg_path else None, _b2s(ffprobe_path) if ffprobe_path else None)

    # ---- ölçüm
    def media_probe_json(self, filepath, out, out_size):
        path = _b2s(filepath)
        if not path or out is None or out_size < 16:
            return -1
        try:
            r = _run([find_tool("ffprobe"), "-v", "error", "-print_format", "json",
                      "-show_format", "-show_streams", path], timeout=30, text=False)
        except Exception as e:
            _log(e)
            return -2
        data = r.stdout or b""
        if r.returncode != 0 or not data:
            return -2
        if len(data) >= out_size:
            return -3
        ctypes.memmove(out, data + b"\0", len(data) + 1)
        return len(data)

    def get_media_duration_ms(self, filepath):
        path = _b2s(filepath)
        if not path:
            return -1
        try:
            r = _run([find_tool("ffprobe"), "-v", "error", "-show_entries", "format=duration",
                      "-of", "default=noprint_wrappers=1:nokey=1", path], timeout=30)
            sec = float((r.stdout or "").strip().splitlines()[0])
        except Exception:
            return -1
        if r.returncode != 0 or not math.isfinite(sec) or sec <= 0:
            return -1
        return int(round(sec * 1000.0))

    def get_video_dimensions(self, filepath, out_w, out_h):
        path = _b2s(filepath)
        wref = getattr(out_w, "_obj", out_w)
        href = getattr(out_h, "_obj", out_h)
        try:
            wref.value = 0
            href.value = 0
            r = _run([find_tool("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                      "stream=width,height:stream_tags=rotate:stream_side_data=rotation",
                      "-of", "default=noprint_wrappers=1", path], timeout=30)
        except Exception:
            return -1
        if r.returncode != 0:
            return -1
        w = h = rot = 0
        for line in (r.stdout or "").splitlines():
            line = line.strip()
            if line.startswith("width="):
                w = int(float(line[6:] or 0))
            elif line.startswith("height="):
                h = int(float(line[7:] or 0))
            elif line.startswith("rotation="):
                rot = int(round(float(line[9:] or 0)))
            elif line.startswith("TAG:rotate="):
                rot = int(float(line[11:] or 0))
        if w <= 0 or h <= 0:
            return -1
        rot = ((rot % 360) + 360) % 360
        if rot in (90, 270):
            w, h = h, w
        wref.value, href.value = w, h
        return 0

    # ---- kesme
    def cut_media_segment(self, input_filepath, cut_point_ms, out1, out2, media_type):
        src, o1, o2, mt = _b2s(input_filepath), _b2s(out1), _b2s(out2), _b2s(media_type)
        if not src or not o1 or not o2:
            return -1
        if cut_point_ms <= 0:
            return -2
        if src == o1 or src == o2 or o1 == o2:
            return -3
        is_video = mt in ("video", "recorded_video")
        is_audio = mt in ("audio", "recorded_audio")
        if not is_video and not is_audio:
            return -4
        t = f"{cut_point_ms // 1000}.{cut_point_ms % 1000:03d}"

        def codec_args(out_path):
            e = _lower_ext(out_path)
            if is_video:
                a = ["-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k"]
                if e in (".mp4", ".mov", ".rec"):
                    a += ["-movflags", "+faststart"]
                if e == ".rec":
                    a += ["-f", "mp4"]
                return a
            a = ["-map", "0:a:0", "-vn"]
            if e == ".wav":
                a += ["-c:a", "pcm_s16le"]
            elif e == ".saund":
                a += ["-c:a", "pcm_s16le", "-f", "wav"]
            elif e == ".mp3":
                a += ["-c:a", "libmp3lame", "-q:a", "2"]
            elif e == ".flac":
                a += ["-c:a", "flac"]
            elif e == ".ogg":
                a += ["-c:a", "libvorbis", "-q:a", "6"]
            elif e == ".aac":
                a += ["-c:a", "aac", "-b:a", "192k", "-f", "adts"]
            else:
                a += ["-c:a", "aac", "-b:a", "192k"]
            return a

        ff = find_tool("ffmpeg")
        c1 = [ff, "-v", "error", "-y", "-i", src, "-t", t] + codec_args(o1) + [o1]
        r1 = _run(c1, timeout=3600, text=True)
        if r1.returncode != 0:
            print("MediaCore: kesme (1) başarısız:\n" + (r1.stderr or ""))
            _rm(o1)
            return -101
        c2 = [ff, "-v", "error", "-y", "-ss", t, "-i", src] + codec_args(o2) + [o2]
        r2 = _run(c2, timeout=3600, text=True)
        if r2.returncode != 0:
            print("MediaCore: kesme (2) başarısız:\n" + (r2.stderr or ""))
            _rm(o1)
            _rm(o2)
            return -102
        if not (os.path.isfile(o1) and os.path.isfile(o2)):
            _rm(o1)
            _rm(o2)
            return -103
        return 0

    def delete_media_file(self, filepath):
        p = _b2s(filepath)
        if not p:
            return -1
        try:
            os.remove(p)
            return 0
        except OSError:
            return -2

    # ---- arşiv
    def archive_segments_with_compression(self, output_tar_path, temp_dir, manifest_path, compression):
        out, src = _b2s(output_tar_path), _b2s(temp_dir)
        comp = _b2s(compression) if compression else "gz"
        if not out or not src:
            return -1
        if comp not in ("gz", "xz"):
            return -2
        try:
            with tarfile.open(out, "w:" + comp) as tar:
                for name in sorted(os.listdir(src)):
                    if name.startswith("."):
                        continue
                    tar.add(os.path.join(src, name), arcname=name)
            return 0
        except Exception as e:
            _log(e)
            return -3

    def archive_segments(self, output_tar_gz_path, temp_dir, manifest_path):
        return self.archive_segments_with_compression(output_tar_gz_path, temp_dir, manifest_path, b"gz")

    def extract_segments(self, input_tar_path, output_dir):
        src, dst = _b2s(input_tar_path), _b2s(output_dir)
        if not src or not dst:
            return -1
        try:
            os.makedirs(dst, exist_ok=True)
            with tarfile.open(src, "r:*") as tar:
                _safe_extract(tar, dst)
            return 0
        except Exception as e:
            _log(e)
            return -2

    # ---- ses kaydı (PortAudio / sounddevice)
    def init_audio_engine(self):
        try:
            import sounddevice  # noqa: F401
            return 0
        except Exception as e:
            print(f"MediaCore: PortAudio (sounddevice) yüklenemedi: {e}")
            return -1

    def terminate_audio_engine(self):
        return 0

    def start_audio_record(self, base_pattern, final_filepath):
        path = _b2s(final_filepath)
        with self._lock:
            if self._rec is not None:
                return -1
            if not path:
                return -2
            try:
                rec = WavRecorder(path, samplerate=48000, channels=1)
                rec.start()
            except Exception as e:
                print(f"MediaCore: ses kaydı başlatılamadı: {e}")
                _rm(path)
                return -4
            self._rec = rec
            return 0

    def stop_audio_record(self):
        with self._lock:
            rec, self._rec = self._rec, None
        if rec is None:
            return -1
        rec.stop()
        return 0

    def merge_audio_files(self, output_filepath):
        p = _b2s(output_filepath)
        if not p:
            return -1
        return 0 if os.path.isfile(p) else -2

    # ---- zaman çizelgesi
    def calculate_segment_position(self, start_time_ms, timeline_width, total_ms):
        if not (math.isfinite(start_time_ms) and math.isfinite(timeline_width) and math.isfinite(total_ms)):
            return 0.0
        if total_ms <= 0.0 or timeline_width <= 0.0:
            return 0.0
        ratio = min(1.0, max(0.0, max(0.0, start_time_ms) / total_ms))
        return ratio * timeline_width

    def update_timeline_smoothly(self, current, target, step):
        if not math.isfinite(current) and not math.isfinite(target):
            return 0.0
        if not math.isfinite(target):
            return current if math.isfinite(current) else 0.0
        if not math.isfinite(current):
            return target
        if current == target:
            return current
        if not math.isfinite(step) or step <= 0.0:
            return target
        if abs(target - current) < step:
            return target
        return current + step if current < target else current - step


def _rm(p):
    try:
        os.remove(p)
    except OSError:
        pass


class WavRecorder:
    """Mikrofondan tek WAV dosyasına (16-bit PCM) kayıt: halka tamponlu, callback asla bloklanmaz."""

    def __init__(self, path, samplerate=48000, channels=1, device=None):
        self.path = path
        self.samplerate = samplerate
        self.channels = channels
        self.device = device
        self._q = None
        self._stream = None
        self._writer = None
        self._sf = None
        self._run = threading.Event()
        self.started_at = None

    def start(self):
        import queue
        import sounddevice as sd
        import soundfile as sf
        self._q = queue.Queue(maxsize=4000)
        self._sf = sf.SoundFile(self.path, mode="w", samplerate=self.samplerate, channels=self.channels,
                                subtype="PCM_16")
        self._run.set()

        def cb(indata, frames, time_info, status):
            try:
                self._q.put_nowait(indata.copy())
            except Exception:
                pass            # dolu: bu örnekleri at (callback bloklanmaz)

        try:
            self._stream = sd.InputStream(samplerate=self.samplerate, channels=self.channels, dtype="float32",
                                          device=self.device, callback=cb)
            self._stream.start()
        except Exception:
            self._run.clear()
            self._sf.close()
            self._sf = None
            raise
        self.started_at = time.time()
        self._writer = threading.Thread(target=self._write_loop, name="kavram-wav", daemon=True)
        self._writer.start()

    def _write_loop(self):
        import queue
        while self._run.is_set() or not self._q.empty():
            try:
                block = self._q.get(timeout=0.05)
            except queue.Empty:
                continue
            try:
                self._sf.write(block)
            except Exception as e:
                _log(e)

    def stop(self):
        self._run.clear()
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        except Exception as e:
            _log(e)
        self._stream = None
        if self._writer is not None:
            self._writer.join(timeout=5)
        try:
            if self._sf is not None:
                self._sf.close()
        except Exception as e:
            _log(e)
        self._sf = None


# =============================================================================================
# PyRecorderSession  —  media_recorder'ın Python karşılığı (kamera + mikrofon / yalnızca mikrofon)
# =============================================================================================
def _parse_kv(args):
    kv = {}
    for a in args:
        if "=" in a and not a.startswith("--"):
            k, v = a.split("=", 1)
            kv[k] = v
    return kv


def _crop_resize(frame, w, h):
    import cv2
    fh, fw = frame.shape[:2]
    target = w / float(h)
    cur = fw / float(fh)
    if abs(cur - target) > 0.01:
        if cur > target:
            nw = int(fh * target)
            x0 = (fw - nw) // 2
            frame = frame[:, x0:x0 + nw]
        else:
            nh = int(fw / target)
            y0 = (fh - nh) // 2
            frame = frame[y0:y0 + nh, :]
    if frame.shape[1] != w or frame.shape[0] != h:
        frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA)
    return frame


def make_recorder_session_class():
    """RecorderSession (QObject) sınıfını üretir; Qt, çağrıldığında içe aktarılır."""
    from PyQt5.QtCore import QObject, pyqtSignal

    class RecorderSession(QObject):
        started = pyqtSignal()
        finished = pyqtSignal(int, str, str)       # çıkış kodu, çıkış dosyası, günlük

        def __init__(self, binary, args, out_path, parent=None):
            super().__init__(parent)
            self.out_path = out_path
            self._kv = _parse_kv(args)
            self._stop = threading.Event()
            self._thread = None
            self._init_ev = threading.Event()
            self._init_ok = False
            self._log = ""
            self._proc = None
            self._done = False

        # ---- QProcess uyumlu arayüz ----
        def start(self):
            self._thread = threading.Thread(target=self._main, name="kavram-kayit", daemon=True)
            self._thread.start()
            self._init_ev.wait(8.0)
            return self._init_ok

        def is_running(self):
            return self._thread is not None and self._thread.is_alive()

        def request_stop(self):
            self._stop.set()

        def kill(self):
            self._stop.set()
            p = self._proc
            if p is not None:
                try:
                    p.kill()
                except Exception as e:
                    _log(e)
            if self._thread:
                self._thread.join(timeout=3)

        # ---- iş parçacığı ----
        def _say(self, msg):
            self._log += msg + "\n"

        def _fail_init(self, msg):
            self._say(msg)
            self._init_ok = False
            self._init_ev.set()

        def _main(self):
            code = 0
            try:
                mode = self._kv.get("mode", "audio")
                if mode == "camera":
                    code = self._record_camera()
                else:
                    code = self._record_audio()
            except Exception as e:
                self._say(f"Kayıt hatası: {e}")
                code = 1
                if not self._init_ev.is_set():
                    self._init_ok = False
                    self._init_ev.set()
            finally:
                if not self._done:
                    self._done = True
                    self.finished.emit(code, self.out_path, self._log[-2000:])

        def _record_audio(self):
            rec = WavRecorder(self.out_path, samplerate=48000, channels=1)
            try:
                rec.start()
            except Exception as e:
                self._fail_init(f"Mikrofon açılamadı: {e}")
                return 1
            self._init_ok = True
            self._init_ev.set()
            self.started.emit()
            while not self._stop.is_set():
                time.sleep(0.05)
            rec.stop()
            return 0

        def _record_camera(self):
            import numpy as np  # noqa: F401
            kv = self._kv
            w = _even(int(kv.get("w", 1280)))
            h = _even(int(kv.get("h", 720)))
            fps = max(5, min(60, int(kv.get("fps", 30))))
            cw, ch = int(kv.get("cw", 1280)), int(kv.get("ch", 720))
            cam = kv.get("camera", "auto")
            want_audio = kv.get("audio", "none") != "none"
            pv = kv.get("pv")
            pv_w = int(kv.get("pv_w", 480))

            cap = open_capture("" if cam in ("auto", "") else cam, cw, ch, fps)
            if cap is None:
                msg = "Kamera açılamadı."
                if kp.IS_MAC:
                    msg += " Sistem Ayarları → Gizlilik ve Güvenlik → Kamera'dan izin verin."
                self._fail_init(msg)
                return 1

            latest = {"f": None}
            reader_stop = threading.Event()

            def reader():
                import cv2
                last_pv = 0.0
                while not reader_stop.is_set():
                    ok, fr = cap.read()
                    if not ok or fr is None:
                        time.sleep(0.02)
                        continue
                    latest["f"] = fr
                    now = time.time()
                    if pv and now - last_pv >= 0.066:
                        last_pv = now
                        try:
                            small = fr
                            if fr.shape[1] > pv_w:
                                sh = int(fr.shape[0] * pv_w / fr.shape[1])
                                small = cv2.resize(fr, (pv_w, max(2, sh)), interpolation=cv2.INTER_AREA)
                            publish_frame(pv, _bgr_to_qimage(small))
                        except Exception as e:
                            _log(e)

            rt = threading.Thread(target=reader, name="kavram-kamera-oku", daemon=True)
            rt.start()
            # ilk kareyi bekle
            t0 = time.time()
            while latest["f"] is None and time.time() - t0 < 5.0:
                time.sleep(0.02)
            if latest["f"] is None:
                reader_stop.set()
                cap.release()
                self._fail_init("Kameradan görüntü alınamadı.")
                return 1

            tmp_dir = os.path.dirname(self.out_path) or "."
            vid_tmp = os.path.join(tmp_dir, "_kamera_video.mp4")
            wav_tmp = os.path.join(tmp_dir, "_kamera_ses.wav")
            wrec = None
            audio_t0 = None
            if want_audio:
                try:
                    wrec = WavRecorder(wav_tmp, samplerate=48000, channels=1)
                    wrec.start()
                    audio_t0 = wrec.started_at
                except Exception as e:
                    self._say(f"Mikrofon açılamadı (yalnızca video kaydedilecek): {e}")
                    wrec = None

            cmd = [find_tool("ffmpeg"), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                   "-s", f"{w}x{h}", "-framerate", str(fps), "-i", "-",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", vid_tmp]
            kw = dict(kp.hidden_console_kwargs())
            kw["env"] = ffmpeg_env()
            try:
                self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                              stderr=subprocess.PIPE, **kw)
            except Exception as e:
                reader_stop.set()
                cap.release()
                if wrec:
                    wrec.stop()
                self._fail_init(f"FFmpeg başlatılamadı: {e}")
                return 1

            self._init_ok = True
            self._init_ev.set()
            self.started.emit()

            video_t0 = time.time()
            n = 0
            period = 1.0 / fps
            try:
                while not self._stop.is_set():
                    due = video_t0 + n * period
                    now = time.time()
                    if now < due:
                        time.sleep(min(0.01, due - now))
                        continue
                    fr = latest["f"]
                    if fr is None:
                        continue
                    data = _crop_resize(fr, w, h).tobytes()
                    # geride kalındıysa aynı kareyi tekrarla (sabit fps)
                    repeat = 1 + min(5, int((now - due) / period))
                    for _ in range(repeat):
                        self._proc.stdin.write(data)
                        n += 1
            except (BrokenPipeError, OSError) as e:
                self._say(f"FFmpeg yazma hatası: {e}")
            finally:
                reader_stop.set()
                rt.join(timeout=2)
                try:
                    cap.release()
                except Exception as e:
                    _log(e)
                if pv:
                    clear_frames(pv)
                if wrec:
                    wrec.stop()
                try:
                    self._proc.stdin.close()
                except Exception as e:
                    _log(e)
                try:
                    err = self._proc.stderr.read().decode("utf-8", "replace")
                    self._proc.wait(timeout=30)
                except Exception:
                    err = ""
                    try:
                        self._proc.kill()
                    except Exception as e:
                        _log(e)
                if err.strip():
                    self._say(err[-1500:])

            if not os.path.isfile(vid_tmp) or os.path.getsize(vid_tmp) == 0:
                self._say("Video dosyası oluşmadı.")
                return 1

            # birleştir (ses varsa eşitleyerek)
            mux = [find_tool("ffmpeg"), "-y", "-v", "error", "-i", vid_tmp]
            if wrec and os.path.isfile(wav_tmp) and os.path.getsize(wav_tmp) > 44:
                off = max(0.0, (audio_t0 or video_t0) - video_t0)
                if off > 0.001:
                    mux += ["-itsoffset", f"{off:.3f}"]
                mux += ["-i", wav_tmp, "-map", "0:v:0", "-map", "1:a:0",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest"]
            else:
                mux += ["-c", "copy"]
            mux += [self.out_path]
            r = _run(mux, timeout=600, text=True)
            _rm(vid_tmp)
            _rm(wav_tmp)
            if r.returncode != 0 or not os.path.isfile(self.out_path):
                self._say("Birleştirme başarısız:\n" + (r.stderr or ""))
                return 1
            return 0

    return RecorderSession
