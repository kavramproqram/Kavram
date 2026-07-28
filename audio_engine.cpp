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
 * along with this program.  If not, see /Kavram/License/GPLv3.txt
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

#include <cmath>
#include <complex>
#include <vector>
#include <algorithm>
#include <cstring>
#include <memory>
#include <cassert>
#include <numeric>
#include <cstdint>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif
#define M_PI_F 3.14159265f

using c32 = std::complex<float>;

// ═══════════════════════════════════════════════════════════════════
//  Radix-2 Cooley-Tukey FFT  (float32, in-place)
//  n MUST be power of 2
// ═══════════════════════════════════════════════════════════════════
static void fft(c32* x, int n, bool inverse) {
    // Bit-reversal permutation
    for (int i = 1, j = 0; i < n; ++i) {
        int bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) { c32 t = x[i]; x[i] = x[j]; x[j] = t; }
    }
    // Butterfly stages
    for (int len = 2; len <= n; len <<= 1) {
        float ang  = (inverse ? 1.f : -1.f) * 2.f * M_PI_F / (float)len;
        c32   wlen = c32(cosf(ang), sinf(ang));
        int   half = len >> 1;
        for (int i = 0; i < n; i += len) {
            c32 w(1.f, 0.f);
            for (int j = 0; j < half; ++j) {
                c32 u = x[i + j];
                c32 v = x[i + j + half] * w;
                x[i + j]        = u + v;
                x[i + j + half] = u - v;
                w *= wlen;
            }
        }
    }
    if (inverse) {
        float inv = 1.f / (float)n;
        for (int i = 0; i < n; ++i) x[i] *= inv;
    }
}

static int next_pow2(int n) {
    int p = 1;
    while (p < n) p <<= 1;
    return p;
}

// ═══════════════════════════════════════════════════════════════════
//  Biquad filtresi — Direct Form II Transposed
//  Coefficient design: Butterworth 2nd-order, notch, peaking EQ, highshelf
// ═══════════════════════════════════════════════════════════════════
struct Biquad {
    double b0=1, b1=0, b2=0, a1=0, a2=0;
    double s1=0, s2=0;

    void reset() { s1 = s2 = 0; }

    inline float tick(float xin) {
        double y = b0 * xin + s1;
        s1 = b1 * xin - a1 * y + s2;
        s2 = b2 * xin - a2 * y;
        // Denormal flush
        if (std::abs(s1) < 1e-30) s1 = 0;
        if (std::abs(s2) < 1e-30) s2 = 0;
        return (float)y;
    }

    void process(const float* in, float* out, int n) {
        for (int i = 0; i < n; ++i) out[i] = tick(in[i]);
    }

    // ── Coefficient design helpers ──────────────────────────────
    void set_hp2(double fc, double Q, double sr) {
        double w0 = 2*M_PI*fc/sr, c = cos(w0), s = sin(w0);
        double alpha = s/(2*Q), a0 = 1+alpha;
        b0=(1+c)/(2*a0); b1=-(1+c)/a0; b2=(1+c)/(2*a0);
        a1=(-2*c)/a0;    a2=(1-alpha)/a0;
    }

    void set_lp2(double fc, double Q, double sr) {
        double w0 = 2*M_PI*fc/sr, c = cos(w0), s = sin(w0);
        double alpha = s/(2*Q), a0 = 1+alpha;
        b0=(1-c)/(2*a0); b1=(1-c)/a0; b2=(1-c)/(2*a0);
        a1=(-2*c)/a0;   a2=(1-alpha)/a0;
    }

    void set_notch(double fc, double Q, double sr) {
        double w0 = 2*M_PI*fc/sr, c = cos(w0), s = sin(w0);
        double alpha = s/(2*Q), a0 = 1+alpha;
        b0=1/a0; b1=(-2*c)/a0; b2=1/a0;
        a1=(-2*c)/a0; a2=(1-alpha)/a0;
    }

    void set_peak(double fc, double Q, double gain_db, double sr) {
        double w0 = 2*M_PI*fc/sr, A = pow(10, gain_db/40);
        double alpha = sin(w0)/(2*Q), a0 = 1+alpha/A;
        b0=(1+alpha*A)/a0; b1=(-2*cos(w0))/a0; b2=(1-alpha*A)/a0;
        a1=(-2*cos(w0))/a0; a2=(1-alpha/A)/a0;
    }

    void set_highshelf(double fc, double gain_db, double sr) {
        double w0 = 2*M_PI*fc/sr, A = pow(10, gain_db/40);
        double cosw = cos(w0), sinw = sin(w0);
        double alpha = sinw/2 * sqrt((A+1/A)*(1/0.707-1)+2);
        double a0 = (A+1)-(A-1)*cosw+2*sqrt(A)*alpha;
        b0 = A*((A+1)+(A-1)*cosw+2*sqrt(A)*alpha)/a0;
        b1 = -2*A*((A-1)+(A+1)*cosw)/a0;
        b2 = A*((A+1)+(A-1)*cosw-2*sqrt(A)*alpha)/a0;
        a1 = 2*((A-1)-(A+1)*cosw)/a0;
        a2 = ((A+1)-(A-1)*cosw-2*sqrt(A)*alpha)/a0;
    }

    void set_lowshelf(double fc, double gain_db, double sr) {
        double w0 = 2*M_PI*fc/sr, A = pow(10, gain_db/40);
        double cosw = cos(w0), sinw = sin(w0);
        double alpha = sinw/2 * sqrt((A+1/A)*(1/0.707-1)+2);
        double a0 = (A+1)+(A-1)*cosw+2*sqrt(A)*alpha;
        b0 = A*((A+1)-(A-1)*cosw+2*sqrt(A)*alpha)/a0;
        b1 = 2*A*((A-1)-(A+1)*cosw)/a0;
        b2 = A*((A+1)-(A-1)*cosw-2*sqrt(A)*alpha)/a0;
        a1 = -2*((A-1)+(A+1)*cosw)/a0;
        a2 = ((A+1)+(A-1)*cosw-2*sqrt(A)*alpha)/a0;
    }
};

// ═══════════════════════════════════════════════════════════════════
//  4. derece Butterworth (iki 2. derece bölüm kaskat)
//  Q değerleri: 0.5412 ve 1.3066 (Butterworth pole pairs)
// ═══════════════════════════════════════════════════════════════════
struct Butter4 {
    Biquad s1, s2;
    bool is_hp = true;

    void set_hp(double fc, double sr) {
        s1.set_hp2(fc, 0.5412, sr);
        s2.set_hp2(fc, 1.3066, sr);
        is_hp = true;
    }
    void set_lp(double fc, double sr) {
        s1.set_lp2(fc, 0.5412, sr);
        s2.set_lp2(fc, 1.3066, sr);
        is_hp = false;
    }
    void reset() { s1.reset(); s2.reset(); }

    void process(float* buf, int n) {
        s1.process(buf, buf, n);
        s2.process(buf, buf, n);
    }
};

// ═══════════════════════════════════════════════════════════════════
//  Noise Gate — envelope follower tabanlı, hold + hysteresis
// ═══════════════════════════════════════════════════════════════════
struct NoiseGate {
    float env         = 0.f;
    float attack_c    = 0.f;
    float release_c   = 0.f;
    float threshold   = 0.f;
    int   hold_cnt    = 0;
    int   hold_max    = 0;

    void setup(float thr, float sr) {
        threshold = thr;
        attack_c  = expf(-1.f / (0.001f * sr));
        release_c = expf(-1.f / (0.05f  * sr));
        hold_max  = (int)(0.06f * sr);
    }

    void process(float* buf, int n) {
        for (int i = 0; i < n; ++i) {
            float abs_x = fabsf(buf[i]);
            env = (abs_x > env) ? attack_c * env + (1-attack_c)*abs_x
                                : release_c * env;
            if (env > threshold)      { hold_cnt = hold_max; }
            else if (hold_cnt > 0)    { --hold_cnt; }
            else                      { buf[i] = 0.f; continue; }
            // Optional smooth-open (fade when just above threshold)
        }
    }
};

