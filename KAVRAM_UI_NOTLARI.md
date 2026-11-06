# Kavram — ortak arayüz dili ve düzeltmeler

## 1. Ortak arayüz dili: `kavram_ui.py` (yeni, kök klasörde)
Bütün editörler (text, sound, drawing, media, rec, sphere, ai, filter, converter, copy, file_manager)
aynı renkleri, aynı düğme tasarımını ve aynı üst barı bu tek dosyadan kullanır.

* **Tasarım korunur:** kare düğme 30x30, yazılı düğme 90x30, 8 px köşe, `#555` çerçeve, `#444` üzerine gelince,
  `#666` basılınca. Aynı tasarım aşağıdaki durumlarda da vardır: seçili/açık, devre dışı, koyu.
* **Yazı asla kesilmez:** `KButton`, verilen ölçüyü (`setFixedSize(90, 30)`) "tasarım ölçüsü" sayar. Yazı sığmıyorsa
  düğme gerektiği kadar genişler; yazı sonradan değişirse (Play/Stop, 12 -> 100) otomatik yeniden ölçülür.
* **İki taraflı, esnek üst bar (`ToolbarLayout`):** soldaki grup = diğer düğmeler, sağdaki grup = Export + editör adı.
  Pencere daralınca sağ köşe düğmeleri alt satıra düşer (sağa yaslı kalır), gerekirse sol grup da satır atlar;
  üst bar yüksekliği buna göre uzar (tek satırda 40 px, yani eski görünüm aynı). Pencere artık eskisi gibi
  "üst bar yüzünden" küçülmez durumda değildir.
* **Açıklamalar:** her düğmenin üstünde fare 0,6 saniye durunca **siyah zemin / beyaz yazı** ile Türkçe açıklama çıkar.
  Açıklama metinleri `kavram_ui.py` içinde `TIPS_ATTR` (düğmenin öznitelik adı) ve `TIPS_TEXT` (düğme yazısı)
  sözlüklerindedir; yeni düğme için tek satır eklemek yeter. Kodda elle verilmiş açıklama varsa o öncelikli olur.
* Ortak yardımcılar: `style_text/mini/active/toggle/dark/disabled/combo/menu/input`, `safe_extract_tar`,
  `atomic_write_json/text`, `ui_wait`, `log_exc`, `shm_dir`.

Yeni düğme eklerken: `from kavram_ui import KButton` -> `b = KButton("Ad"); b.setFixedSize(90, 30)`.
Üst bar için: `kui.prepare_toolbar(frame)` ve `kui.ToolbarLayout(frame)` (`QHBoxLayout` yerine; `addStretch()` sol/sağ ayırıcıdır).

Hata ayıklama: `KAVRAM_UI_EKSIK=1` açıklaması olmayan düğmeleri yazar; `KAVRAM_DEBUG=1` sessizce yutulan hataları yazar.

## 2. C dosyaları tek dosya
`file_manager/file_engine.c` artık eski `view_engine.c`'yi de içerir; tek kütüphane: `libfile_engine.so`.
`view_engine.c` silindi. `file_manager.py`, `derleme.txt`, `kavram.spec`, `paketle.sh` buna göre güncellendi.

## 3. Hata ve güvenlik düzeltmeleri
* `sphere.py` `.kitap` açma: tar çıkarma yol kontrolü (`startswith` ön ek hatası), symlink/hardlink ve mutlak yol
  engellenmiyordu -> `kui.safe_extract_tar` (hepsini reddeder).
* Arayüz thread'inde `time.sleep` (sphere, sphere_kare): pencere donuyordu -> `kui.ui_wait` (donmaz).
* Çıplak `except:` -> `except Exception:` (Ctrl+C / çıkış artık yutulmaz); sessiz `except ...: pass` -> hata günlüğü
  (`KAVRAM_DEBUG=1` ile görünür).
* Ayar/JSON dosyaları artık atomik yazılır (çökme olsa bile dosya bozulmaz) ve her zaman UTF-8 okunur/yazılır.
* `QApplication.desktop()` (kullanımdan kalkmış) -> `primaryScreen()`; `rec.py` içindeki `sf` değişken gölgelemesi giderildi.
* md5 önbellek anahtarı `usedforsecurity=False`; media önizleme dosyası yoluna kullanıcı kimliği eklendi.
* `copy.py` tekrarlanan import bloğu tek bloğa indirildi; ~100 kullanılmayan import ve değişken temizlendi.
* Dosya yöneticisi yer imi düğmesi sabit 90 px kalır (uzun ad ortadan kısaltılır, tamamı açıklamadadır).

