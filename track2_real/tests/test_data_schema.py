"""Schema check for processed npz files. Skipped unless --run-data is passed."""
from pathlib import Path

import numpy as np
import pytest

PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"
N_STARS = 20

FIELD_SHAPES = {
    "X": lambda s: (s, 3, 11, 11),
    "star_xy": lambda s: (s, N_STARS, 2),
    "star_tmag": lambda s: (s, N_STARS),
    "star_mask": lambda s: (s, N_STARS),
    "y": lambda s: (s,),
    "crowd": lambda s: (s,),
    "snr": lambda s: (s,),
    "depth_ppm": lambda s: (s,),
    "tic_id": lambda s: (s,),
    "injected": lambda s: (s,),
}


@pytest.mark.data
def test_processed_npz_schema():
    files = sorted(PROCESSED.glob("*.npz"))
    if not files:
        pytest.skip(f"no npz files in {PROCESSED}")
    for f in files:
        d = np.load(f)
        s = d["y"].shape[0]
        for name, shape_fn in FIELD_SHAPES.items():
            assert name in d.files, f"{f.name}: missing {name}"
            assert d[name].shape == shape_fn(s), f"{f.name}: bad shape for {name}"
        y = d["y"].astype(int)
        assert ((y >= 0) & (y < N_STARS)).all()
        assert d["star_mask"].astype(bool)[np.arange(s), y].all(), f"{f.name}: true star is masked"
        assert np.isfinite(d["X"]).all(), f"{f.name}: non-finite pixels"
