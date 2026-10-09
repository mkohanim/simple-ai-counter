import os

import udi_interface

from counter_core import CounterCore

LOGGER = udi_interface.LOGGER
Node = udi_interface.Node


class CounterNode(Node):
    id = 'counter'
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 25},
        {'driver': 'COUNTER', 'value': 0, 'uom': 114},
        {'driver': 'STEP_SIZE', 'value': 1, 'uom': 108},
    ]

    def __init__(self, polyglot, primary, address, name, persist_dir=None):
        super().__init__(polyglot, primary, address, name)
        state_file = os.path.join(persist_dir, 'counter_state.json') if persist_dir else None
        self.core = CounterCore(state_file=state_file, on_change=self._push)

    def _push(self):
        count, step, running = self.core.snapshot()
        self.setDriver('ST', 1 if running else 0)
        self.setDriver('COUNTER', count)
        self.setDriver('STEP_SIZE', step)

    def begin(self):
        self.core.begin()

    def shutdown(self):
        self.core.shutdown()

    def query(self, command=None):
        self._push()

    def cmd_start(self, command=None):
        self.core.start()

    def cmd_stop(self, command=None):
        self.core.stop()

    def cmd_increment(self, command=None):
        self.core.increment()

    def cmd_decrement(self, command=None):
        self.core.decrement()

    def cmd_set_step(self, command=None):
        if isinstance(command, dict):
            value = command.get('value')
        else:
            value = getattr(command, 'value', None)
        try:
            self.core.set_step(value)
        except ValueError as e:
            LOGGER.error('SET_STEP rejected: %s', e)
            self._push()  # restore the displayed value

    commands = {
        'START': cmd_start,
        'STOP': cmd_stop,
        'INCREMENT': cmd_increment,
        'DECREMENT': cmd_decrement,
        'SET_STEP': cmd_set_step,
    }
