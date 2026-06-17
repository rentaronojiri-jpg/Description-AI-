# 予算管理PDF読み込みスキル

`業者見積もり/` フォルダ内の業者見積PDFをすべて読み込み、
`予算管理/予算管理テンプレート.html` の各記入欄を自動記入するスキル。

## 使い方

```
/予算管理PDF読み込み
```

---

## 実行手順

### 1. PDFを収集・読み込む

`業者見積もり/` 配下のサブフォルダを含むすべての `.pdf` を列挙して読み込む。

ファイル名に全角スペースや日本語が含まれる場合は PowerShell で一時コピーしてから Read する：

```powershell
$files = Get-ChildItem -LiteralPath "業者見積もり" -Recurse -Filter "*.pdf"
Copy-Item $files[X].FullName "業者見積もり\tmp_read.pdf"
# Read 後に削除
Remove-Item "業者見積もり\tmp_read.pdf" -Confirm:$false
```

各PDFから抽出する情報：

| 項目 | 備考 |
|---|---|
| 業者名 | 発行元（右上または署名欄） |
| 工種 | 解体・塗装・内装・給排水 など |
| 現場名 | 「現場名」または「件名」欄 |
| 発注者 | 「御中」の宛名 |
| 見積日付 | 発行日 |
| 発注金額（税抜） | 小計欄 |
| 発注金額（税込） | 合計欄 |

### 2. 不足情報をユーザーに1回で確認する

PDFから読み取れない以下の項目をまとめて1回で確認する（わからない場合は空欄でOKと伝える）：

- **工事名（正式名）**：PDFの現場名と異なる場合
- **現場住所**：工事場所の住所
- **担当者名**：自社の担当者
- **工期（開始日〜完了日）**：例「令和8年6月1日〜令和8年7月31日」
- **請負金額（税込）**：クライアントへの請求額
- **整理番号**：案件管理番号（あれば）
- **自社情報**：会社名・住所・TEL・担当者（初回のみ。2回目以降はCLAUDE.mdに追記して省略可）

### 3. プロジェクト情報欄を記入する

`予算管理/予算管理テンプレート.html` の以下の箇所を更新する。

**対象箇所（`<tbody id="budget-body">` より上の部分）：**

```html
<!-- 工事名 -->
<td contenteditable="true" id="proj-name">{工事名}</td>

<!-- 整理番号 -->
<td contenteditable="true">{整理番号}</td>

<!-- 現場住所 -->
<td colspan="3" contenteditable="true">{現場住所}</td>

<!-- 発注者 -->
<td contenteditable="true">{発注者名}</td>

<!-- 担当者 -->
<td contenteditable="true">{担当者名}</td>

<!-- 工期（開始日） -->
<td contenteditable="true" id="proj-start">{工期開始日}</td>

<!-- 完了日 -->
<td contenteditable="true" id="proj-end">{完了日}</td>

<!-- 自社情報 -->
<div class="company-name" contenteditable="true">{自社名}</div>
<div contenteditable="true">〒{郵便番号}<br>{住所}<br>TEL: {TEL}<br>担当: {担当者}</div>
```

**請負金額：**

```html
<input type="number" id="input-contract" ... value="{請負金額（数値のみ）}">
```

`value` 属性を追加して初期値をセットする。

### 4. 工種別予算管理欄を記入する

PDFの工種・金額を以下のカテゴリにマッピングして `<tbody id="budget-body">` の対応行を更新する：

| PDFの工種キーワード | 予算管理の行 |
|---|---|
| 解体・産廃 | 【解体工事】の各行 |
| 足場・養生・仮設 | 【仮設工事】足場・養生 |
| 大工・ボード・間仕切・クロス・ライニング | 【建築工事】内装工事（ボード・クロス） |
| 塗装 | 【建築工事】塗装工事 |
| 電気 | 【設備工事】電気工事 |
| 給排水・衛生 | 【設備工事】給排水工事 |
| 諸経費・管理 | 【諸経費】現場管理費 |

同一カテゴリに複数の見積がある場合は金額を合算して記入する。

**記入するセル：**
- `estimate-cell`（見積金額）：PDF の税抜小計を記入
- `order-cell`（発注金額）：同上（見積＝発注の前提）
- `actual-cell`（実績金額）：空欄のまま（完了後に手入力）
- 担当業者列：業者名を記入
- 発注状況：`<span class="status-badge badge-quote">見積済</span>` に変更

**行テンプレート（記入例）：**

```html
<tr>
  <td class="center">{No.}</td>
  <td contenteditable="true">{工種名}</td>
  <td contenteditable="true" class="num estimate-cell" oninput="recalcAll()">{税抜金額（カンマ区切り）}</td>
  <td contenteditable="true" class="num budget-cell"   oninput="recalcAll()"></td>
  <td contenteditable="true" class="num order-cell"    oninput="recalcAll()">{税抜金額（カンマ区切り）}</td>
  <td contenteditable="true" class="num actual-cell"   oninput="recalcAll()"></td>
  <td class="num var-cell"></td>
  <td class="center"><span class="status-badge badge-quote">見積済</span></td>
  <td contenteditable="true">{業者名}</td>
  <td contenteditable="true"></td>
  <td class="center no-print"><button onclick="removeRow(this)" style="border:none;background:#dc2626;color:#fff;border-radius:3px;cursor:pointer;font-size:8.5pt;padding:2px 7px;">×</button></td>
</tr>
```

### 5. 業者支払管理欄を記入する

`<tbody id="vendor-body">` 内を、PDFから抽出した全業者データで置き換える。

**1件ずつ別行で記入する（同業者でも工種が異なる場合は行を分ける）。**

**税の扱い注意：**
- 標準的な10%全課税 → 税抜小計をそのまま `vendor-order-ex` に記入
- 課税・非課税混在（材料費・交通費が非課税など） → 税抜小計を記入し、備考に「実際税込〇〇円（〇〇は非課税のため差異あり）」と明記

**行テンプレート：**

```html
<tr>
  <td class="center">{No.}</td>
  <td contenteditable="true">{業者名}</td>
  <td contenteditable="true">{工種}</td>
  <td contenteditable="true" class="num vendor-order-ex" oninput="recalcVendor()">{発注金額税抜（カンマ区切り）}</td>
  <td class="num vendor-order-in"></td>
  <td contenteditable="true"></td>
  <td contenteditable="true"></td>
  <td contenteditable="true" class="num vendor-paid" oninput="recalcVendor()"></td>
  <td class="num vendor-remain"></td>
  <td class="center"><span class="status-badge badge-none">未払</span></td>
  <td contenteditable="true">{見積日付／現場名・備考}</td>
  <td class="center no-print"><button onclick="removeRow(this)" style="border:none;background:#dc2626;color:#fff;border-radius:3px;cursor:pointer;font-size:8.5pt;padding:2px 7px;">×</button></td>
</tr>
```

### 6. 入金・請求管理欄を記入する

請求情報はPDFから取得できないため、行の「請求内容」列のみ標準的な3行を記入する。
金額・日付はユーザーが後から入力する前提で空欄のまま。

```html
<tbody id="billing-body">
  <!-- 行1: 着手金 / 行2: 中間金 / 行3: 完成金 -->
</tbody>
```

既存の3行はそのまま維持する（変更不要）。

### 7. 完成を報告する

以下をユーザーに伝える：

- 読み込んだPDF件数・業者名
- 記入したセクション一覧
- 手動入力が必要な残り項目（実績金額・支払条件・支払予定日・入金情報など）
- 税計算に差異がある行があれば内容を明記して警告する
