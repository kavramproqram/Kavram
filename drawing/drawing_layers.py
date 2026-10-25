# Kavram - Gerçek katman sistemi
#
# Eski sistem: tek bir birleşik görüntü (image) + her işlemde TÜM çizim kayıtlarının
# yeniden oynatılması (replay). Eraser / katman değişimi / görünürlük gibi işlemlerde
# bu yüzden kasıyordu.
#
# Yeni sistem:
#   * Her katmanın kendi QImage'ı vardır (ARGB32_Premultiplied).
#   * DrawingArea.image artık AKTİF KATMANIN görüntüsüdür (property). Bu yüzden
#     mevcut tüm fırça/dolgu/silgi kodu değişmeden yalnız aktif katmana çizer.
#   * Görünürlük, opaklık, sıra, blend modu değişimi sadece yeniden boyamadır (replay yok).
#   * Geri alma yalnız değişen katmanı saklar (tüm sayfayı değil).
#   * Katman yapısı (isim/sıra/görünürlük...) tüm sayfalarda ortaktır; her sayfa
#     kendi katman görüntülerini s{n}_L{id}.png olarak önbellekte tutar.
from drawing_common import *

LAYER_FORMAT = QImage.Format_ARGB32_Premultiplied

BLEND_MODES = [
    ("normal", "Normal", QPainter.CompositionMode_SourceOver),
    ("multiply", "Çarpma", QPainter.CompositionMode_Multiply),
    ("screen", "Ekran", QPainter.CompositionMode_Screen),
    ("overlay", "Bindirme", QPainter.CompositionMode_Overlay),
    ("darken", "Koyulaştır", QPainter.CompositionMode_Darken),
    ("lighten", "Açıklaştır", QPainter.CompositionMode_Lighten),
    ("add", "Ekle", QPainter.CompositionMode_Plus),
]
_BLEND_MAP = {k: m for k, _n, m in BLEND_MODES}


def blend_to_mode(key):
    return _BLEND_MAP.get(key, QPainter.CompositionMode_SourceOver)


def new_layer_image(w, h):
    img = QImage(w, h, LAYER_FORMAT)
    img.fill(Qt.transparent)
    return img


def to_layer_format(img):
    return img if img.format() == LAYER_FORMAT else img.convertToFormat(LAYER_FORMAT)


def fit_to_canvas(img, w, h):
    """Görüntüyü katman formatına çevirir; boyut farklıysa (0,0)'a hizalayıp kırpar/genişletir."""
    img = to_layer_format(img)
    if img.width() == w and img.height() == h:
        return img
    out = new_layer_image(w, h)
    p = QPainter(out)
    p.drawImage(0, 0, img)
    p.end()
    return out


# ---------------------------------------------------------------------------
# Katman ve katman yığını
# ---------------------------------------------------------------------------
class Layer:
    def __init__(self, lid, name, w, h, image=None):
        self.id = lid
        self.name = name
        self.visible = True
        self.opacity = 1.0
        self.blend = "normal"
        self.locked = False
        self._image = fit_to_canvas(image, w, h) if image is not None else new_layer_image(w, h)
        self._pixmap = None
        self.saved_key = None

    # -- görüntü / pixmap önbelleği
    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = to_layer_format(value)
        self._pixmap = None

    def get_pixmap(self):
        if self._pixmap is None:
            self._pixmap = QPixmap.fromImage(self._image)
        return self._pixmap

    def refresh_pixmap(self):
        self._pixmap = QPixmap.fromImage(self._image)

    def invalidate(self):
        self._pixmap = None

    # -- diske yazma takibi
    def touch(self):
        self.saved_key = None

    def mark_saved(self):
        self.saved_key = self._image.cacheKey()

    def is_dirty(self):
        return self.saved_key is None or self.saved_key != self._image.cacheKey()

    def composition_mode(self):
        return blend_to_mode(self.blend)

    def meta(self):
        return {"id": self.id, "name": self.name, "visible": self.visible,
                "opacity": round(self.opacity, 4), "blend": self.blend, "locked": self.locked}

    def apply_meta(self, d):
        self.name = d.get("name", self.name)
        self.visible = bool(d.get("visible", True))
        self.opacity = float(d.get("opacity", 1.0))
        self.blend = d.get("blend", "normal")
        self.locked = bool(d.get("locked", False))


