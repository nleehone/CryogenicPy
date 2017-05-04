import pika
import visa
import json
import logging
from threading import Thread
import os
import tkinter as tk


# Get the directory's full path
dir_path = os.path.dirname(os.path.realpath(__file__))


class PikaComponent(object):
    """Base class for components that talk to each other

    A component has a command socket (REP=response) that allows other parts of the system to communicate with them
    """
    def __init__(self, command_queue_name):
        self.setup_logger()
        self.command_queue_name = command_queue_name

    def setup_logger(self):
        self.logger = logging.getLogger(type(self).__name__)
        self.logger.setLevel(logging.INFO)

        # Create a file handler
        handler = logging.FileHandler("{}/{}.log".format(dir_path, __name__))
        handler.setLevel(logging.INFO)

        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

    def start(self):
        self.logger.info("Started component")

        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.command_channel = self.connection.channel()
        self.command_channel.queue_declare(queue=self.command_queue_name, exclusive=True, auto_delete=True)
        self.command_channel.basic_consume(self.on_command, queue=self.command_queue_name)

        # Consume messages in a separate thread so we can do operations on the main thread
        self.logger.info("Starting command thread")
        self.command_thread = Thread(target=self.run_command_channel)
        self.command_thread.daemon = True
        self.command_thread.start()

    def shutdown(self):
        self.logger.info("Shutting down the connection")
        self.connection.close()

    def run_command_channel(self):
        try:
            self.logger.info("Start consuming on command channel")
            self.command_channel.start_consuming()
        except KeyboardInterrupt:
            self.logger.info("Stop consuming on command channel")
            self.command_channel.stop_consuming()

    def on_command(self, channel, method_frame, properties, body):
        self.logger.info("Received command: {}".format(body))
        reply = self.process_command(body)
        if reply:
            self.logger.info("Sending reply: {}".format(reply))
            self.command_channel.basic_publish('', routing_key=properties.reply_to, body=reply)

    def process_command(self, body):
        return json.dumps("Not implemented")


class Driver(object):
    """Base class for all instrument drivers"""
    def __init__(self, params):
        rm = visa.ResourceManager()
        self.resource = rm.open_resource(params['address'])
        if 'baud_rate' in params:
            self.resource.baud_rate = params['baud_rate']
        if 'data_bits' in params:
            self.resource.data_bits = params['data_bits']
        if 'parity' in params:
            self.resource.parity = {
                'odd': visa.constants.Parity.odd,
                'even': visa.constants.Parity.even,
                'none': visa.constants.Parity.none
            }[params['parity']]
        if 'stop_bits' in params:
            self.resource.stop_bits = {
                'one': visa.constants.StopBits.one
            }[params['stop_bits']]
        if 'termination' in params:
            self.resource.termination = {
                'CR': self.resource.CR,
                'LF': self.resource.LF
            }[params['termination']]

    def write(self, msg):
        """
        :param msg (str): Message to be sent
        :return (int): Number of bytes written
        """
        return self.resource.write(msg)

    def read(self):
        """
        Read a string from the device.

        Reads until the termination character is found
        :return (str): The string with termination character stripped
        """
        return self.resource.read()

    def query(self, msg):
        """
        Sequential write and read
        :param msg (str): Message to be sent
        :return (str): The string with termination character stripped
        """
        return self.resource.query(msg)


class ControllerComponent(PikaComponent):
    def __init__(self, params):
        super().__init__("{}.{}".format(params['name'], 'controller'))
        self.driver_queue_name = "{}.{}".format(params['name'], 'driver')

    def start(self):
        super().start()
        self.driver_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.driver_channel = self.driver_connection.channel()
        self.driver_channel.basic_consume(self.driver_reply, queue='amq.rabbitmq.reply-to', no_ack=True)

        #self.driver_channel.basic_publish(exchange='',
        #                                  routing_key=self.driver_queue_name,
        #                                  body=json.dumps({'METHOD': 'QUERY', 'CMD': 'SRDG?A'}),
        #                                  properties=pika.BasicProperties(reply_to='amq.rabbitmq.reply-to'))
        # Consume messages in a separate thread so we can do operations on the main thread
        self.logger.info("A Starting command thread")
        self.driver_thread = Thread(target=self.run_driver_channel)
        self.driver_thread.daemon = True
        self.driver_thread.start()

    def run_driver_channel(self):
        try:
            self.logger.info("Start consuming on driver channel")
            self.driver_channel.start_consuming()
        except KeyboardInterrupt:
            self.logger.info("Stop consuming on driver channel")
            self.driver_channel.stop_consuming()

    def send_message(self):
        self.driver_channel.basic_publish(exchange='',
                                          routing_key=self.driver_queue_name,
                                          body=json.dumps('Test message'),
                                          properties=pika.BasicProperties(reply_to='amq.rabbitmq.reply-to'))

    def driver_reply(self, channel, method_frame, properties, body):
        print("Reply is:", body)

    def process_command(self, body):
        print(body)
        return "Some value"
        #self.command_channel.basic_publish('', routing_key=properties.reply_to, body=reply)


class DriverComponent(PikaComponent):
    """Single point of communication with the instrument

    Having a common point of communication prevents multiple parts of the system from trying to access the hardware
    at the same time.

    It is up to the user to make sure that only one instance of the Driver is ever running.
    """
    def __init__(self, params):
        super().__init__("{}.{}".format(params['name'], "driver"))
        self.driver = Driver(params)

    def process_command(self, body):
        print(body)
        # METHOD: {READ, WRITE, QUERY}
        body = json.loads(body.decode('utf-8'))
        try:
            method = body['METHOD']
            cmd = body['CMD']
            if method == 'WRITE':
                self.driver.write(cmd)
            elif method == 'QUERY':
                return json.dumps(self.driver.query(cmd))
            elif method == 'READ':
                return json.dumps(self.driver.read())
            else:
                self.logger.warning("Unrecognized METHOD: {}".format(method))
        except AttributeError:
            self.logger.warning("Invalid command: {}".format(body))


if __name__ == '__main__':
    # Test the component interacting with a client

    command_queue = 'cmd_queue'
    params = {
        'name': 'LS350',
        'baud_rate': 57600,
        'data_bits': 7,
        'parity': 'odd',
        'driver': 'LS350Driver.py',
        'address': 'ASRL9::INSTR',
    }

    component = ControllerComponent(params)#command_queue)
    component.start()

    def reply(channel, method_frame, properties, body):
        print("Reply is:", body)

    c = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    ch = c.channel()
    ch.basic_consume(reply, queue='amq.rabbitmq.reply-to', no_ack=True)
    print("Sending Test command")
    ch.basic_publish(exchange='',
                     routing_key='LS350.controller',#command_queue,
                     body=json.dumps('Test message'),
                     properties=pika.BasicProperties(reply_to='amq.rabbitmq.reply-to'))

    try:
        ch.start_consuming()
    except KeyboardInterrupt:
        ch.stop_consuming()

    c.close()

    component.shutdown()
