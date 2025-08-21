import serial
import time

class sensors:
    def __init__(self, port, baudrate = 115200, timeout = 1.0):
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

    def connect(self):
        self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        time.sleep(2)
        return self.ser.is_open
    
    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        else:
            raise RuntimeError("Serial not open, call connect() first")
    
    def send(self, cmd):
        if self.ser and self.ser.is_open:
            self.ser.write((cmd + "\n").encode())
            line = self.ser.readline().decode().strip()
            return line
        else:
            raise RuntimeError("Serial not open, call connect() first")
        
    def get_ambtemp(self):
        response = self.send("GetAmbTemp")
        self.ambtemp = float(response)
        return self.ambtemp
    
    def get_rH(self):
        response = self.send("GetrH")
        self.rH = float(response)
        return self.rH
    
    def get_door(self):
        response = self.send("GetDoor")
        self.door = bool(int(response))
        return self.door
    
    def get_leak(self):
        response = self.send("GetLeak")
        self.leak = bool(int(response))
        return self.leak

    def get_TCtemps(self):
        response1 = self.send("GetTC1Temp")
        response2 = self.send("GetTC2Temp")
        self.TCtemps = [float(response1), float(response2)]
        return self.TCtemps
    
    def get_TCfaults(self):
        response1 = self.send("GetTC1Status")
        response2 = self.send("GetTC2Status")
        self.TCfaults = [response1.strip().split(","), response2.strip().split(",")]
        return self.TCfaults
    
    def get_dhtstatus(self):
        response = self.send("GetDHTStatus")
        self.dhtstatus = bool(response)
        return self.dhtstatus

    def restart_dht(self):
        response = self.send("RestartDHT")
        self.dhtstatus = bool(response)
        return self.dhtstatus