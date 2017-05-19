import rmq_component as rmq
import logging
import time

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class Producer(rmq.RmqComponent):
    def __init__(self):
        super().__init__()
        self.count = 0;

    def process(self):
        self.channel.basic_publish(exchange='',
                                   routing_key='hello',
                                   body='Hello World! ' + str(self.count))
        self.count += 1
        time.sleep(1)

    def init_queues(self):
        self.channel.queue_declare(queue='hello')
        LOGGER.info('Created queue: hello')


class Consumer(rmq.RmqComponent):
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

    # Produce messages and put them in the queue
    comp1 = Producer()
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        comp1.close()

    # Consume the queue
    comp2 = Consumer()
    try:
        time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        comp2.close()
