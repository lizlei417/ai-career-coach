"""Public JD import: bounded downloads, pinned public DNS, structured job parsers.
No browser automation, credentials, model calls, CAPTCHA or access bypasses.
"""
from __future__ import annotations
import asyncio
import contextlib
import ipaddress
import json
import logging
import re
import socket
import time
import zlib
from dataclasses import dataclass
from html import unescape
from uuid import uuid4
from urllib.parse import urljoin, parse_qs

import httpcore
import httpx
from bs4 import BeautifulSoup
from .errors import AppError
from .config import MAX_TEXT_CHARS

log = logging.getLogger('coach.jd_import')
MAX_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
TOTAL_SECONDS = 28

class ImportError(AppError):
    def __init__(self, code, stage, status=None, reason=''):
        self.stage, self.upstream_status, self.reason = stage, status, reason
        super().__init__(code, 422, f'stage={stage};status={status or "none"};reason={reason}'[:200])


def validate_url(value: str) -> httpx.URL:
    try:
        url = httpx.URL(value.strip())
        if (url.scheme not in ('http','https') or not url.host or url.userinfo or
                url.port not in (None,80,443) or '%' in url.host or '\\' in value or
                any(ord(c)<32 for c in value)):
            raise ValueError()
        if url.host.lower().rstrip('.') in ('localhost','localhost.localdomain'):
            raise ImportError('URL_UNSAFE','validate',reason='private_host')
        return url
    except ImportError:
        raise
    except (ValueError, httpx.InvalidURL):
        raise ImportError('URL_INVALID','validate',reason='invalid_url') from None


