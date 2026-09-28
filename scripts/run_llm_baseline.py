"""Track B/D — 無料チャットLLMを同一ケースのベースラインとして走らせる。

モデル: OpenRouter の無料チャットモデル（既定 nvidia/nemotron-3-super-120b-a12b:free）
用途: span-01-lite の decision 呼び出しと同一ケースでの P/R・レイテンシ・決定性の比較。
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request

from envconfig import get_key
from run_matrix import CASES

CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
LAT = re.compile(r"[A-Za-z]{2,}")

SYSTEM = (
    "You decide whether a Japanese narration text contains English words or phrases that a Japanese "
    "speaker would have to read aloud as English. Count even a single English word next to Japanese text. "
    "Do NOT count katakana loanwords, brand names (iPhone, YouTube), URLs, version/file names, code "
    "fragments, short acronyms (AI, OK), or character/proper names in Latin (e.g. Kuro). "
    "Answer with exactly one word: YES or NO."
)


def ask(text, key, model=MODEL, temperature=0.0, timeout=120):
    body = {"model": model, "temperature": temperature, "max_tokens": 512,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": text}]}
    req = urllib.request.Request(CHAT_URL, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
        msg = data["choices"][0]["message"]
        content = (msg.get("content") or "").strip()
        reasoning = (msg.get("reasoning") or "").strip()
        usage = data.get("usage") or {}
        # 最終回答は content の末尾に出る想定。content が空なら reasoning の末尾を見る。
        source = content or reasoning
        # 末尾 200 文字から最後の YES/NO を探す
        tail = source[-200:].upper()
        matches = re.findall(r"\b(YES|NO)\b", tail)
        ans = matches[-1] if matches else None
        return {"ok": True, "answer": ans, "raw": source[-60:],
                "flagged": (ans == "YES") if ans else None,
                "cost": usage.get("cost"), "elapsed": round(time.time() - t0, 2)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}: {e.read().decode()[:160]}", "elapsed": round(time.time() - t0, 2)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:160], "elapsed": round(time.time() - t0, 2)}


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else float("nan")
    r = tp / (tp + fn) if tp + fn else float("nan")
    return p, r, (2 * p * r / (p + r) if p == p and r == r and p + r else float("nan"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="../results/trackD_llm.json")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--repeat-check", type=int, default=3, help="決定性チェック: 上位N件を3回反復")
    ap.add_argument("--interval", type=float, default=3.2)
    args = ap.parse_args()

    key, src = get_key()
    print(f"model={args.model} key<{src}> cases={len(CASES)}", flush=True)
    out = {"meta": {"model": args.model, "observed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "system": SYSTEM}, "results": [], "determinism": []}
    for i, (cid, cat, text, sp, lp) in enumerate(CASES, 1):
        r = ask(text, key, model=args.model)
        out["results"].append({"id": cid, "category": cat, "text": text,
                               "strict_positive": bool(LAT.search(text)), "lenient_positive": lp, **r})
        print(f"[{i}/{len(CASES)}] {cid:22} {r.get('answer')} ({r.get('raw')!r}) {r.get('elapsed')}s", flush=True)
        time.sleep(args.interval)

    # 決定性: 先頭の数件を temperature 0 で3回
    for cid, cat, text, sp, lp in CASES[:args.repeat_check]:
        reps = []
        for _ in range(3):
            reps.append(ask(text, key, model=args.model).get("answer"))
            time.sleep(args.interval)
        out["determinism"].append({"id": cid, "answers": reps})
        print(f"determinism {cid}: {reps}", flush=True)

    s = [0, 0, 0, 0]; l = [0, 0, 0, 0]
    for rec in out["results"]:
        fl = rec.get("flagged") or False
        for arr, y in ((s, rec["strict_positive"]), (l, rec["lenient_positive"])):
            if y and fl: arr[0] += 1
            elif not y and fl: arr[1] += 1
            elif y and not fl: arr[2] += 1
            else: arr[3] += 1
    sp, sr, sf = prf(*s[:3]); lp, lr, lf = prf(*l[:3])
    print(f"\nstrict  TP/FP/FN={s[0]}/{s[1]}/{s[2]} P={sp:.2f} R={sr:.2f} F1={sf:.2f}")
    print(f"lenient TP/FP/FN={l[0]}/{l[1]}/{l[2]} P={lp:.2f} R={lr:.2f} F1={lf:.2f}")
    lat = [r["elapsed"] for r in out["results"] if r.get("elapsed")]
    if lat:
        lat.sort()
        print(f"latency median={lat[len(lat)//2]:.2f}s min={lat[0]:.2f}s max={lat[-1]:.2f}s")
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
