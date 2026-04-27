import ast
import atexit
import hashlib
import os
import typing as t
from lk_utils import fs


class T:
    # {file: tuple nodes, ...}
    #     nodes: ((node, line), ...)
    #         node: ast.Import | ast.ImportFrom
    #         line: str, preserves indentation
    CacheData = t.Dict[
        str, t.Tuple[t.Tuple[t.Union[ast.Import, ast.ImportFrom], str], ...]
    ]


class FileNodesCache:
    def __init__(self, pkl_file: str) -> None:
        self._cache: T.CacheData = fs.load(pkl_file)
        self._cache_file = pkl_file
        self._new_files = set()
        atexit.register(self._save)

    @property
    def changed_files(self) -> t.Set[str]:
        return self._new_files

    def parse_nodes(
        self, file: str
    ) -> t.Iterator[t.Tuple[t.Union[ast.Import, ast.ImportFrom], str]]:
        file_id = get_file_id(file)
        if file_id in self._cache:
            yield from self._cache[file_id]
            return
        print(':vi', 'parsing file', file)
        self._new_files.add(file)
        source = fs.load(file, 'plain')
        lines = source.splitlines()
        try:
            tree = ast.parse(source, file)
        except SyntaxError:
            print(':v8', 'syntax error when parsing file', file_id, file)
            nodes = ()
        else:
            nodes = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    line = lines[node.lineno - 1]
                    yield node, line
                    nodes.append((node, line))
        self._cache[file_id] = tuple(nodes)

    def _save(self) -> None:
        if self._new_files:
            fs.dump(self._cache, self._cache_file)


def get_file_id(file: str) -> str:
    return '{}:{}'.format(
        file, hashlib.md5(fs.load(file, 'binary')).hexdigest()
    )


# ------------------------------------------------------------------------------

cache_root: str
cache_file: str
file_cache: FileNodesCache
if _path := os.getenv('TREE_SHAKING_CACHE_ROOT'):
    assert fs.exist(_path), _path
    print(':vs', 'found tree-shaking cache root from environment', _path)
    if not fs.exist('{}/.init_ok'.format(_path)):
        fs.copy_file(
            fs.xpath('_cache/ignores.txt'), '{}/ignores.txt'.format(_path)
        )
        fs.make_dir('{}/auxiliary'.format(_path))
        fs.make_dir('{}/dumped_resources_maps'.format(_path))
        fs.make_dir('{}/module_graphs'.format(_path))
        fs.dump({}, '{}/module_graphs_alias.yaml'.format(_path))
        fs.dump({}, '{}/cache.pkl'.format(_path))
        fs.dump('', '{}/.init_ok'.format(_path))
    cache_root = _path
    cache_file = '{}/cache.pkl'.format(_path)
else:
    cache_root = fs.xpath('_cache')
    if not fs.exist('{}/.init_ok'.format(cache_root)):
        fs.dump({}, '{}/module_graphs_alias.yaml'.format(cache_root))
        fs.dump({}, '{}/cache.pkl'.format(cache_root))
        fs.dump('', '{}/.init_ok'.format(cache_root))
    cache_file = '{}/cache.pkl'.format(cache_root)
file_cache = FileNodesCache(cache_file)
