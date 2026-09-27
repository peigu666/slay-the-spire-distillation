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
| 知识库版本 | `1.4.1` |
| 游戏 | Slay the Spire 2.3.4 |
| 本体 JAR | `desktop-1.0.jar` |
| 本体 SHA-256 | `CFAD868AC8D65A88E71A0BF096FB09F78811E553EFFE0787C5309A655E081673` |
| ModTheSpire 元数据 | `999.999.999`（JAR 内标记，不等同于实际发布版本） |
| BaseMod | 5.56.0 |
| StSLib | 2.12.0 |
| Java | `1.8.0_144` |
| JAR 快照 | 67 个：本体 1、框架 3、本地 Mod 2、Workshop 60、可选 Mod 1 |
| API 类型记录 | 35,163 个类（其中可选 Mod API 4,075 个） |
| JAR 资源记录 | 19,038 项；可选 Mod 只保留资源路径/指纹，不复制文本正文 |
| 文本资源记录 | 1,580 项 |
| Workshop 外置文件清单 | 524 个文件，102,092,675 bytes；只保存路径/指纹，不保存文件本体 |
| 补丁注解引用 | 3,332 条，718 个唯一目标类，其中 664 个目标类已解析 |
| JVM 指令快照 | 本体 2,306 个类 / 12,696 个方法 / 461,731 条指令；另有 8,758 个补丁目标方法和 664 个 `javap -p -s -c` 类快照 |
| 无效 Mod 元数据 | 1 个，保留 `metadata_raw_fallback` |
| 生成时间 | 以 `manifest.json` / `ai_manifest.json` 的 `generated_at_utc` 为准 |

生成时的绝对路径只用于审计；使用知识库时应使用 `portable_path` 和 SHA-256，不要假设其他人的安装路径相同。

## 目录说明

| 路径 | 内容 | 主要用途 |
|---|---|---|
| `api/base_game_api.*` | 本体 `com.megacrit.cardcrawl.*` API | 查询游戏类、方法、字段和补丁目标 |
| `api/modthespire_api.*` | ModTheSpire API | 查询补丁注解、Locator 和补丁框架 |
| `api/basemod_api.*` | BaseMod API | 注册卡牌、遗物、药水、角色和生命周期订阅 |
| `api/stslib_api.*` | StSLib API | 查询额外机制、接口和通用动作 |
| `api/installed_mods_api.*` | 生成时已安装 Mod 的类索引 | 参考现有 Mod 的调用方式和命名 |
| `api/optional_mods_api.*` | 未纳入当前安装基线的可选 Mod API（本版含 Downfall） | AI 查询未安装 Mod 的真实类、方法、字段和注解 |
| `api/third_party_api.*` | LibGDX、Spine、Javassist 等第三方类 | UI、图片、动画和底层依赖 |
| `environment/` | JAR、类、资源、Workshop 和运行环境快照 | 版本审计、依赖定位和资源定位 |
| `ai_manifest.json` | AI 默认摄取范围、优先级和按需数据策略 | 控制上下文大小并避免混用资料角色 |
| `ai_file_index.jsonl` | 每个知识文件的哈希、角色、优先级和解析方式 | 完整性校验与 AI 文件路由 |
| `environment/workshop_external_files.jsonl` | Workshop JAR 外的文件路径、大小和 SHA-256 | 定位图片/程序/配置等外置资源，不分发其本体 |
| `environment/optional_mod_manifest.json` | 可选 Mod 的 Workshop ID、版本、大小和 SHA-256 | 没有对应 Mod 时仍可使用 API；需要重生成时按指纹下载校验 |
| `environment/patch_targets.jsonl` | Mod 补丁注解到目标类/方法的映射 | 追踪 Locator、Prefix/Postfix/Insert/Raw 补丁目标 |
| `bytecode/full_game_instruction_snapshots.jsonl` | 本体 `com.megacrit.cardcrawl.*` 全部方法的 JVM 指令记录 | 按类/方法按需分析完整本体行为和插入点 |
| `bytecode/full_game_parse_errors.jsonl` | 本体字节码解析失败审计清单 | 确认全量快照是否存在解析缺口；本基线为空 |
| `bytecode/instruction_snapshots.jsonl` | 目标类方法的 JVM 指令级记录 | 查看偏移、操作码、常量池引用、分支目标和代码哈希 |
| `bytecode/javap/` | 对应目标类的 `javap -p -s -c` 文本快照 | 人工核对当前方法体和补丁插入点 |
| `resources/text_resources.jsonl` | JAR 内可读文本资源 | 查询 JSON、Atlas、语言包和少量源码文本 |
| `docs/MOD_VERSION_MATRIX.md` | 逐 Mod 版本、Workshop ID、依赖和 SHA-256 | 在 GitHub 上核对每个 Mod 的具体基线 |
| `docs/` | 工作流、API 入口、补丁、资源和排错说明 | 给 AI 或开发者的使用导航 |
| `templates/` | Java 8 + ModTheSpire + BaseMod 最小模板 | 创建和构建新 Mod |
| `tools/` | API 查询、JAR 校验、`javap` 辅助脚本和生成器 | 实际验证与再生成 |
| `sts_ai_knowledge_report.html` | 离线类/成员浏览器 | 人类快速搜索，不作为唯一事实来源 |

