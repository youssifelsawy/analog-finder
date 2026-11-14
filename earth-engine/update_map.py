#!/usr/bin/env python3
"""
update_map.py - load Earth Engine results into the Analog Finder map.

Usage:
  python3 update_map.py analog-finder.html \
      --sites analog_sites_features.csv \
      --candidates analog_candidates_mars_jezero.csv analog_candidates_moon_pit.csv \
      --out analog-finder-updated.html

  --sites       CSV from MODE='sites'. Replaces the estimated values of every listed
                site with the values measured from satellite data.
  --candidates  One or more CSVs from MODE='scan'. The best areas that are NOT near a
                listed site are added to the map as new candidates.
  --top N       How many new candidates to add per scan file (default 5).
  --meta        sites_meta.json (names, rock types, notes, caves, craters). Default: next to this script.

Needs only the Python standard library.
"""
import argparse, csv, json, math, os, re, sys

NUM = ["precip", "ndvi", "mat", "dtr", "elev", "slope"]
LITH_OK = {"basalt", "anorthosite", "evaporite", "carbonate", "clay", "sandstone", "ironox", "granite", "ice", "unknown"}


def fnum(v):
    try:
        x = float(v)
        return None if math.isnan(x) else x
    except (TypeError, ValueError):
        return None


def rounded(key, v):
    if key == "precip":
        return round(v, 1) if v < 10 else round(v)
    if key == "ndvi":
        return round(max(v, 0), 2)
    if key == "elev":
        return int(round(v))
    return round(v, 1)


def ice_from_mat(mat):
    return 1 if mat < -2 else (0.5 if mat < 2 else 0)


def apply_practical(s, row):
    """Practical info (not scored): SMAP soil moisture, travel time, protected area."""
    if "smap" in row:
        v = fnum(row.get("smap"))
        s["smap"] = round(v, 3) if v is not None else None
    if "access_min" in row:
        v = fnum(row.get("access_min"))
        s["access_min"] = int(round(v)) if v is not None and v >= 0 else None
    if "protected" in row:
        s["protected"] = (row.get("protected") or "").strip()


def apply_sites(sites, path, radius_km):
    by_id = {s["id"]: s for s in sites}
    updated, missing = 0, []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            s = by_id.get(row.get("id"))
            if not s:
                continue
            vals = {k: fnum(row.get(k)) for k in NUM}
            gaps = [k for k, v in vals.items() if v is None]
            for k, v in vals.items():
                if v is not None:
                    s[k] = rounded(k, v)
            if vals["mat"] is not None:
                # keep a catalogued permafrost flag; otherwise use the temperature proxy
                s["ice"] = max(s.get("ice", 0), ice_from_mat(vals["mat"]))
            s["source"] = "gee" if not gaps else "mixed"
            apply_practical(s, row)
            s["radius_km"] = radius_km
            if gaps:
                missing.append(f"{s['id']} (kept estimates for {', '.join(gaps)})")
            updated += 1
    return updated, missing