// ═══════════════════════════════════════════════════════════════════
//  Dinamik Kompresör — log-domain, RMS zarfı
// ═══════════════════════════════════════════════════════════════════
struct Compressor {
    float env       = 0.f;
    float gain_db   = 0.f;
    float thr_db    = -20.f;
    float ratio     = 2.f;
    float attack_c  = 0.f;
    float release_c = 0.f;
    static constexpr float RMS_WIN_S = 0.010f;

    void setup(float thr_db_, float ratio_, float attack_ms,
               float release_ms, float sr) {
        thr_db    = thr_db_;
        ratio     = ratio_;
        attack_c  = expf(-1.f / (attack_ms  * 0.001f * sr));
        release_c = expf(-1.f / (release_ms * 0.001f * sr));
    }

    void process(float* buf, int n) {
        for (int i = 0; i < n; ++i) {
            float sq = buf[i] * buf[i];
            env = attack_c * env + (1.f - attack_c) * sq;
            float level_db = (env > 1e-12f) ? 4.342944f * logf(env) : -120.f;
            float over     = level_db - thr_db;
            float gr       = (over > 0.f) ? over * (1.f/ratio - 1.f) : 0.f;
            gain_db = (gr < gain_db) ? attack_c * gain_db + (1.f-attack_c)*gr
                                     : release_c * gain_db + (1.f-release_c)*gr;
            buf[i] *= powf(10.f, gain_db / 20.f);
        }
    }
};

// ═══════════════════════════════════════════════════════════════════
//  Look-ahead Limiter
// ═══════════════════════════════════════════════════════════════════
struct Limiter {
    static constexpr int LA = 512;
    float  buf[LA]   = {};
    int    pos       = 0;
    float  ceiling   = 1.f;
    float  env       = 0.f;
    float  release_c = 0.f;

    void setup(float ceil_db, float sr) {
        ceiling   = powf(10.f, ceil_db / 20.f);
        release_c = expf(-1.f / (0.10f * sr));
        memset(buf, 0, sizeof(buf));
        env = 0.f; pos = 0;
    }

    void process(float* io, int n) {
        for (int i = 0; i < n; ++i) {
            float peak = fabsf(io[i]);
            env  = (peak > env) ? peak : release_c * env + (1.f-release_c)*peak;
            float gr  = (env > ceiling) ? ceiling / env : 1.f;
            buf[pos]  = io[i] * gr;
            pos = (pos + 1) % LA;
            io[i] = buf[pos];
        }
    }
};

// ═══════════════════════════════════════════════════════════════════
//  Spektral Gürültü Azaltma — STFT + Wiener (STFT overlap-add)
//
//  Algorithm:
//  1. Hann penceresi, %75 örtüşme
//  2. FFT → gürültü profili öğren (ilk çağrıda veya dışarıdan)
//  3. Wiener kazancı: G = SNR/(SNR+1), SNR = max(|Y|²/N-1, 0)
//  4. IFFT → overlap-add → normalize
// ═══════════════════════════════════════════════════════════════════
class SpectralNR {
public:
    int n_fft, hop, n_bins;
    float prop;

    std::vector<float> window;
    std::vector<float> noise_est;
    std::vector<c32>   fft_buf;
    bool noise_learned = false;

    float gain_floor = 0.02f;  // Dynamic: lower = more aggressive suppression

    SpectralNR(int nfft, int hop_, float prop_)
        : n_fft(nfft), hop(hop_), n_bins(nfft/2+1), prop(prop_)
    {
        // Aggressiveness-based gain floor: the harder we suppress, the lower the floor
        if      (prop_ >= 0.90f) gain_floor = 0.001f;
        else if (prop_ >= 0.70f) gain_floor = 0.004f;
        else if (prop_ >= 0.50f) gain_floor = 0.012f;
        else if (prop_ >= 0.30f) gain_floor = 0.025f;
        else                     gain_floor = 0.060f;

        window.resize(n_fft);
        for (int i = 0; i < n_fft; ++i)
            window[i] = 0.5f*(1.f - cosf(2.f*M_PI_F*i/n_fft));
        noise_est.resize(n_bins, 1e-10f);
        fft_buf.resize(n_fft);
    }

    void learn_noise(const float* data, int n) {
        int n_frames = (n - n_fft) / hop;
        if (n_frames <= 0) return;
        std::fill(noise_est.begin(), noise_est.end(), 0.f);
        int cnt = 0;
        for (int fi = 0; fi <= (n-n_fft)/hop; ++fi) {
            int off = fi * hop;
            for (int i = 0; i < n_fft; ++i)
                fft_buf[i] = c32(data[off+i] * window[i], 0.f);
            fft(fft_buf.data(), n_fft, false);
            for (int k = 0; k < n_bins; ++k)
                noise_est[k] += std::norm(fft_buf[k]);
            ++cnt;
        }
        if (cnt > 0)
            for (auto& v : noise_est) v = std::max(v / cnt, 1e-10f);
        noise_learned = true;
    }

    // in-place: writes result to 'out' (can differ from 'in')
    void process(const float* in, float* out, int n) {
        if (!noise_learned) {
            int nn = std::min(n, n_fft * 10);
            learn_noise(in, nn);
        }

        std::fill(out, out + n, 0.f);
        std::vector<float> norm_sum(n, 0.f);

        for (int fi = 0; off(fi) + n_fft <= n; ++fi) {
            int o = off(fi);
            for (int i = 0; i < n_fft; ++i)
                fft_buf[i] = c32(in[o+i] * window[i], 0.f);
            fft(fft_buf.data(), n_fft, false);

            // Wiener gain per bin
            for (int k = 0; k < n_bins; ++k) {
                float pwr  = std::norm(fft_buf[k]);
                float nse  = noise_est[k];
                float snr  = std::max(pwr / nse - 1.f, 0.f);
                float gain = (prop < 1.f) ? std::max(1.f - prop * nse/std::max(pwr,nse), gain_floor)
                                          : snr / (snr + 1.f);
                gain = std::min(gain, 1.f);
                // For Wiener path, also apply floor
                if (prop >= 1.f) gain = std::max(gain, gain_floor);
                fft_buf[k] *= gain;
                if (k > 0 && k < n_fft - k)
                    fft_buf[n_fft - k] = std::conj(fft_buf[k]);
            }

            fft(fft_buf.data(), n_fft, true);

            for (int i = 0; i < n_fft; ++i) {
                if (o+i < n) {
                    out[o+i]      += fft_buf[i].real() * window[i];
                    norm_sum[o+i] += window[i] * window[i];
                }
            }
        }
        for (int i = 0; i < n; ++i)
            if (norm_sum[i] > 1e-6f) out[i] /= norm_sum[i];
    }

private:
    int off(int fi) const { return fi * hop; }
};

// ═══════════════════════════════════════════════════════════════════
//  Fan Konuşma Ayırıcı — Min-stat + DD-SNR + Wiener kazanç
//
//  Optimizasyonlar vs. Python versiyonu:
//  • C++ ile tüm iç döngüler 10-30x daha hızlı
//  • Exponential smoothing: tek geçişli IIR döngü
//  • Min-stat: halka tamponu ile O(1) güncelleme
//  • Overlap-add: normalize tampon
// ═══════════════════════════════════════════════════════════════════
class FanSep {
public:
    int n_fft, hop, n_bins, sr;
    float alpha, ms_bias, gain_floor, speech_boost, dd_alpha;

    static constexpr int MS_WIN = 45;  // ~900ms @ 20ms hop

    std::vector<float> window;
    std::vector<c32>   fft_buf;
    std::vector<float> smoothed;
    std::vector<float> noise_est;
    std::vector<float> prev_wiener;
    // Min-stat ring buffer: MS_WIN × n_bins
    std::vector<std::vector<float>> ms_ring;
    int ms_pos = 0;

