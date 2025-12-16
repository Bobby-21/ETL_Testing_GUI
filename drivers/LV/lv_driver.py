import socket

class LVPowerSupply():
    def __init__(self, ip, channel, tcp_port=5025, timeout=1.0):
        self.ip = ip
        self.tcp_port = tcp_port
        self.channel = channel
        self.timeout = timeout
        self.sock = None
        self.connect()

    def connect(self):
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(self.timeout)
            self.sock.connect((self.ip, self.tcp_port))

    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def send_command(self, cmd):
        self.sock.sendall((cmd + '\n').encode())
        if "?" not in cmd:
            response = None
            return response
        
        response = ""
        while True:
            chunk = self.sock.recv(1)
            if not chunk:
                break
            chunk = chunk.decode()
            response += chunk
            if '\n' in chunk:
                break

        return response


    def set_voltage(self, voltage):
        response = self.send_command(f"CH{self.channel}: VOLT {voltage}")
    
    def set_current_limit(self, current):
        response = self.send_command(f"CH{self.channel}: CURR {current}")
    
    def set_channel_on(self):
        response = self.send_command(f"OUTP CH{self.channel},ON")
    
    def set_channel_off(self):
        response = self.send_command(f"OUTP CH{self.channel},OFF")
    
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
    