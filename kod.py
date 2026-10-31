#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PyStudio X — PyQt5 tabanlı Python geliştirme ortamı
# Kurulum: python3 -m pip install PyQt5
# Çalıştırma: python3 pystudio_x.py

import os
import sys
import json
import keyword
import re
from pathlib import Path

from PyQt5.QtCore import Qt, QProcess, QTimer, QSize
from PyQt5.QtGui import (
    QColor, QFont, QTextCharFormat, QSyntaxHighlighter, QTextCursor,
    QKeySequence, QTextDocument
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPlainTextEdit, QTextEdit, QTabWidget,
    QVBoxLayout, QHBoxLayout, QTreeView, QFileSystemModel, QAction,
    QFileDialog, QMessageBox, QToolBar, QStatusBar, QLabel, QLineEdit,
    QPushButton, QDockWidget, QComboBox, QInputDialog, QMenu
)

# ---- Kavram File / Export penceresi (file_manager) -------------------------------
# Kavram çekirdeğinden çalışırken "kavram_file_manager" adıyla yüklenir; program tek başına
# çalıştırılırsa kardeş klasördeki file_manager/file_manager.py doğrudan yüklenir.  Hiçbiri
# olmazsa Qt'nin kendi diyaloğuna dönülür (program asla dosya seçemeden kalmaz).
try:
    import kavram_file_manager as _fm
except Exception:
    try:
        import importlib.util as _ilu
        import os as _fm_os
        import sys as _fm_sys
        _fm_yol = _fm_os.path.join(_fm_os.path.dirname(_fm_os.path.abspath(__file__)), "file_manager", "file_manager.py")
        _fm_spec = _ilu.spec_from_file_location("kavram_file_manager", _fm_yol)
        _fm = _ilu.module_from_spec(_fm_spec)
        _fm_sys.modules["kavram_file_manager"] = _fm
        _fm_spec.loader.exec_module(_fm)
    except Exception:
        from PyQt5.QtWidgets import QFileDialog as _QFD

        class _fm:  # yedek: Qt diyaloğu
            ALL_FILES_LABEL = "Bütün Dosyalar (*)"

            @staticmethod
            def get_open_file_name(parent=None, caption="", directory="", filter="", initialFilter="",
                                   options=None, **_kw):
                return _QFD.getOpenFileName(parent, caption, directory, filter)

            @staticmethod
            def get_open_file_names(parent=None, caption="", directory="", filter="", initialFilter="",
                                    options=None, **_kw):
                return _QFD.getOpenFileNames(parent, caption, directory, filter)

            @staticmethod
            def get_save_file_name(parent=None, caption="", directory="", filter="", initialFilter="",
                                   options=None, **_kw):
                return _QFD.getSaveFileName(parent, caption, directory, filter)

            @staticmethod
            def get_existing_directory(parent=None, caption="", directory="", options=None, **_kw):
                return _QFD.getExistingDirectory(parent, caption, directory)

            @staticmethod
            def notify_saved(parent=None, text="Dosya kaydedildi.", msec=400):
                print(text)
# -----------------------------------------------------------------------------------


APP = "PyStudio X"
CONFIG_DIR = Path.home() / ".pystudio_x"
CONFIG_FILE = CONFIG_DIR / "settings.json"

