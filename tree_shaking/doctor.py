import lk_utils
from argsense import cli
from lk_utils import fs


@cli.cmd()
def check_lk_utils(graph_id: str) -> None:
    dir0 = fs.normpath(lk_utils.__path__[0])
    files0 = []
    for f in fs.findall_files(dir0, filter=True):
        files0.append(f.relpath)
    
    files1 = []
    for k, v in fs.load(fs.xpath(
        '_cache/module_graphs/{}.yaml'.format(graph_id)
    )).items():
        if k.startswith('lk_utils'):
            files1.append(v.split('/lk_utils/')[1])
    
    print(set(files0) - set(files1), ':l')
    #   if the difference is:
    #       {'__main__.py', 'subproc/multiprocess.py'}
    #   then it's OK
    
    if x := set(files1) - set(files0):  # this must be empty!
        print(x, ':lv4')


if __name__ == '__main__':
    # pox tree_shaking/doctor.py check-lk-utils ...
    cli.run()
