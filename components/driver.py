from .rmq_component import RmqResp, logger
from .components import Component
import time
import json
import visa
import re
import traceback
from enum import Enum


def find_subclasses(obj, type):
    results = {}
    for attrname in dir(obj.__class__):
        o = getattr(obj, attrname)
        try:
            if issubclass(o, type):
                o.calc_num_args()
                results[o.cmd] = o
        except TypeError:
            pass
    return results


class Driver(RmqResp, Component):
    """Single point of communication with the instrument

    Having a common point of communication prevents multiple parts of the system from
    trying to access the hardware at the same time.

    It is up to the user to make sure that only one instance of the Driver is ever running.
    """
    def __init__(self, driver_queue, driver_params, **kwargs):
        self.create_resource(driver_params)
        super().__init__(driver_queue, **kwargs)

    def create_resource(self, driver_params):
        rm = visa.ResourceManager(driver_params.get('library', ''))
        self.resource = rm.open_resource(driver_params['address'])

        if 'baud_rate' in driver_params:
            self.resource.baud_rate = driver_params['baud_rate']
        if 'data_bits' in driver_params:
            self.resource.data_bits = driver_params['data_bits']
        if 'parity' in driver_params:
            self.resource.parity = {
                'odd': visa.constants.Parity.odd,
                'even': visa.constants.Parity.even,
                'none': visa.constants.Parity.none
            }[driver_params['parity']]
        if 'stop_bits' in driver_params:
            self.resource.stop_bits = {
                'one': visa.constants.StopBits.one
            }[driver_params['stop_bits']]
        if 'termination' in driver_params:
            self.resource.termination = {
                'CR': self.resource.CR,
                'LF': self.resource.LF,
            }.get(driver_params['termination'], driver_params['termination'])

    def process_message(self, message):
        commands = message['CMD']
        results = []
        errors = []
        try:
            for command in commands.split(';'):
                result, error = self.execute_command(command)
                errors.append(error if error is not None else "")
                results.append(result if result is not None else "")
        except AttributeError:
            logger.exception("Received message with improper format")
        return results

    def execute_command(self, command):
        pass


def validate_num_params(pars, num):
    if len(pars) != num:
        raise ValueError("Number of parameters ({}) does not match expectation ({})".format(len(pars), num))


def validate_range(par, low, high):
    if par < low or par > high:
        raise ValueError("Parameter must be in the range [{}:{}], but got {}".format(low, high, par))


class CommandType(Enum):
    GET = 0
    SET = 1


class Command(object):
    cmd = ""
    cmd_alias = None
    arguments = ""
    arguments_alias = ""
    num_args = 0
    type = None

    @classmethod
    def calc_num_args(cls):
        cls.num_args = len(re.findall("{(\s*)}", cls.arguments))

    @classmethod
    def command(cls, pars=None):
        if pars is None:
            pars = []
        cls.validate(pars)
        return (cls.cmd + " " + cls.arguments.format(*pars)).strip()

    @classmethod
    def validate(cls, pars):
        validate_num_params(pars, cls.num_args)
        cls._validate(pars)

    @classmethod
    def _validate(cls, pars):
        pass

    @classmethod
    def command_alias(cls, pars=None):
        if pars is None:
            pars = []
        cls.validate(pars)
        return (cls.cmd_alias + " " + cls.arguments_alias.format(*pars)).strip()


class WriteCommand(Command):
    type = CommandType.SET

    @classmethod
    def execute(cls, pars, method):
        if cls.cmd_alias is None:
            method(cls.command(pars))
        else:
            method(cls.command_alias(pars))


class QueryCommand(Command):
    type = CommandType.GET

    @classmethod
    def process_result(cls, driver, cmd, pars, result):
        return result

    @classmethod
    def execute(cls, driver, cmd, pars, method):
        # Method is either resource.query or resource.write
        if cls.cmd_alias is None:
            result = method(cls.command(pars))
        else:
            result = method(cls.command_alias(pars))
        return cls.process_result(driver, cmd, pars, result)


class CommandDriver(Driver):
    def __init__(self, driver_queue, driver_params, **kwargs):
        super().__init__(driver_queue, driver_params, **kwargs)
        self.get_commands = find_subclasses(self, QueryCommand)
        self.set_commands = find_subclasses(self, WriteCommand)
        self.all_commands = {**self.get_commands, **self.set_commands}

    def split_cmd(self, cmd):
        """Split the command string into a command and a set of parameters"""
        command, *pars = list(filter(None, map(lambda x: x.strip(), re.split(',| |\?', cmd))))
        # Put the question mark back in since it was removed in the split process
        if "?" in cmd:
            command += "?"
        return command, pars

    def execute_command(self, command):
        """Run the command and create a result object.
        The result object will be of the form
        {
            t0: time before sending command to instrument. -1 if there was a validation error
            t1: time after receiving reply from instrument. -1 if there was a validation error
            error: error message caused by validation problem or execution problem
            result: object containing the response from the instrument
        }
        """
        result = None
        t0 = t1 = -1
        cmd, pars = self.split_cmd(command)
        error = self.check_command(cmd, pars)

        if error is None:
            # Get time before sending command to instrument
            t0 = time.time()

            result = self.all_commands[cmd].execute(self, cmd, pars, self.resource)

            # Get time after receiving reply from instrument
            # Having both times allows us to get an estimate of the time at which the command ran in case the instrument
            # does not report this
            t1 = time.time()

        command_result = {'t0': t0,
                          't1': t1,
                          'error': str(error) if error is not None else '',
                          'result': result if result is not None else ''}

        logger.debug(command_result)
        return command_result, error

    def check_command(self, cmd, pars):
        """Make sure that the command has the proper format and correct parameters"""
        try:
            self.all_commands[cmd].validate(pars)
        except Exception as e:
            logger.exception("Command '{}' failed validation with parameters {}".format(cmd, pars))
            return e


class IEEE488_CommonCommands(object):
    """Common IEEE-488 commands are defined here. To use this class, include it in the Driver's definition:
    class SomeDriver(IEEE488_CommonCommands, Driver):
    """
    class ClearStatus(WriteCommand):
        cmd = "*CLS"

    class SetEventStatusEnable(WriteCommand):
        cmd = "*ESE"
        arguments = "{}"
        num_args = 1

        @classmethod
        def _validate(cls, pars):
            validate_range(pars[0], 0, 255)

    class GetEventStatusEnable(QueryCommand):
        cmd = "*ESE?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetEventStatusRegister(QueryCommand):
        cmd = "*ESR?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetIdentification(QueryCommand):
        cmd = "*IDN?"

    class SetOperationComplete(WriteCommand):
        cmd = "*OPC"

    class GetOperationComplete(QueryCommand):
        cmd = "*OPC?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class ResetInstrument(WriteCommand):
        cmd = "*RST"

    class SetServiceRequestEnable(WriteCommand):
        cmd = "*SRE"
        arguments = "{}"
        num_args = 1

    class GetServiceRequestEnable(QueryCommand):
        cmd = "*SRE?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetStatusByte(QueryCommand):
        cmd = "*STB?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class SelfTest(WriteCommand):
        cmd = "*TST?"

    class Wait(WriteCommand):
        cmd = "*WAI"
