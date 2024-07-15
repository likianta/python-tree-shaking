import os
import typing as t
from collections import defaultdict

from lk_utils import fs

from .config_parser import parse_config
from .path_scope import path_scope


class T:
    Config = t.TypedDict('Config', {
        'cwd'          : str,
        'search_paths' : t.List[str],
        'module_graphs': t.List[str],
        'spec_files'   : t.List[str],
    })


def make_tree(file_i: str, dir_o: str, copyfiles: bool = False) -> None:
    """
    params:
        file_i:
            data for example:
                search_paths:
                    - .
                    - chore/site_packages
                module_graphs:
                    # the name must be existed in `data/module_graphs/<name>
                    # .yaml`
                    # see generation at `tree_shaking/__main__.py:dump_module
                    # _graph`
                    - depsland
                    - streamlit
                    - toga-winforms
                spec_files:
                    # path could be relative or absolute.
                    # make sure path must be under one of the search paths.
                    - chore/site_packages/streamlit/__init__.py
                    - chore/site_packages/streamlit/__main__.py
                    # trick: add '/' to the end of the path to indicate a
                    # directory type.
                    - depsland/chore/
                    - depsland/__init__.py
                    - depsland/__main__.py
        dir_o: an empty folder to store the tree. it can be an inexistent path.
    """
    dir_o = fs.abspath(dir_o)
    
    cfg: T.Config = parse_config(file_i)
    
    files = set()  # a set of absolute paths
    dirs = set()  # a set of absolute paths
    for graph_file in cfg['module_graphs']:
        datum = fs.load(graph_file)
        files.update(datum.values())
    for path, isdir in cfg['spec_files']:
        if isdir:
            dirs.add(path)
        else:
            files.add(path)
    
    all_abs_dirs = set()
    for f in files:
        all_abs_dirs.add(fs.parent(f))
    for d in dirs:
        all_abs_dirs.add(d)
    print(len(all_abs_dirs), len(files), ':v2')
    
    roots = _get_common_roots(all_abs_dirs)
    for root, reldirs in roots.items():
        print(root, len(reldirs), ':i2')
        init_target_tree('{}/{}'.format(dir_o, fs.basename(root)), reldirs)
    
    known_roots = tuple(sorted(roots.keys(), reverse=True))
    for f in files:
        i = f
        r, s = _split_path(f, known_roots)
        o = '{}/{}/{}'.format(dir_o, fs.basename(r), s)
        if copyfiles:
            fs.copy_file(i, o)
        else:
            fs.make_link(i, o)
    for d in dirs:
        i = d
        r, s = _split_path(d, known_roots)
        o = '{}/{}'.format(dir_o, fs.basename(r), s)
        if copyfiles:
            fs.copy_tree(i, o, True)
        else:
            fs.make_link(i, o, True)
    
    # TODO
    # for k, v in data.get('replace', {}).items():
    #     if isinstance(v, str):
    #         v = (v,)
    #     src = k
    #     for dst in v:
    #         if dst.endswith('/'):
    #             if copyfiles:
    #                 fs.copy_tree(src, dst, True)
    #             else:
    #                 fs.make_link(src, dst, True)
    #         else:
    #             if copyfiles:
    #                 fs.copy_file(src, dst, True)
    #             else:
    #                 fs.make_link(src, dst, True)
    
    print('done', ':t')


def init_target_tree(root: str, reldirs: t.Iterable[str]) -> None:
    print('init making tree', root, ':p')
    paths_to_be_created = {root}
    paths_to_be_created.update((f'{root}/{x}' for x in reldirs))
    paths_to_be_created = sorted(paths_to_be_created)
    # print(':vl', paths_to_be_created)
    for p in paths_to_be_created:
        os.makedirs(p, exist_ok=True)


def _get_common_roots(absdirs: t.Iterable[str]) -> t.Dict[str, t.Set[str]]:
    search_roots = set()
    for path, isdir in path_scope.module_2_path.values():
        # e.g.
        #   isdir = True:
        #       '<project>/venv/site-packages/numpy'
        #       -> '<project>/venv/site-packages'
        #   isdir = False:
        #       '<project>/venv/site-packages/typing_extensions.py'
        #       -> '<project>/venv/site-packages'
        search_roots.add(fs.parent(path))
    search_roots = tuple(sorted(search_roots, reverse=True))
    
    out = defaultdict(set)  # {root: {reldir, ...}, ...}
    for d in absdirs:
        if d in search_roots:
            continue
        for root in search_roots:
            if d.startswith(root + '/'):
                out[root].add(d.removeprefix(root + '/'))
                break
        else:
            raise Exception('path should be under one of the search roots', d)
    print(':l', search_roots, tuple(out.keys()))
    # print(':vl', out)
    return out


def _split_path(path: str, known_roots: t.Sequence[str]) -> t.Tuple[str, str]:
    for root in known_roots:
        if path.startswith(root + '/'):
            return root, path.removeprefix(root + '/')
    raise Exception('path should be under one of the search roots', path)
