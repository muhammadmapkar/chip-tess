import numpy as np
import pandas as pd
import pytest

import config
from dataset import (
    draw_transit, generate_samples, null_kappa, pack_target, pixel_noise, prepare_cube, snr_per_unit_depth,
)
from pixels import gaussian_psf_image, star_flux_e_per_s

STARS = [(5.0, 5.0, 10.0), (2.0, 2.5, 11.5), (8.2, 7.0, 12.0)]


def make_field(n_t=6000, noise=3.0, seed=0, shape=(11, 11)):
    rng = np.random.default_rng(seed)
    time = np.arange(n_t) * (2.0 / 1440.0)
    base = sum(star_flux_e_per_s(t) * gaussian_psf_image(shape, x, y, 1.0) for x, y, t in STARS)
    flux = base[None] + rng.normal(0.0, noise, size=(n_t, *shape))
    return time, flux


def kept_frame():
    return pd.DataFrame({"ID": ["11", "12", "13"], "Tmag": [t for *_, t in STARS],
                         "x": [x for x, *_ in STARS], "y": [y for _, y, _ in STARS]})


def test_prepare_cube_zeros_bad_pixels_and_flags_bad_cadences():
    _, flux = make_field(n_t=200)
    flux[:, 0, 0] = np.nan          # dead pixel
    flux[7, 4, 4] = np.nan          # one bad sample in a good pixel
    out, fin, valid = prepare_cube(flux)
    assert not valid[0, 0] and valid[4, 4]
    assert (out[:, 0, 0] == 0).all()
    assert not fin[7] and fin.sum() == 199


def test_pixel_noise_recovers_white_noise_sigma_and_ignores_dead_pixels():
    _, flux = make_field(noise=3.0)
    flux[:, 0, 0] = 0.0
    sig = pixel_noise(flux, np.ones(len(flux), dtype=bool))
    assert np.median(sig[1:, 1:]) == pytest.approx(3.0, rel=0.05)
    assert np.isinf(sig[0, 0])


def test_snr_scales_as_sqrt_of_in_transit_cadences_and_with_kappa():
    sig = np.full((11, 11), 3.0)
    a = snr_per_unit_depth(5, 5, 10.0, sig, 100, 1.0)
    assert snr_per_unit_depth(5, 5, 10.0, sig, 400, 1.0) == pytest.approx(2 * a)
    assert snr_per_unit_depth(5, 5, 10.0, sig, 100, 2.0) == pytest.approx(a / 2)


def test_null_kappa_is_near_one_for_white_noise():
    time, flux = make_field(noise=3.0, seed=1)
    kappa = null_kappa(flux, time, (5.0, 5.0), np.random.default_rng(0))
    assert 1.0 <= kappa < 1.6


def test_null_kappa_is_nan_when_no_event_is_usable():
    time, flux = make_field(n_t=300)
    assert np.isnan(null_kappa(flux, time, (5.0, 5.0), np.random.default_rng(0)))


def test_generate_samples_respects_snr_floor_and_peak_lands_on_true_star():
    time, flux = make_field(noise=3.0, seed=2)
    flux, fin, _ = prepare_cube(flux)
    sig = pixel_noise(flux, fin)
    xy = np.array([[x, y] for x, y, _ in STARS])
    tm = np.array([t for *_, t in STARS])
    samples, n_failed = generate_samples(flux, time, fin, sig, 1.0, xy, tm, np.random.default_rng(3), k=15)
    assert len(samples) + n_failed == 15 and len(samples) >= 10
    assert all(m["snr"] >= config.SNR_ACCEPT_MIN for m in samples)
    assert all(config.DEPTH_MIN <= m["depth"] <= config.DEPTH_MAX for m in samples)
    strong = [m for m in samples if m["snr"] >= 15]
    assert strong
    for m in strong:
        py, px = np.unravel_index(np.argmax(m["diff"]), m["diff"].shape)
        near = int(np.argmin(np.hypot(xy[:, 0] - px, xy[:, 1] - py)))
        assert near == m["j"]


def test_pack_target_layout_padding_and_recentring():
    time, flux = make_field(noise=3.0, seed=4)
    flux, fin, _ = prepare_cube(flux)
    sig = pixel_noise(flux, fin)
    kept = kept_frame()
    xy = kept[["x", "y"]].to_numpy()
    samples, _ = generate_samples(flux, time, fin, sig, 1.0, xy, kept["Tmag"].to_numpy(), np.random.default_rng(5), k=4)
    packed = pack_target(samples, kept, (4.0, 6.0), tic_id=11, sector=7, crowd=0.4)
    s = len(samples)
    assert packed["X"].shape == (s, 3, 11, 11) and packed["star_xy"].shape == (s, 20, 2)
    assert packed["star_mask"][0].tolist() == [True] * 3 + [False] * 17
    assert (packed["star_tmag"][0, 3:] == 0).all() and (packed["star_tic"][0, 3:] == 0).all()
    # target (4, 6) moves to (5, 5): positions shift by (+1, -1)
    assert packed["star_xy"][0, 0].tolist() == [6.0, 4.0]
    assert packed["tic_id"].tolist() == [11] * s and packed["injected"].tolist() == [1] * s
    assert packed["y"].max() < 3 and np.isfinite(packed["X"]).all()


def test_draw_transit_ranges():
    time = np.arange(100) * 0.01
    rng = np.random.default_rng(0)
    for _ in range(200):
        p, d, e = draw_transit(time, rng)
        assert config.PERIOD_D[0] <= p <= config.PERIOD_D[1]
        assert config.DURATION_H[0] / 24 <= d <= config.DURATION_H[1] / 24
        assert time[0] <= e <= time[0] + p
