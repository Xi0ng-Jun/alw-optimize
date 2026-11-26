# HANDOFF — ALW / SSAP 交接入口（2026-11-26）

本仓库是 `ssap`（MCR v2 / SSAP 工具链）在 **ALW（AnalogLayoutWorld）** 基准上的完整工作树快照，
为**跨机器交接**而建：另一台电脑上的 agent 克隆本仓库即可获得全部代码、文档、实验记录、战报与原始会话。

| 项 | 值 |
|---|---|
| 源码 HEAD | `58e3bf2`（原分支 `feat/ssap`，与服务器 `ssap alw-test` 使用的代码一致） |
| 当前擂主 | `H* = H_base + repair-cert-diagnosis + repair-lvs-artifacts` |
| val 集 | **不再使用**（协议变更，见 `docs/alw-deployment-log.md` §7.3） |
| 原始交接指令 | [`docs/handoff-2026-11-26.md`](docs/handoff-2026-11-26.md)（正文原样，仅两处路径改为新位置） |

> ⚠️ **本仓库是公开仓库（public）**。按交接要求保留了服务器路径、本机用户名与实验战报；
> 密钥类凭据在入库前单独扫描过，未发现真实 key（仅有测试里的假占位符）。

---

## 1. 一眼状态

| 事项 | 状态 |
|---|---|
| Phase 0–2（环境、`H_base` 基线、离线检验库） | 已完成 |
| Phase 3 外层循环 | 已停止。Round 1 `+0.0551`、Round 2 `+0.0116`，累计 `+0.0667`，全部来自 TIA 种子 0 一个 trial；判为抢修随机性 |
| 测试集最终评测 `ssap alw-test` | **2026-11-26 已在服务器启动，预计 17–22 小时**，结果尚未产生 |
| 最终报告 `ssap alw-report` | 未执行。**带一次性锁，只能跑一次**（第一次看到分数） |
| 幻灯片 `docs/presentation/tonight_slots.tex` | 停在 11-25 08:17，Round 1–2 结果未更新 |

测试集结果**只存在于服务器状态目录**（`$S/runs/test_runs.jsonl`、`$S/report/`），不在本仓库。
它跑完后需要人把结果带回、写进 `docs/alw-deployment-log.md`，并更新幻灯片。

## 2. 目录索引

| 路径 | 内容 |
|---|---|
| `AGENTS.md` | 仓库约定、三段不变式、本次测试集协议变更说明 |
| `README.md` | 方法概述（MCR v2 三条核心不变式）与 CLI 列表 |
| `docs/mcr-formal.tex` / `.pdf`、`docs/mcr-plain.md` | 方法形式化规格与通俗版 |
| `docs/alw-progressive-plan.md` | Phase 0–3 渐进执行计划与模块架构 |
| `docs/alw-mcr-instantiation.md` | ALW 实例化、`H_base` 契约 |
| `docs/alw-experiment-walkthrough-plain.md` | 全流程通俗走查 |
| `docs/alw-deployment-log.md` | **实测主记录**；§7 = Phase 3 两轮结果 + 测试集方案（§7.3 = 协议变更） |
| `docs/alw-server-env.md` | 评测服务器、网关同质化、代理隔离 |
| `docs/handoff-2026-11-26.md` | 原始交接指令（逐字） |
| `src/ssap/` | 包源码 |
| `src/ssap/eval/{auto_loop,proposer_sandbox,fork_eval}.py` | 外层循环（Path 1/2/3、proposer 沙箱） |
| `src/ssap/eval/holdout.py` | 测试集运行（`ssap alw-test`；测试：`tests/test_alw_holdout.py`） |
| `src/ssap/eval/c1_protocol.py` | 报告（`ssap alw-report`） |
| `src/ssap/cli.py` | 命令行入口 |
| `container/alw/`、`src/ssap/kernel/`、`src/ssap/checkers/alw/` | 保底壳 `H_base` |
| `configs/alw/config.server.json` | 服务端配置（`parallel_max = 6`） |
| `configs/alw/split.json`、`catalog.json`、`clusters.json` | 12/14/14 划分、题目目录、电路簇 |
| `docs/server-info/` | 从服务器拷回的战报与导出（Round 1/2、Phase 1c、Phase 2；已脱敏为 `<USER>`） |
| `docs/logs/hbase_chat.md` | `H_base` 阶段的对话记录 |
| `docs/presentation/` | 幻灯片 LaTeX 源码 + `alw-progress-slides.pdf`（`build/` 未入库，用 `docs/presentation/tools/render.py` 重建） |
| `.cc-history/` | Claude Code 侧会话记录（原始） |
| `docs/session-logs/antigravity/` | 主对话 transcript（Antigravity，`transcript.jsonl` / `transcript_full.jsonl` + 截图 `media/`） |

### 2.1 交接指令里的路径 → 本仓库位置

`docs/handoff-2026-11-26.md` 的正文未改写，只把两处旧机器路径换成新位置：

| 原文写法 | 现位置 |
|---|---|
| 工作目录 `…/benchmark-deepeval/.worktrees/ssap`，分支 `feat/ssap` | 本仓库根目录，分支 `main`（同一份 `58e3bf2` 代码） |
| `~/.gemini/antigravity/brain/<id>/.system_generated/logs/transcript.jsonl` | `docs/session-logs/antigravity/transcript.jsonl`（同目录另有 `transcript_full.jsonl` 与 `media/` 截图） |

其余路径原文未动：`docs/…`、`configs/…`、`src/…`、`container/…`、`.cc-history/` 在本仓库内原样存在；
`$S/…`、`~/autoalw/ssap`、`/localdata/$(whoami)/…` 只在评测服务器上有效。

