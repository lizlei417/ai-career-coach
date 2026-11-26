"""Real public pages, actual importer and sockets. No model or fake JD content."""
import asyncio,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app import job_import as ji
from public_dns import PublicDNSResolver
ji.PublicResolver=PublicDNSResolver
E=Path(__file__).resolve().parent/'evidence/jd-import'
urls=[(x['name'],x['url']) for x in json.loads((Path(__file__).resolve().parent/'jd_sources.json').read_text())]
async def main():
 out=[]
 for name,url in urls:
  try:
   r=await ji.fetch_job_posting(url);(E/(name+'-import.txt')).write_text(r['text']);out.append({'name':name,'url':url,'ok':True,'chars':len(r['text']),'source':r['source'],'title':r['title'],'company':r['company'],'location':r['location'],'import_id':r['import_id']})
  except Exception as e:out.append({'name':name,'url':url,'ok':False,'code':getattr(e,'code',type(e).__name__),'detail':getattr(e,'detail',str(e))})
  print(json.dumps(out[-1],ensure_ascii=False),flush=True)
 (E/'local-live-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
asyncio.run(main())
