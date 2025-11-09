/*
 * Kavram 1.0.0
 * Copyright (C) 2025-09-01 Kavram or Contributors
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see /Kavram/License/GPLv3.txt
 *
 * ---------------------------------------------
 *
 * Kavram 1.0.0
 * Copyright (C) 2025-09-01 Kavram veya Contributors
 *
 * Bu program özgür bir yazılımdır: Özgür Yazılım Vakfı tarafından yayınlanan
 * GNU Genel Kamu Lisansı'nın 3. sürümü veya (tercihinize bağlı olarak)
 * daha sonraki herhangi bir sürümü kapsamında yeniden dağıtabilir ve/veya
 * değiştirebilirsiniz.
 *
 * Bu program, faydalı olacağı umuduyla dağıtılmaktadır, ancak HERHANGİ BİR
 * GARANTİ OLMADAN; hatta SATILABİLİRLİK veya BELİRLİ BİR AMACA UYGUNLUK
 * zımni garantisi olmaksızın.
 *
 * Bu programla birlikte GNU Genel Kamu Lisansı'nın bir kopyasını almış olmanız gerekir:
 * /Kavram/License/GPLv3.txt
 */

#include <iostream>
#include <vector>
#include <string>
#include <cmath>     // For std::abs, std::sqrt, std::pow, and M_PI
#include <algorithm> // For std::min/max
#include <stdexcept> // For exceptions
#include <numeric>   // For std::accumulate

// libsndfile kütüphanesini dahil edin.
#include <sndfile.h> // Libsndfile başlık dosyası

// PortAudio kütüphanesini dahil edin.
// Kurulum: Arch Linux'ta `sudo pacman -S portaudio`
// Derleme sırasında `-lportaudio` eklemeniz gerekecek.
#include <portaudio.h> // PortAudio başlık dosyası

// AudioEngine yapısının ileri bildirimi
// pa_record_callback ve pa_playback_callback fonksiyonlarında kullanılacağı için gereklidir.
struct AudioEngine;

// PortAudio geri çağırma fonksiyonlarının bildirimi
static int pa_record_callback(const void *inputBuffer, void *outputBuffer,
                              unsigned long framesPerBuffer,
                              const PaStreamCallbackTimeInfo* timeInfo,
                              PaStreamCallbackFlags statusFlags,
                              void *userData);

static int pa_playback_callback(const void *inputBuffer, void *outputBuffer,
                                unsigned long framesPerBuffer,
                                const PaStreamCallbackTimeInfo* timeInfo,
                                PaStreamCallbackFlags statusFlags,
                                void *userData);


// Structure to hold all audio engine related data and methods
// AudioEngine struct tanımı
struct AudioEngine {
    // Gerçek ses verileri için depolama
    std::vector<float> audio_buffer; // Tüm ana ses verisi (interleaved float formatında)
    int sample_rate;                 // Sesin örnekleme oranı (Hz)
    int channels;                    // Sesin kanal sayısı

    int current_play_position_ms; // Current playback position in ms
    int total_duration_ms;        // Total audio duration in ms
    bool is_playing_flag;         // Playback status
    float current_speed;          // Playback speed
    std::vector<float> envelope_data_storage; // Gerçek dalga şekli verisi

    // Mikrofon kaydı için PortAudio özel değişkenleri
    PaStream *record_stream;            // PortAudio kayıt akışı
    std::vector<float> recorded_audio_buffer; // Kaydedilen ses verisi
    bool is_recording_flag;            // Recording status

    // Oynatma için PortAudio özel değişkenleri
    PaStream *play_stream;              // PortAudio oynatma akışı
    long playback_frame_index;          // Oynatma akışındaki mevcut kare indeksi

    // Düşük Geçiren Filtre (Low-Pass Filter) için değişkenler (Playback)
    float lp_filter_alpha;                     // Playback filtre katsayısı
    std::vector<float> lp_filter_prev_output;  // Her kanal için önceki filtrelenmiş çıktı (Playback)

    // --- Mikrofon İşleme Değişkenleri ---
    float mic_noise_gate_threshold; // Gürültü kapısı eşiği (linear amplitude, 0.0 - 1.0)
    float mic_noise_gate_release_ms; // Gürültü kapısı bırakma süresi (ms)
    std::vector<float> mic_noise_gate_gain; // Her kanal için gürültü kapısı kazancı (0.0 - 1.0)
    std::vector<float> mic_noise_gate_prev_sample; // Her kanal için önceki örnek (release için)

    float mic_hp_filter_alpha; // Yüksek Geçiren Filtre katsayısı (Mikrofon)
    std::vector<float> mic_hp_filter_prev_output; // Her kanal için önceki filtrelenmiş çıktı (Mikrofon HPF)
    std::vector<float> mic_hp_filter_prev_input; // Her kanal için önceki giriş (Mikrofon HPF)

    float mic_lp_filter_alpha; // Düşük Geçiren Filtre katsayısı (Mikrofon)
    std::vector<float> mic_lp_filter_prev_output; // Her kanal için önceki filtrelenmiş çıktı (Mikrofon LPF)

    float mic_input_gain; // Mikrofon giriş kazancı (linear, 0.0 - infinity)

    // Yeni eklenen değişkenler:
    // Reverb Azaltma (Basit LPF olarak simüle edildi)
    float mic_reverb_lp_filter_alpha; // Reverb azaltma için LPF katsayısı
    std::vector<float> mic_reverb_lp_filter_prev_output; // Her kanal için önceki filtrelenmiş çıktı (Reverb LPF)

    // De-esser (Basit yüksek raf filtresi olarak simüle edildi)
    float mic_de_esser_gain; // De-esser için yüksek raf kazancı (linear)
    float mic_de_esser_cutoff_hz; // De-esser için kesme frekansı
    std::vector<float> de_esser_b0, de_esser_b1, de_esser_b2; // De-esser filtre katsayıları
    std::vector<float> de_esser_a1, de_esser_a2; // De-esser filtre katsayıları
    std::vector<float> de_esser_x_prev, de_esser_x_prev2; // De-esser filtre durumu
    std::vector<float> de_esser_y_prev, de_esser_y_prev2; // De-esser filtre durumu

    // De-hum (Çentik filtresi)
    float mic_de_hum_q; // De-hum çentik filtresi Q faktörü
    std::vector<float> de_hum_b0, de_hum_b1, de_hum_b2; // De-hum filtre katsayıları
    std::vector<float> de_hum_a1, de_hum_a2; // De-hum filtre katsayıları
    std::vector<float> de_hum_x_prev, de_hum_x_prev2; // De-hum filtre durumu
    std::vector<float> de_hum_y_prev, de_hum_y_prev2; // De-hum filtre durumu
    float de_hum_frequency_hz; // De-hum frekansı (50Hz veya 60Hz)
    bool de_hum_enabled; // De-hum etkin mi?

    // Compressor
    float mic_comp_threshold_db; // Compressor threshold in dB
    float mic_comp_ratio;        // Compressor ratio (e.g., 2.0 for 2:1)
    float mic_comp_attack_ms;    // Compressor attack time in ms
    float mic_comp_release_ms;   // Compressor release time in ms
    float mic_comp_makeup_gain_db; // Compressor makeup gain in dB
    std::vector<float> mic_comp_envelope; // Envelope follower state for each channel
    std::vector<float> mic_comp_gain;     // Current gain applied by compressor for each channel

    // Parametric EQ (single band)
    float mic_eq_gain_db;      // EQ band gain in dB
    float mic_eq_frequency_hz; // EQ band center frequency in Hz
    float mic_eq_q;            // EQ band Q factor
    bool mic_eq_enabled;       // EQ band enabled/disabled
    std::vector<float> eq_b0, eq_b1, eq_b2; // EQ filter coefficients
    std::vector<float> eq_a1, eq_a2;       // EQ filter coefficients
    std::vector<float> eq_x_prev, eq_x_prev2; // EQ filter state
    std::vector<float> eq_y_prev, eq_y_prev2; // EQ filter state


