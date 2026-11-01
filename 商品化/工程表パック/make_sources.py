# -*- coding: utf-8 -*-
"""元の工程表素材から、実名を含まない商品用素材を src/ に作る(一度だけ実行)。"""
import json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
ORIG = HERE.parents[1] / '工程表作成'
SRC = HERE / 'src'
SRC.mkdir(exist_ok=True)

html = (ORIG / '工程表テンプレート_編集版.html').read_text(encoding='utf-8')
old = '<div class="foot">株式会社AXIS　登録番号 T7030001171938</div>'
assert html.count(old) == 1
html = html.replace(old, '<div class="foot" contenteditable data-meta="footer" title="クリックして編集（会社名など）"></div>')
# 作業が0件(白紙版)でも描画が止まらないようにする
old2 = "T.forEach(t => { dates.push(dateOf(t.s), dateOf(endIdx(t))); });"
assert html.count(old2) == 1
html = html.replace(old2, old2 + " if (!dates.length) dates.push(dateOf(0));")
# 工種の見出し行だけがページ末尾に残らないようにする
old3 = "tr.grp .gname {"
assert html.count(old3) == 1
html = html.replace(old3, "tr.grp { break-after: avoid; page-break-after: avoid; }\n  " + old3)
(SRC / 'template.html').write_text(html, encoding='utf-8')

st = json.loads((ORIG / 'サンプル' / '中目黒大規模改修_state.json').read_text(encoding='utf-8'))
st['meta'] = {
    'name': '◯◯ビル改修工事',
    'place': '◯◯県◯◯市◯◯1-2-3',
    'client': '◯◯不動産 御中',
    'contractor': '◯◯建設（サンプル施工者）',
    'person': '◯◯ ◯◯',
    'created': '2027年1月1日',
    'scope': '内装解体（B1〜3F・階段・EV新設開口・外部）／外壁補修・塗装／屋上防水／クリーニング',
    'footer': '',
}
st['notes'] = [
    '※ 本工程表はサンプルです。実際の案件に合わせて、日付・作業名・注記を書き換えてください。',
    '※ 工事着工日は仮置きです。契約・各種届出の承認状況により変動します。',
    '※ 休工日は日曜・祝日・年末年始です。騒音を伴う作業は近隣へ事前にお知らせします。',
    '※ 石綿（アスベスト）含有が確認された場合は、除去工事・届出期間（14日前）と協議のため、別途工程を調整します。',
    '※ 構造に関わる解体は、構造協議の完了後に着手します。',
    '※ 天候・資材納期・追加工事等により工程が変動する場合は、速やかにご連絡し工程表を更新します。',
]
for t in st['tasks']:
    if '足場' in t['name'] and '計画届' in t['name']:
        t['note'] = '足場組立の30日前まで（要確認）'
(SRC / 'sample_state.json').write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding='utf-8')

blank = {
    'meta': {k: '' for k in st['meta']},
    'start': st['start'], 'satWork': True,
    'holidays': st['holidays'], 'breaks': st['breaks'],
    'groups': [{'name': '工種1', 'color': '#546e7a'}],
    'tasks': [],
    'notes': ['※ ここに注記を書きます（1行＝1項目）。'],
}
(SRC / 'blank_state.json').write_text(json.dumps(blank, ensure_ascii=False, indent=1), encoding='utf-8')
print('sources written to', SRC)
