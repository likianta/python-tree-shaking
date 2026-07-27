import sys
import typing as tp

from lk_utils import fs

from .module import KNOWN_STDLIB_MODULE_NAMES


def grab_global_modules() -> tp.Iterator[tp.Tuple[str, str, bool]]:
    # yields: tuple[name, path, isdir]
    for key, mod in sys.modules.items():
        if key.split('.')[0] in KNOWN_STDLIB_MODULE_NAMES:
            continue
        if hasattr(mod, '__file__'):
            if getattr(mod, '__file__'):
                assert mod.__file__, mod
                yield mod.__name__, fs.normpath(mod.__file__), False
            else:
                print(':v7n', 'mod has invalid __file__ attr', mod)
                assert len(mod.__path__) == 1, mod
                yield mod.__name__, fs.normpath(mod.__path__[0]), True
        else:  # e.g. '_cython_runtime', '_cython_3_1_4'
            print(':v8n', 'mod has no __file__ attr', mod)
