from components import Component
from .rmq_component import RmqReq, RmqResp


class ControllerComponent(RmqReq, RmqResp, Component):
    def __init__(self, controller_queue, **kwargs):
        super(RmqReq, self).__init__(controller_queue, **kwargs)
        super(RmqResp, self).__init__(controller_queue, **kwargs)
        super(Component, self).__init__(**kwargs)

    def process(self):
        pass