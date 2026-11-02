"""Validate data/processed/{train,val,cal,test}.npz and print the crowding histogram and split counts.

Run from the repo root:  python track2_real/src/validate_dataset.py
Hard checks fail the run. The peak-pixel sanity numbers are a check that injected dips land on the
labelled star, not a result for the paper.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import config  # noqa: E402
from conformal import assign_crowd_bins  # noqa: E402

PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"
SHAPES = {"X": lambda s: (s, 3, 11, 11), "star_xy": lambda s: (s, 20, 2), "star_tmag": lambda s: (s, 20),
          "star_mask": lambda s: (s, 20), "y": lambda s: (s,), "crowd": lambda s: (s,), "snr": lambda s: (s,),
          "depth_ppm": lambda s: (s,), "tic_id": lambda s: (s,), "injected": lambda s: (s,)}


def text_hist(values, bins=10, width=36):
    counts, edges = np.histogram(values, bins=bins, range=(0, 1))
    for c, lo, hi in zip(counts, edges[:-1], edges[1:]):
        print(f"  {lo:4.2f}-{hi:4.2f} {'#' * int(round(width * c / max(counts.max(), 1))):<{width}} {c}")


def main():
    meta = json.loads((PROCESSED / "meta.json").read_text())
    edges = np.array(meta["crowd_edges_cal"])
    data = {s: dict(np.load(PROCESSED / f"{s}.npz")) for s in config.SPLIT_FRACTIONS}
    failures = []

    def check(ok, msg):
        if not ok:
            failures.append(msg)
            print("FAIL:", msg)

    tics = {}
    for s, d in data.items():
        n = d["y"].shape[0]
        for k, fn in SHAPES.items():
            check(d[k].shape == fn(n), f"{s}.{k} shape {d[k].shape}")
        check(np.isfinite(d["X"]).all(), f"{s}: non-finite pixels")
        check(((d["y"] >= 0) & (d["y"] < config.N_STARS)).all(), f"{s}: y out of range")
        check(d["star_mask"][np.arange(n), d["y"]].all(), f"{s}: true star is masked")
        check(((d["crowd"] > 0) & (d["crowd"] <= 1)).all(), f"{s}: crowd outside (0, 1]")
        check((d["snr"] >= config.SNR_ACCEPT_MIN).all(), f"{s}: snr below floor")
        check(((d["depth_ppm"] >= config.DEPTH_MIN * 1e6 * 0.999) & (d["depth_ppm"] <= config.DEPTH_MAX * 1e6 * 1.001)).all(),
              f"{s}: depth outside range")
        check((d["star_tmag"][~d["star_mask"]] == 0).all(), f"{s}: padded Tmag not zero")
        check(d["star_mask"].sum(axis=1).min() >= 1, f"{s}: sample with no stars")
        tics[s] = set(map(int, np.unique(d["tic_id"])))
    names = list(data)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            check(not (tics[a] & tics[b]), f"targets shared between {a} and {b}")
    total = sum(len(d["y"]) for d in data.values())
    print(f"samples {total}, targets {sum(len(t) for t in tics.values())}")

    print("\nsplit counts (samples / targets), then per crowding bin (0 = most crowded):")
    print(f"  tercile edges from cal set: {np.round(edges, 4).tolist()}")
    print(f"  {'split':<6}{'samples':>8}{'targets':>8}   samples per bin   targets per bin")
    for s, d in data.items():
        b = assign_crowd_bins(d["crowd"], edges)
        spb = [int((b == k).sum()) for k in range(3)]
        tpb = [len(np.unique(d["tic_id"][b == k])) for k in range(3)]
        print(f"  {s:<6}{len(d['y']):>8}{len(tics[s]):>8}   {spb}   {tpb}")
        if s == "cal":
            check(min(spb) >= 10, f"cal has a crowding bin with fewer than 10 samples: {spb}")

    allc = np.concatenate([d["crowd"] for d in data.values()])
    print("\ncrowding histogram, all samples (target flux / kept flux):")
    text_hist(allc)
    print("\nsnr (kappa-corrected) quantiles 5/50/95%:", np.round(np.percentile(
        np.concatenate([d["snr"] for d in data.values()]), [5, 50, 95]), 1).tolist())
    print("candidates per sample, mean:", round(float(np.concatenate([d["star_mask"].sum(1) for d in data.values()]).mean()), 1))

    print("\npeak-pixel sanity (diff channel argmax -> nearest candidate == true star), by crowding bin. Not a result.")
    X = np.concatenate([d["X"] for d in data.values()])
    xy = np.concatenate([d["star_xy"] for d in data.values()])
    mk = np.concatenate([d["star_mask"] for d in data.values()])
    y = np.concatenate([d["y"] for d in data.values()])
    bins = assign_crowd_bins(np.concatenate([d["crowd"] for d in data.values()]), edges)
    hit = np.zeros(len(y), dtype=bool)
    for i in range(len(y)):
        py, px = np.unravel_index(np.argmax(X[i, 0]), X[i, 0].shape)
        dist = np.hypot(xy[i, :, 0] - px, xy[i, :, 1] - py)
        dist[~mk[i]] = np.inf
        hit[i] = int(np.argmin(dist)) == y[i]
    for k in range(3):
        print(f"  bin {k}: {hit[bins == k].mean():.3f} of {int((bins == k).sum())}")
    print("\nresult:", "FAILED" if failures else "all hard checks passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
