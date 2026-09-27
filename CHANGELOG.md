# 更新日志

## v1.3.0 — 2026-09-27

补齐基础游戏全量 JVM 指令覆盖，并增强按需查询能力。
- 新增 `bytecode/full_game_instruction_snapshots.jsonl`，覆盖本体 `com.megacrit.cardcrawl.*` 的 2,306 个类、12,696 个方法和 461,731 条解析后的 JVM 指令。
- 新增 `bytecode/full_game_parse_errors.jsonl`，显式记录本体类解析失败；本次基线解析失败数为 0。
- 保留较小的补丁目标快照和 `javap` 文本快照，分别服务于补丁定位和人工核对。
- `tools/query-bytecode.ps1` 新增 `-FullGame`，可按类名/方法名查询本体全量快照。
- 将新增大文件纳入 Git LFS，并在 `ai_manifest.json`、文件索引和整包校验中标记为按需数据。

## v1.2.0 — 2026-09-27

完善 AI-ready 发布结构和整包可验证性。

- 新增 `ai_manifest.json`，定义默认摄取、按需数据、证据优先级和版本边界。
- 扩展 `ai_file_index.jsonl`，为每个文件记录角色、优先级、解析方式和默认摄取状态。
- 生成器不再把 `.git`、Python 缓存和模板构建产物写入知识文件索引。
- 统一一次生成过程中的 `generated_at_utc`，避免 manifest、环境快照和 AI 指南时间漂移。
- 验证工具新增路径逃逸、重复/漏索引、AI manifest 和模板入口检查。
- 明确标注 JVM 指令快照是补丁目标范围，不冒充全量方法字节码。

## v1.1.0 — 2026-09-27

补充补丁目标和 Workshop 外置资源证据链。

- 新增 `environment/workshop_external_files.jsonl` 与汇总文件，收录 524 个 JAR 外 Workshop 文件的路径、大小和 SHA-256，不上传二进制本体。
- 新增 `environment/patch_targets.jsonl`，记录 2,943 条实际 Mod 补丁注解引用、目标类/方法、参数和解析状态。
- 新增 7,668 个方法的指令级 JVM bytecode 快照，以及 574 个 `javap -p -s -c` 类文本快照。
- 无法解析的目标类/方法保留 `missing_class` 或 `method_not_found` 状态，不用猜测替代。
- 无效的 `ModTheSpire.json` 新增 `metadata_raw_fallback` 原文、路径和 SHA-256 字段。
- 新增 `tools/query-bytecode.ps1` 和 Workshop 外置文件校验选项。

### 兼容性

- 生成基线仍为 Slay the Spire 2.3.4、`desktop-1.0.jar`、BaseMod 5.56.0、StSLib 2.12.0、Java 8。
- `javap` 文本快照使用生成时的 JDK 21.0.11；运行游戏仍以游戏自带 Java 8 为准。
- Java 项目中的“IL”指 JVM bytecode 指令，不是 .NET CLR IL。

## v1.0.0 — 2026-09-27

首次公开发布 Slay the Spire 蒸馏 AI Mod 开发知识库。

- 收录 Slay the Spire 2.3.4、ModTheSpire、BaseMod、StSLib、已安装 Mod 和 Workshop Mod 的 API 与环境索引。
- 提供 31,088 条类型记录、10,931 条 JAR 资源记录和 1,580 条文本资源记录。
- 提供 JSONL 查询、JAR 哈希校验、最小 Java 8 Mod 构建模板、离线 HTML 浏览报告和 AI 读取指南。
- 保留 Workshop 资源清单、版本快照和路径索引，但不把游戏、Mod、图片、音频或完整 Workshop 资源打包进仓库。
- `api/installed_mods_api.types.jsonl` 使用 Git LFS 保存，以避免超过 GitHub 普通 Git 文件限制。

### 兼容性

- 生成基线：桌面版 `desktop-1.0.jar`，SHA-256 为 `CFAD868AC8D65A88E71A0BF096FB09F78811E553EFFE0787C5309A655E081673`。
- 主要依赖：BaseMod 5.56.0、StSLib 2.12.0、Java 8。
- 其他用户的 Workshop 订阅和本机安装路径可能不同；需要运行时校验时，应按 README 重新生成或校验快照。
