import components as cmp
from components import QueryCommand, WriteCommand
import logging
import time
import json
import re

driver_queue = 'LS350.driver'
controller_queue = 'LS350.controller'

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class LS350Driver(cmp.IEEE488_2_CommonCommands):
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

    class GetBrightness(QueryCommand):
        cmd = "BRIGT?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class SetBrightness(WriteCommand):
        cmd = "BRIGT"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            if pars[0] < 1 or pars[0] > 32:
                raise ValueError("Brightness must be between 1 and 32, instead got {}".format(pars[0]))

    class GetTemperatureCelsius(QueryCommand):
        cmd = "CRDG?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_letter(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return float(result)

    class GetTemperatureKelvin(QueryCommand):
        cmd = "KRDG?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_letter(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return float(result)

    class GetSensorReading(QueryCommand):
        cmd = "SRDG?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_letter(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return float(result)

    class GetHeaterOutputPercent(QueryCommand):
        cmd = "HTR?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_heater_output(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return float(result)

    class GetRampParameters(QueryCommand):
        cmd = "RAMP?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"On/Off": int(resp[0]),
                    "Rate": float(resp[1])}

    class SetRampParameters(WriteCommand):
        cmd = "RAMP"
        arguments = "{},{},{}"

        @classmethod
        def _validate(cls, pars):
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

    class GetRampStatus(QueryCommand):
        cmd = "RAMPST?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result[0])

    class GetHeaterRange(QueryCommand):
        cmd = "RANGE?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
           return int(result)

    class SetHeaterRange(WriteCommand):
        cmd = "RANGE"
        arguments = "{},{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])
            LS350Driver.validate_heater_range(pars[0], pars[1])

    class GetHeaterSetup(QueryCommand):
        cmd = "HTRSET?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_heater_output(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"Resistance": int(resp[0]),
                    "Max Current": int(resp[1]),
                    "Max User": float(resp[2]),
                    "Current/Power": int(resp[3])}

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

    class GetReadingStatus(QueryCommand):
        cmd = "RDGST?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_letter(pars[0], include_all=False)

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetSetpoint(QueryCommand):
        cmd = "SETP?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return float(result)

    class SetSetpoint(WriteCommand):
        cmd = "SETP"
        arguments = "{},{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])

    class GetPID(QueryCommand):
        cmd = "PID?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"P": float(resp[0]),
                    "I": float(resp[1]),
                    "D": float(resp[2])}

    class SetPID(WriteCommand):
        cmd = "PID"
        arguments = "{},{},{},{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    driver = LS350Driver(driver_queue, {'library': '',
                                                'address': 'ASRL9::INSTR',
                                                'baud_rate': 56000,
                                                'parity': 'odd',
                                                'data_bits': 7})

    try:
        time.sleep(1000000)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        driver.close()
