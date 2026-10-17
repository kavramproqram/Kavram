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
// GÜNCELLEME NOTU (2.2.3):
//  - archive_segments_with_compression() eklendi (gz / xz).
//  - extract_segments() magic-byte ile gz/xz otomatik algılar.
//  - export_timeline_media() eklendi: video (mkv/mp4) ve ses-only (wav/mp3/opus/aac/flac).
//  - get_video_dimensions() eklendi (Python tarafında en-boy oranı için).
//  - Mevcut API (archive_segments, merge_timeline_to_video vs.) korunmuştur.
//
// GÜNCELLEME NOTU (2.2.4):
//  - timeline_logic.c içindeki calculate_segment_position() ve update_timeline_smoothly()
//    fonksiyonları bu dosyanın içine (extern "C" bloğuna) taşındı.
//
// GÜNCELLEME NOTU (2.2.5):
//  - Eski Lua uyumluluk katmanı (init_lua_engine, call_lua_segment_calculation,
//    close_lua_engine) TAMAMEN KALDIRILDI.
//
// GÜNCELLEME NOTU (2.2.6):
//  - manifest_has_nonempty_line() eklendi. Sadece "dosya var mı?" değil,
//    "içinde en az bir boş olmayan satır var mı?" kontrolü yapılıyor. Boş
//    manifest dosyası FFmpeg concat için geçersizdir ve exit 183 / -22
//    hatasına yol açıyordu.
//  - export_timeline_media ve merge_timeline_to_video bu yardımcıyı
//    kullanacak şekilde güncellendi.

#include <opencv2/opencv.hpp>
#include <string>
#include <thread>
#include <atomic>
#include <portaudio.h>
#include <sndfile.h>
#include <iostream>
#include <cstring>
#include <chrono>
#include <vector>
#include <cstdio>
#include <numeric>
#include <sstream>
#include <iomanip>
#include <stdexcept>
#include <sys/wait.h>
#include <fstream>
#include <algorithm>
#include <cmath>
#include <cctype>
#include <climits>
#include <cstddef>
#include <limits>
#include <new>

// Shell için güvenli tek tırnaklama.
static std::string shell_quote(const std::string& value) {
    std::string quoted("'");
    for (char c : value) {
        if (c == '\'') {
            quoted += "'\\''";
        } else {
            quoted += c;
        }
    }
    quoted += "'";
    return quoted;
}

static int normalize_pclose_status(int status) {
    if (status < 0) return -1;
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    if (WIFSIGNALED(status)) return 128 + WTERMSIG(status);
    return -1;
}

static int execute_command_capture(const std::string& cmd, const char* label, int open_error) {
    std::cout << "C++: Running " << label << " command: " << cmd << std::endl;
    const std::string capture_cmd = cmd + " 2>&1";
    FILE* pipe = popen(capture_cmd.c_str(), "r");
    if (!pipe) {
        std::cerr << "C++: Could not run " << label << " command: " << cmd << std::endl;
        return open_error;
    }

    std::string result_output;
    char buffer[1024];
    while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
        result_output += buffer;
    }

    const int exit_code = normalize_pclose_status(pclose(pipe));
    if (exit_code != 0) {
        std::cerr << "C++: ERROR: " << label << " command failed (exit code: "
        << exit_code << "). Command: " << cmd << std::endl;
        if (!result_output.empty()) {
            std::cerr << "C++: " << label << " output:\n" << result_output << std::endl;
        }
    }
    return exit_code;
}

int execute_ffmpeg_command(const std::string& cmd) {
    return execute_command_capture(cmd, "FFmpeg", -100);
}

int execute_external_command(const std::string& cmd) {
    return execute_command_capture(cmd, "external", -1);
}

