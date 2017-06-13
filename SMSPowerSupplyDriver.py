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


class SMSPowerSupplyDriver(cmp.CommandDriver):
    def __init__(self):
        self.tesla_per_amp = 0

    @staticmethod
    def validate_units_T_A(units):
        if units not in ['T', 'A']:
            raise ValueError("Units must be either T or A, instead got {}".format(units))

    class GetMid(QueryCommand):
        cmd = "MID"
        arguments = "{}"
        cmd_alias = "GET MID"
        arguments_alias = ""

        @classmethod
        def _validate(cls, pars):
            SMSPowerSupplyDriver.validate_units_T_A(pars[0])

        @classmethod
        def process_result(cls, pars, result):
            print(result)
            return result


    class Update(QueryCommand):
        cmd = "UPDATE"
        arguments = "{}"


    class Get(QueryCommand):
        cmd = "GET"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            pass

        @classmethod
        def process_result(cls, pars, result):
            pass

        @classmethod
        def command(cls, pars):
            cls.validate(pars)
            return (cls.cmd + " " + cls.arguments.format(pars)).strip()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    driver = cmp.DriverComponent(driver_queue, {'library': '',
                                                'address': 'ASRL9::INSTR',
                                                'baud_rate': 9600,
                                                'parity': 'odd',
                                                'data_bits': 7}, SMSPowerSupplyDriver)

    try:
        time.sleep(1000000)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        driver.close()