DARK = '''
QMainWindow,QWidget{background:#17191f;color:#e3e6ee}
QMenuBar,QMenu,QToolBar{background:#20232b;color:#e3e6ee;border:0}
QMenuBar::item:selected,QMenu::item:selected{background:#343a49}
QToolBar{spacing:6px;padding:6px;border-bottom:1px solid #303541}
QToolButton{background:#292e39;border:1px solid #3a4150;border-radius:5px;padding:6px 9px}
QToolButton:hover{background:#3a4252}
QTabWidget::pane{border:1px solid #343a46}
QTabBar::tab{background:#222630;color:#b9c0ce;padding:9px 15px;border:1px solid #303642}
QTabBar::tab:selected{background:#343b49;color:#fff;border-bottom:2px solid #e04b4b}
QTreeView{background:#1c1f26;alternate-background-color:#222630;border:0}
QTreeView::item{padding:4px}
QTreeView::item:selected{background:#343b49}
QLineEdit,QComboBox{background:#20242d;color:#f0f2f8;border:1px solid #3a4150;border-radius:4px;padding:6px}
QPushButton{background:#303746;color:#f0f2f8;border:1px solid #434c5e;border-radius:5px;padding:6px 12px}
QPushButton:hover{background:#414b5e}
QStatusBar{background:#20232b;color:#b9c0ce}
QDockWidget::title{background:#242832;padding:7px}
QScrollBar:vertical{background:#1b1e25;width:12px}
QScrollBar::handle:vertical{background:#414858;min-height:25px;border-radius:5px}
'''
LIGHT = '''
QMainWindow,QWidget{background:#f4f5f8;color:#20232b}
QMenuBar,QMenu,QToolBar{background:#e8eaf0;color:#20232b;border:0}
QMenuBar::item:selected,QMenu::item:selected{background:#d2d7e2}
QToolBar{spacing:6px;padding:6px;border-bottom:1px solid #ccd1dc}
QToolButton{background:#fff;border:1px solid #c8ceda;border-radius:5px;padding:6px 9px}
QToolButton:hover{background:#e2e7f0}
QTabWidget::pane{border:1px solid #ccd1dc}
QTabBar::tab{background:#e8eaf0;color:#444b59;padding:9px 15px;border:1px solid #ccd1dc}
QTabBar::tab:selected{background:#fff;color:#111;border-bottom:2px solid #d63f46}
QTreeView{background:#fff;alternate-background-color:#f2f4f8;border:0}
QTreeView::item{padding:4px}
QTreeView::item:selected{background:#d8e3f7}
QLineEdit,QComboBox{background:#fff;color:#20232b;border:1px solid #c8ceda;border-radius:4px;padding:6px}
QPushButton{background:#e8eaf0;color:#20232b;border:1px solid #c8ceda;border-radius:5px;padding:6px 12px}
QPushButton:hover{background:#dce2ed}
QStatusBar{background:#e8eaf0;color:#444b59}
QDockWidget::title{background:#e2e5ec;padding:7px}
'''

class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document, dark=True):
        super().__init__(document)
        self.rules = []
        def add(pattern, color, bold=False, italic=False):
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Bold)
            if italic:
                fmt.setFontItalic(True)
            self.rules.append((re.compile(pattern), fmt))
        kw = "|".join(keyword.kwlist)
        add(r"\b(" + kw + r")\b", "#c792ea" if dark else "#7c3aed", True)
        add(r"\b(self|cls|None|True|False|NotImplemented|Ellipsis)\b", "#ffcb6b" if dark else "#9a6700")
        add(r"\b\d+(\.\d+)?\b", "#f78c6c" if dark else "#b45309")
        add(r"\b(def|class)\s+[A-Za-z_]\w*", "#82aaff" if dark else "#1d4ed8", True)
        add(r"\b[A-Za-z_]\w*(?=\s*\()", "#89ddff" if dark else "#0e7490")
        add(r"#.*$", "#697386" if dark else "#6b7280", False, True)
        add(r"'([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\"", "#c3e88d" if dark else "#15803d")
        add(r"@[A-Za-z_]\w*", "#f07178" if dark else "#be123c")
    def highlightBlock(self, text):
        for pattern, fmt in self.rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)

class CodeEditor(QPlainTextEdit):
    def __init__(self, dark=True):
        super().__init__()
        self.file_path = None
        self.saved_text = ""
        self.dark = dark
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setFont(QFont("DejaVu Sans Mono", 11))
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.highlighter = PythonHighlighter(self.document(), dark)
        self.cursorPositionChanged.connect(self.highlight_line)
        self.update_style()
    def update_style(self):
        if self.dark:
            self.setStyleSheet("QPlainTextEdit{background:#171a21;color:#d6deeb;border:0;padding:8px;selection-background-color:#38465f}")
        else:
            self.setStyleSheet("QPlainTextEdit{background:#fff;color:#20232b;border:0;padding:8px;selection-background-color:#c8daf7}")
        self.highlight_line()
    def highlight_line(self):
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#222833" if self.dark else "#f0f4fa"))
        selection.format.setProperty(QTextCharFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])
    def modified(self):
        return self.toPlainText() != self.saved_text
    def mark_saved(self):
        self.saved_text = self.toPlainText()
        self.document().setModified(False)

