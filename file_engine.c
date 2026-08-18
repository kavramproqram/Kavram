#define _GNU_SOURCE

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <pthread.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#include <limits.h>
#include <math.h>
#include <stdarg.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    char name[256];
    char path[1024];
    bool is_directory;
    bool is_hidden;
    uint64_t size;
    int64_t mtime;
} FileItem;

typedef struct {
    char kind[32];
    char mime[160];
    char extension[32];
    char label[64];
    char detail[256];
    bool safe_to_preview;
    bool playable;
    uint64_t size;
} FileAnalysis;

/* Directory cache is per-thread to keep worker-thread calls isolated. */
static _Thread_local FileItem *g_items = NULL;
static _Thread_local size_t g_items_count = 0;
static _Thread_local size_t g_items_capacity = 0;

#define ANALYSIS_CACHE_SIZE 256
#define ANALYSIS_KEY_SIZE 1200

typedef struct {
    int valid;
    char key[ANALYSIS_KEY_SIZE];
    FileAnalysis analysis;
    uint64_t stamp;
} AnalysisCacheEntry;

static AnalysisCacheEntry g_analysis_cache[ANALYSIS_CACHE_SIZE];
static pthread_mutex_t g_analysis_lock = PTHREAD_MUTEX_INITIALIZER;
static uint64_t g_analysis_stamp = 1;

static void copy_str(char *dst, size_t cap, const char *src) {
    if (!dst || cap == 0) return;
    if (!src) src = "";
    size_t n = strlen(src);
    if (n >= cap) n = cap - 1;
    memcpy(dst, src, n);
    dst[n] = '\0';
}

static const char *home_dir(void) {
    const char *h = getenv("HOME");
    return (h && *h) ? h : "";
}

static void trim_inplace(char *s) {
    if (!s) return;
    char *p = s;
    while (*p && isspace((unsigned char)*p)) ++p;
    if (p != s) memmove(s, p, strlen(p) + 1);
    size_t n = strlen(s);
    while (n > 0 && isspace((unsigned char)s[n - 1])) s[--n] = '\0';
}

static const char *extension_ptr(const char *path) {
    const char *slash = strrchr(path ? path : "", '/');
    const char *base = slash ? slash + 1 : (path ? path : "");
    const char *dot = strrchr(base, '.');
    return (dot && dot != base) ? dot : "";
}

static void lowercase_copy(char *dst, size_t cap, const char *src) {
    if (!dst || cap == 0) return;
    size_t i = 0;
    if (src) {
        for (; src[i] && i + 1 < cap; ++i)
            dst[i] = (char)tolower((unsigned char)src[i]);
    }
    dst[i] = '\0';
}

static const char *classify_mime(const char *mime, const char *ext) {
    char m[160];
    lowercase_copy(m, sizeof(m), mime);
    if (strncmp(m, "image/", 6) == 0) return "image";
    if (strncmp(m, "video/", 6) == 0) return "video";
    if (strncmp(m, "audio/", 6) == 0) return "audio";
    if (strcmp(m, "application/pdf") == 0) return "pdf";
    if (strncmp(m, "text/", 5) == 0 || strstr(m, "json") || strstr(m, "xml") ||
        strstr(m, "javascript") || strstr(m, "csv")) return "text";
    if (strstr(m, "zip") || strstr(m, "compressed") || strstr(m, "tar") ||
        strstr(m, "gzip") || strstr(m, "bzip") || strstr(m, "xz") ||
        strstr(m, "7z") || strstr(m, "rar")) return "archive";
    if (strstr(m, "font")) return "font";
    if (strstr(m, "officedocument") || strstr(m, "msword") ||
        strstr(m, "ms-excel") || strstr(m, "ms-powerpoint") || strstr(m, "opendocument"))
        return "document";
    if (strstr(m, "diskimage") || strstr(m, "iso")) return "disk";
    if (strcmp(m, "application/octet-stream") == 0) return "binary";
    return (ext && *ext) ? "file" : "binary";
}