    // Constructor
    // DÜZELTME: -Wreorder uyarısını düzeltmek için başlatma sırası, struct içindeki bildirim sırasıyla eşleştirildi.
    AudioEngine() : sample_rate(44100), channels(2), // Varsayılan değerler, bildirim sırasına göre önce başlatıldı
                    current_play_position_ms(0), total_duration_ms(0),
                    is_playing_flag(false), current_speed(1.0f),
                    record_stream(nullptr), is_recording_flag(false),
                    play_stream(nullptr), playback_frame_index(0) { // Yeni üyeleri başlat
        std::cout << "AudioEngine created." << std::endl;
        // PortAudio'yu başlat
        PaError err = Pa_Initialize();
        if (err != paNoError) {
            std::cerr << "PortAudio error during initialization: " << Pa_GetErrorText(err) << std::endl;
            // Hata durumunda uygun şekilde ele alın
        }

        // Düşük Geçiren Filtre (Playback) parametrelerini başlat
        const double playback_lp_cutoff_frequency_hz = 3000.0;
        const double T_playback = 1.0 / sample_rate;
        lp_filter_alpha = (2.0 * M_PI * playback_lp_cutoff_frequency_hz * T_playback) / (2.0 * M_PI * playback_lp_cutoff_frequency_hz * T_playback + 1.0);
        lp_filter_prev_output.resize(channels, 0.0f);

        // --- Mikrofon İşleme Parametrelerini Başlat ---
        mic_noise_gate_threshold = 0.0001f; // -80dB (çok agresif)
        mic_noise_gate_release_ms = 20.0f; // 20 ms (hızlı bırakma)
        mic_noise_gate_gain.resize(channels, 0.0f); // Başlangıçta kapalı
        mic_noise_gate_prev_sample.resize(channels, 0.0f);

        // mic_hp_filter_alpha'yı varsayılan olarak etkinleştir ve bir kesme frekansı ata
        const float default_mic_hp_cutoff_frequency_hz = 150.0f; // Fan uğultusu için daha yüksek
        if (sample_rate > 0) {
            mic_hp_filter_alpha = 1.0f / (1.0f + 2.0f * M_PI * default_mic_hp_cutoff_frequency_hz / sample_rate);
        } else {
            mic_hp_filter_alpha = 0.0f; // Güvenlik için
        }
        mic_hp_filter_prev_output.resize(channels, 0.0f);
        mic_hp_filter_prev_input.resize(channels, 0.0f);

        mic_lp_filter_alpha = 0.0f; // Başlangıçta kapalı
        mic_lp_filter_prev_output.resize(channels, 0.0f);

        mic_input_gain = 1.0f; // 0dB

        // Reverb Reduction (LPF)
        mic_reverb_lp_filter_alpha = 0.0f; // Başlangıçta kapalı
        mic_reverb_lp_filter_prev_output.resize(channels, 0.0f);

        // De-esser (High-Shelf Filter)
        mic_de_esser_gain = 1.0f; // Linear gain (0dB)
        mic_de_esser_cutoff_hz = 6000.0f; // Varsayılan kesme frekansı
        de_esser_b0.resize(channels, 0.0f); de_esser_b1.resize(channels, 0.0f); de_esser_b2.resize(channels, 0.0f);
        de_esser_a1.resize(channels, 0.0f); de_esser_a2.resize(channels, 0.0f);
        de_esser_x_prev.resize(channels, 0.0f); de_esser_x_prev2.resize(channels, 0.0f);
        de_esser_y_prev.resize(channels, 0.0f); de_esser_y_prev2.resize(channels, 0.0f);

        // De-hum (Notch Filter)
        de_hum_frequency_hz = 50.0f; // Varsayılan hum frekansı (Avrupa için 50Hz)
        mic_de_hum_q = 30.0f; // Varsayılan Q faktörü (dar çentik)
        de_hum_enabled = false;
        de_hum_b0.resize(channels, 0.0f); de_hum_b1.resize(channels, 0.0f); de_hum_b2.resize(channels, 0.0f);
        de_hum_a1.resize(channels, 0.0f); de_hum_a2.resize(channels, 0.0f);
        de_hum_x_prev.resize(channels, 0.0f); de_hum_x_prev2.resize(channels, 0.0f);
        de_hum_y_prev.resize(channels, 0.0f); de_hum_y_prev2.resize(channels, 0.0f);

        // Compressor
        mic_comp_threshold_db = 0.0f; // Default: 0dB (Off)
        mic_comp_ratio = 1.0f;        // Default: 1:1 (Off)
        mic_comp_attack_ms = 1.0f;    // Default: 1ms
        mic_comp_release_ms = 100.0f; // Default: 100ms
        mic_comp_makeup_gain_db = 0.0f; // Default: 0dB
        mic_comp_envelope.resize(channels, 0.0f);
        mic_comp_gain.resize(channels, 1.0f); // Start with no gain reduction

        // Parametric EQ
        mic_eq_gain_db = 0.0f;      // Default: 0dB (flat)
        mic_eq_frequency_hz = 1000.0f; // Default: 1kHz
        mic_eq_q = 1.0f;            // Default: Q=1.0
        mic_eq_enabled = false;
        eq_b0.resize(channels, 0.0f); eq_b1.resize(channels, 0.0f); eq_b2.resize(channels, 0.0f);
        eq_a1.resize(channels, 0.0f); eq_a2.resize(channels, 0.0f);
        eq_x_prev.resize(channels, 0.0f); eq_x_prev2.resize(channels, 0.0f);
        eq_y_prev.resize(channels, 0.0f); eq_y_prev2.resize(channels, 0.0f);

        // --- Mikrofon İşleme Parametreleri Sonu ---
    }

    // Destructor
    ~AudioEngine() {
        std::cout << "AudioEngine destroying..." << std::endl;
        // PortAudio akışlarını durdur ve sonlandır
        if (record_stream) {
            Pa_StopStream(record_stream);
            Pa_CloseStream(record_stream);
            record_stream = nullptr;
        }
        if (play_stream) { // Oynatma akışını da kapat
            Pa_StopStream(play_stream);
            Pa_CloseStream(play_stream);
            play_stream = nullptr;
        }
        PaError err = Pa_Terminate();
        if (err != paNoError) {
            std::cerr << "PortAudio error during termination: " << Pa_GetErrorText(err) << std::endl;
        }

        audio_buffer.clear();
        envelope_data_storage.clear();
        recorded_audio_buffer.clear();
        lp_filter_prev_output.clear(); // Playback filtre değişkenlerini de temizle

        // --- Yeni Eklenen Mikrofon İşleme Değişkenlerini Temizle ---
        mic_noise_gate_gain.clear();
        mic_noise_gate_prev_sample.clear();
        mic_hp_filter_prev_output.clear();
        mic_hp_filter_prev_input.clear();
        mic_lp_filter_prev_output.clear();
        mic_reverb_lp_filter_prev_output.clear();
        de_esser_b0.clear(); de_esser_b1.clear(); de_esser_b2.clear();
        de_esser_a1.clear(); de_esser_a2.clear();
        de_esser_x_prev.clear(); de_esser_x_prev2.clear();
        de_esser_y_prev.clear(); de_esser_y_prev2.clear();
        de_hum_b0.clear(); de_hum_b1.clear(); de_hum_b2.clear();
        de_hum_a1.clear(); de_hum_a1.clear();
        de_hum_x_prev.clear(); de_hum_x_prev2.clear();
        de_hum_y_prev.clear(); de_hum_y_prev2.clear();
        mic_comp_envelope.clear();
        mic_comp_gain.clear();
        eq_b0.clear(); eq_b1.clear(); eq_b2.clear();
        eq_a1.clear(); eq_a2.clear();
        eq_x_prev.clear(); eq_x_prev2.clear();
        eq_y_prev.clear(); eq_y_prev2.clear();
        // --- Yeni Eklenen Mikrofon İşleme Değişkenleri Sonu ---
    }

    // Yardımcı fonksiyon: Zarf verisini yeniden hesapla
    void recalculate_envelope_data() {
        envelope_data_storage.clear();
        if (audio_buffer.empty() || sample_rate == 0 || channels == 0) {
            return;
        }

        const int ENVELOPE_MS_PER_POINT = 50; // Her 50 ms için bir nokta
        // DÜZELTME: -Wsign-compare uyarısını düzeltmek için 'long' -> 'size_t'
        size_t frames_per_envelope_point = (sample_rate * ENVELOPE_MS_PER_POINT) / 1000;
        if (frames_per_envelope_point == 0) frames_per_envelope_point = 1;

        // DÜZELTME: -Wsign-compare uyarısını düzeltmek için 'long i' -> 'size_t i'
        for (size_t i = 0; i < audio_buffer.size() / channels; i += frames_per_envelope_point) {
            float max_amplitude = 0.0f;
            // DÜZELTME: -Wsign-compare uyarısını düzeltmek için 'long j' -> 'size_t j'
            // 'j' zaten 'size_t' idi, karşılaştırıldığı 'frames_per_envelope_point' artık 'size_t'
            for (size_t j = 0; j < frames_per_envelope_point; ++j) {
                // DÜZELTME: (i + j) artık 'size_t' (unsigned) olduğu için karşılaştırma güvenli.
                if ((i + j) * channels < audio_buffer.size()) {
                    for (int k = 0; k < channels; ++k) {
                        max_amplitude = std::max(max_amplitude, std::abs(audio_buffer[(i + j) * channels + k]));
                    }
                } else {
                    break;
                }
            }
            envelope_data_storage.push_back(max_amplitude);
        }
        total_duration_ms = static_cast<int>((static_cast<double>(audio_buffer.size() / channels) / sample_rate) * 1000);
        std::cout << "Envelope data recalculated. New duration: " << total_duration_ms << " ms, Length: " << envelope_data_storage.size() << std::endl;
    }


    // Ses dosyalarını yükleme ve zarf verisi oluşturma
    // Returns 0 on success, -1 on failure.
    int load_files(char** filePaths, int numFiles) {
        std::cout << "Attempting to load " << numFiles << " audio files." << std::endl;
        if (numFiles == 0) {
            std::cerr << "No files to load." << std::endl;
            return -1;
        }

        // Önceki verileri temizle
        audio_buffer.clear();
        current_play_position_ms = 0;
        total_duration_ms = 0;
        is_playing_flag = false;
        // sample_rate ve channels değerleri burada güncellenecek, varsayılanlar üzerine yazılacak.
        // Eğer ilk dosya yükleniyorsa, bu değerler dosyanınkilerle eşleşecek.

        for (int i = 0; i < numFiles; ++i) {
            std::string filePath = filePaths[i];
            std::cout << "  Loading: " << filePath << std::endl;

            SF_INFO sfinfo;
            SNDFILE* infile = sf_open(filePath.c_str(), SFM_READ, &sfinfo);

            if (!infile) {
                std::cerr << "Error opening sound file: " << filePath << " - " << sf_strerror(NULL) << std::endl;
                audio_buffer.clear(); // Hata durumunda buffer'ı temizle
                return -1;
            }

            // İlk dosyanın örnekleme oranı ve kanal sayısını al
            if (i == 0) {
                sample_rate = sfinfo.samplerate;
                channels = sfinfo.channels;
            } else {
                // Sonraki dosyaların aynı formatta olduğundan emin olun
                if (sfinfo.samplerate != sample_rate || sfinfo.channels != channels) {
                    std::cerr << "Warning: Mismatch in sample rate or channels for " << filePath << ". Skipping." << std::endl;
                    sf_close(infile);
                    continue; // Bu dosyayı atla
                }
            }

            // Dosyadan tüm ses verilerini oku
            std::vector<float> file_data(sfinfo.frames * sfinfo.channels);
            sf_readf_float(infile, file_data.data(), sfinfo.frames);
            sf_close(infile);

            // Mevcut ses buffer'ına ekle
            audio_buffer.insert(audio_buffer.end(), file_data.begin(), file_data.end());
        }

        if (audio_buffer.empty() || sample_rate == 0 || channels == 0) {
            std::cerr << "No valid audio data loaded." << std::endl;
            return -1;
        }

        recalculate_envelope_data(); // Yeni zarf verisini hesapla

        std::cout << "Audio files loaded. Total duration: " << total_duration_ms << " ms." << std::endl;
        std::cout << "Envelope data length: " << envelope_data_storage.size() << std::endl;
        current_play_position_ms = 0;
        is_playing_flag = false;
        return 0; // Indicate success
    }