## 给 AI 的推荐读取顺序

1. 读取本文件、`AI_INGESTION_GUIDE.md` 和 `ai_manifest.json`。
2. 读取 `manifest.json`，确认本知识库对应的本体 JAR 哈希。
3. 默认只加载核心 API、环境 JSON 摘要、docs、templates 和 tools；具体以 `ai_file_index.jsonl` 的 `include_by_default` 和 `priority` 为准。
4. 查本体类时使用 `api/base_game_api.types.jsonl`；查 ModTheSpire、BaseMod、StSLib 时只读取对应角色的 JSONL。
5. 查已安装 Mod、第三方库、资源、补丁指令或 Workshop 外置文件时，按目标类型/成员/路径读取对应的按需 JSONL。
6. 涉及补丁插入点、方法行为或字节码布局时，先读 `environment/patch_targets.jsonl`；补丁目标优先读 `bytecode/instruction_snapshots.jsonl`，一般本体方法按需读 `bytecode/full_game_instruction_snapshots.jsonl`，再用对应 `bytecode/javap/` 快照核对。
7. 遇到元数据解析失败时，读取同一条记录的 `metadata_raw_fallback`；不要把空的 `metadata` 当成“没有 Mod 元数据”。

不要把所有大型 JSONL 一次性放进上下文；先按类型名和成员名查询。

可选 Mod API 不代表本机已经安装该 Mod。查询 Downfall 等未安装 Mod 时使用 `-Role optional_mods`；只有需要从 Workshop 重新生成或验证时，才使用 `tools/fetch-optional-mods.ps1` 获取原始 JAR。

## 其他玩家与不同 Mod 环境

本知识包是生成时单台电脑的快照，不要求其他玩家安装完全相同数量的 Mod。完整逐 Mod 基线见 [`docs/MOD_VERSION_MATRIX.md`](docs/MOD_VERSION_MATRIX.md)，离线 HTML 报告也提供可筛选的版本清单。

- 对方的本体、框架或某个 Mod JAR 的 SHA-256 一致时，可以直接使用对应资料。
- 对方缺少的 Mod 应忽略；对方多出的或哈希不同的 Mod 需要另行扫描，不能从本包推断其 API。
- 版本文本相同不保证 JAR 相同，判断文件身份时以 SHA-256 为准。
- 相同 JAR 但配置、启用状态、语言、存档或加载顺序不同，静态 API 仍可参考，实际行为必须结合对方当前配置和启动日志。
- `preferences`、Mod 配置和存档可能包含隐私信息，不应无条件收集或上传。

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
  -VerifyWorkshopExternalFiles `
  -VerifyTemplate
```

