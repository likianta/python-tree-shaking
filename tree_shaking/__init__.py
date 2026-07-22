# fmt: off
if 1: import neoprint as _np; _np.setup()  # noqa
# fmt: on

from .cache import cache_maker
from .cache import cache_root
from .config import T
from .config import parse_config
from .export import dump_tree
from .graph import build_module_graphs
from .patch import implicit_hooks_file

__version__ = '0.4.0'
