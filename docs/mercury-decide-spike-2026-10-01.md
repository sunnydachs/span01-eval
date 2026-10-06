# mercury-decide vs span-01 spike — 2026-10-01

同じ「System One(型付き意思決定)」カテゴリの2モデルを、span01-eval の23ケース境界スイートで
同条件(production 指示文 v4、閾値0.5)で撃ち合わせたスパイク。API はどちらも OpenRouter 経由で
同じ `/alpha/decisions` エンドポイント(要 OPENROUTER_API_KEY)。記事・リポジトリ公開時は
プロバイダ名と free 枠には触れない(span-01 記事と同じ方針)。

## 結果(23ケース, lenient ラベル, 閾値0.5)

| model | TP | FP | FN | P | R | F1 | latency avg | neg_max | pos_min | miss |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mercury-decide:free | 7 | 0 | 1 | 1.00 | 0.88 | 0.93 | 0.45s | 0.026 | 0.002 | pos_long_eng |
| span-01-lite:free | 7 | 0 | 1 | 1.00 | 0.88 | 0.93 | 0.75s | 0.362 | 0.243 | pos_noun |

- 同点だが**取りこぼしが違う**。mercury は純粋な英語挨拶文(Hello everyone, welcome back...)を、
  span-01 は compartments という単語を見落とした。両方とも固定再現(温度非依存の決定的挙動)。
- 確率の極性がまったく違う:
  - mercury: 0.0001〜0.9997(極端に張り付く、擬似的な2値分類器のような分布)
  - span-01: 0.025〜0.955(幅を持つ、実質的な連続確率)
- 閾値スイープで挙動差:
  - mercury: 0.15〜0.85 全域で F1 0.93(閾値にほぼ無頓着、ただし neg_max 0.026 との間に谷が薄い)
  - span-01: 0.15で F1 0.89 まで落ちる(OK/コード断片が回収される)、0.85で 0.67 に急落
- **ORアンサンブル(どちらか一方が0.5以上なら陽性)で F1 1.00**。取りこぼしが互いに補完される。

## mercury-decide の3型スキーマ(実測)

- noul(boolean): {type:"noul", instructions:"..."} → answers.<key>.noul(0-1)
- choice: {type:"choice", instructions, criteria:{オプション:説明}} → choice / probabilities / confidence
  - criteria 内のキー名は何でもよい(options や choices でも応答にそのまま出る)
- score: {type:"score", instructions, criteria:["順序付きラベル",...]} → score(確率加重平均) / legend / probabilities / confidence
- 1リクエストで複数質問を並列に送れる。レスポンス形は Jev(/v1/systemone スキーマ)と同一。
- input_tokens 課金なし(早期アクセス中は cost 0)、output_tokens も数トークンで実質ゼロ。
- 速度: 実測平均 0.45s/決定(span-01-lite は 0.75s)

## 差別化の核(記事の問い)

1. **ルールの与え方**: span-01 は prose で行動を定義(promptがルール)。mercury は criteria で
   構造化。指示文の言い回し依存は span-01 が主犯だった(vague 0.06 → full 0.81)が、
   mercury は vague でも 0.98 と堅かった(=構造化が prose 依存を減らす可能性を示す実測)。
2. **確率の極性**: mercury は極端に張り付く(ほぼ2値)、span-01 は幅を持つ(閾値チューニングが
   実質的に意味を持つ)。閾値スイープの谷の深さの違いとして記事にできる。
3. **取りこぼしの相補性**: 23ケースで miss が互い違い → ORアンサンブルで F1 1.00。
   「どちらかが正しい」ではなく「2モデルのアンサンブルで完璧」が新しい切り口。
4. **速度**: mercury 0.45s vs span-01 0.75s(平均、1リクエスト1決定)

## 制限(記事の honest limitations に使う)

- 23ケース・各1回(再試行で決定的であることは確認済み)
- 指示文は span01-eval の v4 を使い回し(mercury 用に最適化していない)
- ラベルは自分の判定(lenient ベース)
- 無料は早期アクセス中のみで、料金・レート制限は変わる可能性

## 多角的再評価(2026-10-01 追記、レートリミット429到達後に保存データで実施)

1. **確率の量子化なし**: 両モデルとも23ケースで一意値23。mercury=15桁浮動小数点(連続的),
   span-01=8桁固定小数点(粗め)。「同じ値の繰り返し=離散的決定」ではない。
2. **FLAG一致21/23**: 片方だけFLAGしたのは2件(pos_noun, pos_long_eng)で、これが OR ensemble の
   補完性(=アンサンブルでF1 1.00)を支える。ただしMcNemar検定(b=2,c=0)では p=0.48、
   「mercuryのほうが優れている」とは統計的に言えない(n=23の解像度不足)。
3. **結論の堅牢性**: 両モデルとも miss が1件ずつだが内容が違う→「F1同点0.93」は堅い。
   「取りこぼしが互い違い」は堅い。「確率の極性が違う」は堅い(0.0001〜0.9997 vs 0.025〜0.955)。
   「mercuryがprose依存に強い」は V4B での修正を見たが、これは指示文添加の効果であって
   アーキテクチャの差とは言えない(vagueでの値を比較していない点、要再検証)。
