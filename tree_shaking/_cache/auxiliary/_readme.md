## About

This directory is for `tree-shaking:export` to check if files changed.

Since `tree-shaking:export` currently can only detect files that are added or 
deleted, but not for files that are "existent but have content-updated". We use 
this directory to record this infomation.

## How is it created?

Graph dumper cached all files' ast info with its content hash id. When file 
content is changed, it gets a new id, so that we know it is "content-changed" 
file.

The changed files list will be saved to `./<root_hash>.pkl`.

## How is it used?

Tree dumper reads `../dumped_resources_maps/<root_hash>.pkl` and 
`./<root_hash>.pkl` (their `<root_hash>`s are same), after all additions and 
deletions done, it checks the content-updated list and redo symlinks, which 
makes folder modification time updated.

The [depsland](https://github.com/likianta/depsland) will find out the changed 
assets by checking their modification times.

## Related code

- `/tree_shaking/graph.py : build_module_graphs`
- `/tree_shaking/cache.py : FileNodesCache : _new_files`
- `/tree_shaking/export.py : _incremental_updates`
