import neoprint as np
from argsense import cli
from lk_utils import fs

from . import insight
from .export import dump_tree_from_config_file
from .graph import build_module_graphs
from .path_scope import path_scope


def dump_tree(config_file: str, dir_o: str = '', dry_run: int = 0) -> None:
    """
    params:
        dir_o (-o):
        dry_run (-d):
    """
    dump_tree_from_config_file(
        config_file,
        dir_o,
        dry_run=dry_run,  # type: ignore
    )


def trace(
    entry_script: str, target_module: str, search_paths: str = '$venv'
) -> None:
    entry_script = fs.abspath(entry_script)
    for p in search_paths.split(';'):
        if p == '$venv':
            temp_dir = fs.parent(entry_script)
            while True:
                if fs.exist('{}/.venv'.format(temp_dir)):
                    assert fs.exist(
                        '{}/.venv/Lib/site-packages'.format(temp_dir)
                    )
                    p = '{}/.venv/Lib/site-packages'.format(temp_dir)
                    np.print('add venv to scope', p, ':v')
                    path_scope.add_scope(p)
                    path_scope.add_scope(temp_dir)
                    break
                else:
                    temp_dir = fs.parent(temp_dir)
        else:
            path_scope.add_scope(fs.abspath(p))
    with np.scope('tracing'):
        insight.trace(entry_script, target_module)


cli.add_cmd(build_module_graphs)
cli.add_cmd(dump_tree)
cli.add_cmd(trace)


if __name__ == '__main__':
    cli.run()
