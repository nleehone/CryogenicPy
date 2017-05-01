import visa
import sys
import json
from driver import Driver


class SR830Driver(Driver):
    def __init__(self, params):
        super().__init__(params)


if __name__ == '__main__':
    driver = SR830Driver(json.loads(sys.argv[1]))
    while True:
        pass