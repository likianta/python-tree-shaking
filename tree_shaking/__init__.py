if 1:
    # fmt: off
    import neoprint as _np
    _np.setup()
    # fmt: on

from .cache import cache_root
from .config import T
from .config import parse_config
from .export import dump_tree
from .graph import build_module_graph
from .graph import build_module_graphs

__version__ = '0.2.6'
