import asyncio, sys, json
from playwright.async_api import async_playwright
async def main(path):
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':1440,'height':1000})
        async def r(route):
            u=route.request.url
            f='/home/claude/vendor2/d3-7.8.5/package/dist/d3.min.js' if 'd3' in u else '/home/claude/vendor2/topojson-3.0.2/package/dist/topojson.min.js'
            await route.fulfill(path=f, content_type='application/javascript')
        await pg.route('https://cdnjs.cloudflare.com/**', r)
        await pg.route('https://fonts.googleapis.com/**', lambda rt: rt.abort())
        errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('file://'+path); await pg.wait_for_timeout(1500)
        out = await pg.evaluate("""() => TARGETS.map(t => { const r=SITES.map(s=>({n:s.id,m:score(s,t).match,p:score(s,t).potential})); const bm=[...r].sort((a,b)=>b.m-a.m).slice(0,5); const bp=[...r].sort((a,b)=>b.p-a.p).slice(0,3); return t.id+'\\n  match: '+bm.map(x=>x.n+' '+Math.round(x.m*100)).join(', ')+'\\n  new:   '+bp.map(x=>x.n+' '+Math.round(x.p*100)).join(', ')}).join('\\n')""")
        print(out); print('ERRS',errs); await b.close()
asyncio.run(main(sys.argv[1]))
