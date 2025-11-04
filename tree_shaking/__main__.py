from argsense import cli
from .export import dump_tree
from .graph import build_module_graphs
from .graph import build_module_graph

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
