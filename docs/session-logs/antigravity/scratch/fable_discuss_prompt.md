# Discussion Brief for Fable 5.2: Tomorrow's LaTeX Presentation Deck

You are collaborating on preparing a visually clear, high-impact **LaTeX presentation (`16:9` Beamer deck)** in `/home/wabiwabi/silicon-notebook/benchmark-deepeval/.worktrees/ssap/docs/presentation/` for the user's live group/progress report **tomorrow**.

**THIS TURN IS DISCUSSION & ENVIRONMENT DISCOVERY ONLY — DO NOT WRITE OR MODIFY ANY REPO FILES YET.**

## 1. Context & Strict Guardrails (`AGENTS.md`)
- Read `/home/wabiwabi/silicon-notebook/benchmark-deepeval/.worktrees/ssap/AGENTS.md` first.
- **Strict Blind-Cluster & Anti-Leakage Rule**:
  - Do NOT read raw `docs/server-info/*.json` directly. Instead, read our pre-scrubbed, `BlindBoundary`-verified fact pack at:
    `/home/wabiwabi/.gemini/antigravity/brain/9cde5e0b-3c8c-47a3-9b93-95bdabd5c9f9/scratch/verified_visible_facts.json`
  - Also read `docs/alw-experiment-walkthrough-plain.md`, `docs/alw-deployment-log.md`, and inspect 1–2 visible `dev` tasks (e.g., `#2` `sky130-adb-buf-ppsf-bs-gain1-sfdr90-layout` or `#21` `sky130-adb-ota-5t-gain40-pm60-noise50uv-pvt-layout`) plus `container/alw/bin/` and `src/ssap/eval/{proposer_sandbox.py,auto_loop.py}`.
  - The 3 frozen internal blind clusters (`4` dev tasks, `8` Phase 1c runs) MUST ONLY appear as aggregate counts (`3 个内部冻结盲簇合计`), NEVER by task number, task ID, cluster ID, or per-run detail.
  - Zero real usernames, hostnames, IPs, or secrets (`<USER>`, `<HOST>`, `<GATEWAY_URL>`).
  - Separate measured `[事实]` from tonight's pending `[待填槽位]` — never invent unmeasured numbers.

## 2. User's Core Presentation Needs
The user needs listeners who do NOT know ALW or MCR internals to clearly understand:
1. **任务是什么**：AnalogLayoutWorld (40 SKY130 130nm analog layout tasks) — what goes in (`circuit.spice` netlist + PDK rules + electrical specs/testbenches), what comes out (`submission/layout.gds`), and how the 5-stage signoff waterfall (`GDS -> DRC -> LVS -> PEX -> Post-Sim`) computes $Y^\star \in [0, 1]$ and $C^\star \in \{0, 1\}$.
2. **Agent 具体怎么操作把「网表 -> GDS 文件」**：Concretely demystify how Claude Code operates inside the container (not black-box magic: reading `circuit.spice`, running single-PCell extraction experiments in `work/exp/`, writing modular Python `klayout.db` / Magic Tcl layout scripts `devices.py` + `build.py` + router in `work/draft/src/`, running DRC/LVS CLI tools, promoting via `mcr_promote`, illustrated with the real `#2 buf_ppsf_bs` visible execution trace).
3. **我们的优化是怎么优化的、怎么改的、改了哪里**：
   - **内层保底壳（`H_raw -> H_base`）**：改了容器哪里（`mcr_entrypoint.py` 透明垫片、`mcr_hook.py` 写保护、`mcr_promote` 6 项零参数镜像检查器 `m_1..m_6` 棘轮只进不退、双水位线 `140m/165m/180m` + 无状态 Phase B `80` 轮抢修）。
   - **外层自动演化（`H_base -> H*`，Phase 2 + Phase 3）**：49 样本主动裁判库 `B_dev`（24 终态 + 25 零 Token 双端验证合成变体） $\to$ 断网白纸 Proposer 沙盒（只看 8 道可见题失败现场，无人工提示） $\to$ 四类受控变异（Class 1 镜像门控 / Class 2 启发探针 / Class 3 报错精简翻译 / Class 4 无状态抢修优化） $\to$ Stage 0 零误杀筛查 + 语法树客观分流（`Path 1` 归档分叉重放 vs `Path 2` `B1->B2` 分批重跑） $\to$ `val` 纯净 `C1` 选模与 `test` 3 种子揭盲。
4. **轨迹怎么变、结果怎么变**：
   - **已实测闭环对比（Phase 1b $\to$ Phase 1c + Phase 2）**：具体改了哪几处（`MeteringProxy` 客户端断连脱钩、`T_warn 150m->140m`、`Delta_S_rep 15->80` 轮、`metrics_reader` 几何有效性对齐） $\to$ 容器轨迹怎么变（Phase B 不再在 22% 时间预算处因 15 轮耗尽被截断） $\to$ 结果怎么变（`24/24` 零基建误判，Phase B 棘轮晋升从 `0/3` 升至 `5/20 = 25.0%`，$\overline{Y^\star}=0.1640$，五级漏斗定位 `DRC 15/24 -> LVS 5/24` 核心断崖，49 样本 Stage 0 全绿）。
   - **今晚服务器正在跑的 Phase 3 Round 1/2 留空热插拔设计**：用户明早到工位只有很短时间填数据，必须把“今晚出来的白纸 Agent 补丁 diff、变异类别、Path 1/2 分流、单题轨迹前后变化、LVS 与 $Y^\star$ 涨分、可选版图图片框”单独抽成一个极易编辑的配置文件（如 `tonight_slots.tex`），现在渲染为美观的“运行中 / 明早填入”占位卡片，明早改几个宏重编即成完整终稿！

## 3. What to Return in Your Response
1. **Host LaTeX Toolchain & Font Check**: Check on this WSL machine what compilers (`tectonic`, `xelatex`, `lualatex`, `latexmk`) and PDF-to-PNG preview tools (`pdftoppm`, `gs`, `python3` pypdfium2/fitz) + CJK fonts (`fc-list :lang=zh`) exist, and recommend the exact build command.
2. **Visual Design System**: Recommend how to make Beamer slides look modern, clean, and executive-ready (16:9 aspectratio=169, clean custom theme without dated default Warsaw/Madrid bars, cohesive color semantics, TikZ visual components instead of bullet walls, typography hierarchy, plain Chinese explanations for every EDA term).
3. **Slide-by-Slide Blueprint**: Propose the exact 12–15 slide deck structure (title, visual layout of each slide — e.g. 2-column split, TikZ pipeline, funnel bar chart, trajectory timeline comparison, code diff card — and exact data shown).
4. **Tomorrow-Morning Hot-Swap Design**: Propose the exact macro/file interface for `tonight_slots.tex` so the user can update tonight's Round 1/2 server results in < 5 minutes tomorrow morning without touching TikZ/Beamer layout code.