class LayerStack:
    """Alttan üste sıralı katman listesi."""

    def __init__(self, w, h, names=("Eskiz", "Çizim", "5", "4", "3", "2", "1"), active="Çizim"):
        self.w = w
        self.h = h
        self.layers = []
        self._next_id = 1
        self.active = None
        for n in names:
            self.add(n)
        self.active = self.by_name(active) or self.layers[-1]

    # -- erişim
    def by_id(self, lid):
        for l in self.layers:
            if l.id == lid:
                return l
        return None

    def by_name(self, name):
        for l in self.layers:
            if l.name == name:
                return l
        return None

    def index_of(self, layer):
        return self.layers.index(layer)

    def unique_name(self, name, ignore=None):
        existing = {l.name for l in self.layers if l is not ignore}
        if name not in existing:
            return name
        i = 2
        while f"{name} {i}" in existing:
            i += 1
        return f"{name} {i}"

    # -- değişiklik
    def add(self, name=None, index=None, lid=None, image=None):
        if lid is None:
            lid = self._next_id
        self._next_id = max(self._next_id, lid + 1)
        name = self.unique_name(name or f"Katman {lid}")
        layer = Layer(lid, name, self.w, self.h, image)
        if index is None or index >= len(self.layers):
            self.layers.append(layer)
        else:
            self.layers.insert(max(0, index), layer)
        return layer

    def remove(self, layer):
        if len(self.layers) <= 1 or layer not in self.layers:
            return False
        i = self.layers.index(layer)
        self.layers.pop(i)
        if self.active is layer:
            self.active = self.layers[min(i, len(self.layers) - 1)]
        return True

    def duplicate(self, layer):
        i = self.index_of(layer)
        new = self.add(layer.name + " kopya", index=i + 1, image=layer.image.copy())
        new.visible, new.opacity, new.blend = layer.visible, layer.opacity, layer.blend
        new.touch()
        return new

    def merge_down(self, layer):
        i = self.index_of(layer)
        if i <= 0:
            return None
        below = self.layers[i - 1]
        if layer.visible:
            p = QPainter(below.image)
            p.setOpacity(layer.opacity)
            p.setCompositionMode(layer.composition_mode())
            p.drawImage(0, 0, layer.image)
            p.end()
        below.invalidate()
        below.touch()
        self.layers.pop(i)
        self.active = below
        return below

    def move(self, layer, delta):
        i = self.index_of(layer)
        j = i + delta
        if j < 0 or j >= len(self.layers):
            return False
        self.layers[i], self.layers[j] = self.layers[j], self.layers[i]
        return True

    def resize(self, w, h):
        self.w, self.h = w, h
        for l in self.layers:
            l.image = fit_to_canvas(l.image, w, h)
            l.touch()

    # -- meta / anlık görüntü
    def export_meta(self):
        return [l.meta() for l in self.layers]

    def import_meta(self, meta_list, active_id=None):
        """Yapıyı verilen meta'dan kurar (görüntüler boş başlar)."""
        self.layers = []
        self._next_id = 1
        for d in meta_list:
            l = self.add(d.get("name", "Katman"), lid=int(d["id"]))
            l.apply_meta(d)
        if not self.layers:
            self.add("Çizim")
        self.active = self.by_id(active_id) or self.layers[-1]

    def snapshot_full(self):
        return {"kind": "full",
                "layers": [(l.meta(), l.image.copy()) for l in self.layers],
                "active": self.active.id, "next": self._next_id}

    def restore_full(self, snap):
        self.layers = []
        for meta, img in snap["layers"]:
            l = Layer(meta["id"], meta["name"], self.w, self.h, img)
            l.apply_meta(meta)
            l.touch()
            self.layers.append(l)
        self._next_id = max(self._next_id, snap.get("next", 1))
        self.active = self.by_id(snap["active"]) or self.layers[-1]


def meta_signature(meta):
    return tuple((m["id"], bool(m.get("visible", True)), round(float(m.get("opacity", 1.0)), 3),
                  m.get("blend", "normal")) for m in meta)


