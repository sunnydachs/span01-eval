"""結果を集計し、複数のベースラインと比較する。

2つの正解基準を併記する:
- strict : ラテン語トークンが1つでもあれば陽性（固有名詞の例外なし）
- lenient: 固有名詞/キャラ名（LEGIT）を除外して陽性判定

比較対象（without 側）:
- none   : 何もしない（歴史的な実態。全件 未検知 = 再現率0）
- latin  : 厳格な「ラテン語検出」regex（参考の素朴ベースライン）
- proj   : language_gate.regex_mixed_language_hit（直隣接＋空白区切り）
- gate   : span-01-lite:free の noul
"""
import argparse
import json
import re

LATIN = re.compile(r"[A-Za-z]{2,}")
JP = r"ぁ-んァ-ヶー一-龥々"
PROJ_PATTERNS = (
    rf"[A-Za-z]{{2,}}[{JP}]", rf"[{JP}][A-Za-z]{{2,}}",
    rf"[A-Za-z]{{2,}}\s+[{JP}]", rf"[{JP}]\s+[A-Za-z]{{2,}}",
)

# 固有名詞・キャラ名として扱うトークン（lenient 基準のみで除外）。実行時に --exempt で指定。
DEFAULT_EXEMPT: set = set()


def proj_regex(text):
    return any(re.search(p, text) for p in PROJ_PATTERNS)


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    f = 2 * p * r / (p + r) if p == p and r == r and (p + r) else float("nan")
    return p, r, f


def true_label(rec, standard, exempt=frozenset()):
    toks = rec["latin_tokens"]
    if standard == "strict":
        return bool(toks)
    return bool([t for t in toks if t not in exempt])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--exempt", default="", help="lenient基準で固有名詞扱いにするトークン(カンマ区切り)")
    args = ap.parse_args()
    exempt = frozenset(t.strip() for t in args.exempt.split(",") if t.strip())
    data = json.load(open(args.results))
    res = [r for r in data["results"] if r.get("ok") and isinstance(r.get("probability"), (int, float))]

    print(f"model={data['meta']['model']} n={len(res)} threshold={args.threshold}")
    print(f"instructions={data['meta']['instructions'][:80]}...\n")

    for standard in ("strict", "lenient"):
        print(f"=== label standard: {standard} ===")
        rows = {
            "none":  [0, 0, 0, 0],
            "latin": [0, 0, 0, 0],
            "proj":  [0, 0, 0, 0],
            "gate":  [0, 0, 0, 0],
        }
        for r in res:
            y = true_label(r, standard, exempt)
            preds = {
                "none": False,
                "latin": bool(LATIN.search(r["narration"])),
                "proj": proj_regex(r["narration"]),
                "gate": r["probability"] >= args.threshold,
            }
            for name, pred in preds.items():
                if y and pred: rows[name][0] += 1
                elif y and not pred: rows[name][2] += 1
                elif not y and pred: rows[name][1] += 1
                else: rows[name][3] += 1
        print(f"{'method':6} TP  FP  FN  TN    P      R      F1")
        for name, (tp, fp, fn, tn) in rows.items():
            p, rr, f = prf(tp, fp, fn)
            print(f"{name:6} {tp:<3} {fp:<3} {fn:<3} {tn:<3}  {p:.3f}  {rr:.3f}  {f:.3f}")
        print()

    # 確率分布
    flags = sorted(r["probability"] for r in res if r["probability"] >= args.threshold)
    rest = sorted(r["probability"] for r in res if r["probability"] < args.threshold)
    print(f"flagged ({len(flags)}): min={flags[0]:.3f} max={flags[-1]:.3f}" if flags else "flagged: none")
    print(f"unflagged ({len(rest)}): min={rest[0]:.3f} max={rest[-1]:.3f}" if rest else "unflagged: none")

    print("\n=== gate-unflagged items that contain latin (recall misses) ===")
    for r in res:
        if r["latin_tokens"] and r["probability"] < args.threshold:
            print(f"  {r['id']} {r['latin_tokens']} prob={r['probability']:.3f}")

    print("\n=== gate-flagged items without latin (precision misses) ===")
    for r in res:
        if not r["latin_tokens"] and r["probability"] >= args.threshold:
            print(f"  {r['id']} prob={r['probability']:.3f}")


if __name__ == "__main__":
    main()
