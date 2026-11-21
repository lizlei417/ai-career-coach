"""LOCAL QA ONLY: use real public DNS answers when this Mac's VPN returns
198.18.0.0/15 fake-IP mappings. HTTP responses are never mocked here; the app
still connects to the validated public numeric IP and verifies the original TLS
hostname. Production uses the normal resolver and does not import this file.
"""
import ipaddress,socket,asyncio
import httpx
from app import job_import as ji

class PublicDNSResolver(ji.PublicResolver):
 async def addresses(self,host,port):
  try:return await super().addresses(host,port)
  except ji.ImportError as error:
   if error.code!='URL_UNSAFE':raise
   infos=await asyncio.get_running_loop().getaddrinfo(host,port,type=socket.SOCK_STREAM)
   if not infos or not all(ipaddress.ip_address(i[4][0]) in ipaddress.ip_network('198.18.0.0/15') for i in infos):raise
   if host != 'httpbingo.org' and not host.endswith(('.greenhouse.io','.lever.co','.python.org')):raise
   async with httpx.AsyncClient(timeout=10) as c:
    r=await c.get('https://dns.google/resolve',params={'name':host,'type':'A'});r.raise_for_status()
   ips=[x['data'] for x in r.json().get('Answer',[]) if x.get('type')==1]
   if not ips or not all(ji.public_ip(ip) for ip in ips):raise error
   self.cache[(host,port)]=ips
   return ips
