import os
import typing as t
from collections import defaultdict

from lk_utils import fs

from .config import parse_config
from .graph import T
from .patch import patch
from .path_scope import path_scope


def dump_tree(
    file_i: str,
    dir_o: str,
    copyfiles: bool = False,
    incremental_updates: bool = False
) -> t.Tuple[t.Set[str], t.Set[str]]:
    """
    params:
        file_i (-i):
        dir_o (-o):
            an empty folder to store the tree. it can be an inexistent path.
        copyfiles (-c): if true, use copy instead of symlink.
        incremental_updates (-u):
    
    file content for example:
        search_paths:
            - .
            - chore/site_packages
        module_graphs:
            # the name must be existed in `data/module_graphs/<name>.yaml`
            # see generation at `tree_shaking/__main__.py:dump_module_graph`
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
    """
    dir_o = fs.abspath(dir_o)
    cfg: T.Config = parse_config(file_i)
    
    files = set()  # a set of absolute paths
    dirs = set()  # a set of absolute paths
    patched_modules = set()
    
    for graph_file in cfg['export']['module_graphs']:
        graph: T.DumpedModuleGraph = fs.load(graph_file)
        for module_name, relpath in graph['modules'].items():
            uid, relpath = relpath.split('/', 1)
            uid = uid[1:-1]
            abspath = '{}/{}'.format(graph['source_roots'][uid], relpath)
            files.add(abspath)
            
            top_name = module_name.split('.', 1)[0]
            if top_name in patch:
                if top_name not in patched_modules:
                    patched_modules.add(top_name)
                    # assert relpath.startswith(top)
                    base_dir = '{}/{}'.format(
                        graph['source_roots'][uid], top_name
                    )
                    for relpath1 in patch[top_name]['files']:
                        # relpath1: str | [str, ...]
                        if isinstance(relpath1, str):
                            xlist = (relpath1,)
                        else:
                            xlist = relpath1
                        for x0 in xlist:
                            x1 = fs.normpath('{}/{}'.format(base_dir, x0))
                            if fs.exist(x1):
                                abspath1 = x1
                                if x0.endswith('/'):
                                    dirs.add(abspath1)
                                else:
                                    files.add(abspath1)
                                break
                        else:
                            raise Exception(top_name, relpath1)
    for path, isdir in cfg['export']['spec_files']:
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
    
    created_files, created_dirs = set(), set()
    
    known_roots = tuple(sorted(roots.keys(), reverse=True))
    for f in files:
        r, s = _split_path(f, known_roots)
        i, o = f, '{}/{}/{}'.format(dir_o, fs.basename(r), s)
        if copyfiles:
            fs.copy_file(i, o, overwrite=True)
        else:
            fs.make_link(i, o, overwrite=None if incremental_updates else True)
        created_files.add(o)
    for d in sorted(dirs, reverse=True):
        r, s = _split_path(d, known_roots)
        i, o = d, '{}/{}/{}'.format(dir_o, fs.basename(r), s)
        if copyfiles:
            fs.copy_tree(i, o, overwrite=True)
        else:
            fs.make_link(i, o, overwrite=None if incremental_updates else True)
        created_dirs.add(o)
    
    print('done', ':t')
    return created_files, created_dirs


def refresh_tree(file_i: str, dir_o: str, copyfiles: bool = False) -> None:
    assert fs.exists(dir_o)
    created_files, created_dirs = map(
        frozenset, dump_tree(file_i, dir_o, copyfiles)
    )
    
    def get_tiled_created_dirs() -> t.Set[str]:
        def add_dirpath(path: str):
            segs = path.split('/')
            x = ''
            for s in segs:
                x += s + '/'
                out.add(x)
        
        out = set()
        for f in created_files:
            add_dirpath(f.rsplit('/', 1)[0])
        for d in created_dirs:
            add_dirpath(d)
        return out
    
    tiled_created_dirs = frozenset(get_tiled_created_dirs())
    print(len(created_files), len(created_dirs), len(tiled_created_dirs))
    
    def collect_irrelevant_paths(dir, _check_files: bool = True):
        for d in fs.find_dirs(dir):
            if d.path + '/' in tiled_created_dirs:
                yield from collect_irrelevant_paths(
                    d.path, _check_files=d.path not in created_dirs
                )
            else:
                yield d.path
        if _check_files:
            for f in fs.find_files(dir):
                if f.path not in created_files:
                    yield f.path
    
    irrelevant_paths = sorted(collect_irrelevant_paths(dir_o))
    if irrelevant_paths:
        print(len(irrelevant_paths))
        for p in irrelevant_paths:
            print(':v8i', 'remove', p)
            pass


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
    # print(':l', search_roots, tuple(out.keys()))
    # print(':vl', out)
    return out


def _split_path(path: str, known_roots: t.Sequence[str]) -> t.Tuple[str, str]:
    for root in known_roots:
        if path.startswith(root + '/'):
            return root, path.removeprefix(root + '/')
    raise Exception('path should be under one of the search roots', path)
