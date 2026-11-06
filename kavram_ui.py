# -*- coding: utf-8 -*-
"""
kavram_ui.py  —  Kavram ortak arayüz dili
=========================================

Bütün editörler (text, sound, drawing, media, rec, sphere, ai, filter, converter,
copy, file_manager ...) bu tek dosyadan aynı renkleri, aynı düğme tasarımını ve aynı
üst bar davranışını kullanır.  Böylece hepsi aynı sistemin parçası olarak görünür.

Bu dosyada olanlar
------------------
1.  TEMA            : renk sabitleri + hazır stiller (style_text, style_mini, style_active ...)
2.  KButton         : QPushButton yerine geçer.  Tasarım ölçüsü (30x30 / 90x30 ...) KORUNUR;
                      yazı sığmazsa düğme genişler, yazı asla kesilmez.  Yazı sonradan
                      değişirse (Play/Stop, 12 -> 100 ...) düğme kendiliğinden yeniden ölçülür.
3.  KToolButton     : aynısı QToolButton için (yalnızca açıklama desteği).
4.  ToolbarLayout   : iki taraflı üst bar.  Sol grup = "diğer düğmeler", sağ grup = "Export +
                      editör adı".  Pencere daralırsa sağ köşe düğmeleri alt satıra düşer,
                      gerekirse sol grup da satır atlar.  Üst bar yüksekliği buna göre uzar.
5.  Açıklamalar     : her düğmenin üstünde fare 0,6 saniye durunca siyah zemin / beyaz yazı ile
                      Türkçe açıklama çıkar.  Açıklamalar aşağıdaki TIPS_* sözlüklerindedir.
6.  install()       : uygulama genelinde tema + açıklama gecikmesini kurar (KButton ilk
                      oluşturulduğunda kendiliğinden çağrılır; elle çağırmak gerekmez).

Yeni düğme eklerken:   from kavram_ui import KButton   ->   KButton("Ad")
Yeni açıklama eklerken: aşağıdaki TIPS_ATTR (öznitelik adı) veya TIPS_TEXT (yazı) sözlüğüne bir satır.
Hata ayıklama:          KAVRAM_UI_EKSIK=1 python3 kavram.py   -> açıklaması olmayan düğmeleri yazar.
"""
import os
import re
import sys

from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QFont, QFontMetrics, QColor, QPalette
from PyQt5.QtWidgets import (
    QApplication, QLayout, QPushButton, QProxyStyle, QSizePolicy, QSpacerItem,
    QStyle, QToolButton, QToolTip,
)

# ===========================================================================
# 1) TEMA
# ===========================================================================
BG = "#222"               # pencere / üst bar zemini
BG_PANEL = "#282828"      # açılır liste, panel
BG_MENU = "#333"          # menü zemini
BORDER = "#555"           # çerçeve
HOVER = "#444"            # fare üstünde
PRESSED = "#666"          # basılıyken
ACTIVE_BG = "#555"        # açık (toggle) durum
ACTIVE_BORDER = "#888"
ACTIVE_HOVER = "#666"
ACTIVE_PRESSED = "#777"
TEXT = "white"
DISABLED_BG = "#333"
DISABLED_TEXT = "#777"
DISABLED_BORDER = "#444"
TIP_BG = "#000"           # açıklama balonu: siyah zemin
TIP_FG = "#fff"           # açıklama balonu: beyaz yazı

ICON_W = 30               # kare (ikon) düğme
BTN_W = 90                # yazılı düğme
BTN_H = 30                # bütün düğmelerin yüksekliği
RADIUS = 8
TOOLBAR_H = 40            # tek satırlık üst bar yüksekliği
TOOLBAR_QSS = "background-color: #222; border-bottom: 2px solid #555;"
MAX_BTN_W = 420           # çok uzun yazılarda bile düğmenin ulaşabileceği en büyük genişlik
TIP_DELAY_MS = 600        # açıklama gecikmesi (0,6 saniye)

_ARROW_SVG = ("data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0i"
              "bm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cGF0aCBkPSJNNyAxMEwxMiAxNUwxNyAxMCIgc3Ryb2tl"
              "PSIjZWVlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPjwv"
              "c3ZnPg==")


def style_text():
    """Yazılı düğme (File, Export, Terminal ...)."""
    return f"""
        QPushButton {{ background-color: transparent; color: {TEXT}; font-size: 14px; font-weight: bold;
            border: 2px solid {BORDER}; border-radius: {RADIUS}px; padding: 2px 8px; }}
        QPushButton:hover {{ background-color: {HOVER}; }}
        QPushButton:pressed {{ background-color: {PRESSED}; }}
        QPushButton:checked {{ background-color: {ACTIVE_BG}; border-color: {ACTIVE_BORDER}; }}
        QPushButton:checked:hover {{ background-color: {ACTIVE_HOVER}; }}
        QPushButton:disabled {{ background-color: {DISABLED_BG}; color: {DISABLED_TEXT}; border-color: {DISABLED_BORDER}; }}
        QPushButton::menu-indicator {{ image: none; width: 0px; }}
    """


def style_mini():
    """Kare ikon / tek harfli düğme (30x30)."""
    return f"""
        QPushButton {{ background-color: transparent; color: {TEXT}; font-size: 16px;
            border: 2px solid {BORDER}; border-radius: {RADIUS}px; padding: 2px; }}
        QPushButton:hover {{ background-color: {HOVER}; }}
        QPushButton:pressed {{ background-color: {PRESSED}; }}
        QPushButton:checked {{ background-color: {ACTIVE_BG}; border-color: {ACTIVE_BORDER}; }}
        QPushButton:checked:hover {{ background-color: {ACTIVE_HOVER}; }}
        QPushButton:disabled {{ background-color: {DISABLED_BG}; color: {DISABLED_TEXT}; border-color: {DISABLED_BORDER}; }}
        QPushButton::menu-indicator {{ image: none; width: 0px; }}
    """


