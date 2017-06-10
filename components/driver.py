import visa
import re
from enum import Enum


def validate_num_params(pars, num):
    if len(pars) != num:
        raise ValueError("Number of parameters ({}) does not match expectation ({})".format(len(pars), num))


def validate_range(par, low, high):
    if par < low or par > high:
        raise ValueError("Parameter must be in the range [{}:{}], but got {}".format(low, high, par))


class Driver(object):
    """Base class for all instrument drivers"""
    def __init__(self, params):
        rm = visa.ResourceManager(params.get('library', ''))
        self.resource = rm.open_resource(params['address'])
        if 'baud_rate' in params:
            self.resource.baud_rate = params['baud_rate']
        if 'data_bits' in params:
            self.resource.data_bits = params['data_bits']
        if 'parity' in params:
            self.resource.parity = {
                'odd': visa.constants.Parity.odd,
                'even': visa.constants.Parity.even,
                'none': visa.constants.Parity.none
            }[params['parity']]
        if 'stop_bits' in params:
            self.resource.stop_bits = {
                'one': visa.constants.StopBits.one
            }[params['stop_bits']]
        if 'termination' in params:
            self.resource.termination = {
                'CR': self.resource.CR,
                'LF': self.resource.LF
            }[params['termination']]

    def write(self, msg):
        """
        :param msg (str): Message to be sent
        :return (int): Number of bytes written
        """
        error = self.check_command(msg)
        if error:
            return None, error
        return self.resource.write(msg), None

    def read(self):
        """
        Read a string from the device.

        Reads until the termination character is found
        :return (str): The string with termination character stripped
        """
        return self.resource.read(), None

    def query(self, msg):
        """
        Sequential write and read
        :param msg (str): Message to be sent
        :return (str): The string with termination character stripped
        """
        error = self.check_command(msg)
        if error:
            return None, error
        return self.process_response(self.resource.query(msg), msg)

    def check_command(self, msg):
        # Don't check the command on the base Driver
        return None

    def process_response(self, resp, msg):
        # Pass the raw response back for the base Driver
        return resp, None


class CommandType(Enum):
    GET = 0
    SET = 1


class Command(object):
    cmd = ""
    arguments = ""
    num_args = 0
    type = None

    @classmethod
    def command(cls, pars):
        cls.validate(pars)
        return (cls.cmd + " " + cls.arguments.format(pars)).strip()

    @classmethod
    def validate(cls, pars):
        validate_num_params(pars, cls.num_args)
        cls._validate(pars)

    @classmethod
    def _validate(cls, pars):
        pass


class SetCommand(Command):
    type = CommandType.SET


class GetCommand(Command):
    type = CommandType.GET

    @classmethod
    def result(cls, pars, result):
        return result


def find_subclasses(obj, type):
    results = {}
    for attrname in dir(obj.__class__):
        o = getattr(obj, attrname)
        try:
            if issubclass(o, type):
                results[o.cmd] = o
        except TypeError:
            pass
    return results


class IEEE488_2_CommonCommands(Driver):
    def __init__(self, params):
        super().__init__(params)
        self.get_commands = find_subclasses(self, GetCommand)
        self.set_commands = find_subclasses(self, SetCommand)
        self.all_commands = {**self.get_commands, **self.set_commands}

    def split_cmd(self, cmd):
        # Split the message into a command and a set of parameters
        command, *pars = list(filter(None, map(lambda x: x.strip(), re.split(',| |\?', cmd))))
        # Put the question mark back in since it was removed in the split process
        if "?" in cmd:
            command += "?"
        return command, pars

    def check_command(self, cmd):
        cmd, pars = self.split_cmd(cmd)
        try:
            self.all_commands[cmd].validate(pars)
            """try:
            {
                "*CLS": IEEE488_2_CommonCommands.clear_status_validate,
                "*ESE": IEEE488_2_CommonCommands.set_event_status_enable_validate,
                "*ESE?": IEEE488_2_CommonCommands.get_event_status_enable_validate,
                "*ESR?": IEEE488_2_CommonCommands.get_event_status_register_validate,
                "*IDN?": IEEE488_2_CommonCommands.get_identification_validate,
                "*OPC": IEEE488_2_CommonCommands.set_operation_complete_validate,
                "*OPC?": IEEE488_2_CommonCommands.get_operation_complete_validate,
                "*RST": IEEE488_2_CommonCommands.reset_instrument_validate,
                "*SRE": IEEE488_2_CommonCommands.set_service_request_enable_validate,
                "*SRE?": IEEE488_2_CommonCommands.get_service_request_enable_validate,
                "*STB?": IEEE488_2_CommonCommands.get_status_byte_validate,
                "*TST?": IEEE488_2_CommonCommands.self_test_validate,
                "*WAI": IEEE488_2_CommonCommands.wait_validate,
            }[cmd](pars)"""
        except Exception as e:
            return e

    def process_response(self, response, cmd):
        cmd, pars = self.split_cmd(cmd)
        try:
            processed = self.get_commands[cmd].result(pars, response)
            """processed = {
                "*ESE?": IEEE488_2_CommonCommands.get_event_status_enable_response,
                "*ESR?": IEEE488_2_CommonCommands.get_event_status_register_response,
                "*IDN?": IEEE488_2_CommonCommands.get_identification_response,
                "*OPC?": IEEE488_2_CommonCommands.get_operation_complete_response,
                "*SRE?": IEEE488_2_CommonCommands.get_service_request_enable_response,
                "*STB?": IEEE488_2_CommonCommands.get_status_byte_response,
            }[cmd](pars, response)"""
        except Exception as e:
            return None, e
        return processed, None

    class ClearStatus(SetCommand):
        cmd = "*CLS"

    class SetEventStatusEnable(SetCommand):
        cmd = "*ESE"
        format = "{}"
        num_args = 1

        @classmethod
        def _validate(cls, pars):
            validate_range(pars[0], 0, 255)

    class GetEventStatusEnable(GetCommand):
        cmd = "*ESE?"

        @classmethod
        def result(cls, pars, result):
            return int(result)

    class GetEventStatusRegister(GetCommand):
        cmd = "*ESR?"

        @classmethod
        def result(cls, pars, result):
            return int(result)

    class GetIdentification(GetCommand):
        cmd = "*IDN?"

    class SetOperationComplete(SetCommand):
        cmd = "*OPC"

    class GetOperationComplete(GetCommand):
        cmd = "*OPC?"

        @classmethod
        def result(cls, pars, result):
            return int(result)

    class ResetInstrument(SetCommand):
        cmd = "*RST"

    class SetServiceRequestEnable(SetCommand):
        cmd = "*SRE"
        format = "{}"
        num_args = 1

    class GetServiceRequestEnable(GetCommand):
        cmd = "*SRE?"

        @classmethod
        def result(cls, pars, result):
            return int(result)

    class GetStatusByte(GetCommand):
        cmd = "*STB?"

        @classmethod
        def result(cls, pars, result):
            return int(result)

    class SelfTest(SetCommand):
        cmd = "*TST?"

    class Wait(SetCommand):
        cmd = "*WAI"
