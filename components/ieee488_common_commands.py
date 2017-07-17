from components import WriteCommand, QueryCommand, validate_range, DriverWriteCommand, DriverQueryCommand


class IEEE488_CommonCommands(object):
    """Common IEEE-488 commands are defined here. To use this class, include it in the Driver's definition:
    class SomeDriver(IEEE488_CommonCommands, Driver):
    """
    class ClearStatus(DriverWriteCommand):
        cmd = "*CLS"

    class SetEventStatusEnable(DriverWriteCommand):
        cmd = "*ESE"
        arguments = "{}"
        num_args = 1

        @classmethod
        def _validate(cls, pars):
            validate_range(pars[0], 0, 255)

    class GetEventStatusEnable(DriverQueryCommand):
        cmd = "*ESE?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetEventStatusRegister(DriverQueryCommand):
        cmd = "*ESR?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetIdentification(DriverQueryCommand):
        cmd = "*IDN?"

    class SetOperationComplete(DriverWriteCommand):
        cmd = "*OPC"

    class GetOperationComplete(DriverQueryCommand):
        cmd = "*OPC?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class ResetInstrument(DriverWriteCommand):
        cmd = "*RST"

    class SetServiceRequestEnable(DriverWriteCommand):
        cmd = "*SRE"
        arguments = "{}"
        num_args = 1

    class GetServiceRequestEnable(DriverQueryCommand):
        cmd = "*SRE?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class GetStatusByte(DriverQueryCommand):
        cmd = "*STB?"

        @classmethod
        def process_result(cls, driver, cmd, pars, result):
            return int(result)

    class SelfTest(DriverWriteCommand):
        cmd = "*TST?"

    class Wait(DriverWriteCommand):
        cmd = "*WAI"
