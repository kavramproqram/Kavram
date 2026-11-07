<div align="center">

<img src="ikon/kavram.png" alt="Kavram" width="120">

# Kavram

**Eğitim ve medya çalışmalarını tek çatı altında toplayan, özgür ve açık kaynaklı arşiv platformu**<br>
**A free and open-source archive platform that brings education and media work under one roof**

![Version](https://img.shields.io/badge/version-2.2.2-blue)
![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![PyQt5](https://img.shields.io/badge/UI-PyQt5-41CD52?logo=qt&logoColor=white)
![Linux](https://img.shields.io/badge/Linux-supported-success?logo=linux&logoColor=white)
![Windows](https://img.shields.io/badge/Windows%2010%2F11-experimental-orange?logo=windows&logoColor=white)
![macOS](https://img.shields.io/badge/macOS%2011%2B-experimental-orange?logo=apple&logoColor=white)
![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)

### [🇹🇷 Türkçe](#türkçe)  ·  [🇬🇧 English](#english)

<img width="3450" height="1880" alt="sh" src="https://github.com/user-attachments/assets/2f3a8157-ee17-4cf0-97b0-be832fb5480b" />

</div>

---

# Türkçe

**Kavram**, eğitim ve medya çalışmalarını tek bir çatı altında toplayan, özgür ve açık kaynak kodlu bir arşiv platformudur.

Metin, çizim, ses, video, ekran kaydı ve notlar gibi farklı araçları tek bir sistem içerisinde sunar. Oluşturduğunuz içerikleri düzenleyebilir, birbirleriyle ilişkilendirebilir ve **SPHERE** üzerinden zihin haritaları oluşturarak şifreli şekilde arşivleyebilirsiniz.

Kavram yalnızca hazır programlardan oluşmaz. İhtiyaçlarınıza göre kendi geliştirdiğiniz programları da sisteme dahil edebilirsiniz. Bu yönüyle Kavram, klasik bir uygulama paketinden çok, kendi çalışma ortamınızı oluşturabileceğiniz bir platform olarak tasarlanmıştır.

**10 entegre program + genişletilebilir program sistemi.**

**Bu sayfada:** [İş akışı](#i̇ş-akışı) · [Programlar](#programlar) · [Kurulum](#kurulum) · [Yapı](#yapı) · [SPHERE](#sphere) · [TEXT](#text) · [DRAWING](#drawing) · [SOUND](#sound) · [AI](#ai) · [MEDIA](#media) · [REC](#rec) · [COPY](#copy) · [FILTER](#filter) · [CONVERTER](#converter)

## İş Akışı

1. **Dosya Üretimi:** Esas programlarda gerekli dosyalar oluşturulur.
2. **Haritalandırma:** Üretilen bu dosyalar ana ekranda haritalandırılır.
3. **Dışa Aktarma:** Zihin haritası şifrelenmiş biçimde dışa aktarılır (`Export`).

> **İpucu:** Oluşturduğunuz dosyayı şifresiz olarak doğrudan paylaşabilir veya erişim şifresini satabilirsiniz.

> **Önemli Not:** İndirdiğiniz `.kitap` uzantılı dosyaların güvenilir bir kaynaktan olduğundan lütfen emin olun.

## Programlar

| Program | Ne işe yarar? |
| --- | --- |
| **SPHERE** | Ana ekran |
| **TEXT** | Metin düzenleme |
| **DRAWING** | Çizim ve animasyon |
| **SOUND** | Ses düzenleme |
| **AI** | Yapay hafıza |
| **MEDIA** | Ses + video karma arşivi |
| **REC** | Ekran ve ses kaydı |
| **COPY** | Not defteri |
| **FILTER** | Ses filtreleme |
| **CONVERTER** | Format dönüştürme |

Bütün programlarda ortak kurallar:

- Her düğmenin üzerinde fare **0,6 saniye** durunca, siyah zeminli bir kutuda ne işe yaradığı yazar.
- Üst çubukta, en sağdaki düğme (programın adı: *Text*, *Sound*, *Rec* …) `Ctrl + Q` menüsünü açar; yanındaki **Export** dışa aktarır. Pencere daralırsa bu iki düğme alt satıra iner.
- Düğmeler 30×30 (simge) veya 90×30 (yazılı) boyuttadır; yazı sığmazsa düğme kendiliğinden genişler.

---

## Kurulum

> **Not:** Linux Mint XFCE üzerinde kurulması önerilir.

Komutları Kavram klasöründe (`kavram.py`'nin yanında) çalıştırın. Her komut şu adımları yapar: **sistem paketleri → sanal ortam (venv) → Python kütüphaneleri → C++ motorları → paketleme (`dist/`) → başlatma.** Paket, **kendi işletim sisteminde** üretilir (PyInstaller çapraz derleme yapmaz). İlk kurulum internet ister ve 10–30 dakika sürebilir.

| İşletim sistemi | Komut | Oluşan paket |
| --- | --- | --- |
| **Linux** (dağıtımı kendisi tanır) | `bash baslat_linux.sh` | `dist/kavram/kavram` ve `.tar.gz` |
| Debian · Ubuntu · Mint · Pop!_OS · Kali | `bash kurulum_deb.txt` | aynısı |
| Arch · Manjaro · EndeavourOS · CachyOS | `bash kurulum_arch.txt` | aynısı |
| Fedora · Nobara · AlmaLinux · Rocky | `bash kurulum_fedora.txt` | aynısı (RPM Fusion otomatik eklenir) |
| openSUSE Tumbleweed / Leap | `bash kurulum_opensuse.txt` | aynısı (Packman otomatik eklenir) |
| Void Linux | `bash kurulum_void.txt` | aynısı |
| **Windows 10 / 11** | `baslat_win.bat` dosyasına çift tıklayın | `dist\kavram\kavram.exe`, `.zip`, masaüstü kısayolu |
| **macOS 11+** (Apple Silicon / Intel) | `baslat_mac.command` dosyasına çift tıklayın (veya `bash kurulum_mac.txt`) | `dist/Kavram.app`, `.dmg`, `.zip` |

Linux betiklerini terminale **yapıştırarak** da çalıştırabilirsiniz.

| Sistem | Durum |
| --- | --- |
| **Linux** | Destekleniyor. Paket derlenip açıldığı doğrulandı. |
| **Windows 10/11** | **Deneysel.** Kod ve betikler hazır; Linux üzerinde taklitle denendi, gerçek Windows'ta henüz doğrulanmadı. |
| **macOS 11+** | **Deneysel.** Aynı durum: gerçek Mac'te henüz doğrulanmadı. |

> Bir adım takılırsa çıktıyı *issue* olarak paylaşın. Fedora, openSUSE ve Void betikleri de kendi dağıtımlarında henüz denenmedi (kurulamayan paket olursa betik uyarı verip devam eder). Alpine ve NixOS desteklenmiyor.

Windows/macOS'ta ekran, mikrofon ve kamera kaydının çalıştığını kurulumdan sonra şu komutla denetleyebilirsiniz (aygıtları listeler, kısa deneme kaydı yapar, her adımı `OK` / `HATA` olarak yazar):

```bash
venv\Scripts\python kayit_testi.py      # Windows
./venv/bin/python kayit_testi.py        # macOS
```

<img width="1920" height="1049" alt="3" src="https://github.com/user-attachments/assets/0b8b71af-737a-4387-a516-77c0fa217e6c" />

## Yapı

```text
kavram/
├── kavram.py              Çekirdek: program yükleyici ve editör değiştirici (Ctrl + Q)
├── kavram_ui.py           Ortak tasarım: düğmeler, üst bar, 0,6 sn Türkçe ipuçları
├── kavram_platform.py     Linux / Windows / macOS farkları
├── kavram_capture.py      Windows/macOS kayıt altyapısı (FFmpeg + OpenCV + PortAudio)
├── kavram.spec            Paketleme tarifi (PyInstaller)
├── baslat_linux.sh · baslat_win.bat · baslat_mac.command     Sistem başlatıcıları
├── kurulum_*.txt          Dağıtıma / sisteme özel kurulum betikleri
├── text/ drawing/ sound/ media/ rec/ sphere/ ai/ copy/ filter/ converter/ file_manager/ terminal/
│       └── her programın klasöründe:  rec.py (Linux) · rec_win.py (Windows) · rec_mac.py (macOS)
└── ikon/                  Uygulama simgesi
```

- **Çalışma:** `kavram.py` açılır, işletim sistemini belirler ve her program için o sistemin dosyasını yükler (yoksa varsayılan `.py`'ye döner). Her program kendi klasöründe durur; C++ motorları ve `derleme.txt` de aynı klasördedir.
- **Paketleme:** `kavram.spec` yalnızca çalışılan sistemin dosyalarını toplar ve `dist/` içinde paketi üretir.
- **C++ motorları:** ses, filtre ve dönüştürücü motorları her sistemde derlenir. Medya ve ekran kaydı motorları (GStreamer / PipeWire / X11) yalnızca Linux'tadır; Windows/macOS'ta yerlerini FFmpeg, OpenCV ve PortAudio tabanlı Python altyapısı alır.

---

# SPHERE

## Ana Ekran

Ana ekran, zihin haritalarının şifreli olarak arşivlendiği yerdir.

<img width="1918" height="1047" alt="s1" src="https://github.com/user-attachments/assets/4e6782df-e53e-4245-a70f-131ed9d720e4" />

<img width="1920" height="1047" alt="sphere" src="https://github.com/user-attachments/assets/bccf70d7-1060-4ec4-a2be-36493d3fe0f6" />

## Butonlarının İşlevleri

| Buton | İşlevi |
| --- | --- |
| **File** | İçeri arşiv almak ve kare (dosya) eklemek için kullanılır. |
| **Geri Al / İleri Al** | Yapılan işlemleri geri alır veya yeniden uygular. |
| **+** | Kare ekler. |
| **Liste** | Bağlantıların konum listesini açar. |
| **Terminal** | Terminal komutlarını kullanmak için açılır. |
| **/** | Arka plandaki gridli yapıyı açar / kapatır. |
| **Export** | **Sol tık:** XZ formatında dosya oluşturur (dosya daha küçük, ama oluşması daha uzun sürer).<br>**Sağ tık:** GZ formatında kaydeder (dosya daha büyük, ama daha hızlı oluşur).<br>Dosya `.kitap` uzantısıyla, şifreli olarak kaydedilir. |
| **Sphere** | Bütün programlarda üst barın en sağında, programın adıyla bulunur. `Ctrl + Q` menüsünü açar. |

### Terminal Komutları

**1. `reset`** — Her şeyi tamamen siler.

**2. `ap resim konumu`** — Duvar kâğıdını değiştirir.

```text
ap /home/lts/Pictures/resim4.png
```

### Harici Programları Sisteme Dahil Etme

**3. `isim program konumu`** — `Ctrl + Q` menüsünün **alt** kısmına bir program ekler (yardımcı programlar için).

```text
Zaman /home/lts/Kavram/Programlar/Zaman/Zaman
```

<img width="1920" height="1049" alt="Z" src="https://github.com/user-attachments/assets/a569dba7-1714-42cd-8502-16d0bd917692" />

**4. `k isim program konumu`** — `Ctrl + Q` menüsünün **üst** kısmına bir program ekler (ana programlar için). Dosya eklemek de mümkündür.

```text
k Blender /home/lts/blender-5.2.0-linux-x64/blender
```

<img width="1920" height="1050" alt="bl" src="https://github.com/user-attachments/assets/2749222e-e76c-43ec-b58f-aa33c5370315" />

> **Önemli:** Kavram bir tür işletim sistemi gibi çalıştığı için ana program kapatılırsa ona bağlı bütün programlar otomatik kapanır. Örneğin Blender kapatılmadan önce dosyayı kaydetmenizi ister; ama Kavram'ı kapatırsanız Blender hiçbir şey sormadan kapanır. Veri kaybı yaşamamak için dosyalarınızı önceden yedekleyin.

### Dikkat Edilmesi Gerekenler

1. **Dosyalarınızı yedekleyin.** Veri kaybı ihtimali çok düşük olsa da sıfır değildir.
2. **`reset` komutu** terminale yazıldığında her şey silinir.
3. **`Ctrl + S`** Sphere dışındaki 7 ana programda geçerlidir: açık programı kapatır ve ana ekrana döner. **Hiçbir şeyi kaydetmez.** Hızlı kaydetme için her editörde **File** butonunun yanındaki ikonu kullanın. Sphere'de bu ikon, o anki düzeni varsayılan yapar; program yeniden açılınca her şey aynı şekilde gelir.

---

# TEXT

**Metin düzenleme programı.** Zengin metin belgeleri oluşturur, biçimlendirir; not ve kod bloklarını düzenler.

<img width="1920" height="1049" alt="T1" src="https://github.com/user-attachments/assets/665de852-5ba9-4185-b21a-39a42a75a2bc" />

| Buton | İşlevi |
| :--- | :--- |
| **File** | Dosya açma / içeri aktarma penceresini açar. |
| **Kaydet** (disk ikonu) | Açık belgeyi kaydeder. |
| **Geri Al / Yinele** | Düzenleme geçmişinde geri veya ileri gider. |
| **Yazı boyutu** (rakam) | Tıklayınca boyut listesi açılır; fare tekerleği ile de değişir. |
| **O** | Yazılan satırları ortalar (açık / kapalı). |
| **A** | Yazıyı kalın yapar (açık / kapalı). |
| **Color** | Yazı rengi panelini açar; seçilen renkler HEX kodlarıyla görünür. |
| **/** | Sembol panelini açar / kapatır. |
| **I** | Otomatik kaydırma (okuma modu) başlatır / durdurur. |
| **Hız** (rakam) | Kaydırma hızını ayarlar (tekerlekle de değişir). |
| **Terminal** | Özel silme komutlarını çalıştırır (örn. dil veya karakter grubu silme). |
| **Arama kutusu, ara, ↑, ↓** | Metinde arar; bulunan sonuçlar arasında ileri / geri gider. |
| **Export** | Belgeyi dışa aktarır. |
| **Text** | Programın adı. `Ctrl + Q` menüsünü açar. |

---

# DRAWING

**Çizim ve animasyon programı.** Sayfa sayfa çizim, katmanlar, renk karıştırma, ızgara ve kare kare animasyon sunar.

<img width="1920" height="1050" alt="d1" src="https://github.com/user-attachments/assets/f4d11e07-ac0c-4ff9-b1f0-672a7c87cf5c" />

| Buton | Sol tık | Sağ tık |
| :--- | :--- | :--- |
| **File** | Görsel veya proje dosyası içe aktarır. | Referans görsel ekler. |
| **Kaydet** | Projeyi kaydeder. | — |
| **Sayfa numarası** | Sayfa menüsünü açar (tekerlekle sayfalar arasında gezilir). | — |
| **+** / **−** | Yeni sayfa ekler / mevcut sayfayı siler. | — |
| **Geri Al / Yinele** | Son işlemi geri alır / yineler. | — |
| **Kalem stili** | Fırça stilini değiştirir. | — |
| **O** | Gezinme modunu açar / kapatır. | Tuval boyutu / çözünürlük penceresini açar. |
| **G** | Referans görseli gösterir / gizler. | Referans saydamlığı ve katman konumu menüsü. |
| **Mix açısı** | Karışım açısı menüsü (tekerlekle de değişir). | Karışım modu menüsü. |
| **Color** | Renk seçimi menüsünü açar. | — |
| **Eraser** | Silgi modunu açar / kapatır. | Arka plan rengini değiştirir. |
| **R:** | Fırça / silgi boyutu menüsünü açar. | — |
| **Çizim** | Katman menüsünü açar. | — |
| **#** | Aktif katmanı en üstte sabitler. | — |
| **lm** | Lazy Mouse modunu açar / kapatır (yavaşlatılmış fare, düzgün çizgi). | Lazy Mouse ayar menüsü. |
| **/** | Basınç hassasiyetini açar / kapatır. | — |
| **» «** | Dikey ayna modunu açar / kapatır. | Yatay ayna modunu açar / kapatır. |
| **Export** | Dışa aktarım penceresini açar. | Gelişmiş dışa aktarım (FPS) menüsü. |
| **Drawing** | Programın adı. `Ctrl + Q` menüsünü açar. | — |

---

# SOUND

**Ses düzenleme programı.** Dalga formu üzerinde kesme, silme ve kayıt yapar.

<img width="1920" height="1047" alt="Ekran görüntüsü_2026-08-28_10-42-08" src="https://github.com/user-attachments/assets/33505066-7391-4be6-a0f7-0f3c17ae7406" />

| Buton | Sol tık | Sağ tık |
| :--- | :--- | :--- |
| **File** | Ses dosyalarını (`.wav`) veya `.sound` paketini içe aktarır. | — |
| **Kaydet** (disk ikonu) | Geçerli sesi veya `.sound` paketini kaydeder. | — |
| **Geri Al / Yinele** | Son işlemi geri alır / yineler (`Ctrl+Z`, `Ctrl+Shift+Z`). | — |
| **Cut** | Oynatma başlığının bulunduğu yerden keser. | — |
| **::** | Seçili alanın kalınlığındaki (ses düzeyi) tüm boşlukları otomatik siler. | — |
| **Delete** | Seçili ses bölümlerini siler. | — |
| **Play** | Oynatmayı başlatır / duraklatır. | — |
| **Record** | Mikrofon kaydını başlatır / durdurur. | — |
| **I** | Kayıt sonrası filtreleri açar / kapatır (kalıcı ayar). | — |
| **Dalga ölçeği** (rakam) | Dalga formu genişliğini ayarlar (1–7). | — |
| **Hız** | Oynatma hızını değiştirir (0,1x – 3x). | — |
| **Kaydırma adımı** | Fare tekerleği ile kaydırma adımını ayarlar (0,1 sn – 30 sn). | — |
| **/** | Geçici metin panelini açar / kapatır. | — |
| **O** | Paneldeki metni ortalar / sola yaslar. | — |
| **Yazı boyutu** (rakam) | Paneldeki yazı boyutunu ayarlar. | — |
| **Export** | Sesi `WAV` olarak dışa aktarır. | Sesi metin ve ayarlarla birlikte `.sound` paketi olarak dışa aktarır. |
| **Sound** | Programın adı. `Ctrl + Q` menüsünü açar. | — |

> **Not:** Kayıt, Linux'ta ses motoru (PortAudio) ile, Windows/macOS'ta aynı motorun kendi sürümüyle yapılır. macOS'ta ilk kayıtta mikrofon izni istenir.

---

# AI

**Yapay hafıza.** SQLite tabanlı soru-cevap paketlerini yönetir; yanıtlara ses (`.mp3`, `.wav`), resim (`.png`, `.jpg`), video (`.mp4`) ve harici dosya ekleyebilirsiniz. Kayıtlı veriler üzerinde sohbet modunda arama yapılır.

<img width="1920" height="1043" alt="ai" src="https://github.com/user-attachments/assets/63637946-2309-4697-ba3b-3ac3395fff04" />

| Buton | İşlevi |
| :--- | :--- |
| **File** | Veritabanı veya medya dosyalarını içeri aktarır / açar. |
| **Kaydet** | Değişiklikleri, paketleri ve veritabanını kaydeder. |
| **New** | Veri sayfasında yeni, boş bir soru-cevap paketi oluşturur. |
| **Chat** | Sohbet (etkileşim ve arama) sayfasını açar. |
| **Edit** | Veri yönetimi (soru-cevap paketleri) sayfasını açar. |
| **X** | Sohbet ekranındaki mesajları temizler. |
| **_** | Tam ekran / medya görünümünden çıkar. |
| **Yazı boyutu** (rakam) | Metin boyutunu değiştirir (tıklama, menü veya tekerlek). |
| **S** | Geçici `ai` çalışma klasörünü ve açık veri belleğini temizler. |
| **Export** | Veri paketlerini ve bağlı medyayı dışa aktarır. |
| **Ai** | Programın adı. `Ctrl + Q` menüsünü açar. |

---

# MEDIA

**Ses ve videolardan oluşan karma arşiv programı.** Zaman çizelgesinde parçaları keser, sıralar, kaydeder ve tek dosyaya birleştirir.

<img width="1920" height="1049" alt="M" src="https://github.com/user-attachments/assets/2aa5206d-dedb-4256-b859-ffb58721ae99" />

| Buton | Sol tık | Sağ tık |
| :--- | :--- | :--- |
| **File** | Medya dosyalarını (video, ses, `.media` arşivi) içe aktarır. | — |
| **Kaydet** (disk ikonu) | Projeyi hızlıca kaydeder (daha önce kaydedildiyse üzerine yazar, değilse "farklı kaydet" açar). | — |
| **Geri Al / Yinele** | Son işlemi geri alır / yineler. | — |
| **Play** | Seçili parçayı oynatır / duraklatır. | — |
| **/** | Sıralı oynatmayı açar / kapatır (parçalar arası otomatik geçiş). | — |
| **Cut** | Aktif parçayı oynatma başlığının bulunduğu yerden ikiye böler. | — |
| **Delete** | Zaman çizelgesinde seçili parçayı siler. | — |
| **Camera** | Kamera modunu açar: kamera + mikrofon kaydı (geliştirme aşamasında). | — |
| **Sound** | Mikrofon ile ses kaydını başlatır / durdurur. | — |
| **I** | Gürültü filtresini açar / kapatır (kalıcı ayar). | — |
| **S** | `medya_cut` çalışma klasörünü temizler, zaman çizelgesini sıfırlar. | — |
| **Seek aralığı** (açılır kutu) | Tekerlekle ileri / geri sarma adımını ayarlar (2 sn, 5 sn, 1 dk …). | — |
| **Oynatma hızı** (açılır kutu) | Oynatma hızını değiştirir (0,5x, 1x, 2x …). | — |
| **Export** | Bütün parçaları `.media` arşivi olarak dışa aktarır (proje kaydı). | Bütün zaman çizelgesini tek bir `.mkv` videoya render eder. |
| **Media** | Programın adı. `Ctrl + Q` menüsünü açar. | — |

> **Not:** Kamera ve mikrofon kaydı Linux'ta C++ kaydedici ile, Windows/macOS'ta OpenCV + PortAudio + FFmpeg ile yapılır. İlk açılışta kamera / mikrofon izni istenir.

---

# REC

**Ekran ve ses kaydetme programı.** Kayıt, arka planda parça parça (`s1.mkv`, `s2.mkv` …) alınır; **Export** hepsini sırayla birleştirir.

<img width="1918" height="1046" alt="r1" src="https://github.com/user-attachments/assets/9e91a992-8da1-4b17-b614-d4e0e4f235fa" />

| Buton | İşlevi |
| :--- | :--- |
| **File** | Harici bir video (`.rec`, `.mp4`, `.mkv`) veya ses (`.wav`) dosyasını oynatıcıya yükler. |
| **Camera** | Yüzen kamera penceresini açar; pencere ekran kaydına girer (geliştirme aşamasında). |
| **Windows** | Ekran kaydı alınıp alınmayacağını belirler. Aktifken rengi değişir; yalnızca ses kaydı için kapatılabilir. |
| **Sound** | Mikrofon / sistem sesi kaydını açar / kapatır. Linux'ta EasyEffects ve varsayılan PulseAudio kaynaklarını otomatik algılar. |
| **I** | Gürültü engelleme ve ses filtresi zincirini açar / kapatır (dışa aktarırken uygulanır). |
| **S** | Her şeyi siler ve kapatır. |
| **Kalınlık** (rakam) | Yüzen pencerenin kalınlığını (30–50 px) ayarlar.<br>• Tekerlek: kalınlık<br>• Sol tık: yüzen pencereyi varsayılan konuma getirir<br>• Sağ tık: mevcut konumu varsayılan yapar |
| **/** | Klavye tuşlarını ve fare tıklamalarını ekranda gösteren yüzen siyah paneli açar / kapatır. |
| **Z** | Ekrandaki canlı kayıt süresi panelini açar / kapatır. |
| **Süre** (açılır menü) | Kayıt limiti (1–30 dk): süreye ulaşınca kayıt otomatik duraklar. |
| **Segment** (açılır menü) | Arka planda kaç saniyede bir yeni parça dosyası oluşacağını belirler. |
| **Play / Pause** | Kaydı veya oynatmayı başlatır / duraklatır (genel kısayol: `Ctrl + M`). |
| **X** | Açık dosya oynatma çubuğunu kapatır, oynatıcıyı sıfırlar. |
| **Segment X** (menü) | Biriken kayıt parçalarını listeler; tek tek veya **Hepsi** ile siler. |
| **Export** | Bütün parçaları sırayla birleştirir, isteğe bağlı ses filtresini uygular, MKV / WAV olarak kaydeder. |
| **Rec** | Programın adı. `Ctrl + Q` menüsünü açar. |

> **Not:** Eski bilgisayarlarda çalışacak şekilde tasarlanmıştır; süre sınırı vardır. Büyük dosyalar oluşturmadan önce kendi bilgisayarınızda deneyin.
>
> **Windows / macOS:** ekran kaydı FFmpeg ile (`gdigrab` / `avfoundation`), kamera OpenCV ile yapılır. Canlı ekran önizlemesi ve ses seviyesi paneli yoktur; hoparlör sesini kaydetmek için sanal ses aygıtı (Windows: Stereo Mix / VB-Cable, macOS: BlackHole) gerekir. macOS'ta **Ekran Kaydı**, Kamera ve Mikrofon izinleri istenir.

<img width="1920" height="1045" alt="R" src="https://github.com/user-attachments/assets/bbb4c6c4-e8c5-41cf-9273-8ffed6543335" />

---

# COPY

**Not defteri programı.** Renkli notlar, görsel / metin galerileri ve PDF sayfaları saklar.

<img width="1920" height="1043" alt="N" src="https://github.com/user-attachments/assets/34d80842-0917-4ae5-8d5c-5f28b30d7e00" />

| Buton | İşlevi |
| :--- | :--- |
| **File** | `.copya` proje dosyasını açar. |
| **Kaydet** (disk ikonu) | Projeyi kaydeder (dosya yoksa "farklı kaydet" açar). |
| **+** | Yeni boş not ekler. |
| **Galeri** | Görselleri, `.txt` ve `.txr` dosyalarını seçip galeri notu olarak ekler. |
| **Belge** | `PDF` veya `PNF` (Drawing) dosyasını sayfa sayfa galeri notu olarak içe aktarır. |
| **#** (sayfa numarası) | Genişletilmiş galerideki öğeler arasında gezinme menüsü. |
| **I** | Otomatik kaydırmayı (okuma modu) başlatır / durdurur. |
| **Hız** (rakam) | Otomatik kaydırma hızı menüsü. |
| **Boyut** (rakam) | Belge modunda sayfa boyutunu ayarlar. |
| **X** | Genişletilmiş notu siler. |
| **_** | Genişletilmiş notu küçültür. |
| **/** | Notun içeriğini panoya kopyalar (resimde dosya yolu, metinde düz metin). |
| **Export** | Projeyi `.copya` arşivi olarak dışa aktarır. |
| **Copy** | Programın adı. `Ctrl + Q` menüsünü açar. |

---

# FILTER

**Ses ve video filtreleme.** Spektral gürültü azaltma, akıllı VAD (ses aktivite tespiti) ve çok katmanlı filtreleme ile ses ve video dosyalarını işler.

- **x1 filtresi (spektral temizleme):** 2 aşamalı gürültü azaltma; güç ayarı 1–9.
- **x2 filtresi (akıllı alt frekans susturma):** 30–200 Hz arasında belirlenen frekansın altındaki gürültü bölgelerini susturur.
- **Gürültü profilleri:** Kullanıcının oluşturduğu hedefli profiller (en fazla 8).
- **Video desteği:** Videodan ses çıkarır, filtreler ve işlenmiş sesi videoyla birleştirir (FFmpeg).
- **Ses düzenleme paneli:** Genel ses, arka plan müziği şiddeti, pitch, hız, bitiş sonrası müzik süresi.
- **Kalıcı müzik:** Arka plan müziğini kaydedip her seferinde otomatik ekler.
- **5 saniyelik önizleme** ve son 5 işlemi gösteren **rapor paneli**.

<img width="1920" height="1048" alt="F" src="https://github.com/user-attachments/assets/c6763870-86d7-4973-b307-0e94eecca578" />

| Buton | Sol tık | Sağ tık |
| :--- | :--- | :--- |
| **File** | Ses veya video dosyası yükler. | — |
| **::** | Gürültü profili için ses dosyası seçer (en fazla 8). | — |
| **/** | Ses düzenleme panelini açar / kapatır. | — |
| **Process** | Aktif filtreleri seçili dosyaya uygular. | — |
| **Reset** | Panel açıksa ayarları sıfırlar; kapalıysa bütün profilleri varsayılana döndürür (x1 güç = 5, x2 kesim = 75 Hz). | — |
| **Play** | Filtrelenmiş sesin 5 saniyelik önizlemesini çalar; tekrar tıklayınca duraklar. | — |
| **Müzik** | Arka plan müziği seçer (geçici). | Seçili müziği kalıcı yapar veya iptal eder. |
| **Export** | Filtrelenmiş sesi (WAV, MP3, FLAC) veya videoyu (orijinal format) kaydeder. | — |

> **Not:** Filter, **Sound, Media ve Rec** ile bağlantılıdır. Bu üç programın üst barındaki **I** ikonunu açarsanız, ses kaydı alınırken dosya filtrelenir.

---

# CONVERTER

**Dosya format değiştirme programı.** Ses, video, PDF ve resim dosyalarını dönüştürür.

<img width="1920" height="1027" alt="C" src="https://github.com/user-attachments/assets/87a96bb1-d300-48c4-a062-9aaf4cf3e815" />

| Kontrol | İşlevi |
| :--- | :--- |
| **File** | Dönüştürülecek dosyayı (ses, video, PDF, resim) seçer. |
| **Convert** | Seçilen dosyayı, aşağıdaki ayarlara göre dönüştürür. |
| **Reset** | Bütün dönüştürme ayarlarını varsayılana döndürür. |
| **Export** | Çıktı dosyasını seçilen konuma kaydeder. |
| **Format** | Çıktı formatı (`.wav`, `.mp3`, `.mp4`, `.pdf`, `.jpg` …). |
| **Frekans değiştir / Yeni frekans (Hz)** | Ses örnekleme frekansını değiştirmeyi açar / kapatır; hedef Hz değeri girilir. |
| **Ses hızı** | 0,10x – 4,0x. |
| **Ses perdesi** | −6 ile +6 ton arası. |
| **Ses efekti** | Normalleştir, Sıkıştır, Filtre, Fade, Kaydırma vb. |
| **Kapak resmi seç** | Sesi videoya çevirirken kullanılacak kapak resmini seçer. |
| **Video: renkleri ters çevir / gri ton / sesi sil** | Evet seçilirse çıktıya uygulanır. |
| **Harici ses ekle (Sync)** | Videoya ana ses olarak eklenecek harici ses dosyasını seçer. |
| **PDF / Resim: ters çevir, gri ton** | Evet seçilirse çıktıya uygulanır. |
| **Resim çözünürlüğü** | −5 = %25 küçült, 0 = orijinal, +5 = %250 büyüt. |

### Lisans

GNU Genel Kamu Lisansı sürüm 3 veya (tercihinize bağlı) daha yenisi. Ayrıntı `kavram.py` dosyasının başındadır.

[⬆ Başa dön](#kavram) · [🇬🇧 English](#english)

---

# English

**Kavram** is a free, open-source archive platform that brings educational and media work under one roof.

It offers text, drawing, sound, video, screen recording and notes in a single system. You can edit what you create, link the pieces together, and build mind maps in **SPHERE** that are archived in encrypted form.

Kavram is not only a set of ready-made programs. You can also plug in programs you develop yourself, so it is designed less as a classic application bundle and more as a platform on which you build your own working environment.

**10 integrated programs + an extensible program system.**

**On this page:** [Workflow](#workflow) · [Programs](#programs) · [Installation](#installation) · [Structure](#structure) · [Sphere](#sphere-home-screen) · [Text](#text-text-editor) · [Drawing](#drawing-drawing-and-animation) · [Sound](#sound-audio-editor) · [AI](#ai-artificial-memory) · [Media](#media-mixed-archive) · [Rec](#rec-recorder) · [Copy](#copy-notes) · [Filter](#filter-audio-filter) · [Converter](#converter-format-converter)

## Workflow

1. **Create files:** the required files are produced in the main programs.
2. **Map them:** the produced files are laid out on the home screen as a map.
3. **Export:** the mind map is exported in encrypted form (`Export`).

> **Tip:** you can share the file you create without a password, or sell the access password.

> **Important:** make sure any `.kitap` file you download comes from a trusted source.

## Programs

| Program | What it is for |
| --- | --- |
| **SPHERE** | Home screen |
| **TEXT** | Text editing |
| **DRAWING** | Drawing and animation |
| **SOUND** | Audio editing |
| **AI** | Artificial memory |
| **MEDIA** | Mixed audio + video archive |
| **REC** | Screen and audio recording |
| **COPY** | Notebook |
| **FILTER** | Audio filtering |
| **CONVERTER** | Format conversion |

Rules shared by all programs:

- Hold the mouse over any button for **0.6 seconds** and a black box tells you what it does.
- In the top bar, the right-most button (the program name: *Text*, *Sound*, *Rec* …) opens the `Ctrl + Q` menu; the **Export** next to it exports. When the window gets narrow these two buttons drop to a second row.
- Buttons are 30×30 (icon) or 90×30 (text); if the text does not fit, the button widens by itself.

---

## Installation

> **Note:** Linux Mint XFCE is the recommended platform.

Run the commands in the Kavram folder (next to `kavram.py`). Every command performs these steps: **system packages → virtual environment (venv) → Python libraries → C++ engines → packaging (`dist/`) → launch.** The package is built **on its own operating system** (PyInstaller does not cross-compile). The first installation needs internet access and can take 10–30 minutes.

| System | Command | Resulting package |
| --- | --- | --- |
| **Linux** (detects the distro itself) | `bash baslat_linux.sh` | `dist/kavram/kavram` and `.tar.gz` |
| Debian · Ubuntu · Mint · Pop!_OS · Kali | `bash kurulum_deb.txt` | same |
| Arch · Manjaro · EndeavourOS · CachyOS | `bash kurulum_arch.txt` | same |
| Fedora · Nobara · AlmaLinux · Rocky | `bash kurulum_fedora.txt` | same (RPM Fusion is added automatically) |
| openSUSE Tumbleweed / Leap | `bash kurulum_opensuse.txt` | same (Packman is added automatically) |
| Void Linux | `bash kurulum_void.txt` | same |
| **Windows 10 / 11** | double-click `baslat_win.bat` | `dist\kavram\kavram.exe`, `.zip`, desktop shortcut |
| **macOS 11+** (Apple Silicon / Intel) | double-click `baslat_mac.command` (or `bash kurulum_mac.txt`) | `dist/Kavram.app`, `.dmg`, `.zip` |

You can also **paste** the Linux scripts into a terminal.

| System | Status |
| --- | --- |
| **Linux** | Supported. The package was built and launch-verified. |
| **Windows 10/11** | **Experimental.** Code and scripts are ready; tested by simulation on Linux, not yet validated on real Windows. |
| **macOS 11+** | **Experimental.** Same: not yet validated on a real Mac. |

> If a step fails, please share the output as an *issue*. The Fedora, openSUSE and Void scripts have not yet been tried on their own distributions either (if a package cannot be installed, the script warns and continues). Alpine and NixOS are not supported.

On Windows/macOS you can check that screen, microphone and camera capture work after installation with this command (it lists the devices, makes a short trial recording and prints each step as `OK` / `HATA`, i.e. error):

```bash
venv\Scripts\python kayit_testi.py      # Windows
./venv/bin/python kayit_testi.py        # macOS
```

<img width="1920" height="1049" alt="3" src="https://github.com/user-attachments/assets/0b8b71af-737a-4387-a516-77c0fa217e6c" />

## Structure

```text
kavram/
├── kavram.py              Core: program loader and editor switcher (Ctrl + Q)
├── kavram_ui.py           Shared design: buttons, top bar, 0.6 s tooltips
├── kavram_platform.py     Linux / Windows / macOS differences
├── kavram_capture.py      Windows/macOS recording backend (FFmpeg + OpenCV + PortAudio)
├── kavram.spec            Packaging recipe (PyInstaller)
├── baslat_linux.sh · baslat_win.bat · baslat_mac.command     Per-OS launchers
├── kurulum_*.txt          Install scripts per distribution / system
├── text/ drawing/ sound/ media/ rec/ sphere/ ai/ copy/ filter/ converter/ file_manager/ terminal/
│       └── in each program folder:  rec.py (Linux) · rec_win.py (Windows) · rec_mac.py (macOS)
└── ikon/                  Application icon
```

- **Runtime:** `kavram.py` starts, detects the operating system and loads that system's file for each program (falling back to the default `.py`). Every program lives in its own folder, together with its C++ engines and `derleme.txt`.
- **Packaging:** `kavram.spec` collects only the current system's files and produces the package in `dist/`.
- **C++ engines:** the sound, filter and converter engines are built on every system. The media and screen-recording engines (GStreamer / PipeWire / X11) exist only on Linux; on Windows/macOS a Python backend based on FFmpeg, OpenCV and PortAudio takes their place.

---

# Sphere: home screen

The home screen is where mind maps are archived in encrypted form.

<img width="1918" height="1047" alt="s1" src="https://github.com/user-attachments/assets/4e6782df-e53e-4245-a70f-131ed9d720e4" />

<img width="1920" height="1047" alt="sphere" src="https://github.com/user-attachments/assets/bccf70d7-1060-4ec4-a2be-36493d3fe0f6" />

## Button functions

| Button | Function |
| --- | --- |
| **File** | Imports an archive and adds a tile (file). |
| **Undo / Redo** | Reverts or re-applies the actions you made. |
| **+** | Adds a tile. |
| **List** | Opens the location list of the links. |
| **Terminal** | Opens the terminal for commands. |
| **/** | Shows / hides the grid in the background. |
| **Export** | **Left click:** creates an XZ file (smaller, but takes longer to create).<br>**Right click:** saves as GZ (larger, but created faster).<br>The file is saved encrypted with the `.kitap` extension. |
| **Sphere** | In every program it sits at the far right of the top bar under the program's name. Opens the `Ctrl + Q` menu. |

### Terminal commands

**1. `reset`** — wipes everything completely.

**2. `ap image-path`** — changes the wallpaper.

```text
ap /home/lts/Pictures/resim4.png
```

### Adding external programs to the system

**3. `name program-path`** — adds a program to the **lower** part of the `Ctrl + Q` menu (for helper programs).

```text
Zaman /home/lts/Kavram/Programlar/Zaman/Zaman
```

<img width="1920" height="1049" alt="Z" src="https://github.com/user-attachments/assets/a569dba7-1714-42cd-8502-16d0bd917692" />

**4. `k name program-path`** — adds a program to the **upper** part of the `Ctrl + Q` menu (for main programs). Adding files is also possible.

```text
k Blender /home/lts/blender-5.2.0-linux-x64/blender
```

<img width="1920" height="1050" alt="bl" src="https://github.com/user-attachments/assets/2749222e-e76c-43ec-b58f-aa33c5370315" />

> **Important:** Kavram works like a small operating system, so when the main program is closed, every program attached to it closes automatically. For example Blender asks you to save before closing, but if you close Kavram, Blender closes without asking. Back up your files beforehand to avoid losing data.

### Things to watch out for

1. **Back up your files.** The chance of data loss is very low, but it is not zero.
2. **The `reset` command** wipes everything when typed in the terminal.
3. **`Ctrl + S`** works in the 7 main programs other than Sphere: it closes the open program and returns to the home screen. **It saves nothing.** For quick saving use the icon next to the **File** button in each editor. In Sphere that icon makes the current layout the default, so everything comes back the same way when the program is reopened.

---

# Text: text editor

**Text editing program.** Creates and formats rich-text documents; organizes notes and code blocks.

<img width="1920" height="1049" alt="T1" src="https://github.com/user-attachments/assets/665de852-5ba9-4185-b21a-39a42a75a2bc" />

| Button | Function |
| :--- | :--- |
| **File** | Opens the file open / import window. |
| **Save** (disk icon) | Saves the open document. |
| **Undo / Redo** | Goes back or forward in the edit history. |
| **Font size** (number) | Click for the size list; the mouse wheel also changes it. |
| **O** | Centers the typed lines (on / off). |
| **A** | Makes the text bold (on / off). |
| **Color** | Opens the text-color panel; chosen colors appear as HEX codes. |
| **/** | Shows / hides the symbol panel. |
| **I** | Starts / stops auto-scroll (reading mode). |
| **Speed** (number) | Sets the scroll speed (the wheel also changes it). |
| **Terminal** | Runs special delete commands (e.g. deleting a language or character group). |
| **Search box, search, ↑, ↓** | Searches the text; moves forward / back between the matches. |
| **Export** | Exports the document. |
| **Text** | The program name. Opens the `Ctrl + Q` menu. |

---

# Drawing: drawing and animation

**Drawing and animation program.** Offers page-by-page drawing, layers, color mixing, a grid and frame-by-frame animation.

<img width="1920" height="1050" alt="d1" src="https://github.com/user-attachments/assets/f4d11e07-ac0c-4ff9-b1f0-672a7c87cf5c" />

| Button | Left click | Right click |
| :--- | :--- | :--- |
| **File** | Imports an image or project file. | Adds a reference image. |
| **Save** | Saves the project. | — |
| **Page number** | Opens the page menu (the wheel moves between pages). | — |
| **+** / **−** | Adds a new page / deletes the current page. | — |
| **Undo / Redo** | Reverts / re-applies the last action. | — |
| **Pen style** | Changes the brush style. | — |
| **O** | Turns navigation mode on / off. | Opens the canvas size / resolution window. |
| **G** | Shows / hides the reference image. | Reference opacity and layer-position menu. |
| **Mix angle** | Mix-angle menu (the wheel also changes it). | Mix-mode menu. |
| **Color** | Opens the color-selection menu. | — |
| **Eraser** | Turns eraser mode on / off. | Changes the background color. |
| **R:** | Opens the brush / eraser size menu. | — |
| **Drawing** | Opens the layer menu. | — |
| **#** | Pins the active layer on top. | — |
| **lm** | Turns Lazy Mouse on / off (slowed mouse for smooth lines). | Lazy Mouse settings menu. |
| **/** | Turns pressure sensitivity on / off. | — |
| **» «** | Turns vertical mirror mode on / off. | Turns horizontal mirror mode on / off. |
| **Export** | Opens the export window. | Advanced export (FPS) menu. |
| **Drawing** | The program name. Opens the `Ctrl + Q` menu. | — |

---

# Sound: audio editor

**Audio editing program.** Cuts, deletes and records on a waveform.

<img width="1920" height="1047" alt="Ekran görüntüsü_2026-08-28_10-42-08" src="https://github.com/user-attachments/assets/33505066-7391-4be6-a0f7-0f3c17ae7406" />

| Button | Left click | Right click |
| :--- | :--- | :--- |
| **File** | Imports audio files (`.wav`) or a `.sound` package. | — |
| **Save** (disk icon) | Saves the current audio or `.sound` package. | — |
| **Undo / Redo** | Reverts / re-applies the last action (`Ctrl+Z`, `Ctrl+Shift+Z`). | — |
| **Cut** | Cuts at the playhead. | — |
| **::** | Automatically deletes every gap with the thickness (volume level) of the selected area. | — |
| **Delete** | Deletes the selected audio sections. | — |
| **Play** | Starts / pauses playback. | — |
| **Record** | Starts / stops microphone recording. | — |
| **I** | Turns post-recording filters on / off (persistent setting). | — |
| **Waveform scale** (number) | Sets the waveform width (1–7). | — |
| **Speed** | Changes the playback speed (0.1x – 3x). | — |
| **Scroll step** | Sets the mouse-wheel scroll step (0.1 s – 30 s). | — |
| **/** | Shows / hides the temporary text panel. | — |
| **O** | Centers / left-aligns the text in the panel. | — |
| **Font size** (number) | Sets the font size in the panel. | — |
| **Export** | Exports the audio as `WAV`. | Exports the audio together with the text and settings as a `.sound` package. |
| **Sound** | The program name. Opens the `Ctrl + Q` menu. | — |

> **Note:** Recording uses the sound engine (PortAudio) on Linux, and the same engine's own build on Windows/macOS. macOS asks for microphone permission on the first recording.

---

# AI: artificial memory

**Artificial memory.** Manages SQLite-based question-answer packets; you can attach audio (`.mp3`, `.wav`), images (`.png`, `.jpg`), video (`.mp4`) and external files to the answers. Search runs over the stored data in chat mode.

<img width="1920" height="1043" alt="ai" src="https://github.com/user-attachments/assets/63637946-2309-4697-ba3b-3ac3395fff04" />

| Button | Function |
| :--- | :--- |
| **File** | Imports / opens a database or media files. |
| **Save** | Saves changes, packets and the database. |
| **New** | Creates a new, empty question-answer packet on the data page. |
| **Chat** | Opens the chat (interaction and search) page. |
| **Edit** | Opens the data-management (question-answer packets) page. |
| **X** | Clears the messages on the chat screen. |
| **_** | Leaves the full-screen / media view. |
| **Font size** (number) | Changes the text size (click, menu or wheel). |
| **S** | Clears the temporary `ai` working folder and the open data memory. |
| **Export** | Exports the data packets and the linked media. |
| **Ai** | The program name. Opens the `Ctrl + Q` menu. |

---

# Media: mixed archive

**Mixed archive program made of audio and video.** Cuts, orders, saves and merges pieces into one file on a timeline.

<img width="1920" height="1049" alt="M" src="https://github.com/user-attachments/assets/2aa5206d-dedb-4256-b859-ffb58721ae99" />

| Button | Left click | Right click |
| :--- | :--- | :--- |
| **File** | Imports media files (video, audio, `.media` archive). | — |
| **Save** (disk icon) | Saves the project quickly (overwrites if it was saved before, otherwise opens "save as"). | — |
| **Undo / Redo** | Reverts / re-applies the last action. | — |
| **Play** | Plays / pauses the selected piece. | — |
| **/** | Turns sequential playback on / off (automatic hand-over between pieces). | — |
| **Cut** | Splits the active piece in two at the playhead. | — |
| **Delete** | Deletes the piece selected on the timeline. | — |
| **Camera** | Turns on camera mode: camera + microphone recording (under development). | — |
| **Sound** | Starts / stops audio recording with the microphone. | — |
| **I** | Turns the noise filter on / off (persistent setting). | — |
| **S** | Clears the `medya_cut` working folder and resets the timeline. | — |
| **Seek interval** (drop-down) | Sets the wheel's forward / back seek step (2 s, 5 s, 1 min …). | — |
| **Playback speed** (drop-down) | Changes the playback speed (0.5x, 1x, 2x …). | — |
| **Export** | Exports all pieces as a `.media` archive (project save). | Renders the whole timeline into a single `.mkv` video. |
| **Media** | The program name. Opens the `Ctrl + Q` menu. | — |

> **Note:** Camera and microphone recording uses the C++ recorder on Linux, and OpenCV + PortAudio + FFmpeg on Windows/macOS. Camera / microphone permission is requested on first use.

---

# Rec: recorder

**Screen and audio recording program.** Recording is taken in the background piece by piece (`s1.mkv`, `s2.mkv` …); **Export** merges them all in order.

<img width="1918" height="1046" alt="r1" src="https://github.com/user-attachments/assets/9e91a992-8da1-4b17-b614-d4e0e4f235fa" />

| Button | Function |
| :--- | :--- |
| **File** | Loads an external video (`.rec`, `.mp4`, `.mkv`) or audio (`.wav`) file into the player. |
| **Camera** | Opens the floating camera window; the window appears in the screen recording (under development). |
| **Windows** | Decides whether the screen is recorded. Its color changes when active; it can be turned off for audio-only recording. |
| **Sound** | Turns microphone / system-audio recording on / off. On Linux it detects EasyEffects and default PulseAudio sources automatically. |
| **I** | Turns the noise-suppression and audio-filter chain on / off (applied while exporting). |
| **S** | Deletes everything and closes. |
| **Thickness** (number) | Sets the thickness (30–50 px) of the floating window.<br>• Wheel: thickness<br>• Left click: puts the floating window back at the default position<br>• Right click: makes the current position the default |
| **/** | Shows / hides the floating black panel that displays keystrokes and mouse clicks. |
| **Z** | Shows / hides the live recording-time panel on screen. |
| **Duration** (drop-down) | Recording limit (1–30 min): recording pauses automatically when it is reached. |
| **Segment** (drop-down) | Sets how many seconds pass before a new piece file is created in the background. |
| **Play / Pause** | Starts / pauses recording or playback (global shortcut: `Ctrl + M`). |
| **X** | Closes the open-file playback bar and resets the player. |
| **Segment X** (menu) | Lists the accumulated recording pieces; delete one by one or with **All**. |
| **Export** | Merges all pieces in order, optionally applies the audio filter, and saves as MKV / WAV. |
| **Rec** | The program name. Opens the `Ctrl + Q` menu. |

> **Note:** Designed to work on older computers; there is a time limit. Test on your own computer before creating large files.
>
> **Windows / macOS:** screen recording uses FFmpeg (`gdigrab` / `avfoundation`) and the camera uses OpenCV. There is no live screen preview or audio-level panel; recording speaker audio needs a virtual audio device (Windows: Stereo Mix / VB-Cable, macOS: BlackHole). macOS asks for **Screen Recording**, Camera and Microphone permissions.

<img width="1920" height="1045" alt="R" src="https://github.com/user-attachments/assets/bbb4c6c4-e8c5-41cf-9273-8ffed6543335" />

---

# Copy: notes

**Notebook program.** Stores colored notes, image / text galleries and PDF pages.

<img width="1920" height="1043" alt="N" src="https://github.com/user-attachments/assets/34d80842-0917-4ae5-8d5c-5f28b30d7e00" />

| Button | Function |
| :--- | :--- |
| **File** | Opens a `.copya` project file. |
| **Save** (disk icon) | Saves the project (opens "save as" if there is no file yet). |
| **+** | Adds a new empty note. |
| **Gallery** | Picks images, `.txt` and `.txr` files and adds them as a gallery note. |
| **Document** | Imports a `PDF` or `PNF` (Drawing) file page by page as a gallery note. |
| **#** (page number) | Menu for moving between items in the expanded gallery. |
| **I** | Starts / stops auto-scroll (reading mode). |
| **Speed** (number) | Auto-scroll speed menu. |
| **Size** (number) | Sets the page size in document mode. |
| **X** | Deletes the expanded note. |
| **_** | Shrinks the expanded note. |
| **/** | Copies the note's content to the clipboard (file path for images, plain text for text). |
| **Export** | Exports the project as a `.copya` archive. |
| **Copy** | The program name. Opens the `Ctrl + Q` menu. |

---

# Filter: audio filter

**Audio and video filtering.** Processes audio and video files with spectral noise reduction, smart VAD (voice activity detection) and multi-layer filtering.

- **x1 filter (spectral cleaning):** 2-stage noise reduction; strength setting 1–9.
- **x2 filter (smart low-frequency muting):** mutes noise regions below the frequency you set between 30–200 Hz.
- **Noise profiles:** targeted profiles created by the user (up to 8).
- **Video support:** extracts audio from a video, filters it, and merges the processed audio back into the video (FFmpeg).
- **Audio editing panel:** overall volume, background-music level, pitch, speed, music length after the end.
- **Persistent music:** saves the background music and adds it automatically every time.
- **5-second preview** and a **report panel** showing the last 5 operations.

<img width="1920" height="1048" alt="F" src="https://github.com/user-attachments/assets/c6763870-86d7-4973-b307-0e94eecca578" />

| Button | Left click | Right click |
| :--- | :--- | :--- |
| **File** | Loads an audio or video file. | — |
| **::** | Picks an audio file for a noise profile (up to 8). | — |
| **/** | Shows / hides the audio editing panel. | — |
| **Process** | Applies the active filters to the selected file. | — |
| **Reset** | Resets the settings if the panel is open; otherwise returns all profiles to defaults (x1 strength = 5, x2 cutoff = 75 Hz). | — |
| **Play** | Plays a 5-second preview of the filtered audio; click again to pause. | — |
| **Music** | Picks background music (temporary). | Makes the selected music persistent or cancels it. |
| **Export** | Saves the filtered audio (WAV, MP3, FLAC) or video (original format). | — |

> **Note:** Filter is linked to **Sound, Media and Rec**. If you turn on the **I** icon in the top bar of these three programs, the file is filtered while audio is being recorded.

---

# Converter: format converter

**File format conversion program.** Converts audio, video, PDF and image files.

<img width="1920" height="1027" alt="C" src="https://github.com/user-attachments/assets/87a96bb1-d300-48c4-a062-9aaf4cf3e815" />

| Control | Function |
| :--- | :--- |
| **File** | Selects the file to convert (audio, video, PDF, image). |
| **Convert** | Converts the selected file using the settings below. |
| **Reset** | Returns all conversion settings to their defaults. |
| **Export** | Saves the output file to the chosen location. |
| **Format** | Output format (`.wav`, `.mp3`, `.mp4`, `.pdf`, `.jpg` …). |
| **Change frequency / New frequency (Hz)** | Turns audio sample-rate change on / off; the target Hz value is entered. |
| **Audio speed** | 0.10x – 4.0x. |
| **Audio pitch** | −6 to +6 semitones. |
| **Audio effect** | Normalize, Compress, Filter, Fade, Shift, etc. |
| **Choose cover image** | Picks the cover image used when turning audio into video. |
| **Video: invert colors / grayscale / remove audio** | Applied to the output when Yes is selected. |
| **Add external audio (Sync)** | Picks an external audio file to be added to the video as the main audio. |
| **PDF / Image: invert, grayscale** | Applied to the output when Yes is selected. |
| **Image resolution** | −5 = shrink 25%, 0 = original, +5 = enlarge 250%. |

### License

GNU General Public License version 3 or (at your option) any later version — see the header of `kavram.py`.

[⬆ Back to top](#kavram) · [🇹🇷 Türkçe](#türkçe)
