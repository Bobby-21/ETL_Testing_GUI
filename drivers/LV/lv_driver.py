import serial

class LVPowerSupply():
    def __init__(self, port, channel, baud=115200):
        self.port = port
        self.baud = baud
        self.channel = channel
        self.ser = serial.Serial(self.port, self.baud, timeout=1)
        self.flush_input_buffer()

    def close(self):
        if self.ser != None:
            self.ser.close()

    def send_command(self, cmd):
        if self.ser and self.ser.is_open:
            self.ser.reset_input_buffer()
            self.ser.write((f"{cmd}\n").encode())
            self.ser.flush()
            line = self.ser.readline().decode()
            return line
        else:
            raise RuntimeError("Serial not open, call connect() first")
    
    def flush_input_buffer(self):
        self.ser.flushInput()

    def set_voltage(self, voltage):
        response = self.send_command(f"CH{self.channel}: VOLT {voltage}").strip()
    
    def set_current_limit(self, current):
        response = self.send_command(f"CH{self.channel}: CURR {current}").strip()
    
    def set_channel_on(self):
        response = self.send_command(f"OUTP CH{self.channel},ON").strip()
    
    def set_channel_off(self):
        response = self.send_command(f"OUTP CH{self.channel},OFF").strip()
    
    def read_vset(self):
        response = self.send_command(f"CH{self.channel}: VOLT?").strip()
        return float(response)
    
    def read_vmon(self):
        response = self.send_command(f"MEAS: VOLT? CH{self.channel}").strip()
        return float(response)
        
    def read_iset(self):
        response = self.send_command(f"CH{self.channel}: CURR?").strip()
        return float(response)
    
    def read_imon(self):
        response = self.send_command(f"MEAS: CURR? CH{self.channel}").strip()
        return float(response)
    
    def read_power(self):
        response = self.send_command(f"MEAS: POWE? CH{self.channel}").strip()
        return float(response)
    
    def read_status(self):
        response = self.send_command("SYST:STAT?").strip()
        return int(response)