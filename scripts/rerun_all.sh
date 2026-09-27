#!/usr/bin/env bash
# 汎用プレースホルダ(Kuro)への差し替え後に全測定をやり直す。
set -euo pipefail
cd "$(dirname "$0")"
PY="${PY:-python3}"
: "${SPAN01_CORPUS_SRC:?set SPAN01_CORPUS_SRC to the corpus root containing */*/story.json}"
echo "=== build corpus ==="
$PY ../corpus/build_corpus.py
echo "=== track C matrix (v1/v2/v3) ==="
$PY run_matrix.py
echo "=== tune v4 ==="
$PY tune_instruction.py --instructions "@../candidates/v4_production.txt" --out ../results/tune_v4.json
echo "=== track A real (v4) ==="
$PY run_gate.py --sample-neg 30 --instructions "$(cat ../candidates/v4_production.txt)" --out ../results/trackA_v4.json
echo "=== track D llm baseline ==="
$PY run_llm_baseline.py --out ../results/trackD_llm.json
echo "=== analysis ==="
$PY analyze.py --results ../results/trackA_v4.json --exempt "Kuro"
$PY calibrate.py --synth ../results/tune_v4.json --real ../results/trackA_v4.json --exempt "Kuro"
echo "=== DONE ==="
