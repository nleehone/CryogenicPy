from zmq_components import *
from zmq_components import QueryCommand, WriteCommand
import logging
import time


LS350_port = 'tcp://*:5580'


class LS350Driver(IEEE488_2_CommonCommands, CommandDriver):
    @staticmethod
    def validate_input_letter(input, include_all=True):
        valid = ["A", "B", "C", "D"]
        if include_all:
            valid.append("0")

        if input not in valid:
            raise ValueError("Input must be one of {}, instead got {}".format(valid, input))

    @staticmethod
    def validate_input_number(input):
        if int(input) not in [1, 2, 3, 4]:
            raise ValueError("Input must be one of [1, 2, 3, 4], instead got {}".format(input))

    @staticmethod
    def validate_heater_output(output):
        if int(output) not in [1, 2]:
            raise ValueError("Heater output must be one of [1, 2], instead got {}".format(output))

    class GetBrightness(QueryCommand):
        cmd = "BRIGT?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class SetBrightness(WriteCommand):
        cmd = "BRIGT"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            if pars[0] < 1 or pars[0] > 32:
                raise ValueError("Brightness must be between 1 and 32, instead got {}".format(pars[0]))

    class GetTemperatureCelsius(QueryCommand):
        cmd = "CRDG?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_letter(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return float(result)

    class GetTemperatureKelvin(QueryCommand):
        cmd = "KRDG?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_letter(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return float(result)

    class GetSensorReading(QueryCommand):
        cmd = "SRDG?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_letter(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return float(result)

    class GetHeaterOutputPercent(QueryCommand):
        cmd = "HTR?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_heater_output(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return float(result)

    class GetRampParameters(QueryCommand):
        cmd = "RAMP?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"On/Off": int(resp[0]),
                    "Rate": float(resp[1])}

    class SetRampParameters(WriteCommand):
        cmd = "RAMP"
        arguments = "{},{},{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])
            LS350Driver.validate_ramp_on_off(pars[1])
            LS350Driver.validate_ramp_rate(pars[2])

    @staticmethod
    def validate_ramp_on_off(on_or_off):
        if int(on_or_off) not in [0, 1]:
            raise ValueError("Ramp mode must be either 0=Off or 1=On, instead got {}".format(on_or_off))

    @staticmethod
    def validate_ramp_rate(rate):
        rate = float(rate)
        if rate < 0 or rate > 100:
            raise ValueError("Ramp rate must be between 0 and 100. 0 means infinite ramp rate.")

    class GetRampStatus(QueryCommand):
        cmd = "RAMPST?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result[0])

    class GetHeaterRange(QueryCommand):
        cmd = "RANGE?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            int(result)

    class SetHeaterRange(WriteCommand):
        cmd = "RANGE"
        arguments = "{},{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])
            LS350Driver.validate_heater_range(pars[0], pars[1])

    @staticmethod
    def validate_heater_range(output, heater_range):
        output = int(output)
        heater_range = int(heater_range)
        if output in [1, 2]:
            if heater_range not in range(0, 6):
                raise ValueError("Heater range must be an integer between 0 and 5 for outputs [1, 2], instead got {}".format(heater_range))
        elif output in [3, 4]:
            if heater_range not in [0, 1]:
                raise ValueError("Heater range must be either 0 or 1 for outputs [3, 4], instead got {}".format(heater_range))

    class GetReadingStatus(QueryCommand):
        cmd = "RDGST?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_letter(pars[0], include_all=False)

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetSetpoint(QueryCommand):
        cmd = "SETP?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return float(result)

    class SetSetpoint(WriteCommand):
        cmd = "SETP"
        arguments = "{},{}"

        @classmethod
        def _validate(cls, pars):
            LS350Driver.validate_input_number(pars[0])


if __name__ == '__main__':
    driver = LS350Driver(LS350_port, {'library': '',
                                      'address': 'ASRL6::INSTR',
                                      'baud_rate': 56000,
                                      'parity': 'odd',
                                      'data_bits': 7})

    driver.run()