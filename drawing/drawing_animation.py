# Kavram - Animasyon: soğan zarı (onion skin), oynatma, kare süresi (hold), zaman çizelgesi
from collections import OrderedDict

from drawing_common import *
from drawing_layers import (composite_page, page_signature, meta_signature)


def expand_sequence(pages_data):
    """Kare sürelerini (hold) açar: [0, 0, 1, 2, 2, 2] gibi sayfa indeks dizisi döner."""
    seq = []
    for i, page in enumerate(pages_data):
        seq.extend([i] * max(1, int(page.get("hold", 1))))
    return seq


# ---------------------------------------------------------------------------
# Denetleyici: soğan zarı + oynatma
# ---------------------------------------------------------------------------
class AnimationController(QObject):
    onionChanged = pyqtSignal()
    playStateChanged = pyqtSignal(bool)
    playheadMoved = pyqtSignal(int)       # oynatma sırasında gösterilen sayfa indeksi

    ONION_OPACITY = [0.38, 0.22, 0.12]
    PREV_TINT = QColor(255, 80, 80)
    NEXT_TINT = QColor(70, 170, 255)
    PREFETCH = 10
    CACHE_MAX = 48

    def __init__(self, window):
        super().__init__(window)
        self.win = window
        s = QSettings("kavram", "DrawingEditor")
        self.onion_enabled = s.value("onionEnabled", True, type=bool)
        self.onion_before = s.value("onionBefore", 1, type=int)
        self.onion_after = s.value("onionAfter", 0, type=int)
        self.loop = s.value("loopPlayback", True, type=bool)

        self.is_playing = False
        self._onion_dirty = True
        self._onion_list = []
        self._tint_cache = {}

        # oynatma
        self._seq = []
        self._shown_page = -1
        self._start_page = 0
        self._frames = OrderedDict()
        self._lock = threading.Lock()
        self._prefetch_thread = None
        self._clock = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)
        self._timer.timeout.connect(self._tick)

        area = window.drawing_area
        area.onion_provider = self.onion_frames
        area.layersChanged.connect(self.invalidate_onion)

    # -------------------------------------------------- ayarlar
    def _save(self):
        s = QSettings("kavram", "DrawingEditor")
        s.setValue("onionEnabled", self.onion_enabled)
        s.setValue("onionBefore", self.onion_before)
        s.setValue("onionAfter", self.onion_after)
        s.setValue("loopPlayback", self.loop)

    def set_onion_enabled(self, v):
        self.onion_enabled = bool(v)
        self._save()
        self._refresh_onion()

    def set_onion_range(self, before=None, after=None):
        if before is not None:
            self.onion_before = max(0, min(3, int(before)))
        if after is not None:
            self.onion_after = max(0, min(3, int(after)))
        self._save()
        self._refresh_onion()

    def set_loop(self, v):
        self.loop = bool(v)
        self._save()

    def toggle_onion(self):
        self.set_onion_enabled(not self.onion_enabled)

    # -------------------------------------------------- soğan zarı
    def invalidate_onion(self):
        self._onion_dirty = True
        self._tint_cache.clear()

    def _refresh_onion(self):
        self.invalidate_onion()
        self.win.drawing_area.update()
        self.onionChanged.emit()

    def on_page_changed(self):
        self._onion_dirty = True
        self.win.drawing_area.update()

    def onion_frames(self):
        if not self.onion_enabled or self.is_playing:
            return []
        if self._onion_dirty:
            self._rebuild_onion()
        return self._onion_list

    def _rebuild_onion(self):
        self._onion_dirty = False
        self._onion_list = []
        w = self.win
        cur = w.current_page_index
        n = len(w.pages_data)
        jobs = [(cur - d, self.PREV_TINT, d) for d in range(1, self.onion_before + 1)]
        jobs += [(cur + d, self.NEXT_TINT, d) for d in range(1, self.onion_after + 1)]
        for idx, tint, dist in jobs:
            if 0 <= idx < n:
                img = self._tinted(idx, tint)
                if img is not None:
                    op = self.ONION_OPACITY[min(dist, len(self.ONION_OPACITY)) - 1]
                    self._onion_list.append((img, op))

    def _tinted(self, idx, tint):
        w = self.win
        st = w.drawing_area.layer_stack
        meta = st.export_meta()
        key = (idx, tint.rgb())
        sig = page_signature(w.drawing_cache_dir, idx, meta)
        cached = self._tint_cache.get(key)
        if cached and cached[0] == sig:
            return cached[1]
        img = composite_page(w.drawing_cache_dir, idx, meta, st.w, st.h, None)
        p = QPainter(img)
        p.setCompositionMode(QPainter.CompositionMode_SourceIn)
        p.fillRect(img.rect(), tint)
        p.end()
        self._tint_cache[key] = (sig, img)
        return img

    # -------------------------------------------------- kare süresi
    def get_hold(self, idx):
        if 0 <= idx < len(self.win.pages_data):
            return max(1, int(self.win.pages_data[idx].get("hold", 1)))
        return 1

    def set_hold(self, idx, n):
        if 0 <= idx < len(self.win.pages_data):
            self.win.pages_data[idx]["hold"] = max(1, min(120, int(n)))
            self.win.is_project_modified = True

    # -------------------------------------------------- oynatma
    @property
    def fps(self):
        return max(1, int(self.win.current_export_fps))

    def toggle_play(self):
        if self.is_playing:
            self.stop()
        else:
            self.start()

    def start(self):
        if self.is_playing or len(self.win.pages_data) == 0:
            return
        w = self.win
        w.flushCurrentPageToCache()
        self._seq = expand_sequence(w.pages_data)
        if not self._seq:
            return
        self._start_page = w.current_page_index
        self._shown_page = -1
        with self._lock:
            self._frames.clear()
        area = w.drawing_area
        area.playback_stop_cb = self.stop
        # editör araçlarının oynatma sırasında kullanılmaması için metin kutusunu kapat
        try:
            area.text_input_widget.hide()
        except Exception:
            pass
        self.is_playing = True
        self._clock.start()
        self._timer.start(12)
        self.playStateChanged.emit(True)
        self._tick()

    def stop(self):
        if not self.is_playing:
            return
        self._timer.stop()
        self.is_playing = False
        area = self.win.drawing_area
        area.playback_frame = None
        area.playback_stop_cb = None
        with self._lock:
            self._frames.clear()
        self._onion_dirty = True
        area.update()
        self.playStateChanged.emit(False)
        self.playheadMoved.emit(self.win.current_page_index)

    def _page_frame(self, page):
        with self._lock:
            img = self._frames.get(page)
            if img is not None:
                self._frames.move_to_end(page)
                return img
        img = self._render_frame(page)
        self._store(page, img)
        return img

    def _render_frame(self, page):
        w = self.win
        st = w.drawing_area.layer_stack
        bg = QColor(w.pages_data[page].get("background", w.background_color))
        return composite_page(w.drawing_cache_dir, page, st.export_meta(), st.w, st.h, bg)

    def _store(self, page, img):
        with self._lock:
            self._frames[page] = img
            self._frames.move_to_end(page)
            while len(self._frames) > self.CACHE_MAX:
                self._frames.popitem(last=False)

    def _tick(self):
        if not self.is_playing:
            return
        seq = self._seq
        pos = int(self._clock.elapsed() * self.fps / 1000.0)
        if pos >= len(seq):
            if not self.loop:
                self.stop()
                return
            pos %= len(seq)
        page = seq[pos]
        if page != self._shown_page:
            self._shown_page = page
            area = self.win.drawing_area
            area.playback_frame = self._page_frame(page)
            area.update()
            self.playheadMoved.emit(page)
        self._kick_prefetch(pos)

    def _kick_prefetch(self, pos):
        if self._prefetch_thread is not None and self._prefetch_thread.is_alive():
            return
        seq = self._seq
        upcoming = []
        for k in range(pos + 1, pos + 1 + self.PREFETCH * 4):
            page = seq[k % len(seq)] if (self.loop or k < len(seq)) else None
            if page is None:
                break
            if page not in upcoming:
                upcoming.append(page)
            if len(upcoming) >= self.PREFETCH:
                break
        with self._lock:
            missing = [p for p in upcoming if p not in self._frames]
        if not missing:
            return
        # QColor/pages_data okuması ana iş parçacığında yapılır; iş parçacığı yalnız QImage ile çalışır
        w = self.win
        st = w.drawing_area.layer_stack
        meta = st.export_meta()
        jobs = [(p, QColor(w.pages_data[p].get("background", w.background_color))) for p in missing]
        cache_dir, cw, ch = w.drawing_cache_dir, st.w, st.h

        def work():
            for p, bg in jobs:
                if not self.is_playing:
                    return
                img = composite_page(cache_dir, p, meta, cw, ch, bg)
                self._store(p, img)

        self._prefetch_thread = threading.Thread(target=work, daemon=True)
        self._prefetch_thread.start()


