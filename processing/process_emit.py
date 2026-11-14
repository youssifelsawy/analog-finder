#!/usr/bin/env python3
"""
process_emit.py - summarise NASA EMIT L2B mineral identifications at each site.

Input: the CSV(s) AppEEARS returns for a point request on product EMITL2BMIN.001
(layers group_1_mineral_id, group_1_band_depth, group_2_mineral_id, group_2_band_depth),
using emit_points_for_appeears.csv (Category = site id, 9 points per site).

For every valid observation, the mineral ID is looked up in NASA's mineral grouping table
(emit-sds-l2b, mineral_grouping_matrix_20230503.csv) and counted toward its family:
Carbonate, Clay, Sulfate, Iron Oxide. Group 1 = ~1 um iron-oxide features,
group 2 = ~2 um features (clays, carbonates, sulfates).

Output: JSON {site_id: {"n_obs": .., "carbonate": share, "clay": .., "sulfate": .., "iron_oxide": ..,
"top_minerals": [...]}} written to emit_summary.json.
"""
import csv, json, sys, os, collections

FAMILIES = {"Carbonate": "carbonate", "Clay": "clay", "Sulfate": "sulfate", "Iron Oxide": "iron_oxide"}
MINERAL_FAMILY = {"Calcite": "Carbonate", "Dolomite": "Carbonate", "Gypsum": "Sulfate",
                  "Goethite": "Iron Oxide", "Hematite": "Iron Oxide", "Chlorite": "Clay",
                  "Illite+Muscovite": "Clay", "Kaolinite": "Clay", "Montmorillonite": "Clay",
                  "Vermiculite": "Clay"}
MIN_DEPTH = 0.02   # ignore very weak spectral features


def load_groups(path):
    table = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                idx, grp = int(r["Index"]), int(r["Group"])
            except (ValueError, KeyError):
                continue
            fams = {k for k in FAMILIES if (r.get(k) or "").strip() not in ("", "0")}
            for mineral, fam in MINERAL_FAMILY.items():      # the ten EMIT target minerals
                if (r.get(mineral) or "").strip() not in ("", "0"):
                    fams.add(fam)
            table[(grp, idx)] = {"name": r["Name"].split(" ")[0], "families": fams}
    return table


def find_col(cols, *needles):
    for c in cols:
        lc = c.lower()
        if all(n in lc for n in needles):
            return c
    return None


def main(csv_paths, groups_path, out_path):
    groups = load_groups(groups_path)
    obs = collections.defaultdict(lambda: {"n": 0, "fam": collections.Counter(), "min": collections.Counter(),
                                           "ng": collections.Counter(), "famg": collections.Counter()})
    for p in csv_paths:
        with open(p, newline="", encoding="utf-8") as fh:
            rd = csv.DictReader(fh)
            cols = rd.fieldnames or []
            c_cat = find_col(cols, "category")
            if "group" in cols and "mineral_id" in cols:      # long format: one row per detection
                for r in rd:
                    try:
                        grp, mid, depth = int(r["group"]), int(float(r["mineral_id"])), float(r.get("band_depth") or 1)
                    except (TypeError, ValueError):
                        continue
                    if mid <= 0 or depth < MIN_DEPTH or (grp, mid) not in groups:
                        continue
                    g = groups[(grp, mid)]
                    o = obs[r[c_cat]]
                    o["n"] += 1
                    o["ng"][grp] += 1
                    o["min"][g["name"]] += 1
                    for f in g["families"]:
                        o["fam"][FAMILIES[f]] += 1
                        o["famg"][(grp, FAMILIES[f])] += 1
                continue
            spec = [(1, find_col(cols, "group_1_mineral_id"), find_col(cols, "group_1_band_depth")),
                    (2, find_col(cols, "group_2_mineral_id"), find_col(cols, "group_2_band_depth"))]
            if not c_cat or not all(s[1] for s in spec):
                sys.exit(f"{p}: could not find Category / mineral_id columns. Columns are: {cols}")
            for r in rd:
                site = r[c_cat]
                for grp, c_id, c_depth in spec:
                    try:
                        mid = int(float(r[c_id]))
                        depth = float(r[c_depth]) if c_depth else 1.0
                    except (TypeError, ValueError):
                        continue
                    if mid <= 0 or depth < MIN_DEPTH or (grp, mid) not in groups:
                        continue
                    g = groups[(grp, mid)]
                    o = obs[site]
                    o["n"] += 1
                    o["min"][g["name"]] += 1
                    for f in g["families"]:
                        o["fam"][FAMILIES[f]] += 1
    out = {}
    for site, o in sorted(obs.items()):
        n = o["n"]
        n1, n2 = o["ng"][1] or 1, o["ng"][2] or 1
        out[site] = {"n_obs": n, **{v: round(o["fam"][v] / n, 2) for v in FAMILIES.values()},
                     # shares within each spectral group: 2-um features (carbonate/clay/sulfate), 1-um (iron oxide)
                     "carbonate_2um": round(o["famg"][(2, "carbonate")] / n2, 2),
                     "clay_2um": round(o["famg"][(2, "clay")] / n2, 2),
                     "sulfate_2um": round(o["famg"][(2, "sulfate")] / n2, 2),
                     "iron_oxide_1um": round(o["famg"][(1, "iron_oxide")] / n1, 2),
                     "n_2um": o["ng"][2], "n_1um": o["ng"][1],
                     "top_minerals": [m for m, _ in o["min"].most_common(3)]}
    json.dump(out, open(out_path, "w"), indent=1)
    for site, v in out.items():
        print(f"{site:20s} 2um n={v['n_2um']:3d} carb {v['carbonate_2um']:.2f} clay {v['clay_2um']:.2f} "
              f"sulf {v['sulfate_2um']:.2f} | 1um FeOx {v['iron_oxide_1um']:.2f}  {', '.join(v['top_minerals'])}")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    if len(sys.argv) < 2:
        sys.exit("usage: process_emit.py appeears_result.csv [more.csv ...]")
    main(sys.argv[1:], os.path.join(here, "emit_mineral_groups.csv"), "emit_summary.json")
