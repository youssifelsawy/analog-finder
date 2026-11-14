import asyncio, json
from playwright.async_api import async_playwright
JS = r"""
() => {
  const listed = SITES.filter(s => !s.id.startsWith('scan-'));
  const rankOf = (sid, tid, pool) => {
    const t = TARGETS.find(x => x.id === tid);
    const r = pool.map(s => ({id: s.id, m: score(s, t).match})).sort((a, b) => b.m - a.m);
    return {rank: r.findIndex(x => x.id === sid) + 1, n: r.length, m: r.find(x => x.id === sid).m};
  };
  const pairs = [
    ['lanzarote','moon-pit','Lava tubes; ESA PANGAEA cave training'],
    ['hawaii','moon-pit','Lava tubes; lunar regolith tests'],
    ['cotm','moon-pit','Lava tubes; NASA field research'],
    ['lanzarote','mars-arsia','Lava tubes'],
    ['hawaii','mars-arsia','Lava tubes'],
    ['haughton','mars-arcadia','Polar desert with ground ice'],
    ['dryvalleys','mars-arcadia','Cold dry permafrost'],
    ['allanhills','moon-sp','Extreme steady cold, ice'],
    ['atacama','mars-gale','Driest desert, Mars soil tests'],
    ['atacama','mars-meridiani','Driest desert, sulfates'],
    ['riotinto','mars-meridiani','Jarosite and hematite like Meridiani'],
    ['mistastin','moon-high','Anorthosite impact crater'],
    ['meteor','moon-high','Apollo crater training'],
    ['holuhraun','moon-mare','Basalt plains; Apollo geology training'],
    ['haughton','mars-jezero','Impact crater with carbonates']
  ];
  const val = pairs.map(([s,t,why]) => Object.assign({site:s,target:t,why}, rankOf(s,t,listed)));
  // sensitivity: per-factor weight multipliers U(0.5,1.5)
  let seed = 42; const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
  const N = 2000, out = {};
  const checks = {'mars-jezero':'scan-', 'moon-pit':'khaybar', 'moon-sp':'mistastin', 'mars-gale':'atacama', 'mars-meridiani':null, 'mars-arcadia':'allanhills'};
  const counts = {}; Object.keys(checks).forEach(k => counts[k] = {top1:{}, inTop3:{}});
  const scanTop = {top1:0, top5all:0};
  for (let i = 0; i < N; i++) {
    DIMS.forEach(d => state.mult[d.k] = 0.5 + rnd());
    for (const tid of Object.keys(checks)) {
      const t = TARGETS.find(x => x.id === tid);
      const r = SITES.map(s => ({id: s.id, m: score(s, t).match})).sort((a, b) => b.m - a.m);
      counts[tid].top1[r[0].id] = (counts[tid].top1[r[0].id] || 0) + 1;
      r.slice(0,3).forEach(x => counts[tid].inTop3[x.id] = (counts[tid].inTop3[x.id] || 0) + 1);
      if (tid === 'mars-jezero') {
        if (r[0].id.startsWith('scan-')) scanTop.top1++;
        if (r.slice(0,5).every(x => x.id.startsWith('scan-'))) scanTop.top5all++;
        const wd = r.findIndex(x=>x.id==='whitedesert')+1; out.wdRanks = (out.wdRanks||[]); out.wdRanks.push(wd);
      }
    }
  }
  DIMS.forEach(d => state.mult[d.k] = 1);
  const fmt = o => Object.entries(o).sort((a,b)=>b[1]-a[1]).slice(0,5).map(([k,v])=>k+' '+Math.round(v/N*100)+'%').join(', ');
  const sens = Object.keys(checks).map(k => k+'\n   #1: '+fmt(counts[k].top1)+'\n   in top 3: '+fmt(counts[k].inTop3)).join('\n');
  const wd = out.wdRanks.sort((a,b)=>a-b);
  return {val, sens, scanTop1: scanTop.top1/N, scanTop5: scanTop.top5all/N, wdMedian: wd[N/2], wdP5: wd[Math.floor(N*0.05)], wdP95: wd[Math.floor(N*0.95)], n: N};
}
"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        async def r(route):
            u=route.request.url
            f='/home/claude/vendor2/d3-7.8.5/package/dist/d3.min.js' if 'd3' in u else '/home/claude/vendor2/topojson-3.0.2/package/dist/topojson.min.js'
            await route.fulfill(path=f, content_type='application/javascript')
        await pg.route('https://cdnjs.cloudflare.com/**', r)
        await pg.route('https://fonts.googleapis.com/**', lambda rt: rt.abort())
        await pg.goto('file:///home/claude/real/analog-finder-v19.html'); await pg.wait_for_timeout(1200)
        res = await pg.evaluate(JS)
        json.dump(res, open('/home/claude/real/validation_v19.json','w'), indent=1)
        for v in res['val']: print(f"{v['site']:12s} -> {v['target']:15s} rank {v['rank']:2d}/{v['n']}  ({v['m']*100:.0f}%)  {v['why']}")
        print(res['sens']); print('Jezero: scan candidate #1 in', res['scanTop1'], '; top5 all scan in', res['scanTop5'], '; White Desert rank median/5%/95%:', res['wdMedian'], res['wdP5'], res['wdP95'])
        await b.close()
asyncio.run(main())
