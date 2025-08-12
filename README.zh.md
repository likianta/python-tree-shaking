# Python: 基于 "树摇" 的依赖库体积瘦身术

## 工作原理

假设 A 模块依赖于 B 模块. B 模块位于 C 依赖库中. C 是通过 `pip install C` 获得的.

这意味着, 在上述假设情形中, C 目录下除 B 以外的其他文件, 可能是 A 模块不需要的.

这些文件是否可以从 C 中删去, 并且不影响 A 仍然能正常运行?

本项目是对于上述想法的验证.

就实践结果而言, 本项目发挥了出乎意料的效果, 在依赖库体积裁剪中, 降低了 ???% 的占用空间.

...

## 配置文件

`tree-shaking` 通过 YAML 格式的配置文件来完成依赖解析, 提取和瘦身工作.

配置文件提供了以下信息:

- 入口脚本在哪里
- 依赖库的搜索目录
- 应该忽略哪些包的解析

配置文件名称是任意的, 只要是符合要求的 yaml 文件即可. 文件格式如下:

```yaml
# example.yaml
root: .
search_paths:
  - <root>/.venv
  - <root>/lib
  - <root>
entries:
  - <root>/src/hello_world/main.py
```

字段详解如下:

- **root**

  定义当前项目的根目录, 可以是一个绝对路径, 也可以是一个 **相对于该配置文件** 的路径. 通常推荐使用相对路径.

  假设当前项目位于:

  ```
  /workspace/hello-world
  |= src
     |= hello_world
        |- main.py
        |- ...
  |- README.md
  |- tree_shaking_modules.yaml
  |- ...
  ```

  即, 配置文件位于 "hello-world" 根目录下. 那么 `root: .` 表示 "配置文件所在的目录为项目根目录."

  如果:

  ```
  /workspace/hello-world
  |= config
     |- tree_shaking_modules.yaml
  |= src
     |= hello_world
        |- main.py
        |- ...
  |- README.md
  |- ...
  ```

  那么 `root: ..` 表示 "配置文件的上一级目录为项目根目录."

- **search_paths**

  依赖库的搜索路径. 可以有多个, 其中, 越靠下的优先级越高.

  例如, 依赖库 "numpy" 同时存在于 `<root>/.venv/numpy` 和 `<root>/lib/numpy`, 那么前者会被忽略, 后者会被使用.

  `<root>` 是一个占位符, 在 tree-shaking 解析时, 会被替换为项目根目录的绝对路径.

- **entries**

  程序入口, 指你的程序启动时的脚本.

## 使用示例

目录结构:

```
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

配置文件 (tree_shaking.yaml) 内容:

```yaml
root: .
search_paths:
  - <root>/.venv/Lib/site-packages
  - <root>
entries:
  - <root>/hello_world/__main__.py
```

代码 (在根目录下创建一个 "build.py" 脚本):

```python
import tree_shaking
tree_shaking.build_graph_modules("./tree_shaking.yaml")
tree_shaking.dump_tree("./tree_shaking.yaml", "./dist/minified_libs")
```

运行后的目录结构:

```
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

将 `dist/minified_libs` 压缩成 zip 文件, 对比 `.venv/Lib/site-packages` 体积变化如下: ...

## 增量更新

...

### 如何禁用增量更新

对于 `tree_shaking.dump_tree`, 你需要手动删除导出目录, 然后重新调用此函数.

值得注意的是, 如果你使用 Depsland 分发你的程序, 禁用增量更新会导致 Depsland 重新完整地上传所有树摇结果, 哪怕与之前版本的文件相比内容没有变化 (即哈希值一致). 这是因为 Depsland 的快速比较策略导致的. 在最坏的情况下, 用户在升级程序时, 将花费几乎等同于重新下载完整的新版本的时间.

### 在什么情况下适合禁用增量更新?

- 你认为树摇结果出现了问题, 并且是在升级了 tree-shaking 这个包之后出现的.
- `tree-shaking : patches : implicit_imports_list.yaml` 发生了变化.

