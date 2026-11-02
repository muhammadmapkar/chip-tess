"""Build the target pool across galactic latitudes, print the crowding histogram, pick the targets (D16).

Run from the repo root:  python track2_real/src/pool.py
Writes data/interim/pool.csv (every candidate target with a TIC-only crowding estimate) and
data/interim/selected_targets.csv (balanced across crowding terciles and fields).
The crowding estimate here uses angular distance from TIC only. Final crowding comes from the
build step, which uses the TPF WCS. The terciles here only balance the sample.
"""
import subprocess
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import astropy.units as u
import numpy as np
import pandas as pd
from astropy.coordinates import SkyCoord

warnings.filterwarnings("ignore", message=".*tpfmodel.*")
import lightkurve as lk  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from config import MAX_PIX, PIX_ARCSEC, SPLIT_SEED, WORKERS  # noqa: E402
from tic import cone_radius_arcsec, query_tic_cone, select_candidates, with_retries  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
FIELD_DIR = INTERIM / "fields"
PER_FIELD = 30
N_SELECT = 330
SEARCH_RADIUS_DEG = 1.0
FIELD_TIMEOUT_S = 1200   # one field (search plus its TIC queries) is killed after this
FIELD_WORKERS = 3

# (galactic l, galactic b) in degrees. Plane to pole, both hemispheres. Fields with no SPOC
# 2-minute TPFs simply return nothing and are reported.
FIELDS_LB = [
    (300, -1), (285, -3), (320, 2), (340, -3), (5, -5), (25, 3), (60, 2), (90, -3), (120, 3), (150, -2),
    (180, -3), (210, 2), (240, -4), (270, -6), (330, -12), (10, -15), (45, -20), (200, -30), (300, -30),
    (120, 45), (300, 55), (60, 50), (0, 89), (350, 6), (30, -8), (225, -12), (315, -20), (80, 12),
]


def search_field(l_deg, b_deg):
    centre = SkyCoord(l=l_deg * u.deg, b=b_deg * u.deg, frame="galactic").icrs
    res = with_retries(lambda: lk.search_targetpixelfile(
        centre, radius=SEARCH_RADIUS_DEG * u.deg, author="SPOC", exptime=120, mission="TESS"))
    if len(res) == 0:
        return pd.DataFrame()
    tab = res.table.to_pandas()[["target_name", "sequence_number", "s_ra", "s_dec", "distance"]]
    tab = tab.sort_values(["distance", "sequence_number"], ascending=[True, False])
    tab = tab.drop_duplicates("target_name").head(PER_FIELD)  # nearest the centre, latest sector
    return pd.DataFrame({"field": f"l{l_deg}_b{b_deg}", "tic_id": tab["target_name"].astype(str).str.replace("TIC ", ""),
                         "sector": tab["sequence_number"].astype(int), "ra": tab["s_ra"], "dec": tab["s_dec"]})


def crowd_estimate(row):
    """TIC-only crowding for one target. Returns a dict, or None if the target is not found."""
    try:
        cat = query_tic_cone(row["ra"], row["dec"], cone_radius_arcsec())
        centre = SkyCoord(row["ra"] * u.deg, row["dec"] * u.deg)
        me = cat[cat["ID"] == str(row["tic_id"])]
        if me.empty:
            return None
        pos = SkyCoord(cat["ra"].to_numpy() * u.deg, cat["dec"].to_numpy() * u.deg)
        t = pos[(cat["ID"] == str(row["tic_id"])).to_numpy()][0]
        cat["d"] = pos.separation(t).arcsec / PIX_ARCSEC
        _, info = select_candidates(cat, row["tic_id"])
        return dict(target_tmag=info["target_tmag"], n_candidates=info["n_candidates"], crowd_est=info["crowd"],
                    flux_lost_est=info["flux_lost"])
    except Exception as e:  # keep the pool going, count the failure
        return dict(error=str(e)[:80])


def balanced_selection(pool, n_select, seed=SPLIT_SEED):
    """Equal numbers from each crowding tercile of the pool, interleaved across fields."""
    rng = np.random.default_rng(seed)
    pool = pool.copy()
    pool["tercile"] = pd.qcut(pool["crowd_est"].rank(method="first"), 3, labels=False)
    picks = []
    for t in range(3):
        grp = pool[pool["tercile"] == t]
        queues = [g.sample(frac=1, random_state=int(rng.integers(1 << 31))).to_dict("records")
                  for _, g in grp.groupby("field")]
        want, got = n_select // 3, []
        while len(got) < want and any(queues):
            for q in queues:
                if q and len(got) < want:
                    got.append(q.pop())
        picks += got
    return pd.DataFrame(picks)


