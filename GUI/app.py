import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, QSize
from arduino_panel import ArduinoPanel
from tamalero_panel import TamaleroPanel
from chiller_panel import ChillerPanel
from results_panel import ResultsPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ETL Testing GUI")
        self.setFixedSize(QSize(1500, 1000))          # keep your fixed size; users can still drag splitters
        self.setStyleSheet("background-color: #3b3b3b;")

        # ----- Build panels -----
        self.ard = ArduinoPanel()
        self.chill = ChillerPanel()
        self.tam = TamaleroPanel()
        self.term = ResultsPanel()

        # ----- Left column: vertical splitter (Arduino / Chiller) -----
        self.left_split = QSplitter(Qt.Vertical)
        self.left_split.addWidget(self.ard)
        self.left_split.addWidget(self.chill)
        self.left_split.setChildrenCollapsible(False)
        self.left_split.setHandleWidth(6)
        # Equal stretch so they split evenly when window resizes
        self.left_split.setStretchFactor(0, 1)
        self.left_split.setStretchFactor(1, 1)

        # ----- Right column: vertical splitter (Tamalero / Terminal) -----
        self.right_split = QSplitter(Qt.Vertical)
        self.right_split.addWidget(self.tam)
        self.right_split.addWidget(self.term)
        self.right_split.setChildrenCollapsible(False)
        self.right_split.setHandleWidth(6)
        # 8:2 stretch so resizing keeps the ratio roughly 7:3
        self.right_split.setStretchFactor(0, 7)
        self.right_split.setStretchFactor(1, 3)

        # ----- Main: horizontal splitter (Left column / Right column) -----
        self.main_split = QSplitter(Qt.Horizontal)
        self.main_split.addWidget(self.left_split)
        self.main_split.addWidget(self.right_split)
        self.main_split.setChildrenCollapsible(False)
        self.main_split.setHandleWidth(8)
        # Keep columns resizing proportionally (1:1 by default; change to 2:3 etc. if you prefer)
        self.main_split.setStretchFactor(0, 1)
        self.main_split.setStretchFactor(1, 1)

        # ----- Central widget & margins -----
        container = QWidget()
        root = QHBoxLayout(container)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(self.main_split)
        self.setCentralWidget(container)

        # Set initial pixel sizes after the window is shown, so the ratio applies immediately.
        # (Stretch factors handle subsequent resizes.)
        QTimer.singleShot(0, self._init_split_sizes)

    def _init_split_sizes(self):
        # Main split: left/right initial widths (tweak as you like)
        total_w = self.centralWidget().width()
        self.main_split.setSizes([total_w // 2, total_w // 2])

        # Left split: Arduino/Chiller equal heights
        total_h_left = self.left_split.height() or (self.height() - 32)
        self.left_split.setSizes([total_h_left // 2, total_h_left // 2])

        # Right split: Tamalero/Terminal at 8:2 ratio
        total_h_right = self.right_split.height() or (self.height() - 32)
        h8 = int(total_h_right * 0.8)
        h2 = total_h_right - h8
        self.right_split.setSizes([h8, h2])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
