import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QSplitter
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QIcon
from pathlib import Path

from arduino_panel import ArduinoPanel
from chiller_panel import ChillerPanel
from hv_panel import HVPanel
from lv_panel import LVPanel

MAIN_DIR = Path(__file__).parent.parent
gui_dir = MAIN_DIR / "GUI"
sys.path.append(str(gui_dir))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("ETL Testing GUI")
        self.setFixedSize(QSize(1500, 1000))
        self.setStyleSheet("background-color: #3b3b3b;")
        self.setWindowIcon(QIcon(str(gui_dir / "icon.png")))

        # ----- Build panels -----
        self.ard = ArduinoPanel()
        self.chill = ChillerPanel()
        self.hv = HVPanel()
        self.lv = LVPanel()    

        # ----- Left column: vertical splitter (Arduino / Chiller / HV / LV) -----
        self.left_split = QSplitter(Qt.Vertical)
        self.left_split.addWidget(self.ard)
        self.left_split.addWidget(self.chill)
        self.left_split.addWidget(self.hv)
        self.left_split.addWidget(self.lv)

        self.left_split.setHandleWidth(6)    

        # ----- Right column: vertical splitter (Module Testing) -----
        self.right_split = QSplitter(Qt.Vertical)
        self.right_split.setHandleWidth(6)


        # ----- Main: horizontal splitter (Left column / Right column) -----
        self.main_split = QSplitter(Qt.Horizontal)
        self.main_split.addWidget(self.left_split)
        self.main_split.addWidget(self.right_split)
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
        total_w = self.centralWidget().width()
        self.main_split.setSizes([total_w // 2, total_w // 2])

        # Left split: Arduino/Chiller/HV equal heights 1:1:1
        total_h_left = self.left_split.height() or (self.height() - 32)
        left_num = 4
        lefth = total_h_left // left_num
        self.left_split.setSizes([lefth, lefth, lefth, lefth])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(gui_dir / "icon.png")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
