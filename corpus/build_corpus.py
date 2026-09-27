"""ナレーションコーパスから評価アイテムを生成する。

入力: 任意のディレクトリツリー配下の `*/story.json`（{"scenes":[{"narration":...}]} 形式）
出力: corpus/items.jsonl

ソースは引数か環境変数 SPAN01_CORPUS_SRC で指定する（このリポジトリには実データを同梱しない）。

  SPAN01_CORPUS_SRC=/path/to/output python corpus/build_corpus.py
"""
import argparse
import glob
import json
import os
import re

OUT = os.path.join(os.path.dirname(__file__), "items.jsonl")
LATIN = re.compile(r"[A-Za-z]{2,}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=os.environ.get("SPAN01_CORPUS_SRC", ""),
                    help="story.json を探すルート（例: <project>/data/output）")
    args = ap.parse_args()
    if not args.source:
        raise SystemExit("--source (or SPAN01_CORPUS_SRC) is required; see README")

    items = []
    for p in sorted(glob.glob(os.path.join(args.source, "*", "*", "story.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        scenes = d.get("scenes") or []
        narr = " ".join((s.get("narration") or "") for s in scenes).strip()
        if not narr:
            continue
        toks = LATIN.findall(narr)
        rel = os.path.relpath(p, args.source).split(os.sep)
        items.append({
            "id": f"{rel[0]}/{rel[1]}",          # <group>/<run>
            "group": rel[0],
            "run": rel[1],
            "narration": narr,
            "latin_tokens": sorted(set(toks)),
            "has_latin": bool(toks),
        })

    with open(OUT, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    pos = sum(1 for it in items if it["has_latin"])
    print(f"wrote {len(items)} items -> {OUT}  (has_latin={pos}, clean={len(items)-pos})")


if __name__ == "__main__":
    main()
