from . import rmq_component as rmq
from .components import Component
import time
import visa
import re
import traceback
from enum import Enum


class DriverComponent(rmq.RmqComponent, Component):
    """Single point of communication with the instrument

    Having a common point of communication prevents multiple parts of the system from
    trying to access the hardware at the same time.

    It is up to the user to make sure that only one instance of the Driver is ever running.
    """
    def __init__(self, driver_queue, driver_params, driver_class, **kwargs):
        self.driver = driver_class(driver_params)
        self.driver_queue = driver_queue
        super().__init__(**kwargs)

    def init_queues(self):
        self.channel.queue_declare(queue=self.driver_queue)

    def process(self):
        method, properties, body = self.channel.basic_get(queue=self.driver_queue,
                                                          no_ack=True)
        if method is not None:
            t0 = time.time()
            result, error = self.process_command(body)
            print("RESULT: ", result, error)
            t1 = time.time()
            reply = {"t0": t0,
                     "t1": t1,
                     "result": result,
                     "error": ["".join(traceback.format_exception(etype=type(e),value=e,tb=e.__traceback__) if e else "") for e in error] if error is not None else ""}
            print(body)
            print(reply, result, error)
            if result != [] or error != []:
                print(properties.reply_to, reply)
                self.channel.basic_publish('', routing_key=properties.reply_to, body=json.dumps(reply))

    def process_command(self, body):
        # METHOD: {READ, WRITE, QUERY}
        body = json.loads(body.decode('utf-8'))
        try:
            method = body['METHOD']
            if method not in ['WRITE', 'QUERY', 'READ']:
                error = "Unrecognized METHOD: {}".format(method)
                self.logger.warning(error)
                return None, error

            cmd = body['CMD']
            results = []
            errors = []
            for command in cmd.split(';'):
                if method == 'WRITE':
                    self.driver.write(command)
                elif method == 'QUERY':
                    r, e = self.driver.query(command)
                    results.append(r)
                    errors.append(e if e is not None else "")
                elif method == 'READ':
                    r, e = self.driver.read()
                    results.append(r)
                    errors.append(e)
            return results, errors
        except AttributeError:
            self.logger.warning("Invalid command format: {}".format(body))


def validate_num_params(pars, num):
    if len(pars) != num:
        raise ValueError("Number of parameters ({}) does not match expectation ({})".format(len(pars), num))


def validate_range(par, low, high):
    if par < low or par > high:
        raise ValueError("Parameter must be in the range [{}:{}], but got {}".format(low, high, par))


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
        return self.resource.query(msg)

    def check_command(self, msg):
        # Don't check the command on the base Driver
        return None


class CommandType(Enum):
    GET = 0
    SET = 1


class Command(object):
    cmd = ""
    cmd_alias = None
    arguments = ""
    arguments_alias = None
    num_args = 0
    type = None

    @classmethod
    def calc_num_args(cls):
        cls.num_args = len(re.findall("{(\s*)}", cls.arguments))

    @classmethod
    def command(cls, pars):
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
    def command_alias(cls, pars):
        cls.validate(pars)
        return (cls.cmd_alias + " " + cls.arguments_alias.format(*pars)).strip()


class WriteCommand(Command):
    type = CommandType.SET

    @classmethod
    def execute(cls, pars, resource):
        if cls.cmd_alias is None:
            resource.write(cls.command(pars))
        else:
            cls.validate(pars)
            resource.write(cls.command_alias(pars))


class QueryCommand(Command):
    type = CommandType.GET

    @classmethod
    def process_result(cls, pars, result):
        return result

    @classmethod
    def execute(cls, pars, resource):
        if cls.cmd_alias is None:
            result = resource.query(cls.command(pars))
        else:
            result = resource.query(cls.command_alias(pars))
        return cls.process_result(pars, result)


class CommandDriver(Driver):
    def __init__(self, params):
        super().__init__(params)
        self.get_commands = find_subclasses(self, QueryCommand)
        self.set_commands = find_subclasses(self, WriteCommand)
        self.all_commands = {**self.get_commands, **self.set_commands}

    def write(self, msg):
        """
        :param msg (str): Message to be sent
        :return (int): Number of bytes written
        """
        error = self.check_command(msg)
        cmd, pars = self.split_cmd(msg)
        if error:
            return None, error
        return self.all_commands[cmd].execute(pars, self.resource), None

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
        cmd, pars = self.split_cmd(msg)
        return self.get_commands[cmd].execute(pars, self.resource), None

    def check_command(self, cmd):
        cmd, pars = self.split_cmd(cmd)
        try:
            self.all_commands[cmd].validate(pars)
        except Exception as e:
            return e


class IEEE488_2_CommonCommands(CommandDriver):
    def split_cmd(self, cmd):
        # Split the message into a command and a set of parameters
        command, *pars = list(filter(None, map(lambda x: x.strip(), re.split(',| |\?', cmd))))
        # Put the question mark back in since it was removed in the split process
        if "?" in cmd:
            command += "?"
        return command, pars

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
        def process_result(cls, pars, result):
            return int(result)

    class GetEventStatusRegister(QueryCommand):
        cmd = "*ESR?"

        @classmethod
        def process_result(cls, pars, result):
            return int(result)

    class GetIdentification(QueryCommand):
        cmd = "*IDN?"

    class SetOperationComplete(WriteCommand):
        cmd = "*OPC"

    class GetOperationComplete(QueryCommand):
        cmd = "*OPC?"

        @classmethod
        def process_result(cls, pars, result):
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
        def process_result(cls, pars, result):
            return int(result)

    class GetStatusByte(QueryCommand):
        cmd = "*STB?"

        @classmethod
        def process_result(cls, pars, result):
            return int(result)

    class SelfTest(WriteCommand):
        cmd = "*TST?"

    class Wait(WriteCommand):
        cmd = "*WAI"
