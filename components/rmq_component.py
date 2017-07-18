import pika
import time
import json
import threading
import logging
from queue import Queue, PriorityQueue


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

    def close(self):
        # Request that the component close in the next iteration of the run loop
        logger.info('Requesting server close')
        self.done = True


class RmqResp(RmqComponent):
    """The RmqResp class represents a response server, which sends responses to the client"""
    def __init__(self, server_queue, **kwargs):
        super().__init__(**kwargs)
        self.response_server_queue = server_queue
        self.response_thread_queue = Queue()

    def run_server_thread(self):
        thread = threading.Thread(target=self.setup_and_run_server)
        thread.start()

    def init_server_queues(self):
        self.server_channel.queue_delete(queue=self.response_server_queue)
        self.server_channel.queue_declare(queue=self.response_server_queue)
        logger.info('Declared queue: {}'.format(self.response_server_queue))

    def setup_and_run_server(self):
        self.server_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        logger.info('Server Connection opened')
        logger.info('Creating a new server channel')
        self.server_channel = self.server_connection.channel()

        # Initialise queues here - this is a user-supplied function
        self.init_server_queues()

        self.run_response_server()

    def run_response_server(self):
        try:
            while not self.done:
                # Wait for next message from client
                message, properties = self.receive_message()
                # Custom user processing code is provided by the 'process_response' method
                response = self.process_message(message)
                self.send_response(response, properties)
        finally:
            self.server_channel.close()
            logger.info('Server Channel closed')
            self.server_connection.close()
            logger.info('Server Connection closed')

    def process_message(self, message):
        return None

    def receive_message(self):
        """
        Gets a json message. This method can be overridden if a different message type is
        required.
        """
        message = None
        properties = None
        while not self.done:
            # Process message queue events, returning as soon as possible
            self.server_connection.process_data_events(time_limit=0)

            method, properties, body = self.server_channel.basic_get(queue=self.response_server_queue,
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
        self.server_channel.basic_publish('', routing_key=properties.reply_to, body=json.dumps(response))


class RmqReq(RmqComponent):
    """The RmqReq class represents a request client, which sends messages to a server
    and waits for a response.

    Messages are sent via send_direct_message, and are received via process_direct_reply
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_response = None
        self.request_thread_queue = Queue()

    def run_client_thread(self):
        thread = threading.Thread(target=self.setup_client)
        thread.start()

    def setup_client(self):
        self.client_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        logger.info('Client Connection opened')
        logger.info('Creating a new client channel')
        self.client_channel = self.client_connection.channel()

        # Initialise queues here - this is a user-supplied function
        self.init_client_queues()

        while True:
            queue_name, message = self.request_thread_queue.get()

            """Wrapper for the basic_publish method specifically for sending a direct reply-to message"""
            self.client_channel.basic_publish(exchange='',
                                              routing_key=queue_name,
                                              body=message,
                                              properties=pika.BasicProperties(
                                                  reply_to='amq.rabbitmq.reply-to'
                                              ))

            # Process events until we get a reply back from the server
            self.processed = False
            while not self.processed:
                self.client_connection.process_data_events(time_limit=0)

    def send_direct_message(self, queue_name, message):
        self.request_thread_queue.put((queue_name, message))

    def init_client_queues(self):
        """Create the direct-reply consumer"""
        self.client_channel.basic_consume(self.process_direct_reply, queue='amq.rabbitmq.reply-to', no_ack=True)

    def process_direct_reply(self, channel, method, properties, body):
        """User-supplied function that processes the direct-reply events"""
        self.server_response = body
        self.processed = True

    def get_response(self):
        while self.server_response is None:
            pass
        resp = json.loads(self.server_response.decode('utf-8'))
        self.server_response = None
        return resp
