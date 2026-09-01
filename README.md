# Kavram

**''Kavram'', eğitim ve medya düzenleme süreçlerini tek bir çatı altında toplamayı amaçlayan özgür ve açık kaynak kodlu bir arşiv platformudur.**

<img width="3450" height="1880" alt="sh" src="https://github.com/user-attachments/assets/2f3a8157-ee17-4cf0-97b0-be832fb5480b" />
Platform, kullanıcıların farklı ihtiyaçlarına yanıt vermek üzere tasarlanmış çeşitli tümleşik programlardan oluşur:

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

<img width="1920" height="1047" alt="sphere" src="https://github.com/user-attachments/assets/bccf70d7-1060-4ec4-a2be-36493d3fe0f6" />

## Butonlarının İşlevleri

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
---

# Harici Programları Sisteme Dahil Etme
---

**3. `isim program konumu`**

`Ctrl + Q` kısayolu ile açılan menünün alt kısmına bir program ekler.

Bu bölüm, yardımcı programlar için kullanılır.

Örnek:

```text
Zaman /home/lts/Kavram/Programlar/Zaman/Zaman
```
<img width="1920" height="1049" alt="Z" src="https://github.com/user-attachments/assets/a569dba7-1714-42cd-8502-16d0bd917692" />

**4. `k isim program konumu`**

`Ctrl + Q` kısayolu ile açılan menünün üst kısmına bir program ekler.

Bu bölüm, ana programlar için kullanılır. Dosya eklemek de mümkündür.

Örnek:

```text
k Blender /home/lts/blender-5.2.0-linux-x64/blender
```
<img width="1920" height="1050" alt="bl" src="https://github.com/user-attachments/assets/2749222e-e76c-43ec-b58f-aa33c5370315" />


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

Bu programda özellikle dikkat edilmesi gereken 3 komut/işlem vardır:

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

## Programın Amacı

**Text**, kullanıcıların zengin metin belgeleri oluşturmasını, biçimlendirmesini, dosyalar üzerinde temel metin işlemlerini gerçekleştirmesini ve not/kod bloklarını organize etmesini sağlayan PyQt5 tabanlı bir metin düzenleme platformudur.

---
<img width="1920" height="1049" alt="T1" src="https://github.com/user-attachments/assets/665de852-5ba9-4185-b21a-39a42a75a2bc" />

## Butonlarının İşlevleri

| Buton  | İşlevi |
| :--- | :--- |
| **File** | Dosya açma ve içeri aktarma diyalogunu başlatır. |
| **Kaydet (Save)** | Aktif metin belgesindeki değişiklikleri ve güncellemeleri kaydeder. |
| **Geri Al / Yinele (Undo / Redo)** | Düzenleme geçmişindeki adımları geri alır veya yineler. |
| **Font Seçici** | Arayüzdeki metin boyutunu dinamik olarak değiştirir. |
| **Terminal** | Özel silme komutlarını (örneğin dil veya karakter gruplarını silme) çalıştırmayı sağlar. |
| **Auto Scroll / Read Mode** | Belirlenen hızda otomatik kaydırma (okuma) modunu tetikler. |
| **Arama ve Eşleşme Butonları** | Metin içinde arama yapar, bulunan sonuçlar arasında ileri/geri gezinir. |
| **Export** | Oluşturulan belgeleri dışa aktarır. |
| **Text** | Bu buton bütün eses proqramlarda var proqram ismini gösterir ve ctrl +q kısa yolunu tetikler. |


---

# DRAWING

## Programın Amacı
Çizim ve animasyon.  
---
<img width="1920" height="1050" alt="d1" src="https://github.com/user-attachments/assets/f4d11e07-ac0c-4ff9-b1f0-672a7c87cf5c" />

---
## Butonlarının İşlevleri
---

