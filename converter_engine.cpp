// converter_engine.cpp  —  Kavram 2.3  (C++ / FFmpeg) - Akıllı Önizleme & Bellek Optimizasyonlu
// Derleme: g++ -O2 -shared -fPIC -o libconverter_engine.so converter_engine.cpp -lm \
//          $(pkg-config --cflags --libs libavformat libavcodec libavutil libswresample libswscale)
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

#include <unistd.h>
#include <atomic>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cmath>
#include <cstdio>
#include <cstdarg>
#include <vector>
#include <string>
#include <algorithm>

#ifdef __linux__
#  include <sys/resource.h>
#  include <sys/stat.h>
#endif

extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libavutil/avutil.h>
#include <libavutil/opt.h>
#include <libavutil/channel_layout.h>
#include <libavutil/samplefmt.h>
#include <libavutil/imgutils.h>
#include <libswresample/swresample.h>
#include <libswscale/swscale.h>
}

#ifdef _WIN32
#  define EXPORT extern "C" __declspec(dllexport)
#else
#  define EXPORT extern "C" __attribute__((visibility("default")))
#endif

static char              g_err[512] = "";
static std::atomic<bool> g_cancel{false};

static void set_err(const char* fmt, ...) {
    va_list a; va_start(a, fmt);
    vsnprintf(g_err, sizeof(g_err), fmt, a);
    va_end(a);
}

EXPORT const char* kavram_last_error()   { return g_err; }
EXPORT const char* kavram_version()      { return "2.3.1"; }
EXPORT void        kavram_cancel()       { g_cancel.store(true,  std::memory_order_relaxed); }
EXPORT void        kavram_reset_cancel() { g_cancel.store(false, std::memory_order_relaxed); }

typedef void (*ProgressCB)(int);
static inline void fire_cb(ProgressCB cb, int& last, int val) {
    if (!cb) return;
    val = val < 0 ? 0 : val > 100 ? 100 : val;
    if (val > last) { last = val; cb(val); }
}

EXPORT int kavram_file_copy(const char* src, const char* dst) {
    if (!src || !dst || !src[0] || !dst[0]) { set_err("Geçersiz dosya yolu"); return -1; }
#ifdef __linux__
    struct stat ss, ds;
    if (stat(src, &ss) == 0 && stat(dst, &ds) == 0 &&
        ss.st_dev == ds.st_dev && ss.st_ino == ds.st_ino) return 0;
#else
    char rp_s[4096] = {}, rp_d[4096] = {};
    if (realpath(src, rp_s) && realpath(dst, rp_d) && strcmp(rp_s, rp_d) == 0) return 0;
#endif
    FILE* fi = fopen(src, "rb");
    if (!fi) { set_err("Kaynak açılamadı: %s", src); return -1; }
    FILE* fo = fopen(dst, "wb");
    if (!fo) { fclose(fi); set_err("Hedef açılamadı: %s", dst); return -1; }
    static const size_t BUF = 262144;
    std::vector<char> buf(BUF);
    size_t n;
    int ok = 1;
    while ((n = fread(buf.data(), 1, BUF, fi)) > 0) {
        if (fwrite(buf.data(), 1, n, fo) != n) { ok = 0; break; }
    }
    fclose(fi); fclose(fo);
    if (!ok) { set_err("Yazma hatası: %s", dst); return -1; }
    return 0;
}

static int audio_change_speed(const int16_t* in, int n, int ch, float spd, int16_t* out) {
    if (fabsf(spd - 1.0f) < 0.001f) { memcpy(out, in, (size_t)n * 2); return n; }
    int frames = n / ch;
    int new_frames = (int)ceilf((float)frames / spd);
    if (new_frames < 1) new_frames = 1;
    for (int i = 0; i < new_frames; i++) {
        float sp = (float)i * spd;
        int   si = (int)sp;
        float fr = sp - (float)si;
        if (si >= frames - 1) { si = frames - 1; fr = 0.0f; }
        for (int c = 0; c < ch; c++) {
            float s0 = in[si * ch + c];
            float s1 = (si + 1 < frames) ? in[(si + 1) * ch + c] : s0;
            float v  = s0 + fr * (s1 - s0);
            out[i * ch + c] = (int16_t)(v < -32768.0f ? -32768 : v > 32767.0f ? 32767 : v);
        }
    }
    return new_frames * ch;
}
static int audio_calc_pitch_rate(int sr, float semitones) {
    return (int)((float)sr * powf(2.0f, semitones / 12.0f));
}
static void audio_normalize(int16_t* s, int n) {
    int16_t pk = 0;
    for (int i = 0; i < n; i++) {
        int16_t v = s[i] < 0 ? (int16_t)-s[i] : s[i];
        if (v > pk) pk = v;
    }
    if (!pk) return;
    float g = 32767.0f / (float)pk;
    for (int i = 0; i < n; i++) {
        float v = s[i] * g;
        s[i] = (int16_t)(v < -32768.0f ? -32768 : v > 32767.0f ? 32767 : v);
    }
}
static void audio_compress(int16_t* s, int n, float thr_ratio, float ratio) {
    float thr = thr_ratio * 32767.0f;
    for (int i = 0; i < n; i++) {
        float v = (float)s[i], av = fabsf(v);
        if (av > thr) {
            float sg = v < 0.0f ? -1.0f : 1.0f;
            v = sg * (thr + (av - thr) / ratio);
        }
        s[i] = (int16_t)(v < -32768.0f ? -32768 : v > 32767.0f ? 32767 : v);
    }
}
static void audio_low_pass(int16_t* s, int n, int ch, int sr, float hz) {
    float rc = 1.0f / (2.0f * 3.14159265f * hz), dt = 1.0f / (float)sr;
    float a = dt / (rc + dt);
    std::vector<float> p(ch, 0.0f);
    for (int i = 0; i < n; i++) {
        int c = i % ch;
        float f = p[c] + a * ((float)s[i] - p[c]); p[c] = f;
        s[i] = (int16_t)(f < -32768.0f ? -32768 : f > 32767.0f ? 32767 : f);
    }
}
static void audio_high_pass(int16_t* s, int n, int ch, int sr, float hz) {
    float rc = 1.0f / (2.0f * 3.14159265f * hz), dt = 1.0f / (float)sr;
    float a = rc / (rc + dt);
    std::vector<float> pi(ch, 0.0f), po(ch, 0.0f);
    for (int i = 0; i < n; i++) {
        int c = i % ch;
        float v = (float)s[i], f = a * (po[c] + v - pi[c]);
        pi[c] = v; po[c] = f;
        s[i] = (int16_t)(f < -32768.0f ? -32768 : f > 32767.0f ? 32767 : f);
    }
}
static void audio_fade_in(int16_t* s, int n, int ch, int sr, float sec) {
    int fade = (int)(sec * (float)sr) * ch;
    if (fade > n) fade = n;
    for (int i = 0; i < fade; i++) {
        float v = (float)s[i] * ((float)i / (float)fade);
        s[i] = (int16_t)(v < -32768.0f ? -32768 : v > 32767.0f ? 32767 : v);
    }
}
static void audio_fade_out(int16_t* s, int n, int ch, int sr, float sec) {
    int fade = (int)(sec * (float)sr) * ch;
    if (fade > n) fade = n;
    int st = n - fade;
    for (int i = st; i < n; i++) {
        float v = (float)s[i] * ((float)(n - i) / (float)fade);
        s[i] = (int16_t)(v < -32768.0f ? -32768 : v > 32767.0f ? 32767 : v);
    }
}
static void audio_invert_phase(int16_t* s, int n) {
    for (int i = 0; i < n; i++) {
        int v = -(int)s[i];
        s[i] = (int16_t)(v < -32768 ? -32768 : v > 32767 ? 32767 : v);
    }
}
static void audio_pan(int16_t* s, int n, float pan) {
    float lg = pan <= 0.0f ? 1.0f : 1.0f - pan;
    float rg = pan >= 0.0f ? 1.0f : 1.0f + pan;
    for (int i = 0; i + 1 < n; i += 2) {
        float l = (float)s[i] * lg, r = (float)s[i+1] * rg;
        s[i]   = (int16_t)(l < -32768.0f ? -32768 : l > 32767.0f ? 32767 : l);
        s[i+1] = (int16_t)(r < -32768.0f ? -32768 : r > 32767.0f ? 32767 : r);
    }
}
static void apply_dsp(std::vector<int16_t>& buf, int ch, int sr, float speed, int effect) {
    if (fabsf(speed - 1.0f) > 0.001f) {
        int cnt    = (int)buf.size();
        int frames = cnt / ch;
        int new_frames = (int)ceilf((float)frames / speed) + 2;
        std::vector<int16_t> tmp((size_t)new_frames * ch);
        int n = audio_change_speed(buf.data(), cnt, ch, speed, tmp.data());
        tmp.resize((size_t)(n > 0 ? n : 0));
        buf = std::move(tmp);
    }
    int count = (int)buf.size();
    switch (effect) {
        case 1: audio_normalize   (buf.data(), count); break;
        case 2: audio_compress    (buf.data(), count, 0.3f, 4.0f); break;
        case 3: audio_low_pass    (buf.data(), count, ch, sr, 1000.0f); break;
        case 4: audio_high_pass   (buf.data(), count, ch, sr, 3000.0f); break;
        case 5: audio_fade_in (buf.data(), count, ch, sr, 1.0f);
                audio_fade_out(buf.data(), count, ch, sr, 1.0f); break;
        case 6: audio_invert_phase(buf.data(), count); break;
        case 7: if (ch == 2) audio_pan(buf.data(), count, -0.5f); break;
        case 8: if (ch == 2) audio_pan(buf.data(), count,  0.5f); break;
        default: break;
    }
}
static void set_ch_layout(AVCodecContext* ctx, int nb_ch) {
    AVChannelLayout layout = (nb_ch == 1) ? (AVChannelLayout)AV_CHANNEL_LAYOUT_MONO
                                          : (AVChannelLayout)AV_CHANNEL_LAYOUT_STEREO;
    av_channel_layout_copy(&ctx->ch_layout, &layout);
}

