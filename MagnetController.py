from LS218Driver import LS218Driver
from SMSPowerSupplyDriver import SMSPowerSupplyDriver
from components import ControllerComponent, logger, QueryCommand, WriteCommand
import time
import json
import logging
import configparser
import sys

from state_machine.state_machine import StateMachine, State


class StateInitialize(State):
    def next(self, condition):
        return StateIdle, False

    def run(self):
        self.component.get_magnet_temperature()
        self.done = True
        print("Init")


class StateIdle(State):
    def next(self, condition):
        state = {"start_ramp": StateRampInit}.get(condition, StateIdle)
        return state, state != StateIdle

    def run(self):
        self.component.get_persistent_mode_heater_switch_temperature()
        self.component.get_magnet_temperature()
        self.component.get_field()
        print("Idle")


class StateRampInit(State):
    def next(self, condition):
        return StateWaitPersistentMode, False

    def run(self):
        self.component.set_persistent_mode_heater_switch(1)
        print("RampInit")
        self.done = True


class StateWaitPersistentMode(State):
    def __init__(self, component):
        super().__init__(component)
        self.switch_on_time = time.time()

    def next(self, condition):
        state = {"stop_ramp": StateRampDone}.get(condition, StateWaitPersistentMode)
        return state, state != StateWaitPersistentMode

    def run(self):
        temperature = self.component.get_persistent_mode_heater_switch_temperature()
        self.component.get_magnet_temperature()
        self.component.get_field()
        print(time.time() - self.switch_on_time)
        print("Wait Persistent Mode Temperature:", temperature)


class StateQuenched(State):
    @staticmethod
    def next(condition):
        return StateIdle

    @staticmethod
    def run(controller):
        print("Quenched")


class StateRampDone(State):
    def next(self, condition):
        return StateIdle, False

    def run(self):
        self.component.set_persistent_mode_heater_switch(0)
        print("RampDone")
        self.done = True


class StateRamping(State):
    @staticmethod
    def next(condition):
        state = {'stop_ramp': StateRampDone}.get(condition, StateRamping)
        return state

    @staticmethod
    def run(controller):
        #while not controller.at_setpoint:
        #    magnet_temperature = controller.get_magnet_temperature()
        #    if controller.safe_temperature(magnet_temperature):
        #        pass

        print("Ramping")


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
        self.persistent_heater_switch_temperature_channel = config['persistent_heater_switch_temperature_channel']

        self.magnet_temperature_channel = config['magnet_temperature_channel']
        self.magnet_safe_temperatures = np.array(json.loads(config['magnet_safe_temperatures'])).reshape((-1, 2))
        self.magnet_safe_temperatures_interp = interp1d(self.magnet_safe_temperatures[:,0], self.magnet_safe_temperatures[:,1])
        print(self.magnet_safe_temperatures)

        self.magnet_temperature = Measurement()
        self.field = Measurement()
        self.persistent_mode_heater_switch_temperature = Measurement()

        self.state_machine = StateMachine(self, StateInitialize)

        self.run_client_thread()
        self.run_server_thread()

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
        print(val)
        self.field.t0 = val['t0']
        self.field.t1 = val['t1']
        self.field.value = val['result']

    def get_mid(self):
        return self.send_message_and_get_reply(self.power_supply_driver, SMSPowerSupplyDriver.GetMid.raw_command(['A']))

    def set_setpoint(self, setpoint):
        return self.send_message_and_get_reply(self.power_supply_driver,
                                               SMSPowerSupplyDriver.SetSetpoint.raw_command([setpoint, 'T']))

    def set_ramp_rate(self, ramp_rate):
        return self.send_message_and_get_reply(self.power_supply_driver,
                                               SMSPowerSupplyDriver.SetRampRate.raw_command([ramp_rate, 'T']))

    def ramp(self, ramp_status):
        self.state_machine.condition = ['stop_ramp', 'start_ramp'][int(ramp_status)]

    def set_persistent_mode_heater_switch(self, on_off):
        # On = 1, Off = 0
        self.send_message_and_get_reply(self.power_supply_driver,
                                        SMSPowerSupplyDriver.SetPersistentHeaterStatus.raw_command([on_off]))

    def get_persistent_mode_heater_switch_temperature(self):
        val = self.send_message_and_get_reply(self.magnet_temperature_driver,
                                        LS218Driver.GetKelvinReading.raw_command([self.persistent_heater_switch_temperature_channel]))[0]
        self.persistent_mode_heater_switch_temperature.t0 = val['t0']
        self.persistent_mode_heater_switch_temperature.t1 = val['t1']
        self.persistent_mode_heater_switch_temperature.value = val['result']
        return self.persistent_mode_heater_switch_temperature.value

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

    def run_state_machine(self):
        self.state_machine.run()

    class GetField(QueryCommand):
        cmd = "GetField"
        arguments = ""

        @classmethod
        def execute(cls, controller, cmd, pars):
            print(controller.field)
            if controller.field.value == None:
                print(controller.field)
            return controller.field.value

    class GetMagnetTemperature(QueryCommand):
        cmd = "GetMagnetTemperature"
        arguments = ""

        @classmethod
        def execute(cls, controller, cmd, pars):
            return controller.magnet_temperature.value

    class SetSetpoint(WriteCommand):
        cmd = "SetSetpoint"
        arguments = "{}"

        @classmethod
        def execute(cls, controller, cmd, pars):
            return controller.set_setpoint(*pars)

    class SetRampRate(WriteCommand):
        cmd = "SetRampRate"
        arguments = "{}"

        @classmethod
        def execute(cls, controller, cmd, pars):
            return controller.set_ramp_rate(*pars)

    class Ramp(WriteCommand):
        cmd = "Ramp"
        arguments = "{}"

        @classmethod
        def execute(cls, controller, cmd, pars):
            return controller.ramp(*pars)

    class GetPersistentHeaterTemperature(QueryCommand):
        cmd = "GetPersistentHeaterTemperature"
        arguments = ""

        @classmethod
        def execute(cls, controller, cmd, pars):
            return controller.persistent_mode_heater_switch_temperature.value


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
