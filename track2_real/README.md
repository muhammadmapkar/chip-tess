# Track 2: Real pixels (Muhammad)

Owner: Muhammad. Branches: `track2/<task>`. Edit only this folder.

## Goal

Test crowding-aware conformal prediction sets on real TESS pixels. Synthetic transits are injected into real SPOC 2-minute target pixel files, so the true source star is known while the real noise and real neighboring stars stay.

## Rules

- Do not import from `track1_synthetic/`. The two tracks are independent.
- Follow `../docs/SPEC.md` (schema_version 1) and `../docs/protocol.md`.
- Candidate stars come from the TESS Input Catalog. Write "TIC (Gaia-derived)", not "Gaia DR3".
- Proper motion is ignored. The Gaussian PSF used for injection (sigma = 1.0 pixel) is an approximation. Both are logged.
- Check every Lightkurve and astroquery function with installed docs or `help()` before use.
- No planet claims. TIC 4206066 is a display demo only: shortlist output, nothing more.
- Never commit `data/`, `*.npz`, `*.pt`, `*.ckpt`, `.venv/`, or files over 5 MB.
- No em-dashes in any file.

## Layout

| Path | Purpose |
|---|---|
| `TASKS.md` | Task list |
| `requirements.txt` | Python dependencies |
| `src/conformal.py` | Split and Mondrian conformal, per SPEC |
| `src/pixels.py` | Gaussian-PSF transit injection and difference images |
| `src/smoke_test.py` | Phase 1 smoke test (5 targets, needs network). Run from the repo root |
| `src/config.py` | Phase 2 parameters (proposals until frozen in the protocol) |
| `src/tic.py` | TIC cone queries, retries, candidate selection and crowding |
| `src/dataset.py` | Injection with an SNR target, null kappa, packing into the SPEC layout |
| `src/pool.py` | Target pool across galactic latitudes, crowding histogram, balanced selection |
| `src/build_dataset.py` | Per-target build with resume, then merge, splits, meta.json |
| `src/validate_dataset.py` | Hard checks, crowding histogram, split counts |
| `src/data_card.py` | Writes `DATA_CARD.md` from meta.json and the targets CSV |
| `src/detrend_check.py` | Null test of difference images by baseline order |
| `DATA_CARD.md` | Dataset description and limits |
| `tests/` | pytest tests. Data tests are skipped unless `--run-data` is passed |
| `outputs/` | Small CSVs and figures (committed). Large files go in `outputs/large/` (ignored) |

## Setup

From the repo root:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r track2_real/requirements.txt
pytest track2_real/tests
```

Data tests need processed data in `data/processed/` and run with `pytest track2_real/tests --run-data`.

## Phases

Phase 0 scaffold. Phase 1 data smoke test (5 targets). Phase 2 full dataset (about 300 targets). Phase 3 model, conformal, results. Phase 4 writing drafts. See `../PLAN.md`.
