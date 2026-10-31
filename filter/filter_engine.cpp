/*
 * Kavram Pro v5.3 - C++ Native DSP Engine
 * High-Performance Audio Filtering Shared Library
 */

#include <iostream>
#include <vector>
#include <complex>
#include <cmath>
#include <algorithm>
#include <cstring>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

typedef void (*ProgressCallback)(int);

// ==========================================
// RADIX-2 FFT / IFFT IMPLEMENTATION
// ==========================================
void fft_radix2(std::vector<std::complex<float>>& x) {
    size_t N = x.size();
    if (N <= 1) return;

    size_t j = 0;
    for (size_t i = 0; i < N; ++i) {
        if (i < j) std::swap(x[i], x[j]);
        size_t bit = N >> 1;
        while (j & bit) {
            j ^= bit;
            bit >>= 1;
        }
        j ^= bit;
    }

    for (size_t len = 2; len <= N; len <<= 1) {
        float angle = -2.0f * (float)M_PI / len;
        std::complex<float> wlen(std::cos(angle), std::sin(angle));
        for (size_t i = 0; i < N; i += len) {
            std::complex<float> w(1.0f, 0.0f);
            for (size_t k = 0; k < len / 2; ++k) {
                std::complex<float> u = x[i + k];
                std::complex<float> v = x[i + k + len / 2] * w;
                x[i + k] = u + v;
                x[i + k + len / 2] = u - v;
                w *= wlen;
            }
        }
    }
}

void ifft_radix2(std::vector<std::complex<float>>& x) {
    size_t N = x.size();
    for (size_t i = 0; i < N; ++i) {
        x[i] = std::conj(x[i]);
    }
    fft_radix2(x);
    for (size_t i = 0; i < N; ++i) {
        x[i] = std::conj(x[i]) / static_cast<float>(N);
    }
}

// ==========================================
// STFT / ISTFT DSP HELPER CLASS
// ==========================================
class STFTProcessor {
public:
    int n_fft;
    int hop_length;
    std::vector<float> window;

    STFTProcessor(int n_fft_ = 2048, int hop_length_ = 512) 
        : n_fft(n_fft_), hop_length(hop_length_) {
        window.resize(n_fft);
        for (int i = 0; i < n_fft; ++i) {
            window[i] = 0.5f * (1.0f - std::cos(2.0f * (float)M_PI * i / (float)n_fft));
        }
    }

    void stft(const std::vector<float>& input, 
              std::vector<std::vector<std::complex<float>>>& stft_matrix) {
        int n_frames = (input.size() - n_fft) / hop_length + 1;
        if (n_frames <= 0) return;

        stft_matrix.resize(n_frames, std::vector<std::complex<float>>(n_fft / 2 + 1));
        std::vector<std::complex<float>> frame_buf(n_fft);

        for (int f = 0; f < n_frames; ++f) {
            int start = f * hop_length;
            for (int i = 0; i < n_fft; ++i) {
                frame_buf[i] = input[start + i] * window[i];
            }
            fft_radix2(frame_buf);
            for (int k = 0; k <= n_fft / 2; ++k) {
                stft_matrix[f][k] = frame_buf[k];
            }
        }
    }

    void istft(const std::vector<std::vector<std::complex<float>>>& stft_matrix, 
               std::vector<float>& output, int target_len) {
        int n_frames = stft_matrix.size();
        output.assign(target_len, 0.0f);
        std::vector<float> window_sum(target_len, 0.0f);

        std::vector<std::complex<float>> frame_buf(n_fft);

        for (int f = 0; f < n_frames; ++f) {
            for (int k = 0; k <= n_fft / 2; ++k) {
                frame_buf[k] = stft_matrix[f][k];
            }
            for (int k = n_fft / 2 + 1; k < n_fft; ++k) {
                frame_buf[k] = std::conj(stft_matrix[f][n_fft - k]);
            }

            ifft_radix2(frame_buf);

            int start = f * hop_length;
            for (int i = 0; i < n_fft; ++i) {
                if (start + i < target_len) {
                    output[start + i] += frame_buf[i].real() * window[i];
                    window_sum[start + i] += window[i] * window[i];
                }
            }
        }

        // Overlap-Add Normalizasyonu
        for (int i = 0; i < target_len; ++i) {
            if (window_sum[i] > 1e-6f) {
                output[i] /= window_sum[i];
            }
        }
    }
};