## 4. Linux + Windows uyumu (`kavram_platform.py`)
İşletim sistemine özgü her şey tek modülde: kütüphane uzantısı (.so/.dll), süreç başlatma/sonlandırma,
`LD_LIBRARY_PATH`/`PATH`, varsayılan programla açma, pencere öne getirme, veri klasörü, paylaşımlı bellek klasörü.
Kodda `os.killpg`, `start_new_session`, `os.getuid`, `xdg-open` gibi doğrudan çağrılar kalmadı.

### Kurulum betikleri (hepsi: sistem paketleri -> venv -> pip -> C++ derleme -> PAKETLEME (dist/) -> başlat)
| Dosya | Dağıtımlar |
|---|---|
| `kurulum_linux.txt` | Otomatik tanır, aşağıdakilerden uygununu çalıştırır |
| `kurulum_deb.txt` | Debian, Ubuntu, Linux Mint, Pop!_OS, Zorin, elementary |
| `kurulum_arch.txt` | Arch, Manjaro, EndeavourOS, CachyOS, Garuda |
| `kurulum_fedora.txt` | Fedora, Nobara, AlmaLinux, Rocky, CentOS Stream (RPM Fusion otomatik eklenir) |
| `kurulum_opensuse.txt` | openSUSE Tumbleweed / Leap (Packman otomatik eklenir) |
| `kurulum_void.txt` | Void Linux |
| `kurulum_win.txt` (+ `baslat_win.bat`) | Windows 10 / 11 x64 -> `dist\kavram\kavram.exe` + zip |

Paket adları `*/derleme.txt` başlıklarındadır (`# apt:`, `# pacman:`, `# dnf:`, `# zypper:`, `# xbps:`, `# pip:`).
Yeni bir dağıtım eklemek = bir `# <yönetici>:` satırı + `paketle.sh` içinde bir `case` kolu.
Windows motorları: `derleme_win.txt` (MSYS2/MinGW). Linux paket çıktısı da artık `dist/` klasörüne gider.

### Windows'ta durum
Çalışır: text, drawing, sphere, copy, ai, filter, converter, sound, file_manager.
Linux'a özel (şimdilik): media ve rec'in ekran/kamera KAYIT motorları (GStreamer + PipeWire/X11) — programlar açılır,
kayıt başlatılamaz. Alpine ve NixOS desteklenmiyor.