def text_hist(values, bins=12, width=40):
    counts, edges = np.histogram(values, bins=bins, range=(0, 1))
    for c, lo, hi in zip(counts, edges[:-1], edges[1:]):
        print(f"  {lo:4.2f}-{hi:4.2f} {'#' * int(round(width * c / max(counts.max(), 1))):<{width}} {c}")


def build_field(l_deg, b_deg):
    """Search one field and estimate crowding for its targets. Writes data/interim/fields/<name>.csv."""
    from astroquery.mast import conf as mast_conf
    mast_conf.timeout = 120
    FIELD_DIR.mkdir(parents=True, exist_ok=True)
    targets = search_field(l_deg, b_deg)
    if targets.empty:
        targets = pd.DataFrame(columns=["field", "tic_id", "sector", "ra", "dec"])
    est = [crowd_estimate(r) for r in targets.to_dict("records")]
    est = pd.DataFrame([r if r else {"error": "target not in TIC rows"} for r in est])
    out = pd.concat([targets.reset_index(drop=True), est], axis=1)
    out.to_csv(FIELD_DIR / f"l{l_deg}_b{b_deg}.csv", index=False)


def run_field(lb):
    """Run build_field in a subprocess with a hard timeout, two attempts. Returns (lb, status)."""
    l, b = lb
    path = FIELD_DIR / f"l{l}_b{b}.csv"
    if path.exists():
        return lb, "cached"
    for attempt in (1, 2):
        t0 = time.time()
        try:
            subprocess.run([sys.executable, "-u", str(Path(__file__)), "--field", str(l), str(b)],
                           timeout=FIELD_TIMEOUT_S, capture_output=True, check=True)
            return lb, f"ok in {time.time() - t0:.0f}s"
        except subprocess.TimeoutExpired:
            status = f"timeout after {FIELD_TIMEOUT_S}s (attempt {attempt})"
        except subprocess.CalledProcessError as e:
            status = f"error (attempt {attempt}): {e.stderr.decode()[-150:]!r}"
        print(f"field l={l} b={b}: {status}", flush=True)
    return lb, "gave up"


def main():
    INTERIM.mkdir(parents=True, exist_ok=True)
    FIELD_DIR.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(FIELD_WORKERS) as ex:
        for lb, status in ex.map(run_field, FIELDS_LB):
            path = FIELD_DIR / f"l{lb[0]}_b{lb[1]}.csv"
            n = len(pd.read_csv(path)) if path.exists() else 0
            print(f"field l={lb[0]} b={lb[1]}: {n} targets, {status}", flush=True)
    frames = [pd.read_csv(p) for p in sorted(FIELD_DIR.glob("*.csv"))]
    pool = pd.concat([f for f in frames if len(f)], ignore_index=True).drop_duplicates("tic_id")
    pool.to_csv(INTERIM / "pool.csv", index=False)
    if "crowd_est" not in pool:
        sys.exit("no crowding estimates at all")
    ok = pool[pool["crowd_est"].notna()].reset_index(drop=True)
    print(f"pool: {len(pool)} targets, {len(ok)} with a crowding estimate, {len(pool) - len(ok)} failed")
    print("pool crowding estimate histogram (target flux / kept flux, lower = more crowded):")
    text_hist(ok["crowd_est"])
    print(ok.groupby("field")["crowd_est"].agg(["count", "median", "min", "max"]).round(3).to_string())
    sel = balanced_selection(ok, N_SELECT)
    sel.to_csv(INTERIM / "selected_targets.csv", index=False)
    print(f"selected {len(sel)} targets, {sel['field'].nunique()} fields; per tercile:")
    print(sel.groupby("tercile")["crowd_est"].agg(["count", "min", "max"]).round(3).to_string())
    print("selected crowding histogram:")
    text_hist(sel["crowd_est"])


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--field":
        build_field(int(sys.argv[2]), int(sys.argv[3]))
    else:
        main()
