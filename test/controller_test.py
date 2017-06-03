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


class LS350Driver(cmp.DriverComponent):
    @staticmethod
    def validate_num_params(pars, num):
        if len(pars) != num:
            raise ValueError("Number of parameters ({}) does not match expectation ({})".format(len(pars), num))

    @staticmethod
    def validate_input_letter(input, include_all=True):
        valid = ["A", "B", "C", "D"]
        if include_all:
            valid.append("0")

        if input not in valid:
            raise ValueError("Input must be one of {}, instead got {}".format(valid, input))

    @staticmethod
    def validate_input_number(input):
        if input not in [1, 2, 3, 4]:
            raise ValueError("Input must be one of [1, 2, 3, 4], instead got {}".format(input))

    @staticmethod
    def validate_heater_output(output):
        if output not in [1, 2]:
            raise ValueError("Heater output must be one of [1, 2], instead got {}".format(output))

    @staticmethod
    def get_identity(pars):
        LS350Driver.get_identity_validate(pars)
        return "*IDN?"

    @staticmethod
    def get_identity_validate(pars):
        LS350Driver.validate_num_params(pars, 0)

    @staticmethod
    def reset(pars):
        LS350Driver.reset_validate(pars)
        return "*RST"

    @staticmethod
    def reset_validate(pars):
        LS350Driver.validate_num_params(pars, 0)

    @staticmethod
    def get_brightness(pars):
        LS350Driver.get_brightness_validate(pars)
        return "BRIGT?"

    @staticmethod
    def get_brightness_validate(pars):
        LS350Driver.validate_num_params(pars, 0)

    @staticmethod
    def set_brightness(pars):
        LS350Driver.set_brightness_validate(pars)
        return "BRIGT {}".format(*pars)

    @staticmethod
    def get_temperature_celsius(pars):
        LS350Driver.get_sensor_validate(pars)
        return "CRDG? {}".format(*pars)

    @staticmethod
    def get_temperature_kelvin(pars):
        LS350Driver.get_sensor_validate(pars)
        return "KRDG? {}".format(*pars)

    @staticmethod
    def get_sensor_reading(pars):
        LS350Driver.get_sensor_validate(pars)
        return "SRDG? {}".format(*pars)

    @staticmethod
    def get_sensor_validate(pars):
        LS350Driver.validate_num_params(pars, 1)
        LS350Driver.validate_input(pars[0])

    @staticmethod
    def get_heater_output_percent(pars):
        LS350Driver.get_heater_output_percent_validate(pars)
        return "HTR? {output}".format(*pars)

    @staticmethod
    def get_heater_output_percent_validate(pars):
        LS350Driver.validate_num_params(pars, 1)
        LS350Driver.validate_heater_output(pars[0])

    @staticmethod
    def get_ramp_parameters(pars):
        LS350Driver.get_ramp_parameters_validate(pars)
        return "RAMP? {}".format(*pars)

    @staticmethod
    def get_ramp_parameters_validate(pars):
        LS350Driver.validate_num_params(pars, 1)
        LS350Driver.validate_input_number(pars[0])

    @staticmethod
    def set_ramp_parameters(pars):
        LS350Driver.set_ramp_parameters_validate(pars)
        return "RAMP {},{},{}".format(*pars)

    @staticmethod
    def set_ramp_parameters_validate(pars):
        LS350Driver.validate_num_params(pars, 3)
        LS350Driver.validate_input_number(pars[0])
        LS350Driver.validate_ramp_on_off(pars[1])
        LS350Driver.validate_ramp_rate(pars[2])

    @staticmethod
    def validate_ramp_on_off(on_or_off):
        if on_or_off not in [0, 1]:
            raise ValueError("Ramp mode must be either 0=Off or 1=On, instead got {}".format(on_or_off))

    @staticmethod
    def validate_ramp_rate(rate):
        if rate < 0 or rate > 100:
            raise ValueError("Ramp rate must be between 0 and 100. 0 means infinite ramp rate.")

    @staticmethod
    def get_ramp_status(pars):
        LS350Driver.get_ramp_status_validate(pars)
        return "RAMPST? {}".format(*pars)

    @staticmethod
    def get_ramp_status_validate(pars):
        LS350Driver.validate_num_params(pars, 1)
        LS350Driver.validate_input_number(pars[0])

    @staticmethod
    def get_heater_range(pars):
        LS350Driver.get_heater_range_validate(pars)
        return "RANGE? {}".format(*pars)

    @staticmethod
    def get_heater_range_validate(pars):
        LS350Driver.validate_num_params(pars, 1)
        LS350Driver.validate_input_number(pars[0])

    @staticmethod
    def set_heater_range(pars):
        LS350Driver.set_heater_range_validate(pars)
        return "RANGE {},{}".format(*pars)

    @staticmethod
    def set_heater_range_validate(pars):
        LS350Driver.validate_num_params(pars, 2)
        LS350Driver.validate_input_number(pars[0])
        LS350Driver.validate_heater_range(pars[0], pars[1])

    @staticmethod
    def validate_heater_range(output, heater_range):
        if output in [1, 2]:
            if heater_range not in range(0, 6):
                raise ValueError("Heater range must be an integer between 0 and 5 for outputs [1, 2], instead got {}".format(heater_range))
        elif output in [3, 4]:
            if heater_range not in [0, 1]:
                raise ValueError("Heater range must be either 0 or 1 for outputs [3, 4], instead got {}".format(heater_range))

    @staticmethod
    def get_reading_status(pars):
        LS350Driver.get_reading_status_validate(pars)
        return "RDGST? {}".format(pars)

    @staticmethod
    def get_reading_status_validate(pars):
        LS350Driver.validate_num_params(pars, 1)
        # We cannot get reading status for all inputs at the same time
        LS350Driver.validate_input_letter(pars[0], include_all=False)

    @staticmethod
    def get_setpoint(pars):
        LS350Driver.get_setpoint_validate(pars)
        return "SETP? {}".format(*pars)

    @staticmethod
    def get_setpoint_validate(pars):
        LS350Driver.validate_num_params(pars, 1)
        LS350Driver.validate_input_number(pars[0])

    @staticmethod
    def set_setpoint(pars):
        LS350Driver.set_setpoint_validate(pars)
        return "SETP {},{}".format(*pars)

    @staticmethod
    def set_setpoint_validate(pars):
        LS350Driver.validate_num_params(pars, 2)
        LS350Driver.validate_input_number(pars[0])


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

    driver = cmp.DriverComponent(driver_queue, {'library': 'instruments.yaml@mock',
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
