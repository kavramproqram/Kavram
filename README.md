# Kavram

**''Kavram'', eğitim ve medya düzenleme süreçlerini tek bir çatı altında toplamayı amaçlayan özgür ve açık kaynak kodlu bir eğitim platformudur.**

<img width="3450" height="1880" alt="sh" src="https://github.com/user-attachments/assets/2f3a8157-ee17-4cf0-97b0-be832fb5480b" />
Platform, kullanıcıların farklı ihtiyaçlarına yanıt vermek üzere tasarlanmış çeşitli tümleşik proqramlardan oluşur:

| Program       | Ne işe yarar?            |
| ------------- | ------------------------ |
| **SPHERE**    | Ana ekran                |
| **TEXT**      | Metin düzenleme          |
| **DRAWING**   | Çizim                    |
| **SOUND**     | Ses düzenleme            |
| **AI**        | Yapay hafıza             |
| **MEDIA**     | Ses + video karma arşivi |
| **REC**       | Ekran ve ses kaydı       |
| **COPY**      | Not defteri              |
| **FILTER**    | Ses filtreleme           |
| **CONVERTER** | Format dönüştürme        |

---

# Kurulum

> **Not:** Linux Mint XFCE üzerinde kurulması önerilir.

<img width="1920" height="1049" alt="3" src="https://github.com/user-attachments/assets/0b8b71af-737a-4387-a516-77c0fa217e6c" />

---

# SPHERE

## Ana Ekran

Ana ekran, zihin haritalarının şifreli olarak arşivlendiği yerdir.

<img width="1918" height="1047" alt="s1" src="https://github.com/user-attachments/assets/4e6782df-e53e-4245-a70f-131ed9d720e4" />

<img width="1911" height="1042" alt="1" src="https://github.com/user-attachments/assets/c8e427be-2e96-4e5e-b066-6960165e98b7" />

## Üst Bardaki Butonlar

**1. File** — İçeri arşiv almak ve kare (dosya) eklemek için kullanılır.

**3 ve 4.** — Yapılan işlemleri geri almak için kullanılır.

**5. +** — Kare eklemek için kullanılır.

**6.** — Bağlantıların konum listesini açar.

**7. Terminal** — Terminal komutlarını kullanmak için açılır.

### Terminal Komutları

**1. `reset`**

Her şeyi tamamen siler.

**2. `ap resim konumu`**

Duvar kâğıdını değiştirmek için kullanılır.

Örnek:

```text
ap /home/lts/Pictures/resim4.png
```

**3. `isim program konumu`**

`Ctrl + Q` kısayolu ile açılan menünün alt kısmına bir program ekler.

Bu bölüm, yardımcı programlar için kullanılır.

Örnek:

```text
Zaman /home/lts/Kavram/Programlar/Zaman/Zaman
```

**4. `k isim program konumu`**

`Ctrl + Q` kısayolu ile açılan menünün üst kısmına bir program ekler.

Bu bölüm, ana programlar için kullanılır. Dosya eklemek de mümkündür.

Örnek:

```text
k Blender /home/lts/blender-5.2.0-linux-x64/blender
```

> **Önemli:** Kavram, bir tür işletim sistemi gibi çalıştığı için ana program kapatılırsa ona bağlı olan programların tamamı otomatik olarak kapanır.
>
> Örneğin Blender kapatılmadan önce dosyayı kaydetmenizi ister.
>
> Eğer Kavram programını kapatırsanız Blender hiçbir şey sormadan kapanır. Veri kaybı yaşanmaması için dosyalarınızı önceden yedekleyin.

**8. `/`**

Arka planda oluşan gridli yapıyı açıp kapatmak için kullanılır.

**9. Export**

**Sol tık:** XZ formatında bir dosya oluşturur. Dosya daha küçük olur ancak oluşturulması ve export edilmesi daha uzun sürer.

**Sağ tık:** GZ formatında kaydeder. Dosya, XZ'ye kıyasla daha büyük olur ancak dosya daha hızlı oluşturulur.

