# bookings/management/commands/run_system_test.py
from django.core.management.base import BaseCommand
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, date, timedelta
from bookings.models import Service, Customer, Booking, Therapist, BusinessHours, Schedule, BookingSettings
from emails.models import MailSettings, EmailTemplate
import json
import re


class Command(BaseCommand):
    help = 'WEB予約サイトの全機能を自動テストします'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='詳細なテスト結果を表示'
        )
        parser.add_argument(
            '--category',
            type=str,
            choices=['basic', 'validation', 'email', 'admin', 'security'],
            help='特定のカテゴリのみテスト'
        )
    
    def __init__(self):
        super().__init__()
        self.client = Client()
        self.test_results = []
        self.detailed = False
        
    def handle(self, *args, **options):
        self.detailed = options['detailed']
        category = options.get('category')
        
        self.stdout.write(self.style.SUCCESS('🚀 GRACE SPA 自動テストを開始します'))
        self.stdout.write('=' * 50)
        
        # テストデータの準備
        self.setup_test_data()
        
        # テスト実行
        if not category or category == 'basic':
            self.test_basic_functionality()
        if not category or category == 'validation':
            self.test_form_validation()
        if not category or category == 'email':
            self.test_email_functionality()
        if not category or category == 'admin':
            self.test_admin_functionality()
        if not category or category == 'security':
            self.test_security()
            
        # テスト結果の表示
        self.display_results()
    
    def setup_test_data(self):
        """テストデータの準備"""
        self.stdout.write('📋 テストデータを準備中...')
        
        # サービス作成
        self.service, _ = Service.objects.get_or_create(
            name='テスト施術',
            defaults={
                'duration_minutes': 60,
                'price': 10000,
                'description': 'テスト用サービス',
                'is_active': True
            }
        )
        
        # 施術者作成
        self.therapist, _ = Therapist.objects.get_or_create(
            name='テスト施術者',
            defaults={
                'display_name': 'テスト施術者',
                'is_active': True
            }
        )
        
        # 営業時間設定
        BusinessHours.objects.get_or_create(
            weekday=0,  # 月曜日
            defaults={
                'is_open': True,
                'open_time': '09:00',
                'close_time': '18:00',
                'last_booking_time': '17:00'
            }
        )
        
        # 管理者作成
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                'testadmin', 
                'admin@test.com', 
                'testpass123'
            )
    
    def test_basic_functionality(self):
        """基本機能のテスト"""
        self.stdout.write(self.style.WARNING('🔍 基本機能テスト'))
        
        tests = [
            ('ホームページ表示', self.test_home_page),
            ('予約ステップ1', self.test_booking_step1),
            ('予約ステップ2', self.test_booking_step2),
            ('予約ステップ3', self.test_booking_step3),
            ('セラピスト紹介', self.test_therapists_page),
            ('時間枠取得API', self.test_available_times_api),
        ]
        
        self.run_test_category(tests, '基本機能')
    
    def test_form_validation(self):
        """フォームバリデーションのテスト"""
        self.stdout.write(self.style.WARNING('📝 フォームバリデーションテスト'))
        
        tests = [
            ('必須項目チェック', self.test_required_fields),
            ('メールアドレス形式', self.test_email_format),
            ('電話番号形式', self.test_phone_format),
            ('SQLインジェクション対策', self.test_sql_injection),
            ('XSS対策', self.test_xss_protection),
            ('CSRF保護', self.test_csrf_protection),
        ]
        
        self.run_test_category(tests, 'フォームバリデーション')
    
    def test_email_functionality(self):
        """メール機能のテスト"""
        self.stdout.write(self.style.WARNING('📧 メール機能テスト'))
        
        tests = [
            ('メール設定確認', self.test_mail_settings),
            ('メールテンプレート', self.test_email_templates),
            ('予約確認メール', self.test_booking_confirmation_email),
        ]
        
        self.run_test_category(tests, 'メール機能')
    
    def test_admin_functionality(self):
        """管理機能のテスト"""
        self.stdout.write(self.style.WARNING('🛠️ 管理機能テスト'))
        
        tests = [
            ('管理画面アクセス', self.test_admin_access),
            ('ダッシュボード', self.test_dashboard),
            ('予約管理', self.test_booking_management),
            ('顧客管理', self.test_customer_management),
        ]
        
        self.run_test_category(tests, '管理機能')
    
    def test_security(self):
        """セキュリティテスト"""
        self.stdout.write(self.style.WARNING('🔒 セキュリティテスト'))
        
        tests = [
            ('認証保護', self.test_auth_protection),
            ('権限チェック', self.test_permission_check),
            ('セキュリティヘッダー', self.test_security_headers),
        ]
        
        self.run_test_category(tests, 'セキュリティ')
    
    def run_test_category(self, tests, category_name):
        """テストカテゴリの実行"""
        for test_name, test_func in tests:
            try:
                result = test_func()
                self.test_results.append({
                    'category': category_name,
                    'name': test_name,
                    'status': 'PASS' if result else 'FAIL',
                    'details': getattr(test_func, '_details', None)
                })
                status_icon = '✅' if result else '❌'
                self.stdout.write(f'  {status_icon} {test_name}')
                
            except Exception as e:
                self.test_results.append({
                    'category': category_name,
                    'name': test_name,
                    'status': 'ERROR',
                    'details': str(e)
                })
                self.stdout.write(f'  ⚠️  {test_name}: {str(e)}')
    
    # 基本機能テスト実装
    def test_home_page(self):
        """ホームページのテスト"""
        response = self.client.get('/')
        return response.status_code == 200 and 'GRACE SPA' in response.content.decode()
    
    def test_booking_step1(self):
        """予約ステップ1のテスト"""
        response = self.client.get(reverse('bookings:booking_step1'))
        return response.status_code == 200 and 'サービス選択' in response.content.decode()
    
    def test_booking_step2(self):
        """予約ステップ2のテスト（セッション付き）"""
        # セッションにステップ1のデータを設定
        session = self.client.session
        session['booking_data'] = {'service_id': self.service.id}
        session.save()
        
        response = self.client.get(reverse('bookings:booking_step2'))
        return response.status_code == 200
    
    def test_booking_step3(self):
        """予約ステップ3のテスト（セッション付き）"""
        # セッションにステップ1-2のデータを設定
        session = self.client.session
        tomorrow = (timezone.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
        session['booking_data'] = {
            'service_id': self.service.id,
            'booking_date': tomorrow,
            'booking_time': '10:00',
            'therapist_id': self.therapist.id
        }
        session.save()
        
        response = self.client.get(reverse('bookings:booking_step3'))
        return response.status_code == 200
    
    def test_therapists_page(self):
        """セラピスト紹介ページのテスト"""
        response = self.client.get(reverse('website:therapists'))
        return response.status_code == 200
    
    def test_available_times_api(self):
        """時間枠取得APIのテスト"""
        tomorrow = (timezone.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
        response = self.client.get(
            reverse('bookings:get_available_times'),
            {'date': tomorrow, 'service_id': self.service.id}
        )
        return response.status_code == 200
    
    # バリデーションテスト実装
    def test_required_fields(self):
        """必須項目のテスト"""
        # セッションデータを設定
        session = self.client.session
        tomorrow = (timezone.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
        session['booking_data'] = {
            'service_id': self.service.id,
            'booking_date': tomorrow,
            'booking_time': '10:00',
            'therapist_id': self.therapist.id
        }
        session.save()
        
        # 必須項目を空で送信
        response = self.client.post(reverse('bookings:booking_step3'), {
            'customer_name': '',  # 必須項目を空に
            'customer_email': 'test@example.com',
            'customer_phone': '090-1234-5678',
            'customer_gender': 'male',
            'customer_is_first_visit': 'True',
            'booking_notes': ''
        })
        
        # エラーメッセージが含まれているかチェック
        return 'お名前は必須' in response.content.decode() or response.status_code != 302
    
    def test_email_format(self):
        """メールアドレス形式のテスト"""
        session = self.client.session
        tomorrow = (timezone.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
        session['booking_data'] = {
            'service_id': self.service.id,
            'booking_date': tomorrow,
            'booking_time': '10:00',
            'therapist_id': self.therapist.id
        }
        session.save()
        
        # 無効なメールアドレス
        response = self.client.post(reverse('bookings:booking_step3'), {
            'customer_name': 'テスト太郎',
            'customer_email': 'invalid-email',  # 無効なメール形式
            'customer_phone': '090-1234-5678',
            'customer_gender': 'male',
            'customer_is_first_visit': 'True',
            'booking_notes': ''
        })
        
        return 'メールアドレス' in response.content.decode() and response.status_code != 302
    
    def test_phone_format(self):
        """電話番号形式のテスト"""
        session = self.client.session
        tomorrow = (timezone.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
        session['booking_data'] = {
            'service_id': self.service.id,
            'booking_date': tomorrow,
            'booking_time': '10:00',
            'therapist_id': self.therapist.id
        }
        session.save()
        
        # 無効な電話番号
        response = self.client.post(reverse('bookings:booking_step3'), {
            'customer_name': 'テスト太郎',
            'customer_email': 'test@example.com',
            'customer_phone': '090-abcd-5678',  # 無効な電話番号形式
            'customer_gender': 'male',
            'customer_is_first_visit': 'True',
            'booking_notes': ''
        })
        
        return '電話番号' in response.content.decode() and response.status_code != 302
    
    def test_sql_injection(self):
        """SQLインジェクション対策のテスト"""
        session = self.client.session
        tomorrow = (timezone.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
        session['booking_data'] = {
            'service_id': self.service.id,
            'booking_date': tomorrow,
            'booking_time': '10:00',
            'therapist_id': self.therapist.id
        }
        session.save()
        
        # SQLインジェクション試行
        response = self.client.post(reverse('bookings:booking_step3'), {
            'customer_name': "'; DROP TABLE customers; --",
            'customer_email': 'test@example.com',
            'customer_phone': '090-1234-5678',
            'customer_gender': 'male',
            'customer_is_first_visit': 'True',
            'booking_notes': ''
        })
        
        # テーブルが存在することを確認（削除されていない）
        try:
            Customer.objects.count()
            return True
        except:
            return False
    
    def test_xss_protection(self):
        """XSS対策のテスト"""
        session = self.client.session
        tomorrow = (timezone.now().date() + timedelta(days=1)).strftime('%Y-%m-%d')
        session['booking_data'] = {
            'service_id': self.service.id,
            'booking_date': tomorrow,
            'booking_time': '10:00',
            'therapist_id': self.therapist.id
        }
        session.save()
        
        xss_script = "<script>alert('XSS')</script>"
        response = self.client.post(reverse('bookings:booking_step3'), {
            'customer_name': 'テスト太郎',
            'customer_email': 'test@example.com',
            'customer_phone': '090-1234-5678',
            'customer_gender': 'male',
            'customer_is_first_visit': 'True',
            'booking_notes': xss_script
        })
        
        # レスポンスにスクリプトタグがエスケープされて含まれていることを確認
        return xss_script not in response.content.decode()
    
    def test_csrf_protection(self):
        """CSRF保護のテスト"""
        # CSRFトークン無しでリクエスト
        response = self.client.post(reverse('bookings:booking_step3'), {
            'customer_name': 'テスト太郎',
            'customer_email': 'test@example.com',
            'customer_phone': '090-1234-5678'
        }, HTTP_X_CSRFTOKEN='invalid-token')
        
        # 403エラーまたはCSRFエラーが返されることを確認
        return response.status_code == 403
    
    # メール機能テスト
    def test_mail_settings(self):
        """メール設定のテスト"""
        try:
            mail_settings = MailSettings.objects.first()
            return mail_settings is not None
        except:
            return False
    
    def test_email_templates(self):
        """メールテンプレートのテスト"""
        try:
            templates = EmailTemplate.objects.all()
            return templates.count() > 0
        except:
            return False
    
    def test_booking_confirmation_email(self):
        """予約確認メールのテスト"""
        # テスト用顧客を作成
        customer = Customer.objects.create(
            name='テスト太郎',
            email='test@example.com',
            phone='090-1234-5678'
        )
        
        # テスト用予約を作成
        tomorrow = timezone.now().date() + timedelta(days=1)
        booking = Booking.objects.create(
            customer=customer,
            service=self.service,
            therapist=self.therapist,
            booking_date=tomorrow,
            booking_time='10:00',
            status='pending'
        )
        
        # メール送信をテスト（実際には送信しない）
        from emails.utils import render_email_template
        try:
            context = {'booking': booking}
            subject, body_text, body_html = render_email_template('customer_booking_confirmation', context)
            return subject is not None and body_text is not None
        except:
            return False
    
    # 管理機能テスト
    def test_admin_access(self):
        """管理画面アクセスのテスト"""
        response = self.client.get('/admin/')
        return response.status_code in [200, 302]  # ログイン画面にリダイレクトされるのは正常
    
    def test_dashboard(self):
        """ダッシュボードのテスト"""
        # 管理者でログイン
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            self.client.force_login(admin_user)
            response = self.client.get('/dashboard/dashboard/')
            return response.status_code == 200
        return False
    
    def test_booking_management(self):
        """予約管理のテスト"""
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            self.client.force_login(admin_user)
            response = self.client.get('/dashboard/bookings/')
            return response.status_code == 200
        return False
    
    def test_customer_management(self):
        """顧客管理のテスト"""
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            self.client.force_login(admin_user)
            response = self.client.get('/dashboard/customers/')
            return response.status_code == 200
        return False
    
    # セキュリティテスト
    def test_auth_protection(self):
        """認証保護のテスト"""
        # 未認証でダッシュボードにアクセス
        response = self.client.get('/dashboard/dashboard/')
        return response.status_code in [302, 401, 403]  # リダイレクトまたは認証エラー
    
    def test_permission_check(self):
        """権限チェックのテスト"""
        # 一般ユーザーでダッシュボードにアクセス
        regular_user, created = User.objects.get_or_create(
            username='regular_user',
            defaults={'email': 'user@example.com'}
        )
        self.client.force_login(regular_user)
        response = self.client.get('/dashboard/dashboard/')
        return response.status_code in [302, 401, 403]
    
    def test_security_headers(self):
        """セキュリティヘッダーのテスト"""
        response = self.client.get('/')
        headers = response.headers
        
        # 重要なセキュリティヘッダーの確認
        security_checks = [
            'X-Frame-Options' in headers,
            'X-Content-Type-Options' in headers,
            # その他のセキュリティヘッダー
        ]
        
        return any(security_checks)
    
    def display_results(self):
        """テスト結果の表示"""
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('📊 テスト結果サマリー'))
        
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r['status'] == 'PASS'])
        failed = len([r for r in self.test_results if r['status'] == 'FAIL'])
        errors = len([r for r in self.test_results if r['status'] == 'ERROR'])
        
        self.stdout.write(f'総テスト数: {total_tests}')
        self.stdout.write(f'✅ 成功: {passed}')
        self.stdout.write(f'❌ 失敗: {failed}')
        self.stdout.write(f'⚠️  エラー: {errors}')
        
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        self.stdout.write(f'成功率: {success_rate:.1f}%')
        
        # カテゴリ別結果
        self.stdout.write('\n📋 カテゴリ別結果:')
        categories = {}
        for result in self.test_results:
            category = result['category']
            if category not in categories:
                categories[category] = {'pass': 0, 'fail': 0, 'error': 0}
            categories[category][result['status'].lower()] += 1
        
        for category, stats in categories.items():
            total = stats['pass'] + stats['fail'] + stats['error']
            rate = (stats['pass'] / total * 100) if total > 0 else 0
            self.stdout.write(f'  {category}: {stats["pass"]}/{total} ({rate:.1f}%)')
        
        # 失敗・エラーの詳細
        if failed > 0 or errors > 0:
            self.stdout.write('\n⚠️  要修正項目:')
            for result in self.test_results:
                if result['status'] in ['FAIL', 'ERROR']:
                    icon = '❌' if result['status'] == 'FAIL' else '⚠️'
                    self.stdout.write(f'  {icon} [{result["category"]}] {result["name"]}')
                    if self.detailed and result.get('details'):
                        self.stdout.write(f'     詳細: {result["details"]}')
        
        # 推奨事項
        self.stdout.write('\n💡 推奨事項:')
        if success_rate >= 90:
            self.stdout.write('  ✨ システムは良好な状態です。英語化作業を開始できます。')
        elif success_rate >= 75:
            self.stdout.write('  🔧 いくつかの問題がありますが、軽微な修正で対応可能です。')
        else:
            self.stdout.write('  🚨 重要な問題が複数あります。修正してから英語化を進めてください。')
        
        self.stdout.write('\n' + '=' * 50)