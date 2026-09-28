# span01-eval

**Evaluating a prompt-defined "decision model" (span-01-lite) as a language gate — against a plain regex and a generic chat model — with every number recomputed from saved JSON artifacts.**

English | [日本語](README.ja.md)

Can a model that scores "does this text match a behavior described in plain language" replace a regex for keeping generated Japanese narration pure Japanese? This repo measures it honestly: a 23-case boundary suite, a real narration corpus, instruction-wording sweeps, calibration, and a threshold sweep — plus `AUDIT.md`, the record of having five independent models re-review every number before publishing.

## The task

Detect English words mixed into Japanese narration (the kind a TTS voice reads aloud awkwardly). Three detectors are compared on identical inputs:

| method | what it is |
|---|---|
| regex | adjacency + whitespace patterns against Latin tokens |
| gate | `respan/span-01-lite` — a decision model: describe the behavior in prose, get a probability |
| chat | a generic chat model answering YES/NO at temperature 0 |

## Measured results

Boundary suite (23 hand-built edge cases; lenient labels = brands/URLs/proper names/code/acronyms are acceptable):

| method | TP | FP | FN | P | R | F1 |
|---|---|---|---|---|---|---|
| regex (project patterns) | 6 | 9 | 2 | 0.40 | 0.75 | 0.52 |
| regex (`[A-Za-z]{2,}`) | 8 | 10 | 0 | 0.44 | 1.00 | 0.62 |
| gate v1 (vague instruction) | 5 | 2 | 3 | 0.71 | 0.62 | 0.67 |
| gate v3 (exclusions spelled out) | 7 | 2 | 1 | 0.78 | 0.88 | 0.82 |
| gate v4 (single words counted, exclusions listed) | 7 | 0 | 1 | 1.00 | 0.88 | 0.93 |
| generic chat model | 8 | 0 | 0 | 1.00 | 1.00 | 1.00 |

Real narration corpus (211 items, 22 with Latin tokens, 30-item clean control): regex 22/22, gate 21/22 — **but that ground truth is circular** (the clean set is defined as "contains no Latin"), so it is not evidence that regex beats the model. Details: `reports/trackA.md`.

Key findings:

- **On boundary cases the models beat the regex decisively** — the regex false-positives on every brand, URL, Latin character name, `OK`, `AI`, `DX`.
- **Instruction wording dominates the gate's accuracy** (F1 0.67 → 0.93); the same single English word flips from 0.06 to 0.81 depending on phrasing.
- **Instructions are not fully obeyed**: "detect ALL Latin letters" still excludes brands/URLs.
- **Threshold sweep** (75 items): 0.15 is the worst operating point (7 FPs), 0.7 the best; the earlier 0.15/0.85 hysteresis recommendation was withdrawn. See `reports/trackB.md`.

## Honest limitations

- n=23, single runs, no confidence intervals; the 0.93-vs-1.00 gap is one case.
- The gate instruction was tuned on the same 23 cases (no hold-out).
- Labels come from a single annotator; one label was corrected after the run (recorded in `LABELS.md`).
- The real corpus is private, so Track A needs your own corpus to reproduce.
- `AUDIT.md` documents the five-model external review that caught the original numbers' defects, and what was fixed.

## Setup

Python 3.11+ (stdlib only — no dependencies).

```bash
# API key: environment variable, or a repo-root .env (git-ignored)
export SPAN01_API_KEY=sk-or-v1-...          # or:
echo 'SPAN01_API_KEY=sk-or-v1-...' > .env
```

The scripts read the key from `SPAN01_API_KEY` or `OPENROUTER_API_KEY` — environment first, then a repo-root `.env` (`scripts/envconfig.py`). The key is never written to outputs.

## Reproduce

The real narration corpus is private (third-party content), so Track A needs your own corpus. Point `SPAN01_CORPUS_SRC` at a tree containing `*/*/story.json` files (`{"scenes": [{"narration": ...}]}`):

```bash
export SPAN01_CORPUS_SRC=/path/to/corpus-root   # for Track A
export SPAN01_EXEMPT=CharName                  # lenient-label exempt tokens, comma-separated

python corpus/build_corpus.py                  # -> corpus/items.jsonl
bash scripts/rerun_all.sh                      # all tracks, end to end
python scripts/run_baselines.py --json         # regex baselines + threshold sweep (offline)
```

Individual tracks (one report each in `reports/`):

```bash
cd scripts
python run_matrix.py                                                       # Track C: 23 cases x 3 instructions
python tune_instruction.py --instructions @../candidates/v4_production.txt \
    --out ../results/tune_v4.json                                            # v4 on the same cases
python run_gate.py --sample-neg 30 \
    --instructions "$(cat ../candidates/v4_production.txt)" \
    --out ../results/trackA_v4.json                                          # Track A: real corpus
python run_llm_baseline.py --out ../results/trackD_llm.json                  # Track D: chat baseline
python analyze.py --results ../results/trackA_v4.json                       # Track A tables
python calibrate.py --synth ../results/tune_v4.json \
    --real ../results/trackA_v4.json                                         # Track B: calibration
```

`analyze.py` / `calibrate.py` pick up `SPAN01_EXEMPT` from the environment; pass `--exempt` explicitly to override.

Every report number traces to a JSON in `results/`. `results/public/trackA_anon.json` is the anonymized real-data subset (ids anonymized, narration stripped via `scripts/sanitize_results.py`).

## Data handling

- The real corpus's original text and group names are not committed (`.gitignore`); the anonymized subset ships in `results/public/`.
- The synthetic cases (`CASES` in `scripts/run_matrix.py`) are original to this repo.

## Repository layout

| path | contents |
|---|---|
| `corpus/` | `build_corpus.py` — extract narration items from `story.json` trees |
| `scripts/` | runners (`run_gate`, `run_matrix`, `tune_instruction`, `run_llm_baseline`, `run_baselines`) + analysis (`analyze`, `calibrate`, `sanitize_results`, `envconfig`) |
| `results/` | raw JSON artifacts per track (real-corpus files git-ignored) |
| `reports/` | one markdown report per track + `summary.md` |
| `candidates/` | instruction texts (v4 = production) |
| `LABELS.md` | ground-truth definitions, exemption-list versioning, the post-run label change |
| `AUDIT.md` | the five-model external review: findings → verification → fixes |

## License

[MIT](LICENSE)
