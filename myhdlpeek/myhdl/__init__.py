from ..peekerbase import setup
from .peeker import Peeker
setup(cls=Peeker)

from ..trace import *
from ..peekerbase import *

from functools import partial
setup = partial(setup, cls=Peeker)
