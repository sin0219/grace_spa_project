# GRACE SPA メール機能セットアップガイド

## 📧 概要

GRACE SPAの予約システムに本格的なメール機能を追加しました。以下の機能が利用可能です：

- 顧客向け予約確認メール（自動送信）
- 管理者向け新規予約通知メール（自動送信）
- 予約リマインダーメール（スケジュール送信）
- 予約キャンセル通知メール
- 予約ステータス変更通知メール
- メール送信ログ管理
- カスタマイズ可能なメールテンプレート

## 🚀 セットアップ手順

### 1. 必要なファイルの作成

以下のファイル・フォルダ構造を作成してください：

```
grace_spa_project/
├── emails/                           # 新規アプリケーション
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── admin.py
│   ├── utils.py
│   ├── signals.py
│   ├── management/
│   │   ├── __init__.py
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── send_emails.py
│   │       ├── schedule_reminders.py
│   │       └── init_email_templates.py
│   └── migrations/
│       ├── __init__.py
│       └── 0001_initial.py
├── static/admin/
│   ├── css/
│   │   └── email_template.css
│   └── js/
│       └── mail_settings.js
├── .env.example                      # 環境変数のサンプル
└── setup_email.py                    # セットアップスクリプト
```

### 2. 設定ファイルの更新

`grace_spa_project/settings.py` を提供されたコードで更新してください。主な変更点：

- `emails` アプリを `INSTALLED_APPS` に追加
- メール設定（SMTP、送信者情報など）を追加
- 予約関連メール設定を追加

### 3. 環境変数の設定

`.env.example` をコピーして `.env` ファイルを作成し、以下を設定：

```bash
# Gmailの設定
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password  # ⚠️ アプリパスワードを使用

# その他の設定
SECRET_KEY=your-secret-key-here
SITE_URL=https://gracespa.com
```

**📋 Gmailアプリパスワードの取得方法：**
1. Googleアカウント → セキュリティ
2. 2段階認証を有効化
3. アプリパスワード → 「その他」→ 「Django App」
4. 生成されたパスワードを `EMAIL_HOST_PASSWORD` に設定

### 4. セットアップスクリプトの実行

```bash
python setup_email.py
```

または手動で実行：

```bash
# データベースマイグレーション
python manage.py makemigrations emails
python manage.py migrate

# メールテンプレート初期化
python manage.py init_email_templates
```

### 5. 管理画面での設定

Django管理画面 (`/admin/`) で以下を設定：

1. **メール設定** (`/admin/emails/mailsettings/`)
   - 送信者情報（名前、メールアドレス）
   - 管理者情報
   - 通知機能の有効/無効
   - リマインダー送信時間
   - メール署名

2. **メールテンプレート** (`/admin/emails/emailtemplate/`)
   - 件名、本文の内容をカスタマイズ
   - HTML版のメールテンプレート編集

3. **テストメール送信**
   - メール設定画面で「テストメール送信」ボタンをクリック
   - 正常に送信されることを確認

## 📨 利用可能なメールテンプレート

### 1. 顧客向け予約確認メール
- **送信タイミング:** 新規予約作成時（自動）
- **内容:** 予約詳細、来店案内、注意事項

### 2. 管理者向け新規予約通知
- **送信タイミング:** 新規予約作成時（自動）
- **内容:** 顧客情報、予約詳細、管理画面リンク

### 3. 予約リマインダー
- **送信タイミング:** 予約の24時間前・2時間前（設定可能）
- **内容:** 予約確認、来店準備の案内

### 4. 予約キャンセル通知
- **送信タイミング:** 予約キャンセル時（自動）
- **内容:** キャンセル確認、再予約の案内

### 5. 予約ステータス変更通知
- **送信タイミング:** 予約ステータス変更時（自動）
- **内容:** 変更内容、次のステップの案内

## 🔧 テンプレート変数

メールテンプレートで使用可能な変数：

### 予約関連
- `{{ booking.booking_date }}` - 予約日
- `{{ booking.booking_time }}` - 予約時間
- `{{ booking_datetime_formatted }}` - 日時（フォーマット済み）
- `{{ service.name }}` - サービス名
- `{{ service.price }}` - 料金
- `{{ service.duration_minutes }}` - 施術時間
- `{{ therapist.display_name }}` - 施術者名（指名なしの場合は空）

### 顧客関連
- `{{ customer.name }}` - 顧客名
- `{{ customer.email }}` - メールアドレス
- `{{ customer.phone }}` - 電話番号

### システム関連
- `{{ mail_settings.signature }}` - メール署名
- `{{ site_name }}` - サイト名
- `{{ site_url }}` - サイトURL
- `{{ current_year }}` - 現在の年

## ⚙️ 管理機能

### メール送信ログ
- **場所:** `/admin/emails/emaillog/`
- **機能:** 
  - 送信済み/失敗したメールの確認
  - エラー詳細の確認
  - 再送信処理
  - 送信統計

### バッチ処理（リマインダ