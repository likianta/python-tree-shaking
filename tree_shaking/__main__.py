from argsense import cli

from .export import dump_tree_from_config_file
from .graph import build_module_graphs

cli.add_cmd(build_module_graphs)
cli.add_cmd(dump_tree_from_config_file, 'dump-tree')

if __name__ == '__main__':
    cli.run()
