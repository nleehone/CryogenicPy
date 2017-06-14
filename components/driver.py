from . import rmq_component as rmq
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


class DriverComponent(rmq.RmqComponent, Component):
    """Single point of communication with the instrument

    Having a common point of communication prevents multiple parts of the system from
    trying to access the hardware at the same time.

    It is up to the user to make sure that only one instance of the Driver is ever running.
    """
    def __init__(self, driver_queue, driver_params, **kwargs):
        self.create_resource(driver_params)
        self.driver_queue = driver_queue

        super().__init__(**kwargs)

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

    def init_queues(self):
        self.channel.queue_declare(queue=self.driver_queue)

    def process(self):
        method, properties, body = self.channel.basic_get(queue=self.driver_queue,
                                                          no_ack=True)
        if method is not None:
            t0 = time.time()
            cmd_method, result, error = self.process_command(body)
            print("RESULT: ", result, error)
            t1 = time.time()
            reply = {"t0": t0,
                     "t1": t1,
                     "result": result,
                     "error": ["".join(traceback.format_exception(etype=type(e),value=e,tb=e.__traceback__) if e else "") for e in error] if error is not None else ""}
            print(body)
            print(reply, result, error)
            if cmd_method == 'QUERY' or cmd_method == 'READ':
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
                return method, None, error

            cmd = body['CMD']
            results = []
            errors = []
            for command in cmd.split(';'):
                cmd, pars = self.split_cmd(command)
                if method == 'WRITE':
                    result, error = self.write(cmd, pars, command)
                elif method == 'QUERY':
                    result, error = self.query(cmd, pars, command)
                elif method == 'READ':
                    result, error = self.read(cmd, pars, command)
                else:
                    raise AttributeError("Unrecognized METHOD")
                errors.append(error if error is not None else "")
                results.append(result if result is not None else "")
            return method, results, errors
        except AttributeError as e:
            self.logger.warning("Invalid command format: {}".format(body))

    def read(self, cmd, pars, command):
        return self.resource.read(), None

    def write(self, cmd, pars, command):
        result = None
        error = self.check_command(cmd, pars)
        if error is None:
            self.resource.write(command)
        return result, error

    def query(self, cmd, pars, command):
        result = None
        error = self.check_command(cmd, pars)
        if error is None:
            result = self.resource.query(command)
            result = self.process_result(cmd, pars, result)
        return result, error

    def split_cmd(self, cmd):
        # Don't split the commands on the base Driver
        return cmd

    def check_command(self, cmd, pars):
        # Don't check the command on the base Driver
        return None

    def process_result(self, cmd, pars, result):
        # Don't modify the result for the base Driver
        return result


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
    arguments_alias = None
    num_args = 0
    type = None

    @classmethod
    def calc_num_args(cls):
        cls.num_args = len(re.findall("{(\s*)}", cls.arguments))

    @classmethod
    def command(cls, pars):
        cls.validate(pars)
        if cls.cmd_alias is None:
            return (cls.cmd + " " + cls.arguments.format(*pars)).strip()
        else:
            return (cls.cmd_alias + " " + cls.arguments_alias.format(*pars)).strip()

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
    def process_result(cls, driver, cmd, pars, result):
        return result

    @classmethod
    def execute(cls, pars, resource):
        if cls.cmd_alias is None:
            result = resource.query(cls.command(pars))
        else:
            result = resource.query(cls.command_alias(pars))
        return cls.process_result(pars, result)


class CommandDriver(DriverComponent):
    def __init__(self, driver_queue, driver_params, **kwargs):
        super().__init__(driver_queue, driver_params, **kwargs)
        self.get_commands = find_subclasses(self, QueryCommand)
        self.set_commands = find_subclasses(self, WriteCommand)
        self.all_commands = {**self.get_commands, **self.set_commands}

    def write(self, cmd, pars, command):
        result = None
        error = self.check_command(cmd, pars)
        if error is None:
            self.resource.write(self.all_commands[cmd].command(pars))
        return result, error

    def query(self, cmd, pars, command):
        result = None
        error = self.check_command(cmd, pars)
        if error is None:
            result = self.resource.query(self.get_commands[cmd].command(pars))
            result = self.get_commands[cmd].process_result(self, cmd, pars, result)
        return result, error

    def check_command(self, cmd, pars):
        try:
            self.all_commands[cmd].validate(pars)
        except Exception as e:
            return e

    def split_cmd(self, cmd):
        # Split the message into a command and a set of parameters
        command, *pars = list(filter(None, map(lambda x: x.strip(), re.split(',| |\?', cmd))))
        # Put the question mark back in since it was removed in the split process
        if "?" in cmd:
            command += "?"
        return command, pars


class IEEE488_2_CommonCommands(CommandDriver):
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
