import pyvisa

import components as cmp
from components import QueryCommand, DriverQueryCommand, DriverCommandRunner
import time
import re
import configparser
import sys


def find_number(string):
    return re.search(r'[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?', string)


def find_numbers(string):
    return list(re.finditer(r'[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?', string))


def convert_units(driver, value, units):
    result = driver.resource.query(driver.GetUnits.command())
    found = re.search(r'(TESLA|AMPS)', result)
    if found:
        instr_units = found.group()
        instr_units = 'T' if instr_units == 'TESLA' else 'A'
    else:
        raise ValueError("Could not get the instrument's units")

    if units == 'T':
        if instr_units == 'A':
            value /= driver.tesla_per_amp
    else:
        if instr_units == 'T':
            value *= driver.tesla_per_amp
    return value


class SMSQueryCommand(DriverQueryCommand):
    @classmethod
    def execute(cls, driver, cmd, pars):
        try:
            result = driver.resource.query(cls.command(pars))
        except pyvisa.errors.VisaIOError as e:
            #print("Could not connect to the instrument. Set the instrument to remote mode and restart the driver")
            #print(e)
            return None
        # Remove the special \x13 character before processing
        result = result.replace('\x13', '')
        print("RES", result)
        message_type, result = SMSPowerSupplyDriver.strip_message_type(result)
        print(message_type, result)
        if 'REMOTE CONTROL: DISABLED' in result or 'REMOTE CONTROL: ENABLED' in result:
            return None
        print(result)
        return cls.process_result(driver, cmd, pars, result)


