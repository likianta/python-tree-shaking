import os
import typing as t
from collections import defaultdict
from glob import glob

from lk_utils import fs

from .config import graphs_root
from .config import hash_path_to_uid
from .config import parse_config
from .graph import T as T0
from .patch import patch
from .path_scope import path_scope


class T(T0):
    TodoDirs = t.Set[str]  # a set of absolute paths
    TodoFiles = t.Set[str]  # a set of absolute paths
    Resources = t.Tuple[TodoFiles, TodoDirs]
    ResourcesMap = t.TypedDict('ResourcesMap', {
        'created_directories': TodoDirs,
        'linked_resources': Resources,
    })


def dump_tree(
    file_i: str,
    dir_o: str,
    sole_export: str = None,
    copyfiles: bool = False,
    dry_run: bool = False,
) -> None:
    """
    params:
        file_i (-i):
        dir_o (-o):
            an empty folder to store the tree. it can be an inexistent path.
        sole_export (-s):
            by default (=None), we export all modules in all of -
            `file_i:search_paths`, if you want to limit to only one root in -
            them, give it here.
            be noted the value must be one of `file_i:search_paths`.
        copyfiles (-c): if true, use copy instead of symlink.
        dry_run (-d):
    
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
    """
    root = fs.abspath(dir_o)
    # del dir_o
    
    cfg: T.Config = parse_config(file_i)
    
    if sole_export:
        sole_root = '{}/{}'.format(cfg['root'], sole_export)
        assert sole_root in cfg['search_paths'], (sole_export, sole_root)
    else:
        sole_root = None
    del sole_export
    files, dirs = _mount_resources(
        cfg, verbose=dry_run, limited_search_root=sole_root
    )
    
    tobe_created_dirs = _analyze_dirs_to_be_created(files, dirs)
    print(len(tobe_created_dirs), len(files), len(dirs), ':v1')
    
    if _check_if_first_time_export(root):
        _first_time_exports(
            root, tobe_created_dirs, (files, dirs),
            copyfiles, sole_root, dry_run
        )
    else:
        _incremental_updates(
            root, tobe_created_dirs, (files, dirs),
            copyfiles, sole_root, dry_run
        )
    fs.dump(
        {
            'created_directories': tobe_created_dirs,
            'linked_resources'   : (files, dirs),
        },
        fs.xpath(
            '_cache/dumped_resources_maps/{}.pkl'.format(
                x := hash_path_to_uid(root)
            )
        )
    )
    print('(cache) saved resources map', x, ':v')
    
    print('done', ':t')


def _first_time_exports(
    root: str,
    tobe_created_dirs: T.TodoDirs,
    tobe_linked_resources: T.Resources,
    copyfiles: bool,
    sole_root: t.Optional[str] = None,
    dry_run: bool = False,
) -> None:
    if not fs.exist(root) and not dry_run:
        fs.make_dir(root)
    
    roots = _get_common_roots(tobe_created_dirs, sole_root)
    for subroot, reldirs in roots.items():
        if sole_root:
            dir_prefix = root
        else:
            dir_prefix = '{}/{}'.format(root, fs.basename(subroot))
            if not dry_run:
                fs.make_dir(dir_prefix)
        for x in sorted(reldirs):
            d = '{}/{}'.format(dir_prefix, x)
            if dry_run:
                print(':i', '(dry run) make dir: {}'.format(
                    fs.relpath(d, root)
                ))
            else:
                fs.make_dir(d)
    
    files, dirs = tobe_linked_resources
    known_roots = tuple(sorted(roots.keys(), reverse=True))
    print(known_roots, ':vl')
    for f in files:
        r, s = _split_path(f, known_roots)
        i, o = f, (
            '{}/{}'.format(root, s) if sole_root else
            '{}/{}/{}'.format(root, fs.basename(r), s)
        )
        if dry_run:
            print(':i', '(dry run) {}: {}'.format(
                'copying file' if copyfiles else 'symlinking file',
                '<root>/{}'.format(o[len(root) + 1:])
            ))
        else:
            if copyfiles:
                fs.copy_file(i, o, overwrite=True)
            else:
                fs.make_link(i, o, overwrite=True)
    for d in sorted(dirs, reverse=True):
        #   note: be careful the `dirs` may contain "A/B" and "A/B/C" paths, -
        #   i.e. the cross-including paths. we need to process "A/B/C" first, -
        #   then "A/B". that's why we use "sorted(dirs, reverse=True)".
        #   TODO: maybe we can eliminate cross-including paths in -
        #       "_mount_resources()" stage.
        r, s = _split_path(d, known_roots)
        i, o = d, (
            '{}/{}'.format(root, s) if sole_root else
            '{}/{}/{}'.format(root, fs.basename(r), s)
        )
        if dry_run:
            print(':i', '(dry run) {}: {}'.format(
                'copying dir' if copyfiles else 'symlinking dir',
                '<root>/{}/'.format(o[len(root) + 1:])
            ))
        else:
            if copyfiles:
                fs.copy_tree(i, o, overwrite=True)
            else:
                fs.make_link(i, o, overwrite=True)


