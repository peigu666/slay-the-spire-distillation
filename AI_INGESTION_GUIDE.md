# Slay the Spire Mod AI 知识包

这是从本机 Slay the Spire Java 安装和已安装 Mod JAR 生成的、面向 Mod 开发与排错的可查询资料包。它对应生成时的具体文件指纹，不宣称覆盖所有版本。

## 当前基线

- 本体 JAR：`desktop-1.0.jar`，SHA-256：`CFAD868AC8D65A88E71A0BF096FB09F78811E553EFFE0787C5309A655E081673`
- 生成时本体目录：`E:\SteamLibrary\steamapps\common\SlayTheSpire`（仅审计信息；使用时以 `environment/jar_inventory.jsonl` 的 `portable_path` 为准）
- 本体 `com.megacrit.cardcrawl.*`：2306 个类，12696 个方法，13678 个字段
- ModTheSpire 元数据 `mts_version`：999.999.999（该 JAR 的元数据标记，不等同于发布版本号）
- BaseMod：5.56.0
- StSLib：2.12.0
- 生成器 Java 运行时：`java version "1.8.0_144"`

## 给 AI 的读取顺序

1. 先读本文件和 `manifest.json`，确认这是哪一套 JAR。
2. 需要查本体类时，查 `api/base_game_api.types.jsonl`；需要编译 API 时分别查 `api/modthespire_api.types.jsonl`、`api/basemod_api.types.jsonl`、`api/stslib_api.types.jsonl`。
3. 需要理解本机已经装了什么 Mod 时，查 `environment/mod_catalog.json` 和 `api/installed_mods_api.types.jsonl`；Mod 的 `ModTheSpire.json` 元数据、注解和资源路径也被索引。
4. 遇到版本、类路径、资源路径或依赖问题，先查 `environment/jar_inventory.jsonl`、`environment/resource_inventory.jsonl` 和 `environment/workshop_manifest.json`。
5. 需要快速定位类/成员时，用 `tools/query-sts-api.ps1`；需要判断当前 JAR 是否仍与本包一致时，用 `tools/verify-sts-pack.ps1`。

## 证据优先级

`api/*.types.jsonl` 中的当前 JAR 结构 > 本机 JAR 的 SHA-256 与元数据 > 本机运行日志和构建结果 > 参考 Mod 的调用模式 > AI 的记忆或旧教程。不要把不同版本的 `desktop-1.0.jar`、ModTheSpire、BaseMod 或 StSLib 混在一起；同名方法必须以描述符和当前 JAR 为准。

## 文档导航

- `docs/MODDING_WORKFLOW.md`：从空项目到能加载的最小 Mod。
- `docs/API_MAP.md`：卡牌、遗物、能力、药水、角色、怪物、战斗动作、事件和 UI 的类图入口。
- `docs/PATCHING_GUIDE.md`：ModTheSpire 注解、Locator、插入/前后缀/替换/字节码补丁。
- `docs/RESOURCE_AND_LOCALIZATION.md`：资源、语言包和 `loadCustomStrings` 的路径规则。
- `docs/TROUBLESHOOTING.md`：日志、依赖、Java 版本和常见加载失败的证据化排查顺序。
- `sts_ai_knowledge_report.html`：无需服务器、双击即可使用的离线类/成员浏览器。
- `templates/`：不依赖绝对路径的最小 Java 8 Mod 模板。

## 边界

- 本包没有复制游戏 JAR、图片、音频或存档，只记录它们的哈希、类签名和资源索引；这样可以避免把资料包绑定到生成机的绝对路径，也避免把大体积二进制重复分发。
- 类记录包含私有成员和方法代码长度/哈希，但不等同于可读的 Java 源码；行为判断需要结合局部 `javap -c`、运行日志或实际编译/运行结果。
- `installed_mods` 是生成时本机目录中的快照；创意工坊更新后必须重新生成并重新校验。
