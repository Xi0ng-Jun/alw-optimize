#!/usr/bin/env python3
"""Compile the deck, copy the PDF next to the sources and render every page to PNG.

    ~/.local/bin/uv run --no-project --with pymupdf python tools/render.py
    python3 tools/render.py --no-png          # compile + copy only (no PyMuPDF needed)

Steps: (1) compile ``main.tex`` into ``build/`` with the first engine found: ``tectonic`` on
PATH, the micromamba-cached tectonic under ``~/.local/share/mamba/pkgs`` (started with its conda
libraries on ``LD_LIBRARY_PATH``), ``latexmk -xelatex``, or ``xelatex`` twice; (2) copy
``build/main.pdf`` to ``alw-progress-slides.pdf``; (3) render ``build/png/page-NN.png``.
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

DECK = Path(__file__).resolve().parent.parent
PDF_NAME = "alw-progress-slides.pdf"


def engine() -> tuple[list[str], dict[str, str], str]:
    env = dict(os.environ)
    exe = shutil.which("tectonic")
    if exe:
        return [exe, "--keep-logs", "--outdir", "build"], env, "tectonic"
    pkgs = Path.home() / ".local/share/mamba/pkgs/https/conda.anaconda.org/conda-forge/linux-64"
    cached = sorted(glob.glob(str(pkgs / "tectonic-*" / "bin" / "tectonic")))
    if cached:
        libs = ":".join(sorted(glob.glob(str(pkgs / "*" / "lib"))))
        env["LD_LIBRARY_PATH"] = libs + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
        return [cached[-1], "--keep-logs", "--outdir", "build"], env, "tectonic (micromamba cache)"
    if shutil.which("latexmk"):
        return ["latexmk", "-xelatex", "-interaction=nonstopmode", "-halt-on-error",
                "-outdir=build"], env, "latexmk"
    if shutil.which("xelatex"):
        return ["xelatex", "-interaction=nonstopmode", "-halt-on-error",
                "-output-directory=build"], env, "xelatex"
    sys.exit("render: no TeX engine found (tectonic, latexmk or xelatex). On Overleaf: upload this "
             "folder and set the compiler to XeLaTeX.")


def compile_deck(tex: str) -> Path:
    cmd, env, name = engine()
    (DECK / "build").mkdir(exist_ok=True)
    runs = 2 if name == "xelatex" else 1
    for _ in range(runs):
        p = subprocess.run(cmd + [tex], cwd=DECK, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True)
        if p.returncode != 0:
            sys.stdout.write(p.stdout[-6000:])
            sys.exit(f"render: {name} failed (see build/{Path(tex).stem}.log)")
    pdf = DECK / "build" / (Path(tex).stem + ".pdf")
    if not pdf.is_file():
        sys.exit("render: the engine reported success but wrote no PDF")
    log = DECK / "build" / (Path(tex).stem + ".log")
    if log.is_file():
        text = log.read_text(errors="replace")
        over = [l for l in text.splitlines() if l.startswith("Overfull \\hbox") or l.startswith("Overfull \\vbox")]
        miss = text.count("Missing character")
        print(f"render: compiled with {name}; overfull boxes: {len(over)}; missing glyphs: {miss}")
        for l in over[:12]:
            print("   ", l)
    return pdf


def render_png(pdf: Path, out: Path, dpi: int) -> int:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        sys.exit("render: PyMuPDF is missing; run with\n"
                 "  ~/.local/bin/uv run --no-project --with pymupdf python tools/render.py\n"
                 "or pass --no-png")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    doc = fitz.open(pdf)
    for i, page in enumerate(doc, 1):
        page.get_pixmap(dpi=dpi).save(out / f"page-{i:02d}.png")
    return len(doc)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--tex", default="main.tex", help="TeX file in the deck folder (default main.tex)")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--no-png", action="store_true")
    ap.add_argument("--no-copy", action="store_true", help=f"do not update {PDF_NAME}")
    args = ap.parse_args()
    pdf = compile_deck(args.tex)
    if not args.no_copy and Path(args.tex).name == "main.tex":
        shutil.copyfile(pdf, DECK / PDF_NAME)
        print(f"render: {PDF_NAME} updated")
    if not args.no_png:
        out = DECK / "build" / ("png" if Path(args.tex).name == "main.tex" else f"png-{Path(args.tex).stem}")
        n = render_png(pdf, out, args.dpi)
        print(f"render: {n} pages -> {out.relative_to(DECK)}/page-NN.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
