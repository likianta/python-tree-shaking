"""
step 1:
    source folder   target folder
    |- a            |- a  # from source.a
    |- b            |- b  # from source.b
step 2:
    delete source.a
    rename source.b to source.a
step 3:
    - does target.a exist?
"""
import os
from lk_utils import fs
from lk_utils import timestamp

test_root = fs.xpath('_test_root_{}'.format(timestamp('hns')))
print(fs.basename(test_root), ':v1')

fs.make_dir(test_root)
fs.make_dir(test_root + '/source')
fs.make_dir(test_root + '/target')

a0 = f'{test_root}/source/a.txt'
a1 = f'{test_root}/target/a.txt'
b0 = f'{test_root}/source/b.txt'
b1 = f'{test_root}/target/b.txt'

fs.dump('aaa', a0)
fs.dump('bbb', b0)

fs.make_link(a0, a1)
fs.make_link(b0, b1)
print(
    os.path.realpath(a1),
    fs.exist(a1),
    fs.real_exist(a1),
    fs.issame(a1, a0),
    ':il'
)

fs.remove_file(a0)
print(
    os.path.realpath(a1),
    fs.exist(a1),
    fs.real_exist(a1),
    fs.issame(a1, a0),
    ':il'
)

fs.make_link(b0, a1, True)
print(
    os.path.realpath(a1),
    fs.exist(a1),
    fs.real_exist(a1),
    fs.issame(a1, a0),
    fs.issame(a1, b0),
    ':il'
)

print('remove test folder', fs.basename(test_root), ':v7')
fs.remove_tree(test_root)
