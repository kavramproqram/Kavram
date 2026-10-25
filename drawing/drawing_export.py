# Kavram - Animasyon dışa aktarma (MP4, WebM, MKV, GIF, APNG, PNG dizisi)
# Kareler ayrı bir iş parçacığında (QThread) üretilir; arayüz donmaz, iptal edilebilir.
from drawing_common import *
from drawing_layers import composite_page
from drawing_animation import expand_sequence

# ---- Kavram File / Export penceresi (file_manager) -------------------------------
# Kavram çekirdeğinden çalışırken "kavram_file_manager" adıyla yüklenir; program tek başına
# çalıştırılırsa kardeş klasördeki file_manager/file_manager.py doğrudan yüklenir.  Hiçbiri
# olmazsa Qt'nin kendi diyaloğuna dönülür (program asla dosya seçemeden kalmaz).
try:
    import kavram_file_manager as _fm
except Exception:
    try:
        import importlib.util as _ilu
        import os as _fm_os
        import sys as _fm_sys
        _fm_yol = _fm_os.path.join(_fm_os.path.dirname(_fm_os.path.abspath(__file__)), "..", "file_manager", "file_manager.py")
        _fm_spec = _ilu.spec_from_file_location("kavram_file_manager", _fm_yol)
        _fm = _ilu.module_from_spec(_fm_spec)
        _fm_sys.modules["kavram_file_manager"] = _fm
        _fm_spec.loader.exec_module(_fm)
    except Exception:
        from PyQt5.QtWidgets import QFileDialog as _QFD

        class _fm:  # yedek: Qt diyaloğu
            ALL_FILES_LABEL = "Bütün Dosyalar (*)"

            @staticmethod
            def get_open_file_name(parent=None, caption="", directory="", filter="", initialFilter="",
                                   options=None, **_kw):
                return _QFD.getOpenFileName(parent, caption, directory, filter)

            @staticmethod
            def get_open_file_names(parent=None, caption="", directory="", filter="", initialFilter="",
                                    options=None, **_kw):
                return _QFD.getOpenFileNames(parent, caption, directory, filter)

            @staticmethod
            def get_save_file_name(parent=None, caption="", directory="", filter="", initialFilter="",
                                   options=None, **_kw):
                return _QFD.getSaveFileName(parent, caption, directory, filter)

            @staticmethod
            def get_existing_directory(parent=None, caption="", directory="", options=None, **_kw):
                return _QFD.getExistingDirectory(parent, caption, directory)

            @staticmethod
            def notify_saved(parent=None, text="Dosya kaydedildi.", msec=400):
                print(text)
# -----------------------------------------------------------------------------------


# anahtar, etiket, uzantı, saydamlık desteği
EXPORT_FORMATS = [
    ("mp4", "MP4 (H.264)", ".mp4", False),
    ("webm", "WebM (VP9, saydamlık destekli)", ".webm", True),
    ("mkv", "MKV (H.264)", ".mkv", False),
    ("gif", "GIF (animasyonlu)", ".gif", True),
    ("apng", "APNG (animasyonlu PNG)", ".png", True),
    ("png_seq", "PNG dizisi (klasöre tüm kareler)", "", True),
]
_FMT = {k: (label, ext, alpha) for k, label, ext, alpha in EXPORT_FORMATS}


class ExportCancelled(Exception):
    pass


