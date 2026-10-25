#!/usr/bin/env bash
# =====================================================================================
# KAVRAM — tek komutla KURULUM + PAKETLEME
#
#   Kullanım (kavram klasöründe):
#       bash paketle.sh              sistem paketlerini kurar, venv + Python kütüphanelerini hazırlar,
#                                    C++ motorlarını derler, PyInstaller ile paketi üretir (paket/)
#       bash paketle.sh --kur        ek olarak paketi ~/.local/share/kavram/app altına kurar,
#                                    ~/.local/bin/kavram komutunu ve uygulama menü girdisini ekler
#       bash paketle.sh --sadece-paket
#                                    kurulum adımlarını atlar (venv ve motorlar hazırsa)
#
#   Çıktılar:
#       paket/kavram/                          çalıştırılabilir paket dizini (paket/kavram/kavram)
#       paket/kavram-<sürüm>-linux-<mimari>.tar.gz   dağıtım arşivi (+ .sha256)
#
#   Desteklenen kurulum yöneticileri: apt (Debian/Ubuntu/Mint), pacman (Arch/Manjaro/EndeavourOS).
#   Sistem paketleri sudo ister. Paket, desteklenecek EN ESKİ dağıtımda derlenmelidir.
# =====================================================================================
set -Eeuo pipefail
cd "$(dirname "$0")"

KURULUM=0
SADECE_PAKET=0
for arg in "$@"; do
  case "$arg" in
    --kur) KURULUM=1 ;;
    --sadece-paket) SADECE_PAKET=1 ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "Bilinmeyen seçenek: $arg"; exit 2 ;;
  esac
done

adim() { echo; echo "==> $*"; }
uyari() { echo "UYARI: $*" >&2; }
hata() { echo "HATA: $*" >&2; exit 1; }

[ -f kavram.py ] || hata "Bu betiği kavram klasöründe (kavram.py'nin yanında) çalıştırın."
[ -f kavram.spec ] || hata "kavram.spec bulunamadı."
[ -f rthook_kavram.py ] || hata "rthook_kavram.py bulunamadı."

SURUM=$(grep -m1 -oE 'Kavram [0-9]+\.[0-9]+\.[0-9]+' kavram.py | awk '{print $2}' || true)
SURUM=${SURUM:-0.0.0}
MIMARI=$(uname -m)
export KAVRAM_MARCH="${KAVRAM_MARCH:-x86-64}"     # motorlar dağıtımlar arası taşınabilir derlensin

# ------------------------------------------------------------------ dağıtım tespiti
if command -v apt-get >/dev/null 2>&1; then
  YONETICI=apt
elif command -v pacman >/dev/null 2>&1; then
  YONETICI=pacman
else
  YONETICI=yok
fi

# derleme.txt satırlarından paket listeleri (tekilleştirilmiş)
listele() { cat */derleme.txt 2>/dev/null | sed -n "s/^# $1: *//p" | tr ' ' '\n' | sed '/^$/d' | sort -u | tr '\n' ' '; }

