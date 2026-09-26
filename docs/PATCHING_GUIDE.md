# ModTheSpire 补丁要点

## 补丁类型

- `@SpirePatch` / `@SpirePatch2`：指向类、方法和可选参数类型。`SpirePatch2` 是当前 JAR 中的独立注解，必须以 API JSONL 的注解属性为准。
- `@SpirePrefixPatch`：目标方法执行前运行；返回 `void` 表示继续，使用 `SpireReturn.Return(...)` 或相关返回值机制时可以短路（先查当前 `SpireReturn` 签名）。
- `@SpirePostfixPatch`：目标方法正常执行后运行，可接收原返回值并返回修改后的值。
- `@SpireInsertPatch`：在目标方法内部插入，通常配合 `SpireInsertLocator`、`LineFinder`、`Matcher`；`loc/rloc/locs/rlocs` 与 `localvars` 的具体属性在当前 API 记录里。
- `@SpireInstrumentPatch`：使用 Javassist `ExprEditor` 等机制改写方法体，脆弱度最高。
- `@SpireRawPatch`：直接接触原始字节码时使用，只有在普通补丁无法满足需求时考虑。
- `@SpireField` / `StaticSpireField`：给原类增加实例/静态扩展字段，不要直接假设本体私有字段在下一版本仍存在。

## 写补丁的顺序

1. 从 `api/base_game_api.types.jsonl` 找目标类和目标重载。
2. 用 `tools/query-sts-api.ps1 -IncludeBody` 看方法的代码长度/哈希和补丁类已有的注解属性；必要时对本地 JAR 单独运行 `javap -c` 做行为确认。
3. 选择最小补丁：前缀/后缀优先，其次插入，最后才是 Instrument/Raw。
4. 如果目标属于可选 Mod，填写 `requiredModId` 或 `optional`，并在 `ModTheSpire.json` 中区分硬依赖和可选依赖。
5. 一次只引入一个补丁目标，启动后检查日志中的 patch 应用结果。

## Locator 不能靠猜

插入点由字节码指令决定；源码行号、反编译出来的局部变量名和旧版教程都不能替代当前 JAR。类记录中的 `code.sha256` 只用于发现目标是否变了，不是可读源码。目标方法变更后应重新确定 Matcher/Locator，而不是只改注解名字。

## 常见误区

- 把构造器写成普通方法名：JVM 描述符里构造器是 `<init>`。
- 只写类名不写参数：重载会命中错误方法或根本无法应用。
- 用 `@SpirePatch` 的旧属性名替代当前 `clz/cls/method/paramtypez/paramtypes`。
- 把 BaseMod 订阅接口当作 ModTheSpire 补丁：前者是生命周期回调，后者是字节码补丁，两条链路可以并存。
- 在没有验证当前 JAR 哈希的情况下引用旧的 `Locator` 行号。
