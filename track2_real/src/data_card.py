"""Write track2_real/DATA_CARD.md from data/processed/meta.json and outputs/targets_phase2.csv.

Run from the repo root after build_dataset.py:  python track2_real/src/data_card.py
Every number comes from those two files.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]


def main():
    meta = json.loads((ROOT / "data/processed/meta.json").read_text())
    tg = pd.read_csv(ROOT / "track2_real/outputs/targets_phase2.csv")
    ok = tg[tg["n_samples"] > 0]
    p = meta["params"]
    c = meta["counts"]
    lost = ok["flux_lost"]
    lines = f"""# Data card: Track 2 real-pixel dataset (schema_version {meta['schema_version']})

Built on {meta['created']} by `track2_real/src/build_dataset.py`. Files live in `data/processed` (git-ignored).

## What it is

Synthetic transits injected into real TESS SPOC 2-minute target pixel files. The true source is the star the dip was injected into. Real noise and real neighboring stars stay. Candidate stars come from the TIC (Gaia-derived). This is an injection benchmark, not a set of real transit hosts.

## Size

- Targets attempted: {meta['n_targets_attempted']}. With samples: {meta['n_targets_with_samples']}. No samples: {meta['n_targets_no_samples']}. Errors: {meta['n_targets_error']}.
- Samples: {meta['n_samples']} (up to {p['SAMPLES_PER_TARGET']} injections per target, all from the same TPF per target).
- TPF shapes (rows x columns): {', '.join(f'{k}: {v}' for k, v in meta['tpf_shapes'].items())}.
- One sector per target. Split by target, with targets closer than {p['CLUSTER_ARCMIN']} arcmin kept in the same split (split seed {p['SPLIT_SEED']}).

| split | targets | samples | samples per crowding bin (0 = most crowded) |
|---|---|---|---|
""" + "\n".join(f"| {s} | {v['targets']} | {v['samples']} | {v['samples_per_bin']} |" for s, v in c.items()) + f"""

Crowding tercile cut points, from the calibration set only: {[round(e, 4) for e in meta['crowd_edges_cal']]}.

## Fields (npz)

`X [S,3,11,11]` (difference, reference, noise; e-/s), `star_xy [S,20,2]` (cutout pixel coordinates, zero-based, x = column), `star_tmag [S,20]`, `star_mask [S,20]` (True = real star), `y [S]` (index of the true source), `crowd [S]`, `snr [S]`, `depth_ppm [S]`, `tic_id [S]` (the TIC target, used for splitting), `injected [S]` (all 1 here).
Extra fields: `sector`, `star_tic [S,20]` (TIC IDs of the candidates), `period_d`, `duration_h`. Padded star slots are zero.

## How it was made

- **Candidate stars:** TIC rows within {p['MAX_PIX']} pixels of the target (21 arcsec per pixel), real stars only, `DUPLICATE` rows dropped. Stars fainter than Tmag {p['TMAG_CUT']} are dropped, the brightest {p['N_STARS'] - 1} of the rest are kept, and the target is always kept. Sky positions go to pixels with the TPF WCS. Proper motion is ignored.
- **Crowding:** target flux over the sum of kept candidate fluxes, flux = 10^(-0.4 Tmag). It uses the TIC target and not the injected star, so it does not depend on the label and can define Mondrian bins at test time. One value per target.
- **Flux lost to truncation** (fraction of all candidate flux within {p['MAX_PIX']} px that the kept set omits): median {lost.median():.3f}, 90th percentile {lost.quantile(0.9):.3f}, max {lost.max():.3f}.
- **Injection:** box transit, Gaussian PSF sigma = {p['SIGMA_PIX']} px, period log-uniform {p['PERIOD_D']} d, duration {p['DURATION_H']} h, at least {p['MIN_EVENTS']} usable transits. The true source is drawn uniformly from the kept stars. A target SNR is drawn log-uniformly in {p['SNR_TARGET']}, depth is set to reach it and clipped to [{p['DEPTH_MIN']}, {p['DEPTH_MAX']}], and the draw is rejected if SNR is below {p['SNR_ACCEPT_MIN']}.
- **Difference image:** mean out-of-transit residual minus mean in-transit residual, after a local polynomial baseline of order {p['DETREND_ORDER']} fitted to out-of-transit cadences around each transit (both sides required). Reference image is the mean out-of-transit flux. Noise map is the standard error of the difference. The 11x11 cutout is centred on the TIC target by whole-pixel shifts and padded with zero.
- **SNR:** white-noise matched-filter SNR divided by kappa. Kappa is the robust spread of z = difference / noise measured on {p['NULL_DRAWS']} null difference images (no injection) near the target, floored at 1. Median kappa over targets: {ok['kappa'].median():.2f}, 90th percentile {ok['kappa'].quantile(0.9):.2f}, max {ok['kappa'].max():.2f}.

## Approximations and limits

""" + "\n".join(f"- {a}" for a in meta["approximations"]) + f"""
- The noise map assumes white noise, but null tests show the real noise is correlated in time. Kappa corrects the SNR only as a single number per target. See `outputs/phase2_detrend_check.csv`.
- Selection effect: stars too faint to reach SNR {p['SNR_ACCEPT_MIN']} at depth {p['DEPTH_MAX']} are never chosen as the true source. Targets where no star can be injected have no samples ({meta['n_targets_no_samples']} here). Bright targets with strong jitter (large kappa) are the likeliest to be lost, so the most crowded bin may be easier than the real sky.
- Samples from one target share a TPF, noise and candidate list, so they are not independent. Splits are by target, so calibration and test never share a target, but the exchangeability guarantee is then at the level of targets drawn from this pool, not of the whole sky.
- The target pool was chosen to balance crowding terciles across fields. It is not a random sample of TESS targets.
- Not validated against real transits. Timing, depth, shape, and PSF are all simulated.
"""
    (ROOT / "track2_real" / "DATA_CARD.md").write_text(lines)
    print("wrote track2_real/DATA_CARD.md")


if __name__ == "__main__":
    main()