    // Play audio
    // Returns 0 on success, -1 on failure.
    int play() {
        if (audio_buffer.empty() || sample_rate == 0 || channels == 0) {
            std::cerr << "Error: No audio data to play." << std::endl;
            return -1;
        }

        if (is_playing_flag) {
            std::cout << "Audio is already playing." << std::endl;
            return 0; // Already playing
        }

        // Eğer oynatma akışı zaten varsa, durdurup kapat
        if (play_stream) {
            Pa_StopStream(play_stream);
            Pa_CloseStream(play_stream);
            play_stream = nullptr;
        }

        // Oynatma akışı parametrelerini ayarla
        PaStreamParameters outputParameters;

        // --- GÜNCELLEME: API Prioritizasyonu (PulseAudio > ALSA > Default) ---
        // Kullanıcının Linux uyumluluğu için önerdiği mantık
        PaHostApiIndex targetApiIndex = Pa_GetDefaultHostApi();
        int host_api_count = Pa_GetHostApiCount();
        
        // 1. API'leri tara ve PulseAudio'yu (veya ALSA'yı) ara
        for (PaHostApiIndex i = 0; i < host_api_count; ++i) {
            const PaHostApiInfo* info = Pa_GetHostApiInfo(i);
            if (info) {
                std::string apiName = info->name;
                // PulseAudio'yu (veya modern PipeWire/Pulse katmanını) tercih et
                // ALSA, PipeWire'ın ALSA arayüzü olarak da kullanılabilir
                if (apiName.find("PulseAudio") != std::string::npos ||
                    apiName.find("ALSA") != std::string::npos) 
                {
                    targetApiIndex = i;
                    // PulseAudio en yüksek önceliği alsın ve hemen kullanılsın
                    if (apiName.find("PulseAudio") != std::string::npos) {
                        std::cout << "AudioEngine: Found PulseAudio Host API for playback." << std::endl;
                        break;
                    }
                }
            }
        }

        // 2. Bulunan API'ye ait varsayılan cihazı kullan
        const PaHostApiInfo* targetApiInfo = Pa_GetHostApiInfo(targetApiIndex);
        if (!targetApiInfo) {
             std::cerr << "Error: Could not get info for target Host API." << std::endl;
             return -1;
        }
        
        PaDeviceIndex device_index = targetApiInfo->defaultOutputDevice;
        if (device_index == paNoDevice) {
             // Seçilen API'nin varsayılan çıkış cihazı yoksa, genel varsayılana geri dön
             std::cout << "AudioEngine: Target API has no default output. Falling back to overall default device." << std::endl;
             device_index = Pa_GetDefaultOutputDevice();
             if (device_index == paNoDevice) {
                std::cerr << "Error: No default output device found for any Host API." << std::endl;
                return -1;
             }
        } else {
            std::cout << "AudioEngine: Using Host API '" << targetApiInfo->name << "' for playback." << std::endl;
        }

        outputParameters.device = device_index; // Seçilen cihazı ata
        // --- GÜNCELLEME SONU ---


        // Cihaz bilgilerini al
        const PaDeviceInfo* deviceInfo = Pa_GetDeviceInfo(outputParameters.device);
        if (!deviceInfo) {
            std::cerr << "Error: Could not get device info for selected output device." << std::endl;
            return -1;
        }

        // Ses motorunun kendi örnekleme hızını kullan
        // Bu, ses dosyasının orijinal örnekleme hızında oynatılmasını sağlar.
        double playback_sample_rate = static_cast<double>(sample_rate);

        outputParameters.channelCount = channels; // Mevcut ses kanalı sayısını kullan
        outputParameters.sampleFormat = paFloat32; // Float32 formatında oynatma
        // Daha yüksek gecikme (latency) kullanarak tamponlama sorunlarını azaltmaya çalışıyoruz.
        // Bu, sesin daha akıcı çalmasına yardımcı olabilir ancak küçük bir gecikme yaratır.
        outputParameters.suggestedLatency = deviceInfo->defaultHighOutputLatency; // Düşük yerine yüksek gecikme
        outputParameters.hostApiSpecificStreamInfo = NULL;

        // Oynatma akışını aç
        PaError err = Pa_OpenStream(
            &play_stream,
            NULL, // Giriş parametresi yok (sadece oynatma)
            &outputParameters,
            playback_sample_rate, // Ses motorunun örnekleme oranını kullan
            1024, // Sabit bir tampon boyutu belirledik (önceki 512 yerine 1024)
            paClipOff, // Aşırı yüklenmeyi engelle
            pa_playback_callback, // Geri çağırma fonksiyonu
            this // userData (AudioEngine pointer'ı)
        );

        if (err != paNoError) {
            std::cerr << "PortAudio error during Pa_OpenStream for playback: " << Pa_GetErrorText(err) << std::endl;
            play_stream = nullptr;
            return -1;
        }

        // Oynatma akışını başlat
        err = Pa_StartStream(play_stream);
        if (err != paNoError) {
            std::cerr << "PortAudio error during Pa_StartStream for playback: " << Pa_GetErrorText(err) << std::endl;
            Pa_CloseStream(play_stream);
            play_stream = nullptr;
            return -1;
        }

        is_playing_flag = true;
        // Oynatma pozisyonunu sıfırla veya kaldığı yerden devam ettir (current_play_position_ms'i kullan)
        playback_frame_index = static_cast<long>((static_cast<double>(current_play_position_ms) / 1000.0) * sample_rate);

        std::cout << "Audio playback started." << std::endl;
        return 0; // Success
    }

    // Pause audio
    // Returns 0 on success, -1 on failure.
    int pause() {
        if (!is_playing_flag) {
            std::cout << "Audio is not playing." << std::endl;
            return 0; // Already paused
        }
        if (play_stream) {
            PaError err = Pa_StopStream(play_stream); // Akışı duraklatmak için StopStream kullanılır
            if (err != paNoError) {
                std::cerr << "PortAudio error during Pa_StopStream for pause: " << Pa_GetErrorText(err) << std::endl;
                return -1;
            }
        }
        is_playing_flag = false;
        std::cout << "Audio playback paused." << std::endl;
        return 0; // Success
    }

    // Stop audio
    // Returns 0 on success, -1 on failure.
    int stop() {
        if (!is_playing_flag && playback_frame_index == 0) { // Zaten durmuşsa
            std::cout << "Audio is already stopped." << std::endl;
            return 0;
        }
        if (play_stream) {
            PaError err = Pa_StopStream(play_stream);
            if (err != paNoError) {
                std::cerr << "PortAudio error during Pa_StopStream for stop: " << Pa_GetErrorText(err) << std::endl;
                // Hata olsa bile akışı kapatmaya çalış
                Pa_CloseStream(play_stream);
                play_stream = nullptr;
                is_playing_flag = false;
                current_play_position_ms = 0; // Pozisyonu sıfırla
                playback_frame_index = 0;
                return -1;
            }
            Pa_CloseStream(play_stream); // Akışı kapat
            play_stream = nullptr;
        }
        is_playing_flag = false;
        current_play_position_ms = 0; // Pozisyonu sıfırla
        playback_frame_index = 0;
        std::cout << "Audio playback stopped." << std::endl;
        return 0; // Success
    }

    // Get current playback position in milliseconds
    // Returns position in ms, or 0 on error/no media.
    int get_position_ms() {
        // Bu fonksiyonun PortAudio callback'i tarafından güncellenen playback_frame_index'i kullanması daha doğru.
        // UI güncelleme sıklığına göre bu değer zaten güncelleniyor.
        // current_play_position_ms'i doğrudan döndürelim, çünkü callback onu güncelleyecek.
        return current_play_position_ms;
    }

    // Get total duration in milliseconds
    // Returns duration in ms, or 0 on error/no media.
    int get_duration_ms() {
        return total_duration_ms;
    }

    // Get waveform envelope data length
    int get_envelope_length() {
        return envelope_data_storage.size();
    }

    // Get waveform envelope data pointer
    const float* get_envelope_data() {
        if (envelope_data_storage.empty()) {
            return nullptr;
        }
        return envelope_data_storage.data();
    }

    // Set playback speed
    int set_speed(float speed) {
        std::cout << "Setting playback speed to " << speed << "x." << std::endl;
        current_speed = speed;
        // PortAudio doğrudan hız ayarı sunmaz, bu yüzden callback içinde veri okuma hızını ayarlamak gerekir.
        // Bu karmaşık bir konu olduğu için şimdilik sadece simülasyon amaçlı bırakıldı.
        return 0;
    }

    // Set playback position in milliseconds
    // Oynatma pozisyonunu milisaniye cinsinden ayarlar.
    // Ses oynatılırken bile sorunsuz bir şekilde konum değiştirmeyi sağlar.
    int set_play_position_ms(int ms) {
        // Geçersiz değerleri sınırla
        if (ms < 0) ms = 0;
        if (ms > total_duration_ms) ms = total_duration_ms;

        // Mevcut oynatma pozisyonunu milisaniye cinsinden güncelle
        current_play_position_ms = ms;

        // Karşılık gelen kare indeksini hesapla
        long new_playback_frame_index = static_cast<long>((static_cast<double>(current_play_position_ms) / 1000.0) * sample_rate);

        // Ses motorunun oynatma kare indeksini güncelle
        playback_frame_index = new_playback_frame_index;

        std::cout << "Set playback position to " << ms << " ms. New frame index: " << playback_frame_index << std::endl;

        // Eğer ses şu anda oynatılıyorsa, akışı durdurup yeniden başlatmaya gerek yoktur.
        // pa_playback_callback, bir sonraki döngüsünde güncellenmiş playback_frame_index'ten otomatik olarak devam edecektir.
        // Eğer duraklatılmış veya durdurulmuşsa, oynatma başladığında doğru konumdan devam etmesi için dahili indeksi güncelleriz.
        // Akışı durdurıp yeniden başlatma mantığı, sorunsuz arama için sorunluydu.

        return 0; // Pozisyon güncellemesinde başarıyı belirt
    }

    // Get playback state
    // Returns 1 if playing, 0 if paused/stopped.
    int get_is_playing() {
        return is_playing_flag ? 1 : 0;
    }

    // Delete a segment of audio
    int delete_segment(int start_ms, int end_ms) {
        std::cout << "Deleting audio segment from " << start_ms << " to " << end_ms << " ms (requires audio data manipulation)." << std::endl;
        if (audio_buffer.empty() || sample_rate == 0 || channels == 0) {
            std::cerr << "Error: No audio data to delete from." << std::endl;
            return -1;
        }

        long start_frame = static_cast<long>((static_cast<double>(start_ms) / 1000.0) * sample_rate);
        long end_frame = static_cast<long>((static_cast<double>(end_ms) / 1000.0) * sample_rate);

        // Clamp to valid range
        start_frame = std::max(0L, start_frame);
        end_frame = std::min(static_cast<long>(audio_buffer.size() / channels), end_frame);

        if (start_frame >= end_frame) {
            std::cout << "No valid segment to delete." << std::endl;
            return 0; // Nothing to delete, consider it success
        }

        // Calculate start and end indices in the interleaved buffer
        long start_idx = start_frame * channels;
        long end_idx = end_frame * channels;

        // Remove the segment from the audio_buffer
        audio_buffer.erase(audio_buffer.begin() + start_idx, audio_buffer.begin() + end_idx);

        recalculate_envelope_data(); // Yeniden hesapla

        return 0; // Success
    }