def apply_candidates(sites, path, top):
    added = []
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    rows.sort(key=lambda r: fnum(r.get("match")) or 0, reverse=True)
    for r in rows:
        if len(added) >= top:
            break
        if (r.get("near_listed_site") or "").strip():
            continue
        lat, lon = fnum(r.get("lat")), fnum(r.get("lon"))
        vals = {k: fnum(r.get(k)) for k in NUM}
        if lat is None or lon is None or any(v is None for v in vals.values()):
            continue
        # skip a candidate within 50 km of one already added
        if any(abs(c["lat"] - lat) < 0.45 and abs(c["lon"] - lon) < 0.45 for c in sites):
            continue
        target = r.get("target", "scan")
        lith = r.get("lith_guess") if r.get("lith_guess") in LITH_OK else "sandstone"
        area = fnum(r.get("area_km2")) or 0
        match = fnum(r.get("match")) or 0
        cid = f"scan-{target}-{len(added) + 1}"
        site = {
            "id": cid,
            "name": f"Scan candidate {abs(lat):.2f}°{'N' if lat >= 0 else 'S'}, {abs(lon):.2f}°{'E' if lon >= 0 else 'W'}",
            "region": f"Found by the global scan for {target}",
            "lat": round(lat, 3), "lon": round(lon, 3), "status": "new",
            "lith": [lith], "ice": ice_from_mat(vals["mat"]), "caves": 0, "crater": 0,
            "note": (f"Area of about {area:,.0f} km² that scored {match * 100:.0f}% in the Earth Engine scan. "
                     f"Rock type '{lith}' is a guess from ASTER thermal-infrared indices; caves and craters "
                     f"are not checked yet. Check the location in satellite imagery and the literature."),
            "source": "gee", "radius_km": None,
        }
        for k, v in vals.items():
            site[k] = rounded(k, v)
        apply_practical(site, r)
        sites.append(site)
        added.append(site)
    return added


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html")
    ap.add_argument("--sites")
    ap.add_argument("--candidates", nargs="*", default=[])
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--radius-km", type=float, default=10)
    ap.add_argument("--meta", default=os.path.join(here, "sites_meta.json"))
    ap.add_argument("--permafrost", help="permafrost_summary.json from tools/process_permafrost.py")
    ap.add_argument("--emit", help="emit_summary.json from tools/process_emit.py")
    ap.add_argument("--out", default="analog-finder-updated.html")
    a = ap.parse_args()

    html = open(a.html, encoding="utf-8").read()
    m = re.search(r"/\*SITES_START\*/(.*?)/\*SITES_END\*/", html, re.S)
    if not m:
        sys.exit("Could not find the SITES block in the HTML (missing /*SITES_START*/ marker).")
    sites = json.load(open(a.meta, encoding="utf-8"))

    if a.sites:
        n, missing = apply_sites(sites, a.sites, a.radius_km)
        print(f"Updated {n} of {len(sites)} sites from {os.path.basename(a.sites)}")
        for s in missing:
            print("  partial:", s)
    for path in a.candidates:
        added = apply_candidates(sites, path, a.top)
        print(f"Added {len(added)} new candidates from {os.path.basename(path)}")
        for s in added:
            print(f"  {s['name']}  ({s['lith'][0]})")

    if a.permafrost:
        pf = json.load(open(a.permafrost, encoding="utf-8"))
        for s in sites:
            v = pf.get(s["id"])
            pfr = v.get("pfr") if v else None
            if pfr is None:
                # outside the ESA CCI maps (25N-85N, 60S-85S) or no permafrost pixels: none
                pfr = 0.0
            s["pfr"] = pfr
            s["ice"] = 1 if pfr >= 50 else 0.5 if pfr >= 10 else 0
            s["ice_source"] = "ESA CCI Permafrost v5.0 (2023)"
        print(f"Applied ESA CCI permafrost to {len(sites)} sites")

    if a.emit:
        em = json.load(open(a.emit, encoding="utf-8"))
        for s in sites:
            v = em.get(s["id"])
            if not v or v.get("n_2um", 0) < 20:
                continue
            s["emit"] = {"carb": v["carbonate_2um"], "clay": v["clay_2um"], "sulf": v["sulfate_2um"],
                         "n": v["n_2um"], "top": v["top_minerals"]}
            # EMIT-confirmed families: carbonate >= 50 % or sulfate >= 20 % of 2-um detections.
            # (Clay and iron-oxide signals are present in almost all desert dust, so they are not used.)
            confirmed = []
            if v["carbonate_2um"] >= 0.5: confirmed.append("carbonate")
            if v["sulfate_2um"] >= 0.2: confirmed.append("evaporite")
            if s["id"].startswith("scan-"):
                # scan candidates: EMIT replaces the ASTER-based guess
                # basalt and halite-type evaporites have no ~2-um mineral signature, so EMIT cannot
                # overrule them (the "clay" it sees there is dust); it can only add confirmed families
                if "basalt" in s["lith"] or "evaporite" in s["lith"]:
                    s["lith"] = s["lith"] + [c for c in confirmed if c not in s["lith"]]
                else:
                    s["lith"] = confirmed or (["clay"] if v["clay_2um"] >= 0.5 else s["lith"])
            else:
                for c in confirmed:
                    if c not in s["lith"]:
                        s["lith"] = s["lith"] + [c]
        print(f"Applied EMIT minerals to {sum(1 for s in sites if 'emit' in s)} sites")

    block = "/*SITES_START*/" + json.dumps(sites, ensure_ascii=False, indent=1) + "/*SITES_END*/"
    html = html[:m.start()] + block + html[m.end():]
    open(a.out, "w", encoding="utf-8").write(html)
    print("Wrote", a.out)


if __name__ == "__main__":
    main()
