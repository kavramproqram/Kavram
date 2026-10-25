# Kavram - S modu (piksel seçimi) + iki mod için ortak anahtar kare (keyframe) yardımcıları
#
# S modu (piksel seçimi):
#   Sürükle = serbest seçim, Shift+sürükle = dikdörtgen seçim (noktalı çizgi).
#   G = taşı, S = büyüt/küçült, R = döndür   (sol tık onayla, Esc / sağ tık iptal; G'de X/Y eksen kısıtı)
#   D = seçimi başka kareye kopyala,  Ctrl+D = aradaki kareleri otomatik doldur
#
# A modu (nokta düzenleme) için bkz. drawing_points.py - aynı kısayollar, aynı D / Ctrl+D mantığı.
from drawing_common import *
from drawing_layers import (LAYER_FORMAT, new_layer_image, fit_to_canvas, layer_path)


# ---------------------------------------------------------------------------
# Ortak yardımcılar (S ve A modu kullanır)
# ---------------------------------------------------------------------------
def bleach_alpha(mask):
    """Maskedeki kısmi saydamlıkları (kenar yumuşatma) güçlendirir; silerken hayalet halka kalmasın."""
    src = mask.copy()
    p = QPainter(mask)
    p.setCompositionMode(QPainter.CompositionMode_Plus)
    for _ in range(3):
        p.drawImage(0, 0, src)
    p.end()


def erase_mask(img, mask):
    """mask'in dolu olduğu yerleri img'den siler."""
    bleach_alpha(mask)
    p = QPainter(img)
    p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
    p.drawImage(0, 0, mask)
    p.end()


def erase_elements(area, img, elements):
    """Çizim kayıtlarının raster karşılığını img'den siler."""
    if not elements:
        return
    mask = new_layer_image(img.width(), img.height())
    area._render_group(mask, elements)
    erase_mask(img, mask)


def edit_layer_file(win, page_idx, layer_id, image_fn):
    """Bir karenin bir katman dosyasını diskte düzenler (kare yüklü olmasa da). image_fn(QImage) görüntüyü değiştirir."""
    st = win.drawing_area.layer_stack
    cache = win.drawing_cache_dir
    path = layer_path(cache, page_idx, layer_id)

    # Eski tek parça dosyası olan karede içeriği kaybetmemek için önce katman dosyasına taşı
    legacy = os.path.join(cache, f"s{page_idx + 1}.png")
    has_layer_files = any(os.path.isfile(layer_path(cache, page_idx, l.id)) for l in st.layers)
    if not has_layer_files and os.path.isfile(legacy):
        target = st.by_name("Çizim") or st.layers[-1]
        shutil.copyfile(legacy, layer_path(cache, page_idx, target.id))

    img = QImage(path) if os.path.isfile(path) else QImage()
    img = fit_to_canvas(img, st.w, st.h) if not img.isNull() else new_layer_image(st.w, st.h)
    image_fn(img)
    if not img.save(path, "PNG"):
        raise IOError(f"Kare dosyası yazılamadı: {path}")


def read_page_elements(win, page_idx):
    """Karenin çizim kayıtlarını diskten okur (önce flushCurrentPageToCache çağrılmış olmalı)."""
    f = os.path.join(win.drawing_cache_dir, f"s{page_idx + 1}_elements.json")
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return []


def write_page_elements(win, page_idx, elements):
    f = os.path.join(win.drawing_cache_dir, f"s{page_idx + 1}_elements.json")
    with open(f, 'w', encoding='utf-8') as fh:
        json.dump(elements, fh)


def ask_target_frame(win):
    """Hedef kare numarasını sorar; 0 tabanlı indeks döner (iptalde None)."""
    cur = win.current_page_index
    total = len(win.pages_data)
    default = total if total > cur + 1 else min(win.max_pages, cur + 2)
    no, ok = QInputDialog.getInt(
        win, "Kareye Kopyala",
        "Kopyanın gönderileceği kare numarası:\n(Olmayan kareler otomatik oluşturulur)",
        default, 1, win.max_pages)
    if not ok:
        return None
    if no - 1 == cur:
        QMessageBox.information(win, "Kareye Kopyala", "Hedef kare, mevcut kareden farklı olmalı.")
        return None
    return no - 1


