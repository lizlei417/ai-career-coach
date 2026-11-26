"""Offline test of the FastAPI actions, DeepSeek request contract and evidence audit."""
import json
import unittest
from unittest.mock import patch

import httpx
import openai
from fastapi.testclient import TestClient
from server import app, cloud
from fastapi import HTTPException
import copy


class DeepSeekActions(unittest.TestCase):
    def test_actions(self):
        original = openai.OpenAI
        calls = []
        def respond(req):
            body = json.loads(req.content)
            self.assertEqual(str(req.url), "https://api.deepseek.com/chat/completions")
            self.assertEqual(body["model"], "deepseek-flash")
            self.assertEqual(body["thinking"], {"type": "disabled"})
            instruction, message = body["messages"]
            title = json.loads(instruction["content"].split("matching this schema:\n")[1])["title"]
            calls.append(title)
            payload = json.loads(message["content"])
            evidence = [{"source_id":"R001", "quote":"Built a dashboard"}]
            result = {
                "Extraction":{"resume_is_valid":True,"jd_is_valid":True,"issues":[],"requirements":[{"id":"Q1","source_id":"J001","quote":"dashboard","category":"required"}]},
                "Optimization":{"revisions":[{"id":"E1","requirement_ids":["Q1"],"evidence":evidence,"optimized":"Created a dashboard.","reason":"Use an active verb."}],"gaps":[],"guide_ids":[]},
                "Matching":{"matches":[{"requirement_id":"Q1","status":"direct","gap_type":"sufficient","evidence":evidence,"suggestion":"","assessment":"Dashboard experience cited.","priority":"low"}],"guide_ids":[]},
                "Question":{"text":"How did you validate the dashboard?","kind":"technical","evidence":evidence,"requirement_id":"Q1","guide_ids":[]},
                "Feedback":{"strengths":["Described validation."],"missing_information":["Add an example."],"action":"Describe one check.","answer_quotes":[],"follow_up":None,"guide_ids":[]},
                "Audit":{"items":[{"id":x["id"],"supported":True,"reason":"Supported by example"} for x in payload.get("candidate_items",[])]},
            }[title]
            return httpx.Response(200,json={"id":"test","model":"deepseek-flash","created":1,"object":"chat.completion","choices":[{"index":0,"message":{"role":"assistant","content":json.dumps(result)},"finish_reason":"stop"}]})

        def sdk(**kwargs):
            self.assertEqual(kwargs["max_retries"],0)
            return original(**kwargs,http_client=httpx.Client(transport=httpx.MockTransport(respond)))

        records={}
        def put(key,body):
            records[key]={"revision":body.revision+1,"state":copy.deepcopy(body.state)}
        def get(key):
            if key not in records: raise HTTPException(404)
            return copy.deepcopy(records[key])
        self.addCleanup(patch.stopall)
        for name,value in {"verify":("00000000-0000-4000-8000-000000000001",False),"reserve_call":1,"record_usage":None,"dispatch_call":None,"cancel_unsent":None}.items():
            patch.object(cloud,name,return_value=value).start()
        patch.object(cloud,"read",side_effect=get).start()
        patch.object(cloud,"save",side_effect=put).start()
        with patch.dict("os.environ",{"DEEPSEEK_API_KEY":"synthetic-only"}), patch.object(openai,"OpenAI",sdk), TestClient(app,headers={"Authorization":"Bearer offline-test"}) as client:
            self.assertEqual(client.get("/api/bootstrap").json()["status"]["connection"],"unverified")
            created = client.post("/api/project",json={"role":"Analyst","name":"Test","resume":"Built a dashboard for a fictional student research team.","jd":"We need dashboard analysis and communication experience."}).json()
            headers = {"X-Project":created["token"]}
            self.assertFalse(calls)
            for version,kind in enumerate(["optimize","match","question","answer"]):
                response=client.post("/api/action",headers=headers,json={"kind":kind,"version":version,"answer":"I checked the totals.","language":"en"})
                self.assertEqual(response.status_code,200,response.text)
            p=response.json()
            self.assertEqual(p["status"]["connection"],"verified")
            self.assertEqual(p["optimization"]["data"]["revisions"][0]["evidence"][0]["source_id"],"R001")
            self.assertEqual(p["matching"]["data"]["matches"][0]["status"],"direct")
            self.assertEqual(p["interview"]["turns"][0]["answer"],"I checked the totals.")
