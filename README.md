# Slay the Spire 蒸馏

面向 AI 的《Slay the Spire》（杀戮尖塔）Java Mod 开发知识库。它把本机游戏、ModTheSpire、BaseMod、StSLib、已安装 Mod 和第三方 Java API 整理成可检索的 JSONL 索引，并附带 Workshop 外置文件指纹、补丁目标 `javap -c` 快照、指令级 JVM bytecode、查询校验工具、构建模板和离线浏览报告。

这个仓库不是游戏本体，也不是 Mod 安装包。它的目标是让 AI 在编写或排查 Slay the Spire Mod 时，能够依据当前 JAR 的真实类名、方法描述符、参数、返回值、访问级别、注解、字段和资源路径回答，而不是依赖过时教程或猜测重载。

## 它有什么用

- 为 AI 编写卡牌、遗物、能力、药水、角色、怪物、事件和 UI Mod 提供当前版本 API 依据。
- 查询 ModTheSpire 的补丁注解、Locator、Insert/Prefix/Postfix/Instrument Patch 和 `SpireField`。
- 查询 BaseMod、StSLib 和已安装 Mod 的类、方法、字段、注解和依赖信息。
- 根据资源索引定位卡图、遗物图标、语言包、Spine/Atlas 和其他 JAR 内资源。
- 根据外置 Workshop 文件清单定位 JAR 外的 PNG/JPG/EXE/BAT 等文件，并用大小和 SHA-256 判断本机资源是否变化。
- 根据实际补丁注解定位目标类/方法，读取 `javap -p -s -c` 快照和带偏移、操作码、操作数、分支目标的 JVM 指令记录。
- 对无效的 `ModTheSpire.json` 保留 `metadata_raw_fallback` 原文、路径和 SHA-256，避免错误元数据被静默丢弃。
- 用 SHA-256 校验本机 JAR 是否仍与知识库生成时的版本一致。
- 用最小 Java 8 模板快速创建一个可编译的 Mod 项目。

## 当前快照

| 项目 | 当前值 |
|---|---|
| 知识库版本 | `1.1.0` |
| 游戏 | Slay the Spire 2.3.4 |
| 本体 JAR | `desktop-1.0.jar` |
| 本体 SHA-256 | `CFAD868AC8D65A88E71A0BF096FB09F78811E553EFFE0787C5309A655E081673` |
| ModTheSpire 元数据 | `999.999.999`（JAR 内标记，不等同于实际发布版本） |
| BaseMod | 5.56.0 |
| StSLib | 2.12.0 |
| Java | `1.8.0_144` |
| JAR 快照 | 66 个：本体 1、框架 3、本地 Mod 2、Workshop 60 |
| API 类型记录 | 31,088 个类 |
| JAR 资源记录 | 10,931 项 |
| 文本资源记录 | 1,580 项 |
| Workshop 外置文件清单 | 524 个文件，102,092,675 bytes；只保存路径/指纹，不保存文件本体 |
| 补丁注解引用 | 2,943 条，664 个唯一目标类 |
| JVM 指令快照 | 7,668 个方法；574 个 `javap -p -s -c` 类快照 |
| 无效 Mod 元数据 | 1 个，保留 `metadata_raw_fallback` |
| 生成时间 | 2026-09-26 17:43 UTC |



这些绝对路径只用于审计。使用知识库时应使用 `portable_path` 和 SHA-256，不要假设别人的  安装路径相同。

## 目录说明