static int decode_audio_to_pcm(const char* in_path, std::vector<int16_t>& all,
                               int& out_ch, int& out_sr, ProgressCB cb, int pct_end, int is_preview) {
    AVFormatContext* ifmt = nullptr;
    if (avformat_open_input(&ifmt, in_path, nullptr, nullptr) < 0) {
        set_err("Giriş açılamadı: %s", in_path); return -1;
    }
    avformat_find_stream_info(ifmt, nullptr);
    int aidx = -1;
    for (unsigned i = 0; i < ifmt->nb_streams; i++)
        if (ifmt->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_AUDIO) { aidx = (int)i; break; }
    if (aidx < 0) { avformat_close_input(&ifmt); set_err("Ses akışı bulunamadı"); return -1; }
    AVCodecParameters* ipar = ifmt->streams[aidx]->codecpar;
    const AVCodec* idec = avcodec_find_decoder(ipar->codec_id);
    if (!idec) { avformat_close_input(&ifmt); set_err("Decoder bulunamadı"); return -1; }
    AVCodecContext* ictx = avcodec_alloc_context3(idec);
    avcodec_parameters_to_context(ictx, ipar);
    ictx->thread_count = 2;
    avcodec_open2(ictx, idec, nullptr);
    int in_sr = ictx->sample_rate;
    int in_ch = ictx->ch_layout.nb_channels;
    if (in_ch < 1) in_ch = 1;
    if (in_ch > 2) in_ch = 2;
    AVChannelLayout chl = in_ch == 1 ? (AVChannelLayout)AV_CHANNEL_LAYOUT_MONO
                                     : (AVChannelLayout)AV_CHANNEL_LAYOUT_STEREO;
    SwrContext* swr = nullptr;
    swr_alloc_set_opts2(&swr, &chl, AV_SAMPLE_FMT_S16, in_sr,
                        &ictx->ch_layout, ictx->sample_fmt, in_sr, 0, nullptr);
    swr_init(swr);
    if (ifmt->duration > 0) {
        int64_t ds = ifmt->duration / AV_TIME_BASE;
        all.reserve((size_t)(ds + 10) * (size_t)in_sr * (size_t)in_ch);
    }
    AVPacket* pkt = av_packet_alloc();
    AVFrame* frm = av_frame_alloc();
    int64_t dur_ts = ifmt->streams[aidx]->duration;
    int64_t pos_ts = 0;
    int     last   = -1;
    
    while (!g_cancel.load(std::memory_order_relaxed) && av_read_frame(ifmt, pkt) >= 0) {
        if (pkt->stream_index != aidx) { av_packet_unref(pkt); continue; }
        if (pkt->pts != AV_NOPTS_VALUE) pos_ts = pkt->pts;
        
        if (is_preview && pkt->pts != AV_NOPTS_VALUE) {
            double sec = pkt->pts * av_q2d(ifmt->streams[aidx]->time_base);
            if (sec > 15.0) { av_packet_unref(pkt); break; }
        }
        
        avcodec_send_packet(ictx, pkt);
        while (avcodec_receive_frame(ictx, frm) == 0) {
            int n = frm->nb_samples;
            size_t old = all.size();
            all.resize(old + (size_t)(n * in_ch));
            uint8_t* d = (uint8_t*)(all.data() + old);
            swr_convert(swr, &d, n, (const uint8_t**)frm->data, n);
            av_frame_unref(frm);
        }
        av_packet_unref(pkt);
        if (dur_ts > 0) fire_cb(cb, last, (int)(pos_ts * pct_end / dur_ts));
    }
    avcodec_send_packet(ictx, nullptr);
    while (avcodec_receive_frame(ictx, frm) == 0) {
        int n = frm->nb_samples;
        size_t old = all.size();
        all.resize(old + (size_t)(n * in_ch));
        uint8_t* d = (uint8_t*)(all.data() + old);
        swr_convert(swr, &d, n, (const uint8_t**)frm->data, n);
        av_frame_unref(frm);
    }
    av_frame_free(&frm); av_packet_free(&pkt);
    swr_free(&swr); avcodec_free_context(&ictx); avformat_close_input(&ifmt);
    out_ch = in_ch; out_sr = in_sr;
    return 0;
}

