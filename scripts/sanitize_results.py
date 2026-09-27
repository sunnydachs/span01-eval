"""実データ由来の測定結果から、公開可能な形へ匿名化したコピーを作る。

- id / channel / run を item_0001... へ置換（安定マッピング）
- narration（原文テキスト）を削除
- latin_tokens の具体名は残す（判定対象の特徴を示すため）

  python scripts/sanitize_results.py --in results/trackA_v4.json --out results/public/trackA_anon.json
"""
import argparse
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = json.load(open(args.inp, encoding="utf-8"))
    mapping = {}
    out = {"meta": dict(data.get("meta", {})), "note": "anonymized: ids replaced, narration removed",
           "results": []}
    for r in data["results"]:
        key = r["id"]
        if key not in mapping:
            mapping[key] = f"item_{len(mapping)+1:04d}"
        rec = {k: v for k, v in r.items() if k not in ("id", "channel", "run", "narration")}
        # ラテン語トークンの実名も固有情報になり得るため、個数のみ残す
        rec["latin_token_count"] = len(rec.pop("latin_tokens", []) or [])
        rec["item"] = mapping[key]
        out["results"].append(rec)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {args.out}: {len(out['results'])} items anonymized")


if __name__ == "__main__":
    main()
