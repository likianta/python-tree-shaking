from argsense import cli

from .export import dump_tree_from_config_file
from .graph import build_module_graphs

cli.add_cmd(build_module_graphs)


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


if __name__ == '__main__':
    cli.run()
