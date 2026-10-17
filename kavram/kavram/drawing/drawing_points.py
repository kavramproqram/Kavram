# Kavram - A modu (nokta düzenleme)
#
# Çizimler "noktalı görünüme" geçer: her çizginin köşe noktaları arka plan renginde gösterilir
# (düz çizgi 2 nokta, dikdörtgen 4, karmaşık çizim onlarca nokta). Serbest çizimler önce
# sadeleştirilir (Ramer-Douglas-Peucker), böylece yüzlerce fare örneği yerine anlamlı köşeler görünür.
#
#   Tıkla = nokta seç, Shift+tıkla = çoklu seçim, boşlukta sürükle = kutuyla seçim (Shift = ekle)
#   G = taşı, S = büyüt/küçült, R = döndür  (sol tık onayla, Esc / sağ tık iptal; G'de X/Y eksen kısıtı)
#   D = seçili noktaların çizgilerini başka kareye kopyala, Ctrl+D = aradaki kareleri otomatik doldur
#       (nokta konumları kareler arasında geçiş yapar: gerçek "morph" ara kare)
#
# Çizgi, noktalar hareket edince yeniden çizilir: noktaların arasındaki ham örnekler, komşu köşelerin
# yer değiştirmesine göre yumuşakça karıştırılır (eğrilik korunur).
from drawing_common import *
from drawing_layers import LAYER_FORMAT, new_layer_image
import drawing_select as KS


# ---------------------------------------------------------------------------
# Saf yardımcılar (Qt gerektirmez)
# ---------------------------------------------------------------------------
def is_editable(el):
    if el.get("is_eraser"):
        return False
    t = el.get("type")
    if t in ("stroke", "stroke_pressure"):
        return len(el.get("points", [])) >= 1
    if t in ("text", "image"):
        return "position" in el
    return False


def element_xy(el):
    if el["type"] in ("stroke", "stroke_pressure"):
        return [(float(p[0]), float(p[1])) for p in el["points"]]
    return [(float(el["position"][0]), float(el["position"][1]))]


def apply_xy(el, xy):
    if el["type"] in ("stroke", "stroke_pressure"):
        for row, (x, y) in zip(el["points"], xy):
            row[0] = round(x, 2)
            row[1] = round(y, 2)
        if el.get("is_solid_fill") and "bbox" in el and xy:
            xs = [p[0] for p in xy]
            ys = [p[1] for p in xy]
            el["bbox"] = [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
    else:
        el["position"] = [round(xy[0][0], 2), round(xy[0][1], 2)]


def copy_element(el):
    """Büyük metinleri (doku, görsel) kopyalamadan, konumları değişebilen alanları kopyalar."""
    new = dict(el)
    if "points" in el:
        new["points"] = [list(r) for r in el["points"]]
    if "position" in el:
        new["position"] = list(el["position"])
    if "bbox" in el:
        new["bbox"] = list(el["bbox"])
    if isinstance(el.get("color"), list):
        new["color"] = list(el["color"])
    return new


def rdp_indices(pts, eps):
    """Ramer-Douglas-Peucker (yinelemesiz). Korunan nokta indekslerini döndürür."""
    n = len(pts)
    if n <= 2:
        return list(range(n))
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        root = math.sqrt(l2)
        dmax, idx = -1.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            if l2 == 0:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dy * (px - ax) - dx * (py - ay)) / root
            if d > dmax:
                dmax, idx = d, i
        if dmax > eps and idx > 0:
            keep[idx] = True
            stack.append((a, idx))
            stack.append((idx, b))
    return [i for i, k in enumerate(keep) if k]


def key_info(xy, max_keys=40, eps0=2.5):
    """Bir çizginin köşe noktaları. 'all' = tüm anahtarlar, 'show' = gösterilenler (kapalı şekilde son = ilk)."""
    n = len(xy)
    if n <= 2:
        keys = list(range(n))
    else:
        eps = eps0
        keys = rdp_indices(xy, eps)
        while len(keys) > max_keys:
            eps *= 1.4
            keys = rdp_indices(xy, eps)
    closed = (n >= 4 and len(keys) >= 3 and keys[0] == 0 and keys[-1] == n - 1
              and math.hypot(xy[0][0] - xy[-1][0], xy[0][1] - xy[-1][1]) <= 1.5)
    return {"all": keys, "show": keys[:-1] if closed else list(keys), "closed": closed, "n": n}


