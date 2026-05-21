# ArtyGal C++ 版

这是《炽焰炮阵：铸锋少年》的轻量 C++/FTXUI 重构版本。

## 结构

- `../assets/story.gal`：外部剧本文件，剧情不写在 C++ 代码里。
- `../ansi_art/*.ans`：角色和场景 ANSI 图。
- `../tools/export_story.py`：从 Python 原型导出并扩展剧本。
- `../tools/embed_resources.py`：把剧本和 ANSI 图 gzip 压缩后生成 C++ 头文件。
- `src/main.cpp`：FTXUI 播放器、剧本解析、ANSI 真彩色渲染、存读档。

## 构建

需要 CMake、C++20 编译器、Python3、zlib。FTXUI 会由 CMake FetchContent 拉取。

```powershell
$env:PATH = "C:\Software\Coding\ninja-win;C:\Software\Coding\msys2\mingw64\bin;C:\Software\Coding\msys2\usr\bin;" + $env:PATH
cmake -S cpp -B cpp/build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build --config Release
```

如果已经在 `cpp` 目录内：

```powershell
$env:PATH = "C:\Software\Coding\ninja-win;C:\Software\Coding\msys2\mingw64\bin;C:\Software\Coding\msys2\usr\bin;" + $env:PATH
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

若网络无法从 GitHub 拉取 FTXUI，可手动把 FTXUI 放到 `cpp/vendor/FTXUI`，或配置：

```powershell
cmake -S cpp -B cpp/build -G Ninja -DCMAKE_BUILD_TYPE=Release -DARTYGAL_FTXUI_DIR=D:/path/to/FTXUI
```

Linux:

```bash
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build -j
```

生成的程序是 `artygal` / `artygal.exe`。发布时只需要这个单个可执行文件，剧本和 ANSI 图已经压缩嵌入。

## 更新剧情

编辑 `assets/story.gal` 后重新构建即可。若要从 Python 原型重新导出：

```powershell
python tools/export_story.py
```
