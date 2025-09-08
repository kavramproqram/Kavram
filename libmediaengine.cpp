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

// media_engine.cpp

#include <opencv2/opencv.hpp>
#include <string>
#include <thread>
#include <atomic>
#include <portaudio.h> // PortAudio library added
#include <sndfile.h>   // libsndfile library added
#include <iostream>    // Added for error messages
#include <cstring>     // Added for memcpy
#include <chrono>      // For time delay
#include <vector>      // For storing segment paths
#include <cstdio>      // For remove
#include <numeric>     // For accumulate
#include <sstream>     // For string stream
#include <iomanip>     // For setprecision - This was corrected!
#include <stdexcept>   // For std::runtime_error
#include <sys/wait.h>  // For WEXITSTATUS
#include <fstream>     // Added for file operations
#include <algorithm>   // Added for std::replace

// Lua C API headers
extern "C" {
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>
}

// Helper function to execute FFmpeg command
// This function is now globally defined and can be used by all C functions.
int execute_ffmpeg_command(const std::string& cmd) {
    std::cout << "C++: Running FFmpeg command: " << cmd << std::endl;
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) {
        std::cerr << "C++: Could not run FFmpeg command: " << cmd << std::endl;
        return -100; // Command execution failed error
    }
    char buffer[1024];
    std::string result_output = "";
    while (fgets(buffer, sizeof(buffer), pipe) != NULL) {
        result_output += buffer;
    }
    int exit_code = pclose(pipe);

    // pclose returns the exit code of the command. Normally 0 is success.
    // We can get the actual exit code with WIFEXITED macro (on POSIX systems)
    if (WIFEXITED(exit_code)) {
        exit_code = WEXITSTATUS(exit_code);
    } else {
        exit_code = -1; // Command did not terminate normally (e.g., terminated by signal)
    }

    if (exit_code != 0) {
        std::cerr << "C++: ERROR: FFmpeg command failed (exit code: " << exit_code << "). Command: " << cmd << std::endl;
        std::cerr << "C++: FFmpeg output:\n" << result_output << std::endl;
    }
    return exit_code;
}

// New: General helper function to run external commands
int execute_external_command(const std::string& cmd) {
    std::cout << "C++: Running external command: " << cmd << std::endl;
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) {
        std::cerr << "C++: Could not run external command: " << cmd << std::endl;
        return -1;
    }
    std::string result_output = "";
    char buffer[1024];
    while (fgets(buffer, sizeof(buffer), pipe) != NULL) {
        result_output += buffer;
    }
    int exit_code = pclose(pipe);
    if (WIFEXITED(exit_code)) {
        exit_code = WEXITSTATUS(exit_code);
    } else {
        exit_code = -1;
    }
    if (exit_code != 0) {
        std::cerr << "C++: ERROR: External command failed (exit code: " << exit_code << "). Command: " << cmd << std::endl;
        std::cerr << "C++: Output:\n" << result_output << std::endl;
    }
    return exit_code;
}


