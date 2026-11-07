# Kavram

**Kavram**, eğitim ve medya çalışmalarını tek bir çatı altında toplayan, özgür ve açık kaynak kodlu bir arşiv platformudur.

Metin, çizim, ses, video, ekran kaydı ve notlar gibi farklı araçları tek bir sistem içerisinde sunar. Oluşturduğunuz içerikleri düzenleyebilir, birbirleriyle ilişkilendirebilir ve **SPHERE** üzerinden zihin haritaları oluşturarak şifreli şekilde arşivleyebilirsiniz.

Kavram yalnızca hazır programlardan oluşmaz. İhtiyaçlarınıza göre kendi geliştirdiğiniz programları da sisteme dahil edebilirsiniz. Bu yönüyle Kavram, klasik bir uygulama paketinden çok, kendi çalışma ortamınızı oluşturabileceğiniz bir platform olarak tasarlanmıştır.

**10 entegre program + genişletilebilir program sistemi.**

[Türkçe](#türkçe) · [English](#english)

<img width="3450" height="1880" alt="sh" src="https://github.com/user-attachments/assets/2f3a8157-ee17-4cf0-97b0-be832fb5480b" />

---

# Türkçe

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

# Kurulum

> **Not:** Linux Mint XFCE üzerinde kurulması önerilir.

Komutları Kavram klasöründe (`kavram.py`'nin yanında) çalıştırın. Her komut sistem paketlerini kurar, C++ motorlarını derler, programı **paketler** (`dist/` klasörü) ve başlatır. Paket, **kendi işletim sisteminde** üretilir. İlk kurulum internet ister ve 10–30 dakika sürebilir.

| İşletim sistemi | Komut | Oluşan paket |
| --- | --- | --- |
| **Linux** (dağıtımı kendisi tanır) | `bash baslat_linux.sh` | `dist/kavram/kavram` ve `.tar.gz` |
| Debian · Ubuntu · Mint · Pop!_OS · Kali | `bash kurulum_deb.txt` | aynısı |
| Arch · Manjaro · EndeavourOS | `bash kurulum_arch.txt` | aynısı |
| Fedora · AlmaLinux · Rocky | `bash kurulum_fedora.txt` | aynısı |
| openSUSE | `bash kurulum_opensuse.txt` | aynısı |
| Void | `bash kurulum_void.txt` | aynısı |
| **Windows 10 / 11** | `baslat_win.bat` dosyasına çift tıklayın | `dist\kavram\kavram.exe` ve `.zip` |
| **macOS 11+** | `baslat_mac.command` dosyasına çift tıklayın (veya `bash kurulum_mac.txt`) | `dist/Kavram.app`, `.dmg`, `.zip` |

> **Durum:** Linux'ta paket derlenip açıldığı doğrulandı. **Windows ve macOS deneysel:** kod ve betikler hazır, fakat gerçek bir Windows/Mac'te henüz denenmedi. Bir adım takılırsa çıktıyı *issue* olarak paylaşın. Fedora, openSUSE ve Void betikleri de kendi dağıtımlarında denenmedi.

Windows/macOS'ta kayıt (ekran, mikrofon, kamera) çalışıyor mu diye bakmak için kurulumdan sonra:

```bash
venv\Scripts\python kayit_testi.py      # Windows
./venv/bin/python kayit_testi.py        # macOS
```

Her program kendi klasöründe, işletim sistemine özel dosyalarıyla durur: `rec.py` (Linux), `rec_win.py` (Windows), `rec_mac.py` (macOS). Kavram çalıştığı sistemin dosyasını kendisi seçer.

<img width="1920" height="1049" alt="3" src="https://github.com/user-attachments/assets/0b8b71af-737a-4387-a516-77c0fa217e6c" />

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

---

## Lisans

GNU Genel Kamu Lisansı sürüm 3 veya (tercihinize bağlı) daha yenisi. Ayrıntı `kavram.py` dosyasının başındadır.

---

# English

**Kavram** is a free, open-source archive platform that brings educational and media work under one roof: text, drawing, sound, video, screen recording and notes in a single system. Content can be edited, linked, and archived in encrypted form as mind maps in **SPHERE**. You can also plug your own programs into it. **10 integrated programs + an extensible program system.**

| Program | Purpose |
| --- | --- |
| **SPHERE** | Home screen: encrypted mind-map archive (`.kitap` export) |
| **TEXT** | Text editing |
| **DRAWING** | Drawing and animation |
| **SOUND** | Audio editing and recording |
| **AI** | Artificial memory (question-answer packets with media) |
| **MEDIA** | Mixed audio + video archive / timeline |
| **REC** | Screen and audio recording |
| **COPY** | Notes |
| **FILTER** | Audio noise filtering |
| **CONVERTER** | Format conversion |

Hover over any button for **0.6 seconds** to see what it does. The full button reference for every editor is in the Turkish section above.

## Install

Run the command in the Kavram folder (next to `kavram.py`). It installs system packages, builds the C++ engines, **packages** the program into `dist/`, and starts it. Each package is built **on its own operating system**.

| System | Command | Output |
| --- | --- | --- |
| **Linux** (auto-detects distro) | `bash baslat_linux.sh` | `dist/kavram/kavram` + `.tar.gz` |
| Debian / Ubuntu / Mint / Kali | `bash kurulum_deb.txt` | same |
| Arch / Manjaro | `bash kurulum_arch.txt` | same |
| Fedora / AlmaLinux / Rocky | `bash kurulum_fedora.txt` | same |
| openSUSE | `bash kurulum_opensuse.txt` | same |
| Void | `bash kurulum_void.txt` | same |
| **Windows 10 / 11** | double-click `baslat_win.bat` | `dist\kavram\kavram.exe` + `.zip` |
| **macOS 11+** | double-click `baslat_mac.command` (or `bash kurulum_mac.txt`) | `dist/Kavram.app`, `.dmg`, `.zip` |

> **Status:** Linux is verified (package built and launched). **Windows and macOS are experimental** — scripts and code are ready but not yet validated on real machines. Please open an issue with the output if a step fails. Linux Mint XFCE is the recommended platform.

To check screen / microphone / camera capture on Windows or macOS after installing, run `venv\Scripts\python kayit_testi.py` (Windows) or `./venv/bin/python kayit_testi.py` (macOS).

## License

GNU General Public License version 3 or (at your option) any later version — see the header of `kavram.py`.
