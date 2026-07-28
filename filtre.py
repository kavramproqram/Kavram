#!/usr/bin/env python3
# Kavram 2.2.2
# Copyright (C) 2026-07-22 Kavram or Contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see /Kavram/License/GPLv3.txt
#
# ---------------------------------------------
#
# Kavram 2.2.2
# Copyright (C) 2026-07-22 Kavram veya Contributors
#
# Bu program özgür bir yazılımdır: Özgür Yazılım Vakfı tarafından yayınlanan
# GNU Genel Kamu Lisansı'nın 3. sürümü veya (tercihinize bağlı olarak)
# daha sonraki herhangi bir sürümü kapsamında yeniden dağıtabilir ve/veya
# değiştirebilirsiniz.
#
# Bu program, faydalı olacağı umuduyla dağıtılmaktadır, ancak HERHANGİ BİR
# GARANTİ OLMADAN; hatta SATILABİLİRLİK veya BELİRLİ BİR AMACA UYGUNLUK
# zımni garantisi olmaksızın.
#
# Bu programla birlikte GNU Genel Kamu Lisansı'nın bir kopyasını almış olmanız gerekir:
# /Kavram/License/GPLv3.txt

# -*- coding: utf-8 -*-
"""
Kavram Pro v5.3 - Seri Filtreleme Sistemi + x2 Akıllı Alt Frekans Susturma (VAD)
===================================================================
- x1 Filtresi (Silinemez, açılıp kapanabilir)
- x2 Filtresi (Silinemez, açılıp kapanabilir, 30-200 Hz alt kesim, varsayılan 75 Hz)
- x2 SADECE o frekans altındaki gürültü bölgelerini tespit eder ve sesi TAMAMEN 0'a indirir.
- x2 kesme frekansı kalıcıdır (JSON'da saklanır)
- Gürültü Profili Yönetimi (Sağ tık ile silme)
- Seri Filtreleme (Her filtre için 0-100 Progress Bar)
- 5 Saniye Önizleme
- Varsayılan Export Klasörü
- Video desteği (sesi filtrele, video ile birleştir)
- Her profil için güç ayarı (1-9) (ComboBox, tekerlek desteği)
- Reset butonu (tüm profilleri varsayılana döndür, x2 frekansı 75 Hz)
- Rapor paneli: son 5 eylem, seçilebilir/kopyalanabilir, sıra numarası yok
- YENİ: Harici bağlantılar için process_audio_background metodu (Media, Camera)
- GÜNCELLEME: Sağ tık ile Kalıcı Müzik Ekleme & Hassas Müzik Seviyesi Ayarı (0-20%)
"""

import sys
import os
import json
import subprocess
import tempfile
import shutil
import numpy as np
import librosa
import soundfile as sf
import sounddevice as sd
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Optional, List
import warnings
warnings.filterwarnings('ignore')

from scipy.io import wavfile
from scipy.ndimage import gaussian_filter1d
from scipy.signal import butter, filtfilt

from pydub import AudioSegment

from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel,
    QFileDialog, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QMessageBox, QMenu, QAction, QGroupBox,
    QFrame, QSizePolicy, QProgressBar, QRadioButton,
    QSpinBox, QComboBox, QTextEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QThread, QTimer, QEvent, QPoint
from PyQt5.QtGui import QFont, QIcon, QWheelEvent

# =========================
# KOD İÇİNE GÖMÜLÜ AYARLAR
# =========================

MAX_PROFILES = 8  # Maksimum gürültü profili sayısı
PREVIEW_DURATION = 5000  # 5 saniye önizleme (ms)
MAX_REPORT_LINES = 5  # Raporda tutulacak maksimum satır sayısı (son 5 eylem)

# Varsayılan Export Klasörü - Script'in bulunduğu dizinde
# Varsayılan Export Klasörü - Çalışma dizininde
DEFAULT_EXPORT_DIR = Path(os.getcwd()) / "Export"
DEFAULT_EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Profil dosyası konumu
PROFILES_DIR = Path(os.getcwd()) / "veri"
PROFILES_FILE = PROFILES_DIR / "data.json"
X2_CONFIG_FILE = PROFILES_DIR / "x2_config.json"  # x2 ayarları için ayrı dosya
MUSIC_CONFIG_FILE = PROFILES_DIR / "music_config.json" # Kalıcı müzik ayarları için

# İkon dizini
ICON_DIR = Path(os.getcwd()) / "ikon"

# Desteklenen video uzantıları
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.rec')
AUDIO_EXTENSIONS = ('.wav', '.mp3', '.flac', '.ogg', '.aac', '.m4a', '.saund')


