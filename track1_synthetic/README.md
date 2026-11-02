# Track 1: Synthetic world (peer)

Owner: peer. Branches: `track1/<task>`. Edit only this folder.

## Goal

Build a controlled synthetic world where the true host star is known exactly, so we can test crowding-aware conformal prediction sets under conditions we control: star density, PSF width, noise level.

## Rules

- Do not read or import `track2_real/`. The two tracks are independent.
- Follow `../docs/SPEC.md` (schema_version 1) and `../docs/protocol.md`.
- Write your own implementation of `conformal_cutoff` and `prediction_sets` and your own tests T1 to T3.
- Output `results_synth.csv` with the SPEC columns.
- Follow the honesty rules in `../README.md`.
- Never commit `data/`, `*.npz`, `*.pt`, `*.ckpt`, `.venv/`, or files over 5 MB.
- No em-dashes in any file.

## Layout

| Path | Purpose |
|---|---|
| `TASKS.md` | Task list |
| `PEER_PROMPT.md` | Prompt to paste into your own Claude Code |
| `requirements.txt` | Python dependencies |
| `src/` | Your code |
| `tests/` | Your tests |

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r track1_synthetic/requirements.txt
pytest track1_synthetic/tests
```
