"""Optional isolated Chromium UI smoke check; mocks all HTTP, NOT a full server E2E.
Requires Playwright and Chromium installed; edit executable_path if non-Linux.
Run: python scripts/ui_smoke_mock.py
"""
import asyncio, pathlib, json, re
from playwright.async_api import async_playwright
base=pathlib.Path(__file__).resolve().parents[1]/'apps/web/dist'
fixture=pathlib.Path(__file__).resolve().parents[1]/'data/fixtures/milton_advisories.json'
async def main():
 html=(base/'index.html').read_text();css=(base/'style.css').read_text();js=(base/'app.js').read_text();storm=json.loads(fixture.read_text());
 for p in storm['points']:
  p['wind_kt']=round(p['wind_mph']/1.150779448,1)
  p['category']=5 if p['wind_kt']>=137 else 4 if p['wind_kt']>=113 else 3 if p['wind_kt']>=96 else 2 if p['wind_kt']>=83 else 1 if p['wind_kt']>=64 else None
 css=re.sub(r"@import\s+url\([^)]*\);",'',css)
 html=re.sub(r'<link rel="icon"[^>]*>', '',html)
 html=re.sub(r'<link rel="stylesheet"[^>]*>', '<style>'+css+'</style>',html)
 mock={'coasts':json.loads((base/'coastlines.json').read_text()),'lands':json.loads((base/'landpolygons.json').read_text()),'archive':{'storms':[{'id':storm['id'],'name':storm['name'],'year':storm['year'],'basin':storm['basin'],'dataset':storm['dataset'],'point_count':len(storm['points'])}]},'detail':storm,'live':{'availability':'UNAVAILABLE','storms':[],'error':'NOAA blocked in test environment'},'recon':{'quality':'ARCHIVED','source_kind':'NHC HDOB','mission':'AF300 WXWXA','source_url':'https://www.nhc.noaa.gov/text/URNT15-USAF.shtml','note':'HDOB verification fixture','points':[{'time':'2026-09-10T01:04:00Z','lat':30.5,'lon':-89.4,'wind_kt':15},{'time':'2026-09-10T01:05:00Z','lat':30.4,'lon':-89.2,'wind_kt':16}]}}
 mock_js=f'''const TEST_DATA={json.dumps(mock)};
 window.fetch=async function(url,opts){{let path=String(url);let v;
 if(path.includes('coastlines.json'))v=TEST_DATA.coasts;
 else if(path.includes('landpolygons.json'))v=TEST_DATA.lands;
 else if(path.includes('/api/storms/historical/'))v=TEST_DATA.detail;
 else if(path.includes('/api/storms/historical'))v=TEST_DATA.archive;
 else if(path.includes('/api/storms/live'))v=TEST_DATA.live;
 else if(path.includes('/api/recon/fixture'))v=TEST_DATA.recon;
 else v={{service:'STORMWATCH',status:'ok'}};
 return {{ok:true,status:200,json:async()=>v,text:async()=>JSON.stringify(v)}};
 }};
 window.WebSocket=function(){{this.close=()=>{{}};}};
 '''
 html=html.replace('<script src="/static/app.js" defer></script>', '<script>'+mock_js+'\n'+js+'</script>')
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
  page=await browser.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
  errors=[];page.on('pageerror',lambda err: errors.append(str(err)))
  await page.set_content(html,wait_until='domcontentloaded',timeout=10000)
  await page.wait_for_timeout(1200)
  print('STORMS',await page.locator('.storm-item').count())
  print('TITLE',await page.locator('#mapTitle').inner_text())
  print('POINT',await page.locator('#timelineTime').inner_text())
  print('JS ERRORS',errors)
  await page.screenshot(path=str(base.parents[2]/'docs/stormwatch_browser_mock.png'),full_page=True)
  await page.locator('#skipForward').click()
  print('ADVANCE',await page.locator('#timelineTime').inner_text())
  await page.locator('#reconButton').click();await page.wait_for_timeout(80)
  print('RECON',await page.locator('.inspector-title').inner_text())
  await page.locator('[data-view="flat"]').click()
  print('2D',await page.locator('[data-view="flat"]').get_attribute('class'))
  print('JS ERRORS END',errors)
  await browser.close()
asyncio.run(main())
