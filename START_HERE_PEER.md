# Start here (Track 1, peer)

Follow these steps in order. Repo URL: https://github.com/muhammadmapkar/chip-tess

1. Accept the repo invite, or fork the repo. When forking, UNCHECK "Copy the main branch only".
2. Clone your fork.
3. Run: `git remote add upstream https://github.com/muhammadmapkar/chip-tess`
4. Run: `git fetch upstream`
5. Run: `git checkout -b track1/start upstream/setup/scaffold`
6. Read `README.md`, `docs/SPEC.md`, `docs/protocol.md`, and `track1_synthetic/README.md` and `track1_synthetic/TASKS.md`.
7. Open `track1_synthetic/PEER_PROMPT.md`. Paste it into your own Claude Code.
8. Work only inside `track1_synthetic/`. Do not read or import `track2_real/`.
9. Commit often. Push with: `git push -u origin track1/start`
10. Open a pull request from your fork's branch to upstream `main`. Muhammad reviews it.
11. After `setup/scaffold` is merged to `main`, sync with: `git fetch upstream`, then `git merge upstream/main`.

Notes:

- If you were invited as a collaborator instead of forking, `origin` is already the shared repo. Skip step 3 and use `origin` in place of `upstream`. Push only branches named `track1/<task>`.
- Never push to `main`. Never force push.
- Exact commands for everything else are in `GIT_CHEATSHEET.md`.
