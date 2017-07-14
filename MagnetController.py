from SMSPowerSupplyDriver import SMSPowerSupplyDriver
from components import ControllerComponent, logger
import time
import json
import logging
import configparser
import sys

from state_machine.state_machine import StateMachine, State


class StateInitialize(State):
    @staticmethod
    def next():
        return StateIdle

    @staticmethod
    def run(controller):
        print(controller.get_mid())


class StateIdle(State):
    @staticmethod
    def next():
        return StateIdle

    @staticmethod
    def run(controller):
        print("Idle")


class MagnetController(ControllerComponent):
    def __init__(self, controller_queue, power_supply_driver, magnet_temperature_driver, hall_sensor_driver):
        super().__init__(controller_queue)
        self.power_supply_driver = power_supply_driver
        self.magnet_temperature_driver = magnet_temperature_driver
        self.hall_sensor_driver = hall_sensor_driver
        self.state_machine = StateMachine(self, StateInitialize)

    def wait_for_response(self):
        while self.server_response is None:
            pass
        response = self.server_response
        self.server_response = None
        return response

    def get_mid(self):
        self.send_direct_message(self.power_supply_driver,
                                 json.dumps({"CMD": SMSPowerSupplyDriver.GetMid.raw_command(['T'])}))

        return self.wait_for_response()

    def process_message(self, message):
        commands = message['CMD']
        results = []
        errors = []
        try:
            for command in commands.split(';'):
                result, error = self.execute_command(command)
                errors.append(error if error is not None else "")
                results.append(result if result is not None else "")
        except AttributeError:
            logger.exception("Received message with improper format")
        return results

    def execute_command(self, command):
        """Run the command and create a result object.
        The result object will be of the form
        {
            t0: time before sending command to instrument. -1 if there was a validation error
            t1: time after receiving reply from instrument. -1 if there was a validation error
            error: error message caused by validation problem or execution problem
            result: object containing the response from the instrument
        }
        """
        """result = None
        t0 = t1 = -1
        cmd, pars = self.split_cmd(command)
        error = self.check_command(cmd, pars)

        if error is None:
            # Get time before sending command to instrument
            t0 = time.time()

            result = self.all_commands[cmd].execute(self, cmd, pars, self.resource)

            # Get time after receiving reply from instrument
            # Having both times allows us to get an estimate of the time at which the command ran in case the instrument
            # does not report this
            t1 = time.time()

            # Set commands take time to process so there must be a time delay
            if cmd in self.set_commands:
                time.sleep(self.command_delay)

        command_result = {'t0': t0,
                          't1': t1,
                          'error': str(error) if error is not None else '',
                          'result': result if result is not None else ''}

        logger.debug(command_result)
        return command_result, error"""
        return None, None

    def run_state_machine(self):
        self.state_machine.run()


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read(sys.argv[1])
    MC_config = config['MagnetController']

    controller = MagnetController(MC_config['controller_queue'],
                                  MC_config['power_supply_driver'],
                                  MC_config['magnet_temperature_driver'],
                                  MC_config['hall_sensor_driver'])
    try:
        while True:
            controller.get_mid()
            time.sleep(0.5)
        controller.run_state_machine()
    except KeyboardInterrupt:
        pass
    finally:
        pass
        controller.close()
