# -*- coding: utf-8 -*-
"""工程表 state.json → 編集可能な工程表HTML(+任意でA3 PDF)を生成し、日付・先行関係を検証する。

使い方:  python build_schedule.py <state.json> <出力.html> [--pdf]
state.json の仕様は .claude/commands/工程表作成.md を参照。
"""
import json, sys, io, os, re, subprocess, datetime as dt, pathlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = pathlib.Path(__file__).resolve().parent
P = dt.date.fromisoformat


def calendar(st):
    hol = {P(x) for x in st['holidays']}
    brk = [(P(a), P(b)) for a, b in st['breaks']]
    def off(d):
        return d.weekday() == 6 or (d.weekday() == 5 and not st['satWork']) or d in hol or any(a <= d <= b for a, b in brk)
    base = P(st['start'])
    while off(base):
        base += dt.timedelta(1)
    def date_of(i):                       # 稼働日インデックス → 日付 (0 = 着工日以降の最初の稼働日)
        d, step = base, (1 if i >= 0 else -1)
        n = 0
        while n != i:
            d += dt.timedelta(step)
            if not off(d):
                n += step
        return d
    return date_of, off, base


def validate(st):
    date_of, off, base = calendar(st)
    T = st['tasks']
    ids = [t['id'] for t in T]
    warn = []
    if len(ids) != len(set(ids)):
        warn.append('id が重複しています: ' + ', '.join(sorted({i for i in ids if ids.count(i) > 1})))
    gnames = {g['name'] for g in st['groups']}
    for t in T:
        if t['group'] not in gnames:
            warn.append(f"{t['id']}: group「{t['group']}」が groups にありません(画面に出ません)")
        if t['d'] < 1:
            warn.append(f"{t['id']}: d(稼働日数)が1未満")
    by = {t['id']: t for t in T}
    e = lambda t: t['s'] + t['d'] - 1
    for t in T:
        for dep in [x for x in re.split(r'[;,\s]+', t.get('dep', '')) if x]:
            p = by.get(dep)
            if not p:
                warn.append(f"{t['id']}: 先行 {dep} が存在しません")
            elif t['s'] < e(p) or (t['s'] == e(p) and t['type'] not in ('milestone', 'approval')):
                warn.append(f"{t['id']} {t['name']} が先行 {dep} {p['name']}(〜{date_of(e(p)):%m/%d})の完了前に開始({date_of(t['s']):%m/%d})")
    # 足場の計画届は組立の30日前まで(高さ10m以上・60日以上の場合)
    nt = [t for t in T if '計画届' in t['name'] and '足場' in t['name']]
    sc = [t for t in T if '足場' in t['name'] and '組立' in t['name'] and '解体' not in t['name'] and t['type'] == 'task']
    if nt and sc:
        gap = (date_of(min(t['s'] for t in sc)) - date_of(nt[0]['s'])).days
        if gap < 30:
            warn.append(f"足場計画届 → 足場組立が{gap}日(30日未満)")
    end = date_of(max(e(t) for t in T if t['s'] >= 0))
    print(f"着工日 {base}  最終日 {end}  約{round((end - base).days / 30.44, 1)}か月  稼働日{max(e(t) for t in T) + 1}日  行数{len(T)}")
    print('警告なし' if not warn else '警告 %d件:' % len(warn))
    for w in warn:
        print('  -', w)
    return warn


def find_chrome():
    for p in [r'C:\Program Files\Google\Chrome\Application\chrome.exe', r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
              r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', r'C:\Program Files\Microsoft\Edge\Application\msedge.exe']:
        if os.path.exists(p):
            return p


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    src, dest = sys.argv[1], sys.argv[2]
    st = json.load(open(src, encoding='utf-8'))
    validate(st)
    html = (HERE / '工程表テンプレート_編集版.html').read_text(encoding='utf-8')
    title = '工程表 - ' + st['meta']['name']
    html = html.replace('{{TITLE}}', title).replace('/*STATE*/{}', json.dumps(st, ensure_ascii=False).replace('<', '\u003c'))
    pathlib.Path(dest).write_text(html, encoding='utf-8')
    print('HTML:', dest)
    if '--pdf' in sys.argv:
        chrome = find_chrome()
        if not chrome:
            print('Chrome/Edge が見つからないためPDFは作成しませんでした(HTMLをブラウザで開き 印刷→PDF保存)'); return
        pdf = str(pathlib.Path(dest).with_suffix('.pdf').resolve())
        subprocess.run([chrome, '--headless=new', '--disable-gpu', '--no-pdf-header-footer', f'--print-to-pdf={pdf}',
                        pathlib.Path(dest).resolve().as_uri()], check=False, capture_output=True, timeout=120)
        print('PDF:', pdf, '(存在)' if os.path.exists(pdf) else '(作成失敗)')


if __name__ == '__main__':
    main()