if [ "$SADECE_PAKET" -eq 0 ]; then
  # ---------------------------------------------------------------- 1) sistem paketleri
  adim "Sistem paketleri kuruluyor ($YONETICI)"
  case "$YONETICI" in
    apt)
      sudo apt-get update
      sudo apt-get install -y $(listele apt) || hata "apt paketleri kurulamadı"
      for p in $(listele apt-opsiyonel); do
        sudo apt-get install -y "$p" || uyari "opsiyonel paket kurulamadı: $p"
      done ;;
    pacman)
      sudo pacman -S --needed --noconfirm $(listele pacman) || hata "pacman paketleri kurulamadı"
      for p in $(listele pacman-opsiyonel); do
        sudo pacman -S --needed --noconfirm "$p" || uyari "opsiyonel paket kurulamadı: $p"
      done ;;
    *) uyari "apt/pacman bulunamadı; sistem paketleri atlandı (gerekli geliştirme araçlarını elle kurun)." ;;
  esac

  # ---------------------------------------------------------------- 2) venv + Python kütüphaneleri
  adim "Sanal ortam (venv) ve Python kütüphaneleri"
  [ -x venv/bin/python ] || python3 -m venv venv || hata "venv oluşturulamadı"
  ./venv/bin/pip install --upgrade pip wheel || hata "pip güncellenemedi"
  PIP=$(listele pip)
  # shellcheck disable=SC2086
  ./venv/bin/pip install $PIP pyinstaller || hata "Python kütüphaneleri kurulamadı"
  if ./venv/bin/python -c "import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)"; then
    ./venv/bin/pip install audioop-lts || true
  fi

  # ---------------------------------------------------------------- 3) C++ motorları
  adim "C++ motorları derleniyor (KAVRAM_MARCH=$KAVRAM_MARCH)"
  HATALI=""
  for d in */; do
    d=${d%/}
    [ -f "$d/derleme.txt" ] || continue
    echo "--- $d"
    ( cd "$d" && bash derleme.txt ) || HATALI="$HATALI $d"
  done
  if [ -n "$HATALI" ]; then
    uyari "Şu programların C++ derlemesi başarısız oldu:$HATALI (ilgili özellikler paketsiz çalışır)."
  fi
fi

[ -x venv/bin/pyinstaller ] || hata "PyInstaller yok. Önce 'bash paketle.sh' (sadece-paket olmadan) çalıştırın."

# ------------------------------------------------------------------ 4) PyInstaller ile paketleme
adim "Paket üretiliyor (PyInstaller)"
rm -rf paket build_tmp
./venv/bin/pyinstaller --noconfirm --clean --distpath paket --workpath build_tmp kavram.spec \
  || hata "PyInstaller başarısız"
[ -x paket/kavram/kavram ] || hata "paket/kavram/kavram oluşmadı"

# Motor ve çalıştırılabilir dosyalarının çalıştırma izni (kopyalamada kaybolmuş olabilir)
for f in paket/kavram/_internal/*/media_recorder paket/kavram/_internal/*/rec_engine; do
  [ -f "$f" ] && chmod +x "$f"
done

# Eksik motor raporu
for f in sound/sound_engine.so media/media_engine.so media/media_recorder filter/filter_engine.so \
         converter/converter_engine.so rec/rec_engine file_manager/libfile_engine.so file_manager/libview_engine.so; do
  [ -e "$f" ] || uyari "Motor yok, paketsiz kalır: $f"
done

# ------------------------------------------------------------------ 5) dağıtım arşivi
adim "Dağıtım arşivi hazırlanıyor"
ARSIV="kavram-${SURUM}-linux-${MIMARI}.tar.gz"
( cd paket && tar -czf "$ARSIV" kavram && sha256sum "$ARSIV" > "$ARSIV.sha256" )
echo "Arşiv: paket/$ARSIV"

# ------------------------------------------------------------------ 6) isteğe bağlı kullanıcı kurulumu
if [ "$KURULUM" -eq 1 ]; then
  adim "Kullanıcı dizinine kuruluyor (~/.local)"
  HEDEF="$HOME/.local/share/kavram/app"
  rm -rf "$HEDEF"
  mkdir -p "$(dirname "$HEDEF")" "$HOME/.local/bin" "$HOME/.local/share/applications"
  cp -a paket/kavram "$HEDEF"
  ln -sfn "$HEDEF/kavram" "$HOME/.local/bin/kavram"
  cat > "$HOME/.local/share/applications/kavram.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Kavram
Comment=Kavram $SURUM
Exec=$HEDEF/kavram
Icon=$HEDEF/_internal/ikon/kavram.png
Terminal=false
Categories=AudioVideo;Graphics;Utility;
EOF
  command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" || true
  echo "Kuruldu: $HEDEF"
  echo "Başlatma: kavram   (veya uygulama menüsünden 'Kavram')"
  case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) uyari "~/.local/bin PATH içinde değil; ekleyin: export PATH=\"\$HOME/.local/bin:\$PATH\"" ;; esac
fi

adim "Bitti (Kavram $SURUM, $MIMARI)"
echo "Paket dizini: paket/kavram/kavram"
echo "Arşiv:        paket/$ARSIV"
