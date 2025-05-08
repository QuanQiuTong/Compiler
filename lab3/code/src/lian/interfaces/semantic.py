#!/usr/bin/env python3

import os,sys

from lian.semantic.traversal import InternalTraversal
from lian.util import util


def run(options, module_symbols):
    InternalTraversal(options, module_symbols).run()
    
