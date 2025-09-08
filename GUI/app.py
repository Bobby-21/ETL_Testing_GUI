import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QFrame,
    QPushButton, QLabel
)
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont
from panel import Panel
from arduino_panel import ArduinoPanel
from tamalero_panel import TamaleroPanel
from chiller_panel import ChillerPanel
from terminal_panel import TerminalPanel

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("ETL Testing GUI")
        self.setFixedSize(QSize(1500, 1000))
        self.setStyleSheet("background-color: #3b3b3b;")

        grid = QGridLayout()
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(8)

        ard = ArduinoPanel()
        tam = TamaleroPanel()
        chill = ChillerPanel()
        term = TerminalPanel()

        grid.addWidget(ard, 0, 0)
        grid.addWidget(tam, 0, 1)
        grid.addWidget(chill, 1, 0)
        grid.addWidget(term, 1, 1)

        widget = QWidget()
        widget.setLayout(grid)
        self.setCentralWidget(widget)

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()