# ---------------------------------------------------------------------------
# Sayfa dosyaları (önbellek klasörü)   -  n = 1 tabanlı sayfa numarası
# ---------------------------------------------------------------------------
def layer_path(cache_dir, page_idx, lid):
    return os.path.join(cache_dir, f"s{page_idx + 1}_L{lid}.png")


def page_files(cache_dir, n):
    out = []
    try:
        names = os.listdir(cache_dir)
    except OSError:
        return out
    for name in names:
        if (name == f"s{n}.png" or name == f"s{n}_elements.json"
                or (name.startswith(f"s{n}_L") and name.endswith(".png"))):
            out.append(name)
    return out


def delete_page_files(cache_dir, n):
    for name in page_files(cache_dir, n):
        try:
            os.remove(os.path.join(cache_dir, name))
        except OSError:
            pass


def copy_page_files(cache_dir, src_n, dst_n):
    delete_page_files(cache_dir, dst_n)
    for name in page_files(cache_dir, src_n):
        suffix = name[len(f"s{src_n}"):]
        shutil.copyfile(os.path.join(cache_dir, name), os.path.join(cache_dir, f"s{dst_n}{suffix}"))


def reorder_page_files(cache_dir, order):
    """order[k] = eski 1-tabanlı sayfa no; yeni konum k+1'e taşınır."""
    for new_n, old_n in enumerate(order, start=1):
        for name in page_files(cache_dir, old_n):
            suffix = name[len(f"s{old_n}"):]
            os.replace(os.path.join(cache_dir, name), os.path.join(cache_dir, f"tmp_{new_n}{suffix}"))
    for name in os.listdir(cache_dir):
        if name.startswith("tmp_"):
            rest = name[4:]
            n_str = rest.split("_")[0].split(".")[0]
            suffix = rest[len(n_str):]
            os.replace(os.path.join(cache_dir, name), os.path.join(cache_dir, f"s{n_str}{suffix}"))


def save_page_layers(cache_dir, page_idx, stack, force=False):
    """Değişen (veya dosyası olmayan) katmanları diske yazar."""
    for l in stack.layers:
        path = layer_path(cache_dir, page_idx, l.id)
        if force or l.is_dirty() or not os.path.isfile(path):
            if not l.image.save(path, "PNG"):
                raise IOError(f"Katman kaydedilemedi: {path}")
            l.mark_saved()


def load_page_layers(cache_dir, page_idx, stack, legacy_layer_name="Çizim"):
    """Sayfanın katman görüntülerini yükler. Katman dosyası yoksa eski s{n}.png'yi
    (tek parça çizim) 'Çizim' katmanına alır."""
    any_found = False
    for l in stack.layers:
        path = layer_path(cache_dir, page_idx, l.id)
        img = QImage(path) if os.path.isfile(path) else QImage()
        if not img.isNull():
            any_found = True
            l.image = fit_to_canvas(img, stack.w, stack.h)
            l.mark_saved()
        else:
            l.image = new_layer_image(stack.w, stack.h)
            l.mark_saved()
    if not any_found:
        legacy = os.path.join(cache_dir, f"s{page_idx + 1}.png")
        if os.path.isfile(legacy):
            img = QImage(legacy)
            if not img.isNull():
                target = stack.by_name(legacy_layer_name) or stack.layers[-1]
                target.image = fit_to_canvas(img, stack.w, stack.h)
                target.touch()


def composite_images(items, w, h, bg=None):
    """items: [(QImage, visible, opacity, blend)] alttan üste."""
    out = QImage(w, h, LAYER_FORMAT)
    if bg is None:
        out.fill(Qt.transparent)
    else:
        out.fill(bg)
    p = QPainter(out)
    for img, visible, opacity, blend in items:
        if not visible or img is None or img.isNull():
            continue
        p.setOpacity(opacity)
        p.setCompositionMode(blend_to_mode(blend))
        p.drawImage(0, 0, img)
    p.end()
    return out


