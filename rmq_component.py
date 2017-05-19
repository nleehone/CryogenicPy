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


class Producer(RmqComponent):
    def process(self):
        self.channel.basic_publish(exchange='',
                                   routing_key='hello',
                                   body='Hello World!')
        time.sleep(1)

    def init_queues(self):
        self.channel.queue_declare(queue='hello')
        LOGGER.info('Created queue: hello')


class Consumer(RmqComponent):
    def process(self):
        method, properties, body = self.channel.basic_get(queue='hello',
                                   no_ack=True)
        if method is not None:
            print(method, properties, body)

    def init_queues(self):
        self.channel.queue_declare(queue='hello')
        LOGGER.info('Created queue: hello')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    comp1 = Producer()
    comp2 = Consumer()
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        comp1.close()
        comp2.close()
