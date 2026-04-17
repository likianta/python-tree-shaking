import atexit
import hashlib
import os
import sys
import typing as t
from functools import cache
from functools import partial
from lk_utils import fs
from lk_utils import run_cmd_args
from os.path import isabs
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
    SpecialPath = str  # '$venv' or `$venv/...`
    
    # noinspection PyTypedDict
    Config0 = t.TypedDict('Config0', {
        'root'        : AnyDirPath,
        'search_paths': t.List[t.Union[RelPath, SpecialPath]],
        'entries'     : t.List[RelPath],  # must ends with ".py"
        'ignores'     : t.List[IgnoredName],
        'export'      : t.Optional[t.TypedDict('ExportOption0', {
            'source': t.Union[SpecialPath, AnyDirPath],
            'target': AnyDirPath,
        })],
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
        'export'      : t.TypedDict('ExportOption1', {
            'source': NormPath, 'target': NormPath,
        }),
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
        'export'      : {'source': '', 'target': ''},
    }
    
    # 1
    if isabs(cfg0['root']):  # not suggested
        cfg1['root'] = fs.normpath(cfg0['root'])
    else:
        cfg1['root'] = fs.normpath('{}/{}'.format(cfg_dir, cfg0['root']))
    
    # 2
    _root = cfg1['root']
    
    def fmtpath(p: t.Union[T.RelPath, T.SpecialPath]) -> T.NormPath:
        if p == '': 
            raise ValueError('path cannot be empty')
        if p == '.': 
            return _root
        if p.startswith('$venv'): 
            return p.replace('$venv', _get_venv_root(_root), 1)
        assert not p.startswith(('./', '../', '<')), p
        out = '{}/{}'.format(_root, p)
        assert fs.exist(out), out
        return out
    
    temp = cfg1['search_paths']
    for p in map(fmtpath, reversed(cfg0['search_paths'])):
        temp.append(p)
        path_scope.add_scope(p)
    
    # 3
    temp = cfg1['entries']
    for p in cfg0['entries']:
        p = fmtpath(p)
        temp[p] = hash_path_to_uid(p)
    
    # 4
    cfg1['ignores'] = frozenset(cfg0.get('ignores', ()))  # type: ignore
    
    # 5
    dict0 = kwargs.get('export', {'source': '', 'target': ''})
    dict1 = cfg0.get('export', {'source': '', 'target': ''})
    if src := (dict0['source'] or dict1['source']):
        assert src in cfg0['search_paths']
        cfg1['export']['source'] = fmtpath(src)
    if dict0['target']:
        cfg1['export']['target'] = fs.abspath(dict0['target'])
    elif dict1['target']:
        cfg1['export']['target'] = fs.normpath('{}/{}'.format(
            cfg1['root'], dict1['target']
        ))
    
    if _save:
        atexit.register(partial(_save_graph_alias, cfg1))
    
    # print(cfg1, ':l')
    return cfg1

def hash_path_to_uid(abspath: str) -> str:
    return hashlib.md5(abspath.encode()).hexdigest()

@cache
def _get_venv_root(working_root: str) -> T.NormPath:
    """
    find venv root (the "site-packages" folder) by `poetry env` command.
    """
    # https://stackoverflow.com/questions/75232761/
    if 'VIRTUAL_ENV' in os.environ:
        del os.environ['VIRTUAL_ENV']
    venv_root = fs.normpath(
        run_cmd_args(
            (
                sys.executable, '-m', 'poetry', 'env', 'info', '--path', 
                '--no-ansi', '--directory', working_root
            ), 
            cwd=working_root,
        )
    )
    print(venv_root)
    assert venv_root.endswith('py3.12')
    
    if os.name == 'nt':
        out = '{}/Lib/site-packages'.format(venv_root)
    else:
        out = '{}/lib/python{}.{}/site-packages'.format(
            venv_root, sys.version_info.major, sys.version_info.minor
        )
    assert fs.exist(out), (working_root, venv_root, out)
    return out

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
