import tree_shaking
from lk_utils import fs

tree_shaking.dynamic_dump_tree(
    (f for m, f in tree_shaking.grab_global_modules()),
    dir_o='test/_dynamic_dumped',
    single_source_entry=fs.abspath('.venv/Lib/site-packages'),
    dry_run=True,
)