def deform_points(xy, keys_all, disp):
    """Anahtar noktaların yer değiştirmesini (disp) aradaki ham noktalara yay uzunluğuyla dağıtır."""
    n = len(xy)
    if n == 0:
        return []
    if len(keys_all) == 1:
        d = disp[0]
        return [(x + d[0], y + d[1]) for x, y in xy]
    cum = [0.0]
    for i in range(1, n):
        cum.append(cum[-1] + math.hypot(xy[i][0] - xy[i - 1][0], xy[i][1] - xy[i - 1][1]))
    out = [None] * n
    for j in range(len(keys_all) - 1):
        a, b = keys_all[j], keys_all[j + 1]
        da, db = disp[j], disp[j + 1]
        span = cum[b] - cum[a]
        for i in range(a, b + 1):
            if span > 1e-9:
                t = (cum[i] - cum[a]) / span
            else:
                t = (i - a) / float(b - a) if b > a else 0.0
            out[i] = (xy[i][0] + da[0] + (db[0] - da[0]) * t,
                      xy[i][1] + da[1] + (db[1] - da[1]) * t)
    return out


def lerp_element(s, e, k, uid):
    """İki anahtar kare arasındaki ara çizgiyi (nokta konumlarını karıştırarak) üretir."""
    if s.get("type") != e.get("type"):
        return None
    sxy, exy = element_xy(s), element_xy(e)
    if len(sxy) != len(exy):
        return None
    new = copy_element(s)
    new.pop("lk", None)
    new["tw"] = uid
    apply_xy(new, [(sx + (ex - sx) * k, sy + (ey - sy) * k) for (sx, sy), (ex, ey) in zip(sxy, exy)])
    return new


