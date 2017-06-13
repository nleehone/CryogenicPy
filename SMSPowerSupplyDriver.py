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
    def __init__(self, params):
        super().__init__(params)
        self.tesla_per_amp = 0

    def split_cmd(self, cmd):
        # Split the message into a command and a set of parameters
        command, *pars = list(filter(None, map(lambda x: x.strip(), re.split(',| |\?', cmd))))
        # Put the question mark back in since it was removed in the split process
        if "?" in cmd:
            command += "?"
        return command, pars

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
        def process_result(cls, pars, result):
            print(result)
            return result

    class GetTeslaPerAmp(QueryCommand):
        cmd = "TPA?"
        arguments = ""
        cmd_alias = "GET TPA"
        arguments_alias = ""


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


class SMSPowerSupplyDriverComponent(cmp.DriverComponent):
    def __init__(self, driver_queue, driver_params, driver_class, **kwargs):
        super.__init__(driver_queue, driver_params, driver_class, kwargs)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    driver = cmp.DriverComponent(driver_queue, {'library': '',
                                                'address': 'ASRL9::INSTR',
                                                'baud_rate': 9600,
                                                'parity': 'none',
                                                'data_bits': 8,
                                                'termination': 'x13'}, SMSPowerSupplyDriver)

    try:
        time.sleep(1000000)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        driver.close()