static const char *turkish_label(const char *kind) {
    if (!strcmp(kind, "dir")) return "Klasör";
    if (!strcmp(kind, "image")) return "Resim";
    if (!strcmp(kind, "video")) return "Video";
    if (!strcmp(kind, "audio")) return "Ses";
    if (!strcmp(kind, "pdf")) return "Kitap";
    if (!strcmp(kind, "text")) return "Yazı";
    if (!strcmp(kind, "document")) return "Belge";
    if (!strcmp(kind, "archive")) return "Arşiv";
    if (!strcmp(kind, "font")) return "Yazı tipi";
    if (!strcmp(kind, "disk")) return "Disk";
    if (!strcmp(kind, "binary")) return "İkili dosya";
    return "Dosya";
}

static int preview_safe_kind(const char *kind) {
    return !strcmp(kind, "image") || !strcmp(kind, "video") ||
           !strcmp(kind, "audio") || !strcmp(kind, "pdf") || !strcmp(kind, "text");
}

static int append_item(const FileItem *item) {
    if (g_items_count == g_items_capacity) {
        size_t next = g_items_capacity ? g_items_capacity * 2 : 128;
        FileItem *p = (FileItem *)realloc(g_items, next * sizeof(*g_items));
        if (!p) return 0;
        g_items = p;
        g_items_capacity = next;
    }
    g_items[g_items_count++] = *item;
    return 1;
}

static int cmp_items(const void *va, const void *vb, void *ctx) {
    const FileItem *a = (const FileItem *)va;
    const FileItem *b = (const FileItem *)vb;
    int sort_mode = *(const int *)ctx;
    if (a->is_directory != b->is_directory)
        return a->is_directory ? -1 : 1;
    if (sort_mode == 1 && a->mtime != b->mtime)
        return (a->mtime > b->mtime) ? -1 : 1;
    if (sort_mode == 2 && a->size != b->size)
        return (a->size > b->size) ? -1 : 1;
    return strcmp(a->name, b->name);
}

static void sort_items(int sort_mode) {
#if defined(__GLIBC__)
    qsort_r(g_items, g_items_count, sizeof(*g_items), cmp_items, &sort_mode);
#else
    /* Portable fallback: decorate with a temporary index and insertion sort.
       Directory lists are normally small; avoids non-standard qsort_r ABI. */
    for (size_t i = 1; i < g_items_count; ++i) {
        FileItem key = g_items[i];
        size_t j = i;
        while (j > 0 && cmp_items(&key, &g_items[j - 1], &sort_mode) < 0) {
            g_items[j] = g_items[j - 1];
            --j;
        }
        g_items[j] = key;
    }
#endif
}

static int is_regular_file_safe(const char *path, struct stat *st_out) {
    if (!path || !*path) return 0;
    struct stat st;
    if (lstat(path, &st) != 0 || !S_ISREG(st.st_mode)) return 0;
    if (st_out) *st_out = st;
    return 1;
}

static int make_key(char *out, size_t cap, const char *path, const struct stat *st) {
    if (!out || !cap || !path || !st) return 0;
    int n = snprintf(out, cap, "%s\n%lld:%ld\n%lld",
                     path,
                     (long long)st->st_mtim.tv_sec,
                     (long)st->st_mtim.tv_nsec,
                     (long long)st->st_size);
    return n >= 0 && (size_t)n < cap;
}

static int cache_lookup(const char *key, FileAnalysis *out) {
    int found = 0;
    pthread_mutex_lock(&g_analysis_lock);
    for (size_t i = 0; i < ANALYSIS_CACHE_SIZE; ++i) {
        if (g_analysis_cache[i].valid && strcmp(g_analysis_cache[i].key, key) == 0) {
            *out = g_analysis_cache[i].analysis;
            g_analysis_cache[i].stamp = ++g_analysis_stamp;
            found = 1;
            break;
        }
    }
    pthread_mutex_unlock(&g_analysis_lock);
    return found;
}

