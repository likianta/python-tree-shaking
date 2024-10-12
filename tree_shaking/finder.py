import typing as t
from collections import defaultdict

from lk_utils import fs

from .file_parser import FileParser
from .file_parser import T
from .patch import patch


def get_all_imports(
    script: T.FilePath,
    include_self: t.Optional[bool] = True,
    _resolved_files: t.Set = None,
) -> t.Iterator[t.Tuple[T.ModuleName, T.FilePath]]:
    """
    given a script file ('*.py'), return all direct and indirect modules that
    are imported by this file.
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
    
    if _resolved_files is None:  # first time init
        _resolved_files = set()
        # init/reset global holders
        _patched_modules.clear()
        _references[0].clear()
        _references[1].clear()
    
    # each script can only be resolved once
    if script in _resolved_files:
        return
    
    parser = FileParser(script)
    self_module_name = parser.module_info.full_name
    if include_self:
        yield self_module_name, parser.file
    
    more_files = set()
    for module, path in parser.parse_imports():
        # print(module, path)
        _references[0][self_module_name].add(module.full_name)
        _references[1][module.full_name].add(self_module_name)
        
        if path in _resolved_files: continue
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
            possible_init_file = '{}/__init__.py'.format(path.rsplit('/', 1)[0])
            if possible_init_file in _resolved_files:
                continue
            elif fs.exists(possible_init_file):
                more_files.add((
                    possible_init_file,
                    True if include_self in (True, None) else False
                ))
            else:
                _resolved_files.add(possible_init_file)
        
    for path in _more_imports(parser.module_info):
        more_files.add((path, True if include_self in (True, None) else False))
    
    _resolved_files.add(script)
    
    for p, s in more_files:  # 'p': path, 's': self included
        yield from get_all_imports(p, s, _resolved_files)
    

# DELETE
def get_direct_imports(
    script: T.FilePath, include_self: bool = True
) -> T.ImportsInfo:
    script = fs.abspath(script)
    parser = FileParser(script)
    if include_self:
        yield parser.module_info, parser.file
    yield from parser.parse_imports()
    for path in _more_imports(parser.module_info):
        x = FileParser(path)
        yield x.module_info, x.file


def get_references() -> t.Tuple[dict, dict]:
    assert _references[0] and _references[1], \
        'get_references() should be called after get_all_imports().'
    return _references


_patched_modules = set()

# (forward_refs, backward_refs)
#   forward_refs: {
#       module_name_a: set[module_name_b, ...],
#       module_name_b: empty_set,
#       ...
#   }
#   backward_refs: {
#       module_name_a: empty_set,
#       module_name_b: set[module_name_a, ...],
#       ...
#   }
_references = (defaultdict(set), defaultdict(set))


def _more_imports(module: T.ModuleInfo) -> t.Iterator[T.FilePath]:
    if module.top in patch:
        if module.top not in _patched_modules:
            _patched_modules.add(module.top)
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