static int convert_audio(const char* in_path, const char* out_path,
                         float speed, float pitch, int effect,
                         int change_freq, int new_freq, int is_preview, ProgressCB cb) {
    std::vector<int16_t> all;
    int in_ch = 1, in_sr = 44100;
    int last_pct = -1;
    if (decode_audio_to_pcm(in_path, all, in_ch, in_sr, cb, 30, is_preview) < 0) return -1;
    fire_cb(cb, last_pct, 30);
    if (g_cancel.load()) return -99;
    apply_dsp(all, in_ch, in_sr, speed, effect);
    fire_cb(cb, last_pct, 50);
    int out_sr = in_sr;
    if (fabsf(pitch) > 0.001f) out_sr = audio_calc_pitch_rate(in_sr, pitch);
    else if (change_freq && new_freq > 0) out_sr = new_freq;
    std::string op(out_path);
    auto ends = [&](const char* s) {
        size_t sl = strlen(s);
        return op.size() >= sl && op.compare(op.size() - sl, sl, s) == 0;
    };
    const char* enc_name = "pcm_s16le";
    if      (ends(".mp3"))                enc_name = "libmp3lame";
    else if (ends(".opus"))               enc_name = "libopus";
    else if (ends(".ogg"))                enc_name = "libvorbis";
    else if (ends(".m4a") || ends(".aac")) enc_name = "aac";
    else if (ends(".flac"))               enc_name = "flac";
    else if (ends(".wma"))                enc_name = "wmav2";
    const AVCodec* oenc = avcodec_find_encoder_by_name(enc_name);
    if (!oenc) oenc = avcodec_find_encoder(AV_CODEC_ID_MP3);
    if (!oenc) { set_err("Ses encoder bulunamadı"); return -1; }
    AVFormatContext* ofmt = nullptr;
    if (avformat_alloc_output_context2(&ofmt, nullptr, nullptr, out_path) < 0) {
        set_err("Çıkış oluşturulamadı: %s", out_path); return -1;
    }
    AVStream* ost  = avformat_new_stream(ofmt, nullptr);
    AVCodecContext* octx = avcodec_alloc_context3(oenc);
    octx->sample_rate = out_sr;
    octx->bit_rate    = 192000;
    octx->sample_fmt  = oenc->sample_fmts ? oenc->sample_fmts[0] : AV_SAMPLE_FMT_FLTP;
    set_ch_layout(octx, in_ch);
    if (ofmt->oformat->flags & AVFMT_GLOBALHEADER) octx->flags |= AV_CODEC_FLAG_GLOBAL_HEADER;
    avcodec_open2(octx, oenc, nullptr);
    avcodec_parameters_from_context(ost->codecpar, octx);
    ost->time_base = {1, out_sr};
    if (!(ofmt->oformat->flags & AVFMT_NOFILE)) avio_open(&ofmt->pb, out_path, AVIO_FLAG_WRITE);
    if (avformat_write_header(ofmt, nullptr) < 0) {
        avcodec_free_context(&octx);
        if (!(ofmt->oformat->flags & AVFMT_NOFILE)) avio_closep(&ofmt->pb);
        avformat_free_context(ofmt);
        set_err("Ses başlık yazılamadı: %s", out_path); return -1;
    }
    AVChannelLayout enc_chl; av_channel_layout_copy(&enc_chl, &octx->ch_layout);
    AVChannelLayout src_chl = in_ch == 1 ? (AVChannelLayout)AV_CHANNEL_LAYOUT_MONO
                                         : (AVChannelLayout)AV_CHANNEL_LAYOUT_STEREO;
    SwrContext* swr2 = nullptr;
    if (octx->sample_fmt != AV_SAMPLE_FMT_S16) {
        swr_alloc_set_opts2(&swr2, &enc_chl, octx->sample_fmt, out_sr,
                            &src_chl, AV_SAMPLE_FMT_S16, out_sr, 0, nullptr);
        swr_init(swr2);
    }
    int frame_size = octx->frame_size > 0 ? octx->frame_size : 1024;
    AVFrame* ef = av_frame_alloc();
    ef->nb_samples  = frame_size;
    ef->format      = octx->sample_fmt;
    ef->sample_rate = out_sr;
    av_channel_layout_copy(&ef->ch_layout, &octx->ch_layout);
    av_frame_get_buffer(ef, 0);
    AVPacket* epkt  = av_packet_alloc();
    int offset = 0, pts = 0;
    int total_s = (int)all.size();
    
    while (!g_cancel.load(std::memory_order_relaxed) && offset < total_s) {
        if (is_preview && ((double)offset / (double)(in_ch * out_sr)) > 5.0) break;
        
        int avail = (total_s - offset) / in_ch;
        int ns    = avail < frame_size ? avail : frame_size;
        ef->nb_samples = ns;
        av_frame_make_writable(ef);
        if (swr2) {
            const uint8_t* src = (const uint8_t*)(all.data() + offset);
            swr_convert(swr2, (uint8_t**)ef->data, ns, &src, ns);
        } else {
            memcpy(ef->data[0], all.data() + offset, (size_t)ns * (size_t)in_ch * 2);
        }
        ef->pts = pts; pts += ns; offset += ns * in_ch;
        avcodec_send_frame(octx, ef);
        while (avcodec_receive_packet(octx, epkt) == 0) {
            av_packet_rescale_ts(epkt, octx->time_base, ost->time_base);
            epkt->stream_index = 0;
            av_interleaved_write_frame(ofmt, epkt);
            av_packet_unref(epkt);
        }
        fire_cb(cb, last_pct, 55 + (int)((float)offset / (float)total_s * 40.0f));
    }
    avcodec_send_frame(octx, nullptr);
    while (avcodec_receive_packet(octx, epkt) == 0) {
        av_packet_rescale_ts(epkt, octx->time_base, ost->time_base);
        epkt->stream_index = 0;
        av_interleaved_write_frame(ofmt, epkt);
        av_packet_unref(epkt);
    }
    av_write_trailer(ofmt);
    if (swr2) swr_free(&swr2);
    av_frame_free(&ef); av_packet_free(&epkt);
    avcodec_free_context(&octx);
    if (!(ofmt->oformat->flags & AVFMT_NOFILE)) avio_closep(&ofmt->pb);
    avformat_free_context(ofmt);
    fire_cb(cb, last_pct, 100);
    return g_cancel.load() ? -99 : 0;
}

