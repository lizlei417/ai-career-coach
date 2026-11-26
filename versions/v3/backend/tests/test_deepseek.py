"""Run with python -m unittest discover -s tests from backend. No external traffic."""
import json
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from app.main import app
from app import llm, cloud

MATERIAL = {"user_stage":"current_student","job_goal":"internship","resume_lines":[{"id":"R1","text":"Mapped student feedback.","heading":False,"section":""}],
            "jd_lines":[{"id":"J1","text":"Map feedback."}],
            "requirements":[{"id":"Q1","category":"required","text":"Map feedback.","kind":"technical","source_ids":["J1"]}]}

class DeepSeekRoutes(unittest.TestCase):
    def use(self, patcher):
        patcher.start()
        self.addCleanup(patcher.stop)

    def setUp(self):
        self.client = TestClient(app,headers={"Authorization":"Bearer test-only"})
        self.use(patch.object(cloud,"verify",return_value=("00000000-0000-4000-8000-000000000001",False)))
        self.use(patch.object(cloud,"reserve_call",return_value=1))
        self.use(patch.object(cloud,"record_usage"))
        self.use(patch.object(cloud,"dispatch_call"))
        self.use(patch.object(cloud,"cancel_unsent"))
        self.reply = {}
        self.status = 200
        self.calls = 0
        original = httpx.AsyncClient
        self.original_client = original
        def transport(req):
            self.calls += 1
            body = json.loads(req.content)
            self.assertEqual(str(req.url), "https://api.deepseek.com/chat/completions")
            self.assertEqual(body["model"], "deepseek-flash")
            self.assertEqual(body["thinking"]["type"], "disabled")
            if '"task"' in body['messages'][1]['content']:
                from app.m3 import system_prompt
                self.assertTrue(body['messages'][0]['content'].startswith(system_prompt()))
                payload=json.loads(body['messages'][1]['content'])
                self.assertTrue(payload['rag_chunks'])
                self.assertEqual(payload['ui_language'],'en')
            return httpx.Response(self.status, json={"choices":[{"finish_reason":"stop","message":{"content":json.dumps(self.reply)}}]})
        self.use(patch.dict("os.environ", {"DEEPSEEK_API_KEY":"synthetic-test-only"}))
        self.use(patch.object(llm,"balance_blocked",False))
        self.use(patch.object(httpx,"AsyncClient",lambda **kw: original(transport=httpx.MockTransport(transport), **kw)))

    def feature(self, path, reply, **extra):
        self.reply = {"status":"ok","message":"","result":reply,"citations":[]}
        res = self.client.post("/api/"+path,json={"materials":MATERIAL,"lang":"en",**extra})
        self.assertEqual(res.status_code,200,res.text)
        return res.json()

    def test_features(self):
        item = self.feature("resume/optimize", {"edits":[{"original":"Mapped student feedback.","jd_quote":"Map feedback.","rewrite":"Organized student feedback.","reason":"Clarity"}],"questions_to_student":[]})["items"][0]
        self.assertEqual(item["original"],"Mapped student feedback.")
        item = self.feature("match", {"requirements":[{"jd_quote":"Map feedback.","priority":"required","status":"direct","evidence_quotes":["Mapped student feedback."],"reason":"Evidence","next_step":"Review"}]})["items"][0]
        self.assertEqual(item["evidence"][0]["id"],"R1")
        q = self.feature("interview/question", {"phase":"question","question":"How did you group feedback?","feedback":None,"summary":None})
        self.feature("interview/feedback", {"phase":"question","question":"How did you use feedback?","feedback":{"answer_quote":"I grouped comments by topic.","strength":"Grouped by topic","next_try":"Explain one category."},"summary":None},question=q,answer="I grouped comments by topic.")
        self.assertEqual(self.client.get("/api/health").json()["llm"]["connection"],"verified")
        self.assertEqual(self.calls,4)

    def test_errors(self):
        for status,code in [(401,"LLM_AUTH"),(429,"LLM_RATE_LIMIT"),(402,"LLM_BALANCE"),(402,"LLM_BALANCE")]:
            self.status=status
            self.assertEqual(self.client.post("/api/settings/test").json()["error"]["code"],code)
        self.assertEqual(self.calls,3)
        self.assertEqual(self.client.get("/api/health").json()["llm"]["connection"],"failed")

    def test_unsent_transport_and_preflight_accounting(self):
        for kind, refunded, status in [(httpx.ConnectError,True,502),(httpx.ReadTimeout,False,504)]:
            cloud.cancel_unsent.reset_mock()
            def fail(request): raise kind("offline fixture",request=request)
            with patch.object(httpx,"AsyncClient",lambda **kw:self.original_client(transport=httpx.MockTransport(fail),**kw)):
                self.assertEqual(self.client.post("/api/settings/test").status_code,status)
            self.assertEqual(cloud.cancel_unsent.called,refunded)
        cloud.reserve_call.reset_mock()
        self.assertEqual(self.client.post("/api/resume/optimize",json={}).status_code,422)
        cloud.reserve_call.assert_not_called()
