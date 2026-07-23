import sys
import typing as tp
from collections import defaultdict
from glob import glob

import neoprint as np
from lk_utils import fs

from .cache import cache_maker
from .config import parse_config
from .dynamic_analyzer import grab_global_modules
from .graph import T as T0
from .patch import patch


class T:
    AbsDirPath = AbsFilePath = str
    AnyDirPath = AnyFilePath = str
    Config = T0.Config
    DryRun = tp.Union[bool, tp.Literal[0, 1, 2]]
    #   0: no dry run
    #   1: no actual file operations, only prints.
    #   2: same as 1, but disable incremental update
    RelDirPath = RelFilePath = RelPath = str

    Records = tp.TypedDict(
        'Records',
        {
            'created_directories': tp.FrozenSet[RelDirPath],
            'resource_records': tp.Dict[RelPath, int],
        },
    )
    TodoDirs = tp.Union[tp.Set[RelDirPath]]
    TodoFiles = tp.Union[tp.Set[RelFilePath]]


def dump_tree_from_config_file(
    file_i: T.AnyFilePath,
    dir_o: T.AnyDirPath = '',
    single_source_entry: T.AnyDirPath = '',
    dry_run: T.DryRun = False,
    **kwargs,
):
    cfg: T.Config = parse_config(
        file_i, export={'source': single_source_entry, 'target': dir_o}
    )
    dump_tree_from_config(cfg, dry_run, **kwargs)


def dump_tree_from_config(
    config: T.Config, dry_run: T.DryRun = False, **kwargs
) -> None:
    source = config['export']['source']  # an optional absolute path
    target = config['export']['target']  # a valid abspath
    print(source, target, ':nv2l')
    assert target

    if source:
        files, dirs = _mount_resources(
            config, verbose=bool(dry_run), limited_search_root=source
        )
        print(len(files), len(dirs), ':n')
        _dump_single_source(
            root_i=source,
            root_o=target,
            files_i=files,
            dirs_i=dirs,
            dry_run=dry_run,
            **kwargs,
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


def dump_tree_from_modules(
    dir_o: T.AnyDirPath, dry_run: T.DryRun = False, **kwargs
) -> None:
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
        **kwargs,
    )


# ------------------------------------------------------------------------------


def _dump_single_source(
    root_i: T.AbsDirPath,
    root_o: T.AbsDirPath,
    files_i: tp.Iterable[T.AbsFilePath],
    dirs_i: tp.Iterable[T.AbsDirPath] = (),
    # copy_files: bool = False,
    dry_run: T.DryRun = False,
    cache_reference_file: str = '',  # TODO or DELETE
) -> None:
    if not cache_reference_file:
        # cache_reference_file = '{};{}'.format(root_i, root_o)
        raise Exception('please provide a cache_reference_file')

    with np.scope():
        todo_relfiles = set()
        for f in files_i:
            if f.startswith(root_i + '/'):
                if fs.exist(f):
                    todo_relfiles.add(f.removeprefix(root_i + '/'))
                else:
                    print(':v6', 'file not exists', f)
            elif dry_run:
                print('ignore file resource out of root_i', f, ':i2v5')
        assert todo_relfiles

        todo_reldirs = set()
        for d in dirs_i:
            if d.startswith(root_i + '/'):
                if fs.exist(d):
                    todo_reldirs.add(d.removeprefix(root_i + '/'))
                else:
                    print(':v6', 'dir not exists', d)
            elif dry_run:
                print('ignore dir resource out of root_i', d, ':i2v5')

    tobe_created_reldirs = set()
    for p in todo_relfiles | todo_reldirs:
        if '/' in p:
            tobe_created_reldirs.update(
                _grind_down_dirpath(p.rsplit('/', 1)[0])
            )
    print(
        len(todo_relfiles), len(todo_reldirs), len(tobe_created_reldirs), ':n'
    )

    def is_first_time_dump() -> bool:
        if dry_run == 2:
            return True
        elif fs.exist(root_o):
            for _ in fs.find_dirs(root_o):
                return False
            return True
        else:
            return True

    if is_first_time_dump():
        print('first time dump', ':v2')

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
        for r in sorted(res1, reverse=True):
            # add resource
            if dry_run:
                print(':i2v4', '[dry run] add res: {}'.format(r))
            else:
                i = '{}/{}'.format(root_i, r)
                o = '{}/{}'.format(root_o, r)
                # FIXME
                # fs.make_link(i, o, True)
                # fs.make_link(i, o, False)
                if fs.exist(o):
                    print(
                        ':v8iln',
                        'target file exists! (this should not happen)',
                        i,
                        o,
                    )
                else:
                    fs.make_link(i, o, False)
        
        # TEST
        from lk_utils import start_ipython
        start_ipython(globals() | locals())

    else:
        assert (
            x := cache_maker.get_cache(
                '{};{}'.format(root_i, root_o),
                'last_dumped_records',
                check=False,
            )
        )
        records0: T.Records = x

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
            for r1 in sorted(res1, reverse=True):
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
            for r0 in sorted(res0, reverse=True):
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

    if not dry_run:
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


