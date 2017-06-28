import time
import zmq
from zmq_components import *

server = ZMQ_Resp('tcp://*:5555')

while True:
    # Wait for next request from client (REQ)
    message = server.socket.recv()
    print("Received request: %s" % message)

    # Do some work
    time.sleep(1)

    # Send reply back to client
    server.socket.send(b"World")
