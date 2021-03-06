from .rmq_component import RmqResp, logger
import visa


class Driver(object):
    """Single point of communication with the instrument

    Having a common point of communication prevents multiple parts of the system from
    trying to access the hardware at the same time.

    It is up to the user to make sure that only one instance of the Driver is ever running.
    """
    def __init__(self, driver_params, **kwargs):
        self.create_resource(driver_params)
        super().__init__(**kwargs)

    def create_resource(self, driver_params):
        rm = visa.ResourceManager(driver_params.get('library', ''))
        self.resource = rm.open_resource(driver_params['address'])

        if 'baud_rate' in driver_params:
            self.resource.baud_rate = driver_params['baud_rate']
        if 'data_bits' in driver_params:
            self.resource.data_bits = driver_params['data_bits']
        if 'parity' in driver_params:
            self.resource.parity = {
                'odd': visa.constants.Parity.odd,
                'even': visa.constants.Parity.even,
                'none': visa.constants.Parity.none
            }[driver_params['parity']]
        if 'stop_bits' in driver_params:
            self.resource.stop_bits = {
                'one': visa.constants.StopBits.one
            }[driver_params['stop_bits']]
        if 'termination' in driver_params:
            self.resource.termination = {
                'CR': self.resource.CR,
                'LF': self.resource.LF,
            }.get(driver_params['termination'], driver_params['termination'])
