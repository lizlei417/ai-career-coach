"""Offline acceptance: real disposable PostgreSQL + fake Auth/Storage, no model HTTP.
Run with DATABASE_URL ending coachtest_increment, COACH_APPS pointing to three apps.
"""
import os
from pathlib import Path
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import psycopg,httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
if not os.environ.get('DATABASE_URL','').endswith('/coachtest_increment'):
 raise RuntimeError('Disposable coachtest_increment database required')
with psycopg.connect(os.environ['DATABASE_URL'],autocommit=True) as db:
 for file in ['001_private.sql','003_account_quota.sql']:db.execute(Path(__file__).with_name(file).read_text())
import gateway
from career_v1 import cloud as v1
from career_v2 import cloud as v2
from coach import cloud as claude
apps=[v1,v2,claude];a,b,c=map(str,[uuid4(),uuid4(),uuid4()]);ids={'A':a,'B':b,'C':c}
original=httpx.AsyncClient
patch.object(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'id':ids[req.headers['authorization'].split()[-1]],'email_confirmed_at':'2026-11-21T00:00:00Z','app_metadata':{}})),**kw)).start()
client=TestClient(gateway.app)
def req(method,path,user='A',**kw):return client.request(method,path,headers={'Authorization':'Bearer '+user},**kw)
def reserve(args):
 lib,uid=args;lib.identity.set(uid);lib.request_context.set(None)
 try:return lib.reserve_call()
 except HTTPException as e:assert e.status_code==429;return None
# Seed four old-style same-day records across apps and one previous-day record.
with v2.connect() as db:
 db.execute("insert into career_private.calls(day,user_id,app_id) select (current_timestamp at time zone 'Asia/Hong_Kong')::date,%s,case when n%%2=0 then 'codex_v1' else 'claude' end from generate_series(1,4) n",(a,))
 db.execute("insert into career_private.calls(day,user_id,app_id) values ((current_timestamp at time zone 'Asia/Hong_Kong')::date-1,%s,'codex_v2')",(a,))
for prefix in ['v1','v2','claude']:assert req('GET',f'/{prefix}/api/quota').json()['remaining']==6
with ThreadPoolExecutor(max_workers=6) as pool:out=list(pool.map(reserve,[(apps[i%3],a) for i in range(13)]))
assert len([x for x in out if x])==6
for prefix in ['v1','v2','claude']:assert req('GET',f'/{prefix}/api/quota').json()['remaining']==0
with ThreadPoolExecutor(max_workers=6) as pool:out=list(pool.map(reserve,[(apps[i%3],b) for i in range(13)]))
assert len([x for x in out if x])==10
assert reserve((claude,c)) # 21st global call succeeds.
print('PASS: old four calls retained, HK date excludes yesterday, six new A reservations, ten independent B reservations, 21st global call allowed, cross-app concurrency cannot exceed ten')
claude.identity.set(c);claude.request_context.set(['duplicate-request-00001',0]);call=claude.reserve_call();claude.dispatch_call(call)
claude.request_context.set(['duplicate-request-00001',0])
try:claude.reserve_call();raise AssertionError('duplicate admitted')
except HTTPException as e:assert e.status_code==409
claude.cancel_unsent(call)
with claude.connect() as db:assert claude.counts(db)['used']==1
print('PASS: duplicate operation rejected; transport-proven unsent reservation refunded')
state={'inputs':{'resumeText':'Fictional experience','jdText':'Fictional role'},'resume':{'data':'saved analysis'},'interview':{'draft':'saved answer'}}
r=req('PUT','/v2/api/workspaces/menu',json={'name':'Original','revision':0,'state':state});revision=r.json()['revision']
assert req('PATCH','/v2/api/workspaces/menu',json={'name':'   ','revision':revision}).status_code==422
assert req('PATCH','/v2/api/workspaces/menu','B',json={'name':'Stolen','revision':revision}).status_code==404
assert req('PATCH','/v2/api/workspaces/menu',json={'name':' Renamed ','revision':revision}).status_code==200
assert req('GET','/v2/api/workspaces/menu').json()['state']==state
assert req('GET','/v2/api/workspaces/menu').json()['name']=='Renamed'
assert req('PATCH','/v2/api/workspaces/menu',json={'name':'Stale','revision':revision}).status_code==409
objects={};fault=[False]
def storage(method,path,data=None):
 if method=='POST':objects[path]=data;return httpx.Response(200)
 if method=='GET':return httpx.Response(200,content=objects[path]) if path in objects else httpx.Response(404)
 if fault[0]:return httpx.Response(503)
 objects.pop(path,None);return httpx.Response(200)
for lib in apps:patch.object(lib,'storage',side_effect=storage).start()
v2.identity.set(a);fid=v2.store_pdf('menu',b'%PDF test');v2.identity.set(b);other=v2.store_pdf('menu',b'%PDF B')
assert req('DELETE','/v2/api/workspaces/menu','B').status_code==404
fault[0]=True;assert req('DELETE','/v2/api/workspaces/menu').status_code==502
assert req('GET','/v2/api/workspaces/menu').status_code==200
fault[0]=False;assert req('DELETE','/v2/api/workspaces/menu').json()=={'deletedProjects':1,'deletedDocuments':1}
assert req('GET','/v2/api/workspaces/menu').status_code==404
assert req('GET',f'/v2/api/documents/{fid}?project_id=menu').status_code==404
assert req('GET',f'/v2/api/documents/{other}?project_id=menu','B').status_code==200
assert req('GET','/v2/api/quota').json()['remaining']==0
print('PASS: rename trims, validates owner/revision and preserves all state; partial Storage failure retains catalog; retry deletes only owning project/PDF, accounting and foreign PDF preserved')
with patch.dict(os.environ,{'AI_REQUESTS_ENABLED':'false'}):
 try:v1.reserve_call();raise AssertionError()
 except HTTPException as e:assert e.status_code==503
print('PASS: emergency switch; ZERO external model calls')
