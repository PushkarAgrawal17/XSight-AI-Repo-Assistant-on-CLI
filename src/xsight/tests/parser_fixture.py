import os
import numpy as np
from collections import OrderedDict
from typing import List, Dict as D
from ..parser.tests import sibling
from .pkg import helper
from mymodule import *


def top_level_function(x: int) -> int:
    return x + 1


async def top_level_async_function() -> None:
    pass


class Base:
    pass


class Derived(Base):
    def normal_method(self) -> None:
        pass

    @staticmethod
    def decorated_method() -> None:
        pass


@dataclass
class DecoratedClass:
    pass