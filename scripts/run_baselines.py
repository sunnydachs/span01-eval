"""合成スイートに対する regex ベースラインと、閾値スイープを計算する。

これまで reports/trackD.md の「regex段」行は実データ(n=52)の数値を合成23件の表に
混ぜていた（外部レビューで指摘）。ここで同一条件の数値を再現可能な形で出す。

  python scripts/run_baselines.py            # 表示のみ
  python scripts/run_baselines.py --json     # results/baselines.json へ保存
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_matrix import CASES  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results")

LATIN = re.compile(r"[A-Za-z]{2,}")
JP = r"ぁ-んァ-ヶー一-龥々"
PROJ_PATTERNS = (rf"[A-Za-z]{{2,}}[{JP}]", rf"[{JP}][A-Za-z]{{2,}}",
                 rf"[A-Za-z]{{2,}}\s+[{JP}]", rf"[{JP}]\s+[A-Za-z]{{2,}}")

# 実データ lenient で許容するトークン（--exempt / SPAN01_EXEMPT で指定）
EXEMPT: set = set()


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def score(pred, standard):
    tp = fp = fn = tn = 0
    for _id, _cat, _text, s_pos, l_pos in CASES:
        y = s_pos if standard == "strict" else l_pos
        hit = pred[_id]
        if y and hit: tp += 1
        elif y and not hit: fn += 1
        elif not y and hit: fp += 1
        else: tn += 1
    p, r, f = prf(tp, fp, fn)
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "p": round(p, 3),
            "r": round(r, 3), "f1": round(f, 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--exempt", default=os.environ.get("SPAN01_EXEMPT", ""),
                    help="実データの lenient 基準で許容するトークン（カンマ区切り。LABELS.md 参照）")
    args = ap.parse_args()
    global EXEMPT
    EXEMPT = {t.strip() for t in args.exempt.split(",") if t.strip()}
    print(f"exempt={sorted(EXEMPT)}")

    preds = {
        "latin_any": {c[0]: bool(LATIN.search(c[2])) for c in CASES},
        "proj_patterns": {c[0]: any(re.search(p, c[2]) for p in PROJ_PATTERNS) for c in CASES},
    }
    out = {"n_cases": len(CASES), "methods": {}, "threshold_sweep": {}}
    for name, pred in preds.items():
        out["methods"][name] = {s: score(pred, s) for s in ("strict", "lenient")}

    print("=== 合成23件に対する regex ベースライン ===")
    for name in preds:
        for std in ("strict", "lenient"):
            m = out["methods"][name][std]
            print(f"{name:<14} {std:<8} TP={m['tp']:>2} FP={m['fp']:>2} FN={m['fn']:>2} TN={m['tn']:>2} "
                  f"P={m['p']:.3f} R={m['r']:.3f} F1={m['f1']:.3f}")

    # 閾値スイープ（合成23 + 実データ52 = 75、lenient相当）
    rows = []
    tune = os.path.join(RESULTS, "tune_v4.json")
    if os.path.exists(tune):
        data = json.load(open(tune))
        for r in data["results"]:
            if r.get("ok") and isinstance(r.get("probability"), (int, float)):
                rows.append((r["probability"], r["lenient_positive"]))
    real = os.path.join(RESULTS, "trackA_v4.json")
    if os.path.exists(real):
        data = json.load(open(real))
        for r in data["results"]:
            if not r.get("ok"):
                continue
            toks = r.get("latin_tokens") or []
            rows.append((r["probability"], bool([t for t in toks if t not in EXEMPT])))
    print(f"\n=== 閾値スイープ (n={len(rows)}) ===")
    print("thr    TP FP FN   P      R      F1")
    for thr in (0.15, 0.3, 0.4, 0.5, 0.6, 0.7, 0.85):
        tp = fp = fn = 0
        for prob, y in rows:
            if prob is None:
                continue
            hit = prob >= thr
            if y and hit: tp += 1
            elif y and not hit: fn += 1
            elif not y and hit: fp += 1
        p, r, f = prf(tp, fp, fn)
        out["threshold_sweep"][str(thr)] = {"tp": tp, "fp": fp, "fn": fn,
                                            "p": round(p, 3), "r": round(r, 3), "f1": round(f, 3)}
        print(f"{thr:<6} {tp:>2} {fp:>2} {fn:>2}   {p:.3f}  {r:.3f}  {f:.3f}")

    if args.json:
        path = os.path.join(RESULTS, "baselines.json")
        json.dump(out, open(path, "w"), ensure_ascii=False, indent=2)
        print(f"\nsaved {os.path.relpath(path)}")


if __name__ == "__main__":
    main()
