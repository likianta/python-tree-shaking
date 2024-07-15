from os.path import isabs

from lk_utils import fs

from .path_scope import path_scope


def parse_config(file: str) -> dict:
    cfg_dir = fs.parent(fs.abspath(file))
    cfg = fs.load(file)
    out = {}
    
    cwd = out['cwd'] = (
        fs.normpath(cfg['cwd']) if isabs(cfg['cwd']) else
        fs.normpath('{}/{}'.format(cfg_dir, cfg['cwd']))
    )
    
    temp = out['search_paths'] = []
    for p in cfg['search_paths']:
        if isabs(p):
            p = fs.normpath(p)
        else:
            p = f'{cwd}/{p}'
        temp.append(p)
        path_scope.add_scope(p)
    
    temp = out['modules'] = {}
    for p, n in cfg.get('modules', {}).items():
        temp[f'{cwd}/{p}'] = n
    
    temp = out['module_graphs'] = []
    for graph_id in cfg.get('module_graphs', ()):
        graph_file = fs.xpath(f'../data/module_graphs/{graph_id}.yaml')
        assert fs.exists(graph_file), graph_id
        temp.append(graph_file)
    
    temp = out['spec_files'] = []
    for relpath in cfg.get('spec_files', ()):
        if relpath.endswith('/'):
            path = (f'{cwd}/{relpath.removesuffix("/")}', True)
        else:
            path = (f'{cwd}/{relpath}', False)
        temp.append(path)
    
    return out
