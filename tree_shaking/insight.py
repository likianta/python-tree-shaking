import typing as tp

import neoprint as np
from lk_utils import fs

from .cache import cache_maker
from .file_parser import T as T0
from .finder import Finder
from .path_typing import T as T1


class T(T1):
    Module = T0.ModuleInfo
    ModuleFullName = str
    ModuleGraph = tp.Dict[ModuleFullName, tp.Sequence[ModuleFullName]]
    DumpedModuleGraph = tp.TypedDict(
        'DumpedModuleGraph',
        {'initial_imports': tp.List[ModuleFullName], 'graph': ModuleGraph},
    )


def trace(entry_script: T.AnyFilePath, target_module: T.ModuleFullName) -> None:
    x = trace_all(entry_script, _quiet=True)
    initial_imports = x['initial_imports']
    graph = x['graph']

    _visited = set()

    def find_in_graph(curr_list, parent):
        for mod in curr_list:
            if mod == target_module:
                yield '{} -> {}'.format(parent, mod)
                break
            elif mod not in _visited:
                _visited.add(mod)
                if mod in graph:
                    yield from find_in_graph(
                        graph[mod], '{} -> {}'.format(parent, mod)
                    )

    result = []
    for mod in initial_imports:
        assert mod in graph
        result.extend(find_in_graph(graph[mod], mod))
    if result:
        assert len(result) < 500  # in case printing too long
        for clue in sorted(result):
            parts = clue.split(' -> ')
            for i, p in enumerate(parts):
                print(':s', '{}-> {}'.format('  ' * (i + 1), p))
    else:
        print('target not found', target_module)


def trace_all(
    entry_script: T.AnyFilePath,
    _check_if_cached: bool = True,
    _quiet: bool = False,
) -> T.DumpedModuleGraph:
    entry_script = fs.abspath(entry_script)
    if (
        x := cache_maker.get_cache(entry_script + ':1', 'module_trace')
    ) is not None:
        if not _quiet:
            print('already cached', ':v4')
        return x
    else:
        with np.scope():
            graph = {}
            initial_imports = []
            _trace_all(entry_script, graph, initial_imports)
        result: T.DumpedModuleGraph = {
            'initial_imports': initial_imports,
            'graph': graph,
        }
        print(len(result), ':n')
        cache_maker.save_cache(entry_script + ':1', 'module_trace', result)
        return result


_finder = Finder()


def _trace_all(
    entry_script: T.AbsFilePath,
    result_holder: T.ModuleGraph,
    list_holder: tp.List[T.ModuleFullName],
) -> T.ModuleGraph:
    for m0, p0 in _finder.get_direct_imports(entry_script):
        assert m0.full_name
        list_holder.append(m0.full_name)
        if m0.full_name not in result_holder:
            print(m0.full_name, ':i2n')
            x0 = result_holder[m0.full_name] = []
            if p0.endswith('.py'):
                _trace_all(p0, result_holder, x0)
    return result_holder