| 路径 | 内容 | 主要用途 |
|---|---|---|
| `api/base_game_api.*` | 本体 `com.megacrit.cardcrawl.*` API | 查询游戏类、方法、字段和补丁目标 |
| `api/modthespire_api.*` | ModTheSpire API | 查询补丁注解、Locator 和补丁框架 |
| `api/basemod_api.*` | BaseMod API | 注册卡牌、遗物、药水、角色和生命周期订阅 |
| `api/stslib_api.*` | StSLib API | 查询额外机制、接口和通用动作 |
| `api/installed_mods_api.*` | 生成时已安装 Mod 的类索引 | 参考现有 Mod 的调用方式和命名 |
| `api/third_party_api.*` | LibGDX、Spine、Javassist 等第三方类 | UI、图片、动画和底层依赖 |
| `environment/` | JAR、类、资源、Workshop 和运行环境快照 | 版本审计、依赖定位和资源定位 |
| `environment/workshop_external_files.jsonl` | Workshop JAR 外的文件路径、大小和 SHA-256 | 定位图片/程序/配置等外置资源，不分发其本体 |
| `environment/patch_targets.jsonl` | Mod 补丁注解到目标类/方法的映射 | 追踪 Locator、Prefix/Postfix/Insert/Raw 补丁目标 |
| `bytecode/instruction_snapshots.jsonl` | 目标类方法的 JVM 指令级记录 | 查看偏移、操作码、常量池引用、分支目标和代码哈希 |
| `bytecode/javap/` | 对应目标类的 `javap -p -s -c` 文本快照 | 人工核对当前方法体和补丁插入点 |
| `resources/text_resources.jsonl` | JAR 内可读文本资源 | 查询 JSON、Atlas、语言包和少量源码文本 |
| `docs/` | 工作流、API 入口、补丁、资源和排错说明 | 给 AI 或开发者的使用导航 |
| `templates/` | Java 8 + ModTheSpire + BaseMod 最小模板 | 创建和构建新 Mod |
| `tools/` | API 查询、JAR 校验、`javap` 辅助脚本和生成器 | 实际验证与再生成 |
| `sts_ai_knowledge_report.html` | 离线类/成员浏览器 | 人类快速搜索，不作为唯一事实来源 |

## 给 AI 的推荐读取顺序

1. 读取本文件和 `AI_INGESTION_GUIDE.md`。
2. 读取 `manifest.json`，确认本知识库对应的本体 JAR 哈希。
3. 查本体类时使用 `api/base_game_api.types.jsonl`。
4. 查 ModTheSpire、BaseMod、StSLib 或已安装 Mod 时，只读取对应角色的 JSONL。
5. 遇到资源、依赖或 Workshop 版本问题时读取 `environment/`。
6. 涉及补丁插入点、方法行为或字节码布局时，先读 `environment/patch_targets.jsonl`，再读 `bytecode/instruction_snapshots.jsonl` 和对应 `bytecode/javap/` 快照。
7. 遇到元数据解析失败时，读取同一条记录的 `metadata_raw_fallback`；不要把空的 `metadata` 当成“没有 Mod 元数据”。

不要把所有大型 JSONL 一次性放进上下文；先按类型名和成员名查询。

## 常用命令

查询本体的 `AbstractCard.use`：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\query-sts-api.ps1 `
  -PackRoot $PWD `
  -Role base_game `
  -TypeName com.megacrit.cardcrawl.cards.AbstractCard `
  -Member use
```

查询 BaseMod 的 `addCard`：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\query-sts-api.ps1 `
  -PackRoot $PWD `
  -Role basemod `
  -TypeName basemod.BaseMod `
  -Member addCard
```

校验本机安装是否与快照一致：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\verify-sts-pack.ps1 `
  -GameRoot 'E:\SteamLibrary\steamapps\common\SlayTheSpire' `
  -PackRoot $PWD `
  -VerifyPackFiles `
  -VerifyWorkshopExternalFiles
```

查询 `AbstractCard` 的补丁目标和指令快照：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\query-bytecode.ps1 `
  -PackRoot $PWD `
  -TargetClass 'com.megacrit.cardcrawl.cards.AbstractCard*' `
  -IncludeInstructions
```

使用最小模板：

```powershell
.\templates\build.ps1 `
  -StsRoot 'E:\SteamLibrary\steamapps\common\SlayTheSpire' `
  -JavaHome 'C:\Program Files\Java\jdk8'
