# Open questions and logged assumptions

Status values: OPEN (needs an answer), ASSUMED (we proceed on this assumption), DECIDED.

## A. Course and venue (ECTE408 at UOWD, ISDIA 2027)

| # | Item | Status | Notes |
|---|---|---|---|
| A1 | Is Python allowed for the ECTE408 project, or is MATLAB required? | OPEN | Ask the lecturer. Whole repo is Python. |
| A2 | Does the lecturer approve reusing this work for an ISDIA submission? | OPEN | Ask before any submission. |
| A3 | GenAI acknowledgment rules for ECTE408 and for ISDIA | OPEN | `AI_USE_LOG.md` is kept meanwhile. Git attribution choice: no co-author trailers (Muhammad's decision, Day 1). Revisit when rules are known. |
| A4 | ISDIA 2027 page limit | OPEN | NOT verified. Placeholder: `[PAGE LIMIT: TBD]`. Do not invent a limit. |
| A5 | Springer LNNS template details for ISDIA 2027 | OPEN | NOT verified. Placeholder: `[TEMPLATE: TBD]`. |
| A6 | Phase-III deadline Nov 15, 2026 | ASSUMED | Taken from the project brief, not independently verified. Equals Day 14. |

## B. Dates

| # | Item | Status | Notes |
|---|---|---|---|
| B1 | Date assumption | ASSUMED | Today is Nov 2, 2026 = Day 1. All plans use day numbers. |
| B2 | `protocol-v1` tag | OPEN | Protocol freezes on Day 2. Muhammad creates the tag himself. Claude does not push tags. |

## C. Data choices

| # | Item | Status | Notes |
|---|---|---|---|
| C1 | Candidate star source | DECIDED | TESS Input Catalog, written as "TIC (Gaia-derived)". Not written as "Gaia DR3" unless Gaia DR3 is actually queried. Currently no Gaia DR3 query is planned. |
| C2 | Proper motion | ASSUMED | Ignored when converting candidate sky positions to pixels. Logged as an approximation. |
| C3 | Injection PSF | ASSUMED | Gaussian, sigma = 1.0 pixel (parameter). An approximation of the real TESS PSF. Logged. |
| C4 | TIC 4206066 | ASSUMED | Candidate from a Sept 2026 Zenodo preprint (Rabtsevich). We have not verified the preprint. Display demo only. Shortlist only, no planet claim. |
| C5 | 40 known off-target TOIs (arXiv 2310.15833) | OPEN | Not yet checked whether the list, true hosts, and 2-minute pixel cutouts are obtainable. If not feasible, log here and skip. |

## D. SPEC ambiguities to settle before the Day 2 freeze

These are gaps in `docs/SPEC.md` found while writing it. Neither track should silently choose. Resolve by pull request on SPEC, then freeze.

| # | Gap | Proposed default |
|---|---|---|
| D1 | Crowding formula: does the sum of candidate fluxes include the target itself? | Sum over all unmasked candidates, target included, so crowding is in (0, 1]. |
| D2 | "Target" vs "true source": in injection experiments the true source can be a neighbor, not the TIC target. Which star's flux is the numerator? | The true source (injected star). To be confirmed. |
| D3 | Heatmap sampling at star positions: nearest pixel or bilinear? | Bilinear, with positions clipped to the 11x11 grid. |
| D4 | ECE for a softmax over stars | Top-1 confidence vs top-1 correctness, 15 equal-width bins. |
| D5 | `crowd_bin` values in the results CSV, and the value for overall rows | `0,1,2` for terciles (0 = most crowded) and `all` for overall. `dataset` values: `synth`, `real`, plus a suffix for shift tests. |
| D6 | Shift test cutoffs: are the tercile cut points taken from the calibration set only, as in SPEC? | Yes. Calibrate on the least crowded tercile of the cal set, test on the most crowded tercile of the test set. |
| D7 | Multiple injections per target and exchangeability | Split by target ID. Within a split, samples from one target are correlated. Must be stated as a limit. See D8. |
| D8 | Minimum calibration size per bin: with alpha = 0.10, the cutoff is +inf for n <= 8 (k = ceil(0.9 * (n + 1)) > n), so sets are everything | Plan at least 10 calibration samples per bin, so at least about 30 calibration samples, preferably hundreds. With about 300 targets and a 15% cal split (about 45 targets), use several injections per target. |
| D9 | Empty prediction sets: the SPEC rule can produce an empty set when the cutoff is below every star's score | Report empty-set rate. Do not patch silently. |
| D10 | Padding for fewer than 20 candidates: mask semantics and value used in `star_xy`, `star_tmag` | `star_mask` True = real star. Padded entries are zero and ignored. |
| D11 | Seeds: do seeds change the data split, the model init, or both? | Model init and training order only. Splits fixed by a split seed recorded in meta.json. Needs confirmation. |

## E. Environment

| # | Item | Status | Notes |
|---|---|---|---|
| E1 | Python version used for the venv | DECIDED | Python 3.15.0 (Homebrew). Installed: numpy 2.5.4, scipy 1.18.1, torch 2.15.0, astropy 8.0.2, lightkurve 2.6.0, astroquery 0.4.11, matplotlib 3.11.2, pandas 2.3.3, pytest 9.2.0. Peer may use a different Python version. Requirements are unpinned for now. |
| E2 | Peer's GitHub handle and whether peer is a collaborator or a fork | OPEN | START_HERE_PEER.md supports both. |
| E3 | Lightkurve and astroquery calls | ASSUMED | Every function is checked with installed docs or `help()` before use. No API is assumed from memory. |
