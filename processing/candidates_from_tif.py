"""Candidate areas from an Earth Engine match image: top X% of land pixels, joined into 8-connected areas.
Same rule as MODE='scan' in the Earth Engine script. Usage: python3 candidates_from_tif.py match.tif [top_pct] [n]"""
import sys, json, numpy as np, rasterio
from scipy import ndimage
path=sys.argv[1]; pct=float(sys.argv[2]) if len(sys.argv)>2 else 0.5; N=int(sys.argv[3]) if len(sys.argv)>3 else 25
src=rasterio.open(path); a=src.read(1).astype('float64'); T=src.transform
m=np.isfinite(a)&(a>0)
if src.nodata is not None: m&=(a!=src.nodata)
thr=np.percentile(a[m],100-pct); top=m&(a>=thr)
lab,n=ndimage.label(top,structure=np.ones((3,3)))
lat_row=T.f+T.e*(np.arange(a.shape[0])+0.5)
pxkm=(abs(T.a)*111.32*np.cos(np.radians(lat_row)))*(abs(T.e)*110.57)
idx=np.arange(1,n+1)
area=ndimage.sum(np.broadcast_to(pxkm[:,None],a.shape),lab,idx); mean=ndimage.mean(a,lab,idx); mx=ndimage.maximum(a,lab,idx)
pos=ndimage.maximum_position(a,lab,idx)
out=[]
for k in np.argsort(-area)[:N]:
    r,c=pos[k]
    out.append(dict(area_km2=round(float(area[k])),mean=round(float(mean[k]),3),max=round(float(mx[k]),3),
                    best_lat=round(float(T.f+T.e*(r+0.5)),3),best_lon=round(float(T.c+T.a*(c+0.5)),3)))
print(json.dumps(dict(file=path,threshold=round(float(thr),3),land_max=round(float(a[m].max()),3),regions=int(n),top=out),indent=1))
