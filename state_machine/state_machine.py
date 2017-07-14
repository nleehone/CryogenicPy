class State(object):
    @staticmethod
    def run(parent):
        raise NotImplementedError()

    @staticmethod
    def next():
        raise NotImplementedError()


class StateMachine(object):
    def __init__(self, parent, initial_state):
        self.parent = parent
        self.current_state = initial_state

    def run(self):
        while True:
            self.current_state.run(self.parent)
            self.current_state = self.current_state.next()