import pika
import time
import threading
import logging


LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class RmqComponent(object):
    def __init__(self):
        self.done = False
        thread = threading.Thread(target=self.run)
        thread.start()

    def run(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        LOGGER.info('Connection opened')
        LOGGER.info('Creating a new channel')
        self.channel = self.connection.channel()

        self.init_queues()

        try:
            while not self.done:
                # Process message queue events, returning as soon as possible.
                # Issues mq_callback() when applicable.
                self.connection.process_data_events(time_limit=0)
                self.process()
        finally:
            self.channel.close()
            LOGGER.info('Channel closed')
            self.connection.close()
            LOGGER.info('Connection closed')

    def close(self):
        LOGGER.info('Requesting close')
        self.done = True

    def init_queues(self):
        pass

    def process(self):
        pass
