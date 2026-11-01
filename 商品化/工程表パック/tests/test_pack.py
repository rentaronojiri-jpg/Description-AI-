# -*- coding: utf-8 -*-
import json, pathlib, re, sys, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC, DIST = ROOT / 'src', ROOT / 'dist'
sys.path.insert(0, str(ROOT.parents[1] / '工程表作成'))

FORBIDDEN_WORDS = ['中目黒', '目黒', 'AXIS', '英進', '株式会社', 'T7030001171938', '埼玉', '東京都']
FORBIDDEN_PATTERNS = [r'\d{2,4}-\d{2,4}-\d{4}', r'T\d{13}', r'〒?\d{3}-\d{4}']


def scan(text):
    hits = [w for w in FORBIDDEN_WORDS if w in text]
    hits += [p for p in FORBIDDEN_PATTERNS if re.search(p, text)]
    return hits


class TestSources(unittest.TestCase):
    def test_sources_have_no_private_strings(self):
        files = list(SRC.glob('*'))
        self.assertTrue(files, 'src is empty')
        for p in files:
            self.assertEqual(scan(p.read_text(encoding='utf-8')), [], p.name)

    def test_sample_state_validates_without_warnings(self):
        import build_schedule
        st = json.loads((SRC / 'sample_state.json').read_text(encoding='utf-8'))
        self.assertEqual(build_schedule.validate(st), [])
        self.assertGreaterEqual(len(st['tasks']), 80)
        self.assertEqual(st['meta']['name'], '◯◯ビル改修工事')

    def test_blank_state_is_empty_but_valid_shape(self):
        st = json.loads((SRC / 'blank_state.json').read_text(encoding='utf-8'))
        self.assertEqual(st['tasks'], [])
        for k in ('meta', 'start', 'satWork', 'holidays', 'breaks', 'groups', 'notes'):
            self.assertIn(k, st)

    def test_template_footer_is_editable_blank(self):
        t = (SRC / 'template.html').read_text(encoding='utf-8')
        self.assertIn('data-meta="footer"', t)
        self.assertIn('{{TITLE}}', t)
        self.assertIn('/*STATE*/{}', t)


class TestBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT))
        import build_pack
        cls.bp = build_pack
        cls.out = build_pack.build(DIST)

    def test_files_created(self):
        for name in ('工程表テンプレート_サンプル入り.html', '工程表テンプレート_白紙.html', '工程表サンプル.pdf'):
            self.assertTrue((DIST / name).exists(), name)

    def test_built_html_has_no_private_strings(self):
        for p in DIST.glob('*.html'):
            self.assertEqual(scan(p.read_text(encoding='utf-8')), [], p.name)

    def test_sample_renders_all_rows(self):
        dom = self.bp.render_dom(DIST / '工程表テンプレート_サンプル入り.html')
        self.assertGreaterEqual(dom.count('class="row'), 80)
        self.assertEqual(scan(dom), [])

    def test_blank_renders_without_error(self):
        dom = self.bp.render_dom(DIST / '工程表テンプレート_白紙.html')
        self.assertIn('工　程　表', dom)
        # 描画が途中で止まると工期欄・工種グループ・凡例が空のままになる
        m = re.search(r'id="period"[^>]*>([^<]*)<', dom)
        self.assertTrue(m and '〜' in m.group(1), 'period cell is empty: render stopped')
        self.assertIn('class="grp"', dom, 'group header row missing')

    def test_holiday_calendar_is_rendered(self):
        dom = self.bp.render_dom(DIST / '工程表テンプレート_サンプル入り.html')
        self.assertGreaterEqual(dom.count('class="cal"'), 5)
        self.assertRegex(dom, r'<button class="hol" data-hd="2027-01-11"')
        self.assertRegex(dom, r'<button class="brk" data-hd="2026-12-30"[^>]*disabled')
        self.assertRegex(dom, r'<button class="sun" data-hd="2027-01-10"[^>]*disabled')
        blank = self.bp.render_dom(DIST / '工程表テンプレート_白紙.html')
        self.assertGreaterEqual(blank.count('class="cal"'), 3)

    def test_end_date_input_exists(self):
        for n in ('工程表テンプレート_サンプル入り.html', '工程表テンプレート_白紙.html'):
            t = (DIST / n).read_text(encoding='utf-8')
            self.assertIn('id="endDate"', t, n)
            self.assertIn('竣工日', t, n)

    def test_pdf_pages_are_all_a3_landscape(self):
        import fitz
        doc = fitz.open(DIST / '工程表サンプル.pdf')
        self.assertLessEqual(len(doc), 3)
        for pg in doc:
            self.assertAlmostEqual(pg.rect.width, 1191, delta=6)
            self.assertAlmostEqual(pg.rect.height, 842, delta=6)
            self.assertGreater(len(pg.get_text()), 200)


