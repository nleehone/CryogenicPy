import pika
import time
import json
import threading
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info('Current pika version is {}'.format(pika.__version__))


class RmqComponent(object):
    """Base class for RabbitMQ components.
    Each component runs its own RabbitMQ connection in its own thread (RabbitMQ is NOT thread safe).
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.done = False   # Flag to tell if the thread should be shut down
        thread = threading.Thread(target=self.setup_and_run)
        thread.start()

    def setup_and_run(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        logger.info('Connection opened')
        logger.info('Creating a new channel')
        self.channel = self.connection.channel()

        # Initialise queues here - this is a user-supplied function
        self.init_queues()

        self.run()

    def run(self):
        # Immediately exit if this is the base RMQ class
        self.channel.close()
        logger.info('Channel closed')
        self.connection.close()
        logger.info('Connection closed')

    def close(self):
        # Request that the component close in the next iteration of the run loop
        logger.info('Requesting close')
        self.done = True

    def init_queues(self):
        pass

    def process_message(self, message):
        return message


class RmqResp(RmqComponent):
    """The RmqResp class represents a response server, which sends responses to the client"""
    def __init__(self, queue_name, **kwargs):
        self.response_server_queue = queue_name
        super().__init__(**kwargs)

    def init_queues(self):
        self.channel.queue_declare(queue=self.response_server_queue)
        logger.info('Declared queue: {}'.format(self.response_server_queue))

    def run(self):
        try:
            while not self.done:
                # Wait for next message from client
                message, properties = self.receive_message()
                # Custom user processing code is provided by the 'process_response' method
                response = self.process_message(message)
                self.send_response(response, properties)
        finally:
            self.channel.close()
            logger.info('Channel closed')
            self.connection.close()
            logger.info('Connection closed')

    def receive_message(self):
        """
        Gets a json message. This method can be overridden if a different message type is
        required.
        """
        message = None
        properties = None
        while not self.done:
            # Process message queue events, returning as soon as possible
            self.connection.process_data_events(time_limit=0)

            method, properties, body = self.channel.basic_get(queue=self.response_server_queue,
                                                              no_ack=True)
            # Return as soon as we get a valid message
            if method is not None:
                print(method, properties, body)
                message = json.loads(body.decode('utf-8'))
                logger.info('Received a message: {} | {}'.format(body, properties.reply_to))
                break

        return message, properties

    def send_response(self, response, properties):
        logger.info('Sending response: {}'.format(json.dumps(response)))
        self.channel.basic_publish('', routing_key=properties.reply_to, body=json.dumps(response))


class RmqReq(RmqComponent):
    """The RmqReq class represents a request client, which sends messages to a server
    and waits for a response.

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
