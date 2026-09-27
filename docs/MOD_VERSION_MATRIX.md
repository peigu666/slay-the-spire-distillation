# Mod 版本与环境兼容矩阵

本表对应本知识包生成时的单台电脑快照，不代表所有玩家的安装。版本优先读取 JAR 根目录的 `ModTheSpire.json`；显示“未声明”时不要根据文件名猜测版本。即使版本文本相同，也只有 SHA-256 一致时才能确认是同一个 JAR。

其他玩家可以继续使用哈希一致的本体、框架和单个 Mod 资料；缺少的 Mod 应忽略，多出的 Mod 需要另行扫描。相同 JAR 但配置、启用状态或加载顺序不同，API 仍可参考，实际行为必须结合对方的配置和当前启动日志判断。

| 来源 | 名称 | Mod ID | 元数据版本 | Workshop ID | 声明依赖 | JAR SHA-256 |
|---|---|---|---|---|---|---|
| 本地 Mod | Feminization | Feminization | 0.1.6.4 | — | — | `F1D2DA519A099E38437C935E8317ECC6DF6782B0383823B730B47637D8C6624C` |
| 本地 Mod | 道初 更多遗物 | SpireOddities | 0.5.1 | — | basemod | `E30C6CD0A1EA08807870F9D81A1991B3AE33D996163855A37AF816897A3DF295` |
| 核心框架 | ModTheSpire | modthespire | 999.999.999 | [1605060445](https://steamcommunity.com/sharedfiles/filedetails/?id=1605060445) | — | `541B5E8A875D2A404A5A6D54F4A6F814284B0CF71ACB9245239D9C5EF50EA604` |
| 核心框架 | BaseMod | basemod | 5.56.0 | [1605833019](https://steamcommunity.com/sharedfiles/filedetails/?id=1605833019) | — | `C3353C10E64C621B723E9FD7D0502DFA796F828B101B68513594A5F5EF83FBAF` |
| 核心框架 | StSLib | stslib | 2.12.0 | [1609158507](https://steamcommunity.com/sharedfiles/filedetails/?id=1609158507) | basemod | `B71A4934C9EB6C020799F5418B0BEC5E5957879F9A0F8B4F7CE80288F456FF62` |
| Workshop Mod | Highlight Path | HighlightPath | 0.0.3 | [1611047977](https://steamcommunity.com/sharedfiles/filedetails/?id=1611047977) | basemod | `500CC7FA195266CC18941BCD9E4C1BAA2F532545D44F970DC724B51364CC8784` |
| Workshop Mod | Colored Map | coloredmap | 2.4.1 | [1611666859](https://steamcommunity.com/sharedfiles/filedetails/?id=1611666859) | basemod | `E51D940D14918628A51DAA0498DAC5DEEC0E242E21C4DD6A89AF50D84F430CAC` |
| Workshop Mod | Friendly Minions | Friendly_Minions_0987678 | v0.1.2 | [1612426481](https://steamcommunity.com/sharedfiles/filedetails/?id=1612426481) | basemod | `28534A945500662C2E242D43EE858DB7EEB433CADBE32E9B4F05C946C042C983` |
| Workshop Mod | The Animator | eatyourbeetsvg-theanimator | 3.5.9 | [1638308801](https://steamcommunity.com/sharedfiles/filedetails/?id=1638308801) | basemod, stslib | `174E3A87E680F076EDA516A08FF580BBD845B650A62AFAEA1E239381AA0251C6` |
| Workshop Mod | GifTheSpireLib | GifTheSpireLib | 2.0.1 | [1685625583](https://steamcommunity.com/sharedfiles/filedetails/?id=1685625583) | basemod | `E5CCDEFA9D9C8455081097C1857364F4414972CD9F79BB9884E5368F5DF9B38A` |
| Workshop Mod | AchievementEnabler | AchievementEnabler | 1.0.0 | [1692554109](https://steamcommunity.com/sharedfiles/filedetails/?id=1692554109) | basemod | `F651076E05F09A46FC4664314B71E4503A0AD1B2AB7361A9FF1FB88D09EA804F` |
| Workshop Mod | Colored Powertips | coloredpowertips | 2.3.0 | [1748973286](https://steamcommunity.com/sharedfiles/filedetails/?id=1748973286) | basemod | `A5165613017F75D0422C7D35D87D70EA4E717FEFC27F822FAE3E6EE710498DB6` |
| Workshop Mod | Quick Restart | quickrestart | 2.1.1 | [1805046408](https://steamcommunity.com/sharedfiles/filedetails/?id=1805046408) | basemod | `7BAFF1D13D9574D894ABA19BB176189721DF88681016EECCCD411A0C9B499682` |
| Workshop Mod | Minty Spire (QoL Compilation) | mintyspire | 2.5.10 | [1812723899](https://steamcommunity.com/sharedfiles/filedetails/?id=1812723899) | basemod | `2894AD544F610D8B0E76B67C185ACC35AE4DB1E2E974A8083B600257CD16EB53` |
| Workshop Mod | yUi | yUi | 2.2.1 | [1879864511](https://steamcommunity.com/sharedfiles/filedetails/?id=1879864511) | basemod, stslib | `A1006531D4D8E7073F77CBF6E59E810B8B627D16666CC4D1ABB8EA4A5C49EFA7` |
| Workshop Mod | yUi | yUi | 2.2.1 | [1879864511](https://steamcommunity.com/sharedfiles/filedetails/?id=1879864511) | basemod, stslib | `F34E32DBF2DB3BCAFAC4904631E63AD72B9AA98031ECDD908557C5184E44B4DD` |
| Workshop Mod | Act Like it! | actlikeit | v1.2.8 | [1934902042](https://steamcommunity.com/sharedfiles/filedetails/?id=1934902042) | basemod | `3DDA7C89AC9E18E632AF9079E4A1F70324F3B8EFD8C48535F2595B55482D6B3D` |
| Workshop Mod | Better Synergies | BetterSynergies | 1.1 | [2013374906](https://steamcommunity.com/sharedfiles/filedetails/?id=2013374906) | basemod | `46A05396BD0C53C193CD41782391651DBCEEA705789A84FA1CFA0AF237719D02` |
| Workshop Mod | BshForSts | BshForSts | 1.0.0 | [2130981996](https://steamcommunity.com/sharedfiles/filedetails/?id=2130981996) | basemod | `C4FA2C72C431B7D8D2315C8E7C02CB0D5EC07A5184DFDDEF95CE22381F58A2B7` |
| Workshop Mod | Communication Mod | CommunicationMod | 1.2.1 | [2131373661](https://steamcommunity.com/sharedfiles/filedetails/?id=2131373661) | basemod | `12B99249ECCFD5245DDB0B6B7575E1A1DFBA0CE0ED6FAD5BD5BBD4A303897EF5` |
| Workshop Mod | Together in Spire | spireTogether | 6.4.20 | [2384072973](https://steamcommunity.com/sharedfiles/filedetails/?id=2384072973) | basemod, stslib | `F5B4313A29A58C0B35F5022D2019E26DE7137F2C8559BDE433BFF7A2ECEEFBCB` |
| Workshop Mod | MusicTipLib | MusicTipLib | 2.7.3 | [2448191360](https://steamcommunity.com/sharedfiles/filedetails/?id=2448191360) | basemod | `E979424252EC738C12F030D6F3AF4731A0294FA27528D432CC6654328CDDFA32` |
| Workshop Mod | Anm2 Player | Anm2Player | 1.3.4 | [2545997486](https://steamcommunity.com/sharedfiles/filedetails/?id=2545997486) | — | `13C6C9672CD026EF81354436F25B932D7BA77EC404547E158E9C5656FD17061C` |
| Workshop Mod | Lazy Man Kits | LazyManKits | 1.4.13 | [2554005913](https://steamcommunity.com/sharedfiles/filedetails/?id=2554005913) | basemod | `319C3A9D0CE44686E179CE69A009A518BA9B7A281933F7F067128ADC686879D2` |
| Workshop Mod | Better Animation（更好的动作Mod） | Better_Animation | 0.2.0 | [2554778215](https://steamcommunity.com/sharedfiles/filedetails/?id=2554778215) | basemod | `8A9BEC1B9BE2C4350672DBD8C88EC8D41FB8961B5D7F773EAC4EAA35E5630EF2` |
| Workshop Mod | Clickable Orbs | ClickableOrbs | 0.0.1 | [2633214568](https://steamcommunity.com/sharedfiles/filedetails/?id=2633214568) | basemod, stslib | `13878F5839E87C7DE60E5109D026D757F6F77BD8511AF2DF237A1CB48E06F414` |
| Workshop Mod | Downfall Char Boss API | downfallcharbossapi | 1.1.0 | [2708878699](https://steamcommunity.com/sharedfiles/filedetails/?id=2708878699) | basemod, downfall | `DF0BE1CFF02AEAFF13E282806B5C1D5C3B19B41EF6D76202E8C42539037078AD` |
| Workshop Mod | RULib | RelicUpgradeLib | 1.0.1 | [2769174299](https://steamcommunity.com/sharedfiles/filedetails/?id=2769174299) | — | `0C213580AEF2D94CF0E8AB84E545634D7930E29B370047D4378E0527F6C15D71` |
| Workshop Mod | EUI | extendedui | 4.5.4-hotfix03 | [2788071529](https://steamcommunity.com/sharedfiles/filedetails/?id=2788071529) | basemod | `79730D4D0836A251E2FC4FA2765024C0C52A8FF845DBB8383562ECFC9D11D2AA` |
| Workshop Mod | Reskin the Spire | gm-reskin | 1.0.4 | [2798024345](https://steamcommunity.com/sharedfiles/filedetails/?id=2798024345) | basemod, Anm2Player | `7C5E676C045C17914DF136E031A2976E73B83FED697E44FE765B21895ABE54D8` |
| Workshop Mod | Loadout Mod | loadout | 1.2.4 | [2814267979](https://steamcommunity.com/sharedfiles/filedetails/?id=2814267979) | basemod, stslib | `6D8295565C12D517C6928FB97571325588D66D5E99025F9BBFDA2007ED58994C` |
| Workshop Mod | FriendlyMonsters | FriendlyMonsters | 1.1.0 | [2816293692](https://steamcommunity.com/sharedfiles/filedetails/?id=2816293692) | basemod | `292AD0C47554AFFF844E0A89613DD6617040040885AE1DDFB624E69BCE19A90F` |
| Workshop Mod | Ascension Manager | ascensionmanager | 1.0.0 | [2870621729](https://steamcommunity.com/sharedfiles/filedetails/?id=2870621729) | basemod | `92224F82FB20BDEF821D53E00094080B999133A8C7A8A437D39CB7C8F1E403B9` |
| Workshop Mod | AKDream's More Relics | AKDsMoreRelics | 1.6.3 | [2901671450](https://steamcommunity.com/sharedfiles/filedetails/?id=2901671450) | basemod, stslib | `9D19E0E06C2B3D43F954AC01045FDE6F9A22D21B8D861A38CADCDD3DE1BD85E3` |
| Workshop Mod | Bundle Of Bundles | bundlecore | 9.3.2 | [2915571146](https://steamcommunity.com/sharedfiles/filedetails/?id=2915571146) | basemod, stslib | `B9905AA3D020A8C655C42A0C44C62F5F251AB62A701005142C49B6C02B96B373` |
| Workshop Mod | Fabricate | pinacolada-fabricate | 4.3.2 | [2947433143](https://steamcommunity.com/sharedfiles/filedetails/?id=2947433143) | basemod, stslib, extendedui | `B470006B96D09BA6ABF3DFAE0518F86AF83CEF5FDD5ED85B177C0879CDD16EFB` |
| Workshop Mod | Texture Replacer | texturereplacer | 1.1 | [2961840292](https://steamcommunity.com/sharedfiles/filedetails/?id=2961840292) | basemod | `A87FA66E174687CBC26548E2813A07ED642707E99F4E75CA9F99590699043514` |
| Workshop Mod | Chimera Cards | CardAugments | 1.0.5 | [2970981743](https://steamcommunity.com/sharedfiles/filedetails/?id=2970981743) | basemod, stslib | `610C44AD167F2726ED662BC28A89F5E822C03BD5D78FB77AF36DC0AD6C94776A` |
| Workshop Mod | Shammy Lib | shammy-lib | 0.0.1 | [3005590935](https://steamcommunity.com/sharedfiles/filedetails/?id=3005590935) | basemod, stslib | `067A870C741058B661CC3844F4977A56A8D45F1D80D70DB52BFBBEBF2181D799` |
| Workshop Mod | Defense is the Best Offense | DefenseBestOffense | 0.1.0 | [3020919562](https://steamcommunity.com/sharedfiles/filedetails/?id=3020919562) | basemod, stslib | `FF47C30A69566441A741EAC9BB770C4E3093DF8FC785D79135B25638A90E6303` |
| Workshop Mod | Script The Spire | ScriptTheSpire | 1.0.0 | [3038839709](https://steamcommunity.com/sharedfiles/filedetails/?id=3038839709) | basemod | `9CD641FF512D565CEC32E8DF451004ECE92076C146B63CF6C548C4D2A7247CC1` |
| Workshop Mod | Lights Out | LightsOut | 0.0.5 | [3133446987](https://steamcommunity.com/sharedfiles/filedetails/?id=3133446987) | basemod, stslib | `C0EFE1D0376DAF66671A680B06B8559ABCF38366DA50348B272AA274E99A31C8` |
| Workshop Mod | 视频播放工具VideoTheSpire | VideoTheSpire | 1.0.0 | [3189856464](https://steamcommunity.com/sharedfiles/filedetails/?id=3189856464) | — | `4085DDFA563EA76F8F0EC6EF2B6A71BC8E4CFFEE41C91D24B544A643A8CC3172` |
| Workshop Mod | Dice of Fate | diceoffate | 1.1.0 | [3334117298](https://steamcommunity.com/sharedfiles/filedetails/?id=3334117298) | basemod | `26AC9E52C701E6BE353C81AE40BC0331509B8C54AD1C2E90AAFDEDF09576A9C4` |
| Workshop Mod | STS Service Framework | ypp-rpc | 0.1.5 | [3338653644](https://steamcommunity.com/sharedfiles/filedetails/?id=3338653644) | basemod | `797890B015FDB8ABD2AF8F9F92BBB02A14ADCE92738024EB238A8726E892FE2B` |
| Workshop Mod | STS Metrics | sts-metrics | 0.1.3 | [3338653921](https://steamcommunity.com/sharedfiles/filedetails/?id=3338653921) | basemod, ypp-rpc | `4BCBAE6D9D8EBFB2AFD9D694AD08BF819C4D76B9C91E5239FC302066028BC40C` |
| Workshop Mod | Library of Ruina Fix | LORFix | 0.0.1 | [3356036058](https://steamcommunity.com/sharedfiles/filedetails/?id=3356036058) | basemod, stslib | `076902BB2493C3ADEF76D43E6FC893C72930578D92833F7DDB603175790BA792` |
| Workshop Mod | Monster B Gone Fix | MBGFix | 0.0.1 | [3356036058](https://steamcommunity.com/sharedfiles/filedetails/?id=3356036058) | basemod, stslib | `C63AD166D30AE7B3FF26349CC965C7018D69A683267833706B1D26CBF267BC9E` |
| Workshop Mod | PepperLoader | PepperLoader | 1.7.0.4 | [3356036058](https://steamcommunity.com/sharedfiles/filedetails/?id=3356036058) | basemod, stslib, bundlecore | `0E7A6E56BBB845B5AB894DCA1DDB185377444B4AEC21D5A0A4BD0C2FF577DB02` |
| Workshop Mod | Soul Bound Fix | SoulboundFix | 0.0.1 | [3356036058](https://steamcommunity.com/sharedfiles/filedetails/?id=3356036058) | basemod, stslib | `1EC85E695A520DB331F0D10561A4D2FDCDCC4D8CE4A85B4B48DFB9C5A391CFB5` |
| Workshop Mod | Shop Grid | shopgrid | 1.1.0 | [3368820915](https://steamcommunity.com/sharedfiles/filedetails/?id=3368820915) | basemod | `D85D807DAB4B9BDADBE1572CA3DFCC82130DF1BB08FC3BBC34380960FFD521ED` |
| Workshop Mod | Npc Feminization | NpcFeminization | 0.2 | [3372712228](https://steamcommunity.com/sharedfiles/filedetails/?id=3372712228) | — | `8FB75C76DBA15212CDFDBDEB5F4834CD39A92BFE66C9814933D26DC6E6C69C1F` |
| Workshop Mod | STS Metrics Local | sts-metrics-local | 0.1.1 | [3384855730](https://steamcommunity.com/sharedfiles/filedetails/?id=3384855730) | basemod | `1CC124E3AC2436D2B5469E093BEB2E26EEB27F5811473B2E407099D0E0C27001` |
| Workshop Mod | Mod成就Achievement | ModAchievement | 0.0.1 | [3420913574](https://steamcommunity.com/sharedfiles/filedetails/?id=3420913574) | — | `AE1D8AEC537AF70A4EC55AECC84E220148DAC440D32709F21BD09FC848F09F80` |
| Workshop Mod | STS Signature Lib | SignatureLib | 6.0.6 | [3433319964](https://steamcommunity.com/sharedfiles/filedetails/?id=3433319964) | basemod | `6CE3CF8C23D5E299B7BDF6913BB148F0CC141539684F96789636DA5FAFAB4C17` |
| Workshop Mod | 多人游戏增益共享 | sts_mp_override | 1.0 | [3465836194](https://steamcommunity.com/sharedfiles/filedetails/?id=3465836194) | basemod, spireTogether | `6A9C2271C11066AA9B458682847016D55662F7DED9EAE3755B0CA70F8D401083` |
| Workshop Mod | 尖塔卡面娘化+萌化 | MoeAndFemTheSpire | 1.0.0 | [3506704233](https://steamcommunity.com/sharedfiles/filedetails/?id=3506704233) | basemod | `ABE531356459B9A662F807BD5181E8EF2E4EEF8B732302BE32E4A1FAE56A6EF4` |
| Workshop Mod | TreeHole_Mod(树洞) | TreeHoleMod | 0.7.0 | [3537874513](https://steamcommunity.com/sharedfiles/filedetails/?id=3537874513) | basemod | `1DD7B79E20FBBFCC6B1EEF4475BCE05F2833470923ADA8837FC53F0A68A16220` |
| Workshop Mod | Ryoiki Tenkai（领域展开） | RyoikiTenkai | 1.1.5 | [3549855500](https://steamcommunity.com/sharedfiles/filedetails/?id=3549855500) | basemod | `0A5064032BB82F610000258C03BE9D38C8B8D5F5DF9DFB1D780CA950E3E04580` |
| Workshop Mod | BaseModEx | BaseModEx | 1.3.0 | [3617683629](https://steamcommunity.com/sharedfiles/filedetails/?id=3617683629) | basemod | `2CCB39536C136E4D36B96F26D2712720CAD3EED9CD3EE8DF8D09BCF6849238E6` |
| Workshop Mod | 蛊真人(Reverend Insanity) | GuZhenRen | 1.0.0 | [3701087103](https://steamcommunity.com/sharedfiles/filedetails/?id=3701087103) | basemod, stslib | `B9810902AE6140183A5AC3845E7B90941A762210D739F6CAEBE03E16C15B28FB` |
| Workshop Mod | Merchant Feminization | MerchantFeminization | 0.1.1 | [3718263434](https://steamcommunity.com/sharedfiles/filedetails/?id=3718263434) | — | `4BBE000E5F228E93E73628559BDFF7924C4410AF2E1F9A50DFBD9F6A88C08E6B` |
| Workshop Mod | Pick All Boss Relics | PickAllBossRelics | 1.1.3 | [3756209214](https://steamcommunity.com/sharedfiles/filedetails/?id=3756209214) | basemod | `25E867756A50FC3A43C593411DE36D8A29A987B0132C27976A20B5670254F36F` |
| Workshop Mod | Expanded Chest Relics | expandedchestrelics | 1.0.0 | [3769603861](https://steamcommunity.com/sharedfiles/filedetails/?id=3769603861) | — | `7FF579268D61A2AAB4CF3FEF679D0D58B1BF1D32D1A9C129CE74C790BEE09330` |
| Workshop Mod | TheCrimsonEyedRedux.jar | — | 未声明 | [3782761370](https://steamcommunity.com/sharedfiles/filedetails/?id=3782761370) | — | `25187476DD3BD3A25ED9527AB7144858E3A74412DADDFA3E3A4FF50A42DC3329` |
| Optional Mod API | Downfall | downfall | 6.0.20 | [1610056683](https://steamcommunity.com/sharedfiles/filedetails/?id=1610056683) | basemod, stslib | `E649B239731986B91FC6010D2BE5509CB53889D3F3B1C7C6AC25E1DD7EEE1B98` |
