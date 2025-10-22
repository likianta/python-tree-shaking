from lk_utils import fs


class T:
    Anypath = str
    Dirpath = str


class PathScope:
    
    def __init__(self) -> None:
        self.module_2_path = {}
        #   struct a (abandoned):
        #       {module_name: (parent, relpath, isdir), ...}
        #           parent: absolute dirpath.
        #           relpath: relative path to parent.
        #           isdir: bool
        #   struct b:
        #       {module_name: (path, isdir), ...}
        #           path: absolute, could be filepath or dirpath.
        self.path_2_module = {}
        #   {path: module_name, ...}
        #       path: absolute filepath.
    
    def add_scope(self, scope: T.Dirpath) -> None:
        """
        notice: if a module name both exists in `<scope>/<module>` and
        `self.module_2_path`, the former one takes effect.
        """
        module_2_path = {}
        path_2_module = {}
        scope = fs.abspath(scope)
        for d in fs.find_dirs(scope, filter=True):
            if '.' not in d.name:
                module_name = d.name
                module_2_path[module_name] = (d.path, True)
                path_2_module[d.path] = module_name
        for f in fs.find_files(scope, ('.py', '.pyc', '.pyd'), filter=True):
            # module_name = f.stem
            module_name = f.name.split('.', 1)[0]
            #   '_cffi_backend.cp312-win_amd64.pyd' -> '_cffi_backend'
            module_2_path[module_name] = (f.path, False)
            path_2_module[f.path] = module_name
        self.module_2_path.update(module_2_path)
        self.path_2_module.update(path_2_module)
        # sort paths from long to short
        self.path_2_module = dict(sorted(
            self.path_2_module.items(),
            key=lambda x: x[0],
            reverse=True
        ))
        # print(self.path_2_module, ':vl')
    
    def add_path(self, path: T.Anypath) -> None:
        path = fs.abspath(path)
        module_name = fs.barename(path)
        self.module_2_path[module_name] = (path, fs.isdir(path))
        self.path_2_module[path] = module_name
        # sort paths from long to short
        self.path_2_module = dict(sorted(
            self.path_2_module.items(),
            key=lambda x: x[0],
            reverse=True
        ))


path_scope = PathScope()
