"""Düğmelerin Türkçe açıklamaları. Fare düğmenin üzerine geldiğinde siyah zeminli,
beyaz yazılı ipucu olarak görünür."""
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QToolTip

from . import config

TIPS = {
    # Üst araç çubuğu
    "file": "Dosya: Kayıtlı bir .copya projesini açar.",
    "save": "Kaydet: Projeyi son kullanılan dosyaya kaydeder. Dosya yoksa 'Farklı kaydet' penceresi açılır.",
    "add": "Ekle: Boş bir metin notu oluşturur.",
    "gallery": "Galeri: Resim ve metin dosyalarından galeri notu oluşturur. Bir galeri açıkken o galeriye öğe ekler.",
    "belge": "Belge: PDF, Word, Excel, PowerPoint, PNF ve resim dosyalarını sayfalı belge olarak açar.",
    "nav": "Sayfa listesi: Açık galeri veya belgede istediğin sayfaya geçmeni sağlar.",
    "auto_scroll": "Otomatik kaydırma (okuma modu): Açık notu seçilen hızda kendiliğinden kaydırır. Tekrar basınca durur.",
    "speed": "Kaydırma hızı: Otomatik kaydırma hızını seçer.",
    "doc_size": "Belge boyutu: Açık belgenin sayfa genişliğini yüzde olarak ayarlar.",
    "toolbar_delete": "Sil: Açık notu kalıcı olarak siler.",
    "toolbar_min": f"Küçült: Açık notu kapatıp ızgaraya döner. Kısayol: {config.TOGGLE_EXPAND_SHORTCUT}",
    "toolbar_copy": "Kopyala: Açık notun içeriğini panoya kopyalar.",
    "export": "Dışa aktar: Tüm projeyi yeni bir .copya dosyası olarak kaydeder.",
    "switcher": "Copy: Kavram program geçiş menüsünü açar.",

    # Not kartı
    "note_title": "Not başlığı: Notun adını buraya yazabilirsin.",
    "note_copy": "Kopyala: Notu panoya kopyalar. Metin notları düz metin olarak, galeri ve belgeler dosya olarak kopyalanır.",
    "note_max": "Büyüt: Notu tam ekranda açar.",
    "note_delete": "Sil: Bu notu kalıcı olarak siler.",

    # Galeri ve belge satırları
    "item_delete": "Öğeyi sil: Bu resmi veya sayfayı listeden çıkarır.",
    "item_up": "Yukarı taşı: Öğeyi bir sıra yukarı alır.",
    "item_down": "Aşağı taşı: Öğeyi bir sıra aşağı indirer.",
    "item_num": "Sıra: Tıklayınca öğenin sırasını doğrudan seçebilirsin.",

    # Belge sayfası
    "doc_page": "Sayfa numarası: Belgenin hangi sayfada olduğunu gösterir.",
}


def set_tip(widget, key: str) -> None:
    widget.setToolTip(TIPS[key])


def install_tooltip_palette() -> None:
    """Tüm ipuçlarını siyah zeminli, beyaz yazılı yapar. Diğer pencereleri etkilemez."""
    palette = QToolTip.palette()
    palette.setColor(QPalette.ToolTipBase, QColor("#000000"))
    palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
    QToolTip.setPalette(palette)
