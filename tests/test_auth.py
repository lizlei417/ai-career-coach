import unittest
from unittest.mock import patch
from fastapi import HTTPException
import httpx
from coach import cloud

class PublicAuth(unittest.IsolatedAsyncioTestCase):
 async def test_email_and_admin_boundary(self):
  original=httpx.AsyncClient
  user={"id":"00000000-0000-4000-8000-000000000001","email_confirmed_at":"2026-11-21T00:00:00Z","app_metadata":{},"user_metadata":{"coach_admin":True,"coach_member":True}}
  def request(_):return httpx.Response(200,json=user)
  with patch.dict("os.environ",{"SUPABASE_URL":"https://auth.invalid","SUPABASE_PUBLISHABLE_KEY":"synthetic"}),patch.object(httpx,"AsyncClient",lambda **kw:original(transport=httpx.MockTransport(request),**kw)):
   uid,admin=await cloud.verify("Bearer offline")
   self.assertEqual(uid,user["id"]);self.assertFalse(admin)
   user["app_metadata"]={"coach_admin":True}
   self.assertTrue((await cloud.verify("Bearer offline"))[1])
   user["is_anonymous"]=True
   with self.assertRaises(HTTPException):await cloud.verify("Bearer offline")
   user.pop("is_anonymous");user.pop("email_confirmed_at")
   with self.assertRaises(HTTPException):await cloud.verify("Bearer offline")

 def test_emergency_switch_is_server_enforced(self):
  with patch.dict("os.environ",{"AI_REQUESTS_ENABLED":"false"}),patch.object(cloud,"connect") as connect:
   with self.assertRaises(HTTPException) as error: cloud.reserve_call()
   self.assertEqual(error.exception.status_code,503)
   connect.assert_not_called()
