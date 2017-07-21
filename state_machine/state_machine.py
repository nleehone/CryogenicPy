class State(object):
    def __init__(self, component):
        self.component = component
        self.done = False

    def enter(self):
        pass

    def run(self):
        pass

    def exit(self):
        pass

    def next(self, condition):
        raise NotImplementedError()


class StateMachine(object):
    def __init__(self, component, initial_state):
        self.component = component
        self.condition = None

        self.current_state = initial_state(self.component)
        self.current_state.enter()

    def run(self):
        while True:
            self.current_state.run()

            if self.current_state.done:
                self.current_state.exit()
                # Get the next state to be run
                state, used_condition = self.current_state.next(self.condition)
                self.current_state = state(self.component)
                self.current_state.enter()

            elif self.condition is not None:
                # Get the next state to be run
                state, used_condition = self.current_state.next(self.condition)
                if used_condition:
                    self.current_state.exit()
                    self.current_state = state(self.component)
                    self.current_state.enter()
                    self.condition = None