    // Insert audio data from a file
    int insert_audio(const std::string& filePath, int position_ms) {
        std::cout << "Inserting audio file '" << filePath << "' at position " << position_ms << " ms (requires audio data manipulation)." << std::endl;
        if (sample_rate == 0 || channels == 0) {
            std::cerr << "Error: Main audio engine not initialized with sample rate/channels. Load a file first." << std::endl;
            return -1; // Cannot insert if main audio properties are unknown
        }

        SF_INFO sfinfo;
        SNDFILE* infile = sf_open(filePath.c_str(), SFM_READ, &sfinfo);

        if (!infile) {
            std::cerr << "Error opening sound file for insertion: " << filePath << " - " << sf_strerror(NULL) << std::endl;
            return -1;
        }

        // Sample rate mismatch check
        if (sfinfo.samplerate != sample_rate) {
            std::cerr << "Error: Sample rate mismatch for inserted file. Expected: "
                      << sample_rate << "Hz. Got: " << sfinfo.samplerate << "Hz." << std::endl;
            sf_close(infile);
            return -1;
        }

        std::vector<float> inserted_data(sfinfo.frames * sfinfo.channels);
        sf_readf_float(infile, inserted_data.data(), sfinfo.frames);
        sf_close(infile);

        // Kanal sayısı eşleştirme
        std::vector<float> processed_inserted_data;
        if (sfinfo.channels == channels) {
            processed_inserted_data = inserted_data; // Kanal sayısı zaten eşleşiyor
        } else if (sfinfo.channels == 1 && channels == 2) {
            // Mono'dan Stereo'ya dönüştürme: Her mono örneği iki kez kopyala
            processed_inserted_data.reserve(inserted_data.size() * 2);
            for (float sample : inserted_data) {
                processed_inserted_data.push_back(sample); // Left channel
                processed_inserted_data.push_back(sample); // Right channel
            }
            std::cout << "Converted mono inserted audio to stereo." << std::endl;
        } else if (sfinfo.channels == 2 && channels == 1) {
            // Stereo'dan Mono'ya dönüştürme: Kanalları ortalama
            processed_inserted_data.reserve(inserted_data.size() / 2);
            for (size_t i = 0; i < inserted_data.size(); i += 2) {
                processed_inserted_data.push_back((inserted_data[i] + inserted_data[i+1]) / 2.0f);
            }
            std::cout << "Converted stereo inserted audio to mono." << std::endl;
        } else {
            std::cerr << "Error: Unsupported channel count mismatch for inserted file. Expected: "
                      << channels << "ch. Got: " << sfinfo.channels << "ch." << std::endl;
            return -1;
        }

        long insert_frame = static_cast<long>((static_cast<double>(position_ms) / 1000.0) * sample_rate);
        insert_frame = std::max(0L, std::min(insert_frame, static_cast<long>(audio_buffer.size() / channels)));

        long insert_idx = insert_frame * channels;

        audio_buffer.insert(audio_buffer.begin() + insert_idx, processed_inserted_data.begin(), processed_inserted_data.end());

        recalculate_envelope_data(); // Yeniden hesapla

        return 0; // Success
    }

    // Start microphone recording
    int start_microphone_recording() {
        std::cout << "Starting microphone recording." << std::endl;
        if (is_recording_flag) {
            std::cout << "Already recording." << std::endl;
            return 1; // Already recording
        }

        PaStreamParameters inputParameters;
        
        // --- GÜNCELLEME: API Prioritizasyonu (PulseAudio > ALSA > Default) ---
        // Kullanıcının Linux uyumluluğu için önerdiği mantık
        PaHostApiIndex targetApiIndex = Pa_GetDefaultHostApi();
        int host_api_count = Pa_GetHostApiCount();
        
        // 1. API'leri tara ve PulseAudio'yu (veya ALSA'yı) ara
        for (PaHostApiIndex i = 0; i < host_api_count; ++i) {
            const PaHostApiInfo* info = Pa_GetHostApiInfo(i);
            if (info) {
                std::string apiName = info->name;
                if (apiName.find("PulseAudio") != std::string::npos ||
                    apiName.find("ALSA") != std::string::npos) 
                {
                    targetApiIndex = i;
                    if (apiName.find("PulseAudio") != std::string::npos) {
                        std::cout << "AudioEngine: Found PulseAudio Host API for recording." << std::endl;
                        break;
                    }
                }
            }
        }

        // 2. Bulunan API'ye ait varsayılan cihazı kullan
        const PaHostApiInfo* targetApiInfo = Pa_GetHostApiInfo(targetApiIndex);
        if (!targetApiInfo) {
             std::cerr << "Error: Could not get info for target Host API." << std::endl;
             return -1;
        }

        PaDeviceIndex device_index = targetApiInfo->defaultInputDevice; // GİRİŞ CİHAZI
        if (device_index == paNoDevice) {
             std::cout << "AudioEngine: Target API has no default input. Falling back to overall default device." << std::endl;
             device_index = Pa_GetDefaultInputDevice(); // GİRİŞ CİHAZI
             if (device_index == paNoDevice) {
                std::cerr << "Error: No default input device found for any Host API." << std::endl;
                return -1;
             }
        } else {
            std::cout << "AudioEngine: Using Host API '" << targetApiInfo->name << "' for recording." << std::endl;
        }

        inputParameters.device = device_index; // Seçilen cihazı ata
        // --- GÜNCELLEME SONU ---


        // Cihaz bilgilerini al
        const PaDeviceInfo* deviceInfo = Pa_GetDeviceInfo(inputParameters.device);
        if (!deviceInfo) {
            std::cerr << "Error: Could not get device info for selected input device." << std::endl;
            return -1;
        }

        // Mikrofon kaydının örnekleme hızını ve kanal sayısını AudioEngine'in değerleriyle eşleştir.
        // Bu, kaydedilen sesin ana timeline ile uyumlu olmasını sağlar.
        double recording_sample_rate = static_cast<double>(sample_rate);
        inputParameters.channelCount = channels;

        inputParameters.sampleFormat = paFloat32; // Float32 formatında kayıt
        inputParameters.suggestedLatency = deviceInfo->defaultLowInputLatency;
        inputParameters.hostApiSpecificStreamInfo = NULL;

        PaError err = Pa_OpenStream(
            &record_stream,
            &inputParameters,
            NULL, // Çıkış parametresi yok (sadece kayıt)
            recording_sample_rate, // AudioEngine'in örnekleme oranını kullan
            paFramesPerBufferUnspecified, // Buffer boyutu PortAudio'ya bırakılır
            paClipOff, // Aşırı yüklenmeyi engelle
            pa_record_callback, // Geri çağırma fonksiyonu
            this // userData (AudioEngine pointer'ı)
        );

        if (err != paNoError) {
            std::cerr << "PortAudio error during Pa_OpenStream: " << Pa_GetErrorText(err) << std::endl;
            record_stream = nullptr;
            return -1;
        }

        err = Pa_StartStream(record_stream);
        if (err != paNoError) {
            std::cerr << "PortAudio error during Pa_StartStream: " << Pa_GetErrorText(err) << std::endl;
            Pa_CloseStream(record_stream);
            record_stream = nullptr;
            return -1;
        }

        recorded_audio_buffer.clear(); // Yeni kayıt için buffer'ı temizle
        is_recording_flag = true;
        std::cout << "Microphone recording started." << std::endl;
        return 0; // Success
    }

    // Stop microphone recording
    int stop_microphone_recording() {
        std::cout << "Stopping microphone recording." << std::endl;
        if (!is_recording_flag) {
            std::cout << "Not currently recording." << std::endl;
            return 1; // Not recording
        }

        PaError err = Pa_StopStream(record_stream);
        if (err != paNoError) {
            std::cerr << "PortAudio error during Pa_StopStream: " << Pa_GetErrorText(err) << std::endl;
            // Hata olsa bile akışı kapatmaya çalış
            Pa_CloseStream(record_stream);
            record_stream = nullptr;
            is_recording_flag = false;
            return -1;
        }

        err = Pa_CloseStream(record_stream);
        if (err != paNoError) {
            std::cerr << "PortAudio error during Pa_CloseStream: " << Pa_GetErrorText(err) << std::endl;
            record_stream = nullptr;
            is_recording_flag = false;
            return -1;
        }

        record_stream = nullptr;
        is_recording_flag = false;
        std::cout << "Microphone recording stopped. Recorded " << recorded_audio_buffer.size() << " samples." << std::endl;
        return 0; // Success
    }

    // Play recorded audio (placeholder - not directly used in GUI but defined in Python)
    int play_recorded_audio() {
        std::cout << "Playing recorded audio (placeholder)." << std::endl;
        // Gerçekte kaydedilen ses oynatılır.
        return 0;
    }

