import typing as tp
from collections import defaultdict

from lk_utils import fs

from .cache import T as T0
from .cache import cache_maker
from .config import T as T1
from .file_parser import FileParser
from .file_parser import T as T2
from .file_parser import file_exists
from .patch import patch


class T(T2):
    Ignores = T1.Ignores
    SideFactors = T0.SideFactors


class Finder:
    def __init__(self) -> None:
        self._patched_modules = set()
        self._references = defaultdict(set)
        #   {module_name: {module_name, ...}, ...}
        self._resolved_files = set()

    @property
    def references(self) -> tp.Dict[str, tp.Set[str]]:
        assert self._references, (
            '`references` should be fetched after `get_all_imports()`'
        )
        return self._references

    def get_all_imports(
        self,
        script: T.FilePath,
        include_self: tp.Optional[bool] = True,
        ignores: T.Ignores = (),
        side_factors: T.SideFactors = (),
    ) -> tp.Dict[T.ModuleName, T.FilePath]:
        """
        Given a script file ('*.py'), return all direct and indirect modules
        that are imported by this file.
        Args:
            script: Must be formalized and absolute path.
            include_self:
                True: Yield module of script itself.
                False: Not yield itself.
                None: Not yield itself, but yield its children-selves if needed.
                    Note: `None` is only for internal use!
                As a caller, you should always give True or False.
        Yields:
            ((module_name, file_path), ...)
        """
        cache_key = (
            script + ':1',
            str(sorted(ignores)) + ':0' if ignores else '_:0',
            *side_factors,
        )
        if (
            x := cache_maker.get_cache(
                cache_key,
                'all_imports_{}'.format(1 if include_self else 0),
                persistent=True,
            )
        ) is not None:
            return x
        self._clear_holders()
        out = dict(self._get_all_imports(script, include_self, ignores))
        cache_maker.save_cache(
            cache_key,
            'all_imports_{}'.format(1 if include_self else 0),
            out,
            persistent=True,
        )
        return out

    def get_direct_imports(
        self,
        script: T.FilePath,
        include_self: bool = False,
        ignores: T.Ignores = (),
    ) -> T.ImportsInfo:
        script = fs.abspath(script)
        parser = FileParser(script)
        if include_self:
            yield parser.module_info, parser.file
        yield from parser.parse_imports(ignores)
        for path in self._more_imports(parser.module_info):
            x = FileParser(path)
            yield x.module_info, x.file

    def _get_all_imports(
        self,
        script: T.FilePath,
        include_self: tp.Optional[bool] = True,
        ignores: T.Ignores = (),
        _parent_info: tp.Optional[tp.Any] = None,
    ) -> tp.Iterator[tp.Tuple[T.ModuleName, T.FilePath]]:
        # each script can only be resolved once
        if script in self._resolved_files:
            return
        if not file_exists(script):
            # why this may be happened?
            # when we parsed a script that hit the cache through
            # `FileParser.parse_imports:cache_maker.get_cache`, it returned a
            # list of module infos. but the module info may contain outdated
            # and broken data.
            # for example, `streamlit_canary/session.py` was cached before, it
            # gave us a list of module infos, said that `lk_utils/textwrap.py`
            # was imported, but actually `lk_utils@3.8.0` did not have this
            # file. thus we can not resolve it by this method.
            # this was usually happened in recursive calls.
            # TODO: should we invalidate the cache in this case?
            print(':nv6il', 'script not exists', script, _parent_info)
            return

        parser = FileParser(script)
        # if parser.module_info.top in ignores:
        #     print('ignore', parser.module_info)
        #     return

        self_module_name = parser.module_info.full_name
        if include_self:
            assert self_module_name
            assert parser.module_info.top not in ignores
            yield self_module_name, parser.file

        more_files = set()
        for module, path in parser.parse_imports(ignores):
            # print(module, path)
            self._references[self_module_name].add(module.full_name)
            if path in self._resolved_files:
                continue
            assert module.full_name
            assert module.top not in ignores
            yield module.full_name, path

            # recursive
            if path.endswith(('.pyc', '.pyd')):
                continue
            else:  # endswith '.py'
                more_files.add((path, None))

            if path.endswith('/__init__.py'):
                continue
            else:
                possible_init_file = '{}/__init__.py'.format(
                    path.rsplit('/', 1)[0]
                )
                if possible_init_file in self._resolved_files:
                    continue
                elif fs.exist(possible_init_file):
                    more_files.add(
                        (
                            possible_init_file,
                            True if include_self in (True, None) else False,
                        )
                    )
                else:
                    self._resolved_files.add(possible_init_file)

        for path in self._more_imports(parser.module_info):
            more_files.add(
                (path, True if include_self in (True, None) else False)
            )

        self._resolved_files.add(script)

        for p, s in more_files:  # 'p': path, 's': self included
            yield from self._get_all_imports(
                p,
                s,
                ignores=ignores,
                _parent_info=(parser.module_info, parser.file),
            )

    def _clear_holders(self) -> None:
        self._patched_modules.clear()
        self._references.clear()
        self._resolved_files.clear()

    reset = _clear_holders

    def _more_imports(self, module: T.ModuleInfo) -> tp.Iterator[T.FilePath]:
        if module.top in patch:
            if module.top not in self._patched_modules:
                self._patched_modules.add(module.top)
                assert module.base_dir
                # print(module.full_name, patch[module.top]['imports'], ':l')
                for relpath in patch[module.top]['imports']:
                    if relpath.endswith('/'):
                        abspath = fs.normpath(
                            '{}/{}/__init__.py'.format(
                                module.base_dir, relpath.rstrip('/')
                            )
                        )
                    elif relpath.endswith(('.pyc', '.pyd')):
                        raise NotImplementedError
                    elif relpath.endswith('.py'):
                        abspath = fs.normpath(
                            '{}/{}'.format(module.base_dir, relpath)
                        )
                    else:
                        raise Exception(module, relpath)
                    yield abspath
