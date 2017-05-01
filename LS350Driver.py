import visa
import sys
import json
from driver import DriverComponent


class LS350Driver(DriverComponent):
    def __init__(self, params):
        super().__init__(params)

    @classmethod
    def validate_channel(cls, channel):
        if channel not in ['A', 'B', 'C', 'D']:
            raise ValueError("Channel must be one of {'A', 'B', 'C', 'D'}")

    @classmethod
    def validate_unit(cls, unit):
        if unit not in ['K', 'C', 'S']:
            raise ValueError("Units must be one of {'K', 'C', 'S'}.")

    @classmethod
    def set_temperature(cls, channel, temperature, unit='K'):
        """"""
        LS350Driver.validate_channel(channel)
        LS350Driver.validate_unit(unit)
        return 'SETP{}'.format(temperature)

    @classmethod
    def get_temperature_setpoint(cls, channel, unit='K'):
        LS350Driver.validate_channel(channel)
        LS350Driver.validate_unit(unit)
        return 'SETP?{}'.format(channel)

    @classmethod
    def get_temperature(cls, channel, unit='K'):
        """"""
        LS350Driver.validate_channel(channel)
        LS350Driver.validate_unit(unit)
        return '{}RDG?{}'.format(unit, channel)

    @classmethod
    def get_sensor(cls, channel):
        """"""
        LS350Driver.validate_channel(channel)
        return 'SRDG?{}'.format(channel)

    @classmethod
    def set_P(cls, channel, P):
        """"""
        LS350Driver.validate_channel(channel)
        return ""

    @classmethod
    def get_P(cls, channel):
        """"""
        LS350Driver.validate_channel(channel)

    @classmethod
    def set_I(cls, channel, I):
        """
        """
        LS350Driver.validate_channel(channel)

    @classmethod
    def get_I(cls, channel):
        """"""
        LS350Driver.validate_channel(channel)

    @classmethod
    def set_D(cls, channel, D):
        """"""
        LS350Driver.validate_channel(channel)

    @classmethod
    def get_D(cls, channel):
        """"""
        LS350Driver.validate_channel(channel)

    @classmethod
    def set_PID(cls, channel, P, I=0, D=0):
        """"""
        LS350Driver.validate_channel(channel)

    @classmethod
    def get_PID(cls, channel):
        """"""
        LS350Driver.validate_channel(channel)

    @classmethod
    def set_heater_range(cls, channel, range):
        """"""
        LS350Driver.validate_channel(channel)

    @classmethod
    def get_heater_range(cls, channel):
        """"""
        LS350Driver.validate_channel(channel)

    @classmethod
    def set_heater_power(cls, channel, power):
        """"""
        LS350Driver.validate_channel(channel)

    @classmethod
    def get_heater_power(cls, channel):
        """"""
        LS350Driver.validate_channel(channel)

    @classmethod
    def set_calibration_curve(cls, channel, curve):
        """"""
        LS350Driver.validate_channel(channel)

    @classmethod
    def get_calibration_curve(cls, channel):
        """"""
        LS350Driver.validate_channel(channel)


if __name__ == '__main__':
    driver = LS350Driver(json.loads(sys.argv[1]))
    driver.start()
    while True:
        pass
    driver.shutdown()
