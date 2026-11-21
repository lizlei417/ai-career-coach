import unittest
from unittest.mock import patch
import httpx
from app.materials import fetch_job_posting
from app.errors import AppError

class UrlTests(unittest.IsolatedAsyncioTestCase):
 async def test_extract_actual_html(self):
  original=httpx.AsyncClient
  text='Support marketing campaigns and coordinate weekly campaign reports with the communications team. '
  def response(req):return httpx.Response(200,headers={'content-type':'text/html'},text='<main><h1>Marketing Assistant</h1><p>'+text*3+'</p></main>')
  with patch('app.materials._host_is_public',return_value=True),patch.object(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(response),**kw)):
   result=await fetch_job_posting('https://careers.example.test/role')
   self.assertIn('Marketing Assistant',result['text']);self.assertIn(text.strip(),result['text'])
 async def test_redirect_to_private_and_no_content(self):
  original=httpx.AsyncClient
  def redirect(req):return httpx.Response(302,headers={'location':'http://127.0.0.1/private'})
  with patch('app.materials._host_is_public',side_effect=lambda h:h=='careers.example.test'),patch.object(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(redirect),**kw)):
   with self.assertRaises(AppError) as error:await fetch_job_posting('https://careers.example.test/role')
   self.assertEqual(error.exception.code,'URL_FETCH_FAILED')
  def empty(req):return httpx.Response(200,headers={'content-type':'text/html'},text='<body>Login</body>')
  with patch('app.materials._host_is_public',return_value=True),patch.object(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(empty),**kw)):
   with self.assertRaises(AppError) as error:await fetch_job_posting('https://careers.example.test/role')
   self.assertEqual(error.exception.code,'URL_NO_CONTENT')
