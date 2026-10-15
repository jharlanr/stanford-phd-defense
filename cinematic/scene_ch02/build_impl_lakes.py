"""Ch.2 IMPLICATIONS, one figure per center lake (the director wanted
the implications figure to show ice flowing from right to left, and
found the seven-lake stack unreadable: which centre lake is it, and why
do the same symbols, like downward triangles, repeat?).

Beat 9 is now THE CHOSEN LAKE's figure: its elastic and viscous Δσ_t1
(the published SI recipe — tensor-first difference, tangent-projected,
first principal; build_results_assets.tangent_principals_diff, which
asserts equality with the block's drape) in the model's own flow-aligned
frame, ROTATED 180° so the ice flows RIGHT → LEFT (a rotation, not a
mirror: the map keeps its handedness, and it reads like the north-up
DIFFERENCE maps of beat 7, whose flow points west-south-west), tension
only, inferno 0 → 1 MPa. Per lake:

A later note: a colour scheme different from the red-and-blue already
used for stress was confusing, so the figure uses the same one:
the fields are now the BLOCK's colours — matplotlib seismic, ±1 MPa
(negative blue · 0 white · positive red; build_results_assets.
seismic_rgba's norm) — under NEW names (R2 objects are immutable):
impl2_{e,v}_<id>.png + impl_lakes_v2.json (same numbers, the new image
names). The inferno impl_* objects stay in R2 untouched.

A still later note: on the summary page, where elastic and viscous sit
side by side with the implication takeaway, the ice should flow from
left to right instead of right to left. So the 180° turn is
UNDONE — the fields are drawn in the model frame as it stands, x
downstream to the RIGHT and y (left of flow) UP, the Chapter 2 block's
own convention (its ICE FLOW arrow points along +x). Still a rotation of
the v2 picture, never a mirror: every map keeps its handedness, so the
v3 PNG is the v2 PNG turned 180°, pixel for pixel. NEW names again:
impl3_{e,v}_<id>.png + impl_lakes_v3.json, which also carries the
display mapping (`display`: screen-x = half + sx·x, screen-y = half +
sy·y, here sx = +1, sy = −1) so the page places the numbers, the
R = 2.5 km ring, the blister / patch word and the reach ruler from the
sidecar instead of a hard-coded turn. impl2_* + v2 stay in R2 untouched.


  impl3_{e,v}_<id>.png the field, IMPL_PX square = the ±half_km analysis
                       window (the rotated domain square IS this frame)
  impl_lakes_v3.json   per lake: the +100 kPa contour (km, model frame),
                       the upstream reach of the +100 kPa region, peak
                       (p99.9) and area above +100 kPa (asserted equal to
                       results.json), and every catalog lake's rings in
                       the model frame (km) with its class.

Model frame: x downstream, y to the left of flow (km, origin = the
drained lake). Display (the website, v3): screen-x = half + x, screen-y =
half − y — the same mapping as the PNGs (column 0 = −half upstream,
row 0 = +half, left of flow); the sidecar's `display` says so. (v2 was
the 180° turn: screen-x = half − x, screen-y = half + y.)

Run (defense checkout root, the cinematic venv):
  ./cinematic/.venv/bin/python -u cinematic/scene_ch02/build_impl_lakes.py
Outputs: cinematic/scene_ch02/output_results/impl/
Upload:
  rclone copy cinematic/scene_ch02/output_results/impl r2:<bucket>/ch02/results --header-upload 'Cache-Control: public, max-age=31536000, immutable'
"""

import json
import sys
from pathlib import Path

import numpy as np
from matplotlib import colormaps
from PIL import Image

sys.stdout.reconfigure(line_buffering=True)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import build_results_assets as bra  # noqa: E402
import build_sim_domains as bsd  # noqa: E402

ROOT = HERE.parents[1]
OUT = HERE / 'output_results' / 'impl'
SIM_DOMAINS = ROOT / 'website' / '.r2-cache' / 'ch02' / 'sim' / 'sim_domains.json'
RESULTS = ROOT / 'website' / '.r2-cache' / 'ch02' / 'results' / 'results.json'

IMPL_PX = 720
LEVEL = bra.LEVEL_KPA      # +100 kPa
VLIM = bsd.VLIM_KPA        # 1 MPa: the top of the tension scale
CMAP = 'seismic'           # the block's ±1 MPa map
PNG_PREFIX = 'impl3'        # new bytes = new names (v3: flow → right)
JSON_NAME = 'impl_lakes_v3.json'
# The display mapping (screen = half + s·model, km): flow LEFT → RIGHT,
# left-of-flow UP — the block's own frame. v2 was sx = −1, sy = +1.
DISPLAY = {'sx': 1, 'sy': -1}


def r3(v: float) -> float:
    return round(float(v), 3)


