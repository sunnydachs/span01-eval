"""Track A を誰でも再現できるようにするための合成サロゲートコーパス生成器。

実コーパスは第三者コンテンツのため非公開（LABELS.md / README 参照）。そこで
同じ `*/*/story.json` 形式・同じ規模（210件、うち英字含有22件）の合成コーパスを
決定的に生成し、パイプライン全体を第三者が最後まで実行できるようにする。

  python corpus/make_public_corpus.py --out public_corpus
  SPAN01_CORPUS_SRC=public_corpus python corpus/build_corpus.py

注意: このコーパスは公開用の合成データであり、reports/ に載せた実測値は
このコーパス由来ではない。実データの Track A 数値は
results/public/trackA_anon.json（匿名化済み）からのみ再採点できる。
"""
import argparse
import json
import os
import random

# 純粋な日本語のナレーション文（ラテン文字を含まない）
CLEAN = [
    "静かな夜の町に、小さな灯りがともっていた。",
    "風が丘を渡り、草の波が月明かりに揺れた。",
    "少女は古い地図を広げ、指先で線をなぞった。",
    "時計台の針が、ゆっくりと真夜中を指した。",
    "路地裏の猫が、一夜に一度だけ鳴いた。",
    "桜の花びらが、川面に静かに落ちていった。",
    "旅人は丘の上で、街の灯りを眺めていた。",
    "雨上がりの路面に、星の鏡が映っていた。",
    "老婦人は真珠を掌に乗せ、長い物語を語り始めた。",
    "笛の音が谷に響き、鳥たちが一斉に飛び立った。",
    "小さな店の看板が、風に軋んで揺れた。",
    "少年は屋根の上で、流れ星を三つ数えた。",
    "霧の立ち込める橋の上を、誰かが渡っていった。",
    "機械仕掛けの鳥が、朝一番に歌をさえずった。",
    "灯台の光が、遠い船を静かに導いていた。",
    "木漏れ日の下で、子鹿が初めて立ち上がった。",
    "石段の奥から、湧き水の音が聞こえてきた。",
    "紙飛行機が風に乗って、塀の向こうへ消えた。",
    "夜の市場に、香辛料の匂いが満ちていた。",
    "雪解けの水が、谷の岩を何千年も削ってきた。",
    "影絵師が蝋燭を灯すと、壁に竜が現れた。",
    "砂時計の砂が落ちきる前に、門は閉ざされた。",
    "深い森の泉に、月がもう一つ浮かんでいた。",
    "帆船が朝霧を抜けて、港に静かに入ってきた。",
]

# 英字を含むナレーション文（実測で見つかった混入パターンを模した合成例）
# ブランド/URL/略語/人名等を含むものは lenient 基準では許容（LABELS.md 参照）
INJECTED = [
    "巨大な magnifying glassで、微小な足跡を観察した。",
    "その光が、missing pieceを呼び寄せた。",
    "このmethodはやばい。今日は最強の裏技を紹介するよ。",
    "それでは Let's go 次の町へ進もう。",
    "猫 keeper が真珠を老女に渡した。時が、再び前進した。",
    "このiPhoneの設定方法を紹介します。画面をタップしてください。",
    "詳細は https://example.com を確認してください。",
    "バージョン 2.1 に更新しました。設定ファイル config.yaml も新しくなっています。",
    "設定は `npm install` を実行してください。",
    "AIとDXの時代です。仕事のやり方が変わります。",
    "ぼくはKuro。静かな草原で、遠くの子守歌が聞こえる。",
    "Hello everyone, welcome back to my channel.",
    "彼は cloak をまとっていた。星屑が淡く輝いていた。",
    "隠された compartments を開けると、光る音符があった。",
    "YouTubeのチャンネル登録もお願いします。高評価もよろしく。",
    "この method は本当にやばい。早速やってみよう。",
    "散る桜 petals に星座を描き出す。",
    "妖怪が櫻の花びらを clockの文字に織り込んでいた。",
    "Kuroは bubble wand を振り、光を集めた。",
    "はい、OKです。このまま進めましょう。",
    "スマートフォンの battery が切れかけていた。",
    "次のステップに行こう。 This is amazing, right?",
]

GROUPS = [f"tales_{c}" for c in "abcdefghij"]  # 10グループ
RUNS_PER_GROUP = 21                            # 10 x 21 = 210件
INJECTED_COUNT = len(INJECTED)                 # 22件


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="public_corpus")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    os.makedirs(args.out, exist_ok=True)

    # どの(group, run)に混入を置くかを決定的に決める
    slots = [(g, r) for g in GROUPS for r in range(RUNS_PER_GROUP)]
    injected_slots = set(rng.sample(slots, INJECTED_COUNT))

    n = 0
    injected_seen = 0
    for g in GROUPS:
        gdir = os.path.join(args.out, g)
        os.makedirs(gdir, exist_ok=True)
        for r in range(RUNS_PER_GROUP):
            scenes = []
            n_scenes = rng.randint(3, 5)
            for _ in range(n_scenes):
                scenes.append({"narration": rng.choice(CLEAN)})
            if (g, r) in injected_slots:
                # 混入文はシーンの1つとして差し込む
                pos = rng.randrange(len(scenes))
                scenes[pos] = {"narration": INJECTED[injected_seen % INJECTED_COUNT]}
                injected_seen += 1
            story = {"scenes": scenes}
            rdir = os.path.join(gdir, f"run_{r:03d}")
            os.makedirs(rdir, exist_ok=True)
            with open(os.path.join(rdir, "story.json"), "w", encoding="utf-8") as f:
                json.dump(story, f, ensure_ascii=False, indent=1)
            n += 1

    print(f"wrote {n} stories -> {args.out}/<group>/<run>/story.json "
          f"(injected={injected_seen}, clean={n - injected_seen}, seed={args.seed})")
    print(f"next: SPAN01_CORPUS_SRC={args.out} python corpus/build_corpus.py")


if __name__ == "__main__":
    main()
