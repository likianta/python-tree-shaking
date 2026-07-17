from argsense import cli

from .export import dump_tree
from .graph import build_module_graphs

cli.add_cmd(build_module_graphs)
cli.add_cmd(dump_tree)

if __name__ == '__main__':
    cli.run()
