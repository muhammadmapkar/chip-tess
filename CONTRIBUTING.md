# Contributing

## Ownership

- Each person edits only their own track folder. Muhammad: `track2_real/`. Peer: `track1_synthetic/`.
- Shared files (everything in `docs/` and the root files) change only by pull request, with the other person's approval.
- No code import between track folders. Do not read the other track's folder while building your track.

## Branches

- Peer: `track1/<task>`
- Muhammad: `track2/<task>`
- Scaffold: `setup/scaffold`
- Never push to `main` directly. Never force push. Never delete branches that others use.

## Pull requests

- Use `.github/pull_request_template.md`.
- Merge pull requests with **Create a merge commit**. Never squash.
- The other person reviews. Do not merge your own pull request without approval.

## Do not commit

`data/`, `*.npz`, `*.pt`, `*.ckpt`, `.venv/`, and any file over 5 MB. Never put tokens or passwords in any file or URL. If authentication fails, run `gh auth login` or fix SSH.

## Writing rules

- No em-dashes in any file.
- Follow the honesty rules in `README.md`.
- Every number in a paper draft must come from a results CSV.
- Log generative AI use in `AI_USE_LOG.md`.
- Spec or protocol changes after the Day 2 freeze go in the Deviations section of `docs/protocol.md` with date and reason.
