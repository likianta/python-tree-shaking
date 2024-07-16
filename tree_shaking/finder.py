import typing as t

from lk_utils import fs

from .file_parser import FileParser
from .file_parser import T
from .patch import patch


def dump_all_imports(
    script: T.FilePath, result_file: str, sort: bool = False
) -> t.Tuple[t.Dict[T.ModuleName, T.FilePath], T.FilePath]:
    script = fs.abspath(script)
    result = dict(get_all_imports(script))
    if sort:
        result = dict(sorted(result.items()))
    # for module in result:
    #     print(':i', module)
    fs.dump(result, result_file)
    return result, result_file


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
            values:
                True: yield module of script itself.
                False: not yield module of script itself.
                None: not yield itself, but yield its children-selves if needed.
                    note: None is for internal use!
            as a caller, you should always give True or False to this param.
    """
    
    if _resolved_files is None:  # first time init
        _resolved_files = set()
        _patched_modules.clear()
    
    # each script can only be resolved once
    if script in _resolved_files:
        return
    
    parser = FileParser(script)
    if include_self:
        yield parser.module_info.full_name, parser.file
    
    more_files = set()
    for module, path in parser.parse_imports():
        # print(module, path)
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
            possible_init_file = '{}/__init__.py'.format(
                path.rsplit('/', 1)[0]
            )
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
    
    for p, s in more_files:
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


_patched_modules = set()


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
