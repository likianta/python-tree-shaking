from lk_utils import fs

from .config import parse_config
from .finder import get_all_imports

graph_dir = fs.xpath('../data/module_graphs')


def dump_module_graph(script: str, graph_id: str, sort: bool = True) -> str:
    file_i = fs.abspath(script)
    file_o = '{}/{}.yaml'.format(graph_dir, graph_id)
    
    result = dict(get_all_imports(file_i))
    if sort:
        result = dict(sorted(result.items()))
    # for module in result:
    #     print(':i', module)
    fs.dump(result, file_o)
    
    print(
        ':v2t', 'dumped {} items. see result at "{}"'
        .format(len(result), file_o)
    )
    return file_o


def batch_dump_module_graphs(config_file: str) -> None:
    cfg = parse_config(config_file)
    for p, n in cfg['modules'].items():
        print(':dv2', p, n)
        dump_module_graph(p, n)