def public_ip(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
        return ip.is_global and not ip.is_multicast and not (
            isinstance(ip,ipaddress.IPv6Address) and (ip.ipv4_mapped or ip.sixtofour or ip.teredo))
    except ValueError:
        return False


class PublicResolver:
    """Resolve once per host/import and pin these exact addresses for the socket."""
    def __init__(self): self.cache = {}
    async def addresses(self, host: str, port: int) -> list[str]:
        key=(host,port)
        if key not in self.cache:
            try:
                infos=await asyncio.wait_for(asyncio.get_running_loop().getaddrinfo(host,port,type=socket.SOCK_STREAM),5)
            except (socket.gaierror,UnicodeError):
                raise ImportError('URL_DNS','dns',reason='resolution_failed') from None
            except asyncio.TimeoutError:
                raise ImportError('URL_TIMEOUT','dns',reason='resolution_timeout') from None
            ips=list(dict.fromkeys(info[4][0] for info in infos))
            if not ips or not all(public_ip(ip) for ip in ips):
                raise ImportError('URL_UNSAFE','dns',reason='non_public_address')
            self.cache[key]=sorted(ips,key=lambda ip:':' in ip)
        return self.cache[key]


class PublicBackend(httpcore.AsyncNetworkBackend):
    def __init__(self,resolver): self.resolver,self.backend=resolver,httpcore.AnyIOBackend()
    async def connect_tcp(self,host,port,timeout=None,local_address=None,socket_options=None):
        addresses=await self.resolver.addresses(host,port)
        # The TLS upgrade is still performed by httpcore with the ORIGINAL host.
        # Only the TCP destination changes to the already-validated numeric IP.
        for index,ip in enumerate(addresses[:2]):
            try:return await self.backend.connect_tcp(ip,port,timeout=timeout,local_address=local_address,socket_options=socket_options)
            except (httpcore.ConnectError,httpcore.ConnectTimeout):
                if index==min(len(addresses),2)-1:raise
    async def connect_unix_socket(self,*args,**kwargs):
        raise ImportError('URL_UNSAFE','connect',reason='unix_socket')
    async def sleep(self,seconds): await asyncio.sleep(seconds)


@contextlib.contextmanager
def map_network_errors():
    try:yield
    except (httpcore.TimeoutException,httpcore.NetworkError,httpcore.ProtocolError) as exc:
        name=type(exc).__name__
        cls=getattr(httpx,name,httpx.RequestError)
        raise cls(name) from None

class CoreStream(httpx.AsyncByteStream):
    def __init__(self,stream): self.stream=stream
    async def __aiter__(self):
        with map_network_errors():
            async for chunk in self.stream:yield chunk
    async def aclose(self):await self.stream.aclose()

class PublicTransport(httpx.AsyncBaseTransport):
    def __init__(self,resolver):
        self.pool=httpcore.AsyncConnectionPool(network_backend=PublicBackend(resolver),max_connections=4,retries=0)
    async def handle_async_request(self,request):
        with map_network_errors():
            response=await self.pool.handle_async_request(httpcore.Request(
                method=request.method,url=httpcore.URL(scheme=request.url.raw_scheme,host=request.url.raw_host,port=request.url.port,target=request.url.raw_path),
                headers=request.headers.raw,content=request.stream,extensions=request.extensions))
        return httpx.Response(response.status,headers=response.headers,stream=CoreStream(response.stream),extensions=response.extensions)
    async def aclose(self):await self.pool.aclose()


def make_client(resolver):
    return httpx.AsyncClient(transport=PublicTransport(resolver),trust_env=False,follow_redirects=False,
        timeout=httpx.Timeout(10,connect=5),headers={
            'User-Agent':'AI-Career-Coach/3.0 (public job description reader)',
            'Accept':'text/html,application/json,application/xhtml+xml;q=0.9,*/*;q=0.5',
            'Accept-Language':'en,zh-CN;q=0.9,zh-TW;q=0.8','Accept-Encoding':'gzip, deflate'})


def tidy(text):
    text=str(text or '').replace('\r','').replace('\u00a0',' ')
    return '\n'.join(re.sub(r'[\t ]+',' ',line).strip() for line in text.splitlines() if line.strip()).strip()


def html_text(markup):
    s=BeautifulSoup(markup,'html.parser')
    for el in s.select('script,style,noscript,nav,header,footer,aside,form,button,iframe,svg,[hidden],[aria-hidden="true"]'):el.decompose()
    for br in s.find_all('br'):br.replace_with('\n')
    for li in s.find_all('li'):li.insert_before('\n• ');li.append('\n')
    for el in s.find_all(['p','div','section','h1','h2','h3','h4','dl','dt','dd']):el.insert_before('\n');el.append('\n')
    return tidy(s.get_text(' ',strip=False))


def clean_markup(content):
    for _ in range(2):
        decoded=unescape(content)
        if decoded==content:break
        content=decoded
    return html_text(content)


def result(title,body,company='',location='',source='html',status=''):
    body=tidy(body)
    if len(re.sub(r'\s','',body))<80:
        raise ImportError('URL_NO_CONTENT','parse',200,'no_job_description')
    prefix=[tidy(title)] if title else []
    if company:prefix.append('Company: '+tidy(company))
    if location:prefix.append('Location: '+tidy(location))
    if status:prefix.append(status)
    text='\n'.join(prefix+[body])
    if len(text)>MAX_TEXT_CHARS:
        raise ImportError('URL_TOO_LARGE','parse',200,'job_text_limit')
    return dict(title=tidy(title)[:160],text=text,company=tidy(company),location=tidy(location),source=source)


def json_objects(value):
    if isinstance(value,dict):
        yield value
        for k in ('@graph','mainEntity'):
            yield from json_objects(value.get(k))
    elif isinstance(value,list):
        for item in value:yield from json_objects(item)


def parse_html(text,url):
    s=BeautifulSoup(text,'html.parser')
    page_title=s.title.get_text(' ',strip=True) if s.title else ''
    if re.search(r'(just a moment|access denied|security (check|verification)|captcha|安全验证|访问受限)',page_title,re.I):
        raise ImportError('URL_ACCESS_DENIED','parse',200,'access_challenge')
    for script in s.select('script[type="application/ld+json"]'):
        try:values=list(json_objects(json.loads(script.string or script.get_text())))
        except (ValueError,TypeError):continue
        for job in values:
            if 'JobPosting' not in (job.get('@type') if isinstance(job.get('@type'),list) else [job.get('@type')]):continue
            desc=job.get('description')
            if not isinstance(desc,str) or not desc.strip():continue
            org=job.get('hiringOrganization') or {};company=org.get('name','') if isinstance(org,dict) else ''
            places=job.get('jobLocation') or []
            places=places if isinstance(places,list) else [places]
            location=[]
            for place in places:
                if isinstance(place,dict):
                    address=place.get('address') or {}
                    if isinstance(address,dict):location.append(', '.join(str(address[k]) for k in ['addressLocality','addressRegion','addressCountry'] if isinstance(address.get(k),str)))
                    elif isinstance(address,str):location.append(address)
            parts=[clean_markup(desc)]
            for key,label in [('responsibilities','Responsibilities'),('qualifications','Qualifications'),('skills','Skills'),('experienceRequirements','Experience requirements')]:
                value=job.get(key)
                if isinstance(value,str) and value and value not in desc:parts.append(label+'\n'+clean_markup(value))
            return result(job.get('title',''),'\n'.join(parts),company,'; '.join(location),'json_ld')
    h1=s.find('h1');title=h1.get_text(' ',strip=True) if h1 else (s.title.get_text(' ',strip=True) if s.title else '')
    # Nowcoder publishes a real server-rendered job-specific container.
    if url.host in ('www.nowcoder.com','nowcoder.com'):
        node=s.select_one('.job-detail-infos')
        if node:
            location_node=node.find('iconweizhi')
            location=location_node.parent.get_text(' ',strip=True) if location_node else ''
            if location_node:location_node.parent.decompose()
            for extra in node.select('jobkeys,.deliver-range'):extra.decompose()
            empty_label=node.find(string=lambda t:t and t.strip()=='岗位关键词')
            if empty_label:empty_label.parent.decompose()
            company=''
            if s.title:
                parts=s.title.get_text().split('_')
                if len(parts)>2:company=re.sub(r'(实习|校招|社招)$','',parts[-2])
            closed=bool(s.find(string=lambda t:t and t.strip()=='已结束'))
            return result(title,html_text(str(node)),company,location,source='nowcoder_html',status='职位状态：已结束' if closed else '')
    # Prefer job-specific scopes. Never fall back to the entire navigation-heavy body.
    selectors=['[itemprop="description"]','.job-description','#job-description','.job_description','#jobDescription',
               '.posting-page .content','.posting','.job-detail','#content .job-post','article','main']
    node=next((s.select_one(selector) for selector in selectors if s.select_one(selector)),None)
    if node:
        article=node if node.name=='article' else node.find_parent('article')
        heading=node.find('h1') or (article.find('h1') if article else None)
        if heading:
            for badge in heading.select('.listing-new'):badge.decompose()
            listing_name=heading.select_one('.listing-company-name')
            title=listing_name.get_text('\n',strip=True).splitlines()[0] if listing_name else heading.get_text(' ',strip=True)
        for extra in node.select('[class*="recommend"],[class*="related-job"],[class*="cookie"],[class*="advert"],.application,.apply'):
            extra.decompose()
        body=html_text(str(node))
    else:
        short=s.get_text(' ',strip=True)
        if len(short)<2000 and re.search(r'(verify (you are|that you)|complete the security check|访问过于频繁|请完成安全验证)',short,re.I):
            raise ImportError('URL_ACCESS_DENIED','parse',200,'access_challenge')
        raise ImportError('URL_NO_CONTENT','parse',200,'no_job_scope')
    # A generic main/article still needs an actual job heading or responsibilities.
    if not re.search(r'(responsibilit|qualificat|requirement|what you.ll|your (role|mission)|about (the|this) (role|job)|岗位|职位|職位|任职|职责|職責)',body,re.I):
        raise ImportError('URL_NO_CONTENT','parse',200,'no_job_sections')
    if re.search(r'(just a moment|verify (you are|that you)|enable javascript and cookies|captcha|access denied)',title+'\n'+body,re.I):
        raise ImportError('URL_ACCESS_DENIED','parse',200,'access_challenge')
    if re.search(r'\b\d+ jobs\b|\b(search jobs|all jobs|open positions)\b',title,re.I):
        raise ImportError('URL_NO_CONTENT','parse',200,'job_listing_not_detail')
    company=location=''
    company_node=s.select_one('.listing-company-name')
    if company_node:
        lines=company_node.get_text('\n',strip=True).splitlines()
        if len(lines)>1:company=lines[-1]
    location_node=s.select_one('.listing-location')
    if location_node:location=location_node.get_text(' ',strip=True)
    return result(title,body,company,location,source='html')


def provider(url):
    parts=[p for p in url.path.split('/') if p]
    if url.host in ('job-boards.greenhouse.io','boards.greenhouse.io','job-boards.eu.greenhouse.io','boards.eu.greenhouse.io'):
        if len(parts)>=3 and parts[1]=='jobs' and re.fullmatch(r'[a-zA-Z0-9_-]+',parts[0]) and parts[2].isdigit():
            base='boards-api.eu.greenhouse.io' if '.eu.' in url.host else 'boards-api.greenhouse.io'
            return 'greenhouse',f'https://{base}/v1/boards/{parts[0]}/jobs/{parts[2]}',parts[0]
        query=parse_qs(url.query.decode())
        if url.path.endswith('embed/job_app') and query.get('for') and query.get('token'):
            board,job=query['for'][0],query['token'][0]
            if re.fullmatch(r'[a-zA-Z0-9_-]+',board) and job.isdigit():return 'greenhouse',f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job}',board
    if url.host in ('jobs.lever.co','jobs.eu.lever.co') and len(parts)>=2:
        if re.fullmatch(r'[a-zA-Z0-9_-]+',parts[0]) and re.fullmatch(r'[0-9a-fA-F-]{36}',parts[1]):
            base='api.eu.lever.co' if '.eu.' in url.host else 'api.lever.co'
            return 'lever',f'https://{base}/v0/postings/{parts[0]}/{parts[1]}',parts[0]
    return None


