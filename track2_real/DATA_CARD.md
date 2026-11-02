# Data card: Track 2 real-pixel dataset (schema_version 1)

Built on 2026-11-03 by `track2_real/src/build_dataset.py`. Files live in `data/processed` (git-ignored).

## What it is

Synthetic transits injected into real TESS SPOC 2-minute target pixel files. The true source is the star the dip was injected into. Real noise and real neighboring stars stay. Candidate stars come from the TIC (Gaia-derived). This is an injection benchmark, not a set of real transit hosts.

## Size

- Targets attempted: 330. With samples: 330. No samples: 0. Errors: 0.
- Samples: 6600 (up to 20 injections per target, all from the same TPF per target).
- TPF shapes (rows x columns): 11x11: 277, 13x11: 40, 23x11: 2, 65x11: 1, 15x15: 1, 33x11: 1, 21x11: 1, 27x11: 1, 39x11: 1, 15x11: 4, 35x11: 1.
- One sector per target. Split by target, with targets closer than 5.0 arcmin kept in the same split (split seed 0).

| split | targets | samples | samples per crowding bin (0 = most crowded) |
|---|---|---|---|
| train | 199 | 3980 | [1160, 1640, 1180] |
| val | 33 | 660 | [280, 140, 240] |
| cal | 49 | 980 | [320, 320, 340] |
| test | 49 | 980 | [280, 480, 220] |

Crowding tercile cut points, from the calibration set only: [0.4637, 0.9591].

## Fields (npz)

`X [S,3,11,11]` (difference, reference, noise; e-/s), `star_xy [S,20,2]` (cutout pixel coordinates, zero-based, x = column), `star_tmag [S,20]`, `star_mask [S,20]` (True = real star), `y [S]` (index of the true source), `crowd [S]`, `snr [S]`, `depth_ppm [S]`, `tic_id [S]` (the TIC target, used for splitting), `injected [S]` (all 1 here).
Extra fields: `sector`, `star_tic [S,20]` (TIC IDs of the candidates), `period_d`, `duration_h`. Padded star slots are zero.

## How it was made

- **Candidate stars:** TIC rows within 3.0 pixels of the target (21 arcsec per pixel), real stars only, `DUPLICATE` rows dropped. Stars fainter than Tmag 16.0 are dropped, the brightest 19 of the rest are kept, and the target is always kept. Sky positions go to pixels with the TPF WCS. Proper motion is ignored.
- **Crowding:** target flux over the sum of kept candidate fluxes, flux = 10^(-0.4 Tmag). It uses the TIC target and not the injected star, so it does not depend on the label and can define Mondrian bins at test time. One value per target.
- **Flux lost to truncation** (fraction of all candidate flux within 3.0 px that the kept set omits): median 0.036, 90th percentile 0.251, max 0.706.
- **Injection:** box transit, Gaussian PSF sigma = 1.0 px, period log-uniform [1.0, 10.0] d, duration [1.0, 4.0] h, at least 2 usable transits. The true source is drawn uniformly from the kept stars. A target SNR is drawn log-uniformly in [5.0, 30.0], depth is set to reach it and clipped to [0.0001, 0.1], and the draw is rejected if SNR is below 5.0.
- **Difference image:** mean out-of-transit residual minus mean in-transit residual, after a local polynomial baseline of order 1 fitted to out-of-transit cadences around each transit (both sides required). Reference image is the mean out-of-transit flux. Noise map is the standard error of the difference. The 11x11 cutout is centred on the TIC target by whole-pixel shifts and padded with zero.
- **SNR:** white-noise matched-filter SNR divided by kappa. Kappa is the robust spread of z = difference / noise measured on 16 null difference images (no injection) near the target, floored at 1. Median kappa over targets: 1.28, 90th percentile 2.30, max 5.34.

## Approximations and limits

- Gaussian PSF sigma=1.0 px for injection (not the real TESS PSF)
- box transit, no ingress or egress
- flux zero point 15000 e-/s at Tmag 10
- proper motion ignored when placing TIC stars on the TPF
- SNR is white-noise matched-filter SNR divided by kappa (null z spread)
- The noise map assumes white noise, but null tests show the real noise is correlated in time. Kappa corrects the SNR only as a single number per target. See `outputs/phase2_detrend_check.csv`.
- Selection effect: stars too faint to reach SNR 5.0 at depth 0.1 are never chosen as the true source. Targets where no star can be injected have no samples (0 here). Bright targets with strong jitter (large kappa) are the likeliest to be lost, so the most crowded bin may be easier than the real sky.
- Samples from one target share a TPF, noise and candidate list, so they are not independent. Splits are by target, so calibration and test never share a target, but the exchangeability guarantee is then at the level of targets drawn from this pool, not of the whole sky.
- The target pool was chosen to balance crowding terciles across fields. It is not a random sample of TESS targets.
- Not validated against real transits. Timing, depth, shape, and PSF are all simulated.
