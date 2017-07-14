import components.rmq_component as rmq
import logging
import time
import pika

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class Producer(rmq.RmqReq):
    def __init__(self):
        super().__init__()
        self.count = 0

    def run(self):
        message = 'Some work to be done: ' + str(self.count)

        LOGGER.info('Sent message: ' + message)
        self.send_direct_message('test_queue',
                             message)

        self.count += 1
        time.sleep(1)

    def process_direct_reply(self, channel, method, properties, body):
        LOGGER.info("Producer got back: " + str(body))


class Consumer(rmq.RmqResp):
    def process(self):
        pass
        method, properties, body = self.server_channel.basic_get(queue='test_queue',
                                                          no_ack=True)
        if method is not None:
            LOGGER.info("Consumer received: " + str((method, str(properties), body)))
            reply = 'Replying to: ' + str((method, str(properties), body))
            LOGGER.info("Consumer sending reply: " + reply)
            self.server_channel.basic_publish('', routing_key=properties.reply_to, body=reply)

    def init_queues(self):
        self.server_channel.queue_declare(queue="test_queue")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    # Produce messages and put them in the queue
    comp1 = Producer()
    comp2 = Consumer('test_queue')
    try:
        comp1.run()
        time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        comp1.close()
        comp2.close()