## 5. macOS
`kurulum_mac.txt` (veya Finder'da `baslat_mac.command`): Xcode komut satırı araçları -> Homebrew -> paketler -> venv -> pip ->
C++ motorları (`derleme_mac.txt`, `.dylib`) -> PyInstaller -> `dist/Kavram.app` + `dist/Kavram-<sürüm>-macos-<mimari>.dmg` (+ .zip).
Apple Silicon ve Intel desteklenir; paket, kurulumun yapıldığı mimari için üretilir. Uygulama ad-hoc imzalanır; ilk açılışta
engellenirse: sağ tık -> Aç. Veriler `~/Library/Application Support/kavram` altında tutulur.
`kurulum_linux.txt` macOS'u da tanır ve `kurulum_mac.txt`'yi çalıştırır.

## 6. Üç sistemde çıktılar
| Sistem | Betik | Çıktı |
|---|---|---|
| Linux (deb/arch/fedora/opensuse/void) | `kurulum_linux.txt` | `dist/kavram/kavram` + `.tar.gz` |
| Windows 10/11 | `baslat_win.bat` | `dist\kavram\kavram.exe` + `.zip` |
| macOS 11+ | `kurulum_mac.txt` / `.command` | `dist/Kavram.app` + `.dmg` + `.zip` |
Her paket kendi işletim sisteminde üretilmelidir (PyInstaller çapraz derleme yapmaz).

## 7. İşletim sistemine özel kod dosyaları (yapılandırma sistematiği)
Her program klasöründe üç sürüm vardır:

| Sistem | Dosya | Örnek |
|---|---|---|
| Linux (varsayılan) | `<ad>.py` | `rec/rec.py` |
| Windows | `<ad>_win.py` | `rec/rec_win.py` |
| macOS | `<ad>_mac.py` | `rec/rec_mac.py` |

* **Seçim:** `kavram.py` çalıştığı sistemin dosyasını yükler (yoksa varsayılana döner). `sphere_kare` gibi yan modüller de aynı kuralla seçilir.
* **Paketleme:** `kavram.spec` yalnızca o sistemin dosyalarını pakete koyar (Windows paketinde `*_win.py`, mac'te `*_mac.py`, Linux'ta varsayılanlar).
* **Sonekleri değiştirmek:** tek yer, `kavram_platform.py` içindeki `SONEKLER` tablosu.
* **Deneme:** başka sistemin dosyalarını denemek için `KAVRAM_OS=win` veya `KAVRAM_OS=mac` ortam değişkeni (yalnızca arayüz/kod yükleme denemesi içindir).
* **Başlatıcılar:** `baslat_linux.sh`, `baslat_win.bat`, `baslat_mac.command` — her biri kendi sisteminin kodlarını kullanarak
  paketi (`dist/`) üretir ve Kavram'ı başlatır.
* **`yapilandir.py`:** varsayılan dosyadan `_win` / `_mac` dosyalarını üretir ve o sisteme göre yapılandırır
  (platform sabitleri sabitlenir, çalışmayacak dallar budanır, `.dll`/`.dylib` adları yazılır, başlık eklenir).
  Var olan sistem dosyalarına DOKUNMAZ; `--zorla` hepsini yeniden üretir (elle değişiklikleri siler), `--denetle` eksik/eskimiş olanları listeler.
  Sistem dosyalarını artık elle düzenleyebilirsiniz.

Not: `_win` / `_mac` dosyaları şimdilik varsayılan dosyanın o sisteme göre yapılandırılmış hâlidir (kayıt motorları dışında işlev
farkı yoktur); her sistemin kendine özgü iyileştirmeleri (ör. Windows'ta rec için DXGI kaydı) bu dosyalara eklenecektir.

## 8. Windows / macOS'ta kayıt (rec, media, sound)
Linux'taki C++ kayıt motorları (GStreamer/PipeWire/X11) Windows ve macOS'ta yoktur. `rec_win.py / rec_mac.py` ve
`media_win.py / media_mac.py` bunun yerine ortak `kavram_capture.py` modülünü kullanır:

| Özellik | Linux | Windows | macOS |
|---|---|---|---|
| Ekran kaydı (rec) | rec_engine / FFmpeg x11grab | FFmpeg **gdigrab** | FFmpeg **avfoundation** |
| Mikrofon (rec) | PipeWire / Pulse | FFmpeg **dshow** | FFmpeg **avfoundation** |
| Kamera penceresi (rec, yüzen) | C++ + paylaşımlı bellek | **OpenCV** (DirectShow) | **OpenCV** (AVFoundation) |
| Kamera + mikrofon kaydı (media) | media_recorder (GStreamer) | **OpenCV + PortAudio + FFmpeg** | aynı |
| Yalnızca ses kaydı (media) | media_recorder / PortAudio | **PortAudio** (sounddevice) | aynı |
| Medya motoru (media) | media_engine.so (C++) | **MediaCore** (Python, FFmpeg/FFprobe) | aynı |
| Ses kaydı (sound) | sound_engine (PortAudio) | sound_engine.dll (PortAudio, **MME**) | sound_engine.dylib (CoreAudio) |

Bilinen sınırlar (Windows / macOS): canlı ekran önizlemesi ve ses seviyesi paneli (rec) yoktur; "sistem sesi"
(hoparlör kaydı) için sanal ses aygıtı gerekir (Windows: Stereo Mix / VB-Cable, macOS: BlackHole) — Mikrofon menüsünden seçilebilir.
İzinler: macOS'ta Kamera, Mikrofon ve **Ekran Kaydı** izni istenir (Sistem Ayarları → Gizlilik ve Güvenlik);
Windows'ta Ayarlar → Gizlilik → Kamera / Mikrofon.

**Kayıt denetimi:** kurulumdan sonra  `venv\Scripts\python kayit_testi.py` (Windows) veya `./venv/bin/python kayit_testi.py` (macOS):
aygıtları listeler, 3 sn ekran / 2 sn mikrofon / kamera denemesi yapar ve her adımı OK / HATA olarak yazar.
Kayıt altyapısı eklenen `rec_*` ve `media_*` dosyaları `yapilandir.py --zorla` ile ezilmez (`--cok-zorla` ezer).
