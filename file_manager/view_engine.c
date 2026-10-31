#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <pthread.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    double zoom;
    int pan_x;
    int pan_y;
} kv_view_state;

static double clampd(double v, double lo, double hi) {
    if (lo > hi) {
        double t = lo;
        lo = hi;
        hi = t;
    }
    if (isnan(v)) return lo;
    /* +inf üst sınıra, -inf alt sınıra gider (eski sürüm ikisini de lo yapıyordu). */
    return v < lo ? lo : (v > hi ? hi : v);
}

static double safe_factor(double factor) {
    if (!isfinite(factor) || factor <= 0.0) return 1.0;
    return factor;
}

static void normalize_zoom_bounds(double *min_zoom, double *max_zoom) {
    if (!min_zoom || !max_zoom) return;
    if (!isfinite(*min_zoom) || *min_zoom <= 0.0) *min_zoom = 0.05;
    if (!isfinite(*max_zoom) || *max_zoom <= 0.0) *max_zoom = 64.0;
    if (*min_zoom > *max_zoom) {
        double t = *min_zoom;
        *min_zoom = *max_zoom;
        *max_zoom = t;
    }
    if (*min_zoom <= 0.0) *min_zoom = 0.05;
    if (*max_zoom < *min_zoom) *max_zoom = *min_zoom;
}

void kv_view_reset(kv_view_state* s) {
    if (!s) return;
    s->zoom = 1.0;
    s->pan_x = 0;
    s->pan_y = 0;
}

void kv_view_zoom(kv_view_state* s, double factor, double min_zoom, double max_zoom) {
    if (!s) return;
    normalize_zoom_bounds(&min_zoom, &max_zoom);
    const double current = clampd(s->zoom, min_zoom, max_zoom);
    const double next = current * safe_factor(factor);
    s->zoom = isfinite(next) ? clampd(next, min_zoom, max_zoom) : max_zoom;
}

/*
 * Zoom around a mouse/gesture anchor.
 * screen = viewport_center + pan + (image_point * zoom)
 * Keeping the cursor position stable means updating pan together with zoom.
 */
void kv_view_zoom_at(kv_view_state* s,
                     double factor,
                     double anchor_x,
                     double anchor_y,
                     double center_x,
                     double center_y,
                     double min_zoom,
                     double max_zoom) {
    if (!s) return;
    normalize_zoom_bounds(&min_zoom, &max_zoom);

    const double old_zoom = clampd(s->zoom, min_zoom, max_zoom);
    const double raw_new_zoom = old_zoom * safe_factor(factor);
    const double new_zoom = isfinite(raw_new_zoom)
        ? clampd(raw_new_zoom, min_zoom, max_zoom) : max_zoom;

    if (new_zoom <= 0.0 || !isfinite(new_zoom)) return;
    if (fabs(new_zoom - old_zoom) < 1e-12) return;

    const double rel_x = anchor_x - center_x - (double)s->pan_x;
    const double rel_y = anchor_y - center_y - (double)s->pan_y;
    const double scale = new_zoom / old_zoom;

    double next_pan_x = (double)(anchor_x - center_x) - rel_x * scale;
    double next_pan_y = (double)(anchor_y - center_y) - rel_y * scale;

    if (!isfinite(next_pan_x)) next_pan_x = s->pan_x;
    if (!isfinite(next_pan_y)) next_pan_y = s->pan_y;

    s->zoom = new_zoom;
    if (next_pan_x > (double)INT32_MAX) next_pan_x = (double)INT32_MAX;
    if (next_pan_x < (double)INT32_MIN) next_pan_x = (double)INT32_MIN;
    if (next_pan_y > (double)INT32_MAX) next_pan_y = (double)INT32_MAX;
    if (next_pan_y < (double)INT32_MIN) next_pan_y = (double)INT32_MIN;
    s->pan_x = (int)llround(next_pan_x);
    s->pan_y = (int)llround(next_pan_y);
}

void kv_view_pan(kv_view_state* s, int dx, int dy) {
    if (!s) return;
    if (dx > 0 && s->pan_x > INT32_MAX - dx) s->pan_x = INT32_MAX;
    else if (dx < 0 && s->pan_x < INT32_MIN - dx) s->pan_x = INT32_MIN;
    else s->pan_x += dx;

    if (dy > 0 && s->pan_y > INT32_MAX - dy) s->pan_y = INT32_MAX;
    else if (dy < 0 && s->pan_y < INT32_MIN - dy) s->pan_y = INT32_MIN;
    else s->pan_y += dy;
}

int64_t kv_frame_step(int64_t position_ms, int64_t duration_ms, int direction, int64_t frame_ms) {
    if (frame_ms < 1) frame_ms = 33;
    if (position_ms < 0) position_ms = 0;
    if (duration_ms >= 0 && position_ms > duration_ms) position_ms = duration_ms;

    int64_t p;
    if (direction < 0) {
        p = (position_ms <= frame_ms) ? 0 : position_ms - frame_ms;
    } else {
        /* Saturate before adding to avoid signed int64 overflow. */
        p = (position_ms > INT64_MAX - frame_ms) ? INT64_MAX : position_ms + frame_ms;
    }
    if (duration_ms >= 0 && p > duration_ms) p = duration_ms;
    return p;
}

/* Small reusable RGBA buffer pool. Thread-safe, bounded, and double-release tolerant. */
typedef struct kv_buffer {
    uint8_t* data;
    size_t size;
    int in_pool;
    size_t ref_count;
    struct kv_buffer* next;
} kv_buffer;

static kv_buffer* g_free = NULL;
static size_t g_pool_bytes = 0;
static const size_t KV_MAX_POOL_BYTES = 64u * 1024u * 1024u;
static const size_t KV_MAX_POOL_COUNT = 64u;
static size_t g_pool_count = 0;
static pthread_mutex_t g_pool_lock = PTHREAD_MUTEX_INITIALIZER;

void* kv_buffer_acquire(size_t bytes) {
    kv_buffer* chosen = NULL;

    pthread_mutex_lock(&g_pool_lock);
    /* Best-fit: isteği karşılayan EN KÜÇÜK tampon seçilir. İlk uyan (first-fit) seçimde
     * 1 KB'lık istek 60 MB'lık tamponu kilitleyebiliyordu. 2x'ten büyük israf kabul edilmez. */
    kv_buffer** best = NULL;
    for (kv_buffer** cur = &g_free; *cur; cur = &(*cur)->next) {
        size_t sz = (*cur)->size;
        if (sz >= bytes && (bytes == 0 || sz / 2 <= bytes) && (!best || sz < (*best)->size)) {
            best = cur;
            if (sz == bytes) break;
        }
    }
    if (best) {
        chosen = *best;
        *best = chosen->next;
        chosen->next = NULL;
        chosen->in_pool = 0;
        chosen->ref_count = 1;
        if (g_pool_bytes >= chosen->size) g_pool_bytes -= chosen->size;
        else g_pool_bytes = 0;
        if (g_pool_count > 0) --g_pool_count;
    }
    pthread_mutex_unlock(&g_pool_lock);

    if (chosen) return chosen;

    kv_buffer* b = (kv_buffer*)calloc(1, sizeof(kv_buffer));
    if (!b) return NULL;
    b->data = (uint8_t*)malloc(bytes ? bytes : 1);
    if (!b->data) {
        free(b);
        return NULL;
    }
    b->size = bytes;
    b->in_pool = 0;
    b->ref_count = 1;
    b->next = NULL;
    return b;
}

uint8_t* kv_buffer_data(void* ptr) {
    kv_buffer* b = (kv_buffer*)ptr;
    return b ? b->data : NULL;
}

size_t kv_buffer_size(void* ptr) {
    kv_buffer* b = (kv_buffer*)ptr;
    return b ? b->size : 0;
}

/* Reference counting makes retain/release semantics match the exported ABI. */
void kv_buffer_retain(void* ptr) {
    if (!ptr) return;
    kv_buffer* b = (kv_buffer*)ptr;
    pthread_mutex_lock(&g_pool_lock);
    if (!b->in_pool && b->ref_count > 0 && b->ref_count < SIZE_MAX)
        ++b->ref_count;
    pthread_mutex_unlock(&g_pool_lock);
}

void kv_buffer_release(void* ptr) {
    if (!ptr) return;
    kv_buffer* b = (kv_buffer*)ptr;

    pthread_mutex_lock(&g_pool_lock);
    if (b->in_pool) {
        pthread_mutex_unlock(&g_pool_lock);
        return;
    }
    if (b->ref_count > 1) {
        --b->ref_count;
        pthread_mutex_unlock(&g_pool_lock);
        return;
    }
    b->ref_count = 0;
    if (b->size > 0 && b->size <= KV_MAX_POOL_BYTES && g_pool_count < KV_MAX_POOL_COUNT &&
        g_pool_bytes <= KV_MAX_POOL_BYTES - b->size) {
        b->in_pool = 1;
        b->next = g_free;
        g_free = b;
        g_pool_bytes += b->size;
        ++g_pool_count;
        pthread_mutex_unlock(&g_pool_lock);
        return;
    }
    pthread_mutex_unlock(&g_pool_lock);

    free(b->data);
    free(b);
}

void kv_buffer_pool_trim(void) {
    pthread_mutex_lock(&g_pool_lock);
    kv_buffer* b = g_free;
    g_free = NULL;
    g_pool_bytes = 0;
    g_pool_count = 0;
    pthread_mutex_unlock(&g_pool_lock);

    while (b) {
        kv_buffer* n = b->next;
        b->next = NULL;
        b->in_pool = 0;
        free(b->data);
        free(b);
        b = n;
    }
}

#ifdef __cplusplus
}
#endif