class PyStudio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP + " — Python Geliştirme Ortamı")
        self.resize(1450, 900)
        self.dark = True
        self.process = None
        self.settings = self.load_settings()
        self.last_dir = self.settings.get("last_dir", str(Path.home()))
        self.dark = bool(self.settings.get("dark", True))
        self.build_ui()
        self.apply_theme()
        self.restore_session()
        self.setStatusBar(QStatusBar())
        self.cursor_label = QLabel("Satır 1, Sütun 1")
        self.statusBar().addPermanentWidget(QLabel("PyQt5"))
        self.statusBar().addPermanentWidget(self.cursor_label)
        self.statusBar().showMessage("Hazır")
        self.recovery_timer = QTimer(self)
        self.recovery_timer.setInterval(30000)
        self.recovery_timer.timeout.connect(self.autosave_recovery)
        self.recovery_timer.start()

    def load_settings(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save_settings(self):
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            self.settings.update({
                "last_dir": self.last_dir, "dark": self.dark,
                "open_files": [e.file_path for e in self.editors() if e.file_path],
                "active_index": self.tabs.currentIndex()
            })
            CONFIG_FILE.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
        except Exception:
            pass

    def build_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_cursor_status)
        self.setCentralWidget(self.tabs)
        self.make_actions()
        self.make_menus()
        self.make_toolbar()
        self.make_file_dock()
        self.make_output_dock()
        self.make_find_dock()
        self.tabs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.tab_menu)
        self.new_file()

    def action(self, title, shortcut, fn):
        act = QAction(title, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(fn)
        return act

    def make_actions(self):
        self.new_act = self.action("Yeni Dosya", "Ctrl+N", self.new_file)
        self.open_act = self.action("Dosya Aç…", "Ctrl+O", self.open_file)
        self.save_act = self.action("Kaydet", "Ctrl+S", self.save_file)
        self.saveas_act = self.action("Farklı Kaydet…", "Ctrl+Shift+S", self.save_as)
        self.run_act = self.action("Çalıştır ▶", "F5", self.run_file)
        self.stop_act = self.action("Durdur ■", "Shift+F5", self.stop_process)
        self.find_act = self.action("Bul", "Ctrl+F", self.show_find)
        self.replace_act = self.action("Bul ve Değiştir", "Ctrl+H", self.show_find)
        self.goto_act = self.action("Satıra Git…", "Ctrl+G", self.goto_line)
        self.comment_act = self.action("Yorum Satırı", "Ctrl+/", self.toggle_comment)
        self.theme_act = self.action("Koyu/Açık Tema", "", self.toggle_theme)

    def make_menus(self):
        bar = self.menuBar()
        fm = bar.addMenu("Dosya")
        for a in (self.new_act, self.open_act, self.save_act, self.saveas_act):
            fm.addAction(a)
        fm.addSeparator()
        fm.addAction("Proje Klasörü Aç…", self.open_project)
        fm.addAction("Çıkış", self.close)
        em = bar.addMenu("Düzenle")
        for a in (self.find_act, self.replace_act, self.goto_act, self.comment_act):
            em.addAction(a)
        rm = bar.addMenu("Çalıştır")
        rm.addAction(self.run_act)
        rm.addAction(self.stop_act)
        rm.addAction("Çıktıyı Temizle", lambda: self.output.clear())
        vm = bar.addMenu("Görünüm")
        vm.addAction(self.theme_act)
        vm.addAction("Dosya Ağacını Göster/Gizle", lambda: self.file_dock.setVisible(not self.file_dock.isVisible()))
        vm.addAction("Çıktı Panelini Göster/Gizle", lambda: self.output_dock.setVisible(not self.output_dock.isVisible()))
        hm = bar.addMenu("Yardım")
        hm.addAction("Hakkında", self.about)

    def make_toolbar(self):
        tb = QToolBar("Ana Araçlar")
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)
        for a in (self.new_act, self.open_act, self.save_act, self.saveas_act):
            tb.addAction(a)
        tb.addSeparator()
        tb.addAction(self.run_act)
        tb.addAction(self.stop_act)
        tb.addSeparator()
        tb.addAction(self.find_act)
        tb.addAction(self.theme_act)
        tb.addWidget(QLabel("  Python: "))
        self.python = QComboBox()
        self.python.setEditable(True)
        self.python.addItems(list(dict.fromkeys([sys.executable, "python3", "python"])))
        self.python.setMinimumWidth(190)
        tb.addWidget(self.python)

    def make_file_dock(self):
        self.file_dock = QDockWidget("Proje / Dosyalar", self)
        self.file_dock.setObjectName("fileDock")
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        row = QHBoxLayout()
        self.project_path = QLineEdit(self.last_dir)
        self.project_path.setReadOnly(True)
        choose = QPushButton("Klasör")
        choose.clicked.connect(self.open_project)
        row.addWidget(self.project_path, 1)
        row.addWidget(choose)
        layout.addLayout(row)
        self.fs_model = QFileSystemModel(self)
        self.fs_model.setRootPath(self.last_dir)
        self.fs_model.setNameFilters(["*.py", "*.pyw", "*.txt", "*.md", "*.json", "*.toml", "*.yaml", "*.yml", "*.ini", "*.html", "*.css", "*.js", "*.c", "*.cpp", "*.h", "*.sh"])
        self.fs_model.setNameFilterDisables(False)
        self.tree = QTreeView()
        self.tree.setModel(self.fs_model)
        self.tree.setRootIndex(self.fs_model.index(self.last_dir))
        for col in range(1, 4):
            self.tree.hideColumn(col)
        self.tree.doubleClicked.connect(self.open_tree_item)
        layout.addWidget(self.tree)
        self.file_dock.setWidget(panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.file_dock)
        self.file_dock.setMinimumWidth(220)

    def make_output_dock(self):
        self.output_dock = QDockWidget("Çalıştırma Çıktısı", self)
        self.output_dock.setObjectName("outputDock")
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        row = QHBoxLayout()
        self.output_status = QLabel("İşlem bekleniyor")
        clear = QPushButton("Temizle")
        clear.clicked.connect(lambda: self.output.clear())
        row.addWidget(self.output_status, 1)
        row.addWidget(clear)
        layout.addLayout(row)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("DejaVu Sans Mono", 10))
        layout.addWidget(self.output)
        self.output_dock.setWidget(panel)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.output_dock)
        self.output_dock.setMinimumHeight(170)

    def make_find_dock(self):
        self.find_dock = QDockWidget("Bul / Değiştir", self)
        self.find_dock.setObjectName("findDock")
        panel = QWidget()
        row = QHBoxLayout(panel)
        row.setContentsMargins(6, 4, 6, 4)
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Aranacak metin…")
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Yeni metin…")
        for text, fn in (("Önceki", lambda: self.find_text(True)),
                         ("Sonraki", lambda: self.find_text(False)),
                         ("Değiştir", self.replace_one), ("Tümünü Değiştir", self.replace_all)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
            if text == "Önceki":
                row.insertWidget(0, self.find_input)
            if text == "Değiştir":
                row.insertWidget(row.count()-1, self.replace_input)
        self.find_dock.setWidget(panel)
        self.addDockWidget(Qt.TopDockWidgetArea, self.find_dock)
        self.find_dock.hide()
        self.find_input.returnPressed.connect(lambda: self.find_text(False))

    def editors(self):
        return [self.tabs.widget(i) for i in range(self.tabs.count()) if isinstance(self.tabs.widget(i), CodeEditor)]

    def current_editor(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, CodeEditor) else None

    def new_file(self):
        ed = CodeEditor(self.dark)
        ed.textChanged.connect(self.update_titles)
        ed.cursorPositionChanged.connect(self.update_cursor_status)
        self.tabs.setCurrentIndex(self.tabs.addTab(ed, "Adsız"))
        ed.setFocus()

    def open_file(self, path=None):
        if not isinstance(path, str) or not path:
            path, _ = _fm.get_open_file_name(self, "Dosya Aç", self.last_dir,
                "Kaynak dosyaları (*.py *.pyw *.txt *.md *.json *.toml *.yaml *.yml *.ini *.html *.css *.js *.c *.cpp *.h *.sh);;Tüm dosyalar (*)", double_click="select")
        if not path:
            return
        path = str(Path(path).expanduser().resolve())
        for i in range(self.tabs.count()):
            ed = self.tabs.widget(i)
            if isinstance(ed, CodeEditor) and ed.file_path == path:
                self.tabs.setCurrentIndex(i)
                return
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            QMessageBox.critical(self, "Dosya açılamadı", str(exc))
            return
        ed = CodeEditor(self.dark)
        ed.file_path = path
        ed.setPlainText(text)
        ed.mark_saved()
        ed.textChanged.connect(self.update_titles)
        ed.cursorPositionChanged.connect(self.update_cursor_status)
        self.tabs.setCurrentIndex(self.tabs.addTab(ed, Path(path).name))
        self.last_dir = str(Path(path).parent)
        self.project_path.setText(self.last_dir)
        self.fs_model.setRootPath(self.last_dir)
        self.tree.setRootIndex(self.fs_model.index(self.last_dir))
        self.update_titles()
        self.statusBar().showMessage("Açıldı: " + path, 3000)

    def save_file(self):
        ed = self.current_editor()
        if not ed:
            return False
        if not ed.file_path:
            return self.save_as()
        try:
            Path(ed.file_path).write_text(ed.toPlainText(), encoding="utf-8")
            ed.mark_saved()
            self.update_titles()
            self.statusBar().showMessage("Kaydedildi: " + ed.file_path, 3000)
            return True
        except Exception as exc:
            QMessageBox.critical(self, "Kaydetme hatası", str(exc))
            return False

    def save_as(self):
        ed = self.current_editor()
        if not ed:
            return False
        path, _ = _fm.get_save_file_name(self, "Farklı Kaydet", ed.file_path or self.last_dir, "Python dosyası (*.py);;Tüm dosyalar (*)")
        if not path:
            return False
        if not Path(path).suffix:
            path += ".py"
        ed.file_path = str(Path(path).expanduser().resolve())
        self.last_dir = str(Path(ed.file_path).parent)
        return self.save_file()

    def update_titles(self, *_):
        for i in range(self.tabs.count()):
            ed = self.tabs.widget(i)
            if isinstance(ed, CodeEditor):
                name = Path(ed.file_path).name if ed.file_path else "Adsız"
                self.tabs.setTabText(i, ("● " if ed.modified() else "") + name)
                self.tabs.setTabToolTip(i, ed.file_path or "Kaydedilmemiş dosya")
        self.update_cursor_status()

    def close_tab(self, i):
        if i < 0 or i >= self.tabs.count():
            return
        ed = self.tabs.widget(i)
        if ed.modified():
            answer = QMessageBox.question(self, "Kaydedilmemiş değişiklikler",
                f"{self.tabs.tabText(i)} kaydedilmedi. Kaydetmek istiyor musunuz?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
            if answer == QMessageBox.Cancel:
                return
            if answer == QMessageBox.Save:
                self.tabs.setCurrentIndex(i)
                if not self.save_file():
                    return
        self.tabs.removeTab(i)
        ed.deleteLater()
        if self.tabs.count() == 0:
            self.new_file()

    def open_tree_item(self, index):
        path = self.fs_model.filePath(index)
        if os.path.isfile(path):
            self.open_file(path)

    def open_project(self):
        folder = _fm.get_existing_directory(self, "Proje klasörü seç", self.last_dir)
        if folder:
            self.last_dir = folder
            self.project_path.setText(folder)
            self.fs_model.setRootPath(folder)
            self.tree.setRootIndex(self.fs_model.index(folder))
            self.statusBar().showMessage("Proje açıldı: " + folder, 3000)

    def run_file(self):
        ed = self.current_editor()
        if not ed:
            return
        if ed.modified() and not self.save_file():
            return
        if not ed.file_path:
            QMessageBox.information(self, "Dosyayı kaydet", "Çalıştırmadan önce dosyayı kaydedin.")
            return
        if self.process and self.process.state() != QProcess.NotRunning:
            QMessageBox.warning(self, "Çalışan işlem", "Önce çalışan programı durdurun.")
            return
        python = self.python.currentText().strip() or sys.executable
        self.output.clear()
        self.output.appendPlainText(f"$ {python} -u {ed.file_path}\n")
        self.output_status.setText("Çalışıyor…")
        self.output_dock.show()
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(Path(ed.file_path).parent))
        self.process.setProgram(python)
        self.process.setArguments(["-u", ed.file_path])
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.process_finished)
        self.process.errorOccurred.connect(self.process_error)
        self.process.start()

    def read_output(self):
        if self.process:
            data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
            if data:
                self.output.moveCursor(QTextCursor.End)
                self.output.insertPlainText(data)
                self.output.moveCursor(QTextCursor.End)

    def process_finished(self, code, status):
        self.read_output()
        message = "başarıyla tamamlandı" if code == 0 else f"hata kodu: {code}"
        self.output.appendPlainText(f"\n[Program {message}]")
        self.output_status.setText(message.capitalize())
        self.process = None

    def process_error(self, error):
        if self.process:
            self.output.appendPlainText("\n[Başlatma hatası] " + self.process.errorString())
            self.output_status.setText("Başlatılamadı")

    def stop_process(self):
        if self.process and self.process.state() != QProcess.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(1000):
                self.process.kill()
            self.output.appendPlainText("\n[İşlem durduruldu]")
            self.output_status.setText("Durduruldu")
            self.process = None

    def show_find(self):
        self.find_dock.show()
        self.find_dock.raise_()
        self.find_input.setFocus()
        self.find_input.selectAll()

    def find_text(self, backwards=False):
        ed = self.current_editor()
        term = self.find_input.text()
        if not ed or not term:
            return
        flags = QTextDocument.FindBackward if backwards else QTextDocument.FindFlags()
        if not ed.find(term, flags):
            cursor = ed.textCursor()
            cursor.movePosition(QTextCursor.End if backwards else QTextCursor.Start)
            ed.setTextCursor(cursor)
            if not ed.find(term, flags):
                self.statusBar().showMessage("Metin bulunamadı.", 2500)

    def replace_one(self):
        ed = self.current_editor()
        if not ed:
            return
        cursor = ed.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self.find_input.text():
            cursor.insertText(self.replace_input.text())
        self.find_text(False)

    def replace_all(self):
        ed = self.current_editor()
        term = self.find_input.text()
        if not ed or not term:
            return
        text = ed.toPlainText()
        count = text.count(term)
        if count:
            ed.setPlainText(text.replace(term, self.replace_input.text()))
            self.statusBar().showMessage(f"{count} eşleşme değiştirildi.", 3000)
        else:
            self.statusBar().showMessage("Metin bulunamadı.", 2500)

    def goto_line(self):
        ed = self.current_editor()
        if not ed:
            return
        line, ok = QInputDialog.getInt(self, "Satıra Git", "Satır numarası:", 1, 1, max(1, ed.blockCount()))
        if ok:
            ed.setTextCursor(QTextCursor(ed.document().findBlockByNumber(line - 1)))
            ed.setFocus()

    def toggle_comment(self):
        ed = self.current_editor()
        if not ed:
            return
        cursor = ed.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        c = QTextCursor(ed.document())
        c.setPosition(start)
        c.movePosition(QTextCursor.StartOfBlock)
        first = c.blockNumber()
        c.setPosition(end)
        c.movePosition(QTextCursor.StartOfBlock)
        last = c.blockNumber()
        blocks = [ed.document().findBlockByNumber(n) for n in range(first, last + 1)]
        nonempty = [b.text() for b in blocks if b.text().strip()]
        uncomment = bool(nonempty) and all(t.lstrip().startswith("#") for t in nonempty)
        cursor.beginEditBlock()
        for block in reversed(blocks):
            c = QTextCursor(block)
            c.movePosition(QTextCursor.StartOfBlock)
            if uncomment:
                pos = len(block.text()) - len(block.text().lstrip())
                c.movePosition(QTextCursor.Right, QTextCursor.MoveAnchor, pos)
                if c.block().text()[pos:pos+1] == "#":
                    c.deleteChar()
                    if c.block().text()[pos:pos+1] == " ":
                        c.deleteChar()
            elif block.text().strip():
                c.insertText("# ")
        cursor.endEditBlock()

    def update_cursor_status(self, *_):
        if not hasattr(self, "cursor_label"):
            return
        ed = self.current_editor()
        if ed:
            c = ed.textCursor()
            self.cursor_label.setText(f"Satır {c.blockNumber()+1}, Sütun {c.positionInBlock()+1}")

    def toggle_theme(self):
        self.dark = not self.dark
        self.apply_theme()
        for ed in self.editors():
            ed.dark = self.dark
            ed.highlighter = PythonHighlighter(ed.document(), self.dark)
            ed.update_style()

    def apply_theme(self):
        self.setStyleSheet(DARK if self.dark else LIGHT)
        if hasattr(self, "output"):
            self.output.setStyleSheet(
                "QPlainTextEdit{background:#11141a;color:#c8d3e4;border:0;padding:6px}" if self.dark
                else "QPlainTextEdit{background:#fff;color:#20232b;border:0;padding:6px}"
            )

    def tab_menu(self, pos):
        menu = QMenu(self)
        menu.addAction("Kaydet", self.save_file)
        menu.addAction("Sekmeyi Kapat", lambda: self.close_tab(self.tabs.currentIndex()))
        menu.exec_(self.tabs.mapToGlobal(pos))

    def autosave_recovery(self):
        try:
            recovery = {}
            for i, ed in enumerate(self.editors()):
                if ed.modified():
                    recovery[str(i)] = {"path": ed.file_path, "text": ed.toPlainText()}
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            (CONFIG_DIR / "recovery.json").write_text(json.dumps(recovery, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def restore_session(self):
        for path in self.settings.get("open_files", []):
            if path and Path(path).is_file():
                self.open_file(path)
        if self.tabs.count() > 1:
            self.tabs.setCurrentIndex(min(self.settings.get("active_index", 0), self.tabs.count()-1))

    def about(self):
        QMessageBox.about(self, "Hakkında",
            "<h2>PyStudio X</h2><p>PyQt5 ile hazırlanmış Python geliştirme ortamı.</p>"
            "<ul><li>Sekmeli editör ve sözdizimi renklendirme</li><li>Proje dosya ağacı</li>"
            "<li>Python çalıştırma/durdurma ve çıktı paneli</li><li>Bul, değiştir ve satıra git</li>"
            "<li>Koyu/açık tema, oturum ayarları ve kurtarma taslağı</li></ul>"
            "<p>Bu sürüm temel IDE özelliklerini içerir; tam teşekküllü hata ayıklayıcı içermez.</p>")

    def closeEvent(self, event):
        for i in range(self.tabs.count()-1, -1, -1):
            ed = self.tabs.widget(i)
            if ed.modified():
                self.tabs.setCurrentIndex(i)
                answer = QMessageBox.question(self, "Kaydedilmemiş değişiklikler",
                    f"{self.tabs.tabText(i)} kaydedilmedi. Kaydetmek istiyor musunuz?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
                if answer == QMessageBox.Cancel:
                    event.ignore()
                    return
                if answer == QMessageBox.Save and not self.save_file():
                    event.ignore()
                    return
        self.stop_process()
        self.save_settings()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP)
    app.setStyle("Fusion")
    window = PyStudio()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