Oluşan dosya `.kitap` uzantısıyla şifreli bir şekilde kaydedilir.

**10. Sphere**

Bu buton, bütün programlarda üst barda en sağda farklı isimlerle bulunur.

`Ctrl + Q` kısayolu ile açılan menüyü açmak için kullanılır.

### Dikkat Edilmesi Gereken Komutlar

Bu program içinde özellikle dikkat edilmesi gereken 3 komut/işlem vardır:

**1. Dosyalarınızı yedekleyin.**

Veri kaybı ihtimali çok düşük olsa da sıfır değildir.

**2. `reset` komutu**

Terminalde `reset` komutu yazıldığında her şey silinir.

**3. `Ctrl + S`**

`Ctrl + S` kısayolu, Sphere (ana ekran) dışında bulunan 7 ana program için geçerlidir.

O anda açık olan programı yok eder ve ana ekrana geri döner. Hiçbir şeyi kaydetmez; yalnızca programı kapatır.

Hızlı kaydetme için her editörde **File** butonunun yanında bir ikon bulunur. Bu ikon Sphere için geçerli değildir.

Sphere içindeki bu ikonun görevi, o anda oluşturulan düzeni varsayılan hâle getirmektir. Böylece program yeniden açıldığında her şey aynı şekilde açılır.

---

# TEXT

## Metin Düzenleme Programı

<img width="1920" height="1049" alt="T1" src="https://github.com/user-attachments/assets/665de852-5ba9-4185-b21a-39a42a75a2bc" />

---

# DRAWING

## Çizim Programı

> **Not:** Animasyon oluşturmak istiyorsanız **Export** butonuna sağ tıklayın.

<img width="1920" height="1050" alt="d1" src="https://github.com/user-attachments/assets/f4d11e07-ac0c-4ff9-b1f0-672a7c87cf5c" />

---

# SOUND

## Ses Düzenleme Programı

<img width="1920" height="1047" alt="Ekran görüntüsü_2026-08-28_10-42-08" src="https://github.com/user-attachments/assets/33505066-7391-4be6-a0f7-0f3c17ae7406" />

---

# AI

## Yapay Hafıza
## Programın Amacı

**AI**, SQLite tabanlı dinamik veri/soru-cevap yönetimi, multimedya entegrasyonu (ses, görsel, video, harici dosya) ve özelleştirilmiş AI/Chat etkileşim arayüzü sunan bir masaüstü yazılımıdır. 

Temel amaçları şunlardır:
- **Sorular ve Yanıtlar (Paket Yönetimi):** Veritabanı üzerinde benzersiz soru kontrolü ile soru-cevap paketleri oluşturma, düzenleme ve silme.
- **Çoklu Medya Desteği:** Soru yanıtlarına çoklu ses (`.mp3`, `.wav`), resim (`.png`, `.jpg`), video (`.mp4`) ve harici dosya ekleri bağlama.
- **Sohbet ve Etkileşim Modu:** Kayıtlı soru-cevap verileri üzerinden arama yapma ve geçmiş modunda gezinme.
- **Lazy Loading ve Performans:** SQLite veritabanı yapısı ve önbellek yönetimi ile kaynak tüketimini optimize etme.

---

## Üst Bar Butonlarının İşlevleri

| Buton / Bileşen | Metin / Simge | İşlevi |
| :--- | :--- | :--- |
| **File** | File | Veritabanı veya medya dosyalarını içeri aktarmak / açmak için dosya seçim diyalogunu başlatır. |
| **Kaydet** | Save | Mevcut değişiklikleri, paketleri ve veritabanı güncellemelerini kaydeder. |
| **New** | New | Veri yönetimi panelinde yeni bir boş soru-cevap paketi oluşturur ve odaklanır. |
| **Chat** | Chat | Sohbet (etkileşim ve arama) panelini aktif görünüme getirir. |
| **Exit Fullscreen** | Exit Fullscreen | Aktif multimedya overlay veya tam ekran modundan çıkış yapar. |
| **Edit** | Edit | Veri yönetimi (SQLite soru-cevap paketleri) sayfasını aktif görünüme getirir. |
| **Sohbeti Temizle** | Clear | Sohbet ekranındaki mevcut mesaj balonlarını ve sohbet geçmişi görünümünü temizler. |
| **Font Seçici** | Sayısal Değer | Arayüzdeki metin boyutunu dinamik olarak değiştirir (tıklama, menü veya tekerlek ile). |
| **Temizle (AI/Klasör)** | S | Geçici `ai` çalışma klasörünü ve açık veri belleğini temizler. |
| **Export** | Export | Oluşturulan veri paketlerini ve bağlı medyayı dışa aktarır. |
| **Ai Modu** | Ai | Ana çekirdek modülleri veya AI editör modları arasında geçişi tetikler. |

