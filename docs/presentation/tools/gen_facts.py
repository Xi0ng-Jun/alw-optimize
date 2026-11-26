#!/usr/bin/env python3
"""Generate ``facts.tex`` and ``tools/visible_tasks.json`` for the ALW progress deck.

Every number shown in the deck is copied by this script, never typed into a slide:

* ``pack``   - the BlindBoundary-verified fact pack (``verified_visible_facts.json``);
* ``config`` - ``configs/alw/config.server.json`` and ``container/alw/Dockerfile.agent``;
* ``log``    - figures parsed by regex from ``docs/alw-deployment-log.md`` (script-extracted
               there from the server sync data). Each regex must match or the script aborts.

Cross-checks (visible + blind aggregate == all-24 totals, pack vs log) abort on mismatch.

Blind clusters: only aggregate counts are emitted. ``docs/server-info/`` and
``configs/alw/split.json`` are never opened. Python 3 standard library only.

Usage:  python3 tools/gen_facts.py --pack /path/to/verified_visible_facts.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECK = HERE.parent
REPO = DECK.parent.parent

# Display labels only (presentation wording, not measurements).
LABELS = {
    2: "推挽源随缓冲器", 7: "折叠共源共栅运放", 11: "采样反馈 OTA，增益 1",
    12: "采样反馈 OTA，增益 8", 13: "全差分两级 Miller 运放", 18: "低功耗线驱动器",
    21: "五管 OTA", 27: "跨阻放大器 TIA",
}
MIRRORS = ("m_gds", "m_lvs", "m_shape", "m_fill", "m_morph", "m_drc")
VARKEYS = {"drc_sliver": "var.drcSliver", "fill_low_ring": "var.fillLowRing",
           "lvs_missing_label": "var.lvsMissingLabel", "shape_q_over_4": "var.shapeOver",
           "shape_q_advisory": "var.shapeAdvisory", "grid_shift": "var.gridShift",
           "rotate90": "var.rotate", "gds_truncated": "var.gdsTruncated",
           "gds_renamed_top": "var.gdsRenamedTop"}


def die(msg: str) -> None:
    sys.exit(f"gen_facts: {msg}")


def tex(s: object) -> str:
    out = str(s)
    for a, b in (("\\", r"\textbackslash{}"), ("_", r"\_"), ("%", r"\%"), ("#", r"\#"),
                 ("&", r"\&"), ("$", r"\$"), ("{", r"\{"), ("}", r"\}")):
        out = out.replace(a, b)
    return out


def thousands(n: int) -> str:
    return f"{n:,}".replace(",", r"\,")


class Log:
    def __init__(self, path: Path):
        self.text = path.read_text(encoding="utf-8")

    def grab(self, pattern: str, what: str) -> tuple[str, ...]:
        m = re.search(pattern, self.text)
        if not m:
            die(f"deployment log: pattern for '{what}' not found")
        return m.groups()

    def ints(self, pattern: str, what: str) -> list[int]:
        return [int(g.replace(",", "")) for g in self.grab(pattern, what)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--pack", required=True, help="verified_visible_facts.json")
    ap.add_argument("--log", default=str(REPO / "docs" / "alw-deployment-log.md"))
    ap.add_argument("--config", default=str(REPO / "configs" / "alw" / "config.server.json"))
    ap.add_argument("--dockerfile", default=str(REPO / "container" / "alw" / "Dockerfile.agent"))
    ap.add_argument("--walkthrough", default=str(REPO / "docs" / "alw-experiment-walkthrough-plain.md"))
    ap.add_argument("--auto-loop", default=str(REPO / "src" / "ssap" / "eval" / "auto_loop.py"))
    ap.add_argument("--alw-repo", default=os.environ.get("ALW_REPO") or str(
        REPO.parents[2] / "external" / "AnalogLayoutWorld" / "repo"),
        help="AnalogLayoutWorld checkout (read as data: the agent-visible files of task #21)")
    ap.add_argument("--out", default=str(DECK / "facts.tex"))
    ap.add_argument("--tasks-out", default=str(HERE / "visible_tasks.json"))
    args = ap.parse_args()

    pack = json.loads(Path(args.pack).read_text(encoding="utf-8"))
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    log = Log(Path(args.log))
    F: list[tuple[str, str, str]] = []          # (key, value, source)

    def put(key: str, value: object, src: str) -> None:
        value = str(value)
        F.append((key, value if value.startswith("\\") or "\\," in value else tex(value), src))

    # ------------------------------------------------------------------ split (pack)
    sp = pack["split_summary"]
    for k_tex, k in (("split.total", "total_tasks"), ("split.dev", "dev"),
                     ("split.devVisible", "dev_visible"), ("split.blindClusters", "dev_blind_clusters"),
                     ("split.blindTasks", "dev_blind_tasks"), ("split.val", "val_sealed"),
                     ("split.test", "test_sealed")):
        put(k_tex, sp[k], "pack")
    tasks = sorted(pack["visible_dev_tasks"], key=lambda t: t["number"])
    if len(tasks) != sp["dev_visible"] or {t["number"] for t in tasks} != set(LABELS):
        die("visible task list does not match the expected 8 visible dev tasks")
    by_id = {t["task_id"]: t for t in tasks}

    # ------------------------------------------------------------------ config
    wm = cfg["watermarks"]
    for k_tex, k in (("wm.tMax", "t_max_sec"), ("wm.tWarn", "t_warn_sec"), ("wm.tSoft", "t_soft_sec"),
                     ("wm.repSec", "delta_t_rep_sec"), ("wm.repTurns", "delta_s_rep_turns"),
                     ("wm.minRemain", "min_remaining_for_repair_sec"),
                     ("wm.verifierSec", "verifier_timeout_sec")):
        put(k_tex, wm[k], "config")
    for k_tex, k in (("wm.tMaxMin", "t_max_sec"), ("wm.tWarnMin", "t_warn_sec"),
                     ("wm.tSoftMin", "t_soft_sec"), ("wm.repMin", "delta_t_rep_sec"),
                     ("wm.verifierMin", "verifier_timeout_sec")):
        if wm[k] % 60:
            die(f"watermark {k} is not a whole number of minutes")
        put(k_tex, wm[k] // 60, "config")
    put("res.cpus", cfg["run"]["trial_cpus"], "config")
    put("res.memGiB", cfg["run"]["trial_memory_mb"] // 1024, "config")
    put("agent.slots", len(cfg["model_homogeneity"]["slots"]), "config")
    put("agent.version", cfg["agent"]["kwargs"]["version"], "config")
    m = re.search(r"ARG CLAUDE_CODE_VERSION=(\S+)", Path(args.dockerfile).read_text())
    if not m or m.group(1) != cfg["agent"]["kwargs"]["version"]:
        die("Claude Code version differs between Dockerfile.agent and config.server.json")
    (model,) = log.grab(r"上游回报 `(deepseek-v4-1-flash)-\d+`", "upstream model")
    put("agent.model", model, "log")

    # ------------------------------------------------------------------ Phase 1c (pack)
    runs = pack["visible_phase1c_runs"]
    agg = pack["phase1c_all24_aggregates"]
    n_all, n_vis = agg["n_scored"], len(runs)
    if any(r["task_id"] not in by_id for r in runs):
        die("fact pack contains a Phase 1c run outside the visible task list")
    put("pc.n", n_all, "pack")
    put("pc.nInfra", agg["n_infra_error"], "pack")
    put("pc.meanY", f"{agg['mean_Y_star']:.4f}", "pack")
    snf = agg["seed_noise_floor"]
    put("pc.sigmaSeed", f"{snf['sigma_seed']:.4f}", "pack")
    put("pc.seedMeanZero", f"{snf['seed_means']['0']:.4f}", "pack")
    put("pc.seedMeanOne", f"{snf['seed_means']['1']:.4f}", "pack")
    tx = agg["taxonomy_counts"]
    put("pc.taxMirror", tx["public_mirror_execution_gap"], "pack")
    put("pc.taxElec", tx["electrical_or_hidden_info_gap"], "pack")
    put("pc.taxGds", tx["missing_or_invalid_gds"], "pack")
    put("pc.taxCap", tx["capability_bound"], "pack")
    put("pc.nNotPassed", sum(tx.values()), "pack")
    for name in MIRRORS:
        c = agg["mirror_concordance"][name]
        short = name[2:]
        put(f"conc.{short}.agree", c["agree"], "pack")
        put(f"conc.{short}.excluded", c["excluded_bottom_or_missing"], "pack")
        put(f"conc.{short}.falseReject", c["m0_d1_false_reject"], "pack")
        put(f"conc.{short}.falseCertify", c["m1_d0_false_certify"], "pack")

    vis_sum_y = sum(r["Y_star"] for r in runs)
    vis = {"gds": sum(r["d_star"]["gds"] == 1 for r in runs),
           "drc": sum(r["d_star"]["drc"] == 1 for r in runs),
           "lvs": sum(r["d_star"]["lvs"] == 1 for r in runs),
           "promoted": sum(bool(r["ratchet_promoted"]) for r in runs),
           "gate": sum(bool(r["gate_triggered"]) for r in runs),
           "tsoft": sum(bool(r["t_soft_stop"]) for r in runs),
           "requests": sum(r["proxy_requests"] for r in runs)}
    put("vis.n", n_vis, "pack")
    put("vis.meanY", f"{vis_sum_y / n_vis:.4f}", "pack")
    for k in ("gds", "drc", "lvs", "promoted", "gate"):
        put(f"vis.{k}", vis[k], "pack")
    put("vis.promotedStillLow", sum(1 for r in runs if r["ratchet_promoted"] and r["Y_star"] <= 0.1 + 1e-9),
        "pack")
    put("vis.wallMin", f"{min(r['wall_sec'] for r in runs):.0f}", "pack")
    put("vis.wallMax", f"{max(r['wall_sec'] for r in runs):.0f}", "pack")
    n_blind = n_all - n_vis
    blind_mean = (agg["mean_Y_star"] * n_all - vis_sum_y) / n_blind
    put("blind.nRuns", n_blind, "pack")
    put("blind.meanY", f"{blind_mean:.3f}", "pack")

    # ------------------------------------------------------------------ Phase 1c (log)
    fun = log.ints(r"\| 通过次数 \| `(\d+) / 24`[^|]*\| `(\d+) / 24`[^|]*\| `(\d+) / 24`[^|]*"
                   r"\| `(\d+) / 24`[^|]*\| `(\d+) / 24`", "funnel")
    for k, v in zip(("gds", "drc", "lvs", "pex", "postsim"), fun):
        put(f"fun.{k}", v, "log")
    tsoft, gate, prom, gate2 = log.ints(
        r"`t_soft_stop = true` `(\d+) / 24`；`gate_triggered = true` `(\d+) / 24`；"
        r"`ratchet_promoted = true` `(\d+) / (\d+)`", "watermark counts")
    if gate != gate2:
        die("gate_triggered denominators differ in the log")
    put("pc.tsoft", tsoft, "log")
    put("pc.gate", gate, "log")
    put("pc.promoted", prom, "log")
    put("pc.promotedPct", f"{100 * prom / gate:.1f}", "log")
    disc, disc_runs = log.ints(r"`client_disconnects` 合计 `(\d+)`，分布在 `(\d+)` 次运行中", "disconnects")
    put("pc.disconnects", disc, "log")
    put("pc.disconnectRuns", disc_runs, "log")
    (req,) = log.ints(r"`proxy_requests` 合计 `(\d+)`；`input_tokens", "requests")
    tin, tout, tcache = log.ints(r"`input_tokens = ([\d,]+)`，`output_tokens = ([\d,]+)`，"
                                 r"`cached_tokens = ([\d,]+)` \| 每次运行平均", "tokens")
    put("pc.requests", thousands(req), "log")
    put("pc.requestsPerRun", f"{req / n_all:.0f}", "log")
    put("pc.inputTokM", f"{tin / 1e6:.1f}", "log")
    put("pc.outputTokM", f"{tout / 1e6:.1f}", "log")
    put("pc.inputTokPerRunM", f"{tin / n_all / 1e6:.1f}", "log")
    put("pc.outputTokPerRunM", f"{tout / n_all / 1e6:.2f}", "log")
    dist = log.ints(r"`Y\*` 计数分布：`= 0` 共 `(\d+)` 次，`= 0\.1` 共 `(\d+)` 次，`= 0\.2` 共 `(\d+)` 次，"
                    r"`> 0\.2` 共 `(\d+)` 次", "Y distribution")
    for k, v in zip(("zero", "tenth", "fifth", "above"), dist):
        put(f"dist.{k}", v, "log")
    b = log.grab(r"\| 3 个内部冻结盲簇合计[^|]*\| — \| — \| — \| 均值 `([\d.]+)` \| 合计 `(\d+)` \| "
                 r"计数 `(\d+)/(\d+)/(\d+)/(\d+)/(\d+)` \| — \| — \| 合计 `(\d+)` \| — \| — \| "
                 r"计数 `(\d+) / (\d+) / (\d+)`", "blind aggregate row")
    b_mean, b_c = float(b[0]), int(b[1])
    b_fun = [int(x) for x in b[2:7]]
    b_req, b_tsoft, b_gate, b_prom = (int(x) for x in b[7:11])
    put("blind.cSum", b_c, "log")
    for k, v in zip(("gds", "drc", "lvs", "pex", "postsim"), b_fun):
        put(f"blind.{k}", v, "log")
    put("blind.promoted", b_prom, "log")

    # cross-checks: visible (pack) + blind aggregate (log) == all 24 (log / pack)
    checks = [
        (abs(b_mean - blind_mean) < 5e-6, "blind mean Y* (pack arithmetic vs log)"),
        (vis["gds"] + b_fun[0] == fun[0], "gds funnel"), (vis["drc"] + b_fun[1] == fun[1], "drc funnel"),
        (vis["lvs"] + b_fun[2] == fun[2], "lvs funnel"),
        (vis["requests"] + b_req == req, "proxy request total"),
        (vis["promoted"] + b_prom == prom, "promotions"), (vis["gate"] + b_gate == gate, "gate count"),
        (vis["tsoft"] + b_tsoft == tsoft, "t_soft count"),
        (sum(dist) == n_all, "Y* distribution total"),
        (fun[4] == n_all - sum(tx.values()), "C*=1 count vs taxonomy"),
        (sum(1 for r in runs if r["Y_star"] == 0.0) <= dist[0], "Y*=0 count"),
    ]
    for ok, what in checks:
        if not ok:
            die(f"cross-check failed: {what}")

    # ------------------------------------------------------------------ Phase 1b (pack + log)
    fz = pack["visible_phase1b_forensic"]
    two = next((f for f in fz if "buf_ppsf_bs" in (f.get("hand") or {}).get("artifact", "")), None)
    other = next((f for f in fz if f is not two), None)
    if two is None or other is None or len(fz) != 2:
        die("Phase 1b forensic entries not recognised")
    pb_log = log.grab(r"\| phase_b seconds \| `([\d.]+)` \| `([\d.]+)` \|", "phase_b seconds")
    if f"{other['trace']['phase_b']['seconds']:.3f}" != pb_log[0] or \
            f"{two['trace']['phase_b']['seconds']:.3f}" != pb_log[1]:
        die("Phase 1b forensic order does not match the log table (#21, #2)")
    for tag, f in (("pbTwo", two), ("pbTwentyone", other)):
        sec, budget = f["trace"]["phase_b"]["seconds"], f["fork"]["granted_repair_budget_sec"]
        put(f"{tag}.sec", f"{sec:.1f}", "pack")
        put(f"{tag}.budget", f"{budget:.1f}", "pack")
        put(f"{tag}.pct", f"{100 * sec / budget:.1f}", "pack")
        put(f"{tag}.frac", f"{sec / 900.0:.4f}", "pack")
        put(f"{tag}.budgetFrac", f"{budget / 900.0:.4f}", "pack")
        put(f"{tag}.rc", f["trace"]["phase_b"]["returncode"], "pack")
        put(f"{tag}.turns", f["fork"]["granted_repair_turns"], "pack")
    w1b = two["fork"]["watermarks"]
    put("pOneB.tWarn", f"{w1b['t_warn_sec']:.0f}", "pack")
    put("pOneB.tWarnMin", f"{w1b['t_warn_sec'] / 60:.0f}", "pack")
    put("pOneB.repTurns", w1b["delta_s_rep_turns"], "pack")
    put("pOneB.phaseASec", f"{two['fork']['phase_a']['seconds']:.0f}", "pack")
    log.grab(r"但 `unrecovered_gateway_error = true`（`unrecovered_gateway_errors = 1`）三题全中", "1b flags")
    put("pOneB.nRuns", 3, "log")
    put("pOneB.flagged", 3, "log")
    log.grab(r"Phase 1b 为 `0 / 3` 晋升", "1b promotions")
    put("pOneB.promoted", 0, "log")
    (gds_files,) = log.ints(r"\| #gds files \| `\d+` \| `(\d+)` \|", "#2 gds files")
    put("two.gdsFiles", gds_files, "log")

    # ------------------------------------------------------------------ task #2 and #21 (pack)
    t2, t21 = by_id[next(i for i in by_id if by_id[i]["number"] == 2)], \
        by_id[next(i for i in by_id if by_id[i]["number"] == 21)]
    put("two.devices", t2["devices"], "pack")
    put("two.nets", t2["nets"], "pack")
    put("two.ports", len(t2["ports"]), "pack")
    put("two.qmax", f"{t2['q_max']:.0f}", "pack")
    mir = two["hand"]["mirror"]
    (q,) = re.search(r"aspect q = ([\d.]+)", mir["m_shape"]).groups()
    put("two.q", q, "pack")
    (mk,) = re.search(r"PASS - (\d+) markers", mir["m_drc"]).groups()
    put("two.drcMarkers", mk, "pack")
    ports, ext, sch = re.search(r"(\d+) ports reported disconnected; (\d+) extracted vs (\d+) schematic",
                                mir["m_lvs"]).groups()
    if int(sch) != t2["devices"]:
        die("#2 schematic device count differs between handoff and catalog")
    put("two.lvsPorts", ports, "pack")
    put("two.lvsExtracted", ext, "pack")
    x0, y0, x1, y1 = (float(v) for v in re.search(
        r"bbox \(([-\d.]+),([-\d.]+)\)-\(([-\d.]+),([-\d.]+)\)", mir["m_gds"]).groups())
    put("two.bboxW", f"{x1 - x0:.0f}", "pack")
    put("two.bboxH", f"{y1 - y0:.0f}", "pack")
    blk = " ".join(two["hand"]["known_blockers"] + two["hand"]["next_steps"] + two["hand"]["what_is_done"])
    (islands,) = re.search(r"hence (\d+) nets", blk).groups()
    put("two.islandNets", islands, "pack")
    (route_nets,) = re.search(r"route (\d+) nets", blk).groups()
    put("two.routeNets", route_nets, "pack")
    (ncap,) = re.search(r"(\d+) MIM caps", blk).groups()
    (nres,) = re.search(r"(\d+) serpentine poly resistors", blk).groups()
    put("two.caps", ncap, "pack")
    put("two.res", nres, "pack")
    p1c2 = [r for r in runs if r["task_id"] == t2["task_id"]]
    put("two.pcY", "/".join(f"{r['Y_star']:.1f}" for r in sorted(p1c2, key=lambda r: r["seed"])), "pack")
    put("ota.devices", t21["devices"], "pack")
    put("ota.nets", t21["nets"], "pack")
    put("ota.qmax", f"{t21['q_max']:.0f}", "pack")
    put("task.timeoutMin", f"{t21['agent_timeout_sec'] / 60:.0f}", "pack")

    # ------------------------------------------------------------------ Phase 2 (pack + log)
    p2 = pack["phase2_bank_summary"]
    cov = p2["screen_hbase"]["coverage"]
    put("bank.n", cov["n_total"], "pack")
    put("bank.terminal", cov["by_source_kind"]["terminal"], "pack")
    put("bank.neg", cov["by_source_kind"]["synthetic_neg"], "pack")
    put("bank.pos", cov["by_source_kind"]["synthetic_pos"], "pack")
    put("bank.sPlus", cov["n_S_plus"], "pack")
    syn = p2["synthesize_bank_counts"]
    put("bank.variants", syn["n_added"], "pack")
    put("bank.verified", syn["n_verified"], "pack")
    put("bank.sources", syn["n_sources"], "pack")
    if syn["bank_size"] != cov["n_total"] or syn["n_added"] != cov["by_source_kind"]["synthetic_neg"] + \
            cov["by_source_kind"]["synthetic_pos"]:
        die("Phase 2 bank counts are inconsistent")
    c1 = p2["screen_hbase"]["class1"]
    n_ok = 0
    for name in MIRRORS:
        ck, short = c1[name], name[2:]
        put(f"scr.{short}.nPlus", ck["checks"]["n_S_plus_k"], "pack")
        put(f"scr.{short}.viol", ck["checks"]["directional_violations"], "pack")
        put(f"scr.{short}.ok", int(bool(ck["ok"])), "pack")
        n_ok += bool(ck["ok"])
    put("scr.nOk", n_ok, "pack")
    put("scr.nMirrors", len(MIRRORS), "pack")
    put("scr.classOneOk", int(bool(p2["screen_hbase"]["class1_ok"])), "pack")
    c2 = p2["screen_hbase"]["class2"]["advisory_aspect_gt_3"]["checks"]
    put("scr.kFP", c2["k_FP_S_plus"], "pack")
    put("scr.kTPblind", c2["k_TP_blind"], "pack")
    put("scr.epsFill", f"{p2['calibrate_eps']['eps']:.1f}", "pack")
    var = {}
    for name in ("drc_sliver", "fill_low_ring", "lvs_missing_label", "shape_q_over_4",
                 "shape_q_advisory", "grid_shift", "rotate90"):
        a, n = log.ints(rf"`{name}`（`(\d+)/(\d+) agree`）", f"variant {name}")
        if a != n:
            die(f"variant {name}: agree != total in the log")
        var[name] = n
    for name in ("gds_truncated", "gds_renamed_top"):
        (n,) = log.ints(rf"`{name}`（`(\d+)`）", f"variant {name}")
        var[name] = n
    if sum(var.values()) != syn["n_added"]:
        die("variant counts in the log do not sum to the synthetic sample count")
    for name, n in var.items():
        put(VARKEYS[name], n, "log")

    # ------------------------------------------------------------------ misc (log / docs / code)
    (y1b,) = log.grab(r"\| verifier score \| `[\d.]+` \| `([\d.]+)` \|", "#2 Phase 1b score")
    put("two.pbY", f"{float(y1b):.2f}", "log")
    log.grab(r"`verifier_repeatability\.measured = false`", "verifier repeatability flag")
    log.grab(r"`n_runs_measured = 0`", "checkpoint gap flag")
    wt = Path(args.walkthrough).read_text(encoding="utf-8")
    m = re.search(r"全库 40 题里，(\d+) 题用 \*\*KLayout\*\*", wt)
    if not m:
        die("walkthrough: KLayout LVS task count not found")
    put("lvs.klayout", int(m.group(1)), "walkthrough")
    put("lvs.magic", sp["total_tasks"] - int(m.group(1)), "walkthrough")
    if t2["lvs_backend"] != "magic_netgen":
        die("#2 is expected to use the magic_netgen LVS backend")
    al = Path(args.auto_loop).read_text(encoding="utf-8")
    r_rep = int(re.search(r"^R_REP = (\d+)$", al, re.M).group(1))
    b1 = int(re.search(r"^B1_SIZE = (\d+)$", al, re.M).group(1))
    par = int(re.search(r":-(\d+)\}", str(cfg["run"]["parallel"])).group(1))
    put("loop.rRep", r_rep, "code")
    put("loop.bOne", b1, "code")
    put("loop.bTwo", sp["dev"] - b1, "code")
    put("loop.parallel", par, "config")
    batches = math.ceil(b1 / par) + math.ceil((sp["dev"] - b1) / par)
    put("est.batches", batches, "estimate")
    put("est.hoursLow", batches * wm["t_max_sec"] // 3600, "estimate")
    put("est.hoursHigh", batches * (wm["t_max_sec"] + wm["verifier_timeout_sec"]) // 3600, "estimate")
    put("est.pathTwoInputM", f"{sp['dev'] * tin / n_all / 1e6:.0f}", "estimate")
    put("est.pathOneMinPerTrial", r_rep * wm["delta_t_rep_sec"] // 60, "estimate")

    # task #21: agent-visible netlist and spec lines, copied from the benchmark checkout
    tdir = Path(args.alw_repo) / "tasks" / t21["task_id"]
    net_p, ins_p = tdir / "environment" / "task" / "circuit.spice", tdir / "instruction.md"
    if not net_p.is_file() or not ins_p.is_file():
        die(f"task #21 files not found under {tdir}; pass --alw-repo")
    net = [l.rstrip() for l in net_p.read_text().splitlines() if l.strip() and not l.startswith("*")]
    if sum(l.startswith("X") for l in net) != t21["devices"]:
        die("#21 netlist device count differs from the catalog")
    ins = ins_p.read_text()
    spec = re.search(r">= (\d+) dB at 1 kHz, have UGB >= (\d+) MHz, and have phase margin >= (\d+) deg", ins)
    noise = re.search(r"noise <= (\d+) uVrms", ins)
    power = re.search(r"reference branch <= ([\d.]+) mW", ins)
    pvt = re.search(r"all (\d+) combinations", ins)
    if not (spec and noise and power and pvt):
        die("#21 instruction.md: spec lines not recognised")
    put("ota.gainDb", spec.group(1), "task")
    put("ota.ugbMHz", spec.group(2), "task")
    put("ota.pmDeg", spec.group(3), "task")
    put("ota.noiseUv", noise.group(1), "task")
    put("ota.powerMw", power.group(1), "task")
    put("ota.pvt", pvt.group(1), "task")

    # ------------------------------------------------------------------ write facts.tex
    lines = ["% AUTO-GENERATED by tools/gen_facts.py -- do not edit by hand.",
             "% Sources: pack = verified_visible_facts.json; config = configs/alw/config.server.json;",
             "%          log = docs/alw-deployment-log.md (regex-parsed, cross-checked).",
             "% Blind clusters appear only as aggregate counts.", ""]
    seen = set()
    for key, value, src in F:
        if key in seen:
            die(f"duplicate fact key {key}")
        seen.add(key)
        lines.append(f"\\setfact{{{key}}}{{{value}}}% {src}")

    # visible 8 x 2 grid (slide: baseline) and the 16-row table (backup)
    lines += ["", "% ---- visible Phase 1c grid: \\runcell{row}{seed}{Y*}{state}", "\\def\\FactVisibleGrid{%"]
    for i, t in enumerate(tasks):
        lines.append(f"  \\tasklabel{{{i}}}{{\\#{t['number']}}}{{{LABELS[t['number']]}}}%")
        for r in sorted((r for r in runs if r["task_id"] == t["task_id"]), key=lambda r: r["seed"]):
            d = r["d_star"]
            state = "nogds" if d["gds"] != 1 else "lvs" if d["lvs"] == 1 else "drc" if d["drc"] == 1 else "gds"
            lines.append(f"  \\runcell{{{i}}}{{{r['seed']}}}{{{r['Y_star']:.1f}}}{{{state}}}%")
    lines.append("}")
    lines += ["", "% ---- visible Phase 1c runs, one table row each", "\\def\\FactVisibleRunRows{%"]

    def tri(v):
        return "1" if v == 1 else "0" if v == 0 else r"$\bot$"

    def yn(v):
        return r"\yes" if v else r"\no"
    for t in tasks:
        for r in sorted((r for r in runs if r["task_id"] == t["task_id"]), key=lambda r: r["seed"]):
            d = r["d_star"]
            mvec = "".join(str(x) for x in r["m"]) if r["m"] is not None else "无 GDS"
            lines.append(
                f"  \\#{t['number']} {LABELS[t['number']]} & {r['seed']} & {r['Y_star']:.1f} & "
                f"{tri(d['gds'])}/{tri(d['drc'])}/{tri(d['lvs'])} & \\texttt{{{mvec}}} & "
                f"{r['proxy_requests']} & {r['cost']['input_tokens'] / 1e6:.1f} & {r['wall_sec']:.0f} & "
                f"{100 * r['gateway_wait_seconds'] / r['wall_sec']:.1f}\\% & "
                f"{yn(r['t_soft_stop'])} & {yn(r['gate_triggered'])} & {yn(r['ratchet_promoted'])} \\\\%")
    lines.append("}")
    lines += ["", "% ---- task #21 netlist (comment lines dropped, model prefix sky130_fd_pr__ shortened)",
              "\\def\\FactOtaNetlist{%"]
    for l in net:
        l = re.sub(r"\s+", " ", l.replace("sky130_fd_pr__", ""))
        lines.append("  \\nl{" + tex(l).replace(" ", "\\ ") + "}%")
    lines.append("}")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")

    allow = [{"number": t["number"], "task_id": t["task_id"], "top": t["top"], "label": LABELS[t["number"]]}
             for t in tasks]
    Path(args.tasks_out).write_text(json.dumps(
        {"_comment": "AUTO-GENERATED by tools/gen_facts.py: the 8 visible dev tasks (allowlist for "
                     "fill_slots.py). Blind-cluster, val and test tasks are deliberately absent.",
         "visible_dev_tasks": allow}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"gen_facts: {len(F)} facts -> {args.out}; {len(allow)} visible tasks -> {args.tasks_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
