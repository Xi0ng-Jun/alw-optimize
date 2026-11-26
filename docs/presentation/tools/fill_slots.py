#!/usr/bin/env python3
"""Fill ``tonight_slots.tex`` from the server's Phase 3 round outputs (Python 3 stdlib only).

    python3 tools/fill_slots.py --round 1 --report round_report_redacted.json \
        [--stage0 stage0_report.json] [--patch candidate.patch] [--proposal proposal.json]
    python3 tools/fill_slots.py --bank-report phase2_bank_report.json     # m_gds re-screen

Inputs (all optional; give what exists when you leave the server):

  --report     STATE/loop/round_<g>/round_report_redacted.json      (round finished)
  --stage0     STATE/loop/round_<g>/attempt_<a>/screen/stage0_report.json
  --patch      STATE/loop/round_<g>/attempt_<a>/screen/candidate.patch
  --proposal   STATE/loop/round_<g>/attempt_<a>/proposer_ws/proposal.json   (rationale only)
  --state      force a state: running | stage1 | nocand | rejected | evaluated | promoted | infra

The script rewrites only the block of the given round between ``%% BEGIN r<g>`` and
``%% END r<g>`` (and the ``bank`` block for --bank-report); hand edits elsewhere are kept.

Guardrails (the script writes nothing and exits 2 when one trips):

* every task id found anywhere in the inputs must be one of the 8 visible dev tasks in
  ``tools/visible_tasks.json`` -- blind-cluster, val and test tasks can never reach a slide;
* blind clusters are copied only from the ``blind_aggregate`` counts of the redacted report;
* no user names in paths, no IP addresses, no URLs, no key-like strings.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECK = HERE.parent
STATES = ("running", "stage1", "nocand", "rejected", "evaluated", "promoted", "infra")
TASK_RE = re.compile(r"sky130-[a-z0-9]+(?:-[a-z0-9]+)*?-layout")
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,47}")
WORD_RE = re.compile(r"[A-Za-z0-9_():.+-]{1,64}")
LEAKS = (
    (re.compile(r"/(?:home|localdata|Users|scratch)/(?!<USER>)[^/\s\"'<>]+"), "user name in a path"),
    (re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"), "IP address"),
    (re.compile(r"[a-z][a-z0-9+.-]*://", re.I), "URL"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{12,}|\bBearer\s+[A-Za-z0-9._-]{12,}|"
                r"(?i:api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"\s]{8,}"), "key-like string"),
)


class Refuse(Exception):
    pass


def load_allow() -> dict[str, dict]:
    p = HERE / "visible_tasks.json"
    if not p.is_file():
        raise Refuse(f"{p} is missing; run tools/gen_facts.py first")
    tasks = json.loads(p.read_text(encoding="utf-8"))["visible_dev_tasks"]
    if len(tasks) != 8:
        raise Refuse("visible_tasks.json must list exactly the 8 visible dev tasks")
    return {t["task_id"]: t for t in tasks}


def scan(name: str, text: str, allow: dict[str, dict]) -> None:
    """Refuse any non-allowlisted task id or leak pattern in *text*."""
    for i, line in enumerate(text.splitlines(), 1):
        for tid in TASK_RE.findall(line):
            if tid not in allow:
                raise Refuse(f"{name}:{i}: task id outside the 8 visible dev tasks (not shown here "
                             "on purpose); this input must not go on a slide")
        for rx, what in LEAKS:
            if rx.search(line):
                raise Refuse(f"{name}:{i}: {what} found; scrub the input first")


def tex(s: object) -> str:
    out = []
    for ch in str(s):
        out.append({"\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "$": r"\$", "&": r"\&",
                    "#": r"\#", "%": r"\%", "_": r"\_", "^": r"\textasciicircum{}",
                    "~": r"\textasciitilde{}", "<": r"\textless{}", ">": r"\textgreater{}",
                    "|": r"\textbar{}", '"': r"\textquotedbl{}", "\t": "    "}.get(ch, ch))
    return "".join(out).replace("--", "-{}-")


def code(s: str) -> str:
    """Escape one source line for the monospace diff card (spaces kept)."""
    return tex(s).replace(" ", r"\ ")


def ident(v: object, what: str, rx: re.Pattern = ID_RE) -> str:
    v = "" if v is None else str(v)
    if v and not rx.fullmatch(v):
        raise Refuse(f"{what} has an unexpected format")
    return v


def num(v: object, what: str) -> float | None:
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise Refuse(f"{what} is not a number")
    return float(v)


def signed(v: float | None, nd: int = 3) -> str:
    return "" if v is None else f"{v:+.{nd}f}"


def task_label(tid: str, allow: dict[str, dict]) -> str:
    if tid not in allow:                       # second line of defence behind scan()
        raise Refuse("a task outside the 8 visible dev tasks reached the row builder")
    t = allow[tid]
    return f"\\#{t['number']} {t['label']}"


def read_json(path: str | None, name: str, allow: dict[str, dict]) -> dict | None:
    if not path:
        return None
    text = Path(path).read_text(encoding="utf-8")
    scan(name, text, allow)
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise Refuse(f"{name}: expected a JSON object")
    return obj


# --------------------------------------------------------------------------------------------
# patch -> slots/r<g>_patch.tex
# --------------------------------------------------------------------------------------------

def render_patch(text: str, max_lines: int, width: int) -> tuple[str, dict]:
    files, added, removed, body = [], 0, 0, []
    for line in text.splitlines():
        if line.startswith("+++ "):
            rel = line[4:].strip()
            rel = rel[2:] if rel.startswith(("a/", "b/")) else rel
            if rel != "/dev/null":
                files.append(rel)
            body.append(("dfile", rel if rel != "/dev/null" else "(文件删除)"))
        elif line.startswith("--- ") or line.startswith(("diff ", "index ")):
            continue
        elif line.startswith("Binary files "):
            body.append(("dhunk", "二进制文件改动"))
        elif line.startswith("@@"):
            body.append(("dhunk", line))
        elif line.startswith("+"):
            added += 1
            body.append(("dadd", line))
        elif line.startswith("-"):
            removed += 1
            body.append(("ddel", line))
        else:
            body.append(("dctx", line))
    # When truncated, skip a leading module-docstring hunk if real code hunks follow.
    hunks = [i for i, (k, _) in enumerate(body) if k == "dhunk"]
    if len(body) > max_lines and len(hunks) >= 2:
        first_chunk = body[hunks[0]:hunks[1]]
        if not any("def " in ln or "class " in ln for _, ln in first_chunk):
            body = [x for x in body[:hunks[0]] if x[0] == "dfile"] + body[hunks[1]:]
    shown = body[:max_lines]
    out = ["% AUTO-GENERATED by tools/fill_slots.py from the candidate patch -- do not edit."]
    for kind, line in shown:
        if len(line) > width:
            line = line[: width - 1] + "…"
        out.append(f"\\{kind}{{{code(line)}}}")
    if len(body) > len(shown):
        out.append(f"\\dmore{{另有 {len(body) - len(shown)} 行未显示}}")
    stats = {"files": len(dict.fromkeys(files)), "added": added, "removed": removed, "lines": len(body)}
    return "\n".join(out) + "\n", stats


# --------------------------------------------------------------------------------------------
# round block
# --------------------------------------------------------------------------------------------

def round_slots(rid: str, args, allow: dict[str, dict]) -> tuple[list[str], str | None]:
    rep = read_json(args.report, "report", allow)
    st0 = read_json(args.stage0, "stage0", allow)
    prop = read_json(args.proposal, "proposal", allow)
    S: dict[str, str] = {}
    rows: list[str] = []

    cand = (rep or {}).get("candidate") or {}
    src = cand or (st0 if st0 and st0.get("ok") else {}) or {}
    if st0 and not st0.get("ok") and not cand:
        src = st0                                   # rejected attempt: still show what it was
    S["candId"] = ident(src.get("candidate_id"), "candidate_id")
    mc = src.get("mutation_class")
    if mc is not None and mc not in (1, 2, 3, 4):
        raise Refuse("mutation_class must be 1..4")
    S["class"] = "" if mc is None else str(mc)
    S["checker"] = ident(src.get("checker"), "checker", WORD_RE)
    path = ident(src.get("evaluation_path"), "evaluation_path", WORD_RE)
    if path not in ("", "path1", "path2"):
        raise Refuse("evaluation_path must be path1 or path2")
    S["path"] = path[-1:] if path else ""
    if prop:
        if S["candId"] and ident(prop.get("candidate_id"), "proposal candidate_id") != S["candId"]:
            raise Refuse("proposal.json belongs to a different candidate")
        text = " ".join(str(prop.get("rationale") or "").split())
        S["rationale"] = tex(text[: args.rationale_chars - 1] + "…" if len(text) > args.rationale_chars
                             else text)
    if st0:
        ck = st0.get("checks") or {}
        for key, k in (("nFiles", "n_changed_files"), ("nPhaseA", "n_phase_a_files_changed")):
            v = num(ck.get(k), k)
            S[key] = "" if v is None else str(int(v))
        if "offline_smoke_ok" in ck:
            S["smoke"] = "1" if ck["offline_smoke_ok"] else "0"
        S["stageZero"] = "1" if st0.get("ok") else "0"
        if not st0.get("ok"):
            S["reason"] = tex(ident(st0.get("reason"), "stage0 reason", WORD_RE))

    state = "running"
    if rep is not None:
        if int(rep.get("round", -1)) != args.round:
            raise Refuse(f"report is for round {rep.get('round')}, not round {args.round}")
        atts = rep.get("attempts") or []
        S["attempts"] = str(len(atts))
        ev = rep.get("evaluation")
        if not cand:
            hard = [a for a in atts if a.get("stage") not in (None, "proposal", "diff")]
            state = "rejected" if hard else "nocand"
            last = (hard or atts or [{}])[-1]
            S["reason"] = tex(ident(last.get("reason"), "attempt reason", WORD_RE))
        elif ev is None or ev.get("dry_run"):
            state = "stage1"
        else:
            reason = ident(ev.get("reason"), "evaluation reason", WORD_RE)
            S["reason"] = tex(reason)
            state = ("promoted" if ev.get("promoted") else
                     "infra" if reason in ("unresolved_infra_error", "b1_infra_or_crash") else "evaluated")
            ev_path = ident(ev.get("reclassified_from") or ev.get("path"), "evaluation path", WORD_RE)
            blind = ev.get("blind_aggregate") or {}
            if ev.get("path") == "path1":
                S["deltaKind"] = "sum"
                S["delta"] = signed(num(ev.get("sum_delta_Y"), "sum_delta_Y"))
                S["nTrials"] = str(int(num(ev.get("n_trials"), "n_trials") or 0))
                S["nDivergent"] = str(int(num(ev.get("n_divergent"), "n_divergent") or 0))
                S["blindDelta"] = signed(num(blind.get("sum_delta_Y"), "blind sum_delta_Y"))
                S["blindN"] = str(int(num(blind.get("n_divergent"), "blind n_divergent") or 0))
                vt = [t for t in ev.get("visible_trials") or [] if t.get("divergent")]
                vt.sort(key=lambda t: -abs(t.get("delta_Y") or 0.0))
                for t in vt[: args.max_rows]:
                    rows.append(f"\\slotrow{{{rid}}}{{{task_label(str(t.get('task_id')), allow)}}}"
                                f"{{{int(t.get('seed', 0))}}}{{{signed(num(t.get('delta_Y'), 'delta_Y'))}}}"
                                f"{{{tex(ident(t.get('verdict'), 'verdict', WORD_RE))}}}")
                S["rowsOmitted"] = str(max(0, len(vt) - args.max_rows))
            else:                                   # path2, or path2 reclassified to path3 pooling
                S["deltaKind"] = "mean"
                S["delta"] = signed(num(ev.get("net_delta"), "net_delta"))
                n1, n2 = num(ev.get("n_B1"), "n_B1"), num(ev.get("n_B2"), "n_B2")
                seeds = num(ev.get("seeds"), "seeds") or 1
                S["nTrials"] = "" if n1 is None or n2 is None else str(int((n1 + n2) * seeds))
                S["blindDelta"] = signed(num(blind.get("mean_delta"), "blind mean_delta"))
                S["blindN"] = "" if blind.get("n_tasks") is None else str(int(blind["n_tasks"]))
                ptd = ev.get("visible_per_task_delta") or {}
                for tid, dv in sorted(ptd.items(), key=lambda kv: allow[kv[0]]["number"]
                                      if kv[0] in allow else -1)[: args.max_rows]:
                    d = num(dv, "per-task delta")
                    verdict = "升" if d > 1e-6 else "降" if d < -1e-6 else "持平"
                    rows.append(f"\\slotrow{{{rid}}}{{{task_label(str(tid), allow)}}}{{全部}}"
                                f"{{{signed(d)}}}{{{verdict}}}")
                S["rowsOmitted"] = str(max(0, len(ptd) - args.max_rows))
            if ev_path and S["path"] and ev_path[-1:] != S["path"]:
                S["path"] = ev_path[-1:]
            S["llmCalls"] = "" if ev.get("llm_calls") is None else str(int(ev["llm_calls"]))
            S["unresolved"] = str(int(num(ev.get("n_unresolved"), "n_unresolved") or 0))
        S["hIncAfter"] = tex(ident(rep.get("h_inc_after"), "h_inc_after", re.compile(r"[A-Za-z0-9_.+-]{1,96}")))
    elif st0 is not None:
        state = "stage1" if st0.get("ok") else "rejected"
    if args.state:
        state = args.state

    patch_tex = None
    if args.patch:
        text = Path(args.patch).read_text(encoding="utf-8", errors="replace")
        scan("patch", text, allow)
        patch_tex, stats = render_patch(text, args.patch_lines, args.patch_width)
        S["patch"] = f"slots/{rid}_patch"
        S["patchFiles"], S["patchAdded"], S["patchRemoved"] = (str(stats[k]) for k in
                                                               ("files", "added", "removed"))
        if not S.get("nFiles"):
            S["nFiles"] = str(stats["files"])

    order = ("candId", "class", "checker", "path", "attempts", "rationale", "stageZero", "nFiles",
             "nPhaseA", "smoke", "patch", "patchFiles", "patchAdded", "patchRemoved", "deltaKind",
             "delta", "nTrials", "nDivergent", "llmCalls", "blindDelta", "blindN", "unresolved",
             "rowsOmitted", "reason", "hIncAfter")
    lines = [f"\\slot{{{rid}.state}}{{{state}}}"]
    lines += [f"\\slot{{{rid}.{k}}}{{{S.get(k, '')}}}" for k in order]
    return lines + rows, patch_tex


def bank_slots(path: str) -> list[str]:
    """Post-refresh Stage 0 screen of the six mirrors (integers only are read)."""
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    scr = obj.get("screen_hbase") or (obj.get("phase2_bank_summary") or {}).get("screen_hbase") or obj
    c1 = scr.get("class1")
    if not isinstance(c1, dict) or "m_gds" not in c1:
        raise Refuse("bank report: screen_hbase.class1.m_gds not found")
    viol = int(c1["m_gds"]["checks"]["directional_violations"])
    n_ok = sum(1 for v in c1.values() if isinstance(v, dict) and v.get("ok") is True)
    return [f"\\slot{{bank.mgdsViol}}{{{viol}}}", f"\\slot{{bank.nOk}}{{{n_ok}}}",
            f"\\slot{{bank.classOneOk}}{{{1 if scr.get('class1_ok') else 0}}}"]


def replace_block(text: str, tag: str, lines: list[str]) -> str:
    rx = re.compile(rf"(%% BEGIN {re.escape(tag)}\b[^\n]*\n)(.*?)(%% END {re.escape(tag)}\b)", re.S)
    if not rx.search(text):
        raise Refuse(f"marker '%% BEGIN {tag}' ... '%% END {tag}' not found in the slots file")
    return rx.sub(lambda m: m.group(1) + "\n".join(lines) + "\n" + m.group(3), text, count=1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--round", type=int, choices=(1, 2))
    ap.add_argument("--report")
    ap.add_argument("--stage0")
    ap.add_argument("--patch")
    ap.add_argument("--proposal")
    ap.add_argument("--state", choices=STATES)
    ap.add_argument("--bank-report")
    ap.add_argument("--asof", default=_dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
    ap.add_argument("--slots", default=str(DECK / "tonight_slots.tex"))
    ap.add_argument("--patch-lines", type=int, default=17)
    ap.add_argument("--patch-width", type=int, default=86)
    ap.add_argument("--rationale-chars", type=int, default=260)
    ap.add_argument("--max-rows", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true", help="print the new slots file, write nothing")
    args = ap.parse_args()
    if args.round is None and not args.bank_report:
        ap.error("give --round (with any of --report/--stage0/--patch/--proposal/--state) or --bank-report")
    slots_path = Path(args.slots)
    try:
        allow = load_allow()
        text = slots_path.read_text(encoding="utf-8")
        patch_tex = None
        if args.round is not None:
            rid = f"r{args.round}"
            lines, patch_tex = round_slots(rid, args, allow)
            text = replace_block(text, rid, lines)
        if args.bank_report:
            text = replace_block(text, "bank", bank_slots(args.bank_report))
        if not re.fullmatch(r"[0-9: -]{1,20}", args.asof):
            raise Refuse("--asof must look like 2026-11-25 08:40")
        text = re.sub(r"\\slot\{asof\}\{[^}]*\}", lambda m: f"\\slot{{asof}}{{{args.asof}}}", text, count=1)
    except Refuse as exc:
        print(f"fill_slots: REFUSED: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"fill_slots: cannot read the inputs ({type(exc).__name__}: {exc})", file=sys.stderr)
        return 2
    if args.dry_run:
        sys.stdout.write(text)
        return 0
    if patch_tex is not None:
        out = slots_path.parent / "slots" / f"r{args.round}_patch.tex"
        out.parent.mkdir(exist_ok=True)
        out.write_text(patch_tex, encoding="utf-8")
        print(f"fill_slots: wrote {out}")
    slots_path.write_text(text, encoding="utf-8")
    print(f"fill_slots: updated {slots_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
