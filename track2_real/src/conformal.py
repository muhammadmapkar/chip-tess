"""Split and Mondrian conformal prediction for host-star shortlists (SPEC, schema_version 1).

Score = 1 - p(true star). A star enters the set if (1 - p) <= cutoff.
"""
import math

import numpy as np


def conformal_cutoff(cal_scores: np.ndarray, alpha: float) -> float:
    """k-th smallest calibration score, k = ceil((n + 1) * (1 - alpha)). +inf if k > n."""
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1), got {alpha}")
    scores = np.asarray(cal_scores, dtype=float).ravel()
    n = scores.size
    # the small offset keeps float noise (for example 10 * 0.9) from bumping k up by one
    k = math.ceil((n + 1) * (1.0 - alpha) - 1e-9)
    if k > n:
        return float("inf")
    return float(np.partition(scores, k - 1)[k - 1])


def prediction_sets(probs: np.ndarray, mask: np.ndarray, cutoff: float) -> np.ndarray:
    """Bool array [S, N]. Only real (unmasked) stars can enter a set."""
    probs = np.asarray(probs, dtype=float)
    mask = np.asarray(mask, dtype=bool)
    if probs.shape != mask.shape:
        raise ValueError(f"probs {probs.shape} and mask {mask.shape} must match")
    return mask & ((1.0 - probs) <= cutoff)


def true_star_scores(probs: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Conformal score 1 - p(true star) for each sample. y holds the true star index."""
    probs = np.asarray(probs, dtype=float)
    y = np.asarray(y, dtype=int)
    return 1.0 - probs[np.arange(probs.shape[0]), y]


def crowd_bin_edges(cal_crowd: np.ndarray, n_bins: int = 3) -> np.ndarray:
    """Tercile cut points (n_bins - 1 values), computed on the calibration set only."""
    qs = np.arange(1, n_bins) / n_bins
    return np.quantile(np.asarray(cal_crowd, dtype=float), qs)


def assign_crowd_bins(crowd: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Bin index per sample. Bin 0 is the lowest crowding value, i.e. the most crowded."""
    return np.searchsorted(np.asarray(edges, dtype=float), np.asarray(crowd, dtype=float), side="right")


def mondrian_cutoffs(cal_scores: np.ndarray, cal_bins: np.ndarray, alpha: float, n_bins: int = 3) -> np.ndarray:
    """One cutoff per crowding bin. A bin with too few samples gets +inf (see conformal_cutoff)."""
    cal_scores = np.asarray(cal_scores, dtype=float)
    cal_bins = np.asarray(cal_bins, dtype=int)
    return np.array([conformal_cutoff(cal_scores[cal_bins == b], alpha) for b in range(n_bins)])


def mondrian_prediction_sets(probs: np.ndarray, mask: np.ndarray, bins: np.ndarray, cutoffs: np.ndarray) -> np.ndarray:
    """Bool array [S, N], using the cutoff of each sample's crowding bin."""
    probs = np.asarray(probs, dtype=float)
    bins = np.asarray(bins, dtype=int)
    sets = np.zeros(probs.shape, dtype=bool)
    for b, cutoff in enumerate(cutoffs):
        rows = bins == b
        sets[rows] = prediction_sets(probs[rows], np.asarray(mask, dtype=bool)[rows], cutoff)
    return sets
