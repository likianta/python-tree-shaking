# 缓存系统设计

缓存目录结构为:

```
tree_shaking
|= _cache
    |= watch_files
        |= <source_id>
            |- <thread>.pkl
            |- ...
        |= ...
```

**source_id**

source_id 是一个形如 "8fa8d279db8d36bdab46fbe26012f63b" 的字符串, 它由以下方法计算得到:

- 假设有一个固定的字符串 S, 它的 source_id 为 S 的哈希值. 也就是说 S 和它的 source_id 是固定的映射关系.
- 假设有一个文件 F, 它的 source_id 为 F 的绝对路径的哈希值.
- 假设有一个目录 D, 它的 source_id 为 D 的绝对路径的哈希值.

此外, 以上三种情况的组合, 也能作为 source_id, 比如, 我可以传入 `(S, F, D)`, 则它的 source_id 为 `get_hash(f'{S};{F};{D}')`.

不管哪种方法计算的 source_id, 其长度都是 32. 所以 watch_files 目录下, 你会看到成百上千个形如 "8fa8d279db8d36bdab46fbe26012f63b" (32 个字符) 的目录.

**thread**

thread 可以理解为一个特定的话题, 讨论的是关于这个 source_id 的某个议题.

例如, 文件 F 可以有多个话题:

```
tree_shaking
|= _cache
    |= watch_files
        |= <F_source_id>
            |- ast_parsing_results.pkl  # 这些都是话题.
            |- module_graphs.pkl
            |- module_trace.pkl
            |- ...
```

一个 thread 是一个 ".pkl" 文件, 它的内容结构为:

```
(<revision_number>, <data>)  
#   see also `tree_shaking/cache.py : _CacheMaker : get_cache : if fs.exists : 
#   last_revision, data = fs.load(file)`.
```

这是一个元组对象, 有两个元素, 第一个是修订号 (str 类型), 第二个是数据 (any 类型).

`data` 的具体类型取决于该话题的制定者想要什么数据, 这里按下不表. 我们重点看 `revision_number`.

revision_number 由以下方法计算得到:

- 对于一个固定的字符串 S, 它的 revision_number 为 S 的哈希值.
- 对于一个文件 F, 它的 revision_number 为 F 的修改时间的哈希值.
- 对于一个目录 D, 它的 revision_number 为 D 的递归所有子文件的修改时间的最大值的哈希值.
- 支持以上三者的任意组合, 比如, `(S, F, D)`, 则它的 revision_number 为 `get_hash(f'{S_fixed};{F_mtime};{D_recursive_max_mtime}')`.

这是本系统有趣的部分. S, F, D 采用了截然不同的计算方式, 对于调用者来说, 它显著降低了心智负担:

**调用者只需要指定一个来源, 而不需要关心来源是否已经被缓存过, 缓存系统会根据来源类型 (S/F/D) 来计算 source_id 和 revision_number, 以此判断是否存在缓存以及缓存是否过期.**

于是, 对于一个 F 文件, 当它未曾被修改过, 则修订号保持不变, 调用者哪怕多次调用, 拿到的都是同一个缓存结果 -- 缓存机制总是生效中.

一旦文件发生变化, 修订号会发生变化 (但 source_id 不会变), 因此缓存系统知道, 原先缓存的数据过期了. 当调用者下次调用时, 缓存系统会告诉对方, 缓存数据已失效, 你需要重新计算.
