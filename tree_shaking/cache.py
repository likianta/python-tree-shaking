"""
Doc: docs/the-cache-system.zh.md
"""

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
    #   - valid file path
    #   - valid directory path
    #   - any other string (we call it "solid factor")
    #   to let cache maker recognize them, use ':0' for solid factor, ':1' for
    #   file path, and ':2' for directory path.
    #   trick: if you mark a dir path with ':1', it will read the folder mtime
    #   instead of recursively reading all subfiles' mtimes.
    #   see also `_CacheMaker:_parse_source_factors`.
    SourceId = str

    InitialFactor = tp.Union[SourceFactor, tp.Iterable[SourceFactor]]
    ImpactFactors = tp.Iterable[SourceFactor]


EMPTY_FACTOR = '_0'


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

_CACHE_VERSION = '1'
#   a simple string of digit, if we change it (usually increment it), all
#   existing cache files will be invalidated.
#   TODO: we may remove `_CacheMaker.invalidate_cache` method, and use this
#   mechanism instead.


class _CacheMaker:
    def __init__(self, cache_root: str) -> None:
        self._bad_mode = False  # DELETE
        self._cache_root = cache_root
        self._quick_fetches = {}
        self._sanitized_files = set()
        self._tobe_deleted_files = set()
        atexit.register(self._delete_outdated_files)

    def is_cached(
        self,
        initiator: T.InitialFactor,
        impact_factors: T.ImpactFactors,
        thread: str,
    ) -> bool:
        (init_id, init_rev), (impact_id, impact_rev), (dir0, dir1, file) = (
            self._parse_factor_args(initiator, impact_factors, thread)
        )
        if file in self._tobe_deleted_files:
            return False
        elif self._bad_mode and file not in self._sanitized_files:
            return False
        else:
            if fs.exist(file):
                last_init_rev: str = fs.load('{}/revision.pkl'.format(dir0))
                if last_init_rev == init_rev:
                    last_impact_rev: str = fs.load(
                        '{}/revision.pkl'.format(dir1)
                    )
                    if last_impact_rev == impact_rev:
                        return True
                self._tobe_deleted_files.add(file)
            return False

    def invalidate_cache(self) -> None:
        """
        mark all existing cache files invalid.
        """
        self._bad_mode = True
        self._sanitized_files.clear()

    def get_cache(
        self,
        initiator: T.InitialFactor,
        impact_factors: T.ImpactFactors,
        thread: str,
        persistent: bool = False,
    ) -> tp.Optional[tp.Any]:
        """
        Args:
            thread: Characters must be valid filename pattern (without
                extension).
        Notice: The return value may be an empty list, empty dict or something.
        You should not use the bare pattern of `if data: ...` to check it.
        """
        (init_id, init_rev), (impact_id, impact_rev), (dir0, dir1, file) = (
            self._parse_factor_args(initiator, impact_factors, thread)
        )

        # negative check
        if file in self._tobe_deleted_files:
            return None
        elif self._bad_mode and file not in self._sanitized_files:
            return None

        if fs.exist(file):
            # assert fs.exist('{}/revision.pkl'.format(dir0))
            # assert fs.exist('{}/revision.pkl'.format(dir1))
            last_init_rev: str = fs.load('{}/revision.pkl'.format(dir0))
            if last_init_rev == init_rev:
                last_impact_rev: str = fs.load('{}/revision.pkl'.format(dir1))
                if last_impact_rev == impact_rev:
                    data: tp.Any = fs.load(file)
                    if persistent:
                        self._quick_fetches[(init_id, impact_id, thread)] = data
                    return data
            self._tobe_deleted_files.add(file)
        return None

    def save_cache(
        self,
        initiator: T.InitialFactor,
        impact_factors: T.ImpactFactors,
        thread: str,
        data: tp.Any,
        persistent: bool = False,
    ) -> str:
        (init_id, init_rev), (impact_id, impact_rev), (dir0, dir1, file) = (
            self._parse_factor_args(initiator, impact_factors, thread)
        )

        if not fs.exist(dir1):
            fs.make_dirs(dir1)
        fs.dump(init_rev, '{}/revision.pkl'.format(dir0))
        fs.dump(impact_rev, '{}/revision.pkl'.format(dir1))
        fs.dump(data, file)

        if self._bad_mode:
            self._sanitized_files.add(file)
        if file in self._tobe_deleted_files:
            self._tobe_deleted_files.remove(file)

        if persistent:
            self._quick_fetches[(init_id, impact_id, thread)] = data
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

    def _parse_factor_args(
        self,
        initiator: T.InitialFactor,
        impact_factors: T.ImpactFactors,
        thread: str,
    ) -> tp.Tuple[
        tp.Tuple[T.SourceId, T.RevisionNumber],
        tp.Tuple[T.SourceId, T.RevisionNumber],
        tp.Tuple[str, str, str],
    ]:
        init_id, init_rev = self._parse_source_factors(initiator)

        dir0_type: tp.Literal['0', '1', '2', '3']
        if isinstance(initiator, str):
            dir0_type = initiator[-1]  # type: ignore
        else:
            xs = ''.join(sorted(frozenset(x[-1] for x in initiator)))
            assert xs in ('0', '1', '2', '01', '02', '12', '012'), (
                initiator,
                xs,
            )
            if xs in ('0', '1', '2', '01', '02'):
                dir0_type = xs[-1]  # type: ignore
            else:  # '12', '012'
                dir0_type = '3'

        dir0 = '{}/watch_files/{}-{}'.format(
            self._cache_root, dir0_type, init_id
        )
        impact_id, impact_rev = self._parse_source_factors(impact_factors)
        dir1 = '{}/{}'.format(dir0, impact_id)
        file = '{}/{}.pkl'.format(dir1, thread)
        return (init_id, init_rev), (impact_id, impact_rev), (dir0, dir1, file)

    # def _parse_source_factor(
    #     self, factor: T.SourceFactor
    # ) -> tp.Tuple[T.SourceId, T.RevisionNumber]:
    #     assert factor.endswith((':0', ':1', ':2'))
    #     if factor.endswith(':0'):
    #         return uuid(factor[:-2]), uuid(factor[:-2] + ';' + _CACHE_VERSION)
    #     elif factor.endswith(':1'):
    #         return uuid(factor[:-2]), uuid(
    #             str(fs.mtime(factor[:-2])) + ';' + _CACHE_VERSION
    #         )
    #     else:  # ':2'
    #         return uuid(factor[:-2]), uuid(
    #             str(fs.mtime(factor[:-2], recursive=True))
    #             + ';'
    #             + _CACHE_VERSION
    #         )

    def _parse_source_factors(
        self, any_factor: tp.Union[T.SourceFactor, tp.Iterable[T.SourceFactor]]
    ) -> tp.Tuple[T.SourceId, T.RevisionNumber]:
        # note: `any_factor` may be empty... but we do not suggest this form, 
        # instead, please use `EMPTY_FACTOR`.
        factors = (
            (EMPTY_FACTOR,)
            if not any_factor
            else (any_factor,)
            if isinstance(any_factor, str)
            else any_factor
        )

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
