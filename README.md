# Mesh Converter

A tiny desktop GUI for batch-converting 3D mesh files (FBX, OBJ, STL, glTF, PLY, DAE, 3DS, X3D, …) on **macOS / Linux / Windows**.

Built because I wanted to turn a folder full of `.fbx` files into something I could just preview in Finder (`OBJ` works with macOS QuickLook — press space and you see the model).

中文说明在下方 ↓

---

## Why this exists

The most popular tool for FBX → voxel/.vox conversion on the internet is [FileToVox / MeshToVox](https://github.com/Zarbuz/FileToVox), but it's a Windows-only Unity build and won't run natively on macOS or Linux. For most use cases I just wanted **OBJ** anyway (so the file opens with the OS file preview, Blender, or any DCC tool). So this is a thin GUI on top of [Open Asset Import Library (`assimp`)](https://github.com/assimp/assimp), which is already cross-platform and supports dozens of formats.

If you specifically need `.vox` voxel output, see the *Voxel output* section at the bottom.

---

## What it does

- Add files one-by-one, or drop a whole folder (recursive scan).
- Pick an output format from the dropdown (OBJ, glTF 2.0, STL, PLY, FBX, DAE, X3D, 3DS).
- Pick an output directory, or leave it as "same as input" to put `.obj` next to each `.fbx`.
- Click **Convert**. Each file is processed via `assimp export`. Errors and successes show in the log; overall progress shows in a bar.
- "Overwrite" toggle — by default it skips files whose output already exists.

No telemetry, no network, ~250 lines of pure stdlib Python (Tkinter).

---

## Requirements

| Dependency | macOS | Linux | Windows |
|---|---|---|---|
| Python 3.8+ with Tkinter | system Python 3 already has it (`/usr/bin/python3`); Homebrew's may not — see "Tkinter" below | `apt install python3-tk` (Debian/Ubuntu) | bundled with the official python.org installer |
| `assimp` CLI on `PATH` | `brew install assimp` | `apt install assimp-utils` or build from source | [download a release](https://github.com/assimp/assimp/releases) |

### Tkinter on macOS

If `python3 -c "import tkinter"` fails on your Homebrew Python, either:

- Use the macOS system Python: `/usr/bin/python3 mesh_converter.py` (always has Tk), **or**
- Install the matching Tk for your Homebrew Python, e.g. `brew install python-tk@3.12`.

---

## Install & run

### Option A — download the prebuilt macOS app (arm64, no Python needed)

1. Grab the latest `MeshConverter-macos-arm64.zip` from [Releases](https://github.com/Zachary002/mesh-converter/releases).
2. Unzip — you get `Mesh Converter.app`. Drag it to `/Applications` (optional).
3. **First launch**: macOS will say "cannot be opened because the developer cannot be verified" (the app isn't signed). Either:
   - Right-click the app → **Open** → **Open** in the confirmation dialog, or
   - Run once: `xattr -cr "/Applications/Mesh Converter.app"` then double-click.
4. Install `assimp` if you haven't: `brew install assimp`. The app shows a warning in its log if it can't find it.

The prebuilt is **macOS arm64 only** (Apple Silicon). Intel Macs / Linux / Windows: use Option B.

### Option B — run from source

```sh
git clone https://github.com/Zachary002/mesh-converter.git
cd mesh-converter
brew install assimp                       # if you don't have it yet (macOS)
/usr/bin/python3 mesh_converter.py        # macOS — uses system Python so Tk is guaranteed
# or, if your `python3` has Tk:
python3 mesh_converter.py
```

A window opens. That's it.

### Building the .app yourself

```sh
/usr/bin/python3 -m venv .venv-build
source .venv-build/bin/activate
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "Mesh Converter" mesh_converter.py
# result: dist/Mesh Converter.app
```

---

## Usage

1. **Add files** — *Add files…* picks individual meshes; *Add folder…* scans a whole directory tree.
2. **Pick output format** — defaults to OBJ. The other formats in the dropdown are anything `assimp` can write.
3. **Pick output dir** *(optional)* — defaults to writing next to each input file. If you choose one, every output file lands flat in that single folder.
4. **Overwrite?** Off by default — existing files are skipped (you'll see "skip (exists)" in the log).
5. **Convert** — runs in a background thread so the UI stays responsive. Watch the log for per-file ✓/✗ lines.

### Command-line equivalents

If you don't want a GUI, here's exactly what the tool runs:

```sh
# single file
assimp export input.fbx output.obj -f obj

# batch (zsh/bash)
for f in /path/to/dir/*.fbx; do
  assimp export "$f" "${f%.fbx}.obj" -f obj
done
```

---

## Voxel (`.vox`) output

`assimp` does **not** produce voxel `.vox` files (it's a mesh library). If you need MagicaVoxel-compatible `.vox`, use [vengi-voxconvert](https://github.com/vengi-voxel/vengi/releases) — it has a native macOS arm64 build and accepts FBX/OBJ/glTF as input:

```sh
# install (no Homebrew formula; download mac-vengi-voxconvert-app.zip from releases)
VC=~/Applications/vengi/vengi-voxconvert.app/Contents/MacOS/vengi-voxconvert
"$VC" -set voxformat_voxelizemode 1 -set voxformat_scale 0.1 \
      --input model.fbx --output model.vox
```

`voxformat_scale 0.1` is important for any mesh bigger than a few thousand units — without it, voxelization can OOM.

I might bake `.vox` support into this GUI later. Issues / PRs welcome.

---

## License

MIT — see [LICENSE](LICENSE).

---

# 中文说明

一个简单的 3D 网格批量转换桌面工具。最初是为了把一堆 `.fbx` 模型转成 `.obj`，这样在 mac 的访达里按空格键就能直接预览，而不用安装专门的 3D 软件。

## 它能做什么

- 添加多个文件，或拖一个文件夹（递归扫描所有支持的格式）
- 选输出格式：OBJ / glTF 2.0 / STL / PLY / FBX / DAE / X3D / 3DS
- 选输出位置（默认放在原文件旁边）
- 点 **Convert** 一键批量转换；带进度条和日志
- "Overwrite" 开关 —— 默认跳过已存在的输出

底层是 [assimp](https://github.com/assimp/assimp)，跨平台、格式覆盖广。代码只有约 250 行纯标准库 Python（Tkinter），无第三方依赖、无网络请求。

## 依赖

- **Python 3.8+ 且带 Tkinter**：mac 系统自带的 `/usr/bin/python3` 一定带，Homebrew 的 python 不一定带（必要时 `brew install python-tk@3.x`）
- **assimp**：`brew install assimp`（mac）/ `apt install assimp-utils`（Debian/Ubuntu）/ [Windows release](https://github.com/assimp/assimp/releases)

## 安装运行

### 方案 A：直接下载 mac 打包好的 .app（Apple Silicon arm64）

1. 去 [Releases](https://github.com/Zachary002/mesh-converter/releases) 下载 `MeshConverter-macos-arm64.zip`
2. 解压得到 `Mesh Converter.app`，拖进 `/Applications`（可选）
3. **首次打开**：mac 会提示"无法验证开发者"。右键 → **打开** → 再点 **打开** 即可；或执行 `xattr -cr "/Applications/Mesh Converter.app"` 后再双击
4. 装 assimp：`brew install assimp`。如果没装，App 启动后会在日志区提示

只有 mac arm64 版本（Intel mac / Linux / Windows 请用方案 B）。

### 方案 B：从源码运行

```sh
git clone https://github.com/Zachary002/mesh-converter.git
cd mesh-converter
brew install assimp
/usr/bin/python3 mesh_converter.py
```

## 不想用 GUI？直接命令行

```sh
# 单文件
assimp export 输入.fbx 输出.obj -f obj

# 批量（同目录）
for f in /某目录/*.fbx; do
  assimp export "$f" "${f%.fbx}.obj" -f obj
done
```

## 需要 `.vox` 体素输出？

assimp 不输出体素格式。用 [vengi-voxconvert](https://github.com/vengi-voxel/vengi/releases)（mac arm64 原生），命令在英文版本里。后续可能把 .vox 输出也集成进这个 GUI。

## License

MIT