# =========================
# YENİ: UYGULAMA İÇİ FFMPEG YOLU
# =========================
def resource_path(relative_path):
    """ PyInstaller vb. derlemeler için dinamik kaynak yolu bulucu. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---- Uygulama içi FFmpeg yolu (bin/ altında) ----
FFMPEG_PATH = resource_path("bin/ffmpeg")
if not os.path.exists(FFMPEG_PATH):
    print(f"Uyarı: {FFMPEG_PATH} bulunamadı. Video işleme çalışmayabilir.")
elif not os.access(FFMPEG_PATH, os.X_OK):
    print(f"Uyarı: {FFMPEG_PATH} çalıştırılabilir değil. Video işleme çalışmayabilir.")


# =========================
# YENİ: SAĞ TIKLANABİLİR BUTON SINIFI
# =========================
class RightClickButton(QPushButton):
    rightClicked = pyqtSignal()
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.RightButton:
            self.rightClicked.emit()

# =========================
# x1 FİLTRE ALGORİTMASI
# =========================

class X1Denoiser:
    """x1 Filtresi - 2 Aşamalı Spektral Temizleme"""
    def __init__(self, sr: int, power: int = 5):
        self.sr = sr
        self.n_fft = 2048
        self.hop_length = 512
        self.power = power  # 1-9 arası güç, varsayılan 5

    def process(self, audio: np.ndarray, progress_callback=None) -> np.ndarray:
        alpha = 1.2 + (self.power - 1) * 0.2   # 1.2 -> 2.8 arası
        beta = 0.05 + (self.power - 1) * 0.02   # 0.05 -> 0.21 arası
        
        if progress_callback: progress_callback(5)

        D = librosa.stft(audio, n_fft=self.n_fft, hop_length=self.hop_length)
        mag = np.abs(D)
        phase = np.angle(D)

        if progress_callback: progress_callback(20)

        noise_est = np.median(mag, axis=1, keepdims=True)
        mask = (mag - alpha * noise_est) / (mag + 1e-10)
        mask = np.clip(mask, beta, 1.0)

        if progress_callback: progress_callback(40)

        mask = gaussian_filter1d(mask, sigma=1.0, axis=1)
        mag_clean = mag * mask
        D_clean = mag_clean * np.exp(1j * phase)
        audio_stage1 = librosa.istft(D_clean, hop_length=self.hop_length)

        if progress_callback: progress_callback(50)

        D2 = librosa.stft(audio_stage1, n_fft=self.n_fft, hop_length=self.hop_length)
        mag2 = np.abs(D2)
        phase2 = np.angle(D2)

        if progress_callback: progress_callback(65)

        noise_est2 = np.median(mag2, axis=1, keepdims=True)
        low_boost = np.linspace(1.5 + (self.power-1)*0.1, 1.0, mag2.shape[0]).reshape(-1, 1)
        threshold = noise_est2 * low_boost * (1.5 + (self.power-1)*0.1)

        mask2 = np.where(mag2 > threshold, 1.0, 0.0)
        mask2 = gaussian_filter1d(mask2, sigma=1.0, axis=1)
        mask2[mask2 < 0.05] = 0.0

        if progress_callback: progress_callback(80)

        mag_clean2 = mag2 * mask2
        D_clean2 = mag_clean2 * np.exp(1j * phase2)
        audio_out = librosa.istft(D_clean2, hop_length=self.hop_length)

        if progress_callback: progress_callback(90)

        if len(audio_out) > len(audio):
            audio_out = audio_out[:len(audio)]
        elif len(audio_out) < len(audio):
            audio_out = np.pad(audio_out, (0, len(audio) - len(audio_out)))

        max_val = np.max(np.abs(audio_out))
        if max_val > 0.95:
            audio_out = audio_out * 0.95 / max_val

        if progress_callback: progress_callback(100)

        return audio_out


X1_PROFILE = {
    'id': 'x1_filter',
    'name': 'x1',
    'description': '2 Aşamalı Spektral Filtre',
    'is_builtin': True,
    'active': True,
    'can_delete': False,
    'power': 5
}

# =========================
# x2 FİLTRE ALGORİTMASI
# =========================

class X2Filter:
    def __init__(self, sr: int, cutoff_freq: float = 75.0):
        self.sr = sr
        self.cutoff_freq = cutoff_freq 
        self.n_fft = 2048
        self.hop_length = 512
        self.vad_top_db = 40 

    def process(self, audio: np.ndarray, progress_callback=None) -> np.ndarray:
        if progress_callback: progress_callback(5)

        D = librosa.stft(audio, n_fft=self.n_fft, hop_length=self.hop_length)
        mag = np.abs(D)
        phase = np.angle(D)
        
        if progress_callback: progress_callback(25)

        rms = np.mean(mag, axis=0)

        sorted_rms = np.sort(rms)
        noise_idx = max(1, int(len(sorted_rms) * 0.20))
        noise_floor = np.mean(sorted_rms[:noise_idx])

        if progress_callback: progress_callback(40)

        sensitivity_multiplier = self.cutoff_freq / 20.0
        volume_threshold = noise_floor * sensitivity_multiplier
        max_rms = np.max(rms)

        if progress_callback: progress_callback(50)

        freqs = librosa.fft_frequencies(sr=self.sr, n_fft=self.n_fft)
        low_bins = freqs <= self.cutoff_freq
        high_bins = freqs > self.cutoff_freq

        low_energy = np.sum(mag[low_bins, :], axis=0)
        high_energy = np.sum(mag[high_bins, :], axis=0)

        if progress_callback: progress_callback(60)
        
        is_noise_only = rms <= volume_threshold
        is_low_freq_dominant = low_energy > (high_energy * 2.0)
        is_not_speech = rms < (max_rms * 0.20)

        mute_mask = is_noise_only | (is_low_freq_dominant & is_not_speech)

        if progress_callback: progress_callback(75)

        gain = np.ones(mag.shape[1], dtype=np.float32)
        gain[mute_mask] = 0.0
        gain = gaussian_filter1d(gain, sigma=6.0)

        if progress_callback: progress_callback(85)

        mag_clean = mag * gain
        D_clean = mag_clean * np.exp(1j * phase)
        audio_out = librosa.istft(D_clean, hop_length=self.hop_length)

        if progress_callback: progress_callback(95)

        if len(audio_out) > len(audio):
            audio_out = audio_out[:len(audio)]
        elif len(audio_out) < len(audio):
            audio_out = np.pad(audio_out, (0, len(audio) - len(audio_out)))

        if progress_callback: progress_callback(100)

        return audio_out

X2_PROFILE = {
    'id': 'x2_filter',
    'name': 'x2',
    'description': 'Belirtilen Yükseklik/Frekanstaki Gürültüyü %100 Sustur',
    'is_builtin': True,
    'active': True,
    'can_delete': False,
    'cutoff': 75 
}

# =========================
# KALICI AYAR YÖNETİMİ
# =========================

def load_x2_config():
    try:
        if X2_CONFIG_FILE.exists():
            with open(X2_CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cutoff = data.get('cutoff', 75)
                if 30 <= cutoff <= 200:
                    X2_PROFILE['cutoff'] = cutoff
                else:
                    X2_PROFILE['cutoff'] = 75
        else:
            X2_PROFILE['cutoff'] = 75
    except Exception as e:
        print(f"x2 config yüklenemedi: {e}")
        X2_PROFILE['cutoff'] = 75

def save_x2_config():
    try:
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        with open(X2_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'cutoff': X2_PROFILE['cutoff']}, f, indent=2)
        return True
    except Exception as e:
        print(f"x2 config kaydedilemedi: {e}")
        return False

def load_music_config():
    """Kalıcı arka plan müziği yolunu getir"""
    try:
        if MUSIC_CONFIG_FILE.exists():
            with open(MUSIC_CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('music_path')
    except Exception:
        pass
    return None

def save_music_config(path):
    """Kalıcı arka plan müziğini kaydet"""
    try:
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)
        with open(MUSIC_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({'music_path': path}, f, indent=2)
    except Exception as e:
        print(f"Music config kaydedilemedi: {e}")

# =========================
# DSP / FILTER CORE
# =========================

def audiosegment_to_np(audio_seg: AudioSegment) -> Tuple[np.ndarray, int, int, int]:
    if audio_seg is None:
        raise ValueError("AudioSegment is None")
    
    if audio_seg.sample_width == 8:
        samples = np.array(audio_seg.get_array_of_samples(), dtype=np.float64)
        max_val = np.max(np.abs(samples))
        if max_val > 0:
            samples = samples / max_val
        samples = (samples * 32767).astype(np.int16)
        audio_seg = AudioSegment(
            samples.tobytes(),
            frame_rate=audio_seg.frame_rate,
            sample_width=2,
            channels=audio_seg.channels
        )
    
    samples = np.array(audio_seg.get_array_of_samples())
    channels = audio_seg.channels
    sample_width = audio_seg.sample_width
    if channels > 1:
        arr = samples.reshape((-1, channels)).T.astype(np.float64)
    else:
        arr = samples.reshape((1, -1)).astype(np.float64)
    max_val = float(2 ** (8 * sample_width - 1))
    return arr / max_val, audio_seg.frame_rate, sample_width, channels


def np_to_audiosegment(arr: np.ndarray, sr: int, sample_width: int, channels: int) -> AudioSegment:
    arr = np.clip(arr, -0.99, 0.99)
    max_int = 2 ** (8 * sample_width - 1) - 1
    if channels > 1:
        frames = (arr * max_int).astype(np.int16 if sample_width == 2 else np.int32)
        interleaved = np.empty((frames.shape[1] * channels,), dtype=frames.dtype)
        for i in range(channels):
            interleaved[i::channels] = frames[i]
        raw_data = interleaved.tobytes()
    else:
        raw_data = (arr[0] * max_int).astype(np.int16 if sample_width == 2 else np.int32).tobytes()
    return AudioSegment(data=raw_data, sample_width=sample_width, frame_rate=sr, channels=channels)


def stft(signal, n_fft=2048, hop_length=512):
    return librosa.stft(signal, n_fft=n_fft, hop_length=hop_length)


def istft(stft_matrix, hop_length=512):
    return librosa.istft(stft_matrix, hop_length=hop_length)


def estimate_noise(noise_signal, n_fft=2048, hop_length=512):
    noise_stft = stft(noise_signal, n_fft, hop_length)
    noise_mag = np.abs(noise_stft)

    max_noise = np.max(noise_mag, axis=1, keepdims=True)
    mean_noise = np.mean(noise_mag, axis=1, keepdims=True)

    return (max_noise * 0.8) + (mean_noise * 0.2)


def spectral_subtraction(speech_signal, noise_profile, alpha=3.0, beta=0.0001):
    S = stft(speech_signal)
    mag = np.abs(S)
    phase = np.angle(S)

    mag_power = mag ** 2
    noise_power = noise_profile ** 2

    subtracted_power = mag_power - (alpha * noise_power)
    subtracted_power = np.maximum(subtracted_power, beta * noise_power)
    cleaned_mag = np.sqrt(subtracted_power)

    cleaned_stft = cleaned_mag * np.exp(1j * phase)
    return istft(cleaned_stft)


def serialize_noise_profile(profile_array):
    return {
        'shape': list(profile_array.shape),
        'data': profile_array.flatten().tolist()
    }


def deserialize_noise_profile(profile_dict):
    shape = tuple(profile_dict['shape'])
    data = np.array(profile_dict['data'])
    return data.reshape(shape)

# =========================
# PROFİL YÖNETİMİ
# =========================

class ProfileManager:
    def __init__(self):
        self._ensure_directories()
        self.profiles = self._load_profiles()

    def _ensure_directories(self):
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    def _load_profiles(self):
        if PROFILES_FILE.exists():
            try:
                with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[HATA] Profil dosyası okunamadı: {e}")
                return []
        return []

    def _save_profiles(self):
        try:
            with open(PROFILES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            print(f"[HATA] Profil dosyası kaydedilemedi: {e}")
            return False

    def add_profile(self, name, profile_data, source_file):
        if len(self.profiles) >= MAX_PROFILES:
            return False, f"Maksimum profil sayısına ulaşıldı ({MAX_PROFILES})"

        existing_names = [p['name'] for p in self.profiles]
        if name in existing_names:
            return False, "Bu isimde bir profil zaten mevcut"

        profile_entry = {
            'id': datetime.now().strftime("%Y%m%d_%H%M%S"),
            'name': name,
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'source_file': source_file,
            'profile_data': serialize_noise_profile(profile_data),
            'active': False,
            'is_builtin': False,
            'can_delete': True,
            'power': 5
        }

        self.profiles.append(profile_entry)
        self._save_profiles()
        return True, "Profil başarıyla eklendi"

    def remove_profile(self, profile_id):
        self.profiles = [p for p in self.profiles if p['id'] != profile_id]
        self._save_profiles()

    def set_active(self, profile_id, active):
        if profile_id == 'x1_filter':
            X1_PROFILE['active'] = active
            return
        if profile_id == 'x2_filter':
            X2_PROFILE['active'] = active
            return

        for profile in self.profiles:
            if profile['id'] == profile_id:
                profile['active'] = active
                break
        self._save_profiles()

    def set_power(self, profile_id, power):
        if profile_id == 'x1_filter':
            X1_PROFILE['power'] = power
            return
        for profile in self.profiles:
            if profile['id'] == profile_id:
                profile['power'] = power
                break
        self._save_profiles()

    def set_x2_cutoff(self, cutoff):
        X2_PROFILE['cutoff'] = max(30, min(200, cutoff))
        save_x2_config()

    def reset_all(self):
        X1_PROFILE['power'] = 5
        X2_PROFILE['cutoff'] = 75
        save_x2_config()
        for profile in self.profiles:
            profile['power'] = 5
        self._save_profiles()

    def ensure_at_least_one_active(self):
        any_active = X1_PROFILE['active'] or X2_PROFILE['active'] or any(p.get('active', False) for p in self.profiles)
        if not any_active:
            X1_PROFILE['active'] = True
            self._save_profiles()
            print("[Filtre] Hiçbir profil aktif değildi, x1 otomatik aktif edildi.")

    def get_active_profiles(self):
        active = []
        if X1_PROFILE['active']:
            active.append({
                'id': 'x1_filter',
                'name': 'x1',
                'data': None,
                'is_x1': True,
                'power': X1_PROFILE.get('power', 5)
            })

        for profile in self.profiles:
            if profile['active']:
                profile_array = deserialize_noise_profile(profile['profile_data'])
                active.append({
                    'id': profile['id'],
                    'name': profile['name'],
                    'data': profile_array,
                    'is_x1': False,
                    'power': profile.get('power', 5)
                })
        return active

    def get_profile_count(self):
        return len(self.profiles)

# =========================
# SES DÜZENLEME FONKSİYONLARI
# =========================

def apply_audio_editing(audio: np.ndarray, sr: int,
                        master_volume: float = 0.65,
                        music_path: Optional[str] = None,
                        music_volume: float = 0.02,
                        pitch_shift: float = 0.0,
                        time_stretch: float = 1.0,
                        extra_duration: float = 0.0) -> Tuple[np.ndarray, int]:
    processed = audio.copy().astype(np.float32)

    if not np.isclose(time_stretch, 1.0):
        processed = librosa.effects.time_stretch(processed, rate=time_stretch)

    if not np.isclose(pitch_shift, 0.0):
        processed = librosa.effects.pitch_shift(processed, sr=sr, n_steps=pitch_shift, res_type='soxr_vhq')

    processed = librosa.util.normalize(processed)

    total_samples = len(processed) + int(extra_duration * sr)

    if music_path and os.path.exists(music_path):
        music, _ = librosa.load(music_path, sr=sr)
        music = librosa.util.normalize(music)

        if len(music) < total_samples:
            repeats = int(np.ceil(total_samples / len(music)))
            music = np.tile(music, repeats)
        music = music[:total_samples] * music_volume

        speech_padded = np.zeros(total_samples)
        speech_padded[:len(processed)] = processed

        final = speech_padded + music
    else:
        final = np.zeros(total_samples)
        final[:len(processed)] = processed

    final = final * master_volume

    max_val = np.max(np.abs(final))
    if max_val > 0.95:
        final = final * 0.95 / max_val

    return final, sr

# =========================
# WORKER'LAR
# =========================

class FilterWorker(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finishedTask = pyqtSignal(bool)

    def __init__(self, speech_path, active_profiles):
        super().__init__()
        self.speech_path = speech_path
        self.active_profiles = active_profiles 
        self.filtered_audio = None
        self.sr = None

    def run(self):
        try:
            speech, self.sr = librosa.load(self.speech_path, sr=None)
            total_profiles = len(self.active_profiles)

            if total_profiles == 0:
                self.status.emit("Aktif profil yok!")
                self.finishedTask.emit(False)
                return

            current_audio = speech.copy()

            for i, profile in enumerate(self.active_profiles):
                profile_name = profile['name']
                is_x1 = profile.get('is_x1', False)
                is_x2 = profile.get('is_x2', False)
                power = profile.get('power', 5)

                if is_x1:
                    self.status.emit(f"[{i+1}/{total_profiles}] x1 Filtresi uygulanıyor... (güç:{power})")
                    x1_denoiser = X1Denoiser(self.sr, power)
                    current_audio = x1_denoiser.process(
                        current_audio,
                        progress_callback=lambda p: self.progress.emit(p)
                    )
                    self.status.emit(f"[{i+1}/{total_profiles}] x1 tamamlandı")
                elif is_x2:
                    cutoff = profile.get('cutoff', 75)
                    self.status.emit(f"[{i+1}/{total_profiles}] x2 Uygulanıyor... (O frekanstaki bölgeleri tamamen sustur: {cutoff} Hz)")
                    x2_filter = X2Filter(self.sr, cutoff)
                    current_audio = x2_filter.process(
                        current_audio,
                        progress_callback=lambda p: self.progress.emit(p)
                    )
                    self.status.emit(f"[{i+1}/{total_profiles}] x2 tamamlandı")
                else:
                    noise_profile = profile['data']
                    self.status.emit(f"[{i+1}/{total_profiles}] {profile_name} uygulanıyor... (güç:{power})")
                    alpha = 2.0 + (power - 1) * 0.3
                    beta = 0.0001 + (power - 1) * 0.0002
                    current_audio = self._spectral_subtraction_with_progress(
                        current_audio, noise_profile,
                        lambda p: self.progress.emit(p),
                        alpha=alpha, beta=beta
                    )
                    self.status.emit(f"[{i+1}/{total_profiles}] {profile_name} tamamlandı")

            self.filtered_audio = current_audio
            self.progress.emit(100)
            self.status.emit("Tüm filtreler tamamlandı!")
            self.finishedTask.emit(True)

        except Exception as e:
            self.status.emit(f"Hata: {str(e)}")
            self.finishedTask.emit(False)

    def _spectral_subtraction_with_progress(self, speech_signal, noise_profile, progress_callback, alpha=3.0, beta=0.0001):
        progress_callback(10)
        S = stft(speech_signal)
        mag = np.abs(S)
        phase = np.angle(S)

        progress_callback(30)
        mag_power = mag ** 2
        noise_power = noise_profile ** 2

        progress_callback(50)
        subtracted_power = mag_power - (alpha * noise_power)
        subtracted_power = np.maximum(subtracted_power, beta * noise_power)
        cleaned_mag = np.sqrt(subtracted_power)

        progress_callback(70)
        cleaned_stft = cleaned_mag * np.exp(1j * phase)

        progress_callback(85)
        result = istft(cleaned_stft)

        progress_callback(100)
        return result

# =========================
# ANA UYGULAMA UI
# =========================

BUTTON_STYLE = """
    QPushButton {
        background-color: transparent;
        color: #E0E0E0;
        border: 2px solid #555;
        border-radius: 8px;
        font-weight: bold;
        font-size: 14px;
    }
    QPushButton:hover {
        background-color: #3C3C3C;
        border: 1px solid #777;
    }
    QPushButton:pressed {
        background-color: #1A1A1A;
        padding: 6px 10px 4px 10px;
    }
    QPushButton:disabled {
        background-color: #202020;
        color: #555;
        border: 1px solid #333;
    }