extern "C" {

struct Frame {
    unsigned char* data;
    int width;
    int height;
    int channels;
    bool data_owner; // Indicates whether this Frame owns the 'data' pointer.
};

static cv::VideoCapture cap;
static std::atomic<bool> playing(false);

// Global variables for audio recording
static std::atomic<bool> g_audio_recording(false);
static PaStream *audio_stream = nullptr;
static SNDFILE *audio_sndfile = nullptr; // nullptr initially
static SF_INFO audio_sfinfo;

// Global variables for segmented recording
static std::string g_base_audio_filepath_pattern; // E.g.: "/path/to/rec_audio_%03d.wav"
static std::string g_final_merged_audio_filepath;
static std::atomic<long long> g_frames_recorded_in_segment;
static const long long FRAMES_PER_SEGMENT = 48000 * 60; // 1 minute (sample rate * seconds)
static int g_current_segment_number;
static std::vector<std::string> g_recorded_segment_paths; // Paths of recorded segments

// Global variable for Lua state
lua_State *L = nullptr;

// Audio recording callback function
static int audioRecordCallback(const void *input, void *, unsigned long frameCount,
                               const PaStreamCallbackTimeInfo *, PaStreamCallbackFlags,
                               void *) {
    if (g_audio_recording && audio_sndfile) {
        // Convert 32-bit float data from PortAudio to 64-bit double.
        const float* float_input = (const float*)input;
        std::vector<double> double_buffer(frameCount);
        for (unsigned long i = 0; i < frameCount; ++i) {
            double_buffer[i] = static_cast<double>(float_input[i]);
        }
        sf_writef_double(audio_sndfile, double_buffer.data(), frameCount);
        g_frames_recorded_in_segment += frameCount;

        // Create a new file if 1 minute segment duration is reached
        if (g_frames_recorded_in_segment >= FRAMES_PER_SEGMENT) {
            std::cout << "C++: 1 minute segment completed. Starting a new audio file..." << std::endl;
            sf_close(audio_sndfile); // Close current file
            audio_sndfile = nullptr;

            g_current_segment_number++;
            char segment_filepath[256];
            snprintf(segment_filepath, sizeof(segment_filepath), g_base_audio_filepath_pattern.c_str(), g_current_segment_number);

            audio_sndfile = sf_open(segment_filepath, SFM_WRITE, &audio_sfinfo);
            if (!audio_sndfile) {
                std::cerr << "C++: Error opening new audio segment file: " << sf_strerror(NULL) << std::endl;
                g_audio_recording = false; // Stop recording
                return paComplete; // Complete callback
            }
            g_recorded_segment_paths.push_back(segment_filepath); // Save new segment path
            g_frames_recorded_in_segment = 0; // Reset frame counter for segment
        }
    }
    return g_audio_recording ? paContinue : paComplete;
}

// Function to open video
bool open_video(const char* filepath) {
    cap.open(filepath);
    return cap.isOpened();
}

// Function to close video
void close_video() {
    playing = false;
    if (cap.isOpened()) {
        cap.release();
    }
}

// Function to read frame
bool read_frame(Frame* out_frame) {
    if (!cap.isOpened()) return false;

    cv::Mat frame;
    if (!cap.read(frame)) return false;

    // Calculate data size
    size_t data_size = frame.total() * frame.elemSize();

    // Dynamically allocate memory and copy data
    out_frame->data = new unsigned char[data_size];
    if (!out_frame->data) {
        std::cerr << "C++: Memory allocation failed for frame data." << std::endl;
        return false;
    }
    memcpy(out_frame->data, frame.data, data_size);
    out_frame->data_owner = true; // Mark that this frame owns this memory area

    out_frame->width = frame.cols;
    out_frame->height = frame.rows;
    out_frame->channels = frame.channels();

    return true;
}

// Function to free dynamically allocated data in Frame, to be called by Python
void free_frame_data(Frame* frame) {
    if (frame && frame->data && frame->data_owner) {
        delete[] frame->data;
        frame->data = nullptr;
        frame->data_owner = false;
    }
}

// Function to get FPS
int get_fps() {
    if (!cap.isOpened()) return 30;
    return static_cast<int>(cap.get(cv::CAP_PROP_FPS));
}

// Function to get frame width
int get_frame_width() {
    return static_cast<int>(cap.get(cv::CAP_PROP_FRAME_WIDTH));
}

// Function to get frame height
int get_frame_height() {
    return static_cast<int>(cap.get(cv::CAP_PROP_FRAME_HEIGHT));
}

// Function to check playback status
bool is_playing() {
    return playing;
}

// Function to set playback status
void set_playing(bool play) {
    playing = play;
}

// Function to start audio recording
// base_filepath_pattern: File name pattern for recorded segments (e.g., "/path/to/rec_audio_%03d.wav")
// final_filepath: Final file name where all segments will be merged
int start_audio_record(const char *base_filepath_pattern, const char *final_filepath) {
    if (g_audio_recording) {
        std::cout << "C++: Audio recording is already active." << std::endl;
        return -1; // Return error if already recording
    }

    g_base_audio_filepath_pattern = base_filepath_pattern;
    g_final_merged_audio_filepath = final_filepath;
    g_frames_recorded_in_segment = 0;
    g_current_segment_number = 1;
    g_recorded_segment_paths.clear(); // Clear previous segment paths

    audio_sfinfo.channels = 1;
    audio_sfinfo.samplerate = 48000; // Sample rate updated to 48000
    // WAV format, set to 64-bit Double
    audio_sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_DOUBLE;

    // Open the first segment file
    char segment_filepath[256];
    snprintf(segment_filepath, sizeof(segment_filepath), g_base_audio_filepath_pattern.c_str(), g_current_segment_number);
    audio_sndfile = sf_open(segment_filepath, SFM_WRITE, &audio_sfinfo);
    if (!audio_sndfile) {
        std::cerr << "C++: Error opening first audio segment file: " << sf_strerror(NULL) << std::endl;
        return -2; // Return error if file cannot be opened
    }
    g_recorded_segment_paths.push_back(segment_filepath); // Save path of first segment

    // Open PortAudio in 32-bit float format
    PaError err = Pa_OpenDefaultStream(&audio_stream, 1, 0, paFloat32, audio_sfinfo.samplerate, // Reverted to paFloat32
                                       paFramesPerBufferUnspecified, audioRecordCallback, nullptr);
    if (err != paNoError) {
        std::cerr << "C++: PortAudio error (Pa_OpenDefaultStream): " << Pa_GetErrorText(err) << std::endl;
        sf_close(audio_sndfile); // Close file on error
        audio_sndfile = nullptr;
        return err; // Return error if stream cannot be opened
    }

    g_audio_recording = true; // Set recording status to true
    err = Pa_StartStream(audio_stream);
    if (err != paNoError) {
        std::cerr << "C++: PortAudio error (Pa_StartStream): " << Pa_GetErrorText(err) << std::endl;
        Pa_CloseStream(audio_stream); // Close stream on error
        audio_stream = nullptr;
        if (audio_sndfile) {
            sf_close(audio_sndfile); // Close file on error
            audio_sndfile = nullptr;
        }
        g_audio_recording = false; // Reset flag on error
        return err; // Return error if stream cannot be started
    }

    std::cout << "C++: Audio recording started. Segment pattern: " << g_base_audio_filepath_pattern << std::endl;
    return 0; // Success
}

// Merges all recorded audio segments into a single file
int merge_audio_files(const char *output_filepath) {
    if (g_recorded_segment_paths.empty()) {
        std::cerr << "C++: No audio segments found to merge." << std::endl;
        return -1;
    }

    SF_INFO output_sfinfo = audio_sfinfo; // Output file format same as input files

    SNDFILE *outfile = sf_open(output_filepath, SFM_WRITE, &output_sfinfo);
    if (!outfile) {
        std::cerr << "C++: Error opening output file for merging: " << sf_strerror(NULL) << std::endl;
        return -2;
    }

    double buffer[4096]; // Buffer type changed from float to double
    sf_count_t frames_read;

    for (const auto& segment_path : g_recorded_segment_paths) {
        SNDFILE *infile = sf_open(segment_path.c_str(), SFM_READ, &audio_sfinfo);
        if (!infile) {
            std::cerr << "C++: Could not read segment file: " << segment_path << " - " << sf_strerror(NULL) << std::endl;
            // Continue merging others even if one segment cannot be read
            continue;
        }

        while ((frames_read = sf_readf_double(infile, buffer, 4096)) > 0) { // Changed from sf_readf_float to sf_readf_double
            if (sf_writef_double(outfile, buffer, frames_read) != frames_read) { // Changed from sf_writef_float to sf_writef_double
                std::cerr << "C++: Error writing to output file: " << sf_strerror(NULL) << std::endl;
                sf_close(infile);
                sf_close(outfile);
                return -3;
            }
        }
        sf_close(infile);
        std::cout << "C++: Segment merged and cleaned: " << segment_path << std::endl;
        remove(segment_path.c_str()); // Clean up merged segment file
    }

    sf_close(outfile);
    g_recorded_segment_paths.clear(); // Clear list as all segments are merged
    std::cout << "C++: All audio segments successfully merged: " << output_filepath << std::endl;
    return 0; // Success
}

// Function to stop audio recording
int stop_audio_record() {
    if (!g_audio_recording) {
        std::cout << "C++: Audio recording is not active." << std::endl;
        return -1; // Return error if not recording
    }

    g_audio_recording = false; // Set recording status to false

    // Add a short delay to wait for the stream to stop
    // Allow PortAudio to complete its last callback
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    PaError err_stop = paNoError;
    PaError err_close = paNoError;

    if (audio_stream) {
        err_stop = Pa_StopStream(audio_stream);
        err_close = Pa_CloseStream(audio_stream);
        audio_stream = nullptr; // Reset stream pointer
    }

    if (audio_sndfile) {
        sf_close(audio_sndfile); // Close the last open segment file
        audio_sndfile = nullptr; // Reset pointer
    }

    if (err_stop != paNoError) {
        std::cerr << "C++: PortAudio error (Pa_StopStream): " << Pa_GetErrorText(err_stop) << std::endl;
        return err_stop;
    }
    if (err_close != paNoError) {
        std::cerr << "C++: PortAudio error (Pa_CloseStream): " << Pa_GetErrorText(err_close) << std::endl;
        return err_close;
    }

    std::cout << "C++: Audio recording stopped. Merging segments..." << std::endl;
    // Merge segments after recording stops
    // The merge_audio_files function will now be called by Python.
    // This C++ function only stops recording.

    return 0; // Success
}

// Function to initialize PortAudio
int init_audio_engine() {
    PaError err = Pa_Initialize();
    if (err != paNoError) {
        std::cerr << "C++: PortAudio initialization error: " << Pa_GetErrorText(err) << std::endl;
    }
    return err;
}

// Function to terminate PortAudio
int terminate_audio_engine() {
    PaError err = Pa_Terminate();
    if (err != paNoError) {
        std::cerr << "C++: PortAudio termination error: " << Pa_GetErrorText(err) << std::endl;
    }
    return err;
}

// Function to start camera recording
bool start_camera_record(const char* device_path, int width, int height, int fps) {
    if (cap.isOpened()) {
        std::cerr << "C++: Camera is already open." << std::endl;
        return false;
    }
    int camera_id = 0; // Default camera
    if (device_path && std::string(device_path) != "0") {
        // Advanced cases can add device path processing here.
        // If device_path is a numeric value, use it as camera_id.
        try {
            camera_id = std::stoi(device_path);
        } catch (const std::invalid_argument& ia) {
            std::cerr << "C++: Invalid camera ID/path: " << device_path << ". Using default (0)." << std::endl;
        } catch (const std::out_of_range& oor) {
            std::cerr << "C++: Camera ID/path out of range: " << device_path << ". Using default (0)." << std::endl;
        }
    }

    // Check previous state of VideoCapture before attempting to open camera
    if (!cap.open(camera_id)) {
        std::cerr << "C++: Could not open camera with ID " << camera_id << "." << std::endl;
        return false;
    }
    // Set camera parameters (optional, OpenCV does it automatically)
    cap.set(cv::CAP_PROP_FRAME_WIDTH, width);
    cap.set(cv::CAP_PROP_FRAME_HEIGHT, height);
    cap.set(cv::CAP_PROP_FPS, fps);

    std::cout << "C++: Camera successfully opened for recording." << std::endl;
    return true;
}

// Function to stop camera recording
void stop_camera_record() {
    if (cap.isOpened()) {
        cap.release();
        std::cout << "C++: Camera closed." << std::endl;
    } else {
        std::cout << "C++: Camera is not open." << std::endl;
    }
}

// Check if camera is open
bool is_camera_open() {
    return cap.isOpened();
}

// Returns media file duration in milliseconds (using ffprobe)
long long get_media_duration_ms(const char* filepath) {
    std::string cmd = "ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 \"";
    cmd += filepath;
    cmd += "\"";
    // Now that execute_ffmpeg_command is global, we can call it directly.
    // However, we need to capture ffprobe output, so popen usage continues.
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) {
        std::cerr << "C++: get_media_duration_ms: Could not run FFprobe." << std::endl;
        return -1;
    }
    char buffer[128];
    std::string result = "";
    while (fgets(buffer, sizeof(buffer), pipe) != NULL) {
        result += buffer;
    }
    pclose(pipe);

    try {
        double duration_seconds = std::stod(result);
        return static_cast<long long>(duration_seconds * 1000); // Convert to milliseconds
    } catch (const std::exception& e) {
        std::cerr << "C++: get_media_duration_ms: Error parsing FFprobe output: " << e.what() << " - Output: '" << result << "'" << std::endl;
        return -1;
    }
}