---

# MEDIA

## Ses ve Videolardan Oluşan Karma Arşiv Programı  ()

<img width="1920" height="1049" alt="M" src="https://github.com/user-attachments/assets/2aa5206d-dedb-4256-b859-ffb58721ae99" />

---

# REC

## Ekran ve Ses Kaydetme Programı
Markdown

# Kavram - Media & Screen Recording Module

**Kavram**, Linux Mint (ve diğer Linux dağıtımları) üzerinde gelişmiş ekran/ses kaydı, segment tabanlı medya yönetimi ve klavye/fare (input) gösterimi sağlayan PyQt5 tabanlı modüler bir masaüstü uygulaması bileşenidir.

---

## Programın Amacı

Bu modülün temel amacı, ekran ve ses kaynaklarını yüksek performansla eşzamanlı veya bağımsız olarak kaydetmek, kayıt sürecini dinamik segmentlere ayırarak yönetmek ve video/ses oynatma ile filtreleme süreçlerini tek bir merkezden yürütmektir.

* **Esnek Kayıt Modları:** Sadece ekran (MKV), sadece ses (WAV) veya ekran ve ses bir arada (MKV) kayıt alabilme.
* **Segment Tabanlı Kayıt:** Uzun süreli kayıtları belirlenen sürelerde (20 sn - 3 dk) parçalara (segment) ayırarak veri kaybı riskini en aza indirme.
* **Yüzen (Floating) Zaman ve Input Göstergesi:** Ekran kaydı sırasında en üstte duran, Ctrl + Sol Tık ile taşınabilen süre ve basılan tuşları/fare komutlarını anlık gösteren bildirim pencereleri.
* **Ses Filtreleme ve Dışa Aktarma:** Dahili FFmpeg ve ses işleme hattı (noise reduce, EQ, compressor) desteği ile kayıtları filtreleyip tek bir dosyada birleştirerek dışa aktarma.
* **Dahili Medya Oynatıcı:** Kaydedilen veya harici olarak yüklenen `.mkv`, `.mp4`, `.rec` ve `.wav` dosyalarını uygulama içerisinden oynatma.

---

## Üst Bar Butonlarının İşlevleri