"""

GREY_BUTTON_STYLE = """
    QPushButton {
        background-color: #555555;
        color: #DDDDDD;
        border: 2px solid #777777;
        border-radius: 8px;
        font-weight: bold;
        font-size: 14px;
    }
    QPushButton:hover {
        background-color: #666666;
        border: 1px solid #888888;
    }
    QPushButton:pressed {
        background-color: #444444;
        padding: 6px 10px 4px 10px;
    }
    QPushButton:disabled {
        background-color: #202020;
        color: #555;
        border: 1px solid #333;
    }
"""

COMBO_STYLE = """
    QComboBox {
        background-color: #2E2E2E;
        color: white;
        font-size: 13px;
        font-weight: bold;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 4px;
    }
    QComboBox:hover {
        background-color: #3C3C3C;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 0px;
        border: none;
    }
    QComboBox::down-arrow {
        image: none;
    }
    QComboBox QAbstractItemView {
        background-color: #1F1F1F;
        border: 1px solid #444;
        selection-background-color: #444;
        color: white;
        outline: none;
    }
    QComboBox QAbstractItemView::item {
        background-color: #1F1F1F;
        color: white;
        padding: 4px;
        min-height: 24px;
    }
    QComboBox QAbstractItemView::item:selected {
        background-color: #444;
        color: white;
    }
    QComboBox QAbstractItemView::item:hover {
        background-color: #353535;
    }
