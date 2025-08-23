# bookings/management/commands/simple_test.py
from django.core.management.base import BaseCommand
from django.test import Client, override_settings
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = '基本的なWEB予約サイトの動作確認を行います（簡易版）'
    
    def __init__(self):
        super().__init__()
        self.client = Client()
        self.test_results = []
        
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 簡易テストを開始します'))
        self.stdout.write('=' * 50)
        
        # 基本的なページテスト
        self.test_basic_pages()
        
        # データベーステスト
        self.test_database_basic()
        
        # メール機能テスト  
        self.test_email_basic()
        
        # 結果表示
        self.display_results()
    
    def test_basic_pages(self):
        """基本ページのテスト"""
        self.stdout.write(self.style.WARNING('🔍 基本ページテスト'))
        
        tests = [
            ('ホームページ', '/'),
            ('予約ステップ1', '/booking/step1/'),
            ('セラピスト紹介', '/therapists/'),
            ('管理画面', '/admin/'),
        ]
        
        for name, url in tests:
            self.run_page_test(name, url)
        
        # Django管理画面のテスト
        self.test_admin_pages()
    
    def run_page_test(self, name, url):
        """単一ページのテスト"""
        try:
            # テスト環境でALLOWED_HOSTSを一時的に設定
            from django.conf import settings
            original_allowed_hosts = settings.ALLOWED_HOSTS
            settings.ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1'] + list(original_allowed_hosts)
            
            response = self.client.get(url)
            
            # 設定を元に戻す
            settings.ALLOWED_HOSTS = original_allowed_hosts
            
            if response.status_code == 200:
                self.test_results.append((name, 'PASS', None))
                self.stdout.write(f'  ✅ {name}: OK')
            elif response.status_code == 302:
                self.test_results.append((name, 'REDIRECT', 'リダイレクト'))
                self.stdout.write(f'  🔄 {name}: リダイレクト')
            else:
                self.test_results.append((name, 'FAIL', f'Status: {response.status_code}'))
                self.stdout.write(f'  ❌ {name}: エラー ({response.status_code})')
                
        except Exception as e:
            self.test_results.append((name, 'ERROR', str(e)))
            self.stdout.write(f'  ⚠️  {name}: {str(e)}')
    
    def test_admin_pages(self):
        """管理画面のテスト"""
        self.stdout.write(self.style.WARNING('🛠️ 管理機能テスト'))
        
        # 管理者ユーザーが存在するかチェック
        admin_exists = User.objects.filter(is_superuser=True).exists()
        if admin_exists:
            self.test_results.append(('管理者ユーザー', 'PASS', None))
            self.stdout.write('  ✅ 管理者ユーザー: 存在')
        else:
            self.test_results.append(('管理者ユーザー', 'FAIL', '管理者が存在しません'))
            self.stdout.write('  ❌ 管理者ユーザー: 存在しません')
        
        # ダッシュボードテスト（管理者がいる場合）
        if admin_exists:
            admin_user = User.objects.filter(is_superuser=True).first()
            self.client.force_login(admin_user)
            
            dashboard_tests = [
                ('ダッシュボード', '/dashboard/'),
                ('予約一覧', '/dashboard/bookings/'),
                ('顧客一覧', '/dashboard/customers/'),
            ]
            
            for name, url in dashboard_tests:
                self.run_page_test(name, url)
    
    def test_database_basic(self):
        """データベースの基本テスト"""
        self.stdout.write(self.style.WARNING('🗃️ データベーステスト'))
        
        try:
            from bookings.models import Service, Customer, Booking, Therapist
            
            # モデルの基本操作テスト
            service_count = Service.objects.count()
            customer_count = Customer.objects.count()
            booking_count = Booking.objects.count()
            therapist_count = Therapist.objects.count()
            
            self.test_results.append(('データベース接続', 'PASS', None))
            self.stdout.write('  ✅ データベース接続: OK')
            
            self.stdout.write(f'     サービス数: {service_count}')
            self.stdout.write(f'     顧客数: {customer_count}')
            self.stdout.write(f'     予約数: {booking_count}')
            self.stdout.write(f'     施術者数: {therapist_count}')
            
            if service_count == 0:
                self.test_results.append(('基本データ', 'WARN', 'サービスが登録されていません'))
                self.stdout.write('  ⚠️  サービスが登録されていません')
            else:
                self.test_results.append(('基本データ', 'PASS', None))
                self.stdout.write('  ✅ 基本データ: OK')
                
        except Exception as e:
            self.test_results.append(('データベース接続', 'ERROR', str(e)))
            self.stdout.write(f'  ❌ データベースエラー: {str(e)}')
    
    def test_email_basic(self):
        """メール機能の基本テスト"""
        self.stdout.write(self.style.WARNING('📧 メール機能テスト'))
        
        try:
            from emails.models import MailSettings, EmailTemplate
            
            mail_settings_count = MailSettings.objects.count()
            email_template_count = EmailTemplate.objects.count()
            
            if mail_settings_count > 0:
                self.test_results.append(('メール設定', 'PASS', None))
                self.stdout.write('  ✅ メール設定: 存在')
            else:
                self.test_results.append(('メール設定', 'WARN', 'メール設定が未設定'))
                self.stdout.write('  ⚠️  メール設定: 未設定')
            
            if email_template_count > 0:
                self.test_results.append(('メールテンプレート', 'PASS', None))
                self.stdout.write('  ✅ メールテンプレート: 存在')
            else:
                self.test_results.append(('メールテンプレート', 'WARN', 'テンプレート未設定'))
                self.stdout.write('  ⚠️  メールテンプレート: 未設定')
                
        except ImportError:
            self.test_results.append(('メール機能', 'WARN', 'emailsアプリが設定されていません'))
            self.stdout.write('  ⚠️  emailsアプリが設定されていません')
        except Exception as e:
            self.test_results.append(('メール機能', 'ERROR', str(e)))
            self.stdout.write(f'  ❌ メール機能エラー: {str(e)}')
    
    def display_results(self):
        """結果の表示"""
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('📊 テスト結果'))
        
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r[1] == 'PASS'])
        failed = len([r for r in self.test_results if r[1] == 'FAIL'])
        errors = len([r for r in self.test_results if r[1] == 'ERROR'])
        warnings = len([r for r in self.test_results if r[1] == 'WARN'])
        redirects = len([r for r in self.test_results if r[1] == 'REDIRECT'])
        
        self.stdout.write(f'総テスト数: {total_tests}')
        self.stdout.write(f'✅ 成功: {passed}')
        self.stdout.write(f'🔄 リダイレクト: {redirects}')
        self.stdout.write(f'⚠️  警告: {warnings}')
        self.stdout.write(f'❌ 失敗: {failed}')
        self.stdout.write(f'🚨 エラー: {errors}')
        
        # 成功率計算（リダイレクトは成功とみなす）
        success_count = passed + redirects
        success_rate = (success_count / total_tests * 100) if total_tests > 0 else 0
        self.stdout.write(f'成功率: {success_rate:.1f}%')
        
        # 推奨事項
        self.stdout.write('\n💡 推奨事項:')
        if success_rate >= 80 and errors == 0:
            self.stdout.write('  ✨ 基本機能は正常に動作しています。')
            if warnings > 0:
                self.stdout.write('  🔧 いくつかの設定が不完全ですが、基本的な使用には問題ありません。')
        elif success_rate >= 60:
            self.stdout.write('  🔧 いくつかの問題がありますが、修正可能です。')
        else:
            self.stdout.write('  🚨 重要な問題があります。設定を確認してください。')
        
        # 問題のある項目を表示
        problem_items = [r for r in self.test_results if r[1] in ['FAIL', 'ERROR']]
        if problem_items:
            self.stdout.write('\n⚠️  要確認項目:')
            for name, status, detail in problem_items:
                icon = '❌' if status == 'FAIL' else '🚨'
                self.stdout.write(f'  {icon} {name}: {detail or status}')
        
        # 詳細テストの提案
        self.stdout.write(f'\n📋 次のステップ:')
        if success_rate >= 80:
            self.stdout.write('  1. python manage.py simple_fix --check-only  # 設定の確認')
            self.stdout.write('  2. 英語化作業の開始を検討')
        else:
            self.stdout.write('  1. python manage.py simple_fix  # 基本設定の修正')
            self.stdout.write('  2. python manage.py simple_test  # 再テスト')
        
        self.stdout.write('=' * 50)