def parse_provider(kind,data,board):
    if not isinstance(data,dict):raise ImportError('URL_NO_CONTENT','parse',200,'invalid_provider_object')
    if kind=='greenhouse':
        return result(data.get('title',''),clean_markup(data.get('content','')),data.get('company_name',''),(data.get('location') or {}).get('name',''),'greenhouse_api')
    body=[data.get('descriptionPlain') or clean_markup(data.get('description',''))]
    for item in data.get('lists') or []:
        if isinstance(item,dict):body.append(str(item.get('text') or '')+'\n'+clean_markup(item.get('content','')))
    tail=data.get('additionalPlain') or clean_markup(data.get('additional',''))
    if tail:body.append(tail)
    categories=data.get('categories') or {}
    return result(data.get('text',''),'\n'.join(body),board,categories.get('location',''),'lever_api')


@dataclass
class Download:
    url: httpx.URL
    status: int
    text: str
    content: bytes
    content_type: str


async def read_bounded(response):
    # Do not reconstruct a Response with the original gzip header after decoding.
    # Raw wire bytes are decoded ONCE with an explicit decompressed-size bound.
    if response.is_stream_consumed:
        data=response.content
        if len(data)>MAX_BYTES:raise ImportError('URL_TOO_LARGE','read',response.status_code,'decoded_size')
        return data
    coding=response.headers.get('content-encoding','identity').lower().strip()
    if coding not in ('identity','','gzip','deflate'):
        raise ImportError('URL_DECODE','decode',response.status_code,'unsupported_encoding')
    decoder=zlib.decompressobj(16+zlib.MAX_WBITS if coding=='gzip' else zlib.MAX_WBITS) if coding in ('gzip','deflate') else None
    data=bytearray();wire=0;first=True
    try:
        async for chunk in response.aiter_raw(chunk_size=16384):
            wire+=len(chunk)
            if wire>MAX_BYTES:raise ImportError('URL_TOO_LARGE','read',response.status_code,'wire_size')
            try:decoded=decoder.decompress(chunk,MAX_BYTES-len(data)+1) if decoder else chunk
            except zlib.error:
                if coding!='deflate' or not first:raise
                decoder=zlib.decompressobj(-zlib.MAX_WBITS);decoded=decoder.decompress(chunk,MAX_BYTES-len(data)+1)
            first=False;data.extend(decoded)
            if len(data)>MAX_BYTES:raise ImportError('URL_TOO_LARGE','read',response.status_code,'decoded_size')
        if decoder and not decoder.eof:raise zlib.error('incomplete compressed response')
    except zlib.error:
        raise ImportError('URL_DECODE','decode',response.status_code,'invalid_compressed_body') from None
    return bytes(data)


