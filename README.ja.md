# span01-eval

**プロンプトで行動を定義する「判定モデル」(span-01-lite) を言語ゲートとして評価する — 正規表現と汎用チャットモデルと比較し、すべての数値を保存済みJSONから再計算可能にした検証記録。**

[English](README.md) | 日本語

「この文章は自然文で記述した行動に当てはまるか」を確率で返すモデルは、生成した日本語ナレーションを日本語のまま保つ正規表現の代替になるか。このリポジトリで正直に測ります: 境界ケース23件のスイート、実ナレーションコーパス、指示文の言い回しスイープ、較正、閾値スイープ — さらに公開前に5つの独立したモデルで全数値を再レビューさせた記録が `AUDIT.md` です。

## タスク

日本語ナレーションに混ざった英語を検出する（TTSが読み上げると不自然になる類のもの）。同一入力で3つの検出器を比較します:

| 手法 | 内容 |
|---|---|
| 正規表現 | ラテン文字トークンに対する隣接＋空白区切りのパターン |
| gate | `respan/span-01-lite` — 判定モデル: 自然文で行動を記述すると確率が返る |
| chat | 汎用チャットモデルが temperature 0 で YES/NO を返す |

## 測定結果

境界スイート（自作の厳密ケース23件。lenient基準 = ブランド/URL/固有名詞/コード/略語は許容）:

| 手法 | TP | FP | FN | P | R | F1 |
|---|---|---|---|---|---|---|
| 正規表現（プロジェクトのパターン） | 6 | 9 | 2 | 0.40 | 0.75 | 0.52 |
| 正規表現（`[A-Za-z]{2,}`） | 8 | 10 | 0 | 0.44 | 1.00 | 0.62 |
| gate v1（曖昧な指示文） | 5 | 2 | 3 | 0.71 | 0.62 | 0.67 |
| gate v3（除外を明示） | 7 | 2 | 1 | 0.78 | 0.88 | 0.82 |
| gate v4（単一語も数える・除外を列挙） | 7 | 0 | 1 | 1.00 | 0.88 | 0.93 |
| 汎用チャットモデル | 8 | 0 | 0 | 1.00 | 1.00 | 1.00 |

実ナレーションコーパス（211件、うちラテン文字含有22件、クリーン30件の対照群）: 正規表現 22/22、gate 21/22 — **ただしこの正解は循環的です**（クリーン群は「ラテン文字を含まない」と定義して抽出）。正規表現がモデルに勝った証拠にはなりません。詳細は `reports/trackA.md`。

主な知見:

- **境界ケースではモデルが正規表現に大差で勝つ** — 正規表現はブランド、URL、ラテン文字の人名、`OK`、`AI`、`DX`をすべて誤検知する。
- **指示文の言葉遣いがgateの精度を支配する**（F1 0.67 → 0.93）。同じ単一英単語が言い回し次第で 0.06 ↔ 0.81 と反転する。
- **指示は完全には守られない**: 「全てのラテン文字を検知せよ」と書いてもブランド/URLは除外され続ける。
- **閾値スイープ**（75件）: 0.15 が最悪（誤検知7件）、0.7 が最良。以前推奨していた 0.15/0.85 のヒステリシス帯は撤回した。`reports/trackB.md` 参照。

## 正直な限界

- n=23・各1回・信頼区間なし。0.93 と 1.00 の差は1ケース。
- gateの指示文は同じ23件で選んだ（hold-out なし）。
- ラベルは単一作業者。1件は実行後に修正した（`LABELS.md` に記録）。
- 実コーパスは非公開のため、その Track A 数値そのものは第三者が再測定できません。パイプライン自体は同梱のサロゲートコーパス（下記）で最後まで再現可能で、実データの匿名化サブセットは `results/public/trackA_anon.json` に同梱しています。
- `AUDIT.md` に、元の数値の欠陥を見つけた5モデル外部レビューと修正内容を記録している。

## セットアップ

Python 3.11以上（標準ライブラリのみ — 依存なし）。

`.env` にLLM認証情報を置きます（OpenAI互換のエンドポイントなら何でも）:

```bash
LLM_API_KEY=sk-...
LLM_BASE_URL=https://your-openai-compatible-endpoint.example.com   # 任意。既定はOpenRouter
```

