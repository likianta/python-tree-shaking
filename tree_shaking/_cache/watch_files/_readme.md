Tree shaking tries its best to reuse every thing that was calculated before, 
since the calculation is expensive.

## About This Folder

Folder structure:

```
tree_shaking/
|= _cache/
    |= watch_files/
        |- _readme.md   # this file
        |= <id>
            |- <namespace>.pkl
                # data structure: `(timestamp, data)`.
                # see also `../cache2.py`.
```