static void cache_store(const char *key, const FileAnalysis *analysis) {
    pthread_mutex_lock(&g_analysis_lock);
    size_t slot = 0;
    uint64_t oldest = UINT64_MAX;
    for (size_t i = 0; i < ANALYSIS_CACHE_SIZE; ++i) {
        if (!g_analysis_cache[i].valid) { slot = i; oldest = 0; break; }
        if (g_analysis_cache[i].stamp < oldest) {
            oldest = g_analysis_cache[i].stamp;
            slot = i;
        }
    }
    g_analysis_cache[slot].valid = 1;
    copy_str(g_analysis_cache[slot].key, sizeof(g_analysis_cache[slot].key), key);
    g_analysis_cache[slot].analysis = *analysis;
    g_analysis_cache[slot].stamp = ++g_analysis_stamp;
    pthread_mutex_unlock(&g_analysis_lock);
}

/* Execute argv without a shell, capture stdout+stderr, and enforce a timeout. */
static int read_command_output(char *const argv[], int timeout_ms, char *out, size_t out_cap) {
    if (!argv || !argv[0] || !out || out_cap == 0) return 0;
    out[0] = '\0';
    int pipefd[2];
    if (pipe(pipefd) != 0) return 0;
    pid_t pid = fork();
    if (pid < 0) { close(pipefd[0]); close(pipefd[1]); return 0; }
    if (pid == 0) {
        int flags = fcntl(pipefd[1], F_GETFD);
        if (flags >= 0) fcntl(pipefd[1], F_SETFD, flags & ~FD_CLOEXEC);
        dup2(pipefd[1], STDOUT_FILENO);
        dup2(pipefd[1], STDERR_FILENO);
        close(pipefd[0]); close(pipefd[1]);
        execvp(argv[0], argv);
        _exit(127);
    }
    close(pipefd[1]);
    size_t used = 0;
    int status = 0;
    int elapsed = 0;
    for (;;) {
        struct pollfd pfd = { pipefd[0], POLLIN, 0 };
        int wait_ms = timeout_ms - elapsed;
        if (wait_ms <= 0) break;
        if (wait_ms > 100) wait_ms = 100;
        int pr = poll(&pfd, 1, wait_ms);
        elapsed += wait_ms;
        if (pr > 0 && (pfd.revents & (POLLIN | POLLHUP))) {
            char buf[1024];
            ssize_t n = read(pipefd[0], buf, sizeof(buf));
            if (n > 0) {
                size_t copy = (size_t)n;
                if (copy > out_cap - 1 - used) copy = out_cap - 1 - used;
                if (copy) {
                    memcpy(out + used, buf, copy);
                    used += copy;
                    out[used] = '\0';
                }
            }
        }
        pid_t done = waitpid(pid, &status, WNOHANG);
        if (done == pid) {
            for (;;) {
                char buf[1024];
                ssize_t n = read(pipefd[0], buf, sizeof(buf));
                if (n <= 0) break;
                size_t copy = (size_t)n;
                if (copy > out_cap - 1 - used) copy = out_cap - 1 - used;
                if (copy) { memcpy(out + used, buf, copy); used += copy; out[used] = '\0'; }
            }
            close(pipefd[0]);
            trim_inplace(out);
            return WIFEXITED(status) && WEXITSTATUS(status) == 0;
        }
        if (pr < 0 && errno != EINTR) break;
    }
    kill(pid, SIGKILL);
    waitpid(pid, &status, 0);
    close(pipefd[0]);
    trim_inplace(out);
    return 0;
}

static int run_to_file(char *const argv[], int timeout_ms) {
    if (!argv || !argv[0]) return 0;
    pid_t pid = fork();
    if (pid < 0) return 0;
    if (pid == 0) {
        int devnull = open("/dev/null", O_WRONLY);
        if (devnull >= 0) {
            dup2(devnull, STDERR_FILENO);
            close(devnull);
        }
        execvp(argv[0], argv);
        _exit(127);
    }
    int status = 0;
    int elapsed = 0;
    while (elapsed < timeout_ms) {
        pid_t done = waitpid(pid, &status, WNOHANG);
        if (done == pid)
            return WIFEXITED(status) && WEXITSTATUS(status) == 0;
        if (done < 0 && errno != EINTR) break;
        usleep(10000);
        elapsed += 10;
    }
    kill(pid, SIGKILL);
    waitpid(pid, &status, 0);
    return 0;
}

