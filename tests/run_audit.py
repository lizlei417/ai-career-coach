"""Reproducible isolated audit. Requires an existing disposable UTF8 PostgreSQL DB.
Does not create a database, contact hosted Supabase, or call real AI by default.
"""
import os, sys, subprocess, socket, time
from pathlib import Path
import psycopg
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'tests/evidence';EVIDENCE.mkdir(exist_ok=True)
url=os.environ.get('QA_DATABASE_URL','')
if not url.rsplit('/',1)[-1].startswith('coachtest_v3_audit'):
 raise SystemExit('Set QA_DATABASE_URL to an isolated coachtest_v3_audit* UTF8 database')
with psycopg.connect(url) as db:
 if db.execute('show server_encoding').fetchone()[0]!='UTF8':raise SystemExit('UTF8 server encoding required')
 for name in ['001_private.sql','003_account_quota.sql']:db.execute((ROOT/'deploy'/name).read_text())
env=dict(os.environ,DATABASE_URL=url,SUPABASE_URL='http://127.0.0.1:28648',SUPABASE_PUBLISHABLE_KEY='sb_publishable_offline',SUPABASE_SECRET_KEY='sb_secret_offline',DEEPSEEK_API_KEY='offline-test-only')
env['QA_DOCUMENTS_MOCK']='1'
env.pop('QA_REAL_JD_IMPORT',None);env.pop('QA_PUBLIC_DNS',None);env.pop('QA_REAL_MODEL',None);env.pop('QA_APP_ROOT',None);env.pop('FRONTEND_DIST',None)
processes=[]
def launch(kind,port):
 with socket.socket() as s:
  if s.connect_ex(('127.0.0.1',port))==0:raise RuntimeError(f'Test port {port} already in use; no process was stopped')
 log=open(EVIDENCE/('mock-'+kind+'-server.log'),'w')
 process=subprocess.Popen([sys.executable,str(ROOT/'tests/qa_server.py'),kind],env=env,stdout=log,stderr=log)
 processes.append((process,log))
 for _ in range(100):
  if process.poll() is not None:raise RuntimeError(kind+' server exited')
  with socket.socket() as s:
   if s.connect_ex(('127.0.0.1',port))==0:return
  time.sleep(.1)
 raise RuntimeError(kind+' failed to start')
try:
 launch('auth',28648);launch('app',28649)
 scripts=sys.argv[1:] or ['e2e_races.py','api_integration.py','e2e_audit.py']
 if any(s not in ['e2e_races.py','api_integration.py','e2e_audit.py','m3_interview_e2e.py','profile_recovery_e2e.py','exploration_e2e.py','review_report_e2e.py','resume_documents_e2e.py','auth_verification_e2e.py'] for s in scripts):raise ValueError('Unknown test suite')
 for script in scripts:
  with open(EVIDENCE/(script.removesuffix('.py')+'.log'),'w') as log:
   subprocess.run([sys.executable,str(ROOT/'tests'/script)],cwd=ROOT,env=env,stdout=log,stderr=log,check=True)
  print('PASS',script,flush=True)
 with open(EVIDENCE/'unit-tests.log','w') as log:
  subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log,check=True)
 print('PASS backend unit/integration tests; all mock E2E flows. Real API is a separate explicit run.',flush=True)
finally:
 for process,log in reversed(processes):
  process.terminate()
  try:process.wait(timeout=8)
  except subprocess.TimeoutExpired:process.kill();process.wait()
  log.close()