| Sembol / İsim | Açıklama / İşlev |
| :--- | :--- |
| **File** | Harici bir video (`.rec`, `.mp4`, `.mkv`) veya ses (`.wav`) dosyasını oynatıcıya yüklemek için dosya seçici penceresini açar. |
| **Camera** | Geliştirme aşamasında olan kamera modülü . |
| **Windows** | Ekran kaydı alıp alınmayacağını belirler. Aktifken buton rengi değişir. Sadece ses kaydı alınacaksa kapatılabilir. |
| **Sound** | Sistem/Mikrofon ses kaydının alınıp alınmayacağını belirler. EasyEffects ve varsayılan PulseAudio kaynaklarını otomatik algılar. |
| **I (Noise Filter)** | Gürültü engelleme ve ses filtreleme zincirini aktif/deaktif eder. Aktif olduğunda dışa aktarım sırasında gelişmiş ses temizleme uygulanır. |
| **S (Kurtarma/Denetim)** | Segment dosya yapısını ve kayıt durumunu kontrol ederek olası aksamaları doğrular ve kurtarma/düzenleme işlevini çalıştırır. |
| **Thickness (Sayı Butonu)** | Yüzen zaman/input penceresinin kalınlığını (30-50 px) ayarlar. <br>• **Fare Tekerleği:** Kalınlığı artırır/azaltır.<br>• **Sol Tık:** Yüzen pencereyi varsayılan konumuna sıfırlar.<br>• **Sağ Tık:** Yüzen pencerenin mevcut konumunu varsayılan yapar. |
| **/** | **Input Overlay Toggle:** Klavye tuş basımlarını ve fare tıklamalarını (ekranın üzerinde yüzen siyah panelde) gösteren mekanizmayı açar/kapatır. |
| **Z** | **Time Overlay Toggle:** Ekranın üstünde duran yüzen canlı kayıt süresi panelinin görünürlüğünü açar/kapatır. |
| **Süre Açılır Menüsü** | **Kayıt Limiti (Örn: 5 dk):** Belirlenen süreye ulaşıldığında kaydın otomatik olarak duraklatılmasını sağlar (1 dk - 30 dk arası). |
| **Segment Açılır Menüsü** | **Segment Süresi (Örn: 30 sn):** Kayıt yapılırken arka planda kaç saniyede bir yeni parça dosya (`s1.mkv`, `s2.mkv`...) oluşturulacağını belirler. |
| **Play / Pause** | Kaydı veya medya oynatmayı başlatır/duraklatır. (Global Kısayol: `Ctrl + M`) |
| **X** | Açık olan dosya oynatma çubuğunu kapatır ve oynatıcıyı sıfırlar. |
| **Segment X Menüsü** | O an bellekte/diskte biriken kayıt segmentlerini listeler. İstenen parçayı münferit olarak silme veya **Hepsi** seçeneğiyle tüm parçaları temizleme imkanı sunar. |
| **Export** | Kaydedilmiş tüm segment parçalarını sırasıyla birleştirir, isteğe bağlı ses filtresini uygular ve nihayi MKV/WAV dosyası olarak kaydeder. |
| **Rec** | Modül/Ana pencere görünüm geçişlerini sağlar. |
> **Not:** Eski bilgisayarlarda çalışması için tasarlanmıştır. Kullanırken dikkat edin; süre sınırı vardır.
>
> Her bilgisayarla uyumlu olmayabilir. Büyük dosyalar oluşturmadan önce test etmeniz tavsiye edilir.

<img width="1920" height="1045" alt="R" src="https://github.com/user-attachments/assets/bbb4c6c4-e8c5-41cf-9273-8ffed6543335" />

---

# COPY

## Not Defteri Programı

> **Not:** PDF ve Drawing'de üretilen `.pnf` dosyalarını, resimleri de not olarak paketlemek mümkündür.

<img width="1920" height="1043" alt="N" src="https://github.com/user-attachments/assets/34d80842-0917-4ae5-8d5c-5f28b30d7e00" />

---

# FILTER

## Ses Filtreleme Programı

> **Not:** Bu program 3 programla bağlantılıdır: **Sound, Media ve Rec.**
>
> Bu 3 programın üst barında **İ** ikonu bulunur. Bu ikonu aktif ederseniz ses kaydı aldığınızda dosya filtrelenir.

<img width="1920" height="1048" alt="F" src="https://github.com/user-attachments/assets/c6763870-86d7-4973-b307-0e94eecca578" />

---

# CONVERTER

## Dosya Format Değiştirme Programı

<img width="1920" height="1027" alt="C" src="https://github.com/user-attachments/assets/87a96bb1-d300-48c4-a062-9aaf4cf3e815" />

---

# Harici Programları Sisteme Dahil Etme

> **Not:** Kendi geliştirdiğiniz veya internetten indirdiğiniz programları sisteme dâhil etmek için Terminal'i kullanın.

<img width="1920" height="1049" alt="Z" src="https://github.com/user-attachments/assets/a569dba7-1714-42cd-8502-16d0bd917692" />

<img width="1920" height="1050" alt="bl" src="https://github.com/user-attachments/assets/2749222e-e76c-43ec-b58f-aa33c5370315" />





## 📦 Modüller ve Özellikleri

---

### 1. AI Editor (`---.txt` / `ai_editor.py`)

**Programın Amacı:**
SQLite tabanlı dinamik veri/soru-cevap yönetimi, multimedya entegrasyonu (ses, görsel, video, harici dosya) ve özelleştirilmiş AI/Chat etkileşim arayüzü sunar.

**Üst Bar Butonları:**

| Buton | Etiket | İşlev |
| :--- | :--- | :--- |
| **File** | `File` | `.ai` dosyasını veya JSON verilerini içe aktarır |
| **Save** | 🖫 | Mevcut `.ai` dosyasını üzerine kaydeder |
| **New** | `New` | Veri yönetimi panelinde yeni boş paket oluşturur |
| **Chat** | `Chat` | Sohbet panelini aktif görünüme getirir |
| **Exit Fullscreen** | `_` | Aktif multimedya overlay'den çıkış yapar |
| **Edit** | `Edit` | Veri yönetimi sayfasını aktif görünüme getirir |
| **Sohbeti Temizle** | ✕ | Sohbet mesajlarını ve geçmişi temizler |
| **Font Seçici** | Sayısal | Metin boyutunu dinamik değiştirir |
| **Temizle (AI/Klasör)** | `S` | `ai` çalışma klasörünü ve veri belleğini temizler |
| **Export** | `Export` | Veri paketlerini `.ai` formatında dışa aktarır |
| **Ai** | `Ai` | Ana çekirdek modülleri arasında geçiş yapar |

---

### 2. Drawing Editor (`Drawing_editor.py`)

**Programın Amacı:**
Katmanlı çizim, referans görsel yönetimi, gelişmiş fırça motoru ve video dışa aktarma desteği sunan profesyonel bir dijital çizim aracı.

**Üst Bar Butonları:**

| Buton | Etiket | İşlev |
| :--- | :--- | :--- |
| **File** | `File` | Veritabanı veya medya dosyalarını içe aktarır. **Sağ tık:** Referans görsel ekler |
| **Save** | 🖫 | Değişiklikleri ve veritabanı güncellemelerini kaydeder |
| **New** | `New` | Yeni boş soru-cevap paketi oluşturur |
| **Chat** | `Chat` | Sohbet panelini aktif görünüme getirir |
| **Exit Fullscreen** | `_` | Multimedya overlay'den çıkış yapar |
| **Edit** | `Edit` | Veri yönetimi sayfasını aktif görünüme getirir |
| **Sohbeti Temizle** | ✕ | Sohbet mesajlarını temizler |
| **Font Seçici** | Sayısal | Metin boyutunu dinamik değiştirir |
| **Temizle (AI/Klasör)** | `S` | `ai` çalışma klasörünü temizler |
| **Export** | `Export` | Veri paketlerini dışa aktarır |
| **Ai Modu** | `Ai` | AI editör modları arasında geçiş yapar |

---

### 3. Filtre (`filtre.py`)

**Programın Amacı:**
Gelişmiş spektral gürültü azaltma, akıllı VAD (Ses Aktivite Tespiti) ve çok katmanlı filtreleme motoru ile ses ve video dosyalarını işler.

**Üst Bar Butonları:**

| Buton | Etiket | İşlev |
| :--- | :--- | :--- |
| **File** | `File` | Ses veya video dosyası yükler |
| **:: (Profil Ekle)** | `::` | Gürültü profili ekler (maks. 8) |
| **/ (Düzenleme)** | `/` | Ses düzenleme panelini açar/kapatır |
| **Process** | `Process` | Aktif filtreleri dosyaya uygular |
| **Reset** | `Reset` | Profilleri varsayılana döndürür |
| **Play** | `Play` | 5 saniyelik önizlemeyi oynatır |
| **Müzik** | `Müzik` | Arka plan müziği seçer. **Sağ tık:** Kalıcı yapar |
| **Export** | `Export` | Filtrelenmiş ses/videoyu kaydeder |