def _incremental_updates(
    root: str,
    tobe_created_dirs: T.TodoDirs,
    tobe_linked_resources: T.Resources,
    copyfiles: bool,
    sole_root: t.Optional[str] = None,
    dry_run: bool = False,
) -> None:
    assert fs.exist(x := fs.xpath(
        '_cache/dumped_resources_maps/{}.pkl'.format(hash_path_to_uid(root))
    )), x  # devnote: if AssertionError, check if file was dumped by another -
    #   venv provider.
    old_res_map: T.ResourcesMap = fs.load(x)
    new_res_map: T.ResourcesMap = {
        'created_directories': tobe_created_dirs,
        'linked_resources'   : tobe_linked_resources,
    }
    known_roots = tuple(sorted(
        _get_common_roots(tobe_created_dirs, sole_root).keys(),
        reverse=True
    ))
    for action, path_i in _analyze_incremental_updates(
        old_res_map, new_res_map
    ):
        a, b = _split_path(path_i, known_roots)
        path_o = (
            '{}/{}'.format(root, b) if sole_root else
            '{}/{}/{}'.format(root, fs.basename(a), b)
        )
        if dry_run:
            print(':i', '(dry run) {}: {}'.format(
                action, '<root>/{}'.format(path_o[len(root) + 1:])
            ))
        else:
            if (
                action in ('drop_dir', 'del_file', 'del_dir') and
                not fs.exist(path_o)
            ):
                print(':v6', 'already removed?', action, path_o)
                continue
            match action:
                case 'make_dir':
                    fs.make_dir(path_o)
                case 'drop_dir':
                    fs.remove_tree(path_o)
                case 'add_file':
                    if copyfiles:
                        fs.copy_file(path_i, path_o, overwrite=True)
                    else:
                        fs.make_link(path_i, path_o, overwrite=True)
                case 'del_file':
                    if copyfiles:
                        fs.remove_file(path_o)
                    else:
                        os.unlink(path_o)
                case 'add_dir':
                    if copyfiles:
                        fs.copy_tree(path_i, path_o, overwrite=True)
                    else:
                        fs.make_link(path_i, path_o, overwrite=True)
                case 'del_dir':
                    if copyfiles:
                        fs.remove_tree(path_o)
                    else:
                        os.unlink(path_o)


# -----------------------------------------------------------------------------

def _analyze_dirs_to_be_created(
    files: T.TodoFiles, dirs: T.TodoDirs
) -> t.Set[str]:
    """
    returns: a set of dir paths, the paths are grind down to each level of -
    directories.
    note: the returned value is a set of "source" paths, not "target" paths.
    """
    out = set()
    for x in (files | dirs):
        out.update(_grind_down_dirpath(fs.parent(x)))
    # remove existing dirs that out of search roots
    search_roots = _get_search_roots(shrink=True)
    for d in tuple(out):
        if any(x.startswith(d + '/') for x in search_roots):
            print('pick out high-priority existing dir', d, ':vi')
            # assert fs.exist(d)
            out.remove(d)
    return out


def _analyze_incremental_updates(
    old_resources_map: T.ResourcesMap, new_resources_map: T.ResourcesMap
) -> t.Iterator[t.Tuple[str, str]]:
    tree0 = old_resources_map['created_directories']
    tree1 = new_resources_map['created_directories']
    for d in sorted(tree1 - tree0):
        yield 'make_dir', d
    for d in sorted(tree0 - tree1, reverse=True):
        yield 'drop_dir', d
    
    # f2f: "file-to-file"
    f2f0 = old_resources_map['linked_resources'][0]
    f2f1 = new_resources_map['linked_resources'][0]
    for f in f2f1 - f2f0:
        yield 'add_file', f
    for f in f2f0 - f2f1:
        yield 'del_file', f
        
    # d2d: "dir-to-dir"
    d2d0 = old_resources_map['linked_resources'][1]
    d2d1 = new_resources_map['linked_resources'][1]
    for d in sorted(d2d1 - d2d0, reverse=True):
        yield 'add_dir', d
    for d in sorted(d2d0 - d2d1, reverse=True):
        yield 'del_dir', d


def _check_if_first_time_export(root: str) -> bool:
    if not fs.exist(root):
        return True
    if not fs.find_dir_names(root):
        return True
    return False


