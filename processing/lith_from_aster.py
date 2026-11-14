"""Rock type from ASTER indices (qi, ci, mi) with the same rule as the Earth Engine scan:
each class's fingerprint = mean indices of listed (non-scan) sites whose main rock is that class;
distance scaled by the SD across those sites; the most similar class wins.
Usage: python3 lith_from_aster.py sites.csv sites_meta.json id1 id2 ..."""
import csv, json, math, sys
rows={r['id']:r for r in csv.DictReader(open(sys.argv[1]))}
meta=json.load(open(sys.argv[2])); meta=meta if isinstance(meta,list) else meta['sites']
lith={m['id']:m['lith'][0] for m in meta if m.get('lith')}
def f(r,k):
    try: return float(r[k])
    except: return None
ref=[r for i,r in rows.items() if not i.startswith('scan-') and i in lith and all(f(r,k) is not None for k in ('qi','ci','mi'))]
def sd(k):
    v=[f(r,k) for r in ref]; m=sum(v)/len(v); return math.sqrt(sum((x-m)**2 for x in v)/len(v))
SD={k:sd(k) for k in ('qi','ci','mi')}
classes={}
for r in ref: classes.setdefault(lith[r['id']],[]).append(r)
FP={c:{k:sum(f(r,k) for r in L)/len(L) for k in ('qi','ci','mi')} for c,L in classes.items()}
out={}
for i in sys.argv[3:]:
    r=rows[i]
    if any(f(r,k) is None for k in ('qi','ci','mi')): out[i]=None; continue
    sims={c:math.exp(-0.5*sum(((f(r,k)-fp[k])/SD[k])**2 for k in fp)/3) for c,fp in FP.items()}
    best=sorted(sims.items(),key=lambda x:-x[1])
    out[i]={'lith':best[0][0],'sim':round(best[0][1],3),'second':best[1][0],'sim2':round(best[1][1],3)}
print(json.dumps(out,indent=1))
