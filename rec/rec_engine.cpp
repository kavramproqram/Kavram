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

/*
 * DERLEME (Ubuntu/Debian):
 *   sudo apt install g++ pkg-config libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
 *        libglib2.0-dev
 *   g++ -std=c++17 -O2 -Wall camera_recorder.cpp -o camera_recorder \
 *       $(pkg-config --cflags --libs gstreamer-1.0 gstreamer-app-1.0 gstreamer-video-1.0 gio-2.0)
 *
 * ÇALIŞMA ZAMANI (kayıt/önizleme için GStreamer eklentileri):
 *   gstreamer1.0-plugins-base  (videoconvert, videoscale, videorate, audioconvert, appsink)
 *   gstreamer1.0-plugins-good  (ximagesrc, v4l2src, pulsesrc, matroskamux, level)
 *   gstreamer1.0-plugins-ugly  (x264enc)
 *   gstreamer1.0-plugins-bad   (h264parse, aacparse, voaacenc)
 *   gstreamer1.0-pipewire      (pipewiresrc  -> yalnızca Wayland ekran kaydı)
 *   gstreamer1.0-libav         (isteğe bağlı: avenc_aac / MJPEG kamera çözücü)
 *
 * KOMUTLAR:
 *   --record <anahtar=değer ...>   Kayıt (ekran + ses, tek dosya, süresiz) + canlı önizleme
 *                                  stdin komutları: PAUSE / RESUME (durdurma = SIGINT)
 *   --preview <anahtar=değer ...>  Yalnızca önizleme (dosya yazmaz)
 *   --record-wayland <dir> <start> <seg> <fps> <w> <h>   (eski arayüz, korunur)
 *   --merge-recordings <video_list> <audio_list> <out>   (eski arayüz, korunur)
 *   --list-cameras                 Kullanılabilir kameraları "yol|ad" olarak yazar
 *   --capabilities                 Motor sürümü ve eklenti durumu
 *
 * ÇIKIŞ KODLARI:  0 = normal, 1 = genel hata, 2 = kamera hatası,
 *                 3 = ekran paylaşımı reddedildi/iptal, 4 = ses hatası,
 *                 5 = eksik GStreamer eklentisi
 *
 * ÖNİZLEME AKTARIMI: Önizleme kareleri küçük ve BGRx biçiminde /dev/shm altındaki
 * paylaşımlı bellek dosyasına yazılır; PyQt arayüzü bunu sıfır-kopya yakın okur.
 * Böylece ağır bir boru (pipe) trafiği olmaz, eski bilgisayarlarda bile akıcıdır.
 */

#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <set>
#include <thread>
#include <chrono>
#include <fstream>
#include <sstream>
#include <cstdlib> // For system()
#include <cstdio>  // For popen/pclose
#include <cstring>
#include <cerrno>
#include <filesystem> // C++17 for file system operations
#include <algorithm>
#include <utility>
#include <csignal>
#include <ctime>
#include <unistd.h> // For access()
#include <fcntl.h>
#include <dirent.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <linux/videodev2.h>

#include <gio/gio.h>
#include <glib.h>
#include <glib/gstdio.h>
#include <gst/gst.h>
#include <gst/app/gstappsink.h>
#include <gst/video/video.h>

#define KAVRAM_WAYLAND_RECORDER 1
#define KAVRAM_ENGINE_VERSION 1

// ============================================================
// Genel yardımcılar
// ============================================================
static volatile std::sig_atomic_t g_stop_requested = 0;
static volatile std::sig_atomic_t g_preview_cmd = 0;   // 0: yok, 1: aç, 2: kapat
static bool g_fake_sources = false;                    // KAVRAM_FAKE_SOURCES=1 (test)

static void on_stop_signal(int) { g_stop_requested = 1; }
static void on_usr1_signal(int) { g_preview_cmd = 1; }
static void on_usr2_signal(int) { g_preview_cmd = 2; }

static void log_info(const std::string &s) { std::cout << "C++: " << s << std::endl; }
static void log_err(const std::string &s)  { std::cerr << "C++ Hata: " << s << std::endl; }
static void emit_event(const std::string &s) { std::cout << "EVENT " << s << std::endl; }

static uint64_t mono_ms()
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return static_cast<uint64_t>(ts.tv_sec) * 1000ull + static_cast<uint64_t>(ts.tv_nsec / 1000000);
}

typedef std::map<std::string, std::string> KV;

static KV parse_kv(int argc, char **argv, int from)
{
    KV kv;
    for (int i = from; i < argc; ++i) {
        std::string a = argv[i];
        size_t eq = a.find('=');
        if (eq == std::string::npos || eq == 0) continue;
        kv[a.substr(0, eq)] = a.substr(eq + 1);
    }
    return kv;
}

static std::string kv_str(const KV &kv, const char *key, const std::string &def = "")
{
    auto it = kv.find(key);
    return it == kv.end() ? def : it->second;
}

static int kv_int(const KV &kv, const char *key, int def)
{
    auto it = kv.find(key);
    if (it == kv.end() || it->second.empty()) return def;
    try { return std::stoi(it->second); } catch (...) { return def; }
}

static bool have_factory(const char *name)
{
    GstElementFactory *f = gst_element_factory_find(name);
    if (f) { gst_object_unref(f); return true; }
    return false;
}

// Bir eleman fabrikasının belirli bir özelliği var mı? (eski GStreamer sürümlerine uyum için)
static bool factory_has_prop(const char *factory, const char *prop)
{
    GstElement *e = gst_element_factory_make(factory, nullptr);
    if (!e) return false;
    bool ok = g_object_class_find_property(G_OBJECT_GET_CLASS(e), prop) != nullptr;
    gst_object_unref(e);
    return ok;
}

static bool dir_is_safe(const std::string &p)
{
    return !p.empty() && p.find('"') == std::string::npos && p.find('\n') == std::string::npos;
}


// ============================================================
// KAVRAM_WAYLAND_RECORDER
// Wayland -> xdg-desktop-portal -> PipeWire -> GStreamer
//
// Portal izni alınır, ScreenCast session oluşturulur,
// PipeWire node id alınır ve GStreamer pipeline bu node üzerinden
// GERÇEK ekran görüntüsünü çeker.
//
// Önemli not: pipewiresrc 'always-copy=true' olmadan portal
// üzerinden gelen buffer'lar bazen yalnızca imleç güncellemesi
// olarak yansıyor. cursor_mode=2 (embedded) ile imleç karenin
// içine gömülür.
//
// YENİ: Portal yanıt sinyali artık çağrıdan ÖNCE dinlenir (hızlı yanıt
// yarışı yok) ve restore_token saklanır; böylece ilk izinden sonra
// her kayıtta/önizlemede tekrar tekrar iletişim kutusu çıkmaz.
// ============================================================
struct PortalResponse {
    guint code = 999;
    GVariant *results = nullptr;
    bool received = false;
};

struct PortalSession {
    GDBusConnection *bus = nullptr;
    std::string handle;
    guint node_id = 0;
};

static void free_portal_response(PortalResponse &response)
{
    if (response.results) {
        g_variant_unref(response.results);
        response.results = nullptr;
    }
}

static void on_wayland_portal_response(
    GDBusConnection *,
    const gchar *,
    const gchar *,
    const gchar *,
    const gchar *,
    GVariant *parameters,
    gpointer user_data)
{
    auto *response = static_cast<PortalResponse *>(user_data);

    guint code = 999;
    GVariant *results = nullptr;

    g_variant_get(parameters, "(u@a{sv})", &code, &results);

    response->code = code;
    response->results = results;
    response->received = true;
}

static std::string portal_make_token(const char *prefix)
{
    static int counter = 0;
    return std::string(prefix) + "_" + std::to_string(static_cast<long>(getpid())) +
           "_" + std::to_string(++counter);
}

static std::string portal_request_path(GDBusConnection *bus, const std::string &token)
{
    const gchar *unique = g_dbus_connection_get_unique_name(bus);
    std::string sender = unique ? unique : "";
    if (!sender.empty() && sender[0] == ':') sender.erase(0, 1);
    for (auto &ch : sender) if (ch == '.') ch = '_';
    return "/org/freedesktop/portal/desktop/request/" + sender + "/" + token;
}

