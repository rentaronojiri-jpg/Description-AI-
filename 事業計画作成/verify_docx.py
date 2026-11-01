# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from docx import Document

path = r'C:\Users\renta\OneDrive\Desktop\AI事務\事業計画作成\jigyou_keikaku02_完成.docx'
doc = Document(path)
table = doc.tables[0]

sep = ' | '
for ri, row in enumerate(table.rows):
    seen = set()
    texts = []
    for cell in row.cells:
        cid = id(cell._tc)
        if cid not in seen:
            seen.add(cid)
            t = cell.text.strip()
            if t:
                texts.append(t[:60])
    if texts:
        print('Row' + str(ri) + ': ' + sep.join(texts))
