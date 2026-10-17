# Kavram - küçük widget ve diyaloglar
from drawing_common import *

class AspectRatioPreviewWidget(QWidget):
    """
    Kullanıcının seçtiği çözünürlüğü ve en-boy oranını,
    ekstrem değerlerde bile kusursuz oranlayıp görselleştiren şık önizleme tuvali.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.target_width = 1920
        self.target_height = 1080
        self.setMinimumSize(240, 200)

    def update_dimensions(self, width, height):
        self.target_width = max(1, width)
        self.target_height = max(1, height)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        painter.fillRect(rect, QColor("#111111"))

        margin = 35
        widget_w = rect.width() - (margin * 2)
        widget_h = rect.height() - (margin * 2)
        
        ratio = self.target_width / self.target_height
        
        if (widget_w / ratio) <= widget_h:
            preview_w = widget_w
            preview_h = widget_w / ratio
        else:
            preview_h = widget_h
            preview_w = widget_h * ratio

        min_thickness = 10.0
        if preview_w < min_thickness:
            preview_w = min_thickness
        if preview_h < min_thickness:
            preview_h = min_thickness

        x = (rect.width() - preview_w) / 2
        y = (rect.height() - preview_h) / 2

        preview_rect = QRectF(x, y, preview_w, preview_h)
        painter.setBrush(QBrush(QColor(255, 255, 255, 8)))
        
        pen = QPen(QColor("#555555"), 1.5)
        painter.setPen(pen)
        painter.drawRoundedRect(preview_rect, 4, 4)

        info_area_height = 32
        info_rect = QRectF(0, rect.height() - info_area_height, rect.width(), info_area_height)
        painter.fillRect(info_rect, QColor("#090909"))
        
        painter.setPen(QPen(QColor("#333333"), 1))
        painter.drawLine(0, int(rect.height() - info_area_height), rect.width(), int(rect.height() - info_area_height))

        painter.setPen(QColor("#aaaaaa"))
        painter.setFont(QFont("Segoe UI", 8, QFont.Bold))
        
        gcd = math.gcd(self.target_width, self.target_height)
        simple_w = self.target_width // gcd
        simple_h = self.target_height // gcd
        ratio_text = f"{simple_w}:{simple_h}"
        
        painter.drawText(info_rect, Qt.AlignCenter, f"{self.target_width} x {self.target_height}  •  ({ratio_text})")


class AspectRatioDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Çözünürlük (Tuval Boyutu)")
        self.setWindowIcon(QIcon(resource_path('ikon/kavram.png')))
        self.setModal(True)
        self.resize(580, 320)

        self.setStyleSheet("""
            QDialog {
                background-color: #222222;
                color: #FFFFFF;
            }
            QLabel {
                color: #aaaaaa;
                font-family: 'Segoe UI', Arial;
                font-size: 11px;
                font-weight: bold;
            }
            QLabel#section_title {
                color: #eeeeee;
                font-size: 12px;
                font-weight: bold;
            }
            QComboBox {
                background-color: transparent;
                color: white;
                border: 2px solid #555555;
                border-radius: 8px;
                padding: 5px 10px;
                font-family: 'Segoe UI';
                font-size: 12px;
            }
            QComboBox:hover {
                background-color: #444444;
            }
            QComboBox::drop-down {
                border: none;
                width: 0px; 
            }
            QComboBox QAbstractItemView {
                background-color: #222222;
                color: white;
                border: 2px solid #555555;
                selection-background-color: #444444;
                selection-color: white;
                outline: none;
            }
            QSpinBox {
                background-color: transparent;
                color: white;
                border: 2px solid #555555;
                border-radius: 8px;
                padding: 5px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
            QSpinBox:hover {
                background-color: #444444;
            }
            QSpinBox:focus {
                border: 2px solid #888888;
            }
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 8px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:pressed {
                background-color: #666666;
            }
            QFrame#divider {
                background-color: #333333;
                max-height: 1px;
                min-height: 1px;
            }
            QFrame#sidebar {
                background-color: #1a1a1a;
                border: 1px solid #333333;
                border-radius: 8px;
            }
        """)

        # Varsayılanlar başa eklendi
        self.presets = {
            "Varsayılan": [
                ("Klasik Kavram (1100 x 600)", 1100, 600),
                ("Standart Full HD (1920 x 1080)", 1920, 1080),
                ("Kare Tuval (1080 x 1080)", 1080, 1080)
            ],
            "Geniş Ekran (16:9)": [
                ("3840 x 2160 - 4K Ultra HD", 3840, 2160),
                ("2560 x 1440 - 2K / QHD", 2560, 1440),
                ("1920 x 1080 - Full HD", 1920, 1080)
            ],
            "Dikey & Sosyal Medya": [
                ("1080 x 1920 - Reels & TikTok", 1080, 1920),
                ("1080 x 1350 - Instagram Post 4:5", 1080, 1350),
                ("1080 x 1080 - Kare Post 1:1", 1080, 1080)
            ],
            "Kitap, Manga & Yayın": [
                ("2480 x 3508 - A4 Baskı / PDF", 2480, 3508),
                ("1748 x 2480 - A5 Kitap / PDF", 1748, 2480),
                ("1200 x 1600 - 3:4 Dijital Manga", 1200, 1600),
                ("1500 x 2100 - Yüksek Çözünürlüklü Manga", 1500, 2100),
                ("800 x 1280 - Webtoon Panel Parçası", 800, 1280)
            ],
            "Özel Boyut": []
        }

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)

        left_panel.addWidget(QLabel("EN-BOY ORANI:", self))
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(list(self.presets.keys()))
        left_panel.addWidget(self.ratio_combo)

        left_panel.addWidget(QLabel("HAZIR ÇÖZÜNÜKLER:", self))
        self.preset_combo = QComboBox()
        left_panel.addWidget(self.preset_combo)

        divider = QFrame()
        divider.setObjectName("divider")
        left_panel.addWidget(divider)

        dim_layout = QHBoxLayout()
        dim_layout.setSpacing(10)
        
        width_box = QVBoxLayout()
        width_box.setSpacing(4)
        width_box.addWidget(QLabel("GENİŞLİK (PX):"))
        self.width_input = QSpinBox()
        self.width_input.setRange(8, 30000) 
        self.width_input.setValue(1100)
        self.width_input.setButtonSymbols(QSpinBox.NoButtons) 
        width_box.addWidget(self.width_input)
        
        height_box = QVBoxLayout()
        height_box.setSpacing(4)
        height_box.addWidget(QLabel("YÜKSEKLİK (PX):"))
        self.height_input = QSpinBox()
        self.height_input.setRange(8, 30000)
        self.height_input.setValue(600)
        self.height_input.setButtonSymbols(QSpinBox.NoButtons) 
        height_box.addWidget(self.height_input)

        dim_layout.addLayout(width_box)
        dim_layout.addLayout(height_box)
        left_panel.addLayout(dim_layout)

        self.info_label = QLabel("Bilgi: 0.66 Megapiksel")
        self.info_label.setStyleSheet("color: #777777; font-size: 10px;")
        left_panel.addWidget(self.info_label)

        left_panel.addStretch()

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.cancel_button = QPushButton("İptal")
        self.cancel_button.clicked.connect(self.reject)
        
        self.ok_button = QPushButton("Kaydet")
        self.ok_button.setStyleSheet("""
            QPushButton {
                border-color: #777777;
                background-color: #2a2a2a;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
            }
        """)
        self.ok_button.clicked.connect(self.accept)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        left_panel.addLayout(button_layout)

        right_panel_container = QFrame()
        right_panel_container.setObjectName("sidebar")
        right_panel_layout = QVBoxLayout(right_panel_container)
        right_panel_layout.setContentsMargins(10, 10, 10, 10)
        
        preview_title = QLabel("ÖNİZLEME")
        preview_title.setObjectName("section_title")
        preview_title.setAlignment(Qt.AlignCenter)
        right_panel_layout.addWidget(preview_title)

        self.preview_widget = AspectRatioPreviewWidget()
        right_panel_layout.addWidget(self.preview_widget)

        main_layout.addLayout(left_panel, stretch=3)
        main_layout.addWidget(right_panel_container, stretch=2)

        self.ratio_combo.currentIndexChanged.connect(self.on_ratio_changed)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        self.width_input.valueChanged.connect(self.on_dimension_changed)
        self.height_input.valueChanged.connect(self.on_dimension_changed)

        self.load_settings()
        self.update_info_label()

    def load_settings(self):
        settings = QSettings("kavram", "DrawingEditor")
        saved_ratio = settings.value("ratio", "Varsayılan")
        saved_width = settings.value("canvasWidth", 1100, type=int)
        saved_height = settings.value("canvasHeight", 600, type=int)

        self.ratio_combo.blockSignals(True)
        self.preset_combo.blockSignals(True)
        self.width_input.blockSignals(True)
        self.height_input.blockSignals(True)

        ratio_index = self.ratio_combo.findText(saved_ratio)
        if ratio_index != -1:
            self.ratio_combo.setCurrentIndex(ratio_index)
        else:
            self.ratio_combo.setCurrentIndex(0)

        selected_ratio = self.ratio_combo.currentText()
        preset_list = self.presets.get(selected_ratio, [])
        if preset_list:
            self.preset_combo.setEnabled(True)
            for text, w, h in preset_list:
                self.preset_combo.addItem(text, (w, h))
        else:
            self.preset_combo.addItem("Serbest Giriş")
            self.preset_combo.setEnabled(False)

        self.width_input.setValue(saved_width)
        self.height_input.setValue(saved_height)

        matched_preset_index = -1
        for i in range(self.preset_combo.count()):
            data = self.preset_combo.itemData(i)
            if data and data == (saved_width, saved_height):
                matched_preset_index = i
                break

        if matched_preset_index != -1:
            self.preset_combo.setCurrentIndex(matched_preset_index)
        else:
            if selected_ratio != "Özel Boyut":
                self.ratio_combo.setCurrentText("Özel Boyut")
                self.preset_combo.clear()
                self.preset_combo.addItem("Serbest Giriş")
                self.preset_combo.setEnabled(False)

        self.ratio_combo.blockSignals(False)
        self.preset_combo.blockSignals(False)
        self.width_input.blockSignals(False)
        self.height_input.blockSignals(False)

        self.preview_widget.update_dimensions(saved_width, saved_height)

    def on_ratio_changed(self, index):
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        
        selected_ratio = self.ratio_combo.currentText()
        preset_list = self.presets.get(selected_ratio, [])

        if preset_list:
            self.preset_combo.setEnabled(True)
            for text, w, h in preset_list:
                self.preset_combo.addItem(text, (w, h))
            self.preset_combo.blockSignals(False)
            self.on_preset_changed(0)
        else:
            self.preset_combo.addItem("Serbest Giriş")
            self.preset_combo.setEnabled(False)
            self.preset_combo.blockSignals(False)

    def on_preset_changed(self, index):
        if index < 0:
            return
            
        data = self.preset_combo.currentData()
        if data:
            width, height = data
            self.width_input.blockSignals(True)
            self.height_input.blockSignals(True)
            
            self.width_input.setValue(width)
            self.height_input.setValue(height)
            
            self.width_input.blockSignals(False)
            self.height_input.blockSignals(False)
            
            self.preview_widget.update_dimensions(width, height)
            self.update_info_label()

    def on_dimension_changed(self, value):
        w = self.width_input.value()
        h = self.height_input.value()
        
        self.ratio_combo.blockSignals(True)
        if not self.check_if_matches_preset(w, h):
            self.ratio_combo.setCurrentText("Özel Boyut")
            self.preset_combo.setEnabled(False)
        self.ratio_combo.blockSignals(False)

        self.preview_widget.update_dimensions(w, h)
        self.update_info_label()

    def check_if_matches_preset(self, w, h):
        for ratio_key, preset_list in self.presets.items():
            for text, px_w, px_h in preset_list:
                if px_w == w and px_h == h:
                    return True
        return False

    def update_info_label(self):
        w = self.width_input.value()
        h = self.height_input.value()
        mp = (w * h) / 1000000.0
        
        if w > h:
            orientation = "Yatay"
        elif h > w:
            orientation = "Dikey"
        else:
            orientation = "Kare"
            
        self.info_label.setText(f"Özet: {mp:.2f} Megapiksel • {orientation}")

    def accept(self):
        settings = QSettings("kavram", "DrawingEditor")
        settings.setValue("ratio", self.ratio_combo.currentText())
        settings.setValue("canvasWidth", self.width_input.value())
        settings.setValue("canvasHeight", self.height_input.value())
        super().accept()

    def getSettings(self):
        return {
            "ratio": self.ratio_combo.currentText(),
            "width": self.width_input.value(),
            "height": self.height_input.value()
        }


# --- Özel Widgetlar ---

class ExportMenu(QMenu):
    def __init__(self, parent=None, default_callback=None):
        super().__init__(parent)
        self.default_callback = default_callback

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            active = self.activeAction()
            if active:
                active.trigger()
            elif self.default_callback:
                self.default_callback()
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)

class ResizableTextEdit(QTextEdit):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFrameShape(QFrame.Box)
        self.setFrameShadow(QFrame.Plain)
        self.setLineWidth(1)
        self.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: white;
                border: 1px dashed rgba(255, 255, 255, 150);
                border-radius: 4px;
                padding: 5px;
            }
        """)
        self.textChanged.connect(self.updateGeometry)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if event.modifiers() & Qt.ShiftModifier:
                self.finished.emit()
                event.accept()
                return
            else:
                super().keyPressEvent(event)
                return
        super().keyPressEvent(event)

    def updateGeometry(self):
        document = self.document()
        font_metrics = QFontMetrics(self.font())
        lines = self.toPlainText().split('\n')
        max_width = 0
        for line in lines:
            w = font_metrics.horizontalAdvance(line)
            if w > max_width:
                max_width = w

        new_width = max(100, max_width + 40)
        doc_height = document.size().height()
        new_height = max(40, doc_height + 10)

        self.resize(int(new_width), int(new_height))
        super().updateGeometry()

