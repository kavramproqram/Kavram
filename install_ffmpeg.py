import os
import tarfile
import shutil

# --- Ayarlar ---
# Arşiv dosyası adı
ARCHIVE_ADI = "ffmpeg-8.0.tar.xz" 

# Kurulumun yapılacağı dizin (betiğin bulunduğu yer)
# os.getcwd(), betiğin çalıştırıldığı anki dizini verir.
KURULUM_DIZINI = os.getcwd() 

def manuel_ffmpeg_kurulumu():
    # Arşivin tam yolunu oluştur
    archive_path = os.path.join(KURULUM_DIZINI, ARCHIVE_ADI)

    print(f"1. FFmpeg Arşivi Aranıyor: {archive_path}")
    if not os.path.exists(archive_path):
        print(f"\nHATA: Arşiv dosyası bulunamadı: {archive_path}")
        print("Lütfen dosyanın adının ve konumunun doğru olduğundan emin olun.")
        return

    # 2. Arşivi Açma
    print(f"\n2. Arşiv ({ARCHIVE_ADI}) açılıyor...")
    
    try:
        # Arşivi aç
        with tarfile.open(archive_path, "r:xz") as tar:
            # Arşivin içindeki ana klasör adını dinamik olarak bul
            # Bu, 'ffmpeg-8.0' gibi bir isim olmalıdır.
            ana_klasor_adi = [m.name.split('/')[0] for m in tar.getmembers() if m.isdir() and m.name.count('/') == 0]
            
            if not ana_klasor_adi:
                print("HATA: Arşiv içinde ana klasör bulunamadı. Yapı bozuk olabilir.")
                return

            ana_klasor_adi = ana_klasor_adi[0]
            tar.extractall(path=KURULUM_DIZINI) # Bulunduğu yere aç

    except tarfile.ReadError:
        print(f"HATA: {ARCHIVE_ADI} dosyası formatı hatalı veya bozuk.")
        return
    except Exception as e:
        print(f"Arşiv açılırken beklenmeyen bir hata oluştu: {e}")
        return

    kaynak_dizin = os.path.join(KURULUM_DIZINI, ana_klasor_adi)
    
    # 3. Çalıştırılabilir Dosyaları 'bin' Altına Taşıma (Standartlaştırma)
    
    # Yeni bir 'bin' klasörü oluştur (Bu, sanal ortamlara benzer standart bir yapıdır.)
    bin_dizini = os.path.join(KURULUM_DIZINI, "ffmpeg_bin")
    if not os.path.exists(bin_dizini):
        os.makedirs(bin_dizini)

    print(f"\n3. Çalıştırılabilir dosyalar {bin_dizini} klasörüne taşınıyor...")
    
    # ff* ile başlayan ana dosyalar (ffmpeg, ffprobe, ffplay)
    for dosya in os.listdir(kaynak_dizin):
        if dosya.startswith('ff') and not dosya.endswith(('.txt', '.md', '.log')): # Sadece çalıştırılabilir dosyaları hedefle
            shutil.move(os.path.join(kaynak_dizin, dosya), bin_dizini)
        # qt-faststart gibi diğer yardımcı araçları da taşı
        elif dosya == 'qt-faststart':
            shutil.move(os.path.join(kaynak_dizin, dosya), bin_dizini)


    # 4. Kalan geçici klasörü silme
    try:
        shutil.rmtree(kaynak_dizin)
        print("4. Geçici arşiv klasörü silindi.")
    except Exception as e:
        print(f"Geçici klasör silinemedi: {e}")


    print("\n✅ Kurulum Başarılı!")
    print(f"FFmpeg ve FFprobe artık burada: {bin_dizini}")
    print("\nProgramınızı çalıştırmadan önce PATH'i ayarlamayı unutmayın:")
    print(f'export PATH="{bin_dizini}:$PATH"')
    
if __name__ == "__main__":
    manuel_ffmpeg_kurulumu()
