import typing as tp
from os.path import isabs as is_abspath

from lk_utils import fs

from .cache import cache_maker
from .path_scope import path_scope


class T:
    AnyDirPath = str
    IgnoredName = str
    #   - must be lower case.
    #   - use underscore, not hyphen.
    #   - use correct name.
    #   for example:
    #       wrong       right
    #       --------    --------
    #       IPython     ipython
    #       lk-utils    lk_utils
    #       pillow      pil
    NormPath = str  # absolute path.
    RelPath = str  # relative path, starts from `root`.
    SpecialPath = str  # '$venv' or `$venv/...`

    Config0 = tp.TypedDict(
        'Config0',
        {
            'root': AnyDirPath,
            'search_paths': tp.List[tp.Union[RelPath, SpecialPath]],
            'entries': tp.List[RelPath],  # must ends with ".py"
            'ignores': tp.List[IgnoredName],
            'export': tp.Optional[
                tp.TypedDict(  # ty: ignore
                    'ExportOption0',
                    {
                        'source': tp.Union[SpecialPath, AnyDirPath],
                        'target': AnyDirPath,
                    },
                )
            ],
        },
        total=False,
    )
    #   {
    #       'root': dirpath,
    #       'search_paths': (dirpath, ...),
    #       'entries': (script_path, ...),
    #       'ignores': (module_name, ...),
    #       #   module_name is case sensitive.
    #   }

    Config1 = tp.TypedDict(
        'Config1',
        {
            'root': NormPath,
            'search_paths': tp.List[NormPath],
            'entries': tp.Tuple[NormPath, ...],
            'ignores': tp.Union[tp.FrozenSet[str], tp.Tuple[str, ...]],
            'export': tp.TypedDict(  # ty: ignore
                'ExportOption1', {'source': NormPath, 'target': NormPath}
            ),
        },
    )

    Config = Config1


def parse_config(file: str, **kwargs) -> T.Config:
    """
    file:
        - file can be YAML or JSON.
        - we suggest using 'xxx-modules.yaml', 'xxx_modules.yaml' or just
        'modules.yaml' as the file name.
        see example of `[project] depsland :
        /build/build_tool/_tree_shaking_model.yaml`.
    """
    cfg_file: str = fs.abspath(file)

    if x := cache_maker.get_cache(cfg_file, 'config'):
        return x

    cfg_dir: str = fs.parent(cfg_file)
    cfg0: T.Config0 = fs.load(cfg_file)
    cfg1: T.Config1 = {
        'root': '',
        'search_paths': [],
        'entries': (),
        'ignores': (),
        'export': {'source': '', 'target': ''},
    }

    # 1
    if is_abspath(cfg0['root']):  # not suggested
        cfg1['root'] = fs.normpath(cfg0['root'])
    else:
        cfg1['root'] = fs.normpath('{}/{}'.format(cfg_dir, cfg0['root']))

    # 2
    _root = cfg1['root']

    def fmtpath(p: tp.Union[T.RelPath, T.SpecialPath]) -> T.NormPath:
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

    for p in map(fmtpath, reversed(cfg0['search_paths'])):
        cfg1['search_paths'].append(p)
        path_scope.add_scope(p)

    # 3
    cfg1['entries'] = tuple(map(fmtpath, cfg0['entries']))

    # 4
    cfg1['ignores'] = frozenset(cfg0.get('ignores', ()))

    # 5
    dict0 = kwargs.get('export', {'source': '', 'target': ''})
    dict1 = cfg0.get('export', {'source': '', 'target': ''})
    if src := (dict0['source'] or dict1['source']):  # type: ignore
        assert src in cfg0['search_paths']
        cfg1['export']['source'] = fmtpath(src)
    if dict0['target']:
        cfg1['export']['target'] = fs.abspath(dict0['target'])
    elif dict1['target']:  # type: ignore
        cfg1['export']['target'] = fs.normpath(
            '{}/{}'.format(cfg1['root'], dict1['target'])  # type: ignore
        )

    # print(cfg1, ':ln')
    cache_maker.save_cache(cfg_file, 'config', cfg1)
    return cfg1


def _get_venv_root(working_root: str) -> T.NormPath:
    """
    find venv root (the "site-packages" folder).
    """
    if fs.exist('{}/.venv'.format(working_root)):
        assert fs.exist('{}/.venv/Lib/site-packages'.format(working_root))
        return '{}/.venv/Lib/site-packages'.format(working_root)
    else:
        raise Exception(
            '".venv" folder should be under working root', working_root
        )
