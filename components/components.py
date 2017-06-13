import os
import time
import json
from . import rmq_component as rmq
import logging
import traceback


# Get the directory's full path
dir_path = os.path.dirname(os.path.realpath(__file__))


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
        except AttributeError as e:
            print(e)
            self.logger.warning("Invalid command format: {}".format(body))


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