---

### 4. Copya (`copya.py`)

**Programın Amacı:**
Notlar, görseller, PDF'ler, PNF projeleri ve metin dosyalarını tek bir çatı altında toplayan gelişmiş belge yönetim sistemi.

**Üst Bar Butonları:**

| Buton | Etiket | İşlev |
| :--- | :--- | :--- |
| **File** | `File` | `.copya` proje dosyası açar |
| **Save** | 🖫 | Projeyi kaydeder |
| **+** | `+` | Yeni boş not kartı ekler |
| **Galeri** | `Galeri` | Görsel/metin dosyalarıyla galeri kartı oluşturur |
| **Belge** | `Belge` | PDF veya PNF dosyası ile belge kartı oluşturur |
| **#1** | `#1` | Öğe numarasını gösterir, tık: öğe listesi |
| **I (Okuma)** | `I` | Otomatik kaydırma modunu açar/kapatır |
| **Hız** | `1.0` | Kaydırma hızını ayarlar |
| **Boyut** | `15` | Belge görüntüleme boyutunu ayarlar |
| **X (Sil)** | `X` | Aktif kartı siler |
| **_ (Küçült)** | `_` | Aktif kartı daraltır |
| **/ (Kopyala)** | `/` | Kart içeriğini panoya kopyalar |
| **Export** | `Export` | Projeyi `.copya` formatında dışa aktarır |
| **Copy** | `Copy` | Core switcher |

