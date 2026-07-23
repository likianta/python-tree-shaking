import sys
import typing as tp
from glob import glob

import neoprint as np
from lk_utils import fs
from lk_utils import slice

from .cache import cache_maker
from .config import parse_config
from .dynamic_analyzer import grab_global_modules
from .graph import T as T0
from .patch import patch


class T:
    AbsDirPath = AbsFilePath = str
    AnyDirPath = AnyFilePath = str
    Config = T0.Config
    RelDirPath = RelPath = str

    Records = tp.TypedDict(
        'Records',
        {
            'created_directories': tp.FrozenSet[RelDirPath],
            'resource_records': tp.Dict[RelPath, int],
        },
    )
    TodoDirs = tp.Union[tp.Set[AbsDirPath], tp.FrozenSet[AbsDirPath]]
    TodoFiles = tp.Union[tp.Set[AbsFilePath], tp.FrozenSet[AbsFilePath]]


def dump_tree_from_config_file(
    file_i: T.AnyFilePath,
    dir_o: T.AnyDirPath = '',
    single_source_entry: T.AnyDirPath = '',
    dry_run: bool = False,
):
    cfg: T.Config = parse_config(
        file_i, export={'source': single_source_entry, 'target': dir_o}
    )
    dump_tree_from_config(cfg, dry_run)


def dump_tree_from_config(config: T.Config, dry_run: bool = False) -> None:
    source = config['export']['source']  # an optional absolute path
    target = config['export']['target']  # a valid abspath
    print(source, target, ':nv2l')
    assert target

    if source:
        files, dirs = _mount_resources(
            config, verbose=dry_run, limited_search_root=source
        )
        _dump_single_source(
            root_i=source,
            root_o=target,
            files_i=files,
            dirs_i=dirs,
            dry_run=dry_run,
        )
    else:
        """
        memo:
            is_single_source:
                it affects direct folder structure of `dir_o`.
                for example:
                    if is_single_source:
                        roots_i = ('/aaa',)  # assert len(roots_i) == 1
                        dir_o = '/bbb'
                        tobe_linked_resources = (
                            {'/aaa/ccc.py',}, {'/aaa/ddd',}
                        )
                        tree_result:
                            bbb
                            |= ddd
                            |- ccc.py
                    else:
                        roots_i = ('/aaa', '/eee', '/fff')
                        dir_o = '/bbb'
                        tobe_linked_resources = (
                            {'/aaa/ccc.py',}, {'/aaa/ddd',}
                        )
                        tree_result:
                            bbb
                            |= aaa
                                |= ddd
                                |- ccc.py
                            |= eee
                            |= fff
        """
        raise NotImplementedError(
            'multi-roots mode is not implemented', config['search_paths']
        )


def dump_tree_from_modules(dir_o: T.AnyDirPath, dry_run: bool = False) -> None:
    assert sys.exec_prefix.endswith('.venv')
    root_i = fs.normpath('{}/Lib/site-packages'.format(sys.exec_prefix))
    root_o = fs.abspath(dir_o)

    mods = tuple(grab_global_modules())
    _dump_single_source(
        root_i=root_i,
        root_o=root_o,
        files_i=(x for _, x, d in mods if not d),
        dirs_i=(x for _, x, d in mods if d),
        dry_run=dry_run,
    )


# ------------------------------------------------------------------------------


