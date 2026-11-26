# ALW 实验进展汇报幻灯片（16:9 LaTeX Beamer）

成品 PDF：[alw-progress-slides.pdf](alw-progress-slides.pdf)（共 17 页：15 页主汇报 + 2 页备用表）。

## 1. 目录结构

- `main.tex`：主幻灯片（第 1–12、15 页为已实测事实与机制拆解；第 13–14 页自动读取 `tonight_slots.tex`）。
- `theme.tex`：配色、字体（WSL 自动加载微软雅黑 + Consolas，Linux/Overleaf 自动回退至标准 `ctexbeamer` 字体）与 TikZ 组件。
- `facts.tex`：由 `tools/gen_facts.py` 从实测配置与同步数据自动生成，请勿手改。
- **`tonight_slots.tex`**：**明早到工位唯一需要更新的文件**（未填项自动渲染为橙色「明早填入」标签，即使只填一部分也能正常编译展示）。
- `tools/fill_slots.py`：纯 Python 3 标准库脚本，从服务器战报一键填入 `tonight_slots.tex`，内置 8 道可见题白名单与防泄漏门卫。
- `tools/render.py`：自动寻找 `tectonic` / `latexmk` / `xelatex` 编译更新 `alw-progress-slides.pdf`，并可导出逐页 PNG 预览。

---

## 2. 明早到工位 3 分钟更新今晚服务器结果

### 第一步：在服务器上打包今晚的脱敏战报与补丁（复制 `< 400B` 命令到服务器执行）

```bash
S="/localdata/$(whoami)/ssap-alw-state/loop"
mkdir -p /tmp/r1_export && A=$(ls -d "$S"/round_1/attempt_* 2>/dev/null | sort -V | tail -1)
cp -f "$S/round_1/round_report_redacted.json" /tmp/r1_export/ 2>/dev/null || true
[ -n "$A" ] && cp -f "$A/screen/stage0_report.json" "$A/screen/candidate.patch" "$A/proposer_ws/proposal.json" /tmp/r1_export/ 2>/dev/null || true
ls -la /tmp/r1_export/
```

把服务器 `/tmp/r1_export/` 下的几个小文件拷回本机 `docs/server-info/r1_export/`（`docs/server-info/` 已 gitignore，不会误提交）。

### 第二步：一键填入 `tonight_slots.tex`

在本仓库根目录或 `docs/presentation/` 下执行：

```bash
cd docs/presentation
python3 tools/fill_slots.py --round 1 \
  --report ../server-info/r1_export/round_report_redacted.json \
  --stage0 ../server-info/r1_export/stage0_report.json \
  --patch  ../server-info/r1_export/candidate.patch \
  --proposal ../server-info/r1_export/proposal.json
```

- 如果 Round 2 今晚也跑完了，同样传 `--round 2 ...`，并可把 `tonight_slots.tex` 里的 `\slot{r2.full}{0}` 改为 `1` 展开完整两页。
- 如果想展示某一道**可见题**（仅限 `#2, #7, #11, #12, #13, #18, #21, #27`）的前后对比或放一张版图截图，把截图放进 `slots/case.png`，在 `tonight_slots.tex` 底部将 `\slot{case.show}{0}` 改为 `1` 并填好几行文字即可。

### 第三步：重新编译生成 `alw-progress-slides.pdf`

- **在本机 WSL 上编译（离线秒级，并导出逐页预览图）**：
  ```bash
  cd docs/presentation
  ~/.local/bin/uv run --no-project --with pymupdf python tools/render.py
  ```
- **在装有 `xelatex` / `tectonic` 的 Linux 机器上编译（无需 PyMuPDF）**：
  ```bash
  cd docs/presentation
  python3 tools/render.py --no-png
  ```
- **在 Overleaf 上编译**：直接把 `docs/presentation/` 除 `build/` 外的全部文件打包上传，左上角 Menu 将 Compiler 选为 **XeLaTeX** 即可一键编译。
