#!/bin/bash

# Hata durumunda script'i durdur
set -e

# Çıktı klasörünü ve dosya adını tanımla
APP_NAME="Kavram"
SPEC_FILE="Kavram_appimage.spec"
APPIMAGE_OUTPUT="${APP_NAME}-x86_64.AppImage"
DIST_DIR="dist/${APP_NAME}"

echo "--- 1. PyInstaller Kurulum Kontrolü ve Derleme ---"
PYINSTALLER_BIN="./venv/bin/pyinstaller"

if [ ! -f "$PYINSTALLER_BIN" ]; then
    echo "HATA: PyInstaller sanal ortamda bulunamadi! venv/bin/ klasorunu kontrol edin."
    exit 1
fi

echo "--- 1. PyInstaller ($PYINSTALLER_BIN) ile tek-klasör derlemesi basliyor (dist/${APP_NAME})... ---"
# Eski dist/ build'i sil (Temizlik)
rm -rf dist/${APP_NAME} build
# PyInstaller'ı çalıştır
"$PYINSTALLER_BIN" "$SPEC_FILE"


echo "--- 2. Gerekli AppImage araçlari indiriliyor... ---"
# linuxdeploy ve Qt eklentisini indir (eğer inmemişse)
LINUXDEPLOY_BIN="linuxdeploy-x86_64.AppImage"
QT_PLUGIN_BIN="linuxdeploy-plugin-qt-x86_64.AppImage"

# wget komutlarını kontrol etmeden sadece chmod ile devam ediyorum, dosyalar zaten inmiş.
chmod +x "${LINUXDEPLOY_BIN}"
chmod +x "${QT_PLUGIN_BIN}"

echo "--- 3. linuxdeploy ile AppImage olusturuluyor (Kritik Qt Path Düzeltmesi)... ---"

# linuxdeploy için zorunlu olan .desktop ve .png dosyalarının dist klasörü içine kopyalanması
cp "${APP_NAME}.desktop" "${DIST_DIR}/"
cp "${APP_NAME}.png" "${DIST_DIR}/"

# --- KRİTİK QT ORTAM DEĞİŞKENLERİ ---
# linuxdeploy-plugin-qt'nin Qt kütüphanelerini bulmasını sağlamak için path'leri ayarla.
# Linux Mint/Ubuntu'da Qt 5 kütüphanelerinin standart konumu.
QT_LIB_PATH="/usr/lib/x86_64-linux-gnu"
QT_PLUGIN_PATH="${QT_LIB_PATH}/qt5/plugins"

# linuxdeploy çalıştırma komutu (Ortam değişkenleri ile)
export APPIMAGE_EXTRACT_AND_RUN=1
export VERSION="1.0"
export LD_LIBRARY_PATH="${QT_LIB_PATH}:${LD_LIBRARY_PATH}" # Kütüphane arama yolunu ekle
export QT_PLUGIN_PATH="${QT_PLUGIN_PATH}" # Qt eklentilerini bulma yolunu ekle

./"${LINUXDEPLOY_BIN}" \
  --appdir "${DIST_DIR}" \
  --executable "${DIST_DIR}/${APP_NAME}/Kavram" \
  --desktop-file "${DIST_DIR}/${APP_NAME}.desktop" \
  --icon-file "${APP_NAME}.png" \
  --plugin qt \
  --output appimage

# AppImage dosyasını son adına göre yeniden adlandır
if [ -f "Kavram.AppImage" ]; then
    mv Kavram.AppImage "${APPIMAGE_OUTPUT}"
    echo "--- BAŞARILI: ${APPIMAGE_OUTPUT} oluşturuldu! ---"
else
    echo "HATA: AppImage dosyası Kavram.AppImage adıyla bulunamadı. Lütfen üstteki hata mesajlarını kontrol edin."
    exit 1
fi

# Temizlik (İsteğe bağlı, build ve dist klasörlerini silmek için)
# rm -rf build
# rm -rf dist

