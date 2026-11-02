import numpy as np

import config
from build_dataset import assign_splits, clusters_by_separation


def test_clusters_link_close_targets_transitively_and_keep_far_ones_apart():
    ra = np.array([10.0, 10.0 + 4.0 / 60, 10.0 + 8.0 / 60, 50.0])  # 4 arcmin steps at dec 0
    dec = np.zeros(4)
    lab = clusters_by_separation(ra, dec, arcmin=5.0)
    assert lab[0] == lab[1] == lab[2] and lab[3] != lab[0]


def test_clusters_handle_ra_wraparound_and_poles_without_nan():
    lab = clusters_by_separation(np.array([359.99, 0.01, 180.0]), np.array([0.0, 0.0, 89.9]), arcmin=5.0)
    assert lab[0] == lab[1] and lab[2] != lab[0]


def test_splits_follow_target_fractions_and_never_split_a_cluster():
    cluster = np.repeat(np.arange(120), [1] * 100 + [5] * 20)  # 100 singles and 20 clusters of 5
    out = assign_splits(cluster)
    assert set(out) == set(np.unique(cluster))
    tally = {s: 0 for s in config.SPLIT_FRACTIONS}
    for c in cluster:
        tally[out[c]] += 1
    total = len(cluster)
    for s, f in config.SPLIT_FRACTIONS.items():
        assert abs(tally[s] / total - f) < 0.05, (s, tally)


def test_splits_are_deterministic_for_a_seed_and_change_with_it():
    cluster = np.arange(200)
    assert assign_splits(cluster, seed=0) == assign_splits(cluster, seed=0)
    assert assign_splits(cluster, seed=0) != assign_splits(cluster, seed=1)