原文里两句“交接时状态”已过时，读时以大表为准：

- “未提交：`.cc-history/`、`docs/presentation/`、`docs/logs/`。” → 这三个目录现已入库。
- “材料位置（本机）”标题指的是交接时的开发机，现在指本仓库。

## 3. 在新机器上恢复

```bash
git clone git@github.com:Xi0ng-Jun/alw-optimize.git
cd alw-optimize
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest                                   # 纯本地、确定性、无需 Docker
.venv/bin/ssap alw-check-split --config configs/alw/config.server.json
```

注意：

- 仓库里只有代码与文档，**没有** `var/`、运行目录、虚拟环境、Docker 镜像。
- `alw-eval` / `alw-concordance --docker yes` / `alw-loop` / `alw-test` 需要评测服务器：
  ALW 仓库、`ssap-alw-agent:2.1.302` 镜像、网关环境变量（`SSAP_MODEL` / `SSAP_GATEWAY` /
  `SSAP_UPSTREAM_KEY`）以及状态目录 `SSAP_STATE`。这些都不在仓库里，见 `docs/alw-server-env.md`
  与 transcript。
- `docs/presentation/` 的 `build/` 被 `.gitignore` 排除；重排：

  ```bash
  cd docs/presentation && python3 tools/render.py   # 用法见 docs/presentation/README.md
  ```

## 4. 服务器侧：交接时正在跑的事

测试集评测由 `ssap alw-test`（commit `58e3bf2`）启动，状态目录 `S=/localdata/$(whoami)/ssap-alw-state`。
监控命令（可反复执行）：

```bash
S="/localdata/$(whoami)/ssap-alw-state"
pgrep -u "$(whoami)" -f alw-test >/dev/null && echo "proc: RUNNING" || echo "proc: STOPPED"
for a in H_base H_raw; do echo "$a started: $(ls -d "$S"/jobs/test-$a/harbor/*/ 2>/dev/null | wc -l)/14 done: $([ -f "$S/jobs/test-$a/launch_results.json" ] && echo yes || echo no)"; done
echo "replays: $(ls "$S/test/replay/repairs" 2>/dev/null | wc -l)"
[ -f "$S/runs/test_runs.jsonl" ] && echo "TEST RUNS DONE"
```

- 两臂各 14 次、同一个池子并行 6；基础设施失败各重跑一次（目录名带 `-retry-`）。
- 两臂的 `done: yes` 要等 28 次全部跑完才同时出现。
- 显示 `STOPPED` 但没有 `TEST RUNS DONE` 时：

  ```bash
  tail -n 40 "$S/test.log" | sed "s/$(whoami)/<USER>/g"
  ```

  重跑 `$S/test.sh` 不会重复已完成的臂。
- `$S/test/manifest.json` 锁定了 `H_base` 代码哈希 `e0a8d807…` 与 `H*` 哈希 `284ac52d…`；
  **锁定后不要再改 `H*` 代码**，否则运行会拒绝继续。

出现 `TEST RUNS DONE` 后出最终表（**第一次看到分数，只能执行一次**）：

```bash
cd ~/autoalw/ssap && ssap alw-report --config configs/alw/config.server.json --seeds 1 \
  --accept-fewer-seeds --selected-version "H_base+repair-cert-diagnosis+repair-lvs-artifacts"
```

输出在 `$S/report/`（含一次性锁文件）。之后：写进 `docs/alw-deployment-log.md`，按需更新
`docs/presentation/tonight_slots.tex`。

## 5. 已知问题与未完成

1. 外层循环的 Path 1 抢修是**串行**的（约 13.5 小时一轮），`--parallel` 对它无效。
2. Path 1 晋升不会更新 `h_inc_runs.jsonl`，于是 Path 2 候选会跟 `H_base` 比
   （`src/ssap/eval/proposer_sandbox.py:350-352`）。循环已停，没修。
3. 幻灯片 `docs/presentation/tonight_slots.tex` 未更新 Round 1–2。
4. `docs/server-info/round1.txt` 首行多一行命令提示符、末尾缺一个 `}`（手工抄录痕迹）。
5. 测试集结果尚未产生；`alw-report` 的一次性锁仍在未触发状态。

## 6. 材料来源与脱敏

- `docs/server-info/` 是服务器导出的原始战报/JSON，`launch_results.json` 等已把账户名替换为 `<USER>`。
- `docs/alw-deployment-log.md`、`docs/alw-server-env.md` 内文用 `<USER>` / `<HOST>` / `<GATEWAY_URL>`
  等占位符，不含真实密钥或内网地址。
- `.cc-history/`、`docs/session-logs/antigravity/` 是**原始会话记录**，含本机路径与命令输出；
  入库前扫描过 `sk-*`、`Bearer`、`ghp_*`、私钥等模式，未发现真实凭据（只有测试里的假值）。
  如果之后要公开分享本仓库，建议先剔除这两个目录。
- 盲区题逐题明细（`stage1_result.json`、`repair_results.jsonl`）按约定留在服务器，未入库。

## 7. 建议的第一件事

1. 读 `AGENTS.md` → `docs/alw-deployment-log.md` §7（含 §7.3 协议变更）。
2. 在服务器上执行第 4 节的监控命令，确认 `alw-test` 还在跑、已完成的臂数。
3. 等 `TEST RUNS DONE`；**先不要**动 `H*` 代码，也不要重复执行 `alw-report`。
4. 拿到最终表后，按三项归因（`H_raw → H_base → H*`）写进 deployment-log §8，再更新幻灯片。
