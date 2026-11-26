"""Read public, server-rendered job postings, including schema.org JobPosting."""
import ipaddress
import json
import re
import socket
import ssl
import time
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import urlopen

import urllib3
from bs4 import BeautifulSoup

from coach.errors import CoachError
from coach.parsing import validate_text

INVALID = "请输入可公开访问的 HTTP 或 HTTPS 岗位链接。"
UNREADABLE = "无法读取岗位网页。请检查链接，或粘贴岗位描述。"
UNSUPPORTED = "未找到可读取的岗位说明。请粘贴职责和任职要求。"
TOO_LARGE = "岗位网页过大，请直接粘贴岗位描述。"


def public_addresses(host, port):
    addresses = [info[4][0] for info in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)]
    # Some desktop VPNs use the RFC 2544 benchmarking range for every DNS answer.
    # Resolve public hostnames independently, then apply the normal IP restrictions.
    benchmark = ipaddress.ip_network("198.18.0.0/15")
    if addresses and all(ipaddress.ip_address(a) in benchmark for a in addresses):
        if not re.fullmatch(r"(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,63}", host):
            raise ValueError
        if host.endswith((".local", ".localhost", ".internal", ".test", ".invalid")):
            raise ValueError
        query = urlencode({"name": host, "type": "A"})
        try:
            with urlopen("https://dns.google/resolve?" + query, timeout=4) as response:
                records = json.loads(response.read(65536))
            addresses = [a["data"] for a in records.get("Answer", []) if a.get("type") == 1]
        except (ValueError, KeyError, OSError):
            raise CoachError(UNREADABLE) from None
    return addresses


def target(url):
    try:
        p = urlsplit(url)
        if (p.scheme not in {"http", "https"} or not p.hostname or p.username is not None
                or p.password is not None or len(url) > 4096 or re.search(r"[\s\\\x00-\x1f]", url)):
            raise ValueError
        port = 443 if p.scheme == "https" else 80
        if p.port not in {None, port}:
            raise ValueError
        host = p.hostname.encode("idna").decode("ascii")
        addresses = public_addresses(host, port)
        for addr in addresses:
            ip = ipaddress.ip_address(addr)
            if not ip.is_global or ip.is_multicast or getattr(ip, "ipv4_mapped", None) or getattr(ip, "sixtofour", None) or getattr(ip, "teredo", None) or "%" in addr:
                raise ValueError
        if not addresses:
            raise ValueError
        return p, host, port, addresses[0]
    except (ValueError, UnicodeError, OSError):
        raise CoachError(INVALID) from None


def posting(node):
    if isinstance(node, dict):
        types = node.get("@type", [])
        if "JobPosting" in ([types] if isinstance(types, str) else types or []) and isinstance(node.get("description"), str):
            return node["description"]
        return posting(list(node.values()))
    if isinstance(node, list):
        for item in node:
            found = posting(item)
            if found:
                return found
    return None


def extract(data):
    soup = BeautifulSoup(data, "html.parser")
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            desc = posting(json.loads(script.get_text()))
        except (ValueError, TypeError, RecursionError):
            continue
        if desc:
            return validate_text(BeautifulSoup(desc, "html.parser").get_text("\n", strip=True), "JD")
    for tag in soup.select("script,style,noscript,nav,footer,header,form,aside,button,svg"):
        tag.decompose()
    main = (soup.select_one('[itemprop="description"], #jobDescriptionText, .job__description, .job-description')
            or soup.select_one("article") or soup.select_one("main") or soup.body or soup)
    text = main.get_text("\n", strip=True)
    if not re.search(r"responsibilit|qualifications?|requirements?|what you.ll do|what you.ll bring|任职|任職|职责|職責|要求|條件|条件", text, re.I):
        raise CoachError(UNSUPPORTED)
    return validate_text(text, "JD")


def import_job(url):
    deadline = time.monotonic() + 18
    for _ in range(5):
        p, host, port, ip = target(url)
        authority = f"[{host}]" if ":" in host else host
        pool = (urllib3.HTTPSConnectionPool(ip, port, server_hostname=host, assert_hostname=host,
                                            ssl_context=ssl.create_default_context())
                if p.scheme == "https" else urllib3.HTTPConnectionPool(ip, port))
        response = None
        try:
            if time.monotonic() >= deadline:
                raise CoachError(UNREADABLE)
            response = pool.urlopen("GET", urlunsplit(("", "", p.path or "/", p.query, "")),
                                    headers={"Host": authority, "User-Agent": "CareerCoach/1.0", "Accept-Encoding": "identity"},
                                    redirect=False, retries=False, preload_content=False,
                                    timeout=urllib3.Timeout(connect=4, read=5))
            if response.status in {301, 302, 303, 307, 308} and response.headers.get("Location"):
                url = urljoin(url, response.headers["Location"])
                continue
            if response.status != 200:
                raise CoachError(UNREADABLE)
            if response.headers.get("Content-Type", "").split(";")[0].strip().lower() not in {"text/html", "application/xhtml+xml"}:
                raise CoachError(UNSUPPORTED)
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise CoachError(UNSUPPORTED)
            data = bytearray()
            for chunk in response.stream(32768, decode_content=False):
                data.extend(chunk)
                if len(data) > 2_000_000:
                    raise CoachError(TOO_LARGE)
                if time.monotonic() >= deadline:
                    raise CoachError(UNREADABLE)
            return extract(bytes(data))
        except (urllib3.exceptions.HTTPError, OSError, UnicodeError):
            raise CoachError(UNREADABLE) from None
        finally:
            if response:
                response.close()
            pool.close()
    raise CoachError(UNREADABLE)

