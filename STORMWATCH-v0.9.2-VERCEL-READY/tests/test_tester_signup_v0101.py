from pathlib import Path
import os
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from stormwatch.main import app, _signup_attempts

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'apps/web/dist'

def payload(**change):
    return {'name':'Test Person','email':'example@example.com','interest':'Radar & satellite','feedback':'Testing mobile','consent':True,'website':'',**change}

def test_pages_include_tester_links_and_modal():
    for name in ('index.html','about.html','news.html'):
        page=(DIST/name).read_text()
        assert 'testerBackdrop' in page
        assert '/static/testers.js' in page
        assert '/static/testers.css' in page
    assert 'data-open-testers' in (DIST/'index.html').read_text()
    assert 'SEND FEEDBACK' in (DIST/'about.html').read_text()

def test_missing_email_service_rejected(monkeypatch):
    monkeypatch.delenv('RESEND_API_KEY',raising=False)
    monkeypatch.delenv('TESTER_NOTIFICATION_FROM',raising=False)
    with TestClient(app) as client:
        result=client.post('/api/testers/signup',json=payload())
    assert result.status_code==503

def test_validation_and_consent():
    with TestClient(app) as client:
        assert client.post('/api/testers/signup',json=payload(consent=False)).status_code==422
        assert client.post('/api/testers/signup',json=payload(email='bad')).status_code==422
        assert client.post('/api/testers/signup',json=payload(name='x'*100)).status_code==422
        assert client.post('/api/testers/signup',json=payload(website='spam-domain')).json()['ok']

def test_send_email_success_and_provider_error(monkeypatch):
    import httpx
    _signup_attempts.clear()
    monkeypatch.setenv('RESEND_API_KEY','re_mock')
    monkeypatch.setenv('TESTER_NOTIFICATION_FROM','STORMWATCH <testers@stormwatch.site>')
    success=httpx.Response(200,json={'id':'mail_123'},request=httpx.Request('POST','https://api.resend.com/emails'))
    with patch('httpx.AsyncClient.post',new_callable=AsyncMock,return_value=success) as send:
        with TestClient(app) as client:
            result=client.post('/api/testers/signup',json=payload())
        assert result.status_code==200
        assert result.json()['ok']
        kwargs=send.await_args.kwargs
        assert kwargs['json']['to']==['mattsails07@gmail.com']
        assert kwargs['json']['reply_to']=='example@example.com'
        assert 're_mock' in kwargs['headers']['Authorization']
        assert 'Test Person' in kwargs['json']['html']
    failure=httpx.Response(403,json={'message':'not verified'},request=httpx.Request('POST','https://api.resend.com/emails'))
    with patch('httpx.AsyncClient.post',new_callable=AsyncMock,return_value=failure):
        with TestClient(app) as client:
            assert client.post('/api/testers/signup',json=payload(email='second@example.com')).status_code==503
