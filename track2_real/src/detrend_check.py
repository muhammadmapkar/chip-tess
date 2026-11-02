"""Null test for D14: difference images with no injection, by local baseline order.

If the noise map is honest, z = difference / noise has a spread near 1. Larger spread means
correlated systematics that the baseline did not remove.
Run from the repo root on cached TPFs:  python track2_real/src/detrend_check.py
"""
import glob
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
import lightkurve as lk  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from config import DURATION_H, PERIOD_D  # noqa: E402
from pixels import difference_images  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
N_DRAWS = 80
ORDERS = (0, 1, 2)


def robust_sigma(z):
    return 1.4826 * np.median(np.abs(z - np.median(z)))


def main():
    rows = []
    for path in sorted(glob.glob(str(ROOT / "data/raw/**/*_tp.fits"), recursive=True)):
        tpf = lk.read(path)
        flux, time = tpf.flux.value.astype(float), tpf.time.value
        h, w = flux.shape[1:]
        med = np.nanmedian(flux, axis=0)
        py, px = np.unravel_index(np.nanargmax(med), med.shape)
        near = (np.hypot(*np.indices((h, w)) - np.array([py, px])[:, None, None]) <= 2.0)
        rng = np.random.default_rng(0)
        z = {o: [] for o in ORDERS}
        zn = {o: [] for o in ORDERS}
        for _ in range(N_DRAWS):
            period = float(np.exp(rng.uniform(*np.log(PERIOD_D))))
            dur = rng.uniform(*DURATION_H) / 24.0
            epoch = time[0] + rng.uniform(0, period)
            try:
                res = {o: difference_images(flux, time, period, epoch, dur, order=o, min_events=2) for o in ORDERS}
            except ValueError:
                continue
            for o, (diff, _, noise, _, _) in res.items():
                zz = diff / noise
                z[o].append(zz[~near].ravel())
                zn[o].append(zz[near].ravel())
        for o in ORDERS:
            far, close = np.concatenate(z[o]), np.concatenate(zn[o])
            rows.append(dict(tic_id=int(tpf.targetid), sector=tpf.sector, tmag_peak_e_s=float(med[py, px]), order=o,
                             n_draws=len(z[o]), z_sigma_far=robust_sigma(far), z_sigma_near=robust_sigma(close),
                             frac_abs_z_gt_3_near=float((np.abs(close) > 3).mean())))
    df = pd.DataFrame(rows)
    out = ROOT / "track2_real" / "outputs" / "phase2_detrend_check.csv"
    df.to_csv(out, index=False)
    pd.set_option("display.width", 200)
    print(df.round(3).to_string(index=False))
    print(df.groupby("order")[["z_sigma_far", "z_sigma_near", "frac_abs_z_gt_3_near"]].median().round(3))


if __name__ == "__main__":
    main()