def ensure_pages(win, target):
    created = False
    while len(win.pages_data) <= target:
        win.pages_data.append({"background": QColor(win.background_color), "hold": 1})
        created = True
    if created:
        win.refreshPageButtonMenu()
    return created


def after_keyframe_change(win, message):
    win.is_project_modified = True
    if hasattr(win, "anim"):
        win.anim.invalidate_onion()
    win.drawing_area.update()
    if hasattr(win, "timeline"):
        win.timeline.schedule_refresh()
    QToolTip.showText(QCursor.pos(), message, win.drawing_area)


# ---------------------------------------------------------------------------
# S modu: tuval davranışı
# ---------------------------------------------------------------------------
class SelectionMixin:
    # ------------------------------------------------------------------ durum
    def initSelection(self):
        self.setMouseTracking(True)
        self.select_active = False
        self.sel_path = None              # QPainterPath (tuval koordinatı)
        self.sel_rect = QRect()
        self.sel_points = []              # çizilmekte olan serbest seçim noktaları
        self.sel_drawing = False
        self.sel_rect_mode = False
        self.sel_floating = None          # tutulan piksel parçası (QImage)
        self.sel_grab = False             # bir işlem (G/S/R) sürüyor mu
        self.sel_op = None                # 'g' / 's' / 'r'
        self.sel_dp = QPointF(0, 0)
        self.sel_k = 1.0
        self.sel_a = 0.0
        self.sel_grab_mouse0 = QPointF(0, 0)
        self.sel_axis = None              # G için: None / 'x' / 'y'
        self.sel_cur = {"p": QPointF(0, 0), "s": 1.0, "r": 0.0}   # takip edilen merkez / ölçek / açı
        self.sel_last_canvas = QPointF(0, 0)
        self.sel_tween = None
        self._keep_selection_once = False
        self._sel_dash = 0
        self._sel_timer = QTimer(self)
        self._sel_timer.setInterval(120)
        self._sel_timer.timeout.connect(self._sel_tick)

    def setSelectActive(self, active):
        active = bool(active)
        if not active:
            if self.sel_grab:
                self.selectCancelGrab()
            self.clearSelection()
        self.select_active = active
        if active:
            self.setCursor(Qt.CrossCursor)
        self.update()

    def clearSelection(self):
        self.sel_path = None
        self.sel_rect = QRect()
        self.sel_points = []
        self.sel_drawing = False
        self._sel_timer.stop()
        self.update()

    def pageChangedReset(self):
        """Sayfa değişince çağrılır. D ile kopyalama sırasındaki geçişte piksel seçimi korunur."""
        if hasattr(self, "ptPageChanged"):
            self.ptPageChanged()
        if self._keep_selection_once:
            self._keep_selection_once = False
            return
        if self.sel_grab:
            self.sel_floating = None
            self.sel_grab = False
            self.sel_op = None
        self.clearSelection()

    def onHistoryApplied(self):
        """Geri al / yinele sonrası seçimler geçersiz olabilir."""
        self.sel_floating = None
        self.sel_grab = False
        self.sel_op = None
        self.clearSelection()
        if hasattr(self, "ptHistoryApplied"):
            self.ptHistoryApplied()

    def hasSelection(self):
        return self.sel_path is not None and not self.sel_rect.isEmpty()

    def _sel_tick(self):
        self._sel_dash = (self._sel_dash + 1) % 8
        if self.hasSelection() or self.sel_drawing:
            self.update()

    # ------------------------------------------------------------------ iki mod için ortak yönlendirme
    def modeStartOp(self, kind):
        if self.select_active:
            self.selectStartOp(kind)
        elif getattr(self, "point_active", False):
            self.ptStartOp(kind)

    def modeEscape(self):
        if self.select_active:
            self.selectEscape()
        elif getattr(self, "point_active", False):
            self.ptEscape()

    def modeDelete(self):
        if self.select_active:
            self.selectDelete()
        elif getattr(self, "point_active", False):
            self.ptDelete()

    def modeAxis(self, axis):
        if self.select_active:
            self.selectSetAxis(axis)
        elif getattr(self, "point_active", False):
            self.ptSetAxis(axis)

    # ------------------------------------------------------------------ fare
    def _select_can_handle(self, event):
        parent = self.parent()
        if parent is None:
            return False
        if self.alt_held or self.alt_permanent_pan_mode or parent.nav_button.isChecked():
            return False
        return True

    def selectMousePress(self, event):
        if not self._select_can_handle(event):
            return False
        if self.sel_grab:
            if event.button() == Qt.RightButton:
                self.selectCancelGrab()
            elif event.button() == Qt.LeftButton:
                self.selectConfirmGrab()
            return True
        if event.button() != Qt.LeftButton:
            return False
        pos = self.toCanvas(event.pos())
        self.sel_drawing = True
        self.sel_rect_mode = bool(event.modifiers() & Qt.ShiftModifier)
        self.sel_points = [QPointF(pos)]
        self.sel_path = None
        self.sel_rect = QRect()
        self._sel_timer.start()
        self.update()
        return True

    def selectMouseMove(self, event):
        if self.panning:
            return False
        pos = self.toCanvas(event.pos())
        self.sel_last_canvas = QPointF(pos)
        if self.sel_grab:
            self._sel_update_op(pos)
            self.update()
            return True
        if self.sel_drawing:
            if self.sel_rect_mode:
                self.sel_points = [self.sel_points[0], QPointF(pos)]
            else:
                last = self.sel_points[-1]
                if abs(pos.x() - last.x()) + abs(pos.y() - last.y()) > 2.0:
                    self.sel_points.append(QPointF(pos))
            self.update()
            return True
        return False

    def selectMouseRelease(self, event):
        if self.sel_grab:
            return True
        if self.sel_drawing and event.button() == Qt.LeftButton:
            self.sel_drawing = False
            self._finish_lasso()
            return True
        return False

    def _finish_lasso(self):
        path = QPainterPath()
        if self.sel_rect_mode and len(self.sel_points) >= 2:
            path.addRect(QRectF(self.sel_points[0], self.sel_points[-1]).normalized())
        elif len(self.sel_points) >= 3:
            path.addPolygon(QPolygonF(self.sel_points))
            path.closeSubpath()
        canvas = QPainterPath()
        canvas.addRect(QRectF(0, 0, self.layer_stack.w, self.layer_stack.h))
        path = path.intersected(canvas)
        rect = path.boundingRect().toAlignedRect().intersected(QRect(0, 0, self.layer_stack.w, self.layer_stack.h))
        self.sel_points = []
        if rect.width() < 2 or rect.height() < 2:
            self.clearSelection()
            return
        self.sel_path = path
        self.sel_rect = rect
        self.sel_cur = {"p": QPointF(rect.x() + rect.width() / 2.0, rect.y() + rect.height() / 2.0),
                        "s": 1.0, "r": 0.0}
        self._sel_timer.start()
        self.update()

    # ------------------------------------------------------------------ piksel işlemleri
    def _extract_clip(self, layer, path, rect):
        clip = QImage(rect.size(), LAYER_FORMAT)
        clip.fill(Qt.transparent)
        p = QPainter(clip)
        local = QPainterPath(path)
        local.translate(-rect.x(), -rect.y())
        p.setClipPath(local)
        p.drawImage(0, 0, layer.image, rect.x(), rect.y(), rect.width(), rect.height())
        p.end()
        return clip

    def _erase_region(self, layer, path, rect):
        p = QPainter(layer.image)
        p.setClipPath(path)
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        p.fillRect(rect, QColor(0, 0, 0, 0))
        p.end()
        layer.invalidate()
        layer.touch()

    # ------------------------------------------------------------------ G / S / R
    def _sel_xf(self):
        """Mevcut önizleme dönüşümü (tuval koordinatından tuval koordinatına, merkez etrafında)."""
        c = self.sel_cur["p"]
        xf = QTransform()
        xf.translate(c.x() + self.sel_dp.x(), c.y() + self.sel_dp.y())
        xf.rotate(self.sel_a)
        xf.scale(self.sel_k, self.sel_k)
        xf.translate(-c.x(), -c.y())
        return xf

    def selectStartOp(self, kind):
        if not self.select_active or not self.hasSelection() or self.sel_grab:
            return
        if not self.isLayerEditable():
            QToolTip.showText(QCursor.pos(), "Aktif katman gizli veya kilitli", self)
            return
        layer = self.layer_stack.active
        self.saveStateForUndo()
        clip = self._extract_clip(layer, self.sel_path, self.sel_rect)
        self._erase_region(layer, self.sel_path, self.sel_rect)
        self.commitImageToPixmap()
        self.sel_floating = clip
        self.sel_op = kind
        self.sel_grab = True
        self.sel_dp = QPointF(0, 0)
        self.sel_k = 1.0
        self.sel_a = 0.0
        self.sel_grab_mouse0 = QPointF(self.sel_last_canvas)
        self.sel_axis = None
        self.setCursor(Qt.SizeAllCursor)
        self.update()

    def selectStartGrab(self):
        self.selectStartOp('g')

    def _sel_update_op(self, pos):
        c = self.sel_cur["p"]
        m0 = self.sel_grab_mouse0
        if self.sel_op == 'g':
            dx = round(pos.x() - m0.x())
            dy = round(pos.y() - m0.y())
            if self.sel_axis == 'x':
                dy = 0
            elif self.sel_axis == 'y':
                dx = 0
            self.sel_dp = QPointF(dx, dy)
        elif self.sel_op == 's':
            d0 = max(8.0, math.hypot(m0.x() - c.x(), m0.y() - c.y()))
            d1 = math.hypot(pos.x() - c.x(), pos.y() - c.y())
            self.sel_k = max(0.02, d1 / d0)
        elif self.sel_op == 'r':
            a0 = math.atan2(m0.y() - c.y(), m0.x() - c.x())
            a1 = math.atan2(pos.y() - c.y(), pos.x() - c.x())
            self.sel_a = math.degrees(a1 - a0)

    def selectSetAxis(self, axis):
        if self.sel_grab and self.sel_op == 'g':
            self.sel_axis = None if self.sel_axis == axis else axis
            self._sel_update_op(self.sel_last_canvas)
            self.update()

    def selectConfirmGrab(self):
        if not self.sel_grab or self.sel_floating is None:
            return
        layer = self.layer_stack.active
        xf = self._sel_xf()
        p = QPainter(layer.image)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setTransform(xf)
        p.drawImage(self.sel_rect.topLeft(), self.sel_floating)
        p.end()
        self.sel_path = xf.map(self.sel_path)
        canvas_rect = QRect(0, 0, self.layer_stack.w, self.layer_stack.h)
        rect = self.sel_path.boundingRect().toAlignedRect().intersected(canvas_rect)
        # takip edilen merkez / ölçek / açı (ara kare hesabı için)
        c = self.sel_cur["p"]
        self.sel_cur = {"p": QPointF(c.x() + self.sel_dp.x(), c.y() + self.sel_dp.y()),
                        "s": self.sel_cur["s"] * self.sel_k, "r": self.sel_cur["r"] + self.sel_a}
        self.sel_rect = rect if not rect.isEmpty() else QRect(self.sel_rect)
        self.sel_floating = None
        self.sel_grab = False
        self.sel_op = None
        self.sel_dp = QPointF(0, 0)
        self.sel_k = 1.0
        self.sel_a = 0.0
        self.setCursor(Qt.CrossCursor)
        self.commitImageToPixmap()
        if self.parent():
            self.parent().is_project_modified = True
        t = self.sel_tween
        win = self.parent()
        if t and win is not None and t.get("kind") == "pixels" and t["layer_id"] == layer.id \
                and win.current_page_index == t["end_page"]:
            t["end"] = {"p": QPointF(self.sel_cur["p"]), "s": self.sel_cur["s"], "r": self.sel_cur["r"]}
        self.update()
        self.contentChanged.emit()

    def selectCancelGrab(self):
        if not self.sel_grab:
            return
        if self.undo_stack:
            _elements, snap = self.undo_stack.pop()
            if snap.get("kind") == "layer":
                layer = self.layer_stack.by_id(snap["id"])
                if layer is not None and snap.get("image") is not None:
                    layer.image = snap["image"]
                    layer.touch()
        self.sel_floating = None
        self.sel_grab = False
        self.sel_op = None
        self.sel_dp = QPointF(0, 0)
        self.sel_k = 1.0
        self.sel_a = 0.0
        self.setCursor(Qt.CrossCursor)
        self.commitImageToPixmap()
        self.update()

    def selectEscape(self):
        if self.sel_grab:
            self.selectCancelGrab()
        elif self.hasSelection() or self.sel_drawing:
            self.clearSelection()

    def selectDelete(self):
        if not self.select_active or not self.hasSelection() or self.sel_grab or not self.isLayerEditable():
            return
        self.saveStateForUndo()
        self._erase_region(self.layer_stack.active, self.sel_path, self.sel_rect)
        self.commitImageToPixmap()
        self.update()
        self.contentChanged.emit()

    # ------------------------------------------------------------------ çizim (noktalı seçim çizgisi)
    def _paint_selection(self, painter):
        if not self.select_active:
            return
        painter.save()
        xf = None
        if self.sel_grab and self.sel_floating is not None:
            xf = self._sel_xf()
            painter.save()
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            painter.setOpacity(self.layer_stack.active.opacity)
            painter.setTransform(xf, True)
            painter.drawImage(self.sel_rect.topLeft(), self.sel_floating)
            painter.restore()

        path = None
        if self.sel_drawing and self.sel_points:
            path = QPainterPath()
            if self.sel_rect_mode and len(self.sel_points) >= 2:
                path.addRect(QRectF(self.sel_points[0], self.sel_points[-1]).normalized())
            else:
                path.addPolygon(QPolygonF(self.sel_points))
        elif self.hasSelection():
            path = QPainterPath(self.sel_path)
            if xf is not None:
                path = xf.map(path)

        if path is not None:
            painter.fillPath(path, QColor(90, 150, 255, 32))
            black = QPen(QColor(0, 0, 0, 230), 1)
            black.setCosmetic(True)
            painter.setPen(black)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(path)
            dotted = QPen(QColor(255, 255, 255), 1)
            dotted.setCosmetic(True)
            dotted.setStyle(Qt.CustomDashLine)
            dotted.setDashPattern([4, 4])
            dotted.setDashOffset(self._sel_dash)
            painter.setPen(dotted)
            painter.drawPath(path)
        painter.restore()