static int write_trashinfo(const char *info_path, const char *original_path) {
    FILE *f = fopen(info_path, "w");
    if (!f) return 0;
    time_t now = time(NULL);
    struct tm tmv;
    localtime_r(&now, &tmv);
    char buf[64];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S", &tmv);
    fputs("[Trash Info]\nPath=", f);
    for (const unsigned char *p = (const unsigned char *)original_path; p && *p; ++p) {
        unsigned char c = *p;
        if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
            (c >= '0' && c <= '9') || c == '/' || c == '.' || c == '_' ||
            c == '-' || c == '~') {
            fputc(c, f);
        } else {
            fprintf(f, "%%%02X", (unsigned)c);
        }
    }
    fprintf(f, "\nDeletionDate=%s\n", buf);
    int ok = !ferror(f);
    fclose(f);
    return ok;
}

static int mkdir_p(const char *path, mode_t mode) {
    if (!path || !*path) return 0;
    char tmp[PATH_MAX];
    if (strlen(path) >= sizeof(tmp)) return 0;
    strcpy(tmp, path);
    if (tmp[0] == '/' && tmp[1] == '\0') return 1;
    for (char *p = tmp + 1; *p; ++p) {
        if (*p == '/') {
            *p = '\0';
            if (mkdir(tmp, mode) != 0 && errno != EEXIST) return 0;
            *p = '/';
        }
    }
    if (mkdir(tmp, mode) != 0 && errno != EEXIST) return 0;
    return 1;
}

/* ------------------------------ exported ABI ------------------------------ */

int fetch_directory_items(const char *dir_path, int show_hidden, int sort_mode) {
    g_items_count = 0;
    if (!dir_path || !*dir_path) return -1;

    DIR *dir = opendir(dir_path);
    if (!dir) return -1;

    struct dirent *de;
    while ((de = readdir(dir)) != NULL) {
        const char *name = de->d_name;
        if (!name[0] || (!show_hidden && name[0] == '.')) continue;

        FileItem item;
        memset(&item, 0, sizeof(item));
        copy_str(item.name, sizeof(item.name), name);
        int n = snprintf(item.path, sizeof(item.path), "%s/%s", dir_path, name);
        if (n < 0 || (size_t)n >= sizeof(item.path)) continue;
        item.is_hidden = (name[0] == '.');

        struct stat st;
        if (stat(item.path, &st) == 0) {
            item.is_directory = S_ISDIR(st.st_mode);
            item.size = S_ISREG(st.st_mode) ? (uint64_t)st.st_size : 0;
            item.mtime = (int64_t)st.st_mtime;
        } else {
            /* Keep inaccessible entries visible, but harmlessly marked as file. */
            item.is_directory = 0;
            item.size = 0;
            item.mtime = 0;
        }
        if (!append_item(&item)) { closedir(dir); return -1; }
    }
    closedir(dir);
    sort_items(sort_mode);
    return (int)g_items_count;
}

bool get_item_at(int index, FileItem *out_item) {
    if (!out_item || index < 0 || (size_t)index >= g_items_count) return false;
    *out_item = g_items[(size_t)index];
    return true;
}

void clear_cache(void) {
    free(g_items);
    g_items = NULL;
    g_items_count = 0;
    g_items_capacity = 0;
}

