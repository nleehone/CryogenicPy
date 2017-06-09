import visa


def validate_num_params(pars, num):
    if len(pars) != num:
        raise ValueError("Number of parameters ({}) does not match expectation ({})".format(len(pars), num))


def validate_range(par, low, high):
    if par < low or par > high:
        raise ValueError("Parameter must be in the range [{}:{}], but got {}".format(low, high, par))


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


class IEEE488_2_CommonCommands(Driver):
    def split_cmd(self, cmd):
        # Split the message into a command and a set of parameters
        command, *pars = list(filter(None, map(lambda x: x.strip(), re.split(',| |\?', cmd))))
        # Put the question mark back in since it was removed in the split process
        if "?" in cmd:
            command += "?"
        return command, pars

    def check_command(self, cmd):
        cmd, pars = self.split_cmd(cmd)
        try:
            {
                "*CLS": IEEE488_2_CommonCommands.clear_status_validate,
                "*ESE": IEEE488_2_CommonCommands.set_event_status_enable_validate,
                "*ESE?": IEEE488_2_CommonCommands.get_event_status_enable_validate,
                "*ESR?": IEEE488_2_CommonCommands.get_event_status_register_validate,
                "*IDN?": IEEE488_2_CommonCommands.get_identification_validate,
                "*OPC": IEEE488_2_CommonCommands.set_operation_complete_validate,
                "*OPC?": IEEE488_2_CommonCommands.get_operation_complete_validate,
                "*RST": IEEE488_2_CommonCommands.reset_instrument_validate,
                "*SRE": IEEE488_2_CommonCommands.set_service_request_enable_validate,
                "*SRE?": IEEE488_2_CommonCommands.get_service_request_enable_validate,
                "*STB?": IEEE488_2_CommonCommands.get_status_byte_validate,
                "*TST?": IEEE488_2_CommonCommands.self_test_validate,
                "*WAI": IEEE488_2_CommonCommands.wait_validate,
            }[cmd](pars)
        except Exception as e:
            return e

    def process_response(self, response, cmd):
        cmd, pars = self.split_cmd(cmd)
        try:
            processed = {
                "*ESE?": IEEE488_2_CommonCommands.get_event_status_enable_response,
                "*ESR?": IEEE488_2_CommonCommands.get_event_status_register_response,
                "*IDN?": IEEE488_2_CommonCommands.get_identification_response,
                "*OPC?": IEEE488_2_CommonCommands.get_operation_complete_response,
                "*SRE?": IEEE488_2_CommonCommands.get_service_request_enable_response,
                "*STB?": IEEE488_2_CommonCommands.get_status_byte_response,
            }[cmd](pars, response)
        except Exception as e:
            return None, e
        return processed, None

    @staticmethod
    def clear_status(pars):
        """Clears event registers and clears the error queue"""
        IEEE488_2_CommonCommands.clear_status_validate(pars)
        return "*CLS"

    @staticmethod
    def clear_status_validate(pars):
        validate_num_params(pars, 0)

    @staticmethod
    def set_event_status_enable(pars):
        IEEE488_2_CommonCommands.set_event_status_enable_validate(pars)
        return "*ESE {}".format(*pars)

    @staticmethod
    def set_event_status_enable_validate(pars):
        validate_num_params(pars, 1)
        validate_range(pars[0], 0, 255)

    @staticmethod
    def get_event_status_enable(pars):
        IEEE488_2_CommonCommands.get_event_status_enable_validate(pars)
        return "*ESE?"

    @staticmethod
    def get_event_status_enable_validate(pars):
        validate_num_params(pars, 0)

    @staticmethod
    def get_event_status_enable_response(pars, resp):
        return int(resp)

    @staticmethod
    def get_event_status_register(pars):
        IEEE488_2_CommonCommands.get_event_status_register_validate(pars)
        return "*ESR?"

    @staticmethod
    def get_event_status_register_validate(pars):
        validate_num_params(pars, 0)

    @staticmethod
    def get_event_status_register_response(pars, resp):
        return int(resp)

    @staticmethod
    def get_identification(pars):
        IEEE488_2_CommonCommands.get_identification_validate(pars)
        return "*IDN?"

    @staticmethod
    def get_identification_validate(pars):
        validate_num_params(pars, 0)

    @staticmethod
    def get_identification_response(pars, resp):
        return resp

    @staticmethod
    def set_operation_complete(pars):
        IEEE488_2_CommonCommands.set_operation_complete_validate(pars)
        return "*OPC"

    @staticmethod
    def set_operation_complete_validate(pars):
        validate_num_params(pars, 0)

    @staticmethod
    def get_operation_complete(pars):
        IEEE488_2_CommonCommands.get_operation_complete_validate(pars)
        return "*OPC?"

    @staticmethod
    def get_operation_complete_validate(pars):
        validate_num_params(pars, 0)

    @staticmethod
    def get_operation_complete_response(pars, resp):
        return int(resp)

    @staticmethod
    def reset_instrument(pars):
        """Reset the instrument to the factory default state"""
        IEEE488_2_CommonCommands.reset_instrument_validate(pars)
        return "*RST"

    @staticmethod
    def reset_instrument_validate(pars):
        validate_num_params(pars, 0)

    @staticmethod
    def set_service_request_enable(pars):
        IEEE488_2_CommonCommands.set_service_request_enable_validate(pars)
        return "*SRE {}".format(pars)

    @staticmethod
    def set_service_request_enable_validate(pars):
        validate_num_params(pars, 1)

    @staticmethod
    def get_service_request_enable(pars):
        IEEE488_2_CommonCommands.get_service_request_enable_validate(pars)
        return "*SRE?"

    @staticmethod
    def get_service_request_enable_validate(pars):
        validate_num_params(pars, 0)

    @staticmethod
    def get_service_request_enable_response(pars, resp):
        return int(resp)

    @staticmethod
    def get_status_byte(pars):
        IEEE488_2_CommonCommands.get_status_byte_validate(pars)
        return "*STB?"

    @staticmethod
    def get_status_byte_validate(pars):
        validate_num_params(pars, 0)

    @staticmethod
    def get_status_byte_response(pars, resp):
        return int(resp)

    @staticmethod
    def self_test(pars):
        IEEE488_2_CommonCommands.self_test_validate(pars)
        return "*TST?"

    @staticmethod
    def self_test_validate(pars):
        validate_num_params(pars, 0)

    @staticmethod
    def wait(pars):
        IEEE488_2_CommonCommands.wait_validate(pars)
        return "*WAI"

    @staticmethod
    def wait_validate(pars):
        validate_num_params(pars, 0)




