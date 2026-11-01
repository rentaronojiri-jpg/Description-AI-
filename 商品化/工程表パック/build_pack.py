# -*- coding: utf-8 -*-
"""src から dist を作る。  使い方: python build_pack.py"""
import json, os, pathlib, subprocess, tempfile

HERE = pathlib.Path(__file__).resolve().parent
SRC, DIST = HERE / 'src', HERE / 'dist'
CHROMES = [r'C:\Program Files\Google\Chrome\Application\chrome.exe',
           r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
           r'C:\Program Files\Microsoft\Edge\Application\msedge.exe']


def find_chrome():
    for p in CHROMES:
        if os.path.exists(p):
            return p
    raise RuntimeError('Chrome/Edge が見つかりません')


def make_html(state_file, title):
    html = (SRC / 'template.html').read_text(encoding='utf-8')
    st = json.loads((SRC / state_file).read_text(encoding='utf-8'))
    return html.replace('{{TITLE}}', title).replace('/*STATE*/{}', json.dumps(st, ensure_ascii=False).replace('<', '\u003c'))


def _run_chrome(args):
    with tempfile.TemporaryDirectory() as prof:
        return subprocess.run([find_chrome(), '--headless=new', '--disable-gpu', f'--user-data-dir={prof}', *args],
                              capture_output=True, timeout=120)


def render_dom(html_path):
    r = _run_chrome(['--dump-dom', pathlib.Path(html_path).resolve().as_uri()])
    return r.stdout.decode('utf-8', 'replace')


def make_pdf(html_path, pdf_path):
    _run_chrome(['--no-pdf-header-footer', f'--print-to-pdf={pathlib.Path(pdf_path).resolve()}',
                 pathlib.Path(html_path).resolve().as_uri()])
    return pathlib.Path(pdf_path).exists()


def build(dest):
    dest = pathlib.Path(dest)
    dest.mkdir(exist_ok=True)
    out = {}
    sample = dest / '工程表テンプレート_サンプル入り.html'
    sample.write_text(make_html('sample_state.json', '工程表 - サンプル'), encoding='utf-8')
    blank = dest / '工程表テンプレート_白紙.html'
    blank.write_text(make_html('blank_state.json', '工程表'), encoding='utf-8')
    pdf = dest / '工程表サンプル.pdf'
    make_pdf(sample, pdf)
    docs = {'guide_sekosha.html': '1_施工者向け使い方.html',
            'checklist_hacchusha.html': '2_発注者向けチェックリスト.html',
            'notice.html': '3_ご利用上の注意.html'}
    for s_, d_ in docs.items():
        (dest / d_).write_text((SRC / s_).read_text(encoding='utf-8'), encoding='utf-8')
    out['docs'] = list(docs.values())
    out.update(sample=sample.name, blank=blank.name, pdf=pdf.name)
    return out


def make_zip(dest):
    import zipfile
    dest = pathlib.Path(dest)
    z = dest / '工程表パック.zip'
    if z.exists():
        z.unlink()
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(dest.iterdir()):
            if p != z:
                zf.write(p, p.name)
    return z


if __name__ == '__main__':
    print(build(DIST))
    print(make_zip(DIST))