def style_active(mini=False):
    """Açık / seçili (toggle) durum."""
    size = "16px" if mini else "14px"
    bold = "" if mini else "font-weight: bold;"
    pad = "2px" if mini else "2px 8px"
    return f"""
        QPushButton {{ background-color: {ACTIVE_BG}; color: {TEXT}; font-size: {size}; {bold}
            border: 2px solid {ACTIVE_BORDER}; border-radius: {RADIUS}px; padding: {pad}; }}
        QPushButton:hover {{ background-color: {ACTIVE_HOVER}; }}
        QPushButton:pressed {{ background-color: {ACTIVE_PRESSED}; }}
        QPushButton:disabled {{ background-color: {DISABLED_BG}; color: {DISABLED_TEXT}; border-color: {DISABLED_BORDER}; }}
        QPushButton::menu-indicator {{ image: none; width: 0px; }}
    """


def style_toggle(active, mini=False):
    """active True ise 'açık' görünüm, değilse normal görünüm."""
    if active:
        return style_active(mini)
    return style_mini() if mini else style_text()


def style_dark():
    """Koyu (pasif görünümlü) kare düğme."""
    return f"""
        QPushButton {{ background-color: #111; color: #aaa; font-size: 16px;
            border: 2px solid #333; border-radius: {RADIUS}px; padding: 2px; }}
        QPushButton:hover {{ background-color: #222; }}
        QPushButton:pressed {{ background-color: #000; }}
    """


def style_disabled():
    return f"""
        QPushButton {{ background-color: {DISABLED_BG}; color: {DISABLED_TEXT}; font-size: 14px; font-weight: bold;
            border: 2px solid {DISABLED_BORDER}; border-radius: {RADIUS}px; padding: 2px 8px; }}
    """


def style_combo():
    """Açılır kutu — düğmeyle aynı görünüm."""
    return f"""
        QComboBox {{ background-color: transparent; color: {TEXT}; font-size: 14px; font-weight: bold;
            border: 2px solid {BORDER}; border-radius: {RADIUS}px; padding: 2px 8px; padding-left: 10px; }}
        QComboBox:hover {{ background-color: {HOVER}; }}
        QComboBox::drop-down {{ border: 0px; subcontrol-origin: padding; subcontrol-position: top right; width: 20px; }}
        QComboBox::down-arrow {{ image: url({_ARROW_SVG}); width: 16px; height: 16px; }}
        QComboBox QAbstractItemView {{ background-color: {BG_PANEL}; border: 1px solid {BORDER};
            selection-background-color: {HOVER}; color: {TEXT}; }}
    """


def style_menu():
    return f"""
        QMenu {{ background-color: {BG_MENU}; border: 1px solid {BORDER}; color: {TEXT}; padding: 5px; }}
        QMenu::item {{ padding: 5px 20px; min-width: 100px; }}
        QMenu::item:selected {{ background-color: {ACTIVE_BG}; }}
        QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
    """


def style_input():
    """QLineEdit — arama kutusu vb."""
    return f"""
        QLineEdit {{ background-color: {HOVER}; color: {TEXT}; border: 1px solid {BORDER};
            border-radius: 5px; padding: 3px; font-size: 14px; }}
        QLineEdit:focus {{ border: 1px solid #777; }}
    """


def style_toolbar():
    return TOOLBAR_QSS


def style_tool_button():
    """QToolButton (galeri / not düğmeleri)."""
    return f"""
        QToolButton {{ background-color: {HOVER}; color: #eee; border: 1px solid #666; border-radius: 6px; font-weight: bold; }}
        QToolButton:hover {{ background-color: {ACTIVE_BG}; color: white; border-color: {ACTIVE_BORDER}; }}
        QToolButton:pressed {{ background-color: #333; }}
        QToolButton:disabled {{ color: {DISABLED_TEXT}; border-color: {DISABLED_BORDER}; }}
    """


# Uygulama genelinde (düşük öncelikli) ortak stil: açıklama balonu, menü, kaydırma çubuğu, mesaj kutuları.
APP_QSS = f"""
QToolTip {{ background-color: {TIP_BG}; color: {TIP_FG}; border: 1px solid {BORDER};
    padding: 4px 8px; font-size: 13px; }}
QMenu {{ background-color: {BG_MENU}; border: 1px solid {BORDER}; color: {TEXT}; padding: 4px; }}
QMenu::item {{ padding: 5px 20px; }}
QMenu::item:selected {{ background-color: {ACTIVE_BG}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
QScrollBar:vertical {{ background: {BG}; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {BORDER}; min-height: 24px; border-radius: 5px; margin: 2px; }}
QScrollBar::handle:vertical:hover {{ background: #777; }}
QScrollBar:horizontal {{ background: {BG}; height: 12px; margin: 0; }}
QScrollBar::handle:horizontal {{ background: {BORDER}; min-width: 24px; border-radius: 5px; margin: 2px; }}
QScrollBar::handle:horizontal:hover {{ background: #777; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QMessageBox, QInputDialog {{ background-color: {BG_MENU}; }}
QMessageBox QLabel, QInputDialog QLabel {{ color: {TEXT}; background: transparent; }}
"""


# ===========================================================================
# 2) KURULUM: açıklama gecikmesi (0,6 sn) + siyah/beyaz balon + ortak stil
# ===========================================================================
class _KStyle(QProxyStyle):
    """Mevcut stili aynen korur; yalnızca açıklama balonunun bekleme süresini değiştirir."""

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.SH_ToolTip_WakeUpDelay:
            return TIP_DELAY_MS
        if hint == QStyle.SH_ToolTip_FallAsleepDelay:
            return 0          # başka düğmeye geçince de 0,6 sn beklensin
        return super().styleHint(hint, option, widget, returnData)


_installed = {"done": False}