# ---------------------------------------------------------------------------
# Tuval davranışı
# ---------------------------------------------------------------------------
class PointModeMixin:
    def initPoints(self):
        self.point_active = False
        self.pt_selected = set()          # {(eleman_indeksi, nokta_sırası)}
        self.pt_sel_layer = None
        self.pt_cache = {}                # id(eleman) -> köşe bilgisi
        self.pt_marquee = None            # [QPointF, QPointF]
        self.pt_marquee_shift = False
        self.pt_op = None                 # 'g' / 's' / 'r'
        self.pt_data = None
        self.pt_axis = None
        self.pt_mouse0 = QPointF(0, 0)
        self.pt_preview = None
        self.pt_preview_pts = []
        self.pt_tween = None

    def setPointActive(self, active):
        active = bool(active)
        if not active:
            if self.pt_op:
                self.ptCancelOp()
            self.pt_selected = set()
            self.pt_marquee = None
        self.point_active = active
        if active:
            self.setCursor(Qt.CrossCursor)
        self.update()

    def ptPageChanged(self):
        self.pt_selected = set()
        self.pt_cache = {}
        self.pt_marquee = None
        self.pt_op = None
        self.pt_data = None
        self.pt_preview = None

    def ptHistoryApplied(self):
        self.ptPageChanged()

    # ------------------------------------------------------------------ nokta bilgisi
    def _pt_info(self, el):
        n = len(el["points"]) if "points" in el else 1
        info = self.pt_cache.get(id(el))
        if info is None or info["n"] != n or info["el"] is not el:
            info = key_info(element_xy(el))
            info["el"] = el          # güçlü referans: id yeniden kullanımını engeller
            self.pt_cache[id(el)] = info
        return info

    def _pt_candidates(self):
        layer = self.layer_stack.active
        return [(i, el) for i, el in enumerate(self.drawing_elements)
                if el.get("layer") == layer.name and is_editable(el)]

    def _pt_visible(self, x, y):
        img = self.layer_stack.active.image
        xi, yi = int(x), int(y)
        if xi < 0 or yi < 0 or xi >= img.width() or yi >= img.height():
            return True
        return img.pixelColor(xi, yi).alpha() > 8      # silinmiş çizgilerin hayalet noktaları gösterilmesin

    def _pt_positions(self, i, el, check_visible=True):
        info = self._pt_info(el)
        xy = element_xy(el)
        out = []
        for slot, idx in enumerate(info["show"]):
            x, y = xy[idx]
            if check_visible and not self._pt_visible(x, y):
                continue
            out.append((slot, QPointF(x, y)))
        return out

    def _pt_validate(self):
        layer = self.layer_stack.active
        if self.pt_sel_layer is not None and self.pt_sel_layer != layer.id:
            self.pt_selected = set()
        n = len(self.drawing_elements)
        if any(i >= n for i, _s in self.pt_selected):
            self.pt_selected = set()

    def _pt_hit(self, pos):
        radius = 9.0 / max(self.zoom_factor, 0.01)
        best, best_d = None, radius
        for i, el in self._pt_candidates():
            for slot, pt in self._pt_positions(i, el):
                d = math.hypot(pt.x() - pos.x(), pt.y() - pos.y())
                if d <= best_d:
                    best, best_d = (i, slot), d
        return best

    # ------------------------------------------------------------------ fare
    def ptMousePress(self, event):
        if not self._select_can_handle(event):
            return False
        if self.pt_op:
            if event.button() == Qt.RightButton:
                self.ptCancelOp()
            elif event.button() == Qt.LeftButton:
                self.ptConfirmOp()
            return True
        if event.button() != Qt.LeftButton:
            return False
        pos = self.toCanvas(event.pos())
        shift = bool(event.modifiers() & Qt.ShiftModifier)
        self._pt_validate()
        hit = self._pt_hit(pos)
        if hit is not None:
            if shift:
                if hit in self.pt_selected:
                    self.pt_selected.discard(hit)
                else:
                    self.pt_selected.add(hit)
            elif hit not in self.pt_selected:
                self.pt_selected = {hit}
            self.pt_sel_layer = self.layer_stack.active.id
            self.pt_marquee = None
        else:
            self.pt_marquee = [QPointF(pos), QPointF(pos)]
            self.pt_marquee_shift = shift
        self.update()
        return True

    def ptMouseMove(self, event):
        if self.panning:
            return False
        pos = self.toCanvas(event.pos())
        self.sel_last_canvas = QPointF(pos)
        if self.pt_op:
            self._pt_update_preview(pos)
            self.update()
            return True
        if self.pt_marquee:
            self.pt_marquee[1] = QPointF(pos)
            self.update()
            return True
        return False

    def ptMouseRelease(self, event):
        if self.pt_op:
            return True
        if self.pt_marquee and event.button() == Qt.LeftButton:
            a, b = self.pt_marquee
            moved = abs(b.x() - a.x()) + abs(b.y() - a.y()) > 4.0 / max(self.zoom_factor, 0.01)
            if moved:
                rect = QRectF(a, b).normalized()
                picked = set()
                for i, el in self._pt_candidates():
                    for slot, pt in self._pt_positions(i, el):
                        if rect.contains(pt):
                            picked.add((i, slot))
                self._pt_validate()
                self.pt_selected = (self.pt_selected | picked) if self.pt_marquee_shift else picked
                self.pt_sel_layer = self.layer_stack.active.id
            elif not self.pt_marquee_shift:
                self.pt_selected = set()                 # boşluğa tıklama: seçimi kaldır
            self.pt_marquee = None
            self.update()
            return True
        return False

    # ------------------------------------------------------------------ G / S / R
    def ptStartOp(self, kind):
        if not self.point_active or self.pt_op:
            return
        self._pt_validate()
        if not self.pt_selected:
            QToolTip.showText(QCursor.pos(), "Önce nokta seçin", self)
            return
        if not self.isLayerEditable():
            QToolTip.showText(QCursor.pos(), "Aktif katman gizli veya kilitli", self)
            return
        layer = self.layer_stack.active
        idxs = sorted({i for i, _s in self.pt_selected})
        self.saveStateForUndo()
        bases, olds, sel_pts = {}, [], []
        for i in idxs:
            old = self.drawing_elements[i]
            info = self._pt_info(old)
            xy = element_xy(old)
            slots = {s for j, s in self.pt_selected if j == i}
            bases[i] = {"el": old, "xy": xy, "info": info, "slots": slots}
            olds.append(old)
            for s in slots:
                sel_pts.append(xy[info["all"][s]])
            live = copy_element(old)                       # undo yığınındaki eski nesneler bozulmasın
            self.drawing_elements[i] = live
            self.pt_cache[id(live)] = dict(info, el=live)
        KS.erase_elements(self, layer.image, olds)
        layer.invalidate()
        self.commitImageToPixmap()
        pivot = QPointF(sum(p[0] for p in sel_pts) / len(sel_pts), sum(p[1] for p in sel_pts) / len(sel_pts))
        self.pt_op = kind
        self.pt_axis = None
        self.pt_data = {"bases": bases, "pivot": pivot}
        self.pt_mouse0 = QPointF(self.sel_last_canvas)
        self.pt_preview = new_layer_image(self.layer_stack.w, self.layer_stack.h)
        self._pt_update_preview(self.sel_last_canvas)
        self.setCursor(Qt.SizeAllCursor)
        self.update()

    def _pt_transform_fn(self, pos):
        piv, m0 = self.pt_data["pivot"], self.pt_mouse0
        if self.pt_op == 'g':
            dx, dy = round(pos.x() - m0.x()), round(pos.y() - m0.y())
            if self.pt_axis == 'x':
                dy = 0
            elif self.pt_axis == 'y':
                dx = 0
            return lambda x, y: (x + dx, y + dy)
        if self.pt_op == 's':
            d0 = max(8.0, math.hypot(m0.x() - piv.x(), m0.y() - piv.y()))
            k = max(0.02, math.hypot(pos.x() - piv.x(), pos.y() - piv.y()) / d0)
            return lambda x, y: (piv.x() + (x - piv.x()) * k, piv.y() + (y - piv.y()) * k)
        ang = math.atan2(pos.y() - piv.y(), pos.x() - piv.x()) - math.atan2(m0.y() - piv.y(), m0.x() - piv.x())
        c, s = math.cos(ang), math.sin(ang)
        return lambda x, y: (piv.x() + (x - piv.x()) * c - (y - piv.y()) * s,
                             piv.y() + (x - piv.x()) * s + (y - piv.y()) * c)

    def _pt_build_elements(self, f):
        out = {}
        for i, b in self.pt_data["bases"].items():
            xy, info = b["xy"], b["info"]
            keys = info["all"]
            disp = [(0.0, 0.0)] * len(keys)
            for s in b["slots"]:
                kx, ky = xy[keys[s]]
                nx, ny = f(kx, ky)
                disp[s] = (nx - kx, ny - ky)
            if info["closed"]:
                disp[-1] = disp[0]
            el = copy_element(b["el"])
            apply_xy(el, deform_points(xy, keys, disp))
            out[i] = el
        return out

    def _pt_update_preview(self, pos):
        els = self._pt_build_elements(self._pt_transform_fn(pos))
        self.pt_preview.fill(Qt.transparent)
        self._render_group(self.pt_preview, list(els.values()))
        pts = []
        for i, el in els.items():
            info = self.pt_data["bases"][i]["info"]
            xy = element_xy(el)
            for slot, idx in enumerate(info["show"]):
                pts.append((QPointF(xy[idx][0], xy[idx][1]), (i, slot) in self.pt_selected))
        self.pt_preview_pts = pts

    def ptConfirmOp(self):
        if not self.pt_op:
            return
        layer = self.layer_stack.active
        els = self._pt_build_elements(self._pt_transform_fn(self.sel_last_canvas))
        self._render_group(layer.image, list(els.values()))
        for i, el in els.items():
            self.drawing_elements[i] = el
            self.pt_cache[id(el)] = dict(self.pt_data["bases"][i]["info"], el=el)
        self.pt_op = None
        self.pt_data = None
        self.pt_preview = None
        self.pt_preview_pts = []
        self.setCursor(Qt.CrossCursor)
        layer.invalidate()
        self.commitImageToPixmap()
        if self.parent():
            self.parent().is_project_modified = True
        self.update()
        self.contentChanged.emit()

    def ptCancelOp(self):
        if not self.pt_op:
            return
        if self.undo_stack:
            _elements, snap = self.undo_stack.pop()
            if snap.get("kind") == "layer":
                layer = self.layer_stack.by_id(snap["id"])
                if layer is not None and snap.get("image") is not None:
                    layer.image = snap["image"]
                    layer.touch()
        self.pt_op = None
        self.pt_data = None
        self.pt_preview = None
        self.pt_preview_pts = []
        self.setCursor(Qt.CrossCursor)
        self.commitImageToPixmap()
        self.update()

    def ptSetAxis(self, axis):
        if self.pt_op == 'g':
            self.pt_axis = None if self.pt_axis == axis else axis
            self._pt_update_preview(self.sel_last_canvas)
            self.update()

    def ptEscape(self):
        if self.pt_op:
            self.ptCancelOp()
        elif self.pt_selected or self.pt_marquee:
            self.pt_selected = set()
            self.pt_marquee = None
            self.update()

    def ptDelete(self):
        """Seçili noktaların ait olduğu çizgileri tümüyle siler."""
        if self.pt_op or not self.pt_selected or not self.isLayerEditable():
            return
        self._pt_validate()
        idxs = {i for i, _s in self.pt_selected}
        if not idxs:
            return
        layer = self.layer_stack.active
        self.saveStateForUndo()
        olds = [self.drawing_elements[i] for i in sorted(idxs)]
        KS.erase_elements(self, layer.image, olds)
        self.drawing_elements = [el for i, el in enumerate(self.drawing_elements) if i not in idxs]
        self._painted_count = len(self.drawing_elements)
        self.pt_selected = set()
        self.pt_cache = {}
        layer.invalidate()
        self.commitImageToPixmap()
        self.update()
        self.contentChanged.emit()

    def ptRestoreSelection(self, links):
        """{lk: [slot, ...]} bağlantılarına göre seçimi yeniden kurar (D ile kareye geçişten sonra)."""
        sel = set()
        for i, el in enumerate(self.drawing_elements):
            lk = el.get("lk")
            if lk in links and is_editable(el):
                for s in links[lk]:
                    sel.add((i, s))
        self.pt_selected = sel
        self.pt_sel_layer = self.layer_stack.active.id

    # ------------------------------------------------------------------ çizim
    def _paint_points(self, painter):
        if not self.point_active:
            return
        parent = self.parent()
        painter.save()
        layer = self.layer_stack.active
        zoom = max(self.zoom_factor, 0.01)
        if self.pt_op and self.pt_preview is not None:
            painter.setOpacity(layer.opacity)
            painter.drawImage(0, 0, self.pt_preview)
            painter.setOpacity(1.0)

        rad = 4.5 / zoom
        bg = QColor(parent.background_color) if parent is not None else QColor(51, 51, 51)
        lum = 0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()
        edge = QColor(255, 255, 255) if lum < 140 else QColor(20, 20, 20)
        pen = QPen(edge, 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QBrush(bg))                      # noktalar arka plan renginde

        affected = set(self.pt_data["bases"].keys()) if (self.pt_op and self.pt_data) else set()
        selected_draw = []
        for i, el in self._pt_candidates():
            if i in affected:
                continue
            for slot, pt in self._pt_positions(i, el):
                if (i, slot) in self.pt_selected:
                    selected_draw.append(pt)
                else:
                    painter.drawEllipse(pt, rad, rad)
        if self.pt_op:
            for pt, sel in self.pt_preview_pts:
                if sel:
                    selected_draw.append(pt)
                else:
                    painter.drawEllipse(pt, rad, rad)

        sel_pen = QPen(QColor(255, 255, 255), 1.5)
        sel_pen.setCosmetic(True)
        painter.setPen(sel_pen)
        painter.setBrush(QColor(255, 150, 0))
        for pt in selected_draw:
            painter.drawEllipse(pt, rad * 1.2, rad * 1.2)

        if self.pt_marquee:
            rect = QRectF(self.pt_marquee[0], self.pt_marquee[1]).normalized()
            painter.fillRect(rect, QColor(90, 150, 255, 35))
            dash = QPen(QColor(255, 255, 255), 1)
            dash.setCosmetic(True)
            dash.setStyle(Qt.DashLine)
            painter.setPen(dash)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)
        painter.restore()


