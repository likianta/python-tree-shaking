import sys

from lk_utils import fs

from .module import KNOWN_STDLIB_MODULE_NAMES


def grab_global_modules():
    for key, mod in sys.modules.items():
        if key.split('.')[0] in KNOWN_STDLIB_MODULE_NAMES:
            continue
        if hasattr(mod, '__file__'):
            assert mod.__file__, mod
            yield mod.__name__, fs.normpath(mod.__file__)
        else:  # e.g. '_cython_runtime', '_cython_3_1_4'
            print(':v8n', mod)
