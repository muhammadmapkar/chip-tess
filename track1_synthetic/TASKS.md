# Track 1 tasks (peer): synthetic world

1. **Generator.** 11x11 grid, random stars with Tmag, Gaussian PSF (sigma is a parameter), Gaussian noise. Knobs: star density (crowding), PSF width, noise level.
2. **Dip injection.** Inject a dip at one known star. Build difference images.
3. **Splits.** Split by field ID per SPEC.
4. **Models and conformal.** Baselines, CNN, plain conformal, Mondrian conformal. Own implementation and own tests (T1 to T3).
5. **Stress tests.** Shift test (see SPEC and protocol). Blur-mismatch test: train at one PSF width, test at another.
6. **Outputs.** `results_synth.csv`, figures, and a draft of the Controlled Experiments section.

## Definition of done

- T1 to T3 pass.
- All 5 seeds (0 to 4) run. Mean and std reported.
- `results_synth.csv` uses the SPEC columns.
- Every number in the draft comes from the CSV.
- Negative results are reported, not hidden.
