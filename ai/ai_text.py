# Kavram AI Editörü — metin normalleştirme (Qt gerektirmez)
# Kavram 2.2.2 | GNU GPL v3 veya üstü (ayrıntı: ai.py başlığı ve /Kavram/License/GPLv3.txt)

import unicodedata

# Türkçe harfler: ı / İ / I hepsi "i" olarak katlanır ("kışla" → "kisla").
_TR_FOLD = str.maketrans({"ı": "i", "İ": "i", "I": "i"})


def normalize_text(s: str) -> str:
    """Arama/eşleştirme için metni sadeleştirir: küçük harf, aksansız, tek boşluklu.

    Eski sürüm ASCII dışındaki her karakteri silerdi (ı harfi kayboluyor,
    Kiril/Arapça kelimelerin anahtarı boş kalıyordu). Artık yalnızca
    birleşik aksan işaretleri atılır.
    """
    if not s:
        return ""
    s = s.translate(_TR_FOLD).lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return " ".join(s.split())
