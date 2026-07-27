import typing as tp
from glob import glob

from lk_utils import fs

from .path_typing import T as T0


class T(T0):
    PatchItem = tp.TypedDict(
        'PatchItem',
        {'files': tp.Tuple[str, ...], 'imports': tp.Tuple[str, ...]},
    )


class Patch:
    def __init__(self, hooks_file: T.AnyFilePath) -> None:
        hooks = fs.load(hooks_file)
        self._patches = {}
        #   {
        #     module: {
        #         'imports': (relpath, ...),
        #         'files': (relpath | relpaths, ...)
        #         #   relpaths: [relpath, ...]
        #         #       one of them should be existed in target folder.
        #         #       there may be None in the list, means it doesn't matter -
        #         #       if none of them existed.
        #     }, ...
        #   }
        for k, v in hooks.items():
            self._patches[k] = {
                'imports': tuple(v.get('imports', ())),
                'files': tuple(v.get('files', ())),
            }

    def __contains__(self, module_name: str) -> bool:
        return module_name in self._patches

    def __getitem__(self, module_name: str) -> T.PatchItem:
        return self._patches[module_name]


class ResourcePatch:
    def __init__(self, source_root: T.AbsDirPath) -> None:
        self._resolved_modules = set()
        self._source_root = source_root

    def is_resolved(self, module_name: str) -> bool:
        return module_name in self._resolved_modules

    def resolve(
        self, module_name: str
    ) -> tp.Tuple[tp.Set[T.RelFilePath], tp.Set[T.RelDirPath]]:
        files, dirs = set(), set()
        base_dir = '{}/{}'.format(self._source_root, module_name)
        for relpath in patch[module_name]['files']:
            if abspath := self._resolve_path(base_dir, relpath):
                assert abspath.startswith(self._source_root + '/'), abspath
                relpath2 = abspath.removeprefix(self._source_root + '/')
                if relpath2.endswith('/'):
                    dirs.add(relpath2[:-1])
                else:
                    files.add(relpath2)
        self._resolved_modules.add(module_name)
        return files, dirs

    def _resolve_path(self, base_dir: T.AbsDirPath, relpath: T.RelPath) -> str:
        """
        returns: a must-exist abspath or empty string. the returned path may
        contain '/' at the end to indicate a directory.
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
            raise Exception(base_dir, relpath)


implicit_hooks_file = fs.here('patches/implicit_import_hooks.yaml')
patch = Patch(implicit_hooks_file)
