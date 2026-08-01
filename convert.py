# Kavram 2.2.2
# Copyright (C) 2026-07-22 Kavram or Contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see /Kavram/License/GPLv3.txt
#
# ---------------------------------------------
#
# Kavram 2.2.2
# Copyright (C) 2026-07-22 Kavram veya Contributors
#
# Bu program özgür bir yazılımdır: Özgür Yazılım Vakfı tarafından yayınlanan
# GNU Genel Kamu Lisansı'nın 3. sürümü veya (tercihinize bağlı olarak)
# daha sonraki herhangi bir sürümü kapsamında yeniden dağıtabilir ve/veya
# değiştirebilirsiniz.
#
# Bu program, faydalı olacağı umuduyla dağıtılmaktadır, ancak HERHANGİ BİR
# GARANTİ OLMADAN; hatta SATILABİLİRLİK veya BELİRLİ BİR AMACA UYGUNLUK
# zımni garantisi olmaksızın.
#
# Bu programla birlikte GNU Genel Kamu Lisansı'nın bir kopyasını almış olmanız gerekir:
# /Kavram/License/GPLv3.txt


import sys, os, ctypes, time, subprocess, json, shutil, uuid

# Linux Mint / GStreamer VA-API uyuşmazlıklarını önlemek için ortam değişkenleri (Kritik Düzeltme)
if sys.platform.startswith('linux'):
    os.environ["GST_VAAPI_ALL_DRIVERS"] = "0"
    os.environ["GST_GL_API"] = "opengl"

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QFileDialog, QMessageBox, QProgressBar, QComboBox,
    QLineEdit, QFormLayout, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, QObject, pyqtSignal, QSettings, QTimer, QUrl
from PyQt5.QtGui import QIcon, QPixmap, QImage, QPainter, QColor

# Video oynatma için MediaPlayer
try:
    from PyQt5.QtMultimediaWidgets import QVideoWidget
    from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
    HAS_MEDIA = True
except ImportError:
    HAS_MEDIA = False
    QVideoWidget = None
    QMediaPlayer = None

# PyMuPDF — PDF dönüşümü için
try:
    import fitz
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False
    print("UYARI: PyMuPDF (fitz) kurulu değil. pip install PyMuPDF")

# Pillow — PDF içinde resim işlemek ve video nota ikonu çizmek için
try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Uygulama içi FFmpeg yolları (resource_path) ──
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

FFMPEG_PATH  = resource_path("bin/ffmpeg")
FFPROBE_PATH = resource_path("bin/ffprobe")
FFPLAY_PATH  = resource_path("bin/ffplay")

# Varlık ve çalıştırılabilirlik kontrolü (opsiyonel, uyarı ver)
for p in [FFMPEG_PATH, FFPROBE_PATH, FFPLAY_PATH]:
    if not os.path.exists(p):
        print(f"Uyarı: {p} bulunamadı. Video/medya işleme çalışmayabilir.")
    elif not os.access(p, os.X_OK):
        print(f"Uyarı: {p} çalıştırılabilir değil. Video/medya işleme çalışmayabilir.")

# ── C++ core ─────────────────────────────────────────────────────────────────
_core_path = None

def _load_core():
    global _core_path
    d = os.path.dirname(os.path.abspath(__file__))
    
    # Kütüphane isimleri (platforma göre)
    if sys.platform == 'win32':
        names = ['libconverter_engine.dll', 'kavram_core.dll']
    elif sys.platform == 'darwin':
        names = ['libconverter_engine.dylib', 'libkavram_core.dylib', 'kavram_core.so']
    else:
        names = ['libconverter_engine.so', 'libkavram_core.so', 'kavram_core.so']

    # 1. ÖNCELİKLE: lib/ klasöründe ara (Paketlenmiş sürüm)
    for n in names:
        p = os.path.join(d, "lib", n)
        if os.path.exists(p):
            try:
                lib = ctypes.CDLL(p)
                _setup(lib)
                _core_path = p
                print(f"[Kavram] C++ core (lib/): {p}")
                return lib
            except Exception as e:
                print(f"[Kavram] lib/ klasöründen yükleme başarısız: {e}")

    # 2. FALLBACK: Kök dizinde ara (Geliştirme ortamı)
    for n in names:
        p = os.path.join(d, n)
        if os.path.exists(p):
            try:
                lib = ctypes.CDLL(p)
                _setup(lib)
                _core_path = p
                print(f"[Kavram] C++ core (fallback): {p}")
                return lib
            except Exception as e:
                print(f"[Kavram] Kök dizinden yükleme başarısız: {e}")

    # Hiçbiri bulunamazsa hata fırlat
    raise RuntimeError(
        "libconverter_engine.so bulunamadı!\n"
        "Derleme Komutu (Linux Mint / Debian):\n"
        "  g++ -O2 -shared -fPIC -o libconverter_engine.so converter_engine.cpp -lm \\\n"
        "    $(pkg-config --cflags --libs libavformat libavcodec libavutil libswresample libswscale)\n\n"
        "NOT: Eksik kütüphaneler varsa şunu çalıştırın:\n"
        "  sudo apt install build-essential pkg-config libavformat-dev libavcodec-dev libavutil-dev libswresample-dev libswscale-dev"
    )

ProgressCB = ctypes.CFUNCTYPE(None, ctypes.c_int)

def _setup(lib):
    lib.kavram_convert.restype  = ctypes.c_int
    lib.kavram_convert.argtypes = [
        ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
        ctypes.c_int, ctypes.c_float, ctypes.c_float,
        ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, ProgressCB,
    ]
    lib.kavram_last_error.restype  = ctypes.c_char_p
    lib.kavram_last_error.argtypes = []
    lib.kavram_version.restype     = ctypes.c_char_p
    lib.kavram_version.argtypes    = []
    lib.kavram_cancel.restype      = None
    lib.kavram_cancel.argtypes     = []
    lib.kavram_reset_cancel.restype  = None
    lib.kavram_reset_cancel.argtypes = []
    lib.kavram_file_copy.restype   = ctypes.c_int
    lib.kavram_file_copy.argtypes  = [ctypes.c_char_p, ctypes.c_char_p]

try:
    _cpp = _load_core()
    if _cpp:
        print(f"[Kavram] sürüm: {_cpp.kavram_version().decode()}")
except RuntimeError as _e:
    print(f"FATAL: {_e}")
    _cpp = None

# ── Sabitler ve Klasörler ─────────────────────────────────────────────────────────────────
AUDIO_EXT  = ['.mp3', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.wav', '.opus']
VIDEO_EXT  = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']
PDF_EXT    = ['.pdf']
IMAGE_EXT  = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.gif']
ALL_EXT    = AUDIO_EXT + VIDEO_EXT + PDF_EXT + IMAGE_EXT
EXPORT_DIR = os.path.join(os.path.expanduser('~'), 'Kavram', 'Export')
CONVERT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'convert')

# Geçici klasörü hazırla
os.makedirs(CONVERT_DIR, exist_ok=True)

MODE_AUDIO   = 0
MODE_VIDEO   = 1
MODE_AUD2VID = 2
MODE_IMAGE   = 3
MODE_PDF     = 4
MODE_VID_MIX = 5

# ── Ön kontrol (ses bozuklukları) ───────────────────────────────────────────
_AAC_VALID_SR = {7350,8000,11025,12000,16000,22050,24000,
                 32000,44100,48000,64000,88200,96000}

def _preflight_check(path):
    try:
        out = subprocess.check_output(
            [FFPROBE_PATH, '-v', 'quiet',
             '-analyzeduration', '500000',
             '-probesize',       '500000',
             '-print_format', 'json',
             '-show_streams', path],
            stderr=subprocess.DEVNULL, timeout=5)
        data   = json.loads(out)
        issues = []
        for s in data.get('streams', []):
            if s.get('codec_type') != 'audio': continue
            ch  = int(s.get('channels', 1) or 0)
            sr  = int(s.get('sample_rate', 44100) or 0)
            lay = s.get('channel_layout', '')
            cod = s.get('codec_name', '')
            if ch == 0:
                issues.append("Ses kanalı = 0 (bozuk header)")
            if not lay:
                issues.append("Kanal düzeni tanımsız")
            if cod == 'aac' and sr not in _AAC_VALID_SR:
                issues.append(f"AAC için geçersiz örnekleme hızı: {sr} Hz")
        if issues:
            return True, " | ".join(issues)
        return False, ""
    except Exception:
        return False, ""

