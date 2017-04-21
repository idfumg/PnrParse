#!/usr/bin/env python

import re
from pnr_types import *

def logit(fn):
    def wrapper(*args, **kwargs):
        print('called: {0}'.format(fn.__name__))
        return fn(*args, **kwargs)
    return wrapper
