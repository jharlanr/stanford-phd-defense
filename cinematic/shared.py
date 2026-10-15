"""
Shared paths and constants for the cinematic scenes.

RULE: pipelines never reference the original lab data
directories (Drive / Oak / external drives). All private inputs are
COPIED into cinematic/source_data/ (gitignored) by fetch_sources.sh, and
every script reads only from there.
"""

from pathlib import Path

CINEMATIC_DIR = Path(__file__).resolve().parent

# Local, gitignored mirror of every private source dataset. Populate
# with:  bash cinematic/fetch_sources.sh
SOURCE_DATA = CINEMATIC_DIR / "source_data"

# BedMachine Greenland v6 — same DEM used in the JOG paper.
BEDMACHINE_PATH = SOURCE_DATA / "data" / "BedMachineGreenland-v6.nc"


def require_source(path: Path) -> Path:
    """Fail with a fetch hint instead of a bare FileNotFoundError."""
    if not path.exists():
        raise SystemExit(
            f"Missing source copy: {path}\n"
            "Run:  bash cinematic/fetch_sources.sh   (one-time copy from the lab Drive)"
        )
    return path


# Greenland centroid in lat/lon (rough — for camera framing).
GREENLAND_LAT = 72.0
GREENLAND_LON = -40.0

# Output paths
OUTPUT_DIR = CINEMATIC_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