class SMSPowerSupplyDriver(DriverCommandRunner):
    """The SMS power supply takes a long time to respond to commands. It is therefore important to use a query for every
    command in order to ensure that we don't overload the instrument with too many commands. The instrument should only
    be communicated with once the previous command has returned.

    Since there is no way to get the setpoint on the SMS120C we have to use a workaround. The MID point can be used to
    track the setpoint as long as MAX is set to the maximum value that the power supply can output. Then MID can be
    set to the same value as MAX to initiate a ramp to maximum value. This works the same way for ZERO.
    """

    def write(self, command):
        time.sleep(1)
        return 0, None

    def query(self, command):
        time.sleep(1)
        return 0, None

    def __init__(self, driver_queue, driver_params, **kwargs):
        super().__init__(driver_queue, driver_params, **kwargs)
        self.tesla_per_amp = 0

        self.run_server_thread()
        self.startup()

    def set_tesla_per_amp(self, tesla_per_amp):
        self.tesla_per_amp = tesla_per_amp

    def startup(self):
        try:
            self.tesla_per_amp = float(self.GetTeslaPerAmp.execute(self, self.GetTeslaPerAmp.cmd, []))
            print(self.tesla_per_amp)
        except TypeError:
            print("Could not start the driver because the instrument was not set to remote mode")
            quit(-1)

        self.resource.query(self.GetMid.command(['T']))

    @staticmethod
    def validate_units_T_A(units):
        if units not in ['T', 'A']:
            raise ValueError("Units must be either T or A, instead got {}".format(units))

    @staticmethod
    def validate_ramp_to(ramp_to):
        if ramp_to not in ["ZERO", "MID", "MAX"]:
            raise ValueError("Ramp-to must be one of ['ZERO', 'MID', 'MAX'], instead got {}".format(ramp_to))

    @staticmethod
    def strip_message_type(message):
        """Separates the message into a message_type and the real message

        Messages come from the SMS in the format '******** Message'
        The 8 * characters represent the message_type and is always followed by a space.
        """
        # Remove any unwanted whitespace at start and end of message
        message = message.strip()
        message = message.replace('\x13', '')
        message_head = message[:8]
        message = message[9:]
        if message[:10] == "!!------->":
            message = message[11:]
            message_type = "command_information"
        else:
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

    class GetFilterStatus(SMSQueryCommand):
        cmd = "FILTER?"
        cmd_alias = "FILTER"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            found = re.search(r'(ON|OFF)', result)
            if not found:
                raise ValueError("The result '{}' did not match the expected format for the '{}' command".format(
                    result, cls.cmd))
            return 0 if found.group() == 'OFF' else 1

    class GetOutput(SMSQueryCommand):
        cmd = "OUTP?"
        arguments = "{}"
        cmd_alias = "GET OUTPUT"
        arguments_alias = ""

        #@classmethod
        #def execute(cls, driver, cmd, pars, method):
        ##    value = convert_units(driver, float(pars[0]), pars[1])
        #    result = method(cls.cmd_alias + " " + cls.arguments_alias.format(value))
        #    return cls.process_result(driver, cmd, pars, result)

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            print(result)
            values = find_numbers(result)
            units = re.search(r'(TESLA|AMPS)', result)
            if not values or not units:
                raise ValueError("The result '{}' did not match the expected format for the '{}' command".
                                 format(result, cls.cmd_alias))
            output = float(values[0].group())
            print("OUTPUT VALUE:", output, units)
            units = units.group()

            if pars[0] == 'T' and units == 'AMPS':
                output *= driver.tesla_per_amp
            elif pars[0] == 'A' and units == 'TESLA':  # pars[0] == 'A' is the only other option because we validated the command before this
                output /= driver.tesla_per_amp
            print("OUTPUT VALUE:", output)

            return {'Output': output,
                    'Voltage': float(values[1].group()),
                    'Persistent': 0}

    class SetFilterStatus(SMSQueryCommand):
        cmd = "FILTER"
        arguments = "{}"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return ""

    class GetUnits(SMSQueryCommand):
        cmd = "UNITS?"
        arguments = ""
        cmd_alias = "TESLA"
        arguments_alias = ""

        @classmethod
        def process_result(cls, driver, cmd, pars, result):

            found = re.search(r'(TESLA|AMPS)', result)
            if found:
                units = found.group()
                return 'T' if units == 'TESLA' else 'A'
            else:
                raise ValueError("The result '{}' did not match the expected format for the '{}' command".
                                 format(result, cls.cmd_alias))

    class SetUnits(SMSQueryCommand):
        cmd = "UNITS"
        arguments = "{}"
        cmd_alias = "TESLA"
        arguments_alias = "{}"

        @classmethod
        def execute(cls, driver, cmd, pars):
            value = 1 if pars[0] == 'T' else 0
            result = driver.resource.query(cls.cmd_alias + " " + cls.arguments_alias.format(value))
            return cls.process_result(driver, cmd, pars, result)

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return ""

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

    class SetMid(SMSQueryCommand):
        cmd = "MID"
        arguments = "{},{}"
        cmd_alias = "SET MID"
        arguments_alias = "{}"

        @classmethod
        def _validate(cls, pars):
            SMSPowerSupplyDriver.validate_units_T_A(pars[1])

        @classmethod
        def execute(cls, driver, cmd, pars):
            value = convert_units(driver, float(pars[0]), pars[1])
            result = driver.resource.query(cls.cmd_alias + " " + cls.arguments_alias.format(value))
            return cls.process_result(driver, cmd, pars, result)

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            #if message_type == "command_information":
            #    return result
            return ""

    class GetSetpoint(GetMid):
        """The get setpoint command returns the MID value in order to get around the limitation of not being able to
        query the setpoint on the SMS120C. This command is purely for clarity when using the driver and does exactly the
        same thing that "GET MID" does
        """
        cmd = "SETP?"

    class SetSetpoint(SetMid):
        """The set setpoint command sets the MID value in order to get around the limitation of not being able to
        query the setpoint on the SMS120C. This command is purely for clarity when using the driver and does exactly the
        same thing that "SET MID" does
        """
        cmd = "SETP"

    class GetMax(GetMid):
        cmd = "MAX?"
        cmd_alias = "GET MAX"

    class SetMax(SetMid):
        cmd = "MAX"
        cmd_alias = "SET MAX"

    class SetRamp(SMSQueryCommand):
        cmd = "RAMP"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            SMSPowerSupplyDriver.validate_ramp_to(pars[0])

        @classmethod
        def execute(cls, driver, cmd, pars, method):
            result = driver.resource.write(cls.command(pars))
            return cls.process_result(driver, cmd, pars, '')

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return result

    class GetRampRate(SMSQueryCommand):
        cmd = "RATE?"
        arguments = "{}"
        cmd_alias = "GET RATE"
        arguments_alias = ""

        @classmethod
        def _validate(cls, pars):
            SMSPowerSupplyDriver.validate_units_T_A(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            value = find_number(result)
            if not value:
                raise ValueError("The result '{}' did not match the expected format for the '{}' command".
                                 format(result, cls.cmd_alias))
            value = float(value.group())

            if pars[0] == 'T':
                return value * driver.tesla_per_amp
            else:
                return value

    class SetRampRate(SMSQueryCommand):
        cmd = "RATE"
        arguments = "{},{}"
        cmd_alias = "SET RAMP"
        arguments_alias = "{}"

        @classmethod
        def _validate(cls, pars):
            SMSPowerSupplyDriver.validate_units_T_A(pars[1])

        @classmethod
        def execute(cls, driver, cmd, pars):
            value = float(pars[0])
            if pars[1] == 'T':
                value /= driver.tesla_per_amp
            result = driver.resource.query(cls.cmd_alias + " " + cls.arguments_alias.format(value))
            return cls.process_result(driver, cmd, pars, result)

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            #message_type, result = SMSPowerSupplyDriver.strip_message_type(result)
            #if message_type == "command_information":
            #    return result
            return ""

    class GetVoltageLimit(SMSQueryCommand):
        cmd = "VLIM?"
        arguments = ""
        cmd_alias = "GET VL"
        arguments_alias = ""

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            value = find_number(result)
            if not value:
                raise ValueError("The result '{}' did not match the expected format for the '{}' command".
                                 format(result, cls.cmd_alias))
            return float(value.group())

    class SetVoltageLimit(SMSQueryCommand):
        cmd = "VLIM"
        arguments = "{}"
        cmd_alias = "SET LIMIT"
        arguments_alias = "{}"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return ""

    class GetHeaterVoltage(SMSQueryCommand):
        cmd = "HTRV?"
        cmd_alias = "GET HV"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            value = find_number(result)
            if not value:
                raise ValueError("The result '{}' did not match the expected format for the '{}' command".
                                 format(result, cls.cmd_alias))
            return float(value.group())

    class SetHeaterVoltage(SMSQueryCommand):
        cmd = "HTRV"
        arguments = "{}"
        cmd_alias = "SET HEATER"
        arguments_alias = "{}"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return ""

    class GetPauseState(SMSQueryCommand):
        cmd = "PAUSE?"
        cmd_alias = "PAUSE"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            status = re.search(r'(ON|OFF)', result)
            if not status:
                raise ValueError("The result '{}' did not match the expected format for the '{}' command".
                                 format(result, cls.cmd_alias))
            return 0 if status.group() == 'OFF' else 1

    class SetPauseState(SMSQueryCommand):
        cmd = "PAUSE"
        arguments = "{}"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return ""

    class GetPersistentHeaterStatus(SMSQueryCommand):
        cmd = "HTR?"
        arguments = "{}"
        cmd_alias = "HEATER"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            value = find_number(result)
            units = re.search(r'(TESLA|AMPS)', result)
            status = re.search(r'(ON|OFF)', result)
            if not status:
                raise ValueError("The result '{}' did not match the expected format for the '{}' command".
                                 format(result, cls.cmd_alias))
            if value:
                value = float(value.group())
                if units == 'TESLA' and pars[0] == 'A':
                    value /= driver.tesla_per_amp
                elif units == 'AMPS' and pars[0] == 'T':
                    value *= driver.tesla_per_amp
            else:
                value = 0
            return {'Status': 0 if status.group() == 'OFF' else 1,
                    'Switched off at': value}

    class SetPersistentHeaterStatus(SMSQueryCommand):
        cmd = "HTR"
        arguments = "{}"
        cmd_alias = "HEATER"
        arguments_alias = "{}"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return ""

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
    config = configparser.ConfigParser()
    config.read(sys.argv[1])
    SMS_config = config['SMSPowerSupply']

    driver = SMSPowerSupplyDriver(SMS_config['queue_name'], {'library': '',
                                                 'address': SMS_config['address'],
                                                 'baud_rate': SMS_config.getint('baud_rate'),
                                                 'parity': SMS_config['parity'],
                                                 'data_bits': SMS_config.getint('data_bits'),
                                                 'termination': SMS_config['termination']})

    try:
        time.sleep(1000000)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        driver.close()