| Buton Adı | Sol Tık İşlevi | Sağ Tık İşlevi |
| :--- | :--- | :--- |
| **File** | Görsel veya proje dosyası içe aktar. | Referans görsel ekle. |
| **Kaydet** | Projeyi kaydeder. | — |
| **Sayfa Numarası** | Sayfa menüsünü açar. | — |
| **+** | Yeni sayfa ekler. | — |
| **-** | Mevcut sayfayı siler. | — |
| **Geri Al** | Son işlemi geri alır. | — |
| **Yinele** | Geri alınan işlemi yineler. | — |
| **Kalem Stili** | Fırça stilini değiştirir. | — |
| **O** | Gezinme modunu açar/kapatır. | Tuval boyutu/çözünürlük diyaloğunu açar. |
| **G** | Referans görseli göster/gizle. | Referans saydamlık ve katman konumu menüsü. |
| **Mix Açısı** | Karışım açısı menüsünü açar. | Karışım modu menüsünü açar. |
| **Color** | Renk seçimi menüsünü açar. | — |
| **Eraser** | Silgi modunu açar/kapatır. | Arka plan rengini değiştirir. |
| **R:** | Fırça/silgi boyutu menüsünü açar. | — |
| **Çizim** | Katman menüsünü açar. | — |
| **#** | Aktif katmanı en üstte sabitle. | — |
| **lm** | Lazy Mouse modunu açar/kapatır. | Lazy Mouse ayar menüsünü açar. |
| **/** | Basınç hassasiyetini açar/kapatır. | — |
| **» «** | Dikey ayna modunu açar/kapatır. | Yatay ayna modunu açar/kapatır. |
| **Export** | Dışa aktarım diyaloğunu açar. | Gelişmiş dışa aktarım (FPS) menüsü. |
| **Drawing** | Bu buton bütün eses proqramlarda var proqram ismini gösterir ve ctrl +q kısa yolunu tetikler. | — |


---

# SOUND
## Programın Amacı
Ses düzenleme programı
---

<img width="1920" height="1047" alt="Ekran görüntüsü_2026-08-28_10-42-08" src="https://github.com/user-attachments/assets/33505066-7391-4be6-a0f7-0f3c17ae7406" />

---

## Butonlarının İşlevleri

---


| Buton Adı | Sol Tık İşlevi (`Left Click`) | Sağ Tık İşlevi (`Right Click`) |
| :--- | :--- | :--- |
| **File** | Ses dosyalarını (`.wav`) veya `.sound` paketini içe aktarır. | — |
| **Kaydet (disk ikonu)** | Geçerli sesi veya `.sound` paketini kaydeder. | — |
| **Geri Al** | Son işlemi geri alır (`Ctrl+Z`). | — |
| **Yinele** | Geri alınan işlemi yineler (`Ctrl+Shift+Z` veya `Ctrl+Y`). | — |
| **Cut** | Oynatma başlığının bulunduğu konuma kesme noktası ekler. | — |
| **`::`** | Seçili alanın kalınlığındaki (ses düzeyi) tüm boşlukları otomatik siler. | — |
| **Delete** | Seçili ses bölümlerini siler. | — |
| **Play** | Oynatmayı başlatır / duraklatır. | — |
| **Record** | Mikrofon kaydını başlatır / durdurur. | — |
| **I** | Kayıt sonrası filtreleri açar/kapatır (kalıcı ayar). | — |
| **Dalga Ölçeği (rakam)** | Dalga formu genişliğini ayarlar (1–7 arası). | — |
| **Hız (`Speed`)** | Oynatma hızını değiştirir (`0.1x – 3x`). | — |
| **Kaydırma Adımı** | Fare tekerleği ile kaydırma adımını ayarlar (`0.1s – 30s`). | — |
| **`/`** | Geçici metin panelini açar / kapatır. | — |
| **O** | Paneldeki metni ortalar / sola yaslar. | — |
| **Yazı Boyutu (rakam)** | Paneldeki yazı boyutunu ayarlar (tekerlek ile de değişir). | — |
| **Export** | Sesi `WAV` dosyası olarak dışa aktarır. | Sesi metin ve ayarlarla birlikte `.sound` paketi olarak dışa aktarır. |
| **Sound** | Bu buton bütün eses proqramlarda var proqram ismini gösterir ve ctrl +q kısa yolunu tetikler. | — |

---

# AI

## Yapay Hafıza
## Programın Amacı
<img width="1920" height="1043" alt="ai" src="https://github.com/user-attachments/assets/63637946-2309-4697-ba3b-3ac3395fff04" />

**AI**, SQLite tabanlı dinamik veri/soru-cevap yönetimi, multimedya entegrasyonu (ses, görsel, video, harici dosya) ve özelleştirilmiş AI/Chat etkileşim arayüzü sunan bir masaüstü yazılımıdır. 

Temel amaçları şunlardır:
- **Sorular ve Yanıtlar (Paket Yönetimi):** Veritabanı üzerinde benzersiz soru kontrolü ile soru-cevap paketleri oluşturma, düzenleme ve silme.
- **Çoklu Medya Desteği:** Soru yanıtlarına çoklu ses (`.mp3`, `.wav`), resim (`.png`, `.jpg`), video (`.mp4`) ve harici dosya ekleri bağlama.
- **Sohbet ve Etkileşim Modu:** Kayıtlı soru-cevap verileri üzerinden arama yapma ve geçmiş modunda gezinme.
- **Lazy Loading ve Performans:** SQLite veritabanı yapısı ve önbellek yönetimi ile kaynak tüketimini optimize etme.

---

## Butonlarının İşlevleri
---

| Buton / Bileşen | Metin / Simge | İşlevi |
| :--- | :--- | :--- |
| **File** | File | Veritabanı veya medya dosyalarını içeri aktarmak / açmak için dosya seçim diyalogunu başlatır. |
| **Kaydet** | Save | Mevcut değişiklikleri, paketleri ve veritabanı güncellemelerini kaydeder. |
| **New** | New | Veri yönetimi panelinde yeni bir boş soru-cevap paketi oluşturur ve odaklanır. |
| **Chat** | Chat | Sohbet (etkileşim ve arama) panelini aktif görünüme getirir. |
| **Exit Fullscreen** | _ | Aktif multimedya overlay veya tam ekran modundan çıkış yapar. |
| **Edit** | Edit | Veri yönetimi (SQLite soru-cevap paketleri) sayfasını aktif görünüme getirir. |
| **Sohbeti Temizle** | X | Sohbet ekranındaki mevcut mesaj balonlarını ve sohbet geçmişi görünümünü temizler. |
| **Font Seçici** | Sayısal Değer | Arayüzdeki metin boyutunu dinamik olarak değiştirir (tıklama, menü veya tekerlek ile). |
| **Temizle (AI/Klasör)** | S | Geçici `ai` çalışma klasörünü ve açık veri belleğini temizler. |
| **Export** | Export | Oluşturulan veri paketlerini ve bağlı medyayı dışa aktarır. |
| **Ai Modu** | Ai | Bu buton bütün eses proqramlarda var proqram ismini gösterir ve ctrl +q kısa yolunu tetikler. |


> **Not:** Cevap olarak ses, video ve resimleri eklemek mümkündür.

---

# MEDIA

## Ses ve Videolardan Oluşan Karma Arşiv Programı
---
<img width="1920" height="1049" alt="M" src="https://github.com/user-attachments/assets/2aa5206d-dedb-4256-b859-ffb58721ae99" />

---

## Butonlarının İşlevleri

---

| Buton Adı | Sol Tık İşlevi (`Left Click`) | Sağ Tık İşlevi (`Right Click`) |
| :--- | :--- | :--- |
| **File** | Medya dosyalarını (video, ses, `.media` arşivi) içe aktarır. | — |
| **Kaydet (disk ikonu)** | Mevcut projeyi hızlıca kaydeder (daha önce kaydedildiyse üzerine yazar, değilse farklı kaydet açar). | — |
| **Geri Al** | Son işlemi geri alır (`Ctrl+Z`). | — |
| **Yinele** | Geri alınan işlemi yineler (`Ctrl+Shift+Z`). | — |
| **Play** | Seçili medya segmentinin oynatmasını başlatır / duraklatır. | — |
| **`/`** | Sıralı oynatma modunu açar/kapatır (segmentler arası otomatik geçiş). | — |
| **Cut** | Aktif segmenti, oynatma başlığının bulunduğu konumdan iki parçaya böler (keser). | — |
| **Delete** | Zaman çizelgesinde seçili olan segmenti siler. | — |
| **Camera** | Kamerayı açar (geliştirme aşamasındadır). | — |
| **Sound** | Mikrofon ile ses kaydını başlatır / durdurur. | — |
| **`I`** | Gürültü filtreleme özelliğini açar/kapatır (kalıcı ayardır). | — |
| **`S`** | `medya_cut` çalışma klasörünü temizler ve zaman çizelgesini tamamen sıfırlar. | — |
| **Seek Aralığı (Açılır Kutu)** | Fare tekerleği ile ileri/geri sarma veya atlama adımını ayarlar (örn. 2s, 5s, 1dk). | — |
| **Oynatma Hızı (Açılır Kutu)** | Medya oynatma hızını değiştirir (örn. 0.5x, 1x, 2x). | — |
| **Export** | Zaman çizelgesindeki tüm segmentleri `.media` arşiv dosyası olarak dışa aktarır (proje olarak kaydeder). | Tüm zaman çizelgesini tek bir `.mkv` video dosyası olarak render eder ve dışa aktarır. |
| **Media** | Ana uygulamaya (`Kavram`) geçiş yapar. | — |


# REC

## Ekran ve Ses Kaydetme Programı

### Kavram - Media & Screen Recording Module

**Kavram**, Linux Mint (ve diğer Linux dağıtımları) üzerinde gelişmiş ekran/ses kaydı, segment tabanlı medya yönetimi ve klavye/fare (input) gösterimi sağlayan PyQt5 tabanlı modüler bir masaüstü uygulaması bileşenidir.

---

## Programın Amacı

Bu programın temel amacı, ekran ve ses kaydetmektir .

<img width="1918" height="1046" alt="r1" src="https://github.com/user-attachments/assets/9e91a992-8da1-4b17-b614-d4e0e4f235fa" />

---

## Butonlarının İşlevleri
---

| Sembol / İsim | Açıklama / İşlev |
| :--- | :--- |
| **File** | Harici bir video (`.rec`, `.mp4`, `.mkv`) veya ses (`.wav`) dosyasını oynatıcıya yüklemek için dosya seçici penceresini açar. |
| **Camera** | Geliştirme aşamasında olan kamera modülü . |
| **Windows** | Ekran kaydı alıp alınmayacağını belirler. Aktifken buton rengi değişir. Sadece ses kaydı alınacaksa kapatılabilir. |
| **Sound** | Sistem/Mikrofon ses kaydının alınıp alınmayacağını belirler. EasyEffects ve varsayılan PulseAudio kaynaklarını otomatik algılar. |
| **I (Noise Filter)** | Gürültü engelleme ve ses filtreleme zincirini aktif/deaktif eder. Aktif olduğunda dışa aktarım sırasında gelişmiş ses temizleme uygulanır. |
| **S (Sil)** | Her şeyi siler ve kapatır. |
| **Thickness (Sayı Butonu)** | Yüzen zaman/input penceresinin kalınlığını (30-50 px) ayarlar. <br>• **Fare Tekerleği:** Kalınlığı artırır/azaltır.<br>• **Sol Tık:** Yüzen pencereyi varsayılan konumuna sıfırlar.<br>• **Sağ Tık:** Yüzen pencerenin mevcut konumunu varsayılan yapar. |
| **/** | **Input Overlay Toggle:** Klavye tuş basımlarını ve fare tıklamalarını (ekranın üzerinde yüzen siyah panelde) gösteren mekanizmayı açar/kapatır. |
| **Z** | **Time Overlay Toggle:** Ekranın üstünde duran yüzen canlı kayıt süresi panelinin görünürlüğünü açar/kapatır. |
| **Süre Açılır Menüsü** | **Kayıt Limiti (Örn: 5 dk):** Belirlenen süreye ulaşıldığında kaydın otomatik olarak duraklatılmasını sağlar (1 dk - 30 dk arası). |
| **Segment Açılır Menüsü** | **Segment Süresi (Örn: 30 sn):** Kayıt yapılırken arka planda kaç saniyede bir yeni parça dosya (`s1.mkv`, `s2.mkv`...) oluşturulacağını belirler. |
| **Play / Pause** | Kaydı veya medya oynatmayı başlatır/duraklatır. (Global Kısayol: `Ctrl + M`) |
| **X** | Açık olan dosya oynatma çubuğunu kapatır ve oynatıcıyı sıfırlar. |
| **Segment X Menüsü** | O an bellekte/diskte biriken kayıt segmentlerini listeler. İstenen parçayı münferit olarak silme veya **Hepsi** seçeneğiyle tüm parçaları temizleme imkânı sunar. |
| **Export** | Kaydedilmiş tüm segment parçalarını sırasıyla birleştirir, isteğe bağlı ses filtresini uygular ve nihai MKV/WAV dosyası olarak kaydeder. |
| **Rec** | Bu buton bütün eses proqramlarda var proqram ismini gösterir ve ctrl +q kısa yolunu tetikler.. |