// Media file cutting operation (using FFmpeg)
// ffmpeg -ss [start] -i input.mp4 -to [end] -c:v libx64 -preset veryfast -crf 23 -c:a aac -b:a 128k output.mp4
int cut_media_segment(const char* input_filepath, long long cut_point_ms,
                        const char* output_filepath_1, const char* output_filepath_2,
                        const char* media_type_str) {
    std::string input_path = input_filepath;
    std::string output_path_1 = output_filepath_1;
    std::string output_path_2 = output_filepath_2;
    std::string media_type = media_type_str;

    // Convert milliseconds to HH:MM:SS.mmm format
    auto format_time_ms = [](long long ms) {
        long long total_seconds = ms / 1000;
        long long hours = total_seconds / 3600;
        long long minutes = (total_seconds % 3600) / 60;
        long long seconds = total_seconds % 60;
        long long milliseconds_remainder = ms % 1000;
        std::stringstream ss;
        ss << std::setfill('0') << std::setw(2) << hours << ":"
           << std::setfill('0') << std::setw(2) << minutes << ":"
           << std::setfill('0') << std::setw(2) << seconds << "."
           << std::setfill('0') << std::setw(3) << milliseconds_remainder; // Millisecond precision
        return ss.str();
    };

    std::string cut_time_str = format_time_ms(cut_point_ms);

    std::string codec_options;
    std::string map_stream_option; // New option for stream selection
    std::string output_format_flag; // New flag to force output format

    // Common options: "-map_metadata 0" for metadata copying, "-movflags +faststart" for fast web playback
    // These options are still valid for stream copy.
    std::string common_options = "-map_metadata 0 -movflags +faststart";

    // Stream copy option. Does not re-encode, which speeds up the process.
    std::string stream_copy_option = "-c copy";

    if (media_type == "video" || media_type == "recorded_video") {
        // Copy all streams including video and audio
        codec_options = stream_copy_option;
        map_stream_option = "-map 0"; // Copy all streams
        output_format_flag = "-f mp4"; // Force MP4 format
    } else { // audio or recorded_audio
        // Copy only audio stream. -vn disables video streams.
        codec_options = "-c:a copy -vn";
        map_stream_option = "-map 0:a"; // Select only audio stream
        output_format_flag = "-f wav"; // Force WAV format
    }

    // First part (from 0 to cut point)
    // The order "-i [input] -to [end]" provides more precise cutting at the end point.
    std::string cmd1 = "ffmpeg -i \"" + input_path +
                       "\" -to " + cut_time_str + " " + map_stream_option + " " + output_format_flag + " -y " + codec_options + " " + common_options + " \"" + output_path_1 + "\"";
    std::cout << "C++: Running FFmpeg command 1 (stream copy): " << cmd1 << std::endl;
    int result1 = execute_ffmpeg_command(cmd1);
    if (result1 != 0) {
        std::cerr << "C++: Error: FFmpeg command 1 failed." << std::endl;
        return -101; // Command 1 failed
    }
    std::cout << "C++: FFmpeg command 1 successful." << std::endl;

    // Second part (from cut point to end)
    // The order "-ss [start] -i [input]" performs fast seek. Used with stream copy.
    std::string cmd2 = "ffmpeg -ss " + cut_time_str + " -i \"" + input_path +
                       "\" " + map_stream_option + " " + output_format_flag + " -y " + codec_options + " " + common_options + " \"" + output_path_2 + "\"";
    std::cout << "C++: Running FFmpeg command 2 (stream copy): " << cmd2 << std::endl;
    int result2 = execute_ffmpeg_command(cmd2);
    if (result2 != 0) {
        std::cerr << "C++: Error: FFmpeg command 2 failed." << std::endl;
        // Clean up if first file was successful but second failed
        remove(output_path_1.c_str());
        return -102; // Command 2 failed
    }
    std::cout << "C++: FFmpeg command 2 successful." << std::endl;

    std::cout << "C++: Media segment successfully cut (Stream Copy)." << std::endl;
    return 0; // Success
}

