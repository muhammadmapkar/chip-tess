"""Per-target sample generation: injection with an SNR target, difference images, recentring.

Pure numpy, no network. Approximations are listed in pixels.py and in the data card.
SNR here is the white-noise matched-filter SNR divided by kappa, where kappa is the spread of
z = difference / noise measured on null difference images of the same TPF (see detrend_check.py).
"""
import numpy as np

from config import (
    CUTOUT, DEPTH_MAX, DEPTH_MIN, DETREND_ORDER, DURATION_H, KAPPA_MIN_DRAWS, MAX_PIX, MAX_TRIES, MIN_EVENTS,
    N_STARS, NULL_DRAWS, PERIOD_D, SIGMA_PIX, SNR_ACCEPT_MIN, SNR_TARGET,
)
from pixels import (
    OUT_OUTER, difference_images, gaussian_psf_image, in_transit_mask, inject_transit, phase_offset, recenter,
    star_flux_e_per_s,
)


def prepare_cube(flux):
    """float64 cube with unusable pixels zeroed. A pixel is unusable if finite in under 90% of cadences.

    Returns (flux, fin, valid_pix): fin marks cadences with every pixel finite.
    """
    flux = np.asarray(flux, dtype=float)
    valid_pix = np.isfinite(flux).mean(axis=0) >= 0.9
    flux = np.where(valid_pix[None], flux, 0.0)
    return flux, np.isfinite(flux).all(axis=(1, 2)), valid_pix


def pixel_noise(flux, fin):
    """Per-pixel white-noise sigma (e-/s per cadence) from the scatter of consecutive differences.

    Robust to slow trends and to transits. Pixels with zero scatter get inf so they carry no weight.
    """
    d = np.diff(flux[fin], axis=0)
    sig = 1.4826 * np.median(np.abs(d - np.median(d, axis=0)), axis=0) / np.sqrt(2.0)
    return np.where(sig > 0, sig, np.inf)


def draw_transit(time, rng):
    """Random period (log-uniform, days), duration (days), epoch (BTJD)."""
    period = float(np.exp(rng.uniform(*np.log(PERIOD_D))))
    duration = float(rng.uniform(*DURATION_H) / 24.0)
    epoch = float(time[0] + rng.uniform(0.0, period))
    return period, duration, epoch


def window_slice(flux, time, period, epoch, duration):
    """Cadences within the out-of-transit window of any transit. Keeps the cube small for injection."""
    keep = np.abs(phase_offset(time, period, epoch)) <= OUT_OUTER * duration
    return flux[keep], time[keep]


def snr_per_unit_depth(x, y, tmag, noise_pix, n_in, kappa, sigma=SIGMA_PIX):
    """Matched-filter SNR for depth 1 on a star at (x, y): sqrt(n_in) * |a / (sigma_pix * kappa)|."""
    a = star_flux_e_per_s(tmag) * gaussian_psf_image(noise_pix.shape, x, y, sigma)
    return float(np.sqrt(n_in) * np.sqrt(np.sum((a / (noise_pix * kappa)) ** 2)))


def null_kappa(flux, time, target_xy, rng, n_draws=NULL_DRAWS, order=DETREND_ORDER):
    """Robust spread of z = difference / noise with no injection, within MAX_PIX of the target.

    Returns nan if fewer than KAPPA_MIN_DRAWS draws were usable. The result is floored at 1.
    """
    yy, xx = np.indices(flux.shape[1:])
    near = np.hypot(xx - target_xy[0], yy - target_xy[1]) <= MAX_PIX
    zs = []
    for _ in range(3 * n_draws):
        period, duration, epoch = draw_transit(time, rng)
        fw, tw = window_slice(flux, time, period, epoch, duration)
        try:
            diff, _, noise, _, _ = difference_images(fw, tw, period, epoch, duration, order=order, min_events=MIN_EVENTS)
        except ValueError:
            continue
        zs.append((diff / noise)[near])
        if len(zs) == n_draws:
            break
    if len(zs) < KAPPA_MIN_DRAWS:
        return float("nan")
    z = np.concatenate(zs)
    return float(max(1.4826 * np.median(np.abs(z - np.median(z))), 1.0))