---

### 5. Camera Editor (`camera_editor.py`)

**Programın Amacı:**
Ekran ve ses kaydı, video/audio oynatma, gelişmiş filtreleme ve canlı input gösterimi sunan profesyonel kayıt aracı.

**Üst Bar Butonları:**

| Buton | Etiket | İşlev |
| :--- | :--- | :--- |
| **File** | `File` | Video veya ses dosyası açar |
| **Camera** | `Camera` | Kamera özelliği (geliştirme aşamasında) |
| **Windows** | `Windows` | Ekran kaydı modunu açar/kapatır |
| **Sound** | `Sound` | Ses kaydı modunu açar/kapatır |
| **I (Filtre)** | `I` | Gürültü filtresini açar/kapatır (kalıcı) |
| **S (Temizle)** | `S` | Kayıt klasörünü temizler ve ayarları sıfırlar |
| **Kalınlık** | `40` | Overlay kalınlığını ayarlar (30-50) |
| **/ (Input)** | `/` | Klavye/Mouse input gösterimini açar/kapatır |
| **Z (Overlay)** | `Z` | Yüzen zaman göstergesini gösterir/gizler |
| **Kayıt Süresi** | `5 dk` | Otomatik durdurma süresini ayarlar |
| **Segment Süresi** | `30 sn` | Segment bölme süresini ayarlar |
| **Play/Pause** | `Play` | Oynatmayı başlatır/duraklatır |
| **X (Kapat)** | `X` | Oynatma çubuğunu kapatır |
| **Segment Sayısı** | `Segment 0` | Segment menüsü (tek silme, hepsini silme) |
| **Export** | `Export` | Segmentleri birleştirip dışa aktarır |
| **Rec** | `Rec` | Core switcher |

---

### 6. Convert (`convert.py`)

**Programın Amacı:**
Ses, video, PDF ve görsel dosyalarını dönüştüren, düzenleyen ve birleştiren evrensel medya dönüştürücü.

**Üst Bar Butonları:**

| Buton | Etiket | İşlev |
| :--- | :--- | :--- |
| **File** | `File` | Dönüştürülecek dosyayı seçer |
| **Convert** | `Convert` | Seçili dosyayı ayarlarla dönüştürür |
| **Reset** | `Reset` | Tüm ayarları varsayılana döndürür |
| **Export** | `Export` | Dönüştürülen dosyayı kaydeder |

**Ayarlar Paneli (Sol - Ses):**

| Kontrol | İşlev |
| :--- | :--- |
| **Format** | Çıktı formatını seçer |
| **Frekans Değiştir** | Örnekleme frekansını değiştirir |
| **Ses Hızı** | Oynatma hızını ayarlar (0.10x - 4.00x) |
| **Ses Perdesi** | Ses tonunu ayarlar (-6 ila +6 semiton) |
| **Ses Efekti** | Normalleştir, Sıkıştır, Filtre, Fade, Faz Ters Çevir |

