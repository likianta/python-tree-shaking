import atexit
import os
import typing as tp

from lk_utils import fs
from lk_utils import uuid


class T:
    RevisionNumber = str
    SourceFactor = str
    #   source factor is a string with suffix ':0', ':1' or ':2'.
    #   the string has three types:
    #   1. valid file path
    #   2. valid directory path
    #   3. any other string (we call it "solid factor")
    #   to let cache maker recognize them, use ':0' for solid factor, ':1' for
    #   file path, and ':2' for directory path.
    #   trick: if you mark a dir path with ':1', it will read the folder mtime
    #   instead of recursively reading all subfiles' mtimes.
    #   see also `_CacheMaker:get_cache:source_factors`.
    AnySourceFactors = tp.Union[str, tp.Iterable[SourceFactor]]
    SourceId = str


def _init_cache_root() -> str:
    if path := os.getenv('TREE_SHAKING_CACHE_ROOT'):
        assert fs.exist(path), path
        print(':v', 'get tree-shaking cache root from environment', path)
        if not fs.exist('{}/.init_ok'.format(path)):
            fs.copy_file(
                fs.here('_cache/ignores.txt'), '{}/ignores.txt'.format(path)
            )
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

_CACHE_VERSION = '0'
#   a simple string of digit, if we change it (usually increment it), all
#   existing cache files will be invalidated.
#   TODO: we may remove `_CacheMaker.invalidate_cache` method, and use this
#   mechanism instead.


class _CacheMaker:
    def __init__(self, cache_root: str) -> None:
        self._bad_mode = False
        self._cache_root = cache_root
        self._quick_fetches = {}
        self._sanitized_files = set()
        self._tobe_deleted_files = set()
        atexit.register(self._delete_outdated_files)

    def is_cached(
        self, source_factors: T.AnySourceFactors, thread: str
    ) -> bool:
        source_id, revision = self._parse_source_factors(source_factors)
        file = '{}/watch_files/{}/{}.pkl'.format(
            self._cache_root, source_id, thread
        )
        if file in self._tobe_deleted_files:
            return False
        elif self._bad_mode and file not in self._sanitized_files:
            return False
        else:
            file = '{}/watch_files/{}/{}.pkl'.format(
                self._cache_root, source_id, thread
            )
            if fs.exist(file):
                last_revision = fs.load(file)[0]
                if last_revision == revision:
                    return True
                else:
                    self._tobe_deleted_files.add(file)
                    return False
            else:
                return False

    def invalidate_cache(self) -> None:
        """
        mark all existing cache files invalid.
        """
        self._bad_mode = True
        self._sanitized_files.clear()

    def get_cache(
        self,
        source_factors: T.AnySourceFactors,
        thread: str,
        persistent: bool = False,
    ) -> tp.Optional[tp.Any]:
        """
        thread: characters must be valid filename pattern (without extension).
        notice: the return value may be empty list, empty dict or something.
        you should not use generic `if data: ...` to check it.
        """
        source_id, revision = self._parse_source_factors(source_factors)

        if persistent and (source_id, thread) in self._quick_fetches:
            return self._quick_fetches[(source_id, thread)]

        file = '{}/watch_files/{}/{}.pkl'.format(
            self._cache_root, source_id, thread
        )
        if file in self._tobe_deleted_files:
            return None
        if self._bad_mode and file not in self._sanitized_files:
            return None
        if fs.exist(file):
            last_revision, data = fs.load(file)
            if last_revision == revision:
                if persistent:
                    self._quick_fetches[(source_id, thread)] = data
                return data
            else:
                self._tobe_deleted_files.add(file)
                return None
        else:
            return None

    def save_cache(
        self,
        source_factors: T.AnySourceFactors,
        thread: str,
        data: tp.Any,
        persistent: bool = False,
    ) -> str:
        source_id, revision = self._parse_source_factors(source_factors)
        file = '{}/watch_files/{}/{}.pkl'.format(
            self._cache_root, source_id, thread
        )
        if not fs.exist(fs.parent(file)):
            fs.make_dir(fs.parent(file))
        fs.dump((revision, data), file)
        if self._bad_mode:
            self._sanitized_files.add(file)
        if file in self._tobe_deleted_files:
            self._tobe_deleted_files.remove(file)
        if persistent:
            self._quick_fetches[(source_id, thread)] = data
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

    def _parse_source_factors(
        self, factors: tp.Union[str, tp.Iterable[T.SourceFactor]]
    ) -> tp.Tuple[T.SourceId, T.RevisionNumber]:
        if isinstance(factors, str):
            factors = (factors,)
        assert all(x.endswith((':0', ':1', ':2')) for x in factors)
        source_id = uuid(';'.join(x[:-2] for x in factors))
        revision = uuid(
            ';'.join(
                map(
                    str,
                    (
                        x[:-2]
                        if x.endswith(':0')
                        else fs.mtime(x[:-2])
                        if x.endswith(':1')
                        else fs.mtime(x[:-2], recursive=True)
                        for x in factors
                    ),
                )
            )
            + ';'
            + _CACHE_VERSION
        )
        return source_id, revision


cache_maker = _CacheMaker(cache_root)
