# Plan

Date assumption: today is Nov 2, 2026 = Day 1. The Phase-III deadline of Nov 15, 2026 is Day 14. The deadline and the ISDIA 2027 page limit and template are not independently verified (see `OPEN_QUESTIONS.md`).

This is an aggressive schedule. Day 13 is a buffer. If Phase 2 slips past Day 5, cut the target count before cutting seeds or the shift test.

## Shared milestones

| Day | Date | Milestone |
|---|---|---|
| 1 | Nov 2 | Phase 0: scaffold published on `setup/scaffold`. Peer onboarding message sent. |
| 2 | Nov 3 | Review SPEC and protocol, settle open spec items, freeze. Muhammad tags `protocol-v1`. |
| 3 to 5 | Nov 4 to 6 | Data and generator built (both tracks, independently). |
| 6 to 8 | Nov 7 to 9 | Baselines, CNN, plain and Mondrian conformal, T1 to T3 passing. |
| 9 | Nov 10 | Shift test, off-target real check, TIC 4206066 display demo. |
| 10 | Nov 11 | All 5 seeds done. `results_synth.csv` and `results_real.csv` final. Figures. |
| 11 to 12 | Nov 12 to 13 | Section drafts from CSV numbers only. Merge into paper outline. |
| 13 | Nov 14 | Buffer. Honesty checklist, template check, AI-use and acknowledgment review. |
| 14 | Nov 15 | Deadline. Aim to submit on Day 13 if possible. |

## Track 2 (Muhammad), on branch `track2/real-pixels`

| Day | Work |
|---|---|
| 1 | Phase 0 scaffold. |
| 2 | Phase 1: data smoke test on 5 targets (file shapes, candidate counts, one difference-image figure). |
| 3 to 5 | Phase 2: scale to about 300 targets with caching and retries. Build and validate npz files. Crowding histogram and split counts. |
| 6 to 8 | Phase 3: baselines, CNN (print parameter count), plain and Mondrian conformal. |
| 9 | Shift test. Off-target TOI check (skip and log if infeasible). TIC 4206066 demo (shortlist only). |
| 10 | `results_real.csv`, figures. |
| 11 to 12 | Phase 4: Real Experiments and Results drafts. Abstract, Introduction, Related Work, Method overview, Limitations, Conclusion. |

## Track 1 (peer), on branches `track1/<task>`

| Day | Work |
|---|---|
| 2 | Onboard, read SPEC and protocol. |
| 3 to 4 | Generator, dip injection, difference images, field-ID splits. |
| 5 to 8 | Baselines, CNN, plain and Mondrian conformal, own tests T1 to T3. |
| 9 | Shift test and blur-mismatch test. |
| 10 | `results_synth.csv`, figures. |
| 11 to 12 | Controlled Experiments draft. |

## Checkpoints

- Day 2: protocol frozen before any result is seen.
- Day 8: both tracks pass T1 to T3.
- Day 10: results CSVs final. No tuning after this day.
- Day 13: every number in the paper traces to a CSV row.
