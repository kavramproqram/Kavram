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
#include <fstream>   // For EDL logging and text export
#include <sstream>   // For string stream manipulation
#include <chrono>    // For timestamps in EDL metadata
#include <iomanip>   // For std::put_time and std::setfill
#include <filesystem> // For project directory and safe copy operations

// libsndfile kütüphanesini dahil edin.
#include <sndfile.h> // Libsndfile başlık dosyası

// PortAudio kütüphanesini dahil edin.
// Kurulum: Arch Linux'ta `sudo pacman -S portaudio`
// Derleme sırasında `-lportaudio` eklemeniz gerekecek.
#include <portaudio.h> // PortAudio başlık dosyası

namespace fs = std::filesystem;

// Edit Decision List (EDL) ve Memento / Komut deseni için veri modelleri
enum class ActionType {
    LOAD_FILE,
    DELETE_SEGMENT,
    DELETE_SIMILAR_SEGMENTS,
    DELETE_BY_THICKNESS,
    INSERT_AUDIO,
    INSERT_RECORDING,
    UNDO,
    REDO
};

// EDL üzerinde saklanacak her bir düzenleme kararı (Command / Metadata)
struct AudioEditCommand {
    uint64_t id;
    ActionType type;
    std::string type_name;
    int start_ms;
    int end_ms;
    std::string timestamp;
    std::string description;
    std::string source_file_path;
    std::vector<float> saved_segment_data; // Undo/memento için saklanan orijinal ham ses parçası
};

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
    // --- PROJE DİZİNİ VE GÜVENLİ KOPYALAMA (COW / EDL) VERİLERİ ---
    std::string project_directory;        // varsayılan: "export/saund"
    std::string original_copy_path;       // varsayılan: "export/saund/original.wav"
    std::vector<AudioEditCommand> edl_log; // Chronological Edit Decision List
    uint64_t command_counter;

    // Gerçek ses verileri için depolama
    std::vector<float> audio_buffer; // Tüm ana ses verisi (interleaved float formatında)
    int sample_rate;                 // Sesin örnekleme oranı (Hz)
    int channels;                    // Sesin kanal sayısı

    int current_play_position_ms; // Current playback position in ms
    int total_duration_ms;        // Total audio duration in ms
    bool is_playing_flag;         // Playback status
    float current_speed;          // Playback speed
    std::vector<float> envelope_data_storage; // Gerçek dalga şekli verisi

    // --- UNDO / REDO Geçmiş Sistemi ---
    // Güvenlik ve stabilite için maks. 5 adım hafızada tutulacak. RAM şişmesi engellenir.
    std::vector<std::vector<float>> history_stack;
    int history_index;
    const size_t MAX_HISTORY_STEPS = 5;

    // Mikrofon kaydı için PortAudio özel değişkenleri
    PaStream *record_stream;            // PortAudio kayıt akışı
    std::vector<float> recorded_audio_buffer; // Kaydedilen ses verisi
    bool is_recording_flag;            // Recording status

    // Oynatma için PortAudio özel değişkenleri
    PaStream *play_stream;              // PortAudio oynatma akışı
    long playback_frame_index;          // Oynatma akışındaki mevcut kare indeksi
    double playback_position_frames = 0.0; // ← double çok önemli!

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
    AudioEngine() : project_directory("export/saund"),
                    original_copy_path("export/saund/original.wav"),
                    command_counter(0),
                    sample_rate(44100), channels(2),
                    current_play_position_ms(0), total_duration_ms(0),
                    is_playing_flag(false), current_speed(1.0f),
                    history_index(-1),
                    record_stream(nullptr), is_recording_flag(false),
                    play_stream(nullptr), playback_frame_index(0), playback_position_frames(0.0) {
        std::cout << "AudioEngine created with Safe Non-Destructive Storage & EDL support." << std::endl;
        
        // Proje dizin yapısını oluştur
        try {
            fs::create_directories(project_directory);
        } catch (const std::exception& e) {
            std::cerr << "Directory creation warning: " << e.what() << std::endl;
        }

        // PortAudio'yu başlat
        PaError err = Pa_Initialize();
        if (err != paNoError) {
            std::cerr << "PortAudio error during initialization: " << Pa_GetErrorText(err) << std::endl;
        }

        // Düşük Geçiren Filtre (Playback) parametrelerini başlat
        const double playback_lp_cutoff_frequency_hz = 3000.0;
        const double T_playback = 1.0 / sample_rate;
        lp_filter_alpha = (2.0 * M_PI * playback_lp_cutoff_frequency_hz * T_playback) / (2.0 * M_PI * playback_lp_cutoff_frequency_hz * T_playback + 1.0);
        lp_filter_prev_output.resize(channels, 0.0f);

        // --- Mikrofon İşleme Parametrelerini Başlat ---
        mic_noise_gate_threshold = 0.0001f; // -80dB
        mic_noise_gate_release_ms = 20.0f; // 20 ms
        mic_noise_gate_gain.resize(channels, 0.0f);
        mic_noise_gate_prev_sample.resize(channels, 0.0f);

        const float default_mic_hp_cutoff_frequency_hz = 150.0f;
        if (sample_rate > 0) {
            mic_hp_filter_alpha = 1.0f / (1.0f + 2.0f * M_PI * default_mic_hp_cutoff_frequency_hz / sample_rate);
        } else {
            mic_hp_filter_alpha = 0.0f;
        }
        mic_hp_filter_prev_output.resize(channels, 0.0f);
        mic_hp_filter_prev_input.resize(channels, 0.0f);

        mic_lp_filter_alpha = 0.0f;
        mic_lp_filter_prev_output.resize(channels, 0.0f);

        mic_input_gain = 1.0f;

        // Reverb Reduction (LPF)
        mic_reverb_lp_filter_alpha = 0.0f;
        mic_reverb_lp_filter_prev_output.resize(channels, 0.0f);

        // De-esser
        mic_de_esser_gain = 1.0f;
        mic_de_esser_cutoff_hz = 6000.0f;
        de_esser_b0.resize(channels, 0.0f); de_esser_b1.resize(channels, 0.0f); de_esser_b2.resize(channels, 0.0f);
        de_esser_a1.resize(channels, 0.0f); de_esser_a2.resize(channels, 0.0f);
        de_esser_x_prev.resize(channels, 0.0f); de_esser_x_prev2.resize(channels, 0.0f);
        de_esser_y_prev.resize(channels, 0.0f); de_esser_y_prev2.resize(channels, 0.0f);

        // De-hum
        de_hum_frequency_hz = 50.0f;
        mic_de_hum_q = 30.0f;
        de_hum_enabled = false;
        de_hum_b0.resize(channels, 0.0f); de_hum_b1.resize(channels, 0.0f); de_hum_b2.resize(channels, 0.0f);
        de_hum_a1.resize(channels, 0.0f); de_hum_a2.resize(channels, 0.0f);
        de_hum_x_prev.resize(channels, 0.0f); de_hum_x_prev2.resize(channels, 0.0f);
        de_hum_y_prev.resize(channels, 0.0f); de_hum_y_prev2.resize(channels, 0.0f);

        // Compressor
        mic_comp_threshold_db = 0.0f;
        mic_comp_ratio = 1.0f;
        mic_comp_attack_ms = 1.0f;
        mic_comp_release_ms = 100.0f;
        mic_comp_makeup_gain_db = 0.0f;
        mic_comp_envelope.resize(channels, 0.0f);
        mic_comp_gain.resize(channels, 1.0f);

        // Parametric EQ
        mic_eq_gain_db = 0.0f;
        mic_eq_frequency_hz = 1000.0f;
        mic_eq_q = 1.0f;
        mic_eq_enabled = false;
        eq_b0.resize(channels, 0.0f); eq_b1.resize(channels, 0.0f); eq_b2.resize(channels, 0.0f);
        eq_a1.resize(channels, 0.0f); eq_a2.resize(channels, 0.0f);
        eq_x_prev.resize(channels, 0.0f); eq_x_prev2.resize(channels, 0.0f);
        eq_y_prev.resize(channels, 0.0f); eq_y_prev2.resize(channels, 0.0f);
    }

    // Destructor
    ~AudioEngine() {
        std::cout << "AudioEngine destroying..." << std::endl;
        if (record_stream) {
            Pa_StopStream(record_stream);
            Pa_CloseStream(record_stream);
            record_stream = nullptr;
        }
        if (play_stream) {
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
        lp_filter_prev_output.clear();
        
        clear_history();

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
    }

    // Helper: Geçerli zaman damgasını alma
    std::string get_current_timestamp() {
        auto now = std::chrono::system_clock::now();
        auto in_time_t = std::chrono::system_clock::to_time_t(now);
        std::stringstream ss;
        ss.fill('0');
        struct tm timeinfo;
#if defined(_WIN32)
        localtime_s(&timeinfo, &in_time_t);
#else
        localtime_r(&in_time_t, &timeinfo);
#endif
        ss << std::put_time(&timeinfo, "%Y-%m-%d %H:%M:%S");
        return ss.str();
    }

    // EDL günlüğüne komut kaydetme ve metin dosyasını otomatik güncelleme
    void log_edl_command(ActionType type, const std::string& type_name, int start_ms, int end_ms, const std::string& desc, const std::string& src_path = "") {
        AudioEditCommand cmd;
        cmd.id = ++command_counter;
        cmd.type = type;
        cmd.type_name = type_name;
        cmd.start_ms = start_ms;
        cmd.end_ms = end_ms;
        cmd.timestamp = get_current_timestamp();
        cmd.description = desc;
        cmd.source_file_path = src_path;

        edl_log.push_back(cmd);
        export_edl_to_file();
    }

    // EDL kaydını metin dosyası şeklinde export/saund/edl_log.txt olarak dışa aktarma
    int export_edl_to_file() {
        try {
            fs::create_directories(project_directory);
            std::string edl_file_path = project_directory + "/edl_log.txt";
            std::ofstream outfile(edl_file_path);
            if (!outfile.is_open()) return -1;

            outfile << "====================================================\n";
            outfile << "           KAVRAM EDIT DECISION LIST (EDL)          \n";
            outfile << "====================================================\n";
            outfile << "Project Directory : " << project_directory << "\n";
            outfile << "Original WAV Copy : " << original_copy_path << "\n";
            outfile << "Current Duration  : " << total_duration_ms << " ms\n";
            outfile << "Sample Rate       : " << sample_rate << " Hz\n";
            outfile << "Channels          : " << channels << "\n";
            outfile << "----------------------------------------------------\n\n";

            for (const auto& cmd : edl_log) {
                outfile << "[" << cmd.id << "] " << cmd.timestamp << " | " << cmd.type_name << "\n";
                if (cmd.start_ms >= 0 || cmd.end_ms >= 0) {
                    outfile << "    Time Range: " << cmd.start_ms << " ms -> " << cmd.end_ms << " ms\n";
                }
                if (!cmd.source_file_path.empty()) {
                    outfile << "    Source File: " << cmd.source_file_path << "\n";
                }
                outfile << "    Description: " << cmd.description << "\n";
                outfile << "----------------------------------------------------\n";
            }
            outfile.close();
            return 0;
        } catch (...) {
            return -1;
        }
    }

    // Orijinal dosyanın kilitlenmemiş güvenli bir kopyasını alma (Non-Destructive copy)
    int safe_copy_original_file(const std::string& source_path) {
        try {
            fs::create_directories(project_directory);
            original_copy_path = project_directory + "/original.wav";
            
            // Eğer sistem destekliyorsa reflink (Linux cp --reflink=auto benzeri) veya standart kopya
            std::error_code ec;
            fs::copy_file(source_path, original_copy_path, fs::copy_options::overwrite_existing, ec);
            if (ec) {
                std::cerr << "Safe copy warning: " << ec.message() << std::endl;
                return -1;
            }
            std::cout << "Original sound safely copied to: " << original_copy_path << std::endl;
            return 0;
        } catch (const std::exception& e) {
            std::cerr << "Safe copy error: " << e.what() << std::endl;
            return -1;
        }
    }

    // --- GEÇMİŞ YÖNETİMİ (History Management for Undo/Redo) ---
    void clear_history() {
        history_stack.clear();
        history_index = -1;
    }

    void push_history() {
        if (history_index < static_cast<int>(history_stack.size()) - 1) {
            history_stack.erase(history_stack.begin() + history_index + 1, history_stack.end());
        }
        
        try {
            history_stack.push_back(audio_buffer); // Güvenli Kopya
            if (history_stack.size() > MAX_HISTORY_STEPS) {
                history_stack.erase(history_stack.begin());
            } else {
                history_index++;
            }
        } catch (const std::bad_alloc& e) {
            std::cerr << "Warning: Could not save undo state (Out of memory). Edits will not be undoable." << std::endl;
        }
    }

    int undo() {
        if (history_index > 0) {
            history_index--;
            audio_buffer = history_stack[history_index];
            recalculate_envelope_data();
            log_edl_command(ActionType::UNDO, "UNDO", -1, -1, "Reverted last action using command stack.");
            std::cout << "Undo successful. Returning to history index: " << history_index << std::endl;
            return 0;
        }
        return -1;
    }

    int redo() {
        if (history_index < static_cast<int>(history_stack.size()) - 1) {
            history_index++;
            audio_buffer = history_stack[history_index];
            recalculate_envelope_data();
            log_edl_command(ActionType::REDO, "REDO", -1, -1, "Re-applied action using command stack.");
            std::cout << "Redo successful. Returning to history index: " << history_index << std::endl;
            return 0;
        }
        return -1;
    }

    int can_undo() { return history_index > 0 ? 1 : 0; }
    int can_redo() { return history_index < static_cast<int>(history_stack.size()) - 1 ? 1 : 0; }

    // Yardımcı fonksiyon: Zarf verisini yeniden hesapla
    void recalculate_envelope_data() {
        envelope_data_storage.clear();
        if (audio_buffer.empty() || sample_rate == 0 || channels == 0) {
            total_duration_ms = 0;
            return;
        }

        const int ENVELOPE_MS_PER_POINT = 50; // Her 50 ms için bir nokta
        size_t frames_per_envelope_point = (sample_rate * ENVELOPE_MS_PER_POINT) / 1000;
        if (frames_per_envelope_point == 0) frames_per_envelope_point = 1;

        for (size_t i = 0; i < audio_buffer.size() / channels; i += frames_per_envelope_point) {
            float max_amplitude = 0.0f;
            for (size_t j = 0; j < frames_per_envelope_point; ++j) {
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
        
        // Yeni bir dosya yüklendiği için geçmişi tamamen sıfırla.
        clear_history(); 

        for (int i = 0; i < numFiles; ++i) {
            std::string filePath = filePaths[i];
            std::cout << "  Loading: " << filePath << std::endl;

            // Ilk dosyayı asıl dosyayı bozmamak için güvenli kopya konumuna kopyala
            if (i == 0) {
                safe_copy_original_file(filePath);
            }

            SF_INFO sfinfo;
            SNDFILE* infile = sf_open(filePath.c_str(), SFM_READ, &sfinfo);

            if (!infile) {
                std::cerr << "Error opening sound file: " << filePath << " - " << sf_strerror(NULL) << std::endl;
                audio_buffer.clear();
                return -1;
            }

            // İlk dosyanın örnekleme oranı ve kanal sayısını al
            if (i == 0) {
                sample_rate = sfinfo.samplerate;
                channels = sfinfo.channels;
            } else {
                if (sfinfo.samplerate != sample_rate || sfinfo.channels != channels) {
                    std::cerr << "Warning: Mismatch in sample rate or channels for " << filePath << ". Skipping." << std::endl;
                    sf_close(infile);
                    continue;
                }
            }

            std::vector<float> file_data(sfinfo.frames * sfinfo.channels);
            sf_readf_float(infile, file_data.data(), sfinfo.frames);
            sf_close(infile);

            audio_buffer.insert(audio_buffer.end(), file_data.begin(), file_data.end());

            // EDL günlüğüne ekle
            log_edl_command(ActionType::LOAD_FILE, "LOAD_FILE", 0, static_cast<int>((static_cast<double>(sfinfo.frames)/sfinfo.samplerate)*1000), "Loaded file into non-destructive engine.", filePath);
        }

        if (audio_buffer.empty() || sample_rate == 0 || channels == 0) {
            std::cerr << "No valid audio data loaded." << std::endl;
            return -1;
        }

        recalculate_envelope_data();
        push_history(); 

        std::cout << "Audio files loaded safely. Total duration: " << total_duration_ms << " ms." << std::endl;
        current_play_position_ms = 0;
        is_playing_flag = false;
        return 0;
    }

    // Play audio
    int play() {
        if (audio_buffer.empty() || sample_rate == 0 || channels == 0) {
            std::cerr << "Error: No audio data to play." << std::endl;
            return -1;
        }

        if (is_playing_flag) {
            std::cout << "Audio is already playing." << std::endl;
            return 0;
        }

        if (play_stream) {
            Pa_StopStream(play_stream);
            Pa_CloseStream(play_stream);
            play_stream = nullptr;
        }

        PaStreamParameters outputParameters;

        PaHostApiIndex targetApiIndex = Pa_GetDefaultHostApi();
        int host_api_count = Pa_GetHostApiCount();
        
        for (PaHostApiIndex i = 0; i < host_api_count; ++i) {
            const PaHostApiInfo* info = Pa_GetHostApiInfo(i);
            if (info) {
                std::string apiName = info->name;
                if (apiName.find("PulseAudio") != std::string::npos ||
                    apiName.find("ALSA") != std::string::npos) 
                {
                    targetApiIndex = i;
                    if (apiName.find("PulseAudio") != std::string::npos) {
                        std::cout << "AudioEngine: Found PulseAudio Host API for playback." << std::endl;
                        break;
                    }
                }
            }
        }

        const PaHostApiInfo* targetApiInfo = Pa_GetHostApiInfo(targetApiIndex);
        if (!targetApiInfo) {
             std::cerr << "Error: Could not get info for target Host API." << std::endl;
             return -1;
        }
        
        PaDeviceIndex device_index = targetApiInfo->defaultOutputDevice;
        if (device_index == paNoDevice) {
             std::cout << "AudioEngine: Target API has no default output. Falling back to overall default device." << std::endl;
             device_index = Pa_GetDefaultOutputDevice();
             if (device_index == paNoDevice) {
                std::cerr << "Error: No default output device found for any Host API." << std::endl;
                return -1;
             }
        } else {
            std::cout << "AudioEngine: Using Host API '" << targetApiInfo->name << "' for playback." << std::endl;
        }

        outputParameters.device = device_index;

        const PaDeviceInfo* deviceInfo = Pa_GetDeviceInfo(outputParameters.device);
        if (!deviceInfo) {
            std::cerr << "Error: Could not get device info for selected output device." << std::endl;
            return -1;
        }

        double playback_sample_rate = static_cast<double>(sample_rate);

        outputParameters.channelCount = channels;
        outputParameters.sampleFormat = paFloat32;
        outputParameters.suggestedLatency = deviceInfo->defaultHighOutputLatency;
        outputParameters.hostApiSpecificStreamInfo = NULL;

        PaError err = Pa_OpenStream(
            &play_stream,
            NULL,
            &outputParameters,
            playback_sample_rate,
            1024,
            paClipOff,
            pa_playback_callback,
            this
        );

        if (err != paNoError) {
            std::cerr << "PortAudio error during Pa_OpenStream for playback: " << Pa_GetErrorText(err) << std::endl;
            play_stream = nullptr;
            return -1;
        }

        err = Pa_StartStream(play_stream);
        if (err != paNoError) {
            std::cerr << "PortAudio error during Pa_StartStream for playback: " << Pa_GetErrorText(err) << std::endl;
            Pa_CloseStream(play_stream);
            play_stream = nullptr;
            return -1;
        }

        is_playing_flag = true;
        playback_frame_index = static_cast<long>((static_cast<double>(current_play_position_ms) / 1000.0) * sample_rate);

        std::cout << "Audio playback started." << std::endl;
        return 0;
    }

    // Pause audio
    int pause() {
        if (!is_playing_flag) {
            std::cout << "Audio is not playing." << std::endl;
            return 0;
        }
        if (play_stream) {
            PaError err = Pa_StopStream(play_stream);
            if (err != paNoError) {
                std::cerr << "PortAudio error during Pa_StopStream for pause: " << Pa_GetErrorText(err) << std::endl;
                return -1;
            }
        }
        is_playing_flag = false;
        std::cout << "Audio playback paused." << std::endl;
        return 0;
    }

    // Stop audio
    int stop() {
        if (!is_playing_flag && playback_frame_index == 0) {
            std::cout << "Audio is already stopped." << std::endl;
            return 0;
        }
        if (play_stream) {
            PaError err = Pa_StopStream(play_stream);
            if (err != paNoError) {
                std::cerr << "PortAudio error during Pa_StopStream for stop: " << Pa_GetErrorText(err) << std::endl;
                Pa_CloseStream(play_stream);
                play_stream = nullptr;
                is_playing_flag = false;
                current_play_position_ms = 0;
                playback_frame_index = 0;
                return -1;
            }
            Pa_CloseStream(play_stream);
            play_stream = nullptr;
        }
        is_playing_flag = false;
        current_play_position_ms = 0;
        playback_frame_index = 0;
        std::cout << "Audio playback stopped." << std::endl;
        return 0;
    }

    int get_position_ms() { return current_play_position_ms; }
    int get_duration_ms() { return total_duration_ms; }
    int get_envelope_length() { return envelope_data_storage.size(); }

    const float* get_envelope_data() {
        if (envelope_data_storage.empty()) return nullptr;
        return envelope_data_storage.data();
    }

    int set_speed(float speed) {
        std::cout << "Setting playback speed to " << speed << "x." << std::endl;
        current_speed = speed;
        return 0;
    }

    int set_play_position_ms(int ms) {
        if (ms < 0) ms = 0;
        if (ms > total_duration_ms) ms = total_duration_ms;

        current_play_position_ms = ms;
        long new_playback_frame_index = static_cast<long>((static_cast<double>(current_play_position_ms) / 1000.0) * sample_rate);
        playback_frame_index = new_playback_frame_index;
        playback_position_frames = (static_cast<double>(ms) / 1000.0) * sample_rate;

        std::cout << "Set playback position to " << ms << " ms. New frame index: " << playback_frame_index << std::endl;
        return 0; 
    }

    int get_is_playing() { return is_playing_flag ? 1 : 0; }

    // Delete a segment of audio
    int delete_segment(int start_ms, int end_ms) {
        std::cout << "Deleting audio segment from " << start_ms << " to " << end_ms << " ms (non-destructive EDL recorded)." << std::endl;
        if (audio_buffer.empty() || sample_rate == 0 || channels == 0) {
            std::cerr << "Error: No audio data to delete from." << std::endl;
            return -1;
        }

        long start_frame = static_cast<long>((static_cast<double>(start_ms) / 1000.0) * sample_rate);
        long end_frame = static_cast<long>((static_cast<double>(end_ms) / 1000.0) * sample_rate);

        start_frame = std::max(0L, start_frame);
        end_frame = std::min(static_cast<long>(audio_buffer.size() / channels), end_frame);

        if (start_frame >= end_frame) {
            std::cout << "No valid segment to delete." << std::endl;
            return 0;
        }

        long start_idx = start_frame * channels;
        long end_idx = end_frame * channels;

        audio_buffer.erase(audio_buffer.begin() + start_idx, audio_buffer.begin() + end_idx);

        recalculate_envelope_data();
        push_history(); 

        log_edl_command(ActionType::DELETE_SEGMENT, "DELETE_SEGMENT", start_ms, end_ms, "Cut audio range from buffer.");

        return 0;
    }

    // --- BENZER SES TESPİTİ VE OTOMATİK SİLME ALGORİTMASI ---
    int detect_and_delete_similar_segments(int start_ms, int end_ms, float threshold) {
        if (audio_buffer.empty() || sample_rate == 0 || channels == 0 || start_ms >= end_ms) {
            return -1;
        }

        push_history();

        long start_frame = static_cast<long>((static_cast<double>(start_ms) / 1000.0) * sample_rate);
        long end_frame = static_cast<long>((static_cast<double>(end_ms) / 1000.0) * sample_rate);
        long total_frames = audio_buffer.size() / channels;

        start_frame = std::max(0L, std::min(start_frame, total_frames));
        end_frame = std::max(0L, std::min(end_frame, total_frames));
        long pattern_len_frames = end_frame - start_frame;

        if (pattern_len_frames <= 0) {
            return 0; 
        }

        long step_size = (sample_rate * 2) / 1000; 
        if (step_size < 1) step_size = 1;

        long num_bins = total_frames / step_size;
        if (num_bins == 0) return 0;

        std::vector<float> global_energy(num_bins, 0.0f);
        std::vector<float> global_zcr(num_bins, 0.0f);

        for (long b = 0; b < num_bins; ++b) {
            float rms = 0.0f;
            long zcr_count = 0;
            long f_start = b * step_size;
            long f_end = std::min(f_start + step_size, total_frames);
            
            float prev_val = (f_start > 0) ? audio_buffer[(f_start - 1) * channels] : 0.0f;

            for (long f = f_start; f < f_end; ++f) {
                float current_val = audio_buffer[f * channels];
                if ((current_val >= 0.0f && prev_val < 0.0f) || (current_val < 0.0f && prev_val >= 0.0f)) {
                    zcr_count++;
                }
                prev_val = current_val;

                for (int c = 0; c < channels; ++c) {
                    float val = audio_buffer[f * channels + c];
                    rms += val * val;
                }
            }
            long count = f_end - f_start;
            global_energy[b] = std::sqrt(rms / (count > 0 ? count * channels : 1));
            global_zcr[b] = static_cast<float>(zcr_count) / (count > 0 ? count : 1);
        }

        long pattern_start_bin = start_frame / step_size;
        long pattern_end_bin = end_frame / step_size;
        long pattern_bins_count = pattern_end_bin - pattern_start_bin;

        if (pattern_bins_count <= 0) return 0;

        std::vector<float> pattern_energy(global_energy.begin() + pattern_start_bin, global_energy.begin() + pattern_end_bin);
        std::vector<float> pattern_zcr(global_zcr.begin() + pattern_start_bin, global_zcr.begin() + pattern_end_bin);

        float effective_threshold = std::min(threshold, 0.85f);

        float pattern_norm = 0.0f;
        float pattern_mean_zcr = 0.0f;
        for (size_t i = 0; i < pattern_energy.size(); ++i) {
            pattern_norm += pattern_energy[i] * pattern_energy[i];
            pattern_mean_zcr += pattern_zcr[i];
        }
        pattern_norm = std::sqrt(pattern_norm);
        if (pattern_norm == 0.0f) pattern_norm = 1.0f;
        pattern_mean_zcr /= pattern_energy.size();

        std::vector<std::pair<long, long>> segments_to_delete;

        for (long b = 0; b <= num_bins - pattern_bins_count; ++b) {
            float candidate_norm = 0.0f;
            float dot_product = 0.0f;
            float candidate_mean_zcr = 0.0f;

            for (long i = 0; i < pattern_bins_count; ++i) {
                float c_val = global_energy[b + i];
                candidate_norm += c_val * c_val;
                dot_product += pattern_energy[i] * c_val;
                candidate_mean_zcr += global_zcr[b + i];
            }
            candidate_norm = std::sqrt(candidate_norm);
            if (candidate_norm == 0.0f) candidate_norm = 1.0f;
            candidate_mean_zcr /= pattern_bins_count;

            float similarity = dot_product / (pattern_norm * candidate_norm);
            float amplitude_ratio = (pattern_norm > 0.0f && candidate_norm > 0.0f) ? (candidate_norm / pattern_norm) : 1.0f;
            float zcr_diff = std::abs(pattern_mean_zcr - candidate_mean_zcr);
            bool zcr_match = zcr_diff < 0.12f;

            if (similarity >= effective_threshold && amplitude_ratio > 0.3f && amplitude_ratio < 3.0f && zcr_match) {
                long del_start = b * step_size;
                long del_end = (b + pattern_bins_count) * step_size;
                segments_to_delete.push_back({del_start, del_end});
                b += pattern_bins_count - 1; 
            }
        }

        bool original_included = false;
        for (const auto& r : segments_to_delete) {
            if (std::abs(r.first - start_frame) < step_size * 2) {
                original_included = true;
                break;
            }
        }
        if (!original_included) {
            segments_to_delete.push_back({start_frame, end_frame});
        }

        std::sort(segments_to_delete.begin(), segments_to_delete.end(), [](const auto& a, const auto& b) {
            return a.first < b.first;
        });

        std::vector<std::pair<long, long>> merged_segments;
        if (!segments_to_delete.empty()) {
            merged_segments.push_back(segments_to_delete[0]);
            for (size_t i = 1; i < segments_to_delete.size(); ++i) {
                auto& last = merged_segments.back();
                if (segments_to_delete[i].first <= last.second) {
                    last.second = std::max(last.second, segments_to_delete[i].second);
                } else {
                    merged_segments.push_back(segments_to_delete[i]);
                }
            }
        }

        for (auto it = merged_segments.rbegin(); it != merged_segments.rend(); ++it) {
            long s_idx = it->first * channels;
            long e_idx = it->second * channels;
            if (s_idx >= 0 && e_idx <= static_cast<long>(audio_buffer.size())) {
                audio_buffer.erase(audio_buffer.begin() + s_idx, audio_buffer.begin() + e_idx);
            }
        }

        recalculate_envelope_data();
        log_edl_command(ActionType::DELETE_SIMILAR_SEGMENTS, "DELETE_SIMILAR", start_ms, end_ms, "Detected and deleted " + std::to_string(merged_segments.size()) + " similar audio pattern segments.");

        std::cout << "High-Accuracy Similar segments deleted. Count: " << merged_segments.size() << std::endl;
        return 0;
    }

    // --- KALINLIĞA (GENLİĞE/VOLUME) GÖRE BOŞLUK TEMİZLEME ALGORİTMASI ---
    int delete_segments_by_thickness(int start_ms, int end_ms) {
        if (audio_buffer.empty() || sample_rate == 0 || channels == 0 || start_ms >= end_ms) {
            return -1;
        }

        push_history();

        long start_frame = static_cast<long>((static_cast<double>(start_ms) / 1000.0) * sample_rate);
        long end_frame = static_cast<long>((static_cast<double>(end_ms) / 1000.0) * sample_rate);
        long total_frames = audio_buffer.size() / channels;

        start_frame = std::max(0L, std::min(start_frame, total_frames));
        end_frame = std::max(0L, std::min(end_frame, total_frames));

        if (start_frame >= end_frame) return 0;

        float max_thickness = 0.0f;
        for (long i = start_frame; i < end_frame; ++i) {
            for (int c = 0; c < channels; ++c) {
                float val = std::abs(audio_buffer[i * channels + c]);
                if (val > max_thickness) {
                    max_thickness = val;
                }
            }
        }

        float threshold = max_thickness * 1.2f;
        if (threshold < 0.001f) threshold = 0.001f;

        long window_frames = (sample_rate * 10) / 1000;
        if (window_frames < 1) window_frames = 1;
        
        long min_silence_frames = (sample_rate * 150) / 1000; 
        long padding_frames = (sample_rate * 25) / 1000; 

        std::vector<std::pair<long, long>> segments_to_delete;
        long current_silence_start = -1;

        for (long i = 0; i <= total_frames; i += window_frames) {
            long w_end = std::min(i + window_frames, total_frames);
            float w_max = 0.0f;
            
            if (i < total_frames) {
                for (long j = i; j < w_end; ++j) {
                    for (int c = 0; c < channels; ++c) {
                        float val = std::abs(audio_buffer[j * channels + c]);
                        if (val > w_max) w_max = val;
                    }
                }
            } else {
                w_max = threshold + 1.0f;
            }

            if (w_max <= threshold && i < total_frames) {
                if (current_silence_start == -1) {
                    current_silence_start = i;
                }
            } else {
                if (current_silence_start != -1) {
                    long silence_length = i - current_silence_start;
                    if (silence_length >= min_silence_frames) {
                        long del_start = current_silence_start + padding_frames;
                        long del_end = i - padding_frames;
                        if (del_end > del_start) {
                            segments_to_delete.push_back({del_start, del_end});
                        }
                    }
                    current_silence_start = -1;
                }
            }
        }

        segments_to_delete.push_back({start_frame, end_frame});

        std::sort(segments_to_delete.begin(), segments_to_delete.end(), [](const auto& a, const auto& b) {
            return a.first < b.first;
        });
        std::vector<std::pair<long, long>> merged_segments;
        if (!segments_to_delete.empty()) {
            merged_segments.push_back(segments_to_delete[0]);
            for (size_t i = 1; i < segments_to_delete.size(); ++i) {
                auto& last = merged_segments.back();
                if (segments_to_delete[i].first <= last.second) {
                    last.second = std::max(last.second, segments_to_delete[i].second);
                } else {
                    merged_segments.push_back(segments_to_delete[i]);
                }
            }
        }

        for (auto it = merged_segments.rbegin(); it != merged_segments.rend(); ++it) {
            long s_idx = it->first * channels;
            long e_idx = it->second * channels;
            if (s_idx >= 0 && e_idx <= static_cast<long>(audio_buffer.size())) {
                audio_buffer.erase(audio_buffer.begin() + s_idx, audio_buffer.begin() + e_idx);
            }
        }

        recalculate_envelope_data();
        log_edl_command(ActionType::DELETE_BY_THICKNESS, "DELETE_THICKNESS", start_ms, end_ms, "Deleted quiet/silence gaps based on thickness sample.");

        std::cout << "Thickness based deletion completed. Segments deleted: " << merged_segments.size() << std::endl;
        return 0;
    }

    // Insert audio data from a file
    int insert_audio(const std::string& filePath, int position_ms) {
        std::cout << "Inserting audio file '" << filePath << "' at position " << position_ms << " ms." << std::endl;
        if (sample_rate == 0 || channels == 0) {
            std::cerr << "Error: Main audio engine not initialized with sample rate/channels. Load a file first." << std::endl;
            return -1;
        }

        SF_INFO sfinfo;
        SNDFILE* infile = sf_open(filePath.c_str(), SFM_READ, &sfinfo);

        if (!infile) {
            std::cerr << "Error opening sound file for insertion: " << filePath << " - " << sf_strerror(NULL) << std::endl;
            return -1;
        }

        if (sfinfo.samplerate != sample_rate) {
            std::cerr << "Error: Sample rate mismatch for inserted file. Expected: "
                      << sample_rate << "Hz. Got: " << sfinfo.samplerate << "Hz." << std::endl;
            sf_close(infile);
            return -1;
        }

        std::vector<float> inserted_data(sfinfo.frames * sfinfo.channels);
        sf_readf_float(infile, inserted_data.data(), sfinfo.frames);
        sf_close(infile);

        std::vector<float> processed_inserted_data;
        if (sfinfo.channels == channels) {
            processed_inserted_data = inserted_data;
        } else if (sfinfo.channels == 1 && channels == 2) {
            processed_inserted_data.reserve(inserted_data.size() * 2);
            for (float sample : inserted_data) {
                processed_inserted_data.push_back(sample);
                processed_inserted_data.push_back(sample);
            }
        } else if (sfinfo.channels == 2 && channels == 1) {
            processed_inserted_data.reserve(inserted_data.size() / 2);
            for (size_t i = 0; i < inserted_data.size(); i += 2) {
                processed_inserted_data.push_back((inserted_data[i] + inserted_data[i+1]) / 2.0f);
            }
        } else {
            return -1;
        }

        long insert_frame = static_cast<long>((static_cast<double>(position_ms) / 1000.0) * sample_rate);
        insert_frame = std::max(0L, std::min(insert_frame, static_cast<long>(audio_buffer.size() / channels)));

        long insert_idx = insert_frame * channels;

        audio_buffer.insert(audio_buffer.begin() + insert_idx, processed_inserted_data.begin(), processed_inserted_data.end());

        recalculate_envelope_data();
        push_history();

        log_edl_command(ActionType::INSERT_AUDIO, "INSERT_AUDIO", position_ms, position_ms, "Inserted audio segment from external file.", filePath);

        return 0;
    }

    // Start microphone recording
    int start_microphone_recording() {
        std::cout << "Starting microphone recording." << std::endl;
        if (is_recording_flag) {
            std::cout << "Already recording." << std::endl;
            return 1;
        }

        PaStreamParameters inputParameters;
        
        PaHostApiIndex targetApiIndex = Pa_GetDefaultHostApi();
        int host_api_count = Pa_GetHostApiCount();
        
        for (PaHostApiIndex i = 0; i < host_api_count; ++i) {
            const PaHostApiInfo* info = Pa_GetHostApiInfo(i);
            if (info) {
                std::string apiName = info->name;
                if (apiName.find("PulseAudio") != std::string::npos ||
                    apiName.find("ALSA") != std::string::npos) 
                {
                    targetApiIndex = i;
                    if (apiName.find("PulseAudio") != std::string::npos) {
                        break;
                    }
                }
            }
        }

        const PaHostApiInfo* targetApiInfo = Pa_GetHostApiInfo(targetApiIndex);
        if (!targetApiInfo) return -1;

        PaDeviceIndex device_index = targetApiInfo->defaultInputDevice; 
        if (device_index == paNoDevice) {
             device_index = Pa_GetDefaultInputDevice();
             if (device_index == paNoDevice) return -1;
        }

        inputParameters.device = device_index;
        const PaDeviceInfo* deviceInfo = Pa_GetDeviceInfo(inputParameters.device);
        if (!deviceInfo) return -1;

        double recording_sample_rate = static_cast<double>(sample_rate);
        inputParameters.channelCount = channels;

        inputParameters.sampleFormat = paFloat32; 
        inputParameters.suggestedLatency = deviceInfo->defaultLowInputLatency;
        inputParameters.hostApiSpecificStreamInfo = NULL;

        PaError err = Pa_OpenStream(
            &record_stream,
            &inputParameters,
            NULL, 
            recording_sample_rate, 
            paFramesPerBufferUnspecified, 
            paClipOff, 
            pa_record_callback, 
            this 
        );

        if (err != paNoError) {
            record_stream = nullptr;
            return -1;
        }

        err = Pa_StartStream(record_stream);
        if (err != paNoError) {
            Pa_CloseStream(record_stream);
            record_stream = nullptr;
            return -1;
        }

        recorded_audio_buffer.clear(); 
        
        try {
            recorded_audio_buffer.reserve(sample_rate * channels * 1800);
        } catch(...) {}

        is_recording_flag = true;
        std::cout << "Microphone recording started." << std::endl;
        return 0;
    }

    // Stop microphone recording
    int stop_microphone_recording() {
        std::cout << "Stopping microphone recording." << std::endl;
        if (!is_recording_flag) {
            std::cout << "Not currently recording." << std::endl;
            return 1;
        }

        PaError err = Pa_StopStream(record_stream);
        if (err != paNoError) {
            Pa_CloseStream(record_stream);
            record_stream = nullptr;
            is_recording_flag = false;
            return -1;
        }

        err = Pa_CloseStream(record_stream);
        if (err != paNoError) {
            record_stream = nullptr;
            is_recording_flag = false;
            return -1;
        }

        record_stream = nullptr;
        is_recording_flag = false;
        std::cout << "Microphone recording stopped. Recorded " << recorded_audio_buffer.size() << " samples." << std::endl;
        return 0;
    }

    int play_recorded_audio() {
        return 0;
    }

    // Insert recorded audio into the timeline
    int insert_recorded_audio(int position_ms) {
        std::cout << "Inserting recorded audio at position " << position_ms << " ms." << std::endl;
        if (recorded_audio_buffer.empty()) {
            std::cerr << "Error: No recorded audio to insert." << std::endl;
            return -1;
        }
        
        float max_amplitude = 0.0f;
        for (float sample : recorded_audio_buffer) {
            max_amplitude = std::max(max_amplitude, std::abs(sample));
        }

        const float TARGET_AMPLITUDE = 0.9f; 
        
        if (max_amplitude > 0.0f) { 
            float scale_factor = TARGET_AMPLITUDE / max_amplitude;
            for (float& sample : recorded_audio_buffer) {
                sample *= scale_factor;
            }
        }

        if (sample_rate == 0 || channels == 0) { 
            std::cerr << "Error: Main audio engine not initialized with sample rate/channels. Load a file first." << std::endl;
            return -1;
        }

        if (channels == 2 && recorded_audio_buffer.size() % 2 != 0) { 
            std::vector<float> stereo_recorded_audio_buffer;
            stereo_recorded_audio_buffer.reserve(recorded_audio_buffer.size() * 2);
            for (float sample : recorded_audio_buffer) {
                stereo_recorded_audio_buffer.push_back(sample);
                stereo_recorded_audio_buffer.push_back(sample);
            }
            recorded_audio_buffer = stereo_recorded_audio_buffer;
        } else if (channels == 1 && recorded_audio_buffer.size() % 2 == 0 && recorded_audio_buffer.size() > 0) {
            std::vector<float> mono_recorded_audio_buffer;
            mono_recorded_audio_buffer.reserve(recorded_audio_buffer.size() / 2);
            for (size_t i = 0; i < recorded_audio_buffer.size(); i += 2) {
                mono_recorded_audio_buffer.push_back((recorded_audio_buffer[i] + recorded_audio_buffer[i+1]) / 2.0f);
            }
            recorded_audio_buffer = mono_recorded_audio_buffer;
        }

        long insert_frame = static_cast<long>((static_cast<double>(position_ms) / 1000.0) * sample_rate);
        insert_frame = std::max(0L, std::min(insert_frame, static_cast<long>(audio_buffer.size() / channels)));

        long insert_idx = insert_frame * channels;

        audio_buffer.insert(audio_buffer.begin() + insert_idx, recorded_audio_buffer.begin(), recorded_audio_buffer.end());

        recorded_audio_buffer.clear();
        recalculate_envelope_data();
        push_history();

        log_edl_command(ActionType::INSERT_RECORDING, "INSERT_MIC_RECORDING", position_ms, position_ms, "Inserted live microphone recording at cursor.");

        std::cout << "Recorded audio inserted. New total duration: " << total_duration_ms << " ms." << std::endl;
        return 0;
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
        sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_FLOAT; 

        SNDFILE* outfile = sf_open(filePath.c_str(), SFM_WRITE, &sfinfo);
        if (!outfile) {
            std::cerr << "Error opening output file for saving: " << filePath << " - " << sf_strerror(NULL) << std::endl;
            return -1;
        }

        sf_writef_float(outfile, audio_buffer.data(), audio_buffer.size() / channels);
        sf_close(outfile);

        // Export/Save işlemini de EDL kaydına not alıyoruz
        log_edl_command(ActionType::LOAD_FILE, "EXPORT_FILE", 0, total_duration_ms, "Exported final audio session to file.", filePath);

        return 0;
    }

    // --- Mikrofon İşleme Fonksiyonları ---
    int set_noise_gate_threshold(float threshold) {
        mic_noise_gate_threshold = std::max(0.0f, std::min(1.0f, threshold));
        return 0;
    }

    int set_noise_gate_release(float ms) {
        mic_noise_gate_release_ms = std::max(0.0f, ms);
        return 0;
    }

    int set_high_pass_filter_cutoff(float hz) {
        if (hz <= 0.0f || sample_rate == 0) {
            mic_hp_filter_alpha = 0.0f;
        } else {
            mic_hp_filter_alpha = 1.0f / (1.0f + 2.0f * M_PI * hz / sample_rate);
        }
        std::fill(mic_hp_filter_prev_output.begin(), mic_hp_filter_prev_output.end(), 0.0f);
        std::fill(mic_hp_filter_prev_input.begin(), mic_hp_filter_prev_input.end(), 0.0f);
        return 0;
    }

    int set_microphone_gain(float gain) {
        mic_input_gain = std::max(0.0f, gain);
        return 0;
    }

    int set_microphone_low_pass_filter_cutoff(float hz) {
        if (hz <= 0.0f || sample_rate == 0) {
            mic_lp_filter_alpha = 0.0f; 
        } else {
            const double T = 1.0 / sample_rate;
            mic_lp_filter_alpha = (2.0 * M_PI * hz * T) / (2.0 * M_PI * hz * T + 1.0);
        }
        std::fill(mic_lp_filter_prev_output.begin(), mic_lp_filter_prev_output.end(), 0.0f);
        return 0;
    }

    int set_reverb_reduction_level(int level) {
        mic_reverb_lp_filter_prev_output.assign(channels, 0.0f); 
        if (level == 0 || sample_rate == 0) { 
            mic_reverb_lp_filter_alpha = 0.0f; 
        } else {
            float cutoff_hz;
            switch (level) {
                case 1: cutoff_hz = 10000.0f; break; 
                case 2: cutoff_hz = 8000.0f; break;  
                case 3: cutoff_hz = 6000.0f; break;  
                case 4: cutoff_hz = 4000.0f; break;  
                default: cutoff_hz = 20000.0f; break; 
            }
            const double T = 1.0 / sample_rate;
            mic_reverb_lp_filter_alpha = (2.0 * M_PI * cutoff_hz * T) / (2.0 * M_PI * cutoff_hz * T + 1.0);
        }
        return 0;
    }

    int set_de_esser_level(int level) {
        de_esser_x_prev.assign(channels, 0.0f); de_esser_x_prev2.assign(channels, 0.0f);
        de_esser_y_prev.assign(channels, 0.0f); de_esser_y_prev2.assign(channels, 0.0f);

        if (level == 0 || sample_rate == 0) { 
            mic_de_esser_gain = 1.0f; 
            for(int k=0; k<channels; ++k) {
                de_esser_b0[k] = 0.0f; de_esser_b1[k] = 0.0f; de_esser_b2[k] = 0.0f;
                de_esser_a1[k] = 0.0f; de_esser_a2[k] = 0.0f;
            }
        } else {
            float gain_db;
            switch (level) {
                case 1: gain_db = -3.0f; break;  
                case 2: gain_db = -6.0f; break;  
                case 3: gain_db = -9.0f; break;  
                default: gain_db = 0.0f; break;
            }
            mic_de_esser_gain = std::pow(10.0f, gain_db / 20.0f); 
            mic_de_esser_cutoff_hz = 6000.0f; 
            
            float Q_val = 0.707f; 

            float A = std::pow(10.0f, gain_db / 40.0f); 
            float omega = 2.0f * M_PI * mic_de_esser_cutoff_hz / sample_rate;
            float sn = std::sin(omega);
            float cs = std::cos(omega);
            float alpha_shelf = sn / (2.0f * Q_val); 

            float b0_val, b1_val, b2_val, a0_val, a1_val, a2_val;

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
        }
        return 0;
    }

    int set_de_hum_level(int level) {
        de_hum_x_prev.assign(channels, 0.0f); de_hum_x_prev2.assign(channels, 0.0f);
        de_hum_y_prev.assign(channels, 0.0f); de_hum_y_prev2.assign(channels, 0.0f);

        if (level == 0 || sample_rate == 0) { 
            de_hum_enabled = false;
            for(int k=0; k<channels; ++k) {
                de_hum_b0[k] = 0.0f; de_hum_b1[k] = 0.0f; de_hum_b2[k] = 0.0f;
                de_hum_a1[k] = 0.0f; de_hum_a2[k] = 0.0f;
            }
        } else {
            de_hum_enabled = true;
            switch (level) {
                case 1: mic_de_hum_q = 10.0f; break; 
                case 2: mic_de_hum_q = 30.0f; break; 
                case 3: mic_de_hum_q = 60.0f; break; 
                default: mic_de_hum_q = 30.0f; break;
            }

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
        }
        return 0;
    }

    int set_mic_compressor_threshold(float db_threshold) {
        mic_comp_threshold_db = db_threshold;
        return 0;
    }

    int set_mic_compressor_ratio(float ratio) {
        mic_comp_ratio = std::max(1.0f, ratio); 
        return 0;
    }

    int set_mic_compressor_attack(float ms) {
        mic_comp_attack_ms = std::max(0.1f, ms); 
        return 0;
    }

    int set_mic_compressor_release(float ms) {
        mic_comp_release_ms = std::max(1.0f, ms); 
        return 0;
    }

    int set_mic_compressor_makeup_gain(float db_gain) {
        mic_comp_makeup_gain_db = db_gain;
        return 0;
    }

    int set_mic_eq_gain(float db_gain) {
        mic_eq_gain_db = db_gain;
        mic_eq_enabled = (db_gain != 0.0f); 
        return 0;
    }

    int set_mic_eq_frequency(float hz) {
        mic_eq_frequency_hz = std::max(20.0f, std::min(20000.0f, hz)); 
        return 0;
    }

    int set_mic_eq_q(float q_val) {
        mic_eq_q = std::max(0.1f, q_val); 
        return 0;
    }

    void calculate_eq_coefficients() {
        if (sample_rate == 0 || !mic_eq_enabled) {
            for(int k=0; k<channels; ++k) {
                eq_b0[k] = 1.0f; eq_b1[k] = 0.0f; eq_b2[k] = 0.0f;
                eq_a1[k] = 0.0f; eq_a2[k] = 0.0f;
            }
            return; 
        }

        float A = std::pow(10.0f, mic_eq_gain_db / 40.0f); 
        float omega = 2.0f * M_PI * mic_eq_frequency_hz / sample_rate;
        float sn = std::sin(omega);
        float cs = std::cos(omega);
        float alpha = sn / (2.0f * mic_eq_q);

        float b0_val, b1_val, b2_val, a0_val, a1_val, a2_val;

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

    int save_recorded_audio_to_file(const std::string& filePath) {
        std::cout << "Saving recorded audio to: " << filePath << std::endl;
        if (recorded_audio_buffer.empty() || sample_rate == 0 || channels == 0) {
            std::cerr << "Error: No recorded audio data to save." << std::endl;
            return -1;
        }

        SF_INFO sfinfo;
        sfinfo.samplerate = sample_rate;
        sfinfo.channels = channels; 
        sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_FLOAT;

        SNDFILE* outfile = sf_open(filePath.c_str(), SFM_WRITE, &sfinfo);
        if (!outfile) {
            std::cerr << "Error opening output file for saving recorded audio: " << filePath << " - " << sf_strerror(NULL) << std::endl;
            return -1;
        }

        sf_writef_float(outfile, recorded_audio_buffer.data(), recorded_audio_buffer.size() / channels);
        sf_close(outfile);

        return 0;
    }
};

// PortAudio geri çağırma fonksiyonunun implementasyonu (Kayıt)
static int pa_record_callback(const void *inputBuffer, void *outputBuffer,
                              unsigned long framesPerBuffer,
                              const PaStreamCallbackTimeInfo* timeInfo,
                              PaStreamCallbackFlags statusFlags,
                              void *userData)
{
    (void)outputBuffer;
    (void)timeInfo;
    (void)statusFlags;

    AudioEngine *engine = (AudioEngine*)userData;
    const float *in = (const float*)inputBuffer;

    if (inputBuffer == NULL) {
        return paContinue;
    }

    if (engine->is_recording_flag) {
        float noise_gate_release_gain_per_sample = 0.0f;
        if (engine->mic_noise_gate_release_ms > 0) {
            noise_gate_release_gain_per_sample = 1.0f / (engine->mic_noise_gate_release_ms / 1000.0f * engine->sample_rate);
        }

        float comp_attack_coeff = 0.0f;
        if (engine->mic_comp_attack_ms > 0) {
            comp_attack_coeff = std::exp(-1.0f / (engine->mic_comp_attack_ms / 1000.0f * engine->sample_rate));
        }
        float comp_release_coeff = 0.0f;
        if (engine->mic_comp_release_ms > 0) {
            comp_release_coeff = std::exp(-1.0f / (engine->mic_comp_release_ms / 1000.0f * engine->sample_rate));
        }

        if (engine->mic_eq_enabled) {
            engine->calculate_eq_coefficients();
        }

        for (unsigned long i = 0; i < framesPerBuffer; ++i) {
            for (int k = 0; k < engine->channels; ++k) {
                float sample = in[i * engine->channels + k];

                sample *= engine->mic_input_gain;

                if (engine->mic_hp_filter_alpha > 0.0f) {
                    float filtered_hp = engine->mic_hp_filter_alpha * engine->mic_hp_filter_prev_output[k] +
                                        sample - engine->mic_hp_filter_prev_input[k];
                    engine->mic_hp_filter_prev_input[k] = sample;
                    engine->mic_hp_filter_prev_output[k] = filtered_hp;
                    sample = filtered_hp;
                }

                if (engine->mic_lp_filter_alpha > 0.0f) {
                    float filtered_lp = engine->mic_lp_filter_alpha * sample +
                                        (1.0f - engine->mic_lp_filter_alpha) * engine->mic_lp_filter_prev_output[k];
                    engine->mic_lp_filter_prev_output[k] = filtered_lp;
                    sample = filtered_lp;
                }

                float current_amplitude = std::abs(sample);
                if (current_amplitude >= engine->mic_noise_gate_threshold) {
                    engine->mic_noise_gate_gain[k] = 1.0f;
                } else {
                    engine->mic_noise_gate_gain[k] = std::max(0.0f, engine->mic_noise_gate_gain[k] - noise_gate_release_gain_per_sample);
                }
                sample *= engine->mic_noise_gate_gain[k];

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

                if (engine->de_esser_b0[k] != 0.0f || engine->de_esser_b1[k] != 0.0f || engine->de_esser_b2[k] != 0.0f) { 
                    float x_current = sample;
                    float y_current = engine->de_esser_b0[k] * x_current + engine->de_esser_b1[k] * engine->de_esser_x_prev[k] + engine->de_esser_b2[k] * engine->de_esser_x_prev2[k]
                                    - engine->de_esser_a1[k] * engine->de_esser_y_prev[k] - engine->de_esser_a2[k] * engine->de_esser_y_prev2[k];
                    engine->de_esser_x_prev2[k] = engine->de_esser_x_prev[k];
                    engine->de_esser_x_prev[k] = x_current;
                    engine->de_esser_y_prev2[k] = engine->de_esser_y_prev[k];
                    engine->de_esser_y_prev[k] = y_current;
                    sample = y_current;
                }

                if (engine->mic_reverb_lp_filter_alpha > 0.0f) {
                    float filtered_reverb_lp = engine->mic_reverb_lp_filter_alpha * sample +
                                               (1.0f - engine->mic_reverb_lp_filter_alpha) * engine->mic_reverb_lp_filter_prev_output[k];
                    engine->mic_reverb_lp_filter_prev_output[k] = filtered_reverb_lp;
                    sample = filtered_reverb_lp;
                }

                float abs_sample = std::abs(sample);
                if (abs_sample > engine->mic_comp_envelope[k]) { 
                    engine->mic_comp_envelope[k] = comp_attack_coeff * engine->mic_comp_envelope[k] + (1.0f - comp_attack_coeff) * abs_sample;
                } else { 
                    engine->mic_comp_envelope[k] = comp_release_coeff * engine->mic_comp_envelope[k] + (1.0f - comp_release_coeff) * abs_sample;
                }

                float threshold_linear = std::pow(10.0f, engine->mic_comp_threshold_db / 20.0f);

                float gain_reduction = 1.0f;
                if (engine->mic_comp_ratio > 1.0f && engine->mic_comp_envelope[k] > threshold_linear) {
                    float gain_reduction_db = (engine->mic_comp_envelope[k] - threshold_linear) * (1.0f - (1.0f / engine->mic_comp_ratio));
                    gain_reduction = std::pow(10.0f, -gain_reduction_db / 20.0f);
                }
                
                float makeup_gain_linear = std::pow(10.0f, engine->mic_comp_makeup_gain_db / 20.0f);
                sample *= gain_reduction * makeup_gain_linear;

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

                engine->recorded_audio_buffer.push_back(sample);
            }
        }
    } 
    return paContinue; 
}

// PortAudio geri çağırma fonksiyonunun implementasyonu (Oynatma)
static int pa_playback_callback(const void *inputBuffer, void *outputBuffer,
                                unsigned long framesPerBuffer,
                                const PaStreamCallbackTimeInfo* timeInfo,
                                PaStreamCallbackFlags statusFlags,
                                void *userData)
{
    (void)inputBuffer;
    (void)timeInfo;
    (void)statusFlags;

    AudioEngine *engine = (AudioEngine*)userData;
    float *out = (float*)outputBuffer;
    unsigned long frames_to_write;
    long total_frames_in_buffer = engine->audio_buffer.size() / engine->channels;

    double speed = engine->current_speed;
    if (speed != 1.0f) {
        engine->playback_position_frames = static_cast<double>(engine->playback_frame_index);

        for (unsigned long i = 0; i < framesPerBuffer; ++i)
        {
            long src_frame = static_cast<long>(engine->playback_position_frames);
            if (src_frame >= total_frames_in_buffer) {
                for (int k = 0; k < engine->channels; ++k) {
                    out[i * engine->channels + k] = 0.0f;
                }
                engine->is_playing_flag = false;
                engine->current_play_position_ms = engine->total_duration_ms;
                return paComplete;
            }
            for (int k = 0; k < engine->channels; ++k)
            {
                size_t idx = src_frame * engine->channels + k;
                float sample = (idx < engine->audio_buffer.size()) ?
                               engine->audio_buffer[idx] : 0.0f;
                float filtered = engine->lp_filter_alpha * sample +
                                 (1.0f - engine->lp_filter_alpha) * engine->lp_filter_prev_output[k];
                out[i * engine->channels + k] = filtered;
                engine->lp_filter_prev_output[k] = filtered;
            }
            engine->playback_position_frames += speed; 
        }
        engine->current_play_position_ms = static_cast<int>(
            (engine->playback_position_frames / engine->sample_rate) * 1000.0
        );
        engine->playback_frame_index = static_cast<long>(engine->playback_position_frames);
        return paContinue;
    }

    long remaining_frames = total_frames_in_buffer - engine->playback_frame_index;

    if (remaining_frames <= 0) {
        for (unsigned long i = 0; i < framesPerBuffer * engine->channels; ++i) {
            out[i] = 0.0f;
        }
        engine->is_playing_flag = false;
        engine->current_play_position_ms = engine->total_duration_ms; 
        return paComplete; 
    }

    frames_to_write = std::min(framesPerBuffer, (unsigned long)remaining_frames);

    long start_idx = engine->playback_frame_index * engine->channels;
    if (start_idx + frames_to_write * engine->channels > engine->audio_buffer.size()) {
        frames_to_write = (engine->audio_buffer.size() - start_idx) / engine->channels;
    }

    if (frames_to_write > 0) {
        for (unsigned long i = 0; i < frames_to_write; ++i) {
            for (int k = 0; k < engine->channels; ++k) {
                size_t current_audio_buffer_idx = (engine->playback_frame_index + i) * engine->channels + k;
                if (current_audio_buffer_idx < engine->audio_buffer.size()) {
                    float input_sample = engine->audio_buffer[current_audio_buffer_idx];
                    float filtered_sample = engine->lp_filter_alpha * input_sample +
                                            (1.0f - engine->lp_filter_alpha) * engine->lp_filter_prev_output[k];
                    out[i * engine->channels + k] = filtered_sample;
                    engine->lp_filter_prev_output[k] = filtered_sample; 
                } else {
                    out[i * engine->channels + k] = 0.0f; 
                }
            }
        }
        engine->playback_frame_index += frames_to_write; 
        engine->current_play_position_ms = static_cast<int>((static_cast<double>(engine->playback_frame_index) / engine->sample_rate) * 1000);
    }

    if (frames_to_write < framesPerBuffer) {
        for (unsigned long i = frames_to_write * engine->channels; i < framesPerBuffer * engine->channels; ++i) {
            out[i] = 0.0f;
        }
    }

    if (engine->is_playing_flag) { 
        return paContinue;
    } else {
        return paComplete; 
    }
}

// C interface functions (extern "C" ensures C-style linking)
extern "C" {
    void* create_audio_engine() {
        try {
            AudioEngine* engine = new AudioEngine();
            return engine;
        }
        catch (...) { return nullptr; }
    }

    int destroy_audio_engine(void* ptr) {
        if (ptr) {
            try { delete static_cast<AudioEngine*>(ptr); return 0; }
            catch (...) { return -1; }
        }
        return -1;
    }

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
    int set_play_position_ms(void* ptr, int ms) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_play_position_ms(ms); }

    // --- Editing C Functions ---
    int delete_audio_segment(void* ptr, int start_ms, int end_ms) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->delete_segment(start_ms, end_ms); }
    int insert_audio_file(void* ptr, const char* filePath, int position_ms) { if (!ptr || !filePath) return -1; return static_cast<AudioEngine*>(ptr)->insert_audio(std::string(filePath), position_ms); }

    // --- Benzer Sesleri Otomatik Silme C Fonksiyonu ---
    int detect_and_delete_similar(void* ptr, int start_ms, int end_ms, float threshold) {
        if (!ptr) return -1;
        return static_cast<AudioEngine*>(ptr)->detect_and_delete_similar_segments(start_ms, end_ms, threshold);
    }
    
    // --- Kalınlığa (Amplitude) Göre Sesleri Silme C Fonksiyonu ---
    int delete_segments_by_thickness(void* ptr, int start_ms, int end_ms) {
        if (!ptr) return -1;
        return static_cast<AudioEngine*>(ptr)->delete_segments_by_thickness(start_ms, end_ms);
    }

    // --- Microphone Recording C Functions ---
    int start_microphone_recording(void* ptr) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->start_microphone_recording(); }
    int stop_microphone_recording(void* ptr) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->stop_microphone_recording(); }
    int play_recorded_audio(void* ptr) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->play_recorded_audio(); }
    int insert_recorded_audio(void* ptr, int position_ms) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->insert_recorded_audio(position_ms); }

    // --- Save Audio C Function ---
    int save_audio_to_file(void* ptr, const char* filePath) { if (!ptr || !filePath) return -1; return static_cast<AudioEngine*>(ptr)->save_to_file(std::string(filePath)); }

    // --- Undo / Redo C Functions ---
    int undo_audio(void* ptr) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->undo(); }
    int redo_audio(void* ptr) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->redo(); }
    int can_undo_audio(void* ptr) { if (!ptr) return 0; return static_cast<AudioEngine*>(ptr)->can_undo(); }
    int can_redo_audio(void* ptr) { if (!ptr) return 0; return static_cast<AudioEngine*>(ptr)->can_redo(); }

    // --- EDL (Edit Decision List) Export C Function ---
    int export_edl_log(void* ptr) {
        if (!ptr) return -1;
        return static_cast<AudioEngine*>(ptr)->export_edl_to_file();
    }

    // --- Mikrofon İşleme C Fonksiyonları ---
    int set_mic_noise_gate_threshold(void* ptr, float threshold) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_noise_gate_threshold(threshold); }
    int set_mic_noise_gate_release(void* ptr, float ms) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_noise_gate_release(ms); }
    int set_mic_high_pass_filter_cutoff(void* ptr, float hz) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_high_pass_filter_cutoff(hz); }
    int set_mic_input_gain(void* ptr, float gain) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_microphone_gain(gain); }
    int set_mic_low_pass_filter_cutoff(void* ptr, float hz) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_microphone_low_pass_filter_cutoff(hz); }
    int set_mic_reverb_reduction_level(void* ptr, int level) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_reverb_reduction_level(level); }
    int set_mic_de_esser_level(void* ptr, int level) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_de_esser_level(level); }
    int set_mic_de_hum_level(void* ptr, int level) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_de_hum_level(level); }
    
    // Compressor Fonksiyonları
    int set_mic_compressor_threshold(void* ptr, float db_threshold) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_compressor_threshold(db_threshold); }
    int set_mic_compressor_ratio(void* ptr, float ratio) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_compressor_ratio(ratio); }
    int set_mic_compressor_attack(void* ptr, float ms) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_compressor_attack(ms); }
    int set_mic_compressor_release(void* ptr, float ms) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_compressor_release(ms); }
    int set_mic_compressor_makeup_gain(void* ptr, float db_gain) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_compressor_makeup_gain(db_gain); }

    // Parametric EQ Fonksiyonları
    int set_mic_eq_gain(void* ptr, float db_gain) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_eq_gain(db_gain); }
    int set_mic_eq_frequency(void* ptr, float hz) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_eq_frequency(hz); }
    int set_mic_eq_q(void* ptr, float q_val) { if (!ptr) return -1; return static_cast<AudioEngine*>(ptr)->set_mic_eq_q(q_val); }

    int calculate_eq_coefficients(void* ptr) { if (!ptr) return -1; static_cast<AudioEngine*>(ptr)->calculate_eq_coefficients(); return 0; }

    int save_recorded_audio_to_file(void* ptr, const char* filePath) {
        if (!ptr || !filePath) return -1;
        return static_cast<AudioEngine*>(ptr)->save_recorded_audio_to_file(std::string(filePath));
    }
} // End of extern "C" block
