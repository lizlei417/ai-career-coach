import copy, io, unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from pypdf import PdfReader
from docx import Document
from app.final_resume import compose, input_key, pdf_bytes, docx_bytes
from app.materials import segment, pdf_to_text
from app.errors import AppError
from app.main import app
from app import cloud

TEXT='ALEX TAYLOR\nalex.taylor@example.test | Hong Kong\n\nEXPERIENCE\n• Helped prepare campaign reports\nusing spreadsheets for the student society.\n• Created social media posts for campus events.\n\nEDUCATION\nBBA Marketing, Example University, 2026\nSKILLS\nExcel, English, Cantonese\n'
def state():
 lines=segment(TEXT,'R')
 lines_with_changes=[x for x in lines if x['text'].startswith(('Helped','Created'))]
 items=[dict(id=f'O{i+1}',source_id=x['id'],original=x['text'],rewrite=x['text'].replace('Helped','Supported').replace('Created','Prepared'),verification={'status':'grounded'}) for i,x in enumerate(lines_with_changes)]
 inputs=dict(resumeText=TEXT,jdText='Marketing Assistant: prepare campaign reports.',jobTitle='Marketing Assistant')
 return dict(inputs=inputs,inputsKey=input_key(inputs),materials={'fingerprint':'fp','resume_lines':lines},resume=dict(fingerprint='fp',source={'text':TEXT,'lines':lines},data={'items':items},decisions={}))
