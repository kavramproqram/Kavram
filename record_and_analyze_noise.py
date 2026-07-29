import pyaudio
import wave
import numpy as np
import librosa

# Kayıt ayarları
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 3
WAVE_OUTPUT_FILENAME = "background_noise.wav"

# Ses kaydı fonksiyonu
def record_audio():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    print("Kayıt başlıyor...")
    frames = []
    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
    print("Kayıt tamamlandı.")
    stream.stop_stream()
    stream.close()
    p.terminate()
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

# Gürültü analizi fonksiyonu
def analyze_noise():
    y, sr = librosa.load(WAVE_OUTPUT_FILENAME, sr=RATE)
    rms = librosa.feature.rms(y=y)[0]
    mean_rms = np.mean(rms)
    print(f"Ortalama RMS (gürültü seviyesi): {mean_rms}")

if __name__ == "__main__":
    record_audio()
    analyze_noise()