4. **correlation r=0.761 / Spearman rho=0.582**: 同一モデルではない(同一なら r≈1.0)が、
   同じ分布から独立に生成されたわけでもない=どちらも同じ概念空間を見ている。
5. **コスト構造の違い**: ``inception/mercury-decide:free`` は cost=0 & output_tokens=3(確率のみ生成)
   、``respan/span-01-lite:free`` も cost=0 & output_tokens=1-2。Jev(有料)は input/output別課金、
   無料2モデルが Jev の商業モデルと同じスキーマ(/v1/systemone)で使える=記事の価値。
6. **latency**: mercury 0.45s vs span-01 0.75s(平均)。mercuryが速いが、n=23・単一コネクション
   なので有意な速度差とは言い切れない。ただし diffuser系の設計(並列トークン精錬)を考えると
   構造的に速いはず。

## prose依存検証(2026-10-02 追記、無料枠回復後に cron 実行、APIエラー0件)

23ケース × 2モデル × 2指示文(vague=v1_current / v4_full=production)= 92 calls。

| model | variant | TP | FP | FN | F1 |
| --- | --- | --- | --- | --- | --- |
| mercury-decide | vague | 6 | 4 | 2 | 0.67 |
| mercury-decide | v4_full | 6 | 1 | 2 | 0.80 |
| span-01-lite | vague | 5 | 2 | 3 | 0.67 |
| span-01-lite | v4_full | 7 | 0 | 1 | **0.93** |

**10/1の仮説が逆転: prose依存が強いのは mercury-decide の方だった。**

- 判定反転(vague→v4): mercury **9/23件** vs span-01 4/23件
- mercury は vague で正例・不例とも過剰FLAG(brand_multi 0.73, latin_name_sp 0.97, number_unit 0.97, acronym 0.82 を誤FLAG)。v4 でFPは4→1に減るが、代わりに pos_long_eng(0.95→0.00)と org_english_role_noun(0.97→0.00)を落とす=指示文の列挙が「包含リスト」として解釈され、列挙外の正例が除外された可能性
- span-01 は反転4件すべてが改善方向(neg_code 0.57→0.15, neg_ok 0.73→0.24 を正しく陰性化)。**「書けば書くほど良くなる」は span-01 で再確認、mercury では指示文の列挙が両刃**
- **時系列安定性(10/1 vs 10/2, 同一入力・同一v4指示)**: span-01 は0件反転(完全に再現)。mercury は2件反転(neg_katakana3 0.018→0.915, org_english_role_noun 0.947→0.004)=**同一指示でも日によって判定が変わる非決定性あり**。10/1に「決定的」と書いたのは再試行3回以内の話で、別日の再実行では変わった。訂正する

## 訂正と実務上の結論

1. 「mercury は vague でも堅い」は**誤り**。10/1の単発測定(0.98)は pos_adjacent という1ケースの観察で、スイート全体では vague F1 0.67
2. 言語ゲートの本番運用(別リポジトリの動画パイプライン)は **span-01-lite + v4_full 単体で F1 0.93** のままが最良。mercury への置き換え理由は現状ない
3. mercury の残る価値は OR アンサンブルの第2意見(F1 1.00 を支える相補的 miss)と、choice/score 型(言語ゲートは noul 相当なので未検証)
4. 決定的(diffusionの固定出力?)は同一日内の再試行限定的。クロスデイでは2/23反転→「確率は安定だが完全な決定性ではない」と訂正

## spike 記録

- 結果JSON: results/spike_mercury_vs_span.json(10/1) + results/prose_dependence.json(10/2)
- 23ケース: scripts/run_matrix.py の CASES を再利用
- 指示文: scripts/run_gate.py の v4(production)、v1_current(vague)
- 10/2 の sweep はスケジュール実行(完走後に結果を保存)


## 原記事(span-01)の10/3再実行検証(2026-10-03 追記)

span01-eval の全パイプライン(167→168コール)を10/3に再実行し、
9/27記事の数値との一致を検証した。mercury-decide 続編を書く前に、
第1弾記事の数値が「その日のモデル都合」でないことを確定させるため。

- 合成23件 gate v4: TP7 FP0 FN1 F1=0.933 — **完全一致**
- 汎用チャット: TP8 FP0 FN0 F1=1.000 — **完全一致**
- regex: F1=0.522(プロジェクトパターン)/ 0.615(latin_any) — **完全一致**
- 実データ: コーパスが211→245件に増えたため陽性22→23件。旧22陽性は全て再サンプルに
  含まれ、判定反転0件・確率差≤0.008で実質同一(検知21/22のまま)
- 閾値スイープ: 0.15/0.5は完全一致、0.7/0.85は±1件分ブレ(F1 0.902/0.809)
- 判定反転(クロスデイ): span-01-lite で **0件** — 10/1-10/2 の mercury-decide が
  2/23反転したのと対照的。続編記事の「決定性の非対称性」の土台データ
- 呼び出し数: 記事の「176」は導出記録なし。正値は167(9/27 rerun)。
  記事・README を167に修正済み
