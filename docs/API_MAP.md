# API 入口地图

所有名称都应以当前 `api/*.types.jsonl` 的记录为最终依据。下表是搜索入口，不是对方法参数的替代。

| 任务 | 首查类/包 | 常见下一跳 |
|---|---|---|
| 卡牌 | `com.megacrit.cardcrawl.cards.AbstractCard` | `cards.CardGroup`、`cards.CardLibrary`、`actions`、`powers` |
| 遗物 | `com.megacrit.cardcrawl.relics.AbstractRelic` | `relics.AbstractRelic.RelicTier`、`RelicLibrary`、`basemod.helpers.RelicType` |
| 能力 | `com.megacrit.cardcrawl.powers.AbstractPower` | `powers.AbstractPower.PowerType`、`actions.common.ApplyPowerAction` |
| 药水 | `com.megacrit.cardcrawl.potions.AbstractPotion` | `BaseMod.addPotion`、`potions.PotionSlot` |
| 角色 | `com.megacrit.cardcrawl.characters.AbstractPlayer` | `PlayerClass`、`CardColor`、`BaseMod.addCharacter` |
| 怪物 | `com.megacrit.cardcrawl.monsters.AbstractMonster` | `MonsterGroup`、`MonsterInfo`、`getMove`/`takeTurn` |
| 战斗动作 | `com.megacrit.cardcrawl.actions.AbstractGameAction` | `GameActionManager`、`actions.common`、`actions.utility` |
| 地牢状态 | `com.megacrit.cardcrawl.dungeons.AbstractDungeon` | `player`、`actionManager`、抽牌/弃牌/奖励/房间 |
| 游戏状态 | `com.megacrit.cardcrawl.core.CardCrawlGame` | `GameMode`、语言包、屏幕、设置 |
| 事件 | `com.megacrit.cardcrawl.events.AbstractEvent` | `events.AbstractImageEvent`、`EventUtils`、BaseMod 注册 |
| 房间 | `com.megacrit.cardcrawl.rooms.AbstractRoom` | `MapRoomNode`、战斗/商店/篝火房间 |
| UI/图片 | `com.megacrit.cardcrawl.helpers.ImageMaster` | `TextureAtlas`、`FontHelper`、`Hitbox`、`UIElement` |
| 字符串 | `com.megacrit.cardcrawl.localization.*` | `CardStrings`、`RelicStrings`、`PowerStrings`、`PotionStrings` |
| Mod 订阅 | `basemod.interfaces.*Subscriber` | `BaseMod.subscribe`、`receive...` 生命周期 |
| 字段扩展 | `com.evacipated.cardcrawl.modthespire.lib.SpireField` | `StaticSpireField`、`initialize/get/set` |
| 补丁 | `com.evacipated.cardcrawl.modthespire.lib.SpirePatch*` | Locator、Matcher、`SpireReturn`、`LineFinder` |
| 扩展机制 | `com.evacipated.cardcrawl.mod.stslib.*` | 卡牌/遗物/能力接口和对应 patch |

## 推荐查询

```powershell
.\tools\query-sts-api.ps1 -PackRoot $PWD -Role base_game -TypeName AbstractCard
.\tools\query-sts-api.ps1 -PackRoot $PWD -Role basemod -TypeName BaseMod -Member addCard
.\tools\query-sts-api.ps1 -PackRoot $PWD -Role modthespire -TypeName '*SpirePatch*'
.\tools\query-sts-api.ps1 -PackRoot $PWD -Role installed_mods -Member 'receive*'
```

查询结果中的 `descriptor` 是 JVM 的真实签名；同名重载必须同时看它和 `parameter_types`。
