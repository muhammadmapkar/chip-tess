# Generative AI use log

Log every substantial use of generative AI. GenAI acknowledgment rules for ECTE408 and ISDIA are not yet known (see `OPEN_QUESTIONS.md`, A3).

| date | tool | purpose | prompt summary | output used | how verified |
|---|---|---|---|---|---|
| 2026-11-02 | Claude Code (Claude Sonnet 5.5) | Phase 0 scaffold: folder tree, docs, SPEC, protocol, conformal functions and tests for Track 2, git setup and publishing of branch `setup/scaffold` | Long role prompt describing the project, honesty rules, git rules, SPEC, and Track 1 and Track 2 tasks | Scaffold files, `track2_real/src/conformal.py` and its tests | Muhammad reviews the pull request. Tests T1 to T3 run with pytest. Em-dash check by grep. Library functions are checked against installed docs before use. arXiv summaries beyond 2310.15833 are marked not verified. |
| 2026-11-02 | Claude Code (Claude Sonnet 5.5) | Phase 1 data smoke test: pixel helpers, 5-target download, TIC candidate stars, injected dip, difference-image figures | Run Phase 1 on 5 targets and report shapes, candidate counts, one figure, API problems | `track2_real/src/pixels.py`, `smoke_test.py`, unit tests, figures, OPEN_QUESTIONS D12 to D16 | Lightkurve and astroquery signatures read from installed docs first. Unit tests on synthetic cubes. Overlay figures checked by eye. WCS checked against the brightest flux pixel. Flux scale checked against sparse targets. |

Git attribution: Muhammad chose no `Co-Authored-By` trailer for Claude on commits (2026-11-02). AI use is disclosed here instead.
