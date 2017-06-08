import components as cmp
import logging
import time
import json
import re

driver_queue = 'LS350.driver'
controller_queue = 'LS350.controller'

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class LS350Driver(cmp.Driver):
    def split_cmd(self, cmd):
        # Split the message into a command and a set of parameters
        command, *pars = list(filter(None, map(lambda x: x.strip(), re.split(',| |\?', cmd))))
        # Put the question mark back in since it was removed in the split process
        if "?" in cmd:
            command += "?"
        return command, pars

    def check_command(self, cmd):
        cmd, pars = self.split_cmd(cmd)

        try:
            {
                "*IDN?": LS350Driver.get_identity_validate,
                "*RST": LS350Driver.reset_validate,

                "BRIGT?": LS350Driver.get_brightness_validate,
                "HTR?": LS350Driver.get_heater_output_percent_validate,
                "CRDG?": LS350Driver.get_sensor_validate,
                "KRDG?": LS350Driver.get_sensor_validate,
                "SRDG?": LS350Driver.get_sensor_validate,
                "RANGE?": LS350Driver.get_heater_range_validate,
                "RAMP?": LS350Driver.get_ramp_parameters_validate,
                "RAMPST?": LS350Driver.get_ramp_status_validate,
                "RDGST?": LS350Driver.get_reading_status_validate,
                "SETP?": LS350Driver.get_setpoint_validate,

                "BRIGT": LS350Driver.set_brightness_validate,
                "RANGE": LS350Driver.set_heater_range_validate,
                "RAMP": LS350Driver.set_ramp_parameters_validate,
                "SETP": LS350Driver.set_setpoint_validate,
             }[cmd](pars)
        except Exception as e:
            return e

    def process_response(self, response, cmd):
        cmd, pars = self.split_cmd(cmd)
        try:
            processed = {
                "*IDN?": LS350Driver.get_identity_response,
                "BRIGT?": LS350Driver.get_brightness_response,
                "HTR?": LS350Driver.get_heater_output_percent_response,
                "CRDG?": LS350Driver.get_sensor_reading_response,
                "KRDG?": LS350Driver.get_sensor_reading_response,
                "SRDG?": LS350Driver.get_sensor_reading_response,
                "RANGE?": LS350Driver.get_heater_range_response,
                "RAMP?": LS350Driver.get_ramp_parameters_response,
                "RAMPST?": LS350Driver.get_ramp_status_response,
                "RDGST?": LS350Driver.get_reading_status_response,
                "SETP?": LS350Driver.get_setpoint_response,
            }[cmd](pars, response)
        except Exception as e:
            return None, e
        return processed, None

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
        if int(input) not in [1, 2, 3, 4]:
            raise ValueError("Input must be one of [1, 2, 3, 4], instead got {}".format(input))

    @staticmethod
    def validate_heater_output(output):
        if int(output) not in [1, 2]:
            raise ValueError("Heater output must be one of [1, 2], instead got {}".format(output))

    @staticmethod
    def get_identity(pars):
        LS350Driver.get_identity_validate(pars)
        return "*IDN?"

    @staticmethod
    def get_identity_validate(pars):
        LS350Driver.validate_num_params(pars, 0)

    @staticmethod
    def get_identity_response(pars, resp):
        return resp

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
    def get_brightness_response(pars, resp):
        return int(resp)

    @staticmethod
    def set_brightness(pars):
        LS350Driver.set_brightness_validate(pars)
        return "BRIGT {}".format(*pars)

    @staticmethod
    def set_brightness_validate(pars):
        LS350Driver.validate_num_params(pars, 1)

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
        LS350Driver.validate_input_letter(pars[0])

    @staticmethod
    def get_sensor_reading_response(pars, resp):
        return float(resp)

    @staticmethod
    def get_heater_output_percent(pars):
        LS350Driver.get_heater_output_percent_validate(pars)
        return "HTR? {output}".format(*pars)

    @staticmethod
    def get_heater_output_percent_validate(pars):
        LS350Driver.validate_num_params(pars, 1)
        LS350Driver.validate_heater_output(pars[0])

    @staticmethod
    def get_heater_output_percent_response(pars, resp):
        return float(resp)

    @staticmethod
    def get_ramp_parameters(pars):
        LS350Driver.get_ramp_parameters_validate(pars)
        return "RAMP? {}".format(*pars)

    @staticmethod
    def get_ramp_parameters_validate(pars):
        LS350Driver.validate_num_params(pars, 1)
        LS350Driver.validate_input_number(pars[0])

    @staticmethod
    def get_ramp_parameters_response(pars, resp):
        print(resp)
        resp = list(map(lambda x: x.strip(), resp.split(',')))
        return {"On/Off": int(resp[0]),
                "Rate": float(resp[1])}

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
        if int(on_or_off) not in [0, 1]:
            raise ValueError("Ramp mode must be either 0=Off or 1=On, instead got {}".format(on_or_off))

    @staticmethod
    def validate_ramp_rate(rate):
        rate = float(rate)
        if rate < 0 or rate > 100:
            raise ValueError("Ramp rate must be between 0 and 100. 0 means infinite ramp rate.")

    @staticmethod
    def get_ramp_status(pars):
        LS350Driver.get_ramp_status_validate(pars)
        return "RAMPST? {}".format(*pars)

    @staticmethod
    def get_ramp_status_validate(pars):
        print(pars)
        LS350Driver.validate_num_params(pars, 1)
        LS350Driver.validate_input_number(pars[0])

    @staticmethod
    def get_ramp_status_response(pars, resp):
        return int(resp)

    @staticmethod
    def get_heater_range(pars):
        LS350Driver.get_heater_range_validate(pars)
        return "RANGE? {}".format(*pars)

    @staticmethod
    def get_heater_range_validate(pars):
        LS350Driver.validate_num_params(pars, 1)
        LS350Driver.validate_input_number(pars[0])

    @staticmethod
    def get_heater_range_response(pars, resp):
        return int(resp)

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
        output = int(output)
        heater_range = int(heater_range)
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
    def get_reading_status_response(pars, resp):
        return int(resp)

    @staticmethod
    def get_setpoint(pars):
        LS350Driver.get_setpoint_validate(pars)
        return "SETP? {}".format(*pars)

    @staticmethod
    def get_setpoint_validate(pars):
        LS350Driver.validate_num_params(pars, 1)
        LS350Driver.validate_input_number(pars[0])

    @staticmethod
    def get_setpoint_response(pars, resp):
        return float(resp)

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
        message = {'METHOD': 'QUERY', 'CMD': LS350Driver.get_identity([])}
        self.send_direct_message(self.driver_queue, json.dumps(message))
        time.sleep(1)

    def process_direct_reply(self, channel, method, properties, body):
        LOGGER.info("Producer got back: " + str(body))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    driver = cmp.DriverComponent(driver_queue, {'library': '',
                                                'address': 'ASRL6::INSTR',
                                                'baud_rate': 56000,
                                                'parity': 'odd',
                                                'data_bits': 7}, LS350Driver)
    #controller = LS350Controller(driver_queue, controller_queue)

    try:
        time.sleep(10000)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        driver.close()
        #controller.close()
