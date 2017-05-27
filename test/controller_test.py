import rmq_component as rmq
import components as cmp
import logging
import time
import json
import re


# Force the loading of pyvisa-mock. We need this because pyvisa-mock is not a valid identifier
import importlib
mock = importlib.import_module("pyvisa-mock")


driver_queue = 'LS350.driver'
controller_queue = 'LS350.controller'

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


K_to_C = -273.15


class LS350Device(mock.devices.Device):
    def __init__(self, name, delimiter):
        super().__init__(name, delimiter)
        self.idn = "LSCI,MODEL350,1234567/1234567,1.0"
        self.brightness = 32
        self.sensors = [10, 10, 10, 10]
        self.setpoints = [300, 300, 300, 300]
        self.heater_ranges = [0, 0, 0, 0]
        # Ramps are [On=1/Off=0, Rate (K/m)]
        self.ramps = [[0, 0], [0, 0], [0, 0], [0, 0]]

    def sensor_to_kelvin(self, sensor):
        """Simplistic version of the temperature controller's calibration files"""
        return 30*self.sensors[sensor]

    @staticmethod
    def channel_letter_to_number(letter):
        return {'A': 0,
                'B': 1,
                'C': 2,
                'D': 3}[letter]

    @staticmethod
    def check_valid_channel_number(channel):
        channel = int(channel)
        if channel < 1 or channel > 4:
            raise ValueError("Invalid channel number: {}".format(channel))
        return channel - 1

    def _match(self, cmd):
        """Tries to match the query to the set of commands the instrument
        recognises

        :param query: message tuple
        :type query: Tuple[bytes]
        :return: response if found or None
        :rtype: Tuple[bytes] | None
        """
        cmd = cmd.decode('utf-8').strip()

        if "?" in cmd:
            return bytes(str(self._query(cmd)).encode('utf-8'))
        else:
            self._write(cmd)

    def _query(self, cmd):
        cmd, *pars = list(map(lambda x: x.strip(), re.split(',| |\?', cmd)))

        if cmd == '*IDN':
            return self.idn
        elif cmd == 'BRIGT':
            return self.brightness
        elif cmd == 'SRDG':
            return self.sensor[LS350Device.channel_letter_to_number(pars[0])]
        elif cmd == 'KRDG':
            return self.sensor_to_kelvin(LS350Device.channel_letter_to_number(pars[0]))
        elif cmd == 'CRDG':
            return self.sensor_to_kelvin(LS350Device.channel_letter_to_number(pars[0])) - K_to_C
        elif cmd == 'SETP':
            return self.setpoints[LS350Device.check_valid_channel_number(pars[0])]
        elif cmd == 'RANGE':
            return self.heater_ranges[LS350Device.check_valid_channel_number(pars[0])]
        elif cmd == 'RAMPST':
            return self.ramps[LS350Device.check_valid_channel_number(pars[0])][0]
        elif cmd == 'RAMP':
            return "{},{}".format(*self.ramps[LS350Device.check_valid_channel_number(pars[0])])
        else:
            raise ValueError(cmd, pars, "This command is not available")

    def _write(self, cmd):
        cmd, *pars = list(map(lambda x: x.strip(), re.split(',| ', cmd)))

        # Deal with queries of the form SETP1,300, where the command has the
        # channel attached
        try:
            val = int(cmd[-1])
            cmd = cmd[:-1]
            pars.insert(0, val)
        except:
            pass

        if cmd == 'BRIGT':
            self.brightness = int(pars[0])
        elif cmd == 'SETP':
            self.setpoints[LS350Device.check_valid_channel_number(int(pars[0]))] = float(pars[1])
        elif cmd == 'RANGE':
            channel = int(pars[0])
            LS350Device.check_valid_channel_number(channel)

            range = int(pars[1])
            if channel in [1, 2]:
                if range < 0 or range > 5:
                    raise ValueError("Invalid range for channel {}", channel)
            elif channel in [3, 4]:
                if range < 0 or range > 1:
                    raise ValueError("Invalid range for channel {}", channel)

            self.heater_ranges[int(pars[0]) - 1] = int(pars[1])
        elif cmd == 'RAMP':
            self.ramps[LS350Device.check_valid_channel_number(int(pars[0]))] = [int(pars[1]), float(pars[2])]
        else:
            raise ValueError(cmd, pars, "This command is not available")


class LS350Controller(cmp.ControllerComponent):
    def process(self):
        #message = {'METHOD': 'QUERY', 'CMD': 'CRVHDR?8'}
        #self.send_direct_message(self.driver_queue, json.dumps(message))
        #time.sleep(1)
        message = {'METHOD': 'QUERY', 'CMD': '*IDN?'}
        self.send_direct_message(self.driver_queue, json.dumps(message))
        message = {'METHOD': 'QUERY', 'CMD': 'BRIGT?'}
        self.send_direct_message(self.driver_queue, json.dumps(message))
        message = {'METHOD': 'WRITE', 'CMD': 'BRIGT 23'}
        self.send_direct_message(self.driver_queue, json.dumps(message))
        message = {'METHOD': 'QUERY', 'CMD': 'BRIGT?'}
        self.send_direct_message(self.driver_queue, json.dumps(message))
        message = {'METHOD': 'WRITE', 'CMD': 'SETP1,200'}
        self.send_direct_message(self.driver_queue, json.dumps(message))
        message = {'METHOD': 'QUERY', 'CMD': 'SETP?1'}
        self.send_direct_message(self.driver_queue, json.dumps(message))
        time.sleep(1)

    def process_direct_reply(self, channel, method, properties, body):
        LOGGER.info("Producer got back: " + str(body))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    driver = cmp.DriverComponent(driver_queue, {'library': 'test/instruments.yaml@mock',
                                                'address': 'ASRL1::INSTR'})
    controller = LS350Controller(driver_queue, controller_queue)
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        driver.close()
        controller.close()
