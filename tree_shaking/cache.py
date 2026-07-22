import atexit
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
            fs.make_dir('{}/dumped_resources_maps'.format(path))
            fs.make_dir('{}/watch_files'.format(path))
            fs.dump('', '{}/.init_ok'.format(path))
        cache_root = path
    else:
        cache_root = fs.here('_cache')
        if not fs.exist('{}/.init_ok'.format(cache_root)):
            fs.dump('', '{}/.init_ok'.format(cache_root))
    return cache_root


cache_root = _init_cache_root()

# ------------------------------------------------------------------------------


class _CacheMaker:
    def __init__(self, cache_root: str) -> None:
        self._cache_root = cache_root
        self._quick_fetches = {}
        self._tobe_deleted_files = set()
        atexit.register(self._delete_outdated_files)

    def is_cached(self, source: str, namespace: str) -> bool:
        if source in self._tobe_deleted_files:
            return False
        else:
            file = '{}/watch_files/{}/{}.pkl'.format(
                self._cache_root, uuid(source), namespace
            )
            if fs.exist(file):
                timestamp = fs.load(file)[0]
                if timestamp == fs.filetime(source):
                    return True
                else:
                    self._tobe_deleted_files.add(file)
                    return False
            else:
                return False

    def get_cache(
        self, source: str, namespace: str, persistent: bool = False
    ) -> tp.Optional[tp.Any]:
        """
        source: suggest passing script path. generally, any string is ok.

        notice: the return value may be empty list, empty dict or something.
        you should not use generic `if data: ...` to check it.
        """
        if persistent and (source, namespace) in self._quick_fetches:
            return self._quick_fetches[(source, namespace)]

        file = '{}/watch_files/{}/{}.pkl'.format(
            self._cache_root, uuid(source), namespace
        )
        if file in self._tobe_deleted_files:
            return None
        if fs.exist(file):
            timestamp, data = fs.load(file)
            if timestamp == fs.filetime(source):
                if persistent:
                    self._quick_fetches[(source, namespace)] = data
                return data
            else:
                self._tobe_deleted_files.add(file)
                return None
        else:
            return None

    def save_cache(
        self,
        source: str,
        namespace: str,
        data: tp.Any,
        persistent: bool = False,
    ) -> str:
        file = '{}/watch_files/{}/{}.pkl'.format(
            self._cache_root, uuid(fs.abspath(source)), namespace
        )
        if not fs.exist(fs.parent(file)):
            fs.make_dir(fs.parent(file))
        fs.dump((fs.filetime(source), data), file)
        if file in self._tobe_deleted_files:
            self._tobe_deleted_files.remove(file)
        if persistent:
            self._quick_fetches[(source, namespace)] = data
        return file

    def _delete_outdated_files(self) -> None:
        if self._tobe_deleted_files:
            for file in self._tobe_deleted_files:
                print(
                    ':v7i',
                    'remove outdated cache file',
                    fs.relpath(file, self._cache_root),
                )
                fs.remove(file)
            self._tobe_deleted_files.clear()


cache_maker = _CacheMaker(cache_root)
