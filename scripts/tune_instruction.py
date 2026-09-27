"""指示文チューニング: 合成ケースで候補 instructions を比較する。

run_matrix.CASES を再利用。使い方:
  python scripts/tune_instruction.py --instruction-file candidates/v4.txt --out results/tune_v4.json
"""
import argparse
import json
import re
import time

from run_gate import DEFAULT_MODEL, call, get_key
from run_matrix import CASES

LAT = re.compile(r"[A-Za-z]{2,}")


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    return p, r, (2 * p * r / (p + r) if p == p and r == r and p + r else float("nan"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instructions", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--interval", type=float, default=3.2)
    args = ap.parse_args()

    instructions = args.instructions
    if instructions.startswith("@"):
        instructions = open(instructions[1:], encoding="utf-8").read().strip()

    key, src = get_key()
    print(f"model={DEFAULT_MODEL} key<{src}> cases={len(CASES)}")
    print(f"instructions: {instructions[:100]}...\n")

    out = {"meta": {"model": DEFAULT_MODEL, "instructions": instructions, "threshold": args.threshold,
                    "observed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, "results": []}
    for i, (cid, cat, text, sp, lp) in enumerate(CASES, 1):
        r = call(text, key, DEFAULT_MODEL, instructions, "mixed_lang")
        prob = r.get("probability")
        flagged = isinstance(prob, (int, float)) and prob >= args.threshold
        out["results"].append({"id": cid, "category": cat, "text": text,
                               "strict_positive": bool(LAT.search(text)), "lenient_positive": lp,
                               "probability": prob, "flagged": flagged, "cost": r.get("cost"),
                               "elapsed": r.get("elapsed"), "ok": r.get("ok")})
        print(f"[{i}/{len(CASES)}] {cid:22} {prob} {'FLAG' if flagged else '-'}", flush=True)
        if i < len(CASES):
            time.sleep(args.interval)

    s = [0, 0, 0, 0]; l = [0, 0, 0, 0]
    for rec in out["results"]:
        for arr, y in ((s, rec["strict_positive"]), (l, rec["lenient_positive"])):
            if y and rec["flagged"]: arr[0] += 1
            elif not y and rec["flagged"]: arr[1] += 1
            elif y and not rec["flagged"]: arr[2] += 1
            else: arr[3] += 1
    sp, sr, sf = prf(*s[:3]); lp, lr, lf = prf(*l[:3])
    print(f"\nstrict  TP/FP/FN={s[0]}/{s[1]}/{s[2]} P={sp:.2f} R={sr:.2f} F1={sf:.2f}")
    print(f"lenient TP/FP/FN={l[0]}/{l[1]}/{l[2]} P={lp:.2f} R={lr:.2f} F1={lf:.2f}")
    print("\nmisses (lenient):")
    for rec in out["results"]:
        if rec["lenient_positive"] and not rec["flagged"]:
            print(f"  MISS {rec['id']} prob={rec['probability']}")
    for rec in out["results"]:
        if not rec["lenient_positive"] and rec["flagged"]:
            print(f"  FP   {rec['id']} prob={rec['probability']}")
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nsaved {args.out}")


if __name__ == "__main__":
    main()
