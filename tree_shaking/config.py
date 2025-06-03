import hashlib
import typing as t
from functools import partial
from os.path import isabs

from lk_utils import fs

from .path_scope import path_scope


class T:
    AnyPath = str
    #   - absolute path, or relative path based on the config file itself.
    #   - separated by '/', no '\\'.
    #   - for relative path, must start with './' or '../'.
    #   - for directory, path must end with '/'.
    #   - use '<root>' to indicate the root directory.
    #       for example: '<root>/venv'
    #   - use '<module>' to indicate the module directory.
    #       (it locates at `<python-tree-shaking-project>/data/module_graphs`)
    AnyDirPath = str
    AnyScriptPath = str
    #   must be a '.py' script file.
    #   other rules same as `AnyPath`.
    GraphId = str
    #   just the md5 value of its abspath. see `_hash_path_to_uid()`.
    IgnoredName = str
    #   - must be lower case.
    #   - use underscore, not hyphen.
    #   - use correct name.
    #   for example:
    #       wrong       right
    #       -----       -------
    #       IPython     ipython
    #       lk-utils    lk_utils
    #       pillow      pil
    NormPath = str
    #   normalized path, must be absolute path.
    
    # noinspection PyTypedDict
    Config0 = t.TypedDict('Config0', {
        'root'        : AnyDirPath,
        'search_paths': t.List[AnyDirPath],
        'entries'     : t.List[AnyScriptPath],
        'ignores'     : t.List[IgnoredName],
    }, total=False)
    """
        {
            'root': dirpath,
            'search_paths': (dirpath, ...),
            'entries': (script_path, ...),
            'ignores': (module_name, ...),
            #   module_name is case sensitive.
        }
    """
    
    # noinspection PyTypedDict
    Config1 = t.TypedDict('Config1', {
        'root'        : NormPath,
        'search_paths': t.List[NormPath],
        'entries'     : t.Dict[NormPath, GraphId],
        'ignores'     : t.Union[t.FrozenSet[str], t.Tuple[str, ...]],
        # 'exports'     : t.Sequence[str],
    })
    
    Config = Config1


graphs_root = fs.xpath('_cache/module_graphs')


def parse_config(file: str) -> T.Config:
    """
    file: see example at `examples/depsland_modules.yaml`.
        - the file ext must be '.yaml' or '.yml'.
        - we suggest using 'xxx-modules.yaml', 'xxx_modules.yaml' or just
        'modules.yaml' as the file name.
    """
    cfg_file: str = fs.abspath(file)
    cfg_dir: str = fs.parent(cfg_file)
    cfg: T.Config0 = fs.load(cfg_file)
    out: T.Config1 = {
        'root'        : '',
        'search_paths': [],
        'entries'     : {},
        'ignores'     : (),
        # 'exports'     : (),
    }
    
    # 1
    if isabs(cfg['root']):
        out['root'] = fs.normpath(cfg['root'])
    else:
        out['root'] = fs.normpath('{}/{}'.format(cfg_dir, cfg['root']))
    
    # 2
    pathfmt = partial(_format_path, root=out['root'], base=cfg_dir)
    
    temp = out['search_paths']
    for p in map(pathfmt, cfg['search_paths']):
        temp.append(p)
        path_scope.add_scope(p)
    
    # 3
    temp = out['entries']
    for p in cfg['entries']:
        p = pathfmt(p)
        temp[p] = hash_path_to_uid(p)
    
    # 4
    out['ignores'] = frozenset(cfg.get('ignores', ()))
    
    # print(out, ':l')
    return out


def hash_path_to_uid(abspath: str) -> str:
    return hashlib.md5(abspath.encode()).hexdigest()


def _format_path(path: str, root: str, base: str) -> str:
    # note: return an absolute path.
    if path.startswith(('./', '../')):
        path = fs.normpath('{}/{}'.format(base, path))
    elif path.startswith('<root>'):
        path = fs.normpath(path.replace('<root>', root))
    elif path.startswith('<module>'):
        path = fs.normpath(path.replace('<module>', graphs_root))
    else:
        path = fs.normpath(path)
    assert isabs(path) and fs.exists(path), path
    return path
