import neoprint as np
from argsense import cli
from lk_utils import fs
from neoprint import print

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
    entry_script: str,
    target_module: str,
    search_paths: str = '$venv;$proj;$entry',
    concise: bool = False,
) -> None:
    """
    Args:
        entry_script (-e):
        target_module (-t):
        search_paths (-s):
        concise (-c):
    """

    entry_script = fs.abspath(entry_script)

    def get_entry_dir():
        return fs.parent(entry_script)

    def get_proj_dir():
        temp_dir = fs.parent(entry_script)
        while True:
            if fs.exist('{}/pyproject.toml'.format(temp_dir)):
                return temp_dir
            else:
                temp_dir = fs.parent(temp_dir)

    def get_venv_dir():
        temp_dir = fs.parent(entry_script)
        while True:
            if fs.exist('{}/.venv'.format(temp_dir)):
                assert fs.exist('{}/.venv/Lib/site-packages'.format(temp_dir))
                return '{}/.venv/Lib/site-packages'.format(temp_dir)
            else:
                temp_dir = fs.parent(temp_dir)

    scopes = set()
    for p in search_paths.split(';'):
        if p[0] == '$':
            a, b = p.split('/', 1) if '/' in p else (p, '')
            c = (
                get_entry_dir()
                if a == '$entry'
                else get_proj_dir()
                if a == '$proj'
                else get_venv_dir()
            )
            scopes.add(c)
            if b:
                scopes.add(c + '/' + b)
        else:
            scopes.add(fs.abspath(p))
    print(sorted(scopes), ':nl')
    for p in sorted(scopes):
        path_scope.add_scope(p)

    with np.scope('tracing'):
        insight.trace(entry_script, target_module, concise=concise)


cli.add_cmd(build_module_graphs)
cli.add_cmd(dump_tree)
cli.add_cmd(trace)


if __name__ == '__main__':
    cli.run()
