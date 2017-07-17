from .components import Component
from .rmq_component import RmqReq, RmqResp


class ControllerComponent(RmqReq, RmqResp, Component):
    def __init__(self, controller_queue, **kwargs):
        super().__init__(server_queue=controller_queue, **kwargs)

    def process(self):
        pass