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
    """The SMS power supply takes a long time to respond to commands. It is therefore important to use a query for every
    command in order to ensure that we don't overload the instrument with too many commands. The instrument should only
    be communicated with once the previous command has returned."""

    def __init__(self, driver_queue, driver_params, **kwargs):
        super().__init__(driver_queue, driver_params, **kwargs)
        self.tesla_per_amp = 0

        self.startup()

    def set_tesla_per_amp(self, tesla_per_amp):
        self.tesla_per_amp = tesla_per_amp

    def startup(self):
        self.query(self.GetTeslaPerAmp.command())

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

    class GetUnits(QueryCommand):
        cmd = "UNITS?"
        arguments = ""
        cmd_alias = "TESLA"
        arguments_alias = "{}"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            message_type, result = SMSPowerSupplyDriver.strip_message_type(result)
            found = re.search(r'', result)
            if found:
                units = result.group()
                return units
            else:
                raise ValueError("The result '{}' did not match the expected format for the '{}' command".
                                 format(result, cls.cmd_alias))

    class GetMid(QueryCommand):
        cmd = "MID?"
        arguments = "{}"
        cmd_alias = "GET MID\nTESLA"
        arguments_alias = ""

        @classmethod
        def _validate(cls, pars):
            SMSPowerSupplyDriver.validate_units_T_A(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            print(result)
            return result

    class SetTeslaPerAmp(QueryCommand):
        cmd = "TPA"
        arguments = "{}"
        cmd_alias = "SET TPA"
        arguments_alias = "{}"

        @classmethod
        def _validate(cls, pars):
            pass

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
                tesla_per_amp = result.group()
                # Record the T/A setting on the driver. The user should never set this via the instrument front panel
                # so it should be OK to store this whenever it is read
                driver.set_tesla_per_amp(tesla_per_amp)
                return tesla_per_amp
            else:
                raise ValueError("The result '{}' did not match the expected format for the '{}' command".
                                 format(result, cls.cmd_alias))


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