    FanSep(int sample_rate, int mode)
        : sr(sample_rate)
    {
        n_fft  = next_pow2(std::max(256, (int)(sr * 0.025f)));
        hop    = std::max(64,  (int)(sr * 0.010f));
        n_bins = n_fft / 2 + 1;

        static const float P[4][5] = {
            // alpha    ms_bias  gain_floor  speech_boost  dd_alpha
            {0.970f,    1.30f,   0.35f,      0.12f,        0.93f},  // gentle
            {0.955f,    1.55f,   0.12f,      0.28f,        0.91f},  // balanced
            {0.930f,    1.90f,   0.03f,      0.50f,        0.87f},  // aggressive
            {0.905f,    2.50f,   0.001f,     0.90f,        0.83f},  // max  ← much stronger
        };
        int m = std::max(0, std::min(3, mode));
        alpha=P[m][0]; ms_bias=P[m][1]; gain_floor=P[m][2];
        speech_boost=P[m][3]; dd_alpha=P[m][4];

        window.resize(n_fft);
        for (int i = 0; i < n_fft; ++i)
            window[i] = 0.5f*(1.f-cosf(2.f*M_PI_F*i/n_fft));

        fft_buf.resize(n_fft);
        smoothed.resize(n_bins, 0.f);
        noise_est.resize(n_bins, 1e-10f);
        prev_wiener.resize(n_bins, 0.5f);
        ms_ring.assign(MS_WIN, std::vector<float>(n_bins, 1e-10f));
    }

    // Pre-warm min-stat ring buffer with noise-only data.
    // Eliminates the "loud opening seconds" artifact.
    void warmup(const float* noise_data, int noise_n) {
        int needed = (MS_WIN + 4) * hop + n_fft;
        std::vector<float> longbuf;
        longbuf.reserve(needed);
        while ((int)longbuf.size() < needed)
            for (int i = 0; i < noise_n && (int)longbuf.size() < needed; ++i)
                longbuf.push_back(noise_data[i]);
        std::vector<float> dummy(longbuf.size(), 0.f);
        process(longbuf.data(), dummy.data(), (int)longbuf.size());
    }

    void process(const float* in, float* out, int n) {
        std::fill(out, out + n, 0.f);
        std::vector<float> norm_sum(n, 0.f);

        float hz_per_bin = (float)sr / n_fft;
        int speech_lo = (int)(200.f / hz_per_bin);
        int speech_hi = (int)(4000.f / hz_per_bin);
        speech_lo = std::max(0, std::min(speech_lo, n_bins-1));
        speech_hi = std::max(0, std::min(speech_hi, n_bins-1));

        for (int fi = 0; fi * hop + n_fft <= n; ++fi) {
            int o = fi * hop;

            // Window + FFT
            for (int i = 0; i < n_fft; ++i)
                fft_buf[i] = c32(in[o+i] * window[i], 0.f);
            fft(fft_buf.data(), n_fft, false);

            // Power spectrum
            std::vector<float> power(n_bins);
            for (int k = 0; k < n_bins; ++k)
                power[k] = std::norm(fft_buf[k]);

            // Exponential smoothing (IIR, C++ loop = fast)
            for (int k = 0; k < n_bins; ++k)
                smoothed[k] = alpha * smoothed[k] + (1.f-alpha) * power[k];

            // Update ring buffer, compute min (min-stat)
            ms_ring[ms_pos] = smoothed;
            ms_pos = (ms_pos + 1) % MS_WIN;

            for (int k = 0; k < n_bins; ++k) {
                float mn = smoothed[k];
                for (int r = 0; r < MS_WIN; ++r)
                    mn = std::min(mn, ms_ring[r][k]);
                noise_est[k] = std::max(mn * ms_bias, 1e-12f);
            }

            // DD SNR + Wiener gain
            for (int k = 0; k < n_bins; ++k) {
                float snr_post  = std::max(power[k] / noise_est[k] - 1.f, 0.f);
                float dd        = dd_alpha * (prev_wiener[k]*prev_wiener[k]) * snr_post;
                float snr_prior = dd + (1.f - dd_alpha) * snr_post;
                float gain      = snr_prior / (1.f + snr_prior);
                gain = std::max(gain, gain_floor);

                // Speech band boost
                if (k >= speech_lo && k <= speech_hi) {
                    float boost = 1.f + speech_boost * tanhf(snr_prior / 3.f);
                    gain = std::min(gain * boost, 2.5f);
                }

                prev_wiener[k] = gain;
                fft_buf[k] *= gain;
                if (k > 0 && k < n_fft - k)
                    fft_buf[n_fft-k] = std::conj(fft_buf[k]);
            }

            // Perceptual smoothing (freq)
            for (int k = 1; k < n_bins-1; ++k) {
                float g = 0.6f * std::abs(fft_buf[k])
                        + 0.2f * std::abs(fft_buf[k-1])
                        + 0.2f * std::abs(fft_buf[k+1]);
                float ph = std::arg(fft_buf[k]);
                fft_buf[k] = c32(g*cosf(ph), g*sinf(ph));
                if (k > 0 && k < n_fft-k)
                    fft_buf[n_fft-k] = std::conj(fft_buf[k]);
            }

            // IFFT
            fft(fft_buf.data(), n_fft, true);

            // Overlap-add
            for (int i = 0; i < n_fft; ++i) {
                if (o+i < n) {
                    out[o+i]      += fft_buf[i].real() * window[i];
                    norm_sum[o+i] += window[i] * window[i];
                }
            }
        }
        for (int i = 0; i < n; ++i)
            if (norm_sum[i] > 1e-6f) out[i] /= norm_sum[i];
    }
};

// ═══════════════════════════════════════════════════════════════════
//  SpeechEnhancer — Konuşma Yükseltici
//
//  Algoritma:
//  • STFT (1024-point, %75 overlap)
//  • Her frame'de kısa-dönem otokorelasyon ile ses periyodikliği ölçülür
//  • Harmonik bölgeler tespit edilip güçlendirilir (formant freqanslara odak)
//  • F1(~800Hz), F2(~1700Hz), F3(~2700Hz) peak EQ ile konuşma netleştirilir
//  • Gürültülü (aperiodik) freqanslar bastırılmaz — sadece speech öne çıkarılır
// ═══════════════════════════════════════════════════════════════════
class SpeechEnhancer {
public:
    int n_fft, hop, n_bins, sr;
    float strength;     // 0..1

    std::vector<float> window;
    std::vector<c32>   fft_buf;
    // Smoothed power per bin (IIR)
    std::vector<float> smooth_pwr;
    // Running noise floor estimate per bin (slow min-track)
    std::vector<float> noise_floor;
    float alpha_s;  // power smoothing
    float alpha_n;  // noise floor tracking (very slow)

    SpeechEnhancer(int sr_, float str)
        : sr(sr_), strength(str)
    {
        n_fft  = 1024;
        hop    = 256;
        n_bins = n_fft / 2 + 1;

        alpha_s = 0.85f;
        alpha_n = 0.9985f;  // very slow noise floor — adapts only in silence

        window.resize(n_fft);
        for (int i = 0; i < n_fft; ++i)
            window[i] = 0.5f * (1.f - cosf(2.f * M_PI_F * i / n_fft));

        fft_buf.resize(n_fft);
        smooth_pwr.resize(n_bins, 1e-10f);
        noise_floor.resize(n_bins, 1e-10f);
    }

