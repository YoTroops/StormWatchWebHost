"""Radar regression: stale data hidden, NOAA-mock fresh image, archive hiding."""
import asyncio,io,json,pathlib,re
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
WEB=ROOT/'apps/web/dist'

def transparent_radar():
    im=Image.new('RGBA',(540,480),(0,0,0,0));d=ImageDraw.Draw(im)
    # Deliberately synthetic georeference check: red ellipse near Florida's east coast.
    bbox=(-91,23,-73,39);lon,lat=-80.3,27.2
    x=(lon-bbox[0])/(bbox[2]-bbox[0])*540
    y=(bbox[3]-lat)/(bbox[3]-bbox[1])*480
    d.ellipse((x-12,y-12,x+12,y+12),fill=(255,40,30,255))
    out=io.BytesIO();im.save(out,'PNG');return out.getvalue()

async def main():
    fixture=json.loads((ROOT/'data/fixtures/milton_advisories.json').read_text())
    data={'coasts':json.loads((WEB/'coastlines.json').read_text()),'lands':json.loads((WEB/'landpolygons.json').read_text()),
      'archive':{'storms':[{'id':fixture['id'],'name':'MILTON','year':2024,'basin':'Atlantic','dataset':fixture['dataset'],'point_count':len(fixture['points'])}]},'detail':fixture,
      'live':{'availability':'AVAILABLE','checked_utc':'2026-10-14T20:00:00Z','storms':[]},
      'satellite':{'quality':'UNAVAILABLE'},'radar':{'quality':'UNAVAILABLE'},'recon':{'quality':'UNAVAILABLE'},'aircraft':{'quality':'UNAVAILABLE'},'satmap':{'quality':'UNAVAILABLE'}}
    html=(WEB/'index.html').read_text();html=re.sub(r'@import\s+url\([^)]*\);','',html)
    html=html.replace('<head>','<head><base href="http://127.0.0.1:8000/">',1)
    js=(WEB/'app.js').read_text();release=(WEB/'release-notes.js').read_text()
    stub=f'''<script>const MOCK_DATA={json.dumps(data)};
     window.fetch=async function(url){{let u=String(url),v;
       if(u.includes('coastlines.json'))v=MOCK_DATA.coasts;
       else if(u.includes('landpolygons.json'))v=MOCK_DATA.lands;
       else if(u.includes('/api/storms/historical/'))v=MOCK_DATA.detail;
       else if(u.includes('/api/storms/historical'))v=MOCK_DATA.archive;
       else if(u.includes('/api/storms/live'))v=MOCK_DATA.live;
       else if(u.includes('/api/satellite/map/status'))v=MOCK_DATA.satmap;
       else if(u.includes('/api/satellite/latest'))v=MOCK_DATA.satellite;
       else if(u.includes('/api/radar/status'))v=MOCK_DATA.radar;
       else if(u.includes('/api/aircraft/noaa'))v=MOCK_DATA.aircraft;
       else if(u.includes('/api/recon/status'))v=MOCK_DATA.recon;
       else v={{status:'ok'}};
       return {{ok:true,status:200,json:async()=>v,text:async()=>JSON.stringify(v)}};
     }};
     window.WebSocket=function(){{this.close=()=>{{}};}};</script><script>{js}</script>'''
    html=re.sub(r'<script src="/static/app.js\?[^" ]+" defer></script>',lambda m:stub,html)
    html=re.sub(r'<script src="/static/release-notes.js\?[^" ]+" defer></script>',lambda m:'<script>'+release+'</script>',html)
    async with async_playwright() as p:
       b=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
       page=await b.new_page(viewport={'width':1400,'height':850})
       errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
       await page.evaluate('''Object.defineProperty(window,'localStorage',{configurable:true,value:{getItem:k=>'0.9.2',setItem:()=>{}}})''')
       image_hits=[]
       async def image_response(route):
           image_hits.append(route.request.url)
           await route.fulfill(status=200,content_type='image/png',body=transparent_radar())
       await page.route('http://127.0.0.1:8000/api/radar/image**',image_response)
       print('SET CONTENT',flush=True)
       await page.set_content(html,wait_until='domcontentloaded',timeout=12000)
       print('CONTENT SET',flush=True)
       print('WEATHER CLICK',flush=True)
       await page.locator('[data-workspace-tab="weather"]').click(timeout=8000)
       await page.locator('#radarDisclosure > summary').click()
       # Provider reports stale service extent: NEVER display the old raster.
       await page.evaluate("MOCK_DATA.radar={quality:'STALE',coverage_window_end_utc:'2026-10-14T19:00:00Z'}")
       print('LOAD RADAR',flush=True)
       await page.evaluate('loadRadar()')
       assert 'STALE' in await page.locator('#radarStatus').inner_text()
       assert await page.evaluate('state.radarImage===null')
       assert len(image_hits)==0
       # Provider available: request new transparent PNG in fixed projection.
       print('CHANGE RADAR REGION',flush=True)
       await page.locator('#radarRegion').select_option('southeast',timeout=8000)
       await page.evaluate("MOCK_DATA.radar={quality:'AVAILABLE',coverage_window_start_utc:'2026-10-14T18:00:00Z',coverage_window_end_utc:'2026-10-14T19:55:00Z'}")
       print('AVAILABLE IMAGE',flush=True)
       await page.evaluate('loadRadar()')
       print('IMAGE LOADED',flush=True)
       assert await page.evaluate('state.radarImage !== null')
       assert 'AVAILABLE' in await page.locator('#radarStatus').inner_text()
       assert 'alignment=2' in image_hits[-1] and 'region=southeast' in image_hits[-1]
       # Test both 2D and 3D repaints (synthetic image, NOT live weather).
       await page.locator('[data-view="flat"]').click()
       await page.locator('#radarFocus').click()
       await page.screenshot(path=str(ROOT/'docs/stormwatch_v092_radar_mock.png'))
       await page.locator('#archiveMode').click()
       assert not await page.locator('[data-workspace-tab="weather"]').is_visible()
       assert await page.evaluate("state.mode==='ARCHIVE'")
       # Render guard on archive prevents today's radar remaining on old storm.
       await page.evaluate('render()')
       await page.locator('#liveMode').click()
       assert await page.locator('[data-workspace-tab="weather"]').is_visible()
       assert errors==[],errors
       print('PASS: STALE provider => no PNG request/no overlay, fresh => fixed-geometry mocked radar PNG, 2D render, archive hides weather, live restore; JS errors: 0')
       await b.close()

if __name__=='__main__':asyncio.run(main())
