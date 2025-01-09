import ast
import atexit
import hashlib
import typing as t

from lk_utils import fs
from lk_utils import p


class FileNodesCache:
    
    def __init__(self, pkl_file: str) -> None:
        self._cache = fs.load(pkl_file)
        self._cache_file = pkl_file
        self._changed = False
        atexit.register(self._save)
    
    def parse_nodes(
        self, file: str
    ) -> t.Iterator[t.Tuple[t.Union[ast.Import, ast.ImportFrom], str]]:
        file_id = get_file_id(file)
        if file_id in self._cache:
            yield from self._cache[file_id]
            return
        print(':vi2', 'parsing file', file)
        source = fs.load(file, 'plain')
        lines = source.splitlines()
        tree = ast.parse(source, file)
        nodes = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                line = lines[node.lineno - 1]
                yield node, line
                nodes.append((node, line))
        self._cache[file_id] = tuple(nodes)
        self._changed = True
    
    def _save(self) -> None:
        if self._changed:
            fs.dump(self._cache, self._cache_file)


def get_file_id(file: str) -> str:
    return '{}:{}'.format(
        file, hashlib.md5(fs.load(file, 'binary')).hexdigest()
    )


if not fs.exists(x := p('../data/cache.pkl')):
    '''
    {file: tuple nodes, ...}
        nodes: ((node, line), ...)
            node: ast.Import | ast.ImportFrom
            line: str, preserves indentation
    '''
    fs.dump({}, x)
file_cache = FileNodesCache(x)