    void process(const float* in, float* out, int n) {
        std::fill(out, out + n, 0.f);
        std::vector<float> norm_sum(n, 0.f);

        float hz_per_bin = (float)sr / n_fft;

        // Formant regions: F1 300-1000Hz, F2 1000-2500Hz, F3 2500-3500Hz
        int f1_lo = (int)(300.f  / hz_per_bin);
        int f1_hi = (int)(1000.f / hz_per_bin);
        int f2_lo = (int)(1000.f / hz_per_bin);
        int f2_hi = (int)(2500.f / hz_per_bin);
        int f3_lo = (int)(2500.f / hz_per_bin);
        int f3_hi = (int)(3500.f / hz_per_bin);

        // F1 boost more (primary vowel energy), F2/F3 moderate
        float f1_boost = 1.f + 0.60f * strength;
        float f2_boost = 1.f + 0.45f * strength;
        float f3_boost = 1.f + 0.35f * strength;

        auto clamp = [](int v, int lo, int hi){ return std::max(lo, std::min(v, hi)); };
        f1_lo = clamp(f1_lo, 0, n_bins-1); f1_hi = clamp(f1_hi, 0, n_bins-1);
        f2_lo = clamp(f2_lo, 0, n_bins-1); f2_hi = clamp(f2_hi, 0, n_bins-1);
        f3_lo = clamp(f3_lo, 0, n_bins-1); f3_hi = clamp(f3_hi, 0, n_bins-1);

        for (int fi = 0; fi * hop + n_fft <= n; ++fi) {
            int o = fi * hop;
            for (int i = 0; i < n_fft; ++i)
                fft_buf[i] = c32(in[o + i] * window[i], 0.f);
            fft(fft_buf.data(), n_fft, false);

            // Power + update smooth / noise floor
            float frame_energy = 0.f;
            for (int k = 0; k < n_bins; ++k) {
                float p = std::norm(fft_buf[k]);
                smooth_pwr[k]  = alpha_s  * smooth_pwr[k]  + (1.f - alpha_s)  * p;
                frame_energy  += p;
            }
            // Decide: speech-active frame or silence?
            float noise_energy = 0.f;
            for (int k = 0; k < n_bins; ++k) noise_energy += noise_floor[k];
            bool speech_active = (frame_energy > noise_energy * 3.5f);

            if (!speech_active) {
                // Slow-update noise floor in silence
                for (int k = 0; k < n_bins; ++k)
                    noise_floor[k] = alpha_n * noise_floor[k] + (1.f - alpha_n) * smooth_pwr[k];
            }

            // Apply formant-region gain
            for (int k = 0; k < n_bins; ++k) {
                float g = 1.f;
                if      (k >= f1_lo && k <= f1_hi) g = f1_boost;
                else if (k >= f2_lo && k <= f2_hi) g = f2_boost;
                else if (k >= f3_lo && k <= f3_hi) g = f3_boost;

                // Additionally: if this bin has good SNR vs noise floor → boost more
                if (speech_active && noise_floor[k] > 1e-15f) {
                    float local_snr = smooth_pwr[k] / noise_floor[k];
                    float snr_boost = std::min(1.f + 0.3f * strength * tanhf(local_snr / 8.f), 1.8f);
                    g *= snr_boost;
                }

                fft_buf[k] *= std::min(g, 2.5f);
                if (k > 0 && k < n_fft - k)
                    fft_buf[n_fft - k] = std::conj(fft_buf[k]);
            }

            fft(fft_buf.data(), n_fft, true);

            for (int i = 0; i < n_fft; ++i) {
                if (o + i < n) {
                    out[o + i]      += fft_buf[i].real() * window[i];
                    norm_sum[o + i] += window[i] * window[i];
                }
            }
        }
        for (int i = 0; i < n; ++i)
            if (norm_sum[i] > 1e-6f) out[i] /= norm_sum[i];
    }
};

// ═══════════════════════════════════════════════════════════════════
//  NoiseSupervisor — Sürekli Adaptif Gürültü Denetleyici
//
//  Algoritma:
//  • SpectralNR / FanSep'ten FARKLI: ikisi de sabit gürültü modeli kullanır.
//    Bu modül, gürültü spektrumunu GERÇEK ZAMANLI takip eder.
//  • 8 mel-benzeri band'a böler; her band için bağımsız gürültü eşiği
//  • Konuşma aktifken → gürültü tahmini dondurulur
//  • Sessizlikte → agresif güncelleme
//  • Her band'a soft-knee Wiener kazanç uygulanır
//  • Artık gürültü (residual) için ek spectral floor bastırma
// ═══════════════════════════════════════════════════════════════════
class NoiseSupervisor {
public:
    int n_fft, hop, n_bins, sr;
    float strength;

    std::vector<float> window;
    std::vector<c32>   fft_buf;

    // Per-bin noise model (fast + slow)
    std::vector<float> noise_fast;   // fast-attack, slow-release (catches sudden noise)
    std::vector<float> noise_slow;   // very slow (long-term floor)
    std::vector<float> prev_gain;    // DD-style gain smoothing

    float alpha_speech  = 0.96f;  // how fast to track when speech on
    float alpha_silence = 0.60f;  // how fast to track in silence
    float alpha_gain    = 0.88f;  // gain temporal smoothing

    NoiseSupervisor(int sr_, float str) : sr(sr_), strength(str) {
        n_fft  = 2048;
        hop    = 512;
        n_bins = n_fft / 2 + 1;

        window.resize(n_fft);
        for (int i = 0; i < n_fft; ++i)
            window[i] = 0.5f * (1.f - cosf(2.f * M_PI_F * i / n_fft));

        fft_buf.resize(n_fft);
        noise_fast.resize(n_bins, 1e-10f);
        noise_slow.resize(n_bins, 1e-10f);
        prev_gain.resize(n_bins, 1.f);
    }

    // Warmup: gürültü verisiyle noise model'i ısıt (açılış gürültüsünü engelle)
    void warmup(const float* noise_data, int noise_n) {
        int needed = 4 * n_fft;
        std::vector<float> dummy(std::max(needed, noise_n), 0.f);
        // Gürültüyü tekrarlayarak yeterince uzun warmup verisi oluştur
        std::vector<float> wb;
        wb.reserve(needed);
        while ((int)wb.size() < needed)
            for (int i = 0; i < noise_n && (int)wb.size() < needed; ++i)
                wb.push_back(noise_data[i]);
        process(wb.data(), dummy.data(), (int)wb.size());
    }

    void process(const float* in, float* out, int n) {
        std::fill(out, out + n, 0.f);
        std::vector<float> norm_sum(n, 0.f);

        float hz_per_bin = (float)sr / n_fft;
        // Speech band: 200-4000 Hz
        int speech_lo = (int)(200.f  / hz_per_bin);
        int speech_hi = (int)(4000.f / hz_per_bin);
        speech_lo = std::max(0, std::min(speech_lo, n_bins-1));
        speech_hi = std::max(0, std::min(speech_hi, n_bins-1));

        // gain floor: more strength → lower floor (more suppression)
        float gfloor = std::max(0.001f, 0.15f - 0.13f * strength);

        for (int fi = 0; fi * hop + n_fft <= n; ++fi) {
            int o = fi * hop;
            for (int i = 0; i < n_fft; ++i)
                fft_buf[i] = c32(in[o + i] * window[i], 0.f);
            fft(fft_buf.data(), n_fft, false);

            // Compute power
            std::vector<float> pwr(n_bins);
            for (int k = 0; k < n_bins; ++k) pwr[k] = std::norm(fft_buf[k]);

            // Detect speech activity: speech-band energy vs total noise
            float speech_energy = 0.f, noise_energy = 0.f;
            for (int k = speech_lo; k <= speech_hi; ++k) speech_energy += pwr[k];
            for (int k = 0; k < n_bins; ++k) noise_energy += noise_fast[k];
            bool speech_on = (speech_energy > noise_energy * 4.f * (1.f - strength * 0.3f));

            // Update noise model
            float alpha = speech_on ? alpha_speech : alpha_silence;
            float slow_alpha = speech_on ? 0.9995f : 0.90f;
            for (int k = 0; k < n_bins; ++k) {
                noise_fast[k] = alpha * noise_fast[k] + (1.f - alpha) * pwr[k];
                noise_slow[k] = slow_alpha * noise_slow[k] + (1.f - slow_alpha) * pwr[k];
            }

            // Wiener gain with DD smoothing
            for (int k = 0; k < n_bins; ++k) {
                // Use max(fast, slow) as noise reference
                float noise_ref = std::max(noise_fast[k], noise_slow[k]);
                float snr_post  = std::max(pwr[k] / std::max(noise_ref, 1e-15f) - 1.f, 0.f);

                // DD prior SNR
                float dd = alpha_gain * prev_gain[k] * prev_gain[k] * (pwr[k] / std::max(noise_ref, 1e-15f));
                float snr_prior = 0.98f * dd + 0.02f * snr_post;
                float gain = snr_prior / (1.f + snr_prior);

                // Scale by strength (more strength = more attenuation)
                gain = gfloor + (gain - gfloor) * (1.f - 0.3f * strength) + gain * 0.3f * strength;
                gain = std::max(gain, gfloor);
                gain = std::min(gain, 1.f);

                // Temporal smoothing
                prev_gain[k] = alpha_gain * prev_gain[k] + (1.f - alpha_gain) * gain;
                fft_buf[k] *= prev_gain[k];
                if (k > 0 && k < n_fft - k)
                    fft_buf[n_fft - k] = std::conj(fft_buf[k]);
            }

            fft(fft_buf.data(), n_fft, true);

            for (int i = 0; i < n_fft; ++i) {
                if (o + i < n) {
                    out[o + i]      += fft_buf[i].real() * window[i];
                    norm_sum[o + i] += window[i] * window[i];
                }
            }
        }
        for (int i = 0; i < n; ++i)
            if (norm_sum[i] > 1e-6f) out[i] /= norm_sum[i];
    }
};