# ---------------------------------------------------------------------------
# S modu: D (kareye kopyala) ve Ctrl+D (ara kareler)
# ---------------------------------------------------------------------------
def _pixel_xf(t, params):
    """Klibin verilen parametrelerle (merkez p, ölçek s, açı r) çizim dönüşümü."""
    p, ref = params["p"], t["ref"]
    xf = QTransform()
    xf.translate(p.x(), p.y())
    xf.rotate(params["r"])
    xf.scale(params["s"], params["s"])
    xf.translate(-ref.x(), -ref.y())
    return xf


def _draw_clip(painter, t, params):
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    painter.setTransform(_pixel_xf(t, params))
    painter.drawImage(0, 0, t["clip"])


def select_copy_to_frame(win):
    """D (S modu): seçimi başka bir kareye kopyalar, o kareye geçer ve kopyayı seçili bırakır."""
    area = win.drawing_area
    if not (area.select_active and area.hasSelection()):
        QToolTip.showText(QCursor.pos(), "Önce bir bölge seçin", area)
        return
    if area.sel_grab:
        area.selectConfirmGrab()
    layer = area.layer_stack.active
    cur = win.current_page_index
    target = ask_target_frame(win)
    if target is None:
        return

    clip = area._extract_clip(layer, area.sel_path, area.sel_rect)
    rect = QRect(area.sel_rect)
    path_copy = QPainterPath(area.sel_path)
    p0 = QPointF(area.sel_cur["p"])
    ref = QPointF(p0.x() - rect.x(), p0.y() - rect.y())     # takip edilen merkez, klip yerel koordinatında

    win.flushCurrentPageToCache()
    ensure_pages(win, target)

    def image_fn(img):
        p = QPainter(img)
        p.drawImage(rect.topLeft(), clip)
        p.end()
    edit_layer_file(win, target, layer.id, image_fn)

    ident = {"p": QPointF(p0), "s": 1.0, "r": 0.0}
    area.sel_tween = {"kind": "pixels", "start_page": cur, "end_page": target, "layer_id": layer.id,
                      "clip": clip, "ref": ref,
                      "start": {"p": QPointF(p0), "s": 1.0, "r": 0.0},
                      "end": {"p": QPointF(p0), "s": 1.0, "r": 0.0}, "drawn": {}}

    area._keep_selection_once = True
    win.loadPageData(target)
    area.sel_path = path_copy
    area.sel_rect = rect
    area.sel_cur = ident
    area._sel_timer.start()
    area.update()
    after_keyframe_change(win, f"Kopya kare {target + 1}'e eklendi. G/S/R ile düzenleyin, sonra Ctrl+D.")


