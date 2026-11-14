#!/usr/bin/env python3
"""plot_match.py - slide figure from an Earth Engine match GeoTIFF (analog_match_<target>.tif).

Usage: python3 plot_match.py match.tif "Title" out.png [--sites sites_meta.json] [--extent W E S N]
"""
import argparse, json
import numpy as np
import rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

BG, LAND, TEXT, MUTED = "#0d141c", "#1d2a37", "#e4e9ef", "#8c9bad"
CMAP = LinearSegmentedColormap.from_list("match", ["#22303f", "#4a4a52", "#9c5a3a", "#e3804f", "#ffe1b8"])

ap = argparse.ArgumentParser()
ap.add_argument("tif"); ap.add_argument("title"); ap.add_argument("out")
ap.add_argument("--sites"); ap.add_argument("--extent", nargs=4, type=float)
ap.add_argument("--subtitle", default="")
a = ap.parse_args()

with rasterio.open(a.tif) as src:
    z = src.read(1).astype(float)
    if src.nodata is not None:
        z[z == src.nodata] = np.nan
    b = src.bounds
extent = [b.left, b.right, b.bottom, b.top]
valid = np.isfinite(z)
top = np.nanpercentile(z, 99.5)

fig, ax = plt.subplots(figsize=(16, 8.2), dpi=150)
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
land = np.where(valid, 1.0, np.nan)
ax.imshow(land, extent=extent, cmap=LinearSegmentedColormap.from_list("l", [LAND, LAND]), interpolation="nearest")
im = ax.imshow(z, extent=extent, cmap=CMAP, vmin=0.4, vmax=max(0.85, top + 0.02), interpolation="nearest")
ax.contour(np.where(valid, z, 0) >= top, levels=[0.5], extent=[b.left, b.right, b.top, b.bottom],
           colors="#5cc8a8", linewidths=0.9)
if a.sites:
    sites = json.load(open(a.sites, encoding="utf-8"))
    xs = [s["lon"] for s in sites]; ys = [s["lat"] for s in sites]
    ax.scatter(xs, ys, s=14, c="white", edgecolors=BG, linewidths=0.6, zorder=5, label="Listed sites")
if a.extent:
    ax.set_xlim(a.extent[0], a.extent[1]); ax.set_ylim(a.extent[2], a.extent[3])
else:
    ax.set_xlim(-180, 180); ax.set_ylim(-60, 82)
ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values():
    s.set_visible(False)
fig.text(0.02, 0.955, a.title, color=TEXT, fontsize=20, fontweight="bold", ha="left", va="top")
fig.text(0.02, 0.905, a.subtitle or f"Match score per 5 km pixel · green outline = top 0.5% of land (≥ {top:.2f})",
         color=MUTED, fontsize=11.5, ha="left", va="top")
cax = fig.add_axes([0.70, 0.915, 0.27, 0.018])
cb = fig.colorbar(im, cax=cax, orientation="horizontal")
cb.set_label("Match", color=MUTED, fontsize=10); cb.ax.tick_params(colors=MUTED, labelsize=9)
cb.outline.set_visible(False)
fig.text(0.98, 0.02, "Data: NASA MODIS, ASTER, GPM; TerraClimate; USGS GMTED2010; ESA Copernicus DEM · Analog Finder",
         color=MUTED, fontsize=8.5, ha="right")
plt.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.04)
fig.savefig(a.out, facecolor=BG)
print("saved", a.out, "top-0.5% threshold", round(top, 3))
