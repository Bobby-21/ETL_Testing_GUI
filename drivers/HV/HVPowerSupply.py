# Write python serial file to talk to CAEN NDT 1470 HV power supply

import serial
import time
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import os
from etlup.module.ModuleIV import ModuleIVV0
from etlup import prod_session

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
    
    def wait_ramp(self, delay):
        while True:
            if abs(float(self.read_vmon()['VAL'])-float(self.read_vset()['VAL']))<= self.vtol:
                break
            if int(self.read_status()['VAL']) & 128 or int(self.read_status()['VAL']) & 8:
                raise ValueError("Compliance reached, supply tripped")
            time.sleep(.1)
        time.sleep(delay)
        if int(self.read_status()['VAL']) & 128 or int(self.read_status()['VAL']) & 8:
                raise ValueError("Compliance reached, supply tripped")
    
    
    def extract_float_value(self, response_dict):
        if 'VAL' in response_dict:
            try:
                return float(response_dict['VAL'])
            except ValueError:
                return None
        return None
    
    def IV_curve(self, start_v, stop_v, step_v, curr_limit, delay):
        n = abs((stop_v - start_v) // step_v) + 1
        voltages = []
        currents = []
        kfactors = []
        if self.read_polarity()['VAL'] == '-':
            pol = -1
        else:
            pol = 1
        self.set_current_limit(curr_limit)
        self.set_voltage(start_v)
        self.set_channel_on()
        try:
            self.wait_ramp(delay)
        except ValueError as e:
            print(e)
        vmon_resp = self.read_vmon()
        imon_resp = self.read_imon()
        vmon = self.extract_float_value(vmon_resp)
        imon = self.extract_float_value(imon_resp)
        print(f"Vmon: {vmon*pol}, Imon: {imon}")
        voltages.append(vmon*pol)
        currents.append(imon)
        kfactors.append(np.nan)

        for v in range(1, int(n)):
            volt = start_v + v * step_v
            self.set_voltage(volt)
            try:
                self.wait_ramp(delay)
            except ValueError as e:
                print(e)
                break
            vmon_resp = self.read_vmon()
            imon_resp = self.read_imon()
            vmon = self.extract_float_value(vmon_resp)
            imon = self.extract_float_value(imon_resp)
            if imon>0:
                kfactor = ((imon-currents[v-1])/(vmon-pol*voltages[v-1]))*(vmon/imon)
            else:
                kfactor = np.nan

            print(f"Vmon: {vmon*pol}, Imon: {imon}, K-Factor: {kfactor}")
            voltages.append(vmon*pol)
            currents.append(imon)
            kfactors.append(kfactor)
        self.set_channel_off()
        return voltages, currents, kfactors
    
    def plot_IV_curve(self, start_v, stop_v, step_v, curr_limit, moduleid, delay=10):
        voltages, currents, kfactors = self.IV_curve(start_v, stop_v, step_v, curr_limit, delay)

        timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
        maindir = Path(__file__).parent.parent.parent

        resultdir = maindir / "IV_Curves" / str(moduleid) / timestamp
        if not os.path.isdir(resultdir):
            os.makedirs(resultdir)

        resultdir.mkdir(exist_ok=True)

        outfile = resultdir / f"IV_Curve_{moduleid}_{timestamp}.csv"
        with open(outfile, 'w') as f:
            f.write(f"Voltage (V): {voltages}\n")
            f.write(f"Current (uA): {currents}\n")
            f.write(f"K-Factor: {kfactors}\n")

        fig, ax1 = plt.subplots()

        ax1.set_xlabel('Voltage (V)')
        ax1.set_ylabel('Current ($\mu$A)')
        p1 = ax1.plot(voltages, currents, color = 'red', label="Current", marker='.')
        ax1.tick_params(axis = 'y', labelcolor = 'red', color = 'red')

        ax2 = ax1.twinx()
        ax2.set_ylabel('K-Factor')
        p2 = ax2.plot(voltages, kfactors, color = 'blue', label="K-Factor", marker='.')
        ax2.tick_params(axis = 'y', labelcolor = 'blue', color = 'blue')

        if self.read_polarity()['VAL'] == '-':
            plt.gca().invert_xaxis()

        ps = p1+p2
        labs = [l.get_label() for l in ps]
        ax1.legend(ps, labs, loc=0)
        ax1.grid()
        plt.title('IV Curve')
        plt.savefig(resultdir / f"IV_Curve_{moduleid}_{timestamp}.png")
        plt.show()

        upload_bool = input("Upload results to database? (y/n): ")
        if upload_bool.strip().lower() == 'y' or upload_bool.strip().lower() == 'yes':
            user = str(input("CERN Username: "))
            iv = ModuleIVV0(
                module=moduleid,
                measurement_date=timestamp,
                location="BU",
                user_created=user,
                current = currents,
                voltage = voltages,
                k_factor = kfactors,
            )
            print(iv)
            tests = [iv]
            prod_session.add_all(tests)
            prod_session.upload()