def install(app=None):
    """Tema + açıklama davranışını kurar.  Birden çok çağrılsa da bir kez çalışır."""
    if _installed["done"]:
        return True
    app = app or QApplication.instance()
    if app is None:
        return False
    _installed["done"] = True
    try:
        base = app.style().objectName() or "fusion"
        app.setStyle(_KStyle(base))
    except Exception as exc:                      # stil değişmezse de açıklamalar çalışır
        print("[kavram_ui] stil kurulamadı:", exc)
    try:
        pal = QPalette(QToolTip.palette())
        pal.setColor(QPalette.ToolTipBase, QColor(TIP_BG))
        pal.setColor(QPalette.ToolTipText, QColor(TIP_FG))
        QToolTip.setPalette(pal)
        f = QToolTip.font()
        f.setPixelSize(13)
        QToolTip.setFont(f)
    except Exception as exc:
        print("[kavram_ui] balon paleti kurulamadı:", exc)
    try:
        app.setStyleSheet((app.styleSheet() or "") + APP_QSS)
    except Exception as exc:
        print("[kavram_ui] ortak stil kurulamadı:", exc)
    return True


# ===========================================================================
# 3) AÇIKLAMALAR (Türkçe)  —  önce öznitelik adına, sonra yazıya bakılır
# ===========================================================================
TIPS_ATTR = {
    # ---- ortak (bütün editörlerde aynı anlam) ----
    "file_button": "Dosya: dosya seçme penceresini açar; kayıtlı bir çalışmayı veya dosyayı açarsın.",
    "btn_file": "Dosya: dosya seçme penceresini açar; işlenecek dosyayı seçersin.",
    "file_btn": "Dosya: medya dosyalarını seçip zaman çizelgesine ekler.",
    "save_button": "Kaydet: çalışmanı hızlıca kaydeder.",
    "quick_save_button": "Hızlı kaydet: çalışmanı hemen kaydeder.",
    "save_btn": "Kaydet: açık notu / çalışmayı hızlıca kaydeder.",
    "undo_button": "Geri al: son yaptığın işlemi geri alır (Ctrl+Z).",
    "undo_btn": "Geri al: son yaptığın işlemi geri alır (Ctrl+Z).",
    "redo_button": "İleri al: geri aldığın işlemi tekrar uygular (Ctrl+Shift+Z).",
    "redo_btn": "İleri al: geri aldığın işlemi tekrar uygular (Ctrl+Shift+Z).",
    "export_button": "Dışa aktar: çalışmanı Export klasörüne / seçtiğin yere aktarır.",
    "btn_export": "Dışa aktar: sonucu Export klasörüne / seçtiğin yere aktarır.",
    "Export_button": "Dışa aktar: sesi Export klasörüne / seçtiğin yere aktarır.",
    "export_btn": "Dışa aktar: zaman çizelgesindeki medyayı birleştirip dışa aktarır.",
    # ---- editör adı düğmeleri (köşedeki düğme) ----
    "sound_button": "Editör değiştirici: Kavram'daki diğer editörlere geçiş penceresini açar.",
    "text_button": "Editör değiştirici: Kavram'daki diğer editörlere geçiş penceresini açar.",
    "drawing_button": "Editör değiştirici: Kavram'daki diğer editörlere geçiş penceresini açar.",
    "sphere_button": "Editör değiştirici: Kavram'daki diğer editörlere geçiş penceresini açar.",
    "media_btn": "Editör değiştirici: Kavram'daki diğer editörlere geçiş penceresini açar.",
    "ai_button": "Editör değiştirici: Kavram'daki diğer editörlere geçiş penceresini açar.",
    # ---- text ----
    "font_size_button": "Yazı boyutu: tıklayınca boyut listesi açılır; fare tekerleği ile de değiştirilir.",
    "center_btn": "Ortala: açıksa yazılan satırlar ortalanır.",
    "bold_btn": "Kalın: açıksa yazılan metin kalın olur.",
    "color_btn": "Renk: yazı rengi panelini açar; seçilen renkler HEX kodlarıyla görünür.",
    "symbol_toggle_button": "Sembol paneli: özel sembol ve kısayol panelini açar / kapatır.",
    "read_mode_button": "Otomatik kaydırma / okuma modu: metni kendiliğinden aşağı kaydırır.",
    "scroll_speed_button": "Kaydırma hızı: tıklayınca hız listesi açılır; fare tekerleği ile de değiştirilir.",
    "terminal_button": "Terminal: yerleşik komut penceresini açar.",
    "search_button": "Ara: kutuya yazdığın kelimeyi metinde arar.",
    "prev_match_button": "Önceki sonuç: aramada bir önceki eşleşmeye gider.",
    "next_match_button": "Sonraki sonuç: aramada bir sonraki eşleşmeye gider.",
    "delete_btn": {"Sil": "Silme modu: açıkken renge tıklayınca renk silinir.",
                   "Delete": "Sil: seçili medya parçasını siler.",
                   "*": "Sil: seçili öğeyi siler."},
    "dot_btn": "Nokta modu: açıkken sembol paneli nokta ve üst simge girişi yapar.",
    "caps_btn": "Büyük harf: sembol panelindeki harfleri büyük / küçük yapar.",
    "nav_btn": "Gezinme modu: açıkken sembol paneli imleç hareketi için kullanılır.",
    "add_btn": "Yeni sembol ekle: sembol paneline kendi sembolünü eklersin.",
    # ---- sound ----
    "cut_button": "Kes: oynatma çizgisinin bulunduğu yerden sesi böler.",
    "similar_delete_button": "Benzer boşlukları sil: seçili alanın kalınlığındaki (ses seviyesi / sessizlik) tüm boşlukları siler.",
    "delete_button": "Sil: seçili ses parçalarını siler.",
    "play_button": "Oynat / Durdur: sesi oynatır veya durdurur.",
    "record_button": "Kayıt: mikrofondan kayıt alıp oynatma çizgisine ekler.",
    "filter_button": "Gürültü filtresi: aktif filtreleri uygular; ayar kalıcıdır.",
    "wave_scale_button": "Dalga formu genişliği (1-12): ses dalgasının yatay ölçeğini ayarlar.",
    "panel_toggle_button": "Geçici metin paneli: ses üzerinde not alma panelini açar / kapatır.",
    "center_text_button": "Metni ortala / sola yasla.",
    # ---- media ----
    "play_pause_btn": "Oynat / Durdur: zaman çizelgesindeki medyayı oynatır veya durdurur.",
    "sequence_play_btn": "Sıralı oynatma: parçaları sırayla art arda oynatma modunu açar / kapatır.",
    "cut_btn": "Kes: oynatma çizgisinin bulunduğu yerden medyayı böler.",
    "camera_mode_btn": "Kamera: kameradan görüntü kaydı alır.",
    "audio_mode_btn": "Ses: ses kaydı alma modunu açar / kapatır.",
    "noise_filter_button": "Gürültü azaltma filtresi: açar / kapatır.",
    "clear_folders_btn": "Temizle: medya geçici klasörlerini boşaltır.",
    # ---- rec ----
    "camera_button_feature": "Yüzen kamera: kamera penceresi ekran kaydına girer.",
    "windows_button": "Pencereler: kaydedilecek pencereyi / ekranı seçer.",
    "btn_s_kurtarma": "Kurtarma: yarım kalan kayıt dosyalarını denetler ve kurtarır.",
    "thickness_button": "Çizim kalınlığı: ekran üstü çizim kalınlığını ayarlar; tıklayınca varsayılan konuma döner.",
    "keystroke_toggle_button": "Tuş gösterimi: bastığın tuşları ekranda gösterir / gizler.",
    "z_toggle_button": "Z katmanı: ekran üstü gösterimleri açar / kapatır.",
    "main_play_pause_button": "Oynat / Durdur: açılan kaydı oynatır veya durdurur.",
    "main_close_playback_button": "Kapat: oynatma çubuğunu kapatır.",
    "camera_button": "Kayıt: ekran / kamera kaydını başlatır veya durdurur.",
    # ---- filter ----
    "btn_noise": "Gürültü profili ekle: gürültü örneği seçerek profil oluşturur.",
    "btn_edit": "Düzenleme paneli: filtre ayarlarının bulunduğu paneli açar / kapatır.",
    "btn_process": "İşle: seçili filtreleri sese uygular.",
    "btn_reset": "Sıfırla: bütün profilleri ve ayarları başa döndürür.",
    "btn_play": "Oynat / Durdur: sesi oynatır veya durdurur.",
    "btn_music": "Müzik: arka plan müziği seçer (sağ tık: kalıcı müzik seç).",
    "btn_convert": "Dönüştür: seçili dosyayı seçtiğin biçime çevirir.",
    "btn_cover": "Kapak resmi seç: ses dosyasına kapak olarak resim ekler.",
    "btn_vid_aud": "Harici ses ekle: videoya ayrı bir ses dosyasını senkronlayarak ekler.",
    # ---- drawing ----
    "add_page_btn": "Sayfa ekle: yeni bir çizim sayfası ekler.",
    "remove_page_btn": "Sayfa sil: açık çizim sayfasını siler.",
    "nav_button": "Gezinme modu: tıklayınca değişir; sağ tık çözünürlük penceresini açar.",
    "g_button": "Referans görseli tüm sayfalarda göster / gizle (sağ tık: ayarlar).",
    "page_button": "Sayfa: fare tekerleği ile sayfalar arasında gezinir; tıklayınca sayfa listesi açılır.",
    "mix_angle_button": "Karışım açısı: fare tekerleği ile değişir; sağ tık karışım türü menüsü.",
    "color_button": "Renk: renk karıştırma panelini açar.",
    "eraser_button": "Silgi: çizimi siler; açıkken fırça yerine silgi kullanılır.",
    "radius_button": "Fırça yarıçapı: tekerlekle değişir, tıklayınca menü açılır.",
    "layer_button": "Katman paneli: katmanları açar / kapatır.",
    "always_top_btn": "Seçili olmayan katmanları üstte tut.",
    "select_button": "S modu: piksel seçimi (A modu ile aynı anda açık olamaz).",
    "point_button": "A modu: nokta düzenleme (S modu ile aynı anda açık olamaz).",
    "lazy_mouse_button": "Lazy Mouse: yavaşlatılmış fare, düzgün çizgi için.",
    "pressure_button": "Basınç hassasiyeti: kalem baskısına göre kalınlığı değiştirir.",
    "mirror_button": "Ayna: sol tık dikey, sağ tık yatay ayna çizimi açar / kapatır.",
    "play_btn": "Oynat / Durdur: animasyonu veya sesi oynatır.",
    "onion_btn": "Soğan zarı: önceki ve sonraki kareleri soluk gösterir.",
    "btn_top": "Üst: bu katmanı en üste alır.",
    "btn_bottom": "Alt: bu katmanı en alta alır.",
    # ---- sphere ----
    "add_box_button": "Kutu ekle: sahneye yeni bir kare / kutu ekler.",
    "grid_toggle_button": "Izgara: sahnedeki ızgarayı gösterir / gizler.",
    "editor_action_button": "Editörde aç: bu kareye bağlı editörü açar (çift tıklama da açar).",
    "select_editor_button": "Editör seç: bu kareye bağlanacak editörü seçersin.",
    "close_button": "Kapat: bu kareyi sahneden kaldırır.",
    # ---- ai ----
    "send_button": "Gönder: yazdığın mesajı yapay zekâya iletir.",
    "summary_btn": "Etkinleştir: bu paketi yapay zekâ hafızasında etkin yapar.",
    "btn_delete_packet": "Bu paketi sil.",
    "new_button": "Yeni paket: yeni bir hafıza paketi oluşturur.",
    "chat_button": "Sohbet: sohbet sayfasını açar.",
    "edit_button": "Veriler: hafıza paketlerinin düzenlendiği sayfayı açar.",
    "clear_chat_button": "Sohbeti temizle: sohbet geçmişini siler.",
    "exit_fullscreen_button": "Tam ekrandan çık: büyütülmüş medyayı kapatır.",
    "clear_ai_button": "Temizle: açık verileri ve 'ai' klasörünü temizler.",
    # ---- file_manager ----
    "btn_back": "Geri: önceki klasöre döner.",
    "btn_forward": "İleri: geri gidilen klasöre tekrar ilerler.",
    "btn_up": "Üst klasör: bir üst klasöre çıkar.",
    "btn_home": "Export klasörü: Kavram'ın export klasörüne gider.",
    "btn_preview": "Önizleme: fare üstüne gelince dosya önizlemesini açar / kapatır.",
    "btn_refresh": "Yenile: klasör içeriğini yeniden okur.",
    # ---- copy ----
    "current_btn": "Renk: seçili rengi gösterir; tıklayınca renk seçicisini açar.",
    "btn_del": "Sil: bu notu kalıcı olarak siler.",
    "btn_exp": "Genişlet: notu açıp tam görünümde gösterir.",
    "copy_btn": "Kopyala: notun içeriğini panoya kopyalar.",
    "max_btn": "Büyüt / küçült: notu tam görünüme alır veya geri küçültür.",
    "close_btn": "Kapat.",
    # ---- kod ----
    "choose": "Klasör seç: işlenecek klasörü seçersin.",
    "clear": "Temizle: listeyi / seçimi temizler.",
}

