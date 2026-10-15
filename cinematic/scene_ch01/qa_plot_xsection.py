"""
Quick QA plot of the North Lake cross-section JSON. Not a publication
figure — just visual confirmation that surface/bed/ice-thickness arrays
look reasonable (no NaNs, monotone-ish surface, bed near sea level).

Output goes to cinematic/output/ (gitignored) — re-runnable from the JSON.
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE   = Path(__file__).resolve().parent
INPUT  = HERE / "data" / "north_lake_xsection.json"
OUTDIR = HERE.parent / "output"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUTPUT = OUTDIR / "ch01_north_lake_xsection_qa.png"

d   = json.loads(INPUT.read_text())
s   = np.array(d["profile"]["x_m"]) / 1000.0      # km along flow
sur = np.array(d["profile"]["surface_m"])
bed = np.array(d["profile"]["bed_m"])
thk = np.array(d["profile"]["thickness_m"])

fig, ax = plt.subplots(figsize=(11, 4))

# Bedrock fill
ax.fill_between(s, -200, bed, color="#9c7e5c", alpha=0.85, label="bedrock")
# Ice column
ax.fill_between(s, bed, sur, color="#cfe5f4", alpha=0.95, label="ice")
# Surface line
ax.plot(s, sur, color="#1f3a5f", lw=1.4)
# Bed line
ax.plot(s, bed, color="#5a4329", lw=1.0)
# Sea-level line
ax.axhline(0, color="#888", lw=0.6, ls="--", alpha=0.7)
# North Lake centre marker
ax.axvline(0, color="#c43a3a", lw=1.0, alpha=0.8)
ax.scatter([0], [d["lake"]["surface_m"]], s=60, color="#c43a3a", zorder=5,
           label=f"North Lake (lon={d['lake']['lon']}, lat={d['lake']['lat']})")

ax.set_xlabel("Along-flow distance from lake centre [km]  (downflow → +)")
ax.set_ylabel("Elevation [m, EGM2008-ish]")
ax.set_title(
    f"North Lake along-flow cross-section · "
    f"surface velocity {d['flow']['speed_m_yr']:.0f} m/yr · "
    f"thickness at lake {d['profile']['surface_m'][len(s)//2] - d['profile']['bed_m'][len(s)//2]:.0f} m"
)
ax.legend(loc="upper right", framealpha=0.9)
ax.set_xlim(s.min(), s.max())
ax.set_ylim(-200, max(sur) + 100)
ax.grid(alpha=0.25)

plt.tight_layout()
plt.savefig(OUTPUT, dpi=140)
print(f"  wrote {OUTPUT}")
