# Working agreement for this repository

Short rules for anyone — human or agent — publishing numbers from this repository.

## What this repository is

An offline evaluation: scripts under `scripts/` produce the JSON artifacts under
`results/` and the write-ups under `reports/`. There is no library and no test
suite — the public artifacts are the product.

## Ground rules

- **Every published figure must be recomputable offline.** No credentials, no
  network. `scripts/check_artifacts.py` is the gate: it compiles the scripts,
  parses every `results/**/*.json`, and runs the documented command.
- **An artifact and the code that made it must agree.** `check_artifacts.py`
  re-runs `run_baselines.py --json` and diffs the result against the committed
  file. When it reports DRIFT, reconcile it deliberately — either regenerate the
  artifact or record why the committed one differs. Do not leave it silent.
- **No fabricated or hand-edited numbers.** A figure in a report must come from a
  committed artifact, and that artifact from a script in this repository.
- **No secrets in Git.** Nothing here may call a paid endpoint by default; a script
  that needs a key reads it from the environment and says so in the README.
- **No absolute paths** in code, docs or artifacts.
- **Do not bypass the secret scan.** `git commit --no-verify` is never a fix for a
  gitleaks hit.
- **The README is a promise.** Every documented command must work on a fresh clone.

## Checks that must pass

```
python3 scripts/check_artifacts.py
```
