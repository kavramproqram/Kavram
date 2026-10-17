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
#include <cmath>      // std::abs, std::sqrt, std::pow, M_PI
#include <algorithm>  // std::min/max
#include <stdexcept>
#include <numeric>
#include <fstream>
#include <sstream>
#include <chrono>
#include <ctime>
#include <iomanip>
#include <filesystem>
#include <atomic>
#include <mutex>
#include <shared_mutex>
#include <functional>
#include <new>
#include <cstdint>
#include <cstring>

#ifdef _WIN32
#include <process.h>
#else
#include <unistd.h>
#endif

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// libsndfile (ses dosyası okuma/yazma)
#include <sndfile.h>

// PortAudio (oynatma / mikrofon)
// Arch Linux: sudo pacman -S portaudio libsndfile zlib
#include <portaudio.h>

// zlib (.sound paketi = zip kapsayıcı; deflate/inflate + crc32)
#include <zlib.h>

namespace fs = std::filesystem;

// =====================================================================
//  .SOUND PAKETİ (ZIP + metadata.json) — TAMAMEN C++ TARAFINDA
//
//  Paket biçimi (eski Python sürümüyle birebir uyumlu):
//      audio.wav       -> ses verisi
//      metadata.json   -> {"text": ..., "alignment_center": ..., "font_size": ...}
//
//  Python artık zip/json/tempfile ile uğraşmaz; yalnızca yol ve metin verir.
// =====================================================================
namespace pkg {

static inline void put16(std::string& s, uint16_t v) {
    s.push_back(static_cast<char>(v & 0xFF));
    s.push_back(static_cast<char>((v >> 8) & 0xFF));
}
static inline void put32(std::string& s, uint32_t v) {
    for (int i = 0; i < 4; ++i) s.push_back(static_cast<char>((v >> (8 * i)) & 0xFF));
}
static inline uint16_t get16(const unsigned char* p) {
    return static_cast<uint16_t>(p[0] | (p[1] << 8));
}
static inline uint32_t get32(const unsigned char* p) {
    return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) |
           (static_cast<uint32_t>(p[2]) << 16) | (static_cast<uint32_t>(p[3]) << 24);
}

static void dos_datetime(uint16_t& dtime, uint16_t& ddate) {
    std::time_t t = std::time(nullptr);
    std::tm tmv{};
#if defined(_WIN32)
    localtime_s(&tmv, &t);
#else
    localtime_r(&t, &tmv);
#endif
    int year = tmv.tm_year + 1900;
    if (year < 1980) year = 1980;
    dtime = static_cast<uint16_t>((tmv.tm_hour << 11) | (tmv.tm_min << 5) | (tmv.tm_sec / 2));
    ddate = static_cast<uint16_t>(((year - 1980) << 9) | ((tmv.tm_mon + 1) << 5) | tmv.tm_mday);
}

// ---------------------------------------------------------------------
//  ZIP YAZICI (akışlı deflate; büyük WAV'lar belleği şişirmez)
// ---------------------------------------------------------------------
class ZipWriter {
public:
    // Kaynak: okunan bayt sayısı; 0 = dosya sonu; <0 = hata
    using Source = std::function<std::ptrdiff_t(unsigned char*, size_t)>;

    bool open(const std::string& path, std::string& err) {
        out_.open(path, std::ios::binary | std::ios::trunc);
        if (!out_) { err = "Cannot create package file: " + path; return false; }
        return true;
    }

    bool add(const std::string& name, const Source& src, std::string& err) {
        Rec r;
        r.name = name;
        dos_datetime(r.dtime, r.ddate);

        std::streamoff off = out_.tellp();
        if (off < 0 || static_cast<uint64_t>(off) > 0xFFFFFFF0ull) {
            err = "Package too large for classic ZIP format.";
            return false;
        }
        r.offset = static_cast<uint32_t>(off);

        std::string hdr;
        put32(hdr, 0x04034b50);
        put16(hdr, 20);          // version needed
        put16(hdr, 0);           // flags
        put16(hdr, 8);           // deflate
        put16(hdr, r.dtime);
        put16(hdr, r.ddate);
        put32(hdr, 0);           // crc  (sonradan yamalanacak)
        put32(hdr, 0);           // csize
        put32(hdr, 0);           // usize
        put16(hdr, static_cast<uint16_t>(name.size()));
        put16(hdr, 0);           // extra
        hdr += name;
        out_.write(hdr.data(), static_cast<std::streamsize>(hdr.size()));
        if (!out_) { err = "Write error while creating package."; return false; }

        z_stream zs{};
        if (deflateInit2(&zs, 1, Z_DEFLATED, -MAX_WBITS, 8, Z_DEFAULT_STRATEGY) != Z_OK) {
            err = "zlib deflate initialisation failed.";
            return false;
        }

        std::vector<unsigned char> in(1 << 16), outb(1 << 16);
        uint64_t total_in = 0, total_out = 0;
        uLong crc = crc32(0L, Z_NULL, 0);
        bool ok = true;

        for (;;) {
            std::ptrdiff_t n = src(in.data(), in.size());
            if (n < 0) { err = "Read error while creating package."; ok = false; break; }
            const bool eof = (n == 0);
            if (n > 0) crc = crc32(crc, in.data(), static_cast<uInt>(n));
            total_in += static_cast<uint64_t>(n);

            zs.next_in = in.data();
            zs.avail_in = static_cast<uInt>(n);
            const int flush = eof ? Z_FINISH : Z_NO_FLUSH;
            do {
                zs.next_out = outb.data();
                zs.avail_out = static_cast<uInt>(outb.size());
                int ret = deflate(&zs, flush);
                if (ret == Z_STREAM_ERROR) { err = "zlib deflate error."; ok = false; break; }
                size_t have = outb.size() - zs.avail_out;
                if (have) {
                    out_.write(reinterpret_cast<const char*>(outb.data()), static_cast<std::streamsize>(have));
                    total_out += have;
                    if (!out_) { err = "Write error while creating package."; ok = false; break; }
                }
            } while (zs.avail_out == 0);
            if (!ok || eof) break;
            if (total_in > 0xFFFFFFF0ull || total_out > 0xFFFFFFF0ull) {
                err = "Package too large for classic ZIP format.";
                ok = false;
                break;
            }
        }
        deflateEnd(&zs);
        if (!ok) return false;
        if (total_in > 0xFFFFFFF0ull || total_out > 0xFFFFFFF0ull) {
            err = "Package too large for classic ZIP format.";
            return false;
        }

        r.crc = static_cast<uint32_t>(crc);
        r.csize = static_cast<uint32_t>(total_out);
        r.usize = static_cast<uint32_t>(total_in);

        // Yerel başlığı gerçek crc/boyutlarla yamala
        std::streamoff end_pos = out_.tellp();
        std::string patch;
        put32(patch, r.crc);
        put32(patch, r.csize);
        put32(patch, r.usize);
        out_.seekp(static_cast<std::streamoff>(r.offset) + 14);
        out_.write(patch.data(), static_cast<std::streamsize>(patch.size()));
        out_.seekp(end_pos);
        if (!out_) { err = "Write error while finalising package entry."; return false; }

        entries_.push_back(r);
        return true;
    }

    bool add_buffer(const std::string& name, const std::string& data, std::string& err) {
        size_t pos = 0;
        Source src = [&](unsigned char* dst, size_t cap) -> std::ptrdiff_t {
            size_t n = std::min(cap, data.size() - pos);
            if (n) std::memcpy(dst, data.data() + pos, n);
            pos += n;
            return static_cast<std::ptrdiff_t>(n);
        };
        return add(name, src, err);
    }

    bool add_file(const std::string& name, const std::string& path, std::string& err) {
        std::ifstream f(path, std::ios::binary);
        if (!f) { err = "Cannot read temporary audio file: " + path; return false; }
        Source src = [&](unsigned char* dst, size_t cap) -> std::ptrdiff_t {
            f.read(reinterpret_cast<char*>(dst), static_cast<std::streamsize>(cap));
            if (f.bad()) return -1;
            return static_cast<std::ptrdiff_t>(f.gcount());
        };
        return add(name, src, err);
    }

    bool finish(std::string& err) {
        std::streamoff cd_off = out_.tellp();
        if (cd_off < 0 || static_cast<uint64_t>(cd_off) > 0xFFFFFFF0ull || entries_.size() >= 0xFFFF) {
            err = "Package too large for classic ZIP format.";
            return false;
        }
        std::string cd;
        for (const auto& r : entries_) {
            put32(cd, 0x02014b50);
            put16(cd, 20);   // version made by
            put16(cd, 20);   // version needed
            put16(cd, 0);    // flags
            put16(cd, 8);    // method
            put16(cd, r.dtime);
            put16(cd, r.ddate);
            put32(cd, r.crc);
            put32(cd, r.csize);
            put32(cd, r.usize);
            put16(cd, static_cast<uint16_t>(r.name.size()));
            put16(cd, 0);    // extra
            put16(cd, 0);    // comment
            put16(cd, 0);    // disk start
            put16(cd, 0);    // internal attrs
            put32(cd, 0);    // external attrs
            put32(cd, r.offset);
            cd += r.name;
        }
        std::string eocd;
        put32(eocd, 0x06054b50);
        put16(eocd, 0);
        put16(eocd, 0);
        put16(eocd, static_cast<uint16_t>(entries_.size()));
        put16(eocd, static_cast<uint16_t>(entries_.size()));
        put32(eocd, static_cast<uint32_t>(cd.size()));
        put32(eocd, static_cast<uint32_t>(cd_off));
        put16(eocd, 0);

        out_.write(cd.data(), static_cast<std::streamsize>(cd.size()));
        out_.write(eocd.data(), static_cast<std::streamsize>(eocd.size()));
        out_.flush();
        if (!out_) { err = "Write error while finalising package."; return false; }
        out_.close();
        return true;
    }

private:
    struct Rec {
        std::string name;
        uint32_t crc = 0, csize = 0, usize = 0, offset = 0;
        uint16_t dtime = 0, ddate = 0;
    };
    std::ofstream out_;
    std::vector<Rec> entries_;
};

// ---------------------------------------------------------------------
//  ZIP OKUYUCU (stored + deflate; CRC ve boyut doğrulamalı)
// ---------------------------------------------------------------------
class ZipReader {
public:
    struct Entry {
        std::string name;
        uint16_t flags = 0, method = 0;
        uint32_t crc = 0, csize = 0, usize = 0, local_off = 0;
    };
    using Sink = std::function<bool(const unsigned char*, size_t)>;

    bool open(const std::string& path, std::string& err) {
        in_.open(path, std::ios::binary);
        if (!in_) { err = "Cannot open package: " + path; return false; }
        in_.seekg(0, std::ios::end);
        std::streamoff sz = in_.tellg();
        if (sz < 22) { err = "Not a valid .sound package (file too small)."; return false; }
        file_size_ = static_cast<uint64_t>(sz);

        const size_t tail = static_cast<size_t>(std::min<uint64_t>(file_size_, 22u + 65535u));
        std::vector<unsigned char> buf(tail);
        in_.seekg(static_cast<std::streamoff>(file_size_ - tail));
        in_.read(reinterpret_cast<char*>(buf.data()), static_cast<std::streamsize>(tail));
        if (!in_) { err = "Cannot read package directory."; return false; }

        long eocd = -1;
        for (long i = static_cast<long>(tail) - 22; i >= 0; --i) {
            if (get32(&buf[static_cast<size_t>(i)]) == 0x06054b50) { eocd = i; break; }
        }
        if (eocd < 0) { err = "Not a valid .sound package (no ZIP directory)."; return false; }

        const unsigned char* e = &buf[static_cast<size_t>(eocd)];
        uint32_t n_entries = get16(e + 10);
        uint32_t cd_size = get32(e + 12);
        uint32_t cd_off = get32(e + 16);
        if (n_entries == 0xFFFF || cd_size == 0xFFFFFFFFu || cd_off == 0xFFFFFFFFu) {
            err = "ZIP64 packages are not supported.";
            return false;
        }
        if (static_cast<uint64_t>(cd_off) + cd_size > file_size_) {
            err = "Package directory is corrupt.";
            return false;
        }

        std::vector<unsigned char> cd(cd_size);
        in_.clear();
        in_.seekg(static_cast<std::streamoff>(cd_off));
        if (cd_size) in_.read(reinterpret_cast<char*>(cd.data()), static_cast<std::streamsize>(cd_size));
        if (!in_) { err = "Cannot read package directory."; return false; }

        size_t pos = 0;
        for (uint32_t i = 0; i < n_entries; ++i) {
            if (pos + 46 > cd.size() || get32(&cd[pos]) != 0x02014b50) {
                err = "Package directory is corrupt.";
                return false;
            }
            const unsigned char* p = &cd[pos];
            Entry en;
            en.flags = get16(p + 8);
            en.method = get16(p + 10);
            en.crc = get32(p + 16);
            en.csize = get32(p + 20);
            en.usize = get32(p + 24);
            uint16_t nl = get16(p + 28), el = get16(p + 30), cl = get16(p + 32);
            en.local_off = get32(p + 42);
            if (pos + 46 + nl + el + cl > cd.size()) {
                err = "Package directory is corrupt.";
                return false;
            }
            en.name.assign(reinterpret_cast<const char*>(p + 46), nl);
            entries_.push_back(std::move(en));
            pos += 46u + nl + el + cl;
        }
        return true;
    }

