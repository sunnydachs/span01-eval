"""Track B — 較正（reliability）: 予測確率 vs 実測正解率。

合成ケース（正解が明確・lenient基準）と実データ（lenient基準）を統合してビン集計する。
決定性は同一入力の反復で確認済み（別途）。
"""
import argparse
import json
import os
import re

LEGIT: set = set()  # 実行時に --exempt で指定（lenient基準）
LAT = re.compile(r"[A-Za-z]{2,}")
BINS = [(0.0, 0.05), (0.05, 0.15), (0.15, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 0.95), (0.95, 1.01)]


def load_synth(path):
    d = json.load(open(path))
    rows = []
    for r in d["results"]:
        if isinstance(r.get("probability"), (int, float)):
            rows.append({"id": "synth/" + r["id"], "probability": r["probability"],
                         "y": bool(r["lenient_positive"]), "src": "synthetic"})
    return rows


def load_real(path):
    d = json.load(open(path))
    rows = []
    for r in d["results"]:
        if isinstance(r.get("probability"), (int, float)):
            y = bool([t for t in r.get("latin_tokens", []) if t not in LEGIT])
            rows.append({"id": r["id"], "probability": r["probability"], "y": y, "src": "real"})
    return rows


def main():
    global LEGIT
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth", default="../results/tune_v4.json")
    ap.add_argument("--real", default="../results/trackA_v4.json")
    ap.add_argument("--exempt", default=os.environ.get("SPAN01_EXEMPT", ""),
                    help="lenient基準で固有名詞扱いにするトークン(カンマ区切り)。未指定なら環境変数 SPAN01_EXEMPT")
    args = ap.parse_args()
    LEGIT = {t.strip() for t in args.exempt.split(",") if t.strip()}
    rows = load_synth(args.synth) + load_real(args.real)
    n_pos = sum(1 for r in rows if r["y"])
    print(f"n={len(rows)} positives={n_pos} negatives={len(rows)-n_pos} (lenient labels)\n")

    print(f"{'bin':14} {'n':>4} {'avg_pred':>9} {'actual':>7}  gap")
    tot_gap = 0.0
    for lo, hi in BINS:
        grp = [r for r in rows if lo <= r["probability"] < hi]
        if not grp:
            continue
        ap_ = sum(r["probability"] for r in grp) / len(grp)
        ac = sum(1 for r in grp if r["y"]) / len(grp)
        gap = ac - ap_
        tot_gap += abs(gap) * len(grp)
        print(f"[{lo:.2f},{hi:.2f})   {len(grp):>4} {ap_:9.3f} {ac:7.3f}  {gap:+.3f}")
    print(f"\nmean |gap| (weighted) = {tot_gap/len(rows):.3f}")

    # 分離度: 陽性群と陰性群の確率レンジ
    posp = [r["probability"] for r in rows if r["y"]]
    negp = [r["probability"] for r in rows if not r["y"]]
    if posp and negp:
        print(f"\npositives: n={len(posp)} min={min(posp):.3f} max={max(posp):.3f}")
        print(f"negatives: n={len(negp)} min={min(negp):.3f} max={max(negp):.3f}")
        # 0.5 での混同
        fn = [r for r in rows if r["y"] and r["probability"] < 0.5]
        fp = [r for r in rows if not r["y"] and r["probability"] >= 0.5]
        print(f"at 0.5: FN={len(fn)} FP={len(fp)}")
        for r in fn + fp:
            print(f"   {r['id']:34} p={r['probability']:.3f} y={r['y']} [{r['src']}]")


if __name__ == "__main__":
    main()