// GÜNCELLENDİ: vid_rm_aud bayrağı eklendi.
static int convert_video_remux(const char* in, const char* out, int vid_rm_aud, int is_preview, ProgressCB cb) {
    AVFormatContext* ifmt = nullptr;
    if (avformat_open_input(&ifmt, in, nullptr, nullptr) < 0) { set_err("Video açılamadı: %s", in); return -1; }
    avformat_find_stream_info(ifmt, nullptr);
    AVFormatContext* ofmt = nullptr;
    avformat_alloc_output_context2(&ofmt, nullptr, nullptr, out);
    if (!ofmt) { avformat_close_input(&ifmt); set_err("Çıkış oluşturulamadı: %s", out); return -1; }
    
    std::vector<int> stream_map(ifmt->nb_streams, -1);
    int out_idx = 0;
    for (unsigned i = 0; i < ifmt->nb_streams; i++) {
        AVStream* ist = ifmt->streams[i];
        if (vid_rm_aud && ist->codecpar->codec_type == AVMEDIA_TYPE_AUDIO) continue; // Sesi Atla!
        
        AVStream* ost = avformat_new_stream(ofmt, nullptr);
        avcodec_parameters_copy(ost->codecpar, ist->codecpar);
        ost->codecpar->codec_tag = 0;
        ost->time_base = ist->time_base;
        stream_map[i] = out_idx++;
    }
    
    if (!(ofmt->oformat->flags & AVFMT_NOFILE)) avio_open(&ofmt->pb, out, AVIO_FLAG_WRITE);
    if (avformat_write_header(ofmt, nullptr) < 0) {
        if (!(ofmt->oformat->flags & AVFMT_NOFILE)) avio_closep(&ofmt->pb);
        avformat_free_context(ofmt); avformat_close_input(&ifmt);
        set_err("Video başlık yazılamadı: %s", out); return -1;
    }
    
    int64_t dur = ifmt->duration;
    int last_pct = -1;
    AVPacket* pkt = av_packet_alloc();
    
    while (!g_cancel.load(std::memory_order_relaxed) && av_read_frame(ifmt, pkt) >= 0) {
        unsigned si = (unsigned)pkt->stream_index;
        if (si >= ifmt->nb_streams || stream_map[si] < 0) { av_packet_unref(pkt); continue; }
        
        if (is_preview && pkt->pts != AV_NOPTS_VALUE) {
            double sec = pkt->pts * av_q2d(ifmt->streams[si]->time_base);
            if (sec > 5.0) { av_packet_unref(pkt); break; }
        }

        pkt->stream_index = stream_map[si];
        av_packet_rescale_ts(pkt, ifmt->streams[si]->time_base, ofmt->streams[pkt->stream_index]->time_base);
        pkt->pos = -1;
        av_interleaved_write_frame(ofmt, pkt);
        
        if (dur > 0 && pkt->pts != AV_NOPTS_VALUE) {
            int64_t pos = av_rescale_q(pkt->pts, ofmt->streams[pkt->stream_index]->time_base, AV_TIME_BASE_Q);
            fire_cb(cb, last_pct, (int)(pos * 95 / dur));
        }
        av_packet_unref(pkt);
    }
    av_packet_free(&pkt);
    av_write_trailer(ofmt);
    if (!(ofmt->oformat->flags & AVFMT_NOFILE)) avio_closep(&ofmt->pb);
    avformat_free_context(ofmt);
    avformat_close_input(&ifmt);
    fire_cb(cb, last_pct, 100);
    return g_cancel.load() ? -99 : 0;
}

// GÜNCELLENDİ: Invert (Ters Renk) ve Sesi Sil (rm_aud) özellikleri eklendi.
static int convert_video_fx(const char* in, const char* out, int do_gray, int do_inv, int rm_aud, int is_preview, ProgressCB cb) {
    AVFormatContext* ifmt = nullptr;
    if (avformat_open_input(&ifmt, in, nullptr, nullptr) < 0) { set_err("Video açılamadı: %s", in); return -1; }
    avformat_find_stream_info(ifmt, nullptr);
    int vidx = -1, aidx = -1;
    for (unsigned i = 0; i < ifmt->nb_streams; i++) {
        auto t = ifmt->streams[i]->codecpar->codec_type;
        if (t == AVMEDIA_TYPE_VIDEO && vidx < 0) vidx = (int)i;
        if (t == AVMEDIA_TYPE_AUDIO && aidx < 0) aidx = (int)i;
    }
    if (vidx < 0) { avformat_close_input(&ifmt); set_err("Video akışı yok"); return -1; }
    AVCodecParameters* vpar = ifmt->streams[vidx]->codecpar;
    const AVCodec* vdec = avcodec_find_decoder(vpar->codec_id);
    if (!vdec) { avformat_close_input(&ifmt); set_err("Video decoder bulunamadı"); return -1; }
    AVCodecContext* vctx = avcodec_alloc_context3(vdec);
    avcodec_parameters_to_context(vctx, vpar);
    vctx->thread_count = 2;
    avcodec_open2(vctx, vdec, nullptr);
    
    AVFormatContext* ofmt = nullptr;
    avformat_alloc_output_context2(&ofmt, nullptr, nullptr, out);
    if (!ofmt) { avcodec_free_context(&vctx); avformat_close_input(&ifmt); set_err("Çıkış oluşturulamadı: %s", out); return -1; }
    const AVCodec* venc = avcodec_find_encoder_by_name("libx264");
    if (!venc) venc = avcodec_find_encoder(AV_CODEC_ID_H264);
    if (!venc) venc = avcodec_find_encoder(AV_CODEC_ID_MPEG4);
    if (!venc) { avformat_free_context(ofmt); avcodec_free_context(&vctx); avformat_close_input(&ifmt); set_err("Video encoder bulunamadı"); return -1; }
    
    AVRational fr = av_guess_frame_rate(ifmt, ifmt->streams[vidx], nullptr);
    if (!fr.num || !fr.den) fr = {25, 1};
    AVStream* vst = avformat_new_stream(ofmt, nullptr);
    AVCodecContext* venc_ctx = avcodec_alloc_context3(venc);
    venc_ctx->width        = vctx->width;
    venc_ctx->height       = vctx->height;
    venc_ctx->pix_fmt      = AV_PIX_FMT_YUV420P;
    venc_ctx->time_base    = {fr.den, fr.num};
    venc_ctx->framerate    = fr;
    venc_ctx->thread_count = 2;
    venc_ctx->gop_size     = 50;
    av_opt_set(venc_ctx->priv_data, "preset", "veryfast", 0);
    av_opt_set(venc_ctx->priv_data, "crf",    "23",       0);
    if (ofmt->oformat->flags & AVFMT_GLOBALHEADER) venc_ctx->flags |= AV_CODEC_FLAG_GLOBAL_HEADER;
    if (avcodec_open2(venc_ctx, venc, nullptr) < 0) {
        avcodec_free_context(&venc_ctx); avformat_free_context(ofmt);
        avcodec_free_context(&vctx); avformat_close_input(&ifmt);
        set_err("Video encoder açılamadı"); return -1;
    }
    avcodec_parameters_from_context(vst->codecpar, venc_ctx);
    vst->time_base = venc_ctx->time_base;
    
    int ast_idx = -1;
    // Eğer sesi sil opsiyonu aktifse audio stream OLUŞTURMA
    if (aidx >= 0 && !rm_aud) {
        AVStream* ast = avformat_new_stream(ofmt, nullptr);
        avcodec_parameters_copy(ast->codecpar, ifmt->streams[aidx]->codecpar);
        ast->codecpar->codec_tag = 0;
        ast->time_base = ifmt->streams[aidx]->time_base;
        ast_idx = ast->index;
    }
    
    if (!(ofmt->oformat->flags & AVFMT_NOFILE)) avio_open(&ofmt->pb, out, AVIO_FLAG_WRITE);
    if (avformat_write_header(ofmt, nullptr) < 0) {
        avcodec_free_context(&venc_ctx); avcodec_free_context(&vctx);
        if (!(ofmt->oformat->flags & AVFMT_NOFILE)) avio_closep(&ofmt->pb);
        avformat_free_context(ofmt); avformat_close_input(&ifmt);
        set_err("Video başlık yazılamadı: %s", out); return -1;
    }
    
    SwsContext* sws = sws_getContext(vctx->width, vctx->height, vctx->pix_fmt,
                                     vctx->width, vctx->height, AV_PIX_FMT_YUV420P,
                                     SWS_FAST_BILINEAR, nullptr, nullptr, nullptr);
    AVPacket* pkt     = av_packet_alloc();
    AVPacket* opkt    = av_packet_alloc();
    AVFrame* dec_frm = av_frame_alloc();
    AVFrame* enc_frm = av_frame_alloc();
    enc_frm->format = AV_PIX_FMT_YUV420P;
    enc_frm->width  = vctx->width;
    enc_frm->height = vctx->height;
    av_frame_get_buffer(enc_frm, 0);
    
    int64_t dur = ifmt->duration;
    int last_pct = -1;
    int64_t frame_num = 0;
    
    while (!g_cancel.load(std::memory_order_relaxed) && av_read_frame(ifmt, pkt) >= 0) {
        if (is_preview && pkt->pts != AV_NOPTS_VALUE) {
            double sec = pkt->pts * av_q2d(ifmt->streams[pkt->stream_index]->time_base);
            if (sec > 5.0) { av_packet_unref(pkt); break; }
        }

        if (pkt->stream_index == vidx) {
            avcodec_send_packet(vctx, pkt);
            while (avcodec_receive_frame(vctx, dec_frm) == 0) {
                av_frame_make_writable(enc_frm);
                sws_scale(sws, (const uint8_t* const*)dec_frm->data, dec_frm->linesize,
                          0, vctx->height, enc_frm->data, enc_frm->linesize);
                
                // --- PİKSEL MODİFİKASYONLARI (SIFIR EK YÜK, DOĞRUDAN BELLEK) ---
                if (do_inv) {
                    for (int y = 0; y < vctx->height; y++) {
                        uint8_t* p = enc_frm->data[0] + y * enc_frm->linesize[0];
                        for (int x = 0; x < vctx->width; x++) p[x] = 255 - p[x];
                    }
                    int uv_h = (enc_frm->height + 1) / 2;
                    int uv_w = (enc_frm->width + 1) / 2;
                    for (int y = 0; y < uv_h; y++) {
                        uint8_t* pu = enc_frm->data[1] + y * enc_frm->linesize[1];
                        uint8_t* pv = enc_frm->data[2] + y * enc_frm->linesize[2];
                        for (int x = 0; x < uv_w; x++) { pu[x] = 255 - pu[x]; pv[x] = 255 - pv[x]; }
                    }
                }
                
                if (do_gray) {
                    int uv_h = (enc_frm->height + 1) / 2;
                    memset(enc_frm->data[1], 128, (size_t)enc_frm->linesize[1] * (size_t)uv_h);
                    memset(enc_frm->data[2], 128, (size_t)enc_frm->linesize[2] * (size_t)uv_h);
                }
                // ----------------------------------------------------------------

                enc_frm->pts = frame_num++;
                avcodec_send_frame(venc_ctx, enc_frm);
                while (avcodec_receive_packet(venc_ctx, opkt) == 0) {
                    opkt->stream_index = vst->index;
                    av_packet_rescale_ts(opkt, venc_ctx->time_base, vst->time_base);
                    av_interleaved_write_frame(ofmt, opkt);
                    av_packet_unref(opkt);
                }
                if (dur > 0 && dec_frm->best_effort_timestamp != AV_NOPTS_VALUE) {
                    int64_t pos = av_rescale_q(dec_frm->best_effort_timestamp,
                                               ifmt->streams[vidx]->time_base,
                                               AV_TIME_BASE_Q);
                    fire_cb(cb, last_pct, (int)(pos * 95 / dur));
                }
                av_frame_unref(dec_frm);
            }
        } else if (ast_idx >= 0 && aidx >= 0 && pkt->stream_index == aidx) {
            // ast_idx geçerli ise rm_aud = 0 (Sesi Silme kapalı) demektir. Ses yazılır.
            AVPacket* apkt = av_packet_clone(pkt);
            apkt->stream_index = ast_idx;
            av_packet_rescale_ts(apkt, ifmt->streams[aidx]->time_base, ofmt->streams[ast_idx]->time_base);
            apkt->pos = -1;
            av_interleaved_write_frame(ofmt, apkt);
            av_packet_free(&apkt);
        }
        av_packet_unref(pkt);
    }
    
    avcodec_send_frame(venc_ctx, nullptr);
    while (avcodec_receive_packet(venc_ctx, opkt) == 0) {
        opkt->stream_index = vst->index;
        av_packet_rescale_ts(opkt, venc_ctx->time_base, vst->time_base);
        av_interleaved_write_frame(ofmt, opkt);
        av_packet_unref(opkt);
    }
    
    av_write_trailer(ofmt);
    sws_freeContext(sws);
    av_frame_free(&dec_frm); av_frame_free(&enc_frm);
    av_packet_free(&pkt); av_packet_free(&opkt);
    avcodec_free_context(&vctx); avcodec_free_context(&venc_ctx);
    if (!(ofmt->oformat->flags & AVFMT_NOFILE)) avio_closep(&ofmt->pb);
    avformat_free_context(ofmt);
    avformat_close_input(&ifmt);
    fire_cb(cb, last_pct, 100);
    return g_cancel.load() ? -99 : 0;
}

