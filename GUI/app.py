import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, QSize

from arduino_panel import ArduinoPanel
from tamalero_panel import TamaleroPanel
from chiller_panel import ChillerPanel
from results_panel import ResultsPanel
from hv_panel import HVPanel   


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ETL Testing GUI")
        self.setFixedSize(QSize(1500, 1200))
        self.setStyleSheet("background-color: #3b3b3b;")

        # ----- Build panels -----
        self.ard = ArduinoPanel()
        self.chill = ChillerPanel()
        self.hv = HVPanel()         
        self.tam = TamaleroPanel()
        self.term = ResultsPanel()

        # ----- Left column: vertical splitter (Arduino / Chiller / HV) -----
        self.left_split = QSplitter(Qt.Vertical)
        self.left_split.addWidget(self.ard)
        self.left_split.addWidget(self.chill)
        self.left_split.addWidget(self.hv)          
        self.left_split.setChildrenCollapsible(False)
        self.left_split.setHandleWidth(6)
        # Equal stretch so they split 1:1:1
        self.left_split.setStretchFactor(0, 1)
        self.left_split.setStretchFactor(1, 1)
        self.left_split.setStretchFactor(2, 1)      

        # ----- Right column: vertical splitter (Tamalero / Terminal) -----
        self.right_split = QSplitter(Qt.Vertical)
        self.right_split.addWidget(self.tam)
        self.right_split.addWidget(self.term)
        self.right_split.setChildrenCollapsible(False)
        self.right_split.setHandleWidth(6)
        # Keep ~7:3 ratio
        self.right_split.setStretchFactor(0, 7)
        self.right_split.setStretchFactor(1, 3)

        # ----- Main: horizontal splitter (Left column / Right column) -----
        self.main_split = QSplitter(Qt.Horizontal)
        self.main_split.addWidget(self.left_split)
        self.main_split.addWidget(self.right_split)
        self.main_split.setChildrenCollapsible(False)
        self.main_split.setHandleWidth(8)
        self.main_split.setStretchFactor(0, 4)      
        self.main_split.setStretchFactor(1, 6)      

        # ----- Central widget & margins -----
        container = QWidget()
        root = QHBoxLayout(container)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(self.main_split)
        self.setCentralWidget(container)

        QTimer.singleShot(0, self._init_split_sizes)

    def _init_split_sizes(self):
        # Main split initial widths ~ 3:7
        total_w = self.centralWidget().width()
        left_w = int(total_w * 0.3)
        right_w = total_w - left_w
        self.main_split.setSizes([left_w, right_w])

        # Left split: Arduino/Chiller/HV equal heights 1:1:1
        total_h_left = self.left_split.height() or (self.height() - 32)
        unit = total_h_left // 5
        h2 = int(2 * unit)
        h1 = int(1 * unit)
        self.left_split.setSizes([h1, h2, total_h_left - 2*(h1 + h2)])

        # Right split: Tamalero/Terminal ~ 7:3
        total_h_right = self.right_split.height() or (self.height() - 32)
        h7 = int(total_h_right * 0.7)
        h3 = total_h_right - h7
        self.right_split.setSizes([h7, h3])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
