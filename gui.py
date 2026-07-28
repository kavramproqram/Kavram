# Kavram 1.0.0
# Copyright (C) 2025-09-01 Kavram or Contributors
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
# Kavram 1.0.0
# Copyright (C) 2025-09-01 Kavram veya Contributors
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

# gui.py
import sys
import os
import ctypes
import cv2
from PyQt5.QtWidgets import QApplication, QMainWindow, QToolBar, QPushButton, QLabel, QVBoxLayout, QWidget
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer

LIB_PATH = "./librecord.so"
SAVE_DIR = "/home/takyon/İndirilenler/Kavram/medya_cut/"

class RecorderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kavram")

        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        self.camera_btn = QPushButton("Camera")
        self.sound_btn = QPushButton("Sound")
        self.toolbar.addWidget(self.camera_btn)
        self.toolbar.addWidget(self.sound_btn)

        self.preview = QLabel()
        self.preview.setFixedHeight(360)
        self.preview.setStyleSheet("background-color: black")

        central = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.preview)
        central.setLayout(layout)
        self.setCentralWidget(central)

        self.audio = ctypes.CDLL(LIB_PATH)
        self.audio.init_audio()

        self.sound_recording = False
        self.cam_recording = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)

        self.camera_btn.clicked.connect(self.toggle_camera)
        self.sound_btn.clicked.connect(self.toggle_sound)

    def toggle_sound(self):
        path = os.path.join(SAVE_DIR, "only_audio.wav").encode("utf-8")
        if not self.sound_recording:
            self.audio.record_wav(path)
            self.sound_btn.setText("Stop Sound")
        else:
            self.audio.stop_wav()
            self.sound_btn.setText("Sound")
        self.sound_recording = not self.sound_recording

    def toggle_camera(self):
        if not self.cam_recording:
            self.cap = cv2.VideoCapture(0)
            self.video_path = os.path.join(SAVE_DIR, "video.mp4")
            self.audio_path = os.path.join(SAVE_DIR, "video_audio.wav").encode("utf-8")
            self.output_path = os.path.join(SAVE_DIR, "merged_output.mp4")
            self.writer = cv2.VideoWriter(self.video_path, cv2.VideoWriter_fourcc(*'mp4v'), 20.0, (640, 480))
            self.audio.record_wav(self.audio_path)
            self.timer.start(30)
            self.camera_btn.setText("Stop Camera")
        else:
            self.timer.stop()
            self.audio.stop_wav()
            self.cap.release()
            self.writer.release()
            cv2.destroyAllWindows()
            os.system(f"ffmpeg -y -i {self.video_path} -i {SAVE_DIR}video_audio.wav -c:v copy -c:a aac {self.output_path}")
            self.camera_btn.setText("Camera")
        self.cam_recording = not self.cam_recording

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            self.writer.write(frame)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            self.preview.setPixmap(QPixmap.fromImage(img))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = RecorderApp()
    win.show()
    sys.exit(app.exec_())

