# Kavram 1.0.0
# Copyright (C) 2025-09-01 Kavram or Contributors

import subprocess
import json
import os
import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QGroupBox, QPushButton, QFrame
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QIcon

os.environ["QT_LOGGING_RULES"] = "qt.*=false;*.debug=false;qt.x11.*=false;qt.qpa.*=false;qt.accessibility.*=false"

# Gölge yazı stili — tek yerden yönetilir
HINT_STYLE = (
    "color: #787878;"
    "font-size: 11px;"
    "font-style: italic;"
    "font-weight: 900;"          # maksimum kalınlık
    "padding-bottom: 4px;"
)


class Settings(QWidget):
    # Dizinleri dinamik ve güvenli bir şekilde oluşturuyoruz
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    VERI_DIR = os.path.join(BASE_DIR, "veri")
    SETTINGS_FILE = os.path.join(VERI_DIR, "blue_light_filter_settings.json")
    SHADER_FILE   = os.path.join(VERI_DIR, "grayscale.glsl")

    DEFAULTS = {
        "red":         100,
        "green":       100,
        "blue_filter":   0,   # 0–100
        "brightness":  100,
        "darkness":      0,
        "gray":        False,
        "reading":     False,
    }

    def __init__(self):
        super().__init__()
        self.grayscale_method        = None
        self._block_save             = True
        self.picom_was_running       = self._check_picom()
        self.xfce_compositing_was_on = self._check_xfce_comp()
        self._original_cursor_theme  = self._get_cursor_theme()

        self._build_ui()
        self._load_settings()
        self._block_save = False
        self._apply()

        self.installEventFilter(self)

    # ═══════════════════════════════════════════════════════════════════════
    #  SİSTEM SORGULARI
    # ═══════════════════════════════════════════════════════════════════════
    def _check_picom(self):
        try:
            subprocess.check_output(["pgrep", "-x", "picom"]); return True
        except: return False

    def _check_xfce_comp(self):
        try:
            o = subprocess.check_output(
                ["xfconf-query", "-c", "xfwm4", "-p", "/general/use_compositing"]
            ).decode().strip()
            return o.lower() == "true"
        except: return False

    def _set_xfce_comp(self, enable):
        try:
            subprocess.run(["xfconf-query", "-c", "xfwm4",
                             "-p", "/general/use_compositing", "--set",
                             "true" if enable else "false"], check=True)
            subprocess.Popen(["xfwm4", "--replace"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.8)
        except: pass

    def _get_cursor_theme(self):
        try:
            return subprocess.check_output(
                ["xfconf-query", "-c", "xsettings", "-p", "/Gtk/CursorThemeName"]
            ).decode().strip()
        except: return ""

    def _set_cursor_theme(self, theme):
        if not theme: return
        try:
            subprocess.run(["xfconf-query", "-c", "xsettings",
                             "-p", "/Gtk/CursorThemeName", "--set", theme], check=False)
        except: pass

    def _connected_displays(self):
        try:
            out = subprocess.check_output("xrandr --current", shell=True).decode()
            return [l.split()[0] for l in out.splitlines() if " connected" in l]
        except: return []

    # ═══════════════════════════════════════════════════════════════════════
    #  ARAYÜZ
    # ═══════════════════════════════════════════════════════════════════════
    def _build_ui(self):
        self.setWindowTitle("Settings")
        self.setMinimumSize(680, 640)
        self.setWindowIcon(QIcon("ikon/Kavram.png"))

        self.setStyleSheet("""
            QWidget {
                background-color: #2E2E2E;
                color: #E0E0E0;
                font-family: 'Segoe UI', Arial;
                font-size: 14px;
            }
            QLabel { color: #E0E0E0; }
            QGroupBox {
                border: 2px solid #333333;
                border-radius: 12px;
                margin-top: 1.5ex;
                font-weight: bold;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: #2E2E2E;
                color: #a0a0a0;
            }
            QSlider::groove:horizontal {
                border: 1px solid #3a3a3a;
                height: 10px;
                background: #555555;
                margin: 2px 0;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #a0a0a0;
                border: 1px solid #707070;
                width: 20px;
                height: 20px;
                margin: -5px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal:hover {
                background: #c8c8c8;
                border: 1px solid #999999;
            }
        """)

        BTN = """
            QPushButton {
                background-color: transparent;
                color: #E0E0E0;
                border: 2px solid #555555;
                border-radius: 8px;
                padding: 5px 10px;
                font-weight: bold;
                font-size: 15px;
            }
            QPushButton:hover  { background-color: #3C3C3C; border: 1px solid #777777; }
            QPushButton:pressed{ background-color: #1A1A1A; padding: 6px 10px 4px 10px; }
            QPushButton:checked{ background-color: #4A4A4A; border: 2px solid #777777; color: #ffffff; }
            QPushButton:disabled{ background-color: #202020; color: #555; border: 1px solid #333; }
        """

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        # ── ÜST BAR ────────────────────────────────────────────────────────
        top_bar = QFrame()
        top_bar.setFixedHeight(40)
        top_bar.setStyleSheet("background-color: #1F1F1F; border-bottom: 2px solid #555;")
        bar = QHBoxLayout(top_bar)
        bar.setContentsMargins(15, 5, 15, 5)
        bar.setSpacing(15)

        self.reset_button = QPushButton("Reset")
        self.reset_button.setFixedSize(90, 30)
        self.reset_button.setStyleSheet(BTN)
        self.reset_button.setCursor(Qt.PointingHandCursor)
        self.reset_button.clicked.connect(self._reset)
        bar.addWidget(self.reset_button)

        # YENİ OTO-BAŞLAT BUTONU ( / )
        self.autostart_button = QPushButton("/")
        self.autostart_button.setFixedSize(30, 30)
        self.autostart_button.setStyleSheet(BTN)
        self.autostart_button.setCursor(Qt.PointingHandCursor)
        self.autostart_button.setCheckable(True)
        self.autostart_button.setToolTip("Bilgisayar açılışında ayarları otomatik uygula")
        
        # Önceden aktiv edilmiş mi kontrol et (Linux Mint XFCE autostart)
        autostart_path = os.path.expanduser("~/.config/autostart/kavram_blf.desktop")
        self.autostart_button.setChecked(os.path.exists(autostart_path))
        self.autostart_button.toggled.connect(self._on_autostart_toggled)
        bar.addWidget(self.autostart_button)

        bar.addStretch()

        self.reading_button = QPushButton("Reading")
        self.reading_button.setFixedSize(90, 30)
        self.reading_button.setStyleSheet(BTN)
        self.reading_button.setCursor(Qt.PointingHandCursor)
        self.reading_button.setCheckable(True)
        self.reading_button.toggled.connect(self._on_reading)

        self.gray_button = QPushButton("Gray")
        self.gray_button.setFixedSize(90, 30)
        self.gray_button.setStyleSheet(BTN)
        self.gray_button.setCursor(Qt.PointingHandCursor)
        self.gray_button.setCheckable(True)
        self.gray_button.toggled.connect(self._apply)

        rr = QHBoxLayout()
        rr.setSpacing(12)
        rr.addWidget(self.reading_button)
        rr.addWidget(self.gray_button)
        bar.addLayout(rr)

        main_layout.addWidget(top_bar)

        # ── İÇERİK ─────────────────────────────────────────────────────────
        content = QVBoxLayout()
        content.setContentsMargins(12, 10, 12, 10)
        content.setSpacing(10)

        # Durum
        sg = QGroupBox("Durum")
        sl = QVBoxLayout()
        self.status_label = QLabel("Durum: Aktif")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #a0a0a0; font-size: 15px;")
        sl.addWidget(self.status_label)
        sg.setLayout(sl)
        content.addWidget(sg)

        # Mavi Işık Filtresi
        bg = QGroupBox("Mavi Işık Filtresi")
        bv = QVBoxLayout()
        self.blue_filter_slider = self._make_row(
            bv, "Blue Light Filter",
            "0–33 arası: mavi ışık azaltır  |  33–100 arası: mavi zemine ek ekran kararır — göz yorgunluğunu en aza indirir",
            0, 100, 0
        )
        bg.setLayout(bv)
        content.addWidget(bg)

        # Renk Dengesi
        cg = QGroupBox("Renk Dengesi")
        cv = QVBoxLayout()
        self.red_slider = self._make_row(
            cv, "Red Channel",
            "Kırmızı kanalı artırmak ekranı ısıtır; mavi filtre ile birlikte doğal sıcaklık sağlar",
            50, 160, 100
        )
        self.green_slider = self._make_row(
            cv, "Green Channel",
            "Yeşil ton dengesi — genellikle varsayılanda bırakın",
            50, 160, 100
        )
        cg.setLayout(cv)
        content.addWidget(cg)

        # Parlaklık & Karanlık
        pg = QGroupBox("Parlaklık & Karanlık Filtre")
        pv = QVBoxLayout()
        self.brightness_slider = self._make_row(
            pv, "Brightness",
            "Genel ekran parlaklığı — karanlık ortamda düşürün, gündüz artırın",
            20, 150, 100
        )
        self.darkness_slider = self._make_row(
            pv, "Darkness Filter",
            "Gamma tabanlı ek karartma — parlaklık ayarından bağımsız, çok karanlık ortamlar için",
            0, 70, 0
        )
        pg.setLayout(pv)
        content.addWidget(pg)

        # Alt kısayol notu
        shortcut_lbl = QLabel("Alt + V  →  tüm ayarları sıfırlar  (ekran bozulursa kurtarma kısayolu)")
        shortcut_lbl.setStyleSheet(HINT_STYLE + "padding: 2px 4px;")
        shortcut_lbl.setAlignment(Qt.AlignCenter)
        content.addWidget(shortcut_lbl)

        content.addStretch()
        main_layout.addLayout(content)

    # ── Slider satırı ──────────────────────────────────────────────────────
    def _make_row(self, layout, name, hint_text, min_v=0, max_v=100, def_v=0):
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("color: #D0D0D0; font-size: 14px; font-weight: bold;")
        layout.addWidget(name_lbl)

        sld = QSlider(Qt.Horizontal)
        sld.setRange(min_v, max_v)
        sld.setValue(def_v)
        sld.valueChanged.connect(self._apply)
        layout.addWidget(sld)

        hint_lbl = QLabel(hint_text)
        hint_lbl.setStyleSheet(HINT_STYLE)
        hint_lbl.setWordWrap(True)
        layout.addWidget(hint_lbl)

        return sld

    # ═══════════════════════════════════════════════════════════════════════
    #  OTO-BAŞLAT (AUTOSTART) SİSTEMİ
    # ═══════════════════════════════════════════════════════════════════════
    def _on_autostart_toggled(self, checked):
        autostart_dir = os.path.expanduser("~/.config/autostart")
        desktop_file = os.path.join(autostart_dir, "kavram_blf.desktop")

        if checked:
            os.makedirs(autostart_dir, exist_ok=True)
            script_path = os.path.abspath(__file__)
            # Sistemin varsayılan Python'unu kullanarak arkaplanda `--startup` parametresiyle başlatır.
            content = f"""[Desktop Entry]
Type=Application
Exec={sys.executable} "{script_path}" --startup
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Kavram Renk Ayarlari
Comment=Sistem baslangicinda belirlenen renk ayarlarini otomatik uygular
"""
            try:
                with open(desktop_file, "w") as f:
                    f.write(content)
                os.chmod(desktop_file, 0o755)
            except Exception as e:
                print("Autostart dosyası oluşturulamadı:", e)
        else:
            if os.path.exists(desktop_file):
                try:
                    os.remove(desktop_file)
                except:
                    pass

    # ═══════════════════════════════════════════════════════════════════════
    #  EVENT FILTER  —  Alt+V
    # ═══════════════════════════════════════════════════════════════════════
    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.modifiers() == Qt.AltModifier and event.key() == Qt.Key_V:
                self._reset()
                return True
        return super().eventFilter(obj, event)

    # ═══════════════════════════════════════════════════════════════════════
    #  GRİ MOD
    # ═══════════════════════════════════════════════════════════════════════
    def _apply_ctm(self, displays, enable):
        gray_ctm = ("913110047,0,3071760610,0,310096639,0,"
                    "913110047,0,3071760610,0,310096639,0,"
                    "913110047,0,3071760610,0,310096639,0")
        id_ctm   = "0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1"
        for d in displays:
            try:
                subprocess.run(["xrandr", "--output", d, "--set", "CTM",
                                 gray_ctm if enable else id_ctm], check=True)
            except: pass

    def _apply_shader(self, enable):
        # 'veri' klasörünün varlığından emin oluyoruz ki hata vermesin
        os.makedirs(self.VERI_DIR, exist_ok=True)
        
        if enable:
            if self.xfce_compositing_was_on: self._set_xfce_comp(False)
            subprocess.call(["pkill", "picom"])
            time.sleep(0.4)
            shader = """\
#version 330
in vec2 texcoord;
uniform sampler2D tex;
uniform float opacity;
vec4 default_post_processing(vec4 c);
vec4 window_shader() {
    vec2 sz = textureSize(tex, 0);
    vec4 c  = texture2D(tex, texcoord / sz, 0);
    float g = 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b;
    c = vec4(vec3(g) * opacity, c.a * opacity);
    return default_post_processing(c);
}"""
            with open(self.SHADER_FILE, "w") as f: f.write(shader)
            subprocess.Popen(
                ["picom", "--backend", "glx",
                 "--window-shader-fg", self.SHADER_FILE,
                 "--no-use-damage"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        else:
            subprocess.call(["pkill", "picom"])
            if self.picom_was_running:
                subprocess.Popen(["picom"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if self.xfce_compositing_was_on: self._set_xfce_comp(True)
            return False

    def _enable_gray(self):
        if self.grayscale_method: return
        displays = self._connected_displays()
        try:
            verbose = subprocess.check_output(
                f"xrandr --output {displays[0]} --verbose", shell=True).decode()
            if "CTM" in verbose:
                self._apply_ctm(displays, True)
                self.grayscale_method = "ctm"
                self._set_cursor_theme("DMZ-White")
            elif self._apply_shader(True):
                self.grayscale_method = "shader"
            else:
                self.grayscale_method = "gamma"
        except:
            self.grayscale_method = "gamma"

    def _disable_gray(self):
        if self.grayscale_method == "ctm":
            self._apply_ctm(self._connected_displays(), False)
            if self._original_cursor_theme:
                self._set_cursor_theme(self._original_cursor_theme)
        elif self.grayscale_method == "shader":
            self._apply_shader(False)
        self.grayscale_method = None

    # ═══════════════════════════════════════════════════════════════════════
    #  BLUE FILTER HESABI
    # ═══════════════════════════════════════════════════════════════════════
    def _blue_params(self):
        v = self.blue_filter_slider.value() / 100.0  # 0.0–1.0

        THIRD = 1.0 / 3.0

        if v <= THIRD:
            t         = v / THIRD           
            blue_g    = 1.0 - t * 0.9       
            extra_br  = 1.0

        elif v <= 2 * THIRD:
            t         = (v - THIRD) / THIRD 
            blue_g    = 0.1
            extra_br  = 1.0 - t * 0.40      

        else:
            t         = (v - 2 * THIRD) / THIRD  
            blue_g    = 0.1
            extra_br  = 0.60 - t * 0.35     

        return blue_g, extra_br

    # ═══════════════════════════════════════════════════════════════════════
    #  ANA UYGULAMA MOTORU
    # ═══════════════════════════════════════════════════════════════════════
    def _apply(self, *_):
        is_gray   = self.gray_button.isChecked()
        dark_coef = (100 - self.darkness_slider.value()) / 100.0
        br_base   = self.brightness_slider.value() / 100.0

        blue_g, extra_br = self._blue_params()

        br = br_base * extra_br

        r = (self.red_slider.value()   / 100.0) * dark_coef
        g = (self.green_slider.value() / 100.0) * dark_coef
        b = blue_g                              * dark_coef

        if is_gray:
            self._enable_gray()
            if self.grayscale_method == "gamma":
                avg = 0.2126 * r + 0.7152 * g + 0.0722 * b
                r = g = b = avg
        else:
            if self.grayscale_method:
                self._disable_gray()

        clamp     = lambda v: max(0.1, round(v, 4))
        gamma_str = f"{clamp(r)}:{clamp(g)}:{clamp(b)}"
        br_str    = f"{max(0.1, round(br, 4))}"

        for d in self._connected_displays():
            try:
                subprocess.run(["xrandr", "--output", d,
                                 "--gamma",      gamma_str,
                                 "--brightness", br_str])
            except: pass

        self._update_status()
        if not self._block_save:
            self._save()

    # ═══════════════════════════════════════════════════════════════════════
    #  OKUMA MODU 
    # ═══════════════════════════════════════════════════════════════════════
    def _on_reading(self, checked):
        self._block_save = True
        if checked:
            self.red_slider.setValue(118)
            self.green_slider.setValue(90)
            self.blue_filter_slider.setValue(55)   
            self.brightness_slider.setValue(80)
            self.darkness_slider.setValue(5)
        else:
            self.red_slider.setValue(100)
            self.green_slider.setValue(100)
            self.blue_filter_slider.setValue(0)
            self.brightness_slider.setValue(100)
            self.darkness_slider.setValue(0)
        self._block_save = False
        self._apply()

    # ═══════════════════════════════════════════════════════════════════════
    #  KAYDET / YÜKLE / SIFIRLA
    # ═══════════════════════════════════════════════════════════════════════
    def _save(self):
        # 'veri' klasörünü oluşturmayı garantiye alıyoruz
        os.makedirs(self.VERI_DIR, exist_ok=True)
        
        data = {
            "red":         self.red_slider.value(),
            "green":       self.green_slider.value(),
            "blue_filter": self.blue_filter_slider.value(),
            "brightness":  self.brightness_slider.value(),
            "darkness":    self.darkness_slider.value(),
            "gray":        self.gray_button.isChecked(),
            "reading":     self.reading_button.isChecked(),
        }
        try:
            with open(self.SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except: pass

    def _load_settings(self):
        self._block_save = True
        d = self.DEFAULTS.copy()
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE) as f:
                    saved = json.load(f)
                d.update(saved)
            except: pass

        self.blue_filter_slider.setValue(d["blue_filter"])
        self.red_slider.setValue(d["red"])
        self.green_slider.setValue(d["green"])
        self.brightness_slider.setValue(d["brightness"])
        self.darkness_slider.setValue(d["darkness"])
        self.gray_button.setChecked(d["gray"])
        self.reading_button.setChecked(d["reading"])
        self._block_save = False

    def _reset(self):
        self._block_save = True
        D = self.DEFAULTS
        self.red_slider.setValue(D["red"])
        self.green_slider.setValue(D["green"])
        self.blue_filter_slider.setValue(D["blue_filter"])
        self.brightness_slider.setValue(D["brightness"])
        self.darkness_slider.setValue(D["darkness"])
        self.gray_button.setChecked(False)
        self.reading_button.setChecked(False)
        self._block_save = False
        self._apply()

    def _update_status(self):
        m    = f" [{self.grayscale_method}]" if self.grayscale_method else ""
        bf   = self.blue_filter_slider.value()
        gray = f"GRİ: AÇIK{m}" if self.gray_button.isChecked() else "GRİ: kapalı"

        if bf == 0:
            flt = "Mavi Filtre: kapalı"
        elif bf <= 33:
            flt = f"Mavi Filtre: %{bf}  [hafif]"
        elif bf <= 67:
            flt = f"Mavi Filtre: %{bf}  [güçlü]"
        else:
            flt = f"Mavi Filtre: %{bf}  [ultra]"

        rd = "  |  Okuma: AÇIK" if self.reading_button.isChecked() else ""
        self.status_label.setText(f"Durum: Aktif  |  {gray}  |  {flt}{rd}")

    # ═══════════════════════════════════════════════════════════════════════
    #  PENCERE KAPANIŞI
    # ═══════════════════════════════════════════════════════════════════════
    def closeEvent(self, event):
        self._save()
        event.accept()


if __name__ == "__main__":
    # Eğer XFCE masaüstü açılışında `--startup` komutuyla gelirse
    # XFCE'nin kendi ekran bileşenlerinin tam oturması için kısa bir süre bekleriz.
    if "--startup" in sys.argv:
        time.sleep(4)
        
    app = QApplication(sys.argv)
    w = Settings()
    
    # Oto-başlatma devredeyse sadece ayarları uygulayıp (bu iş __init__'te yapıldı zaten)
    # pencereyi hiç göstermeden güvenli şekilde programı kapatır.
    if "--startup" in sys.argv:
        sys.exit(0)
        
    w.show()
    sys.exit(app.exec_())