def _dump_single_source(
    root_i: T.AbsDirPath,
    root_o: T.AbsDirPath,
    files_i: tp.Iterable[T.AbsFilePath],
    dirs_i: tp.Iterable[T.AbsDirPath] = (),
    # copy_files: bool = False,
    dry_run: bool = False,
) -> None:
    with np.scope():
        todo_relfiles = set()
        for f in files_i:
            if f.startswith(root_i + '/'):
                todo_relfiles.add(f.removeprefix(root_i + '/'))
            else:
                print('ignore file resource out of root_i', f, ':i2v5')
        assert todo_relfiles

        todo_reldirs = set()
        for d in dirs_i:
            if d.startswith(root_i + '/'):
                todo_reldirs.add(fs.relpath(d, root_i))
            else:
                print('ignore dir resource out of root_i', d, ':i2v5')

    tobe_created_reldirs = set()
    for p in todo_relfiles | todo_reldirs:
        if '/' in p:
            tobe_created_reldirs.update(
                _grind_down_dirpath(slice(p).cut().rfind('/').cut().out())
            )
    print(
        len(todo_relfiles), len(todo_reldirs), len(tobe_created_reldirs), ':n'
    )

    if x := cache_maker.get_cache(
        '{};{}'.format(root_i, root_o), 'last_dumped_records', check=False
    ):
        print('incremental update')
        records0: T.Records = x[root_i]

        tree0 = records0['created_directories']
        tree1 = tobe_created_reldirs
        for d in sorted(tree1 - tree0):
            # make directory
            if dry_run:
                print(':iv4', '[dry run] make dir: {}'.format(d))
            else:
                o = '{}/{}'.format(root_o, d)
                fs.make_dir(o)
        for d in sorted(tree0 - tree1):
            # delete directory
            if dry_run:
                print(':iv8', '[dry run] drop dir: {}'.format(d))
            else:
                o = '{}/{}'.format(root_o, d)
                fs.remove_tree(o)

        res0 = records0['resource_records']
        res1 = {}
        for r in todo_relfiles:
            res1[r] = tp.cast(int, fs.mtime('{}/{}'.format(root_i, r)))
        for r in sorted(todo_reldirs, reverse=True):
            #   note: be careful the `todo_reldirs` may contain "A/B" and
            #   "A/B/C" paths -- i.e. the cross-including paths. we need to
            #   process "A/B/C" first, then "A/B". that's why we use
            #   `sorted(todo_reldirs, reverse=True)`.
            #   TODO: maybe we can eliminate cross-including paths in
            #   `_mount_resources()` stage.
            res1[r] = tp.cast(
                int, fs.mtime('{}/{}'.format(root_i, r), recursive=True)
            )
        with np.scope():
            for r1 in res1:
                if r1 not in res0:
                    # add resource
                    if dry_run:
                        print(':i2v4', '[dry run] add res: {}'.format(r1))
                    else:
                        o = '{}/{}'.format(root_o, r1)
                        fs.make_link('{}/{}'.format(root_i, r1), o, True)
                else:
                    t1 = res1[r1]
                    t0 = res0[r1]
                    if t1 != t0:
                        # update resource
                        if dry_run:
                            print(
                                ':i2v6', '[dry run] update res: {}'.format(r1)
                            )
                        else:
                            o = '{}/{}'.format(root_o, r1)
                            fs.make_link('{}/{}'.format(root_i, r1), o, True)
            for r0 in res0:
                if r0 not in res1:
                    # delete resource
                    if dry_run:
                        print(':i2v8', '[dry run] drop res: {}'.format(r0))
                    else:
                        o = '{}/{}'.format(root_o, r0)
                        if fs.exist(o):
                            fs.remove(o)
                        else:
                            print('already removed?', r0)
    else:
        print('first time dump')

        tree1 = tobe_created_reldirs
        for d in sorted(tree1):
            # make directory
            if dry_run:
                print(':iv4', '[dry run] make dir: {}'.format(d))
            else:
                o = '{}/{}'.format(root_o, d)
                fs.make_dir(o)

        res1 = {}
        for r in todo_relfiles:
            res1[r] = tp.cast(int, fs.mtime('{}/{}'.format(root_i, r)))
        for r in todo_reldirs:
            res1[r] = tp.cast(
                int, fs.mtime('{}/{}'.format(root_i, r), recursive=True)
            )
        for r in res1:
            # add resource
            if dry_run:
                print(':i2v4', '[dry run] add res: {}'.format(r))
            else:
                o = '{}/{}'.format(root_o, r)
                fs.make_link('{}/{}'.format(root_i, r), o, False)

    records1: T.Records = {
        'created_directories': frozenset(tree1),
        'resource_records': res1,
    }
    cache_maker.save_cache(
        '{};{}'.format(root_i, root_o),
        'last_dumped_records',
        records1,
        check=False,
    )
    print('export done', ':ptv4')


def _grind_down_dirpath(path: str) -> tp.Iterator[str]:
    a, *b = path.split('/')
    yield a
    for c in b:
        a += '/' + c
        yield a


def _mount_resources(
    config: T.Config,
    verbose: bool = False,
    limited_search_root: tp.Optional[T.AbsDirPath] = None,
) -> tp.Tuple[T.TodoFiles, T.TodoDirs]:
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
                # currently we don't allow multiple candidates. i think it's
                # fine to unlock this behavior. let me review this case later.
                raise Exception(relpath, candidates, nullable)
        else:
            if fs.exist(x := '{}/{}'.format(base_dir, relpath)):
                return x

        if nullable:
            return ''
        else:
            raise Exception(top_name, relpath)

    for entry_path in config['entries']:
        graph: T.DumpedModuleGraph = cache_maker.get_cache(  # type: ignore
            entry_path, 'module_graphs'
        )
        assert graph

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
                        'remove file "{}" that has been covered by "{}"'.format(
                            f, d
                        ),
                        ':v7i',
                    )
                files.remove(f)

    return files, dirs
