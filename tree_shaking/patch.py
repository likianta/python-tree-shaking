import typing as t

from lk_utils import fs


class Patch:
    
    def __init__(self) -> None:
        # cfg_dir = fs.xpath('../patches')
        # cfg = fs.load(f'{cfg_dir}/implicit_imports_list.yaml')
        cfg = fs.load(fs.xpath('../patches/implicit_imports_list.yaml'))
        
        # {module: {'imports': (relpath, ...), 'files': (relpath, ...)}, ...}
        # # {module: (abspath, ...), ...}
        # #   abspath: if endswith '/', it's a dir, else it's a file.
        # # {module: (relpath, ...), ...}
        self._patches = {}
        for k, v in cfg.items():
            self._patches[k] = {
                'files': tuple(v.get('files', ())),
                'imports': tuple(v.get('imports', ()))
            }
    
    def __contains__(self, module_name: str) -> bool:
        return module_name in self._patches
    
    def __getitem__(self, module_name: str) -> t.TypedDict('PatchItem', {
        'files': t.Tuple[str, ...], 'imports': t.Tuple[str, ...]
    }):
        return self._patches[module_name]


patch = Patch()