class NavigationModeButton(QPushButton):
    rightClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("O", parent)
        self.setCheckable(True)
        self.setFixedSize(40, 30)
        self.setStyleSheet(self.getStyle(False))
        self.clicked.connect(self.updateStyle)
        self.setToolTip("Gezinme Modu (Wheel: Zoom, Orta Tuş: Pan, Sol Tık: Çizim, Sağ Tık: Çözünürlük ve Boyutlar)")

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit()
        else:
            super().mousePressEvent(event)

    def updateStyle(self):
        self.setStyleSheet(self.getStyle(self.isChecked()))

    def getStyle(self, active):
        if active:
            return """
                QPushButton { background-color: #777; color: white; font-weight: bold; font-size: 16px; border: 2px solid #999; border-radius: 8px; }
            """
        else:
            return """
                QPushButton { background-color: transparent; color: #aaa; font-weight: bold; font-size: 16px; border: 2px solid #555; border-radius: 8px; }
                QPushButton:hover { background-color: #444; }
            """

class RadiusOverlayDialog(QDialog):
    def __init__(self, current_val, parent=None, is_sensitivity=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 80)
        self.is_sensitivity = is_sensitivity

        is_eraser = False
        if parent and hasattr(parent, 'eraser_mode') and parent.eraser_mode:
            is_eraser = True

        layout = QVBoxLayout(self)

        if self.is_sensitivity:
            title_text = f"Basınç Hassasiyeti: {'Oto' if current_val == -1 else current_val}"
        else:
            title_text = f"Silgi Boyutu: {current_val}" if is_eraser else f"Kalem Boyutu: {current_val}"

        self.label = QLabel(title_text, self)
        self.label.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        self.label.setAlignment(Qt.AlignCenter)

        self.slider = QSlider(Qt.Horizontal, self)

        if self.is_sensitivity:
             self.slider.setRange(0, 100)
             self.slider.setValue(0 if current_val == -1 else current_val)
        else:
             self.slider.setRange(1, 150)
             self.slider.setValue(current_val)

        self.slider.setStyleSheet("""
            QSlider::groove:horizontal { border: 1px solid #555; height: 8px; background: #333; margin: 2px 0; border-radius: 4px; }
            QSlider::handle:horizontal { background: #aaa; border: 1px solid #555; width: 18px; height: 18px; margin: -7px 0; border-radius: 9px; }
        """)
        self.slider.valueChanged.connect(lambda v: self.updateLabel(v, is_eraser))

        layout.addWidget(self.label)
        layout.addWidget(self.slider)

        self.setStyleSheet("background-color: #222; border: 2px solid #555; border-radius: 10px;")

    def updateLabel(self, val, is_eraser):
        if self.is_sensitivity:
            txt = "Oto" if val == 0 else str(val)
            self.label.setText(f"Basınç Hassasiyeti: {txt}")
        else:
            title_text = f"Silgi Boyutu: {val}" if is_eraser else f"Kalem Boyutu: {val}"
            self.label.setText(title_text)

    def getValue(self):
        val = self.slider.value()
        if self.is_sensitivity and val == 0:
            return -1
        return val

