"""Pixel-level helpers: Gaussian-PSF transit injection and difference images.

Approximations (logged in OPEN_QUESTIONS.md and the data card):
- The PSF is a circular Gaussian, not the real TESS PSF.
- The transit is a box with no ingress or egress.
- Star flux from Tmag uses a fixed zero point (see TESS_E_PER_S_AT_T10).
"""
import numpy as np

# Approximate TESS count rate of a Tmag = 10 star, in e-/s. The smoke test compares it with the
# measured target flux, so treat it as a rough scale only.
TESS_E_PER_S_AT_T10 = 15000.0

# Out-of-transit window used for difference images, as multiples of the transit duration.
# A cadence is out of transit when OUT_INNER * duration < |dt| <= OUT_OUTER * duration.
OUT_INNER = 0.75
OUT_OUTER = 2.5


def star_flux_e_per_s(tmag):
    return TESS_E_PER_S_AT_T10 * 10.0 ** (-0.4 * (np.asarray(tmag, dtype=float) - 10.0))


def gaussian_psf_image(shape, x0, y0, sigma):
    """Circular Gaussian evaluated at pixel centres, normalised to unit sum over the whole plane.

    x is the column index and y the row index, both zero-based. Flux that falls outside the
    array is lost, so the image sums to less than 1 for a star near the edge.
    """
    yy, xx = np.indices(shape, dtype=float)
    return np.exp(-((xx - x0) ** 2 + (yy - y0) ** 2) / (2.0 * sigma**2)) / (2.0 * np.pi * sigma**2)


def phase_offset(time, period, epoch):
    """Signed time from the nearest transit midpoint, in the units of `time`, within +-period/2."""
    return (np.asarray(time, dtype=float) - epoch + 0.5 * period) % period - 0.5 * period


def in_transit_mask(time, period, epoch, duration):
    return np.abs(phase_offset(time, period, epoch)) <= 0.5 * duration


def inject_transit(flux, time, x0, y0, tmag, sigma, period, epoch, duration, depth):
    """Return a copy of flux [T, H, W] with a box transit of fractional `depth` on one star."""
    flux = np.asarray(flux, dtype=float)
    dip = depth * star_flux_e_per_s(tmag) * gaussian_psf_image(flux.shape[1:], x0, y0, sigma)
    out = flux.copy()
    out[in_transit_mask(time, period, epoch, duration)] -= dip
    return out


def difference_images(flux, time, period, epoch, duration):
    """Difference, reference, and noise images from a flux cube [T, H, W].

    difference = mean(out of transit) - mean(in transit), so a dip is positive.
    reference = mean(out of transit).
    noise = standard error of the difference, from the sample variances of both groups.
    Out-of-transit cadences come from windows around each transit (see OUT_INNER, OUT_OUTER),
    so slow trends over the sector do not dominate. NaNs are ignored.
    Returns (diff, ref, noise, n_in, n_out) where n_in and n_out count cadences.
    """
    flux = np.asarray(flux, dtype=float)
    if OUT_OUTER * duration >= 0.5 * period:
        raise ValueError("out-of-transit window overlaps the next transit; shorten duration or lengthen period")
    dt = np.abs(phase_offset(time, period, epoch))
    inside = dt <= 0.5 * duration
    outside = (dt > OUT_INNER * duration) & (dt <= OUT_OUTER * duration)
    fin = np.isfinite(flux).all(axis=(1, 2))
    inside, outside = inside & fin, outside & fin
    n_in, n_out = int(inside.sum()), int(outside.sum())
    if n_in < 2 or n_out < 2:
        raise ValueError(f"too few usable cadences (in={n_in}, out={n_out})")
    f_in, f_out = flux[inside], flux[outside]
    ref = f_out.mean(axis=0)
    diff = ref - f_in.mean(axis=0)
    noise = np.sqrt(f_out.var(axis=0, ddof=1) / n_out + f_in.var(axis=0, ddof=1) / n_in)
    return diff, ref, noise, n_in, n_out
