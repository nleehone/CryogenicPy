import LS350Driver
from driver import ControllerComponent

params = {
    'name': 'LS350',
    'baud_rate': 57600,
    'data_bits': 7,
    'parity': 'odd',
    'driver': 'LS350Driver.py',
    'address': 'ASRL9::INSTR',
}


class LS350Controller(ControllerComponent):
    def __init__(self, params):
        super().__init__(params)


if __name__ == '__main__':
    controller = LS350Controller(params)
    controller.start()
    while True:
        pass