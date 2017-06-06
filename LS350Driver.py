import components as cmp
import logging
import time
import json

driver_queue = 'LS350.driver'
controller_queue = 'LS350.controller'

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


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
        message = {'METHOD': 'QUERY', 'CMD': LS350Driver.get_identity([])}
        self.send_direct_message(self.driver_queue, json.dumps(message))
        #message = {'METHOD': 'QUERY', 'CMD': 'BRIGT?'}
        #self.send_direct_message(self.driver_queue, json.dumps(message))
        #message = {'METHOD': 'WRITE', 'CMD': 'BRIGT 23'}
        #self.send_direct_message(self.driver_queue, json.dumps(message))
        #message = {'METHOD': 'QUERY', 'CMD': 'BRIGT?'}
        #self.send_direct_message(self.driver_queue, json.dumps(message))
        #message = {'METHOD': 'WRITE', 'CMD': 'SETP1,200'}
        #self.send_direct_message(self.driver_queue, json.dumps(message))
        #message = {'METHOD': 'QUERY', 'CMD': 'SETP?1'}
        #self.send_direct_message(self.driver_queue, json.dumps(message))
        time.sleep(1)

    def process_direct_reply(self, channel, method, properties, body):
        LOGGER.info("Producer got back: " + str(body))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    driver = cmp.DriverComponent(driver_queue, {'library': '',
                                                'address': 'ASRL6::INSTR',
                                                'baud_rate': 56000,
                                                'parity': 'odd',
                                                'data_bits': 7})
    controller = LS350Controller(driver_queue, controller_queue)

    try:
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        driver.close()
        controller.close()