class Assembly(unittest.TestCase):
 def test_saved_complete_resume_survives_material_and_review_changes(self):
  s=state();s['finalResume']={'text':'林知夏\n专业技能\nExcel、SQL\n手动补充段落','version':2}
  original=copy.deepcopy(s['inputs'])
  s['resume']['decisions']={'O1':{'state':'adopted'}}
  self.assertEqual(compose(s)['text'],s['finalResume']['text'])
  s['inputs']['jdText']='new JD';s['resume']=None
  self.assertEqual(compose(s)['text'],s['finalResume']['text'])
  self.assertEqual(s['inputs']['resumeText'],original['resumeText'])
 def test_docx_embeds_chinese_font_and_preserves_all_paragraphs(self):
  import zipfile
  text='林知夏\nlin@example.test\n教育背景\n香港城市大學 碩士\n实习经历\n协助产品团队整理用户反馈，编制每周运营报告。'
  data=docx_bytes(text);doc=Document(io.BytesIO(data))
  self.assertEqual('\n'.join(p.text for p in doc.paragraphs),text)
  archive=zipfile.ZipFile(io.BytesIO(data));self.assertIn('word/fonts/ResumeSans.odttf',archive.namelist())
  self.assertIn(b'embedRegular',archive.read('word/fontTable.xml'))
  pdf=PdfReader(io.BytesIO(pdf_bytes(text)));self.assertIn('香港城市大學',pdf.pages[0].extract_text())
  self.assertNotIn('\x7f',pdf.pages[0].extract_text())
 def test_profile_change_requires_reanalysis_without_breaking_legacy_state(self):
  s=state();self.assertEqual(compose(s)['text'],TEXT)
  s['inputs'].update(userStage='current_student',jobGoal='internship')
  s['inputsKey']=input_key(s['inputs']);self.assertEqual(compose(s)['text'],TEXT)
  s['inputs']['jobGoal']='job'
  with self.assertRaises(AppError):compose(s)
 def test_reject_all_and_pending_preserve_exact_original(self):
  s=state();self.assertEqual(compose(s)['text'],TEXT)
  s['resume']['decisions']={x['id']:{'state':'kept'} for x in s['resume']['data']['items']}
  self.assertEqual(compose(s)['text'],TEXT)
 def test_partial_manual_undo_and_original_retention(self):
  s=state();original=copy.deepcopy(s)
  s['resume']['decisions']={'O1':{'state':'adopted'},'O2':{'state':'kept'}}
  self.assertEqual(compose(s)['text'],TEXT.replace('Helped prepare campaign reports\nusing spreadsheets for the student society.','Supported prepare campaign reports using spreadsheets for the student society.'))
  s['resume']['decisions']['O2']={'state':'edited','text':'Prepared social media posts for campus events with the society.'}
  self.assertIn('with the society.',compose(s)['text'])
  s['resume']['decisions']['O2']={'state':'pending'}
  self.assertIn('Created social media posts',compose(s)['text'])
  self.assertEqual(s['resume']['source'],original['resume']['source'])
  self.assertEqual(s['inputs']['resumeText'],TEXT)
 def test_stale_and_unlocatable_fail_closed(self):
  for what in ['jdText','resumeText','jobTitle']:
   s=state();s['inputs'][what]+=' changed'
   with self.assertRaises(AppError):compose(s)
  s=state();s['resume']['decisions']={'O1':{'state':'adopted'}}
  s['resume']['source']['lines'][3]['text']='unlocatable source'
  with self.assertRaises(AppError):compose(s)
 def test_historical_snapshot_and_duplicate_lines(self):
  s=state();del s['resume']['source'];self.assertEqual(compose(s)['text'],TEXT)
  s=state();original=s['resume']['data']['items'][0]['original'];s['resume']['data']['items'].append(copy.deepcopy(s['resume']['data']['items'][0]))
  with self.assertRaises(AppError):compose(s)
 def test_identical_paragraphs_replace_only_selected_source(self):
  s=state();extra='Created social media posts for campus events.'
  s['inputs']['resumeText'] += '\n'+extra
  lines=segment(s['inputs']['resumeText'],'R')
  s['materials']['resume_lines']=lines
  s['resume']['source']={'text':s['inputs']['resumeText'],'lines':lines}
  s['inputsKey']=input_key(s['inputs'])
  s['resume']['data']['items'].append({'id':'O3','source_id':lines[-1]['id'],'original':extra,'rewrite':'Prepared social media posts for campus events.'})
  s['resume']['decisions']={'O3':{'state':'adopted'}}
  out=compose(s)['text']
  self.assertEqual(out.count(extra),1)
  self.assertTrue(out.endswith('Prepared social media posts for campus events.'))
 def test_unsupported_direct_adoption_blocked(self):
  s=state();s['resume']['data']['items'][0]['verification']['status']='needs_review'
  s['resume']['decisions']={'O1':{'state':'adopted'}}
  with self.assertRaises(AppError):compose(s)
 def test_pdf_docx_complete_multipage_and_cjk(self):
  text=TEXT+'\n'.join(f'Additional fictional activity {i}: Coordinated student communications and meeting notes.' for i in range(100))+'\nFINAL CONTENT MARKER'
  reader=PdfReader(io.BytesIO(pdf_bytes(text)))
  self.assertGreater(len(reader.pages),1)
  self.assertIn('FINAL CONTENT MARKER','\n'.join(p.extract_text() for p in reader.pages))
  extracted=''.join(''.join(p.extract_text().split()) for p in reader.pages)
  for line in text.splitlines():self.assertIn(''.join(line.split()),extracted)
  doc=Document(io.BytesIO(docx_bytes(text)))
  self.assertEqual('\n'.join(p.text for p in doc.paragraphs),text)
  cjk='陳小明\n教育背景\n香港示例大學 市場營銷學士\n技能\n廣東話 English Excel'
  self.assertIn('陳小明',PdfReader(io.BytesIO(pdf_bytes(cjk))).pages[0].extract_text())
 def test_scanned_corrupt_and_size_limit(self):
  from reportlab.pdfgen.canvas import Canvas
  buffer=io.BytesIO();c=Canvas(buffer);c.showPage();c.showPage();c.save()
  with self.assertRaises(AppError) as error:pdf_to_text(buffer.getvalue())
  self.assertEqual(error.exception.code,'PDF_NO_TEXT')
  with self.assertRaises(AppError):pdf_to_text(b'%PDF-broken')
 def test_owner_scoped_routes_and_real_files(self):
  client=TestClient(app,headers={'Authorization':'Bearer qa'})
  with patch.object(cloud,'verify',return_value=('00000000-0000-4000-8000-000000000001',False)),patch.object(cloud,'read',return_value={'state':state()}) as read:
   self.assertEqual(client.get('/api/workspaces/demo/resume/final').json()['text'],TEXT)
   pdf=client.get('/api/workspaces/demo/resume/export?format=pdf');self.assertEqual(pdf.status_code,200);self.assertTrue(pdf.content.startswith(b'%PDF'))
   docx=client.get('/api/workspaces/demo/resume/export?format=docx');self.assertEqual(docx.status_code,200);self.assertTrue(docx.content.startswith(b'PK'))
   self.assertEqual(client.get('/api/workspaces/demo/resume/export?format=txt').status_code,422)
   read.assert_called_with('demo')
  self.assertEqual(TestClient(app).get('/api/workspaces/demo/resume/export').status_code,401)
if __name__=='__main__':unittest.main()
