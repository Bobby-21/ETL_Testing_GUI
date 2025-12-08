import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStyleFactory, QWidget, QHBoxLayout, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon

from arduino_panel import ArduinoPanel
#from tamalero_panel import TamaleroPanel
from chiller_panel import ChillerPanel
#from results_panel import ResultsPanel
from hv_panel import HVPanel   


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ETL Testing GUI")
        self.setFixedSize(QSize(1500, 1000))
        self.setStyleSheet("background-color: #3b3b3b;")

        # ----- Build panels -----
        self.ard = ArduinoPanel()
        self.chill = ChillerPanel()
        self.hv = HVPanel()         
        #self.tam = TamaleroPanel()
        #self.term = ResultsPanel()

        # ----- Left column: vertical splitter (Arduino / Chiller / HV) -----
        self.left_split = QSplitter(Qt.Vertical)
        self.left_split.addWidget(self.ard)
        self.left_split.addWidget(self.chill)
        self.left_split.addWidget(self.hv)
        self.left_split.setHandleWidth(6)    

        # ----- Right column: vertical splitter (Tamalero / Terminal) -----
        self.right_split = QSplitter(Qt.Vertical)
        #self.right_split.addWidget(self.tam)
        #self.right_split.addWidget(self.term)
        self.right_split.setHandleWidth(6)
        # Keep ~7:3 ratio

        # ----- Main: horizontal splitter (Left column / Right column) -----
        self.main_split = QSplitter(Qt.Horizontal)
        self.main_split.addWidget(self.left_split)
        #self.main_split.addWidget(self.tam)
        self.main_split.setHandleWidth(6)

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
        lefth = total_h_left // 3
        self.left_split.setSizes([lefth, lefth, lefth])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("./cat.jpg"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
