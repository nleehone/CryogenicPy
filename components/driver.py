import visa


class Driver(object):
    """Base class for all instrument drivers"""
    def __init__(self, params):
        rm = visa.ResourceManager(params.get('library', ''))
        self.resource = rm.open_resource(params['address'])
        if 'baud_rate' in params:
            self.resource.baud_rate = params['baud_rate']
        if 'data_bits' in params:
            self.resource.data_bits = params['data_bits']
        if 'parity' in params:
            self.resource.parity = {
                'odd': visa.constants.Parity.odd,
                'even': visa.constants.Parity.even,
                'none': visa.constants.Parity.none
            }[params['parity']]
        if 'stop_bits' in params:
            self.resource.stop_bits = {
                'one': visa.constants.StopBits.one
            }[params['stop_bits']]
        if 'termination' in params:
            self.resource.termination = {
                'CR': self.resource.CR,
                'LF': self.resource.LF
            }[params['termination']]

    def write(self, msg):
        """
        :param msg (str): Message to be sent
        :return (int): Number of bytes written
        """
        error = self.check_command(msg)
        if error:
            return None, error
        return self.resource.write(msg), None

    def read(self):
        """
        Read a string from the device.

        Reads until the termination character is found
        :return (str): The string with termination character stripped
        """
        return self.resource.read(), None

    def query(self, msg):
        """
        Sequential write and read
        :param msg (str): Message to be sent
        :return (str): The string with termination character stripped
        """
        error = self.check_command(msg)
        if error:
            return None, error
        return self.process_response(self.resource.query(msg), msg)

    def check_command(self, msg):
        # Don't check the command on the base Driver
        return None

    def process_response(self, resp, msg):
        # Pass the raw response back for the base Driver
        return resp, None
