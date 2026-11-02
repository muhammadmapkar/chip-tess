# Crowding-Aware Conformal Prediction Sets for Host-Star Identification in TESS Pixel Images

Repo: https://github.com/muhammadmapkar/chip-tess

A small CNN scores the stars near a TESS brightness dip, and split conformal prediction turns those scores into a shortlist of stars that should contain the true source at least 90% of the time, calibrated per crowding level.

Setup is in branch `setup/scaffold`. Peer: read `START_HERE_PEER.md` first.

## The idea

A TESS pixel is about 21 arcsec wide, so several stars blend in one pixel. When a star dips in brightness, we do not know which nearby star caused it. A small CNN reads pixel images around the dip and scores each nearby candidate star. Split conformal prediction turns the scores into a shortlist of stars. The true source should be in the shortlist at least 90% of the time (alpha = 0.10). We also calibrate per crowding level (Mondrian) and test crowded fields on purpose.

Target venue: ISDIA 2027 (Springer LNNS). Phase-III deadline: Nov 15, 2026 (as given to us, not independently verified). Page limit and template are NOT verified. See `docs/paper_outline.md` for placeholders.

The work also serves as an ECTE408 project at UOWD. Open items are tracked in `OPEN_QUESTIONS.md`.

## Honesty rules

These apply to every file, figure, and sentence in this repo.

1. **No planet claims.** TIC 4206066 is a candidate from a Sept 2026 Zenodo preprint (Rabtsevich). Use it only as a display demo. Output the star shortlist only.
2. **State the exchangeability limit.** The coverage guarantee holds only if calibration and test data are exchangeable. Under shift (for example, calibrate on sparse fields and test on crowded fields) it can fail, and we report when it does.
3. **Report negative results.** If H1, H2, or H3 in `docs/protocol.md` fail, we say so.
4. **Do not claim to beat prior top-1 numbers.** Our setting (injected transits in real pixels, our own splits) is not directly comparable to published numbers.
5. **Novelty claim stays hedged:** "In about 40 papers checked, we found no conformal host-star method for TESS. This is not a systematic review."
6. **Candidate star source.** We use the TESS Input Catalog, written as "TIC (Gaia-derived)". We do not write "Gaia DR3" unless Gaia DR3 is truly used. The choice is logged in `OPEN_QUESTIONS.md`.

Style rule: no em-dashes in any file in this repo.

## Layout

| Path | What it is |
|---|---|
| `docs/SPEC.md` | Frozen shared contract (schema_version 1) |
| `docs/protocol.md` | Pre-registration (freeze on Day 2) |
| `docs/research_brief.md` | Source list with verification status |
| `docs/paper_outline.md` | Sections and owners |
| `track1_synthetic/` | Track 1 (peer): synthetic world |
| `track2_real/` | Track 2 (Muhammad): real TESS pixels |
| `PLAN.md` | Day-by-day plan (Day 1 = Nov 2, 2026) |
| `CONTRIBUTING.md` | Who edits what, how to merge |
| `OPEN_QUESTIONS.md` | Open items and logged assumptions |
| `AI_USE_LOG.md` | Log of generative AI use |
| `GIT_CHEATSHEET.md` | Exact git and gh commands |

## Tracks

Both tracks are fully independent. There is no code import between track folders. Each track writes its own implementation of the SPEC and its own tests, and writes `results_*.csv` with the columns defined in the SPEC. The two sets of results are compared only in the paper.

## What is not committed

`data/`, `*.npz`, `*.pt`, `*.ckpt`, `.venv/`, and any file over 5 MB. Small CSVs and figures are committed.

## Status

Phase 0 (scaffold) only. No experiments have been run and there are no results yet.