TIPS_TEXT = {
    "File": "Dosya: dosya seçme penceresini açar.",
    "Export": "Dışa aktar: çalışmanı Export klasörüne / seçtiğin yere aktarır.",
    "Terminal": "Terminal: yerleşik komut penceresini açar.",
    "Play": "Oynat / Durdur.",
    "Cut": "Kes: oynatma çizgisinden böler.",
    "Delete": "Sil: seçili öğeyi siler.",
    "Record": "Kayıt: kayıt almayı başlatır / durdurur.",
    "Rec": "Kayıt: kayıt almayı başlatır / durdurur.",
    "Stop": "Durdur.",
    "Reset": "Sıfırla: ayarları başa döndürür.",
    "Process": "İşle: seçili işlemi uygular.",
    "Convert": "Dönüştür: seçili dosyayı seçtiğin biçime çevirir.",
    "Color": "Renk: renk panelini açar.",
    "Eraser": "Silgi: çizimi siler.",
    "Müzik": "Müzik: arka plan müziği seçer.",
    "Camera": "Kamera.",
    "Sound": "Ses.",
    "Windows": "Pencereler.",
    "New": "Yeni: yeni bir kayıt oluşturur.",
    "Chat": "Sohbet sayfasını açar.",
    "Edit": "Düzenleme sayfasını açar.",
    "OK": "Tamam: değişikliği onaylar ve pencereyi kapatır.",
    "Tamam": "Tamam: değişikliği onaylar ve pencereyi kapatır.",
    "Kaydet": "Kaydet: değişiklikleri kaydeder.",
    "İptal": "İptal: değişiklik yapmadan pencereyi kapatır.",
    "Iptal": "İptal: değişiklik yapmadan pencereyi kapatır.",
    "Cancel": "İptal: değişiklik yapmadan pencereyi kapatır.",
    "Sil": "Sil: seçili öğeyi siler.",
    "Gözat…": "Gözat: klasör / dosya seçme penceresini açar.",
    "Dışa Aktar": "Dışa aktar: seçtiğin ayarlarla çıktıyı oluşturur.",
    "Yenile": "Yenile: içeriği yeniden okur.",
    "Geri": "Geri: önceki konuma döner.",
    "İleri": "İleri: sonraki konuma gider.",
    "Üst": "Üst: bir üst düzeye çıkar.",
    "Alt": "Alt: bir alt düzeye iner.",
    "Seçilenleri sıfırla": "Seçili öğeleri sıfırlar.",
    "Select Editor": "Editör seç: bu kareye bağlanacak editörü seçersin.",
    "Klasör": "Klasör seç.",
    "Temizle": "Temizle.",
    "X": "Kapat.",
    "x": "Sil / kapat.",
    "+": "Ekle.",
    "-": "Çıkar.",
    "↑": "Gönder.",
    "_": "Küçült / kapat.",
}


