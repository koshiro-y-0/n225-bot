# TODO — n225-bot 開発タスク管理

## Phase 2: 日本株モジュール単体開発

### 2-1. yfinance で日経平均データ取得 ✅
- [x] `src/nikkei/fetch_nikkei.py` を作成
- [x] `^N225` から終値・前日比・前日比(%)を取得する関数
- [x] 52週高値を取得する関数
- [x] 年初来騰落率を算出する関数
- [x] フォールバック値の定義（API障害時用）
- [x] 単体テスト `tests/test_fetch_nikkei.py` を作成

### 2-2. JPX 公式サイトから PER/EPS スクレイピング ✅
- [x] `src/nikkei/jpx_scraper.py` を作成
- [x] JPX `misc/04.html` からプライム市場加重平均PER/PBRを取得
- [x] EPS算出（日経平均 / PER）
- [x] HTML構造変更時のフォールバック処理
- [x] PER 水準コメント生成（長期平均15倍との比較）
- [x] 単体テスト `tests/test_jpx_scraper.py` を作成

### 2-3. 節目判定ロジック ✅
- [x] `src/nikkei/nikkei_module.py` を作成
- [x] 日経平均の節目判定（config.py の NIKKEI_MILESTONES 参照）
- [x] EPS の節目判定（config.py の EPS_MILESTONES 参照）
- [x] 前回節目状態の管理（重複通知防止）
- [x] 節目アラートメッセージ整形
- [x] 単体テスト `tests/test_nikkei_module.py` を作成

### 2-4. 日経平均テンプレート作成 ✅
- [x] `templates/daily_nikkei.j2` を作成（設計書のメッセージイメージに準拠）
- [x] `templates/nikkei_alert.j2` を作成（節目アラート用）
- [x] テンプレート変数の定義を文書化

### 2-5. 単独 LINE 送信テスト
- [x] `src/nikkei/send_test.py` 作成（fetch → テンプレート → LINE送信 の通しテスト）
- [x] `.github/workflows/nikkei_test.yml` 追加（workflow_dispatch）
- [ ] GitHub Actions Secrets 登録後、Actions タブから手動実行して動作確認

---

## Phase 3: dispatcher.py 統合

### 3-1. dispatcher.py の実装
- [ ] 曜日判定ロジック（月曜 → 金曜終値配信フラグ）
- [ ] `nikkei_module` 呼出し + `ueda_module` 呼出し
- [ ] 両モジュールのメッセージを統合して1つの配信にまとめる
- [ ] 統合テンプレート `templates/daily_integrated.j2` を作成

### 3-2. daily.yml の切り替え
- [ ] dispatcher.py をエントリーポイントに設定（既に設定済み、動作確認のみ）
- [ ] 月曜日の配信メッセージに「先週金曜日の情報です」が表示されることを確認

### 3-3. alert.yml の拡張
- [ ] 日経平均の節目アラートを alert.yml に追加
- [ ] EPS 節目アラートを alert.yml に追加
- [ ] 前回節目フラグの永続化方式を決定（GitHub Cache or ファイル）
- [ ] 重複通知防止の動作確認

### 3-4. 統合テスト
- [ ] 全機能を統合した状態で LINE 送信テスト
- [ ] 月曜日ルールのテスト
- [ ] アラートの重複通知防止テスト

---

## Phase 4: ウィークリーレポート

### 4-1. 週間データ集計
- [ ] `src/nikkei/weekly_report.py` を作成
- [ ] 月〜金の日経平均終値を yfinance でまとめ取得
- [ ] 週間騰落額・騰落率を算出
- [ ] PER/EPS の週間変化を算出

### 4-2. 週間チャート画像生成
- [ ] matplotlib で日経225 週間折れ線チャートを生成
- [ ] 800 x 400px、PNG 形式
- [ ] UedaBot の `generate_chart.py` パターンを踏襲

### 4-3. ウィークリーテンプレート
- [ ] `templates/weekly_nikkei.j2` を作成（設計書のメッセージイメージに準拠）
- [ ] UedaBot 週次サマリーとの統合方式を検討

### 4-4. LINE 画像送信
- [ ] `src/common/notify.py` の `send_line_image()` を利用
- [ ] multipart/form-data でテキスト + 画像を同時送信
- [ ] weekly.yml の動作確認（金曜 15:30 JST）

### 4-5. 統合テスト
- [ ] 金曜 15:30 に画像付きウィークリーレポートが配信されることを確認

---

## 横断タスク（全 Phase 共通）

- [ ] GitHub Secrets の登録（LINE_CHANNEL_TOKEN, LINE_USER_ID, ESTAT_API_KEY, LINE_CHANNEL_SECRET）
- [ ] Vercel へのデプロイ設定（Webhook 対話機能用）
- [ ] `.env.example` の作成（ローカル開発用の環境変数テンプレート）
