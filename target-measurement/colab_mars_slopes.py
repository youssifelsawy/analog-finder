# Analog Finder - Mars target slopes from NASA MOLA (paste this whole cell into Google Colab and run it)
# Downloads 5 MOLA MEGDR tiles (128 px/deg, ~463 m) from the NASA Planetary Data System, ~130 MB each,
# and measures the mean slope in a 20 x 20 km box around each Mars target.
import os, math, json, urllib.request
import numpy as np

BASE = "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg128/"
R, PPD, LINES, SAMPLES, HALF_KM = 3396000.0, 128, 5632, 11520, 10.0
TARGETS = {  # target: (lat, east lon, tile)
    "mars-jezero":    (18.44,  77.45,  "megt44n000hb.img"),
    "mars-gale":      (-5.40, 137.80,  "megt00n090hb.img"),
    "mars-arcadia":   (40.00, 200.00,  "megt44n180hb.img"),
    "mars-arsia":     (-8.26, 239.91,  "megt00n180hb.img"),
    "mars-meridiani": (-1.95, 354.50,  "megt00n270hb.img"),
}

def tile_bounds(name):
    top = int(name[4:6]) * (1 if name[6] == "n" else -1)
    west = int(name[7:10])
    return top, top - 44, west

results = {}
for tid, (lat, lon, tile) in TARGETS.items():
    if not os.path.exists(tile):
        print("downloading", tile, "...")
        urllib.request.urlretrieve(BASE + tile, tile)
    top, bottom, west = tile_bounds(tile)
    z = np.memmap(tile, dtype=">i2", mode="r", shape=(LINES, SAMPLES))
    r0, c0 = int((top - lat) * PPD), int((lon - west) * PPD)
    dy = R * math.radians(1 / PPD); dx = dy * math.cos(math.radians(lat))
    hr, hc = int(HALF_KM * 1000 / dy), int(HALF_KM * 1000 / dx)
    win = np.array(z[r0 - hr:r0 + hr + 1, c0 - hc:c0 + hc + 1], dtype=float)
    gy, gx = np.gradient(win, dy, dx)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    results[tid] = {"mean_slope_deg": round(float(slope.mean()), 2),
                    "relief": round(min(1, float(slope.mean()) / 20), 3),
                    "elev_m": round(float(win.mean())), "window_px": list(win.shape)}
    print(f"{tid:16s} mean slope {slope.mean():5.2f} deg   mean elevation {win.mean():7.0f} m")

print("\nCOPY EVERYTHING BELOW THIS LINE AND SEND IT BACK:")
print(json.dumps(results))
