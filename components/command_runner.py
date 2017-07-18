import re
import time
from enum import Enum

from components import Driver, logger, RmqResp


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
        cls.calc_num_args()
        if pars is None:
            pars = []
        cls.validate(pars)
        if cls.cmd_alias is None:
            return (cls.cmd + " " + cls.arguments.format(*pars)).strip()
        else:
            return (cls.cmd_alias + " " + cls.arguments_alias.format(*pars)).strip()

    @classmethod
    def raw_command(cls, pars=None):
        cls.calc_num_args()
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
    def execute(cls, component, cmd, pars):
        pass

    @classmethod
    def process_results(cls, component, cmd, pars, result):
        return result


class QueryCommand(Command):
    type = CommandType.GET

    @classmethod
    def execute(cls, component, cmd, pars):
        pass

    @classmethod
    def process_results(cls, component, cmd, pars, result):
        return result


class CommandRunner(RmqResp):
    query_class = QueryCommand
    write_class = WriteCommand

    def __init__(self, command_queue='', command_delay=0.05, **kwargs):
        super().__init__(command_queue, **kwargs)
        self.get_commands = find_subclasses(self, self.query_class)
        self.set_commands = find_subclasses(self, self.write_class)
        self.all_commands = {**self.get_commands, **self.set_commands}
        self.command_delay = command_delay

        self.run_resp_server()

    def split_cmd(self, cmd):
        """Split the command string into a command and a set of parameters"""
        command, *pars = list(filter(None, map(lambda x: x.strip(), re.split(',| |\?', cmd))))
        # Put the question mark back in since it was removed in the split process
        if "?" in cmd:
            command += "?"
        return command, pars

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

            result = self.all_commands[cmd].execute(self, cmd, pars)

            # Get time after receiving reply from instrument
            # Having both times allows us to get an estimate of the time at which the command ran in case the instrument
            # does not report this
            t1 = time.time()

            # Set commands take time to process so there must be a time delay
            if cmd in self.set_commands:
                time.sleep(self.command_delay)

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


class DriverWriteCommand(WriteCommand):
    @classmethod
    def execute(cls, driver, cmd, pars):
        if cls.cmd_alias is None:
            driver.resource.write(cls.command(pars))
        else:
            driver.resource.write(cls.command_alias(pars))


class DriverQueryCommand(QueryCommand):
    @classmethod
    def process_result(cls, driver, cmd, pars, result):
        return result

    @classmethod
    def execute(cls, driver, cmd, pars):
        # Method is either resource.query or resource.write
        if cls.cmd_alias is None:
            result = driver.resource.query(cls.command(pars))
        else:
            result = driver.resource.query(cls.command_alias(pars))
        return cls.process_result(driver, cmd, pars, result)


class DriverCommandRunner(CommandRunner, Driver):
    query_class = DriverQueryCommand
    write_class = DriverWriteCommand

    def __init__(self, driver_queue, driver_params, command_delay=0.05, **kwargs):
        super().__init__(command_queue=driver_queue,
                         command_delay=command_delay,
                         driver_params=driver_params,
                         **kwargs)
