import time
from zmq_components import *


class Server(ZMQ_Resp):
    def process_message(self, message):
        print("Received request: %s" % message)
        time.sleep(1)
        return "World"


server = Server('tcp://*:5555')
server.run()

