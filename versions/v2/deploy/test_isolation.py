import os
from pathlib import Path
from uuid import uuid4
import json
from unittest.mock import patch
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
import httpx
import gateway
from career_v1 import cloud as v1
from career_v2 import cloud as v2
from coach import cloud as claude
from fastapi import HTTPException

if not os.getenv('DATABASE_URL','').rsplit('/',1)[-1].startswith('coachtest'):
    raise RuntimeError('Use a disposable coachtest database only')

apps=[('v1',v1),('v2',v2),('claude',claude)]
a,b=map(str,[uuid4(),uuid4()])
members={'A':a,'B':b,'guest':str(uuid4())}
async_client=httpx.AsyncClient
def auth(req):
    assert req.url.path=='/auth/v1/user'
    who=req.headers['authorization'].split()[-1]
    if who not in members:return httpx.Response(401)
    return httpx.Response(200,json={'id':members[who],'email_confirmed_at':'2026-11-21T00:00:00Z' if who!='guest' else None,'app_metadata':{}})
objects={}
fault=False
def storage(method,path,data=None):
    if method=='POST':objects[path]=data;return httpx.Response(200)
    if method=='DELETE' and fault:return httpx.Response(503)
    if path not in objects:return httpx.Response(404)
    if method=='GET':return httpx.Response(200,content=objects[path])
    if method=='DELETE':del objects[path];return httpx.Response(200)
    raise AssertionError()
patch.object(httpx,'AsyncClient',lambda **kw:async_client(transport=httpx.MockTransport(auth),**kw)).start()
for _,lib in apps:patch.object(lib,'storage',side_effect=storage).start()
client=TestClient(gateway.app)
def req(method,path,user=None,**kw):return client.request(method,path,headers={'Authorization':'Bearer '+user} if user else {},**kw)
for name,lib in apps:
    base='/'+name
    assert req('GET',base+'/').status_code==200
    assert req('GET',base+'/api/me').status_code==401
    assert req('GET',base+'/api/me','bad').status_code==401
    assert req('GET',base+'/api/me','guest').status_code==403
    for user in ['A','B']:
        assert req('GET',base+'/api/me',user).json()['id']==members[user]
        out=req('PUT',base+'/api/workspaces/'+('draft' if name=='claude' else 'demo'),user,json={'name':'Same','revision':0,'state':{'marker':user+name},'user_id':a,'app_id':'bogus'})
        assert out.status_code==200,out.text
for name,l in apps:
    for u in ['A','B']:
        r=req('GET','/'+name+'/api/workspaces/'+('draft' if name=='claude' else 'demo'),u).json()
        assert r['state']=={'marker':u+name}
        assert req('PUT','/'+name+'/api/workspaces/'+('draft' if name=='claude' else 'demo'),u,json={'name':'Same','revision':0,'state':{}}).status_code==409
fileids=[]
for name,l in apps:
    for uid in [a,b]:
        l.identity.set(uid)
        fileids.append(l.store_pdf('demo',b'%PDF-1.4 offline fixture'))
file=fileids[2]
assert req('GET','/v2/api/documents/'+file+'?project_id=demo','A').content==b'%PDF-1.4 offline fixture'
for base,u in [('v2','B'),('v1','A'),('claude','A')]:
    assert req('GET','/'+base+'/api/documents/'+file+'?project_id=demo',u).status_code==404
    assert req('DELETE','/'+base+'/api/documents/'+file+'?project_id=demo',u).status_code==404
def reserve(lib,uid):
    lib.identity.set(uid)
    try:
        call=lib.reserve_call()
        lib.record_usage(call,8)
        return 1
    except HTTPException as e:
        assert e.status_code==429
        return 0
with ThreadPoolExecutor(max_workers=9) as pool:
    assert sum(pool.map(lambda _:reserve(v2,a),range(14)))==10
    assert sum(pool.map(lambda i:reserve(claude if i%2 else v1,b),range(24)))==10
for i in range(3):
    r=req('GET','/v2/api/quota','A').json()
    assert r=={'remaining':0,'limit':10,'used':10,'blocked':False},r
assert req('GET','/v2/api/workspaces/demo','A').status_code==200
fault=True
assert req('DELETE','/v2/api/my-data','A').status_code==502
assert req('GET','/v2/api/workspaces/demo','A').status_code==200
fault=False
assert req('DELETE','/v2/api/my-data','A').json()=={'deletedProjects':1,'deletedDocuments':1}
assert req('GET','/v2/api/documents/'+file+'?project_id=demo','A').status_code==404
assert req('GET','/v2/api/workspaces','A').json()==[]
assert req('GET','/v2/api/quota','A').json()['remaining']==0
for name,l in apps:
    for u in ['A','B']:
        if name!='v2' or u!='A':
            assert req('GET','/'+name+'/api/workspaces/'+('draft' if name=='claude' else 'demo'),u).json()['state']=={'marker':u+name}
assert len(objects)==5
v2.record_usage(0,blocked=True)
for _,lib in apps:
    lib.identity.set(a)
    try:lib.reserve_call();raise AssertionError()
    except HTTPException as e:assert e.status_code==402
print('PASS: three mounted applications, signed-out/nonmember access, A/B ownership, write conflicts, PDFs, concurrent ten-per-account quotas, partial-delete retry, cross-version preservation, 402 latch')
