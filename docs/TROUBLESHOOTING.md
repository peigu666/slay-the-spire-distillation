# 排错手册

## 先做三项确认

1. `powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\verify-sts-pack.ps1 -GameRoot 'E:\Games\SlayTheSpire' -PackRoot $PWD`。
2. 确认 `desktop-1.0.jar`、ModTheSpire、BaseMod、StSLib 的 SHA-256 与 `environment/jar_inventory.jsonl` 一致。
3. 读取当前游戏目录下 `sendToDevs/logs/SlayTheSpire.log`、`sendToDevs/mts_launcher.log`，不要只看旧截图或旧教程。

## 日志关键词

- `NoClassDefFoundError` / `ClassNotFoundException`：类路径或依赖缺失。
- `NoSuchMethodError` / `NoSuchFieldError`：编译时 JAR 与运行时 JAR 不一致，或 API 版本不匹配。
- `VerifyError` / `IllegalAccessError`：补丁生成的字节码、访问级别或 Java 版本不兼容。
- patch application failed、Locator、Matcher：目标方法或字节码布局已经变了，重新查描述符并重新设计 Locator。
- `FileNotFoundException`、Spine/Texture 异常：JAR 内资源路径、大小写、前缀或 atlas/png 配套不一致。

## Java 版本

本机游戏自带 JRE 为生成时实际可见的版本，写入 `environment/environment_manifest.json`。模板默认编译到 Java 8 字节码以适配这套启动链路；但已安装模组的构建 JDK 可能是 17 或 21，JAR 的 `classfile.major` 会如实记录。若运行时是 Java 8，直接加载更高 major 的 Mod 会失败；应以当前启动器和日志为准，不要仅凭 `Build-Jdk` 字段判断运行时。

## 依赖顺序

`ModTheSpire.json` 的 `dependencies` 是加载依赖；`optional_dependencies` 不应被当成硬依赖。先检查 `environment/mod_catalog.json` 的元数据，再检查实际 JAR 是否存在；只在类确实被引用时才把 StSLib 或其他 Mod 设为硬依赖。

## 版本不一致时

不要手工编辑 API JSONL 来“修正”版本。保留旧包，换新的输出目录重新跑生成器，再重新运行验证工具；这样 AI 能区分不同基线。
