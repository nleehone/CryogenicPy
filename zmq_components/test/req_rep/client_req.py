import zmq
from zmq_components import *


client = ZMQ_Req('tcp://localhost:5555')

# Do 10 requests, waiting each time for a response
for request in range(10):
    print("Sending request %s ..." % request)
    client.socket.send(b"Hello")

    # Get the reply
    message = client.socket.recv()
    print("Received reply %s [ %s ]" % (request, message))