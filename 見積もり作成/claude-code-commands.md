# Claude Code コマンド一覧

> 最終更新: 2026-06-13

---

## 組み込みスラッシュコマンド

会話入力欄で `/` を入力すると使えるコマンド。

| コマンド | 説明 |
|---|---|
| `/help` | ヘルプを表示 |
| `/clear` | 会話履歴をクリア（コンテキストをリセット） |
| `/compact` | 会話を圧縮してコンテキストを節約 |
| `/config` | 設定を表示・変更 |
| `/cost` | 現在のセッションのトークン使用量とコストを表示 |
| `/doctor` | Claude Code の環境・設定の健全性チェック |
| `/exit` | Claude Code を終了 |
| `/fast` | Fast モード（高速出力）のオン/オフ切り替え |
| `/ide` | IDE 連携モードの設定 |
| `/init` | プロジェクトの `CLAUDE.md` ファイルを初期化 |
| `/login` | Anthropic アカウントにログイン |
| `/logout` | ログアウト |
| `/memory` | メモリの表示・管理 |
| `/model` | 使用するモデルを変更（例: `claude-opus-4-8`） |
| `/permissions` | 現在のツール権限を表示 |
| `/pr-comments` | GitHub PR にコメントを投稿 |
| `/release-notes` | リリースノートを表示 |
| `/status` | 現在の接続・認証状態を表示 |
| `/terminal-setup` | ターミナル向け設定を最適化 |
| `/vim` | Vim キーバインドモードのオン/オフ |

---

## ユーザー呼び出しスキル（スラッシュコマンド形式）

スキルは `/<skill-name>` の形式で呼び出す。

| コマンド | 説明 |
|---|---|
| `/code-review` | コードレビューを実行。`/code-review ultra` でマルチエージェントによる詳細レビュー（`/code-review ultra <PR番号>` で GitHub PR 指定可） |
| `/security-review` | セキュリティ観点のコードレビュー |
| `/claude-api` | Claude API / Anthropic SDK の実装支援。`/claude-api migrate` で既存コードを新モデルへ移行 |
| `/init` | プロジェクト初期化（CLAUDE.md の作成） |
| `/run` | コマンド・スクリプトの実行支援 |
| `/review` | ファイル・コードのレビュー |
| `/loop` | ループモードで繰り返しタスクを自動実行 |
| `/schedule` | スケジュールベースのタスク設定 |
| `/simplify` | コードをシンプルに書き直す |
| `/verify` | 実装の検証・確認 |
| `/fewer-permission-prompts` | 権限プロンプトを減らす設定 |
| `/update-config` | 設定ファイルの更新 |
| `/keybindings-help` | キーバインド一覧を表示 |

---

## `/code-review ultra` の使い方

```
/code-review ultra            # 現在のブランチをレビュー
/code-review ultra <PR番号>   # GitHub PR を指定してレビュー
```

- git リポジトリが必要（なければ `git init` を提案）
- クラウド上でマルチエージェントが実行される（課金あり）
- `/ultrareview` は旧エイリアス（非推奨）

---

## キーボードショートカット（CLI・ターミナル）

| ショートカット | 動作 |
|---|---|
| `Ctrl+C` | 現在の生成を中断 |
| `Ctrl+D` | Claude Code を終了 |
| `↑ / ↓` | 会話履歴をナビゲート |
| `Escape` | 入力をキャンセル |

---

## モデル一覧（2026-06-13 時点）

| モデル名 | モデル ID | コンテキスト | 用途 |
|---|---|---|---|
| Claude Fable 5 | `claude-fable-5` | 1M | 最高性能・最難タスク |
| Claude Opus 4.8 | `claude-opus-4-8` | 1M | デフォルト推奨 |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 1M | バランス型 |
| Claude Haiku 4.5 | `claude-haiku-4-5` | 200K | 高速・低コスト |

> **デフォルト推奨**: `claude-opus-4-8`（特に指定がない場合）

---

## よくある使い方パターン

### プロジェクト初期化
```
/init
```

### モデル変更
```
/model claude-opus-4-8
```

### コスト確認
```
/cost
```

### PR レビュー（GitHub）
```
/code-review ultra 123
```

### ループタスク
```
/loop テストが全部通るまでバグを修正し続けて
```
