#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

import sys
import os
import json
import calendar
import time
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, QTimer, QSettings, QLocale, QDate, pyqtSignal
from PyQt5.QtGui import QColor, QPalette, QFont, QIcon, QTextCharFormat, QKeyEvent
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QSpinBox, QCheckBox, QStackedWidget,
    QFrame, QAbstractItemView, QCalendarWidget, QDateTimeEdit, QDialog, 
    QDialogButtonBox, QStyleFactory, QGridLayout, QTextEdit, QLineEdit, QMessageBox
)

def resource_path(relative_path):
    """ PyInstaller vb. derleyiciler ve geliştirme ortamı için kaynak yolu bulucu """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---------- MODERN DARK STYLESHEET ----------
DARK_STYLE = """
QMainWindow {
    background-color: #121212;
}
QWidget {
    background-color: #121212;
    color: #e0e0e0;
    font-family: 'Segoe UI', 'Ubuntu', sans-serif;
    font-size: 14px;
}
QFrame {
    background-color: #1e1e1e;
    border-radius: 8px;
    border: 1px solid #2d2d2d;
}
QLabel {
    background: transparent;
    border: none;
    color: #ffffff;
}
QComboBox, QLineEdit, QTextEdit {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
    padding: 6px 12px;
    border-radius: 6px;
    color: #ffffff;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #2b2b2b;
    selection-background-color: #4CAF50;
    color: #ffffff;
    border: 1px solid #3d3d3d;
}
QPushButton {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
    padding: 8px 16px;
    border-radius: 6px;
    color: #ffffff;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #383838;
    border: 1px solid #4d4d4d;
}
QPushButton:pressed {
    background-color: #1e1e1e;
}
QTableWidget {
    background-color: #1e1e1e;
    alternate-background-color: #252525;
    gridline-color: #2d2d2d;
    selection-background-color: #3d3d3d;
    color: #ffffff;
    border: 1px solid #2d2d2d;
    border-radius: 8px;
}
QTableWidget::item {
    padding: 8px;
}
QHeaderView::section {
    background-color: #2b2b2b;
    padding: 6px;
    border: 1px solid #2d2d2d;
    color: #e0e0e0;
    font-weight: bold;
}
QProgressBar {
    border: 1px solid #2d2d2d;
    border-radius: 6px;
    text-align: center;
    background-color: #1a1a1a;
    color: #ffffff;
    font-weight: bold;
    height: 20px;
}
QProgressBar::chunk {
    background-color: #4CAF50;
    border-radius: 5px;
}
QSpinBox {
    background-color: #2b2b2b;
    border: 1px solid #3d3d3d;
    padding: 6px;
    border-radius: 6px;
    color: #ffffff;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #3d3d3d;
    border-radius: 3px;
    margin: 1px;
}
/* CALENDAR WIDGET BEYAZ KARE DÜZELTMESİ */
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #2b2b2b;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QCalendarWidget QToolButton {
    color: #ffffff;
    background-color: transparent;
    border-radius: 4px;
    padding: 4px;
}
QCalendarWidget QToolButton:hover {
    background-color: #3d3d3d;
}
QCalendarWidget QMenu {
    background-color: #2b2b2b;
    color: #ffffff;
}
QCalendarWidget QSpinBox {
    background-color: #3d3d3d;
    color: #ffffff;
}
QCalendarWidget QTableView {
    background-color: #1e1e1e;
    alternate-background-color: #252525;
    color: #ffffff;
    selection-background-color: #4CAF50;
    selection-color: #ffffff;
}
QCheckBox {
    background: transparent;
    border: none;
    color: #ffffff;
}
QDialog {
    background-color: #121212;
}
"""

def format_sayi(sayi):
    return f"{int(sayi):,}".replace(',', '.')

