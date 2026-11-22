# Resume document font

`ResumeSans.ttf` is the regular (weight 400) static instance of Google Noto Sans SC,
which includes simplified Chinese, traditional Chinese and Latin glyphs. It is
used by V3's deterministic PDF and DOCX exports and its private document viewer.
The complete font is embedded in DOCX; ReportLab embeds used glyphs in PDF.

Source: https://github.com/google/fonts/tree/main/ofl/notosanssc
Original: `NotoSansSC[wght].ttf`, downloaded 2026-11-22.
License: SIL Open Font License 1.1, included as `OFL.txt`.
Generated once using FontTools `instantiateVariableFont(..., {'wght': 400})`.
The 10 MB font is intentional, avoiding missing Chinese fonts on Render and
users' computers. FontTools is a development tool, not a runtime dependency.
No user documents or proprietary fonts are bundled here.
