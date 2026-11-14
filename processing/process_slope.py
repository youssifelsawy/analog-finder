#!/usr/bin/env python3
"""
process_slope.py - mean slope of a Moon or Mars elevation tile, measured the same way as on Earth.

Usage: python3 process_slope.py <target-id> <dem.tif> [--body moon|mars] [--is-slope]

The Earth sites use slope from a DEM averaged to ~250 m pixels, so planetary DEMs are
block-averaged to the nearest whole multiple of their pixel size that is >= 250 m before slope
is computed. Geographic (degree) grids are converted to metres with the body's radius.
--is-slope: the file is already a slope map in degrees (e.g. the USGS Jezero CTX slope map);
its pixels are averaged directly.

Prints mean slope (degrees) and the map's relief value (mean slope / 20, capped at 1),
and appends the result to target_slopes.json.
"""
import json, math, sys, os
import numpy as np
import rasterio

RADIUS_M = {"moon": 1737400.0, "mars": 3396190.0}
TARGET_RES_M = 250.0


def main(target, path, body, is_slope):
    with rasterio.open(path) as src:
        z = src.read(1).astype(float)
        if src.nodata is not None:
            z[z == src.nodata] = np.nan
        z[np.abs(z) > 1e6] = np.nan
        a = src.transform
        px_x, px_y = abs(a.a), abs(a.e)
        geographic = src.crs is None or src.crs.is_geographic or px_x < 0.5   # degrees, not metres
        if geographic:
            lat0 = a.f + a.e * src.height / 2
            m_per_deg = math.pi * RADIUS_M[body] / 180
            px_x *= m_per_deg * math.cos(math.radians(lat0))
            px_y *= m_per_deg
    if is_slope:
        slope = z
        note = "precomputed slope map"
    else:
        k = max(1, int(round(TARGET_RES_M / max(px_x, px_y))))
        if k > 1:   # block-average to ~250 m like the Earth DEM
            h, w = (z.shape[0] // k) * k, (z.shape[1] // k) * k
            z = np.nanmean(z[:h, :w].reshape(h // k, k, w // k, k), axis=(1, 3))
        gy, gx = np.gradient(z, px_y * k, px_x * k)
        slope = np.degrees(np.arctan(np.hypot(gx, gy)))
        note = f"DEM {px_x:.0f} m pixels, slope at {px_x * k:.0f} m"
    mean = float(np.nanmean(slope))
    relief = round(min(1.0, mean / 20), 2)
    print(f"{target}: mean slope {mean:.1f} deg -> relief {relief}  ({note})")
    out = json.load(open("target_slopes.json")) if os.path.exists("target_slopes.json") else {}
    out[target] = {"mean_slope_deg": round(mean, 1), "relief": relief, "file": os.path.basename(path), "note": note}
    json.dump(out, open("target_slopes.json", "w"), indent=1)


if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    body = "moon" if args[0].startswith("moon") else "mars"
    if "--body" in sys.argv:
        body = sys.argv[sys.argv.index("--body") + 1]
        args = [x for x in args if x != body]
    main(args[0], args[1], body, "--is-slope" in sys.argv)
