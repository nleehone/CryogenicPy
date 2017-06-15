import components as cmp
from components import QueryCommand, WriteCommand
import logging
import time
import json
import re

driver_queue = 'LS218.driver'

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class LS218Driver(cmp.IEEE488_2_CommonCommands):
    @staticmethod
    def validate_input_number(input, include_all=False):
        min = 0 if include_all else 1
        try:
            if int(input) not in range(min, 9):
                raise ValueError("Input must be one of {}, instead got {}".format(range(min, 9), input))
        except ValueError as e:
            raise ValueError("Input must be an integer between 0 and 9, instead got {}".format(input))

    @staticmethod
    def validate_output_number(input):
        try:
            if int(input) not in [1, 2]:
                raise ValueError("Input must be one of {}, instead got {}".format([1, 2], input))
        except ValueError as e:
            raise ValueError("Input must be 1 or 2, instead got {}".format(input))

    class GetSensorReading(QueryCommand):
        cmd = "SRDG?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0], include_all=True)

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            print(result, pars)
            if int(pars[0]) == 0:
                return list(map(lambda x: float(x), result.split(',')))
            else:
                return float(result)

    class GetKelvinReading(GetSensorReading):
        cmd = "KRDG?"

    class GetCelsiusReading(GetSensorReading):
        cmd = "CRDG?"

    class GetAlarmParameters(QueryCommand):
        cmd = "ALARM?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"on/off": int(resp[0]),
                    "source": int(resp[1]),
                    "high": float(resp[2]),
                    "low": float(resp[3]),
                    "deadband": float(resp[4]),
                    "latch": int(resp[5])}

    class GetAlarmStatus(QueryCommand):
        cmd = "ALARMST?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"high": int(resp[0]),
                    "low": int(resp[1])}

    class GetAnalogOutputParameters(QueryCommand):
        cmd = "ANALOG?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_output_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"bipolar": int(resp[0]),
                    "mode": int(resp[1]),
                    "input": int(resp[2]),
                    "source": int(resp[3]),
                    "high": float(resp[4]),
                    "low": float(resp[5]),
                    "manual": float(resp[6])}

    class GetAnalogOutputData(QueryCommand):
        cmd = "AOUT?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_output_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return float(result)

    class GetBaudRate(QueryCommand):
        cmd = "BAUD?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    driver = LS218Driver(driver_queue, {'library': '',
                                                'address': 'ASRL3::INSTR',
                                                'baud_rate': 9600,
                                                'parity': 'odd',
                                                'data_bits': 7})

    try:
        time.sleep(1000000)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        driver.close()