# ---------------------------------------------------------------------------
# D (kareye kopyala) ve Ctrl+D (ara kareler) - nokta modu
# ---------------------------------------------------------------------------
def points_copy_to_frame(win):
    area = win.drawing_area
    if not (area.point_active and area.pt_selected):
        QToolTip.showText(QCursor.pos(), "Önce nokta seçin", area)
        return
    if area.pt_op:
        area.ptConfirmOp()
    area._pt_validate()
    idxs = sorted({i for i, _s in area.pt_selected})
    if not idxs:
        return
    slots_by_idx = {i: sorted(s for j, s in area.pt_selected if j == i) for i in idxs}
    target = KS.ask_target_frame(win)
    if target is None:
        return
    layer = area.layer_stack.active
    cur = win.current_page_index

    base = str(int(time.time() * 1000) % 1000000000)
    links = {}
    for n, i in enumerate(idxs):                           # başlangıç çizgilerini bağlantı etiketiyle işaretle
        lk = f"{base}_{n}"
        area.drawing_elements[i]["lk"] = lk
        links[lk] = slots_by_idx[i]

    win.flushCurrentPageToCache()
    KS.ensure_pages(win, target)
    copies = [copy_element(area.drawing_elements[i]) for i in idxs]
    existing = KS.read_page_elements(win, target)
    KS.write_page_elements(win, target, existing + copies)
    KS.edit_layer_file(win, target, layer.id, lambda img: area._render_group(img, copies))

    area.pt_tween = {"kind": "points", "start_page": cur, "end_page": target, "layer_id": layer.id,
                     "links": list(links.keys()), "uid": base}
    win.loadPageData(target)
    area.ptRestoreSelection(links)
    area.update()
    KS.after_keyframe_change(win, f"Kopya kare {target + 1}'e eklendi. G/S/R ile noktaları düzenleyin, sonra Ctrl+D.")


