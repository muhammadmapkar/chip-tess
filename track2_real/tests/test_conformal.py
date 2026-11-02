import numpy as np

from conformal import (
    assign_crowd_bins,
    conformal_cutoff,
    crowd_bin_edges,
    mondrian_cutoffs,
    mondrian_prediction_sets,
    prediction_sets,
    true_star_scores,
)

N_STARS = 20


def random_probs(rng, n_samples):
    logits = rng.normal(size=(n_samples, N_STARS))
    e = np.exp(logits - logits.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def test_t1_perfect_model_full_coverage_set_size_one():
    rng = np.random.default_rng(0)
    n_cal, n_test = 100, 200
    y_cal = rng.integers(0, N_STARS, n_cal)
    y_test = rng.integers(0, N_STARS, n_test)
    probs_cal = np.eye(N_STARS)[y_cal]
    probs_test = np.eye(N_STARS)[y_test]
    mask = np.ones((n_test, N_STARS), dtype=bool)

    cutoff = conformal_cutoff(true_star_scores(probs_cal, y_cal), alpha=0.1)
    sets = prediction_sets(probs_test, mask, cutoff)

    assert sets[np.arange(n_test), y_test].mean() == 1.0
    assert (sets.sum(axis=1) == 1).all()


def test_t2_random_scores_random_labels_coverage_near_90():
    rng = np.random.default_rng(1)
    n_cal, n_test, repeats = 200, 500, 200
    coverages = []
    for _ in range(repeats):
        probs = random_probs(rng, n_cal + n_test)
        y = rng.integers(0, N_STARS, n_cal + n_test)
        cutoff = conformal_cutoff(true_star_scores(probs[:n_cal], y[:n_cal]), alpha=0.1)
        mask = np.ones((n_test, N_STARS), dtype=bool)
        sets = prediction_sets(probs[n_cal:], mask, cutoff)
        coverages.append(sets[np.arange(n_test), y[n_cal:]].mean())
    assert 0.88 <= np.mean(coverages) <= 0.92


def test_t3_cutoff_is_max_for_n9_and_inf_for_n5():
    rng = np.random.default_rng(2)
    scores9 = rng.random(9)
    assert conformal_cutoff(scores9, 0.1) == scores9.max()
    assert conformal_cutoff(rng.random(5), 0.1) == float("inf")


def test_cutoff_k_th_smallest_and_boundary_sizes():
    scores = np.arange(1.0, 20.0)  # n = 19, k = ceil(20 * 0.9) = 18
    assert conformal_cutoff(scores, 0.1) == 18.0
    assert conformal_cutoff(np.arange(1.0, 9.0), 0.1) == float("inf")  # n = 8, k = 9
    assert conformal_cutoff(np.array([]), 0.1) == float("inf")


def test_prediction_sets_never_include_masked_stars():
    probs = np.array([[0.5, 0.3, 0.2], [0.1, 0.1, 0.8]])
    mask = np.array([[True, True, False], [True, False, True]])
    sets = prediction_sets(probs, mask, float("inf"))
    assert (sets == mask).all()


def test_prediction_sets_threshold_is_inclusive():
    probs = np.array([[0.6, 0.4]])
    mask = np.ones((1, 2), dtype=bool)
    assert prediction_sets(probs, mask, 0.6).tolist() == [[True, True]]
    assert prediction_sets(probs, mask, 0.5).tolist() == [[True, False]]


def test_mondrian_uses_one_cutoff_per_bin_and_edges_from_cal_only():
    rng = np.random.default_rng(3)
    cal_crowd = rng.random(300)
    edges = crowd_bin_edges(cal_crowd)
    assert edges.shape == (2,)
    bins = assign_crowd_bins(cal_crowd, edges)
    assert set(bins) == {0, 1, 2}

    scores = rng.random(300)
    cutoffs = mondrian_cutoffs(scores, bins, 0.1)
    for b in range(3):
        assert cutoffs[b] == conformal_cutoff(scores[bins == b], 0.1)

    probs = random_probs(rng, 300)
    mask = np.ones((300, N_STARS), dtype=bool)
    sets = mondrian_prediction_sets(probs, mask, bins, cutoffs)
    for b in range(3):
        rows = bins == b
        assert (sets[rows] == prediction_sets(probs[rows], mask[rows], cutoffs[b])).all()


def test_mondrian_empty_bin_gets_inf():
    cutoffs = mondrian_cutoffs(np.array([0.1, 0.2]), np.array([0, 0]), 0.1, n_bins=3)
    assert np.isinf(cutoffs).all()