def composite_page(cache_dir, page_idx, meta, w, h, bg=None):
    """Önbellekteki katman dosyalarından sayfayı birleştirir. İş parçacığında güvenle çağrılabilir
    (yalnızca QImage/QPainter kullanır)."""
    items = []
    found = False
    for m in meta:
        path = layer_path(cache_dir, page_idx, m["id"])
        if not os.path.isfile(path):
            continue
        found = True
        if not m.get("visible", True):
            continue
        img = QImage(path)
        if img.isNull():
            continue
        items.append((img, True, float(m.get("opacity", 1.0)), m.get("blend", "normal")))
    if not found:
        legacy = os.path.join(cache_dir, f"s{page_idx + 1}.png")
        if os.path.isfile(legacy):
            img = QImage(legacy)
            if not img.isNull():
                items.append((img, True, 1.0, "normal"))
    return composite_images(items, w, h, bg)


def page_signature(cache_dir, page_idx, meta):
    """Sayfanın dosya değişim imzası (önbellek anahtarı)."""
    parts = []
    for m in meta:
        try:
            parts.append(os.stat(layer_path(cache_dir, page_idx, m["id"])).st_mtime_ns)
        except OSError:
            parts.append(0)
    try:
        parts.append(os.stat(os.path.join(cache_dir, f"s{page_idx + 1}.png")).st_mtime_ns)
    except OSError:
        parts.append(0)
    return (tuple(parts), meta_signature(meta))


