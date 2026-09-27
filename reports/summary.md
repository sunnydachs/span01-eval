# summary — 汎用LLM vs 専用 decision モデル (2026-09-27)

対象: OpenRouter Decisions API の `respan/span-01-lite:free`（無料・行動スコアラー）。
用途: 「出力を1言語に固定する」＝日本語ナレーションへの英語混入ゲート。
（有料 `span-01` / `typesafe/jev-*` は手元キーが 403 のため未測定）

## 方法
- 実コーパス: 日本語ナレーション約200件（うちラテン語含有22件、クリーン30件をサンプル）
- 合成境界スイート: 23件 × 指示文3種
- 比較: regex / gate(v1〜v4) / 無料LLM
- 全コール `usage.cost=$0`、429なし（3.2s pacing）

## 結論
1. **専用 decision モデルの必然性は薄い。** 合成23件(lenient)では無料汎用LLMが F1=1.00、
   gate v4 が 0.93。実データでは regex 22/22、gate 21/22。
2. **ゲートの弱点は指示文で決まる。** 曖昧な文言(v1)は単一英単語を落とす(F1 0.67)。
   単一語も数える/除外を明示した v4 で F1 0.93 まで改善。
3. **指示は完全には効かない。** 「全てのラテン文字」と指示してもブランド/URL/固有名詞は除外され続ける。
   固有名詞の除外は**例示駆動**で、指示文に載っていない名前は除外されない（脆い）。
4. **較正**は両端で良好、中間帯0.3–0.7は崩れる。v4 では陰性の上限が0.331まで下がり分離は改善。
   それでも閾値0.5は安全とは言い切れない（陽性の下限 0.025 が残る）。
5. **決定性**は同一入力で bit 一致。ただし同種の特徴でも文脈が変われば確率は大きく振れる。

## 実務レシピ
- regex を第一段に残す（決定的・0コスト・実データで最強）。
- モデルを使うなら「複数語の英語」の追加シグナルとして。指示文は1箇所に定数化し、変更時は回帰テスト。
- 閾値は0.5固定でなく、0.15/0.85 などのヒステリシス帯を使う。
- 無料LLMで代替可能（要リトライ・レイテンシ裾に注意）。

## 成果物
`scripts/`（run_gate, run_matrix, tune_instruction, run_llm_baseline, analyze, calibrate, sanitize_results）
`reports/`（trackA〜trackD, 本ファイル） `candidates/v4_production.txt`

## 再現
```
export SPAN01_CORPUS_SRC=/path/to/root
python corpus/build_corpus.py
python scripts/run_matrix.py
python scripts/tune_instruction.py --instructions @candidates/v4_production.txt --out results/tune_v4.json
python scripts/run_gate.py --sample-neg 30 --instructions "$(cat candidates/v4_production.txt)" --out results/trackA_v4.json
python scripts/run_llm_baseline.py --out results/trackD_llm.json
python scripts/analyze.py --results results/trackA_v4.json
python scripts/calibrate.py --synth results/tune_v4.json --real results/trackA_v4.json
```
