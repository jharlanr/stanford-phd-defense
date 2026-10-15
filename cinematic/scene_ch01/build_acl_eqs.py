"""Typeset the ACL-stage equations with REAL LaTeX.

The director asked that the ACL and max tau_xx equations stop
floating over the plot; they move into the equation band ABOVE the
chart, side by side. They are re-typeset here with latex + dvisvgm
(Computer Modern, glyphs converted to paths so the browser needs no
fonts), warm-white ink, and the slider parameters h, alpha, ell, tau_val
inked GOLD in the source via xcolor — the earlier gold highlights,
now native to the typesetting instead of patched glyph ids.

Outputs (cinematic/data/eq2/):
  acl.svg      manuscript eqn:acl (eq 48), [x] spelled out
  taumax.svg   max tau_xx = rho g alpha ell / 4

Needs /Library/TeX/texbin (latex, dvisvgm). Run:
  python cinematic/scene_ch01/build_acl_eqs.py
Then (rclone copy, never sync):
  rclone copy cinematic/data/eq2 r2:<bucket>/ch01/eq2 --header-upload 'Cache-Control: public, max-age=31536000, immutable'
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

TEXBIN = "/Library/TeX/texbin"
OUT = Path(__file__).resolve().parents[1] / "data" / "eq2"
OUT.mkdir(parents=True, exist_ok=True)

INK = "F5F0E6"   # warm white — the site's equation ink
GOLD = "F5C75E"  # the site gold — the tunable parameters

G = r"\color{gold}"
EQS = {
    "acl": (
        r"\mathrm{ACL} \;=\; \frac{\bigl(2B{" + G + r"h}/C\bigr)^{\frac{n}{n+1}}}"
        r"{n^{-\frac{1}{n+1}}}\;"
        r"\ln\!\left(\frac{\rho g{" + G + r"\alpha}{" + G + r"\ell}/4}"
        r"{{" + G + r"\tau_{val}}}\right)"
    ),
    "taumax": (
        r"\max\,\tau_{xx} \;=\; \frac{\rho g{" + G + r"\alpha}{" + G + r"\ell}}{4}"
    ),
}

TEMPLATE = r"""\documentclass[preview,border=1.5pt]{standalone}
\usepackage{amsmath}
\usepackage{xcolor}
\definecolor{ink}{HTML}{%(ink)s}
\definecolor{gold}{HTML}{%(gold)s}
\begin{document}
\color{ink}$\displaystyle %(eq)s$
\end{document}
"""


def build(name: str, eq: str) -> None:
    env = dict(os.environ, PATH=f"{TEXBIN}:{os.environ.get('PATH', '')}")
    with tempfile.TemporaryDirectory() as td:
        tex = Path(td) / f"{name}.tex"
        tex.write_text(TEMPLATE % {"ink": INK, "gold": GOLD, "eq": eq})
        subprocess.run(["latex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
                       cwd=td, env=env, check=True, capture_output=True)
        svg = Path(td) / f"{name}.svg"
        subprocess.run(["dvisvgm", "--no-fonts", "--exact-bbox", "-o", svg.name, f"{name}.dvi"],
                       cwd=td, env=env, check=True, capture_output=True)
        out = OUT / f"{name}.svg"
        shutil.copy(svg, out)
    text = out.read_text()
    m = re.search(r"viewBox='[-\d.]+ [-\d.]+ ([\d.]+) ([\d.]+)'", text)
    w, h = float(m.group(1)), float(m.group(2))
    n_gold = text.count(f"fill='#{GOLD.lower()}'")
    print(f"wrote eq2/{name}.svg  viewBox {w:.2f} x {h:.2f}  aspect w/h = {w / h:.4f}  "
          f"gold groups = {n_gold}  ({out.stat().st_size / 1e3:.1f} kB)")


if __name__ == "__main__":
    for k, v in EQS.items():
        build(k, v)
