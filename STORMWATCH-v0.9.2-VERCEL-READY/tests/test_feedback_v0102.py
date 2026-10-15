from fastapi.testclient import TestClient
from unittest.mock import AsyncMock,patch
from stormwatch.main import app,_signup_attempts
import httpx

def test_feedback_validation():
 with TestClient(app) as c:
  base={'feedback':'Radar overlay offset over land','interest':'Bug report'}
  assert c.post('/api/feedback',json={**base,'feedback':'  '}).status_code==422
  assert c.post('/api/feedback',json={**base,'email':'bad'}).status_code==422
  assert c.post('/api/feedback',json={**base,'website':'bot'}).json()['ok']

def test_feedback_email(monkeypatch):
 _signup_attempts.clear()
 monkeypatch.setenv('RESEND_API_KEY','re_mock')
 monkeypatch.setenv('TESTER_NOTIFICATION_FROM','STORMWATCH <feedback@stormwatch.site>')
 response=httpx.Response(200,json={'id':'mail1'},request=httpx.Request('POST','https://api.resend.com/emails'))
 with patch('httpx.AsyncClient.post',new_callable=AsyncMock,return_value=response) as send:
  with TestClient(app) as c:
   r=c.post('/api/feedback',json={'feedback':'Radar offset on mobile','interest':'Bug report'})
  assert r.status_code==200
  payload=send.await_args.kwargs['json']
  assert payload['to']==['mattsails07@gmail.com']
  assert 'reply_to' not in payload
  assert 'Radar offset' in payload['html']
