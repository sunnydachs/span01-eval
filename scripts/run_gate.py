"""corpus/items.jsonl を Decisions API で採点する。

契約（OpenRouter Decisions API, 実測で確認）:
  POST https://openrouter.ai/api/alpha/decisions
  {model, state, questions: {<key>: {type:"noul", instructions:"..."}}}
  応答 answers.<key>.noul = 陽性確率, usage.cost
  ※ noul の質問文は `instructions` フィールド。`question` や `criteria` は 400 になる。

使用例:
  python scripts/run_gate.py --all-class --out results/trackA_all.json
  python scripts/run_gate.py --sample-neg 30 --out results/trackA.json
"""
import argparse
import json
import os
import random
import time
import urllib.error
import urllib.request

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
DEFAULT_MODEL = "respan/span-01-lite:free"
DEFAULT_KEY = "mixed_lang"
DEFAULT_INSTRUCTIONS = (
    "The Japanese narration is meant to be read aloud as Japanese. Return yes if it contains "
    "English vocabulary that a Japanese speaker would have to pronounce as an English word "
    "(for example: method, clock, missing piece, bubble wand, Let's go, welcome back). "
    "Count even a single English word that sits directly next to Japanese text. "
    "Do NOT count: katakana loanwords, established brand names (iPhone, YouTube, Instagram), "
    "URLs, version or file names, code fragments, short acronyms such as AI, DX, OK, and "
    "character or proper names written in Latin (for example the character name Kuro)."
)
ENV_CANDIDATES = [
    os.path.expanduser("~/.hermes/.env"),
]


def get_key():
    k = os.getenv("OPENROUTER_API_KEY")
    if k:
        return k, "env"
    for p in ENV_CANDIDATES:
        try:
            for line in open(p):
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'"), p
        except OSError:
            pass
    raise SystemExit("OPENROUTER_API_KEY not found")


def call(text, key, model, instructions, question_key, timeout=30):
    body = {"model": model, "state": text,
            "questions": {question_key: {"type": "noul", "instructions": instructions}}}
    req = urllib.request.Request(
        DECISIONS_URL, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        ans = (data.get("answers") or {}).get(question_key) or {}
        return {"ok": True, "probability": ans.get("noul"),
                "cost": (data.get("usage") or {}).get("cost"),
                "input_tokens": (data.get("usage") or {}).get("input_tokens"),
                "model": data.get("model"), "elapsed": round(time.time() - t0, 3)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode()[:200]}", "elapsed": round(time.time() - t0, 3)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:200], "elapsed": round(time.time() - t0, 3)}


def load_items():
    p = os.path.join(os.path.dirname(__file__), "..", "corpus", "items.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all-class", action="store_true", help="has_latin の全件 + clean全件ではなく分類全件")
    ap.add_argument("--all", action="store_true", help="全アイテム")
    ap.add_argument("--sample-neg", type=int, default=0, help="clean から決定的にサンプルする件数")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--instructions", default=DEFAULT_INSTRUCTIONS)
    ap.add_argument("--question-key", default=DEFAULT_KEY)
    ap.add_argument("--threshold", type=float, default=0.5)
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval", type=float, default=3.2)
    ap.add_argument("--seed", type=int, default=20260927)
    args = ap.parse_args()

    key, src = get_key()
    items = load_items()
    pos = [it for it in items if it["has_latin"]]
    neg = [it for it in items if not it["has_latin"]]
    if args.all:
        sel = items
    elif args.all_class:
        sel = pos + neg
    else:
        random.seed(args.seed)
        sel = pos + random.sample(neg, min(args.sample_neg, len(neg)))

    print(f"key<{src}> model={args.model} selected={len(sel)} (pos={len(pos)})", flush=True)
    out = {"meta": {"model": args.model, "question_key": args.question_key,
                    "threshold": args.threshold, "instructions": args.instructions,
                    "observed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "count": len(sel)},
           "results": []}
    for i, it in enumerate(sel, 1):
        r = call(it["narration"], key, args.model, args.instructions, args.question_key)
        rec = {"id": it["id"], "channel": it.get("group", it.get("channel", "")), "run": it["run"],
               "latin_tokens": it["latin_tokens"], "has_latin": it["has_latin"],
               "narration": it["narration"], **r}
        if r.get("ok") and isinstance(r.get("probability"), (int, float)):
            rec["flagged"] = r["probability"] >= args.threshold
        out["results"].append(rec)
        print(f"[{i}/{len(sel)}] {it['id']} {it['latin_tokens']} -> "
              f"{r.get('probability')} ({'FLAG' if rec.get('flagged') else '-'}) "
              f"cost={r.get('cost')} {r.get('elapsed')}s"
              + ("" if r.get("ok") else f" ERR={r.get('error')}"), flush=True)
        if i < len(sel):
            time.sleep(args.interval)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = [r for r in out["results"] if r.get("ok")]
    zero = [r for r in ok if r.get("cost") == 0]
    print(f"\nsaved {args.out}: ok={len(ok)}/{len(sel)} cost==0:{len(zero)}/{len(ok)}")


if __name__ == "__main__":
    main()