# TODO or DELETE
def _init_target_tree(
    root: str, tobe_created_dirs: T.TodoDirs, dry_run: bool = False
) -> None:
    roots = _get_common_roots(tobe_created_dirs)
    for subroot, reldirs in roots.items():
        dir_prefix = '{}/{}'.format(root, fs.basename(subroot))
        if not dry_run:
            fs.make_dir(dir_prefix)
        for x in sorted(reldirs):
            d = '{}/{}'.format(dir_prefix, x)
            if dry_run:
                print(':i', '(dry run) make dir: {}'.format(
                    fs.relpath(d, root)
                ))
            else:
                fs.make_dir(d)


def _mount_resources(
    config: T.Config,
    verbose: bool = False,
    limited_search_root: t.Optional[str] = None
) -> t.Tuple[T.TodoFiles, T.TodoDirs]:
    """
    limited_search_root: an absolute path.
    """
    files: T.TodoFiles = set()
    dirs: T.TodoDirs = set()
    patched_modules = set()
    
    def resolve_patched_path(relpath: str) -> str:
        """
        returns: a must-exist abspath or empty string.
        """
        if relpath.endswith('?'):
            nullable = True
            relpath = relpath[:-1]
        else:
            nullable = False
        
        if '*' in relpath:
            candidates = glob('{}/{}'.format(base_dir, relpath))
            if len(candidates) == 0 and nullable:
                return ''
            elif len(candidates) == 1:
                if fs.exist(candidates[0]):
                    return candidates[0].replace('\\', '/')
            else:
                raise Exception(relpath, candidates, nullable)
        else:
            if fs.exist(x := '{}/{}'.format(base_dir, relpath)):
                return x
        
        if nullable:
            return ''
        else:
            raise Exception(top_name, relpath)
    
    for graph_id in config['entries'].values():
        graph_file = '{}/{}.yaml'.format(graphs_root, graph_id)
        graph: T.DumpedModuleGraph = fs.load(graph_file)
        
        limited_uid = None
        if limited_search_root:
            for uid, root in graph['source_roots'].items():
                if root == limited_search_root:
                    limited_uid = uid
                    break
        
        for module_name, relpath in graph['modules'].items():
            uid, relpath = relpath.split('/', 1)
            uid = uid[1:-1]
            if limited_uid and uid != limited_uid:
                continue
            abspath = '{}/{}'.format(graph['source_roots'][uid], relpath)
            files.add(abspath)
            
            # patch: fill extra files
            top_name = module_name.split('.', 1)[0]
            if top_name in patch:
                if top_name not in patched_modules:
                    patched_modules.add(top_name)
                    # assert relpath.startswith(top)
                    base_dir = '{}/{}'.format(
                        graph['source_roots'][uid], top_name
                    )
                    for relpath1 in patch[top_name]['files']:
                        if abspath1 := resolve_patched_path(relpath1):
                            if abspath1.endswith('/'):
                                dirs.add(abspath1)
                            else:
                                files.add(abspath1)
    
    for f in tuple(files):
        # since `len(dirs)` is usually small, we can simply for-loop it -
        # without worrying about efficiency.
        for d in dirs:
            if f.startswith(d + '/'):
                if verbose:
                    print(
                        'remove file "{}" that has been covered by "{}"'
                        .format(f, d), ':v7i'
                    )
                files.remove(f)
    
    return files, dirs


# -----------------------------------------------------------------------------
# neutral

def _get_common_roots(
    absdirs: t.Iterable[str], single_root: str = None
) -> t.Dict[str, t.Set[str]]:
    """
    returns: {known_root: {relpath, ...}, ...}
        note that all `return:keys` are existing dirs. but their sequence is -
        not guaranteed to be ordered. i.e. the returned dict cannot be -
        definitely treated as an "ordered" dict, though in most cases it is.
    """
    if single_root:
        r = single_root + '/'
        x = set()
        for d in absdirs:
            if d.startswith(r):
                x.add(d.removeprefix(r))
            else:
                assert r.startswith(d + '/')
        return {single_root: x}
    
    search_roots = _get_search_roots(shrink=True)
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
    return out


def _get_search_roots(shrink: bool = False) -> t.Tuple[str, ...]:
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
    if shrink:
        buried_search_roots = set()
        for root in search_roots:
            for other in search_roots:
                if (
                    other != root and
                    other not in buried_search_roots and
                    other.startswith(root + '/')
                ):
                    buried_search_roots.add(other)
        if buried_search_roots:
            print('shrink search roots count from {} to {}'.format(
                len(search_roots), len(search_roots - buried_search_roots)
            ))
            search_roots = search_roots - buried_search_roots
    return tuple(sorted(search_roots, reverse=True))


def _grind_down_dirpath(path: str) -> t.Iterator[str]:
    a, *b = path.split('/')
    yield a
    for c in b:
        a += '/' + c
        yield a


def _split_path(path: str, known_roots: t.Sequence[str]) -> t.Tuple[str, str]:
    for root in known_roots:
        if path.startswith(root + '/'):
            return root, path.removeprefix(root + '/')
    raise Exception('path should be under one of the search roots', path)
