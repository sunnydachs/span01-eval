# Contributing to span01-eval

Thanks for your interest. This is a small evaluation repo, so the rules are short.

## Dev setup

```bash
git clone https://github.com/sunnydachs/span01-eval && cd span01-eval
python3 -m venv .venv && source .venv/bin/activate   # stdlib only; venv is optional
export SPAN01_API_KEY=sk-or-v1-...                   # or put it in a repo-root .env
```

## Ground rules

- **Determinism first.** The regex baselines and label logic must stay pure functions of their inputs. No hidden state, no time-dependent behavior.
- **Never commit secrets.** `.env` is git-ignored — keep it that way. Keys are read via `scripts/envconfig.py` only.
- **Never commit the real corpus.** `corpus/items.jsonl`, `results/trackA*.json`, and `results/rerun.log` are git-ignored because they contain third-party content. The anonymized subset (`results/public/`) is the shippable form.
- **Freeze labels before measuring.** Ground truth lives in `LABELS.md`. If you change a label, do it *before* the run, record the change there, and re-run the affected tracks — do not edit artifacts after a run (see `AUDIT.md` for why).
- **Numbers must trace to artifacts.** Every number in `reports/` and the READMEs should be recomputable from `results/*.json` by `scripts/analyze.py`, `scripts/calibrate.py`, or `scripts/run_baselines.py`. If you add a number, add the artifact and the command.

## Verify before opening a PR

```bash
bash scripts/rerun_all.sh          # end-to-end (needs SPAN01_CORPUS_SRC + API key)
python scripts/run_baselines.py   # offline regex baselines + threshold sweep
```

If your change touches scripts, run the relevant track and confirm the report tables still reproduce.

## Commit style

Short imperative subject, body explaining *why* (see `git log` for examples). Japanese or English is fine.

## Reporting problems

Open an issue with the input text, the command you ran, and the output you got. If it's a numbers question, include the JSON artifact path you're disputing.
