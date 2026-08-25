import subprocess
import json
import os
import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QGroupBox, QPushButton, QFrame, QToolButton
)
from PyQt5.QtCore import Qt, QEvent, QTimer
from PyQt5.QtGui import QIcon

# Suppress Qt background warnings
os.environ["QT_LOGGING_RULES"] = "qt.*=false;*.debug=false;qt.x11.*=false;qt.qpa.*=false;qt.accessibility.*=false"

HINT_STYLE = (
    "color: #8A8A8A;"
    "font-size: 11px;"
    "font-style: italic;"
    "font-weight: 600;"
    "padding-bottom: 4px;"
)


class Settings(QWidget):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    VERI_DIR = os.path.join(BASE_DIR, "veri")
    SETTINGS_FILE = os.path.join(VERI_DIR, "blue_light_filter_settings.json")
    SHADER_FILE = os.path.join(VERI_DIR, "grayscale.glsl")

    DEFAULTS = {
        "red": 100,
        "green": 100,
        "blue_filter": 0,    # 0–100
        "brightness": 100,
        "darkness": 0,
        "gray": False,
        "reading": False,
    }

    def __init__(self):
        super().__init__()
        self.session_type = os.environ.get("XDG_SESSION_TYPE", "x11").lower()
        self.grayscale_method = None
        self._block_save = True
        self._displays_cache = None
        
        # Debounce timer for smooth slider responsiveness (35ms delay)
        self._apply_timer = QTimer(self)
        self._apply_timer.setSingleShot(True)
        self._apply_timer.timeout.connect(self._apply_now)

        # Detect active backends (gammastep, wlsunset, xrandr)
        self.has_gammastep = self._has_cmd("gammastep")
        self.has_wlsunset = self._has_cmd("wlsunset")
        self.picom_was_running = self._check_picom()
        self.xfce_compositing_was_on = self._check_xfce_comp()
        self._original_cursor_theme = self._get_cursor_theme()

        self._build_ui()
        self._load_settings()
        self._block_save = False
        
        # Initial display query and application
        self._refresh_displays()
        self._apply_now()

        self.installEventFilter(self)

    def _has_cmd(self, cmd):
        try:
            subprocess.run(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return True
        except Exception:
            return False

    def _check_picom(self):
        try:
            subprocess.check_output(["pgrep", "-x", "picom"])
            return True
        except Exception:
            return False

    def _check_xfce_comp(self):
        try:
            o = subprocess.check_output(
                ["xfconf-query", "-c", "xfwm4", "-p", "/general/use_compositing"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
            return o.lower() == "true"
        except Exception:
            return False

    def _set_xfce_comp(self, enable):
        try:
            subprocess.run(["xfconf-query", "-c", "xfwm4",
                             "-p", "/general/use_compositing", "--set",
                             "true" if enable else "false"], check=False)
            subprocess.Popen(["xfwm4", "--replace"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.4)
        except Exception:
            pass

    def _get_cursor_theme(self):
        try:
            return subprocess.check_output(
                ["xfconf-query", "-c", "xsettings", "-p", "/Gtk/CursorThemeName"],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except Exception:
            return ""

    def _set_cursor_theme(self, theme):
        if not theme:
            return
        try:
            subprocess.run(["xfconf-query", "-c", "xsettings",
                             "-p", "/Gtk/CursorThemeName", "--set", theme], check=False)
        except Exception:
            pass

    def _refresh_displays(self):
        """Cache connected displays instead of running xrandr on every frame."""
        if self.session_type == "wayland":
            self._displays_cache = ["Wayland-Display"]
            return self._displays_cache

        try:
            out = subprocess.check_output("xrandr --current", shell=True, stderr=subprocess.DEVNULL).decode()
            self._displays_cache = [l.split()[0] for l in out.splitlines() if " connected" in l]
        except Exception:
            self._displays_cache = []
        return self._displays_cache

    def _connected_displays(self):
        if self._displays_cache is None:
            return self._refresh_displays()
        return self._displays_cache

    def _build_ui(self):
        self.setWindowTitle("Kavram Screen & Color Manager (Optimized)")
        self.setMinimumSize(680, 640)
        
        # Load icon if available
        icon_path = os.path.join(self.BASE_DIR, "ikon", "Kavram.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QWidget {
                background-color: #262626;
                color: #E0E0E0;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
            }
            QLabel { color: #E0E0E0; }
            QGroupBox {
                border: 2px solid #363636;
                border-radius: 10px;
                margin-top: 1.5ex;
                font-weight: bold;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: #262626;
                color: #B0B0B0;
            }
            QSlider::groove:horizontal {
                border: 1px solid #3A3A3A;
                height: 8px;
                background: #444444;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #A0A0A0;
                border: 1px solid #707070;
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #00ADB5;
                border: 1px solid #00FFF0;
            }
        """)

        BTN_STYLE = """
            QPushButton {
                background-color: #333333;
                color: #E0E0E0;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 5px 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover  { background-color: #3D3D3D; border: 1px solid #777777; }
            QPushButton:pressed{ background-color: #1A1A1A; }
            QPushButton:checked{ background-color: #00ADB5; border: 1px solid #00FFF0; color: #ffffff; }
            QPushButton:disabled{ background-color: #202020; color: #555; border: 1px solid #333; }
        """

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

        # ── TOP BAR ────────────────────────────────────────────────────────
        top_bar = QFrame()
        top_bar.setFixedHeight(48)
        top_bar.setStyleSheet("background-color: #1A1A1A; border-bottom: 2px solid #3A3A3A;")
        bar = QHBoxLayout(top_bar)
        bar.setContentsMargins(15, 5, 15, 5)
        bar.setSpacing(10)

        self.reset_button = QPushButton("Reset")
        self.reset_button.setFixedHeight(32)
        self.reset_button.setStyleSheet(BTN_STYLE)
        self.reset_button.setCursor(Qt.PointingHandCursor)
        self.reset_button.clicked.connect(self._reset)
        bar.addWidget(self.reset_button)

        self.refresh_btn = QPushButton("Refresh Displays")
        self.refresh_btn.setFixedHeight(32)
        self.refresh_btn.setStyleSheet(BTN_STYLE)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setToolTip("Rescan connected monitors")
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
        bar.addWidget(self.refresh_btn)

        # Autostart toggle button
        self.autostart_button = QPushButton("Autostart")
        self.autostart_button.setFixedHeight(32)
        self.autostart_button.setStyleSheet(BTN_STYLE)
        self.autostart_button.setCursor(Qt.PointingHandCursor)
        self.autostart_button.setCheckable(True)
        self.autostart_button.setToolTip("Automatically apply color settings on system startup")
        
        autostart_path = os.path.expanduser("~/.config/autostart/kavram_blf.desktop")
        self.autostart_button.setChecked(os.path.exists(autostart_path))
        self.autostart_button.toggled.connect(self._on_autostart_toggled)
        bar.addWidget(self.autostart_button)

        bar.addStretch()

        self.reading_button = QPushButton("Reading Mode")
        self.reading_button.setFixedHeight(32)
        self.reading_button.setStyleSheet(BTN_STYLE)
        self.reading_button.setCursor(Qt.PointingHandCursor)
        self.reading_button.setCheckable(True)
        self.reading_button.toggled.connect(self._on_reading)

        self.gray_button = QPushButton("Grayscale")
        self.gray_button.setFixedHeight(32)
        self.gray_button.setStyleSheet(BTN_STYLE)
        self.gray_button.setCursor(Qt.PointingHandCursor)
        self.gray_button.setCheckable(True)
        self.gray_button.toggled.connect(self._apply)

        bar.addWidget(self.reading_button)
        bar.addWidget(self.gray_button)

        main_layout.addWidget(top_bar)

        content = QVBoxLayout()
        content.setContentsMargins(15, 10, 15, 10)
        content.setSpacing(10)

        # Status Group
        sg = QGroupBox("System Status")
        sl = QVBoxLayout()
        self.status_label = QLabel("Status: Active")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #00ADB5; font-size: 14px; font-weight: bold;")
        sl.addWidget(self.status_label)
        sg.setLayout(sl)
        content.addWidget(sg)

        # Blue Light Filter
        bg = QGroupBox("Blue Light Filter (Aggressive Curve)")
        bv = QVBoxLayout()
        self.blue_filter_slider = self._make_row(
            bv, "Blue Light Filter Level",
            "0–40: Mild blue attenuation | 40–80: Deep night protection | 80–100: Ultra warmth for night reading",
            0, 100, 0
        )
        bg.setLayout(bv)
        content.addWidget(bg)

        # Color Channels
        cg = QGroupBox("RGB Color Balance")
        cv = QVBoxLayout()
        self.red_slider = self._make_row(
            cv, "Red Channel",
            "Enhances warmth and compensates for high blue attenuation",
            50, 160, 100
        )
        self.green_slider = self._make_row(
            cv, "Green Channel",
            "Adjusts green warmth tint — recommended at default (100)",
            50, 160, 100
        )
        cg.setLayout(cv)
        content.addWidget(cg)

        # Brightness & Darkness
        pg = QGroupBox("Brightness & Gamma Darkness")
        pv = QVBoxLayout()
        self.brightness_slider = self._make_row(
            pv, "Display Brightness",
            "Hardware/Software global display luminance control",
            20, 150, 100
        )
        self.darkness_slider = self._make_row(
            pv, "Gamma Darkness Attenuation",
            "Non-linear gamma curve reduction — deeply dims bright backgrounds in low-light rooms",
            0, 80, 0
        )
        pg.setLayout(pv)
        content.addWidget(pg)

        # Recovery hint
        shortcut_lbl = QLabel("Shortcut: Press Alt + V to instantly reset all screen settings if display gets distorted.")
        shortcut_lbl.setStyleSheet(HINT_STYLE + "padding: 4px;")
        shortcut_lbl.setAlignment(Qt.AlignCenter)
        content.addWidget(shortcut_lbl)

        content.addStretch()
        main_layout.addLayout(content)

    def _make_row(self, layout, name, hint_text, min_v=0, max_v=100, def_v=0):
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("color: #EEEEEE; font-size: 13px; font-weight: bold;")
        layout.addWidget(name_lbl)

        sld = QSlider(Qt.Horizontal)
        sld.setRange(min_v, max_v)
        sld.setValue(def_v)
        # Connect to debounced applier rather than instant process creation
        sld.valueChanged.connect(self._apply)
        layout.addWidget(sld)

        hint_lbl = QLabel(hint_text)
        hint_lbl.setStyleSheet(HINT_STYLE)
        hint_lbl.setWordWrap(True)
        layout.addWidget(hint_lbl)

        return sld

    def _on_refresh_clicked(self):
        self._refresh_displays()
        self._apply_now()

    def _on_autostart_toggled(self, checked):
        autostart_dir = os.path.expanduser("~/.config/autostart")
        desktop_file = os.path.join(autostart_dir, "kavram_blf.desktop")

        if checked:
            os.makedirs(autostart_dir, exist_ok=True)
            script_path = os.path.abspath(__file__)
            content = f"""[Desktop Entry]
Type=Application
Exec={sys.executable} "{script_path}" --startup
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Kavram Screen Manager
Comment=Applies custom screen color and brightness profile on login
"""
            try:
                with open(desktop_file, "w") as f:
                    f.write(content)
                os.chmod(desktop_file, 0o755)
            except Exception as e:
                print("Failed to create autostart desktop entry:", e)
        else:
            if os.path.exists(desktop_file):
                try:
                    os.remove(desktop_file)
                except Exception:
                    pass

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.modifiers() == Qt.AltModifier and event.key() == Qt.Key_V:
                self._reset()
                return True
        return super().eventFilter(obj, event)

    def _apply_ctm(self, displays, enable):
        gray_ctm = ("913110047,0,3071760610,0,310096639,0,"
                    "913110047,0,3071760610,0,310096639,0,"
                    "913110047,0,3071760610,0,310096639,0")
        id_ctm   = "0,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,1"
        for d in displays:
            try:
                subprocess.run(["xrandr", "--output", d, "--set", "CTM",
                                 gray_ctm if enable else id_ctm],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def _apply_shader(self, enable):
        os.makedirs(self.VERI_DIR, exist_ok=True)
        if enable:
            if self.xfce_compositing_was_on:
                self._set_xfce_comp(False)
            subprocess.call(["pkill", "picom"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(0.2)
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
            with open(self.SHADER_FILE, "w") as f:
                f.write(shader)
            subprocess.Popen(
                ["picom", "--backend", "glx", "--window-shader-fg", self.SHADER_FILE, "--no-use-damage"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return True
        else:
            subprocess.call(["pkill", "picom"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if self.picom_was_running:
                subprocess.Popen(["picom"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if self.xfce_compositing_was_on:
                self._set_xfce_comp(True)
            return False

    def _enable_gray(self):
        if self.grayscale_method:
            return
        displays = self._connected_displays()
        if not displays or self.session_type == "wayland":
            self.grayscale_method = "gamma"
            return

        try:
            verbose = subprocess.check_output(
                f"xrandr --output {displays[0]} --verbose", shell=True, stderr=subprocess.DEVNULL
            ).decode()
            if "CTM" in verbose:
                self._apply_ctm(displays, True)
                self.grayscale_method = "ctm"
                self._set_cursor_theme("DMZ-White")
            elif self._apply_shader(True):
                self.grayscale_method = "shader"
            else:
                self.grayscale_method = "gamma"
        except Exception:
            self.grayscale_method = "gamma"

    def _disable_gray(self):
        if self.grayscale_method == "ctm":
            self._apply_ctm(self._connected_displays(), False)
            if self._original_cursor_theme:
                self._set_cursor_theme(self._original_cursor_theme)
        elif self.grayscale_method == "shader":
            self._apply_shader(False)
        self.grayscale_method = None

    def _blue_params(self):
        """
        Aggressive blue filter calculation curve:
        - 0 to 40%: Smooth gradual blue reduction (1.0 -> 0.40)
        - 40 to 80%: Aggressive steep blue drop (0.40 -> 0.08)
        - 80 to 100%: Ultra warm night mode (0.08 -> 0.02)
        """
        val = self.blue_filter_slider.value() / 100.0

        if val <= 0.40:
            norm = val / 0.40
            blue_g = 1.0 - (norm * 0.60)  # 1.0 down to 0.40
            extra_br = 1.0
        elif val <= 0.80:
            norm = (val - 0.40) / 0.40
            blue_g = 0.40 - (norm * 0.32)  # 0.40 down to 0.08
            extra_br = 1.0 - (norm * 0.15)
        else:
            norm = (val - 0.80) / 0.20
            blue_g = 0.08 - (norm * 0.06)  # 0.08 down to 0.02
            extra_br = 0.85 - (norm * 0.15)

        return blue_g, extra_br

    def _apply(self, *_):
        """Starts 35ms single-shot timer to debounce high-frequency slider drag events."""
        self._apply_timer.start(35)

    def _apply_now(self):
        is_gray = self.gray_button.isChecked()
        
        # Enhanced darkness calculation with parabolic attenuation curve
        darkness_val = self.darkness_slider.value() / 100.0
        dark_coef = (1.0 - darkness_val) ** 1.35  # Non-linear curve for smoother shadow dimming

        br_base = self.brightness_slider.value() / 100.0
        blue_g, extra_br = self._blue_params()

        br = br_base * extra_br

        r = (self.red_slider.value() / 100.0) * dark_coef
        g = (self.green_slider.value() / 100.0) * dark_coef
        b = blue_g * dark_coef

        if is_gray:
            self._enable_gray()
            if self.grayscale_method == "gamma":
                avg = 0.2126 * r + 0.7152 * g + 0.0722 * b
                r = g = b = avg
        else:
            if self.grayscale_method:
                self._disable_gray()

        clamp = lambda v: max(0.05, round(v, 4))
        r_c, g_c, b_c = clamp(r), clamp(g), clamp(b)
        br_str = f"{max(0.1, round(br, 4))}"
        gamma_str = f"{r_c}:{g_c}:{b_c}"

        # ── Wayland Execution Branch ────────────────────────────────────
        if self.session_type == "wayland":
            if self.has_gammastep:
                # Map blue light level to Kelvin color temperature (6500K down to 1800K)
                temp = int(6500 - (self.blue_filter_slider.value() * 47))
                subprocess.Popen(
                    ["gammastep", "-O", str(temp), "-b", f"{br_str}:0.8"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            elif self.has_wlsunset:
                temp = int(6500 - (self.blue_filter_slider.value() * 47))
                subprocess.Popen(
                    ["wlsunset", "-T", str(temp)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
        # ── X11 Execution Branch ────────────────────────────────────────
        else:
            displays = self._connected_displays()
            for d in displays:
                try:
                    subprocess.run(
                        ["xrandr", "--output", d, "--gamma", gamma_str, "--brightness", br_str],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                except Exception:
                    pass

        self._update_status()
        if not self._block_save:
            self._save()

    def _on_reading(self, checked):
        self._block_save = True
        if checked:
            self.red_slider.setValue(120)
            self.green_slider.setValue(92)
            self.blue_filter_slider.setValue(65)
            self.brightness_slider.setValue(82)
            self.darkness_slider.setValue(12)
        else:
            self.red_slider.setValue(100)
            self.green_slider.setValue(100)
            self.blue_filter_slider.setValue(0)
            self.brightness_slider.setValue(100)
            self.darkness_slider.setValue(0)
        self._block_save = False
        self._apply_now()

    def _save(self):
        os.makedirs(self.VERI_DIR, exist_ok=True)
        data = {
            "red": self.red_slider.value(),
            "green": self.green_slider.value(),
            "blue_filter": self.blue_filter_slider.value(),
            "brightness": self.brightness_slider.value(),
            "darkness": self.darkness_slider.value(),
            "gray": self.gray_button.isChecked(),
            "reading": self.reading_button.isChecked(),
        }
        try:
            with open(self.SETTINGS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load_settings(self):
        self._block_save = True
        d = self.DEFAULTS.copy()
        if os.path.exists(self.SETTINGS_FILE):
            try:
                with open(self.SETTINGS_FILE) as f:
                    saved = json.load(f)
                d.update(saved)
            except Exception:
                pass

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
        self._apply_now()

    def _update_status(self):
        m = f" [{self.grayscale_method}]" if self.grayscale_method else ""
        bf = self.blue_filter_slider.value()
        gray = f"GRAY: ON{m}" if self.gray_button.isChecked() else "GRAY: off"

        if bf == 0:
            flt = "Blue Filter: Off"
        elif bf <= 35:
            flt = f"Blue Filter: %{bf} [Mild]"
        elif bf <= 75:
            flt = f"Blue Filter: %{bf} [Strong]"
        else:
            flt = f"Blue Filter: %{bf} [Ultra Warm]"

        rd = " | Reading: ON" if self.reading_button.isChecked() else ""
        session_info = f" ({self.session_type.upper()})"
        self.status_label.setText(f"Status: Active{session_info}  |  {gray}  |  {flt}{rd}")

    def closeEvent(self, event):
        self._save()
        event.accept()


if __name__ == "__main__":
    if "--startup" in sys.argv:
        time.sleep(3)

    app = QApplication(sys.argv)
    w = Settings()

    if "--startup" in sys.argv:
        sys.exit(0)

    w.show()
    sys.exit(app.exec_())
