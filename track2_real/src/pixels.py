"""Pixel-level helpers: Gaussian-PSF transit injection, difference images, recentring.

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


def difference_images(flux, time, period, epoch, duration, order=1, min_events=1):
    """Difference, reference, and noise images from a flux cube [T, H, W].

    For each transit event, a polynomial of degree `order` is fitted per pixel to the out-of-transit
    cadences in the window around it. order=0 subtracts the local out-of-transit mean. The event
    needs out-of-transit cadences on both sides, so the baseline is never extrapolated.
    difference = mean(out-of-transit residual) - mean(in-transit residual), so a dip is positive.
    reference = mean raw flux out of transit, over the events used.
    noise = standard error of the difference, from the residual variances of both groups.
    NaNs are ignored. Returns (diff, ref, noise, n_in, n_out), the last two counting cadences.
    """
    flux = np.asarray(flux, dtype=float)
    time = np.asarray(time, dtype=float)
    if OUT_OUTER * duration >= 0.5 * period:
        raise ValueError("out-of-transit window overlaps the next transit; shorten duration or lengthen period")
    off = phase_offset(time, period, epoch)
    adt = np.abs(off)
    inside = adt <= 0.5 * duration
    outside = (adt > OUT_INNER * duration) & (adt <= OUT_OUTER * duration)
    fin = np.isfinite(flux).all(axis=(1, 2))
    inside, outside = inside & fin, outside & fin
    event = np.rint((time - epoch) / period).astype(int)
    n_pix = flux.shape[1] * flux.shape[2]

    res_in, res_out, raw_out = [], [], []
    for e in np.unique(event[inside]):
        m_in, m_out = inside & (event == e), outside & (event == e)
        left, right = m_out & (off < 0), m_out & (off > 0)
        if m_in.sum() < 1 or left.sum() < order + 2 or right.sum() < order + 2:
            continue
        mid = epoch + e * period
        design = lambda m: np.vander(time[m] - mid, order + 1, increasing=True)
        y_out = flux[m_out].reshape(-1, n_pix)
        coef, *_ = np.linalg.lstsq(design(m_out), y_out, rcond=None)
        res_out.append(y_out - design(m_out) @ coef)
        res_in.append(flux[m_in].reshape(-1, n_pix) - design(m_in) @ coef)
        raw_out.append(y_out)
    if len(res_in) < min_events:
        raise ValueError(f"too few usable transit events ({len(res_in)} < {min_events})")
    r_in, r_out, f_out = np.concatenate(res_in), np.concatenate(res_out), np.concatenate(raw_out)
    n_in, n_out = r_in.shape[0], r_out.shape[0]
    if n_in < 2 or n_out < 2:
        raise ValueError(f"too few usable cadences (in={n_in}, out={n_out})")
    shape = flux.shape[1:]
    diff = (r_out.mean(axis=0) - r_in.mean(axis=0)).reshape(shape)
    ref = f_out.mean(axis=0).reshape(shape)
    noise = np.sqrt(r_out.var(axis=0, ddof=1) / n_out + r_in.var(axis=0, ddof=1) / n_in).reshape(shape)
    return diff, ref, noise, n_in, n_out


def recenter(imgs, centre_xy, size=11, fill=0.0):
    """Integer-pixel shift so the pixel nearest `centre_xy` lands at the middle of a size x size cutout.

    imgs has shape [..., H, W]. Pixels with no source data are set to `fill`.
    Returns (cutout, (sx, sy)), where sx and sy are the integer shifts to add to x and y positions.
    """
    imgs = np.asarray(imgs)
    h, w = imgs.shape[-2:]
    half = size // 2
    cx, cy = int(np.rint(centre_xy[0])), int(np.rint(centre_xy[1]))
    out = np.full(imgs.shape[:-2] + (size, size), fill, dtype=imgs.dtype)
    x0, y0 = cx - half, cy - half  # source index of the cutout's (0, 0)
    xs, xe = max(x0, 0), min(x0 + size, w)
    ys, ye = max(y0, 0), min(y0 + size, h)
    if xs < xe and ys < ye:
        out[..., ys - y0:ye - y0, xs - x0:xe - x0] = imgs[..., ys:ye, xs:xe]
    return out, (-x0, -y0)