int analyze_file(const char *path, FileAnalysis *out) {
    if (!out) return 0;
    memset(out, 0, sizeof(*out));

    struct stat st;
    if (!is_regular_file_safe(path, &st)) {
        copy_str(out->kind, sizeof(out->kind), "unsafe");
        copy_str(out->label, sizeof(out->label), "Güvenli değil");
        return 0;
    }

    char key[ANALYSIS_KEY_SIZE];
    if (!make_key(key, sizeof(key), path, &st)) return 0;
    if (cache_lookup(key, out)) return 1;

    const char *ext = extension_ptr(path);
    copy_str(out->extension, sizeof(out->extension), (*ext) ? ext : "(uzantısız)");
    out->size = (uint64_t)st.st_size;

    char mime[160];
    char *mime_argv[] = { (char *)"file", (char *)"--brief", (char *)"--mime-type", (char *)"--", (char *)path, NULL };
    if (!read_command_output(mime_argv, 2500, mime, sizeof(mime)) || !mime[0])
        copy_str(mime, sizeof(mime), "application/octet-stream");
    copy_str(out->mime, sizeof(out->mime), mime);

    const char *kind = classify_mime(mime, ext);
    copy_str(out->kind, sizeof(out->kind), kind);
    copy_str(out->label, sizeof(out->label), turkish_label(kind));
    out->safe_to_preview = preview_safe_kind(kind);
    out->playable = (!strcmp(kind, "audio") || !strcmp(kind, "video"));

    char detail[256];
    copy_str(detail, sizeof(detail), mime);
    if (out->playable) {
        char probe[160];
        char *probe_argv[] = {
            (char *)"ffprobe", (char *)"-v", (char *)"error", (char *)"-show_entries",
            (char *)"format=duration,format_name", (char *)"-of",
            (char *)"default=noprint_wrappers=1:nokey=0", (char *)"--", (char *)path, NULL
        };
        if (read_command_output(probe_argv, 2500, probe, sizeof(probe)) && probe[0]) {
            size_t used = strlen(detail);
            if (used + 3 < sizeof(detail)) {
                snprintf(detail + used, sizeof(detail) - used, " | %s", probe);
            }
        }
    }
    copy_str(out->detail, sizeof(out->detail), detail);
    cache_store(key, out);
    return 1;
}

int render_preview(const char *path, const char *out_png, int max_w, int max_h, double time_sec) {
    if (!path || !out_png || !*out_png) return 0;
    FileAnalysis a;
    if (!analyze_file(path, &a) || !a.safe_to_preview) return 0;
    if (max_w < 64) max_w = 64;
    if (max_h < 64) max_h = 64;
    if (max_w > 8192) max_w = 8192;
    if (max_h > 8192) max_h = 8192;

    if (!strcmp(a.kind, "image")) {
        char resize[64], output[1100];
        snprintf(resize, sizeof(resize), "%dx%d>", max_w, max_h);
        snprintf(output, sizeof(output), "PNG:%s", out_png);
        char *argv[] = {
            (char *)"convert", (char *)path, (char *)"-auto-orient", (char *)"-resize",
            resize, output, NULL
        };
        return run_to_file(argv, 7000);
    }

    if (!strcmp(a.kind, "pdf")) {
        char prefix[1100];
        copy_str(prefix, sizeof(prefix), out_png);
        char *dot = strrchr(prefix, '.');
        if (dot) *dot = '\0';
        strncat(prefix, "_pdf", sizeof(prefix) - strlen(prefix) - 1);
        char w[32], h[32];
        snprintf(w, sizeof(w), "%d", max_w);
        snprintf(h, sizeof(h), "%d", max_h);
        char *argv[] = {
            (char *)"pdftoppm", (char *)"-f", (char *)"1", (char *)"-singlefile",
            (char *)"-png", (char *)"-scale-to-x", w, (char *)"-scale-to-y", h,
            (char *)path, prefix, NULL
        };
        return run_to_file(argv, 7000);
    }

    if (!strcmp(a.kind, "video")) {
        char ts[64], scale[128];
        if (!isfinite(time_sec) || time_sec < 0.0) time_sec = 0.0;
        snprintf(ts, sizeof(ts), "%.3f", time_sec);
        snprintf(scale, sizeof(scale), "scale=%d:%d:force_original_aspect_ratio=decrease", max_w, max_h);
        char *argv[] = {
            (char *)"ffmpeg", (char *)"-hide_banner", (char *)"-loglevel", (char *)"error",
            (char *)"-ss", ts, (char *)"-i", (char *)path, (char *)"-frames:v", (char *)"1",
            (char *)"-vf", scale, (char *)"-y", (char *)out_png, NULL
        };
        return run_to_file(argv, 9000);
    }

    return 0;
}


