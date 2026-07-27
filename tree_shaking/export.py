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
from .path_typing import T as T1


class T(T1):
    Config = T0.Config
    DryRun = tp.Union[bool, tp.Literal[0, 1, 2]]
    #   0: no dry run
    #   1: no actual file operations, only prints.
    #   2: same as 1, but disable incremental update

    Records = tp.TypedDict(
        'Records',
        {
            'created_directories': tp.FrozenSet[T1.RelDirPath],
            'resource_records': tp.Dict[T1.RelPath, int],
        },
    )
    TodoDirs = tp.Union[tp.Set[T1.RelDirPath]]
    TodoFiles = tp.Union[tp.Set[T1.RelFilePath]]


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


def dump_tree_from_config(config: T.Config, dry_run: T.DryRun = False) -> None:
    source = config['export']['source']  # an absolute path
    target = config['export']['target']  # a valid abspath
    print(source, target, ':nv2l')
    assert source and target

    if source:
        files, dirs = _mount_resources(config, source)
        _dump_single_source(
            root_i=source,
            root_o=target,
            files_i=files,
            dirs_i=dirs,
            dry_run=dry_run,
            _exempt=True,
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
    dir_o: T.AnyDirPath, dry_run: T.DryRun = False
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
    )


# ------------------------------------------------------------------------------


def _dump_single_source(
    root_i: T.AbsDirPath,
    root_o: T.AbsDirPath,
    files_i: tp.Union[tp.Iterable[T.RelPath], tp.Iterable[T.AbsPath]],
    dirs_i: tp.Union[tp.Iterable[T.RelPath], tp.Iterable[T.AbsPath]] = (),
    # copy_files: bool = False,
    dry_run: T.DryRun = False,
    _exempt: bool = False,
) -> None:
    if _exempt:
        todo_relfiles = set(files_i)
        todo_reldirs = set(dirs_i)
    else:
        with np.scope():
            todo_relfiles = set()
            for f in files_i:
                if f.startswith(root_i + '/'):
                    todo_relfiles.add(f.removeprefix(root_i + '/'))
                    # if fs.exist(f):
                    #     todo_relfiles.add(f.removeprefix(root_i + '/'))
                    # else:
                    #     print(':v6', 'file not exists', f)
                elif dry_run:
                    print('ignore file resource out of root_i', f, ':i2v5')
            assert todo_relfiles

            todo_reldirs = set()
            for d in dirs_i:
                if d.startswith(root_i + '/'):
                    todo_reldirs.add(d.removeprefix(root_i + '/'))
                elif dry_run:
                    print('ignore dir resource out of root_i', d, ':i2v5')

    tobe_created_reldirs = _analyze_dirs_tobe_created(
        todo_relfiles, todo_reldirs
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
                fs.make_link(i, o, False)
                # fs.make_link(i, o, True)
                # if fs.exist(o):
                #     print(
                #         ':v8iln',
                #         'target file exists! (this should not happen)',
                #         i,
                #         o,
                #     )
                # else:
                #     fs.make_link(i, o, False)

    else:
        assert (
            x := cache_maker.get_cache(
                '{};{}'.format(root_i, root_o) + ':0', 'last_dumped_records'
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
                if fs.exist(o):
                    fs.remove_tree(o)
                else:
                    print('already removed?', d, ':v5')

        res0 = records0['resource_records']
        res1 = {}
        for r in todo_relfiles:
            res1[r] = tp.cast(int, fs.mtime('{}/{}'.format(root_i, r)))
        for r in sorted(todo_reldirs, reverse=True):
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
                            print('already removed?', r0, ':v5')

    if not dry_run:
        records1: T.Records = {
            'created_directories': frozenset(tree1),
            'resource_records': res1,
        }
        cache_maker.save_cache(
            '{};{}'.format(root_i, root_o) + ':0',
            'last_dumped_records',
            records1,
        )
    print('export done', ':ptv4')


# ------------------------------------------------------------------------------


def _analyze_dirs_tobe_created(
    todo_relfiles: T.TodoFiles, todo_reldirs: T.TodoDirs
) -> T.TodoDirs:
    out = set()
    for p in todo_relfiles | todo_reldirs:
        if '/' in p:
            out.update(_grind_down_dirpath(p.rsplit('/', 1)[0]))
    # remove paths that are covered by todo_reldirs.
    out = set(
        x
        for x in out
        if x not in todo_reldirs
        and not any(x.startswith(y + '/') for y in todo_reldirs)
    )
    return out


def _eliminate_overlapping_resources(
    reldirs: T.TodoDirs, relfiles: T.TodoFiles
) -> tp.Tuple[T.TodoDirs, T.TodoFiles]:
    """
    if there are "A/B" and "A/B/C", then "A/B/C" is eliminated. because "A/B"
    already covers "A/B/C".
    """
    before_count = (len(reldirs), len(relfiles))

    for d0 in sorted(reldirs)[:-1]:
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
            temp_dict[f.rsplit('/', 1)[0] + '/'].add(f)
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
    config: T.Config, source_root: T.AbsDirPath
) -> tp.Tuple[T.TodoFiles, T.TodoDirs]:
    files: T.TodoFiles = set()
    dirs: T.TodoDirs = set()
    patched_modules: tp.Set[str] = set()

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
            entry_path + ':1', 'module_graphs', persistent=True
        )
        assert graph

        # required_uid = dict(
        #     (v, k) for k, v in graph['source_roots'].items()
        # )[source_root]
        required_uid: tp.Optional[str] = None
        for uid, root in graph['source_roots'].items():
            if root == source_root:
                required_uid = uid
                break
        assert required_uid

        for module_name, relpath in graph['modules'].items():
            uid, relpath = relpath.split('/', 1)
            uid = uid[1:-1]
            if uid != required_uid:
                continue

            files.add(relpath)

            # patch: fill extra files
            top_name = module_name.split('.', 1)[0]
            if top_name in patch:
                if top_name not in patched_modules:
                    patched_modules.add(top_name)
                    # assert relpath.startswith(top)
                    base_dir = '{}/{}'.format(source_root, top_name)
                    for relpath1 in patch[top_name]['files']:
                        if abspath1 := resolve_patched_path(base_dir, relpath1):
                            assert abspath1.startswith(source_root + '/')
                            relpath2 = abspath1.removeprefix(source_root + '/')
                            if relpath2.endswith('/'):
                                dirs.add(relpath2[:-1])
                            else:
                                files.add(relpath2)

    dirs, files = _eliminate_overlapping_resources(dirs, files)
    return files, dirs
