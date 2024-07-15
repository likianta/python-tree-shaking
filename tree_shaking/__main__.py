import hashlib

from argsense import cli
from lk_utils import fs

from . import finder
from .build import make_tree
from .config_parser import parse_config


@cli.cmd()
def dump_module_graph(script: str, base_name_o: str = None) -> None:
    result_file = fs.xpath('../data/module_graphs/{}.yaml'.format(
        base_name_o or '{}-{}'.format(
            fs.barename(script), _get_content_hash(script)[::4]
        )
    ))
    result, file = finder.dump_all_imports(script, result_file, sort=True)
    print(':v2t', 'dumped {} items. see result at "{}"'
          .format(len(result), file))


def _get_content_hash(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()


@cli.cmd()
def batch_dump_module_graphs(config_file: str) -> None:
    cfg = parse_config(config_file)
    for p, n in cfg['modules'].items():
        print(':dv2', p, n)
        dump_module_graph(p, n)


# @cli.cmd()
# def make_tree(config_file: str, output_dir: str, copyfiles: bool = False) -> None:
#     cfg = fs.load(config_file)

cli.add_cmd(make_tree)

if __name__ == '__main__':
    # pox -m sidework.tree_shaking dump-module-graph
    #   depsland/__main__.py depsland
    #       prepare: make sure `chore/site_packages` latest:
    #           pox sidework/merge_external_venv_to_local_pypi.py .
    #           pox build/init.py make-site-packages --remove-exists
    
    # pox -m sidework.tree_shaking make-tree <file_i> <dir_o>
    # pox -m sidework.tree_shaking make-tree <file_i> <dir_o> --copyfiles
    cli.run()
