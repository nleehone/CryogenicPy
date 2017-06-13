import os
from . import rmq_component as rmq
import logging


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