def build(meta: dict, published: dict) -> dict:
    new_id = meta['id']
    old_n = int(meta['old_id'][6:])
    num = old_n + 1523
    ds, dsv = bsd.open_lake_ncs(old_n)
    x = ds['x'].values
    y = ds['y'].values
    half = float(min(x.max(), y.max()))
    t1e, _ = bra.tangent_principals_diff(ds, 'blister')
    t1v, _ = bra.tangent_principals_diff(dsv, 'patch')
    ds.close()
    dsv.close()

    # The display grid from DISPLAY: column c sits at screen-x, row r at
    # screen-y; model x = sx·(screen − half), y = sy·(screen − half).
    # v3: column 0 = −half (upstream, LEFT), row 0 = +half (left of flow,
    # TOP) — the model frame as it stands, ice flowing left → right.
    sc = np.linspace(-half, half, IMPL_PX)
    gx = DISPLAY['sx'] * sc
    gy = DISPLAY['sy'] * sc
    GX, GY = np.meshgrid(gx, gy)
    X, Y = np.meshgrid(x, y)
    cell_km2 = (x[1] - x[0]) * (y[1] - y[0]) / 1e6

    models = {}
    for tag, model, f1 in (('e', 'elastic', t1e), ('v', 'viscous', t1v)):
        img = bra.bilinear(f1, x, y, GX, GY)
        rgba = (colormaps[CMAP](np.clip((img + VLIM) / (2 * VLIM), 0, 1)) * 255).astype(np.uint8)
        rgba[..., 3] = 255
        fname = f'{PNG_PREFIX}_{tag}_{new_id}.png'
        Image.fromarray(rgba).save(OUT / fname, optimize=True)

        lines = []
        for ln in bra.contour_lines(f1, LEVEL):
            xs = np.interp(ln[:, 0], np.arange(len(x)), x)
            ys = np.interp(ln[:, 1], np.arange(len(y)), y)
            pts = bra.decimate(np.stack([xs, ys], axis=1), bra.DECIMATE_M)
            if len(pts) >= 4:
                lines.append([[r3(px / 1e3), r3(py / 1e3)] for px, py in pts])

        above = f1 > LEVEL
        area = round(float(above.sum() * cell_km2), 2)
        peak = round(float(np.nanpercentile(f1, 99.9)), 1)
        pub = published['lakes'][new_id]['models'][model]
        assert abs(area - pub['area100_km2']) < 0.011, (new_id, model, area, pub['area100_km2'])
        assert abs(peak - pub['peak_kpa']) < 0.11, (new_id, model, peak, pub['peak_kpa'])
        # Upstream reach of the +100 kPa region (the composite's rule, per
        # lake): the farthest-upstream column holding any cell above it.
        xs_above = X[above]
        up = float(-xs_above.min() / 1e3) if above.any() and xs_above.min() < 0 else 0.0
        models[model] = {
            'image': fname,
            'contour100_km': lines,
            'peak_kpa': peak,
            'area100_km2': area,
            'upstream100_km': round(up, 2),
        }
        print(f'  {num} {model:8s} peak {peak:7.1f} kPa · area>100 {area:6.2f} km² · '
              f'upstream reach {up:5.2f} km · {len(lines)} contour pieces')

    # Catalog lakes in the model frame (km).
    e0, n0 = bsd.T4326_3413.transform(meta['lon'], meta['lat'])
    th = np.deg2rad(meta['flow_angle_deg'])
    c, s = np.cos(th), np.sin(th)
    rings_all = bsd.geojson_rings()
    cats = bsd.LAKE_CATEGORIES[old_n]
    listed = sorted({cw for cls in cats.values() for cw in cls})
    pub_lakes = {l['num']: l for l in published['lakes'][new_id]['lakes']}
    lakes = []
    for cw in listed:
        cls = bsd.lake_class(old_n, cw)
        rings = rings_all.get(cw)
        if cls is None or not rings:
            continue
        out_rings = []
        for ring in rings:
            ee, nn = bsd.T4326_3413.transform([p[0] for p in ring], [p[1] for p in ring])
            ee = np.asarray(ee) - e0
            nn = np.asarray(nn) - n0
            lx = ee * c + nn * s
            ly = -ee * s + nn * c
            out_rings.append([[r3(a / 1e3), r3(b / 1e3)] for a, b in zip(lx, ly)])
        pl = pub_lakes[cw + 1523]
        lakes.append({
            'num': cw + 1523,
            'cls': cls,
            'center': cw == old_n,
            'phase': pl['phase'],
            'rings_km': out_rings,
        })
    return {'num': num, 'half_km': r3(half / 1e3), 'models': models, 'lakes': lakes}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    doc = json.loads(SIM_DOMAINS.read_text())
    published = json.loads(RESULTS.read_text())
    lakes = {}
    for meta in doc['lakes']:
        lakes[meta['id']] = build(meta, published)
    (OUT / JSON_NAME).write_text(json.dumps({
        'level_kpa': LEVEL,
        'vlim_kpa': VLIM,
        'frame': 'model frame km (x downstream, y left of flow); '
                 'display: screen = half + (sx·x, sy·y) — flow left → right',
        'display': DISPLAY,
        'lakes': lakes,
    }, separators=(',', ':')))
    print(f'wrote {OUT / JSON_NAME}')


if __name__ == '__main__':
    main()
