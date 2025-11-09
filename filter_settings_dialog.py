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

import sys
from PyQt5.QtWidgets import (QDialog, QGridLayout, QComboBox, QLabel, QPushButton)
from PyQt5.QtCore import Qt

class AdvancedFilterDialog(QDialog):
    """
    Gelişmiş ses filtresi ayarlarını yönetmek için kullanılan,
    bağımsız ve yeniden kullanılabilir bir Qt diyalog penceresi.
    """
    def __init__(self, initial_settings, parent=None):
        """
        Diyalog penceresini başlatır.

        Args:
            initial_settings (dict): Diyalogun başlangıçta göstereceği ayarları içeren sözlük.
            parent (QWidget, optional): Üst pencere (parent widget). Varsayılanı None'dır.
        """
        super().__init__(parent)
        self.setWindowTitle("Filter Settings")
        # Dışarı tıklandığında kapanması için Popup olarak ayarlandı
        self.setWindowFlags(Qt.Popup)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        # Başlangıç ayarlarının bir kopyasını alıyoruz
        self.settings = initial_settings.copy()

        # Arayüz stilini ayarla
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(40, 40, 40, 245);
                border: 1px solid #777;
                border-radius: 8px;
            }
            QLabel {
                color: #e0e0e0;
                background: transparent;
                font-size: 13px;
                font-weight: bold;
                padding-right: 5px;
            }
            QComboBox {
                background-color: #333; color: white; font-size: 13px;
                border: 1px solid #555; border-radius: 4px; padding: 4px;
            }
            QComboBox:hover { background-color: #444; }
            QComboBox::drop-down { border: 0px; }
            QComboBox QAbstractItemView {
                background-color: #282828; border: 1px solid #555;
                selection-background-color: #555; color: white;
            }
            QPushButton {
                background-color: #444; color: white; border: 1px solid #666;
                border-radius: 4px; padding: 5px 15px; margin-top: 5px;
            }
            QPushButton:hover { background-color: #555; }
        """)

        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

        # Filtre kontrollerini oluştur
        # Sütun 1
        self.combo_ai_nr = self.create_filter_combo(0, "AI Noise Reduction", ["Off", "On"])
        self.combo_noise_gate = self.create_filter_combo(1, "Noise Gate", ["Off"] + [f"{i}dB" for i in range(-80, -19, 5)])
        self.combo_hp = self.create_filter_combo(2, "HP Filter", ["Off"] + [f"{i}Hz" for i in range(20, 301, 10)])
        self.combo_lp = self.create_filter_combo(3, "LP Filter", ["Off"] + [f"{i}Hz" for i in range(2000, 20001, 1000)])
        self.combo_gain = self.create_filter_combo(4, "Gain", [f"{i}dB" for i in range(-12, 13, 1)])
        self.combo_reverb = self.create_filter_combo(5, "Reverb Reduction", ["Off", "Low", "Medium", "High", "Very High"])

        # Sütun 2
        self.combo_de_esser = self.create_filter_combo(0, "De-Esser", ["Off", "Low", "Medium", "High"], col_start=2)
        self.combo_de_hum = self.create_filter_combo(1, "De-Hum", ["Off", "Low", "Medium", "High"], col_start=2)
        self.combo_comp_thresh = self.create_filter_combo(2, "Comp. Threshold", ["Off"] + [f"{i}dB" for i in range(-60, 1, 5)], col_start=2)
        self.combo_comp_ratio = self.create_filter_combo(3, "Comp. Ratio", ["1:1", "2:1", "3:1", "4:1", "5:1", "8:1", "10:1"], col_start=2)
        self.combo_comp_attack = self.create_filter_combo(4, "Comp. Attack", [f"{i}ms" for i in [1, 5, 10, 20, 50, 100]], col_start=2)
        self.combo_comp_release = self.create_filter_combo(5, "Comp. Release", [f"{i}ms" for i in [50, 100, 200, 500, 1000]], col_start=2)

        # Sütun 3
        self.combo_eq_gain = self.create_filter_combo(0, "EQ Gain", [f"{i}dB" for i in range(-12, 13, 1)], col_start=4)
        self.combo_eq_freq = self.create_filter_combo(1, "EQ Freq.", [f"{i}Hz" for i in [500, 1000, 1500, 2000, 3000, 4000]], col_start=4)
        self.combo_eq_q = self.create_filter_combo(2, "EQ Q", ["0.5", "1.0", "2.0", "3.0", "5.0", "8.0"], col_start=4)

        # OK Butonu
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.layout.addWidget(self.ok_button, 6, 0, 1, 6, Qt.AlignCenter)

        self.load_initial_settings()
        self.setFixedSize(self.sizeHint())

    def create_filter_combo(self, row, label_text, items, col_start=0):
        """Yardımcı fonksiyon: Etiket ve ComboBox oluşturup layout'a ekler."""
        label = QLabel(label_text)
        combo = QComboBox()
        combo.addItems(items)
        self.layout.addWidget(label, row, col_start, Qt.AlignRight)
        self.layout.addWidget(combo, row, col_start + 1)
        return combo

    def load_initial_settings(self):
        """Mevcut ayarları ComboBox'lara yükler."""
        self.combo_ai_nr.setCurrentText("On" if self.settings.get('ai_nr_enabled') else "Off")
        self.combo_noise_gate.setCurrentText(f"{int(self.settings.get('noise_gate_threshold_db', -70))}dB" if self.settings.get('noise_gate_threshold_db', -70) > -990 else "Off")
        self.combo_hp.setCurrentText(f"{self.settings.get('hp_cutoff_hz', 150)}Hz" if self.settings.get('hp_cutoff_hz', 150) > 0 else "Off")
        self.combo_lp.setCurrentText(f"{self.settings.get('lp_cutoff_hz', 10000)}Hz" if self.settings.get('lp_cutoff_hz', 10000) > 0 else "Off")
        self.combo_gain.setCurrentText(f"{int(self.settings.get('gain_db', 6))}dB")

        level_map_rev = {0: "Off", 1: "Low", 2: "Medium", 3: "High", 4: "Very High"}
        self.combo_reverb.setCurrentText(level_map_rev.get(self.settings.get('reverb_reduction_level', 0), "Off"))
        self.combo_de_esser.setCurrentText(level_map_rev.get(self.settings.get('de_esser_level', 0), "Off"))
        self.combo_de_hum.setCurrentText(level_map_rev.get(self.settings.get('de_hum_level', 0), "Off"))

        self.combo_comp_thresh.setCurrentText(f"{int(self.settings.get('compressor_threshold_db', 0))}dB" if self.settings.get('compressor_threshold_db', 0) != 0 else "Off")
        self.combo_comp_ratio.setCurrentText(f"{int(self.settings.get('compressor_ratio', 3))}:1")
        self.combo_comp_attack.setCurrentText(f"{int(self.settings.get('compressor_attack_ms', 5))}ms")
        self.combo_comp_release.setCurrentText(f"{int(self.settings.get('compressor_release_ms', 150))}ms")

        self.combo_eq_gain.setCurrentText(f"{int(self.settings.get('eq_gain_db', 0))}dB")
        self.combo_eq_freq.setCurrentText(f"{int(self.settings.get('eq_freq_hz', 1000))}Hz")
        self.combo_eq_q.setCurrentText(str(self.settings.get('eq_q', 1.0)))

    def getSettings(self):
        """
        ComboBox'lardaki güncel değerleri okur ve bir ayar sözlüğü olarak döndürür.

        Returns:
            dict: Kullanıcının seçtiği en son ayarları içeren sözlük.
        """
        s = {} # Boş bir sözlükle başla
        s['ai_nr_enabled'] = self.combo_ai_nr.currentText() == "On"

        ng_text = self.combo_noise_gate.currentText()
        s['noise_gate_threshold_db'] = float(ng_text.replace('dB', '')) if ng_text != "Off" else -999

        hp_text = self.combo_hp.currentText()
        s['hp_cutoff_hz'] = int(hp_text.replace('Hz', '')) if hp_text != "Off" else 0

        lp_text = self.combo_lp.currentText()
        s['lp_cutoff_hz'] = int(lp_text.replace('Hz', '')) if lp_text != "Off" else 0

        s['gain_db'] = float(self.combo_gain.currentText().replace('dB', ''))

        level_map = {"Off": 0, "Low": 1, "Medium": 2, "High": 3, "Very High": 4}
        s['reverb_reduction_level'] = level_map.get(self.combo_reverb.currentText(), 0)
        s['de_esser_level'] = level_map.get(self.combo_de_esser.currentText(), 0)
        s['de_hum_level'] = level_map.get(self.combo_de_hum.currentText(), 0)

        ct_text = self.combo_comp_thresh.currentText()
        s['compressor_threshold_db'] = float(ct_text.replace('dB', '')) if ct_text != "Off" else 0.0

        s['compressor_ratio'] = float(self.combo_comp_ratio.currentText().replace(':1', ''))
        s['compressor_attack_ms'] = float(self.combo_comp_attack.currentText().replace('ms', ''))
        s['compressor_release_ms'] = float(self.combo_comp_release.currentText().replace('ms', ''))

        s['eq_gain_db'] = float(self.combo_eq_gain.currentText().replace('dB', ''))
        s['eq_freq_hz'] = float(self.combo_eq_freq.currentText().replace('Hz', ''))
        s['eq_q'] = float(self.combo_eq_q.currentText())

        return s

    def focusOutEvent(self, event):
        """Pencere odağını kaybettiğinde otomatik olarak kabul eder (kapanır)."""
        self.accept()
        super().focusOutEvent(event)

# Bu blok, dosyanın doğrudan çalıştırılıp test edilmesini sağlar.
if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import json

    # Test için varsayılan ayarlar
    test_settings = {
        'ai_nr_enabled': True, 'noise_gate_threshold_db': -70.0, 'hp_cutoff_hz': 150,
        'lp_cutoff_hz': 10000, 'gain_db': 6.0, 'reverb_reduction_level': 1,
        'de_esser_level': 2, 'de_hum_level': 0, 'compressor_threshold_db': -20.0,
        'compressor_ratio': 4.0, 'compressor_attack_ms': 5.0, 'compressor_release_ms': 150.0,
        'eq_gain_db': 3.0, 'eq_freq_hz': 2000.0, 'eq_q': 1.0,
    }

    app = QApplication(sys.argv)
    dialog = AdvancedFilterDialog(initial_settings=test_settings)

    # Diyalog penceresi "OK" ile kapatılırsa, seçilen ayarları yazdır
    if dialog.exec_():
        final_settings = dialog.getSettings()
        print("Ayarlar Kaydedildi:")
        print(json.dumps(final_settings, indent=4))
    else:
        print("İptal Edildi.")

    sys.exit()