# ---------------------------------------------------------------------------
# DrawingArea için karışım sınıfı (mixin)
# ---------------------------------------------------------------------------
class LayerAreaMixin:
    MAX_UNDO_REDO_STEPS = 30

    # -- başlatma
    def initLayers(self, w, h):
        self.layer_stack = LayerStack(w, h)
        self._painted_count = 0
        self._actively_modifying = False

    # -- uyumluluk özellikleri: mevcut kod self.image / current_layer_name kullanır
    @property
    def image(self):
        return self.layer_stack.active.image

    @image.setter
    def image(self, value):
        self.layer_stack.active.image = value

    @property
    def current_layer_name(self):
        return self.layer_stack.active.name

    @current_layer_name.setter
    def current_layer_name(self, name):
        self.setActiveLayer(name=name)

    @property
    def layer_order(self):
        return [l.name for l in self.layer_stack.layers]

    # -- durum
    def isLayerEditable(self):
        l = self.layer_stack.active
        return l.visible and not l.locked

    def syncPaintedCount(self):
        self._painted_count = len(self.drawing_elements)

    def _append_live(self, element):
        """Raster'a zaten canlı çizilmiş bir kaydı günlüğe ekler (tekrar çizilmez)."""
        self.drawing_elements.append(element)
        self._painted_count = len(self.drawing_elements)

    def _structure_changed(self):
        if self.parent():
            self.parent().is_project_modified = True
        self.update()
        self.layersChanged.emit()
        self.contentChanged.emit()

    # -- görüntü / pixmap
    def commitImageToPixmap(self):
        layer = self.layer_stack.active
        layer.refresh_pixmap()
        layer.touch()
        self._actively_modifying = False

    def _paint_layers(self, painter, source_rect):
        st = self.layer_stack
        order = list(st.layers)
        if getattr(self, "force_active_layer_bottom", False) and st.active in order:
            order.remove(st.active)
            order.insert(0, st.active)
        for layer in order:
            if not layer.visible:
                continue
            painter.save()
            painter.setOpacity(layer.opacity)
            painter.setCompositionMode(layer.composition_mode())
            if layer is st.active and (self._actively_modifying or layer._pixmap is None):
                painter.drawImage(source_rect, layer.image, source_rect)
            else:
                painter.drawPixmap(source_rect, layer.get_pixmap(), source_rect)
            painter.restore()

    # -- sayfa dosyaları
    def loadLayersFromCache(self, cache_dir, page_idx):
        load_page_layers(cache_dir, page_idx, self.layer_stack)
        for l in self.layer_stack.layers:
            l.invalidate()
        self._actively_modifying = False
        self.update()

    def saveLayersToCache(self, cache_dir, page_idx):
        save_page_layers(cache_dir, page_idx, self.layer_stack)

    def flattenCurrent(self, bg=None):
        st = self.layer_stack
        return composite_images([(l.image, l.visible, l.opacity, l.blend) for l in st.layers], st.w, st.h, bg)

    # -- geri al / yinele (yalnız değişen katmanı saklar, kopya sayısı düşük)
    def _snapshot(self, full):
        st = self.layer_stack
        if full:
            return st.snapshot_full()
        return {"kind": "layer", "id": st.active.id, "image": st.active.image.copy()}

    def _snapshot_like(self, snap):
        st = self.layer_stack
        if snap["kind"] == "full":
            return st.snapshot_full()
        layer = st.by_id(snap["id"])
        if layer is None:
            return {"kind": "layer", "id": snap["id"], "image": None}
        return {"kind": "layer", "id": layer.id, "image": layer.image.copy()}

    def saveStateForUndo(self, deep_copy=False, all_layers=False):
        if self.parent():
            self.parent().is_project_modified = True
        elements_copy = copy.deepcopy(self.drawing_elements) if deep_copy else self.drawing_elements[:]
        self.undo_stack.append((elements_copy, self._snapshot(deep_copy or all_layers)))
        if len(self.undo_stack) > self.MAX_UNDO_REDO_STEPS:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def _apply_history(self, source, target):
        if not source:
            return
        elements, snap = source.pop()
        current = self._snapshot_like(snap)
        target.append((self.drawing_elements, current))
        if len(target) > self.MAX_UNDO_REDO_STEPS:
            target.pop(0)
        self.drawing_elements = elements
        self._painted_count = len(elements)
        st = self.layer_stack
        if snap["kind"] == "full":
            st.restore_full(snap)
        else:
            layer = st.by_id(snap["id"])
            if layer is not None and snap["image"] is not None:
                layer.image = snap["image"]
                layer.touch()
        self._actively_modifying = False
        self.commitImageToPixmap()
        if hasattr(self, "onHistoryApplied"):
            self.onHistoryApplied()
        if self.parent():
            self.parent().is_project_modified = True
        self.update()
        self.layersChanged.emit()
        self.contentChanged.emit()

    def undo(self):
        self._apply_history(self.undo_stack, self.redo_stack)

    def redo(self):
        self._apply_history(self.redo_stack, self.undo_stack)

    # -- çizim kayıtlarını rasterlaştırma
    def _cached_b64_image(self, b64):
        key = (len(b64), b64[:40], b64[-40:])
        img = self.image_cache.get(key)
        if img is None:
            img = QImage()
            img.loadFromData(base64.b64decode(b64), "PNG")
            self.image_cache[key] = img
        return img

    def updateImageFromElements(self, full=False):
        """Varsayılan: yalnızca henüz rasterlaştırılmamış (yeni) kayıtları ilgili katmana çizer.
        full=True: tüm kayıtları yeniden çizer (renk değiştirme gibi işlemler için)."""
        elems = self.drawing_elements if full else self.drawing_elements[self._painted_count:]
        if elems:
            self._render_elements(elems)
        self._painted_count = len(self.drawing_elements)
        self.commitImageToPixmap()
        self.update()
        self.contentChanged.emit()

    # -- katman işlemleri
    def setActiveLayer(self, layer_id=None, name=None):
        st = self.layer_stack
        target = st.by_id(layer_id) if layer_id is not None else st.by_name(name)
        if target is None or target is st.active:
            return
        self.commitImageToPixmap()
        st.active = target
        self.update()
        self.layersChanged.emit()

    def addLayer(self, name=None):
        self.saveStateForUndo(all_layers=True)
        st = self.layer_stack
        self.commitImageToPixmap()
        layer = st.add(name, index=st.index_of(st.active) + 1)
        st.active = layer
        self._structure_changed()
        return layer

    def removeLayer(self, layer=None):
        st = self.layer_stack
        layer = layer or st.active
        if len(st.layers) <= 1:
            return False
        self.saveStateForUndo(all_layers=True)
        ok = st.remove(layer)
        self._structure_changed()
        return ok

    def duplicateLayer(self, layer=None):
        st = self.layer_stack
        layer = layer or st.active
        self.saveStateForUndo(all_layers=True)
        new = st.duplicate(layer)
        st.active = new
        self._structure_changed()

    def mergeLayerDown(self, layer=None):
        st = self.layer_stack
        layer = layer or st.active
        if st.index_of(layer) <= 0:
            return False
        self.saveStateForUndo(all_layers=True)
        st.merge_down(layer)
        self.commitImageToPixmap()
        self._structure_changed()
        return True

    def moveLayer(self, layer, delta):
        st = self.layer_stack
        if not (0 <= st.index_of(layer) + delta < len(st.layers)):
            return False
        self.saveStateForUndo(all_layers=True)
        st.move(layer, delta)
        self._structure_changed()
        return True

    def renameLayer(self, layer, new_name):
        new_name = (new_name or "").strip()
        if not new_name or new_name == layer.name:
            return
        st = self.layer_stack
        new_name = st.unique_name(new_name, ignore=layer)
        old = layer.name
        for el in self.drawing_elements:
            if el.get("layer") == old:
                el["layer"] = new_name
        layer.name = new_name
        self._structure_changed()

    def setLayerVisible(self, layer, visible):
        layer.visible = bool(visible)
        self._structure_changed()

    def setLayerLocked(self, layer, locked):
        layer.locked = bool(locked)
        self.layersChanged.emit()

    def setLayerOpacity(self, layer, opacity):
        layer.opacity = max(0.0, min(1.0, float(opacity)))
        if self.parent():
            self.parent().is_project_modified = True
        self.update()
        self.contentChanged.emit()

    def setLayerBlend(self, layer, key):
        layer.blend = key
        if self.parent():
            self.parent().is_project_modified = True
        self.update()
        self.contentChanged.emit()

    def setLayerOrder(self, names_ordered):
        st = self.layer_stack
        by_name = {l.name: l for l in st.layers}
        new_list = [by_name[n] for n in names_ordered if n in by_name]
        for l in st.layers:
            if l not in new_list:
                new_list.append(l)
        st.layers = new_list
        self._structure_changed()

    def setLayerVisibility(self, layer_name, visible):
        l = self.layer_stack.by_name(layer_name)
        if l:
            self.setLayerVisible(l, visible)

    def clear(self):
        """Sayfadaki tüm katmanları temizler."""
        self.drawing_elements.clear()
        self._painted_count = 0
        self.undo_stack.clear()
        self.redo_stack.clear()
        if self.parent():
            self.parent().is_project_modified = True
        for l in self.layer_stack.layers:
            l.image = new_layer_image(self.layer_stack.w, self.layer_stack.h)
            l.touch()
        self.commitImageToPixmap()
        self.update()
        self.contentChanged.emit()


