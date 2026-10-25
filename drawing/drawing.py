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

# Kavram çekirdeği: Drawing_editor.py
# Ağır parçalar modüllere ayrıldı (aynı klasörde olmaları yeterli):
#   drawing_common.py     ortak içe aktarmalar, FFmpeg bulucu, SVG ikonlar
#   drawing_widgets.py    küçük widget ve diyaloglar
#   drawing_layers.py     gerçek katman sistemi (katman modeli, sayfa dosyaları, katman paneli)
#   drawing_canvas.py     DrawingArea (çizim tuvali)
#   drawing_animation.py  soğan zarı, oynatma, kare süresi, zaman çizelgesi
#   drawing_export.py     iş parçacıklı çoklu biçim dışa aktarma
# --- kavram yol ayarı (otomatik; klasör yapısı: kavram/<program>/<program>.py) ---
import os as _os
_PROGRAM_DIR = _os.path.dirname(_os.path.abspath(__file__))
_KAVRAM_DIR = _os.environ.get("KAVRAM_DIR") or _os.path.dirname(_PROGRAM_DIR)
_KAVRAM_EXPORT_DIR = _os.path.join(_KAVRAM_DIR, "export")
# -------------------------------------------------------------------------------
from drawing_common import *
from drawing_widgets import *
from drawing_layers import *
from drawing_canvas import DrawingArea
from drawing_animation import AnimationController, TimelinePanel, expand_sequence
from drawing_export import start_export
from drawing_select import keyframe_copy, keyframe_tween

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



