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
    if inputs.get('userStage') or inputs.get('jobGoal'):
        text += '\0' + str(inputs.get('userStage') or '') + '\0' + str(inputs.get('jobGoal') or '')
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
    manual = state.get('finalResume')
    if manual and isinstance(manual.get('text'), str) and manual['text'].strip():
        return {'text': manual['text'], 'manual': True, 'version': manual.get('version', 1),
                'saved_at': manual.get('savedAt'), 'applied': 0, 'pending': 0, 'original_preserved': True}
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


FONT_PATH = Path(__file__).resolve().parents[1] / 'data/fonts/ResumeSans.ttf'


def _heading(text: str) -> bool:
    return bool(text) and len(text) < 65 and (bool(re.fullmatch(r'[A-Z &/()-]{3,64}', text)) or text.rstrip(':：').lower() in {
        'experience', 'education', 'skills', 'projects', 'summary', 'professional experience',
        'work experience', 'internship experience', 'project experience', 'certifications',
        '工作经历', '教育背景', '技能', '项目经历', '工作經歷', '專案經歷',
        '实习经历', '實習經歷', '专业技能', '專業技能', '自我评价', '自我評價', '个人简介', '個人簡介'})


def blocks(text: str):
    """Conservative template semantics; never invent, remove or reorder resume text."""
    section = False
    first = True
    for line in text.splitlines():
        clean = line.strip()
        if not clean:
            yield 'blank', line
        elif re.fullmatch(r'[•·●\s]+', clean):
            yield 'marker', line
        elif first:
            first = False
            yield ('name' if len(clean) < 80 else 'body'), line
        elif _heading(clean):
            section = True
            yield 'section', line
        elif section and ('|' in clean or '｜' in clean or re.search(r'20\d{2}[./年-]\d', clean)):
            yield 'entry', line
        elif section and len(clean) > 24 and not clean.startswith(('主要课程', '主要課程')):
            yield 'bullet', line
        else:
            yield 'body', line


def pdf_bytes(text: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    # An embedded OFL Noto font covers simplified/traditional Chinese and Latin.
    # No dependency on fonts installed on Render or the user's PDF reader.
    font = 'CareerResumeNoto'
    if font not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(font, str(FONT_PATH)))
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4, rightMargin=45, leftMargin=45,
        topMargin=40, bottomMargin=40, title='Resume', author='')
    body = ParagraphStyle('Body', fontName=font, fontSize=10, leading=15,
        textColor=colors.HexColor('#172333'), bulletFontName=font, bulletFontSize=10, spaceAfter=5, wordWrap='CJK', splitLongWords=True)
    styles = {
        'body': body,
        'marker': ParagraphStyle('Marker', parent=body, fontSize=2, leading=2, spaceAfter=0),
        'name': ParagraphStyle('Name', parent=body, fontSize=21, leading=28, spaceAfter=10, keepWithNext=True),
        'section': ParagraphStyle('Section', parent=body, fontSize=13, leading=19, spaceBefore=11, spaceAfter=7, keepWithNext=True),
        'entry': ParagraphStyle('Entry', parent=body, fontSize=10.5, spaceBefore=4, keepWithNext=True),
        'bullet': ParagraphStyle('Bullet', parent=body, leftIndent=10, bulletIndent=0),
    }
    story = []
    for kind, line in blocks(text):
        if kind == 'blank':
            story.append(Spacer(1, 4));continue
        bullet = '•' if kind == 'bullet' and not line.lstrip().startswith(('•', '-', '·', '●')) else None
        story.append(Paragraph(escape(line), styles[kind], bulletText=bullet))
    def footer(canvas, page):
        canvas.setFont(font, 8);canvas.setFillColor(colors.grey)
        canvas.drawRightString(A4[0]-45, 22, str(page.page))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()