// Function to delete media file
int delete_media_file(const char* filepath) {
    std::string path = filepath;
    if (remove(path.c_str()) != 0) {
        std::cerr << "C++: Error: Could not delete file: " << path << std::endl;
        return -1; // Error
    }
    std::cout << "C++: File successfully deleted: " << path << std::endl;
    return 0; // Success
}


// New: Function to archive segments as tar.gz
int archive_segments(const char* output_tar_gz_path, const char* temp_dir, const char* manifest_path) {
    std::string output_path = output_tar_gz_path;
    std::string temp_directory = temp_dir;
    std::string manifest = manifest_path;

    // Get only the file name from output path (without extension)
    size_t last_slash_pos = output_path.find_last_of("/\\");
    std::string archive_base_name = output_path.substr(last_slash_pos + 1);
    size_t dot_pos = archive_base_name.find_last_of('.');
    if (dot_pos != std::string::npos) {
        archive_base_name = archive_base_name.substr(0, dot_pos);
    }
    // If .media extension exists and not removed, clean it as well
    size_t media_ext_pos = archive_base_name.find(".media");
    if (media_ext_pos != std::string::npos) {
        archive_base_name = archive_base_name.substr(0, media_ext_pos);
    }


    // Add manifest file and all files in temp_dir to tar.gz
    // We adjust paths relative to the archive's root directory.
    std::stringstream tar_cmd_ss;
    tar_cmd_ss << "cd \"" << temp_directory << "\" && tar -czf \"" << output_path << "\" --exclude='.*' *";

    int result = execute_external_command(tar_cmd_ss.str());
    if (result != 0) {
        std::cerr << "C++: Error: tar/gzip command failed while archiving segments." << std::endl;
        return -1;
    }
    std::cout << "C++: Segments successfully archived: " << output_path << std::endl;
    return 0;
}