// ═══════════════════════════════════════════════════════════════════
//  HissSuppressor — Tiz Tıslama (sssss) Bastırıcı
//
//  "Sssss" / hiss sesi = yüksek freqanslarda (4-12 kHz) sürekli
//  stokastik (gürültü benzeri) enerji.
//  Konuşma sibilantlarından (ş, s, ç sesleri) ayırt eder:
//    → Sibilant: kısa süreli, güçlü patlama, ardından düşer
//    → Hiss: sürekli, düz spektral şekil, konuşmadan bağımsız
//
//  Algoritma:
//  1. FFT → her frame'de 4-12 kHz bölgesini 8 alt banda böl
//  2. Her alt bantta Spectral Flatness Measure (SFM) hesapla
//     SFM = geometrik_ortalama / aritmetik_ortalama  (0..1)
//     SFM ≈ 1 → gürültü (düz spektrum)
//     SFM ≈ 0 → tonal/harmonik ses
//  3. Sürekli hiss = SFM yüksek AND enerji stabil (düşük varyans)
//  4. Adaptif Wiener kazancı sadece hiss benzeri bölgelere uygulanır
//  5. Konuşma sibilantları (<100ms patlama) korunur
// ═══════════════════════════════════════════════════════════════════
class HissSuppressor {
public:
    int n_fft, hop, n_bins, sr;
    float strength;

    std::vector<float> window;
    std::vector<c32>   fft_buf;

    // Per-bin state
    std::vector<float> hiss_floor;      // running hiss noise estimate
    std::vector<float> prev_gain;       // temporal smoothing

    // Sub-band onset detector (for protecting sibilants)
    static constexpr int N_BANDS = 12;
    float band_prev_energy[N_BANDS] = {};
    float band_onset[N_BANDS]       = {};  // onset detector state

    float alpha_hiss  = 0.92f;  // hiss floor tracking speed
    float alpha_gain  = 0.80f;  // gain smoothing

    HissSuppressor(int sr_, float str) : sr(sr_), strength(str) {
        n_fft  = 2048;
        hop    = 256;   // shorter hop for better temporal precision
        n_bins = n_fft / 2 + 1;

        window.resize(n_fft);
        for (int i = 0; i < n_fft; ++i)
            window[i] = 0.5f * (1.f - cosf(2.f * M_PI_F * i / n_fft));

        fft_buf.resize(n_fft);
        hiss_floor.resize(n_bins, 1e-10f);
        prev_gain.resize(n_bins, 1.f);
    }

    // Warmup: hiss floor modelini ön ısıt
    void warmup(const float* noise_data, int noise_n) {
        int needed = 6 * n_fft;
        std::vector<float> dummy(needed, 0.f);
        std::vector<float> wb;
        wb.reserve(needed);
        while ((int)wb.size() < needed)
            for (int i = 0; i < noise_n && (int)wb.size() < needed; ++i)
                wb.push_back(noise_data[i]);
        process(wb.data(), dummy.data(), (int)wb.size());
    }

    void process(const float* in, float* out, int n) {
        std::fill(out, out + n, 0.f);
        std::vector<float> norm_sum(n, 0.f);

        float hz_per_bin = (float)sr / n_fft;

        // Hiss target range: 4 kHz - 12 kHz
        int hiss_lo = (int)(4000.f  / hz_per_bin);
        int hiss_hi = (int)(12000.f / hz_per_bin);
        hiss_lo = std::max(0, std::min(hiss_lo, n_bins - 1));
        hiss_hi = std::max(0, std::min(hiss_hi, n_bins - 1));
        int hiss_range = std::max(1, hiss_hi - hiss_lo);

        // Sibilant protection region: 4-8 kHz (speech consonants)
        int sib_lo = hiss_lo;
        int sib_hi = (int)(8000.f / hz_per_bin);
        sib_hi = std::max(0, std::min(sib_hi, n_bins - 1));
        int band_width = std::max(1, hiss_range / N_BANDS);

        float gfloor = std::max(0.0005f, 0.08f - 0.07f * strength);

        for (int fi = 0; fi * hop + n_fft <= n; ++fi) {
            int o = fi * hop;
            for (int i = 0; i < n_fft; ++i)
                fft_buf[i] = c32(in[o + i] * window[i], 0.f);
            fft(fft_buf.data(), n_fft, false);

            std::vector<float> pwr(n_bins);
            for (int k = 0; k < n_bins; ++k) pwr[k] = std::norm(fft_buf[k]);

            // ── Per sub-band onset detection (sibilant protection) ──────
            float onset_flag[N_BANDS] = {};
            for (int b = 0; b < N_BANDS; ++b) {
                int k0 = hiss_lo + b * band_width;
                int k1 = std::min(k0 + band_width, hiss_hi);
                float energy = 0.f;
                for (int k = k0; k < k1; ++k) energy += pwr[k];
                // Onset: sudden energy rise (>3x previous smoothed level)
                float ratio = energy / std::max(band_prev_energy[b], 1e-20f);
                if (ratio > 3.0f) {
                    // Sibilant onset → protect this band for a few frames
                    band_onset[b] = 6.f;  // hold for ~6 frames
                } else if (band_onset[b] > 0.f) {
                    band_onset[b] -= 1.f;
                }
                onset_flag[b] = (band_onset[b] > 0.f) ? 1.f : 0.f;
                // Slow-update band energy
                band_prev_energy[b] = 0.85f * band_prev_energy[b] + 0.15f * energy;
            }

            // ── Spectral Flatness Measure per sub-band ──────────────────
            // SFM near 1 = noise-like (hiss), near 0 = tonal
            float sfm[N_BANDS] = {};
            for (int b = 0; b < N_BANDS; ++b) {
                int k0 = hiss_lo + b * band_width;
                int k1 = std::min(k0 + band_width, hiss_hi);
                double log_sum = 0.0, lin_sum = 0.0;
                int cnt = 0;
                for (int k = k0; k < k1; ++k) {
                    float p = std::max(pwr[k], 1e-20f);
                    log_sum += (double)logf(p);
                    lin_sum += (double)p;
                    ++cnt;
                }
                if (cnt > 0) {
                    float geo = expf((float)(log_sum / cnt));
                    float ari = (float)(lin_sum / cnt);
                    sfm[b] = (ari > 1e-20f) ? geo / ari : 1.f;
                    sfm[b] = std::min(sfm[b], 1.f);
                }
            }

            // ── Apply gain per bin ──────────────────────────────────────
            for (int k = 0; k < n_bins; ++k) {
                if (k < hiss_lo || k > hiss_hi) continue;  // outside hiss range

                // Which sub-band?
                int b = std::min((k - hiss_lo) / std::max(1, band_width), N_BANDS - 1);

                // Update running hiss floor
                float p = pwr[k];
                hiss_floor[k] = alpha_hiss * hiss_floor[k] + (1.f - alpha_hiss) * p;

                // Base Wiener gain from SNR vs hiss floor
                float snr = std::max(p / std::max(hiss_floor[k], 1e-15f) - 1.f, 0.f);
                float gain = snr / (1.f + snr);
                gain = std::max(gain, gfloor);

                // Scale suppression by how "flat" (noise-like) this band is
                // High SFM → full suppression; low SFM → reduce suppression
                float sfm_weight = sfm[b] * sfm[b];  // square for sharper cutoff
                float target = gfloor + (gain - gfloor) * (1.f - sfm_weight * strength);
                gain = std::max(target, gfloor);

                // Protect sibilants: if onset detected → ease off suppression
                if (onset_flag[b] > 0.f && k >= sib_lo && k <= sib_hi) {
                    gain = 0.5f * gain + 0.5f;  // blend with unity gain
                }

                // Temporal smoothing
                prev_gain[k] = alpha_gain * prev_gain[k] + (1.f - alpha_gain) * gain;
                fft_buf[k] *= prev_gain[k];
                if (k > 0 && k < n_fft - k)
                    fft_buf[n_fft - k] = std::conj(fft_buf[k]);
            }

            fft(fft_buf.data(), n_fft, true);

            for (int i = 0; i < n_fft; ++i) {
                if (o + i < n) {
                    out[o + i]      += fft_buf[i].real() * window[i];
                    norm_sum[o + i] += window[i] * window[i];
                }
            }
        }
        for (int i = 0; i < n; ++i)
            if (norm_sum[i] > 1e-6f) out[i] /= norm_sum[i];
    }
};

