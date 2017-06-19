import components as cmp
from components import QueryCommand, WriteCommand
import logging
import time
import json
import re
import configparser
import sys

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


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read(sys.argv[1])
    LS218_config = config['LS218']

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    driver = LS218Driver(LS218_config['queue_name'], {'library': '',
                                                'address': LS218_config['address'],
                                                'baud_rate': LS218_config.getint('baud_rate'),
                                                'parity': LS218_config['parity'],
                                                'data_bits': LS218_config.getint('data_bits')})

    try:
        time.sleep(1000000)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        driver.close()
