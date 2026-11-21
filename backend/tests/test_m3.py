import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from app import m3
from app.rag import GuidanceIndex, index, expand
from app.config import RAG_DIR
from app.errors import AppError

RESUME = 'ALEX TAYLOR\nEXPERIENCE\nHelped prepare weekly campaign reports using Excel for the campus society.\nCreated social media posts for campus events.\nEDUCATION\nBBA Marketing, Example University, 2026'
JD = 'Marketing Assistant\nResponsibilities\nPrepare campaign reports using Excel and support campus communications.\nRequirements\nStrong written English and teamwork skills are required.\nPreferred\nExperience with social media content is preferred.'
def ok(result,citations=None):return {'status':'ok','message':'','result':result,'citations':citations or []}

class RagTests(unittest.TestCase):
    def test_complete_and_relevant(self):
        status=index.status()
        self.assertTrue(status['connected']);self.assertTrue(status['integrity'])
        self.assertEqual(status['chunks'],18);self.assertEqual(len(status['files']),4)
        for task,q,wanted in [('resume_optimization','personal statement sample resumes','resume-03'),('job_matching','900 occupations O*NET','career-03'),('mock_interview','STAR framework peers feedback','workshop-01')]:
            hits=index.search(task,q,3);self.assertIn(wanted,[x['chunk_id'] for x in hits]);self.assertTrue(all(h['source_url'].startswith('https://') for h in hits))
        self.assertIn('interview',expand('面试'));self.assertIn('resume',expand('簡歷'))
        self.assertEqual(index.search('resume_optimization','zzzzqxy123456'),[])
    def test_fail_closed_integrity_duplicate_missing_snapshot(self):
        for mode in ('text','duplicate','raw','missing'):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)/'rag';shutil.copytree(RAG_DIR,root)
                p=root/'chunks.jsonl';lines=p.read_text().splitlines()
                if mode=='text':
                    c=json.loads(lines[0]);c['text']='tampered';lines[0]=json.dumps(c);p.write_text('\n'.join(lines))
                if mode=='duplicate':p.write_text('\n'.join(lines+[lines[0]]))
                if mode=='raw':(root/'raw/resume.html').write_text('tampered')
                if mode=='missing':(root/'raw/resume.html').unlink()
                other=GuidanceIndex(root);self.assertFalse(other.status()['connected']);self.assertEqual(other.search('resume_optimization','resume'),[])