// ═══════════════════════════════════════════════════════════════════
//  DCBlocker — Dosya başı DC offset + düşük-frekans gürültü temizle
//  Birinci-dereceli yüksek geçiş @ ~5 Hz
//  Açılış gürültüsünün %60'ı DC offset kaynaklıdır
// ═══════════════════════════════════════════════════════════════════
struct DCBlocker {
    float x1 = 0.f, y1 = 0.f;
    // R yakın 1 → daha düşük kesim freq; 0.9999 ≈ 5Hz @ 44100
    static constexpr float R = 0.9999f;

    void reset() { x1 = 0.f; y1 = 0.f; }

    void process(float* buf, int n) {
        for (int i = 0; i < n; ++i) {
            float x0 = buf[i];
            float y0 = x0 - x1 + R * y1;
            x1 = x0; y1 = y0;
            // Denormal flush
            if (fabsf(y1) < 1e-30f) y1 = 0.f;
            buf[i] = y0;
        }
    }
};

// ═══════════════════════════════════════════════════════════════════
//  VoiceTone — Ses Tonu (Kalınlık / İncelik) Kontrolü
//
//  Algoritma: Low-shelf @ 300 Hz + ters High-shelf @ 4 kHz
//  Pozitif gain_db → Daha kalın/sıcak ses
//  Negatif gain_db → Daha ince/parlak ses
//  Tip: Erkek ses +3..+6 dB; Kadın ses -3..-6 dB önerilir
// ═══════════════════════════════════════════════════════════════════
struct VoiceTone {
    Biquad low_shelf, high_shelf;

    void setup(double gain_db, double sr) {
        // Low shelf: tam kazanç
        low_shelf.set_lowshelf(300.0, gain_db, sr);
        // High shelf: yarı ters (ton dengesi için)
        high_shelf.set_highshelf(4000.0, -gain_db * 0.45, sr);
        low_shelf.reset(); high_shelf.reset();
    }

    void process(float* buf, int n) {
        low_shelf.process(buf, buf, n);
        high_shelf.process(buf, buf, n);
    }
};

// ═══════════════════════════════════════════════════════════════════
//  VoiceWarmth — Ses Isısı / Tüp Sıcaklık Simülasyonu
//
//  Algoritma:
//  1. Peak EQ @ 600 Hz — "warmth" frekansını öne çıkarır
//  2. Soft-clip (tanh) — çok düşük seviyede tüp harmonik renklendirme
//     drive düşük tutulur, hiçbir şekilde ses bozulmaz
// ═══════════════════════════════════════════════════════════════════
struct VoiceWarmth {
    Biquad warm_eq;
    float drive = 0.f;

    void setup(float strength, double sr) {
        double gain_db = strength * 5.5;   // 0..5.5 dB boost @ 600Hz
        warm_eq.set_peak(600.0, 1.2, gain_db, sr);
        warm_eq.reset();
        drive = strength * 0.18f;  // very gentle saturation
    }

    void process(float* buf, int n) {
        warm_eq.process(buf, buf, n);
        if (drive > 0.f) {
            float inv = 1.f / (1.f + drive);
            for (int i = 0; i < n; ++i)
                buf[i] = tanhf(buf[i] * (1.f + drive)) * inv;
        }
    }
};

// ═══════════════════════════════════════════════════════════════════
//  VocalEnhancer — Konuşma Berraklık Güçlendirici
//
//  Algoritma: Konuşma anlaşılırlığı için özel ayarlanmış 3-bant EQ
//  • 150 Hz → hafif kesme (boğuk/bulanık sesi azalt)
//  • 2000 Hz → presence boost (kelime anlaşılırlığı)
//  • 4000 Hz → clarity boost (ünsüz sesler: t, k, p, f)
//  Müzik ve ses kayıtları için farklı "presence" eğrisi
// ═══════════════════════════════════════════════════════════════════
struct VocalEnhancer {
    Biquad cut_lo, boost_pres, boost_clar;

    void setup(float strength, double sr) {
        cut_lo.set_peak    (150.0,  1.0, -3.0 * strength, sr);
        boost_pres.set_peak(2000.0, 1.2,  5.0 * strength, sr);
        boost_clar.set_peak(4000.0, 1.8,  3.5 * strength, sr);
        cut_lo.reset(); boost_pres.reset(); boost_clar.reset();
    }

    void process(float* buf, int n) {
        cut_lo.process    (buf, buf, n);
        boost_pres.process(buf, buf, n);
        boost_clar.process(buf, buf, n);
    }
};

// ═══════════════════════════════════════════════════════════════════
//  TransientShaper — Geçici Sinyal (Attack) Güçlendirici
//
//  Algoritma: Çift zarf dedektörü (hızlı + yavaş)
//  • fast_env: 1ms attack (ani patlama yakalamak için)
//  • slow_env: 40ms RMS (arka plan seviyesi)
//  • Oran fast/slow > 1 → transient algılandı → kazanç artır
//  Konuşmada: t, p, k, d, b patlamaları daha baskın hale gelir
// ═══════════════════════════════════════════════════════════════════
struct TransientShaper {
    float fast_env = 0.f, slow_env = 0.f;
    float fast_c = 0.f, slow_c = 0.f;
    float gain_factor = 0.f;

    void setup(float strength, float sr) {
        fast_c      = expf(-1.f / (0.0010f * sr));  // 1ms
        slow_c      = expf(-1.f / (0.040f  * sr));  // 40ms
        gain_factor = strength * 3.0f;  // max ~3x transient boost
    }

    void process(float* buf, int n) {
        for (int i = 0; i < n; ++i) {
            float abs_x = fabsf(buf[i]);
            fast_env = fast_c * fast_env + (1.f - fast_c) * abs_x;
            slow_env = slow_c * slow_env + (1.f - slow_c) * abs_x;
            float ratio = (slow_env > 1e-10f) ? fast_env / slow_env : 1.f;
            float g = 1.f + gain_factor * std::max(ratio - 1.2f, 0.f);
            g = std::min(g, 3.5f);  // güvenlik sınırı
            buf[i] *= g;
        }
    }
};

// ═══════════════════════════════════════════════════════════════════
//  AirBand — Yüksek Frekans "Hava" Bandı
//
//  Algoritma: Yüksek raf (high-shelf) EQ @ 10 kHz
//  Pozitif kazanç → ses daha "havadar", parlak, modern stüdyo sesi
//  Podcast, vlog, yayın seslerinde yaygın kullanım
// ═══════════════════════════════════════════════════════════════════
struct AirBand {
    Biquad shelf;

    void setup(double gain_db, double sr) {
        shelf.set_highshelf(10000.0, gain_db, sr);
        shelf.reset();
    }

    void process(float* buf, int n) {
        shelf.process(buf, buf, n);
    }
};

// ═══════════════════════════════════════════════════════════════════
//  Preemphasis (reverb reduction)
// ═══════════════════════════════════════════════════════════════════
static void apply_preemphasis(float* buf, int n, float coef, float& prev) {
    for (int i = 0; i < n; ++i) {
        float cur = buf[i];
        buf[i]    = cur - coef * prev;
        prev      = cur;
    }
}

// ═══════════════════════════════════════════════════════════════════
//  Ana Audio Engine yapısı
// ═══════════════════════════════════════════════════════════════════
struct AudioEngine {
    int   sr;

    // Zincir
    float gain_lin    = 1.f;
    Butter4 hp, lp;
    bool hp_on = false, lp_on = false;

    Biquad notch_50, notch_60;
    bool hum_on = false;

    Biquad de_esser_bq;
    bool de_esser_on = false;

    Biquad presence_bq;       // Clarity presence boost
    bool presence_on = false;
    float presence_gain = 0.f;

    Biquad sib_bq;            // Sibilance reduction
    bool sib_on = false;
    float sib_cut = 0.f;      // 0..1 strength

    NoiseGate gate;
    bool gate_on = false;

    Compressor comp;
    bool comp_on = false;

