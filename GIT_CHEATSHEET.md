# Git cheatsheet

Repo: https://github.com/muhammadmapkar/chip-tess

Names used below: `upstream` = the shared repo (muhammadmapkar/chip-tess). `origin` = your fork. Replace `<you>` with your GitHub username and `<task>` with a short task name.

## 1. Fork and clone

On GitHub, click Fork on the repo page and UNCHECK "Copy the main branch only". Or with the GitHub CLI (all branches are copied unless you pass `--default-branch-only`):

```
gh repo fork muhammadmapkar/chip-tess --clone=false
git clone https://github.com/<you>/chip-tess.git
cd chip-tess
```

## 2. Add the upstream remote

```
git remote add upstream https://github.com/muhammadmapkar/chip-tess
git remote -v
```

## 3. Fetch a branch from upstream

```
git fetch upstream
git branch -r
git checkout -b track1/start upstream/setup/scaffold
```

## 4. Sync

After `setup/scaffold` or later work is merged to upstream `main`:

```
git fetch upstream
git checkout track1/<task>
git merge upstream/main
```

Do not rebase branches that are already pushed.

## 5. Create branches

Peer:

```
git checkout -b track1/<task>
```

Muhammad:

```
git checkout -b track2/<task>
```

## 6. Commit and push to your fork

```
git add track1_synthetic/
git status
git commit -m "Short clear message"
git push -u origin track1/<task>
```

Never `git push --force`. Never push to `main`. Never commit `data/`, `*.npz`, `*.pt`, `*.ckpt`, `.venv/`, or files over 5 MB.

## 7. Open a pull request

On GitHub: open your fork, click "Compare and pull request", base repository = muhammadmapkar/chip-tess, base = `main`, compare = your branch. Fill in the template.

With the GitHub CLI:

```
gh pr create --repo muhammadmapkar/chip-tess --base main --head <you>:track1/<task> --title "Track 1: <task>" --body-file .github/pull_request_template.md
```

Merge with "Create a merge commit". Never squash.

## 8. Authentication problems

If push fails with an authentication error, run `gh auth login` or fix your SSH key. Do not paste tokens into files, URLs, or chats.
