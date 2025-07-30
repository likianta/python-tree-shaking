import os
from argsense import cli
from lk_utils import fs
from lk_utils import run_cmd_args

from .export import dump_tree
from .graph import build_module_graphs
from .graph import build_module_graph


@cli.cmd()
def check_if_patch_worked(target_project: str):
    os.environ.pop('VIRTUAL_ENV')
    venv_root = run_cmd_args(
        'poetry', 'env', 'info', '--path', cwd=target_project
    )
    site_packages_dir = '{}/Lib/site-packages'.format(venv_root)
    assert fs.exist(site_packages_dir)
    
    patch = fs.load(fs.xpath('patches/implicit_import_hooks.yaml'))
    for k, v in patch.items():
        if 'files' in v:
            for item in v['files']:
                if isinstance(item, str):
                    pass


cli.add_cmd(build_module_graphs)
cli.add_cmd(build_module_graph)
#   FIXME: cannot use this commnad, `path_scope` won't be updated because no
#       given config file.
#       related:
#           tree_shaking.config.parse_config : [code] path_scope.add_scope(p)
#           tree_shaking.path_scope.path_scope.add_scope
cli.add_cmd(dump_tree)

if __name__ == '__main__':
    # pox -m tree_shaking build-module-graph depsland/__main__.py depsland
    #       prepare: make sure `chore/site_packages` latest:
    #           pox sidework/merge_external_venv_to_local_pypi.py .
    #           pox build/init.py make-site-packages --remove-exists
    
    # pox -m tree_shaking build-module-graphs demo_config/modules.yaml
    
    # pox -m tree_shaking dump-tree <file_i> <dir_o>
    # pox -m tree_shaking dump-tree <file_i> <dir_o> --copyfiles
    cli.run()
