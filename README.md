# Kindle AZW3 批量转换器

Windows 桌面工具，可离线将无 DRM 的 EPUB 和 MOBI 批量转换为 AZW3。支持从文件资源管理器拖入多个文件、指定输出目录，以及查看单本转换结果。同名输出会自动编号。

## 安装与使用

1. 安装 Windows x64 版 Python 3，保留 Tcl/Tk 和 pip，并把 Python 加入 PATH。
2. 下载或克隆本仓库。在项目目录打开 PowerShell，运行一次：

   ```powershell
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\Install AZW3 Engine.ps1"
   ```

3. 双击 `Start AZW3 Converter.cmd`。把电子书拖进列表，选择输出目录后点击「开始转换」。
4. 通过 USB 把生成的 `.azw3` 复制到 Kindle 的 `documents` 目录，再从书库打开。

首次安装依赖需要联网，电子书转换在本机完成。程序无需 Calibre，也不会解除 DRM。

## 转换组件

- [Epub3-Kindle](https://github.com/cbz-tools/Epub3-Kindle) 生成 AZW3。
- [KindleUnpack](https://github.com/kevinhendricks/KindleUnpack) 提取 MOBI 的内容。
- [Kindling](https://github.com/ciscoriordan/kindling) 将旧版 MOBI 解包后的 OPF 转成中间 EPUB。
- [TkinterDnD2](https://pypi.org/project/tkinterdnd2/) 提供资源管理器拖放支持。

已在 Windows 上验证多个 EPUB 和 MOBI 格式的输出。不同 Kindle 型号和固件的实际显示效果以设备试读为准。