// New: Function to extract files from tar.gz archive
int extract_segments(const char* input_tar_gz_path, const char* output_dir) {
    std::string input_path = input_tar_gz_path;
    std::string output_directory = output_dir;

    // Extract tar.gz file to the specified directory
    // tar -xzf [input_tar_gz_path] -C [output_dir]
    std::stringstream tar_cmd_ss;
    tar_cmd_ss << "tar -xzf \"" << input_path << "\" -C \"" << output_directory << "\"";

    int result = execute_external_command(tar_cmd_ss.str());
    if (result != 0) {
        std::cerr << "C++: Error: tar/gzip command failed while extracting segments." << std::endl;
        return -1;
    }
    std::cout << "C++: Segments successfully extracted: " << output_directory << std::endl;
    return 0;
}

// Updated: Function to merge segments into a single video file
// output_filepath: Path of the output video file (e.g., /path/to/output.mp4)
// temp_dir: Temporary directory containing the manifest file and media files to be merged
// video_manifest_filename: Name of the manifest file containing the list of video files to be merged
// audio_manifest_filename: Name of the manifest file containing the list of audio files to be merged
int merge_timeline_to_video(const char* output_filepath, const char* temp_dir, const char* video_manifest_filename, const char* audio_manifest_filename) {
    std::string output_path = output_filepath;
    std::string temp_directory = temp_dir;
    std::string video_manifest_file_path = temp_directory + "/" + video_manifest_filename;
    std::string audio_manifest_file_path = temp_directory + "/" + audio_manifest_filename;

    bool has_video_manifest = std::ifstream(video_manifest_file_path).good();
    bool has_audio_manifest = std::ifstream(audio_manifest_file_path).good();

    if (!has_video_manifest && !has_audio_manifest) {
        std::cerr << "C++: Error: Video or audio manifest file not found. Cannot merge." << std::endl;
        return -1;
    }

    std::string temp_video_output_path = temp_directory + "/temp_concat_video.mp4";
    std::string temp_audio_output_path = temp_directory + "/temp_concat_audio.aac";

    int result = 0;

    // Step 1: Merge video segments
    if (has_video_manifest) {
        // OPTIMIZATION: Use 'veryfast' preset for video concatenation
        // '-preset veryfast' can be kept for speed, we will look at other settings for precision.
        std::string concat_video_cmd = "ffmpeg -f concat -safe 0 -i \"" + video_manifest_file_path + "\" -c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p -movflags +faststart -y \"" + temp_video_output_path + "\"";
        std::cout << "C++: Merging video segments: " << concat_video_cmd << std::endl;
        result = execute_ffmpeg_command(concat_video_cmd);
        if (result != 0) {
            std::cerr << "C++: Error: Failed to merge video segments." << std::endl;
            return -2;
        }
    }

    // Step 2: Merge audio segments
    if (has_audio_manifest) {
        std::string concat_audio_cmd = "ffmpeg -f concat -safe 0 -i \"" + audio_manifest_file_path + "\" -c:a aac -b:a 128k -y \"" + temp_audio_output_path + "\"";
        std::cout << "C++: Merging audio segments: " << concat_audio_cmd << std::endl;
        result = execute_ffmpeg_command(concat_audio_cmd);
        if (result != 0) {
            std::cerr << "C++: Error: Failed to merge audio segments." << std::endl;
            if (has_video_manifest && std::ifstream(temp_video_output_path).good()) {
                remove(temp_video_output_path.c_str());
            }
            return -3;
        }
    }

    // Step 3: Merge combined video and audio (if both exist)
    std::string final_merge_cmd = "ffmpeg";
    if (has_video_manifest && has_audio_manifest) {
        final_merge_cmd += " -i \"" + temp_video_output_path + "\" -i \"" + temp_audio_output_path + "\"";
        // The `-shortest` flag truncates the output to the duration of the shortest stream.
        // This can improve synchronization if one stream is slightly longer than the other.
        final_merge_cmd += " -c:v copy -c:a copy -map 0:v:0 -map 1:a:0 -map_metadata 0 -movflags +faststart -shortest -y \"" + output_path + "\"";
    } else if (has_video_manifest) { // If only video exists
        final_merge_cmd += " -i \"" + temp_video_output_path + "\"";
        final_merge_cmd += " -c:v copy -map_metadata 0 -movflags +faststart -y \"" + output_path + "\"";
    } else if (has_audio_manifest) { // If only audio exists, but user requested video. Create a blank video stream and merge with audio.
        long long audio_duration_ms = get_media_duration_ms(temp_audio_output_path.c_str());
        if (audio_duration_ms == -1) {
            std::cerr << "C++: Error: Could not get audio duration. Blank video could not be created." << std::endl;
            if (has_audio_manifest && std::ifstream(temp_audio_output_path).good()) {
                remove(temp_audio_output_path.c_str());
            }
            return -4;
        }
        // Use 'ultrafast' preset when creating blank video stream as well
        final_merge_cmd += " -f lavfi -i color=c=black:s=1280x720:d="; // Default resolution 1280x720
        final_merge_cmd += std::to_string(static_cast<double>(audio_duration_ms) / 1000.0); // Pass in seconds
        final_merge_cmd += " -i \"" + temp_audio_output_path + "\"";
        final_merge_cmd += " -c:v libx264 -preset ultrafast -crf 23 -c:a copy -map 0:v:0 -map 1:a:0 -map_metadata 0 -movflags +faststart -shortest -y \"" + output_path + "\""; // -shortest added
    } else {
        std::cerr << "C++: Error: No media stream to merge." << std::endl;
        return -5;
    }

    std::cout << "C++: Running final video and audio merge command: " << final_merge_cmd << std::endl;
    result = execute_ffmpeg_command(final_merge_cmd);

    // Clean up temporary files
    if (has_video_manifest && std::ifstream(temp_video_output_path).good()) {
        remove(temp_video_output_path.c_str());
    }
    if (has_audio_manifest && std::ifstream(temp_audio_output_path).good()) {
        remove(temp_audio_output_path.c_str());
    }

    if (result != 0) {
        std::cerr << "C++: Error: Final merge stage failed." << std::endl;
        return -6;
    }

    std::cout << "C++: Segments successfully merged into single video file: " << output_path << std::endl;
    return 0;
}

