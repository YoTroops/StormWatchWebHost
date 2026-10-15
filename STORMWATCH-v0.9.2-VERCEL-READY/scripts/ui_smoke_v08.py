"""Isolated mock forecast visualization; not live NOAA, Google, or ECMWF data."""
import asyncio,io,json,pathlib,re
from PIL import Image,ImageDraw
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
WEB=ROOT/'apps/web/dist'

def dummy_png(alpha=False):
    img=Image.new('RGBA',(256,256),(15,30,48,0) if alpha else (220,227,230,255))
    draw=ImageDraw.Draw(img)
    if not alpha:
        for n in range(0,256,42):draw.line([(0,n),(255,255-n)], fill=(125,146,159,255),width=2)
        draw.text((52,117),'MOCK MAP TILE',fill=(40,80,100,255))
    else:
        draw.ellipse((35,40,220,210),fill=(230,105,140,125))
        draw.text((62,110),'MOCK IR',fill=(255,255,255,255))
    out=io.BytesIO();img.save(out,format='PNG');return out.getvalue()

async def main():
    fixture=json.loads((ROOT/'data/fixtures/milton_advisories.json').read_text())
    data={'coasts':json.loads((WEB/'coastlines.json').read_text()),'lands':json.loads((WEB/'landpolygons.json').read_text()),
     'archive':{'storms':[{'id':fixture['id'],'name':'Milton','year':2024,'basin':'Atlantic','dataset':fixture['dataset'],'point_count':len(fixture['points'])}]},
     'detail':fixture,'live':{'availability':'AVAILABLE','checked_utc':'2026-10-14T20:00:00Z','storms':[{'id':'AL092026','name':'TEST SYSTEM','basin':'Atlantic','lat':22,'lon':-73,'wind_kt':60,'pressure_hpa':985,'category':1,'quality':'DELAYED','time':'2026-10-14T12:00:00Z','provider':'MOCK NHC'}]},
     'satellite':{'quality':'UNAVAILABLE'},'radar':{'quality':'UNAVAILABLE'},'recon':{'quality':'UNAVAILABLE'},
     'aircraft':{'quality':'AVAILABLE','aircraft':[]},
     'models':{'quality':'AVAILABLE','storm_id':'AL092026','cycle_utc':'2026-10-14T12:00:00Z','available_cycles':['2026-10-14T12:00:00Z'],'available_models':4,'cycle_age_hours':1,'models':[{'id':x,'name':nm,'family':family,'availability':available,'aid_used':aid,'note':'MOCK TEST ONLY','points':[{'tau_hours':i,'lat':22+i/24*(k+1),'lon':-73-i/24*(k+1),'wind_kt':60+k*5+i/3,'pressure_hpa':980-i/4,'valid_utc':'2026-10-15T12:00:00Z'} for i in (0,24,48)] if available=='AVAILABLE' else [],'max_wind_kt':80+k*5} for k,(x,nm,family,available,aid) in enumerate([('nhc','NHC Official','official','AVAILABLE','OFCL'),('hafsa','HAFS-A','dynamical','AVAILABLE','HFSA'),('gfs','GFS','dynamical','AVAILABLE','AVNI'),('google','Google DeepMind','ai','AVAILABLE','GDMI'),('hafsai','HAFS-AI (requested)','ai','UNAVAILABLE',None)])]},
     'satmap':{'quality':'AVAILABLE','checked_utc':'2026-10-14T20:00:00Z','layer_name':'TEST ONLY IR Composite','layer_id':8}}
    html=(WEB/'index.html').read_text()
    html=re.sub(r'@import\s+url\([^)]*\);','',html)
    html=html.replace('<head>','<head><base href="http://127.0.0.1:8000/">',1)
    js=(WEB/'app.js').read_text()
    mock=f'''<script>
    const MOCK_DATA={json.dumps(data)};
    window.fetch=async function(url,options){{let p=String(url),value;
     if(p.includes('coastlines.json'))value=MOCK_DATA.coasts;
     else if(p.includes('landpolygons.json'))value=MOCK_DATA.lands;
     else if(p.includes('/api/storms/historical/'))value=MOCK_DATA.detail;
     else if(p.includes('/api/storms/historical'))value=MOCK_DATA.archive;
     else if(p.includes('/api/storms/live'))value=MOCK_DATA.live;
     else if(p.includes('/api/models/'))value=MOCK_DATA.models;
     else if(p.includes('/api/satellite/map/status'))value=MOCK_DATA.satmap;
     else if(p.includes('/api/satellite/latest'))value=MOCK_DATA.satellite;
     else if(p.includes('/api/radar/status'))value=MOCK_DATA.radar;
     else if(p.includes('/api/aircraft/noaa'))value=MOCK_DATA.aircraft;
     else if(p.includes('/api/recon/status'))value=MOCK_DATA.recon;
     else value={{status:'ok'}};
     return {{ok:true,status:200,json:async()=>value,text:async()=>JSON.stringify(value)}};
    }};
    window.WebSocket=function(){{this.close=()=>{{}};}};
    </script><script>{js}</script>'''
    html=re.sub(r'<script src="/static/app.js\?[^" ]+" defer></script>',lambda m:mock,html)
    async with async_playwright() as pw:
     browser=await pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
     page=await browser.new_page(viewport={'width':1580,'height':970},device_scale_factor=1)
     errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
     tiles={'total':0};tile=dummy_png();sat=dummy_png(alpha=True)
     async def route_osm(route):
      tiles['total']+=1
      await route.fulfill(status=200,content_type='image/png',body=tile,headers={'Access-Control-Allow-Origin':'*','Cache-Control':'public, max-age=86400'})
     await page.route('https://tile.openstreetmap.org/**',route_osm)
     async def route_sat(route):
      await route.fulfill(status=200,content_type='image/png',body=sat)
     await page.route('**/api/satellite/map/image**',route_sat)
     await page.set_content(html,wait_until='domcontentloaded',timeout=20000)
     await page.wait_for_timeout(1200)
     await page.locator('#stormList .storm-item').first.click()
     await page.wait_for_timeout(350)
     assert '2026' in await page.locator('#modelMeta').inner_text()
     assert await page.locator('#modelList [data-model=\"google\"]').is_enabled()
     assert not await page.locator('#modelList [data-model=\"hafsai\"]').is_enabled()
     await page.locator('#modelMetric').select_option('pressure_hpa')
     await page.locator('#modelList [data-model=\"gfs\"]').uncheck()
     assert await page.locator('#modelsIntensityChart').is_visible()
     await page.locator('#forecastModelsPanel').scroll_into_view_if_needed()
     await page.screenshot(path=str(ROOT/'docs/stormwatch_v08_models_mock.png'),full_page=True)
     assert tiles['total']>0,tiles
     assert 'OSM DETAIL' in await page.locator('#mapDetailStatus').inner_text(),await page.locator('#mapDetailStatus').inner_text()
     assert await page.locator('#mapAttribution').is_visible()
     await page.locator('#zoomIn').click();await page.locator('#zoomIn').click()
     await page.locator('[data-view="flat"]').click()
     assert 'active' in (await page.locator('[data-view="flat"]').get_attribute('class'))
     await page.locator('#mappedSatEnabled').check()
     await page.wait_for_timeout(900)
     assert 'TEST ONLY IR' in (await page.locator('#mappedSatStatus').inner_text()), (await page.locator('#mappedSatStatus').inner_text(),errors)
     await page.screenshot(path=str(ROOT/'docs/stormwatch_v08_live_mock.png'),full_page=True)
     await page.locator('#archiveMode').click()
     assert not await page.locator('#mappedSatControls').is_visible()
     assert not await page.locator('#liveImageryOptions').is_visible()
     assert not await page.locator('#liveAircraftPanel').is_visible()
     assert not await page.locator('#forecastModelsPanel').is_visible()
     assert not await page.locator('.model-chart-section').is_visible()
     assert await page.locator('#mapAttribution').is_visible()
     assert await page.locator('#detailedMapToggle').is_visible()
     await page.locator('#stormList .storm-item').first.click()
     await page.locator('#skipForward').click()
     assert 'POINT 2' in await page.locator('#timelinePoint').inner_text()
     await page.screenshot(path=str(ROOT/'docs/stormwatch_v08_archive_mock.png'),full_page=True)
     await page.locator('#detailedMapToggle').click()
     assert not await page.locator('#mapAttribution').is_visible()
     assert 'OFFLINE COASTLINES' in await page.locator('#mapDetailStatus').inner_text()
     await page.locator('#liveMode').click()
     assert await page.locator('#mappedSatControls').is_visible()
     assert await page.locator('#forecastModelsPanel').is_visible()
     assert not errors,errors
     print(f'ISOLATED CHROMIUM PASS: {tiles["total"]} mocked map requests, storm/model selection, forecast chart, model toggles, unavailable AI status, archive hides forecast controls, JS errors 0')
     await browser.close()

if __name__=='__main__':asyncio.run(main())
