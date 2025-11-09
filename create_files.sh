#!/bin/bash

# Gerekli paket listesi dosyalarını oluşturma
echo "requirements.txt dosyası oluşturuluyor..."
touch requirements.txt

echo "lua_packages.txt dosyası oluşturuluyor..."
touch lua_packages.txt

echo "vcpkg.json dosyası oluşturuluyor..."
touch vcpkg.json

# Ana kurulum betiğini oluşturma ve içine komutları yazma
echo "install.sh dosyası oluşturuluyor ve kurulum komutları yazılıyor..."
cat << 'EOF' > install.sh
#!/bin/bash

echo "Python paketleri kuruluyor..."
pip install -r requirements.txt

echo "Lua paketleri kuruluyor..."
while read package; do
  luarocks install "$package"
done < lua_packages.txt

echo "C++ paketleri kuruluyor..."
vcpkg install

echo "Tüm paketler başarıyla kuruldu."
EOF

# Betiklere çalıştırma izni verme
echo "Oluşturulan betiklere çalıştırma izni veriliyor..."
chmod +x install.sh
chmod +x create_files.sh

echo "Dosyalar başarıyla oluşturuldu. Şimdi paket listelerini bu dosyalara ekleyebilirsin:"
echo "- requirements.txt"
echo "- lua_packages.txt"
echo "- vcpkg.json"
echo ""
echo "Ardından 'sh install.sh' komutuyla tüm paketlerini kurabilirsin."
