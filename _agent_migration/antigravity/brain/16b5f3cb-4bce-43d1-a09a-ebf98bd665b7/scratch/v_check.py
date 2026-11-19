# python v_check.py <ref_env.json> <new_env.json> <old_anim.json> <new_anim.json> [<old_clay.json> <new_clay.json>]
import json, sys, re, math
from collections import defaultdict

def load(p):
    return json.load(open(p, encoding="utf-8"))

args = sys.argv[1:]
ref, new, oanim, nanim = [load(p) for p in args[:4]]
clay = [load(p) for p in args[4:6]] if len(args) >= 6 else None
defects = []
def D(msg):
    defects.append(msg)
    print("DEFECT:", msg)

def dist(a, b):
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(len(a))))
def dims(o):
    return [o["bmax"][i] - o["bmin"][i] for i in range(3)]

def is_v5(n):
    return n.startswith("V5_")

print("objects: ref %d  new env %d  old anim %d  new anim %d" % (ref["nobj"], new["nobj"], oanim["nobj"], nanim["nobj"]))

for label, F in (("env", new), ("anim", nanim)) + ((("clay", clay[1]),) if clay else ()):
    O = F["objects"]
    print("\n===== %s (%s) =====" % (label, F["file"]))
    # 1. origin pile
    refnear = {n for n, o in ref["objects"].items() if math.hypot(o["c"][0], o["c"][1]) < 5}
    pile = [n for n, o in O.items() if is_v5(n) and o["type"] == "MESH" and math.hypot(o["c"][0], o["c"][1]) < 5 and n not in refnear]
    print("V5 meshes:", sum(1 for n, o in O.items() if is_v5(n) and o["type"] == "MESH"), " near-origin (not in ref):", len(pile))
    if pile:
        D("%s: %d V5_ meshes piled at origin: %s" % (label, len(pile), pile[:12]))
    # placement vs ref, by name (skip parts whose count changed on purpose)
    skip = re.compile(r"_(Col|Flagpole|Truss|TrussB)\d+$|^V5_Flag_|^V5_PitBoxLine_")
    moved = []
    for n, o in O.items():
        if not is_v5(n) or o["type"] != "MESH" or skip.search(n) or n not in ref["objects"]:
            continue
        r = ref["objects"][n]
        dc = dist(o["c"], r["c"])
        dd = max(abs(a - b) for a, b in zip(dims(o), dims(r)))
        if dc > 0.05 or dd > 0.05:
            moved.append((round(dc, 2), round(dd, 2), n, o["c"], r["c"]))
    print("same-name V5 meshes off vs 11/14 ref:", len(moved))
    for m in sorted(moved, reverse=True)[:25]:
        print("   ", m)
    if moved:
        D("%s: %d V5_ meshes differ from 11/14 placement (center/dims), worst: %s" % (label, len(moved), sorted(moved, reverse=True)[:5]))
    missing = sorted(n for n in ref["objects"] if is_v5(n) and not skip.search(n) and n not in O)
    print("ref V5 names missing in new (merged/renamed?):", len(missing), missing[:40])
    # assembly union bbox vs ref
    def akey(n):
        m = re.match(r"^(V5_Stand_[A-Za-z0-9]+|V5_Flag_V5_Stand_[A-Za-z0-9]+|V5_Bridge_[A-Z]|V5_Screen_[A-Z]|V5_Brake_\d+|V5_Marshal_\d+|V5_Hangar_\d+|V5_Ad_\d+|V5_PitGarage|V5_PitRoof|V5_PitTop|V5_PitWall|V5_Gantry|V5_StartLight|V5_PitBoxLine|V5_FieldMasts|V5_FencePosts)", n)
        if not m:
            return None
        k = m.group(1)
        return k.replace("V5_Flag_V5_Stand_", "V5_Stand_")
    def unions(Obj):
        U = {}
        for n, o in Obj.items():
            if o["type"] != "MESH" or not is_v5(n):
                continue
            k = akey(n)
            if not k:
                continue
            if k not in U:
                U[k] = [list(o["bmin"]), list(o["bmax"])]
            else:
                for i in range(3):
                    U[k][0][i] = min(U[k][0][i], o["bmin"][i])
                    U[k][1][i] = max(U[k][1][i], o["bmax"][i])
        return U
    UR, UN = unions(ref["objects"]), unions(O)
    bad = []
    for k in sorted(UR):
        if k not in UN:
            bad.append((k, "MISSING"))
            continue
        cr = [(UR[k][0][i] + UR[k][1][i]) / 2 for i in range(3)]
        cn = [(UN[k][0][i] + UN[k][1][i]) / 2 for i in range(3)]
        er = max(max(abs(UR[k][0][i] - UN[k][0][i]), abs(UR[k][1][i] - UN[k][1][i])) for i in range(3))
        if er > 0.5:
            bad.append((k, round(dist(cr, cn), 2), round(er, 2), [round(x, 1) for x in cn], [round(x, 1) for x in cr]))
    print("assemblies:", len(UR), " differing union bbox (>0.5 m):", len(bad))
    for b in bad:
        print("   ", b)
    if bad:
        D("%s: assembly union bbox differs from 11/14 ref: %s" % (label, bad[:8]))
    extra = sorted(set(UN) - set(UR))
    if extra:
        print("new assemblies not in ref:", extra)

    # 2. geometry
    geo = []
    for n, o in O.items():
        if not is_v5(n) or o["type"] != "MESH":
            continue
        if o["loose"] or o["zero"] or o["dupf"] or o["nf"] == 0:
            geo.append((n, "v%d f%d loose%d zero%d dupf%d" % (o["nv"], o["nf"], o["loose"], o["zero"], o["dupf"])))
    print("V5 meshes with loose/zero-area/dup faces:", len(geo))
    for g in geo[:40]:
        print("   ", g)
    if geo:
        D("%s: meshes with loose verts / zero-area / duplicate faces: %s" % (label, geo[:10]))
    for nm in ("V5_FencePosts", "V5_FieldMasts"):
        o = O.get(nm)
        print(nm, None if not o else "v%d f%d loose%d zero%d dupf%d dims=%s" % (o["nv"], o["nf"], o["loose"], o["zero"], o["dupf"], [round(x, 2) for x in dims(o)]))
        if not o:
            D("%s: %s missing" % (label, nm))
    grp = defaultdict(list)
    for n, o in O.items():
        if o["type"] == "MESH" and is_v5(n):
            grp[(tuple(round(x, 2) for x in o["c"]), tuple(round(x, 2) for x in dims(o)))].append(n)
    dup = [v for v in grp.values() if len(v) > 1]
    print("co-located duplicate V5 objects:", dup[:20])
    if dup:
        D("%s: co-located duplicate objects: %s" % (label, dup[:10]))
    pole = [n for n in O if re.search(r"_pole\.\d+$", n)]
    tiny = [n for n, o in O.items() if is_v5(n) and o["type"] == "MESH" and max(dims(o)) < 0.2]
    trussobj = [n for n in O if re.search(r"_Truss(B)?\d+$", n)]
    print("pole.00x:", pole, " tiny(<0.2m) V5 meshes:", len(tiny), tiny[:10], " Truss#/TrussB# objects:", len(trussobj))
    if trussobj:
        D("%s: %d per-truss objects still present" % (label, len(trussobj)))
    pbl = [n for n in O if n.startswith("V5_PitBoxLine")]
    print("PitBoxLine objects:", pbl[:5], len(pbl))
    # per-stand counts
    sc = defaultdict(list)
    for n, o in O.items():
        m = re.match(r"^V5_(?:Flag_V5_)?Stand_([A-Za-z0-9]+)", n)
        if m:
            sc[m.group(1)].append(n)
    for s in sorted(sc):
        print("  stand %s: %d objs: %s" % (s, len(sc[s]), sorted(sc[s])))

    # 3. origins
    far = []
    for n, o in O.items():
        if o["type"] != "MESH" or not (is_v5(n)):
            continue
        dg = math.sqrt(sum(x * x for x in dims(o)))
        do = dist(o["mw_t"], o["c"])
        if do > dg / 2 + 1.0:
            far.append((n, round(do, 1), round(dg, 1)))
    print("V5 meshes with origin away from geometry:", len(far), far[:20])
    if far:
        D("%s: origins far from geometry: %s" % (label, sorted(far, key=lambda x: -x[1])[:10]))
    # empties
    kids = defaultdict(list)
    for n, o in O.items():
        if o["parent"]:
            kids[o["parent"]].append(n)
    def desc(n):
        out = []
        for c in kids.get(n, []):
            out.append(c)
            out += desc(c)
        return out
    emps = [n for n, o in O.items() if o["type"] == "EMPTY" and is_v5(n)]
    print("V5 empties:", len(emps))
    for e in sorted(emps):
        ds = [d for d in desc(e) if O[d]["type"] == "MESH"]
        if not ds:
            D("%s: empty %s has no mesh children" % (label, e))
            continue
        mn = [min(O[d]["bmin"][i] for d in ds) for i in range(3)]
        mx = [max(O[d]["bmax"][i] for d in ds) for i in range(3)]
        cc = [(mn[i] + mx[i]) / 2 for i in range(3)]
        el = O[e]["mw_t"]
        hd = math.hypot(el[0] - cc[0], el[1] - cc[1])
        ext = math.hypot(mx[0] - mn[0], mx[1] - mn[1])
        flag = "" if hd < max(1.0, 0.1 * ext) else "  <-- NOT AT CENTER"
        print("  %-28s kids=%3d loc=%s center=%s hdist=%.2f z=%.2f (bbox z %.1f..%.1f) cols=%s%s" % (e, len(ds), [round(x, 1) for x in el], [round(x, 1) for x in cc], hd, el[2], mn[2], mx[2], O[e]["cols"], flag))
        if flag:
            D("%s: empty %s not at assembly center (hdist %.1f m)" % (label, e, hd))
    asm = re.compile(r"^V5_(Stand_|Flag_|Bridge_|Screen_|Brake_|Marshal_|Gantry|StartLight)")
    orphan = sorted(n for n, o in O.items() if o["type"] == "MESH" and asm.match(n) and not o["parent"])
    print("assembly meshes without parent:", len(orphan), orphan[:30])
    if orphan:
        D("%s: assembly parts without Empty parent: %s" % (label, orphan[:15]))
    for kind in ("Stand", "Bridge", "Screen", "Brake", "Marshal"):
        print("  empties for %s: %s" % (kind, sorted(e for e in emps if e.startswith("V5_" + kind))))
    # collections
    cols = F["all_cols"]
    print("collections:", cols)
    for g in ("V5_01_Road", "V5_02_Terrain", "V5_03_Barriers", "V5_04_Stands", "V5_05_Pit", "V5_06_Props", "V5_07_Lighting"):
        if g not in cols:
            D("%s: collection %s missing" % (label, g))
    bad_c = [c for c in cols if c == "09_Studio_Stage_Rig" or c.startswith("WheelSpokes_")]
    if bad_c:
        D("%s: clutter collections still present: %s" % (label, bad_c))
    def walk(t, path=""):
        if t["n"] == 0 and not t["children"]:
            print("  empty collection:", path + "/" + t["name"])
        for ch in t["children"]:
            walk(ch, path + "/" + t["name"])
    walk(F["collections"])
    # V5 objects not in a V5_0x collection
    stray = sorted(n for n, o in O.items() if is_v5(n) and not any(c.startswith("V5_0") for c in o["cols"]))
    print("V5 objects outside V5_0x collections:", len(stray), stray[:20])
    if stray:
        D("%s: V5 objects outside V5_0x collections: %s" % (label, stray[:10]))
    # empties' children in different collection buckets
    for e in emps:
        for d in desc(e):
            if set(O[d]["cols"]) != set(O[e]["cols"]):
                print("  note: %s in %s but parent %s in %s" % (d, O[d]["cols"], e, O[e]["cols"]))
                break

