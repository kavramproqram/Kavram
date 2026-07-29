import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                             QLabel, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

class RecWindow(QWidget):
    def __init__(self):
        super().__init__()
        # Başlangıç durumu: Paused (Duraklatılmış/Başlamamış)
        self.is_running = False 
        self.seconds = 0
        self.segments = 1
        
        self.init_ui()

    def init_ui(self):
        # Pencere Ayarları
        self.setWindowTitle("Rec")
        self.setFixedWidth(140)  # Küçük ve dikey pencere
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool) # Her zaman üstte
        
        # Gri Tema Stil Sayfası (Kullanıcı tercihi: Tasarım birebir korundu)
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #e0e0e0;
                font-family: 'Segoe UI', Arial;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
                font-weight: bold;
                margin-bottom: 2px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
                border: 1px solid #777;
            }
            QPushButton:pressed {
                background-color: #222;
            }
            QLabel {
                font-size: 11px;
                color: #aaa;
                padding: 2px;
            }
            .info-label {
                background-color: #1e1e1e;
                border-radius: 3px;
                color: #00ff00;
                font-family: 'Courier New';
                font-weight: bold;
                margin-top: 2px;
            }
        """)

        # Ana Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)

        # 4 Buton (Alt alta)
        self.btn_sound = QPushButton("Sound")
        self.btn_windows = QPushButton("Windows")
        
        # GÜNCELLEME: Kendiliğinden çalışmaması için başlangıç metni "Play" yapıldı
        self.btn_play_pause = QPushButton("Play") 
        
        self.btn_export = QPushButton("Export")

        # Buton Fonksiyonları
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)

        layout.addWidget(self.btn_sound)
        layout.addWidget(self.btn_windows)
        layout.addWidget(self.btn_play_pause)
        layout.addWidget(self.btn_export)

        # Ayırıcı Çizgi
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #444;")
        layout.addWidget(line)

        # Bilgi Göstergeleri (Alt alta 2 gösterge)
        self.lbl_time = QLabel("00:00:00")
        self.lbl_time.setAlignment(Qt.AlignCenter)
        self.lbl_time.setProperty("class", "info-label")
        self.lbl_time.setStyleSheet("background-color: #1e1e1e; color: #00ff00; padding: 5px;")

        self.lbl_segments = QLabel("Segments: 1")
        self.lbl_segments.setAlignment(Qt.AlignCenter)
        self.lbl_segments.setProperty("class", "info-label")
        self.lbl_segments.setStyleSheet("background-color: #1e1e1e; color: #00ff00; padding: 5px;")

        layout.addWidget(self.lbl_time)
        layout.addWidget(self.lbl_segments)

        self.setLayout(layout)

        # Zamanlayıcı (Timer) - Başlangıçta start() çağrılmadı (Kendiliğinden çalışmaz)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)

    def toggle_play_pause(self):
        """Play ve Pause arasında geçiş yapar ve zamanlayıcıyı yönetir."""
        if not self.is_running:
            # Çalışmaya başla
            self.is_running = True
            self.btn_play_pause.setText("Pause")
            self.timer.start(1000)
        else:
            # Duraklat
            self.is_running = False
            self.btn_play_pause.setText("Play")
            self.timer.stop()

    def update_timer(self):
        """Zamanı günceller."""
        self.seconds += 1
        hours = self.seconds // 3600
        mins = (self.seconds % 3600) // 60
        secs = self.seconds % 60
        self.lbl_time.setText(f"{hours:02d}:{mins:02d}:{secs:02d}")
        
        # Segment artışı (Örnek mantık: Her 60 saniyede bir)
        if self.seconds % 60 == 0:
            self.segments += 1
            self.lbl_segments.setText(f"Segments: {self.segments}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RecWindow()
    window.show()
    sys.exit(app.exec_())
