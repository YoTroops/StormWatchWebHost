"""Isolated browser regressions for mobile interactions; all provider data is MOCKED."""
import asyncio, json, pathlib, re, io
from PIL import Image
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
WEB=ROOT/'apps/web/dist'

def png():
 b=io.BytesIO();Image.new('RGB',(128,128),(20,51,66)).save(b,'PNG');return b.getvalue()

async def main():
 fixture=json.loads((ROOT/'data/fixtures/milton_advisories.json').read_text())
 data={'coasts':json.loads((WEB/'coastlines.json').read_text()),'lands':json.loads((WEB/'landpolygons.json').read_text()),
 'archive':{'storms':[{'id':fixture['id'],'name':'MILTON','year':2024,'basin':'Atlantic','dataset':fixture['dataset'],'point_count':len(fixture['points'])}]},
 'detail':fixture,'live':{'availability':'AVAILABLE','checked_utc':'2026-10-15T04:00:00Z','storms':[]},
 'satellite':{'quality':'UNAVAILABLE'},'radar':{'quality':'UNAVAILABLE'},'recon':{'quality':'UNAVAILABLE'},
 'aircraft':{'quality':'UNAVAILABLE','aircraft':[]},'satmap':{'quality':'UNAVAILABLE'}}
 html=(WEB/'index.html').read_text()
 html=re.sub(r'@import\s+url\([^)]*\);','',html)
 mock=f'''<script>const MOCK_DATA={json.dumps(data)};
 window.fetch=async function(url){{let p=String(url),v;
 if(p.includes('coastlines.json'))v=MOCK_DATA.coasts;
 else if(p.includes('landpolygons.json'))v=MOCK_DATA.lands;
 else if(p.includes('/api/storms/historical/'))v=MOCK_DATA.detail;
 else if(p.includes('/api/storms/historical'))v=MOCK_DATA.archive;
 else if(p.includes('/api/storms/live'))v=MOCK_DATA.live;
 else if(p.includes('/api/satellite/map/status'))v=MOCK_DATA.satmap;
 else if(p.includes('/api/satellite/latest'))v=MOCK_DATA.satellite;
 else if(p.includes('/api/radar/status'))v=MOCK_DATA.radar;
 else if(p.includes('/api/aircraft/noaa'))v=MOCK_DATA.aircraft;
 else if(p.includes('/api/recon/status'))v=MOCK_DATA.recon;
 else v={{status:'ok'}};
 return {{ok:true,status:200,json:async()=>v,text:async()=>JSON.stringify(v)}};}};
 window.WebSocket=function(){{this.close=()=>{{}};}};</script>'''
 for name in ['app','release-notes','mobile']:
  html=re.sub(fr'<script src="/static/{name}\.js\?[^" ]+" defer></script>',lambda m: mock+'<script>'+(WEB/(name+'.js')).read_text()+'</script>' if name=='app' else '<script>'+(WEB/(name+'.js')).read_text()+'</script>',html)
 css=(WEB/'mobile.css').read_text()
 html=html.replace('<link rel="stylesheet" href="/static/mobile.css?v=093"/>','<style>'+css+'</style>')
 html=html.replace('<link rel="stylesheet" href="/static/style.css?v=20261015-ui9"/>','')
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage','--disable-features=MediaRouter'])
  for width,height in [(390,844),(375,667),(320,640),(1440,900)]:
   context=await browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,is_mobile=width<800,has_touch=width<800)
   page=await context.new_page()
   errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
   await page.evaluate("""Object.defineProperty(window,'localStorage',{configurable:true,value:{getItem:()=> '0.9.3',setItem:()=>{}}})""")
   await page.route('https://tile.openstreetmap.org/**',lambda route:route.fulfill(status=200,body=png(),content_type='image/png'))
   await page.set_content(html,wait_until='domcontentloaded')
   await page.wait_for_timeout(850)
   if width<800:
    assert await page.locator('.mobile-nav').is_visible(),f'nav absent {width}'
    assert not await page.locator('.leftsidebar').is_visible(),f'left sidebar shown at map {width}'
    assert await page.locator('#earthCanvas').is_visible(),f'map invisible {width}'
    box=await page.locator('#mapArea').bounding_box()
    assert box['height']>260,(width,box)
    assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'),f'horizontal overflow {width}'
    await page.locator('.mobile-nav-button[data-panel="storms"]').click()
    await page.locator('.leftsidebar').wait_for(state='visible',timeout=1500)
    await page.locator('.mobile-nav-button[data-panel="weather"]').click()
    assert await page.locator('#workspace-weather').is_visible(),f'weather workspace not open {width}'
    await page.locator('.mobile-nav-button[data-panel="map"]').click()
    await page.locator('.leftsidebar').wait_for(state='hidden',timeout=1500)
    await page.locator('.mobile-replay-toggle').click()
    assert await page.locator('.timeline').is_visible(),f'replay absent {width}'
    await page.locator('.mobile-replay-toggle').click()
    assert not await page.locator('.timeline').is_visible()
    await page.locator('#archiveMode').click()
    assert not await page.locator('.mobile-nav-button[data-panel="weather"]').is_visible()
    assert not await page.locator('.mobile-nav-button[data-panel="models"]').is_visible()
    await page.locator('.mobile-nav-button[data-panel="storms"]').click()
    await page.locator('.leftsidebar').wait_for(state='visible',timeout=1500)
    await page.locator('.mobile-nav-button[data-panel="map"]').click()
    await page.locator('.mobile-nav-button[data-panel="info"]').click()
    await page.locator('.rightsidebar').wait_for(state='visible',timeout=1500)
    await page.locator('.mobile-sheet-close').last.click()
    await page.locator('.rightsidebar').wait_for(state='hidden',timeout=1500)
    if width==390:
     await page.locator('#liveMode').click()
     await page.screenshot(path=str(ROOT/'docs/stormwatch_v093_mobile_mock.png'))
   else:
    assert not await page.locator('.mobile-nav').is_visible()
    await page.locator('.leftsidebar').wait_for(state='visible',timeout=1500)
    assert await page.locator('.rightsidebar').is_visible()
   assert not errors,(width,errors[:5])
   print('PASS',width,'x',height,'map height', (await page.locator('#mapArea').bounding_box())['height'],'errors',len(errors))
   await context.close()
  await browser.close()
if __name__=='__main__': asyncio.run(main())