# 4. non-V5 unchanged: anim vs old anim, clay vs old clay
def cmp_nonv5(label, A, B):
    print("\n===== non-V5 compare %s =====" % label)
    OA, OB = A["objects"], B["objects"]
    na = {n for n in OA if not is_v5(n)}
    nb = {n for n in OB if not is_v5(n)}
    if na != nb:
        D("%s: non-V5 object set changed: removed %s added %s" % (label, sorted(na - nb)[:20], sorted(nb - na)[:20]))
    ch = []
    for n in sorted(na & nb):
        a, b = OA[n], OB[n]
        for k in ("type", "parent", "mods", "hash", "mats", "cam", "action", "ndrivers", "hide"):
            if a.get(k) != b.get(k):
                ch.append((n, k, str(a.get(k))[:60], str(b.get(k))[:60]))
        if max(abs(x - y) for ra, rb in zip(a["mw"], b["mw"]) for x, y in zip(ra, rb)) > 1e-3:
            ch.append((n, "matrix_world", a["mw_t"], b["mw_t"]))
    print("non-V5 changed:", len(ch))
    for c in ch[:40]:
        print("   ", c)
    if ch:
        D("%s: %d non-V5 object changes, e.g. %s" % (label, len(ch), ch[:6]))
    ncam = sum(1 for o in OB.values() if o["type"] == "CAMERA")
    print("cameras:", ncam)
    if ncam != sum(1 for o in OA.values() if o["type"] == "CAMERA"):
        D("%s: camera count changed" % label)
    # animation
    an = 0
    for f in A["anim"]:
        fa, fb = A["anim"][f], B["anim"].get(f, {})
        for k in fa:
            if k not in fb:
                an += 1; print("   anim missing", f, k); continue
            if k == "__active_cam":
                if fa[k] != fb[k]:
                    an += 1; print("   active cam differs", f, fa[k], fb[k])
                continue
            dm = max(abs(x - y) for ra, rb in zip(fa[k], fb[k]) for x, y in zip(ra, rb))
            if dm > 2e-3:
                an += 1
                if an < 20:
                    print("   anim diff f%s %s %.4f" % (f, k, dm))
    print("animated matrix diffs:", an)
    if an:
        D("%s: %d animated transform differences (cameras/rig/car)" % (label, an))
    for k in ("fs", "fe", "fps", "engine", "res", "camera", "markers", "view", "look", "exposure", "world"):
        if A["scene"][k] != B["scene"][k]:
            D("%s: scene %s changed: %s -> %s" % (label, k, str(A["scene"][k])[:200], str(B["scene"][k])[:200]))
    print("frame range", B["scene"]["fs"], B["scene"]["fe"], " markers", len(B["scene"]["markers"]))
    MA, MB = A["materials"], B["materials"]
    print("materials: old %d new %d; removed %s; added %s" % (len(MA), len(MB), sorted(set(MA) - set(MB)), sorted(set(MB) - set(MA))))
    mc = [m for m in set(MA) & set(MB) if MA[m].get("nodes") != MB[m].get("nodes") or MA[m].get("links") != MB[m].get("links")]
    if mc:
        D("%s: material node trees changed: %s" % (label, mc[:10]))
    rem = [m for m in set(MA) - set(MB) if MA[m]["users"] > 0]
    if rem:
        D("%s: used materials removed: %s" % (label, rem))
    if A["images"] != B["images"]:
        print("images changed:", A["images"], B["images"])

cmp_nonv5("anim", oanim, nanim)
if clay:
    cmp_nonv5("clay", clay[0], clay[1])
    # env V5 placement consistency anim vs clay vs env
for label, F in (("anim", nanim),) + ((("clay", clay[1]),) if clay else ()):
    dif = [n for n, o in new["objects"].items() if is_v5(n) and o["type"] == "MESH" and (n not in F["objects"] or dist(o["c"], F["objects"][n]["c"]) > 0.01)]
    print("%s V5 mesh placement differs from new env: %d %s" % (label, len(dif), dif[:10]))
    if dif:
        D("%s: V5 placement differs from env file: %s" % (label, dif[:10]))

print("\n######## %d DEFECTS ########" % len(defects))
for i, d in enumerate(defects, 1):
    print(i, d)