class ExportWorker(QThread):
    progress = pyqtSignal(int, str)
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, params, parent=None):
        super().__init__(parent)
        self.p = params
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def _check(self):
        if self._cancel:
            raise ExportCancelled()

    def run(self):
        p = self.p
        tmp = None
        try:
            fmt = p["fmt"]
            transparent = p["transparent"] and _FMT[fmt][2]
            tmp = tempfile.mkdtemp(prefix="kavram_export_")
            if fmt == "png_seq":
                frame_dir = p["out_path"]
                os.makedirs(frame_dir, exist_ok=True)
                name_fmt = "kare_%05d.png"
            else:
                frame_dir = tmp
                name_fmt = "frame_%05d.png"

            jobs = p["jobs"]                       # [(sayfa_idx, (r,g,b,a), hold)]
            total = max(1, sum(h for _i, _bg, h in jobs))
            scale = p["scale"] / 100.0
            out_w = max(2, int(round(p["w"] * scale)))
            out_h = max(2, int(round(p["h"] * scale)))

            frame_no = 1
            for k, (idx, bg, hold) in enumerate(jobs):
                self._check()
                bgc = None if transparent else QColor(*bg)
                img = composite_page(p["cache_dir"], idx, p["meta"], p["w"], p["h"], bgc)
                if (out_w, out_h) != (p["w"], p["h"]):
                    img = img.scaled(out_w, out_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                if not transparent:
                    img = img.convertToFormat(QImage.Format_RGB32)
                first = os.path.join(frame_dir, name_fmt % frame_no)
                if not img.save(first, "PNG"):
                    raise IOError(f"Kare yazılamadı: {first}")
                for r in range(1, hold):          # kare süresi: aynı kareyi kopyala
                    shutil.copyfile(first, os.path.join(frame_dir, name_fmt % (frame_no + r)))
                frame_no += hold
                pct = int(5 + 80 * (frame_no - 1) / total) if fmt != "png_seq" else int(100 * (frame_no - 1) / total)
                self.progress.emit(min(pct, 99), f"Kare {k + 1}/{len(jobs)} hazırlanıyor…")

            if fmt == "png_seq":
                self.done.emit(frame_dir)
                return

            self._check()
            self.progress.emit(88, "Video kodlanıyor…")
            self._encode(fmt, transparent, tmp, p)
            self.progress.emit(100, "Tamamlandı")
            self.done.emit(p["out_path"])
        except ExportCancelled:
            try:
                if p["fmt"] != "png_seq" and os.path.exists(p["out_path"]):
                    os.remove(p["out_path"])
            except OSError:
                pass
            self.failed.emit("")           # boş mesaj = kullanıcı iptal etti
        except Exception as e:
            self.failed.emit(str(e))
        finally:
            if tmp:
                shutil.rmtree(tmp, ignore_errors=True)

    def _encode(self, fmt, transparent, tmp, p):
        ff = p["ffmpeg"]
        out = p["out_path"]
        inp = os.path.join(tmp, "frame_%05d.png")
        base = [ff, "-y", "-framerate", str(p["fps"]), "-i", inp]
        if fmt in ("mp4", "mkv"):
            cmd = base + ["-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "18", "-pix_fmt", "yuv420p"]
            if fmt == "mp4":
                cmd += ["-movflags", "+faststart"]
            cmd += [out]
        elif fmt == "webm":
            pix = "yuva420p" if transparent else "yuv420p"
            cmd = base + ["-c:v", "libvpx-vp9", "-pix_fmt", pix, "-b:v", "0", "-crf", "30"]
            if transparent:
                cmd += ["-auto-alt-ref", "0"]
            cmd += [out]
        elif fmt == "gif":
            flt = ("split[s0][s1];[s0]palettegen=reserve_transparent=%d[pal];"
                   "[s1][pal]paletteuse=alpha_threshold=128") % (1 if transparent else 0)
            cmd = base + ["-filter_complex", flt, "-loop", "0", out]
        elif fmt == "apng":
            cmd = base + ["-plays", "0", "-pix_fmt", "rgba", "-f", "apng", out]
        else:
            raise ValueError("Bilinmeyen format: " + fmt)

        log_path = os.path.join(tmp, "ffmpeg.log")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        with open(log_path, "w", encoding="utf-8", errors="replace") as log:
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=log, creationflags=flags)
            while proc.poll() is None:
                if self._cancel:
                    proc.kill()
                    proc.wait()
                    raise ExportCancelled()
                time.sleep(0.05)
        if proc.returncode != 0:
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    tail = "".join(f.readlines()[-8:])
            except OSError:
                tail = ""
            raise RuntimeError(f"ffmpeg hata kodu {proc.returncode}\n{tail}")


class ExportDialog(QDialog):
    def __init__(self, win, fps, preset=None):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Animasyonu Dışa Aktar")
        self.setMinimumWidth(460)
        self.setStyleSheet("""
            QDialog { background-color: #2b2b2b; }
            QLabel, QCheckBox { color: #eee; }
            QLineEdit, QSpinBox, QComboBox { background-color: #3a3a3a; color: #eee; border: 1px solid #555;
                                              border-radius: 5px; padding: 3px 6px; }
            QComboBox QAbstractItemView { background-color: #3a3a3a; color: #eee; }
            QPushButton { background-color: #3a3a3a; color: #eee; border: 1px solid #666; border-radius: 6px; padding: 5px 14px; }
            QPushButton:hover { background-color: #4a4a4a; }
        """)
        lay = QVBoxLayout(self)
        form_rows = []

        self.fmt = QComboBox()
        for key, label, _ext, _alpha in EXPORT_FORMATS:
            self.fmt.addItem(label, key)
        if preset:
            i = self.fmt.findData(preset)
            if i >= 0:
                self.fmt.setCurrentIndex(i)
        self.fmt.currentIndexChanged.connect(self._on_format)

        self.fps = QSpinBox()
        self.fps.setRange(1, 120)
        self.fps.setValue(fps)

        self.scale = QSpinBox()
        self.scale.setRange(10, 400)
        self.scale.setValue(100)
        self.scale.setSuffix(" %")

        self.transparent = QCheckBox("Saydam arka plan (arka plan rengi olmadan)")

        self.path = QLineEdit()
        browse = QPushButton("Gözat…")
        browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path, 1)
        path_row.addWidget(browse)

        n_frames = sum(max(1, int(pg.get("hold", 1))) for pg in win.pages_data)
        self.info = QLabel()
        self.info.setStyleSheet("color: #aaa;")

        for text, widget in (("Biçim", self.fmt), ("Kare hızı (FPS)", self.fps), ("Ölçek", self.scale)):
            row = QHBoxLayout()
            lbl = QLabel(text)
            lbl.setMinimumWidth(110)
            row.addWidget(lbl)
            row.addWidget(widget, 1)
            lay.addLayout(row)
        lay.addWidget(self.transparent)
        lay.addWidget(QLabel("Kayıt yeri"))
        lay.addLayout(path_row)
        lay.addWidget(self.info)

        btns = QHBoxLayout()
        btns.addStretch(1)
        ok = QPushButton("Dışa Aktar")
        ok.setDefault(True)
        cancel = QPushButton("İptal")
        ok.clicked.connect(self._accept)
        cancel.clicked.connect(self.reject)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        lay.addLayout(btns)

        self._n_frames = n_frames
        self.fps.valueChanged.connect(self._update_info)
        self.scale.valueChanged.connect(self._update_info)
        self._on_format()

    def _update_info(self):
        secs = self._n_frames / float(max(1, self.fps.value()))
        w = int(round(self.win.canvas_width * self.scale.value() / 100.0))
        h = int(round(self.win.canvas_height * self.scale.value() / 100.0))
        self.info.setText(f"{self._n_frames} kare  •  {secs:.1f} sn  •  {w}×{h}")

    def _on_format(self):
        key = self.fmt.currentData()
        alpha = _FMT[key][2]
        self.transparent.setEnabled(alpha)
        if not alpha:
            self.transparent.setChecked(False)
        # uzantıyı yeni biçime uydur
        cur = self.path.text().strip()
        if cur and key != "png_seq":
            root, _ = os.path.splitext(cur)
            self.path.setText(root + _FMT[key][1])
        self._update_info()

    def _default_dir(self):
        p = getattr(self.win, "current_file_path", None)
        if p:
            return os.path.dirname(p)
        return self.win.DEFAULT_BASE_DIR

    def _browse(self):
        key = self.fmt.currentData()
        if key == "png_seq":
            d = _fm.get_existing_directory(self, "Kare klasörünü seç", self._default_dir(), editor="Drawing")
            if d:
                self.path.setText(d)
        else:
            ext = _FMT[key][1]
            f, _ = _fm.get_save_file_name(self, "Dışa aktar", os.path.join(self._default_dir(), "animasyon" + ext),
                                               f"{_FMT[key][0]} (*{ext})", editor="Drawing")
            if f:
                if not f.lower().endswith(ext):
                    f += ext
                self.path.setText(f)

    def _accept(self):
        if not self.path.text().strip():
            self._browse()
            if not self.path.text().strip():
                return
        self.accept()

    def options(self):
        key = self.fmt.currentData()
        out = self.path.text().strip()
        if key != "png_seq" and not out.lower().endswith(_FMT[key][1]):
            out += _FMT[key][1]
        return {"fmt": key, "fps": self.fps.value(), "scale": self.scale.value(),
                "transparent": self.transparent.isChecked(), "out_path": out}