# ── FFmpeg fallback worker (ses için) ───────────────────────────────────────
class FfmpegFallbackWorker(QObject):
    finished = pyqtSignal(str, float)
    error    = pyqtSignal(str)
    progress = pyqtSignal(int)
    _CODEC = {
        '.wav':  ('pcm_s16le', []),
        '.mp3':  ('libmp3lame', ['-q:a', '2']),
        '.opus': ('libopus',    ['-b:a', '128k']),
        '.m4a':  ('aac',        ['-b:a', '192k']),
        '.mp4':  ('aac',        ['-b:a', '192k', '-vn']),
        '.mkv':  ('aac',        ['-b:a', '192k', '-vn']),
        '.flac': ('flac',       []),
        '.ogg':  ('libvorbis',  ['-q:a', '5']),
    }
    def __init__(self, in_path, out_path, out_ext, speed=1.0, is_preview=False):
        super().__init__()
        self.in_path    = in_path
        self.out_path   = out_path
        self.out_ext    = out_ext.lower()
        self.speed      = speed
        self.is_preview = is_preview
        self._stop      = False
        self._proc      = None
        
    def run(self):
        t0 = time.time()
        try:
            acodec, extra = self._CODEC.get(self.out_ext, ('aac', ['-b:a','192k']))
            atempo = []
            sp = float(self.speed)
            if abs(sp - 1.0) > 0.01:
                while sp > 2.0:   atempo.append('atempo=2.0'); sp /= 2.0
                while sp < 0.5:   atempo.append('atempo=0.5'); sp *= 2.0
                atempo.append(f'atempo={sp:.4f}')
            af = ['aresample=44100:resampler=swr', 'pan=stereo|c0=c0|c1=c0']
            if atempo:
                af += atempo
                
            cmd = [FFMPEG_PATH, '-y']
            if self.is_preview:
                cmd.extend(['-t', '5'])
                
            cmd.extend([
                   '-analyzeduration', '10000000',
                   '-probesize',       '10000000',
                   '-i', self.in_path,
                   '-vn',
                   '-af', ','.join(af),
                   '-acodec', acodec,
                   ])
            cmd.extend(extra)
            cmd.append(self.out_path)
            
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True)
            last_pct = 10
            for line in self._proc.stdout:
                if 'time=' in line:
                    last_pct = min(last_pct + 3, 90)
                    self.progress.emit(last_pct)
                if self._stop:
                    self._proc.kill(); break
                time.sleep(0.05)
            self._proc.wait()
            if self._stop: return
            if self._proc.returncode != 0:
                self.error.emit(f"FFmpeg dönüştürme başarısız (kod {self._proc.returncode})")
                return
            self.progress.emit(100)
            self.finished.emit(self.out_path, time.time() - t0)
        except FileNotFoundError:
            self.error.emit(f"ffmpeg bulunamadı: {FFMPEG_PATH}\nLütfen uygulama dizininde bin/ffmpeg olduğundan emin olun.")
        except Exception as e:
            self.error.emit(str(e))
    def stop(self):
        self._stop = True
        if self._proc:
            try: self._proc.kill()
            except: pass

# ── PDF dönüşümü (PyMuPDF) ──────────────────────────────────────────────────
def pdf_convert_with_fitz(in_path, out_path, do_invert, do_grayscale, to_txt, progress_cb):
    if not HAS_FITZ:
        return False, "PyMuPDF (fitz) kurulu değil. pip install PyMuPDF"
    try:
        doc = fitz.open(in_path)
        total = len(doc)
        if to_txt:
            with open(out_path, 'w', encoding='utf-8') as f:
                for i, page in enumerate(doc):
                    text = page.get_text()
                    f.write(text)
                    if progress_cb:
                        progress_cb(int((i+1)/total * 100))
            return True, ""
        else:
            new_doc = fitz.open()
            for i, page in enumerate(doc):
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
                img_data = pix.tobytes("png")
                if do_grayscale or do_invert:
                    if not HAS_PIL:
                        return False, "Pillow kurulu değil. pip install Pillow"
                    import io
                    img = Image.open(io.BytesIO(img_data))
                    if do_grayscale:
                        img = img.convert("L").convert("RGB")
                    if do_invert:
                        img = Image.eval(img, lambda x: 255 - x)
                    buf = io.BytesIO()
                    img.save(buf, format="PNG", quality=95)
                    img_data = buf.getvalue()
                rect = page.rect
                new_page = new_doc.new_page(width=rect.width, height=rect.height)
                new_page.insert_image(rect, stream=img_data)
                if progress_cb:
                    progress_cb(int((i+1)/total * 95))
            new_doc.save(out_path)
            new_doc.close()
            if progress_cb:
                progress_cb(100)
            return True, ""
    except Exception as e:
        return False, str(e)

# ── YARDIMCI: Ses + Resim -> Video (FFmpeg) ─────────────────────────────────
def create_video_from_audio_image(audio_wav_path, image_path, output_path, is_preview, progress_cb):
    actual_image = image_path
    cleanup_needed = False
    try:
        if HAS_PIL:
            img = Image.open(image_path).convert("RGB")
            max_w, max_h = 1920, 1080
            if img.width > max_w or img.height > max_h:
                ratio = min(max_w / img.width, max_h / img.height)
                new_w = int(img.width * ratio)
                new_h = int(img.height * ratio)
                img = img.resize((new_w, new_h), Image.LANCZOS)
            tmp_img = os.path.join(CONVERT_DIR, f"cover_{uuid.uuid4().hex}.png")
            img.save(tmp_img, format="PNG")
            actual_image = tmp_img
            cleanup_needed = True
    except Exception as e:
        print(f"[Kavram] Resim işleme hatası: {e}, orijinal kullanılıyor")

    filter_complex = "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p"
    cmd = [
        FFMPEG_PATH, "-y", "-loop", "1", "-framerate", "1",
        "-i", actual_image, "-i", audio_wav_path,
        "-vf", filter_complex,
        "-c:v", "libx264", "-preset", "ultrafast", "-tune", "stillimage",
        "-r", "1", "-crf", "28", "-c:a", "aac", "-b:a", "128k", "-shortest"
    ]
    if is_preview: cmd.extend(["-t", "5"])
    cmd.append(output_path)

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        last = 10
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None: break
            if 'frame=' in line and progress_cb:
                last = min(last + 5, 95)
                progress_cb(last)
        stderr = proc.stderr.read()
        proc.wait()
        if proc.returncode != 0: return False, f"FFmpeg video oluşturma hatası: {stderr}"
        return True, ""
    except Exception as e:
        return False, str(e)
    finally:
        if cleanup_needed and os.path.exists(actual_image):
            try: os.unlink(actual_image)
            except: pass

