# Track 2 tasks (Muhammad): real pixels

1. **Targets.** Pick about 300 TESS targets. Mix crowded and sparse fields (for example, TIC cone searches at low and high galactic latitude). Use SPOC 2-minute target pixel files. Cache in `data/raw` (git-ignored).
2. **Candidate stars.** Get candidate neighbor stars within about 3 pixels from the TIC (position and Tmag). Convert sky positions to pixels with the file's WCS. Log that proper motion is ignored.
3. **Crowding.** Compute crowding per SPEC.
4. **Injection.** Inject synthetic transits into real pixels. Start with a Gaussian PSF (sigma = 1.0 pixel as a parameter) and log it as an approximation. Random period, epoch, duration (1 to 4 hours), and depth. Record SNR. The true source is the star the dip was injected into. Real noise and real stars stay.
5. **Images.** Build difference images (mean out-of-transit minus mean in-transit), reference image, and noise map. Crop or pad to 11x11 around the target. Log TPF shapes.
6. **Data files.** Write npz files plus `meta.json` in `data/processed` (git-ignored). Fields: `X [S,3,11,11]`, `star_xy [S,20,2]`, `star_tmag [S,20]`, `star_mask [S,20]`, `y [S]`, `crowd [S]`, `snr [S]`, `depth_ppm [S]`, `tic_id [S]`, `injected [S]`. Write `DATA_CARD.md`.
7. **Models and conformal.** Baselines, CNN, plain conformal, Mondrian conformal. Own implementation and own tests (T1 to T3).
8. **Off-target check.** Find the 40 known off-target TOIs with known true hosts (ExoFOP notes, per arXiv 2310.15833). Check if cutouts exist. Build a small real set if feasible. If not, log it in `OPEN_QUESTIONS.md` and skip.
9. **Display demo.** TIC 4206066: shortlist only, no planet claim.
10. **Outputs.** `results_real.csv`, figures, and a draft of the Real Experiments section.

## Phase gates

- Phase 1: 5 targets only. Show file shapes, candidate star counts, one difference-image figure with candidate positions overlaid. Report API problems.
- Phase 2: about 300 targets with caching and retries. Build and validate npz files. Print the crowding histogram and split counts.
- Phase 3: baselines, CNN (print parameter count), plain and Mondrian conformal, shift test, `results_real.csv`, figures.
- Phase 4: draft Real Experiments and Results text with numbers pulled from the CSV only.
