import ast
import atexit
import os
import typing as tp

from lk_utils import fs
from lk_utils import uuid


class T:
    AstNode = tp.Union[ast.Import, ast.ImportFrom]
    FileId = str  # see `get_file_id`
    CacheData = tp.Dict[FileId, tp.Tuple[tp.Tuple[AstNode, str], ...]]
    #   {file_id: tuple nodes, ...}
    #       nodes: ((node, line), ...)
    #           node: ast.Import | ast.ImportFrom
    #           line: str, preserves indentation


class FileNodesCache:
    _cache_data: T.CacheData
    _cache_file: str
    _cache_root: str
    _new_files: tp.Set[str]

    def __init__(self, cache_root: str) -> None:
        self._cache_root = cache_root
        self._new_files = set()
        atexit.register(self._save)

    def init_by_profile(self, profile: str) -> None:
        self._cache_file = '{}/cached_by_profile/{}.pkl'.format(
            self._cache_root, uuid(profile)
        )
        self._cache_data = fs.load(self._cache_file, default=lambda: {})

    @property
    def changed_files(self) -> tp.Set[str]:
        return self._new_files

    def parse_nodes(self, file: str) -> tp.Iterator[tp.Tuple[T.AstNode, str]]:
        file_id = get_file_id(file)
        if file_id in self._cache_data:
            #   if AttributeError happens to `self._cache_data`, check if you
            #   forget to call `init_by_profile`.
            yield from self._cache_data[file_id]
            return
        print(':vi', 'ast parsing file', file)
        self._new_files.add(file)
        source = fs.load(file, 'plain')
        lines = source.splitlines()
        nodes = []
        try:
            tree = ast.parse(source, file)
        except SyntaxError:
            print(':v8', 'syntax error when parsing file', file_id, file)
        else:
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    line = lines[node.lineno - 1]
                    yield node, line
                    nodes.append((node, line))
        print(':v', file, file_id, len(nodes))
        self._cache_data[file_id] = tuple(nodes)

    def _save(self) -> None:
        if self._new_files:
            fs.dump(self._cache_data, self._cache_file)
            print(
                'saved tree shaking cache',
                len(self._new_files),
                self._cache_file,
                fs.filesize(self._cache_file, str),
                ':vnl',
            )


def get_file_id(file: str) -> T.FileId:
    return uuid('{}:{}'.format(file, fs.filetime(file)))


# ------------------------------------------------------------------------------

cache_root: str
if _path := os.getenv('TREE_SHAKING_CACHE_ROOT'):
    assert fs.exist(_path), _path
    print(':v', 'get tree-shaking cache root from environment', _path)
    if not fs.exist('{}/.init_ok'.format(_path)):
        fs.copy_file(
            fs.here('_cache/ignores.txt'), '{}/ignores.txt'.format(_path)
        )
        fs.make_dir('{}/auxiliary'.format(_path))
        fs.make_dir('{}/cached_by_profile'.format(_path))
        fs.make_dir('{}/dumped_resources_maps'.format(_path))
        fs.make_dir('{}/module_graphs'.format(_path))
        fs.dump({}, '{}/module_graphs_alias.yaml'.format(_path))
        fs.dump('', '{}/.init_ok'.format(_path))
    cache_root = _path
else:
    cache_root = fs.here('_cache')
    if not fs.exist('{}/.init_ok'.format(cache_root)):
        fs.dump({}, '{}/module_graphs_alias.yaml'.format(cache_root))
        fs.dump('', '{}/.init_ok'.format(cache_root))

file_cache = FileNodesCache(cache_root)
