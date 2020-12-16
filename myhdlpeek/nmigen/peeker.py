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

        # Create storage for signal trace.
        self.trace = Trace()

        # Assign a unique name to this peeker.
        self.name_dup = False  # Start off assuming the name has no duplicates.
        index = 0  # Starting index for disambiguating duplicates.
        nm = "{name}[{index}]".format(
            **locals()
        )  # Create name with bracketed index.
        # Search through the peeker names for a match.
        while nm in self._peekers:
            # A match was found, so mark the matching names as duplicates.
            self._peekers[nm].name_dup = True
            self.name_dup = True
            # Go to the next index and see if that name is taken.
            index += 1
            nm = "{name}[{index}]".format(**locals())
        self.trace.name = nm  # Assign the unique name.

        # Set the width of the signal.
        self.trace.num_bits = len(signal)

        # Keep a reference to the signal so we can get info about it later, if needed.
        self.signal = signal

        # Add this peeker to the global list.
        self._peekers[self.trace.name] = self

    @classmethod
    def assign_simulator(cls, simulator):
        """Assign nmigen Simulator to all Peekers."""

        def peek_process():
            while True:
                for peeker in cls.peekers():
                    peeker.trace.store_sample((yield peeker.signal), simulator._engine.now)
                yield Tick()

        simulator.add_process(peek_process)
