# span01-eval — 汎用LLM vs 専用 decision モデルを「言語ゲート」で比較する

`respan/span-01(-lite)(:free)` / `typesafe/jev-*`（OpenRouter の Decisions API）を
「出力を1言語に固定する（日本語ナレーションに英語を混ぜない）」用途で評価した記録。

結論を先に: **この用途では専用 decision モデルの必然性は薄い**。
- 実データでは単純な regex で 22/22 検知、モデルは 21/22。
- 合成境界スイートでは、無料の汎用LLM（nemotron-3-super）が lenient F1 1.00 で
  専用モデル（0.93）に並ぶか上回る。
- 専用モデルの価値は「指示文で行動を定義できる」「誤検知を出しにくい」点に限られる。

## 対象（すべて無料・手元キー、`usage.cost=0`）
| 手法 | 呼び出し | 特徴 |
|---|---|---|
| regex | `regex_mixed_language_hit`（直隣接＋空白区切り） | 決定的・0コスト・ゼロレイテンシ |
| gate | `respan/span-01-lite:free`（noul） | 人が自然文で行動を定義 → 確率 |
| llm | `nvidia/nemotron-3-super-120b-a12b:free`（chat, temp0） | YES/NO 分類 |

## トラック
- **A** 実データ（日本語ナレーション約200件）での with/without
- **B** 較正（確率 → 実測正解率）
- **C** 合成境界23件 × 指示文3種（言い回し感度）
- **D** 3手法の同一条件比較（精度・レイテンシ・決定性）

## 主な結果（詳細は `reports/`）

合成境界23件（lenient = ブランド/固有名詞/URL/略語/コード片は陰性扱い）:
| 手法 | P | R | F1 |
|---|---|---|---|
| regex相当（プロジェクト内の段） | 0.82 | 1.00 | 0.90 |
| gate v1（曖昧な指示文） | 0.71 | 0.62 | 0.67 |
| gate v3（除外を明示） | 0.78 | 0.88 | 0.82 |
| **gate v4（単一語も数える/除外を明示）** | **1.00** | **0.88** | **0.93** |
| **無料LLM (nemotron-3-super)** | **1.00** | **1.00** | **1.00** |

- **指示文の言葉遣いが結果を支配**。v1 は `このmethodはやばい` を 0.06 で見逃す。
- 「全てのラテン文字を検知せよ」と指示しても守られない（ブランド/URLは除外され続ける）。
- 無料LLMはレイテンシの裾が重く（max 3.9–8.9s）、稀に空レスポンスを返す（リトライ必須）。

## 使い方（実データは同梱していません）
```bash
export SPAN01_CORPUS_SRC=/path/to/root   # */*/story.json ({"scenes":[{"narration":...}]}) を持つルート
python corpus/build_corpus.py
bash scripts/rerun_all.sh
```
`OPENROUTER_API_KEY` は環境変数か `~/.hermes/.env` から読みます（キーは出力しません）。

## データ扱い
- 実コーパスの原文・グループ名はリポジトリに含めません（`.gitignore`）。
  公開用には `scripts/sanitize_results.py` で id を匿名化し原文を削除します。
- 合成ケース（`scripts/run_matrix.py` の `CASES`）は本リポジトリの著作物です。

## ディレクトリ
`corpus/` 抽出スクリプト / `scripts/` 実行 / `results/` 生データ（実データ系は除外） / `reports/` まとめ / `candidates/` 指示文
