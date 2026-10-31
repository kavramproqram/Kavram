# Kavram - terminal: sistem terminali arayüzü (komutları sphere/sphere.py işler)
from PyQt5.QtWidgets import QTextEdit, QDialog, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QTextCursor


class TerminalTextEdit(QTextEdit):
    commandEntered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Komut girin...")
        self.history = []
        self.history_index = len(self.history)
        self.last_temp_command = ""

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() == Qt.NoModifier:
                command = self.toPlainText().strip()
                if command:
                    self.commandEntered.emit(command)
                    if command not in self.history:
                         self.history.append(command)
                    self.history_index = len(self.history)
                    self.last_temp_command = ""
                return

        elif event.key() == Qt.Key_Up:
            if self.history:
                if self.history_index == len(self.history):
                    self.last_temp_command = self.toPlainText()
                self.history_index -= 1
                if self.history_index < 0:
                    self.history_index = len(self.history) - 1
                self.setPlainText(self.history[self.history_index])
                self.moveCursorToEnd()
            return

        elif event.key() == Qt.Key_Down:
            if self.history:
                self.history_index += 1
                if self.history_index >= len(self.history):
                    self.history_index = 0
                self.setPlainText(self.history[self.history_index])
                self.moveCursorToEnd()
            return

        super().keyPressEvent(event)

    def moveCursorToEnd(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)

class TerminalDialog(QDialog):
    commandEntered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Terminal")
        self.setStyleSheet("""
            QDialog {
                background-color: #222;
                border: 1px solid #555;
            }
            QLabel {
                color: #aaa;
                font-family: monospace;
            }
        """)
        self.resize(600, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.terminal_text = TerminalTextEdit(self)
        self.terminal_text.setStyleSheet("""
            QTextEdit {
                background-color: #111;
                color: #ddd;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                border: 1px solid #444;
                padding: 5px;
            }
            QTextEdit:focus {
                border: 1px solid #666;
            }
        """)
        self.terminal_text.setFocusPolicy(Qt.StrongFocus)
        self.terminal_text.setFocus()
        self.terminal_text.commandEntered.connect(self.handleCommand)
        layout.addWidget(self.terminal_text)

        self.setLayout(layout)

    def handleCommand(self, cmd):
        self.commandEntered.emit(cmd)
        self.terminal_text.clear()
