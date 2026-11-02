import numpy as np
import pytest

from pixels import (
    difference_images,
    gaussian_psf_image,
    in_transit_mask,
    inject_transit,
    phase_offset,
    recenter,
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


def test_detrend_order_removes_quadratic_baseline():
    time, flux = make_cube(noise=0.5, seed=5)
    ev_mid = 0.2 + 1.2 * np.rint((time - 0.2) / 1.2)
    curve = 30.0 * (time - ev_mid) + 400.0 * (time - ev_mid) ** 2  # per-event slow trend, e-/s
    flux = flux + curve[:, None, None]
    out = inject_transit(flux, time, 7.0, 3.0, tmag=10.0, sigma=1.0, period=1.2, epoch=0.2, duration=0.1, depth=0.01)
    true_peak = 0.01 * 15000.0 * gaussian_psf_image((11, 11), 7.0, 3.0, 1.0)[3, 7]
    err = {}
    for order in (0, 1, 2):
        diff, *_ = difference_images(out, time, 1.2, 0.2, 0.1, order=order)
        err[order] = abs(diff[3, 7] - true_peak) / true_peak
    assert err[2] < 0.1
    assert err[2] < err[0]


def test_min_events_is_enforced():
    time, flux = make_cube()
    with pytest.raises(ValueError):
        difference_images(flux, time, 1.2, 0.2, 0.1, min_events=50)


def test_event_without_out_of_transit_on_both_sides_is_skipped():
    time, flux = make_cube(n_t=300)  # 0.42 d of data, one event whose midpoint is its first cadence
    with pytest.raises(ValueError):
        difference_images(flux, time, 5.0, 0.0, 0.1, order=1)
    # same data, but the event sits in the middle: usable
    difference_images(flux, time, 5.0, 0.2, 0.1, order=1)


def test_recenter_moves_target_pixel_to_middle_and_pads():
    img = np.arange(11 * 11, dtype=float).reshape(11, 11) + 1.0
    out, (sx, sy) = recenter(img, (4.4, 5.2), size=11)  # rounds to (4, 5)
    assert (sx, sy) == (1, 0)
    assert out[5, 5] == img[5, 4]
    assert (out[:, 0] == 0).all()  # padded column
    assert out[0, 1] == img[0, 0]
    out_same, (sx2, sy2) = recenter(img, (5.0, 5.0))
    assert (sx2, sy2) == (0, 0) and np.array_equal(out_same, img)


def test_recenter_handles_stacks_and_crops_larger_arrays():
    big = np.random.default_rng(0).random((3, 15, 15))
    out, (sx, sy) = recenter(big, (7.0, 7.0), size=11)
    assert out.shape == (3, 11, 11)
    assert np.array_equal(out, big[:, 2:13, 2:13])
    assert (sx, sy) == (-2, -2)