extern "C" {

    struct Frame {
        unsigned char* data;
        int width;
        int height;
        int channels;
        bool data_owner;
    };

    static cv::VideoCapture cap;
    static std::atomic<bool> playing(false);

    // Ses kaydı global değişkenleri
    static std::atomic<bool> g_audio_recording(false);
    static PaStream *audio_stream = nullptr;
    static SNDFILE *audio_sndfile = nullptr;
    static SF_INFO audio_sfinfo;

    // Segment kaydı
    static std::string g_base_audio_filepath_pattern;
    static std::string g_final_merged_audio_filepath;
    static std::atomic<long long> g_frames_recorded_in_segment;
    static const long long FRAMES_PER_SEGMENT = 48000 * 60;
    static int g_current_segment_number;
    static std::vector<std::string> g_recorded_segment_paths;

    static int audioRecordCallback(const void *input, void *, unsigned long frameCount,
                                   const PaStreamCallbackTimeInfo *, PaStreamCallbackFlags,
                                   void *) {
        if (!g_audio_recording || !audio_sndfile) {
            return paComplete;
        }
        if (!input || frameCount == 0) {
            return paContinue;
        }

        const float* float_input = static_cast<const float*>(input);
        std::vector<double> double_buffer(frameCount);
        for (unsigned long i = 0; i < frameCount; ++i) {
            double_buffer[i] = static_cast<double>(float_input[i]);
        }

        const sf_count_t frames_written = sf_writef_double(audio_sndfile, double_buffer.data(), frameCount);
        if (frames_written != static_cast<sf_count_t>(frameCount)) {
            std::cerr << "C++: Error writing audio callback data: " << sf_strerror(audio_sndfile) << std::endl;
            g_audio_recording = false;
            return paComplete;
        }
        g_frames_recorded_in_segment += frames_written;

        if (g_frames_recorded_in_segment >= FRAMES_PER_SEGMENT) {
            std::cout << "C++: 1 minute segment completed. Starting a new audio file..." << std::endl;
            sf_close(audio_sndfile);
            audio_sndfile = nullptr;

            ++g_current_segment_number;
            char segment_filepath[4096] = {0};
            const int written = snprintf(segment_filepath, sizeof(segment_filepath),
                                         g_base_audio_filepath_pattern.c_str(),
                                         g_current_segment_number);
            if (written < 0 || static_cast<size_t>(written) >= sizeof(segment_filepath)) {
                std::cerr << "C++: Audio segment path is too long." << std::endl;
                g_audio_recording = false;
                return paComplete;
            }

            audio_sndfile = sf_open(segment_filepath, SFM_WRITE, &audio_sfinfo);
            if (!audio_sndfile) {
                std::cerr << "C++: Error opening new audio segment file: " << sf_strerror(nullptr) << std::endl;
                g_audio_recording = false;
                return paComplete;
            }
            g_recorded_segment_paths.emplace_back(segment_filepath);
            g_frames_recorded_in_segment = 0;
        }
        return g_audio_recording ? paContinue : paComplete;
                                   }

                                   bool open_video(const char* filepath) {
                                       if (!filepath || *filepath == '\0') return false;
                                       playing = false;
                                       if (cap.isOpened()) cap.release();
                                       return cap.open(filepath);
                                   }

                                   void close_video() {
                                       playing = false;
                                       if (cap.isOpened()) {
                                           cap.release();
                                       }
                                   }

                                   bool read_frame(Frame* out_frame) {
                                       if (!out_frame || !cap.isOpened()) return false;

                                       out_frame->data = nullptr;
                                       out_frame->width = 0;
                                       out_frame->height = 0;
                                       out_frame->channels = 0;
                                       out_frame->data_owner = false;

                                       cv::Mat frame;
                                       if (!cap.read(frame) || frame.empty()) return false;

                                       const size_t data_size = frame.total() * frame.elemSize();
                                       if (data_size == 0 || data_size > static_cast<size_t>(std::numeric_limits<std::ptrdiff_t>::max())) {
                                           return false;
                                       }

                                       unsigned char* data = new (std::nothrow) unsigned char[data_size];
                                       if (!data) {
                                           std::cerr << "C++: Memory allocation failed for frame data." << std::endl;
                                           return false;
                                       }

                                       std::memcpy(data, frame.data, data_size);
                                       out_frame->data = data;
                                       out_frame->data_owner = true;
                                       out_frame->width = frame.cols;
                                       out_frame->height = frame.rows;
                                       out_frame->channels = frame.channels();
                                       return true;
                                   }

                                   void free_frame_data(Frame* frame) {
                                       if (frame && frame->data && frame->data_owner) {
                                           delete[] frame->data;
                                           frame->data = nullptr;
                                           frame->data_owner = false;
                                       }
                                   }

                                   int get_fps() {
                                       if (!cap.isOpened()) return 30;
                                       return static_cast<int>(cap.get(cv::CAP_PROP_FPS));
                                   }

                                   int get_frame_width() {
                                       return static_cast<int>(cap.get(cv::CAP_PROP_FRAME_WIDTH));
                                   }

                                   int get_frame_height() {
                                       return static_cast<int>(cap.get(cv::CAP_PROP_FRAME_HEIGHT));
                                   }

                                   bool is_playing() {
                                       return playing;
                                   }

                                   void set_playing(bool play) {
                                       playing = play;
                                   }

                                   int start_audio_record(const char *base_filepath_pattern, const char *final_filepath) {
                                       if (g_audio_recording) {
                                           std::cout << "C++: Audio recording is already active." << std::endl;
                                           return -1;
                                       }
                                       if (!base_filepath_pattern || !final_filepath || *base_filepath_pattern == '\0' || *final_filepath == '\0') {
                                           std::cerr << "C++: Invalid audio recording path arguments." << std::endl;
                                           return -2;
                                       }

                                       g_base_audio_filepath_pattern = base_filepath_pattern;
                                       g_final_merged_audio_filepath = final_filepath;
                                       g_frames_recorded_in_segment = 0;
                                       g_current_segment_number = 1;
                                       g_recorded_segment_paths.clear();
                                       std::memset(&audio_sfinfo, 0, sizeof(audio_sfinfo));
                                       audio_sfinfo.channels = 1;
                                       audio_sfinfo.samplerate = 48000;
                                       audio_sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_DOUBLE;

                                       char segment_filepath[4096] = {0};
                                       const int written = snprintf(segment_filepath, sizeof(segment_filepath),
                                                                    g_base_audio_filepath_pattern.c_str(),
                                                                    g_current_segment_number);
                                       if (written < 0 || static_cast<size_t>(written) >= sizeof(segment_filepath)) {
                                           std::cerr << "C++: Audio segment path is too long." << std::endl;
                                           return -3;
                                       }

                                       audio_sndfile = sf_open(segment_filepath, SFM_WRITE, &audio_sfinfo);
                                       if (!audio_sndfile) {
                                           std::cerr << "C++: Error opening first audio segment file: " << sf_strerror(nullptr) << std::endl;
                                           return -4;
                                       }
                                       g_recorded_segment_paths.emplace_back(segment_filepath);

                                       PaError err = Pa_OpenDefaultStream(&audio_stream, 1, 0, paFloat32,
                                                                          audio_sfinfo.samplerate,
                                                                          paFramesPerBufferUnspecified,
                                                                          audioRecordCallback, nullptr);
                                       if (err != paNoError) {
                                           std::cerr << "C++: PortAudio error (Pa_OpenDefaultStream): "
                                           << Pa_GetErrorText(err) << std::endl;
                                           sf_close(audio_sndfile);
                                           audio_sndfile = nullptr;
                                           remove(segment_filepath);
                                           g_recorded_segment_paths.clear();
                                           return static_cast<int>(err);
                                       }

                                       g_audio_recording = true;
                                       err = Pa_StartStream(audio_stream);
                                       if (err != paNoError) {
                                           std::cerr << "C++: PortAudio error (Pa_StartStream): "
                                           << Pa_GetErrorText(err) << std::endl;
                                           Pa_CloseStream(audio_stream);
                                           audio_stream = nullptr;
                                           if (audio_sndfile) {
                                               sf_close(audio_sndfile);
                                               audio_sndfile = nullptr;
                                           }
                                           remove(segment_filepath);
                                           g_recorded_segment_paths.clear();
                                           g_audio_recording = false;
                                           return static_cast<int>(err);
                                       }

                                       std::cout << "C++: Audio recording started. Segment pattern: "
                                       << g_base_audio_filepath_pattern << std::endl;
                                       return 0;
                                   }

                                   int merge_audio_files(const char *output_filepath) {
                                       if (!output_filepath || *output_filepath == '\0') return -1;
                                       if (g_recorded_segment_paths.empty()) {
                                           std::cerr << "C++: No audio segments found to merge." << std::endl;
                                           return -2;
                                       }

                                       SF_INFO output_sfinfo{};
                                       output_sfinfo.samplerate = audio_sfinfo.samplerate > 0 ? audio_sfinfo.samplerate : 48000;
                                       output_sfinfo.channels = audio_sfinfo.channels > 0 ? audio_sfinfo.channels : 1;
                                       output_sfinfo.format = audio_sfinfo.format != 0 ? audio_sfinfo.format : (SF_FORMAT_WAV | SF_FORMAT_DOUBLE);

                                       SNDFILE *outfile = sf_open(output_filepath, SFM_WRITE, &output_sfinfo);
                                       if (!outfile) {
                                           std::cerr << "C++: Error opening output file for merging: " << sf_strerror(nullptr) << std::endl;
                                           return -3;
                                       }

                                       double buffer[4096];
                                       for (const auto& segment_path : g_recorded_segment_paths) {
                                           SF_INFO input_sfinfo{};
                                           SNDFILE *infile = sf_open(segment_path.c_str(), SFM_READ, &input_sfinfo);
                                           if (!infile) {
                                               std::cerr << "C++: Could not read segment file: " << segment_path
                                               << " - " << sf_strerror(nullptr) << std::endl;
                                               sf_close(outfile);
                                               remove(output_filepath);
                                               return -4;
                                           }
                                           if (input_sfinfo.samplerate != output_sfinfo.samplerate ||
                                               input_sfinfo.channels != output_sfinfo.channels) {
                                               std::cerr << "C++: Incompatible audio segment format: " << segment_path << std::endl;
                                           sf_close(infile);
                                           sf_close(outfile);
                                           remove(output_filepath);
                                           return -5;
                                               }

                                               sf_count_t frames_read = 0;
                                               while ((frames_read = sf_readf_double(infile, buffer, 4096)) > 0) {
                                                   if (sf_writef_double(outfile, buffer, frames_read) != frames_read) {
                                                       std::cerr << "C++: Error writing to output file: " << sf_strerror(outfile) << std::endl;
                                                       sf_close(infile);
                                                       sf_close(outfile);
                                                       remove(output_filepath);
                                                       return -6;
                                                   }
                                               }
                                               if (frames_read < 0) {
                                                   std::cerr << "C++: Error reading segment file: " << segment_path << std::endl;
                                                   sf_close(infile);
                                                   sf_close(outfile);
                                                   remove(output_filepath);
                                                   return -7;
                                               }
                                               sf_close(infile);
                                       }

                                       if (sf_close(outfile) != 0) {
                                           std::cerr << "C++: Error closing merged output file." << std::endl;
                                           remove(output_filepath);
                                           return -8;
                                       }

                                       for (const auto& segment_path : g_recorded_segment_paths) {
                                           remove(segment_path.c_str());
                                       }
                                       g_recorded_segment_paths.clear();
                                       std::cout << "C++: All audio segments successfully merged: " << output_filepath << std::endl;
                                       return 0;
                                   }

                                   int stop_audio_record() {
                                       const bool was_recording = g_audio_recording.exchange(false);
                                       const bool had_resources = (audio_stream != nullptr) || (audio_sndfile != nullptr);
                                       if (!was_recording && !had_resources) {
                                           std::cout << "C++: Audio recording is not active." << std::endl;
                                           return -1;
                                       }

                                       PaError err_stop = paNoError;
                                       PaError err_close = paNoError;
                                       if (audio_stream) {
                                           err_stop = Pa_StopStream(audio_stream);
                                           err_close = Pa_CloseStream(audio_stream);
                                           audio_stream = nullptr;
                                           if (err_stop != paNoError) {
                                               std::cerr << "C++: PortAudio Pa_StopStream warning: "
                                               << Pa_GetErrorText(err_stop) << std::endl;
                                           }
                                       }

                                       if (audio_sndfile) {
                                           if (sf_close(audio_sndfile) != 0) {
                                               std::cerr << "C++: Error closing audio segment file." << std::endl;
                                               if (err_close == paNoError) err_close = -1;
                                           }
                                           audio_sndfile = nullptr;
                                       }

                                       if (err_close != paNoError) {
                                           std::cerr << "C++: PortAudio error (Pa_CloseStream): "
                                           << Pa_GetErrorText(err_close) << std::endl;
                                           return static_cast<int>(err_close);
                                       }
                                       std::cout << "C++: Audio recording stopped. Merging segments..." << std::endl;
                                       return 0;
                                   }

                                   int init_audio_engine() {
                                       PaError err = Pa_Initialize();
                                       if (err != paNoError) {
                                           std::cerr << "C++: PortAudio initialization error: " << Pa_GetErrorText(err) << std::endl;
                                       }
                                       return err;
                                   }

                                   int terminate_audio_engine() {
                                       PaError err = Pa_Terminate();
                                       if (err != paNoError) {
                                           std::cerr << "C++: PortAudio termination error: " << Pa_GetErrorText(err) << std::endl;
                                       }
                                       return err;
                                   }

                                   bool start_camera_record(const char* device_path, int width, int height, int fps) {
                                       if (cap.isOpened()) {
                                           std::cerr << "C++: Camera is already open." << std::endl;
                                           return false;
                                       }
                                       if (!device_path || *device_path == '\0') {
                                           std::cerr << "C++: Invalid camera device path." << std::endl;
                                           return false;
                                       }

                                       const std::string device(device_path);
                                       bool opened = false;
                                       try {
                                           size_t consumed = 0;
                                           const long long parsed = std::stoll(device, &consumed, 10);
                                           if (consumed == device.size() && parsed >= 0 && parsed <= INT_MAX) {
                                               opened = cap.open(static_cast<int>(parsed));
                                           }
                                       } catch (...) {
                                           // Sayısal değilse aşağıdaki device/path açma denemesi kullanılacak.
                                       }
                                       if (!opened) {
                                           opened = cap.open(device);
                                       }
                                       if (!opened) {
                                           std::cerr << "C++: Could not open camera device: " << device << std::endl;
                                           return false;
                                       }

                                       if (width > 0) cap.set(cv::CAP_PROP_FRAME_WIDTH, width);
                                       if (height > 0) cap.set(cv::CAP_PROP_FRAME_HEIGHT, height);
                                       if (fps > 0) cap.set(cv::CAP_PROP_FPS, fps);
                                       std::cout << "C++: Camera successfully opened for recording." << std::endl;
                                       return true;
                                   }

                                   void stop_camera_record() {
                                       if (cap.isOpened()) {
                                           cap.release();
                                           std::cout << "C++: Camera closed." << std::endl;
                                       } else {
                                           std::cout << "C++: Camera is not open." << std::endl;
                                       }
                                   }

                                   bool is_camera_open() {
                                       return cap.isOpened();
                                   }

                                   long long get_media_duration_ms(const char* filepath) {
                                       if (!filepath || *filepath == '\0') return -1;
                                       const std::string cmd = "ffprobe -v error -show_entries format=duration "
                                       "-of default=noprint_wrappers=1:nokey=1 " + shell_quote(filepath);
                                       FILE* pipe = popen((cmd + " 2>&1").c_str(), "r");
                                       if (!pipe) {
                                           std::cerr << "C++: get_media_duration_ms: Could not run FFprobe." << std::endl;
                                           return -1;
                                       }

                                       char buffer[128];
                                       std::string result;
                                       while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
                                           result += buffer;
                                       }
                                       const int status = normalize_pclose_status(pclose(pipe));
                                       if (status != 0) {
                                           std::cerr << "C++: get_media_duration_ms: FFprobe failed (" << status << ") output: "
                                           << result << std::endl;
                                           return -1;
                                       }

                                       try {
                                           const double duration_seconds = std::stod(result);
                                           if (!std::isfinite(duration_seconds) || duration_seconds <= 0.0) return -1;
                                           const long double duration_ms = static_cast<long double>(duration_seconds) * 1000.0L;
                                           if (duration_ms > static_cast<long double>(LLONG_MAX)) return -1;
                                           return static_cast<long long>(std::llround(duration_ms));
                                       } catch (const std::exception& e) {
                                           std::cerr << "C++: get_media_duration_ms: Error parsing FFprobe output: "
                                           << e.what() << " - Output: '" << result << "'" << std::endl;
                                           return -1;
                                       }
                                   }

                                   int get_video_dimensions(const char* filepath, int* out_width, int* out_height) {
                                       if (!filepath || *filepath == '\0' || !out_width || !out_height) return -1;
                                       *out_width = 0;
                                       *out_height = 0;
                                       cv::VideoCapture tmp_cap;
                                       if (!tmp_cap.open(filepath)) return -1;
                                       *out_width = static_cast<int>(tmp_cap.get(cv::CAP_PROP_FRAME_WIDTH));
                                       *out_height = static_cast<int>(tmp_cap.get(cv::CAP_PROP_FRAME_HEIGHT));
                                       tmp_cap.release();
                                       if (*out_width <= 0 || *out_height <= 0) return -1;
                                       return 0;
                                   }

                                   int cut_media_segment(const char* input_filepath, long long cut_point_ms,
                                                         const char* output_filepath_1, const char* output_filepath_2,
                                                         const char* media_type_str) {
                                       if (!input_filepath || !output_filepath_1 || !output_filepath_2 || !media_type_str ||
                                           *input_filepath == '\0' || *output_filepath_1 == '\0' || *output_filepath_2 == '\0') {
                                           return -1;
                                           }
                                           if (cut_point_ms <= 0) return -2;
                                           if (std::strcmp(input_filepath, output_filepath_1) == 0 ||
                                               std::strcmp(input_filepath, output_filepath_2) == 0 ||
                                               std::strcmp(output_filepath_1, output_filepath_2) == 0) {
                                               return -3;
                                               }

                                               const std::string media_type(media_type_str);
                                           const bool is_video = (media_type == "video" || media_type == "recorded_video");
                                           const bool is_audio = (media_type == "audio" || media_type == "recorded_audio");
                                           if (!is_video && !is_audio) return -4;

                                           const std::string cut_time_str = [&]() {
                                               const long long total_seconds = cut_point_ms / 1000;
                                               const long long hours = total_seconds / 3600;
                                               const long long minutes = (total_seconds % 3600) / 60;
                                               const long long seconds = total_seconds % 60;
                                               const long long milliseconds = cut_point_ms % 1000;
                                               std::ostringstream ss;
                                               ss << std::setfill('0') << std::setw(2) << hours << ":"
                                               << std::setfill('0') << std::setw(2) << minutes << ":"
                                               << std::setfill('0') << std::setw(2) << seconds << "."
                                               << std::setfill('0') << std::setw(3) << milliseconds;
                                               return ss.str();
                                           }();

                                           const std::string input_q = shell_quote(input_filepath);
                                           const std::string out1_q = shell_quote(output_filepath_1);
                                           const std::string out2_q = shell_quote(output_filepath_2);
                                           const std::string mapping = is_video ? "-map 0" : "-map 0:a:0";
                                           const std::string codec = is_video ? "-c copy" : "-c:a copy -vn";

                                           const std::string output_ext = [&]() {
                                               std::string ext = output_filepath_1;
                                               const size_t dot = ext.find_last_of('.');
                                               if (dot == std::string::npos) return std::string();
                                               ext = ext.substr(dot);
                                               std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char c) {
                                                   return static_cast<char>(std::tolower(c));
                                               });
                                               return ext;
                                           }();
                                           const std::string special_format =
                                           (is_video && output_ext == ".rec") ? " -f mp4" :
                                           (is_audio && output_ext == ".saund") ? " -f wav" : "";

                                           const std::string cmd1 = "ffmpeg -v error -i " + input_q +
                                           " -to " + shell_quote(cut_time_str) + " " + mapping +
                                           " -avoid_negative_ts make_zero -y " + codec + special_format + " " + out1_q;
                                           int result1 = execute_ffmpeg_command(cmd1);
                                           if (result1 != 0) {
                                               remove(output_filepath_1);
                                               return -101;
                                           }

                                           const std::string cmd2 = "ffmpeg -v error -ss " + shell_quote(cut_time_str) +
                                           " -i " + input_q + " " + mapping +
                                           " -avoid_negative_ts make_zero -y " + codec + special_format + " " + out2_q;
                                           const int result2 = execute_ffmpeg_command(cmd2);
                                           if (result2 != 0) {
                                               remove(output_filepath_1);
                                               remove(output_filepath_2);
                                               return -102;
                                           }

                                           if (!std::ifstream(output_filepath_1).good() || !std::ifstream(output_filepath_2).good()) {
                                               remove(output_filepath_1);
                                               remove(output_filepath_2);
                                               return -103;
                                           }
                                           std::cout << "C++: Media segment successfully cut (stream copy)." << std::endl;
                                           return 0;
                                                         }

                                                         int delete_media_file(const char* filepath) {
                                                             if (!filepath || *filepath == '\0') return -1;
                                                             const std::string path = filepath;
                                                             if (remove(path.c_str()) != 0) {
                                                                 std::cerr << "C++: Error: Could not delete file: " << path << std::endl;
                                                                 return -2;
                                                             }
                                                             std::cout << "C++: File successfully deleted: " << path << std::endl;
                                                             return 0;
                                                         }

                                                         // ============================================================================
                                                         // ARŞİVLEME / ÇIKARMA
                                                         // ============================================================================

                                                         int archive_segments_with_compression(const char* output_tar_path, const char* temp_dir,
                                                                                               const char* manifest_path, const char* compression) {
                                                             if (!output_tar_path || !temp_dir || *output_tar_path == '\0' || *temp_dir == '\0') return -1;
                                                             const std::string comp = compression ? compression : "gz";
                                                             if (comp != "gz" && comp != "xz") {
                                                                 std::cerr << "C++: Unsupported archive compression: " << comp << std::endl;
                                                                 return -2;
                                                             }
                                                             (void)manifest_path;

                                                             const std::string output_path = output_tar_path;
                                                             const std::string temp_directory = temp_dir;
                                                             const std::string flag = (comp == "xz") ? "-cJf" : "-czf";

                                                             std::stringstream tar_cmd_ss;
                                                             tar_cmd_ss << "cd " << shell_quote(temp_directory) << " && tar " << flag
                                                             << " " << shell_quote(output_path) << " --exclude='.*' -- *";

                                                             const int result = execute_external_command(tar_cmd_ss.str());
                                                             if (result != 0) {
                                                                 std::cerr << "C++: Error: tar (" << comp << ") command failed while archiving segments." << std::endl;
                                                                 return -3;
                                                             }
                                                             return 0;
                                                                                               }

                                                                                               int archive_segments(const char* output_tar_gz_path, const char* temp_dir, const char* manifest_path) {
                                                                                                   return archive_segments_with_compression(output_tar_gz_path, temp_dir, manifest_path, "gz");
                                                                                               }

                                                                                               static std::string detect_compression(const std::string& path) {
                                                                                                   std::ifstream f(path, std::ios::binary);
                                                                                                   if (!f.is_open()) return "";
                                                                                                   unsigned char magic[6] = {0};
                                                                                                   f.read(reinterpret_cast<char*>(magic), sizeof(magic));
                                                                                                   const std::streamsize read_bytes = f.gcount();
                                                                                                   if (read_bytes >= 2 && magic[0] == 0x1f && magic[1] == 0x8b) return "gz";
                                                                                                   if (read_bytes >= 6 && magic[0] == 0xFD && magic[1] == 0x37 && magic[2] == 0x7A &&
                                                                                                       magic[3] == 0x58 && magic[4] == 0x5A && magic[5] == 0x00) return "xz";
                                                                                                   return "";
                                                                                               }

                                                                                               int extract_segments(const char* input_tar_gz_path, const char* output_dir) {
                                                                                                   if (!input_tar_gz_path || !output_dir || *input_tar_gz_path == '\0' || *output_dir == '\0') return -1;
                                                                                                   const std::string input_path = input_tar_gz_path;
                                                                                                   const std::string output_directory = output_dir;

                                                                                                   const std::string comp = detect_compression(input_path);
                                                                                                   std::string flag;
                                                                                                   if (comp == "xz") flag = "-xJf";
                                                                                                   else if (comp == "gz") flag = "-xzf";
                                                                                                   else flag = "-xJf";

                                                                                                   std::stringstream tar_cmd_ss;
                                                                                                   tar_cmd_ss << "tar " << flag << " " << shell_quote(input_path)
                                                                                                   << " -C " << shell_quote(output_directory);
                                                                                                   int result = execute_external_command(tar_cmd_ss.str());

                                                                                                   if (result != 0 && comp.empty()) {
                                                                                                       std::stringstream tar_cmd_gz;
                                                                                                       tar_cmd_gz << "tar -xzf " << shell_quote(input_path)
                                                                                                       << " -C " << shell_quote(output_directory);
                                                                                                       result = execute_external_command(tar_cmd_gz.str());
                                                                                                   }
                                                                                                   if (result != 0) {
                                                                                                       std::cerr << "C++: Error: tar command failed while extracting segments." << std::endl;
                                                                                                       return -2;
                                                                                                   }
                                                                                                   return 0;
                                                                                               }

                                                                                               // ============================================================================
                                                                                               // RENDER / DIŞA AKTARIM
                                                                                               // ============================================================================

                                                                                               // Bir manifest dosyasının "gerçekten satır içerip içermediğini" kontrol eder.
                                                                                               // Sadece var olmak yetmez; boş dosya FFmpeg concat için geçersizdir ve
                                                                                               // exit 183 / hata -22'ye yol açar.
                                                                                               static bool manifest_has_nonempty_line(const std::string& path) {
                                                                                                   if (path.empty()) return false;
                                                                                                   std::ifstream f(path);
                                                                                                   if (!f.good()) return false;
                                                                                                   std::string line;
                                                                                                   while (std::getline(f, line)) {
                                                                                                       for (char c : line) {
                                                                                                           if (!std::isspace(static_cast<unsigned char>(c))) {
                                                                                                               return true;
                                                                                                           }
                                                                                                       }
                                                                                                   }
                                                                                                   return false;
                                                                                               }

                                                                                               int merge_timeline_to_video(const char* output_filepath, const char* temp_dir,
                                                                                                                           const char* video_manifest_filename, const char* audio_manifest_filename) {
                                                                                                   if (!output_filepath || !temp_dir || *output_filepath == '\0' || *temp_dir == '\0') return -1;

                                                                                                   const std::string output_path = output_filepath;
                                                                                                   const std::string temp_directory = temp_dir;
                                                                                                   const std::string video_manifest_name = video_manifest_filename ? video_manifest_filename : "";
                                                                                                   const std::string audio_manifest_name = audio_manifest_filename ? audio_manifest_filename : "";
                                                                                                   const std::string video_manifest_file_path = video_manifest_name.empty() ? "" : temp_directory + "/" + video_manifest_name;
                                                                                                   const std::string audio_manifest_file_path = audio_manifest_name.empty() ? "" : temp_directory + "/" + audio_manifest_name;

                                                                                                   // GÜNCELLEME (2.2.6): boş manifest "yok" sayılır.
                                                                                                   const bool has_video_manifest = manifest_has_nonempty_line(video_manifest_file_path);
                                                                                                   const bool has_audio_manifest = manifest_has_nonempty_line(audio_manifest_file_path);
                                                                                                   if (!has_video_manifest && !has_audio_manifest) {
                                                                                                       std::cerr << "C++: Error: Video or audio manifest file not found or empty. Cannot merge." << std::endl;
                                                                                                       return -2;
                                                                                                   }

                                                                                                   const std::string temp_video_output_path = temp_directory + "/temp_concat_video.mp4";
                                                                                                   const std::string temp_audio_output_path = temp_directory + "/temp_concat_audio.aac";
                                                                                                   remove(temp_video_output_path.c_str());
                                                                                                   remove(temp_audio_output_path.c_str());

                                                                                                   int result = 0;
                                                                                                   if (has_video_manifest) {
                                                                                                       const std::string concat_video_cmd =
                                                                                                       "ffmpeg -v error -f concat -safe 0 -i " + shell_quote(video_manifest_file_path) +
                                                                                                       " -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -movflags +faststart -y " +
                                                                                                       shell_quote(temp_video_output_path);
                                                                                                       result = execute_ffmpeg_command(concat_video_cmd);
                                                                                                       if (result != 0) {
                                                                                                           remove(temp_video_output_path.c_str());
                                                                                                           return -3;
                                                                                                       }
                                                                                                   }

                                                                                                   if (has_audio_manifest) {
                                                                                                       const std::string concat_audio_cmd =
                                                                                                       "ffmpeg -v error -f concat -safe 0 -i " + shell_quote(audio_manifest_file_path) +
                                                                                                       " -c:a aac -b:a 128k -y " + shell_quote(temp_audio_output_path);
                                                                                                       result = execute_ffmpeg_command(concat_audio_cmd);
                                                                                                       if (result != 0) {
                                                                                                           remove(temp_video_output_path.c_str());
                                                                                                           remove(temp_audio_output_path.c_str());
                                                                                                           return -4;
                                                                                                       }
                                                                                                   }

                                                                                                   std::string final_merge_cmd = "ffmpeg -v error";
                                                                                                   if (has_video_manifest && has_audio_manifest) {
                                                                                                       final_merge_cmd += " -i " + shell_quote(temp_video_output_path) +
                                                                                                       " -i " + shell_quote(temp_audio_output_path) +
                                                                                                       " -c:v copy -c:a copy -map 0:v:0 -map 1:a:0 -map_metadata 0 "
                                                                                                       "-movflags +faststart -shortest -y " + shell_quote(output_path);
                                                                                                   } else if (has_video_manifest) {
                                                                                                       final_merge_cmd += " -i " + shell_quote(temp_video_output_path) +
                                                                                                       " -c:v copy -map_metadata 0 -movflags +faststart -y " + shell_quote(output_path);
                                                                                                   } else {
                                                                                                       const long long audio_duration_ms = get_media_duration_ms(temp_audio_output_path.c_str());
                                                                                                       if (audio_duration_ms <= 0) {
                                                                                                           remove(temp_audio_output_path.c_str());
                                                                                                           return -5;
                                                                                                       }
                                                                                                       const double duration_sec = static_cast<double>(audio_duration_ms) / 1000.0;
                                                                                                       final_merge_cmd += " -f lavfi -i " + shell_quote("color=c=black:s=1280x720:d=" + std::to_string(duration_sec)) +
                                                                                                       " -i " + shell_quote(temp_audio_output_path) +
                                                                                                       " -c:v libx264 -preset ultrafast -crf 23 -c:a copy "
                                                                                                       "-map 0:v:0 -map 1:a:0 -map_metadata 0 -movflags +faststart -shortest -y " +
                                                                                                       shell_quote(output_path);
                                                                                                   }

                                                                                                   result = execute_ffmpeg_command(final_merge_cmd);
                                                                                                   remove(temp_video_output_path.c_str());
                                                                                                   remove(temp_audio_output_path.c_str());
                                                                                                   if (result != 0) return -6;
                                                                                                   return 0;
                                                                                                                           }

                                                                                                                           int export_timeline_media(const char* output_filepath, const char* temp_dir,
                                                                                                                                                     const char* video_manifest_filename, const char* audio_manifest_filename,
                                                                                                                                                     const char* output_format) {
                                                                                                                               if (!output_filepath || !temp_dir || *output_filepath == '\0' || *temp_dir == '\0') return -1;

                                                                                                                               const std::string output_path = output_filepath;
                                                                                                                               const std::string temp_directory = temp_dir;
                                                                                                                               const std::string video_manifest_name = video_manifest_filename ? video_manifest_filename : "";
                                                                                                                               const std::string audio_manifest_name = audio_manifest_filename ? audio_manifest_filename : "";
                                                                                                                               const std::string video_manifest_file_path = video_manifest_name.empty() ? "" : temp_directory + "/" + video_manifest_name;
                                                                                                                               const std::string audio_manifest_file_path = audio_manifest_name.empty() ? "" : temp_directory + "/" + audio_manifest_name;

                                                                                                                               std::string fmt = output_format ? output_format : "mkv";
                                                                                                                               std::transform(fmt.begin(), fmt.end(), fmt.begin(), [](unsigned char c) {
                                                                                                                                   return static_cast<char>(std::tolower(c));
                                                                                                                               });
                                                                                                                               const std::vector<std::string> allowed_formats = {
                                                                                                                                   "mkv", "mp4", "wav", "mp3", "opus", "m4a", "aac", "flac", "ogg"
                                                                                                                               };
                                                                                                                               if (std::find(allowed_formats.begin(), allowed_formats.end(), fmt) == allowed_formats.end()) {
                                                                                                                                   std::cerr << "C++: export_timeline_media: Unsupported format: " << fmt << std::endl;
                                                                                                                                   return -2;
                                                                                                                               }

                                                                                                                               // GÜNCELLEME (2.2.6): boş manifest "yok" sayılır; exit 183 / -22 hatası
                                                                                                                               // artık oluşmaz.
                                                                                                                               const bool has_video_manifest = manifest_has_nonempty_line(video_manifest_file_path);
                                                                                                                               const bool has_audio_manifest = manifest_has_nonempty_line(audio_manifest_file_path);
                                                                                                                               const bool is_audio_only = (fmt == "wav" || fmt == "mp3" || fmt == "opus" ||
                                                                                                                               fmt == "aac" || fmt == "m4a" || fmt == "flac" || fmt == "ogg");

                                                                                                                               if (is_audio_only) {
                                                                                                                                   if (!has_audio_manifest) return -10;
                                                                                                                                   const std::string temp_audio = temp_directory + "/temp_export_audio.wav";
                                                                                                                                   remove(temp_audio.c_str());

                                                                                                                                   const std::string concat_cmd =
                                                                                                                                   "ffmpeg -v error -f concat -safe 0 -i " + shell_quote(audio_manifest_file_path) +
                                                                                                                                   " -c:a pcm_s16le -ar 48000 -ac 1 -y " + shell_quote(temp_audio);
                                                                                                                                   int r = execute_ffmpeg_command(concat_cmd);
                                                                                                                                   if (r != 0) {
                                                                                                                                       remove(temp_audio.c_str());
                                                                                                                                       return -11;
                                                                                                                                   }

                                                                                                                                   std::string codec_args;
                                                                                                                                   if (fmt == "wav") codec_args = "-c:a pcm_s16le";
                                                                                                                                   else if (fmt == "mp3") codec_args = "-c:a libmp3lame -b:a 192k";
                                                                                                                                   else if (fmt == "opus") codec_args = "-c:a libopus -b:a 128k";
                                                                                                                                   else if (fmt == "aac" || fmt == "m4a") codec_args = "-c:a aac -b:a 192k";
                                                                                                                                   else if (fmt == "flac") codec_args = "-c:a flac";
                                                                                                                                   else codec_args = "-c:a libvorbis -q:a 5";

                                                                                                                                   const std::string convert_cmd = "ffmpeg -v error -i " + shell_quote(temp_audio) +
                                                                                                                                   " " + codec_args + " -y " + shell_quote(output_path);
                                                                                                                                   r = execute_ffmpeg_command(convert_cmd);
                                                                                                                                   remove(temp_audio.c_str());
                                                                                                                                   return r == 0 ? 0 : -12;
                                                                                                                               }

                                                                                                                               if (fmt != "mkv" && fmt != "mp4") return -13;
                                                                                                                               if (!has_video_manifest && !has_audio_manifest) return -20;

                                                                                                                               const std::string temp_concat_video = temp_directory + "/temp_concat_video.mp4";
                                                                                                                               const std::string temp_concat_audio = temp_directory + "/temp_concat_audio.aac";
                                                                                                                               remove(temp_concat_video.c_str());
                                                                                                                               remove(temp_concat_audio.c_str());

                                                                                                                               if (has_video_manifest) {
                                                                                                                                   const std::string concat_v =
                                                                                                                                   "ffmpeg -v error -f concat -safe 0 -i " + shell_quote(video_manifest_file_path) +
                                                                                                                                   " -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -movflags +faststart -y " +
                                                                                                                                   shell_quote(temp_concat_video);
                                                                                                                                   const int r = execute_ffmpeg_command(concat_v);
                                                                                                                                   if (r != 0) {
                                                                                                                                       remove(temp_concat_video.c_str());
                                                                                                                                       remove(temp_concat_audio.c_str());
                                                                                                                                       return -21;
                                                                                                                                   }
                                                                                                                               }

                                                                                                                               if (has_audio_manifest) {
                                                                                                                                   const std::string concat_a =
                                                                                                                                   "ffmpeg -v error -f concat -safe 0 -i " + shell_quote(audio_manifest_file_path) +
                                                                                                                                   " -c:a aac -b:a 192k -y " + shell_quote(temp_concat_audio);
                                                                                                                                   const int r = execute_ffmpeg_command(concat_a);
                                                                                                                                   if (r != 0) {
                                                                                                                                       remove(temp_concat_video.c_str());
                                                                                                                                       remove(temp_concat_audio.c_str());
                                                                                                                                       return -22;
                                                                                                                                   }
                                                                                                                               }

                                                                                                                               const std::string v_codec = "-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p";
                                                                                                                               const std::string a_codec = "-c:a aac -b:a 192k";
                                                                                                                               const std::string extra = (fmt == "mp4") ? "-movflags +faststart" : "";
                                                                                                                               std::string final_cmd = "ffmpeg -v error";

                                                                                                                               if (has_video_manifest && has_audio_manifest) {
                                                                                                                                   final_cmd += " -i " + shell_quote(temp_concat_video) + " -i " + shell_quote(temp_concat_audio) +
                                                                                                                                   " " + v_codec + " " + a_codec +
                                                                                                                                   " -map 0:v:0 -map 1:a:0 -map_metadata 0 " + extra +
                                                                                                                                   " -shortest -y " + shell_quote(output_path);
                                                                                                                               } else if (has_video_manifest) {
                                                                                                                                   final_cmd += " -i " + shell_quote(temp_concat_video) +
                                                                                                                                   " " + v_codec + " -map 0:v:0 -map_metadata 0 " + extra +
                                                                                                                                   " -y " + shell_quote(output_path);
                                                                                                                               } else {
                                                                                                                                   const long long audio_dur = get_media_duration_ms(temp_concat_audio.c_str());
                                                                                                                                   if (audio_dur <= 0) {
                                                                                                                                       remove(temp_concat_audio.c_str());
                                                                                                                                       return -23;
                                                                                                                                   }
                                                                                                                                   const double dur_sec = static_cast<double>(audio_dur) / 1000.0;
                                                                                                                                   const std::string color_source = "color=c=black:s=1280x720:d=" + std::to_string(dur_sec);
                                                                                                                                   final_cmd += " -f lavfi -i " + shell_quote(color_source) +
                                                                                                                                   " -i " + shell_quote(temp_concat_audio) +
                                                                                                                                   " " + v_codec + " " + a_codec +
                                                                                                                                   " -map 0:v:0 -map 1:a:0 -map_metadata 0 " + extra +
                                                                                                                                   " -shortest -y " + shell_quote(output_path);
                                                                                                                               }

                                                                                                                               const int r = execute_ffmpeg_command(final_cmd);
                                                                                                                               remove(temp_concat_video.c_str());
                                                                                                                               remove(temp_concat_audio.c_str());
                                                                                                                               if (r != 0) return -30;
                                                                                                                               return 0;
                                                                                                                                                     }

                                                                                                                                                     // ============================================================================
                                                                                                                                                     // Timeline logic engine
                                                                                                                                                     // ============================================================================

                                                                                                                                                     double calculate_segment_position(double start_time_ms, double timeline_width, double total_timeline_duration_ms) {
                                                                                                                                                         if (!std::isfinite(start_time_ms) || !std::isfinite(timeline_width) || !std::isfinite(total_timeline_duration_ms)) {
                                                                                                                                                             return 0.0;
                                                                                                                                                         }
                                                                                                                                                         if (total_timeline_duration_ms <= 0.0 || timeline_width <= 0.0) {
                                                                                                                                                             return 0.0;
                                                                                                                                                         }
                                                                                                                                                         if (start_time_ms < 0.0) {
                                                                                                                                                             start_time_ms = 0.0;
                                                                                                                                                         }
                                                                                                                                                         double position_ratio = start_time_ms / total_timeline_duration_ms;
                                                                                                                                                         if (position_ratio < 0.0) position_ratio = 0.0;
                                                                                                                                                         if (position_ratio > 1.0) position_ratio = 1.0;
                                                                                                                                                         return position_ratio * timeline_width;
                                                                                                                                                     }

                                                                                                                                                     double update_timeline_smoothly(double current_value, double target_value, double step_size) {
                                                                                                                                                         if (!std::isfinite(current_value) && !std::isfinite(target_value)) {
                                                                                                                                                             return 0.0;
                                                                                                                                                         }
                                                                                                                                                         if (!std::isfinite(target_value)) {
                                                                                                                                                             return std::isfinite(current_value) ? current_value : 0.0;
                                                                                                                                                         }
                                                                                                                                                         if (!std::isfinite(current_value)) {
                                                                                                                                                             return target_value;
                                                                                                                                                         }
                                                                                                                                                         if (current_value == target_value) {
                                                                                                                                                             return current_value;
                                                                                                                                                         }
                                                                                                                                                         if (!std::isfinite(step_size) || step_size <= 0.0) {
                                                                                                                                                             return target_value;
                                                                                                                                                         }
                                                                                                                                                         if (std::fabs(target_value - current_value) < step_size) {
                                                                                                                                                             return target_value;
                                                                                                                                                         }
                                                                                                                                                         if (current_value < target_value) {
                                                                                                                                                             return current_value + step_size;
                                                                                                                                                         }
                                                                                                                                                         return current_value - step_size;
                                                                                                                                                     }

} // extern "C"
