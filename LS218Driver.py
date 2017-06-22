import components as cmp
from components import QueryCommand, WriteCommand
import logging
import time
import json
import re
import configparser
import sys

LOG_FORMAT = ('%(levelname) -10s %(asctime)s %(name) -30s %(funcName) '
              '-35s %(lineno) -5d: %(message)s')
LOGGER = logging.getLogger(__name__)


class LS218Driver(cmp.IEEE488_2_CommonCommands):
    @staticmethod
    def validate_input_number(input, include_all=False):
        min = 0 if include_all else 1
        try:
            if int(input) not in range(min, 9):
                raise ValueError("Input must be one of {}, instead got {}".format(range(min, 9), input))
        except ValueError as e:
            raise ValueError("Input must be an integer between 0 and 9, instead got {}".format(input))

    @staticmethod
    def validate_digits_number(digits):
        if "." in str(digits):
            digits = str(digits).replace(".", "")

        try:
            if len(str(digits)) > 6:
                raise ValueError("Input must have at most 6 digits {}, instead got {}".format(len(str(digits))))
        except ValueError as e:
            raise ValueError("Input must have at most 6 digits, instead got {}".format(len(str(digits))))

    @staticmethod
    def validate_output_number(output):
        try:
            if int(output) not in [1, 2]:
                raise ValueError("Output must be one of {}, instead got {}".format([1, 2], output))
        except ValueError as e:
            raise ValueError("Output must be 1 or 2, instead got {}".format(output))

    @staticmethod
    def validate_mode(mode):
        try:
            if int(mode) not in [0, 1, 2]:
                raise ValueError("Mode must be one of {}, instead got {}".format([0, 1, 2], mode))
        except ValueError as e:
            raise ValueError("Mode must be 1 or 2, instead got {}".format(mode))

    @staticmethod
    def validate_terminator(mode):
        try:
            if int(mode) not in [0, 1, 2, 3]:
                raise ValueError("Mode must be one of {}, instead got {}".format([0, 1, 2, 3], mode))
        except ValueError as e:
            raise ValueError("Mode must be one of {}, instead got {}".format([0, 1, 2, 3], mode))

    @staticmethod
    def validate_onoff(onoff):
        try:
            if int(onoff) not in [0, 1]:
                raise ValueError("off/on must be one of {}, instead got {}".format([0, 1], onoff))
        except ValueError as e:
            raise ValueError("off/on must be 0 or 1, instead got {}".format(onoff))

    @staticmethod
    def validate_source(source):
        try:
            if int(source) not in [1, 2, 3, 4]:
                raise ValueError("Source must be one of {}, instead got {}".format([1, 2, 3, 4], source))
        except ValueError as e:
            raise ValueError("Source must be {}, instead got {}".format([1, 2, 3, 4], source))

    @staticmethod
    def validate_source6(source):
        try:
            if int(source) not in [1, 2, 3, 4, 5, 6]:
                raise ValueError("Source must be one of {}, instead got {}".format([1, 2, 3, 4, 5, 6], source))
        except ValueError as e:
            raise ValueError("Source must be {}, instead got {}".format([1, 2, 3, 4, 5, 6], source))

    @staticmethod
    def validate_sensor_type(sensor):
        try:
            if int(sensor) not in [1, 2, 3, 4, 5]:
                raise ValueError("Source must be one of {}, instead got {}".format([1, 2, 3, 4, 5], sensor))
        except ValueError as e:
            raise ValueError("Source must be {}, instead got {}".format([1, 2, 3, 4, 5, 6], sensor))

    @staticmethod
    def validate_curve_data(curve, user_curve=False):
            if user_curve:
                try:
                    if int(curve) not in range(21, 29):
                        raise ValueError(
                            "Input must be valid curve"
                            " 21-28: User Curves. Instead got {}".format(curve))
                except ValueError as e:
                    raise ValueError("Input must be valid curve."
                                 "21-28: User Curves. Instead got {}".format(curve))

            else:
                try:
                    if int(curve) not in list(range(0, 10)) + list(range(21, 29)):
                        raise ValueError("Input must be valid curve. 1-5: Standard Diode Curves, 6-9: Standard Platinum"
                                         "Curves, 21-28: User Curves.instead got {}".format(curve))
                except ValueError as e:
                    raise ValueError("Input must be valid curve. 1-5: Standard Diode Curves, 6-9: Standard Platinum"
                                 " Curves, 21-28: User Curves. Instead got {}".format(curve))

    @staticmethod
    def validate_point_index(point):
        try:
            if int(point) not in range(1, 201):
                raise ValueError("Points must be between 1 and 200, instead got {}".format(point))
        except ValueError as e:
            raise ValueError("Points must be between 1 and 200, instead got {}".format(point))

    @staticmethod
    def validate_filter_points(points):
        try:
            if int(points) not in range(2, 65):
                raise ValueError("Points must be between 2 and 65, instead got {}".format(points))
        except ValueError as e:
            raise ValueError("Points must be between 2 and 65, instead got {}".format(points))

    @staticmethod
    def validate_filter_window(window):
        try:
            if int(window) not in range(2, 65):
                raise ValueError("Points must be between 2 and 65, instead got {}".format(window))
        except ValueError as e:
            raise ValueError("Points must be between 2 and 65, instead got {}".format(window))

    @staticmethod
    def validate_month(month):
        try:
            if int(month) not in range(1, 13):
                raise ValueError("Month must be {}, instead got {}".format(range(1, 13), month))
        except ValueError as e:
            raise ValueError("Month must be {}, instead got {}".format(range(1, 13), month))

    @staticmethod
    def validate_day(day):
        try:
            if int(day) not in range(1, 32):
                raise ValueError("Day must be {}, instead got {}".format(range(1, 32), day))
        except ValueError as e:
            raise ValueError("day must be {}, instead got {}".format(range(1, 32), day))

    @staticmethod
    def validate_year(year):
        try:
            if int(year) not in range(0, 100):
                raise ValueError("Year must be {}, instead got {}".format(range(0, 100), year))
        except ValueError as e:
            raise ValueError("Year must be {}, instead got {}".format(range(0, 100), year))

    @staticmethod
    def validate_hour(hour):
        try:
            if int(hour) not in range(0, 24):
                raise ValueError("Hour must be {}, instead got {}".format(range(0, 24), hour))
        except ValueError as e:
            raise ValueError("Hour must be {}, instead got {}".format(range(0, 24), hour))

    @staticmethod
    def validate_minSec(minsec):
        try:
            if int(minsec) not in range(0, 60):
                raise ValueError("Input must be {}, instead got {}".format(range(0, 60), minsec))
        except ValueError as e:
            raise ValueError("Input must be {}, instead got {}".format(range(0, 60), minsec))

    @staticmethod
    def validate_input_group(input):
        try:
            if str(input) not in ['A', 'B']:
                raise ValueError("Input group must be {}, instead got {}".format(['A', 'B'], input))
        except ValueError as e:
            raise ValueError("Input group must be {}, instead got {}".format(['A', 'B'], input))

    class GetSensorReading(QueryCommand):
        cmd = "SRDG?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0], include_all=True)

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            print(result, pars)
            if int(pars[0]) == 0:
                return list(map(lambda x: float(x), result.split(',')))
            else:
                return float(result)

    class GetKelvinReading(GetSensorReading):
        cmd = "KRDG?"

    class GetCelsiusReading(GetSensorReading):
        cmd = "CRDG?"

    class GetAlarmParameters(QueryCommand):
        cmd = "ALARM?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"on/off": int(resp[0]),
                    "source": int(resp[1]),
                    "high": float(resp[2]),
                    "low": float(resp[3]),
                    "deadband": float(resp[4]),
                    "latch": int(resp[5])}

    class GetAlarmStatus(QueryCommand):
        cmd = "ALARMST?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"high": int(resp[0]),
                    "low": int(resp[1])}

    class GetAnalogOutputParameters(QueryCommand):
        cmd = "ANALOG?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_output_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"bipolar": int(resp[0]),
                    "mode": int(resp[1]),
                    "input": int(resp[2]),
                    "source": int(resp[3]),
                    "high": float(resp[4]),
                    "low": float(resp[5]),
                    "manual": float(resp[6])}

    class GetAnalogOutputData(QueryCommand):
        cmd = "AOUT?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_output_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return float(result)

    class GetBaudRate(QueryCommand):
        cmd = "BAUD?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            if int(result) == 0:
                return int(300)
            elif int(result) == 1:
                return int(1200)
            elif int(result) == 2:
                return int(9600)


    class GetCurveDataPoint(QueryCommand):
        cmd = "CRVPT?"
        arguments = "{}, {}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_curve_data(pars[0])
            LS218Driver.validate_point_index(pars[1])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"units": float(resp[0]),
                    "temp": float(resp[1])}

    class GetDateTime(QueryCommand):
        cmd = "DATETIME?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"MM": int(resp[0]),
                    "DD": int(resp[1]),
                    "YY": int(resp[2]),
                    "HH": int(resp[3]),
                    "mm": int(resp[4]),
                    "ss": int(resp[5])
                    }

    class GetDisplayedField(QueryCommand):
        cmd = "DISPFLD?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"input": int(resp[0]),
                    "temp": int(resp[1])
                    }

    class GetFilterParameters(QueryCommand):
        cmd = "FILTER?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"off/on": int(resp[0]),
                    "points": int(resp[1]),
                    "window": int(resp[2])
                    }

    class GetIEEEParameters(QueryCommand):
        cmd = "IEEE?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"term": int(resp[0]),
                    "EOI": int(resp[1]),
                    "address": int(resp[2])
                    }

    class GetCurveNumber(QueryCommand):
        cmd = "INCRV?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetControlParameter(QueryCommand):
        cmd = "INPUT?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetSensorType(QueryCommand):
        cmd = "INTYPE?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_group(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetKeyStatus(QueryCommand):
        cmd = "KEYST?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetLinearEqParameters(QueryCommand):
        cmd = "LINEAR?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"m": float(resp[0]),
                    "source": int(resp[1]),
                    "b": float(resp[2])
                    }

    class GetLogStatus(QueryCommand):
        cmd = "LOG?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetLogNumber(QueryCommand):
        cmd = "LOGNUM?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetLogRecord(QueryCommand):
        cmd = "LOGREAD?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"input": int(resp[0]),
                    "source": int(resp[1])
                    }

    class GetLoggingParameters(QueryCommand):
        cmd = "LOGSET?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"mode": int(resp[0]),
                    "overwrite": int(resp[1]),
                    "start": int(resp[2]),
                    "period": int(resp[3]),
                    "readings": int(resp[4])
                    }

    class GetLoggedData(QueryCommand):
        cmd = "LOGVIEW?"
        arguments = "{}, {}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])
            LS218Driver.validate_input_number(pars[1])



        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"date": str(resp[0]),
                    "time": str(resp[1]),
                    "reading": float(resp[2]),
                    "status": int(resp[3]),
                    "source": int(resp[4])
                    }

    class GetLinearEquationData(QueryCommand):
        cmd = "LRDG?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return(float(result))

    class GetMinMaxInputParameters(QueryCommand):
        cmd = "MNMX?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return(int(result))

    class GetMinMaxData(QueryCommand):
        cmd = "MNMXRDG?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"min": float(resp[0]),
                    "max": float(resp[1])
                    }

    class GetRemoteInterfaceMode(QueryCommand):
        cmd = "MODE?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetInputStatus(QueryCommand):
        cmd = "RDGST?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetRelayControlParameters(QueryCommand):
        cmd = "RELAY?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"mode": int(resp[0]),
                    "input": int(resp[1]),
                    "type": int(resp[2]),
                    }

    class GetRelayStatus(QueryCommand):
        cmd = "RELAYST?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetAudibleAlarm(QueryCommand):
        cmd = "ALMB?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class SetDateTime(WriteCommand):
        cmd = "DATETIME"
        arguments = "{}, {}, {}, {}, {}, {}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_month(pars[0])
            LS218Driver.validate_day(pars[1])
            LS218Driver.validate_year(pars[2])
            LS218Driver.validate_hour(pars[3])
            LS218Driver.validate_minSec(pars[4])
            LS218Driver.validate_minSec(pars[5])

    class SetAlarmParameters(WriteCommand):
        cmd = "ALARM"
        arguments = "{}, {}, {}, {}, {}, {}, {}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])
            LS218Driver.validate_offon_number(pars[1])
            LS218Driver.validate_source(pars[2])
            LS218Driver.validate_onoff(pars[6])

    class SetAudibleAlarm(WriteCommand):
        cmd = "ALMB"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_onoff(pars[0])

    class SetClearAlarmStatus(WriteCommand):
        cmd = "ALMRST"

    class SetConfigureAnalogParameters(WriteCommand):
        cmd = "ANALOG"
        arguments = "{}, {}, {}, {}, {}, {}, {}, {}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_output_number(pars[0])
            LS218Driver.validate_onoff(pars[1])
            LS218Driver.validate_mode_number(pars[2])
            LS218Driver.validate_input_number(pars[3])
            LS218Driver.validate_source(pars[4])

    class SetBaudRate(WriteCommand):
        cmd = "BAUD"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_mode(pars[0])

    class SetDeleteUserCurve(WriteCommand):
        cmd = "CRVDEL"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_curve_data(pars[0], user_curve=True)

    class SetConfigureCurveDataPoint(WriteCommand):
        cmd = "CRVPT"
        arguments = "{}, {}, {}, {}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_curve_data(pars[0], user_curve=True)
            LS218Driver.validate_point_index(pars[1])

    class SetDisplayParameters(WriteCommand):
        cmd = "DSPFLD"
        arguments = "{}, {}, {}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])
            LS218Driver.validate_input_number(pars[1], include_all=True)
            LS218Driver.validate_source6(pars[2])

    class SetFilterParameters(WriteCommand):
        cmd = "FILTER"
        arguments = "{}, {}, {}, {}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])
            LS218Driver.validate_onoff(pars[1])
            LS218Driver.validate_filter_points(pars[2])
            LS218Driver.validate_window(pars[3])

    class SetIEEE488(WriteCommand):
        cmd = "IEEE"
        arguments = "{}, {}, {}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_terminator(pars[0])
            LS218Driver.validate_onoff(pars[1])

    class SetInputControl(WriteCommand):
        cmd = "INPUT"
        arguments = "{}, {}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_terminator(pars[0])
            LS218Driver.validate_onoff(pars[1])

    class SetInputType(WriteCommand):
        cmd = "INTYPE"
        arguments = "{}, {}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_group(pars[0])
            LS218Driver.validate_sensor_type(pars[1])

    class SetInputCurveNumber(WriteCommand):
        cmd = "INCRV"
        arguments = "{}, {}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])
            LS218Driver.validate_curve_data(pars[1])

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read(sys.argv[1])
    LS218_config = config['LS218']

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    driver = LS218Driver(LS218_config['queue_name'], {'library': '',
                                                'address': LS218_config['address'],
                                                'baud_rate': LS218_config.getint('baud_rate'),
                                                'parity': LS218_config['parity'],
                                                'data_bits': LS218_config.getint('data_bits')})

    try:
        time.sleep(1000000)
    except KeyboardInterrupt:
        pass
    finally:
        pass
        driver.close()