async def download(client,resolver,value,request_id):
    url=validate_url(value)
    for hop in range(MAX_REDIRECTS+1):
        await resolver.addresses(url.host,url.port or (443 if url.scheme=='https' else 80))
        log.info('jd_import id=%s stage=fetch host=%s hop=%s',request_id,url.host,hop)
        async with client.stream('GET',url) as r:
            log.info('jd_import id=%s stage=http host=%s status=%s encoding=%s',request_id,url.host,r.status_code,r.headers.get('content-encoding','identity'))
            if r.is_redirect:
                location=r.headers.get('location')
                if not location or hop==MAX_REDIRECTS:raise ImportError('URL_REDIRECT','redirect',r.status_code,'redirect_limit_or_missing_location')
                url=validate_url(urljoin(str(url),location));continue
            if r.status_code in (404,410):raise ImportError('URL_NOT_FOUND','http',r.status_code,'not_found')
            if r.status_code in (401,403,407,451):raise ImportError('URL_ACCESS_DENIED','http',r.status_code,'access_denied')
            if r.status_code==429:raise ImportError('URL_RATE_LIMIT','http',429,'rate_limited')
            if r.status_code>=400:raise ImportError('URL_HTTP_ERROR','http',r.status_code,'upstream_error')
            data=await read_bounded(r)
            # Only Content-Type is needed for charset decoding. The body is decoded.
            decoded=httpx.Response(r.status_code,headers={'content-type':r.headers.get('content-type','')},content=data)
            return Download(url,r.status_code,decoded.text,data,r.headers.get('content-type','').lower())


