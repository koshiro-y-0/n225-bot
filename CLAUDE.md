# CLAUDE.md — n225-bot プロジェクトガイド

## プロジェクト概要

日本株・マクロ経済情報を LINE で自動配信する Bot。
既存の UedaBot（植田総裁Bot）に日本株モジュールを統合し、GitHub Actions でサーバーレス運用する。

**コスト制約: 完全無料（¥0）運用**

## 技術スタック

| カテゴリ | 技術 |
|---|---|
| 言語 | Python 3.11 |
| 実行基盤 | GitHub Actions (cron) |
| 通知 | LINE Messaging API / Discord Webhook |
| 対話 | Vercel Serverless Functions (Webhook) |
| データ取得 | yfinance / JPX スクレイピング (BeautifulSoup4) / 日銀 IMAS API / e-Stat API |
| テンプレート | Jinja2 |
| チャート | matplotlib |
| テスト | pytest |

## ディレクトリ構造

```
n225-bot/
├── .github/workflows/
│   ├── daily.yml          # 平日 8:30 JST 定時配信
│   ├── weekly.yml         # 金曜 15:30 JST 週次レポート
│   ├── alert.yml          # 平日 30分毎 節目アラート
│   └── test.yml           # feature/* push / PR で自動テスト
├── src/
│   ├── common/            # 共通モジュール
│   │   ├── notify.py      # LINE / Discord 送信
│   │   ├── data_store.py  # CSV 永続化
│   │   └── tz.py          # JST ユーティリティ
│   ├── ueda/              # UedaBot（植田総裁Bot）
│   │   ├── main.py        # 日次エントリーポイント
│   │   ├── weekly_main.py # 週次エントリーポイント
│   │   ├── forex_alert.py # 為替アラート
│   │   ├── fetch_indicators.py
│   │   ├── fetch_detail.py
│   │   ├── generate_report.py
│   │   ├── generate_detail.py
│   │   ├── generate_weekly.py
│   │   ├── generate_chart.py
│   │   ├── generate_glossary.py
│   │   └── generate_richmenu.py
│   └── nikkei/            # 日本株モジュール（新規開発）
│       ├── fetch_nikkei.py       # yfinance (^N225)
│       ├── jpx_scraper.py        # PER/EPS スクレイピング
│       ├── nikkei_module.py      # メッセージ整形・節目判定
│       └── weekly_report.py      # 週次集計・チャート
├── api/
│   └── webhook.py         # Vercel Webhook（LINE 対話応答）
├── templates/             # Jinja2 テンプレート
├── data/                  # CSV・チャート画像（Actions がコミット）
├── tests/
├── specs/                 # 設計書
├── dispatcher.py          # 統合エントリーポイント
├── config.py              # 節目設定・定数管理
├── requirements.txt
└── vercel.json
```

## アーキテクチャ

### 3層構造

```
[データ取得層]          [処理・生成層]          [配信層]
yfinance (^N225)   →  nikkei_module.py    →  LINE Messaging API
JPX scraper        →  generate_report     →  Discord Webhook
BOJ IMAS API       →  generate_weekly     →  GitHub Actions (cron)
e-Stat API         →  generate_chart
yfinance (FX)      →  dispatcher.py（統合）
```

### エントリーポイント

| ファイル | 呼び出し元 | 役割 |
|---|---|---|
| `dispatcher.py` | daily.yml | 曜日判定 → UedaBot + 日経モジュール統合配信 |
| `src/ueda/weekly_main.py` | weekly.yml | 週間サマリー + チャート画像 |
| `src/ueda/forex_alert.py` | alert.yml | 為替アラート判定 |

## インポート規約

パッケージインポート方式を採用。各モジュールは `src.common.*` / `src.ueda.*` / `src.nikkei.*` で参照する。

```python
# 正しいインポート
from src.common.tz import now_jst
from src.common.notify import send_line, send_all
from src.ueda.fetch_indicators import fetch_all
from src.nikkei.fetch_nikkei import fetch_nikkei225

# やってはいけない（旧方式のフラットインポート）
from tz import now_jst  # NG
from notify import send_line  # NG
```

エントリーポイントファイル（`dispatcher.py`, `src/ueda/main.py` 等）は先頭でプロジェクトルートを `sys.path` に追加する:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
```

## テンプレートとパスの解決

テンプレートディレクトリはプロジェクトルートの `templates/` に統一:

```python
TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
```

データディレクトリも同様:

```python
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
```

## GitHub Actions スケジュール

| Workflow | cron (UTC) | JST | 内容 |
|---|---|---|---|
| daily.yml | `0 23 * * 0-4` | 平日 8:30 | 定時レポート |
| weekly.yml | `30 6 * * 5` | 金曜 15:30 | ウィークリー + 画像 |
| alert.yml | `*/30 0-7 * * 1-5` | 平日 9-16時 30分毎 | 節目アラート |
| test.yml | push/PR | - | pytest 自動実行 |

## 環境変数（GitHub Secrets）

| 変数名 | 用途 | 必須 |
|---|---|---|
| `LINE_CHANNEL_TOKEN` | LINE Messaging API Bearer トークン | Yes |
| `LINE_CHANNEL_SECRET` | Webhook 署名検証用 | Yes (Webhook) |
| `LINE_USER_ID` | Push 通知先ユーザーID | Yes |
| `ESTAT_API_KEY` | e-Stat API キー（CPI 取得） | Yes |
| `DISCORD_WEBHOOK_URL` | Discord デバッグ用 | No |
| `FOREX_ALERT_THRESHOLD` | 為替アラート閾値（デフォルト 2.0円） | No |

## Git ワークフロー

- **main ブランチへの直接コミット禁止**
- 機能ごとに `feature/xxx` ブランチを作成
- 意味のあるまとまりでこまめにコミット
- 完了後は GitHub に Push → PR 作成
- テストは `test.yml` が自動実行

## コーディング規約

- Python 3.11 準拠
- 関数・クラスには日本語 docstring を記述
- テンプレート変数名は snake_case
- エラーハンドリング: データ取得失敗時はフォールバック値を使用し、配信をスキップしない
- JPX スクレイピングは HTML 構造変更リスクがあるため、try/except で囲みフォールバックを必ず用意する
- yfinance も非公式ライブラリのため同様にフォールバック対応

## よく使うコマンド

```bash
# テスト実行
pytest tests/ -v

# ローカルでの日次レポート生成テスト（LINE送信なし）
python -c "
import sys; sys.path.insert(0, '.')
from src.ueda.fetch_indicators import fetch_all
data = fetch_all()
from src.ueda.generate_report import generate_report
print(generate_report(data))
"

# dispatcher 実行（統合配信テスト）
python dispatcher.py

# リッチメニュー画像生成
python src/ueda/generate_richmenu.py

# リッチメニュー LINE 登録
python src/ueda/generate_richmenu.py --register
```

## 節目設定（config.py）

```python
NIKKEI_MILESTONES = [34_000, 36_000, 38_000, 40_000, 42_000]  # 日経平均
EPS_MILESTONES = [2_200, 2_300, 2_400, 2_500, 2_600]          # 日経EPS
PER_LONG_TERM_AVERAGE = 15.0                                    # PER長期平均
```

## 開発フェーズ

| Phase | 内容 | 状態 |
|---|---|---|
| Phase 1 | UedaBot 移行・リポジトリ構築 | 完了 |
| Phase 2 | 日本株モジュール単体開発 | 次に着手 |
| Phase 3 | dispatcher.py 統合（曜日制御・月曜ルール・アラート） | 未着手 |
| Phase 4 | ウィークリーレポート + matplotlib 画像送信 | 未着手 |