def _attr_name(btn):
    """Düğmenin, ait olduğu pencerede hangi öznitelik adıyla tutulduğunu bulur."""
    p = btn.parentWidget()
    guard = 0
    while p is not None and guard < 12:
        try:
            for k, v in vars(p).items():
                if v is btn:
                    return k
        except Exception:
            pass
        p = p.parentWidget()
        guard += 1
    return ""


def describe(btn):
    """Düğme için Türkçe açıklama bulur; bulamazsa ''."""
    name = btn.objectName() or _attr_name(btn)
    try:
        txt = btn.text().strip()
    except Exception:
        txt = ""
    if name and name in TIPS_ATTR:
        val = TIPS_ATTR[name]
        if isinstance(val, dict):          # aynı ad, farklı editörde farklı anlam: yazıya göre seç
            return val.get(txt) or val.get("*", "")
        return val
    if txt and txt in TIPS_TEXT:
        return TIPS_TEXT[txt]
    return ""


def tip(widget, text):
    """Elle açıklama koy (ör. kod içinde:  kui.tip(self.btn, "Kaydet: ...")) ."""
    widget.setToolTip(text)
    return widget


_eksik = set()


def _tipi_uygula(btn):
    if btn.toolTip():
        return
    t = describe(btn)
    if t:
        btn.setToolTip(t)
    elif os.environ.get("KAVRAM_UI_EKSIK"):
        key = (btn.objectName() or _attr_name(btn) or "?", btn.text())
        if key not in _eksik:
            _eksik.add(key)
            print(f"[kavram_ui] açıklaması yok: ad={key[0]!r} yazı={key[1]!r}", file=sys.stderr)


