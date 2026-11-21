"""Deterministic, project-scoped resume assembly. Never calls a language model.

Replace only verified source spans, in reverse order, in the full original text.
Everything outside those spans (including contact details and blank lines) survives.
Ambiguous, overlapping or unlocatable changes fail closed, never silently disappear.
"""
from __future__ import annotations
import io
import re
from pathlib import Path
from html import escape
from .errors import AppError


def input_key(inputs: dict) -> str:
    text = '\0'.join(str(inputs.get(k, '')).strip() for k in ('resumeText', 'jdText', 'jobTitle'))
    units = text.encode('utf-16-le', errors='surrogatepass')
    codes = [int.from_bytes(units[i:i+2], 'little') for i in range(0, len(units), 2)]
    h1, h2 = 0x811c9dc5, 0
    for c in codes:
        h1 = ((h1 ^ c) * 16777619) & 0xffffffff
        h2 = (h2 * 31 + c) & 0xffffffff
    def base36(n):
        out = ''
        while n:
            n, r = divmod(n, 36); out = '0123456789abcdefghijklmnopqrstuvwxyz'[r] + out
        return out or '0'
    return base36(h1) + base36(h2) + str(len(codes))


def compose(state: dict) -> dict:
    inputs, result, materials = state.get('inputs') or {}, state.get('resume'), state.get('materials')
    if not result or not materials:
        raise AppError('MATERIALS_STALE', 409)
    if (result.get('fingerprint') != materials.get('fingerprint') or
            input_key(inputs) != state.get('inputsKey')):
        raise AppError('MATERIALS_STALE', 409)
    # Optional snapshot is additive. Historical projects fall back to unchanged materials.
    source = result.get('source') or {'text': inputs.get('resumeText', ''), 'lines': materials.get('resume_lines', [])}
    original = source['text']
    if original != inputs.get('resumeText'):
        raise AppError('MATERIALS_STALE', 409)
    if not original.strip():raise AppError('RESUME_EMPTY', 422)
    items = result['data']['items']
    decisions = result.get('decisions') or {}
    by_source = {}
    for item in items:
        if item['source_id'] in by_source:raise AppError('RESUME_ASSEMBLY', 409)
        by_source[item['source_id']] = item
    # Whitespace-insensitive matching handles wrapped PDF lines. The index maps
    # every canonical character back to its exact offset in the full source.
    positions = [i for i, char in enumerate(original) if not char.isspace()]
    canonical = ''.join(original[i] for i in positions)
    cursor, edits, found = 0, [], set()
    for line in source['lines']:
        needle = re.sub(r'\s+', '', line['text'])
        start = canonical.find(needle, cursor) if needle else -1
        item = by_source.get(line['id'])
        decision = decisions.get(item['id'], {}) if item else {}
        applied = decision.get('state') in ('adopted', 'edited')
        if start < 0:
            if applied:raise AppError('RESUME_ASSEMBLY', 409)
            continue
        end = start + len(needle)
        cursor = end
        if not applied:continue
        if line.get('heading') or item['original'] != line['text']:
            raise AppError('RESUME_ASSEMBLY', 409)
        text = item['rewrite'] if decision['state'] == 'adopted' else decision.get('text', '')
        if not isinstance(text, str) or not text.strip():raise AppError('RESUME_ASSEMBLY', 409)
        # The UI prevents direct adoption of flagged output; enforce it here too.
        if decision['state'] == 'adopted' and item.get('verification', {}).get('status') == 'needs_review':
            raise AppError('RESUME_REVIEW', 409)
        edits.append((positions[start], positions[end-1]+1, text.strip()))
        found.add(item['id'])
    requested = {it['id'] for it in items if decisions.get(it['id'], {}).get('state') in ('adopted','edited')}
    if requested != found:raise AppError('RESUME_ASSEMBLY', 409)
    text = original
    for start, end, replacement in reversed(edits):
        text = text[:start] + replacement + text[end:]
    return {'text': text, 'applied': len(edits),
            'pending': sum(decisions.get(it['id'], {}).get('state','pending') == 'pending' for it in items),
            'original_preserved': True}


def _heading(text: str) -> bool:
    return bool(text) and len(text) < 65 and (text.isupper() or text.rstrip(':：').lower() in {
        'experience','education','skills','projects','summary','professional experience','work experience',
        '工作经历','教育背景','技能','项目经历','工作經歷','教育背景','專案經歷'})


def pdf_bytes(text: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont
    import reportlab
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    # Built-in CJK CID font preserves non-Latin input without OS font dependencies.
    cjk = bool(re.search(r'[\u3400-\u9fff]', text))
    font = 'STSong-Light' if cjk else 'ResumeSans'
    if not cjk and font not in pdfmetrics.getRegisteredFontNames():
        fonts = Path(reportlab.__file__).parent / 'fonts'
        pdfmetrics.registerFont(TTFont('ResumeSans', str(fonts / 'Vera.ttf')))
        pdfmetrics.registerFont(TTFont('ResumeSansBold', str(fonts / 'VeraBd.ttf')))
    if font == 'STSong-Light' and font not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(UnicodeCIDFont(font))
    output=io.BytesIO()
    doc=SimpleDocTemplate(output,pagesize=A4,rightMargin=48,leftMargin=48,topMargin=44,bottomMargin=44,title='Resume',author='')
    body=ParagraphStyle('Body',fontName=font,fontSize=10.5,leading=15,textColor=colors.HexColor('#172333'),spaceAfter=5,alignment=TA_LEFT,wordWrap='CJK' if font=='STSong-Light' else None,splitLongWords=True)
    head=ParagraphStyle('Section',parent=body,fontName='ResumeSansBold' if not cjk else font,fontSize=11.5,spaceBefore=10,spaceAfter=7,keepWithNext=True)
    name=ParagraphStyle('Name',parent=head,fontSize=19,leading=24,spaceBefore=0,spaceAfter=10)
    story=[]
    for i,line in enumerate(text.splitlines()):
        if not line.strip():story.append(Spacer(1,5));continue
        style=name if i==0 and len(line)<80 else head if _heading(line.strip()) else body
        story.append(Paragraph(escape(line),style))
    def footer(canvas, doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.grey)
        canvas.drawRightString(A4[0]-48,25,str(doc.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return output.getvalue()


def docx_bytes(text: str) -> bytes:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    doc=Document();sec=doc.sections[0]
    sec.page_width,sec.page_height=Inches(8.2677), Inches(11.6929)
    sec.top_margin=sec.bottom_margin=Inches(.61);sec.left_margin=sec.right_margin=Inches(.67)
    normal=doc.styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(10.5)
    normal.paragraph_format.space_after=Pt(5)
    normal.paragraph_format.line_spacing=1.15
    for style in ['Title','Heading 1']:
        doc.styles[style].font.color.rgb=RGBColor.from_string('172333')
        doc.styles[style].font.name='Calibri'
    doc.styles['Title'].font.size=Pt(19)
    doc.styles['Title'].font.color.rgb=RGBColor.from_string('000000')
    # Some python-docx distributions ship a blue rule in the Title style.
    for border in list(doc.styles['Title'].element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
    doc.styles['Heading 1'].font.size=Pt(11.5)
    for i,line in enumerate(text.splitlines()):
        p=doc.add_paragraph(line, 'Title' if i==0 and len(line)<80 else 'Heading 1' if _heading(line.strip()) else 'Normal')
        p.paragraph_format.widow_control=True
    doc.core_properties.author='';doc.core_properties.title='Resume'
    footer=sec.footer.paragraphs[0];footer.alignment=2
    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
    output=io.BytesIO();doc.save(output);return output.getvalue()
