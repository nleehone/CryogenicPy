from zmq_components import *


class Client(ZMQ_Req):
    def run(self):
        # Do 10 requests, waiting each time for a response
        for request in range(10):
                print("Sending request %s ..." % request)
                client.socket.send_json("Hello")

                # Get the reply
                message = client.socket.recv_json()
                print("Received reply %s [ %s ]" % (request, message))


client = Client('tcp://localhost:5555')
client.run()

