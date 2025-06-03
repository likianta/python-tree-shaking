# Python Tree Shaking

[中文版](./README.zh.md)

*English README is under construction.*

## Install

```sh
pip install tree-shaking
```

Be noted `tree-shaking` requires Python >= 3.12.

## Usage

Project tree (before):

```sh
# my example project
/workspace/hello-world
|= .venv
|= hello_world
   |- __init__.py
   |- __main__.py
   |- ...
|= dist
|- pyprojet.toml
|- tree_shaking.yaml
|- ...
```

"tree_shaking.yaml" content:

```yaml
root: .
search_paths:
  - <root>/.venv/Lib/site-packages
  - <root>
entries:
  - <root>/hello_world/__main__.py
```

Create a temporary script (e.g. "build.py"), code like this:

```python
import tree_shaking
tree_shaking.build_graph_modules("./tree_shaking.yaml")
tree_shaking.dump_tree("./tree_shaking.yaml", "./dist/minified_libs")
```

After running, the project tree changes:

```sh
# my example project
/workspace/hello-world
|= .venv
|= hello_world
   |- __init__.py
   |- __main__.py
   |- ...
|= dist
   |= minified_libs  # updated
      |= ...
|- pyprojet.toml
|- tree_shaking.yaml
|- ...
```

You can temporarily exclude ".venv/Lib/site-packages", and add "dist/minified_libs" to Python's `sys.path` (put it at the first place) to test if worked.

After testing, compress "dist/minified_libs" to zip, and compare its size with ".venv/Lib/site-packages" -- the more heavy dependencies you have, the more notable changes on size reduction.

## Incremental Updates

Just rerun "build.py", outputs results to the same path as last time, `tree-shaking` will find the changed parts and do only necessary adding/deleting operations to the target directory.