async def fetch_job_posting(value):
    request_id=uuid4().hex[:12];start=time.monotonic();host='';stage='validate'
    async def run():
        nonlocal host,stage
        url=validate_url(value);host=url.host
        resolver=PublicResolver();stage='dns'
        # Validate the user-provided host even when routing to an official API.
        await resolver.addresses(url.host,url.port or (443 if url.scheme=='https' else 80))
        route=provider(url)
        async with make_client(resolver) as client:
            stage='fetch'
            target=route[1] if route else str(url)
            fetched=await download(client,resolver,target,request_id)
            stage='parse'
            if route:
                try:data=json.loads(fetched.text)
                except ValueError:raise ImportError('URL_NO_CONTENT','parse',fetched.status,'provider_invalid_json') from None
                out=parse_provider(route[0],data,route[2])
            elif 'pdf' in fetched.content_type:
                from .materials import pdf_to_text
                out=result('',pdf_to_text(fetched.content)['text'],source='pdf')
            elif 'html' in fetched.content_type or 'text' in fetched.content_type:
                out=parse_html(fetched.text,fetched.url)
            else:raise ImportError('URL_NO_CONTENT','parse',fetched.status,'unsupported_content_type')
            out['url']=str(url);out['import_id']=request_id
            log.info('jd_import id=%s stage=done host=%s status=%s source=%s chars=%s elapsed_ms=%s',request_id,host,fetched.status,out['source'],len(out['text']),int((time.monotonic()-start)*1000))
            return out
    try:
        return await asyncio.wait_for(run(),TOTAL_SECONDS)
    except (asyncio.TimeoutError,httpx.TimeoutException) as exc:
        phase='read' if isinstance(exc,httpx.ReadTimeout) else 'connect' if isinstance(exc,httpx.ConnectTimeout) else stage
        error=ImportError('URL_TIMEOUT',phase,reason=type(exc).__name__)
    except ImportError as exc:error=exc
    except httpx.DecodingError as exc:error=ImportError('URL_DECODE','decode',reason=type(exc).__name__)
    except httpx.RequestError as exc:error=ImportError('URL_NETWORK','connect' if isinstance(exc,httpx.ConnectError) else stage,reason=type(exc).__name__)
    except Exception as exc:
        error=ImportError('URL_SERVER',stage,reason=type(exc).__name__)
    log.warning('jd_import id=%s stage=%s host=%s status=%s code=%s reason=%s elapsed_ms=%s',request_id,error.stage,host,error.upstream_status,error.code,error.reason,int((time.monotonic()-start)*1000))
    error.detail += ';id='+request_id
    raise error