查询 `AbstractCard` 的补丁目标和指令快照：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\query-bytecode.ps1 `
  -PackRoot $PWD `
  -TargetClass 'com.megacrit.cardcrawl.cards.AbstractCard*' `
  -IncludeInstructions
```

查询本体完整指令快照中的指定方法：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\query-bytecode.ps1 `
  -PackRoot $PWD `
  -FullGame `
  -TargetClass 'com.megacrit.cardcrawl.cards.AbstractCard' `
  -TargetMethod 'use'
```

使用最小模板：

```powershell
.\templates\build.ps1 `
  -StsRoot 'E:\SteamLibrary\steamapps\common\SlayTheSpire' `
  -JavaHome 'C:\Program Files\Java\jdk8'
```

## 获取与使用

这是给 AI 和 Mod 开发者使用的知识库，不是需要复制到 `mods` 目录的 Mod。直接下载或克隆仓库后，将整个目录作为 AI 的参考资料；如果只需要查询，可以运行 `tools/query-sts-api.ps1` 或打开 `sts_ai_knowledge_report.html`。

优先下载 GitHub Release 的压缩包，不必克隆约 469 MiB 的 Git LFS 完整仓库。Release 包含完整 API 资料；原始游戏和 Mod 二进制不随仓库发布。

克隆包含 Git LFS 大文件的完整版本需要先安装 Git LFS：

```powershell
git lfs install
git clone https://github.com/peigu666/slay-the-spire-distillation.git
```

如果只浏览网页端 JSONL 索引，可以直接打开 GitHub 文件列表；如果要重新校验本机 JAR，则需要本机安装对应的 Slay the Spire、Java 8 和 Mod，并使用上面的校验命令。

查询 Downfall API（不需要本机安装 Downfall）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\query-sts-api.ps1 `
  -PackRoot $PWD -Role optional_mods `
  -TypeName downfall.actions.AbstractXAction -Member initialize
```

需要重新生成可选 Mod API 时，先下载并核验 Workshop JAR，再把对应的 Workshop content 根目录传给生成器的 `-OptionalMods`；不要把下载的 JAR 提交到仓库。

## 可移植性与 Workshop 快照

`environment/mod_catalog.json`、`environment/jar_inventory.jsonl`、`environment/workshop_manifest.json` 和 `environment/workshop_external_files.jsonl` 是生成机的安装快照，不代表每个使用者都安装了相同的 Mod 或外置资源。

本仓库不上传游戏 JAR、Mod JAR、图片、音频、存档或完整 Workshop 资源。JAR 内资源只保留路径、大小、CRC/哈希和必要的可读文本索引；可选 Mod 只进入独立 API 角色和资源路径索引，不复制 Downfall 等大型文本资源。其他用户缺少对应 Workshop 项目是正常情况：AI 查询不需要这些二进制，只有实际运行、重新生成或验证某个 Mod 时，用户才需要自行通过 Steam Workshop 获取它，并重新运行校验脚本。

## 重要边界

- API 记录来自生成时的具体 JAR，不应泛化到所有 Slay the Spire、ModTheSpire、BaseMod 或 StSLib 版本。
- 普通类记录包含私有成员、访问级别、描述符、注解以及方法代码长度/哈希；本体另有完整 JVM 指令快照，补丁目标额外提供局部 `javap -p -s -c` 和专项指令索引，但不等同于 Java 源码。
- `installed_mods` 是生成时的 Mod 快照；Workshop 更新后必须重新生成或重新校验。
- `optional_mods` 是独立的未安装 Mod API 档案；本版 Downfall 来自 Workshop `1610056683`，只记录其 API、资源路径和 SHA-256，不分发 482 MB 原始 JAR。
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
