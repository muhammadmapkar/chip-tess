# Protocol (pre-registration)

Status: DRAFT. Freeze on Day 2 (Nov 3, 2026). After the freeze, Muhammad tags `protocol-v1` himself. Claude does not push tags.

Any change after the freeze goes in the Deviations section below with date and reason.

## Hypotheses

- **H1:** Overall test coverage is within 2 points of 90% at alpha = 0.10.
- **H2:** Plain split conformal under-covers in the most crowded bin.
- **H3:** Mondrian calibration restores coverage in that bin with larger shortlists.

We report each hypothesis as supported or not supported. Negative results are reported.

## Metrics

top-1, top-3, coverage (overall and per crowd bin), mean set size per bin, expected calibration error (15 bins). Definitions are in `SPEC.md`.

## Split rule

60% train, 10% val, 15% cal, 15% test. Split by target or field ID, never by sample.

## Seeds

0, 1, 2, 3, 4. Report mean and std across seeds.

## Baselines

- Star nearest the difference-image centroid.
- Brightest star.

## Shift test

Calibrate on the least crowded tercile, test on the most crowded. The exchangeability guarantee is not expected to hold here. We report the observed coverage whatever it is.

## Deviations

| date | what changed | reason |
|---|---|---|
| (none yet) | | |