    Limiter lim;
    bool lim_on = false;

    Biquad eq_bq;
    bool eq_on = false;

    // Reverb reduction preemphasis state
    float  rev_prev  = 0.f;
    float  rev_coef  = 0.f;
    bool   rev_on    = false;

    // Spectral
    std::unique_ptr<SpectralNR> nr;
    bool nr_on = false;

    std::unique_ptr<FanSep> fan;
    bool fan_on = false;

    // ── Yeni AI modülleri ──────────────────────────────────────────
    std::unique_ptr<SpeechEnhancer>  speech_enh;
    bool speech_enh_on = false;

    std::unique_ptr<NoiseSupervisor> noise_sup;
    bool noise_sup_on = false;

    std::unique_ptr<HissSuppressor>  hiss_sup;
    bool hiss_sup_on = false;

    // ── Ses tonu ve karakter modülleri ────────────────────────────
    DCBlocker    dc_block;
    VoiceTone    voice_tone;
    bool         voice_tone_on = false;

    VoiceWarmth  voice_warmth;
    bool         voice_warmth_on = false;

    VocalEnhancer vocal_enh;
    bool          vocal_enh_on = false;

    TransientShaper transient_shaper;
    bool            transient_on = false;

    AirBand      air_band;
    bool         air_band_on = false;
    // ───────────────────────────────────────────────────────────────

    // Noise profile (from VAD)
    std::vector<float> noise_buf;
    bool has_noise = false;

    explicit AudioEngine(int sample_rate) : sr(sample_rate) {}
};