# ---------- VERİ YÖNETİCİSİ (JSON) ----------
class DataManager:
    def __init__(self):
        self.dir_name = "Zaman_Veri"
        self.file_name = os.path.join(self.dir_name, "veriler.json")
        self.data = {
            "notes": {},  # Format: "MM-DD": {"title": "...", "text": "..."}
            "settings": {
                "life_target_ts": None,
                "mod3_seg1": 0,
                "mod3_seg2": 8,
                "mod3_seg3": 11,
                "mod3_show_seconds": False,
                "pomodoro": {}
            }
        }
        self.load()

    def load(self):
        if not os.path.exists(self.dir_name):
            os.makedirs(self.dir_name)
        
        if os.path.exists(self.file_name):
            try:
                with open(self.file_name, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Geriye dönük uyumluluk ve eksik anahtarları koruma
                    if "notes" in loaded: self.data["notes"] = loaded["notes"]
                    if "settings" in loaded: 
                        for k, v in loaded["settings"].items():
                            self.data["settings"][k] = v
            except Exception as e:
                print(f"Veri okunurken hata: {e}")
                
    def save(self):
        if not os.path.exists(self.dir_name):
            os.makedirs(self.dir_name)
        try:
            with open(self.file_name, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Veri kaydedilirken hata: {e}")

    def get_note(self, mm_dd):
        return self.data["notes"].get(mm_dd, {"title": "", "text": ""})

    def set_note(self, mm_dd, title, text):
        if not title.strip() and not text.strip():
            if mm_dd in self.data["notes"]:
                del self.data["notes"][mm_dd]
        else:
            self.data["notes"][mm_dd] = {"title": title, "text": text}
        self.save()

# Global DataManager Instance
db = DataManager()

# ---------- GÜNLÜK NOT DİYALOĞU ----------
class NoteDialog(QDialog):
    def __init__(self, date_str_mm_dd, display_date_str, parent=None):
        super().__init__(parent)
        self.date_str = date_str_mm_dd
        self.setWindowTitle(f"Not Ekle/Düzenle - {display_date_str}")
        self.setMinimumSize(400, 300)
        self.setStyleSheet(DARK_STYLE)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Başlık:"))
        self.title_input = QLineEdit()
        layout.addWidget(self.title_input)
        
        layout.addWidget(QLabel("Metin:"))
        self.text_input = QTextEdit()
        layout.addWidget(self.text_input)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Save).setText("Kaydet")
        btn_box.button(QDialogButtonBox.Cancel).setText("İptal")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
        # Mevcut veriyi yükle
        note = db.get_note(self.date_str)
        self.title_input.setText(note["title"])
        self.text_input.setPlainText(note["text"])

    def get_data(self):
        return self.title_input.text(), self.text_input.toPlainText()


# ---------- STATE: Pomodoro ----------
class PomodoroState:
    def __init__(self):
        self.work_sec = 25 * 60
        self.short_break_sec = 5 * 60
        self.long_break_sec = 15 * 60
        self.cycles_before_long = 4

        self.phase = "Çalışma"
        self.remaining_seconds = self.work_sec
        self.cycles_done = 0
        self.running = False
        self.target_ts = None
        
        # Sinyaller için basit bir callback mekanizması
        self.on_phase_ended = None 

    def reset(self):
        self.phase = "Çalışma"
        self.remaining_seconds = self.work_sec
        self.cycles_done = 0
        self.running = False
        self.target_ts = None

    def start_or_pause(self):
        if not self.running:
            self.running = True
            self.target_ts = datetime.now() + timedelta(seconds=self.remaining_seconds)
        else:
            self.running = False
            self.remaining_seconds = max(0, (self.target_ts - datetime.now()).total_seconds())
            self.target_ts = None

    def update(self):
        if self.running and self.target_ts:
            secs = (self.target_ts - datetime.now()).total_seconds()
            if secs <= 0:
                self._next_phase()
            else:
                self.remaining_seconds = int(secs)

    def _next_phase(self):
        if self.phase == "Çalışma":
            self.cycles_done += 1
            if self.cycles_done % self.cycles_before_long == 0:
                self.phase = "Uzun Mola"
                self.remaining_seconds = self.long_break_sec
            else:
                self.phase = "Kısa Mola"
                self.remaining_seconds = self.short_break_sec
        else:
            self.phase = "Çalışma"
            self.remaining_seconds = self.work_sec

        self.running = False # Kullanıcı Enter'a basana kadar durur
        self.target_ts = None
        
        if self.on_phase_ended:
            self.on_phase_ended()

    def to_dict(self):
        return {
            "work_sec": self.work_sec,
            "short_break_sec": self.short_break_sec,
            "long_break_sec": self.long_break_sec,
            "cycles_before_long": self.cycles_before_long,
            "phase": self.phase,
            "remaining_seconds": self.remaining_seconds,
            "cycles_done": self.cycles_done,
            "running": self.running,
            "target_ts": self.target_ts.isoformat() if self.target_ts else None,
        }

    def load_dict(self, d):
        self.work_sec = d.get("work_sec", 25 * 60)
        self.short_break_sec = d.get("short_break_sec", 5 * 60)
        self.long_break_sec = d.get("long_break_sec", 15 * 60)
        self.cycles_before_long = d.get("cycles_before_long", 4)
        self.phase = d.get("phase", "Çalışma")
        self.cycles_done = d.get("cycles_done", 0)
        self.running = d.get("running", False)
        
        target_str = d.get("target_ts")
        if target_str:
            self.target_ts = datetime.fromisoformat(target_str)
        else:
            self.target_ts = None

        if self.running and self.target_ts:
            rem = (self.target_ts - datetime.now()).total_seconds()
            if rem > 0:
                self.remaining_seconds = int(rem)
            else:
                # Süre bilgisayar kapalıyken dolmuş
                self.remaining_seconds = 0
                self.running = False
                self.target_ts = None
        else:
            self.remaining_seconds = max(0, d.get("remaining_seconds", self.work_sec))


# ---------- MOD 0 : Pomodoro Widget ----------
class PomodoroWidget(QWidget):
    def __init__(self, state: PomodoroState, save_callback, alert_callback):
        super().__init__()
        self.state = state
        self.save_callback = save_callback
        self.alert_callback = alert_callback
        self.state.on_phase_ended = self.phase_ended_event
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Ayarlar
        settings_frame = QFrame()
        settings_layout = QHBoxLayout(settings_frame)
        
        settings_layout.addWidget(QLabel("Çalışma(dk):"))
        self.work_spin = QSpinBox()
        self.work_spin.setRange(1, 120)
        self.work_spin.setValue(self.state.work_sec // 60)
        self.work_spin.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.work_spin)

        settings_layout.addWidget(QLabel("Kısa Mola(dk):"))
        self.short_spin = QSpinBox()
        self.short_spin.setRange(1, 60)
        self.short_spin.setValue(self.state.short_break_sec // 60)
        self.short_spin.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.short_spin)

        settings_layout.addWidget(QLabel("Uzun Mola(dk):"))
        self.long_spin = QSpinBox()
        self.long_spin.setRange(1, 120)
        self.long_spin.setValue(self.state.long_break_sec // 60)
        self.long_spin.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.long_spin)

        layout.addWidget(settings_frame)

        # Görüntü
        display_frame = QFrame()
        display_layout = QVBoxLayout(display_frame)
        
        self.phase_label = QLabel(self.state.phase)
        self.phase_label.setAlignment(Qt.AlignCenter)
        self.phase_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #e0e0e0;")
        display_layout.addWidget(self.phase_label)

        self.time_label = QLabel("25:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("font-size: 72px; font-weight: bold; color: #4CAF50;")
        display_layout.addWidget(self.time_label)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(12)
        display_layout.addWidget(self.progress)
        
        layout.addWidget(display_frame)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Başlat / Duraklat (Enter)")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.on_start_pause)
        btn_layout.addWidget(self.start_btn)

        self.reset_btn = QPushButton("Sıfırla")
        self.reset_btn.setMinimumHeight(40)
        self.reset_btn.clicked.connect(self.on_reset)
        btn_layout.addWidget(self.reset_btn)

        layout.addLayout(btn_layout)
        
        # Günün Notu Alanı
        note_frame = QFrame()
        note_layout = QVBoxLayout(note_frame)
        note_layout.setContentsMargins(10, 5, 10, 10)
        
        self.note_title_lbl = QLabel("Günün Notu")
        self.note_title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #aaaaaa;")
        note_layout.addWidget(self.note_title_lbl)
        
        self.note_text_display = QTextEdit()
        self.note_text_display.setReadOnly(True)
        self.note_text_display.setStyleSheet("background-color: transparent; border: none; color: #e0e0e0;")
        self.note_text_display.setMinimumHeight(60)
        note_layout.addWidget(self.note_text_display)
        
        layout.addWidget(note_frame)

    def phase_ended_event(self):
        self.save_callback()
        self.alert_callback()

    def trigger_enter(self):
        # Enter'a basıldığında başlat veya durdur
        self.on_start_pause()

    def on_settings_changed(self):
        self.state.work_sec = self.work_spin.value() * 60
        self.state.short_break_sec = self.short_spin.value() * 60
        self.state.long_break_sec = self.long_spin.value() * 60
        
        if not self.state.running:
            if self.state.phase == "Çalışma":
                self.state.remaining_seconds = self.state.work_sec
            elif self.state.phase == "Kısa Mola":
                self.state.remaining_seconds = self.state.short_break_sec
            else:
                self.state.remaining_seconds = self.state.long_break_sec
        self.save_callback()

    def on_start_pause(self):
        self.state.start_or_pause()
        self.save_callback()

    def on_reset(self):
        self.state.reset()
        self.work_spin.setValue(self.state.work_sec // 60)
        self.short_spin.setValue(self.state.short_break_sec // 60)
        self.long_spin.setValue(self.state.long_break_sec // 60)
        self.save_callback()

    def update_display(self):
        self.state.update()
        mins, secs = divmod(self.state.remaining_seconds, 60)
        self.time_label.setText(f"{int(mins):02d}:{int(secs):02d}")
        self.phase_label.setText(self.state.phase)

        if self.state.phase == "Çalışma":
            total = self.state.work_sec
            color = "#4CAF50" # Yeşil
        elif self.state.phase == "Kısa Mola":
            total = self.state.short_break_sec
            color = "#0A84FF" # Mavi
        else:
            total = self.state.long_break_sec
            color = "#FF9F0A" # Turuncu
            
        self.time_label.setStyleSheet(f"font-size: 72px; font-weight: bold; color: {color}; border: none;")

        self.progress.setMaximum(total)
        self.progress.setValue(int(total - self.state.remaining_seconds))
        
        # Günün notunu güncelle
        today_mm_dd = datetime.now().strftime("%m-%d")
        note = db.get_note(today_mm_dd)
        if note["title"] or note["text"]:
            self.note_title_lbl.setText(f"📋 {note['title']}" if note['title'] else "📋 Günün Notu")
            self.note_text_display.setPlainText(note["text"])
        else:
            self.note_title_lbl.setText("Günün Notu Yok")
            self.note_text_display.setPlainText("")


# ---------- MOD 1 : Normal Türkçe Takvim ----------
class NormalCalendarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        clock_frame = QFrame()
        clock_layout = QVBoxLayout(clock_frame)
        
        self.digital_clock = QLabel("00:00:00")
        self.digital_clock.setAlignment(Qt.AlignCenter)
        self.digital_clock.setStyleSheet("font-size: 48px; font-weight: bold; color: #ffffff; border: none;")
        clock_layout.addWidget(self.digital_clock)

        half_layout = QHBoxLayout()
        self.first_half_bar = QProgressBar()
        self.first_half_bar.setFormat("İlk 12 Saat %p%")
        half_layout.addWidget(self.first_half_bar)
        
        self.second_half_bar = QProgressBar()
        self.second_half_bar.setFormat("Son 12 Saat %p%")
        half_layout.addWidget(self.second_half_bar)
        
        clock_layout.addLayout(half_layout)
        layout.addWidget(clock_frame)

        self.calendar = QCalendarWidget(self)
        self.calendar.setLocale(QLocale(QLocale.Turkish, QLocale.Turkey))
        self.calendar.setFirstDayOfWeek(Qt.Monday)
        self.calendar.setGridVisible(True)
        self.calendar.setStyleSheet("border-radius: 8px; border: 1px solid #2d2d2d;")
        
        self.calendar.activated.connect(self.date_clicked)
        self.calendar.clicked.connect(self.date_clicked)

        layout.addWidget(self.calendar)

    def date_clicked(self, qdate):
        # Format: MM-DD
        mm_dd = f"{qdate.month():02d}-{qdate.day():02d}"
        display_str = f"{qdate.day()} {QLocale(QLocale.Turkish).monthName(qdate.month())}"
        dlg = NoteDialog(mm_dd, display_str, self)
        if dlg.exec_() == QDialog.Accepted:
            t, txt = dlg.get_data()
            db.set_note(mm_dd, t, txt)

    def update_display(self):
        now = datetime.now()
        self.digital_clock.setText(now.strftime("%H:%M:%S"))
        
        hour = now.hour
        minute = now.minute
        
        if hour < 12:
            val1 = int(((hour * 60) + minute) / (12 * 60) * 100)
            val2 = 0
        else:
            val1 = 100
            val2 = int((((hour - 12) * 60) + minute) / (12 * 60) * 100)
            
        self.first_half_bar.setValue(val1)
        self.second_half_bar.setValue(val2)
        
        # Not olan günleri griye boyama
        fmt_note = QTextCharFormat()
        fmt_note.setBackground(QColor("#555555"))
        fmt_note.setForeground(QColor("#ffffff"))
        
        fmt_normal = QTextCharFormat()
        fmt_normal.setBackground(QColor("transparent"))
        fmt_normal.setForeground(QColor("#ffffff"))

        # Ekranda görünen ayın günlerini tarayıp notları kontrol et
        y = self.calendar.yearShown()
        m = self.calendar.monthShown()
        days_in_month = calendar.monthrange(y, m)[1]
        
        for d in range(1, days_in_month + 1):
            date_obj = QDate(y, m, d)
            mm_dd = f"{m:02d}-{d:02d}"
            
            # Seçili gün değilse boya (seçili günün kendi özel rengi var)
            if db.get_note(mm_dd)["title"] or db.get_note(mm_dd)["text"]:
                self.calendar.setDateTextFormat(date_obj, fmt_note)
            else:
                self.calendar.setDateTextFormat(date_obj, fmt_normal)


# ---------- MOD 2 : Rakamlı Takvim ----------
class NumericCalendarWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        clock_frame = QFrame()
        clock_layout = QVBoxLayout(clock_frame)
        self.digital_clock = QLabel("00:00:00")
        self.digital_clock.setAlignment(Qt.AlignCenter)
        self.digital_clock.setStyleSheet("font-size: 48px; font-weight: bold; color: #ffffff; border:none;")
        clock_layout.addWidget(self.digital_clock)
        
        half_layout = QHBoxLayout()
        self.first_half_bar = QProgressBar()
        self.first_half_bar.setFormat("İlk 12 Saat %p%")
        half_layout.addWidget(self.first_half_bar)
        self.second_half_bar = QProgressBar()
        self.second_half_bar.setFormat("Son 12 Saat %p%")
        half_layout.addWidget(self.second_half_bar)
        
        clock_layout.addLayout(half_layout)
        layout.addWidget(clock_frame)

        self.month_year_label = QLabel()
        self.month_year_label.setAlignment(Qt.AlignCenter)
        self.month_year_label.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px; color: #ffffff;")
        layout.addWidget(self.month_year_label)

        self.table = QTableWidget(6, 7)
        self.table.setHorizontalHeaderLabels(["1", "2", "3", "4", "5", "6", "7"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellClicked.connect(self.cell_clicked)
        layout.addWidget(self.table)

    def cell_clicked(self, row, col):
        item = self.table.item(row, col)
        if item and item.text():
            day = int(item.text())
            now = datetime.now()
            mm_dd = f"{now.month:02d}-{day:02d}"
            display_str = f"{day} (Ay: {now.month})"
            dlg = NoteDialog(mm_dd, display_str, self)
            if dlg.exec_() == QDialog.Accepted:
                t, txt = dlg.get_data()
                db.set_note(mm_dd, t, txt)

    def update_display(self):
        now = datetime.now()
        self.digital_clock.setText(now.strftime("%H:%M:%S"))
        
        hour = now.hour
        minute = now.minute
        if hour < 12:
            val1 = int(((hour * 60) + minute) / (12 * 60) * 100)
            val2 = 0
        else:
            val1 = 100
            val2 = int((((hour - 12) * 60) + minute) / (12 * 60) * 100)
            
        self.first_half_bar.setValue(val1)
        self.second_half_bar.setValue(val2)

        year = now.year
        month = now.month
        self.month_year_label.setText(f"Ay: {month}  |  Yıl: {year}")

        cal = calendar.monthcalendar(year, month)
        
        self.table.clearContents()
        
        for row_idx, week in enumerate(cal[:6]):
            for col_idx, day in enumerate(week):
                if day != 0:
                    item = QTableWidgetItem(str(day))
                    item.setTextAlignment(Qt.AlignCenter)
                    
                    mm_dd = f"{month:02d}-{day:02d}"
                    has_note = bool(db.get_note(mm_dd)["title"] or db.get_note(mm_dd)["text"])
                    
                    if day == now.day:
                        item.setBackground(QColor("#4CAF50"))
                        item.setForeground(QColor("white"))
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                    elif has_note:
                        item.setBackground(QColor("#555555"))
                        item.setForeground(QColor("white"))
                    else:
                        item.setForeground(QColor("#ffffff"))
                        
                    self.table.setItem(row_idx, col_idx, item)


# ---------- MOD 3 : Sekizli Takvim (Miladi Senkronize) ----------
class OctalCalendarWidget(QWidget):
    def __init__(self):
        super().__init__()
        # Ayarlar veritabanından alınır
        self.show_seconds = db.data["settings"].get("mod3_show_seconds", False)
        self.seg1_start = db.data["settings"].get("mod3_seg1", 0)
        self.seg2_start = db.data["settings"].get("mod3_seg2", 8)
        self.seg3_start = db.data["settings"].get("mod3_seg3", 11)
        
        self.view_year = datetime.now().year
        self.view_month = self.get_current_octal_month()

        self.init_ui()

    def get_current_octal_month(self):
        now = datetime.now()
        doy = now.timetuple().tm_yday
        return min(((doy - 1) // 40) + 1, 9)

    def save_segments(self):
        self.seg1_start = self.spin_seg1.value()
        self.seg2_start = self.spin_seg2.value()
        self.seg3_start = self.spin_seg3.value()
        
        db.data["settings"]["mod3_seg1"] = self.seg1_start
        db.data["settings"]["mod3_seg2"] = self.seg2_start
        db.data["settings"]["mod3_seg3"] = self.seg3_start
        db.save()

    def init_ui(self):
        layout = QVBoxLayout(self)

        clock_frame = QFrame()
        clock_layout = QVBoxLayout(clock_frame)
        
        self.small_clock = QLabel("00:00:00")
        self.small_clock.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self.small_clock.setStyleSheet("font-size: 16px; color: #aaaaaa; border: none;")
        clock_layout.addWidget(self.small_clock)

        self.segment_label = QLabel("1. Bölüm - 0:00")
        self.segment_label.setAlignment(Qt.AlignCenter)
        self.segment_label.setStyleSheet("font-size: 48px; font-weight: bold; color: #4CAF50; border: none;")
        clock_layout.addWidget(self.segment_label)

        self.sec_check = QCheckBox("Saniyeyi Göster")
        self.sec_check.setChecked(self.show_seconds)
        self.sec_check.toggled.connect(self.toggle_seconds)
        clock_layout.addWidget(self.sec_check, 0, Qt.AlignHCenter)
        
        layout.addWidget(clock_frame)

        seg_settings_frame = QFrame()
        seg_layout = QHBoxLayout(seg_settings_frame)
        
        seg_layout.addWidget(QLabel("1. Bölüm:"))
        self.spin_seg1 = QSpinBox()
        self.spin_seg1.setRange(0, 23)
        self.spin_seg1.setValue(self.seg1_start)
        self.spin_seg1.valueChanged.connect(self.save_segments)
        seg_layout.addWidget(self.spin_seg1)
        
        seg_layout.addWidget(QLabel("2. Bölüm:"))
        self.spin_seg2 = QSpinBox()
        self.spin_seg2.setRange(0, 23)
        self.spin_seg2.setValue(self.seg2_start)
        self.spin_seg2.valueChanged.connect(self.save_segments)
        seg_layout.addWidget(self.spin_seg2)
        
        seg_layout.addWidget(QLabel("3. Bölüm:"))
        self.spin_seg3 = QSpinBox()
        self.spin_seg3.setRange(0, 23)
        self.spin_seg3.setValue(self.seg3_start)
        self.spin_seg3.valueChanged.connect(self.save_segments)
        seg_layout.addWidget(self.spin_seg3)

        layout.addWidget(seg_settings_frame)

        # Takvim Navigasyon
        nav_frame = QFrame()
        nav_layout = QHBoxLayout(nav_frame)
        
        self.btn_prev = QPushButton("< Önceki Ay")
        self.btn_prev.clicked.connect(self.prev_month)
        nav_layout.addWidget(self.btn_prev)
        
        self.month_info_label = QLabel()
        self.month_info_label.setAlignment(Qt.AlignCenter)
        self.month_info_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        nav_layout.addWidget(self.month_info_label, 1)
        
        self.btn_next = QPushButton("Sonraki Ay >")
        self.btn_next.clicked.connect(self.next_month)
        nav_layout.addWidget(self.btn_next)
        
        self.btn_today = QPushButton("Bugün")
        self.btn_today.clicked.connect(self.go_today)
        nav_layout.addWidget(self.btn_today)
        
        layout.addWidget(nav_frame)

        self.grid_table = QTableWidget(5, 8)
        self.grid_table.setHorizontalHeaderLabels([f"{i+1}" for i in range(8)])
        self.grid_table.setVerticalHeaderLabels([f"{i+1}" for i in range(5)])
        self.grid_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.grid_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.grid_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.grid_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.grid_table.cellClicked.connect(self.cell_clicked)
        layout.addWidget(self.grid_table)

    def toggle_seconds(self, checked):
        self.show_seconds = checked
        db.data["settings"]["mod3_show_seconds"] = checked
        db.save()

    def prev_month(self):
        self.view_month -= 1
        if self.view_month < 1:
            self.view_month = 9
            self.view_year -= 1
        self.update_calendar_grid()

    def next_month(self):
        self.view_month += 1
        if self.view_month > 9:
            self.view_month = 1
            self.view_year += 1
        self.update_calendar_grid()

    def go_today(self):
        self.view_year = datetime.now().year
        self.view_month = self.get_current_octal_month()
        self.update_calendar_grid()

    def cell_clicked(self, row, col):
        item = self.grid_table.item(row, col)
        if item and item.text():
            day = int(item.text())
            # Miladi Karşılığını (MM-DD) Bul
            doy = ((self.view_month - 1) * 40) + day
            try:
                # O yılın 1 ocağına gün ekleyerek normal tarihi bul
                target_date = datetime(self.view_year, 1, 1) + timedelta(days=doy - 1)
                mm_dd = target_date.strftime("%m-%d")
                
                dlg = NoteDialog(mm_dd, f"Sekizli {day}. Gün ({target_date.strftime('%d.%m.%Y')})", self)
                if dlg.exec_() == QDialog.Accepted:
                    t, txt = dlg.get_data()
                    db.set_note(mm_dd, t, txt)
                    self.update_calendar_grid() # Renk yenilemesi için
            except ValueError:
                pass # Yıl sonu gün aşımı vs korunması (normalde olmaz)

    def update_calendar_grid(self):
        self.month_info_label.setText(f"Yıl: {self.view_year}  |  Ay: {self.view_month}")
        
        days_in_year = 366 if calendar.isleap(self.view_year) else 365
        if self.view_month < 9:
            days_in_this_month = 40
        else:
            days_in_this_month = days_in_year - 320 # Genelde 45 veya 46 (Kullanıcı 5-6 dedi ama 365-320 = 45. Yani 9. ay 45 gün çeker. Biz 40 lık sisteme uyalım)
            
            # Eğer tam 40 gün ise ve artan son aysa:
            # 365 / 40 = 9 ay. 8 ay * 40 = 320. Geriye 45 gün kalıyor. 
            # 9 ay sisteminde son ay 45 gün çekmelidir. 
            # Tablomuz 5x8 = 40 lık. Eğer 45 gün sığacaksa 6. satır gerekir!
            # Bunu çözmek için tablo satır sayısını dinamik yapalım.

        self.grid_table.clearContents()
        
        # Satır sayısını ayarla (Genelde 5 satır = 40 gün. 9. Ay için 6 satır = 48 hücre)
        required_rows = (days_in_this_month + 7) // 8
        self.grid_table.setRowCount(required_rows)
        self.grid_table.setVerticalHeaderLabels([f"{i+1}" for i in range(required_rows)])

        now = datetime.now()
        current_doy = now.timetuple().tm_yday
        current_oct_month = self.get_current_octal_month()
        current_oct_day = ((current_doy - 1) % 40) + 1 if current_oct_month < 9 else current_doy - 320

        for r in range(required_rows):
            for c in range(8):
                gun_no = (r * 8) + c + 1
                if gun_no <= days_in_this_month:
                    item = QTableWidgetItem(str(gun_no))
                    item.setTextAlignment(Qt.AlignCenter)
                    
                    # Normal tarih karşılığını bularak not var mı kontrol et
                    doy = ((self.view_month - 1) * 40) + gun_no
                    has_note = False
                    try:
                        target_date = datetime(self.view_year, 1, 1) + timedelta(days=doy - 1)
                        mm_dd = target_date.strftime("%m-%d")
                        has_note = bool(db.get_note(mm_dd)["title"] or db.get_note(mm_dd)["text"])
                    except: pass
                    
                    if self.view_year == now.year and self.view_month == current_oct_month and gun_no == current_oct_day:
                        item.setBackground(QColor("#4CAF50"))
                        item.setForeground(QColor("white"))
                        font = QFont()
                        font.setBold(True)
                        item.setFont(font)
                    elif has_note:
                        item.setBackground(QColor("#555555"))
                        item.setForeground(QColor("white"))
                    else:
                        item.setForeground(QColor("#ffffff"))
                        
                    self.grid_table.setItem(r, c, item)

    def update_display(self):
        now = datetime.now()
        self.small_clock.setText(now.strftime("%H:%M:%S"))
        
        hour = now.hour
        minute = now.minute
        second = now.second

        times = [
            (self.seg1_start, 1),
            (self.seg2_start, 2),
            (self.seg3_start, 3)
        ]
        times.sort(reverse=True)

        current_seg = times[-1][1]
        seg_start_hour = times[-1][0]
        
        for start_h, seg_idx in times:
            if hour >= start_h:
                current_seg = seg_idx
                seg_start_hour = start_h
                break

        seg_hour = (hour - seg_start_hour) % 24
        
        seg_time_str = f"{current_seg}. Bölüm  |  {seg_hour}:{minute:02d}"
        if self.show_seconds:
            seg_time_str += f":{second:02d}"
            
        self.segment_label.setText(seg_time_str)
        self.update_calendar_grid() # Sadece bugünü boyamak için hızlı güncelleme

# ---------- MOD 4 : Ömür Sayacı (Kusursuz Senkron) ----------
class LifeCountdownWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.target_ts = self.load_target()
        self.init_ui()

    def load_target(self):
        val = db.data["settings"].get("life_target_ts")
        if val:
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                pass
        return None

    def save_target(self):
        if self.target_ts:
            db.data["settings"]["life_target_ts"] = self.target_ts.isoformat()
        else:
            db.data["settings"]["life_target_ts"] = None
        db.save()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        display_frame = QFrame()
        disp_layout = QVBoxLayout(display_frame)
        disp_layout.setSpacing(20)

        self.sec_label = QLabel("0 Saniye")
        self.sec_label.setAlignment(Qt.AlignCenter)
        self.sec_label.setStyleSheet("font-size: 42px; font-weight: bold; color: #aaaaaa; border: none;")
        disp_layout.addWidget(self.sec_label)

        self.min_label = QLabel("0 Dakika")
        self.min_label.setAlignment(Qt.AlignCenter)
        self.min_label.setStyleSheet("font-size: 52px; font-weight: bold; color: #cccccc; border: none;")
        disp_layout.addWidget(self.min_label)

        self.hour_label = QLabel("0 Saat")
        self.hour_label.setAlignment(Qt.AlignCenter)
        self.hour_label.setStyleSheet("font-size: 64px; font-weight: bold; color: #ffffff; border: none;")
        disp_layout.addWidget(self.hour_label)

        self.day_label = QLabel("0 Gün")
        self.day_label.setAlignment(Qt.AlignCenter)
        self.day_label.setStyleSheet("font-size: 80px; font-weight: bold; color: #4CAF50; border: none;")
        disp_layout.addWidget(self.day_label)

        layout.addWidget(display_frame)

        cfg_frame = QFrame()
        cfg_layout = QHBoxLayout(cfg_frame)
        
        cfg_layout.addWidget(QLabel("Ömür Hedefi (Yıl):"))
        self.year_spin = QSpinBox()
        self.year_spin.setRange(1, 1000)
        self.year_spin.setValue(40)
        self.year_spin.setStyleSheet("font-size: 16px; padding: 4px;")
        cfg_layout.addWidget(self.year_spin)
        
        self.set_btn = QPushButton("Sayacı Başlat / Güncelle")
        self.set_btn.clicked.connect(self.start_countdown)
        cfg_layout.addWidget(self.set_btn)
        
        layout.addWidget(cfg_frame)

    def start_countdown(self):
        years = self.year_spin.value()
        # Tam doğru sayım için bulunduğumuz andan itibaren yılı ekleriz
        # Saniyesine kadar takip eder
        days = years * 365.25 # Artık yılları da ortalama katarak daha hassas bir ölçüm
        self.target_ts = datetime.now() + timedelta(days=days)
        self.save_target()
        self.update_display()

    def update_display(self):
        if not self.target_ts:
            self.sec_label.setText("-- Saniye")
            self.min_label.setText("-- Dakika")
            self.hour_label.setText("-- Saat")
            self.day_label.setText("-- Gün")
            return
            
        now = datetime.now()
        delta = self.target_ts - now
        
        if delta.total_seconds() <= 0:
            self.sec_label.setText("0 Saniye")
            self.min_label.setText("0 Dakika")
            self.hour_label.setText("0 Saat")
            self.day_label.setText("0 Gün")
            return

        total_secs = delta.total_seconds()
        
        total_mins = total_secs / 60
        total_hours = total_secs / 3600
        total_days = total_secs / 86400

        self.sec_label.setText(f"{format_sayi(total_secs)} Saniye")
        self.min_label.setText(f"{format_sayi(total_mins)} Dakika")
        self.hour_label.setText(f"{format_sayi(total_hours)} Saat")
        self.day_label.setText(f"{format_sayi(total_days)} Gün")


# ---------- ANA PENCERE ----------
class Zaman(QMainWindow):
    MODES = [
        "Mod 0: Pomodoro", 
        "Mod 1: Normal Türkçe Takvim", 
        "Mod 2: Rakamlı Takvim", 
        "Mod 3: Sekizli Takvim", 
        "Mod 4: Ömür Sayacı"
    ]

    def __init__(self):
        super().__init__()
        self.local_settings = QSettings("Zaman", "ZamanAppLocal")
        self.setWindowTitle("Zaman Yönetimi")
        
        self.setWindowIcon(QIcon(resource_path('ikon/Kavram.png')))
        self.setMinimumSize(750, 700)

        self.pomo_state = PomodoroState()
        self.pomo_state.load_dict(db.data["settings"].get("pomodoro", {}))

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        top_layout = QHBoxLayout()
        mod_label = QLabel("Aktif Mod:")
        mod_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        top_layout.addWidget(mod_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(self.MODES)
        self.mode_combo.currentIndexChanged.connect(self.switch_mode)
        top_layout.addWidget(self.mode_combo)
        
        info_label = QLabel("(Tam Ekran için F11'e basın)")
        info_label.setStyleSheet("color: #888888; font-size: 12px;")
        top_layout.addWidget(info_label)
        
        top_layout.addStretch()
        main_layout.addLayout(top_layout)

        self.stack = QStackedWidget()
        
        self.pomodoro_widget = PomodoroWidget(self.pomo_state, self.save_pomo_state, self.play_alert)
        self.normal_cal_widget = NormalCalendarWidget()
        self.numeric_cal_widget = NumericCalendarWidget()
        self.octal_cal_widget = OctalCalendarWidget()
        self.life_widget = LifeCountdownWidget()

        self.stack.addWidget(self.pomodoro_widget)
        self.stack.addWidget(self.normal_cal_widget)
        self.stack.addWidget(self.numeric_cal_widget)
        self.stack.addWidget(self.octal_cal_widget)
        self.stack.addWidget(self.life_widget)
        
        main_layout.addWidget(self.stack)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_active_mode)
        self.timer.start(100) 

        self.load_ui_state()

    def play_alert(self):
        # 2 kez bip sesi çıkar (Linux/Windows çapraz uyumlu)
        print('\a\a', end='', flush=True) 
        QApplication.beep()
        QTimer.singleShot(500, QApplication.beep)
        
        # Pencereyi en öne getir
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.raise_()
        self.activateWindow()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # Enter tuşuna basıldığında eğer Pomodoro sekmesindeysek başlat/durdur yap
            if self.stack.currentIndex() == 0:
                self.pomodoro_widget.trigger_enter()
        super().keyPressEvent(event)

    def save_pomo_state(self):
        db.data["settings"]["pomodoro"] = self.pomo_state.to_dict()
        db.save()

    def load_ui_state(self):
        idx = self.local_settings.value("current_mode", 0, type=int)
        if 0 <= idx < len(self.MODES):
            self.mode_combo.setCurrentIndex(idx)
        else:
            self.mode_combo.setCurrentIndex(0)

    def save_ui_state(self):
        self.local_settings.setValue("current_mode", self.mode_combo.currentIndex())
        self.save_pomo_state()

    def switch_mode(self, index):
        self.stack.setCurrentIndex(index)
        self.update_active_mode()
        self.save_ui_state()

    def update_active_mode(self):
        self.pomo_state.update()
        
        idx = self.stack.currentIndex()
        if idx == 0:
            self.pomodoro_widget.update_display()
        elif idx == 1:
            self.normal_cal_widget.update_display()
        elif idx == 2:
            self.numeric_cal_widget.update_display()
        elif idx == 3:
            self.octal_cal_widget.update_display()
        elif idx == 4:
            self.life_widget.update_display()

    def closeEvent(self, event):
        self.save_ui_state()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)
    
    win = Zaman()
    win.show()
    sys.exit(app.exec_())
