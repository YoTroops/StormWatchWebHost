"""Isolated Chromium frontend test with mocked source responses (no NOAA claim).
Run from project root: python scripts/ui_smoke_live.py
Requires playwright and Chromium; not part of runtime dependencies.
"""
import asyncio, base64, json, re
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'apps/web/dist'

async def main():
    html=(DIST/'index.html').read_text()
    js=(DIST/'app.js').read_text()
    html=re.sub(r'<script src="/static/app.js[^>]*></script>','',html)
    html=re.sub(r"@import url\([^;]+;",'',html)
    fixture=json.loads((ROOT/'data/fixtures/milton_advisories.json').read_text())
    for point in fixture['points']:
        if 'wind_kt' not in point and 'wind_mph' in point:
            point['wind_kt']=round(point['wind_mph']/1.150779448,1)
    img=Image.new('RGB',(640,360),'#233c59')
    ImageDraw.Draw(img).text((20,30),'UI TEST MOCK — NOT NOAA IMAGERY',fill='white')
    buffer=BytesIO();img.save(buffer,'PNG')
    image_b64='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()
    satellite_url='https://cdn.star.nesdis.noaa.gov/GOES19/ABI/CONUS/GEOCOLOR/20262871440_GOES19-ABI-CONUS-GEOCOLOR-1250x750.jpg'
    sat={'satellite':'GOES-19 (GOES-East)','sector':'CONUS','channel':'GEOCOLOR','channel_label':'GeoColor (day/night composite)',
         'image_url':satellite_url,'quality':'LIVE','observed_utc':'2026-10-14T14:40:00Z','checked_utc':'2026-10-14T14:45:00Z',
         'source_url':'https://www.star.nesdis.noaa.gov/GOES/conus.php?sat=G19'}
    rimg=Image.new('RGBA',(720,480),(0,0,0,0))
    rd=ImageDraw.Draw(rimg)
    rd.ellipse((300,155,460,285),fill=(38,175,219,185))
    rd.ellipse((341,183,410,247),fill=(243,162,62,205))
    rd.text((12,15),'RADAR UI MOCK - NO WEATHER OBSERVATIONS',fill=(240,240,240,255))
    buf=BytesIO();rimg.save(buf,'PNG');radar_image_b64='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
    mock={
        'coasts':json.loads((DIST/'coastlines.json').read_text()),
        'lands':json.loads((DIST/'landpolygons.json').read_text()),
        'archives':{'storms':[{'id':fixture['id'],'name':fixture['name'],'year':fixture['year'],'basin':fixture['basin'],
                                'dataset':fixture['dataset'],'point_count':len(fixture['points'])}]},
        'detail':fixture,
        'live':{'availability':'AVAILABLE','checked_utc':'2026-10-14T14:45:00Z',
                'storms':[{'id':'AL012026','name':'TEST STORM UI MOCK','basin':'Atlantic',
                'classification':'Tropical Storm','wind_kt':45,'pressure_hpa':995,'category':None,
                'lat':22,'lon':-80,'motion_deg':300,'motion_mph':12,'time':'2026-10-14T14:00:00Z',
                'quality':'DELAYED','provider':'NOAA/NHC','source_url':'https://www.nhc.noaa.gov/'}]},
        'sat':sat,
        'radar':{'provider':'NOAA/NWS MRMS','quality':'AVAILABLE',
                 'coverage_window_start_utc':'2026-10-14T17:50:00Z',
                 'coverage_window_end_utc':'2026-10-14T19:50:00Z',
                 'checked_utc':'2026-10-14T20:00:00Z'},
    }
    injection=f"""
    const MOCK_DATA={json.dumps(mock)};
    window.fetch=async function(input){{
      const path=String(input);let obj;
      if(path.includes('coastlines.json'))obj=MOCK_DATA.coasts;
      else if(path.includes('landpolygons.json'))obj=MOCK_DATA.lands;
      else if(path.includes('/api/storms/live'))obj=MOCK_DATA.live;
      else if(path.includes('/api/storms/historical/'))obj=MOCK_DATA.detail;
      else if(path.includes('/api/storms/historical'))obj=MOCK_DATA.archives;
      else if(path.includes('/api/satellite/latest'))obj=MOCK_DATA.sat;
      else if(path.includes('/api/radar/status'))obj=MOCK_DATA.radar;
      else if(path.includes('/api/recon/status'))obj={{quality:'UNAVAILABLE',note:'UI test mock: no HDOB'}};
      else obj={{service:'STORMWATCH',status:'ok',providers:{{}}}};
      return {{ok:true,status:200,json:async()=>obj,text:async()=>JSON.stringify(obj)}};
    }};
    window.WebSocket=function(){{this.close=()=>{{}};}};
    const realDescriptor=Object.getOwnPropertyDescriptor(HTMLImageElement.prototype,'src');
    Object.defineProperty(HTMLImageElement.prototype,'src',{{configurable:true,
      set(v){{realDescriptor.set.call(this,String(v).startsWith('https://cdn.star.nesdis.noaa.gov/')?{json.dumps(image_b64)}:String(v).startsWith('/api/radar/image')?{json.dumps(radar_image_b64)}:v)}},
      get(){{return realDescriptor.get.call(this)}}
    }});
    """
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
        page=await browser.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda error: errors.append(str(error)))
        await page.set_content(html,wait_until='domcontentloaded',timeout=10000)
        await page.add_script_tag(content=injection+'\n'+js)
        await page.wait_for_function("document.querySelector('#satelliteMeta').textContent.includes('OBSERVED')",timeout=12000)
        assert await page.evaluate("getComputedStyle(document.querySelector('.workarea')).display")=='grid','Inline CSS did not load'
        assert await page.locator('#stormList .storm-item').count()==1,'LIVE storms not displayed'
        assert await page.locator('#satelliteImage').is_visible(),'Satellite preview not displayed'
        await page.wait_for_function("document.querySelector('#radarStatus').textContent==='AVAILABLE'",timeout=12000)
        assert 'NWS WINDOW' in await page.locator('#radarMeta').inner_text(),'Radar time window absent'
        await page.locator('#radarOffset').select_option('15')
        await page.wait_for_function("document.querySelector('#radarMeta').textContent.includes('19:35')",timeout=12000)
        await page.locator('#radarRegion').select_option('southeast')
        await page.locator('#radarFocus').click()
        assert await page.evaluate("state.radarRegion")=='southeast'
        await page.locator('#radarOpacity').fill('30')
        assert abs(await page.evaluate('state.radarOpacity')-.30)<.001
        assert 'LIVE' in await page.locator('#satelliteStatus').inner_text(),'Satellite quality label missing'
        await page.locator('[data-storm]').click()
        assert 'TEST STORM' in await page.locator('#inspector').inner_text(),'Live inspector failed'
        await page.locator('#satelliteExpand').click()
        assert await page.locator('.satellite-large').is_visible(),'Expand preview failed'
        await page.locator('#closeModal').click()
        await page.locator('#archiveMode').click()
        assert await page.locator('#stormList .storm-item').count()>0,'Archive mode failed'
        await page.locator('#stormList .storm-item').first.click()
        assert 'ARCHIVED' in await page.locator('#inspector').inner_text(),'Archive inspector failed'
        await page.locator('#skipForward').click()
        assert 'POINT 2' in await page.locator('#timelinePoint').inner_text(),'Replay failed'
        await page.locator('[data-view="flat"]').click()
        assert 'active' in (await page.locator('[data-view="flat"]').get_attribute('class')),'2D switch failed'
        if errors:raise AssertionError('JS page errors: '+repr(errors))
        output=ROOT/'docs/stormwatch_v05_browser_mock.png'
        await page.screenshot(path=str(output),full_page=True)
        print('PASS: isolated Chromium UI test — layout, LIVE storm, NWS radar time/region/opacity, GOES preview, archive, replay, 2D; no page errors')
        print('Screenshot:',output)
        await browser.close()

if __name__=='__main__':asyncio.run(main())
