import os
import visa
import json
import rmq_component as rmq
import logging


# Get the directory's full path
dir_path = os.path.dirname(os.path.realpath(__file__))


class Driver(object):
    """Base class for all instrument drivers"""
    def __init__(self, params):
        rm = visa.ResourceManager()
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
        return self.resource.write(msg)

    def read(self):
        """
        Read a string from the device.

        Reads until the termination character is found
        :return (str): The string with termination character stripped
        """
        return self.resource.read()

    def query(self, msg):
        """
        Sequential write and read
        :param msg (str): Message to be sent
        :return (str): The string with termination character stripped
        """
        return self.resource.query(msg)


class DriverComponent(rmq.RmqComponentRPC):
    """Single point of communication with the instrument

    Having a common point of communication prevents multiple parts of the system from trying to access the hardware
    at the same time.

    It is up to the user to make sure that only one instance of the Driver is ever running.
    """
    def __init__(self, params):
        super().__init__()
        self.setup_logger()
        self.driver = Driver(params)

    def setup_logger(self):
        self.logger = logging.getLogger(type(self).__name__)
        self.logger.setLevel(logging.INFO)

        # Create a file handler
        handler = logging.FileHandler("{}/{}.log".format(dir_path, __name__))
        handler.setLevel(logging.INFO)

        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def direct_reply(self, channel, method, properties, body):
        reply = self.process_command(body)

        if reply is not None:
            self.direct_reply_to()

    def process_command(self, body):
        # METHOD: {READ, WRITE, QUERY}
        body = json.loads(body.decode('utf-8'))
        try:
            method = body['METHOD']
            cmd = body['CMD']
            if method == 'WRITE':
                self.driver.write(cmd)
            elif method == 'QUERY':
                return json.dumps(self.driver.query(cmd))
            elif method == 'READ':
                return json.dumps(self.driver.read())
            else:
                self.logger.warning("Unrecognized METHOD: {}".format(method))
        except AttributeError:
            self.logger.warning("Invalid command: {}".format(body))


class Driver(rmq.RmqComponentRPC):
    def __init__(self, resource):
        super().__init__()
        self.resource = resource

    def direct_reply(self, channel, method, properties, body):
        body = json.loads(body)
        try:
            command_method = body['METHOD']
            command = body['CMD']

            if command_method == 'WRITE':
            elif command_method == 'READ':
            elif command_method == 'QUERY':
                resource.
        except AttributeError: