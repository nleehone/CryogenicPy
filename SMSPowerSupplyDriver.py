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


def find_number(string):
    return re.search(r'[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?', string)


class SMSQueryCommand(QueryCommand):
    @classmethod
    def execute(cls, driver, cmd, pars, method):
        # Method is either resource.query or resource.write
        if cls.cmd_alias is None:
            result = method(cls.command(pars))
        else:
            result = method(cls.command_alias(pars))
        # Remove the special \x13 character before processing
        return cls.process_result(driver, cmd, pars, result.replace('\x13', ''))


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
        self.query(self.GetMid.command(['T']))
        print(self.tesla_per_amp)

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

    class GetUnits(SMSQueryCommand):
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

    class GetMid(SMSQueryCommand):
        cmd = "MID?"
        arguments = "{}"
        cmd_alias = "GET MID"
        arguments_alias = ""

        @classmethod
        def _validate(cls, pars):
            SMSPowerSupplyDriver.validate_units_T_A(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            message_type, result = SMSPowerSupplyDriver.strip_message_type(result)
            value = find_number(result)
            units = re.search(r'(TESLA|AMPS)', result)
            if not value or not units:
                raise ValueError("The result '{}' did not match the expected format for the '{}' command".
                                 format(result, cls.cmd_alias))
            value = float(value.group())
            units = units.group()

            if pars[0] == 'T':
                if units == 'TESLA':
                    return value
                else:
                    return value * driver.tesla_per_amp
            else: # pars[0] == 'A' is the only other option because we validated the command before this
                if units == 'TESLA':
                    return value / driver.tesla_per_amp
                else:
                    return value

    class SetTeslaPerAmp(SMSQueryCommand):
        cmd = "TPA"
        arguments = "{}"
        cmd_alias = "SET TPA"
        arguments_alias = "{}"

        @classmethod
        def _validate(cls, pars):
            value = float(pars[0])
            if (value < 0.01 and value != 0) or value > 0.5:
                raise ValueError("The T/A setting must be either 0, or 0.01 and 0.5")

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            print(result)
            return result

    class GetTeslaPerAmp(SMSQueryCommand):
        cmd = "TPA?"
        arguments = ""
        cmd_alias = "GET TPA"
        arguments_alias = ""

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            message_type, result = SMSPowerSupplyDriver.strip_message_type(result)
            found = find_number(result)
            if found:
                tesla_per_amp = float(found.group())
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
                                                 'termination': '\x13'})

    try:
        time.sleep(1000000)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        driver.close()
