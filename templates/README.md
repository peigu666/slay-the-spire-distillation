# Minimal StS Mod 模板

这是 Java 8 + ModTheSpire + BaseMod 的最小入口。模板不复制任何游戏或框架 JAR；用 `build.ps1` 通过参数指向本机安装。

```powershell
.\build.ps1 `
  -StsRoot 'E:\SteamLibrary\steamapps\common\SlayTheSpire' `
  -JavaHome 'C:\Program Files\Java\jdk8'
```

如果多个创意工坊版本同时存在，显式传 `-ModTheSpireJar`、`-BaseModJar`、`-StSLibJar`。运行时需要把生成的 JAR 和根目录 `ModTheSpire.json` 放进 ModTheSpire 扫描的模组目录；实际加载顺序和错误以当前启动日志为准。