> **Not:** Eski bilgisayarlarda çalışması için tasarlanmıştır. Kullanırken dikkat edin; süre sınırı vardır.
>
> Her bilgisayarla uyumlu olmayabilir. Büyük dosyalar oluşturmadan önce test etmeniz tavsiye edilir.

<img width="1920" height="1045" alt="R" src="https://github.com/user-attachments/assets/bbb4c6c4-e8c5-41cf-9273-8ffed6543335" />

---

# COPY
## Programın Amacı
Not defteri programı
---
<img width="1920" height="1043" alt="N" src="https://github.com/user-attachments/assets/34d80842-0917-4ae5-8d5c-5f28b30d7e00" />


---
## Butonlarının İşlevleri
---

| Buton Adı | Sol Tık İşlevi (`Left Click`) |
| :--- | :--- |
| **File** | `.copya` proje dosyasını açar. |
| **Kaydet (disk ikonu)** | Geçerli projeyi kaydeder (eğer dosya yoksa farklı kaydet açar). |
| **`+`** | Yeni bir boş not ekler. |
| **Galeri** | Görseller, `.txt` ve `.txr` metin dosyalarını seçip mevcut veya yeni bir galeri notu olarak ekler. |
| **Belge** | `PDF` veya `PNF` (`Drawing`) dosyasını seçip sayfa sayfa galeri notu olarak içe aktarır. |
| **`#` (sayfa numarası)** | Genişletilmiş galerideki öğeler arasında gezinmek için menü açar. |
| **`I`** | Otomatik kaydırma (okuma modu) başlatır/durdurur. |
| **Hız (rakam)** | Otomatik kaydırma hızını ayarlamak için menü açar. |
| **Boyut (rakam)** | Belge modunda görüntülenen sayfanın boyutunu ayarlar. |
| **`X`** | Aktif olarak genişletilmiş notu siler. |
| **`_` (alt çizgi)** | Genişletilmiş notu küçültür (kapatır). |
| **`/` (eğik çizgi)** | Aktif notun içeriğini panoya kopyalar (resimlerde dosya yolları, metinlerde düz metin). |
| **Export** | Mevcut projeyi `.copya` arşivi olarak dışa aktarır. |
| **Copy** | Bu buton bütün eses proqramlarda var proqram ismini gösterir ve ctrl +q kısa yolunu tetikler. |


