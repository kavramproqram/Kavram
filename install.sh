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
