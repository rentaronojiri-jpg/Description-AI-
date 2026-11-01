"""見積書HTMLを一括増額する。使い方: python make_uplift.py 元.html 出力.html [倍率=1.10]
㎡項目は単価据え置きで数量を調整、少数量(30未満)・式・箇所は不変、%連動費は同率で増額。"""
import re,sys,html,math
sys.stdout.reconfigure(encoding='utf-8')
src=sys.argv[1]; dst=sys.argv[2]
RATE=float(sys.argv[3]) if len(sys.argv)>3 else 1.10  # 増額率（例 1.10 = 10%増）
s=open(src,encoding='utf-8').read()
cut=s.index('<script>')
body,tail=s[:cut],s[cut:]
AREA={'㎡'}
# 面積扱いの単位誤記（式だが数量は面積）
AREA_NAMES={'仮設材運搬費','高圧洗浄','浴室解体'}
PCT={'現場管理費','作業員交通費、駐車場費','法定福利費'}
MINQ=30
rowre=re.compile(r'<tr(?: class="[^"]*")?>(?:(?!</tr>).)*?</tr>',re.S)
def parse(row):
    ta=[html.unescape(x) for x in re.findall(r'<textarea[^>]*>(.*?)</textarea>',row,re.S)]
    inp=re.findall(r'<input[^>]*value="([^"]*)"',row)
    return ta,inp
# pass1: collect
items=[]
for m in re.finditer(r'<table class="items" data-cat="(\w+)">(.*?)</table>',body,re.S):
    tb=re.search(r'<tbody.*?</tbody>',m.group(2),re.S)
    for r in rowre.finditer(tb.group(0)):
        ta,inp=parse(r.group(0))
        if len(inp)<3: continue
        items.append((m.group(1),ta[0],inp[0],inp[1],inp[2]))
def amt(q,p):
    try: return round(float(q or 0)*float(p or 0))
    except: return 0
def eligible(name,q,u):
    try: qv=float(q)
    except: return False
    return (u in AREA or name.strip() in AREA_NAMES) and qv>=MINQ
def newq(q,f):
    qv=float(q)*f
    return str(int(round(qv)))
base=sum(amt(i[2],i[4]) for i in items)
target=base*RATE
pct_base=sum(amt(i[2],i[4]) for i in items if i[1].strip() in PCT)
pct_new=sum(round(amt(i[2],i[4])*RATE) for i in items if i[1].strip() in PCT)
fixed=base-pct_base
need=target-pct_new   # 非%項目の目標合計
elig=sum(amt(i[2],i[4]) for i in items if eligible(i[1],i[2],i[3]))
noelig=fixed-elig
f=(need-noelig)/elig
print('base',base,'target',target,'elig',elig,'f',f)
overrides={}  # (cat,name,q)->new q
def calc(f,ov):
    tot=0
    out=[]
    for c,n,q,u,p in items:
        if n.strip() in PCT:
            np_=str(round(float(p)*RATE)); out.append((q,np_)); tot+=amt(q,np_); continue
        if eligible(n,q,u):
            nq=ov.get((c,n,q)) or newq(q,f)
        else: nq=q
        out.append((nq,p)); tot+=amt(nq,p)
    return tot,out
tot,out=calc(f,overrides)
print('after rounding',tot,tot/base)
# fine tune: nudge items by +-1 unit to hit target
diff=target-tot
cands=[(c,n,q,u,p) for c,n,q,u,p in items if eligible(n,q,u) and float(p or 0)>0]
import itertools
# greedy by price
cands.sort(key=lambda x:-float(x[4]))
for c,n,q,u,p in cands:
    key=(c,n,q)
    cur=int(overrides.get(key) or newq(q,f))
    pr=float(p)
    k=int(diff//pr) if diff>0 else -int(-diff//pr)
    if k!=0:
        overrides[key]=str(cur+k); diff-=k*pr
    if abs(diff)<pr*0.5 and abs(diff)<2000: break
tot,out=calc(f,overrides)
print('tuned',tot,tot/base,'diff',tot-target)
# pass2: rewrite
idx=[0]
def fmt(n): return '¥{:,}'.format(n)
catsum={}
def rewrite_table(m):
    cat=m.group(1); t=m.group(2)
    sub=0
    def rrow(r):
        row=r.group(0)
        ta,inp=parse(row)
        if len(inp)<3: return row
        nq,np_=out[idx[0]]; idx[0]+=1
        a=amt(nq,np_)
        nonlocal_sub[0]+=a
        # replace qty and price input values (1st and 3rd inputs)
        cnt=[0]
        def repl(mm):
            cnt[0]+=1
            if cnt[0]==1: return mm.group(1)+nq+mm.group(3)
            if cnt[0]==3: return mm.group(1)+np_+mm.group(3)
            return mm.group(0)
        row=re.sub(r'(<input[^>]*value=")([^"]*)(")',repl,row)
        row=re.sub(r'(<td class="num amount-cell">)[^<]*(</td>)',lambda mm:mm.group(1)+fmt(a)+mm.group(2),row)
        return row
    nonlocal_sub=[0]
    tb=re.search(r'<tbody.*?</tbody>',t,re.S)
    newtb=rowre.sub(rrow,tb.group(0))
    t=t.replace(tb.group(0),newtb)
    t=re.sub(r'(id="subtotal-%s">)[^<]*'%cat,lambda mm:mm.group(1)+fmt(nonlocal_sub[0]),t)
    catsum[cat]=nonlocal_sub[0]
    return m.group(0).replace(m.group(2),t)
body2=re.sub(r'<table class="items" data-cat="(\w+)">(.*?)</table>',rewrite_table,body,flags=re.S)
grand=sum(catsum.values()); tax=round(grand*0.1); total=grand+tax
for c,v in catsum.items():
    body2=re.sub(r'(id="cat-amount-%s">)[^<]*'%c,lambda mm:mm.group(1)+fmt(v),body2)
body2=re.sub(r'(id="summary-subtotal">)[^<]*',lambda m:m.group(1)+fmt(grand),body2)
body2=re.sub(r'(id="summary-tax">)[^<]*',lambda m:m.group(1)+fmt(tax),body2)
body2=re.sub(r'(id="summary-total">)[^<]*',lambda m:m.group(1)+fmt(total),body2)
body2=re.sub(r'(id="cover-total">)[^<]*',lambda m:m.group(1)+'{:,}'.format(total),body2)
body2=re.sub(r'(id="cover-subtotal">)[^<]*',lambda m:m.group(1)+'{:,}'.format(grand),body2)
body2=re.sub(r'(id="cover-tax">)[^<]*',lambda m:m.group(1)+'{:,}'.format(tax),body2)
open(dst,'w',encoding='utf-8').write(body2+tail)
print('grand',grand,'tax',tax,'total',total,'old total',280144464,'ratio',total/280144464)
print('changes:')
i=0
for c,n,q,u,p in items:
    nq,np_=out[i];i+=1
    if nq!=q or np_!=p: print(' ',c,n.strip()[:28],q,'->',nq,'' if np_==p else f'price {p}->{np_}')
