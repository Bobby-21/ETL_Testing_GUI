import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QFrame,
    QPushButton, QLabel, QSizePolicy
)
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont
from panel import Panel

class ArduinoPanel(Panel):
    def __init__(self, title="Arduino"):
        super().__init__(title)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: green;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #228B22;
            }
            QPushButton:pressed {
                background-color: #006400;
            }
        """)
        self.connect_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setStyleSheet("""
            QPushButton {
                background-color: red;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #8B0000;
            }
        """)
        self.disconnect_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        serialstatus = "Disconnected"  # Placeholder for actual status
        self.serialstatus_lbl = QLabel(f"Serial: {serialstatus}")
        self.serialstatus_lbl.setStyleSheet("""
            font-weight: 600;
            color: #eeeeee;
            padding: 10px;
        """)

        ambtemp = 24.2  # Placeholder for ambient temperature
        self.ambtemp_lbl = QLabel(f"Ambient Temp: {ambtemp}°C")
        self.ambtemp_lbl.setStyleSheet("""
            font-weight: 600;
            color: #eeeeee;
            padding: 10px;
        """)
        
        rH = 45.3  # Placeholder for relative humidity
        self.rH_lbl = QLabel(f"Relative Humidity: {rH}%")
        self.rH_lbl.setStyleSheet("""
            font-weight: 600;
            color: #eeeeee;
            padding: 10px;
        """)

        door_status = "Closed"  # Placeholder for door status
        self.door_lbl = QLabel(f"Door: {door_status}")
        self.door_lbl.setStyleSheet("""
            font-weight: 600;
            color: #eeeeee;
            padding: 10px;
        """)

        leak_status = "No Leak"  # Placeholder for leak status
        self.leak_lbl = QLabel(f"Leak: {leak_status}")
        self.leak_lbl.setStyleSheet("""
            font-weight: 600;
            color: #eeeeee;
            padding: 10px;
        """)

        TC1_temp = 22.5  # Placeholder for TC1 temperature
        self.TC1_lbl = QLabel(f"TC1 Temp: {TC1_temp}°C")
        self.TC1_lbl.setStyleSheet("""
            font-weight: 600;
            color: #eeeeee;
            padding: 10px;
        """)

        TC1_fault = "OK"  # Placeholder for TC1 fault status
        self.TC1_fault_lbl = QLabel(f"TC1 Faults: {TC1_fault}")
        self.TC1_fault_lbl.setStyleSheet("""
            font-weight: 600;
            color: #eeeeee;
            padding: 10px;
        """)

        TC2_temp = 23.1  # Placeholder for TC2 temperature
        self.TC2_lbl = QLabel(f"TC2 Temp: {TC2_temp}°C")
        self.TC2_lbl.setStyleSheet("""
            font-weight: 600;
            color: #eeeeee;
            padding: 10px;
        """)

        TC2_fault = "OK"  # Placeholder for TC2 fault status
        self.TC2_fault_lbl = QLabel(f"TC2 Faults: {TC2_fault}")
        self.TC2_fault_lbl.setStyleSheet("""
            font-weight: 600;
            color: #eeeeee;
            padding: 10px;
        """)

        dewpoint = 12.3  # Placeholder for dewpoint
        self.dewpoint_lbl = QLabel(f"Dew Point: {dewpoint}°C")
        self.dewpoint_lbl.setStyleSheet("""
            font-weight: 600;
            color: #eeeeee;
            padding: 10px;
        """)

        dhtstatus = "OK"  # Placeholder for DHT status
        self.dhtstatus_lbl = QLabel(f"DHT Status: {dhtstatus}")
        self.dhtstatus_lbl.setStyleSheet("""
            font-weight: 600;
            color: #eeeeee;
            padding: 10px;
        """)

        self.subgrid.setColumnStretch(0, 1)
        self.subgrid.addWidget(self.connect_btn, 1, 1)
        self.subgrid.addWidget(self.disconnect_btn, 1, 2)
        self.subgrid.addWidget(self.serialstatus_lbl, 1, 3)
        self.subgrid.setColumnStretch(4, 1)

        self.subgrid.addWidget(self.ambtemp_lbl, 2, 3)
        self.subgrid.addWidget(self.rH_lbl, 3, 3)
        self.subgrid.addWidget(self.dewpoint_lbl, 2, 4)
        self.subgrid.addWidget(self.dhtstatus_lbl, 3, 4)
        self.subgrid.addWidget(self.door_lbl, 4, 3)
        self.subgrid.addWidget(self.leak_lbl, 4, 4)
        self.subgrid.addWidget(self.TC1_lbl, 5, 3)
        self.subgrid.addWidget(self.TC1_fault_lbl, 5, 4)
        self.subgrid.addWidget(self.TC2_lbl, 6, 3)
        self.subgrid.addWidget(self.TC2_fault_lbl, 6, 4)
        self.subgrid.setRowStretch(7, 1)