# ------------------------------------------------------------------------------


# def _analyze_dirs_tobe_created(todo_relfiles, todo_reldirs):
#     tobe_created_reldirs = set()
#     for p in todo_relfiles | todo_reldirs:
#         if '/' in p:
#             tobe_created_reldirs.update(
#                 _grind_down_dirpath(p.rsplit('/', 1)[0])
#             )
#     tobe_created_reldirs -= todo_reldirs
#     return tobe_created_reldirs


def _eliminate_overlapping_resources(
    reldirs: T.TodoDirs, relfiles: T.TodoFiles
) -> tp.Tuple[T.TodoDirs, T.TodoFiles]:
    """
    if there "A/B" and "A/B/C", then "A/B/C" is eliminated.
    because "A/B" already covers "A/B/C".
    """
    before_count = (len(reldirs), len(relfiles))

    for d0 in sorted(reldirs):
        if d0 in reldirs:
            for d1 in sorted(reldirs, reverse=True):
                if len(d1) > len(d0):
                    if d1.startswith(d0 + '/'):
                        print(
                            'remove dir "{}" that is covered by "{}"'.format(
                                d1, d0
                            ),
                            ':i2v',
                        )
                        reldirs.remove(d1)
                else:
                    break

    temp_dict = defaultdict(set)
    for f in relfiles:
        if '/' in f:
            temp_dict[f.rsplit('/', 1)[0]].add(f)
        else:
            temp_dict[''].add(f)
    for d1 in temp_dict.keys():
        if d1:
            for d0 in reldirs:
                if d1.startswith(d0 + '/'):
                    print(
                        'remove files "{}/*" (count={}) that are covered by '
                        '"{}"'.format(d1, len(temp_dict[d1]), d0),
                        ':i2v',
                    )
                    relfiles -= temp_dict[d1]
                    break

    after_count = (len(reldirs), len(relfiles))
    if after_count != before_count:
        print(
            'eliminate overlapping resources: {} -> {}'.format(
                before_count, after_count
            ),
            ':r2',
        )
    return reldirs, relfiles


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

    def resolve_patched_path(base_dir: str, relpath: str) -> str:
        """
        returns: a must-exist abspath or empty string.
        """
        if relpath.endswith('?'):
            nullable = True
            relpath = relpath[:-1]
        else:
            nullable = False

        suffix = '/' if relpath.endswith('/') else ''

        if '*' in relpath:
            candidates = glob('{}/{}'.format(base_dir, relpath))
            if len(candidates) == 0 and nullable:
                return ''
            elif len(candidates) == 1:
                if fs.exist(candidates[0]):
                    return fs.normpath(candidates[0]) + suffix
            else:
                # currently we don't allow multiple candidates. i think it's
                # fine to unlock this behavior. let me review this case later.
                raise Exception(relpath, candidates, nullable)
        else:
            if fs.exist(x := fs.normpath('{}/{}'.format(base_dir, relpath))):
                return x + suffix

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
                        if abspath1 := resolve_patched_path(base_dir, relpath1):
                            if abspath1.endswith('/'):
                                dirs.add(abspath1[:-1])
                            else:
                                files.add(abspath1)

    dirs, files = _eliminate_overlapping_resources(dirs, files)
    return files, dirs
