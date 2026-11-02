import numpy as np
import pytest

from pixels import (
    difference_images,
    gaussian_psf_image,
    in_transit_mask,
    inject_transit,
    phase_offset,
    star_flux_e_per_s,
)


def make_cube(n_t=3000, shape=(11, 11), noise=1.0, seed=0):
    rng = np.random.default_rng(seed)
    time = np.arange(n_t) * (2.0 / 1440.0)  # 2-minute cadence, days
    flux = 100.0 + rng.normal(0.0, noise, size=(n_t, *shape))
    return time, flux


def test_psf_sums_to_one_on_large_grid():
    img = gaussian_psf_image((61, 61), 30.0, 30.0, 1.0)
    assert img.sum() == pytest.approx(1.0, abs=1e-6)


def test_star_flux_scale_is_10_to_the_minus_0p4_per_mag():
    assert star_flux_e_per_s(10.0) == pytest.approx(15000.0)
    assert star_flux_e_per_s(12.5) / star_flux_e_per_s(10.0) == pytest.approx(0.1)


def test_phase_offset_range_and_transit_mask():
    t = np.linspace(0, 10, 1001)
    off = phase_offset(t, period=2.0, epoch=0.5)
    assert off.min() >= -1.0 and off.max() <= 1.0
    m = in_transit_mask(t, period=2.0, epoch=0.5, duration=0.2)
    assert m.sum() > 0
    assert (np.abs(off[m]) <= 0.1 + 1e-12).all()


def test_injected_flux_removed_matches_depth_times_star_flux():
    time, flux = make_cube(shape=(41, 41))
    out = inject_transit(flux, time, 20.0, 20.0, tmag=10.0, sigma=1.0,
                         period=1.5, epoch=0.3, duration=0.125, depth=0.01)
    m = in_transit_mask(time, 1.5, 0.3, 0.125)
    removed = (flux[m] - out[m]).sum(axis=(1, 2))
    assert removed == pytest.approx(np.full(m.sum(), 0.01 * 15000.0), rel=1e-6)
    assert np.array_equal(flux[~m], out[~m])


def test_difference_image_peaks_at_injected_star():
    time, flux = make_cube(noise=1.0)
    out = inject_transit(flux, time, 7.0, 3.0, tmag=10.0, sigma=1.0,
                         period=1.2, epoch=0.2, duration=0.1, depth=0.01)
    diff, ref, noise, n_in, n_out = difference_images(out, time, 1.2, 0.2, 0.1)
    row, col = np.unravel_index(np.argmax(diff), diff.shape)
    assert (col, row) == (7, 3)
    assert n_in > 0 and n_out > n_in
    assert ref.mean() == pytest.approx(100.0, abs=0.5)
    assert (noise > 0).all()
    assert diff[3, 7] / noise[3, 7] > 10


def test_difference_image_is_unbiased_without_a_dip():
    time, flux = make_cube(noise=1.0, seed=3)
    diff, _, noise, _, _ = difference_images(flux, time, 1.2, 0.2, 0.1)
    assert abs(diff.mean()) < 3 * noise.mean() / np.sqrt(diff.size)


def test_difference_images_ignores_nan_cadences_and_rejects_overlap():
    time, flux = make_cube()
    flux[10] = np.nan
    difference_images(flux, time, 1.2, 0.2, 0.1)
    with pytest.raises(ValueError):
        difference_images(flux, time, 0.5, 0.2, 0.2)
    with pytest.raises(ValueError):
        difference_images(flux, time, 1000.0, 500.0, 0.1)  # transit falls outside the data