    // Insert recorded audio into the timeline
    int insert_recorded_audio(int position_ms) {
        std::cout << "Inserting recorded audio at position " << position_ms << " ms." << std::endl;
        if (recorded_audio_buffer.empty()) {
            std::cerr << "Error: No recorded audio to insert." << std::endl;
            return -1;
        }
        
        // --- Yeni Eklenen Kod: Kaydedilen Sesi Normalleştirme ---
        float max_amplitude = 0.0f;
        for (float sample : recorded_audio_buffer) {
            max_amplitude = std::max(max_amplitude, std::abs(sample));
        }

        // Hedef genlik: 1.0f (maksimum float değeri) veya biraz daha düşük (örneğin 0.9f)
        // 0.9f kullanmak, olası kırpmaları (clipping) önlemek için daha güvenli olabilir.
        const float TARGET_AMPLITUDE = 0.9f; 
        
        if (max_amplitude > 0.0f) { // Sıfıra bölme hatasını önle
            float scale_factor = TARGET_AMPLITUDE / max_amplitude;
            for (float& sample : recorded_audio_buffer) {
                sample *= scale_factor;
            }
            std::cout << "Recorded audio normalized with scale factor: " << scale_factor << std::endl;
        } else {
            std::cout << "Recorded audio is silent, no normalization applied." << std::endl;
            // Eğer ses tamamen sessizse, küçük bir varsayılan kazanç uygulayabiliriz
            // veya kullanıcıdan bir sonraki adımda manuel olarak ayarlamasını isteyebiliriz.
            // Şimdilik, sessizse işlem yapmıyoruz.
        }
        // --- Yeni Eklenen Kod Sonu ---

        // Kaydedilen sesin sample_rate ve channels değerleri, motorun mevcut değerleriyle uyumlu olmalı.
        // Motorun başlangıçta varsayılan değerleri (44100, 2) ile başlatıldığı varsayılıyor.
        // Eğer daha sonra bir dosya yüklenirse ve motorun sample_rate/channels'ı değişirse,
        // bu fonksiyonun da kaydedilen sesin formatını dönüştürmesi gerekebilir.
        // Şimdilik, kaydedilen sesin motorun mevcut formatıyla aynı olduğunu varsayıyoruz.
        if (sample_rate == 0 || channels == 0) { // Bu kontrol, varsayılan değerler ayarlandığı için teorik olarak gereksiz, ancak güvenlik için bırakıldı.
            std::cerr << "Error: Main audio engine not initialized with sample rate/channels. Load a file first." << std::endl;
            return -1;
        }

        // recorded_audio_buffer'ın kanal sayısını kontrol et ve ana audio_buffer'ın kanal sayısıyla eşleştir.
        // recorded_audio_buffer'daki veri PortAudio callback'i tarafından zaten engine->channels kadar kanal ile kaydediliyor.
        // Bu nedenle burada ek bir kanal dönüşümüne gerek yok.
        // Ancak, eğer callback'te kanal sayısı farklı kaydediliyorsa (ki olmamalı), burada düzeltme yapılmalıdır.
        // Şu anki log çıktısı "Got: 44100Hz, 1ch." dediği için, callback'in mono kaydettiği anlaşılıyor.
        // Bunu düzeltmek için PortAudio stream açılırken inputParameters.channelCount = channels; satırının
        // doğru çalıştığından emin olmalıyız.
        // Eğer recorded_audio_buffer'ın boyutu channels * framesPerBuffer'a uymuyorsa, burada bir sorun var demektir.

        // Eğer kaydedilen ses mono ise ve ana ses stereo ise, mono sesi stereo'ya dönüştür.
        // Bu durum, PortAudio'nun varsayılan giriş cihazının mono olması durumunda ortaya çıkabilir.
        // Normalde PortAudio, stream'i açarken istenen kanal sayısını kullanmaya çalışır.
        // Ancak, cihazın kendisi mono ise, mono olarak alınır.
        if (channels == 2 && recorded_audio_buffer.size() % 2 != 0) { // Eğer stereo bekleniyor ve buffer boyutu tek ise (mono)
            std::vector<float> stereo_recorded_audio_buffer;
            stereo_recorded_audio_buffer.reserve(recorded_audio_buffer.size() * 2);
            for (float sample : recorded_audio_buffer) {
                stereo_recorded_audio_buffer.push_back(sample); // Left channel
                stereo_recorded_audio_buffer.push_back(sample); // Right channel
            }
            recorded_audio_buffer = stereo_recorded_audio_buffer;
            std::cout << "Converted recorded mono audio to stereo for insertion." << std::endl;
        } else if (channels == 1 && recorded_audio_buffer.size() % 2 == 0 && recorded_audio_buffer.size() > 0) {
            // Eğer mono bekleniyor ve buffer boyutu çift ise (stereo)
            std::vector<float> mono_recorded_audio_buffer;
            mono_recorded_audio_buffer.reserve(recorded_audio_buffer.size() / 2);
            for (size_t i = 0; i < recorded_audio_buffer.size(); i += 2) {
                mono_recorded_audio_buffer.push_back((recorded_audio_buffer[i] + recorded_audio_buffer[i+1]) / 2.0f);
            }
            recorded_audio_buffer = mono_recorded_audio_buffer;
            std::cout << "Converted recorded stereo audio to mono for insertion." << std::endl;
        }


        long insert_frame = static_cast<long>((static_cast<double>(position_ms) / 1000.0) * sample_rate);
        insert_frame = std::max(0L, std::min(insert_frame, static_cast<long>(audio_buffer.size() / channels)));

        long insert_idx = insert_frame * channels;

        audio_buffer.insert(audio_buffer.begin() + insert_idx, recorded_audio_buffer.begin(), recorded_audio_buffer.end());

        recorded_audio_buffer.clear(); // Kaydedilen sesi ekledikten sonra temizle
        recalculate_envelope_data(); // Yeniden hesapla

        std::cout << "Recorded audio inserted. New total duration: " << total_duration_ms << " ms." << std::endl;
        return 0; // Success
    }

    // Save combined/edited audio data to a file
    int save_to_file(const std::string& filePath) {
        std::cout << "Saving edited audio to: " << filePath << std::endl;
        if (audio_buffer.empty() || sample_rate == 0 || channels == 0) {
            std::cerr << "Error: No audio data to save." << std::endl;
            return -1;
        }

        SF_INFO sfinfo;
        sfinfo.samplerate = sample_rate;
        sfinfo.channels = channels;
        // WAV formatı ve float tipi
        sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_FLOAT; // .saund için de bu formatı kullanabiliriz.

        SNDFILE* outfile = sf_open(filePath.c_str(), SFM_WRITE, &sfinfo);
        if (!outfile) {
            std::cerr << "Error opening output file for saving: " << filePath << " - " << sf_strerror(NULL) << std::endl;
            return -1;
        }

        // Tüm buffer'ı yaz
        sf_writef_float(outfile, audio_buffer.data(), audio_buffer.size() / channels);
        sf_close(outfile);

        std::cout << "Audio successfully saved to: " << filePath << std::endl;
        return 0; // Success
    }

    // --- Mikrofon İşleme Fonksiyonları ---
    // Gürültü kapısı eşiğini ayarlar (linear amplitude)
    int set_noise_gate_threshold(float threshold) {
        mic_noise_gate_threshold = std::max(0.0f, std::min(1.0f, threshold));
        std::cout << "Noise gate threshold set to: " << mic_noise_gate_threshold << std::endl;
        return 0;
    }

    // Gürültü kapısı bırakma süresini ayarlar (milisaniye)
    int set_noise_gate_release(float ms) {
        mic_noise_gate_release_ms = std::max(0.0f, ms);
        std::cout << "Noise gate release set to: " << mic_noise_gate_release_ms << " ms" << std::endl;
        return 0;
    }

    // Yüksek Geçiren Filtre kesme frekansını ayarlar (Hz)
    int set_high_pass_filter_cutoff(float hz) {
        if (hz <= 0.0f || sample_rate == 0) {
            mic_hp_filter_alpha = 0.0f; // Filtreyi devre dışı bırak
            std::cout << "High-pass filter disabled." << std::endl;
        } else {
            // Basit bir birinci dereceden HPF katsayısı
            // alpha = 1 / (1 + 2 * PI * fc / fs)
            // y[n] = alpha * y[n-1] + x[n] - x[n-1]
            mic_hp_filter_alpha = 1.0f / (1.0f + 2.0f * M_PI * hz / sample_rate);
            std::cout << "High-pass filter cutoff set to: " << hz << " Hz (alpha: " << mic_hp_filter_alpha << ")" << std::endl;
        }
        // Filtre durumunu sıfırla
        std::fill(mic_hp_filter_prev_output.begin(), mic_hp_filter_prev_output.end(), 0.0f);
        std::fill(mic_hp_filter_prev_input.begin(), mic_hp_filter_prev_input.end(), 0.0f);
        return 0;
    }

    // Mikrofon giriş kazancını ayarlar (linear)
    int set_microphone_gain(float gain) {
        mic_input_gain = std::max(0.0f, gain); // Kazanç negatif olamaz
        std::cout << "Microphone input gain set to: " << mic_input_gain << std::endl;
        return 0;
    }

    // Mikrofon Düşük Geçiren Filtre kesme frekansını ayarlar (Hz)
    int set_microphone_low_pass_filter_cutoff(float hz) {
        if (hz <= 0.0f || sample_rate == 0) {
            mic_lp_filter_alpha = 0.0f; // Filtreyi devre dışı bırak
            std::cout << "Microphone low-pass filter disabled." << std::endl;
        } else {
            // Basit bir birinci dereceden LPF katsayısı
            // alpha = (2 * PI * fc * T) / (2 * PI * fc * T + 1)
            const double T = 1.0 / sample_rate;
            mic_lp_filter_alpha = (2.0 * M_PI * hz * T) / (2.0 * M_PI * hz * T + 1.0);
            std::cout << "Microphone low-pass filter cutoff set to: " << hz << " Hz (alpha: " << mic_lp_filter_alpha << ")" << std::endl;
        }
        // Filtre durumunu sıfırla
        std::fill(mic_lp_filter_prev_output.begin(), mic_lp_filter_prev_output.end(), 0.0f);
        return 0;
    }

    // Reverb azaltma seviyesini ayarlar (LPF olarak simüle edildi)
    int set_reverb_reduction_level(int level) {
        mic_reverb_lp_filter_prev_output.assign(channels, 0.0f); // Reset filter state
        if (level == 0 || sample_rate == 0) { // Off
            mic_reverb_lp_filter_alpha = 0.0f; // No filtering
            std::cout << "Reverb reduction disabled." << std::endl;
        } else {
            float cutoff_hz;
            // Level'a göre kesme frekansını ayarla (daha yüksek seviye = daha düşük kesme)
            switch (level) {
                case 1: cutoff_hz = 10000.0f; break; // Low
                case 2: cutoff_hz = 8000.0f; break;  // Medium
                case 3: cutoff_hz = 6000.0f; break;  // High
                case 4: cutoff_hz = 4000.0f; break;  // Very High
                default: cutoff_hz = 20000.0f; break; // Default to high for safety
            }
            const double T = 1.0 / sample_rate;
            mic_reverb_lp_filter_alpha = (2.0 * M_PI * cutoff_hz * T) / (2.0 * M_PI * cutoff_hz * T + 1.0);
            std::cout << "Reverb reduction level set to: " << level << " (Simulated with LPF cutoff: " << cutoff_hz << " Hz)" << std::endl;
        }
        return 0;
    }

