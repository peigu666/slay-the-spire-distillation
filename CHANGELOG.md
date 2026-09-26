# 更新日志

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
