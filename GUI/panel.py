from PyQt5.QtWidgets import QFrame, QLabel, QGridLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class Panel(QFrame):
    def __init__(self, title):
        super().__init__()

        self.setFrameShape(QFrame.Panel)
        self.setFrameShadow(QFrame.Raised)
        self.setLineWidth(15)
        self.setStyleSheet("background-color: #3b3b3b;")

        subgrid = QGridLayout(self)
        subgrid.setContentsMargins(8,8,8,8)
        subgrid.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        title_lbl.setStyleSheet("""
                                font-weight: 600;
                                color: #eeeeee;
                                """)
        title_lbl.setFont(QFont("Calibri", 15))
        subgrid.addWidget(title_lbl, 0, 0, 1, -1, alignment=Qt.AlignHCenter)

        self.subgrid = subgrid