class DrawingEditorWindow(QWidget):
    DEFAULT_BASE_DIR = _KAVRAM_EXPORT_DIR

    TOOL_ORDER = [
        ("Normal", 0),
        ("Yazı (Text)", 35),
        ("Ok İşareti (Arrow)", 36),
        ("Pencil", 1),
        ("Brush", 2),
        ("Line (Nokta)", 3),
        ("Solid Fill", 4),
        ("Curve (Eğri)", 5),
        ("Calligraphy", 6),
        ("Marker (Keçeli)", 7),
        ("Spray (Sprey)", 8),
        ("Chalk (Tebeşir)", 9),
        ("Highlighter", 10),
        ("Airbrush", 11),
        ("Ink (Dolma)", 12),
        ("Pixel", 13),
        ("Charcoal (Karakalem)", 14),
        ("Stamp (Damga)", 15),
        ("Web (Örümcek)", 16),
        ("Neon", 17),
        ("Confetti", 18),
        ("Leaf (Yaprak)", 19),
        ("Star (Yıldız)", 20),
        ("Bubble (Balon)", 21),
        ("Grass (Çim)", 22),
        ("Rainbow", 23),
        ("Fur (Kürk)", 24),
        ("Sketchy", 25),
        ("Dotted (Noktalı)", 26),
        ("Dashed (Kesik)", 27),
        ("Double (Çift)", 28),
        ("Shadow (Gölge)", 29),
        ("3D", 30),
        ("DNA", 31),
        ("Sawtooth (Testere)", 32),
        ("Grid (Izgara)", 33),
        ("Lightning (Şimşek)", 34),
        ("Dikdörtgen (Rectangle)", 37),
        ("Daire (Circle)", 38)
    ]

    def __init__(self, core_window_ref=None):
        super().__init__()
        self.core_window_ref = core_window_ref
        
        self.is_project_modified = False
        
        settings = QSettings("kavram", "DrawingEditor")
        self.canvas_width = settings.value("canvasWidth", 1100, type=int)
        self.canvas_height = settings.value("canvasHeight", 600, type=int)

        self.drawing_cache_dir = os.path.join(DrawingEditorWindow.DEFAULT_BASE_DIR, "Drawing")
        self.clearDrawingCache()

        self.pen_color = QColor("#cccccc")
        self.mix_colors = [QColor("#cccccc")]
        self.mix_history = [[QColor("#cccccc")]]
        self.mix_mode = 'random'
        self.mix_angle = 0

        saved_bg = settings.value("backgroundColor", "#333", type=str)
        self.background_color = QColor(saved_bg)

        self.pen_radius = 8
        self.eraser_radius = 15
        self.sensitivity_value = -1

        self.eraser_mode = False
        self.pen_pressure_enabled = False
        self.text_mode = False
        self.placing_image = False
        self.polyline_mode = False
        self.curve_mode = False
        self.solid_fill_mode = False
        self.mirror_mode = False
        self.mirror_axis = 'vertical'
        self.is_v_pressed = False
        self.is_c_pressed = False
        self.always_top_mode = False
        self.current_file_path = None

        self.pages_data = []
        self.current_page_index = 0
        self.max_pages = 500

        self.normal_tool_index = 0
        self.eraser_tool_index = 4

        self.tool_radiuses = {
            0: 8, 1: 3, 2: 15, 3: 5, 4: 1, 5: 5,
            6: 8, 7: 15, 8: 30, 9: 5, 10: 20, 11: 40, 12: 3, 13: 1, 14: 10, 15: 30, 16: 2,
            17: 10, 18: 20, 19: 15, 20: 20, 21: 15, 22: 5, 23: 5, 24: 10, 25: 1, 26: 3, 27: 3,
            28: 6, 29: 5, 30: 5, 31: 10, 32: 2, 33: 1, 34: 2,
            35: 8, 36: 4, 37: 5, 38: 5
        }
        self.current_tool_index = 0
        
        self.lazy_mouse_enabled = False
        self.lazy_radius = 30
        self.lazy_factor = 15
        
        self.current_export_fps = settings.value("exportFPS", 24, type=int)
        
        self.alt_last_press_time = 0
        self.alt_double_click_threshold = 300

        self.reference_transparency = settings.value("referenceTransparency", 55, type=int)
        self.reference_transparency = max(0, min(95, self.reference_transparency))

        self.global_reference_visible = True
        self.next_reference_id = 1

        # Araç ipuçları (özellik + kısayol yazısı): siyah arka plan, beyaz metin
        _app = QApplication.instance()
        if _app is not None and "Kavram-tooltip" not in _app.styleSheet():
            _app.setStyleSheet(_app.styleSheet() + "\n/* Kavram-tooltip */\nQToolTip { background-color: #000000; color: #ffffff; "
                               "border: 1px solid #5a5a5a; padding: 4px 7px; font-size: 12px; }")
        self.initUI()
        
        self.pages_data.append({"background": self.background_color, "hold": 1})
        
        first_json_path = os.path.join(self.drawing_cache_dir, "sx.json")
        with open(first_json_path, 'w', encoding='utf-8') as f:
            json.dump([], f)
        
        self.loadPageData(0, save_current=False)
        
        self.loadLazyMouseSettings()
        self.lazy_mouse_button.updateButtonText(self)
        self.lazy_mouse_button.updateToolTip(self)
        if self.lazy_mouse_enabled:
            self.lazy_mouse_button.setStyleSheet(self.buttonStylePressure(True))
            
        QTimer.singleShot(100, self.fitCanvasToView)

    def fitCanvasToView(self):
        margin = 40
        w = self.drawing_area.width() - margin
        h = self.drawing_area.height() - margin
        
        if w > 0 and h > 0:
            zoom_x = w / float(self.canvas_width)
            zoom_y = h / float(self.canvas_height)
            
            new_zoom = min(zoom_x, zoom_y)
            new_zoom = max(0.05, min(10.0, new_zoom))
            
            self.drawing_area.zoom_factor = new_zoom
            self.drawing_area.view_offset = QPoint(0, 0)
            self.drawing_area.update()

    def clearDrawingCache(self):
        os.makedirs(self.drawing_cache_dir, exist_ok=True)
        try:
            for name in os.listdir(self.drawing_cache_dir):
                if (name.startswith("s") or name.startswith("r")) and (name.endswith(".png") or name.endswith("_elements.json") or name == "sx.json"):
                    path = os.path.join(self.drawing_cache_dir, name)
                    if os.path.isfile(path):
                        os.remove(path)
        except Exception:
            pass

    def keyPressEvent(self, event):
        import time
        if event.key() == Qt.Key_V:
            self.is_v_pressed = True
            self.drawing_area.setCursor(Qt.SizeHorCursor)
        elif event.key() == Qt.Key_C:
            self.is_c_pressed = True
        elif event.key() == Qt.Key_N:
            if not self.drawing_area.text_input_widget.isVisible():
                self.pen_style_combo.showPopup()
        elif event.key() == Qt.Key_R:
            self.showRadiusSliderDialog()
        
        elif event.key() == Qt.Key_Right:
            if len(self.pages_data) > 0:
                new_idx = (self.current_page_index + 1) % len(self.pages_data)
                self.loadPageData(new_idx)
        elif event.key() == Qt.Key_Left:
            if len(self.pages_data) > 0:
                new_idx = (self.current_page_index - 1) % len(self.pages_data)
                self.loadPageData(new_idx)

        elif event.key() == Qt.Key_Alt:
            current_time = int(time.time() * 1000)
            if current_time - self.alt_last_press_time < self.alt_double_click_threshold:
                self.drawing_area.alt_permanent_pan_mode = not self.drawing_area.alt_permanent_pan_mode
                if self.drawing_area.alt_permanent_pan_mode:
                    self.drawing_area.setCursor(Qt.OpenHandCursor)
                else:
                    self.drawing_area.setCursor(Qt.CrossCursor)
            else:
                self.drawing_area.alt_held = True
            self.alt_last_press_time = current_time
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.polyline_mode or self.curve_mode:
                self.drawing_area.finalizePolyline()

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_V:
            self.is_v_pressed = False
            self.drawing_area.setCursor(Qt.ArrowCursor)
        elif event.key() == Qt.Key_C:
            self.is_c_pressed = False
        elif event.key() == Qt.Key_Alt:
            self.drawing_area.alt_held = False
            if not self.drawing_area.alt_permanent_pan_mode:
                self.drawing_area.setCursor(Qt.CrossCursor)
        
        super().keyReleaseEvent(event)

    def showRadiusSliderDialog(self):
        current_val = self.eraser_radius if self.eraser_mode else self.pen_radius
        dialog = RadiusOverlayDialog(current_val, self)
        dialog_x = (self.width() - dialog.width()) // 2
        dialog_y = (self.height() - dialog.height()) // 2
        dialog.move(self.mapToGlobal(QPoint(dialog_x, dialog_y)))
        dialog.slider.valueChanged.connect(self.changeRadiusValue)
        dialog.exec_()

    def showSensitivitySliderDialog(self):
        dialog = RadiusOverlayDialog(self.sensitivity_value, self, is_sensitivity=True)
        dialog_x = (self.width() - dialog.width()) // 2
        dialog_y = (self.height() - dialog.height()) // 2
        dialog.move(self.mapToGlobal(QPoint(dialog_x, dialog_y)))
        dialog.exec_()

    def initUI(self):
        self.setWindowTitle("Kavram")
        self.setWindowIcon(QIcon(resource_path('ikon/kavram.png')))
        self.resize(900, 600)
        self.setStyleSheet("background-color: #222;")

        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("background-color: #222; border-bottom: 2px solid #555;")
        toolbar_frame.setFixedHeight(40)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.setSpacing(10)

        self.file_button = RightClickButton("File")
        self.file_button.setStyleSheet(self.buttonStyle())
        self.file_button.setFixedSize(90, 30)
        self.file_button.clicked.connect(self.importFile)
        self.file_button.rightClicked.connect(self.importReferenceImage)  # Sağ tık referans ekle
        toolbar_layout.addWidget(self.file_button, alignment=Qt.AlignLeft)

        self.save_button = QPushButton()
        self.save_button.setIcon(create_svg_icon(SVG_SAVE_ICON, size=20))
        self.save_button.setStyleSheet(self.buttonStyleMini())
        self.save_button.setFixedSize(30, 30)
        self.save_button.setToolTip("Projeyi Kaydet")
        self.save_button.clicked.connect(self.saveProject)
        toolbar_layout.addWidget(self.save_button, alignment=Qt.AlignLeft)

        page_control_widget = QWidget()
        page_control_widget.setFixedSize(140, 30)
        page_control_layout = QHBoxLayout(page_control_widget)
        page_control_layout.setContentsMargins(0,0,0,0)
        page_control_layout.setSpacing(2)

        self.page_button = PageNavigatorButton("1")
        self.page_button.setStyleSheet(self.buttonStyle())
        self.page_button.setFixedSize(40, 30)
        self.page_button.pageChanged.connect(self.cyclePages)

        self.page_menu = QMenu(self)
        self.page_menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; }")
        self.page_button.setMenu(self.page_menu)
        self.page_menu.aboutToShow.connect(self.refreshPageButtonMenu)
        page_control_layout.addWidget(self.page_button)

        self.add_page_btn = QPushButton("+")
        self.add_page_btn.setStyleSheet(self.buttonStyle())
        self.add_page_btn.setFixedSize(30, 30)
        self.add_page_btn.clicked.connect(self.addNewPage)
        page_control_layout.addWidget(self.add_page_btn)

        self.remove_page_btn = QPushButton("-")
        self.remove_page_btn.setStyleSheet(self.buttonStyle())
        self.remove_page_btn.setFixedSize(30, 30)
        self.remove_page_btn.clicked.connect(self.removePage)
        page_control_layout.addWidget(self.remove_page_btn)

        toolbar_layout.addWidget(page_control_widget, alignment=Qt.AlignLeft)

        self.undo_button = QPushButton()
        self.undo_button.setIcon(create_svg_icon(SVG_UNDO_ICON, size=20))
        self.undo_button.setStyleSheet(self.buttonStyleMini())
        self.undo_button.setFixedSize(30, 30)
        self.undo_button.clicked.connect(self.undo)
        toolbar_layout.addWidget(self.undo_button, alignment=Qt.AlignLeft)

        self.redo_button = QPushButton()
        self.redo_button.setIcon(create_svg_icon(SVG_REDO_ICON, size=20))
        self.redo_button.setStyleSheet(self.buttonStyleMini())
        self.redo_button.setFixedSize(30, 30)
        self.redo_button.clicked.connect(self.redo)
        toolbar_layout.addWidget(self.redo_button, alignment=Qt.AlignLeft)

        self.pen_style_combo = QComboBox()
        self.pen_style_combo.addItems([name for name, _ in self.TOOL_ORDER])
        self.pen_style_combo.setStyleSheet("""
            QComboBox { background-color: transparent; color: white; border: 2px solid #555; border-radius: 8px; padding: 5px 10px; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView { background-color: #444; color: white; selection-background-color: #666; }
        """)
        self.pen_style_combo.setFixedSize(155, 30)
        self.pen_style_combo.currentIndexChanged.connect(self.changePenStyle)
        toolbar_layout.addWidget(self.pen_style_combo, alignment=Qt.AlignLeft)

        self.nav_button = NavigationModeButton(self)
        self.nav_button.rightClicked.connect(self.openResolutionDialog)
        toolbar_layout.addWidget(self.nav_button, alignment=Qt.AlignLeft)

        # S butonu kaldırıldı

        # G butonu (sadece sol tık ile aç/kapa, sağ tık ile menü)
        self.g_button = RightClickButton("G")
        self.g_button.setFixedSize(35, 30)
        self.g_button.setToolTip("Referans görseli tüm sayfalarda göster/gizle (sağ tık: ayarlar)")
        self.g_button.setStyleSheet("""
            QPushButton { background-color: transparent; color: white; font-weight: bold; font-size: 14px; border: 2px solid #555; border-radius: 8px; }
            QPushButton:hover { background-color: #444; color: white; }
        """)
        self.g_button.clicked.connect(self.toggle_global_reference)
        self.g_button.rightClicked.connect(self.showReferenceTransparencyMenu)  # Sağ tık menü
        toolbar_layout.addWidget(self.g_button, alignment=Qt.AlignLeft)

        self.mix_angle_button = MixAngleButton(f"Mix {self.mix_angle}°")
        self.mix_angle_button.setStyleSheet(self.buttonStyle())
        self.mix_angle_button.setFixedSize(70, 30)
        self.mix_angle_button.deltaChanged.connect(self.changeMixAngle)

        self.mix_angle_menu = QMenu(self)
        self.mix_angle_menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; }")
        for angle in range(0, 361, 10):
            if angle == 360:
                angle = 0
            act = self.mix_angle_menu.addAction(f"{angle}°")
            act.triggered.connect(lambda checked, a=angle: self.setMixAngle(a))
            if angle == 0:
                self.mix_angle_menu.addSeparator()
        self.mix_angle_button.setMenu(self.mix_angle_menu)
        self.mix_angle_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mix_angle_button.customContextMenuRequested.connect(self.showMixTypeMenu)
        toolbar_layout.addWidget(self.mix_angle_button, alignment=Qt.AlignLeft)

        self.color_button = QPushButton(f"Color ({len(self.mix_colors)})")
        self.color_button.setStyleSheet(self.buttonStyle())
        self.color_button.setFixedSize(80, 30)
        self.color_menu = QMenu()
        self.color_menu.setStyleSheet("""
            QMenu { background-color: #333; color: white; border: 1px solid #555; padding: 5px; }
            QMenu::item:selected { background-color: #444; }
        """)
        self.updateColorMenu()
        self.color_button.setMenu(self.color_menu)
        toolbar_layout.addWidget(self.color_button, alignment=Qt.AlignLeft)

        self.eraser_button = QPushButton("Eraser")
        self.eraser_button.setStyleSheet(self.buttonStylePressure(self.eraser_mode))
        self.eraser_button.setFixedSize(70, 30)
        self.eraser_button.clicked.connect(self.toggleEraser)
        self.eraser_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.eraser_button.customContextMenuRequested.connect(self.changeBackgroundColor)
        toolbar_layout.addWidget(self.eraser_button, alignment=Qt.AlignLeft)

        self.radius_button = WheelButton(f"R: {self.pen_radius}", parent=self)
        self.radius_button.setStyleSheet(self.buttonStyle())
        self.radius_button.setFixedSize(60, 30)
        self.radius_button.clicked.connect(self.showRadiusMenu)
        toolbar_layout.addWidget(self.radius_button, alignment=Qt.AlignLeft)

        self.layer_button = QPushButton("Çizim")
        self.layer_button.setStyleSheet(self.buttonStyle())
        self.layer_button.setFixedSize(80, 30)
        self.layer_button.clicked.connect(self.toggleLayerPanel)
        self.layer_button.setToolTip("Katman panelini aç / kapat")
        icon = create_svg_icon(SVG_LAYER_DRAWING, 16)
        self.layer_button.setIcon(icon)
        toolbar_layout.addWidget(self.layer_button, alignment=Qt.AlignLeft)

        self.always_top_btn = QPushButton("#")
        self.always_top_btn.setFixedSize(40, 30)
        self.always_top_btn.setStyleSheet(self.buttonStylePressure(self.always_top_mode))
        self.always_top_btn.setToolTip("Seçili Olmayan Katmanları Üstte Tut")
        self.always_top_btn.clicked.connect(self.toggleAlwaysTop)
        toolbar_layout.addWidget(self.always_top_btn, alignment=Qt.AlignLeft)
        self.select_button = QPushButton("S")
        self.select_button.setFixedSize(40, 30)
        self.select_button.setStyleSheet(self.buttonStylePressure(False))
        self.select_button.setToolTip("S modu: piksel seçimi  (A modu ile aynı anda açık olamaz)\n"
                                      "Sürükle: serbest seçim  •  Shift+sürükle: dikdörtgen\n"
                                      "G: taşı  •  S: büyüt/küçült  •  R: döndür  (X / Y: eksen kısıtı)\n"
                                      "D: seçimi başka kareye kopyala  •  Ctrl+D: ara kareleri otomatik oluştur\n"
                                      "Delete: sil  •  Esc: iptal")
        self.select_button.clicked.connect(lambda: self.setEditMode('s'))
        toolbar_layout.addWidget(self.select_button, alignment=Qt.AlignLeft)
        self.point_button = QPushButton("A")
        self.point_button.setFixedSize(40, 30)
        self.point_button.setStyleSheet(self.buttonStylePressure(False))
        self.point_button.setToolTip("A modu: nokta düzenleme  (S modu ile aynı anda açık olamaz)\n"
                                     "Çizimler köşe noktalarıyla görünür. Tıkla: seç  •  Shift: çoklu seçim\n"
                                     "Boşlukta sürükle: kutuyla seç\n"
                                     "G: taşı  •  S: büyüt/küçült  •  R: döndür  (X / Y: eksen kısıtı)\n"
                                     "D: seçili çizgileri başka kareye kopyala  •  Ctrl+D: ara kareleri otomatik oluştur\n"
                                     "Delete: çizgiyi sil  •  Esc: iptal")
        self.point_button.clicked.connect(lambda: self.setEditMode('a'))
        toolbar_layout.addWidget(self.point_button, alignment=Qt.AlignLeft)

        self.lazy_mouse_button = LazyMouseButton(self)
        self.lazy_mouse_button.setFixedSize(33, 30)
        self.lazy_mouse_button.setStyleSheet(self.buttonStylePressure(self.lazy_mouse_enabled))
        self.lazy_mouse_button.setToolTip("Lazy Mouse: Yavaşlatılmış fare (Blender tarzı)\nVarsayılan: R=30, H=15")
        self.lazy_mouse_button.clicked.connect(self.toggleLazyMouse)
        self.lazy_mouse_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lazy_mouse_button.customContextMenuRequested.connect(self.showLazyMouseMenu)
        toolbar_layout.addWidget(self.lazy_mouse_button, alignment=Qt.AlignLeft)

        self.pressure_button = RightClickButton("/", self)
        self.pressure_button.setStyleSheet(self.buttonStylePressure(self.pen_pressure_enabled))
        self.pressure_button.setFixedSize(30, 30)
        self.pressure_button.setToolTip("Sol: Basınç hassasiyeti")
        self.pressure_button.clicked.connect(self.togglePressure)
        toolbar_layout.addWidget(self.pressure_button, alignment=Qt.AlignLeft)

        self.mirror_button = MirrorControlButton("» «")
        self.mirror_button.setStyleSheet(self.buttonStylePressure(self.mirror_mode))
        self.mirror_button.setFixedSize(50, 30)
        self.mirror_button.leftClicked.connect(lambda: self.toggleMirrorMode('vertical'))
        self.mirror_button.rightClicked.connect(lambda: self.toggleMirrorMode('horizontal'))
        toolbar_layout.addWidget(self.mirror_button, alignment=Qt.AlignLeft)

        toolbar_layout.addStretch()

        self.export_button = QPushButton("Export")
        self.export_button.setStyleSheet(self.buttonStyle())
        self.export_button.setFixedSize(90, 30)
        self.export_button.clicked.connect(self.exportFile)
        self.export_button.setContextMenuPolicy(Qt.CustomContextMenu)
        self.export_button.customContextMenuRequested.connect(self.showExportMenu)
        toolbar_layout.addWidget(self.export_button, alignment=Qt.AlignRight)

        self.drawing_button = QPushButton("Drawing")
        self.drawing_button.setStyleSheet(self.buttonStyle())
        self.drawing_button.setFixedSize(90, 30)
        self.drawing_button.clicked.connect(self.triggerCoreSwitcher)
        toolbar_layout.addWidget(self.drawing_button, alignment=Qt.AlignRight)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(toolbar_frame)

        self.drawing_area = DrawingArea(self)

        # Katman paneli (sağ) + tuval
        self.layer_panel = LayerPanel(self.drawing_area, self)
        self.layer_panel.setVisible(QSettings("kavram", "DrawingEditor").value("layerPanelVisible", True, type=bool))
        middle = QHBoxLayout()
        middle.setContentsMargins(0, 0, 0, 0)
        middle.setSpacing(0)
        middle.addWidget(self.drawing_area, 1)
        middle.addWidget(self.layer_panel)
        main_layout.addLayout(middle, 1)

        # Animasyon: soğan zarı + oynatma + zaman çizelgesi (altta)
        self.anim = AnimationController(self)
        self.timeline = TimelinePanel(self, self.anim)
        main_layout.addWidget(self.timeline)
        self.setLayout(main_layout)
        self.drawing_area.layersChanged.connect(self.onLayersChanged)

        QShortcut(QKeySequence("Ctrl+Z"), self, self.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self, self.redo)
        
        QShortcut(QKeySequence("Ctrl+Right"), self, self.goNextPage)
        QShortcut(QKeySequence("Ctrl+Left"), self, self.goPrevPage)
        QShortcut(QKeySequence("Ctrl+Shift+Right"), self, self.duplicateToNextPage)
        QShortcut(QKeySequence("Ctrl+Shift+Left"), self, self.duplicateToPrevPage)

        # Animasyon kısayolları
        QShortcut(QKeySequence("Ctrl+Space"), self, self.anim.toggle_play)
        QShortcut(QKeySequence("Ctrl+Shift+O"), self, lambda: self.timeline.onion_btn.toggle())
        self.esc_shortcut = QShortcut(QKeySequence("Esc"), self, self.onEscapePressed)
        self.esc_shortcut.setEnabled(False)            # yalnızca oynatma / S veya A modunda etkin
        self.anim.playStateChanged.connect(lambda _p: self.updateEscShortcut())

        # S ve A modu ortak kısayolları (yalnız bir mod açıkken etkin; metin yazarken tuşlar çalınmaz)
        self.select_shortcuts = []
        for seq, fn in (("G", lambda: self.drawing_area.modeStartOp('g')),
                        ("S", lambda: self.drawing_area.modeStartOp('s')),
                        ("R", lambda: self.drawing_area.modeStartOp('r')),
                        ("D", lambda: keyframe_copy(self)),
                        ("Ctrl+D", lambda: keyframe_tween(self)),
                        ("X", lambda: self.drawing_area.modeAxis('x')),
                        ("Y", lambda: self.drawing_area.modeAxis('y')),
                        ("Delete", lambda: self.drawing_area.modeDelete())):
            sc = QShortcut(QKeySequence(seq), self, fn)
            sc.setEnabled(False)
            self.select_shortcuts.append(sc)

    def openResolutionDialog(self):
        """Nav butonuna sağ tık ile çözünürlük ayarlarını açar."""
        if len(self.pages_data) > 1 or self.is_project_modified:
            QMessageBox.warning(self, "Uyarı", "Çözünürlük yalnızca boş ve yeni bir projede değiştirilebilir.\n\nYeni, boş bir proje açın.")
            return

        dialog = AspectRatioDialog(self)
        if dialog.exec_():
            settings = dialog.getSettings()
            new_w = settings["width"]
            new_h = settings["height"]
            self.applyNewResolution(new_w, new_h)

    def applyNewResolution(self, w, h):
        """Tuval boyutunu değiştirir; tüm karelerin tüm katmanlarını yeni boyuta uyarlar."""
        if w == self.canvas_width and h == self.canvas_height:
            return

        self.saveCurrentPageData()

        old_w = self.canvas_width
        old_h = self.canvas_height

        self.canvas_width = w
        self.canvas_height = h

        st = self.drawing_area.layer_stack
        meta = st.export_meta()
        for i in range(len(self.pages_data)):
            paths = [layer_path(self.drawing_cache_dir, i, m["id"]) for m in meta]
            paths.append(os.path.join(self.drawing_cache_dir, f"s{i + 1}.png"))      # eski tek parça dosya
            for path in paths:
                if os.path.isfile(path):
                    img = QImage(path)
                    if not img.isNull():
                        fit_to_canvas(img, w, h).save(path, "PNG")
        st.resize(w, h)

        self.drawing_area.mirror_line_x = w // 2
        self.drawing_area.mirror_line_y = h // 2

        scale_x = w / old_w
        scale_y = h / old_h
        for element in self.drawing_area.drawing_elements:
            if element["type"] == "image":
                element["position"][0] = int(element["position"][0] * scale_x)
                element["position"][1] = int(element["position"][1] * scale_y)
                element["current_width"] = int(element["current_width"] * scale_x)
                element["current_height"] = int(element["current_height"] * scale_y)
                element["original_width"] = int(element["original_width"] * scale_x)
                element["original_height"] = int(element["original_height"] * scale_y)

        self.loadPageData(self.current_page_index, save_current=False)
        if hasattr(self, "timeline"):
            self.timeline.schedule_refresh()

        QTimer.singleShot(100, self.fitCanvasToView)

    def importReferenceImage(self):
        """File butonuna sağ tık: referans görsel ekle (sadece 1)"""
        path, _ = _fm.get_open_file_name(self, "Referans Görsel Seç", "",
                                              "Görseller (*.png *.jpg *.jpeg *.bmp *.gif *.webp)", editor="Drawing", double_click="select")
        if path:
            img = QImage(path)
            if not img.isNull():
                self.drawing_area.startReferencePlacement(img)
                self.is_project_modified = True
                # Referans PNF'ye kaydedilmez, sadece DrawingArea'da tutulur

    def toggle_global_reference(self):
        """G butonu sol tık: referans görünürlüğünü aç/kapa"""
        self.global_reference_visible = not self.global_reference_visible
        self.g_button.setStyleSheet(self.buttonStylePressure(self.global_reference_visible))
        self.drawing_area.update()

    def showReferenceTransparencyMenu(self, pos):
        """G butonu sağ tık: saydamlık ve katman konumu menüsü"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #252525;
                color: white;
                border: 1px solid #555;
                padding: 8px;
            }
        """)

        # Saydamlık kaydırıcı
        container = QWidget(menu)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        title = QLabel("Referans Saydamlığı")
        title.setStyleSheet("color: #eee; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        value_label = QLabel()
        value_label.setStyleSheet("color: #aaa; font-size: 10px;")
        value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_label)

        slider = QSlider(Qt.Vertical, container)
        slider.setRange(0, 95)
        slider.setValue(int(self.reference_transparency))
        slider.setFixedHeight(150)
        slider.setToolTip("0 = opak, 95 = neredeyse tamamen saydam")
        slider.setStyleSheet("""
            QSlider::groove:vertical {
                width: 6px; background: #444; border-radius: 3px;
            }
            QSlider::handle:vertical {
                width: 16px; height: 16px; margin: 0 -5px;
                background: #aaa; border: 1px solid #666; border-radius: 8px;
            }
        """)
        layout.addWidget(slider, alignment=Qt.AlignHCenter)

        def update_value(value):
            value_label.setText(f"{int(value)}% saydam")
            self.setReferenceTransparency(value)

        slider.valueChanged.connect(update_value)
        update_value(slider.value())

        slider_action = QWidgetAction(menu)
        slider_action.setDefaultWidget(container)
        menu.addAction(slider_action)

        # Katman konumu butonları (sadece Alt ve Üst)
        button_widget = QWidget(menu)
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)

        btn_top = QPushButton("Üst")
        btn_top.setCheckable(True)
        btn_bottom = QPushButton("Alt")
        btn_bottom.setCheckable(True)

        # Varsayılan olarak "Üst" seçili
        btn_top.setChecked(True)

        def set_position(pos_val):
            self.drawing_area.reference_layer_position = pos_val
            btn_top.setChecked(pos_val == 0)
            btn_bottom.setChecked(pos_val == 1)
            self.drawing_area.update()

        btn_top.clicked.connect(lambda: set_position(0))
        btn_bottom.clicked.connect(lambda: set_position(1))

        button_layout.addWidget(btn_top)
        button_layout.addWidget(btn_bottom)

        button_action = QWidgetAction(menu)
        button_action.setDefaultWidget(button_widget)
        menu.addAction(button_action)

        menu.exec_(self.g_button.mapToGlobal(QPoint(0, self.g_button.height())))

    def setReferenceTransparency(self, value):
        self.reference_transparency = max(0, min(95, int(value)))
        settings = QSettings("kavram", "DrawingEditor")
        settings.setValue("referenceTransparency", self.reference_transparency)
        self.drawing_area.update()

    # Aşağıdaki metotlar artık kullanılmıyor (referans kaydetme/yükleme kaldırıldı)
    def updateCurrentPageReferenceData(self):
        pass  # Referans kaydedilmez

    def loadPageData(self, index, save_current=True, elements=None):
        if 0 <= index < len(self.pages_data):
            if save_current:
                self.saveCurrentPageData()

            self.current_page_index = index
            page_info = self.pages_data[index]

            self.background_color = page_info["background"]

            area = self.drawing_area
            area.undo_stack.clear()
            area.redo_stack.clear()
            area.clearImageCache()
            area.pageChangedReset()

            if elements is not None:
                area.drawing_elements = elements
            else:
                elements_file = os.path.join(self.drawing_cache_dir, f"s{index + 1}_elements.json")
                try:
                    with open(elements_file, 'r', encoding='utf-8') as f:
                        area.drawing_elements = json.load(f)
                except Exception:
                    area.drawing_elements = []
            area.syncPaintedCount()

            # Katman görüntüleri (her katman ayrı dosya; eski tek parça dosya varsa 'Çizim' katmanına alınır)
            area.loadLayersFromCache(self.drawing_cache_dir, index)
            area.layersChanged.emit()
            area.update()

            self.page_button.setText(str(self.current_page_index + 1))

            # Referans yüklenmez (sadece mevcut DrawingArea'daki referans korunur)
            area.placing_reference = False

            if hasattr(self, "anim"):
                self.anim.on_page_changed()
            if hasattr(self, "timeline"):
                self.timeline.sync_current()

    def flushCurrentPageToCache(self):
        """Geçerli kareyi önbelleğe yazar (katman PNG'leri + kayıtlar). Durumu/undo'yu TEMİZLEMEZ.
        Oynatma, dışa aktarma ve proje kaydı bunu kullanır."""
        if 0 <= self.current_page_index < len(self.pages_data):
            try:
                self.drawing_area.saveLayersToCache(self.drawing_cache_dir, self.current_page_index)
                elements_file = os.path.join(self.drawing_cache_dir, f"s{self.current_page_index + 1}_elements.json")
                with open(elements_file, 'w', encoding='utf-8') as f:
                    json.dump(self.drawing_area.drawing_elements, f)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Sayfa kaydedilemedi: {e}")
                return False
            self.pages_data[self.current_page_index]["background"] = self.background_color
        return True

    def saveCurrentPageData(self):
        if 0 <= self.current_page_index < len(self.pages_data):
            if not self.flushCurrentPageToCache():
                return
            self.drawing_area.drawing_elements.clear()
            self.drawing_area.syncPaintedCount()
            self.drawing_area.undo_stack.clear()
            self.drawing_area.redo_stack.clear()

    def showExportMenu(self, pos):
        """Export butonuna sağ tık menüsü"""
        menu = ExportMenu(self, default_callback=lambda: self.setFpsAndExport(self.current_export_fps))
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
        
        save_action = menu.addAction(f"MKV Olarak Kaydet ({self.current_export_fps} fps)")
        font = save_action.font()
        font.setBold(True)
        save_action.setFont(font)
        menu.setDefaultAction(save_action)
        save_action.triggered.connect(lambda: self.setFpsAndExport(self.current_export_fps))
        
        menu.addSeparator()
        
        fps_options = [3, 6, 12, 24, 25, 30, 60]
        
        for fps in fps_options:
            text = f"{fps} fps" if fps == self.current_export_fps else str(fps)
            action = menu.addAction(text)
            action.triggered.connect(lambda checked, f=fps: self.setFpsAndExport(f))
            
        menu.exec_(self.export_button.mapToGlobal(pos))

    def setFpsAndExport(self, fps):
        self.current_export_fps = fps
        settings = QSettings("kavram", "DrawingEditor")
        settings.setValue("exportFPS", fps)
        self.promptMKVExport()

    def promptMKVExport(self):
        """Eski ad korunuyor: artık çok biçimli dışa aktarma penceresini açar."""
        start_export(self, "mkv")

    def goNextPage(self):
        if len(self.pages_data) > 0:
            new_idx = (self.current_page_index + 1) % len(self.pages_data)
            self.loadPageData(new_idx)

    def goPrevPage(self):
        if len(self.pages_data) > 0:
            new_idx = (self.current_page_index - 1) % len(self.pages_data)
            self.loadPageData(new_idx)

    def duplicateToNextPage(self):
        elements_copy = copy.deepcopy(self.drawing_area.drawing_elements)
        self.saveCurrentPageData()
        bg_color = QColor(self.background_color)
        cur = self.current_page_index
        new_idx = cur + 1
        if new_idx >= len(self.pages_data):
            if len(self.pages_data) >= self.max_pages:
                QMessageBox.warning(self, "Uyarı", f"Sayfa sınırı ({self.max_pages}) aşıldı.")
                return
            self.pages_data.append({"background": bg_color, "hold": 1})
        else:
            self.pages_data[new_idx]["background"] = bg_color
        copy_page_files(self.drawing_cache_dir, cur + 1, new_idx + 1)
        self.refreshPageButtonMenu()
        self.loadPageData(new_idx, save_current=False, elements=elements_copy)
        self.is_project_modified = True

    def duplicateToPrevPage(self):
        if self.current_page_index <= 0:
            return
        elements_copy = copy.deepcopy(self.drawing_area.drawing_elements)
        self.saveCurrentPageData()
        bg_color = QColor(self.background_color)
        cur = self.current_page_index
        new_idx = cur - 1
        self.pages_data[new_idx]["background"] = bg_color
        copy_page_files(self.drawing_cache_dir, cur + 1, new_idx + 1)
        self.refreshPageButtonMenu()
        self.loadPageData(new_idx, save_current=False, elements=elements_copy)
        self.is_project_modified = True

    def resetView(self):
        self.drawing_area.zoom_factor = 1.0
        self.drawing_area.view_offset = QPoint(0, 0)
        self.drawing_area.update()

    def toggleAlwaysTop(self):
        self.always_top_mode = not self.always_top_mode
        self.always_top_btn.setStyleSheet(self.buttonStylePressure(self.always_top_mode))
        self.drawing_area.force_active_layer_bottom = self.always_top_mode
        self.drawing_area.update()      # yalnızca yeniden boyama: tekrar oynatma yok

    def toggleLazyMouse(self):
        self.lazy_mouse_enabled = not self.lazy_mouse_enabled
        self.lazy_mouse_button.setStyleSheet(self.buttonStylePressure(self.lazy_mouse_enabled))
        self.updateButtonStyles()
        self.saveLazyMouseSettings()
    
    def showLazyMouseMenu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #333; color: white; border: 1px solid #555; padding: 5px; }
            QMenu::item:selected { background-color: #555; }
        """)
        toggle_action = menu.addAction("✓ Aktif" if self.lazy_mouse_enabled else "Pasif")
        toggle_action.triggered.connect(self.toggleLazyMouse)
        menu.addSeparator()
        radius_menu = menu.addMenu(f"Yarıçap: {self.lazy_radius}")
        for r in [10, 20, 30, 40, 50, 75, 100, 150, 200]:
            action = radius_menu.addAction(f"{r} px")
            action.triggered.connect(lambda checked, val=r: self.setLazyRadius(val))
        factor_menu = menu.addMenu(f"Hassasiyet: {self.lazy_factor}")
        for f in [5, 10, 15, 20, 30, 50, 75, 100]:
            action = factor_menu.addAction(f"{f}")
            action.triggered.connect(lambda checked, val=f: self.setLazyFactor(val))
        menu.addSeparator()
        reset_action = menu.addAction("Varsayılana Sıfırla")
        reset_action.triggered.connect(self.resetLazyMouseSettings)
        menu.exec_(self.lazy_mouse_button.mapToGlobal(pos))
    
    def setLazyRadius(self, value):
        self.lazy_radius = value
        self.lazy_mouse_button.updateButtonText(self)
        self.lazy_mouse_button.updateToolTip(self)
        self.saveLazyMouseSettings()
    
    def setLazyFactor(self, value):
        self.lazy_factor = value
        self.lazy_mouse_button.updateButtonText(self)
        self.lazy_mouse_button.updateToolTip(self)
        self.saveLazyMouseSettings()
    
    def resetLazyMouseSettings(self):
        self.lazy_radius = 30
        self.lazy_factor = 15
        self.lazy_mouse_button.updateButtonText(self)
        self.lazy_mouse_button.updateToolTip(self)
        self.saveLazyMouseSettings()
    
    def saveLazyMouseSettings(self):
        settings = QSettings("kavram", "DrawingEditor")
        settings.setValue("lazyMouse/enabled", self.lazy_mouse_enabled)
        settings.setValue("lazyMouse/radius", self.lazy_radius)
        settings.setValue("lazyMouse/factor", self.lazy_factor)
    
    def loadLazyMouseSettings(self):
        settings = QSettings("kavram", "DrawingEditor")
        self.lazy_mouse_enabled = settings.value("lazyMouse/enabled", False, type=bool)
        self.lazy_radius = settings.value("lazyMouse/radius", 30, type=int)
        self.lazy_factor = settings.value("lazyMouse/factor", 15, type=int)

    def setEditMode(self, mode):
        """S (piksel seçimi) ve A (nokta düzenleme) modları aynı anda açık kalamaz:
        birine basılınca diğeri otomatik kapanır; açık olana tekrar basılınca o kapanır."""
        area = self.drawing_area
        current = 's' if area.select_active else ('a' if area.point_active else None)
        if mode == current:
            mode = None
        area.setSelectActive(mode == 's')
        area.setPointActive(mode == 'a')
        self.select_button.setStyleSheet(self.buttonStylePressure(mode == 's'))
        self.point_button.setStyleSheet(self.buttonStylePressure(mode == 'a'))
        for sc in self.select_shortcuts:
            sc.setEnabled(mode is not None)
        self.updateEscShortcut()

    def updateEscShortcut(self):
        area = self.drawing_area
        self.esc_shortcut.setEnabled(bool(self.anim.is_playing or area.select_active or area.point_active))

    def onEscapePressed(self):
        if self.anim.is_playing:
            self.anim.stop()
        else:
            self.drawing_area.modeEscape()

    def toggleLayerPanel(self):
        visible = not self.layer_panel.isVisible()
        self.layer_panel.setVisible(visible)
        QSettings("kavram", "DrawingEditor").setValue("layerPanelVisible", visible)

    def onLayersChanged(self):
        """Aktif katman değişince araç çubuğundaki katman düğmesini günceller."""
        layer = self.drawing_area.layer_stack.active
        fm = QFontMetrics(self.layer_button.font())
        self.layer_button.setText(fm.elidedText(layer.name, Qt.ElideRight, 48))
        self.layer_button.setToolTip(f"Aktif katman: {layer.name}  (paneli aç/kapat)")
        icon = create_svg_icon(SVG_LAYER_SKETCH if layer.name == "Eskiz" else SVG_LAYER_DRAWING, 16)
        self.layer_button.setIcon(icon)

    def addNewPage(self):
        if len(self.pages_data) >= self.max_pages:
            QMessageBox.warning(self, "Uyarı", f"Sayfa sınırı ({self.max_pages}) aşıldı.")
            return
        self.saveCurrentPageData()
        self.pages_data.append({"background": self.background_color, "hold": 1})
        new_index = len(self.pages_data) - 1
        self.refreshPageButtonMenu()
        self.loadPageData(new_index, save_current=False)
        self.is_project_modified = True

    def insertBlankPageAfter(self):
        """Geçerli karenin hemen sonrasına boş kare ekler (diğer kareleri kaydırır)."""
        if len(self.pages_data) >= self.max_pages:
            QMessageBox.warning(self, "Uyarı", f"Sayfa sınırı ({self.max_pages}) aşıldı.")
            return
        self.saveCurrentPageData()
        cur = self.current_page_index
        total = len(self.pages_data)
        for i in range(total - 1, cur, -1):
            move_page_files(self.drawing_cache_dir, i + 1, i + 2)
        self.pages_data.insert(cur + 1, {"background": QColor(self.background_color), "hold": 1})
        self.refreshPageButtonMenu()
        self.loadPageData(cur + 1, save_current=False)
        self.is_project_modified = True

    def movePage(self, src, dst):
        """Zaman çizelgesinde sürükle-bırak ile kare sırasını değiştirir."""
        n = len(self.pages_data)
        if not (0 <= src < n and 0 <= dst < n) or src == dst:
            return
        current_page_obj = self.pages_data[self.current_page_index]
        self.saveCurrentPageData()
        order = list(range(1, n + 1))
        order.insert(dst, order.pop(src))
        reorder_page_files(self.drawing_cache_dir, order)
        page = self.pages_data.pop(src)
        self.pages_data.insert(dst, page)
        new_cur = next((i for i, p in enumerate(self.pages_data) if p is current_page_obj), 0)
        self.refreshPageButtonMenu()
        self.loadPageData(new_cur, save_current=False)
        self.is_project_modified = True

    def removePage(self):
        if len(self.pages_data) <= 1:
            QMessageBox.warning(self, "Uyarı", "En az bir sayfa kalmalıdır.")
            return
        reply = QMessageBox.question(self, "Sayfa Sil", "Mevcut sayfayı silmek istiyor musunuz?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            delete_page_files(self.drawing_cache_dir, self.current_page_index + 1)
            for i in range(self.current_page_index, len(self.pages_data) - 1):
                move_page_files(self.drawing_cache_dir, i + 2, i + 1)
            self.pages_data.pop(self.current_page_index)
            if self.current_page_index >= len(self.pages_data):
                self.current_page_index = len(self.pages_data) - 1
            self.drawing_area.undo_stack.clear()
            self.drawing_area.redo_stack.clear()
            self.refreshPageButtonMenu()
            self.loadPageData(self.current_page_index, save_current=False)
            self.is_project_modified = True

    def cyclePages(self, delta):
        new_index = self.current_page_index + delta
        if 0 <= new_index < len(self.pages_data):
            self.loadPageData(new_index)

    def refreshPageButtonMenu(self):
        self.page_menu.clear()
        for i in range(len(self.pages_data)):
            action = self.page_menu.addAction(f"Sayfa {i+1}")
            action.triggered.connect(lambda checked, idx=i: self.loadPageData(idx))
        if hasattr(self, "timeline"):
            self.timeline.schedule_refresh()

    def changeMixAngle(self, delta):
        self.mix_angle = (self.mix_angle + delta) % 360
        self.mix_angle_button.setText(f"Mix {self.mix_angle}°")

    def setMixAngle(self, angle):
        self.mix_angle = angle
        self.mix_angle_button.setText(f"Mix {self.mix_angle}°")

    def showMixTypeMenu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; }")
        menu.addAction("--- Mix Modes ---").setEnabled(False)
        types = [
            ('Random (Rastgele)', 'random'), 
            ('Sequential (Sıralı)', 'sequential'), 
            ('Gradient (Açısal)', 'gradient'), 
            ('Smooth (Pürüzsüz)', 'smooth'), 
            ('Harman (Doku)', 'harman'),
            ('Gradyan Geçiş (Yumuşak)', 'gradient_soft'),
            ('Mermer Efekti (Marble)', 'marble'),
            ('Renk Serpiştirme (Splatter)', 'splatter'),
            ('Dalgalı (Wave)', 'wave'),
            ('Piksel Gürültüsü (Pixel)', 'pixel'),
            ('Sünger (Sponge)', 'sponge'),
            ('Gökkuşağı Dairesel (Radial)', 'radial'),
            ('Puslu (Mist)', 'mist')
        ]
        for label, key in types:
            action = menu.addAction(label)
            action.setCheckable(True)
            if self.mix_mode == key:
                action.setChecked(True)
            action.triggered.connect(lambda checked, k=key: self.setMixMode(k))
        menu.addSeparator()
        menu.addAction(f"--- Active Mix Colors ({len(self.mix_colors)}) ---").setEnabled(False)
        strip_widget = QWidgetAction(menu)
        strip = ColorHistoryStrip(self.mix_colors)
        strip.colorSelected.connect(self.onHistoryColorSelected)
        strip_widget.setDefaultWidget(strip)
        menu.addAction(strip_widget)
        menu.exec_(self.mix_angle_button.mapToGlobal(pos))

    def updateColorMenu(self):
        self.color_menu.clear()
        select_action = self.color_menu.addAction("Select Single Color")
        select_action.triggered.connect(self.changeColor)
        add_action = self.color_menu.addAction("Add Color to Mix (+)")
        add_action.triggered.connect(self.addColorToMix)
        self.color_menu.addSeparator()
        history_label_action = QWidgetAction(self.color_menu)
        history_label = QLabel("  Color History:", self.color_menu)
        history_label.setStyleSheet("color: #aaa; font-weight: bold; padding: 2px 5px;")
        history_label_action.setDefaultWidget(history_label)
        self.color_menu.addAction(history_label_action)
        for i, colors in enumerate(reversed(self.mix_history)):
            action_widget = QWidgetAction(self.color_menu)
            strip = ColorHistoryStrip(colors)
            strip.colorSelected.connect(self.onHistoryColorSelected)
            action_widget.setDefaultWidget(strip)
            self.color_menu.addAction(action_widget)

    def onHistoryColorSelected(self, single_color, mix_colors):
        if single_color:
            self.pen_color = single_color
            self.mix_colors = [single_color]
            self.eraser_mode = False
            self.drawing_area.cancelImagePlacement()
            self.color_button.setText("Color (1)")
            if not self.mix_history or self.mix_history[-1] != [single_color]:
                self.mix_history.append([single_color])
                self.updateColorMenu()
        elif mix_colors:
            self.mix_colors = list(mix_colors)
            self.pen_color = mix_colors[0]
            self.eraser_mode = False
            self.drawing_area.cancelImagePlacement()
            self.color_button.setText(f"Color ({len(self.mix_colors)})")
        self.color_menu.close()
        self.updateButtonStyles()

    def buttonStyle(self):
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 14px; font-weight: bold;
                border: 2px solid #555; border-radius: 8px; padding: 5px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
            QPushButton::menu-indicator { image: none; }
        """

    def buttonStyleMini(self):
        return """
            QPushButton {
                background-color: transparent; color: white; font-size: 16px;
                border: 2px solid #555; border-radius: 8px; padding: 5px;
            }
            QPushButton:hover { background-color: #444; }
            QPushButton:pressed { background-color: #666; }
        """

    def buttonStylePressure(self, pressed):
        if pressed:
            return """
                QPushButton {
                    background-color: #555; color: white; font-size: 16px;
                    border: 2px solid #555; border-radius: 8px; padding: 5px;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: transparent; color: white; font-size: 16px;
                    border: 2px solid #555; border-radius: 8px; padding: 5px;
                }
                QPushButton:hover { background-color: #444; }
                QPushButton:pressed { background-color: #666; }
            """

    def importFile(self):
        options = QFileDialog.Options()
        file_filter = "Supported Files (*.pnf *.drawing *.png *.jpg *.jpeg *.bmp *.gif *.webp);;Project Files (*.pnf *.drawing);;Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.webp)"
        file_path, _ = _fm.get_open_file_name(
            self, "Import Drawing or Image", DrawingEditorWindow.DEFAULT_BASE_DIR,
            file_filter,
            options=options
        , editor="Drawing")
        if file_path:
            self.load_image_from_path(file_path)

    def saveProject(self):
        if self.current_file_path:
            self._save_to_path(self.current_file_path)
            _fm.notify_saved(self)
        else:
            self.exportFile()

    def _save_to_path(self, path):
        # Not: durumu/undo'yu temizlemeden yalnız önbelleğe yazar
        self.flushCurrentPageToCache()

        st = self.drawing_area.layer_stack
        meta = st.export_meta()
        project_data = []
        for i, page in enumerate(self.pages_data):
            bg_color = page["background"]
            bg_list = [bg_color.red(), bg_color.green(), bg_color.blue(), bg_color.alpha()]

            layers_b64 = {}
            for m in meta:
                lp = layer_path(self.drawing_cache_dir, i, m["id"])
                if os.path.exists(lp):
                    with open(lp, 'rb') as img_f:
                        layers_b64[str(m["id"])] = base64.b64encode(img_f.read()).decode('utf-8')

            legacy_png = os.path.join(self.drawing_cache_dir, f"s{i + 1}.png")
            legacy_b64 = ""
            if not layers_b64 and os.path.exists(legacy_png):
                with open(legacy_png, 'rb') as img_f:
                    legacy_b64 = base64.b64encode(img_f.read()).decode('utf-8')

            elements_file = os.path.join(self.drawing_cache_dir, f"s{i + 1}_elements.json")
            elements_data = []
            if os.path.exists(elements_file):
                with open(elements_file, 'r', encoding='utf-8') as f:
                    elements_data = json.load(f)

            page_dict = {
                "elements": elements_data,
                "image_data": legacy_b64,
                "layers": layers_b64,
                "hold": max(1, int(page.get("hold", 1))),
                "background": bg_list,
                "resolution": {"width": self.canvas_width, "height": self.canvas_height}
            }
            project_data.append(page_dict)

        full_data = {
            "version": 2,
            "pages": project_data,
            "layers_meta": meta,
            "active_layer": st.active.id,
            "global_reference_visible": self.global_reference_visible,
            "reference_transparency": self.reference_transparency
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(full_data, f)

        self.current_file_path = path
        self.is_project_modified = False

    def exportFile(self):
        self.flushCurrentPageToCache()

        QDir().mkpath(DrawingEditorWindow.DEFAULT_BASE_DIR)
        options = QFileDialog.Options()

        file_filter = "Project Native Format (*.pnf);;PDF Files (*.pdf);;PNG Files (*.png);;Drawing Files (*.drawing);;JPEG Files (*.jpg *.jpeg);;BMP Files (*.bmp);;All Files (*)"
        default_filter = "Project Native Format (*.pnf)"

        file_path, selected_filter = _fm.get_save_file_name(
            self, "Projeyi Dışa Aktar", self.current_file_path or DrawingEditorWindow.DEFAULT_BASE_DIR,
            file_filter,
            default_filter,
            options=options
        , editor="Drawing")

        if not file_path:
            return

        if selected_filter.startswith("Project Native Format") or file_path.lower().endswith(".pnf"):
            if not file_path.lower().endswith(".pnf"):
                file_path += ".pnf"
            try:
                self._save_to_path(file_path)
                _fm.notify_saved(self)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya kaydedilemedi: {e}")

        elif selected_filter == "Drawing Files (*.drawing)" or file_path.lower().endswith(".drawing"):
            if not file_path.lower().endswith(".drawing"):
                file_path += ".drawing"
            try:
                payload = {"version": 2,
                           "resolution": {"width": self.canvas_width, "height": self.canvas_height},
                           "elements": self.drawing_area.drawing_elements}
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, indent=4)
                _fm.notify_saved(self)
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya kaydedilemedi: {e}")

        elif selected_filter == "PDF Files (*.pdf)" or file_path.lower().endswith(".pdf"):
            if not file_path.lower().endswith(".pdf"):
                file_path += ".pdf"
            try:
                printer = QPrinter(QPrinter.HighResolution)
                printer.setOutputFormat(QPrinter.PdfFormat)
                printer.setOutputFileName(file_path)
                painter = QPainter(printer)
                try:
                    st = self.drawing_area.layer_stack
                    meta = st.export_meta()
                    for i, page_data in enumerate(self.pages_data):
                        if i > 0:
                            printer.newPage()
                        bg = QColor(page_data.get("background", QColor("#333")))
                        image = composite_page(self.drawing_cache_dir, i, meta, st.w, st.h, bg)

                        rect = painter.viewport()
                        size = image.size()
                        size.scale(rect.size(), Qt.KeepAspectRatio)
                        painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
                        painter.setWindow(image.rect())
                        painter.drawImage(0, 0, image)

                    painter.end()
                    _fm.notify_saved(self)
                except Exception as e:
                    painter.end()
                    raise e
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"PDF dışa aktarılamadı: {e}")
        else:
            if selected_filter == "JPEG Files (*.jpg *.jpeg)":
                if not file_path.lower().endswith((".jpg", ".jpeg")):
                    file_path += ".jpg"
                file_format = "JPEG"
            elif selected_filter == "BMP Files (*.bmp)":
                if not file_path.lower().endswith(".bmp"):
                    file_path += ".bmp"
                file_format = "BMP"
            else:
                if not file_path.lower().endswith(".png"):
                    file_path += ".png"
                file_format = "PNG"

            if file_format == "PNG":
                export_img = self.drawing_area.flattenCurrent(None)          # saydam arka plan
            else:
                export_img = self.drawing_area.flattenCurrent(QColor(self.background_color)).convertToFormat(QImage.Format_RGB32)
            if not export_img.save(file_path, file_format):
                QMessageBox.critical(self, "Hata", "Çizim dışa aktarılamadı.")
            else:
                _fm.notify_saved(self)

    def load_image_from_path(self, file_path):
        if file_path.lower().endswith(".pnf"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, list):
                    project_data = data
                    global_ref_vis = True
                else:
                    project_data = data.get("pages", [])
                    global_ref_vis = data.get("global_reference_visible", True)
                    if "reference_transparency" in data:
                        self.reference_transparency = max(0, min(95, int(data.get("reference_transparency", self.reference_transparency))))
                        QSettings("kavram", "DrawingEditor").setValue("referenceTransparency", self.reference_transparency)

                self.global_reference_visible = global_ref_vis
                self.g_button.setStyleSheet(self.buttonStylePressure(self.global_reference_visible))

                is_empty_project = (len(self.pages_data) == 1 and len(self.drawing_area.drawing_elements) == 0)

                if is_empty_project:
                    self.clearDrawingCache()
                    self.pages_data.clear()
                    start_index = 0
                else:
                    self.saveCurrentPageData()
                    start_index = len(self.pages_data)

                file_layers_meta = data.get("layers_meta") if isinstance(data, dict) else None

                if isinstance(project_data, list) and len(project_data) > 0:
                    if "resolution" in project_data[0]:
                        res = project_data[0]["resolution"]
                        self.applyNewResolution(res.get("width", 1100), res.get("height", 600))

                    # Boş projeye açılıyorsa dosyanın katman yapısı aynen benimsenir
                    adopt_layers = bool(file_layers_meta) and is_empty_project
                    if adopt_layers:
                        self.drawing_area.layer_stack.import_meta(file_layers_meta, data.get("active_layer"))
                    current_ids = {str(m["id"]) for m in self.drawing_area.layer_stack.export_meta()}

                    for i, page in enumerate(project_data):
                        bg_list = page.get("background", [51, 51, 51, 255])
                        bg_color = QColor(bg_list[0], bg_list[1], bg_list[2], bg_list[3])
                        
                        page_idx = start_index + i
                        self.pages_data.append({"background": bg_color, "hold": max(1, int(page.get("hold", 1)))})
                        
                        new_base = os.path.join(self.drawing_cache_dir, f"s{page_idx + 1}")

                        page_layers = page.get("layers") or {}
                        if page_layers and set(page_layers.keys()) <= current_ids:
                            for lid, b64 in page_layers.items():
                                try:
                                    with open(layer_path(self.drawing_cache_dir, page_idx, int(lid)), 'wb') as img_f:
                                        img_f.write(base64.b64decode(b64))
                                except Exception:
                                    pass
                        elif page_layers:
                            # Katman yapısı uyuşmuyor (projeye ekleme): sayfayı düzleştirip 'Çizim' katmanına al
                            try:
                                items = []
                                for fm in (file_layers_meta or []):
                                    b64 = page_layers.get(str(fm["id"]))
                                    if b64:
                                        li = QImage()
                                        li.loadFromData(base64.b64decode(b64), "PNG")
                                        items.append((li, fm.get("visible", True), float(fm.get("opacity", 1.0)), fm.get("blend", "normal")))
                                flat = composite_images(items, self.canvas_width, self.canvas_height, None)
                                flat.save(f"{new_base}.png", "PNG")
                            except Exception:
                                pass
                        else:
                            b64_image = page.get("image_data", "")
                            if b64_image:
                                try:
                                    with open(f"{new_base}.png", 'wb') as img_f:
                                        img_f.write(base64.b64decode(b64_image))
                                except Exception:
                                    pass
                        
                        elements_data = page.get("elements", [])
                        elements_file = f"{new_base}_elements.json"
                        with open(elements_file, 'w', encoding='utf-8') as ef:
                            json.dump(elements_data, ef, indent=4)

                if len(self.pages_data) > 0:
                    self.refreshPageButtonMenu()
                    self.loadPageData(start_index, save_current=False)
                    self.drawing_area.layersChanged.emit()

                    if is_empty_project:
                        self.current_file_path = file_path
                        self.setWindowTitle(f"Kavram - {os.path.basename(file_path)}")
                        self.is_project_modified = False
                        
                    QTimer.singleShot(150, self.fitCanvasToView)

            except Exception as e:
                QMessageBox.critical(self, "Hata", f"PNF dosyası yüklenemedi: {e}")

        elif file_path.lower().endswith(".drawing"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                elems = data.get("elements", []) if isinstance(data, dict) else data
                self.drawing_area.saveStateForUndo()
                self.drawing_area.drawing_elements.extend(elems)
                self.drawing_area.updateImageFromElements()      # yalnızca yeni kayıtlar çizilir
                self.is_project_modified = True
            except Exception as e:
                QMessageBox.critical(self, "Hata", f".drawing dosyası yüklenemedi: {e}")
        else:
            imported_image = QImage(file_path)
            if imported_image.isNull():
                QMessageBox.critical(self, "Hata", "Could not load image.")
                return
            imported_image = imported_image.convertToFormat(QImage.Format_ARGB32)
            extracted_colors = []
            small_thumb = imported_image.scaled(50, 50, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            for y in range(0, 50, 10):
                for x in range(0, 50, 10):
                    c = small_thumb.pixelColor(x, y)
                    is_unique = True
                    for ex in extracted_colors:
                        if abs(ex.red() - c.red()) < 30 and abs(ex.green() - c.green()) < 30 and abs(ex.blue() - c.blue()) < 30:
                            is_unique = False
                            break
                    if is_unique:
                        extracted_colors.append(c)
                    if len(extracted_colors) >= 8:
                        break
                if len(extracted_colors) >= 8:
                    break
            if extracted_colors:
                self.mix_history.append(extracted_colors)
                self.updateColorMenu()
            self.placing_image = True
            self.text_mode = False
            self.eraser_mode = False
            self.drawing_area.text_input_widget.hide()
            self.drawing_area.startImagePlacement(imported_image)
            self.updateButtonStyles()

    def toggleEraser(self):
        self.eraser_mode = not self.eraser_mode
        self.text_mode = False
        self.drawing_area.cancelImagePlacement()

        if self.eraser_mode:
            self.normal_tool_index = self.current_tool_index
            self.current_tool_index = self.eraser_tool_index

            if self.eraser_tool_index == 4:
                self.pen_radius = 1
                self.solid_fill_mode = True
            else:
                self.pen_radius = self.tool_radiuses.get(self.eraser_tool_index, 15)
                self.solid_fill_mode = (self.eraser_tool_index == 4)

            self.pen_style_combo.blockSignals(True)
            combo_idx = -1
            for i, (name, logic_id) in enumerate(self.TOOL_ORDER):
                if logic_id == self.eraser_tool_index:
                    combo_idx = i
                    break
            if combo_idx != -1:
                self.pen_style_combo.setCurrentIndex(combo_idx)
            self.pen_style_combo.blockSignals(False)

        else:
            self.eraser_tool_index = self.current_tool_index
            self.current_tool_index = self.normal_tool_index

            self.pen_radius = self.tool_radiuses.get(self.normal_tool_index, 8)
            self.solid_fill_mode = (self.normal_tool_index == 4)
            if self.solid_fill_mode:
                self.pen_radius = 1

            self.pen_style_combo.blockSignals(True)
            combo_idx = -1
            for i, (name, logic_id) in enumerate(self.TOOL_ORDER):
                if logic_id == self.normal_tool_index:
                    combo_idx = i
                    break
            if combo_idx != -1:
                self.pen_style_combo.setCurrentIndex(combo_idx)
            self.pen_style_combo.blockSignals(False)

        self.updateButtonStyles()
        self.radius_button.setText(f"R: {self.pen_radius}")

    def toggleMirrorMode(self, axis):
        if self.mirror_mode and self.mirror_axis == axis:
             self.mirror_mode = False
        else:
             self.mirror_mode = True
             self.mirror_axis = axis

        if self.mirror_mode:
            self.drawing_area.mirror_line_x = self.drawing_area.image.width() // 2
            self.drawing_area.mirror_line_y = self.drawing_area.image.height() // 2

        self.updateButtonStyles()
        self.drawing_area.update()

    def changeColor(self):
        dialog = CircleBrightnessDialog(initialColor=self.pen_color, parent=self)
        button_pos = self.color_button.mapToGlobal(QPoint(0, self.color_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            selected = dialog.getSelectedColor()
            self.pen_color = selected
            self.mix_colors = [selected]
            self.mix_history.append([selected])
            self.updateColorMenu()
            self.eraser_mode = False
            self.drawing_area.cancelImagePlacement()
            self.updateButtonStyles()
            self.color_button.setText("Color (1)")

    def addColorToMix(self):
        dialog = CircleBrightnessDialog(initialColor=self.pen_color, parent=self)
        button_pos = self.color_button.mapToGlobal(QPoint(0, self.color_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            selected = dialog.getSelectedColor()
            if len(self.mix_colors) >= 4:
                self.mix_colors.pop(0)
            self.mix_colors.append(selected)
            self.pen_color = selected
            self.mix_history.append(list(self.mix_colors))
            self.updateColorMenu()
            self.color_button.setText(f"Color ({len(self.mix_colors)})")

    def setMixMode(self, mode):
        self.mix_mode = mode

    def changePenStyle(self, index):
        if self.polyline_mode or self.curve_mode:
            self.drawing_area.finalizePolyline()

        logic_id = self.TOOL_ORDER[index][1]
        self.current_tool_index = logic_id

        if self.eraser_mode:
            self.eraser_tool_index = logic_id
        else:
            self.normal_tool_index = logic_id

        self.polyline_mode = False
        self.curve_mode = False
        self.solid_fill_mode = False
        self.text_mode = False

        if logic_id == 0:
            pass
        elif logic_id == 1:
            pass
        elif logic_id == 2:
            pass
        elif logic_id == 3:
            self.polyline_mode = True
        elif logic_id == 4:
            self.solid_fill_mode = True
            self.pen_radius = 1
            self.radius_button.setText(f"R: 1")
        elif logic_id == 5:
            self.curve_mode = True
        elif logic_id == 35:
            self.text_mode = True
            font_size = max(10, self.pen_radius * 2)
            self.drawing_area.text_input_widget.setFont(QFont("Arial", font_size))
        elif logic_id == 36:
            self.polyline_mode = True

        if logic_id != 4:
             self.pen_radius = self.tool_radiuses.get(logic_id, self.pen_radius)
             self.radius_button.setText(f"R: {self.pen_radius}")
        self.updateButtonStyles()

    def clearDrawing(self):
        self.updateButtonStyles()
        self.drawing_area.clear()

    def changeRadiusValue(self, new_value):
        if self.solid_fill_mode or (self.eraser_mode and self.eraser_tool_index == 4) or (not self.eraser_mode and self.normal_tool_index == 4):
             self.pen_radius = 1
             self.radius_button.setText("R: 1")
             return

        if self.eraser_mode:
            self.eraser_radius = new_value
            self.pen_radius = new_value
            self.tool_radiuses[self.eraser_tool_index] = new_value
            self.radius_button.setText(f"R: {self.pen_radius}")
        else:
            self.pen_radius = new_value
            self.tool_radiuses[self.normal_tool_index] = new_value
            self.radius_button.setText(f"R: {self.pen_radius}")

            if self.text_mode:
                self.drawing_area.text_input_widget.setFont(QFont("Arial", max(10, self.pen_radius * 2)))
                self.drawing_area.text_input_widget.updateGeometry()

    def showRadiusMenu(self):
        if self.solid_fill_mode:
             return
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
        custom_values = [1, 3, 5]
        custom_values.extend(range(10, 61, 5))
        for val in custom_values:
            action = menu.addAction(f"{val}")
            action.triggered.connect(lambda checked, v=val: self.changeRadiusValue(v))
        menu.exec_(self.radius_button.mapToGlobal(QPoint(0, self.radius_button.height())))

    def togglePressure(self):
        self.pen_pressure_enabled = not self.pen_pressure_enabled
        self.drawing_area.cancelImagePlacement()
        self.updateButtonStyles()

    def updateButtonStyles(self):
        self.eraser_button.setStyleSheet(self.buttonStylePressure(self.eraser_mode))
        self.pressure_button.setStyleSheet(self.buttonStylePressure(self.pen_pressure_enabled))
        self.mirror_button.setStyleSheet(self.buttonStylePressure(self.mirror_mode))
        self.always_top_btn.setStyleSheet(self.buttonStylePressure(self.always_top_mode))
        self.lazy_mouse_button.setStyleSheet(self.buttonStylePressure(self.lazy_mouse_enabled))
        self.g_button.setStyleSheet(self.buttonStylePressure(self.global_reference_visible))
        if self.placing_image:
            self.file_button.setStyleSheet(self.buttonStylePressure(True))
        elif self.drawing_area.placing_reference:
            self.file_button.setStyleSheet(self.buttonStylePressure(True))
        else:
            self.file_button.setStyleSheet(self.buttonStyle())
        self.nav_button.updateStyle()

    def undo(self):
        self.drawing_area.undo()
    def redo(self):
        self.drawing_area.redo()
    def getCurrentPen(self):
        color = self.background_color if self.eraser_mode else self.pen_color
        return color, self.pen_radius
    def changeBackgroundColor(self, pos=None):
        dialog = CircleBrightnessDialog(initialColor=self.background_color, parent=self)
        button_pos = self.eraser_button.mapToGlobal(QPoint(0, self.eraser_button.height()))
        dialog.move(button_pos)
        if dialog.exec_():
            new_color = dialog.getSelectedColor()
            if self.background_color != new_color:
                self.background_color = new_color
                settings = QSettings("kavram", "DrawingEditor")
                settings.setValue("backgroundColor", new_color.name())
                if 0 <= self.current_page_index < len(self.pages_data):
                    self.pages_data[self.current_page_index]["background"] = new_color
                self.drawing_area.update()          # arka plan paintEvent'te çizilir
                if hasattr(self, "timeline"):
                    self.timeline.sync_current()
                    self.timeline._content_changed()

    def triggerCoreSwitcher(self):
        main_window = self.window()
        if hasattr(main_window, 'showSwitcher'):
            main_window.showSwitcher()
        else:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = DrawingEditorWindow()
    editor.show()
    sys.exit(app.exec_())