def points_build_tween(win):
    area = win.drawing_area
    t = area.pt_tween
    if not t or t.get("kind") != "points":
        QMessageBox.information(win, "Ara Kareler",
                                "Önce noktaları seçip D ile hedef kareye kopyalayın, G / S / R ile düzenleyin;\n"
                                "ardından Ctrl+D ile ara kareler oluşturulur.")
        return
    if area.pt_op:
        area.ptConfirmOp()
    start, end = t["start_page"], t["end_page"]
    lo, hi = min(start, end), max(start, end)
    if hi - lo < 2:
        QMessageBox.information(win, "Ara Kareler", "Başlangıç ve hedef kare arasında ara kare yok.")
        return
    if not win.flushCurrentPageToCache():
        return

    s_elems = KS.read_page_elements(win, start)
    e_elems = KS.read_page_elements(win, end)
    pairs = []
    for lk in t["links"]:
        s = next((e for e in s_elems if e.get("lk") == lk), None)
        e = next((e for e in e_elems if e.get("lk") == lk), None)
        if s is not None and e is not None and lerp_element(s, e, 0.0, "x") is not None:
            pairs.append((s, e))
    if not pairs:
        QMessageBox.information(win, "Ara Kareler",
                                "Eşleşen çizgi bulunamadı (nokta sayısı değişmiş veya çizgiler silinmiş olabilir).")
        return

    uid, lid, span = t["uid"], t["layer_id"], float(end - start)
    try:
        for pg in range(lo + 1, hi):
            k = (pg - start) / span
            new_elems = [lerp_element(s, e, k, uid) for s, e in pairs]
            page_elems = KS.read_page_elements(win, pg)
            old = [e for e in page_elems if e.get("tw") == uid]
            kept = [e for e in page_elems if e.get("tw") != uid]

            def image_fn(img, old=old, new_elems=new_elems):
                KS.erase_elements(area, img, old)           # önceki Ctrl+D izini sil
                area._render_group(img, new_elems)
            KS.edit_layer_file(win, pg, lid, image_fn)
            KS.write_page_elements(win, pg, kept + new_elems)
    except Exception as ex:
        QMessageBox.critical(win, "Hata", f"Ara kareler oluşturulamadı: {ex}")
        return

    if lo < win.current_page_index < hi:
        win.loadPageData(win.current_page_index, save_current=False)
    KS.after_keyframe_change(win, f"{hi - lo - 1} ara kare oluşturuldu.")
