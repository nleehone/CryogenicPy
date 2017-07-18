from .command_runner import CommandRunner
from .components import Component
from .rmq_component import RmqReq, RmqResp


class ControllerComponent(CommandRunner, Component):
    def __init__(self, controller_queue, **kwargs):
        super().__init__(command_queue=controller_queue, **kwargs)

    def process(self):
        pass