# bookings/management/commands/simple_fix.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = '基本的な問題を自動修正します（簡潔版）'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='修正せずにチェックのみ実行'
        )
    
    def handle(self, *args, **options):
        check_only = options['check_only']
        
        self.stdout.write(self.style.SUCCESS('🔧 簡潔版クイック修正'))
        
        if check_only:
            self.stdout.write(self.style.WARNING('⚠️ チェックモード'))
        
        self.stdout.write('=' * 40)
        
        results = []
        
        # 1. 管理者ユーザーチェック
        admin_exists = User.objects.filter(is_superuser=True).exists()
        if admin_exists:
            results.append(('管理者ユーザー', 'OK'))
            self.stdout.write('  ✅ 管理者ユーザー: 存在')
        else:
            if not check_only:
                User.objects.create_superuser(
                    username='admin',
                    email='admin@gracespa.com',
                    password='admin123'
                )
                results.append(('管理者ユーザー', 'FIXED'))
                self.stdout.write('  🔧 管理者ユーザー: 作成完了')
            else:
                results.append(('管理者ユーザー', 'NEED_FIX'))
                self.stdout.write('  ⚠️  管理者ユーザー: 要作成')
        
        # 2. 基本サービスチェック
        try:
            from bookings.models import Service
            service_count = Service.objects.filter(is_active=True).count()
            
            if service_count > 0:
                results.append(('基本サービス', 'OK'))
                self.stdout.write(f'  ✅ 基本サービス: {service_count}件存在')
            else:
                if not check_only:
                    # 基本サービス作成
                    Service.objects.create(
                        name='リラクゼーションマッサージ',
                        duration_minutes=60,
                        price=8000,
                        description='全身をゆっくりとほぐすリラクゼーションマッサージです。',
                        sort_order=1,
                        is_active=True
                    )
                    Service.objects.create(
                        name='アロマトリートメント',
                        duration_minutes=90,
                        price=12000,
                        description='天然アロマオイルを使用したトリートメントです。',
                        sort_order=2,
                        is_active=True
                    )
                    results.append(('基本サービス', 'FIXED'))
                    self.stdout.write('  🔧 基本サービス: 作成完了')
                else:
                    results.append(('基本サービス', 'NEED_FIX'))
                    self.stdout.write('  ⚠️  基本サービス: 要作成')
                    
        except ImportError:
            results.append(('基本サービス', 'SKIP'))
            self.stdout.write('  ⏭️  基本サービス: スキップ')
        
        # 3. 施術者チェック
        try:
            from bookings.models import Therapist
            therapist_count = Therapist.objects.filter(is_active=True).count()
            
            if therapist_count > 0:
                results.append(('施術者', 'OK'))
                self.stdout.write(f'  ✅ 施術者: {therapist_count}名存在')
            else:
                if not check_only:
                    Therapist.objects.create(
                        name='therapist1',
                        display_name='田中 美穂',
                        is_active=True,
                        sort_order=1
                    )
                    Therapist.objects.create(
                        name='therapist2',
                        display_name='佐藤 恵子',
                        is_active=True,
                        sort_order=2
                    )
                    results.append(('施術者', 'FIXED'))
                    self.stdout.write('  🔧 施術者: 作成完了')
                else:
                    results.append(('施術者', 'NEED_FIX'))
                    self.stdout.write('  ⚠️  施術者: 要作成')
                    
        except ImportError:
            results.append(('施術者', 'SKIP'))
            self.stdout.write('  ⏭️  施術者: スキップ')
        
        # 4. 営業時間チェック
        try:
            from bookings.models import BusinessHours
            hours_count = BusinessHours.objects.filter(is_open=True).count()
            
            if hours_count > 0:
                results.append(('営業時間', 'OK'))
                self.stdout.write(f'  ✅ 営業時間: {hours_count}日設定済み')
            else:
                if not check_only:
                    # 月〜土曜日の営業時間作成
                    for weekday in range(6):
                        BusinessHours.objects.create(
                            weekday=weekday,
                            is_open=True,
                            open_time='09:00',
                            close_time='18:00',
                            last_booking_time='17:00'
                        )
                    results.append(('営業時間', 'FIXED'))
                    self.stdout.write('  🔧 営業時間: 作成完了')
                else:
                    results.append(('営業時間', 'NEED_FIX'))
                    self.stdout.write('  ⚠️  営業時間: 要作成')
                    
        except ImportError:
            results.append(('営業時間', 'SKIP'))
            self.stdout.write('  ⏭️  営業時間: スキップ')
        
        # 5. メール設定チェック
        try:
            from emails.models import MailSettings
            mail_count = MailSettings.objects.count()
            
            if mail_count > 0:
                results.append(('メール設定', 'OK'))
                self.stdout.write('  ✅ メール設定: 存在')
            else:
                if not check_only:
                    MailSettings.objects.create(
                        from_name='GRACE SPA',
                        from_email='info@gracespa.com',
                        admin_email='admin@gracespa.com',
                        enable_customer_notifications=True,
                        enable_admin_notifications=True,
                        enable_reminders=True,
                        reminder_hours_before_24=True,
                        reminder_hours_before_2=True,
                        signature='GRACE SPA\n〒000-0000 東京都○○区○○\nTEL: 03-0000-0000'
                    )
                    results.append(('メール設定', 'FIXED'))
                    self.stdout.write('  🔧 メール設定: 作成完了')
                else:
                    results.append(('メール設定', 'NEED_FIX'))
                    self.stdout.write('  ⚠️  メール設定: 要作成')
                    
        except ImportError:
            results.append(('メール設定', 'SKIP'))
            self.stdout.write('  ⏭️  メール設定: emailsアプリ未設定')
        
        # 結果サマリー
        self.stdout.write('\n' + '=' * 40)
        self.stdout.write(self.style.SUCCESS('📊 結果サマリー'))
        
        ok_count = len([r for r in results if r[1] == 'OK'])
        fixed_count = len([r for r in results if r[1] == 'FIXED'])
        need_fix_count = len([r for r in results if r[1] == 'NEED_FIX'])
        skip_count = len([r for r in results if r[1] == 'SKIP'])
        
        self.stdout.write(f'✅ 正常: {ok_count}')
        if not check_only:
            self.stdout.write(f'🔧 修正済み: {fixed_count}')
        else:
            self.stdout.write(f'⚠️  要修正: {need_fix_count}')
        self.stdout.write(f'⏭️  スキップ: {skip_count}')
        
        # 推奨事項
        if not check_only and fixed_count > 0:
            self.stdout.write('\n💡 修正が完了しました。テストを実行してください：')
            self.stdout.write('python manage.py simple_test')
        elif check_only and need_fix_count > 0:
            self.stdout.write('\n💡 修正を実行するには：')
            self.stdout.write('python manage.py simple_fix')
        else:
            self.stdout.write('\n✨ 基本設定は完了しています。')
        
        self.stdout.write('=' * 40)