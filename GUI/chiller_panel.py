import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout, QFrame,
    QPushButton, QLabel, QSizePolicy, QLineEdit, QHBoxLayout, QFormLayout, QVBoxLayout
)
from pathlib import Path
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QFont
from panel import Panel
import threading
import serial
import time
import os

MAIN_DIR = Path(__file__).parent.parent
chill_dir = MAIN_DIR / "drivers" / "Chiller"
sys.path.append(str(chill_dir))

from chiller import JULABO

class ChillerPanel(Panel):
    def __init__(self, title="Chiller"):
        super().__init__(title)
        self.setObjectName("ChillerPanel")
        self.setStyleSheet("""
        #HVPanel QWidget { color: #ffffff; }
        QLabel { color: #ffffff; }

        QLineEdit, QPlainTextEdit {
            color: #ffffff;
            border: 1px solid #ffffff;
            border-radius: 6px;
            padding: 4px 6px;
            selection-background-color: #2563eb;
            selection-color: #ffffff;
        }

        QPushButton {
            color: #ffffff;
            border: none;
            border-radius: 10px;
            padding: 8px 14px;
            font-weight: 600;
        }
        QPushButton:disabled { color: #9aa5b1; }

        QPushButton#greenButton {
            background-color: #16a34a;
            color: #ffffff;
        }
        QPushButton#greenButton:hover { background-color: #22c55e; }
        QPushButton#greenButton:pressed { background-color: #15803d; }
        QPushButton#greenButton:disabled { background-color: #14532d; color: #9aa5b1;}


        QPushButton#redButton {
            background-color: #e53935;
            color: #ffffff;
        }
        QPushButton#redButton:hover { background-color: #ef5350; }
        QPushButton#redButton:pressed { background-color: #c62828; }
        QPushButton#redButton:disabled { background-color: #7f1d1d; color: #9aa5b1;}
                           
        QPushButton#blueButton {
            background-color: #007bff;
            color: #ffffff;
        }
        QPushButton#blueButton:hover { background-color: #339cff; }
        QPushButton#blueButton:pressed { background-color: #0056b3; }
        """)

        self.chiller_stop_evt = None
        self.chiller_thread = None
        self.log_status = False
        self.log_timestamp = None

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("greenButton")
        self.btn_connect.clicked.connect(self.start_chiller)
        self.btn_connect.setEnabled(True)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setObjectName("redButton")
        self.btn_disconnect.clicked.connect(self.stop_chiller)
        self.btn_disconnect.setEnabled(False)

        self.lbl_status = QLabel("Disconnected")

        self.btn_logging = QPushButton("Toggle Logging")
        self.btn_logging.setObjectName("blueButton")
        self.btn_logging.clicked.connect(self.toggle_log)
        self.lbl_logging = QLabel("Not Logging")

        button_row = QHBoxLayout()
        button_row.addWidget(self.btn_connect)
        button_row.addWidget(self.btn_disconnect)
        button_row.addWidget(self.lbl_status, 1, Qt.AlignLeft)
        button_row.addStretch(1)
        button_row.addWidget(self.btn_logging)
        button_row.addWidget(self.lbl_logging, 1, Qt.AlignLeft)

        def make_label(text):
            lbl = QLabel(text)
            lbl.setFont(QFont("Calibri", 15))
            return lbl
        
        label_row = QHBoxLayout()

        self.lbl_power = make_label("Power: ---")
        self.lbl_set_temp = make_label("Set Temp: --- °C")
        self.lbl_curr_temp = make_label("Current Temp: --- °C")

        label_row.addWidget(self.lbl_power)
        label_row.addWidget(self.lbl_set_temp)
        label_row.addWidget(self.lbl_curr_temp)

        input_row = QHBoxLayout()

        self.lbl_power_toggle = make_label("Power: ")
        self.btn_power_on = QPushButton("ON")
        self.btn_power_on.setObjectName("greenButton")
        self.btn_power_on.clicked.connect(self.power_on)
        self.btn_power_off = QPushButton("OFF")
        self.btn_power_off.setObjectName("redButton")
        self.btn_power_off.clicked.connect(self.power_off)
        self.btn_power_on.setEnabled(False)
        self.btn_power_off.setEnabled(False)
        self.lbl_set_temp_input = make_label("Set Temp (°C): ")
        self.input_set_temp = QLineEdit()
        self.input_set_temp.setFixedSize(60, 30)
        self.btn_set_temp = QPushButton("Set")
        self.btn_set_temp.setObjectName("blueButton")
        self.btn_set_temp.clicked.connect(self.set_temperature)
        input_row.addWidget(self.lbl_power_toggle)
        input_row.addWidget(self.btn_power_on)
        input_row.addWidget(self.btn_power_off)
        input_row.addWidget(self.lbl_set_temp_input)
        input_row.addWidget(self.input_set_temp)
        input_row.addWidget(self.btn_set_temp)
        input_row.addStretch(1)

        layout = QVBoxLayout()
        layout.addLayout(button_row)
        layout.addLayout(label_row)
        layout.addLayout(input_row)
        layout.addStretch(1)

        self.subgrid.addLayout(layout, 1, 0, 5, 3)
        self.sample_time = 1.0
        self.cmd_waiting = False

    def start_chiller(self):
        if self.chiller_thread != None:
            print("Chiller thread already running")
            return
        
        self.chiller_stop_evt = threading.Event()
        try:
            self.chiller = JULABO("/dev/chiller", baud=4800)
            self.lbl_status.setText("Connected")
        except serial.SerialException as e:
            print(f"Failed to connect: {e}")
        
        self.chiller_stop_evt.clear()
        self.chiller_thread = threading.Thread(target=self.chiller_run, daemon=True)
        self.chiller_thread.start()
        self.btn_disconnect.setEnabled(True)
        self.btn_connect.setEnabled(False)
        time.sleep(self.sample_time)
    
    def stop_chiller(self):
        if self.chiller_thread == None:
            print("Chiller thread not running")
            return
        
        self.chiller_stop_evt.set()
        if self.chiller_thread:
            self.chiller_thread.join()
            self.chiller_thread = None
        if self.chiller:
            self.chiller.close()
            self.lbl_status.setText("Disconnected")
            self.lbl_power.setText("Power: ---")
            self.lbl_set_temp.setText("Set Temp: --- °C")
            self.lbl_curr_temp.setText("Current Temp: --- °C")
            self.btn_disconnect.setEnabled(False)
            self.btn_connect.setEnabled(True)

    def power_on(self):
        if self.chiller:
            self.chiller.set_power_on()
    
    def power_off(self):
        if self.chiller:
            self.chiller.set_power_off()
        
    def set_temperature(self):
        if self.chiller:
            self.cmd_waiting = True

    def chiller_run(self):
        while not self.chiller_stop_evt.is_set():
            if not self.cmd_waiting:
                try:
                    self.curr_temp = self.chiller.get_temperature()
                    self.set_temp = self.chiller.get_work_temperature()
                    self.lbl_curr_temp.setText(f"Current Temp: {self.curr_temp:.2f} °C")
                    self.lbl_set_temp.setText(f"Set Temp: {self.set_temp:.2f} °C")
                    self.power = self.chiller.get_power().strip()
                    if self.power == '1':
                        self.lbl_power.setText("Power: ON")
                        self.btn_power_on.setEnabled(False)
                        self.btn_power_off.setEnabled(True)
                    else:
                        self.lbl_power.setText("Power: OFF")
                        self.btn_power_on.setEnabled(True)
                        self.btn_power_off.setEnabled(False)
                    
                    if self.log_status:
                        timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
                        maindir = Path(__file__).parent.parent

                        resultdir = maindir / "Environmental Data" / "Chiller Data"
                        if not os.path.isdir(resultdir):
                            os.makedirs(resultdir)

                        resultdir.mkdir(exist_ok=True)

                        outfile = resultdir / f"chiller_data_{self.log_timestamp}.csv"

                        data = {"Power": self.power.strip(), "Set Temp (°C)": self.set_temp, "Curr Temp (°C)": self.curr_temp}
                        with open(outfile, 'a') as f:
                            f.write(f"{timestamp}: {data}\n")

                except Exception as e:
                    print(f"Error reading chiller data: {e}")
            else:
                self.cmd_waiting = False
                temp = float(self.input_set_temp.text())
                self.chiller.set_work_temperature(temp)
                self.input_set_temp.clear()

            time.sleep(self.sample_time)

    def toggle_log(self):
        self.log_status = not self.log_status
        if self.log_status:
            self.lbl_logging.setText("Logging")
            self.log_timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
        else:
            self.lbl_logging.setText("Not Logging")