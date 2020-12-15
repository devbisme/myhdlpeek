# -*- coding: utf-8 -*-

# Copyright (c) 2017-2020, XESS Corp. The MIT License (MIT).

from ..peekerbase import setup
from .peeker import Peeker
setup(cls=Peeker)

from ..trace import *
from ..peekerbase import *

from functools import partial
setup = partial(setup, cls=Peeker)