def generate_samples(flux, time, fin, noise_pix, kappa, star_xy, star_tmag, rng, k):
    """Up to k injected samples. Returns (samples, n_failed).

    The true source is drawn uniformly from the kept stars. A target SNR is drawn log-uniformly,
    the depth that reaches it is clipped to [DEPTH_MIN, DEPTH_MAX], and the draw is rejected if the
    resulting SNR is below SNR_ACCEPT_MIN. Stars that are too faint for any allowed depth are
    therefore never chosen, which is a selection effect reported in the data card.
    Each sample dict has diff, ref, noise (TPF coordinates, e-/s) and the injection parameters.
    """
    samples, n_failed = [], 0
    for _ in range(k):
        for _try in range(MAX_TRIES):
            period, duration, epoch = draw_transit(time, rng)
            n_est = int((in_transit_mask(time, period, epoch, duration) & fin).sum())
            if n_est < 30:
                continue
            j = int(rng.integers(len(star_tmag)))
            x, y, tmag = float(star_xy[j][0]), float(star_xy[j][1]), float(star_tmag[j])
            unit = snr_per_unit_depth(x, y, tmag, noise_pix, n_est, kappa)
            target = float(np.exp(rng.uniform(*np.log(SNR_TARGET))))
            depth = float(np.clip(target / unit, DEPTH_MIN, DEPTH_MAX))
            if unit * depth < SNR_ACCEPT_MIN:
                continue
            fw, tw = window_slice(flux, time, period, epoch, duration)
            injected = inject_transit(fw, tw, x, y, tmag, SIGMA_PIX, period, epoch, duration, depth)
            try:
                diff, ref, noise, n_in, n_out = difference_images(
                    injected, tw, period, epoch, duration, order=DETREND_ORDER, min_events=MIN_EVENTS)
            except ValueError:
                continue
            snr = unit * np.sqrt(n_in / n_est) * depth
            if snr < SNR_ACCEPT_MIN:
                continue
            samples.append(dict(j=j, diff=diff, ref=ref, noise=noise, period=period, duration=duration, epoch=epoch,
                                depth=depth, snr=float(snr), n_in=n_in))
            break
        else:
            n_failed += 1
    return samples, n_failed


def pack_target(samples, kept, target_xy, tic_id, sector, crowd):
    """Arrays for one target, in the SPEC layout, with the target recentred in an 11x11 cutout.

    kept is a DataFrame with ID, Tmag, x, y (TPF coordinates), sorted as the model will see it.
    Padded star slots are zero and star_mask is False there. snr is the kappa-corrected SNR.
    Extra fields beyond the SPEC: sector, star_tic, period_d, duration_h.
    """
    s = len(samples)
    stack = np.stack([np.stack([m["diff"], m["ref"], m["noise"]]) for m in samples])
    cut, (sx, sy) = recenter(stack, target_xy, size=CUTOUT, fill=0.0)
    n = len(kept)
    star_xy = np.zeros((N_STARS, 2), dtype=np.float32)
    star_tmag = np.zeros(N_STARS, dtype=np.float32)
    star_tic = np.zeros(N_STARS, dtype=np.int64)
    star_xy[:n, 0], star_xy[:n, 1] = kept["x"].to_numpy() + sx, kept["y"].to_numpy() + sy
    star_tmag[:n] = kept["Tmag"].to_numpy()
    star_tic[:n] = kept["ID"].astype(np.int64).to_numpy()
    mask = np.zeros(N_STARS, dtype=bool)
    mask[:n] = True
    rep = lambda a: np.repeat(a[None], s, axis=0)
    return dict(
        X=cut.astype(np.float32), star_xy=rep(star_xy), star_tmag=rep(star_tmag), star_mask=rep(mask),
        y=np.array([m["j"] for m in samples], dtype=np.int64), crowd=np.full(s, crowd, dtype=np.float32),
        snr=np.array([m["snr"] for m in samples], dtype=np.float32),
        depth_ppm=np.array([m["depth"] * 1e6 for m in samples], dtype=np.float32),
        tic_id=np.full(s, tic_id, dtype=np.int64), injected=np.ones(s, dtype=np.int8),
        sector=np.full(s, sector, dtype=np.int16), star_tic=rep(star_tic),
        period_d=np.array([m["period"] for m in samples], dtype=np.float32),
        duration_h=np.array([m["duration"] * 24.0 for m in samples], dtype=np.float32),
    )