# ===========================================================================
# 4) KButton / KToolButton
# ===========================================================================
_RE_PAD = re.compile(r"padding\s*:\s*(\d+)px(?:\s+(\d+)px)?(?:\s+(\d+)px)?(?:\s+(\d+)px)?")
_RE_BORDER = re.compile(r"border\s*:\s*(\d+)px")
_RE_FONT = re.compile(r"font-size\s*:\s*(\d+)px")
_RE_BOLD = re.compile(r"font-weight\s*:\s*(bold|[6-9]00)")


def _horiz_padding(ss):
    m = _RE_PAD.search(ss or "")
    if not m:
        return 8
    v = [int(x) for x in m.groups() if x is not None]
    if len(v) == 1:
        return v[0] * 2
    if len(v) == 2:
        return v[1] * 2
    if len(v) == 3:
        return v[1] * 2
    return v[1] + v[3]


class KButton(QPushButton):
    """Kavram ortak düğmesi.

    * setFixedSize(w, h) çağrısı "tasarım ölçüsü"dür (30x30 / 90x30 ...) ve korunur.
    * Yazı bu genişliğe sığmıyorsa düğme gerektiği kadar genişler; yazı kesilmez.
    * Yazı değişirse (setText) otomatik yeniden ölçülür ve üst bar yeniden dizilir.
    * İlk gösterimde, açıklaması yoksa Türkçe açıklama sözlüğünden doldurulur.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dw = None
        self._dh = None
        self._auto_style = True
        self._busy = False
        self._raw_sheet = ""
        self._tip_done = False
        install()

    # ---- ölçü ----
    def setFixedSize(self, *a):
        if len(a) == 1:
            w, h = a[0].width(), a[0].height()
        else:
            w, h = a
        self._dw, self._dh = int(w), int(h)
        if getattr(self, "_raw_sheet", None):
            self._push_sheet()
        else:
            self._refit()

    def setFixedWidth(self, w):
        self._dw = int(w)
        self._refit()

    def setFixedHeight(self, h):
        self._dh = int(h)
        QPushButton.setFixedHeight(self, int(h))
        self._refit()

    def setText(self, text):
        super().setText(text)
        self._refit()

    def setIcon(self, icon):
        super().setIcon(icon)
        self._refit()

    def setStyleSheet(self, sheet):
        self._auto_style = False
        self._raw_sheet = sheet
        self._push_sheet()

    def _push_sheet(self):
        """Kare/ikon boyutlu (<=44 px) düğmede yan dolguyu daraltır; tek harf sığsın."""
        sheet = getattr(self, "_raw_sheet", "") or ""
        if self._dw is not None and self._dw <= 44:
            sheet = sheet.replace("padding: 2px 8px", "padding: 2px")
        if sheet != QPushButton.styleSheet(self):
            QPushButton.setStyleSheet(self, sheet)
        self._refit()

    # ---- hesap ----
    def _need_width(self):
        t = self.text()
        if not t:
            return 0
        ss = self.styleSheet()
        m = _RE_FONT.search(ss)
        px = int(m.group(1)) if m else 14
        f = QFont(self.font())
        f.setPixelSize(px)
        f.setBold(bool(_RE_BOLD.search(ss)) if ss else False)
        fm = QFontMetrics(f)
        adv = max(fm.horizontalAdvance(line) for line in t.split("\n"))
        mb = _RE_BORDER.search(ss)
        border = int(mb.group(1)) if mb else 2
        icon = 0
        if not self.icon().isNull():
            icon = self.iconSize().width() + 4
        return adv + icon + 2 * border + _horiz_padding(ss) + 4

    def _refit(self):
        if self._busy or self._dw is None:
            return
        self._busy = True
        try:
            w = self._dw
            need = self._need_width()
            if need > w:
                w = min(need, MAX_BTN_W)
            if self._dh is None:
                QPushButton.setFixedWidth(self, w)
            else:
                QPushButton.setFixedSize(self, w, self._dh)
            self.updateGeometry()
        finally:
            self._busy = False

    def _ancestor_styled(self):
        """Üst widget'lardan biri düğme için özel kural yazmışsa (QPushButton {...} / #ad {...}) ona dokunma."""
        name = self.objectName()
        p = self.parentWidget()
        guard = 0
        while p is not None and guard < 16:
            ss = p.styleSheet()
            if ss and ("QPushButton" in ss or "QAbstractButton" in ss or (name and "#" + name in ss)):
                return True
            p = p.parentWidget()
            guard += 1
        return False

    def _default_style(self):
        """Hiç stil verilmemiş düğmeye ortak tasarımı uygular (özel stilli üst widget yoksa)."""
        if not self._auto_style or self.styleSheet():
            return
        self._auto_style = False
        if self._ancestor_styled():
            return
        mini = (not self.text()) or (self._dw is not None and self._dw <= 44)
        self.setStyleSheet(style_mini() if mini else style_text())

    def showEvent(self, e):
        super().showEvent(e)
        if not self._tip_done:
            self._tip_done = True
            self._default_style()
            _tipi_uygula(self)
            self._refit()