    const Entry* find(const std::string& name) const {
        for (const auto& e : entries_) if (e.name == name) return &e;
        return nullptr;
    }

    bool extract(const Entry& e, uint64_t max_size, const Sink& sink, std::string& err) {
        if (e.flags & 1) { err = "Encrypted packages are not supported."; return false; }
        if (e.method != 0 && e.method != 8) { err = "Unsupported ZIP compression method."; return false; }
        if (e.csize == 0xFFFFFFFFu || e.usize == 0xFFFFFFFFu) { err = "ZIP64 entries are not supported."; return false; }
        if (e.usize > max_size) { err = "Package entry '" + e.name + "' is too large."; return false; }

        unsigned char lh[30];
        in_.clear();
        in_.seekg(static_cast<std::streamoff>(e.local_off));
        in_.read(reinterpret_cast<char*>(lh), 30);
        if (!in_ || get32(lh) != 0x04034b50) { err = "Package entry header is corrupt."; return false; }
        uint64_t data_off = static_cast<uint64_t>(e.local_off) + 30u + get16(lh + 26) + get16(lh + 28);
        if (data_off + e.csize > file_size_) { err = "Package entry is truncated."; return false; }
        in_.seekg(static_cast<std::streamoff>(data_off));

        uLong crc = crc32(0L, Z_NULL, 0);
        uint64_t produced = 0;
        uint64_t remaining = e.csize;
        std::vector<unsigned char> inb(1 << 16), outb(1 << 16);

        if (e.method == 0) {
            if (e.csize != e.usize) { err = "Package entry size mismatch."; return false; }
            while (remaining > 0) {
                size_t n = static_cast<size_t>(std::min<uint64_t>(remaining, inb.size()));
                in_.read(reinterpret_cast<char*>(inb.data()), static_cast<std::streamsize>(n));
                if (!in_) { err = "Package entry is truncated."; return false; }
                crc = crc32(crc, inb.data(), static_cast<uInt>(n));
                produced += n;
                remaining -= n;
                if (!sink(inb.data(), n)) { err = "Write error while extracting package."; return false; }
            }
        } else {
            z_stream zs{};
            if (inflateInit2(&zs, -MAX_WBITS) != Z_OK) { err = "zlib inflate initialisation failed."; return false; }
            int ret = Z_OK;
            bool ok = true;
            while (ret != Z_STREAM_END && ok) {
                if (zs.avail_in == 0) {
                    if (remaining == 0) { err = "Package entry is truncated."; ok = false; break; }
                    size_t n = static_cast<size_t>(std::min<uint64_t>(remaining, inb.size()));
                    in_.read(reinterpret_cast<char*>(inb.data()), static_cast<std::streamsize>(n));
                    if (!in_) { err = "Package entry is truncated."; ok = false; break; }
                    zs.next_in = inb.data();
                    zs.avail_in = static_cast<uInt>(n);
                    remaining -= n;
                }
                do {
                    zs.next_out = outb.data();
                    zs.avail_out = static_cast<uInt>(outb.size());
                    ret = inflate(&zs, Z_NO_FLUSH);
                    if (ret != Z_OK && ret != Z_STREAM_END && ret != Z_BUF_ERROR) {
                        err = "Package entry is corrupt (inflate failed).";
                        ok = false;
                        break;
                    }
                    size_t have = outb.size() - zs.avail_out;
                    if (have) {
                        produced += have;
                        if (produced > e.usize) { err = "Package entry is corrupt (size overflow)."; ok = false; break; }
                        crc = crc32(crc, outb.data(), static_cast<uInt>(have));
                        if (!sink(outb.data(), have)) { err = "Write error while extracting package."; ok = false; break; }
                    }
                    if (ret == Z_BUF_ERROR && zs.avail_in == 0) break;
                } while (zs.avail_out == 0 && ret != Z_STREAM_END);
            }
            inflateEnd(&zs);
            if (!ok) return false;
        }

        if (produced != e.usize) { err = "Package entry size mismatch."; return false; }
        if (static_cast<uint32_t>(crc) != e.crc) { err = "Package entry failed its integrity check (CRC)."; return false; }
        return true;
    }

private:
    std::ifstream in_;
    uint64_t file_size_ = 0;
    std::vector<Entry> entries_;
};

// ---------------------------------------------------------------------
//  Minimal JSON (yalnızca metadata.json için; UTF-8 ve \uXXXX güvenli)
// ---------------------------------------------------------------------
struct PackageMeta {
    std::string text;
    bool alignment_center = false;
    int font_size = 14;
};

