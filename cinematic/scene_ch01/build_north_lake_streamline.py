"""
Pick the streamline that comes closest to North Lake out of the shared
greenland_streamlines.json on R2, save it as its own small JSON for Ch.1.

Used by the JOG chapter Beat 4 ("highlight the streamline through North Lake")
and Beat 5 ("peel-back slider reveal of the cross-section along that
streamline, from ice-divide to coast").

Input:  shared/greenland_streamlines.json (already on R2; pulled by the
        existing motivation step-1 streamline rendering). Array of
        objects with `lonlat: [[lon, lat], ...]` polylines.

Output: cinematic/scene_ch01/data/north_lake_streamline.json
        {
          "lake":  { "lon": ..., "lat": ... },
          "stream_idx":     <index in the source array>,
          "min_dist_km":    <min distance from any vertex to the lake>,
          "lonlat":         [[lon, lat], ...]   # full polyline of the chosen streamline
        }

Run:
    python3 cinematic/scene_ch01/build_north_lake_streamline.py
"""

import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

NL_LON, NL_LAT = -49.49574, 68.72493

# Read from the live dev server so we don't depend on rclone or a separate
# download step. If the dev server isn't running, fall back to fetching R2
# direct (still no auth needed — it's the public pub-* URL).
URLS = [
    "http://localhost:5174/r2/shared/greenland_streamlines.json",
    "https://pub-70e18a35468a402b9bedda6fb300f342.r2.dev/shared/greenland_streamlines.json",
]

HERE = Path(__file__).resolve().parent
OUT_PATH = HERE / "data" / "north_lake_streamline.json"


def fetch_streamlines():
    # urllib's default User-Agent is "Python-urllib/X.Y", which the R2 dev
    # URL rejects with 403. Send a normal UA instead.
    headers = {"User-Agent": "curl/7.0"}
    last_err = None
    for url in URLS:
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                return json.load(resp)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"could not fetch streamlines from any URL: {last_err}")


def haversine_km(lon1, lat1, lon2, lat2):
    """Great-circle distance between two (lon, lat) points in km."""
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def turn_angle_deg(a, b, c):
    """Interior turn angle at b for the path a→b→c, in degrees.
    0 = straight, 180 = reversed direction."""
    ab = (b[0] - a[0], b[1] - a[1])
    bc = (c[0] - b[0], c[1] - b[1])
    la = math.hypot(*ab) or 1e-12
    lc = math.hypot(*bc) or 1e-12
    cos_t = (ab[0] * bc[0] + ab[1] * bc[1]) / (la * lc)
    cos_t = max(-1.0, min(1.0, cos_t))
    return math.degrees(math.acos(cos_t))


def trim_to_first_kink(pts, kink_threshold_deg=15.0, min_segments=5):
    """Walk the polyline from the divide end (index 0) and stop at the
    first vertex where the turn angle exceeds `kink_threshold_deg`. We
    skip the first `min_segments` to avoid catching tiny early jitter
    near the divide. Returns the trimmed list of vertices including the
    kink vertex itself.

    The director's spec: the cut streamline runs only up to the first
    corner kink in the highlighted (yellow) streamline."""
    if len(pts) < 3:
        return pts[:]
    kink_idx = len(pts) - 1  # fallback: full polyline
    kink_angle = 0.0
    for i in range(min_segments + 1, len(pts) - 1):
        angle = turn_angle_deg(pts[i - 1], pts[i], pts[i + 1])
        if angle > kink_threshold_deg:
            kink_idx = i
            kink_angle = angle
            break
    print(f"  kink: idx={kink_idx} (of {len(pts) - 1})  angle={kink_angle:.1f}°")
    return pts[: kink_idx + 1]


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"  fetching streamlines…")
    data = fetch_streamlines()
    print(f"    {len(data)} streamlines")

    # Find the streamline with any vertex closest to the lake.
    best_i = -1
    best_d = float("inf")
    for i, sline in enumerate(data):
        pts = sline.get("lonlat") or []
        for (lon, lat) in pts:
            d = haversine_km(lon, lat, NL_LON, NL_LAT)
            if d < best_d:
                best_d = d
                best_i = i
    print(f"  best stream idx={best_i}  min_dist={best_d:.2f} km")

    if best_i < 0:
        raise SystemExit("no streamlines found")

    chosen = data[best_i]
    full_pts = chosen["lonlat"]
    # The shared streamlines run interior→coast. Per the director's note, we
    # only want the segment from the ice-divide end up to the first
    # sharp kink for the CUT path. The full polyline still gets rendered
    # as the Beat 4 highlight tube.
    trimmed = trim_to_first_kink(full_pts)
    print(f"  trimmed {len(full_pts)} → {len(trimmed)} vertices")

    out = {
        "lake":         {"lon": NL_LON, "lat": NL_LAT},
        "stream_idx":   best_i,
        "min_dist_km":  round(best_d, 3),
        "lonlat":       trimmed,
        "lonlat_full":  full_pts,
        "comment": (
            "The shared streamline whose polyline passes closest to North "
            "Lake (CW2019_1889 / CW2018_1366). `lonlat` is the cut path "
            "for Ch.1 (JOG) Beat 5: ice-divide → first kink only ("
            "beyond the kink the streamline veers in a way "
            "that's not the cross-section we want). `lonlat_full` keeps "
            "the entire original streamline for the Beat 4 highlight "
            "rendering."
        ),
    }
    OUT_PATH.write_text(json.dumps(out, separators=(',', ':')))
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"  wrote {OUT_PATH} ({size_kb:.1f} KB, {len(trimmed)} trimmed verts, {len(full_pts)} full)")


if __name__ == "__main__":
    main()
