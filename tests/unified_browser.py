"""Five-version browser acceptance with dedicated synthetic hosted QA accounts.
QA_ACCOUNTS_FILE is a private JSON file with two email/password fixtures.
This writes fictional materials to those accounts only; no model call is made.
Do not point it at ordinary users. Evidence remains gitignored.
"""
from pathlib import Path
import json,sys,os
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1]
out=Path(os.environ.get('QA_EVIDENCE_DIR',ROOT/'tests/evidence/unified'));out.mkdir(parents=True,exist_ok=True)
accounts=json.loads(Path(os.environ['QA_ACCOUNTS_FILE']).read_text())
assert len(accounts)==2 and all(a['email'].startswith('is5542-unified-qa-') and a['email'].endswith('@example.test') for a in accounts),'Dedicated synthetic QA accounts required'
a=accounts[1]
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:28814';results={}

with sync_playwright() as pw:
 b=pw.chromium.launch(channel='chrome',headless=True)
 for v in ['v1','v2','v3','v4','claude']:
  ctx=b.new_context(viewport={'width':1440,'height':960});p=ctx.new_page();p.set_default_timeout(60000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  try:
   p.goto(base+'/'+v+'/login');f=p.locator('.auth-card > form');f.locator('[name=email]').fill(a['email']);f.locator('[name=password]').fill(a['password']);f.locator('button').click()
   if v=='claude':
    p.locator('#work-resume').wait_for();rid='#work-resume';jid='#work-jd'
   else:p.locator('.workspace').wait_for();rid='#resume';jid='#jd'
   marker='FICTIONAL_BROWSER_'+v.upper()+'_UNIFIED_ACCEPTANCE'
   p.locator(rid).fill(marker+'\nExample Student, campus volunteer. Prepared fictional weekly reports using Excel.')
   with p.expect_response(lambda r:'/api/workspaces/' in r.url and r.request.method=='PUT' and r.status==200 and marker in json.dumps(r.request.post_data_json),timeout=60000):p.locator(jid).fill('Fictional Marketing Assistant. Coordinate campaigns and prepare weekly Excel reports.')
   if v=='claude':
    for name in ['简历优化','岗位匹配','模拟面试','设置','求职工作台']:
     p.locator('.sidebar').get_by_role('button',name=name,exact=True).click() if p.locator('.sidebar').count() else p.get_by_role('button',name=name,exact=True).first.click()
    p.locator('select').first.select_option('en');p.locator('select').first.select_option('zh-CN')
   else:
    nav=p.locator('aside nav')
    names=['简历优化','岗位匹配','模拟面试','设置','工作台']
    if v=='v4':names=['职业测评','面经复盘']+names
    for name in names:nav.get_by_role('button',name=name,exact=True).click()
    for language in ['EN','繁','简']:p.get_by_role('radio',name=language,exact=True).click()
   # Wait for the last queued save, rather than reloading during in-flight writes.
   p.wait_for_function("""async ([v,marker])=>{const key=Object.keys(localStorage).find(k=>k.startsWith('coach.auth.'));if(!key)return false;const a=JSON.parse(localStorage.getItem(key));const h={Authorization:'Bearer '+a.access_token};const rows=await (await fetch('/'+v+'/api/workspaces',{headers:h})).json();for(const row of rows){const r=await fetch('/'+v+'/api/workspaces/'+row.id,{headers:h});if(r.ok&&JSON.stringify((await r.json()).state).includes(marker))return true;}return false;}""",arg=[v,marker],timeout=60000)
   p.reload();p.locator(rid).wait_for();expect(p.locator(rid)).to_have_value(__import__('re').compile(marker))
   # Smoke mobile rendering without asserting old desktop-only layouts were redesigned.
   p.set_viewport_size({'width':390,'height':844});expect(p.locator('body')).to_be_visible();p.set_viewport_size({'width':1440,'height':960})
   assert not errors,errors
   p.screenshot(path=str(out/('browser-'+('local' if '127.0.0.1' in base else 'production')+'-'+v+'.png')),full_page=True)
   results[v]={'real_supabase_login':True,'materials_save_reload':True,'feature_navigation':True,'language_switch':True,'mobile_render':True,'page_errors':errors}
   print('PASS',v,'real browser login, materials save/reload, all module navigation, languages, responsive render',flush=True)
  except Exception:
   p.screenshot(path=str(out/('browser-failure-'+v+'.png')),full_page=True);(out/('browser-failure-'+v+'.txt')).write_text(p.locator('body').inner_text());raise
  finally:ctx.close()
 b.close()
(out/('five-version-browser-'+('local' if '127.0.0.1' in base else 'production')+'.json')).write_text(json.dumps(results,indent=2))
