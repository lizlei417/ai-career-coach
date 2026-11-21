"""Local-only synthetic provider for browser QA. No actual service credentials."""
import base64,json,time,secrets
from uuid import uuid4
from fastapi import FastAPI,Request,HTTPException,Response
from fastapi.middleware.cors import CORSMiddleware
app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=["http://127.0.0.1:28549"],allow_methods=["*"],allow_headers=["*"])
users={email:dict(id=str(uuid4()),email=email,aud="authenticated",role="authenticated",app_metadata={"coach_member":True},user_metadata={},created_at="2025-01-01T00:00:00Z") for email in ["a@example.test","b@example.test"]}
pw={e:"fixture-password" for e in users}
tokens={}
objects={}
def enc(o):return base64.urlsafe_b64encode(json.dumps(o).encode()).decode().strip('=')
def user(r):
 t=r.headers.get('authorization','').removeprefix("Bearer ")
 if t not in tokens:raise HTTPException(401)
 return tokens[t]
@app.post('/auth/v1/token')
async def login(r:Request):
 form=await r.json()
 email=form.get('email')
 if email not in users or form.get('password')!=pw[email]:raise HTTPException(401)
 exp=int(time.time())+3600
 t=enc({'alg':'HS256','typ':'JWT'})+'.'+enc({'sub':users[email]['id'],'exp':exp,'session_id':str(uuid4())})+'.ZmFrZQ'
 tokens[t]=users[email]
 return dict(access_token=t,token_type='bearer',expires_in=3600,expires_at=exp,refresh_token=secrets.token_hex(16),user=users[email])
@app.get('/auth/v1/user')
def verify(r:Request):return user(r)
@app.put('/auth/v1/user')
async def update(r:Request):
 u=user(r)
 pw[u['email']]=(await r.json())['password']
 return u
@app.post('/auth/v1/logout')
def logout(r:Request):
 user(r);del tokens[r.headers['authorization'][7:]]
 return Response(status_code=204)
@app.api_route('/storage/v1/object/career-resumes-private/{path:path}',methods=['POST','GET','DELETE'])
async def object(path:str,r:Request):
 if r.headers.get('apikey')!='sb_secret_offline':raise HTTPException(403)
 if r.method=='POST':objects[path]=await r.body();return {}
 if path not in objects:raise HTTPException(404)
 if r.method=='GET':return Response(objects[path],media_type='application/pdf')
 del objects[path];return {}

@app.delete('/storage/v1/object/career-resumes-private')
async def remove_objects(r:Request):
 if r.headers.get('apikey')!='sb_secret_offline':raise HTTPException(403)
 paths=(await r.json())['prefixes']
 for path in paths: objects.pop(path,None)
 return []
