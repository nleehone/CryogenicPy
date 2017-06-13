import components as cmp
from components import QueryCommand, WriteCommand
import logging
import time
import json
import re

driver_queue = 'SMS.driver'

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

    @staticmethod
    def strip_message_type(message):
        """Separates the message into a message_type and the real message

        Messages come from the SMS in the format '******** Message'
        The 8 * characters represent the message_type and is always followed by a space.
        """
        # Remove any unwanted whitespace at start and end of message
        message = message.strip()
        message_head = message[:8]
        message = message[9:]
        if message_head == "........":
            message_type = "status_confirmation"
        elif message_head == "=======>":
            message_type = "fault_report"
        elif message_head == "------->":
            message_type = "command_information"
        elif message_head == "        ":  # 8 spaces
            message_type = "controller identification"
        else:  # Should have the format HH:MM:SS
            message_type = "status_update"
        return message_type, message

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

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            message_type, result = SMSPowerSupplyDriver.strip_message_type(result)
            found = re.search(r'[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?', result)
            if found:
                print(found, result)
            print(result)


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
