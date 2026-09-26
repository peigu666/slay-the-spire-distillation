# Mod 制作工作流

## 1. 运行链路

标准链路是：Steam 游戏目录提供 `desktop-1.0.jar` 和 Java 运行时；ModTheSpire 负责启动、扫描 `ModTheSpire.json`、按依赖排序并对本体类应用补丁；BaseMod 提供订阅者、卡牌/遗物/药水/角色注册和自定义字符串；StSLib 提供可复用的额外机制与接口。

生成时的实际 JAR 和版本写在 `environment/mod_catalog.json`，不要直接把这段概念当成所有版本的保证。

## 2. 最小入口

模板 `templates/src/main/java/example/MinimalMod.java` 使用 `@SpireInitializer`、`BaseMod.subscribe` 和 `PostInitializeSubscriber`。`ModTheSpire.json` 至少需要 `modid`、`name`、`author_list`、`description` 和 `version`；依赖 BaseMod/StSLib 时显式填写 `dependencies`。

```powershell
.\templates\build.ps1 -StsRoot 'E:\Games\SlayTheSpire' -JavaHome 'C:\Program Files\Java\jdk8'
```

脚本会优先从 `$StsRoot\mods` 和 `steamapps\workshop\content\646570` 中查找 ModTheSpire/BaseMod/StSLib。也可以显式传 `-ModTheSpireJar`、`-BaseModJar` 和 `-StSLibJar`。

## 3. 添加内容的最小路径

- 卡牌：继承 `com.megacrit.cardcrawl.cards.AbstractCard`，在初始化阶段 `BaseMod.addCard`；复杂卡牌效果通常在 `use`、`applyPowers`、`calculateCardDamage` 和升级逻辑中完成。
- 遗物：继承 `AbstractRelic` 或 BaseMod 的 `CustomRelic`，使用 `BaseMod.addRelic` 或自定义池注册。
- 能力：继承 `AbstractPower`，由卡牌/遗物通过 `ApplyPowerAction` 等动作施加。
- 药水：继承 `AbstractPotion`，通过 `BaseMod.addPotion` 注册。
- 角色：继承 `AbstractPlayer`，用 BaseMod 的 `addCharacter` 和角色类/颜色枚举完成接入。
- 怪物/遭遇/事件：先查 `base_game_api.types.jsonl` 和 `basemod_api.types.jsonl` 的同名类与注册方法，再照当前版本签名实现。

## 4. 写补丁前先查签名

先用查询工具确认目标类、方法名、参数类型和返回值。补丁目标必须用精确方法描述符区分重载；私有目标可以被补丁框架定位，但 Mod 自己编译时仍应遵守 Java 访问规则，必要时使用 ModTheSpire 的字段/补丁机制，而不是猜字段名。

## 5. 验证标准

1. 用模板或项目自己的构建脚本编译，确保类路径包含本体、ModTheSpire、BaseMod 和实际使用的扩展库。
2. 将生成的 JAR 和 `ModTheSpire.json` 放进正确的 `mods` 目录，使用 ModTheSpire 启动。
3. 检查 `sendToDevs/logs/SlayTheSpire.log`、`sendToDevs/mts_launcher.log` 和启动器输出。
4. 如果行为与知识包不一致，先重新跑 `tools/verify-sts-pack.ps1`；哈希不一致就重新生成，不要继续套用旧签名。
