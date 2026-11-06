#!/bin/bash
# KAVRAM — LINUX BAŞLATICI:   bash baslat_linux.sh   (veya terminalde ./baslat_linux.sh)
# Linux'a özel kodları (rec.py, text.py ... varsayılan dosyalar) kullanır; dağıtımınızı tanıyıp sistem paketlerini kurar,
# paketini (dist/kavram/kavram + .tar.gz) oluşturur ve Kavram'ı başlatır.
cd "$(dirname "$0")" || exit 1
if [ "$(uname -s)" != "Linux" ]; then
  echo "Bu betik Linux içindir. macOS için baslat_mac.command, Windows için baslat_win.bat kullanın."; exit 1
fi
export KAVRAM_OS=linux
exec bash kurulum_linux.txt