def docx_bytes(text: str) -> bytes:
    import zipfile
    from uuid import uuid4
    from lxml import etree
    from docx import Document
    from docx.shared import Mm, Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    doc = Document();sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    sec.top_margin = sec.bottom_margin = Mm(14)
    sec.left_margin = sec.right_margin = Mm(16)
    for key in ['Normal', 'Title', 'Title Char', 'Heading 1', 'Heading 1 Char', 'List Bullet']:
        style = doc.styles[key];style.font.name = 'Noto Sans SC';style.font.size = Pt(10)
        style.font.color.rgb = RGBColor.from_string('172333')
        fonts = style.element.get_or_add_rPr().get_or_add_rFonts()
        for attr in list(fonts.attrib):
            if 'theme' in attr.lower():del fonts.attrib[attr]
        fonts.set(qn('w:eastAsia'), 'Noto Sans SC')
        if hasattr(style, 'paragraph_format'):
            style.paragraph_format.line_spacing = 1.3;style.paragraph_format.space_after = Pt(5)
    doc.styles['Title'].font.size = Pt(21);doc.styles['Title'].font.color.rgb = RGBColor.from_string('000000')
    doc.styles['Heading 1'].font.size = Pt(13)
    for level in doc.part.numbering_part.element.iter(qn('w:lvl')):
        fmt = level.find(qn('w:numFmt'))
        if fmt is not None and fmt.get(qn('w:val')) == 'bullet':
            level.find(qn('w:lvlText')).set(qn('w:val'), '•')
            props = level.find(qn('w:rPr'))
            if props is not None:
                fonts = props.find(qn('w:rFonts'))
                if fonts is not None:
                    fonts.set(qn('w:ascii'), 'Noto Sans SC');fonts.set(qn('w:hAnsi'), 'Noto Sans SC')
    doc.styles['Heading 1'].paragraph_format.space_before = Pt(11)
    for border in list(doc.styles['Title'].element.iter(qn('w:pBdr'))):border.getparent().remove(border)
    for kind, line in blocks(text):
        style = {'name': 'Title', 'section': 'Heading 1', 'bullet': 'List Bullet'}.get(kind, 'Normal')
        if kind == 'bullet' and line.lstrip().startswith(('•', '-', '·', '●')):style = 'Normal'
        p = doc.add_paragraph(line, style)
        p.paragraph_format.widow_control = True
        if kind == 'marker':
            p.paragraph_format.space_after = Pt(0);p.paragraph_format.line_spacing = Pt(2)
            for run in p.runs:run.font.size = Pt(2)
        if kind in ('name', 'section', 'entry'):p.paragraph_format.keep_with_next = True
        if kind in ('name', 'section', 'entry'):
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(21 if kind == 'name' else 13 if kind == 'section' else 10.5)
    doc.core_properties.author = '';doc.core_properties.title = 'Resume'
    footer = sec.footer.paragraphs[0];footer.alignment = 2
    field = OxmlElement('w:fldSimple');field.set(qn('w:instr'), 'PAGE');footer._p.append(field)
    output = io.BytesIO();doc.save(output)
    # Embed the licensed font in the actual Word package, also read by docx-preview.
    key = uuid4();mask = bytes.fromhex(key.hex)[::-1]
    data = bytearray(FONT_PATH.read_bytes())
    for i in range(32):data[i] ^= mask[i % 16]
    source = zipfile.ZipFile(io.BytesIO(output.getvalue()))
    table = etree.fromstring(source.read('word/fontTable.xml'))
    font = OxmlElement('w:font');font.set(qn('w:name'), 'Noto Sans SC')
    embedded = OxmlElement('w:embedRegular');embedded.set(qn('r:id'), 'rIdCareerFont')
    embedded.set(qn('w:fontKey'), '{' + str(key).upper() + '}');font.append(embedded);table.append(font)
    rels = b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdCareerFont" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/font" Target="fonts/ResumeSans.odttf"/></Relationships>'
    content_types = etree.fromstring(source.read('[Content_Types].xml'))
    ext = etree.SubElement(content_types, '{http://schemas.openxmlformats.org/package/2006/content-types}Default')
    ext.set('Extension', 'odttf');ext.set('ContentType', 'application/vnd.openxmlformats-officedocument.obfuscatedFont')
    target = io.BytesIO()
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in source.namelist():
            archive.writestr(file, etree.tostring(table) if file == 'word/fontTable.xml' else etree.tostring(content_types) if file == '[Content_Types].xml' else source.read(file))
        archive.writestr('word/_rels/fontTable.xml.rels', rels)
        archive.writestr('word/fonts/ResumeSans.odttf', data)
    return target.getvalue()
