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


class ZMQ_Resp(ZMQ_Component):
    """The ZMQ_Resp class represents a response server, which sends responses to the client"""
    def __init__(self, port):
        super().__init__()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(port)
