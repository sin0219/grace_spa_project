from django.core.management.base import BaseCommand
from bookings.models import BusinessHours, BookingSettings
import datetime

class Command(BaseCommand):
    help = '営業時間とBookingSettingsの初期設定を行います'

    def handle(self, *args, **options):
        self.stdout.write('営業時間の設定を開始します...')
        
        # 営業時間の設定
        business_hours_data = [
            # 月曜日から土曜日は営業
            {'weekday': 0, 'is_open': True, 'open_time': '09:00', 'close_time': '20:00', 'last_booking_time': '19:00'},  # 月
            {'weekday': 1, 'is_open': True, 'open_time': '09:00', 'close_time': '20:00', 'last_booking_time': '19:00'},  # 火
            {'weekday': 2, 'is_open': True, 'open_time': '09:00', 'close_time': '20:00', 'last_booking_time': '19:00'},  # 水
            {'weekday': 3, 'is_open': True, 'open_time': '09:00', 'close_time': '20:00', 'last_booking_time': '19:00'},  # 木
            {'weekday': 4, 'is_open': True, 'open_time': '09:00', 'close_time': '20:00', 'last_booking_time': '19:00'},  # 金
            {'weekday': 5, 'is_open': True, 'open_time': '09:00', 'close_time': '20:00', 'last_booking_time': '19:00'},  # 土
            # 日曜日は定休日
            {'weekday': 6, 'is_open': False, 'open_time': '09:00', 'close_time': '20:00', 'last_booking_time': '19:00'},  # 日
        ]
        
        for data in business_hours_data:
            business_hour, created = BusinessHours.objects.get_or_create(
                weekday=data['weekday'],
                defaults={
                    'is_open': data['is_open'],
                    'open_time': datetime.time.fromisoformat(data['open_time']),
                    'close_time': datetime.time.fromisoformat(data['close_time']),
                    'last_booking_time': datetime.time.fromisoformat(data['last_booking_time']),
                }
            )
            if created:
                weekday_names = ['月', '火', '水', '木', '金', '土', '日']
                status = '営業' if data['is_open'] else '定休日'
                self.stdout.write(
                    self.style.SUCCESS(f'{weekday_names[data["weekday"]]}曜日: {status} ({data["open_time"]}-{data["close_time"]})')
                )
            else:
                weekday_names = ['月', '火', '水', '木', '金', '土', '日']
                self.stdout.write(f'{weekday_names[data["weekday"]]}曜日: 既に設定済み')
        
        # BookingSettingsの設定
        self.stdout.write('\n予約設定を確認します...')
        
        booking_settings, created = BookingSettings.objects.get_or_create(
            defaults={
                'booking_interval_minutes': 30,  # 30分刻み
                'treatment_buffer_minutes': 15,   # 15分インターバル
                'advance_booking_days': 90,       # 90日先まで予約可能
                'same_day_booking_cutoff_hour': 12,  # 当日予約は12時まで
                'enable_therapist_selection': True,   # 施術者選択を有効
                'max_concurrent_bookings': 3,     # 同時予約数上限
                'enable_online_payment': False,   # オンライン決済は無効
                'require_phone_verification': False,  # 電話認証は不要
                'auto_confirm_bookings': False,   # 自動承認は無効
                'send_reminder_emails': True,     # リマインダーメール有効
                'reminder_hours_before': 24,      # 24時間前にリマインダー
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('BookingSettingsを作成しました'))
        else:
            self.stdout.write('BookingSettings: 既に設定済み')
        
        self.stdout.write(self.style.SUCCESS('\n営業時間とBookingSettingsの設定が完了しました！'))
        self.stdout.write('管理画面で詳細な設定を変更できます: /admin/')