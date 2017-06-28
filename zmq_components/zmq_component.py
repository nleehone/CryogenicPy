import zmq
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Current libzmq version is {}".format(zmq.zmq_version()))
logger.info("Current pyzmq version is {}".format(zmq.__version__))


class ZMQ_Component(object):
    def __init__(self):
        self.context = zmq.Context()


class ZMQ_Req(ZMQ_Component):
    """The ZMQ_Req class represents a request client, which sends messages to the server"""
    def __init__(self, port):
        super().__init__()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(port)

    def run(self):
        pass


class ZMQ_Resp(ZMQ_Component):
    """The ZMQ_Resp class represents a response server, which sends responses to the client"""
    def __init__(self, port):
        super().__init__()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(port)

    def run(self):
        while True:
            # Wait for next request from client (REQ)
            message = self.receive_message()

            response = self.process_message(message)

            self.send_response(response)

    def receive_message(self):
        """
        Gets a json message from the socket. This method can be overridden if a different
        message type is required.
        """
        try:
            return self.socket.recv_json()
        except Exception:
            logger.exception("receive_message failed to get a message")

    def process_message(self, message):
        """Default message processing: Returns the original message (echo server)"""
        return message

    def send_response(self, response):
        """
        Sends a json message back to the client. This method can be overridden if a different
        message type is required.
        """
        self.socket.send_json(response)

