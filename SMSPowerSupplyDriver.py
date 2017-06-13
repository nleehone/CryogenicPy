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
    def __init__(self, driver_queue, driver_params, **kwargs):
        super().__init__(driver_queue, driver_params, **kwargs)
        self.tesla_per_amp = 0

    @staticmethod
    def validate_units_T_A(units):
        if units not in ['T', 'A']:
            raise ValueError("Units must be either T or A, instead got {}".format(units))

    class GetMid(QueryCommand):
        cmd = "MID?"
        arguments = "{}"
        cmd_alias = "GET MID"
        arguments_alias = ""

        @classmethod
        def _validate(cls, pars):
            SMSPowerSupplyDriver.validate_units_T_A(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            print(result)
            return result

    class GetTeslaPerAmp(QueryCommand):
        cmd = "TPA?"
        arguments = ""
        cmd_alias = "GET TPA"
        arguments_alias = ""


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    driver = SMSPowerSupplyDriver(driver_queue, {'library': '',
                                                'address': 'ASRL9::INSTR',
                                                'baud_rate': 9600,
                                                'parity': 'none',
                                                'data_bits': 8,
                                                'termination': 'x13'})

    try:
        time.sleep(1000000)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        driver.close()
