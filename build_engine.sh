#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  Kavram Audio Engine — Derleme Betiği
#  Kullanım: ./build_engine.sh
#
#  Gereksinimler: g++ (C++17), libm
#  İsteğe bağlı: libfftw3 (daha hızlı FFT için)
# ═══════════════════════════════════════════════════════════════════
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$SCRIPT_DIR/audio_engine.cpp"
OUT="$SCRIPT_DIR/libaudioengine.so"

echo "╔══════════════════════════════════════╗"
echo "║  Kavram Audio Engine - Derleniyor... ║"
echo "╚══════════════════════════════════════╝"

# Derleyici kontrolü
if ! command -v g++ &>/dev/null; then
    echo "[HATA] g++ bulunamadı. Kurmak için: sudo apt install build-essential"
    exit 1
fi

CXX_VERSION=$(g++ -dumpversion | cut -d. -f1)
if [ "$CXX_VERSION" -lt 7 ]; then
    echo "[UYARI] g++ >= 7 önerilir. Mevcut: $CXX_VERSION"
fi

# Derleme bayrakları
CFLAGS="-O3 -march=native -ffast-math -std=c++17"
CFLAGS="$CFLAGS -shared -fPIC"
CFLAGS="$CFLAGS -funroll-loops -ftree-vectorize"
CFLAGS="$CFLAGS -fno-finite-math-only"  # NaN koruması için
LDFLAGS="-lm"

# FFTW3 varsa bağla (opsiyonel - şimdilik built-in FFT kullanıyoruz)
# if pkg-config --exists fftw3f 2>/dev/null; then
#     CFLAGS="$CFLAGS -DUSE_FFTW3"
#     LDFLAGS="$LDFLAGS $(pkg-config --libs fftw3f)"
#     echo "[INFO] FFTW3 bulundu, kullanılıyor."
# fi

echo "Kaynak: $SRC"
echo "Çıktı:  $OUT"
echo ""

g++ $CFLAGS -o "$OUT" "$SRC" $LDFLAGS

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Derleme başarılı: $OUT"
    echo "  Boyut: $(du -sh "$OUT" | cut -f1)"
    # Sembolleri doğrula
    echo ""
    echo "  Dışa aktarılan fonksiyonlar:"
    nm -D "$OUT" | grep ' T ae_' | awk '{print "    " $3}'
else
    echo "[HATA] Derleme başarısız."
    exit 1
fi
