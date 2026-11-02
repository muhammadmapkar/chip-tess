"""Phase 2 dataset parameters. Values are proposals until frozen in docs/protocol.md."""

# SPEC constants
N_STARS = 20
CUTOUT = 11
ALPHA = 0.10
SEEDS = (0, 1, 2, 3, 4)
SPLIT_FRACTIONS = {"train": 0.60, "val": 0.10, "cal": 0.15, "test": 0.15}

# candidate stars (TIC, Gaia-derived)
PIX_ARCSEC = 21.0
MAX_PIX = 3.0
TMAG_CUT = 16.0          # D12: stars fainter than this are dropped, except the target

# injection (approximations, see OPEN_QUESTIONS.md)
SIGMA_PIX = 1.0          # Gaussian PSF
DURATION_H = (1.0, 4.0)
PERIOD_D = (1.0, 10.0)   # log-uniform. Lower bound keeps the out-of-transit windows from overlapping
SNR_TARGET = (5.0, 30.0) # log-uniform target SNR (D13). SNR is the white-noise matched-filter SNR divided by kappa
SNR_ACCEPT_MIN = 5.0
NULL_DRAWS = 16          # null difference images per target, to measure kappa (z spread with no injection)
KAPPA_MIN_DRAWS = 6
DEPTH_MIN = 1e-4
DEPTH_MAX = 0.10
MIN_EVENTS = 2           # transits that must be usable in the data
SAMPLES_PER_TARGET = 20
MAX_TRIES = 40

# difference images (D14)
DETREND_ORDER = 1

# splits (D11): fixed split seed, clusters of targets closer than this are never separated
SPLIT_SEED = 0
CLUSTER_ARCMIN = 5.0

# runtime
WORKERS = 4
MIN_FREE_GB = 8.0