# ---------------------------------------------------------------------------
# Katman paneli
# ---------------------------------------------------------------------------
_PANEL_CSS = """
QFrame#layerPanel { background-color: #262626; border-left: 2px solid #555; }
QLabel { color: #ddd; background: transparent; }
QListWidget { background-color: #1e1e1e; border: 1px solid #444; border-radius: 6px; outline: none; color: #eee; }
QListWidget::item { border-bottom: 1px solid #2c2c2c; }
QListWidget::item:selected { background-color: #3a4a66; }
QPushButton { background-color: #333; color: #eee; border: 1px solid #555; border-radius: 6px; padding: 3px 6px; }
QPushButton:hover { background-color: #444; }
QPushButton:disabled { color: #777; border-color: #3a3a3a; }
QToolButton { background: transparent; border: none; }
QToolButton:hover { background-color: #444; border-radius: 4px; }
QComboBox { background-color: #333; color: #eee; border: 1px solid #555; border-radius: 6px; padding: 2px 6px; }
QComboBox QAbstractItemView { background-color: #333; color: #eee; selection-background-color: #556; }
QSlider::groove:horizontal { height: 4px; background: #555; border-radius: 2px; }
QSlider::handle:horizontal { background: #ddd; width: 12px; margin: -5px 0; border-radius: 6px; }
"""


class _LayerRow(QWidget):
    def __init__(self, layer, on_eye, on_lock):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(4, 2, 4, 2)
        h.setSpacing(3)
        self.eye = SvgIconButton(SVG_EYE_OPEN if layer.visible else SVG_EYE_CLOSED,
                                 "#eeeeee" if layer.visible else "#777777", size=28, icon_px=19)
        self.eye.setToolTip("Katmanı göster / gizle")
        self.eye.clicked.connect(lambda: on_eye(layer))
        self.lock = SvgIconButton(SVG_LOCK if layer.locked else SVG_UNLOCK,
                                  "#ffb347" if layer.locked else "#777777", size=28, icon_px=17)
        self.lock.setToolTip("Katmanı kilitle / kilidi aç")
        self.lock.clicked.connect(lambda: on_lock(layer))
        self.label = QLabel(layer.name)
        self.label.setStyleSheet("color: %s; font-size: 13px;" % ("#eeeeee" if layer.visible else "#777777"))
        h.addWidget(self.eye)
        h.addWidget(self.lock)
        h.addWidget(self.label, 1)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents, True)


