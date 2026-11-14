#!/usr/bin/env python3
"""
process_mola.py - mean slope around Mars targets from MOLA MEGDR 128 pixel/degree tiles.

Usage: python3 process_mola.py megt44n000hb.img [more .img ...]

Tiles (PDS: mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/): 5632 lines x 11520 samples,
16-bit big-endian integers, metres above the areoid, 128 px/deg (~463 m), simple cylindrical.
Name megtLLXlllhb: LL = northern edge (88n, 44n, 00n, 44s), lll = western edge (east longitude).

For each target inside a tile, a 20 x 20 km window is cut out and slope is computed at the
native ~463 m spacing (the closest MOLA gets to the 250 m used on Earth). Writes target_slopes.json.
"""
import json, math, os, re, sys
import numpy as np

R = 3396000.0
PPD = 128
LINES, SAMPLES = 5632, 11520
TARGETS = {"mars-jezero": (18.44, 77.45), "mars-gale": (-5.4, 137.8), "mars-arcadia": (40.0, 200.0),
           "mars-arsia": (-8.26, 239.91), "mars-meridiani": (-1.95, 354.5)}
HALF_KM = 10.0


def tile_bounds(name):
    m = re.search(r"megt(\d\d)([ns])(\d{3})", name.lower())
    if not m:
        sys.exit(f"Not a MEGDR tile name: {name}")
    top = int(m.group(1)) * (1 if m.group(2) == "n" else -1)
    west = int(m.group(3))
    return top, top - 44, west, west + 90


def main(paths):
    out = json.load(open("target_slopes.json")) if os.path.exists("target_slopes.json") else {}
    for p in paths:
        top, bottom, west, east = tile_bounds(os.path.basename(p))
        z = np.memmap(p, dtype=">i2", mode="r", shape=(LINES, SAMPLES))
        for tid, (lat, lon) in TARGETS.items():
            lon = lon % 360
            if not (bottom <= lat <= top and west <= lon < east):
                continue
            r0, c0 = int((top - lat) * PPD), int((lon - west) * PPD)
            dy = R * math.radians(1 / PPD)                       # metres per line
            dx = dy * math.cos(math.radians(lat))                # metres per sample
            hr, hc = int(HALF_KM * 1000 / dy), int(HALF_KM * 1000 / dx)
            win = np.array(z[max(0, r0 - hr):r0 + hr + 1, max(0, c0 - hc):c0 + hc + 1], dtype=float)
            gy, gx = np.gradient(win, dy, dx)
            slope = np.degrees(np.arctan(np.hypot(gx, gy)))
            mean = float(np.mean(slope))
            out[tid] = {"mean_slope_deg": round(mean, 2), "relief": round(min(1, mean / 20), 3),
                        "elev_m": round(float(np.mean(win))), "pixel_m": round(dy),
                        "file": os.path.basename(p), "note": "MOLA MEGDR 128 px/deg, 20 x 20 km"}
            print(f"{tid:16s} mean slope {mean:5.2f} deg  relief {min(1, mean/20):.3f}  "
                  f"mean elevation {np.mean(win):7.0f} m  ({win.shape[0]}x{win.shape[1]} px)")
    json.dump(out, open("target_slopes.json", "w"), indent=1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