**Ayarlar Paneli (Sağ - Gelişmiş):**

| Kontrol | İşlev |
| :--- | :--- |
| **Kapak Resmi Seç** | Ses → Video dönüşümünde kapak resmi |
| **Video Renk Ters** | Video renklerini negatif yapar |
| **Video Gri Ton** | Videoyu siyah-beyaz yapar |
| **Video Ses Sil** | Videodaki orijinal sesi kaldırır |
| **Harici Ses Ekle** | Videoya harici ses dosyası ekler |
| **PDF Ters Çevir** | PDF renklerini ters çevirir |
| **PDF Gri Ton** | PDF sayfalarını gri ton yapar |
| **Resim Ters Çevir** | Görsel renklerini ters çevirir |
| **Resim Gri Ton** | Görseli siyah-beyaz yapar |
| **Resim Çözünürlük** | Görsel boyutunu ölçeklendirir |

---

### 7. Media Editor (`media_editor.py`)

**Programın Amacı:**
Video ve ses dosyalarını zaman çizelgesi üzerinde düzenleme, kesme, birleştirme ve dışa aktarma.

**Üst Bar Butonları:**

| Buton | Etiket | İşlev |
| :--- | :--- | :--- |
| **File** | `File` | Medya dosyaları veya `.media` proje arşivi açar |
| **Save** | 🖫 | Hızlı kaydet (mevcut projeyi üzerine yazar) |
| **Undo** | ↩️ | Son işlemi geri alır (Ctrl+Z) |
| **Redo** | ↪️ | Geri alınan işlemi yeniden yapar |
| **Play** | `Play` | Aktif segmenti oynatır/duraklatır |
| **/ (Sequence)** | `/` | Sıralı oynatma modunu açar/kapatır |
| **Cut** | `Cut` | Aktif segmenti mevcut konumdan keser |
| **Delete** | `Delete` | Seçili segmenti siler |
| **Camera** | `Camera` | Kamera modu (geliştirme aşamasında) |
| **Sound** | `Sound` | Ses kaydını başlatır/durdurur |
| **I (Filtre)** | `I` | Gürültü filtresini açar/kapatır (kalıcı) |
| **S (Temizle)** | `S` | `medya_cut` klasörünü temizler ve sıfırlar |
| **Arama Aralığı** | `2s` | Fare tekerleği sarım miktarı |
| **Oynatma Hızı** | `1` | Oynatma hızını değiştirir |
| **Süre Göstergesi** | `00:00:00.0` | Mevcut konumu gösterir |
| **Export** | `Export` | **Sol tık:** `.media` arşiv. **Sağ tık:** MKV render |
| **Media** | `Media` | Core switcher |

---

### 8. Zaman (`Zaman.py`)

**Programın Amacı:**
Pomodoro zamanlayıcı, görev planlayıcı, notlar, takvim, ömür sayacı, ekran ayarları ve alışkanlık takibi.

**Mod Seçici (Üst Bar):**

| Mod | Adı | İşlev |
| :--- | :--- | :--- |
| **Mod 0** | Pomodoro | Çalışma/mola zamanlayıcı, sesli alarm, görev bağlama |
| **Mod 1** | Görev / Planlayıcı | Görev yönetimi, öncelik, Pomodoro sayacı |
| **Mod 2** | Notlar | Not ekleme, düzenleme, silme, arama |
| **Mod 3** | Normal Takvim | Haftalık ay takvimi, görev entegrasyonu |
| **Mod 4** | Rakamlı Takvim | Sade sayısal takvim (1-7) |
| **Mod 5** | Sekizli Takvim | 40 günlük bölümler, 3 zaman dilimi |
| **Mod 6** | Ömür Sayacı | Belirlenen yıl hedefine geri sayım |
| **Mod 7** | Tarih Ayarı | Referans saat ayarı, tüm modları senkronize |
| **Mod 8** | Ekran Ayarı | Mavi ışık filtresi, RGB, parlaklık, gri mod |
| **Mod 9** | Alışkanlık Takibi | 40 günlük alışkanlık takibi |