# ── YARDIMCI: Video + Harici Ses Mix (Nota İkonu Destekli) ──────────────────
def _create_music_note_image(w, h):
    """Matematiksel olarak Pillow ile tekli nota (♪) ikonu çizer, sistem fontlarından bağımsızdır."""
    img_path = os.path.join(CONVERT_DIR, f"music_note_{uuid.uuid4().hex}.png")
    try:
        if not HAS_PIL: return None
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0)) # Şeffaf
        d = ImageDraw.Draw(img)
        cx, cy = w // 2, h // 2
        
        # Boyut yarı yarıya küçültüldü (eski değer 6 yerine 12 yapıldı)
        s = min(w, h) // 12  
        
        # Premium koyu arka plan deseni
        d.rectangle([0, 0, w, h], fill=(18, 18, 24, 255))
        
        # Tekli Müzik Notası Çizimi (Sekizlik Nota - ♪)
        # 1. Kafa (Eliptik nota başı)
        d.ellipse([cx - 1.5*s, cy + 0.8*s, cx + 0.5*s, cy + 2.4*s], fill=(240, 240, 240, 255)) 
        
        # 2. Sap (Yukarı doğru zarif çizgi)
        stem_x = cx + 0.3*s
        d.line([stem_x, cy + 1.5*s, stem_x, cy - 3*s], fill=(240, 240, 240, 255), width=max(3, s//4)) 
        
        # 3. Kuyruk (Bayrak - sağa aşağı doğru kıvrım)
        flag_points = [
            (stem_x, cy - 3*s),         # Sapın en üstü
            (cx + 2.0*s, cy - 1.2*s),   # Dış sağ kavis
            (cx + 2.2*s, cy - 0.2*s),   # Alt sivri uç
            (cx + 1.0*s, cy - 1.2*s),   # İç kavis dönüşü
            (stem_x, cy - 1.8*s)        # Sapa geri birleşme noktası
        ]
        d.polygon(flag_points, fill=(240, 240, 240, 255))
        
        img.save(img_path, format="PNG")
        return img_path
    except Exception as e:
        print(f"[Kavram] Nota ikonu çizilemedi: {e}")
        return None

def mix_video_and_audio(vid_path, aud_path, out_path, do_inv, do_gray, is_preview, progress_cb):
    """Videoya harici sesi ekler. Çok daha kararlı, çökmeyen ve asenkron uyumlu tpad/apad filtre yapısı."""
    try:
        # 1. Video çözünürlüğü ve süresini al (Kapsamlı FFprobe Fallback)
        probe_cmd = [FFPROBE_PATH, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 
                     'stream=width,height,duration', '-of', 'json', vid_path]
        out = subprocess.check_output(probe_cmd, stderr=subprocess.DEVNULL)
        info = json.loads(out).get('streams', [{}])[0]
        w = int(info.get('width', 1280))
        h = int(info.get('height', 720))
        w = (w // 2) * 2
        h = (h // 2) * 2
        
        try:
            v_dur = float(info.get('duration'))
        except (TypeError, ValueError):
            try:
                probe_format = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', vid_path]
                out_f = subprocess.check_output(probe_format, stderr=subprocess.DEVNULL)
                v_dur = float(json.loads(out_f).get('format', {}).get('duration', 10.0))
            except:
                v_dur = 10.0

        # Ses dosyasının süresini al
        probe_aud = [FFPROBE_PATH, '-v', 'error', '-select_streams', 'a:0', '-show_entries', 
                     'stream=duration', '-of', 'json', aud_path]
        out_a = subprocess.check_output(probe_aud, stderr=subprocess.DEVNULL)
        aud_info = json.loads(out_a).get('streams', [{}])
        try:
            a_dur = float(aud_info[0].get('duration')) if aud_info else 10.0
        except (TypeError, ValueError, IndexError):
            try:
                probe_aud_f = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', aud_path]
                out_af = subprocess.check_output(probe_aud_f, stderr=subprocess.DEVNULL)
                a_dur = float(json.loads(out_af).get('format', {}).get('duration', 10.0))
            except:
                a_dur = 10.0

        # Temel video efekt filtreleri
        filters = []
        if do_inv: filters.append("negate")
        if do_gray: filters.append("hue=s=0")
        fx_str = ",".join(filters) + "," if filters else ""

        cmd = [FFMPEG_PATH, '-y', '-i', vid_path, '-i', aud_path]
        
        if a_dur > v_dur:
            # Ses videodan uzunsa: Videoyu duraklat (siyah ekran yap) ve üzerine nota ikonu overlay et
            note_img_path = _create_music_note_image(w, h)
            if note_img_path:
                cmd.extend(['-loop', '1', '-i', note_img_path])
                pad_dur = a_dur - v_dur
                filter_complex = (
                    f"[0:v]{fx_str}scale={w}:{h},tpad=stop_mode=0:stop_duration={pad_dur}[padded];"
                    f"[2:v]scale={w}:{h}[note];"
                    f"[padded][note]overlay=0:0:enable='gt(t,{v_dur})'[vout]"
                )
                cmd.extend(['-filter_complex', filter_complex, '-map', '[vout]', '-map', '1:a'])
            else:
                # Nota resmi çizilemezse yedek olarak siyah ekran uzatması
                pad_dur = a_dur - v_dur
                filter_complex = f"[0:v]{fx_str}scale={w}:{h},tpad=stop_mode=0:stop_duration={pad_dur}[vout]"
                cmd.extend(['-filter_complex', filter_complex, '-map', '[vout]', '-map', '1:a'])
        else:
            # Video sesten uzunsa: Videoyu normal oynat, biten sesi asenkron sessizlikle besle (apad)
            note_img_path = None
            filter_complex = f"[0:v]{fx_str}scale={w}:{h}[vout];[1:a]apad[aout]"
            cmd.extend(['-filter_complex', filter_complex, '-map', '[vout]', '-map', '[aout]'])

        cmd.extend([
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '24',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '192k',
            '-shortest'
        ])
        
        if is_preview:
            cmd.extend(['-t', '5'])
        
        cmd.append(out_path)
        
        # FFmpeg hata akışını tamamen kaydetmek için tampon bellek dizi loglama yapısı
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        err_lines = []
        last_pct = 10
        
        while True:
            line = proc.stderr.readline()
            if not line:
                if proc.poll() is not None:
                    break
                else:
                    time.sleep(0.01)
                    continue
            err_lines.append(line)
            if 'time=' in line and progress_cb:
                last_pct = min(last_pct + 2, 95)
                progress_cb(last_pct)
                
        proc.wait()
        if note_img_path and os.path.exists(note_img_path):
            try: os.unlink(note_img_path)
            except: pass
            
        if proc.returncode != 0:
            err_log = "".join(err_lines[-20:]) if err_lines else "Bilinmeyen FFmpeg birleştirme hatası"
            print(f"[Kavram Mix Hatası]: {err_log}")
            return False, f"FFmpeg video-ses mix işlemi başarısız oldu. Hata Ayrıştırma Çıktısı:\n{err_log}"
        return True, ""
    except Exception as e:
        return False, str(e)

# ── ConversionWorker ────────────────────────────────────────────────────────
class ConversionWorker(QObject):
    finished = pyqtSignal(str, float)
    error    = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, in_path, out_path, cover_path, mode, s, is_preview=False):
        super().__init__()
        self.in_path    = in_path
        self.out_path   = out_path
        self.cover_path = cover_path
        self.mode       = mode
        self.s          = s
        self.is_preview = is_preview
        self._stop      = False

    def run(self):
        if not _cpp:
            self.error.emit("C++ core yüklü değil."); return
        t0 = time.time()

        if self.mode == MODE_AUD2VID:
            self._run_aud2vid_with_ffmpeg(t0)
            return
            
        if self.mode == MODE_VID_MIX:
            self._run_vid_mix_with_ffmpeg(t0)
            return

        s  = self.s
        gray_arg = int(s['vid_gray']) if self.mode == MODE_VIDEO else int(s['img_gray'])
        vid_inv  = int(s['vid_invert'])
        vid_rm   = int(s['vid_rm_aud'])

        last_prog = [0]
        def prog_cb(val):
            if val > last_prog[0]:
                last_prog[0] = val
                self.progress.emit(val)
        c_prog = ProgressCB(prog_cb)

        # C++ API Yeni Signature ile çağrılır
        ret = _cpp.kavram_convert(
            self.in_path.encode(), self.out_path.encode(),
            self.cover_path.encode() if self.cover_path else None,
            self.mode,
            ctypes.c_float(s['speed']),
            ctypes.c_float(s['pitch']),
            ctypes.c_int(s['effect']),
            ctypes.c_int(1 if s['change_freq'] else 0),
            ctypes.c_int(s['new_freq']),
            ctypes.c_int(1 if s['pdf_invert'] else 0),
            ctypes.c_int(1 if s['pdf_gray'] else 0),
            ctypes.c_int(1 if s['img_invert'] else 0),
            ctypes.c_int(gray_arg),
            ctypes.c_int(s['img_scale']),
            ctypes.c_int(vid_inv),
            ctypes.c_int(vid_rm),
            ctypes.c_int(1 if self.is_preview else 0),
            c_prog
        )

        if self._stop:
            return

        if ret == -99:
            return

        if self.mode == MODE_PDF and ret == -2:
            self.progress.emit(0)
            self._handle_pdf_fallback_with_fitz()
            return

        if ret != 0:
            err = _cpp.kavram_last_error().decode(errors='replace')
            if not err:
                err = f"İşlem başarısız (kod {ret})"
            self.error.emit(err)
            return

        self.progress.emit(100)
        self.finished.emit(self.out_path, time.time() - t0)

    def _run_vid_mix_with_ffmpeg(self, t0):
        """Videoya harici ses ekler ve gerekirse ikon çizer"""
        s = self.s
        self.progress.emit(10)
        success, err = mix_video_and_audio(
            self.in_path, s['vid_audio_path'], self.out_path,
            s['vid_invert'], s['vid_gray'], self.is_preview,
            lambda p: self.progress.emit(p)
        )
        if self._stop: return
        if not success:
            self.error.emit(err)
            return
        self.progress.emit(100)
        self.finished.emit(self.out_path, time.time() - t0)

    def _run_aud2vid_with_ffmpeg(self, t0):
        s = self.s
        tmp_audio_path = os.path.join(CONVERT_DIR, f"temp_audio_{uuid.uuid4().hex}.wav")

        tmp_prog = [0]
        def tmp_cb(val):
            if val > tmp_prog[0]:
                tmp_prog[0] = val
                self.progress.emit(int(val * 0.3))
        c_prog = ProgressCB(tmp_cb)
        ret = _cpp.kavram_convert(
            self.in_path.encode(), tmp_audio_path.encode(), None,
            MODE_AUDIO,
            ctypes.c_float(s['speed']),
            ctypes.c_float(s['pitch']),
            ctypes.c_int(s['effect']),
            ctypes.c_int(1 if s['change_freq'] else 0),
            ctypes.c_int(s['new_freq']),
            0, 0, 0, 0, 0, 0, 0,
            ctypes.c_int(1 if self.is_preview else 0),
            c_prog
        )
        if ret != 0 or self._stop:
            if os.path.exists(tmp_audio_path):
                os.unlink(tmp_audio_path)
            if ret != 0:
                err = _cpp.kavram_last_error().decode(errors='replace')
                self.error.emit(f"Ses işleme başarısız: {err}")
            return

        self.progress.emit(35)
        success, err_msg = create_video_from_audio_image(
            tmp_audio_path, self.cover_path, self.out_path,
            self.is_preview, lambda p: self.progress.emit(35 + int(p * 0.6))
        )
        try: os.unlink(tmp_audio_path)
        except: pass

        if self._stop: return
        if not success:
            self.error.emit(err_msg)
            return

        self.progress.emit(100)
        self.finished.emit(self.out_path, time.time() - t0)

    def _handle_pdf_fallback_with_fitz(self):
        def update_prog(pct): self.progress.emit(pct)
        success, err = pdf_convert_with_fitz(
            self.in_path, self.out_path,
            self.s['pdf_invert'], self.s['pdf_gray'],
            self.out_path.lower().endswith('.txt'),
            update_prog
        )
        if success: self.finished.emit(self.out_path, 0.0)
        else: self.error.emit(f"PDF dönüştürme başarısız: {err}")

    def stop(self):
        self._stop = True
        if _cpp: _cpp.kavram_cancel()

# ── Önizleme Yardımcıları ────────────────────────────────────────────────────

class ZoomablePreviewLabel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scale = 1.0
        self._min_scale = 0.5
        self._max_scale = 5.0
        self._default_scale = 1.0
        self._offset_x = 0
        self._offset_y = 0
        self._dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._last_offset_x = 0
        self._last_offset_y = 0

        self._pixmap = None
        self._scaled_pixmap = None
        self._text_message = ""

        self.setMinimumSize(300, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("background-color:#1F1F1F;border-radius:6px;")
        self.setCursor(Qt.SizeAllCursor)

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self._text_message = ""
        self.reset_view()

    def setText(self, text):
        self._pixmap = None
        self._scaled_pixmap = None
        self._text_message = text
        self.update()

    def reset_view(self):
        self._scale = self._default_scale
        self._offset_x = 0
        self._offset_y = 0
        self._update_scaled_pixmap()
        self.update()

    # DÜZELTME: resizeEvent eklendi - Tam ekran sorunu çözüldü
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scaled_pixmap()
        self.update()

    def _update_scaled_pixmap(self):
        if self._pixmap is None:
            self._scaled_pixmap = None
            return
        if self._scale == 1.0:
            self._scaled_pixmap = self._pixmap
        else:
            w = int(self._pixmap.width() * self._scale)
            h = int(self._pixmap.height() * self._scale)
            if w > 0 and h > 0:
                self._scaled_pixmap = self._pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            else:
                self._scaled_pixmap = self._pixmap

    def wheelEvent(self, event):
        if self._pixmap is None: return

        mouse_x = event.x()
        mouse_y = event.y()

        if self._scaled_pixmap:
            pix_w = self._scaled_pixmap.width()
            pix_h = self._scaled_pixmap.height()
            label_w = self.width()
            label_h = self.height()
            offset_x = (label_w - pix_w) // 2
            offset_y = (label_h - pix_h) // 2
        else:
            offset_x = offset_y = 0

        pixcoord_x = mouse_x - offset_x - self._offset_x
        pixcoord_y = mouse_y - offset_y - self._offset_y

        if pixcoord_x < 0 or pixcoord_y < 0: return

        scale_factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        new_scale = max(self._min_scale, min(self._max_scale, self._scale * scale_factor))

        if new_scale != self._scale:
            old_scale = self._scale
            self._scale = new_scale
            self._update_scaled_pixmap()

            if old_scale != 0 and new_scale != 0:
                self._offset_x = int(pixcoord_x * (1 - new_scale / old_scale))
                self._offset_y = int(pixcoord_y * (1 - new_scale / old_scale))
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_start_x = event.x()
            self._drag_start_y = event.y()
            self._last_offset_x = self._offset_x
            self._last_offset_y = self._offset_y
            self.setCursor(Qt.ClosedHandCursor)
        elif event.button() == Qt.RightButton:
            self.reset_view()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._offset_x = self._last_offset_x + (event.x() - self._drag_start_x)
            self._offset_y = self._last_offset_y + (event.y() - self._drag_start_y)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self.setCursor(Qt.SizeAllCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(event.rect(), QColor("#1F1F1F"))

        if self._pixmap is None and self._text_message:
            painter.setPen(QColor("#666666"))
            painter.drawText(self.rect(), Qt.AlignCenter, self._text_message)
            return

        if self._scaled_pixmap is None:
            painter.setPen(QColor("#666666"))
            painter.drawText(self.rect(), Qt.AlignCenter, "Dosya yükleyin")
            return

        # DÜZELTME: Her paintEvent'te dinamik merkezleme
        x = (self.width() - self._scaled_pixmap.width()) // 2 + self._offset_x
        y = (self.height() - self._scaled_pixmap.height()) // 2 + self._offset_y

        if self._scaled_pixmap.hasAlpha():
            painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.drawPixmap(int(x), int(y), self._scaled_pixmap)

def generate_image_preview(img_path, max_size=600):
    try:
        pixmap = QPixmap(img_path)
        if pixmap.isNull(): return None
        if pixmap.width() > max_size or pixmap.height() > max_size:
            return pixmap.scaled(max_size, max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return pixmap
    except Exception as e:
        print(f"[Kavram] Resim önizleme hatası: {e}")
        return None

def generate_pdf_preview(pdf_path, max_size=600):
    if not HAS_FITZ: return None
    try:
        doc = fitz.open(pdf_path)
        if doc.page_count == 0:
            doc.close(); return None
        page = doc[0]
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        doc.close()
        img = QImage.fromData(pix.tobytes("png"))
        if img.isNull(): return None
        pixmap = QPixmap.fromImage(img)
        if pixmap.width() > max_size or pixmap.height() > max_size:
            return pixmap.scaled(max_size, max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return pixmap
    except Exception as e:
        print(f"[Kavram] PDF önizleme hatası: {e}")
        return None

def generate_txt_preview(txt_path, max_lines=15):
    try:
        with open(txt_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= max_lines: break
                lines.append(line.rstrip())
            return '\n'.join(lines)
    except Exception as e:
        print(f"[Kavram] TXT önizleme hatası: {e}")
        return None

# ── GUI (UniversalConverter) ────────────────────────────────────────────────────
class UniversalConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.file_path        = None
        self.cover_image_path = None
        self.vid_audio_path   = None
        self.current_mode     = 'audio'
        self.conv_thread      = None
        self.conv_worker      = None
        self._out_path        = None
        self.qsettings        = QSettings("Kavram", "UniversalConverter")
        self._session_num     = self._next_export_counter()

        self._ffplay_proc = None
        self._preview_timer = None
        self._is_playing = False
        self._video_preview_process = None

        self.preview_thread = None
        self.preview_worker = None

        self._media_player = None
        self._video_widget = None

        self._cached_preview_path = None
        self._cached_preview_settings = None

        self._init_ui()
        self._reset()
        self._update_btns()

    def _next_export_counter(self):
        n = self.qsettings.value("export_counter", 0, int) + 1
        self.qsettings.setValue("export_counter", n)
        return n

    def _get_settings_hash(self):
        s = self._get_settings()
        mode_int = self._get_current_mode_int()
        fmt = self.c_fmt.currentText()
        cover = self.cover_image_path
        vid_aud = self.vid_audio_path
        return (mode_int, fmt, cover, vid_aud, s['speed'], s['pitch'], s['effect'], 
                s['change_freq'], s['new_freq'], s['vid_invert'], s['vid_rm_aud'], s['vid_gray'])

    # DÜZELTME: Thread güvenli başlatma
    def _start_preview_pipeline(self):
        if not self.file_path: return
        ext = os.path.splitext(self.file_path)[1].lower()

        # Saf video (efekt yoksa) doğrudan oynat
        if ext in VIDEO_EXT and not self.vid_audio_path and self.c_vid_gray.currentIndex() == 0 and self.c_vid_inv.currentIndex() == 0 and self.c_vid_rm_aud.currentIndex() == 0:
            self._start_video_preview_playback(self.file_path)
            return

        # DÜZELTME: Çalışan thread varsa temizle
        if self.preview_thread and self.preview_thread.isRunning():
            if self.preview_worker:
                try: self.preview_worker.stop()
                except: pass
            self.preview_thread.quit()
            if not self.preview_thread.wait(3000):
                self.preview_thread.terminate()
                self.preview_thread.wait(2000)

        mode = self._get_current_mode_int()
        if mode == -1:
            QMessageBox.warning(self, "Uyarı", "Oluşturmak için kapak resmi seçin.")
            return

        current_hash = self._get_settings_hash()
        if self._cached_preview_path and os.path.exists(self._cached_preview_path) and self._cached_preview_settings == current_hash:
            self.btn_play_preview.setEnabled(True)
            self.btn_play_preview.setText("Play")
            return

        s = self._get_settings()
        fmt = self.c_fmt.currentText()

        if mode in (MODE_AUD2VID, MODE_VID_MIX):
            preview_ext = '.mp4'
        else:
            preview_ext = '.wav' if self.current_mode == 'audio' else fmt

        self._preview_path = os.path.join(CONVERT_DIR, f"preview_{uuid.uuid4().hex}{preview_ext}")

        self.btn_play_preview.setText("Hazırlanıyor...")
        self.btn_play_preview.setEnabled(False)

        use_fallback = False
        broken, reason = _preflight_check(self.file_path)
        if broken and mode not in (MODE_AUD2VID, MODE_VID_MIX):
            use_fallback = True

        self.preview_thread = QThread()
        if use_fallback:
            self.preview_worker = FfmpegFallbackWorker(
                self.file_path, self._preview_path, preview_ext, speed=s.get('speed', 1.0), is_preview=True)
        else:
            cov = self.cover_image_path if mode == MODE_AUD2VID else None
            self.preview_worker = ConversionWorker(
                self.file_path, self._preview_path, cov, mode, s, is_preview=True)

        self.preview_worker.moveToThread(self.preview_thread)
        self.preview_thread.started.connect(self.preview_worker.run)
        self.preview_worker.finished.connect(self._on_preview_done)
        self.preview_worker.error.connect(self._on_preview_error)
        self.preview_worker.finished.connect(self.preview_thread.quit)
        self.preview_worker.error.connect(self.preview_thread.quit)

        self.preview_thread.start(QThread.LowPriority)

    def _play_preview_file(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in VIDEO_EXT: self._start_video_preview_playback(file_path)
        else: self._start_ffplay(file_path)

    def _on_preview_done(self, out_path, elapsed):
        self.btn_play_preview.setEnabled(True)
        self.btn_play_preview.setText("Play")
        self._cached_preview_path = out_path
        self._cached_preview_settings = self._get_settings_hash()
        self.lbl_status.setText("Önizleme hazır. Play butonuna basın.")

    def _on_preview_error(self, msg):
        self.btn_play_preview.setEnabled(True)
        self.btn_play_preview.setText("Play")
        QMessageBox.warning(self, "Önizleme Hatası", f"Önizleme oluşturulamadı:\n{msg}")

    def _start_ffplay(self, path):
        try:
            self._ffplay_proc = subprocess.Popen(
                [FFPLAY_PATH, '-nodisp', '-autoexit', path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            self._is_playing = True
            self.btn_play_preview.setText("Pauze")

            if self._preview_timer: self._preview_timer.stop()
            self._preview_timer = QTimer()
            self._preview_timer.timeout.connect(self._check_ffplay_status)
            self._preview_timer.start(500)
        except Exception as e:
            print(f"[Kavram] Oynatma hatası: {e}")
            self._stop_playback()

    def _check_ffplay_status(self):
        if self._ffplay_proc and self._ffplay_proc.poll() is not None:
            self._stop_playback()

    def _stop_playback(self):
        if self._media_player:
            self._media_player.stop()
            self._media_player.setMedia(QMediaContent())

        if self._ffplay_proc:
            try:
                self._ffplay_proc.terminate()
                self._ffplay_proc.wait(timeout=1)
            except:
                try: self._ffplay_proc.kill()
                except: pass
            self._ffplay_proc = None

        if self._video_preview_process:
            try:
                self._video_preview_process.terminate()
                self._video_preview_process.wait(timeout=1)
            except:
                try: self._video_preview_process.kill()
                except: pass
            self._video_preview_process = None

        self._is_playing = False
        if hasattr(self, 'btn_play_preview'):
            self.btn_play_preview.setText("Play")

        if self._preview_timer:
            self._preview_timer.stop()
            self._preview_timer = None

    def _toggle_playback(self):
        if self._is_playing:
            self._stop_playback()
        else:
            if self._cached_preview_path and os.path.exists(self._cached_preview_path) and self._cached_preview_settings == self._get_settings_hash():
                self._play_preview_file(self._cached_preview_path)
            else:
                self._start_preview_pipeline()

    def _on_media_position_changed(self, position):
        if self._media_player:
            duration = self._media_player.duration()
            if duration > 0 and position >= 5000:
                self._stop_playback()
                self._restore_video_preview_ui()

    def _on_media_state_changed(self, state):
        if not HAS_MEDIA: return
        if hasattr(QMediaPlayer, 'StoppedState') and state == QMediaPlayer.StoppedState and self._is_playing:
            self._restore_video_preview_ui()

    def _on_media_error(self, error):
        error_str = self._media_player.errorString() if self._media_player and hasattr(self._media_player, 'errorString') else "Bilinmeyen hata"
        QMessageBox.warning(self, "Video Hatası", f"Video oynatılamadı: {error_str}")
        self._restore_video_preview_ui()

    # DÜZELTME: Video önizleme artık her zaman PyQt içinde gömülü
    def _start_video_preview_playback(self, video_path):
        if not os.path.exists(video_path): return
        self._stop_playback()

        # Her zaman gömülü oynatıcıyı dene
        if HAS_MEDIA and self._media_player and self._video_widget:
            self.preview_scroll.setVisible(False)
            self.preview_zoom.setVisible(False)
            self.preview_label.setVisible(True)
            self.preview_label.setText("Video Önizleme (5 sn)")
            self._video_widget.setVisible(True)

            url = QMediaContent(QUrl.fromLocalFile(video_path))
            if self._media_player.media().canonicalUrl() != url:
                self._media_player.setMedia(url)
            self._media_player.play()
            self._is_playing = True
            self.btn_play_preview.setText("Pauze")
            
            if self._preview_timer: self._preview_timer.stop()
            self._preview_timer = QTimer()
            self._preview_timer.setSingleShot(True)
            self._preview_timer.timeout.connect(self._stop_playback)
            self._preview_timer.start(5000)
            return

        # Eğer HAS_MEDIA yoksa, kullanıcıya bilgi ver
        QMessageBox.information(self, "Bilgi", 
            "Video oynatma için QtMultimedia kütüphanesi gerekli.\n"
            "Ses önizlemesi için Play butonuna basabilirsiniz.")
        self._show_audio_info(is_video=True)

    def _restore_video_preview_ui(self):
        if self._video_widget: self._video_widget.setVisible(False)
        self._show_audio_info(is_video=True)

    def _init_ui(self):
        self.setWindowTitle('Convert')
        self.resize(920, 600)
        self.setWindowIcon(QIcon("ikon/Kavram.png"))
        self.setStyleSheet(
            'background-color:#2E2E2E;color:#E0E0E0;'
            'font-family:"Inter",sans-serif;font-size:11pt;')
        ml = QVBoxLayout(self)
        ml.setContentsMargins(0, 0, 0, 0); ml.setSpacing(0)
        ml.addWidget(self._make_topbar())
        ml.addWidget(self._make_content())

    def _make_topbar(self):
        bar = QFrame()
        bar.setFixedHeight(40)
        bar.setStyleSheet('background-color:#1F1F1F;border-bottom:2px solid #555;')
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(15, 5, 15, 5); bl.setSpacing(10)

        self.btn_file    = QPushButton('File')
        self.btn_convert = QPushButton('Convert')
        self.btn_reset   = QPushButton('Reset')
        self.btn_play_preview = QPushButton('Play')
        self.btn_play_preview.setEnabled(False)
        self.btn_export  = QPushButton('Export')

        self.btn_file.clicked.connect(self._select_file)
        self.btn_convert.clicked.connect(self._start)
        self.btn_export.clicked.connect(self._export)
        self.btn_reset.clicked.connect(self._reset)
        self.btn_play_preview.clicked.connect(self._toggle_playback)

        bs = self._btn_css()
        for b in [self.btn_file, self.btn_convert, self.btn_reset, self.btn_export]:
            b.setFixedSize(80, 30); b.setStyleSheet(bs)
            b.setCursor(Qt.PointingHandCursor)

        self.btn_play_preview.setFixedSize(90, 30)
        play_style = bs.replace('background-color:transparent', 'background-color:#3A3A3A')
        self.btn_play_preview.setStyleSheet(play_style)

        bl.addWidget(self.btn_file)
        bl.addWidget(self.btn_convert)
        bl.addWidget(self.btn_reset)
        bl.addWidget(self.btn_play_preview)
        bl.addStretch()
        bl.addWidget(self.btn_export)
        return bar

    def _make_content(self):
        cf = QFrame()
        cl = QVBoxLayout(cf)
        cl.setContentsMargins(15, 10, 15, 10); cl.setSpacing(10)

        info_frame = QFrame()
        info_frame.setStyleSheet("background-color:#282828;border-radius:8px;")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(5)

        self.lbl_status = QLabel('Lütfen bir dosya seçin.')
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("font-size:14px;color:#888;")

        self.lbl_info = QLabel("Dosya Bilgisi: -")
        self.lbl_info.setAlignment(Qt.AlignCenter)
        self.lbl_info.setStyleSheet("font-size:11px;color:#666;")

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMinimumHeight(12)
        self.progress.setStyleSheet("""
            QProgressBar{border:1px solid #444;border-radius:6px;
                background-color:#1F1F1F;color:#E0E0E0;
                text-align:center;padding:2px;}
            QProgressBar::chunk{background-color:#888;border-radius:5px;}""")

        info_layout.addWidget(self.lbl_status)
        info_layout.addWidget(self.lbl_info)
        info_layout.addWidget(self.progress)

        main_frame = QFrame()
        main_hlayout = QHBoxLayout(main_frame)
        main_hlayout.setContentsMargins(0, 5, 0, 0)
        main_hlayout.setSpacing(15)

        left_panel = self._make_settings()

        # DÜZELTME: Sağ panel layout düzeltildi
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color:#282828;border-radius:10px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)

        self.preview_label = QLabel("Önizleme")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("color:#888;font-weight:bold;font-size:12px;")

        self.preview_zoom = ZoomablePreviewLabel()
        self.preview_zoom.setVisible(False)

        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollArea > QWidget > QLabel { background-color: transparent; }
        """)

        self.preview_image = QLabel()
        self.preview_image.setAlignment(Qt.AlignCenter)
        self.preview_image.setText("Dosya Yüklendi")
        self.preview_image.setStyleSheet("color:#555;font-size:12px;background-color:#1F1F1F;border-radius:6px;padding:20px;")

        self.preview_scroll.setWidget(self.preview_image)
        self.preview_scroll.setVisible(False)

        if HAS_MEDIA:
            self._video_widget = QVideoWidget()
            self._video_widget.setMinimumSize(320, 180)
            self._video_widget.setMaximumSize(640, 360)
            self._video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
            self._video_widget.setStyleSheet("background-color:#000000;border-radius:6px;")
            self._video_widget.setVisible(False)

            self._media_player = QMediaPlayer()
            self._media_player.setVideoOutput(self._video_widget)
            self._media_player.setVolume(100)
            self._media_player.stateChanged.connect(self._on_media_state_changed)
            self._media_player.error.connect(self._on_media_error)
            self._media_player.positionChanged.connect(self._on_media_position_changed)
        else:
            self._video_widget = None
            self._media_player = None

        right_layout.addWidget(self.preview_label)
        right_layout.addWidget(self.preview_zoom, 1)
        right_layout.addWidget(self.preview_scroll, 1)
        if HAS_MEDIA and self._video_widget:
            right_layout.addWidget(self._video_widget, 1)

        main_hlayout.addWidget(left_panel, 1) 
        main_hlayout.addWidget(right_panel, 1)

        cl.addWidget(info_frame)
        cl.addWidget(main_frame, 1)
        return cf

    def _make_settings(self):
        fr = QFrame()
        fr.setStyleSheet("""
            QFrame{border:1px solid #444;border-radius:12px;background-color:#282828;}
            QLabel{border:none;font-weight:bold;color:#E0E0E0;}
            QComboBox,QLineEdit{padding:6px;border:1px solid #555;border-radius:6px;
                background-color:#1F1F1F;color:#E0E0E0;}
            QComboBox::drop-down{border:0px;}""")

        self.fl = QFormLayout(fr)
        self.fl.setContentsMargins(15, 15, 15, 15); self.fl.setSpacing(12)

        def row(label, widget, tip=None):
            if tip: widget.setToolTip(tip)
            self.fl.addRow(label, widget)
            return widget

        self.c_fmt = QComboBox()
        self.c_fmt.currentIndexChanged.connect(self._on_fmt_changed)
        self.c_fmt.currentIndexChanged.connect(self._invalidate_preview_cache)
        row("Format (Export Format):", self.c_fmt)

        self.c_freq_on = QComboBox()
        self.c_freq_on.addItems(['Kapalı (Off)', 'Açık (On)'])
        self.c_freq_on.currentIndexChanged.connect(self._toggle_freq)
        self.c_freq_on.currentIndexChanged.connect(self._invalidate_preview_cache)
        row("Frekans Değiştir (Frequency):", self.c_freq_on)
        self.e_freq = QLineEdit()
        self.e_freq.setPlaceholderText("Örnek: 44100")
        self.e_freq.setVisible(False)
        self.e_freq.textChanged.connect(self._invalidate_preview_cache)
        row("Yeni Frekans Hz:", self.e_freq)

        self.c_speed = QComboBox()
        speeds = [f"{v:.2f}x" for v in [
            .10,.15,.20,.25,.30,.35,.40,.45,.50,.55,.60,.65,.70,.75,.80,.85,.90,.95,
            1.0,1.05,1.10,1.15,1.20,1.25,1.30,1.35,1.40,
            1.50,1.60,1.70,1.80,1.90,2.0,2.20,2.50,2.70,3.0,3.50,4.0]]
        self.c_speed.addItems(speeds)
        self.c_speed.setCurrentText('1.00x')
        self.c_speed.currentIndexChanged.connect(self._invalidate_preview_cache)
        row("Ses Hızı (Speed):", self.c_speed)

        self.c_pitch = QComboBox()
        pitch_items = {f"Yüksek Perde ({-i} Ton)": -i for i in range(6, 0, -1)}
        pitch_items["Normal Perde (0 Ton)"] = 0
        pitch_items.update({f"Düşük Perde (+{i} Ton)": i for i in range(1, 7)})
        self._pitch_vals = list(pitch_items.values())
        self.c_pitch.addItems(pitch_items.keys())
        self.c_pitch.currentIndexChanged.connect(self._invalidate_preview_cache)
        row("Ses Perdesi (Pitch):", self.c_pitch)

        self.c_effect = QComboBox()
        self.c_effect.addItems([
            "Efekt Yok", "Normalleştir", "Sıkıştır", "Alçak Geçiren Filtre",
            "Yüksek Geçiren Filtre", "Giriş/Çıkış Fade", "Faz Ters Çevir",
            "Sola Kaydır", "Sağa Kaydır"])
        self.c_effect.currentIndexChanged.connect(self._invalidate_preview_cache)
        row("Ses Efekti:", self.c_effect)

        self.btn_cover = QPushButton("Kapak Resmi Seç")
        self.btn_cover.setStyleSheet(self._btn_css())
        self.btn_cover.setCursor(Qt.PointingHandCursor)
        self.btn_cover.clicked.connect(self._select_cover)
        self.btn_cover.setVisible(False)
        self.lbl_cover = QLabel("Resim seçilmedi")
        self.lbl_cover.setStyleSheet("color:#888;font-size:10px;")
        self.lbl_cover.setVisible(False)
        row("Video Kapak Resmi:", self.btn_cover)
        row("", self.lbl_cover)

        # YENİ VİDEO ÖZELLİKLERİ
        self.c_vid_inv = QComboBox()
        self.c_vid_inv.addItems(['Hayır (No)', 'Evet (Yes)'])
        self.c_vid_inv.currentIndexChanged.connect(self._invalidate_preview_cache)
        row("Video Renkleri Ters Çevir:", self.c_vid_inv)
        
        self.c_vid_gray = QComboBox()
        self.c_vid_gray.addItems(['Hayır (No)', 'Evet (Yes)'])
        self.c_vid_gray.currentIndexChanged.connect(self._invalidate_preview_cache)
        row("Video Gri Ton (Grayscale):", self.c_vid_gray)
        
        self.c_vid_rm_aud = QComboBox()
        self.c_vid_rm_aud.addItems(['Hayır (No)', 'Evet (Yes)'])
        self.c_vid_rm_aud.currentIndexChanged.connect(self._invalidate_preview_cache)
        row("Video Sesini Tamamen Sil:", self.c_vid_rm_aud)

        self.btn_vid_aud = QPushButton("Harici Ses Ekle (Sync)")
        self.btn_vid_aud.setStyleSheet(self._btn_css())
        self.btn_vid_aud.setCursor(Qt.PointingHandCursor)
        self.btn_vid_aud.clicked.connect(self._select_vid_audio)
        self.lbl_vid_aud = QLabel("Ses seçilmedi")
        self.lbl_vid_aud.setStyleSheet("color:#888;font-size:10px;")
        row("Videoya Ses Ekle:", self.btn_vid_aud)
        row("", self.lbl_vid_aud)

        # PDF & IMG
        self.c_pdf_inv  = QComboBox(); self.c_pdf_inv.addItems(['Hayır', 'Evet'])
        row("PDF Ters Çevir:", self.c_pdf_inv)
        self.c_pdf_gray = QComboBox(); self.c_pdf_gray.addItems(['Hayır', 'Evet'])
        row("PDF Gri Ton:", self.c_pdf_gray)

        self.c_img_inv  = QComboBox(); self.c_img_inv.addItems(['Hayır', 'Evet'])
        row("Resim Ters Çevir:", self.c_img_inv)
        self.c_img_gray = QComboBox(); self.c_img_gray.addItems(['Hayır', 'Evet'])
        row("Resim Gri Ton:", self.c_img_gray)
        self.c_img_scale = QComboBox()
        self.c_img_scale.addItems([
            '-5 (x0.25)', '-4 (x0.35)', '-3 (x0.50)', '-2 (x0.65)', '-1 (x0.80)',
            '0 (Orijinal)', '+1 (x1.25)', '+2 (x1.50)', '+3 (x1.75)', '+4 (x2.00)', '+5 (x2.50)'])
        self.c_img_scale.setCurrentIndex(5)
        row("Resim Çözünürlüğü:", self.c_img_scale)

        self._audio_ws = [self.c_freq_on, self.e_freq, self.c_speed, self.c_pitch, self.c_effect]
        self._video_ws = [self.c_vid_inv, self.c_vid_gray, self.c_vid_rm_aud, self.btn_vid_aud, self.lbl_vid_aud]
        self._pdf_ws   = [self.c_pdf_inv, self.c_pdf_gray]
        self._img_ws   = [self.c_img_inv, self.c_img_gray, self.c_img_scale]

        self._toggle_ui('audio')
        return fr

    def _invalidate_preview_cache(self):
        self._cached_preview_path = None
        self._cached_preview_settings = None

    def _row_vis(self, w, v):
        w.setVisible(v)
        lbl = self.fl.labelForField(w)
        if lbl: lbl.setVisible(v)

    def _toggle_ui(self, mode):
        self.current_mode = mode
        for w in self._audio_ws + self._video_ws + self._pdf_ws + self._img_ws:
            self._row_vis(w, False)
        self._row_vis(self.btn_cover, False)
        self.lbl_cover.setVisible(False)

        self.c_fmt.blockSignals(True)
        self.c_fmt.clear()
        if mode == 'pdf':
            for w in self._pdf_ws: self._row_vis(w, True)
            self.c_fmt.addItems(['.pdf', '.txt'])
        elif mode == 'image':
            for w in self._img_ws: self._row_vis(w, True)
            self.c_fmt.addItems(['.jpg', '.png', '.webp', '.bmp'])
        elif mode == 'video':
            for w in self._audio_ws: self._row_vis(w, True)
            self._row_vis(self.e_freq, self.c_freq_on.currentIndex() == 1)
            for w in self._video_ws: self._row_vis(w, True)
            self.c_fmt.addItems(['.mp4', '.mkv', '.avi', '.wav', '.mp3'])
        else:
            for w in self._audio_ws: self._row_vis(w, True)
            self._row_vis(self.e_freq, self.c_freq_on.currentIndex() == 1)
            self.c_fmt.addItems(['.wav', '.opus', '.mp3', '.m4a', '.mp4', '.mkv'])
        self.c_fmt.blockSignals(False)

        if self.file_path:
            ext = os.path.splitext(self.file_path)[1].lower()
            idx = self.c_fmt.findText(ext)
            if idx >= 0: self.c_fmt.setCurrentIndex(idx)

        self._on_fmt_changed()
        self._invalidate_preview_cache()

    def _on_fmt_changed(self):
        fmt  = self.c_fmt.currentText()
        show_cov = self.current_mode == 'audio' and fmt in ['.mp4', '.mkv']
        self._row_vis(self.btn_cover, show_cov)
        self.lbl_cover.setVisible(show_cov and bool(self.cover_image_path))
        self._update_preview_original()
        self._invalidate_preview_cache()

    def _toggle_freq(self, idx):
        self._row_vis(self.e_freq, idx == 1)
        self._invalidate_preview_cache()

    def _update_preview_original(self):
        if not hasattr(self, 'preview_scroll'): return
        if not self.file_path:
            self.preview_scroll.setVisible(False)
            self.preview_zoom.setVisible(False)
            self.preview_label.setVisible(False)
            if self._video_widget: self._video_widget.setVisible(False)
            return

        ext = os.path.splitext(self.file_path)[1].lower()
        try:
            if ext in IMAGE_EXT:
                self._show_original_image()
                if self._video_widget: self._video_widget.setVisible(False)
            elif ext in PDF_EXT:
                self._show_original_pdf()
                if self._video_widget: self._video_widget.setVisible(False)
            elif ext in VIDEO_EXT:
                self._show_video_thumbnail()
            elif ext in AUDIO_EXT:
                fmt = self.c_fmt.currentText()
                if self.cover_image_path and fmt in ['.mp4', '.mkv']:
                    self.preview_zoom.setVisible(False)
                    self.preview_scroll.setVisible(True)
                    self.preview_label.setVisible(True)
                    self.preview_label.setText("Video Önizleme (Ses+Resim)")
                    self.preview_image.setText("\nSes + Kapak resmi. Play ile izleyin.")
                    if self._video_widget: self._video_widget.setVisible(False)
                else:
                    self._show_audio_info(is_video=False)
                    if self._video_widget: self._video_widget.setVisible(False)
            else:
                self.preview_scroll.setVisible(False)
                self.preview_zoom.setVisible(False)
                self.preview_label.setVisible(False)
                if self._video_widget: self._video_widget.setVisible(False)
        except Exception as e:
            print(f"[Kavram] Önizleme hatası: {e}")

    def _show_video_thumbnail(self):
        if not hasattr(self, 'preview_scroll'): return
        self.preview_scroll.setVisible(False)
        self.preview_zoom.setVisible(False)
        self.preview_label.setVisible(True)
        self.preview_label.setText("Video Önizleme (Duraklatıldı)")
        if HAS_MEDIA and self._video_widget and self._media_player:
            self._video_widget.setVisible(True)
            url = QUrl.fromLocalFile(self.file_path)
            if self._media_player.media().canonicalUrl() != url:
                self._media_player.setMedia(QMediaContent(url))
            self._media_player.pause()
        else:
            self.preview_label.setText("Video Önizleme")
            self.preview_image.setText("\nVideo dosyası yüklendi\nPlay ile önizleyin.")
            self.preview_scroll.setVisible(True)

    def _show_original_image(self):
        if not hasattr(self, 'preview_zoom'): return
        self.preview_scroll.setVisible(False)
        self.preview_zoom.setVisible(True)
        self.preview_label.setVisible(True)
        self.preview_label.setText("Resim Önizleme")
        pixmap = generate_image_preview(self.file_path, max_size=400)
        self.preview_zoom.setPixmap(pixmap) if pixmap else self.preview_zoom.setText("Yüklenemedi")

    def _show_original_pdf(self):
        if not hasattr(self, 'preview_zoom'): return
        self.preview_scroll.setVisible(False)
        self.preview_zoom.setVisible(True)
        self.preview_label.setVisible(True)
        self.preview_label.setText("PDF Önizleme - Sayfa 1")
        pixmap = generate_pdf_preview(self.file_path, max_size=400)
        self.preview_zoom.setPixmap(pixmap) if pixmap else self.preview_zoom.setText("Yüklenemedi")

    def _show_audio_info(self, is_video=False):
        if not hasattr(self, 'preview_scroll'): return
        self.preview_zoom.setVisible(False)
        self.preview_scroll.setVisible(True)
        self.preview_label.setVisible(True)
        if is_video:
            self.preview_label.setText("Video Önizleme")
            self.preview_image.setText("\nVideo yüklendi. Play ile izleyin.")
        else:
            self.preview_label.setText("Ses Önizleme")
            self.preview_image.setText("\nSes yüklendi. Play ile dinleyin.")
        self.preview_image.setAlignment(Qt.AlignCenter)
        self.preview_image.setScaledContents(False)

    def _select_file(self):
        init = EXPORT_DIR if os.path.exists(EXPORT_DIR) else os.path.expanduser('~')
        ae = ' '.join('*' + x for x in ALL_EXT)
        p, _ = QFileDialog.getOpenFileName(
            self, "Dosya Seç", init,
            f"Tüm Desteklenen ({ae});;"
            f"Ses ({'  '.join('*'+x for x in AUDIO_EXT)});;"
            f"Video ({'  '.join('*'+x for x in VIDEO_EXT)});;"
            f"PDF (*.pdf);;Resim ({'  '.join('*'+x for x in IMAGE_EXT)})")
        if not p: return
        self.file_path        = p
        self.cover_image_path = None
        self.vid_audio_path   = None
        self.lbl_cover.setText("Resim seçilmedi")
        self.lbl_vid_aud.setText("Ses seçilmedi")
        self._out_path = None
        self._invalidate_preview_cache()

        ext  = os.path.splitext(p)[1].lower()
        name = os.path.basename(p)
        mode_map = {**{e: 'pdf' for e in PDF_EXT}, **{e: 'image' for e in IMAGE_EXT}, **{e: 'video' for e in VIDEO_EXT}}
        self.current_mode = mode_map.get(ext, 'audio')
        labels = {'pdf': 'PDF Belgesi', 'image': 'Resim', 'video': 'Video', 'audio': 'Ses'}
        self.lbl_info.setText(f"{labels[self.current_mode]}: {name}")
        self.lbl_status.setText(f"Yüklendi:\n{name}")
        self._toggle_ui(self.current_mode)
        self._update_btns()
        self._update_preview_original()
        self.btn_play_preview.setEnabled(ext in AUDIO_EXT or ext in VIDEO_EXT)
        if not self.btn_play_preview.isEnabled(): self._stop_playback()

    def _select_cover(self):
        init = os.path.dirname(self.file_path) if self.file_path else os.path.expanduser('~')
        p, _ = QFileDialog.getOpenFileName(self, "Kapak Resmi Seç", init, "Resimler (*.jpg *.png *.webp *.bmp)")
        if p and os.path.exists(p):
            self.cover_image_path = p
            self.lbl_cover.setText(os.path.basename(p))
            self.lbl_cover.setVisible(True)
            self._update_preview_original()
            self._invalidate_preview_cache()

    def _select_vid_audio(self):
        init = os.path.dirname(self.file_path) if self.file_path else os.path.expanduser('~')
        p, _ = QFileDialog.getOpenFileName(self, "Videoya Eklenecek Sesi Seç", init, f"Ses ({' '.join('*'+x for x in AUDIO_EXT)})")
        if p and os.path.exists(p):
            self.vid_audio_path = p
            self.lbl_vid_aud.setText(os.path.basename(p))
            self.lbl_vid_aud.setVisible(True)
            self.c_vid_rm_aud.setCurrentIndex(0)
            self._invalidate_preview_cache()

    def _make_out_path(self):
        os.makedirs(CONVERT_DIR, exist_ok=True)
        ext  = self.c_fmt.currentText()
        base = os.path.splitext(os.path.basename(self.file_path))[0]
        candidate = os.path.join(CONVERT_DIR, f"_{self._session_num}_{base}{ext}")
        counter = 1
        original = candidate
        while os.path.exists(candidate):
            name, ext = os.path.splitext(original)
            candidate = f"{name}_{counter}{ext}"
            counter += 1
        return candidate

    def _get_current_mode_int(self):
        fmt = self.c_fmt.currentText()
        if self.current_mode == 'pdf': return MODE_PDF
        if self.current_mode == 'image': return MODE_IMAGE
        if self.current_mode == 'video' and fmt in ['.mp4', '.mkv', '.avi']:
            if self.vid_audio_path: return MODE_VID_MIX
            return MODE_VIDEO
        if self.current_mode == 'audio' and fmt in ['.mp4', '.mkv']:
            if not self.cover_image_path: return -1
            return MODE_AUD2VID
        return MODE_AUDIO

    # DÜZELTME: Thread güvenli başlatma
    def _start(self):
        if not self.file_path: return
        self._stop_playback()
        
        # Çalışan thread varsa temizle
        if self.conv_thread and self.conv_thread.isRunning():
            if self.conv_worker:
                try: self.conv_worker.stop()
                except: pass
            self.conv_thread.quit()
            if not self.conv_thread.wait(3000):
                self.conv_thread.terminate()
                self.conv_thread.wait(2000)
        
        mode = self._get_current_mode_int()
        if mode == -1:
            QMessageBox.warning(self, "Uyarı", "Video oluşturmak için kapak resmi seçin.")
            return

        s = self._get_settings()
        fmt = self.c_fmt.currentText()
        use_fallback = False
        if self.current_mode in ('video', 'audio') and mode not in (MODE_AUD2VID, MODE_VID_MIX):
            broken, reason = _preflight_check(self.file_path)
            if broken:
                use_fallback = True
                self.lbl_status.setText(f"⚠ Ses stream sorunu: {reason}\nFFmpeg ile onarılıyor...")

        out_path = self._make_out_path()
        self.progress.setValue(0)
        self.progress.setVisible(True)
        if not use_fallback: self.lbl_status.setText("İşleniyor...")
        self._update_btns(converting=True)

        self.conv_thread = QThread()
        if use_fallback and mode != MODE_AUD2VID:
            self.conv_worker = FfmpegFallbackWorker(self.file_path, out_path, fmt, speed=s.get('speed', 1.0), is_preview=False)
        else:
            self.conv_worker = ConversionWorker(self.file_path, out_path, self.cover_image_path, mode, s, is_preview=False)

        self.conv_worker.moveToThread(self.conv_thread)
        self.conv_thread.started.connect(self.conv_worker.run)
        self.conv_worker.finished.connect(self._on_done)
        self.conv_worker.error.connect(self._on_error)
        self.conv_worker.progress.connect(self.progress.setValue)
        self.conv_worker.finished.connect(self.conv_thread.quit)
        self.conv_worker.error.connect(self.conv_thread.quit)

        self.conv_thread.start(QThread.LowPriority)

    def _on_done(self, out_path, elapsed):
        self._out_path = out_path
        self.lbl_status.setText(f"✓ {elapsed:.2f} saniyede tamamlandı")
        self._cleanup()
        self._update_btns()
        self._show_converted_preview(out_path, auto_play=False)

    def _show_converted_preview(self, path, auto_play=False):
        if not path or not os.path.exists(path): return
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in IMAGE_EXT:
                self.preview_scroll.setVisible(False)
                self.preview_zoom.setVisible(True)
                self.preview_label.setVisible(True)
                if self._video_widget: self._video_widget.setVisible(False)
                self.preview_label.setText("Resim (Dönüştürülmüş)")
                pixmap = generate_image_preview(path, max_size=400)
                if pixmap: self.preview_zoom.setPixmap(pixmap)
            elif ext in PDF_EXT:
                self.preview_scroll.setVisible(False)
                self.preview_zoom.setVisible(True)
                self.preview_label.setVisible(True)
                if self._video_widget: self._video_widget.setVisible(False)
                self.preview_label.setText("PDF (Dönüştürülmüş)")
                pixmap = generate_pdf_preview(path, max_size=400)
                if pixmap: self.preview_zoom.setPixmap(pixmap)
            elif ext == '.txt':
                self.preview_zoom.setVisible(False)
                self.preview_scroll.setVisible(True)
                self.preview_label.setVisible(True)
                if self._video_widget: self._video_widget.setVisible(False)
                self.preview_label.setText("TXT Önizleme")
                txt_content = generate_txt_preview(path, max_lines=15)
                self.preview_image.setText(txt_content if txt_content else "Hata")
            elif ext in VIDEO_EXT:
                self.preview_zoom.setVisible(False)
                self.preview_scroll.setVisible(False)
                self.preview_label.setVisible(True)
                if self._video_widget: self._video_widget.setVisible(True)
                self.preview_label.setText("Video (Dönüştürülmüş)")
                if HAS_MEDIA and self._video_widget and self._media_player:
                    url = QUrl.fromLocalFile(path)
                    if self._media_player.media().canonicalUrl() != url:
                        self._media_player.setMedia(QMediaContent(url))
                    self._media_player.pause()
                if auto_play: self._start_video_preview_playback(path)
            elif ext in AUDIO_EXT:
                self.preview_zoom.setVisible(False)
                self.preview_scroll.setVisible(True)
                self.preview_label.setVisible(True)
                if self._video_widget: self._video_widget.setVisible(False)
                self.preview_label.setText("Ses (Dönüştürülmüş)")
                self.preview_image.setText("\nSes dönüştürüldü\nPlay butonuna basın.")
                if auto_play: self._start_ffplay(path)
        except Exception as e: print(f"[Kavram] Gösterim hatası: {e}")

    def _on_error(self, msg):
        self._out_path = None
        self.lbl_status.setText("✗ Başarısız.")
        QMessageBox.critical(self, "Hata", f"Bir hata oluştu:\n\n{msg}")
        self._cleanup()
        self._update_btns()

    def _cleanup(self):
        self.progress.setVisible(False)
        if self.conv_thread and self.conv_thread.isRunning():
            self.conv_thread.quit()
            if not self.conv_thread.wait(5000):
                self.conv_thread.terminate()
                self.conv_thread.wait(2000)
        self.conv_thread = None
        self.conv_worker = None

    def _export(self):
        src = self._out_path
        if not src or not os.path.exists(src):
            QMessageBox.warning(self, "Uyarı", "Önce 'Convert' butonuna basın."); return

        ext = self.c_fmt.currentText()
        orig_base    = os.path.splitext(os.path.basename(self.file_path))[0]
        suggest_name = f"_{self._session_num}_{orig_base}{ext}"
        default = os.path.join(EXPORT_DIR if os.path.exists(EXPORT_DIR) else os.path.expanduser('~'), suggest_name)

        dst, _ = QFileDialog.getSaveFileName(self, "Dosyayı Kaydet", default, f"Dosyalar (*{ext})")
        if not dst: return
        if not dst.lower().endswith(ext.lower()): dst += ext

        try:
            if os.path.exists(dst) and os.path.samefile(src, dst):
                self.lbl_status.setText("Dosya zaten bu konumda.")
                QMessageBox.information(self, "Bilgi", "Kaynak ve hedef aynı dosya.")
                return
        except: pass

        success = False
        if _cpp:
            ret = _cpp.kavram_file_copy(src.encode(), dst.encode())
            if ret == 0: success = True
            else: QMessageBox.critical(self, "Hata", f"Kayıt başarısız:\n{_cpp.kavram_last_error().decode()}")
        else:
            try:
                shutil.copy2(src, dst)
                success = True
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Kayıt başarısız:\n{e}")

        if success:
            self.lbl_status.setText("Başarıyla kaydedildi.")
            QMessageBox.information(self, "Başarılı", f"Dosya kaydedildi:\n{dst}")
            self._clean_convert_dir()

    def _clean_convert_dir(self):
        if os.path.exists(CONVERT_DIR):
            for f in os.listdir(CONVERT_DIR):
                fpath = os.path.join(CONVERT_DIR, f)
                try:
                    if os.path.isfile(fpath): os.unlink(fpath)
                except: pass
        self._cached_preview_path = None
        self._cached_preview_settings = None

    def _get_settings(self):
        try: nf = int(self.e_freq.text())
        except: nf = 0
        return {
            'speed':       float(self.c_speed.currentText().replace('x', '')),
            'pitch':       float(self._pitch_vals[self.c_pitch.currentIndex()]),
            'effect':      self.c_effect.currentIndex(),
            'change_freq': self.c_freq_on.currentIndex() == 1,
            'new_freq':    nf,
            'pdf_invert':  self.c_pdf_inv.currentIndex()  == 1,
            'pdf_gray':    self.c_pdf_gray.currentIndex() == 1,
            'img_invert':  self.c_img_inv.currentIndex()  == 1,
            'img_gray':    self.c_img_gray.currentIndex() == 1,
            'img_scale':   self.c_img_scale.currentIndex(),
            'vid_invert':  self.c_vid_inv.currentIndex()  == 1,
            'vid_gray':    self.c_vid_gray.currentIndex() == 1,
            'vid_rm_aud':  self.c_vid_rm_aud.currentIndex() == 1,
            'vid_audio_path': self.vid_audio_path
        }

    def _update_btns(self, converting=False):
        self.btn_file.setEnabled(not converting)
        self.btn_convert.setEnabled(bool(self.file_path) and not converting)
        self.btn_reset.setEnabled(not converting)
        self.btn_export.setEnabled(bool(self._out_path) and os.path.exists(self._out_path or '') and not converting)
        ext = os.path.splitext(self.file_path)[1].lower() if self.file_path else ''
        self.btn_play_preview.setEnabled((ext in AUDIO_EXT or ext in VIDEO_EXT) and not converting and bool(self.file_path))

    def _reset(self):
        self.c_fmt.setCurrentIndex(0)
        self.c_freq_on.setCurrentIndex(0)
        self.e_freq.clear()
        self.c_speed.setCurrentText('1.00x')
        self.c_pitch.setCurrentIndex(6)
        self.c_effect.setCurrentIndex(0)
        self.c_pdf_inv.setCurrentIndex(0)
        self.c_pdf_gray.setCurrentIndex(0)
        self.c_img_inv.setCurrentIndex(0)
        self.c_img_gray.setCurrentIndex(0)
        self.c_img_scale.setCurrentIndex(5)
        self.c_vid_inv.setCurrentIndex(0)
        self.c_vid_gray.setCurrentIndex(0)
        self.c_vid_rm_aud.setCurrentIndex(0)
        
        self.cover_image_path = None
        self.vid_audio_path   = None
        self.lbl_cover.setVisible(False)
        self.lbl_vid_aud.setVisible(False)
        
        self._on_fmt_changed()
        self._stop_playback()
        self._invalidate_preview_cache()

    def _btn_css(self):
        return """
            QPushButton{background-color:transparent;color:#E0E0E0;
                border:2px solid #555;border-radius:8px;
                padding:5px 10px;font-weight:bold;}
            QPushButton:hover{background-color:#3C3C3C;border:1px solid #777;}
            QPushButton:pressed{background-color:#1A1A1A;padding:6px 10px 4px 10px;}
            QPushButton:disabled{background-color:#202020;color:#555;border:1px solid #333;}"""

    def closeEvent(self, event):
        self._stop_playback()
        if self.conv_worker: self.conv_worker.stop()
        if self.conv_thread and self.conv_thread.isRunning():
            self.conv_thread.quit()
            if not self.conv_thread.wait(5000):
                self.conv_thread.terminate()
                self.conv_thread.wait(2000)

        if self.preview_worker: self.preview_worker.stop()
        if self.preview_thread and self.preview_thread.isRunning():
            self.preview_thread.quit()
            self.preview_thread.wait(2000)

        if self._video_preview_process:
            try:
                self._video_preview_process.terminate()
                self._video_preview_process.wait(timeout=1)
            except:
                try: self._video_preview_process.kill()
                except: pass

        self._clean_convert_dir()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = UniversalConverter()
    w.show()
    sys.exit(app.exec_())