static int join_path2(char *dst, size_t cap, const char *a, const char *b) {
    if (!dst || cap == 0 || !a || !b) return 0;
    size_t na = strlen(a);
    size_t nb = strlen(b);
    if (na > cap - 1 || nb > cap - 1) return 0;
    size_t sep = (na > 0 && a[na - 1] == '/') ? 0u : 1u;
    if (na + sep + nb + 1 > cap) return 0;
    memcpy(dst, a, na);
    size_t pos = na;
    if (sep) dst[pos++] = '/';
    memcpy(dst + pos, b, nb);
    dst[pos + nb] = '\0';
    return 1;
}

static int join_suffix(char *dst, size_t cap, const char *dir,
                       const char *base, const char *suffix) {
    if (!dst || cap == 0 || !dir || !base || !suffix) return 0;
    size_t nd = strlen(dir), nb = strlen(base), ns = strlen(suffix);
    size_t sep = (nd > 0 && dir[nd - 1] == '/') ? 0u : 1u;
    if (nd + sep + nb + ns + 1 > cap) return 0;
    size_t p = 0;
    memcpy(dst + p, dir, nd); p += nd;
    if (sep) dst[p++] = '/';
    memcpy(dst + p, base, nb); p += nb;
    memcpy(dst + p, suffix, ns); p += ns;
    dst[p] = '\0';
    return 1;
}

int trash_item(const char *file_path) {
    if (!file_path || !*file_path) return 0;
    struct stat st;
    if (lstat(file_path, &st) != 0) return 0;

    char files_dir[PATH_MAX], info_dir[PATH_MAX];
    const char *home = home_dir();
    if (!home[0]) return 0;
    if (!join_suffix(files_dir, sizeof(files_dir), home, ".local/share/Trash", "/files")) {
        return 0;
    }
    if (!join_suffix(info_dir, sizeof(info_dir), home, ".local/share/Trash", "/info")) {
        return 0;
    }
    if (!mkdir_p(files_dir, 0700) || !mkdir_p(info_dir, 0700)) return 0;

    const char *base = strrchr(file_path, '/');
    base = base ? base + 1 : file_path;
    if (!*base) return 0;

    char dest[PATH_MAX];
    if (!join_path2(dest, sizeof(dest), files_dir, base)) return 0;
    if (access(dest, F_OK) == 0) {
        int found = 0;
        for (int n = 1; n < 100000; ++n) {
            char suffix[32];
            int sn = snprintf(suffix, sizeof(suffix), ".%d", n);
            if (sn < 0 || (size_t)sn >= sizeof(suffix)) return 0;
            if (!join_suffix(dest, sizeof(dest), files_dir, base, suffix)) return 0;
            if (access(dest, F_OK) != 0) {
                found = 1;
                break;
            }
        }
        if (!found) return 0;
    }

    if (rename(file_path, dest) != 0) {
        /* Cross-filesystem fallback using safe argv-only helpers. */
        char *cp_argv[] = { (char *)"cp", (char *)"-a", (char *)"--", (char *)file_path, dest, NULL };
        if (!run_to_file(cp_argv, 30000)) return 0;
        char *rm_argv[] = {
            (char *)"rm", (char *)"-rf", (char *)"--", (char *)file_path, NULL
        };
        if (!run_to_file(rm_argv, 30000)) return 0;
    }

    char info_path[PATH_MAX];
    const char *dest_base = strrchr(dest, '/');
    dest_base = dest_base ? dest_base + 1 : dest;
    if (!join_suffix(info_path, sizeof(info_path), info_dir, dest_base, ".trashinfo"))
        return 0;
    write_trashinfo(info_path, file_path);
    return 1;
}

#ifdef __cplusplus
}
#endif
