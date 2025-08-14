#!/usr/bin/env python
"""
メール機能セットアップスクリプト
このスクリプトを実行して、メール機能の初期設定を行います。
"""

import os
import sys
import django

# Djangoの設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grace_spa_project.settings')
django.setup()

from django.core.management import call_command
from emails.models import MailSettings

def main():
    print("GRACE SPA メール機能セットアップを開始します...")
    print("=" * 50)
    
    # 1. マイグレーション実行
    print("1. データベースマイグレーション実行中...")
    try:
        call_command('makemigrations', 'emails', verbosity=0)
        call_command('migrate', verbosity=0)
        print("✓ マイグレーション完了")
    except Exception as e:
        print(f"✗ マイグレーションエラー: {e}")
        return False
    
    # 2. メールテンプレート初期化
    print("2. メールテンプレート初期化中...")
    try:
        call_command('init_email_templates', verbosity=0)
        print("✓ メールテンプレート初期化完了")
    except Exception as e:
        print(f"✗ テンプレート初期化エラー: {e}")
        return False
    
    # 3. メール設定初期化
    print("3. メール設定初期化中...")
    try:
        mail_settings = MailSettings.get_settings()
        
        # 管理者メールアドレスの設定
        admin_email = input("管理者メールアドレスを入力してください: ").strip()
        if admin_email:
            mail_settings.admin_email = admin_email
            
        admin_name = input("管理者名を入力してください（省略可）: ").strip()
        if admin_name:
            mail_settings.admin_name = admin_name
            
        from_email = input("送信者メールアドレスを入力してください（省略可）: ").strip()
        if from_email:
            mail_settings.from_email = from_email
            
        mail_settings.save()
        print("✓ メール設定初期化完了")
        
    except Exception as e:
        print(f"✗ メール設定エラー: {e}")
        return False
    
    # 4. 環境変数の確認
    print("4. 環境変数の確認...")
    email_user = os.environ.get('EMAIL_HOST_USER')
    email_password = os.environ.get('EMAIL_HOST_PASSWORD')
    
    if not email_user or not email_password:
        print("⚠️  環境変数が設定されていません:")
        print("   EMAIL_HOST_USER: メール送信用のGmailアドレス")
        print("   EMAIL_HOST_PASSWORD: Gmailのアプリパスワード")
        print("   .envファイルを作成するか、環境変数を設定してください。")
        print("   例: .env.example を参考にしてください。")
    else:
        print("✓ 環境変数設定済み")
    
    print("=" * 50)
    print("メール機能セットアップ完了！")
    print("\n次のステップ:")
    print("1. Django管理画面で /admin/emails/ にアクセス")
    print("2. メール設定でテストメール送信を確認")
    print("3. メールテンプレートを必要に応じてカスタマイズ")
    print("4. crontabでリマインダーメール送信を設定（オプション）")
    print("   例: python manage.py schedule_reminders && python manage.py send_emails")
    
    return True

if __name__ == '__main__':
    main()