```

## 获取与使用

这是给 AI 和 Mod 开发者使用的知识库，不是需要复制到 `mods` 目录的 Mod。直接下载或克隆仓库后，将整个目录作为 AI 的参考资料；如果只需要查询，可以运行 `tools/query-sts-api.ps1` 或打开 `sts_ai_knowledge_report.html`。

克隆包含 Git LFS 大文件的完整版本需要先安装 Git LFS：

```powershell
git lfs install
git clone https://github.com/peigu666/slay-the-spire-distillation.git
```

如果只浏览网页端 JSONL 索引，可以直接打开 GitHub 文件列表；如果要重新校验本机 JAR，则需要本机安装对应的 Slay the Spire、Java 8 和 Mod，并使用上面的校验命令。

## 可移植性与 Workshop 快照

`environment/mod_catalog.json`、`environment/jar_inventory.jsonl`、`environment/workshop_manifest.json` 和 `environment/workshop_external_files.jsonl` 是生成机的安装快照，不代表每个使用者都安装了相同的 Mod 或外置资源。

本仓库不上传游戏 JAR、Mod JAR、图片、音频、存档或完整 Workshop 资源。JAR 内资源只保留路径、大小、CRC/哈希和可读文本索引；JAR 外文件清单只保留路径、大小和 SHA-256。其他用户缺少对应 Workshop 项目是正常情况。需要实际运行或验证某个 Mod 时，用户应自行通过 Steam Workshop 安装，并重新运行校验脚本。

## 重要边界

- API 记录来自生成时的具体 JAR，不应泛化到所有 Slay the Spire、ModTheSpire、BaseMod 或 StSLib 版本。
- 普通类记录包含私有成员、访问级别、描述符、注解以及方法代码长度/哈希；补丁目标额外提供局部 `javap -p -s -c` 和解析后的 JVM 指令，但不等同于 Java 源码。
- `installed_mods` 是生成时的 Mod 快照；Workshop 更新后必须重新生成或重新校验。
- 一个 Workshop Mod 的 `ModTheSpire.json` 存在格式问题；`mod_catalog.json` 和 `jar_inventory.jsonl` 会在 `metadata_raw_fallback` 中保留原文，供回退分析。
- Java 的“IL”在本项目中指 JVM bytecode 指令，不是 .NET CLR IL；当前 JAR 中不存在可直接提供的 CLR IL。
- 这个仓库只提供知识索引和工具，不替代游戏、ModTheSpire、BaseMod、StSLib 或具体 Mod 的安装包。

## 搜索关键词 / Search keywords

### 中文

`杀戮尖塔` `尖塔` `Slay the Spire` `StS Mod` `尖塔 Mod` `杀戮尖塔 Mod 开发` `杀戮尖塔模组` `Java 模组` `Java Mod` `ModTheSpire` `BaseMod` `StSLib` `卡牌 Mod` `遗物 Mod` `能力 Mod` `药水 Mod` `角色 Mod` `怪物 Mod` `事件 Mod` `补丁` `字节码补丁` `JVM 字节码` `指令级字节码` `javap` `Locator` `插入补丁` `资源路径` `外置 Workshop 文件` `语言包` `本地化` `卡图` `创意工坊` `Steam Workshop` `AI 知识库` `API 索引` `JAR 分析` `Java 8`

### English

`slay-the-spire` `slay-the-spire-modding` `sts-modding` `slay-the-spire-mod` `java-mod` `java-game-modding` `modthespire` `basemod` `stslib` `card-mod` `relic-mod` `power-mod` `potion-mod` `character-mod` `monster-mod` `event-mod` `ui-mod` `game-modding` `mod-development` `java-8` `javassist` `bytecode-patching` `jvm-bytecode` `javap` `runtime-patching` `api-index` `jsonl` `workshop-mods` `steam-workshop` `ai-knowledge-base` `reverse-engineering` `resource-index` `localization` `modding-tools` `patch-targets`

## 第三方内容说明

本仓库发布的是从本机安装生成的 API、元数据、资源索引和辅助工具，不包含《Slay the Spire》本体或完整 Mod 二进制。类名、方法签名、资源路径、Mod 名称和文本可能受原作者或相应项目许可约束。使用、再分发或基于这些资料开发时，请遵守 Steam、游戏本体、ModTheSpire、BaseMod、StSLib 以及各 Workshop Mod 的许可和作者要求。
