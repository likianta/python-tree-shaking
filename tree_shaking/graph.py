import hashlib
import typing as t
from textwrap import dedent

from lk_utils import fs

from .config import T as T0
from .config import graphs_root
from .config import parse_config
from .finder import Finder


class T(T0):
    DumpedModuleGraph = t.TypedDict('DumpedModuleGraph', {
        'source_roots': t.Dict[str, str],
        'modules'     : t.Dict[str, str],
    })
    '''
        {
            'source_roots': {uid: root_path, ...},
                uid: 8-char md5 hash of root_path.
                root_path: absolute dirpath.
            'modules': {module: short_path, ...}
                short_path: `<uid>/path/to/module.py`
        }
    '''


# FIXME
def build_module_graph(
    script: T.AnyScriptPath, graph_id: T.GraphId, sort: bool = True
) -> str:
    file_i = fs.abspath(script)
    file_o = '{}/{}.yaml'.format(graphs_root, graph_id)
    
    finder = Finder(())
    result = dict(finder.get_all_imports(file_i))
    if sort:
        result = dict(sorted(result.items()))
    # for module in result:
    #     print(':i', module)
    fs.dump(result, file_o)
    
    print(
        ':v2t', 'dumped {} items. see result at "{}"'
        .format(len(result), file_o)
    )
    return file_o


def build_module_graphs(config_file: T.AnyPath) -> None:
    cfg = parse_config(config_file, _save=True)
    finder = Finder(cfg['ignores'])
    for p, n in cfg['entries'].items():  # 'p': path, 'n': name
        print(':v2', p, n)
        # build_module_graph(p, n)
        file_i = fs.abspath(p)
        file_o = '{}/{}.yaml'.format(graphs_root, n)
        result = dict(finder.get_all_imports(file_i))
        # prettify result data for reader friendly
        result = dict(sorted(result.items()))
        result = _reformat_paths(result, cfg)
        # add refs info to result
        # refs = finder.references
        # result['references'] = {k: sorted(refs[k]) for k in sorted(refs.keys())}
        fs.dump(result, file_o)
        print(
            ':v2ti',
            dedent(
                '''
                entry at {}:
                    graph id is {}.
                    found {} source roots,
                    dumped {} items,
                    see result at "{}".
                '''.format(
                    p,
                    n,
                    len(result['source_roots']),
                    len(result['modules']),
                    '<tree_shaking>/<graphs_root>/{}'.format(
                        fs.relpath(file_o, graphs_root)
                    )
                )
            )
        )


def _reformat_paths(modules: t.Dict[str, str], config: T.Config) -> dict:
    out: T.DumpedModuleGraph = {'source_roots': {}, 'modules': {}}
    
    def hash_content(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()[::4]  # length: 8
    
    temp = out['source_roots']
    for root in sorted(config['search_paths'], reverse=True):
        temp[hash_content(root)] = root
    _frozen_source_roots = tuple((k, v + '/') for k, v in temp.items())
    used_source_roots = set()
    
    def reformat_path(path: str) -> str:
        for uid, root in _frozen_source_roots:
            if path.startswith(root):
                used_source_roots.add(uid)
                return '<{}>/{}'.format(uid, path[len(root):])
        else:
            print(':lv4', _frozen_source_roots, path)
            raise Exception(path)
    
    temp = out['modules']
    for m, p in modules.items():
        temp[m] = reformat_path(p)
    
    # remove unused source roots
    assert 0 < len(used_source_roots) <= len(out['source_roots'])
    if len(used_source_roots) < len(out['source_roots']):
        for k in tuple(out['source_roots'].keys()):
            if k not in used_source_roots:
                out['source_roots'].pop(k)
    
    return t.cast(dict, out)