// ==========================================
// EXPORTED C-API FUNCTIONS FOR PYTHON CTYPES
// ==========================================
extern "C" {

void process_x1_cpp(float* audio_in, float* audio_out, int length, int sample_rate, int power, ProgressCallback cb) {
    if (length <= 2048) {
        std::memcpy(audio_out, audio_in, length * sizeof(float));
        if (cb) cb(100);
        return;
    }

    STFTProcessor dsp(2048, 512);
    std::vector<float> input(audio_in, audio_in + length);
    std::vector<std::vector<std::complex<float>>> stft_mat;

    if (cb) cb(10);
    dsp.stft(input, stft_mat);
    if (cb) cb(30);

    int n_frames = stft_mat.size();
    int n_bins = dsp.n_fft / 2 + 1;

    float alpha = 1.2f + (power - 1) * 0.2f;
    float beta = 0.05f + (power - 1) * 0.02f;

    // Spektral Gürültü Kestirimi
    std::vector<float> noise_est(n_bins, 0.0f);
    for (int k = 0; k < n_bins; ++k) {
        std::vector<float> mags(n_frames);
        for (int f = 0; f < n_frames; ++f) {
            mags[f] = std::abs(stft_mat[f][k]);
        }
        std::sort(mags.begin(), mags.end());
        noise_est[k] = mags[n_frames / 2];
    }

    if (cb) cb(50);

    for (int f = 0; f < n_frames; ++f) {
        for (int k = 0; k < n_bins; ++k) {
            float mag = std::abs(stft_mat[f][k]);
            float clean_mag = mag - alpha * noise_est[k];
            if (clean_mag < beta * mag) clean_mag = beta * mag;
            
            float phase = std::arg(stft_mat[f][k]);
            stft_mat[f][k] = std::complex<float>(clean_mag * std::cos(phase), clean_mag * std::sin(phase));
        }
    }

    if (cb) cb(80);

    std::vector<float> stage1_out;
    dsp.istft(stft_mat, stage1_out, length);

    float max_val = 0.0f;
    for (int i = 0; i < length; ++i) {
        float abs_v = std::abs(stage1_out[i]);
        if (abs_v > max_val) max_val = abs_v;
    }

    if (max_val > 0.95f) {
        for (int i = 0; i < length; ++i) {
            audio_out[i] = stage1_out[i] * 0.95f / max_val;
        }
    } else {
        std::memcpy(audio_out, stage1_out.data(), length * sizeof(float));
    }

    if (cb) cb(100);
}

void process_x2_cpp(float* audio_in, float* audio_out, int length, int sample_rate, float cutoff_freq, ProgressCallback cb) {
    if (length <= 2048) {
        std::memcpy(audio_out, audio_in, length * sizeof(float));
        if (cb) cb(100);
        return;
    }

    STFTProcessor dsp(2048, 512);
    std::vector<float> input(audio_in, audio_in + length);
    std::vector<std::vector<std::complex<float>>> stft_mat;

    if (cb) cb(15);
    dsp.stft(input, stft_mat);
    if (cb) cb(40);

    int n_frames = stft_mat.size();
    int n_bins = dsp.n_fft / 2 + 1;
    float freq_bin_hz = (float)sample_rate / (float)dsp.n_fft;

    std::vector<float> frame_rms(n_frames, 0.0f);
    std::vector<float> low_energy(n_frames, 0.0f);
    std::vector<float> high_energy(n_frames, 0.0f);

    float max_rms = 0.0f;

    for (int f = 0; f < n_frames; ++f) {
        float sum_sq = 0.0f;
        for (int k = 0; k < n_bins; ++k) {
            float mag = std::abs(stft_mat[f][k]);
            sum_sq += mag * mag;
            float freq = k * freq_bin_hz;
            if (freq <= cutoff_freq) {
                low_energy[f] += mag;
            } else {
                high_energy[f] += mag;
            }
        }
        frame_rms[f] = std::sqrt(sum_sq / n_bins);
        if (frame_rms[f] > max_rms) max_rms = frame_rms[f];
    }

    if (cb) cb(60);

    std::vector<float> sorted_rms = frame_rms;
    std::sort(sorted_rms.begin(), sorted_rms.end());
    int noise_idx = std::max(1, (int)(n_frames * 0.20f));
    float noise_floor = 0.0f;
    for (int i = 0; i < noise_idx; ++i) noise_floor += sorted_rms[i];
    noise_floor /= noise_idx;

    float sensitivity_multiplier = cutoff_freq / 20.0f;
    float volume_threshold = noise_floor * sensitivity_multiplier;

    std::vector<float> gain_mask(n_frames, 1.0f);
    for (int f = 0; f < n_frames; ++f) {
        bool is_noise_only = frame_rms[f] <= volume_threshold;
        bool is_low_dominant = low_energy[f] > (high_energy[f] * 2.0f);
        bool is_not_speech = frame_rms[f] < (max_rms * 0.20f);

        if (is_noise_only || (is_low_dominant && is_not_speech)) {
            gain_mask[f] = 0.0f;
        }
    }

    std::vector<float> smooth_gain(n_frames, 1.0f);
    for (int f = 1; f < n_frames - 1; ++f) {
        smooth_gain[f] = 0.25f * gain_mask[f - 1] + 0.5f * gain_mask[f] + 0.25f * gain_mask[f + 1];
    }

    if (cb) cb(80);

    for (int f = 0; f < n_frames; ++f) {
        float g = smooth_gain[f];
        for (int k = 0; k < n_bins; ++k) {
            stft_mat[f][k] *= g;
        }
    }

    std::vector<float> out_vec;
    dsp.istft(stft_mat, out_vec, length);
    std::memcpy(audio_out, out_vec.data(), length * sizeof(float));

    if (cb) cb(100);
}

void process_spectral_subtraction_cpp(float* audio_in, float* audio_out, int length, int sample_rate, 
                                       float* noise_profile, int profile_bins, float alpha, float beta, ProgressCallback cb) {
    if (length <= 2048) {
        std::memcpy(audio_out, audio_in, length * sizeof(float));
        if (cb) cb(100);
        return;
    }

    STFTProcessor dsp(2048, 512);
    std::vector<float> input(audio_in, audio_in + length);
    std::vector<std::vector<std::complex<float>>> stft_mat;

    if (cb) cb(20);
    dsp.stft(input, stft_mat);
    if (cb) cb(50);

    int n_frames = stft_mat.size();
    int n_bins = dsp.n_fft / 2 + 1;

    for (int f = 0; f < n_frames; ++f) {
        for (int k = 0; k < n_bins; ++k) {
            float mag = std::abs(stft_mat[f][k]);
            float noise_p = (k < profile_bins) ? noise_profile[k] : 0.0f;
            
            float mag_sq = mag * mag;
            float sub_sq = mag_sq - alpha * (noise_p * noise_p);
            if (sub_sq < beta * (noise_p * noise_p)) {
                sub_sq = beta * (noise_p * noise_p);
            }
            
            float clean_mag = std::sqrt(sub_sq);
            float phase = std::arg(stft_mat[f][k]);
            stft_mat[f][k] = std::complex<float>(clean_mag * std::cos(phase), clean_mag * std::sin(phase));
        }
    }

    if (cb) cb(85);
    std::vector<float> out_vec;
    dsp.istft(stft_mat, out_vec, length);
    std::memcpy(audio_out, out_vec.data(), length * sizeof(float));

    if (cb) cb(100);
}

} // extern "C"