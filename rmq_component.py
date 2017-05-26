import pika
import time
import threading
import logging


LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class RmqComponent(object):
    """Base class for RabbitMQ components.
    Each component runs its own RabbitMQ connection in its own thread (RabbitMQ is NOT thread safe).
    """
    def __init__(self):
        self.done = False   # Flag to tell if the thread should be shut down
        thread = threading.Thread(target=self.run)
        thread.start()

    def run(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        LOGGER.info('Connection opened')
        LOGGER.info('Creating a new channel')
        self.channel = self.connection.channel()

        # Initialise queues here - this is a user-supplied function
        self.init_queues()

        try:
            while not self.done:
                # Process message queue events, returning as soon as possible.
                self.connection.process_data_events(time_limit=0)
                # Custom user processing code is provided by the 'process' method
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


class RmqComponentRPC(RmqComponent):
    """The RmqComponentRPC class is used to send RPC messages to other RmqComponents and
    process the returned messages.

    Messages are sent via send_direct_message, and are received via process_direct_reply
    """
    def send_direct_message(self, queue_name, message):
        """Wrapper for the basic_publish method specifically for sending a direct reply-to message"""
        self.channel.basic_publish(exchange='',
                                   routing_key=queue_name,
                                   body=message,
                                   properties=pika.BasicProperties(
                                       reply_to='amq.rabbitmq.reply-to'
                                   ))

    def init_queues(self):
        """Create the direct-reply consumer"""
        self.channel.basic_consume(self.process_direct_reply, queue='amq.rabbitmq.reply-to', no_ack=True)

    def process_direct_reply(self, channel, method, properties, body):
        """User-supplied function that processes the direct-reply events"""
        pass
