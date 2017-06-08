import components as cmp
import time
import json
import logging


params = {
    'driver_queue': 'LS350.driver',
    'controller_queue': 'Temperature.controller',
}

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class TemperatureController(cmp.ControllerComponent):
    def __init__(self, params):
        super().__init__(params['driver_queue'], params['controller_queue'])

    def process(self):
        method, properties, body = self.channel.basic_get(queue=self.controller_queue,
                                                          no_ack=True)
        if method is not None:
            t0 = time.time()
            result, error = self.process_command(body)
            t1 = time.time()
            reply = {"t0": t0,
                     "t1": t1,
                     "result": result,
                     "error": error}
            if reply is not None:
                self.channel.basic_publish('', routing_key=properties.reply_to, body=json.dumps(reply))

    def process_command(self, body):
        # METHOD: {READ, WRITE, QUERY}
        body = json.loads(body.decode('utf-8'))
        try:
            method = body['METHOD']
            cmd = body['CMD']
            if method == 'WRITE':
                return "WRITE", None
            elif method == 'QUERY':
                return "QUERY", None
            elif method == 'READ':
                return "READ", None
            else:
                error = "Unrecognized METHOD: {}".format(method)
                self.logger.warning(error)
                return None, error
        except AttributeError:
            self.logger.warning("Invalid command: {}".format(body))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    controller = TemperatureController(params)
    try:
        time.sleep(10000)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        controller.close()
