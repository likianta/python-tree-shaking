import typing as t

from lk_utils import fs

from .file_parser import FileParser
from .file_parser import T


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
    _resolved_modules: t.Set = None,
    # _resolved_files: t.Set = None,
    _resolved_init_files: t.Set = None,
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
    
    if _resolved_modules is None:  # first time init
        _resolved_modules = set()
        # _resolved_files = set()
        _resolved_init_files = set()
    
    parser = FileParser(script)
    if include_self:
        yield parser.module_info.full_name, parser.file
    
    for module, path in parser.parse_imports():
        # print(module, path)
        assert module.full_name
        if module.full_name not in _resolved_modules:
            _resolved_modules.add(module.full_name)
            yield module.full_name, path
            
            # recursive
            if path.endswith('.py'):  # to deviate '.pyc' and '.pyd' files
                yield from get_all_imports(
                    path,
                    None,
                    _resolved_modules,
                    _resolved_init_files,
                )
            
            if path.endswith('/__init__.py'):
                _resolved_init_files.add(path)
            else:
                possible_init_file = '{}/__init__.py'.format(
                    path.rsplit('/', 1)[0]
                )
                if possible_init_file not in _resolved_init_files:
                    _resolved_init_files.add(possible_init_file)
                    if fs.exists(possible_init_file):
                        # global _auto_index
                        # _auto_index += 1
                        # yield (
                        #     '__implicit_import_{:03}'.format(_auto_index),
                        #     possible_init_file
                        # )
                        yield from get_all_imports(
                            possible_init_file,
                            True if include_self in (True, None) else False,
                            _resolved_modules,
                            _resolved_init_files,
                        )


_auto_index = 0  # DELETE


def get_direct_imports(
    script: T.FilePath, include_self: bool = True
) -> T.ImportsInfo:
    parser = FileParser(script)
    if include_self:
        yield parser.module_info, parser.file
    yield from parser.parse_imports()
