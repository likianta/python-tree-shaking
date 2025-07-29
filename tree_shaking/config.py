import atexit
import hashlib
import typing as t
from functools import partial
from os.path import isabs

from lk_utils import fs

from .path_scope import path_scope


class T:
    AnyDirPath = str
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
    NormPath = str  # absolute path.
    RelPath = str  # relative path, starts from `root`.
    
    # noinspection PyTypedDict
    Config0 = t.TypedDict('Config0', {
        'root'        : AnyDirPath,
        'search_paths': t.List[RelPath],
        'entries'     : t.List[RelPath],  # must ends with ".py"
        'ignores'     : t.List[IgnoredName],
        'sole_export' : t.Optional[RelPath],
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
        'sole_export' : t.Optional[NormPath],
    })
    
    Config = Config1


graphs_root = fs.xpath('_cache/module_graphs')


def parse_config(file: str, _save: bool = False, **kwargs) -> T.Config:
    """
    file:
        - the file ext must be '.yaml' or '.yml'.
        - we suggest using 'xxx-modules.yaml', 'xxx_modules.yaml' or just
        'modules.yaml' as the file name.
        see example of `[project] depsland : -
        /build/build_tool/_tree_shaking_model.yaml`.
    """
    cfg_file: str = fs.abspath(file)
    cfg_dir: str = fs.parent(cfg_file)
    cfg0: T.Config0 = fs.load(cfg_file)
    cfg1: T.Config1 = {
        'root'        : '',
        'search_paths': [],
        'entries'     : {},
        'ignores'     : (),
        'sole_export' : None,
    }
    
    # 1
    if isabs(cfg0['root']):
        cfg1['root'] = fs.normpath(cfg0['root'])
    else:
        cfg1['root'] = fs.normpath('{}/{}'.format(cfg_dir, cfg0['root']))
    
    # 2
    _root = cfg1['root']
    
    def fmtpath(p: T.RelPath) -> T.NormPath:
        if p == '.': return _root
        assert not p.startswith(('./', '../', '<')), p
        out = '{}/{}'.format(_root, p)
        assert fs.exist(out)
        return out
    
    temp = cfg1['search_paths']
    for p in map(fmtpath, cfg0['search_paths']):
        temp.append(p)
        path_scope.add_scope(p)
    
    # 3
    temp = cfg1['entries']
    for p in cfg0['entries']:
        p = fmtpath(p)
        temp[p] = hash_path_to_uid(p)
    
    # 4
    cfg1['ignores'] = frozenset(cfg0.get('ignores', ()))
    
    # 5
    if x := (kwargs.get('sole_export') or cfg0.get('sole_export')):
        assert x in cfg0['search_paths']  # noqa
        cfg1['sole_export'] = fmtpath(x)
    
    if _save:
        atexit.register(partial(_save_graph_alias, cfg1))
    
    # print(cfg1, ':l')
    return cfg1


def hash_path_to_uid(abspath: str) -> str:
    return hashlib.md5(abspath.encode()).hexdigest()


def _save_graph_alias(config: T.Config1) -> None:
    map_ = fs.load(fs.xpath('_cache/module_graphs_alias.yaml'), default={})
    if config['root'] in map_:
        if (
            set(config['entries'].values()) ==
            set(map_[config['root']].values())
        ):
            return
    map_[config['root']] = {
        # k.replace(config['root'], '<root>'): v
        fs.relpath(k, config['root']): v
        for k, v in config['entries'].items()
    }
    fs.dump(map_, fs.xpath('_cache/module_graphs_alias.yaml'), sort_keys=True)