// method: "CreateSession" | "SelectSources" | "Start"
static bool portal_call(
    GDBusConnection *bus,
    const char *method,
    const std::string &session_handle,
    GVariantBuilder *options,
    PortalResponse &response)
{
    std::string token = portal_make_token("kvreq");
    std::string request_path = portal_request_path(bus, token);

    g_variant_builder_add(options, "{sv}", "handle_token",
                          g_variant_new_string(token.c_str()));

    // Yanıt sinyali, çağrıdan önce dinlenmeli (hızlı yanıtlarda kaçmasın)
    guint subscription = g_dbus_connection_signal_subscribe(
        bus,
        "org.freedesktop.portal.Desktop",
        "org.freedesktop.portal.Request",
        "Response",
        request_path.c_str(),
        nullptr,
        G_DBUS_SIGNAL_FLAGS_NONE,
        on_wayland_portal_response,
        &response,
        nullptr);

    if (!subscription) {
        log_err(std::string("Wayland: ") + method + " için yanıt dinleyicisi kurulamadı.");
        g_variant_builder_clear(options);
        return false;
    }

    GVariant *params = nullptr;
    if (std::strcmp(method, "CreateSession") == 0) {
        params = g_variant_new("(a{sv})", options);
    } else if (std::strcmp(method, "SelectSources") == 0) {
        params = g_variant_new("(oa{sv})", session_handle.c_str(), options);
    } else {
        params = g_variant_new("(osa{sv})", session_handle.c_str(), "", options);
    }

    GError *error = nullptr;
    GVariant *reply = g_dbus_connection_call_sync(
        bus,
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.portal.ScreenCast",
        method,
        params,
        G_VARIANT_TYPE("(o)"),
        G_DBUS_CALL_FLAGS_NONE,
        -1,
        nullptr,
        &error);

    if (!reply) {
        log_err(std::string("Wayland: ") + method + ": " +
                (error ? error->message : "bilinmeyen hata"));
        if (error) g_error_free(error);
        g_dbus_connection_signal_unsubscribe(bus, subscription);
        return false;
    }
    g_variant_unref(reply);

    // Kullanıcı kaynak seçerken uzun sürebilir (2 dk). Durdurma isteği gelirse bırak.
    const gint64 deadline = g_get_monotonic_time() + 120 * G_USEC_PER_SEC;
    bool ok = true;
    while (!response.received) {
        while (g_main_context_pending(nullptr)) {
            g_main_context_iteration(nullptr, FALSE);
        }
        if (response.received) break;
        if (g_stop_requested) { ok = false; break; }
        if (g_get_monotonic_time() >= deadline) {
            log_err(std::string("Wayland: ") + method + " yanıtı zaman aşımına uğradı.");
            ok = false;
            break;
        }
        g_usleep(2000);
    }

    g_dbus_connection_signal_unsubscribe(bus, subscription);
    return ok;
}

static std::string portal_token_path(const std::string &custom)
{
    if (!custom.empty()) return custom;
    gchar *dir = g_build_filename(g_get_user_config_dir(), "Kavram", nullptr);
    g_mkdir_with_parents(dir, 0700);
    gchar *file = g_build_filename(dir, "screencast_restore_token", nullptr);
    std::string path = file;
    g_free(file);
    g_free(dir);
    return path;
}

static std::string portal_load_token(const std::string &path)
{
    std::ifstream in(path);
    std::string tok;
    if (in) std::getline(in, tok);
    while (!tok.empty() && (tok.back() == '\r' || tok.back() == '\n' || tok.back() == ' ')) tok.pop_back();
    return tok;
}

static void portal_save_token(const std::string &path, const std::string &token)
{
    if (token.empty()) return;
    std::ofstream out(path, std::ios::trunc);
    if (out) {
        out << token << "\n";
        out.close();
        chmod(path.c_str(), 0600);
    }
}

// Portal ScreenCast arayüz sürümü (restore_token için >= 4 gerekir). 0 = bilinmiyor.
static guint portal_screencast_version(GDBusConnection *bus)
{
    GError *error = nullptr;
    GVariant *reply = g_dbus_connection_call_sync(
        bus,
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
        "org.freedesktop.DBus.Properties",
        "Get",
        g_variant_new("(ss)", "org.freedesktop.portal.ScreenCast", "version"),
        G_VARIANT_TYPE("(v)"),
        G_DBUS_CALL_FLAGS_NONE,
        1500,
        nullptr,
        &error);
    if (!reply) {
        if (error) g_error_free(error);
        return 0;
    }
    GVariant *inner = nullptr;
    g_variant_get(reply, "(v)", &inner);
    guint version = 0;
    if (inner) {
        if (g_variant_is_of_type(inner, G_VARIANT_TYPE_UINT32)) version = g_variant_get_uint32(inner);
        g_variant_unref(inner);
    }
    g_variant_unref(reply);
    return version;
}

static bool create_wayland_session(GDBusConnection *bus, std::string &session_handle)
{
    GVariantBuilder options;
    g_variant_builder_init(&options, G_VARIANT_TYPE("a{sv}"));

    std::string token = portal_make_token("kavram_session");
    g_variant_builder_add(&options, "{sv}", "session_handle_token",
                          g_variant_new_string(token.c_str()));

    PortalResponse response;
    if (!portal_call(bus, "CreateSession", "", &options, response)) {
        free_portal_response(response);
        return false;
    }

    if (response.code != 0 || !response.results) {
        log_err("Wayland: CreateSession reddedildi. Kod=" + std::to_string(response.code));
        free_portal_response(response);
        return false;
    }

    GVariant *value = g_variant_lookup_value(response.results, "session_handle", G_VARIANT_TYPE_STRING);
    if (value) {
        const gchar *handle = g_variant_get_string(value, nullptr);
        if (handle) session_handle = handle;
        g_variant_unref(value);
    }
    free_portal_response(response);

    return !session_handle.empty();
}

// code_out: portal yanıt kodu (0 = tamam, 1 = kullanıcı iptal, 2 = diğer)
static bool select_wayland_monitor(
    GDBusConnection *bus,
    const std::string &session_handle,
    const std::string &restore_token,
    guint &code_out)
{
    GVariantBuilder options;
    g_variant_builder_init(&options, G_VARIANT_TYPE("a{sv}"));

    // types: 1 = MONITOR (tüm ekran)
    g_variant_builder_add(&options, "{sv}", "types", g_variant_new_uint32(1));
    g_variant_builder_add(&options, "{sv}", "multiple", g_variant_new_boolean(FALSE));

    /*
     * cursor_mode:
     *   1 = Hidden
     *   2 = Embedded  (imleç görüntüye gömülür)   <-- KULLANDIĞIMIZ
     *   4 = Metadata  (imleç ayrı metadata)
     */
    g_variant_builder_add(&options, "{sv}", "cursor_mode", g_variant_new_uint32(2));

    // İzni hatırla (portal >= 4): bir sonraki kayıtta tekrar sormaz.
    g_variant_builder_add(&options, "{sv}", "persist_mode", g_variant_new_uint32(2));
    if (!restore_token.empty()) {
        g_variant_builder_add(&options, "{sv}", "restore_token",
                              g_variant_new_string(restore_token.c_str()));
    }

    PortalResponse response;
    if (!portal_call(bus, "SelectSources", session_handle, &options, response)) {
        free_portal_response(response);
        return false;
    }

    code_out = response.code;
    bool success = response.code == 0;
    if (!success) {
        log_err("Wayland: SelectSources reddedildi. Kod=" + std::to_string(response.code));
    }
    free_portal_response(response);
    return success;
}

static bool start_wayland_portal(
    GDBusConnection *bus,
    const std::string &session_handle,
    const std::string &token_path,
    guint &node_id_out,
    guint &code_out)
{
    GVariantBuilder options;
    g_variant_builder_init(&options, G_VARIANT_TYPE("a{sv}"));

    PortalResponse response;
    if (!portal_call(bus, "Start", session_handle, &options, response)) {
        free_portal_response(response);
        return false;
    }

    code_out = response.code;
    if (response.code != 0 || !response.results) {
        log_err("Wayland: Start reddedildi. Kod=" + std::to_string(response.code));
        free_portal_response(response);
        return false;
    }

    // Yeni restore_token varsa sakla
    {
        const gchar *tok = nullptr;
        if (g_variant_lookup(response.results, "restore_token", "&s", &tok) && tok) {
            portal_save_token(token_path, tok);
        }
    }

    GVariant *streams = g_variant_lookup_value(response.results, "streams", G_VARIANT_TYPE("a(ua{sv})"));
    if (!streams) {
        log_err("Wayland: Stream listesi bulunamadı.");
        free_portal_response(response);
        return false;
    }

    GVariantIter iter;
    GVariant *stream = nullptr;
    g_variant_iter_init(&iter, streams);

    if (!g_variant_iter_next(&iter, "@(ua{sv})", &stream)) {
        g_variant_unref(streams);
        free_portal_response(response);
        log_err("Wayland: Stream alınamadı.");
        return false;
    }

    guint32 node_id = 0;
    GVariant *properties = nullptr;
    g_variant_get(stream, "(u@a{sv})", &node_id, &properties);

    node_id_out = node_id;

    if (properties) g_variant_unref(properties);
    g_variant_unref(stream);
    g_variant_unref(streams);
    free_portal_response(response);

    if (!node_id_out) {
        log_err("Wayland: PipeWire node ID alınamadı.");
        return false;
    }

    log_info("Wayland: PipeWire node ID = " + std::to_string(node_id_out));
    return true;
}

static void close_wayland_session(GDBusConnection *bus, const std::string &session_handle)
{
    if (!bus || session_handle.empty()) return;

    GError *error = nullptr;
    GVariant *reply = g_dbus_connection_call_sync(
        bus,
        "org.freedesktop.portal.Desktop",
        session_handle.c_str(),
        "org.freedesktop.portal.Session",
        "Close",
        nullptr,
        nullptr,
        G_DBUS_CALL_FLAGS_NONE,
        5000,
        nullptr,
        &error);

    if (!reply) {
        if (error) {
            std::cerr << "C++ Wayland Uyarı: Portal session kapatılamadı: " << error->message << std::endl;
            g_error_free(error);
        }
        return;
    }
    g_variant_unref(reply);
}

