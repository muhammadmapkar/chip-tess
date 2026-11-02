# SPEC (frozen shared contract)

schema_version: 1

Both tracks implement this independently. Changes after the Day 2 freeze go through a pull request and are logged in the Deviations section of `protocol.md`. Gaps found while writing this file are listed in `OPEN_QUESTIONS.md`, section D.

## Constants

- alpha = 0.10
- Maximum candidate stars per sample: N = 20
- Cutout: 11 x 11 pixels
- Channels (3): difference image, reference image, noise map

## Crowding

- Crowding = target flux / sum of candidate fluxes
- flux = 10^(-0.4 * Tmag)
- Lower means more crowded.
- Crowding bins: 3 terciles. Cut points are computed on the calibration set only.

## Splits

- 60% train, 10% val, 15% cal, 15% test.
- Split by target or field ID, never by sample.

## Seeds

- Seeds: 0, 1, 2, 3, 4.
- Report mean and std across seeds.

## Model

- CNN with under 1M parameters.
- Output a heatmap. Sample it at each candidate star pixel position.
- Softmax over real (unmasked) stars.
- Cross-entropy loss.

## Baselines

- Star nearest the difference-image centroid.
- Brightest star.

## Conformal

- Score = 1 - p(true star).
- Split conformal.
- cutoff = the k-th smallest calibration score, with k = ceil((n + 1) * (1 - alpha)).
- If k > n, cutoff = +inf.
- A star enters the set if (1 - p) <= cutoff.

Required function signatures (each track writes its own copy):

```python
def conformal_cutoff(cal_scores: np.ndarray, alpha: float) -> float: ...

def prediction_sets(probs: np.ndarray, mask: np.ndarray, cutoff: float) -> np.ndarray:
    """Returns bool array of shape [S, N]."""
```

Mondrian: one cutoff per crowding bin.

## Metrics

- top-1
- top-3
- coverage, overall and per crowd bin
- mean set size per bin
- expected calibration error (ECE), 15 bins

## Results CSV

Columns, in this order:

```
method, dataset, crowd_bin, seed, n, top1, top3, coverage, mean_set_size, ece
```

Track 1 writes `results_synth.csv`. Track 2 writes `results_real.csv`.

## Required conformal tests

Each track must pass its own copy.

- **T1:** a perfect model gives coverage 1.0 and set size 1.
- **T2:** random scores and random labels, averaged over 200 repeated random splits, give mean coverage between 0.88 and 0.92.
- **T3:** for n = 9 and alpha = 0.1, k = ceil(10 * 0.9) = 9, so cutoff = the largest calibration score. For n = 5 and alpha = 0.1, k = 6 > n, so cutoff = +inf.
