import pika
import time
import threading


class RmqComponent(object):
    def __init__(self):
        self.done = False
        thread = threading.Thread(target=self.run)
        thread.start()

    def run(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        self.init_queues()

        try:
            while not self.done:
                # Process message queue events, returning as soon as possible.
                # Issues mq_callback() when applicable.
                self.connection.process_data_events(time_limit=0)
                self.process()
        finally:
            self.channel.stop_consuming()
            self.connection.close()
            print("Closed")

    def close(self):
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


class Consumer(RmqComponent):
    def process(self):
        method, properties, body = self.channel.basic_get(queue='hello',
                                   no_ack=True)
        if method is not None:
            print(method, properties, body)

    def callback(self, channel, method, properties, body):
        print(" [*] Received %r" % body)

    def init_queues(self):
        self.channel.queue_declare(queue='hello')


if __name__ == '__main__':
    comp1 = Producer()
    comp2 = Consumer()
    time.sleep(10)
    comp1.close()
    comp2.close()
