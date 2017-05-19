import rmq_component as rmq
import logging
import time
import pika

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class Producer(rmq.RmqComponent):
    def __init__(self):
        super().__init__()
        self.count = 0

    def process(self):
        message = 'Some work to be done: ' + str(self.count)

        LOGGER.info('Sent message: ' + message)
        self.channel.basic_publish(exchange='',
                                   routing_key='test_queue',
                                   body=message,
                                   properties=pika.BasicProperties(
                                       reply_to='amq.rabbitmq.reply-to'
                                   ))
        self.count += 1
        time.sleep(1)

    def init_queues(self):
        self.channel.basic_consume(self.reply, queue='amq.rabbitmq.reply-to', no_ack=True)

    def reply(self, channel, method, properties, body):
        LOGGER.info("Producer got back: " + str(body))


class Consumer(rmq.RmqComponent):
    def process(self):
        pass
        method, properties, body = self.channel.basic_get(queue='test_queue',
                                                          no_ack=True)
        if method is not None:
            LOGGER.info("Consumer received: " + str((method, str(properties), body)))
            reply = 'Replying to: ' + str((method, str(properties), body))
            LOGGER.info("Consumer sending reply: " + reply)
            self.channel.basic_publish('', routing_key=properties.reply_to, body=reply)

    def init_queues(self):
        self.channel.queue_declare(queue="test_queue")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    # Produce messages and put them in the queue
    comp1 = Producer()
    comp2 = Consumer()
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        comp1.close()
        comp2.close()