    // De-esser seviyesini ayarlar (Basit yüksek raf filtresi olarak simüle edildi)
    int set_de_esser_level(int level) {
        // Reset filter state
        de_esser_x_prev.assign(channels, 0.0f); de_esser_x_prev2.assign(channels, 0.0f);
        de_esser_y_prev.assign(channels, 0.0f); de_esser_y_prev2.assign(channels, 0.0f);

        if (level == 0 || sample_rate == 0) { // Off
            mic_de_esser_gain = 1.0f; // 0dB linear gain
            // Clear filter coefficients
            for(int k=0; k<channels; ++k) {
                de_esser_b0[k] = 0.0f; de_esser_b1[k] = 0.0f; de_esser_b2[k] = 0.0f;
                de_esser_a1[k] = 0.0f; de_esser_a2[k] = 0.0f;
            }
            std::cout << "De-esser disabled." << std::endl;
        } else {
            float gain_db;
            switch (level) {
                case 1: gain_db = -3.0f; break;  // Low
                case 2: gain_db = -6.0f; break;  // Medium
                case 3: gain_db = -9.0f; break;  // High
                default: gain_db = 0.0f; break;
            }
            mic_de_esser_gain = std::pow(10.0f, gain_db / 20.0f); // Convert dB to linear gain

            // Basit bir yüksek raf filtresi için katsayıları hesapla (örnek)
            // Bu sadece bir simülasyon, gerçek de-esser dinamik bir filtredir.
            // Burada sabit bir kesme frekansı kullanıyoruz ve sadece kazancı ayarlıyoruz.
            mic_de_esser_cutoff_hz = 6000.0f; // Sibilansın tipik frekans aralığı
            
            // Bilinear transform kullanarak 1. dereceden high-shelf filter katsayıları
            // G = mic_de_esser_gain
            // w0 = 2 * PI * mic_de_esser_cutoff_hz / sample_rate
            // alpha = (tan(w0/2) - 1) / (tan(w0/2) + 1) for LPF, but for shelf it's different.
            // Using simplified coefficients for a basic high-shelf:
            // This is a very simplified model and might not sound like a perfect de-esser.
            // A common approximation for a high-shelf is to use a low-pass filter and blend.
            // Let's use a simpler gain application based on the high-pass filtered signal.

            // For a simple high-shelf effect, we can combine a high-pass filter with the original signal
            // and apply gain to the high-pass part.
            // However, the current structure expects IIR filter coefficients.
            // Let's use a simplified digital biquad filter for high-shelf.
            // From Audio EQ Cookbook (simplified for high-shelf):
            // V0 = pow(10, G / 20)
            // K = tan(pi * f0 / Fs)
            // norm = 1 / (1 + K/Q + K*K)
            // b0 = (1 + sqrt(V0)*K/Q + V0*K*K) * norm
            // b1 = 2 * (V0*K*K - 1) * norm
            // b2 = (1 - sqrt(V0)*K/Q + V0*K*K) * norm
            // a1 = 2 * (K*K - 1) * norm
            // a2 = (1 - K/Q + K*K) * norm
            // Q for de-esser is usually not a fixed value, but for simplicity, let's use a fixed Q.
            float Q_val = 0.707f; // A common Q value for shelving filters (Butterworth)

            float A = std::pow(10.0f, gain_db / 40.0f); // Convert dB to amplitude ratio for shelf
            float omega = 2.0f * M_PI * mic_de_esser_cutoff_hz / sample_rate;
            float sn = std::sin(omega);
            float cs = std::cos(omega);
            float alpha_shelf = sn / (2.0f * Q_val); // Q factor

            float b0_val, b1_val, b2_val, a0_val, a1_val, a2_val;

            // High-Shelf filter coefficients (from Audio EQ Cookbook, simplified for G)
            // For cutting (gain_db < 0), A < 1
            b0_val = A * ((A + 1) + (A - 1) * cs + 2 * std::sqrt(A) * alpha_shelf);
            b1_val = -2 * A * ((A - 1) + (A + 1) * cs);
            b2_val = A * ((A + 1) + (A - 1) * cs - 2 * std::sqrt(A) * alpha_shelf);
            a0_val = (A + 1) - (A - 1) * cs + 2 * std::sqrt(A) * alpha_shelf;
            a1_val = -2 * ((A - 1) + (A + 1) * cs);
            a2_val = (A + 1) - (A - 1) * cs - 2 * std::sqrt(A) * alpha_shelf;

            for(int k=0; k<channels; ++k) {
                de_esser_b0[k] = b0_val / a0_val;
                de_esser_b1[k] = b1_val / a0_val;
                de_esser_b2[k] = b2_val / a0_val;
                de_esser_a1[k] = a1_val / a0_val;
                de_esser_a2[k] = a2_val / a0_val;
            }
            std::cout << "De-esser level set to: " << level << " (Simulated with high-shelf gain: " << gain_db << " dB)" << std::endl;
        }
        return 0;
    }

    // De-hum seviyesini ayarlar (Çentik filtresi)
    int set_de_hum_level(int level) {
        // Reset filter state
        de_hum_x_prev.assign(channels, 0.0f); de_hum_x_prev2.assign(channels, 0.0f);
        de_hum_y_prev.assign(channels, 0.0f); de_hum_y_prev2.assign(channels, 0.0f);

        if (level == 0 || sample_rate == 0) { // Off
            de_hum_enabled = false;
            // Clear filter coefficients
            for(int k=0; k<channels; ++k) {
                de_hum_b0[k] = 0.0f; de_hum_b1[k] = 0.0f; de_hum_b2[k] = 0.0f;
                de_hum_a1[k] = 0.0f; de_hum_a2[k] = 0.0f;
            }
            std::cout << "De-hum disabled." << std::endl;
        } else {
            de_hum_enabled = true;
            // Q faktörünü seviyeye göre ayarla (daha yüksek seviye = daha dar çentik)
            switch (level) {
                case 1: mic_de_hum_q = 10.0f; break; // Low (wider)
                case 2: mic_de_hum_q = 30.0f; break; // Medium (default, narrower)
                case 3: mic_de_hum_q = 60.0f; break; // High (very narrow)
                default: mic_de_hum_q = 30.0f; break;
            }

            // Çentik filtresi katsayılarını hesapla (50Hz veya 60Hz)
            // Burada 50Hz varsayıyoruz (Avrupa/Azerbaycan için yaygın)
            float omega0 = 2.0f * M_PI * de_hum_frequency_hz / sample_rate;
            float alpha_notch = std::sin(omega0) / (2.0f * mic_de_hum_q);

            float b0_val = 1.0f;
            float b1_val = -2.0f * std::cos(omega0);
            float b2_val = 1.0f;
            float a0_val = 1.0f + alpha_notch;
            float a1_val = -2.0f * std::cos(omega0);
            float a2_val = 1.0f - alpha_notch;

            for(int k=0; k<channels; ++k) {
                de_hum_b0[k] = b0_val / a0_val;
                de_hum_b1[k] = b1_val / a0_val;
                de_hum_b2[k] = b2_val / a0_val;
                de_hum_a1[k] = a1_val / a0_val;
                de_hum_a2[k] = a2_val / a0_val;
            }
            std::cout << "De-hum level set to: " << level << " (Notch filter at " << de_hum_frequency_hz << " Hz, Q: " << mic_de_hum_q << ")" << std::endl;
        }
        return 0;
    }

    // Compressor Threshold
    int set_mic_compressor_threshold(float db_threshold) {
        mic_comp_threshold_db = db_threshold;
        std::cout << "Compressor Threshold set to: " << db_threshold << " dB" << std::endl;
        return 0;
    }

    // Compressor Ratio
    int set_mic_compressor_ratio(float ratio) {
        mic_comp_ratio = std::max(1.0f, ratio); // Ratio must be >= 1.0
        std::cout << "Compressor Ratio set to: " << ratio << ":1" << std::endl;
        return 0;
    }

    // Compressor Attack Time
    int set_mic_compressor_attack(float ms) {
        mic_comp_attack_ms = std::max(0.1f, ms); // Minimum attack time
        std::cout << "Compressor Attack set to: " << ms << " ms" << std::endl;
        return 0;
    }

    // Compressor Release Time
    int set_mic_compressor_release(float ms) {
        mic_comp_release_ms = std::max(1.0f, ms); // Minimum release time
        std::cout << "Compressor Release set to: " << ms << " ms" << std::endl;
        return 0;
    }

    // Compressor Makeup Gain
    int set_mic_compressor_makeup_gain(float db_gain) {
        mic_comp_makeup_gain_db = db_gain;
        std::cout << "Compressor Makeup Gain set to: " << db_gain << " dB" << std::endl;
        return 0;
    }

    // Parametric EQ Gain
    int set_mic_eq_gain(float db_gain) {
        mic_eq_gain_db = db_gain;
        mic_eq_enabled = (db_gain != 0.0f); // Enable if gain is not 0dB
        std::cout << "EQ Gain set to: " << db_gain << " dB" << std::endl;
        return 0;
    }

    // Parametric EQ Frequency
    int set_mic_eq_frequency(float hz) {
        mic_eq_frequency_hz = std::max(20.0f, std::min(20000.0f, hz)); // Clamp frequency
        std::cout << "EQ Frequency set to: " << hz << " Hz" << std::endl;
        return 0;
    }

    // Parametric EQ Q Factor
    int set_mic_eq_q(float q_val) {
        mic_eq_q = std::max(0.1f, q_val); // Q must be positive
        std::cout << "EQ Q Factor set to: " << q_val << std::endl;
        return 0;
    }

    // Helper to calculate Biquad Peak/Notch filter coefficients
    void calculate_eq_coefficients() {
        if (sample_rate == 0 || !mic_eq_enabled) {
            for(int k=0; k<channels; ++k) {
                eq_b0[k] = 1.0f; eq_b1[k] = 0.0f; eq_b2[k] = 0.0f;
                eq_a1[k] = 0.0f; eq_a2[k] = 0.0f;
            }
            return; // No filtering if disabled or sample rate is zero
        }

        float A = std::pow(10.0f, mic_eq_gain_db / 40.0f); // Convert dB to amplitude ratio
        float omega = 2.0f * M_PI * mic_eq_frequency_hz / sample_rate;
        float sn = std::sin(omega);
        float cs = std::cos(omega);
        float alpha = sn / (2.0f * mic_eq_q);

        float b0_val, b1_val, b2_val, a0_val, a1_val, a2_val;

        // Peak/notch filter (from Audio EQ Cookbook)
        b0_val = 1.0f + alpha * A;
        b1_val = -2.0f * cs;
        b2_val = 1.0f - alpha * A;
        a0_val = 1.0f + alpha / A;
        a1_val = -2.0f * cs;
        a2_val = 1.0f - alpha / A;

        for(int k=0; k<channels; ++k) {
            eq_b0[k] = b0_val / a0_val;
            eq_b1[k] = b1_val / a0_val;
            eq_b2[k] = b2_val / a0_val;
            eq_a1[k] = a1_val / a0_val;
            eq_a2[k] = a2_val / a0_val;
        }
    }

