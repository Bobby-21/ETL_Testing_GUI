import serial
import time

class Sensors:
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
        time.sleep(2)
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
            time.sleep(1)
            line = self.ser.readline().decode().strip()
            return line
        else:
            raise RuntimeError("Serial not open, call connect() first")
        
    def get_ambtemp(self):
        response = self.send("GetAmbTemp")
        self.ambtemp = float(response) if response else 'ERR'
        return self.ambtemp
    
    def get_rH(self):
        response = self.send("GetrH")
        self.rH = float(response) if response else 'ERR'
        return self.rH
    
    def get_door(self):
        response = self.send("GetDoor")
        self.door = bool(float(response)) if response else 'ERR'
        return self.door
    
    def get_leak(self):
        response = self.send("GetLeak")
        self.leak = bool(float(response)) if response else 'ERR'
        return self.leak

    def get_TCtemps(self):
        response1 = self.send("GetTC1Temp")
        response2 = self.send("GetTC2Temp")
        self.TCtemps = [float(response1) if response1 else 'ERR', float(response2) if response2 else 'ERR']
        return self.TCtemps
    
    def get_TCfaults(self):
        response1 = self.send("GetTC1Status")
        response2 = self.send("GetTC2Status")
        self.TCfaults = [response1.strip().split(","), response2.strip().split(",")]
        return self.TCfaults
    
    def get_dhtstatus(self):
        response = self.send("GetDHTStatus")
        self.dhtstatus = bool(float(response)) if response else 'ERR'
        return self.dhtstatus

    def restart_dht(self):
        response = self.send("RestartDHT")
        self.dhtstatus = bool(response) if response else 'ERR'
        return self.dhtstatus
        
    def get_dewpoint(self):
        self.rH = self.get_rH()
        self.ambtemp = self.get_ambtemp()
        if self.rH != 'ERR' and self.ambtemp != 'ERR':
            self.dewpoint = self.ambtemp - (100 - self.rH)/5
        else:
            self.dewpoint = 'ERR'
        return self.dewpoint
    
    def get_data(self):
        # ambtemp, rH, dhtstatus, door, leak, TCtemp1, TCtemp2, TCfault1, TCfault2, dewpoint, is_connected
        response = self.send("GetData")
        data_list = response.split(",")
        if data_list != ['']:
            try:
                self.ambtemp = float(data_list[0]) if data_list[0] else 'ERR'
                self.rH = float(data_list[1]) if data_list[1] else 'ERR'
                self.dhtstatus = bool(float(data_list[2])) if data_list[2] else 'ERR'
                self.door = bool(float(data_list[3])) if data_list[3] else 'ERR'
                self.leak = bool(float(data_list[4])) if data_list[4] else 'ERR'
                self.TCtemps = [float(data_list[5]) if data_list[5] else 'ERR', float(data_list[7]) if data_list[7] else 'ERR']
                TC1faultbyte = int(data_list[6]) if data_list[7] else 0
                TC2faultbyte = int(data_list[8]) if data_list[8] else 0
                if TC1faultbyte == 0:
                    self.TCfaults[0] = "No Faults"
                else:
                    self.TCfaults[0] = [name for i, name in enumerate(self.TCFaultNames) if (TC1faultbyte & (1 << i))].join(", ")

                if TC2faultbyte == 0:
                    self.TCfaults[1] = "No Faults"
                else:
                    self.TCfaults[1] = [name for i, name in enumerate(self.TCFaultNames) if (TC2faultbyte & (1 << i))].join(", ")

                if self.ambtemp != 'ERR' and self.rH != 'ERR':
                    self.dewpoint = round(self.ambtemp - (100 - self.rH)/5, 2)
                else:
                    self.dewpoint = 'ERR'
        
                if self.ser and self.ser.is_open:
                    self.is_connected = True
                else:
                    self.is_connected = False

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
            except Exception as e:
                print(f"Arduino sensor read failed: {e}")
                print(f"Received data: {data_list}")
        else:
            print("No sensor data received")
            return None
    
    def update_all(self):
        try:
            self.get_ambtemp()
        except Exception as e:
            print(f"Ambient temperature read failed: {e}")

        try:
            self.get_dhtstatus()
        except Exception as e:
            print(f"DHT22 status read failed: {e}")

        try:
            self.get_rH()
        except Exception as e:
            print(f"Relative humidity read failed: {e}")

        try:
            self.get_door()
        except Exception as e:
            print(f"Door sensor read failed: {e}")

        try:
            self.get_leak()
        except Exception as e:
            print(f"Leak sensor read failed: {e}")

        try:
            self.get_TCfaults()
        except Exception as e:
            print(f"Thermocouple fault read failed: {e}")

        try:
            self.get_TCtemps()
        except Exception as e:
            print(f"Thermocouple temperatures read failed: {e}")

        try:
            self.get_dewpoint()
        except Exception as e:
            print(f"Dewpoint calculation failed: {e}")

        try:
            self.check_serial_connected()
        except Exception as e:
            print(f"Serial connection status read failed: {e}")
    
    def package(self):
        self.update_all()
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