…または環境変数として export してください。`scripts/envconfig.py` は `LLM_API_KEY` と `LLM_BASE_URL` を「環境変数 → リポジトリ直下の `.env`（git対象外）」の順に読みます。`SPAN01_API_KEY` / `OPENROUTER_API_KEY` も後方互換として使えます。キーが出力に書かれることはありません。

## 再現

### 同梱のサロゲートコーパスで全パイプライン（非公開データ不要）

```bash
python corpus/make_public_corpus.py --out public_corpus    # 210件の決定的な合成ストーリーを生成
export SPAN01_CORPUS_SRC=public_corpus
export SPAN01_EXEMPT=Kuro                                 # lenient基準で許容するトークン（カンマ区切り）

bash scripts/rerun_all.sh                                  # 全トラックを一括実行
python scripts/run_baselines.py --json                     # 正規表現ベースライン＋閾値スイープ（オフライン）
```

サロゲートコーパスは実コーパスと同じ形状（210件、うちラテン文字含有22件、`*/*/story.json` 配置）で、決定的（seed 42）です。Track A を含むパイプライン全体を、誰でも最初から最後まで実行できます。

### 自分のコーパスで実行

`{"scenes": [{"narration": ...}]}` を含む `*/*/story.json` ツリーのルートを `SPAN01_CORPUS_SRC` に指定し、同じコマンドを実行します。

個別トラック（`reports/` に1ファイルずつ）:

```bash
cd scripts
python run_matrix.py                                                       # Track C: 23ケース × 指示文3種
python tune_instruction.py --instructions @../candidates/v4_production.txt \
    --out ../results/tune_v4.json                                            # 同じケースで v4
python run_gate.py --sample-neg 30 \
    --instructions "$(cat ../candidates/v4_production.txt)" \
    --out ../results/trackA_v4.json                                          # Track A: コーパス実行
python run_llm_baseline.py --out ../results/trackD_llm.json                  # Track D: chatベースライン
python analyze.py --results ../results/trackA_v4.json                       # Track A の表
python calibrate.py --synth ../results/tune_v4.json \
    --real ../results/trackA_v4.json                                         # Track B: 較正
```

`analyze.py` / `calibrate.py` は環境変数 `SPAN01_EXEMPT` を拾います。上書きする場合は `--exempt` を明示的に渡してください。

### 再現できるもの・できないもの

- **パイプライン・ハーネス・解析: 完全に再現可能** — 同梱のサロゲートコーパスなら非公開データなしで最後まで動きます。
- **`reports/` の実データの数値そのもの**: 実コーパスは第三者コンテンツのため非公開を維持します。同梱のアーティファクト（`results/public/trackA_anon.json`。id匿名化・本文除去は `scripts/sanitize_results.py`）により、公開済みの確率から Track A の各指標を再導出することは誰にでもできますが、元テキストでモデルを再実行することはこのリポジトリ外ではできません。
- レポートの数値はすべて `results/` のJSONに遡ります。

## データの扱い

- 実コーパスの原文とグループ名は絶対にコミットしない（`.gitignore`）。匿名化サブセットは `results/public/` に同梱。
- 合成ケース（`scripts/run_matrix.py` の `CASES`）とサロゲートコーパス（`corpus/make_public_corpus.py`）は本リポジトリの著作物。

## ディレクトリ

| パス | 内容 |
|---|---|
| `corpus/` | `build_corpus.py` — `story.json` ツリーから項目を抽出。`make_public_corpus.py` — 決定的なサロゲートコーパス生成器 |
| `scripts/` | 実行系（`run_gate`, `run_matrix`, `tune_instruction`, `run_llm_baseline`, `run_baselines`）＋解析系（`analyze`, `calibrate`, `sanitize_results`, `envconfig`） |
| `results/` | トラック別の生JSON（実コーパス系はgit対象外） |
| `reports/` | トラック別のレポート + `summary.md` |
| `candidates/` | 指示文（v4 = 本番） |
| `LABELS.md` | 正解基準の定義、除外リストの版管理、実行後のラベル変更 |
| `AUDIT.md` | 5モデル外部レビュー: 指摘 → 検証 → 修正 |

## ライセンス

[MIT](LICENSE)
