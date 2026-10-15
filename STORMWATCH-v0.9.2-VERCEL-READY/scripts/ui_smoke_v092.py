"""Full v0.9.2 browser check using mocked provider data; no live source claims."""
import asyncio,io,json,pathlib,re
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
WEB=ROOT/'apps/web/dist'

def png(w=256,h=256):
 im=Image.new('RGB',(w,h),(22,59,78));d=ImageDraw.Draw(im);d.text((max(4,w//5),max(4,h//2)),'MOCK IMAGE - NOT LIVE',fill='white');o=io.BytesIO();im.save(o,'PNG');return o.getvalue()

async def main():
 fixture=json.loads((ROOT/'data/fixtures/milton_advisories.json').read_text())
 data={'coasts':json.loads((WEB/'coastlines.json').read_text()),'lands':json.loads((WEB/'landpolygons.json').read_text()),
  'archive':{'storms':[{'id':fixture['id'],'name':'MILTON','year':2024,'basin':'Atlantic','dataset':fixture['dataset'],'point_count':len(fixture['points'])}]},'detail':fixture,
  'live':{'availability':'AVAILABLE','checked_utc':'2026-10-14T20:00:00Z','storms':[]},
  'satellite':{'quality':'DELAYED','channel':'GEOCOLOR','channel_label':'GeoColor','image_url':'https://cdn.star.nesdis.noaa.gov/GOES19/ABI/CONUS/GEOCOLOR/20262871955_GOES19-ABI-CONUS-GEOCOLOR-1250x750.jpg','observed_utc':'2026-10-14T19:55:00Z','checked_utc':'2026-10-14T20:00:00Z'},
  'radar':{'quality':'UNAVAILABLE'},'recon':{'quality':'UNAVAILABLE'},'aircraft':{'quality':'AVAILABLE','aircraft':[]},'satmap':{'quality':'UNAVAILABLE'}}
 html=(WEB/'index.html').read_text(encoding='utf-8');html=re.sub(r'@import\s+url\([^)]*\);','',html)
 js=(WEB/'app.js').read_text(encoding='utf-8');release=(WEB/'release-notes.js').read_text(encoding='utf-8')
 mock=f'''<script>const MOCK_DATA={json.dumps(data)};
 window.fetch=async function(url,options){{let p=String(url),v;
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
 window.WebSocket=function(){{this.close=()=>{{}};}};</script><script>{js}</script>'''
 html=re.sub(r'<script src="/static/app.js\?[^" ]+" defer></script>',lambda m:mock,html)
 html=re.sub(r'<script src="/static/release-notes.js\?[^" ]+" defer></script>',lambda m:'<script>'+release+'</script>',html)
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
  context=await browser.new_context(viewport={'width':1480,'height':900},device_scale_factor=1)
  page=await context.new_page(); errs=[];page.on('pageerror',lambda e:errs.append(str(e)))
  # Browser security policy prevents local URL navigation; exercise DOM with set_content.
  # about:blank disallows localStorage, so provide a storage shim for this isolated test.
  await page.evaluate("""window.releaseStore={};Object.defineProperty(window,'localStorage',{configurable:true,value:{getItem:k=>window.releaseStore[k]??null,setItem:(k,v)=>{window.releaseStore[k]=v}}});""")
  await page.route('https://tile.openstreetmap.org/**',lambda r:r.fulfill(status=200,content_type='image/png',body=png()))
  await page.route('https://cdn.star.nesdis.noaa.gov/**',lambda r:r.fulfill(status=200,content_type='image/png',body=png(1250,750)))
  await page.set_content(html,wait_until='domcontentloaded')
  assert await page.locator('#releaseDialogBackdrop').is_visible()
  assert await page.locator('#releaseDialogTitle').inner_text()=='STORMWATCH v0.9.2'
  assert await page.locator('.release-change').count()==3
  assert await page.locator('#releaseHistoryList details').count()==8
  assert await page.locator('#releaseDialogBackdrop').evaluate('(d)=>getComputedStyle(d).zIndex')=='100'
  assert await page.locator('#app').evaluate('(d)=>d.inert') is True
  await page.screenshot(path=str(ROOT/'docs/stormwatch_v092_welcome_mock.png'))
  await page.locator('#releaseHistoryList details').first.locator('summary').click()
  assert await page.locator('#releaseHistoryList details').first.evaluate('(d)=>d.open') is True
  await page.locator('#releaseEnter').click()
  assert not await page.locator('#releaseDialogBackdrop').is_visible()
  assert await page.locator('#app').evaluate('(d)=>d.inert') is False
  assert await page.evaluate('localStorage.getItem("stormwatch.releaseNotes.dismissedVersion")')=='0.9.2'
  await page.locator('#openReleaseNotes').click()
  assert await page.locator('#releaseDialogBackdrop').is_visible()
  assert await page.evaluate('document.activeElement.id')=='releaseDialogClose'
  await page.keyboard.press('Escape')
  assert not await page.locator('#releaseDialogBackdrop').is_visible()
  assert await page.evaluate('document.activeElement.id')=='openReleaseNotes'
  # Simulate a new browser visit with stored version, without local network access.
  for seen_version, should_open in [('0.9.2',False),('0.9.0',True)]:
   p2=await context.new_page()
   p2.on('pageerror',lambda e:errs.append(str(e)))
   await p2.evaluate('''(stored) => {window.releaseStore={'stormwatch.releaseNotes.dismissedVersion':stored}; Object.defineProperty(window,'localStorage',{configurable:true,value:{getItem:k=>window.releaseStore[k]??null,setItem:(k,v)=>{window.releaseStore[k]=v}}});}''',seen_version)
   await p2.set_content(html,wait_until='domcontentloaded')
   assert (await p2.locator('#releaseDialogBackdrop').is_visible()) is should_open
   await p2.close()
  # Verify underlying interface still works including archive cleanup.
  await page.locator('#archiveMode').click()
  assert not await page.locator('[data-workspace-tab="weather"]').is_visible()
  assert not await page.locator('[data-workspace-tab="models"]').is_visible()
  await page.locator('#liveMode').click()
  assert await page.locator('[data-workspace-tab="weather"]').is_visible()
  await page.locator('#openReleaseNotes').click()
  await page.set_viewport_size({'width':640,'height':700})
  dimensions=await page.locator('.release-dialog').bounding_box()
  assert dimensions['height'] <= 700 and dimensions['width'] <= 640,dimensions
  assert not errs,errs
  print('PASS: first launch, 8 prior changelogs, dismissal persistence, manual reopen, Escape and focus, version upgrade, archive/live, responsive, JS errors:',len(errs))
  await browser.close()

if __name__=='__main__':asyncio.run(main())
