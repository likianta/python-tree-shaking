import typing as t

from lk_utils import fs


class Patch:
    def __init__(self, hooks_file: str) -> None:
        hooks = fs.load(hooks_file)

        # {
        #   module: {
        #       'imports': (relpath, ...),
        #       'files': (relpath | relpaths, ...)
        #       #   relpaths: [relpath, ...]
        #       #       one of them should be existed in target folder.
        #       #       there may be None in the list, means it doesn't matter -
        #       #       if none of them existed.
        #   }, ...
        # }
        self._patches = {}
        for k, v in hooks.items():
            self._patches[k] = {
                'files': tuple(v.get('files', ())),
                'imports': tuple(v.get('imports', ())),
            }

    def __contains__(self, module_name: str) -> bool:
        return module_name in self._patches

    def __getitem__(self, module_name: str) -> t.TypedDict(
        'PatchItem', {'files': t.Tuple[str, ...], 'imports': t.Tuple[str, ...]}
    ):
        return self._patches[module_name]


implicit_hooks_file = fs.here('patches/implicit_import_hooks.yaml')
patch = Patch(implicit_hooks_file)