class TestDocs(unittest.TestCase):
    NAMES = ['1_施工者向け使い方.html', '2_発注者向けチェックリスト.html', '3_ご利用上の注意.html']

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT))
        import build_pack
        build_pack.build(DIST)

    def test_docs_exist_and_clean(self):
        for n in self.NAMES:
            t = (DIST / n).read_text(encoding='utf-8')
            self.assertEqual(scan(t), [], n)
            self.assertIn('@page', t)

    def test_checklist_marks_uncertain_law_as_check_required(self):
        t = (DIST / self.NAMES[1]).read_text(encoding='utf-8')
        self.assertGreaterEqual(t.count('要確認'), 3)
        for kw in ('石綿', '足場', 'フロン', '道路使用', '構造', '乾燥', '引渡し'):
            self.assertIn(kw, t)

    def test_guide_explains_calendar_selection(self):
        t = (DIST / self.NAMES[0]).read_text(encoding='utf-8')
        for kw in ('カレンダー', 'Shift', '文字で編集'):
            self.assertIn(kw, t)

    def test_guide_explains_end_date(self):
        t = (DIST / self.NAMES[0]).read_text(encoding='utf-8')
        self.assertIn('竣工日', t)
        self.assertIn('伸び縮み', t)

    def test_guide_covers_every_toolbar_feature(self):
        t = (DIST / self.NAMES[0]).read_text(encoding='utf-8')
        for kw in ('着工日', '土曜', '元に戻す', '工種グループ', '保存', '印刷', '休工日', 'ドラッグ'):
            self.assertIn(kw, t)

    def test_scaffold_wording_is_consistent(self):
        st = json.loads((SRC / 'sample_state.json').read_text(encoding='utf-8'))
        note = [t['note'] for t in st['tasks'] if '足場' in t['name'] and '計画届' in t['name']][0]
        self.assertIn('要確認', note)
        self.assertNotIn('着工30日前', note)
        t = (DIST / self.NAMES[1]).read_text(encoding='utf-8')
        self.assertGreaterEqual(t.count('要確認'), 5)

    def test_guide_mentions_builtin_holiday_limit(self):
        t = (DIST / self.NAMES[0]).read_text(encoding='utf-8')
        self.assertIn('2027年5月', t)

    def test_notice_states_responsibility(self):
        t = (DIST / self.NAMES[2]).read_text(encoding='utf-8')
        for kw in ('目安', '管轄', '責任', '再配布'):
            self.assertIn(kw, t)


class TestZip(unittest.TestCase):
    def test_zip_contains_all_files_and_is_clean(self):
        import zipfile
        sys.path.insert(0, str(ROOT))
        import build_pack
        build_pack.build(DIST)
        z = build_pack.make_zip(DIST)
        with zipfile.ZipFile(z) as zf:
            names = zf.namelist()
            self.assertEqual(len(names), 6, names)
            for n in names:
                self.assertEqual(scan(n), [], n)
                if n.endswith('.html'):
                    self.assertEqual(scan(zf.read(n).decode('utf-8')), [], n)


if __name__ == '__main__':
    unittest.main()
