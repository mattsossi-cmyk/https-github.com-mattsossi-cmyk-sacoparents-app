import collections, json, sys

R = json.load(open(sys.argv[1]))
agg = collections.defaultdict(lambda: {"pages": [], "nodes": 0})
pairs = collections.Counter()
examples = {}
for r in R:
    for v in r.get("violations", []):
        a = agg[v["id"]]
        a["pages"].append(f"{r['who']}:{r['path']}")
        a["nodes"] += v["n"]
        a["impact"], a["help"] = v["impact"], v["help"]
        a.setdefault("ex", v["nodes"][:3])
        if v["id"] == "color-contrast":
            for nd in v["nodes"]:
                d = nd.get("d") or {}
                key = (d.get("fgColor"), d.get("bgColor"), d.get("contrastRatio"))
                pairs[key] += 1
                examples.setdefault(key, (r["path"], nd["html"][:120]))
for k, a in sorted(agg.items(), key=lambda x: -len(x[1]["pages"])):
    print(f"\n## {k} [{a['impact']}] pages={len(a['pages'])} nodes={a['nodes']} - {a['help']}")
    if k != "color-contrast":
        print("  pages:", a["pages"][:12])
        for e in a["ex"]:
            print("   ", e["t"], "|", e["html"][:110])
print("\n## contrast pairs (fg, bg, ratio) count / example")
for key, c in pairs.most_common(int(sys.argv[2]) if len(sys.argv) > 2 else 40):
    print(c, key, examples[key])
print("\nERRORS:", [(r["path"], r["error"]) for r in R if r.get("error")])
print("OVERFLOW 390:", [f"{r['who']}:{r['path']}" for r in R if r.get("overflow")])
print("OVERFLOW 200%:", [f"{r['who']}:{r['path']}" for r in R if r.get("overflow_200")])
