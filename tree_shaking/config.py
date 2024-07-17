import typing as t
from functools import partial
from os.path import isabs

from lk_utils import fs

from .path_scope import path_scope


class T:
    AnyPath = str
    """
        - absolute or relative to the config file itself.
        - separate with '/'.
        - for relative path, must start with './' or '../'.
        - directory must end with '/'.
        - use '<root>' to indicate the root directory.
            for example '<root>/venv'
        - use '<module>' to indicate the module directory.
            (it locates at `<python-tree-shaking-project>/data/module_graphs`)
    """
    AnyDirPath = str
    AnyScriptPath = str
    """
        - must be a '.py' script file.
        - other rules same as `AnyDirPath`.
    """
    GraphName = str
    NormPath = str
    
    # noinspection PyTypedDict
    Config0 = t.TypedDict('Config0', {
        'root'        : AnyDirPath,
        'search_paths': t.List[AnyDirPath],
        'modules'     : t.Dict[AnyScriptPath, GraphName],
        'build'       : t.TypedDict('Build', {
            'module_graphs': t.Union[t.Literal['*'], t.List[str]],
            'spec_files'   : t.Iterable[AnyPath],
        }),
    }, total=False)
    """
        {
            'root': str dirpath,
            'search_paths': (dirpath, ...),
            'modules': {
                script: graph_name, ...
            },
            'build': {
                'module_graphs': '*' | (graph_name, ...),
                'spec_files': (path, ...),
            }
        }
    """
    
    # noinspection PyTypedDict
    Config1 = t.TypedDict('Config1', {
        'root'        : NormPath,
        'search_paths': t.List[NormPath],
        'modules'     : t.Dict[NormPath, GraphName],
        'build'       : t.TypedDict('Build', {
            'module_graphs': t.List[NormPath],
            'spec_files'   : t.List[t.Tuple[NormPath, bool]],
            # 'spec_files'   : t.List[NormPath],
        }),
    })
    
    Config = Config1


def parse_config(file: str) -> T.Config:
    """
    file: see example at `examples/depsland_modules.yaml`.
        - the file ext must be '.yaml' or '.yml'.
        - we suggest using 'xxx-modules.yaml', 'xxx_modules.yaml' or just
        'modules.yaml' as the file name.
    """
    file: str = fs.abspath(file)
    cfg_dir: str = fs.parent(file)
    cfg: T.Config0 = fs.load(file)
    out: T.Config1 = {
        'root'        : '',
        'search_paths': [],
        'modules'     : {},
        'build'       : {'module_graphs': [], 'spec_files': []}
    }
    
    if isabs(cfg['root']):
        out['root'] = fs.normpath(cfg['root'])
    else:
        out['root'] = fs.normpath('{}/{}'.format(cfg_dir, cfg['root']))
    
    pathfmt = partial(_format_path, root=out['root'], base=cfg_dir)
    
    temp = out['search_paths']
    for p in map(pathfmt, cfg['search_paths']):
        temp.append(p)
        path_scope.add_scope(p)
    
    temp = out['modules']
    for p, n in cfg.get('modules', {}).items():
        p = pathfmt(p)
        temp[p] = n
    
    # 1/3
    if 'build' not in cfg:
        # noinspection PyTypedDict
        cfg['build'] = {'module_graphs': '*', 'spec_files': ()}
    else:
        if 'module_graphs' not in cfg['build']:
            # noinspection PyTypedDict
            cfg['build']['module_graphs'] = '*'
        if 'spec_files' not in cfg['build']:
            cfg['build']['spec_files'] = ()
    # 2/3
    if cfg['build']['module_graphs'] == '*':
        graph_names = out['modules'].values()
    else:
        graph_names = cfg['build']['module_graphs']
    for n in graph_names:
        graph_file = '{}/{}.yaml'.format(_graph_dir, n)
        out['build']['module_graphs'].append(graph_file)
    # 3/3
    for f in cfg['build']['spec_files']:
        out['build']['spec_files'].append((pathfmt(f), f.endswith('/')))
    
    # print(out, ':l')
    return out


_graph_dir = fs.xpath('../data/module_graphs')


def _format_path(path: str, root: str, base: str) -> str:
    if path.startswith(('./', '../')):
        path = fs.normpath('{}/{}'.format(base, path))
    elif path.startswith('<root>'):
        path = fs.normpath(path.replace('<root>', root))
    elif path.startswith('<module>'):
        path = fs.normpath(path.replace('<module>', _graph_dir))
    else:
        path = fs.normpath(path)
    assert isabs(path) and fs.exists(path), path
    return path
