from pathlib import Path
import json,hashlib
from urllib.parse import urlparse
from bs4 import BeautifulSoup
p=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
sources=json.loads((p/'sources.json').read_text()); chunks=[json.loads(l) for l in (p/'chunks.jsonl').read_text().splitlines()];assert len(chunks)==len({x['chunk_id'] for x in chunks})
for m in sources:
 raw=(p/m['raw']).read_bytes();assert sha(raw)==m['raw_sha256'];s=BeautifulSoup(raw,'html.parser');rs=[x for x in chunks if x['source_id']==m['id']];assert len(rs)==m['chunk_count'];assert urlparse(m['url']).hostname.endswith('.cityu.edu.hk')
 for x in rs:
  assert x['source_url'].split('#')[0]==m['url'] and x['raw_sha256']==sha(raw) and x['text_sha256']==sha(x['text'].encode());anc=urlparse(x['source_url']).fragment;node=s.find(id=anc) if anc else s;assert x['text'] in ' '.join(node.get_text(' ',strip=True).split())
assert sum(m['chunk_count'] for m in sources)==len(chunks);print(f'PASS: {len(sources)} snapshots; {len(chunks)} verified chunks')
