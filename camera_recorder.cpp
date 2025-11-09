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
#include <string>
#include <vector>
#include <thread>
#include <chrono>
#include <fstream>
#include <cstdlib> // For system()
#include <cstdio>  // For popen/pclose
#include <filesystem> // C++17 for file system operations
#include <sstream> // For stringstream

// Function to merge video and/or audio segments
// This function will be called by Python during the export process.
// It takes paths to text files listing the segments and the final output file.
int mergeRecordings(const std::string& video_list_file, const std::string& audio_list_file, const std::string& output_file) {
    std::cout << "C++: Kayıtlar birleştiriliyor... (" << video_list_file << ", " << audio_list_file << " -> " << output_file << ")" << std::endl;
    fflush(stdout);

    // Check if the list files actually exist and have content
    bool has_video = std::filesystem::exists(video_list_file) && std::filesystem::file_size(video_list_file) > 0;
    bool has_audio = std::filesystem::exists(audio_list_file) && std::filesystem::file_size(audio_list_file) > 0;

    if (!has_video && !has_audio) {
        std::cerr << "C++ Hata: Birleştirme için video veya ses segment listesi sağlanmadı." << std::endl;
        fflush(stderr);
        return 1;
    }

    std::string ffmpeg_command = "ffmpeg -y ";

    // Add concat demuxer inputs
    if (has_video) {
        ffmpeg_command += "-f concat -safe 0 -i \"" + video_list_file + "\" ";
    }
    if (has_audio) {
        ffmpeg_command += "-f concat -safe 0 -i \"" + audio_list_file + "\" ";
    }

    // Mapping streams and codecs with improved synchronization
    if (has_video && has_audio) {
        // Both streams are present. Copy video to preserve quality and speed up the process.
        // Re-encode audio to AAC to fix potential timestamp issues.
        // -vsync cfr ensures a constant frame rate, which is crucial for sync.
        // -shortest flag is added to finish encoding when the shortest stream ends.
        // This helps fix sync issues if audio and video recordings have slightly different lengths.
        ffmpeg_command += "-map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -vsync cfr -shortest ";
    } else if (has_video) {
        // Only video, just copy it.
        ffmpeg_command += "-map 0:v:0 -c:v copy ";
    } else { // Only audio
        // Only audio, copy it directly.
        ffmpeg_command += "-map 0:a:0 -c:a copy ";
    }

    // Output file
    ffmpeg_command += "\"" + output_file + "\"";

    std::cout << "C++: FFmpeg birleştirme komutu: " << ffmpeg_command << std::endl;
    fflush(stdout);

    // Run FFmpeg command
    int result = std::system(ffmpeg_command.c_str());

    if (result != 0) {
        std::cerr << "C++ Hata: FFmpeg birleştirme işlemi " << result << " çıkış koduyla başarısız oldu." << std::endl;
        fflush(stderr);
        return 1;
    }

    // The Python side now handles segment file cleanup. We just clean up the list files.
    try {
        if (has_video) {
            if (std::filesystem::exists(video_list_file)) {
                std::filesystem::remove(video_list_file);
                std::cout << "C++: Video segment listesi dosyası silindi: " << video_list_file << std::endl;
                fflush(stdout);
            }
        }
        if (has_audio) {
            if (std::filesystem::exists(audio_list_file)) {
                std::filesystem::remove(audio_list_file);
                std::cout << "C++: Ses segment listesi dosyası silindi: " << audio_list_file << std::endl;
                fflush(stdout);
            }
        }
    } catch (const std::filesystem::filesystem_error& e) {
        std::cerr << "C++ Hata: Geçici liste dosyası silinirken hata oluştu: " << e.what() << std::endl;
        fflush(stderr);
    }

    std::cout << "C++: Kayıtlar başarıyla birleştirildi: " << output_file << std::endl;
    fflush(stdout);

    return 0;
}


int main(int argc, char* argv[]) {
    // Disable synchronization with C stdio (for faster I/O)
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    std::cout.tie(NULL);
    std::cerr.tie(NULL);

    if (argc < 2) {
        std::cerr << "C++ Hata: Komut argümanı eksik. Kullanım: camera_recorder.exe [komut] [argümanlar...]" << std::endl;
        fflush(stderr);
        return 1;
    }

    std::string command = argv[1];

    if (command == "--merge-recordings") {
        if (argc != 5) {
            std::cerr << "C++ Hata: --merge-recordings için yanlış sayıda argüman. 3 parametre (video_list_file, audio_list_file, output_file) bekleniyordu, " << argc - 2 << " parametre alındı." << std::endl;
            fflush(stderr);
            return 1;
        }
        std::string video_list_file = argv[2];
        std::string audio_list_file = argv[3];
        std::string output_file = argv[4];

        // Use a placeholder for non-existent files so the logic works
        if (video_list_file == "NUL" || video_list_file == "/dev/null") video_list_file = "";
        if (audio_list_file == "NUL" || audio_list_file == "/dev/null") audio_list_file = "";

        return mergeRecordings(video_list_file, audio_list_file, output_file);
    }
    else {
        std::cerr << "C++ Hata: Bilinmeyen komut: " << command << std::endl;
        fflush(stderr);
        return 1;
    }

    std::cout << "C++ Main: Uygulama çıkışı." << std::endl;
    fflush(stdout);
    return 0;
}
