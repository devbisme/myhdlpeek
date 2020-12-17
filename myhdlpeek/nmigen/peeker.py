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

    @classmethod
    def assign_simulator(cls, simulator):
        """Assign nmigen Simulator to all Peekers."""

        def peek_process():
            while True:
                for peeker in cls.peekers():
                    peeker.trace.store_sample((yield peeker.signal), simulator._engine.now)
                yield Tick()

        simulator.add_process(peek_process)
