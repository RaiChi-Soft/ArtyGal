《炽焰炮阵：铸锋少年》TUI Galgame

少年以毕生热忱献身火炮军械，深耕火炮设计、实弹调校、阵地战术，以炮为魂、以火为志，热血逐梦军械之路。

## 目录

- `galgame.py`：Python/Textual 游戏本体。
- `resources/`：运行资源，包含 ANSI 图、`Drafting_the_Final_Gear.mp3`、`artygal.ico`。
- `scripts/build_windows.ps1`：Windows 单文件打包脚本。
- `tools/`：资源转换脚本。
- `release/`：打包产物。

## 打包

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```