---

### 9. Sound Editor (`sound_GUI.py`)

**Programın Amacı:**
Dalga formu görüntüleme, kesme, silme, kayıt, filtreleme ve metin entegrasyonu sunan profesyonel ses düzenleyici.

**Üst Bar Butonları:**

| Buton | Etiket | İşlev |
| :--- | :--- | :--- |
| **File** | `File` | WAV veya `.sound` paket dosyası açar |
| **Save** | 🖫 | Hızlı kaydet (`.sound` ise üzerine yazar) |
| **Undo** | ↩️ | Son işlemi geri alır (Ctrl+Z) |
| **Redo** | ↪️ | Geri alınan işlemi yeniden yapar |
| **Cut** | `Cut` | Oynatma konumuna split noktası ekler |
| **:: (Kalınlık Sil)** | `::` | Seçili alanın kalınlığındaki tüm sessiz bölgeleri siler |
| **Delete** | `Delete` | Seçili segmenti siler |
| **Play** | `Play` | Ses oynatmayı başlatır/duraklatır |
| **Record** | `Record` | Mikrofon kaydını başlatır/durdurur |
| **I (Filtre)** | `I` | Gürültü filtresini açar/kapatır (kalıcı) |
| **Dalga Ölçek** | `1` | Dalga formu genişliğini ayarlar (1-7) |
| **Hız** | `1x` | Oynatma hızını değiştirir |
| **Scroll Step** | `5s` | Fare tekerleği kaydırma adımı |
| **/ (Panel)** | `/` | Geçici metin panelini açar/kapatır |
| **O (Hizalama)** | `O` | Metin hizalamasını Ortala/Sola Yasla |
| **Font Boyutu** | `14` | Metin font boyutunu ayarlar |
| **Export** | `Export` | **Sol tık:** WAV. **Sağ tık:** `.sound` paketi |
| **Sound** | `Sound` | Core switcher |

---

### 10. Text Editor (`text_editor.py`)

**Programın Amacı:**
Sembol paneli, terminal komutları, akıllı otomatik kaydırma ve gelişmiş metin işleme özellikleri sunan metin düzenleyici.

**Üst Bar Butonları:**

| Buton | Etiket | İşlev |
| :--- | :--- | :--- |
| **File** | `File` | `.txr`, `.txt`, `.md`, `.log` dosyalarını açar |
| **Save** | 🖫 | Hızlı kaydet (mevcut dosyaya kaydeder) |
| **Undo** | ↩️ | Son işlemi geri alır (Ctrl+Z) |
| **Redo** | ↪️ | Geri alınan işlemi yeniden yapar |
| **Font Boyutu** | `15` | Metin font boyutunu ayarlar |
| **/ (Panel)** | `/` | Sembol panelini açar/kapatır |
| **I (Okuma)** | `I` | Otomatik kaydırma modunu açar/kapatır |
| **Hız Göstergesi** | `1.0` | Kaydırma hızını ayarlar |
| **Terminal** | `Terminal` | Terminal penceresini açar |
| **Line** | `Line: 0` | Mevcut satır sayısını gösterir |
| **Arama Kutusu** | `Ara...` | Metin içinde arama yapar |
| **🔍 / ⬆ / ⬇** | - | Arama ve eşleşme gezinme |
| **Export** | `Export` | Metni `.txr` formatında dışa aktarır |
| **Text** | `Text` | Core switcher |

**Sembol Paneli Özellikleri:**

| Kontrol | İşlev |
| :--- | :--- |
| **. ^ (Dot)** | Enter çift tıklama ile otomatik nokta |
| **A (Caps)** | Satır başında otomatik büyük harf |
| **O (Center)** | Metin hizalamasını değiştirir |
| **@ (Nav)** | Ok tuşları ile sembol panelinde gezinme |
| **+ (Ekle)** | Özel sembol ekleme |

---