class LayerEditDialog(QDialog):
    """Katmanı düzenle: ad, görünürlük, kilit, opaklık, karışım modu."""

    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Katmanı Düzenle")
        self.setMinimumWidth(320)
        self.setStyleSheet(_PANEL_CSS + "QDialog { background-color: #2b2b2b; } QLineEdit { background-color: #3a3a3a; "
                           "color: #eee; border: 1px solid #555; border-radius: 5px; padding: 3px 6px; } QCheckBox { color: #eee; }")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Katman adı"))
        self.name = QLineEdit(layer.name)
        self.name.selectAll()
        lay.addWidget(self.name)
        self.visible = QCheckBox("Görünür")
        self.visible.setChecked(layer.visible)
        self.locked = QCheckBox("Kilitli (çizilemez)")
        self.locked.setChecked(layer.locked)
        lay.addWidget(self.visible)
        lay.addWidget(self.locked)
        self.op_label = QLabel()
        lay.addWidget(self.op_label)
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(0, 100)
        self.opacity.setValue(int(round(layer.opacity * 100)))
        self.opacity.valueChanged.connect(lambda v: self.op_label.setText(f"Opaklık: {v}%"))
        self.op_label.setText(f"Opaklık: {self.opacity.value()}%")
        lay.addWidget(self.opacity)
        lay.addWidget(QLabel("Karışım modu"))
        self.blend = QComboBox()
        for key, label, _m in BLEND_MODES:
            self.blend.addItem(label, key)
        self.blend.setCurrentIndex(max(0, self.blend.findData(layer.blend)))
        lay.addWidget(self.blend)
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = QPushButton("İptal")
        ok = QPushButton("Tamam")
        ok.setDefault(True)
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)


