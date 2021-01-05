# -*- coding: utf-8 -*-

# Copyright (c) 2017-2020, XESS Corp. The MIT License (MIT).

from __future__ import absolute_import, division, print_function, unicode_literals

import functools
from builtins import dict, int, str, super

from future import standard_library
from nmigen.sim import Tick

from ..peekerbase import *

standard_library.install_aliases()


class Peeker(PeekerBase):
    def __init__(self, signal, name=None):

        # Get the name from the signal if it's not explicitly given.
        if not name:
            name = signal.name

        super().__init__(signal, name)

        # Set the width of the signal.
        self.trace.num_bits = len(signal)

        # The VCD writer won't store a sample until the signal changes,
        # so store the default signal value at time zero to initialize
        # the trace.
        self.trace.store_sample(0, 0)  # Signal value 0 at time 0.

    @classmethod
    def assign_simulator(cls, simulator, use_vcd_writer=False):
        """Capture traces using a synchronous process or a VCD writer."""

        if use_vcd_writer:
            simulator._engine._vcd_writers.append(cls)

        else:
            # Use a synchronous process to capture trace samples.
            def peek_process():
                while True:
                    for peeker in cls.peekers.values():
                        peeker.trace.store_sample(
                            (yield peeker.signal), simulator._engine.now
                        )
                    yield Tick()

            simulator.add_process(peek_process)

    @classmethod
    def update(cls, time, signal, value):
        """Called during VCD writing to record signal value."""

        for peeker in cls.peekers.values():
            if id(peeker.signal) == id(signal):
                # print(f"store: {peeker.trace.name} {value} @ {time}")
                peeker.trace.store_sample(value, time)
                return