static void append_utf8(std::string& out, uint32_t cp) {
    if (cp < 0x80) out.push_back(static_cast<char>(cp));
    else if (cp < 0x800) {
        out.push_back(static_cast<char>(0xC0 | (cp >> 6)));
        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    } else if (cp < 0x10000) {
        out.push_back(static_cast<char>(0xE0 | (cp >> 12)));
        out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    } else {
        out.push_back(static_cast<char>(0xF0 | (cp >> 18)));
        out.push_back(static_cast<char>(0x80 | ((cp >> 12) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
        out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    }
}

static std::string json_escape(const char* s, size_t n) {
    std::string o;
    o.reserve(n + 16);
    for (size_t i = 0; i < n; ++i) {
        unsigned char c = static_cast<unsigned char>(s[i]);
        switch (c) {
            case '"':  o += "\\\""; break;
            case '\\': o += "\\\\"; break;
            case '\b': o += "\\b";  break;
            case '\f': o += "\\f";  break;
            case '\n': o += "\\n";  break;
            case '\r': o += "\\r";  break;
            case '\t': o += "\\t";  break;
            default:
                if (c < 0x20) {
                    char buf[8];
                    std::snprintf(buf, sizeof(buf), "\\u%04x", c);
                    o += buf;
                } else {
                    o.push_back(static_cast<char>(c)); // UTF-8 baytları olduğu gibi
                }
        }
    }
    return o;
}

static std::string build_metadata_json(const std::string& text, bool center, int font_size) {
    std::string j = "{\n";
    j += "    \"version\": 1,\n";
    j += "    \"text\": \"" + json_escape(text.data(), text.size()) + "\",\n";
    j += std::string("    \"alignment_center\": ") + (center ? "true" : "false") + ",\n";
    j += "    \"font_size\": " + std::to_string(font_size) + "\n";
    j += "}\n";
    return j;
}

class MiniJson {
public:
    explicit MiniJson(const std::string& s) : p_(s.data()), e_(s.data() + s.size()) {}

    bool parse_meta(PackageMeta& m) {
        if (e_ - p_ >= 3 && static_cast<unsigned char>(p_[0]) == 0xEF &&
            static_cast<unsigned char>(p_[1]) == 0xBB && static_cast<unsigned char>(p_[2]) == 0xBF) p_ += 3;
        ws();
        if (!eat('{')) return false;
        ws();
        if (peek() == '}') { ++p_; return true; }
        for (;;) {
            ws();
            std::string key;
            if (!str(key)) return false;
            ws();
            if (!eat(':')) return false;
            ws();
            Val v;
            if (!value(v, 0)) return false;
            if (key == "text" && v.type == Val::Str) m.text = std::move(v.s);
            else if (key == "alignment_center") {
                if (v.type == Val::Bool) m.alignment_center = v.b;
                else if (v.type == Val::Num) m.alignment_center = (v.n != 0.0);
            } else if (key == "font_size" && v.type == Val::Num) {
                int fs_ = static_cast<int>(v.n);
                m.font_size = std::max(10, std::min(200, fs_));
            }
            ws();
            if (peek() == ',') { ++p_; continue; }
            if (peek() == '}') { ++p_; return true; }
            return false;
        }
    }

private:
    struct Val {
        enum T { Other, Str, Num, Bool } type = Other;
        std::string s;
        double n = 0.0;
        bool b = false;
    };

    const char* p_;
    const char* e_;

    char peek() const { return p_ < e_ ? *p_ : '\0'; }
    bool eat(char c) { if (p_ < e_ && *p_ == c) { ++p_; return true; } return false; }
    void ws() { while (p_ < e_ && (*p_ == ' ' || *p_ == '\t' || *p_ == '\n' || *p_ == '\r')) ++p_; }

    bool hex4(uint32_t& out) {
        if (e_ - p_ < 4) return false;
        out = 0;
        for (int i = 0; i < 4; ++i) {
            char c = *p_++;
            out <<= 4;
            if (c >= '0' && c <= '9') out |= static_cast<uint32_t>(c - '0');
            else if (c >= 'a' && c <= 'f') out |= static_cast<uint32_t>(c - 'a' + 10);
            else if (c >= 'A' && c <= 'F') out |= static_cast<uint32_t>(c - 'A' + 10);
            else return false;
        }
        return true;
    }

    bool str(std::string& out) {
        if (!eat('"')) return false;
        while (p_ < e_) {
            char c = *p_++;
            if (c == '"') return true;
            if (c != '\\') { out.push_back(c); continue; }
            if (p_ >= e_) return false;
            char esc = *p_++;
            switch (esc) {
                case '"': out.push_back('"'); break;
                case '\\': out.push_back('\\'); break;
                case '/': out.push_back('/'); break;
                case 'b': out.push_back('\b'); break;
                case 'f': out.push_back('\f'); break;
                case 'n': out.push_back('\n'); break;
                case 'r': out.push_back('\r'); break;
                case 't': out.push_back('\t'); break;
                case 'u': {
                    uint32_t cp;
                    if (!hex4(cp)) return false;
                    if (cp >= 0xD800 && cp <= 0xDBFF) {
                        uint32_t lo = 0;
                        if (e_ - p_ >= 6 && p_[0] == '\\' && p_[1] == 'u') {
                            const char* save = p_;
                            p_ += 2;
                            if (hex4(lo) && lo >= 0xDC00 && lo <= 0xDFFF) {
                                cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                            } else { p_ = save; cp = 0xFFFD; }
                        } else cp = 0xFFFD;
                    } else if (cp >= 0xDC00 && cp <= 0xDFFF) cp = 0xFFFD;
                    append_utf8(out, cp);
                    break;
                }
                default: return false;
            }
        }
        return false;
    }

    bool value(Val& v, int depth) {
        if (depth > 64) return false;
        ws();
        char c = peek();
        if (c == '"') { v.type = Val::Str; return str(v.s); }
        if (c == 't' && e_ - p_ >= 4 && std::strncmp(p_, "true", 4) == 0) { p_ += 4; v.type = Val::Bool; v.b = true; return true; }
        if (c == 'f' && e_ - p_ >= 5 && std::strncmp(p_, "false", 5) == 0) { p_ += 5; v.type = Val::Bool; v.b = false; return true; }
        if (c == 'n' && e_ - p_ >= 4 && std::strncmp(p_, "null", 4) == 0) { p_ += 4; return true; }
        if (c == '-' || (c >= '0' && c <= '9')) {
            const char* s = p_;
            while (p_ < e_ && (std::strchr("+-.eE0123456789", *p_) != nullptr)) ++p_;
            std::string tmp(s, p_);
            char* endp = nullptr;
            v.n = std::strtod(tmp.c_str(), &endp);
            v.type = Val::Num;
            return endp && *endp == '\0';
        }
        if (c == '[') {
            ++p_; ws();
            if (peek() == ']') { ++p_; return true; }
            for (;;) {
                Val tmp;
                if (!value(tmp, depth + 1)) return false;
                ws();
                if (peek() == ',') { ++p_; continue; }
                if (peek() == ']') { ++p_; return true; }
                return false;
            }
        }
        if (c == '{') {
            ++p_; ws();
            if (peek() == '}') { ++p_; return true; }
            for (;;) {
                ws();
                std::string k;
                if (!str(k)) return false;
                ws();
                if (!eat(':')) return false;
                Val tmp;
                if (!value(tmp, depth + 1)) return false;
                ws();
                if (peek() == ',') { ++p_; continue; }
                if (peek() == '}') { ++p_; return true; }
                return false;
            }
        }
        return false;
    }
};

} // namespace pkg

// Geçici dosya yolu üretici + RAII silici
static std::string make_temp_path(const std::string& suffix) {
    static std::atomic<unsigned> counter{0};
    std::error_code ec;
    fs::path dir = fs::temp_directory_path(ec);
    if (ec) dir = ".";
#ifdef _WIN32
    long pid = static_cast<long>(_getpid());
#else
    long pid = static_cast<long>(getpid());
#endif
    auto stamp = std::chrono::steady_clock::now().time_since_epoch().count();
    std::ostringstream n;
    n << "kavram_" << pid << "_" << stamp << "_" << counter++ << suffix;
    return (dir / n.str()).string();
}

struct TempFile {
    std::string path;
    explicit TempFile(const std::string& suffix) : path(make_temp_path(suffix)) {}
    ~TempFile() { std::error_code ec; fs::remove(path, ec); }
    TempFile(const TempFile&) = delete;
    TempFile& operator=(const TempFile&) = delete;
};

// Edit Decision List (EDL) ve Memento / Komut deseni için veri modelleri
enum class ActionType {
    LOAD_FILE,
    DELETE_SEGMENT,
    DELETE_SIMILAR_SEGMENTS,
    DELETE_BY_THICKNESS,
    INSERT_AUDIO,
    INSERT_RECORDING,
    UNDO,
    REDO,
    EXPORT_FILE,
    LOAD_PACKAGE,
    EXPORT_PACKAGE
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
    std::vector<float> saved_segment_data; // (ayrılmış alan)
};

struct AudioEngine;

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

// Kanal sayıları farklı olan interleaved veriyi hedef kanal sayısına çevirir.
//  - aynı kanal sayısı : kopya
//  - hedef mono        : kanalların ortalaması
//  - kaynak mono       : her kanala kopya
//  - diğer             : hedef kanal c <- kaynak kanal min(c, src_ch-1)
static std::vector<float> convert_channels(const float* src, size_t frames, int src_ch, int dst_ch) {
    std::vector<float> out;
    if (src_ch <= 0 || dst_ch <= 0) return out;
    if (src_ch == dst_ch) { out.assign(src, src + frames * static_cast<size_t>(src_ch)); return out; }
    out.resize(frames * static_cast<size_t>(dst_ch));
    for (size_t f = 0; f < frames; ++f) {
        const float* in = src + f * static_cast<size_t>(src_ch);
        float* o = out.data() + f * static_cast<size_t>(dst_ch);
        if (dst_ch == 1) {
            float sum = 0.0f;
            for (int c = 0; c < src_ch; ++c) sum += in[c];
            o[0] = sum / static_cast<float>(src_ch);
        } else {
            for (int c = 0; c < dst_ch; ++c) o[c] = in[std::min(c, src_ch - 1)];
        }
    }
    return out;
}

// Ses dosyasını (libsndfile'ın desteklediği her biçim) float olarak okur.
static bool read_audio_file(const std::string& path, std::vector<float>& out,
                            int& sr, int& ch, std::string& err) {
    SF_INFO info{};
    SNDFILE* f = sf_open(path.c_str(), SFM_READ, &info);
    if (!f) {
        err = "Error opening sound file: " + path + " - " + sf_strerror(NULL);
        return false;
    }
    if (info.frames <= 0 || info.channels <= 0 || info.samplerate <= 0) {
        sf_close(f);
        err = "Sound file is empty or invalid: " + path;
        return false;
    }
    sr = info.samplerate;
    ch = info.channels;
    try {
        out.assign(static_cast<size_t>(info.frames) * static_cast<size_t>(info.channels), 0.0f);
    } catch (const std::bad_alloc&) {
        sf_close(f);
        err = "Out of memory while loading: " + path;
        return false;
    }
    sf_count_t got = sf_readf_float(f, out.data(), info.frames);
    sf_close(f);
    if (got <= 0) {
        out.clear();
        err = "Could not read audio data from: " + path;
        return false;
    }
    if (got < info.frames) {
        std::cerr << "Warning: file is truncated, read " << got << " of " << info.frames << " frames." << std::endl;
        out.resize(static_cast<size_t>(got) * static_cast<size_t>(ch));
    }
    return true;
}

static bool write_wav_file(const std::string& path, const float* data, size_t frames,
                           int sr, int ch, std::string& err) {
    SF_INFO sfinfo{};
    sfinfo.samplerate = sr;
    sfinfo.channels = ch;
    sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_FLOAT;
    SNDFILE* outfile = sf_open(path.c_str(), SFM_WRITE, &sfinfo);
    if (!outfile) {
        err = "Error opening output file for saving: " + path + " - " + sf_strerror(NULL);
        return false;
    }
    sf_count_t written = sf_writef_float(outfile, data, static_cast<sf_count_t>(frames));
    int close_result = sf_close(outfile);
    if (written != static_cast<sf_count_t>(frames)) {
        err = "Error writing output file: " + path;
        return false;
    }
    if (close_result != 0) {
        err = "Error closing output file: " + path;
        return false;
    }
    return true;
}

// Yarım yazılmış/bozuk dosya bırakmamak için: önce .tmp'ye yaz, sonra atomik rename.
static bool write_wav_atomic(const std::string& path, const float* data, size_t frames,
                             int sr, int ch, std::string& err) {
    const std::string tmp = path + ".tmp";
    if (!write_wav_file(tmp, data, frames, sr, ch, err)) {
        std::error_code ec; fs::remove(tmp, ec);
        return false;
    }
    std::error_code ec;
    fs::rename(tmp, path, ec);
    if (ec) {
        err = "Could not replace output file: " + path + " (" + ec.message() + ")";
        fs::remove(tmp, ec);
        return false;
    }
    return true;
}

// Structure to hold all audio engine related data and methods
struct AudioEngine {
    // --- PROJE DİZİNİ VE GÜVENLİ KOPYALAMA (COW / EDL) VERİLERİ ---
    std::string project_directory;
    std::string original_copy_path;
    std::vector<AudioEditCommand> edl_log;
    uint64_t command_counter;

    // Gerçek ses verileri
    std::vector<float> audio_buffer; // interleaved float
    int sample_rate;
    int channels;

    // Ses verisine erişim kilidi: düzenleme = unique, okuma/kaydetme = shared.
    // PortAudio geri çağırması yalnızca try_lock_shared kullanır (asla bloklanmaz).
    std::shared_mutex buffer_mutex;

    // Ses iş parçacığı ile GUI iş parçacığı arasında paylaşılan durum
    std::atomic<int>    current_play_position_ms;
    int                 total_duration_ms;
    std::atomic<bool>   is_playing_flag;
    std::atomic<float>  current_speed;
    std::atomic<long>   playback_frame_index;
    std::atomic<double> playback_position_frames; // oynatma konumunun asıl kaynağı
    std::atomic<int>    seek_serial;              // konum değişikliklerini callback'e bildirir
    int                 play_channels;            // oynatma akışı açılırken kullanılan kanal sayısı
    std::vector<float>  envelope_data_storage;

    // --- UNDO / REDO (her adım: işlem SONRASI durumun anlık görüntüsü) ---
    std::vector<std::vector<float>> history_stack;
    int history_index;
    const size_t MAX_HISTORY_STEPS = 5;

    // Mikrofon kaydı
    PaStream *record_stream;
    std::vector<float> recorded_audio_buffer;
    std::atomic<bool> is_recording_flag;
    int record_channels;        // cihazdan gerçekten alınan kanal sayısı
    int recorded_sample_rate;   // kaydın örnekleme oranı

    // Oynatma
    PaStream *play_stream;

    // Playback Low-Pass
    float playback_lp_cutoff_hz;
    float lp_filter_alpha;
    std::vector<float> lp_filter_prev_output;

    // --- Mikrofon işleme parametreleri ---
    float mic_noise_gate_threshold;
    float mic_noise_gate_release_ms;
    std::vector<float> mic_noise_gate_gain;
    std::vector<float> mic_noise_gate_prev_sample;

    float mic_hp_cutoff_hz;
    float mic_hp_filter_alpha;
    std::vector<float> mic_hp_filter_prev_output;
    std::vector<float> mic_hp_filter_prev_input;

    float mic_lp_cutoff_hz;
    float mic_lp_filter_alpha;
    std::vector<float> mic_lp_filter_prev_output;

    float mic_input_gain;

    int   reverb_level;
    float mic_reverb_lp_filter_alpha;
    std::vector<float> mic_reverb_lp_filter_prev_output;

    int   de_esser_level;
    float mic_de_esser_gain;
    float mic_de_esser_cutoff_hz;
    std::vector<float> de_esser_b0, de_esser_b1, de_esser_b2;
    std::vector<float> de_esser_a1, de_esser_a2;
    std::vector<float> de_esser_x_prev, de_esser_x_prev2;
    std::vector<float> de_esser_y_prev, de_esser_y_prev2;

    int   de_hum_level;
    float mic_de_hum_q;
    std::vector<float> de_hum_b0, de_hum_b1, de_hum_b2;
    std::vector<float> de_hum_a1, de_hum_a2;
    std::vector<float> de_hum_x_prev, de_hum_x_prev2;
    std::vector<float> de_hum_y_prev, de_hum_y_prev2;
    float de_hum_frequency_hz;
    bool de_hum_enabled;

    float mic_comp_threshold_db;
    float mic_comp_ratio;
    float mic_comp_attack_ms;
    float mic_comp_release_ms;
    float mic_comp_makeup_gain_db;
    std::vector<float> mic_comp_envelope;
    std::vector<float> mic_comp_gain;

    float mic_eq_gain_db;
    float mic_eq_frequency_hz;
    float mic_eq_q;
    bool  mic_eq_enabled;
    std::vector<float> eq_b0, eq_b1, eq_b2;
    std::vector<float> eq_a1, eq_a2;
    std::vector<float> eq_x_prev, eq_x_prev2;
    std::vector<float> eq_y_prev, eq_y_prev2;

    // --- .sound paketinden gelen metin/ayarlar (Python bunları buradan okur) ---
    std::string pkg_text;
    int pkg_alignment_center;
    int pkg_font_size;

    // Hata bilgisi (Python'un diyaloglarda gösterebilmesi için)
    std::string last_error;
    int last_load_skipped;

    // ------------------------------------------------------------------
    AudioEngine() : project_directory("Export/saund"),
                    original_copy_path("Export/saund/original.wav"),
                    command_counter(0),
                    sample_rate(44100), channels(2),
                    current_play_position_ms(0), total_duration_ms(0),
                    is_playing_flag(false), current_speed(1.0f),
                    playback_frame_index(0), playback_position_frames(0.0),
                    seek_serial(0), play_channels(0),
                    history_index(-1),
                    record_stream(nullptr), is_recording_flag(false),
                    record_channels(2), recorded_sample_rate(44100),
                    play_stream(nullptr),
                    playback_lp_cutoff_hz(3000.0f), lp_filter_alpha(0.0f),
                    mic_noise_gate_threshold(0.0001f),
                    mic_noise_gate_release_ms(20.0f),
                    mic_hp_cutoff_hz(150.0f), mic_hp_filter_alpha(0.0f),
                    mic_lp_cutoff_hz(0.0f), mic_lp_filter_alpha(0.0f),
                    mic_input_gain(1.0f),
                    reverb_level(0), mic_reverb_lp_filter_alpha(0.0f),
                    de_esser_level(0), mic_de_esser_gain(1.0f), mic_de_esser_cutoff_hz(6000.0f),
                    de_hum_level(0), mic_de_hum_q(30.0f), de_hum_frequency_hz(50.0f), de_hum_enabled(false),
                    mic_comp_threshold_db(0.0f), mic_comp_ratio(1.0f),
                    mic_comp_attack_ms(1.0f), mic_comp_release_ms(100.0f), mic_comp_makeup_gain_db(0.0f),
                    mic_eq_gain_db(0.0f), mic_eq_frequency_hz(1000.0f), mic_eq_q(1.0f), mic_eq_enabled(false),
                    pkg_alignment_center(0), pkg_font_size(14), last_load_skipped(0)
    {
        std::cout << "AudioEngine created with Safe Non-Destructive Storage & EDL support." << std::endl;

        try {
            fs::create_directories(project_directory);
        } catch (const std::exception& e) {
            std::cerr << "Directory creation warning: " << e.what() << std::endl;
        }

        PaError err = Pa_Initialize();
        if (err != paNoError) {
            std::cerr << "PortAudio error during initialization: " << Pa_GetErrorText(err) << std::endl;
        }

        resize_channel_state(channels);
        refresh_dsp_params();
    }

    ~AudioEngine() {
        std::cout << "AudioEngine destroying..." << std::endl;
        is_playing_flag = false;
        is_recording_flag = false;
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
        clear_history();
    }

    // Hata kaydı + stderr + -1
    int fail(const std::string& msg) {
        last_error = msg;
        std::cerr << "AudioEngine error: " << msg << std::endl;
        return -1;
    }

    // ------------------------------------------------------------------
    //  KANAL / ÖRNEKLEME ORANI DEĞİŞİNCE DSP DURUMUNU TUTARLI TUT
    //  [DÜZELTME] Eskiden vektörler yalnızca 2 kanala göre açılıyordu;
    //  2'den fazla kanallı dosya yüklenince bellek taşması oluyordu.
    //  Filtre katsayıları da ilk (44100 Hz) orana göre kalıyordu.
    // ------------------------------------------------------------------
    void resize_channel_state(int ch) {
        if (ch < 1) ch = 1;
        const size_t n = static_cast<size_t>(ch);
        lp_filter_prev_output.assign(n, 0.0f);
        mic_noise_gate_gain.assign(n, 0.0f);
        mic_noise_gate_prev_sample.assign(n, 0.0f);
        mic_hp_filter_prev_output.assign(n, 0.0f);
        mic_hp_filter_prev_input.assign(n, 0.0f);
        mic_lp_filter_prev_output.assign(n, 0.0f);
        mic_reverb_lp_filter_prev_output.assign(n, 0.0f);
        for (auto* v : {&de_esser_b0, &de_esser_b1, &de_esser_b2, &de_esser_a1, &de_esser_a2,
                        &de_esser_x_prev, &de_esser_x_prev2, &de_esser_y_prev, &de_esser_y_prev2,
                        &de_hum_b0, &de_hum_b1, &de_hum_b2, &de_hum_a1, &de_hum_a2,
                        &de_hum_x_prev, &de_hum_x_prev2, &de_hum_y_prev, &de_hum_y_prev2,
                        &eq_b0, &eq_b1, &eq_b2, &eq_a1, &eq_a2,
                        &eq_x_prev, &eq_x_prev2, &eq_y_prev, &eq_y_prev2}) {
            v->assign(n, 0.0f);
        }
        mic_comp_envelope.assign(n, 0.0f);
        mic_comp_gain.assign(n, 1.0f);
    }

    void reset_mic_state() {
        const size_t n = static_cast<size_t>(std::max(1, channels));
        mic_noise_gate_gain.assign(n, 0.0f);
        mic_noise_gate_prev_sample.assign(n, 0.0f);
        mic_hp_filter_prev_output.assign(n, 0.0f);
        mic_hp_filter_prev_input.assign(n, 0.0f);
        mic_lp_filter_prev_output.assign(n, 0.0f);
        mic_reverb_lp_filter_prev_output.assign(n, 0.0f);
        for (auto* v : {&de_esser_x_prev, &de_esser_x_prev2, &de_esser_y_prev, &de_esser_y_prev2,
                        &de_hum_x_prev, &de_hum_x_prev2, &de_hum_y_prev, &de_hum_y_prev2,
                        &eq_x_prev, &eq_x_prev2, &eq_y_prev, &eq_y_prev2}) {
            v->assign(n, 0.0f);
        }
        mic_comp_envelope.assign(n, 0.0f);
        mic_comp_gain.assign(n, 1.0f);
    }

    static float one_pole_alpha(float hz, int sr) {
        if (hz <= 0.0f || sr <= 0) return 0.0f;
        const double T = 1.0 / sr;
        return static_cast<float>((2.0 * M_PI * hz * T) / (2.0 * M_PI * hz * T + 1.0));
    }

    void apply_playback_lp() { lp_filter_alpha = one_pole_alpha(playback_lp_cutoff_hz, sample_rate); }

    void apply_mic_hp() {
        if (mic_hp_cutoff_hz <= 0.0f || sample_rate <= 0) mic_hp_filter_alpha = 0.0f;
        else mic_hp_filter_alpha = static_cast<float>(1.0 / (1.0 + 2.0 * M_PI * mic_hp_cutoff_hz / sample_rate));
        std::fill(mic_hp_filter_prev_output.begin(), mic_hp_filter_prev_output.end(), 0.0f);
        std::fill(mic_hp_filter_prev_input.begin(), mic_hp_filter_prev_input.end(), 0.0f);
    }

    void apply_mic_lp() {
        mic_lp_filter_alpha = one_pole_alpha(mic_lp_cutoff_hz, sample_rate);
        std::fill(mic_lp_filter_prev_output.begin(), mic_lp_filter_prev_output.end(), 0.0f);
    }

    void apply_reverb() {
        mic_reverb_lp_filter_prev_output.assign(mic_reverb_lp_filter_prev_output.size(), 0.0f);
        if (reverb_level == 0 || sample_rate <= 0) { mic_reverb_lp_filter_alpha = 0.0f; return; }
        float cutoff_hz;
        switch (reverb_level) {
            case 1: cutoff_hz = 10000.0f; break;
            case 2: cutoff_hz = 8000.0f; break;
            case 3: cutoff_hz = 6000.0f; break;
            case 4: cutoff_hz = 4000.0f; break;
            default: cutoff_hz = 20000.0f; break;
        }
        mic_reverb_lp_filter_alpha = one_pole_alpha(cutoff_hz, sample_rate);
    }

    void apply_de_esser() {
        const size_t n = de_esser_b0.size();
        de_esser_x_prev.assign(n, 0.0f); de_esser_x_prev2.assign(n, 0.0f);
        de_esser_y_prev.assign(n, 0.0f); de_esser_y_prev2.assign(n, 0.0f);

        auto bypass = [&]() {
            mic_de_esser_gain = 1.0f;
            for (size_t k = 0; k < n; ++k) {
                de_esser_b0[k] = 0.0f; de_esser_b1[k] = 0.0f; de_esser_b2[k] = 0.0f;
                de_esser_a1[k] = 0.0f; de_esser_a2[k] = 0.0f;
            }
        };
        if (de_esser_level == 0 || sample_rate <= 0) { bypass(); return; }

        float gain_db;
        switch (de_esser_level) {
            case 1: gain_db = -3.0f; break;
            case 2: gain_db = -6.0f; break;
            case 3: gain_db = -9.0f; break;
            default: gain_db = 0.0f; break;
        }
        mic_de_esser_cutoff_hz = 6000.0f;
        if (gain_db == 0.0f || mic_de_esser_cutoff_hz >= 0.49f * static_cast<float>(sample_rate)) { bypass(); return; }
        mic_de_esser_gain = std::pow(10.0f, gain_db / 20.0f);

        const double Q_val = 0.707;
        const double A = std::pow(10.0, gain_db / 40.0);
        const double omega = 2.0 * M_PI * mic_de_esser_cutoff_hz / sample_rate;
        const double sn = std::sin(omega), cs = std::cos(omega);
        const double alpha_shelf = sn / (2.0 * Q_val);
        const double sA = 2.0 * std::sqrt(A) * alpha_shelf;

        // RBJ high-shelf
        const double b0 = A * ((A + 1) + (A - 1) * cs + sA);
        const double b1 = -2.0 * A * ((A - 1) + (A + 1) * cs);
        const double b2 = A * ((A + 1) + (A - 1) * cs - sA);
        const double a0 = (A + 1) - (A - 1) * cs + sA;
        // [DÜZELTME] Eski kodda a1 işareti hatalıydı: doğru ifade 2*((A-1) - (A+1)*cs)
        const double a1 = 2.0 * ((A - 1) - (A + 1) * cs);
        const double a2 = (A + 1) - (A - 1) * cs - sA;

        for (size_t k = 0; k < n; ++k) {
            de_esser_b0[k] = static_cast<float>(b0 / a0);
            de_esser_b1[k] = static_cast<float>(b1 / a0);
            de_esser_b2[k] = static_cast<float>(b2 / a0);
            de_esser_a1[k] = static_cast<float>(a1 / a0);
            de_esser_a2[k] = static_cast<float>(a2 / a0);
        }
    }

    void apply_de_hum() {
        const size_t n = de_hum_b0.size();
        de_hum_x_prev.assign(n, 0.0f); de_hum_x_prev2.assign(n, 0.0f);
        de_hum_y_prev.assign(n, 0.0f); de_hum_y_prev2.assign(n, 0.0f);

        if (de_hum_level == 0 || sample_rate <= 0 || de_hum_frequency_hz >= 0.49f * static_cast<float>(sample_rate)) {
            de_hum_enabled = false;
            for (size_t k = 0; k < n; ++k) {
                de_hum_b0[k] = 0.0f; de_hum_b1[k] = 0.0f; de_hum_b2[k] = 0.0f;
                de_hum_a1[k] = 0.0f; de_hum_a2[k] = 0.0f;
            }
            return;
        }
        de_hum_enabled = true;
        switch (de_hum_level) {
            case 1: mic_de_hum_q = 10.0f; break;
            case 2: mic_de_hum_q = 30.0f; break;
            case 3: mic_de_hum_q = 60.0f; break;
            default: mic_de_hum_q = 30.0f; break;
        }
        const double omega0 = 2.0 * M_PI * de_hum_frequency_hz / sample_rate;
        const double alpha_notch = std::sin(omega0) / (2.0 * mic_de_hum_q);
        const double b0 = 1.0, b1 = -2.0 * std::cos(omega0), b2 = 1.0;
        const double a0 = 1.0 + alpha_notch, a1 = -2.0 * std::cos(omega0), a2 = 1.0 - alpha_notch;
        for (size_t k = 0; k < n; ++k) {
            de_hum_b0[k] = static_cast<float>(b0 / a0);
            de_hum_b1[k] = static_cast<float>(b1 / a0);
            de_hum_b2[k] = static_cast<float>(b2 / a0);
            de_hum_a1[k] = static_cast<float>(a1 / a0);
            de_hum_a2[k] = static_cast<float>(a2 / a0);
        }
    }

    void calculate_eq_coefficients() {
        const size_t n = eq_b0.size();
        eq_x_prev.assign(n, 0.0f); eq_x_prev2.assign(n, 0.0f);
        eq_y_prev.assign(n, 0.0f); eq_y_prev2.assign(n, 0.0f);

        if (sample_rate <= 0 || !mic_eq_enabled || mic_eq_frequency_hz >= 0.49f * static_cast<float>(sample_rate)) {
            for (size_t k = 0; k < n; ++k) {
                eq_b0[k] = 1.0f; eq_b1[k] = 0.0f; eq_b2[k] = 0.0f;
                eq_a1[k] = 0.0f; eq_a2[k] = 0.0f;
            }
            return;
        }
        const double A = std::pow(10.0, mic_eq_gain_db / 40.0);
        const double omega = 2.0 * M_PI * mic_eq_frequency_hz / sample_rate;
        const double sn = std::sin(omega), cs = std::cos(omega);
        const double alpha = sn / (2.0 * mic_eq_q);

        const double b0 = 1.0 + alpha * A, b1 = -2.0 * cs, b2 = 1.0 - alpha * A;
        const double a0 = 1.0 + alpha / A, a1 = -2.0 * cs, a2 = 1.0 - alpha / A;
        for (size_t k = 0; k < n; ++k) {
            eq_b0[k] = static_cast<float>(b0 / a0);
            eq_b1[k] = static_cast<float>(b1 / a0);
            eq_b2[k] = static_cast<float>(b2 / a0);
            eq_a1[k] = static_cast<float>(a1 / a0);
            eq_a2[k] = static_cast<float>(a2 / a0);
        }
    }

    void refresh_dsp_params() {
        apply_playback_lp();
        apply_mic_hp();
        apply_mic_lp();
        apply_reverb();
        apply_de_esser();
        apply_de_hum();
        calculate_eq_coefficients();
    }

    // ------------------------------------------------------------------
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

    void log_edl_command(ActionType type, const std::string& type_name, int start_ms, int end_ms,
                         const std::string& desc, const std::string& src_path = "") {
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
        Export_edl_to_file();
    }

    int Export_edl_to_file() {
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

    int safe_copy_original_file(const std::string& source_path) {
        try {
            fs::create_directories(project_directory);
            original_copy_path = project_directory + "/original.wav";

            std::error_code ec;
            // [DÜZELTME] Kaynak zaten original.wav ise kendi üzerine kopyalama hatası verme
            if (fs::exists(original_copy_path, ec) && fs::equivalent(source_path, original_copy_path, ec)) {
                return 0;
            }
            ec.clear();
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

    // --- GEÇMİŞ YÖNETİMİ ---
    void clear_history() {
        history_stack.clear();
        history_index = -1;
    }

    // Her düzenlemeden ÖNCE çağrılır: geçmiş boşsa mevcut durum başlangıç adımı olur.
    // [DÜZELTME] Yüklemesiz (yalnızca kayıt eklenen) oturumda ilk işlem geri alınamıyordu.
    void ensure_history_baseline() {
        if (history_stack.empty()) push_history();
    }

    void push_history() {
        if (history_index < static_cast<int>(history_stack.size()) - 1) {
            history_stack.erase(history_stack.begin() + history_index + 1, history_stack.end());
        }
        try {
            history_stack.push_back(audio_buffer);
            if (history_stack.size() > MAX_HISTORY_STEPS) {
                history_stack.erase(history_stack.begin());
            } else {
                history_index++;
            }
        } catch (const std::bad_alloc&) {
            std::cerr << "Warning: Could not save undo state (Out of memory). Edits will not be undoable." << std::endl;
        }
    }

    int undo() {
        std::unique_lock<std::shared_mutex> lk(buffer_mutex);
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
        std::unique_lock<std::shared_mutex> lk(buffer_mutex);
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

    // Zarf (dalga şekli) verisi + süre. ÇAĞIRAN KİLİDİ TUTMALIDIR.
    void recalculate_envelope_data() {
        envelope_data_storage.clear();
        if (audio_buffer.empty() || sample_rate <= 0 || channels <= 0) {
            total_duration_ms = 0;
            current_play_position_ms = 0;
            playback_frame_index = 0;
            playback_position_frames = 0.0;
            ++seek_serial;
            return;
        }

        const int ENVELOPE_MS_PER_POINT = 50;
        size_t frames_per_envelope_point = (static_cast<size_t>(sample_rate) * ENVELOPE_MS_PER_POINT) / 1000;
        if (frames_per_envelope_point == 0) frames_per_envelope_point = 1;

        const size_t total_frames = audio_buffer.size() / static_cast<size_t>(channels);
        envelope_data_storage.reserve(total_frames / frames_per_envelope_point + 1);
        for (size_t i = 0; i < total_frames; i += frames_per_envelope_point) {
            float max_amplitude = 0.0f;
            const size_t end = std::min(total_frames, i + frames_per_envelope_point);
            for (size_t f = i; f < end; ++f) {
                for (int k = 0; k < channels; ++k) {
                    max_amplitude = std::max(max_amplitude, std::abs(audio_buffer[f * channels + k]));
                }
            }
            envelope_data_storage.push_back(max_amplitude);
        }
        total_duration_ms = static_cast<int>((static_cast<double>(total_frames) / sample_rate) * 1000);

        // [DÜZELTME] Düzenleme sonrası süre kısalırsa oynatma konumu dışarıda kalmasın
        if (current_play_position_ms > total_duration_ms) {
            current_play_position_ms = total_duration_ms;
            playback_position_frames = static_cast<double>(total_frames);
            playback_frame_index = static_cast<long>(total_frames);
            ++seek_serial;
        }
        std::cout << "Envelope data recalculated. New duration: " << total_duration_ms
                  << " ms, Length: " << envelope_data_storage.size() << std::endl;
    }

    // ------------------------------------------------------------------
    //  YÜKLEME
    // ------------------------------------------------------------------
    void stop_playback_stream() {
        is_playing_flag = false;
        if (play_stream) {
            Pa_StopStream(play_stream);
            Pa_CloseStream(play_stream);
            play_stream = nullptr;
        }
    }

    // Çözülmüş sesi motora işler (hepsi-ya-da-hiç: hata olursa eski proje korunur).
    int commit_audio(std::vector<float>&& data, int sr, int ch) {
        if (data.empty() || sr <= 0 || ch <= 0) return fail("No valid audio data loaded.");
        if (is_recording_flag) return fail("Cannot load audio while recording.");

        stop_playback_stream();
        std::unique_lock<std::shared_mutex> lk(buffer_mutex);
        audio_buffer.swap(data);
        sample_rate = sr;
        channels = ch;
        resize_channel_state(channels);
        refresh_dsp_params();

        current_play_position_ms = 0;
        playback_frame_index = 0;
        playback_position_frames = 0.0;
        ++seek_serial;
        is_playing_flag = false;

        clear_history();
        recalculate_envelope_data();
        push_history();
        pkg_text.clear();
        pkg_alignment_center = 0;
        pkg_font_size = 14;
        return 0;
    }

    int load_files(char** filePaths, int numFiles) {
        std::cout << "Attempting to load " << numFiles << " audio files." << std::endl;
        last_load_skipped = 0;
        if (!filePaths || numFiles <= 0) return fail("No files to load.");
        if (is_recording_flag) return fail("Cannot load files while recording.");

        std::vector<float> combined;
        int new_sr = 0, new_ch = 0;
        std::string first_path;
        struct Loaded { std::string path; int dur_ms; };
        std::vector<Loaded> loaded;

        for (int i = 0; i < numFiles; ++i) {
            std::string filePath = filePaths[i] ? filePaths[i] : "";
            std::cout << "  Loading: " << filePath << std::endl;

            std::vector<float> data;
            int sr = 0, ch = 0;
            std::string err;
            if (!read_audio_file(filePath, data, sr, ch, err)) {
                if (i == 0 || new_sr == 0) return fail(err);   // ilk dosya açılamadı → işlemi iptal et
                std::cerr << "Warning: " << err << " Skipping." << std::endl;
                last_load_skipped++;
                continue;
            }
            if (new_sr == 0) {
                new_sr = sr; new_ch = ch; first_path = filePath;
            } else if (sr != new_sr || ch != new_ch) {
                std::cerr << "Warning: Mismatch in sample rate or channels for " << filePath << ". Skipping." << std::endl;
                last_load_skipped++;
                continue;
            }
            const int dur_ms = static_cast<int>((static_cast<double>(data.size() / static_cast<size_t>(ch)) / sr) * 1000);
            try {
                combined.insert(combined.end(), data.begin(), data.end());
            } catch (const std::bad_alloc&) {
                return fail("Out of memory while combining audio files.");
            }
            loaded.push_back({filePath, dur_ms});
        }

        if (combined.empty()) return fail("No valid audio data loaded.");
        if (commit_audio(std::move(combined), new_sr, new_ch) != 0) return -1;

        safe_copy_original_file(first_path);
        for (const auto& l : loaded) {
            log_edl_command(ActionType::LOAD_FILE, "LOAD_FILE", 0, l.dur_ms,
                            "Loaded file into non-destructive engine.", l.path);
        }
        std::cout << "Audio files loaded safely. Total duration: " << total_duration_ms << " ms." << std::endl;
        return 0;
    }

    // .sound paketini (zip + metadata.json) açar: ses VE metin tek hamlede içe alınır.
    // Dönüş: 0 = tamam, 1 = ses yüklendi ama metadata eksik/bozuk (uyarı), -1 = hata
    int load_sound_package(const std::string& path) {
        last_load_skipped = 0;
        if (is_recording_flag) return fail("Cannot load a package while recording.");

        std::string err;
        pkg::ZipReader zr;
        if (!zr.open(path, err)) return fail(err);

        const pkg::ZipReader::Entry* ea = zr.find("audio.wav");
        if (!ea) return fail("Invalid .sound package: audio.wav is missing.");

        // 1) Sesi geçici WAV'a akıt (CRC doğrulamalı)
        TempFile tmp_wav(".wav");
        {
            std::ofstream o(tmp_wav.path, std::ios::binary | std::ios::trunc);
            if (!o) return fail("Cannot create temporary audio file.");
            auto sink = [&o](const unsigned char* d, size_t n) {
                o.write(reinterpret_cast<const char*>(d), static_cast<std::streamsize>(n));
                return static_cast<bool>(o);
            };
            if (!zr.extract(*ea, 0xFFFFFFF0ull, sink, err)) return fail(err);
            o.flush();
            if (!o) return fail("Write error while extracting audio.");
        }

        // 2) Metadata (opsiyonel; bozuksa ses yine de açılır)
        pkg::PackageMeta meta;
        int status = 0;
        std::string warn;
        const pkg::ZipReader::Entry* em = zr.find("metadata.json");
        if (!em) {
            status = 1; warn = "metadata.json is missing; text/settings were not restored.";
        } else {
            std::string js;
            std::string merr;
            auto msink = [&js](const unsigned char* d, size_t n) {
                js.append(reinterpret_cast<const char*>(d), n);
                return true;
            };
            if (!zr.extract(*em, 16u * 1024u * 1024u, msink, merr)) {
                status = 1; warn = "metadata.json could not be read: " + merr;
            } else {
                pkg::MiniJson parser(js);
                if (!parser.parse_meta(meta)) {
                    meta = pkg::PackageMeta();
                    status = 1; warn = "metadata.json is not valid; text/settings were not restored.";
                }
            }
        }

        // 3) Sesi çöz ve motora işle
        std::vector<float> data;
        int sr = 0, ch = 0;
        if (!read_audio_file(tmp_wav.path, data, sr, ch, err)) return fail(err);
        const int dur_ms = static_cast<int>((static_cast<double>(data.size() / static_cast<size_t>(ch)) / sr) * 1000);
        if (commit_audio(std::move(data), sr, ch) != 0) return -1;

        safe_copy_original_file(tmp_wav.path);
        pkg_text = std::move(meta.text);
        pkg_alignment_center = meta.alignment_center ? 1 : 0;
        pkg_font_size = meta.font_size;
        log_edl_command(ActionType::LOAD_PACKAGE, "LOAD_PACKAGE", 0, dur_ms,
                        "Loaded .sound package (audio + text).", path);

        if (status == 1) { last_error = warn; std::cerr << "Package warning: " << warn << std::endl; }
        return status;
    }

    // Sesi + metni .sound paketi olarak yazar (önce .tmp, sonra atomik rename).
    int save_sound_package(const std::string& path, const std::string& text, bool center, int font_size) {
        TempFile tmp_wav(".wav");
        std::string err;
        {
            std::shared_lock<std::shared_mutex> lk(buffer_mutex);
            if (audio_buffer.empty() || sample_rate <= 0 || channels <= 0) return fail("No audio data to save.");
            if (!write_wav_file(tmp_wav.path, audio_buffer.data(),
                                audio_buffer.size() / static_cast<size_t>(channels),
                                sample_rate, channels, err)) return fail(err);
        }

        font_size = std::max(10, std::min(200, font_size));
        const std::string json = pkg::build_metadata_json(text, center, font_size);

        const std::string tmp_zip = path + ".tmp";
        pkg::ZipWriter zw;
        bool ok = zw.open(tmp_zip, err) &&
                  zw.add_file("audio.wav", tmp_wav.path, err) &&
                  zw.add_buffer("metadata.json", json, err) &&
                  zw.finish(err);
        std::error_code ec;
        if (!ok) { fs::remove(tmp_zip, ec); return fail(err); }
        fs::rename(tmp_zip, path, ec);
        if (ec) { fs::remove(tmp_zip, ec); return fail("Could not write package: " + path); }

        pkg_text = text;
        pkg_alignment_center = center ? 1 : 0;
        pkg_font_size = font_size;
        log_edl_command(ActionType::EXPORT_PACKAGE, "EXPORT_PACKAGE", 0, total_duration_ms,
                        "Exported .sound package (audio + text).", path);
        return 0;
    }

    // ------------------------------------------------------------------
    //  OYNATMA
    // ------------------------------------------------------------------
    // PulseAudio > ALSA > varsayılan sırasıyla ana bilgisayar API'si seç
    PaHostApiIndex find_preferred_host_api() {
        PaHostApiIndex target = Pa_GetDefaultHostApi();
        int count = Pa_GetHostApiCount();
        for (PaHostApiIndex i = 0; i < count; ++i) {
            const PaHostApiInfo* info = Pa_GetHostApiInfo(i);
            if (!info) continue;
            std::string apiName = info->name;
            if (apiName.find("PulseAudio") != std::string::npos ||
                apiName.find("ALSA") != std::string::npos) {
                target = i;
                if (apiName.find("PulseAudio") != std::string::npos) break;
            }
        }
        return target;
    }

    int play() {
        long total_frames = 0;
        {
            std::shared_lock<std::shared_mutex> lk(buffer_mutex);
            if (audio_buffer.empty() || sample_rate <= 0 || channels <= 0) return fail("No audio data to play.");
            total_frames = static_cast<long>(audio_buffer.size() / static_cast<size_t>(channels));
        }
        if (is_playing_flag) { std::cout << "Audio is already playing." << std::endl; return 0; }
        if (is_recording_flag) return fail("Cannot play while recording.");

        if (play_stream) {
            Pa_StopStream(play_stream);
            Pa_CloseStream(play_stream);
            play_stream = nullptr;
        }

        PaHostApiIndex targetApiIndex = find_preferred_host_api();
        const PaHostApiInfo* targetApiInfo = Pa_GetHostApiInfo(targetApiIndex);
        if (!targetApiInfo) return fail("Could not get info for target Host API.");

        PaDeviceIndex device_index = targetApiInfo->defaultOutputDevice;
        if (device_index == paNoDevice) {
            device_index = Pa_GetDefaultOutputDevice();
            if (device_index == paNoDevice) return fail("No default output device found for any Host API.");
        } else {
            std::cout << "AudioEngine: Using Host API '" << targetApiInfo->name << "' for playback." << std::endl;
        }

        const PaDeviceInfo* deviceInfo = Pa_GetDeviceInfo(device_index);
        if (!deviceInfo) return fail("Could not get device info for selected output device.");

        PaStreamParameters outputParameters{};
        outputParameters.device = device_index;
        outputParameters.channelCount = channels;
        outputParameters.sampleFormat = paFloat32;
        outputParameters.suggestedLatency = deviceInfo->defaultHighOutputLatency;
        outputParameters.hostApiSpecificStreamInfo = NULL;

        // [DÜZELTME] Konum, akış BAŞLAMADAN önce ayarlanır; son bitmişse baştan başlar.
        double pos = playback_position_frames.load();
        if (pos >= static_cast<double>(total_frames) || pos < 0.0) pos = 0.0;
        playback_position_frames = pos;
        playback_frame_index = static_cast<long>(pos);
        current_play_position_ms = static_cast<int>((pos / sample_rate) * 1000.0);
        ++seek_serial;
        std::fill(lp_filter_prev_output.begin(), lp_filter_prev_output.end(), 0.0f);
        play_channels = channels;

        // [DÜZELTME] Bayrak StartStream'den ÖNCE true olur (aksi halde ilk callback akışı bitirebiliyordu)
        is_playing_flag = true;

        PaError err = Pa_OpenStream(&play_stream, NULL, &outputParameters,
                                    static_cast<double>(sample_rate), 1024, paClipOff,
                                    pa_playback_callback, this);
        if (err != paNoError) {
            is_playing_flag = false;
            play_stream = nullptr;
            return fail(std::string("PortAudio error during Pa_OpenStream for playback: ") + Pa_GetErrorText(err));
        }
        err = Pa_StartStream(play_stream);
        if (err != paNoError) {
            is_playing_flag = false;
            Pa_CloseStream(play_stream);
            play_stream = nullptr;
            return fail(std::string("PortAudio error during Pa_StartStream for playback: ") + Pa_GetErrorText(err));
        }

        std::cout << "Audio playback started." << std::endl;
        return 0;
    }

    int pause() {
        if (!is_playing_flag) { std::cout << "Audio is not playing." << std::endl; return 0; }
        is_playing_flag = false;
        if (play_stream) {
            PaError err = Pa_StopStream(play_stream);
            if (err != paNoError && err != paStreamIsStopped) {
                return fail(std::string("PortAudio error during Pa_StopStream for pause: ") + Pa_GetErrorText(err));
            }
        }
        std::cout << "Audio playback paused." << std::endl;
        return 0;
    }

    int stop() {
        stop_playback_stream();
        current_play_position_ms = 0;
        playback_frame_index = 0;
        playback_position_frames = 0.0;
        ++seek_serial;
        std::cout << "Audio playback stopped." << std::endl;
        return 0;
    }

    int get_position_ms() { return current_play_position_ms.load(); }
    int get_duration_ms() { return total_duration_ms; }
    int get_envelope_length() { return static_cast<int>(envelope_data_storage.size()); }

    const float* get_envelope_data() {
        if (envelope_data_storage.empty()) return nullptr;
        return envelope_data_storage.data();
    }

    int set_speed(float speed) {
        // [DÜZELTME] 0 veya negatif hız, callback'te negatif indekse (bellek hatası) yol açabiliyordu
        if (!(speed > 0.0f) || speed > 16.0f) return fail("Invalid playback speed.");
        std::cout << "Setting playback speed to " << speed << "x." << std::endl;
        current_speed = speed;
        return 0;
    }

    int set_play_position_ms(int ms) {
        if (ms < 0) ms = 0;
        if (ms > total_duration_ms) ms = total_duration_ms;
        const double frames = (static_cast<double>(ms) / 1000.0) * sample_rate;
        playback_position_frames = frames;
        playback_frame_index = static_cast<long>(frames);
        current_play_position_ms = ms;
        ++seek_serial;
        return 0;
    }

    int get_is_playing() { return is_playing_flag ? 1 : 0; }

    // ------------------------------------------------------------------
    //  DÜZENLEME (hepsi C++ tarafında; unique_lock ile korunur)
    // ------------------------------------------------------------------
    int delete_segment(int start_ms, int end_ms) {
        std::cout << "Deleting audio segment from " << start_ms << " to " << end_ms << " ms (non-destructive EDL recorded)." << std::endl;
        std::unique_lock<std::shared_mutex> lk(buffer_mutex);
        if (audio_buffer.empty() || sample_rate <= 0 || channels <= 0) return fail("No audio data to delete from.");

        long start_frame = static_cast<long>((static_cast<double>(start_ms) / 1000.0) * sample_rate);
        long end_frame = static_cast<long>((static_cast<double>(end_ms) / 1000.0) * sample_rate);
        start_frame = std::max(0L, start_frame);
        end_frame = std::min(static_cast<long>(audio_buffer.size() / channels), end_frame);

        if (start_frame >= end_frame) {
            std::cout << "No valid segment to delete." << std::endl;
            return 0;
        }

        ensure_history_baseline();
        audio_buffer.erase(audio_buffer.begin() + start_frame * channels,
                           audio_buffer.begin() + end_frame * channels);

        recalculate_envelope_data();
        push_history();
        log_edl_command(ActionType::DELETE_SEGMENT, "DELETE_SEGMENT", start_ms, end_ms, "Cut audio range from buffer.");
        return 0;
    }

    // --- BENZER SES TESPİTİ VE OTOMATİK SİLME ---
    int detect_and_delete_similar_segments(int start_ms, int end_ms, float threshold) {
        std::unique_lock<std::shared_mutex> lk(buffer_mutex);
        if (audio_buffer.empty() || sample_rate <= 0 || channels <= 0 || start_ms >= end_ms) {
            return fail("Invalid selection for similar-segment detection.");
        }

        long start_frame = static_cast<long>((static_cast<double>(start_ms) / 1000.0) * sample_rate);
        long end_frame = static_cast<long>((static_cast<double>(end_ms) / 1000.0) * sample_rate);
        long total_frames = static_cast<long>(audio_buffer.size() / channels);

        start_frame = std::max(0L, std::min(start_frame, total_frames));
        end_frame = std::max(0L, std::min(end_frame, total_frames));
        long pattern_len_frames = end_frame - start_frame;
        if (pattern_len_frames <= 0) return 0;

        long step_size = (static_cast<long>(sample_rate) * 2) / 1000;
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
                if ((current_val >= 0.0f && prev_val < 0.0f) || (current_val < 0.0f && prev_val >= 0.0f)) zcr_count++;
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
        long pattern_end_bin = std::min(end_frame / step_size, num_bins);
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
                long del_end = std::min((b + pattern_bins_count) * step_size, total_frames);
                segments_to_delete.push_back({del_start, del_end});
                b += pattern_bins_count - 1;
            }
        }

        bool original_included = false;
        for (const auto& r : segments_to_delete) {
            if (std::abs(r.first - start_frame) < step_size * 2) { original_included = true; break; }
        }
        if (!original_included) segments_to_delete.push_back({start_frame, end_frame});

        std::sort(segments_to_delete.begin(), segments_to_delete.end(),
                  [](const auto& a, const auto& b) { return a.first < b.first; });

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

        // [DÜZELTME] Geçmiş anlık görüntüsü işlemden SONRA alınır (eskiden öncesinde alınıyordu,
        // bu yüzden Redo bu işlemi geri getiremiyordu).
        ensure_history_baseline();
        for (auto it = merged_segments.rbegin(); it != merged_segments.rend(); ++it) {
            long s_idx = it->first * channels;
            long e_idx = it->second * channels;
            if (s_idx >= 0 && e_idx <= static_cast<long>(audio_buffer.size()) && s_idx < e_idx) {
                audio_buffer.erase(audio_buffer.begin() + s_idx, audio_buffer.begin() + e_idx);
            }
        }

        recalculate_envelope_data();
        push_history();
        log_edl_command(ActionType::DELETE_SIMILAR_SEGMENTS, "DELETE_SIMILAR", start_ms, end_ms,
                        "Detected and deleted " + std::to_string(merged_segments.size()) + " similar audio pattern segments.");
        std::cout << "High-Accuracy Similar segments deleted. Count: " << merged_segments.size() << std::endl;
        return 0;
    }

    // --- KALINLIĞA (GENLİK/SESSİZLİK) GÖRE TÜM PARÇADA SİLME ---
    int delete_segments_by_thickness(int start_ms, int end_ms) {
        std::unique_lock<std::shared_mutex> lk(buffer_mutex);
        if (audio_buffer.empty() || sample_rate <= 0 || channels <= 0 || start_ms >= end_ms) {
            return fail("Invalid selection for thickness-based deletion.");
        }

        long start_frame = static_cast<long>((static_cast<double>(start_ms) / 1000.0) * sample_rate);
        long end_frame = static_cast<long>((static_cast<double>(end_ms) / 1000.0) * sample_rate);
        long total_frames = static_cast<long>(audio_buffer.size() / static_cast<size_t>(channels));

        start_frame = std::max(0L, std::min(start_frame, total_frames));
        end_frame = std::max(0L, std::min(end_frame, total_frames));
        if (start_frame >= end_frame) return fail("Selection is empty.");

        // Seçili bölüm "kalınlık" referansıdır: RMS + peak birlikte kullanılır.
        float reference_peak = 0.0f;
        double reference_sum_sq = 0.0;
        long reference_frame_count = end_frame - start_frame;

        for (long frame = start_frame; frame < end_frame; ++frame) {
            for (int c = 0; c < channels; ++c) {
                float value = audio_buffer[frame * channels + c];
                reference_peak = std::max(reference_peak, std::abs(value));
                reference_sum_sq += static_cast<double>(value) * static_cast<double>(value);
            }
        }
        double reference_sample_count = static_cast<double>(reference_frame_count) * static_cast<double>(channels);
        float reference_rms = static_cast<float>(std::sqrt(reference_sum_sq / std::max(1.0, reference_sample_count)));

        constexpr float RMS_TOLERANCE = 0.20f;
        constexpr float PEAK_TOLERANCE = 0.20f;
        float rms_threshold = std::max(reference_rms * (1.0f + RMS_TOLERANCE), 0.00005f);
        float peak_threshold = std::max(reference_peak * (1.0f + PEAK_TOLERANCE), 0.0001f);

        long window_frames = (static_cast<long>(sample_rate) * 5) / 1000;       // 5 ms tarama
        if (window_frames < 1) window_frames = 1;
        long min_matching_frames = (static_cast<long>(sample_rate) * 20) / 1000; // en az 20 ms
        if (min_matching_frames < 1) min_matching_frames = 1;
        long max_bridge_frames = (static_cast<long>(sample_rate) * 10) / 1000;   // 10 ms'ye kadar delik köprülenir
        if (max_bridge_frames < 1) max_bridge_frames = 1;

        std::vector<std::pair<long, long>> segments_to_delete;
        segments_to_delete.reserve(64);

        long current_match_start = -1;
        long last_match_end = -1;   // son GERÇEK eşleşen pencerenin sonu
        long bridge_start = -1;

        for (long i = 0; i < total_frames; i += window_frames) {
            long w_end = std::min(i + window_frames, total_frames);
            if (w_end <= i) break;

            double sum_sq = 0.0;
            float w_peak = 0.0f;
            long frame_count = w_end - i;
            for (long frame = i; frame < w_end; ++frame) {
                for (int c = 0; c < channels; ++c) {
                    float value = audio_buffer[frame * channels + c];
                    w_peak = std::max(w_peak, std::abs(value));
                    sum_sq += static_cast<double>(value) * static_cast<double>(value);
                }
            }
            double sample_count = static_cast<double>(frame_count) * static_cast<double>(channels);
            float w_rms = static_cast<float>(std::sqrt(sum_sq / std::max(1.0, sample_count)));

            bool thickness_match = (w_rms <= rms_threshold) && (w_peak <= peak_threshold);

            if (thickness_match) {
                if (current_match_start < 0) current_match_start = i;
                last_match_end = w_end;
                bridge_start = -1;
            } else if (current_match_start >= 0) {
                if (bridge_start < 0) bridge_start = i;
                if ((w_end - bridge_start) > max_bridge_frames) {
                    // [DÜZELTME] Segment son gerçek eşleşmede biter (köprü penceresi dahil edilmez)
                    if ((last_match_end - current_match_start) >= min_matching_frames) {
                        segments_to_delete.push_back({current_match_start, last_match_end});
                    }
                    current_match_start = -1;
                    last_match_end = -1;
                    bridge_start = -1;
                }
            }
        }

        // [DÜZELTME] Döngü bitince açık kalan segment de son gerçek eşleşmede kapanır
        // (eskiden sondaki eşleşmeyen köprü penceresi de siliniyordu).
        if (current_match_start >= 0 && last_match_end > current_match_start) {
            if ((last_match_end - current_match_start) >= min_matching_frames) {
                segments_to_delete.push_back({current_match_start, last_match_end});
            }
        }

        // Seçilen örnek her durumda silinir
        segments_to_delete.push_back({start_frame, end_frame});

        std::sort(segments_to_delete.begin(), segments_to_delete.end(),
                  [](const auto& a, const auto& b) { return a.first < b.first; });

        std::vector<std::pair<long, long>> merged_segments;
        merged_segments.push_back(segments_to_delete[0]);
        for (size_t i = 1; i < segments_to_delete.size(); ++i) {
            auto& last = merged_segments.back();
            if (segments_to_delete[i].first <= last.second + max_bridge_frames) {
                last.second = std::max(last.second, segments_to_delete[i].second);
            } else {
                merged_segments.push_back(segments_to_delete[i]);
            }
        }

        // [DÜZELTME] Geçmiş anlık görüntüsü işlemden SONRA alınır; böylece Undo/Redo doğru çalışır.
        ensure_history_baseline();

        size_t deleted_frames = 0;
        for (auto it = merged_segments.rbegin(); it != merged_segments.rend(); ++it) {
            long s_frame = std::max(0L, std::min(it->first, total_frames));
            long e_frame = std::max(0L, std::min(it->second, total_frames));
            if (s_frame >= e_frame) continue;

            long s_idx = s_frame * channels;
            long e_idx = e_frame * channels;
            if (e_idx <= static_cast<long>(audio_buffer.size())) {
                deleted_frames += static_cast<size_t>(e_frame - s_frame);
                audio_buffer.erase(audio_buffer.begin() + s_idx, audio_buffer.begin() + e_idx);
            }
        }

        recalculate_envelope_data();
        push_history();
        log_edl_command(ActionType::DELETE_BY_THICKNESS, "DELETE_THICKNESS", start_ms, end_ms,
                        "Deep full-track thickness scan deleted " + std::to_string(merged_segments.size()) +
                        " matching/quiet regions (" + std::to_string(deleted_frames) + " frames).");

        std::cout << "Thickness based deep deletion completed. Segments deleted: " << merged_segments.size()
                  << ", frames deleted: " << deleted_frames << std::endl;
        return 0;
    }

    // Dosyadan ses ekle
    int insert_audio(const std::string& filePath, int position_ms) {
        std::cout << "Inserting audio file '" << filePath << "' at position " << position_ms << " ms." << std::endl;
        if (is_recording_flag) return fail("Cannot insert audio while recording.");

        std::vector<float> inserted;
        int sr = 0, ch = 0;
        std::string err;
        if (!read_audio_file(filePath, inserted, sr, ch, err)) return fail(err);

        std::unique_lock<std::shared_mutex> lk(buffer_mutex);
        if (sample_rate <= 0 || channels <= 0) return fail("Engine is not initialised. Load a file first.");
        if (sr != sample_rate) {
            return fail("Sample rate mismatch for inserted file. Expected: " + std::to_string(sample_rate) +
                        " Hz. Got: " + std::to_string(sr) + " Hz.");
        }

        std::vector<float> processed = convert_channels(inserted.data(), inserted.size() / static_cast<size_t>(ch), ch, channels);
        inserted.clear();
        inserted.shrink_to_fit();
        if (processed.empty()) return fail("Inserted file has no usable audio.");

        long insert_frame = static_cast<long>((static_cast<double>(position_ms) / 1000.0) * sample_rate);
        insert_frame = std::max(0L, std::min(insert_frame, static_cast<long>(audio_buffer.size() / channels)));

        ensure_history_baseline();
        audio_buffer.insert(audio_buffer.begin() + insert_frame * channels, processed.begin(), processed.end());

        recalculate_envelope_data();
        push_history();
        log_edl_command(ActionType::INSERT_AUDIO, "INSERT_AUDIO", position_ms, position_ms,
                        "Inserted audio segment from external file.", filePath);
        return 0;
    }

    // ------------------------------------------------------------------
    //  MİKROFON KAYDI
    // ------------------------------------------------------------------
    int start_microphone_recording() {
        std::cout << "Starting microphone recording." << std::endl;
        if (is_recording_flag) { std::cout << "Already recording." << std::endl; return 1; }
        if (is_playing_flag) return fail("Cannot record while playing.");

        if (record_stream) {            // önceki hatalı denemeden kalan akış
            Pa_StopStream(record_stream);
            Pa_CloseStream(record_stream);
            record_stream = nullptr;
        }

        PaHostApiIndex targetApiIndex = find_preferred_host_api();
        const PaHostApiInfo* targetApiInfo = Pa_GetHostApiInfo(targetApiIndex);
        if (!targetApiInfo) return fail("Could not get info for target Host API.");

        PaDeviceIndex device_index = targetApiInfo->defaultInputDevice;
        if (device_index == paNoDevice) {
            device_index = Pa_GetDefaultInputDevice();
            if (device_index == paNoDevice) return fail("No input (microphone) device found.");
        }
        const PaDeviceInfo* deviceInfo = Pa_GetDeviceInfo(device_index);
        if (!deviceInfo || deviceInfo->maxInputChannels <= 0) return fail("Selected device has no input channels.");

        // [DÜZELTME] Mikrofon, projedeki kanal sayısını desteklemiyorsa (ör. mono mikrofon + stereo proje)
        // cihazın verebildiği kanal sayısıyla açılır; eklerken proje kanal sayısına dönüştürülür.
        const int rec_ch = std::max(1, std::min(channels, deviceInfo->maxInputChannels));

        PaStreamParameters inputParameters{};
        inputParameters.device = device_index;
        inputParameters.channelCount = rec_ch;
        inputParameters.sampleFormat = paFloat32;
        inputParameters.suggestedLatency = deviceInfo->defaultLowInputLatency;
        inputParameters.hostApiSpecificStreamInfo = NULL;

        recorded_audio_buffer.clear();
        try {
            // 10 dakikalık ön rezerv (eskiden 30 dk ≈ 635 MB'lık tek seferlik ayırma yapılıyordu)
            recorded_audio_buffer.reserve(static_cast<size_t>(sample_rate) * static_cast<size_t>(rec_ch) * 600);
        } catch (...) {}
        record_channels = rec_ch;
        recorded_sample_rate = sample_rate;
        reset_mic_state();   // [DÜZELTME] önceki kayıttan kalan filtre durumu yeni kaydın başında tık yapıyordu

        // Bayrak akış başlamadan önce açılır; callback hemen kayda başlayabilir.
        is_recording_flag = true;

        PaError err = Pa_OpenStream(&record_stream, &inputParameters, NULL,
                                    static_cast<double>(sample_rate), paFramesPerBufferUnspecified,
                                    paClipOff, pa_record_callback, this);
        if (err != paNoError) {
            is_recording_flag = false;
            record_stream = nullptr;
            return fail(std::string("PortAudio error opening microphone: ") + Pa_GetErrorText(err));
        }
        err = Pa_StartStream(record_stream);
        if (err != paNoError) {
            is_recording_flag = false;
            Pa_CloseStream(record_stream);
            record_stream = nullptr;
            return fail(std::string("PortAudio error starting microphone: ") + Pa_GetErrorText(err));
        }

        std::cout << "Microphone recording started (" << rec_ch << " ch)." << std::endl;
        return 0;
    }

    int stop_microphone_recording() {
        std::cout << "Stopping microphone recording." << std::endl;
        if (!is_recording_flag) { std::cout << "Not currently recording." << std::endl; return 1; }

        PaError err = record_stream ? Pa_StopStream(record_stream) : paNoError;
        is_recording_flag = false;
        if (err != paNoError) {
            if (record_stream) Pa_CloseStream(record_stream);
            record_stream = nullptr;
            return fail(std::string("PortAudio error stopping microphone: ") + Pa_GetErrorText(err));
        }
        if (record_stream) {
            err = Pa_CloseStream(record_stream);
            record_stream = nullptr;
            if (err != paNoError) return fail(std::string("PortAudio error closing microphone: ") + Pa_GetErrorText(err));
        }
        std::cout << "Microphone recording stopped. Recorded " << recorded_audio_buffer.size() << " samples." << std::endl;
        return 0;
    }

    int play_recorded_audio() { return 0; }

    // Kaydı zaman çizelgesine ekle
    int insert_recorded_audio(int position_ms) {
        std::cout << "Inserting recorded audio at position " << position_ms << " ms." << std::endl;
        if (is_recording_flag) return fail("Stop the recording before inserting it.");
        if (recorded_audio_buffer.empty()) return fail("No recorded audio to insert.");
        if (record_channels <= 0) return fail("Recording has an invalid channel count.");

        std::unique_lock<std::shared_mutex> lk(buffer_mutex);
        if (sample_rate <= 0 || channels <= 0) return fail("Engine is not initialised.");
        if (recorded_sample_rate != sample_rate) {
            return fail("Recording sample rate differs from the project's sample rate.");
        }

        // [DÜZELTME] Eski kod, kanal sayısı eşleşen kaydı bile "mono/stereo dönüşümü" sanıp bozuyordu
        // (mono projede yarı uzunluğa düşürüyordu). Ayrıca kaydı 0.9'a normalize edip sessiz
        // kayıtlardaki gürültüyü şişiriyordu; dosyadan ekleme akışıyla tutarlı olması için kaldırıldı.
        std::vector<float> processed = convert_channels(
            recorded_audio_buffer.data(),
            recorded_audio_buffer.size() / static_cast<size_t>(record_channels),
            record_channels, channels);
        if (processed.empty()) return fail("Recording has no usable audio.");

        long insert_frame = static_cast<long>((static_cast<double>(position_ms) / 1000.0) * sample_rate);
        insert_frame = std::max(0L, std::min(insert_frame, static_cast<long>(audio_buffer.size() / channels)));

        ensure_history_baseline();
        audio_buffer.insert(audio_buffer.begin() + insert_frame * channels, processed.begin(), processed.end());

        recorded_audio_buffer.clear();
        recalculate_envelope_data();
        push_history();
        log_edl_command(ActionType::INSERT_RECORDING, "INSERT_MIC_RECORDING", position_ms, position_ms,
                        "Inserted live microphone recording at cursor.");
        std::cout << "Recorded audio inserted. New total duration: " << total_duration_ms << " ms." << std::endl;
        return 0;
    }

    // Düzenlenmiş sesi WAV olarak kaydet (atomik: bozuk/yarım dosya bırakmaz)
    int save_to_file(const std::string& filePath) {
        std::cout << "Saving edited audio to: " << filePath << std::endl;
        std::string err;
        {
            std::shared_lock<std::shared_mutex> lk(buffer_mutex);
            if (audio_buffer.empty() || sample_rate <= 0 || channels <= 0) return fail("No audio data to save.");
            if (!write_wav_atomic(filePath, audio_buffer.data(),
                                  audio_buffer.size() / static_cast<size_t>(channels),
                                  sample_rate, channels, err)) return fail(err);
        }
        log_edl_command(ActionType::EXPORT_FILE, "EXPORT_FILE", 0, total_duration_ms,
                        "Exported final audio session to file.", filePath);
        return 0;
    }

    int save_recorded_audio_to_file(const std::string& filePath) {
        std::cout << "Saving recorded audio to: " << filePath << std::endl;
        if (is_recording_flag) return fail("Stop the recording before saving it.");
        if (recorded_audio_buffer.empty() || record_channels <= 0) return fail("No recorded audio data to save.");
        std::string err;
        if (!write_wav_atomic(filePath, recorded_audio_buffer.data(),
                              recorded_audio_buffer.size() / static_cast<size_t>(record_channels),
                              recorded_sample_rate, record_channels, err)) return fail(err);
        return 0;
    }

    // ------------------------------------------------------------------
    //  MİKROFON İŞLEME AYARLARI
    // ------------------------------------------------------------------
    int set_noise_gate_threshold(float threshold) {
        mic_noise_gate_threshold = std::max(0.0f, std::min(1.0f, threshold));
        return 0;
    }
    int set_noise_gate_release(float ms) {
        mic_noise_gate_release_ms = std::max(0.0f, ms);
        return 0;
    }
    int set_high_pass_filter_cutoff(float hz) {
        mic_hp_cutoff_hz = hz;
        apply_mic_hp();
        return 0;
    }
    int set_microphone_gain(float gain) {
        mic_input_gain = std::max(0.0f, gain);
        return 0;
    }
    int set_microphone_low_pass_filter_cutoff(float hz) {
        mic_lp_cutoff_hz = hz;
        apply_mic_lp();
        return 0;
    }
    int set_reverb_reduction_level(int level) {
        reverb_level = level;
        apply_reverb();
        return 0;
    }
    int set_de_esser_level(int level) {
        de_esser_level = level;
        apply_de_esser();
        return 0;
    }
    int set_de_hum_level(int level) {
        de_hum_level = level;
        apply_de_hum();
        return 0;
    }
    int set_mic_compressor_threshold(float db_threshold) { mic_comp_threshold_db = db_threshold; return 0; }
    int set_mic_compressor_ratio(float ratio)            { mic_comp_ratio = std::max(1.0f, ratio); return 0; }
    int set_mic_compressor_attack(float ms)              { mic_comp_attack_ms = std::max(0.1f, ms); return 0; }
    int set_mic_compressor_release(float ms)             { mic_comp_release_ms = std::max(1.0f, ms); return 0; }
    int set_mic_compressor_makeup_gain(float db_gain)    { mic_comp_makeup_gain_db = db_gain; return 0; }

    int set_mic_eq_gain(float db_gain) {
        mic_eq_gain_db = db_gain;
        mic_eq_enabled = (db_gain != 0.0f);
        calculate_eq_coefficients();
        return 0;
    }
    int set_mic_eq_frequency(float hz) {
        mic_eq_frequency_hz = std::max(20.0f, std::min(20000.0f, hz));
        calculate_eq_coefficients();
        return 0;
    }
    int set_mic_eq_q(float q_val) {
        mic_eq_q = std::max(0.1f, q_val);
        calculate_eq_coefficients();
        return 0;
    }
};

// PortAudio geri çağırma fonksiyonu (Kayıt)
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

    if (inputBuffer == NULL || !engine->is_recording_flag) return paContinue;

    const int ch = engine->record_channels;
    // Durum vektörleri en az kayıt kanalı kadar büyük olmalı
    if (ch <= 0 || static_cast<size_t>(ch) > engine->mic_noise_gate_gain.size()) return paContinue;

    const float sr = static_cast<float>(engine->sample_rate);

    float noise_gate_release_gain_per_sample = 0.0f;
    if (engine->mic_noise_gate_release_ms > 0) {
        noise_gate_release_gain_per_sample = 1.0f / (engine->mic_noise_gate_release_ms / 1000.0f * sr);
    }
    float comp_attack_coeff = 0.0f;
    if (engine->mic_comp_attack_ms > 0) {
        comp_attack_coeff = std::exp(-1.0f / (engine->mic_comp_attack_ms / 1000.0f * sr));
    }
    float comp_release_coeff = 0.0f;
    if (engine->mic_comp_release_ms > 0) {
        comp_release_coeff = std::exp(-1.0f / (engine->mic_comp_release_ms / 1000.0f * sr));
    }
    // Döngü dışına alınan sabitler (eskiden her örnekte pow() hesaplanıyordu)
    const float comp_threshold_db = engine->mic_comp_threshold_db;
    const float comp_ratio = engine->mic_comp_ratio;
    const float makeup_gain_linear = std::pow(10.0f, engine->mic_comp_makeup_gain_db / 20.0f);

    const size_t old_size = engine->recorded_audio_buffer.size();
    engine->recorded_audio_buffer.resize(old_size + static_cast<size_t>(framesPerBuffer) * static_cast<size_t>(ch));
    float* dst = engine->recorded_audio_buffer.data() + old_size;

    for (unsigned long i = 0; i < framesPerBuffer; ++i) {
        for (int k = 0; k < ch; ++k) {
            float sample = in[i * ch + k];

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

            // [DÜZELTME] Sıkıştırma artık dB alanında hesaplanır (eski kod doğrusal genlik ile dB'yi karıştırıyordu)
            float gain_reduction = 1.0f;
            const float env = engine->mic_comp_envelope[k];
            if (comp_ratio > 1.0f && env > 1e-9f) {
                float env_db = 20.0f * std::log10(env);
                if (env_db > comp_threshold_db) {
                    float gain_reduction_db = (env_db - comp_threshold_db) * (1.0f - (1.0f / comp_ratio));
                    gain_reduction = std::pow(10.0f, -gain_reduction_db / 20.0f);
                }
            }
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

            dst[i * ch + k] = sample;
        }
    }
    return paContinue;
}

// PortAudio geri çağırma fonksiyonu (Oynatma)
// Konumun asıl kaynağı playback_position_frames'tir (double); hız 1.0 iken de aynı yol kullanılır,
// böylece hız değişse bile kesirli konum kaybolmaz.
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
    const int ch = engine->play_channels;
    if (ch <= 0 || !out) return paComplete;

    // Düzenleme sürerken asla bloklanma: o ara sessizlik üret.
    std::shared_lock<std::shared_mutex> lock(engine->buffer_mutex, std::try_to_lock);
    if (!lock.owns_lock()) {
        std::fill(out, out + framesPerBuffer * ch, 0.0f);
        return paContinue;
    }
    if (engine->channels != ch || engine->sample_rate <= 0) {
        std::fill(out, out + framesPerBuffer * ch, 0.0f);
        engine->is_playing_flag = false;
        return paComplete;
    }

    const long total_frames = static_cast<long>(engine->audio_buffer.size() / static_cast<size_t>(ch));
    const double speed = engine->current_speed.load();
    const int serial = engine->seek_serial.load();
    double pos = engine->playback_position_frames.load();
    bool finished = false;

    unsigned long i = 0;
    for (; i < framesPerBuffer; ++i) {
        long src_frame = static_cast<long>(pos);
        if (src_frame < 0) src_frame = 0;
        if (src_frame >= total_frames) { finished = true; break; }

        for (int k = 0; k < ch; ++k) {
            float sample = engine->audio_buffer[static_cast<size_t>(src_frame) * ch + k];
            float filtered = engine->lp_filter_alpha * sample +
                             (1.0f - engine->lp_filter_alpha) * engine->lp_filter_prev_output[k];
            out[i * ch + k] = filtered;
            engine->lp_filter_prev_output[k] = filtered;
        }
        pos += speed;
    }
    if (finished) std::fill(out + i * ch, out + framesPerBuffer * ch, 0.0f);

    // Kullanıcı bu arada konum değiştirdiyse (seek) onun değerini ezme
    if (engine->seek_serial.load() == serial) {
        if (finished) {
            engine->playback_position_frames = static_cast<double>(total_frames);
            engine->playback_frame_index = total_frames;
            engine->current_play_position_ms = engine->total_duration_ms;
        } else {
            engine->playback_position_frames = pos;
            engine->playback_frame_index = static_cast<long>(pos);
            engine->current_play_position_ms = static_cast<int>((pos / engine->sample_rate) * 1000.0);
        }
    }

    if (finished) {
        engine->is_playing_flag = false;
        return paComplete;
    }
    return paContinue;
}

// =====================================================================
//  C ARAYÜZÜ (extern "C")
//  Mevcut fonksiyon adları ve imzaları AYNEN korunmuştur.
//  [DÜZELTME] Her çağrı try/catch ile sarıldı: bir C++ istisnası (ör. bellek yetersizliği)
//  ctypes sınırından geçerse tüm uygulama çöker; artık hata kodu olarak döner.
// =====================================================================
template <typename F>
static int safe_call(F&& f, int fallback = -1) noexcept {
    try {
        return f();
    } catch (const std::exception& e) {
        std::cerr << "AudioEngine exception: " << e.what() << std::endl;
    } catch (...) {
        std::cerr << "AudioEngine: unknown exception." << std::endl;
    }
    return fallback;
}

static inline AudioEngine* E(void* p) { return static_cast<AudioEngine*>(p); }

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
        return safe_call([&] { return E(ptr)->load_files(filePaths, numFiles); });
    }

    // --- .sound paketi (ses + metin) : TAMAMEN C++ ---
    // Dönüş: 0 = tamam, 1 = ses yüklendi ama metadata eksik/bozuk, -1 = hata
    int load_sound_package(void* ptr, const char* filePath) {
        if (!ptr || !filePath) return -1;
        return safe_call([&] { return E(ptr)->load_sound_package(std::string(filePath)); });
    }
    int save_sound_package(void* ptr, const char* filePath, const char* text_utf8, int text_len,
                           int alignment_center, int font_size) {
        if (!ptr || !filePath) return -1;
        return safe_call([&] {
            std::string text;
            if (text_utf8 && text_len > 0) text.assign(text_utf8, static_cast<size_t>(text_len));
            return E(ptr)->save_sound_package(std::string(filePath), text, alignment_center != 0, font_size);
        });
    }
    int get_package_text_size(void* ptr) {
        if (!ptr) return 0;
        return static_cast<int>(E(ptr)->pkg_text.size());
    }
    // buf'a en fazla cap bayt kopyalar (NUL eklemez); kopyalanan bayt sayısını döndürür
    int copy_package_text(void* ptr, char* buf, int cap) {
        if (!ptr || !buf || cap <= 0) return 0;
        const std::string& t = E(ptr)->pkg_text;
        int n = static_cast<int>(std::min<size_t>(t.size(), static_cast<size_t>(cap)));
        if (n > 0) std::memcpy(buf, t.data(), static_cast<size_t>(n));
        return n;
    }
    int get_package_alignment_center(void* ptr) { if (!ptr) return 0; return E(ptr)->pkg_alignment_center; }
    int get_package_font_size(void* ptr) { if (!ptr) return 14; return E(ptr)->pkg_font_size; }

    // Son hata/uyarı metni (UTF-8) ve atlanan dosya sayısı
    const char* get_last_error(void* ptr) { if (!ptr) return ""; return E(ptr)->last_error.c_str(); }
    int get_last_load_skipped_files(void* ptr) { if (!ptr) return 0; return E(ptr)->last_load_skipped; }

    // --- Playback Control ---
    int play_audio(void* ptr) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->play(); }); }
    int pause_audio(void* ptr) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->pause(); }); }
    int stop_audio(void* ptr) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->stop(); }); }

    // --- Information Retrieval ---
    int get_position_ms(void* ptr) { if (!ptr) return 0; return E(ptr)->get_position_ms(); }
    int get_duration_ms(void* ptr) { if (!ptr) return 0; return E(ptr)->get_duration_ms(); }
    int get_is_playing(void* ptr) { if (!ptr) return 0; return E(ptr)->get_is_playing(); }

    // --- Waveform Data ---
    int get_envelope_length(void* ptr) { if (!ptr) return 0; return E(ptr)->get_envelope_length(); }
    const float* get_envelope_data(void* ptr) { if (!ptr) return nullptr; return E(ptr)->get_envelope_data(); }

    // --- Settings ---
    int set_speed(void* ptr, float speed) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_speed(speed); }); }
    int set_play_position_ms(void* ptr, int ms) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_play_position_ms(ms); }); }

    // --- Editing ---
    int delete_audio_segment(void* ptr, int start_ms, int end_ms) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->delete_segment(start_ms, end_ms); }); }
    int insert_audio_file(void* ptr, const char* filePath, int position_ms) {
        if (!ptr || !filePath) return -1;
        return safe_call([&] { return E(ptr)->insert_audio(std::string(filePath), position_ms); });
    }

    int detect_and_delete_similar(void* ptr, int start_ms, int end_ms, float threshold) {
        if (!ptr) return -1;
        return safe_call([&] { return E(ptr)->detect_and_delete_similar_segments(start_ms, end_ms, threshold); });
    }

    int delete_segments_by_thickness(void* ptr, int start_ms, int end_ms) {
        if (!ptr) return -1;
        return safe_call([&] { return E(ptr)->delete_segments_by_thickness(start_ms, end_ms); });
    }

    // --- Microphone Recording ---
    int start_microphone_recording(void* ptr) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->start_microphone_recording(); }); }
    int stop_microphone_recording(void* ptr) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->stop_microphone_recording(); }); }
    int play_recorded_audio(void* ptr) { if (!ptr) return -1; return E(ptr)->play_recorded_audio(); }
    int insert_recorded_audio(void* ptr, int position_ms) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->insert_recorded_audio(position_ms); }); }

    // --- Save Audio ---
    int save_audio_to_file(void* ptr, const char* filePath) {
        if (!ptr || !filePath) return -1;
        return safe_call([&] { return E(ptr)->save_to_file(std::string(filePath)); });
    }

    // --- Undo / Redo ---
    int undo_audio(void* ptr) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->undo(); }); }
    int redo_audio(void* ptr) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->redo(); }); }
    int can_undo_audio(void* ptr) { if (!ptr) return 0; return E(ptr)->can_undo(); }
    int can_redo_audio(void* ptr) { if (!ptr) return 0; return E(ptr)->can_redo(); }

    // --- EDL ---
    int Export_edl_log(void* ptr) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->Export_edl_to_file(); }); }

    // --- Mikrofon İşleme ---
    int set_mic_noise_gate_threshold(void* ptr, float threshold) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_noise_gate_threshold(threshold); }); }
    int set_mic_noise_gate_release(void* ptr, float ms) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_noise_gate_release(ms); }); }
    int set_mic_high_pass_filter_cutoff(void* ptr, float hz) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_high_pass_filter_cutoff(hz); }); }
    int set_mic_input_gain(void* ptr, float gain) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_microphone_gain(gain); }); }
    int set_mic_low_pass_filter_cutoff(void* ptr, float hz) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_microphone_low_pass_filter_cutoff(hz); }); }
    int set_mic_reverb_reduction_level(void* ptr, int level) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_reverb_reduction_level(level); }); }
    int set_mic_de_esser_level(void* ptr, int level) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_de_esser_level(level); }); }
    int set_mic_de_hum_level(void* ptr, int level) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_de_hum_level(level); }); }

    // Compressor
    int set_mic_compressor_threshold(void* ptr, float db_threshold) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_mic_compressor_threshold(db_threshold); }); }
    int set_mic_compressor_ratio(void* ptr, float ratio) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_mic_compressor_ratio(ratio); }); }
    int set_mic_compressor_attack(void* ptr, float ms) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_mic_compressor_attack(ms); }); }
    int set_mic_compressor_release(void* ptr, float ms) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_mic_compressor_release(ms); }); }
    int set_mic_compressor_makeup_gain(void* ptr, float db_gain) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_mic_compressor_makeup_gain(db_gain); }); }

    // Parametric EQ
    int set_mic_eq_gain(void* ptr, float db_gain) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_mic_eq_gain(db_gain); }); }
    int set_mic_eq_frequency(void* ptr, float hz) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_mic_eq_frequency(hz); }); }
    int set_mic_eq_q(void* ptr, float q_val) { if (!ptr) return -1; return safe_call([&] { return E(ptr)->set_mic_eq_q(q_val); }); }

    int calculate_eq_coefficients(void* ptr) { if (!ptr) return -1; E(ptr)->calculate_eq_coefficients(); return 0; }

    int save_recorded_audio_to_file(void* ptr, const char* filePath) {
        if (!ptr || !filePath) return -1;
        return safe_call([&] { return E(ptr)->save_recorded_audio_to_file(std::string(filePath)); });
    }
} // End of extern "C" block