"""

class AudioCleanerUI(QWidget):
    def __init__(self):
        super().__init__()
        load_x2_config()
        
        self.profile_manager = ProfileManager()
        self.speech_path = None
        self.original_audio_path = None
        self.filtered_audio = None          # Process ile oluşturulmuş nihai ses (filtre + müzik)
        self.filtered_sr = None
        self.preview_worker = None
        self.filter_worker = None
        self.is_playing = False
        self.report_history = []

        self.is_video = False
        self.original_video_path = None
        self.filtered_video_path = None
        self.temp_audio_path = None
        self.temp_dir = None

        self.edit_panel_visible = False
        self.edit_widget = None
        
        self.edit_settings = {
            'master_vol': 65,
            'music_vol': 2, 
            'pitch': 0,
            'speed': 100,
            'extra_sec': 0,
            'music_path': None
        }
        
        # Kalıcı müzik ayarını yükle
        self.persistent_music_path = load_music_config()
        if self.persistent_music_path and os.path.exists(self.persistent_music_path):
            self.edit_settings['music_path'] = self.persistent_music_path
        else:
            self.persistent_music_path = None

        self.edited_audio = None
        self.edited_sr = None

        self.init_ui()
        self.load_profile_list()

    def init_ui(self):
        self.setWindowTitle("Filter")
        self.setGeometry(200, 200, 820, 590)
        self.setMinimumSize(820, 590)
        self.setMaximumSize(1300, 900)

        icon_path = ICON_DIR / "Kavram.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setStyleSheet("""
            QWidget {
                background-color: #2E2E2E;
                color: #E0E0E0;
                font-family: 'Segoe UI', 'Ubuntu', sans-serif;
            }
            QLabel {
                color: #E0E0E0;
            }
            QListWidget {
                background-color: #1F1F1F;
                border: 1px solid #333;
                border-radius: 5px;
                padding: 5px;
                outline: none;
            }
            QListWidget::item {
                background-color: #252525;
                border-radius: 3px;
                margin: 2px;
                padding: 3px;
            }
            QListWidget::item:selected {
                background-color: #353535;
            }
            QListWidget::item:hover {
                background-color: #303030;
            }
            QProgressBar {
                background-color: #1A1A1A;
                border: 1px solid #444;
                border-radius: 5px;
                text-align: center;
                height: 20px;
                color: #CCC;
            }
            QProgressBar::chunk {
                background-color: #555;
                border-radius: 5px;
            }
            QScrollBar:vertical {
                background-color: #1A1A1A;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar:handle:vertical {
                background-color: #444;
                border-radius: 4px;
                min-height: 15px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QRadioButton {
                color: #AAA;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
            }
            QTextEdit {
                background-color: #1A1A1A;
                border: 1px solid #333;
                border-radius: 5px;
                color: #AAA;
                font-size: 12px;
                font-family: monospace;
                selection-background-color: #555;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ÜST BAR
        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(40)
        self.top_bar.setStyleSheet("background-color: #1F1F1F; border-bottom: 2px solid #555;")
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setSpacing(8)
        top_bar_layout.setContentsMargins(10, 0, 10, 0)

        self.btn_file = QPushButton("File")
        self.btn_file.setFixedSize(90, 30)
        self.btn_file.setStyleSheet(BUTTON_STYLE)
        self.btn_file.clicked.connect(self.load_speech)

        self.btn_noise = QPushButton("::")
        self.btn_noise.setFixedSize(30, 30)
        self.btn_noise.setStyleSheet(BUTTON_STYLE)
        self.btn_noise.clicked.connect(self.add_noise_profile)

        self.btn_edit = QPushButton("/")
        self.btn_edit.setFixedSize(30, 30)
        self.btn_edit.setStyleSheet(BUTTON_STYLE)
        self.btn_edit.setCheckable(True)
        self.btn_edit.clicked.connect(self.toggle_edit_panel)

        self.btn_process = QPushButton("Process")
        self.btn_process.setFixedSize(90, 30)
        self.btn_process.setStyleSheet(BUTTON_STYLE)
        self.btn_process.clicked.connect(self.start_filtering)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.setFixedSize(90, 30)
        self.btn_reset.setStyleSheet(BUTTON_STYLE)
        self.btn_reset.clicked.connect(self.reset_all_profiles)

        top_bar_layout.addWidget(self.btn_file)
        top_bar_layout.addWidget(self.btn_noise)
        top_bar_layout.addWidget(self.btn_edit)
        top_bar_layout.addWidget(self.btn_process)
        top_bar_layout.addWidget(self.btn_reset)
        top_bar_layout.addStretch()

        self.btn_play = QPushButton("Play")
        self.btn_play.setFixedSize(80, 30)
        self.btn_play.setStyleSheet(BUTTON_STYLE)
        self.btn_play.clicked.connect(self.toggle_play_pause)
        self.btn_play.setEnabled(False)
        top_bar_layout.addWidget(self.btn_play)

        self.btn_music = RightClickButton("Müzik")
        self.btn_music.setFixedSize(80, 30)
        
        if self.persistent_music_path:
            self.btn_music.setStyleSheet(GREY_BUTTON_STYLE)
        else:
            self.btn_music.setStyleSheet(BUTTON_STYLE)
            
        self.btn_music.clicked.connect(self.select_music_file_temp)
        self.btn_music.rightClicked.connect(self.select_music_file_persistent)
        top_bar_layout.addWidget(self.btn_music)

        self.btn_export = QPushButton("Export")
        self.btn_export.setFixedSize(90, 30)
        self.btn_export.setEnabled(False)
        self.btn_export.setStyleSheet(BUTTON_STYLE)
        self.btn_export.clicked.connect(self.export_file)
        top_bar_layout.addWidget(self.btn_export)

        self.top_bar.setLayout(top_bar_layout)

        # ORTA KISIM
        self.middle_widget = QWidget()
        self.middle_widget.setStyleSheet("background-color: #1F1F1F;")
        self.middle_layout = QVBoxLayout()
        self.middle_layout.setSpacing(8)
        self.middle_layout.setContentsMargins(15, 15, 15, 15)

        self.profile_list = QListWidget()
        self.profile_list.setMinimumHeight(280)
        self.profile_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.profile_list.customContextMenuRequested.connect(self.show_context_menu)

        self.middle_layout.addWidget(self.profile_list)
        self.middle_widget.setLayout(self.middle_layout)

        # ALT KISIM
        self.bottom_widget = QWidget()
        self.bottom_widget.setFixedHeight(200)
        self.bottom_widget.setStyleSheet("background-color: #1A1A1A; border-top: 1px solid #333;")
        bottom_layout = QVBoxLayout()
        bottom_layout.setSpacing(10)
        bottom_layout.setContentsMargins(15, 12, 15, 12)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        bottom_layout.addWidget(self.progress_bar)

        select_layout = QHBoxLayout()
        self.radio_original = QRadioButton("Orijinal")
        self.radio_filtered = QRadioButton("Filtrelenmis")
        self.radio_original.setChecked(True)
        select_layout.addWidget(self.radio_original)
        select_layout.addWidget(self.radio_filtered)
        select_layout.addStretch()
        bottom_layout.addLayout(select_layout)

        self.report_textedit = QTextEdit()
        self.report_textedit.setReadOnly(True)
        self.report_textedit.setMaximumHeight(100)
        bottom_layout.addWidget(self.report_textedit)

        self.bottom_widget.setLayout(bottom_layout)

        main_layout.addWidget(self.top_bar)
        main_layout.addWidget(self.middle_widget)
        main_layout.addWidget(self.bottom_widget)
        self.setLayout(main_layout)

    # =========================
    # YARDIMCI SINIFLAR
    # =========================
    class PowerComboBox(QComboBox):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.addItems([str(i) for i in range(1, 10)])
            self.setCurrentText("5")
            self.setFixedSize(40, 30)
            self.setStyleSheet(COMBO_STYLE)
            self.setFocusPolicy(Qt.StrongFocus)

        def wheelEvent(self, event: QWheelEvent):
            delta = event.angleDelta().y()
            current = int(self.currentText())
            if delta > 0:
                new_val = min(9, current + 1)
            else:
                new_val = max(1, current - 1)
            if new_val != current:
                self.setCurrentText(str(new_val))
                self.currentTextChanged.emit(self.currentText())
            event.accept()

    class FreqComboBox(QComboBox):
        def __init__(self, parent=None):
            super().__init__(parent)
            items = [str(i) for i in range(30, 201, 5)]
            self.addItems(items)
            self.setCurrentText(str(X2_PROFILE['cutoff'])) 
            self.setFixedSize(70, 30)
            self.setStyleSheet(COMBO_STYLE)
            self.setFocusPolicy(Qt.StrongFocus)

        def wheelEvent(self, event: QWheelEvent):
            delta = event.angleDelta().y()
            current = int(self.currentText())
            idx = self.findText(str(current))
            if idx >= 0:
                if delta > 0 and idx < self.count() - 1:
                    self.setCurrentIndex(idx + 1)
                elif delta < 0 and idx > 0:
                    self.setCurrentIndex(idx - 1)
            event.accept()

    # =========================
    # PROFİL LİSTESİ OLUŞTURMA
    # =========================
    def create_profile_widget(self, profile_data, is_x1=False, is_x2=False):
        widget = QFrame()
        widget.setStyleSheet("QFrame { background-color: transparent; }")

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(8)

        profile_id = profile_data['id']
        is_active = profile_data.get('active', False)

        toggle_btn = QPushButton()
        toggle_btn.setFixedSize(20, 20)
        toggle_btn.setCheckable(True)
        toggle_btn.setChecked(is_active)
        toggle_btn.setProperty("profile_id", profile_id)

        if is_active:
            toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #555;
                    border: 2px solid #666;
                    border-radius: 10px;
                    color: #AAA;
                    font-size: 15px;
                    font-weight: bold;
                    text-align: center;
                    padding-bottom: 2px;
                    outline: none;
                }
                QPushButton:hover { background-color: #606060; }
            """)
            toggle_btn.setText("●")
        else:
            toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #444;
                    border: 2px solid #555;
                    border-radius: 10px;
                    color: transparent;
                }
                QPushButton:hover { background-color: #505050; }
            """)
            toggle_btn.setText("")

        toggle_btn.clicked.connect(lambda checked, pid=profile_id: self.on_toggle_clicked(pid, checked))

        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)

        if is_x1:
            name_label = QLabel("x1")
            name_label.setStyleSheet("color: #CCC; font-weight: bold; font-size: 14px;")
            desc_label = QLabel("2 Aşamalı Spektral")
            desc_label.setStyleSheet("color: #888; font-size: 11px;")
            info_layout.addWidget(name_label)
            info_layout.addWidget(desc_label)
        elif is_x2:
            name_label = QLabel("x2")
            name_label.setStyleSheet("color: #CCC; font-weight: bold; font-size: 14px;")
            desc_label = QLabel(f"Sadece O Frekanstaki Bölgeleri Tamamen Sustur ({profile_data.get('cutoff',75)} Hz)")
            desc_label.setStyleSheet("color: #888; font-size: 11px;")
            info_layout.addWidget(name_label)
            info_layout.addWidget(desc_label)
        else:
            source_file = profile_data.get('source_file', 'Bilinmiyor')
            name_label = QLabel(profile_data['name'])
            name_label.setStyleSheet("color: #E0E0E0; font-weight: bold; font-size: 14px;")
            file_label = QLabel(f"Kaynak: {source_file}")
            file_label.setStyleSheet("color: #888; font-size: 11px;")
            info_layout.addWidget(name_label)
            info_layout.addWidget(file_label)

        layout.addWidget(toggle_btn)
        layout.addLayout(info_layout)
        layout.addStretch()

        if is_x1:
            power_combo = self.PowerComboBox()
            power_combo.setCurrentText(str(profile_data.get('power', 5)))
            power_combo.setProperty("profile_id", profile_id)
            power_combo.currentTextChanged.connect(lambda val, pid=profile_id: self.on_power_changed(pid, int(val)))
            layout.addWidget(power_combo)
        elif is_x2:
            freq_combo = self.FreqComboBox()
            freq_combo.setProperty("profile_id", profile_id)
            freq_combo.currentTextChanged.connect(lambda val, pid=profile_id: self.on_x2_cutoff_changed(pid, int(val)))
            layout.addWidget(freq_combo)
        else:
            power_combo = self.PowerComboBox()
            power_combo.setCurrentText(str(profile_data.get('power', 5)))
            power_combo.setProperty("profile_id", profile_id)
            power_combo.currentTextChanged.connect(lambda val, pid=profile_id: self.on_power_changed(pid, int(val)))
            layout.addWidget(power_combo)

        widget.setLayout(layout)
        return widget

    def on_power_changed(self, profile_id, value):
        self.profile_manager.set_power(profile_id, value)

    def on_x2_cutoff_changed(self, profile_id, value):
        if profile_id == 'x2_filter':
            self.profile_manager.set_x2_cutoff(value)  
            self.load_profile_list()  
            self.log_report(f"x2 kesme frekansı {value} Hz olarak ayarlandı (kalıcı)")

    def on_toggle_clicked(self, profile_id, checked):
        self.profile_manager.set_active(profile_id, checked)
        self.load_profile_list()

    def load_profile_list(self):
        self.profile_list.clear()
        x1_item = QListWidgetItem()
        x1_item.setData(Qt.UserRole, 'x1_filter')
        x1_widget = self.create_profile_widget(X1_PROFILE, is_x1=True)
        self.profile_list.addItem(x1_item)
        x1_item.setSizeHint(QSize(0, 55))
        self.profile_list.setItemWidget(x1_item, x1_widget)

        for profile in self.profile_manager.profiles:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, profile['id'])
            widget = self.create_profile_widget(profile, is_x1=False, is_x2=False)
            self.profile_list.addItem(item)
            item.setSizeHint(QSize(0, 55))
            self.profile_list.setItemWidget(item, widget)

        x2_item = QListWidgetItem()
        x2_item.setData(Qt.UserRole, 'x2_filter')
        x2_widget = self.create_profile_widget(X2_PROFILE, is_x2=True)
        self.profile_list.addItem(x2_item)
        x2_item.setSizeHint(QSize(0, 55))
        self.profile_list.setItemWidget(x2_item, x2_widget)

    def show_context_menu(self, pos):
        item = self.profile_list.itemAt(pos)
        if not item:
            return
        profile_id = item.data(Qt.UserRole)
        if profile_id in ('x1_filter', 'x2_filter'):
            return
        profile_name = ""
        for p in self.profile_manager.profiles:
            if p['id'] == profile_id:
                profile_name = p['name']
                break
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #252525; color: #E0E0E0; border: 1px solid #444; padding: 5px; }
            QMenu::item { padding: 8px 20px; border-radius: 3px; }
            QMenu::item:selected { background-color: #3A3A3A; }
        """)
        delete_action = menu.addAction("Sil")
        delete_action.triggered.connect(lambda: self.delete_profile(profile_id, profile_name))
        menu.exec_(self.profile_list.mapToGlobal(pos))

    def delete_profile(self, profile_id, profile_name):
        reply = QMessageBox.question(self, 'Profili Sil', f'"{profile_name}" profili silinecek. Emin misiniz?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.profile_manager.remove_profile(profile_id)
            self.load_profile_list()
            self.log_report(f"Profil silindi: {profile_name}")

    def add_noise_profile(self):
        if self.profile_manager.get_profile_count() >= MAX_PROFILES:
            QMessageBox.warning(self, "Sinir Asildi", f"Maksimum {MAX_PROFILES} profil ekleyebilirsiniz.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Gurultu Dosyasi Sec", str(DEFAULT_EXPORT_DIR),
                                               filter="Audio Files (*.wav *.mp3 *.flac *.ogg)")
        if not path:
            return
        try:
            noise_data, sr = librosa.load(path, sr=None)
            noise_profile = estimate_noise(noise_data)
            base_name = os.path.splitext(os.path.basename(path))[0]
            timestamp = datetime.now().strftime("%H%M%S")
            profile_name = f"{base_name}_{timestamp}"
            success, message = self.profile_manager.add_profile(profile_name, noise_profile, os.path.basename(path))
            if success:
                self.load_profile_list()
                self.log_report(f"Yeni profil: {profile_name}")
            else:
                QMessageBox.warning(self, "Hata", message)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya yuklenemedi:\n{str(e)}")

    # =========================
    # SES / VİDEO YÜKLEME
    # =========================
    def load_speech(self):
        if self.filter_worker and self.filter_worker.isRunning():
            self.filter_worker.terminate()
            self.filter_worker.wait()
            self.filter_worker = None
            self.btn_process.setEnabled(True)
            self.progress_bar.setValue(0)
            self.log_report("Önceki işlem iptal edildi ve yeni dosya yükleniyor.")

        video_filter = "Video Files (" + " ".join(f"*{ext}" for ext in VIDEO_EXTENSIONS) + ")"
        audio_filter = "Audio Files (" + " ".join(f"*{ext}" for ext in AUDIO_EXTENSIONS) + ")"
        all_filter = "All Supported (" + " ".join(f"*{ext}" for ext in AUDIO_EXTENSIONS + VIDEO_EXTENSIONS) + ")"
        filter_str = f"{all_filter};;{audio_filter};;{video_filter};;All Files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Medya Dosyasi Sec", str(DEFAULT_EXPORT_DIR), filter=filter_str)
        if not path:
            return
        
        self.filtered_audio = None
        self.filtered_sr = None
        self.filtered_video_path = None
        self.edited_audio = None
        
        self.radio_original.setChecked(True)
        
        self.btn_export.setEnabled(False)
        self.btn_play.setEnabled(False)
        self.stop_audio()
        
        ext = os.path.splitext(path)[1].lower()
        if ext in VIDEO_EXTENSIONS:
            self.is_video = True
            self.original_video_path = path
            self.log_report(f"Video yüklendi: {os.path.basename(path)}")
            if not self._check_ffmpeg():
                QMessageBox.warning(self, "FFmpeg Gerekli", 
                    f"Video işlemek için '{FFMPEG_PATH}' dosyası bulunamadı veya çalıştırılamıyor.\n\n"
                    "Lütfen uygulama dizininde 'bin/ffmpeg' olduğundan emin olun.")
                return
            self.temp_dir = tempfile.mkdtemp(prefix="filtre_video_")
            self.temp_audio_path = os.path.join(self.temp_dir, "extracted_audio.wav")
            success = self._extract_audio_from_video(path, self.temp_audio_path)
            if not success:
                QMessageBox.critical(self, "Hata", "Ses çıkarılamadı.")
                self._cleanup_temp()
                return
            self.speech_path = self.temp_audio_path
            self.original_audio_path = self.temp_audio_path
        else:
            self.is_video = False
            self.original_video_path = None
            self.speech_path = path
            self.original_audio_path = path
            self.log_report(f"Ses yüklendi: {os.path.basename(path)}")
        
        self.btn_play.setEnabled(True)

    def _check_ffmpeg(self):
        if os.path.exists(FFMPEG_PATH) and os.access(FFMPEG_PATH, os.X_OK):
            return True
        self.log_report(f"FFmpeg bulunamadı veya çalıştırılamıyor: {FFMPEG_PATH}")
        return False

    def _extract_audio_from_video(self, video_path, output_wav_path):
        cmd = [FFMPEG_PATH, "-i", video_path, "-vn", "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "1", "-y", output_wav_path]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def _replace_audio_in_video(self, video_path, audio_wav_path, output_video_path):
        cmd = [FFMPEG_PATH, "-i", video_path, "-i", audio_wav_path, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-map", "0:v:0", "-map", "1:a:0", "-shortest", "-y", output_video_path]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def _cleanup_temp(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass
        self.temp_dir = None
        self.temp_audio_path = None

    # =========================
    # FİLTRELEME İŞLEMİ
    # =========================
    def start_filtering(self):
        active_profiles = self.profile_manager.get_active_profiles()
        if X2_PROFILE['active']:
            active_profiles.append({
                'id': 'x2_filter',
                'name': 'x2',
                'is_x2': True,
                'cutoff': X2_PROFILE['cutoff']
            })

        if not active_profiles:
            QMessageBox.warning(self, "Profil Secilmedi", "En az bir filtreyi aktif edin.")
            return
        if not self.speech_path:
            QMessageBox.warning(self, "Medya Dosyasi Secilmedi", "Lutfen once bir dosya secin.")
            return
            
        self.btn_process.setEnabled(False)
        self.btn_export.setEnabled(False)
        self.progress_bar.setValue(0)
        self.filtered_audio = None
        self.filtered_video_path = None
        self.edited_audio = None
        self.filter_worker = FilterWorker(self.speech_path, active_profiles)
        self.filter_worker.progress.connect(self.progress_bar.setValue)
        self.filter_worker.status.connect(self.on_filter_status)
        self.filter_worker.finishedTask.connect(self.on_filtering_finished)
        self.filter_worker.start()

    def on_filter_status(self, msg):
        pass

    def on_filtering_finished(self, success):
        self.btn_process.setEnabled(True)
        if success and self.filter_worker.filtered_audio is not None:
            filtered = self.filter_worker.filtered_audio
            sr = self.filter_worker.sr
            
            music_path = self.edit_settings.get('music_path')
            if music_path and os.path.exists(music_path):
                music_vol = self.edit_settings['music_vol'] / 100.0
                self.filtered_audio, self.filtered_sr = apply_audio_editing(
                    filtered, sr,
                    master_volume=1.0,
                    music_path=music_path,
                    music_volume=music_vol,
                    pitch_shift=0,
                    time_stretch=1,
                    extra_duration=0
                )
                self.log_report(f"Müzik eklendi: {os.path.basename(music_path)} (şiddet: {self.edit_settings['music_vol']}%)")
            else:
                self.filtered_audio = filtered
                self.filtered_sr = sr
            
            self.radio_filtered.setChecked(True)
            
            if self.is_video and self.original_video_path:
                temp_filtered_wav = os.path.join(self.temp_dir, "filtered_audio.wav")
                try:
                    sf.write(temp_filtered_wav, self.filtered_audio, self.filtered_sr)
                    
                    # Güncelleme: Videoyu doğrudan orijinal klasöre kaydetmek yerine temp'te beklet
                    orig_filename = os.path.basename(self.original_video_path)
                    base, ext = os.path.splitext(orig_filename)
                    output_video = os.path.join(self.temp_dir, f"temp_{base}{ext}")
                    
                    if self._replace_audio_in_video(self.original_video_path, temp_filtered_wav, output_video):
                        self.filtered_video_path = output_video
                        self.log_report(f"Video işlendi. Dışa aktarmak için Export'a tıklayın.")
                        self.btn_export.setEnabled(True)
                    else:
                        self.log_report("Video birleştirme hatası")
                except Exception as e:
                    self.log_report(f"Hata: {str(e)}")
            else:
                self.btn_export.setEnabled(True)
                self.log_report("Filtreleme tamamlandi")
        else:
            self.log_report("Filtreleme basarisiz")

    def reset_all_profiles(self):
        if self.edit_panel_visible:
            self.edit_settings = {
                'master_vol': 65,
                'music_vol': 2,
                'pitch': 0,
                'speed': 100,
                'extra_sec': 0,
                'music_path': self.persistent_music_path if self.persistent_music_path else None
            }
            self.sync_edit_combos()
            self.edited_audio = None
            self.log_report("Düzenleme ayarları sıfırlandı")
        else:
            self.profile_manager.reset_all() 
            self.load_profile_list()
            self.log_report("Tüm profiller varsayılana döndürüldü (x1 güç=5, x2 kesim=75 Hz)")

    # =========================
    # DÜZENLEME PANELİ
    # =========================
    def toggle_edit_panel(self):
        if not self.edit_panel_visible:
            self.edit_panel_visible = True
            self.btn_edit.setChecked(True)
            self.profile_list.hide()
            if self.edit_widget is None:
                self.create_edit_panel()
            self.middle_layout.addWidget(self.edit_widget)
            self.edit_widget.show()
        else:
            self.edit_panel_visible = False
            self.btn_edit.setChecked(False)
            if self.edit_widget:
                self.edit_widget.hide()
                self.middle_layout.removeWidget(self.edit_widget)
            self.profile_list.show()

    def create_edit_panel(self):
        self.edit_widget = QWidget()
        self.edit_widget.setStyleSheet("background-color: #1F1F1F;")
        layout = QVBoxLayout(self.edit_widget)
        layout.setSpacing(8)
        layout.setContentsMargins(5, 5, 5, 5)

        master_widget = self.create_edit_row("GENEL SES YÜKSEKLİĞİ")
        self.combo_master = self.create_edit_combo([f"{i}%" for i in range(0, 101, 5)], f"{self.edit_settings['master_vol']}%")
        master_widget.layout().addWidget(self.combo_master)
        layout.addWidget(master_widget)

        music_widget = self.create_edit_row("ARKA PLAN MÜZİK ŞİDDETİ")
        self.combo_music_vol = self.create_edit_combo([f"{i}%" for i in range(0, 21)], f"{self.edit_settings['music_vol']}%")
        music_widget.layout().addWidget(self.combo_music_vol)
        layout.addWidget(music_widget)

        pitch_widget = self.create_edit_row("SES TONU (KALINLIK/İNCELİK)")
        pitch_values = [f"{i} semiton" for i in range(-12, 13)]
        self.combo_pitch = self.create_edit_combo(pitch_values, f"{self.edit_settings['pitch']} semiton")
        pitch_widget.layout().addWidget(self.combo_pitch)
        layout.addWidget(pitch_widget)

        speed_widget = self.create_edit_row("OYNATMA HIZI")
        speed_values = [f"{i/100:.2f}x" for i in range(50, 201, 5)]
        self.combo_speed = self.create_edit_combo(speed_values, f"{self.edit_settings['speed']/100:.2f}x")
        speed_widget.layout().addWidget(self.combo_speed)
        layout.addWidget(speed_widget)

        extra_widget = self.create_edit_row("BİTİŞTEN SONRA MÜZİK SÜRESİ")
        self.combo_extra = self.create_edit_combo([f"{i} s" for i in range(0, 31)], f"{self.edit_settings['extra_sec']} s")
        extra_widget.layout().addWidget(self.combo_extra)
        layout.addWidget(extra_widget)

        layout.addStretch()

    def create_edit_row(self, label_text):
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border-radius: 3px;
                margin: 2px;
                padding: 3px;
            }
            QFrame:hover {
                background-color: #303030;
            }
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(8)

        label = QLabel(label_text)
        label.setStyleSheet("color: #E0E0E0; font-weight: bold; font-size: 14px;")
        layout.addWidget(label)
        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def create_edit_combo(self, items, default_text):
        combo = QComboBox()
        combo.addItems(items)
        combo.setCurrentText(default_text)
        combo.setFixedWidth(120)
        combo.setStyleSheet(COMBO_STYLE)
        combo.currentTextChanged.connect(self.on_edit_combo_changed)
        return combo

    def on_edit_combo_changed(self, text):
        sender = self.sender()
        if sender == self.combo_master:
            val = int(text.rstrip('%'))
            self.edit_settings['master_vol'] = val
        elif sender == self.combo_music_vol:
            val = int(text.rstrip('%'))
            self.edit_settings['music_vol'] = val
            if self.filtered_audio is not None:
                self.log_report("Müzik şiddeti değişti. Değişikliklerin etkili olması için Process'e tekrar basın.")
        elif sender == self.combo_pitch:
            val = int(text.split()[0])
            self.edit_settings['pitch'] = val
        elif sender == self.combo_speed:
            val = float(text.rstrip('x'))
            self.edit_settings['speed'] = int(val * 100)
        elif sender == self.combo_extra:
            val = int(text.rstrip(' s'))
            self.edit_settings['extra_sec'] = val
        self.edited_audio = None

    def sync_edit_combos(self):
        if hasattr(self, 'combo_master'):
            self.combo_master.setCurrentText(f"{self.edit_settings['master_vol']}%")
            self.combo_music_vol.setCurrentText(f"{self.edit_settings['music_vol']}%")
            self.combo_pitch.setCurrentText(f"{self.edit_settings['pitch']} semiton")
            self.combo_speed.setCurrentText(f"{self.edit_settings['speed']/100:.2f}x")
            self.combo_extra.setCurrentText(f"{self.edit_settings['extra_sec']} s")

    def select_music_file_temp(self):
        path, _ = QFileDialog.getOpenFileName(self, "Arka Plan Müziği Seç", str(DEFAULT_EXPORT_DIR),
                                              filter="Audio Files (*.wav *.mp3 *.flac *.ogg)")
        if path:
            self.edit_settings['music_path'] = path
            self.edited_audio = None
            self.btn_music.setStyleSheet(BUTTON_STYLE)
            self.log_report(f"Müzik seçildi (Geçici): {os.path.basename(path)} (Sağ tık ile kalıcı yapabilirsiniz)")

    def select_music_file_persistent(self):
        if self.persistent_music_path:
            self.persistent_music_path = None
            save_music_config(None) 
            self.btn_music.setStyleSheet(BUTTON_STYLE)
            self.log_report("Kalıcı müzik iptal edildi. (Mevcut müzik sadece bu seferlik kullanılacak)")
            return

        path = self.edit_settings.get('music_path')
        if not path or not os.path.exists(path):
            self.log_report("Önce sol tıklayarak bir müzik dosyası seçmelisiniz!")
            return

        try:
            for f in PROFILES_DIR.glob("kalici_muzik.*"):
                if f.is_file():
                    try:
                        f.unlink()
                    except Exception:
                        pass
            
            if path != self.persistent_music_path:
                ext = os.path.splitext(path)[1]
                dest_path = PROFILES_DIR / f"kalici_muzik{ext}"
                shutil.copy2(path, dest_path)
                
                self.persistent_music_path = str(dest_path)
                self.edit_settings['music_path'] = self.persistent_music_path
                save_music_config(self.persistent_music_path)
            
            self.btn_music.setStyleSheet(GREY_BUTTON_STYLE)
            self.edited_audio = None
            self.log_report(f"Seçili müzik kalıcı hale getirildi: {os.path.basename(self.persistent_music_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kalıcı müzik ayarlanamadı:\n{str(e)}")

    def get_edited_audio(self):
        if self.filtered_audio is None or self.filtered_sr is None:
            return None, None
        if self.edited_audio is not None:
            return self.edited_audio, self.edited_sr

        master = self.edit_settings['master_vol'] / 100.0
        pitch = self.edit_settings['pitch']
        speed = self.edit_settings['speed'] / 100.0
        extra = float(self.edit_settings['extra_sec'])
        
        edited, sr = apply_audio_editing(
            self.filtered_audio, self.filtered_sr,
            master_volume=master,
            music_path=None,
            music_volume=0,
            pitch_shift=pitch,
            time_stretch=speed,
            extra_duration=extra
        )
        self.edited_audio = edited
        self.edited_sr = sr
        return edited, sr

    # =========================
    # OYNATMA
    # =========================
    def toggle_play_pause(self):
        if self.is_playing:
            self.stop_audio()
        else:
            self.start_preview()

    def start_preview(self):
        self.stop_audio()
        try:
            if self.edit_panel_visible:
                edited, sr = self.get_edited_audio()
                if edited is None:
                    QMessageBox.warning(self, "Filtrelenmiş Ses Yok", "Önce bir dosya yükleyip Process ile filtreleyin.")
                    return
                audio_array = edited
                sr_used = sr
            else:
                if self.radio_filtered.isChecked() and self.filtered_audio is not None:
                    audio_array = self.filtered_audio
                    sr_used = self.filtered_sr
                elif self.original_audio_path is not None and os.path.exists(self.original_audio_path):
                    audio_array, sr_used = librosa.load(self.original_audio_path, sr=None, mono=False)
                    if audio_array.ndim > 1:
                        audio_array = audio_array[0]
                else:
                    self.log_report("Oynatılacak ses bulunamadı")
                    return

            self.is_playing = True
            self.btn_play.setText("Pause")
            
            if len(audio_array.shape) == 1:
                audio_stereo = np.column_stack((audio_array, audio_array))
            else:
                audio_stereo = audio_array
            samples_to_take = int(sr_used * 5)
            audio_to_play = audio_stereo[:samples_to_take]
            fade_samples = int(sr_used * 0.1)
            if len(audio_to_play) > fade_samples * 2:
                fade_in = np.linspace(0, 1, fade_samples)
                fade_out = np.linspace(1, 0, fade_samples)
                audio_to_play[:fade_samples, 0] *= fade_in
                audio_to_play[:fade_samples, 1] *= fade_in
                audio_to_play[-fade_samples:, 0] *= fade_out
                audio_to_play[-fade_samples:, 1] *= fade_out
            sd.play(audio_to_play, sr_used)
            self.play_timer = QTimer()
            self.play_timer.timeout.connect(self.check_playback_status)
            self.play_timer.start(100)
        except Exception as e:
            self.is_playing = False
            self.btn_play.setText("Play")
            self.log_report(f"Oynatma hatası: {str(e)}")
            QMessageBox.warning(self, "Oynatma Hatası", f"Ses oynatılırken hata oluştu:\n{str(e)}")

    def check_playback_status(self):
        try:
            if not sd.get_stream().active:
                self.stop_audio()
        except:
            pass

    def stop_audio(self):
        sd.stop()
        self.is_playing = False
        self.btn_play.setText("Play")
        if hasattr(self, 'play_timer'):
            self.play_timer.stop()
            delattr(self, 'play_timer')

    # =========================
    # EXPORT (YENİ SİSTEM)
    # =========================
    def export_file(self):
        # Orijinal dosyanın adını ve uzantısını tespit et
        original_path = self.original_video_path if self.is_video else self.original_audio_path
        if original_path:
            orig_name = os.path.basename(original_path)
            orig_base, orig_ext = os.path.splitext(orig_name)
        else:
            orig_base = "isimsiz_dosya"
            orig_ext = ".wav"
            
        # Kullanıcının dilerse tamamen değiştirebileceği, orijinal formata uygun bir ön isim oluştur.
        default_name = f"{orig_base}_F1{orig_ext}"
        default_path = DEFAULT_EXPORT_DIR / default_name

        # 1. Video Dışa Aktarma
        if self.is_video and self.filtered_video_path and os.path.exists(self.filtered_video_path):
            filter_str = f"Video Dosyası (*{orig_ext});;Tüm Dosyalar (*)"
            path, _ = QFileDialog.getSaveFileName(self, "Filtrelenmiş Videoyu Kaydet", str(default_path), filter=filter_str)
            
            if path:
                if not path.lower().endswith(orig_ext.lower()):
                    path += orig_ext
                try:
                    # Videoyu temp klasöründen kullanıcının seçtiği kalıcı yere aktar
                    shutil.copy2(self.filtered_video_path, path)
                    self.log_report(f"Video başarıyla kaydedildi: {os.path.basename(path)}")
                    QMessageBox.information(self, "Başarılı", f"Filtrelenmiş video kaydedildi:\n{path}")
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"Video kaydetme başarısız:\n{e}")
            return
            
        # 2. Ses Dışa Aktarma (Edit Paneli VEYA Normal Filtreleme)
        audio_to_save = None
        sr_to_save = None
        
        if self.edit_panel_visible:
            edited, sr = self.get_edited_audio()
            if edited is None:
                QMessageBox.warning(self, "Filtrelenmiş Ses Yok", "Önce bir dosya yükleyip Process ile filtreleyin.")
                return
            audio_to_save, sr_to_save = edited, sr
        else:
            if self.filtered_audio is None:
                QMessageBox.warning(self, "Ses Yok", "Önce bir dosya yükleyip Process ile filtreleyin.")
                return
            audio_to_save, sr_to_save = self.filtered_audio, self.filtered_sr
            
        if audio_to_save is not None and sr_to_save is not None:
            # Orijinal uzantıyı, WAV ve diğer ses formatlarını pencerede hazırla
            filter_str = f"Ses Dosyası (*{orig_ext});;WAV Dosyası (*.wav);;MP3 Dosyası (*.mp3);;FLAC Dosyası (*.flac)"
            path, _ = QFileDialog.getSaveFileName(self, "Sesi Kaydet", str(default_path), filter=filter_str)
            
            if path:
                ext = os.path.splitext(path)[1].lower()
                if not ext:
                    path += orig_ext
                    ext = orig_ext.lower()
                
                try:
                    if ext in ['.wav', '.flac', '.ogg']:
                        sf.write(path, audio_to_save, sr_to_save)
                    else:
                        # Eğer kullanıcı orjinal .mp3 vb istiyorsa ffmpeg ile sorunsuz çevrim yap
                        temp_dir = self.temp_dir if self.temp_dir else tempfile.gettempdir()
                        temp_wav = os.path.join(temp_dir, f"temp_export_{datetime.now().strftime('%H%M%S')}.wav")
                        sf.write(temp_wav, audio_to_save, sr_to_save)
                        cmd = [FFMPEG_PATH, "-y", "-i", temp_wav, path]
                        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if os.path.exists(temp_wav):
                            os.remove(temp_wav)
                            
                    self.log_report(f"Ses başarıyla kaydedildi: {os.path.basename(path)}")
                    QMessageBox.information(self, "Başarılı", f"Ses dosyası kaydedildi:\n{path}")
                except Exception as e:
                    QMessageBox.critical(self, "Hata", f"Kaydetme başarısız:\n{e}")

    # =========================
    # RAPOR
    # =========================
    def log_report(self, text):
        self.report_history.insert(0, text)
        if len(self.report_history) > MAX_REPORT_LINES:
            self.report_history = self.report_history[:MAX_REPORT_LINES]
        report_text = "\n".join(self.report_history)
        self.report_textedit.setPlainText(report_text)
        cursor = self.report_textedit.textCursor()
        cursor.movePosition(cursor.Start)
        self.report_textedit.setTextCursor(cursor)
        try:
            log_file = PROFILES_DIR / "log.txt"
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}\n")
        except IOError:
            pass

    # =========================
    # HARİCİ BAĞLANTI
    # =========================
    def process_audio_background(self, audio_path, callback=None):
        file_name = os.path.basename(audio_path)
        self.log_report(f"Harici bağlantı: {file_name} filtreleniyor...")

        active_profiles = self.profile_manager.get_active_profiles()
        if X2_PROFILE['active']:
            active_profiles.append({
                'id': 'x2_filter',
                'name': 'x2',
                'is_x2': True,
                'cutoff': X2_PROFILE['cutoff']
            })

        if not active_profiles:
            self.log_report(f"Hata: {file_name} - Aktif filtre yok")
            if callback:
                callback(False, None, "Aktif filtre yok")
            return False

        if not os.path.exists(audio_path):
            self.log_report(f"Hata: {file_name} - Dosya bulunamadı")
            if callback:
                callback(False, None, "Dosya bulunamadı")
            return False

        base_name = os.path.splitext(audio_path)[0]
        output_path = f"{base_name}_filtered.wav"

        try:
            speech, sr = librosa.load(audio_path, sr=None)
            current_audio = speech.copy()

            for profile in active_profiles:
                is_x1 = profile.get('is_x1', False)
                is_x2 = profile.get('is_x2', False)
                power = profile.get('power', 5)

                if is_x1:
                    x1_denoiser = X1Denoiser(sr, power)
                    current_audio = x1_denoiser.process(current_audio, progress_callback=None)
                elif is_x2:
                    cutoff = profile.get('cutoff', 75)
                    x2_filter = X2Filter(sr, cutoff)
                    current_audio = x2_filter.process(current_audio, progress_callback=None)
                else:
                    noise_profile = profile['data']
                    alpha = 2.0 + (power - 1) * 0.3
                    beta = 0.0001 + (power - 1) * 0.0002
                    current_audio = self._spectral_subtraction_simple(current_audio, noise_profile, alpha, beta)

            sf.write(output_path, current_audio, sr)
            self.log_report(f"{file_name} filtrelendi -> {os.path.basename(output_path)}")
            if callback:
                callback(True, output_path, "Filtreleme tamamlandı")
            return True

        except Exception as e:
            error_msg = str(e)
            self.log_report(f"Hata: {file_name} - {error_msg}")
            if callback:
                callback(False, None, error_msg)
            return False

    def _spectral_subtraction_simple(self, speech_signal, noise_profile, alpha=3.0, beta=0.0001):
        S = stft(speech_signal)
        mag = np.abs(S)
        phase = np.angle(S)

        mag_power = mag ** 2
        noise_power = noise_profile ** 2

        subtracted_power = mag_power - (alpha * noise_power)
        subtracted_power = np.maximum(subtracted_power, beta * noise_power)
        cleaned_mag = np.sqrt(subtracted_power)

        cleaned_stft = cleaned_mag * np.exp(1j * phase)
        return istft(cleaned_stft)

    def closeEvent(self, event):
        self._cleanup_temp()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = AudioCleanerUI()
    window.show()
    sys.exit(app.exec_())