// ═══════════════════════════════════════════════════════════════════
//  C API — Python ctypes tarafından çağrılır
// ═══════════════════════════════════════════════════════════════════
extern "C" {

// ── Yönetim ───────────────────────────────────────────────────────
void* ae_create(int sr) {
    return new AudioEngine(sr);
}
void ae_destroy(void* p) {
    delete static_cast<AudioEngine*>(p);
}

// ── Gürültü profili öğret (VAD'dan non-speech segment) ────────────
void ae_set_noise_profile(void* p, const float* data, int n) {
    auto* e = static_cast<AudioEngine*>(p);
    e->noise_buf.assign(data, data+n);
    e->has_noise = true;
    if (e->nr) e->nr->learn_noise(data, n);
}

// ── Filtre konfigürasyonları ───────────────────────────────────────
void ae_set_gain(void* p, float db) {
    static_cast<AudioEngine*>(p)->gain_lin = powf(10.f, db/20.f);
}

void ae_set_hp(void* p, float fc) {
    auto* e = static_cast<AudioEngine*>(p);
    if (fc <= 0.f) { e->hp_on = false; return; }
    e->hp.set_hp(fc, e->sr); e->hp.reset(); e->hp_on = true;
}

void ae_set_lp(void* p, float fc) {
    auto* e = static_cast<AudioEngine*>(p);
    if (fc <= 0.f || fc >= e->sr*0.499f) { e->lp_on = false; return; }
    e->lp.set_lp(fc, e->sr); e->lp.reset(); e->lp_on = true;
}

void ae_set_gate(void* p, float thr_linear) {
    auto* e = static_cast<AudioEngine*>(p);
    if (thr_linear <= 0.f) { e->gate_on = false; return; }
    e->gate.setup(thr_linear, (float)e->sr); e->gate_on = true;
}

void ae_set_dehum(void* p, int level) {
    auto* e = static_cast<AudioEngine*>(p);
    if (level <= 0) { e->hum_on = false; return; }
    float qs[] = {10.f, 30.f, 60.f};
    float q = qs[std::min(level-1, 2)];
    e->notch_50.set_notch(50.0,  q, e->sr); e->notch_50.reset();
    e->notch_60.set_notch(60.0,  q, e->sr); e->notch_60.reset();
    e->hum_on = true;
}

void ae_set_deesser(void* p, int level) {
    auto* e = static_cast<AudioEngine*>(p);
    if (level <= 0) { e->de_esser_on = false; return; }
    float gains[] = {-3.f, -6.f, -9.f};
    float g = gains[std::min(level-1, 2)];
    e->de_esser_bq.set_highshelf(5500.0, g, e->sr);
    e->de_esser_bq.reset();
    e->de_esser_on = true;
}

void ae_set_reverb(void* p, int level) {
    auto* e = static_cast<AudioEngine*>(p);
    if (level <= 0) { e->rev_on = false; return; }
    float coefs[] = {0.88f, 0.91f, 0.94f, 0.97f};
    e->rev_coef = coefs[std::min(level-1, 3)];
    e->rev_prev = 0.f;
    e->rev_on   = true;
}

void ae_set_comp(void* p, float thr_db, float ratio,
                 float atk_ms, float rel_ms) {
    auto* e = static_cast<AudioEngine*>(p);
    if (ratio <= 1.0001f) { e->comp_on = false; return; }
    e->comp.setup(thr_db, ratio, atk_ms, rel_ms, (float)e->sr);
    e->comp_on = true;
}

void ae_set_limiter(void* p, float ceil_db) {
    auto* e = static_cast<AudioEngine*>(p);
    if (ceil_db >= 0.f) { e->lim_on = false; return; }
    e->lim.setup(ceil_db, (float)e->sr); e->lim_on = true;
}

void ae_set_eq(void* p, float gain_db, float freq, float q) {
    auto* e = static_cast<AudioEngine*>(p);
    if (fabsf(gain_db) < 0.1f) { e->eq_on = false; return; }
    e->eq_bq.set_peak(freq, q, gain_db, e->sr);
    e->eq_bq.reset(); e->eq_on = true;
}

void ae_set_nr(void* p, int on, float strength) {
    auto* e = static_cast<AudioEngine*>(p);
    if (!on) { e->nr_on = false; return; }
    // strength 0.92+ → use larger FFT for better resolution
    int fft_size = (strength >= 0.85f) ? 4096 : 2048;
    e->nr = std::make_unique<SpectralNR>(fft_size, 512, strength);
    if (e->has_noise)
        e->nr->learn_noise(e->noise_buf.data(), (int)e->noise_buf.size());
    e->nr_on = true;
}

// mode: 0=off, 1=gentle, 2=balanced, 3=aggressive, 4=max
void ae_set_fan(void* p, int mode) {
    auto* e = static_cast<AudioEngine*>(p);
    if (mode <= 0) { e->fan_on = false; return; }
    e->fan = std::make_unique<FanSep>(e->sr, mode-1);
    e->fan_on = true;
}

// AI Clarity: level 0-4
void ae_set_clarity(void* p, int level) {
    auto* e = static_cast<AudioEngine*>(p);
    if (level <= 0) {
        e->presence_on = false; e->sib_on = false; return;
    }
    float strengths[] = {0.f, 0.20f, 0.35f, 0.50f, 0.65f};
    float st = strengths[std::min(level, 4)];

    // Presence boost 2-4 kHz
    if (level >= 2) {
        double boost_db = st * 6.0;
        e->presence_bq.set_peak(3000.0, 0.8, boost_db, e->sr);
        e->presence_bq.reset();
        e->presence_gain = st * 0.06f;
        e->presence_on   = true;
    } else {
        e->presence_on = false;
    }

    // Sibilance reduction (level 4 only)
    if (level >= 4) {
        e->sib_bq.set_highshelf(7500.0, -6.0, e->sr);
        e->sib_bq.reset();
        e->sib_cut = 0.25f;
        e->sib_on  = true;
    } else {
        e->sib_on = false;
    }
}

// ── SpeechEnhancer: level 0=off, 1-4 strength ────────────────────
void ae_set_speech_enhance(void* p, int level) {
    auto* e = static_cast<AudioEngine*>(p);
    if (level <= 0) { e->speech_enh_on = false; return; }
    float strengths[] = {0.f, 0.25f, 0.50f, 0.75f, 1.00f};
    float st = strengths[std::min(level, 4)];
    e->speech_enh = std::make_unique<SpeechEnhancer>(e->sr, st);
    e->speech_enh_on = true;
}

// ── NoiseSupervisor: level 0=off, 1-4 strength ───────────────────
void ae_set_noise_sup(void* p, int level) {
    auto* e = static_cast<AudioEngine*>(p);
    if (level <= 0) { e->noise_sup_on = false; return; }
    float strengths[] = {0.f, 0.25f, 0.50f, 0.75f, 1.00f};
    float st = strengths[std::min(level, 4)];
    e->noise_sup = std::make_unique<NoiseSupervisor>(e->sr, st);
    e->noise_sup_on = true;
}

// ── HissSuppressor: level 0=off, 1-4 strength ────────────────────
void ae_set_hiss_sup(void* p, int level) {
    auto* e = static_cast<AudioEngine*>(p);
    if (level <= 0) { e->hiss_sup_on = false; return; }
    float strengths[] = {0.f, 0.25f, 0.50f, 0.75f, 1.00f};
    float st = strengths[std::min(level, 4)];
    e->hiss_sup = std::make_unique<HissSuppressor>(e->sr, st);
    e->hiss_sup_on = true;
}

// ── Warmup: pre-fill spectral estimators with noise to fix loud-opening bug ──
// Call after ae_set_noise_profile / ae_set_nr / ae_set_fan, before ae_process.
void ae_warmup(void* p, const float* noise_data, int n) {
    auto* e = static_cast<AudioEngine*>(p);
    if (n <= 0) return;
    // Warmup SpectralNR noise model
    if (e->nr_on && e->nr) {
        e->nr->learn_noise(noise_data, n);
    }
    // Warmup FanSep min-stat ring buffer (main fix for opening artifact)
    if (e->fan_on && e->fan) {
        e->fan->warmup(noise_data, n);
    }
    // Warmup NoiseSupervisor adaptive model
    if (e->noise_sup_on && e->noise_sup) {
        e->noise_sup->warmup(noise_data, n);
    }
    // Warmup HissSuppressor hiss floor
    if (e->hiss_sup_on && e->hiss_sup) {
        e->hiss_sup->warmup(noise_data, n);
    }
    // DC blocker reset (temiz başlangıç)
    e->dc_block.reset();
}

// ── Ana işlem fonksiyonu — in-place, float32 ─────────────────────
int ae_process(void* p, float* buf, int n) {
    auto* e = static_cast<AudioEngine*>(p);
    std::vector<float> tmp(n);

    // 0. DC Blocker — dosya başı DC offset temizle (her zaman aktif)
    e->dc_block.process(buf, n);

    // 1. Gain
    if (e->gain_lin != 1.f)
        for (int i = 0; i < n; ++i) buf[i] *= e->gain_lin;

    // 2. HP
    if (e->hp_on) e->hp.process(buf, n);

    // 3. LP
    if (e->lp_on) e->lp.process(buf, n);

    // 4. Noise Gate
    if (e->gate_on) e->gate.process(buf, n);

    // 5. De-Hum
    if (e->hum_on) {
        e->notch_50.process(buf, buf, n);
        e->notch_60.process(buf, buf, n);
    }

    // 6. De-Esser
    if (e->de_esser_on)
        e->de_esser_bq.process(buf, buf, n);

    // 7. Reverb reduction
    if (e->rev_on)
        apply_preemphasis(buf, n, e->rev_coef, e->rev_prev);

    // 8. AI Noise Reduction
    if (e->nr_on) {
        e->nr->process(buf, tmp.data(), n);
        memcpy(buf, tmp.data(), n * sizeof(float));
    }

    // 9. Fan Speech Separator
    if (e->fan_on) {
        e->fan->process(buf, tmp.data(), n);
        memcpy(buf, tmp.data(), n * sizeof(float));
    }

    // 10. Speech Enhancer — konuşma formantlarını güçlendir
    if (e->speech_enh_on) {
        e->speech_enh->process(buf, tmp.data(), n);
        memcpy(buf, tmp.data(), n * sizeof(float));
    }

    // 11. Noise Supervisor — sürekli adaptif gürültü denetimi
    if (e->noise_sup_on) {
        e->noise_sup->process(buf, tmp.data(), n);
        memcpy(buf, tmp.data(), n * sizeof(float));
    }

    // 12. Hiss Suppressor — ssssss tiz tıslama bastırıcı
    if (e->hiss_sup_on) {
        e->hiss_sup->process(buf, tmp.data(), n);
        memcpy(buf, tmp.data(), n * sizeof(float));
    }

    // 13. AI Clarity — presence boost
    if (e->presence_on) {
        e->presence_bq.process(buf, tmp.data(), n);
        for (int i = 0; i < n; ++i)
            buf[i] = buf[i] * (1.f - e->presence_gain) + tmp[i] * e->presence_gain;
    }

    // 14. Sibilance reduction
    if (e->sib_on)
        e->sib_bq.process(buf, buf, n);

    // 15. Voice Tone — kalınlık / incelik
    if (e->voice_tone_on)
        e->voice_tone.process(buf, n);

    // 16. Voice Warmth — tüp ısısı / 600Hz sıcaklık
    if (e->voice_warmth_on)
        e->voice_warmth.process(buf, n);

    // 17. Vocal Enhancer — konuşma berraklık güçlendirici
    if (e->vocal_enh_on)
        e->vocal_enh.process(buf, n);

    // 18. Compressor
    if (e->comp_on) e->comp.process(buf, n);

    // 19. Transient Shaper — attack/patlama güçlendirici
    if (e->transient_on)
        e->transient_shaper.process(buf, n);

    // 20. EQ
    if (e->eq_on) e->eq_bq.process(buf, buf, n);

    // 21. Air Band — 10kHz+ yüksek raf
    if (e->air_band_on)
        e->air_band.process(buf, n);

    // 22. Limiter (always last)
    if (e->lim_on) e->lim.process(buf, n);

    return 0;
}

// ── Peak normalize ───────────────────────────────────────────────
void ae_peak_normalize(float* buf, int n, float target_dbfs) {
    float peak = 0.f;
    for (int i = 0; i < n; ++i) peak = std::max(peak, fabsf(buf[i]));
    if (peak < 1e-7f) return;
    float g = powf(10.f, target_dbfs/20.f) / peak;
    for (int i = 0; i < n; ++i) buf[i] *= g;
}

// ── Fade-in (tıklama/tıslama önleme) ─────────────────────────────
void ae_fade_in(float* buf, int n, int fade_samples) {
    int f = std::min(n, fade_samples);
    for (int i = 0; i < f; ++i)
        buf[i] *= (float)i / (float)f;
}

// ── VoiceTone: gain_db > 0 = kalın/sıcak, < 0 = ince/parlak ────
void ae_set_voice_tone(void* p, float gain_db) {
    auto* e = static_cast<AudioEngine*>(p);
    if (fabsf(gain_db) < 0.1f) { e->voice_tone_on = false; return; }
    e->voice_tone.setup((double)gain_db, (double)e->sr);
    e->voice_tone_on = true;
}

// ── VoiceWarmth: strength 0..1 ───────────────────────────────────
void ae_set_voice_warmth(void* p, float strength) {
    auto* e = static_cast<AudioEngine*>(p);
    if (strength < 0.01f) { e->voice_warmth_on = false; return; }
    e->voice_warmth.setup(strength, (double)e->sr);
    e->voice_warmth_on = true;
}

// ── VocalEnhancer: strength 0..1 ─────────────────────────────────
void ae_set_vocal_enh(void* p, float strength) {
    auto* e = static_cast<AudioEngine*>(p);
    if (strength < 0.01f) { e->vocal_enh_on = false; return; }
    e->vocal_enh.setup(strength, (double)e->sr);
    e->vocal_enh_on = true;
}

// ── TransientShaper: strength 0..1 ───────────────────────────────
void ae_set_transient(void* p, float strength) {
    auto* e = static_cast<AudioEngine*>(p);
    if (strength < 0.01f) { e->transient_on = false; return; }
    e->transient_shaper.setup(strength, (float)e->sr);
    e->transient_on = true;
}

// ── AirBand: gain_db 0 = off, > 0 = hava/parlaklık boost ─────────
void ae_set_air(void* p, float gain_db) {
    auto* e = static_cast<AudioEngine*>(p);
    if (fabsf(gain_db) < 0.1f) { e->air_band_on = false; return; }
    e->air_band.setup((double)gain_db, (double)e->sr);
    e->air_band_on = true;
}

// ── Sürüm bilgisi ─────────────────────────────────────────────────
const char* ae_version() { return "KavramAudioEngine/1.3"; }

} // extern "C"