---

# FILTER
## Programın Amacı
Ses Filtreleme Programı
---

<img width="1920" height="1048" alt="F" src="https://github.com/user-attachments/assets/c6763870-86d7-4973-b307-0e94eecca578" />


---
## Butonlarının İşlevleri
---

| Kontrol Adı | Türü | Sol Tık / Etkileşim İşlevi (`Left Click / Interaction`) |
| :--- | :--- | :--- |
| **File** | Buton | Dönüştürülecek kaynak dosyayı (ses, video, PDF, resim) seçmek için dosya açma diyaloğunu açar. |
| **Convert** | Buton | Seçilen dosyayı, aşağıda yapılan tüm ayarlara göre dönüştürme işlemini başlatır. |
| **Reset** | Buton | Tüm dönüştürme ayarlarını (format, hız, efekt, filtreler vb.) varsayılan değerlerine sıfırlar. |
| **Export** | Buton | Dönüştürme sonucu oluşan çıktı dosyasını, kullanıcının seçtiği konuma kaydeder (kopyalar). |
| **Format (`Export Format`)** | Açılır Kutu (`ComboBox`) | Dönüştürme sonrası oluşacak dosyanın uzantısını/formatını belirler (örn: `.wav`, `.mp3`, `.mp4`, `.pdf`, `.jpg`). |
| **Frekans Değiştir (`Frequency`)** | Açılır Kutu (`ComboBox`) | Ses örnekleme frekansını değiştirme özelliğini açar (`Açık`) veya kapatır (`Kapalı`). |
| **Yeni Frekans Hz** | Metin Girişi (`LineEdit`) | Frekans değiştirme aktifken, hedef örnekleme frekansını (Hz cinsinden) girilen değere ayarlar. |
| **Ses Hızı (`Speed`)** | Açılır Kutu (`ComboBox`) | Sesin oynatma/dönüştürme hızını ayarlar (`0.10x ile 4.0x arası`). |
| **Ses Perdesi (`Pitch`)** | Açılır Kutu (`ComboBox`) | Sesin perdesini yükseltir (eksi ton) veya düşürür (artı ton) (`-6 Ton ile +6 Ton arası`). |
| **Ses Efekti** | Açılır Kutu (`ComboBox`) | Sese uygulanacak özel efekti seçer (`Normalleştir`, `Sıkıştır`, `Filtre`, `Fade`, `Kaydırma` vb.). |
| **Kapak Resmi Seç** | Buton | Sesi videoya dönüştürürken (ses+resim->video) kullanılacak kapak resmini seçmek için diyalog açar. |
| **Video Renkleri Ters Çevir** | Açılır Kutu (`ComboBox`) | Video çıktısının renklerini negatifine çevirir (`Evet` seçiliyse). |
| **Video Gri Ton (`Grayscale`)** | Açılır Kutu (`ComboBox`) | Video çıktısını siyah-beyaz (gri tonlamalı) yapar (`Evet` seçiliyse). |
| **Video Sesini Tamamen Sil** | Açılır Kutu (`ComboBox`) | Video dosyasındaki orijinal ses kanallarını tamamen kaldırır (`Evet` seçiliyse). |
| **Harici Ses Ekle (`Sync`)** | Buton | Videoya ana ses olarak eklenecek harici bir ses dosyası seçmek için diyalog açar. |
| **PDF Ters Çevir** | Açılır Kutu (`ComboBox`) | PDF sayfalarının renklerini negatifine çevirir (`Evet` seçiliyse). |
| **PDF Gri Ton** | Açılır Kutu (`ComboBox`) | PDF sayfalarını siyah-beyaz (gri tonlamalı) yapar (`Evet` seçiliyse). |
| **Resim Ters Çevir** | Açılır Kutu (`ComboBox`) | Resim çıktısının renklerini negatifine çevirir (`Evet` seçiliyse). |
| **Resim Gri Ton** | Açılır Kutu (`ComboBox`) | Resim çıktısını siyah-beyaz (gri tonlamalı) yapar (`Evet` seçiliyse). |
| **Resim Çözünürlüğü** | Açılır Kutu (`ComboBox`) | Resim çıktısının ölçek oranını ayarlar (`-5 = %25 küçült, 0 = Orijinal, +5 = %250 büyüt`). |