// New: Function to initialize Lua engine
int init_lua_engine() {
    L = luaL_newstate(); // Create a new Lua state
    if (L == nullptr) {
        std::cerr << "C++: Could not create Lua state!" << std::endl;
        return -1;
    }
    luaL_openlibs(L); // Open standard Lua libraries

    // Load Lua script (expected to be in the same directory as libmediaengine.so)
    if (luaL_dofile(L, "timeline_logic.lua") != LUA_OK) {
        std::cerr << "C++: Error loading Lua script: " << lua_tostring(L, -1) << std::endl;
        lua_pop(L, 1); // Remove error from stack
        lua_close(L);
        L = nullptr;
        return -2;
    }
    std::cout << "C++: Lua script successfully loaded: timeline_logic.lua" << std::endl;
    return 0;
}

// New: Example C++ function calling a Lua function
// Can be called by Python and uses the calculate_segment_position function in Lua
double call_lua_segment_calculation(double start_time_ms, double timeline_width, double total_timeline_duration_ms) {
    if (L == nullptr) {
        std::cerr << "C++: Lua state not initialized!" << std::endl;
        return -1.0; // Return -1 on error
    }

    lua_getglobal(L, "calculate_segment_position"); // Push Lua function to stack
    if (!lua_isfunction(L, -1)) {
        std::cerr << "C++: Lua function 'calculate_segment_position' not found or is not a function!" << std::endl;
        lua_pop(L, 1); // Remove wrong value from stack
        return -1.0;
    }

    // Push parameters to stack
    lua_pushnumber(L, start_time_ms);
    lua_pushnumber(L, timeline_width);
    lua_pushnumber(L, total_timeline_duration_ms);

    // Call function with 3 arguments, expect 1 return value
    if (lua_pcall(L, 3, 1, 0) != LUA_OK) {
        std::cerr << "C++: Error calling Lua function: " << lua_tostring(L, -1) << std::endl;
        lua_pop(L, 1); // Remove error from stack
        return -1.0;
    }

    // Get return value
    double result = lua_tonumber(L, -1);
    lua_pop(L, 1); // Remove return value from stack
    return result;
}

// New: Function to close Lua state
void close_lua_engine() {
    if (L != nullptr) {
        lua_close(L);
        L = nullptr;
        std::cout << "C++: Lua state closed." << std::endl;
    }
}

} // extern "C"


