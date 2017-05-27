import rmq_component as rmq
import components as cmp
import logging
import time
import json


driver_queue = 'LS350.driver'
controller_queue = 'LS350.controller'

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class LS350Controller(cmp.ControllerComponent):
    def process(self):
        #message = {'METHOD': 'QUERY', 'CMD': 'CRVHDR?8'}
        #self.send_direct_message(self.driver_queue, json.dumps(message))
        #time.sleep(1)
        message = {'METHOD': 'WRITE', 'CMD': 'SETP1,200'}
        self.send_direct_message(self.driver_queue, json.dumps(message))
        message = {'METHOD': 'QUERY', 'CMD': 'SETP?1'}
        self.send_direct_message(self.driver_queue, json.dumps(message))
        time.sleep(1)

    def process_direct_reply(self, channel, method, properties, body):
        LOGGER.info("Producer got back: " + str(body))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    driver = cmp.DriverComponent(driver_queue, {'library': 'test/instruments.yaml@sim',
                                                'address': 'ASRL1::INSTR'})
    controller = LS350Controller(driver_queue, controller_queue)
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        driver.close()
        controller.close()
