class State(object):
    def __init__(self, component):
        self.component = component
        self.done = False

    def run(self):
        raise NotImplementedError()

    def next(self, condition):
        raise NotImplementedError()

    def setup(self):
        pass


class StateMachine(object):
    def __init__(self, component, initial_state):
        self.component = component
        self.current_state = initial_state(self.component)
        self.condition = None

    def run(self):
        while True:
            self.current_state.run()
            if self.current_state.done or self.condition is not None:
                state, used_condition = self.current_state.next(self.condition)
                self.current_state = state(self.component)
                self.current_state.setup()
                if used_condition:
                    self.condition = None