    // Save recorded audio data to a file
    int save_recorded_audio_to_file(const std::string& filePath) {
        std::cout << "Saving recorded audio to: " << filePath << std::endl;
        if (recorded_audio_buffer.empty() || sample_rate == 0 || channels == 0) {
            std::cerr << "Error: No recorded audio data to save." << std::endl;
            return -1;
        }

        SF_INFO sfinfo;
        sfinfo.samplerate = sample_rate;
        sfinfo.channels = channels; // Kaydedilen buffer'ın kanal sayısını kullan
        sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_FLOAT;

        SNDFILE* outfile = sf_open(filePath.c_str(), SFM_WRITE, &sfinfo);
        if (!outfile) {
            std::cerr << "Error opening output file for saving recorded audio: " << filePath << " - " << sf_strerror(NULL) << std::endl;
            return -1;
        }

        sf_writef_float(outfile, recorded_audio_buffer.data(), recorded_audio_buffer.size() / channels);
        sf_close(outfile);

        std::cout << "Recorded audio successfully saved to: " << filePath << std::endl;
        return 0; // Success
    }

    // --- Mikrofon İşleme Fonksiyonları Sonu ---
};

// PortAudio geri çağırma fonksiyonunun implementasyonu (Kayıt)
// Bu fonksiyon, PortAudio tarafından ses verisi geldiğinde çağrılır.
static int pa_record_callback(const void *inputBuffer, void *outputBuffer,
                              unsigned long framesPerBuffer,
                              const PaStreamCallbackTimeInfo* timeInfo,
                              PaStreamCallbackFlags statusFlags,
                              void *userData)
{
    // DÜZELTME: -Wunused-parameter uyarılarını düzeltmek için kullanılmayan parametreleri (void) cast et.
    (void)outputBuffer;
    (void)timeInfo;
    (void)statusFlags;

    // userData, AudioEngine pointer'ını içerir.
    AudioEngine *engine = (AudioEngine*)userData;
    const float *in = (const float*)inputBuffer;

    if (inputBuffer == NULL) {
        // Giriş buffer'ı boşsa (örneğin, giriş cihazı yoksa)
        return paContinue;
    }

    // Kayıt modundaysak veriyi kaydet
    if (engine->is_recording_flag) {
        float noise_gate_release_gain_per_sample = 0.0f;
        if (engine->mic_noise_gate_release_ms > 0) {
            noise_gate_release_gain_per_sample = 1.0f / (engine->mic_noise_gate_release_ms / 1000.0f * engine->sample_rate);
        }

        // Compressor attack/release coefficients
        float comp_attack_coeff = 0.0f;
        if (engine->mic_comp_attack_ms > 0) {
            comp_attack_coeff = std::exp(-1.0f / (engine->mic_comp_attack_ms / 1000.0f * engine->sample_rate));
        }
        float comp_release_coeff = 0.0f;
        if (engine->mic_comp_release_ms > 0) {
            comp_release_coeff = std::exp(-1.0f / (engine->mic_comp_release_ms / 1000.0f * engine->sample_rate));
        }

        // Calculate EQ coefficients once per buffer if EQ is enabled
        if (engine->mic_eq_enabled) {
            engine->calculate_eq_coefficients();
        }


        for (unsigned long i = 0; i < framesPerBuffer; ++i) {
            for (int k = 0; k < engine->channels; ++k) {
                float sample = in[i * engine->channels + k];

                // 1. Mikrofon Giriş Kazancı Uygula
                sample *= engine->mic_input_gain;

                // 2. Yüksek Geçiren Filtre (HPF) Uygula (sadece mikrofon için)
                if (engine->mic_hp_filter_alpha > 0.0f) {
                    float filtered_hp = engine->mic_hp_filter_alpha * engine->mic_hp_filter_prev_output[k] +
                                        sample - engine->mic_hp_filter_prev_input[k];
                    engine->mic_hp_filter_prev_input[k] = sample;
                    engine->mic_hp_filter_prev_output[k] = filtered_hp;
                    sample = filtered_hp;
                }

                // 3. Düşük Geçiren Filtre (LPF) Uygula (sadece mikrofon için)
                if (engine->mic_lp_filter_alpha > 0.0f) {
                    float filtered_lp = engine->mic_lp_filter_alpha * sample +
                                        (1.0f - engine->mic_lp_filter_alpha) * engine->mic_lp_filter_prev_output[k];
                    engine->mic_lp_filter_prev_output[k] = filtered_lp;
                    sample = filtered_lp;
                }

                // 4. Gürültü Kapısı (Noise Gate) Uygula (sadece mikrofon için)
                float current_amplitude = std::abs(sample);
                if (current_amplitude >= engine->mic_noise_gate_threshold) {
                    // Eşik üzerinde, kapıyı aç
                    engine->mic_noise_gate_gain[k] = 1.0f;
                } else {
                    // Eşik altında, kazancı düşür (release)
                    engine->mic_noise_gate_gain[k] = std::max(0.0f, engine->mic_noise_gate_gain[k] - noise_gate_release_gain_per_sample);
                }
                sample *= engine->mic_noise_gate_gain[k];

                // --- Yeni DSP Efektleri ---

                // 5. De-hum (Çentik Filtresi)
                if (engine->de_hum_enabled) {
                    float x_current = sample;
                    float y_current = engine->de_hum_b0[k] * x_current + engine->de_hum_b1[k] * engine->de_hum_x_prev[k] + engine->de_hum_b2[k] * engine->de_hum_x_prev2[k]
                                    - engine->de_hum_a1[k] * engine->de_hum_y_prev[k] - engine->de_hum_a2[k] * engine->de_hum_y_prev2[k];
                    engine->de_hum_x_prev2[k] = engine->de_hum_x_prev[k];
                    engine->de_hum_x_prev[k] = x_current;
                    engine->de_hum_y_prev2[k] = engine->de_hum_y_prev[k];
                    engine->de_hum_y_prev[k] = y_current;
                    sample = y_current;
                }

                // 6. De-esser (Basit Yüksek Raf Filtresi)
                if (engine->de_esser_b0[k] != 0.0f || engine->de_esser_b1[k] != 0.0f || engine->de_esser_b2[k] != 0.0f) { // Filtre aktifse
                    float x_current = sample;
                    float y_current = engine->de_esser_b0[k] * x_current + engine->de_esser_b1[k] * engine->de_esser_x_prev[k] + engine->de_esser_b2[k] * engine->de_esser_x_prev2[k]
                                    - engine->de_esser_a1[k] * engine->de_esser_y_prev[k] - engine->de_esser_a2[k] * engine->de_esser_y_prev2[k];
                    engine->de_esser_x_prev2[k] = engine->de_esser_x_prev[k];
                    engine->de_esser_x_prev[k] = x_current;
                    engine->de_esser_y_prev2[k] = engine->de_esser_y_prev[k];
                    engine->de_esser_y_prev[k] = y_current;
                    sample = y_current;
                }

                // 7. Reverb Azaltma (LPF olarak simüle edildi)
                if (engine->mic_reverb_lp_filter_alpha > 0.0f) {
                    float filtered_reverb_lp = engine->mic_reverb_lp_filter_alpha * sample +
                                               (1.0f - engine->mic_reverb_lp_filter_alpha) * engine->mic_reverb_lp_filter_prev_output[k];
                    engine->mic_reverb_lp_filter_prev_output[k] = filtered_reverb_lp;
                    sample = filtered_reverb_lp;
                }

                // 8. Compressor
                // Envelope follower (peak detector with attack/release)
                float abs_sample = std::abs(sample);
                if (abs_sample > engine->mic_comp_envelope[k]) { // Attack
                    engine->mic_comp_envelope[k] = comp_attack_coeff * engine->mic_comp_envelope[k] + (1.0f - comp_attack_coeff) * abs_sample;
                } else { // Release
                    engine->mic_comp_envelope[k] = comp_release_coeff * engine->mic_comp_envelope[k] + (1.0f - comp_release_coeff) * abs_sample;
                }

                // Convert threshold from dB to linear
                float threshold_linear = std::pow(10.0f, engine->mic_comp_threshold_db / 20.0f);

                float gain_reduction = 1.0f;
                if (engine->mic_comp_ratio > 1.0f && engine->mic_comp_envelope[k] > threshold_linear) {
                    // Calculate gain reduction in dB
                    float gain_reduction_db = (engine->mic_comp_envelope[k] - threshold_linear) * (1.0f - (1.0f / engine->mic_comp_ratio));
                    gain_reduction = std::pow(10.0f, -gain_reduction_db / 20.0f);
                }
                
                // Apply makeup gain
                float makeup_gain_linear = std::pow(10.0f, engine->mic_comp_makeup_gain_db / 20.0f);

                sample *= gain_reduction * makeup_gain_linear;

                // 9. Parametric EQ
                if (engine->mic_eq_enabled) {
                    float x_current = sample;
                    float y_current = engine->eq_b0[k] * x_current + engine->eq_b1[k] * engine->eq_x_prev[k] + engine->eq_b2[k] * engine->eq_x_prev2[k]
                                    - engine->eq_a1[k] * engine->eq_y_prev[k] - engine->eq_a2[k] * engine->eq_y_prev2[k];
                    engine->eq_x_prev2[k] = engine->eq_x_prev[k];
                    engine->eq_x_prev[k] = x_current;
                    engine->eq_y_prev2[k] = engine->eq_y_prev[k];
                    engine->eq_y_prev[k] = y_current;
                    sample = y_current;
                }

                // --- Yeni DSP Efektleri Sonu ---


                engine->recorded_audio_buffer.push_back(sample);
            }
        }
    } // End of if (engine->is_recording_flag) block.
    return paContinue; // This should be the final return for the function.
}

