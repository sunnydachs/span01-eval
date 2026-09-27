"""Track C — 行動信頼マップ + 指示文の言い回し感度。

合成ケース（境界を明示したもの）を、言い回しの異なる3つの instructions で採点し、
(a) どの境界が API 側で安定して判定できるか、(b) instructions の言葉遣いが結果を
どれだけ動かすか、を測る。

判定基準は2つ:
  strict : ラテン語が出たら陽性
  lenient: ブランド/固有名詞/URL/略語/カタカナは陰性（= 現行指示文の意図）
"""
import json
import os
import time

from run_gate import DEFAULT_MODEL, call, get_key

# (id, category, text, strict_positive, lenient_positive)
CASES = [
    ("pos_adjacent",   "english_word", "このmethodはやばい。今日は最強の裏技を紹介するよ。", True, True),
    ("pos_spaced",     "english_word", "この method は本当にやばい。早速やってみよう。", True, True),
    ("pos_sentence",   "english_sentence", "次のステップに行こう。 This is amazing, right? みんなも絶対試してほしい。", True, True),
    ("pos_phrase",     "english_phrase", "彼は cloak をまとっていた。星屑が淡く輝いていた。", True, True),
    ("pos_noun",       "english_word", "隠された compartments を開けると、光る音符があった。", True, True),
    ("pos_long_eng",   "english_sentence", "Hello everyone, welcome back to my channel. 今日もよろしく。", True, True),
    ("pos_greeting",   "english_phrase", "それでは Let's go 早速やってみよう。", True, True),

    ("neg_katakana",   "katakana", "スマートフォンを使って、まずはスタートしよう。アプリをひらいてボタンをおすだけ。", False, False),
    ("neg_katakana2",  "katakana", "バブルワンドで夢の窓を開けた。アプリの設定はこれで完了だ。", False, False),
    ("neg_katakana3",  "katakana", "メソッドを使ってみましょう。まずはスタート地点を決めよう。", False, False),
    ("neg_brand_iphone", "brand", "このiPhoneの設定方法を紹介します。画面をタップしてください。", False, False),
    ("neg_brand_youtube", "brand", "YouTubeのチャンネル登録もお願いします。高評価もよろしく。", False, False),
    ("neg_brand_multi", "brand", "InstagramとTikTokにも同じ動画を投稿しました。", False, False),
    ("neg_char_latin_name", "proper_noun", "ぼくはKuro。静かな草原で、遠くの子守歌が聞こえる。", False, False),
    ("neg_char_latin_name_sp", "proper_noun", "霞と月光でできた守護者が現れ、静かに Kuro を見つめた。", False, False),
    ("neg_url",        "url", "詳細は https://example.com を確認してください。", False, False),
    ("neg_version",    "alnum", "バージョン v2.1 に更新しました。動作も軽くなっています。", False, False),
    ("neg_number_unit", "alnum", "5GBのデータを使いました。残りは3GBです。", False, False),
    ("neg_acronym",    "acronym", "AIとDXの時代です。仕事のやり方が変わります。", False, False),
    ("neg_code",       "code", "設定は `npm install` を実行してください。", False, False),
    ("neg_ok",         "acronym", "はい、OKです。このまま進めましょう。", False, False),

    ("org_english_role_noun", "organic", "猫 keeper が真珠を老女に渡した。時が、再び前進した。", True, True),

    ("neu_pure_ja",    "control_negative", "この裏技は本当にやばい。今日の動画では最強の方法を紹介します。", False, False),
]

VARIANTS = {
    "v1_current": (
        "The text contains English words or phrases (A-Z/a-z) mixed into Japanese narration. "
        "Established brand names (iPhone, YouTube), proper nouns, and katakana loanwords do NOT count."
    ),
    "v2_any_latin": (
        "The text contains any Latin alphabet characters (A-Z/a-z). Japanese katakana does NOT count."
    ),
    "v3_lenient_explicit": (
        "The Japanese narration contains English words that a Japanese speaker would have to read aloud as "
        "English vocabulary (e.g. 'method', 'Let's go', 'welcome back'). Brand names, URLs, version "
        "numbers, acronyms (AI, OK), and character names written in Latin are acceptable and do NOT count."
    ),
}


def main():
    key, src = get_key()
    print(f"key<{src}> model={DEFAULT_MODEL} cases={len(CASES)} variants={len(VARIANTS)}", flush=True)
    out = {"meta": {"model": DEFAULT_MODEL, "observed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "variants": VARIANTS, "count": len(CASES) * len(VARIANTS)}, "results": []}
    n = 0
    total = len(CASES) * len(VARIANTS)
    for cid, cat, text, sp, lp in CASES:
        rec = {"id": cid, "category": cat, "text": text, "strict_positive": sp, "lenient_positive": lp, "by_variant": {}}
        for vname, vtext in VARIANTS.items():
            n += 1
            r = call(text, key, DEFAULT_MODEL, vtext, "mixed_lang")
            rec["by_variant"][vname] = r
            print(f"[{n}/{total}] {cid:22} {vname:20} -> "
                  f"{r.get('probability')} {'FLAG' if (r.get('probability') or 0) >= 0.5 else '-'} "
                  f"cost={r.get('cost')}", flush=True)
            time.sleep(3.2)
        out["results"].append(rec)
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "trackC_matrix.json")
    json.dump(out, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nsaved {os.path.relpath(out_path)}")


if __name__ == "__main__":
    main()
