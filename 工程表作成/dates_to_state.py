# -*- coding: utf-8 -*-
"""日付つきの工程案(JSON配列)を、稼働日インデックス形式の state.json に変換する。

使い方:  python dates_to_state.py <base_state.json> <出力state.json> <rows1.json> [rows2.json ...]

base_state.json : meta / start / satWork / holidays / breaks / groups / notes を持つ state(tasks は空でよい)
rows*.json      : [{"group","id","name","note","type","dep","start":"YYYY-MM-DD","end":"YYYY-MM-DD"}, ...]
                  日付は base_state のカレンダー(日曜・祝日・休工期間を除く稼働日)上の日付であること
                  (休工日を指していたら次の稼働日/前の稼働日に丸めて警告を出す)
"""
import json, sys, io, datetime as dt

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
P = dt.date.fromisoformat


def main():
    base_path, out_path, *row_paths = sys.argv[1:]
    st = json.load(open(base_path, encoding='utf-8'))
    hol = {P(x) for x in st['holidays']}
    brk = [(P(a), P(b)) for a, b in st['breaks']]
    off = lambda d: d.weekday() == 6 or (d.weekday() == 5 and not st['satWork']) or d in hol or any(a <= d <= b for a, b in brk)
    base = P(st['start'])
    while off(base):
        base += dt.timedelta(1)

    def idx(d, snap):
        if off(d):
            step = 1 if snap == 'fwd' else -1
            d0 = d
            while off(d):
                d += dt.timedelta(step)
            print(f'  ! {d0} は休工日のため {d} に丸めました')
        n, x, step = 0, base, (1 if d >= base else -1)
        while x != d:
            x += dt.timedelta(step)
            if not off(x):
                n += step
        return n

    order = {g['name']: i for i, g in enumerate(st['groups'])}
    rows = [r for p in row_paths for r in json.load(open(p, encoding='utf-8'))]
    for r in rows:
        if r['group'] not in order:
            print(f"  ! group「{r['group']}」が base_state.groups に無いため末尾に追加します")
            order[r['group']] = len(order)
            st['groups'].append({'name': r['group'], 'color': '#607d8b'})
    rows.sort(key=lambda r: (order[r['group']], r['start'], r['end']))
    tasks = []
    for r in rows:
        s, e = idx(P(r['start']), 'fwd'), idx(P(r['end']), 'bwd')
        one = r['type'] in ('milestone', 'approval')
        tasks.append(dict(id=r['id'], group=r['group'], name=r['name'], note=r.get('note', ''), type=r['type'], dep=r.get('dep', ''),
                          s=s, d=1 if one else max(1, e - s + 1)))
    st['tasks'] = tasks
    json.dump(st, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(tasks)} 行を変換 → {out_path}')


if __name__ == '__main__':
    main()
