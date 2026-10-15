"""Isolated mocked-browser check. Does NOT validate external ADS-B or NOAA connectivity."""
import asyncio
import json
import pathlib
import re
from playwright.async_api import async_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
WEB=ROOT/'apps/web/dist'

async def main():
    fixture=json.loads((ROOT/'data/fixtures/milton_advisories.json').read_text())
    data={
      'coasts':json.loads((WEB/'coastlines.json').read_text()),
      'lands':json.loads((WEB/'landpolygons.json').read_text()),
      'archive':{'storms':[{'id':fixture['id'],'name':'Milton','year':2024,
          'basin':'Atlantic','dataset':fixture['dataset'],'point_count':len(fixture['points'])}]},
      'detail':fixture,
      'live':{'availability':'AVAILABLE','checked_utc':'2026-10-14T20:00:00Z','storms':[]},
      'satellite':{'quality':'UNAVAILABLE'},
      'radar':{'quality':'UNAVAILABLE'},
      'recon':{'quality':'UNAVAILABLE'},
      'aircraft':{'quality':'AVAILABLE','aircraft':[{
          'registration':'N42RF','icao_hex':'a4fac3','callsign':'NOAA42',
          'name':'Kermit','aircraft_type':'NOAA WP-3D Orion','identity_verified':True,
          'mission_status':'NOT VERIFIED','lat':28.4,'lon':-84.8,'altitude_ft':12000,
          'groundspeed_kt':220,'heading_deg':180,'observed_utc':'2026-10-14T20:00:00Z',
          'age_seconds':22,'quality':'LIVE'}]},
      'teal':{'quality':'AVAILABLE','aircraft':[]}
    }
    js=(WEB/'app.js').read_text()
    html=(WEB/'index.html').read_text()
    html=re.sub(r'@import\s+url\([^)]*\);','',html)
    script=f'''<script>
const MOCK_DATA={json.dumps(data)};
window.fetch=async function(url,options){{let p=String(url),value;
  if(p.includes('coastlines.json'))value=MOCK_DATA.coasts;
  else if(p.includes('landpolygons.json'))value=MOCK_DATA.lands;
  else if(p.includes('/api/storms/historical/'))value=MOCK_DATA.detail;
  else if(p.includes('/api/storms/historical'))value=MOCK_DATA.archive;
  else if(p.includes('/api/storms/live'))value=MOCK_DATA.live;
  else if(p.includes('/api/satellite/latest'))value=MOCK_DATA.satellite;
  else if(p.includes('/api/radar/status'))value=MOCK_DATA.radar;
  else if(p.includes('/api/aircraft/noaa'))value=MOCK_DATA.aircraft;
  else if(p.includes('/api/aircraft/teal'))value=MOCK_DATA.teal;
  else if(p.includes('/api/recon/status'))value=MOCK_DATA.recon;
  else value={{status:'ok'}};
  return {{ok:true,status:200,json:async()=>value,text:async()=>JSON.stringify(value)}};
}};
window.WebSocket=function(){{this.close=()=>{{}};}};
</script><script>{js}</script>'''
    html=re.sub(r'<script src="/static/app.js\?[^" ]+" defer></script>',lambda m:script,html)
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
        page=await browser.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        await page.set_content(html,wait_until='domcontentloaded',timeout=15000)
        await page.wait_for_selector('.aircraft-item',timeout=10000)
        assert await page.locator('#liveImageryOptions').is_visible()
        assert await page.locator('#liveAircraftPanel').is_visible()
        await page.locator('.aircraft-item').first.click()
        assert 'Kermit' in await page.locator('.inspector-title').inner_text()
        await page.locator('#archiveMode').click()
        assert not await page.locator('#liveImageryOptions').is_visible()
        assert not await page.locator('#liveAircraftPanel').is_visible()
        assert not await page.locator('[data-layer="radar"]').is_visible()
        assert not await page.locator('#reconLiveButton').is_visible()
        assert await page.locator('#stormList .storm-item').count()==1
        await page.locator('#stormList .storm-item').first.click()
        assert 'MILTON' in (await page.locator('#mapTitle').inner_text()).upper()
        await page.locator('#skipForward').click()
        assert 'POINT 2' in (await page.locator('#timelinePoint').inner_text())
        screenshot=ROOT/'docs/stormwatch_v06_archive_mock.png'
        await page.screenshot(path=str(screenshot),full_page=True)
        await page.locator('#liveMode').click()
        assert await page.locator('#liveImageryOptions').is_visible()
        assert await page.locator('#liveAircraftPanel').is_visible()
        assert await page.locator('.aircraft-item').count()==1
        await page.locator('[data-view="flat"]').click()
        assert 'active' in (await page.locator('[data-view="flat"]').get_attribute('class'))
        await page.screenshot(path=str(ROOT/'docs/stormwatch_v06_live_mock.png'),full_page=True)
        assert not errors, errors
        print('ISOLATED CHROMIUM PASS: archive hides live imagery and aircraft panels; live restores them; NOAA aircraft inspection, replay, 2D map; JS errors 0')
        await browser.close()

if __name__=='__main__':
    asyncio.run(main())
