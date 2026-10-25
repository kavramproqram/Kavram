"""Copya sabitleri. Limit, boyut ve kısayol gibi ayarlar yalnızca bu dosyada tutulur."""

# --- Sınırlar ---
MAX_NOTES = 200
MAX_GALLERY_ITEMS = 35
MAX_DOCUMENT_ITEMS = 500          # belge sayfası / resmi üst sınırı
ARCHIVE_MAX_MEMBERS = 10_000      # .copya içindeki en fazla dosya sayısı
ARCHIVE_MAX_BYTES = 4 * 1024**3   # .copya açılınca toplam açılmış boyut üst sınırı

# --- Kaydırma ve belge boyutu ---
SCROLL_SPEEDS = [0.1, 0.3, 0.5, 0.7, 0.9, 1.0, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]
DEFAULT_SCROLL_INDEX = 4
DEFAULT_DOC_SIZE = 15
DOC_SIZE_CHOICES = [0.5] + list(range(1, 21))

# --- Önbellek ve performans ---
RENDER_DPI = 150
PAGE_CACHE_SIZE = 8               # önbellekte tutulan render edilmiş sayfa sayısı
IMAGE_CACHE_SIZE = 8              # önbellekte tutulan tam çözünürlüklü resim sayısı
OPEN_DOCUMENT_CACHE_SIZE = 3      # açık tutulan PDF/belge tanıtıcısı sayısı
TEXT_DEBOUNCE_MS = 300            # metin değişikliğinde HTML üretimini geciktirme süresi

# --- Arayüz ---
NOTE_HEIGHT = 220
CARD_HEIGHT = 180
TOGGLE_EXPAND_SHORTCUT = "Ctrl+Alt+M"   # üst çubuktaki "_" (notu küçült) düğmesi

# --- Dönüştürme ---
OFFICE_TIMEOUT_S = 180

# --- Desteklenen dosya türleri (küçük harf, nokta ile) ---
IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tif', '.tiff')
TEXT_EXTS = ('.txt', '.txr')
PAGED_EXTS = ('.pdf', '.xps', '.epub', '.mobi', '.fb2', '.cbz', '.svg')
OFFICE_EXTS = ('.doc', '.docx', '.odt', '.rtf', '.txt', '.xls', '.xlsx', '.ods',
               '.csv', '.ppt', '.pptx', '.odp')
PNF_EXTS = ('.pnf',)

GALLERY_EXTS = IMAGE_EXTS + TEXT_EXTS
DOCUMENT_EXTS = PAGED_EXTS + OFFICE_EXTS + PNF_EXTS + IMAGE_EXTS
