# Kavram - Çizim tuvali (DrawingArea)
from drawing_common import *
from drawing_widgets import *
from drawing_layers import *
from drawing_select import SelectionMixin
from drawing_points import PointModeMixin


class DrawingArea(PointModeMixin, SelectionMixin, LayerAreaMixin, QWidget):
    layersChanged = pyqtSignal()   # katman yapısı / aktif katman değişti
    contentChanged = pyqtSignal()  # kare içeriği değişti (küçük resim, soğan zarı)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StaticContents)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.modified = False
        self.drawing = False
        self.lastPoint = QPoint()
        self.last_widget_pos = QPoint() 
        self.last_pressure = 1.0

        # --- EKSİK NİTELİKLER EKLENDİ ---
        self.zoom_factor = 1.0
        self.view_offset = QPoint(0, 0)
        self.panning = False
        self.last_pan_pos = QPoint()

        # TUVAL BOYUTU DİNAMİKLEŞTİRİLDİ
        canvas_w = self.parent().canvas_width if self.parent() and hasattr(self.parent(), 'canvas_width') else 1100
        canvas_h = self.parent().canvas_height if self.parent() and hasattr(self.parent(), 'canvas_height') else 600

        # Katman sistemi: her katmanın kendi görüntüsü var; self.image = aktif katman (bkz. drawing_layers.py)
        self.initLayers(canvas_w, canvas_h)
        self.initSelection()
        self.initPoints()

        # Animasyon bağlantıları (drawing_animation.py doldurur)
        self.playback_frame = None       # oynatma sırasında gösterilen hazır kare (QImage)
        self.playback_stop_cb = None
        self.onion_provider = None       # () -> [(QImage, opaklık), ...]

        # Referans görsel değişkenleri (sayfaya özel)
        # Yeni sistem: sadece 1 referans
        self.reference_image = None          # {'id': int, 'image': QImage, 'offset': QPoint, 'display_size': QSize, 'visible': bool}
        self._reference_scaled_cache = {}   # Önbellek (id, width, height) -> scaled QImage

        self.placing_reference = False         # yerleştirme modunda mı?


        self.image_cache = {}

        self.mirror_line_x = canvas_w // 2
        self.mirror_line_y = canvas_h // 2
        self.dragging_mirror_line = False

        self.drawing_elements = []
        
        self.undo_stack = []
        self.redo_stack = []

        self.force_active_layer_bottom = False

        self.text_input_widget = ResizableTextEdit(self)
        self.text_input_widget.hide()
        self.text_input_widget.finished.connect(self.addTextToDrawing)

        self.original_image_for_placement = None
        self.current_image_display_size = QSize(0, 0)
        self.image_placement_offset = QPoint(0, 0)
        self.dragging_image = False
        self.last_drag_pos = QPoint()

        self.current_stroke_points = []
        self.current_stroke_pen_info = []
        self.current_mix_index = 0
        self.stroke_length_accumulator = 0.0

        self.polyline_points = []
        self.hovered_poly_point_index = -1
        self.dragging_poly_point_index = -1
        self.dragging_whole_polyline = False
        self.last_poly_drag_pos = QPoint()

        self.curve_points = []

        self.lazy_mouse_pos = None  
        self.lazy_damping = 0.40    
        self.lazy_target_pos = None 
        self.lazy_velocity = QPointF(0, 0)  

        self.alt_permanent_pan_mode = False  
        self.alt_held = False                

        # Referans katman konumu: 0 üstte, 1 altta
        self.reference_layer_position = 0

    def clearImageCache(self):
        """Görsel önbelleğini temizler (bellek sızıntısını önlemek için)."""
        self.image_cache.clear()

    def calculateMixColor(self, x, y, step_accum, mix_colors, mix_mode, mix_angle, sequential_idx=0):
        if not mix_colors:
            return QColor(0,0,0)
        num_colors = len(mix_colors)
        if num_colors == 1:
            return mix_colors[0]

        def lerp(c1, c2, frac):
            return QColor(
                int(c1.red() + (c2.red() - c1.red()) * frac),
                int(c1.green() + (c2.green() - c1.green()) * frac),
                int(c1.blue() + (c2.blue() - c1.blue()) * frac)
            )

        if mix_mode == 'random':
            return random.choice(mix_colors)
        elif mix_mode == 'sequential':
            return mix_colors[int(sequential_idx) % num_colors]
        elif mix_mode == 'gradient':
            angle_rad = math.radians(mix_angle)
            proj = x * math.cos(angle_rad) + y * math.sin(angle_rad)
            idx = int(abs(proj) / 100.0) % num_colors
            return mix_colors[idx]
        elif mix_mode == 'smooth':
            transition_length = 200.0
            pos = step_accum / transition_length
            idx1 = int(pos) % num_colors
            idx2 = (idx1 + 1) % num_colors
            frac = pos - int(pos)
            return lerp(mix_colors[idx1], mix_colors[idx2], frac)
        elif mix_mode == 'harman':
            freq = 0.15
            noise = (math.sin(x * freq) + math.cos(y * freq) + math.sin((x + y) * freq * 0.5)) / 3.0
            noise = max(0.0, min(1.0, (noise + 1.0) / 2.0 + random.uniform(-0.05, 0.05)))
            scaled_noise = noise * (num_colors - 1)
            idx1 = int(scaled_noise)
            idx2 = min(num_colors - 1, idx1 + 1)
            return lerp(mix_colors[idx1], mix_colors[idx2], scaled_noise - idx1)
        elif mix_mode == 'gradient_soft':
            transition_length = 500.0
            pos = (step_accum / transition_length) % 1.0
            scaled_pos = pos * (num_colors - 1)
            idx1 = int(scaled_pos)
            idx2 = min(num_colors - 1, idx1 + 1)
            return lerp(mix_colors[idx1], mix_colors[idx2], scaled_pos - idx1)
        elif mix_mode == 'marble':
            freq1, freq2 = 0.03, 0.015
            noise = math.sin(x * freq1 + math.cos(y * freq1)) + math.sin(y * freq2)
            noise = (noise + 2.0) / 4.0
            noise = max(0.0, min(1.0, noise))
            scaled_noise = noise * (num_colors - 1)
            idx1 = int(scaled_noise)
            idx2 = min(num_colors - 1, idx1 + 1)
            return lerp(mix_colors[idx1], mix_colors[idx2], scaled_noise - idx1)
        elif mix_mode == 'splatter':
            if random.random() > 0.8:
                return random.choice(mix_colors)
            return mix_colors[0]
        elif mix_mode == 'wave':
            wave = (math.sin(step_accum * 0.05) + 1.0) / 2.0
            scaled_wave = wave * (num_colors - 1)
            idx1 = int(scaled_wave)
            idx2 = min(num_colors - 1, idx1 + 1)
            return lerp(mix_colors[idx1], mix_colors[idx2], scaled_wave - idx1)
        elif mix_mode == 'pixel':
            return mix_colors[random.randint(0, num_colors - 1)]
        elif mix_mode == 'sponge':
            block_size = 15
            bx, by = int(x / block_size), int(y / block_size)
            seed = (bx * 73856093 ^ by * 19349663)
            return mix_colors[seed % num_colors]
        elif mix_mode == 'radial':
            cx, cy = self.mirror_line_x, self.mirror_line_y
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            pos = (dist / 300.0) % 1.0
            scaled_pos = pos * (num_colors - 1)
            idx1 = int(scaled_pos)
            idx2 = min(num_colors - 1, idx1 + 1)
            return lerp(mix_colors[idx1], mix_colors[idx2], scaled_pos - idx1)
        elif mix_mode == 'mist':
            freq = 0.08
            noise = (math.sin(x * freq) * math.cos(y * freq) + 1.0) / 2.0
            noise = max(0.0, min(1.0, noise + random.uniform(-0.1, 0.1)))
            scaled_noise = noise * (num_colors - 1)
            idx1 = int(scaled_noise)
            idx2 = min(num_colors - 1, idx1 + 1)
            return lerp(mix_colors[idx1], mix_colors[idx2], scaled_noise - idx1)
        else:
            return mix_colors[0]

    def enterEvent(self, event):
        self.setCursor(Qt.CrossCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def toCanvas(self, widget_pos):
        center_offset_x = 0
        center_offset_y = 0
        if self.width() > self.image.width() * self.zoom_factor:
            center_offset_x = (self.width() - self.image.width() * self.zoom_factor) / 2
        if self.height() > self.image.height() * self.zoom_factor:
            center_offset_y = (self.height() - self.image.height() * self.zoom_factor) / 2

        final_offset = self.view_offset + QPoint(int(center_offset_x), int(center_offset_y))
        return (widget_pos - final_offset) / self.zoom_factor

    def resizeEvent(self, event):
        self.mirror_line_x = self.image.width() // 2
        self.mirror_line_y = self.image.height() // 2
        super().resizeEvent(event)

    def generateSmoothCurvePath(self, points):
        if len(points) < 2:
            return QPainterPath()
        path = QPainterPath()
        path.moveTo(points[0])
        if len(points) == 2:
            path.lineTo(points[1])
            return path
        for i in range(len(points) - 1):
            p0 = points[i - 1] if i > 0 else points[i]
            p1 = points[i]
            p2 = points[i + 1]
            p3 = points[i + 2] if i < len(points) - 2 else points[i + 1]
            c1 = p1 + (p2 - p0) / 6.0
            c2 = p2 - (p3 - p1) / 6.0
            path.cubicTo(c1, c2, p2)
        return path

    def getMirroredPoint(self, p):
        parent = self.parent()
        if not parent:
            return p
        if parent.mirror_axis == 'vertical':
            return QPoint(int(self.mirror_line_x - (p.x() - self.mirror_line_x)), int(p.y()))
        else:
            return QPoint(int(p.x()), int(self.mirror_line_y - (p.y() - self.mirror_line_y)))

    def _get_scaled_reference(self, ref):
        """Önbellekten veya yeniden ölçekleyerek referans görselini döndür."""
        key = (ref['id'], ref['display_size'].width(), ref['display_size'].height())
        cached = self._reference_scaled_cache.get(key)
        if cached is not None and not cached.isNull():
            return cached
        scaled = ref['image'].scaled(ref['display_size'], Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._reference_scaled_cache[key] = scaled
        return scaled

    def _draw_reference(self, painter, parent, placing=False):
        """Referans görselini çizer. placing=True ise yerleştirme modunda tam opak çizer."""
        if self.reference_image is None:
            return
        painter.save()
        if not placing:
            transparency = max(0, min(95, int(getattr(parent, 'reference_transparency', 55)))) / 100.0
            painter.setOpacity(1.0 - transparency)
        else:
            painter.setOpacity(1.0)
        ref = self.reference_image
        if ref.get('visible', True) or placing:
            scaled = self._get_scaled_reference(ref)
            if scaled:
                painter.drawImage(ref['offset'], scaled)
        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1a1a1a"))
        painter.save()  # 1. save

        center_offset_x = 0
        center_offset_y = 0
        scaled_w = self.image.width() * self.zoom_factor
        scaled_h = self.image.height() * self.zoom_factor

        if self.width() > scaled_w:
            center_offset_x = (self.width() - scaled_w) / 2
        if self.height() > scaled_h:
            center_offset_y = (self.height() - scaled_h) / 2

        final_offset_x = self.view_offset.x() + center_offset_x
        final_offset_y = self.view_offset.y() + center_offset_y

        transform = QTransform()
        transform.translate(final_offset_x, final_offset_y)
        transform.scale(self.zoom_factor, self.zoom_factor)
        painter.setTransform(transform)

        parent = self.parent()

        # ---- ARKA PLAN RENGİ (EN ALTTA) ----
        if parent:
            painter.save()
            painter.fillRect(QRectF(0, 0, self.image.width(), self.image.height()), parent.background_color)
            painter.restore()
        else:
            painter.save()
            painter.fillRect(QRectF(0, 0, self.image.width(), self.image.height()), QColor("#333333"))
            painter.restore()

        # ---- OYNATMA: hazır kareyi göster, gerisini çizme ----
        if self.playback_frame is not None:
            painter.drawImage(0, 0, self.playback_frame)
            painter.restore()
            return

        # ---- REFERANS (ALTTA) ----
        if parent and not self.placing_reference and parent.global_reference_visible and self.reference_layer_position == 1:
            self._draw_reference(painter, parent, placing=False)

        # ---- ANA ÇİZİM (image) ----
        widget_rect = self.rect()
        inverted_transform, _ = transform.inverted()
        visible_rect_on_canvas = inverted_transform.mapRect(QRectF(widget_rect)).toRect()
        source_rect = visible_rect_on_canvas.intersected(self.image.rect())

        if not source_rect.isEmpty():
            self._paint_layers(painter, source_rect)
            # Soğan zarı (önceki/sonraki kareler): yalnızca ekranda, dışa aktarımda yok
            if self.onion_provider is not None:
                for onion_img, onion_opacity in self.onion_provider():
                    painter.save()
                    painter.setOpacity(onion_opacity)
                    painter.drawImage(source_rect, onion_img, source_rect)
                    painter.restore()

        self._paint_selection(painter)
        self._paint_points(painter)

        # ---- REFERANS (ÜSTTE) ----
        if parent and (self.placing_reference or (parent.global_reference_visible and self.reference_layer_position == 0)):
            self._draw_reference(painter, parent, placing=self.placing_reference)

        # ---- MİROR ÇİZGİSİ ----
        if parent and (parent.mirror_mode or self.dragging_mirror_line):
            painter.save()
            pen = QPen(QColor(100, 100, 100), 1 / self.zoom_factor, Qt.DashLine)
            if self.dragging_mirror_line:
                pen = QPen(QColor(255, 0, 0), 2 / self.zoom_factor, Qt.SolidLine)
            painter.setPen(pen)

            if parent.mirror_axis == 'vertical':
                line_pos = int(self.mirror_line_x)
                painter.drawLine(line_pos, visible_rect_on_canvas.top(), line_pos, visible_rect_on_canvas.bottom())
            else:
                line_pos = int(self.mirror_line_y)
                painter.drawLine(visible_rect_on_canvas.left(), line_pos, visible_rect_on_canvas.right(), line_pos)
            painter.restore()

        # Şekil Araçları Önizleme
        if parent and parent.current_tool_index in [37, 38] and self.drawing and len(self.current_stroke_points) >= 2:
            painter.save()
            pen_color, pen_width = parent.getCurrentPen()
            painter.setPen(QPen(pen_color, pen_width / self.zoom_factor, Qt.SolidLine))
            
            if parent.solid_fill_mode:
                if parent.eraser_mode:
                    painter.setBrush(Qt.NoBrush)
                else:
                    painter.setBrush(QBrush(QColor(pen_color.red(), pen_color.green(), pen_color.blue(), 100)))
            else:
                painter.setBrush(Qt.NoBrush)

            p1 = self.current_stroke_points[0]
            p2 = self.current_stroke_points[1]

            if parent.current_tool_index == 37: 
                rect = QRect(p1, p2).normalized()
                painter.drawRect(rect)
                if parent.mirror_mode:
                    m_p1 = self.getMirroredPoint(p1)
                    m_p2 = self.getMirroredPoint(p2)
                    m_rect = QRect(m_p1, m_p2).normalized()
                    painter.drawRect(m_rect)

            elif parent.current_tool_index == 38: 
                r = math.hypot(p2.x() - p1.x(), p2.y() - p1.y())
                painter.drawEllipse(p1, int(r), int(r))
                if parent.mirror_mode:
                    m_p1 = self.getMirroredPoint(p1)
                    painter.drawEllipse(m_p1, int(r), int(r))

            painter.restore()

        if self.isLayerEditable():
            if parent and not parent.polyline_mode and not parent.curve_mode and parent.current_tool_index not in [37, 38]:
                if self.current_stroke_points and len(self.current_stroke_points) > 2 and parent.solid_fill_mode and self.drawing:
                    painter.save()
                    if parent.eraser_mode:
                        painter.setBrush(Qt.NoBrush)
                    else:
                        fill_color = QColor(parent.pen_color.red(), parent.pen_color.green(), parent.pen_color.blue(), 100)
                        painter.setBrush(QBrush(fill_color))

                    painter.setPen(QPen(QColor(255, 255, 255, 150), 1, Qt.SolidLine))
                    painter.drawPolygon(QPolygon(self.current_stroke_points))

                    if parent.mirror_mode:
                        mirrored_poly = [self.getMirroredPoint(p) for p in self.current_stroke_points]
                        painter.drawPolygon(QPolygon(mirrored_poly))

                    painter.restore()

                elif self.current_stroke_points and len(self.current_stroke_points) > 1 and parent.current_tool_index != 36:
                    painter.save()
                    if parent.solid_fill_mode:
                        if parent.eraser_mode:
                             painter.setBrush(Qt.NoBrush)
                             painter.setPen(QPen(QColor(255, 255, 255, 150), 1 / self.zoom_factor, Qt.SolidLine))
                        else:
                            c = parent.pen_color
                            fill_color = QColor(c.red(), c.green(), c.blue(), 150)
                            painter.setBrush(QBrush(fill_color))
                            painter.setPen(QPen(c, 1 / self.zoom_factor, Qt.SolidLine))

                        painter.drawPolygon(QPolygon(self.current_stroke_points))
                        if parent.mirror_mode:
                            mirrored_poly = [self.getMirroredPoint(p) for p in self.current_stroke_points]
                            painter.drawPolygon(QPolygon(mirrored_poly))
                    painter.restore()

            if parent and (parent.polyline_mode or parent.curve_mode):
                active_points = self.polyline_points if parent.polyline_mode else self.curve_points
                if active_points:
                    painter.save()
                    if parent.eraser_mode:
                        poly_color = parent.background_color
                    elif len(parent.mix_colors) > 1:
                        poly_color = parent.mix_colors[0]
                    else:
                        poly_color = parent.pen_color

                    current_radius = parent.eraser_radius if parent.eraser_mode else parent.pen_radius

                    pen = QPen(poly_color, current_radius, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    painter.setPen(pen)
                    if len(active_points) > 1:
                        if parent.curve_mode:
                            path = self.generateSmoothCurvePath(active_points)
                            painter.setBrush(Qt.NoBrush)
                            painter.drawPath(path)
                            if parent.mirror_mode:
                                mirrored_pts = [self.getMirroredPoint(p) for p in active_points]
                                m_path = self.generateSmoothCurvePath(mirrored_pts)
                                painter.drawPath(m_path)
                        else:
                            if parent.current_tool_index == 36 and len(active_points) >= 2:
                                p1 = active_points[0]
                                p2 = active_points[-1]
                                painter.drawPolyline(QPolygon(active_points))
                                angle = math.atan2(active_points[-2].y() - p2.y(), active_points[-2].x() - p2.x())
                                arrow_len = current_radius * 3
                                p3 = QPoint(int(p2.x() + arrow_len * math.cos(angle + math.pi / 6)), int(p2.y() + arrow_len * math.sin(angle + math.pi / 6)))
                                p4 = QPoint(int(p2.x() + arrow_len * math.cos(angle - math.pi / 6)), int(p2.y() + arrow_len * math.sin(angle - math.pi / 6)))
                                painter.drawLine(p2, p3)
                                painter.drawLine(p2, p4)

                                if parent.mirror_mode:
                                    mirrored_pts = [self.getMirroredPoint(p) for p in active_points]
                                    painter.drawPolyline(QPolygon(mirrored_pts))
                                    mp2 = mirrored_pts[-1]
                                    mp_prev = mirrored_pts[-2]
                                    m_angle = math.atan2(mp_prev.y() - mp2.y(), mp_prev.x() - mp2.x())
                                    mp3 = QPoint(int(mp2.x() + arrow_len * math.cos(m_angle + math.pi / 6)), int(mp2.y() + arrow_len * math.sin(m_angle + math.pi / 6)))
                                    mp4 = QPoint(int(mp2.x() + arrow_len * math.cos(m_angle - math.pi / 6)), int(mp2.y() + arrow_len * math.sin(m_angle - math.pi / 6)))
                                    painter.drawLine(mp2, mp3)
                                    painter.drawLine(mp2, mp4)
                            else:
                                painter.drawPolyline(QPolygon(active_points))
                                if parent.mirror_mode:
                                    mirrored_pts = [self.getMirroredPoint(p) for p in active_points]
                                    painter.drawPolyline(QPolygon(mirrored_pts))

                    painter.setPen(Qt.NoPen)
                    radius = max(5, (current_radius + 2)) / self.zoom_factor
                    points_to_draw = [(p, False) for p in active_points]
                    if parent.mirror_mode:
                        for p in active_points:
                            points_to_draw.append((self.getMirroredPoint(p), True))
                    for i, (pt, is_mirrored) in enumerate(points_to_draw):
                        is_hovered = False
                        if not is_mirrored:
                             if i == self.hovered_poly_point_index:
                                 is_hovered = True
                        if is_hovered:
                            painter.setBrush(QColor(255, 0, 0))
                        else:
                            painter.setBrush(QColor(0, 255, 255) if not is_mirrored else QColor(0, 150, 150))
                        painter.drawEllipse(pt, radius, radius)
                    painter.restore()

        if self.original_image_for_placement and self.current_image_display_size.isValid():
            scaled_temp_image = self.original_image_for_placement.scaled(
                self.current_image_display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            final_pos = self.image_placement_offset

            if parent and parent.mirror_mode:
                painter.save()
                if parent.mirror_axis == 'vertical':
                    mirror_line_screen = self.mirror_line_x
                    painter.setClipRect(0, 0, int(mirror_line_screen) + 1, self.image.height())
                    painter.drawImage(final_pos, scaled_temp_image)

                    painter.setClipRect(int(mirror_line_screen), 0, self.image.width(), self.image.height())

                    mirrored_x = 2 * mirror_line_screen - final_pos.x() - scaled_temp_image.width()
                    mirrored_pos = QPoint(int(mirrored_x), final_pos.y())
                    mirrored_image = scaled_temp_image.mirrored(True, False)
                    painter.drawImage(mirrored_pos, mirrored_image)

                else:
                    mirror_line_screen = self.mirror_line_y
                    painter.setClipRect(0, 0, self.image.width(), int(mirror_line_screen) + 1)
                    painter.drawImage(final_pos, scaled_temp_image)

                    painter.setClipRect(0, int(mirror_line_screen), self.image.width(), self.image.height())

                    mirrored_y = 2 * mirror_line_screen - final_pos.y() - scaled_temp_image.height()
                    mirrored_pos = QPoint(final_pos.x(), int(mirrored_y))

                    mirrored_image = scaled_temp_image.mirrored(False, True)
                    painter.drawImage(mirrored_pos, mirrored_image)

                painter.restore()
            else:
                painter.drawImage(final_pos, scaled_temp_image)

        # Cursor preview (sadece parent varsa)
        if parent:
            if parent.eraser_mode and not parent.nav_button.isChecked():
                mouse_canvas = self.mapFromGlobal(QCursor.pos())
                if self.rect().contains(mouse_canvas):
                    painter.save()
                    painter.setPen(QPen(QColor(255, 255, 255), 0))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(mouse_canvas, 0, 0)
                    painter.restore()

            if parent.lazy_mouse_enabled and self.lazy_mouse_pos is not None:
                painter.save()

                transform = QTransform()
                transform.translate(final_offset_x, final_offset_y)
                transform.scale(self.zoom_factor, self.zoom_factor)
                painter.setTransform(transform)

                if self.lazy_target_pos is not None:
                    lazy_radius = parent.lazy_radius
                    painter.setPen(QPen(QColor(100, 200, 255, 150), 1 / self.zoom_factor, Qt.DashLine))
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(self.lazy_target_pos, lazy_radius, lazy_radius)

                    painter.setPen(QPen(QColor(255, 150, 0), 2 / self.zoom_factor)) 
                    painter.setBrush(QColor(255, 200, 100, 200))
                    painter.drawEllipse(self.lazy_mouse_pos, 5 / self.zoom_factor, 5 / self.zoom_factor)

                    painter.setPen(QPen(QColor(255, 150, 0, 100), 1 / self.zoom_factor, Qt.DotLine))
                    painter.drawLine(self.lazy_target_pos, self.lazy_mouse_pos)

                painter.restore()

        painter.restore()  # 1. restore

    def keyPressEvent(self, event):
        parent = self.parent()
        if not parent:
            super().keyPressEvent(event)
            return
        if parent.polyline_mode or parent.curve_mode:
            active_points = self.polyline_points if parent.polyline_mode else self.curve_points
            if event.key() == Qt.Key_Delete:
                if active_points:
                    active_points.pop()
                    self.hovered_poly_point_index = -1
                    self.update()
        super().keyPressEvent(event)

    def tabletEvent(self, event):
        if event.type() == QTabletEvent.TabletPress or event.type() == QTabletEvent.TabletMove:
            self.last_pressure = event.pressure()
        elif event.type() == QTabletEvent.TabletRelease:
            self.last_pressure = 1.0
        event.ignore()

    def startReferencePlacement(self, ref_image):
        if self.parent():
            self.parent().is_project_modified = True

        # Önceki referansı temizle (sadece bir tane)
        self.reference_image = None

        max_width = max(20, int(self.image.width() * 0.85))
        max_height = max(20, int(self.image.height() * 0.85))
        initial_size = ref_image.size().scaled(max_width, max_height, Qt.KeepAspectRatio)

        ref_id = 1
        if self.parent() and hasattr(self.parent(), 'next_reference_id'):
            ref_id = self.parent().next_reference_id
            self.parent().next_reference_id += 1
        else:
            ref_id = 1

        new_ref = {
            'id': ref_id,
            'image': ref_image.convertToFormat(QImage.Format_ARGB32),
            'offset': QPoint(
                max(0, (self.image.width() - initial_size.width()) // 2),
                max(0, (self.image.height() - initial_size.height()) // 2)
            ),
            'display_size': initial_size,
            'visible': True
        }
        self.reference_image = new_ref
        self.placing_reference = True
        self._reference_scaled_cache.clear()

        if self.parent():
            self.parent().nav_button.setChecked(False)
            self.parent().nav_button.updateStyle()
        self.setCursor(Qt.CrossCursor)
        self.update()

    def cancelReferencePlacement(self):
        self.placing_reference = False
        self.setCursor(Qt.ArrowCursor)
        self.updateImageFromElements()
        if self.parent():
            self.parent().updateButtonStyles()
        self.update()

    def mousePressEvent(self, event):
        parent = self.parent()
        if not parent:
            return
        if self.playback_frame is not None:
            if self.playback_stop_cb:
                self.playback_stop_cb()
            return
        if self.select_active and self.selectMousePress(event):
            return
        if self.point_active and self.ptMousePress(event):
            return
        canvas_pos_float = self.toCanvas(event.pos())
        canvas_pos = QPoint(int(canvas_pos_float.x()), int(canvas_pos_float.y()))

        is_o_mode = parent.nav_button.isChecked()

        if event.button() == Qt.LeftButton:
            pass
        elif event.button() == Qt.MidButton and is_o_mode and not parent.placing_image:
            self.panning = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return

        if self.alt_held and event.button() == Qt.LeftButton:
            pass

        if (event.modifiers() & Qt.ShiftModifier) and event.button() == Qt.LeftButton and is_o_mode:
            self.panning = True
            self.last_pan_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return

        layer_active = self.isLayerEditable()

        if parent.text_mode and layer_active and event.button() == Qt.LeftButton:
             self.text_input_widget.move(event.pos())
             self.text_input_widget.show()
             self.text_input_widget.setFocus()
             self.text_input_widget.clear()
             base_size = max(10, parent.pen_radius * 2)
             scaled_size = int(base_size * self.zoom_factor)
             self.text_input_widget.setFont(QFont("Arial", scaled_size))
             self.text_input_widget.updateGeometry() 
             return

        if parent.polyline_mode or parent.curve_mode:
            if not layer_active:
                return
            active_points = self.polyline_points if parent.polyline_mode else self.curve_points

            if (event.modifiers() & Qt.ControlModifier) and event.button() == Qt.LeftButton:
                self.dragging_whole_polyline = True
                self.last_poly_drag_pos = canvas_pos
                self.setCursor(Qt.SizeAllCursor)
                return
            if parent.is_c_pressed and event.button() == Qt.MiddleButton:
                self.dragging_whole_polyline = True
                self.last_poly_drag_pos = canvas_pos
                self.setCursor(Qt.SizeAllCursor)
                return
            if event.button() == Qt.LeftButton:
                active_points.append(canvas_pos)
                self.update()
                return
            elif event.button() == Qt.MidButton:
                if self.hovered_poly_point_index != -1 and not parent.is_c_pressed:
                    self.dragging_poly_point_index = self.hovered_poly_point_index
                    self.setCursor(Qt.ClosedHandCursor)
                return
            elif event.button() == Qt.RightButton:
                menu = QMenu(self)
                menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")

                finish_action = menu.addAction("Bitir (Enter)")
                menu.addSeparator()

                delete_last_action = menu.addAction("Delete Last Point")
                menu.addSeparator()
                reset_action = menu.addAction("Reset")
                action = menu.exec_(self.mapToGlobal(event.pos()))

                if action == finish_action:
                    self.finalizePolyline()
                elif action == delete_last_action:
                    if active_points:
                        active_points.pop()
                elif action == reset_action:
                    if parent.polyline_mode:
                        self.polyline_points = []
                    else:
                        self.curve_points = []
                self.update()
                return

        if event.button() == Qt.MiddleButton and not is_o_mode:
            if hasattr(parent, 'is_v_pressed') and parent.is_v_pressed:
                 self.dragging_mirror_line = True
                 self.last_pan_pos = event.pos()
                 self.setCursor(Qt.SizeHorCursor)
                 return

        if event.button() == Qt.RightButton and not parent.placing_image and not parent.polyline_mode and not parent.curve_mode:
            if self.rect().contains(event.pos()):
                if 0 <= canvas_pos.x() < self.image.width() and 0 <= canvas_pos.y() < self.image.height():
                    picked_color = self.image.pixelColor(canvas_pos)
                    menu = QMenu(self)
                    menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
                    info_action = QAction(create_svg_icon(SVG_UNDO_ICON, size=16, color=picked_color.name()), f"Selected Color: {picked_color.name()}", self)
                    info_action.setEnabled(False)
                    menu.addAction(info_action)
                    menu.addSeparator()
                    copy_action = menu.addAction(f"Copy Hex ({picked_color.name().upper()})")
                    change_action = menu.addAction("Change This Color")
                    delete_action = menu.addAction("Delete This Color (Remove)")
                    action = menu.exec_(self.mapToGlobal(event.pos()))
                    if action == copy_action:
                        clipboard = QApplication.clipboard()
                        clipboard.setText(picked_color.name().upper())
                    elif action == change_action or action == delete_action:
                        reply = QMessageBox.question(self, "Replacement Mode", "Apply to entire drawing (Global) or only connected area (Connected)?",
                                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                        mode = 'global' if reply == QMessageBox.Yes else 'connected'
                        if action == change_action:
                            dialog = CircleBrightnessDialog(initialColor=picked_color, parent=self)
                            dialog.move(self.mapToGlobal(event.pos()))
                            if dialog.exec_():
                                new_color = dialog.getSelectedColor()
                                self.replaceColor(picked_color, new_color, is_delete=False, mode=mode, pos=canvas_pos)
                        elif action == delete_action:
                            bg_col = parent.background_color
                            self.replaceColor(picked_color, bg_col, is_delete=True, mode=mode, pos=canvas_pos)
            return

        if self.placing_reference and event.button() == Qt.LeftButton:
            self.placing_reference = False
            if parent:
                parent.updateCurrentPageReferenceData()
            self.setCursor(Qt.ArrowCursor)
            self.updateImageFromElements()
            parent.updateButtonStyles()
            return

        if self.placing_reference and (event.button() == Qt.MiddleButton or event.button() == Qt.RightButton):
            self.dragging_image = True
            self.last_drag_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        if parent.placing_image and layer_active:
            if event.button() == Qt.LeftButton:
                if self.original_image_for_placement and self.current_image_display_size.isValid():
                    self.saveStateForUndo(deep_copy=True)

                    if parent.mirror_mode:
                        final_pos = self.image_placement_offset
                        orig_img = self.original_image_for_placement
                        scale_x = orig_img.width() / self.current_image_display_size.width()
                        scale_y = orig_img.height() / self.current_image_display_size.height()

                        if parent.mirror_axis == 'vertical':
                            mirror_line = self.mirror_line_x
                            rect_1 = QRect(final_pos, self.current_image_display_size)
                            clip_rect_1 = QRect(rect_1.x(), rect_1.y(), int(mirror_line - rect_1.x()) + 1, rect_1.height())
                            final_rect_1 = rect_1.intersected(clip_rect_1)

                            if final_rect_1.width() > 0 and final_rect_1.height() > 0:
                                off_x = (final_rect_1.x() - rect_1.x()) * scale_x
                                off_y = (final_rect_1.y() - rect_1.y()) * scale_y
                                cw = final_rect_1.width() * scale_x
                                ch = final_rect_1.height() * scale_y
                                cropped_1 = orig_img.copy(int(off_x), int(off_y), int(cw), int(ch))
                                b1 = QByteArray()
                                bu1 = QBuffer(b1)
                                bu1.open(QIODevice.WriteOnly)
                                cropped_1.save(bu1, "PNG")
                                b64_1 = base64.b64encode(b1.data()).decode('utf-8')
                                self.drawing_elements.append({
                                    "type": "image", "base64_data": b64_1,
                                    "position": [final_rect_1.x(), final_rect_1.y()],
                                    "original_width": cropped_1.width(), "original_height": cropped_1.height(),
                                    "current_width": final_rect_1.width(), "current_height": final_rect_1.height(),
                                    "layer": self.current_layer_name
                                })

                            scaled_w = self.current_image_display_size.width()
                            mirrored_x = 2 * mirror_line - final_pos.x() - scaled_w
                            mirrored_pos = QPoint(int(mirrored_x), final_pos.y())
                            rect_2 = QRect(mirrored_pos, self.current_image_display_size)
                            clip_rect_2 = QRect(int(mirror_line), rect_2.y(), 99999, rect_2.height())
                            final_rect_2 = rect_2.intersected(clip_rect_2)

                            if final_rect_2.width() > 0 and final_rect_2.height() > 0:
                                full_mirrored = orig_img.mirrored(True, False)
                                off_x_2 = (final_rect_2.x() - rect_2.x()) * scale_x
                                off_y_2 = (final_rect_2.y() - rect_2.y()) * scale_y
                                cw_2 = final_rect_2.width() * scale_x
                                ch_2 = final_rect_2.height() * scale_y
                                cropped_2 = full_mirrored.copy(int(off_x_2), int(off_y_2), int(cw_2), int(ch_2))
                                b2 = QByteArray()
                                bu2 = QBuffer(b2)
                                bu2.open(QIODevice.WriteOnly)
                                cropped_2.save(bu2, "PNG")
                                b64_2 = base64.b64encode(b2.data()).decode('utf-8')
                                self.drawing_elements.append({
                                    "type": "image", "base64_data": b64_2,
                                    "position": [final_rect_2.x(), final_rect_2.y()],
                                    "original_width": cropped_2.width(), "original_height": cropped_2.height(),
                                    "current_width": final_rect_2.width(), "current_height": final_rect_2.height(),
                                    "layer": self.current_layer_name
                                })
                        else:
                            mirror_line = self.mirror_line_y
                            rect_1 = QRect(final_pos, self.current_image_display_size)
                            clip_rect_1 = QRect(rect_1.x(), rect_1.y(), rect_1.width(), int(mirror_line - rect_1.y()) + 1)
                            final_rect_1 = rect_1.intersected(clip_rect_1)

                            if final_rect_1.height() > 0:
                                off_x = (final_rect_1.x() - rect_1.x()) * scale_x
                                off_y = (final_rect_1.y() - rect_1.y()) * scale_y
                                cw = final_rect_1.width() * scale_x
                                ch = final_rect_1.height() * scale_y
                                cropped_1 = orig_img.copy(int(off_x), int(off_y), int(cw), int(ch))
                                b1 = QByteArray()
                                bu1 = QBuffer(b1)
                                bu1.open(QIODevice.WriteOnly)
                                cropped_1.save(bu1, "PNG")
                                b64_1 = base64.b64encode(b1.data()).decode('utf-8')
                                self.drawing_elements.append({
                                    "type": "image", "base64_data": b64_1,
                                    "position": [final_rect_1.x(), final_rect_1.y()],
                                    "original_width": cropped_1.width(), "original_height": cropped_1.height(),
                                    "current_width": final_rect_1.width(), "current_height": final_rect_1.height(),
                                    "layer": self.current_layer_name
                                })

                            scaled_h = self.current_image_display_size.height()
                            mirrored_y = 2 * mirror_line - final_pos.y() - scaled_h
                            mirrored_pos = QPoint(final_pos.x(), int(mirrored_y))
                            rect_2 = QRect(mirrored_pos, self.current_image_display_size)
                            clip_rect_2 = QRect(rect_2.x(), int(mirror_line), rect_2.width(), 99999)
                            final_rect_2 = rect_2.intersected(clip_rect_2)

                            if final_rect_2.height() > 0:
                                full_mirrored = orig_img.mirrored(False, True)
                                off_x_2 = (final_rect_2.x() - rect_2.x()) * scale_x
                                off_y_2 = (final_rect_2.y() - rect_2.y()) * scale_y
                                cw_2 = final_rect_2.width() * scale_x
                                ch_2 = final_rect_2.height() * scale_y
                                cropped_2 = full_mirrored.copy(int(off_x_2), int(off_y_2), int(cw_2), int(ch_2))
                                b2 = QByteArray()
                                bu2 = QBuffer(b2)
                                bu2.open(QIODevice.WriteOnly)
                                cropped_2.save(bu2, "PNG")
                                b64_2 = base64.b64encode(b2.data()).decode('utf-8')
                                self.drawing_elements.append({
                                    "type": "image", "base64_data": b64_2,
                                    "position": [final_rect_2.x(), final_rect_2.y()],
                                    "original_width": cropped_2.width(), "original_height": cropped_2.height(),
                                    "current_width": final_rect_2.width(), "current_height": final_rect_2.height(),
                                    "layer": self.current_layer_name
                                })
                    else:
                        buffer = QByteArray()
                        buffer_io = QBuffer(buffer)
                        buffer_io.open(QIODevice.WriteOnly)
                        self.original_image_for_placement.save(buffer_io, "PNG")
                        base64_data = base64.b64encode(buffer.data()).decode('utf-8')
                        self.drawing_elements.append({
                            "type": "image", "base64_data": base64_data,
                            "position": [self.image_placement_offset.x(), self.image_placement_offset.y()],
                            "original_width": self.original_image_for_placement.width(), "original_height": self.original_image_for_placement.height(),
                            "current_width": self.current_image_display_size.width(), "current_height": self.current_image_display_size.height(),
                            "layer": self.current_layer_name
                        })

                    self.updateImageFromElements()
                    self.cancelImagePlacement()
                    parent.updateButtonStyles()
                return

            elif event.button() == Qt.MiddleButton or event.button() == Qt.RightButton:
                self.dragging_image = True
                self.last_drag_pos = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return

        elif event.button() == Qt.LeftButton and layer_active:
            self.saveStateForUndo(deep_copy=False)
            
            self.lastPoint = canvas_pos
            self.last_widget_pos = event.pos() 
            self.drawing = True
            
            self._actively_modifying = True

            if parent.lazy_mouse_enabled:
                self.lazy_mouse_pos = QPointF(canvas_pos)
                self.lazy_target_pos = QPointF(canvas_pos)
                self.lazy_velocity = QPointF(0, 0)

            if parent.current_tool_index in [37, 38]:
                self.current_stroke_points = [canvas_pos, canvas_pos]
                self.update()
                return

            if parent.eraser_mode:
                pen_color = QColor(0, 0, 0)
                pen_width = parent.eraser_radius
            else:
                pen_color, pen_width = parent.getCurrentPen()

            if parent.pen_pressure_enabled:
                sensitivity_multiplier = 1.0
                if parent.sensitivity_value != -1: 
                    sensitivity_multiplier = parent.sensitivity_value / 50.0

                adjusted_pressure = self.last_pressure * sensitivity_multiplier
                pen_width = max(1, pen_width * adjusted_pressure)

            self.current_stroke_points = [canvas_pos]
            self.current_mix_index = 0
            self.stroke_length_accumulator = 0.0

            if not parent.eraser_mode and len(parent.mix_colors) > 1:
                pen_color = self.calculateMixColor(canvas_pos.x(), canvas_pos.y(), self.stroke_length_accumulator, parent.mix_colors, parent.mix_mode, parent.mix_angle, self.current_mix_index)
                if parent.mix_mode == 'sequential':
                    self.current_mix_index += 1

            self.current_stroke_pen_info = [[pen_color, pen_width]]

            if not parent.solid_fill_mode:
                painter = QPainter(self.image)
                painter.setRenderHint(QPainter.Antialiasing)

                if parent.eraser_mode:
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)

                if parent.current_tool_index >= 6 and parent.current_tool_index != 36:
                    self.drawBrushStroke(painter, canvas_pos, canvas_pos, pen_color, pen_width, parent.current_tool_index)
                    if parent.mirror_mode:
                        mirrored_pos = self.getMirroredPoint(canvas_pos)
                        self.drawBrushStroke(painter, mirrored_pos, mirrored_pos, pen_color, pen_width, parent.current_tool_index)
                else:
                    painter.setPen(QPen(pen_color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                    painter.drawPoint(canvas_pos)
                    if parent.mirror_mode:
                        mirrored_pos = self.getMirroredPoint(canvas_pos)
                        painter.drawPoint(mirrored_pos)
                painter.end()

            self.update()

    def mouseMoveEvent(self, event):
        parent = self.parent()
        if not parent:
            return
        if self.select_active and self.selectMouseMove(event):
            return
        if self.point_active and self.ptMouseMove(event):
            return
        is_o_mode = parent.nav_button.isChecked()

        needs_full_update = False
        if parent.eraser_mode or parent.lazy_mouse_enabled or self.dragging_image or (self.panning and is_o_mode) or self.dragging_mirror_line or self.dragging_whole_polyline or self.placing_reference:
            needs_full_update = True
        elif parent.polyline_mode or parent.curve_mode or parent.mirror_mode:
            needs_full_update = True

        if needs_full_update:
            self.update()

        if self.panning and is_o_mode:
            delta = event.pos() - self.last_pan_pos
            self.view_offset += delta

            scaled_w = self.image.width() * self.zoom_factor
            scaled_h = self.image.height() * self.zoom_factor
            limit_x = max(self.width(), int(scaled_w)) + 200
            limit_y = max(self.height(), int(scaled_h)) + 200

            x = max(-limit_x, min(limit_x, self.view_offset.x()))
            y = max(-limit_y, min(limit_y, self.view_offset.y()))

            self.view_offset = QPoint(x, y)

            self.last_pan_pos = event.pos()
            self.update()
            return

        canvas_pos_float = self.toCanvas(event.pos())
        canvas_pos = QPoint(int(canvas_pos_float.x()), int(canvas_pos_float.y()))
        
        if parent.lazy_mouse_enabled:
            target_pos = QPointF(canvas_pos_float)
            self.lazy_target_pos = target_pos
            
            lazy_radius = parent.lazy_radius
            lazy_factor = parent.lazy_factor / 100.0  
            
            if self.lazy_mouse_pos is None:
                self.lazy_mouse_pos = QPointF(canvas_pos_float)
                self.lazy_velocity = QPointF(0, 0)
            
            if self.drawing:
                dx = target_pos.x() - self.lazy_mouse_pos.x()
                dy = target_pos.y() - self.lazy_mouse_pos.y()
                distance = math.sqrt(dx * dx + dy * dy)

                if distance > lazy_radius:
                    excess_distance = distance - lazy_radius
                    if distance > 0:
                        nx = dx / distance
                        ny = dy / distance
                    else:
                        nx, ny = 0, 0

                    self.lazy_velocity.setX(self.lazy_velocity.x() * (1 - self.lazy_damping) + nx * excess_distance * lazy_factor * 2)
                    self.lazy_velocity.setY(self.lazy_velocity.y() * (1 - self.lazy_damping) + ny * excess_distance * lazy_factor * 2)

                    new_x = self.lazy_mouse_pos.x() + self.lazy_velocity.x()
                    new_y = self.lazy_mouse_pos.y() + self.lazy_velocity.y()
                    self.lazy_mouse_pos = QPointF(new_x, new_y)
                else:
                    self.lazy_velocity.setX(self.lazy_velocity.x() * (1 - self.lazy_damping * 0.5))
                    self.lazy_velocity.setY(self.lazy_velocity.y() * (1 - self.lazy_damping * 0.5))

                canvas_pos = QPoint(int(self.lazy_mouse_pos.x()), int(self.lazy_mouse_pos.y()))
            else:
                self.lazy_mouse_pos = QPointF(canvas_pos_float)

        if self.dragging_mirror_line:
            if parent.mirror_axis == 'vertical':
                delta_x = event.pos().x() - self.last_pan_pos.x()
                self.mirror_line_x += delta_x / self.zoom_factor
            else:
                delta_y = event.pos().y() - self.last_pan_pos.y()
                self.mirror_line_y += delta_y / self.zoom_factor
            self.last_pan_pos = event.pos()
            self.update()
            return

        if self.dragging_whole_polyline:
            active_points = self.polyline_points if parent.polyline_mode else self.curve_points
            delta = canvas_pos - self.last_poly_drag_pos
            if parent.polyline_mode:
                self.polyline_points = [p + delta for p in active_points]
            else:
                self.curve_points = [p + delta for p in active_points]
            self.last_poly_drag_pos = canvas_pos
            self.update()
            return

        if parent.polyline_mode or parent.curve_mode:
            active_points = self.polyline_points if parent.polyline_mode else self.curve_points
            current_radius = parent.eraser_radius if parent.eraser_mode else parent.pen_radius

            if self.dragging_poly_point_index != -1:
                active_points[self.dragging_poly_point_index] = canvas_pos
                self.update()
            else:
                radius = max(5, current_radius + 5) / self.zoom_factor
                found = -1
                for i, pt in enumerate(active_points):
                    if (pt - canvas_pos).manhattanLength() < radius:
                        found = i
                        break
                if found != self.hovered_poly_point_index:
                    self.hovered_poly_point_index = found
                    self.update()
            if self.dragging_poly_point_index != -1:
                return

        if self.dragging_image and self.placing_reference:
            delta_widget = event.pos() - self.last_drag_pos
            delta_canvas = QPoint(
                int(round(delta_widget.x() / max(self.zoom_factor, 0.0001))),
                int(round(delta_widget.y() / max(self.zoom_factor, 0.0001)))
            )
            if self.reference_image is not None:
                self.reference_image['offset'] += delta_canvas
                self._reference_scaled_cache.clear()
            self.last_drag_pos = event.pos()
            self.update()
            event.accept()
            return

        if self.dragging_image:
            delta = event.pos() - self.last_drag_pos
            self.image_placement_offset += delta
            self.last_drag_pos = event.pos()
            self.applyImagePlacementBounds()
            self.update()
            event.accept()
            return

        if not self.isLayerEditable():
            return

        if (event.buttons() & Qt.LeftButton) and self.drawing and not parent.polyline_mode and not parent.curve_mode:
            
            if parent.current_tool_index in [37, 38]:
                if len(self.current_stroke_points) >= 2:
                    self.current_stroke_points[1] = canvas_pos
                    self.update()
                return

            if parent.current_tool_index == 36:
                return

            if parent.eraser_mode:
                pen_color = QColor(0, 0, 0)
                pen_width = parent.eraser_radius
            elif len(parent.mix_colors) > 1:
                pen_color = random.choice(parent.mix_colors) if parent.mix_mode == 'random' else parent.pen_color
                pen_width = parent.pen_radius
            else: 
                pen_color, pen_width = parent.getCurrentPen()

            if parent.pen_pressure_enabled:
                 sensitivity_multiplier = 1.0
                 if parent.sensitivity_value != -1:
                     sensitivity_multiplier = parent.sensitivity_value / 50.0
                 adjusted_pressure = self.last_pressure * sensitivity_multiplier
                 pen_width = max(1, pen_width * adjusted_pressure)

            if not self.current_stroke_points:
                self.current_stroke_points.append(canvas_pos)
                self.current_stroke_pen_info.append([pen_color, pen_width])
                self.lastPoint = canvas_pos
            else:
                last_point_in_stroke = self.current_stroke_points[-1]
                dx = canvas_pos.x() - last_point_in_stroke.x()
                dy = canvas_pos.y() - last_point_in_stroke.y()
                distance = math.sqrt(dx*dx + dy*dy)

                step_size = max(1, pen_width / 2.0)

                scatter_tools = [15, 18, 19, 20, 21, 22] 
                if parent.current_tool_index in scatter_tools:
                    step_size = max(15, pen_width * 1.5)
                elif parent.current_tool_index >= 6:
                    step_size = 2

                if not parent.solid_fill_mode:
                    painter = QPainter(self.image)
                    painter.setRenderHint(QPainter.Antialiasing)

                    if parent.eraser_mode:
                        painter.setCompositionMode(QPainter.CompositionMode_Clear)

                    if distance > step_size:
                        num_steps = int(distance / step_size)
                        for i in range(1, num_steps + 1):
                            interp_x = last_point_in_stroke.x() + (dx * i / num_steps)
                            interp_y = last_point_in_stroke.y() + (dy * i / num_steps)
                            interpolated_point = QPoint(int(interp_x), int(interp_y))

                            interp_color = pen_color
                            if not parent.eraser_mode and len(parent.mix_colors) > 1:
                                self.stroke_length_accumulator += step_size
                                interp_color = self.calculateMixColor(interp_x, interp_y, self.stroke_length_accumulator, parent.mix_colors, parent.mix_mode, parent.mix_angle, self.current_mix_index)
                                if parent.mix_mode == 'sequential':
                                    self.current_mix_index += 1

                            if parent.current_tool_index >= 6:
                                self.drawBrushStroke(painter, self.lastPoint, interpolated_point, interp_color, pen_width, parent.current_tool_index)
                                if parent.mirror_mode:
                                    mirrored_last = self.getMirroredPoint(self.lastPoint)
                                    mirrored_interp = self.getMirroredPoint(interpolated_point)
                                    self.drawBrushStroke(painter, mirrored_last, mirrored_interp, interp_color, pen_width, parent.current_tool_index)
                            else:
                                painter.setPen(QPen(interp_color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                                painter.drawLine(self.lastPoint, interpolated_point)
                                if parent.mirror_mode:
                                    mirrored_last = self.getMirroredPoint(self.lastPoint)
                                    mirrored_curr = self.getMirroredPoint(interpolated_point)
                                    painter.drawLine(mirrored_last, mirrored_curr)

                            self.current_stroke_points.append(interpolated_point)
                            self.current_stroke_pen_info.append([interp_color, pen_width])
                            self.lastPoint = interpolated_point

                    if parent.current_tool_index >= 6:
                        self.drawBrushStroke(painter, self.lastPoint, canvas_pos, pen_color, pen_width, parent.current_tool_index)
                        if parent.mirror_mode:
                            mirrored_last = self.getMirroredPoint(self.lastPoint)
                            mirrored_curr = self.getMirroredPoint(canvas_pos)
                            self.drawBrushStroke(painter, mirrored_last, mirrored_curr, pen_color, pen_width, parent.current_tool_index)
                    else:
                        painter.setPen(QPen(pen_color, pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                        painter.drawLine(self.lastPoint, canvas_pos)
                        if parent.mirror_mode:
                            mirrored_last = self.getMirroredPoint(self.lastPoint)
                            mirrored_curr = self.getMirroredPoint(canvas_pos)
                            painter.drawLine(mirrored_last, mirrored_curr)

                    painter.end()

                self.current_stroke_points.append(canvas_pos)
                self.current_stroke_pen_info.append([pen_color, pen_width])
                self.lastPoint = canvas_pos

                if parent.solid_fill_mode or needs_full_update:
                    self.update()
                else:
                    padding = int((pen_width * self.zoom_factor) + 100)
                    min_x = min(self.last_widget_pos.x(), event.pos().x()) - padding
                    min_y = min(self.last_widget_pos.y(), event.pos().y()) - padding
                    max_x = max(self.last_widget_pos.x(), event.pos().x()) + padding
                    max_y = max(self.last_widget_pos.y(), event.pos().y()) + padding
                    update_rect = QRect(min_x, min_y, max_x - min_x, max_y - min_y)
                    self.update(update_rect)

                self.last_widget_pos = event.pos()

    def createSolidFill(self, points_to_draw, is_mirrored_shape=False):
        parent = self.parent()
        if not parent:
            return
        if not points_to_draw or len(points_to_draw) < 3:
            return

        if parent.eraser_mode:
            final_fill_color = QColor(0, 0, 0)
        elif len(self.current_stroke_pen_info) > 0 and len(parent.mix_colors) > 1:
            final_fill_color = self.current_stroke_pen_info[-1][0]
        else:
            final_fill_color = parent.pen_color

        min_x = min(p.x() for p in points_to_draw)
        max_x = max(p.x() for p in points_to_draw)
        min_y = min(p.y() for p in points_to_draw)
        max_y = max(p.y() for p in points_to_draw)
        w = max(1, max_x - min_x)
        h = max(1, max_y - min_y)

        path = QPainterPath()
        path.moveTo(points_to_draw[0])
        for p in points_to_draw[1:]:
            path.lineTo(p)
        path.closeSubpath()

        painter = QPainter(self.image)
        painter.setRenderHint(QPainter.Antialiasing)

        if parent.eraser_mode:
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(Qt.black))
            painter.drawPath(path)
            painter.end()
            element_data = {
                "type": "stroke", "points": [[p.x(), p.y()] for p in points_to_draw],
                "color": [0, 0, 0, 0],
                "width": 1, "pressure_enabled": False, "is_solid_fill": True, "is_eraser": True,
                "layer": self.current_layer_name
            }
            self._append_live(element_data)
            return

        border_pen = QPen(final_fill_color, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(border_pen)

        texture_b64 = None
        if not parent.eraser_mode and len(parent.mix_colors) > 1:
            if parent.mix_mode == 'smooth':
                center = QPointF(min_x + w/2, min_y + h/2)
                angle_rad = math.radians(parent.mix_angle)
                r = math.sqrt(w*w + h*h) / 2
                start_point = QPointF(center.x() - r * math.cos(angle_rad), center.y() - r * math.sin(angle_rad))
                end_point = QPointF(center.x() + r * math.cos(angle_rad), center.y() + r * math.sin(angle_rad))
                gradient = QLinearGradient(start_point, end_point)
                for i, col in enumerate(parent.mix_colors):
                    pos = i / (len(parent.mix_colors) - 1) if len(parent.mix_colors) > 1 else 0
                    gradient.setColorAt(pos, col)
                painter.setBrush(QBrush(gradient))
                painter.drawPath(path)

                pattern_img = QImage(w, h, QImage.Format_ARGB32)
                pattern_img.fill(Qt.transparent)
                p_painter = QPainter(pattern_img)
                p_painter.setRenderHint(QPainter.Antialiasing)
                local_start = start_point - QPointF(min_x, min_y)
                local_end = end_point - QPointF(min_x, min_y)
                local_gradient = QLinearGradient(local_start, local_end)
                for i, col in enumerate(parent.mix_colors):
                    pos = i / (len(parent.mix_colors) - 1) if len(parent.mix_colors) > 1 else 0
                    local_gradient.setColorAt(pos, col)
                p_painter.setBrush(QBrush(local_gradient))
                p_painter.setPen(Qt.NoPen)
                path_translated = QPainterPath()
                path_translated.moveTo(points_to_draw[0] - QPoint(min_x, min_y))
                for p in points_to_draw[1:]:
                    path_translated.lineTo(p - QPoint(min_x, min_y))
                path_translated.closeSubpath()
                p_painter.drawPath(path_translated)
                p_painter.end()
                if is_mirrored_shape:
                    pattern_img = pattern_img.mirrored(True, False)
                buffer = QByteArray()
                buffer_io = QBuffer(buffer)
                buffer_io.open(QIODevice.WriteOnly)
                pattern_img.save(buffer_io, "PNG")
                texture_b64 = base64.b64encode(buffer.data()).decode('utf-8')
            else:
                pattern_img = QImage(w, h, QImage.Format_ARGB32)
                pattern_img.fill(final_fill_color)
                p_painter = QPainter(pattern_img)
                p_painter.setRenderHint(QPainter.Antialiasing)
                num_blobs = int(w * h / 50)
                mix_idx = 0
                angle_rad = math.radians(parent.mix_angle)
                for i in range(max(10, num_blobs)):
                    bx = random.randint(0, w)
                    by = random.randint(0, h)
                    global_x = min_x + bx
                    global_y = min_y + by
                    if is_mirrored_shape:
                        global_x = self.mirror_line_x - (global_x - self.mirror_line_x)
                    
                    color = self.calculateMixColor(global_x, global_y, 0.0, parent.mix_colors, parent.mix_mode, parent.mix_angle, mix_idx)
                    if parent.mix_mode == 'sequential':
                        mix_idx += 1
                    
                    p_painter.setBrush(QBrush(color))
                    p_painter.setPen(Qt.NoPen)
                    r = random.randint(5, 25)
                    p_painter.drawEllipse(bx, by, r, r)
                p_painter.end()
                if is_mirrored_shape:
                    pattern_img = pattern_img.mirrored(True, False)
                buffer = QByteArray()
                buffer_io = QBuffer(buffer)
                buffer_io.open(QIODevice.WriteOnly)
                pattern_img.save(buffer_io, "PNG")
                texture_b64 = base64.b64encode(buffer.data()).decode('utf-8')
                brush = QBrush(pattern_img)
                painter.translate(min_x, min_y)
                path_translated = QPainterPath()
                path_translated.moveTo(points_to_draw[0] - QPoint(min_x, min_y))
                for p in points_to_draw[1:]:
                    path_translated.lineTo(p - QPoint(min_x, min_y))
                path_translated.closeSubpath()
                painter.setBrush(brush)
                painter.drawPath(path_translated)
                painter.translate(-min_x, -min_y)
        else:
            painter.setBrush(QBrush(final_fill_color))
            painter.drawPath(path)

        painter.end()
        element_data = {
            "type": "stroke", "points": [[p.x(), p.y()] for p in points_to_draw],
            "color": [final_fill_color.red(), final_fill_color.green(), final_fill_color.blue(), final_fill_color.alpha()],
            "width": 1, "pressure_enabled": False, "is_solid_fill": True, "layer": self.current_layer_name
        }
        if parent.eraser_mode:
            element_data["is_eraser"] = True

        if texture_b64:
            element_data["fill_texture"] = texture_b64
            element_data["bbox"] = [min_x, min_y, w, h]
        self._append_live(element_data)

    def _save_stroke(self, points, info, is_mirrored_call=False):
        parent = self.parent()
        if not parent:
            return
        if parent.pen_pressure_enabled or len(parent.mix_colors) > 1 or parent.current_tool_index >= 6:
            extended_points = []
            for i, point in enumerate(points):
                color_info = info[i][0]
                width_info = info[i][1]
                pt = self.getMirroredPoint(point) if is_mirrored_call else point
                extended_points.append([
                    pt.x(), pt.y(),
                    color_info.red(), color_info.green(), color_info.blue(), color_info.alpha(),
                    width_info
                ])
            data = {
                "type": "stroke_pressure", "points": extended_points, "pressure_enabled": True,
                "brush_type": parent.current_tool_index if parent.current_tool_index >= 6 else 0, "layer": self.current_layer_name
            }
            if parent.eraser_mode:
                data["is_eraser"] = True
            self._append_live(data)
        else:
            if parent.eraser_mode:
                color_to_save = QColor(0, 0, 0, 0)
                width_to_save = parent.eraser_radius
            else:
                color_to_save, width_to_save = parent.getCurrentPen()

            final_points = []
            for p in points:
                pt = self.getMirroredPoint(p) if is_mirrored_call else p
                final_points.append([pt.x(), pt.y()])
            data = {
                "type": "stroke", "points": final_points,
                "color": [color_to_save.red(), color_to_save.green(), color_to_save.blue(), color_to_save.alpha()],
                "width": width_to_save, "pressure_enabled": False, "layer": self.current_layer_name
            }
            if parent.eraser_mode:
                data["is_eraser"] = True
            self._append_live(data)

    def mouseReleaseEvent(self, event):
        parent = self.parent()
        if not parent:
            return
        if self.select_active and self.selectMouseRelease(event):
            return
        if self.point_active and self.ptMouseRelease(event):
            return

        if self.panning:
            self.panning = False
            if self.alt_permanent_pan_mode:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.CrossCursor)
            return

        if self.dragging_mirror_line:
            self.dragging_mirror_line = False
            self.setCursor(Qt.CrossCursor)
            return
        if self.dragging_whole_polyline:
            self.dragging_whole_polyline = False
            self.setCursor(Qt.CrossCursor)
            return
        if parent.polyline_mode or parent.curve_mode:
            self.dragging_poly_point_index = -1
            self.setCursor(Qt.CrossCursor)
            return

        if (event.button() == Qt.MiddleButton or event.button() == Qt.RightButton) and self.dragging_image:
            self.dragging_image = False
            self.setCursor(Qt.CrossCursor)
            event.accept()
            return

        if event.button() == Qt.LeftButton and self.drawing:
            
            if parent.current_tool_index in [37, 38]:
                if len(self.current_stroke_points) >= 2:
                    p1 = self.current_stroke_points[0]
                    p2 = self.current_stroke_points[1]
                    pts = []

                    if parent.current_tool_index == 37: 
                        pts = [p1, QPoint(p2.x(), p1.y()), p2, QPoint(p1.x(), p2.y()), p1]
                    elif parent.current_tool_index == 38: 
                        r = math.hypot(p2.x() - p1.x(), p2.y() - p1.y())
                        steps = max(30, min(100, int(r))) 
                        if steps > 0:
                            for i in range(steps + 1):
                                angle = 2 * math.pi * i / steps
                                pts.append(QPoint(int(p1.x() + r * math.cos(angle)), int(p1.y() + r * math.sin(angle))))
                        else:
                            pts = [p1, p1]

                    if parent.solid_fill_mode:
                        self.createSolidFill(pts, is_mirrored_shape=False)
                        if parent.mirror_mode:
                            mirrored_pts = [self.getMirroredPoint(p) for p in pts]
                            mirrored_pts.reverse()
                            self.createSolidFill(mirrored_pts, is_mirrored_shape=True)
                    else:
                        pen_color, pen_width = parent.getCurrentPen()
                        data = {
                            "type": "stroke", "points": [[p.x(), p.y()] for p in pts],
                            "color": [pen_color.red(), pen_color.green(), pen_color.blue(), pen_color.alpha()],
                            "width": pen_width, "pressure_enabled": False, "layer": self.current_layer_name
                        }
                        if parent.eraser_mode:
                            data["is_eraser"] = True
                        self.drawing_elements.append(data)

                        if parent.mirror_mode:
                            m_pts = [self.getMirroredPoint(p) for p in pts]
                            m_data = {
                                "type": "stroke", "points": [[p.x(), p.y()] for p in m_pts],
                                "color": [pen_color.red(), pen_color.green(), pen_color.blue(), pen_color.alpha()],
                                "width": pen_width, "pressure_enabled": False, "layer": self.current_layer_name
                            }
                            if parent.eraser_mode:
                                m_data["is_eraser"] = True
                            self.drawing_elements.append(m_data)

                self.current_stroke_points = []
                self.drawing = False
                self._actively_modifying = False
                self.updateImageFromElements()
                return

            if parent.solid_fill_mode:
                if len(self.current_stroke_points) > 2:
                    self.createSolidFill(self.current_stroke_points, is_mirrored_shape=False)
                    if parent.mirror_mode:
                        mirrored_points = [self.getMirroredPoint(p) for p in self.current_stroke_points]
                        mirrored_points.reverse()
                        self.createSolidFill(mirrored_points, is_mirrored_shape=True)
                    self.update()
            else:
                is_mixed = len(parent.mix_colors) > 1 and not parent.eraser_mode
                is_special_brush = parent.current_tool_index >= 6

                if parent.current_tool_index == 36:
                     pass

                else:
                    self._save_stroke(self.current_stroke_points, self.current_stroke_pen_info, is_mirrored_call=False)
                    if parent.mirror_mode:
                        self._save_stroke(self.current_stroke_points, self.current_stroke_pen_info, is_mirrored_call=True)

            self.current_stroke_points = []
            self.current_stroke_pen_info = []
            self.drawing = False
            self._actively_modifying = False
            
            self.lazy_mouse_pos = None
            self.lazy_target_pos = None
            self.lazy_velocity = QPointF(0, 0)

            # Eski sistem silgide/"üstte tut" modunda TÜM kayıtları yeniden oynatıyordu (kasma nedeni).
            # Artık çizim zaten aktif katmanın raster'ında; yalnızca pixmap tazelenir.
            self.commitImageToPixmap()
            self.update()
            self.contentChanged.emit()

    def finalizePolyline(self):
        if not self.parent():
            return
        parent = self.parent()
        active_points = self.polyline_points if parent.polyline_mode else self.curve_points
        if not active_points:
            return
        self.saveStateForUndo(deep_copy=False)

        if parent.eraser_mode:
            c = QColor(0, 0, 0, 0)
            w = parent.eraser_radius
        elif len(parent.mix_colors) > 1:
            c = random.choice(parent.mix_colors)
            w = parent.pen_radius
        else:
            c = parent.pen_color
            w = parent.pen_radius

        def save_path_as_stroke(pts, add_arrow=False):
            data = None
            if parent.curve_mode:
                path = self.generateSmoothCurvePath(pts)
                rasterized_points = []
                for i in range(101):
                    pt = path.pointAtPercent(i / 100.0)
                    rasterized_points.append([pt.x(), pt.y()])
                data = {
                    "type": "stroke", "points": rasterized_points,
                    "color": [c.red(), c.green(), c.blue(), c.alpha()],
                    "width": w, "pressure_enabled": False, "layer": self.current_layer_name
                }
            else:
                final_pts = [[p.x(), p.y()] for p in pts]
                if add_arrow and len(pts) >= 2:
                    p_end = pts[-1]
                    p_prev = pts[-2]
                    angle = math.atan2(p_prev.y() - p_end.y(), p_prev.x() - p_end.x())
                    arrow_len = w * 3
                    p3 = QPoint(int(p_end.x() + arrow_len * math.cos(angle + math.pi / 6)), int(p_end.y() + arrow_len * math.sin(angle + math.pi / 6)))
                    p4 = QPoint(int(p_end.x() + arrow_len * math.cos(angle - math.pi / 6)), int(p_end.y() + arrow_len * math.sin(angle - math.pi / 6)))
                    final_pts.append([p3.x(), p3.y()])
                    final_pts.append([p_end.x(), p_end.y()])
                    final_pts.append([p4.x(), p4.y()])

                data = {
                    "type": "stroke", "points": final_pts,
                    "color": [c.red(), c.green(), c.blue(), c.alpha()],
                    "width": w, "pressure_enabled": False, "layer": self.current_layer_name
                }

            if data:
                if parent.eraser_mode:
                    data["is_eraser"] = True
                self.drawing_elements.append(data)

        is_arrow = (parent.current_tool_index == 36)
        save_path_as_stroke(active_points, add_arrow=is_arrow)
        if parent.mirror_mode:
            mirrored_pts = [self.getMirroredPoint(p) for p in active_points]
            save_path_as_stroke(mirrored_pts, add_arrow=is_arrow)

        if parent.polyline_mode:
            self.polyline_points = []
        else:
            self.curve_points = []
        self.updateImageFromElements()

    def drawBrushStroke(self, painter, p1, p2, color, width, tool_index):
        dist = math.sqrt((p2.x()-p1.x())**2 + (p2.y()-p1.y())**2)
        i_width = int(width) if width > 0 else 1

        if tool_index == 6:
            pen = QPen(color, width)
            pen.setCapStyle(Qt.SquareCap)
            painter.setPen(pen)
            painter.save()
            painter.translate(p2)
            painter.rotate(45)
            painter.drawLine(0, -i_width//2, 0, i_width//2)
            painter.restore()
            painter.drawLine(p1, p2)
        elif tool_index == 7:
            marker_color = QColor(color)
            marker_color.setAlpha(40)
            painter.setPen(Qt.NoPen)
            painter.setBrush(marker_color)
            rect_size = width * 1.5
            painter.drawRect(int(p2.x() - rect_size/2), int(p2.y() - rect_size/2), int(rect_size), int(rect_size))
        elif tool_index == 8:
            density = int(width * 1.5)
            painter.setPen(QPen(color, 1))
            for _ in range(density):
                angle = random.random() * 2 * math.pi
                radius = random.random() * width
                dx = int(radius * math.cos(angle))
                dy = int(radius * math.sin(angle))
                painter.drawPoint(p2.x() + dx, p2.y() + dy)
        elif tool_index == 9:
            chalk_color = QColor(color)
            chalk_color.setAlpha(150)
            painter.setPen(QPen(chalk_color, 1))
            steps = max(1, int(dist))
            for i in range(steps):
                t = i / steps
                x = p1.x() + (p2.x() - p1.x()) * t
                y = p1.y() + (p2.y() - p1.y()) * t
                rx = random.randint(int(-i_width//2), int(i_width//2))
                ry = random.randint(int(-i_width//2), int(i_width//2))
                if random.random() > 0.3:
                    painter.drawPoint(int(x + rx), int(y + ry))
        elif tool_index == 10:
            hl_color = QColor(color)
            hl_color.setAlpha(60)
            painter.setPen(Qt.NoPen)
            painter.setBrush(hl_color)
            h = width * 2
            w = 5
            painter.drawRect(int(p2.x() - w/2), int(p2.y() - h/2), w, int(h))
        elif tool_index == 11:
            gradient = QRadialGradient(p2, width)
            c1 = QColor(color)
            c1.setAlpha(20)
            c2 = QColor(color)
            c2.setAlpha(0)
            gradient.setColorAt(0, c1)
            gradient.setColorAt(1, c2)
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(p2, width, width)
        elif tool_index == 12:
            painter.setPen(QPen(color, max(1, i_width//2), Qt.SolidLine))
            painter.drawLine(p1, p2)
        elif tool_index == 13:
            painter.setPen(QPen(color, 1))
            painter.drawPoint(p2)
        elif tool_index == 14:
            char_color = QColor(40, 40, 40, 100)
            painter.setPen(QPen(char_color, 1))
            for _ in range(i_width):
                rx = random.randint(int(-i_width//2), int(i_width//2))
                ry = random.randint(int(-i_width//2), int(i_width//2))
                painter.drawPoint(p2.x() + rx, p2.y() + ry)
        elif tool_index == 15:
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(p2, int(width/2), int(width/2))
        elif tool_index == 16:
            painter.setPen(QPen(color, 1))
            painter.drawPoint(p2)
            if random.random() > 0.8:
                offset_x = random.randint(-50, 50)
                offset_y = random.randint(-50, 50)
                painter.setPen(QPen(color, 0.5))
                painter.drawLine(p2, QPoint(p2.x()+offset_x, p2.y()+offset_y))
        elif tool_index == 17:
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap))
            painter.setOpacity(0.3)
            painter.drawLine(p1, p2)
            painter.setOpacity(1.0)
            painter.setPen(QPen(QColor(255, 255, 255), max(1, i_width//3), Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1, p2)
        elif tool_index == 18:
            if dist > 5:
                painter.setPen(Qt.NoPen)
                for _ in range(3):
                    conf_color = QColor(random.randint(0,255), random.randint(0,255), random.randint(0,255))
                    painter.setBrush(conf_color)
                    cx = p2.x() + random.randint(int(-i_width), int(i_width))
                    cy = p2.y() + random.randint(int(-i_width), int(i_width))
                    cs = random.randint(2, 6)
                    if random.random() > 0.5:
                        painter.drawEllipse(cx, cy, cs, cs)
                    else:
                        painter.drawRect(cx, cy, cs, cs)

        elif tool_index == 19:
             painter.setPen(Qt.NoPen)
             painter.setBrush(color)
             painter.save()
             painter.translate(p2)
             painter.rotate(random.randint(0, 360))
             path = QPainterPath()
             path.moveTo(0, -width)
             path.quadTo(width/2, -width/2, 0, width)
             path.quadTo(-width/2, -width/2, 0, -width)
             painter.drawPath(path)
             painter.restore()

        elif tool_index == 20:
             painter.setPen(QPen(color, 1))
             painter.setBrush(Qt.NoBrush)
             size = i_width
             painter.save()
             painter.translate(p2)
             painter.rotate(random.randint(0, 360))
             points = [QPoint(0, -size), QPoint(size//4, -size//4), QPoint(size, 0), QPoint(size//4, size//4), QPoint(0, size), QPoint(-size//4, size//4), QPoint(-size, 0), QPoint(-size//4, -size//4)]
             painter.drawPolygon(QPolygon(points))
             painter.restore()

        elif tool_index == 21:
            painter.setPen(QPen(color, 1))
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 50))
            painter.drawEllipse(p2, width, width)
            painter.setBrush(QColor(255, 255, 200))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(p2.x() - i_width//3, p2.y() - i_width//3, i_width//3, i_width//3)

        elif tool_index == 22:
            if dist > 3:
                painter.setPen(QPen(color, 1))
                for _ in range(3):
                    gx = p2.x() + random.randint(-5, 5)
                    gy = p2.y() + random.randint(-2, 2)
                    gh = random.randint(int(width), int(width * 3)) if width > 1 else random.randint(5, 15)
                    painter.drawLine(gx, gy, gx, gy - gh)

        elif tool_index == 23:
            hue = (p2.x() + p2.y()) % 360
            rb_color = QColor.fromHsv(hue, 200, 250)
            painter.setPen(QPen(rb_color, width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1, p2)
        elif tool_index == 24:
            painter.setPen(QPen(color, 1))
            dx = p2.x() - p1.x()
            dy = p2.y() - p1.y()
            normal_x = -dy
            normal_y = dx
            length = math.sqrt(normal_x**2 + normal_y**2)
            if length > 0:
                normal_x /= length
                normal_y /= length
                fur_len = width * 1.5
                painter.drawLine(p2.x(), p2.y(), int(p2.x() + normal_x * fur_len), int(p2.y() + normal_y * fur_len))

        elif tool_index == 25:
            painter.setPen(QPen(color, 1))
            painter.drawLine(p1, p2)
            if random.random() > 0.5:
                w_offset = max(1, int(width // 2))
                offsets = [random.randint(-w_offset, w_offset) for _ in range(4)]
                painter.drawLine(p1.x()+offsets[0], p1.y()+offsets[1], p2.x()+offsets[2], p2.y()+offsets[3])

        elif tool_index == 26:
            pen = QPen(color, width)
            pen.setStyle(Qt.DotLine)
            painter.setPen(pen)
            painter.drawLine(p1, p2)
        elif tool_index == 27:
            pen = QPen(color, width)
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(p1, p2)
        elif tool_index == 28:
            pen = QPen(color, max(1, i_width//3))
            offset = i_width // 2 + 2
            painter.setPen(pen)
            painter.drawLine(p1.x()-offset, p1.y()-offset, p2.x()-offset, p2.y()-offset)
            painter.drawLine(p1.x()+offset, p1.y()+offset, p2.x()+offset, p2.y()+offset)
        elif tool_index == 29:
            shadow_color = QColor(0, 0, 0, 50)
            painter.setPen(QPen(shadow_color, width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1.x()+5, p1.y()+5, p2.x()+5, p2.y()+5)
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1, p2)
        elif tool_index == 30:
            darker = color.darker(150)
            painter.setPen(QPen(darker, width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1.x()+2, p1.y()+2, p2.x()+2, p2.y()+2)
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(p1, p2)

        elif tool_index == 31:
            if dist > 0:
                painter.setPen(QPen(color, 2))
                amplitude = max(5, width)
                angle = math.atan2(p2.y()-p1.y(), p2.x()-p1.x())
                perp_angle = angle + math.pi/2
                offset = (p2.x() + p2.y()) / 10.0
                off1 = math.sin(offset) * amplitude
                off2 = math.sin(offset + math.pi) * amplitude
                pt1_x = p2.x() + math.cos(perp_angle) * off1
                pt1_y = p2.y() + math.sin(perp_angle) * off1
                pt2_x = p2.x() + math.cos(perp_angle) * off2
                pt2_y = p2.y() + math.sin(perp_angle) * off2
                painter.drawPoint(int(pt1_x), int(pt1_y))
                painter.drawPoint(int(pt2_x), int(pt2_y))
                if random.random() > 0.8:
                    painter.setPen(QPen(color, 1))
                    painter.drawLine(int(pt1_x), int(pt1_y), int(pt2_x), int(pt2_y))

        elif tool_index == 32:
            painter.setPen(QPen(color, 2))
            offset = 5 if int(p2.x() / 10) % 2 == 0 else -5
            painter.drawPoint(p2.x() + offset, p2.y() + offset)

        elif tool_index == 33:
            painter.setPen(QPen(color, 1))
            grid_size = max(5, int(width * 2))
            snap_x = (p2.x() // grid_size) * grid_size
            snap_y = (p2.y() // grid_size) * grid_size
            painter.drawLine(snap_x, snap_y, snap_x+grid_size, snap_y)
            painter.drawLine(snap_x, snap_y, snap_x, snap_y+grid_size)

        elif tool_index == 34:
             painter.setPen(QPen(color, 1))
             if dist > 5:
                 rand_range = max(2, int(width))
                 mx = (p1.x() + p2.x()) / 2 + random.randint(-rand_range, rand_range)
                 my = (p1.y() + p2.y()) / 2 + random.randint(-rand_range, rand_range)
                 painter.drawLine(p1, QPoint(int(mx), int(my)))
                 painter.drawLine(QPoint(int(mx), int(my)), p2)
             else:
                 painter.drawLine(p1, p2)

        else:
            painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(p1, p2)

    def wheelEvent(self, event):
        parent = self.parent()
        if not parent:
            super().wheelEvent(event)
            return
        is_o_mode = parent.nav_button.isChecked()

        if self.placing_reference and self.reference_image is not None and not is_o_mode:
            ref = self.reference_image
            num_degrees = event.angleDelta().y() / 8
            num_steps = num_degrees / 15
            scale_factor = 1.0 + num_steps * 0.1
            current_size = ref['display_size']
            new_width = int(current_size.width() * scale_factor)
            new_height = int(current_size.height() * scale_factor)
            
            min_size = 20
            max_size_width = self.image.width()
            max_size_height = self.image.height()
            new_width = max(min_size, min(new_width, max_size_width))
            new_height = max(min_size, min(new_height, max_size_height))
            
            if new_width != current_size.width() or new_height != current_size.height():
                current_center = ref['offset'] + QPoint(current_size.width() // 2, current_size.height() // 2)
                ref['display_size'] = QSize(new_width, new_height)
                ref['offset'] = current_center - QPoint(ref['display_size'].width() // 2, ref['display_size'].height() // 2)
                self._reference_scaled_cache.clear()
                self.update()
                event.accept()
                return

        if parent.placing_image and self.original_image_for_placement:
            num_degrees = event.angleDelta().y() / 8
            num_steps = num_degrees / 15
            scale_factor = 1.0 + num_steps * 0.1
            current_image_size = self.current_image_display_size
            new_width = int(current_image_size.width() * scale_factor)
            new_height = int(current_image_size.height() * scale_factor)
            min_size = 20
            max_size_width = self.width() - 10
            max_size_height = self.height() - 10
            new_width = max(min_size, min(new_width, max_size_width))
            new_height = max(min_size, min(new_height, max_size_height))
            if new_width == current_image_size.width() and new_height == current_image_size.height():
                event.ignore()
                return
            current_center = self.image_placement_offset + QPoint(current_image_size.width() // 2, current_image_size.height() // 2)
            self.current_image_display_size = QSize(new_width, new_height)
            self.image_placement_offset = current_center - QPoint(self.current_image_display_size.width() // 2, self.current_image_display_size.height() // 2)
            self.applyImagePlacementBounds()
            self.update()
            event.accept()
        elif parent.polyline_mode or parent.curve_mode:
            active_points = self.polyline_points if parent.polyline_mode else self.curve_points
            if len(active_points) == 0:
                return
            center_x = sum(p.x() for p in active_points) / len(active_points)
            center_y = sum(p.y() for p in active_points) / len(active_points)
            center = QPoint(int(center_x), int(center_y))
            num_degrees = event.angleDelta().y() / 8
            scale_factor = 1.05 if num_degrees > 0 else 0.95
            new_points = []
            for p in active_points:
                vec = p - center
                new_vec_x = vec.x() * scale_factor
                new_vec_y = vec.y() * scale_factor
                new_points.append(QPoint(int(center.x() + new_vec_x), int(center.y() + new_vec_y)))
            if parent.polyline_mode:
                self.polyline_points = new_points
            else:
                self.curve_points = new_points
            self.update()
            event.accept()
        else:
            if is_o_mode:
                old_zoom = self.zoom_factor
                delta = event.angleDelta().y()
                factor = 1.1 if delta > 0 else 0.9
                new_zoom = old_zoom * factor
                new_zoom = max(0.1, min(30.0, new_zoom))

                if new_zoom != old_zoom:
                    mouse_pos = event.pos()
                    p_img = self.toCanvas(mouse_pos)
                    self.zoom_factor = new_zoom
                    center_offset_x = 0
                    center_offset_y = 0
                    scaled_w = self.image.width() * self.zoom_factor
                    scaled_h = self.image.height() * self.zoom_factor

                    if self.width() > scaled_w:
                         center_offset_x = (self.width() - scaled_w) / 2
                    if self.height() > scaled_h:
                         center_offset_y = (self.height() - scaled_h) / 2

                    new_vx = mouse_pos.x() - (p_img.x() * new_zoom) - center_offset_x
                    new_vy = mouse_pos.y() - (p_img.y() * new_zoom) - center_offset_y

                    self.view_offset = QPoint(int(new_vx), int(new_vy))
                    self.update()

                event.accept()
            else:
                super().wheelEvent(event)

    def drawTabletLineTo(self, endPoint, pressure):
        pass

    def addTextToDrawing(self):
        parent = self.parent()
        if not parent:
            return
        text_content = self.text_input_widget.toPlainText()
        if text_content:
            self.saveStateForUndo(deep_copy=False)

            cursor = self.text_input_widget.textCursor()
            cursor.setPosition(0)
            rect = self.text_input_widget.cursorRect(cursor)

            text_start_in_widget = self.text_input_widget.viewport().mapToParent(rect.topLeft())
            absolute_text_pos = self.text_input_widget.pos() + text_start_in_widget
            canvas_pos_f = self.toCanvas(absolute_text_pos)

            screen_font_size = self.text_input_widget.font().pointSize()
            canvas_font_size = int(screen_font_size / self.zoom_factor)
            if canvas_font_size < 1:
                canvas_font_size = 1

            final_x = canvas_pos_f.x()
            final_y = canvas_pos_f.y()

            color = parent.pen_color

            self.drawing_elements.append({
                "type": "text", "content": text_content,
                "position": [final_x, final_y],
                "color": [color.red(), color.green(), color.blue(), color.alpha()],
                "font_size": canvas_font_size, "layer": self.current_layer_name
            })
            if parent.mirror_mode:
                 p_canvas = QPoint(int(final_x), int(final_y))
                 mirrored_pos = self.getMirroredPoint(p_canvas)
                 self.drawing_elements.append({
                    "type": "text", "content": text_content,
                    "position": [mirrored_pos.x(), mirrored_pos.y()],
                    "color": [color.red(), color.green(), color.blue(), color.alpha()],
                    "font_size": canvas_font_size, "is_mirrored": True, "layer": self.current_layer_name
                })
            self.updateImageFromElements()

        self.text_input_widget.hide()
        self.text_input_widget.clear()

    def startImagePlacement(self, original_image_qimage):
        if self.parent():
            self.parent().is_project_modified = True
            
        self.original_image_for_placement = original_image_qimage
        drawing_area_size = self.size()
        max_width = drawing_area_size.width() - 10
        max_height = drawing_area_size.height() - 10
        initial_scaled_size = self.original_image_for_placement.size().scaled(max_width, max_height, Qt.KeepAspectRatio)
        self.current_image_display_size = initial_scaled_size
        self.image_placement_offset = QPoint((self.width() - initial_scaled_size.width()) // 2, (self.height() - initial_scaled_size.height()) // 2)
        self.applyImagePlacementBounds()
        self.dragging_image = False
        self.setCursor(Qt.CrossCursor)
        self.drawing = False
        self.current_stroke_points = []
        self.current_stroke_pen_info = []

        parent = self.parent()
        if parent:
            parent.nav_button.setChecked(False)
            parent.nav_button.updateStyle()

        self.update()

    def cancelImagePlacement(self):
        self.original_image_for_placement = None
        self.current_image_display_size = QSize(0, 0)
        self.image_placement_offset = QPoint(0, 0)
        self.dragging_image = False
        self.setCursor(Qt.ArrowCursor)
        self.drawing = False
        self.current_stroke_points = []
        self.current_stroke_pen_info = []
        self.update()
        parent = self.parent()
        if parent:
            parent.placing_image = False
            parent.updateButtonStyles()

    def applyImagePlacementBounds(self):
        if not self.original_image_for_placement or not self.current_image_display_size.isValid():
            return
        pass

    def _render_elements(self, elements, target_image=None):
        """Kayıtları rasterlaştırır. target_image verilirse hepsi oraya çizilir; yoksa her kayıt kendi katmanına."""
        if target_image is not None:
            self._render_group(target_image, elements)
            return
        st = self.layer_stack
        groups = {}
        order = []
        for element in elements:
            layer = st.by_name(element.get("layer", "")) or st.active
            if layer.id not in groups:
                groups[layer.id] = (layer, [])
                order.append(layer.id)
            groups[layer.id][1].append(element)

        for lid in order:
            layer, layer_elements = groups[lid]
            self._render_group(layer.image, layer_elements)
            layer.invalidate()
            layer.touch()

    def _render_group(self, image, layer_elements):
        """Kayıtları verilen görüntüye çizer (katmana bağlı değildir; A modu ve ara kareler de kullanır)."""
        layer_painter = QPainter(image)
        layer_painter.setRenderHint(QPainter.Antialiasing)
        try:
            for element in layer_elements:
                is_eraser = element.get("is_eraser", False)
                if is_eraser:
                    layer_painter.setCompositionMode(QPainter.CompositionMode_Clear)
                else:
                    layer_painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

                if element.get("is_solid_fill", False):
                    c = QColor(*element["color"])
                    pts = [QPoint(int(p[0]), int(p[1])) for p in element["points"]]
                    if len(pts) > 2:
                        path = QPainterPath()
                        path.moveTo(pts[0])
                        for p in pts[1:]:
                            path.lineTo(p)
                        path.closeSubpath()
                        layer_painter.setPen(QPen(c, 1, Qt.SolidLine))
                        if is_eraser:
                            layer_painter.setBrush(QBrush(Qt.black))
                            layer_painter.drawPath(path)
                        elif "fill_texture" in element and element["fill_texture"]:
                            pattern_img = self._cached_b64_image(element["fill_texture"])
                            bbox = element.get("bbox", [0, 0, 1, 1])
                            min_x, min_y = bbox[0], bbox[1]
                            layer_painter.save()
                            layer_painter.translate(min_x, min_y)
                            path_translated = QPainterPath()
                            path_translated.moveTo(pts[0] - QPoint(int(min_x), int(min_y)))
                            for p in pts[1:]:
                                path_translated.lineTo(p - QPoint(int(min_x), int(min_y)))
                            path_translated.closeSubpath()
                            layer_painter.setBrush(QBrush(pattern_img))
                            layer_painter.drawPath(path_translated)
                            layer_painter.restore()
                        else:
                            layer_painter.setBrush(QBrush(c))
                            layer_painter.drawPath(path)
                    continue

                if element["type"] == "stroke":
                    color = QColor(*element["color"])
                    width = element["width"]
                    pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                    layer_painter.setPen(pen)
                    points = [QPoint(int(p[0]), int(p[1])) for p in element["points"]]
                    if len(points) > 1:
                        layer_painter.drawPolyline(QPolygon(points))
                    elif len(points) == 1:
                        layer_painter.drawPoint(points[0])

                elif element["type"] == "stroke_pressure":
                    points_data = element["points"]
                    brush_type = element.get("brush_type", 0)
                    if brush_type == 0:
                        reuse_pen = QPen(Qt.black, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                        last_pen_key = None
                        for i in range(len(points_data) - 1):
                            p1_data = points_data[i]
                            p2_data = points_data[i+1]
                            p1 = QPoint(int(p1_data[0]), int(p1_data[1]))
                            p2 = QPoint(int(p2_data[0]), int(p2_data[1]))
                            pen_key = (p1_data[2], p1_data[3], p1_data[4], p1_data[5], p1_data[6])
                            if pen_key != last_pen_key:
                                reuse_pen.setColor(QColor(p1_data[2], p1_data[3], p1_data[4], p1_data[5]))
                                reuse_pen.setWidthF(float(p1_data[6]))
                                layer_painter.setPen(reuse_pen)
                                last_pen_key = pen_key
                            layer_painter.drawLine(p1, p2)
                    else:
                        for i in range(len(points_data) - 1):
                            p1_data = points_data[i]
                            p2_data = points_data[i+1]
                            p1 = QPoint(int(p1_data[0]), int(p1_data[1]))
                            p2 = QPoint(int(p2_data[0]), int(p2_data[1]))
                            color = QColor(p1_data[2], p1_data[3], p1_data[4], p1_data[5])
                            width = p1_data[6]
                            self.drawBrushStroke(layer_painter, p1, p2, color, width, brush_type)

                elif element["type"] == "text":
                    color = QColor(*element["color"])
                    font = QFont("Arial", element["font_size"])
                    layer_painter.setPen(color)
                    layer_painter.setFont(font)
                    text_pos = QPoint(int(element["position"][0]), int(element["position"][1]))
                    font_metrics = QFontMetrics(font)
                    lines = element["content"].split('\n')
                    current_y = text_pos.y()
                    if element.get("is_mirrored", False):
                        layer_painter.save()
                        layer_painter.translate(text_pos.x(), text_pos.y())
                        layer_painter.scale(-1, 1)
                        for line in lines:
                            current_y += font_metrics.ascent()
                            layer_painter.drawText(0, current_y - text_pos.y(), line)
                            current_y += 5
                        layer_painter.restore()
                    else:
                        for line in lines:
                            current_y += font_metrics.ascent()
                            layer_painter.drawText(text_pos.x(), current_y, line)
                            current_y += 5

                elif element["type"] == "image":
                    base64_data = element["base64_data"]
                    cache_key = str(len(base64_data)) + base64_data[:30]
                    if cache_key in self.image_cache:
                        temp_image = self.image_cache[cache_key]
                    else:
                        image_data = base64.b64decode(base64_data)
                        temp_image = QImage()
                        temp_image.loadFromData(image_data, "PNG")
                        self.image_cache[cache_key] = temp_image
                    scaled_image = temp_image.scaled(
                        element["current_width"], element["current_height"],
                        Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                    image_pos = QPoint(int(element["position"][0]), int(element["position"][1]))
                    if is_eraser:
                        layer_painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
                        layer_painter.drawImage(image_pos, scaled_image)
                    else:
                        layer_painter.drawImage(image_pos, scaled_image)
        finally:
            layer_painter.end()

    def replaceColor(self, target_color, new_color, is_delete=False, mode='global', pos=None):
        self.saveStateForUndo(deep_copy=True)
        if mode == 'global':
            self.replaceColorGlobally(target_color, new_color, is_delete)
        elif mode == 'connected' and pos is not None:
            self.floodFill(pos, target_color, new_color if not is_delete else QColor(0,0,0,0))

    def replaceColorGlobally(self, target_color, new_color, is_delete=False):
        target_rgba = (target_color.red(), target_color.green(), target_color.blue())
        tolerance = 20
        for element in self.drawing_elements:
            if element["type"] == "stroke":
                ec = element["color"]
                if abs(ec[0]-target_rgba[0]) < tolerance and abs(ec[1]-target_rgba[1]) < tolerance and abs(ec[2]-target_rgba[2]) < tolerance:
                    if is_delete:
                        element["color"][3] = 0
                    else:
                        element["color"] = [new_color.red(), new_color.green(), new_color.blue(), new_color.alpha()]
            elif element["type"] == "stroke_pressure":
                points = element["points"]
                for p in points:
                    if abs(p[2]-target_rgba[0]) < tolerance and abs(p[3]-target_rgba[1]) < tolerance and abs(p[4]-target_rgba[2]) < tolerance:
                         if is_delete:
                             p[5] = 0
                         else:
                             p[2], p[3], p[4], p[5] = new_color.red(), new_color.green(), new_color.blue(), new_color.alpha()
            elif element["type"] == "text":
                if (abs(element["color"][0]-target_rgba[0]) < tolerance and
                    abs(element["color"][1]-target_rgba[1]) < tolerance and
                    abs(element["color"][2]-target_rgba[2]) < tolerance):
                    if is_delete:
                        element["color"] = [0, 0, 0, 0]
                    else:
                        element["color"] = [new_color.red(), new_color.green(), new_color.blue(), new_color.alpha()]
            elif element["type"] == "image":
                base64_data = element["base64_data"]
                image_data = base64.b64decode(base64_data)
                temp_image = QImage()
                temp_image.loadFromData(image_data, "PNG")
                temp_image = temp_image.convertToFormat(QImage.Format_ARGB32)
                width = temp_image.width()
                height = temp_image.height()
                modified = False
                for y in range(height):
                    for x in range(width):
                        pixel_color = temp_image.pixelColor(x, y)
                        if abs(pixel_color.red()-target_rgba[0]) < tolerance and abs(pixel_color.green()-target_rgba[1]) < tolerance and abs(pixel_color.blue()-target_rgba[2]) < tolerance:
                             if is_delete:
                                 temp_image.setPixelColor(x, y, QColor(0,0,0,0))
                             else:
                                 temp_image.setPixelColor(x, y, new_color)
                             modified = True
                if modified:
                    buffer = QByteArray()
                    buffer_io = QBuffer(buffer)
                    buffer_io.open(QIODevice.WriteOnly)
                    temp_image.save(buffer_io, "PNG")
                    element["base64_data"] = base64.b64encode(buffer.data()).decode('utf-8')
        self.updateImageFromElements(full=True)

    def floodFill(self, pos, target_color, replacement_color, tolerance=20):
        if not (0 <= pos.x() < self.image.width() and 0 <= pos.y() < self.image.height()):
            return
        image = self.image
        w, h = image.width(), image.height()
        queue = deque([pos])
        visited = set()
        if target_color == replacement_color:
            return
        while queue:
            p = queue.popleft()
            px, py = p.x(), p.y()
            if not (0 <= px < w and 0 <= py < h):
                continue
            key = (px, py)
            if key in visited:
                continue
            visited.add(key)
            current_color = image.pixelColor(px, py)
            if not (abs(current_color.red() - target_color.red()) < tolerance and abs(current_color.green() - target_color.green()) < tolerance and abs(current_color.blue() - target_color.blue()) < tolerance):
                continue
            image.setPixelColor(px, py, replacement_color)
            queue.append(QPoint(px + 1, py))
            queue.append(QPoint(px - 1, py))
            queue.append(QPoint(px, py + 1))
            queue.append(QPoint(px, py - 1))
        self.commitImageToPixmap()
        self.update()
