import json, re, os
S = r"C:\Users\86052\.gemini\antigravity\brain\f904dce7-b62b-4bab-b561-90c92d39c8a3\scratch"
ref = json.load(open(os.path.join(S, "ref.json")))
new = json.load(open(os.path.join(S, "new.json")))


def union(names, d):
    mn = [min(d[n]["mn"][i] for n in names) for i in range(3)]
    mx = [max(d[n]["mx"][i] for n in names) for i in range(3)]
    return mn, mx


def ctr(b):
    return [(b[0][i] + b[1][i]) / 2 for i in range(3)]


RULES = [
    (r"^(V5_Stand_\w+?)_Tier(\d+)$", lambda m: [m.group(1) + "_" + m.group(2)]),
    (r"^(V5_Screen_\w)_Panel$", lambda m: [m.group(1)]),
    (r"^(V5_Bridge_\w)_Deck$", lambda m: [m.group(1)]),
    (r"^(V5_Marshal_\d)_Hut$", lambda m: [m.group(1)]),
    (r"^(V5_Marshal_\d)_Lamp$", lambda m: [m.group(1) + "_lamp"]),
    (r"^V5_Gantry_Post_L$", lambda m: ["V5_Gantry_Post_-1"]),
    (r"^V5_Gantry_Post_R$", lambda m: ["V5_Gantry_Post_1"]),
    (r"^(V5_Stand_\w+?)_Columns$", lambda m: [n for n in ref if re.match(re.escape(m.group(1)) + r"_Col\d+$", n)]),
    (r"^(V5_Stand_\w+?)_Flagpoles$", lambda m: [n for n in ref if re.match(re.escape(m.group(1)) + r"_Flagpole\d+$", n)]),
    (r"^(V5_Stand_\w+?)_Flags$", lambda m: [n for n in ref if re.match("V5_Flag_" + re.escape(m.group(1)) + r"_\d+$", n)]),
    (r"^(V5_Stand_\w+?)_FrontPosts$", lambda m: [n for n in ref if re.match(re.escape(m.group(1)) + r"_Post-?1$", n)]),
    (r"^(V5_Stand_\w+?)_Trusses$", lambda m: [n for n in ref if re.match(re.escape(m.group(1)) + r"_TrussB?\d+$", n)]),
    (r"^(V5_Screen_\w)_Legs$", lambda m: [n for n in ref if n.startswith(m.group(1) + "_leg")]),
    (r"^(V5_Bridge_\w)_Piers$", lambda m: [n for n in ref if n.startswith(m.group(1) + "_pier")]),
    (r"^(V5_Bridge_\w)_Rails$", lambda m: [n for n in ref if n.startswith(m.group(1) + "_rail")]),
    (r"^(V5_Brake_\d)_Poles$", lambda m: [n for n in ref if n.startswith(m.group(1) + "_") and "_pole" in n]),
    (r"^V5_PitBoxLines$", lambda m: [n for n in ref if n.startswith("V5_PitBoxLine_")]),
]
worst = []
unmatched = []
for n, d in new.items():
    names = None
    if n in ref:
        names = [n]
    else:
        for pat, fn in RULES:
            m = re.match(pat, n)
            if m:
                names = [x for x in fn(m) if x in ref]
                break
    if not names:
        unmatched.append(n)
        continue
    rb = union(names, ref)
    nb = (d["mn"], d["mx"])
    dc = max(abs(a - b) for a, b in zip(ctr(rb), ctr(nb)))
    ds = max(abs((rb[1][i] - rb[0][i]) - (nb[1][i] - nb[0][i])) for i in range(3))
    worst.append((dc, ds, n, len(names)))
worst.sort(reverse=True)
print("COMPARED", len(worst), "unmatched", unmatched)
for w in worst[:25]:
    print("CMP dc=%.3f dsize=%.3f %s (ref parts %d)" % w)
bad = [(n, d["loose"], d["dup"], d["zero"]) for n, d in new.items() if d["loose"] or d["dup"] or d["zero"]]
print("GEOM issues", bad)
pile = [n for n, d in new.items() if all(abs(c) < 1.0 for c in ctr((d["mn"], d["mx"])))]
print("PILE", pile)
far = [(n, max(abs(d["origin"][i] - ctr((d["mn"], d["mx"]))[i]) for i in range(3))) for n, d in new.items()]
far = [x for x in far if x[1] > 0.01]
print("ORIGIN off-center", far[:20], len(far))
