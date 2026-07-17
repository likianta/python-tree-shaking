import os
import typing as tp

from lk_utils import fs
from lk_utils import uuid


def _init_cache_root() -> str:
    if path := os.getenv('TREE_SHAKING_CACHE_ROOT'):
        assert fs.exist(path), path
        print(':v', 'get tree-shaking cache root from environment', path)
        if not fs.exist('{}/.init_ok'.format(path)):
            fs.copy_file(
                fs.here('_cache/ignores.txt'), '{}/ignores.txt'.format(path)
            )
            fs.make_dir('{}/auxiliary'.format(path))
            fs.make_dir('{}/cached_by_profile'.format(path))
            fs.make_dir('{}/dumped_resources_maps'.format(path))
            fs.make_dir('{}/module_graphs'.format(path))
            fs.make_dir('{}/watch_files'.format(path))
            fs.dump({}, '{}/module_graphs_alias.yaml'.format(path))
            fs.dump('', '{}/.init_ok'.format(path))
        cache_root = path
    else:
        cache_root = fs.here('_cache')
        if not fs.exist('{}/.init_ok'.format(cache_root)):
            fs.dump({}, '{}/module_graphs_alias.yaml'.format(cache_root))
            fs.dump('', '{}/.init_ok'.format(cache_root))
    return cache_root


cache_root = _init_cache_root()

# ------------------------------------------------------------------------------


class _CacheMaker:
    def __init__(self, cache_root: str) -> None:
        self._cache_root = cache_root
        self._tobe_deleted_files = set()

    def get_cache(self, source_file: str, namespace: str) -> tp.Optional[dict]:
        file = '{}/watch_files/{}/{}.pkl'.format(
            self._cache_root, uuid(fs.abspath(source_file)), namespace
        )
        if not fs.exist(fs.parent(file)):
            fs.make_dir(fs.parent(file))
            return None
        if fs.exist(file):
            timestamp, data = fs.load(file)
            if timestamp == fs.filetime(source_file):
                return data
            else:
                self._tobe_deleted_files.add(file)
                return None
        else:
            return None

    def save_cache(
        self, data: tp.Any, source_file: str, namespace: str
    ) -> None:
        file = '{}/watch_files/{}/{}.pkl'.format(
            self._cache_root, uuid(fs.abspath(source_file)), namespace
        )
        fs.dump((fs.filetime(source_file), data), file)


cache_maker = _CacheMaker(cache_root)
