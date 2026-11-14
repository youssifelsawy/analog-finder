#!/usr/bin/env python3
"""
process_permafrost.py - permafrost fraction at each site from ESA CCI Permafrost (v5.0) NetCDF files.

Usage: python3 process_permafrost.py sites_meta.json PFR_northern_hemisphere.nc [PFR_antarctica.nc]

Each file holds variable PFR (permafrost area fraction, %) on a polar-stereographic grid
(~1 km). For each site, the median PFR within ~10 km is taken from whichever file covers it.
Output: permafrost_summary.json {site_id: {"pfr": percent, "zone": IPA zone, "ice": 0/0.5/1}}

IPA zones: continuous 90-100 %, discontinuous 50-90 %, sporadic 10-50 %, isolated 0-10 %.
Mapped to the map's ground-ice factor: >=50 % -> 1, 10-50 % -> 0.5, <10 % -> 0.
"""
import json, math, sys
import numpy as np
import xarray as xr
from pyproj import CRS, Transformer

RADIUS_M = 10000


def grid_crs(ds, var):
    gm = ds[var].attrs.get("grid_mapping")
    if gm and gm in ds:
        try:
            return CRS.from_cf(ds[gm].attrs)
        except Exception:
            pass
    for name in ("polar_stereographic", "spatial_ref", "crs"):
        if name in ds:
            try:
                return CRS.from_cf(ds[name].attrs)
            except Exception:
                continue
    # sensible defaults by hemisphere
    return CRS.from_epsg(3995 if float(ds["y"].max()) > 0 or "north" in str(ds.attrs).lower() else 3031)


def zone(p):
    if p is None:
        return None
    return "continuous" if p >= 90 else "discontinuous" if p >= 50 else "sporadic" if p >= 10 else "isolated or none"


def main(meta_path, nc_paths):
    sites = json.load(open(meta_path, encoding="utf-8"))
    grids, geo = [], []
    for p in nc_paths:
        ds = xr.open_dataset(p)
        var = "PFR" if "PFR" in ds else [v for v in ds.data_vars if ds[v].ndim >= 2][0]
        da = ds[var]
        if "time" in da.dims:
            da = da.isel(time=-1)
        if "lat" in da.dims and "lon" in da.dims:
            geo.append(da.sortby("lat"))
            continue
        crs = grid_crs(ds, var)
        xs, ys = ds["x"].values, ds["y"].values
        grids.append((p, da.values.astype(float), xs, ys, Transformer.from_crs(4326, crs, always_xy=True)))
    out = {}
    for s in sites:
        best = None
        for gds in geo:   # regular lat/lon grids (CCI v5.0)
            lat_lo, lat_hi = float(gds.lat.min()), float(gds.lat.max())
            if not (lat_lo <= s["lat"] <= lat_hi):
                continue
            dlat = RADIUS_M / 111320.0
            dlon = dlat / max(0.05, math.cos(math.radians(s["lat"])))
            sub = gds.sel(lat=slice(s["lat"] - dlat, s["lat"] + dlat),
                          lon=slice(s["lon"] - dlon, s["lon"] + dlon)).values.astype(float)
            sub = sub[np.isfinite(sub)]
            sub = sub[(sub >= 0) & (sub <= 100)]
            if sub.size:
                best = float(np.median(sub))
                break
        for p, arr, xs, ys, tr in grids:
            if best is not None:
                break
            x, y = tr.transform(s["lon"], s["lat"])
            if not (min(xs) <= x <= max(xs) and min(ys) <= y <= max(ys)):
                continue
            ix = np.where(np.abs(xs - x) <= RADIUS_M)[0]
            iy = np.where(np.abs(ys - y) <= RADIUS_M)[0]
            if len(ix) == 0 or len(iy) == 0:
                continue
            win = arr[np.ix_(iy, ix)] if arr.shape == (len(ys), len(xs)) else arr[np.ix_(ix, iy)].T
            win = win[np.isfinite(win)]
            if win.size:
                best = float(np.median(win))
                break
        if best is not None and best > 100:   # some files store 0-1 fractions scaled differently
            best = min(best, 100.0)
        ice = None if best is None else (1 if best >= 50 else 0.5 if best >= 10 else 0)
        out[s["id"]] = {"pfr": None if best is None else round(best, 1), "zone": zone(best), "ice": ice}
        print(f"{s['id']:20s} {('%.0f %%' % best) if best is not None else 'outside map':>12s}  {zone(best) or ''}")
    json.dump(out, open("permafrost_summary.json", "w"), indent=1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
