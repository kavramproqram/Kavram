/*
 * Kavram 2.2.2
 * Copyright (C) 2026-07-22 Kavram or Contributors
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
 * along with this program. If not, see /Kavram/License/GPLv3.txt
 *
 * ---------------------------------------------
 *
 * Kavram 2.2.2
 * Copyright (C) 2026-07-22 Kavram veya Contributors
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

// media_engine.cpp
//
// Bu tek kaynak dosya İKİ çıktı üretir (derleme komutları media/derleme.txt içindedir):
//
//  1) media_engine.so   (kütüphane, Python ctypes ile yüklenir)
//       - zaman çizelgesi hesapları, ffprobe ile ölçüm (süre, boyut, döndürme),
//         kare-doğrusu (frame-accurate) kesme, .media arşivleme/çıkarma, dosya silme,
//         yedek ses kaydı (PortAudio; halka tamponlu + yazıcı iş parçacığı).
//       - OpenCV artık GEREKMEZ.
//
//  2) media_recorder    (ayrı süreç; -DMEDIA_RECORDER_MAIN ile derlenir, GStreamer kullanır)
//       - Kamera + mikrofon (tek MKV, ses/görüntü aynı saatte) ya da yalnızca mikrofon (WAV) kaydı.
//       - Algoritma rec_engine ile aynıdır: v4l2src/pulsesrc -> tee -> kayıt dalı + önizleme dalı,
//         sızıntılı (leaky) kuyruklar, EOS ile temiz kapanış, kamera modu yeniden deneme,
//         önizleme /dev/shm paylaşımlı belleğe yazılır. X11 ve Wayland'da aynı çalışır
//         (kamera ve mikrofon için ekran sunucusu gerekmez).
//
// SÜRÜM NOTU (3.0):
//  - Eski sürümdeki OpenCV kamera/oynatma kodu kaldırıldı; export (render) artık Python tarafında
//    tek geçişli FFmpeg filtre grafiğiyle yapılıyor (en-boy oranı, fps, ses biçimi normalize edilir).
//  - Kesme (cut) artık yeniden kodlayarak yapılır: kesim noktası tam kare doğrulukta, ses/görüntü kaymaz.
//  - Ses kaydı: callback içinde dosya yazma yok (halka tampon + yazıcı iş parçacığı), tek WAV dosyası.

#ifndef MEDIA_RECORDER_MAIN
// =============================================================================
//                               KÜTÜPHANE (.so)
// =============================================================================
#include <portaudio.h>
#include <sndfile.h>
#include <string>
#include <vector>
#include <atomic>
#include <thread>
#include <chrono>
#include <iostream>
#include <sstream>
#include <iomanip>
#include <fstream>
#include <algorithm>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cctype>
#include <climits>
#include <cerrno>
#include <unistd.h>
#include <spawn.h>
#include <poll.h>
#include <fcntl.h>
#include <signal.h>
#include <sys/wait.h>

extern char **environ;

static std::string g_ffmpeg = "ffmpeg";
static std::string g_ffprobe = "ffprobe";

// Shell için güvenli tek tırnaklama (yalnızca tar komutu için).
static std::string shell_quote(const std::string& value) {
    std::string quoted("'");
    for (char c : value) {
        if (c == '\'') quoted += "'\\''"; else quoted += c;
    }
    quoted += "'";
    return quoted;
}

struct RunResult {
    int code = -1;          // çıkış kodu (sinyalle ölürse 128+sinyal), başlatılamazsa -1
    bool timed_out = false;
    std::string out;        // yakalanan çıktı (en fazla ~256 KB; fazlası atılır, SONU saklanır)
};

// Kabuk kullanmadan program çalıştırır (posix_spawn). stdin /dev/null.
static RunResult run_argv(const std::vector<std::string>& args, int timeout_ms, bool capture_stdout, bool capture_stderr) {
    RunResult r;
    if (args.empty()) return r;

    int pfd[2] = {-1, -1};
    const bool use_pipe = capture_stdout || capture_stderr;
    if (use_pipe && pipe2(pfd, O_CLOEXEC) != 0) return r;

    posix_spawn_file_actions_t fa;
    posix_spawn_file_actions_init(&fa);
    posix_spawn_file_actions_addopen(&fa, 0, "/dev/null", O_RDONLY, 0);
    if (capture_stdout) posix_spawn_file_actions_adddup2(&fa, pfd[1], 1);
    else posix_spawn_file_actions_addopen(&fa, 1, "/dev/null", O_WRONLY, 0);
    if (capture_stderr) posix_spawn_file_actions_adddup2(&fa, pfd[1], 2);
    else posix_spawn_file_actions_addopen(&fa, 2, "/dev/null", O_WRONLY, 0);

    std::vector<char*> argv;
    for (const auto& a : args) argv.push_back(const_cast<char*>(a.c_str()));
    argv.push_back(nullptr);

    pid_t pid = 0;
    const int rc = posix_spawnp(&pid, argv[0], &fa, nullptr, argv.data(), environ);
    posix_spawn_file_actions_destroy(&fa);
    if (use_pipe) close(pfd[1]);
    if (rc != 0) {
        if (use_pipe) close(pfd[0]);
        return r;
    }

    const auto start = std::chrono::steady_clock::now();
    if (use_pipe) {
        char buf[4096];
        for (;;) {
            struct pollfd p; p.fd = pfd[0]; p.events = POLLIN; p.revents = 0;
            const int pr = poll(&p, 1, 100);
            if (pr > 0) {
                const ssize_t n = read(pfd[0], buf, sizeof(buf));
                if (n > 0) {
                    r.out.append(buf, static_cast<size_t>(n));
                    if (r.out.size() > 262144) r.out.erase(0, r.out.size() - 131072);
                } else if (n == 0) {
                    break;
                } else if (errno != EINTR && errno != EAGAIN) {
                    break;
                }
            }
            if (timeout_ms > 0) {
                const auto el = std::chrono::duration_cast<std::chrono::milliseconds>(
                    std::chrono::steady_clock::now() - start).count();
                if (el > timeout_ms) { kill(pid, SIGKILL); r.timed_out = true; break; }
            }
        }
        close(pfd[0]);
    } else if (timeout_ms > 0) {
        for (;;) {
            int st = 0;
            const pid_t w = waitpid(pid, &st, WNOHANG);
            if (w == pid) {
                r.code = WIFEXITED(st) ? WEXITSTATUS(st) : 128 + WTERMSIG(st);
                return r;
            }
            const auto el = std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::steady_clock::now() - start).count();
            if (el > timeout_ms) { kill(pid, SIGKILL); r.timed_out = true; break; }
            usleep(20000);
        }
    }

    int status = 0;
    while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {}
    r.code = WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
    return r;
}

static int execute_external_command(const std::string& cmd) {
    RunResult r = run_argv({"/bin/sh", "-c", cmd}, 0, false, true);
    if (r.code != 0) {
        std::cerr << "C++: komut başarısız (" << r.code << "): " << cmd << std::endl;
        if (!r.out.empty()) std::cerr << r.out << std::endl;
    }
    return r.code;
}

static std::string lower_ext(const std::string& path) {
    const size_t dot = path.find_last_of('.');
    const size_t slash = path.find_last_of('/');
    if (dot == std::string::npos || (slash != std::string::npos && dot < slash)) return "";
    std::string e = path.substr(dot);
    std::transform(e.begin(), e.end(), e.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return e;
}

extern "C" {

    int engine_version() { return 300; }

    // Python, paketle gelen ya da sistemdeki ffmpeg/ffprobe yollarını bildirir.
    void set_tool_paths(const char* ffmpeg_path, const char* ffprobe_path) {
        if (ffmpeg_path && *ffmpeg_path) g_ffmpeg = ffmpeg_path;
        if (ffprobe_path && *ffprobe_path) g_ffprobe = ffprobe_path;
    }

    // ------------------------------------------------------------------ ölçüm
    // ffprobe JSON çıktısını out tamponuna yazar. Dönüş: yazılan bayt sayısı, hata: <0
    int media_probe_json(const char* filepath, char* out, int out_size) {
        if (!filepath || *filepath == '\0' || !out || out_size < 16) return -1;
        RunResult r = run_argv({g_ffprobe, "-v", "error", "-print_format", "json",
                                "-show_format", "-show_streams", filepath}, 30000, true, false);
        if (r.code != 0 || r.timed_out || r.out.empty()) return -2;
        if (static_cast<int>(r.out.size()) >= out_size) return -3;
        std::memcpy(out, r.out.data(), r.out.size());
        out[r.out.size()] = '\0';
        return static_cast<int>(r.out.size());
    }

    long long get_media_duration_ms(const char* filepath) {
        if (!filepath || *filepath == '\0') return -1;
        RunResult r = run_argv({g_ffprobe, "-v", "error", "-show_entries", "format=duration",
                                "-of", "default=noprint_wrappers=1:nokey=1", filepath}, 30000, true, false);
        if (r.code != 0 || r.timed_out) return -1;
        char* end = nullptr;
        const double sec = std::strtod(r.out.c_str(), &end);
        if (end == r.out.c_str() || !std::isfinite(sec) || sec <= 0.0) return -1;
        return static_cast<long long>(std::llround(sec * 1000.0));
    }

    // Döndürme bilgisi (telefon videoları) hesaba katılmış, EKRANDA GÖRÜNEN boyut.
    int get_video_dimensions(const char* filepath, int* out_width, int* out_height) {
        if (!filepath || *filepath == '\0' || !out_width || !out_height) return -1;
        *out_width = 0; *out_height = 0;
        RunResult r = run_argv({g_ffprobe, "-v", "error", "-select_streams", "v:0",
                                "-show_entries", "stream=width,height:stream_tags=rotate:stream_side_data=rotation",
                                "-of", "default=noprint_wrappers=1", filepath}, 30000, true, false);
        if (r.code != 0 || r.timed_out) return -1;
        int w = 0, h = 0, rot = 0;
        std::istringstream ss(r.out);
        std::string line;
        while (std::getline(ss, line)) {
            if (line.rfind("width=", 0) == 0) w = std::atoi(line.c_str() + 6);
            else if (line.rfind("height=", 0) == 0) h = std::atoi(line.c_str() + 7);
            else if (line.rfind("rotation=", 0) == 0) rot = static_cast<int>(std::lround(std::atof(line.c_str() + 9)));
            else if (line.rfind("TAG:rotate=", 0) == 0) rot = std::atoi(line.c_str() + 11);
        }
        if (w <= 0 || h <= 0) return -1;
        rot = ((rot % 360) + 360) % 360;
        if (rot == 90 || rot == 270) std::swap(w, h);
        *out_width = w; *out_height = h;
        return 0;
    }

    // ------------------------------------------------------------------ kesme (kare doğrulukta)
    int cut_media_segment(const char* input_filepath, long long cut_point_ms,
                          const char* output_filepath_1, const char* output_filepath_2,
                          const char* media_type_str) {
        if (!input_filepath || !output_filepath_1 || !output_filepath_2 || !media_type_str ||
            *input_filepath == '\0' || *output_filepath_1 == '\0' || *output_filepath_2 == '\0') return -1;
        if (cut_point_ms <= 0) return -2;
        if (std::strcmp(input_filepath, output_filepath_1) == 0 || std::strcmp(input_filepath, output_filepath_2) == 0 ||
            std::strcmp(output_filepath_1, output_filepath_2) == 0) return -3;

        const std::string media_type(media_type_str);
        const bool is_video = (media_type == "video" || media_type == "recorded_video");
        const bool is_audio = (media_type == "audio" || media_type == "recorded_audio");
        if (!is_video && !is_audio) return -4;

        char tbuf[64];
        std::snprintf(tbuf, sizeof(tbuf), "%lld.%03lld", cut_point_ms / 1000, cut_point_ms % 1000);
        const std::string t = tbuf;

        // Codec seçimi çıktı uzantısına göre (kapsayıcı ile uyumlu olsun)
        auto codec_args = [&](const std::string& out_path) {
            const std::string e = lower_ext(out_path);
            std::vector<std::string> a;
            if (is_video) {
                a = {"-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                     "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k"};
                if (e == ".mp4" || e == ".mov" || e == ".rec") { a.push_back("-movflags"); a.push_back("+faststart"); }
                if (e == ".rec") { a.push_back("-f"); a.push_back("mp4"); }
            } else {
                a = {"-map", "0:a:0", "-vn"};
                if (e == ".wav") { a.push_back("-c:a"); a.push_back("pcm_s16le"); }
                else if (e == ".saund") { a.push_back("-c:a"); a.push_back("pcm_s16le"); a.push_back("-f"); a.push_back("wav"); }
                else if (e == ".mp3") { a.push_back("-c:a"); a.push_back("libmp3lame"); a.push_back("-q:a"); a.push_back("2"); }
                else if (e == ".flac") { a.push_back("-c:a"); a.push_back("flac"); }
                else if (e == ".ogg") { a.push_back("-c:a"); a.push_back("libvorbis"); a.push_back("-q:a"); a.push_back("6"); }
                else if (e == ".aac") { a.push_back("-c:a"); a.push_back("aac"); a.push_back("-b:a"); a.push_back("192k"); a.push_back("-f"); a.push_back("adts"); }
                else { a.push_back("-c:a"); a.push_back("aac"); a.push_back("-b:a"); a.push_back("192k"); }
            }
            return a;
        };

        // 1. parça: baştan kesme noktasına
        std::vector<std::string> c1 = {g_ffmpeg, "-v", "error", "-y", "-i", input_filepath, "-t", t};
        for (auto& x : codec_args(output_filepath_1)) c1.push_back(x);
        c1.push_back(output_filepath_1);
        RunResult r1 = run_argv(c1, 0, false, true);
        if (r1.code != 0) {
            std::cerr << "C++: kesme (1) başarısız:\n" << r1.out << std::endl;
            remove(output_filepath_1);
            return -101;
        }
        // 2. parça: kesme noktasından sona (yeniden kodlandığı için seek kare doğrulukta)
        std::vector<std::string> c2 = {g_ffmpeg, "-v", "error", "-y", "-ss", t, "-i", input_filepath};
        for (auto& x : codec_args(output_filepath_2)) c2.push_back(x);
        c2.push_back(output_filepath_2);
        RunResult r2 = run_argv(c2, 0, false, true);
        if (r2.code != 0) {
            std::cerr << "C++: kesme (2) başarısız:\n" << r2.out << std::endl;
            remove(output_filepath_1);
            remove(output_filepath_2);
            return -102;
        }
        if (!std::ifstream(output_filepath_1).good() || !std::ifstream(output_filepath_2).good()) {
            remove(output_filepath_1);
            remove(output_filepath_2);
            return -103;
        }
        return 0;
    }

    int delete_media_file(const char* filepath) {
        if (!filepath || *filepath == '\0') return -1;
        if (remove(filepath) != 0) return -2;
        return 0;
    }

    // ------------------------------------------------------------------ arşiv
    int archive_segments_with_compression(const char* output_tar_path, const char* temp_dir,
                                          const char* manifest_path, const char* compression) {
        if (!output_tar_path || !temp_dir || *output_tar_path == '\0' || *temp_dir == '\0') return -1;
        const std::string comp = compression ? compression : "gz";
        if (comp != "gz" && comp != "xz") return -2;
        (void)manifest_path;
        const std::string flag = (comp == "xz") ? "-cJf" : "-czf";
        std::stringstream cmd;
        cmd << "cd " << shell_quote(temp_dir) << " && tar " << flag << " " << shell_quote(output_tar_path)
            << " --exclude='.*' -- *";
        return execute_external_command(cmd.str()) == 0 ? 0 : -3;
    }

    int archive_segments(const char* output_tar_gz_path, const char* temp_dir, const char* manifest_path) {
        return archive_segments_with_compression(output_tar_gz_path, temp_dir, manifest_path, "gz");
    }

    static std::string detect_compression(const std::string& path) {
        std::ifstream f(path, std::ios::binary);
        if (!f.is_open()) return "";
        unsigned char m[6] = {0};
        f.read(reinterpret_cast<char*>(m), sizeof(m));
        const std::streamsize n = f.gcount();
        if (n >= 2 && m[0] == 0x1f && m[1] == 0x8b) return "gz";
        if (n >= 6 && m[0] == 0xFD && m[1] == 0x37 && m[2] == 0x7A && m[3] == 0x58 && m[4] == 0x5A && m[5] == 0x00) return "xz";
        return "";
    }

    int extract_segments(const char* input_tar_gz_path, const char* output_dir) {
        if (!input_tar_gz_path || !output_dir || *input_tar_gz_path == '\0' || *output_dir == '\0') return -1;
        const std::string in = input_tar_gz_path;
        const std::string comp = detect_compression(in);
        const std::string flag = (comp == "gz") ? "-xzf" : "-xJf";
        std::stringstream cmd;
        cmd << "tar " << flag << " " << shell_quote(in) << " -C " << shell_quote(output_dir);
        int r = execute_external_command(cmd.str());
        if (r != 0 && comp.empty()) {
            std::stringstream c2;
            c2 << "tar -xzf " << shell_quote(in) << " -C " << shell_quote(output_dir);
            r = execute_external_command(c2.str());
        }
        return r == 0 ? 0 : -2;
    }

    // ------------------------------------------------------------------ yedek ses kaydı (PortAudio)
    // media_recorder yoksa kullanılır. Callback yalnızca halka tampona kopyalar;
    // dosyaya yazma ayrı iş parçacığında yapılır (xrun / kesinti olmaz). Tek WAV dosyası (16-bit, 48 kHz, mono).
    static const size_t RING_SAMPLES = 48000 * 20;          // 20 sn tampon
    static std::vector<float> g_ring(RING_SAMPLES);
    static std::atomic<size_t> g_ring_w(0), g_ring_r(0);
    static std::atomic<bool> g_audio_recording(false);
    static std::atomic<bool> g_writer_run(false);
    static std::atomic<bool> g_overrun(false);
    static std::thread g_writer;
    static PaStream* audio_stream = nullptr;
    static SNDFILE* audio_sndfile = nullptr;

    static int audioRecordCallback(const void* input, void*, unsigned long frameCount,
                                   const PaStreamCallbackTimeInfo*, PaStreamCallbackFlags, void*) {
        if (!g_audio_recording.load(std::memory_order_relaxed)) return paComplete;
        const float* in = static_cast<const float*>(input);
        size_t w = g_ring_w.load(std::memory_order_relaxed);
        const size_t r = g_ring_r.load(std::memory_order_acquire);
        for (unsigned long i = 0; i < frameCount; ++i) {
            const size_t next = (w + 1) % RING_SAMPLES;
            if (next == r) { g_overrun = true; break; }       // dolu: bu örnekleri at (callback asla bloklanmaz)
            g_ring[w] = in ? in[i] : 0.0f;
            w = next;
        }
        g_ring_w.store(w, std::memory_order_release);
        return paContinue;
    }

    static void writer_loop() {
        std::vector<short> out;
        while (true) {
            const size_t w = g_ring_w.load(std::memory_order_acquire);
            size_t r = g_ring_r.load(std::memory_order_relaxed);
            if (w == r) {
                if (!g_writer_run.load()) break;
                std::this_thread::sleep_for(std::chrono::milliseconds(5));
                continue;
            }
            out.clear();
            while (r != w && out.size() < 8192) {
                float v = g_ring[r];
                if (v > 1.0f) v = 1.0f; else if (v < -1.0f) v = -1.0f;
                out.push_back(static_cast<short>(v * 32767.0f));
                r = (r + 1) % RING_SAMPLES;
            }
            if (audio_sndfile && !out.empty()) sf_writef_short(audio_sndfile, out.data(), static_cast<sf_count_t>(out.size()));
            g_ring_r.store(r, std::memory_order_release);
        }
    }

    int init_audio_engine() {
        const PaError err = Pa_Initialize();
        if (err != paNoError) std::cerr << "C++: PortAudio başlatılamadı: " << Pa_GetErrorText(err) << std::endl;
        return err;
    }

    int terminate_audio_engine() { return Pa_Terminate(); }

    // base_filepath_pattern uyumluluk için alınır ama kullanılmaz; kayıt doğrudan final_filepath'e yazılır.
    int start_audio_record(const char* base_filepath_pattern, const char* final_filepath) {
        (void)base_filepath_pattern;
        if (g_audio_recording) return -1;
        if (!final_filepath || *final_filepath == '\0') return -2;

        SF_INFO info;
        std::memset(&info, 0, sizeof(info));
        info.channels = 1;
        info.samplerate = 48000;
        info.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;
        audio_sndfile = sf_open(final_filepath, SFM_WRITE, &info);
        if (!audio_sndfile) return -4;

        g_ring_w = 0; g_ring_r = 0; g_overrun = false;
        g_writer_run = true;
        g_audio_recording = true;
        g_writer = std::thread(writer_loop);

        PaError err = Pa_OpenDefaultStream(&audio_stream, 1, 0, paFloat32, 48000,
                                           paFramesPerBufferUnspecified, audioRecordCallback, nullptr);
        if (err == paNoError) err = Pa_StartStream(audio_stream);
        if (err != paNoError) {
            std::cerr << "C++: PortAudio hata: " << Pa_GetErrorText(err) << std::endl;
            if (audio_stream) { Pa_CloseStream(audio_stream); audio_stream = nullptr; }
            g_audio_recording = false;
            g_writer_run = false;
            if (g_writer.joinable()) g_writer.join();
            sf_close(audio_sndfile); audio_sndfile = nullptr;
            remove(final_filepath);
            return static_cast<int>(err);
        }
        return 0;
    }

    int stop_audio_record() {
        if (!g_audio_recording && !audio_stream) return -1;
        g_audio_recording = false;
        if (audio_stream) {
            Pa_StopStream(audio_stream);
            Pa_CloseStream(audio_stream);
            audio_stream = nullptr;
        }
        g_writer_run = false;                       // yazıcı tamponu boşaltıp çıkar
        if (g_writer.joinable()) g_writer.join();
        if (audio_sndfile) { sf_close(audio_sndfile); audio_sndfile = nullptr; }
        return 0;
    }

    // Eski arayüz uyumluluğu: tek dosya zaten yazıldı.
    int merge_audio_files(const char* output_filepath) {
        if (!output_filepath || *output_filepath == '\0') return -1;
        return std::ifstream(output_filepath).good() ? 0 : -2;
    }

    // ------------------------------------------------------------------ zaman çizelgesi
    double calculate_segment_position(double start_time_ms, double timeline_width, double total_timeline_duration_ms) {
        if (!std::isfinite(start_time_ms) || !std::isfinite(timeline_width) || !std::isfinite(total_timeline_duration_ms)) return 0.0;
        if (total_timeline_duration_ms <= 0.0 || timeline_width <= 0.0) return 0.0;
        if (start_time_ms < 0.0) start_time_ms = 0.0;
        double ratio = start_time_ms / total_timeline_duration_ms;
        if (ratio < 0.0) ratio = 0.0;
        if (ratio > 1.0) ratio = 1.0;
        return ratio * timeline_width;
    }

    double update_timeline_smoothly(double current_value, double target_value, double step_size) {
        if (!std::isfinite(current_value) && !std::isfinite(target_value)) return 0.0;
        if (!std::isfinite(target_value)) return std::isfinite(current_value) ? current_value : 0.0;
        if (!std::isfinite(current_value)) return target_value;
        if (current_value == target_value) return current_value;
        if (!std::isfinite(step_size) || step_size <= 0.0) return target_value;
        if (std::fabs(target_value - current_value) < step_size) return target_value;
        return current_value < target_value ? current_value + step_size : current_value - step_size;
    }

} // extern "C"

#else  // MEDIA_RECORDER_MAIN
// =============================================================================
//                    KAYIT PROGRAMI (media_recorder, GStreamer)
//
// KOMUTLAR:
//   --record <anahtar=değer ...>   kamera+mikrofon (mode=camera) ya da yalnızca mikrofon (mode=audio)
//   --list-cameras                 kullanılabilir kameraları "yol|ad" olarak yazar
//   --capabilities                 sürüm ve GStreamer eklenti durumu
//
// --record anahtarları:
//   mode=camera|audio   out=<çıkış dosyası>   camera=auto|/dev/videoN   audio=default|none|<pulse kaynağı>
//   w= h=               (kamera) çıkış boyutu; 0 = kameranın kendi boyutu
//   aspect=crop|fit     (kamera) oran farkı: ortadan kırp ya da siyah bantla sığdır
//   fps=30  cw= ch=     (kamera) kayıt hızı ve istenen kamera çözünürlüğü
//   rate=48000          ses örnekleme hızı
//   pv=<yol> pv_w=480 pv_fps=15   önizleme için /dev/shm paylaşımlı bellek dosyası
//
// stdin: "STOP" (ya da SIGINT/SIGTERM) -> EOS gönderilir, dosya sonlandırılır, süreç 0 ile çıkar.
// stdout olayları:  EVENT started <dosya> | EVENT info <metin> | EVENT error <kod> <etiket> | EVENT finalized <dosya>
// ÇIKIŞ KODLARI: 0 normal, 1 genel hata, 2 kamera hatası, 4 ses hatası, 5 eksik GStreamer eklentisi
// =============================================================================
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <sstream>
#include <fstream>
#include <algorithm>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <cerrno>
#include <csignal>
#include <ctime>
#include <dirent.h>
#include <fcntl.h>
#include <poll.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <linux/videodev2.h>

#include <glib.h>
#include <gst/gst.h>
#include <gst/app/gstappsink.h>
#include <gst/video/video.h>

static volatile std::sig_atomic_t g_stop_requested = 0;
static bool g_fake_sources = false;                      // KAVRAM_FAKE_SOURCES=1 (yalnızca test)

static void on_stop_signal(int) { g_stop_requested = 1; }
static void log_info(const std::string &s) { std::cout << "C++: " << s << std::endl; }
static void log_err(const std::string &s) { std::cerr << "C++ Hata: " << s << std::endl; }
static void emit_event(const std::string &s) { std::cout << "EVENT " << s << std::endl; }

static uint64_t mono_ms() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return static_cast<uint64_t>(ts.tv_sec) * 1000ull + static_cast<uint64_t>(ts.tv_nsec / 1000000);
}

typedef std::map<std::string, std::string> KV;

static KV parse_kv(int argc, char **argv, int from) {
    KV kv;
    for (int i = from; i < argc; ++i) {
        std::string a = argv[i];
        const size_t eq = a.find('=');
        if (eq == std::string::npos || eq == 0) continue;
        kv[a.substr(0, eq)] = a.substr(eq + 1);
    }
    return kv;
}
static std::string kv_str(const KV &kv, const char *k, const std::string &def = "") {
    auto it = kv.find(k);
    return it == kv.end() ? def : it->second;
}
static int kv_int(const KV &kv, const char *k, int def) {
    auto it = kv.find(k);
    if (it == kv.end() || it->second.empty()) return def;
    char *end = nullptr;
    const long v = std::strtol(it->second.c_str(), &end, 10);
    return (end && *end == '\0') ? static_cast<int>(v) : def;
}

static bool have_factory(const char *name) {
    GstElementFactory *f = gst_element_factory_find(name);
    if (!f) return false;
    gst_object_unref(f);
    return true;
}

// ---------------------------------------------------------------- kamera listesi
struct CameraInfo { std::string path, name; };

static std::vector<CameraInfo> enumerate_cameras() {
    std::vector<std::pair<int, std::string>> nodes;
    DIR *d = opendir("/dev");
    if (d) {
        struct dirent *ent;
        while ((ent = readdir(d)) != nullptr) {
            if (std::strncmp(ent->d_name, "video", 5) != 0) continue;
            const char *num = ent->d_name + 5;
            if (!*num) continue;
            bool digits = true;
            for (const char *c = num; *c; ++c) if (*c < '0' || *c > '9') digits = false;
            if (!digits) continue;
            nodes.emplace_back(std::atoi(num), std::string("/dev/") + ent->d_name);
        }
        closedir(d);
    }
    std::sort(nodes.begin(), nodes.end());

    std::vector<CameraInfo> cams;
    for (auto &n : nodes) {
        int fd = open(n.second.c_str(), O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd < 0) continue;
        struct v4l2_capability cap;
        std::memset(&cap, 0, sizeof(cap));
        const bool ok = ioctl(fd, VIDIOC_QUERYCAP, &cap) == 0;
        close(fd);
        if (!ok) continue;
        const __u32 caps = (cap.capabilities & V4L2_CAP_DEVICE_CAPS) ? cap.device_caps : cap.capabilities;
        bool capture = (caps & V4L2_CAP_VIDEO_CAPTURE) || (caps & V4L2_CAP_VIDEO_CAPTURE_MPLANE);
#ifdef V4L2_CAP_META_CAPTURE
        if (caps & V4L2_CAP_META_CAPTURE) capture = false;
#endif
        if (!capture || !(caps & V4L2_CAP_STREAMING)) continue;
        CameraInfo ci;
        ci.path = n.second;
        ci.name = reinterpret_cast<const char *>(cap.card);
        cams.push_back(ci);
    }
    return cams;
}

static int cmd_list_cameras() {
    for (auto &c : enumerate_cameras()) std::cout << c.path << "|" << c.name << std::endl;
    return 0;
}

static int cmd_capabilities() {
    gst_init(nullptr, nullptr);
    std::cout << "engine=1" << std::endl;
    const char *names[] = {"v4l2src", "pulsesrc", "decodebin", "videoconvert", "videoscale", "videorate",
                           "aspectratiocrop", "x264enc", "openh264enc", "vp8enc", "matroskamux", "h264parse",
                           "fdkaacenc", "voaacenc", "avenc_aac", "opusenc", "wavenc", "appsink", "queue"};
    for (const char *n : names) std::cout << n << "=" << (have_factory(n) ? 1 : 0) << std::endl;
    return 0;
}

// ---------------------------------------------------------------- önizleme paylaşımlı belleği
struct PvHeader {
    uint32_t magic, version, width, height, stride, format;
    uint64_t seq, stamp_ms;
    uint32_t payload, capacity, pad[4];
};
static_assert(sizeof(PvHeader) == 64, "PvHeader 64 bayt olmalı");

struct PvShm {
    std::string path;
    int fd = -1;
    uint8_t *map = nullptr;
    size_t size = 0, capacity = 0;
    uint64_t seq = 0;

    bool create(const std::string &p, size_t cap) {
        if (p.empty()) return false;
        capacity = cap;
        size = sizeof(PvHeader) + cap;
        unlink(p.c_str());
        fd = open(p.c_str(), O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
        if (fd < 0) { log_err("Önizleme belleği oluşturulamadı: " + p); return false; }
        if (ftruncate(fd, static_cast<off_t>(size)) != 0) { close(fd); fd = -1; unlink(p.c_str()); return false; }
        void *m = mmap(nullptr, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
        if (m == MAP_FAILED) { close(fd); fd = -1; unlink(p.c_str()); return false; }
        map = static_cast<uint8_t *>(m);
        path = p;
        auto *h = reinterpret_cast<PvHeader *>(map);
        std::memset(h, 0, sizeof(PvHeader));
        h->version = 1; h->format = 1; h->capacity = static_cast<uint32_t>(cap);
        __atomic_store_n(&h->magic, 0x5650564Bu, __ATOMIC_RELEASE);
        return true;
    }
    bool active() const { return map != nullptr; }

    void write_frame(int w, int hgt, const uint8_t *src, int src_stride) {
        if (!map || w <= 0 || hgt <= 0) return;
        const size_t row = static_cast<size_t>(w) * 4;
        const size_t payload = row * static_cast<size_t>(hgt);
        if (payload > capacity) return;
        auto *h = reinterpret_cast<PvHeader *>(map);
        __atomic_store_n(&h->seq, ++seq, __ATOMIC_RELEASE);          // tek sayı: yazılıyor
        uint8_t *dst = map + sizeof(PvHeader);
        if (static_cast<size_t>(src_stride) == row) std::memcpy(dst, src, payload);
        else for (int y = 0; y < hgt; ++y) std::memcpy(dst + y * row, src + static_cast<size_t>(y) * src_stride, row);
        h->width = static_cast<uint32_t>(w);
        h->height = static_cast<uint32_t>(hgt);
        h->stride = static_cast<uint32_t>(row);
        h->payload = static_cast<uint32_t>(payload);
        h->stamp_ms = mono_ms();
        __atomic_store_n(&h->seq, ++seq, __ATOMIC_RELEASE);          // çift sayı: tamam
    }
    void destroy() {
        if (map) munmap(map, size);
        map = nullptr;
        if (fd >= 0) close(fd);
        fd = -1;
        if (!path.empty()) unlink(path.c_str());
        path.clear();
    }
};

static GstFlowReturn on_preview_sample(GstAppSink *sink, gpointer user_data) {
    auto *shm = static_cast<PvShm *>(user_data);
    GstSample *sample = gst_app_sink_pull_sample(sink);
    if (!sample) return GST_FLOW_OK;
    GstCaps *caps = gst_sample_get_caps(sample);
    GstBuffer *buffer = gst_sample_get_buffer(sample);
    GstVideoInfo info;
    if (shm && shm->active() && caps && buffer && gst_video_info_from_caps(&info, caps)) {
        GstVideoFrame frame;
        if (gst_video_frame_map(&frame, &info, buffer, GST_MAP_READ)) {
            shm->write_frame(GST_VIDEO_FRAME_WIDTH(&frame), GST_VIDEO_FRAME_HEIGHT(&frame),
                             static_cast<const uint8_t *>(GST_VIDEO_FRAME_PLANE_DATA(&frame, 0)),
                             GST_VIDEO_FRAME_PLANE_STRIDE(&frame, 0));
            gst_video_frame_unmap(&frame);
        }
    }
    gst_sample_unref(sample);
    return GST_FLOW_OK;
}

// ---------------------------------------------------------------- yapılandırma
struct Config {
    std::string mode = "camera", out, camera = "auto", audio = "default", aspect = "crop", pv;
    int w = 0, h = 0, fps = 30, cw = 1280, ch = 720, rate = 48000, pv_w = 480, pv_fps = 15;
};

struct VEnc { std::string launch, parse; };
struct AEnc { std::string launch, parse; };

static VEnc pick_video_encoder(int fps, int w, int h) {
    VEnc e;
    const int threads = (static_cast<long>(w) * h > 1280L * 720L) ? 3 : 2;
    const int gop = std::max(1, fps * 2);
    if (have_factory("x264enc")) {
        e.launch = "x264enc speed-preset=veryfast tune=zerolatency pass=quant quantizer=21 bframes=0 key-int-max=" +
                   std::to_string(gop) + " threads=" + std::to_string(threads);
        e.parse = "h264parse";
    } else if (have_factory("openh264enc")) {
        e.launch = "openh264enc bitrate=4000000 gop-size=" + std::to_string(gop);
        e.parse = "h264parse";
    } else if (have_factory("vp8enc")) {
        e.launch = "vp8enc deadline=1 cpu-used=6 end-usage=cq cq-level=20 threads=" + std::to_string(threads) +
                   " keyframe-max-dist=" + std::to_string(gop);
    }
    return e;
}

static AEnc pick_audio_encoder() {
    AEnc e;
    if (have_factory("fdkaacenc"))       { e.launch = "fdkaacenc bitrate=160000"; e.parse = "aacparse"; }
    else if (have_factory("voaacenc"))   { e.launch = "voaacenc bitrate=160000";  e.parse = "aacparse"; }
    else if (have_factory("avenc_aac"))  { e.launch = "avenc_aac bitrate=160000"; e.parse = "aacparse"; }
    else if (have_factory("opusenc"))    { e.launch = "opusenc bitrate=128000"; }
    else                                 { e.launch = "audioconvert ! audio/x-raw,format=S16LE"; }
    return e;
}

static std::string preview_branch(int pw, int pfps) {
    std::ostringstream s;
    s << "queue name=pvq max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream"
      << " ! videorate drop-only=true ! video/x-raw,framerate=" << std::max(1, pfps) << "/1"
      << " ! videoscale ! video/x-raw,width=" << std::max(16, pw) << ",pixel-aspect-ratio=1/1"
      << " ! videoconvert ! video/x-raw,format=BGRx"
      << " ! appsink name=pv_cam max-buffers=1 drop=true sync=false async=false";
    return s.str();
}

struct Recorder {
    Config cfg;
    GstElement *pipeline = nullptr;
    PvShm pv;
    VEnc venc;
    AEnc aenc;
    std::string camera_path;
    bool failed = false;
    std::string err_tag, err_msg;
    gint64 attempt_start = 0;

    bool is_cam() const { return cfg.mode == "camera"; }
    bool has_aud() const { return cfg.audio != "none"; }

    bool check_plugins() {
        std::vector<std::string> missing;
        auto need = [&](const char *f, const char *pkg) {
            if (!have_factory(f)) missing.push_back(std::string(f) + " (sudo apt install " + pkg + ")");
        };
        need("queue", "gstreamer1.0-plugins-base");
        if (is_cam()) {
            need("videoconvert", "gstreamer1.0-plugins-base");
            need("videoscale", "gstreamer1.0-plugins-base");
            need("videorate", "gstreamer1.0-plugins-base");
            need("decodebin", "gstreamer1.0-plugins-base");
            need("appsink", "gstreamer1.0-plugins-base");
            need("matroskamux", "gstreamer1.0-plugins-good");
            if (!g_fake_sources) need("v4l2src", "gstreamer1.0-plugins-good");
            if (venc.launch.empty()) missing.push_back("x264enc (sudo apt install gstreamer1.0-plugins-ugly)");
            else if (!venc.parse.empty()) need("h264parse", "gstreamer1.0-plugins-bad");
            if (has_aud() && !aenc.parse.empty()) need("aacparse", "gstreamer1.0-plugins-bad");
        } else {
            need("wavenc", "gstreamer1.0-plugins-good");
        }
        if (has_aud()) {
            need("audioconvert", "gstreamer1.0-plugins-base");
            need("audioresample", "gstreamer1.0-plugins-base");
            if (!g_fake_sources) need("pulsesrc", "gstreamer1.0-plugins-good");
        }
        if (missing.empty()) return true;
        std::string msg = "Eksik GStreamer eklentisi: ";
        for (size_t i = 0; i < missing.size(); ++i) msg += (i ? ", " : "") + missing[i];
        log_err(msg);
        return false;
    }

    std::string camera_head(int try_no) const {
        std::ostringstream s;
        if (g_fake_sources) s << "videotestsrc name=cam_src is-live=true pattern=ball ! video/x-raw,width="
                              << cfg.cw << ",height=" << cfg.ch << ",framerate=" << cfg.fps << "/1";
        else {
            s << "v4l2src name=cam_src";
            std::string size;
            if (cfg.cw > 0 && cfg.ch > 0) size = ",width=" + std::to_string(cfg.cw) + ",height=" + std::to_string(cfg.ch);
            std::string caps;
            if (try_no == 0) {
                const std::string fr = ",framerate=[ " + std::to_string(cfg.fps) + "/1, " + std::to_string(cfg.fps * 2) + "/1 ]";
                caps = "video/x-raw" + size + fr + "; image/jpeg" + size + fr;
            } else if (try_no == 1) {
                caps = "video/x-raw" + size + "; image/jpeg" + size;
            } else {
                caps = "video/x-raw; image/jpeg";
            }
            s << " ! capsfilter caps=\"" << caps << "\" ! decodebin name=cam_dec";
        }
        s << " ! videoconvert ! videorate ! video/x-raw,framerate=" << cfg.fps << "/1";
        return s.str();
    }

    std::string audio_head(bool wav) const {
        std::ostringstream s;
        if (g_fake_sources) s << "audiotestsrc name=aud_src is-live=true wave=sine freq=440 volume=0.2";
        else s << "pulsesrc name=aud_src";
        s << " ! audioconvert ! audioresample ! audio/x-raw,rate=" << cfg.rate << ",channels=2";
        if (wav) s << ",format=S16LE,layout=interleaved";
        return s.str();
    }

    std::string build_pipeline(int try_no) const {
        std::ostringstream p;
        if (is_cam()) {
            p << camera_head(try_no);
            if (cfg.w > 0 && cfg.h > 0) {
                const bool crop = (cfg.aspect == "crop") && have_factory("aspectratiocrop");
                if (crop) p << " ! aspectratiocrop aspect-ratio=" << cfg.w << "/" << cfg.h;
                p << " ! videoscale" << (crop ? "" : " add-borders=true")
                  << " ! video/x-raw,width=" << cfg.w << ",height=" << cfg.h << ",pixel-aspect-ratio=1/1";
            }
            p << " ! tee name=ct ";
            // Kodlayıcı yetişemezse bellek şişmesin: 2 sn / 64 MB dolunca eski kareleri at
            p << "ct. ! queue name=vrq max-size-buffers=0 max-size-bytes=67108864 max-size-time=2000000000 leaky=downstream"
              << " ! videoconvert ! video/x-raw,format=I420 ! " << venc.launch;
            if (!venc.parse.empty()) p << " ! " << venc.parse;
            p << " ! mux.video_0 ";
            if (!cfg.pv.empty()) p << "ct. ! " << preview_branch(cfg.pv_w, cfg.pv_fps) << " ";
            if (has_aud()) {
                p << audio_head(false)
                  << " ! queue name=aud_q max-size-buffers=0 max-size-bytes=0 max-size-time=3000000000"
                  << " ! " << aenc.launch;
                if (!aenc.parse.empty()) p << " ! " << aenc.parse;
                p << " ! mux.audio_0 ";
            }
            p << "matroskamux name=mux ! filesink name=out_file async=false ";
        } else {
            p << audio_head(true)
              << " ! queue name=aud_q max-size-buffers=0 max-size-bytes=0 max-size-time=3000000000"
              << " ! wavenc ! filesink name=out_file async=false ";
        }
        return p.str();
    }

    GstElement *get(const char *name) { return pipeline ? gst_bin_get_by_name(GST_BIN(pipeline), name) : nullptr; }

    static std::string chain_tag(GstObject *obj) {
        GstObject *cur = obj ? static_cast<GstObject *>(gst_object_ref(obj)) : nullptr;
        std::string tag;
        while (cur) {
            const gchar *n = GST_OBJECT_NAME(cur);
            if (n) {
                const std::string name = n;
                if (name.rfind("cam_", 0) == 0 || name.rfind("pv_", 0) == 0 || name.rfind("vrq", 0) == 0) tag = "cam";
                else if (name.rfind("aud_", 0) == 0) tag = "aud";
                if (!tag.empty()) { gst_object_unref(cur); break; }
            }
            GstObject *parent = gst_object_get_parent(cur);
            gst_object_unref(cur);
            cur = parent;
        }
        return tag;
    }

    bool start_pipeline(int try_no) {
        const std::string desc = build_pipeline(try_no);
        log_info("pipeline: " + desc);
        GError *error = nullptr;
        pipeline = gst_parse_launch(desc.c_str(), &error);
        if (error) {
            log_err(std::string("pipeline kurulamadı: ") + error->message);
            g_error_free(error);
            if (pipeline) { gst_object_unref(pipeline); pipeline = nullptr; }
            return false;
        }
        if (!pipeline) return false;

        if (GstElement *f = get("out_file")) {
            g_object_set(f, "location", cfg.out.c_str(), nullptr);
            gst_object_unref(f);
        }
        if (GstElement *src = get("aud_src")) {
            if (!g_fake_sources && cfg.audio != "default" && cfg.audio != "none")
                g_object_set(src, "device", cfg.audio.c_str(), nullptr);
            gst_object_unref(src);
        }
        if (GstElement *src = get("cam_src")) {
            if (!g_fake_sources) g_object_set(src, "device", camera_path.c_str(), nullptr);
            gst_object_unref(src);
        }
        if (GstElement *sink = get("pv_cam")) {
            GstAppSinkCallbacks cb;
            std::memset(&cb, 0, sizeof(cb));
            cb.new_sample = on_preview_sample;
            gst_app_sink_set_callbacks(GST_APP_SINK(sink), &cb, &pv, nullptr);
            gst_object_unref(sink);
        }

        failed = false; err_tag.clear(); err_msg.clear();
        attempt_start = g_get_monotonic_time();
        if (gst_element_set_state(pipeline, GST_STATE_PLAYING) == GST_STATE_CHANGE_FAILURE) {
            GstBus *b = gst_element_get_bus(pipeline);
            GstMessage *m = gst_bus_pop_filtered(b, GST_MESSAGE_ERROR);
            if (m) {
                GError *er = nullptr; gchar *dbg = nullptr;
                gst_message_parse_error(m, &er, &dbg);
                err_msg = er && er->message ? er->message : "";
                err_tag = chain_tag(GST_MESSAGE_SRC(m));
                std::cerr << "C++ GStreamer Hata: " << err_msg << std::endl;
                if (er) g_error_free(er);
                g_free(dbg);
                gst_message_unref(m);
            }
            gst_object_unref(b);
            return false;
        }
        GstState cur = GST_STATE_NULL, pend = GST_STATE_NULL;
        if (gst_element_get_state(pipeline, &cur, &pend, 10 * GST_SECOND) == GST_STATE_CHANGE_FAILURE) return false;
        return true;
    }

    void teardown_pipeline() {
        if (pipeline) {
            gst_element_set_state(pipeline, GST_STATE_NULL);
            gst_object_unref(pipeline);
            pipeline = nullptr;
        }
    }

    // stdin'den "STOP" satırı gelirse true
    static bool poll_stdin_stop(std::string &buf) {
        struct pollfd p; p.fd = 0; p.events = POLLIN; p.revents = 0;
        if (poll(&p, 1, 0) <= 0) return false;
        if (p.revents & (POLLHUP | POLLERR)) return true;       // ana program kapandı: dur
        char tmp[128];
        const ssize_t n = read(0, tmp, sizeof(tmp));
        if (n == 0) return true;
        if (n > 0) buf.append(tmp, static_cast<size_t>(n));
        if (buf.find("STOP") != std::string::npos) return true;
        if (buf.size() > 1024) buf.clear();
        return false;
    }

    int run() {
        const pid_t parent_pid = getppid();
        prctl(PR_SET_PDEATHSIG, SIGTERM);                       // ana program ölürse kamera/mikrofon serbest kalsın

        if (cfg.out.empty()) { log_err("out= verilmedi."); return 1; }
        cfg.w &= ~1; cfg.h &= ~1;
        cfg.fps = std::max(5, std::min(60, cfg.fps));
        cfg.rate = std::max(8000, cfg.rate);

        gst_init(nullptr, nullptr);
        g_fake_sources = g_getenv("KAVRAM_FAKE_SOURCES") != nullptr;
        venc = pick_video_encoder(cfg.fps, cfg.w > 0 ? cfg.w : cfg.cw, cfg.h > 0 ? cfg.h : cfg.ch);
        aenc = pick_audio_encoder();
        if (!check_plugins()) { emit_event("error 5 eksik-eklenti"); return 5; }

        std::signal(SIGINT, on_stop_signal);
        std::signal(SIGTERM, on_stop_signal);
        std::signal(SIGHUP, on_stop_signal);
        std::signal(SIGPIPE, SIG_IGN);

        if (is_cam()) {
            camera_path = cfg.camera;
            if (!g_fake_sources) {
                if (camera_path == "auto" || camera_path.empty()) {
                    auto cams = enumerate_cameras();
                    if (cams.empty()) {
                        log_err("Kamera bulunamadı (/dev/video* yok veya erişim izni yok).");
                        emit_event("error 2 kamera-yok");
                        return 2;
                    }
                    camera_path = cams.front().path;
                }
                if (access(camera_path.c_str(), R_OK | W_OK) != 0) {
                    log_err("Kameraya erişilemiyor: " + camera_path + " (" + std::strerror(errno) +
                            "). Kullanıcının 'video' grubunda olduğundan emin olun.");
                    emit_event("error 2 kamera-erisim");
                    return 2;
                }
            }
            if (!cfg.pv.empty()) {
                const size_t cap = static_cast<size_t>(cfg.pv_w) * cfg.pv_w * 2 * 4;   // en-boy oranından bağımsız yeterli
                if (!pv.create(cfg.pv, cap)) cfg.pv.clear();
            }
        }

        const int max_try = is_cam() ? 2 : 0;
        int result = 0;
        bool stop_done = false;
        std::string in_buf;

        for (int attempt = 0; attempt <= max_try; ++attempt) {
            if (g_stop_requested) break;
            if (!start_pipeline(attempt)) {
                const bool cam_problem = is_cam() && (err_tag.empty() || err_tag == "cam");
                teardown_pipeline();
                if (cam_problem && attempt < max_try) { log_info("Kamera modu uygun değil, farklı mod deneniyor..."); continue; }
                result = (err_tag == "aud") ? 4 : (is_cam() ? 2 : 1);
                emit_event("error " + std::to_string(result) + " " + (err_tag.empty() ? "genel" : err_tag));
                break;
            }
            emit_event("started " + cfg.out);

            GstBus *bus = gst_element_get_bus(pipeline);
            bool eos_sent = false;
            gint64 eos_deadline = 0;
            for (;;) {
                GstMessage *m = gst_bus_timed_pop_filtered(
                    bus, 50 * GST_MSECOND, static_cast<GstMessageType>(GST_MESSAGE_ERROR | GST_MESSAGE_EOS));
                if (m) {
                    if (GST_MESSAGE_TYPE(m) == GST_MESSAGE_EOS) {
                        (void)0;
                    } else {
                        GError *er = nullptr; gchar *dbg = nullptr;
                        gst_message_parse_error(m, &er, &dbg);
                        err_msg = er && er->message ? er->message : "";
                        err_tag = chain_tag(GST_MESSAGE_SRC(m));
                        std::cerr << "C++ GStreamer Hata: " << err_msg << std::endl;
                        if (dbg) std::cerr << "C++ ayrıntı: " << dbg << std::endl;
                        if (er) g_error_free(er);
                        g_free(dbg);
                        failed = true;
                    }
                    gst_message_unref(m);
                    break;
                }
                if (!g_stop_requested && poll_stdin_stop(in_buf)) g_stop_requested = 1;
                if (getppid() != parent_pid) g_stop_requested = 1;       // ana program öldü
                if (g_stop_requested && !eos_sent) {
                    emit_event("stopping");
                    gst_element_send_event(pipeline, gst_event_new_eos());
                    eos_sent = true;
                    eos_deadline = g_get_monotonic_time() + 15 * G_USEC_PER_SEC;
                }
                if (eos_sent && g_get_monotonic_time() > eos_deadline) {
                    log_err("EOS zaman aşımı; dosya olduğu gibi kapatılıyor.");
                    break;
                }
            }

            const gint64 age = g_get_monotonic_time() - attempt_start;
            if (failed) {
                const bool early_cam = (err_tag == "cam") && age < 8 * G_USEC_PER_SEC && attempt < max_try && !g_stop_requested;
                if (early_cam) {
                    log_info("Kamera başlangıç hatası, farklı mod deneniyor...");
                    gst_object_unref(bus);
                    teardown_pipeline();
                    continue;
                }
                // Dosya kurtarma: EOS dene (en çok 3 sn)
                if (age >= 8 * G_USEC_PER_SEC && !eos_sent) {
                    gst_element_send_event(pipeline, gst_event_new_eos());
                    GstMessage *m = gst_bus_timed_pop_filtered(bus, 3 * GST_SECOND,
                        static_cast<GstMessageType>(GST_MESSAGE_EOS | GST_MESSAGE_ERROR));
                    if (m) gst_message_unref(m);
                }
                result = (err_tag == "aud") ? 4 : (err_tag == "cam" ? 2 : 1);
                emit_event("error " + std::to_string(result) + " " + (err_tag.empty() ? "genel" : err_tag));
            }
            gst_object_unref(bus);
            stop_done = true;
            break;
        }

        teardown_pipeline();
        pv.destroy();
        if (result == 0 && stop_done) emit_event("finalized " + cfg.out);
        return result;
    }
};

int main(int argc, char *argv[]) {
    std::ios_base::sync_with_stdio(true);
    if (argc < 2) {
        std::cerr << "Kullanım: media_recorder --record anahtar=değer ... | --list-cameras | --capabilities" << std::endl;
        return 1;
    }
    const std::string cmd = argv[1];
    if (cmd == "--list-cameras") return cmd_list_cameras();
    if (cmd == "--capabilities") return cmd_capabilities();
    if (cmd == "--record") {
        const KV kv = parse_kv(argc, argv, 2);
        Recorder r;
        r.cfg.mode = kv_str(kv, "mode", "camera");
        r.cfg.out = kv_str(kv, "out");
        r.cfg.camera = kv_str(kv, "camera", "auto");
        r.cfg.audio = kv_str(kv, "audio", "default");
        r.cfg.aspect = kv_str(kv, "aspect", "crop");
        r.cfg.pv = kv_str(kv, "pv");
        r.cfg.w = kv_int(kv, "w", 0);
        r.cfg.h = kv_int(kv, "h", 0);
        r.cfg.fps = kv_int(kv, "fps", 30);
        r.cfg.cw = kv_int(kv, "cw", 1280);
        r.cfg.ch = kv_int(kv, "ch", 720);
        r.cfg.rate = kv_int(kv, "rate", 48000);
        r.cfg.pv_w = std::max(64, kv_int(kv, "pv_w", 480));
        r.cfg.pv_fps = std::max(1, kv_int(kv, "pv_fps", 15));
        if (r.cfg.mode != "camera" && r.cfg.mode != "audio") { log_err("Geçersiz mode"); return 1; }
        return r.run();
    }
    std::cerr << "Bilinmeyen komut: " << cmd << std::endl;
    return 1;
}
#endif  // MEDIA_RECORDER_MAIN