class RightClickButton(QPushButton):
    rightClicked = pyqtSignal(object)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit(event.pos())
        else:
            super().mousePressEvent(event)

class MirrorControlButton(QPushButton):
    leftClicked = pyqtSignal()
    rightClicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit()
        else:
            self.leftClicked.emit()
        super().mousePressEvent(event)

class ScrollableButton(QPushButton):
    deltaChanged = pyqtSignal(int)
    def wheelEvent(self, event):
        delta = 1 if event.angleDelta().y() > 0 else -1
        self.deltaChanged.emit(delta)
        event.accept()

class PageNavigatorButton(QPushButton):
    pageChanged = pyqtSignal(int)

    def wheelEvent(self, event):
        delta = 1 if event.angleDelta().y() > 0 else -1
        self.pageChanged.emit(delta)
        event.accept()

class MixAngleButton(QPushButton):
    deltaChanged = pyqtSignal(int)
    def wheelEvent(self, event):
        delta = 1 if event.angleDelta().y() > 0 else -1
        self.deltaChanged.emit(delta)
        event.accept()

class WheelButton(QPushButton):
    def __init__(self, text, parent=None, is_sensitivity=False):
        super().__init__(text, parent)
        self.is_sensitivity = is_sensitivity

    def wheelEvent(self, event):
        main_window = self.window()
        delta = 1 if event.angleDelta().y() > 0 else -1

        if self.is_sensitivity:
             if hasattr(main_window, 'changeSensitivityValue'):
                 current = main_window.sensitivity_value
                 if current == -1:
                     current = 50
                 new_val = max(1, min(100, current + delta))
                 main_window.changeSensitivityValue(new_val)
        else:
            if hasattr(main_window, 'solid_fill_mode') and main_window.solid_fill_mode:
                return

            if hasattr(main_window, 'changeRadiusValue'):
                new_radius = max(1, min(357, main_window.pen_radius + delta))
                main_window.changeRadiusValue(new_radius)
        event.accept()

