import ast
import atexit
import typing as tp
from contextlib import contextmanager

import neoprint as np
from lk_utils import Signal
from lk_utils import fs

from .cache2 import cache_maker
from .cache2 import cache_root
from .module import ModuleInfo
from .module import ModuleInspector
from .module import ModuleNotFound
from .module import PathNotFound
from .module import T as T0
from .path_scope import path_scope

new_parsing_triggered = Signal(str)
module_inspector = ModuleInspector(
    ignores=fs.load('{}/ignores.txt'.format(cache_root)).splitlines()
)
_broken = set()


class T(T0):
    AstNode = tp.Union[ast.Import, ast.ImportFrom]
    ImportsInfo = tp.Iterable[tp.Tuple[T0.ModuleInfo, T0.FilePath]]
    #   ((module_info, path), ...)
    #       module_info: dataclass ModuleInfo


class FileParser:
    def __init__(self, file: T.FilePath) -> None:
        self.file = file
        self.dir = fs.parent(file)

        if self.file in path_scope.path_2_module:
            self.base_dir = self.dir
            self.base_module_segs = ()
        elif self.dir in path_scope.path_2_module:
            self.base_dir = self.dir
            self.base_module_segs = (path_scope.path_2_module[self.dir],)
        else:
            for top_path, top_name in path_scope.path_2_module.items():
                if self.file.startswith(top_path + '/'):
                    self.base_dir = top_path
                    self.base_module_segs = (
                        top_name,
                        *self.dir[len(top_path) + 1 :].split('/'),
                    )
                    break
            else:
                raise Exception(
                    'file should be existed in registered path scopes', file
                )

    @property
    def module_info(self) -> ModuleInfo:
        if self.base_module_segs:
            module_name = '{}.{}'.format(
                '.'.join(self.base_module_segs), fs.barename(self.file)
            )
        else:
            module_name = fs.barename(self.file)
        return ModuleInfo(
            name0=module_name,
            name1='',
            name2='',
            level=0,
            base_dir=self.base_dir,
            full_name=module_name,
        )

    def parse_imports(self) -> T.ImportsInfo:
        # print(':dv2p', 'start', self.file)
        if x := cache_maker.get_cache(
            self.file, 'ast_parsing_results', persistent=True
        ):
            return x
        new_parsing_triggered.emit(self.file)
        out = []
        for node, line in self.parse_nodes(self.file):
            for module in self._get_module_info(node, line):
                try:
                    path = self._get_module_path(module)
                except (ModuleNotFound, PathNotFound):
                    if module.id not in _broken:
                        _broken.add(module.id)
                        # with _err_records.recording():
                        #     print(
                        #         ':v5l',
                        #         '{}:{}'.format(self.file, node.lineno),
                        #         line.strip(),
                        #         module,
                        #         type(e),
                        #     )
                    continue
                except Exception as e:
                    e.add_note(
                        np.format(self.file, node.lineno, module, ':v8ln')
                    )
                    raise e
                if path in ('<stdlib>', '<ignored>'):
                    continue
                else:
                    out.append((module, path))
        # print(':vp', 'end', self.file)
        cache_maker.save_cache(
            self.file, 'ast_parsing_results', out, persistent=True
        )
        return out

    def parse_nodes(self, file: str) -> tp.Iterator[tp.Tuple[T.AstNode, str]]:
        print(':vi', 'ast parsing file', file)
        source_text = fs.load(file, 'plain')
        source_lines = source_text.splitlines()
        try:
            tree = ast.parse(source_text, file)
        except SyntaxError:
            print(':v8', 'syntax error when parsing file', file)
        else:
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    line = source_lines[node.lineno - 1]
                    yield node, line

    def _check_if_relative_import(self, line: str) -> int:
        x = line.lstrip().split()[1]
        if not x:
            raise Exception('empty import', self.file, line)
        dot_cnt = 0
        for ch in x:
            if ch == '.':
                dot_cnt += 1
            else:
                break
        return dot_cnt

    def _get_module_info(
        self, node: T.AstNode, line: str
    ) -> t.Iterator[T.ModuleInfo]:  # noqa
        if dot_cnt := self._check_if_relative_import(line):
            if dot_cnt == 1:
                base_module = '.'.join(self.base_module_segs)
            else:
                base_module = '.'.join(self.base_module_segs[: -(dot_cnt - 1)])
        else:
            base_module = None
        if base_module:
            base_dir = fs.normpath(
                '{}/{}'.format(self.dir, '../' * (dot_cnt - 1))
            )
        else:
            base_dir = None

        if isinstance(node, ast.Import):
            for alias in node.names:
                if base_module:
                    module_name = '{}.{}'.format(base_module, alias.name)
                else:
                    module_name = alias.name
                yield ModuleInfo(
                    name0=module_name,
                    name1=alias.name,
                    name2='',
                    level=dot_cnt,
                    base_dir=base_dir,
                )
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if base_module:
                    if node.module:
                        module_name = '{}.{}'.format(base_module, node.module)
                    else:
                        module_name = base_module
                else:
                    if node.module:
                        module_name = node.module
                    else:
                        print(
                            ':v4l',
                            self.file,
                            node.lineno,
                            line,
                            {
                                k: getattr(node, k)
                                for k in dir(node)
                                if not k.startswith('_')
                            },
                            {
                                k: getattr(alias, k)
                                for k in dir(alias)
                                if not k.startswith('_')
                            },
                        )
                        # raise Exception(self.file, node.lineno, line)
                        continue
                yield ModuleInfo(
                    name0=module_name,
                    name1=node.module or '',
                    name2=alias.name,
                    level=dot_cnt,
                    base_dir=base_dir,
                )

    def _get_module_path(self, module: T.ModuleInfo) -> T.FilePath:
        # assert '//' not in module_inspector.find_module_path(module), module
        return module_inspector.find_module_path(module)


class ErrorRecords:
    def __init__(self) -> None:
        self._records = []
        atexit.register(self.save)

    @contextmanager
    def recording(self) -> tp.Generator:
        # FIXME: with parallel_printing(self._log):
        yield

    def _log(self, msg: str) -> None:
        self._records.append(str(msg))

    def save(self) -> bool:
        if self._records:
            fs.dump(self._records, '{}/errors.txt'.format(cache_root))
            print(
                'found {} errors. see log at "{}/errors.txt"'.format(
                    len(self._records), cache_root
                ),
                ':v8s',
            )
            return True
        return False


_err_records = ErrorRecords()
