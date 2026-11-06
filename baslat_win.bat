@echo off
rem KAVRAM - WINDOWS BASLATICI: bu dosyaya cift tiklayin.
rem Windows icin ozel kodlari (*_win.py) kullanir, paketini (dist\kavram\kavram.exe) olusturur ve baslatir.
cd /d "%~dp0"
set KAVRAM_OS=win
powershell -NoProfile -ExecutionPolicy Bypass -Command "iex ([IO.File]::ReadAllText('kurulum_win.txt',[Text.Encoding]::UTF8))"
pause
