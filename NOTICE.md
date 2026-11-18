# NOTICE / 第三方与许可

本补丁（男娘恋爱物语·屏幕阅读器支持补丁 0.1.1.0）为游戏追加的辅助文件，
**不包含游戏本体资源**（不含任何图片、音频、剧本、台词文件，也不分发引擎二进制）。

## 随包第三方文件

| 文件 | 来源 | 许可 | 说明 |
|---|---|---|---|
| `mod\nvdaControllerClient64.dll` | NV Access（NVDA 项目发布的控制器客户端） | LGPL-2.1 | 原样复制、未修改；用于让游戏进程把朗读文本发给正在运行的 NVDA。LGPL-2.1 全文见 <https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html>。若不需要可删除，补丁会自动回落到争渡 / Windows SAPI。 |

**不随包分发的第三方组件**：

- **争渡读屏（ZDSR）**：补丁通过 `ZDSRAPI_x64.dll` / `ZDSRAPI.dll` 的
  `InitTTS` / `Speak` / `GetSpeakState` / `StopSpeak` 接口调用本机安装的争渡。
  这些 dll 是争渡读屏的产物，**本仓库不分发**；模组只在运行时查找并加载
  用户自己安装的那一份（或用户自己放进游戏根目录的那份）。
  接口签名依据争渡随软件分发的官方 `ZDSRAPI.txt`；打包机上的实现参考了
  同作者 A11yFramework 的 `A11yZdsrBackend`（本机跑通、PE 导出表核对过）。
- **Ren'Py 8.5.2**：读取并使用游戏自带的引擎公开机制
  （自语音 `renpy.display.tts`、焦点事件 `renpy.display.focus`、键位机制
  `renpy.Keymap`、测试框架 `renpy/test`），**不分发、不修改引擎文件**。

## 参考与致谢

- 设计思路与 NVDA 控制接口的调用方式参考了同作者作品
  **OurBriefEternityForAccessibility**（MIT 许可）中的 Ren'Py 无障碍实现；
  本补丁为独立实现（不同文件结构、不同接口分层），不是其代码的直接拷贝。
- 引擎侧能力来自游戏自带的 Ren'Py 8.5.2；补丁只调用这些公开机制。
- 交互形态与操作语义依据 **Framework/docs/交互形态纪律.md** 与
  **Framework/docs/操作逻辑公约.md**（内部规范）。
- 本补丁的自动化验证使用了作者自建的 Ren'Py 无头测试台（游戏副本 +
  引擎自带 `test` 命令 + 语音日志断言），不随发布包分发游戏副本。

## 游戏版权

《男娘恋爱物语》（Femboy Love story）及其全部资源版权归 **磷光工作室** 所有。
本补丁只包含代码与配置，玩家需自行拥有正版游戏。

## 许可

本补丁代码（`mod\game\a11y_platform\*.rpy`、`tools\*.ps1`、文档）以 MIT 许可提供，
可自由修改与再分发，保留本 NOTICE 即可。完整 MIT 文本见 [LICENSE](LICENSE)。

简要说明：

- **可自由使用、修改、再分发**（含商用），但须标注出处 —— 本仓库地址与作者
  Nornageste-mh；若你做了修改，须注明「已修改」，不得让人误以为修改版出自原作者。
- **按「现状」提供，不承担任何责任**：因使用本软件导致的游戏存档损坏、游戏崩溃、
  账号受限、或与游戏厂商及任何第三方产生的争议与索赔，作者与贡献者均不负责。
