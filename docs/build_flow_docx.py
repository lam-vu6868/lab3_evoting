"""
FILE: docs/build_flow_docx.py
MỤC ĐÍCH: Sinh Word từ Luong_du_lieu_he_thong_bau_cu.md bằng Python stdlib.
CÁCH DÙNG: python docs/build_flow_docx.py; không cần DB hoặc thư viện ngoài.
CÁCH SỬA: parser đọc heading/bảng/code; phần cuối đóng gói OOXML và kiểm tra XML.
ĐẦU RA: .docx cùng thư mục; giữ nguyên tài liệu nhị phân đã tạo khi chưa cần tái xuất.
"""
from pathlib import Path
from xml.sax.saxutils import escape
import re
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'Luong_du_lieu_he_thong_bau_cu.md'
DEST = ROOT / 'Luong_du_lieu_he_thong_bau_cu.docx'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def run(text, bold=False):
    props = '<w:rPr><w:b/></w:rPr>' if bold else ''
    return f'<w:r>{props}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def paragraph(text='', style=None, extra=''):
    props = (f'<w:pStyle w:val="{style}"/>' if style else '') + extra
    parts = re.split(r'(\*\*.*?\*\*)', text)
    runs = ''.join(run(p[2:-2], True) if p.startswith('**') and p.endswith('**') else run(p) for p in parts)
    return f'<w:p><w:pPr>{props}</w:pPr>{runs}</w:p>'


def table(rows):
    count = len(rows[0])
    widths = {2: [3300, 6780], 3: [2400, 3000, 4680], 5: [1700, 1700, 2100, 2580, 2000]}.get(count, [10080 // count] * count)
    borders = ''.join(f'<w:{s} w:val="single" w:sz="4" w:color="CFD8E3"/>' for s in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV'])
    result = ['<w:tbl><w:tblPr><w:tblW w:w="10080" w:type="dxa"/><w:tblLayout w:type="fixed"/>',
              f'<w:tblBorders>{borders}</w:tblBorders>',
              '<w:tblCellMar><w:top w:w="90" w:type="dxa"/><w:left w:w="110" w:type="dxa"/><w:bottom w:w="90" w:type="dxa"/><w:right w:w="110" w:type="dxa"/></w:tblCellMar></w:tblPr>',
              '<w:tblGrid>' + ''.join(f'<w:gridCol w:w="{width}"/>' for width in widths) + '</w:tblGrid>']
    for idx, row in enumerate(rows):
        result.append('<w:tr><w:trPr><w:cantSplit/>' + ('<w:tblHeader/>' if idx == 0 else '') + '</w:trPr>')
        for col, cell in enumerate(row):
            bg = 'DFEAF5' if idx == 0 else ('F5F8FB' if idx % 2 == 0 else 'FFFFFF')
            result.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[col]}" w:type="dxa"/><w:shd w:fill="{bg}"/><w:vAlign w:val="center"/></w:tcPr>')
            result.append(paragraph(f'**{cell}**' if idx == 0 else cell, 'TableText'))
            result.append('</w:tc>')
        result.append('</w:tr>')
    result.append('</w:tbl>')
    result.append(paragraph('', 'TableGap'))
    return ''.join(result)


source_text = re.sub(r'<!--.*?-->\s*', '', SOURCE.read_text(encoding='utf-8'), flags=re.S)
lines = source_text.splitlines()
body = []
i = 0
while i < len(lines):
    line = lines[i]
    if not line.strip():
        i += 1
        continue
    if line.startswith('```'):
        code = []
        i += 1
        while i < len(lines) and not lines[i].startswith('```'):
            code.append(lines[i])
            i += 1
        for pos, text in enumerate(code):
            body.append(paragraph(text, 'Code', '<w:keepNext/>' if pos < len(code) - 1 else ''))
        body.append(paragraph('', 'TableGap'))
    elif line.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            cells = [cell.strip() for cell in lines[i].strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?', cell) for cell in cells):
                rows.append(cells)
            i += 1
        body.append(table(rows))
        continue
    elif line.startswith('## '):
        body.append(paragraph(line[3:], 'Heading1'))
    elif line.startswith('# '):
        body.append(paragraph(line[2:], 'Title'))
    else:
        body.append(paragraph(line))
    i += 1

styles = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W}">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="23"/><w:lang w:val="vi-VN"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/><w:widowControl/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:after="240"/></w:pPr><w:rPr><w:b/><w:color w:val="17365D"/><w:sz w:val="36"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="280" w:after="140"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="17365D"/><w:sz w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:ind w:left="150" w:right="100"/><w:shd w:fill="F1F4F8"/></w:pPr><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="19"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TableText"><w:name w:val="Table Text"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0" w:line="250" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="21"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="TableGap"><w:name w:val="Table Gap"/><w:pPr><w:spacing w:after="60" w:line="80" w:lineRule="exact"/></w:pPr><w:rPr><w:sz w:val="4"/></w:rPr></w:style>
</w:styles>'''

document = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{W}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>{''.join(body)}<w:sectPr><w:footerReference w:type="default" r:id="rId2"/><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1000" w:right="913" w:bottom="1000" w:left="913" w:header="400" w:footer="400" w:gutter="0"/></w:sectPr></w:body></w:document>'''
footer = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr xmlns:w="{W}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:sz w:val="18"/><w:color w:val="68788A"/></w:rPr><w:t>Luồng dữ liệu hệ thống bầu cử • Trang </w:t></w:r><w:fldSimple w:instr="PAGE"/></w:p></w:ftr>'''
types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/><Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/></Types>'''
rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/></Relationships>'''
docrels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>'''
core = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Luồng dữ liệu hệ thống bầu cử điện tử</dc:title><dc:subject>Kích hoạt, đăng nhập, ký số, mã hóa, database và kiểm phiếu</dc:subject><dc:description>Tài liệu 10 phần theo ví dụ SV001 bầu ứng viên B. Mô tả thiết kế dự kiến từ ROADMAP.md và db/init.sql.</dc:description><dc:language>vi-VN</dc:language></cp:coreProperties>'''
parts = {'[Content_Types].xml': types, '_rels/.rels': rels, 'word/document.xml': document, 'word/styles.xml': styles, 'word/footer1.xml': footer, 'word/_rels/document.xml.rels': docrels, 'docProps/core.xml': core}
for value in parts.values():
    ET.fromstring(value)
with zipfile.ZipFile(DEST, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, value in parts.items():
        archive.writestr(name, value.encode('utf-8'))

with zipfile.ZipFile(DEST) as archive:
    assert archive.testzip() is None
    tree = ET.fromstring(archive.read('word/document.xml'))
ns = {'w': W}
headings = [p for p in tree.findall('.//w:p', ns) if p.find('./w:pPr/w:pStyle[@w:val="Heading1"]', ns) is not None]
assert len(headings) == 10, len(headings)
tables = tree.findall('.//w:tbl', ns)
assert len(tables) == 10, len(tables)
content = '\n'.join(t.text or '' for t in tree.findall('.//w:t', ns))
assert 'Đăng nhập chỉ đọc thông tin tài khoản và cấp JWT' in content
assert 'Tally tính trong RAM rồi trả cho admin' in content
print(f'Created: {DEST}')
print(f'Validation: 10 sections, {len(tables)} tables, XML and ZIP valid, {DEST.stat().st_size} bytes')