def start_export(win, preset=None):
    """Dışa aktarma penceresini açar ve işi arka planda başlatır."""
    old = getattr(win, "_export_worker", None)
    if old is not None and old.isRunning():
        QMessageBox.information(win, "Dışa Aktarma", "Önceki dışa aktarma hâlâ sürüyor.")
        return
    win.flushCurrentPageToCache()
    dlg = ExportDialog(win, win.current_export_fps, preset)
    if dlg.exec_() != QDialog.Accepted:
        return
    o = dlg.options()
    if o["fmt"] != "png_seq" and not ffmpeg_available():
        QMessageBox.critical(win, "Hata",
                             f"Bu biçim için ffmpeg gerekli, bulunamadı:\n{FFMPEG_PATH}\n\n"
                             "Uygulama dizinine 'bin/ffmpeg' koyun veya ffmpeg'i sisteme kurun.\n"
                             "PNG dizisi biçimi ffmpeg gerektirmez.")
        return
    win.current_export_fps = o["fps"]
    QSettings("kavram", "DrawingEditor").setValue("exportFPS", o["fps"])

    st = win.drawing_area.layer_stack
    jobs = []
    for i, pg in enumerate(win.pages_data):
        c = QColor(pg.get("background", win.background_color))
        jobs.append((i, (c.red(), c.green(), c.blue(), c.alpha()), max(1, int(pg.get("hold", 1)))))
    params = {"cache_dir": win.drawing_cache_dir, "meta": st.export_meta(), "w": st.w, "h": st.h,
              "jobs": jobs, "ffmpeg": FFMPEG_PATH, **o}

    worker = ExportWorker(params)
    prog = QProgressDialog("Hazırlanıyor…", "İptal", 0, 100, win)
    prog.setWindowTitle("Dışa Aktarılıyor")
    prog.setWindowModality(Qt.WindowModal)
    prog.setMinimumDuration(0)
    prog.setAutoClose(False)
    prog.setAutoReset(False)
    prog.setValue(0)

    def on_progress(v, msg):
        prog.setValue(v)
        prog.setLabelText(msg)

    def close_prog():
        try:
            prog.canceled.disconnect()
        except TypeError:
            pass
        prog.close()

    def on_done(path):
        close_prog()
        win._export_worker = None
        _fm.notify_saved(win)

    def on_failed(msg):
        close_prog()
        win._export_worker = None
        if msg:
            QMessageBox.critical(win, "Hata", f"Dışa aktarma başarısız:\n{msg}")

    worker.progress.connect(on_progress)
    worker.done.connect(on_done)
    worker.failed.connect(on_failed)
    prog.canceled.connect(worker.cancel)
    win._export_worker = worker
    worker.start()
