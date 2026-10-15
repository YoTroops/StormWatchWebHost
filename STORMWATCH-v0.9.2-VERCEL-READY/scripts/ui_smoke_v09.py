"""Isolated browser verification of v0.9 layout and controls with mocked upstream sources."""
import asyncio,io,json,pathlib,re
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
WEB=ROOT/'apps/web/dist'

def png(w=256,h=256):
 im=Image.new('RGB',(w,h),(20,48,68));d=ImageDraw.Draw(im);d.text((max(4,w//5),max(4,h//2)),'MOCK SOURCE - NOT LIVE',fill='white');o=io.BytesIO();im.save(o,'PNG');return o.getvalue()

async def main():
 f=json.loads((ROOT/'data/fixtures/milton_advisories.json').read_text())
 data={'coasts':json.loads((WEB/'coastlines.json').read_text()),'lands':json.loads((WEB/'landpolygons.json').read_text()),
  'archive':{'storms':[{'id':f['id'],'name':'MILTON','year':2024,'basin':'Atlantic','dataset':f['dataset'],'point_count':len(f['points'])}]},'detail':f,
  'live':{'availability':'AVAILABLE','checked_utc':'2026-10-14T20:00:00Z','storms':[{'id':'AL092026','name':'TEST SYSTEM','basin':'Atlantic','lat':22,'lon':-73,'wind_kt':60,'pressure_hpa':985,'category':1,'quality':'DELAYED','time':'2026-10-14T12:00:00Z','provider':'MOCK NHC'}]},
  'satellite':{'quality':'DELAYED','channel':'GEOCOLOR','channel_label':'GeoColor','image_url':'https://cdn.star.nesdis.noaa.gov/GOES19/ABI/CONUS/GEOCOLOR/20262871955_GOES19-ABI-CONUS-GEOCOLOR-1250x750.jpg','observed_utc':'2026-10-14T19:55:00Z','checked_utc':'2026-10-14T20:00:00Z','source_url':'https://www.nhc.noaa.gov/'},
  'radar':{'quality':'UNAVAILABLE'},'recon':{'quality':'UNAVAILABLE'},'aircraft':{'quality':'AVAILABLE','aircraft':[]},
  'models':{'quality':'AVAILABLE','storm_id':'AL092026','cycle_utc':'2026-10-14T12:00:00Z','available_cycles':['2026-10-14T12:00:00Z'],'available_models':3,'cycle_age_hours':1,'models':[{'id':x,'name':nm,'family':fam,'availability':av,'aid_used':aid,'note':'MOCK DATA','points':[{'tau_hours':t,'lat':22+t/24,'lon':-73-t/24,'wind_kt':60+t/3,'pressure_hpa':985-t/5,'valid_utc':'2026-10-15T12:00:00Z'} for t in (0,24,48)] if av=='AVAILABLE' else []} for (x,nm,fam,av,aid) in [('nhc','NHC Official','official','AVAILABLE','OFCL'),('gfs','GFS','dynamical','AVAILABLE','AVNI'),('google','Google DeepMind','ai','AVAILABLE','GDMI'),('hafsai','HAFS-AI','ai','UNAVAILABLE',None)]]},
  'satmap':{'quality':'UNAVAILABLE'}}
 html=(WEB/'index.html').read_text();html=re.sub(r'@import\s+url\([^)]*\);','',html)
 html=html.replace('<head>','<head><base href="http://127.0.0.1:8000/">',1)
 js=(WEB/'app.js').read_text()
 mock=f'''<script>const MOCK_DATA={json.dumps(data)};
 window.fetch=async function(url,options){{let p=String(url),v;
 if(p.includes('coastlines.json'))v=MOCK_DATA.coasts;
 else if(p.includes('landpolygons.json'))v=MOCK_DATA.lands;
 else if(p.includes('/api/storms/historical/'))v=MOCK_DATA.detail;
 else if(p.includes('/api/storms/historical'))v=MOCK_DATA.archive;
 else if(p.includes('/api/storms/live'))v=MOCK_DATA.live;
 else if(p.includes('/api/models/'))v=MOCK_DATA.models;
 else if(p.includes('/api/satellite/map/status'))v=MOCK_DATA.satmap;
 else if(p.includes('/api/satellite/latest'))v=MOCK_DATA.satellite;
 else if(p.includes('/api/radar/status'))v=MOCK_DATA.radar;
 else if(p.includes('/api/aircraft/noaa'))v=MOCK_DATA.aircraft;
 else if(p.includes('/api/recon/status'))v=MOCK_DATA.recon;
 else v={{status:'ok'}};
 return {{ok:true,status:200,json:async()=>v,text:async()=>JSON.stringify(v)}};}};
 window.WebSocket=function(){{this.close=()=>{{}};}};</script><script>{js}</script>'''
 html=re.sub(r'<script src="/static/app.js\?[^" ]+" defer></script>',lambda m:mock,html)
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
  page=await browser.new_page(viewport={'width':1580,'height':970},device_scale_factor=1)
  errs=[];page.on('pageerror',lambda e:errs.append(str(e)))
  await page.route('https://tile.openstreetmap.org/**',lambda r:r.fulfill(status=200,content_type='image/png',body=png()))
  await page.route('https://cdn.star.nesdis.noaa.gov/**',lambda r:r.fulfill(status=200,content_type='image/png',body=png(1250,750)))
  await page.set_content(html,wait_until='domcontentloaded',timeout=30000)
  await page.wait_for_timeout(1200)
  assert await page.locator('#workspace-storms').is_visible()
  await page.locator('#stormList .storm-item').first.click()
  await page.locator('[data-workspace-tab="weather"]').click()
  assert await page.locator('#liveImageryOptions').is_visible()
  await page.wait_for_timeout(300)
  image=page.locator('#satelliteImage');await image.wait_for(state='visible',timeout=10000)
  frame=await page.locator('.satellite-frame').bounding_box(); image_box=await image.bounding_box();panel=await page.locator('.side-content').bounding_box()
  assert frame['width'] <=panel['width']+1 and frame['height']<=202,(frame,panel)
  assert image_box['width']<=panel['width']+1 and image_box['height']<=202,(image_box,panel)
  assert await image.evaluate('(i)=>i.naturalWidth')==1250
  await page.screenshot(path=str(ROOT/'docs/stormwatch_v09_weather_ui_mock.png'))
  await page.locator('#satelliteExpand').click()
  assert await page.locator('#modalBackdrop').is_visible()
  modalpic=await page.locator('.satellite-large').bounding_box();assert modalpic['width']<=880 and modalpic['height']<=0.62*970+2,modalpic
  await page.locator('#closeModal').click()
  await page.locator('#radarDisclosure > summary').click()
  assert await page.locator('#radarRegion').is_visible()
  await page.locator('[data-workspace-tab="models"]').click()
  assert await page.locator('#forecastModelsPanel').is_visible()
  assert await page.locator('#modelsIntensityChart').is_visible()
  assert await page.locator('#modelList [data-model="google"]').is_enabled()
  await page.screenshot(path=str(ROOT/'docs/stormwatch_v09_models_ui_mock.png'))
  assert not await page.locator('#modelList [data-model="hafsai"]').is_enabled()
  await page.locator('#modelMetric').select_option('pressure_hpa')
  await page.locator('[data-workspace-tab="layers"]').click()
  assert await page.locator('.layer-list').is_visible()
  await page.locator('[data-workspace-tab="layers"]').focus();await page.keyboard.press('ArrowRight')
  assert await page.locator('#workspace-recon').is_visible()
  await page.locator('[data-workspace-tab="recon"]').click()
  assert await page.locator('#liveAircraftPanel').is_visible()
  assert await page.locator('#reconButton').is_visible()
  await page.locator('[data-workspace-tab="storms"]').click()
  await page.locator('#focusSelected').click()
  await page.screenshot(path=str(ROOT/'docs/stormwatch_v09_live_ui_mock.png'))
  await page.locator('#archiveMode').click()
  for sel in ['[data-workspace-tab="weather"]','[data-workspace-tab="models"]','#liveImageryOptions','#liveAircraftPanel','#forecastModelsPanel','#modelsIntensityChart']:
   assert not await page.locator(sel).is_visible(),sel
  await page.locator('#stormList .storm-item').first.click();await page.locator('#skipForward').click()
  assert 'POINT 2' in await page.locator('#timelinePoint').inner_text()
  await page.locator('[data-workspace-tab="layers"]').click();assert await page.locator('.layer-list').is_visible()
  await page.locator('[data-workspace-tab="recon"]').click();assert await page.locator('#reconButton').is_visible()
  await page.screenshot(path=str(ROOT/'docs/stormwatch_v09_archive_ui_mock.png'))
  await page.locator('#liveMode').click()
  assert await page.locator('#workspace-storms').is_visible()
  assert await page.locator('[data-workspace-tab="weather"]').is_visible()
  assert await page.locator('[data-workspace-tab="models"]').is_visible()
  assert not errs,errs
  # Check narrow desktop responsiveness and layout containment.
  await page.set_viewport_size({'width':1280,'height':800})
  await page.locator('[data-workspace-tab="weather"]').click()
  await page.wait_for_timeout(200)
  rect=await page.locator('.satellite-frame').bounding_box();pane=await page.locator('.side-content').bounding_box()
  assert rect['width']<=pane['width'] and rect['height']<=202,(rect,pane)
  print('PASS: GOES natural=1250x750, thumbnail <=200px tall, modal bounded, 5 working tabs, models, radar, recon, archive hides live workspaces, archive playback, live restore; browser exceptions:',len(errs))
  await browser.close()
if __name__=='__main__':asyncio.run(main())
