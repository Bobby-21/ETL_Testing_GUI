import serial
import time
import numpy as np

class Arduino:
    def __init__(self, port, baudrate, timeout):
        self.port = port
        self.baud = baudrate
        self.timeout = timeout
        self.ser = None

        self.ambtemp = None
        self.rH = None
        self.dhtstatus = None
        self.door = None
        self.leak = None
        self.TCtemps = [None, None]
        self.TCfaults = [None, None]
        self.TCFaultNames= [
            "Open Circuit",   # bit 0
            "TC Voltage OOR", # bit 1
            "TC Temp Low",    # bit 2
            "TC Temp High",   # bit 3
            "CJ Temp Low",    # bit 4
            "CJ Temp High",   # bit 5
            "TC Temp OOR",    # bit 6
            "CJ Temp OOR",    # bit 7
        ]

        self.dewpoint = None

        self.is_connected = False

    def connect(self):
        self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        return self.ser.is_open
    
    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        else:
            raise RuntimeError("Serial not open, call connect() first")
        
    def check_serial_connected(self):
        if self.ser and self.ser.is_open:
            self.is_connected = True
            return self.is_connected
        else:
            self.is_connected = False
            return self.is_connected
    
    def send(self, cmd):
        if self.ser and self.ser.is_open:
            self.ser.reset_input_buffer()
            self.ser.write((cmd + "\n").encode())
            self.ser.flush()
            line = self.ser.readline().decode().strip()
            return line
        else:
            raise RuntimeError("Serial not open, call connect() first")

    def restart_dht(self):
        response = self.send("RestartDHT")
        self.dhtstatus = bool(response)
        return self.dhtstatus
    
    def get_data(self):
        # DATA, door, leak, TCtemp1, TCfault1, TCtemp2, TCfault2, ambtemp, rH, dhtstatus, DONE
        response = self.send("GetData")
        data_list = response.split(",")
        if data_list[0] == "DATA" and data_list[-1] == "DONE":
            
            self.door = bool(float(data_list[1]))
            self.leak = bool(float(data_list[2]))

            self.TCtemps = [float(data_list[3]), float(data_list[5])]
            TC1faultbyte = int(data_list[4])
            TC2faultbyte = int(data_list[6])
            if TC1faultbyte == 0:
                self.TCfaults[0] = "No Faults"
            else:
                self.TCfaults[0] = [name for i, name in enumerate(self.TCFaultNames) if (TC1faultbyte & (1 << i))].join(", ")

            if TC2faultbyte == 0:
                self.TCfaults[1] = "No Faults"
            else:
                self.TCfaults[1] = [name for i, name in enumerate(self.TCFaultNames) if (TC2faultbyte & (1 << i))].join(", ")

            self.ambtemp = float(data_list[7])
            self.rH = float(data_list[8])
            self.dhtstatus = bool(float(data_list[9]))
            
            b = 17.625
            c = 243.04
            gamma = np.log(self.rH/100) + (b*self.ambtemp)/(c + self.ambtemp)
            self.dewpoint = round((c*gamma)/(b-gamma), 2)
    
            if self.ser and self.ser.is_open:
                self.is_connected = True
            else:
                self.is_connected = False
        
        elif data_list[0] == "DATA" and data_list[-1] != "DONE":
            print("Partial data received")
            print(data_list)
            # Assume door and leak are always sent (digital reads, should never be missing)
            last_index = len(data_list) - 2
            self.door = bool(float(data_list[1]))
            self.leak = bool(float(data_list[2]))

            if last_index >= 3:
                self.TCtemps[0] = float(data_list[3])
            else:
                self.TCtemps[0] = None

            if last_index >= 4:
                TC1faultbyte = int(data_list[4])
                if TC1faultbyte == 0:
                    self.TCfaults[0] = "No Faults"
                else:
                    self.TCfaults[0] = [name for i, name in enumerate(self.TCFaultNames) if (TC1faultbyte & (1 << i))].join(", ")
            else: 
                self.TCfaults[0] = None
                
            if last_index >= 5:
                self.TCtemps[1] = float(data_list[5])
            else:
                self.TCtemps[1] = None

            if last_index >= 6:
                TC2faultbyte = int(data_list[6])
                if TC2faultbyte == 0:
                    self.TCfaults[1] = "No Faults"
                else:
                    self.TCfaults[1] = [name for i, name in enumerate(self.TCFaultNames) if (TC2faultbyte & (1 << i))].join(", ")
            else:
                self.TCfaults[1] = None


            if last_index >= 7:
                self.ambtemp = float(data_list[7])
            else:
                self.ambtemp = None

            if last_index >= 8:
                self.rH = float(data_list[8])
            else:
                self.rH = None

            if last_index >= 9:
                self.dhtstatus = bool(float(data_list[9]))
            else:
                self.dhtstatus = None

            if last_index >= 8:
                self.dewpoint = round(self.ambtemp - (100 - self.rH)/5, 2)
            else:
                self.dewpoint = None

            if self.ser and self.ser.is_open:
                self.is_connected = True
            else:
                self.is_connected = False
        elif data_list == ['']:
            print(f"No data received: {data_list}")
            return None
        else:
            print(f"Invalid data received: {data_list}")
            return None
        
        data = {
            "Ambient Temperature": self.ambtemp, 
            "Relative Humidity": self.rH,
            "DHT Status": self.dhtstatus,
            "Door Status": self.door,
            "Leak Status": self.leak,
            "TC Temperatures": self.TCtemps,
            "TC Faults": self.TCfaults,
            "Dewpoint": self.dewpoint,
            "Connected": self.is_connected
        }

        return data