class LayerPanel(QFrame):
    def __init__(self, area, parent=None):
        super().__init__(parent)
        self.setObjectName("layerPanel")
        self.area = area
        self._building = False
        self._refresh_pending = False
        self.setFixedWidth(230)
        self.setStyleSheet(_PANEL_CSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        title = QLabel("Katmanlar")
        title.setStyleSheet("font-weight: bold; font-size: 13px; color: #fff;")
        root.addWidget(title)

        self.list = QListWidget()
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list.currentRowChanged.connect(self._on_row_changed)
        self.list.itemDoubleClicked.connect(self._rename)
        root.addWidget(self.list, 1)

        self.opacity_label = QLabel("Opaklık: 100%")
        root.addWidget(self.opacity_label)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self._on_opacity)
        root.addWidget(self.opacity_slider)

        self.blend_combo = QComboBox()
        for key, label, _m in BLEND_MODES:
            self.blend_combo.addItem(label, key)
        self.blend_combo.currentIndexChanged.connect(self._on_blend)
        root.addWidget(self.blend_combo)

        row1 = QHBoxLayout()
        row2 = QHBoxLayout()
        self.btn_add = self._btn("+ Yeni", "Yeni katman (aktifin üstüne)", self._add)
        self.btn_edit = self._btn("Düzenle", "Katmanı düzenle: ad, görünürlük, kilit, opaklık, karışım", self._edit)
        self.btn_merge = self._btn("Birleştir", "Alttaki katmanla birleştir", self._merge)
        self.btn_del = self._btn("Sil", "Katmanı sil", self._delete)
        self.btn_up = self._btn("▲", "Yukarı taşı", lambda: self._move(+1))
        self.btn_down = self._btn("▼", "Aşağı taşı", lambda: self._move(-1))
        for b in (self.btn_add, self.btn_edit, self.btn_up):
            row1.addWidget(b)
        for b in (self.btn_merge, self.btn_del, self.btn_down):
            row2.addWidget(b)
        root.addLayout(row1)
        root.addLayout(row2)

        area.layersChanged.connect(self._schedule_refresh)
        self.refresh()

    def _btn(self, text, tip, fn):
        b = QPushButton(text)
        b.setToolTip(tip)
        b.setFixedHeight(26)
        b.clicked.connect(fn)
        return b

    # -- yenileme (sinyal içinden liste silmemek için ertelenir)
    def _schedule_refresh(self):
        if self._refresh_pending:
            return
        self._refresh_pending = True
        QTimer.singleShot(0, self._do_refresh)

    def _do_refresh(self):
        self._refresh_pending = False
        self.refresh()

    def refresh(self):
        st = self.area.layer_stack
        self._building = True
        try:
            self.list.clear()
            active_row = 0
            for row, layer in enumerate(reversed(st.layers)):
                item = QListWidgetItem()
                item.setData(Qt.UserRole, layer.id)
                item.setSizeHint(QSize(100, 32))
                self.list.addItem(item)
                self.list.setItemWidget(item, _LayerRow(layer, self._toggle_eye, self._toggle_lock))
                if layer is st.active:
                    active_row = row
            self.list.setCurrentRow(active_row)
            a = st.active
            self.opacity_slider.blockSignals(True)
            self.opacity_slider.setValue(int(round(a.opacity * 100)))
            self.opacity_slider.blockSignals(False)
            self.opacity_label.setText(f"Opaklık: {int(round(a.opacity * 100))}%")
            self.blend_combo.blockSignals(True)
            idx = self.blend_combo.findData(a.blend)
            self.blend_combo.setCurrentIndex(max(0, idx))
            self.blend_combo.blockSignals(False)
            n = len(st.layers)
            i = st.index_of(a)
            self.btn_del.setEnabled(n > 1)
            self.btn_merge.setEnabled(i > 0)
            self.btn_up.setEnabled(i < n - 1)
            self.btn_down.setEnabled(i > 0)
        finally:
            self._building = False

    # -- olaylar
    def _on_row_changed(self, row):
        if self._building or row < 0:
            return
        item = self.list.item(row)
        if item is not None:
            self.area.setActiveLayer(layer_id=item.data(Qt.UserRole))

    def _toggle_eye(self, layer):
        self.area.setLayerVisible(layer, not layer.visible)

    def _toggle_lock(self, layer):
        self.area.setLayerLocked(layer, not layer.locked)

    def _on_opacity(self, v):
        if self._building:
            return
        self.opacity_label.setText(f"Opaklık: {v}%")
        self.area.setLayerOpacity(self.area.layer_stack.active, v / 100.0)

    def _on_blend(self, _i):
        if self._building:
            return
        self.area.setLayerBlend(self.area.layer_stack.active, self.blend_combo.currentData())

    def _rename(self, item):
        layer = self.area.layer_stack.by_id(item.data(Qt.UserRole))
        if layer is not None:
            self._edit_layer(layer)

    def _edit(self):
        self._edit_layer(self.area.layer_stack.active)

    def _edit_layer(self, layer):
        dlg = LayerEditDialog(layer, self)
        if dlg.exec_() != QDialog.Accepted:
            return
        self.area.renameLayer(layer, dlg.name.text())
        layer.visible = dlg.visible.isChecked()
        layer.locked = dlg.locked.isChecked()
        layer.opacity = dlg.opacity.value() / 100.0
        layer.blend = dlg.blend.currentData()
        self.area._structure_changed()

    def _add(self):
        self.area.addLayer()

    def _merge(self):
        self.area.mergeLayerDown()

    def _delete(self):
        st = self.area.layer_stack
        if len(st.layers) <= 1:
            return
        r = QMessageBox.question(self, "Katmanı Sil", f"'{st.active.name}' katmanı tüm kareler için silinsin mi?",
                                 QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if r == QMessageBox.Yes:
            self.area.removeLayer()

    def _move(self, delta):
        self.area.moveLayer(self.area.layer_stack.active, delta)


def move_page_files(cache_dir, src_n, dst_n):
    """src sayfasının tüm dosyalarını dst numarasına taşır (dst önce temizlenir)."""
    delete_page_files(cache_dir, dst_n)
    for name in page_files(cache_dir, src_n):
        suffix = name[len(f"s{src_n}"):]
        os.replace(os.path.join(cache_dir, name), os.path.join(cache_dir, f"s{dst_n}{suffix}"))
