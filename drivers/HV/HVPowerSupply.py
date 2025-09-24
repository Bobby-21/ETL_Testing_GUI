# Write python serial file to talk to CAEN NDT 1470 HV power supply

import serial
import time
import matplotlib.pyplot as plt

class HVPowerSupply():
    def __init__(self, port, baud=9600, bd_addr=0, channel=0):
        self.port = port
        self.baud = baud
        self.bd_addr = bd_addr
        self.channel = channel
        self.vtol = .5
        self.ser = serial.Serial(self.port, 
                                self.baud,
                                parity=serial.PARITY_NONE,
                                stopbits=serial.STOPBITS_ONE,
                                bytesize=serial.EIGHTBITS,
                                timeout=1)
        self.flush_input_buffer()

    def close(self):
        if self.ser != None:
            self.ser.close()

    def send_command(self, type, channel, parameter, value=None):
        cmd = f"$BD:{self.bd_addr},CMD:{type},CH:{channel},PAR:{parameter}"
        if value is not None:
            cmd += f",VAL:{value}"
        cmd += "\r\n"
        self.ser.write(bytes(cmd, 'ascii'))
        response = self.ser.readline()

        return response.decode('ascii')
    
    def parse_response(self, response):
        # Example response: $BD:*,CMD:OK,VAL:*
        parts = response.strip().split(',')
        resp_dict = {}
        for part in parts:
            key, value = part.split(':')
            resp_dict[key] = value
        return resp_dict
    
    def flush_input_buffer(self):
        self.ser.flushInput()

    def set_voltage(self, voltage):
        response = self.send_command('SET', self.channel, "VSET", voltage)
        return self.parse_response(response)
    
    def set_current_limit(self, current):
        response = self.send_command('SET', self.channel, "ISET", current)
        return self.parse_response(response)
    
    def set_channel_on(self):
        response = self.send_command('SET', self.channel, "ON")
        return self.parse_response(response)
    
    def set_channel_off(self):
        response = self.send_command('SET', self.channel, "OFF")
        return self.parse_response(response)
    
    def read_vset(self):
        response = self.send_command('MON', self.channel, "VSET")
        return self.parse_response(response)
    
    def read_vmon(self):
        response = self.send_command('MON', self.channel, "VMON")
        return self.parse_response(response)
    
    def read_imon(self):
        response = self.send_command('MON', self.channel, "IMON")
        return self.parse_response(response)
    
    def set_ramp_up(self, ramp_up):
        response = self.send_command('SET', self.channel, "RUP", ramp_up)
        return self.parse_response(response)
    
    def set_ramp_down(self, ramp_down):
        response = self.send_command('SET', self.channel, "RDW", ramp_down)
        return self.parse_response(response)
    
    def read_ramp_up(self):
        response = self.send_command('MON', self.channel, "RUP")
        return self.parse_response(response)
    
    def read_ramp_down(self):
        response = self.send_command('MON', self.channel, "RDW")
        return self.parse_response(response)
    
    def read_status(self):
        response = self.send_command('MON', self.channel, "STAT")
        return self.parse_response(response)
    
    def read_polarity(self):
        response = self.send_command('MON', self.channel, "POL")
        return self.parse_response(response)
    
    def wait_ramp(self):
        while True:
            if abs(float(self.read_vmon()['VAL'])-float(self.read_vset()['VAL']))<= self.vtol:
                break
            time.sleep(.1)
    
    
    def extract_float_value(self, response_dict):
        if 'VAL' in response_dict:
            try:
                return float(response_dict['VAL'])
            except ValueError:
                return None
        return None
    
    def IV_curve(self, start_v, stop_v, step_v, curr_limit):
        n = abs((stop_v - start_v) // step_v) + 1
        voltages = []
        currents = []
        if self.read_polarity()['VAL'] == '-':
            pol = -1
        else:
            pol = 1
        self.set_current_limit(curr_limit)
        self.set_voltage(start_v)
        self.set_channel_on()
        self.wait_ramp()
        for v in range(1, int(n)):
            volt = start_v + v * step_v
            self.set_voltage(volt)
            self.wait_ramp()
            vmon_resp = self.read_vmon()
            imon_resp = self.read_imon()
            vmon = self.extract_float_value(vmon_resp)
            imon = self.extract_float_value(imon_resp)
            voltages.append(vmon*pol)
            currents.append(imon)
        self.set_channel_off()
        return voltages, currents
    
    def plot_IV_curve(self, start_v, stop_v, step_v, curr_limit):
        voltages, currents = self.IV_curve(start_v, stop_v, step_v, curr_limit)
        plt.figure()
        plt.plot(voltages, currents, marker='o')
        if self.read_polarity()['VAL'] == '-':
            plt.gca().invert_xaxis()
        plt.xlabel('Voltage (V)')
        plt.ylabel('Current ($\mu$A)')
        plt.title('I-V Curve')
        plt.grid(True)
        plt.show()