class LazyMouseButton(QPushButton):
    radiusChanged = pyqtSignal(int)
    factorChanged = pyqtSignal(int)
    rightClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("lm", parent)
        self._adjusting_radius = True
        self.setMouseTracking(True)
        self.setCheckable(True)

        self.setStyleSheet("""
            QPushButton { background-color: transparent; color: #888; border: none; padding: 2px 6px; font-size: 12px; font-weight: normal; }
            QPushButton:hover { color: #aaa; background-color: transparent; }
            QPushButton:checked { color: #4CAF50; }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.rightClicked.emit()
        else:
            super().mousePressEvent(event)

    def wheelEvent(self, event):
        main_window = self.window()
        delta = 1 if event.angleDelta().y() > 0 else -1
        
        if hasattr(main_window, 'lazy_radius') and hasattr(main_window, 'lazy_factor'):
            modifiers = QApplication.keyboardModifiers()
            if modifiers == Qt.ControlModifier:
                new_factor = max(1, min(100, main_window.lazy_factor + delta))
                main_window.lazy_factor = new_factor
                self.factorChanged.emit(new_factor)
            else:
                new_radius = max(5, min(200, main_window.lazy_radius + delta * 5))
                main_window.lazy_radius = new_radius
                self.radiusChanged.emit(new_radius)
            
            self.updateButtonText(main_window)
            self.updateToolTip(main_window)
            if hasattr(main_window, 'saveLazyMouseSettings'):
                main_window.saveLazyMouseSettings()
        event.accept()
    
    def updateButtonText(self, main_window):
        self.setText("lm")
    
    def updateToolTip(self, main_window):
        self.setToolTip(
            f"Lazy Mouse: Yavaşlatılmış fare (Blender tarzı)\n"
            f"R={main_window.lazy_radius} (Yarıçap), H={main_window.lazy_factor} (Hassasiyet)\n"
            f"Fare tekerleği: Radius, Ctrl+Tekerlek: Hassasiyet\n"
            f"Varsayılan: R=30, H=15"
        )


class ColorHistoryStrip(QWidget):
    colorSelected = pyqtSignal(object, object)
    def __init__(self, colors, parent=None):
        super().__init__(parent)
        self.colors = colors
        self.square_size = 24
        self.spacing = 6
        self.margin = 5
        self.cols_per_row = 4
        num_rows = (len(colors) + self.cols_per_row - 1) // self.cols_per_row
        total_width = self.margin * 2 + self.cols_per_row * (self.square_size + self.spacing)
        total_height = self.margin * 2 + num_rows * (self.square_size + self.spacing)
        self.setFixedSize(max(150, total_width), total_height)
        self.setCursor(Qt.PointingHandCursor)
        self.hovered_index = -1
        self.is_pressed = False
        self.setMouseTracking(True)
    def enterEvent(self, event):
        super().enterEvent(event)
    def leaveEvent(self, event):
        self.hovered_index = -1
        self.is_pressed = False
        self.update()
        super().leaveEvent(event)
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.underMouse():
            painter.fillRect(self.rect(), QColor(60, 60, 60))
        for i, color in enumerate(self.colors):
            row = i // self.cols_per_row
            col = i % self.cols_per_row
            x = self.margin + col * (self.square_size + self.spacing)
            y = self.margin + row * (self.square_size + self.spacing)
            rect = QRect(x, y, self.square_size, self.square_size)
            painter.setBrush(QBrush(color))
            if i == self.hovered_index:
                painter.setPen(QPen(Qt.white, 2))
                if self.is_pressed:
                    painter.setBrush(QBrush(color.darker(120)))
            else:
                painter.setPen(QPen(Qt.gray, 1))
            painter.drawRoundedRect(rect, 4, 4)
    def mouseMoveEvent(self, event):
        pos = event.pos()
        old_hover = self.hovered_index
        self.hovered_index = -1
        for i in range(len(self.colors)):
            row = i // self.cols_per_row
            col = i % self.cols_per_row
            x = self.margin + col * (self.square_size + self.spacing)
            y = self.margin + row * (self.square_size + self.spacing)
            rect = QRect(x, y, self.square_size, self.square_size)
            if rect.contains(pos):
                self.hovered_index = i
                break
        if old_hover != self.hovered_index:
            self.update()
        super().mouseMoveEvent(event)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.hovered_index >= 0:
                self.is_pressed = True
                self.update()
            pos = event.pos()
            clicked_color_index = -1
            for i in range(len(self.colors)):
                row = i // self.cols_per_row
                col = i % self.cols_per_row
                x = self.margin + col * (self.square_size + self.spacing)
                y = self.margin + row * (self.square_size + self.spacing)
                rect = QRect(x, y, self.square_size, self.square_size)
                if rect.contains(pos):
                    clicked_color_index = i
                    break
            if clicked_color_index != -1:
                self.colorSelected.emit(self.colors[clicked_color_index], None)
            else:
                if len(self.colors) == 1:
                    self.colorSelected.emit(self.colors[0], None)
                else:
                    self.colorSelected.emit(None, self.colors)
        elif event.button() == Qt.RightButton:
            self.showContextMenu(event.pos())
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_pressed = False
            self.update()
        super().mouseReleaseEvent(event)
    def showContextMenu(self, pos):
        clicked_color_index = -1
        for i in range(len(self.colors)):
            row = i // self.cols_per_row
            col = i % self.cols_per_row
            x = self.margin + col * (self.square_size + self.spacing)
            y = self.margin + row * (self.square_size + self.spacing)
            rect = QRect(x, y, self.square_size, self.square_size)
            if rect.contains(pos):
                clicked_color_index = i
                break
        if clicked_color_index != -1:
            color = self.colors[clicked_color_index]
            menu = QMenu(self)
            menu.setStyleSheet("QMenu { background-color: #333; color: white; border: 1px solid #555; } QMenu::item:selected { background-color: #555; }")
            copy_hex_action = menu.addAction(f"Copy Hex: {color.name().upper()}")
            action = menu.exec_(self.mapToGlobal(pos))
            if action == copy_hex_action:
                clipboard = QApplication.clipboard()
                clipboard.setText(color.name().upper())

class CircleBrightnessDialog(QDialog):
    def __init__(self, initialColor=QColor("white"), parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.hueSatDiameter = 150
        self.radius = self.hueSatDiameter // 2
        hF, sF, vF, _ = initialColor.getHsvF()
        self.h = int(hF * 360)
        self.s = sF
        self.v = vF
        self.setFixedSize(280, 280)

        self.colorWheel = QImage(self.hueSatDiameter, self.hueSatDiameter, QImage.Format_ARGB32)
        self._generateColorWheel()

        self.slider = QSlider(Qt.Vertical, self)
        self.slider.setRange(0, 100)
        self.slider.setValue(int(self.v * 100))
        self.slider.setGeometry(self.hueSatDiameter + 20, 10, 20, self.hueSatDiameter)
        self.slider.valueChanged.connect(self.onValueChanged)

        self._updateSliderStyle()

        self.preview_label = QLabel(self)
        self.preview_label.setGeometry(self.hueSatDiameter + 50, 35, 40, 40)
        self.preview_label.setStyleSheet("QLabel { border: 2px solid #FFFFFF; border-radius: 4px; }")
        self._updatePreviewColor()

        self.brightness_label = QLabel(self)
        self.brightness_label.setStyleSheet("color: white; background: transparent;")
        self.brightness_label.setGeometry(self.hueSatDiameter + 50, 10, 40, 20)
        self.brightness_label.setText(f"{int(self.v*100)}%")

        self.hex_input = QLineEdit(self)
        self.hex_input.setGeometry(10, self.hueSatDiameter + 25, 105, 25) 
        self.hex_input.setStyleSheet("""
            QLineEdit { background-color: #000000; color: #FFFFFF; border: 1px solid #444444; border-radius: 4px; padding: 2px 5px; font-family: Consolas, Monaco, monospace; font-size: 12px; }
            QLineEdit:focus { border: 1px solid #00FF00; }
        """)
        self.hex_input.setMaxLength(6)
        self.hex_input.setPlaceholderText("Hex Kodu")
        self.hex_input.textChanged.connect(self.onHexTextChanged)
        self.hex_input.returnPressed.connect(self.onHexEnterPressed)

        self.hex_ok_btn = QPushButton("OK", self)
        self.hex_ok_btn.setGeometry(120, self.hueSatDiameter + 25, 40, 25)
        self.hex_ok_btn.setStyleSheet("""
            QPushButton { background-color: #222; color: #FFFFFF; border: 1px solid #444; border-radius: 4px; font-family: Consolas, Monaco, monospace; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background-color: #4CAF50; border: 1px solid #4CAF50; }
            QPushButton:pressed { background-color: #388E3C; }
        """)
        self.hex_ok_btn.clicked.connect(self.onHexEnterPressed)

        self.hex_label = QLabel(self)
        self.hex_label.setGeometry(165, self.hueSatDiameter + 25, 105, 25)
        self.hex_label.setStyleSheet("""
            QLabel { background-color: #000000; color: #FFFFFF; border: 1px solid #444444; border-radius: 4px; padding: 2px 5px; font-family: Consolas, Monaco, monospace; font-size: 12px; }
        """)
        self.hex_label.setAlignment(Qt.AlignCenter)
        self.hex_label.setText("#" + initialColor.name().upper()[1:])

        self._updateHexFromColor()

    def _updateHexFromColor(self):
        color = QColor.fromHsvF(self.h/360.0, self.s, self.v)
        hex_code = color.name().upper()[1:]  
        self.hex_label.setText("#" + hex_code)
        self.hex_input.setText(hex_code)
        self._updateSliderStyle()
        self._updatePreviewColor()

    def _updateSliderStyle(self):
        hue_color = QColor.fromHsvF(self.h/360.0, 1.0, 1.0)
        hue_hex = hue_color.name()
        self.slider.setStyleSheet(f"""
            QSlider::groove:vertical {{ border: none; width: 4px; background: qlineargradient(x1:0, y1:1, x2:0, y2:0, stop:0 #000000, stop:0.5 {hue_hex}, stop:1 #FFFFFF); margin: 0px; }}
            QSlider::handle:vertical {{ background: {hue_hex}; border: 2px solid #FFFFFF; width: 12px; height: 12px; margin: -6px 0; border-radius: 6px; }}
            QSlider::handle:vertical:hover {{ background: #FFFFFF; border: 2px solid {hue_hex}; }}
        """)

    def _updatePreviewColor(self):
        current_color = QColor.fromHsvF(self.h/360.0, self.s, self.v)
        self.preview_label.setStyleSheet(f"QLabel {{ background-color: {current_color.name()}; border: 2px solid #FFFFFF; border-radius: 4px; }}")

    def onHexTextChanged(self, text):
        self.hex_input.blockSignals(True)
        clean_text = "".join(c for c in text.upper() if c in "0123456789ABCDEF")
        if clean_text != text:
            cursor = self.hex_input.cursorPosition()
            self.hex_input.setText(clean_text)
            self.hex_input.setCursorPosition(cursor)
        self.hex_input.blockSignals(False)

    def onHexEnterPressed(self):
        hex_text = self.hex_input.text().strip()
        if len(hex_text) == 6:
            try:
                color = QColor("#" + hex_text)
                if color.isValid():
                    hF, sF, vF, _ = color.getHsvF()
                    self.h = int(hF * 360)
                    self.s = sF
                    self.v = vF
                    self.slider.setValue(int(self.v * 100))
                    self.hex_label.setText("#" + hex_text.upper())
                    self.update()
            except Exception:
                pass

    def _handleCtrlV(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        clean_hex = text.replace("#", "").upper()
        clean_hex = "".join(c for c in clean_hex if c in "0123456789ABCDEF")
        if len(clean_hex) == 6:
            try:
                color = QColor("#" + clean_hex)
                if color.isValid():
                    hF, sF, vF, _ = color.getHsvF()
                    self.h = int(hF * 360)
                    self.s = sF
                    self.v = vF
                    self.slider.setValue(int(self.v * 100))
                    self.hex_input.setText(clean_hex)
                    self.hex_label.setText("#" + clean_hex)
                    self.update()
            except Exception:
                pass

    def keyPressEvent(self, event):
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_V:
            self._handleCtrlV()
            event.accept()
            return
        super().keyPressEvent(event)
        
    def _generateColorWheel(self):
        center = self.radius
        for y in range(self.hueSatDiameter):
            for x in range(self.hueSatDiameter):
                dx = x - center
                dy = y - center
                r = math.sqrt(dx*dx + dy*dy)
                if r <= self.radius:
                    hue = (math.degrees(math.atan2(dy, dx)) + 360) % 360
                    sat = r / self.radius
                    c = QColor.fromHsvF(hue/360.0, sat, 1.0)
                    self.colorWheel.setPixelColor(x, y, c)
                else:
                    self.colorWheel.setPixelColor(x, y, Qt.transparent)
                
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(30, 30, 30, 220))
        circleX, circleY = 10, 10
        painter.drawImage(circleX, circleY, self.colorWheel)
        hueRad = math.radians(self.h)
        satR = self.s * self.radius
        selX = circleX + self.radius + satR * math.cos(hueRad)
        selY = circleY + self.radius + satR * math.sin(hueRad)
        painter.setPen(QPen(Qt.black, 2))
        painter.setBrush(Qt.white)
        painter.drawEllipse(QPoint(int(selX), int(selY)), 5, 5)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not self._pickHueSat(event.pos()):
                self.accept()
            else:
                self.update()
        else:
            self.accept()
        
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            if self._pickHueSat(event.pos()):
                self.update()
            
    def _pickHueSat(self, pos):
        x, y = pos.x() - 10, pos.y() - 10
        if 0 <= x < self.hueSatDiameter and 0 <= y < self.hueSatDiameter:
            dx = x - self.radius
            dy = y - self.radius
            r = math.sqrt(dx*dx + dy*dy)
            if r <= self.radius:
                angle = (math.degrees(math.atan2(dy, dx)) + 360) % 360
                self.h = angle
                self.s = r / self.radius
                color = QColor.fromHsvF(self.h/360.0, self.s, self.v)
                hex_code = color.name().upper()[1:]
                self.hex_label.setText("#" + hex_code)
                self.hex_input.setText(hex_code)
                self._updateSliderStyle()
                self._updatePreviewColor()
                return True
        return False
        
    def onValueChanged(self, val):
        self.v = val / 100.0
        self.brightness_label.setText(f"{val}%")
        color = QColor.fromHsvF(self.h/360.0, self.s, self.v)
        hex_code = color.name().upper()[1:]
        self.hex_label.setText("#" + hex_code)
        self.hex_input.setText(hex_code)
        self._updatePreviewColor()
        self.update()
        
    def getSelectedColor(self):
        return QColor.fromHsvF(self.h/360.0, self.s, self.v)
    
    def focusOutEvent(self, event):
        self.accept()
        super().focusOutEvent(event)


