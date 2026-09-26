# 资源与本地化

## 路径规则

Mod JAR 内资源路径是相对于 JAR 根目录的正斜杠路径，代码通过 `Class.getResource`、`Gdx.files.internal`、`ImageMaster` 或 BaseMod 的加载器访问。不要把 `E:\SteamLibrary...` 写进 Mod；把资源放在自己的前缀目录下，例如 `mymodResources/images/...` 和 `mymodResources/localization/eng/...`。

本机已安装 Mod 的 JAR 内资源路径可查 `environment/resource_inventory.jsonl`；JAR 外部的 Workshop 图片、音频、配置和其他文件可查 `environment/workshop_external_files.jsonl`。两者都只提供路径和指纹，不把二进制内容复制进知识库。

## 字符串

常见字符串对象包括 `CardStrings`、`RelicStrings`、`PowerStrings`、`PotionStrings`、`CharacterStrings`、`EventStrings` 和 `UIStrings`。推荐在初始化阶段使用 `BaseMod.loadCustomStrings` 或 `loadCustomStringsFile`，再用类的 `get` 方法取得对应 ID；实际 JSON 文件名和对象结构以当前 BaseMod/API 与已安装 Mod 的文本资源为准。

## 图片和动画

卡牌通常需要攻击/技能/能力的卡图；遗物需要图标和 outline；角色与怪物可能需要 Spine JSON/atlas/png。不要只改路径字符串就认为资源加载成功：同时检查资源确实在 JAR、大小/路径出现在资源索引，并从运行日志确认加载阶段没有 `FileNotFoundException` 或 Spine 解析异常。

## 中文与编码

生成器以 UTF-8 读取并写出 JSON 文本，保留 BOM 兼容读取。中文本地化文件建议保持 UTF-8，并把 `zhs`/`zht` 等语言目录与当前游戏约定对齐。AI 生成新文本时应复用现有 Mod 的字段结构，而不是把描述字符串硬编码进卡牌类。
