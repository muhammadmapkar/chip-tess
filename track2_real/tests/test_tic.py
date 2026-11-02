import numpy as np
import pandas as pd
import pytest

from tic import select_candidates, with_retries


def make_cat(tmags, dists, target_idx=0, **overrides):
    n = len(tmags)
    cat = pd.DataFrame({
        "ID": [str(100 + i) for i in range(n)], "objType": ["STAR"] * n, "disposition": ["--"] * n,
        "Tmag": tmags, "x": np.arange(n, dtype=float), "y": np.zeros(n), "d": dists,
    })
    for col, (i, val) in overrides.items():
        cat.loc[i, col] = val
    return cat, str(100 + target_idx)


def test_target_always_kept_even_if_faint_and_crowding_uses_kept_flux():
    cat, tid = make_cat([17.5, 10.0, 12.0], [0.0, 1.0, 2.0])
    kept, info = select_candidates(cat, tid)
    assert tid in set(kept["ID"])
    assert list(kept["Tmag"]) == [10.0, 12.0, 17.5]
    flux = 10 ** (-0.4 * np.array([10.0, 12.0, 17.5]))
    assert info["crowd"] == pytest.approx(flux[2] / flux.sum())


def test_tmag_cut_then_brightest_n_and_flux_lost():
    tm = [11.0] + [13.0 + 0.1 * i for i in range(30)] + [18.0, 19.0]
    cat, tid = make_cat(tm, [0.0] + [1.0] * 32)
    kept, info = select_candidates(cat, tid, n_stars=20, tmag_cut=16.0)
    assert len(kept) == 20
    assert (kept["Tmag"] <= 16.0).all()
    assert info["n_candidates"] == 33
    assert 0.0 < info["flux_lost"] < 1.0
    assert set(kept["Tmag"]) >= {11.0, 13.0}  # target and brightest neighbours


def test_filters_duplicates_extended_distance_and_missing_tmag():
    cat, tid = make_cat([10.0, 11.0, 11.5, 12.0, 12.5, np.nan], [0.0, 1.0, 1.0, 1.0, 4.0, 1.0],
                        disposition=(1, "DUPLICATE"), objType=(2, "EXTENDED"))
    kept, info = select_candidates(cat, tid)
    assert list(kept["ID"]) == ["100", "103"]
    assert info["flux_lost"] == pytest.approx(0.0)


def test_missing_target_or_tmag_raises():
    cat, tid = make_cat([10.0, 11.0], [0.0, 1.0])
    with pytest.raises(KeyError):
        select_candidates(cat, "999")
    cat.loc[0, "Tmag"] = np.nan
    with pytest.raises(ValueError):
        select_candidates(cat, tid)


def test_with_retries_retries_then_succeeds_and_reraises(monkeypatch):
    monkeypatch.setattr("tic.time.sleep", lambda s: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("boom")
        return "ok"

    assert with_retries(flaky) == "ok" and calls["n"] == 3
    with pytest.raises(RuntimeError):
        with_retries(lambda: (_ for _ in ()).throw(RuntimeError("always")), tries=2)