class KToolButton(QToolButton):
    """QToolButton + Türkçe açıklama desteği (stil her yerde kendi sabitinden gelir)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tip_done = False
        install()

    def showEvent(self, e):
        super().showEvent(e)
        if not self._tip_done:
            self._tip_done = True
            _tipi_uygula(self)


def make_button(text="", w=None, h=BTN_H, tip_text=None, style=None, parent=None):
    """Kısayol: ölçülü, stilli, açıklamalı düğme üretir."""
    b = KButton(text, parent) if parent is not None else KButton(text)
    if style:
        b.setStyleSheet(style)
    if w is None:
        w = BTN_W if text and len(text) > 2 else ICON_W
    b.setFixedSize(w, h)
    if tip_text:
        b.setToolTip(tip_text)
    return b


# ===========================================================================
# 5) ToolbarLayout — iki taraflı, sığmayınca satır atlayan üst bar
# ===========================================================================
class ToolbarLayout(QLayout):
    """QHBoxLayout yerine geçer (addWidget / addStretch / addSpacing aynı).

    İlk 'addStretch()' çağrısından ÖNCEKİ öğeler SOL grup, SONRAKİLER SAĞ grup olur.
    * Hepsi sığıyorsa tek satır: sol grup solda, sağ grup (Export + editör adı) sağ köşede.
    * Sığmıyorsa sağ grup alt satıra düşer ve sağa yaslı kalır.
    * Sol grubun kendisi de sığmazsa satır atlar.
    Üst bar yüksekliği satır sayısına göre otomatik uzar (QLayout.heightForWidth).
    """
    ROW_GAP = 4

    def __init__(self, parent=None, margins=(10, 5, 10, 5), spacing=10):
        if parent is not None:
            super().__init__(parent)
        else:
            super().__init__()
        self._items = []          # [(QLayoutItem, taraf)]  taraf: 0 sol, 1 sağ
        self._split = False
        self._cur_h = BTN_H
        super().setContentsMargins(*margins)
        super().setSpacing(spacing)

    # ---- QHBoxLayout uyumlu API ----
    def addItem(self, item):
        sp = item.spacerItem()
        if sp is not None:
            pol = sp.sizePolicy().horizontalPolicy()
            if pol in (QSizePolicy.Expanding, QSizePolicy.MinimumExpanding):
                self._split = True
                return
        self._items.append((item, 1 if self._split else 0))
        self.invalidate()

    def addWidget(self, widget, stretch=0, alignment=Qt.Alignment()):
        QLayout.addWidget(self, widget)

    def addStretch(self, stretch=0):
        self._split = True

    def addSpacing(self, size):
        self.addItem(QSpacerItem(int(size), 0, QSizePolicy.Fixed, QSizePolicy.Minimum))

    def addSpacerItem(self, item):
        self.addItem(item)

    def addLayout(self, layout, stretch=0):
        self.addChildLayout(layout)
        self.addItem(layout)

    def insertWidget(self, index, widget, stretch=0, alignment=Qt.Alignment()):
        QLayout.addWidget(self, widget)
        it, side = self._items.pop()
        index = max(0, min(index, len(self._items)))
        self._items.insert(index, (it, side))
        self.invalidate()

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i][0] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        if 0 <= i < len(self._items):
            it = self._items.pop(i)[0]
            self.invalidate()
            return it
        return None

    def expandingDirections(self):
        return Qt.Horizontal

    def hasHeightForWidth(self):
        return True

    # ---- ölçüler ----
    def _sp(self):
        s = self.spacing()
        return 10 if s < 0 else s

    def _vm(self):
        """Dikey kenar boşlukları: üst çubuğun 2 px alt çizgisi 40 px toplam yüksekliğin içinde kalsın."""
        m = self.contentsMargins()
        return max(0, m.top() - 1), max(0, m.bottom() - 1)

    @staticmethod
    def _is_gap(item):
        return item.spacerItem() is not None

    def _size(self, item):
        sz = item.sizeHint().expandedTo(item.minimumSize())
        mx = item.maximumSize()
        return QSize(min(sz.width(), mx.width()), min(sz.height(), mx.height()))

    def _pack(self, entries, inner):
        """Sığdığı kadar satıra dizer.  entries: [(item, QSize)] -> [[(item,w,h),...], ...]"""
        sp = self._sp()
        rows, cur, x = [], [], 0
        for item, sz in entries:
            w, h = sz.width(), sz.height()
            if self._is_gap(item):
                if cur:
                    cur.append((item, w, h))
                    x += w
                continue
            add = (sp if cur and not self._is_gap(cur[-1][0]) else 0) + w
            if cur and x + add > inner:
                while cur and self._is_gap(cur[-1][0]):
                    cur.pop()
                rows.append(cur)
                cur, x, add = [], 0, w
            cur.append((item, w, h))
            x += add
        while cur and self._is_gap(cur[-1][0]):
            cur.pop()
        if cur:
            rows.append(cur)
        return rows

    def _row_w(self, row):
        sp = self._sp()
        x, prev_widget = 0, False
        for item, w, _h in row:
            if self._is_gap(item):
                x += w
                prev_widget = False
            else:
                x += (sp if prev_widget else 0) + w
                prev_widget = True
        return x

    def _plan(self, width):
        m = self.contentsMargins()
        inner = max(1, width - m.left() - m.right())
        left, right = [], []
        for item, side in self._items:
            if item.isEmpty() and not self._is_gap(item):
                continue
            (right if side else left).append((item, self._size(item)))
        rows_l = self._pack(left, inner)
        rows_r = self._pack(right, inner)
        rows = [("L", r) for r in rows_l]
        if rows_r:
            sp = self._sp()
            can_share = (len(rows_r) == 1 and rows_l and
                         self._row_w(rows_l[-1]) + 2 * sp + self._row_w(rows_r[0]) <= inner)
            if can_share:
                rows[-1] = ("LR", rows_l[-1], rows_r[0])
            else:
                rows += [("R", r) for r in rows_r]
        return rows, inner

    def _row_h(self, parts):
        h = 0
        for part in parts:
            for _it, _w, hh in part:
                h = max(h, hh)
        return max(h, BTN_H)

    def _total_height(self, width):
        rows, _ = self._plan(width)
        vt, vb = self._vm()
        if not rows:
            return vt + BTN_H + vb
        hs = [self._row_h(r[1:]) for r in rows]
        return vt + sum(hs) + self.ROW_GAP * (len(hs) - 1) + vb

    def heightForWidth(self, w):
        return self._total_height(w)

    def minimumHeightForWidth(self, w):
        return self._total_height(w)

    def sizeHint(self):
        m = self.contentsMargins()
        sp = self._sp()
        w = m.left() + m.right()
        first = True
        for item, _side in self._items:
            if item.isEmpty() and not self._is_gap(item):
                continue
            sz = self._size(item)
            w += sz.width() + (0 if self._is_gap(item) or first else sp)
            first = False
        vt, vb = self._vm()
        return QSize(w, vt + BTN_H + vb)

    def minimumSize(self):
        m = self.contentsMargins()
        wmax = 0
        for item, _side in self._items:
            if item.isEmpty() and not self._is_gap(item):
                continue
            wmax = max(wmax, self._size(item).width())
        vt, vb = self._vm()
        return QSize(wmax + m.left() + m.right(), vt + BTN_H + vb)

    # ---- yerleşim ----
    def setGeometry(self, rect):
        super().setGeometry(rect)
        rows, inner = self._plan(rect.width())
        m = self.contentsMargins()
        sp = self._sp()
        y = rect.y() + self._vm()[0]
        x0 = rect.x() + m.left()

        def place(row, start_x):
            x = start_x
            prev_widget = False
            for item, w, h in row:
                if self._is_gap(item):
                    x += w
                    prev_widget = False
                    continue
                if prev_widget:
                    x += sp
                rh = self._cur_h
                item.setGeometry(QRect(x, y + (rh - h) // 2, w, h))
                x += w
                prev_widget = True

        for r in rows:
            kind = r[0]
            self._cur_h = self._row_h(r[1:])
            if kind == "L":
                place(r[1], x0)
            elif kind == "R":
                place(r[1], x0 + inner - self._row_w(r[1]))
            else:
                place(r[1], x0)
                place(r[2], x0 + inner - self._row_w(r[2]))
            y += self._cur_h + self.ROW_GAP

    def __del__(self):
        try:
            while self._items:
                self._items.pop()
        except Exception:
            pass


def prepare_toolbar(frame):
    """Üst bar çerçevesini (QFrame/QWidget) esnek yükseklikli yapar.

    Eskiden:  frame.setFixedHeight(40)   ->   Şimdi:  kui.prepare_toolbar(frame)
    Tek satırda 40 px'tir (tasarım aynı); pencere daralınca satır sayısı kadar uzar.
    """
    frame.setMinimumHeight(TOOLBAR_H)
    frame.setMaximumHeight(16777215)
    pol = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
    pol.setHeightForWidth(True)
    frame.setSizePolicy(pol)
    return frame


def apply(window):
    """İsteğe bağlı: pencerenin bütün düğmelerine açıklama ve ortak stil bakar (eski düğmeler için)."""
    from PyQt5.QtWidgets import QAbstractButton
    for b in window.findChildren(QAbstractButton):
        if not b.toolTip():
            _tipi_uygula(b)


# ===========================================================================
# 6) Ortak yardımcılar (hata günlüğü, güvenli dosya yazımı, güvenli tar, bekleme)
# ===========================================================================
def log_exc(exc=None):
    """Sessizce yutulan hataları görünür yapar.  Normalde sessizdir; KAVRAM_DEBUG=1 ile stderr'e yazar."""
    if not os.environ.get("KAVRAM_DEBUG"):
        return
    import traceback
    fr = traceback.extract_stack(limit=2)[0]
    print(f"[kavram] yutulan hata ({os.path.basename(fr.filename)}:{fr.lineno}): {exc!r}", file=sys.stderr)


