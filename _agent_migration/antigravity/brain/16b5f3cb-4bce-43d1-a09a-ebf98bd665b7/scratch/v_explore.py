import json, sys, re
from collections import Counter, defaultdict
S = r"C:\Users\86052\.gemini\antigravity\brain\16b5f3cb-4bce-43d1-a09a-ebf98bd665b7\scratch\ref"
ref = json.load(open(S + r"\ref_env_1114.json", encoding="utf-8"))
old = json.load(open(S + r"\old_env_1117.json", encoding="utf-8"))
def pref(n):
    n = re.sub(r"\.\d+$", "", n)
    n = re.sub(r"\d+$", "#", n)
    return n
for nm, d in (("ref", ref), ("old", old)):
    c = Counter(pref(n) for n in d["objects"])
    print(nm, d["nobj"], d["all_cols"])
    print("  ", sorted(c.items(), key=lambda x: -x[1])[:80])
a, b = set(ref["objects"]), set(old["objects"])
print("only ref:", len(a - b), sorted(a - b)[:60])
print("only old:", len(b - a), sorted(b - a)[:60])
# placement diff of common
diffs = []
for n in a & b:
    ca, cb = ref["objects"][n]["c"], old["objects"][n]["c"]
    dd = sum((ca[i] - cb[i]) ** 2 for i in range(3)) ** 0.5
    if dd > 0.05:
        diffs.append((round(dd, 2), n, ca, cb))
print("common moved:", len(diffs))
for x in sorted(diffs)[-15:]:
    print("  ", x)
