import components as cmp
from components import QueryCommand, WriteCommand, IEEE488_CommonCommands, CommandRunner, DriverCommandRunner, \
    DriverQueryCommand, DriverWriteCommand
import logging
import time
import configparser
import sys


class LS218Driver(IEEE488_CommonCommands, DriverCommandRunner):
    @staticmethod
    def validate_input_number(input, include_all=False):
        min = 0 if include_all else 1
        try:
            if int(input) not in range(min, 9):
                raise ValueError("Input must be one of {}, instead got {}".format(range(min, 9), input))
        except ValueError as e:
            raise ValueError("Input must be an integer between 0 and 9, instead got {}".format(input))

    @staticmethod
    def validate_output_number(input):
        try:
            if int(input) not in [1, 2]:
                raise ValueError("Input must be one of {}, instead got {}".format([1, 2], input))
        except ValueError as e:
            raise ValueError("Input must be 1 or 2, instead got {}".format(input))

    @staticmethod
    def validate_curve_data(input):
        try:
            if int(input) not in list(range(1, 10)) + list(range(21, 29)):
                raise ValueError("Input must be valid curve. 1-5: Standard Diode Curves, 6-9: Standard Platinum Curves,"
                                 " 21-28: User Curves.instead got {}".format(input))
        except ValueError as e:
            raise ValueError("Input must be valid curve. 1-5: Standard Diode Curves, 6-9: Standard Platinum Curves,"
                                 "21-28: User Curves. 1 and 200, instead got {}".format(input))

    @staticmethod
    def validate_point_index(input):
        try:
            if int(input) not in range(1, 201):
                raise ValueError("Input must be between 1 and 200, instead got {}".format(input))
        except ValueError as e:
            raise ValueError("Input must be between 1 and 200, instead got {}".format(input))

    @staticmethod
    def validate_Month(input):
        try:
            if int(input) not in range(1, 13):
                raise ValueError("Input must be {}, instead got {}".format(range(1,13),input))
        except ValueError as e:
            raise ValueError("Input must be {}, instead got {}".format(range(1,13),input))

    @staticmethod
    def validate_Day(input):
        try:
            if int(input) not in range(1, 32):
                raise ValueError("Input must be {}, instead got {}".format(range(1, 32), input))
        except ValueError as e:
            raise ValueError("Input must be {}, instead got {}".format(range(1, 32), input))

    @staticmethod
    def validate_Year(input):
        try:
            if int(input) not in range(0, 100):
                raise ValueError("Input must be {}, instead got {}".format(range(0, 100), input))
        except ValueError as e:
            raise ValueError("Input must be {}, instead got {}".format(range(0, 100), input))

    @staticmethod
    def validate_Hour(input):
        try:
            if int(input) not in range(0, 24):
                raise ValueError("Input must be {}, instead got {}".format(range(0, 24), input))
        except ValueError as e:
            raise ValueError("Input must be {}, instead got {}".format(range(0, 24), input))

    @staticmethod
    def validate_MinSec(input):
        try:
            if int(input) not in range(0, 60):
                raise ValueError("Input must be {}, instead got {}".format(range(0, 60), input))
        except ValueError as e:
            raise ValueError("Input must be {}, instead got {}".format(range(0, 60), input))

    @staticmethod
    def validate_input_group(input):
        try:
            if str(input) not in ['A', 'B']:
                raise ValueError("Input group must be {}, instead got {}".format(['A', 'B'], input))
        except ValueError as e:
            raise ValueError("Input group must be {}, instead got {}".format(['A', 'B'], input))

    class GetSensorReading(cmp.DriverQueryCommand):
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

    class GetAlarmParameters(DriverQueryCommand):
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

    class GetAlarmStatus(DriverQueryCommand):
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

    class GetAnalogOutputParameters(DriverQueryCommand):
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

    class GetAnalogOutputData(DriverQueryCommand):
        cmd = "AOUT?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_output_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return float(result)

    class GetBaudRate(DriverQueryCommand):
        cmd = "BAUD?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return (300, 1200, 9600)[int(result)]

    class GetCurveDataPoint(DriverQueryCommand):
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

    class GetDateTime(DriverQueryCommand):
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

    class GetDisplayedField(DriverQueryCommand):
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

    class GetFilterParameters(DriverQueryCommand):
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

    class GetIEEEParameters(DriverQueryCommand):
        cmd = "IEEE?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            resp = list(map(lambda x: x.strip(), result.split(',')))
            return {"term": int(resp[0]),
                    "EOI": int(resp[1]),
                    "address": int(resp[2])
                    }

    class GetCurveNumber(DriverQueryCommand):
        cmd = "INCRV?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetControlParameter(DriverQueryCommand):
        cmd = "INPUT?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetSensorType(DriverQueryCommand):
        cmd = "INTYPE?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_group(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetKeyStatus(DriverQueryCommand):
        cmd = "KEYST?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetLinearEqParameters(DriverQueryCommand):
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

    class GetLogStatus(DriverQueryCommand):
        cmd = "LOG?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetLogNumber(DriverQueryCommand):
        cmd = "LOGNUM?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetLogRecord(DriverQueryCommand):
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

    class GetLoggingParameters(DriverQueryCommand):
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

    #GetLoggedData is currently not working with LabView -> Parse Error: Unexpected lookahead type EOF
    class GetLoggedData(DriverQueryCommand):
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

    class GetLinearEquationData(DriverQueryCommand):
        cmd = "LRDG?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return(float(result))

    class GetMinMaxInputParameters(DriverQueryCommand):
        cmd = "MNMX?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return(int(result))

    class GetMinMaxData(DriverQueryCommand):
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

    class GetRemoteInterfaceMode(DriverQueryCommand):
        cmd = "MODE?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetInputStatus(DriverQueryCommand):
        cmd = "RDGST?"
        arguments = "{}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_input_number(pars[0])

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetRelayControlParameters(DriverQueryCommand):
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

    class GetRelayStatus(DriverQueryCommand):
        cmd = "RELAYST?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class SetDateTime(DriverWriteCommand):
        cmd = "DATETIME"
        arguments = "{}, {}, {}, {}, {}, {}"

        @classmethod
        def _validate(cls, pars):
            LS218Driver.validate_Month(pars[0])
            LS218Driver.validate_Day(pars[1])
            LS218Driver.validate_Year(pars[2])
            LS218Driver.validate_Hour(pars[3])
            LS218Driver.validate_MinSec(pars[4])
            LS218Driver.validate_MinSec(pars[5])

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read(sys.argv[1])
    LS218_config = config['LS218']

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
