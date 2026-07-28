# 使用 pyinstaller-contrib-hooks 处理非常规依赖

> 讨论: https://chatgpt.com/share/6a682186-bec0-83e8-89e1-e242f714f35f

## 结论

我不打算支持 `PyInstaller/hooks/hook-*.py` 以及 `_pyinstaller_hooks_contrib/stdhooks/hook-*.py`, 后续仍然以自定义的 YAML (`tree_shaking/patches/implicit_import_hooks.yaml`) 格式为准. 该决定将持续到某些条件发生变化为止, 具体见下文 ([跳转](#260728143443)).

目前已经有常见的科学计算库被粗略地解决了, 处于 "可用" 状态.

对于后续的发展, 特别是对于那些非常规的依赖的处理, 我会结合下面两个方案一起进行:

1. 测试 - 发现问题 - 完善 implicit_import_hooks.yaml - 重试 - 直到所有问题解决.
2. 参考 pyinstaller hooks, 将它们人工转译为我的 implicit_import_hooks.yaml 格式.

## 现有的 YAML 格式设计评估

优点:

1. 静态元信息, 不需要 python 执行
2. 部分支持模糊匹配
3. 简单高效

缺点:

1. 对于复杂且特殊的依赖, 前期需要大量试错, 低效且开发体验痛苦
2. 不支持版本变体, 特别是跨大版本的变化, 目前只有最新的版本才能得到最佳效果, 考虑到个人精力, 未来也不打算支持多版本
3. 可能包含冗余文件

<span id="260728143443"></span>

## 我会在何时改变该决定

当以下条件全部或大部分满足时, 将促使我改变现有的结论:

- [ ] PyInstaller 提供可用的 API, 方便我在非打包模式下提取并裁剪依赖树
- [ ] AI Agent 在此议题上独立且出色地完成大部分关键的底层工作
- [ ] 本项目开始变得流行, 有大量用户提出此类需求
- [ ] 有专业的开发者参与本项目, 并着力解决该问题
- [ ] Hooks 格式不再是自由散漫的 Python 脚本, 而是静态元信息文件 (JSON, YAML or TOML)