static uint8_t* load_image_ff(const char* path, int* w, int* h, int* ch);
static int convert_audio_to_video(const char* in, const char* out, const char* cover,
                                   float speed, float pitch, int effect,
                                   int change_freq, int new_freq, int is_preview, ProgressCB cb) {
    int last_pct = -1; fire_cb(cb, last_pct, 2);
    std::vector<int16_t> all;
    int in_ch = 1, in_sr = 44100;
    if (decode_audio_to_pcm(in, all, in_ch, in_sr, cb, 25, is_preview) < 0) return -1;
    if (g_cancel.load()) return -99;
    apply_dsp(all, in_ch, in_sr, speed, effect);
    fire_cb(cb, last_pct, 30);
    int out_sr = in_sr;
    if (fabsf(pitch) > 0.001f) out_sr = audio_calc_pitch_rate(in_sr, pitch);
    else if (change_freq && new_freq > 0) out_sr = new_freq;
    int img_w = 0, img_h = 0, img_ch = 0;
    uint8_t* cover_px = load_image_ff(cover, &img_w, &img_h, &img_ch);
    if (!cover_px) { set_err("Kapak resmi yüklenemedi: %s", cover); return -1; }
    img_w = img_w & ~1; img_h = img_h & ~1;
    if (img_w < 2) img_w = 2;
    if (img_h < 2) img_h = 2;
    fire_cb(cb, last_pct, 38);
    AVFormatContext* ofmt = nullptr;
    if (avformat_alloc_output_context2(&ofmt, nullptr, nullptr, out) < 0) {
        free(cover_px); set_err("Çıkış oluşturulamadı: %s", out); return -1;
    }
    const AVCodec* venc = avcodec_find_encoder_by_name("libx264");
    if (!venc) venc = avcodec_find_encoder(AV_CODEC_ID_H264);
    if (!venc) venc = avcodec_find_encoder(AV_CODEC_ID_MPEG4);
    if (!venc) { free(cover_px); avformat_free_context(ofmt); set_err("Video encoder bulunamadı"); return -1; }
    AVStream* vst  = avformat_new_stream(ofmt, nullptr);
    AVCodecContext* vctx = avcodec_alloc_context3(venc);
    vctx->width        = img_w;
    vctx->height       = img_h;
    vctx->pix_fmt      = AV_PIX_FMT_YUV420P;
    vctx->time_base    = {1, 1};
    vctx->framerate    = {1, 1};
    vctx->thread_count = 2;
    vctx->gop_size     = 1;
    av_opt_set(vctx->priv_data, "preset", "ultrafast", 0);
    av_opt_set(vctx->priv_data, "crf",    "28",        0);
    av_opt_set(vctx->priv_data, "tune",   "stillimage",0);
    if (ofmt->oformat->flags & AVFMT_GLOBALHEADER) vctx->flags |= AV_CODEC_FLAG_GLOBAL_HEADER;
    if (avcodec_open2(vctx, venc, nullptr) < 0) {
        free(cover_px); avcodec_free_context(&vctx); avformat_free_context(ofmt);
        set_err("Video encoder açılamadı"); return -1;
    }
    avcodec_parameters_from_context(vst->codecpar, vctx);
    vst->time_base = {1, 1};
    const AVCodec* aenc = avcodec_find_encoder_by_name("aac");
    if (!aenc) aenc = avcodec_find_encoder(AV_CODEC_ID_AAC);
    if (!aenc) { free(cover_px); avcodec_free_context(&vctx); avformat_free_context(ofmt); set_err("AAC encoder bulunamadı"); return -1; }
    AVStream* ast  = avformat_new_stream(ofmt, nullptr);
    AVCodecContext* actx = avcodec_alloc_context3(aenc);
    actx->sample_rate = out_sr;
    actx->bit_rate    = 192000;
    actx->sample_fmt  = aenc->sample_fmts ? aenc->sample_fmts[0] : AV_SAMPLE_FMT_FLTP;
    set_ch_layout(actx, in_ch);
    if (ofmt->oformat->flags & AVFMT_GLOBALHEADER) actx->flags |= AV_CODEC_FLAG_GLOBAL_HEADER;
    avcodec_open2(actx, aenc, nullptr);
    avcodec_parameters_from_context(ast->codecpar, actx);
    ast->time_base = {1, out_sr};
    if (!(ofmt->oformat->flags & AVFMT_NOFILE)) avio_open(&ofmt->pb, out, AVIO_FLAG_WRITE);
    if (avformat_write_header(ofmt, nullptr) < 0) {
        free(cover_px);
        avcodec_free_context(&vctx); avcodec_free_context(&actx);
        if (!(ofmt->oformat->flags & AVFMT_NOFILE)) avio_closep(&ofmt->pb);
        avformat_free_context(ofmt);
        set_err("Ses→Video başlık yazılamadı: %s", out); return -1;
    }

    AVFrame* base_cover = av_frame_alloc();
    base_cover->format = AV_PIX_FMT_YUV420P;
    base_cover->width  = img_w;
    base_cover->height = img_h;
    av_frame_get_buffer(base_cover, 0);

    SwsContext* sws = sws_getContext(img_w, img_h, AV_PIX_FMT_RGB24,
                                     img_w, img_h, AV_PIX_FMT_YUV420P,
                                     SWS_FAST_BILINEAR, nullptr, nullptr, nullptr);
    
    const uint8_t* sp[1] = {cover_px};
    int ss[1] = {img_w * 3};
    sws_scale(sws, sp, ss, 0, img_h, base_cover->data, base_cover->linesize);
    sws_freeContext(sws);
    free(cover_px);

    AVFrame* cover_frm = av_frame_alloc();
    cover_frm->format = AV_PIX_FMT_YUV420P;
    cover_frm->width  = img_w;
    cover_frm->height = img_h;
    av_frame_get_buffer(cover_frm, 0);

    int total_s   = (int)all.size();
    double aud_sec = (double)total_s / (double)(in_ch * out_sr);
    int64_t total_vid_frames = (int64_t)(aud_sec) + 2;
    AVChannelLayout src_chl = in_ch == 1 ? (AVChannelLayout)AV_CHANNEL_LAYOUT_MONO
                                         : (AVChannelLayout)AV_CHANNEL_LAYOUT_STEREO;
    SwrContext* swr2 = nullptr;
    if (actx->sample_fmt != AV_SAMPLE_FMT_S16) {
        AVChannelLayout dst_chl; av_channel_layout_copy(&dst_chl, &actx->ch_layout);
        swr_alloc_set_opts2(&swr2, &dst_chl, actx->sample_fmt, out_sr,
                            &src_chl, AV_SAMPLE_FMT_S16, out_sr, 0, nullptr);
        swr_init(swr2);
    }
    int frame_size = actx->frame_size > 0 ? actx->frame_size : 1024;
    AVFrame* afrm = av_frame_alloc();
    afrm->nb_samples  = frame_size;
    afrm->format      = actx->sample_fmt;
    afrm->sample_rate = out_sr;
    av_channel_layout_copy(&afrm->ch_layout, &actx->ch_layout);
    av_frame_get_buffer(afrm, 0);
    AVPacket* epkt = av_packet_alloc();
    int    a_offset = 0;
    int64_t a_pts   = 0;
    int64_t v_pts   = 0;
    
    while (!g_cancel.load(std::memory_order_relaxed) && a_offset < total_s) {
        double cur_sec = (double)a_pts / (double)out_sr;
        if (is_preview && cur_sec >= 5.0) break;

        while (v_pts <= (int64_t)cur_sec && v_pts < total_vid_frames) {
            {
                for (int y = 0; y < img_h; y++) {
                    memcpy(cover_frm->data[0] + y * cover_frm->linesize[0],
                           base_cover->data[0] + y * base_cover->linesize[0],
                           (size_t)img_w);
                }
                int uv_h = img_h / 2;
                for (int y = 0; y < uv_h; y++) {
                    memcpy(cover_frm->data[1] + y * cover_frm->linesize[1],
                           base_cover->data[1] + y * base_cover->linesize[1],
                           (size_t)(img_w / 2));
                    memcpy(cover_frm->data[2] + y * cover_frm->linesize[2],
                           base_cover->data[2] + y * base_cover->linesize[2],
                           (size_t)(img_w / 2));
                }
            }
            cover_frm->pts = v_pts++;
            avcodec_send_frame(vctx, cover_frm);
            while (avcodec_receive_packet(vctx, epkt) == 0) {
                epkt->stream_index = vst->index;
                av_packet_rescale_ts(epkt, vctx->time_base, vst->time_base);
                av_interleaved_write_frame(ofmt, epkt);
                av_packet_unref(epkt);
            }
        }
        int avail = (total_s - a_offset) / in_ch;
        int ns    = avail < frame_size ? avail : frame_size;
        afrm->nb_samples = ns;
        av_frame_make_writable(afrm);
        if (swr2) {
            const uint8_t* s2 = (const uint8_t*)(all.data() + a_offset);
            swr_convert(swr2, (uint8_t**)afrm->data, ns, &s2, ns);
        } else {
            memcpy(afrm->data[0], all.data() + a_offset, (size_t)ns * (size_t)in_ch * 2);
        }
        afrm->pts = a_pts; a_pts += ns; a_offset += ns * in_ch;
        avcodec_send_frame(actx, afrm);
        while (avcodec_receive_packet(actx, epkt) == 0) {
            epkt->stream_index = ast->index;
            av_packet_rescale_ts(epkt, actx->time_base, ast->time_base);
            av_interleaved_write_frame(ofmt, epkt);
            av_packet_unref(epkt);
        }
        fire_cb(cb, last_pct, 40 + (int)((float)a_offset / (float)total_s * 55.0f));
    }
    
    if (!is_preview) {
        while (v_pts < total_vid_frames) {
            {
                for (int y = 0; y < img_h; y++) {
                    memcpy(cover_frm->data[0] + y * cover_frm->linesize[0],
                           base_cover->data[0] + y * base_cover->linesize[0],
                           (size_t)img_w);
                }
                int uv_h = img_h / 2;
                for (int y = 0; y < uv_h; y++) {
                    memcpy(cover_frm->data[1] + y * cover_frm->linesize[1],
                           base_cover->data[1] + y * base_cover->linesize[1],
                           (size_t)(img_w / 2));
                    memcpy(cover_frm->data[2] + y * cover_frm->linesize[2],
                           base_cover->data[2] + y * base_cover->linesize[2],
                           (size_t)(img_w / 2));
                }
            }
            cover_frm->pts = v_pts++;
            avcodec_send_frame(vctx, cover_frm);
            while (avcodec_receive_packet(vctx, epkt) == 0) {
                epkt->stream_index = vst->index;
                av_packet_rescale_ts(epkt, vctx->time_base, vst->time_base);
                av_interleaved_write_frame(ofmt, epkt);
                av_packet_unref(epkt);
            }
        }
    }
    
    avcodec_send_frame(vctx, nullptr);
    while (avcodec_receive_packet(vctx, epkt) == 0) {
        epkt->stream_index = vst->index;
        av_packet_rescale_ts(epkt, vctx->time_base, vst->time_base);
        av_interleaved_write_frame(ofmt, epkt);
        av_packet_unref(epkt);
    }
    avcodec_send_frame(actx, nullptr);
    while (avcodec_receive_packet(actx, epkt) == 0) {
        epkt->stream_index = ast->index;
        av_packet_rescale_ts(epkt, actx->time_base, ast->time_base);
        av_interleaved_write_frame(ofmt, epkt);
        av_packet_unref(epkt);
    }
    av_write_trailer(ofmt);
    if (swr2) swr_free(&swr2);
    
    av_frame_free(&base_cover);
    av_frame_free(&cover_frm); 
    av_frame_free(&afrm); 
    av_packet_free(&epkt);
    
    avcodec_free_context(&vctx); avcodec_free_context(&actx);
    if (!(ofmt->oformat->flags & AVFMT_NOFILE)) avio_closep(&ofmt->pb);
    avformat_free_context(ofmt);
    fire_cb(cb, last_pct, 100);
    return g_cancel.load() ? -99 : 0;
}
static uint8_t* load_image_ff(const char* path, int* w, int* h, int* ch) {
    AVFormatContext* fmt = nullptr;
    if (avformat_open_input(&fmt, path, nullptr, nullptr) < 0) return nullptr;
    avformat_find_stream_info(fmt, nullptr);
    int idx = -1;
    for (unsigned i = 0; i < fmt->nb_streams; i++) {
        if (fmt->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) { idx = (int)i; break; }
    }
    if (idx < 0) { avformat_close_input(&fmt); return nullptr; }
    const AVCodec* dec = avcodec_find_decoder(fmt->streams[idx]->codecpar->codec_id);
    if (!dec) { avformat_close_input(&fmt); return nullptr; }
    AVCodecContext* ctx = avcodec_alloc_context3(dec);
    avcodec_parameters_to_context(ctx, fmt->streams[idx]->codecpar);
    ctx->thread_count = 1;
    avcodec_open2(ctx, dec, nullptr);
    AVPacket* pkt    = av_packet_alloc();
    AVFrame* frm    = av_frame_alloc();
    uint8_t* pixels = nullptr;
    auto extract_frame = [&]() {
        if (!pixels) {
            *w = frm->width; *h = frm->height; *ch = 3;
            pixels = (uint8_t*)malloc((size_t)(*w) * (size_t)(*h) * 3);
            if (pixels) {
                SwsContext* sws = sws_getContext(frm->width, frm->height, (AVPixelFormat)frm->format,
                                                 frm->width, frm->height, AV_PIX_FMT_RGB24,
                                                 SWS_FAST_BILINEAR, nullptr, nullptr, nullptr);
                int ls[4]; uint8_t* dp[4];
                av_image_fill_arrays(dp, ls, pixels, AV_PIX_FMT_RGB24, *w, *h, 1);
                sws_scale(sws, frm->data, frm->linesize, 0, frm->height, dp, ls);
                sws_freeContext(sws);
            }
        }
    };
    while (av_read_frame(fmt, pkt) >= 0) {
        if (pkt->stream_index == idx) {
            avcodec_send_packet(ctx, pkt);
            while (avcodec_receive_frame(ctx, frm) == 0) {
                extract_frame();
                av_frame_unref(frm);
            }
        }
        av_packet_unref(pkt);
    }
    avcodec_send_packet(ctx, nullptr);
    while (avcodec_receive_frame(ctx, frm) == 0) {
        extract_frame();
        av_frame_unref(frm);
    }
    av_frame_free(&frm); av_packet_free(&pkt);
    avcodec_free_context(&ctx); avformat_close_input(&fmt);
    return pixels;
}
static int save_image_ff(const uint8_t* rgb, int w, int h, const char* out_path) {
    std::string op(out_path);
    auto ends = [&](const char* s) {
        size_t sl = strlen(s);
        return op.size() >= sl && op.compare(op.size() - sl, sl, s) == 0;
    };
    AVCodecID cid = AV_CODEC_ID_MJPEG;
    if      (ends(".png"))  cid = AV_CODEC_ID_PNG;
    else if (ends(".bmp"))  cid = AV_CODEC_ID_BMP;
    else if (ends(".webp")) cid = AV_CODEC_ID_WEBP;
    const AVCodec* enc = avcodec_find_encoder(cid);
    if (!enc) { set_err("Resim encoder bulunamadı"); return -1; }
    AVPixelFormat pix_enc = AV_PIX_FMT_YUVJ420P;
    if (enc->pix_fmts) pix_enc = enc->pix_fmts[0];
    else {
        if      (cid == AV_CODEC_ID_PNG)  pix_enc = AV_PIX_FMT_RGB24;
        else if (cid == AV_CODEC_ID_BMP)  pix_enc = AV_PIX_FMT_BGR24;
        else if (cid == AV_CODEC_ID_WEBP) pix_enc = AV_PIX_FMT_YUV420P;
    }
    AVCodecContext* ctx = avcodec_alloc_context3(enc);
    ctx->width = w; ctx->height = h; ctx->pix_fmt = pix_enc;
    ctx->time_base = {1, 25};
    ctx->thread_count = 1;
    if (cid == AV_CODEC_ID_MJPEG) {
        ctx->flags |= AV_CODEC_FLAG_QSCALE;
        ctx->global_quality = FF_QP2LAMBDA * 3;
    }
    if (avcodec_open2(ctx, enc, nullptr) < 0) {
        avcodec_free_context(&ctx); set_err("Resim encoder açılamadı"); return -1;
    }
    AVFrame* frm = av_frame_alloc();
    frm->format = pix_enc; frm->width = w; frm->height = h;
    av_frame_get_buffer(frm, 1);
    av_frame_make_writable(frm);
    SwsContext* sws = sws_getContext(w, h, AV_PIX_FMT_RGB24, w, h, pix_enc,
                                     SWS_FAST_BILINEAR, nullptr, nullptr, nullptr);
    const uint8_t* src[1] = {rgb};
    int src_ls[1] = {w * 3};
    sws_scale(sws, src, src_ls, 0, h, frm->data, frm->linesize);
    sws_freeContext(sws);
    frm->pts = 0;
    AVPacket* pkt = av_packet_alloc();
    avcodec_send_frame(ctx, frm);
    avcodec_send_frame(ctx, nullptr);
    int ret = -1;
    FILE* f = fopen(out_path, "wb");
    if (f) {
        while (avcodec_receive_packet(ctx, pkt) == 0) {
            if (fwrite(pkt->data, 1, (size_t)pkt->size, f) == (size_t)pkt->size) ret = 0;
            else { set_err("Yazma hatası: %s", out_path); ret = -1; }
            av_packet_unref(pkt);
        }
        fclose(f);
        if (ret != 0 && g_err[0] == '\0') set_err("Resim encode başarısız");
    } else { set_err("Açılamadı: %s", out_path); }
    av_packet_free(&pkt); av_frame_free(&frm); avcodec_free_context(&ctx);
    return ret;
}
EXPORT void image_invert(uint8_t* px, int w, int h, int ch) {
    int t = w * h;
    for (int p = 0; p < t; p++) {
        uint8_t* x = px + p * ch;
        int lim = ch == 4 ? 3 : ch;
        for (int c = 0; c < lim; c++) x[c] = (uint8_t)(255 - x[c]);
    }
}
EXPORT void image_grayscale(uint8_t* px, int w, int h, int ch) {
    int t = w * h;
    for (int p = 0; p < t; p++) {
        uint8_t* x = px + p * ch;
        uint8_t g = (uint8_t)(0.299f * x[0] + 0.587f * x[1] + 0.114f * x[2]);
        x[0] = x[1] = x[2] = g;
    }
}
EXPORT void image_resize_bilinear(const uint8_t* src, int sw, int sh,
                                   uint8_t* dst, int dw, int dh, int ch) {
    float sx = (float)sw / (float)dw, sy = (float)sh / (float)dh;
    for (int y = 0; y < dh; y++) {
        float fy = (float)y * sy;
        int y0 = (int)fy, y1 = y0 + 1 < sh ? y0 + 1 : sh - 1;
        float wy = fy - (float)y0;
        for (int x = 0; x < dw; x++) {
            float fx = (float)x * sx;
            int x0 = (int)fx, x1 = x0 + 1 < sw ? x0 + 1 : sw - 1;
            float wx = fx - (float)x0;
            for (int c = 0; c < ch; c++) {
                float v = src[(y0*sw+x0)*ch+c]*(1.0f-wx)*(1.0f-wy)
                        + src[(y0*sw+x1)*ch+c]*wx*(1.0f-wy)
                        + src[(y1*sw+x0)*ch+c]*(1.0f-wx)*wy
                        + src[(y1*sw+x1)*ch+c]*wx*wy;
                dst[(y*dw+x)*ch+c] = (uint8_t)(v < 0.0f ? 0 : v > 255.0f ? 255 : v);
            }
        }
    }
}
EXPORT void pdf_process_pixels(uint8_t* px, int w, int h, int ch, int do_inv, int do_gray) {
    int t = w * h;
    for (int p = 0; p < t; p++) {
        uint8_t* x = px + p * ch;
        if (do_gray) {
            uint8_t g = (uint8_t)(0.299f*x[0] + 0.587f*x[1] + 0.114f*x[2]);
            x[0] = x[1] = x[2] = g;
        }
        if (do_inv) {
            x[0] = (uint8_t)(255-x[0]);
            x[1] = (uint8_t)(255-x[1]);
            x[2] = (uint8_t)(255-x[2]);
        }
    }
}

