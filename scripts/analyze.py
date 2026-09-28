"""結果を集計し、複数のベースラインと比較する。

2つの正解基準を併記する:
- strict : ラテン語トークンが1つでもあれば陽性（固有名詞の例外なし）
- lenient: 固有名詞/キャラ名（--exempt）を除外して陽性判定

比較対象（without 側）:
- none   : 何もしない（全件 未検知 = 再現率0）
- latin  : 厳格な「ラテン語検出」regex（参考の素朴ベースライン）
- proj   : 直隣接＋空白区切りのパターン
- gate   : 判定モデル (span-01-lite)

入力は run_gate.py の生結果（narration を含む）のほか、匿名化済みの
results/public/*.json（narration 削除・latin_tokens→latin_token_count 置換済み）も
受け付ける。匿名化ファイルは latin/proj の regex 再計算ができないため、
それらの行は省略され、none/gate の行だけが出る。
"""
import argparse
import json
import os
import re

LATIN = re.compile(r"[A-Za-z]{2,}")
JP = r"ぁ-んァ-ヶー一-龥々"
PROJ_PATTERNS = (
    rf"[A-Za-z]{{2,}}[{JP}]", rf"[{JP}][A-Za-z]{{2,}}",
    rf"[A-Za-z]{{2,}}\s+[{JP}]", rf"[{JP}]\s+[A-Za-z]{{2,}}",
)


def proj_regex(text):
    return any(re.search(p, text) for p in PROJ_PATTERNS)


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    f = 2 * p * r / (p + r) if p == p and r == r and (p + r) else float("nan")
    return p, r, f


def has_latin(rec):
    """生結果なら latin_tokens から、匿名化済みなら has_latin / latin_token_count から。"""
    if "latin_tokens" in rec:
        return bool(rec["latin_tokens"])
    if "has_latin" in rec:
        return bool(rec["has_latin"])
    return bool(rec.get("latin_token_count", 0))


def true_label(rec, standard, exempt=frozenset()):
    if standard == "strict":
        return has_latin(rec)
    if "latin_tokens" in rec:
        return bool([t for t in rec["latin_tokens"] if t not in exempt])
    # 匿名化済み: トークン列が無いので strict と同じ扱い（免除は適用不能）
    return has_latin(rec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--exempt", default=os.environ.get("SPAN01_EXEMPT", ""),
                    help="lenient基準で固有名詞扱いにするトークン(カンマ区切り)。未指定なら環境変数 SPAN01_EXEMPT")
    args = ap.parse_args()
    exempt = frozenset(t.strip() for t in args.exempt.split(",") if t.strip())
    data = json.load(open(args.results))
    res = [r for r in data["results"] if r.get("ok") and isinstance(r.get("probability"), (int, float))]
    anonymized = "latin_tokens" not in res[0] if res else False

    print(f"model={data['meta']['model']} n={len(res)} threshold={args.threshold}"
          + ("  [anonymized input: regex rows unavailable]" if anonymized else ""))
    if "instructions" in data["meta"]:
        print(f"instructions={data['meta']['instructions'][:80]}...\n")

    for standard in ("strict", "lenient"):
        if anonymized and standard == "lenient" and exempt:
            print("=== label standard: lenient === (exemption list cannot apply to anonymized data; skipped)\n")
            continue
        print(f"=== label standard: {standard} ===")
        rows = {
            "none":  [0, 0, 0, 0],
            "gate":  [0, 0, 0, 0],
        }
        if not anonymized:
            rows["latin"] = [0, 0, 0, 0]
            rows["proj"] = [0, 0, 0, 0]
        for r in res:
            y = true_label(r, standard, exempt)
            preds = {"none": False, "gate": r["probability"] >= args.threshold}
            if not anonymized:
                preds["latin"] = bool(LATIN.search(r["narration"]))
                preds["proj"] = proj_regex(r["narration"])
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
        if has_latin(r) and r["probability"] < args.threshold:
            toks = r.get("latin_tokens") or f"count={r.get('latin_token_count')}"
            print(f"  {r.get('id') or r.get('item')} {toks} prob={r['probability']:.3f}")

    print("\n=== gate-flagged items without latin (precision misses) ===")
    for r in res:
        if not has_latin(r) and r["probability"] >= args.threshold:
            print(f"  {r.get('id') or r.get('item')} prob={r['probability']:.3f}")


if __name__ == "__main__":
    main()
