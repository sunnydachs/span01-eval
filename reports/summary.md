# summary — 専用 decision モデルを言語ゲートで評価 (2026-09-27)

対象: `respan/span-01-lite`。用途: 日本語ナレーションへの英語混入ゲート。
（有料 `span-01` / `typesafe/jev-*` は手元キーが 403 のため未測定）

## 方法
- 実コーパス: 日本語ナレーション211件（うちラテン文字含有22件、クリーン189件から30件サンプル）
- 合成境界スイート: 23件 × 指示文4種
- 比較: 正規表現 / gate(v1〜v4) / 汎用チャットモデル
- 全コール `usage.cost=$0`、429なし（3.2s pacing）
- 正解基準は `LABELS.md`。**strict は循環的なので結論に使わない。**

## 結論
1. **境界ケースではモデルが正規表現に大差で勝つ。** 合成23件で正規表現 F1 0.52、
   gate v4 0.93、汎用チャット 1.00。正規表現の敗因は誤検知（ブランド/URL/人名/略語）。
2. **実データでは正規表現が 22/22、gate 21/22。** ただしこの物差しは循環的
   （クリーン群＝「ラテン文字を含まない」の定義そのもの）なので、
   **正規表現が優れている証拠にはならない**。
3. **専用モデルの必然性は薄い。** 汎用チャットモデルが同等以上。指示文の言葉遣いで
   成績は F1 0.67〜0.93 と振れる（v1 は `このmethodはやばい` を 0.06 で見逃す）。
4. **指示は完全には効かない。** 「全てのラテン文字」と指示してもブランド/URLは除外され続ける。
   固有名詞の除外は例示駆動で、指示文に載っていない名前は除外されない。
5. **閾値**は 0.15〜0.85 の帯を推奨していたが、実測では 0.15 が最悪（誤検知7件）、
   0.85 も悪い（再現率 0.769）。このデータでは 0.4〜0.7 が同等以上（`reports/trackB.md`）。
6. **較正**は両端（〜0.15 と 0.85〜）で良好。中間帯0.3–0.7は合計3件しかなく、判断できない。

## 実務レシピ
- **正規表現を第一段に置く**（決定的・0コスト・このコーパスの混入型は全部拾える）。
- **モデルは第二段**として、境界ケース（ブランド/URL/人名/略語）の誤検知を減らしたいときだけ足す。
- 指示文は1箇所に定数化し、変更時は回帰テスト。除外リストは測定前に凍結して版管理（`LABELS.md`）。
- 閾値は0.5前後でよい（0.15/0.85 の帯はこのデータでは悪化する）。
- 汎用チャットモデルでも代替可能（要リトライ・レイテンシ裾に注意）。

## 成果物
`scripts/`（run_gate, run_matrix, tune_instruction, run_llm_baseline, analyze, calibrate,
run_baselines, sanitize_results）/ `reports/`（trackA〜trackD, 本ファイル）/
`candidates/v4_production.txt` / `LABELS.md` / `AUDIT.md`

## 既知の弱点（外部レビュー由来。詳細 `AUDIT.md`）
- strict 比較は循環的。合成23件はチューニングにも使用（hold-out なし）。
- 正解ラベルを実行後に1件変更した（gate v4 の F1 は 0.86〜0.93 の幅を持つ）。
- 実コーパス非公開のため Track A は第三者に再現できない。
- モデル版のピン留めなし（解決済みIDは `respan/span-01-lite-20260925`）。
- 実コーパスの lenient 表は `--exempt <キャラクター名>` が必須（スクリプトの既定は指示文の例名）。

## 再現
```
export SPAN01_CORPUS_SRC=/path/to/root
python corpus/build_corpus.py
cd scripts
python run_matrix.py
python tune_instruction.py --instructions @../candidates/v4_production.txt --out ../results/tune_v4.json
python ../scripts/run_gate.py --sample-neg 30 --instructions "$(cat ../candidates/v4_production.txt)" \
    --out ../results/trackA_v4.json     # 実コーパスの lenient 表には --exempt <name> も指定
python run_llm_baseline.py --out ../results/trackD_llm.json
cd ..
python scripts/analyze.py --results results/trackA_v4.json --exempt <name>
python scripts/calibrate.py --synth results/tune_v4.json --real results/trackA_v4.json --exempt <name>
python scripts/run_baselines.py --json
```
（`scripts/rerun_all.sh` は `SPAN01_EXEMPT` を渡すと同じ流れを一括実行する）