static int convert_pdf(const char*, const char*, int, int, bool, ProgressCB) {
    set_err("MUPDF_NOT_LINKED");
    return -2;
}

// ===================== ANA FONKSİYON (GÜNCELLENDİ) =====================
EXPORT int kavram_convert(
    const char* input_path, const char* output_path, const char* cover_path,
    int   mode, float speed, float pitch_semitones, int   effect_index,
    int   change_freq, int   new_freq, int   pdf_invert, int   pdf_gray,
    int   img_invert, int   img_gray, int   img_scale_idx, 
    int   vid_invert, int   vid_rm_aud,
    int   is_preview, ProgressCB progress_cb)
{
    g_err[0] = '\0';
    g_cancel.store(false, std::memory_order_relaxed);
#ifdef __linux__
    setpriority(PRIO_PROCESS, 0, 8);
#endif
    if (mode == 3) {
        int w, h, ch;
        uint8_t* px = load_image_ff(input_path, &w, &h, &ch);
        if (!px) { set_err("Resim yüklenemedi: %s", input_path); return -1; }
        static const float scale_map[] = {0.25f,0.35f,0.50f,0.65f,0.80f,1.00f,1.25f,1.50f,1.75f,2.00f,2.50f};
        int si = img_scale_idx < 0 ? 5 : img_scale_idx > 10 ? 10 : img_scale_idx;
        float sc = scale_map[si];
        int last_pct = -1;
        fire_cb(progress_cb, last_pct, 20);
        if (fabsf(sc - 1.0f) > 0.001f) {
            int nw = (int)((float)w * sc), nh = (int)((float)h * sc);
            if (nw < 1) nw = 1; if (nh < 1) nh = 1;
            uint8_t* npx = (uint8_t*)malloc((size_t)nw * (size_t)nh * (size_t)ch);
            if (!npx) { free(px); set_err("Bellek yetersiz"); return -1; }
            image_resize_bilinear(px, w, h, npx, nw, nh, ch);
            free(px); px = npx; w = nw; h = nh;
        }
        fire_cb(progress_cb, last_pct, 50);
        if (img_gray)   image_grayscale(px, w, h, ch);
        if (img_invert) image_invert   (px, w, h, ch);
        fire_cb(progress_cb, last_pct, 75);
        std::string op(output_path);
        bool to_pdf = op.size() >= 4 && op.compare(op.size()-4, 4, ".pdf") == 0;
        if (to_pdf) {
            set_err("IMAGE_TO_PDF_NEEDS_PYTHON_FALLBACK");
            return -3;
        } else {
            int r = save_image_ff(px, w, h, output_path);
            free(px);
            fire_cb(progress_cb, last_pct, 100);
            return r;
        }
    }
    if (mode == 4) {
        std::string op(output_path);
        bool to_txt = op.size() >= 4 && op.compare(op.size()-4, 4, ".txt") == 0;
        return convert_pdf(input_path, output_path, pdf_invert, pdf_gray, to_txt, progress_cb);
    }
    
    if (mode == 0) return convert_audio(input_path, output_path, speed, pitch_semitones, effect_index, change_freq, new_freq, is_preview, progress_cb);
    if (mode == 1) return (img_gray || vid_invert) ? convert_video_fx(input_path, output_path, img_gray, vid_invert, vid_rm_aud, is_preview, progress_cb) : convert_video_remux(input_path, output_path, vid_rm_aud, is_preview, progress_cb);
    if (mode == 2) return convert_audio_to_video(input_path, output_path, cover_path, speed, pitch_semitones, effect_index, change_freq, new_freq, is_preview, progress_cb);
    set_err("Bilinmeyen mod: %d", mode);
    return -1;
}
