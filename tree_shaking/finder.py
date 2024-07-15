import typing as t

from lk_utils import fs
from .file_parser import FileParser
from .file_parser import T


def dump_all_imports(
    script: T.FilePath, result_file: str, sort: bool = False
) -> t.Tuple[t.Dict[T.ModuleName, T.FilePath], T.FilePath]:
    result = dict(get_all_imports(script))
    if sort:
        result = dict(sorted(result.items()))
    # for module in result:
    #     print(':i', module)
    fs.dump(result, result_file)
    return result, result_file


def get_all_imports(
    script: T.FilePath,
    _resolved_modules: t.Set = None,
    _resolved_init_files: t.Set = None,
) -> t.Iterator[t.Tuple[T.ModuleName, T.FilePath]]:
    """
    given a script file ('*.py'), return all direct and indirect modules that
    are imported by this file.
    """
    if _resolved_modules is None:
        _resolved_modules = set()
        _resolved_init_files = set()
    for module, path in get_direct_imports(script):
        # print(module, path)
        assert module.full_name
        if module.full_name not in _resolved_modules:
            _resolved_modules.add(module.full_name)
            yield module.full_name, path
            if path.endswith('.py'):  # to deviate '.pyc' and '.pyd' files
                yield from get_all_imports(
                    path,
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
                        global _auto_index
                        _auto_index += 1
                        yield (
                            '__implicit_import_{:03}'.format(_auto_index),
                            possible_init_file
                        )
                        yield from get_all_imports(
                            possible_init_file,
                            _resolved_modules,
                            _resolved_init_files,
                        )


_auto_index = 0


def get_direct_imports(script: T.FilePath) -> T.ImportsInfo:
    parser = FileParser(script)
    return parser.parse_imports()
