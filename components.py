import os
import time
import visa
import json
import rmq_component as rmq
import logging


# Get the directory's full path
dir_path = os.path.dirname(os.path.realpath(__file__))


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
        return self.resource.query(msg), None


class Component(object):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setup_logger()

    def setup_logger(self):
        self.logger = logging.getLogger(type(self).__name__)
        self.logger.setLevel(logging.INFO)

        # Create a file handler
        handler = logging.FileHandler("{}/{}.log".format(dir_path, __name__))
        handler.setLevel(logging.INFO)

        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)


class DriverComponent(rmq.RmqComponent, Component):
    """Single point of communication with the instrument

    Having a common point of communication prevents multiple parts of the system from
    trying to access the hardware at the same time.

    It is up to the user to make sure that only one instance of the Driver is ever running.
    """
    def __init__(self, driver_queue, driver_params, **kwargs):
        self.driver = Driver(driver_params)
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
            t1 = time.time()
            reply = {"t0": t0,
                     "t1": t1,
                     "result": result,
                     "error": error}
            if reply is not None:
                self.channel.basic_publish('', routing_key=properties.reply_to, body=json.dumps(reply))

    def process_command(self, body):
        # METHOD: {READ, WRITE, QUERY}
        body = json.loads(body.decode('utf-8'))
        try:
            method = body['METHOD']
            cmd = body['CMD']
            if method == 'WRITE':
                return self.driver.write(cmd)
            elif method == 'QUERY':
                return self.driver.query(cmd)
            elif method == 'READ':
                return self.driver.read()
            else:
                error = "Unrecognized METHOD: {}".format(method)
                self.logger.warning(error)
                return None, error
        except AttributeError:
            self.logger.warning("Invalid command: {}".format(body))


class ControllerComponent(rmq.RmqComponentRPC, Component):
    def __init__(self, driver_queue, controller_queue, **kwargs):
        super().__init__(**kwargs)
        self.driver_queue = driver_queue
        self.controller_queue = controller_queue

    def init_queues(self):
        super().init_queues()
        self.channel.queue_declare(queue=self.controller_queue)

    def process(self):
        pass
