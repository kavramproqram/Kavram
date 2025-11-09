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

// record.cpp
#include <iostream>
#include <atomic>
#include <portaudio.h>
#include <sndfile.h>

static std::atomic<bool> g_recording(false);
static PaStream *stream = nullptr;
static SNDFILE *sndfile;
static SF_INFO sfinfo;

static int recordCallback(const void *input, void *, unsigned long frameCount,
                          const PaStreamCallbackTimeInfo *, PaStreamCallbackFlags,
                          void *) {
    if (g_recording && sndfile) {
        sf_writef_float(sndfile, (const float *)input, frameCount);
    }
    return g_recording ? paContinue : paComplete;
}

extern "C" {

int init_audio() {
    return Pa_Initialize();
}

int record_wav(const char *filepath) {
    if (g_recording) return -1;
    sfinfo.channels = 1;
    sfinfo.samplerate = 44100;
    sfinfo.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;

    sndfile = sf_open(filepath, SFM_WRITE, &sfinfo);
    if (!sndfile) return -2;

    PaError err = Pa_OpenDefaultStream(&stream, 1, 0, paFloat32, sfinfo.samplerate,
                                       paFramesPerBufferUnspecified, recordCallback, nullptr);
    if (err != paNoError) return err;

    g_recording = true;
    err = Pa_StartStream(stream);
    if (err != paNoError) return err;
    return 0;
}

int stop_wav() {
    if (!g_recording) return -1;
    g_recording = false;
    Pa_StopStream(stream);
    Pa_CloseStream(stream);
    sf_close(sndfile);
    return 0;
}

int close_audio() {
    return Pa_Terminate();
}

}