// PortAudio geri çağırma fonksiyonunun implementasyonu (Oynatma)
// Bu fonksiyon, PortAudio tarafından ses verisi istendiğinde çağrılır.
static int pa_playback_callback(const void *inputBuffer, void *outputBuffer,
                                unsigned long framesPerBuffer,
                                const PaStreamCallbackTimeInfo* timeInfo,
                                PaStreamCallbackFlags statusFlags,
                                void *userData)
{
    // DÜZELTME: -Wunused-parameter uyarılarını düzeltmek için kullanılmayan parametreleri (void) cast et.
    (void)inputBuffer;
    (void)timeInfo;

    AudioEngine *engine = (AudioEngine*)userData;
    float *out = (float*)outputBuffer;
    unsigned long frames_to_write;
    long total_frames_in_buffer = engine->audio_buffer.size() / engine->channels;

    // Mevcut pozisyondan itibaren yeterli veri olup olmadığını kontrol et
    long remaining_frames = total_frames_in_buffer - engine->playback_frame_index;

    if (remaining_frames <= 0) {
        // Ses bitti, buffer'ı sıfırla ve oynatmayı durdur
        for (unsigned long i = 0; i < framesPerBuffer * engine->channels; ++i) {
            out[i] = 0.0f;
        }
        engine->is_playing_flag = false;
        engine->current_play_position_ms = engine->total_duration_ms; // Pozisyonu sona ayarla
        return paComplete; // Oynatma tamamlandı
    }

    // Yazılacak kare sayısını belirle
    frames_to_write = std::min(framesPerBuffer, (unsigned long)remaining_frames);

    // Ses verisini çıkış buffer'ına kopyala
    long start_idx = engine->playback_frame_index * engine->channels;
    if (start_idx + frames_to_write * engine->channels > engine->audio_buffer.size()) {
        // Bu durum olmamalı, ancak güvenlik için ek kontrol
        std::cerr << "Playback callback: Buffer overrun detected! Adjusting frames_to_write." << std::endl;
        frames_to_write = (engine->audio_buffer.size() - start_idx) / engine->channels;
        // DÜZELTME: -Wtype-limits uyarısını düzeltmek için gereksiz olan 'if (frames_to_write < 0)' kontrolü kaldırıldı.
        // 'frames_to_write' zaten 'unsigned long' tipindedir.
    }

    if (frames_to_write > 0) {
        for (unsigned long i = 0; i < frames_to_write; ++i) {
            for (int k = 0; k < engine->channels; ++k) {
                // DÜZELTME: -Wsign-compare uyarısını düzeltmek için 'long' -> 'size_t'
                size_t current_audio_buffer_idx = (engine->playback_frame_index + i) * engine->channels + k;
                if (current_audio_buffer_idx < engine->audio_buffer.size()) {
                    float input_sample = engine->audio_buffer[current_audio_buffer_idx];
                    // Düşük geçiren filtreyi uygula (birinci dereceden)
                    // y[n] = alpha * x[n] + (1 - alpha) * y[n-1]
                    float filtered_sample = engine->lp_filter_alpha * input_sample +
                                            (1.0f - engine->lp_filter_alpha) * engine->lp_filter_prev_output[k];
                    out[i * engine->channels + k] = filtered_sample;
                    engine->lp_filter_prev_output[k] = filtered_sample; // Sonraki iterasyon için önceki çıktıyı güncelle
                } else {
                    out[i * engine->channels + k] = 0.0f; // Sınır dışındaysa sessizlikle doldur
                }
            }
        }
        engine->playback_frame_index += frames_to_write; // Pozisyonu güncelle
        // current_play_position_ms'i de burada güncelleyelim
        engine->current_play_position_ms = static_cast<int>((static_cast<double>(engine->playback_frame_index) / engine->sample_rate) * 1000);
    }

    // Kalan buffer'ı sıfırla (sessizlik)
    if (frames_to_write < framesPerBuffer) {
        for (unsigned long i = frames_to_write * engine->channels; i < framesPerBuffer * engine->channels; ++i) {
            out[i] = 0.0f;
        }
    }

    // Durum bayraklarını kontrol et ve logla
    if (statusFlags & paInputUnderflow) {
        std::cerr << "Playback callback: Input Underflow!" << std::endl;
    }
    if (statusFlags & paInputOverflow) {
        std::cerr << "Playback callback: Input Overflow!" << std::endl;
    }
    if (statusFlags & paOutputUnderflow) {
        std::cerr << "Playback callback: Output Underflow! (Kırılma nedeni olabilir)" << std::endl;
    }
    if (statusFlags & paOutputOverflow) {
        std::cerr << "Playback callback: Output Overflow!" << std::endl;
    }
    if (statusFlags & paPrimingOutput) {
        // std::cerr << "Playback callback: Priming Output." << std::endl; // Normal bir durum
    }

    if (engine->is_playing_flag) { // Sadece is_playing_flag true ise devam et
        return paContinue;
    } else {
        return paComplete; // Oynatma tamamlandı veya durduruldu
    }
}


// C interface functions (extern "C" ensures C-style linking)
extern "C" {
    // Create a new AudioEngine instance and return a pointer to it
    void* create_audio_engine() {
        try {
            AudioEngine* engine = new AudioEngine();
            return engine;
        }
        catch (const std::exception& e) { std::cerr << "Exception during AudioEngine creation: " << e.what() << std::endl; return nullptr; }
        catch (...) { std::cerr << "Unknown exception during AudioEngine creation." << std::endl; return nullptr; }
    }

    // Destroy an AudioEngine instance given its pointer
    int destroy_audio_engine(void* ptr) {
        if (ptr) {
            try { delete static_cast<AudioEngine*>(ptr); return 0; }
            catch (const std::exception& e) { std::cerr << "Exception during AudioEngine destruction: " << e.what() << std::endl; return -1; }
            catch (...) { std::cerr << "Unknown exception during AudioEngine destruction." << std::endl; return -1; }
        }
        return -1; // Null pointer
    }

    // Load audio files using the C interface
    // Note: Python's ctypes.POINTER(ctypes.c_char_p) maps to char** in C
    int load_audio_files(void* ptr, char** filePaths, int numFiles) {
        if (!ptr || !filePaths) return -1;
        return static_cast<AudioEngine*>(ptr)->load_files(filePaths, numFiles);
    }

    // --- Playback Control C Functions ---
    int play_audio(void* ptr) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->play(); }
    int pause_audio(void* ptr) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->pause(); }
    int stop_audio(void* ptr) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->stop(); }

    // --- Information Retrieval C Functions ---
    int get_position_ms(void* ptr) { if (!ptr) return 0; return static_cast<AudioEngine*>(ptr)->get_position_ms(); }
    int get_duration_ms(void* ptr) { if (!ptr) return 0; return static_cast<AudioEngine*>(ptr)->get_duration_ms(); }
    int get_is_playing(void* ptr) { if (!ptr) return 0; return static_cast<AudioEngine*>(ptr)->get_is_playing(); }

    // --- Waveform Data C Functions ---
    int get_envelope_length(void* ptr) { if (!ptr) return 0; return static_cast<AudioEngine*>(ptr)->get_envelope_length(); }
    const float* get_envelope_data(void* ptr) { if (!ptr) return nullptr; return static_cast<AudioEngine*>(ptr)->get_envelope_data(); }

    // --- Settings C Functions ---
    int set_speed(void* ptr, float speed) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_speed(speed); }
    // int set_segment_duration(void* ptr, int ms) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_segment_duration(ms); } // Bu satır kaldırıldı
    int set_play_position_ms(void* ptr, int ms) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_play_position_ms(ms); }

    // --- Editing C Functions ---
    int delete_audio_segment(void* ptr, int start_ms, int end_ms) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->delete_segment(start_ms, end_ms); }
    int insert_audio_file(void* ptr, const char* filePath, int position_ms) { if (!ptr || !filePath) return -1; return static_cast<AudioEngine*>(ptr)->insert_audio(std::string(filePath), position_ms); }

    // --- Microphone Recording C Functions ---
    int start_microphone_recording(void* ptr) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->start_microphone_recording(); }
    int stop_microphone_recording(void* ptr) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->stop_microphone_recording(); }
    int play_recorded_audio(void* ptr) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->play_recorded_audio(); }
    int insert_recorded_audio(void* ptr, int position_ms) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->insert_recorded_audio(position_ms); }

    // --- Save Audio C Function ---
    int save_audio_to_file(void* ptr, const char* filePath) { if (!ptr || !filePath) return -1; return static_cast<AudioEngine*>(ptr)->save_to_file(std::string(filePath)); }

    // --- Yeni Eklenen Mikrofon İşleme C Fonksiyonları ---
    int set_mic_noise_gate_threshold(void* ptr, float threshold) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_noise_gate_threshold(threshold); }
    // DÜZELTME: Hata (Error) 2 - 'set_mic_noise_gate_release' -> 'set_noise_gate_release'
    int set_mic_noise_gate_release(void* ptr, float ms) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_noise_gate_release(ms); }
    // DÜZELTME: Hata (Error) 3 - 'set_mic_high_pass_filter_cutoff' -> 'set_high_pass_filter_cutoff'
    int set_mic_high_pass_filter_cutoff(void* ptr, float hz) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_high_pass_filter_cutoff(hz); }
    int set_mic_input_gain(void* ptr, float gain) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_microphone_gain(gain); }
    int set_mic_low_pass_filter_cutoff(void* ptr, float hz) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_microphone_low_pass_filter_cutoff(hz); }
    int set_mic_reverb_reduction_level(void* ptr, int level) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_reverb_reduction_level(level); }
    int set_mic_de_esser_level(void* ptr, int level) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_de_esser_level(level); }
    int set_mic_de_hum_level(void* ptr, int level) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_de_hum_level(level); }
    
    // Yeni Eklenen Compressor Fonksiyonları
    int set_mic_compressor_threshold(void* ptr, float db_threshold) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_compressor_threshold(db_threshold); }
    int set_mic_compressor_ratio(void* ptr, float ratio) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_compressor_ratio(ratio); }
    int set_mic_compressor_attack(void* ptr, float ms) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_compressor_attack(ms); }
    int set_mic_compressor_release(void* ptr, float ms) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_compressor_release(ms); }
    int set_mic_compressor_makeup_gain(void* ptr, float db_gain) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_compressor_makeup_gain(db_gain); }

    // Yeni Eklenen Parametric EQ Fonksiyonları
    int set_mic_eq_gain(void* ptr, float db_gain) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_eq_gain(db_gain); }
    int set_mic_eq_frequency(void* ptr, float hz) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_eq_frequency(hz); }
    int set_mic_eq_q(void* ptr, float q_val) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_eq_q(q_val); }

    // EQ katsayılarını hesaplamak için yardımcı fonksiyon
    int calculate_eq_coefficients(void* ptr) { if (!ptr) return -1; static_cast<AudioEngine*>(ptr)->calculate_eq_coefficients(); return 0; }

    // Kaydedilen sesi bir dosyaya kaydetmek için yeni fonksiyon
    int save_recorded_audio_to_file(void* ptr, const char* filePath) {
        if (!ptr || !filePath) return -1;
        return static_cast<AudioEngine*>(ptr)->save_recorded_audio_to_file(std::string(filePath));
    }
    // --- Yeni Eklenen Mikrofon İşleme C Fonksiyonları Sonu ---

} // End of extern "C" block