def atomic_write_text(path, text, encoding="utf-8"):
    """Önce geçici dosyaya yazar, sonra yerine taşır: çökme olsa bile eski dosya bozulmaz."""
    path = os.fspath(path)
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    tmp = f"{path}.tmp{os.getpid()}"
    try:
        with open(tmp, "w", encoding=encoding) as f:
            f.write(text)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path, obj, **kw):
    """json.dump yerine geçer (aynı anahtar sözcükler: indent, ensure_ascii, sort_keys ...)."""
    import json
    atomic_write_text(path, json.dumps(obj, **kw))


def safe_extract_tar(tar, path="."):
    """Tar arşivini güvenle açar: dış dizine çıkma, mutlak yol, symlink/hardlink ve aygıt dosyası reddedilir."""
    base = os.path.realpath(path)
    members = []
    for m in tar.getmembers():
        if m.issym() or m.islnk() or m.isdev():
            raise ValueError(f"Güvenlik ihlali: arşivde izin verilmeyen öğe türü ({m.name})")
        if os.path.isabs(m.name):
            raise ValueError(f"Güvenlik ihlali: mutlak yol ({m.name})")
        target = os.path.realpath(os.path.join(base, m.name))
        if os.path.commonpath([base, target]) != base:
            raise ValueError(f"Güvenlik ihlali: arşiv dış dizine yazmaya çalışıyor ({m.name})")
        members.append(m)
    tar.extractall(base, members=members)


def ui_wait(seconds):
    """time.sleep gibi bekler ama arayüz donmaz (pencere çizilmeye devam eder, tıklamalar yok sayılır)."""
    from PyQt5.QtCore import QEventLoop, QTimer
    app = QApplication.instance()
    if app is None:
        import time
        time.sleep(seconds)
        return
    loop = QEventLoop()
    QTimer.singleShot(max(1, int(seconds * 1000)), loop.quit)
    loop.exec_(QEventLoop.ExcludeUserInputEvents)


def shm_dir():
    """Önizleme için paylaşımlı bellek klasörü (yoksa geçici klasör)."""
    import tempfile
    return "/dev/shm" if os.path.isdir("/dev/shm") else tempfile.gettempdir()