def select_build_tween(win):
    """Ctrl+D (S modu): ara kareleri konum / ölçek / açı geçişiyle otomatik doldurur."""
    area = win.drawing_area
    t = area.sel_tween
    if not t or t.get("kind") != "pixels":
        QMessageBox.information(win, "Ara Kareler",
                                "Önce nesneyi seçip D ile hedef kareye kopyalayın, G / S / R ile düzenleyin;\n"
                                "ardından Ctrl+D ile ara kareler oluşturulur.")
        return
    if area.sel_grab:
        area.selectConfirmGrab()
    start, end = t["start_page"], t["end_page"]
    lo, hi = min(start, end), max(start, end)
    if hi - lo < 2:
        QMessageBox.information(win, "Ara Kareler", "Başlangıç ve hedef kare arasında ara kare yok.")
        return
    if not win.flushCurrentPageToCache():
        return

    sp, ep = t["start"], t["end"]
    span = float(end - start)
    try:
        for pg in range(lo + 1, hi):
            k = (pg - start) / span
            params = {"p": QPointF(sp["p"].x() + (ep["p"].x() - sp["p"].x()) * k,
                                   sp["p"].y() + (ep["p"].y() - sp["p"].y()) * k),
                      "s": sp["s"] + (ep["s"] - sp["s"]) * k,
                      "r": sp["r"] + (ep["r"] - sp["r"]) * k}
            old = t["drawn"].get(pg)

            def image_fn(img, old=old, params=params):
                if old is not None:                         # önceki Ctrl+D izini sil
                    mask = new_layer_image(img.width(), img.height())
                    mp = QPainter(mask)
                    _draw_clip(mp, t, old)
                    mp.end()
                    erase_mask(img, mask)
                dp = QPainter(img)
                _draw_clip(dp, t, params)
                dp.end()
            edit_layer_file(win, pg, t["layer_id"], image_fn)
            t["drawn"][pg] = params
    except Exception as e:
        QMessageBox.critical(win, "Hata", f"Ara kareler oluşturulamadı: {e}")
        return

    if lo < win.current_page_index < hi:
        area._keep_selection_once = True
        saved = (QPainterPath(area.sel_path) if area.sel_path is not None else None, QRect(area.sel_rect),
                 dict(area.sel_cur))
        win.loadPageData(win.current_page_index, save_current=False)
        if saved[0] is not None:
            area.sel_path, area.sel_rect, area.sel_cur = saved
    after_keyframe_change(win, f"{hi - lo - 1} ara kare oluşturuldu.")


# ---------------------------------------------------------------------------
# D / Ctrl+D yönlendirme: hangi mod açıksa onun mantığı çalışır
# ---------------------------------------------------------------------------
def keyframe_copy(win):
    area = win.drawing_area
    if getattr(area, "point_active", False):
        from drawing_points import points_copy_to_frame
        points_copy_to_frame(win)
    elif area.select_active:
        select_copy_to_frame(win)


def keyframe_tween(win):
    area = win.drawing_area
    if getattr(area, "point_active", False):
        from drawing_points import points_build_tween
        points_build_tween(win)
    elif area.select_active:
        select_build_tween(win)
