from LS218Driver import LS218Driver
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
        return StateInitialize

    @staticmethod
    def run(controller):
        controller.get_magnet_temperature()
        print(controller.magnet_temperature)
        print(controller.safe_temperature())


class StateIdle(State):
    @staticmethod
    def next():
        return StateIdle

    @staticmethod
    def run(controller):
        controller.get_magnet_temperature()
        print("Idle")


class StateQuenched(State):
    @staticmethod
    def next():
        return StateIdle

    @staticmethod
    def run(controller):
        print("Quenched")


class StateRampInit(State):
    @staticmethod
    def next():
        return StateRamping

    @staticmethod
    def run(controller):
        print("RampInit")


class StateRampDone(State):
    @staticmethod
    def next():
        return StateIdle

    @staticmethod
    def run(controller):
        print("RampDone")


class StateRamping(State):
    @staticmethod
    def next():
        return StateRampDone

    @staticmethod
    def run(controller):
        while not controller.at_setpoint:
            magnet_temperature = controller.get_magnet_temperature()
            if controller.safe_temperature(magnet_temperature):
                pass

        print("Ramping")


class StateQuenched(State):
    @staticmethod
    def next():
        return StateIdle

    @staticmethod
    def run(controller):
        print("Quenched")


class Measurement(object):
    def __init__(self):
        self.value = None
        self.t0 = -1
        self.t1 = -1

    def __repr__(self):
        return "{}-{}: {}".format(self.t0, self.t1, self.value)


import numpy as np
import scipy as sp
from scipy.interpolate import interp1d


class MagnetController(ControllerComponent):
    def __init__(self, config):
        super().__init__(config['controller_queue'])
        self.power_supply_driver = config['power_supply_driver']
        self.magnet_temperature_driver = config['magnet_temperature_driver']
        self.hall_sensor_driver = config['hall_sensor_driver']

        self.magnet_temperature_channel = config['magnet_temperature_channel']
        self.magnet_safe_temperatures = np.array(json.loads(config['magnet_safe_temperatures'])).reshape((-1, 2))
        self.magnet_safe_temperatures_interp = interp1d(self.magnet_safe_temperatures[:,0], self.magnet_safe_temperatures[:,1])
        print(self.magnet_safe_temperatures)

        self.magnet_temperature = Measurement()
        self.field = Measurement()

        self.state_machine = StateMachine(self, StateInitialize)

    def send_message_and_get_reply(self, queue, command):
        self.send_direct_message(queue, json.dumps({"CMD": command}))
        return self.wait_for_response()

    def wait_for_response(self):
        while self.server_response is None:
            pass
        response = json.loads(self.server_response.decode('utf-8'))
        self.server_response = None
        return response

    def get_magnet_temperature(self):
        val = self.send_message_and_get_reply(self.magnet_temperature_driver,
                                               LS218Driver.GetKelvinReading.raw_command([self.magnet_temperature_channel]))[0]
        self.magnet_temperature.t0 = val['t0']
        self.magnet_temperature.t1 = val['t1']
        self.magnet_temperature.value = val['result']

    def safe_temperature(self):
        self.get_magnet_temperature()
        self.get_field()

        if self.field.value:
            pass

    def get_field(self):
        val = self.send_message_and_get_reply(self.power_supply_driver,
                                              SMSPowerSupplyDriver.GetOutput.raw_command(['T']))[0]
        self.field.t0 = val['t0']
        self.field.t1 = val['t1']
        self.field.value = val['result']
        print(self.field)

    def get_mid(self):
        return self.send_message_and_get_reply(self.power_supply_driver, SMSPowerSupplyDriver.GetMid.raw_command(['A']))

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

    controller = MagnetController(MC_config)
    try:
        controller.run_state_machine()
    except KeyboardInterrupt:
        pass
    finally:
        pass
        controller.close()