# ---------------------------------------------------------------------------
# Zaman çizelgesi paneli
# ---------------------------------------------------------------------------
_TL_CSS = """
QFrame#timelinePanel { background-color: #262626; border-top: 2px solid #555; }
QLabel { color: #ddd; background: transparent; }
QCheckBox { color: #ddd; spacing: 4px; }
QSpinBox { background-color: #333; color: #eee; border: 1px solid #555; border-radius: 5px; padding: 1px 3px; }
QPushButton, QToolButton { background-color: #333; color: #eee; border: 1px solid #555; border-radius: 6px; padding: 2px 8px; }
QPushButton:hover, QToolButton:hover { background-color: #444; }
QPushButton:checked, QToolButton:checked { background-color: #4a5f8a; border-color: #7f97c9; }
QListWidget { background-color: #1b1b1b; border: 1px solid #444; border-radius: 6px; outline: none; }
QListWidget::item { border: 2px solid transparent; border-radius: 4px; margin: 1px; }
QListWidget::item:selected { border: 2px solid #6fa8ff; background-color: #2b3550; }
"""


class TimelinePanel(QFrame):
    def __init__(self, window, controller):
        super().__init__(window)
        self.setObjectName("timelinePanel")
        self.win = window
        self.ctrl = controller
        self._block = False
        self.show_thumbs = QSettings("kavram", "DrawingEditor").value("timelineThumbs", True, type=bool)
        self._thumbs = {}            # sayfa -> (imza, QPixmap)
        self._pending = []
        self._refresh_pending = False
        self.setStyleSheet(_TL_CSS)
        self.setFixedHeight(118 if self.show_thumbs else 90)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 6)
        root.setSpacing(4)

        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.play_btn = QToolButton()
        self.play_btn.setIcon(create_svg_icon(SVG_PLAY, 18))
        self.play_btn.setToolTip("Oynat / Durdur (Ctrl+Boşluk)")
        self.play_btn.clicked.connect(self.ctrl.toggle_play)
        bar.addWidget(self.play_btn)

        self.loop_chk = QCheckBox("Döngü")
        self.loop_chk.setChecked(self.ctrl.loop)
        self.loop_chk.toggled.connect(self.ctrl.set_loop)
        bar.addWidget(self.loop_chk)

        bar.addWidget(QLabel("FPS"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(self.win.current_export_fps)
        self.fps_spin.valueChanged.connect(self._on_fps)
        bar.addWidget(self.fps_spin)

        bar.addSpacing(10)
        self.onion_btn = QToolButton()
        self.onion_btn.setCheckable(True)
        self.onion_btn.setChecked(self.ctrl.onion_enabled)
        self.onion_btn.setIcon(create_svg_icon(SVG_ONION, 18))
        self.onion_btn.setToolTip("Soğan zarı: önceki/sonraki kareleri soluk göster (Ctrl+Shift+O)")
        self.onion_btn.toggled.connect(self.ctrl.set_onion_enabled)
        bar.addWidget(self.onion_btn)
        bar.addWidget(QLabel("Önce"))
        self.before_spin = QSpinBox()
        self.before_spin.setRange(0, 3)
        self.before_spin.setValue(self.ctrl.onion_before)
        self.before_spin.valueChanged.connect(lambda v: self.ctrl.set_onion_range(before=v))
        bar.addWidget(self.before_spin)
        bar.addWidget(QLabel("Sonra"))
        self.after_spin = QSpinBox()
        self.after_spin.setRange(0, 3)
        self.after_spin.setValue(self.ctrl.onion_after)
        self.after_spin.valueChanged.connect(lambda v: self.ctrl.set_onion_range(after=v))
        bar.addWidget(self.after_spin)

        bar.addSpacing(10)
        self.thumb_btn = SvgIconButton(SVG_EYE_OPEN if self.show_thumbs else SVG_EYE_CLOSED,
                                       "#eeeeee" if self.show_thumbs else "#888888", size=28, icon_px=19)
        self.thumb_btn.setToolTip("Kare küçük resimlerini göster / gizle\n(Gizliyken karelerde yalnız numara görünür, sistem daha az yorulur)")
        self.thumb_btn.clicked.connect(lambda: self._set_thumbs(not self.show_thumbs))
        bar.addWidget(self.thumb_btn)
        bar.addWidget(QLabel("Küçük resim"))

        bar.addSpacing(10)
        bar.addWidget(QLabel("Kare süresi"))
        self.hold_spin = QSpinBox()
        self.hold_spin.setRange(1, 120)
        self.hold_spin.setSuffix(" kare")
        self.hold_spin.setToolTip("Seçili karenin kaç kare boyunca tutulacağı")
        self.hold_spin.valueChanged.connect(self._on_hold)
        bar.addWidget(self.hold_spin)

        bar.addStretch(1)
        for text, tip, fn in (("+ Boş", "Sonrasına boş kare ekle", self.win.insertBlankPageAfter),
                              ("Çoğalt", "Kareyi sonrasına çoğalt", self.win.duplicateToNextPage),
                              ("Sil", "Kareyi sil", self.win.removePage)):
            b = QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(fn)
            bar.addWidget(b)
        root.addLayout(bar)

        self.list = QListWidget()
        self.list.setViewMode(QListWidget.ListMode)
        self.list.setFlow(QListWidget.LeftToRight)
        self.list.setWrapping(False)
        self.list.setSpacing(3)
        self.list.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context_menu)
        self.list.currentRowChanged.connect(self._on_row)
        self.list.model().rowsMoved.connect(self._rows_moved)
        root.addWidget(self.list, 1)

        self.ctrl.playStateChanged.connect(self._on_play_state)
        self.ctrl.playheadMoved.connect(self._on_playhead)
        area = self.win.drawing_area
        area.contentChanged.connect(self._content_changed)

        self._content_timer = QTimer(self)
        self._content_timer.setSingleShot(True)
        self._content_timer.timeout.connect(self._refresh_current_thumb)

        self._fill_timer = QTimer(self)
        self._fill_timer.setSingleShot(True)
        self._fill_timer.timeout.connect(self._fill_next)

        self.refresh()

    # ------------------------------------------------------------ boyutlar
    def _thumb_size(self):
        if not self.show_thumbs:
            return 46, 30
        cw, ch = max(1, self.win.canvas_width), max(1, self.win.canvas_height)
        th = 58
        tw = max(40, min(140, int(round(th * cw / float(ch)))))
        return tw, th

    def _scroll_to_current(self):
        item = self.list.currentItem()
        if item is not None:
            self.list.scrollToItem(item)

    # ------------------------------------------------------------ yenileme
    def schedule_refresh(self):
        if self._refresh_pending:
            return
        self._refresh_pending = True
        QTimer.singleShot(0, self._do_refresh)

    def _do_refresh(self):
        self._refresh_pending = False
        self.refresh()

    def refresh(self):
        w = self.win
        tw, th = self._thumb_size()
        self._block = True
        try:
            self.list.clear()
            self.list.setIconSize(QSize(tw, th))
            blank = QPixmap(tw, th)
            blank.fill(QColor("#222"))
            for i in range(len(w.pages_data)):
                item = QListWidgetItem(QIcon(blank), "")
                item.setSizeHint(QSize(tw + 8, th + 8))
                item.setToolTip(f"Kare {i + 1}")
                self.list.addItem(item)
            self.list.setCurrentRow(min(w.current_page_index, self.list.count() - 1))
            self._scroll_to_current()
        finally:
            self._block = False
        self._sync_hold()
        self._queue_all()

    def sync_current(self):
        """Sayfa değiştiğinde seçimi günceller (sayfayı yeniden yüklemeden)."""
        if self.list.count() != len(self.win.pages_data):
            self.schedule_refresh()
            return
        self._block = True
        try:
            self.list.setCurrentRow(self.win.current_page_index)
            self._scroll_to_current()
        finally:
            self._block = False
        self._sync_hold()
        self._queue_thumb(self.win.current_page_index, front=True)

    def _sync_hold(self):
        self.hold_spin.blockSignals(True)
        self.hold_spin.setValue(self.ctrl.get_hold(self.win.current_page_index))
        self.hold_spin.blockSignals(False)

    # ------------------------------------------------------------ küçük resimler
    def _signature(self, i):
        w = self.win
        st = w.drawing_area.layer_stack
        bg = QColor(w.background_color if i == w.current_page_index else w.pages_data[i].get("background", w.background_color))
        if i == w.current_page_index:
            return ("live", id(self), w.canvas_width, bg.rgba(), self.ctrl.get_hold(i), self._live_rev)
        return (page_signature(w.drawing_cache_dir, i, st.export_meta()), bg.rgba(), self.ctrl.get_hold(i),
                w.canvas_width, w.canvas_height)

    _live_rev = 0

    def _set_thumbs(self, value):
        self.show_thumbs = bool(value)
        QSettings("kavram", "DrawingEditor").setValue("timelineThumbs", self.show_thumbs)
        self.thumb_btn.setSvg(SVG_EYE_OPEN if self.show_thumbs else SVG_EYE_CLOSED,
                              "#eeeeee" if self.show_thumbs else "#888888")
        self.setFixedHeight(118 if self.show_thumbs else 90)
        self._thumbs.clear()
        self._pending = []
        self.refresh()

    def _number_tile(self, i):
        """Küçük resim kapalıyken: yalnız kare numarası (ucuz)."""
        tw, th = self._thumb_size()
        pm = QPixmap(tw, th)
        pm.fill(QColor("#2a303c"))
        p = QPainter(pm)
        f = QFont()
        f.setPixelSize(15)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRect(0, 0, tw, th), Qt.AlignCenter, str(i + 1))
        hold = self.ctrl.get_hold(i)
        if hold > 1:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 170, 40, 230))
            p.drawRoundedRect(QRect(tw - 22, th - 12, 21, 11), 3, 3)
            p.setPen(QColor("#111"))
            f2 = QFont()
            f2.setPixelSize(9)
            f2.setBold(True)
            p.setFont(f2)
            p.drawText(QRect(tw - 22, th - 12, 21, 11), Qt.AlignCenter, f"×{hold}")
        p.end()
        return pm

    def _set_tile(self, i):
        if 0 <= i < self.list.count():
            self.list.item(i).setIcon(QIcon(self._number_tile(i)))

    def _queue_all(self):
        if not self.show_thumbs:
            for i in range(self.list.count()):
                self._set_tile(i)
            return
        cur = self.win.current_page_index
        order = sorted(range(len(self.win.pages_data)), key=lambda i: abs(i - cur))
        self._pending = [i for i in order if self._thumb_stale(i)]
        for i in range(len(self.win.pages_data)):
            cached = self._thumbs.get(i)
            if cached is not None and i < self.list.count():
                self.list.item(i).setIcon(QIcon(cached[1]))
        self._schedule_fill()

    def _thumb_stale(self, i):
        cached = self._thumbs.get(i)
        return cached is None or cached[0] != self._signature(i)

    def _queue_thumb(self, i, front=False):
        if not self.show_thumbs:
            self._set_tile(i)
            return
        if i in self._pending:
            self._pending.remove(i)
        if front:
            self._pending.insert(0, i)
        else:
            self._pending.append(i)
        self._schedule_fill()

    def _schedule_fill(self):
        if self._pending and not self._fill_timer.isActive():
            self._fill_timer.start(5)

    def _fill_next(self):
        budget = 3
        while self._pending and budget > 0:
            i = self._pending.pop(0)
            if i >= self.list.count() or i >= len(self.win.pages_data):
                continue
            sig = self._signature(i)
            cached = self._thumbs.get(i)
            if cached is None or cached[0] != sig:
                pm = self._make_thumb(i)
                self._thumbs[i] = (sig, pm)
            else:
                pm = cached[1]
            self.list.item(i).setIcon(QIcon(pm))
            budget -= 1
        self._schedule_fill()

    def _make_thumb(self, i):
        w = self.win
        area = w.drawing_area
        st = area.layer_stack
        tw, th = self._thumb_size()
        if i == w.current_page_index:
            img = area.flattenCurrent(QColor(w.background_color))
        else:
            bg = QColor(w.pages_data[i].get("background", w.background_color))
            img = composite_page(w.drawing_cache_dir, i, st.export_meta(), st.w, st.h, bg)
        scaled = img.scaled(tw, th, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pm = QPixmap(tw, th)
        pm.fill(QColor("#111"))
        p = QPainter(pm)
        p.drawImage((tw - scaled.width()) // 2, (th - scaled.height()) // 2, scaled)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 170))
        p.drawRoundedRect(QRect(2, 2, 26, 15), 3, 3)
        p.setPen(QColor("#fff"))
        f = QFont()
        f.setPixelSize(10)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRect(2, 2, 26, 15), Qt.AlignCenter, str(i + 1))
        hold = self.ctrl.get_hold(i)
        if hold > 1:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 170, 40, 220))
            p.drawRoundedRect(QRect(tw - 30, th - 17, 28, 15), 3, 3)
            p.setPen(QColor("#111"))
            p.drawText(QRect(tw - 30, th - 17, 28, 15), Qt.AlignCenter, f"×{hold}")
        p.end()
        return pm

    def _content_changed(self):
        if not self.show_thumbs:
            return
        self._live_rev += 1
        self._content_timer.start(450)

    def _refresh_current_thumb(self):
        i = self.win.current_page_index
        if 0 <= i < self.list.count():
            self._queue_thumb(i, front=True)

    # ------------------------------------------------------------ olaylar
    def _on_row(self, row):
        if self._block or row < 0 or self.ctrl.is_playing:
            return
        if row != self.win.current_page_index:
            self.win.loadPageData(row)

    def _on_fps(self, v):
        self.win.current_export_fps = int(v)
        QSettings("kavram", "DrawingEditor").setValue("exportFPS", int(v))

    def _on_hold(self, v):
        i = self.win.current_page_index
        self.ctrl.set_hold(i, v)
        self._queue_thumb(i, front=True)

    def _rows_moved(self, _parent, start, _end, _dest_parent, row):
        src = start
        dst = row - 1 if row > start else row
        if src == dst:
            return
        QTimer.singleShot(0, lambda: self.win.movePage(src, dst))

    def _on_play_state(self, playing):
        self.play_btn.setIcon(create_svg_icon(SVG_STOP if playing else SVG_PLAY, 18))
        self.list.setEnabled(not playing)
        if not playing:
            self.sync_current()

    def _on_playhead(self, page):
        if not self.ctrl.is_playing:
            return
        self._block = True
        try:
            if 0 <= page < self.list.count():
                self.list.setCurrentRow(page)
                self._scroll_to_current()
        finally:
            self._block = False

    def _context_menu(self, pos):
        item = self.list.itemAt(pos)
        if item is None:
            return
        row = self.list.row(item)
        if row != self.win.current_page_index:
            self.win.loadPageData(row)
        menu = QMenu(self)
        a_hold = menu.addAction("Kare süresini ayarla…")
        a_blank = menu.addAction("Sonrasına boş kare ekle")
        a_dup = menu.addAction("Sonrasına çoğalt")
        menu.addSeparator()
        a_del = menu.addAction("Sil")
        chosen = menu.exec_(self.list.mapToGlobal(pos))
        if chosen == a_hold:
            v, ok = QInputDialog.getInt(self, "Kare Süresi", "Kaç kare boyunca tutulsun?",
                                        self.ctrl.get_hold(row), 1, 120)
            if ok:
                self.hold_spin.setValue(v)
        elif chosen == a_blank:
            self.win.insertBlankPageAfter()
        elif chosen == a_dup:
            self.win.duplicateToNextPage()
        elif chosen == a_del:
            self.win.removePage()