// Tam portal akışı. Başarılıysa node_id dolar. exit_code: 0 tamam, 3 iptal/izin yok, 1 hata
static bool open_wayland_portal(PortalSession &ps, const std::string &token_file, int &exit_code)
{
    exit_code = 1;

    const char *wayland = g_getenv("WAYLAND_DISPLAY");
    if (!wayland) {
        log_err("Wayland: WAYLAND_DISPLAY bulunamadı.");
        return false;
    }

    GError *error = nullptr;
    ps.bus = g_bus_get_sync(G_BUS_TYPE_SESSION, nullptr, &error);
    if (!ps.bus) {
        log_err(std::string("Wayland: D-Bus bağlantısı kurulamadı: ") +
                (error ? error->message : "bilinmeyen hata"));
        if (error) g_error_free(error);
        return false;
    }

    const std::string token_path = portal_token_path(token_file);
    const std::string restore_token = portal_load_token(token_path);

    log_info("Wayland: Portal session oluşturuluyor...");
    if (!create_wayland_session(ps.bus, ps.handle)) {
        return false;
    }

    log_info(restore_token.empty()
                 ? "Wayland: Kullanıcıdan kaynak seçmesi isteniyor..."
                 : "Wayland: Kayıtlı izin kullanılıyor (gerekirse yeniden sorulur)...");

    guint code = 0;
    if (!select_wayland_monitor(ps.bus, ps.handle, restore_token, code)) {
        exit_code = (code == 1 || g_stop_requested) ? 3 : 1;
        return false;
    }

    log_info("Wayland: Portal Start çağrısı ve PipeWire node bekleniyor...");
    if (!start_wayland_portal(ps.bus, ps.handle, token_path, ps.node_id, code)) {
        exit_code = (code == 1 || g_stop_requested) ? 3 : 1;
        return false;
    }

    exit_code = 0;
    return true;
}


// ============================================================
// Kamera listesi (V4L2)
// ============================================================
struct CameraInfo {
    std::string path;
    std::string name;
};

