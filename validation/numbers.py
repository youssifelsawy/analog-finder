import asyncio, json
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width':1600,'height':1000}, device_scale_factor=2)
        async def r(route):
            u=route.request.url
            f='/home/claude/vendor2/d3-7.8.5/package/dist/d3.min.js' if 'd3' in u else '/home/claude/vendor2/topojson-3.0.2/package/dist/topojson.min.js'
            await route.fulfill(path=f, content_type='application/javascript')
        await pg.route('https://cdnjs.cloudflare.com/**', r)
        await pg.route('https://fonts.googleapis.com/**', lambda rt: rt.abort())
        await pg.goto('file:///home/claude/real/analog-finder-v19.html'); await pg.wait_for_timeout(1500)
        res = await pg.evaluate("""() => { const out={};
          TARGETS.forEach(t => { const r=SITES.map(s=>({id:s.id,name:s.name,st:s.status,m:Math.round(score(s,t).match*100)})).sort((a,b)=>b.m-a.m);
            out[t.id]={top:r.slice(0,6), bestNew:r.find(x=>x.st==='new'), all:Object.fromEntries(r.map(x=>[x.id,x.m]))}; });
          out.access = Object.fromEntries(SITES.map(s=>[s.id,[s.access_min, s.protected]])); return out; }""")
        json.dump(res, open('real/final_numbers_v19.json','w'), indent=1)
        await pg.screenshot(path='/tmp/map_tool_v19.png')
        await b.close()
asyncio.run(main())
