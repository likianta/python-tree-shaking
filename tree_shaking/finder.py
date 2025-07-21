import typing as t
from collections import defaultdict

from lk_utils import fs

from .file_parser import FileParser
from .file_parser import T
from .patch import patch


class Finder:
    
    def __init__(
        self,
        global_ignores: t.Union[
            t.FrozenSet[T.ModuleName],
            t.Tuple[T.ModuleName, ...]
        ]
    ) -> None:
        self._global_ignores = global_ignores
        self._patched_modules = set()
        self._references = defaultdict(set)
        self._resolved_files = set()
    
    @property
    def references(self) -> t.Dict[str, t.Set[str]]:
        assert self._references, \
            '`references` should be fetched after `get_all_imports()`'
        return self._references
    
    def get_all_imports(
        self,
        script: T.FilePath,
        include_self: t.Optional[bool] = True,
    ) -> t.Iterator[t.Tuple[T.ModuleName, T.FilePath]]:
        """
        given a script file ('*.py'), return all direct and indirect modules
        that are imported by this file.
        params:
            script: must be formalized and absolute path.
            include_self:
                True: yield module of script itself.
                False: not yield itself.
                None: not yield itself, but yield its children-selves if needed.
                    note: None is only for internal use!
                as a caller, you should always give True or False to this param.
        yields:
            ((module_name, file_path), ...)
        """
        self._clear_holders()
        yield from self._get_all_imports(script, include_self)
    
    def get_direct_imports(
        self, script: T.FilePath, include_self: bool = False
    ) -> T.ImportsInfo:
        script = fs.abspath(script)
        parser = FileParser(script)
        if include_self:
            yield parser.module_info, parser.file
        yield from parser.parse_imports()
        for path in self._more_imports(parser.module_info):
            x = FileParser(path)
            yield x.module_info, x.file
    
    def _get_all_imports(
        self,
        script: T.FilePath,
        include_self: t.Optional[bool] = True,
    ) -> t.Iterator[t.Tuple[T.ModuleName, T.FilePath]]:
        # each script can only be resolved once
        if script in self._resolved_files:
            return
        
        parser = FileParser(script)
        # if parser.module_info.top.lower() in self._global_ignores:
        #     print('ignore', parser.module_info)
        #     return
        
        self_module_name = parser.module_info.full_name
        if include_self:
            yield self_module_name, parser.file
        
        more_files = set()
        for module, path in parser.parse_imports():
            # print(module, path)
            if module.top.lower() in self._global_ignores:
                continue
            self._references[self_module_name].add(module.full_name)
            if path in self._resolved_files:
                continue
            assert module.full_name
            yield module.full_name, path
            
            # recursive
            if path.endswith(('.pyc', '.pyd')):
                continue
            else:  # endswith '.py'
                more_files.add((path, None))
            
            if path.endswith('/__init__.py'):
                continue
            else:
                possible_init_file = \
                    '{}/__init__.py'.format(path.rsplit('/', 1)[0])
                if possible_init_file in self._resolved_files:
                    continue
                elif fs.exist(possible_init_file):
                    more_files.add((
                        possible_init_file,
                        True if include_self in (True, None) else False
                    ))
                else:
                    self._resolved_files.add(possible_init_file)
        
        for path in self._more_imports(parser.module_info):
            more_files.add(
                (path, True if include_self in (True, None) else False)
            )
        
        self._resolved_files.add(script)
        
        for p, s in more_files:  # 'p': path, 's': self included
            yield from self._get_all_imports(p, s)
    
    def _clear_holders(self) -> None:
        self._patched_modules.clear()
        self._references.clear()
        self._resolved_files.clear()
        
    reset = _clear_holders
    
    def _more_imports(self, module: T.ModuleInfo) -> t.Iterator[T.FilePath]:
        if module.top in patch:
            if module.top not in self._patched_modules:
                self._patched_modules.add(module.top)
                assert module.base_dir
                # print(module.full_name, patch[module.top]['imports'], ':l')
                for relpath in patch[module.top]['imports']:
                    if relpath.endswith('/'):
                        abspath = fs.normpath('{}/{}/__init__.py'.format(
                            module.base_dir, relpath.rstrip('/')
                        ))
                    elif relpath.endswith(('.pyc', '.pyd')):
                        raise NotImplementedError
                    elif relpath.endswith('.py'):
                        abspath = fs.normpath(
                            '{}/{}'.format(module.base_dir, relpath)
                        )
                    else:
                        raise Exception(module, relpath)
                    yield abspath