class M3Tests(unittest.IsolatedAsyncioTestCase):
    async def materials(self):return await m3.prepare_materials(RESUME,JD,'Marketing Assistant','en','current_student','internship')
    async def test_profile_and_missing_materials_no_model_call(self):
        with patch('app.m3.complete_json',AsyncMock()) as model:
            for stage,goal,cv,jd,code in [(None,None,RESUME,JD,'PROFILE_REQUIRED'),('current_student','job','',JD,'RESUME_EMPTY'),('current_student','job',RESUME,'','JD_EMPTY')]:
                with self.assertRaises(AppError) as e:await m3.prepare_materials(cv,jd,'','en',stage,goal)
                self.assertEqual(e.exception.code,code)
            await self.materials();model.assert_not_called()
    async def test_formal_prompt_payload_three_languages_and_sources(self):
        b=await self.materials()
        with patch('app.m3.complete_json',AsyncMock(return_value=ok({'edits':[],'questions_to_student':[]}))) as model:
            for lang,code in [('zh-CN','zh-Hans'),('zh-TW','zh-Hant'),('en','en')]:
                await m3.resume_optimize(b,lang)
                system,user=model.call_args.args;payload=json.loads(user)
                self.assertTrue(system.startswith(m3.system_prompt()));self.assertIn("citations (array",system);self.assertIn('不把「參與」升格為「主導」',system)
                self.assertEqual(payload['ui_language'],code);self.assertEqual(payload['task'],'resume_optimization')
                self.assertEqual(payload['user_stage'],'current_student');self.assertEqual(payload['job_goal'],'internship')
                self.assertIn('campaign reports',payload['resume_text']);self.assertTrue(payload['rag_chunks'])
                self.assertTrue(all(x['evidence_type']=='resource_listing_only' for x in payload['rag_chunks']))
    async def test_resume_partial_quote_preserves_remainder_and_unsupported_flag(self):
        b=await self.materials();edits=[{'original':'Helped prepare weekly campaign reports','rewrite':'Prepared weekly campaign reports with Python and increased sales 500%','jd_quote':'Prepare campaign reports using Excel','reason':'clarity'}]
        with patch('app.m3.complete_json',AsyncMock(return_value=ok({'edits':edits,'questions_to_student':['What was your contribution?']}))):
            out=await m3.resume_optimize(b,'en');item=out['items'][0]
            self.assertTrue(item['rewrite'].endswith('using Excel for the campus society.'));self.assertEqual(item['verification']['status'],'needs_review')
            self.assertTrue(item['verification']['unsupported_numbers']);self.assertIn('Python',item['verification']['unsupported_terms'])
    async def test_hallucinated_quote_and_citation_removed(self):
        b=await self.materials()
        with patch('app.m3.complete_json',AsyncMock(return_value=ok({'edits':[{'original':'CEO at Imaginary Inc','rewrite':'Led company','jd_quote':'','reason':'x'}],'questions_to_student':[]},[{'claim':'fake','chunk_id':'made-up'}]))):
            out=await m3.resume_optimize(b,'en');self.assertEqual(out['items'],[]);self.assertEqual(out['hidden_count'],1);self.assertEqual(out['m3']['citations'],[])
    async def test_matching_downgrades_false_student_evidence(self):
        b=await self.materials();r={'jd_quote':'Prepare campaign reports using Excel and support campus communications.','priority':'required','status':'direct','evidence_quotes':['Advanced Python certification'],'reason':'x','next_step':'Clarify skills'}
        with patch('app.m3.complete_json',AsyncMock(return_value=ok({'requirements':[r]}))):
            out=await m3.job_match(b,'en');self.assertEqual(out['items'][0]['status'],'none');self.assertEqual(out['items'][0]['evidence'],[]);self.assertEqual(out['items'][0]['priority_code'],'required')
    async def test_empty_rag_and_invalid_result(self):
        b=await self.materials()
        with patch.object(index,'search',return_value=[]),patch('app.m3.complete_json',AsyncMock(return_value=ok({'edits':[],'questions_to_student':[]}))) as model:
            out=await m3.resume_optimize(b,'en');self.assertEqual(json.loads(model.call_args.args[1])['rag_chunks'],[]);self.assertEqual(out['guidance']['sources'],[])
        for value in ({'items':[]},ok({'wrong':[]})):
            with patch('app.m3.complete_json',AsyncMock(return_value=value)):
                with self.assertRaises(AppError):await m3.resume_optimize(b,'en')
    async def test_interview_actual_answer_history_and_follow_up_limit(self):
        b=await self.materials();answer='I grouped comments by topic.'
        result={'phase':'follow_up','question':'What categories did you choose?','feedback':{'answer_quote':answer,'strength':'You gave a method','next_try':'Explain the categories'},'summary':None}
        with patch('app.m3.complete_json',AsyncMock(return_value=ok(result))) as model:
            out=await m3.interview_feedback(b,'en',{'question':'How did you group feedback?','is_follow_up':True},answer,[],[{'question':'Previous?','answer':'Earlier answer.'}])
            self.assertFalse(out['follow_up']['needed']);payload=json.loads(model.call_args.args[1]);self.assertEqual(payload['answer_text'],answer);self.assertEqual(payload['interview_action'],'respond');self.assertEqual(payload['history'][-1]['role'],'assistant')
            self.assertNotIn(answer,json.dumps(payload['history']))
    async def test_profile_change_invalidates_material_fingerprint(self):
        a=await self.materials()
        b=await m3.prepare_materials(RESUME,JD,'Marketing Assistant','en','recent_graduate','job')
        self.assertNotEqual(a['fingerprint'],b['fingerprint'])
    async def test_interview_start_and_finish_use_formal_actions(self):
        b=await self.materials()
        with patch('app.m3.complete_json',AsyncMock(return_value=ok({'phase':'question','question':'How did you prepare reports?','feedback':None,'summary':None}))) as model:
            q=await m3.interview_question(b,'en',[],None);self.assertTrue(q['question']);payload=json.loads(model.call_args.args[1]);self.assertEqual(payload['interview_action'],'start');self.assertEqual(payload['history'],[])
        with patch('app.m3.complete_json',AsyncMock(return_value=ok({'phase':'summary','question':None,'feedback':None,'summary':'You described the method.'}))) as model:
            out=await m3.interview_summary('en',[{'question':'How?','answer':'I prepared reports.'}],b)
            self.assertEqual(out['next_session'],'You described the method.');self.assertEqual(json.loads(model.call_args.args[1])['interview_action'],'finish')
    async def test_prompt_hash_and_damaged_prompt(self):
        self.assertEqual(m3.prompt_status()[0]['sha256'],'85b8f6298336f9c24ecb4a578b68cb965ffc387992ffd8d4dec475d21eb10c9b')
        with patch('app.m3.M3_PROMPT_PATH',Path('/missing/official-prompt')):
            self.assertFalse(m3.prompt_status()[0]['loaded'])
            with self.assertRaises(AppError):m3.system_prompt()

    async def test_language_is_explicit_and_never_guessed(self):
        with patch('app.m3.complete_json',AsyncMock()) as model:
            with self.assertRaises(AppError) as e:await m3.prepare_materials(RESUME,JD,'',None,'current_student','job')
            self.assertEqual(e.exception.code,'LANGUAGE_REQUIRED');model.assert_not_called()
            with self.assertRaises(AppError) as e:await m3.resume_optimize({},None)
            self.assertEqual(e.exception.code,'LANGUAGE_REQUIRED');model.assert_not_called()
    async def test_compound_jd_sentences_are_separate_and_titles_excluded(self):
        jd='Marketing Assistant - Company\nRequirements\nBachelor degree in Marketing. Clear written English is required.'
        b=await m3.prepare_materials(RESUME,jd,'Marketing Assistant','en','current_student','job')
        self.assertEqual([r['text'] for r in b['requirements']],['Bachelor degree in Marketing.','Clear written English is required.'])
    async def test_multiple_assessments_never_overwrite_each_other(self):
        b=await self.materials();quote=b['requirements'][0]['text']
        items=[{'jd_quote':quote,'priority':'required','status':'direct','evidence_quotes':['Created social media posts for campus events.'],'reason':'First assessment','next_step':'First step'},
               {'jd_quote':quote,'priority':'required','status':'not_evidenced','evidence_quotes':[],'reason':'Second assessment','next_step':'Second step'}]
        with patch('app.m3.complete_json',AsyncMock(return_value=ok({'requirements':items}))):
            out=await m3.job_match(b,'en');item=out['items'][0]
            self.assertEqual(len(item['assessments']),2);self.assertIn('First assessment',item['rationale']);self.assertIn('Second assessment',item['rationale']);self.assertEqual(item['status'],'partial')
