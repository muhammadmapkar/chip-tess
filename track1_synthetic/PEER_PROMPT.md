# Peer prompt: Track 1 (synthetic world)

Paste everything below this line into your own Claude Code, started inside your clone of the repo.

---

ROLE
You are the engineer for Track 1 of a two-person research repo. Work inside `track1_synthetic/` only. Work in phases. Stop at the end of each phase and wait for me to say "continue." Never use em-dashes in any file you write. Do not invent APIs: before using any library function you are unsure about, check the installed docs or `help()`.

ISOLATION RULES
- Do not read, list, or import anything in `track2_real/`. The two tracks are fully independent. No code import between track folders.
- Edit only files inside `track1_synthetic/`. Shared files (`docs/`, root files) change only by pull request with the other person's approval.

GIT RULES (strict)
- Push only to my own fork (`origin`), and only branches named `track1/<task>`. Never push anywhere else. Never push to `main`.
- Forbidden: force push, deleting branches, opening or merging pull requests for me, pushing tags, touching any remote other than my fork, putting tokens or passwords in any file or URL.
- If authentication fails, stop and tell me to run `gh auth login` or fix SSH. Do not ask me for tokens.
- Never commit `data/`, `*.npz`, `*.pt`, `*.ckpt`, `.venv/`, or any file over 5 MB.
- Commit often with clear messages. I open the pull request myself.

PROJECT
Title: Crowding-Aware Conformal Prediction Sets for Host-Star Identification in TESS Pixel Images.
A TESS pixel is about 21 arcsec wide. Several stars blend in one pixel. When a star dips in brightness, we do not know which nearby star caused it. A small CNN reads pixel images around the dip and scores each nearby candidate star. Split conformal prediction turns the scores into a shortlist of stars. The true source should be in the shortlist at least 90% of the time. We also calibrate per crowding level (Mondrian) and test crowded fields on purpose.
Venue: ISDIA 2027 (Springer LNNS). Page limit and template are NOT verified. Do not invent them.

HONESTY RULES
1. No planet claims. Output the star shortlist only.
2. State the exchangeability limit. The coverage guarantee holds only if calibration and test data are exchangeable.
3. Report negative results.
4. Do not claim to beat prior top-1 numbers.
5. Novelty claim stays hedged: "In about 40 papers checked, we found no conformal host-star method for TESS. This is not a systematic review."
6. Candidate star source in real data is "TIC (Gaia-derived)", not "Gaia DR3". This matters only for the other track, but keep the wording if you mention it.

YOUR TRACK: SYNTHETIC WORLD
1. Generator: 11x11 grid, random stars with Tmag, Gaussian PSF (sigma is a parameter), Gaussian noise. Knobs: star density (crowding), PSF width, noise level.
2. Inject a dip at one known star. Build difference images.
3. Split by field ID per SPEC.
4. Baselines, CNN, plain conformal, Mondrian conformal. Own implementation and own tests (T1 to T3).
5. Shift test (SPEC). Blur-mismatch test: train at one PSF width, test at another.
6. Output `results_synth.csv`, figures, and a draft of the Controlled Experiments section.

Definition of done: T1 to T3 pass; all 5 seeds run with mean and std reported; `results_synth.csv` uses the SPEC columns; every number in the draft comes from the CSV; negative results are reported.

Put code in `track1_synthetic/src/` and tests in `track1_synthetic/tests/`. Use the requirements in `track1_synthetic/requirements.txt`.

If something in the SPEC is ambiguous, do not guess silently. Write the ambiguity down in a file inside `track1_synthetic/` (for example `NOTES.md`), pick the most conservative reading, and tell me so I can raise it with Muhammad before the Day 2 protocol freeze.

START
Phase A: read the SPEC below and `docs/protocol.md`, then propose the file layout and function list for `track1_synthetic/src/`. Do not write code yet. Stop and wait for "continue."

---

SPEC (copy of docs/SPEC.md; if it ever differs from docs/SPEC.md on the branch, docs/SPEC.md wins)

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