> **Not:** Bu program 3 programla bağlantılıdır: **Sound, Media ve Rec.**
>
> Bu 3 programın üst barında **İ** ikonu bulunur. Bu ikonu aktif ederseniz ses kaydı aldığınızda dosya filtrelenir.
---

# CONVERTER
## Programın Amacı
Dosya Format Değiştirme Programı
---
<img width="1920" height="1027" alt="C" src="https://github.com/user-attachments/assets/87a96bb1-d300-48c4-a062-9aaf4cf3e815" />


---
## Butonlarının İşlevleri
---


| Kontrol Adı | Türü | Sol Tık / Etkileşim İşlevi (`Left Click / Interaction`) |
| :--- | :--- | :--- |
| **File** | Buton | Dönüştürülecek kaynak dosyayı (ses, video, PDF, resim) seçmek için dosya açma diyaloğunu açar. |
| **Convert** | Buton | Seçilen dosyayı, aşağıda yapılan tüm ayarlara göre dönüştürme işlemini başlatır. |
| **Reset** | Buton | Tüm dönüştürme ayarlarını (format, hız, efekt, filtreler vb.) varsayılan değerlerine sıfırlar. |
| **Export** | Buton | Dönüştürme sonucu oluşan çıktı dosyasını, kullanıcının seçtiği konuma kaydeder (kopyalar). |
| **Format (`Export Format`)** | Açılır Kutu (`ComboBox`) | Dönüştürme sonrası oluşacak dosyanın uzantısını/formatını belirler (örn: `.wav`, `.mp3`, `.mp4`, `.pdf`, `.jpg`). |
| **Frekans Değiştir (`Frequency`)** | Açılır Kutu (`ComboBox`) | Ses örnekleme frekansını değiştirme özelliğini açar (`Açık`) veya kapatır (`Kapalı`). |
| **Yeni Frekans Hz** | Metin Girişi (`LineEdit`) | Frekans değiştirme aktifken, hedef örnekleme frekansını (Hz cinsinden) girilen değere ayarlar. |
| **Ses Hızı (`Speed`)** | Açılır Kutu (`ComboBox`) | Sesin oynatma/dönüştürme hızını ayarlar (`0.10x ile 4.0x arası`). |
| **Ses Perdesi (`Pitch`)** | Açılır Kutu (`ComboBox`) | Sesin perdesini yükseltir (eksi ton) veya düşürür (artı ton) (`-6 Ton ile +6 Ton arası`). |
| **Ses Efekti** | Açılır Kutu (`ComboBox`) | Sese uygulanacak özel efekti seçer (`Normalleştir`, `Sıkıştır`, `Filtre`, `Fade`, `Kaydırma` vb.). |
| **Kapak Resmi Seç** | Buton | Sesi videoya dönüştürürken (ses+resim->video) kullanılacak kapak resmini seçmek için diyalog açar. |
| **Video Renkleri Ters Çevir** | Açılır Kutu (`ComboBox`) | Video çıktısının renklerini negatifine çevirir (`Evet` seçiliyse). |
| **Video Gri Ton (`Grayscale`)** | Açılır Kutu (`ComboBox`) | Video çıktısını siyah-beyaz (gri tonlamalı) yapar (`Evet` seçiliyse). |
| **Video Sesini Tamamen Sil** | Açılır Kutu (`ComboBox`) | Video dosyasındaki orijinal ses kanallarını tamamen kaldırır (`Evet` seçiliyse). |
| **Harici Ses Ekle (`Sync`)** | Buton | Videoya ana ses olarak eklenecek harici bir ses dosyası seçmek için diyalog açar. |
| **PDF Ters Çevir** | Açılır Kutu (`ComboBox`) | PDF sayfalarının renklerini negatifine çevirir (`Evet` seçiliyse). |
| **PDF Gri Ton** | Açılır Kutu (`ComboBox`) | PDF sayfalarını siyah-beyaz (gri tonlamalı) yapar (`Evet` seçiliyse). |
| **Resim Ters Çevir** | Açılır Kutu (`ComboBox`) | Resim çıktısının renklerini negatifine çevirir (`Evet` seçiliyse). |
| **Resim Gri Ton** | Açılır Kutu (`ComboBox`) | Resim çıktısını siyah-beyaz (gri tonlamalı) yapar (`Evet` seçiliyse). |
| **Resim Çözünürlüğü** | Açılır Kutu (`ComboBox`) | Resim çıktısının ölçek oranını ayarlar (`-5 = %25 küçült, 0 = Orijinal, +5 = %250 büyüt`). |

