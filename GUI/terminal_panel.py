import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QFrame,
    QPushButton, QLabel, QSizePolicy
)
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont
from panel import Panel

class TerminalPanel(Panel):
    def __init__(self, title="Terminal"):
        super().__init__(title)

        self.subgrid.setColumnStretch(0, 1)
        self.subgrid.setRowStretch(1, 1)