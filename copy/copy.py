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

# --- kavram yol ayarı (otomatik; klasör yapısı: kavram/<program>/<program>.py) ---
import os as _os
import sys as _sys

_PROGRAM_DIR = _os.path.dirname(_os.path.abspath(__file__))
_KAVRAM_DIR = _os.environ.get("KAVRAM_DIR") or _os.path.dirname(_PROGRAM_DIR)
_KAVRAM_EXPORT_DIR = _os.path.join(_KAVRAM_DIR, "export")
# -------------------------------------------------------------------------------

# Bu dosyanın adı 'copy.py' ve Python'un standart 'copy' modülüyle aynı.
# Betik klasörü sys.path'in başındaysa stdlib'nin 'copy' modülü bu dosyayla
# karışır (ör. dataclasses bunu içe aktarır). Bu yüzden klasörü sona taşıyoruz.
_sys.path[:] = [p for p in _sys.path if _os.path.abspath(p or _os.curdir) != _PROGRAM_DIR]
_sys.path.append(_PROGRAM_DIR)

from PyQt5.QtWidgets import QApplication  # noqa: E402

from copya_lib.main_window import MainWindow as _MainWindow  # noqa: E402


class CoreWindow:
    """Yalnızca bağımsız test için yer tutucu (gerçeği kavram.py)."""

    def showSwitcher(self):
        print("Switcher placeholder")


class MainWindow(_MainWindow):
    """Kavram'ın kullandığı giriş noktası. Dışarıdan aynı imza ile çağrılabilir."""

    def __init__(self, core_window_ref=None):
        super().__init__(core_window_ref=core_window_ref, export_dir=_KAVRAM_EXPORT_DIR)


if __name__ == '__main__':
    app = QApplication(_sys.argv)
    window = MainWindow()
    window.show()
    _sys.exit(app.exec_())
