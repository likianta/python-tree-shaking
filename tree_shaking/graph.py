import typing as tp

from lk_utils import fs
from lk_utils import textwrap as tw
from lk_utils import uuid
from neoprint import format

from .cache import cache_maker
from .cache import cache_root
from .config import T as T0
from .config import parse_config
from .finder import Finder


class T(T0):
    DumpedModuleGraph = tp.TypedDict(
        'DumpedModuleGraph',
        {'source_roots': tp.Dict[str, str], 'modules': tp.Dict[str, str]},
    )
    #   {
    #       'source_roots': {uid: root_path, ...},
    #           uid: 8-char md5 hash of root_path.
    #           root_path: absolute dirpath.
    #       'modules': {module: short_path, ...}
    #           short_path: `<uid>/path/to/module.py`
    #   }


def build_module_graphs(config_file: str) -> None:
    cfg = parse_config(config_file)
    finder = Finder(cfg['ignores'])

    for entry_path in cfg['entries']:
        print('entry at {}'.format(fs.relpath(entry_path, cfg['root'])), ':i')
        if not cache_maker.is_cached(entry_path, 'module_graphs'):
            file_i = entry_path
            result = finder.get_all_imports(file_i)
            result = _reformat_paths(sorted(result.items()), cfg)
            # add refs info to result
            # refs = finder.references
            # result['references'] = {
            #   k: sorted(refs[k]) for k in sorted(refs.keys())
            # }
            file_o = cache_maker.save_cache(entry_path, 'module_graphs', result)

            print(
                ':v2ti',
                tw.wrap(
                    """
                    entry: {}
                    source_roots: 
                        {}
                    dumped_modules_count: {}
                    cache: {} ({})
                    """.format(
                        entry_path,
                        tw.join(
                            (
                                '{}: {}'.format(k, v)
                                for k, v in result['source_roots'].items()
                            ),
                            indent=24,
                        ),
                        len(result['modules']),
                        '<tree_shaking_cache>/{}'.format(
                            fs.relpath(file_o, cache_root)
                        ),
                        fs.filesize(file_o, str),
                    ),
                    indent=4,
                    lstrip=False,
                ),
            )


def _reformat_paths(
    modules: tp.Iterable[tp.Tuple[str, str]], config: T.Config
) -> T.DumpedModuleGraph:
    out: T.DumpedModuleGraph = {'source_roots': {}, 'modules': {}}

    def path_to_short_id(path: str) -> str:
        return uuid(path)[::4]

    temp = out['source_roots']
    for root in sorted(config['search_paths'], reverse=True):
        temp[path_to_short_id(root)] = root
    _frozen_source_roots = tuple((k, v + '/') for k, v in temp.items())
    used_source_roots = set()

    def reformat_path(path: str) -> str:
        for uid, root in _frozen_source_roots:
            if path.startswith(root):
                used_source_roots.add(uid)
                return '<{}>/{}'.format(uid, path[len(root) :])
        else:
            raise Exception(format(':nlv8', _frozen_source_roots, path))

    temp = out['modules']
    for m, p in modules:
        temp[m] = reformat_path(p)

    # remove unused source roots
    assert 0 < len(used_source_roots) <= len(out['source_roots'])
    if len(used_source_roots) < len(out['source_roots']):
        for k in tuple(out['source_roots'].keys()):
            if k not in used_source_roots:
                out['source_roots'].pop(k)
    return out


# def _save_graph_alias(config: T.Config1) -> None:
#     map_ = fs.load('{}/module_graphs_alias.yaml'.format(cache_root))
#     if config['root'] in map_:
#         if frozenset(config['entries'].values()) == frozenset(
#             map_[config['root']].values()
#         ):
#             return
#     map_[config['root']] = {
#         # k.replace(config['root'], '<root>'): v
#         fs.relpath(k, config['root']): v
#         for k, v in config['entries'].items()
#     }
#     fs.dump(
#         map_, '{}/module_graphs_alias.yaml'.format(cache_root), sort_keys=True
#     )