static std::vector<CameraInfo> enumerate_cameras()
{
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
        bool ok = ioctl(fd, VIDIOC_QUERYCAP, &cap) == 0;
        close(fd);
        if (!ok) continue;

        __u32 caps = (cap.capabilities & V4L2_CAP_DEVICE_CAPS) ? cap.device_caps : cap.capabilities;
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

static int cmd_list_cameras()
{
    for (auto &c : enumerate_cameras()) {
        std::cout << c.path << "|" << c.name << std::endl;
    }
    return 0;
}

static int cmd_capabilities()
{
    gst_init(nullptr, nullptr);

    std::cout << "engine=" << KAVRAM_ENGINE_VERSION << std::endl;
    const char *names[] = {
        "x264enc", "openh264enc", "vp8enc", "h264parse", "splitmuxsink", "matroskamux",
        "ximagesrc", "pipewiresrc", "v4l2src", "pulsesrc", "decodebin", "level",
        "voaacenc", "avenc_aac", "fdkaacenc", "appsink", nullptr
    };
    for (int i = 0; names[i]; ++i) {
        std::cout << names[i] << "=" << (have_factory(names[i]) ? 1 : 0) << std::endl;
    }

    int restore = 0;
    const char *wl = g_getenv("WAYLAND_DISPLAY");
    if (wl) {
        GError *error = nullptr;
        GDBusConnection *bus = g_bus_get_sync(G_BUS_TYPE_SESSION, nullptr, &error);
        if (bus) {
            restore = portal_screencast_version(bus) >= 4 ? 1 : 0;
            g_object_unref(bus);
        } else if (error) {
            g_error_free(error);
        }
    }
    std::cout << "portal_restore=" << restore << std::endl;
    return 0;
}


// ============================================================
// Önizleme: paylaşımlı bellek (BGRx kareler) ve ses seviyesi
//
// Başlık (64 bayt, little-endian):
//   0 u32 magic 'KVPV' (0x5650564B)   4 u32 version
//   8 u32 width      12 u32 height     16 u32 stride    20 u32 format(1=BGRx)
//  24 u64 seq (tek = yazılıyor)        32 u64 stamp_ms (CLOCK_MONOTONIC)
//  40 u32 payload   44 u32 capacity
// Veri 64. bayttan başlar.
//
// Ses seviyesi dosyası:
//   0 u32 magic 'KVLV' (0x564C564B)   4 u32 version
//   8 u64 seq   16 u64 stamp_ms   24 f32 peak[2]   32 f32 rms[2]   40 u32 channels
// ============================================================
struct PvHeader {
    uint32_t magic;
    uint32_t version;
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    uint32_t format;
    uint64_t seq;
    uint64_t stamp_ms;
    uint32_t payload;
    uint32_t capacity;
    uint32_t pad[4];
};
static_assert(sizeof(PvHeader) == 64, "PvHeader 64 bayt olmalı");

struct LvHeader {
    uint32_t magic;
    uint32_t version;
    uint64_t seq;
    uint64_t stamp_ms;
    float peak[2];
    float rms[2];
    uint32_t channels;
    uint32_t pad;
};

static void *shm_create(const std::string &path, size_t size, int &fd_out)
{
    fd_out = -1;
    if (path.empty()) return nullptr;

    unlink(path.c_str()); // /dev/shm ortak dizin: önce eskisini kaldır
    int fd = open(path.c_str(), O_RDWR | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (fd < 0) {
        log_err("Önizleme belleği oluşturulamadı: " + path + " (" + std::strerror(errno) + ")");
        return nullptr;
    }
    if (ftruncate(fd, static_cast<off_t>(size)) != 0) {
        close(fd);
        unlink(path.c_str());
        return nullptr;
    }
    void *map = mmap(nullptr, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (map == MAP_FAILED) {
        close(fd);
        unlink(path.c_str());
        return nullptr;
    }
    fd_out = fd;
    return map;
}

struct PvShm {
    std::string path;
    int fd = -1;
    uint8_t *map = nullptr;
    size_t size = 0;
    size_t capacity = 0;
    uint64_t seq = 0;

    bool create(const std::string &p, size_t cap)
    {
        if (p.empty()) return false;
        capacity = cap;
        size = sizeof(PvHeader) + cap;
        void *m = shm_create(p, size, fd);
        if (!m) return false;
        map = static_cast<uint8_t *>(m);
        path = p;
        auto *h = reinterpret_cast<PvHeader *>(map);
        std::memset(h, 0, sizeof(PvHeader));
        h->version = 1;
        h->format = 1;
        h->capacity = static_cast<uint32_t>(cap);
        __atomic_store_n(&h->magic, 0x5650564Bu, __ATOMIC_RELEASE);
        return true;
    }

    bool active() const { return map != nullptr; }

    void write_frame(int w, int hgt, const uint8_t *src, int src_stride)
    {
        if (!map || w <= 0 || hgt <= 0) return;
        const size_t row = static_cast<size_t>(w) * 4;
        const size_t payload = row * static_cast<size_t>(hgt);
        if (payload > capacity) return;

        auto *h = reinterpret_cast<PvHeader *>(map);
        __atomic_store_n(&h->seq, ++seq, __ATOMIC_RELEASE);          // tek: yazılıyor
        uint8_t *dst = map + sizeof(PvHeader);
        if (static_cast<size_t>(src_stride) == row) {
            std::memcpy(dst, src, payload);
        } else {
            for (int y = 0; y < hgt; ++y) {
                std::memcpy(dst + static_cast<size_t>(y) * row, src + static_cast<size_t>(y) * src_stride, row);
            }
        }
        h->width = static_cast<uint32_t>(w);
        h->height = static_cast<uint32_t>(hgt);
        h->stride = static_cast<uint32_t>(row);
        h->payload = static_cast<uint32_t>(payload);
        h->stamp_ms = mono_ms();
        __atomic_store_n(&h->seq, ++seq, __ATOMIC_RELEASE);          // çift: tamam
    }

    void destroy()
    {
        if (map) munmap(map, size);
        if (fd >= 0) close(fd);
        if (!path.empty()) unlink(path.c_str());
        map = nullptr; fd = -1; path.clear();
    }
};

struct LvShm {
    std::string path;
    int fd = -1;
    LvHeader *hdr = nullptr;
    uint64_t seq = 0;

    bool create(const std::string &p)
    {
        if (p.empty()) return false;
        void *m = shm_create(p, sizeof(LvHeader), fd);
        if (!m) return false;
        hdr = static_cast<LvHeader *>(m);
        path = p;
        std::memset(hdr, 0, sizeof(LvHeader));
        hdr->version = 1;
        hdr->peak[0] = hdr->peak[1] = -120.0f;
        hdr->rms[0] = hdr->rms[1] = -120.0f;
        __atomic_store_n(&hdr->magic, 0x564C564Bu, __ATOMIC_RELEASE);
        return true;
    }

    bool active() const { return hdr != nullptr; }

    void write_levels(const double *peak, const double *rms, int channels)
    {
        if (!hdr) return;
        __atomic_store_n(&hdr->seq, ++seq, __ATOMIC_RELEASE);
        for (int i = 0; i < 2; ++i) {
            hdr->peak[i] = static_cast<float>(peak[i]);
            hdr->rms[i] = static_cast<float>(rms[i]);
        }
        hdr->channels = static_cast<uint32_t>(channels);
        hdr->stamp_ms = mono_ms();
        __atomic_store_n(&hdr->seq, ++seq, __ATOMIC_RELEASE);
    }

    void destroy()
    {
        if (hdr) munmap(hdr, sizeof(LvHeader));
        if (fd >= 0) close(fd);
        if (!path.empty()) unlink(path.c_str());
        hdr = nullptr; fd = -1; path.clear();
    }
};

// appsink geri çağrısı: kareyi paylaşımlı belleğe kopyala
static GstFlowReturn on_preview_sample(GstAppSink *sink, gpointer user_data)
{
    auto *shm = static_cast<PvShm *>(user_data);
    GstSample *sample = gst_app_sink_pull_sample(sink);
    if (!sample) return GST_FLOW_OK;

    GstCaps *caps = gst_sample_get_caps(sample);
    GstBuffer *buffer = gst_sample_get_buffer(sample);
    GstVideoInfo info;
    if (shm && shm->active() && caps && buffer && gst_video_info_from_caps(&info, caps)) {
        GstVideoFrame frame;
        if (gst_video_frame_map(&frame, &info, buffer, GST_MAP_READ)) {
            shm->write_frame(GST_VIDEO_FRAME_WIDTH(&frame),
                             GST_VIDEO_FRAME_HEIGHT(&frame),
                             static_cast<const uint8_t *>(GST_VIDEO_FRAME_PLANE_DATA(&frame, 0)),
                             GST_VIDEO_FRAME_PLANE_STRIDE(&frame, 0));
            gst_video_frame_unmap(&frame);
        }
    }
    gst_sample_unref(sample);
    return GST_FLOW_OK;
}


// ============================================================
// Yalnızca ses kaydı: WAV segment yazıcı (s%d.wav)
// Segmentler örnek sayısına göre tam sınırda bölünür.
// ============================================================
struct WavWriter {
    std::string dir;
    int index = 1;
    int rate = 48000;
    int channels = 2;
    uint64_t seg_bytes = 0;
    uint64_t written = 0;
    FILE *file = nullptr;
    bool opened_any = false;

    static void put32(uint8_t *p, uint32_t v) { p[0] = v & 255; p[1] = (v >> 8) & 255; p[2] = (v >> 16) & 255; p[3] = (v >> 24) & 255; }
    static void put16(uint8_t *p, uint16_t v) { p[0] = v & 255; p[1] = (v >> 8) & 255; }

    bool open_next()
    {
        std::string path = dir + "/s" + std::to_string(index) + ".wav";
        file = std::fopen(path.c_str(), "wb");
        if (!file) {
            log_err("WAV dosyası açılamadı: " + path);
            return false;
        }
        uint8_t h[44] = {'R', 'I', 'F', 'F', 0, 0, 0, 0, 'W', 'A', 'V', 'E', 'f', 'm', 't', ' ',
                         16, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                         'd', 'a', 't', 'a', 0, 0, 0, 0};
        put16(h + 22, static_cast<uint16_t>(channels));
        put32(h + 24, static_cast<uint32_t>(rate));
        put32(h + 28, static_cast<uint32_t>(rate * channels * 2));
        put16(h + 32, static_cast<uint16_t>(channels * 2));
        put16(h + 34, 16);
        std::fwrite(h, 1, 44, file);
        written = 0;
        opened_any = true;
        emit_event("segment " + path);
        return true;
    }

    void close_current()
    {
        if (!file) return;
        uint8_t b[4];
        std::fseek(file, 4, SEEK_SET);
        put32(b, static_cast<uint32_t>(36 + written));
        std::fwrite(b, 1, 4, file);
        std::fseek(file, 40, SEEK_SET);
        put32(b, static_cast<uint32_t>(written));
        std::fwrite(b, 1, 4, file);
        std::fclose(file);
        file = nullptr;
        ++index;
    }

    void write(const uint8_t *data, size_t size)
    {
        const size_t frame = static_cast<size_t>(channels) * 2;
        while (size >= frame) {
            if (!file && !open_next()) return;
            uint64_t room = seg_bytes > written ? seg_bytes - written : 0;
            size_t chunk = static_cast<size_t>(std::min<uint64_t>(room, size));
            chunk -= chunk % frame;
            if (chunk == 0) { close_current(); continue; }
            std::fwrite(data, 1, chunk, file);
            written += chunk;
            data += chunk;
            size -= chunk;
            if (written >= seg_bytes) close_current();
        }
    }

    void finalize() { close_current(); }
};

static GstFlowReturn on_wav_sample(GstAppSink *sink, gpointer user_data)
{
    auto *wav = static_cast<WavWriter *>(user_data);
    GstSample *sample = gst_app_sink_pull_sample(sink);
    if (!sample) return GST_FLOW_OK;
    GstBuffer *buffer = gst_sample_get_buffer(sample);
    GstMapInfo map;
    if (buffer && gst_buffer_map(buffer, &map, GST_MAP_READ)) {
        wav->write(map.data, map.size);
        gst_buffer_unmap(buffer, &map);
    }
    gst_sample_unref(sample);
    return GST_FLOW_OK;
}

static void on_wav_eos(GstAppSink *, gpointer user_data)
{
    static_cast<WavWriter *>(user_data)->finalize();
}


// ============================================================
// BİRLEŞİK MOTOR: ekran (X11/Wayland) + kamera + ses  ->  kayıt + önizleme
//
// Tek bir GStreamer pipeline içinde bağımsız zincirler çalışır; böylece tüm
// kaynaklar aynı saati paylaşır (ekran/kamera/ses senkron kalır).
//
//   Ekran   -> s%d.mkv   (ses varsa aynı dosyanın içinde AAC olarak)
//   Kamera  -> c%d.mkv   (ekran yoksa ses bu dosyaya girer)
//   Yalnız ses -> s%d.wav
//
// Her zincirin önizleme dalı: leaky queue -> valve -> küçük BGRx -> appsink
// ============================================================
struct Config {
    bool record = false;
    std::string dir;
    int start = 1;
    int seg = 60;
    int fps = 12;
    int w = 854;
    int h = 480;

    std::string screen = "none";   // none | x11 | wayland
    int rx = 0, ry = 0, rw = 0, rh = 0;

    std::string audio = "none";    // none | default | <pulse kaynak adı>
    int rate = 48000;

    std::string camera = "none";   // none | auto | /dev/videoN
    int cw = 640, ch = 480;

    std::string pv_screen, pv_camera, pv_audio;
    int pv_w = 512;
    int pv_cw = 384;
    int pv_fps = 8;
    int pv_cfps = 15;

    std::string token_file;
};

struct VEnc { std::string launch; std::string parse; };
struct AEnc { std::string launch; std::string parse; };

static VEnc pick_video_encoder(int fps, int w, int h)
{
    VEnc e;
    const int threads = (static_cast<long>(w) * h > 1280L * 720L) ? 2 : 1;
    if (have_factory("x264enc")) {
        // ffmpeg: -preset ultrafast -crf 25 -g fps  ile eşdeğer (düşük işlemci yükü)
        e.launch = "x264enc speed-preset=ultrafast tune=zerolatency pass=qual quantizer=25 bframes=0 key-int-max=" +
                   std::to_string(std::max(1, fps)) + " threads=" + std::to_string(threads);
        e.parse = "h264parse";
    } else if (have_factory("openh264enc")) {
        e.launch = "openh264enc bitrate=2500000 gop-size=" + std::to_string(std::max(1, fps));
        e.parse = "h264parse";
    } else if (have_factory("vp8enc")) {
        e.launch = "vp8enc deadline=1 cpu-used=8 end-usage=cq cq-level=30 threads=" + std::to_string(threads) +
                   " keyframe-max-dist=" + std::to_string(std::max(1, fps));
        e.parse = "";
    }
    return e;
}

static AEnc pick_audio_encoder()
{
    AEnc e;
    if (have_factory("fdkaacenc"))      { e.launch = "fdkaacenc bitrate=128000"; e.parse = "aacparse"; }
    else if (have_factory("voaacenc"))  { e.launch = "voaacenc bitrate=128000";  e.parse = "aacparse"; }
    else if (have_factory("avenc_aac")) { e.launch = "avenc_aac bitrate=128000"; e.parse = "aacparse"; }
    else {
        // Hiçbir AAC kodlayıcı yoksa ham PCM'i MKV içine koy (dışa aktarmada AAC'ye çevrilir)
        e.launch = "audioconvert ! audio/x-raw,format=S16LE";
        e.parse = "";
    }
    return e;
}

static const char *pw_node_prop()
{
    return factory_has_prop("pipewiresrc", "target-object") ? "target-object" : "path";
}

static std::string preview_branch(const std::string &tag, int pw, int pfps)
{
    std::ostringstream s;
    s << "queue name=pvq_" << tag << " max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream"
      << " ! valve name=pvv_" << tag
      << " ! videorate drop-only=true"
      << " ! video/x-raw,framerate=" << std::max(1, pfps) << "/1"
      << " ! videoscale"
      << " ! video/x-raw,width=" << std::max(16, pw) << ",pixel-aspect-ratio=1/1"
      << " ! videoconvert"
      << " ! video/x-raw,format=BGRx"
      << " ! appsink name=pv_" << tag << " max-buffers=1 drop=true sync=false async=false";
    return s.str();
}

static std::string video_record_queue(const std::string &name)
{
    // Kodlayıcı yetişemezse bellek şişmesin: 2 sn / 64 MB dolunca eski kareleri at
    return "queue name=" + name +
           " max-size-buffers=0 max-size-bytes=67108864 max-size-time=2000000000 leaky=downstream";
}

struct Engine {
    Config cfg;
    PortalSession portal;
    GstElement *pipeline = nullptr;
    GMainLoop *loop = nullptr;
    guint bus_watch = 0;
    guint tick_id = 0;
    GIOChannel *stdin_channel = nullptr;
    guint stdin_watch = 0;
    PvShm pv_screen, pv_camera;
    LvShm pv_level;
    WavWriter wav;
    std::vector<GstElement *> valves;
    VEnc venc;
    AEnc aenc;
    std::string camera_path;
    int cam_w = 0, cam_h = 0;
    pid_t parent_pid = 0;

    bool eos_sent = false;
    bool paused = false;
    bool failed = false;
    gint64 eos_deadline = 0;
    gint64 attempt_start = 0;
    std::string err_tag;
    std::string err_msg;
    int attempt = 0;

    bool has_scr() const { return cfg.screen != "none"; }
    bool has_cam() const { return cfg.camera != "none"; }
    bool has_aud() const { return cfg.audio != "none"; }

    // ---------------- Ön kontroller ----------------
    bool check_plugins()
    {
        std::vector<std::string> missing;
        auto need = [&](const char *factory, const char *pkg) {
            if (!have_factory(factory)) missing.push_back(std::string(factory) + " (sudo apt install " + pkg + ")");
        };

        need("queue", "gstreamer1.0-plugins-base");
        need("valve", "gstreamer1.0-plugins-base");
        need("videoconvert", "gstreamer1.0-plugins-base");
        need("videoscale", "gstreamer1.0-plugins-base");
        need("videorate", "gstreamer1.0-plugins-base");
        need("appsink", "gstreamer1.0-plugins-base");
        need("audioconvert", "gstreamer1.0-plugins-base");
        need("audioresample", "gstreamer1.0-plugins-base");
        need("level", "gstreamer1.0-plugins-good");

        if (g_fake_sources) {
            need("videotestsrc", "gstreamer1.0-plugins-base");
            need("audiotestsrc", "gstreamer1.0-plugins-base");
        } else {
            if (cfg.screen == "x11") need("ximagesrc", "gstreamer1.0-plugins-good");
            if (cfg.screen == "wayland") need("pipewiresrc", "gstreamer1.0-pipewire");
            if (has_cam()) need("v4l2src", "gstreamer1.0-plugins-good");
            if (has_aud()) need("pulsesrc", "gstreamer1.0-plugins-good");
        }
        if (has_cam()) need("decodebin", "gstreamer1.0-plugins-base");

        const bool video_rec = cfg.record && has_scr();
        if (video_rec) {
            need("matroskamux", "gstreamer1.0-plugins-good");
            if (venc.launch.empty()) {
                missing.push_back("x264enc (sudo apt install gstreamer1.0-plugins-ugly)");
            } else if (!venc.parse.empty()) {
                need("h264parse", "gstreamer1.0-plugins-bad");
            }
            if (has_aud() && !aenc.parse.empty()) need("aacparse", "gstreamer1.0-plugins-bad");
        }

        if (missing.empty()) return true;
        std::string msg = "Eksik GStreamer eklentisi: ";
        for (size_t i = 0; i < missing.size(); ++i) msg += (i ? ", " : "") + missing[i];
        log_err(msg);
        return false;
    }

    // ---------------- Pipeline tanımı ----------------
    std::string audio_head(bool wav_caps) const
    {
        std::ostringstream s;
        if (g_fake_sources) s << "audiotestsrc name=aud_src is-live=true wave=sine freq=440 volume=0.2";
        else s << "pulsesrc name=aud_src";
        s << " ! audioconvert ! audioresample ! audio/x-raw,rate=" << cfg.rate << ",channels=2";
        if (wav_caps) s << ",format=S16LE,layout=interleaved";
        s << " ! level name=aud_level interval=100000000 post-messages=true";
        return s.str();
    }

    std::string screen_head(int rate, bool cfr) const
    {
        std::ostringstream s;
        if (g_fake_sources) {
            s << "videotestsrc name=scr_src is-live=true pattern=smpte ! video/x-raw,framerate=" << rate << "/1";
        } else if (cfg.screen == "x11") {
            s << "ximagesrc name=scr_src use-damage=false show-pointer=true";
            if (cfg.rw > 0 && cfg.rh > 0) {
                s << " startx=" << cfg.rx << " starty=" << cfg.ry
                  << " endx=" << (cfg.rx + cfg.rw - 1) << " endy=" << (cfg.ry + cfg.rh - 1);
            }
            s << " ! video/x-raw,framerate=" << rate << "/1";
        } else {
            s << "pipewiresrc name=scr_src " << pw_node_prop() << "=" << portal.node_id
              << " do-timestamp=true always-copy=true";
            if (factory_has_prop("pipewiresrc", "keepalive-time")) {
                s << " keepalive-time=" << std::max(20, 1000 / std::max(1, rate));
            }
            s << " ! videorate" << (cfr ? "" : " drop-only=true")
              << " ! video/x-raw,framerate=" << rate << "/1";
        }
        return s.str();
    }

    std::string camera_head(int try_no, int rate) const
    {
        std::ostringstream s;
        if (g_fake_sources) s << "videotestsrc name=cam_src is-live=true pattern=ball";
        else s << "v4l2src name=cam_src";

        std::string size;
        if (cam_w > 0 && cam_h > 0) {
            size = ",width=" + std::to_string(cam_w) + ",height=" + std::to_string(cam_h);
        }
        std::string caps;
        if (try_no == 0) {
            // Hedef hıza yakın bir kamera modu iste: gereksiz MJPEG çözme yükünü azaltır
            std::string fr = ",framerate=[ " + std::to_string(rate) + "/1, " + std::to_string(rate * 2) + "/1 ]";
            caps = "video/x-raw" + size + fr + "; image/jpeg" + size + fr;
        } else if (try_no == 1) {
            caps = "video/x-raw" + size + "; image/jpeg" + size;
        } else {
            caps = "video/x-raw; image/jpeg";
        }
        s << " ! capsfilter caps=\"" << caps << "\""
          << " ! decodebin name=cam_dec"
          << " ! videorate ! video/x-raw,framerate=" << rate << "/1"
          << " ! videoconvert ! video/x-raw,format=I420";
        return s.str();
    }

    std::string build_pipeline(int try_no) const
    {
        std::ostringstream p;
        const bool rec = cfg.record;
        const bool aud_in_scr = rec && has_aud() && has_scr();
        const bool aud_wav = rec && has_aud() && !has_scr();

        // ---- Ekran ----  (kayıt: tek MKV dosyası; ses varsa aynı dosyaya girer)
        if (has_scr()) {
            const int rate = rec ? cfg.fps : cfg.pv_fps;
            const int pfps = rec ? std::min(cfg.pv_fps, cfg.fps) : cfg.pv_fps;
            const bool want_pv = !cfg.pv_screen.empty();

            if (rec) {
                p << screen_head(rate, true)
                  << " ! videoscale add-borders=true"
                  << " ! video/x-raw,width=" << cfg.w << ",height=" << cfg.h << ",pixel-aspect-ratio=1/1"
                  << " ! tee name=scr_tee ";
                p << "scr_tee. ! " << video_record_queue("scr_rq")
                  << " ! videoconvert ! video/x-raw,format=I420 ! " << venc.launch;
                if (!venc.parse.empty()) p << " ! " << venc.parse;
                p << " ! screen_mux.video_0 ";
                if (want_pv) p << "scr_tee. ! " << preview_branch("scr", cfg.pv_w, pfps) << " ";
                p << "matroskamux name=screen_mux ! filesink name=screen_file async=false ";
            } else if (want_pv) {
                p << screen_head(rate, false) << " ! " << preview_branch("scr", cfg.pv_w, pfps) << " ";
            }
        }

        // ---- Kamera ----  (her zaman yalnızca önizleme; kayıt ekran kaydı içindeki yüzen pencereyle olur)
        if (has_cam()) {
            const int rate = cfg.pv_cfps;
            if (!cfg.pv_camera.empty()) {
                p << camera_head(try_no, rate) << " ! " << preview_branch("cam", cfg.pv_cw, rate) << " ";
            } else {
                p << camera_head(try_no, rate) << " ! fakesink sync=false async=false ";
            }
        }

        // ---- Ses ----
        if (has_aud()) {
            if (aud_in_scr) {
                p << audio_head(false)
                  << " ! queue name=aud_q max-size-buffers=0 max-size-bytes=0 max-size-time=3000000000"
                  << " ! " << aenc.launch;
                if (!aenc.parse.empty()) p << " ! " << aenc.parse;
                p << " ! screen_mux.audio_0 ";
            } else if (aud_wav) {
                p << audio_head(true) << " ! appsink name=wav_sink max-buffers=400 drop=false sync=false async=false ";
            } else {
                p << audio_head(false) << " ! fakesink name=aud_fake sync=false async=false ";
            }
        }
        return p.str();
    }

    // ---------------- Pipeline kurulum ----------------
    GstElement *get(const char *name)
    {
        return pipeline ? gst_bin_get_by_name(GST_BIN(pipeline), name) : nullptr;
    }

    void setup_output()
    {
        GstElement *file = get("screen_file");
        if (!file) return;
        const std::string path = cfg.dir + "/s" + std::to_string(cfg.start) + ".mkv";
        g_object_set(file, "location", path.c_str(), nullptr);
        emit_event("file " + path);
        gst_object_unref(file);
    }

    void setup_preview_sink(const char *name, PvShm *shm)
    {
        GstElement *sink = get(name);
        if (!sink) return;
        GstAppSinkCallbacks cb;
        std::memset(&cb, 0, sizeof(cb));
        cb.new_sample = on_preview_sample;
        gst_app_sink_set_callbacks(GST_APP_SINK(sink), &cb, shm, nullptr);
        gst_object_unref(sink);
    }

    void collect_valve(const char *name)
    {
        GstElement *v = get(name);
        if (v) valves.push_back(v);   // referans burada tutulur, teardown'da bırakılır
    }

    // Python'dan satır komutları: PAUSE / RESUME (kayıt tek dosyada kalır, zaman damgaları kesintisiz sürer)
    void handle_command(const std::string &cmd)
    {
        if (!pipeline || !cfg.record) return;
        if (cmd == "PAUSE" && !paused) {
            gst_element_set_state(pipeline, GST_STATE_PAUSED);
            paused = true;
            emit_event("paused");
        } else if (cmd == "RESUME" && paused) {
            paused = false;
            gst_element_set_state(pipeline, GST_STATE_PLAYING);
            emit_event("resumed");
        }
    }

    static gboolean on_stdin(GIOChannel *src, GIOCondition cond, gpointer user_data)
    {
        auto *e = static_cast<Engine *>(user_data);
        if (cond & (G_IO_HUP | G_IO_ERR)) return G_SOURCE_REMOVE;
        gchar *line = nullptr;
        gsize len = 0;
        GIOStatus st = g_io_channel_read_line(src, &line, &len, nullptr, nullptr);
        if (st == G_IO_STATUS_NORMAL && line) {
            std::string cmd = line;
            while (!cmd.empty() && (cmd.back() == '\n' || cmd.back() == '\r' || cmd.back() == ' ')) cmd.pop_back();
            g_free(line);
            e->handle_command(cmd);
        } else if (st == G_IO_STATUS_EOF) {
            return G_SOURCE_REMOVE;
        }
        return G_SOURCE_CONTINUE;
    }

    void set_preview_enabled(bool on)
    {
        for (GstElement *v : valves) g_object_set(v, "drop", on ? FALSE : TRUE, nullptr);
        log_info(std::string("Önizleme ") + (on ? "açıldı" : "kapatıldı"));
    }

    void configure()
    {
        if (GstElement *src = get("aud_src")) {
            if (!g_fake_sources && cfg.audio != "default" && cfg.audio != "none") {
                g_object_set(src, "device", cfg.audio.c_str(), nullptr);
            }
            gst_object_unref(src);
        }
        if (GstElement *src = get("cam_src")) {
            if (!g_fake_sources) g_object_set(src, "device", camera_path.c_str(), nullptr);
            gst_object_unref(src);
        }

        if (cfg.record) setup_output();

        setup_preview_sink("pv_scr", &pv_screen);
        setup_preview_sink("pv_cam", &pv_camera);
        collect_valve("pvv_scr");
        collect_valve("pvv_cam");

        if (GstElement *wsink = get("wav_sink")) {
            GstAppSinkCallbacks cb;
            std::memset(&cb, 0, sizeof(cb));
            cb.new_sample = on_wav_sample;
            cb.eos = on_wav_eos;
            gst_app_sink_set_callbacks(GST_APP_SINK(wsink), &cb, &wav, nullptr);
            gst_object_unref(wsink);
        }
    }

    // ---------------- Bus ----------------
    static std::string chain_tag(GstObject *obj)
    {
        GstObject *cur = obj ? static_cast<GstObject *>(gst_object_ref(obj)) : nullptr;
        std::string tag;
        while (cur) {
            const gchar *n = GST_OBJECT_NAME(cur);
            if (n) {
                std::string name = n;
                if (name.rfind("cam_", 0) == 0 || name.rfind("pv_cam", 0) == 0 || name.rfind("pvq_cam", 0) == 0) { tag = "cam"; }
                else if (name.rfind("aud_", 0) == 0) { tag = "aud"; }
                else if (name.rfind("scr_", 0) == 0 || name.rfind("screen_", 0) == 0) { tag = "scr"; }
                if (!tag.empty()) { gst_object_unref(cur); break; }
            }
            GstObject *parent = gst_object_get_parent(cur);
            gst_object_unref(cur);
            cur = parent;
        }
        return tag;
    }

    void handle_level(const GstStructure *s)
    {
        if (!pv_level.active()) return;
        double peak[2] = {-120.0, -120.0};
        double rms[2] = {-120.0, -120.0};
        int channels = 0;

        auto read = [&](const char *field, double *out) {
            const GValue *v = gst_structure_get_value(s, field);
            if (!v) return;
            if (GST_VALUE_HOLDS_ARRAY(v)) {
                guint n = gst_value_array_get_size(v);
                for (guint i = 0; i < n && i < 2; ++i) {
                    out[i] = g_value_get_double(gst_value_array_get_value(v, i));
                    channels = std::max<int>(channels, static_cast<int>(i) + 1);
                }
            } else if (G_VALUE_HOLDS_BOXED(v)) {
                G_GNUC_BEGIN_IGNORE_DEPRECATIONS
                auto *arr = static_cast<GValueArray *>(g_value_get_boxed(v));
                if (arr) {
                    for (guint i = 0; i < arr->n_values && i < 2; ++i) {
                        out[i] = g_value_get_double(g_value_array_get_nth(arr, i));
                        channels = std::max<int>(channels, static_cast<int>(i) + 1);
                    }
                }
                G_GNUC_END_IGNORE_DEPRECATIONS
            }
        };
        read("peak", peak);
        read("rms", rms);
        if (channels == 1) { peak[1] = peak[0]; rms[1] = rms[0]; }
        pv_level.write_levels(peak, rms, std::max(1, channels));
    }

    static gboolean on_bus_message(GstBus *, GstMessage *message, gpointer user_data)
    {
        auto *e = static_cast<Engine *>(user_data);
        if (!message) return G_SOURCE_CONTINUE;

        switch (GST_MESSAGE_TYPE(message)) {
            case GST_MESSAGE_ERROR: {
                GError *error = nullptr;
                gchar *debug = nullptr;
                gst_message_parse_error(message, &error, &debug);

                e->failed = true;
                e->err_tag = chain_tag(GST_MESSAGE_SRC(message));
                e->err_msg = error && error->message ? error->message : "bilinmeyen GStreamer hatası";

                std::cerr << "C++ GStreamer Hata: " << e->err_msg << std::endl;
                if (debug && *debug) std::cerr << "C++ GStreamer Debug: " << debug << std::endl;
                if (error) g_error_free(error);
                g_free(debug);

                if (e->loop) g_main_loop_quit(e->loop);
                break;
            }
            case GST_MESSAGE_WARNING: {
                GError *error = nullptr;
                gchar *debug = nullptr;
                gst_message_parse_warning(message, &error, &debug);
                std::cerr << "C++ GStreamer Uyarı: " << (error && error->message ? error->message : "?") << std::endl;
                if (error) g_error_free(error);
                g_free(debug);
                break;
            }
            case GST_MESSAGE_EOS:
                if (e->loop) g_main_loop_quit(e->loop);
                break;
            case GST_MESSAGE_STATE_CHANGED: {
                if (GST_MESSAGE_SRC(message) == GST_OBJECT(e->pipeline)) {
                    GstState oldst, newst;
                    gst_message_parse_state_changed(message, &oldst, &newst, nullptr);
                    if (newst == GST_STATE_PLAYING && oldst != GST_STATE_PLAYING) emit_event("ready");
                }
                break;
            }
            case GST_MESSAGE_ELEMENT: {
                const GstStructure *s = gst_message_get_structure(message);
                if (s && gst_structure_has_name(s, "level")) e->handle_level(s);
                break;
            }
            default:
                break;
        }
        return G_SOURCE_CONTINUE;
    }

    static gboolean on_tick(gpointer user_data)
    {
        auto *e = static_cast<Engine *>(user_data);

        // Python süreci ölürse (çökme) kaydı düzgün kapat
        if (getppid() != e->parent_pid) g_stop_requested = 1;

        if (g_preview_cmd) {
            int cmd = g_preview_cmd;
            g_preview_cmd = 0;
            e->set_preview_enabled(cmd == 1);
        }

        if (g_stop_requested && !e->eos_sent) {
            e->eos_sent = true;
            if (e->cfg.record && e->pipeline) {
                if (e->paused) {
                    e->paused = false;
                    gst_element_set_state(e->pipeline, GST_STATE_PLAYING);
                }
                log_info("EOS gönderiliyor...");
                gst_element_send_event(e->pipeline, gst_event_new_eos());
                e->eos_deadline = g_get_monotonic_time() + 8 * G_USEC_PER_SEC;
            } else if (e->loop) {
                g_main_loop_quit(e->loop);
            }
        }
        if (e->eos_sent && e->cfg.record && e->loop &&
            g_get_monotonic_time() > e->eos_deadline) {
            log_err("EOS zaman aşımı, zorla kapatılıyor.");
            g_main_loop_quit(e->loop);
        }
        return G_SOURCE_CONTINUE;
    }

    bool start_pipeline(int try_no)
    {
        const std::string desc = build_pipeline(try_no);
        log_info("pipeline: " + desc);

        GError *error = nullptr;
        pipeline = gst_parse_launch(desc.c_str(), &error);
        if (error) {
            log_err(std::string("GStreamer pipeline parse hatası: ") + error->message);
            g_error_free(error);
            if (pipeline) { gst_object_unref(pipeline); pipeline = nullptr; }
            return false;
        }
        if (!pipeline) {
            log_err("GStreamer pipeline oluşturulamadı.");
            return false;
        }

        configure();

        GstBus *bus = gst_element_get_bus(pipeline);
        bus_watch = gst_bus_add_watch(bus, on_bus_message, this);
        gst_object_unref(bus);

        failed = false;
        err_tag.clear();
        err_msg.clear();
        attempt_start = g_get_monotonic_time();

        GstStateChangeReturn ret = gst_element_set_state(pipeline, GST_STATE_PLAYING);
        if (ret == GST_STATE_CHANGE_FAILURE) {
            // Hata ayrıntısı bus'ta bekliyor olabilir
            GstBus *b = gst_element_get_bus(pipeline);
            GstMessage *m = gst_bus_pop_filtered(b, GST_MESSAGE_ERROR);
            if (m) {
                GError *er = nullptr;
                gchar *dbg = nullptr;
                gst_message_parse_error(m, &er, &dbg);
                err_msg = er && er->message ? er->message : "";
                err_tag = chain_tag(GST_MESSAGE_SRC(m));
                std::cerr << "C++ GStreamer Hata: " << err_msg << std::endl;
                if (er) g_error_free(er);
                g_free(dbg);
                gst_message_unref(m);
            }
            gst_object_unref(b);
            log_err("GStreamer PLAYING durumuna geçemedi.");
            return false;
        }

        GstState cur = GST_STATE_NULL, pend = GST_STATE_NULL;
        ret = gst_element_get_state(pipeline, &cur, &pend, 10 * GST_SECOND);
        if (ret == GST_STATE_CHANGE_FAILURE) {
            log_err("GStreamer pipeline başlatılamadı.");
            return false;
        }
        return true;
    }

    void teardown_pipeline()
    {
        if (bus_watch) { g_source_remove(bus_watch); bus_watch = 0; }
        if (pipeline) {
            gst_element_set_state(pipeline, GST_STATE_NULL);
            gst_object_unref(pipeline);
            pipeline = nullptr;
        }
        for (GstElement *v : valves) gst_object_unref(v);
        valves.clear();
        wav.finalize();
    }

    void shutdown()
    {
        teardown_pipeline();
        if (tick_id) { g_source_remove(tick_id); tick_id = 0; }
        if (stdin_watch) { g_source_remove(stdin_watch); stdin_watch = 0; }
        if (stdin_channel) { g_io_channel_unref(stdin_channel); stdin_channel = nullptr; }
        if (loop) { g_main_loop_unref(loop); loop = nullptr; }
        pv_screen.destroy();
        pv_camera.destroy();
        pv_level.destroy();
        if (portal.bus) {
            close_wayland_session(portal.bus, portal.handle);
            g_object_unref(portal.bus);
            portal.bus = nullptr;
        }
    }

    // Best-effort: hata sonrası açık dosyaları bitirmek için EOS dene
    void try_finalize_after_error()
    {
        if (!pipeline || !cfg.record) return;
        gst_element_send_event(pipeline, gst_event_new_eos());
        GstBus *b = gst_element_get_bus(pipeline);
        GstMessage *m = gst_bus_timed_pop_filtered(
            b, 3 * GST_SECOND, static_cast<GstMessageType>(GST_MESSAGE_EOS | GST_MESSAGE_ERROR));
        if (m) gst_message_unref(m);
        gst_object_unref(b);
    }

    // ---------------- Çalıştır ----------------
    int run()
    {
        parent_pid = getppid();

        if (!has_scr() && !has_cam() && !has_aud()) {
            log_err("Kaynak seçilmedi (ekran, kamera veya ses gerekli).");
            return 1;
        }
        if (cfg.screen != "none" && cfg.screen != "x11" && cfg.screen != "wayland") {
            log_err("Geçersiz screen değeri: " + cfg.screen);
            return 1;
        }
        if (cfg.record) {
            if (!dir_is_safe(cfg.dir)) {
                log_err("Geçersiz çıkış klasörü.");
                return 1;
            }
            std::error_code ec;
            std::filesystem::create_directories(cfg.dir, ec);
            if (ec) {
                log_err("Çıkış klasörü oluşturulamadı: " + ec.message());
                return 1;
            }
            if (cfg.start < 1 || cfg.fps < 1 || cfg.w < 2 || cfg.h < 2) {
                log_err("Geçersiz kayıt parametreleri.");
                return 1;
            }
        } else if (cfg.pv_screen.empty() && cfg.pv_camera.empty() && cfg.pv_audio.empty()) {
            log_err("Önizleme için paylaşımlı bellek yolu verilmedi.");
            return 1;
        }

        if (cfg.record && has_cam()) {
            log_info("Not: kamera ayrı kaydedilmez; yalnızca önizlenir (ekran kaydına yüzen pencereyle girer).");
        }
        cfg.w &= ~1;
        cfg.h &= ~1;
        cfg.rate = std::max(8000, cfg.rate);

        gst_init(nullptr, nullptr);
        g_fake_sources = g_getenv("KAVRAM_FAKE_SOURCES") != nullptr;

        venc = pick_video_encoder(cfg.fps, cfg.w, cfg.h);
        aenc = pick_audio_encoder();
        if (!check_plugins()) {
            emit_event("error 5 eksik-eklenti");
            return 5;
        }

        std::signal(SIGINT, on_stop_signal);
        std::signal(SIGTERM, on_stop_signal);
        std::signal(SIGHUP, on_stop_signal);
        std::signal(SIGUSR1, on_usr1_signal);
        std::signal(SIGUSR2, on_usr2_signal);
        std::signal(SIGPIPE, SIG_IGN);

        // Kamera yolu
        if (has_cam()) {
            camera_path = cfg.camera;
            if (!g_fake_sources) {
                if (camera_path == "auto") {
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
            cam_w = cfg.cw;
            cam_h = cfg.ch;
            log_info("Kamera: " + camera_path);
        }

        // Wayland portal izni
        if (cfg.screen == "wayland" && !g_fake_sources) {
            int pcode = 1;
            if (!open_wayland_portal(portal, cfg.token_file, pcode)) {
                emit_event("error " + std::to_string(pcode) + " ekran-portal");
                shutdown();
                return pcode;
            }
        }

        // Önizleme belleği
        if (has_scr() && !cfg.pv_screen.empty()) {
            if (!pv_screen.create(cfg.pv_screen, static_cast<size_t>(cfg.pv_w) * cfg.pv_w * 2 * 4)) cfg.pv_screen.clear();
        }
        if (has_cam() && !cfg.pv_camera.empty()) {
            if (!pv_camera.create(cfg.pv_camera, static_cast<size_t>(cfg.pv_cw) * cfg.pv_cw * 2 * 4)) cfg.pv_camera.clear();
        }
        if (has_aud() && !cfg.pv_audio.empty()) {
            if (!pv_level.create(cfg.pv_audio)) cfg.pv_audio.clear();
        }

        if (cfg.record && has_aud() && !has_scr() && !has_cam()) {
            wav.dir = cfg.dir;
            wav.index = cfg.start;
            wav.rate = cfg.rate;
            wav.channels = 2;
            wav.seg_bytes = 3500ull * 1024ull * 1024ull;   // WAV başlığı 4 GB ile sınırlı: süre sınırı yok, çok uzunsa yeni dosya
        }

        loop = g_main_loop_new(nullptr, FALSE);
        tick_id = g_timeout_add(50, on_tick, this);
        if (cfg.record) {
            stdin_channel = g_io_channel_unix_new(0);
            g_io_channel_set_encoding(stdin_channel, nullptr, nullptr);
            g_io_channel_set_flags(stdin_channel, G_IO_FLAG_NONBLOCK, nullptr);
            stdin_watch = g_io_add_watch(stdin_channel, static_cast<GIOCondition>(G_IO_IN | G_IO_HUP | G_IO_ERR),
                                         on_stdin, this);
        }

        const int max_try = has_cam() ? 2 : 0;
        int result = 0;

        for (attempt = 0; attempt <= max_try; ++attempt) {
            if (g_stop_requested) break;

            bool started = start_pipeline(attempt);
            if (!started) {
                const bool cam_problem = has_cam() && (err_tag.empty() || err_tag == "cam");
                teardown_pipeline();
                if (cam_problem && attempt < max_try) {
                    log_info("Kamera modu uygun değil, farklı mod deneniyor...");
                    continue;
                }
                result = (err_tag == "cam" || (has_cam() && err_tag.empty())) ? 2 : 1;
                break;
            }

            g_main_loop_run(loop);

            const gint64 age = g_get_monotonic_time() - attempt_start;
            if (failed) {
                const bool early_cam = (err_tag == "cam") && age < 8 * G_USEC_PER_SEC &&
                                       attempt < max_try && !g_stop_requested;
                if (early_cam) {
                    log_info("Kamera başlangıç hatası, farklı mod deneniyor...");
                    teardown_pipeline();
                    continue;
                }
                if (age >= 8 * G_USEC_PER_SEC) try_finalize_after_error();
                result = err_tag == "cam" ? 2 : (err_tag == "aud" ? 4 : 1);
                emit_event("error " + std::to_string(result) + " " + (err_tag.empty() ? "genel" : err_tag));
            }
            break;
        }

        teardown_pipeline();
        shutdown();
        if (result == 0) log_info("kayıt/önizleme güvenli şekilde kapatıldı.");
        return result;
    }
};

static int run_engine(const Config &cfg)
{
    Engine engine;
    engine.cfg = cfg;
    return engine.run();
}

static Config config_from_kv(const KV &kv, bool record)
{
    Config c;
    c.record = record;
    c.dir = kv_str(kv, "dir");
    c.start = kv_int(kv, "start", 1);
    c.seg = kv_int(kv, "seg", 60);
    c.fps = kv_int(kv, "fps", 12);
    c.w = kv_int(kv, "w", 854);
    c.h = kv_int(kv, "h", 480);
    c.screen = kv_str(kv, "screen", "none");
    if (c.screen == "auto") {
        const char *wl = g_getenv("WAYLAND_DISPLAY");
        const char *st = g_getenv("XDG_SESSION_TYPE");
        c.screen = (wl && *wl) || (st && std::string(st) == "wayland") ? "wayland" : "x11";
    }
    c.rx = kv_int(kv, "rx", 0);
    c.ry = kv_int(kv, "ry", 0);
    c.rw = kv_int(kv, "rw", 0);
    c.rh = kv_int(kv, "rh", 0);
    c.audio = kv_str(kv, "audio", "none");
    c.rate = kv_int(kv, "rate", 48000);
    c.camera = kv_str(kv, "camera", "none");
    c.cw = kv_int(kv, "cw", 640);
    c.ch = kv_int(kv, "ch", 480);
    c.pv_screen = kv_str(kv, "pv_screen");
    c.pv_camera = kv_str(kv, "pv_camera");
    c.pv_audio = kv_str(kv, "pv_audio");
    c.pv_w = std::max(64, kv_int(kv, "pv_w", 512));
    c.pv_cw = std::max(64, kv_int(kv, "pv_cw", 384));
    c.pv_fps = std::max(1, kv_int(kv, "pv_fps", 8));
    c.pv_cfps = std::max(1, kv_int(kv, "pv_cfps", 15));
    c.token_file = kv_str(kv, "token");
    return c;
}


// Function to merge video and/or audio segments
// This function will be called by Python during the export process.
// It takes paths to text files listing the segments and the final output file.
int mergeRecordings(const std::string& ffmpeg_path, const std::string& video_list_file, const std::string& audio_list_file, const std::string& output_file) {
    std::cout << "C++: Kayıtlar birleştiriliyor... (" << video_list_file << ", " << audio_list_file << " -> " << output_file << ")" << std::endl;
    fflush(stdout);

    // Check if the list files actually exist and have content
    std::error_code video_ec;
    std::error_code audio_ec;
    const bool has_video =
        !video_list_file.empty() &&
        std::filesystem::exists(video_list_file, video_ec) &&
        !video_ec &&
        std::filesystem::file_size(video_list_file, video_ec) > 0 &&
        !video_ec;

    const bool has_audio =
        !audio_list_file.empty() &&
        std::filesystem::exists(audio_list_file, audio_ec) &&
        !audio_ec &&
        std::filesystem::file_size(audio_list_file, audio_ec) > 0 &&
        !audio_ec;

    if (!has_video && !has_audio) {
        std::cerr << "C++ Hata: Birleştirme için video veya ses segment listesi sağlanmadı." << std::endl;
        fflush(stderr);
        return 1;
    }

    // Executable'ı tırnak içine alarak boşluk içeren yollara karşı koruma
    std::string ffmpeg_command = "\"" + ffmpeg_path + "\" -y ";

    // Add concat demuxer inputs
    if (has_video) {
        ffmpeg_command += "-f concat -safe 0 -i \"" + video_list_file + "\" ";
    }
    if (has_audio) {
        ffmpeg_command += "-f concat -safe 0 -i \"" + audio_list_file + "\" ";
    }

    // Mapping streams and codecs with improved synchronization
    if (has_video && has_audio) {
        ffmpeg_command += "-map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -fps_mode cfr ";
    } else if (has_video) {
        ffmpeg_command += "-map 0:v:0 -c:v copy ";
    } else { // Only audio
        ffmpeg_command += "-map 0:a:0 -c:a copy ";
    }

    ffmpeg_command += "\"" + output_file + "\"";

    std::cout << "C++: FFmpeg birleştirme komutu: " << ffmpeg_command << std::endl;
    fflush(stdout);

    int result = std::system(ffmpeg_command.c_str());

    if (result != 0) {
        std::cerr << "C++ Hata: FFmpeg birleştirme işlemi " << result << " çıkış koduyla başarısız oldu." << std::endl;
        fflush(stderr);
        return 1;
    }

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
        std::cerr << "C++ Hata: Komut argümanı eksik. Kullanım: camera_recorder [komut] [argümanlar...]" << std::endl;
        fflush(stderr);
        return 1;
    }

    // FFmpeg yalnızca --merge-recordings için gereklidir.
    std::filesystem::path exe_path(argv[0]);
    std::filesystem::path exe_dir = exe_path.parent_path();
    std::string ffmpeg_path = (exe_dir / "bin" / "ffmpeg").string();

    std::string command = argv[1];

    // ---- Yeni: birleşik motor (kayıt + önizleme) ----
    if (command == "--record") {
        return run_engine(config_from_kv(parse_kv(argc, argv, 2), true));
    }

    if (command == "--preview") {
        return run_engine(config_from_kv(parse_kv(argc, argv, 2), false));
    }

    if (command == "--list-cameras") {
        return cmd_list_cameras();
    }

    if (command == "--capabilities") {
        return cmd_capabilities();
    }

    // ---- Eski arayüz (korunur): Wayland ekran kaydı ----
    if (command == "--record-wayland") {

        if (argc != 8) {
            std::cerr
                << "C++ Hata: --record-wayland kullanımı: "
                << "--record-wayland <output_dir> <start_number> "
                << "<segment_time> <fps> <width> <height>"
                << std::endl;
            return 1;
        }

        std::string output_dir = argv[2];
        int start_number = 0;
        int segment_time = 0;
        int fps = 0;
        int width = 0;
        int height = 0;

        try {
            start_number = std::stoi(argv[3]);
            segment_time = std::stoi(argv[4]);
            fps = std::stoi(argv[5]);
            width = std::stoi(argv[6]);
            height = std::stoi(argv[7]);
        } catch (const std::exception& e) {
            std::cerr
                << "C++ Hata: --record-wayland sayısal parametreleri geçersiz: "
                << e.what()
                << std::endl;
            return 1;
        }

        if (start_number < 1 ||
            segment_time < 1 ||
            fps < 1 ||
            width < 2 ||
            height < 2) {

            std::cerr
                << "C++ Hata: --record-wayland parametreleri geçersiz."
                << std::endl;

            return 1;
        }

        Config cfg;
        cfg.record = true;
        cfg.dir = output_dir;
        cfg.start = start_number;
        cfg.seg = segment_time;
        cfg.fps = fps;
        cfg.w = width;
        cfg.h = height;
        cfg.screen = "wayland";
        return run_engine(cfg);
    }

    if (command == "--merge-recordings") {
        if (!std::filesystem::exists(ffmpeg_path)) {
            std::cerr
                << "C++ Hata: " << ffmpeg_path
                << " bulunamadı. Uygulama dizininde bin/ffmpeg olmalı."
                << std::endl;
            fflush(stderr);
            return 1;
        }

        if (access(ffmpeg_path.c_str(), X_OK) != 0) {
            std::cerr
                << "C++ Hata: " << ffmpeg_path
                << " dosyası çalıştırılabilir değil (izin hatası)."
                << std::endl;
            fflush(stderr);
            return 1;
        }

        if (argc != 5) {
            std::cerr << "C++ Hata: --merge-recordings için yanlış sayıda argüman. 3 parametre (video_list_file, audio_list_file, output_file) bekleniyordu, " << argc - 2 << " parametre alındı." << std::endl;
            fflush(stderr);
            return 1;
        }
        std::string video_list_file = argv[2];
        std::string audio_list_file = argv[3];
        std::string output_file = argv[4];

        if (video_list_file == "NUL" || video_list_file == "/dev/null") video_list_file = "";
        if (audio_list_file == "NUL" || audio_list_file == "/dev/null") audio_list_file = "";

        return mergeRecordings(ffmpeg_path, video_list_file, audio_list_file, output_file);
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
