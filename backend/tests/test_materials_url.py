"""Deterministic failure/safety regressions. Real external success is tested separately."""
import asyncio,gzip,json,socket,unittest,zlib
from unittest.mock import patch,AsyncMock
import httpx
from app import job_import as ji
from app.errors import AppError

BODY='<main><h1>Marketing Assistant</h1><h2>Responsibilities</h2><p>Support marketing campaigns and prepare weekly reports using Excel. Coordinate content and collect customer feedback with the communications team.</p></main>'
URL='https://careers.example.test/job'
def response(text=BODY,status=200,headers=None):
 return httpx.Response(status,headers=headers or {'content-type':'text/html; charset=utf-8'},stream=httpx.ByteStream(text.encode() if isinstance(text,str) else text))
async def public(self,host,port):
 try:
  if not ji.public_ip(host):
   import ipaddress
   ipaddress.ip_address(host)
   raise ji.ImportError('URL_UNSAFE','dns',reason='non_public_address')
 except ValueError:pass
 return ['93.184.216.34']

class UrlTests(unittest.IsolatedAsyncioTestCase):
 async def fetch(self,handler,url=URL):
  with patch.object(ji.PublicResolver,'addresses',public),patch.object(ji,'make_client',lambda resolver:httpx.AsyncClient(transport=httpx.MockTransport(handler),follow_redirects=False)):
   return await ji.fetch_job_posting(url)
 async def test_gzip_is_decoded_exactly_once(self):
  out=await self.fetch(lambda req:response(gzip.compress(BODY.encode()),headers={'content-type':'text/html; charset=utf-8','content-encoding':'gzip'}))
  self.assertIn('weekly reports',out['text']);self.assertEqual(out['source'],'html')
 async def test_deflate_and_charset(self):
  for data in [zlib.compress(BODY.encode()),zlib.compress(BODY.encode())[2:-4]]:
   out=await self.fetch(lambda req:response(data,headers={'content-type':'text/html','content-encoding':'deflate'}));self.assertIn('weekly reports',out['text'])
  text='<main><h1>运营专员</h1><h2>岗位职责</h2><p>'+('负责营销活动及数据分析，协助跟进产品迭代和用户反馈。'*8)+'</p></main>'
  out=await self.fetch(lambda req:response(text.encode('gb18030'),headers={'content-type':'text/html; charset=gb18030'}));self.assertIn('运营专员',out['text'])
 async def test_http_statuses(self):
  for status,code in [(401,'URL_ACCESS_DENIED'),(403,'URL_ACCESS_DENIED'),(404,'URL_NOT_FOUND'),(410,'URL_NOT_FOUND'),(429,'URL_RATE_LIMIT'),(503,'URL_HTTP_ERROR')]:
   with self.assertRaises(ji.ImportError) as e:await self.fetch(lambda req:response('',status))
   self.assertEqual(e.exception.code,code);self.assertEqual(e.exception.upstream_status,status);self.assertEqual(e.exception.stage,'http')
 async def test_timeout_and_network(self):
  for cls,code in [(httpx.ReadTimeout,'URL_TIMEOUT'),(httpx.ConnectError,'URL_NETWORK')]:
   def fail(req):raise cls('test-only',request=req)
   with self.assertRaises(AppError) as e:await self.fetch(fail)
   self.assertEqual(e.exception.code,code)
 async def test_total_budget(self):
  async def slow(req):await asyncio.sleep(.1);return response()
  with patch.object(ji,'TOTAL_SECONDS',.02):
   with self.assertRaises(AppError) as e:await self.fetch(slow)
   self.assertEqual(e.exception.code,'URL_TIMEOUT')
 async def test_size_limits_and_corrupt_compression(self):
  for data,headers,code in [(b'x'*(ji.MAX_BYTES+1),None,'URL_TOO_LARGE'),(gzip.compress(b'x'*(ji.MAX_BYTES+1)),{'content-type':'text/html','content-encoding':'gzip'},'URL_TOO_LARGE'),(b'bad gzip',{'content-type':'text/html','content-encoding':'gzip'},'URL_DECODE')]:
   with self.assertRaises(AppError) as e:await self.fetch(lambda req:response(data,headers=headers))
   self.assertEqual(e.exception.code,code)
 async def test_redirect_private_and_limit(self):
  seen=[]
  def redirect(req):seen.append(str(req.url));return response('',302,{'location':'http://169.254.169.254/latest/meta-data'})
  with self.assertRaises(AppError) as e:await self.fetch(redirect)
  self.assertEqual(e.exception.code,'URL_UNSAFE');self.assertEqual(len(seen),1)
  with self.assertRaises(AppError) as e:await self.fetch(lambda req:response('',302,{'location':'/again'}))
  self.assertEqual(e.exception.code,'URL_REDIRECT')
 async def test_empty_or_non_job_page(self):
  for body in ['<body>Login</body>','<main><h1>Example Domain</h1><p>'+('Not a job. '*30)+'</p></main>']:
   with self.assertRaises(AppError) as e:await self.fetch(lambda req:response(body))
   self.assertEqual(e.exception.code,'URL_NO_CONTENT')
 async def test_json_ld_graph_and_noise(self):
  data={'@graph':[{'@type':'JobPosting','title':'Research Associate','hiringOrganization':{'name':'Example Ltd'},'jobLocation':{'address':{'addressLocality':'Hong Kong'}},'description':'<h2>Responsibilities</h2><p>'+('Analyse campaign data and communicate findings to the team. '*4)+'</p>'}]}
  html='<nav>UNRELATED NAVIGATION</nav><script type="application/ld+json">'+json.dumps(data)+'</script><footer>UNRELATED FOOTER</footer>'
  out=await self.fetch(lambda req:response(html));self.assertEqual(out['source'],'json_ld');self.assertEqual(out['company'],'Example Ltd');self.assertEqual(out['location'],'Hong Kong');self.assertNotIn('UNRELATED',out['text'])
 async def test_scoped_job_heading_ignores_site_heading(self):
  html='<main><h1>22 jobs on the Job Board</h1><article><h1 class="listing-company"><span class="listing-company-name">Data Engineer<br>Example Institute</span><span class="listing-location">Hong Kong</span></h1><div class="job-description"><h2>Requirements</h2><p>'+('Build reliable Python systems and prepare analytical reports with the team. '*3)+'</p></div><aside>RECOMMENDED JOBS</aside></article></main>'
  out=await self.fetch(lambda req:response(html));self.assertEqual(out['title'],'Data Engineer');self.assertEqual(out['company'],'Example Institute');self.assertNotIn('RECOMMENDED JOBS',out['text'])
 async def test_listing_is_not_a_job_detail(self):
  html='<main><h1>22 jobs on the Job Board</h1><h2>Requirements</h2><p>'+('Many different jobs are listed here. '*6)+'</p></main>'
  with self.assertRaises(AppError) as e:await self.fetch(lambda req:response(html))
  self.assertEqual(e.exception.code,'URL_NO_CONTENT')
 async def test_greenhouse_api_and_entity_escaped_content(self):
  seen=[]
  def reply(req):
   seen.append(str(req.url));return response(json.dumps({'title':'Product Intern','company_name':'Example','location':{'name':'Remote'},'content':'&lt;h2&gt;Responsibilities&lt;/h2&gt;&lt;p&gt;'+('Support research and product analysis. '*5)+'&lt;/p&gt;'}),headers={'content-type':'application/json'})
  out=await self.fetch(reply,'https://job-boards.greenhouse.io/example/jobs/123?tracking=ignored')
  self.assertEqual(seen,['https://boards-api.greenhouse.io/v1/boards/example/jobs/123']);self.assertEqual(out['source'],'greenhouse_api');self.assertIn('Responsibilities',out['text']);self.assertNotIn('&lt;',out['text'])
 async def test_lever_api_keeps_lists(self):
  seen=[];pid='2a55d6c9-c564-443a-be3e-a3851db5a93b'
  def reply(req):
   seen.append(str(req.url));return response(json.dumps({'text':'Engineer','descriptionPlain':'Build reliable systems and collaborate with the engineering team. '*3,'categories':{'location':'London'},'lists':[{'text':'Requirements','content':'<li>Python and SQL</li>'}]}),headers={'content-type':'application/json'})
  out=await self.fetch(reply,'https://jobs.eu.lever.co/example/'+pid)
  self.assertEqual(seen,['https://api.eu.lever.co/v0/postings/example/'+pid]);self.assertIn('Python and SQL',out['text']);self.assertEqual(out['source'],'lever_api')
 async def test_invalid_urls(self):
  for value in ['not a link','file:///etc/passwd','ftp://example.com','https://user:password@example.com/','http://localhost/','https://example.com:9999/','https://example.com\\@127.0.0.1/']:
   with self.assertRaises(AppError):await self.fetch(lambda req:response(),value)
 async def test_real_resolver_blocks_private_mixed_and_special_ips(self):
  loop=asyncio.get_running_loop()
  for ips in [['127.0.0.1'],['10.0.0.1'],['169.254.169.254'],['100.64.0.1'],['::1'],['::ffff:127.0.0.1'],['93.184.216.34','192.168.1.1'],['198.18.0.1']]:
   infos=[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443)) for ip in ips]
   with patch.object(loop,'getaddrinfo',AsyncMock(return_value=infos)):
    with self.assertRaises(AppError) as e:await ji.PublicResolver().addresses('example.test',443)
    self.assertEqual(e.exception.code,'URL_UNSAFE')
 async def test_dns_is_pinned_to_checked_socket_address(self):
  loop=asyncio.get_running_loop();resolver=ji.PublicResolver();public_info=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))]
  with patch.object(loop,'getaddrinfo',AsyncMock(side_effect=[public_info,[(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]])) as dns:
   await resolver.addresses('example.test',443)
   backend=ji.PublicBackend(resolver)
   with patch.object(backend.backend,'connect_tcp',AsyncMock(return_value='stream')) as tcp:
    self.assertEqual(await backend.connect_tcp('example.test',443),'stream');self.assertEqual(tcp.call_args.args[0],'93.184.216.34');self.assertEqual(dns.call_count,1)
 async def test_dns_failure_and_server_failure(self):
  with patch.object(asyncio.get_running_loop(),'getaddrinfo',AsyncMock(side_effect=socket.gaierror())):
   with self.assertRaises(AppError) as e:await ji.PublicResolver().addresses('missing.test',443)
   self.assertEqual(e.exception.code,'URL_DNS')
  with patch.object(ji.PublicResolver,'addresses',public),patch.object(ji,'make_client',side_effect=RuntimeError('synthetic exception')):
   with self.assertRaises(AppError) as e:await ji.fetch_job_posting(URL)
   self.assertEqual(e.exception.code,'URL_SERVER');self.assertIn('RuntimeError',e.exception.detail)
