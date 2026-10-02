"""多角的再評価の疑問点を解消する検証: mercury-decide の prose 依存性。

spike(docs/mercury-decide-spike-2026-10-01.md)で「mercuryがprose依存に強い」は
vague 指示での比較が抜けていたため、23ケース境界スイートを2つの instructions で
両モデルに投げて検証する。

  v1_current : 曖昧な指示(run_matrix.VARIANTS の v1_current)
  v4_full    : production 指示文(run_gate.DEFAULT_INSTRUCTIONS)

問い: mercury は vague でも v4 と同じ判定を返すか(=prose依存が小さいか)。
span-01 は既知(vague で OK/コード断片が回収される)。

OpenRouter の無料枠(1,000 calls/日, JST 09:00 リセット)を消費するので
枠回復後に実行すること。92 calls。

使用例:
  python scripts/run_mercury_prose.py --out results/prose_dependence.json
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from envconfig import get_base_url, get_key  # noqa: E402
from run_gate import DEFAULT_INSTRUCTIONS as V4_FULL  # noqa: E402
from run_matrix import CASES, VARIANTS  # noqa: E402

DECISIONS_URL = "/alpha/decisions"
VAGUE = VARIANTS["v1_current"]
MODELS = ["inception/mercury-decide:free", "respan/span-01-lite:free"]


def call(key, model, state, instructions, timeout=60):
    import urllib.error
    import urllib.request

    body = {"model": model, "state": state,
            "questions": {"mixed_lang": {"type": "noul", "instructions": instructions}}}
    req = urllib.request.Request(
        (get_base_url() or "https://openrouter.ai/api") + DECISIONS_URL,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        ans = (data.get("answers") or {}).get("mixed_lang") or {}
        return {"ok": True, "probability": ans.get("noul"),
                "elapsed": round(time.time() - t0, 2)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode()[:200]}",
                "elapsed": round(time.time() - t0, 2)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:200], "elapsed": round(time.time() - t0, 2)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/prose_dependence.json")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--models", nargs="*", default=MODELS)
    args = ap.parse_args()

    key, src = get_key()
    total = len(CASES) * len(args.models) * 2
    print(f"key<{src}> cases={len(CASES)} models={len(args.models)} variants=2 total={total}", flush=True)

    results = []
    n = 0
    for cid, cat, text, sp, lp in CASES:
        rec = {"id": cid, "category": cat, "text": text,
               "strict_positive": sp, "lenient_positive": lp, "by_model": {}}
        for model in args.models:
            by_variant = {}
            for vname, vtext in [("vague", VAGUE), ("v4_full", V4_FULL)]:
                n += 1
                r = call(key, model, text, vtext)
                by_variant[vname] = r
                print(f"[{n}/{total}] {cid:24} {model.split('/')[1]:18} {vname:8} -> "
                      f"{r.get('probability')} {'FLAG' if (r.get('probability') or 0) >= 0.5 else '-'}",
                      flush=True)
                time.sleep(args.interval)
            rec["by_model"][model] = by_variant
        results.append(rec)
        # 進捗を毎ケース保存(タイムアウト対策)
        json.dump({"meta": {"vague": VAGUE, "v4_full": V4_FULL, "threshold": 0.5,
                            "cases": len(CASES)}, "results": results},
                  open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nsaved {args.out}")


if __name__ == "__main__":
    main()
