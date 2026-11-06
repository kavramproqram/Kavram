#!/bin/bash
# KAVRAM — macOS BAŞLATICI: Finder'da bu dosyaya çift tıklayın (Terminal açılır).
# macOS'a özel kodları (*_mac.py) kullanır, paketini (dist/Kavram.app + .dmg) oluşturur ve başlatır.
cd "$(dirname "$0")" || exit 1
export KAVRAM_OS=mac
bash kurulum_mac.txt
read -n 1 -s -r -p "Kapatmak için bir tuşa basın..."
